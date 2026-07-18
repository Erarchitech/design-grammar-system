using System.Text.Json;
using DG.Core.Models.Computgraph;
using DG.Core.Serialization;
using DG.Core.Services;

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

    [Fact]
    public void Deserialize_RoundTrip_ShouldPreserveEntities()
    {
        var context = CreateContext();
        var json = ComputgraphContextSerializer.Serialize(context);

        var roundTrip = ComputgraphContextSerializer.Deserialize(json);

        Assert.Equal(context.SchemaVersion, roundTrip.SchemaVersion);
        Assert.Equal(context.Project, roundTrip.Project);
        Assert.Equal(context.Definition.DocumentId, roundTrip.Definition.DocumentId);
        Assert.Equal(context.Definition.FileName, roundTrip.Definition.FileName);
        Assert.Equal(context.Definition.CapturedAt, roundTrip.Definition.CapturedAt);
        Assert.NotNull(roundTrip.Object);
        Assert.Equal(context.Object!.Name, roundTrip.Object!.Name);
        Assert.Equal(context.Algorithms.Count, roundTrip.Algorithms.Count);

        var procedure = roundTrip.Algorithms[0].Procedures[0];
        Assert.Equal("cg:1:proc:11", procedure.Id);
        Assert.Equal(2, procedure.MemberIds.Count);
        Assert.Single(procedure.Parameters);
        Assert.Equal(ParamKind.Variable, procedure.Parameters[0].Kind);
        Assert.Equal(ParamDataType.Integer, procedure.Parameters[0].DataType);
        Assert.NotNull(procedure.Parameters[0].Domain);
        Assert.Equal(1, procedure.Parameters[0].Domain!.Min);
        Assert.Single(procedure.Interfaces);
        Assert.Equal(IfaceType.Output, procedure.Interfaces[0].IfaceType);
        Assert.Single(procedure.Patterns);

        Assert.Equal(context.Nodes.Count, roundTrip.Nodes.Count);
        Assert.Equal(context.Wires.Count, roundTrip.Wires.Count);
        Assert.Equal(context.Untagged.NodeIds.Count, roundTrip.Untagged.NodeIds.Count);
        Assert.Equal(context.Untagged.Groups.Count, roundTrip.Untagged.Groups.Count);
        Assert.Equal(context.Warnings.Count, roundTrip.Warnings.Count);
    }

    [Fact]
    public void SerializeDeserialize_RoundTrip_ShouldBeIdempotent()
    {
        var context = CreateContext();
        var json = ComputgraphContextSerializer.Serialize(context);

        var roundTripJson = ComputgraphContextSerializer.Serialize(ComputgraphContextSerializer.Deserialize(json));

        Assert.Equal(json, roundTripJson);
    }

    [Fact]
    public void Deserialize_WhenSchemaVersionIsNotCgContext1_ShouldThrow()
    {
        var json = """
            {
              "schemaVersion": "cg-context-2",
              "project": "p",
              "definition": { "documentId": "d", "fileName": "f.gh", "capturedAt": "2026-01-01T00:00:00Z" },
              "object": null,
              "algorithms": [],
              "untagged": { "nodeIds": [], "groups": [] },
              "nodes": [],
              "wires": [],
              "warnings": []
            }
            """;

        var ex = Assert.Throws<InvalidOperationException>(() => ComputgraphContextSerializer.Deserialize(json));

        Assert.Contains("cg-context-1", ex.Message);
    }

    [Fact]
    public void Deserialize_WhenPayloadIsEmpty_ShouldThrow()
    {
        Assert.Throws<InvalidOperationException>(() => ComputgraphContextSerializer.Deserialize(null!));
        Assert.Throws<InvalidOperationException>(() => ComputgraphContextSerializer.Deserialize(""));
        Assert.Throws<InvalidOperationException>(() => ComputgraphContextSerializer.Deserialize("   "));
    }

    [Fact]
    public void Deserialize_WhenJsonIsMalformed_ShouldThrowInvalidOperationExceptionNotJsonException()
    {
        var ex = Assert.Throws<InvalidOperationException>(() => ComputgraphContextSerializer.Deserialize("not json"));

        Assert.Contains("JSON", ex.Message, StringComparison.OrdinalIgnoreCase);
    }

    [Fact]
    public void Serialize_WithDgIds_EmittedJsonContainsDgIdKey()
    {
        var context = CreateContext();
        CgContextDgIdAssigner.AssignDgIds(context, "p1");

        var json = ComputgraphContextSerializer.Serialize(context);

        Assert.Contains("\"dgId\":\"dg:", json);
    }

    [Fact]
    public void Deserialize_RoundTripWithDgIds_PreservesEachEntityDgId()
    {
        var context = CreateContext();
        CgContextDgIdAssigner.AssignDgIds(context, "p1");

        var json = ComputgraphContextSerializer.Serialize(context);
        var roundTrip = ComputgraphContextSerializer.Deserialize(json);

        Assert.Equal(context.Object!.DgId, roundTrip.Object!.DgId);

        for (var i = 0; i < context.Algorithms.Count; i++)
        {
            for (var j = 0; j < context.Algorithms[i].Procedures.Count; j++)
            {
                var srcProc = context.Algorithms[i].Procedures[j];
                var dstProc = roundTrip.Algorithms[i].Procedures[j];
                Assert.Equal(srcProc.DgId, dstProc.DgId);

                for (var k = 0; k < srcProc.Patterns.Count; k++)
                    Assert.Equal(srcProc.Patterns[k].DgId, dstProc.Patterns[k].DgId);

                for (var k = 0; k < srcProc.Parameters.Count; k++)
                    Assert.Equal(srcProc.Parameters[k].DgId, dstProc.Parameters[k].DgId);

                for (var k = 0; k < srcProc.Interfaces.Count; k++)
                    Assert.Equal(srcProc.Interfaces[k].DgId, dstProc.Interfaces[k].DgId);
            }
        }
    }

    [Fact]
    public void SerializeDeserialize_RoundTripWithDgIds_ShouldBeIdempotent()
    {
        var context = CreateContext();
        CgContextDgIdAssigner.AssignDgIds(context, "p1");

        var json = ComputgraphContextSerializer.Serialize(context);
        var roundTripJson = ComputgraphContextSerializer.Serialize(ComputgraphContextSerializer.Deserialize(json));

        Assert.Equal(json, roundTripJson);
    }

    [Fact]
    public void Deserialize_BackwardCompatPre32_1_NoDgIdKeys_ShouldNotThrowAndLeaveDgIdNull()
    {
        var json = """
            {
              "schemaVersion": "cg-context-1",
              "project": "p",
              "definition": { "documentId": "d", "fileName": "f.gh", "capturedAt": "2026-01-01T00:00:00Z" },
              "object": { "name": "FRAME", "classIri": null, "source": "tagged" },
              "algorithms": [
                {
                  "index": 1,
                  "name": "1_ALGORITHM",
                  "procedures": [
                    {
                      "id": "cg:1:proc:11",
                      "index": 11,
                      "name": "2D Truss Configuration",
                      "source": "tagged",
                      "memberIds": [],
                      "patterns": [
                        { "id": "cg:1:pat:11_1", "label": "11_Pat_1", "name": null, "hostPatternId": null, "memberIds": [], "source": "tagged" }
                      ],
                      "parameters": [
                        { "id": "cg:1:par:11_Var_SpansCount", "kind": "Variable", "name": "SpansCount", "dataType": null, "domain": null, "memberIds": [], "source": "tagged" }
                      ],
                      "interfaces": [
                        { "id": "cg:1:intf:11_ParSplitAt", "name": "ParSplitAt", "ifaceType": "Output", "memberIds": [], "source": "tagged" }
                      ]
                    }
                  ]
                }
              ],
              "untagged": { "nodeIds": [], "groups": [] },
              "nodes": [],
              "wires": [],
              "warnings": []
            }
            """;

        var context = ComputgraphContextSerializer.Deserialize(json);

        Assert.NotNull(context);
        Assert.Null(context.Object!.DgId);

        foreach (var algorithm in context.Algorithms)
        {
            foreach (var procedure in algorithm.Procedures)
            {
                Assert.Null(procedure.DgId);

                foreach (var pattern in procedure.Patterns)
                    Assert.Null(pattern.DgId);

                foreach (var parameter in procedure.Parameters)
                    Assert.Null(parameter.DgId);

                foreach (var iface in procedure.Interfaces)
                    Assert.Null(iface.DgId);
            }
        }
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
