using DG.Core.Models;
using DG.Core.Services;

namespace DG.Tests;

public sealed class DesignStateIdGeneratorTests
{
    private static List<DesignStateParameter> BuildParameters()
    {
        return new List<DesignStateParameter>
        {
            new()
            {
                ParameterId = "Height",
                DisplayName = "Height",
                Type = DesignStateParameterType.Number,
                NumberValue = 75.0,
            },
            new()
            {
                ParameterId = "Floors",
                DisplayName = "Floors",
                Type = DesignStateParameterType.Integer,
                IntegerValue = 12,
            },
            new()
            {
                ParameterId = "Active",
                DisplayName = "Active",
                Type = DesignStateParameterType.Boolean,
                BooleanValue = true,
            },
        };
    }

    [Fact]
    public void ComputeParamStateId_ShouldBeDeterministic_RegardlessOfInputOrder()
    {
        var parameters = BuildParameters();
        var reversed = new List<DesignStateParameter>(parameters);
        reversed.Reverse();

        var id1 = DesignStateIdGenerator.ComputeParamStateId(parameters);
        var id2 = DesignStateIdGenerator.ComputeParamStateId(reversed);

        Assert.Equal(id1, id2);
        Assert.StartsWith("DS_", id1);
    }

    [Fact]
    public void ComputeParamStateId_ShouldChange_WhenParameterIsAdded()
    {
        var parameters = BuildParameters();
        var withExtra = new List<DesignStateParameter>(parameters)
        {
            new()
            {
                ParameterId = "ExtraParam",
                DisplayName = "ExtraParam",
                Type = DesignStateParameterType.Boolean,
                BooleanValue = false,
            },
        };

        var originalId = DesignStateIdGenerator.ComputeParamStateId(parameters);
        var extendedId = DesignStateIdGenerator.ComputeParamStateId(withExtra);

        Assert.NotEqual(originalId, extendedId);
    }

    [Fact]
    public void ComputeObjectStateId_ShouldBeDeterministic_ForSameInputs()
    {
        var id1 = DesignStateIdGenerator.ComputeObjectStateId("proj-1", "OS_abc123", "?b");
        var id2 = DesignStateIdGenerator.ComputeObjectStateId("proj-1", "OS_abc123", "?b");

        Assert.Equal(id1, id2);
        Assert.StartsWith("OS_", id1);
    }

    [Fact]
    public void ComputeObjectStateId_ShouldHaveExactlyThreeStringParameters_ProvingCrossRuleIdentity()
    {
        var method = typeof(DesignStateIdGenerator).GetMethod("ComputeObjectStateId");

        Assert.NotNull(method);
        var parameters = method!.GetParameters();
        Assert.Equal(3, parameters.Length);
        Assert.All(parameters, p => Assert.Equal(typeof(string), p.ParameterType));
        Assert.DoesNotContain(parameters, p => string.Equals(p.Name, "ruleId", StringComparison.OrdinalIgnoreCase));
    }

    [Fact]
    public void ComputeObjectStateId_ShouldChange_WhenObjectInstanceIdChanges()
    {
        var id1 = DesignStateIdGenerator.ComputeObjectStateId("proj-1", "OS_abc123", "?b");
        var id2 = DesignStateIdGenerator.ComputeObjectStateId("proj-1", "OS_different", "?b");

        Assert.NotEqual(id1, id2);
    }

    // --- Phase 1202 Plan 06 Task 1: ComputeObjectStateIdFromRef (D-04 minting convergence) ---

    [Fact]
    public void ComputeObjectStateIdFromRef_ShouldReturnOsPrefixed16HexId()
    {
        var id = DesignStateIdGenerator.ComputeObjectStateIdFromRef("building-42", "ex:Building");

        Assert.StartsWith("OS_", id);
        Assert.Equal("OS_".Length + 16, id.Length);
    }

    [Fact]
    public void ComputeObjectStateIdFromRef_ShouldBeSame_WhenOnlyLabelDiffers()
    {
        // Label is no longer identity-bearing (D-04): the OBJECT STATE component's Label input
        // must not affect the ObjState id it mints, reversing the deleted duplicate's behavior.
        var id1 = DesignStateIdGenerator.ComputeObjectStateIdFromRef("building-42", "ex:Building");
        var id2 = DesignStateIdGenerator.ComputeObjectStateIdFromRef("building-42", "ex:Building");

        Assert.Equal(id1, id2);
    }

