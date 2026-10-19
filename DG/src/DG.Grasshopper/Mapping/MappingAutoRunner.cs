#if GRASSHOPPER_SDK
using DG.Core.Mapping;
using DG.Core.Models;
using Grasshopper;
using Grasshopper.Kernel;
using Grasshopper.Kernel.Data;
using Rhino;
using Timer = System.Threading.Timer;

namespace DG.Grasshopper.Mapping;

/// <summary>What CONNECTOR shows for mapping: summary text, geometry by class, slider mapping.</summary>
internal sealed class MappingOutputs
{
    public string Summary { get; init; } = string.Empty;

    public List<string> ClassNames { get; init; } = new();

    public List<OntologyClass> ClassObjects { get; init; } = new();

    public DataTree<object> ByClass { get; init; } = new();

    public List<string> Sliders { get; init; } = new();

    public string MessageSuffix { get; init; } = string.Empty;
}

/// <summary>
/// Automatic mapping owned by CONNECTOR (Phase 1303, owner amendment 2026-10-18): once the
/// account is signed in, every settled change of the canvas is read (no mapping component,
/// no wiring), sent to DG as a mapping session when its content changed, coloured in Rhino by
/// mapping state, followed while draft answers are reviewed, and delivered only after explicit
/// batch confirmation. Geometry is read on Rhino's UI thread; HTTP runs in the background.
/// The connector session goes only into the Authorization header.
/// </summary>
internal sealed class MappingAutoRunner : IDisposable
{
    private const int DebounceMs = 1500;
    private const int PollMs = 3000;

    // Process-lifetime delivery journal: a receipt retry or sign-in must never repeat canvas writes.
    private static readonly Dictionary<(GH_Document Document, string Session, string Batch), MappingDeliveryReceipt?> Deliveries = new();

    private readonly GH_Component _owner;
    private readonly string _dataServiceUrl;
    private readonly MappingSessionClient _client = new();
    private readonly MappingPreviewConduit _conduit = new();
    private readonly MappingCanvasTags _tags = new();
    private readonly object _timerGate = new();

    private GH_Document? _doc;
    private string? _token;
    private string _project = string.Empty;
    private bool _enabled;

    private Timer? _debounce;
    private Timer? _poll;
    private int _polling;

    private string? _postedFingerprint;
    private CanvasMappingRead? _read;
    private MappingSessionState? _session;
    private MappingApplyResult? _applied;
    private MappingBatchPlacer _placer = new();
    private readonly HashSet<string> _deliveredBatchIds = new(StringComparer.Ordinal);
    private string? _placement;
    private string _status = "Mapping: sign in to map automatically";
    private volatile MappingOutputs _outputs = new() { Summary = "Mapping: sign in to map automatically" };

    public MappingAutoRunner(GH_Component owner, string dataServiceUrl)
    {
        _owner = owner;
        _dataServiceUrl = dataServiceUrl;
    }

    public MappingOutputs Outputs => _outputs;

    /// <summary>Signed in with AutoMap on: the runner reads the canvas and follows sessions.</summary>
    public bool Enabled => _enabled;

    public string? SessionId => _session?.SessionId;

    public string Status => _status;

    /// <summary>
    /// Plan 1303-10 (DeGram «Запустить меппинг», bridge command start_mapping): read the canvas now and
    /// create a session even when its content was already sent. UI thread.
    /// </summary>
    public (bool Started, string Message) StartNow()
    {
        if (!_enabled || _doc is null || string.IsNullOrEmpty(_token))
        {
            return (false, _status);
        }

        _postedFingerprint = null;
        _session = null;
        ScheduleScan();
        return (true, "Mapping: reading the canvas");
    }

    /// <summary>Called from CONNECTOR.SolveInstance on the UI thread.</summary>
    public void Configure(GH_Document? doc, string? token, string? project, bool enabled)
    {
        if (!enabled || string.IsNullOrEmpty(token) || doc is null)
        {
            var reason = !enabled
                ? "Mapping: off (AutoMap = false)"
                : string.IsNullOrEmpty(token) ? "Mapping: sign in to map automatically" : "Mapping: no document";
            if (_enabled || _session is not null || _status != reason)
            {
                Stop(reason);
            }

            return;
        }

        var bound = string.IsNullOrWhiteSpace(project) ? "default-project" : project.Trim();
        var changed = !ReferenceEquals(doc, _doc) || token != _token || bound != _project || !_enabled;
        _token = token;
        _project = bound;
        _enabled = true;
        if (!ReferenceEquals(doc, _doc))
        {
            Detach();
            _doc = doc;
            _doc.SolutionEnd += OnSolutionEnd;
        }

        if (changed)
        {
            _postedFingerprint = null;
            _session = null;
            _read = null;
            _applied = null;
            _tags.Clear();
            ScheduleScan();
        }
    }

