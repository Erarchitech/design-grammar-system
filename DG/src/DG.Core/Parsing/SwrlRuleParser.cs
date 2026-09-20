using System.Globalization;
using System.Text.RegularExpressions;
using DG.Core.Contracts;
using DG.Core.Models;

namespace DG.Core.Parsing;

public static class SwrlRuleParser
{
    private static readonly Regex AtomRegex = new(
        "^(?<predicate>[^\\(]+)\\((?<args>.*)\\)$",
        RegexOptions.Compiled | RegexOptions.CultureInvariant);

    /// <summary>
    /// Parses a SWRL expression, throwing on malformed input. Retained unchanged for every existing
    /// caller (Phase 1201 D-01): a thin wrapper over <see cref="TryParse"/> using the default
    /// (null-object) resolver, which re-throws the same exception type and message it always has for
    /// the three hard-failure diagnostic codes (<see cref="ParseDiagnostic.Codes.EmptyExpression"/>,
    /// <see cref="ParseDiagnostic.Codes.ArrowArity"/>, <see cref="ParseDiagnostic.Codes.AtomRegexMiss"/>).
    ///
    /// <para>
    /// <b>Asymmetry, by design:</b> an <see cref="ParseDiagnostic.Codes.UnresolvablePredicateKind"/>
    /// diagnostic (a ≥2-arg, non-<c>swrlb:</c> predicate the null-object resolver cannot classify)
    /// does <b>not</b> make this method throw. Before Phase 1201, such a predicate silently became a
    /// <c>DataPropertyAtom</c> and <c>Parse</c> returned successfully — throwing now would be a
    /// breaking behavior change for every current caller. The atom is instead emitted as an
    /// <c>UnsupportedAtom</c> (D-03), and the rule is returned with that atom in place. Callers that
    /// need the typed <c>unsupported</c> signal must use <see cref="TryParse"/> instead.
    /// </para>
    /// </summary>
    public static ParsedSwrlRule Parse(string swrlExpression)
    {
        var result = TryParse(swrlExpression);

        foreach (var diagnostic in result.Diagnostics)
        {
            switch (diagnostic.Code)
            {
                case ParseDiagnostic.Codes.EmptyExpression:
                    throw new ArgumentException("SWRL expression cannot be empty.", nameof(swrlExpression));
                case ParseDiagnostic.Codes.ArrowArity:
                    throw new FormatException("SWRL expression must contain exactly one '->'.");
                case ParseDiagnostic.Codes.AtomRegexMiss:
                    throw new FormatException(diagnostic.Message);
            }
        }

        // result.Rule is guaranteed non-null here: the only diagnostic codes that leave Rule null
        // (EmptyExpression, ArrowArity) both throw above; every other diagnostic (unresolvable
        // predicate kind, unterminated quoted literal) is emitted alongside a produced rule.
        return result.Rule!;
    }

