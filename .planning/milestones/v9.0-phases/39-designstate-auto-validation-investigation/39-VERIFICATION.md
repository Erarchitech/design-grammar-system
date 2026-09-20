---
phase: 39-designstate-auto-validation-investigation
verified: 2026-07-28T00:00:00Z
status: passed
score: 26/26 must-haves verified
behavior_unverified: 0
overrides_applied: 0
re_verification:
  previous_status: null
  note: "Initial verification — no prior 39-VERIFICATION.md existed"
warnings:
  - id: W-39-A
    item: "spec/DATABASE.md does not document the widened :ValidationRun semantics introduced by this phase"
    detail: "The phase adds trigger / verdictSource / capturedAt / completedAt / attempts / lastError and a status state machine (captured -> completed | superseded | failed), plus an IntegrationConfig{provider:'AutoValidation'} variant. spec/DATABASE.md line 108 still documents only Run_Id / ValidStatus / SendStatus / statePayloadJson / shaclReportJson. CLAUDE.md § Schema Change Propagation treats properties (e.g. shaclReportJson) as propagation surfaces, not only labels."
    severity: warning
    why_not_blocker: "REQUIREMENTS.md line 127 scopes this phase to 'Investigation + prototype + ADR only'; the ADR § Identity-model decision records the add-alongside model and its three accepted costs explicitly, and follow-up item 1 may change the model. Documenting a spike schema in the normative spec would be premature."
    human_decision_requested: "Document the prototype properties in spec/DATABASE.md now, or defer to the follow-up milestone alongside ADR item 1."
  - id: W-39-B
    item: "39-03-SUMMARY.md line 132 still carries the unreconcilable '~1.5 s dg-reasoner SHACL round-trip' decomposition, uncorrected in place"
    detail: "2.0 s debounce + 1.5 s already exceeds the artifact's recorded 2.679 s SC1 total. The figure appears in no EVIDENCE.json key."
    severity: warning
    why_not_blocker: "Both DELIVERABLE documents handle it correctly: 39-INVESTIGATION-NOTE.md § Provenance caveat (line 80) names the contradiction explicitly, refuses to use the figure, and derives path (a)'s bound from artifact arithmetic instead; 39-05-SUMMARY.md records it as a key decision. The SUMMARY is an execution record, not a phase deliverable."
    human_decision_requested: "Optionally annotate 39-03-SUMMARY.md line 132 in place so a reader who opens only that file is not misled."
verifier_reproductions:
  - "Re-ran data-service/tests/test_dsav_live_loop.py in-container (-m 'integration and live'): 6 passed in 194.82s — SC1 and SC2 reproduced independently of the committed artifact"
  - "Re-ran host-tier test_dsav_watcher.py: 18 passed; test_designstate_capture.py: 22 passed"
  - "Queried Speckle GraphQL directly: version 2ab708e884 exists in project 44088eefc6 / model a6d1e0c5da, message 'DG validation run 0afe92c2e2324a85a988d42c4ffedc95', createdAt 2026-07-27T20:04:58.470Z — matches the evidence artifact exactly"
  - "Probed the running data-service: /designstate/capture present in openapi.json; unauthenticated POST returns 401"
  - "Mechanical numeral audit: all 13 bolded numeric figures in the investigation note and all in the ADR are literally present in 39-EVIDENCE.json; 12 provenance markers on the analytic cells; zero free-floating estimates"
---

# Phase 39: DesignState Auto-Validation Investigation — Verification Report

**Phase Goal:** A prototyped, evidence-based answer to "can validation run automatically when a DesignState is captured?" — architecture chosen, guardrails defined, full implementation scoped for a follow-up milestone.
**Verified:** 2026-07-28
**Status:** passed (2 warnings, no gaps)
**Re-verification:** No — initial verification

---

## Verification method

This phase's central deliverable is *measured evidence*, so verification was weighted toward substantiation rather than presence. Adversarial starting hypothesis: **tasks completed, goal missed.** It did not survive.

What I executed myself rather than reading about:

| Check | Result |
|---|---|
| Re-ran the live-Docker evidence driver in-container (`test_dsav_live_loop.py -m "integration and live"`) | **6 passed in 194.82 s** |
| Re-ran host-tier `test_dsav_watcher.py` | **18 passed** |
| Re-ran host-tier `test_designstate_capture.py` | **22 passed** |
| Queried Speckle's own GraphQL for version `2ab708e884` | **exists**, message and `createdAt` match the artifact byte-for-byte |
| Probed the running data-service for `/designstate/capture` | present in `openapi.json`; unauthenticated POST → **401** |
| Mechanical numeral audit of both deliverables against `39-EVIDENCE.json` | **0 untraceable figures** |
| Debt-marker scan (TBD/FIXME/XXX/TODO/HACK/PLACEHOLDER) across all phase source | **0 markers** |

