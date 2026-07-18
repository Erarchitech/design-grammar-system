namespace DG.Core.Models.Computgraph;

/// <summary>
/// Document root mirroring the cgContextJson v1 envelope. Definition metadata
/// (documentId, fileName, capturedAt) identifies the source GH definition.
/// </summary>
public class CgDefinition
{
    public string DocumentId { get; init; } = string.Empty;

    public string FileName { get; init; } = string.Empty;

    /// <summary>
    /// ISO-8601 string, passed through verbatim so re-serialization is
    /// idempotent -- never re-stamped by the serializer.
    /// </summary>
    public string CapturedAt { get; init; } = string.Empty;
}

/// <summary>
/// A group of untagged (non-conforming) nodes with a raw nickname -- the
/// parser never guesses; anything non-conforming lands here plus a warning.
/// </summary>
public class CgUntaggedGroup
{
    public string Nickname { get; init; } = string.Empty;

    public List<string> MemberIds { get; init; } = new();
}

/// <summary>
/// The untagged set: loose node ids plus untagged groups.
/// </summary>
public class CgUntagged
{
    public List<string> NodeIds { get; init; } = new();

    public List<CgUntaggedGroup> Groups { get; init; } = new();
}

/// <summary>
/// cgContextJson v1 document root -- the in-memory shape every downstream
/// artifact (parser, serializer, extractor, fixture) speaks. Mirrors
/// RESEARCH.md &#167;5's envelope 1:1 so the serializer maps directly.
/// </summary>
public class CgContext
{
    public string SchemaVersion { get; init; } = "cg-context-1";

    public string Project { get; init; } = string.Empty;

    public CgDefinition Definition { get; init; } = new();

    public CgObject? Object { get; init; }

    public List<CgAlgorithm> Algorithms { get; init; } = new();

    public CgUntagged Untagged { get; init; } = new();

    public List<CgNode> Nodes { get; init; } = new();

    public List<CgWire> Wires { get; init; } = new();

    public List<string> Warnings { get; init; } = new();
}
