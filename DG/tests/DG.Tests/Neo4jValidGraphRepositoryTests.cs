using System.IO;
using System.Text.Json;
using DG.Core.Contracts;
using DG.Core.Data;
using DG.Core.Models;
using DG.Core.Serialization;

namespace DG.Tests;

public sealed class Neo4jValidGraphRepositoryTests
{
    [Fact]
    public void TryParseDesignState_WithV1Payload_ReturnsParamStateOnlyDesignState()
    {
        // v1 payload: ParamState with StateId, CapturedAtUtc, Parameters array
        var v1Json = """{"stateId":"PS_test","capturedAtUtc":"2026-07-04T12:00:00.0000000Z","parameters":[{"parameterId":"Height","displayName":"Height","type":"number","value":75}]}""";

        var result = Neo4jValidGraphRepository.TryParseDesignState(v1Json);

        Assert.NotNull(result);
        Assert.Equal("PS_test", result!.StateId);
        Assert.Single(result.ParamStates);
        Assert.Empty(result.ObjStates);
        Assert.Empty(result.PropStates);
    }

    [Fact]
    public void TryParseDesignState_WithV2Payload_ReturnsFullDesignState()
    {
        // v2 payload has stateKind or 3-part structure
        var v2Json = """{"stateId":"DS_test","capturedAtUtc":"2026-07-04T12:00:00.0000000Z","objStates":[],"paramStates":[],"propStates":[],"stateKind":"v2"}""";

        var result = Neo4jValidGraphRepository.TryParseDesignState(v2Json);

        Assert.NotNull(result);
        Assert.Equal("DS_test", result!.StateId);
    }

    [Fact]
    public void TryParseDesignState_WithV2PayloadObjStates_ReturnsFullDesignState()
    {
        // v2 payload detected by objStates key (alternative to stateKind)
        var v2Json = """{"stateId":"DS_test","capturedAtUtc":"2026-07-04T12:00:00.0000000Z","objStates":[{"stateId":"OS_001","objectRef":"Wall","capturedAtUtc":"2026-07-04T12:00:00.0000000Z"}],"paramStates":[],"propStates":[]}""";

        var result = Neo4jValidGraphRepository.TryParseDesignState(v2Json);

        Assert.NotNull(result);
        Assert.Equal("DS_test", result!.StateId);
        Assert.Single(result.ObjStates);
        Assert.Equal("OS_001", result.ObjStates[0].StateId);
    }

    [Fact]
    public void TryParseDesignState_WithNullJson_ReturnsNull()
    {
        var result = Neo4jValidGraphRepository.TryParseDesignState(null);
        Assert.Null(result);
    }

    [Fact]
    public void TryParseDesignState_WithEmptyJson_ReturnsNull()
    {
        var result = Neo4jValidGraphRepository.TryParseDesignState("");
        Assert.Null(result);
    }

    [Fact]
    public void TryParseDesignState_WithMalformedJson_ReturnsNull()
    {
        var result = Neo4jValidGraphRepository.TryParseDesignState("{invalid json}");
        Assert.Null(result);
    }

    [Fact]
    public void DesignStates_AreDeduplicatedByStateId()
    {
        // Simulate what the repository does after loading all runs
        var state1 = new DesignState { StateId = "DS_001" };
        var state2 = new DesignState { StateId = "DS_001" }; // Same ID — duplicate
        var state3 = new DesignState { StateId = "DS_002" };

        var allStates = new[] { state1, state2, state3 };
        var seen = new HashSet<string>(StringComparer.Ordinal);
        var distinct = allStates.Where(s => seen.Add(s.StateId)).ToList();

        Assert.Equal(2, distinct.Count);
        Assert.Contains(distinct, s => s.StateId == "DS_001");
        Assert.Contains(distinct, s => s.StateId == "DS_002");
    }

    [Fact]
    public void StatusList_LengthMatchesRunCount()
    {
        // D-03: Run and Status are 1:1 index-matched parallel lists
        var runs = new List<RunInfo> { new() { RunId = "R1" }, new() { RunId = "R2" } };
        var statuses = new List<IReadOnlyList<bool>> { new List<bool> { true }, new List<bool> { false } };

        Assert.Equal(runs.Count, statuses.Count);
    }

