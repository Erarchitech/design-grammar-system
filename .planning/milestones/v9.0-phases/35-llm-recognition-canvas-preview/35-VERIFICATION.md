---
phase: 35-llm-recognition-canvas-preview
verified: 2026-07-27T00:00:00Z
status: gaps_found
score: 7/12 must-haves verified
behavior_unverified: 0
overrides_applied: 0
re_verification:
  previous_status: human_needed
  previous_score: 6/9
  previous_verified: 2026-07-19T16:30:00Z
  gaps_closed:
    - "SC2 live behavior (preview render, single Ctrl+Z, clear_preview no-residue) — UAT tests 2/3/6 now PASS live on UrbanBlock_V7 (2026-07-25/26), including the F4 re-preview crash that was found and fixed by 35-09"
    - "SC3 live behavior (accept -> permanent group, source: recognized, save/reopen persistence, reject, partial accept, mixed accept/reject undo) — UAT tests 4/5 now PASS live (2026-07-25 session 2)"
    - "IN-12 stale-undo-record-after-auto-clear — closed by 35-09 and live-verified"
    - "F5 dataType inference gap — closed (parser primitive tier + accept-time G12 gate), live-retested, Neo4j node confirmed"
  gaps_remaining:
    - "SC1 quality — now MEASURED rather than unmeasured, and the measurement FAILS the gate by ~19x"
  regressions: []
