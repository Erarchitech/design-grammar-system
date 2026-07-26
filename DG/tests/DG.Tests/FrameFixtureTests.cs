using System.Text.Json;
using DG.Core.Models.Computgraph;
using DG.Core.Parsing;
using DG.Core.Serialization;

namespace DG.Tests;

/// <summary>
/// Phase 32 acceptance proof (CGSR-04): loads the checked-in Frame RawCanvas
/// fixture, runs it through the full parse -> serialize pipeline, and asserts
/// all four Phase 32 success criteria against the OWL named individuals
/// (RESEARCH.md &#167;3). Runs entirely in DG.Core (no Grasshopper SDK reference).
/// </summary>
public sealed class FrameFixtureTests
{
    private static readonly JsonSerializerOptions FixtureOptions = new()
    {
        PropertyNamingPolicy = JsonNamingPolicy.CamelCase,
    };

    private static CgContext ParseFixture()
    {
        var path = Path.Combine(AppContext.BaseDirectory, "Fixtures", "frame-cg-context.json");
        var json = File.ReadAllText(path);
        var raw = JsonSerializer.Deserialize<RawCanvas>(json, FixtureOptions);
        Assert.NotNull(raw);
        return CanvasAnnotationParser.Parse(raw!);
    }

    [Fact]
    public void Parse_FrameFixture_MatchesOwlIndividuals()
    {
        var context = ParseFixture();

        // dg:Object_Frame
        Assert.NotNull(context.Object);
        Assert.Equal("FRAME", context.Object!.Name);

        // dgc:Algorithm_1
        Assert.Single(context.Algorithms);
        var algorithm = context.Algorithms[0];
        Assert.Equal(1, algorithm.Index);

        // dgc:Proc_11 / dgc:Proc_12
        Assert.Equal(2, algorithm.Procedures.Count);
        Assert.Contains(algorithm.Procedures, p => p.Index == 11 && p.Name == "2D Truss Configuration");
        Assert.Contains(algorithm.Procedures, p => p.Index == 12 && p.Name == "2D Footer Configuration");

        var proc11 = algorithm.Procedures.Single(p => p.Index == 11);
        var proc12 = algorithm.Procedures.Single(p => p.Index == 12);

        // Pat_11_DivideLine / Pat_11_TopChord (+ host-chain nesting proof)
        Assert.Contains(proc11.Patterns, p => p.Label == "11_Pat_DivideLine");
        var divideLine = proc11.Patterns.Single(p => p.Label == "11_Pat_DivideLine");
        var topChord = proc11.Patterns.Single(p => p.Label == "11_Pat_TopChord");
        Assert.Equal(divideLine.Id, topChord.HostPatternId);

        // Variable / Constant / Emergent parameters under Proc_11
        Assert.Contains(proc11.Parameters, p => p.Kind == ParamKind.Variable && p.Name == "SpansCount");
        Assert.Contains(proc11.Parameters, p => p.Kind == ParamKind.Variable && p.Name == "HTotal");
        Assert.Contains(proc11.Parameters, p => p.Kind == ParamKind.Constant && p.Name == "ptZero");
        Assert.Contains(proc11.Parameters, p => p.Kind == ParamKind.Emergent && p.Name == "DivPoints");

        // IntF_11_ParSplitAt / IntF_11_TrussConfig / IntF_11_MergeRes
        Assert.Contains(proc11.Interfaces, i => i.Name == "ParSplitAt");
        Assert.Contains(proc11.Interfaces, i => i.Name == "TrussConfig");
        Assert.Contains(proc11.Interfaces, i => i.Name == "MergeRes");

        // Proc_12: Variable HFooter, IntF_12_FooterFrame
        Assert.Contains(proc12.Parameters, p => p.Kind == ParamKind.Variable && p.Name == "HFooter");
        Assert.Contains(proc12.Interfaces, i => i.Name == "FooterFrame");
    }

    [Fact]
    public void Parse_EmrTypo_NormalizesToEmergentAndAppendsWarning()
    {
        var context = ParseFixture();
        var proc11 = context.Algorithms.Single(a => a.Index == 1).Procedures.Single(p => p.Index == 11);

        Assert.Contains(proc11.Parameters, p => p.Kind == ParamKind.Emergent && p.Name == "UpperChord");
        Assert.Contains(context.Warnings, w => w.Contains("Emr", StringComparison.Ordinal) && w.Contains("Emg", StringComparison.Ordinal));
    }

