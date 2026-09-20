using System.Globalization;
using DG.Core.Contracts;
using DG.Core.Models;
using DG.Core.Parsing;

namespace DG.Core.Validation;

public sealed class RuleEvaluator
{
    /// <summary>
    /// A single binding's typed outcome (Phase 1201 D-05/D-07/D-08). <see cref="Status"/> is one of
    /// exactly three values here: <see cref="EvidenceStatus.Failed"/> (the body matched — a
    /// violation, per the violation-pattern inversion), <see cref="EvidenceStatus.Passed"/> (the
    /// body did not match — no violation for this binding), or a typed non-verdict
    /// (<see cref="EvidenceStatus.Unsupported"/>, <see cref="EvidenceStatus.Unknown"/>, or
    /// <see cref="EvidenceStatus.Error"/>) when evaluation could not reach a verdict at all. This
    /// replaces the former bool-or-throw shape so an unsupported construct or an unresolvable
    /// binding is a distinct, non-throwing outcome rather than an exception caught and silently
    /// counted as an ordinary rule violation.
    /// </summary>
    private readonly record struct BindingOutcome(EvidenceStatus Status, string? Detail);

    public IReadOnlyList<RuleEvaluationResult> EvaluateRules(
        IReadOnlyList<Rule> rules,
        IReadOnlyList<BindingRow> bindings)
    {
        var results = new List<RuleEvaluationResult>(rules.Count);
        foreach (var rule in rules)
        {
            results.Add(EvaluateRule(rule, bindings));
        }

        return results;
    }

    public RuleEvaluationResult EvaluateRule(Rule rule, IReadOnlyList<BindingRow> bindings)
    {
        if (bindings.Count == 0)
        {
            return new RuleEvaluationResult
            {
                RuleId = rule.Id,
                RuleName = rule.Name,
                RuleDescription = rule.Description,
                Passed = EvidenceEnvelopeFactory.ToLegacyBoolean(EvidenceStatus.NoPopulation),
                Status = EvidenceStatus.NoPopulation,
                Message = "No variable bindings were provided.",
            };
        }

        var bodyAtoms = rule.BodyAtoms.Count > 0
            ? rule.BodyAtoms.ToList()
            : SwrlRuleParser.Parse(rule.Swrl).BodyAtoms;

        var failingBindings = new List<BindingRow>();
        var outcomes = new List<BindingOutcome>(bindings.Count);
        string? unsupportedDetail = null;
        string? firstErrorDetail = null;

        foreach (var binding in bindings)
        {
            BindingOutcome outcome;
            try
            {
                outcome = EvaluateBody(bodyAtoms, binding);
            }
            catch (Exception ex)
            {
                // A genuine unexpected fault (not one of the typed non-verdicts EvaluateBody/
                // EvaluateAtom/EvaluateBuiltin return directly) is surfaced as Error. It still
                // counts as a failing binding below, matching this evaluator's pre-existing
                // behavior for exceptions reaching this catch-all (D-08's narrowing of exactly
                // what can still reach this catch is plan 02's scope, not this tracer slice's).
                outcome = new BindingOutcome(EvidenceStatus.Error, ex.Message);
                firstErrorDetail ??= ex.Message;
            }

            outcomes.Add(outcome);

            if (outcome.Status == EvidenceStatus.Failed || outcome.Status == EvidenceStatus.Error)
            {
                failingBindings.Add(binding);
            }
            else if (outcome.Status == EvidenceStatus.Unsupported && unsupportedDetail is null)
            {
                unsupportedDetail = outcome.Detail;
            }
        }

        var status = StatusRollup.Rollup(outcomes.Select(o => o.Status));
        var passed = EvidenceEnvelopeFactory.ToLegacyBoolean(status);

        var message = status switch
        {
            EvidenceStatus.Error => firstErrorDetail ?? "Rule evaluation encountered an unexpected error.",
            EvidenceStatus.Failed => $"Rule violated by {failingBindings.Count} binding(s).",
            EvidenceStatus.Unsupported => unsupportedDetail ?? "Rule uses a construct outside the implemented SWRL subset.",
            EvidenceStatus.Passed => "Rule passed for all bindings.",
            _ => $"Rule evaluation resolved to {status}.",
        };

        var result = new RuleEvaluationResult
        {
            RuleId = rule.Id,
            RuleName = rule.Name,
            RuleDescription = rule.Description,
            Passed = passed,
            Status = status,
            Message = message,
        };
        result.FailingBindings.AddRange(failingBindings);
        return result;
    }

