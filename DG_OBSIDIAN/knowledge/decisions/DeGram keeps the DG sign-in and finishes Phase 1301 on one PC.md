---
tags: [decision, degram, phase-1301, pairing, acceptance]
date: 2026-10-07
---

# DeGram keeps the DG sign-in and finishes Phase 1301 on one PC

**Status:** accepted by the owner (D-27 2026-10-06, D-28 2026-10-06), recorded in `1301-CONTEXT.md`.

## D-27 — sign-in kept, pairing without expiry

- The embedded DG page keeps its own cookie session (D-05). The agent, relay and tools take their `dgd_` token from the stored pairing when there is one, otherwise from the cookie session.
- A pairing token has no expiry (`expires_at` null). It ends on revoke in Connectors, on a password change, or when its user is deleted; every `dgd_` minted from it ends at once.
- Consequence: DeGram refuses a pairing that belongs to another DG user than the one signed in (the exchange answer carries `username`).

## D-28 — reviewer PC moves to the last phase

- The second independent PC (D-15) is checked in the last v13.0 phase. Phase 1301 finishes all DeGram function and UI with live checks on the pilot PC.
- The findings found on PC1 (G-1, F-11) are closed before the PC1 acceptance; both closed 2026-10-07.

Related: [[knowledge/decisions/DeGram connects through a user-bound pairing connector in the Connectors tab|pairing connector]], [[sessions/2026-10-07 Phase 1301 DeGram pairing connector, rules read fix, 490 MB installer and no Hermes name|session]].
