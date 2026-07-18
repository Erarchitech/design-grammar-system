using System.Runtime.CompilerServices;
using DG.Core.Models.Computgraph;
using DG.Core.Parsing;

namespace DG.Tests;

public sealed class CanvasAnnotationNameFactoryTests
{
    // --- Task 1: parser/grammar consistency guard ---

    [Fact]
    public void Grammar_ConstantsAppearVerbatimInParserSource()
    {
        var source = File.ReadAllText(GetParserSourcePath());

        Assert.Contains(CanvasAnnotationGrammar.ObjectPrefix, source);
        Assert.Contains(CanvasAnnotationGrammar.AlgorithmSuffix, source);
        Assert.Contains(CanvasAnnotationGrammar.ProcedureInfix, source);
        Assert.Contains(CanvasAnnotationGrammar.PatternInfix, source);
        Assert.Contains(CanvasAnnotationGrammar.VariableInfix, source);
        Assert.Contains(CanvasAnnotationGrammar.ConstantInfix, source);

        // EmergentInfix/EmergentToleratedInfix are NOT contiguous substrings in the parser
        // source -- the parser embeds them as a capture-group alternation
        // ("_(?<tag>Emg|Emr)_"), so the literal underscores surrounding the tag are not
        // adjacent to the tag text itself. Assert the bare tag literals instead; this still
        // catches drift (renaming Emg/Emr in either the parser alternation or these
        // constants breaks the assertion).
        Assert.Contains("Emg", source);
        Assert.Contains("Emr", source);
        Assert.Equal("_Emg_", CanvasAnnotationGrammar.EmergentInfix);
        Assert.Equal("_Emr_", CanvasAnnotationGrammar.EmergentToleratedInfix);

        Assert.Contains(CanvasAnnotationGrammar.InterfaceInfix, source);
    }

    private static string GetParserSourcePath([CallerFilePath] string testFilePath = "")
    {
        var testsDir = Path.GetDirectoryName(testFilePath)!;
        return Path.GetFullPath(Path.Combine(testsDir, "..", "..", "src", "DG.Core", "Parsing", "CanvasAnnotationParser.cs"));
    }

    // --- Task 2: CanvasAnnotationNameFactory construction ---

    [Fact]
    public void ForObjectScribble_BuildsObjectPrefixedText()
    {
        Assert.Equal("OBJECT - FRAME", CanvasAnnotationNameFactory.ForObjectScribble("FRAME"));
    }

    [Theory]
    [InlineData("")]
    [InlineData("   ")]
    public void ForObjectScribble_EmptyOrWhitespaceName_ThrowsArgumentException(string name)
    {
        Assert.Throws<ArgumentException>(() => CanvasAnnotationNameFactory.ForObjectScribble(name));
    }

    [Fact]
    public void ForAlgorithmScribble_BuildsAlgorithmSuffixedText()
    {
        Assert.Equal("1_ALGORITHM", CanvasAnnotationNameFactory.ForAlgorithmScribble(1));
    }

    [Theory]
    [InlineData(0)]
    [InlineData(10)]
    [InlineData(-1)]
    public void ForAlgorithmScribble_OutOfRangeIndex_ThrowsArgumentOutOfRangeException(int algorithmIndex)
    {
        Assert.Throws<ArgumentOutOfRangeException>(() => CanvasAnnotationNameFactory.ForAlgorithmScribble(algorithmIndex));
    }

    [Fact]
    public void ForEntity_Var_BuildsVariableName()
    {
        Assert.Equal(
            "11_Var_SpansCount",
            CanvasAnnotationNameFactory.ForEntity(EntityTagKind.Var, 11, "SpansCount"));
    }

    [Fact]
    public void ForEntity_Proc_BuildsProcedureName()
    {
        Assert.Equal(
            "11_Proc - 2D Truss Configuration",
            CanvasAnnotationNameFactory.ForEntity(EntityTagKind.Proc, 11, "2D Truss Configuration"));
    }

    [Fact]
    public void ForEntity_PatWithoutName_BuildsBarePatternName()
    {
        Assert.Equal(
            "11_Pat_2",
            CanvasAnnotationNameFactory.ForEntity(EntityTagKind.Pat, 11, "", patternIndex: 2));
    }

    [Fact]
    public void ForEntity_PatWithName_BuildsLabeledPatternName()
    {
        Assert.Equal(
            "11_Pat_2 TrussFrame",
            CanvasAnnotationNameFactory.ForEntity(EntityTagKind.Pat, 11, "TrussFrame", patternIndex: 2));
    }

    [Fact]
    public void ForEntity_Pat_MissingPatternIndex_ThrowsArgumentException()
    {
        Assert.Throws<ArgumentException>(
            () => CanvasAnnotationNameFactory.ForEntity(EntityTagKind.Pat, 11, "TrussFrame"));
    }

