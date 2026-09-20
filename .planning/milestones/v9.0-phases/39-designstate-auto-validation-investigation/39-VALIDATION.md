---
phase: 39
slug: designstate-auto-validation-investigation
status: passed-with-warnings
nyquist_compliant: true
wave_0_complete: false
created: 2026-07-27
---

# Phase 39 — Validation Strategy

> **Reconciled 2026-09-20 (GSD-ALIGN-009).** Frontmatter `status:` was `planned` while
> `39-VERIFICATION.md` recorded `passed` (26/26 must-haves, 2026-07-28). The two now agree.
> `passed-with-warnings` preserves W-39-A (spec/DATABASE.md does not document the widened
> `:ValidationRun` semantics), W-39-B (stale ~1.5 s SHACL round-trip figure in
> `39-03-SUMMARY.md:132`), and F-39-01 (auto-runs SHACL-validated before their own `ValidStatus`
> is written) as **disclosed open items**, not as failures hidden by a passed status.
> This phase remains "Investigation + prototype + ADR only" — it is **not** production
> auto-validation completion. See `.planning/reconciliation/GSD-ALIGN-RECONCILIATION.md`.


> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest (data-service, in-container) |
| **Config file** | `data-service/tests/` (see `data-service/tests/README.md` — two-tier convention) |
| **Quick run command** | `docker compose exec -T data-service python -m pytest tests/ -q` |
| **Full suite command** | `docker compose exec -T data-service python -m pytest tests/ -v` |
| **Estimated runtime** | ~60-90 seconds |

**Tier note:** this phase's checks split across the two tiers already established in `data-service/tests/README.md`:

- **Tier 1 (pure/unit, no stack):** the pure `poll_once()` body driven by a `FixtureSession` duck-type (the `test_dg_context.py:104-119` precedent), debounce/coalesce logic, rate-limit counters, Cypher parameter shapes, config read/write against `provider:'AutoValidation'`.
- **Tier 2 (in-container, live compose):** the SHACL round-trip through dg-reasoner, the capture→run loop closure, the measured burst, and the single Speckle publish leg (D-11).

---

## Sampling Rate

- **After every task commit:** Run `docker compose exec -T data-service python -m pytest tests/ -q`
- **After every plan wave:** Run the full suite plus, from Wave 2 onward, the live-Docker E2E driver
- **Before `/gsd-verify-work`:** Full suite green AND the SC1/SC2 evidence artifacts written
- **Max feedback latency:** 90 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| 39-01-T1 | 01 | 1 | DSAV-02 | T-39-03, T-39-05 | Retries bounded by an attempt counter; guardrail counters held in-process so polling never write-amplifies against Neo4j | unit (import + symbol contract) | `python -c "import sys; sys.path.insert(0, 'data-service'); import dsav_watcher as w; assert callable(w.poll_once)"` | ❌ created by this task | ⬜ pending |
| 39-01-T2 | 01 | 1 | DSAV-02 | T-39-03, T-39-05 | Debounce collapse, rate-limit skip, and the D-08 attempt ladder are asserted deterministically | unit | `python -m pytest data-service/tests/test_dsav_watcher.py -q` | ❌ created by this task | ⬜ pending |
| 39-02-T1 | 02 | 2 | DSAV-02 | T-39-01, T-39-02, T-39-06, T-39-07 | Bearer connector-token auth, strict project binding, generic 403, payload size cap | unit (TestClient) | `python -m pytest data-service/tests/test_designstate_capture.py -q -k "auth or mismatch or accepted"` | ❌ created by 39-02-T3 | ⬜ pending |
| 39-02-T2 | 02 | 2 | DSAV-02 | T-39-04, T-39-08 | Publish reachable only behind the opt-in flag and non-fatal; watcher start/stop failures never take down the service | unit | `python -m pytest data-service/tests/test_designstate_capture.py -q -k "lifespan or publish or store_validation_run"` | ❌ created by 39-02-T3 | ⬜ pending |
| 39-02-T3 | 02 | 2 | DSAV-02 | T-39-01, T-39-02, T-39-06 | Full rejection matrix (missing, malformed, unknown, revoked, cross-project) plus the pinned D-10 source-hash guard | unit | `python -m pytest data-service/tests/test_designstate_capture.py -q` | ❌ created by this task | ⬜ pending |
| 39-03-T1 | 03 | 3 | DSAV-01, DSAV-02 | T-39-01, T-39-02, T-39-04, T-39-10 | Measured path is the authenticated path; every write scoped to `p39-autoval`; all runs persist-only with `SendStatus` false | integration / E2E | `docker compose exec -T data-service python -m pytest tests/test_dsav_live_loop.py -q -m integration` | ❌ created by this task | ⬜ pending |
| 39-03-T2 | 03 | 3 | DSAV-01 | T-39-09, T-39-12 | Committed evidence carries no token; measurements are machine-written, not hand-typed | CLI assertion | `python -c "import json; d=json.load(open('.planning/milestones/v9.0-phases/39-designstate-auto-validation-investigation/39-EVIDENCE.json')); assert d['measurements']['sc1_loop_closure']['latency_seconds'] > 0"` | ❌ created by this task | ⬜ pending |
| 39-04-T1 | 04 | 4 | DSAV-02 | T-39-04, T-39-11, T-39-12 | Exactly one publish-enabled run phase-wide; flag reset and config row deleted in teardown; a blocked Speckle stack is recorded, never faked | integration + live | `docker compose exec -T data-service python -m pytest tests/test_dsav_publish_leg.py -q -m "integration and live"` | ❌ created by this task | ⬜ pending |
| 39-04-T2 | 04 | 4 | DSAV-02 | T-39-11 | Operator confirms the Speckle version is real and that no `provider:'AutoValidation'` row is left enabled | manual (blocking checkpoint) | human-check — see Manual-Only Verifications below | n/a | ⬜ pending |
| 39-05-T1 | 05 | 5 | DSAV-01 | T-39-12 | Every path-(b) number is transcribed from the evidence artifact and mechanically re-checked against it | CLI assertion | `python -m pytest data-service/tests/ -q` plus the note-transcription check in 39-05-PLAN.md Task 1 | ❌ created by this task | ⬜ pending |
| 39-05-T2 | 05 | 5 | DSAV-03 | T-39-13, T-39-03 | Vault index edited scope-wise, not rewritten; the restart-resettable rate limit is recorded as an explicit residual | CLI assertion | the ADR section/front-matter check in 39-05-PLAN.md Task 2 | ❌ created by this task | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