I deliberately did **not** re-run `test_dsav_publish_leg.py`: D-11 permits exactly one publish-enabled run phase-wide, and re-running would mint a second Speckle version — destroying the very property being measured. That leg is instead corroborated by the Speckle GraphQL read above plus the recorded operator confirmation.

My live re-run left **zero residue**: `p39-autoval` ValidationRun rows = 0, IntegrationConfig rows = 0, enabled AutoValidation projects = `[]`, git working tree unchanged for `data-service/` and `.planning/milestones/v9.0-phases/39-*`.

### Independent reproduction vs. committed artifact

| Signal | Committed `39-EVIDENCE.json` | My fresh re-run | Match |
|---|---|---|---|
| SC1 `trigger` / `verdict_source` | `auto` / `shacl` | `auto` / `shacl` | ✓ |
| SC1 `manual_trigger_used` | `false` | `False` | ✓ |
| SC1 latency | 2.679 s | 4.399 s | ✓ *(within the documented poll-offset spread; latency is a policy number, see below)* |
| SC1 `shacl_conforms` / shapes / `valid_status` | `false` / `["RunStatusShape_valid"]` / `[false,false]` | `False` / `['RunStatusShape_valid']` / `[False,False]` | ✓ **F-39-01 reproduced exactly** |
| SC2 collapse | 8 → 1, 7 superseded, queryable | 8 → 1, 7 superseded, queryable | ✓ |
| SC2 runs/min | 3 measured vs 3 configured, 20 captures | 3 vs 3, 20 captures | ✓ |
| D-08 ladder terminal | `failed`, `completed_at: null` | `failed`, `completed_at: None` | ✓ |
| Cypher constants executed | 8 | 8 | ✓ |
| `speckle_publish` block present | yes (merged by Wave 4) | **absent** | ✓ *(correct — the publish leg is a separate, non-collected module; confirms D-11's one-shot design is genuine and not re-derivable)* |

The latency variance is the one figure that moves, and the note already predicted exactly this: latency is bounded below by the debounce window plus a capture-to-next-tick phase offset of up to one full poll interval. My 4.399 s sample is that offset landing differently. It does **not** invalidate the note's derived bound for path (a): the note's inference is `SHACL round-trip ≤ (phase offset + SHACL) = 0.679 s` for the SC1 sample, which is a sound upper bound regardless of how the residual splits. It also independently reinforces the note's decision to reject the summary's "~1.5 s SHACL round-trip" claim (W-39-B) — a ~1.5 s round-trip is incompatible with a 0.679 s residual.

---

## Goal Achievement

### Roadmap Success Criteria

| # | Success Criterion | Status | Evidence |
|---|---|---|---|
| SC1 | Prototype demonstrably closes the loop on live Docker: DesignState captured → Run appears in ValidGraph and (if enabled) publishes to Speckle — hands-off | ✓ **VERIFIED** | All three clauses hold, and I reproduced two of them myself. **(a) Run appears:** fresh live run produced `status:'completed'`, `trigger:'auto'`, `verdictSource:'shacl'`. **(b) hands-off:** `manual_trigger_used: False`; the daemon is started from `app.py:94-121` FastAPI `lifespan` with both callables injected; no VALIDATOR trigger involved. **(c) publishes when enabled:** Speckle version `2ab708e884` confirmed present by direct GraphQL query, message `DG validation run 0afe92c2e2324a85a988d42c4ffedc95`. See the F-39-01 qualification below — it does **not** falsify SC1 as worded. |
| SC2 | Rapid successive captures do not flood Speckle: debounce/rate-limit design validated in the prototype, not just described | ✓ **VERIFIED** | Established twice over. **Structurally:** auto-runs are persist-only unless a separate per-project `publishEnabled` flag is on (D-09), so Speckle noise is 0 by default — `_auto_publish_run` is reached only behind `config.publish_enabled` (`dsav_watcher.py:538`). **By measurement, reproduced by me:** 8 captures in a 0.124 s burst → 1 run, 7 `superseded` and still queryable; 20 captures over a 60 s window → exactly 3 completed against a configured limit of 3. The single opt-in publish run minted exactly 1 version for 1 capture. |
| SC3 | The ADR records the chosen architecture, the rejected options with reasons, and the follow-up milestone scope | ✓ **VERIFIED** | ADR exists at `DG_OBSIDIAN/knowledge/decisions/Phase 39 DesignState auto-validation — data-service watcher, SHACL verdict, guardrails.md`, 171 lines. **Chosen architecture:** § Decision, path (b) with 8 concrete design commitments. **Rejected options:** § Rejected options — 7 rejections, each carrying an *empirical* blocker (Community edition → no CDC; APOC allowlisted but not installed; `CanvasCommandDispatcher` read-only by design; no server-side SWRL evaluator), not trade-off prose. **Follow-up scope:** § Follow-up milestone scope — 9 ordered items, item 1 being the headline coverage gap. Linked from `DG_OBSIDIAN/00-home/index.md:83`. |

**The F-39-01 qualification, stated plainly (as requested).** `poll_once` calls `shacl_fn` at `dsav_watcher.py:513` and only afterwards writes `ValidStatus` via `COMPLETE_QUERY` at line 523. I confirmed this ordering in source and reproduced its consequence live: every auto-run self-violates `RunStatusShape_valid`, the finding's `focusLabel` is the `runId` which matches no objState, and `derive_valid_status`'s conservative unmapped fallback (lines 378-379) flips every entry to `false`. **Auto-run verdicts are therefore currently a constant, not a judgement.**

My judgment: **SC1 is fully met, not partially met.** SC1 asks whether the Run *appears* in ValidGraph hands-off — not whether its verdict discriminates. It appears, with correct provenance stamps, in a measured 2.679 s / 4.399 s. What F-39-01 limits is the *usefulness* of the loop, and for an **investigation** phase whose deliverable is "an evidence-based answer", discovering and quantifying that limit is a success, not a shortfall. The failure mode I was hunting for — a phase that quietly reports a green loop while the verdict is meaningless — **did not occur**. Both documents lead with it:

- Investigation note line 166: *"This is the single most important thing in this note, and it is an **open, unresolved design question**. Phase 39 measured it; Phase 39 deliberately did not fix it."*
- Investigation note line 181: *"**Do not read the phase's success criteria as saying auto-validation currently produces meaningful pass/fail verdicts. It does not yet.**"*
- ADR line 78: *"This ADR must not be read as saying auto-validation currently produces meaningful pass/fail verdicts. It does not yet."*
- ADR § Follow-up scope item 1 folds F-39-01's resolution into the coverage-gap work.

**Neither document overclaims.** Verified.

### Observable Truths (PLAN frontmatter must-haves)

#### Plan 39-01 — watcher core

| # | Truth | Status | Evidence |
|---|---|---|---|
| 1 | Capture event is a `:ValidationRun` row `status:'captured'` keyed `{graph, project, runId}`; zero new node labels, schema sweep not triggered (D-01) | ✓ VERIFIED *(with a wording note)* | `CAPTURE_QUERY` (line 146) MERGEs `:ValidationRun {graph, project, runId}` with `status:'captured'`. Label scan of the module returns exactly two labels: `:ValidationRun` and `:IntegrationConfig` — **both pre-existing** (CLAUDE.md § ValidGraph Labels). Zero new labels confirmed. *Wording note:* the truth's literal clause "every Cypher constant … MERGEs/MATCHes `:ValidationRun` and no other label" is false as written — 3 of 8 constants target `:IntegrationConfig` — but the operative claim it exists to protect (no new labels ⇒ no ~10-file sweep) holds. See W-39-A for the property-level propagation question. |
| 2 | `poll_once()` runs to completion against an injected `FixtureSession` with zero live Neo4j, zero thread, zero `time.sleep` (D-03) | ✓ VERIFIED | 18 host-tier tests passed with no Neo4j reachable. Signature `poll_once(session, now, shacl_fn, publish_fn)` — all four injected; `_run_read`/`_run_write` branch on `session is not None` before ever touching `_get_driver()`. No `time.sleep` anywhere in the module (only `_stop_event.wait` in the thread loop, outside `poll_once`). |
| 3 | A project with no `IntegrationConfig{provider:'AutoValidation'}` row is invisible — `poll_once()` no-ops (D-13, absent row = disabled) | ✓ VERIFIED | `ENABLED_PROJECTS_QUERY` filters `cfg.enabled = true` at the Cypher level, so an unconfigured project is never enumerated. `get_auto_validation_config` returns `None` on an absent row and never creates one. Tests `test_no_enabled_projects_returns_noop_summary_and_issues_no_writes` and `test_get_auto_validation_config_absent_row_returns_none` pass. **Live confirmation:** `list_enabled_projects()` on the running container returns `[]`. |
| 4 | N captured rows inside the debounce window collapse to exactly 1 validated run; the other N-1 carry `status:'superseded'`, still queryable (D-14) | ✓ VERIFIED | `COALESCE_QUERY` uses `FOREACH` over the stale tail (marks, never deletes). Unit: `test_debounce_release_coalesces_five_captured_rows_marks_four_superseded`. **Live, reproduced by me:** 8 → 1, `superseded: 7`, `superseded_rows_still_queryable: True`. |
| 5 | A SHACL sidecar failure leaves the row `captured` and increments attempts; the maxAttempts-th failure flips it to `failed` with a reason (D-08) | ✓ VERIFIED | `FAIL_QUERY` binds `nextAttempts` in a `WITH` before the `SET` and uses `CASE WHEN nextAttempts >= $maxAttempts`. Unit: `test_fail_path_shacl_timeout_flips_to_failed_on_third_attempt`, `test_fail_path_shacl_fn_none_never_completes_and_reason_is_no_response`. **Live ladder reproduced by me:** tick 1 → `captured`/1, tick 2 → `captured`/2, tick 3 → `failed`/3, `completed_at: None`, `verdict_source: None`. |
| 6 | A completed auto-run carries `trigger:'auto'` and `verdictSource:'shacl'` (D-07) | ✓ VERIFIED | `COMPLETE_QUERY` SETs both unconditionally. Reproduced live on a fresh run. |

#### Plan 39-02 — capture endpoint + lifespan wiring

| # | Truth | Status | Evidence |
|---|---|---|---|
| 7 | POST with no Authorization header → 401, writes nothing | ✓ VERIFIED | `app.py:2221-2230`; test `test_missing_header_returns_401_auth_failed` passes. **Live probe:** unauthenticated POST to the running service returned **401**. |
| 8 | Token bound to project A + body naming project B → 403, writes nothing (T-39-02) | ✓ VERIFIED | `app.py:2236-2243`, exact-equality check against the credential's bound project. Tests `test_project_mismatch_returns_403_and_writes_nothing` **and** `test_project_mismatch_response_leaks_no_project_names` (generic message, T-39-06) both pass. |
| 9 | Valid project-matched token → 202 with a runId, one `:ValidationRun` row `status:'captured'` | ✓ VERIFIED | `status_code=202` on the decorator; `test_matching_project_returns_202_accepted_and_records_one_capture` passes. Route confirmed live in `openapi.json`. |
| 10 | Watcher thread starts at app startup and stops on shutdown; importing app in an existing test file does not start it | ✓ VERIFIED | `lifespan` at `app.py:94-121`; module has no import-time thread start (`start_watcher` is called only from `lifespan`). Tests `test_lifespan_starts_and_stops_watcher_thread_injecting_both_callables`, `test_lifespan_import_does_not_start_watcher_thread`, `test_lifespan_survives_watcher_start_failure` all pass. The comment block at lines 78-89 documents the real trap correctly (supplying `lifespan=` silently disables `on_startup` handlers) and `ensure_spec_indexes()` is called explicitly at line 99 to compensate. |
| 11 | `store_validation_run` is byte-for-byte unchanged (D-10), proven by a pinned source hash | ✓ VERIFIED | `test_store_validation_run_source_hash_is_pinned` present and passing in the 22-test run. Zero regression surface on the shipped manual publish path. |

#### Plan 39-03 — live-Docker evidence

| # | Truth | Status | Evidence |
|---|---|---|---|
| 12 | A single authenticated capture produces a completed run with `trigger:'auto'` / `verdictSource:'shacl'`, no further human action (SC1) | ✓ VERIFIED | *Rolled into SC1 above — reproduced by me on a fresh live run.* |
| 13 | A burst of N rapid captures yields exactly 1 non-superseded run; N-1 carry `superseded` and remain queryable (SC2) | ✓ VERIFIED | *Rolled into SC2 above — reproduced by me: 8 → 1, 7 superseded, queryable.* |
| 14 | Measured latency, collapse ratio and runs-per-minute exist as **numbers in a committed artifact**, not prose | ✓ VERIFIED | `39-EVIDENCE.json` is committed (14 350 bytes), machine-written, with `latency_seconds: 2.679`, `collapse_ratio: "8:1"`, `measured_runs_per_minute: 3`. `missing_measurements: []`. The driver writes to `DSAV_EVIDENCE_PATH` (`/app/data/dsav-evidence.json`) inside the container, so a re-run cannot silently overwrite the committed artifact — verified by re-running and confirming the committed file is untouched. |
| 15 | `list_validation_runs` returns without raising for a project containing captured, superseded, failed and shacl-verdicted completed rows | ✓ VERIFIED | `list_runs_tolerance`: HTTP 200, 5 runs spanning all four statuses, `every_run_has_run_id: true`. Reproduced in the passing live suite. |
| 16 | The four capture/coalesce/complete/fail Cypher shapes execute against live Neo4j 5.26 without error | ✓ VERIFIED | **All 8** constants executed (not just 4), against Neo4j Kernel 5.26.28 (community), with expected row shapes — 39-RESEARCH.md assumption A2 discharged. Reproduced by me: `constants_executed` = 8. The load-bearing `COALESCE_QUERY`-with-exactly-one-captured-row case returns `keptRunId` correctly (the `FOREACH`-not-`UNWIND` P-09 correction is real and tested). |

#### Plan 39-04 — the single Speckle publish leg

| # | Truth | Status | Evidence |
|---|---|---|---|
| 17 | Exactly one auto-run phase-wide runs with `publishEnabled` true, and it mints a real Speckle version (D-11) | ✓ VERIFIED | `versions_minted: 1`, `captures_issued: 1`, `speckle_versions_per_capture: 1.0`. **Independently confirmed by me** via Speckle GraphQL: version `2ab708e884` exists in project `44088eefc6` / model `a6d1e0c5da`. My own live re-run of Wave 3 minted **no** second version (the publish leg is a separate `live`-marked module and was not collected — its `speckle_publish` block is absent from the fresh artifact). |
| 18 | That run's row carries `SendStatus` true plus the Speckle identifier fields, written in place without calling `store_validation_run` | ✓ VERIFIED *(with disclosed caveat)* | `_auto_publish_run` (`app.py:2092-2195`) writes via `AUTO_COMPLETE_PUBLISH_QUERY` (defined line 2077) — a `SET` on the existing row; it never calls `store_validation_run`. Measured `send_status: true` with all identifier fields populated, and `verified_immediately_after_the_leg.send_status_true_rows: 1`. **Caveat properly disclosed:** the Neo4j row was later destroyed — see the row-lifecycle finding below. |
| 19 | A human has confirmed the Speckle version is visible in the viewer for the fixture project | ✓ VERIFIED — **genuine human confirmation** | `39-04-SUMMARY.md:129-141` records the operator's **verbatim** reply (*"Approved — version is there"*), plus a second, independent decision the operator made at the same checkpoint (choosing option (b), add the `live` marker, over the alternatives). A self-approval would not produce a discretionary choice among presented options that then materially changed the codebase. That marker change is real: `test_dsav_live_loop.py:69` now reads `pytestmark = [pytest.mark.integration, pytest.mark.live]`, committed as `c37a8bc`. `coverage` entry sets `human_judgment: true`. This discharges the corresponding row in `39-VALIDATION.md` § Manual-Only Verifications. |
| 20 | The Speckle-noise data point is a real measured version, not an estimate | ✓ VERIFIED | Confirmed against Speckle's own API, not against any project document: `id 2ab708e884`, `message "DG validation run 0afe92c2e2324a85a988d42c4ffedc95"`, `createdAt "2026-07-27T20:04:58.470Z"` — 0.97 s after the row's recorded `completedAt` of 20:04:57.503Z, exactly as the artifact states. |

#### Plan 39-05 — investigation note and ADR

| # | Truth | Status | Evidence |
|---|---|---|---|
| 21 | The note compares all three trigger architectures on latency, publish-flood and Speckle-noise, path (b) measured, (a)/(c) analytic | ✓ VERIFIED | `39-INVESTIGATION-NOTE.md:46-53` — a 3-column × 7-row comparison matrix covering latency, publish-flood, Speckle noise, dependency footprint, testability-without-Rhino, and verdict. |
| 22 | Every analytic estimate cites a measured path-(b) number or a recorded empirical blocker — no free-floating trade-off prose | ✓ VERIFIED | **12 bracketed provenance markers** (`[anchor: …]` / `[blocker: …]`) counted mechanically across the analytic cells. Every path-(a) and path-(c) cell carries at least one. The four named blockers are each independently checkable claims about this repo (Community edition, APOC allowlisted-not-installed, `CanvasCommandDispatcher` read-only, no server-side SWRL evaluator). |
| 23 | The ADR exists in `DG_OBSIDIAN/knowledge/decisions/` and records chosen architecture, each rejected option with its empirical blocker, the guardrails, and follow-up milestone scope | ✓ VERIFIED | *Rolled into SC3 above.* |
| 24 | The SHACL/SWRL coverage gap is stated as the headline finding and as follow-up item #1 | ✓ VERIFIED | Note § "Headline finding: the SHACL/SWRL coverage gap" (line 156), flagged forward from line 21. ADR § same heading (line 70) with *"This is **follow-up milestone item number one**"* explicit at line 74, and § Follow-up milestone scope item 1 matches. |
| 25 | The ADR is linked from `DG_OBSIDIAN/00-home/index.md` | ✓ VERIFIED | `index.md:83` — a scoped single-line wiki-link insertion into the Decisions list, with a descriptive summary naming the coverage gap as the headline open finding. |
| 26 | **No-estimates rule held: every figure in the note and ADR traces to a key in `39-EVIDENCE.json`** | ✓ VERIFIED | Mechanically audited. **13/13** bolded numeric figures in the note and **all** in the ADR are literally present in the evidence artifact. **Zero** untraceable figures. The only two derived numbers (0.679 s residual, 4.299 s publish-leg interval) are explicitly labelled as arithmetic over artifact values in § Provenance. The two summary-sourced figures are quarantined behind an explicit caveat and used in no comparison cell. |

**Score: 26/26 truths verified** (0 present-but-behavior-unverified, 0 overrides applied).

---

## Required Artifacts

| Artifact | Expected | Status | Details |
|---|---|---|---|
| `data-service/dsav_watcher.py` | Watcher state machine + guardrails + pure `poll_once` | ✓ VERIFIED | 613 lines. 8 parameterized Cypher constants, no interpolation. Imported by `app.py:75`, called from `lifespan` and from the capture route. Substantive — no stubs, no debt markers. |
| `data-service/tests/dsav_fixtures.py` | `FixtureSession` duck-type + pinned fixture project | ✓ VERIFIED | 154 lines; `p39-autoval` pinned (P-03), isolated from `p37-structure` / `p1` / `default-project`. |
| `data-service/tests/test_dsav_watcher.py` | Host-tier state-machine suite | ✓ VERIFIED | 466 lines, **18 tests, all passing on host with no Neo4j**. Names map 1:1 to the D-08/D-13/D-14/P-02 truths. |
| `data-service/app.py` | `POST /designstate/capture` + `lifespan` + `_auto_publish_run` | ✓ VERIFIED | Capture route lines 2198-2272; `lifespan` lines 94-121; `_auto_publish_run` lines 2092-2195; `AUTO_COMPLETE_PUBLISH_QUERY` line 2077; `DSAV_MAX_STATE_PAYLOAD_BYTES` line 149. Route confirmed live. |
| `data-service/tests/test_designstate_capture.py` | Auth matrix + lifespan + publish-adapter + D-10 hash guard | ✓ VERIFIED | 556 lines, **22 tests, all passing**. Full rejection matrix (missing / non-Bearer / wrong-prefix / unknown / revoked / cross-project / oversized / empty / absent). |
| `data-service/tests/test_dsav_live_loop.py` | Live-Docker evidence driver | ✓ VERIFIED | 1112 lines, `pytestmark = [integration, live]` (line 69), **6 tests, all passing — re-run by me**. |
| `data-service/tests/test_dsav_publish_leg.py` | Single D-11 Speckle publish leg | ✓ VERIFIED | 647 lines, `pytestmark = [integration, live]` (line 73). Correctly **not** collected by a routine run; deliberately not re-executed by the verifier (D-11). |
| `39-EVIDENCE.json` | Measured evidence artifact | ✓ VERIFIED | 14 350 bytes, committed. Configuration + software context + 6 measurement blocks + 2 findings. `missing_measurements: []`. Every figure in both deliverables traces here. |
| `39-INVESTIGATION-NOTE.md` (DSAV-01) | Three-architecture comparison | ✓ VERIFIED | 238 lines. Comparison matrix, full path-(b) measurements, headline finding, guardrails table, 6 ship-as-is consequences, provenance section, traceability note. |
| ADR in `DG_OBSIDIAN/knowledge/decisions/` (DSAV-03) | Decision record + follow-up scope | ✓ VERIFIED | 171 lines. Frontmatter `status: accepted`, `requirements: [DSAV-01, DSAV-02, DSAV-03]`, `milestone: v9.0`. Linked from vault index. |

---

## Key Link Verification

| From | To | Via | Status | Details |
|---|---|---|---|---|
| `dsav_watcher.py` | `app.py` | **must NOT import** — `shacl_fn`/`publish_fn` injected by caller | ✓ WIRED | Zero `import app` in the module; own `_get_driver()`, own `VALIDATION_GRAPH` constant (duplicated by design, documented lines 5-9). Cycle broken at the call site. |
| `app.py` `lifespan` | `dsav_watcher.start_watcher` | injects `_call_shacl_validate` + `_auto_publish_run` | ✓ WIRED | `app.py:101-104`, both callables passed. Wrapped in try/except so a watcher failure never prevents the service from serving (T-39-08), and `stop_watcher(timeout=5.0)` on shutdown. |
| capture route | `dsav_watcher.capture_state` | single writer of `CAPTURE_QUERY` | ✓ WIRED | `app.py:2260`. No Cypher embedded in `app.py` for this path — confirmed by reading lines 2198-2272. |
| `_auto_publish_run` | run row | `AUTO_COMPLETE_PUBLISH_QUERY` `SET`, after completion, never `store_validation_run` | ✓ WIRED | Runs only from `poll_once` line 541, strictly after `COMPLETE_QUERY`. `verdict_state_before_publish` in the artifact **observes** the P-07 inversion rather than assuming it. Publish exceptions are caught at `dsav_watcher.py:542-545` and never revert the verdict. |
| `derive_valid_status()` | dg-reasoner `_state_label()` | joins on `label or objectRef or stateId` | ✓ WIRED | `dsav_watcher.py:351` builds the index on exactly that key precedence. This is the sole join between a SHACL `focusLabel` and an ObjState index — and F-39-01 is precisely what happens when the join misses. |
| Every poll tick | Neo4j session | own `driver.session()`, none spanning threads/ticks | ✓ WIRED | `_run_read`/`_run_write` both use `with _get_driver().session() as …` per call. No module-level session. |
| Note figures | `39-EVIDENCE.json` | read from artifact, never retyped | ✓ WIRED | Mechanically audited: 13/13 traceable, 0 free-floating. |
| ADR | investigation note + vault index | cross-link per D-16 | ✓ WIRED | ADR § References line 163 names the note; `index.md:83` links the ADR. |

---

## Data-Flow Trace (Level 4)

| Artifact | Data Variable | Source | Produces Real Data | Status |
|---|---|---|---|---|
| `39-EVIDENCE.json` | all measurement blocks | `test_dsav_live_loop.py` / `test_dsav_publish_leg.py`, written by `json.dump` from values read off Neo4j rows | ✓ Yes — machine-written, and I regenerated an equivalent artifact myself | ✓ FLOWING |
| `39-INVESTIGATION-NOTE.md` | every numeral | `39-EVIDENCE.json` | ✓ Yes — 13/13 traceable | ✓ FLOWING |
| ADR | figures + decisions | evidence artifact + note (deliberately does not restate tables) | ✓ Yes | ✓ FLOWING |
| Latency figures | `latency_seconds` | `row.completedAt − row.capturedAt` (P-13) | ✓ Yes — read off the persisted node, **not** an in-process stopwatch | ✓ FLOWING |
| `ValidStatus` on an auto-run | `derive_valid_status()` output | SHACL body + `statePayloadJson` from `COALESCE_QUERY` | ⚠️ Flows, but is **currently a constant** `[false,…]` for every auto-run | ⚠️ Disclosed as F-39-01 — see judgment above; not a hidden stub, it is the phase's headline finding |

---

## Behavioral Spot-Checks

| Behavior | Command | Result | Status |
|---|---|---|---|
| Live loop closes hands-off (SC1) + burst collapse + rate cap + D-08 ladder + Cypher shapes + list tolerance | `docker compose exec -T data-service python -m pytest tests/test_dsav_live_loop.py -q -m "integration and live"` | `6 passed in 194.82s` | ✓ PASS |
| Watcher state machine, host tier | `python -m pytest data-service/tests/test_dsav_watcher.py -q` | `18 passed in 0.37s` | ✓ PASS |
| Capture endpoint auth matrix + lifespan + D-10 hash | `python -m pytest data-service/tests/test_designstate_capture.py -q` | `22 passed in 1.37s` | ✓ PASS |
| Capture route exposed on the running service | `curl /openapi.json` → path filter | `['/designstate/capture']` | ✓ PASS |
| Unauthenticated capture rejected | `curl -X POST /designstate/capture` (no token) | `401` | ✓ PASS |
| Speckle version durability (independent of all project docs) | Speckle GraphQL `project→model→version(2ab708e884)` | returns id + matching message + `createdAt 2026-07-27T20:04:58.470Z` | ✓ PASS |
| Opt-in default is disabled (D-13) | `dsav_watcher.list_enabled_projects()` in the live container | `[]` | ✓ PASS |
| Single-worker assumption (load-bearing per ADR consequence 5) | `/proc/1/cmdline` in data-service | `uvicorn app:app --host 0.0.0.0 --port 8000` — no `--workers` | ✓ PASS |
| Verifier left no residue | Neo4j counts for `p39-autoval` after re-run | ValidationRun 0, IntegrationConfig 0, enabled `[]`; git tree clean | ✓ PASS |
| Publish leg **not** re-run (D-11 respected) | fresh artifact `speckle_publish` key | absent — module correctly not collected | ✓ PASS |

---

## Requirements Coverage

| Requirement | Source Plan | Description | Status | Evidence |
|---|---|---|---|---|
| DSAV-01 | 39-03, 39-05 | Investigation note compares trigger architectures with latency, publish-flood, Speckle-noise analysis | ✓ SATISFIED | `39-INVESTIGATION-NOTE.md`, 3×7 comparison matrix, 12 provenance markers, all figures artifact-traceable |
| DSAV-02 | 39-01, 39-02, 39-03, 39-04 | Prototype demonstrates at least one path end-to-end: capture produces a validation Run without a manual VALIDATOR trigger | ✓ SATISFIED | `dsav_watcher.py` + capture route + lifespan; **reproduced by the verifier** on live Docker with `manual_trigger_used: False` |
| DSAV-03 | 39-05 | ADR records chosen architecture and guardrails (debounce, per-project rate limit, per-project opt-in) and scopes full implementation to a follow-up milestone | ✓ SATISFIED | ADR filed and index-linked; all three guardrails demonstrated with measured numbers, plus a fourth (bounded attempt counter) |

**Orphaned requirements: none.** `.planning/REQUIREMENTS.md:104-106` maps exactly DSAV-01/02/03 to Phase 39; all three are claimed across the plans' `requirements` fields. The traceability range row (line 170) now reads `✅ Complete (2026-07-28)` — consistent with all three checkboxes, and the note's § "A note on requirement traceability" (line 224) correctly explains why the range row lagged during execution.

---

## Anti-Patterns Found

| File | Line | Pattern | Severity | Impact |
|---|---|---|---|---|
| — | — | **No TBD / FIXME / XXX debt markers** in any file modified by this phase | — | Debt-marker gate: **clean** |
| — | — | **No TODO / HACK / PLACEHOLDER** in `dsav_watcher.py`, the phase test modules, or the `app.py` phase region (lines 2000-2280) | — | Clean |
| `spec/DATABASE.md` | 108 | New `:ValidationRun` properties and status state machine not propagated to the normative schema spec | ⚠️ Warning (W-39-A) | Disclosed in the ADR as accepted debt; see the warning entry for the human decision requested |
| `39-03-SUMMARY.md` | 132 | "~1.5 s dg-reasoner SHACL round-trip" — irreconcilable with the recorded 2.679 s total and present in no artifact key | ⚠️ Warning (W-39-B) | Corrected in the deliverable documents, uncorrected in place in the execution record |

Notably **absent**: no orphaned modules, no static/empty returns standing in for data, no `return null` stubs, no console-log-only handlers. `derive_valid_status()` returning `([], 0)` on an unparseable envelope is a documented never-raise contract with three dedicated passing tests, not a stub.

---

## Disconfirmation Pass

Per the Confirmation Bias Counter, I looked specifically for things that pass but should not:

1. **A requirement only partially met.** DSAV-02's prototype is real but its *verdict* is a constant (F-39-01). I judged this against SC1's literal wording and found SC1 met — but I record here that a reader who wants "auto-validation that says something true about a design" does not have it yet. Both deliverables say so first and loudest, so this is disclosed, not partial-in-disguise.
2. **A test that passes without testing the stated behavior.** I checked the highest-risk candidate: `test_store_validation_run_source_hash_is_pinned` (D-10). It pins a source hash — a real regression guard, not a tautology, and it would fail on any edit to the shipped manual-publish writer. I also checked that the live driver reads latency from row timestamps rather than a stopwatch: `latency_source` is `"row.completedAt - row.capturedAt (P-13)"`, and the artifact's structure confirms it.
3. **An error path with no coverage.** The publish-failure path is covered (`test_publish_gating_publish_fn_raising_is_reported_but_run_still_completes`) as is the watcher-start-failure path (`test_lifespan_survives_watcher_start_failure`). The one path with no automated coverage is a **partial** Speckle failure mid-publish (e.g. version minted but `AUTO_COMPLETE_PUBLISH_QUERY` fails) — the run would stay `completed` with a real orphan Speckle version and null identifier fields. Not reachable in a spike and not claimed by any must-have; noting it for the follow-up milestone.
4. **Did the evidence survive its own destruction honestly?** The `row_lifecycle` block is the sharpest test of this phase's integrity, and it passes: it records `run_row_present_now: false`, names the exact fixture and mechanism that deleted the row, states the row was **not** recreated and the leg **not** re-run with the D-11 reason, and points at the durable Speckle-side proof. I verified that Speckle proof myself. The note gives it a call-out block (line 140) rather than a footnote; the ADR carries it as consequence 7. **This is disclosed, not glossed.** The remediation (adding the `live` marker) is real and committed.
5. **Did a SUMMARY claim outrun the code?** I checked the most quotable claim — "zero new packages phase-wide" — against the module's imports: `json`, `logging`, `os`, `threading`, `time`, `dataclasses`, `datetime`, `typing`, `neo4j`. All stdlib or already-present. Claim holds.

---

## Gaps Summary

**None.** The phase goal — *a prototyped, evidence-based answer, with architecture chosen, guardrails defined, and full implementation scoped for a follow-up milestone* — is achieved, and I confirmed it by re-executing the evidence rather than by reading about it.

What makes this pass rather than a paper pass:

- The loop **actually closes** on live Docker. I ran it. 6/6 live scenarios green in 194 s, with `manual_trigger_used: False`.
- The guardrails are **demonstrated, not described**. 8→1 collapse and a 3-vs-3 rate cap reproduced exactly on a fresh run, months of prose notwithstanding.
- The Speckle version **exists**, confirmed against Speckle's own API rather than against any document in this repository.
- The no-estimates rule **held completely**: 13/13 bolded figures traceable, 0 free-floating, 12 provenance markers on the analytic cells.
- The phase's most damaging finding about itself (F-39-01) is **led with, not buried** — in both deliverables, with an explicit "do not read the success criteria as saying…" warning. I reproduced F-39-01 independently and it is exactly as described.
- The one piece of destroyed evidence is **reported rather than repaired**, with the reason (D-11) stated and the durable substitute identified.

Two warnings are recorded above for a human decision (W-39-A schema-spec propagation, W-39-B a stale figure in an execution record). Neither touches a must-have truth, a roadmap success criterion, or a requirement, and neither blocks Phase 40 — whose INTG-03 deliverable reads this ADR to learn that validation runs **auto**, via a data-service watcher, with a SHACL verdict that is not yet discriminating.

---

_Verified: 2026-07-28_
_Verifier: Claude (gsd-verifier)_
