---
phase: 814-reasoner-screen
plan: "814-01"
subsystem: api, ui
tags: reasoner, hermit, pellet, settings, placeholder

requires:
  - phase: 812-connector-screen
    provides: data-service endpoint + JSON persistence pattern
  - phase: 810-ai-engine-screen-connectors-shell
    provides: ReasonerScreen skeleton component

provides:
  - Reasoner registry (HermiT, Pellet) with placeholder status
  - GET/PUT /reasoner/settings endpoints with structured error responses
  - Selectable reasoner cards UI persisted across sessions

affects:
  - Future reasoner integration plan (real reasoner wiring)
  - Validation Graph settings consolidation

tech-stack:
  added: []
  patterns:
    - JSON-file persistence under `data/` matching connectors.py pattern
    - FastAPI endpoint pattern with structured errors from _structured_error_response
    - Card-based selection UI following AiEngineScreen layout conventions

key-files:
  created:
    - data-service/reasoner.py
    - data-service/tests/test_reasoner.py
    - ui-v2/src/lib/reasonerApi.js
  modified:
    - data-service/app.py
    - ui-v2/src/screens/ReasonerScreen.jsx

key-decisions:
  - "Reasoner settings stored as plain JSON (no encryption needed — no secrets)"
  - "Registry structured with explicit status field for future integrated/non-placeholder reasoners"
  - "422 for unknown reasoner (not 400) — follows FastAPI validation idiom"

patterns-established:
  - "Card-based selector with active border treatment + Badge for state annotation"

requirements-completed: [REAS-01, REAS-02, REAS-03]

duration: 9min
completed: 2026-07-11
status: complete
---

# Phase 814 Plan 01: Reasoner Screen Summary

**HermiT/Pellet placeholder reasoner selector with JSON-file persistence, selectable cards UI, and "integration pending" annotation**

## Performance

- **Duration:** 9 min
- **Started:** 2026-07-11T10:34:00Z
- **Completed:** 2026-07-11T10:43:38Z
- **Tasks:** 3
- **Files modified:** 5

## Accomplishments

- Created `data-service/reasoner.py` with registry (HermiT, Pellet) and JSON-file persistence — reasoners carry explicit `status: "placeholder"` for future integrated reasoners
- Added `GET /reasoner/settings` and `PUT /reasoner/settings` endpoints to app.py, following the connector endpoint pattern with `_structured_error_response` for unknown reasoner ids (422)
- Created `data-service/tests/test_reasoner.py` with 8 tests covering registry shape, select/persist round-trip, and unknown id rejection
- Created `ui-v2/src/lib/reasonerApi.js` with `getReasonerSettings()` and `selectReasoner(id)` following llmApi.js conventions
- Updated `ui-v2/src/screens/ReasonerScreen.jsx` with two selectable reasoner cards — selected card has active border treatment + "Active" badge, placeholder entries show "Integration pending" badge, screen-level note explains selection does not yet change validation behavior

## Task Commits

Each task was committed atomically:

1. **Task 1: backend — reasoner.py + endpoints** - `d1bcb5e` (feat)
2. **Task 2: ReasonerScreen UI** - `4cf371c` (feat)
3. **Task 3: Verify** - No file changes (90 tests pass, build passes)

## Files Created/Modified

- `data-service/reasoner.py` — Reasoner registry (HermiT, Pellet) with placeholder status, JSON-file persistence
- `data-service/app.py` — Added `import reasoner`, `ReasonerSettingsPayload` model, GET and PUT `/reasoner/settings` endpoints
- `data-service/tests/test_reasoner.py` — 8 tests: registry shape, select/persist round-trip, unknown id rejection
- `ui-v2/src/lib/reasonerApi.js` — `getReasonerSettings()`, `selectReasoner(id)` with error handling
- `ui-v2/src/screens/ReasonerScreen.jsx` — Full reasoner selector screen with cards, active treatment, placeholder badges, and screen-level annotation

## Decisions Made

- Reasoner settings stored as plain JSON (no secrets, no encryption needed)
- Registry structured with explicit `status` field (`"placeholder"` vs future `"integrated"`) so real integration can be added without schema changes
- 422 status for unknown reasoner (following FastAPI validation idiom rather than 400)

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

None.

## Verification Results

- `python -m pytest data-service/tests/ -q`: 90 passed (82 existing + 8 new reasoner tests)
- `npm --prefix ui-v2 run build`: passes
- Live round-trip: not performed (data-service not running in this environment)

## Next Phase Readiness

- Reasoner screen ready for Phase 814-02 (if any) — placeholder wiring complete
- Real reasoner integration (HermiT/Pellet backend) can be added later by swapping `status: "placeholder"` to `status: "integrated"` and adding the actual reasoning calls

---
*Phase: 814-reasoner-screen*
*Completed: 2026-07-11*