    [Fact]
    public void RunQuery_ShouldTargetValidGraphLayer()
    {
        var query = Neo4jValidGraphRepository.GetRunsQueryForTesting();
        Assert.Contains("graph:'ValidGraph'", query);
        Assert.Contains("project:$project", query);
        Assert.Contains("ORDER BY run.createdAt DESC, run.runId ASC", query);
    }

    [Fact]
    public void ParseRulesJson_WithEmptyArray_ReturnsEmpty()
    {
        var (ruleIds, results) = Neo4jValidGraphRepository.ParseRulesJson("[]");

        Assert.Empty(ruleIds);
        Assert.Empty(results);
    }

    [Fact]
    public void ParseRulesJson_WithValidArray_ReturnsSortedResults()
    {
        var json = """[{"ruleId":"R_B","passed":true},{"ruleId":"R_A","passed":false}]""";
        var (ruleIds, results) = Neo4jValidGraphRepository.ParseRulesJson(json);

        // Results should be sorted by ruleId
        Assert.Equal(2, ruleIds.Count);
        Assert.Equal("R_A", ruleIds[0]);
        Assert.Equal("R_B", ruleIds[1]);
        Assert.False(results[0]); // R_A passed = false
        Assert.True(results[1]);  // R_B passed = true
    }

    [Fact]
    public void ParseRulesJson_WithNullJson_ReturnsEmpty()
    {
        var (ruleIds, results) = Neo4jValidGraphRepository.ParseRulesJson(null);
        Assert.Empty(ruleIds);
        Assert.Empty(results);
    }

    [Fact]
    public void ParseTimestamp_WithValidIso8601_ReturnsParsed()
    {
        var result = Neo4jValidGraphRepository.ParseTimestamp("2026-07-04T12:00:00.0000000Z");
        Assert.Equal(new DateTimeOffset(2026, 7, 4, 12, 0, 0, TimeSpan.Zero), result);
    }

    [Fact]
    public void ParseTimestamp_WithNull_ReturnsMinValue()
    {
        var result = Neo4jValidGraphRepository.ParseTimestamp(null);
        Assert.Equal(DateTimeOffset.MinValue, result);
    }

    [Fact]
    public void ParseTimestamp_WithEmptyString_ReturnsMinValue()
    {
        var result = Neo4jValidGraphRepository.ParseTimestamp("");
        Assert.Equal(DateTimeOffset.MinValue, result);
    }

    // ── Phase 1202 plan 03 Task 2 (D-07/D-09): reader-parity proof and version
    // check. This Fact runs BOTH TryParseDesignState and
    // DesignStatePayloadV2Serializer.Deserialize against the same table of
    // payload inputs already covered by other Facts in this file, and records
    // whether the two readers agree or diverge -- Task 3 may only delete the
    // inline reader once this proof is green (RESEARCH.md Pitfall 2). Any
    // divergence must be an explicit, named assertion, never a silent pass.

    /// <summary>
    /// Walks up from the test assembly's output directory to the repo root, matching the
    /// pattern in SwrlSubsetConformanceTests.FindRepoRoot, so this works regardless of build
    /// configuration or target framework subfolder.
    /// </summary>
    private static string FindRepoRoot()
    {
        var dir = new DirectoryInfo(AppContext.BaseDirectory);
        while (dir is not null)
        {
            if (File.Exists(Path.Combine(dir.FullName, "spec", "evidence-contract.schema.json")))
            {
                return dir.FullName;
            }

            dir = dir.Parent;
        }

        throw new DirectoryNotFoundException(
            $"Neo4jValidGraphRepositoryTests.FindRepoRoot: could not locate repo root (spec/evidence-contract.schema.json) walking up from {AppContext.BaseDirectory}.");
    }

    private static string LoadMixedVerdictsStatePayloadJson()
    {
        var path = Path.Combine(FindRepoRoot(), "fixtures", "golden", "replay", "mixed-verdicts.json");
        using var doc = JsonDocument.Parse(File.ReadAllText(path));
        return doc.RootElement.GetProperty("statePayloadJson").GetString()
            ?? throw new InvalidOperationException("mixed-verdicts.json statePayloadJson was null.");
    }

