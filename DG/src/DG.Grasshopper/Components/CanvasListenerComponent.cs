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
            [CanvasBridgeCommands.PreviewStructure] = HandlePreviewStructure,
            [CanvasBridgeCommands.ClearPreview] = HandleClearPreview,
            [CanvasBridgeCommands.GetPreviewStatus] = HandleGetPreviewStatus,
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

        return tcs.Task.GetAwaiter().GetResult();
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

        return tcs.Task.GetAwaiter().GetResult();
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
    /// then empties the registry. Programmatic removal -- not wrapped in a
    /// <see cref="GH_UndoRecord"/> (the single-undo contract only applies to the render, not
    /// to this explicit clear).
    /// </summary>
    private object? HandleClearPreview(CanvasCommandRequest request)
    {
        return InvokeOnCanvasWrite(doc =>
        {
            var removed = 0;

            foreach (var entry in PreviewRegistry.Pending)
            {
                var obj = doc.Objects.FirstOrDefault(o => o.InstanceGuid == entry.GroupGuid);
                if (obj is not null)
                {
                    doc.RemoveObject(obj, false);
                    removed++;
                }
            }

            if (_previewLegendGuid is { } legendGuid)
            {
                var legendObj = doc.Objects.FirstOrDefault(o => o.InstanceGuid == legendGuid);
                if (legendObj is not null)
                {
                    doc.RemoveObject(legendObj, false);
                }

                _previewLegendGuid = null;
            }

            PreviewRegistry.Clear();

            return (object?)new { cleared = removed };
        });
    }

    /// <summary>
    /// Parses the <c>{"proposals":[...]}</c> bridge command parameters (35-PLAN.md
    /// plan_decisions #1 -- <c>unrecognized[]</c> is report-only and never rendered) into
    /// <see cref="ProposalDto"/> records. The wire proposal shape (cg_recognition.py) has no
    /// proposal id of its own, so a stable per-request index-based id (<c>p0</c>, <c>p1</c>,
    /// ...) is synthesized here so <see cref="PreviewRegistry.RegisterAll"/> can zip
    /// (proposalId, groupGuid) pairs against these <see cref="ProposalDto"/>s by id.
    /// Malformed entries are skipped (guard-and-continue), never thrown.
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

            result.Add(new ProposalDto($"p{index}", kind, suggestedName, procedureIndex, memberIds, confidence, rationale));
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
