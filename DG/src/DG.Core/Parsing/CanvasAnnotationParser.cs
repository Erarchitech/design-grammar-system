using System.Globalization;
using System.Text.RegularExpressions;
using DG.Core.Models.Computgraph;

namespace DG.Core.Parsing;

/// <summary>
/// Turns a <see cref="RawCanvas"/> (extractor output) into a <see cref="CgContext"/> by
/// matching scribble text and group nicknames against the DG Canvas Annotation Convention
/// grammar (RESEARCH.md &#167;4). Conforming names become typed Computgraph entities;
/// everything else falls into <see cref="CgContext.Untagged"/>. The parser never guesses --
/// guessing is Phase 35's LLM job (CONTEXT.md decision #2).
/// </summary>
public static class CanvasAnnotationParser
{
    private const int MaxHostChainDepth = 32;

    // All grammar regexes are anchored (^...$) with literal prefixes and a single greedy
    // ".+" capture -- no nested/overlapping quantifiers -- so matching stays linear and is
    // immune to catastrophic backtracking (ReDoS, threat T-32-03).
    private static readonly Regex ObjectRegex = new(
        "^OBJECT - (?<name>.+)$",
        RegexOptions.Compiled | RegexOptions.CultureInvariant);

    private static readonly Regex AlgorithmRegex = new(
        @"^(?<alg>\d+)_ALGORITHM$",
        RegexOptions.Compiled | RegexOptions.CultureInvariant);

    private static readonly Regex ProcedureRegex = new(
        @"^(?<nn>\d+)_Proc - (?<name>.+)$",
        RegexOptions.Compiled | RegexOptions.CultureInvariant);

    private static readonly Regex PatternRegex = new(
        @"^(?<nn>\d+)_Pat_(?<idx>[^ ]+)( (?<name>.+))?$",
        RegexOptions.Compiled | RegexOptions.CultureInvariant);

    private static readonly Regex VariableRegex = new(
        @"^(?<nn>\d+)_Var_(?<name>.+)$",
        RegexOptions.Compiled | RegexOptions.CultureInvariant);

    private static readonly Regex ConstantRegex = new(
        @"^(?<nn>\d+)_Const_(?<name>.+)$",
        RegexOptions.Compiled | RegexOptions.CultureInvariant);

    private static readonly Regex EmergentRegex = new(
        @"^(?<nn>\d+)_(?<tag>Emg|Emr)_(?<name>.+)$",
        RegexOptions.Compiled | RegexOptions.CultureInvariant);

    private static readonly Regex InterfaceRegex = new(
        @"^(?<nn>\d+)_IntF_(?<name>.+)$",
        RegexOptions.Compiled | RegexOptions.CultureInvariant);

    /// <summary>
    /// Widget members -- an explicit authoring choice, so they outrank the primitive tier.
    /// </summary>
    private static readonly PrimaryComponentKind[] WidgetPrecedence =
    {
        PrimaryComponentKind.Slider,
        PrimaryComponentKind.ValueList,
        PrimaryComponentKind.Panel,
        PrimaryComponentKind.Boolean,
    };

    /// <summary>
    /// Bare GH primitive params -- the fallback tier consulted only when a parameter group holds
    /// no widget member. Without it an ordinary Constant source (a bare Number) infers no dataType
    /// at all and the whole publish payload is rejected (F5).
    /// </summary>
    private static readonly PrimaryComponentKind[] PrimitivePrecedence =
    {
        PrimaryComponentKind.Number,
        PrimaryComponentKind.Integer,
        PrimaryComponentKind.Text,
        PrimaryComponentKind.Geometry,
    };

    private const string WidgetPrecedenceLabel = "slider > value list > panel > boolean";

    private const string PrimitivePrecedenceLabel = "number > integer > text > geometry";

