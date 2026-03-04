using System.Globalization;
using DG.Core.Models;
using DG.Core.Parsing;

namespace DG.Core.Validation;

public sealed class RuleEvaluator
{
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
                Passed = false,
                Message = "No variable bindings were provided.",
            };
        }

        var bodyAtoms = rule.BodyAtoms.Count > 0
            ? rule.BodyAtoms.ToList()
            : SwrlRuleParser.Parse(rule.Swrl).BodyAtoms;

        var failingBindings = new List<BindingRow>();
        string? firstError = null;

        foreach (var binding in bindings)
        {
            try
            {
                if (EvaluateBody(bodyAtoms, binding))
                {
                    failingBindings.Add(binding);
                }
            }
            catch (Exception ex)
            {
                firstError ??= ex.Message;
                failingBindings.Add(binding);
            }
        }

        var passed = failingBindings.Count == 0 && firstError is null;
        var message = firstError ?? (passed
            ? "Rule passed for all bindings."
            : $"Rule violated by {failingBindings.Count} binding(s).");

        var result = new RuleEvaluationResult
        {
            RuleId = rule.Id,
            RuleName = rule.Name,
            RuleDescription = rule.Description,
            Passed = passed,
            Message = message,
        };
        result.FailingBindings.AddRange(failingBindings);
        return result;
    }

    private static bool EvaluateBody(IReadOnlyList<Atom> atoms, BindingRow binding)
    {
        foreach (var atom in atoms)
        {
            if (!EvaluateAtom(atom, binding))
            {
                return false;
            }
        }

        return true;
    }

    private static bool EvaluateAtom(Atom atom, BindingRow binding)
    {
        if (atom.Type.Equals("BuiltinAtom", StringComparison.OrdinalIgnoreCase))
        {
            return EvaluateBuiltin(atom, binding);
        }

        foreach (var arg in atom.Args.Where(a => a.Kind == ArgKind.Variable))
        {
            if (!TryResolveVariableValue(arg.Value, binding, out var value) || value is null)
            {
                throw new InvalidOperationException($"Missing binding for variable {arg.Value}.");
            }
        }

        // MVP behavior: class/data-property atoms are treated as variable-availability constraints.
        return true;
    }

    private static bool EvaluateBuiltin(Atom atom, BindingRow binding)
    {
        var predicate = atom.PredicateIri ?? atom.PredicateLabel ?? string.Empty;
        var args = atom.Args.OrderBy(a => a.Pos).Take(2).ToArray();
        if (args.Length < 2)
        {
            throw new InvalidOperationException($"Builtin {predicate} requires 2 arguments.");
        }

        var left = ResolveArgValue(args[0], binding);
        var right = ResolveArgValue(args[1], binding);

        if (TryToDecimal(left, out var leftDec) && TryToDecimal(right, out var rightDec))
        {
            return predicate.ToLowerInvariant() switch
            {
                "swrlb:lessthan" => leftDec < rightDec,
                "swrlb:greaterthan" => leftDec > rightDec,
                "swrlb:lessthanorequal" => leftDec <= rightDec,
                "swrlb:greaterthanorequal" => leftDec >= rightDec,
                "swrlb:equal" => leftDec == rightDec,
                "swrlb:notequal" => leftDec != rightDec,
                _ => throw new NotSupportedException($"Unsupported builtin in MVP evaluator: {predicate}"),
            };
        }

        return predicate.ToLowerInvariant() switch
        {
            "swrlb:equal" => Equals(left, right),
            "swrlb:notequal" => !Equals(left, right),
            _ => throw new NotSupportedException($"Builtin requires numeric arguments in MVP evaluator: {predicate}"),
        };
    }

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
