---
phase: 38-ai-generated-grasshopper-script-inputs
plan: 06
subsystem: ui
tags: [react, ui-v2, computgraph, generation, model-screen]

# Dependency graph
requires:
  - phase: 38-01
    provides: "spec/API.md normative contracts for generate-inputs and candidates/accept — every JSON key, error code, and vocabulary this client and component render against"
  - phase: 38-04
    provides: "POST /computgraph/generate-inputs route and its exact candidates[]/boundParameters[]/excludedParameters[] response shape"
  - phase: 38-05
    provides: "POST /computgraph/candidates/accept route and fetch_generated_param_states() read"
provides:
  - "ui-v2/src/lib/inputGenApi.js: generateInputs/acceptCandidate/fetchAcceptedCandidates client, mirroring modelApi.js's base()/error-unwrap conventions"
  - "ui-v2/src/components/display/CandidateTable.jsx: row-per-candidate, column-per-parameter presentational table with three honest claim states"
  - "AI input candidates Panel wired into ModelScreen.jsx, with acceptCandidate confined to a single click handler"
affects: [38-07]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "acceptCandidate/generateInputs separation enforced in the component's control flow, not just documented: no useEffect body anywhere in ModelScreen.jsx references either call — grep-verified"
    - "acceptedStateIds tracked per-response by candidateId (session-scoped 'already accepted' flag) rather than recomputing the server's content hash client-side"

key-files:
  created:
    - ui-v2/src/lib/inputGenApi.js
    - ui-v2/src/components/display/CandidateTable.jsx
  modified:
    - ui-v2/src/components/index.js
    - ui-v2/src/screens/ModelScreen.jsx

key-decisions:
  - "CandidateTable's undeterminable claim badge uses Badge's neutral 'soft' variant (never 'signal'/'violation') and carries no confidence number — the D-09 credibility invariant is enforced by variant choice, not by a separate boolean prop that could later be misused"
  - "The satisfied/violated claim label is rendered as '≤ {ruleLimit}' for both states (same label form per the plan's explicit requirement) since the API response carries no explicit comparison-operator field; the full directional basis text is preserved in the badge's title attribute"
  - "ruleForGen is a separate state from the screen's existing ruleId, defaulted from it on every ruleId change via a state-only effect (no generation/acceptance call) — switching the AI panel's generation target independently of the rule being inspected doesn't disturb the validation-run view"
  - "acceptedStateIds in CandidateTable is keyed by candidateId within one generate-inputs response, not the real server-computed StateId hash — documented in-code as a deliberate simplification since recomputing cg_paramstate_store.compute_param_state_id client-side would duplicate persistence-layer logic in a presentational component for no behavioural gain"

requirements-completed: [GHIN-01, GHIN-04]

coverage:
  - id: D1
    description: "inputGenApi.js exposes generateInputs/acceptCandidate/fetchAcceptedCandidates against the two documented routes, with acceptCandidate as the sole writer and bound Cypher parameters throughout"
    requirement: GHIN-01
    verification:
      - kind: other
        ref: "grep-based acceptance criteria in 38-06-PLAN.md Task 1 (all passed: route path counts, hint surfacing, no template-literal Cypher interpolation); npm --prefix ui-v2 run build exits 0"
        status: pass
    human_judgment: false
  - id: D2
    description: "CandidateTable renders candidates as rows/parameters as columns with three honest claim states (satisfied/violated/undeterminable), excludedParameters visible with reason, and no API import of any kind"
    requirement: GHIN-04
    verification:
      - kind: other
        ref: "grep-based acceptance criteria in 38-06-PLAN.md Task 2 (all passed: zero API-import matches, all three claim states present, D-09 comment present, excludedParameters rendered, zero token diff); npm --prefix ui-v2 run build exits 0"
        status: pass
    human_judgment: false
  - id: D3
    description: "AI input candidates Panel wired into ModelScreen with acceptCandidate confined to exactly one click-handler call site and generateInputs never called from a useEffect"
    requirement: GHIN-04
    verification:
      - kind: other
        ref: "grep-based acceptance criteria in 38-06-PLAN.md Task 3 (all passed: single acceptCandidate( call site, single generateInputs( call site, no useEffect body references either); npm --prefix ui-v2 run build exits 0"
        status: pass
    human_judgment: false
  - id: D4
    description: "The three Tier-2 manual browser observations (direct-parameter satisfied/violated rendering, geometry-required Callout + neutral badges, Reject-issues-no-request/Accept-issues-exactly-one-POST) are recorded with actual results"
    human_judgment: true
    rationale: "Requires a human driving a real browser session with the network tab open against live fixture data; this execution environment has no browser-automation tool, and no live Neo4j fixture in this instance currently pairs a published Computgraph definition with a Rule_Id an inputBindings entry maps to. Recorded as outstanding below rather than fabricated — see Task 4 notes."

