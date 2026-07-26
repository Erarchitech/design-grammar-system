using System.Runtime.CompilerServices;
using System.Text.Json;
using DG.Core.Models.Computgraph;
using DG.Core.Parsing;

namespace DG.Tests;

public sealed class CanvasAnnotationParserTests
{
    [Fact]
    public void Parse_NullRawCanvas_ThrowsArgumentNullException()
    {
        Assert.Throws<ArgumentNullException>(() => CanvasAnnotationParser.Parse(null!));
    }

    [Fact]
    public void Parse_ObjectAndAlgorithmScribbles_YieldsObjectAndAlgorithm()
    {
        var raw = new RawCanvas
        {
            Scribbles =
            {
                new RawScribble { Text = "OBJECT - FRAME" },
                new RawScribble { Text = "1_ALGORITHM" },
            },
        };

        var context = CanvasAnnotationParser.Parse(raw);

        Assert.NotNull(context.Object);
        Assert.Equal("FRAME", context.Object!.Name);
        Assert.Single(context.Algorithms);
        Assert.Equal(1, context.Algorithms[0].Index);
    }

    [Fact]
    public void Parse_ProcGroups_YieldsProceduresUnderAlgorithmOne()
    {
        var raw = new RawCanvas
        {
            Scribbles =
            {
                new RawScribble { Text = "OBJECT - FRAME" },
                new RawScribble { Text = "1_ALGORITHM" },
            },
            Groups =
            {
                new RawGroup { Nickname = "11_Proc - 2D Truss Configuration", MemberIds = { "n1", "n2" } },
                new RawGroup { Nickname = "12_Proc - 2D Footer Configuration", MemberIds = { "n3" } },
            },
        };

        var context = CanvasAnnotationParser.Parse(raw);

        Assert.Equal("FRAME", context.Object!.Name);
        Assert.Single(context.Algorithms);
        var algorithm = context.Algorithms[0];
        Assert.Equal(1, algorithm.Index);
        Assert.Equal(2, algorithm.Procedures.Count);
        Assert.Contains(algorithm.Procedures, p => p.Index == 11 && p.Name == "2D Truss Configuration");
        Assert.Contains(algorithm.Procedures, p => p.Index == 12 && p.Name == "2D Footer Configuration");
    }

    [Fact]
    public void Parse_VariableConstantEmergentGroups_YieldsCorrectParamKinds()
    {
        var raw = new RawCanvas
        {
            Groups =
            {
                new RawGroup { Nickname = "11_Proc - 2D Truss Configuration" },
                new RawGroup { Nickname = "11_Var_SpansCount" },
                new RawGroup { Nickname = "11_Const_ptZero" },
                new RawGroup { Nickname = "11_Emg_DivPoints" },
            },
        };

        var context = CanvasAnnotationParser.Parse(raw);

        var procedure = context.Algorithms.Single().Procedures.Single(p => p.Index == 11);
        Assert.Contains(procedure.Parameters, p => p.Kind == ParamKind.Variable && p.Name == "SpansCount");
        Assert.Contains(procedure.Parameters, p => p.Kind == ParamKind.Constant && p.Name == "ptZero");
        Assert.Contains(procedure.Parameters, p => p.Kind == ParamKind.Emergent && p.Name == "DivPoints");
    }

    [Fact]
    public void Parse_InterfaceGroup_YieldsInterfaceWithName()
    {
        var raw = new RawCanvas
        {
            Groups = { new RawGroup { Nickname = "11_IntF_ParSplitAt" } },
        };

        var context = CanvasAnnotationParser.Parse(raw);

        var procedure = context.Algorithms.Single().Procedures.Single(p => p.Index == 11);
        Assert.Contains(procedure.Interfaces, i => i.Name == "ParSplitAt");
    }

    [Fact]
    public void Parse_CyrillicVariableName_RoundTripsVerbatim()
    {
        var raw = new RawCanvas
        {
            Groups = { new RawGroup { Nickname = "11_Var_Высота" } },
        };

        var context = CanvasAnnotationParser.Parse(raw);

        var procedure = context.Algorithms.Single().Procedures.Single(p => p.Index == 11);
        Assert.Contains(procedure.Parameters, p => p.Name == "Высота");
    }