gaps:

  - truth: "ROADMAP SC1 / RCGN-01 — recognition proposes entities whose member sets match the reference annotation for >= the majority of blocks. Gradeable form: M1 exact member-set match >= 0.60 on Corpus B (urbanblock_slice) / arm A3, conjunct with zero anchor violations, zero silent drops, grammar_citation_rate 0.00, confidence-spread passing, provenance complete"
    status: failed
    reason: "Measured, on exactly the corpus and arm SC1 names, at M1 = 0.03125 against a required 0.60 — 1 of 32 reference blocks matched. Independently reproduced this session from the committed cassettes. Every other conjunct passes; M1 alone fails, by roughly 19x. This is a measured failure, not an absent measurement. The A0f/A5 (claude-sonnet-5) arms that did not run are NOT part of SC1's stated gradeable form — they answer the separate diagnostic question of WHY, not WHETHER."
    artifacts:
      - path: ".planning/milestones/v9.0-phases/35-llm-recognition-canvas-preview/35-EVAL-REPORT.md"
        issue: "Reports the verdict as 'SC1 still blocked on provider availability' when the arm SC1 actually names (A3) was measured on the corpus SC1 actually names (Corpus B) and failed the gate. 'Blocked' conflates the unanswered diagnostic question (prompt defect vs. DeepSeek capability ceiling — genuinely undecidable without A0f/A5) with the answered contract question (did A3 on Corpus B clear 0.60 — no)."
      - path: ".planning/milestones/v9.0-phases/35-llm-recognition-canvas-preview/35-UAT.md"
        issue: "Test 1 still reads `result: blocked (provider availability)`. Plan 35-15's own must_have required it to move off `blocked` to either a measured result or 'a recorded FAIL with the failing conjunct named'. The failing conjunct IS named (M1); the status is not."
    missing:
      - "Record SC1 as NOT MET with the measured number, separately from the unresolved A0f/A5 diagnostic — the ROADMAP SC1 line, 35-EVAL-REPORT.md's verdict section, and 35-UAT.md test 1 should all read FAIL (M1 = 0.031 < 0.60 on Corpus B / A3), with 'which of the three F3 branches applies' carried as the open follow-up"
      - "Either raise a frontier-provider run of A0f/A5 as an explicit follow-up phase/plan with the recognition-quality gap as its goal, or accept SC1 as failed for this milestone via an override"

  - truth: "35-15 must_have #1 — A0 runs FIRST and must reproduce UAT F3 (near-zero M1 WITH a non-zero grammar_citation_rate). If A0 does not fail that way the HARNESS is wrong, not the model, and no other arm's number may be reported"
    status: failed
    reason: "The pre-registered mechanical gate `assert_a0_validity()` never passed on either corpus. On Corpus A (frame_ablated) it RAISES when replayed from the committed cassette — reproduced this session: 'A0 validity check FAILED ... near-zero M1 (got 0.000, expected <= 0.1) with a non-zero grammar_citation_rate (got 0.000)'. On Corpus B it is never reached at all: A0 returns valid:false (G7 block), so the driver's `assert result[\"valid\"] is True` fires first. 35-EVAL-REPORT.md is honest that the literal shape did not occur, but then substitutes a narrative argument ('read as harness validated, not harness broken') for the pre-registered check and reports A1-A4 anyway — which the plan's own rule forbids. Post-hoc reinterpretation of a pre-registered gate is the specific failure mode pre-registration exists to prevent."
    artifacts:
      - path: "data-service/tests/test_recognition_eval.py"
        issue: "assert_a0_validity (L441-455) requires grammar_citation_rate > 0.0; the recorded A0 run yields 0.000 on Corpus A and is unscoreable on Corpus B"
    missing:
      - "Either amend the pre-registered A0 validity condition in 35-AI-SPEC.md to accept the G7-interception outcome as a valid control result (with the amendment dated and justified), or re-record A0 under a configuration where the literal F3 signature can still surface — but do not leave a raising gate described in prose as passing"

  - truth: "The eval harness is a trustworthy instrument — no open Critical findings against the code that produced the SC1 number"
    status: failed
    reason: "All three Critical findings from 35-REVIEW.iter3.md are confirmed present in the current working tree and were reproduced independently this session. None was fixed; no SUMMARY claims they were. An instrument with three open Criticals is not yet a citable measurement apparatus, even when — as here — the specific numbers it produced this run happen to check out."
    artifacts:
      - path: "data-service/tests/recognition_eval/live_sweep.py"
        issue: "CR-01 (L219-239): few_shot_permutations() has no distinctness check. Verified live: A0 has 1 few-shot example -> 3 permutations, 1 distinct; A3 has 5 -> 3 distinct. Latent money/measurement hazard on the module's own documented `--arms=A0,A0f,... --permutations=3` command."
      - path: "data-service/tests/test_recognition_eval.py"
        issue: "CR-02 (L593, L599): TestEndToEndDriver still hardcodes negotiated_mode='json_schema_strict' for structured_output arms and passes no negotiated_mode_override. Verified live: resolve_real_negotiated_mode(ARMS['A4']) == 'json_object'; the documented driver command --arm=A4 dies with CassetteMissError key=abd6a4bd... A4 is the only arm this harness exists to distinguish and the only one the CI driver cannot replay."
      - path: "data-service/tests/test_recognition_eval.py"
        issue: "CR-03 (L686-693): the only paid test's assertion is a tautology. Confirmed: ArmCorpusOutcome.status is assigned at exactly 4 sites (live_sweep.py L317/327/335/400) with exactly the 4 literals in allowed_statuses. A record sweep that recorded nothing exits green."
      - path: "data-service/tests/recognition_eval/report.py"
        issue: "WR-04 confirmed: run_report_sweep(corpora, arm_ids) has no permutations parameter and zero 'permutation' references. The permutation sub-sweep table in 35-EVAL-REPORT.md is therefore NOT regenerable from committed state — it exists only as hand-copied pytest stdout, in the one artifact whose stated purpose is thesis-appendix reproducibility."
    missing:
      - "Fix CR-02 (single source of truth for negotiated mode in the driver; delete the known-wrong default in arms.run_arm)"
      - "Fix CR-03 (assert `recorded` is non-empty; refuse the literal 'test-master-secret' on the record path)"
      - "Fix CR-01 (dedupe orderings; record a named shortfall reason instead of silently billing duplicates)"
      - "Fix WR-04 or explicitly re-label the permutation table in 35-EVAL-REPORT.md as non-reproducible-from-cassettes"

human_verification:

  - test: "UAT test 7 (G12 accept-time publishability gate): with a mixed set where one Var/Const/Emg proposal holds a member the parser genuinely cannot type (a component in neither the widget nor the primitive tier), Apply an accept over several proposals"
    expected: "Only the offending proposal is blocked and stays PENDING with a Warning naming the component; every other proposal in the same Apply converts to a permanent convention group; Status reports the blocked count"
    why_human: "DG.Tests (net9.0) cannot reference the net7.0-windows Grasshopper.dll (NU1201), so the StructureConfirmComponent Apply path has no automated coverage; only a live Rhino session can observe it. Code is present and confirmed (StructureConfirmComponent.cs L190 TryInferParameterDataType, L204 blocked++, L287 blockedSegment)."
  - test: "Recognition -> preview integration on real LLM output: run /computgraph/context/pull -> /computgraph/recognize -> preview_structure end-to-end, with the LLM actually on the path"
    expected: "Proposals produced by the model (not a synthetic payload) render as preview groups and flow through DG STRUCTURE CONFIRM"
    why_human: "Every passing UAT canvas test (2/3/4/5/6) was exercised with a SYNTHETIC proposals payload posted straight to gh_preview_structure — the LLM was bypassed. The preview/accept MECHANISM is proven; the recognition->preview seam is not, on any canvas."
