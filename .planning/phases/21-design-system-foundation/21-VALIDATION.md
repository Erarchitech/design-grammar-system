---
phase: 21
slug: design-system-foundation
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-07-07
---

# Phase 21 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | vitest (greenfield — Wave 0 installs; jsdom environment) |
| **Config file** | none — Wave 0 installs (vitest.config.js in the new V2 app dir) |
| **Quick run command** | `npm run test` (in the V2 app directory) |
| **Full suite command** | `npm run test -- --run` |
| **Estimated runtime** | ~{N} seconds |

---

## Sampling Rate

- **After every task commit:** Run `npm run test`
- **After every plan wave:** Run `npm run test -- --run`
- **Before `/gsd-verify-work`:** Full suite must be green
- **Max feedback latency:** {N} seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| {N}-01-01 | 01 | 1 | DSYS-{XX} | — | N/A | unit | `{command}` | ❌ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `vitest` + `jsdom` + `@testing-library/react` install — greenfield app has no test framework
- [ ] `vitest.config.js` — jsdom environment + setup file
- [ ] Token/computed-style test helpers — mount a component, assert `getComputedStyle` for radii/borders/frost

*Note: `backdrop-filter` compositing (frost 78% white + 14px blur) cannot be reliably asserted in jsdom — see Manual-Only Verifications.*

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Frost backdrop blur renders visually | DSYS-03 | jsdom cannot composite `backdrop-filter` | Load `/specimen` in a real browser; confirm frost panel shows 78% white + 14px blur over content behind it |
| Fonts render in spec roles | DSYS-02 | jsdom does not load/rasterize webfonts | Load `/specimen`; confirm Geist (body/headings), Geist Mono (data/code), Oswald (uppercase annotation captions) render |
| Achromatic-except-Signal-Red discipline | DSYS-01 | Visual audit across all specimen surfaces | Load `/specimen`; confirm the only chromatic hue anywhere is Signal Red `#e7000b` |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < {N}s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