    /// <summary>
    /// GH geometry param names, matched exactly -- a geometry-valued Emergent parameter is as
    /// common as a numeric Constant and is otherwise untypeable.
    /// </summary>
    private static readonly HashSet<string> GeometryParamNames = new(StringComparer.OrdinalIgnoreCase)
    {
        "Geometry", "Point", "Vector", "Plane", "Line", "Circle", "Arc", "Curve",
        "Surface", "Brep", "Mesh", "SubD", "Box", "Rectangle", "Transform",
    };

    /// <summary>
    /// Classifies a <see cref="RawCanvas"/> into a populated <see cref="CgContext"/>.
    /// Throws only for a null <paramref name="raw"/> (API-boundary guard); unrecognized
    /// scribble/group text is routed to the untagged set and never guessed.
    /// </summary>
    public static CgContext Parse(RawCanvas raw)
    {
        ArgumentNullException.ThrowIfNull(raw);

        CgObject? cgObject = null;
        var algorithms = new List<CgAlgorithm>();
        var warnings = new List<string>();
        var untaggedGroups = new List<CgUntaggedGroup>();
        var claimedMemberIds = new HashSet<string>(StringComparer.Ordinal);

        // WR-04: an NN token the grammar regexes accept (\d+) but TryParseNn cannot
        // decompose (single digit, or digits overflowing int) must not crash Parse() --
        // the parser contract is "throws only for a null raw". Route the group to the
        // untagged set with a warning naming the offending nickname instead.
        void RouteMalformedNn(string nickname, string nn, RawGroup group)
        {
            warnings.Add(
                $"Group '{nickname}' has a malformed NN token '{nn}' -- need at least two digits " +
                "(algorithm digit + procedure ordinal); routed to untagged.");
            untaggedGroups.Add(new CgUntaggedGroup
            {
                Nickname = nickname,
                MemberIds = new List<string>(group.MemberIds),
            });
        }

        // 1. Scribbles: OBJECT and ALGORITHM declarations.
        foreach (var scribble in raw.Scribbles)
        {
            var text = scribble.Text ?? string.Empty;

            var objectMatch = ObjectRegex.Match(text);
            if (objectMatch.Success)
            {
                cgObject = new CgObject
                {
                    Name = objectMatch.Groups["name"].Value.Trim(),
                    Source = "tagged",
                };
                continue;
            }

            var algorithmMatch = AlgorithmRegex.Match(text);
            if (algorithmMatch.Success)
            {
                var algIndex = int.Parse(algorithmMatch.Groups["alg"].Value, CultureInfo.InvariantCulture);
                if (algorithms.All(a => a.Index != algIndex))
                {
                    algorithms.Add(new CgAlgorithm { Index = algIndex, Name = text.Trim() });
                }
            }
        }

        // 2. Groups, pass 1: Procedures only -- ensures every conforming Proc group exists
        // (with its real Name) before pass 2 attaches Patterns/Parameters/Interfaces to it,
        // regardless of the order groups appear in raw.Groups.
        foreach (var group in raw.Groups)
        {
            var procedureMatch = ProcedureRegex.Match(group.Nickname ?? string.Empty);
            if (!procedureMatch.Success)
            {
                continue;
            }

            var nn = procedureMatch.Groups["nn"].Value;
            if (!TryParseNn(nn, out var algDigit, out var procIndex))
            {
                RouteMalformedNn(group.Nickname ?? string.Empty, nn, group);
                continue;
            }

            var algorithm = GetOrCreateAlgorithm(algorithms, algDigit);

            if (algorithm.Procedures.All(p => p.Index != procIndex))
            {
                algorithm.Procedures.Add(new CgProcedure
                {
                    Id = ProcedureId(algDigit, nn),
                    Index = procIndex,
                    Name = procedureMatch.Groups["name"].Value.Trim(),
                    Source = group.Recognized ? "recognized" : "tagged",
                    Provider = group.Provider,
                    Model = group.Model,
                    Confidence = group.Confidence,
                    MemberIds = new List<string>(group.MemberIds),
                });
            }

            claimedMemberIds.UnionWith(group.MemberIds);
        }

        // 3. Groups, pass 2: Patterns (deferred -- see step 4), Parameters (Var/Const/Emg),
        // Interfaces, and untagged routing.
        var pendingPatterns = new List<PendingPattern>();

        foreach (var group in raw.Groups)
        {
            var nickname = group.Nickname ?? string.Empty;

            if (ProcedureRegex.IsMatch(nickname))
            {
                // Already handled in pass 1.
                continue;
            }

            var patternMatch = PatternRegex.Match(nickname);
            if (patternMatch.Success)
            {
                var nn = patternMatch.Groups["nn"].Value;
                var idx = patternMatch.Groups["idx"].Value;
                if (!TryParseNn(nn, out var algDigit, out var procIndex))
                {
                    RouteMalformedNn(nickname, nn, group);
                    continue;
                }

                var procedure = GetOrCreateProcedure(algorithms, algDigit, procIndex);

                pendingPatterns.Add(new PendingPattern(
                    Group: group,
                    Id: PatternId(algDigit, nn, idx),
                    Procedure: procedure,
                    ProcedureIndex: procIndex,
                    Label: nickname,
                    Name: patternMatch.Groups["name"].Success ? patternMatch.Groups["name"].Value.Trim() : null));

                claimedMemberIds.UnionWith(group.MemberIds);
                continue;
            }

            var variableMatch = VariableRegex.Match(nickname);
            var constantMatch = ConstantRegex.Match(nickname);
            var emergentMatch = EmergentRegex.Match(nickname);
            if (variableMatch.Success || constantMatch.Success || emergentMatch.Success)
            {
                var (kind, kindLiteral, match) = variableMatch.Success
                    ? (ParamKind.Variable, "var", variableMatch)
                    : constantMatch.Success
                        ? (ParamKind.Constant, "const", constantMatch)
                        : (ParamKind.Emergent, "emg", emergentMatch);

                var nn = match.Groups["nn"].Value;
                if (!TryParseNn(nn, out var algDigit, out var procIndex))
                {
                    RouteMalformedNn(nickname, nn, group);
                    continue;
                }

                var procedure = GetOrCreateProcedure(algorithms, algDigit, procIndex);
                var name = match.Groups["name"].Value.Trim();

                if (kind == ParamKind.Emergent && emergentMatch.Groups["tag"].Value == "Emr")
                {
                    warnings.Add($"'{nickname}' normalized to Emergent (Emr→Emg)");
                }

                var memberNodes = raw.Nodes.Where(n => group.MemberIds.Contains(n.InstanceId));
                var (dataType, domain, inferenceWarning) = InferParameterDataType(nickname, memberNodes);
                if (inferenceWarning is not null)
                {
                    warnings.Add(inferenceWarning);
                }

                procedure.Parameters.Add(new CgParameter
                {
                    Id = ParamId(algDigit, kindLiteral, nickname),
                    Kind = kind,
                    Name = name,
                    DataType = dataType,
                    Domain = domain,
                    MemberIds = new List<string>(group.MemberIds),
                    Source = group.Recognized ? "recognized" : "tagged",
                    Provider = group.Provider,
                    Model = group.Model,
                    Confidence = group.Confidence,
                });

                claimedMemberIds.UnionWith(group.MemberIds);
                continue;
            }

            var interfaceMatch = InterfaceRegex.Match(nickname);
            if (interfaceMatch.Success)
            {
                var nn = interfaceMatch.Groups["nn"].Value;
                if (!TryParseNn(nn, out var algDigit, out var procIndex))
                {
                    RouteMalformedNn(nickname, nn, group);
                    continue;
                }

                var procedure = GetOrCreateProcedure(algorithms, algDigit, procIndex);
                var name = interfaceMatch.Groups["name"].Value.Trim();

                procedure.Interfaces.Add(new CgInterface
                {
                    Id = InterfaceId(algDigit, nn, name),
                    Name = name,
                    // Grammar carries no Input/Output marker (RESEARCH.md §4) -- Input is the
                    // conservative default; Phase 35 recognition/human-confirmation refines it.
                    IfaceType = IfaceType.Input,
                    MemberIds = new List<string>(group.MemberIds),
                    Source = group.Recognized ? "recognized" : "tagged",
                    Provider = group.Provider,
                    Model = group.Model,
                    Confidence = group.Confidence,
                });

                claimedMemberIds.UnionWith(group.MemberIds);
                continue;
            }

            // Non-conforming: route to untagged, never guess (CONTEXT.md decision #2).
            untaggedGroups.Add(new CgUntaggedGroup
            {
                Nickname = nickname,
                MemberIds = new List<string>(group.MemberIds),
            });
        }

        // 4. Pattern nesting: resolve each pattern's immediate HostPatternId BEFORE
        // constructing the (init-only) CgPattern instances, then guard the resulting
        // parent-pointer chains against unbounded/cyclic walks (threat T-32-04).
        var hostIdByGroup = ComputeHostPatternIds(raw.Groups, pendingPatterns);
        var allPatterns = new List<CgPattern>(pendingPatterns.Count);
        foreach (var pending in pendingPatterns)
        {
            var pattern = new CgPattern
            {
                Id = pending.Id,
                Label = pending.Label,
                Name = pending.Name,
                HostPatternId = hostIdByGroup.TryGetValue(pending.Group, out var hostId) ? hostId : null,
                MemberIds = new List<string>(pending.Group.MemberIds),
                Source = pending.Group.Recognized ? "recognized" : "tagged",
                Provider = pending.Group.Provider,
                Model = pending.Group.Model,
                Confidence = pending.Group.Confidence,
            };
            pending.Procedure.Patterns.Add(pattern);
            allPatterns.Add(pattern);
        }

        GuardHostChains(allPatterns, warnings);

        // 5. Untagged nodes: any raw node whose id was never claimed by a tagged entity.
        var untaggedNodeIds = raw.Nodes
            .Select(n => n.InstanceId)
            .Where(id => !claimedMemberIds.Contains(id))
            .ToList();

        return new CgContext
        {
            SchemaVersion = "cg-context-1",
            Project = raw.Project,
            Definition = raw.Definition,
            Object = cgObject,
            Algorithms = algorithms,
            Untagged = new CgUntagged
            {
                NodeIds = untaggedNodeIds,
                Groups = untaggedGroups,
            },
            Nodes = raw.Nodes,
            Wires = raw.Wires,
            Warnings = warnings,
        };
    }

