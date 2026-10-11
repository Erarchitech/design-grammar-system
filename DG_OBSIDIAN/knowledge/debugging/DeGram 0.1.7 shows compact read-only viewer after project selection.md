---
tags: [debugging, degram, phase-1301, live-uat]
date: 2026-10-11
---

# DeGram 0.1.7 shows compact read-only viewer after project selection

## Symptom and evidence

On PC1, the owner launched installed DeGram 0.1.7, signed in to DG and selected `v12-hexagonal-facade-01`. The first screenshot showed `DEGRAM`, a read-only workspace header, project buttons and `Select a project`. After clicking a project, the second screenshot showed a selected project and a large circular read-only graph, but no chat, composer or DeGram navigation. User observation is authoritative for this live check; the 0.1.7 project-open UAT is **blocked/failing**, not accepted.

Images in the Hermes composer (private local paths, not repository attachments): `composer_2026-10-11_07-16-11-903_85cb81.png`, `composer_2026-10-11_07-17-51-777_fd379e.png`.

Read-only checks: `%LOCALAPPDATA%\Programs\DeGram\DeGram.exe` reports ProductVersion `0.1.7.0`; installed `resources\app.asar` SHA-256 `B6C57C9E7A9647669D54895B0D7593F038EB64F22D0B95B930B7711A0D30C335` matches `D:\dgb\src\apps\desktop\release\win-unpacked\resources\app.asar`. Thus a different/stale package is not supported by this comparison. The installed backend reached ready in `desktop.log`. One earlier launch logged `DG unreachable during /auth/me`; a later read-only GET of `http://localhost:8080/` returned HTTP 200. This does not establish the cause of the UI mismatch.

## Code paths to investigate

- `ui-v2/src/degram/DeGramWorkspace.jsx` is the compact read-only graph: its `select()` fetches a graph and renders `ReadOnlyGraph`, not a chat.
- `apps/degram/apps/desktop/electron/degram/dg-view.ts` distinguishes graph mode `/#degram` and full mode `/?host=degram` (`dgUrlFor`, lines 130–132); `showSignIn()` loads full host mode, while `showDg()` loads the current mode, initially `graph`.
- `apps/degram/apps/desktop/src/degram/degram-gate.tsx` holds the native DeGram shell behind its first-screen gate until the bridge reports a ready scope. `ui-v2/src/lib/hostMode.js` announces project selection only in `?host=degram` mode. These facts suggest a route/mode or shell-gate mismatch, **not yet a proven root cause**.

## Next diagnostic step

Resume with a tight repro of the owner's exact symptom: inspect current Electron bridge state (auth/scope/page/mode), actual embedded-view URL, renderer gate and network/console after project click; compare expected `/?host=degram` announcement against actual `/#degram`. Trace why the shell is absent before changing code. Avoid launching/resetting/reinstalling automatically or exposing auth cookies/tokens. Re-run `python tools/degram/workspace.py verify` before any component work. Do not mark other 0.1.7 live checks passed.
