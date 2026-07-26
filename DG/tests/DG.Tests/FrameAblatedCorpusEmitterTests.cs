using System.Diagnostics;
using System.Globalization;
using System.Security.Cryptography;
using System.Text;
using System.Text.Json;
using System.Text.RegularExpressions;
using DG.Core.Models.Computgraph;
using DG.Core.Parsing;
using DG.Core.Serialization;

namespace DG.Tests;

/// <summary>
/// Phase 35-11: the Corpus A generator (35-AI-SPEC.md &#167;5 "Reference Dataset", Option 1).
/// One test, four steps: load the tagged Frame fixture, derive the reference blocks from its
/// entity groups, ablate those groups into non-conforming (untagged) nicknames, then parse +
/// serialize the ablated canvas through the production path. Input and reference are emitted by
/// this one generator from one source, so they cannot drift -- this file is the audit trail.
/// <para>
/// The generator is C#, not Python (AI-SPEC's <c>scripts/build_frame_ablated.py</c> filename):
/// the RawCanvas =&gt; cgContextJson v1 path is <see cref="CanvasAnnotationParser"/> +
/// <see cref="ComputgraphContextSerializer"/>, both C#-only. A Python reimplementation of the
/// production serializer would make the corpus worse than the drift it exists to prevent.
/// </para>
/// </summary>
public sealed class FrameAblatedCorpusEmitterTests
{
    private static readonly JsonSerializerOptions FixtureReadOptions = new()
    {
        PropertyNamingPolicy = JsonNamingPolicy.CamelCase,
    };

    private static readonly JsonSerializerOptions ReferenceWriteOptions = new()
    {
        PropertyNamingPolicy = JsonNamingPolicy.CamelCase,
        WriteIndented = true,
    };

    // Local copies of DG.Core.Parsing.CanvasAnnotationParser's private grammar regexes
    // (RESEARCH.md &#167;4). Duplicated deliberately: this emitter classifies the SOURCE fixture's
    // entity groups to build the reference file, which is a distinct concern from the production
    // parser classifying the ABLATED canvas -- the latter is exercised for real below via
    // CanvasAnnotationParser.Parse. The two must agree on the grammar, not share an implementation.
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

    private static readonly Regex EntityGroupRegex = new(
        @"^\d{2}_(Pat|Var|Const|Emg|Emr|IntF)_",
        RegexOptions.Compiled | RegexOptions.CultureInvariant);

    private static readonly Regex ProcedureGroupRegex = new(
        @"^\d+_Proc - ",
        RegexOptions.Compiled | RegexOptions.CultureInvariant);

    private static readonly Regex ConventionRegex = new(
        @"^\d{2}_(Proc|Pat|Var|Const|Emg|Emr|IntF)",
        RegexOptions.Compiled | RegexOptions.CultureInvariant);

    /// <summary>
    /// Tags authored 2026-07-08 (Fixtures/frame-cg-context.json definition.capturedAt;
    /// 35-05-SUMMARY.md). A fixed literal, not "now" -- so the reference stays byte-stable across
    /// every future test run regardless of what day it happens to execute.
    /// </summary>
    private const string AnnotatedAt = "2026-07-08";