duration: ~1h10min
completed: 2026-07-27
status: complete
---

# Phase 38 Plan 06: AI Input Candidates Review Panel Summary

**A `generate-inputs`/`candidates/accept` API client, a row-per-candidate `CandidateTable` with three honest claim states, and an "AI input candidates" panel wired into the existing ui-v2 Model screen — with `acceptCandidate` confined to exactly one click handler and zero `useEffect` reachability into either route.**

## Performance

- **Duration:** ~1h10min
- **Tasks:** 4
- **Files modified:** 4 (2 created, 2 modified)

## Accomplishments

- `ui-v2/src/lib/inputGenApi.js` (new): `generateInputs(project, definitionId, ruleId, candidateCount, parameterOverrides)` and `acceptCandidate(project, definitionId, ruleId, candidate)` POST to the two Phase 38 routes through the same `base()`/`getConfig().dataServiceUrl` convention `modelApi.js` uses; both surface `detail.error` and `detail.hint` on failure. `fetchAcceptedCandidates(project, ruleId)` reads standalone AI-generated `ParamState` nodes via bound Cypher parameters only. A file-header comment states the GHIN-04 rule: `acceptCandidate` is the sole writer.
- `ui-v2/src/components/display/CandidateTable.jsx` (new): presentational table, one row per candidate and one column per bound parameter (label + `[domainMin … domainMax]` secondary text), following the Colibri/MIT DSE row-per-design convention (`38-RESEARCH.md` §4.4). Renders exactly three claim states — `satisfied`/`violated` as a labeled `Badge` and `undeterminable` as a neutral badge with no confidence number, comment naming D-09. `excludedParameters` render as an em dash with the reason as a tooltip, never a blank cell (D-04). A `geometry-required` `determinabilityClass` renders a `Callout` above the table. Accept/Reject actions live in the last column; Reject is a documented local dismissal with no request of any kind (D-19). No API import anywhere in the file. Exported from the `display` barrel.
- `ui-v2/src/screens/ModelScreen.jsx`: new "AI input candidates" `Panel` placed directly after the existing "Rule" panel, inside the same `propMode === "run" && view` block so it shares the screen's rule-selection context. New state: `ruleForGen`, `candidateCount`, `paramOverrides`, `candidates`, `genErr`, `genBusy`, `acceptedStates`, `busyCandidateId`. A rule-change effect resets `ruleForGen`/`candidates`/`genErr` but calls neither route. `Generate` (candidate count clamped 1..8, optional comma-separated parameter overrides) calls `generateInputs` from its own `onClick`. `CandidateTable`'s `onAccept` calls `acceptCandidate` — the only call site in the file — then refreshes via `fetchAcceptedCandidates`; `onReject` only filters local state.
- Docker: rebuilt `design-grammars` with `--no-cache` per `CLAUDE.md`'s cache-staleness gotcha, and (additionally, see Deviations) rebuilt `data-service` so the already-committed Phase 38 routes actually exist in the running container. Both containers are up and serving.

## Task Commits

Each task was committed atomically:

1. **Task 1: API client for the two generation routes** - `36e1dd7` (feat)
2. **Task 2: CandidateTable component** - `2d55847` (feat)
3. **Task 3: Wire the review panel into the Model screen** - `495388d` (feat)
4. **Task 4: Rebuild the UI container and record manual verification steps** - no code changes (infra-only; this SUMMARY plus the metadata commit are the record)

**Plan metadata:** pending (this commit)

## Files Created/Modified

