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
    /// Computes each pattern group's immediate host id: primary via another group's
    /// <see cref="RawGroup.NestedGroupIds"/> naming this group's nickname, fallback via the
    /// smallest strict-superset MemberIds match within the same procedure. Returns a map
    /// keyed by <see cref="RawGroup"/> reference (patterns aren't constructed yet).
    /// </summary>
    private static Dictionary<RawGroup, string?> ComputeHostPatternIds(
        List<RawGroup> allGroups, List<PendingPattern> pendingPatterns)
    {
        var idByGroup = pendingPatterns.ToDictionary(p => p.Group, p => p.Id);
        var result = new Dictionary<RawGroup, string?>();

        foreach (var pending in pendingPatterns)
        {
            string? hostId = null;

            var hostGroup = allGroups.FirstOrDefault(g => g.NestedGroupIds.Contains(pending.Group.Nickname));
            if (hostGroup is not null && idByGroup.TryGetValue(hostGroup, out var primaryHostId))
            {
                hostId = primaryHostId;
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

    private static (ParamDataType? DataType, SliderDomain? Domain, string? Warning) InferParameterDataType(
        string parameterNickname, IEnumerable<CgNode> memberNodes)
    {
        var classified = memberNodes
            .Select(n => (Node: n, Kind: ClassifyNodeKind(n)))
            .Where(t => t.Kind != PrimaryComponentKind.None)
            .ToList();

        if (classified.Count == 0)
        {
            return (null, null, null);
        }

        var distinctKinds = classified.Select(c => c.Kind).Distinct().ToList();
        string? warning = distinctKinds.Count > 1
            ? $"Parameter '{parameterNickname}' has conflicting member component types " +
              $"({string.Join(", ", distinctKinds)}); resolved via precedence slider > value list > panel > boolean."
            : null;

        var primary = classified.FirstOrDefault(c => c.Kind == PrimaryComponentKind.Slider).Node
            ?? classified.FirstOrDefault(c => c.Kind == PrimaryComponentKind.ValueList).Node
            ?? classified.FirstOrDefault(c => c.Kind == PrimaryComponentKind.Panel).Node
            ?? classified.FirstOrDefault(c => c.Kind == PrimaryComponentKind.Boolean).Node;

        if (primary is null)
        {
            return (null, null, warning);
        }

        if (primary.Slider is not null)
        {
            var dataType = primary.IsIntegerSlider ? ParamDataType.Integer : ParamDataType.Float;
            return (dataType, primary.Slider, warning);
        }

        var primaryKind = ClassifyNodeKind(primary);
        var textOrBoolean = primaryKind == PrimaryComponentKind.Boolean
            ? ParamDataType.Boolean
            : ParamDataType.Text;

        return (textOrBoolean, null, warning);
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
    }

    private sealed record PendingPattern(
        RawGroup Group, string Id, CgProcedure Procedure, int ProcedureIndex, string Label, string? Name);
}
