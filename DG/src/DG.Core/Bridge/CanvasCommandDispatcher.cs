namespace DG.Core.Bridge;

/// <summary>
/// Routes a parsed wire-protocol request line to its handler using an explicit
/// allow-list dictionary supplied by the caller — never reflection. A command
/// name absent from the supplied dictionary is unreachable (UNKNOWN_COMMAND),
/// so v10 write commands (add_component, connect_components) require a
/// deliberate code change to become reachable (33-CONTEXT.md, "table that v10
/// can extend"; 33-RESEARCH.md Security Domain, Elevation-of-Privilege).
/// </summary>
public sealed class CanvasCommandDispatcher
{
    private readonly IReadOnlyDictionary<string, Func<CanvasCommandRequest, object?>> _handlers;

    public CanvasCommandDispatcher(IReadOnlyDictionary<string, Func<CanvasCommandRequest, object?>> handlers)
    {
        _handlers = handlers ?? throw new ArgumentNullException(nameof(handlers));
    }

    /// <summary>
    /// Parses, routes, and invokes a single wire-protocol request line, always
    /// returning a single-line response envelope. Never throws — a malformed
    /// line, an unknown command, or a handler exception all become an error
    /// envelope so a single bad request can never crash the accept loop.
    /// </summary>
    public string Dispatch(string line)
    {
        if (!CanvasBridgeProtocol.TryParse(line, out var request))
        {
            return CanvasBridgeProtocol.BuildError("Malformed request line.", "BAD_REQUEST");
        }

        if (!_handlers.TryGetValue(request.Type, out var handler))
        {
            return CanvasBridgeProtocol.BuildError($"Unknown command: {request.Type}", "UNKNOWN_COMMAND");
        }

        try
        {
            var result = handler(request);
            return CanvasBridgeProtocol.BuildOk(result);
        }
        catch (Exception ex)
        {
            return CanvasBridgeProtocol.BuildError(ex.Message, "HANDLER_ERROR");
        }
    }

    /// <summary>
    /// The shared "not supported in v9.0" payload for the three preview stub
    /// commands (preview_structure, clear_preview, get_preview_status).
    /// </summary>
    public static object StubResult(string command)
    {
        return new
        {
            supported = false,
            command,
            message = "Not supported in v9.0 (Phase 35).",
        };
    }
}
