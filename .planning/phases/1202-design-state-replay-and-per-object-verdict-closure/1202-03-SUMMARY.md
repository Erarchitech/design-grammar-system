---
phase: 1202-design-state-replay-and-per-object-verdict-closure
plan: 03
subsystem: database
tags: [json-serialization, design-state, csharp, xunit, reader-parity, tdd-halt]

requires:
  - phase: 1202-design-state-replay-and-per-object-verdict-closure (plan 01)
    provides: RED xUnit Facts naming PerObjectVerdict/BuildPerObjectVerdicts/GetEvidenceQueryForTesting (left untouched, still RED, as instructed); fixtures/golden/replay/mixed-verdicts.json
  - phase: 1202-design-state-replay-and-per-object-verdict-closure (plan 02)
    provides: DesignStateCanonicalProjection / design_state_projection.py; canonicalStateHash filled on the mixed-verdicts fixture
provides:
  - ObjStateDto.ClassIri as a normative optional member of the v2 payload (D-05), round-tripping through Serialize/Deserialize; absence still deserializes with null ClassIri
  - TryParseDesignState version check (D-07): a declared version other than "2" is rejected outright; a version-less payload still routes through the v1 fallback unchanged
  - A parity test suite proving where TryParseDesignState and DesignStatePayloadV2Serializer.Deserialize agree and, critically, a NAMED and ASSERTED divergence on a real production wire-shape mismatch that HALTS Task 3 (the reader-convergence deletion) pending disposition
affects: [1202-04, 1202-05, 1202-06, 1202-07]

tech-stack:
  added: []
  patterns:
    - "Repo-root-walk fixture loading in xUnit tests (SwrlSubsetConformanceTests.FindRepoRoot precedent), reused for loading fixtures/golden/replay/mixed-verdicts.json's statePayloadJson at test time"
    - "Divergence-as-named-Fact: when a cross-reader parity proof finds unequal behavior, assert BOTH observed behaviors explicitly in dedicated Facts rather than folding them into a generic equality assertion that would either mask the divergence or fail uninformatively"

key-files:
  created: []
  modified:
    - DG/src/DG.Core/Serialization/DesignStatePayloadV2Serializer.cs
    - DG/tests/DG.Tests/DesignStatePayloadV2SerializerTests.cs
    - DG/src/DG.Core/Data/Neo4jValidGraphRepository.cs
    - DG/tests/DG.Tests/Neo4jValidGraphRepositoryTests.cs

key-decisions:
  - "Task 3 (delegate TryParseDesignState's v2 branch to DesignStatePayloadV2Serializer.Deserialize, deleting the inline JsonSerializer path and manual Parameters backfill) is NOT executed in this plan run. The plan's own <critical_ordering_note> and Task 2's <action> text both explicitly instruct: if the parity proof surfaces an unanticipated divergence, STOP and report rather than proceeding. Task 2 found exactly such a divergence (see Deviations below) and this executor halted per that instruction."
  - "The divergence found is a REAL, currently-shipping dual wire-shape for a v2 parameter: the accept-candidate writer path (data-service/cg_paramstate_store.py, whose own docstring says 'a different shape for a different call path') emits {parameterId,displayName,type,numberValue,integerValue,booleanValue}, matching DesignStateParameter's CLR property names verbatim -- this is what the INLINE reader parses correctly by construction. DesignStatePayloadV2Serializer's OWN Serialize()/Deserialize() round-trip (and therefore fixtures/golden/replay/mixed-verdicts.json's paramStates member, and any hand-authored fixture using the serializer's shape) uses the condensed {parameterId,displayName,type,value} pair. Each reader was built against, and only correctly handles, ONE of these two shapes."
  - "Rather than silently accept or paper over the divergence, both directions are captured as dedicated, permanently-named Facts (TryParseDesignState_AndSerializerDeserialize_DivergeOnAcceptCandidateWriterEnvelope and its companion _DivergeOnSerializerOwnConciseParameterShape) so the finding is machine-checked evidence, not prose asserted once and then forgotten."

