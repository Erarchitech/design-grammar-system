using DG.Core.Models.Computgraph;
using DG.Core.Parsing;

namespace DG.Tests;

/// <summary>
/// Regression-safe coverage for Phase 35's additive <see cref="RawGroup.Recognized"/> ->
/// <c>Source</c> propagation (RCGN-03). Never touches the classification regex -- only asserts
/// that a recognized group's typed entity carries <c>Source == "recognized"</c> while its kind
/// (Procedure/Pattern/Parameter/Interface) is unaffected.
/// </summary>
public sealed class CanvasAnnotationParserRecognizedSourceTests
{
    [Fact]
    public void Parse_RecognizedProcedureGroup_YieldsSourceRecognized()
    {
        var raw = new RawCanvas
        {
            Groups =
            {
                new RawGroup { Nickname = "11_Proc - 2D Truss Configuration", MemberIds = { "n1" }, Recognized = true },
            },
        };

        var context = CanvasAnnotationParser.Parse(raw);

        var procedure = context.Algorithms.Single().Procedures.Single(p => p.Index == 11);
        Assert.Equal("recognized", procedure.Source);
    }

    [Fact]
    public void Parse_UnrecognizedProcedureGroup_YieldsSourceTagged()
    {
        var raw = new RawCanvas
        {
            Groups =
            {
                new RawGroup { Nickname = "11_Proc - 2D Truss Configuration", MemberIds = { "n1" } },
            },
        };

        var context = CanvasAnnotationParser.Parse(raw);

        var procedure = context.Algorithms.Single().Procedures.Single(p => p.Index == 11);
        Assert.Equal("tagged", procedure.Source);
    }

    [Fact]
    public void Parse_RecognizedPatternGroup_YieldsSourceRecognized()
    {
        var raw = new RawCanvas
        {
            Groups =
            {
                new RawGroup { Nickname = "11_Proc - 2D Truss Configuration", MemberIds = { "n1" } },
                new RawGroup { Nickname = "11_Pat_1 Split", MemberIds = { "n2" }, Recognized = true },
            },
        };

        var context = CanvasAnnotationParser.Parse(raw);

        var procedure = context.Algorithms.Single().Procedures.Single(p => p.Index == 11);
        var pattern = procedure.Patterns.Single(p => p.Label == "11_Pat_1 Split");
        Assert.Equal("recognized", pattern.Source);
    }

    [Fact]
    public void Parse_RecognizedParameterGroup_YieldsSourceRecognized()
    {
        var raw = new RawCanvas
        {
            Groups =
            {
                new RawGroup { Nickname = "11_Proc - 2D Truss Configuration", MemberIds = { "n1" } },
                new RawGroup { Nickname = "11_Var_SpansCount", MemberIds = { "n2" }, Recognized = true },
            },
        };

        var context = CanvasAnnotationParser.Parse(raw);

        var procedure = context.Algorithms.Single().Procedures.Single(p => p.Index == 11);
        var parameter = procedure.Parameters.Single(p => p.Name == "SpansCount");
        Assert.Equal("recognized", parameter.Source);
    }

    [Fact]
    public void Parse_RecognizedInterfaceGroup_YieldsSourceRecognized()
    {
        var raw = new RawCanvas
        {
            Groups =
            {
                new RawGroup { Nickname = "11_IntF_ParSplitAt", MemberIds = { "n1" }, Recognized = true },
            },
        };

        var context = CanvasAnnotationParser.Parse(raw);

        var procedure = context.Algorithms.Single().Procedures.Single(p => p.Index == 11);
        var iface = procedure.Interfaces.Single(i => i.Name == "ParSplitAt");
        Assert.Equal("recognized", iface.Source);
    }

    [Fact]
    public void Parse_RecognizedGroup_DoesNotChangeEntityKindClassification()
    {
        var raw = new RawCanvas
        {
            Groups =
            {
                new RawGroup { Nickname = "11_Proc - 2D Truss Configuration", MemberIds = { "n1" }, Recognized = true },
            },
        };

        var context = CanvasAnnotationParser.Parse(raw);

        // Kind is still Procedure -- the entity landed in Algorithms[0].Procedures, not
        // Patterns/Parameters/Interfaces/Untagged. Classification comes only from the
        // nickname regex, never from Recognized.
        var algorithm = Assert.Single(context.Algorithms);
        var procedure = Assert.Single(algorithm.Procedures);
        Assert.Equal(11, procedure.Index);
        Assert.Equal("2D Truss Configuration", procedure.Name);
        Assert.Empty(context.Untagged.Groups);
    }
}
