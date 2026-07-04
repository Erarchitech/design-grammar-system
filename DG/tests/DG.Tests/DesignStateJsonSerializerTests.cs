using DG.Core.Models;
using DG.Core.Serialization;

namespace DG.Tests;

public sealed class DesignStateJsonSerializerTests
{
    [Fact]
    public void SerializeDeserialize_RoundTrip_ShouldPreserveTypedValues()
    {
        var snapshot = CreateSnapshot(
            new DesignStateParameter
            {
                ParameterId = "height",
                DisplayName = "Height",
                Type = DesignStateParameterType.Number,
                NumberValue = 72.5,
            },
            new DesignStateParameter
            {
                ParameterId = "floors",
                DisplayName = "Floors",
                Type = DesignStateParameterType.Integer,
                IntegerValue = 18,
            },
            new DesignStateParameter
            {
                ParameterId = "hasPodium",
                DisplayName = "Has Podium",
                Type = DesignStateParameterType.Boolean,
                BooleanValue = true,
            });

        var json = DesignStateJsonSerializer.Serialize(snapshot);
        var roundTrip = DesignStateJsonSerializer.Deserialize(json);

        Assert.Equal(snapshot.StateId, roundTrip.StateId);
        Assert.Equal(snapshot.CapturedAtUtc, roundTrip.CapturedAtUtc);
        Assert.Equal(3, roundTrip.Parameters.Count);
        Assert.Contains(roundTrip.Parameters, p => p.ParameterId == "height" && p.NumberValue == 72.5);
        Assert.Contains(roundTrip.Parameters, p => p.ParameterId == "floors" && p.IntegerValue == 18);
        Assert.Contains(roundTrip.Parameters, p => p.ParameterId == "hasPodium" && p.BooleanValue == true);
    }

    [Fact]
    public void Serialize_WhenInsertionOrderDiffers_ShouldRemainDeterministic()
    {
        var first = CreateSnapshot(
            new DesignStateParameter
            {
                ParameterId = "zeta",
                DisplayName = "Zeta",
                Type = DesignStateParameterType.Number,
                NumberValue = 1.2,
            },
            new DesignStateParameter
            {
                ParameterId = "alpha",
                DisplayName = "Alpha",
                Type = DesignStateParameterType.Integer,
                IntegerValue = 9,
            });

        var second = CreateSnapshot(
            new DesignStateParameter
            {
                ParameterId = "alpha",
                DisplayName = "Alpha",
                Type = DesignStateParameterType.Integer,
                IntegerValue = 9,
            },
            new DesignStateParameter
            {
                ParameterId = "zeta",
                DisplayName = "Zeta",
                Type = DesignStateParameterType.Number,
                NumberValue = 1.2,
            });

        var firstJson = DesignStateJsonSerializer.Serialize(first);
        var secondJson = DesignStateJsonSerializer.Serialize(second);

        Assert.Equal(firstJson, secondJson);
    }

    [Fact]
    public void Serialize_WhenTypeValueCombinationIsInvalid_ShouldThrow()
    {
        var snapshot = CreateSnapshot(
            new DesignStateParameter
            {
                ParameterId = "height",
                DisplayName = "Height",
                Type = DesignStateParameterType.Integer,
                NumberValue = 72.5,
            });

        var ex = Assert.Throws<InvalidOperationException>(() => DesignStateJsonSerializer.Serialize(snapshot));

        Assert.Contains("IntegerValue", ex.Message);
    }

    [Fact]
    public void Deserialize_WhenTypeAndValueMismatch_ShouldThrow()
    {
        var json = """
            {
              "stateId": "state-1",
              "capturedAtUtc": "2026-04-30T10:00:00.0000000Z",
              "parameters": [
                {
                  "parameterId": "hasPodium",
                  "displayName": "Has Podium",
                  "type": "boolean",
                  "value": "yes"
                }
              ]
            }
            """;

        var ex = Assert.Throws<InvalidOperationException>(() => DesignStateJsonSerializer.Deserialize(json));

        Assert.Contains("boolean", ex.Message);
    }

    [Fact]
    public void Deserialize_WhenMetadataFieldsMissing_ShouldThrow()
    {
        var missingParameterIdJson = """
            {
              "stateId": "state-1",
              "capturedAtUtc": "2026-04-30T10:00:00.0000000Z",
              "parameters": [
                {
                  "displayName": "Height",
                  "type": "number",
                  "value": 72.5
                }
              ]
            }
            """;

        var missingDisplayNameJson = """
            {
              "stateId": "state-1",
              "capturedAtUtc": "2026-04-30T10:00:00.0000000Z",
              "parameters": [
                {
                  "parameterId": "height",
                  "type": "number",
                  "value": 72.5
                }
              ]
            }
            """;

        var missingCapturedAtJson = """
            {
              "stateId": "state-1",
              "parameters": [
                {
                  "parameterId": "height",
                  "displayName": "Height",
                  "type": "number",
                  "value": 72.5
                }
              ]
            }
            """;

        var ex1 = Assert.Throws<InvalidOperationException>(() => DesignStateJsonSerializer.Deserialize(missingParameterIdJson));
        var ex2 = Assert.Throws<InvalidOperationException>(() => DesignStateJsonSerializer.Deserialize(missingDisplayNameJson));
        var ex3 = Assert.Throws<InvalidOperationException>(() => DesignStateJsonSerializer.Deserialize(missingCapturedAtJson));

        Assert.Contains("ParameterId", ex1.Message);
        Assert.Contains("DisplayName", ex2.Message);
        Assert.Contains("CapturedAtUtc", ex3.Message);
    }

    private static ParamState CreateSnapshot(params DesignStateParameter[] parameters)
    {
        var snapshot = new ParamState
        {
            StateId = "state-1",
            CapturedAtUtc = DateTimeOffset.Parse("2026-04-30T10:00:00.0000000Z"),
        };

        foreach (var parameter in parameters)
        {
            snapshot.Parameters.Add(parameter);
        }

        return snapshot;
    }
}
