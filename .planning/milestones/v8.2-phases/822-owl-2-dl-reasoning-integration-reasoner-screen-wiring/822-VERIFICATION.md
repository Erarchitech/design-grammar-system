---
phase: 822-owl-2-dl-reasoning-integration-reasoner-screen-wiring
verified: 2026-07-12T00:00:00Z
reverified: 2026-07-13
status: passed
score: 4/4 must-haves verified
behavior_unverified: 0
overrides_applied: 0
gaps: []
reverification_note: >
  2026-07-13 (v8.1/v8.2 gap-closure session): all 3 deferred UAT scenarios executed
  against the live docker stack and PASSED — see 822-UAT.md for full evidence.
  (1) Real kill-on-timeout proven end-to-end: DG_REASONER_TIMEOUT_SECONDS temporarily
  90→1, real HermiT java subprocess launched and killed, route returned 504 within
  ~1.5s of the click, UI rendered the achromatic "Inconclusive" verdict — never
  green/red, never a hang; compose value restored, follow-up run consistent in 1999ms.
  (2) Inconsistent verdict render proven live: 820-spike contradiction temporarily
  seeded into ontology/dg-disjointness.ttl → "Schema inconsistent — 1 unsatisfiable
  class." + Inconsistent badge + human label "SlidingDoor" only (no raw IRI); overlay
  restored, re-run flipped back to Consistent (freshness, criterion 4).
  (3) Full click-through: "Running… 0s" timer + Cancel + disabled Run at t+400ms;
  Cancel mid-flight → distinct "× Run cancelled — no result."; uncancelled run →
  "✓ Schema consistent" + Consistent badge + "Last checked just now".
  One cosmetic defect found and fixed: stale v8.1 "both reasoners are placeholders"
  intro copy in ReasonerScreen.jsx corrected to reflect the integrated HermiT check.
behavior_unverified_items:
  - truth: "Criterion 1 — user clicks Run check and a real HermiT check executes, replacing the v8.1 placeholder"
    test: "In the live UI (http://localhost:8080), open Reasoner screen, click 'Run check' on the HermiT card"
    expected: "Spinner + elapsed-seconds counter appears, Run button disables, then a verdict renders (Consistent, per live curl proof the backend genuinely runs HermiT) with no 'Integration pending' badge on HermiT"
    why_human: "No frontend test framework exists in ui-v2 (confirmed — no jest/vitest config, no *.test.jsx files); the Plan 04 manual click-through (Step A) was explicitly skipped per user decision. Backend real-HermiT execution is proven live (curl), but the actual browser click → render sequence has never been observed."
  - truth: "Criterion 2 — Inconsistent verdict shows unsatisfiable-class count + human-labeled list, framed as 'schema consistency'"
    test: "Force an inconsistent ontology fixture (e.g. add a disjoint-class violation to a test project) and click Run check; observe the rendered 'Schema inconsistent — N unsatisfiable classes.' block and its bulleted label list"
    expected: "Signal-red badge 'Inconsistent', correct singular/plural count, each list item shows entry.label only (never a raw IRI)"
    why_human: "The live stack's only exercised project (v8-ui-smoke) is currently consistent — the Inconsistent render branch was never observed live or manually (Plan 04 Step B was skipped, and no inconsistent fixture was run against the real UI). Unit-level shape tests (test_unsatisfiable_classes_have_iri_and_label) prove the API contract but not that ReasonerScreen actually renders it correctly on screen."
  - truth: "Criterion 3 (most safety-critical) — a long-running/hung reasoning call times out and returns a distinct Unknown result rather than silently reporting pass/fail, and never blocks the calling request synchronously"
    test: "Lower DG_REASONER_TIMEOUT_SECONDS to a small value (e.g. 1s) on a project large enough that HermiT actually runs past it, or otherwise force a real hang, then click Run check and confirm the request returns within the bounded window with an Unknown/Inconclusive verdict"
    expected: "The dg-reasoner subprocess is actually killed via os.killpg after the timeout elapses, run_consistency returns {consistent:None, error:'timeout',...}, the data-service proxy passes it through as 504 with no detail wrapper, and the UI renders the achromatic 'Inconclusive' verdict — never green/red, never a hang"
    why_human: "Zero test at any tier (unit, integration, or manual) exercises the REAL subprocess-kill timeout path end-to-end. dg-reasoner/tests/test_routes.py's timeout test monkeypatches reasoning.run_consistency's return value directly — it never calls _reason_with_timeout or triggers an actual process join/kill. The one live integration test (test_run_consistency_completes_without_error) explicitly asserts result.get('error') != 'timeout' — it is a happy-path proof, not a timeout proof. Plan 04's Step C (the one check designed to exercise this exact mechanism) was explicitly skipped per user decision. This is the highest-risk gap: the phase's central trust claim (\"a hung reasoner is an honest Unknown, never a silent pass/fail, never a block\") has never been demonstrated to actually work, only to be theoretically correctly coded."
