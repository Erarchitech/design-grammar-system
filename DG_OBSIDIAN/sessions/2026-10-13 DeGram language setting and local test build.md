---
tags: [session, degram, phase-1308, language]
date: 2026-10-13
---
# DeGram language setting and local test build

## Outcome

Plan 1308-21 is implemented and locally committed in the DeGram component (`c476c236`, branch `degram/phase-1308`) but remains **partial for acceptance**. Settings → Appearance → Language is the sole language switch in DeGram: «Русский» / «English». The open full DG host page receives `#degram-lang=ru|en` in place; subsequent full loads use the latest `&lang=`. An unsupported stored DeGram locale resolves to English. The IPC queue now serializes the asynchronous locale signal with navigation. The stock Hermes switcher remains unchanged.

The Russian overlay was expanded and a D-54 completeness test was added. The owner clarified that Profiles, Skills and Assistant are not DeGram pages, and chose **manual translation review in the app** rather than a mandatory green D-54 Vitest test. Do not treat that automated criterion or live behavior as accepted yet. Details and checks: `.planning/phases/1308-dg-web-ui/1308-21-SUMMARY.md`.

## Verification and local build

- Focused UI tests: 22/22 passed; focused Electron tests: 86/86 passed. Both renderer and Electron TypeScript checks exited 0, without dependency installation.
- RU completeness plus stock catalog suite: 65 passed / 1 failed. The first failing assertion on the committed tree is `settings.plugins.installModal.repoPlaceholder` (an unchanged literal GitHub URL). The completeness gate is open. Exploratory allowances exposed further failures including an unchanged `missingEnv` argument gap and `settings.notifications.testTitle`; they were reverted before commit, so the final run does not enumerate every gap.
- After the owner authorized a build and copy of a checked local payload, compiled current Desktop sources and produced an **unsigned, unpacked local test app** at `apps/degram/apps/desktop/release/win-unpacked/DeGram.exe`. The payload was copied from `D:\dgb\src\apps\desktop\build\agent-payload`, originating at component `7edf519c`; intervening source changes were Desktop-only. The first after-pack attempt failed without `HERMES_PYTHON`, the rerun with the prepared local interpreter passed. The packaged app's renderer/main files matched current build outputs and its stamp was dirty at pre-commit HEAD `5f1d3aa8`. Final session-save edits occurred after packaging, so the executable is a test candidate, not evidence of the final commit's exact packaged contents. It has not been launched, installed or live-tested.
- `workspace.py verify` reports only the known gitlink mismatch; 1308-17 records the temporary single-check waiver. The framework gitlink was not bumped and the public component fork was not pushed.

## Resume

1. Owner tests the unpacked build in the isolated DeGram runtime and reviews DeGram chrome, embedded DG switching and visible Russian copy. No live PASS is recorded until then.
2. Resolve or explicitly accept the remaining D-54 completeness failure before calling plan 21 complete; check any translation edits against the packaged app by rebuilding if necessary.
3. Keep Phase 1308 and publication gates open. Plan 1308-18 needs separate push/gitlink authorization; do not attach an unpushed child commit to the framework.

The extensive staged and unstaged framework planning/Phase 1309 work predates this session's checkpoint and is not part of its commit. No generated `dist`, `release` or copied payload is committed.
