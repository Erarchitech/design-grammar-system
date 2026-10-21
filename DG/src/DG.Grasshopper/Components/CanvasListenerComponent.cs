#if GRASSHOPPER_SDK
using System.Drawing;
using System.Globalization;
using System.Net;
using System.Net.Sockets;
using System.Text;
using System.Text.Json;
using DG.Core.Bridge;
using DG.Core.Parsing;
using DG.Grasshopper.Canvas;
using Grasshopper.Kernel;
using Grasshopper.Kernel.Special;
using Grasshopper.Kernel.Undo;
using Grasshopper.Kernel.Undo.Actions;
using Rhino;

namespace DG.Grasshopper.Components;

/// <summary>
/// DG CANVAS LISTENER -- a long-lived component that hosts a loopback-only
/// <see cref="TcpListener"/> and serves the DG Canvas Bridge wire protocol
/// (Plan 01's <see cref="CanvasBridgeProtocol"/>/<see cref="CanvasCommandDispatcher"/>)
/// to a single external client (grasshopper-mcp, Plan 03's gh_bridge.py) at a time.
/// Canvas reads (<c>get_canvas_context</c>, <c>get_selection</c>) are marshalled onto
/// Rhino's UI thread via <see cref="RhinoApp.InvokeOnUiThread"/>; the socket write
/// always happens on the background accept-loop thread (33-RESEARCH.md Pitfall 1).
/// </summary>
public sealed class CanvasListenerComponent : GH_Component
{
    private const int DefaultPort = 8720;
    private const int ClientReceiveTimeoutMs = 30000;

    private readonly CanvasCommandDispatcher _dispatcher;

    private TcpListener? _listener;
    private Task? _acceptLoopTask;
    private CancellationTokenSource? _listenerCts;
    private string _activeRequestKey = string.Empty;

    private volatile string _status = "Idle";
    private volatile string _lastCommand = string.Empty;

    // Legend scribble created by the last preview_structure call -- stashed here (rather
    // than in PreviewRegistry, which only tracks per-proposal group guids) so
    // clear_preview can remove it deterministically (35-PLAN.md Task 2).
    private Guid? _previewLegendGuid;

    public CanvasListenerComponent()
        : base(
            "DG CANVAS LISTENER",
            "DG CANVAS LISTENER",
            "Hosts a loopback-only TCP listener serving the DG Canvas Bridge wire protocol to grasshopper-mcp.",
            DgComponentCategory.Category,
            DgComponentCategory.GraphSubcategory)
    {
        _dispatcher = BuildDispatcher();
    }

    // Fresh GUID -- no prior component occupied this identity.
    public override Guid ComponentGuid => new("B0F26347-BB77-4593-A192-7BC3B0BC6169");

    protected override System.Drawing.Bitmap Icon => DgIcons.CanvasListener24;

    protected override void RegisterInputParams(GH_InputParamManager pManager)
    {
        pManager.AddBooleanParameter("Run", "Go", "Set true to start the DG Canvas Bridge listener", GH_ParamAccess.item, false);
        pManager.AddIntegerParameter("Port", "Port", "Loopback TCP port to listen on (127.0.0.1 only)", GH_ParamAccess.item, DefaultPort);
    }

    protected override void RegisterOutputParams(GH_OutputParamManager pManager)
    {
        pManager.AddTextParameter("Status", "Status", "Listener status", GH_ParamAccess.item);
        pManager.AddTextParameter("LastCommand", "LastCommand", "Most recently served bridge command", GH_ParamAccess.item);
    }

    protected override void SolveInstance(IGH_DataAccess da)
    {
        var run = false;
        var port = DefaultPort;

        da.GetData(0, ref run);
        da.GetData(1, ref port);

        if (!run)
        {
            StopListener();
            _status = "Idle";
        }
        else
        {
            var requestKey = CanvasListenerRequestKey.Build(run, port);

            // _acceptLoopTask.IsCompleted repairs a loop that died without a
            // deliberate Stop() (e.g. OS socket teardown) -- otherwise the
            // component would report "Listening" forever with nothing bound (WR-06).
            if (_acceptLoopTask is null
                || _acceptLoopTask.IsCompleted
                || !string.Equals(_activeRequestKey, requestKey, StringComparison.Ordinal))
            {
                StartListener(port, requestKey);
            }
        }

        da.SetData(0, _status);
        da.SetData(1, _lastCommand);
    }

    public override void RemovedFromDocument(GH_Document document)
    {
        StopListener();
        base.RemovedFromDocument(document);
    }

    /// <summary>
    /// RemovedFromDocument is NOT raised when the user closes the .gh file, so
    /// without this override a running listener would keep port 8720 bound (and
    /// keep serving a dead document) for the rest of the Rhino session (WR-01).
    /// Note that Unloaded also fires on every document *tab switch*, not just
    /// close, so the Loaded branch below schedules a re-solve: SolveInstance
    /// then restarts the listener (Run=true sees a null accept-loop task) and
    /// the Status output stops showing a stale "Listening ..." value.
    /// </summary>
    public override void DocumentContextChanged(GH_Document document, GH_DocumentContext context)
    {
        if (context == GH_DocumentContext.Close || context == GH_DocumentContext.Unloaded)
        {
            StopListener();
            _status = "Idle";
        }
        else if (context == GH_DocumentContext.Loaded)
        {
            // Re-activating a tab does not trigger a solve on its own, so the
            // listener stopped by the matching Unloaded would silently stay dead
            // while the Status output kept claiming "Listening" (iter-3 WR-01).
            ScheduleRefresh();
        }

        base.DocumentContextChanged(document, context);
    }

    private CanvasCommandDispatcher BuildDispatcher()
    {
        var handlers = new Dictionary<string, Func<CanvasCommandRequest, object?>>
        {
            [CanvasBridgeCommands.GetCanvasContext] = HandleGetCanvasContext,
            [CanvasBridgeCommands.GetSelection] = HandleGetSelection,
            [CanvasBridgeCommands.GetDocumentIdentity] = HandleGetDocumentIdentity,
            [CanvasBridgeCommands.PreviewStructure] = HandlePreviewStructure,
            [CanvasBridgeCommands.ClearPreview] = HandleClearPreview,
            [CanvasBridgeCommands.GetPreviewStatus] = HandleGetPreviewStatus,
            [CanvasBridgeCommands.FocusComponent] = HandleFocusComponent,
            [CanvasBridgeCommands.StartMapping] = HandleStartMapping,
            [CanvasBridgeCommands.GetMappingStatus] = HandleGetMappingStatus,
            [CanvasBridgeCommands.PlacePropertyScript] = HandlePlacePropertyScript,
            [CanvasBridgeCommands.RunPropertyCheck] = HandleRunPropertyCheck,
            [CanvasBridgeCommands.GetPropertyCheckStatus] = HandleGetPropertyCheckStatus,
            [CanvasBridgeCommands.GetPropertyCheckContext] = HandleGetPropertyCheckContext,
        };

        return new CanvasCommandDispatcher(handlers);
    }