audit_acknowledged:
  milestone: v9.0
  at: 2026-09-19
  status: gaps_found
---

# Phase 35: LLM Recognition and On-Canvas Proposal Preview — Verification Report

**Phase Goal:** AI classifies the untagged remainder of the canvas into Computgraph entities — using the architect's tags as ground-truth anchors — and the proposal appears **on the canvas** as clearly-styled temporary groups and scribbles that the architect confirms, edits, or rejects before anything leaves Rhino.
**Verified:** 2026-07-27
**Status:** gaps_found
**Re-verification:** Yes — supersedes the 2026-07-19 report (`human_needed`, 6/9), which predated plans 35-05..16.

## Headline

The phase splits cleanly in two, and the two halves land in different places.

**The canvas half is done and proven.** Preview, undo, clear, accept, reject, partial accept, `source: recognized` persistence across save/reopen — all implemented, and all now closed by live Rhino UAT rather than deferred. The two `PRESENT_BEHAVIOR_UNVERIFIED` truths from the previous verification are both closed. SC2, SC3 and SC4 are met.

**The recognition half is measured, and the measurement fails.** This phase's entire stated purpose for plans 35-05..15 was to turn SC1 from a hand-wave into a number. It succeeded at that — and the number is **M1 = 0.031 against a required 0.60**, on exactly the corpus (Corpus B / `urbanblock_slice`) and exactly the arm (A3) that SC1's gradeable form names. One of 32 reference blocks matched.

The instrument was built well and the number is real: I reproduced every published metric independently from the committed cassettes this session. What I do not accept is the verdict framing.

## The SC1 verdict: not met, not "blocked"

`35-EVAL-REPORT.md` and `35-UAT.md` both record SC1 as **"still blocked on provider availability"** because the frontier arms A0f/A5 (`claude-sonnet-5`) could not run without an Anthropic/OpenAI key. That deferral is legitimate on its own terms — it is user-approved, it matches plan 35-15's pre-registered fallback branch, and it is disclosed prominently rather than buried. It is not a silent omission.

But it does not make SC1 undecidable, because **A0f and A5 are not part of SC1's stated gradeable form.** The ROADMAP text is specific: *"M1 exact member-set match ≥ 0.60 on Corpus B / arm A3."* Arm A3 ran. Corpus B was the corpus. The result is 0.031. The conjunctive gate failed, loudly and correctly, on M1 alone.

Two different questions are being conflated:

| Question | Answerable from this run? | Answer |
|---|---|---|
| Did A3 on Corpus B clear M1 ≥ 0.60? (**this is SC1**) | Yes | **No — 0.031, ~19x short** |
| Is the residual failure a prompt defect or a DeepSeek capability ceiling? (the AI-SPEC F3 decision rule) | No — needs A0f/A5 | Genuinely unresolved |

The second question being open does not suspend the first. A phase can honestly report "SC1 not met; here is the number; here is the specific follow-up that would tell us why" — and that is a *better* outcome than a 0.031 recorded as `blocked`. Plan 35-15's own must_have anticipated exactly this branch: *"UAT test 1 ... moves off `blocked` to a measured result ... — or, if the gate fails, to a recorded FAIL with the failing conjunct named."* The gate failed and the conjunct is named. The status was not moved.

Note also that the pre-registered fallback branch the report invokes was written on the premise (from UAT F3) that DeepSeek could not produce scoreable output at all — i.e. that a DeepSeek-only run would be *uninformative*. It was not. A1–A4 all produced schema-valid, zero-silent-drop, zero-grammar-citation, fully-provenanced proposal sets that scored cleanly. Every conjunct except M1 passed. That is an informative measured failure, not a null result.

## Goal Achievement