human_verification:
  - test: "Click Run check on HermiT card in the live UI and observe the full run → verdict cycle"
    expected: "Spinner+timer, disabled Run button during run, then a rendered Consistent verdict with the framing disclaimer and Last-checked timestamp, no 'Integration pending' badge on HermiT"
    why_human: "No frontend test infra; manual click-through (Plan 04 Step A) was skipped"
  - test: "Force an inconsistent fixture and observe the Inconsistent verdict rendering (count + label list, signal badge)"
    expected: "'Schema inconsistent — N unsatisfiable classes.' with correct pluralization and a bulleted list of entry.label values only"
    why_human: "No inconsistent fixture has ever been run through the live UI or the real HermiT pipeline; only unit-level monkeypatched shape tests exist (Plan 04 Step B skipped)"
  - test: "Force a real reasoner hang (lowered DG_REASONER_TIMEOUT_SECONDS against a slow/large project, or a stub that sleeps past the bound) and confirm the UI shows Inconclusive without hanging, and Cancel independently aborts cleanly to a distinct Cancelled state"
    expected: "Request returns within the bounded ceiling with an Unknown/Inconclusive verdict (never green/red); a separate Cancel click during a run shows 'Run cancelled' distinct from Inconclusive"
    why_human: "This is the phase's single most safety-critical claim and has zero automated or manual proof of the real kill-on-timeout mechanism firing end-to-end (Plan 04 Step C was skipped, and no test anywhere exercises _reason_with_timeout's actual process-group kill path)"
---

# Phase 822: OWL 2 DL Reasoning Integration — Reasoner Screen Wiring Verification Report

**Phase Goal:** Users can run a real OWL 2 DL consistency check from the Reasoner screen and trust the result, replacing the v8.1 placeholder.
**Verified:** 2026-07-12 (initial, backend-only) · **Re-verified:** 2026-07-13 (all 3 deferred UAT scenarios passed live — see frontmatter `reverification_note` + 822-UAT.md)
**Status:** passed
**Re-verification:** Yes — 2026-07-13 gap-closure session closed all 3 `human_verification` items below (kept for history)

## Pre-check: Branch Isolation

Confirmed before any other work, per task instructions:

```
git rev-parse --abbrev-ref HEAD
→ gsd/phase-822-owl-2-dl-reasoning-integration-reasoner-screen-wiring

git log --oneline master..HEAD
→ 248d7de docs(822-04): note re-verification after branch isolation
  102deb7 docs(822-04): complete end-to-end verification plan
  f1c6a7a docs(822-03): complete ReasonerScreen HermiT wiring plan
  51d1c98 feat(822-03): render the four verdict states + D-09 error line + Last-checked
  ce675f2 feat(822-03): add ReasonerScreen run-state machine, Run/Cancel, elapsed timer
  592712a feat(822-03): add runConsistencyCheck to reasonerApi.js
  9a9e674 docs(822-02): add plan summary and update tracking
  593a5a8 feat(822-02): flip HermiT registry status to integrated (D-04)
  ee8eae0 fix(822-02): reconcile reasoner proxy read timeout to sidecar ceiling
  ad48818 test(822-02): add reasoner proxy timeout/error tests + registry-status assertions
  0be366c docs(822-01): add plan summary and update tracking
```

Branch is clean — only 822-0X commits, no 823 (SHACL) commits present. Safe to proceed.

## Goal Achievement

### Observable Truths