patterns-established:
  - "A parity/convergence proof that finds a genuine divergence should split its input table into an 'expected to agree' MemberData Theory and separate, explicitly-named Facts per divergence -- this keeps the agreement cases fast and readable while making each divergence individually diagnosable (and individually fixable later) rather than bundled into one large assertion block."

requirements-completed: [ALGN12-09]

coverage:
  - id: D1
    description: "ObjStateDto carries ClassIri; it round-trips Serialize->Deserialize when present, stays null when absent (both explicit-null and key-absent forms), is emitted under the camelCase classIri wire key, and the payload version stays \"2\""
    requirement: "ALGN12-09"
    verification:
      - kind: unit
        ref: "DesignStatePayloadV2SerializerTests.cs (18 Facts total, 4 new: SerializeDeserialize_RoundTrip_ShouldPreserveClassIriWhenPresent, SerializeDeserialize_RoundTrip_ShouldPreserveNullClassIri, Serialize_ShouldEmitClassIriUnderCamelCaseKey, Deserialize_WithoutClassIriKey_ShouldSucceedWithNullClassIri) -- run via isolated harness against DG.Core.dll since the full DG.Tests assembly is Wave-0-RED per plan 01"
        status: pass
      - kind: other
        ref: "grep -c ClassIri DesignStatePayloadV2Serializer.cs == 3; grep -c 'Version = \"2\"' == 1; grep -c 'Version != \"2\"' == 1; grep -c WithoutClassIri DesignStatePayloadV2SerializerTests.cs == 1"
        status: pass
    human_judgment: false
  - id: D2
    description: "TryParseDesignState rejects a payload whose declared version is not \"2\" (returns null) while a version-less v1 payload still parses through the v1 fallback unchanged; the existing v1 Fact's body is untouched"
    requirement: "ALGN12-09"
    verification:
      - kind: unit
        ref: "Neo4jValidGraphRepositoryTests.cs: TryParseDesignState_WithVersion3Payload_ReturnsNull, TryParseDesignState_WithVersion2Payload_StillParsesAsBefore, TryParseDesignState_WithVersionLessV1Payload_StillParsesThroughV1Fallback -- run via isolated harness (assembly named DG.Tests to satisfy DG.Core's InternalsVisibleTo, RED region from plan 01 excluded from the compile unit only, never from the committed repo file)"
        status: pass
      - kind: other
        ref: "git diff -- Neo4jValidGraphRepositoryTests.cs shows zero deletion lines (insertions-only); TryParseDesignState_WithV1Payload_ReturnsParamStateOnlyDesignState body absent from the diff entirely"
        status: pass
    human_judgment: false
  - id: D3
    description: "A parity Fact proves where TryParseDesignState and DesignStatePayloadV2Serializer.Deserialize agree on covered inputs (plain v2 objStates payload), and explicitly names/asserts a real divergence discovered on the accept-candidate writer envelope and the serializer's own concise parameter shape -- Task 3's reader-convergence delete is correctly halted rather than executed on an unverified assumption of safety"
    requirement: "ALGN12-09"
    verification:
      - kind: unit
        ref: "Neo4jValidGraphRepositoryTests.cs: TryParseDesignState_AndSerializerDeserialize_AgreeOnCoveredInputs (Theory, 1 agreement case), TryParseDesignState_AndSerializerDeserialize_DivergeOnAcceptCandidateWriterEnvelope, TryParseDesignState_AndSerializerDeserialize_DivergeOnSerializerOwnConciseParameterShape -- 24 passed, 1 skipped (plan-01 placeholder) via isolated harness"
        status: pass
    human_judgment: true
    rationale: "Task 3's disposition (whether to converge on the serializer's reader anyway with a compatibility shim, extend the serializer to accept both shapes, or leave the two readers permanently split with a documented exclusion contract) is an architectural decision under Rule 4 -- it changes a currently-shipping cross-language write/read contract (data-service Python writer vs. C# readers) and needs explicit human/plan-04 direction, not an executor's unilateral choice."

duration: ~25min
completed: 2026-09-22
status: complete
---

# Phase 1202 Plan 03: ClassIri Normativity and Reader-Parity Proof (Task 3 Halted) Summary