    [Fact]
    public void Parse_NonAnchoredJunkPrefix_DoesNotMatchGrammar()
    {
        var raw = new RawCanvas
        {
            Scribbles = { new RawScribble { Text = "xxxOBJECT - FRAME" } },
            Groups = { new RawGroup { Nickname = "xx11_Proc - Junk", MemberIds = { "n1" } } },
        };

        var context = CanvasAnnotationParser.Parse(raw);

        Assert.Null(context.Object);
        Assert.Empty(context.Algorithms);
        Assert.Single(context.Untagged.Groups);
        Assert.Equal("xx11_Proc - Junk", context.Untagged.Groups[0].Nickname);
    }

    [Fact]
    public void CanvasAnnotationParserSource_UsesCompiledAnchoredGrammarRegexes()
    {
        var source = File.ReadAllText(GetParserSourcePath());

        Assert.Contains("RegexOptions.Compiled", source);
        Assert.Contains("\"^OBJECT - (?<name>.+)$\"", source);
        Assert.Contains("@\"^(?<alg>\\d+)_ALGORITHM$\"", source);
        Assert.Contains("@\"^(?<nn>\\d+)_Proc - (?<name>.+)$\"", source);
        Assert.Contains("@\"^(?<nn>\\d+)_Pat_(?<idx>[^ ]+)( (?<name>.+))?$\"", source);
        Assert.Contains("@\"^(?<nn>\\d+)_Var_(?<name>.+)$\"", source);
        Assert.Contains("@\"^(?<nn>\\d+)_Const_(?<name>.+)$\"", source);
        Assert.Contains("@\"^(?<nn>\\d+)_(?<tag>Emg|Emr)_(?<name>.+)$\"", source);
        Assert.Contains("@\"^(?<nn>\\d+)_IntF_(?<name>.+)$\"", source);
    }

    // --- Task 2: untagged routing, Emr tolerance, pattern nesting, dataType/domain inference ---

    [Fact]
    public void Parse_NonConformingGroupNickname_RoutesToUntaggedWithMembersIntactAndNoTypedEntity()
    {
        var raw = new RawCanvas
        {
            Groups = { new RawGroup { Nickname = "My scratch group", MemberIds = { "u1", "u2" } } },
        };

        var context = CanvasAnnotationParser.Parse(raw);

        Assert.Empty(context.Algorithms);
        var untaggedGroup = Assert.Single(context.Untagged.Groups);
        Assert.Equal("My scratch group", untaggedGroup.Nickname);
        Assert.Equal(new List<string> { "u1", "u2" }, untaggedGroup.MemberIds);
    }

    [Fact]
    public void Parse_UnclaimedNode_AppearsInUntaggedNodeIds()
    {
        var raw = new RawCanvas
        {
            Groups = { new RawGroup { Nickname = "11_Var_SpansCount", MemberIds = { "claimed1" } } },
            Nodes =
            {
                new CgNode { InstanceId = "claimed1", Name = "Number Slider" },
                new CgNode { InstanceId = "orphan1", Name = "Panel" },
            },
        };

        var context = CanvasAnnotationParser.Parse(raw);

        Assert.Contains("orphan1", context.Untagged.NodeIds);
        Assert.DoesNotContain("claimed1", context.Untagged.NodeIds);
    }

    [Fact]
    public void Parse_EmrTypo_NormalizesToEmergentAndAppendsWarning()
    {
        var raw = new RawCanvas
        {
            Groups = { new RawGroup { Nickname = "11_Emr_UpperChord" } },
        };

        var context = CanvasAnnotationParser.Parse(raw);

        var procedure = context.Algorithms.Single().Procedures.Single(p => p.Index == 11);
        Assert.Contains(procedure.Parameters, p => p.Kind == ParamKind.Emergent && p.Name == "UpperChord");
        Assert.Contains(context.Warnings, w => w.Contains("Emr") && w.Contains("Emg"));
    }

    [Fact]
    public void Parse_NestedPatternGroup_ResolvesHostPatternId()
    {
        var raw = new RawCanvas
        {
            Groups =
            {
                new RawGroup
                {
                    Nickname = "11_Pat_TrussFrame",
                    MemberIds = { "h1" },
                    NestedGroupIds = { "11_Pat_TopChord" },
                },
                new RawGroup { Nickname = "11_Pat_TopChord", MemberIds = { "c1" } },
            },
        };

        var context = CanvasAnnotationParser.Parse(raw);

        var procedure = context.Algorithms.Single().Procedures.Single(p => p.Index == 11);
        var host = procedure.Patterns.Single(p => p.Label == "11_Pat_TrussFrame");
        var child = procedure.Patterns.Single(p => p.Label == "11_Pat_TopChord");

        Assert.Equal(host.Id, child.HostPatternId);
    }

