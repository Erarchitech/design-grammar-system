---
quick_id: 261027-sgc
slug: install-connectors-from-the-degram-conne
date: 2026-10-27
mode: quick
repositories: [component, framework]
---

# Quick 261027-sgc: install connectors from the DeGram Connectors tab

## Goal

The user installs a DG connector with one button in DeGram's «Коннекторы» tab and never runs a script.
The hosted connectors table gets an **Installed** column. Each installable connector shows an **Install**
button there, or **Ready** when the installed copy matches the bundled one.

## Decisions (owner, 2026-10-27)

- Installable connectors: **Revit** and **Grasshopper**. Every other registry row shows «—».
- Revit installs **only the pyRevit extension**: the `install.py` copy set from the bundled
  `resources\revit-mcp` into `%APPDATA%\pyRevit\Extensions\dg-revit-connector.extension`.
  The MCP Python environment is not touched.
- Grasshopper installs the bundled DG plugin (`resources\dg-grasshopper`: `DG.gha` plus its DLLs) into
  `%APPDATA%\Grasshopper\Libraries\DG`.
- The request comes from the untrusted DG page, whose view has no preload. **A native DeGram confirmation dialog**
  must accept it before anything is written.
- Local commits in both repositories, no push, no gitlink bump.

## Design

Page and host already talk through URL fragments (`ui-v2/src/lib/hostMode.js` ↔ `electron/degram/dg-view.ts`).
Three new closed-vocabulary fragments:

| Fragment | Direction | Meaning |
|---|---|---|
| `#degram-connectors-check` | page → host | Report the install state |
| `#degram-install=revit\|grasshopper` | page → host | Install request; main shows a confirmation dialog first |
| `#degram-installed=<id>:<state>[,<id>:<state>]` | host → page | `state` ∈ `ready install installing unavailable needs-host locked failed` |

- `ready`: every bundled file is present in the target with the same SHA-256.
- `install`: the package is bundled but not installed, or the installed copy differs from it.
- `unavailable`: this DeGram build does not carry the package, or the bundled Revit adapter is the old read-only
  `apps/revit-mcp` without `DG.tab`.
- `needs-host`: Revit only. pyRevit was not found: no `%APPDATA%\pyRevit-Master`, no `%PROGRAMDATA%\pyRevit-Master`
  and no `%APPDATA%\pyRevit\pyRevit_config.ini`.
- `locked`: a target file is held open (Rhino or Revit is running). Nothing was changed.
- `failed`: anything else. The backup path is logged, never sent to the page.

Install safety (ported from `apps/dg-revit-connector/install.py`):

- refuse a target that exists but is not ours: Revit without `extension.json`, Grasshopper without `DG.gha`, while
  non-empty;
- check the lock first: open every file that will be overwritten with `r+`. `EBUSY`/`EPERM` means `locked`, before
  any change is made;
- back up an existing target by copying it to `%LOCALAPPDATA%\DG\connector-backups\<id>\<UTC stamp>\`;
- Revit replaces the extension folder, so stale buttons disappear. Grasshopper overwrites files in place;
- single-flight: a second request while a dialog or an install is open is ignored, so a page cannot stack dialogs.

Build pipeline, so the current add-ins reach DeGram:

- `electron-builder.config.cjs` bundles `resources/dg-grasshopper` from `DEGRAM_DG_GRASSHOPPER_SOURCE`.
  The default is the framework's `DG/src/DG.Grasshopper/bin/Release/net48`, the build that Rhino 8 and RiR/Revit 2024
  both load (1303-24). It is skipped when `DG.gha` is absent, and the button then reports `unavailable`.
- The default Revit adapter source becomes `../../../dg-revit-connector` (D-44..D-46; `config_template.yaml` already
  launches that connector).
- Framework `tools/degram/stage_connector_payloads.py`: `dotnet build` of DG `net48` Release at the current commit.
  It then stages `dg-grasshopper/` and `dg-revit-connector/` into one output folder with `connector-manifest.json`
  (framework commit, dirty flag, SHA-256 per file). The build driver points both `DEGRAM_*_SOURCE` variables there.
  One command produces a recorded, current payload pair for every DeGram build.

## Tasks

### Task 1 — component: install service, signals, wiring, bundling (repository: component `apps/degram`)

files:
- `apps/degram/apps/desktop/electron/degram/connector-install.ts` (new)
- `apps/degram/apps/desktop/electron/degram/connector-install.test.ts` (new)
- `apps/degram/apps/desktop/electron/degram/dg-view.ts`, `dg-view.test.ts`
- `apps/degram/apps/desktop/electron/degram/ipc.ts`, `ipc.test.ts`
- `apps/degram/apps/desktop/electron/degram/main-wiring.ts`
- `apps/degram/apps/desktop/electron/main.ts` (deps only: paths and dialog)
- `apps/degram/apps/desktop/electron-builder.config.cjs`

action: implement the service with injectable paths, filesystem and clock. Parse the two page fragments in
`did-navigate-in-page`. Allow `#degram-installed=` in `signal()`. In the runtime, check → status signal and
install → `confirmInstall` → install → status signal, single-flight. Pass `resourcesPath`, `APPDATA`,
`LOCALAPPDATA`, `PROGRAMDATA` and a `dialog.showMessageBox` confirmation (RU/EN by the DG locale) from `main.ts`.
Add the bundling entry and the new Revit default.

verify: `npx vitest run electron/degram` and `npm run typecheck` in `apps/degram/apps/desktop`; changed-file eslint.

done: all three fragments are covered by tests, including the rejection of a foreign or out-of-vocabulary hash. The
service tests cover ready, install, unavailable, needs-host, locked (nothing changed), refuse-foreign-target, backup
and Revit stale-file removal.

### Task 2 — framework: Installed column (repository: framework)

files:
- `ui-v2/src/lib/hostMode.js`, `ui-v2/src/App.jsx`, `ui-v2/src/screens/HostedConnectorsTable.jsx`
- `ui-v2/src/i18n/dict/connectors.js` (RU)
- `ui-v2/tests/host-degram.test.mjs`, `ui-v2/tests/degram-grants.test.mjs` (or the hosted-table test that exists)

action: `requestConnectorStatus()` and `requestConnectorInstall(id)` (host mode only, closed id set). Parse
`#degram-installed=`. App dispatches `dg-connector-install`. The table adds the «Installed» column between Access
and Status and asks for the state on mount and on Refresh.

verify: `npm --prefix ui-v2 test`, `npm --prefix ui-v2 run build`.

done: Revit and Grasshopper rows show Install, Ready, «Installing…» or a hint. Other rows show «—». Outside DeGram
nothing is requested.

### Task 3 — framework: payload staging (repository: framework)

files: `tools/degram/stage_connector_payloads.py`, `tools/degram/tests/test_stage_connector_payloads.py`,
`docs/degram/CLEAN-INSTALL.md` (Revit/Grasshopper steps → the button).

verify: `python -m unittest discover -s tools/degram/tests -v`; one real `--no-build` dry staging into the
scratchpad.

done: the manifest records the commit and hashes, tests/`__pycache__`/`.pdb` are excluded, a missing `DG.gha`
fails loudly.

## Not in scope

Pushing to the fork, the gitlink bump, a DeGram installer build or launch (needs a fresh owner decision per
CLAUDE.md), the MCP Python environment, and editing `D:\dgb\run-build.sh` (outside the repository; the summary gives
the two lines to add).