    private object? HandleGetCanvasContext(CanvasCommandRequest request)
    {
        return InvokeOnCanvas(() =>
        {
            var project = request.TryGetString("project");
            var contextJson = CanvasContextExtractor.SerializeContext(OnPingDocument(), project);
            return (object?)System.Text.Json.Nodes.JsonNode.Parse(contextJson);
        });
    }

    private object? HandleGetSelection(CanvasCommandRequest request)
    {
        return InvokeOnCanvas(() => (object?)new { selection = ReadSelectedGuids() });
    }

    /// <summary>
    /// Read-only (Phase 1301 D-13): identity of the GH document this listener serves.
    /// FilePath is null for an unsaved document. Runs on the UI thread via
    /// <see cref="InvokeOnCanvas"/>; mutates nothing.
    /// </summary>
    private object? HandleGetDocumentIdentity(CanvasCommandRequest request)
    {
        return InvokeOnCanvas(() =>
        {
            var doc = OnPingDocument();
            if (doc is null)
            {
                throw new InvalidOperationException("No active document.");
            }

            var path = doc.FilePath;
            return (object?)new CanvasDocumentIdentity(
                doc.DocumentID.ToString(),
                string.IsNullOrWhiteSpace(path) ? null : path,
                doc.DisplayName,
                doc.IsModified,
                DateTimeOffset.UtcNow);
        });
    }

    /// <summary>
    /// Plan 1303-10: show one canvas object (a mapping proposal row clicked in DeGram). Brings the
    /// Grasshopper editor to the front, selects the object's top-level component and centres and zooms
    /// the canvas on it. The definition itself is not changed.
    /// </summary>
    private object? HandleFocusComponent(CanvasCommandRequest request)
    {
        var id = request.TryGetString("componentId") ?? string.Empty;
        if (!Guid.TryParseExact(id, "N", out var guid) && !Guid.TryParse(id, out guid))
        {
            throw new ArgumentException("componentId must be a Grasshopper InstanceGuid.");
        }

        return InvokeOnCanvas(() =>
        {
            var doc = OnPingDocument() ?? throw new InvalidOperationException("No active document.");
            var obj = doc.FindObject(guid, false);
            var top = obj?.Attributes?.GetTopLevel;
            if (obj is null || top?.DocObject is null)
            {
                return (object?)new { found = false, componentId = id };
            }

            var editor = global::Grasshopper.Instances.DocumentEditor;
            if (editor is not null)
            {
                if (editor.WindowState == FormWindowState.Minimized)
                {
                    editor.WindowState = FormWindowState.Normal;
                }

                editor.Show();
                editor.TopMost = true; // Windows lets a background process raise its window only this way
                editor.TopMost = false;
                editor.Activate();
            }

            var canvas = global::Grasshopper.Instances.ActiveCanvas;
            if (canvas is not null && !ReferenceEquals(canvas.Document, doc))
            {
                canvas.Document = doc;
            }

            foreach (var other in doc.Objects)
            {
                if (other.Attributes is { Selected: true } && !ReferenceEquals(other, top.DocObject))
                {
                    other.Attributes.Selected = false;
                }
            }

            top.Selected = true;
            if (canvas is not null)
            {
                var b = top.Bounds;
                var zoom = Math.Min(canvas.Width / (b.Width + 400f), canvas.Height / (b.Height + 300f));
                canvas.Viewport.Zoom = Math.Max(0.4f, Math.Min(1.6f, zoom));
                canvas.Viewport.MidPoint = new PointF(b.X + b.Width / 2f, b.Y + b.Height / 2f);
                canvas.Refresh();
            }

            return (object?)new { found = true, componentId = id, name = top.DocObject.NickName };
        });
    }

    /// <summary>Plan 1303-10 (DeGram «Запустить меппинг»): CONNECTOR reads the canvas and creates a session now.</summary>
    private object? HandleStartMapping(CanvasCommandRequest request)
    {
        return InvokeOnCanvas(() =>
        {
            var doc = OnPingDocument() ?? throw new InvalidOperationException("No active document.");
            var connector = doc.Objects.OfType<ConnectorComponent>().FirstOrDefault();
            if (connector is null)
            {
                return (object?)new { started = false, message = "No CONNECTOR on this canvas." };
            }

            var mapping = connector.Mapping;
            if (mapping is null)
            {
                return (object?)new { started = false, message = "Sign in on CONNECTOR (AutoMap on) to map this definition." };
            }

            var (started, message) = mapping.StartNow();
            return (object?)new { started, message };
        });
    }

    /// <summary>Plan 1303-10: what DeGram needs to find this definition's mapping session.</summary>
    private object? HandleGetMappingStatus(CanvasCommandRequest request)
    {
        return InvokeOnCanvas(() =>
        {
            var doc = OnPingDocument() ?? throw new InvalidOperationException("No active document.");
            var connector = doc.Objects.OfType<ConnectorComponent>().FirstOrDefault();
            var mapping = connector?.Mapping;
            return (object?)new
            {
                document = DG.Grasshopper.Mapping.MappingCanvasReader.DocumentKey(doc),
                connector = connector is not null,
                signedIn = mapping?.Enabled ?? false,
                sessionId = mapping?.SessionId,
                message = mapping?.Status ?? (connector is null ? "No CONNECTOR on this canvas." : "Sign in on CONNECTOR."),
            };
        });
    }

    private List<string> ReadSelectedGuids()
    {
        var doc = OnPingDocument();
        var result = new List<string>();

        if (doc is null)
        {
            return result;
        }

        foreach (var obj in doc.Objects)
        {
            if (obj.Attributes is { Selected: true })
            {
                result.Add(obj.InstanceGuid.ToString());
            }
        }

        return result;
    }

    /// <summary>
    /// Runs <paramref name="work"/> on Rhino's UI thread and blocks the calling
    /// (background) thread until it completes. The socket write must NEVER happen
    /// inside this delegate -- only canvas reads (33-RESEARCH.md Pitfall 1).
    /// The wait is bounded by <see cref="CanvasBridgeProtocol.CanvasUiTimeoutMs"/>: on expiry
    /// <see cref="CanvasUiWait.Await{T}"/> throws <see cref="CanvasBusyException"/>, which the
    /// dispatcher reports as a BUSY error envelope instead of hanging the accept loop (D-18).
    /// </summary>
    private static object? InvokeOnCanvas(Func<object?> work)
    {
        var tcs = new TaskCompletionSource<object?>(TaskCreationOptions.RunContinuationsAsynchronously);

        RhinoApp.InvokeOnUiThread(new Action(() =>
        {
            try
            {
                tcs.SetResult(work());
            }
            catch (Exception ex)
            {
                tcs.SetException(ex);
            }
        }));

        return CanvasUiWait.Await(tcs.Task);
    }