    [Fact]
    public void ComputeObjectStateIdFromRef_ShouldChange_WhenObjectRefChanges()
    {
        var id1 = DesignStateIdGenerator.ComputeObjectStateIdFromRef("building-42", "ex:Building");
        var id2 = DesignStateIdGenerator.ComputeObjectStateIdFromRef("building-43", "ex:Building");

        Assert.NotEqual(id1, id2);
    }

    [Fact]
    public void ComputeObjectStateIdFromRef_ShouldChange_WhenClassIriChanges_SameObjectRef()
    {
        var id1 = DesignStateIdGenerator.ComputeObjectStateIdFromRef("building-42", "ex:Building");
        var id2 = DesignStateIdGenerator.ComputeObjectStateIdFromRef("building-42", "ex:Site");

        Assert.NotEqual(id1, id2);
    }

    [Fact]
    public void ComputeObjectStateIdFromRef_NullClassIri_IsDeterministic_NotACrash()
    {
        var id1 = DesignStateIdGenerator.ComputeObjectStateIdFromRef("building-42", null);
        var id2 = DesignStateIdGenerator.ComputeObjectStateIdFromRef("building-42", null);

        Assert.Equal(id1, id2);
        Assert.StartsWith("OS_", id1);
    }

    [Fact]
    public void ComputeObjectStateIdFromRef_NullClassIri_DiffersFrom_NonNullClassIri()
    {
        // The null-classIri sentinel must not collide with any real classIri string.
        var withNull = DesignStateIdGenerator.ComputeObjectStateIdFromRef("building-42", null);
        var withClass = DesignStateIdGenerator.ComputeObjectStateIdFromRef("building-42", "ex:Building");

        Assert.NotEqual(withNull, withClass);
    }

    // --- Phase 1203-02 Task 2: project folded into DesignState hashes (D-08) ---

    [Fact]
    public void ComputeObjectStateIdFromRef_ShouldChange_WhenProjectDiffers()
    {
        var p1 = DesignStateIdGenerator.ComputeObjectStateIdFromRef("building-42", "ex:Building", "proj-a");
        var p2 = DesignStateIdGenerator.ComputeObjectStateIdFromRef("building-42", "ex:Building", "proj-b");

        Assert.NotEqual(p1, p2);
    }

    [Fact]
    public void ComputeObjectStateIdFromRef_NullProject_MatchesLegacyId()
    {
        // Omitting project (the shipping ObjectStateComponent call shape) must reproduce the
        // pre-D-08 id -- backward-compatible call shape, no crash.
        var legacy = DesignStateIdGenerator.ComputeObjectStateIdFromRef("building-42", "ex:Building");
        var explicitNull = DesignStateIdGenerator.ComputeObjectStateIdFromRef("building-42", "ex:Building", null);

        Assert.Equal(legacy, explicitNull);
    }

    [Fact]
    public void ComputeParamStateId_ShouldChange_WhenProjectDiffers()
    {
        var parameters = BuildParameters();

        var p1 = DesignStateIdGenerator.ComputeParamStateId(parameters, "proj-a");
        var p2 = DesignStateIdGenerator.ComputeParamStateId(parameters, "proj-b");

        Assert.NotEqual(p1, p2);
    }

    [Fact]
    public void ComputePropStateId_ShouldChange_WhenProjectDiffers()
    {
        var value = new DesignStateParameter
        {
            ParameterId = "height",
            DisplayName = "Height",
            Type = DesignStateParameterType.Number,
            NumberValue = 75.0,
        };

        var p1 = DesignStateIdGenerator.ComputePropStateId("dgm:Rule_R_URB_HEIGHT_MAX_75_V", "dg:hasHeight", value, null, "proj-a");
        var p2 = DesignStateIdGenerator.ComputePropStateId("dgm:Rule_R_URB_HEIGHT_MAX_75_V", "dg:hasHeight", value, null, "proj-b");

        Assert.NotEqual(p1, p2);
    }

