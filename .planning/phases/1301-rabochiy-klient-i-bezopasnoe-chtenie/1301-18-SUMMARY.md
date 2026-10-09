---
phase: 1301-rabochiy-klient-i-bezopasnoe-chtenie
plan: 18
subsystem: desktop-client
tags: [degram, gateway-route, scope, session-list, credentials, electron, react]

requires:
  - phase: 1301-17
    provides: pairing credential, scope controller (plan 12), composer gate and request lifecycle (plan 14)
provides:
  - "scope-route.ts: the chat's gateway route follows state.scope.profile on every scope switch and at boot (G-7, D-19)"
  - "Send guard: sendBlockedReason 'route-mismatch' and a hard ROUTE_MISMATCH refusal in degramPromptSubmit"
  - "Session lists wiped before the route moves, so nothing of the previous scope stays in «Сеансы» (G-3)"
  - "errors.credentialsMissing copy (en/ru) and one credential re-handoff per scope open on CREDENTIALS_MISSING (G-5)"
  - "Variant degram: no session.control.read, DEGRAM_LOCKED reads as unsupported, no /api/profiles refresh, no bot-relay timers (G-6)"
  - "1301-UI-SPEC.md gap-round amendment (copy rows + contracts for plans 18-21, D-29)"
affects: [1301-16, 1301-19, 1301-20, 1301-21, 1301-23, DGCL-02]

tech-stack:
  added: []
  patterns:
    - "scope-route.ts reads the route and the scope state it is handed and never the DeGram store, so the store can ask routeDisagreesWithScope without an import cycle"
    - "Each followScopeRoute call takes a ticket; an older call that finishes after a newer one returns 'superseded' and acts on nothing"
    - "Hooks that read module state through a plain function call carry 'use no memo' (React Compiler would memoize the call on its unrelated inputs)"

key-files:
  created:
    - apps/degram/apps/desktop/src/degram/scope-route.ts
    - apps/degram/apps/desktop/src/degram/scope-route.test.ts
  modified:
    - .planning/phases/1301-rabochiy-klient-i-bezopasnoe-chtenie/1301-UI-SPEC.md
    - apps/degram/apps/desktop/src/degram/use-degram-state.ts
    - apps/degram/apps/desktop/src/degram/shell-host.tsx
    - apps/degram/apps/desktop/src/degram/request-lifecycle.ts
    - apps/degram/apps/desktop/src/degram/composer-seam.ts
    - apps/degram/apps/desktop/src/degram/outcome-copy.ts
    - apps/degram/apps/desktop/src/degram/i18n.ts
    - apps/degram/apps/desktop/src/degram/shell.test.tsx
    - apps/degram/apps/desktop/src/degram/chat.test.tsx
    - apps/degram/apps/desktop/electron/degram/scope.ts
    - apps/degram/apps/desktop/electron/degram/scope.test.ts
    - apps/degram/apps/desktop/src/app/chat/composer/status-stack/index.tsx
    - apps/degram/apps/desktop/src/app/chat/composer/status-stack/session-control.test.tsx
    - apps/degram/apps/desktop/src/store/session-control.ts
    - apps/degram/apps/desktop/src/store/session-control.test.ts
    - apps/degram/apps/desktop/src/store/profile.ts
    - apps/degram/apps/desktop/src/store/profile-cache.test.ts
    - apps/degram/apps/desktop/src/plugins/hermes-bots/plugin.tsx
    - apps/degram/apps/desktop/src/plugins/hermes-bots/plugin-panes.test.tsx

key-decisions:
  - "DegramActions.startNewChat stays () => void; the shell host calls handleNewScope(state, opts, startNewChat), which moves the route first and opens the fresh chat only after it landed"
  - "The bots plugin reads window.hermesDesktop.degramEnabled instead of importing the app store: plugin bundles take no app-store imports"
  - "followScopeRoute always calls ensureGatewayProfile (its fast path is a no-op when the route truly agrees) so an atom that claims the profile over another socket is repaired"

patterns-established:
  - "A route restored at boot is replaced, not kept: first observation of a ready scope whose profile differs from the route fires once with fresh=false (no new chat)"

requirements-completed: [DGCL-02]