    public void Dispose()
    {
        Stop("Mapping: off");
        Detach();
        _conduit.Enabled = false;
        _tags.Dispose();
    }

    private void Detach()
    {
        if (_doc is not null)
        {
            _doc.SolutionEnd -= OnSolutionEnd;
            _doc = null;
        }
    }

    private void Stop(string reason)
    {
        _enabled = false;
        lock (_timerGate)
        {
            _debounce?.Dispose();
            _debounce = null;
            _poll?.Dispose();
            _poll = null;
        }

        _postedFingerprint = null;
        _read = null;
        _session = null;
        _applied = null;
        _tags.Clear();
        _status = reason;
        _outputs = new MappingOutputs { Summary = reason };
        _conduit.Update(Array.Empty<(Rhino.Geometry.GeometryBase, System.Drawing.Color)>());
        _conduit.Enabled = false;
        RhinoDoc.ActiveDoc?.Views.Redraw();
    }

    private void OnSolutionEnd(object sender, GH_SolutionEventArgs e) => ScheduleScan();

    private void ScheduleScan()
    {
        if (!_enabled)
        {
            return;
        }

        lock (_timerGate)
        {
            if (_debounce is null)
            {
                _debounce = new Timer(_ => RhinoApp.InvokeOnUiThread(new Action(ScanOnUi)), null, DebounceMs, Timeout.Infinite);
            }
            else
            {
                _debounce.Change(DebounceMs, Timeout.Infinite);
            }
        }
    }

    private void ScanOnUi()
    {
        var doc = _doc;
        if (!_enabled || doc is null || string.IsNullOrEmpty(_token))
        {
            return;
        }

        if (doc.SolutionState == GH_ProcessStep.Process)
        {
            ScheduleScan();
            return;
        }

        CanvasMappingRead read;
        try
        {
            read = MappingCanvasReader.Read(doc, _read);
        }
        catch (Exception ex)
        {
            Publish($"Mapping: could not read the canvas ({ex.GetType().Name})", expire: true);
            return;
        }

        if (read.Snapshot.IsEmpty)
        {
            Publish("Mapping: nothing to map — no geometry wired into DG components, no visible geometry, no named sliders", expire: true);
            return;
        }

        var fingerprint = read.SourceSignature;
        if (fingerprint == _postedFingerprint)
        {
            return;
        }

        _postedFingerprint = fingerprint;
        _session = null; // Invalidate delivery from the previous source state while the new session is created.
        var token = _token;
        var project = _project;
        var json = read.Snapshot.ToRequestJson(project, $"{read.DocumentKey} · {DateTime.Now:HH:mm:ss}");
        _status = $"Mapping: sending {read.Snapshot.Elements.Count} elements and {read.Snapshot.Parameters.Count} sliders to DG…";
        _ = Task.Run(async () =>
        {
            var created = await _client.CreateAsync(_dataServiceUrl, token, json).ConfigureAwait(false);
            RhinoApp.InvokeOnUiThread(new Action(() => OnCreated(doc, token, project, read, fingerprint, created)));
        });
    }

    private void OnCreated(GH_Document document, string token, string project, CanvasMappingRead read,
        string fingerprint, MappingCallResult<MappingSessionState> created)
    {
        if (!_enabled || _token != token || _project != project || !ReferenceEquals(_doc, document)
            || fingerprint != _postedFingerprint)
        {
            return; // superseded by a newer canvas state or switched off
        }

        if (!created.Ok)
        {
            Publish($"Mapping: DG refused the session ({created.Status} {created.ErrorCode}). Change the canvas or toggle AutoMap to retry.", expire: true);
            return;
        }

        _read = read;
        _placer = new MappingBatchPlacer();
        _deliveredBatchIds.Clear();
        _placement = null;
        _session = created.Value;
        _applied = null;
        UpdateConduit();
        BuildOutputs(expire: true);
        StartPolling(); // An empty question list is not permission to commit or write.
    }

    private void StartPolling()
    {
        lock (_timerGate)
        {
            _poll ??= new Timer(_ => _ = PollAsync(), null, PollMs, PollMs);
        }
    }

    private void StopPolling()
    {
        lock (_timerGate)
        {
            _poll?.Dispose();
            _poll = null;
        }
    }

