---
phase: 1301-rabochiy-klient-i-bezopasnoe-chtenie
plan: 14
subsystem: degram-desktop-renderer-chat
tags: [degram, renderer, document-picker, bridge-status, context-card, whole-definition-consent, policy-deny, request-lifecycle, stop, outcome-copy, composer-seam, tdd]
requires: ["1301-11", "1301-13"]
provides:
  - "src/degram/use-degram-gateway.ts: typed wrapper over the renderer JSON-RPC client for degram.documents.list/pin, degram.context.preview/send/cancel (every answer normalized once; status error becomes an OutcomeInfo; DegramOutcomeError for a refused send); turn events follow the $gateway atom"
  - "src/degram/documents-store.ts: scope-tagged cache of the bridges (per-bridge loading, optimistic pin with rollback, mismatch, unpin); a reader of another scope sees an empty cache, so a project change empties strip and card in the same render"
  - "src/degram/document-picker.tsx + bridge-status.ts: Popover + Command variant menu grouped by bridge, no auto-pin, unsaved and no-identity rows, neutral notice row per unavailable bridge, search above 7 rows, middle-ellipsized paths; state -> dot tone + copy"
  - "src/degram/context-card.tsx: always-expanded summary line, exact-payload LogView, warn badges, inline read failure with Retry read, SegmentedControl scope, whole-definition ConfirmDialog, policy-deny banner (no confirm), FailureBanner with manual Retry request"
  - "src/degram/request-lifecycle.ts: idle > previewing > ready > streaming > done | interrupted | failed; composerGate (fails closed), takeSendPlan/markSent, stopRequest, retryRequest (click only), startTurnEventSync"
  - "src/degram/outcome-copy.ts: copyKeyForOutcome total over the 23-code vocabulary (machine-checked against spec/degram/OPERATIONAL-OUTCOMES.md) plus seven agent/relay codes; parseFailureText finds the code anywhere in wrapped stock text; FORWARDED_TO_MAIN equals AGENT_OUTCOME_CODES"
  - "src/degram/composer-seam.ts: the only stock touch points (gate middleware, degramPromptSubmit, degramOnStop, useDegramSendBlocked), each a no-op outside variant degram"
  - "sign-out-confirm.tsx (requestDegramSignOut), interrupted-badge.tsx, connected-scope-strip.tsx (strip fed with document + both bridges)"
  - "Backend (component): degram.documents.list takes an optional app so each bridge loads on its own (commit e230b056)"
affects: [1301-15, 1301-16]
tech-stack:
  added: []
  patterns:
    - "Authority: the agent owns the payload and the turn; the renderer stores are scope-tagged caches, and an answer for a stale preview id or scope is dropped"
    - "One entry into streaming: the user's Send. A preview is a read; the stock submit path reports markSent; nothing (timer, retry, scope change) sends"
    - "Stock seams are one line each and pinned by a source-audit test, because the upstream shell cannot be rendered offline"
key-files:
  created:
    - apps/degram/apps/desktop/src/degram/{use-degram-gateway.ts,documents-store.ts,document-picker.tsx,bridge-status.ts,context-card.tsx,request-lifecycle.ts,outcome-copy.ts,composer-seam.ts,connected-scope-strip.tsx,sign-out-confirm.tsx,interrupted-badge.tsx,chat.test.tsx}
  modified:
    - apps/degram/apps/desktop/src/degram/{scope-strip.tsx,shell-host.tsx,host-actions.ts,i18n.ts,hidden-surfaces.ts,hidden-surfaces.test.tsx}
    - apps/degram/apps/desktop/src/app/chat/composer/index.tsx
    - apps/degram/apps/desktop/src/app/chat/composer/status-stack/index.tsx
    - apps/degram/apps/desktop/src/app/session/hooks/use-prompt-actions/{index.ts,submit.ts}
    - apps/degram/apps/desktop/src/components/assistant-ui/thread/assistant-message.tsx
    - apps/degram/locales/_keys.desktop.json
    - apps/degram/{degram_variant/documents.py,tui_gateway/methods_degram.py,tui_gateway/contracts/degram.py,apps/shared/src/gateway-contract.generated.ts,apps/shared/src/gateway-contract.openrpc.json,tests/degram/test_context_composer.py}