    [Fact]
    public void EmitFrameAblatedCorpus_MatchesCommittedGoldenFiles()
    {
        var repoRoot = FindRepoRoot();
        var contextPath = Path.Combine(repoRoot, "data-service", "fixtures", "recognition_eval", "frame_ablated.context.json");
        var referencePath = Path.Combine(repoRoot, "data-service", "fixtures", "recognition_eval", "frame_ablated.expected.json");

        var fixturePath = Path.Combine(AppContext.BaseDirectory, "Fixtures", "frame-cg-context.json");
        var raw = JsonSerializer.Deserialize<RawCanvas>(File.ReadAllText(fixturePath), FixtureReadOptions);
        Assert.NotNull(raw);

        // Baseline: whatever is already committed, captured BEFORE this run writes anything.
        var baselineContextJson = File.Exists(contextPath) ? File.ReadAllText(contextPath) : null;
        var baselineReferenceJson = File.Exists(referencePath) ? File.ReadAllText(referencePath) : null;

        var (contextJson, referenceJson, context, blocks, abstainEntries) =
            GenerateCorpus(raw!, repoRoot, referencePath);

        Directory.CreateDirectory(Path.GetDirectoryName(contextPath)!);
        File.WriteAllText(contextPath, contextJson);
        File.WriteAllText(referencePath, referenceJson);

        // Idempotency: regenerating now that both files exist must reproduce them byte-for-byte.
        // frozenAtCommit and annotatedAt are pinned metadata, read back and reused rather than
        // recomputed -- see GenerateCorpus -- so this proves the rest of the pipeline (blocks,
        // memberIds, kind, publishable, the ablated context) is a pure function of the frozen
        // source fixture.
        var (contextJson2, referenceJson2, _, _, _) = GenerateCorpus(raw!, repoRoot, referencePath);
        Assert.Equal(contextJson, contextJson2);
        Assert.Equal(referenceJson, referenceJson2);

        // Golden-file equality against whatever was already committed.
        if (baselineContextJson is not null)
        {
            Assert.True(
                Normalize(contextJson) == Normalize(baselineContextJson),
                "frame_ablated.context.json drifted from the committed golden file -- re-run " +
                "FrameAblatedCorpusEmitterTests and commit both frame_ablated.context.json and " +
                "frame_ablated.expected.json together.");
        }

        if (baselineReferenceJson is not null)
        {
            Assert.True(
                Normalize(referenceJson) == Normalize(baselineReferenceJson),
                "frame_ablated.expected.json drifted from the committed golden file -- re-run " +
                "FrameAblatedCorpusEmitterTests and commit both frame_ablated.context.json and " +
                "frame_ablated.expected.json together.");
        }

        // -- Acceptance minimums (35-AI-SPEC.md ��5) --

        Assert.NotNull(context.Object);
        Assert.Single(context.Algorithms);
        var algorithm = context.Algorithms[0];
        Assert.Equal(2, algorithm.Procedures.Count);
        Assert.All(algorithm.Procedures, p =>
        {
            Assert.Empty(p.Patterns);
            Assert.Empty(p.Parameters);
            Assert.Empty(p.Interfaces);
        });

        Assert.All(context.Untagged.Groups, g =>
            Assert.False(ConventionRegex.IsMatch(g.Nickname), $"untagged group '{g.Nickname}' still matches the tagged convention"));

        Assert.True(blocks.Count >= 28, $"expected >= 28 reference blocks, found {blocks.Count}");
        Assert.Equal(3, abstainEntries.Count);
        Assert.Contains(blocks, b => b.HostBlockId is not null);

        using var referenceDoc = JsonDocument.Parse(referenceJson);
        var root = referenceDoc.RootElement;
        Assert.False(root.GetProperty("tier0Evidence").GetBoolean());
        Assert.Equal("own", root.GetProperty("ipClass").GetString());
        Assert.Equal(1, root.GetProperty("corpusVersion").GetInt32());
        Assert.False(string.IsNullOrWhiteSpace(root.GetProperty("contextSha256").GetString()));

        using var contextDoc = JsonDocument.Parse(contextJson);
        Assert.True(contextDoc.RootElement.TryGetProperty("algorithms", out _));
        Assert.True(contextDoc.RootElement.TryGetProperty("untagged", out _));
    }

