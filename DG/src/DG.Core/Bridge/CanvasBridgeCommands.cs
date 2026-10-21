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

    /// <summary>
    /// Phase 1303-10 (owner decision 2026-10-18, DeGram has full access to the GH canvas): bring the
    /// Grasshopper editor to the front, select one object by its InstanceGuid and zoom to it.
    /// </summary>
    public const string FocusComponent = "focus_component";

    /// <summary>Phase 1303-10: CONNECTOR reads the canvas and creates a mapping session now.</summary>
    public const string StartMapping = "start_mapping";

    /// <summary>Phase 1303-10: the document key, current mapping session and CONNECTOR mapping status.</summary>
    public const string GetMappingStatus = "get_mapping_status";

    /// <summary>
    /// Phase 1303-15 (DGOPN-02): place a generated property-checking chain (calculator and highlighter
    /// scripts plus the DG validation components) on the canvas under one undo record.
    /// </summary>
    public const string PlacePropertyScript = "place_property_script";

    /// <summary>
    /// Phase 1303-15: run the placed property check (Run/Paint/Clear/SendValid toggles, calculator re-reads the live
    /// model), wait briefly for the solution and return its reports. Lets DeGram or the Web UI run the check.
    /// </summary>
    public const string RunPropertyCheck = "run_property_check";

    /// <summary>Phase 1303-15: the reports, violations and runtime messages of the placed property check (read only).</summary>
    public const string GetPropertyCheckStatus = "get_property_check_status";

    /// <summary>Phase 1303-15: the model context the property check read (walls, columns, beams, doors, windows) as
    /// meshes, so data-service can publish it to the Model Viewer's base model next to the checked elements.</summary>
    public const string GetPropertyCheckContext = "get_property_check_context";

    public static IReadOnlyList<string> All { get; } = new[]
    {
        GetCanvasContext,
        GetSelection,
        PreviewStructure,
        ClearPreview,
        GetPreviewStatus,
        GetDocumentIdentity,
        FocusComponent,
        StartMapping,
        GetMappingStatus,
        PlacePropertyScript,
        RunPropertyCheck,
        GetPropertyCheckStatus,
        GetPropertyCheckContext,
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