    /// <summary>
    /// Table of payload strings drawn verbatim from the inputs the existing Facts in this file
    /// already use (plan 03 Task 2's Part A instruction): the plain v2 objStates payload and
    /// fixtures/golden/replay/mixed-verdicts.json's statePayloadJson. The accept-candidate writer
    /// envelope is asserted SEPARATELY below
    /// (<see cref="TryParseDesignState_AndSerializerDeserialize_DivergeOnAcceptCandidateWriterEnvelope"/>)
    /// because it is a documented, named divergence rather than an agreement case -- see that
    /// test's comment for why.
    /// </summary>
    public static IEnumerable<object[]> CoveredV2PayloadInputsExpectedToAgree()
    {
        // Same literal as TryParseDesignState_WithV2PayloadObjStates_ReturnsFullDesignState.
        yield return new object[]
        {
            "PlainV2ObjStates",
            """{"version":"2","stateId":"DS_test","capturedAtUtc":"2026-07-04T12:00:00.0000000Z","objStates":[{"stateId":"OS_001","objectRef":"Wall","capturedAtUtc":"2026-07-04T12:00:00.0000000Z"}],"paramStates":[],"propStates":[]}""",
        };
    }

    [Theory]
    [MemberData(nameof(CoveredV2PayloadInputsExpectedToAgree))]
    public void TryParseDesignState_AndSerializerDeserialize_AgreeOnCoveredInputs(string caseName, string payloadJson)
    {
        // caseName documents which covered input is under test when this Theory fails --
        // xunit already reports it as part of the test name via MemberData.
        Assert.False(string.IsNullOrWhiteSpace(caseName));

        var inlineResult = Neo4jValidGraphRepository.TryParseDesignState(payloadJson);

        DesignState? serializerResult = null;
        Exception? serializerException = null;
        try
        {
            serializerResult = DesignStatePayloadV2Serializer.Deserialize(payloadJson);
        }
        catch (Exception ex)
        {
            serializerException = ex;
        }

        // Every input in this agreement table is expected to be accepted by BOTH readers with
        // identical output. If the serializer throws here, that is an unanticipated divergence:
        // fail loudly (via this assertion) rather than silently treating a null inline result
        // and a thrown serializer exception as "agreement".
        Assert.Null(serializerException);
        Assert.NotNull(inlineResult);
        Assert.NotNull(serializerResult);

        AssertDesignStatesAgree(inlineResult!, serializerResult!);
    }