    /// <summary>
    /// Decomposes an NN token into its algorithm digit and full procedure index
    /// (e.g. "11" -&gt; alg 1, procIndex 11; "12" -&gt; alg 1, procIndex 12). Returns false --
    /// never throws -- for a token that cannot be decomposed: fewer than two digits (the
    /// grammar regexes accept a bare "1" via <c>\d+</c>) or digits that overflow
    /// <see cref="int"/>. Replaces the old SplitNn, whose <c>int.Parse(nn.Substring(1))</c>
    /// threw <see cref="FormatException"/> on a single-digit token and let one malformed
    /// user-typed nickname abort the entire canvas-context extraction (WR-04).
    /// </summary>
    private static bool TryParseNn(string nn, out int algorithm, out int procIndex)
    {
        algorithm = 0;

        if (nn.Length < 2
            || !int.TryParse(nn, NumberStyles.None, CultureInfo.InvariantCulture, out procIndex))
        {
            procIndex = 0;
            return false;
        }

        algorithm = nn[0] - '0';
        return true;
    }

    private static CgAlgorithm GetOrCreateAlgorithm(List<CgAlgorithm> algorithms, int index)
    {
        var existing = algorithms.FirstOrDefault(a => a.Index == index);
        if (existing is not null)
        {
            return existing;
        }

        var created = new CgAlgorithm { Index = index, Name = string.Empty };
        algorithms.Add(created);
        return created;
    }

