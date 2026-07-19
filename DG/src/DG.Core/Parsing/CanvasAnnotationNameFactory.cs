using System.Globalization;

namespace DG.Core.Parsing;

/// <summary>
/// Discriminates the grammar shapes <see cref="CanvasAnnotationNameFactory.ForEntity"/> can
/// build. Mirrors the Kind dispatch inside <see cref="CanvasAnnotationParser"/> (Proc/Pat/Var/
/// Const/Emg/IntF); Object and Algorithm scribbles are built by their own dedicated factory
/// methods since they have no NN-scoped Kind infix.
/// </summary>
public enum EntityTagKind
{
    Proc,
    Pat,
    Var,
    Const,
    Emg,
    IntF,
}

/// <summary>
/// Pure name-construction factory for the DG Canvas Annotation Convention (RESEARCH.md
/// &#167;4) -- the write-path counterpart to <see cref="CanvasAnnotationParser"/>. Every name
/// this factory builds is guaranteed to parse back through
/// <see cref="CanvasAnnotationParser.Parse"/> to the equivalent typed entity
/// (<c>Source == "tagged"</c>), enforced by construction plus the round-trip test suite
/// (TAGC-03). All methods are pure and culture-invariant.
/// </summary>
public static class CanvasAnnotationNameFactory
{
    /// <summary>Builds an OBJECT scribble text, e.g. <c>"OBJECT - FRAME"</c>.</summary>
    public static string ForObjectScribble(string name)
    {
        if (string.IsNullOrWhiteSpace(name))
        {
            throw new ArgumentException(
                "What: Object name is empty or whitespace. " +
                "Where: CanvasAnnotationNameFactory.ForObjectScribble. " +
                "How to fix: supply a non-empty, non-whitespace Object name.",
                nameof(name));
        }

        // WR-07: the parser's ^OBJECT - (?<name>.+)$ regex is neither Singleline nor
        // Multiline, so an embedded newline would silently break the factory's round-trip
        // guarantee -- reject it here rather than relying on caller-side ValidateName.
        if (name.Contains('\n') || name.Contains('\r'))
        {
            throw new ArgumentException(
                "What: Object name contains a newline. " +
                "Where: CanvasAnnotationNameFactory.ForObjectScribble. " +
                "How to fix: remove line breaks from the Object name.",
                nameof(name));
        }

        return CanvasAnnotationGrammar.ObjectPrefix + name.Trim();
    }

    /// <summary>Builds an ALGORITHM scribble text, e.g. <c>"1_ALGORITHM"</c>.</summary>
    public static string ForAlgorithmScribble(int algorithmIndex)
    {
        if (algorithmIndex < 1 || algorithmIndex > 9)
        {
            throw new ArgumentOutOfRangeException(
                nameof(algorithmIndex),
                algorithmIndex,
                "What: AlgorithmIndex is outside the valid single-digit range. " +
                "Where: CanvasAnnotationNameFactory.ForAlgorithmScribble. " +
                "How to fix: pass a value between 1 and 9 -- it becomes the leading NN algorithm digit " +
                "that CanvasAnnotationParser.SplitNn expects.");
        }

        return algorithmIndex.ToString(CultureInfo.InvariantCulture) + CanvasAnnotationGrammar.AlgorithmSuffix;
    }

