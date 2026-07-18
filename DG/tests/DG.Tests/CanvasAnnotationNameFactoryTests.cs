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
}
