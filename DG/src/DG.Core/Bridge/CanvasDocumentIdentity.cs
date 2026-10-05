namespace DG.Core.Bridge;

/// <summary>
/// Payload of the read-only <c>get_document_identity</c> bridge command
/// (Phase 1301 D-13/D-14). Identifies the Grasshopper document the listener
/// serves so a client can pin it and later re-check that the same document is
/// still active. GH-SDK independent: the listener fills it from
/// <c>GH_Document</c>. Serialized camelCase by <see cref="CanvasBridgeProtocol"/>:
/// <c>{documentId, filePath, displayName, isModified, capturedAt}</c>.
/// </summary>
/// <param name="DocumentId">Stable GH document id for the session.</param>
/// <param name="FilePath">Absolute .gh path, or null when the document is unsaved.</param>
/// <param name="DisplayName">GH document display name (file name or "Untitled").</param>
/// <param name="IsModified">True when the document has unsaved changes.</param>
/// <param name="CapturedAt">When the identity was read from the UI thread.</param>
public sealed record CanvasDocumentIdentity(
    string DocumentId,
    string? FilePath,
    string DisplayName,
    bool IsModified,
    DateTimeOffset CapturedAt);
