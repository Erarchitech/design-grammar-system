using System.Globalization;
using DG.Core.Models;
using DG.Core.Parsing;

namespace DG.Core.Validation;

public static class FailingBindingFormatter
{
    public static string Format(Rule rule, BindingRow binding)
    {
        var bodyAtoms = ParseBodyAtoms(rule);
        var classVariables = ExtractClassVariables(bodyAtoms);
        var failedVariables = ExtractFailedVariables(bodyAtoms, classVariables);

        var leftParts = classVariables
            .Select(classVar => $"{NormalizeVarName(classVar)}({FormatValue(ResolveVariableValue(binding, classVar))})")
            .ToList();
        if (leftParts.Count == 0)
        {
            leftParts.Add("<entity>(<missing>)");
        }

        var rightParts = new List<string>();
        foreach (var variable in failedVariables)
        {
            rightParts.Add($"{NormalizeVarName(variable)}({FormatValue(ResolveVariableValue(binding, variable))})");
        }

        if (rightParts.Count == 0)
        {
            var classNormalized = new HashSet<string>(classVariables.Select(NormalizeVarName), StringComparer.OrdinalIgnoreCase);
            foreach (var pair in binding.ValuesByVar)
            {
                var normalized = NormalizeVarName(pair.Key);
                if (string.IsNullOrWhiteSpace(normalized) || classNormalized.Contains(normalized))
                {
                    continue;
                }

                rightParts.Add($"{normalized}({FormatValue(pair.Value)})");
            }
        }

        if (rightParts.Count == 0)
        {
            rightParts.Add("<value>(<missing>)");
        }

        return $"{string.Join(", ", leftParts)}: {string.Join(", ", rightParts)}";
    }

    private static IReadOnlyList<Atom> ParseBodyAtoms(Rule rule)
    {
        if (!string.IsNullOrWhiteSpace(rule.Swrl))
        {
            return SwrlRuleParser.Parse(rule.Swrl).BodyAtoms;
        }

        return rule.BodyAtoms.ToList();
    }

    private static List<string> ExtractClassVariables(IReadOnlyList<Atom> bodyAtoms)
    {
        return bodyAtoms
            .Where(atom => atom.Type.Equals("ClassAtom", StringComparison.OrdinalIgnoreCase))
            .SelectMany(atom => atom.Args)
            .Where(arg => arg.Kind == ArgKind.Variable)
            .Select(arg => arg.Value)
            .Distinct(StringComparer.Ordinal)
            .ToList();
    }

    private static List<string> ExtractFailedVariables(IReadOnlyList<Atom> bodyAtoms, IReadOnlyCollection<string> classVariables)
    {
        var classNormalized = new HashSet<string>(classVariables.Select(NormalizeVarName), StringComparer.OrdinalIgnoreCase);

        var builtin = bodyAtoms
            .Where(atom => atom.Type.Equals("BuiltinAtom", StringComparison.OrdinalIgnoreCase))
            .SelectMany(atom => atom.Args)
            .Where(arg => arg.Kind == ArgKind.Variable)
            .Select(arg => arg.Value)
            .Where(variable => !classNormalized.Contains(NormalizeVarName(variable)))
            .Distinct(StringComparer.Ordinal)
            .ToList();

        if (builtin.Count > 0)
        {
            return builtin;
        }

        return bodyAtoms
            .Where(atom => !atom.Type.Equals("ClassAtom", StringComparison.OrdinalIgnoreCase))
            .SelectMany(atom => atom.Args)
            .Where(arg => arg.Kind == ArgKind.Variable)
            .Select(arg => arg.Value)
            .Where(variable => !classNormalized.Contains(NormalizeVarName(variable)))
            .Distinct(StringComparer.Ordinal)
            .ToList();
    }

    private static object? ResolveVariableValue(BindingRow binding, string variableName)
    {
        if (TryResolve(binding, variableName, out var value))
        {
            return value;
        }

        var withoutPrefix = NormalizeVarName(variableName);
        if (TryResolve(binding, withoutPrefix, out value))
        {
            return value;
        }

        var withPrefix = "?" + withoutPrefix;
        if (TryResolve(binding, withPrefix, out value))
        {
            return value;
        }

        return null;
    }

    private static bool TryResolve(BindingRow binding, string key, out object? value)
    {
        if (binding.ValuesByVar.TryGetValue(key, out value))
        {
            return true;
        }

        foreach (var pair in binding.ValuesByVar)
        {
            if (string.Equals(pair.Key, key, StringComparison.OrdinalIgnoreCase))
            {
                value = pair.Value;
                return true;
            }
        }

        value = null;
        return false;
    }

    private static string NormalizeVarName(string? variableName)
    {
        if (string.IsNullOrWhiteSpace(variableName))
        {
            return string.Empty;
        }

        var trimmed = variableName.Trim();
        return trimmed.StartsWith("?", StringComparison.Ordinal) ? trimmed[1..] : trimmed;
    }

    private static string FormatValue(object? value)
    {
        return value switch
        {
            null => "<missing>",
            IFormattable formattable => formattable.ToString(null, CultureInfo.InvariantCulture),
            _ => value.ToString() ?? "<missing>",
        };
    }
}