    [Fact]
    public void ComputeObjectStateId_ThreeArg_ShouldRemainByteIdentical_ForFixedRegressionVector()
    {
        // Regression pin, re-derived Phase 1203-02 (D-09 length-prefix encoding replaces the
        // naive pipe-join for this method too -- CR-02 applies to every pipe-joined DesignState
        // minting function, not only DgIdMintingService.Mint). Pre-fix value was
        // "OS_493B9A7153D92072"; this is the post-fix value under the final EncodeHashInput
        // contract for the same fixed input ("proj-1", "OS_abc123", "?b").
        var id = DesignStateIdGenerator.ComputeObjectStateId("proj-1", "OS_abc123", "?b");

        Assert.Equal("OS_F8DD38C8DBB34D70", id);
    }

    [Fact]
    public void ComputeObjectStateId_PipeBoundaryShift_ProducesDifferentId()
    {
        // CR-02 collision regression for the 3-arg per-rule-variable form: two tuples sharing
        // the same naive pipe-join must not collide once the hash input is length-prefixed.
        // ("a|b","c","d") and ("a","b|c","d") both naively join to "a|b|c|d" -- under the
        // pre-fix implementation ($"{projectId}|{objectInstanceId}|{variableName}") these two
        // calls would hash the identical string and collide. This test only passes against the
        // length-prefix fix.
        var id1 = DesignStateIdGenerator.ComputeObjectStateId("a|b", "c", "d");
        var id2 = DesignStateIdGenerator.ComputeObjectStateId("a", "b|c", "d");

        Assert.NotEqual(id1, id2);
    }

    [Fact]
    public void ComputePropStateId_ShouldBeDeterministic_ForSameInputs()
    {
        var ruleIri = "dgm:Rule_R_URB_HEIGHT_MAX_75_V";
        var dataPropertyIri = "dg:hasHeight";
        var value = new DesignStateParameter
        {
            ParameterId = "height",
            DisplayName = "Height",
            Type = DesignStateParameterType.Number,
            NumberValue = 75.0,
        };

        var id1 = DesignStateIdGenerator.ComputePropStateId(ruleIri, dataPropertyIri, value);
        var id2 = DesignStateIdGenerator.ComputePropStateId(ruleIri, dataPropertyIri, value);

        Assert.Equal(id1, id2);
        Assert.StartsWith("PS_", id1);
    }

    [Fact]
    public void ComputePropStateId_ShouldChange_WhenRuleIriChanges()
    {
        var value = new DesignStateParameter
        {
            ParameterId = "height",
            DisplayName = "Height",
            Type = DesignStateParameterType.Number,
            NumberValue = 75.0,
        };

        var id1 = DesignStateIdGenerator.ComputePropStateId("dgm:Rule_R_URB_HEIGHT_MAX_75_V", "dg:hasHeight", value);
        var id2 = DesignStateIdGenerator.ComputePropStateId("dgm:Rule_R_URB_SETBACK_MIN_10_V", "dg:hasHeight", value);

        Assert.NotEqual(id1, id2);
    }

    [Fact]
    public void ComputePropStateId_ShouldChange_WhenValueChanges()
    {
        var value1 = new DesignStateParameter
        {
            ParameterId = "height",
            DisplayName = "Height",
            Type = DesignStateParameterType.Number,
            NumberValue = 75.0,
        };
        var value2 = new DesignStateParameter
        {
            ParameterId = "height",
            DisplayName = "Height",
            Type = DesignStateParameterType.Number,
            NumberValue = 100.0,
        };

        var id1 = DesignStateIdGenerator.ComputePropStateId("dgm:Rule_R_URB_HEIGHT_MAX_75_V", "dg:hasHeight", value1);
        var id2 = DesignStateIdGenerator.ComputePropStateId("dgm:Rule_R_URB_HEIGHT_MAX_75_V", "dg:hasHeight", value2);

        Assert.NotEqual(id1, id2);
    }