    [Fact]
    public void Parse_IntegerSliderMember_InfersIntegerDataTypeAndDomain()
    {
        var raw = new RawCanvas
        {
            Groups = { new RawGroup { Nickname = "11_Var_SpansCount", MemberIds = { "s1" } } },
            Nodes =
            {
                new CgNode
                {
                    InstanceId = "s1",
                    Name = "Number Slider",
                    Slider = new SliderDomain { Min = 1, Max = 20, Step = 1 },
                    IsIntegerSlider = true,
                },
            },
        };

        var context = CanvasAnnotationParser.Parse(raw);

        var parameter = context.Algorithms.Single().Procedures.Single(p => p.Index == 11)
            .Parameters.Single(p => p.Name == "SpansCount");

        Assert.Equal(ParamDataType.Integer, parameter.DataType);
        Assert.NotNull(parameter.Domain);
        Assert.Equal(1, parameter.Domain!.Min);
        Assert.Equal(20, parameter.Domain.Max);
        Assert.Equal(1, parameter.Domain.Step);
    }

    [Fact]
    public void Parse_ConflictingMemberComponentTypes_UsesPrecedenceAndAppendsWarning()
    {
        var raw = new RawCanvas
        {
            Groups = { new RawGroup { Nickname = "11_Var_Mode", MemberIds = { "panel1", "slider1" } } },
            Nodes =
            {
                new CgNode { InstanceId = "panel1", Name = "Panel" },
                new CgNode
                {
                    InstanceId = "slider1",
                    Name = "Number Slider",
                    Slider = new SliderDomain { Min = 0, Max = 1, Step = 0.1 },
                    IsIntegerSlider = false,
                },
            },
        };

        var context = CanvasAnnotationParser.Parse(raw);

        var parameter = context.Algorithms.Single().Procedures.Single(p => p.Index == 11)
            .Parameters.Single(p => p.Name == "Mode");

        Assert.Equal(ParamDataType.Float, parameter.DataType);
        Assert.Contains(context.Warnings, w => w.Contains("Mode") && w.Contains("conflicting"));
    }

    [Fact]
    public void Parse_BareNumberMember_InfersFloatDataTypeWithoutWarning()
    {
        // F5 repro: a bare Number component is an ordinary Constant source, but it used to infer
        // no dataType at all -- which 422s the entire publish payload.
        var raw = new RawCanvas
        {
            Groups = { new RawGroup { Nickname = "12_Const_Num", MemberIds = { "n1" } } },
            Nodes = { new CgNode { InstanceId = "n1", Name = "Number" } },
        };

        var context = CanvasAnnotationParser.Parse(raw);

        var parameter = context.Algorithms.Single().Procedures.Single(p => p.Index == 12)
            .Parameters.Single(p => p.Name == "Num");

        Assert.Equal(ParamDataType.Float, parameter.DataType);
        Assert.Empty(context.Warnings);
    }

    [Theory]
    [InlineData("Integer", ParamDataType.Integer)]
    [InlineData("Text", ParamDataType.Text)]
    [InlineData("Brep", ParamDataType.Geometry)]
    [InlineData("Curve", ParamDataType.Geometry)]
    public void Parse_BarePrimitiveParamMember_InfersMatchingDataType(string componentName, ParamDataType expected)
    {
        var raw = new RawCanvas
        {
            Groups = { new RawGroup { Nickname = "11_Emg_Result", MemberIds = { "p1" } } },
            Nodes = { new CgNode { InstanceId = "p1", Name = componentName } },
        };

        var context = CanvasAnnotationParser.Parse(raw);

        var parameter = context.Algorithms.Single().Procedures.Single(p => p.Index == 11)
            .Parameters.Single(p => p.Name == "Result");

        Assert.Equal(expected, parameter.DataType);
    }

