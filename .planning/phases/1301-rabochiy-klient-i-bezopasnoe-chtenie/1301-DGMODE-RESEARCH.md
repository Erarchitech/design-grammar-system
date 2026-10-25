# Phase 1301 — supplemental DGMODE research

Scope: DGMODE-01..04 only. Research and plans prepared inline under the owner's explicit exception to separate GSD roles. No independent researcher/checker acceptance is claimed. Existing 01–41 plans and historic research remain authoritative for their own scope.

## Verified baseline

Workspace preflight passed: component HEAD and framework gitlink both `b619e02e3725869b1ab5125951d3311e3656dc9a`; installed component context present; productAccepted remains false. Framework branch `gsd/milestone13`; child development branch `degram/milestone13`. Existing maximum plan number: 41. New plans: 42–47, serial waves 29–34, with no dependency on the unrelated old release plan 41.

Directly inspected source (all child paths below relative to apps/degram):

| Source | Finding / planning consequence |
|---|---|
| apps/desktop/electron/degram/dg-config.ts | `DEGRAM_DG_ORIGIN` overrides file `dgOrigin`, then localhost:8080. Invalid explicit origin throws rather than falling back. Parser projects only dgOrigin/revitPython/revitMcpDir; a new writer must retain unrelated keys. Current normalization permits remote HTTP. |
| apps/desktop/electron/main.ts, ensureDegramWiring | Resolves origin once, opens shared `persist:degram-dg`, binds partition fetch/profile CLI/backend and cookie session. A renderer-only selector cannot switch the product. |
| apps/desktop/electron/degram/main-wiring.ts | Cookie changed listener has no removal path; runtime/view attached once. Switching needs explicit disposal/rebinding and preserved window/tray attachment. |
| apps/desktop/electron/degram/ipc.ts | Runtime composes fixed-origin session/scope/view; state lacks environment identity. `DgMode` is graph/full display mode, NOT the new target mode. Sender-validated IPC is the extension seam. |
| apps/desktop/electron/degram/scope.ts | ScopeKey only user/company/project. closeCurrent clears credentials then releases backend, but failures are currently best effort; dispose alone only promises timer stop. Switching needs an awaited, fail-closed release barrier, not signOut (which wipes storage). |
| apps/desktop/electron/degram/profiles-cli.ts | ensure/purge use argv values bound to flags; purgeProject has user/project only; cleanupLegacy keep list has no origin. All destructive paths must become environment-aware. |
| degram_variant/profiles.py | Profile hash is user/company/project only. Manifest omits origin. purge-project scans every scope directory, and cleanup-legacy removes invalid manifests. Migration must precede cleanup, be restartable, preserve history and constrain all destructive operations. |
| apps/desktop/src/degram/use-degram-state.ts | Initial getState can arrive after subscribed state; handledEpoch is only numeric. Environment + monotonic generation must fence both initial response and events. |
| apps/desktop/src/degram/documents-store.ts | Cache key is company/project/epoch; native document answers are generation-checked, but key omits origin/user. |
| apps/desktop/src/degram/request-lifecycle.ts | Preview/Send/streaming/confirmation machine exists; a scope reset clears armed Send. Reuse it; do not replay on another target. |
| apps/desktop/src/degram/mapping-api.ts | Mapping uses gateway requests; existing mapping behavior stays unchanged, but cache/binding identity and stale completion need target fences. |
| apps/desktop/package.json + vitest.config.ts | `npm --prefix apps/degram/apps/desktop test -- --project electron ...` and `... --project ui ...` use existing Vitest node/jsdom projects. `typecheck` is available. No install/build/launch is needed for offline planning. |
| tests/degram/ | Actual Python suites include test_profiles.py, test_credentials_provider.py, test_relay_error_mapping.py, test_lockdown.py, test_launchers_degram.py, test_context_composer.py and bridge/mapping suites. There is no tests/test_degram_profiles.py at the guessed path. |

The initial isolated researcher report supplied additional navigation leads, not decisions or verified implementation. Executor must read named consumers before changing them; no broad sweep of the upstream tree.

## Implementation decisions for this slice (not retroactive owner decisions)

