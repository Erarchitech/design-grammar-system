using System;
using System.Collections.Generic;

namespace DG.Core.Validation;

/// <summary>
/// The D-15 machine-checkable allow-list of SWRL builtins the C# <see cref="RuleEvaluator"/>
/// implements. This is the production-side half of the boundary between the schema-level SWRL atom
/// vocabulary and the bounded evaluator subset actually implemented here; <c>spec/SWRL-SUBSET.md</c>
/// (Phase 1201 plan 04) is the prose counterpart, and a conformance test binds the two together so
/// the document and this list cannot silently drift apart.
/// </summary>
public static class SupportedBuiltins
{
    /// <summary>
    /// The six supported comparison builtins, in their canonical <c>swrlb:</c>-prefixed spelling.
    /// Lookups against this set are case-insensitive (<see cref="IsSupported"/>).
    /// </summary>
    public static readonly IReadOnlySet<string> Names = new HashSet<string>(StringComparer.OrdinalIgnoreCase)
    {
        "swrlb:lessThan",
        "swrlb:greaterThan",
        "swrlb:lessThanOrEqual",
        "swrlb:greaterThanOrEqual",
        "swrlb:equal",
        "swrlb:notEqual",
    };

    /// <summary>
    /// The subset of <see cref="Names"/> that <see cref="RuleEvaluator.EvaluateBuiltin"/> can still
    /// evaluate when its arguments do not convert to <see cref="decimal"/>
    /// (<c>RuleEvaluator.cs</c>'s non-numeric fallback branch). The other four members of
    /// <see cref="Names"/> are numeric-only comparisons and have no non-numeric meaning.
    /// </summary>
    public static readonly IReadOnlySet<string> NonNumericCapableNames = new HashSet<string>(StringComparer.OrdinalIgnoreCase)
    {
        "swrlb:equal",
        "swrlb:notEqual",
    };

    /// <summary>
    /// Returns whether <paramref name="predicateIri"/> is one of the six supported builtins.
    /// Returns <c>false</c> for <c>null</c> or whitespace-only input rather than throwing.
    /// </summary>
    public static bool IsSupported(string? predicateIri)
    {
        return !string.IsNullOrWhiteSpace(predicateIri) && Names.Contains(predicateIri.Trim());
    }
}