    [Fact]
    public void ComputePropStateId_ShouldChange_WhenObjectRefChanges()
    {
        // Two objects sharing the same rule + property + value must get distinct StateIds
        // when linked to different objects — otherwise they'd MERGE-collide in Neo4j.
        var value = new DesignStateParameter
        {
            ParameterId = "height",
            DisplayName = "Height",
            Type = DesignStateParameterType.Number,
            NumberValue = 60.0,
        };

        var id1 = DesignStateIdGenerator.ComputePropStateId("dgm:Rule_R_URB_HEIGHT_MAX_75_V", "dg:hasHeight", value, "B1");
        var id2 = DesignStateIdGenerator.ComputePropStateId("dgm:Rule_R_URB_HEIGHT_MAX_75_V", "dg:hasHeight", value, "B2");

        Assert.NotEqual(id1, id2);
        Assert.StartsWith("PS_", id1);
    }

    [Fact]
    public void ComputePropStateId_NullObjectRef_MatchesLegacyId()
    {
        // Passing no objectRef must reproduce the pre-per-object id (backward compatible).
        var value = new DesignStateParameter
        {
            ParameterId = "height",
            DisplayName = "Height",
            Type = DesignStateParameterType.Number,
            NumberValue = 75.0,
        };

        var legacy = DesignStateIdGenerator.ComputePropStateId("dgm:Rule_R_URB_HEIGHT_MAX_75_V", "dg:hasHeight", value);
        var explicitNull = DesignStateIdGenerator.ComputePropStateId("dgm:Rule_R_URB_HEIGHT_MAX_75_V", "dg:hasHeight", value, null);

        Assert.Equal(legacy, explicitNull);
    }

    [Fact]
    public void ComputeDesignStateId_ShouldBeDeterministic_ForSameMemberIds()
    {
        var memberIds = new List<string> { "OS_abc123", "DS_def456", "PS_ghi789" };

        var id1 = DesignStateIdGenerator.ComputeDesignStateId(memberIds);
        var id2 = DesignStateIdGenerator.ComputeDesignStateId(memberIds);

        Assert.Equal(id1, id2);
        Assert.StartsWith("DS_", id1);
    }

    [Fact]
    public void ComputeDesignStateId_ShouldBeDeterministic_RegardlessOfOrder()
    {
        var ordered = new List<string> { "OS_abc", "PS_def", "DS_ghi" };
        var reversed = new List<string> { "DS_ghi", "PS_def", "OS_abc" };

        var id1 = DesignStateIdGenerator.ComputeDesignStateId(ordered);
        var id2 = DesignStateIdGenerator.ComputeDesignStateId(reversed);

        Assert.Equal(id1, id2);
    }

    [Fact]
    public void ComputeDesignStateId_ShouldChange_WhenMembersChange()
    {
        var members1 = new List<string> { "OS_abc", "DS_def" };
        var members2 = new List<string> { "OS_abc", "DS_xyz" };

        var id1 = DesignStateIdGenerator.ComputeDesignStateId(members1);
        var id2 = DesignStateIdGenerator.ComputeDesignStateId(members2);

        Assert.NotEqual(id1, id2);
    }

    // --- Phase 1202 Plan 02 Task 3: ComputeCaptureEventStateId (D-01 layer 1) ---

    [Fact]
    public void ComputeDesignStateId_ShouldRemainByteIdentical_ForFixedRegressionVector()
    {
        // Regression pin (plan's own instruction): a future edit to the shared hash path must
        // not silently change historical StateIds. This literal was captured by running the
        // pre-existing (unmodified) ComputeDesignStateId against a fixed member set.
        //
        // Phase 1203-02 note: this literal is UNCHANGED by this plan. ComputeDesignStateId does
        // not call EncodeHashInput -- it concatenates sorted member StateIds with no separator at
        // all (not a pipe-join), so CR-02's pipe-boundary-shift defect does not apply to it, and
        // per this plan's own instruction it is one of the two aggregate functions
        // (ComputeDesignStateId, ComputeCaptureEventStateId) deliberately left without a project
        // parameter -- project reaches them transitively through their already-project-aware
        // member StateIds. D-03 (historical StateIds are not rewritten) is therefore honored by
        // construction, not merely by policy.
        var memberIds = new List<string> { "OS_REG_A", "PS_REG_B", "DS_REG_C" };

        var id = DesignStateIdGenerator.ComputeDesignStateId(memberIds);

        Assert.Equal("DS_3C3C50530BE1DED0", id);
    }

