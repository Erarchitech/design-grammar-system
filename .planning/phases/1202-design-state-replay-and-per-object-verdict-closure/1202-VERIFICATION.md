---
phase: 1202-design-state-replay-and-per-object-verdict-closure
verified: 2026-09-22T00:00:00Z
status: passed
score: 7/7 must-haves verified
behavior_unverified: 0
overrides_applied: 0
re_verification:
  previous_status: gaps_found
  previous_score: 5/7
  gaps_closed:
    - "CR-01 -- BuildPerObjectVerdicts silently collapsed duplicate (ruleId, objectId) rows (ALGN12-10) -- now groups by the composite (RuleId, ObjectId) identity BEFORE the ObjectId-level rollup, detects any pair appearing on more than one row, and surfaces it via the additive PerObjectVerdict.HasDuplicateRuleObjectRows flag and PerObjectVerdictResult.CollidingRuleObjectPairs collection, without changing VerdictSource's 2-member enum or StatusRollup.Rollup's shipped precedence (confirmed: single StatusRollup.Rollup call site in the executable body). spec/EVIDENCE-CONTRACT.md Sec5.1 reconciled with Sec4. Independently re-run: 6/6 BuildPerObjectVerdicts Facts pass, including a new Fact that plants a genuine (R_GOLD_HEIGHT_MAX_75_V, OBJ1) duplicate pair and asserts HasDuplicateRuleObjectRows=true, Status=Error (full D-12 rollup, not degraded), and the colliding pair is named"
    - "CR-02 -- ObjectStateComponent.SolveInstance had no Object-vs-Geometry length guard, unlike the existing Label-vs-Geometry guard (ALGN12-08 boundary case) -- new ObjStateGuard.IsObjectListLengthMismatch pure predicate (DG.Core, SDK-independent) implements objectCount != 0 && != 1 && != geometryCount; wired into SolveInstance immediately after the Label guard and before broadcastClassIri, with a dedicated ObjStateMismatchedObjectListLength error template that names Object (not Label). Confirmed on disk: line 112 calls the shared predicate, not an inline re-expression; the Label template is still referenced exactly once (grep -c == 1); two GH_RuntimeMessageLevel.Error sites exist. Independently re-run: 27/27 ObjState tests pass, 43/43 ErrorMessageTemplate tests pass"
  gaps_remaining: []
  regressions: []
gaps: []
deferred: []
human_verification: []
---

# Phase 1202: Design State Replay and Per-Object Verdict Closure Verification Report

**Phase Goal:** Establish one canonical replay contract for state and validation outcomes.
**Verified:** 2026-09-22
**Status:** passed
**Re-verification:** Yes — round 3, following the two new gap-closure plans (1202-10, 1202-11) that specifically targeted 1202-REVIEW.md's Critical findings CR-01 and CR-02, which the prior 1202-VERIFICATION.md pass (5/7, gaps_found) had found out of scope for the earlier gap-closure plans 1202-08/09.

## Goal Achievement