    /// <summary>
    /// NAMED, ASSERTED DIVERGENCE (plan 1202-03 Task 2 Part A finding, not fixed by this plan):
    /// TWO real, currently-shipping v2 parameter wire shapes exist for the SAME `parameters[]`
    /// array member, targeting two different call paths on purpose --
    /// <c>data-service/cg_paramstate_store.py:_build_state_payload_json</c>'s own docstring
    /// states this explicitly ("those are a different shape for a different call path"):
    ///   1. The accept-candidate writer's "flat" shape --
    ///      <c>{parameterId, displayName, type, numberValue, integerValue, booleanValue}</c> --
    ///      matches <see cref="DesignStateParameter"/>'s OWN CLR property names verbatim. The
    ///      INLINE reader (<see cref="Neo4jValidGraphRepository.TryParseDesignState"/>) deserializes
    ///      straight into that domain type, so this shape round-trips through it correctly by
    ///      construction.
    ///   2. <see cref="DesignStatePayloadV2Serializer"/>'s OWN Serialize()/Deserialize() shape --
    ///      the condensed <c>{parameterId, displayName, type, value}</c> pair its private DTOs use.
    /// Each reader was built against, and correctly handles, only ONE of these two shapes:
    ///   - The SERIALIZER throws <see cref="InvalidOperationException"/> ("Parameter value is
    ///     required.") on shape 1, because its <c>ParamFromDto</c>/<c>RequireJsonElement</c> path
    ///     requires a <c>value</c> key that shape 1 never has.
    ///   - The INLINE reader silently produces a parameter with EVERY typed value null on shape 2,
    ///     because <c>JsonSerializer.Deserialize&lt;DesignStateParameter&gt;</c> has no <c>Value</c>
    ///     property to bind the wire's <c>value</c> key to (confirmed live below).
    /// Per this plan's own instruction, this divergence is asserted explicitly here rather than
    /// silently treated as parity, and Task 3 (converging on the serializer's reader) is HALTED
    /// pending human/plan-04 disposition, because collapsing to the serializer's reader alone
    /// would silently break the accept-candidate write path's OWN wire shape today. See
    /// 1202-03-SUMMARY.md "Task 2 Parity Finding" for the full writeup.
    /// </summary>
    [Fact]
    public void TryParseDesignState_AndSerializerDeserialize_DivergeOnAcceptCandidateWriterEnvelope()
    {
        // Same literal as TryParseDesignState_WithAcceptCandidateWriterEnvelope_ParsesWithMatchingStateIdAndParameter
        // -- the accept-candidate writer's real "flat" wire shape (cg_paramstate_store.py).
        const string acceptCandidateWriterEnvelopeJson = """
            {"version":"2","stateId":"DS_A1B2C3D4E5F6A7B8","label":null,"capturedAtUtc":"2026-07-27T12:05:00Z","objStates":[],"paramStates":[{"stateId":"DS_A1B2C3D4E5F6A7B8","capturedAtUtc":"2026-07-27T12:05:00Z","parameters":[{"parameterId":"HTotal","displayName":"HTotal","type":"number","numberValue":40.0,"integerValue":null,"booleanValue":null}]}],"propStates":[]}
            """;

        // 1. The inline reader parses this shape correctly (direct CLR property-name match).
        var inlineResult = Neo4jValidGraphRepository.TryParseDesignState(acceptCandidateWriterEnvelopeJson);
        Assert.NotNull(inlineResult);
        var inlineParameter = Assert.Single(inlineResult!.ParamStates[0].Parameters);
        Assert.Equal("HTotal", inlineParameter.ParameterId);
        Assert.Equal(40.0, inlineParameter.NumberValue);

        // 2. The serializer's Deserialize() rejects the SAME shape outright -- it requires the
        // condensed {type, value} pair, which this shape does not have.
        var serializerException = Assert.Throws<InvalidOperationException>(
            () => DesignStatePayloadV2Serializer.Deserialize(acceptCandidateWriterEnvelopeJson));
        Assert.Contains("Parameter value is required", serializerException.Message, StringComparison.Ordinal);
    }

    /// <summary>
    /// NAMED, ASSERTED DIVERGENCE (companion to the Fact above, same root cause, opposite
    /// direction): the serializer's OWN condensed <c>{type, value}</c> wire shape -- which is
    /// what fixtures/golden/replay/mixed-verdicts.json's paramStates member actually carries, and
    /// what <see cref="DesignStatePayloadV2Serializer.Serialize"/> itself emits -- is silently
    /// mis-parsed by the INLINE reader: every typed value comes back null instead of throwing,
    /// because <c>JsonSerializer.Deserialize&lt;DesignStateParameter&gt;</c> has no <c>Value</c>
    /// CLR property for the wire's <c>value</c> key to bind to, and
    /// <c>System.Text.Json</c> silently ignores unmatched JSON properties by default.
    /// </summary>
    [Fact]
    public void TryParseDesignState_AndSerializerDeserialize_DivergeOnSerializerOwnConciseParameterShape()
    {
        var mixedVerdictsPayloadJson = LoadMixedVerdictsStatePayloadJson();

        // The serializer round-trips its own shape correctly.
        var serializerResult = DesignStatePayloadV2Serializer.Deserialize(mixedVerdictsPayloadJson);
        var serializerParameter = Assert.Single(serializerResult.ParamStates[0].Parameters);
        Assert.Equal("HeightSlider", serializerParameter.ParameterId);
        Assert.Equal(42.0, serializerParameter.NumberValue);

        // The inline reader silently drops the typed value on the SAME shape -- NumberValue,
        // IntegerValue, and BooleanValue all come back null, not 42.0. This is NOT a null the
        // fixture author intended; it is System.Text.Json's default unmatched-property behavior
        // combined with DesignStateParameter having no Value property.
        var inlineResult = Neo4jValidGraphRepository.TryParseDesignState(mixedVerdictsPayloadJson);
        Assert.NotNull(inlineResult);
        var inlineParameter = Assert.Single(inlineResult!.ParamStates[0].Parameters);
        Assert.Equal("HeightSlider", inlineParameter.ParameterId);
        Assert.Null(inlineParameter.NumberValue);
        Assert.Null(inlineParameter.IntegerValue);
        Assert.Null(inlineParameter.BooleanValue);
    }