    /// <summary>
    /// Runs <paramref name="work"/> on Rhino's UI thread with the live document and blocks
    /// the calling (background accept-loop) thread until it completes -- the write
    /// counterpart to <see cref="InvokeOnCanvas"/>. Per this plan's locked decision
    /// (35-PLAN.md plan_decisions #2), the delegate mutates <see cref="GH_Document"/>
    /// directly on the UI thread rather than via <c>ScheduleSolution</c>: the bridge
    /// command does not run inside another component's <c>SolveInstance</c>, so there is
    /// no in-progress solution to defer around. After <paramref name="work"/> returns,
    /// <see cref="Grasshopper.Instances.InvalidateCanvas"/> forces the redraw before the
    /// <see cref="TaskCompletionSource{TResult}"/> resolves, so the TCP response is sent
    /// only after the preview objects genuinely exist on canvas. A null document (no
    /// active canvas) resolves to a structured "no document" result instead of invoking
    /// <paramref name="work"/> with null; any exception raised by <paramref name="work"/>
    /// itself is captured on the task, mirroring <see cref="InvokeOnCanvas"/>.
    /// A timeout reports BUSY without retry; the UI delegate is not cancelled and may still
    /// run later, so a client must re-read state before assuming the write did not happen.
    /// </summary>
    private object? InvokeOnCanvasWrite(Func<GH_Document, object?> work)
    {
        var tcs = new TaskCompletionSource<object?>(TaskCreationOptions.RunContinuationsAsynchronously);

        RhinoApp.InvokeOnUiThread(new Action(() =>
        {
            try
            {
                var doc = OnPingDocument();
                if (doc is null)
                {
                    tcs.SetResult((object?)new { ok = false, message = "No active document." });
                    return;
                }

                var result = work(doc);
                global::Grasshopper.Instances.InvalidateCanvas();
                tcs.SetResult(result);
            }
            catch (Exception ex)
            {
                tcs.SetException(ex);
            }
        }));

        return CanvasUiWait.Await(tcs.Task);
    }

    private object? HandleGetPreviewStatus(CanvasCommandRequest request)
    {
        return InvokeOnCanvas(() =>
        {
            var doc = OnPingDocument();
            var pending = PreviewRegistry.Pending.Select(e => new
            {
                proposalId = e.ProposalId,
                kind = e.Kind.ToString(),
                suggestedName = e.SuggestedName,
                confidence = e.Confidence,
                memberCount = doc?.Objects.OfType<GH_Group>()
                    .FirstOrDefault(g => g.InstanceGuid == e.GroupGuid)?.ObjectIDs.Count ?? 0,
            }).ToList();

            return (object?)new { pending };
        });
    }

    /// <summary>
    /// Draws one desaturated, <c>[?] </c>-prefixed <see cref="GH_Group"/> per proposal plus
    /// one text-only scribble legend, all inside a single <see cref="GH_UndoRecord"/>
    /// ("DG structure proposal") so one Ctrl+Z wipes every trace (RCGN-02). Registers the
    /// created groups into <see cref="PreviewRegistry"/> so <c>DG STRUCTURE CONFIRM</c>
    /// (Plan 35-04) can see them.
    /// </summary>
    private object? HandlePreviewStructure(CanvasCommandRequest request)
    {
        var proposals = ParseProposals(request);

        return InvokeOnCanvasWrite(doc =>
        {
            var created = new List<(string proposalId, Guid groupGuid)>();
            var record = new GH_UndoRecord("DG structure proposal");

            // WR-01: proposal ids are synthesized per request (p0, p1, ...), so a second
            // preview_structure call would overwrite the registry entries while the first
            // call's groups (and legend) stayed on canvas -- unreachable by clear_preview
            // and invisible to DG STRUCTURE CONFIRM. Auto-clear the previous preview
            // before rendering the new one.
            //
            // IN-12/F4: the auto-clear shares THIS record, so undoing it re-adds the
            // previous preview's objects. Removing them untracked (as this did before)
            // left the previous render's own record holding GH_AddObjectActions for
            // objects the document no longer owned, so the second Ctrl+Z threw
            // "Undo failed: Object could not be found".
            RemovePendingPreviewObjects(doc, record);

            foreach (var proposal in proposals)
            {
                EntityTagKind kind;
                try
                {
                    kind = proposal.ToEntityTagKind();
                }
                catch (ArgumentOutOfRangeException)
                {
                    // Unknown/unrecognized kind string -- guard-and-continue rather than
                    // aborting the whole preview render over one malformed proposal.
                    continue;
                }

                var group = new GH_Group();
                group.CreateAttributes();
                var confidencePercent = (proposal.Confidence * 100d).ToString("F0", CultureInfo.InvariantCulture);
                group.NickName = $"{CanvasAnnotationStyles.PreviewPrefix}{proposal.SuggestedName} ({confidencePercent}%)";
                group.Colour = CanvasAnnotationStyles.Preview(CanvasAnnotationStyles.ForKind(kind, nested: false));

                foreach (var memberId in proposal.MemberIds)
                {
                    // Guard-and-continue (T-35-08): unparseable/absent member ids are
                    // skipped rather than throwing out of the render.
                    if (Guid.TryParse(memberId, out var memberGuid))
                    {
                        group.AddObject(memberGuid);
                    }
                }

                record.AddAction(new GH_AddObjectAction(group));
                doc.AddObject(group, false);
                created.Add((proposal.ProposalId, group.InstanceGuid));
            }

            var legend = new GH_Scribble();
            legend.CreateAttributes();
            legend.Text = $"[?] {created.Count} proposal(s) pending -- run DG STRUCTURE CONFIRM";
            legend.Font = new Font("Microsoft Sans Serif", 20f, FontStyle.Regular);
            record.AddAction(new GH_AddObjectAction(legend));
            doc.AddObject(legend, false);

            doc.UndoServer.PushUndoRecord(record);

            PreviewRegistry.RegisterAll(created, proposals);
            _previewLegendGuid = legend.InstanceGuid;

            return (object?)new { previewed = created.Count };
        });
    }

    /// <summary>
    /// Removes every currently-pending preview group (via <see cref="PreviewRegistry.Pending"/>)
    /// plus the legend scribble stashed by the last <see cref="HandlePreviewStructure"/> call,
    /// then empties the registry. Wrapped in its own <see cref="GH_UndoRecord"/>
    /// ("DG clear preview") -- see <see cref="RemovePendingPreviewObjects"/> for why an
    /// untracked removal is not safe here (IN-12/F4).
    /// </summary>
    private object? HandleClearPreview(CanvasCommandRequest request)
    {
        return InvokeOnCanvasWrite(doc =>
        {
            var record = new GH_UndoRecord("DG clear preview");
            var removal = RemovePendingPreviewObjects(doc, record);

            if (removal.Objects > 0)
            {
                doc.UndoServer.PushUndoRecord(record);
            }

            return (object?)new { cleared = removal.Groups };
        });
    }

