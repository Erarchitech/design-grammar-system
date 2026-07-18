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
    /// scribble/group text is never guessed into a typed entity.
    /// </summary>
    public static CgContext Parse(RawCanvas raw)
    {
        ArgumentNullException.ThrowIfNull(raw);

        CgObject? cgObject = null;
        var algorithms = new List<CgAlgorithm>();

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
            var (algDigit, _) = SplitNn(nn);
            var procIndex = int.Parse(nn, CultureInfo.InvariantCulture);
            var algorithm = GetOrCreateAlgorithm(algorithms, algDigit);

            if (algorithm.Procedures.All(p => p.Index != procIndex))
            {
                algorithm.Procedures.Add(new CgProcedure
                {
                    Id = ProcedureId(algDigit, nn),
                    Index = procIndex,
                    Name = procedureMatch.Groups["name"].Value.Trim(),
                    Source = "tagged",
                    MemberIds = new List<string>(group.MemberIds),
                });
            }
        }

        // 3. Groups, pass 2: Patterns, Parameters (Var/Const/Emg), Interfaces.
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
                var (algDigit, _) = SplitNn(nn);
                var procIndex = int.Parse(nn, CultureInfo.InvariantCulture);
                var procedure = GetOrCreateProcedure(algorithms, algDigit, procIndex);

                procedure.Patterns.Add(new CgPattern
                {
                    Id = PatternId(algDigit, nn, idx),
                    Label = nickname,
                    Name = patternMatch.Groups["name"].Success ? patternMatch.Groups["name"].Value.Trim() : null,
                    HostPatternId = null,
                    MemberIds = new List<string>(group.MemberIds),
                    Source = "tagged",
                });
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
                var (algDigit, _) = SplitNn(nn);
                var procIndex = int.Parse(nn, CultureInfo.InvariantCulture);
                var procedure = GetOrCreateProcedure(algorithms, algDigit, procIndex);
                var name = match.Groups["name"].Value.Trim();

                procedure.Parameters.Add(new CgParameter
                {
                    Id = ParamId(algDigit, kindLiteral, nickname),
                    Kind = kind,
                    Name = name,
                    DataType = null,
                    Domain = null,
                    MemberIds = new List<string>(group.MemberIds),
                    Source = "tagged",
                });
                continue;
            }

            var interfaceMatch = InterfaceRegex.Match(nickname);
            if (interfaceMatch.Success)
            {
                var nn = interfaceMatch.Groups["nn"].Value;
                var (algDigit, _) = SplitNn(nn);
                var procIndex = int.Parse(nn, CultureInfo.InvariantCulture);
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
                    Source = "tagged",
                });
            }

            // Non-conforming names are not yet routed anywhere -- untagged classification is
            // added in Task 2 (CONTEXT.md decision #2: the parser never guesses).
        }

        return new CgContext
        {
            SchemaVersion = "cg-context-1",
            Project = raw.Project,
            Definition = raw.Definition,
            Object = cgObject,
            Algorithms = algorithms,
            Nodes = raw.Nodes,
            Wires = raw.Wires,
        };
    }

    /// <summary>
    /// Decomposes an NN token into its algorithm digit and procedure ordinal
    /// (e.g. "11" -&gt; alg 1, ordinal 1; "12" -&gt; alg 1, ordinal 2).
    /// </summary>
    private static (int Algorithm, int ProcedureOrdinal) SplitNn(string nn)
    {
        var algDigit = int.Parse(nn.Substring(0, 1), CultureInfo.InvariantCulture);
        var ordinal = int.Parse(nn.Substring(1), CultureInfo.InvariantCulture);
        return (algDigit, ordinal);
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

    private static string ProcedureId(int alg, string nn) => $"cg:{alg}:proc:{nn}";

    private static string PatternId(int alg, string nn, string idx) => $"cg:{alg}:pat:{nn}_{idx}";

    private static string ParamId(int alg, string kindLiteral, string nickname) => $"cg:{alg}:{kindLiteral}:{nickname}";

    private static string InterfaceId(int alg, string nn, string name) => $"cg:{alg}:intf:{nn}_{name}";
}
