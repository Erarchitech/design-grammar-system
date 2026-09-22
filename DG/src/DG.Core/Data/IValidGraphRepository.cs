using DG.Core.Models;

namespace DG.Core.Data;

public sealed class ValidGraphQueryResult
{
    public IReadOnlyList<RunInfo> Runs { get; init; } = Array.Empty<RunInfo>();

    /// <summary>
    /// Legacy, non-authoritative per-run status list. Historically intended as a per-ObjState
    /// Boolean list, but never actually populated that way — see
    /// <see cref="Neo4jValidGraphRepository"/>'s removal of the <c>Enumerable.Repeat</c>
    /// fabrication (D-14). As of this phase, the inner list for each run is the per-RULE
    /// pass/fail sequence <c>Neo4jValidGraphRepository.ParseRulesJson</c> already returns — one
    /// boolean per rule evaluated for that run, not one per object. It is retained
    /// additive-not-breaking (D-13) so existing index-matched <c>Runs[i]</c>/<c>StatusList[i]</c>
    /// consumers keep working, but it must never be treated as a per-object verdict source.
    /// <see cref="IValidGraphRepository.GetPerObjectVerdictsAsync"/> is the canonical per-object
    /// verdict source (D-10). The <c>spec/DATABASE.md</c> contract describing this list as
    /// index-matched to ObjState order is formally retired by this phase's canonical-sort
    /// decision (D-08) — see plan 1202-05 for the spec update.
    /// </summary>
    public IReadOnlyList<IReadOnlyList<bool>> StatusList { get; init; } = Array.Empty<IReadOnlyList<bool>>();
    public IReadOnlyList<DesignState> DesignStates { get; init; } = Array.Empty<DesignState>();
}

public class RunInfo
{
    public string RunId { get; init; } = string.Empty;
    public string Project { get; init; } = string.Empty;
    public DateTimeOffset CapturedAtUtc { get; init; }
    public IReadOnlyList<string> RuleIds { get; init; } = Array.Empty<string>();
    public string? StateId { get; init; }
}

/// <summary>
/// Where a <see cref="PerObjectVerdict"/> was sourced from. Currently the evidence envelope is
/// the only canonical source (D-10); <see cref="Absent"/> marks the degrade case when no
/// envelope could be read (D-11) rather than fabricating a status from a legacy boolean.
/// Deliberately NOT extended with a third member for duplicate-`(ruleId, objectId)`-row
/// detection (CR-01, plan 1202-10): a duplicate-pair verdict is still sourced from the evidence
/// envelope — nothing about its provenance changed — so that condition is carried on
/// <see cref="PerObjectVerdict.HasDuplicateRuleObjectRows"/> /
/// <see cref="PerObjectVerdictResult.CollidingRuleObjectPairs"/> instead. Provenance and row
/// integrity are separate axes.
/// </summary>
public enum VerdictSource
{
    EvidenceEnvelope,
    Absent,
}

/// <summary>
/// A single object's rolled-up canonical verdict, addressed by <see cref="ObjectId"/> — never by
/// list position (D-08 formally retires positional/index-matched verdict matching).
/// </summary>
public sealed class PerObjectVerdict
{
    public string ObjectId { get; init; } = string.Empty;
    public DG.Core.Contracts.EvidenceStatus Status { get; init; }
    public VerdictSource Source { get; init; }

    /// <summary>
    /// CR-01 (<c>1202-REVIEW.md</c>) / <c>spec/EVIDENCE-CONTRACT.md</c> §4: <c>true</c> when at
    /// least one <c>(ruleId, objectId)</c> pair contributing to this object's rollup appeared on
    /// more than one evidence row — a producer-side identity collision, detected rather than
    /// silently absorbed by <see cref="DG.Core.Contracts.StatusRollup.Rollup"/>. Default
    /// <c>false</c> (the non-duplicate case), so every existing object-initializer that does not
    /// set this property keeps its current meaning. A <c>true</c> value does NOT mean degrade —
    /// <see cref="PerObjectVerdictResult.EnvelopePresent"/> is still <c>true</c> and this object's
    /// <see cref="Status"/> is still the complete D-12 shipped-precedence rollup over every
    /// contributing row, duplicates included.
    /// </summary>
    public bool HasDuplicateRuleObjectRows { get; init; }
}

