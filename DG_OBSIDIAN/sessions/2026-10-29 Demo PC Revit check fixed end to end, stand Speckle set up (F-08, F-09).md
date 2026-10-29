---
tags: [session, v13.0, quick, revit, stand, speckle, degram]
date: 2026-10-29
---

# Session: 2026-10-29 — Demo PC Revit check fixed end to end, stand Speckle set up (F-08, F-09)

## Goal

After the rules were entered again, the Revit check from the demo PC (PC-2, DeGram in Demo mode against the stand)
failed with `REVIT_CHECK_FAILED: Name`. The goal was to diagnose and fix it (`/gsd-audit-fix`), and then to make the
check work end to end on the stand.

## What Was Done

- **F-08** (`93e3c11`): fixed the `Name` error.
  - Under pyRevit's CPython engine, `e.Symbol.Name` raises `AttributeError('Name')`, and `inventory()` reads it on
    every check.
  - Type names now go through `element_name()`. Catalogue `1303-15.5`. See
    [[knowledge/debugging/Revit check failed with Name on pyRevit CPython because a FamilySymbol hides Element.Name (F-08)|debugging]].
- **Stand rollout 1:** data-service `dg-data-service:f08-93e3c11` carries F-08 and the pending delete fix
  `993b709`.
  - The stand files were diffed with the commit first; the stand was exactly at `b30d2ea`.
  - It is a thin layer on the running image, and only data-service was recreated. Rollback tag `rollback-f08`.
  - No new snapshot, on the owner's word.
- **The next check reached publishing and failed with `SPECKLE_CONFIG_MISSING`.**
  - Speckle on the stand had never been set up: no users, open registration, empty tokens, no project binding.
  - The Speckle web UI is closed by the edge allowlist.
  - Owner decision: set it up from the server. See
    [[knowledge/decisions/Stand Speckle is set up from the server and its web UI stays closed at the edge|decision]].
- **Speckle bootstrap:**
  - a service admin account, then `inviteOnly: true`;
  - a write token and a read-only token in `.env`;
  - project `cb20909c46` with model `base` and a placeholder version, bound to `isolation-check-a`.
- **F-09** (`2c5f5bc`): fixed `PUBLISH_INTERNAL_ERROR` on the next check.
  - The parallel first publishes raced to create `dg-validation`.
  - A failed create now looks the model up again. See
    [[knowledge/debugging/Parallel first publishes raced to create the dg-validation model (F-09)|debugging]].
- **Stand rollout 2:** `dg-data-service:f09-2c5f5bc`, rollback tag `rollback-f09`.
- **Owner's result: the check from the demo PC publishes normally and everything works.**
- **Checks:**
  - tests: `test_property_scripts`/`test_revit_check` and the calculator suites are green;
  - the connector tests: 438;
  - the only failures are host-only Neo4j tests, which fail the same way without the change;
  - each rollout was verified in the running container (file hashes, catalogue, Speckle tokens and binding).

## Decisions Made

- Owner: no new Contabo snapshot for these rollouts; rollback goes through image tags.
- Owner: set up Speckle from the server and keep its web UI closed at the edge.
- Owner: deploy `993b709` (delete fix) and F-09 to the stand.

## Issues Encountered

- On Windows, `git archive` writes CRLF, so the stand files differ by hash. Compare hashes with CR stripped.
- data-service has no `/health` route. `/auth/me` answering 401 shows it is up.
- In Git Bash, `tar` reads `C:` as a remote host, and `curl` loops mangle `/paths` (use `MSYS_NO_PATHCONV=1`).
- `serverInfoUpdate` needs the server `name` together with `inviteOnly`. The first attempt left registration open,
  and a second session closed it.
- The first F-09 rollout was refused by the permission layer (remote writes). It ran after the owner's explicit
  authorization.

## Next Steps

1. Localhost: rebuild data-service from the current commit (F27/F-07, delete fix, F-08, F-09).
2. Stage 2: the mapping view in the Model Viewer (F-06, D-78).
3. Later, as a separate decision: open the Speckle web UI on the stand, or keep it server-managed.
4. Another DG project on the stand needs its own Speckle project and binding. No server-wide default is set.

## Related Notes

- `.planning/quick/261029-dmt-multi-user-demo-test-fixes/261029-dmt-SUMMARY.md`
- [[sessions/2026-10-29 Revit rule checks without Grasshopper, stand update and F-07 ingest fix|earlier session the same day]]
- Commits: `93e3c11`, `9b55b26`, `b2c163d`, `2c5f5bc`, `300b2cd`