| # | Truth (ROADMAP success criterion) | Status | Evidence |
|---|---|---|---|
| 1 | User clicks "Run check" and a real HermiT consistency check executes against the translated OntoGraph, replacing the "integration pending" placeholder | ⚠️ PRESENT_BEHAVIOR_UNVERIFIED | Backend proven live via curl (real HermiT ran, `duration_ms:1528`, real axiom counts from Neo4j project `v8-ui-smoke`). Registry flip confirmed (`GET /reasoner/settings` → HermiT `status:"integrated"`, no placeholder badge). Frontend click→fetch→render wiring read and matches spec exactly in `ReasonerScreen.jsx`/`reasonerApi.js`. But no frontend test framework exists and Plan 04's manual click-through (Step A) was explicitly skipped — the actual browser interaction has never been observed. |
| 2 | Result displays a clear pass/fail summary with unsatisfiable-class count, labeled "schema consistency" so it's never mistaken for design-compliance | ⚠️ PRESENT_BEHAVIOR_UNVERIFIED | Copy and rendering logic read directly in source: exact strings "Schema consistent —…"/"Schema inconsistent — {N} unsatisfiable class(es)." with framing disclaimer "Schema-consistency check — verifies the ontology's logical structure, not design compliance." above every verdict; `entry.label` rendered, `entry.iri` never rendered (grep confirms no `.iri` in file). Unit test `test_unsatisfiable_classes_have_iri_and_label` proves the API shape. However, the live-only fixture (`v8-ui-smoke`) is currently consistent, so the Inconsistent render branch has never been exercised live or manually (Plan 04 Step B skipped). |
| 3 | A long-running or hung reasoning call times out and returns a distinct "unknown" result rather than silently reporting pass or fail, and never blocks the calling request synchronously | ⚠️ PRESENT_BEHAVIOR_UNVERIFIED (highest risk) | Code exists and is well-documented: `dg-reasoner/reasoning.py`'s `_reason_with_timeout` uses a `spawn`-context subprocess, `os.setsid()`+`os.killpg()` on expiry, hard `process.join(timeout_seconds)`. `data-service/app.py`'s proxy read-timeout is reconciled to track the sidecar's ceiling (verified: `read=float(os.getenv("DG_REASONER_TIMEOUT_SECONDS","90"))+10`, `connect=2.0`). BUT: no test at any tier — unit, integration, or manual — ever triggers the REAL kill-on-timeout path. `test_reason_consistency_timeout_returns_504` and the data-service proxy timeout tests all monkeypatch the return value directly, never invoking `_reason_with_timeout`'s actual process management. The one live integration test explicitly asserts `result.get("error") != "timeout"` (a happy-path, not a timeout, proof). Plan 04's Step C — the step designed to exercise exactly this — was explicitly skipped per user decision. |
| 4 | Re-running the check after an ontology export change reflects updated results, not a cached/stale answer | ✓ VERIFIED | Verified by code inspection of the full request chain, not by dynamic test — appropriate here because this is an absence-of-caching claim: (a) `ui-v2/src/lib/reasonerApi.js`'s `runConsistencyCheck` issues a fresh `fetch` POST every call, no store/memoization (`grep -nE "Cache-Control|memoize"` returns nothing); (b) `ui-v2/nginx.conf`'s `/reasoner/` location block has no `proxy_cache` directive; (c) `data-service/app.py`'s proxy issues a fresh `httpx.post` every request and returns the sidecar body verbatim via `JSONResponse`, no caching; (d) `dg-reasoner/reasoning.py`'s `run_consistency` calls `_hybrid_union` → `ontology_export.build_graph(session, project)` fresh from Neo4j on every invocation, serializes a new temp NTriples file, and spawns a brand-new subprocess each run — there is no persistent state anywhere in the chain that could serve a stale answer. |

**Score:** 1/4 truths verified (3 present + wired, behavior not exercised)

### Required Artifacts

| Artifact | Expected | Status | Details |
|---|---|---|---|
| `dg-reasoner/reasoning.py` | `_local_name` helper + `{iri,label}` enrichment in `_reason_worker` | ✓ VERIFIED | Read directly (L127-140, L160-172); matches plan exactly; `owl#Nothing` excluded, dedup+sort by iri, label falls back to `_local_name` when `.label` empty |
| `dg-reasoner/tests/test_routes.py` | label-shape + fallback assertions | ✓ VERIFIED | `test_local_name_fallback`, `test_unsatisfiable_classes_have_iri_and_label` present and pass |
| `data-service/app.py` | proxy read-timeout reconciled to sidecar ceiling | ✓ VERIFIED | L1190-1195: `read=float(os.getenv("DG_REASONER_TIMEOUT_SECONDS","90"))+10`, `connect=2.0` |
| `data-service/reasoner.py` | HermiT status flipped to `integrated` | ✓ VERIFIED | L20-33: HermiT `"integrated"`, Pellet `"placeholder"` — confirmed live via `GET /reasoner/settings` |
| `data-service/tests/test_reasoner.py` | proxy timeout/connect/pass-through tests + registry-status assertions | ✓ VERIFIED | `TestReasonerConsistencyProxy` (4 tests) + `test_hermit_status_is_integrated` present, all pass |
| `ui-v2/src/lib/reasonerApi.js` | `runConsistencyCheck(project,{signal})` | ✓ VERIFIED | L33-42: no-throw, returns `{ok,status,body}`, forces `engine:"hermit"`, forwards `signal`, no caching |
| `ui-v2/src/screens/ReasonerScreen.jsx` | run-state machine, Run/Cancel, four verdict regions, D-09 error line, Last-checked, phantom-token fix | ✓ VERIFIED (source-level) | Full state machine present (L42-139), all four verdict branches + error line render with correct copy/tokens (L320-597); `--color-accent`/`--surface-focus` phantom tokens absent (grep confirms); real click-through unobserved (see Human Verification) |