### Observable Truths

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | **ROADMAP SC1 / RCGN-01** — M1 ≥ 0.60 on Corpus B / arm A3, conjunct with E1=0, drops=0, `grammar_citation_rate`=0.00, spread OK, provenance complete | ✗ FAILED | Reproduced independently: `pytest --corpus=urbanblock_slice --arm=A3 --sc1-gate=0.60` → `AssertionError: SC1 gate FAILED -- conjunct(s) not satisfied: M1=0.031 < threshold 0.60`. Report sweep regenerated from cassettes: urbanblock_slice × A1/A2/A3/A4 all M1=0.03125, n=32; frame_ablated × A1–A4 all 0.000. Every other conjunct satisfied. |
| 2 | **ROADMAP SC2 / RCGN-02** — proposal visible as preview groups + legend; Ctrl+Z or `clear_preview` removes every trace; re-preview (F4) does not crash the second Ctrl+Z | ✓ VERIFIED | Code: `CanvasListenerComponent.cs` L291 creates the `GH_UndoRecord("DG structure proposal")` **before** the WR-01 auto-clear and hands it to `RemovePendingPreviewObjects(doc, record)` (L304); `RemoveTracked` (L436-439) adds a `GH_RemoveObjectAction` per object *before* `doc.RemoveObject(obj,false)`; `HandleClearPreview` pushes its own `"DG clear preview"` record (L368-369). Zero `StubResult`. Behavior: UAT tests 2, 3, 6 all **pass live** on UrbanBlock_V7 (2026-07-25/26), test 6 flipped FAIL→pass after 35-09, verified against a SHA256-checked `.gha` with `/computgraph/context/pull` before and after each step. |
| 3 | **ROADMAP SC3 / RCGN-03** — accepting yields permanent groups the Phase-32 serializer parses identically to hand-made tags, `source: recognized` recorded and durable | ✓ VERIFIED | Code: `StructureConfirmComponent.cs` L247 `ValueTable.SetValue("dg.recognized.<guid>")`, L271 `GH_RemoveObjectAction` on reject, L152 one `GH_UndoRecord("DG confirm structure")` per Apply. Behavior: UAT test 4 **pass live** — partial accept (2 accepted / 1 rejected / 2 left pending), then accept-all + save + close + reopen + fresh `/computgraph/context/pull` returned `11_Pat_2 SUBPLOT` / `TargetScr` / `Result` / `ScrRatio` all `source=recognized`, nesting detected, **0 parser warnings**. UAT test 5 (mixed accept/reject single Ctrl+Z) **pass live**. |
| 4 | **ROADMAP SC4 / RCGN-04** — nothing written to Neo4j until explicit confirmation; unrecognized blocks appear in the report | ✓ VERIFIED | `grep -vE '^\s*#' cg_recognition.py \| grep -cE 'session\.run\|driver\.session\|tx\.run\|GraphDatabase'` → **0** (re-run this session). `StructureConfirmComponent.cs` → 1 match for `HttpClient\|Neo4j\|neo4j\|data-service`, and it is the doc comment *"Never persists to Neo4j"* (L19). `unrecognized` appears 33× in `cg_recognition.py` including WR-06's validation of the unrecognized block itself. Report sweep confirms `silent_drop_count = 0` on every scored row. |
| 5 | **35-15 #1** — A0 runs first and must reproduce F3 (near-zero M1 **with** non-zero `grammar_citation_rate`); if not, no other arm's number may be reported | ✗ FAILED | Pre-registered gate never passed. Corpus A replay reproduced live: `AssertionError: A0 validity check FAILED ... near-zero M1 (got 0.000, expected <= 0.1) with a non-zero grammar_citation_rate (got 0.000)`. Corpus B never reaches the gate (`valid:false` from G7 trips the earlier `assert result["valid"] is True`). The report is candid that the literal shape did not occur, but substitutes a narrative "harness validated" for the mechanical check and reports A1–A4 regardless. |
| 6 | **35-15 #2** — every SC1 figure from Corpus B / A3 / temperature 0.0 with complete E9 provenance; Corpus A stamped `evidence:false` | ✓ VERIFIED | Regenerated report stamps `evidence: false` on all 5 `frame_ablated` sections; provenance carries `negotiatedMode`, `promptVersion` (`r35.4` for A2/A3/A4, `no-system-prompt` for A0/A1) per row. |
| 7 | **35-15 #3** — ship gate and claim threshold reported as two separate verdicts | ✓ VERIFIED | `35-EVAL-REPORT.md` Task 3 carries distinct "Ship-gate verdict" (FAIL, M1 alone) and "Claim-threshold verdict" (FAIL, Wilson lower bound 0.006 vs > 0.50) sections, and states the narrower claim the data does license. |
| 8 | **35-15 #4** — M1 reported with Wilson interval, block count n, and an explicit statement that the test-retest ceiling and peer floor are unmeasured | ✓ VERIFIED | Table carries `0.031 [0.006, 0.157]`, `n=32`. "Interpretation limits" section states both non-measurements *on the number*, not as a footnote, and repeats them in the report-wide "Not Measured" block. |
| 9 | **35-15 #5** — recorded cassettes committed, each carrying `recordedAt`, replay-reproducible | ✓ VERIFIED (with a scoped exception) | 17 cassettes tracked under `cassettes/{A0..A4}/`. `report --arms A0,A1,A2,A3,A4` → `scored 9; skipped 1`, all metrics byte-identical to the published table; the 1 skip is the A0×Corpus-B G7 block, correctly reported as unscored. **Exception:** permutation rows are not covered — see truth 12 / WR-04. |
| 10 | **35-15 #6** — UAT test 1 moves off `blocked` to a measured result, or to a recorded FAIL with the failing conjunct named | ✗ FAILED | `35-UAT.md` test 1 still reads `result: blocked (provider availability)`. The failing conjunct **is** named in the body (`ship gate FAIL (M1 < 0.60...)`), but the status was not moved to FAIL as the plan's own must_have required for exactly this branch. |
| 11 | **35-16** — `ComputeHostPatternIds` resolves a pattern's host by pattern-ness, order-independently | ✓ VERIFIED | `CanvasAnnotationParser.cs` L446-466: `ComputeHostPatternIds(allGroups, pendingPatterns)` now searches `pendingPatterns` for the innermost enclosing pattern (L455-459) with the strict-superset `MemberIds` fallback retained (L466); the old `allGroups.FirstOrDefault` is gone and the reason is documented in the L426-445 comment. Live UAT test 4 corroborates: `hostPatternId=cg:1:pat:11_1` resolved on reopen. |
| 12 | **The eval harness is a trustworthy instrument — no open Critical review findings** | ✗ FAILED | All 3 Criticals from `35-REVIEW.iter3.md` confirmed unfixed and reproduced live (see below), plus WR-04 confirmed. |

