using System;
using System.Collections.Generic;
using System.Linq;

namespace DG.Core.Contracts;

/// <summary>
/// Constructs an ordered, versioned <see cref="EvidenceEnvelope"/> (spec/EVIDENCE-CONTRACT.md
/// sections 3/4, D-06). Mirrors <c>data-service/evidence_contract.py</c>'s <c>build_envelope</c>
/// row-ordering and roll-up precedence exactly — the two implementations must not diverge, or the
/// C# and Python legs will disagree on the envelope-level status for identical rows and DE-01 will
/// report a false cross-leg divergence.
/// </summary>
public static class EvidenceEnvelopeFactory
{
    public const string ContractVersion = "1.0.0";

    /// <summary>
    /// Builds an <see cref="EvidenceEnvelope"/> with <paramref name="rows"/> sorted ascending by
    /// <see cref="EvidenceRow.ObjectId"/>, ties broken by <see cref="EvidenceRow.RuleId"/>
    /// (ordinal comparison, spec/EVIDENCE-CONTRACT.md section 4). Sets
    /// <see cref="EvidenceEnvelope.ContractVersion"/> and
    /// <see cref="EvidenceEnvelope.CanonicalizationVersion"/> from this class's and
    /// <see cref="CanonicalJsonWriter"/>'s constants respectively, and
    /// <see cref="EvidenceEnvelope.EmittedAt"/> from <see cref="DateTimeOffset.UtcNow"/> rendered
    /// RFC 3339 with a <c>Z</c> suffix. The envelope-level <see cref="EvidenceEnvelope.CanonicalStatus"/>
    /// is derived from <paramref name="rows"/> by the explicit <see cref="StatusRollup.Precedence"/>
    /// chain unless <paramref name="rollUp"/> is supplied, in which case the override is used verbatim.
    /// An empty <paramref name="rows"/> collection yields <see cref="EvidenceStatus.NotEvaluated"/>
    /// when no override is supplied — nothing was evaluated, so this cannot roll up to
    /// <see cref="EvidenceStatus.Passed"/>.
    /// </summary>
    public static EvidenceEnvelope Build(
        string project,
        string definitionId,
        string serviceName,
        string serviceVersion,
        string stage,
        IReadOnlyCollection<EvidenceRow> rows,
        EvidenceStatus? rollUp = null,
        string? dgId = null,
        object? sourceRepresentation = null,
        string? inputHash = null,
        string? outputHash = null,
        string? schemaVersion = null,
        string? ontologyVersion = null,
        string? ruleVersion = null,
        string? shapeVersion = null,
        string? provider = null,
        string? model = null,
        List<string>? warnings = null)
    {
        var sortedRows = rows
            .OrderBy(r => r.ObjectId, StringComparer.Ordinal)
            .ThenBy(r => r.RuleId, StringComparer.Ordinal)
            .ToList();

        var envelopeStatus = rollUp ?? RollupStatus(sortedRows);
        var emittedAt = DateTimeOffset.UtcNow.ToString("yyyy-MM-ddTHH:mm:ssZ");

        return new EvidenceEnvelope
        {
            ContractVersion = ContractVersion,
            CanonicalizationVersion = CanonicalJsonWriter.CanonicalizationVersion,
            Project = project,
            DefinitionId = definitionId,
            ServiceName = serviceName,
            ServiceVersion = serviceVersion,
            EmittedAt = emittedAt,
            Stage = stage,
            CanonicalStatus = envelopeStatus,
            Rows = sortedRows,
            DgId = dgId,
            SourceRepresentation = sourceRepresentation,
            InputHash = inputHash,
            OutputHash = outputHash,
            SchemaVersion = schemaVersion,
            OntologyVersion = ontologyVersion,
            RuleVersion = ruleVersion,
            ShapeVersion = shapeVersion,
            Provider = provider,
            Model = model,
            Warnings = warnings,
        };
    }

    /// <summary>
    /// Derives the envelope-level roll-up status from row statuses by delegating to
    /// <see cref="StatusRollup.Rollup"/> — the single shared precedence, never a second copy. An
    /// empty row list rolls up to <see cref="EvidenceStatus.NotEvaluated"/> (matching
    /// <see cref="StatusRollup.Rollup"/>'s empty-input default) — distinct from
    /// <c>data-service/evidence_contract.py</c>'s zero-row default of <c>no_population</c>, because
    /// this factory's own default for "nothing to roll up over" is "nothing was evaluated"; callers
    /// with a genuine rule-level <c>no_population</c> case (zero contributing rows for one
    /// evaluated-but-empty-population rule) should pass the explicit <c>rollUp</c> override.
    /// </summary>
    private static EvidenceStatus RollupStatus(IReadOnlyCollection<EvidenceRow> rows)
    {
        return StatusRollup.Rollup(rows.Select(r => r.CanonicalStatus));
    }

    /// <summary>
    /// One-directional canonical-to-legacy-boolean mapping (spec/EVIDENCE-CONTRACT.md section 5,
    /// D-03/D-04). Returns <c>true</c> only for <see cref="EvidenceStatus.Passed"/>. The reverse
    /// direction (inferring a canonical status from a legacy boolean) is undefined and forbidden —
    /// no method in this class performs it. A legacy <c>false</c> is compatible with seven of the
    /// eight canonical statuses, and guessing which one collapses exactly the distinction this
    /// vocabulary exists to preserve.
    /// </summary>
    public static bool ToLegacyBoolean(EvidenceStatus status) => status == EvidenceStatus.Passed;
}