    private static void AssertDesignStatesAgree(DesignState inlineResult, DesignState serializerResult)
    {
        Assert.Equal(inlineResult.StateId, serializerResult.StateId);
        Assert.Equal(inlineResult.CapturedAtUtc, serializerResult.CapturedAtUtc);

        Assert.Equal(inlineResult.ObjStates.Count, serializerResult.ObjStates.Count);
        var inlineObjByStateId = inlineResult.ObjStates.ToDictionary(o => o.StateId, StringComparer.Ordinal);
        foreach (var serializerObj in serializerResult.ObjStates)
        {
            Assert.True(
                inlineObjByStateId.TryGetValue(serializerObj.StateId, out var inlineObj),
                $"Inline reader is missing ObjState '{serializerObj.StateId}' that the serializer produced.");
            Assert.Equal(inlineObj!.ObjectRef, serializerObj.ObjectRef);
            Assert.Equal(inlineObj.ClassIri, serializerObj.ClassIri);
        }

        Assert.Equal(inlineResult.ParamStates.Count, serializerResult.ParamStates.Count);
        for (var i = 0; i < inlineResult.ParamStates.Count; i++)
        {
            var inlineParamState = inlineResult.ParamStates[i];
            var serializerParamState = serializerResult.ParamStates[i];
            Assert.Equal(inlineParamState.Parameters.Count, serializerParamState.Parameters.Count);

            var inlineParamsById = inlineParamState.Parameters.ToDictionary(p => p.ParameterId, StringComparer.Ordinal);
            foreach (var serializerParam in serializerParamState.Parameters)
            {
                Assert.True(
                    inlineParamsById.TryGetValue(serializerParam.ParameterId, out var inlineParam),
                    $"Inline reader is missing parameter '{serializerParam.ParameterId}' that the serializer produced.");
                Assert.Equal(inlineParam!.Type, serializerParam.Type);
                Assert.Equal(inlineParam.NumberValue, serializerParam.NumberValue);
                Assert.Equal(inlineParam.IntegerValue, serializerParam.IntegerValue);
                Assert.Equal(inlineParam.BooleanValue, serializerParam.BooleanValue);
            }
        }
    }

    [Fact]
    public void TryParseDesignState_WithVersion3Payload_ReturnsNull()
    {
        // D-07: a future v3 payload must be rejected outright, not structurally
        // sniffed and partially parsed as v2.
        var json = """{"version":"3","stateId":"DS_future","capturedAtUtc":"2026-07-04T12:00:00.0000000Z","objStates":[],"paramStates":[],"propStates":[]}""";

        var result = Neo4jValidGraphRepository.TryParseDesignState(json);

        Assert.Null(result);
    }

    [Fact]
    public void TryParseDesignState_WithVersion2Payload_StillParsesAsBefore()
    {
        var json = """{"version":"2","stateId":"DS_test","capturedAtUtc":"2026-07-04T12:00:00.0000000Z","objStates":[],"paramStates":[],"propStates":[]}""";

        var result = Neo4jValidGraphRepository.TryParseDesignState(json);

        Assert.NotNull(result);
        Assert.Equal("DS_test", result!.StateId);
    }

    [Fact]
    public void TryParseDesignState_WithVersionLessV1Payload_StillParsesThroughV1Fallback()
    {
        // A v1 payload carries no version key at all -- the version check must not
        // break the existing v1 fallback path.
        var v1Json = """{"stateId":"PS_versionless","capturedAtUtc":"2026-07-04T12:00:00.0000000Z","parameters":[{"parameterId":"Height","displayName":"Height","type":"number","value":75}]}""";

        var result = Neo4jValidGraphRepository.TryParseDesignState(v1Json);

        Assert.NotNull(result);
        Assert.Equal("PS_versionless", result!.StateId);
        Assert.Single(result.ParamStates);
    }

    // ── Phase 38 plan 38-05 Task 4: standalone-DesignState read tests ──