    [Fact]
    public void ForEntity_Const_BuildsConstantName()
    {
        Assert.Equal(
            "11_Const_ptZero",
            CanvasAnnotationNameFactory.ForEntity(EntityTagKind.Const, 11, "ptZero"));
    }

    [Fact]
    public void ForEntity_Emg_BuildsEmergentName()
    {
        Assert.Equal(
            "11_Emg_DivPoints",
            CanvasAnnotationNameFactory.ForEntity(EntityTagKind.Emg, 11, "DivPoints"));
    }

    [Fact]
    public void ForEntity_IntF_BuildsInterfaceName()
    {
        Assert.Equal(
            "11_IntF_ParSplitAt",
            CanvasAnnotationNameFactory.ForEntity(EntityTagKind.IntF, 11, "ParSplitAt"));
    }

    [Fact]
    public void ForEntity_ProcIndexBelowTen_ThrowsArgumentOutOfRangeException()
    {
        Assert.Throws<ArgumentOutOfRangeException>(
            () => CanvasAnnotationNameFactory.ForEntity(EntityTagKind.Var, 1, "SpansCount"));
    }

    [Theory]
    [InlineData(EntityTagKind.Var, "Bad_Var_Name")]
    [InlineData(EntityTagKind.Const, "Bad_Proc - Name")]
    [InlineData(EntityTagKind.Emg, "Bad_Emg_Name")]
    [InlineData(EntityTagKind.IntF, "Bad_IntF_Name")]
    public void ForEntity_NameContainsReservedInfixToken_ThrowsArgumentException(EntityTagKind kind, string name)
    {
        Assert.Throws<ArgumentException>(() => CanvasAnnotationNameFactory.ForEntity(kind, 11, name));
    }

    [Fact]
    public void NextFreePatternIndex_ExistingPatterns_ReturnsMaxPlusOne()
    {
        var existing = new[] { "11_Pat_1", "11_Pat_3 Foo" };

        Assert.Equal(4, CanvasAnnotationNameFactory.NextFreePatternIndex(existing, 11));
    }

    [Fact]
    public void NextFreePatternIndex_NoExistingPatterns_ReturnsOne()
    {
        Assert.Equal(1, CanvasAnnotationNameFactory.NextFreePatternIndex(Array.Empty<string>(), 11));
    }

    [Fact]
    public void IsReservedName_NameWithReservedToken_ReturnsTrue()
    {
        Assert.True(CanvasAnnotationNameFactory.IsReservedName("Foo_Var_Bar"));
    }

    [Fact]
    public void IsReservedName_PlainName_ReturnsFalse()
    {
        Assert.False(CanvasAnnotationNameFactory.IsReservedName("SpansCount"));
    }

    // --- Task 2: TAGC-03 round-trip symmetry (factory -> parser) ---

    [Fact]
    public void RoundTrip_ObjectScribble_ParsesToCgObject()
    {
        var raw = new RawCanvas
        {
            Scribbles = { new RawScribble { Text = CanvasAnnotationNameFactory.ForObjectScribble("FRAME") } },
        };

        var context = CanvasAnnotationParser.Parse(raw);

        Assert.NotNull(context.Object);
        Assert.Equal("FRAME", context.Object!.Name);
        Assert.Equal("tagged", context.Object.Source);
    }

    [Fact]
    public void RoundTrip_AlgorithmScribble_ParsesToCgAlgorithm()
    {
        var raw = new RawCanvas
        {
            Scribbles = { new RawScribble { Text = CanvasAnnotationNameFactory.ForAlgorithmScribble(1) } },
        };

        var context = CanvasAnnotationParser.Parse(raw);

        Assert.Single(context.Algorithms);
        Assert.Equal(1, context.Algorithms[0].Index);
    }

    [Fact]
    public void RoundTrip_ProcEntity_ParsesToCgProcedureWithIndex()
    {
        var raw = new RawCanvas
        {
            Groups =
            {
                new RawGroup
                {
                    Nickname = CanvasAnnotationNameFactory.ForEntity(EntityTagKind.Proc, 11, "2D Truss Configuration"),
                },
            },
        };

        var context = CanvasAnnotationParser.Parse(raw);

        var procedure = context.Algorithms.Single(a => a.Index == 1).Procedures.Single(p => p.Index == 11);
        Assert.Equal("2D Truss Configuration", procedure.Name);
        Assert.Equal("tagged", procedure.Source);
    }