    /// <summary>
    /// Phase 1303-15 (DGOPN-02): places a generated property-checking chain -- the calculator
    /// and highlighter as Rhino 8 Python 3 script components, the DG validation components,
    /// toggles and a panel -- next to the CONNECTOR the user signed in on, wires it as the plan
    /// says and groups it, all inside one <see cref="GH_UndoRecord"/> so one Ctrl+Z removes it.
    /// The plan is parsed and validated in DG.Core (<see cref="PropertyScriptPlacement"/>)
    /// before anything touches the document.
    /// </summary>
    private object? HandlePlacePropertyScript(CanvasCommandRequest request)
    {
        var plan = PropertyScriptPlacement.Parse(request.Parameters);
        foreach (var (name, script) in plan.Scripts)
        {
            if (!string.IsNullOrEmpty(script.Sha256) && !string.Equals(Sha256Hex(script.Source), script.Sha256, StringComparison.OrdinalIgnoreCase))
            {
                throw new InvalidOperationException($"Script '{name}' does not match its sha256.");
            }
        }

        return InvokeOnCanvasWrite(doc =>
        {
            var objects = new Dictionary<string, IGH_DocumentObject>(StringComparer.Ordinal);
            var reused = new List<string>();
            foreach (var c in plan.Components.Where(c => c.Reuse))
            {
                var guid = PropertyScriptPlacement.DgComponentTypes[c.Type];
                var existing = doc.Objects.FirstOrDefault(o => o.ComponentGuid == guid);
                if (existing is not null)
                {
                    objects[c.Key] = existing;
                    reused.Add(c.Key);
                }
                else if (c.Required)
                {
                    throw new InvalidOperationException($"Place {c.Type} on the canvas and sign in first.");
                }
            }

            var anchor = objects.Values.FirstOrDefault()?.Attributes.Pivot ?? new PointF(0, 0);
            var origin = new PointF(anchor.X + 450, anchor.Y);
            var record = new GH_UndoRecord("DG property check");

            // Regenerating replaces the project's previous chain (new rules, new calculators) in the same undo record.
            var replaced = 0;
            foreach (var oldGroup in PropertyCheckGroups(doc, plan.Group).ToList())
            {
                foreach (var member in GroupMembers(doc, oldGroup).Where(m => !objects.Values.Contains(m)).ToList())
                {
                    record.AddAction(new GH_RemoveObjectAction(member));
                    doc.RemoveObject(member, false);
                    replaced++;
                }

                record.AddAction(new GH_RemoveObjectAction(oldGroup));
                doc.RemoveObject(oldGroup, false);
            }
            var created = new List<IGH_DocumentObject>();
            foreach (var c in plan.Components.Where(c => !objects.ContainsKey(c.Key)))
            {
                IGH_DocumentObject obj = c.Kind switch
                {
                    "dg" => global::Grasshopper.Instances.ComponentServer.EmitObject(PropertyScriptPlacement.DgComponentTypes[c.Type])
                        ?? throw new InvalidOperationException($"DG component {c.Type} is not loaded."),
                    "script" => CreateScriptComponent(plan.Scripts[c.Script]),
                    "toggle" => new GH_BooleanToggle { Value = c.Value },
                    "panel" => new GH_Panel { UserText = c.Text },
                    _ => throw new InvalidOperationException($"Unknown component kind {c.Kind}."),
                };
                obj.CreateAttributes();
                if (!string.IsNullOrEmpty(c.NickName))
                {
                    obj.NickName = c.NickName;
                }

                obj.Attributes.Pivot = new PointF(origin.X + c.X, origin.Y + c.Y);
                doc.AddObject(obj, false);
                record.AddAction(new GH_AddObjectAction(obj));
                objects[c.Key] = obj;
                created.Add(obj);
            }

            var warnings = new List<string>();
            var wired = 0;
            foreach (var wire in plan.Wires)
            {
                var source = ResolvePort(objects[wire.From.Key], wire.From.Port, output: true);
                var target = ResolvePort(objects[wire.To.Key], wire.To.Port, output: false);
                if (source is null || target is null)
                {
                    warnings.Add($"wire {wire.From} -> {wire.To}: port not found");
                    continue;
                }

                if (target.Sources.Contains(source) && target.Sources.Count == 1)
                {
                    continue;
                }

                record.AddAction(new GH_WireAction(target));
                // An input of a reused canvas component (METAGRAPH) gets exactly the plan's source: a stale wire from
                // an earlier plan (CONNECTOR.Database straight into METAGRAPH, live 2026-10-20) is removed.
                if (reused.Contains(wire.To.Key))
                {
                    target.RemoveAllSources();
                }

                if (!target.Sources.Contains(source))
                {
                    target.AddSource(source);
                }

                wired++;
            }

            var group = new GH_Group();
            group.CreateAttributes();
            group.NickName = string.IsNullOrEmpty(plan.Group) ? "DG property check" : plan.Group;
            group.Colour = Color.FromArgb(60, 22, 163, 74);
            foreach (var obj in created)
            {
                group.AddObject(obj.InstanceGuid);
            }

            doc.AddObject(group, false);
            record.AddAction(new GH_AddObjectAction(group));
            doc.UndoServer.PushUndoRecord(record);
            doc.ScheduleSolution(10);

            return (object?)new
            {
                placed = objects.ToDictionary(kv => kv.Key, kv => kv.Value.InstanceGuid.ToString()),
                reused,
                created = created.Count,
                replaced,
                wires = wired,
                warnings,
                groupId = group.InstanceGuid.ToString(),
            };
        });
    }

    private const string PropertyCheckGroupPrefix = "DG · Проверка свойств";
    private const string CalculatorNickName = "DG PROPERTY CALCULATOR";
    private const string HighlighterNickName = "DG VALIDATION HIGHLIGHTER";
    private GH_Document? _solutionCounterDoc;
    private long _solutionsEnded;

    private static IEnumerable<GH_Group> PropertyCheckGroups(GH_Document doc, string groupName) =>
        doc.Objects.OfType<GH_Group>().Where(g => string.IsNullOrEmpty(groupName)
            ? g.NickName.StartsWith(PropertyCheckGroupPrefix, StringComparison.Ordinal)
            : string.Equals(g.NickName, groupName, StringComparison.Ordinal));

    private static List<IGH_DocumentObject> GroupMembers(GH_Document doc, GH_Group group) =>
        group.ObjectIDs.Select(id => doc.FindObject(id, true)).Where(o => o is not null).Select(o => o!).ToList();

    private static List<IGH_DocumentObject>? PropertyCheckMembers(GH_Document doc, string project)
    {
        var groups = PropertyCheckGroups(doc, string.Empty)
            .Where(g => string.IsNullOrEmpty(project) || g.NickName.Contains($"({project})", StringComparison.Ordinal))
            .ToList();
        return groups.Count == 0 ? null : groups.SelectMany(g => GroupMembers(doc, g)).ToList();
    }