    private static (string ContextJson, string ReferenceJson, CgContext Context, List<ReferenceBlock> Blocks, List<AbstainEntry> AbstainEntries)
        GenerateCorpus(RawCanvas raw, string repoRoot, string referencePath)
    {
        var entityGroups = raw.Groups
            .Where(g => EntityGroupRegex.IsMatch(g.Nickname ?? string.Empty))
            .OrderBy(g => g.Nickname, StringComparer.Ordinal)
            .ToList();

        var blockIdByGroup = new Dictionary<RawGroup, string>();
        for (var i = 0; i < entityGroups.Count; i++)
        {
            blockIdByGroup[entityGroups[i]] = $"b{i + 1:D2}";
        }

        var blocks = new List<ReferenceBlock>();
        foreach (var group in entityGroups)
        {
            var (kind, procedureIndex, name) = ClassifyEntityGroup(group.Nickname);
            var hostBlockId = FindHostBlockId(group, entityGroups, blockIdByGroup);
            var publishable = ComputePublishable(kind, group, raw.Nodes);

            blocks.Add(new ReferenceBlock(
                blockIdByGroup[group],
                kind,
                procedureIndex,
                name,
                group.MemberIds.OrderBy(m => m, StringComparer.Ordinal).ToList(),
                hostBlockId,
                publishable));
        }

        var abstainEntries = new List<AbstainEntry>
        {
            new(
                new List<string> { "n-untagged-01" },
                "isolated panel, no wires in or out -- cannot distinguish a constant from an abandoned experiment"),
            new(
                new List<string> { "n-scratch-01" },
                "member of the non-conforming 'Scratch notes' group, no wires in or out -- a text annotation, not a functional component"),
            new(
                new List<string> { "n-scratch-02" },
                "member of the non-conforming 'Scratch notes' group, no wires in or out -- a text annotation, not a functional component"),
        };

        // Ablate: keep both scribbles (via ablatedRaw.Scribbles = raw.Scribbles below), keep the
        // two _Proc groups verbatim, replace every entity group with a non-conforming (lower-cased,
        // NN/kind-token-stripped) nickname so the parser routes it to untagged.groups.
        // Non-conforming groups (e.g. "Scratch notes") already fail the convention and pass
        // through untouched. All nodes and wires are kept.
        var ablatedGroups = new List<RawGroup>();
        foreach (var group in raw.Groups)
        {
            var nickname = group.Nickname ?? string.Empty;

            if (ProcedureGroupRegex.IsMatch(nickname))
            {
                ablatedGroups.Add(group);
                continue;
            }

            if (EntityGroupRegex.IsMatch(nickname))
            {
                var (_, _, semanticName) = ClassifyEntityGroup(nickname);
                ablatedGroups.Add(new RawGroup
                {
                    Nickname = semanticName.ToLowerInvariant(),
                    MemberIds = new List<string>(group.MemberIds),
                });
                continue;
            }

            ablatedGroups.Add(group);
        }

        var ablatedRaw = new RawCanvas
        {
            Definition = raw.Definition,
            Project = raw.Project,
            Nodes = raw.Nodes,
            Wires = raw.Wires,
            Groups = ablatedGroups,
            Scribbles = raw.Scribbles,
        };

        var context = CanvasAnnotationParser.Parse(ablatedRaw);
        var contextJson = ComputgraphContextSerializer.Serialize(context);
        var contextSha256 = ComputeSha256Hex(contextJson);

        // frozenAtCommit is pinned at true emit time (the first run that creates the reference
        // file) and reused on every later run. HEAD moves with every commit on this shared tree,
        // so recomputing it on each `dotnet test` invocation would make the golden-file
        // comparison fail forever starting with the very next unrelated commit.
        string frozenAtCommit;
        if (File.Exists(referencePath))
        {
            using var existingDoc = JsonDocument.Parse(File.ReadAllText(referencePath));
            frozenAtCommit = existingDoc.RootElement.TryGetProperty("frozenAtCommit", out var el)
                && el.ValueKind == JsonValueKind.String
                    ? el.GetString() ?? "unfrozen"
                    : "unfrozen";
        }
        else
        {
            frozenAtCommit = TryGetGitHeadCommit(repoRoot) ?? "unfrozen";
        }

        var reference = new CorpusReference(
            "frame_ablated",
            "frame_ablated.context.json",
            contextSha256,
            "architect-researcher",
            AnnotatedAt,
            frozenAtCommit,
            "own",
            false,
            1,
            blocks,
            abstainEntries);

        var referenceJson = JsonSerializer.Serialize(reference, ReferenceWriteOptions);

        return (contextJson, referenceJson, context, blocks, abstainEntries);
    }