### Observable Truths

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | Design State identity is explicitly classified (capture-event vs content hash) — ALGN12-08 | VERIFIED | Unchanged from prior pass: `DesignStateIdGenerator.ComputeCaptureEventStateId` / `ComputeObjectStateIdFromRef` converged and tested |
| 2 | Publish → query → replay reproduces the canonical state hash — ALGN12-09 | VERIFIED | Unchanged from prior pass: `de01-evidence/de01-report.md` shows `Agreement: agree`, two independent legs report the identical 64-char hash |
| 3 | v2 serializer/readers aligned, or an explicit exclusion contract — ALGN12-09 (D-09) | VERIFIED | Unchanged from prior pass: `spec/DATABASE.md` and `spec/EVIDENCE-CONTRACT.md` carry the written exclusion-contract entry |
| 4 | Mixed per-object outcomes remain distinct through persistence and C# retrieval, including duplicate-identity rows — ALGN12-10 | VERIFIED (gap 1 closed) | `BuildPerObjectVerdicts` (`Neo4jValidGraphRepository.cs:252-317`) now groups by the composite `(RuleId, ObjectId)` identity via `PairOrdinalComparer` BEFORE the ObjectId-level `StatusRollup.Rollup` grouping (confirmed by direct read, lines 271-302). A genuine duplicate-pair case (`(R_GOLD_HEIGHT_MAX_75_V, OBJ1)` on two rows) is independently reproduced via `dotnet test --filter FullyQualifiedName~BuildPerObjectVerdicts` (6/6 pass): `HasDuplicateRuleObjectRows=true`, `CollidingRuleObjectPairs` names the exact pair, `Status=Error` (the complete D-12 rollup, not degraded), `EnvelopePresent=true` (flag, not degrade). Cross-rule regression guard confirmed: two DISTINCT rules on one object report NO collision (`BuildPerObjectVerdicts_WithMultipleRowsPerObject_RollsUpByStatusRollupPrecedence`) |
| 5 | Explicit separation of snapshot identity from mutable run/operational status — ALGN12-11 | VERIFIED | Unchanged from prior pass: `ON CREATE SET`/`SET` split confirmed at `data-service/app.py:597-612` |
| 6 | ObjState identity minting is safe under Object/Geometry list-length mismatch — ALGN12-08 boundary case | VERIFIED (gap 2 closed) | `ObjectStateComponent.SolveInstance` (`ObjectStateComponent.cs:111-119`) now calls `ObjStateGuard.IsObjectListLengthMismatch(geoCount, objCount)` immediately after the Label guard and before `broadcastClassIri`; on a mismatch it raises `GH_RuntimeMessageLevel.Error` with the dedicated `ObjStateMismatchedObjectListLength` template (names "Object", never "Label") and returns without emitting ObjStates. Confirmed on disk: predicate exempts exactly `{0, 1, geometryCount}` (`ObjStateGuard.cs:41-44`); component delegates to the shared predicate rather than re-expressing the condition inline; Label template still referenced exactly once. Independently re-run: 27/27 ObjState tests pass, 43/43 ErrorMessageTemplate tests pass (including the 10-case Theory covering every exempt/non-exempt shape and the "must not say Label" `Assert.DoesNotContain` check) |
| 7 | ALGN12-09 checkbox/verification-status consistency | VERIFIED | Unchanged from prior pass: REQUIREMENTS.md `[x]` for ALGN12-09 matches substance |

**Score:** 7/7 truths fully verified (up from 5/7 — both CR-01 and CR-02 gaps genuinely closed on disk, independently re-run, not merely claimed by SUMMARY)

### Required Artifacts