    /// <summary>
    /// Parses a SWRL expression without ever throwing (Phase 1201 D-01). Collects
    /// <see cref="ParseDiagnostic"/>s instead of throwing on malformed or unsupported input, and
    /// resolves each ≥2-arg, non-<c>swrlb:</c> predicate's kind via <paramref name="resolver"/>
    /// (defaulting to <see cref="NullPredicateKindResolver.Instance"/>, which reports every predicate
    /// unresolvable) so an <c>ObjectPropertyAtom</c> can be distinguished from a
    /// <c>DataPropertyAtom</c> instead of guessed (D-02). An atom this method cannot classify is
    /// emitted as an <c>UnsupportedAtom</c> rather than dropped (D-03).
    /// </summary>
    public static SwrlParseResult TryParse(string? swrlExpression, IPredicateKindResolver? resolver = null)
    {
        resolver ??= NullPredicateKindResolver.Instance;
        var diagnostics = new List<ParseDiagnostic>();

        if (string.IsNullOrWhiteSpace(swrlExpression))
        {
            diagnostics.Add(new ParseDiagnostic(
                ParseDiagnostic.Codes.EmptyExpression,
                "What: the SWRL expression is empty or whitespace-only. Where: SwrlRuleParser.TryParse "
                    + "input. How to fix: supply a non-empty expression of the form "
                    + "\"Body atoms -> Head atoms\".",
                Offset: -1,
                EvidenceStatus.Error));
            return SwrlParseResult.Create(null, diagnostics);
        }

        var split = swrlExpression.Split("->", StringSplitOptions.TrimEntries);
        if (split.Length != 2)
        {
            diagnostics.Add(new ParseDiagnostic(
                ParseDiagnostic.Codes.ArrowArity,
                "What: the SWRL expression must contain exactly one '->' separating body from head. "
                    + $"Where: expression \"{swrlExpression}\" contains {split.Length - 1} arrow(s). "
                    + "How to fix: rewrite the expression with exactly one '->'.",
                Offset: -1,
                EvidenceStatus.Error));
            return SwrlParseResult.Create(null, diagnostics);
        }

        var parsed = new ParsedSwrlRule { Expression = swrlExpression.Trim() };
        ParseAtoms(split[0], AtomSide.Body, parsed.BodyAtoms, resolver, diagnostics);
        ParseAtoms(split[1], AtomSide.Head, parsed.HeadAtoms, resolver, diagnostics);

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

        return SwrlParseResult.Create(parsed, diagnostics);
    }