**Added ClassIri as a normative optional ObjStateDto member and a version check to TryParseDesignState, then discovered via the mandated parity proof that the two v2 payload readers disagree on a real, currently-shipping wire shape -- halting Task 3's reader-convergence deletion per the plan's own explicit stop instruction rather than deleting code before its safety was actually proven.**

## Performance

- **Duration:** ~25 min
- **Started:** 2026-09-21 (session date at task start)
- **Completed:** 2026-09-22
- **Tasks:** 2/3 completed (Task 3 halted by design, not failed)
- **Files modified:** 4

## Accomplishments

- `ObjStateDto` gained `public string? ClassIri { get; init; }`, wired through both `ToDto`/`FromDto` mapping directions. Optional-additive per D-07: a payload with no `classIri` key still deserializes with `ClassIri` null. Payload version literal untouched (`"2"`). 4 new Facts added to `DesignStatePayloadV2SerializerTests.cs` (18 total): present-ClassIri round-trip, null-ClassIri round-trip, camelCase wire-key emission, and a legacy no-classIri-key payload (`Deserialize_WithoutClassIriKey_ShouldSucceedWithNullClassIri`).
- `TryParseDesignState` gained an explicit `version` field check (D-07's bundled mandatory fix) before the existing structural sniff: a declared version other than `"2"` returns `null` outright (a future v3 is rejected, not partially parsed); a payload with no `version` key at all (v1's shape) falls through unchanged to the structural sniff and, failing that, the v1 fallback. 3 new Facts confirm this: version-3 rejected, version-2 unaffected, version-less v1 still parses. The pre-existing `TryParseDesignState_WithV1Payload_ReturnsParamStateOnlyDesignState` Fact's body is byte-identical (confirmed via `git diff` showing zero deletion lines in the whole file).
- Built the mandated Task 2 parity proof (`TryParseDesignState_AndSerializerDeserialize_AgreeOnCoveredInputs`, a `Theory` over the plain v2 objStates payload and `fixtures/golden/replay/mixed-verdicts.json`) and ran it BEFORE touching any Task 3 code, per the plan's `<critical_ordering_note>`.
- **The parity proof found a real, unanticipated divergence** (full writeup below) and, per the plan's own explicit instruction, this executor **stopped and reported it instead of proceeding to Task 3**. Both directions of the divergence are captured as dedicated, permanently-named Facts (`TryParseDesignState_AndSerializerDeserialize_DivergeOnAcceptCandidateWriterEnvelope` and `_DivergeOnSerializerOwnConciseParameterShape`) rather than left as a one-time prose note, so the finding stays machine-checked.

## Task Commits

Each completed task was committed atomically:

1. **Task 1: Add ClassIri as a normative optional ObjStateDto member (D-05)** - `a88e6e4` (feat)
2. **Task 2: Prove reader parity before convergence, and add the missing version check (D-07)** - `20342c1` (test)
3. **Task 3: Converge the two readers** - **NOT EXECUTED.** Halted per the plan's own stop instruction after Task 2's parity proof surfaced an unanticipated divergence. See "Task 2 Parity Finding" below.

_No plan-metadata commit created by this executor — orchestrator owns STATE.md/ROADMAP.md updates centrally for this wave per the sequential-mode contract._

## Files Created/Modified

- `DG/src/DG.Core/Serialization/DesignStatePayloadV2Serializer.cs` - `ObjStateDto.ClassIri` added; wired through `ToDto`/`FromDto`.
- `DG/tests/DG.Tests/DesignStatePayloadV2SerializerTests.cs` - 4 new Facts for ClassIri round-trip/absence/wire-key behavior; `CreateDesignState()`'s `objState1` given `ClassIri = "ex:Building"`, `objState2` deliberately left null to cover both branches.
- `DG/src/DG.Core/Data/Neo4jValidGraphRepository.cs` - `TryParseDesignState` gained the D-07 version-field check before the structural sniff.
- `DG/tests/DG.Tests/Neo4jValidGraphRepositoryTests.cs` - Added: `FindRepoRoot`/`LoadMixedVerdictsStatePayloadJson` helpers, `CoveredV2PayloadInputsExpectedToAgree` MemberData + `TryParseDesignState_AndSerializerDeserialize_AgreeOnCoveredInputs` Theory, the two named divergence Facts, `AssertDesignStatesAgree` shared assertion helper, and 3 version-check Facts. Insertions-only diff — no existing Fact body touched, and the plan-01 RED region (referencing `PerObjectVerdict`/`BuildPerObjectVerdicts`/`GetEvidenceQueryForTesting`) is completely untouched.