    [Fact]
    public void StandaloneStatesQuery_ShouldTargetParamStateOnValidGraphScopedToProject()
    {
        var query = Neo4jValidGraphRepository.GetStandaloneStatesQueryForTesting();
        Assert.Contains("kind:'ParamState'", query);
        Assert.Contains("graph:'ValidGraph'", query);
        Assert.Contains("project:$project", query);
        // No string-interpolated project literal anywhere in the query text.
        Assert.DoesNotContain("project:'", query);
    }

    [Fact]
    public void TryParseDesignState_WithAcceptCandidateWriterEnvelope_ParsesWithMatchingStateIdAndParameter()
    {
        // Literal fixture matching cg_paramstate_store.py's
        // _build_state_payload_json envelope shape verbatim (Phase 38 plan
        // 38-05 Task 1) -- the cheapest possible guard on the Python-writer /
        // C#-reader cross-language contract. A drift between the two sides
        // fails here rather than in Rhino.
        const string json = """
            {"version":"2","stateId":"DS_A1B2C3D4E5F6A7B8","label":null,"capturedAtUtc":"2026-07-27T12:05:00Z","objStates":[],"paramStates":[{"stateId":"DS_A1B2C3D4E5F6A7B8","capturedAtUtc":"2026-07-27T12:05:00Z","parameters":[{"parameterId":"HTotal","displayName":"HTotal","type":"number","numberValue":40.0,"integerValue":null,"booleanValue":null}]}],"propStates":[]}
            """;

        var result = Neo4jValidGraphRepository.TryParseDesignState(json);

        Assert.NotNull(result);
        Assert.Equal("DS_A1B2C3D4E5F6A7B8", result!.StateId);
        Assert.Single(result.ParamStates);
        Assert.Single(result.ParamStates[0].Parameters);
        var parameter = result.ParamStates[0].Parameters.First();
        Assert.Equal("HTotal", parameter.ParameterId);
        Assert.Equal(DesignStateParameterType.Number, parameter.Type);
        Assert.Equal(40.0, parameter.NumberValue);
    }

    [Fact]
    public void DesignStates_RunDerivedAndStandaloneStateWithSameStateId_YieldsOneEntry()
    {
        // Mirrors GetRunsAsync's own ordering: run-derived states are
        // collected first, then the additive standalone read (Task 3)
        // appends to the same list BEFORE the StateId dedup block runs
        // (D-04) -- a candidate that has since been validated into a run
        // must not be listed twice.
        var runDerivedState = new DesignState { StateId = "DS_shared" };
        var standaloneState = new DesignState { StateId = "DS_shared" };
        var otherStandaloneState = new DesignState { StateId = "DS_only_standalone" };

        var allStates = new List<DesignState> { runDerivedState, standaloneState, otherStandaloneState };

        var seen = new HashSet<string>(StringComparer.Ordinal);
        var distinct = allStates.Where(s => seen.Add(s.StateId)).ToList();

        Assert.Equal(2, distinct.Count);
        Assert.Contains(distinct, s => s.StateId == "DS_shared");
        Assert.Contains(distinct, s => s.StateId == "DS_only_standalone");
    }

    // ── Phase 1202 plan 01 Task 1: RED coverage for the additive per-object
    // verdict read path (D-13/D-14). PerObjectVerdict, VerdictSource,
    // PerObjectVerdictResult, Neo4jValidGraphRepository.BuildPerObjectVerdicts,
    // and Neo4jValidGraphRepository.GetEvidenceQueryForTesting do not exist yet
    // -- this file is expected to fail to compile until plan 04 implements them
    // verbatim against these exact symbol names and signatures. Do NOT add any
    // implementation here; the RED (non-compiling) state is this task's
    // deliverable.

    private static string BuildEnvelopeJson(params (string ruleId, string objectId, EvidenceStatus status)[] rows)
    {
        var rowsJson = string.Join(",", rows.Select(r =>
            $$"""{"ruleId":"{{r.ruleId}}","objectId":"{{r.objectId}}","canonicalStatus":"{{EvidenceStatusNames.ToWireName(r.status)}}"}"""));
        return $$"""{"contractVersion":"1","canonicalizationVersion":1,"project":"DG-1202-REPLAY","definitionId":"R_GOLD_HEIGHT_MAX_75_V","serviceName":"DG.Tests","serviceVersion":"test","emittedAt":"2026-09-21T00:00:00Z","stage":"validation.publish","canonicalStatus":"failed","rows":[{{rowsJson}}]}""";
    }

