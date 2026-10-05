namespace DG.Core.Bridge;

/// <summary>
/// Command-name constants for the DG Canvas Bridge wire protocol (v9.0).
/// This is the explicit allow-list of commands the dispatcher may route —
/// v10 write commands (add_component, connect_components) are deliberately
/// absent and require a code change to become reachable.
/// </summary>
public static class CanvasBridgeCommands
{
    public const string GetCanvasContext = "get_canvas_context";
    public const string GetSelection = "get_selection";
    public const string PreviewStructure = "preview_structure";
    public const string ClearPreview = "clear_preview";
    public const string GetPreviewStatus = "get_preview_status";

    /// <summary>
    /// Phase 1301 D-13: read-only identity of the GH document the listener serves.
    /// </summary>
    public const string GetDocumentIdentity = "get_document_identity";

    public static IReadOnlyList<string> All { get; } = new[]
    {
        GetCanvasContext,
        GetSelection,
        PreviewStructure,
        ClearPreview,
        GetPreviewStatus,
        GetDocumentIdentity,
    };

    /// <summary>
    /// The read-only commands: they never mutate the canvas. This is the
    /// allowlist a DeGram client uses (Phase 1301 D-15: it sends read commands
    /// only); <see cref="PreviewStructure"/> and <see cref="ClearPreview"/> are
    /// mutating and deliberately absent.
    /// </summary>
    public static IReadOnlyList<string> ReadCommands { get; } = new[]
    {
        GetCanvasContext,
        GetSelection,
        GetPreviewStatus,
        GetDocumentIdentity,
    };

    /// <summary>
    /// The three v9.0 preview commands implemented as no-op "not supported" stubs
    /// until Phase 35 fills them in.
    /// </summary>
    public static IReadOnlyList<string> PreviewStubs { get; } = new[]
    {
        PreviewStructure,
        ClearPreview,
        GetPreviewStatus,
    };
}
