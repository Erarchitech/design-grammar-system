using DG.Core.Parsing;

namespace DG.Tests;

public sealed class SwrlRuleParserTests
{
    [Fact]
    public void Parse_ShouldExtractAtomsAndVariables()
    {
        const string swrl = "Building(?b)^hasHeightM(?b,?h)^swrlb:greaterThan(?h,75)->violatesMaxHeight(?b,true)";
        var parsed = SwrlRuleParser.Parse(swrl);

        Assert.Equal(3, parsed.BodyAtoms.Count);
        Assert.Single(parsed.HeadAtoms);
        Assert.Contains(parsed.Variables, variable => variable.Name == "?b");
        Assert.Contains(parsed.Variables, variable => variable.Name == "?h");
    }
}
