---
phase: 822-owl-2-dl-reasoning-integration-reasoner-screen-wiring
plan: 02
subsystem: api
tags: [fastapi, httpx, data-service, reasoner, timeout, hermit]

# Dependency graph
requires:
  - phase: 821-dg-reasoner-sidecar-ontograph-metagraph-rdf-translation
    provides: "data-service /reasoner/consistency thin proxy (app.py L1173-1210) and the reasoner.py registry (Phase 814)"
  - phase: 822-owl-2-dl-reasoning-integration-reasoner-screen-wiring
    plan: "01"
    provides: "unsatisfiable_classes {iri,label} enrichment forwarded verbatim by this plan's proxy"
provides:
  - "data-service /reasoner/consistency proxy read timeout tracks DG_REASONER_TIMEOUT_SECONDS (default 90) + 10s margin instead of a hardcoded value"
  - "reasoner.REASONER_REGISTRY HermiT entry reports status: 'integrated'; Pellet stays 'placeholder'"
affects: [822-03, 822-04]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Proxy timeout monkeypatch pattern: patch app_module.httpx.post (not the FastAPI app instance) via `import app as app_module` alongside the existing `from app import app` TestClient import, so the two imports coexist without name collision"
    - "Fake sidecar response test double (_FakeSidecarResponse) with .status_code/.json()/.text mirrors real httpx.Response's minimal surface used by the proxy route, avoiding a real network call in tests"

key-files:
  created: []
  modified:
    - data-service/app.py
    - data-service/reasoner.py
    - data-service/tests/test_reasoner.py

key-decisions:
  - "Proxy read timeout expression: float(os.getenv('DG_REASONER_TIMEOUT_SECONDS', '90')) + 10 — tracks the sidecar's actual configured ceiling (not a hardcoded number) so a future env-var change to the sidecar's timeout automatically keeps the proxy's read timeout ahead of it"
  - "connect/write/pool timeouts left untouched at 2.0s — an unreachable sidecar still fails fast per the plan's prohibition"
  - "HermiT flipped to 'integrated', Pellet left at 'placeholder' — matches D-04 (HermiT is the one live/run-able engine this phase; Pellet integration is explicitly out of scope per 822-CONTEXT deferred ideas)"

patterns-established:
  - "Env-driven timeout reconciliation as the standard fix for proxy/sidecar timeout-ceiling drift — reusable if a future sidecar timeout knob changes again"

requirements-completed: [REAS-06]

coverage:
  - id: D1
    description: "Proxy read timeout tracks DG_REASONER_TIMEOUT_SECONDS + margin; connect stays 2.0s fast-fail"
    requirement: "REAS-06"
    verification:
      - kind: unit
        ref: "data-service/tests/test_reasoner.py::TestReasonerConsistencyProxy::test_reasoner_consistency_proxy_read_timeout_tracks_sidecar"
        status: pass
    human_judgment: false
  - id: D2
    description: "Data-service transport timeout returns 504 detail.code=REASONER_TIMEOUT with no top-level consistent key (distinct from D-08 semantic timeout)"
    requirement: "REAS-06"
    verification:
      - kind: unit
        ref: "data-service/tests/test_reasoner.py::TestReasonerConsistencyProxy::test_reasoner_consistency_timeout_returns_504_structured"
        status: pass
    human_judgment: false
  - id: D3
    description: "Connect failure returns 502 detail.code=REASONER_UNAVAILABLE"
    requirement: "REAS-06"
    verification:
      - kind: unit
        ref: "data-service/tests/test_reasoner.py::TestReasonerConsistencyProxy::test_reasoner_consistency_connect_error_returns_502"
        status: pass
    human_judgment: false
  - id: D4
    description: "Genuine sidecar semantic-timeout body (consistent:null, error:timeout) passes through verbatim with 504 status, no detail wrapper"
    requirement: "REAS-06"
    verification:
      - kind: unit
        ref: "data-service/tests/test_reasoner.py::TestReasonerConsistencyProxy::test_reasoner_consistency_passes_through_sidecar_timeout_body"
        status: pass
    human_judgment: false
  - id: D5
    description: "HermiT registry status is integrated; Pellet stays placeholder"
    requirement: "REAS-06"
    verification:
      - kind: unit
        ref: "data-service/tests/test_reasoner.py::TestRegistry::test_hermit_status_is_integrated"
        status: pass
    human_judgment: false

# Metrics
duration: 12min
completed: 2026-07-12
status: complete
---

# Phase 822 Plan 02: Reasoner Proxy Timeout Reconciliation + HermiT Status Integration Summary

**Reconciled the data-service `/reasoner/consistency` proxy read timeout to track the sidecar's `DG_REASONER_TIMEOUT_SECONDS` ceiling (env-driven, +10s margin, connect stays 2.0s fast-fail) and flipped HermiT's registry status to `integrated` while Pellet stays `placeholder`.**

## Performance

- **Duration:** ~12 min
- **Started:** 2026-07-12 (session start)
- **Completed:** 2026-07-12
- **Tasks:** 3
- **Files modified:** 3

## Accomplishments

