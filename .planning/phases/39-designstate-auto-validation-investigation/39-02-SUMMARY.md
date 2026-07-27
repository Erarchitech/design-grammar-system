---
phase: 39-designstate-auto-validation-investigation
plan: 02
subsystem: api
tags: [fastapi, lifespan, neo4j, speckle, auth, threading, python]

requires:
  - "39-01 (dsav_watcher.py: capture_state, poll_once, start_watcher/stop_watcher)"
provides:
  - "POST /designstate/capture — the phase's only new public surface: connector-token auth (P-01), strict project binding (T-39-02), UTF-8 payload cap (T-39-07), 202 + minted runId"
  - "FastAPI lifespan starting/stopping the watcher daemon with _call_shacl_validate and _auto_publish_run injected — breaking the app<->watcher import cycle at the call site"
  - "_auto_publish_run + AUTO_COMPLETE_PUBLISH_QUERY — best-effort, completion-first Speckle publish (P-07) that never touches store_validation_run"
  - "test_designstate_capture.py — 22-test host-tier suite incl. the D-10 pinned source-hash guard and the lifespan import-safety guard"
affects: ["39-03 (live-Docker verification)", "39-04", "39-05 (DSAV-03 ADR)"]

tech-stack:
  added: []
  patterns:
    - "Inline Bearer-token auth at the route (connector_heartbeat precedent) rather than a Depends() wrapper — the security-relevant half (project binding) is necessarily route-local"
    - "Callable injection through lifespan: app.py passes _call_shacl_validate/_auto_publish_run into start_watcher, so dsav_watcher never imports app"
    - "Pinned-source-hash regression guard (sha256 over inspect.getsource) as an executable no-touch contract for a function a phase must not modify"

key-files:
  created:
    - data-service/tests/test_designstate_capture.py
  modified:
    - data-service/app.py

key-decisions:
  - "ensure_spec_indexes was migrated off the deprecated startup-event decorator into the new lifespan — Starlette runs on_startup handlers ONLY through its default lifespan, so supplying lifespan= would have silently disabled it (empirically verified, not assumed)"
  - "_auto_publish_run's valid_status parameter carries a default because dsav_watcher.poll_once invokes publish_fn(project, run_id) with exactly two positional arguments; the plan's 3-required-arg signature would have TypeError'd on every auto-publish"
  - "Docstrings/comments in app.py avoid the literal strings 'connectors.authenticate_token', 'connectors.record_heartbeat' and '@app.on_event' so the plan's exact-count acceptance greps measure code, not prose"

requirements-completed: [DSAV-02]

coverage:
  - id: D1
    description: "POST /designstate/capture with no Authorization header returns 401 and writes nothing"
    requirement: "DSAV-02"
    verification:
      - kind: unit
        ref: "data-service/tests/test_designstate_capture.py#test_missing_header_returns_401_auth_failed"
        status: pass
    human_judgment: false
  - id: D2
    description: "The full T-39-01 rejection matrix (non-Bearer, wrong prefix, unknown token, revoked credential) returns 401 and reaches the writer zero times"
    requirement: "DSAV-02"
    verification:
      - kind: unit
        ref: "data-service/tests/test_designstate_capture.py#test_revoked_credential_token_returns_401_auth_failed"
        status: pass
      - kind: unit
        ref: "data-service/tests/test_designstate_capture.py#test_unknown_token_returns_401_auth_failed"
        status: pass
    human_judgment: false
  - id: D3
    description: "A token bound to project A with a body naming project B returns 403 and writes nothing (T-39-02), and the body names neither project (T-39-06)"
    requirement: "DSAV-02"
    verification:
      - kind: unit
        ref: "data-service/tests/test_designstate_capture.py#test_project_mismatch_returns_403_and_writes_nothing"
        status: pass
      - kind: unit
        ref: "data-service/tests/test_designstate_capture.py#test_project_mismatch_response_leaks_no_project_names"
        status: pass
    human_judgment: false
  - id: D4
    description: "A valid project-matched token returns 202 with a 32-char hex runId and delegates exactly one capture_state call carrying the right project/runId/payload"
    requirement: "DSAV-02"
    verification:
      - kind: unit
        ref: "data-service/tests/test_designstate_capture.py#test_matching_project_returns_202_accepted_and_records_one_capture"
        status: pass
    human_judgment: false
  - id: D5
    description: "The watcher thread starts at app startup and stops on shutdown; importing app in an existing test module does not start it"
    requirement: "DSAV-02"
    verification:
      - kind: unit
        ref: "data-service/tests/test_designstate_capture.py#test_lifespan_starts_and_stops_watcher_thread_injecting_both_callables"
        status: pass
      - kind: unit
        ref: "data-service/tests/test_designstate_capture.py#test_lifespan_import_does_not_start_watcher_thread"
        status: pass
    human_judgment: false
  - id: D6
    description: "store_validation_run is byte-for-byte unchanged (D-10), proven by a pinned source hash"
    requirement: "DSAV-02"
    verification:
      - kind: unit
        ref: "data-service/tests/test_designstate_capture.py#test_store_validation_run_source_hash_is_pinned"
        status: pass
    human_judgment: false
  - id: D7
    description: "_auto_publish_run skips without raising when Speckle config/token are absent, never reaches _auto_configure_integration (D-13), and never calls store_validation_run"
    requirement: "DSAV-02"
    verification:
      - kind: unit
        ref: "data-service/tests/test_designstate_capture.py#test_auto_publish_run_skips_when_speckle_config_missing"
        status: pass
      - kind: unit
        ref: "data-service/tests/test_designstate_capture.py#test_auto_publish_run_returns_error_result_and_never_raises"
        status: pass
    human_judgment: false
  - id: D8
    description: "Live-Docker proof that the capture route and the lifespan-started watcher actually close the loop against real Neo4j and a real dg-reasoner sidecar"
    verification: []
    human_judgment: true
    rationale: "This plan is host-tier only: every Neo4j write is replaced by a recorder and every Speckle call is monkeypatched. Live execution is Plan 03's explicit scope."