    private static CgProcedure GetOrCreateProcedure(List<CgAlgorithm> algorithms, int algDigit, int procIndex)
    {
        var algorithm = GetOrCreateAlgorithm(algorithms, algDigit);
        var existing = algorithm.Procedures.FirstOrDefault(p => p.Index == procIndex);
        if (existing is not null)
        {
            return existing;
        }

        // Orphan NN: a Pattern/Parameter/Interface referenced a procedure NN with no
        // matching Proc group. Created with an empty Name so members still attach
        // somewhere rather than being silently dropped.
        var created = new CgProcedure
        {
            Id = ProcedureId(algDigit, procIndex.ToString(CultureInfo.InvariantCulture)),
            Index = procIndex,
            Name = string.Empty,
            Source = "tagged",
        };
        algorithm.Procedures.Add(created);
        return created;
    }

    /// <summary>
    /// Computes each pattern group's immediate host id: primary via the innermost OTHER
    /// pending pattern whose <see cref="RawGroup.NestedGroupIds"/> names this group's
    /// nickname, fallback via the smallest strict-superset MemberIds match within the same
    /// procedure. Returns a map keyed by <see cref="RawGroup"/> reference (patterns aren't
    /// constructed yet).
    /// <para>
    /// The primary-path candidate set is restricted to groups that are THEMSELVES pending
    /// patterns, and ties are broken by ascending <c>MemberIds.Count</c> (Phase 35-16, plan
    /// 35-16-PLAN.md). A real GH extractor reports containment transitively, so a Procedure
    /// group -- or an outer pattern -- can legitimately name a deeply nested child pattern
    /// in its <see cref="RawGroup.NestedGroupIds"/>. Resolving by document order (the old
    /// <c>FirstOrDefault</c> over ALL groups) made the outcome depend on where that
    /// Procedure/outer-pattern group happened to sit in <see cref="RawCanvas.Groups"/>: if it
    /// appeared before the true parent pattern, it won the lookup, the group turned out not
    /// to be a pending pattern, the strict-superset fallback found nothing (disjoint member
    /// sets), and the nesting was silently dropped. Filtering to pattern candidates and
    /// picking the smallest (innermost) enclosing one makes the host the immediate parent
    /// regardless of group order.
    /// </para>
    /// </summary>
    private static Dictionary<RawGroup, string?> ComputeHostPatternIds(
        List<RawGroup> allGroups, List<PendingPattern> pendingPatterns)
    {
        var result = new Dictionary<RawGroup, string?>();

        foreach (var pending in pendingPatterns)
        {
            string? hostId = null;

            var hostPattern = pendingPatterns
                .Where(p => !ReferenceEquals(p.Group, pending.Group))
                .Where(p => p.Group.NestedGroupIds.Contains(pending.Group.Nickname))
                .OrderBy(p => p.Group.MemberIds.Count)
                .FirstOrDefault();
            if (hostPattern is not null)
            {
                hostId = hostPattern.Id;
            }
            else if (pending.Group.MemberIds.Count > 0)
            {
                var candidate = pendingPatterns
                    .Where(p => p.ProcedureIndex == pending.ProcedureIndex && !ReferenceEquals(p.Group, pending.Group))
                    .Where(p => p.Group.MemberIds.Count > pending.Group.MemberIds.Count
                        && pending.Group.MemberIds.All(id => p.Group.MemberIds.Contains(id)))
                    .OrderBy(p => p.Group.MemberIds.Count)
                    .FirstOrDefault();

                if (candidate is not null)
                {
                    hostId = candidate.Id;
                }
            }

            result[pending.Group] = hostId;
        }

        return result;
    }