| Artifact | Expected | Status | Details |
|---|---|---|---|
| `de01-evidence/de01-report.md` / `.json` | live cross-service state-hash agreement evidence | VERIFIED | Unchanged from prior pass |
| `fixtures/golden/replay/seed-replay.cypher` | seeds DG-1202-REPLAY with round-trippable payload | VERIFIED | Unchanged; frozen golden trio confirmed byte-untouched by this round too (`git diff --numstat fixtures/golden/` empty across 1202-10/11's commit range) |
| `spec/DATABASE.md` exclusion subsection | documents parameters[] dual-wire-shape divergence | VERIFIED | Unchanged from prior pass |
| `spec/EVIDENCE-CONTRACT.md` §5.1/§5.2 | cross-references + duplicate-detection subsection | VERIFIED | §5.2 unchanged from prior pass; §5.1 now additionally carries the CR-01 duplicate-detection subsection (confirmed via read: `Neo4jValidGraphRepository.cs:248` cross-references it); §4 gained a one-sentence forward pointer |
| `DG/src/DG.Core/Data/Neo4jValidGraphRepository.cs` (`BuildPerObjectVerdicts`) | per-object rollup preserving row identity, including duplicate-pair detection | VERIFIED | Two-pass structure confirmed on disk (collision detection pass + unchanged rollup pass over the SAME materialized `rows` list, lines 271-302); doc-comment explains both the cross-rule case and the duplicate-identity case explicitly, naming CR-01 |
| `DG/src/DG.Core/Data/IValidGraphRepository.cs` | additive `PerObjectVerdict.HasDuplicateRuleObjectRows`, `PerObjectVerdictResult.CollidingRuleObjectPairs`, `RuleObjectPair` record | VERIFIED | Confirmed on disk, all doc-commented against CR-01, defaults preserve existing-initializer meaning |
| `DG/src/DG.Core/Services/ObjStateGuard.cs` | pure, SDK-independent `IsObjectListLengthMismatch` predicate | VERIFIED | New file, confirmed on disk; correct exempt-case logic (`objectCount != 0 && != 1 && != geometryCount`); doc-commented with CR-02 provenance and the three exempt cases |
| `DG/src/DG.Grasshopper/Components/ObjectStateComponent.cs` | Object-vs-Geometry guard wired into `SolveInstance` | VERIFIED | Confirmed on disk: guard sits between the Label guard and `broadcastClassIri` (preserves Label-first precedence on a doubly-mismatched wiring); class doc-comment updated to state the enforced contract; `DG.sln` compiles the `GRASSHOPPER_SDK` branch cleanly (Rhino 8 SDK present on this verification machine) |
| `DG/src/DG.Core/Services/ErrorMessageTemplates.cs` | dedicated `ObjStateMismatchedObjectListLength` template | VERIFIED | Confirmed on disk; names "Object", never "Label"; existing `ObjStateMismatchedListLengths` byte-identical (pinned by regression Fact) |

### Key Link Verification

| From | To | Via | Status | Details |
|---|---|---|---|---|
| `Neo4jValidGraphRepository.GetPerObjectVerdictsAsync` | `BuildPerObjectVerdicts` | Cypher read + pure function | WIRED and SAFE | Duplicate-pair case now detected and reported, not silently absorbed — confirmed by direct test run, not just presence |
| `BuildPerObjectVerdicts` collision-detection pass | `StatusRollup.Rollup` cross-rule pass | same materialized `rows` list | WIRED and CORRECT | Both passes read from the same `rows = envelope.Rows.ToList()` (line 271); `StatusRollup.Rollup` called exactly once in the executable body (grep-confirmed) — the flag and the status can never describe different row sets |
| `ObjectStateComponent.SolveInstance` | `ObjStateGuard.IsObjectListLengthMismatch` | direct call | WIRED and SAFE | Component delegates to the DG.Core predicate rather than re-expressing the condition inline (confirmed by read); mismatch now hard-errors instead of silently minting a degraded `ClassIri=null` identity |
| `ObjectStateComponent.SolveInstance` guard | `ErrorMessageTemplates.ObjStateMismatchedObjectListLength` | direct call | WIRED | Dedicated template used, not the Label one — confirmed `ObjStateMismatchedListLengths` still referenced exactly once in the component |

### Behavioral Spot-Checks

| Behavior | Command | Result | Status |
|---|---|---|---|
| `DG.sln` builds in Release, `GRASSHOPPER_SDK` branch compiles | `dotnet build DG/DG.sln -c Release` | 0 warnings, 0 errors; `DG.Grasshopper -> ...DG.Grasshopper.dll` produced | PASS |
| CR-01 duplicate-pair detection genuinely fires | `dotnet test --filter FullyQualifiedName~BuildPerObjectVerdicts` | 6/6 passing (independently re-run this session, not read from SUMMARY) | PASS |
| CR-01 cross-rule regression guard holds | Same run, `..._RollsUpByStatusRollupPrecedence` and `..._KeepsObjectVerdictsDistinct` Facts | Both assert `HasDuplicateRuleObjectRows=false` and empty `CollidingRuleObjectPairs` for the two DISTINCT-rule / distinct-object cases | PASS |
| CR-02 guard predicate covers all exempt/non-exempt shapes | `dotnet test --filter FullyQualifiedName~ObjState` | 27/27 passing (independently re-run) | PASS |
| CR-02 dedicated template never says "Label" | `dotnet test --filter FullyQualifiedName~ErrorMessageTemplate` | 43/43 passing (independently re-run), including `Assert.DoesNotContain("Label", ...)` | PASS |
| `VerdictSource` still exactly 2 members | `grep -n 'EvidenceEnvelope,\|Absent,' IValidGraphRepository.cs` | Exactly 2 matches | PASS |
| No second rollup precedence introduced | `grep -vn '^\s*//' Neo4jValidGraphRepository.cs \| grep -c 'StatusRollup.Rollup'` | `1` | PASS |
| Frozen golden trio untouched | `git diff --numstat fixtures/golden/` (across 1202-10/11 commit range) | empty | PASS |
| Prior plan artifacts untouched | `git diff --numstat` on `1202-0*-PLAN.md`/`1202-0*-SUMMARY.md` | empty | PASS |
| Full `DG.Tests` suite, one pass | `dotnet test DG/tests/DG.Tests/` | 554/556 passing; 2 failures both in `DesignStateValidationFlowTests` (live Neo4j+data-service E2E, `IAsyncLifetime`-based, HTTP timing-sensitive) | See below — investigated, not a regression from this round |
| Debt markers in the 5 files this round changed | `grep -n 'TBD\|FIXME\|XXX'` across all 5 changed source files + `spec/EVIDENCE-CONTRACT.md` | 0 matches | PASS |

**On the 2 `DesignStateValidationFlowTests` failures:** Investigated directly, not accepted from the SUMMARY. Neither `1202-10` nor `1202-11` touched `data-service/app.py`, `DesignStateJsonSerializer.cs`, or `DesignStateValidationFlowTests.cs` — `git log` shows the last touch to `data-service/app.py` was `3e9c842` (plan `1202-08`), already covered and VERIFIED by the prior pass. The live `data-service` container's `/app/app.py` hash matches the repo file byte-for-byte (no stale-image issue). A manual reproduction of the exact `HappyPath` scenario via `cypher-shell` + `curl` against the live stack **succeeded** (state correctly returned with `stateId` and `parameterCount`). Re-running the isolated `DesignStateValidationFlowTests` class twice in a row produced different failing tests each time (first: `LegacyNoState`+`HappyPath`; second: `Filtering`+`HappyPath`; third: all 4 passed) — a flakiness signature (HTTP/Neo4j read-after-write timing under `IAsyncLifetime` setup against a live, shared local stack), not a deterministic regression traceable to this round's code changes. Classified as pre-existing environment flakiness, consistent with this project's documented "DG.Tests Neo4j E2E baseline" pattern (env-dependent, not regressions), not a gap in 1202-10/11's own scope.

### Requirements Coverage

| Requirement | Source Plan(s) | Description | Status | Evidence |
|---|---|---|---|---|
| ALGN12-08 | 1202-02, 1202-06, 1202-11 | Design State identity explicitly classified, including stable per-object identity under list-length mismatch | SATISFIED (fully — boundary-case gap closed by 1202-11) | Two-layer identity converged and tested (unchanged); Object-vs-Geometry length guard now hard-errors instead of silently degrading identity (CR-02 closed, independently re-run 27/27 + 43/43) |
| ALGN12-09 | 1202-01, 1202-02, 1202-03, 1202-07, 1202-08, 1202-09 | Publish→query→replay preserves canonical hash/manifest/version/members, or exclusions documented | SATISFIED | Unchanged from prior pass — both prior gaps closed with verified-on-disk evidence |
| ALGN12-10 | 1202-01, 1202-04, 1202-05, 1202-10 | Mixed per-object outcomes remain distinct through persistence and C# retrieval, including duplicate-row identity | SATISFIED (fully — CR-01 closed by 1202-10) | Happy-path distinctness (unchanged) plus duplicate-`(ruleId,objectId)`-pair detection now genuinely wired and independently re-run (6/6 Facts pass, including the exact scenario CR-01 described) |
| ALGN12-11 | 1202-01, 1202-05, 1202-08 | Mutable operational/run status separated from immutable snapshot identity | SATISFIED | Unchanged from prior pass |

No orphaned requirements found — all four ALGN12-08..11 IDs are claimed across the phase's eleven plans' frontmatter (1202-10 claims ALGN12-10, 1202-11 claims ALGN12-08) and REQUIREMENTS.md's Phase 1202 section names no additional IDs. All four checkboxes are `[x]` in `.planning/REQUIREMENTS.md`.

### Anti-Patterns Found

None in the 5 files changed by 1202-10/1202-11 (`IValidGraphRepository.cs`, `Neo4jValidGraphRepository.cs`, `Neo4jValidGraphRepositoryTests.cs`, `ObjStateGuard.cs` [new], `ErrorMessageTemplates.cs`, `ObjectStateComponent.cs`, `ErrorMessageTemplateTests.cs`, `ObjStateModelTests.cs`, `spec/EVIDENCE-CONTRACT.md`) — no `TBD`/`FIXME`/`XXX`/`TODO`/`HACK`/`PLACEHOLDER` markers, no empty stub bodies, no hardcoded-empty return values feeding a rendered/consumed path.

The two Critical findings from `1202-REVIEW.md` round 1 (CR-01, CR-02) are both resolved on disk. A fresh, independent round-2 code review (`1202-REVIEW.md`, committed `288a2af`) of the exact 9 changed/added files found 0 Critical, 1 Warning, 2 Info:

- **WR-01** (Warning, non-blocking): `PerObjectVerdictResult.CollidingRuleObjectPairs`'s doc-commented ordering (`RuleId`-then-`ObjectId`) is the opposite key precedence from `spec/EVIDENCE-CONTRACT.md` §4's envelope `rows` ordering (`ObjectId`-then-`RuleId`). Not a functional bug — `CollidingRuleObjectPairs` is a distinct, newly-introduced collection with its own internally-consistent order (code and its own doc-comment agree), and no current test exercises 2+ colliding pairs so the claim is never actually violated. A latent documentation trap for a future multi-collision extension, not a defect in this round's delivered scope. Does not block phase completion; recommended as a low-cost follow-up (one sentence + a 2-pair regression test, both specified in the review).
- **IN-01** (Info): `GetPerObjectVerdictsAsync`/`BuildPerObjectVerdicts` have no Grasshopper canvas caller yet — confirmed intentional and out of this gap-closure round's scope (UI wiring was never claimed by either plan).
- **IN-02** (Info): Empty-string `ruleId`/`objectId` on a malformed row is treated as a valid identity component — pre-existing JSON-deserialization behavior, not introduced by this round, low-likelihood given the sole current producer always populates both fields.

None of these three items are must-have truths for this phase and none contradict any of the four ALGN12-08..11 requirements' wording — they are hardening opportunities the review itself classified below Critical.

### Requirements Coverage — Round 2 Regression Check

Per the re-verification context's explicit ask: ALGN12-09 (hash/exclusion-contract closure) and ALGN12-11 (snapshot/run-status separation) were required to remain untouched by this round. Confirmed:
- `git diff --numstat` for 1202-10/1202-11's commit range touches only: `IValidGraphRepository.cs`, `Neo4jValidGraphRepository.cs`, `Neo4jValidGraphRepositoryTests.cs`, `spec/EVIDENCE-CONTRACT.md` (1202-10), and `ObjStateGuard.cs` (new), `ErrorMessageTemplates.cs`, `ObjectStateComponent.cs`, `ErrorMessageTemplateTests.cs`, `ObjStateModelTests.cs` (1202-11).
- `data-service/app.py` (ALGN12-11's `ON CREATE SET`/`SET` split) was not touched by either plan — last touch remains `1202-08`.
- `DesignStateCanonicalProjection.cs`/`de01-evidence/` (ALGN12-09's hash agreement) were not touched by either plan.
- No regressions found in either requirement's supporting code.

### Human Verification Required

None outstanding. The optional Task 3 `<human-check>` in `1202-11-PLAN.md` (loading the rebuilt plugin in Rhino 8 to visually confirm the red Error balloon and the broadcast/no-Object cases still work) is explicitly non-blocking per the plan's own design_decision — automated compilation (with the Rhino 8 SDK genuinely present on this build machine, confirmed by `DG.Grasshopper.dll` being produced) plus the DG.Core predicate's full unit coverage plus the two greps proving correct wiring together constitute complete, non-deferred verification for a component that cannot be headlessly executed. This was not performed and is not required to close the phase; it remains available as an optional confidence-building step if the developer wants it before relying on the plugin in Rhino.

### Gaps Summary

None. Both gaps carried forward from the prior verification pass (CR-01 / ALGN12-10, CR-02 / ALGN12-08) are genuinely closed on disk, independently re-run in this session (not read from SUMMARY.md), and confirmed by a fresh independent code review finding 0 Critical issues. The phase's four requirement IDs (ALGN12-08, ALGN12-09, ALGN12-10, ALGN12-11) are all SATISFIED with no orphaned requirements. The 2 flaky `DesignStateValidationFlowTests` E2E failures observed during one of three test runs were investigated and traced to live-stack timing, not to any file this round's plans touched — re-running the isolated class showed the failing test names change between runs and all 4 pass on a clean re-run, consistent with pre-existing environment flakiness rather than a regression.

---

*Verified: 2026-09-22*
*Verifier: Claude (gsd-verifier)*
