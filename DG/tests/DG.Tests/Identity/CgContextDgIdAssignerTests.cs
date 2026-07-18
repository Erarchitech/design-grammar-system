using DG.Core.Models.Computgraph;
using DG.Core.Models.Identity;
using DG.Core.Services;

namespace DG.Tests;

/// <summary>
/// Proves DGID-01: every tagged Computgraph entity carries a deterministic,
/// project-scoped, dg-prefixed identity after the assigner runs.
/// Also locks the entityKey derivation contract for Phase 36 (publish path).
/// </summary>
public sealed class CgContextDgIdAssignerTests
{
    private const string Project = "p1";

    [Fact]
    public void AssignDgIds_AllTaggedEntities_ShouldHaveNonEmptyDgPrefixedDgId()
    {
        var context = CreateContext();

        CgContextDgIdAssigner.AssignDgIds(context, Project);

        // Object
        Assert.NotNull(context.Object?.DgId);
        Assert.StartsWith("dg:", context.Object!.DgId);
        Assert.NotEmpty(context.Object.DgId!);

        // Each Procedure
        foreach (var algorithm in context.Algorithms)
        {
            foreach (var procedure in algorithm.Procedures)
            {
                Assert.NotNull(procedure.DgId);
                Assert.StartsWith("dg:", procedure.DgId);
                Assert.NotEmpty(procedure.DgId!);

                // Each Pattern
                foreach (var pattern in procedure.Patterns)
                {
                    Assert.NotNull(pattern.DgId);
                    Assert.StartsWith("dg:", pattern.DgId);
                    Assert.NotEmpty(pattern.DgId!);
                }

                // Each Parameter
                foreach (var parameter in procedure.Parameters)
                {
                    Assert.NotNull(parameter.DgId);
                    Assert.StartsWith("dg:", parameter.DgId);
                    Assert.NotEmpty(parameter.DgId!);
                }

                // Each Interface
                foreach (var iface in procedure.Interfaces)
                {
                    Assert.NotNull(iface.DgId);
                    Assert.StartsWith("dg:", iface.DgId);
                    Assert.NotEmpty(iface.DgId!);
                }
            }
        }
    }

    [Fact]
    public void AssignDgIds_SameContextTwice_ShouldProduceByteIdenticalDgIds()
    {
        var first = CreateContext();
        var second = CreateContext();

        CgContextDgIdAssigner.AssignDgIds(first, Project);
        CgContextDgIdAssigner.AssignDgIds(second, Project);

        // Object
        Assert.Equal(first.Object!.DgId, second.Object!.DgId);

        // Each entity pair
        for (var i = 0; i < first.Algorithms.Count; i++)
        {
            for (var j = 0; j < first.Algorithms[i].Procedures.Count; j++)
            {
                var fProc = first.Algorithms[i].Procedures[j];
                var sProc = second.Algorithms[i].Procedures[j];
                Assert.Equal(fProc.DgId, sProc.DgId);

                for (var k = 0; k < fProc.Patterns.Count; k++)
                    Assert.Equal(fProc.Patterns[k].DgId, sProc.Patterns[k].DgId);

                for (var k = 0; k < fProc.Parameters.Count; k++)
                    Assert.Equal(fProc.Parameters[k].DgId, sProc.Parameters[k].DgId);

                for (var k = 0; k < fProc.Interfaces.Count; k++)
                    Assert.Equal(fProc.Interfaces[k].DgId, sProc.Interfaces[k].DgId);
            }
        }
    }

    [Fact]
    public void AssignDgIds_ObjectDgId_ShouldDeriveFromNameWithObjPrefix()
    {
        var context = CreateContext();
        var objectName = context.Object!.Name;

        CgContextDgIdAssigner.AssignDgIds(context, Project);

        var expected = DgIdMintingService.Mint(Project, context.Definition.DocumentId, $"obj:{objectName}");
        Assert.Equal(expected.Value, context.Object.DgId);
    }