    /// <summary>
    /// Walks each pattern's HostPatternId parent-pointer chain, bounded to
    /// <see cref="MaxHostChainDepth"/> with cycle detection (threat T-32-04) -- on exceeding
    /// the bound (or detecting a self-referential loop), stops walking and appends a warning
    /// instead of recursing/looping unboundedly.
    /// </summary>
    private static void GuardHostChains(List<CgPattern> allPatterns, List<string> warnings)
    {
        var byId = allPatterns.ToDictionary(p => p.Id, p => p);
        foreach (var pattern in allPatterns)
        {
            var visited = new HashSet<string>(StringComparer.Ordinal);
            CgPattern? current = pattern;
            var depth = 0;

            while (current?.HostPatternId is not null)
            {
                if (!visited.Add(current.Id) || depth >= MaxHostChainDepth)
                {
                    warnings.Add(
                        $"Pattern host chain for '{pattern.Label}' exceeded max depth ({MaxHostChainDepth}) or contains a cycle; stopped resolving.");
                    break;
                }

                depth++;
                byId.TryGetValue(current.HostPatternId, out current);
            }
        }
    }

    /// <summary>
    /// Public seam over <see cref="InferParameterDataType"/> so a caller can ask, BEFORE
    /// committing to a parameter entity, the same question the parser will ask at
    /// context-pull time: can this member set be assigned a <see cref="ParamDataType"/>?
    /// </summary>
    /// <remarks>
    /// Exists for the accept-time publishability gate (Phase 35, guardrail G12). A null
    /// <c>DataType</c> is fatal three phases later -- the SHACL-backed publish rejects the
    /// WHOLE payload when one parameter lacks it (ParameterShape_dataType, sh:minCount 1),
    /// so 11 valid entities cannot land because of 1 invalid one, and the architect reads
    /// that as "the AI made me break my publish" (UAT F5). Asking here moves the failure to
    /// the moment they can still act on it.
    /// <para>
    /// This delegates rather than re-implements on purpose: a second copy of the inference
    /// rules in the Grasshopper layer would drift from this one, and a divergence between
    /// what the gate accepts and what the parser types is exactly how F5 happens again.
    /// </para>
    /// </remarks>
    public static (ParamDataType? DataType, SliderDomain? Domain, string? Warning) TryInferParameterDataType(
        string parameterNickname, IEnumerable<CgNode> memberNodes) =>
        InferParameterDataType(parameterNickname, memberNodes);

