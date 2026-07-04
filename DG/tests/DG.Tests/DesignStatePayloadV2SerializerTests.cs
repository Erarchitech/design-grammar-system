using System.Text.Json;
using DG.Core.Models;
using DG.Core.Serialization;
using DG.Core.Services;

namespace DG.Tests;

public sealed class DesignStatePayloadV2SerializerTests
{
    [Fact]
    public void SerializeDeserialize_RoundTrip_ShouldPreserveAllThreeLists()
    {
        var state = CreateDesignState();

        var json = DesignStatePayloadV2Serializer.Serialize(state);
        var roundTrip = DesignStatePayloadV2Serializer.Deserialize(json);

        Assert.Equal(state.StateId, roundTrip.StateId);
        Assert.Equal(state.ObjStates.Count, roundTrip.ObjStates.Count);
        Assert.Equal(state.ParamStates.Count, roundTrip.ParamStates.Count);
        Assert.Equal(state.PropStates.Count, roundTrip.PropStates.Count);

        Assert.Equal(state.ObjStates[0].StateId, roundTrip.ObjStates[0].StateId);
        Assert.Equal(state.ObjStates[0].ObjectRef, roundTrip.ObjStates[0].ObjectRef);
        Assert.Equal(state.ObjStates[0].Label, roundTrip.ObjStates[0].Label);

        Assert.Equal(state.ParamStates[0].StateId, roundTrip.ParamStates[0].StateId);
        Assert.Equal(state.ParamStates[0].Parameters.Count, roundTrip.ParamStates[0].Parameters.Count);

        Assert.Equal(state.PropStates[0].StateId, roundTrip.PropStates[0].StateId);
        Assert.Equal(state.PropStates[0].RuleIri, roundTrip.PropStates[0].RuleIri);
        Assert.Equal(state.PropStates[0].DataPropertyIri, roundTrip.PropStates[0].DataPropertyIri);
    }

    [Fact]
    public void SerializeDeserialize_RoundTrip_ShouldPreserveTypedParameters()
    {
        var state = CreateDesignState();

        var json = DesignStatePayloadV2Serializer.Serialize(state);
        var roundTrip = DesignStatePayloadV2Serializer.Deserialize(json);

        var paramState = roundTrip.ParamStates[0];
        Assert.Contains(paramState.Parameters, p => p.ParameterId == "height" && p.NumberValue == 72.5);
        Assert.Contains(paramState.Parameters, p => p.ParameterId == "floors" && p.IntegerValue == 18);
    }

    [Fact]
    public void SerializeDeserialize_RoundTrip_ShouldPreservePropStateValues()
    {
        var state = CreateDesignState();

        var json = DesignStatePayloadV2Serializer.Serialize(state);
        var roundTrip = DesignStatePayloadV2Serializer.Deserialize(json);

        var propState = roundTrip.PropStates[0];
        Assert.Equal("http://www.design-grammar.org/ontologies/dg#Rule_heightCheck", propState.RuleIri);
        Assert.NotNull(propState.PropValue);
        Assert.Equal(42.0, propState.PropValue.NumberValue);
    }

    [Fact]
    public void Deserialize_WhenVersionIsMissing_ShouldThrow()
    {
        var json = """
            {
              "stateId": "DS_abc123def456",
              "capturedAtUtc": "2026-07-04T10:00:00.0000000Z",
              "objStates": [],
              "paramStates": [],
              "propStates": []
            }
            """;

        var ex = Assert.Throws<InvalidOperationException>(() => DesignStatePayloadV2Serializer.Deserialize(json));

        Assert.Contains("version", ex.Message, StringComparison.OrdinalIgnoreCase);
    }

    [Fact]
    public void Deserialize_WhenVersionIsNot2_ShouldThrow()
    {
        var json = """
            {
              "version": "1",
              "stateId": "DS_abc123def456",
              "capturedAtUtc": "2026-07-04T10:00:00.0000000Z",
              "objStates": [],
              "paramStates": [],
              "propStates": []
            }
            """;

        var ex = Assert.Throws<InvalidOperationException>(() => DesignStatePayloadV2Serializer.Deserialize(json));

        Assert.Contains("version", ex.Message, StringComparison.OrdinalIgnoreCase);
    }

    [Fact]
    public void Deserialize_WhenJsonIsMalformed_ShouldThrow()
    {
        var json = "not json";

        var ex = Assert.Throws<InvalidOperationException>(() => DesignStatePayloadV2Serializer.Deserialize(json));

        Assert.Contains("JSON", ex.Message, StringComparison.OrdinalIgnoreCase);
    }

