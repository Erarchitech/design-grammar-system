---
tags: [session, degram, phase-1301, uat, v13.0]
date: 2026-10-09
---

# Session: 2026-10-08/09 — Phase 1301 live UAT on PC1 and the 0.1.6 gap list

## Goal

Amend plan 16 to the owner decisions D-24, D-25..D-27 and D-28, then run the live DGCL-01..07 acceptance of DeGram 0.1.5 on the pilot PC step by step with the owner.

## What Was Done

- **Plan 16 amended:** Task 3 runs on PC1 only (D-28; the second independent install stays mandatory in the last v13.0 phase), relay settings come from the Web UI LLM settings (D-24), DeGram connects through a Connectors pairing (D-25..D-27). Tasks 1 and 2 marked done (owner authorization "all" and the relay probe of 2026-10-06).
- **`docs/degram/CLEAN-INSTALL.md`:** the removed `PUT /degram/admin/llm-config` replaced by the Web UI LLM settings, new step 6.5 (pairing), new prerequisite: security software must trust the installed DeGram executables.
- **Live run on PC1 with installed 0.1.5** (Kaspersky trust rules added by the owner; the installed copy now reaches DG). Every step recorded in `.planning/phases/1301-rabochiy-klient-i-bezopasnoe-chtenie/1301-UAT.md`:
  - DGCL-01 pass (Hermes home changes attributed to the owner's headless Hermes gateway, not to DeGram).
  - DGCL-03 pass (Model Viewer geometry only through `/speckle-proxy`, no Speckle token in the DG view).
  - DGCL-04 pass on the route and bridge layer after four live fixes to the Revit adapter fork (see [[knowledge/debugging/DeGram Revit adapter could not load under pyRevit IronPython 3.4]]): 8 read routes registered, 10 write declarations dropped, write routes absent on the wire, not-loopback host registers nothing.
  - DGCL-05 partial: cross-project and cross-company denies, company reassignment revoking open tokens, membership revoke on the server and local purge all pass; no revoke toast, no sign-out control.
  - DGCL-02 fail, DGCL-06/07 partial: the chat stays bound to the first scope profile (see [[knowledge/debugging/DeGram chat stays on the first scope profile after a project or company change]]).
- Owner-approved setup changes left in place for the recheck: the owner's `revit-mcp-server.extension` parked in `%APPDATA%\pyRevit\Extensions.disabled-20261008\`, the DeGram extension installed, companies `UAT-A` (v12) and `UAT-B` (degram-uat-b), `degram-uat-b` owned by the second user.
- Fork `apps/revit-mcp` changes (G-8..G-12, 163 tests pass) are **in the working tree only**, not committed.

## Decisions Made

- **D-29:** one pinned document per bridge, a Revit model and a GH definition at the same time. See [[knowledge/decisions/DeGram pins one document per bridge]].
- Owner skipped the live password-change check; it stays an open live item (offline tests only).
- Company assignment with test names `UAT-A`/`UAT-B` (cannot be unassigned later, only renamed).

## Issues Encountered

- G-3..G-7: the chat, the «Сеансы» list and the error copy follow the profile the window restored at boot, not the scope; stock Hermes provider/key error card; locked `session.control.read` shown as an error.
- G-8..G-12: Revit adapter unloadable under pyRevit IronPython 3.4 (disabled by default, `async def`, implicit relative imports, `urllib.unquote`, JSON body parse); fixed in the fork working tree.
- G-13: one pinned document for both bridges → D-29.
- G-14: Revit busy shown as "DG server can't be reached" (30 s RPC timeout below the 40 s bridge deadline).
- G-15: membership revoke without the toast; an older-company profile of the project left on disk.
- G-16: blank window when DG resets connections at start.
- G-17: no sign-out control in DeGram.

## Next Steps

- Owner: revoke pairing `DeGram_UAT_matrix`; authorize the fork commit/push of the `apps/revit-mcp` fixes.
- `/gsd-plan-phase 1301 --gaps` for G-3..G-17 and D-29, build 0.1.6, then continue DGCL-06/07 and recheck the failed items.
- After the recheck: restore the owner's pyRevit extension from `Extensions.disabled-20261008`.

## Related Notes

- [[sessions/2026-10-08 Model Viewer fixes, landing motion redesign and DeGram 0.1.5]]
- [[knowledge/decisions/DeGram keeps the DG sign-in and finishes Phase 1301 on one PC]]
- [[knowledge/debugging/Kaspersky on PC1 blocks the DeGram installer and the installed executable by path]]
