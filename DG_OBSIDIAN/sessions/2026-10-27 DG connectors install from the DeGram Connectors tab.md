---
tags: [session, degram, connectors, revit, grasshopper, v13.0, quick]
date: 2026-10-27
---

# Session: 2026-10-27 — DG connectors install from the DeGram Connectors tab

## Goal

1. Answer how the DG Revit connector is installed on a user's PC.
2. Run the quick task that followed (`/gsd-quick`, 261027-sgc). The user must never run a script to install a
   connector. The «Коннекторы» tab gets an **Installed** column with an **Install** button per available connector,
   or **Ready** when the connector is already installed.

## What Was Done

- **Analysis.** The DG Revit connector (`apps/dg-revit-connector`) has two halves. The pyRevit extension used to be
  copied by hand with `python install.py`. The MCP server runs from DeGram's `resources\revit-mcp`. It needs its own
  Python with `mcp` 1.x (`uv sync`).
  - `docs/degram/CLEAN-INSTALL.md` still described the retired read-only `apps/revit-mcp` adapter.
  - Since 1303-13 the build has bundled the DG connector into `resources\revit-mcp`, but the builder default still
    pointed at `apps/revit-mcp`.
  - DG.gha was never bundled.
- **Owner decisions** (see the decision note):
  - installable connectors are Revit and Grasshopper;
  - Revit installs the pyRevit extension only;
  - a native DeGram confirmation comes before any write;
  - local commits only, no push.
- **Component `ba10f004`** (`apps/degram`, `degram/milestone13`, not pushed):
  - `electron/degram/connector-install.ts`. States `ready / install / installing / unavailable / needs-host /
    locked / failed`. `ready` means SHA-256 equality with the bundle. Safety: foreign-target refusal, a lock check
    before any change, and a backup to `%LOCALAPPDATA%\DG\connector-backups\<id>\<UTC>`. Revit copies the
    `install.py` copy set and replaces the folder; Grasshopper overwrites in place.
  - Page fragments `#degram-connectors-check` and `#degram-install=revit|grasshopper`. Host fragment
    `#degram-installed=<id>:<state>[,…]`.
  - The runtime runs the confirmation dialog (RU/EN), one dialog at a time, and answers every request.
  - `electron-builder` bundles `resources/dg-grasshopper` from `DEGRAM_DG_GRASSHOPPER_SOURCE`, by default
    `DG/src/DG.Grasshopper/bin/Release/net48`, and only when `DG.gha` exists. The Revit default became
    `apps/dg-revit-connector`.
- **Framework `c286c91`**:
  - `ui-v2` hosted table: **Installed** column («Установка») with Install / Ready / hints, RU strings, and the
    `hostMode.js` vocabulary;
  - `tools/degram/stage_connector_payloads.py`: `dotnet build` net48 Release, then both payloads staged with
    `connector-manifest.json` (commit, dirty flag for `DG/src` and the connector, SHA-256 per file);
  - `CLEAN-INSTALL.md` step 2 is now the button;
  - quick PLAN/SUMMARY and the STATE row.
- **Checks**:
  - Electron `electron/degram`: 329 passed, 1 skipped. Typecheck clean. ESLint has no new findings.
  - ui-v2 headless `run-grants.mjs host`: 11/11, including `GRANTS-host-installed-column`. Node tests 384/385.
    The build is OK.
  - `tools/degram` tests: 32 OK.
  - End to end on a real staged build (16 Grasshopper files, 89 Revit files) into a temporary `%APPDATA%`:
    `needs-host` → `install` → `ready`, and a reinstall made a backup. The Revit file set equals
    `install.py --dry-run` (49/49).

## Decisions Made

- [[knowledge/decisions/DG connectors install from the DeGram Connectors tab with a native confirmation|DG connectors install from the DeGram Connectors tab with a native confirmation]].

## Issues Encountered

- Pre-existing failures, identical on the unchanged tree:
  - two 5 s timeouts in `scripts/degram-build.test.mjs`;
  - `ui-v2/tests/browser-language.test.mjs` (`Cannot set property navigator`);
  - `npm --prefix ui-v2 test` fails because `node --test` with a directory argument fails on this Node.
- Builds modify the tracked `DG/src/*/obj` files. The dirty flag of the staging script therefore ignores
  `bin/` and `obj/` and looks at `DG/src` only.
- `App.jsx` and `hostMode.js` carried another session's unstaged `target-refused` lines, and the real index held its
  staged gitlink bump to `c6e82a5`. I committed only this session's hunks through a temporary index
  (`--unidiff-zero`) and left the foreign changes alone.
- The staging build left untracked `net48` output under `DG/src/*/bin|obj/{Debug,Release}/net48`. It is not
  committed.

## Next Steps

- Push `ba10f004` to the fork (owner authorization). Then bump the framework gitlink and run `workspace.py verify`.
- Before the next DeGram build:
  - run `python tools/degram/stage_connector_payloads.py --out <empty dir>`;
  - add `DEGRAM_DG_GRASSHOPPER_SOURCE` and `DEGRAM_REVIT_MCP_SOURCE` for the staged folders to `D:\dgb\run-build.sh`.
- Live check inside an owner-authorized DeGram build: the column, the native dialog, and Install → Ready for Revit
  (pyRevit Reload, DG ribbon) and Grasshopper (Rhino closed).
- The rest of `CLEAN-INSTALL.md` is still stale: Routes count and `revit_mcp` route names.

## Related Notes

- [[sessions/2026-10-27 DeGram 0.1.12 build verified awaiting isolated installation]]
- [[knowledge/debugging/DeGram installers bundled a stale revit-mcp copy from the build folder]]
- `.planning/quick/261027-sgc-install-connectors-from-the-degram-conne/261027-sgc-SUMMARY.md`
