---
phase: 1301-rabochiy-klient-i-bezopasnoe-chtenie
plan: 31
subsystem: ui-v2
status: complete
completed: 2026-10-11
requires: [1301-30]
provides:
  - Project-scoped DeGram grant administration in the normal Connectors card
  - Caller-only grant and request view in hosted Connectors
  - Offline rendered and transport verification without browser-visible DeGram keys
affects: [1301-32, 1301-34, 1301-36]
key-files:
  created:
    - ui-v2/src/screens/DegramGrantsPanel.jsx
    - ui-v2/tests/degram-grants-api.test.mjs
    - ui-v2/tests/degram-grants.browser.jsx
    - ui-v2/tests/run-grants.mjs
    - ui-v2/tests/evidence/degram-1301-31-offline.json
  modified:
    - ui-v2/src/lib/connectorsApi.js
    - ui-v2/src/screens/ConnectorsScreen.jsx
    - ui-v2/src/App.jsx
    - ui-v2/src/lib/hostMode.js
    - ui-v2/tests/host-degram.test.mjs
    - ui-v2/tests/degram-grants.test.mjs
requirements-completed: []
---

# Phase 1301 Plan 31: CONNECTORS grant views

**The normal Connectors DeGram card now offers project owners and DG admins grant issuance/revocation and pending requests; members and hosted Connectors see only the caller's project grants and request flow. No DeGram key is returned to or revealed by the UI.**

## Implementation

- Replaced the DeGram pairing client with five grant API wrappers through `apiFetch`, retaining the ordinary connector credential reveal only for non-DeGram cards.
- Added an in-memory grant panel: owner/admin actions use the project endpoints and membership list; member/trimmed actions use `/degram/grants/mine` and `/degram/grant-requests`. Stale project-scope reads are ignored; request success and `GRANT_EXISTS` 409 have explicit states.
- Allowed the `connectors` region in `?host=degram`, with a trimmed early return that neither renders nor loads the ordinary connector registry. The normal card mounts the grant panel when expanded.
- Committed production code and tests as `59bedf3` (`feat(1301-31): project-scoped DeGram grants in Connectors`).

## Verification

- `node --test --test-reporter=dot ui-v2/tests/*.test.mjs` — exit 0.
- `npm --prefix ui-v2 run build` — exit 0; existing >500 kB bundle warning only.
- `node ui-v2/tests/run-degram.mjs verified` — 22 passed, 0 failed; synthetic responses, not a live-service check.
- `node ui-v2/tests/run-grants.mjs` and `node ui-v2/tests/run-grants.mjs host` — 6/6 each with real ReactDOM and synthetic API responses: own-project filtering, request and 409 states, issue/revoke, stale read isolation, normal card, and host-only route.
- `node --test ui-v2/tests/degram-grants-api.test.mjs ui-v2/tests/degram-grants.test.mjs ui-v2/tests/host-degram.test.mjs` — 11 passed; scoped cookie/CSRF, no DeGram token reveal, host region policy.
- `git diff --cached --check` passed before the code commit. `graphify update .` completed; generated graph files remain unstaged.

## Deviations and provenance

- `ui-v2/tests/api-security.test.mjs` was untracked before Plan 31; its added grant cases passed in the full Node suite but were **not staged** because the file also contains prior work. An independent plan-scoped API test was committed instead.
- `ui-v2/tests/evidence/degram-verified.json` was already modified before this plan and includes unrelated font, model, Speckle, and other source hashes. The existing script regenerated it during verification; the shared file remains unstaged. A separate script-generated `degram-1301-31-offline.json` records the plan's offline result. It is a whole-bundle hash snapshot, not proof of live use of every bundled source.
- The plan's live owner/member issuance-revocation acceptance is deferred: the running data-service image predates Plan 30 and image rebuild is reserved for Plan 36's owner-consent checkpoint. No service was rebuilt, no live grant was issued or revoked, and no live UAT is claimed.

## Self-Check: PASSED

- Plan implementation commit exists; committed panel and test files exist; offline acceptance commands exited successfully.
- Follow-on Plan 32 may now edit the host-mode surfaces serially. Phase-level DGCL-01/DGCL-05 remain open until the client and live acceptance are verified.
