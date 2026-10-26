---
phase: 1301-rabochiy-klient-i-bezopasnoe-chtenie
plan: 44
subsystem: degram-environment-runtime
status: complete
completed: 2026-10-26
requires: [1301-42, 1301-43]
provides:
  - main-owned serialized target transaction with strict teardown and explicit recovery
  - descriptor-bound Electron runtime replacement and safe target IPC
  - backend admission fence covering running and queued RPCs
  - offline replacement, race, failure, sender and generation regression checks
affects: [1301-45, 1301-46, 1301-47]
requirements-completed: []
---

# Phase 1301 Plan 44: Target-bound runtime switching

**The Electron main composition now owns target replacement and the backend freezes admission atomically. Both implementation tasks are complete at the bounded offline plumbing level. Renderer operation-lifecycle adoption, composed product acceptance and live acceptance remain separate gates.**

## Scope

- Invocation: `/gsd-execute-phase 1301 --wave 3 --no-transition`.
- Computed DAG wave 3 selects plan 44; its historical declared wave is 31. Resumed the existing Task 1 implementation and completed Task 2 without redoing plans 42–43.
- Current checkout only. No workers, worktrees, commits, pushes, installs, Desktop build/launch, installed-profile access, live DG/CAD calls or paid inference.
- Source remains uncommitted in the component; framework gitlink and component HEAD remain `b619e02e3725869b1ab5125951d3311e3656dc9a`. Earlier and unrelated working-tree changes were preserved.
- Primary STATE position remains Phase 1303; no phase transition or requirement completion.

## Lifecycle ordering

1. Validate the requested configured mode and launch-override restriction. Reject concurrent switches and main-held operation leases.
2. Freeze scope admission; refuse opening, clearing, checking or renewing scope activity. An uncertain retained backend without a usable handle fails closed.
3. Ask the real gateway to quiesce. Running and queued RPC reservations share a lock with the backend activity snapshot and freeze. Streaming/session activity still vetoes after an RPC acknowledgement returns.
4. Atomically persist selected intent. If persistence fails, explicitly resume the old generation; failure to resume blocks all actions.
5. Increment the coordinator generation, retain selected intent and clear effective runtime. No fallback to the prior origin.
6. Invalidate old scope callbacks; stop heartbeat/renewal; await credential clear and positive backend release. A failed stage prevents new authentication and requires explicit retry.
7. Remove cookie/window/auth/scope subscriptions, destroy/detach the old native view, and discard the old runtime.
8. Construct one immutable target descriptor: origin, environmentId, generation and resolved partition. Bind partition fetch, navigation policy, profile adapter and backend calls to it. Restore presentation bounds/locale/mode/tray labels and authenticate only this target.
9. Publish ready only after startup succeeds. Failed startup is strictly cleaned up; cleanup failure reports TEARDOWN_FAILED. Selected intent remains visible, effective runtime stays null, and retry does not replay user work.

Switching is not sign-out: it never invokes `/auth/logout`, copies cookies, wipes partition storage/history, purges profiles or automatically stops/resends work.

## Main/backend authority

- `createDegramEnvironmentWiring` registers IPC once against a coordinator and resolves the current runtime dynamically, rather than retaining a disposed runtime in handlers.
- Target selection/retry and lease IPC validate the attached sender and exact selected environmentId/generation; the renderer supplies a configured mode, never an arbitrary URL. Preload exposes no credentials.
- Existing runtime IPC holds a main lease through its Promise completion. The separate acquire/release API supports longer renderer-owned lifecycles in plan 45.
- Backend dispatcher reserves work before invoking or enqueueing a handler, releases on completion/cancellation/enqueue failure, and atomically excludes new work after quiesce. Missing metadata and a different generation cannot bypass a frozen backend. Capability lockdown retains priority.
- Only switch-control RPCs and credential clear/status may enter the frozen backend. Exact-generation resume is required; another generation cannot replace the barrier.
- Main-owned gateway calls carry a validated transport envelope; it is removed before existing closed handler contracts. No public data-service route or alternative provider stack was added.
- Stock Hermes bypasses environment admission; Electron construction remains behind the existing DeGram identity/path gate.

## Disposal inventory

| Resource | Disposal/fence |
| --- | --- |
| Delegated credential / backend | Awaited clear then backend release; retained profile also released after failed credential handoff. |
| Heartbeat / renewal | Stopped before strict close; closed/frozen scopes cannot restart them. |
| Auth / scope subscriptions | Explicit unsubscribe; scope listeners cleared on disposal. |
| Cookie observer | Removed from the old partition; stale callbacks check descriptor/closed state. |
| Window focus / closed callbacks | Removed before replacement; current-window and descriptor checks. |
| Native view | Closed and detached; replacement uses the descriptor partition and exact-origin policy. |
| Pending fetch / queued view publication | Current-generation and disposed guards; late auth cannot publish new scope work. |
| Presentation | Bounds, locale, mode and tray label retained in main and applied to replacement. |