coverage:
  - id: D1
    description: "The renderer's gateway route equals the ready scope's profile before any chat, session list or send uses it, on a scope switch and at boot"
    requirement: "DGCL-02"
    verification:
      - kind: unit
        ref: "apps/degram/apps/desktop: src/degram/scope-route.test.ts (14), shell.test.tsx new-scope cases incl. boot restore"
        status: pass
      - kind: manual_procedural
        ref: "live recheck of UAT 2.4-2.7 and 6.1 on 0.1.6 (plan 16 Task 3)"
        status: unverified
    human_judgment: false
  - id: D2
    description: "A mismatched route disables Send and degramPromptSubmit refuses without calling prompt.submit or degram.context.send"
    requirement: "DGCL-02"
    verification:
      - kind: unit
        ref: "src/degram/chat.test.tsx 'route guard' (4 cases)"
        status: pass
    human_judgment: false
  - id: D3
    description: "CREDENTIALS_MISSING has its own copy and main re-hands the credential at most once per scope open"
    requirement: "DGCL-02"
    verification:
      - kind: unit
        ref: "electron/degram/scope.test.ts (49), src/degram/chat.test.tsx named failures"
        status: pass
    human_judgment: false
  - id: D4
    description: "Variant degram issues no session.control.read, treats DEGRAM_LOCKED as unsupported, and runs no /api/profiles refresh or relay timer"
    verification:
      - kind: unit
        ref: "src/store/session-control.test.ts, status-stack/session-control.test.tsx, store/profile-cache.test.ts, plugins/hermes-bots/plugin-panes.test.tsx"
        status: pass
      - kind: manual_procedural
        ref: "no locked-RPC error row and no 30 s retries in the 0.1.6 log (plan 16 Task 3)"
        status: unverified
    human_judgment: false

duration: ~1h 40m
completed: 2026-10-09
---

# Phase 1301 Plan 18: Renderer follows the scope profile Summary

**The chat now moves its gateway route onto the profile main opened for the ready scope (and replaces a route restored at boot), wipes the previous scope's sessions first, blocks Send while the two disagree, and names CREDENTIALS_MISSING honestly with one automatic credential re-handoff.**

## Performance

- **Completed:** 2026-10-09
- **Tasks:** 4/4 (Task 1 framework, Tasks 2-4 one component commit)
- **Execution:** sequential executor, no checkpoints

## Accomplishments

- `scope-route.ts`: `routeDisagreesWithScope`, `followScopeRoute` (wipe session lists, `ensureGatewayProfile`, `pinNewChatProfile`; outcomes `agreed | switched | failed | superseded`), `handleNewScope` (fresh chat only after the route landed), `startRouteReconcile` (brings the route back if the boot adopts the primary profile after the shell mounted).
- `startDegramSync` hands the state to the handler on every new ready epoch, and once at the first observation when the restored route disagrees (`fresh: false`, no new chat).
- Send guard: `sendBlockedReason()` returns `'route-mismatch'` first (pinned document or not), `composerGate` refuses, `degramPromptSubmit` throws `ROUTE_MISMATCH` before `markSent` and before any RPC; `useDegramSendBlocked` follows the route.
- Copy: `CREDENTIALS_MISSING -> errors.credentialsMissing` (en/ru, `{project}`), `DELEGATED_SESSION_ENDED` keeps `errors.sessionEnded`; `CREDENTIALS_MISSING` joined `FORWARDED_TO_MAIN` and `AGENT_OUTCOME_CODES`; scope controller re-mints and re-hands once per scope open (second report is a no-op).
- G-6: status stack skips `session.control.read` under degram, `DEGRAM_LOCKED` (code, `data.code` or message) reads as unsupported, `refreshProfiles`/`refreshActiveProfile` return without a request, bots plugin skips `startBotRelay()`.
- UI-SPEC: "Gap round 2026-10-09 (G-3..G-17, D-29)" section, four copy rows (credentials missing, sign-out item, document read blocked, documents segment), inventory rows point at it.

## Task Commits

