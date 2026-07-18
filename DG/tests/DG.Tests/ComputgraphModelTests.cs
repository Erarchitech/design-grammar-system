using DG.Core.Models.Computgraph;

namespace DG.Tests;

public sealed class ComputgraphModelTests
{
    [Fact]
    public void CgProcedure_DefaultConstruction_CollectionsAreNonNullAndEmpty()
    {
        var procedure = new CgProcedure();

        Assert.NotNull(procedure.Patterns);
        Assert.Empty(procedure.Patterns);
        Assert.NotNull(procedure.Parameters);
        Assert.Empty(procedure.Parameters);
        Assert.NotNull(procedure.Interfaces);
        Assert.Empty(procedure.Interfaces);
        Assert.NotNull(procedure.MemberIds);
        Assert.Empty(procedure.MemberIds);
    }

    [Fact]
    public void CgContext_DefaultConstruction_SchemaVersionIsCgContext1()
    {
        var context = new CgContext();

        Assert.Equal("cg-context-1", context.SchemaVersion);
        Assert.NotNull(context.Algorithms);
        Assert.Empty(context.Algorithms);
        Assert.NotNull(context.Untagged);
        Assert.NotNull(context.Nodes);
        Assert.Empty(context.Nodes);
        Assert.NotNull(context.Wires);
        Assert.Empty(context.Wires);
        Assert.NotNull(context.Warnings);
        Assert.Empty(context.Warnings);
    }

    [Fact]
    public void ParamKind_EnumMembers_MatchContextDecision()
    {
        Assert.Equal(new[] { "Variable", "Constant", "Emergent" }, Enum.GetNames<ParamKind>());
    }

    [Fact]
    public void ParamDataType_EnumMembers_MatchContextDecision()
    {
        Assert.Equal(
            new[] { "Float", "Integer", "Text", "Boolean", "Geometry" },
            Enum.GetNames<ParamDataType>());
    }

    [Fact]
    public void IfaceType_EnumMembers_MatchContextDecision()
    {
        Assert.Equal(new[] { "Input", "Output" }, Enum.GetNames<IfaceType>());
    }

    [Fact]
    public void RawCanvas_DefaultConstruction_CollectionsAreNonNullAndEmpty()
    {
        var rawCanvas = new RawCanvas();

        Assert.NotNull(rawCanvas.Groups);
        Assert.Empty(rawCanvas.Groups);
        Assert.NotNull(rawCanvas.Scribbles);
        Assert.Empty(rawCanvas.Scribbles);
        Assert.NotNull(rawCanvas.Nodes);
        Assert.Empty(rawCanvas.Nodes);
        Assert.NotNull(rawCanvas.Wires);
        Assert.Empty(rawCanvas.Wires);
    }
}
