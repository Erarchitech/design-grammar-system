using System.Text.Json;
using DG.Core.Models.Computgraph;
using DG.Core.Serialization;

namespace DG.Tests;

public sealed class ComputgraphContextSerializerTests
{
    [Fact]
    public void Serialize_ShouldEmitSchemaVersionAndCamelCaseKeys()
    {
        var context = CreateContext();

        var json = ComputgraphContextSerializer.Serialize(context);

        Assert.Contains("\"schemaVersion\":\"cg-context-1\"", json);
        using var doc = JsonDocument.Parse(json);
        var root = doc.RootElement;
        Assert.True(root.TryGetProperty("algorithms", out _));
        Assert.True(root.TryGetProperty("untagged", out _));
        Assert.True(root.TryGetProperty("nodes", out _));
        Assert.True(root.TryGetProperty("wires", out _));
        Assert.True(root.TryGetProperty("warnings", out _));

        var procedure = root.GetProperty("algorithms")[0].GetProperty("procedures")[0];
        Assert.True(procedure.TryGetProperty("memberIds", out _));
        Assert.True(procedure.GetProperty("parameters")[0].TryGetProperty("kind", out _));
        Assert.True(procedure.GetProperty("parameters")[0].TryGetProperty("dataType", out _));
        Assert.True(procedure.GetProperty("interfaces")[0].TryGetProperty("ifaceType", out _));
    }

    [Fact]
    public void Serialize_ShouldEmitEnumValuesAsStrings()
    {
        var context = CreateContext();

        var json = ComputgraphContextSerializer.Serialize(context);
        using var doc = JsonDocument.Parse(json);

        var procedure = doc.RootElement.GetProperty("algorithms")[0].GetProperty("procedures")[0];
        Assert.Equal("Variable", procedure.GetProperty("parameters")[0].GetProperty("kind").GetString());
        Assert.Equal("Output", procedure.GetProperty("interfaces")[0].GetProperty("ifaceType").GetString());
    }

    [Fact]
    public void Serialize_WithMembersInReversedOrder_ShouldProduceByteIdenticalJson()
    {
        var context = CreateContext();
        var reversed = CreateContextWithReversedMemberOrder();

        var json = ComputgraphContextSerializer.Serialize(context);
        var reversedJson = ComputgraphContextSerializer.Serialize(reversed);

        Assert.Equal(json, reversedJson);
    }

    [Fact]
    public void Serialize_WithNullDataTypeAndDomain_ShouldNotThrowAndShouldNullTheKeys()
    {
        var context = CreateContext();
        context.Algorithms[0].Procedures[0].Parameters.Add(new CgParameter
        {
            Id = "cg:1:par:11_Const_NoType",
            Kind = ParamKind.Constant,
            Name = "NoType",
            DataType = null,
            Domain = null,
        });

        var json = ComputgraphContextSerializer.Serialize(context);
        using var doc = JsonDocument.Parse(json);

        var parameters = doc.RootElement.GetProperty("algorithms")[0].GetProperty("procedures")[0].GetProperty("parameters");
        var noTypeParam = parameters.EnumerateArray().First(p => p.GetProperty("id").GetString() == "cg:1:par:11_Const_NoType");
        Assert.Equal(JsonValueKind.Null, noTypeParam.GetProperty("dataType").ValueKind);
        Assert.Equal(JsonValueKind.Null, noTypeParam.GetProperty("domain").ValueKind);
    }

    [Fact]
    public void Serialize_WhenContextIsNull_ShouldThrowArgumentNullException()
    {
        Assert.Throws<ArgumentNullException>(() => ComputgraphContextSerializer.Serialize(null!));
    }

    private static CgContext CreateContext()
    {
        var context = new CgContext
        {
            Project = "frame-project",
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
        procedure.MemberIds.Add("guid-b");
        procedure.MemberIds.Add("guid-a");

        procedure.Parameters.Add(new CgParameter
        {
            Id = "cg:1:par:11_Var_SpansCount",
            Kind = ParamKind.Variable,
            Name = "SpansCount",
            DataType = ParamDataType.Integer,
            Domain = new SliderDomain { Min = 1, Max = 20, Step = 1 },
        });
        procedure.Parameters[0].MemberIds.Add("guid-slider");

        procedure.Interfaces.Add(new CgInterface
        {
            Id = "cg:1:intf:11_ParSplitAt",
            Name = "ParSplitAt",
            IfaceType = IfaceType.Output,
        });

        procedure.Patterns.Add(new CgPattern
        {
            Id = "cg:1:pat:11_1",
            Label = "11_Pat_1",
        });

        var algorithm = new CgAlgorithm
        {
            Index = 1,
            Name = "1_ALGORITHM",
        };
        algorithm.Procedures.Add(procedure);

        context.Algorithms.Add(algorithm);

        context.Nodes.Add(new CgNode
        {
            InstanceId = "guid-a",
            ComponentGuid = "comp-guid-1",
            Name = "Divide Curve",
            Nickname = "Divide",
            Position = new double[] { 10, 20 },
        });
        context.Nodes.Add(new CgNode
        {
            InstanceId = "guid-b",
            ComponentGuid = "comp-guid-2",
            Name = "Number Slider",
            Nickname = "Slider",
            Position = new double[] { 30, 40 },
        });

        context.Wires.Add(new CgWire
        {
            FromNode = "guid-a",
            FromParam = "param-a",
            ToNode = "guid-b",
            ToParam = "param-b",
        });

        context.Untagged.NodeIds.Add("guid-c");
        context.Untagged.Groups.Add(new CgUntaggedGroup { Nickname = "raw name" });

        context.Warnings.Add("'11_Emr_UpperChord' normalized to Emergent (Emr->Emg)");

        return context;
    }

    private static CgContext CreateContextWithReversedMemberOrder()
    {
        var context = CreateContext();
        var procedure = context.Algorithms[0].Procedures[0];

        var reversedMemberIds = procedure.MemberIds.Reverse<string>().ToList();
        procedure.MemberIds.Clear();
        foreach (var id in reversedMemberIds)
        {
            procedure.MemberIds.Add(id);
        }

        var reversedNodes = context.Nodes.Reverse<CgNode>().ToList();
        context.Nodes.Clear();
        foreach (var node in reversedNodes)
        {
            context.Nodes.Add(node);
        }

        return context;
    }
}
