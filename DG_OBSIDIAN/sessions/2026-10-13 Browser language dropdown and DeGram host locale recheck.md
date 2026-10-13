---
tags: [session, ui-v2, degram, i18n, phase-1308]
date: 2026-10-13
---

# Browser language dropdown and DeGram host locale recheck

## Outcome

During Phase 1308 UAT the owner requested a global Русский / English dropdown in the upper-right of DG Web UI **only in a normal browser**. Within DeGram, Settings → Appearance → Language remains the single control; the owner also reported that switching it did not translate the embedded DG page. This amends D-50..D-54: [[knowledge/decisions/Interface language is switched only in DeGram settings, Russian and English only (D-50..D-54)]]. The affected context, UI spec and plan 1308-21 were amended narrowly.

The browser dropdown now sits above the screen layers. `ui-v2/src/i18n/index.js` validates and persists `dgv2_lang`, preferring that choice over the primary browser language on subsequent loads, and `auth.js` preserves it across tenant-data cleanup. The host mode ignores that preference, hides the dropdown, and accepts only DeGram's `#degram-lang=ru|en` display signal. Tests cover choice, persistence, invalid/storage-blocked values, sign-out retention and host isolation. The component source in `apps/degram` was not changed during this session.

The component's existing committed locale path (Settings → runtime store → renderer bridge → Electron `dg-view.ts` → host-page fragment/query) was reviewed, but **the reported failure in an installed DeGram application was not reproduced or proved fixed end-to-end**. Offline Chromium demonstrates that the current DG source responds to a simulated host fragment on a mounted landing and connector screen, not that the installed app delivers the fragment or serves the current bundle. Live owner acceptance remains open.

## Verification

- `node ui-v2/tests/run-host-centre.mjs`: 7/7 assertions passed at each of two measured sizes (1278×799, 898×699); the harness's expected project-summary and run requests were updated when navigating back to the landing.
- `npm --prefix ui-v2 test`: 286 passed, 0 failed. `npm --prefix ui-v2 run build`: passed (existing large-chunk warning).
- `python tools/degram/workspace.py verify`: component HEAD and staged framework gitlink both `c476c236ad04be8aa28f42410ed20f2e1372858e`; the same commit was confirmed on the fork's `degram/phase-1308` branch after the owner's push. No child source was modified.
- The GSD `1308-21-PLAN.md` frontmatter parses with LF endings, 11 truths, 2 prohibitions and 2 artifacts.
- Focused DeGram Electron tests: 86 passed. Two renderer suites could not start because local `babel-plugin-react-compiler` was absent; no package was installed. The earlier D-54 RU-completeness failure described in [[sessions/2026-10-13 DeGram language setting and local test build]] remains open.
- `graphify update .` ran, creating many generated changes in `graphify-out/`; these were not included in the session commit. Pre-existing planning and UI evidence files were also left untouched.

## Resume

Check the installed DeGram Settings-to-WebContentsView path against a current served DG bundle with fresh authorization for any Desktop launch or live-service rebuild. First add a regression at whichever link actually fails. Visually check the browser dropdown at phone width and on other screens. Do not mark the embedded-language UAT, D-54 completeness or Phase 1308 complete on the offline simulated-host result alone. No live deployment, Desktop launch or new fork push occurred in this session.