duration: ~45min
completed: 2026-07-27
status: complete
---

# Phase 39 Plan 02: Capture Endpoint + Watcher Wiring Summary

**`POST /designstate/capture` now authenticates a connector token, enforces strict project binding, caps the payload and delegates its single write to the Wave 1 watcher — which the app's first-ever FastAPI `lifespan` starts and stops with injected SHACL and best-effort publish callables.**

## Performance

- **Duration:** ~45 min
- **Completed:** 2026-07-27
- **Tasks:** 3 completed
- **Files modified:** 2 (1 new, 1 modified)

## Accomplishments

- **`POST /designstate/capture`** — inline Bearer extraction resolved through `authenticate_token` (P-01, deliberately not `record_heartbeat`), strict equality between the credential's bound project and the body project (T-39-02), a generic 403 that leaks neither project name (T-39-06), a 1 MiB `DSAV_MAX_STATE_PAYLOAD_BYTES` UTF-8 cap returning 413 (T-39-07), a required non-empty `statePayloadJson` (422), and a 202 carrying a freshly minted 32-char hex `runId`. The single Neo4j write is delegated to `dsav_watcher.capture_state()`; no Cypher for this path lives in `app.py`.
- **First `lifespan` in `data-service`** — replaces the bare `FastAPI()`; starts the watcher with `shacl_fn=_call_shacl_validate` and `publish_fn=_auto_publish_run` (so `dsav_watcher` never imports `app` — the cycle is broken at the call site), and stops it with a bounded join. Both halves are guarded so a watcher that cannot start never stops the service from serving (T-39-08).
- **`_auto_publish_run` + `AUTO_COMPLETE_PUBLISH_QUERY`** — P-07's inverted ordering: complete and persist first, publish second, publish failure non-fatal. Skips cleanly on missing Speckle config or write token, never falls through to the implicit-create helper (D-13), SETs the same field names `store_validation_run` writes in place so `list_validation_runs`/`build_view_payload` read an auto-published run identically to a manual one, and never raises.
- **22-test host-tier suite** (plan required ≥11), including the D-10 pinned source-hash guard and the Pitfall-3 import-safety guard.
- Full suite: **698 passed, 4 failed, 25 errors** — exactly the documented baseline (the four `test_dg_context.py` and the 25 `neo4j`-DNS integration errors), confirming the new lifespan did not disturb the ~30 modules that build `TestClient(app)` at import time.

## Task Commits

1. **Task 1 (RED): failing auth-matrix suite** — `16a514a` (test)
2. **Task 1 (GREEN): POST /designstate/capture** — `c24dc7c` (feat)
3. **Task 2 (RED): failing lifespan + publish adapter tests** — `a6f4976` (test)
4. **Task 2 (GREEN): lifespan wiring + auto-publish adapter** — `7833b03` (feat)
5. **Task 3: D-10 pinned source-hash guard** — `2caae3a` (test)

_Plan metadata commit follows below._

## Files Created/Modified

- `data-service/app.py` — `lifespan`, `DesignStateCaptureRequest`/`DesignStateCaptureResponse`, `capture_design_state`, `_auto_publish_run`, `AUTO_COMPLETE_PUBLISH_QUERY`, `DSAV_MAX_STATE_PAYLOAD_BYTES`, plus the `ensure_spec_indexes` decorator migration
- `data-service/tests/test_designstate_capture.py` — 22-test host-tier suite

## Decisions Made

- **`ensure_spec_indexes` migrated into the lifespan.** See the deviation below — this was a correctness requirement, not a preference.
- **`_auto_publish_run(project, run_id, valid_status=None)`.** The plan specified three required parameters, but `poll_once` calls `publish_fn(project, kept_run_id)` with two positionals. `valid_status` is accepted-but-unused (the verdict is already durably on the run when publish is reached) and defaulted, with an arity-contract regression test.
- **Prose in `app.py` avoids the literal strings the plan greps for** (`connectors.authenticate_token`, `connectors.record_heartbeat`, `@app.on_event`). The plan's acceptance criteria assert exact occurrence counts; docstrings referencing those symbols inflated them to 2, 2 and 3 respectively. Reworded to "the connectors module's `authenticate_token`" / "startup-event decorator", preserving the explanation while letting the greps measure code.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] `ensure_spec_indexes` migrated off the deprecated startup-event decorator into the lifespan**

