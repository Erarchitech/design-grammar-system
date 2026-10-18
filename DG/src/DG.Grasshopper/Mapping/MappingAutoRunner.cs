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
/// mapping state, followed while the questions are answered in the DG Web UI, and applied
/// when no question is left. Geometry is read on Rhino's UI thread; HTTP runs in the background.
/// The connector session goes only into the Authorization header.
/// </summary>
internal sealed class MappingAutoRunner : IDisposable
{
    private const int DebounceMs = 1500;
    private const int PollMs = 3000;

    private readonly GH_Component _owner;
    private readonly string _dataServiceUrl;
    private readonly MappingSessionClient _client = new();
    private readonly MappingPreviewConduit _conduit = new();
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
    private bool _placed;
    private string? _placement;
    private string _status = "Mapping: sign in to map automatically";
    private volatile MappingOutputs _outputs = new() { Summary = "Mapping: sign in to map automatically" };

    public MappingAutoRunner(GH_Component owner, string dataServiceUrl)
    {
        _owner = owner;
        _dataServiceUrl = dataServiceUrl;
    }

    public MappingOutputs Outputs => _outputs;

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
            ScheduleScan();
        }
    }

    public void Dispose()
    {
        Stop("Mapping: off");
        Detach();
        _conduit.Enabled = false;
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
            read = MappingCanvasReader.Read(doc);
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

        var fingerprint = read.Snapshot.Fingerprint();
        if (fingerprint == _postedFingerprint)
        {
            return;
        }

        _postedFingerprint = fingerprint;
        var token = _token;
        var project = _project;
        var json = read.Snapshot.ToRequestJson(project, $"{read.DocumentKey} · {DateTime.Now:HH:mm:ss}");
        _status = $"Mapping: sending {read.Snapshot.Elements.Count} elements and {read.Snapshot.Parameters.Count} sliders to DG…";
        _ = Task.Run(async () =>
        {
            var created = await _client.CreateAsync(_dataServiceUrl, token, json).ConfigureAwait(false);
            RhinoApp.InvokeOnUiThread(new Action(() => OnCreated(read, fingerprint, created)));
        });
    }

    private void OnCreated(CanvasMappingRead read, string fingerprint, MappingCallResult<MappingSessionState> created)
    {
        if (!_enabled || fingerprint != _postedFingerprint)
        {
            return; // superseded by a newer canvas state or switched off
        }

        if (!created.Ok)
        {
            Publish($"Mapping: DG refused the session ({created.Status} {created.ErrorCode}). Change the canvas or toggle AutoMap to retry.", expire: true);
            return;
        }

        _read = read;
        _session = created.Value;
        _applied = null;
        UpdateConduit();
        BuildOutputs(expire: true);
        if (_session!.OpenQuestions == 0)
        {
            _ = ApplyAsync(_session.SessionId);
        }
        else
        {
            StartPolling();
        }
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

            var fresh = await _client.GetAsync(_dataServiceUrl, token, _project, current.SessionId).ConfigureAwait(false);
            if (!fresh.Ok)
            {
                return;
            }

            var state = fresh.Value!;
            if (state.Revision != current.Revision || state.OpenQuestions != current.OpenQuestions)
            {
                RhinoApp.InvokeOnUiThread(new Action(() =>
                {
                    if (_session?.SessionId != state.SessionId)
                    {
                        return;
                    }

                    _session = state;
                    UpdateConduit();
                    BuildOutputs(expire: false);
                }));
            }

            if (state.OpenQuestions == 0)
            {
                StopPolling();
                await ApplyAsync(state.SessionId).ConfigureAwait(false);
            }
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

    private async Task ApplyAsync(string sessionId)
    {
        var token = _token;
        if (string.IsNullOrEmpty(token))
        {
            return;
        }

        var applied = await _client.ApplyAsync(_dataServiceUrl, token, _project, sessionId).ConfigureAwait(false);
        RhinoApp.InvokeOnUiThread(new Action(() =>
        {
            if (_session?.SessionId != sessionId || !applied.Ok)
            {
                return;
            }

            _applied = applied.Value;
            BuildOutputs(expire: true);
            TryPlace();
        }));
    }

    /// <summary>
    /// D-38: on a definition without DG states, place and wire the DG components once the
    /// mapping is agreed. Runs once per document; a definition that already has OBJECT STATE /
    /// PROPERTY STATE / VALIDATOR is never changed.
    /// </summary>
    private void TryPlace()
    {
        var doc = _doc;
        var read = _read;
        var applied = _applied;
        if (_placed || doc is null || read is null || applied is null || read.HasDgWiring || MappingPlacer.HasStates(doc))
        {
            return;
        }

        _placed = true;
        var plan = MappingPlacementPlan.From(applied);
        doc.ScheduleSolution(5, d =>
        {
            try
            {
                _placement = MappingPlacer.Place(d, _owner, read, plan);
            }
            catch (Exception ex)
            {
                _placement = $"placement failed: {ex.GetType().Name}: {ex.Message}";
            }

            _owner.ExpireSolution(false);
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
        lines.Add(s.OpenQuestions > 0
            ? $"Answer in DG Web UI → Projects → {_project} → Mapping (session {s.SessionId})"
            : _applied is null ? $"Session {s.SessionId}: applying…" : $"Session {s.SessionId}: applied");
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

        var suffix = s.OpenQuestions > 0 ? $" · Map: {s.OpenQuestions}?" : _applied is not null ? " · Map ✓" : " · Map";
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