## Task 2 Parity Finding (recorded verbatim per the plan's `<output>` instruction)

**The parity Fact's outcome, in full, BEFORE any Task 3 code was touched:**

Running the parity Theory against the plan's specified input table (accept-candidate writer envelope, plain v2 objStates payload, v2 payload with a real parameter, `mixed-verdicts.json`) surfaced two real divergences on two of the four inputs:

**Divergence 1 — `TryParseDesignState_AndSerializerDeserialize_DivergeOnAcceptCandidateWriterEnvelope`:**
The accept-candidate writer envelope (`{"parameterId":"HTotal","displayName":"HTotal","type":"number","numberValue":40.0,"integerValue":null,"booleanValue":null}`) is parsed correctly by the **inline reader** (`NumberValue == 40.0`) but **rejected outright** by `DesignStatePayloadV2Serializer.Deserialize`, which throws `InvalidOperationException: "Parameter value is required."` from `ParamFromDto` → `RequireJsonElement`, because the serializer's DTO expects a `value` key that this shape does not have.

**Divergence 2 — `TryParseDesignState_AndSerializerDeserialize_DivergeOnSerializerOwnConciseParameterShape`:**
The serializer's own concise shape (`{"parameterId":"HeightSlider","displayName":"Height Slider","type":"number","value":42.0}`, which is exactly what `fixtures/golden/replay/mixed-verdicts.json`'s `paramStates` member carries) is parsed correctly by the **serializer** (`NumberValue == 42.0`) but **silently mis-parsed** by the **inline reader**: `NumberValue`, `IntegerValue`, and `BooleanValue` all come back `null` instead of `42.0`, with no exception, because `JsonSerializer.Deserialize<DesignStateParameter>` has no `Value` CLR property to bind the wire's `value` key to and `System.Text.Json` silently ignores unmatched properties by default.

**Root cause, confirmed by reading the producing code directly (not inferred):** `data-service/cg_paramstate_store.py`'s `_build_state_payload_json` docstring states this explicitly and by design:

> "each parameter is written with the model's OWN camelCase property names (`parameterId`, `displayName`, `type`, `numberValue`, `integerValue`, `booleanValue`), never the condensed `{type, value}` pair `DesignStatePayloadV2Serializer`'s private DTOs use for ITS OWN Serialize()/Deserialize() round-trip -- those are a different shape for a different call path."

So this is **not a bug introduced by drift** — it is a previously-undocumented-as-a-risk but deliberately-designed dual wire shape: the accept-candidate write path (Python) and `DesignStatePayloadV2Serializer`'s own round-trip (C#) each emit v2 `parameters[]` members in a different, mutually-incompatible shape, and until this parity proof, **nothing tested them against each other's shape** — each reader was validated only against its own producer's output.

**Why this is Task 3's blocker, not a Rule 1-3 auto-fix:** Task 3's instruction is to delete `TryParseDesignState`'s inline `JsonSerializer.Deserialize<DesignState>` path entirely and delegate the v2 branch to `DesignStatePayloadV2Serializer.Deserialize`. Doing so today would mean:
- Every accept-candidate-writer-produced `statePayloadJson` already stored in Neo4j (flat shape) would throw `InvalidOperationException` inside the converged reader instead of parsing — caught by the broad `catch (Exception) { return null; }`, so `GetRunsAsync` would silently drop these rows' parsed `DesignState` (their `ParamStates`/`Parameters` would vanish from `TryParseDesignState`'s output) rather than crash, but the round-trip this plan exists to make reachable would break for exactly the write path Phase 38-05 built it for.
- This is an architectural collision between two independently-evolved wire-shape conventions on the SAME `parameters[]` array member — a currently-shipping cross-language contract, not a local bug. Per the deviation rules, this is Rule 4 (architectural change requiring a decision), not Rules 1-3.