    [Fact]
    public void Parse_SliderAndBareNumberMembers_PrefersSliderWithoutConflictWarning()
    {
        var raw = new RawCanvas
        {
            Groups = { new RawGroup { Nickname = "11_Var_SpanWidth", MemberIds = { "s1", "n1" } } },
            Nodes =
            {
                new CgNode
                {
                    InstanceId = "s1",
                    Name = "Number Slider",
                    Slider = new SliderDomain { Min = 0, Max = 10, Step = 0.5 },
                    IsIntegerSlider = false,
                },
                new CgNode { InstanceId = "n1", Name = "Number" },
            },
        };

        var context = CanvasAnnotationParser.Parse(raw);

        var parameter = context.Algorithms.Single().Procedures.Single(p => p.Index == 11)
            .Parameters.Single(p => p.Name == "SpanWidth");

        Assert.Equal(ParamDataType.Float, parameter.DataType);
        Assert.NotNull(parameter.Domain);
        Assert.DoesNotContain(context.Warnings, w => w.Contains("conflicting"));
    }

    [Fact]
    public void Parse_UntypeableMember_LeavesDataTypeNullButWarns()
    {
        var raw = new RawCanvas
        {
            Groups = { new RawGroup { Nickname = "11_Const_Mystery", MemberIds = { "x1" } } },
            Nodes = { new CgNode { InstanceId = "x1", Name = "Series" } },
        };

        var context = CanvasAnnotationParser.Parse(raw);

        var parameter = context.Algorithms.Single().Procedures.Single(p => p.Index == 11)
            .Parameters.Single(p => p.Name == "Mystery");

        Assert.Null(parameter.DataType);
        Assert.Contains(
            context.Warnings,
            w => w.Contains("11_Const_Mystery") && w.Contains("dataType is unset"));
    }

    [Fact]
    public void Parse_CyclicPatternNesting_StopsWithWarningInsteadOfHanging()
    {
        var raw = new RawCanvas
        {
            Groups =
            {
                new RawGroup { Nickname = "11_Pat_A", MemberIds = { "a1" }, NestedGroupIds = { "11_Pat_B" } },
                new RawGroup { Nickname = "11_Pat_B", MemberIds = { "b1" }, NestedGroupIds = { "11_Pat_A" } },
            },
        };

        var context = CanvasAnnotationParser.Parse(raw);

        Assert.Contains(
            context.Warnings,
            w => w.Contains("exceeded max depth") || w.Contains("cycle"));
    }

    [Theory]
    [InlineData("1_Proc - Foo")]
    [InlineData("1_Pat_1")]
    [InlineData("1_Var_X")]
    [InlineData("1_Const_X")]
    [InlineData("1_Emg_X")]
    [InlineData("1_IntF_X")]
    [InlineData("99999999999_Proc - Overflow")] // digits overflow int -- same non-throw guarantee
    public void Parse_MalformedNnToken_RoutesGroupToUntaggedWithWarningInsteadOfThrowing(string nickname)
    {
        // WR-04: a user-typed single-digit NN matches the grammar regexes (\d+) but
        // cannot be decomposed into algorithm digit + procedure ordinal. The old
        // SplitNn threw FormatException out of Parse(), taking down the entire
        // canvas-context extraction over one malformed nickname.
        var raw = new RawCanvas
        {
            Groups =
            {
                new RawGroup { Nickname = nickname, MemberIds = { "n1" } },
            },
        };

        var context = CanvasAnnotationParser.Parse(raw);

        var untagged = Assert.Single(context.Untagged.Groups);
        Assert.Equal(nickname, untagged.Nickname);
        Assert.Equal(new[] { "n1" }, untagged.MemberIds);
        Assert.Empty(context.Algorithms); // no phantom algorithm/procedure minted from a bad NN
        Assert.Contains(context.Warnings, w => w.Contains(nickname) && w.Contains("NN token"));
    }

    private static string GetParserSourcePath([CallerFilePath] string testFilePath = "")
    {
        var testsDir = Path.GetDirectoryName(testFilePath)!;
        return Path.GetFullPath(Path.Combine(testsDir, "..", "..", "src", "DG.Core", "Parsing", "CanvasAnnotationParser.cs"));
    }

    // ── Phase 35-09: TryInferParameterDataType public seam (guardrail G12) ──