    private static bool BoolParam(CanvasCommandRequest request, string key, bool fallback) =>
        request.Parameters.ValueKind == JsonValueKind.Object && request.Parameters.TryGetProperty(key, out var v)
            ? v.ValueKind == JsonValueKind.True || (v.ValueKind != JsonValueKind.False && fallback)
            : fallback;

    /// <summary>
    /// Sets the Run / Paint / Clear / SendValid toggles of the placed check, expires the calculator so it re-reads the
    /// live Revit model (a new Design State), schedules a solution and waits up to 25 s for it to finish. A longer
    /// solution answers <c>finished = false</c>; <c>get_property_check_status</c> reads the result later.
    /// </summary>
    private object? HandleRunPropertyCheck(CanvasCommandRequest request)
    {
        var project = request.TryGetString("project");
        var clear = BoolParam(request, "clear", false);
        var paint = BoolParam(request, "paint", true) && !clear;
        var send = BoolParam(request, "send", false);
        long before = 0;

        InvokeOnCanvasWrite(doc =>
        {
            var members = PropertyCheckMembers(doc, project)
                ?? throw new InvalidOperationException("No DG property check on this canvas: generate it first.");
            if (!ReferenceEquals(_solutionCounterDoc, doc))
            {
                if (_solutionCounterDoc is not null)
                {
                    _solutionCounterDoc.SolutionEnd -= OnPropertyCheckSolutionEnd;
                }

                doc.SolutionEnd += OnPropertyCheckSolutionEnd;
                _solutionCounterDoc = doc;
            }

            before = Interlocked.Read(ref _solutionsEnded);
            foreach (var toggle in members.OfType<GH_BooleanToggle>())
            {
                bool? value = toggle.NickName switch
                {
                    "Run" => true,
                    "Paint" => paint,
                    "Clear" => clear,
                    "SendValid" => send,
                    _ => null,
                };
                if (value is { } v && toggle.Value != v)
                {
                    toggle.Value = v;
                    toggle.ExpireSolution(false);
                }
            }

            foreach (var calculator in members.OfType<IGH_Component>().Where(c => c.NickName == CalculatorNickName || c.NickName == HighlighterNickName))
            {
                calculator.ExpireSolution(false);
            }

            doc.ScheduleSolution(5);
            return null;
        });

        var deadline = DateTime.UtcNow.AddSeconds(25);
        var finished = false;
        while (DateTime.UtcNow < deadline)
        {
            Thread.Sleep(400);
            if (Interlocked.Read(ref _solutionsEnded) > before)
            {
                finished = true;
                break;
            }
        }

        var status = HandleGetPropertyCheckStatus(request);
        return new { finished, paint, clear, send, status };
    }

    private void OnPropertyCheckSolutionEnd(object sender, GH_SolutionEventArgs e) => Interlocked.Increment(ref _solutionsEnded);

    /// <summary>
    /// Phase 1303-15 (owner 2026-10-21: walls, columns and beams are checked against but were not in the Model Viewer):
    /// the calculator's Context / ContextLabels outputs serialized as validation geometry (meshes in model units).
    /// </summary>
    private object? HandleGetPropertyCheckContext(CanvasCommandRequest request)
    {
        var project = request.TryGetString("project");
        return InvokeOnCanvas(() =>
        {
            var doc = OnPingDocument() ?? throw new InvalidOperationException("No active document.");
            var members = PropertyCheckMembers(doc, project)
                ?? throw new InvalidOperationException("No DG property check on this canvas: generate it first.");
            var calculator = members.OfType<IGH_Component>().FirstOrDefault(c => c.NickName == CalculatorNickName)
                ?? throw new InvalidOperationException("The property check has no calculator.");
            var geometry = calculator.Params.Output.FirstOrDefault(p => p.Name == "Context")?.VolatileData.AllData(true).ToList()
                ?? new List<global::Grasshopper.Kernel.Types.IGH_Goo>();
            var labels = calculator.Params.Output.FirstOrDefault(p => p.Name == "ContextLabels")?.VolatileData.AllData(true)
                .Select(g => g?.ToString() ?? string.Empty).ToList() ?? new List<string>();
            var elements = new List<object>();
            for (var i = 0; i < geometry.Count; i++)
            {
                var payload = DG.Grasshopper.Validation.ValidationGeometryPayloadSerializer.Serialize(geometry[i]?.ScriptVariable());
                if (payload is null)
                {
                    continue;
                }

                elements.Add(new
                {
                    label = i < labels.Count ? labels[i] : $"context {i}",
                    geometry = new
                    {
                        units = payload.Units,
                        items = payload.Items.Select(it => new { kind = it.Kind, vertices = it.Vertices, faces = it.Faces }),
                    },
                });
            }

            return (object?)new { count = elements.Count, skipped = geometry.Count - elements.Count, elements };
        });
    }

    private object? HandleGetPropertyCheckStatus(CanvasCommandRequest request)
    {
        var project = request.TryGetString("project");
        return InvokeOnCanvas(() =>
        {
            var doc = OnPingDocument() ?? throw new InvalidOperationException("No active document.");
            var members = PropertyCheckMembers(doc, project)
                ?? throw new InvalidOperationException("No DG property check on this canvas: generate it first.");
            var components = members.OfType<IGH_Component>().ToList();
            // The chain reuses the canvas CONNECTOR and METAGRAPH (not group members); their state decides whether
            // VALIDATOR gets rules and a publish token, so it is reported too. CONNECTOR keeps sign-in details off
            // its runtime messages by design, so only its message line and remarks/warnings/errors are read.
            var upstream = doc.Objects.OfType<IGH_Component>()
                .Where(c => c.ComponentGuid == PropertyScriptPlacement.DgComponentTypes["CONNECTOR"]
                            || c.ComponentGuid == PropertyScriptPlacement.DgComponentTypes["METAGRAPH"])
                .Where(c => !components.Contains(c))
                .ToList();
            var upstreamState = upstream.Select(c => new
            {
                component = c.NickName,
                message = c.Message,
                errors = c.RuntimeMessages(GH_RuntimeMessageLevel.Error).ToArray(),
                warnings = c.RuntimeMessages(GH_RuntimeMessageLevel.Warning).ToArray(),
                remarks = c.RuntimeMessages(GH_RuntimeMessageLevel.Remark).ToArray(),
                graphConnected = (c as ConnectorComponent)?.IsGraphConnected,
                connectionStatus = (c as ConnectorComponent)?.ConnectionStatus,
            }).ToList();
            components.AddRange(upstream);

            static string[] Output(IGH_Component? c, string name) =>
                c?.Params.Output.FirstOrDefault(p => p.Name == name)?.VolatileData.AllData(true)
                    .Select(g => g?.ToString() ?? string.Empty).ToArray() ?? Array.Empty<string>();

            var calculator = components.FirstOrDefault(c => c.NickName == CalculatorNickName);
            var highlighter = components.FirstOrDefault(c => c.NickName == HighlighterNickName);
            var validator = components.FirstOrDefault(c => c.ComponentGuid == PropertyScriptPlacement.DgComponentTypes["VALIDATOR"]);
            var messages = components.SelectMany(c =>
                c.RuntimeMessages(GH_RuntimeMessageLevel.Error).Select(m => $"error {c.NickName}: {m}")
                    .Concat(c.RuntimeMessages(GH_RuntimeMessageLevel.Warning).Select(m => $"warning {c.NickName}: {m}")))
                .ToList();
            var toggles = members.OfType<GH_BooleanToggle>().GroupBy(t => t.NickName).ToDictionary(g => g.Key, g => g.First().Value);

            // sha256 of the calculator source on the canvas (LF-normalized): data-service compares it with the script it
            // would generate now and re-places the chain only when the rules' properties changed.
            string? calculatorSha256 = null;
            var tryGetSource = calculator?.GetType().GetMethod("TryGetSource");
            var sourceArgs = new object?[] { null };
            if (tryGetSource is not null && tryGetSource.Invoke(calculator, sourceArgs) is true && sourceArgs[0] is string placedSource)
            {
                calculatorSha256 = Sha256Hex(placedSource.Replace("\r\n", "\n"));
            }

            return (object?)new
            {
                calculatorSha256,
                toggles,
                boxes = Output(calculator, "UniqueIds").Length,
                calculatorReport = Output(calculator, "Report"),
                calculatorOut = Output(calculator, "out"),
                validatorReport = Output(validator, "Report"),
                validStatus = Output(validator, "ValidStatus"),
                ruleNames = Output(validator, "RuleName"),
                validationRunId = Output(validator, "ValidationRunId"),
                highlighterReport = Output(highlighter, "Report"),
                highlighterOut = Output(highlighter, "out"),
                violations = Output(highlighter, "Violations"),
                rulesLoaded = Output(upstream.FirstOrDefault(c => c.NickName == "METAGRAPH"), "Count").FirstOrDefault(),
#if NETFRAMEWORK
                assemblyResolver = NetFrameworkAssemblyResolver.Diagnostics(),
#endif
                upstream = upstreamState,
                messages,
            };
        });
    }