    /// <summary>
    /// Builds a group nickname for the given <paramref name="kind"/> under the full NN token
    /// <paramref name="procIndex"/> (e.g. 11 = algorithm 1, procedure ordinal 1). NN is built by
    /// string concatenation, never arithmetic (inverse of <c>CanvasAnnotationParser.SplitNn</c>).
    /// <paramref name="patternIndex"/> is required (and only meaningful) for
    /// <see cref="EntityTagKind.Pat"/>; when supplied with a non-empty <paramref name="name"/>,
    /// the idx slot is always the auto-assigned integer and Name becomes the optional trailing
    /// label (<c>NN_Pat_idx</c> or <c>NN_Pat_idx Name</c>).
    /// </summary>
    public static string ForEntity(EntityTagKind kind, int procIndex, string name, int? patternIndex = null)
    {
        if (procIndex < 10)
        {
            throw new ArgumentOutOfRangeException(
                nameof(procIndex),
                procIndex,
                "What: ProcIndex is below the minimum valid NN token. " +
                "Where: CanvasAnnotationNameFactory.ForEntity. " +
                "How to fix: pass the full two-digit-or-more NN token (algorithm digit + procedure " +
                "ordinal, e.g. 11), not a bare ordinal -- values below 10 cannot be split by " +
                "CanvasAnnotationParser.SplitNn.");
        }

        var nn = procIndex.ToString(CultureInfo.InvariantCulture);
        var trimmedName = (name ?? string.Empty).Trim();

        switch (kind)
        {
            case EntityTagKind.Proc:
                ValidateName(trimmedName);
                return nn + CanvasAnnotationGrammar.ProcedureInfix + trimmedName;

            case EntityTagKind.Var:
                ValidateName(trimmedName);
                return nn + CanvasAnnotationGrammar.VariableInfix + trimmedName;

            case EntityTagKind.Const:
                ValidateName(trimmedName);
                return nn + CanvasAnnotationGrammar.ConstantInfix + trimmedName;

            case EntityTagKind.Emg:
                ValidateName(trimmedName);
                // Always canonical Emg -- EmergentToleratedInfix ("_Emr_") is a read-only
                // tolerated variant the parser normalizes with a warning; this factory never
                // emits it.
                return nn + CanvasAnnotationGrammar.EmergentInfix + trimmedName;

            case EntityTagKind.IntF:
                ValidateName(trimmedName);
                return nn + CanvasAnnotationGrammar.InterfaceInfix + trimmedName;

            case EntityTagKind.Pat:
                if (patternIndex is null)
                {
                    throw new ArgumentException(
                        "What: patternIndex is required for EntityTagKind.Pat. " +
                        "Where: CanvasAnnotationNameFactory.ForEntity. " +
                        "How to fix: pass a non-null patternIndex, e.g. the next-free index from " +
                        "NextFreePatternIndex.",
                        nameof(patternIndex));
                }

                if (trimmedName.Length > 0)
                {
                    ValidateName(trimmedName);
                }

                var basePart = nn + CanvasAnnotationGrammar.PatternInfix
                    + patternIndex.Value.ToString(CultureInfo.InvariantCulture);
                return trimmedName.Length > 0 ? basePart + " " + trimmedName : basePart;

            default:
                throw new ArgumentOutOfRangeException(nameof(kind), kind, "Unknown EntityTagKind.");
        }
    }

    /// <summary>
    /// Strips a leading convention prefix (<c>NN&lt;Infix&gt;</c>, e.g. <c>"11_IntF_"</c>) from
    /// <paramref name="suggestedName"/> when present, returning the bare trailing Name that
    /// <see cref="ForEntity"/> expects. Phase 35 LLM recognition is taught to emit
    /// <c>suggestedName</c> as a FULL convention name (<c>"11_IntF_ParSplitAt"</c>); feeding
    /// that full name straight back into <see cref="ForEntity"/> would trip
    /// <see cref="ValidateName"/>'s reserved-infix rejection (and double-prefix the result),
    /// so the confirm/accept path bare-names it here first (CR-01). For
    /// <see cref="EntityTagKind.Emg"/> the tolerated <c>_Emr_</c> variant is also stripped;
    /// for <see cref="EntityTagKind.Pat"/> a leading integer idx token after the infix is
    /// dropped too -- <see cref="ForEntity"/> re-assigns a fresh index via its
    /// <c>patternIndex</c> argument. A name with no recognizable leading prefix is returned
    /// trimmed and otherwise unchanged.
    /// </summary>
    public static string StripConventionPrefix(EntityTagKind kind, string suggestedName)
    {
        var name = (suggestedName ?? string.Empty).Trim();
        if (name.Length == 0)
        {
            return name;
        }

        var infixes = kind switch
        {
            EntityTagKind.Proc => new[] { CanvasAnnotationGrammar.ProcedureInfix },
            EntityTagKind.Pat => new[] { CanvasAnnotationGrammar.PatternInfix },
            EntityTagKind.Var => new[] { CanvasAnnotationGrammar.VariableInfix },
            EntityTagKind.Const => new[] { CanvasAnnotationGrammar.ConstantInfix },
            EntityTagKind.Emg => new[]
            {
                CanvasAnnotationGrammar.EmergentInfix,
                CanvasAnnotationGrammar.EmergentToleratedInfix,
            },
            EntityTagKind.IntF => new[] { CanvasAnnotationGrammar.InterfaceInfix },
            _ => throw new ArgumentOutOfRangeException(nameof(kind), kind, "Unknown EntityTagKind."),
        };

        foreach (var infix in infixes)
        {
            var pos = name.IndexOf(infix, StringComparison.Ordinal);
            if (pos <= 0 || !IsAllDigits(name, pos))
            {
                // Only a prefix of shape "<digits><infix>" at the very start counts as a
                // convention prefix; anything else is left for ValidateName to judge.
                continue;
            }

            var rest = name.Substring(pos + infix.Length);

            if (kind == EntityTagKind.Pat)
            {
                // Full Pat names carry an idx slot ("NN_Pat_idx[ Label]") -- drop the idx
                // token; ForEntity assigns a fresh one from its patternIndex argument.
                var spaceIdx = rest.IndexOf(' ');
                var idxToken = spaceIdx >= 0 ? rest.Substring(0, spaceIdx) : rest;
                if (int.TryParse(idxToken, NumberStyles.None, CultureInfo.InvariantCulture, out _))
                {
                    rest = spaceIdx >= 0 ? rest.Substring(spaceIdx + 1) : string.Empty;
                }
            }

            return rest.Trim();
        }

        return name;
    }

