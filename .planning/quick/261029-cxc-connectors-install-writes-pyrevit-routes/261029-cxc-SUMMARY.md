---
phase: quick-261029-cxc
plan: 01
status: complete
date: 2026-10-29
---

# Install for Revit sets pyRevit Routes itself

Implemented and tested offline in the component. **Not built into an installer, not pushed to the fork, not run
on a PC**: the 0.1.16 installer does not exist yet.

## Delivered (component commit `aac8353c` on `degram/milestone13`, local only)

- `connector-install.ts`: `ensureRoutesLoopback` and the Revit `settings` step. Clicking **Установить** now also
  writes `[routes] enabled = true`, `host = "127.0.0.1"` into `%APPDATA%\pyRevit\pyRevit_config.ini`, adding the
  section or keys when missing, replacing a non-loopback host or `enabled = false`, keeping every other line, the
  line endings and a BOM. The previous ini is saved under
  `%LOCALAPPDATA%\DG\connector-backups\revit-settings\<stamp>`. The column reads **Установить** again while only the
  settings are wrong, and that click repairs just them (extension untouched, no extension backup). A non-UTF-8 ini
  is left as it is and the install reports `failed`. Grasshopper is unaffected.
- Dialog text (ru/en) names the Routes setting and asks for a Revit restart; the three Routes error texts point to
  the Connectors tab. Desktop installer version 0.1.16.
- `docs/degram/CLEAN-INSTALL.md` (framework): steps 2–4 and the failure table.

## Verified

- `connector-install.test.ts` 22 passed (10 new); `electron/degram` + `src/degram` 690 passed, 1 skipped;
  eslint clean on the changed files; `degram-build.test.mjs` shows only the 2 known MSIX/updater failures.

## Open

- Build 0.1.16 (`D:\dgb\run-build.sh`), push the component commit to the fork and bump the gitlink (publishes: needs
  the owner's go-ahead), install on the second PC and check the sequence: Install → restart Revit → model appears.
- If Revit is running when Install is clicked, pyRevit keeps its old Routes until Revit restarts; the dialog says
  so, but the column already reads «Готов».
- Not covered: a PYREVIT_CONFIG override, a per-machine (ProgramData) pyRevit config that overrides the user file,
  and a pyRevit that rewrites its ini from memory when Revit closes (not observed, not ruled out).
