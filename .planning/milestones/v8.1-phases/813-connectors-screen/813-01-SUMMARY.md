---
phase: 813-connectors-screen
plan: 813-01
status: complete
completed: 2026-07-11
retroactive: true
retroactive_note: >
  Written 2026-07-13 (gap-closure session) — Phase 813 executed on 2026-07-11
  inside the combined v8.1 session (commit trail below) but its plan SUMMARY
  was never written at the time.
---

# Plan 813-01 Summary: Connectors Screen

**Goal:** The Connectors region shows all connectors by category with credential creation, copy-once tokens, activation status, and last-connection dates (CONN-01..04).

## What was built

- **`ui-v2/src/lib/connectorsApi.js`** (commit `aeecd86`) — thin client over the Phase 812 backend: `listConnectors()` (registry + per-connector status/credentials), `createCredential(connectorId, label)` (returns the one-time `dgc_` token), `revokeCredential(connectorId, credentialId)`.
- **`ui-v2/src/screens/ConnectorsScreen.jsx`** (commit `a419912`) — the Connectors region screen mounted in Phase 810's shell:
  - 14 connectors rendered grouped in the 5 milestone-brief categories, driven entirely by the API registry (no hardcoded connector list in the UI).
  - Credential creation per connector with a **copy-once token panel** ("This token is shown once. Paste it into the …" + copy button) — the token is never retrievable again, matching the backend's hash-only persistence.
  - Per-connector **activation status** and **last-connection date** ("never connected" / formatted date) from the status endpoint.
  - **Two-step revoke** (Revoke → Confirm revoke) with a "Revoked" badge on dead credentials.
- Doc fix `b840b7e` — repaired sed-damaged frontmatter and the connector card count in the plan doc.

## Verification

Retroactively verified 2026-07-13 — see [813-VERIFICATION.md](813-VERIFICATION.md) (4/4 truths, registry 14/5 asserted against source, data-service suite 168/168 in-container, live container renders the screen).

## Notes

- The screen's Grasshopper connector is the minting point for the platform tokens Phase 824's CONNECTOR component consumes — 824-UAT.md uses it as its fixture setup.