**Planner contract for this table:** every task that touches `POST /designstate/capture` MUST carry a non-empty Threat Ref — the capture endpoint is a new unauthenticated write-amplifier and is the highest-severity item in this phase's threat model (39-CONTEXT.md § Open for the planner). Security enforcement is active at ASVS L1, block-on-`high`.

---

## Wave 0 Requirements

- [ ] `data-service/tests/test_dsav_watcher.py` — the watcher's pure poll function, following the `FixtureSession` duck-type pattern in `tests/test_dg_context.py` (no mocking library). **Closed by 39-01-T2 (Wave 1).**
- [ ] `data-service/tests/test_designstate_capture.py` — capture-endpoint auth matrix and the D-10 source-hash guard. **Closed by 39-02-T3 (Wave 2).**
- [ ] `data-service/tests/test_dsav_live_loop.py` — the live-Docker evidence-capture methodology gap: burst captures, read back row timestamps, persist measured numbers. **Closed by 39-03-T1 (Wave 3).**
- [ ] Isolated fixture project string — pinned as **`p39-autoval`** in `data-service/tests/dsav_fixtures.py` (planner decision P-03), distinct from `p37-structure`, `p1` and `default-project`. **Closed by 39-01-T2 (Wave 1).**
- [ ] No framework install needed — pytest already present in the data-service image. Confirmed: the phase installs zero new packages.

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| ADR completeness and correctness | DSAV-03 | Editorial judgement — an ADR can be automatically checked for *presence* of the required sections (chosen architecture / rejected options with reasons / follow-up milestone scope), but not for whether the reasoning is sound | Read the filed ADR in `DG_OBSIDIAN/knowledge/decisions/`; confirm it records the chosen architecture, each rejected option with its **empirical** blocker (Community edition → no CDC, APOC absent, bridge read-only by design, no server-side SWRL evaluator), the SHACL/SWRL coverage gap as headline finding + follow-up item #1, and the D-15 restart-resets-window caveat |
| Single Speckle publish leg produced a real version | DSAV-02 / SC1 | Requires a working Speckle config in the dev stack and visual confirmation the version landed (D-11) | With the auto-publish flag on for one run: capture once, confirm a new Speckle version exists for the project and the run row carries `SendStatus` true |
| Investigation note's analytic columns for paths (a) and (c) | DSAV-01 | Paths (a)/(c) are reasoned estimates anchored to measured path-(b) numbers (D-04), not executed measurements | Confirm each estimate cites either a measured path-(b) number or a recorded blocker from 39-CONTEXT.md § Environment constraints |

---

## Success-Criterion Signal Map

The three roadmap success criteria are **evidence-bearing** — SC1 and SC2 require measured artifacts, not prose. Prose alone fails these.

| SC | Claim | Observable signal | Evidence artifact |
|----|-------|-------------------|-------------------|
| SC1 | Loop closes hands-off on live Docker | `POST /designstate/capture` returns; with no further human action a `:ValidationRun` transitions `captured` → completed, carrying `trigger:'auto'` and `verdictSource:'shacl'` (D-07) | Recorded capture→run latency (ms), read from row timestamps; test asserts no manual VALIDATOR trigger occurred |
| SC2 | Rapid captures do not flood | N captures inside the debounce window yield exactly 1 completed run; the other N-1 rows carry `status:'superseded'` (D-14) | Measured **collapse ratio** (N in → 1 out) and **runs-per-minute** under a burst. Structural guarantee also holds: auto-runs are persist-only by default (D-09), so Speckle noise is 0 unless explicitly opted in |
| SC3 | ADR records choice, rejections, scope | File exists in `DG_OBSIDIAN/knowledge/decisions/` with the required sections | Section-presence check automatable; soundness is manual (see table above) |

---

## Validation Sign-Off

- [x] All tasks have `<automated>` verify or Wave 0 dependencies — 10 of 11 tasks carry an automated command; the single exception is the blocking human checkpoint 39-04-T2, whose automatable half is fully covered by 39-04-T1
- [x] Sampling continuity: no 3 consecutive tasks without automated verify
- [x] Wave 0 covers all MISSING references — every ❌ row above names the task that creates the file
- [x] No watch-mode flags
- [x] Feedback latency < 90s — host-tier modules run in seconds; the two live modules run inside the documented 60–90s in-container envelope
- [x] SC1 and SC2 evidence artifacts are produced as **measured numbers**, not descriptions — `39-EVIDENCE.json` is machine-written by 39-03-T1 and mechanically re-checked by 39-03-T2 and 39-05-T1
- [x] `nyquist_compliant: true` set in frontmatter

**Approval:** planner-complete 2026-07-27 — execution pending. Table rows flip from ⬜ to ✅ as `/gsd-execute-phase 39` lands each task.