    private static CgNode Node(string id, string name, SliderDomain? slider = null, bool isInt = false) =>
        new() { InstanceId = id, Name = name, Nickname = id, Slider = slider, IsIntegerSlider = isInt };

    [Fact]
    public void TryInferParameterDataType_SliderMember_YieldsDataTypeAndDomain()
    {
        var domain = new SliderDomain { Min = 1, Max = 20, Step = 1 };
        var (dataType, resolved, warning) = CanvasAnnotationParser.TryInferParameterDataType(
            "11_Var_SpansCount", new[] { Node("n1", "Number Slider", domain, isInt: true) });

        Assert.Equal(ParamDataType.Integer, dataType);
        Assert.NotNull(resolved);
        Assert.Null(warning);
    }

    [Fact]
    public void TryInferParameterDataType_BareNumberMember_YieldsFloat()
    {
        // The F5 case, fixed in 028ff0e: a bare Number is an entirely ordinary
        // Constant source and used to yield a silent null dataType.
        var (dataType, domain, warning) = CanvasAnnotationParser.TryInferParameterDataType(
            "12_Const_Num", new[] { Node("n1", "Number") });

        Assert.Equal(ParamDataType.Float, dataType);
        Assert.Null(domain);
        Assert.Null(warning);
    }

    [Fact]
    public void TryInferParameterDataType_UntypeableMember_YieldsNullWithWarning()
    {
        // A component in neither the widget nor the primitive tier. This is what the
        // accept-time gate must block on -- publishing it would 422 the whole payload.
        var (dataType, domain, warning) = CanvasAnnotationParser.TryInferParameterDataType(
            "11_Const_Mystery", new[] { Node("n1", "Solar Position") });

        Assert.Null(dataType);
        Assert.Null(domain);
        Assert.NotNull(warning);
        Assert.Contains("dataType is unset", warning!, StringComparison.Ordinal);
    }

    [Fact]
    public void TryInferParameterDataType_NoMembers_StaysQuiet()
    {
        // Tag-then-populate is a normal authoring workflow, so an empty group must not
        // warn -- the publish component's pre-flight catches those instead.
        var (dataType, domain, warning) = CanvasAnnotationParser.TryInferParameterDataType(
            "11_Var_Empty", Array.Empty<CgNode>());

        Assert.Null(dataType);
        Assert.Null(domain);
        Assert.Null(warning);
    }

    // ── Phase 35-16: ComputeHostPatternIds order-independence fix ──
    // Found during 35-05: a Procedure group's NestedGroupIds legitimately names a
    // transitively-nested pattern (real GH containment is transitive), and when that
    // Procedure group appears earlier in RawCanvas.Groups than the true parent pattern,
    // the old FirstOrDefault-over-document-order picked the Procedure, the idByGroup
    // lookup missed (a Procedure isn't a pending pattern), the strict-superset fallback
    // found nothing, and the nesting was silently dropped.

    private static CgContext ParseFrameFixtureForHostTests()
    {
        var path = Path.Combine(AppContext.BaseDirectory, "Fixtures", "frame-cg-context.json");
        var json = File.ReadAllText(path);
        var options = new JsonSerializerOptions { PropertyNamingPolicy = JsonNamingPolicy.CamelCase };
        var raw = JsonSerializer.Deserialize<RawCanvas>(json, options);
        Assert.NotNull(raw);
        return CanvasAnnotationParser.Parse(raw!);
    }

    [Fact]
    public void ComputeHostPatternIds_ProcedureNamesTransitivelyNestedPattern_DoesNotHijackHost()
    {
        var raw = new RawCanvas
        {
            Groups =
            {
                new RawGroup
                {
                    Nickname = "11_Proc - Truss",
                    NestedGroupIds = { "11_Pat_Outer", "11_Pat_Inner" },
                },
                new RawGroup
                {
                    Nickname = "11_Pat_Outer",
                    MemberIds = { "n-a" },
                    NestedGroupIds = { "11_Pat_Inner" },
                },
                new RawGroup { Nickname = "11_Pat_Inner", MemberIds = { "n-b" } },
            },
        };

        var context = CanvasAnnotationParser.Parse(raw);
        var proc = context.Algorithms.Single().Procedures.Single(p => p.Index == 11);
        var outer = proc.Patterns.Single(p => p.Label == "11_Pat_Outer");
        var inner = proc.Patterns.Single(p => p.Label == "11_Pat_Inner");

        Assert.Equal(outer.Id, inner.HostPatternId);
    }