1. Task 1 (framework): `b9f5946` docs(1301-18): UI-SPEC gap-round amendment
2. Tasks 2-4 (component, `degram/phase-1301`, local, not pushed): `d0d69691` fix(1301-18): chat follows the scope profile; credentials-missing copy; locked surfaces quiet (G-3, G-5, G-6, G-7)

The framework gitlink is not bumped and nothing was pushed: plan 23 pushes (owner) and bumps once for the whole gap round.

## Verification

- `npm run typecheck` (renderer, electron, e2e, builder config): pass.
- `vitest --project electron electron/degram`: 12 files, 196 tests pass.
- `vitest --project ui src/degram src/store src/app/chat src/plugins/hermes-bots`: 4354 pass, 3 fail, all unrelated (see Deferred Issues).
- eslint on all touched files: clean after `--fix` on import order and padding.
- Not run: live recheck of UAT 2.4-2.7 and 6.1 (needs the 0.1.6 build; plan 16 Task 3). Reported as unverified.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] `useDegramSendBlocked` never re-rendered on state it did not receive as a hook value**
- **Found during:** Task 2 (route guard test "the Send button follows the route")
- **Issue:** React Compiler memoizes `sendBlockedReason()` (a no-argument call on module state) on `enabled` alone, so the Send button ignored route, pin and machine changes. The same flaw predates this plan for the machine and pin.
- **Fix:** `'use no memo'` in `useDegramSendBlocked`, plus subscriptions to `$degram` and `$activeGatewayProfile`.
- **Files modified:** `src/degram/composer-seam.ts`
- **Commit:** `d0d69691`

**2. [Rule 2 - Missing critical functionality] Route can be moved away after the guard passed**
- **Found during:** Task 2
- **Issue:** `adoptPrimaryProfile` in the boot sets `$activeGatewayProfile` directly, possibly after the shell mounted, leaving Send blocked with nothing to restore the route.
- **Fix:** `startRouteReconcile` (listens to route changes only, so a failed attempt cannot loop) mounted by the shell host.
- **Files modified:** `src/degram/scope-route.ts`, `src/degram/shell-host.tsx`
- **Commit:** `d0d69691`

**3. [Rule 3 - Blocking] Existing chat tests ran with the default route**
- **Issue:** the new guard blocked every chat test whose ready scope has profile `p` while the route was `default`.
- **Fix:** `readyHarness` puts the route on the scope profile; afterEach resets it.
- **Files modified:** `src/degram/chat.test.tsx`, `src/degram/shell.test.tsx`

### Design adjustments within the plan

- `startNewChat` kept its `() => void` shape (the plan sketched `startNewChat(state)`); the state-taking handler is `handleNewScope`, which keeps `DegramActionsContext` and its test doubles unchanged.
- `followScopeRoute` calls `ensureGatewayProfile` also when the atom already agrees (the plan said "no side effects"): its own fast path is a no-op for a true agreement and repairs the atom-over-wrong-socket split-brain; the session wipe still happens only on disagreement.
- The bots plugin reads `window.hermesDesktop.degramEnabled` (the preload flag behind `$degramEnabled`), not the store, because plugin bundles take no app-store imports.
- Extra test files beyond `files_modified`: `status-stack/session-control.test.tsx`, `store/session-control.test.ts`, `store/profile-cache.test.ts`, `plugins/hermes-bots/plugin-panes.test.tsx`.
- Tests were written together with the implementation in one pass; no separate RED run was recorded.

## Deferred Issues

Pre-existing, out of scope (no touched module is imported by them; not re-run on the baseline, so unverified as pre-existing):
- `src/store/voice-prefs.test.ts` (2 cases: localStorage value `'false'` where `null` is expected).
- `src/plugins/hermes-bots/cron-detail.test.tsx` "labels a next run parked past the scheduler grace as overdue" (relative-time fixture against the 2026-10-09 clock).

## Known Stubs

None.

## Threat Flags

None. Mitigations T-1301-18-01..03 implemented: session lists wiped before the route switch; `route-mismatch` guard plus hard `ROUTE_MISMATCH` refusal; one re-handoff per scope open.

## Self-Check: PASSED

Created files and both commits (`b9f5946` framework, `d0d69691` component) found; no tracked file in `apps/degram` is modified after the commit.
