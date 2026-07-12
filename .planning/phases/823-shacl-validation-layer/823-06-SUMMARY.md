---
phase: 823-shacl-validation-layer
plan: 06
subsystem: ui
tags: [react, jsx, design-tokens, shacl, model-screen, badge, collapsible]

# Dependency graph
requires:
  - phase: 823-shacl-validation-layer (Plan 823-03)
    provides: "shaclReport parsed onto the /validation/view/* selected-run `view` payload"
provides:
  - "Severity color tokens (--color-warning*, --color-info*) mirroring the existing --color-signal family, light + dark"
  - "Badge violation/warning/info variants; Collapsible tone prop ('violation'|'warning'|'info'|'neutral') with signal boolean kept as a backward-compatible alias for tone='violation'"
  - "SHACL Data Integrity Panel in ModelScreen's selected-run detail implementing the four UI-SPEC states (not-checked, unavailable/timeout, conforms, findings), keyed on results.length never a conforms boolean"
affects: [824-connector-credential-integration, future-shacl-ui-followups]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Severity token triads (base/-ink/-soft) extend the existing --color-signal pattern for new chromatic categories"
    - "Collapsible tone prop generalizes the prior boolean signal flag while preserving the old call sites unchanged"

key-files:
  created: []
  modified:
    - ui-v2/src/styles/tokens/colors.css
    - ui-v2/src/components/display/Badge.jsx
    - ui-v2/src/components/surfaces/Collapsible.jsx
    - ui-v2/src/screens/ModelScreen.jsx

key-decisions:
  - "Task 3 (checkpoint:human-verify) required no code changes — user reviewed the four SHACL states + severity colors in both themes in the running UI and responded 'approved' with no reported issues"
  - "State selection keys strictly on shaclReport.results.length (0 vs >0), never on a conforms boolean, per the UI-SPEC hard rule (allow_infos/allow_warnings would otherwise conflate warnings with conformance)"
  - "shapeId is destructured/present on finding objects but never interpolated into any rendered JSX expression — verified via source grep, only appears in a code comment describing the rule"

patterns-established:
  - "Per-severity Collapsible groups omit any group whose count is 0, and only render non-zero severity chips in the summary row"
  - "Empty finding fields render the neutral em-dash '—' (KVRow convention) rather than falling back to a raw IRI"

requirements-completed: [SHCL-02]

coverage:
  - id: D1
    description: "Severity color tokens (--color-warning, --color-warning-ink, --color-warning-soft, --color-info, --color-info-ink, --color-info-soft) added in both :root and :root[data-theme=\"dark\"] blocks of colors.css"
    requirement: "SHCL-02"
    verification:
      - kind: unit
        ref: "npm --prefix ui-v2 run build (source assertion: grep --color-warning/--color-info in colors.css)"
        status: pass
    human_judgment: false
  - id: D2
    description: "Badge exposes violation/warning/info variants; Collapsible accepts a tone prop and still honors the legacy signal boolean unchanged at existing call sites"
    requirement: "SHCL-02"
    verification:
      - kind: unit
        ref: "npm --prefix ui-v2 run build (source assertion: grep warning in Badge.jsx)"
        status: pass
    human_judgment: false
  - id: D3
    description: "ModelScreen SHACL Data Integrity Panel renders all four states (not-checked, unavailable/timeout, conforms, findings) keyed on results.length, with Solibri-style chip summary, per-severity Collapsible groups, and 4-line finding cards; shapeId never rendered"
    requirement: "SHCL-02"
    verification:
      - kind: unit
        ref: "npm --prefix ui-v2 run build (source assertions: SHACL Data Integrity panel present, shaclResults.length gating, no shapeId render usage, no dangerouslySetInnerHTML)"
        status: pass
      - kind: manual_procedural
        ref: "Task 3 checkpoint:human-verify — user visually confirmed all four states + severity colors in light/dark theme in the running UI, responded 'approved'"
        status: pass
    human_judgment: true
    rationale: "Visual/chromatic correctness (severity color legibility in both themes, absence of alarming styling on neutral states) requires human eyes on the rendered UI; this was the explicit purpose of the Task 3 checkpoint, already completed by the user's 'approved' response."

# Metrics
duration: ~10min (Task 3 resume only; Tasks 1-2 executed in a prior session)
completed: 2026-07-12
status: complete
---

# Phase 823 Plan 06: SHACL Data Integrity UI Summary

**Solibri-style SHACL Data Integrity panel on the Model screen's selected-run detail, with new red/orange/yellow severity tokens and Badge/Collapsible variants, closing Phase 823's only UI plan.**

## Performance

- **Duration:** ~10 min (this resume session covering Task 3 checkpoint closure); Tasks 1-2 executed and committed in a prior session
- **Tasks:** 3/3 (2 auto, 1 checkpoint:human-verify)
- **Files modified:** 4