key-decisions:
  - "Stale preview or scope never sends: Send is blocked (stale / previewing / read-failed / mismatch) while a document is pinned, and the gate fails closed on any exception; with no pinned document the stock path runs and the request carries project data only"
  - "The consent a user gives belongs to the payload on the card: if the scope, document or preview changed while the whole-definition dialog was open, the send is cancelled"
  - "The stock transcript Retry (and scheduled retry) is hidden in variant degram (surface id stock-error-retry): it would resubmit without the disclosed context. The banner's Retry request re-reads the selection first, then sends through the composer's own submit, so gate, consent and transcript behave as for a typed message"
  - "Whole-definition is offered only for a Grasshopper pin (the agent answers SCOPE_NOT_SUPPORTED for Revit)"
  - "The sign-out confirmation is catalogued and wired (requestDegramSignOut) but no visible sign-out control was invented: UI-SPEC specifies the dialog, not the control"
  - "Turn events are read from the $gateway atom (republished on every activation), not from activeGateway(), so the machine rebinds on a gateway swap"
metrics:
  duration: two sessions (the first cut off by an API rate limit after the backend commit; this one verified the work on disk, found and fixed the missing live event binding, and committed)
  completed: 2026-10-05
requirements-completed: []
requirements-partial: [DGCL-02, DGCL-04, DGCL-06, DGCL-07]  # picker, card, consent, deny, stop and named failures proven offline in jsdom with a scripted gateway; live Revit/Grasshopper/relay runs and pixels are plan 16
status: complete
---

# Phase 1301 Plan 14: DeGram chat surfaces Summary

The DeGram chat now shows what it will send before it sends it: a bridge-grouped document picker with explicit pinning, an always-visible Context card with the exact payload one caret away, whole-definition consent that opens only at Send, a policy-deny banner that can never be confirmed, a Stop that paints in the same frame, and failures that name their cause in the user's language and offer one manual retry. Everything is proven offline with a scripted gateway; nothing was launched.

## Authorization and boundaries

Per the orchestrator brief: local commits in `apps/degram` on `degram/phase-1301` only. No push, no `hermes update`, no Desktop launch, build, dev server or packaging, no Docker, no write to `%LOCALAPPDATA%\hermes` or the Hermes profile, no new package or dependency, no network, no real LLM or live DG/CAD call, `.secrets` untouched. No gitlink bump; `apps/degram` and `apps/revit-mcp` not staged in the framework. `workspace.py verify` reports gitlink != child HEAD, expected until plan 15 (not worked around). The 8 untracked hermes-pytest artifacts and `.git/modules/degram/worktrees/dgp-t` were not touched (each component commit prints the harmless `dgp-t: Permission denied`). No worktree was created.

## Commits

Component repo `apps/degram`, branch `degram/phase-1301` (committing repository: component), base `955215a3`:

| Task | Commit | Message |
|---|---|---|
| backend seam | `e230b056` | feat(1301-14): degram.documents.list takes an optional app so the picker loads each bridge on its own |
| 1 + 2 | `0ee2d12f` | feat(1301-14): document picker, Context card, consent, stop and named failures for the DeGram chat |

Framework repo (master): the `docs(1301-14)` commit with this SUMMARY, STATE.md and ROADMAP.md. No deletions in any commit.

Why Task 1 and Task 2 are one commit: the first (interrupted) session wrote both tasks in one working tree before committing anything but the backend change, and the pieces are entangled (the card imports the lifecycle and outcome copy, `i18n.ts` and `chat.test.tsx` carry both). Splitting after the fact would have produced an intermediate commit that does not type-check. The plan's per-task atomicity is not met; the one commit type-checks and passes its tests as a whole.

## What was built

**Backend seam (`e230b056`).** `degram.documents.list` accepts an optional `app`, so the picker reads Revit and Grasshopper independently (a slow Revit does not hold the Grasshopper rows). Contract, regenerated TS and OpenRPC, and a composer test.