1. Separate `DgTargetMode = developer | demo` from embedded `DgMode = graph | full`. Extend degram.json with schemaVersion, activeDgTarget and dgTargets. Developer accepts canonical HTTP(S) loopback origins only; Demo accepts the configured HTTPS stand only. Initial public Demo origin: `https://dg.173-249-46-99.nip.io`. Public URL is not a secret. Do not probe it during offline implementation.
2. Canonical environment identity derives from canonical origin, not the mutable label. Use SHA-256 over UTF-8 origin with a versioned prefix; filesystem/partition suffix is lowercase hex, colon-free after `persist:`. Profile identity includes origin plus user/company/project with cross-language vectors. No new generic HERMES_* variable or second auth system.
3. Preserve DEGRAM_DG_ORIGIN compatibility as an explicit launch override: canonical override must match a configured target. Display effective mode/origin and override source. While override exists, reject selection of the other target with actionable restart/remove-override guidance. An invalid, remote-HTTP, unmatched or mismatched override fails closed before auth, never silently ignores the persisted selection. Legacy remote origin maps only to Demo if HTTPS; never label it Developer. Conflicting legacy/env origins require explicit repair; never assign ambiguous cookies/history to another origin.
4. Migration has a versioned origin-ownership journal. Legacy cookie partition may be adopted in place for its uniquely proven legacy origin (normally Developer localhost), without copying cookies. Bind that alias permanently to that origin; other origins get new partitions. Mark adoption only after durable ownership write. Do not clear inactive partitions when switching.
5. Legacy profiles/manifests are adopted only for proven legacy origin, before destructive cleanup. Journal old/new paths; move profile directories locally when unambiguous and safe, preserve state.db/memory/logs and recover interrupted moves idempotently. Conflicts or malformed ownership are quarantined/reported, not deleted or overwritten. Unknown origin blocks adoption, not sign-in to an unrelated empty environment. No migration to the hosted server. Ordinary auth/membership/grant validation remains required before restored project/history is exposed.
6. Switch policy: refuse while opening scope, previewing, armed/confirming Send, streaming, mapping/native request or another switch is active. Offer existing Stop then explicit retry; no automatic retry or replay. Main is the enforcement authority; a renderer assertion of idle is insufficient. Use operation leases/backend activity and drain barrier in the real runtime path. Idle async reads may be invalidated and ignored.
7. Transaction order: validate target and busy guard → atomically persist selected target intent → enter switching/generation fence → await credential clear/backend release/listener/view disposal → create new target runtime → authenticate only new origin → ready/signed-out/error. Persistence failure leaves old runtime untouched. Teardown failure leaves all actions blocked, selected/new target visible with no effective runtime; retry teardown explicitly. Auth/network/TLS failure retains selected new target/error across restart, with no automatic fallback. Never have an old active runtime painted as the newly selected mode.
8. Switching is not signOut: preserve inactive cookies/history, clear only in-memory credentials and scoped renderer caches. Revoke/logout remains environment-scoped under existing policy. Native bridge listeners remain workstation-local; target selection confers neither CAD writes nor server-side mapping grants.
9. Amend UI in a separate slice-specific supplement before renderer work: persistent shell selector outside embedded DG view on pre-auth/error and working surfaces; Developer Mode/Demo Mode plus effective origin; busy refusal and target-specific errors. Existing sidebar/ring/layout decisions stay intact.

## Plan allocation

| Plan | Repository | Output | Depends |
|---|---|---|---|
| 42 | component | Target schema/validation/atomic settings and partition ownership | none |
| 43 | component | Environment profiles, safe migration, scoped purge/cleanup | 42 |
| 44 | component | Main-owned switch coordinator, target-bound runtime and typed bridge | 43 |
| 45 | component + framework UI supplement (separate ordered tasks) | Visible selector and fenced renderer consumers | 44 |
| 46 | component | Offline real-path collision/migration/race/negative regression suite | 45 |
| 47 | framework + owner-controlled publication checkpoints | Guide, evidence, authorized published pair and live acceptance | 46 |

Plans 42–46 do not authorize commits, push, build, install or live access. GSD SUMMARY artifacts belong in the framework even for component tasks. Plan 47 authorizes nothing by its existence: explicit gates precede each outward-facing/runtime action. Do not auto-execute old plan 41 as a dependency.

## Validation architecture

Fast focused tests after each seam; full bounded slice suites in 46. Test production imports, settings journal and actual profile filesystem within ONE disposable installation home for A→B→A, plus a separate untouched stock-home sentinel. Boundary Electron/network/backend adapters can be controlled; do not mock the coordinator, config, profile algorithm and stores under test. No paid inference, real stand, installed profile or user PATH writes. Initial Node/Python dependencies are assumed present; missing dependencies are blockers, not permission to install.

Exact existing command entry points:

- Framework cwd: `python tools/degram/workspace.py verify`
- Framework cwd: `python -m unittest discover -s tools/degram/tests -v`
- Framework cwd: `npm --prefix apps/degram/apps/desktop test -- --project electron electron/degram`
- Framework cwd: `npm --prefix apps/degram/apps/desktop test -- --project ui src/degram`
- Framework cwd: `npm --prefix apps/degram/apps/desktop run typecheck`
- Child cwd: `python -m pytest tests/degram/test_profiles.py tests/degram/test_credentials_provider.py tests/degram/test_relay_error_mapping.py tests/degram/test_lockdown.py -q`

New suites and exact focused selectors are specified in plans. Do not run broad upstream launch/install suites or the known PATH-writing test. Successful offline tests are not live acceptance. Requirements remain Pending until framework evidence records expected/actual results, exact versions and separately authorized local/Contabo checks. HOST-05, DGCL and Phase 1301 remain independently open.
