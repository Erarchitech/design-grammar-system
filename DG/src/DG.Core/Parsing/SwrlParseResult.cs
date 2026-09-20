using DG.Core.Contracts;

namespace DG.Core.Parsing;

/// <summary>
/// The typed, non-throwing result of <see cref="SwrlRuleParser.TryParse"/>: a rolled-up
/// <see cref="Status"/>, the parsed rule (when any atoms at all could be produced), and the
/// diagnostics collected along the way (Phase 1201, D-01/D-04).
/// </summary>
/// <param name="Status">The rolled-up <see cref="EvidenceStatus"/> for this parse, derived from
/// <see cref="Diagnostics"/> via <see cref="DG.Core.Contracts.StatusRollup.Rollup"/> — this is not a
/// second precedence table.</param>
/// <param name="Rule">The parsed rule, or <c>null</c> only when no atoms at all could be produced
/// (e.g. an empty expression or a duplicate-arrow expression, where parsing could not even begin).</param>
/// <param name="Diagnostics">Every diagnostic collected while parsing, in the order encountered.</param>
public sealed record SwrlParseResult(
    EvidenceStatus Status,
    ParsedSwrlRule? Rule,
    IReadOnlyList<ParseDiagnostic> Diagnostics)
{
    /// <summary>
    /// Builds a <see cref="SwrlParseResult"/> from a (possibly null) parsed rule and its
    /// diagnostics, deriving <see cref="Status"/> via <see cref="StatusRollup.Rollup"/> over the
    /// diagnostics' statuses. An empty diagnostic list with a non-null rule rolls up to
    /// <see cref="EvidenceStatus.Passed"/> — not the empty-input default
    /// <see cref="EvidenceStatus.NotEvaluated"/> that <see cref="StatusRollup.Rollup"/> otherwise
    /// applies to an empty status set, since a rule genuinely was produced. Do not write a second
    /// precedence table here — this factory only decides what to roll up, not how.
    /// </summary>
    public static SwrlParseResult Create(ParsedSwrlRule? rule, IReadOnlyList<ParseDiagnostic> diagnostics)
    {
        var status = diagnostics.Count == 0 && rule is not null
            ? EvidenceStatus.Passed
            : StatusRollup.Rollup(diagnostics.Select(d => d.Status));

        return new SwrlParseResult(status, rule, diagnostics);
    }
}