**Task 1 (picker, strip, card).** `documents-store.ts` is a cache scoped by company, project and scope epoch; a `pinVersion` stops a list read that predates a pin from overwriting it; a pin is painted optimistically and rolled back visibly on refusal. `document-picker.tsx`: groups per bridge with sticky headings, a pending group is one «Проверка» row with the glyph spinner while the other group stays selectable, an off/busy/setup-incomplete bridge is one neutral notice row with its diagnostic, an unsaved row reads «Не сохранён», a row without identity is disabled with «Нельзя закрепить…», a single document is never pinned for the user, search appears above 7 rows, long Windows paths middle-ellipsize with the drive and file name kept and the full path in the tip. `connected-scope-strip.tsx` feeds `ScopeStrip` (document segment with the accent dot only while pinned and not mismatched; both bridge segments neutral or ink, never red). `context-card.tsx` shows `project · document · N объектов · M параметров · R правил · F фрагментов · size` with locale plurals, zero counts kept, spinner while a read is in flight, warn badges `Сокращено: kept из total` and `Нет данных: …`, an inline read failure with «Повторить чтение», and a caret that reveals `preview.payload` exactly as returned.

**Task 2 (consent, deny, stop, failures).** `request-lifecycle.ts` is the state machine; `composerGate` is registered as the last composer middleware and, with a pinned document, requires a ready, unused preview, opens the whole-definition `ConfirmDialog` (objects, parameters, document, size) when the preview requires consent, and arms the final text. `degramPromptSubmit` replaces the one stock `prompt.submit` call: an armed send goes through `degram.context.send` with the consent flag, so the model receives the payload the card showed. Stop: `degramOnStop` and `stopActiveResponse` clear the request state synchronously and send `degram.context.cancel` (naming the read in flight) and `session.interrupt`, once each; the partial message keeps the muted «Прервано» badge. `outcome-copy.ts` maps every code of the operational vocabulary to a copy key; failure text carrying the code anywhere (including inside the stock `CREDENTIALS_*` wrapper sentence) shows DeGram copy, never the stock sentence. Credential and access codes are forwarded to Electron main through `reportOutcome` (exactly the codes main accepts). Retry is a click; the fake-timer test advances 10 minutes with zero sends.

## TDD

- **Backend seam:** test added in `test_context_composer.py` with the change (first session).
- **Tasks 1 and 2:** the first session's tests-first order cannot be confirmed from disk. Evidence that the tests are real: (a) mutation check, `if (preview.requiresConsent)` disabled -> 3 tests fail (both consent tests and the policy-deny test), restored; (b) mutation `isRetryable` always true -> no failure, an equivalent mutant (the deny branch is taken before `isRetryable` is read), restored.
- **Live event binding (this session):** RED observed first: the new gateway-follow test and the `shell-host.tsx` source-audit row failed (`startTurnEventSync` did not exist, 2 failed / 68 passed), then GREEN (131 in `src/degram`).

## Verification

All commands from `apps\degram\apps\desktop`; nothing launched.

| Check | Result |
|---|---|
| `npx vitest run --project ui src/degram` | 4 files, **131 passed** (chat 70, shell 30, hidden-surfaces 23, presets-fonts 8; was 60 before this plan) |
| touched areas `--project ui src/degram src/i18n src/app/chat src/app/session src/components/assistant-ui src/app/shell src/store` | 572 files, 5684 tests: 5682 passed, 2 failed (`store/voice-prefs.test.ts` x2, both baseline) |
| Full `npx vitest run --project ui` (once) | 1184 files, 10676 tests: 10656 passed, 17 skipped, **3 failed**: `voice-prefs` x2 and `cron-detail` x1, exactly the baseline set. Two further files (`plugins/hermes-bots/bot-delete.test.ts`, `hidden-bots.test.ts`) failed with `Hook timed out in 60000ms` (9 + 8 tests skipped) under the 700 s load; re-run alone they pass 17/17, they import nothing touched here |
| `npm run typecheck` (src, electron, e2e, builder config) | exit 0, no output |
| eslint on all 23 touched files | 0 errors; 1 pre-existing warning (`use-prompt-actions/index.ts:656`, exhaustive-deps, not my lines) |
| prettier --check | clean |
| `npm run i18n:keys` then `vitest run scripts/i18n-keys.test.mjs` | key list regenerated (committed), 2 of 2 pass |
| `tests/degram/test_context_composer.py` + `tests/tui_gateway/contracts` (Python, `run_tests.sh`) | 3 files, 39 passed, 0 failed (generated TS/OpenRPC fresh) |
| Full `--project electron` | not run: no electron or `electron/degram` file changed in this plan (the only cross-import is the type/const read of `AGENT_OUTCOME_CODES` in a test) |

## Deviations from Plan

