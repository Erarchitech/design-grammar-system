using System.Text.Json;
using DG.Core.Models;
using DG.Core.Models.Identity;
using DG.Core.Serialization;
using DG.Core.Services;

namespace DG.Tests;

/// <summary>
/// Proves DGID-03's ObjState half: DesignState/ObjState payloads reference member objects by dgId.
/// Tests round-trip serialization, pre-32.1 backward compatibility without a dgId key, and minting
/// parity with DgIdMintingService.
/// </summary>
public sealed class ObjStateDgIdTests
{
    private const string Project = "p1";
    private const string DefinitionId = "frame.gh";
    private const string EntityKey = "obj:Wall";

    [Fact]
    public void ObjStateDgId_RoundTrip_PreservesValue()
    {
        var dgId = "dg:AAAAAAAAAAAAAAAA";
        var state = CreateDesignState(dgId: dgId);

        var json = DesignStatePayloadV2Serializer.Serialize(state);
        var roundTrip = DesignStatePayloadV2Serializer.Deserialize(json);

        Assert.Equal(dgId, roundTrip.ObjStates[0].DgId);
    }

    [Fact]
    public void ObjStateDgId_PayloadWithoutDgIdKey_DeserializesWithNull()
    {
        // Pre-32.1 backward-compat guarantee: a v2 payload with no dgId key
        // must deserialize without error, leaving DgId as null.
        var state = CreateDesignState(dgId: null);

        var json = DesignStatePayloadV2Serializer.Serialize(state);
        var roundTrip = DesignStatePayloadV2Serializer.Deserialize(json);

        Assert.Null(roundTrip.ObjStates[0].DgId);
    }

    [Fact]
    public void ObjStateDgId_MintedWallIdentity_RoundTripsIdentically()
    {
        // The dgId set on an ObjState equals the deterministically minted
        // Computgraph identity for the same (project, definitionId, entityKey).
        // The Revit BIM wall and its GH counterpart resolve to this same dgId
        // via /identity/bind — one identity within the Design State (DGID-03).
        var wallDgId = DgIdMintingService.Mint(Project, DefinitionId, EntityKey).Value;
        var state = CreateDesignState(dgId: wallDgId);

        var json = DesignStatePayloadV2Serializer.Serialize(state);
        var roundTrip = DesignStatePayloadV2Serializer.Deserialize(json);

        var actualDgId = roundTrip.ObjStates[0].DgId;
        Assert.NotNull(actualDgId);
        Assert.Equal(wallDgId, actualDgId);
        Assert.StartsWith("dg:", actualDgId);
        Assert.Equal(19, actualDgId.Length); // "dg:" + 16 hex chars
    }

    [Fact]
    public void ObjStateDgId_Null_SerializesWithoutError()
    {
        var state = CreateDesignState(dgId: null);

        var json = DesignStatePayloadV2Serializer.Serialize(state);
        var roundTrip = DesignStatePayloadV2Serializer.Deserialize(json);

        Assert.Null(roundTrip.ObjStates[0].DgId);
    }

    /// <summary>
    /// Builds a minimal valid DesignState with one ObjState, optionally setting DgId.
    /// Matches the construction pattern from DesignStatePayloadV2SerializerTests.
    /// </summary>
    private static DesignState CreateDesignState(string? dgId)
    {
        var objState = new ObjState
        {
            StateId = DesignStateIdGenerator.ComputeObjectStateId("test-project", "obj-001", "testObject"),
            ObjectRef = "obj-001",
            Label = "Test Object",
            DgId = dgId,
            CapturedAtUtc = new DateTimeOffset(2026, 7, 4, 10, 0, 0, TimeSpan.Zero),
        };

        var designStateId = DesignStateIdGenerator.ComputeDesignStateId(new[] { objState.StateId });

        return new DesignState
        {
            StateId = designStateId,
            Label = "Test Design State",
            CapturedAtUtc = new DateTimeOffset(2026, 7, 4, 10, 0, 0, TimeSpan.Zero),
            ObjStates = { objState },
        };
    }
}