    private static bool IsAllDigits(string value, int endExclusive)
    {
        for (var i = 0; i < endExclusive; i++)
        {
            if (value[i] < '0' || value[i] > '9')
            {
                return false;
            }
        }

        return true;
    }

    /// <summary>
    /// Computes the next-free integer Pattern index under the given NN token
    /// <paramref name="procIndex"/> by scanning <paramref name="existingGroupNicknames"/> for
    /// <c>NN_Pat_idx[...]</c> shapes, ignoring non-integer idx tokens. Returns 1 when no
    /// existing Pattern nicknames match.
    /// </summary>
    public static int NextFreePatternIndex(IEnumerable<string> existingGroupNicknames, int procIndex)
    {
        ArgumentNullException.ThrowIfNull(existingGroupNicknames);

        var prefix = procIndex.ToString(CultureInfo.InvariantCulture) + CanvasAnnotationGrammar.PatternInfix;
        var maxIdx = 0;

        foreach (var nickname in existingGroupNicknames)
        {
            if (nickname is null || !nickname.StartsWith(prefix, StringComparison.Ordinal))
            {
                continue;
            }

            var remainder = nickname.Substring(prefix.Length);
            var spaceIdx = remainder.IndexOf(' ');
            var idxToken = spaceIdx >= 0 ? remainder.Substring(0, spaceIdx) : remainder;

            if (int.TryParse(idxToken, NumberStyles.None, CultureInfo.InvariantCulture, out var idx) && idx > maxIdx)
            {
                maxIdx = idx;
            }
        }

        return maxIdx + 1;
    }

    /// <summary>
    /// True when <paramref name="name"/> contains any <see cref="CanvasAnnotationGrammar.ReservedInfixTokens"/>
    /// entry (Ordinal comparison). A reserved token inside a Name would make the emitted name
    /// re-parse as a different <see cref="EntityTagKind"/> than intended.
    /// </summary>
    public static bool IsReservedName(string name)
    {
        if (string.IsNullOrEmpty(name))
        {
            return false;
        }

        foreach (var token in CanvasAnnotationGrammar.ReservedInfixTokens)
        {
            if (name.Contains(token, StringComparison.Ordinal))
            {
                return true;
            }
        }

        return false;
    }

    /// <summary>
    /// Rejects an empty/whitespace <paramref name="name"/>, a Name containing a newline, or a
    /// Name containing a reserved grammar infix token (T-34-01, V5 input validation).
    /// </summary>
    public static void ValidateName(string name)
    {
        if (string.IsNullOrWhiteSpace(name))
        {
            throw new ArgumentException(
                "What: Name is empty or whitespace. " +
                "Where: CanvasAnnotationNameFactory.ValidateName. " +
                "How to fix: supply a non-empty, non-whitespace Name.",
                nameof(name));
        }

        if (name.Contains('\n') || name.Contains('\r'))
        {
            throw new ArgumentException(
                "What: Name contains a newline. " +
                "Where: CanvasAnnotationNameFactory.ValidateName. " +
                "How to fix: remove line breaks from Name.",
                nameof(name));
        }

        foreach (var token in CanvasAnnotationGrammar.ReservedInfixTokens)
        {
            if (name.Contains(token, StringComparison.Ordinal))
            {
                throw new ArgumentException(
                    $"What: Name '{name}' contains the reserved grammar infix token '{token}'. " +
                    "Where: CanvasAnnotationNameFactory.ValidateName. " +
                    $"How to fix: remove '{token}' from Name (reserved tokens: " +
                    $"{string.Join(", ", CanvasAnnotationGrammar.ReservedInfixTokens)}).",
                    nameof(name));
            }
        }
    }
}