/// <summary>
/// The result of reading a run's per-object verdicts. <see cref="EnvelopePresent"/> distinguishes
/// "recorded but empty" (<c>true</c>, zero rows) from "not recorded" (<c>false</c>, pre-1200 runs
/// or malformed JSON, per D-11) — callers must never infer a verdict in the latter case.
/// </summary>
public sealed class PerObjectVerdictResult
{
    public IReadOnlyList<PerObjectVerdict> Verdicts { get; init; } = Array.Empty<PerObjectVerdict>();
    public bool EnvelopePresent { get; init; }

    /// <summary>
    /// CR-01 (<c>1202-REVIEW.md</c>) / <c>spec/EVIDENCE-CONTRACT.md</c> §4: names every
    /// <c>(ruleId, objectId)</c> pair that appeared on more than one row in this envelope, so a
    /// caller can report which pairs collided without re-walking the raw <c>evidenceEnvelopeJson</c>.
    /// Defaulted to an empty collection, so every existing initializer that does not set this
    /// property keeps its current meaning. Ordered deterministically — ordinal by
    /// <see cref="RuleObjectPair.RuleId"/> then <see cref="RuleObjectPair.ObjectId"/> — so a test
    /// can assert on it without sorting. A non-empty collection does NOT mean the envelope is
    /// absent or malformed: <see cref="EnvelopePresent"/> is still <c>true</c> with a complete,
    /// usable verdict list (not a degrade); absence keeps its D-11 meaning exclusively.
    /// </summary>
    public IReadOnlyList<RuleObjectPair> CollidingRuleObjectPairs { get; init; } = Array.Empty<RuleObjectPair>();
}

/// <summary>
/// A <c>(ruleId, objectId)</c> identity pair — the evidence row addressing key per
/// <c>spec/EVIDENCE-CONTRACT.md</c> §4. Used by <see cref="PerObjectVerdictResult.CollidingRuleObjectPairs"/>
/// to name which pairs appeared on more than one evidence row (CR-01, plan 1202-10).
/// </summary>
public sealed record RuleObjectPair(string RuleId, string ObjectId);

public interface IValidGraphRepository
{
    Task<ValidGraphQueryResult> GetRunsAsync(
        ConnectionInfo connection, CancellationToken cancellationToken = default);

    /// <summary>
    /// Reads the canonical per-object verdicts for one run from its evidence envelope
    /// (<c>evidenceEnvelopeJson</c>) — the 1200 evidence envelope's per-(rule, object) rows are
    /// the canonical per-object verdict source (D-10). <see cref="ValidGraphQueryResult.StatusList"/>
    /// from <see cref="GetRunsAsync"/> is retained but is non-authoritative and must not be used
    /// as a per-object verdict source. When the envelope is absent (pre-1200 runs) or malformed,
    /// this returns <see cref="PerObjectVerdictResult.EnvelopePresent"/> <c>false</c> and an empty
    /// verdict list — every object is then rendered <c>not_evaluated</c> by the caller, with no
    /// fallback inference from any legacy boolean (D-11): a canonical status can never be derived
    /// from <see cref="ValidGraphQueryResult.StatusList"/> or any other boolean, only reported
    /// absent. The returned result also surfaces duplicate <c>(ruleId, objectId)</c> rows (CR-01)
    /// rather than silently merging them -- see <see cref="PerObjectVerdict.HasDuplicateRuleObjectRows"/>
    /// and <see cref="PerObjectVerdictResult.CollidingRuleObjectPairs"/>.
    /// </summary>
    Task<PerObjectVerdictResult> GetPerObjectVerdictsAsync(
        ConnectionInfo connection, string runId, CancellationToken cancellationToken = default);
}
