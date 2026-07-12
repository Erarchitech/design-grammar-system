---
phase: 822-owl-2-dl-reasoning-integration-reasoner-screen-wiring
plan: 03
subsystem: ui-v2 (Reasoner screen)
tags: [reasoner, hermit, owl-2-dl, consistency-check, react-state-machine]
dependency-graph:
  requires: ["822-01 ({iri,label} unsatisfiable_classes shape)", "822-02 (HermiT integrated status + reconciled proxy timeout)"]
  provides: ["ui-v2/src/lib/reasonerApi.js runConsistencyCheck(project,{signal})", "ReasonerScreen run-state machine + four-verdict rendering"]
  affects: ["ui-v2/src/screens/ReasonerScreen.jsx", "ui-v2/src/lib/reasonerApi.js"]
tech-stack:
  added: []
  patterns:
    - "Screen-local React state machine (no global store) mirroring the existing loading/loadError pairing"
    - "AbortController + fetch cancellation (new pattern for this codebase, per RESEARCH 'No Analog Found')"
    - "setInterval/Date.now elapsed-timer, clearInterval on every exit path (mirrors GraphScreen.jsx)"
    - "formatRelativeDate lifted verbatim from SessionHistory.jsx as a module-level helper"
key-files:
  created: []
  modified:
    - "ui-v2/src/lib/reasonerApi.js"
    - "ui-v2/src/screens/ReasonerScreen.jsx"
decisions:
  - "runConsistencyCheck does not reuse getJson and does not throw on non-2xx -- returns {ok,status,body} so the caller branches on body shape (D-08/D-09), matching RESEARCH Pitfall 1"
  - "Run/Cancel controls and the result region are gated on r.status === 'integrated', not on card selection (isActive) -- a user can run the check without re-selecting HermiT"
  - "Each terminal state (consistent/inconsistent/unknown/cancelled) renders its own enabled 'Run check' button to allow re-running without reloading the screen; error state instead mirrors the existing loadError inline-Retry pattern"
  - "Button/span onClick handlers inside the card call e.stopPropagation() so clicking Run/Cancel/Retry does not also trigger the card's own onClick (handleSelect)"
  - "Spinner implemented as a small inline @keyframes-driven div (no icon library, no new shared primitive) since no spinner precedent exists in ui-v2"
  - "Inconsistent-class list uses the array index as the React key (never entry.iri) to keep the prohibition on rendering/referencing raw IRIs airtight in this file"
metrics:
  duration: "~35min active work (session interrupted after Task 1 commit and resumed)"
  completed: 2026-07-12
status: complete
---

# Phase 822 Plan 03: ReasonerScreen HermiT Run/Cancel + Four-Verdict Wiring Summary

Wired the HermiT card's live OWL 2 DL schema-consistency check into `ui-v2`: a no-throw `runConsistencyCheck` API client, a screen-local run-state machine with Run/Cancel/elapsed-timer, and four distinct verdict renderings (Consistent/Inconsistent/Unknown/Cancelled) plus a separate transport-error line -- completing the frontend half of REAS-06.

## What Was Built

**Task 1 -- `ui-v2/src/lib/reasonerApi.js`:** Added `runConsistencyCheck(project, { signal } = {})`, a dedicated POST client to `/reasoner/consistency` that always forces `engine: "hermit"` (D-05), forwards the caller's `AbortController` signal (D-07), defensively parses the response body, and returns `{ ok, status, body }` without throwing on non-2xx. It deliberately does not reuse the existing `getJson` helper -- `getJson`'s throw-and-collapse behavior would destroy the distinction between the sidecar's genuine semantic timeout body (`{consistent:null,"error":"timeout",...}`) and data-service's structured transport-error body (`{"detail":{"error",...}}`), both of which arrive as HTTP 504 (RESEARCH Pitfall 1). No caching, memoization, or response reuse is present -- every call is a fresh network request (D-10).

**Task 2 -- `ui-v2/src/screens/ReasonerScreen.jsx` state machine:** Added `runState` (`idle|running|consistent|inconsistent|unknown|cancelled|error`), `runError`, `runResult`, `lastCheckedAt`, `elapsedSec`, and an `abortRef` alongside the existing `loading`/`loadError`/`saving`/`saveError` state. `handleRunCheck` creates a fresh `AbortController`, starts a 1s `setInterval` elapsed-seconds ticker, awaits `runConsistencyCheck`, and branches exactly per the RESEARCH-documented body-shape rule: `body.error === "timeout" && "consistent" in body` -> `unknown` (D-08); `!ok` -> `runError` + `error` (D-09); otherwise `consistent`/`inconsistent` from `body.consistent`. `lastCheckedAt` is stamped on consistent/inconsistent/unknown only, never on cancelled/error. The `finally` block always clears the interval and resets `abortRef.current`. `handleCancel` calls `abortRef.current?.abort()`, which the `catch` block recognizes via `err.name === "AbortError"` to set `cancelled`, kept distinct from `unknown`. `formatRelativeDate` was lifted verbatim from `SessionHistory.jsx` as a new module-level helper in this file. The active-keyed load `useEffect` was left untouched -- it does not reset any of the new run-state, so the last verdict persists across screen revisits within the session (D-11). Run/Cancel controls (idle body copy + enabled Run button; running spinner + `Running… {n}s` + Cancel + disabled Run) render only inside `r.status === "integrated"`'s card region; the `r.status === "placeholder"` badge branch and Pellet's "Selected — will be used when integration is complete" line are untouched (D-04/D-06). The phantom tokens `--color-accent` (selection ring, selected-line text) and `--surface-focus` (selection wash) were replaced with the real tokens `--accent-selection`/`--accent-selection-bg` on every line this task touched.