- `ui-v2/src/lib/inputGenApi.js` - `generateInputs`, `acceptCandidate`, `fetchAcceptedCandidates`
- `ui-v2/src/components/display/CandidateTable.jsx` - row-per-candidate presentational table
- `ui-v2/src/components/index.js` - barrel export for `CandidateTable`
- `ui-v2/src/screens/ModelScreen.jsx` - "AI input candidates" Panel, new state, Generate/Accept/Reject wiring

## Decisions Made

- `CandidateTable`'s claim label for both `satisfied` and `violated` renders as `≤ {ruleLimit}` (same label form, per the plan's explicit requirement) since `generate-inputs`'s response carries no separate comparison-operator field — the full directional text lives in `ruleSatisfaction.basis`, surfaced via the badge's `title`.
- `acceptedStateIds` is keyed by `candidateId` within a single `generate-inputs` response rather than the server's real content-hashed `StateId` — recomputing `cg_paramstate_store.compute_param_state_id` client-side would duplicate persistence-layer logic in a presentational component purely to render a checkmark; documented in-code as a deliberate simplification.
- `ruleForGen` is a separate piece of state from the screen's existing `ruleId`, re-defaulted on every `ruleId` change by an effect that touches no route — this lets the AI panel's generation target track the selected validation rule by default while staying independently overridable later if a future plan adds that control.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Two self-referential literal-token false positives caught by this plan's own acceptance-criteria greps before commit**
- **Found during:** Task 1 (route-path grep) and Task 3 (call-site grep)
- **Issue:** `inputGenApi.js`'s header comment originally spelled out both full route paths (`computgraph/generate-inputs`, `computgraph/candidates/accept`) in prose, inflating the "returns 1" acceptance-criteria grep to 2. Separately, `ModelScreen.jsx`'s rule-change effect's own explanatory comment named `generateInputs`/`acceptCandidate` by their bare function names, which would satisfy a literal "no useEffect body references generateInputs" grep as a false failure.
- **Fix:** Reworded the `inputGenApi.js` header comment to describe the two routes without repeating their literal path strings; reworded the `ModelScreen.jsx` effect's comment to describe the guarantee ("performs no generation and no acceptance call of any kind") without naming either function.
- **Files modified:** `ui-v2/src/lib/inputGenApi.js`, `ui-v2/src/screens/ModelScreen.jsx`
- **Commits:** `36e1dd7` (Task 1), `495388d` (Task 3)