### Key Link Verification

| From | To | Via | Status | Details |
|---|---|---|---|---|
| `reasoning._reason_worker` | in-memory owlready2 `.label` | direct attribute read, no new Neo4j round-trip | ✓ WIRED | Confirmed by code read; label read happens inside the same reasoning subprocess |
| `data-service/app.py` proxy | `dg-reasoner` sidecar | `httpx.post` verbatim body/status pass-through | ✓ WIRED | Confirmed live: curl to data-service returns the sidecar's exact D-10 envelope |
| `ui-v2/reasonerApi.js` | `data-service /reasoner/consistency` | `fetch` POST via nginx `/reasoner/` proxy | ✓ WIRED | nginx block has no cache directive; confirmed proxy_pass to `data-service:8000` |
| `ReasonerScreen.handleRunCheck` | `runConsistencyCheck` | body-shape branch (`error==="timeout" && "consistent" in body` → unknown; `!ok` → error; else consistent/inconsistent) | ✓ WIRED | Exact branch logic confirmed in source (L108-122), matches RESEARCH Pitfall 1 exactly |

### Behavioral Spot-Checks / Automated Suites (independently re-run by verifier)

| Behavior | Command | Result | Status |
|---|---|---|---|
| dg-reasoner full suite (incl. live HermiT round-trip against real Neo4j) | `docker exec dg-reasoner python -m pytest tests -x` | 19 passed in 1.96s | ✓ PASS |
| data-service reasoner suite | `python -m pytest data-service/tests/test_reasoner.py -x` | 13 passed, 2 warnings in 1.20s | ✓ PASS |
| Live consistency check against real stack | `curl -X POST localhost:8000/reasoner/consistency -d '{"project":"v8-ui-smoke","engine":"hermit"}'` | `{"consistent":true,"unsatisfiable_classes":[],"axiom_counts":{...89 classes...},"duration_ms":1528,"stripped_builtin_rules":5}` | ✓ PASS — real HermiT execution confirmed (non-trivial duration, real axiom counts) |
| Live registry status | `curl localhost:8000/reasoner/settings` | HermiT `status:"integrated"`, Pellet `status:"placeholder"`, `selected:"hermit"` | ✓ PASS |
| No real-timeout / kill-path test exists anywhere | `grep -rn "_reason_with_timeout\|killpg" dg-reasoner/tests/` | no matches | ⚠️ GAP — see Truth 3 |

