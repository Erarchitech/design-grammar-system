---
phase: 1301-rabochiy-klient-i-bezopasnoe-chtenie
plan: 17
subsystem: auth
tags: [degram, pairing-token, delegated-token, connectors, electron-safestorage, fastapi]

requires:
  - phase: 1301-15
    provides: isolated DeGram build, delegated token (plan 05), relay (plan 08), DG session/scope (plan 12)
provides:
  - "dgp_ DeGram pairing token: Connectors tab create/list/revoke, user-bound, no expiry (D-25, D-26, D-27)"
  - "POST /auth/degram/exchange: pairing -> the same short-lived dgd_ the relay and tools accept"
  - "DeGram stores the pairing as safeStorage ciphertext and mints the agent token through it; panel «Подключение к DG»"
  - "relay_probe pairing support (DEGRAM_PROBE_PAIRING + --project); pasted tokens trimmed, never echoed"
  - "DeGram 0.1.1 build from component 97e158f2"
affects: [1301-16, DGCL-01, DGCL-05, spec/SECURITY-BOUNDARY.md]

tech-stack:
  added: []
  patterns:
    - "A credential that is not a principal: dgp_ is refused before credential resolution on every route but its exchange"
    - "Derived token parent kinds: a dgd_ is bound to a session OR a pairing, re-checked live on every request"

key-files:
  created:
    - data-service/degram_pairing.py
    - data-service/tests/test_degram_pairing.py
    - apps/degram/apps/desktop/electron/degram/pairing-store.ts
    - apps/degram/apps/desktop/src/degram/pairing-panel.tsx
    - .planning/phases/1301-rabochiy-klient-i-bezopasnoe-chtenie/1301-UAT.md
  modified:
    - data-service/auth.py
    - data-service/auth_routes.py
    - data-service/delegation.py
    - data-service/route_policy.py
    - data-service/app.py
    - spec/SECURITY-BOUNDARY.md
    - spec/API.md
    - ui-v2/src/screens/ConnectorsScreen.jsx
    - ui-v2/src/lib/connectorsApi.js
    - tools/degram/relay_probe.py
    - apps/degram/apps/desktop/electron/degram/dg-session.ts
    - apps/degram/apps/desktop/electron/degram/scope.ts
    - apps/degram/apps/desktop/electron/degram/ipc.ts

key-decisions:
  - "D-27: the D-05 DG sign-in stays for the embedded DG page; a pairing never expires and ends only on revoke"
  - "The exchange answer adds username so DeGram refuses a pairing of another DG user than the signed-in one"
  - "A refused pairing closes the scope (pairing-revoked) without purge, view wipe or sign-out; no silent cookie fallback"

patterns-established:
  - "DELEGATED_SESSION_ENDED on a pairing credential triggers one re-mint check instead of ending the DG session"

requirements-completed: []

coverage:
  - id: D1
    description: "Pairing store, exchange route, refusal on every other route, revocation cascade, no token in logs"
    requirement: "DGCL-05"
    verification:
      - kind: unit
        ref: "data-service/tests/test_degram_pairing.py (70 cases x 2 profiles), test_route_inventory.py, test_cross_project_matrix.py, test_security_boundary_spec.py"
        status: pass
      - kind: manual_procedural
        ref: "1301-UAT.md Plan 17 live pairing, revoke at 20:52:45Z -> relay 401 -> exchange 401, 6/6 dgd_ revoked"
        status: pass
    human_judgment: false
  - id: D2
    description: "Connectors tab DeGram card (create shown once, list with last use, revoke)"
    requirement: "DGCL-01"
    verification:
      - kind: manual_procedural
        ref: "1301-UAT.md: create 14:59:31Z, revoke 14:59:17Z and 20:52:45Z, live on PC1"
        status: pass
    human_judgment: true
    rationale: "ui-v2 has no test runner; the card was checked live by the owner"
  - id: D3
    description: "DeGram stores the pairing (safeStorage), mints through it, shows the revoked state and keeps the DG sign-in"
    requirement: "DGCL-01"
    verification:
      - kind: unit
        ref: "apps/degram/apps/desktop: vitest electron/degram src/degram (18 files, 334 tests)"
        status: pass
      - kind: manual_procedural
        ref: "1301-UAT.md: DeGram 0.1.1 on PC1, exchange 17:15:41Z, renewals every 600 s, owner-confirmed revoke state"
        status: pass
    human_judgment: true
    rationale: "The revoked-state UI and the kept sign-in were observed by the owner"
  - id: D4
    description: "relay_probe exchanges a pairing token"
    verification:
      - kind: unit
        ref: "python -m unittest discover -s tools/degram/tests (27)"
        status: pass
      - kind: manual_procedural
        ref: "1301-UAT.md Relay capability probe, 4/4 cases, tokenSource pairing"
        status: pass
    human_judgment: false

duration: ~8h (incl. two installer builds and live checks)
completed: 2026-10-06
---

# Phase 1301 Plan 17: DeGram connector (pairing token) Summary