**Task 3 -- terminal verdict rendering:** Added the four verdict bodies inside the same `r.status === "integrated"` region, each with its own re-run "Run check" button (except error, which mirrors the existing Retry pattern instead): Consistent (`--color-ink` text, `Badge variant="solid"`, "✓ Schema consistent — no unsatisfiable classes found."); Inconsistent (`--color-signal` text on a `--color-signal-soft` wash, `Badge variant="signal"`, a headline with correct singular/plural unsatisfiable-class count, and a bulleted list rendering only `entry.label` -- the empty-list edge case shows the count line with no list); Unknown (`--text-muted`, `Badge variant="outline"` "Inconclusive", "– Inconclusive — the reasoner timed out before finishing. Try again."); Cancelled (`--ink-a56` faint text, no badge, "× Run cancelled — no result."). A distinct D-09 transport-error line (`--color-signal-ink`, "Reasoner unavailable · {detail}" + inline Retry) mirrors the screen's existing `loadError`/Retry pattern verbatim and is never folded into Unknown. A "Last checked {relative time}" caption (via `formatRelativeDate`) renders under every completed verdict except Cancelled/Error.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 2 - missing critical functionality] Added `e.stopPropagation()` to every Run/Cancel/Retry click handler inside the card**
- **Found during:** Task 2
- **Issue:** The reasoner card's outer wrapper `<div>` has its own `onClick={() => handleSelect(r.id)}`. Without stopping propagation, clicking Run/Cancel/Retry inside the card would also bubble up and fire an unrelated `PUT /reasoner/settings` selection call.
- **Fix:** Added `e.stopPropagation()` inside each new button/span `onClick` before invoking `handleRunCheck`/`handleCancel`.
- **Files modified:** `ui-v2/src/screens/ReasonerScreen.jsx`
- **Commit:** ce675f2 (Task 2), 51d1c98 (Task 3, same pattern applied to terminal-state buttons)

**2. [Rule 2 - missing critical functionality] Added a re-run "Run check" button to each terminal verdict state**
- **Found during:** Task 3
- **Issue:** The plan's Task 3 action text specifies rendering the four verdict bodies but doesn't explicitly call out a re-run control for completed states; without one the architect would have no way to run the check again after seeing a result (short of reloading the screen), which would be an incomplete feature relative to D-10's "every run is a fresh POST" expectation.
- **Fix:** Added an enabled `Button variant="outline" size="sm"` "Run check" under each of Consistent/Inconsistent/Unknown/Cancelled (Error already has its own Retry affordance per the mirrored `loadError` pattern, so no separate button was added there).
- **Files modified:** `ui-v2/src/screens/ReasonerScreen.jsx`
- **Commit:** 51d1c98

**3. [Rule 3 - blocking issue, no precedent] Implemented the spinner as a small inline `@keyframes`-driven div**
- **Found during:** Task 2
- **Issue:** UI-SPEC requires a spinner during the `running` state, but the codebase has zero icon library, zero existing spinner component, and zero prior CSS keyframe usage anywhere in `ui-v2/src` (confirmed via `graphify`/grep).
- **Fix:** Rendered a 12px bordered circle with a scoped `<style>{'@keyframes dg-reasoner-spin {...}'}</style>` tag and `animation: dg-reasoner-spin 0.8s linear infinite`, using only existing achromatic tokens (`--color-hairline`, `--text-muted`) — no new shared primitive, no new dependency.
- **Files modified:** `ui-v2/src/screens/ReasonerScreen.jsx`
- **Commit:** ce675f2

No architectural changes (Rule 4) were needed. No authentication gates were encountered.

## Known Stubs

None. The screen wires a real, live `POST /reasoner/consistency` call; no hardcoded/mock data paths were introduced.

## Threat Flags

None beyond what the plan's own `<threat_model>` already covers (T-822-05/T-822-06/T-822-SC) — this plan's rendering strictly follows `entry.label`-only output and pre-written error copy, matching the registered mitigation.

## Verification

- `npm --prefix ui-v2 run build` exits 0 (verified after each task and again at plan completion)
- Task 1: `grep -q "export async function runConsistencyCheck"`, `grep -q 'engine'`, `grep -q 'signal'`, `! grep -nE "Cache-Control|memoize"` all pass on `reasonerApi.js`
- Task 2: `grep -q "AbortController"`, `grep -q "runConsistencyCheck"`, `grep -q 'status === "integrated"'`, `! grep -nE "--color-accent|--surface-focus"` all pass on `ReasonerScreen.jsx`
- Task 3: `grep -q "Schema inconsistent"`, `grep -q "Inconclusive"`, `grep -q "Run cancelled"`, `grep -q "Reasoner unavailable"`, `grep -q "Last checked"`, `! grep -q "\.iri"` all pass on `ReasonerScreen.jsx`
- Confirmed no staleness/"ontology changed" banner text exists (D-12)
- Confirmed no "valid"/"passed"/"compliant" wording in verdict copy — only pre-existing, unrelated uses of "validation" in screen-level prose (D-03)
- Manual UAT of the four verdict states + Cancel + error line against the live stack is deferred to Plan 04 per the plan's own `<verification>` section (no frontend test infra in `ui-v2`)

## Self-Check: PASSED

- FOUND: `ui-v2/src/lib/reasonerApi.js` (modified, contains `runConsistencyCheck`)
- FOUND: `ui-v2/src/screens/ReasonerScreen.jsx` (modified, contains run-state machine + four-verdict rendering)
- FOUND commit 592712a (Task 1)
- FOUND commit ce675f2 (Task 2)
- FOUND commit 51d1c98 (Task 3)