    private static BindingOutcome EvaluateBody(IReadOnlyList<Atom> atoms, BindingRow binding)
    {
        foreach (var atom in atoms)
        {
            var outcome = EvaluateAtom(atom, binding);
            if (outcome.Status != EvidenceStatus.Failed)
            {
                // Either a typed non-verdict (Unsupported/Unknown/Error) or a non-matching atom
                // (Passed) — both stop the body walk. A typed non-verdict propagates as-is; a
                // Passed atom means this atom's constraint did not hold, so the body as a whole
                // does not match (see the Passed branch's rationale below).
                return outcome;
            }
        }

        // Every atom matched (each returned Failed): because these are violation-pattern rules
        // (CLAUDE.md § Graph Schema v4 — body atoms fire when the constraint is violated), a
        // fully-matching body is a violation for this binding. Preserve that inversion; it is
        // established rule semantics, not something this phase changes.
        return new BindingOutcome(EvidenceStatus.Failed, null);
    }

    private static BindingOutcome EvaluateAtom(Atom atom, BindingRow binding)
    {
        if (atom.Type.Equals("BuiltinAtom", StringComparison.OrdinalIgnoreCase))
        {
            return EvaluateBuiltin(atom, binding);
        }

        foreach (var arg in atom.Args.Where(a => a.Kind == ArgKind.Variable))
        {
            if (!TryResolveVariableValue(arg.Value, binding, out var value) || value is null)
            {
                // D-08 (missing variable binding -> a typed `unknown` non-verdict) is explicitly
                // plan 02's scope, not this tracer slice's. Preserve today's throw-and-collapse
                // behavior here unchanged; EvaluateRule's catch-all below still counts it as a
                // failing binding, matching the pre-existing RuleEvaluatorTests assertions.
                throw new InvalidOperationException($"Missing binding for variable {arg.Value}.");
            }
        }

        // MVP behavior: class/data-property atoms are treated as variable-availability constraints.
        // All referenced variables resolved, so this atom "matches" — in the violation-pattern
        // inversion (see EvaluateBody), a matching atom is represented as Failed so the body walk
        // continues toward a rule-level violation.
        return new BindingOutcome(EvidenceStatus.Failed, null);
    }

    private static BindingOutcome EvaluateBuiltin(Atom atom, BindingRow binding)
    {
        var predicate = atom.PredicateIri ?? atom.PredicateLabel ?? string.Empty;
        var args = atom.Args.OrderBy(a => a.Pos).Take(2).ToArray();
        if (args.Length < 2)
        {
            return new BindingOutcome(
                EvidenceStatus.Unsupported,
                $"What: builtin '{predicate}' was called with fewer than 2 arguments. " +
                $"Where: a BuiltinAtom in the rule body. " +
                $"How to fix: express the rule with a fully-applied comparison builtin, or accept this typed non-verdict.");
        }

        if (!SupportedBuiltins.IsSupported(predicate))
        {
            return new BindingOutcome(
                EvidenceStatus.Unsupported,
                $"What: predicate '{predicate}' is outside the implemented SWRL builtin subset. " +
                $"Where: a BuiltinAtom in the rule body. " +
                $"How to fix: express the rule with one of the supported comparison builtins " +
                $"({string.Join(", ", SupportedBuiltins.Names)}), or accept this typed non-verdict.");
        }

        object? left;
        object? right;
        try
        {
            left = ResolveArgValue(args[0], binding);
            right = ResolveArgValue(args[1], binding);
        }
        catch (InvalidOperationException ex)
        {
            return new BindingOutcome(EvidenceStatus.Unknown, ex.Message);
        }

        if (TryToDecimal(left, out var leftDec) && TryToDecimal(right, out var rightDec))
        {
            var matched = predicate.ToLowerInvariant() switch
            {
                "swrlb:lessthan" => leftDec < rightDec,
                "swrlb:greaterthan" => leftDec > rightDec,
                "swrlb:lessthanorequal" => leftDec <= rightDec,
                "swrlb:greaterthanorequal" => leftDec >= rightDec,
                "swrlb:equal" => leftDec == rightDec,
                "swrlb:notequal" => leftDec != rightDec,
                _ => false,
            };
            return BuiltinMatchOutcome(matched);
        }

        if (SupportedBuiltins.NonNumericCapableNames.Contains(predicate))
        {
            var matched = predicate.ToLowerInvariant() switch
            {
                "swrlb:equal" => Equals(left, right),
                "swrlb:notequal" => !Equals(left, right),
                _ => false,
            };
            return BuiltinMatchOutcome(matched);
        }

        return new BindingOutcome(
            EvidenceStatus.Unsupported,
            $"What: builtin '{predicate}' requires numeric arguments in this evaluator and the " +
            $"resolved arguments did not convert to a number. " +
            $"Where: a BuiltinAtom in the rule body. " +
            $"How to fix: supply numeric-convertible arguments, or accept this typed non-verdict.");
    }