    private static void ParseAtoms(
        string chain,
        AtomSide side,
        ICollection<Atom> target,
        IPredicateKindResolver resolver,
        List<ParseDiagnostic> diagnostics)
    {
        var atomTexts = SplitAtomChain(chain);
        var order = 1;
        foreach (var atomText in atomTexts)
        {
            var match = AtomRegex.Match(atomText);
            if (!match.Success)
            {
                diagnostics.Add(new ParseDiagnostic(
                    ParseDiagnostic.Codes.AtomRegexMiss,
                    $"What: the atom text does not match the required \"predicate(args)\" shape. "
                        + $"Where: {side} atom #{order}, text \"{atomText}\". How to fix: wrap the "
                        + "atom's arguments in parentheses, e.g. \"predicate(?x,?y)\".",
                    Offset: -1,
                    EvidenceStatus.Unsupported));

                target.Add(new Atom
                {
                    Id = $"{side}_{order}",
                    Type = "UnsupportedAtom",
                    PredicateIri = atomText,
                    PredicateLabel = atomText,
                    Side = side,
                    Order = order,
                });
                order++;
                continue;
            }

            var predicate = match.Groups["predicate"].Value.Trim();
            var argsRaw = match.Groups["args"].Value;
            var args = SplitArgs(argsRaw, side, order, diagnostics);

            var atom = new Atom
            {
                Id = $"{side}_{order}",
                Type = ResolveAtomType(predicate, args.Count, resolver, side, order, diagnostics),
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

    /// <summary>
    /// Splits a body/head chain into individual atom texts on <c>^</c> (SWRL's atom conjunction
    /// separator), honoring quoted literals so an atom argument containing a literal datatype
    /// suffix (<c>"75.5"^^xsd:decimal</c>) is never mis-split on the suffix's leading <c>^</c>.
    /// A quote-aware linear scanner, not a regex, for the same no-backtracking reason as
    /// <see cref="SplitArgs"/>.
    /// </summary>
    private static List<string> SplitAtomChain(string chain)
    {
        var atoms = new List<string>();
        var current = new System.Text.StringBuilder();
        char? activeQuote = null;
        var escapeNext = false;

        for (var i = 0; i < chain.Length; i++)
        {
            var c = chain[i];

            if (escapeNext)
            {
                current.Append(c);
                escapeNext = false;
                continue;
            }

            if (activeQuote is not null)
            {
                if (c == '\\')
                {
                    current.Append(c);
                    escapeNext = true;
                    continue;
                }

                if (c == activeQuote)
                {
                    activeQuote = null;
                }

                current.Append(c);
                continue;
            }

            if (c is '"' or '\'')
            {
                activeQuote = c;
                current.Append(c);
                continue;
            }

            // "^^" is a literal datatype suffix marker (e.g. "75.5"^^xsd:decimal), never an atom
            // separator -- consume both carets as a unit and keep scanning inside the same atom
            // when the current '^' is immediately followed by another '^'. Only a lone, unquoted
            // '^' conjoins two atoms.
            if (c == '^')
            {
                if (i + 1 < chain.Length && chain[i + 1] == '^')
                {
                    current.Append(c).Append(chain[i + 1]);
                    i++;
                    continue;
                }

                var text = current.ToString().Trim();
                if (text.Length > 0)
                {
                    atoms.Add(text);
                }

                current.Clear();
                continue;
            }

            current.Append(c);
        }

        var trailing = current.ToString().Trim();
        if (trailing.Length > 0)
        {
            atoms.Add(trailing);
        }

        return atoms;
    }

    private static string ResolveAtomType(
        string predicate,
        int argCount,
        IPredicateKindResolver resolver,
        AtomSide side,
        int order,
        List<ParseDiagnostic> diagnostics)
    {
        if (predicate.StartsWith("swrlb:", StringComparison.OrdinalIgnoreCase))
        {
            return "BuiltinAtom";
        }

        if (argCount <= 1)
        {
            return "ClassAtom";
        }

        if (resolver.TryGetKind(predicate, out var kind))
        {
            return kind switch
            {
                PredicateKind.ObjectProperty => "ObjectPropertyAtom",
                PredicateKind.DatatypeProperty => "DataPropertyAtom",
                _ => "UnsupportedAtom",
            };
        }

        // No fallback to DataPropertyAtom here. An unresolvable predicate kind is the exact
        // silent-misclassification defect Phase 1201 D-02 exists to end -- it must surface as a
        // typed UnsupportedAtom, never a guess.
        diagnostics.Add(new ParseDiagnostic(
            ParseDiagnostic.Codes.UnresolvablePredicateKind,
            $"What: predicate '{predicate}' has {argCount} arguments but its kind (ObjectProperty vs "
                + $"DatatypeProperty) could not be resolved against the OntoGraph. Where: {side} atom "
                + $"#{order}, predicate '{predicate}'. How to fix: ensure the predicate IRI is "
                + "registered as an ObjectProperty or DatatypeProperty in the OntoGraph, or supply an "
                + "IPredicateKindResolver that can resolve it.",
            Offset: -1,
            EvidenceStatus.Unsupported));

        return "UnsupportedAtom";
    }

    private static List<string> SplitArgs(string args, AtomSide side, int order, List<ParseDiagnostic> diagnostics)
    {
        var values = new List<string>();
        if (string.IsNullOrWhiteSpace(args))
        {
            return values;
        }

        // Single-pass linear scanner: tracks whether the cursor is inside a quoted literal and
        // honors a backslash escape for the active quote character. Deliberately not a regex --
        // RESEARCH's security section flags nested-quantifier backtracking as the DoS risk for this
        // surface, and a linear scanner has no backtracking at all.
        var current = new System.Text.StringBuilder();
        char? activeQuote = null;
        var escapeNext = false;

        for (var i = 0; i < args.Length; i++)
        {
            var c = args[i];

            if (escapeNext)
            {
                current.Append(c);
                escapeNext = false;
                continue;
            }

            if (activeQuote is not null)
            {
                if (c == '\\')
                {
                    current.Append(c);
                    escapeNext = true;
                    continue;
                }

                if (c == activeQuote)
                {
                    activeQuote = null;
                }

                current.Append(c);
                continue;
            }

            if (c is '"' or '\'')
            {
                activeQuote = c;
                current.Append(c);
                continue;
            }

            if (c == ',')
            {
                values.Add(current.ToString().Trim());
                current.Clear();
                continue;
            }

            current.Append(c);
        }

        if (activeQuote is not null)
        {
            diagnostics.Add(new ParseDiagnostic(
                ParseDiagnostic.Codes.UnterminatedQuotedLiteral,
                $"What: a quoted literal in the argument list was never terminated with a closing "
                    + $"'{activeQuote}'. Where: {side} atom #{order}, args \"{args}\". How to fix: "
                    + "close the quoted literal or escape an embedded quote with a backslash.",
                Offset: -1,
                EvidenceStatus.Unsupported));
            // Stop cleanly: do not emit the trailing partial token as an argument.
            return values;
        }

        var trailing = current.ToString().Trim();
        if (trailing.Length > 0)
        {
            values.Add(trailing);
        }

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

        if (TryParseQuotedLiteral(trimmed, pos, out var quotedArg))
        {
            return quotedArg;
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

    /// <summary>
    /// Recognizes a quoted literal with an explicit datatype suffix (<c>"x"^^xsd:decimal</c>) or a
    /// language tag (<c>"x"@en</c>), before the existing unsuffixed-literal inference chain runs.
    /// Returns <c>false</c> for anything that is not a quoted literal at all, leaving the caller's
    /// existing inference chain untouched for unsuffixed forms.
    /// </summary>
    private static bool TryParseQuotedLiteral(string trimmed, int pos, out AtomArg arg)
    {
        arg = null!;
        if (trimmed.Length < 2 || (trimmed[0] != '"' && trimmed[0] != '\''))
        {
            return false;
        }

        var quote = trimmed[0];
        var closingIndex = FindClosingQuote(trimmed, quote);
        if (closingIndex < 0)
        {
            return false;
        }

        var value = Unescape(trimmed.Substring(1, closingIndex - 1), quote);
        var suffix = trimmed.Substring(closingIndex + 1);

        if (suffix.StartsWith("^^", StringComparison.Ordinal))
        {
            var datatype = suffix.Substring(2).Trim();
            if (datatype.Length == 0)
            {
                return false;
            }

            arg = new AtomArg
            {
                Pos = pos,
                Kind = ArgKind.Literal,
                Value = value,
                Datatype = datatype,
            };
            return true;
        }

        if (suffix.StartsWith("@", StringComparison.Ordinal))
        {
            var language = suffix.Substring(1).Trim();
            if (language.Length == 0)
            {
                return false;
            }

            arg = new AtomArg
            {
                Pos = pos,
                Kind = ArgKind.Literal,
                Value = value,
                Datatype = "xsd:string",
                Language = language,
            };
            return true;
        }

        if (suffix.Trim().Length > 0)
        {
            // Trailing text after the closing quote that is neither a "^^" datatype suffix nor an
            // "@" language tag -- not a form this method recognizes. Let the caller's existing
            // inference chain handle it (matches pre-Task-3 behavior for any such stray suffix).
            return false;
        }

        // A plain quoted literal with no suffix at all -- this is the pre-Task-3 unsuffixed-string
        // case, now routed through the same quote-aware scanner so a backslash-escaped quote inside
        // it is honored rather than left in the value verbatim.
        arg = new AtomArg
        {
            Pos = pos,
            Kind = ArgKind.Literal,
            Value = value,
            Datatype = "xsd:string",
        };
        return true;
    }

    private static int FindClosingQuote(string text, char quote)
    {
        var escapeNext = false;
        for (var i = 1; i < text.Length; i++)
        {
            var c = text[i];
            if (escapeNext)
            {
                escapeNext = false;
                continue;
            }

            if (c == '\\')
            {
                escapeNext = true;
                continue;
            }

            if (c == quote)
            {
                return i;
            }
        }

        return -1;
    }

    private static string Unescape(string value, char quote)
    {
        if (!value.Contains('\\', StringComparison.Ordinal))
        {
            return value;
        }

        var result = new System.Text.StringBuilder(value.Length);
        for (var i = 0; i < value.Length; i++)
        {
            if (value[i] == '\\' && i + 1 < value.Length && (value[i + 1] == quote || value[i + 1] == '\\'))
            {
                result.Append(value[i + 1]);
                i++;
                continue;
            }

            result.Append(value[i]);
        }

        return result.ToString();
    }
}