    private async Task PollAsync()
    {
        if (Interlocked.Exchange(ref _polling, 1) == 1)
        {
            return;
        }

        try
        {
            var current = _session;
            var token = _token;
            if (current is null || string.IsNullOrEmpty(token) || !_enabled)
            {
                return;
            }

            var project = _project;
            var document = _doc;
            var fresh = await _client.GetAsync(_dataServiceUrl, token, project, current.SessionId).ConfigureAwait(false);
            if (!fresh.Ok)
            {
                return;
            }

            var state = fresh.Value!;
            RhinoApp.InvokeOnUiThread(new Action(() =>
            {
                if (!_enabled || _token != token || _project != project || !ReferenceEquals(_doc, document)
                    || _session?.SessionId != state.SessionId)
                {
                    return;
                }

                _session = state;
                UpdateConduit();
                BuildOutputs(expire: false);
                if (state.AppliedAt is null)
                {
                    DeliverNextBatch(state, token, project);
                }
            }));
        }
        catch
        {
            // best effort: the next tick tries again
        }
        finally
        {
            Interlocked.Exchange(ref _polling, 0);
        }
    }

    /// <summary>Deliver only a committed batch. Every canvas mutation is on the pinned document's UI thread.</summary>
    private void DeliverNextBatch(MappingSessionState state, string token, string project)
    {
        var doc = _doc;
        var read = _read;
        var batch = state.Batches.FirstOrDefault(b => b.DeliveryState == "queued");
        if (doc is null || read is null || batch is null)
        {
            return;
        }

        var key = (doc, state.SessionId, batch.BatchId);
        if (Deliveries.TryGetValue(key, out var receipt))
        {
            if (receipt is not null)
            {
                // Only HTTP is repeated; no placement or data writes on receipt failure.
                _ = _client.AcknowledgeAsync(_dataServiceUrl, token, project, state.SessionId, batch.BatchId, receipt);
            }
            else
            {
                _placement = "batch delivery is uncertain; it will not be replayed automatically";
            }

            return;
        }

        if (state.Batches.TakeWhile(b => b.BatchId != batch.BatchId).Any(b => b.DeliveryState == "failed"
            || !_deliveredBatchIds.Contains(b.BatchId)))
        {
            _placement = "earlier batch delivery is failed or unknown in this connector; automatic continuation disabled";
            BuildOutputs(expire: false);
            return;
        }

        Deliveries[key] = null; // Reserve before scheduling; sign-out/reload cannot replay the work.
        var applied = batch.Payload;
        MappingApplyResult cumulative;
        try
        {
            cumulative = MappingSelection.Append(_applied ?? new MappingApplyResult(), applied);
            _ = MappingSelection.Classes(applied, read.Snapshot);
            if (!_placer.IsIntact(doc)) throw new InvalidOperationException("Owned mapping components changed");
        }
        catch (Exception ex)
        {
            _placement = $"batch not written: {ex.GetType().Name}; review the source and committed history";
            Deliveries[key] = new MappingDeliveryReceipt("failed", 0, applied.RolesByElement.Count);
            BuildOutputs(expire: false);
            return;
        }

        doc.ScheduleSolution(5, d =>
        {
            if (!_enabled || _token != token || _project != project || !ReferenceEquals(_doc, d)
                || _session?.SessionId != state.SessionId)
            {
                Deliveries[key] = new MappingDeliveryReceipt("failed", 0, applied.RolesByElement.Count);
                return;
            }

            var mutationStarted = false;
            try
            {
                // Ignore our own added wiring when rereading the original sources.
                var freshRead = MappingCanvasReader.Read(d, read);
                if (freshRead.SourceSignature != read.SourceSignature)
                    throw new InvalidOperationException("The source canvas changed");
                mutationStarted = true;
                _placement = _placer.Place(d, _owner, freshRead, applied, cumulative);
                // Component insertion is not delivery success: wait for this solution's outputs.
                GH_Document.SolutionEndEventHandler? completed = null;
                var placer = _placer;
                completed = (_, _) =>
                {
                    d.SolutionEnd -= completed;
                    if (placer.VerifyLastDelivery())
                    {
                        if (_session?.SessionId == state.SessionId && ReferenceEquals(_doc, d))
                        {
                            _applied = cumulative;
                            _deliveredBatchIds.Add(batch.BatchId);
                        }
                        Deliveries[key] = new MappingDeliveryReceipt("written", applied.RolesByElement.Count, 0);
                    }
                    else
                    {
                        _placement = "placed components did not produce the committed selection; delivery uncertain, replay disabled";
                    }
                    BuildOutputs(expire: true);
                };
                d.SolutionEnd += completed;
            }
            catch (Exception ex)
            {
                // Once placement starts, cleanup is not proof of rollback. Never automatically replay it.
                if (!mutationStarted) Deliveries[key] = new MappingDeliveryReceipt("failed", 0, applied.RolesByElement.Count);
                _placement = $"placement unconfirmed: {ex.GetType().Name}; automatic replay disabled";
                BuildOutputs(expire: false);
            }
        });
    }