**1. [Rule 1 - Bug] Turn events were never bound in the live shell.** The first session defined `bindTurnEvents` and tested the machine by calling `handleTurnEvent` directly, but nothing subscribed to the gateway, so in the real app a request would have stayed `streaming` forever (no done, interrupted or failed; no failure banner, no `reportOutcome`). Fixed: `startTurnEventSync()` (follows the `$gateway` atom, rebinds on a swap, unbinds on stop) mounted once in `DegramShellHost`; event subscription and identity now read `$gateway` instead of `activeGateway()`. Test-first as above. Commit `0ee2d12f`.

**2. [Plan interpretation] Backend change inside a renderer plan.** `degram.documents.list` gained an optional `app` (commit `e230b056`) so each bridge group loads independently as UI-SPEC E3 requires; the plan lists renderer files only. Additive and covered by a test and the regenerated contract.

**3. [Plan interpretation] More files than `files_modified`:** `documents-store.ts`, `composer-seam.ts`, `connected-scope-strip.tsx`, `interrupted-badge.tsx`, `sign-out-confirm.tsx`, plus one-line seams in the stock composer, status stack, `use-prompt-actions` (index and submit) and `assistant-message.tsx`, and the new hidden-surface id `stock-error-retry`.

**4. [Plan interpretation] Tasks 1 and 2 share one commit** (see Commits).

**5. [Plan interpretation] Sign-out has no control.** UI-SPEC gives the dialog copy but no control; `requestDegramSignOut()` is the entry point for any future menu, command or tray item.

## Findings for later plans

- **Plan 15:** (a) the sign-out confirmation has no visible entry point; decide where it lives. (b) Still open from plan 13: profile switcher, profile rail and shared-metrics consent are not gated. (c) The stock error card's Retry is hidden by id `stock-error-retry`; any other stock surface that resubmits a turn (Retry on a user message, queue send, steer) bypasses the gate and goes through plain `prompt.submit` without the card's payload. The 30 s arming TTL and the text match keep a stale arming from leaking, but a steered or queued message is sent without a document snapshot by design: review this against D-17. (d) `FORWARDED_TO_MAIN` is asserted equal to `AGENT_OUTCOME_CODES` by a test, so adding a code on either side fails the suite. (e) The gitlink bump must carry `0ee2d12f` and `e230b056`.
- **Plan 16 (live):** check with a real Revit and Grasshopper: per-bridge loading order, that an unsaved Revit document is listed unpinnable only when it truly has no `creationGuid`, the focus re-read, Stop aborting a real bridge read, the wrapped stock failure text for each code (the parser matches the code anywhere, but real stock wording was only scripted), plural forms in the real ru catalog, payload LogView scroll hand-off, 900 px layout with a Cyrillic file name and the sticky group headings (UI-SPEC backstop rows), and that the composer stack never pushes the transcript off screen.

## Not verified (honest limits)

No pixels: nothing ran in Electron or a browser, so the three UI-SPEC "backstop" rows (E3 long Windows path at 900 px, E4 payload scroll hand-off, E1 strip collapse) are covered only by class and string assertions. The upstream shell (status stack, composer, transcript) cannot be rendered offline; each stock seam is pinned by a source-audit test, and the card, banner and gate are rendered and driven in isolation. No real gateway, bridge, relay or model.

## Known Stubs

None.

## Threat Flags

None beyond the register. T-1301-14-01 (user unaware of sent context): always-visible card, exact-payload LogView, payload-equality through `degram.context.send`. -02 (consent bypassing policy deny): the deny banner has no confirm and the mutation check proves the consent test bites. -03 (silent document switch): no auto-pin test, mismatch copy, manual reselect. -04 (retry storms): manual retry only, 10-minute fake-timer test with zero sends.

## Self-Check: PASSED

- FOUND (component, `apps/degram/apps/desktop/src/degram`): `use-degram-gateway.ts`, `documents-store.ts`, `document-picker.tsx`, `bridge-status.ts`, `context-card.tsx`, `request-lifecycle.ts`, `outcome-copy.ts`, `composer-seam.ts`, `connected-scope-strip.tsx`, `sign-out-confirm.tsx`, `interrupted-badge.tsx`, `chat.test.tsx`
- FOUND commits in the component repo on `degram/phase-1301`: `e230b056`, `0ee2d12f`; `git status` shows only the 8 known untracked pytest-artifact files
- Gitlink not bumped; `apps/degram` and `apps/revit-mcp` not staged in the framework; no deletions in any commit