Note: all three containers (`dg-reasoner`, `data-service`, `design-grammars`) were confirmed `Up` and running current 822 code at verification time (rebuilt per 822-04-SUMMARY.md's documented `--no-cache` rebuild).

### Requirements Coverage

| Requirement | Source Plan | Description | Status | Evidence |
|---|---|---|---|---|
| REAS-06 | 822-01, 822-02, 822-03, 822-04 | User runs an OWL 2 DL consistency check from the Reasoner screen (HermiT default) and sees a pass/fail summary with unsatisfiable-class count, replacing the placeholder | Partially satisfied — backend fully proven, frontend correctly wired at source level, but the three most user-facing/safety-critical behaviors (real click-through, Inconsistent render, real-timeout handling) have no automated or manual behavioral proof | See Observable Truths 1-3 above |

No orphaned requirements — REQUIREMENTS.md maps only REAS-06 to Phase 822, and all four plans declare it.

### Anti-Patterns Found

None. Scanned all phase-touched files (`dg-reasoner/reasoning.py`, `data-service/app.py`, `data-service/reasoner.py`, `ui-v2/src/lib/reasonerApi.js`, `ui-v2/src/screens/ReasonerScreen.jsx`) for `TBD`/`FIXME`/`XXX`/`TODO`/`HACK`/`PLACEHOLDER`/stub patterns — no matches beyond the intentional, correctly-scoped "placeholder" product terminology for Pellet's status (which is the deliberate, documented D-04/D-06 design, not a code debt marker).

### Human Verification Required

Three items — all routed here because the phase's frontend has no test framework and Plan 04's manual UAT (Steps A-G) was explicitly skipped per an already-documented user decision. Listed in priority order:

#### 1. Real timeout → Unknown, never blocks (criterion 3 — highest priority)

**Test:** Force a genuine reasoner hang — either lower `DG_REASONER_TIMEOUT_SECONDS` to a value shorter than a real HermiT run against a non-trivial project, or otherwise cause the subprocess to genuinely exceed the bound — then click Run check and time the response.
**Expected:** The request returns at (or shortly after) the bounded ceiling, never hangs indefinitely; the sidecar's subprocess is actually killed (`os.killpg`); the UI shows the achromatic "Inconclusive" verdict, never green/red, never a stuck spinner.
**Why human:** No test at any tier exercises the real kill-on-timeout mechanism (`_reason_with_timeout`'s process management is only ever monkeypatched around, never actually triggered). This is the phase's central trust claim and it has zero behavioral proof.

#### 2. Inconsistent verdict renders correctly in the live UI

**Test:** Run the check against a project/fixture with a genuine unsatisfiable class (or temporarily add a disjoint-class violation to a test project), click Run check, observe the rendered result.
**Expected:** "Schema inconsistent — N unsatisfiable class(es)." with a bulleted list of human labels only (no raw IRI), signal-red badge "Inconsistent".
**Why human:** The live stack's only project (`v8-ui-smoke`) is currently consistent; this render branch has never been observed outside of monkeypatched unit tests.

#### 3. Full click-through of Run/Cancel and the Consistent verdict

**Test:** Click "Run check" on the HermiT card, observe spinner+elapsed timer+disabled Run button during the run, then the "✓ Schema consistent" verdict with badge and "Last checked" timestamp; separately, start a run and click Cancel mid-flight, confirm "× Run cancelled — no result." renders distinctly (not as Unknown) and the Run button re-enables.
**Expected:** Matches UI-SPEC exactly, per the source already read.
**Why human:** No frontend test framework in `ui-v2`; this exact check was Plan 04's Step A/D and was explicitly skipped per user decision.

### Gaps Summary

No FAILED truths — every artifact required by the four plans exists, is substantive, and is correctly wired; all automated backend test suites (dg-reasoner 19/19, data-service reasoner suite 13/13) pass on independent re-run, and live curl checks against the running stack confirm the real HermiT envelope and HermiT's `"integrated"` registry status.

The reason this is **not** a clean `passed` is that three of the four ROADMAP success criteria assert user-observable *behavior* (a click producing a running→verdict transition, an Inconsistent render, and — most importantly — a genuine hung-reasoner-times-out-safely invariant) for which:
- `ui-v2` has no automated frontend test framework, so no test could have exercised these paths even if attempted, and
- the one available substitute (Plan 04's manual UAT, Steps A-G) was explicitly and knowingly skipped by the user's own decision, recorded in `822-04-SUMMARY.md`.

This verification independently confirms that decision was reasonable for the *backend* half of REAS-06 (which is thoroughly proven, live, by a third party — this verifier) but flags that the *user-facing* half of criteria 1-3 — the actual experience described in the phase goal ("users can run a real check ... and **trust the result**") — has never been observed to work, either automatically or manually. Criterion 3 in particular (the hung-reasoner safety guarantee) has literally zero behavioral evidence at any level, unit included — this is worth flagging distinctly from criteria 1/2, which at least have strong backend live-proof plus verbatim-matching frontend source.

**Recommendation:** This is a judgment call for the developer, not an automatic block. If the click-through gap is acceptable given the strength of the backend proof + source-level frontend correctness, this phase can be considered practically shippable with the three items above logged as a fast follow-up UAT pass (e.g. via `/gsd-verify-work 822` against the already-rebuilt live stack, no further code changes needed — only manual clicking). If the user wants stronger proof before shipping (especially for criterion 3's safety claim), the fastest path is exercising Plan 04's Steps A, C, and D against `http://localhost:8080` with the stack already up and current.

---

_Verified: 2026-07-12_
_Verifier: Claude (gsd-verifier)_