    private void UpdateConduit()
    {
        var read = _read;
        var session = _session;
        if (read is null || session is null)
        {
            return;
        }

        var items = new List<(Rhino.Geometry.GeometryBase, System.Drawing.Color)>();
        foreach (var id in read.Order)
        {
            if (read.Previews.TryGetValue(id, out var g))
            {
                var state = session.Elements.TryGetValue(id, out var es) ? es.State : "unmapped";
                items.Add((g, MappingPreviewConduit.ColourOf(state)));
            }
        }

        _conduit.Update(items);
        _conduit.Enabled = true;
        RhinoDoc.ActiveDoc?.Views.Redraw();
        if (_applied is null)
        {
            _tags.Show(_doc, session.Tags);
        }
    }

    private void BuildOutputs(bool expire)
    {
        var read = _read;
        var s = _session;
        if (read is null || s is null)
        {
            return;
        }

        var lines = new List<string>();
        var parts = new[] { "confirmed", "auto", "suggested", "ambiguous", "unmapped" }
            .Where(k => s.Counts.TryGetValue(k, out var n) && n > 0)
            .Select(k => $"{k} {s.Counts[k]}");
        lines.Add($"Mapping {read.DocumentKey}: {s.Total} elements ({string.Join(", ", parts)}), {s.Measures.Count} calculation outputs, {s.Parameters.Count} sliders, {s.OpenQuestions} open question(s)" + (s.LlmStatus is null ? string.Empty : $", LLM {s.LlmStatus}"));
        lines.Add($"Review drafts and explicitly confirm in DG Web UI → Projects → {_project} → Mapping (session {s.SessionId}); answers alone never write the canvas");
        foreach (var batch in s.Batches)
        {
            lines.Add($"Batch {batch.BatchId}: {batch.DeliveryState}");
        }
        if (read.Streams.Count > 0)
        {
            lines.Add("Streams: " + string.Join(", ", read.Streams));
        }

        var mapped = s.Measures.Where(m => m.PropertyLabel is not null && m.State != "unmapped").Select(m => $"{m.Name} → {m.PropertyLabel} ({m.State})").ToList();
        if (mapped.Count > 0)
        {
            lines.Add("Outputs: " + string.Join("; ", mapped));
        }

        if (_placement is not null)
        {
            lines.Add("Placement: " + _placement);
        }

        lines.AddRange(read.Notes.Take(5).Select(n => "Note: " + n));

        var sliders = s.Parameters
            .Select(p => $"{p.Name} → {(p.State == "unmapped" ? "not a DG parameter" : "DG parameter")} ({p.State})")
            .ToList();

        var byClass = new DataTree<object>();
        var names = new List<string>();
        var objects = new List<OntologyClass>();
        if (_applied is not null)
        {
            var classes = _applied.RolesByElement.Values
                .SelectMany(r => r)
                .Distinct(StringComparer.Ordinal)
                .OrderBy(iri => MappingSessionClient.LocalName(iri), StringComparer.Ordinal)
                .ToList();
            for (var k = 0; k < classes.Count; k++)
            {
                var path = new GH_Path(k);
                byClass.EnsurePath(path);
                foreach (var id in read.Order)
                {
                    if (_applied.RolesByElement.TryGetValue(id, out var roles) && roles.Contains(classes[k]) && read.Previews.TryGetValue(id, out var g))
                    {
                        byClass.Add(g, path);
                    }
                }

                var local = MappingSessionClient.LocalName(classes[k]) ?? classes[k];
                names.Add(local);
                objects.Add(new OntologyClass { Iri = classes[k], Label = local });
            }
        }

        var suffix = s.OpenQuestions > 0 ? $" · Map: {s.OpenQuestions}?" : _applied is not null ? " · Map ✓" : " · Map …";
        _status = lines[0];
        _outputs = new MappingOutputs
        {
            Summary = string.Join(Environment.NewLine, lines),
            ByClass = byClass,
            ClassNames = names,
            ClassObjects = objects,
            Sliders = sliders,
            MessageSuffix = suffix,
        };

        if (expire)
        {
            ExpireOwner();
        }
        else
        {
            _owner.Message = (_owner.Message ?? string.Empty).Split(" · Map")[0] + suffix;
            Instances.RedrawCanvas();
        }
    }

    /// <summary>Shows a status line; re-solves CONNECTOR only when the text changed (no solve loop).</summary>
    private void Publish(string summary, bool expire)
    {
        var changed = !string.Equals(summary, _status, StringComparison.Ordinal);
        _status = summary;
        _outputs = new MappingOutputs { Summary = summary, MessageSuffix = " · Map !" };
        if (expire && changed)
        {
            ExpireOwner();
        }
    }

    private void ExpireOwner()
    {
        var doc = _doc;
        doc?.ScheduleSolution(5, _ => _owner.ExpireSolution(false));
    }
}
#endif