    /// <summary>
    /// A Rhino 8 Python 3 script component with exactly the plan's inputs and outputs (plus the
    /// standard <c>out</c> output) and the generated source. Uses the public variable-parameter
    /// API and <c>SetSource(string)</c> of RhinoCodePluginGH's script component, verified live on
    /// Rhino 8.25 (1303-15 spike); reflection keeps DG.gha free of a RhinoCodePluginGH reference.
    /// </summary>
    private static IGH_DocumentObject CreateScriptComponent(ScriptSpec spec)
    {
        var obj = global::Grasshopper.Instances.ComponentServer.EmitObject(PropertyScriptPlacement.Python3ScriptComponent)
            ?? throw new InvalidOperationException("The Rhino 8 Python 3 Script component is not available.");
        if (obj is not IGH_Component comp || obj is not IGH_VariableParameterComponent variable)
        {
            throw new InvalidOperationException("The Python 3 Script component does not support variable parameters.");
        }

        comp.CreateAttributes();
        comp.NickName = string.IsNullOrEmpty(spec.NickName) ? comp.NickName : spec.NickName;
        while (comp.Params.Input.Count > 0)
        {
            comp.Params.UnregisterInputParameter(comp.Params.Input[0], true);
        }

        foreach (var output in comp.Params.Output.Where(p => p.Name != "out").ToList())
        {
            comp.Params.UnregisterOutputParameter(output, true);
        }

        foreach (var port in spec.Inputs)
        {
            var index = comp.Params.Input.Count;
            var param = variable.CreateParameter(GH_ParameterSide.Input, index);
            NameScriptParam(param, port.Name);
            param.Access = port.Access switch
            {
                "list" => GH_ParamAccess.list,
                "tree" => GH_ParamAccess.tree,
                _ => GH_ParamAccess.item,
            };
            param.Optional = true;
            comp.Params.RegisterInputParam(param, index);
        }

        foreach (var name in spec.Outputs)
        {
            var index = comp.Params.Output.Count;
            var param = variable.CreateParameter(GH_ParameterSide.Output, index);
            NameScriptParam(param, name);
            comp.Params.RegisterOutputParam(param, index);
        }

        var setSource = comp.GetType().GetMethod("SetSource", new[] { typeof(string) })
            ?? throw new InvalidOperationException("The Python 3 Script component has no SetSource(string).");
        setSource.Invoke(comp, new object[] { spec.Source });
        variable.VariableParameterMaintenance();
        comp.Params.OnParametersChanged();
        return comp;
    }

    private static void NameScriptParam(IGH_Param param, string name)
    {
        param.Name = name;
        param.NickName = name;
        param.GetType().GetProperty("VariableName")?.SetValue(param, name);
    }

    /// <summary>The parameter a wire end names: toggles and panels are themselves the parameter;
    /// a component port is matched by Name, then NickName.</summary>
    private static IGH_Param? ResolvePort(IGH_DocumentObject obj, string port, bool output)
    {
        if (string.IsNullOrEmpty(port))
        {
            return obj as IGH_Param;
        }

        if (obj is not IGH_Component comp)
        {
            return null;
        }

        var list = output ? comp.Params.Output : comp.Params.Input;
        return list.FirstOrDefault(p => string.Equals(p.Name, port, StringComparison.Ordinal))
            ?? list.FirstOrDefault(p => string.Equals(p.NickName, port, StringComparison.Ordinal));
    }

    private static string Sha256Hex(string text)
    {
        var hash = DG.Core.Compat.DgCompat.Sha256(Encoding.UTF8.GetBytes(text));
        return DG.Core.Compat.DgCompat.ToHex(hash).ToLowerInvariant();
    }

    /// <summary>
    /// Removes every currently-pending preview group (via <see cref="PreviewRegistry.Pending"/>)
    /// plus the legend scribble stashed by the last <see cref="HandlePreviewStructure"/> call
    /// from <paramref name="doc"/>, then empties the registry. Shared by
    /// <see cref="HandleClearPreview"/> and the auto-clear at the top of
    /// <see cref="HandlePreviewStructure"/>'s render (WR-01). Must run inside an
    /// <see cref="InvokeOnCanvasWrite"/> delegate (UI thread).
    /// </summary>
    /// <param name="undoRecord">
    /// Record that receives a <see cref="GH_RemoveObjectAction"/> per removed object.
    /// Never null in practice: the preview objects were added under a live
    /// "DG structure proposal" <see cref="GH_UndoRecord"/> holding a
    /// <see cref="GH_AddObjectAction"/> for each of them, and undoing that record removes
    /// its objects by instance -- so any untracked removal here leaves it pointing at
    /// objects the document no longer owns and Ctrl+Z throws
    /// "Undo failed: Object could not be found" (IN-12/F4).
    /// </param>
    /// <returns>How many preview groups, and how many objects in total, were removed.</returns>
    private PreviewRemoval RemovePendingPreviewObjects(GH_Document doc, GH_UndoRecord undoRecord)
    {
        var groups = 0;
        var objects = 0;

        foreach (var entry in PreviewRegistry.Pending)
        {
            var obj = doc.Objects.FirstOrDefault(o => o.InstanceGuid == entry.GroupGuid);
            if (obj is not null)
            {
                RemoveTracked(doc, obj, undoRecord);
                groups++;
                objects++;
            }
        }

        if (_previewLegendGuid is { } legendGuid)
        {
            var legendObj = doc.Objects.FirstOrDefault(o => o.InstanceGuid == legendGuid);
            if (legendObj is not null)
            {
                RemoveTracked(doc, legendObj, undoRecord);
                objects++;
            }

            _previewLegendGuid = null;
        }

        PreviewRegistry.Clear();

        return new PreviewRemoval(groups, objects);
    }