**Score:** 7/12 truths verified (0 present-but-behavior-unverified)

### Deferred Items

None. Roadmap phases 36–40 (`Computgraph Persistence`, `Script Structure Validation MVP`, `AI-Generated Script Inputs`, `DesignState Auto-Validation`, `E2E Validation and Docs`) were checked against the SC1 gap. None has a goal or success criterion covering recognition accuracy, the M1 gate, or a frontier-provider ablation run. Phase 40's "runs end-to-end under a cloud provider" is adjacent but is about provider-switching friction, not recognition quality — too tangential to defer against under Step 9b's conservative-matching rule. **The SC1 gap is real and unowned.**

### Independent Reproduction of the Eval Report

Every check below was run by this verifier this session, against the committed cassettes, with no live network call.

| Claim in 35-EVAL-REPORT.md | Verification command | Result | Verdict |
|---|---|---|---|
| Best M1 = 0.031 on Corpus B; gate fails on M1 alone | `pytest ... --corpus=urbanblock_slice --arm=A3 --sc1-gate=0.60` | `AssertionError: SC1 gate FAILED ... M1=0.031 < threshold 0.60`; `1 failed, 40 passed, 1 skipped, 1 deselected` | **Confirmed** |
| Replay reproduces all record-time metrics; 9 scored / 1 skipped; zero cassette misses | `python -m tests.recognition_eval.report --arms A0,A1,A2,A3,A4` | `scored 9 combo(s); skipped 1 combo(s)`; A1–A4 × urbanblock = 0.03125, × frame_ablated = 0.000; `cite=0.0`, `drops=0` everywhere; skip = A0 × urbanblock (`grammar_as_filter`) | **Confirmed** |
| A4 is wire-identical to A3 (`json_object`, no schema sent) | `resolve_real_negotiated_mode(ARMS['A4'])` | `json_object` (A0–A3 → `none`) | **Confirmed** |
| SC1 gate threshold constant intact, still raises | as above | raises `AssertionError`, threshold 0.60 unweakened | **Confirmed** |
| A0 reproduces UAT F3 / "harness validated" | `pytest ... --corpus=frame_ablated --arm=A0` | `AssertionError: A0 validity check FAILED ... grammar_citation_rate (got 0.000)` | **Contradicted** — see truth 5 |
| Permutation sub-sweep is a genuine 3-ordering measurement | `few_shot_permutations` on real artifacts | A3: 5 examples → **3 distinct** orderings; A0: 1 example → **1 distinct of 3** | **Confirmed for the run that was published** (A3 only) |