    [Fact]
    public void ComputeHostPatternIds_IsOrderIndependent_AcrossGroupPermutations()
    {
        RawGroup Proc() => new()
        {
            Nickname = "11_Proc - Truss",
            NestedGroupIds = { "11_Pat_Outer", "11_Pat_Inner" },
        };
        RawGroup Outer() => new()
        {
            Nickname = "11_Pat_Outer",
            MemberIds = { "n-a" },
            NestedGroupIds = { "11_Pat_Inner" },
        };
        RawGroup Inner() => new() { Nickname = "11_Pat_Inner", MemberIds = { "n-b" } };

        var permutations = new List<List<RawGroup>>
        {
            new() { Proc(), Outer(), Inner() },
            new() { Outer(), Proc(), Inner() },
            new() { Inner(), Outer(), Proc() },
            new() { Inner(), Proc(), Outer() },
        };

        foreach (var groups in permutations)
        {
            var raw = new RawCanvas { Groups = groups };
            var context = CanvasAnnotationParser.Parse(raw);
            var proc = context.Algorithms.Single().Procedures.Single(p => p.Index == 11);
            var inner = proc.Patterns.Single(p => p.Label == "11_Pat_Inner");
            var host = proc.Patterns.Single(p => p.Id == inner.HostPatternId);

            Assert.Equal("11_Pat_Outer", host.Label);
        }
    }

    [Fact]
    public void ComputeHostPatternIds_TransitiveDoubleNaming_InnermostPatternWins()
    {
        // A ⊃ B ⊃ C, with A AND B both naming C in NestedGroupIds (transitive
        // containment). The correct host is the immediate parent B, not the
        // outermost ancestor A.
        var raw = new RawCanvas
        {
            Groups =
            {
                new RawGroup
                {
                    Nickname = "11_Pat_A",
                    MemberIds = { "a1", "a2", "a3" },
                    NestedGroupIds = { "11_Pat_B", "11_Pat_C" },
                },
                new RawGroup
                {
                    Nickname = "11_Pat_B",
                    MemberIds = { "b1", "b2" },
                    NestedGroupIds = { "11_Pat_C" },
                },
                new RawGroup { Nickname = "11_Pat_C", MemberIds = { "c1" } },
            },
        };

        var context = CanvasAnnotationParser.Parse(raw);
        var proc = context.Algorithms.Single().Procedures.Single(p => p.Index == 11);
        var a = proc.Patterns.Single(p => p.Label == "11_Pat_A");
        var b = proc.Patterns.Single(p => p.Label == "11_Pat_B");
        var c = proc.Patterns.Single(p => p.Label == "11_Pat_C");

        Assert.Equal(b.Id, c.HostPatternId);
        Assert.NotEqual(a.Id, c.HostPatternId);
    }

    [Fact]
    public void ComputeHostPatternIds_FrameFixture_TopChordStillHostedByDivideLine()
    {
        var context = ParseFrameFixtureForHostTests();
        var proc11 = context.Algorithms.Single(a => a.Index == 1).Procedures.Single(p => p.Index == 11);
        var divideLine = proc11.Patterns.Single(p => p.Label == "11_Pat_DivideLine");
        var topChord = proc11.Patterns.Single(p => p.Label == "11_Pat_TopChord");

        Assert.Equal(divideLine.Id, topChord.HostPatternId);
    }

    [Fact]
    public void ComputeHostPatternIds_NoNestedGroupIdsAnywhere_StrictSupersetFallbackStillResolves()
    {
        var raw = new RawCanvas
        {
            Groups =
            {
                new RawGroup { Nickname = "11_Pat_Outer", MemberIds = { "n-a", "n-b" } },
                new RawGroup { Nickname = "11_Pat_Inner", MemberIds = { "n-b" } },
            },
        };

        var context = CanvasAnnotationParser.Parse(raw);
        var proc = context.Algorithms.Single().Procedures.Single(p => p.Index == 11);
        var outer = proc.Patterns.Single(p => p.Label == "11_Pat_Outer");
        var inner = proc.Patterns.Single(p => p.Label == "11_Pat_Inner");

        Assert.Equal(outer.Id, inner.HostPatternId);
    }
}
