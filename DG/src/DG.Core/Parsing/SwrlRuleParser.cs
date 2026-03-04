using System.Globalization;
using System.Text.RegularExpressions;
using DG.Core.Models;

namespace DG.Core.Parsing;

public static class SwrlRuleParser
{
    private static readonly Regex AtomRegex = new(
        "^(?<predicate>[^\\(]+)\\((?<args>.*)\\)$",
        RegexOptions.Compiled | RegexOptions.CultureInvariant);

    public static ParsedSwrlRule Parse(string swrlExpression)
    {
        if (string.IsNullOrWhiteSpace(swrlExpression))
        {
            throw new ArgumentException("SWRL expression cannot be empty.", nameof(swrlExpression));
        }

        var split = swrlExpression.Split("->", StringSplitOptions.TrimEntries);
        if (split.Length != 2)
        {
            throw new FormatException("SWRL expression must contain exactly one '->'.");
        }

        var parsed = new ParsedSwrlRule { Expression = swrlExpression.Trim() };
        ParseAtoms(split[0], AtomSide.Body, parsed.BodyAtoms);
        ParseAtoms(split[1], AtomSide.Head, parsed.HeadAtoms);

        var variables = parsed.BodyAtoms
            .Concat(parsed.HeadAtoms)
            .SelectMany(atom => atom.Args)
            .Where(arg => arg.Kind == ArgKind.Variable)
            .Select(arg => arg.Value)
            .Distinct(StringComparer.Ordinal)
            .OrderBy(name => name, StringComparer.Ordinal);

        foreach (var variableName in variables)
        {
            parsed.Variables.Add(new Variable { Name = variableName });
        }

        return parsed;
    }

    private static void ParseAtoms(string chain, AtomSide side, ICollection<Atom> target)
    {
        var atomTexts = chain.Split('^', StringSplitOptions.RemoveEmptyEntries | StringSplitOptions.TrimEntries);
        var order = 1;
        foreach (var atomText in atomTexts)
        {
            var match = AtomRegex.Match(atomText);
            if (!match.Success)
            {
                throw new FormatException($"Invalid SWRL atom: {atomText}");
            }

            var predicate = match.Groups["predicate"].Value.Trim();
            var argsRaw = match.Groups["args"].Value;
            var args = SplitArgs(argsRaw);

            var atom = new Atom
            {
                Id = $"{side}_{order}",
                Type = ResolveAtomType(predicate, args.Count),
                PredicateIri = predicate,
                PredicateLabel = predicate,
                Side = side,
                Order = order,
            };

            for (var i = 0; i < args.Count; i++)
            {
                atom.Args.Add(ParseArg(args[i], i + 1));
            }

            target.Add(atom);
            order++;
        }
    }

    private static string ResolveAtomType(string predicate, int argCount)
    {
        if (predicate.StartsWith("swrlb:", StringComparison.OrdinalIgnoreCase))
        {
            return "BuiltinAtom";
        }

        return argCount switch
        {
            <= 1 => "ClassAtom",
            _ => "DataPropertyAtom",
        };
    }

    private static List<string> SplitArgs(string args)
    {
        var values = new List<string>();
        if (string.IsNullOrWhiteSpace(args))
        {
            return values;
        }

        var parts = args.Split(',', StringSplitOptions.RemoveEmptyEntries | StringSplitOptions.TrimEntries);
        values.AddRange(parts);
        return values;
    }

    private static AtomArg ParseArg(string token, int pos)
    {
        var trimmed = token.Trim();
        if (trimmed.StartsWith("?", StringComparison.Ordinal))
        {
            return new AtomArg
            {
                Pos = pos,
                Kind = ArgKind.Variable,
                Value = trimmed,
            };
        }

        if (bool.TryParse(trimmed, out _))
        {
            return new AtomArg
            {
                Pos = pos,
                Kind = ArgKind.Literal,
                Value = trimmed.ToLowerInvariant(),
                Datatype = "xsd:boolean",
            };
        }

        if (decimal.TryParse(trimmed, NumberStyles.Any, CultureInfo.InvariantCulture, out _))
        {
            var datatype = trimmed.Contains('.', StringComparison.Ordinal) ? "xsd:decimal" : "xsd:integer";
            return new AtomArg
            {
                Pos = pos,
                Kind = ArgKind.Literal,
                Value = trimmed,
                Datatype = datatype,
            };
        }

        return new AtomArg
        {
            Pos = pos,
            Kind = ArgKind.Literal,
            Value = trimmed.Trim('"', '\''),
            Datatype = "xsd:string",
        };
    }
}