    /// <summary>
    /// Maps a builtin's boolean match result to a per-binding outcome, in the same
    /// violation-pattern inversion <see cref="EvaluateBody"/> and <see cref="EvaluateAtom"/> use:
    /// a builtin that matches (predicate holds) is <see cref="EvidenceStatus.Failed"/> (continues
    /// the body walk toward a violation); one that does not match is
    /// <see cref="EvidenceStatus.Passed"/> (short-circuits the body as non-violating for this
    /// binding). Neither is a typed non-verdict.
    /// </summary>
    private static BindingOutcome BuiltinMatchOutcome(bool matched) =>
        matched
            ? new BindingOutcome(EvidenceStatus.Failed, null)
            : new BindingOutcome(EvidenceStatus.Passed, null);

    private static object? ResolveArgValue(AtomArg arg, BindingRow binding)
    {
        if (arg.Kind == ArgKind.Variable)
        {
            if (!TryResolveVariableValue(arg.Value, binding, out var value))
            {
                throw new InvalidOperationException($"Missing binding for variable {arg.Value}.");
            }

            return value;
        }

        return ParseLiteral(arg.Value, arg.Datatype);
    }

    private static bool TryResolveVariableValue(string variableName, BindingRow binding, out object? value)
    {
        if (binding.ValuesByVar.TryGetValue(variableName, out value))
        {
            return true;
        }

        var withoutPrefix = variableName.StartsWith("?", StringComparison.Ordinal)
            ? variableName[1..]
            : variableName;
        if (binding.ValuesByVar.TryGetValue(withoutPrefix, out value))
        {
            return true;
        }

        var withPrefix = variableName.StartsWith("?", StringComparison.Ordinal)
            ? variableName
            : "?" + variableName;
        if (binding.ValuesByVar.TryGetValue(withPrefix, out value))
        {
            return true;
        }

        foreach (var pair in binding.ValuesByVar)
        {
            var key = pair.Key?.Trim();
            if (string.IsNullOrWhiteSpace(key))
            {
                continue;
            }

            var normalizedKey = key.StartsWith("?", StringComparison.Ordinal) ? key[1..] : key;
            var normalizedVar = withoutPrefix;
            if (string.Equals(normalizedKey, normalizedVar, StringComparison.OrdinalIgnoreCase))
            {
                value = pair.Value;
                return true;
            }
        }

        value = null;
        return false;
    }

    private static object ParseLiteral(string value, string? datatype)
    {
        if (datatype is not null && datatype.Equals("xsd:boolean", StringComparison.OrdinalIgnoreCase))
        {
            return bool.Parse(value);
        }

        if (datatype is not null && datatype.StartsWith("xsd:", StringComparison.OrdinalIgnoreCase))
        {
            if (datatype.Equals("xsd:integer", StringComparison.OrdinalIgnoreCase))
            {
                return int.Parse(value, CultureInfo.InvariantCulture);
            }

            if (datatype.Equals("xsd:decimal", StringComparison.OrdinalIgnoreCase))
            {
                return decimal.Parse(value, CultureInfo.InvariantCulture);
            }
        }

        if (decimal.TryParse(value, NumberStyles.Any, CultureInfo.InvariantCulture, out var parsedDecimal))
        {
            return parsedDecimal;
        }

        if (bool.TryParse(value, out var parsedBool))
        {
            return parsedBool;
        }

        return value;
    }

    private static bool TryToDecimal(object? value, out decimal result)
    {
        switch (value)
        {
            case decimal d:
                result = d;
                return true;
            case int i:
                result = i;
                return true;
            case long l:
                result = l;
                return true;
            case float f:
                result = (decimal)f;
                return true;
            case double db:
                result = (decimal)db;
                return true;
            case string s when decimal.TryParse(s, NumberStyles.Any, CultureInfo.InvariantCulture, out var parsed):
                result = parsed;
                return true;
            default:
                result = 0;
                return false;
        }
    }
}