    [Fact]
    public void RoundTrip_VarEntity_ParsesToCgParameterVariable_Success1()
    {
        var raw = new RawCanvas
        {
            Groups = { new RawGroup { Nickname = CanvasAnnotationNameFactory.ForEntity(EntityTagKind.Var, 11, "SpansCount") } },
        };

        var context = CanvasAnnotationParser.Parse(raw);

        var parameter = context.Algorithms.Single(a => a.Index == 1).Procedures.Single(p => p.Index == 11)
            .Parameters.Single();

        Assert.Equal(ParamKind.Variable, parameter.Kind);
        Assert.Equal("SpansCount", parameter.Name);
        Assert.Equal("tagged", parameter.Source);
    }

    [Fact]
    public void RoundTrip_ConstEntity_ParsesToCgParameterConstant()
    {
        var raw = new RawCanvas
        {
            Groups = { new RawGroup { Nickname = CanvasAnnotationNameFactory.ForEntity(EntityTagKind.Const, 11, "ptZero") } },
        };

        var context = CanvasAnnotationParser.Parse(raw);

        var parameter = context.Algorithms.Single(a => a.Index == 1).Procedures.Single(p => p.Index == 11)
            .Parameters.Single();

        Assert.Equal(ParamKind.Constant, parameter.Kind);
        Assert.Equal("ptZero", parameter.Name);
        Assert.Equal("tagged", parameter.Source);
    }

    [Fact]
    public void RoundTrip_EmgEntity_ParsesToCgParameterEmergent()
    {
        var raw = new RawCanvas
        {
            Groups = { new RawGroup { Nickname = CanvasAnnotationNameFactory.ForEntity(EntityTagKind.Emg, 11, "DivPoints") } },
        };

        var context = CanvasAnnotationParser.Parse(raw);

        var parameter = context.Algorithms.Single(a => a.Index == 1).Procedures.Single(p => p.Index == 11)
            .Parameters.Single();

        Assert.Equal(ParamKind.Emergent, parameter.Kind);
        Assert.Equal("DivPoints", parameter.Name);
        Assert.Equal("tagged", parameter.Source);
        Assert.Empty(context.Warnings);
    }

    [Fact]
    public void RoundTrip_IntFEntity_ParsesToCgInterface()
    {
        var raw = new RawCanvas
        {
            Groups = { new RawGroup { Nickname = CanvasAnnotationNameFactory.ForEntity(EntityTagKind.IntF, 11, "ParSplitAt") } },
        };

        var context = CanvasAnnotationParser.Parse(raw);

        var iface = context.Algorithms.Single(a => a.Index == 1).Procedures.Single(p => p.Index == 11)
            .Interfaces.Single();

        Assert.Equal("ParSplitAt", iface.Name);
        Assert.Equal("tagged", iface.Source);
    }

    [Fact]
    public void RoundTrip_PatEntityWithName_ParsesToCgPatternWithLabelAndName()
    {
        var raw = new RawCanvas
        {
            Groups =
            {
                new RawGroup
                {
                    Nickname = CanvasAnnotationNameFactory.ForEntity(EntityTagKind.Pat, 11, "TrussFrame", patternIndex: 2),
                },
            },
        };

        var context = CanvasAnnotationParser.Parse(raw);

        var pattern = context.Algorithms.Single(a => a.Index == 1).Procedures.Single(p => p.Index == 11)
            .Patterns.Single();

        Assert.Equal("11_Pat_2 TrussFrame", pattern.Label);
        Assert.Equal("TrussFrame", pattern.Name);
        Assert.Equal("tagged", pattern.Source);
    }

    [Fact]
    public void RoundTrip_PatEntityWithoutName_ParsesToCgPatternWithNullName()
    {
        var raw = new RawCanvas
        {
            Groups =
            {
                new RawGroup
                {
                    Nickname = CanvasAnnotationNameFactory.ForEntity(EntityTagKind.Pat, 11, "", patternIndex: 2),
                },
            },
        };

        var context = CanvasAnnotationParser.Parse(raw);

        var pattern = context.Algorithms.Single(a => a.Index == 1).Procedures.Single(p => p.Index == 11)
            .Patterns.Single();

        Assert.Equal("11_Pat_2", pattern.Label);
        Assert.Null(pattern.Name);
        Assert.Equal("tagged", pattern.Source);
    }

    [Fact]
    public void RoundTrip_CyrillicVariableName_ParsesVerbatim()
    {
        var raw = new RawCanvas
        {
            Groups = { new RawGroup { Nickname = CanvasAnnotationNameFactory.ForEntity(EntityTagKind.Var, 11, "Высота") } },
        };

        var context = CanvasAnnotationParser.Parse(raw);

        var parameter = context.Algorithms.Single(a => a.Index == 1).Procedures.Single(p => p.Index == 11)
            .Parameters.Single();

        Assert.Equal("Высота", parameter.Name);
        Assert.Equal("tagged", parameter.Source);
    }
}
