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
                // D-06 (Phase 1201 plan 02): this is a real, distinguishable evaluation outcome —
                // the rule was evaluated and its binding population was empty — not a failure and
                // not a non-evaluation. Wording deliberately avoids "violated"/"failed" so it does
                // not read as a verdict.
                Message = "Rule evaluated with an empty binding population: no bindings were provided.",
            };
        }

        var bodyAtoms = rule.BodyAtoms.Count > 0
            ? rule.BodyAtoms.ToList()
            : SwrlRuleParser.Parse(rule.Swrl).BodyAtoms;

        var failingBindings = new List<BindingRow>();
        var outcomes = new List<BindingOutcome>(bindings.Count);
        string? unsupportedDetail = null;
        string? unknownDetail = null;
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
                // Phase 1201 plan 02: this catch is now reachable only by a genuine unexpected
                // fault in the evaluation mechanism itself (e.g. a literal that fails to parse in
                // ParseLiteral, or any other fault neither EvaluateBody nor EvaluateAtom nor
                // EvaluateBuiltin turns into a typed BindingOutcome). The four outcomes that used
                // to reach here as thrown exceptions no longer do:
                //   - empty binding population -> handled above, before this loop even starts (D-06)
                //   - a missing/unresolvable variable binding -> Unknown, returned directly by
                //     EvaluateAtom/ResolveArgValue via TryResolveArg (D-08)
                //   - an ObjectPropertyAtom/UnsupportedAtom/unrecognized atom type -> Unsupported,
                //     returned directly by EvaluateAtom's dispatch (D-14)
                //   - an unsupported or malformed builtin -> Unsupported, returned directly by
                //     EvaluateBuiltin (D-07, plan 01)
                // A genuine unexpected fault is a mechanism error, per the contract's `error`
                // semantics, and is still counted as a failing binding here — converting it into a
                // crash inside a Grasshopper-hosted process would be a regression.
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
            else if (outcome.Status == EvidenceStatus.Unknown && unknownDetail is null)
            {
                unknownDetail = outcome.Detail;
            }
        }

        var status = StatusRollup.Rollup(outcomes.Select(o => o.Status));
        var passed = EvidenceEnvelopeFactory.ToLegacyBoolean(status);

        var message = status switch
        {
            EvidenceStatus.Error => firstErrorDetail ?? "Rule evaluation encountered an unexpected error.",
            EvidenceStatus.Failed => $"Rule violated by {failingBindings.Count} binding(s).",
            EvidenceStatus.Unsupported => unsupportedDetail ?? "Rule uses a construct outside the implemented SWRL subset.",
            EvidenceStatus.Unknown => unknownDetail ?? "Rule evaluation could not resolve a variable binding.",
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

    /// <summary>
    /// Dispatches on <see cref="Atom.Type"/> (ordinal-ignore-case), in this deliberate order
    /// (Phase 1201 plan 02, D-14 Pitfall-1 guard):
    /// <list type="bullet">
    /// <item><c>BuiltinAtom</c> -> <see cref="EvaluateBuiltin"/>, as before.</item>
    /// <item><c>ObjectPropertyAtom</c> and <c>UnsupportedAtom</c> -> a typed
    /// <see cref="EvidenceStatus.Unsupported"/> refusal, regardless of whether every variable
    /// resolves. Plan 03 teaches the parser to emit these types; without this branch they would
    /// fall through to the variable-availability check below and — if every variable happened to
    /// resolve — report as satisfied, which is exactly the false general-reasoner claim D-14
    /// disclaims. Recognizing an atom type is not the same as evaluating it.</item>
    /// <item><c>ClassAtom</c> and <c>DataPropertyAtom</c> -> the existing variable-availability
    /// check, unchanged in behavior except that a missing variable now returns a typed
    /// <see cref="EvidenceStatus.Unknown"/> outcome (D-08) instead of throwing.</item>
    /// <item>anything else (an atom type string this evaluator does not recognize at all) ->
    /// the same typed <see cref="EvidenceStatus.Unsupported"/> refusal as the second bullet.</item>
    /// </list>
    /// </summary>
    private static BindingOutcome EvaluateAtom(Atom atom, BindingRow binding)
    {
        if (atom.Type.Equals("BuiltinAtom", StringComparison.OrdinalIgnoreCase))
        {
            return EvaluateBuiltin(atom, binding);
        }

        if (atom.Type.Equals("ObjectPropertyAtom", StringComparison.OrdinalIgnoreCase)
            || atom.Type.Equals("UnsupportedAtom", StringComparison.OrdinalIgnoreCase))
        {
            return ObjectPropertyOrUnsupportedOutcome(atom);
        }

        if (!atom.Type.Equals("ClassAtom", StringComparison.OrdinalIgnoreCase)
            && !atom.Type.Equals("DataPropertyAtom", StringComparison.OrdinalIgnoreCase))
        {
            // An atom type string that is none of the four known kinds. Refuse rather than
            // silently falling through to the availability check below.
            return ObjectPropertyOrUnsupportedOutcome(atom);
        }

        foreach (var arg in atom.Args.Where(a => a.Kind == ArgKind.Variable))
        {
            if (!TryResolveArg(arg, binding, out _, out var unknownDetail))
            {
                // D-08: binding resolution was attempted and could not resolve. A typed
                // Unknown non-verdict, not a thrown exception and not a failing binding.
                return new BindingOutcome(EvidenceStatus.Unknown, unknownDetail);
            }
        }

        // MVP behavior: class/data-property atoms are treated as variable-availability constraints.
        // All referenced variables resolved, so this atom "matches" — in the violation-pattern
        // inversion (see EvaluateBody), a matching atom is represented as Failed so the body walk
        // continues toward a rule-level violation.
        return new BindingOutcome(EvidenceStatus.Failed, null);
    }

    /// <summary>
    /// The D-14 typed refusal for an <c>ObjectPropertyAtom</c>, an explicit <c>UnsupportedAtom</c>,
    /// or any atom type string this evaluator does not recognize. Deliberately does not attempt to
    /// resolve the atom's variables first — the refusal is driven by atom type alone, proving (per
    /// this task's behavior spec) that even a fully-bound atom of this type is refused rather than
    /// reported as satisfied.
    /// </summary>
    private static BindingOutcome ObjectPropertyOrUnsupportedOutcome(Atom atom)
    {
        var predicate = atom.PredicateIri ?? atom.PredicateLabel ?? string.Empty;
        return new BindingOutcome(
            EvidenceStatus.Unsupported,
            $"What: this atom's predicate ('{predicate}') is an object property, which this " +
            $"evaluator recognizes but does not evaluate. " +
            $"Where: atom '{atom.Id}', predicate '{predicate}'. " +
            $"How to fix: express the constraint using a datatype property and one of the " +
            $"supported comparison builtins, or accept this typed non-verdict.");
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

        if (!TryResolveArg(args[0], binding, out var left, out var leftUnknownDetail))
        {
            return new BindingOutcome(EvidenceStatus.Unknown, leftUnknownDetail);
        }

        if (!TryResolveArg(args[1], binding, out var right, out var rightUnknownDetail))
        {
            return new BindingOutcome(EvidenceStatus.Unknown, rightUnknownDetail);
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

    /// <summary>
    /// Try-shape resolution of a single atom argument (Phase 1201 plan 02, D-08). Named after the
    /// existing <see cref="TryResolveVariableValue"/> in this same file so the file stays
    /// internally consistent — both are net7.0-safe <c>Try*</c> shapes already in production here.
    /// A variable argument that is absent from the binding row yields <c>false</c> with a
    /// What+Where+How-to-fix <paramref name="unknownDetail"/> (the <see cref="EvidenceStatus.Unknown"/>
    /// wording pattern from <c>ErrorMessageTemplates</c>) rather than throwing. A literal argument
    /// always resolves.
    /// </summary>
    private static bool TryResolveArg(AtomArg arg, BindingRow binding, out object? value, out string? unknownDetail)
    {
        if (arg.Kind == ArgKind.Variable)
        {
            if (!TryResolveVariableValue(arg.Value, binding, out value))
            {
                unknownDetail =
                    $"What: the variable '{arg.Value}' that the rule body references has no value " +
                    $"in this binding row. " +
                    $"Where: variable '{arg.Value}', atom argument position {arg.Pos}. " +
                    $"How to fix: supply the value for that variable in the binding source, or " +
                    $"accept this typed non-verdict.";
                return false;
            }

            unknownDetail = null;
            return true;
        }

        value = ParseLiteral(arg.Value, arg.Datatype);
        unknownDetail = null;
        return true;
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
