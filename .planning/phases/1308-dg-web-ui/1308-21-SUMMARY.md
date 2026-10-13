---
phase: 1308-dg-web-ui
plan: "21"
subsystem: degram-language
status: partial
completed: null
requirements-completed: []
key-files:
  modified:
    - apps/degram/apps/desktop/electron/degram/dg-view.ts
    - apps/degram/apps/desktop/electron/degram/ipc.ts
    - apps/degram/apps/desktop/src/components/language-switcher.tsx
    - apps/degram/apps/desktop/src/degram/locale-config.ts
    - apps/degram/apps/desktop/src/i18n/ru.ts
  created:
    - apps/degram/apps/desktop/src/degram/ru-catalog-completeness.test.ts
---

# Plan 1308-21: DeGram language setting — partial

## Implemented

- DeGram's existing Settings → Appearance → Language switcher lists only «Русский» and «English» in that order, without search. The stock variant retains its full searchable catalog. An unsupported nonempty stored DeGram locale resolves to English; an absent/empty value keeps the first-run path.
- Electron accepts only `#degram-lang=ru|en`. Changing the locale sends that fragment to the loaded full DG host page without a reload; the next full page load, including a reload after a change, uses the current `&lang=`. IPC queues the asynchronous locale signal with other view tasks; the original plan did not anticipate the necessary `ipc.ts` change.
- Expanded the Russian overlay and added a D-54 catalog completeness test. The owner explicitly chose in-app visual review over making that new test a blocking acceptance criterion. Profiles, Skills and Assistant are not DeGram pages and do not need translation or verification for this plan.
- Component commit: `c476c236ad04be8aa28f42410ed20f2e1372858e` on local branch `degram/phase-1308` (ten files, no push). Framework gitlink remains at the previously published component commit; do not bump it to this unpushed object.

## Checks and limits

- `npx --no-install vitest run --project ui src/components/language-switcher.test.tsx src/degram/locale-config.test.tsx src/degram/sidebar.test.tsx`: **22/22 pass**.
- `npx --no-install vitest run --project electron electron/degram/dg-view.test.ts electron/degram/ipc.test.ts`: **86/86 pass**.
- `npx --no-install tsc -p . --noEmit` and `npx --no-install tsc -p tsconfig.electron.json --noEmit`: both exited 0. No package installation.
- `npx --no-install vitest run --project ui src/degram/ru-catalog-completeness.test.ts src/i18n/catalog-completeness.test.ts`: **1 failed / 65 passed**. The remaining failing D-54 case is `settings.notifications.testTitle` (`Hermes` equals English). This is a deferred automated criterion, not a pass; the owner will inspect the actual DeGram screens. The previously encountered `missingEnv` placeholder gap was left unchanged rather than claiming a green completeness gate.
- `python tools/degram/workspace.py verify` exits 1 solely reporting `Submodule gitlink does not match the selected component HEAD`, under the narrow waiver documented in 1308-17. This is not a green preflight and does not waive other checks.

## Local test build

- After separate owner authorization to build and to copy a previously verified local agent payload, compiled the current dirty Desktop renderer/main/preload and packaged an unsigned, unpacked `win32-x64` application at `apps/degram/apps/desktop/release/win-unpacked/DeGram.exe`. The copied payload comes from local component commit `7edf519cd2c3e98f8274f2d45aa2926d8a30c60b`; changes since then are Desktop-only, and packaging rehashed its payload tools. The packaged app has the current dirty stamp at `5f1d3aa8` (the source HEAD at build time, before the component commit). `app.asar` renderer manifest, HTML and Electron main hashes matched the current compiled output; after-pack passed. The first package attempt failed for unset `HERMES_PYTHON`; the rerun with the prepared local interpreter exited 0. This is not an installer and was not launched or installed. Signing variables were unset.
- The build predates the later non-functional test adjustments and translation edit/revert during the session-save checks; it must not be described as a verified package of the final committed tree. No live language observation, Docker deployment, fork push or gitlink bump occurred.

## Next gate

The owner runs the unpacked executable in the permitted isolated profile and reviews the DeGram/DG language switch and translation in the actual interface. Keep WEBUI acceptance and Phase 1308 closure open until that observation and the remaining rollout gates. Plan 1308-18 handles publication and framework gitlink alignment only with its own authorization.
