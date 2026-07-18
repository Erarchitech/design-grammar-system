using System.Runtime.CompilerServices;
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

    private static string GetParserSourcePath([CallerFilePath] string testFilePath = "")
    {
        var testsDir = Path.GetDirectoryName(testFilePath)!;
        return Path.GetFullPath(Path.Combine(testsDir, "..", "..", "src", "DG.Core", "Parsing", "CanvasAnnotationParser.cs"));
    }
}
