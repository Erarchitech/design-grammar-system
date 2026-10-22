using DG.Core.Models;

namespace DG.Core.Parsing;

/// <summary>
/// Shared classifier for D-61 (Phase 1303 plan 19, requirement DGOPN-06): separates the object a
/// rule checks (the <em>subject</em>) from <em>context-only</em> participants that the rule merely
/// names and relates to the subject. The binder, the evaluator, the failing-binding formatter and
/// the Grasshopper RULE DECONSTRUCT component all consult this one classifier so they cannot
/// disagree about which variables are checked and which are asserted.
/// Design: <c>docs/superpowers/specs/2026-10-21-multi-participant-rule-extraction-design.md</c> §4 and §8a.
/// <para>
/// Definitions (all over the rule's own atoms; nothing is reclassified in
/// <see cref="VariableTypeInferrer"/>):
/// </para>
/// <list type="bullet">
/// <item><b>Subject</b> — the variable at position 1 of the first head atom (the object the rule
/// flags as non-compliant), or <c>null</c> when there is no head atom or that argument is not a
/// variable.</item>
/// <item><b>Context-only variable</b> — not the subject, appears in at least one body atom, appears
/// in no head atom, and every body atom that mentions it is a <c>ClassAtom</c> or an
/// <c>ObjectPropertyAtom</c> (never a <c>DataPropertyAtom</c>, <c>BuiltinAtom</c> or
/// <c>UnsupportedAtom</c>). A rule without a head atom has no subject, so nothing is context-only.</item>
/// <item><b>Context atom</b> — a body <c>ClassAtom</c> whose position-1 variable is context-only, or a
/// body <c>ObjectPropertyAtom</c> with exactly two variable arguments, each the subject or
/// context-only, at least one of them context-only. A context atom is <em>asserted</em> by the rule,
/// never verified.</item>
/// </list>
/// Variable names compare after dropping a leading <c>?</c>, ignoring case, matching
/// <c>RuleEvaluator.TryResolveVariableValue</c>.
/// </summary>
public static class RuleVariableRoles
{
    /// <summary>The variable at position 1 of the first head atom, as written, or null.</summary>
    public static string? SubjectVariable(Rule rule) => Analyze(rule).SubjectVariable;

    /// <summary>True when <paramref name="variableName"/> is a context-only variable of <paramref name="rule"/>.</summary>
    public static bool IsContextOnly(Rule rule, string variableName) => Analyze(rule).IsContextOnly(variableName);

    /// <summary>True when <paramref name="atom"/> (a body atom of <paramref name="rule"/>) is a context atom.</summary>
    public static bool IsContextAtom(Rule rule, Atom atom) => Analyze(rule).IsContextAtom(atom);

    /// <summary>The context atoms of <paramref name="rule"/> in body order.</summary>
    public static IReadOnlyList<Atom> ContextAtoms(Rule rule) => Analyze(rule).ContextAtoms;

    /// <summary>
    /// Classifies <paramref name="rule"/> once. Uses <c>rule.BodyAtoms</c>/<c>rule.HeadAtoms</c>; when
    /// both are empty the SWRL text is parsed with <see cref="SwrlRuleParser.Parse"/> exactly as
    /// <c>RuleEvaluator.EvaluateRule</c> does for the body.
    /// </summary>
    internal static RoleAnalysis Analyze(Rule rule)
    {
        if (rule.BodyAtoms.Count == 0 && rule.HeadAtoms.Count == 0 && !string.IsNullOrWhiteSpace(rule.Swrl))
        {
            var parsed = SwrlRuleParser.Parse(rule.Swrl);
            return Analyze(parsed.BodyAtoms, parsed.HeadAtoms);
        }

        return Analyze(rule.BodyAtoms.ToList(), rule.HeadAtoms.ToList());
    }

    /// <summary>Classifies explicit atom lists, so a caller that already resolved them sees the same atoms.</summary>
    internal static RoleAnalysis Analyze(IReadOnlyList<Atom> bodyAtoms, IReadOnlyList<Atom> headAtoms) =>
        new(bodyAtoms, headAtoms);