- `data-service/tests/test_reasoner.py` gained a `TestReasonerConsistencyProxy` class with four tests covering: the timeout-value tracking assertion, the transport-timeout→504 structured-error shape, the connect-error→502 shape, and verbatim pass-through of a genuine sidecar semantic-timeout body — each shape-distinguishing D-08 (Unknown) from D-09 (hard error) per the plan's must-have.
- `test_registry_each_has_required_fields` now accepts `status` in `{"placeholder", "integrated"}` instead of requiring `"placeholder"` for every entry; a new `test_hermit_status_is_integrated` asserts HermiT is `"integrated"` and Pellet is `"placeholder"`.
- `data-service/app.py`'s `post_reasoner_consistency` route now computes its `httpx.Timeout` read value as `float(os.getenv("DG_REASONER_TIMEOUT_SECONDS", "90")) + 10` instead of a hardcoded literal, so it automatically tracks the sidecar's actual configured ceiling. `connect=2.0`, `write=2.0`, `pool=2.0` are unchanged. No other route logic (exception handling, body/status pass-through) was touched.
- `data-service/reasoner.py`'s `REASONER_REGISTRY` HermiT entry's `status` field is now `"integrated"`; the Pellet entry is untouched at `"placeholder"`.
- Full `data-service` test suite: 95/95 passing, no collateral regression.

## Task Commits

Each task was committed atomically:

1. **Task 1: Wave 0 — proxy timeout/error tests + registry-status assertions** - `ad48818` (test)
2. **Task 2: Reconcile proxy read timeout to the sidecar ceiling (keep connect fast)** - `ee8eae0` (fix)
3. **Task 3: Flip HermiT registry status to "integrated" (D-04)** - `593a5a8` (feat)

**Plan metadata:** pending (this commit)

## Files Created/Modified

- `data-service/tests/test_reasoner.py` — added `import httpx` and `import app as app_module`; added `TestReasonerConsistencyProxy` (4 tests) + `_FakeSidecarResponse` test double; added `test_hermit_status_is_integrated`; relaxed `test_registry_each_has_required_fields`
- `data-service/app.py` — `post_reasoner_consistency`'s `httpx.Timeout(...)` read value now derives from `DG_REASONER_TIMEOUT_SECONDS` (default `"90"`) + 10s margin instead of a hardcoded `95.0`
- `data-service/reasoner.py` — HermiT registry entry `status: "placeholder"` → `status: "integrated"`; Pellet entry unchanged

## Decisions Made

- Proxy read-timeout expression uses `float(os.getenv("DG_REASONER_TIMEOUT_SECONDS", "90")) + 10` rather than a fixed number — this makes the read timeout self-correcting if the sidecar's own timeout env var is ever tuned, closing the drift risk the plan's objective called out (RESEARCH Pitfall 2).
- `connect=2.0` (and `write`/`pool`) left untouched — an unreachable sidecar must still fail fast; only `read` (which bounds a genuinely in-progress reasoning call) needed to track the sidecar's ceiling.
- HermiT flips to `"integrated"`; Pellet intentionally stays `"placeholder"` — per D-04/D-06, Pellet integration is out of this phase's scope.

## Deviations from Plan

### Pre-existing partial fix discovered (not a Rule 1-4 deviation — documented for traceability)

The plan's objective text stated the proxy "currently uses a 5s read timeout (app.py L1186)". On inspection, `app.py` already carried a hardcoded `read=95.0` (not `5.0`) — a partial fix landed in the prior phase's code-review commit (`f45ec8e fix(821): address 8 code-review findings`, which is *before* this plan's premise was written). The hardcoded `95.0` happened to satisfy Task 1's `read >= 90` assertion out of the gate, meaning `test_reasoner_consistency_proxy_read_timeout_tracks_sidecar` was unexpectedly GREEN immediately after Task 1 (rather than RED as the plan's acceptance criteria anticipated). This did not change the plan's intent or scope: Task 2 still needed to happen (the value was hardcoded, not env-driven, so it wouldn't track a future change to `DG_REASONER_TIMEOUT_SECONDS`) and was executed exactly as specified. No checkpoint or user decision was needed — this is a Rule 1 "fix reflects current, more-accurate code state" situation, not an architectural change.

No other deviations. Tasks 2 and 3 matched their `<action>` and `<acceptance_criteria>` blocks exactly.

## Issues Encountered

None. All three tasks passed verification on the first attempt after implementation. Full `pytest data-service/tests -q` (95 tests) green with zero collateral regressions.

## User Setup Required

None — no external service configuration required. No packages added (confirmed no-op per the plan's threat register T-822-SC).

Note: `data-service`'s Docker image is built from source (`build: ./data-service` in `docker-compose.yml`, no source volume mount) — the running `data-service` container (verified up, 2h uptime) has NOT been rebuilt to pick up this plan's `app.py`/`reasoner.py` changes. The plan's `<verification>` "Manual sanity (stack up)" step was not exercised live in this plan; it requires `docker compose build --no-cache data-service && docker compose up -d data-service` first. Automated pytest coverage (13/13 reasoner tests, 95/95 full suite) is the verification basis for this plan's completion; live/manual sanity is deferred to whichever later plan next needs the rebuilt stack (Plan 03/04, per the established 821-04 pattern of rebuilding mid-phase before live verification).

## Next Phase Readiness

- Plan 03 (reasoner screen wiring) can now safely assume: (a) the proxy will not misreport a slow-but-valid HermiT run as a transport timeout as the rule corpus grows, and (b) the two 504 body shapes (D-08 semantic timeout vs. D-09 transport timeout) remain distinguishable exactly as RESEARCH.md specified, so the frontend's body-shape branching logic can be implemented with confidence.
- Plan 03/04 will need a `docker compose build --no-cache data-service` (and likely `design-grammars` for the UI half) before any live/manual E2E verification against the running stack — the container has not been rebuilt since this plan's code changes landed.
- No blockers for Plans 03–04.

---
*Phase: 822-owl-2-dl-reasoning-integration-reasoner-screen-wiring*
*Completed: 2026-07-12*

## Self-Check: PASSED

- FOUND: data-service/app.py
- FOUND: data-service/reasoner.py
- FOUND: data-service/tests/test_reasoner.py
- FOUND: ad48818 (test commit)
- FOUND: ee8eae0 (fix commit)
- FOUND: 593a5a8 (feat commit)