    [Fact]
    public void Deserialize_WhenPayloadIsEmpty_ShouldThrow()
    {
        Assert.Throws<InvalidOperationException>(() => DesignStatePayloadV2Serializer.Deserialize(null!));
        Assert.Throws<InvalidOperationException>(() => DesignStatePayloadV2Serializer.Deserialize(""));
        Assert.Throws<InvalidOperationException>(() => DesignStatePayloadV2Serializer.Deserialize("   "));
    }

    [Fact]
    public void Deserialize_WhenCapturedAtUtcMissing_ShouldThrow()
    {
        var json = """
            {
              "version": "2",
              "stateId": "DS_abc123def456",
              "objStates": [],
              "paramStates": [],
              "propStates": []
            }
            """;

        var ex = Assert.Throws<InvalidOperationException>(() => DesignStatePayloadV2Serializer.Deserialize(json));

        Assert.Contains("CapturedAtUtc", ex.Message);
    }

    [Fact]
    public void Serialize_ShouldProduceValidJson_WithVersion2()
    {
        var state = CreateDesignState();

        var json = DesignStatePayloadV2Serializer.Serialize(state);

        Assert.Contains("\"version\":\"2\"", json);
        using var doc = JsonDocument.Parse(json);
        var root = doc.RootElement;
        Assert.True(root.TryGetProperty("objStates", out _));
        Assert.True(root.TryGetProperty("paramStates", out _));
        Assert.True(root.TryGetProperty("propStates", out _));
    }

    private static DesignState CreateDesignState()
    {
        var objState1 = new ObjState
        {
            StateId = DesignStateIdGenerator.ComputeObjectStateId("test-project", "obj-001", "buildingA"),
            ObjectRef = "obj-001",
            Label = "Building A",
            CapturedAtUtc = new DateTimeOffset(2026, 7, 4, 10, 0, 0, TimeSpan.Zero),
        };

        var objState2 = new ObjState
        {
            StateId = DesignStateIdGenerator.ComputeObjectStateId("test-project", "obj-002", "buildingB"),
            ObjectRef = "obj-002",
            Label = "Building B",
            CapturedAtUtc = new DateTimeOffset(2026, 7, 4, 10, 0, 0, TimeSpan.Zero),
        };

        var heightParam = new DesignStateParameter
        {
            ParameterId = "height",
            DisplayName = "Height",
            Type = DesignStateParameterType.Number,
            NumberValue = 72.5,
        };

        var floorsParam = new DesignStateParameter
        {
            ParameterId = "floors",
            DisplayName = "Floors",
            Type = DesignStateParameterType.Integer,
            IntegerValue = 18,
        };

        var paramStateId = DesignStateIdGenerator.ComputeParamStateId(new[] { heightParam, floorsParam });
        var paramState = new ParamState
        {
            StateId = paramStateId,
            CapturedAtUtc = new DateTimeOffset(2026, 7, 4, 10, 0, 0, TimeSpan.Zero),
        };
        paramState.Parameters.Add(heightParam);
        paramState.Parameters.Add(floorsParam);

        var propValue = new DesignStateParameter
        {
            ParameterId = "maxHeight",
            DisplayName = "Max Height",
            Type = DesignStateParameterType.Number,
            NumberValue = 42.0,
        };

        var propStateId = DesignStateIdGenerator.ComputePropStateId(
            "http://www.design-grammar.org/ontologies/dg#Rule_heightCheck",
            "http://www.design-grammar.org/ontologies/dg#hasMaximumHeight",
            propValue);

        var propState = new PropState
        {
            StateId = propStateId,
            RuleIri = "http://www.design-grammar.org/ontologies/dg#Rule_heightCheck",
            DataPropertyIri = "http://www.design-grammar.org/ontologies/dg#hasMaximumHeight",
            PropValue = propValue,
        };

        var memberStateIds = new[] { objState1.StateId, objState2.StateId, paramState.StateId, propState.StateId };
        var designStateId = DesignStateIdGenerator.ComputeDesignStateId(memberStateIds);

        return new DesignState
        {
            StateId = designStateId,
            CapturedAtUtc = new DateTimeOffset(2026, 7, 4, 10, 0, 0, TimeSpan.Zero),
            ObjStates = { objState1, objState2 },
            ParamStates = { paramState },
            PropStates = { propState },
        };
    }
}