    private static (ParamDataType? DataType, SliderDomain? Domain, string? Warning) InferParameterDataType(
        string parameterNickname, IEnumerable<CgNode> memberNodes)
    {
        var members = memberNodes.ToList();
        var classified = members
            .Select(n => (Node: n, Kind: ClassifyNodeKind(n)))
            .Where(t => t.Kind != PrimaryComponentKind.None)
            .ToList();

        // Widget members (slider / value list / panel / toggle) are a deliberate authoring choice, so
        // they win outright over bare primitive params, which are only a fallback tier. Keeping the
        // two tiers separate also keeps the conflict warning from firing on the common
        // "slider wired through a Number param" shape.
        var tier = classified.Where(c => WidgetPrecedence.Contains(c.Kind)).ToList();
        var precedence = WidgetPrecedence;
        var precedenceLabel = WidgetPrecedenceLabel;

        if (tier.Count == 0)
        {
            tier = classified.Where(c => PrimitivePrecedence.Contains(c.Kind)).ToList();
            precedence = PrimitivePrecedence;
            precedenceLabel = PrimitivePrecedenceLabel;
        }

        if (tier.Count == 0)
        {
            // A null dataType is fatal downstream -- data-service rejects the WHOLE publish payload
            // when one parameter lacks it (ParameterShape_dataType, sh:minCount 1). Never let that
            // leave the parser silently; the author must see it on the context pull. Member-less
            // groups stay quiet (tag-then-populate is a normal workflow) -- the publish component's
            // pre-flight catches those instead.
            return members.Count == 0
                ? (null, null, null)
                : (null, null,
                    $"Parameter '{parameterNickname}' has no member component the parser can type " +
                    $"(expected {WidgetPrecedenceLabel}, or a Number/Integer/Text/geometry param); " +
                    "dataType is unset and publishing will reject the payload.");
        }

        var distinctKinds = tier.Select(c => c.Kind).Distinct().ToList();
        string? warning = distinctKinds.Count > 1
            ? $"Parameter '{parameterNickname}' has conflicting member component types " +
              $"({string.Join(", ", distinctKinds)}); resolved via precedence {precedenceLabel}."
            : null;

        var primary = precedence
            .Select(kind => tier.FirstOrDefault(c => c.Kind == kind).Node)
            .FirstOrDefault(n => n is not null);

        if (primary is null)
        {
            return (null, null, warning);
        }

        if (primary.Slider is not null)
        {
            var dataType = primary.IsIntegerSlider ? ParamDataType.Integer : ParamDataType.Float;
            return (dataType, primary.Slider, warning);
        }

        var inferred = ClassifyNodeKind(primary) switch
        {
            PrimaryComponentKind.Boolean => ParamDataType.Boolean,
            PrimaryComponentKind.Number => ParamDataType.Float,
            PrimaryComponentKind.Integer => ParamDataType.Integer,
            PrimaryComponentKind.Geometry => ParamDataType.Geometry,
            _ => ParamDataType.Text,
        };

        return (inferred, null, warning);
    }