    internal static string Normalize(string? variableName)
    {
        if (string.IsNullOrWhiteSpace(variableName))
        {
            return string.Empty;
        }

        var trimmed = variableName.Trim();
        return trimmed.StartsWith("?", StringComparison.Ordinal) ? trimmed[1..] : trimmed;
    }

    internal sealed class RoleAnalysis
    {
        private readonly HashSet<string> _contextOnly = new(StringComparer.OrdinalIgnoreCase);
        private readonly HashSet<Atom> _contextAtoms = new(ReferenceEqualityComparer.Instance);

        internal RoleAnalysis(IReadOnlyList<Atom> bodyAtoms, IReadOnlyList<Atom> headAtoms)
        {
            SubjectVariable = FindSubject(headAtoms);
            var subject = Normalize(SubjectVariable);

            if (subject.Length > 0)
            {
                var headVariables = new HashSet<string>(
                    headAtoms.SelectMany(VariablesOf).Select(Normalize),
                    StringComparer.OrdinalIgnoreCase);

                foreach (var candidate in bodyAtoms.SelectMany(VariablesOf).Select(Normalize).Distinct(StringComparer.OrdinalIgnoreCase))
                {
                    if (candidate.Length == 0
                        || string.Equals(candidate, subject, StringComparison.OrdinalIgnoreCase)
                        || headVariables.Contains(candidate))
                    {
                        continue;
                    }

                    var onlyRelational = bodyAtoms
                        .Where(atom => VariablesOf(atom).Any(v => string.Equals(Normalize(v), candidate, StringComparison.OrdinalIgnoreCase)))
                        .All(atom => IsType(atom, "ClassAtom") || IsType(atom, "ObjectPropertyAtom"));
                    if (onlyRelational)
                    {
                        _contextOnly.Add(candidate);
                    }
                }
            }

            var ordered = new List<Atom>();
            foreach (var atom in bodyAtoms)
            {
                if (IsContextAtom(atom))
                {
                    ordered.Add(atom);
                    _contextAtoms.Add(atom);
                }
            }

            ContextAtoms = ordered;
        }

        internal string? SubjectVariable { get; }

        internal IReadOnlyList<Atom> ContextAtoms { get; }

        internal bool IsContextOnly(string variableName) =>
            _contextOnly.Contains(Normalize(variableName));

        internal bool IsContextAtom(Atom atom)
        {
            if (_contextAtoms.Contains(atom))
            {
                return true;
            }

            if (_contextOnly.Count == 0)
            {
                return false;
            }

            if (IsType(atom, "ClassAtom"))
            {
                var subjectArg = atom.Args.FirstOrDefault(a => a.Pos == 1);
                return subjectArg is { Kind: ArgKind.Variable } && IsContextOnly(subjectArg.Value);
            }

            if (IsType(atom, "ObjectPropertyAtom"))
            {
                if (atom.Args.Count != 2 || atom.Args.Any(a => a.Kind != ArgKind.Variable))
                {
                    return false;
                }

                var subject = Normalize(SubjectVariable);
                var contextCount = 0;
                foreach (var arg in atom.Args)
                {
                    if (IsContextOnly(arg.Value))
                    {
                        contextCount++;
                    }
                    else if (!string.Equals(Normalize(arg.Value), subject, StringComparison.OrdinalIgnoreCase))
                    {
                        return false;
                    }
                }

                return contextCount >= 1;
            }

            return false;
        }

        private static string? FindSubject(IReadOnlyList<Atom> headAtoms)
        {
            if (headAtoms.Count == 0)
            {
                return null;
            }

            var arg = headAtoms[0].Args.FirstOrDefault(a => a.Pos == 1);
            return arg is { Kind: ArgKind.Variable } && !string.IsNullOrWhiteSpace(arg.Value) ? arg.Value : null;
        }

        private static IEnumerable<string> VariablesOf(Atom atom) =>
            atom.Args.Where(a => a.Kind == ArgKind.Variable).Select(a => a.Value);

        private static bool IsType(Atom atom, string type) =>
            atom.Type.Equals(type, StringComparison.OrdinalIgnoreCase);
    }
}