**2. [Rule 3 - Blocking issue] `data-service` container rebuilt in addition to `design-grammars`**
- **Found during:** Task 4, attempting a live smoke test of `POST /computgraph/generate-inputs` against the running stack
- **Issue:** The plan's Task 4 action only names `docker compose build --no-cache design-grammars`. The running `data-service` container (up since before this session, per `docker compose ps`) predates plans 38-04/38-05's route additions — `data-service` has no source-code volume mount in `docker-compose.yml` (only `./data-service/data` and a read-only `.:/mnt/repo`), so its image must be rebuilt to pick up already-committed code. Without this, `POST /computgraph/generate-inputs` 404s and the panel would be unreachable end-to-end even with a correctly built UI.
- **Fix:** Ran `docker compose build data-service && docker compose up -d data-service` (no `--no-cache`, since Python containers aren't subject to the Vite/nginx static-asset caching gotcha CLAUDE.md documents). Confirmed the route is live afterward: it now returns the documented structured `{error, hint, code}` body (`COMPUTGRAPH_GENERATE_INPUTS_NO_DEFINITION`) instead of FastAPI's generic 404.
- **Files modified:** none (infra rebuild only, no code change)
- **Verification:** `curl -X POST http://localhost:8000/computgraph/generate-inputs ...` returns a structured 422 body naming the correct error code, confirming the route exists and dispatches correctly.

---

**Total deviations:** 2 auto-fixed (2 self-referential documentation false positives, 1 necessary supporting infra rebuild)
**Impact on plan:** No scope creep in the shipped code — both documentation fixes preserve the intended meaning while satisfying the plan's own literal acceptance criteria; the `data-service` rebuild is a zero-code-change infrastructure action needed to make the already-shipped Phase 38 backend routes actually reachable for any live verification (this plan's or 38-07's).

## Issues Encountered

**No live fixture pairs a published Computgraph definition with a Rule an `inputBindings` entry maps to.** Querying the live Neo4j instance directly: the only project with a published Computgraph definition (`definitionId` present, `graph:'Computgraph'`) is `urbanblock-uat`, which has zero `Rule` nodes. The projects that do have `Rule` nodes (`Test Project`, `TestA`, `v8-ui-smoke`, `URBAN_BLOCK_V7`) have zero published Computgraph definitions. This means `POST /computgraph/generate-inputs` cannot resolve past `COMPUTGRAPH_GENERATE_INPUTS_NO_DEFINITION` / `COMPUTGRAPH_GENERATE_INPUTS_RULE_NOT_FOUND` against any currently-live project — confirmed directly against the rebuilt, running `data-service` container, not assumed.

Consequently, the three Tier-2 manual browser observations Task 4 asks for could not be genuinely produced in this session:

1. **Generating for a `direct-parameter` rule renders four rows with values inside their stated domains, claim badges naming the limit.** NOT OBSERVED — no live project combines a published definition with a bound `direct-parameter` rule. `curl`-level confirmation only: the route is live and returns the documented structured-error shape when preconditions aren't met.
2. **Generating for a `geometry-required` rule renders the Callout and four neutral badges, no success styling, no confidence number.** NOT OBSERVED — same blocker. The rendering logic itself is exercised by the component's own structure (verified via source: the `determinabilityClass === "geometry-required"` branch and the `undeterminable` claim branch are the only code paths that can ever render together, since `generate_inputs()` forces `undeterminable` for every candidate when `determinabilityClass` is `geometry-required` per plan 38-04), but this is a static-code argument, not a browser observation.
3. **Reject issues no network request; Accept issues exactly one POST to `/computgraph/candidates/accept`.** NOT OBSERVED — same blocker, and this environment has no browser-automation tool (no Playwright/CDP session) to drive a real network-tab check even if fixture data existed.

This execution environment has no browser-automation tool available, so even with fixture data present, a human-equivalent network-tab observation was not achievable here. Recording this honestly rather than fabricating an observed result, per the plan's own instruction ("Record the actual observed result, including a failure if that is what happens").

**Recommended next action (belongs to plan 38-07 per this plan's own text):** either publish a Computgraph definition into `v8-ui-smoke` (which already carries `R_URB_HEIGHT_MAX_75_V`) via `POST /computgraph/publish`, or add an `inputBindings`-mapped rule into `urbanblock-uat`, then drive the panel through a real browser with the network tab open. Both containers (`design-grammars`, `data-service`) are already rebuilt and running with this plan's code, so no further build step should be needed before that UAT session.

## User Setup Required

None - no external service configuration required. Docker rebuilds were run directly in this session against the already-running local compose stack; no new environment variables or credentials were introduced.

## Next Phase Readiness

- Plan 38-07 (SC1 measurement / phase UAT) inherits a fully wired panel and a live, correctly-routed backend — the `data-service` rebuild performed here removes what would otherwise have been 38-07's own first blocker.
- Plan 38-07's UAT should perform the fixture-data step noted above (publish a definition into a rule-bearing project, or vice versa) before attempting the three Tier-2 browser observations this plan could not complete.
- `npm --prefix ui-v2 run build` exits 0 after every task; `git diff ui-v2/package.json` is empty — no new dependency was introduced (T-38-SC accepted risk, unchanged).
- No blockers to closing this plan's own scope: all three code tasks are complete, committed, and grep/build-verified exactly as their acceptance criteria specify.

## Self-Check: PASSED

All 4 files (`ui-v2/src/lib/inputGenApi.js`, `ui-v2/src/components/display/CandidateTable.jsx`, `ui-v2/src/components/index.js`, `ui-v2/src/screens/ModelScreen.jsx`) verified present on disk, and all 3 task commit hashes (`36e1dd7`, `2d55847`, `495388d`) verified present via `git log --oneline --all`.

---
*Phase: 38-ai-generated-grasshopper-script-inputs*
*Completed: 2026-07-27*