## Accomplishments
- Added six new severity color tokens (`--color-warning*`, `--color-info*`) in both light and dark theme blocks of `colors.css`, mirroring the existing `--color-signal` structure exactly per UI-SPEC hex values
- Extended `Badge.jsx` with `violation`/`warning`/`info` variants and `Collapsible.jsx` with a `tone` prop (`'violation'|'warning'|'info'|'neutral'`), keeping the legacy `signal` boolean as a backward-compatible alias so the two pre-existing Failing/Passing call sites needed no change
- Added a `<Panel title="SHACL Data Integrity">` to `ModelScreen.jsx`'s selected-run detail implementing all four UI-SPEC states (not-checked, unavailable/timeout, conforms, findings), keyed strictly on `shaclReport.results.length`, with a chip count summary, per-severity `Collapsible` groups, and 4-line finding cards — never rendering `shapeId` or a raw IRI fallback
- Closed the Task 3 human-verify checkpoint: user visually reviewed all four states and severity colors in both light and dark theme in the running UI and responded "approved" with no reported issues, requiring zero further code changes
- This is the last plan in Phase 823 — all 6 plans in `823-shacl-validation-layer` are now complete

## Task Commits

Each task was committed atomically:

1. **Task 1: Severity color tokens + Badge and Collapsible severity variants** - `a405af5` (feat)
2. **Task 2: SHACL Data Integrity Panel in ModelScreen (four states)** - `5022e8c` (feat)
3. **Task 3: Visual verification of the four SHACL states + severity colors** - checkpoint:human-verify, closed via user's "approved" response; no code commit (no code changes required — see Deviations)

**Plan metadata:** (this commit) `docs(823-06): complete SHACL Data Integrity UI plan`

## Files Created/Modified
- `ui-v2/src/styles/tokens/colors.css` - Adds `--color-warning`/`-ink`/`-soft` and `--color-info`/`-ink`/`-soft` tokens in `:root` and `:root[data-theme="dark"]`
- `ui-v2/src/components/display/Badge.jsx` - Adds `violation`, `warning`, `info` variants (signal-soft/warning-soft/info-soft backgrounds with matching -ink text)
- `ui-v2/src/components/surfaces/Collapsible.jsx` - Adds `tone` prop driving count-badge color; `signal` boolean retained as alias for `tone='violation'`
- `ui-v2/src/screens/ModelScreen.jsx` - Adds the SHACL Data Integrity Panel (four states) inside the `propMode === "run" && view` branch, reading `view.shaclReport`

## Decisions Made
- Task 3's checkpoint:human-verify gate is satisfied by the user's "approved" response alone — no visual issue was reported (wrong severity color, missing/incorrect state, shapeId leakage, or pre-823 runs rendering as an error), so no follow-up code change was needed for this task
- State selection strictly keys on `shaclReport.results.length` (0 → conforms, >0 → findings), never on a `conforms` boolean, matching the UI-SPEC hard rule that `allow_infos`/`allow_warnings` can keep `conforms` true even when warning/info findings exist
- `shapeId` is present on finding objects (per the Plan 823-03 data shape) but is never interpolated into rendered JSX — confirmed via source grep, the only match is a descriptive code comment

## Deviations from Plan

None - plan executed exactly as written. Task 3 was a pure verification gate; the user's "approved" response confirmed the Task 1/Task 2 implementation needed no visual fixes, so no additional code changes, auto-fixes, or deviations were required to close it out.

## Issues Encountered
None.

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness

- Phase 823 (SHACL Validation Layer) is now fully complete: all 6 plans (823-01 through 823-06) executed, requirements SHCL-01 and SHCL-02 satisfied
- Phase 824 (CONNECTOR Credential Integration) has no dependency on Phase 823 and can proceed independently, per ROADMAP.md
- No blockers carried forward from this plan

## Self-Check: PASSED

- FOUND: ui-v2/src/styles/tokens/colors.css (--color-warning/--color-info tokens present, light + dark)
- FOUND: ui-v2/src/components/display/Badge.jsx (violation/warning/info variants present)
- FOUND: ui-v2/src/components/surfaces/Collapsible.jsx (tone prop present)
- FOUND: ui-v2/src/screens/ModelScreen.jsx (SHACL Data Integrity Panel present, four states, results.length gating, no rendered shapeId, no dangerouslySetInnerHTML)
- FOUND commit a405af5 (Task 1)
- FOUND commit 5022e8c (Task 2)
- `npm --prefix ui-v2 run build` re-run clean (947 modules transformed, built in 5.22s)

---
*Phase: 823-shacl-validation-layer*
*Completed: 2026-07-12*