    /// <summary>
    /// Records the removal on <paramref name="undoRecord"/> BEFORE performing it -- the
    /// action has to capture the object while the document still owns it (same ordering
    /// as <c>StructureConfirmComponent.ApplyToDocument</c>'s reject branch, WR-05).
    /// </summary>
    private static void RemoveTracked(GH_Document doc, IGH_DocumentObject obj, GH_UndoRecord undoRecord)
    {
        undoRecord.AddAction(new GH_RemoveObjectAction(obj));
        doc.RemoveObject(obj, false);
    }

    /// <summary>
    /// Result of <see cref="RemovePendingPreviewObjects"/>: <paramref name="Groups"/> counts
    /// only the preview groups (the number reported to <c>clear_preview</c> callers),
    /// <paramref name="Objects"/> also counts the legend scribble (used to decide whether
    /// there is anything worth pushing an undo record for).
    /// </summary>
    private readonly record struct PreviewRemoval(int Groups, int Objects);

    /// <summary>
    /// Parses the <c>{"proposals":[...]}</c> bridge command parameters (35-PLAN.md
    /// plan_decisions #1 -- <c>unrecognized[]</c> is report-only and never rendered) into
    /// <see cref="ProposalDto"/> records. The wire proposal shape (cg_recognition.py) has no
    /// proposal id of its own, so a stable per-request index-based id (<c>p0</c>, <c>p1</c>,
    /// ...) is synthesized here so <see cref="PreviewRegistry.RegisterAll"/> can zip
    /// (proposalId, groupGuid) pairs against these <see cref="ProposalDto"/>s by id.
    /// Malformed entries are skipped (guard-and-continue), never thrown.
    ///
    /// <para>
    /// Phase 36 UAT F6: <c>provider</c>/<c>model</c> identify the LLM behind the run. One
    /// recognition run resolves ONE provider/model for every proposal it returns
    /// (cg_recognition.recognize_structure), so they are read from the TOP LEVEL of the command
    /// parameters -- the shape `/computgraph/recognize` now returns directly. A per-proposal
    /// <c>provider</c>/<c>model</c> still wins where present, so a caller stitching proposals
    /// from two runs into one preview does not lose either one's provenance.
    /// </para>
    /// </summary>
    private static List<ProposalDto> ParseProposals(CanvasCommandRequest request)
    {
        var result = new List<ProposalDto>();

        if (request.Parameters.ValueKind != JsonValueKind.Object
            || !request.Parameters.TryGetProperty("proposals", out var proposalsElement)
            || proposalsElement.ValueKind != JsonValueKind.Array)
        {
            return result;
        }

        var runProvider = TryGetJsonString(request.Parameters, "provider");
        var runModel = TryGetJsonString(request.Parameters, "model");

        var index = 0;
        foreach (var item in proposalsElement.EnumerateArray())
        {
            if (item.ValueKind != JsonValueKind.Object)
            {
                index++;
                continue;
            }

            var kind = TryGetJsonString(item, "kind");
            var suggestedName = TryGetJsonString(item, "suggestedName");
            var rationale = TryGetJsonString(item, "rationale");

            var provider = TryGetJsonString(item, "provider");
            if (string.IsNullOrEmpty(provider))
            {
                provider = runProvider;
            }

            var model = TryGetJsonString(item, "model");
            if (string.IsNullOrEmpty(model))
            {
                model = runModel;
            }

            var procedureIndex = item.TryGetProperty("procedureIndex", out var procEl)
                && procEl.ValueKind == JsonValueKind.Number
                && procEl.TryGetInt32(out var parsedProcIndex)
                ? parsedProcIndex
                : 0;

            var confidence = item.TryGetProperty("confidence", out var confEl)
                && confEl.ValueKind == JsonValueKind.Number
                && confEl.TryGetDouble(out var parsedConfidence)
                ? parsedConfidence
                : 0d;

            var memberIds = new List<string>();
            if (item.TryGetProperty("memberIds", out var membersEl) && membersEl.ValueKind == JsonValueKind.Array)
            {
                foreach (var member in membersEl.EnumerateArray())
                {
                    if (member.ValueKind == JsonValueKind.String)
                    {
                        var memberId = member.GetString();
                        if (!string.IsNullOrEmpty(memberId))
                        {
                            memberIds.Add(memberId);
                        }
                    }
                }
            }

            result.Add(new ProposalDto(
                $"p{index}",
                kind,
                suggestedName,
                procedureIndex,
                memberIds,
                confidence,
                rationale,
                string.IsNullOrEmpty(provider) ? null : provider,
                string.IsNullOrEmpty(model) ? null : model));
            index++;
        }

        return result;
    }

    private static string TryGetJsonString(JsonElement obj, string key) =>
        obj.TryGetProperty(key, out var value) && value.ValueKind == JsonValueKind.String
            ? value.GetString() ?? string.Empty
            : string.Empty;

    private void StartListener(int port, string requestKey)
    {
        StopListener();

        _activeRequestKey = requestKey;
        _listenerCts = new CancellationTokenSource();

        try
        {
            // Loopback only (T-33-01) -- never IPAddress.Any.
            _listener = new TcpListener(IPAddress.Loopback, port);
            _listener.Start();
            _status = $"Listening on 127.0.0.1:{port}";
        }
        catch (Exception ex)
        {
            _status = $"Failed to start listener: {ex.Message}";
            _listener = null;
            _listenerCts.Dispose();
            _listenerCts = null;
            _activeRequestKey = string.Empty;
            return;
        }

        _acceptLoopTask = RunAcceptLoopAsync(_listener, _listenerCts.Token);
    }

    private void StopListener()
    {
        try
        {
            _listenerCts?.Cancel();
        }
        catch
        {
            // no-op: cancellation is best-effort.
        }

        try
        {
            // Unblocks a pending AcceptTcpClientAsync and frees the port (Pitfall 2).
            _listener?.Stop();
        }
        catch
        {
            // no-op: Stop() is best-effort during teardown.
        }
        finally
        {
            _listenerCts?.Dispose();
            _listenerCts = null;
            _listener = null;
            _acceptLoopTask = null;
            _activeRequestKey = string.Empty;
        }
    }