### Critical Review Findings — Verified Against Code, Not Trusted

`35-REVIEW.iter3.md` reported 3 Critical / 9 Warning against wave 5. **None was fixed** — no SUMMARY claims otherwise, and the fix-loop that closed iterations 1 and 2 was never run for iteration 3. I confirmed each independently.

| ID | Confirmed? | What it does and does NOT invalidate |
|---|---|---|
| **CR-02** — driver hardcodes `json_schema_strict`; A4 unreplayable | **Yes.** `test_recognition_eval.py:593` unchanged; `:599` still calls `run_arm` with no `negotiated_mode_override`. Reproduced: `--arm=A4` → `CassetteMissError key=abd6a4bd...` | **Does not invalidate any published number.** The Task 2 A4 row came from record mode and is reproducible via `report.py`, which *was* fixed. It **does** invalidate the implied completeness of Task 3's "replay reproducibility proof": the documented CI driver cannot replay A4 at all, and A4 is the only arm this harness exists to distinguish. The report does not disclose this. |
| **CR-01** — `few_shot_permutations()` emits duplicate orderings | **Yes.** `live_sweep.py:219-239` has no distinctness check. A0 → 1 distinct of 3. | **Does NOT invalidate the published permutation table.** The sub-sweep was run `--arms=A3` only, and A3 has 5 few-shot examples → 3 genuinely distinct orderings. The "spread = 0.000" claim is a real 3-point measurement, not a fabrication. CR-01 remains a live money/measurement hazard on the module's own documented `--arms=A0,A0f,...` command. |
| **CR-03** — the one paid test's assertion is a tautology | **Yes.** `status` assigned at exactly 4 sites (`live_sweep.py` L317/327/335/400) with exactly the 4 literals in `allowed_statuses`. | **Does not invalidate this run's data** — 17 cassettes exist and replay correctly, so calls demonstrably happened. It means the harness *would* report green on a zero-recording sweep, which is a trustworthiness defect in the instrument for every future run. |
| **WR-04** — permutation rows not replayable | **Yes.** `run_report_sweep(corpora, arm_ids)` has no `permutations` parameter; zero `permutation` references in `report.py`. | The permutation table in `35-EVAL-REPORT.md` is **not regenerable from committed state** — it survives only as hand-copied pytest stdout, in the artifact whose stated purpose is thesis-appendix reproducibility. |

### Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `data-service/cg_recognition.py` | Two-tier recognition backend + guardrails G6–G11 | ✓ VERIFIED | 0 Neo4j write primitives; `unrecognized` handling present; G7 `_grammar_as_filter_triggered` fires live (blocks A0 on Corpus B) |
| `data-service/tests/recognition_eval/` (cassette, arms, scoring, report, live_sweep) | Offline eval harness | ⚠️ SUBSTANTIVE BUT DEFECTIVE | Runs and reproduces; 3 open Criticals + WR-04 |
| `data-service/fixtures/recognition_eval/cassettes/{A0..A4}/` | Committed recordings | ✓ VERIFIED | 17 files (A0:4, A1:2, A2:2, A3:7, A4:2), tracked, replay clean |
| `35-EVAL-REPORT.md` | Terminal SC1 measurement artifact | ⚠️ NUMBERS SOUND, VERDICT MISFRAMED | Metrics reproduce exactly; verdict recorded as `blocked` where the data supports `failed` |
| `DG/src/DG.Grasshopper/Components/CanvasListenerComponent.cs` | Preview handlers + F4 fix | ✓ VERIFIED | Single-record composition across auto-clear + render; `RemoveTracked` records before removing |
| `DG/src/DG.Grasshopper/Components/StructureConfirmComponent.cs` | Accept/reject/partial + G12 gate | ✓ VERIFIED | ValueTable write L247, reject `GH_RemoveObjectAction` L271, G12 `blocked` path L190/204/287 |
| `DG/src/DG.Core/Parsing/CanvasAnnotationParser.cs` | Host resolution + dataType tiers + public seam | ✓ VERIFIED | `ComputeHostPatternIds` pattern-first (L446-466); `TryInferParameterDataType` public seam consumed by the confirm component |
| `35-UAT.md` | UAT close-out with no `blocked` entries | ✗ FAILED | 1 blocked (test 1), 1 pending (test 7); 5 passed |

### Key Link Verification