    [Fact]
    public void AssignDgIds_TypedEntityDgId_ShouldDeriveFromEntityId()
    {
        var context = CreateContext();

        CgContextDgIdAssigner.AssignDgIds(context, Project);

        var procedure = context.Algorithms[0].Procedures[0];
        var expectedProc = DgIdMintingService.Mint(Project, context.Definition.DocumentId, procedure.Id);
        Assert.Equal(expectedProc.Value, procedure.DgId);

        var pattern = procedure.Patterns[0];
        var expectedPat = DgIdMintingService.Mint(Project, context.Definition.DocumentId, pattern.Id);
        Assert.Equal(expectedPat.Value, pattern.DgId);

        var parameter = procedure.Parameters[0];
        var expectedPar = DgIdMintingService.Mint(Project, context.Definition.DocumentId, parameter.Id);
        Assert.Equal(expectedPar.Value, parameter.DgId);

        var iface = procedure.Interfaces[0];
        var expectedIface = DgIdMintingService.Mint(Project, context.Definition.DocumentId, iface.Id);
        Assert.Equal(expectedIface.Value, iface.DgId);
    }

    [Fact]
    public void AssignDgIds_DifferentProject_ShouldChangeEveryAssignedDgId()
    {
        var contextP1 = CreateContext();
        var contextP2 = CreateContext();

        CgContextDgIdAssigner.AssignDgIds(contextP1, "p1");
        CgContextDgIdAssigner.AssignDgIds(contextP2, "p2");

        Assert.NotEqual(contextP1.Object!.DgId, contextP2.Object!.DgId);

        for (var i = 0; i < contextP1.Algorithms.Count; i++)
        {
            for (var j = 0; j < contextP1.Algorithms[i].Procedures.Count; j++)
            {
                var p1Proc = contextP1.Algorithms[i].Procedures[j];
                var p2Proc = contextP2.Algorithms[i].Procedures[j];
                Assert.NotEqual(p1Proc.DgId, p2Proc.DgId);

                for (var k = 0; k < p1Proc.Patterns.Count; k++)
                    Assert.NotEqual(p1Proc.Patterns[k].DgId, p2Proc.Patterns[k].DgId);

                for (var k = 0; k < p1Proc.Parameters.Count; k++)
                    Assert.NotEqual(p1Proc.Parameters[k].DgId, p2Proc.Parameters[k].DgId);

                for (var k = 0; k < p1Proc.Interfaces.Count; k++)
                    Assert.NotEqual(p1Proc.Interfaces[k].DgId, p2Proc.Interfaces[k].DgId);
            }
        }
    }

    private static CgContext CreateContext()
    {
        var context = new CgContext
        {
            Project = Project,
            Definition = new CgDefinition
            {
                DocumentId = "11111111-1111-1111-1111-111111111111",
                FileName = "frame.gh",
                CapturedAt = "2026-07-08T10:00:00.0000000Z",
            },
            Object = new CgObject
            {
                Name = "FRAME",
                Source = "tagged",
            },
        };

        var procedure = new CgProcedure
        {
            Id = "cg:1:proc:11",
            Index = 11,
            Name = "2D Truss Configuration",
            Source = "tagged",
        };

        procedure.Patterns.Add(new CgPattern
        {
            Id = "cg:1:pat:11_1",
            Label = "11_Pat_1",
        });

        procedure.Parameters.Add(new CgParameter
        {
            Id = "cg:1:par:11_Var_SpansCount",
            Kind = ParamKind.Variable,
            Name = "SpansCount",
        });

        procedure.Interfaces.Add(new CgInterface
        {
            Id = "cg:1:intf:11_ParSplitAt",
            Name = "ParSplitAt",
            IfaceType = IfaceType.Output,
        });

        var algorithm = new CgAlgorithm
        {
            Index = 1,
            Name = "1_ALGORITHM",
        };
        algorithm.Procedures.Add(procedure);

        context.Algorithms.Add(algorithm);

        return context;
    }
}