    private async Task RunAcceptLoopAsync(TcpListener listener, CancellationToken ct)
    {
        while (!ct.IsCancellationRequested)
        {
            TcpClient client;
            try
            {
                client = await listener.AcceptTcpClientAsync(ct).ConfigureAwait(false);
            }
            catch (OperationCanceledException)
            {
                break;
            }
            catch (ObjectDisposedException)
            {
                break;
            }
            catch (SocketException ex)
            {
                // Surface an unexpected socket death (not a deliberate Stop()) so
                // the component does not keep claiming "Listening" while nothing
                // is bound; the next solve sees IsCompleted and restarts (WR-06).
                if (!ct.IsCancellationRequested)
                {
                    _status = $"Stopped: {ex.Message}";
                }

                break;
            }

            try
            {
                // The stuck-client timeout (T-33-03, Pitfall 5) is enforced inside
                // ServeClientAsync via a linked, self-cancelling token per read --
                // Socket.ReceiveTimeout applies only to synchronous reads and would
                // be a no-op against the async ReadLineAsync path used there.
                await ServeClientAsync(client, ct).ConfigureAwait(false);
            }
            catch (OperationCanceledException) when (ct.IsCancellationRequested)
            {
                // Deliberate shutdown (toggle-off / port-change restart) is not a
                // client error -- leave _status alone so this late-running loop
                // cannot overwrite a fresh "Idle"/"Listening" status (WR-03).
                break;
            }
            catch (Exception ex)
            {
                // A single bad client must not kill the accept loop (T-33-02).
                _status = $"Client error: {ex.Message}";
            }
            finally
            {
                client.Dispose();
            }
        }
    }

    private async Task ServeClientAsync(TcpClient client, CancellationToken ct)
    {
        using var stream = client.GetStream();
        var encoding = new UTF8Encoding(encoderShouldEmitUTF8Identifier: false);
        // Bounded ingress (WR-02): StreamReader.ReadLineAsync buffers a newline-less
        // line without bound, so the MaxRequestBytes guard in TryParse would only run
        // after the damage is done. BoundedLineReader aborts the connection once the
        // byte budget is exceeded before a '\n' is seen.
        var reader = new BoundedLineReader(stream, CanvasBridgeProtocol.MaxRequestBytes);
        using var writer = new StreamWriter(stream, encoding) { NewLine = "\n", AutoFlush = true };

        while (!ct.IsCancellationRequested)
        {
            // Bounds a stuck client so the single-client slot is released (T-33-03,
            // Pitfall 5). Socket.ReceiveTimeout does NOT apply to async reads, so the
            // idle timeout is enforced with a linked token that self-cancels instead.
            using var readCts = CancellationTokenSource.CreateLinkedTokenSource(ct);
            readCts.CancelAfter(ClientReceiveTimeoutMs);
            string? line;
            try
            {
                line = await reader.ReadLineAsync(readCts.Token).ConfigureAwait(false);
            }
            catch (OperationCanceledException) when (!ct.IsCancellationRequested)
            {
                break; // idle client timed out -- release the single-client slot
            }

            if (line is null)
            {
                break;
            }

            if (line.Length > 0 && line[0] == (char)0xFEFF)
            {
                line = line[1..];
            }

            if (CanvasBridgeProtocol.TryParse(line, out var parsed))
            {
                _lastCommand = parsed.Type;
            }

            // The dispatcher composes canvas reads (InvokeOnCanvas) internally where
            // applicable; the write below always runs on this background thread.
            var response = _dispatcher.Dispatch(line);

            // Bounded egress (iter-3 WR-02): a client that never reads lets TCP
            // backpressure fill the loopback send buffer, and the token-less
            // WriteLineAsync(string) overload would then block forever -- wedging
            // the single-client slot beyond even toggle-off's reach (T-33-03 on
            // the write side). The linked token makes the write observe both the
            // send window and deliberate shutdown; AutoFlush rides the same call.
            using var writeCts = CancellationTokenSource.CreateLinkedTokenSource(ct);
            writeCts.CancelAfter(ClientReceiveTimeoutMs);
            try
            {
                await writer.WriteLineAsync(response.AsMemory(), writeCts.Token).ConfigureAwait(false);
            }
            catch (OperationCanceledException) when (!ct.IsCancellationRequested)
            {
                break; // client stopped reading -- release the single-client slot
            }

            ScheduleRefresh();
        }
    }

    private void ScheduleRefresh()
    {
        var doc = OnPingDocument();
        doc?.ScheduleSolution(1, _ => ExpireSolution(false));
    }

    /// <summary>
    /// Reads newline-terminated UTF-8 lines from a stream with a hard per-line
    /// byte budget (WR-02). Unlike <see cref="StreamReader.ReadLineAsync()"/>,
    /// which accumulates a newline-less line without bound, this reader throws
    /// <see cref="IOException"/> as soon as the budget is exceeded before a
    /// '\n' is seen, so an abusive client cannot grow Rhino's memory.
    /// </summary>
    private sealed class BoundedLineReader
    {
        private readonly Stream _stream;
        private readonly int _maxLineBytes;
        private readonly byte[] _buffer = new byte[4096];
        private int _start;
        private int _end;

        public BoundedLineReader(Stream stream, int maxLineBytes)
        {
            _stream = stream;
            _maxLineBytes = maxLineBytes;
        }

        /// <summary>Returns the next line (without its terminator) or null on EOF.</summary>
        public async Task<string?> ReadLineAsync(CancellationToken ct)
        {
            using var line = new MemoryStream();

            while (true)
            {
                for (var i = _start; i < _end; i++)
                {
                    if (_buffer[i] == (byte)'\n')
                    {
                        line.Write(_buffer, _start, i - _start);
                        _start = i + 1;
                        return DecodeLine(line);
                    }
                }

                line.Write(_buffer, _start, _end - _start);
                _start = 0;
                _end = 0;

                if (line.Length > _maxLineBytes)
                {
                    throw new IOException(
                        $"Request line exceeds the {_maxLineBytes}-byte bridge budget; closing connection.");
                }

                var read = await _stream.ReadAsync(_buffer.AsMemory(0, _buffer.Length), ct).ConfigureAwait(false);
                if (read == 0)
                {
                    return line.Length == 0 ? null : DecodeLine(line);
                }

                _end = read;
            }
        }

        private static string DecodeLine(MemoryStream line)
        {
            var bytes = line.GetBuffer();
            var length = (int)line.Length;

            // Tolerate CRLF clients the same way StreamReader.ReadLine does.
            if (length > 0 && bytes[length - 1] == (byte)'\r')
            {
                length--;
            }

            return Encoding.UTF8.GetString(bytes, 0, length);
        }
    }
}
#else
namespace DG.Grasshopper.Components;

public sealed class CanvasListenerComponent
{
}
#endif
