---
phase: 39
slug: designstate-auto-validation-investigation
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-07-27
---

# Phase 39 — Validation Strategy

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
| *(populated by the planner — one row per task)* | | | | | | | | | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

**Planner contract for this table:** every task that touches `POST /designstate/capture` MUST carry a non-empty Threat Ref — the capture endpoint is a new unauthenticated write-amplifier and is the highest-severity item in this phase's threat model (39-CONTEXT.md § Open for the planner). Security enforcement is active at ASVS L1, block-on-`high`.

---

## Wave 0 Requirements

- [ ] `data-service/tests/` — new test module for the watcher's pure poll function, following the `FixtureSession` duck-type pattern in `tests/test_dg_context.py` (no mocking library)
- [ ] Isolated fixture project string — per the Phase 37-01 convention (`FIXTURE_PROJECT`), any test publishing into live Neo4j must scope itself to a project string no other suite uses. Pick one for Phase 39 and pin it.
- [ ] No framework install needed — pytest already present in the data-service image

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

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 90s
- [ ] SC1 and SC2 evidence artifacts are produced as **measured numbers**, not descriptions
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