Invalid initial origin, configuration or ownership-journal errors expose safe CONFIG_INVALID state before sign-in. Recovery is repair-on-disk plus explicit restart, never localhost fallback. TLS verification is unchanged.

## Fresh verification

Commands use framework cwd unless stated otherwise.

| Check | Result |
| --- | --- |
| `npm --prefix apps/degram/apps/desktop test -- --project electron electron/degram` | Passed: 16 files, 302 tests. |
| `npm --prefix apps/degram/apps/desktop run typecheck` | Passed: all four configured checks, no emit. |
| Existing component `.venv/Scripts/python.exe -m pytest` with `test_environment_activity.py`, `test_lockdown.py`, `test_credentials_provider.py`, gateway `contracts/test_generated.py`, and `test_retirement_admission.py` | Passed: 196 tests, including 11 environment tests. |
| `python -m unittest discover -s tools/degram/tests -v` | Passed: 27 tests. Relay-fixture socket ResourceWarnings were emitted; no live service used. |
| `python tools/degram/workspace.py verify` | Passed: gitlink/HEAD agree, component context installed; productAccepted remains false. |
| `git -C apps/degram diff --check` | Passed; CRLF-to-LF notices only. |
| Encoding inspection of edited main/controller/scope/IPC/gateway files | UTF-8 without BOM; each inspected file consistently CRLF or LF. |
| GSD schema drift | No drift; non-blocking. |
| GSD codebase drift | Tool skipped with `git-diff-failed`; not claimed as verified. |
| GSD `check ui-safety-gate 1301` | hasUiFiles false, block false. |
| Offline code-index refresh | Manifest confirms refresh at `2026-10-26T12:21:15.744375+00:00`, component HEAD b619e02e, paidInference false. Some final source/test edits followed this snapshot; not claimed as an exact final-source index. |
| Additional renderer regression: `npm --prefix apps/degram/apps/desktop test -- --project ui src/degram` | 326 passed / 1 failed: `ru-catalog-completeness.test.ts > explicitly translates settings without EN fallback`, because `settings.plugins.installModal.repoPlaceholder` is the identical URL `https://github.com/owner/repo`. Test and i18n inputs are unchanged from HEAD; no localization fix included. |
| Build, launch, full upstream suite, live TLS/auth/CAD/stand acceptance | Not run; outside this plan's authority. |

Actual production modules are composed in the A→B→A tests with fake external adapters. These are not live Electron or hosted-service acceptance.

## Failures resolved

- PATH Python could not collect gateway tests because `ruamel` was missing. Used the existing component venv; installed nothing.
- A guessed credential-test filename did not exist; corrected to `test_credentials_provider.py`.
- Initial bridge/type/namespace expectations and the readDegramJson argument mismatch were corrected; final typecheck and preload tests pass.
- A concurrent test double initially returned an invalid result contract; corrected its status field.
- Initial new barrier tests leaked their frozen state across test files. Added explicit teardown and retained lockdown priority before environment admission; combined regression passes.
- A main.ts source-pin test expected scopeGate.allow immediately after a comment. Updated it to require the new descriptor-current guard before allow/start, rather than removing that guard.
- Historical GSD UI query aliases were unsupported by this installation; the installed `check ui-safety-gate` command passed.

## Necessary adjacent changes

- `tui_gateway/rpc_dispatch.py` and `server.py`: handler-only activity checks could not close enqueue/admission races. Added a shared process-owned reservation count and lock at the existing dispatch seam; retirement admission regression remains green.
- `src/degram/test-harness.tsx`: explicit fixtures for added bridge methods, throwing when an environment fixture is not configured.
- `scope-gate.test.ts`: updated the existing source pin for the stricter main backend-start guard.

## Follow-up boundary

- Plan 45 / computed wave 4 must adopt target state and generation in renderer stores, gateway callbacks, preview/armed Send/confirmation and streaming lifecycles, acquiring leases until actual completion. This plan supplies that main API, but does not claim those renderer lifecycles are already connected.
- Backend reservations protect work already accepted by the backend; an armed but not submitted Send is not backend work and requires the plan-45 lease integration. No target-selector UI is delivered here.
- Generations are monotonic within the main coordinator lifetime. Restart and stale renderer/backend integration are part of composed plan-46 verification; no cross-process durable-generation guarantee is claimed.
- Plan 46 owns broader composed real-path offline acceptance; plan 47 owns separately authorized publication/build/install/live evidence.
- DGMODE-01..04, DGCL, HOST-05, 1301-16 and full Phase 1301 acceptance remain open. Stop after wave 3.

## Self-check

Implementation artifacts and bounded checks are present. Offline plan completion is not an authorization to switch a live application or mark product requirements accepted.