- **Found during:** Task 2 (RED run surfaced a `DeprecationWarning` from `app.py:881`)
- **Issue:** The plan states "there was no `on_event`, `lifespan` or `threading` usage in this file before Phase 39" and sets an acceptance criterion of `grep -c "@app.on_event" == 0`. In fact `app.py:881` already carried `@app.on_event("startup")` on `ensure_spec_indexes` (SpecGraph fulltext index + `SpecClass` hub nodes + backfill + `init_ollama_models()`). Starlette installs its default lifespan — the one that runs `on_startup` handlers — **only when no `lifespan=` is passed**; supplying one replaces that default outright and registered startup handlers are then silently never invoked. Adding the lifespan as written would therefore have quietly disabled the SpecGraph index bootstrap and Ollama model seeding in production, with no error anywhere.
- **Verified, not assumed:** reproduced standalone — a `FastAPI(lifespan=...)` app with an `@app.on_event('startup')` handler fires only the lifespan (`fired = ['lifespan']`).
- **Fix:** removed the decorator and call `ensure_spec_indexes()` explicitly as the first statement of the lifespan, unguarded, preserving the previous startup moment and failure semantics exactly. This also satisfies the plan's own `== 0` criterion literally.
- **Files modified:** `data-service/app.py`
- **Verification:** `test_lifespan_still_runs_ensure_spec_indexes` asserts the hook fires exactly once on lifespan entry.
- **Committed in:** `7833b03`

---

**2. [Rule 1 - Bug] `_auto_publish_run`'s third parameter defaulted to `None`**

- **Found during:** Task 2 (writing the adapter against `dsav_watcher`'s actual call site)
- **Issue:** The plan specifies `_auto_publish_run(project: str, run_id: str, valid_status: list[bool])` with three required parameters, but Wave 1's `poll_once` invokes `publish_fn(project, kept_run_id)` with exactly two positional arguments. Every auto-publish would have raised `TypeError`, been swallowed by `poll_once`'s `except`, and been reported as a generic `publish_errors` increment — a silent, permanently-broken publish leg that would have looked like a Speckle problem during Wave 3 measurement.
- **Fix:** `valid_status: list[bool] | None = None`, documented in the docstring as accepted-but-unused (the verdict is already persisted before publish is reached).
- **Files modified:** `data-service/app.py`
- **Verification:** `test_auto_publish_run_is_callable_with_the_watcher_publish_fn_contract` binds the signature against `(project, run_id)`; every other adapter test calls it with two arguments, as the watcher does.
- **Committed in:** `7833b03`

---

**Total deviations:** 2 auto-fixed (2 bugs)
**Impact on plan:** Both were latent breakages the plan's own text would have introduced — one silently disabling a shipped startup hook, the other silently breaking the publish leg this phase exists to measure. No scope creep: no other function was touched, and the plan's file scope (`git diff --name-only` = exactly `data-service/app.py` and `data-service/tests/test_designstate_capture.py`) holds.

## Issues Encountered

- The plan's acceptance greps assert exact counts on strings that also appear naturally in explanatory prose. Resolved by rewording comments rather than weakening the criteria (see Decisions). Worth noting for future plans: exact-count greps are brittle against documentation.
- `data-service/tests/dsav_fixtures.py` needs `sys.path.insert(0, os.path.dirname(__file__))` to import (the plan's preamble spec, copied from `test_connectors.py`, only inserts the parent directory). Matched `test_dsav_watcher.py`, which inserts both.
- Host `fastapi` is 0.135.1 (the plan cites 0.140.0 in the container). `lifespan` is available and correct in both; no behavioral difference for this change.

## User Setup Required

None for this plan — it is host-tier only. Note for Plan 03: per P-06 there is deliberately **no configuration route**, so enabling auto-validation for a project means calling `dsav_watcher.upsert_auto_validation_config()` out-of-band (from the Wave 3 test driver or a one-off `docker compose exec data-service python -c ...`).

## Next Phase Readiness

- The loop is closed **in code**: a POST produces a `captured` row and the in-process watcher completes it. Plan 03 measures it on live Docker.
- Still unproven and explicitly Plan 03's scope: the eight Cypher constants have never executed against real Neo4j (39-RESEARCH.md A2 remains open); the SHACL sidecar has never been called by the watcher; and no Speckle version has ever been published through `_auto_publish_run`.
- A `docker compose build data-service` (or restart) is required before Plan 03 — the running container still has the pre-lifespan `app.py`.
- No blockers for Plan 03.

---
*Phase: 39-designstate-auto-validation-investigation*
*Completed: 2026-07-27*