    [Fact]
    public void ComputeCaptureEventStateId_ShouldReturnDesignStatePrefixedId()
    {
        var memberIds = new List<string> { "OS_abc", "PS_def" };
        var capturedAt = new DateTimeOffset(2026, 9, 21, 12, 0, 0, TimeSpan.Zero);

        var id = DesignStateIdGenerator.ComputeCaptureEventStateId(memberIds, capturedAt);

        Assert.StartsWith("DS_", id);
    }

    [Fact]
    public void ComputeCaptureEventStateId_ShouldDiffer_ForDifferentCapturedAtUtc_WithSameMembers()
    {
        var memberIds = new List<string> { "OS_abc", "PS_def" };
        var capturedAt1 = new DateTimeOffset(2026, 9, 21, 12, 0, 0, TimeSpan.Zero);
        var capturedAt2 = new DateTimeOffset(2026, 9, 21, 12, 0, 1, TimeSpan.Zero);

        var id1 = DesignStateIdGenerator.ComputeCaptureEventStateId(memberIds, capturedAt1);
        var id2 = DesignStateIdGenerator.ComputeCaptureEventStateId(memberIds, capturedAt2);

        Assert.NotEqual(id1, id2);
    }

    [Fact]
    public void ComputeCaptureEventStateId_ShouldBeDeterministic_ForSameMembersAndSameCapturedAtUtc()
    {
        var memberIds = new List<string> { "OS_abc", "PS_def" };
        var capturedAt = new DateTimeOffset(2026, 9, 21, 12, 0, 0, TimeSpan.Zero);

        var id1 = DesignStateIdGenerator.ComputeCaptureEventStateId(memberIds, capturedAt);
        var id2 = DesignStateIdGenerator.ComputeCaptureEventStateId(memberIds, capturedAt);

        Assert.Equal(id1, id2);
    }

    [Fact]
    public void ComputeCaptureEventStateId_ShouldBeOrderIndependent_ForMemberIdOrder()
    {
        var ordered = new List<string> { "OS_abc", "PS_def", "DS_ghi" };
        var reversed = new List<string> { "DS_ghi", "PS_def", "OS_abc" };
        var capturedAt = new DateTimeOffset(2026, 9, 21, 12, 0, 0, TimeSpan.Zero);

        var id1 = DesignStateIdGenerator.ComputeCaptureEventStateId(ordered, capturedAt);
        var id2 = DesignStateIdGenerator.ComputeCaptureEventStateId(reversed, capturedAt);

        Assert.Equal(id1, id2);
    }

    [Fact]
    public void ComputeCaptureEventStateId_ShouldDiffer_FromContentAddressedId_ForSameMemberSet()
    {
        var memberIds = new List<string> { "OS_abc", "PS_def" };
        var capturedAt = new DateTimeOffset(2026, 9, 21, 12, 0, 0, TimeSpan.Zero);

        var contentAddressedId = DesignStateIdGenerator.ComputeDesignStateId(memberIds);
        var captureEventId = DesignStateIdGenerator.ComputeCaptureEventStateId(memberIds, capturedAt);

        Assert.NotEqual(contentAddressedId, captureEventId);
    }

    [Fact]
    public void ComputeCaptureEventStateId_ShouldNotModify_ComputeDesignStateIdBehavior()
    {
        // ComputeDesignStateId must remain byte-identical to its pre-plan behavior for every
        // input (D-03) -- this Fact exercises it standalone, independent of the new overload,
        // reproducing the exact literal two other Facts in this file already pinned before this
        // plan touched the file.
        var memberIds = new List<string> { "OS_abc123", "DS_def456", "PS_ghi789" };

        var id1 = DesignStateIdGenerator.ComputeDesignStateId(memberIds);
        var id2 = DesignStateIdGenerator.ComputeDesignStateId(memberIds);

        Assert.Equal(id1, id2);
        Assert.StartsWith("DS_", id1);
    }
}