    [Fact]
    public void BuildPerObjectVerdicts_WithMixedRows_KeepsObjectVerdictsDistinct()
    {
        var envelopeJson = BuildEnvelopeJson(
            ("R_GOLD_HEIGHT_MAX_75_V", "OBJ_GOLD_PASS", EvidenceStatus.Passed),
            ("R_GOLD_HEIGHT_MAX_75_V", "OBJ_GOLD_FAIL", EvidenceStatus.Failed));

        var result = Neo4jValidGraphRepository.BuildPerObjectVerdicts(envelopeJson);

        Assert.True(result.EnvelopePresent);
        Assert.Equal(2, result.Verdicts.Count);

        var passVerdict = Assert.Single(result.Verdicts, v => v.ObjectId == "OBJ_GOLD_PASS");
        var failVerdict = Assert.Single(result.Verdicts, v => v.ObjectId == "OBJ_GOLD_FAIL");

        Assert.Equal(EvidenceStatus.Passed, passVerdict.Status);
        Assert.Equal(EvidenceStatus.Failed, failVerdict.Status);
        Assert.NotEqual(passVerdict.Status, failVerdict.Status);
    }

    [Fact]
    public void BuildPerObjectVerdicts_WithMultipleRowsPerObject_RollsUpByStatusRollupPrecedence()
    {
        // Two rows for the SAME objectId: one failed, one error. StatusRollup.Precedence
        // ranks Error ahead of Failed, so the rolled-up verdict for this object must be
        // Error -- proving D-12's precedence table drives the rollup, not a failed-wins rule.
        var envelopeJson = BuildEnvelopeJson(
            ("R_GOLD_HEIGHT_MAX_75_V", "OBJ_GOLD_FAIL", EvidenceStatus.Failed),
            ("R_OTHER_RULE", "OBJ_GOLD_FAIL", EvidenceStatus.Error));

        var result = Neo4jValidGraphRepository.BuildPerObjectVerdicts(envelopeJson);

        Assert.True(result.EnvelopePresent);
        var verdict = Assert.Single(result.Verdicts);
        Assert.Equal("OBJ_GOLD_FAIL", verdict.ObjectId);
        Assert.Equal(EvidenceStatus.Error, verdict.Status);
        Assert.Equal(EvidenceStatus.Error, StatusRollup.Precedence[0]);
    }

    [Fact]
    public void BuildPerObjectVerdicts_WithNullEnvelope_ReportsNotEvaluatedAndEnvelopeAbsent()
    {
        var result = Neo4jValidGraphRepository.BuildPerObjectVerdicts(null);

        Assert.False(result.EnvelopePresent);
        // D-11: absence of the envelope must never fabricate a verdict list --
        // no inference from a legacy boolean, no defaulted Passed entries.
        Assert.Empty(result.Verdicts);
    }

    [Fact]
    public void BuildPerObjectVerdicts_WithMalformedJson_DegradesToEnvelopeAbsent()
    {
        var result = Neo4jValidGraphRepository.BuildPerObjectVerdicts("{not json");

        Assert.False(result.EnvelopePresent);
        Assert.Empty(result.Verdicts);
    }

    [Fact]
    public void EvidenceQuery_ShouldSelectEvidenceEnvelopeJsonScopedToProjectAndRunId()
    {
        var query = Neo4jValidGraphRepository.GetEvidenceQueryForTesting();

        Assert.Contains("evidenceEnvelopeJson", query);
        Assert.Contains("graph:'ValidGraph'", query);
        Assert.Contains("$project", query);
        Assert.Contains("$runId", query);
    }

    [Fact(Skip = "Plan 04 wires this Fact to an active behavioral assertion once the additive per-object read path lands; today RunsQuery still fabricates StatusList via Enumerable.Repeat (Neo4jValidGraphRepository.cs:73-75) and no internal static seam exposes a per-run StatusList for a synthetic three-ObjState state without a live Neo4j session.")]
    public void RunsQuery_ShouldNotFabricateAPerObjectStatusList()
    {
        // Placeholder RED Fact (D-14): today's RunsQuery fabricates a per-object
        // status list via `Enumerable.Repeat(overallPass, objStateCount)`. Plan 04
        // removes that fabrication; this Fact becomes active then.
    }
}