| From | To | Via | Status | Details |
|------|-----|-----|--------|---------|
| `StructureConfirmComponent` accept | `doc.ValueTable.SetValue("dg.recognized.<guid>")` | write path | ✓ WIRED | L247; key format matches extractor read |
| `CanvasContextExtractor` | `CanvasAnnotationParser` `Source == "recognized"` | ValueTable read → `RawGroup.Recognized` → parser ternary | ✓ WIRED | Live-proven end to end by UAT test 4's save/reopen/re-pull |
| `HandlePreviewStructure` | `RemovePendingPreviewObjects(doc, record)` | shared undo record across auto-clear + render | ✓ WIRED | L291→L304; the F4 fix |
| `StructureConfirmComponent` | `CanvasAnnotationParser.TryInferParameterDataType` | G12 accept-time gate | ✓ WIRED | L190; no inference logic duplicated in the GH layer |
| `TestEndToEndDriver` | `cassette` key for arm A4 | `negotiated_mode` | ✗ NOT_WIRED | CR-02 — hardcoded `json_schema_strict` vs. real `json_object` |
| `report.run_report_sweep` | permutation cassettes | (absent) | ✗ NOT_WIRED | WR-04 — 6 of A3's 7 cassettes unreachable by any replay path |

### Requirements Coverage

| Requirement | Source Plans | Description | Status | Evidence |
|-------------|-------------|--------------|--------|----------|
| **RCGN-01** | 35-01, 05, 06, 07, 08, 10, 11, 12, 13, 14, 15 | Recognition pipeline classifies untagged entities via the LLM gateway, schema-validated, bounded retry, tags as anchors | ⚠️ **PARTIAL** | Pipeline is built, hardened and instrumented (Tier-0 + Tier-1, Pydantic layer, G6–G13, cassette harness). **But the classification quality the requirement exists to deliver is measured at 1/32 correct.** Plumbing satisfied; outcome not. |
| **RCGN-02** | 35-02, 03, 09, 15 | Preview groups + scribbles in a distinct style inside an undo record, fully removable via undo or `clear_preview` | ✓ SATISFIED | Code verified; UAT tests 2/3/6 pass live incl. the F4 re-preview case and the newly-covered `clear_preview → Ctrl+Z` path |
| **RCGN-03** | 35-02, 04, 09, 15, 16 | Confirm / partial accept / reject on canvas; accepted become permanent convention groups indistinguishable from manual tags with `source: recognized`; rejected removed cleanly | ✓ SATISFIED | Code verified; UAT tests 4/5 pass live incl. save/reopen durability, nesting, and mixed-batch atomic undo |
| **RCGN-04** | 35-01, 04, 12, 15 | Nothing published to Neo4j without explicit on-canvas confirmation; unclassifiable blocks reported as unrecognized — never invented, never silently dropped | ✓ SATISFIED | 0 write primitives in both files; `unrecognized` block itself validated (WR-06); `silent_drop_count = 0` on every scored row in the regenerated report |

**No orphaned requirements.** All four RCGN IDs from `REQUIREMENTS.md` lines 76–79 are claimed by plan frontmatter; every plan's `requirements:` field maps to one of them.

**Documentation inconsistency (Info, pre-existing):** `REQUIREMENTS.md` L76–79 mark RCGN-01..04 as `[x]` complete, while the Traceability table at L166 still reads `RCGN-01 … RCGN-04 | Phase 35 | Pending`. The same staleness affects every shipped phase in that table — project-wide sync gap, not phase-35-specific. Separately, given this verification, the `[x]` on **RCGN-01** is now itself questionable and should arguably revert to unchecked or gain a quality caveat.

### Anti-Patterns Found

| File | Line | Pattern | Severity | Impact |
|------|------|---------|----------|--------|
| — | — | `TBD` / `FIXME` / `XXX` | — | **None found** across the 8 primary phase-touched files |
| `test_recognition_eval.py` | 686-693 | Assertion that cannot fail (CR-03) | 🛑 Blocker | The only paid test is structurally incapable of detecting a zero-recording run |
| `test_recognition_eval.py` | 593 | Known-wrong hardcoded default surviving its own fix commit (CR-02) | 🛑 Blocker | A4 replay impossible via the documented CI driver |
| `live_sweep.py` | 219-239 | Silent duplicate-work generator, no distinctness guard (CR-01) | 🛑 Blocker | Latent fabricated-stability + redundant-spend hazard |
| `report.py` | 210-213 | Missing replay path for recorded state (WR-04) | ⚠️ Warning | Permutation results unreproducible from committed cassettes |

### Behavioral Spot-Checks