**The Connectors tab issues DeGram a revocable `dgp_` pairing token; DeGram keeps it encrypted, trades it for the usual 15-minute `dgd_`, and loses access the moment the pairing is revoked, live-verified on PC1.**

## Performance

- **Completed:** 2026-10-06
- **Tasks:** 6/6 (Task 1 decision D-27, Task 6 owner-verified)
- **Execution:** inline (owner choice), no subagents

## Authorization

Owner, 2026-10-06 (AskUserQuestion): D-27 keep-signin-no-expiry; container rebuild; child commit; push + gitlink bump;
installer 0.1.1 build. Install and launch on PC1 requested by the owner in the session.

## Accomplishments

- Server: `degram_pairing.py` (hash-only store `degram-pairings.json`), `POST /connectors/degram/pairings`,
  `DELETE /connectors/degram/pairings/{id}` (owner or admin, same 404 otherwise), DeGram card in `GET /connectors` (category
  Agents), `POST /auth/degram/exchange`; `require_principal` answers 401 `PAIRING_NOT_A_PRINCIPAL` for a `dgp_` on every other
  route, public ones included; `delegation` gained a pairing parent and `revoke_for_pairing`; password change revokes pairings.
- Specs: SECURITY-BOUNDARY Section 3.5 + route-policy block + enforcement row; API.md rows and error codes.
- Connectors tab: DeGram card (label only, token shown once with DeGram copy, last use, revoke).
- DeGram (component `e2fb6ffb`, `97e158f2`): `pairing-store.ts` (safeStorage, atomic, refuses without OS encryption),
  exchange in `dg-session.ts` with user-mismatch refusal, `pairing-revoked` scope path, IPC `degram:pairing:set|clear`,
  panel «Подключение к DG» in the project choice, ru/en copy; version 0.1.1.
- `relay_probe.py`: pairing exchange; trims pasted values, refuses malformed ones, never echoes a token.

## Task Commits

Framework: `6119979` server + specs, `de11958` Connectors card, `4b8464f` probe pairing, `e56b77c` exchange username,
`72bf43e` gitlink e2fb6ffb, `69eeda5` gitlink 97e158f2, `9f0669b` build record, `c91d5a7` probe token echo fix,
`9606ceb` failed-install record, `a741d05` / `69ca48a` / `45acbcc` UAT.
Component (`Erarchitech/degram` `degram/phase-1301`, pushed): `e2fb6ffb` pairing store/exchange/panel, `97e158f2` 0.1.1.

## Deviations from Plan

**1. [Rule 2 - Missing critical] Exchange answer carries `username`** (plan said "the same" answer as the cookie mint). With the
sign-in kept (D-27) DeGram must not let the agent act as another DG user than the one it shows; it refuses such a pairing
(`PAIRING_USER_MISMATCH`). Commit `e56b77c`.

**2. [Rule 3 - Blocking] Files outside `files_modified`:** `test-support.ts`, `scope.ts`/`scope.test.ts`, `main-wiring.ts`,
`electron/main.ts` (inject the store), `degram-gate.tsx` (mount the panel), `use-degram-state.ts` (revoked toast),
`test-harness.tsx`, `preload-degram.test.ts`, `ipc.test.ts`, `data-service/tests/test_connectors.py`,
`data-service/tests/test_cross_project_matrix.py` (the member matrix now selects member-capable rows only, exactly the rows
it covered before; the exchange's cross-project and mismatch denials are in test_degram_pairing.py).

**3. [Rule 1 - Bug] relay_probe printed a pasted token** in a traceback (trailing newline rejected by http.client). Fixed
`c91d5a7`; the exposed pairing was revoked by the owner.

## Issues Encountered

- Build run 1 failed on ReadOnly files in the gitignored `build/agent-payload`; flag cleared, run 2 exit 0 (1301-BUILD.md).
- Install of 0.1.1 on PC1 failed (exit 5, partial): four payload paths exceed 260 chars at the default install dir (F-11), and
  the installer file was then removed from `D:\dgb` (likely Kaspersky). The owner ran the unpacked 0.1.1 build instead.
- Kaspersky resets every connection made by `tools\degram\relay_probe.py` run as a script on PC1; the probe ran via `runpy`.
- Live UAT found **G-1**: `degram_project_graph` fails `RESPONSE_TOO_LARGE` on a project with validation history and never
  reads the rules (1301-UAT.md). Not part of plan 17's scope; open for gap closure.

## Self-Check: PASSED

data-service pairing/route/spec suites green; DeGram vitest 334/334, typecheck and lint clean; tools/degram 27/27;
`workspace.py verify` passes on `97e158f2`; live pairing evidence in 1301-UAT.md.

## Next Phase Readiness

Plan 16 (wave 9) can run: the probe works through a pairing. Open before phase exit: G-1, F-11 (installer long paths),
the Kaspersky interference on PC1, and the two-PC DGCL-01..07 acceptance (plan 16 Task 3).