    private static PrimaryComponentKind ClassifyNodeKind(CgNode node)
    {
        if (node.Slider is not null)
        {
            return PrimaryComponentKind.Slider;
        }

        var name = node.Name ?? string.Empty;

        if (name.Contains("Value List", StringComparison.OrdinalIgnoreCase))
        {
            return PrimaryComponentKind.ValueList;
        }

        if (name.Contains("Panel", StringComparison.OrdinalIgnoreCase))
        {
            return PrimaryComponentKind.Panel;
        }

        if (name.Contains("Toggle", StringComparison.OrdinalIgnoreCase))
        {
            return PrimaryComponentKind.Boolean;
        }

        // Fallback tier: bare GH primitive params carry no widget UI but still imply a dataType.
        // Matched on the exact param name so "Number Slider"-style widgets never land here.
        if (name.Equals("Number", StringComparison.OrdinalIgnoreCase))
        {
            return PrimaryComponentKind.Number;
        }

        if (name.Equals("Integer", StringComparison.OrdinalIgnoreCase))
        {
            return PrimaryComponentKind.Integer;
        }

        if (name.Equals("Text", StringComparison.OrdinalIgnoreCase)
            || name.Equals("String", StringComparison.OrdinalIgnoreCase))
        {
            return PrimaryComponentKind.Text;
        }

        if (GeometryParamNames.Contains(name))
        {
            return PrimaryComponentKind.Geometry;
        }

        return PrimaryComponentKind.None;
    }

    private static string ProcedureId(int alg, string nn) => $"cg:{alg}:proc:{nn}";

    private static string PatternId(int alg, string nn, string idx) => $"cg:{alg}:pat:{nn}_{idx}";

    private static string ParamId(int alg, string kindLiteral, string nickname) => $"cg:{alg}:{kindLiteral}:{nickname}";

    private static string InterfaceId(int alg, string nn, string name) => $"cg:{alg}:intf:{nn}_{name}";

    private enum PrimaryComponentKind
    {
        None,
        Panel,
        ValueList,
        Slider,
        Boolean,
        Number,
        Integer,
        Text,
        Geometry,
    }

    private sealed record PendingPattern(
        RawGroup Group, string Id, CgProcedure Procedure, int ProcedureIndex, string Label, string? Name);
}