**Disposition options for plan 04 (or a human) to choose from, not decided here:**
1. Extend `DesignStatePayloadV2Serializer`'s `ParamFromDto`/`ParseNumber`/`ParseInteger`/`ParseBoolean` to accept EITHER shape (condensed `value` OR flat `numberValue`/`integerValue`/`booleanValue`) before Task 3 converges the readers — makes the serializer a superset reader, no writer-side change needed.
2. Change `data-service/cg_paramstate_store.py`'s writer to emit the serializer's condensed shape instead — but this changes a live Python write path outside this C#-scoped plan's `files_modified` list, and needs its own decision about backward-compat with previously-written flat-shape rows already in Neo4j.
3. Leave the two readers permanently split with a documented exclusion contract (the ROADMAP's own "or an explicit exclusion contract" escape hatch) — accept that `TryParseDesignState` and `DesignStatePayloadV2Serializer.Deserialize` are NOT the same reader, contrary to D-09, and document why.

This executor did not select an option — Rule 4 requires a human/architectural decision, and Task 2's own action text explicitly instructs to stop and report rather than paper over the finding by loosening the serializer's validation.

## Decisions Made

- Task 3 is not executed in this plan run. The plan's `<critical_ordering_note>` states verbatim: "If Task 2 finds an unanticipated divergence, STOP before Task 3 and report it rather than proceeding." That condition was met.
- The divergence is captured as two permanently-named xUnit Facts rather than a one-time report, so it remains machine-checked evidence for whichever future plan resolves it (rather than becoming stale prose nobody re-verifies).
- `TryParseDesignState`'s version check (Task 2 Part B) was still added, since it is an independent, additive fix explicitly described as "bundled mandatory... regardless of the version decision" and does not touch the reader-convergence question — its own 3 Facts pass cleanly and it does not interact with the parameter-shape divergence.

## Deviations from Plan

### Auto-fixed Issues

None — no Rule 1/2/3 auto-fixes were needed in the completed tasks.

### Halted Task (Rule 4 — architectural decision required)

**1. [Rule 4] Task 3 (reader convergence, D-09) halted pending disposition of a real dual-wire-shape collision**

- **Found during:** Task 2's mandated parity proof (Part A), run BEFORE any Task 3 code was touched, exactly as the plan's ordering requires.
- **Issue:** `TryParseDesignState` (inline reader) and `DesignStatePayloadV2Serializer.Deserialize` each correctly parse only ONE of two mutually-incompatible, currently-shipping v2 `parameters[]` wire shapes — the accept-candidate writer's flat shape (`numberValue`/`integerValue`/`booleanValue`) and the serializer's own condensed shape (`value`). Converging onto the serializer's reader alone (Task 3's literal instruction) would silently drop typed parameter values for every already-stored accept-candidate-writer payload.
- **Why not auto-fixed:** This is a cross-language, cross-service (C# reader / Python writer) wire-contract collision, not a local code bug. Fixing it requires choosing among architecturally distinct options (extend the serializer to be a shape superset, change the Python writer, or formally split the readers) — squarely Rule 4's territory, and the plan's own text explicitly instructs stopping here rather than guessing.
- **Action taken:** Documented both divergence directions as dedicated, passing, permanently-named Facts; wrote up the full finding and three disposition options in this SUMMARY for the next plan/human decision; did not modify `TryParseDesignState`'s v2 branch body, its inline `JsonSerializer.Deserialize<DesignState>` call, or its manual `Parameters` backfill loop (all remain exactly as they were before this plan, apart from the Task 2 version-check addition, which sits earlier in the method and does not touch this code).
- **Files affected:** None beyond the parity-Fact addition itself (test-only); no production code deletion occurred.
- **Verification:** `TryParseDesignState_AndSerializerDeserialize_DivergeOnAcceptCandidateWriterEnvelope` and `TryParseDesignState_AndSerializerDeserialize_DivergeOnSerializerOwnConciseParameterShape` both pass, documenting the exact behavior of each reader on each shape.

---

**Total deviations:** 1 halted task (Rule 4, architectural)
**Impact on plan:** Tasks 1 and 2 are fully complete and independently valuable (ClassIri normativity, the version check, and the parity evidence itself). Task 3 is deliberately incomplete — executing it as literally instructed would have silently regressed a currently-shipping write path, which the plan's own safety gate exists to prevent.

## Issues Encountered

- **`dotnet test DG/tests/DG.Tests/ -v minimal --filter <Name>` cannot run** for either task in this plan, because the whole `DG.Tests` assembly still fails to compile (`CS0117` on `BuildPerObjectVerdicts`/`GetEvidenceQueryForTesting`) — this is plan 01's own documented Wave 0 RED outcome, unrelated to and untouched by this plan. Verified via the isolated-harness workaround established by plan 02 (build `DG.Core` standalone, run a scratch xUnit project outside the repo referencing the compiled `DG.Core.dll`, with the harness assembly named `DG.Tests` to satisfy `DG.Core`'s `InternalsVisibleTo(DG.Tests)` restriction on `internal static` members like `TryParseDesignState`). For each task, the harness's copy of the changed test file was trimmed to exclude ONLY the plan-01 RED region (by content marker, not line count) before compiling — the committed repo file was never trimmed; only the disposable scratch copy was. The harness and all scratch scaffolding were deleted after use; no repo file was created or left behind.
- Confirmed live (not assumed) that the whole-assembly compile failure is unchanged by this plan's edits: `dotnet build DG/tests/DG.Tests/ -v quiet` before Task 1 showed exactly the same 5 `CS0117` errors documented in `1202-01-SUMMARY.md`.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- **Task 3 of this plan (1202-03) is NOT done and must be resumed**, not skipped, by whichever plan closes out D-09. The three disposition options above are the starting point; option 1 (extend the serializer's parameter parsing to accept both shapes) is likely the lowest-blast-radius choice since it keeps the change scoped to `DG.Core` and does not touch the live Python writer or require a data migration, but this executor deliberately did not choose for the human/next plan.
- Plan 04 (per-object verdict read path, `BuildPerObjectVerdicts`/`GetEvidenceQueryForTesting`) resolves the `DG.Tests` assembly compile failure that has blocked normal `dotnet test` runs since plan 01. Once that lands, re-run the full suite including this plan's new Facts (22 new: 4 in `DesignStatePayloadV2SerializerTests.cs`, 18 in `Neo4jValidGraphRepositoryTests.cs`) to confirm no regression beyond the 4 known Neo4j-down failures.
- `ObjStateDto.ClassIri` (Task 1) is fully independent of the Task 3 halt and is safe for any downstream consumer today — it is additive-only and does not touch the parameter-shape question at all (`ClassIri` lives on `ObjStateDto`, the divergence is on `ParameterDto`/`DesignStateParameter`).
- The `fixtures/golden/replay/mixed-verdicts.json` fixture's `expectedCanonicalStateHash` (populated in plan 02) is unaffected by this plan's ClassIri addition, since plan 02's hash was computed via the Python projection path, which already read `classIri` from the raw wire dict — re-verify per plan 02's own "Next Phase Readiness" note once the C# `DesignStatePayloadV2Serializer.Deserialize` → `DesignStateCanonicalProjection.ComputeHash` path is exercised against this fixture (now that `ClassIri` round-trips), separately from this plan's Task 3 halt.
- No blocker for parallel wave-1 sibling plans that do not depend on `Neo4jValidGraphRepository`'s reader convergence.

---
*Phase: 1202-design-state-replay-and-per-object-verdict-closure*
*Completed: 2026-09-22*

## Self-Check: PASSED

All modified files verified present on disk:
- FOUND: DG/src/DG.Core/Serialization/DesignStatePayloadV2Serializer.cs (modified)
- FOUND: DG/tests/DG.Tests/DesignStatePayloadV2SerializerTests.cs (modified)
- FOUND: DG/src/DG.Core/Data/Neo4jValidGraphRepository.cs (modified)
- FOUND: DG/tests/DG.Tests/Neo4jValidGraphRepositoryTests.cs (modified)

Both commit hashes verified in git log: a88e6e4, 20342c1.
