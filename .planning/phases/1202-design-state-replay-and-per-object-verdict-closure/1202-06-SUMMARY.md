---
phase: 1202-design-state-replay-and-per-object-verdict-closure
plan: 06
subsystem: grasshopper-plugin
tags: [design-state-identity, objstate, minting-convergence, sha-256, grasshopper]

requires:
  - phase: 1202-design-state-replay-and-per-object-verdict-closure (plan 02)
    provides: DesignStateIdGenerator's rewritten class doc-comment (D-01 two-layer identity contract), HashToHex16, ObjectStatePrefix
provides:
  - DesignStateIdGenerator.ComputeObjectStateIdFromRef(objectRef, classIri?) -- the single function that now mints every ObjState ID produced by ObjectStateComponent
  - Deletion of ObjectStateComponent's private ComputeObjStateId duplicate (the label-folding minting path)
affects: [1202-07]

tech-stack:
  added: []
  patterns:
    - "Additive overload over signature force-fit: when an existing multi-arg minting method's semantics don't match a new caller's available inputs, add a differently-named overload rather than synthesizing fake arguments for the old one"
    - "Stable non-string sentinel (\\u0000no-class-iri\\u0000) for a nullable hash input, chosen to be unreachable by any real classIri string"

key-files:
  created: []
  modified:
    - DG/src/DG.Core/Services/DesignStateIdGenerator.cs
    - DG/src/DG.Grasshopper/Components/ObjectStateComponent.cs
    - DG/tests/DG.Tests/DesignStateIdGeneratorTests.cs

key-decisions:
  - "Pitfall 1 resolved as option (b) from RESEARCH.md: an additive overload (ComputeObjectStateIdFromRef), not a force-fit of the existing 3-arg ComputeObjectStateId(projectId, objectInstanceId, variableName). ObjectStateComponent has no Project port and no per-geometry-instance variableName concept; synthesizing fake values for either would satisfy D-04 in name while destroying the 3-arg method's documented per-rule-variable (CMPST-07) semantics. The 3-arg method is untouched -- confirmed via a regression Fact pinning its output for a fixed input."
  - "Label is deliberately excluded from the new hash input (objectRef + classIri only), reversing the deleted duplicate's objectRef|label formula. This is an intended, surfaced-at-checkpoint behavior change: renaming an object no longer changes its ObjState identity."
  - "Null classIri hashed against a stable non-string sentinel (\\u0000no-class-iri\\u0000) rather than an empty string, so a real empty-string classIri (if one ever occurred) cannot collide with the null case -- verified by a dedicated non-collision Fact."

requirements-completed: [ALGN12-08]

coverage:
  - id: T1
    description: "One minting function serves ObjectStateComponent; the private duplicate is deleted; Label is no longer identity-bearing; the 3-arg per-rule-variable method is untouched"
    requirement: "ALGN12-08"
    verification:
      - kind: unit
        ref: "dotnet test DG/tests/DG.Tests/ -v minimal --filter DesignStateIdGeneratorTests -- 27/27 passed"
        status: pass
      - kind: other
        ref: "grep -c 'private static string ComputeObjStateId' ObjectStateComponent.cs == 0; grep -v '^\\s*//' | grep -cE 'SHA256\\.HashData' == 0; grep -c 'DesignStateIdGenerator.ComputeObjectStateIdFromRef' == 1; grep -c 'ComputeObjectStateId(string projectId' DesignStateIdGenerator.cs == 1"
        status: pass
    human_judgment: false
  - id: T2
    description: "The Grasshopper plugin rebuilds cleanly under the GRASSHOPPER_SDK guard"
    requirement: "ALGN12-08"
    verification:
      - kind: unit
        ref: "dotnet build DG/DG.sln -c Release -- Warnings: 0, Errors: 0 (see verbatim summary below); Rhino 8 SDK was present, so DG.Grasshopper actually compiled under the guard, not skipped"
        status: pass
    human_judgment: false
  - id: T3
    description: "The identity behavior change (renaming no longer changes ObjState id) is confirmed on a live Rhino/Grasshopper canvas by the user, not shipped silently"
    requirement: "ALGN12-08"
    verification:
      - kind: human
        ref: "checkpoint:human-verify, gate=blocking -- awaiting user response"
        status: pending
    human_judgment: true