| Behavior | Command | Result | Status |
|----------|---------|--------|--------|
| SC1 conjunctive gate runs and fails on M1 | `pytest --corpus=urbanblock_slice --arm=A3 --sc1-gate=0.60` | `M1=0.031 < threshold 0.60` | ✓ PASS (gate works; SC1 fails) |
| Replay sweep regenerates all metrics | `python -m tests.recognition_eval.report --arms A0..A4` | `scored 9; skipped 1`, values identical to report | ✓ PASS |
| A0 pre-registered validity gate | `pytest --corpus=frame_ablated --arm=A0` | `A0 validity check FAILED ... citation rate 0.000` | ✗ FAIL |
| A4 driver replay (CR-02) | `pytest TestEndToEndDriver --corpus=urbanblock_slice --arm=A4` | `CassetteMissError key=abd6a4bd...` | ✗ FAIL |
| Permutation distinctness (CR-01) | `few_shot_permutations` on real artifacts | A0: 1 distinct / 3; A3: 3 distinct / 3 | ✗ FAIL (latent) |
| No Neo4j write in recognition backend | `grep -vE '^\s*#' cg_recognition.py \| grep -cE 'session\.run\|driver\.session\|tx\.run\|GraphDatabase'` | `0` | ✓ PASS |
| No persistence in confirm component | `grep -cE 'HttpClient\|Neo4j\|neo4j\|data-service' StructureConfirmComponent.cs` | `1` — a doc comment asserting no persistence | ✓ PASS |
| Debt-marker scan (8 phase files) | `grep -nE 'TBD\|FIXME\|XXX'` | 0 matches | ✓ PASS |

*Test-suite baselines (Python 470/4, C# 403/3) are the documented Neo4j-offline environment baseline, not phase-35 defects — not re-derived here.*

### Human Verification Required

2 items — see `human_verification` frontmatter. UAT test 7 (G12 accept-time gate) remains `pending` and needs a live Rhino session; and the recognition→preview seam has never been exercised with the LLM actually on the path (every passing canvas UAT used a synthetic proposals payload posted directly to `gh_preview_structure`).

### Gaps Summary

Three gaps, one of which is the phase's headline.

**1. SC1 is not met.** M1 = 0.031 vs. a required 0.60, on exactly the corpus and arm SC1 specifies. This should be recorded as a measured FAIL, with the separate and genuinely-open diagnostic question (prompt defect vs. DeepSeek ceiling — needs A0f/A5) carried as a named follow-up. Recording it as `blocked` lets a 19x miss read as an absence of data when the data exists and is unambiguous. Everything else about how this was done is exemplary: pre-registered arms, frozen corpora, committed cassettes, a conjunctive gate that raises, honest interpretation limits stated on the number rather than in a footnote, and a candid "not measured" section. The work earned the right to state the failure plainly.

**2. The A0 harness-validity gate never passed.** Its own pre-registered rule says that when this happens, *no other arm's number may be reported.* The numbers were reported with a reasoned argument for why the G7 interception is a stronger signal than the literal check. That argument is defensible — G7's trigger condition does literally encode F3's signature — but substituting it for a raising pre-registered gate is the exact move pre-registration exists to block. Either amend the pre-registration explicitly and dated, or fix the control. Note this does not make the SC1 number optimistic; it is orthogonal to it.

**3. Three unfixed Criticals in the instrument.** CR-01/CR-02/CR-03 all reproduce. Scoped honestly: none falsifies a number published in `35-EVAL-REPORT.md` — I regenerated every metric from the cassettes and they match exactly, and the permutation sub-sweep ran on A3, which has enough examples for 3 genuine orderings. What they do damage is the harness's standing as a citable apparatus for the *next* run: A4 cannot be replayed by the documented CI driver, a zero-recording sweep would report green, the permutation table cannot be regenerated from committed state, and the documented `--permutations=3` command would bill and mis-report duplicate orderings on A0/A0f.

**The canvas half of the phase goal is achieved.** Preview, confirm, edit, reject — all live-verified, with the two previously-deferred behavior items now closed and the F4 crash fixed and retested. **The recognition half is not.** "AI classifies the untagged remainder of the canvas" currently classifies 1 block in 32 correctly on the evidence corpus. Phase 36 (persistence) can proceed against hand-tagged and accepted structure, but it should do so knowing that the recognition input feeding it is measured as not working.

---

*Verified: 2026-07-27*
*Verifier: Claude (gsd-verifier)*