    private static (string Kind, int ProcedureIndex, string Name) ClassifyEntityGroup(string nickname)
    {
        var patternMatch = PatternRegex.Match(nickname);
        if (patternMatch.Success)
        {
            var idx = patternMatch.Groups["idx"].Value;
            var name = patternMatch.Groups["name"].Success
                ? $"{idx} {patternMatch.Groups["name"].Value.Trim()}"
                : idx;
            return ("Pattern", int.Parse(patternMatch.Groups["nn"].Value, CultureInfo.InvariantCulture), name);
        }

        var variableMatch = VariableRegex.Match(nickname);
        if (variableMatch.Success)
        {
            return ("VariableParam", int.Parse(variableMatch.Groups["nn"].Value, CultureInfo.InvariantCulture), variableMatch.Groups["name"].Value.Trim());
        }

        var constantMatch = ConstantRegex.Match(nickname);
        if (constantMatch.Success)
        {
            return ("ConstantParam", int.Parse(constantMatch.Groups["nn"].Value, CultureInfo.InvariantCulture), constantMatch.Groups["name"].Value.Trim());
        }

        var emergentMatch = EmergentRegex.Match(nickname);
        if (emergentMatch.Success)
        {
            return ("EmergentParam", int.Parse(emergentMatch.Groups["nn"].Value, CultureInfo.InvariantCulture), emergentMatch.Groups["name"].Value.Trim());
        }

        var interfaceMatch = InterfaceRegex.Match(nickname);
        if (interfaceMatch.Success)
        {
            return ("Interface", int.Parse(interfaceMatch.Groups["nn"].Value, CultureInfo.InvariantCulture), interfaceMatch.Groups["name"].Value.Trim());
        }

        throw new InvalidOperationException(
            $"Group '{nickname}' matched EntityGroupRegex but no specific classifier -- grammar drift between this emitter and CanvasAnnotationParser.");
    }

    private static bool ComputePublishable(string kind, RawGroup group, List<CgNode> allNodes)
    {
        if (kind is not ("VariableParam" or "ConstantParam" or "EmergentParam"))
        {
            return true;
        }

        var memberNodes = allNodes.Where(n => group.MemberIds.Contains(n.InstanceId));
        var (dataType, _, _) = CanvasAnnotationParser.TryInferParameterDataType(group.Nickname, memberNodes);
        return dataType.HasValue;
    }

    private static string? FindHostBlockId(RawGroup group, List<RawGroup> entityGroups, Dictionary<RawGroup, string> blockIdByGroup)
    {
        var host = entityGroups.FirstOrDefault(g =>
            !ReferenceEquals(g, group) && g.NestedGroupIds.Contains(group.Nickname));
        return host is not null ? blockIdByGroup[host] : null;
    }

    private static string ComputeSha256Hex(string content)
    {
        var hash = SHA256.HashData(Encoding.UTF8.GetBytes(content));
        return Convert.ToHexString(hash).ToLowerInvariant();
    }

    private static string? TryGetGitHeadCommit(string repoRoot)
    {
        try
        {
            var psi = new ProcessStartInfo("git", "rev-parse HEAD")
            {
                WorkingDirectory = repoRoot,
                RedirectStandardOutput = true,
                RedirectStandardError = true,
                UseShellExecute = false,
            };

            using var process = Process.Start(psi);
            if (process is null)
            {
                return null;
            }

            var output = process.StandardOutput.ReadToEnd().Trim();
            process.WaitForExit(5000);
            return process.ExitCode == 0 && output.Length == 40 ? output : null;
        }
        catch
        {
            return null;
        }
    }

    private static string FindRepoRoot()
    {
        var dir = new DirectoryInfo(AppContext.BaseDirectory);
        while (dir is not null && !Directory.Exists(Path.Combine(dir.FullName, ".git")))
        {
            dir = dir.Parent;
        }

        if (dir is null)
        {
            throw new InvalidOperationException(
                $"Could not locate repository root (no .git ancestor) from '{AppContext.BaseDirectory}'.");
        }

        return dir.FullName;
    }

    private static string Normalize(string s) => s.Replace("\r\n", "\n").Trim();

    private sealed record ReferenceBlock(
        string Id,
        string Kind,
        int ProcedureIndex,
        string Name,
        List<string> MemberIds,
        string? HostBlockId,
        bool Publishable);

    private sealed record AbstainEntry(List<string> MemberIds, string Reason);

    private sealed record CorpusReference(
        string Corpus,
        string SourceContext,
        string ContextSha256,
        string AnnotatedBy,
        string AnnotatedAt,
        string FrozenAtCommit,
        string IpClass,
        bool Tier0Evidence,
        int CorpusVersion,
        List<ReferenceBlock> Blocks,
        List<AbstainEntry> AbstainExpected);
}
