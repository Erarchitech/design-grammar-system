---
tags: [decision, DeGram, v13.0, phase-1301, connectors, auth, security]
date: 2026-10-06
status: planned (1301-17-PLAN.md, framework df62f9e); D-25/D-26 in 1301-CONTEXT.md
---

# DeGram connects through a user-bound pairing connector in the Connectors tab

## Context

DeGram mints its own 15-minute delegated `dgd_` token from the DG session the user opens inside DeGram (D-05, D-06); the user never sees it. The owner wants DeGram's credential created and revoked in the DG Web UI Connectors tab, like the other connectors. Ordinary connector tokens (`dgc_`) cannot serve: they carry no user or company, never expire, are accepted only by publish routes, and 1300 D-07 / 1301 D-06 keep the agent acting as the user.

## Decision (owner, 2026-10-06)

- **D-25:** a separate **DeGram** card in Connectors issues a pairing token (`dgp_`, shown once). DeGram stores it with Electron `safeStorage` and exchanges it (`POST /auth/degram/exchange`) for the same `dgd_` the relay and tools already accept. A `dgp_` is accepted by no other route and is never a connector principal. Revoking it (owner or admin) revokes every `dgd_` minted from it at once.
- **D-26:** the pairing is bound to the user, not a project. The project is chosen in DeGram; each exchange re-checks the live membership and the project's company.

## Open (Task 1 of plan 17)

Whether DeGram keeps the in-app DG sign-in for its embedded DG page, and whether a pairing expires (none / 90 days).

Related: [[knowledge/decisions/DeGram relay takes its model and key from the Web UI LLM settings]], [[sessions/2026-10-06 Phase 1301 audit-fix, DeGram identity and isolation beside open Hermes]].
