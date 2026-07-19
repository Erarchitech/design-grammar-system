#if GRASSHOPPER_SDK
using System.Collections.Concurrent;
using DG.Core.Parsing;

namespace DG.Grasshopper.Canvas;

/// <summary>
/// Process-shared, in-memory store of pending LLM-suggested structure proposals (RCGN-03) --
/// the state holder that lets the DG CANVAS LISTENER (writer, after a recognition run) and the
/// on-canvas confirm/reject component (reader/mutator) see the same pending proposals without
/// either component owning the other. Follows the <see cref="CanvasAnnotationStyles"/>
/// internal-static-class idiom, extended with a <see cref="ConcurrentDictionary{TKey,TValue}"/>
/// for mutable shared state -- both writers ultimately run on the GH UI thread (35-RESEARCH.md
/// Pattern 3), but ConcurrentDictionary removes all doubt at zero cost (T-35-07 mitigation).
/// </summary>
internal static class PreviewRegistry
{
    private static readonly ConcurrentDictionary<string, PreviewEntry> _entries = new();

    /// <summary>
    /// Zips <paramref name="created"/> (proposalId -&gt; the GH_Group GUID just created for it)
    /// with the matching <paramref name="proposals"/> by proposal id and inserts one
    /// <see cref="PreviewEntry"/> per pair. A created id with no matching proposal (or vice
    /// versa) is skipped rather than throwing.
    /// </summary>
    public static void RegisterAll(
        IEnumerable<(string proposalId, Guid groupGuid)> created,
        IEnumerable<ProposalDto> proposals)
    {
        ArgumentNullException.ThrowIfNull(created);
        ArgumentNullException.ThrowIfNull(proposals);

        var proposalsById = proposals.ToDictionary(p => p.ProposalId, StringComparer.Ordinal);

        foreach (var (proposalId, groupGuid) in created)
        {
            if (!proposalsById.TryGetValue(proposalId, out var proposal))
            {
                continue;
            }

            var entry = new PreviewEntry(
                proposal.ProposalId,
                groupGuid,
                proposal.ToEntityTagKind(),
                proposal.SuggestedName,
                proposal.ProcedureIndex,
                proposal.Confidence,
                proposal.Rationale);

            _entries[proposalId] = entry;
        }
    }

    /// <summary>Snapshot of all pending entries -- never a live view (T-35-07: no torn reads).</summary>
    public static IReadOnlyCollection<PreviewEntry> Pending => _entries.Values.ToList();

    public static bool TryGet(string proposalId, out PreviewEntry entry) =>
        _entries.TryGetValue(proposalId, out entry!);

    public static void Remove(string proposalId) => _entries.TryRemove(proposalId, out _);

    public static void Clear() => _entries.Clear();
}

/// <summary>
/// A single pending preview: the created (not-yet-confirmed) group's GUID plus the proposal
/// data needed to render/confirm/reject it. <see cref="ProcedureIndex"/> (Plan 35-04 addition)
/// carries the proposal's enclosing NN token forward so <c>DG STRUCTURE CONFIRM</c>'s accept
/// path can re-derive a convention-conformant permanent nickname via
/// <see cref="CanvasAnnotationNameFactory.ForEntity"/>, which requires it for every
/// <see cref="EntityTagKind"/> -- it would otherwise be lost once <see cref="ProposalDto"/> is
/// projected into this record.
/// </summary>
internal sealed record PreviewEntry(
    string ProposalId,
    Guid GroupGuid,
    EntityTagKind Kind,
    string SuggestedName,
    int ProcedureIndex,
    double Confidence,
    string Rationale);

/// <summary>
/// Wire-JSON carrier for one LLM structure proposal (cg_recognition.py's proposal shape) --
/// deserialization target plus the raw-kind-string -&gt; <see cref="EntityTagKind"/> mapping
/// helper so <see cref="PreviewRegistry"/> and its callers never re-implement the mapping.
/// </summary>
internal sealed record ProposalDto(
    string ProposalId,
    string Kind,
    string SuggestedName,
    int ProcedureIndex,
    IReadOnlyList<string> MemberIds,
    double Confidence,
    string Rationale)
{
    /// <summary>
    /// Maps the raw wire <see cref="Kind"/> string (e.g. "Proc", "Pat", "Var", "Const", "Emg",
    /// "IntF" -- case-insensitive) to the typed <see cref="EntityTagKind"/> enum. Throws for an
    /// unrecognized kind rather than guessing (mirrors CanvasAnnotationParser's "never guess").
    /// </summary>
    public EntityTagKind ToEntityTagKind() =>
        Enum.TryParse<EntityTagKind>(Kind, ignoreCase: true, out var parsed)
            ? parsed
            : throw new ArgumentOutOfRangeException(
                nameof(Kind), Kind, "Unknown proposal Kind -- expected one of the EntityTagKind names.");
}
#else
namespace DG.Grasshopper.Canvas;

/// <summary>Stub for builds without the Grasshopper SDK (GRASSHOPPER_SDK undefined).</summary>
internal static class PreviewRegistry
{
}
#endif
