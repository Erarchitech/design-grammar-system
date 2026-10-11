---
tags: [debugging, degram, phase-1301, backend-pool]
date: 2026-10-11
---

# DeGram: left-scope backend restarted by the renderer reconnect ladder (G-25)

## Symptom

0.1.9 `desktop.log`: after switching projects, "Hermes backend for profile X exited" was followed within milliseconds by "Starting Hermes backend for profile X" for the scope just left. Left scopes filled the 3-slot pool and once evicted the active backend; status polls logged "waiting for a free local slot".

## Root cause (reproduced offline with fakes before the fix)

Main kills the left scope's backend on release, but the renderer's gateway registry still held a secondary entry for it. Its reconnect ladder (`reconnectSecondary` → `openSecondary` → `getConnection(left)`) dialed the dead profile, and main's `ensureBackend` honoured the request and respawned the backend. Evidence came from a failing test showing the left profile's second accepted ensure originating from that stack. `desktop.log` itself was not read, so a status poll or roster read contributing in the live run is unproven.

## Fix (plan 1301-35, component `38728957`)

- `electron/degram/scope-gate.ts`: the scope controller allows only the active profile; release broadcasts `hermes:pool:retiring`; `ensureBackend` and `ensureRegistryBackend` refuse a `scope-<16 hex>` profile that is not active (error "no longer exists" so the ladder stops); `guardPrepare` stops LRU eviction, reclaim and the idle reaper from retiring the active scope.
- `scope-route.ts`: `followScopeRoute` retires the left scope's registry entry once the route lands on the new scope.
- `backend-churn.test.ts`: A→B→C→A gets no ensure for a left profile after release; mutation checks fail the matching tests.

## Caveats

A boot-restored route that names a `scope-…` profile before any scope is open is now refused; not exercised live. Live acceptance is step 10 of `1301-0.1.10-TEST-GUIDE.md` (no "Starting Hermes backend" line for the left profile within 5 s of release).

## Related

- [[sessions/2026-10-11 Phase 1301 gap round executed and DeGram 0.1.10 built]]
- [[knowledge/debugging/DeGram chat stays on the first scope profile after a project or company change]]
