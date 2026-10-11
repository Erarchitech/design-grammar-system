---
phase: 1301-rabochiy-klient-i-bezopasnoe-chtenie
plan: 39
subsystem: degram-host-connecting-state
status: complete
completed: 2026-10-12
requires: [1301-38]
provides:
  - one caption-less connecting sphere on the landing ring centre while a project opens (F-05, D-47)
  - DeGram's own opening loader removed from the first screen (no second "Connecting to DG")
  - host-centre browser test checks the centre at 1280x800 and 900x700 and the RU/EN role=status label
affects: [1301-41]
tech-stack:
  patterns:
    - state announced by role=status + aria-label instead of visible caption
key-files:
  modified:
    - apps/degram/apps/desktop/src/degram/degram-gate.tsx
    - apps/degram/apps/desktop/src/degram/shell.test.tsx
    - ui-v2/src/landing/HostCentre.jsx
    - ui-v2/src/landing/landing.css
    - ui-v2/tests/host-centre.browser.jsx
    - ui-v2/tests/run-host-centre.mjs
requirements-completed: []
---

# Phase 1301 Plan 39: one connecting sphere, centred on the ring (F-05, D-47)

**In 0.1.10 "Connecting to DG" showed twice and the sphere sat below the ring centre. The DeGram gate no longer renders its own opening loader, and the host sphere has no caption and sits at `top: 50%`, which is the ring centre (`landingEngine.js` `cx = vw/2`, `cy = vh/2`, untouched).**

## What was built

- Component `degram-gate.tsx`: removed the `opening && !unreachable && <DgConnecting .../>` render, and the now-unused `opening` / `unreachable` vars and the `DgConnecting` import. The pre-paint loaders (`dg-page.tsx`, `sign-in-state.tsx`) are unchanged and their tests (`shell.test.tsx` D-42 and "shows the Loader until the first paint") are untouched.
- Component `shell.test.tsx`: new test, gate with scope `opening` and the DG page painted renders no "Connecting to DG" text. Confirmed RED before the change (the loader span was found), GREEN after.
- Framework `HostCentre.jsx`: caption `<span>` dropped; container is `role="status"` with `aria-label` "Подключение к DG" / "Connecting to DG"; `aria-live` / `aria-hidden` logic kept.
- Framework `landing.css`: `.dgl-host-centre` at `top: 50%` with the `calc(-50% + 18px)` to `-50%` entrance kept; removed `flex-direction: column`, `gap`, `width`, and the caption font settings, so nothing shifts the sphere off the point.
- Framework `host-centre.browser.jsx` / `run-host-centre.mjs`: the old assertion on visible Russian caption text is replaced by: no visible text, `role=status` + RU `aria-label`, an EN render check, and a geometry check (sphere bounding-box centre within 2 px of `innerWidth/2, innerHeight/2`). The runner now launches headless Chrome twice, at 1280x800 and 900x700 viewports.

## Verification (real output)

- `node ui-v2/tests/run-host-centre.mjs`: exit 0, all 6 checks PASS at both viewports; measured viewports `1280x800, 900x700`; centre offset dx=0, dy=0 at both. Before the CSS/JSX change the same test failed (caption present; then dy=18 / off-centre).
- `node --test ui-v2/tests/host-degram.test.mjs`: 6/6 pass (includes the ring-centre wiring check, engine unchanged).
- `npm --prefix ui-v2 run build`: exit 0.
- `grep "Подключение к DG" ui-v2/src/landing/HostCentre.jsx`: one match, inside the `aria-label` expression.
- `npx vitest run --project ui src/degram` (apps/desktop): 13 files, 259/259 passed.
- `npx tsc -p . --noEmit` (apps/desktop): exit 0. ESLint on the two component files: 0 errors, 1 padding-line warning on a line this plan did not touch (`Notice`).
- `python tools/degram/workspace.py verify`: fails with "Submodule gitlink does not match the selected component HEAD", the expected state while local child commits (plans 37, 38, 39) are not bumped (plan 41's owner checkpoint).

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] host-centre browser test already failing on plan 40's connectors read**
- **Found during:** Task 1 (first full run of the harness).
- **Issue:** plan 40 (`c9665ed`) made the hosted Connectors page call `GET /connectors?project=A`; `host-centre.browser.jsx` did not mock it, so its last check failed with "Unexpected requests" independent of this plan.
- **Fix:** added `allow('/connectors?project=A', { categories: [], connectors: [] })` before the connectors navigation step.
- **Files modified:** `ui-v2/tests/host-centre.browser.jsx`. **Commit:** framework `408f94e`.

**2. [Rule 3 - Blocking] runner file not in plan's `files_modified`**
- **Issue:** the 1280x800 / 900x700 viewport check needs the runner to set the window size; the existing runner used Chrome's default window.
- **Fix:** `run-host-centre.mjs` loops over the two sizes (outer window padded by Chrome's 16x151 px frame so the measured inner viewport is exactly 1280x800 and 900x700) and fails unless two distinct viewports were measured.
- **Commit:** framework `408f94e`.

**3. Test technique:** headless virtual time does not advance CSS transitions (the centre read dy=18 at the entrance start), so the geometry check injects `transition: none` on `.dgl-host-centre` and reads the settled position. The entrance animation itself is unchanged in CSS.

## Known Stubs
None.

## Threat Flags
None. T-1301-39-01 (removing visible text must not hide the state from screen readers): `role="status"` + `aria-label` kept and asserted in RU and EN.

## Limits
- Not verified in the real DeGram window or against the real `/dg-think-*.gif`: in the headless harness the CSP blocks the gif, so the CSS fallback sphere (same size rule) is what was measured. The ring is checked by viewport-centre equality, as the plan specifies, not by reading the canvas pixels. A live check (choose a project in PROJECTS: one sphere, centred in the ring, no text, then the pill) is left for plan 41's installed build.
- Component commit `52a09980` is local only; nothing pushed, framework gitlink not bumped.

## Commits
- component `52a09980` fix(1301-39): one connecting sphere in the ring centre, no DeGram loader on top (F-05, D-47)
- framework `408f94e` fix(1301-39): connecting sphere without caption, centred on the ring (D-47)

## Self-Check: PASSED