    [Fact]
    public void Parse_IntegerSliderMember_InfersIntegerDataTypeAndDomain()
    {
        var context = ParseFixture();
        var proc11 = context.Algorithms.Single(a => a.Index == 1).Procedures.Single(p => p.Index == 11);

        var spansCount = proc11.Parameters.Single(p => p.Name == "SpansCount");

        Assert.Equal(ParamDataType.Integer, spansCount.DataType);
        Assert.NotNull(spansCount.Domain);
        Assert.Equal(1, spansCount.Domain!.Min);
        Assert.Equal(20, spansCount.Domain!.Max);
        Assert.Equal(1, spansCount.Domain!.Step);
    }

    [Fact]
    public void Parse_NonConformingGroup_LandsInUntagged()
    {
        var context = ParseFixture();

        var scratch = Assert.Single(context.Untagged.Groups, g => g.Nickname == "Scratch notes");
        Assert.Equal(2, scratch.MemberIds.Count);
        Assert.Contains("n-scratch-01", scratch.MemberIds);
        Assert.Contains("n-scratch-02", scratch.MemberIds);

        // No typed entity was fabricated from the non-conforming group.
        var allProcedures = context.Algorithms.SelectMany(a => a.Procedures).ToList();
        Assert.DoesNotContain(allProcedures, p => p.Name == "Scratch notes");
        Assert.DoesNotContain(allProcedures.SelectMany(p => p.Patterns), p => p.Label == "Scratch notes");
        Assert.DoesNotContain(allProcedures.SelectMany(p => p.Parameters), p => p.Name == "Scratch notes");
        Assert.DoesNotContain(allProcedures.SelectMany(p => p.Interfaces), i => i.Name == "Scratch notes");

        // The unclaimed loose node (member of no group at all) lands in Untagged.NodeIds.
        Assert.Contains("n-untagged-01", context.Untagged.NodeIds);
    }

    [Fact]
    public void Serialize_FrameContext_IsIdempotent()
    {
        var context = ParseFixture();

        var s1 = ComputgraphContextSerializer.Serialize(context);
        var roundTripped = ComputgraphContextSerializer.Deserialize(s1);
        var s2 = ComputgraphContextSerializer.Serialize(roundTripped);

        Assert.Equal(s1, s2);
        Assert.Contains("\"schemaVersion\":\"cg-context-1\"", s1, StringComparison.Ordinal);
    }

    private static RawCanvas LoadRawFixture()
    {
        var path = Path.Combine(AppContext.BaseDirectory, "Fixtures", "frame-cg-context.json");
        var raw = JsonSerializer.Deserialize<RawCanvas>(File.ReadAllText(path), FixtureOptions);
        Assert.NotNull(raw);
        return raw!;
    }

    /// <summary>
    /// Phase 35-05 regression guard. These three nodes are the corpus's
    /// <c>abstainExpected</c> set: the honest answer for a fully isolated node is
    /// <c>unrecognized</c>, and they are the only positive test case abstention
    /// recall has. Wiring any of them would silently delete that evidence, and the
    /// deletion would look like an improvement (more nodes classifiable).
    /// </summary>
    [Fact]
    public void Frame_AbstainNodes_StayIsolated()
    {
        var raw = LoadRawFixture();

        foreach (var id in new[] { "n-untagged-01", "n-scratch-01", "n-scratch-02" })
        {
            Assert.DoesNotContain(raw.Wires, w => w.FromNode == id || w.ToNode == id);
        }
    }

    /// <summary>
    /// Phase 35-05 regression guard. Empty procedure membership is the live trigger
    /// for UAT F2 -- per-procedure scoping silently widens to the whole canvas when
    /// the requested procedure has no members, turning an intended 14-node call into
    /// a 214-node one and then into the F1 truncation.
    /// </summary>
    [Fact]
    public void Frame_Procedures_OwnTheirMembers()
    {
        var context = ParseFixture();

        var procedures = context.Algorithms.SelectMany(a => a.Procedures).ToList();

        Assert.Equal(2, procedures.Count);
        Assert.All(procedures, p => Assert.NotEmpty(p.MemberIds));
        Assert.Equal(20, procedures.Single(p => p.Index == 11).MemberIds.Count);
        Assert.Equal(11, procedures.Single(p => p.Index == 12).MemberIds.Count);
    }

    /// <summary>
    /// Phase 35-05: the fixture must carry enough real dataflow for degree to be a
    /// meaningful signal. A single-wire fixture collapses every topology rule to
    /// abstain, which would score the deterministic tier as useless for reasons that
    /// have nothing to do with the rules.
    /// </summary>
    [Fact]
    public void Frame_Fixture_CarriesRealWiring()
    {
        var raw = LoadRawFixture();

        Assert.True(raw.Wires.Count >= 25, $"expected >= 25 wires, found {raw.Wires.Count}");
        Assert.All(raw.Wires, w =>
        {
            Assert.Contains(raw.Nodes, n => n.InstanceId == w.FromNode);
            Assert.Contains(raw.Nodes, n => n.InstanceId == w.ToNode);
        });
    }
}
