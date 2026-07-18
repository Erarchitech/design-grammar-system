#if GRASSHOPPER_SDK
using System.Net;
using System.Net.Sockets;
using System.Text;
using DG.Core.Bridge;
using DG.Grasshopper.Canvas;
using Grasshopper.Kernel;
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
            if (_acceptLoopTask is null || !string.Equals(_activeRequestKey, requestKey, StringComparison.Ordinal))
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
    /// </summary>
    public override void DocumentContextChanged(GH_Document document, GH_DocumentContext context)
    {
        if (context == GH_DocumentContext.Close || context == GH_DocumentContext.Unloaded)
        {
            StopListener();
            _status = "Idle";
        }

        base.DocumentContextChanged(document, context);
    }

    private CanvasCommandDispatcher BuildDispatcher()
    {
        var handlers = new Dictionary<string, Func<CanvasCommandRequest, object?>>
        {
            [CanvasBridgeCommands.GetCanvasContext] = HandleGetCanvasContext,
            [CanvasBridgeCommands.GetSelection] = HandleGetSelection,
            [CanvasBridgeCommands.PreviewStructure] = _ => CanvasCommandDispatcher.StubResult(CanvasBridgeCommands.PreviewStructure),
            [CanvasBridgeCommands.ClearPreview] = _ => CanvasCommandDispatcher.StubResult(CanvasBridgeCommands.ClearPreview),
            [CanvasBridgeCommands.GetPreviewStatus] = _ => CanvasCommandDispatcher.StubResult(CanvasBridgeCommands.GetPreviewStatus),
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
            catch (SocketException)
            {
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
            await writer.WriteLineAsync(response).ConfigureAwait(false);

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
