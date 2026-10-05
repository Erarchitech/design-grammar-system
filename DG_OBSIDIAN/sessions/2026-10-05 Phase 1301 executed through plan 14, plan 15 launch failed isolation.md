---
tags: [session, DeGram, v13.0, phase-1301, gsd, execute-phase]
date: 2026-10-05
---

# Session: 2026-10-05 — Phase 1301 executed through plan 14; plan 15 launch failed isolation

## Goal

Run `/gsd-execute-phase 1301` (Рабочий клиент и безопасное чтение, DGCL-01..07): 16 plans in 8 waves, sequential `gsd-executor` agents on the main tree (worktrees off), each result re-verified by the orchestrator.

## What Was Done

Waves 1–6 (plans 01–14) completed and independently re-run; plan 15 is **PARTIAL**; plan 16 blocked. No DGCL ID is marked complete (every plan recorded `requirements-partial`).

| Plan | Result | Repo / commits |
|---|---|---|
| 01 | already done earlier (`#degram` web slice) | — |
| 02 | env restored (`npm ci`, `.venv`), baseline narrowed, fonts hash-recorded | framework `c88a337`, `566a498` |
| 03 | public fork `Erarchitech/revit-mcp-server`, submodule `apps/revit-mcp` pinned `74a8ddca`, `workspace.py verify` covers 2 components (14 tests) | framework `b41afdf`, `32f6907` |
| 05 | project→company map, delegated `dgd_` token (900 s, session-bound revocation) | `a5fce25`, `1e2587b`, `c6562fb` |
| 06 | GH bridge `get_document_identity`, bounded UI wait → BUSY (30/30, build 0 warnings) | `98e916a`, `9a76729`, `637ae39` |
| 04 | `degram` variant: own identity, fixed home `%LOCALAPPDATA%\DeGram\home`, HOME_OVERLAP fail-closed, updater off | child `7c9e6145`, `a05e4894`; fw `bba2fac` |
| 07 | Revit adapter read-only on both layers, loopback-only, identity-pinned (110 passed) | revit child `b6cdde8`, `937384f`; fw `cc05f70` |
| 08 | user-scoped streaming relay + policy + consent, nginx streaming | `66aab07`, `e597784`, `55f026b`, `5a8f19f` |
| 09 | Speckle geometry proxy, token removed from browser payload | `4c2c96d`, `306b3a8`, `23107b4` |
| 10 | agent lockdown: in-memory credential, pinned relay provider, closed tools/RPC/REST, per-scope profiles (212 passed) | child `d2d819e0`, `b1e09d52`, `c27f31cd`; fw `0c506e5` |
| 11 | CAD reads (GH + Revit MCP stdio), Context composer, consent, cancel | child `95d301a4`, `7ae4fb6a`, `50cc2246`, flake fix `7fdb4aae`; fw `ca735d9`, `57bf64a`, `994b2b9` |
| 12 | Electron main: partition sign-in, DG view, token mint/renew/revoke | child `a5f81317`, `0be0679b`, `8f681b7b`, `4f7eb136`; fw `1417611` |
| 13 | renderer shell, DG theme, fonts, hidden surfaces | child `30533c10`, `e709572f`, `e2c04d24`, `955215a3`; fw `1e954a2` |
| 14 | document picker, Context card, consent, stop, named failures | child `e230b056`, `0ee2d12f`; fw `b54b18e` |
| 15 | installer built, protocol written, **launch failed isolation, nothing pushed** | child `6e2b4889`, `386bd704`, `910a060d`; fw `c505dc7` |

Orchestrator checks beyond the agent reports: re-ran each plan's key suites (data-service boundary/route/matrix suites 900–1900 passed per plan; `tests/degram` 333; `electron/degram` 158; ui `src/degram` 131; typecheck exit 0), and for plan 13 proved the 3 ui failures (`voice-prefs` ×2, `cron-detail`) pre-exist at the pin by reverting `src/i18n` to `8b66a510` and re-running (same 3 failures), then restored from HEAD.

## Decisions Made (owner)

