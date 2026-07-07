---
phase: 22-navigation-shell-landing-auth
plan: "22-01"
status: complete
completed: 2026-07-07
commits:
  - 00bed2a feat(22-01) landing particle-ring hero + inline auth
  - e461a7c feat(22-01) layered shell, fly transitions, chrome
duration: ~45min
---

# Summary 22-01: Navigation Shell, Landing and Auth

## What shipped

- **`landingEngine.js`** — the mockup's canvas engine ported: 10,400-particle ring (density 2) with gaussian peaks toward the three region anchors, leader lines + ring dots, hero title sampled from an offscreen Oswald render materialising from / dissolving into the cloud (forming 900ms / dissolving 620ms), region-label radial layout.
- **`LandingLayer.jsx`** — hero DOM, guest CTA ↔ member state (name, red status dot, "System initiated · {project|Select the project}", Sign out), rising frost auth card (login/register mode switch, inline Signal-Red errors, Cancel, Enter submits).
- **`auth.js`** — legacy-compatible client auth (`dg_users` salted SHA-256, `dg_current_user` session).
- **Shell** — four always-mounted layers with the 520ms scale+opacity fly transition; landing recedes at scale 1.6 toward the clicked callout (transform-origin from the engine's ring points); `ScreenHeader` chrome (← Back + title + mono subtitle) on placeholder Graph/Model/Projects screens; Escape returns to landing.

## Decisions / deviations

- **Engine-owned styling contract**: elements the engine animates per-frame carry CSS classes only — no React style props — so state re-renders never wipe animation values.
- **Zero-size self-heal**: embed contexts can report 0×0 at mount without a resize event; the engine re-measures every frame and rebuilds layout on change (found live in preview — canvas was 0×0 and `getImageData` would throw in `sampleHeroTargets`; also guarded).
- **Dark-mode toggle from the mockup dropped** — out of scope per REQUIREMENTS (V2 is deliberately the light reskin).
- **Full-name register** split into legacy `name`/`surname` fields to keep the `dg_users` schema intact.

## Verification results

All flows verified live in the preview browser: landing render (screenshot reviewed), auth card rise (opacity 1, labels fade), register → `dg_users`+session written → member state shown, sign out → guest CTA + session cleared, region navigation (landing scale 1.6 / origin at callout, target layer scale 1), chrome present, Escape + ← Back return with hero re-forming. `npm run build` clean.

## Requirements satisfied

NAV-01, NAV-02 (chrome on placeholders; carried by real screens in 23-25), LAND-01..03, AUTH-01..04.