duration: ~25min (Tasks 1-2 only; Task 3 pending)
completed: 2026-09-22
status: in_progress
---

# Phase 1202 Plan 06: Converge ObjState ID Minting on DesignStateIdGenerator (D-04) Summary

**Added an additive `DesignStateIdGenerator.ComputeObjectStateIdFromRef(objectRef, classIri?)` overload, deleted the private label-folding duplicate `ObjectStateComponent.ComputeObjStateId` it replaces, rebuilt the Grasshopper plugin clean in Release, and paused at a blocking human checkpoint for live-canvas confirmation that Label no longer affects ObjState identity.**

**This plan is NOT complete.** Tasks 1 and 2 are done and committed. Task 3 is a `checkpoint:human-verify` with `gate="blocking"` and is pending human response — it has not been self-approved or skipped.

## Performance

- **Duration:** ~25 min (Tasks 1-2)
- **Started:** 2026-09-22
- **Tasks:** 2/3 completed; Task 3 pending human checkpoint
- **Files modified:** 3 (DesignStateIdGenerator.cs, ObjectStateComponent.cs, DesignStateIdGeneratorTests.cs)

## Accomplishments

- **Task 1 — Additive minting overload + duplicate deletion (D-04):**
  - Added `DesignStateIdGenerator.ComputeObjectStateIdFromRef(string objectRef, string? classIri)` — hashes `objectRef|classIri` (pipe-joined, with a stable `\u0000no-class-iri\u0000` sentinel for null `classIri`) via the existing private `HashToHex16`, prefixed with the existing `ObjectStatePrefix`. No new hasher added; `HashToHex16` untouched.
  - XML doc-comment states both required facts: why it exists alongside the 3-arg `ComputeObjectStateId` (different semantics — per-rule-variable CMPST-07 form vs. per-geometry-instance form the component actually has), and that Label is deliberately NOT folded in.
  - `ObjectStateComponent.cs`: replaced the `ComputeObjStateId(objectRef, label)` call with `DesignStateIdGenerator.ComputeObjectStateIdFromRef(objectRef, classIri)` (reusing the already-resolved `classIri` from line 112). Deleted the private `ComputeObjStateId` method entirely. Removed the now-unused `System.Security.Cryptography`/`System.Text` using directives (confirmed via grep that no other code in the file referenced `SHA256`/`Encoding`/`Convert.ToHexString`). All edits stayed inside the `#if GRASSHOPPER_SDK` guard; the `#else` empty-class fallback was not touched.
  - `DesignStateIdGeneratorTests.cs`: 7 new Facts — `OS_`-prefix/16-hex-length shape, label-insensitivity (`ComputeObjectStateIdFromRef_ShouldBeSame_WhenOnlyLabelDiffers`), objectRef-sensitivity, classIri-sensitivity (same objectRef, different classIri → different id), null-classIri determinism (no crash), null-classIri non-collision with a real classIri string, and a byte-identical regression pin for the untouched 3-arg `ComputeObjectStateId` (`OS_493B9A7153D92072` for `("proj-1", "OS_abc123", "?b")`, computed via an independent SHA-256 script against the exact pre-existing hash formula, not guessed).
  - No existing test pinned the old label-inclusive `OS_` value (the deleted method was private, uncallable from tests directly; `ObjStateModelTests.cs` uses arbitrary literal `StateId` strings like `"OS_test123"` that don't derive from the hash function), so no test literal needed updating — `ObjStateModelTests.cs` is unchanged.

- **Task 2 — Release rebuild under the GRASSHOPPER_SDK guard:**
  - Rhino 8 SDK was present on this build machine (`C:\Program Files\Rhino 8\...RhinoCommon.dll` / `Grasshopper.dll` / `GH_IO.dll` all exist), so `GRASSHOPPER_SDK` was actually defined and `DG.Grasshopper` compiled under the real guard — this was not a missing-SDK skip.
  - `dotnet build DG/DG.sln -c Release` — verbatim final summary:
    ```
    Сборка успешно завершена.
        Предупреждений: 0
        Ошибок: 0
    Прошло времени 00:00:05.53
    ```
    (Russian-locale dotnet output; translation: "Build succeeded. Warnings: 0. Errors: 0.")
  - All 4 projects built: `DG.Core` (net7.0 + net9.0), `DG.De01Harness`, `DG.Tests`, `DG.Grasshopper` (net7.0-windows). No net8+-only API entered either multi-targeted project — the net7.0 `DG.Core` leg built without error.
  - `DG.gha` artifact regenerated at `DG/src/DG.Grasshopper/bin/Release/net7.0-windows/DG.gha` via the project's `CreateGrasshopperAssembly` post-build target — this is the rebuilt binary Task 3 asks the user to copy into their Rhino/Grasshopper components folder.
  - Full suite re-run for confidence: `dotnet test DG/tests/DG.Tests/ -v minimal` → 539 passed, 4 failed, 543 total. The 4 failures are the pre-existing, documented Neo4j-down `DesignStateValidationFlowTests` (env-dependent socket-connection failures to a Neo4j instance not running on this host) — matches this plan's own `<verification>` baseline ("excluding the 4 known Neo4j-down DesignStateValidationFlowTests") and prior phase memory (`DG.Tests Neo4j E2E baseline`). Not a regression.
  - No repo-tracked build artifacts (bin/obj) were committed for this task — they are out of this plan's `files_modified` scope, and the plan's own frontmatter lists only source/test files. The rebuilt `.gha`/`.dll` exist on disk at the paths above for the Task 3 checkpoint; if the user needs the binaries staged/copied into a live Rhino install, that is a manual step outside this repo's git history (per the `<how-to-verify>` instructions in Task 3, which already ask the user to "copy the rebuilt plugin into the Rhino/Grasshopper components folder").

## Task Commits

1. **Task 1: Add the additive ObjState minting overload and delete the private duplicate (D-04)** - `48c90fb` (feat)
2. **Task 2: Rebuild the Grasshopper plugin under the GRASSHOPPER_SDK guard** - no commit (verification-only task; no source files changed; build artifacts intentionally left out of scope per plan's `files_modified` list)

_No plan-metadata commit created by this executor for STATE.md/ROADMAP.md — the orchestrator owns those writes centrally for this wave. This plan additionally cannot receive its own completion metadata yet because Task 3 (blocking human checkpoint) has not resolved._

## Files Created/Modified

- `DG/src/DG.Core/Services/DesignStateIdGenerator.cs` — Added `ComputeObjectStateIdFromRef(string objectRef, string? classIri)`; extended the class-level cross-reference doc-comment list to include it.
- `DG/src/DG.Grasshopper/Components/ObjectStateComponent.cs` — Replaced the `ComputeObjStateId` call site with `DesignStateIdGenerator.ComputeObjectStateIdFromRef`; deleted the private duplicate method; removed unused `System.Security.Cryptography`/`System.Text` usings.
- `DG/tests/DG.Tests/DesignStateIdGeneratorTests.cs` — 7 new Facts for `ComputeObjectStateIdFromRef` plus a regression pin for the untouched 3-arg `ComputeObjectStateId`.

## Decisions Made

- **Pitfall 1 resolution locked as option (b)** (additive overload), per the plan's own pre-decided direction: `ObjectStateComponent` genuinely has no `Project` input port and no per-geometry-instance `variableName` concept (verified by re-reading `RegisterInputParams` — only Object/Geometry/Label ports exist), so force-fitting the 3-arg `ComputeObjectStateId` would have required synthesizing fake values, corrupting its documented CMPST-07 per-rule-variable contract. The new overload takes exactly what the component has: `objectRef` (already resolved via explicit-ref → geometry-GUID → index priority) and `classIri` (already resolved one line above the call site).
- **Label excluded from the new hash input** — this is the D-04 behavior change itself, not incidental. The old private duplicate hashed `objectRef|label`; the new function hashes `objectRef|classIri`. This is surfaced verbatim to the user at Task 3's checkpoint rather than shipped silently.
- **Null-classIri sentinel chosen as a non-printable string (`\u0000no-class-iri\u0000`)** rather than an empty string, specifically so that a real (if unlikely) empty-string `classIri` could never collide with the "no class wired yet" case. A dedicated Fact (`ComputeObjectStateIdFromRef_NullClassIri_DiffersFrom_NonNullClassIri`) proves non-collision against a real classIri, though it does not test collision against literal empty string specifically (not required by the plan's behavior bullets).

## Deviations from Plan

None — plan executed exactly as written for Tasks 1 and 2. The Task 1 acceptance-criteria greps all pass as specified in the plan (verified below); the 3-arg method's regression-pin literal was computed via an independent SHA-256 script rather than guessed, consistent with plan 02's own precedent for cross-checked hash literals.

### Acceptance criteria verification (Task 1, verbatim grep results)

```
grep -c 'private static string ComputeObjStateId' ObjectStateComponent.cs          -> 0
grep -v '^\s*//' ObjectStateComponent.cs | grep -cE 'SHA256\.HashData'             -> 0
grep -c 'DesignStateIdGenerator.ComputeObjectStateIdFromRef' ObjectStateComponent.cs -> 1
grep -c 'ComputeObjectStateId(string projectId' DesignStateIdGenerator.cs         -> 1
dotnet test DG/tests/DG.Tests/ -v minimal --filter DesignStateIdGeneratorTests    -> 27 passed, 0 failed
```

## Threat Flags

None — this plan's edits are entirely internal to the identity-hashing function used by an existing, already-in-scope input surface (Grasshopper canvas → ObjState identity), matching the plan's own `<threat_model>` (T-1202-21/22/23), and introduce no new network endpoint, auth path, file access pattern, or schema change.

## Known Stubs

None.

## Issues Encountered

None beyond the expected pre-existing 4 Neo4j-down test failures (environment fact, not a regression — documented above and in prior phase memory).

## User Setup Required — BLOCKING CHECKPOINT PENDING

**Task 3 is a blocking human checkpoint. This plan cannot be marked complete, and the orchestrator must not advance past it, until the user responds.**

See the CHECKPOINT REACHED section of this executor's return message for the full structured handoff (what-built text, how-to-verify steps, resume signal). In short: the user needs to copy the rebuilt `DG.gha` into their Rhino/Grasshopper components folder, restart Rhino, and confirm on a live canvas that changing an OBJECT STATE component's Label input does NOT change the resulting ObjState id, with no runtime error — and state whether any relabel-to-reset workflow they rely on is broken by this change.

## Next Phase Readiness

- Once Task 3 resolves (user responds "approved" or reports an issue), a continuation agent should: (a) if approved, finalize this plan (no further code changes expected — Task 3's `<done>` only requires recording the response in this SUMMARY) and hand back to the orchestrator for STATE.md/ROADMAP.md updates; (b) if the user reports a broken relabel-to-reset workflow or any other issue, treat it as a new finding requiring Rule 4 (architectural) triage before this plan can close, since it was explicitly named as an "awaiting" item in the plan's own `<what-built>` text.
- Plan 07 (per `affects`) should be able to proceed once this plan's checkpoint clears — no code in this plan blocks 07 from starting in parallel if the wave DAG allows it, but the *behavior change* (Label no longer identity-bearing) is only trustworthy for downstream planning once a human has actually verified it live, per the plan's own threat register (T-1202-23).

---
*Phase: 1202-design-state-replay-and-per-object-verdict-closure*
*Status: IN PROGRESS — Task 3 blocking checkpoint pending*

## Self-Check: PASSED

All created/modified files verified present on disk:
- FOUND: DG/src/DG.Core/Services/DesignStateIdGenerator.cs (modified, contains ComputeObjectStateIdFromRef)
- FOUND: DG/src/DG.Grasshopper/Components/ObjectStateComponent.cs (modified, private duplicate removed)
- FOUND: DG/tests/DG.Tests/DesignStateIdGeneratorTests.cs (modified, 7 new Facts)
- FOUND: DG/tests/DG.Tests/ObjStateModelTests.cs (unmodified — no pinned literal required an update)

Commit hash verified in git log: 48c90fb.

dotnet test DG/tests/DG.Tests/ -v minimal --filter DesignStateIdGeneratorTests: 27 passed, 0 failed.
dotnet build DG/DG.sln -c Release: Warnings 0, Errors 0.