- Plan 02 gate: **authorize-all** (npm ci, `.venv`, local branch `degram/phase-1301`, local child commits), Cyrillic font subsets **granted**; plan 03 gate: **authorize** (public fork, submodule, `uv sync`, local branch).
- Baseline narrowed (2026-10-05): vitest `electron` full; pytest only `tests/hermes_cli` + `tests/tui_gateway` with a 15 min limit; `tests/tools` not captured (targeted later).
- Plan 15 gate: **all (a)–(d)** plus NSIS toolset acquisition. Outcome below.
- See [[knowledge/decisions/DeGram Phase 1301 execution authorizations and narrowed baseline|decision note]].

## Critical Finding — plan 15 launch

The one authorized launch of the built installer's app ran as **stock Hermes Desktop**, not DeGram, and attached to the owner's live Hermes. See [[knowledge/debugging/Packaged DeGram ignored the degram variant and attached to the live Hermes|debugging note]]. Agent stopped before push/gitlink bump, per the isolation rule. Nothing pushed; `ls-remote` empty on both forks; gitlinks still `8b66a510` / `74a8ddca`.

## Other Findings / Fixes

- Plan 11 flaky test (GH 30 s deadline clock) fixed in the test: [[knowledge/debugging/GH deadline test patched the clock only after the first request|note]].
- Plan 10 bug fixed in plan 11: Revit tool allowlist pattern `mcp_revit_*` vs real `mcp__revit__*`.
- Plan 14 bug fixed: nothing subscribed to gateway turn events (requests would stay `streaming`).
- Revit adapter needs an interpreter with `mcp` 1.x; payload is CPython 3.14 and `mcp` 1.9.0 has no cp314 wheel for `pydantic-core` → protocol runs `uv sync --frozen --python 3.13` next to `resources\revit-mcp`.
- `workspace.py verify` reports "gitlink does not match component HEAD" for both children until plan 15 bumps — expected, not worked around.
- Two agents were cut off by account session limits (plans 10 and 13/14); resumed or re-run with state verified on disk first.

## State at Save

- Framework `master` has all phase docs committed (HEAD before this save: `c505dc7`; two foreign commits `c93d0c6`, `2c95013` from the v12 test session sit in between).
- Child branches `degram/phase-1301` exist **locally only** (apps/degram at `910a060d`, apps/revit-mcp at `937384f`).
- Installer `D:\dgb\src\apps\desktop\release\DeGram-Setup-0.0.0.exe` (SHA-256 `46845872fa2646e1ec30935e42f29dcbe9cae99df6783d0abda5612192d4b13f`, built from `386bd704`, **pre-fix: do not launch or distribute**). Evidence and listings in `D:\dgb`.
- Housekeeping not done: 8 untracked pytest artifacts in `apps/degram` root; undeletable empty `.git/modules/degram/worktrees/dgp-t`; `%APPDATA%\HermesBundledCommit386bd70` (from the failed launch).

## Unverified

- Whether the Hermes changes (22 modified, 10 created, `owner-backfill` stamping 11 session rows) were caused by the launch — strong timing correlation, not proven; three `cache\uv` entries may come from an unscrubbed `npm run payload`.
- Live DG/CAD/relay behaviour, nginx streaming, Electron-only paths (`WebContentsView`, `net.request`, focus/cookie events) — only fakes and typecheck.

## Next

1. Owner reviews the Hermes impact (listings in `D:\dgb`).
2. Rebuild from `910a060d` (≈40 min, 22 GB on D:); identity gate on `app.asar.unpacked\dist\electron-main.mjs` (`com.erarchitech.degram`).
3. Second launch only with Hermes Desktop closed or `HERMES_HOME` removed (and `ELECTRON_RUN_AS_NODE` unset); owner authorization for the second launch.
4. Then push both branches (public forks) and bump gitlinks → `workspace.py verify` green → plan 16 live acceptance (needs Docker/paid inference/live CAD decisions).
5. Decide open findings: sign-out entry point; ungated profile switcher / rail / shared-metrics consent; stock resubmit/queue/steer bypassing the Context card; window title; payload size (5.9 GB).
