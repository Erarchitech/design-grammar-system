---
quick_id: 261027-sgc
status: complete
date: 2026-10-27
component_commit: ba10f004 (apps/degram, branch degram/milestone13, not pushed; gitlink not bumped)
executor: Claude inline (owner rule: no DSH, no subagents)
---

# Quick 261027-sgc Summary: install connectors from the DeGram Connectors tab

## Delivered

**Component (`apps/degram`, commit `ba10f004`)**

- `electron/degram/connector-install.ts`. The install service for the two bundled packages:
  - **Revit** copies the `install.py` copy set from `resources\revit-mcp` to
    `%APPDATA%\pyRevit\Extensions\dg-revit-connector.extension`. The folder is replaced, so stale buttons go.
  - **Grasshopper** copies `resources\dg-grasshopper` (`*.gha`, `*.dll`) into `%APPDATA%\Grasshopper\Libraries\DG`,
    overwriting in place.
  - States: `ready`, `install`, `installing`, `unavailable`, `needs-host`, `locked`, `failed`. `ready` means every
    bundled file has the same SHA-256 in the target.
  - Safety: a foreign target is refused, held files are checked before any change, and the previous copy is backed
    up to `%LOCALAPPDATA%\DG\connector-backups\<id>\<UTC>`.
- `dg-view.ts` accepts `#degram-connectors-check` and `#degram-install=revit|grasshopper` only from the DG origin's
  main frame. `signal()` additionally allows `#degram-installed=<id>:<state>[,...]`.
- `ipc.ts`: the runtime shows the native confirmation (`dialog.showMessageBox`, RU/EN by the DG locale) before
  anything is written. One dialog or install runs at a time. Every request, including a cancelled one, is answered
  with the state.
- `main.ts` supplies `resourcesPath`, `APPDATA`, `LOCALAPPDATA`, `PROGRAMDATA` and the dialog.
- `electron-builder.config.cjs`:
  - `resources/dg-grasshopper` comes from `DEGRAM_DG_GRASSHOPPER_SOURCE`, by default
    `DG/src/DG.Grasshopper/bin/Release/net48`. It is bundled only when `DG.gha` exists.
  - The default Revit source is now `apps/dg-revit-connector`.

**Framework**

- `ui-v2`:
  - Hosted connectors table: new **Installed** column between Access and Status. Revit and Grasshopper show
    Install, Ready, «Confirm in DeGram...», «Installing...» or a hint (pyRevit missing, not in this build,
    close Rhino/Revit, failed). Other rows show «—».
  - `hostMode.js` has the closed vocabulary. `App.jsx` dispatches `dg-connector-install`.
  - RU strings in `i18n/dict/connectors.js`.
- `tools/degram/stage_connector_payloads.py`:
  - one command builds DG `net48` Release and stages `dg-grasshopper/` and `dg-revit-connector/`;
  - `connector-manifest.json` records the commit, a dirty flag for `DG/src` and the connector, and the SHA-256 of
    every file;
  - it prints the two `export` lines for the build driver.
- `docs/degram/CLEAN-INSTALL.md`: step 2 is now the button. The Rhino prerequisite no longer asks for a manual copy.

## Verification (controller, 2026-10-27)

- `npx vitest run electron/degram`: **329 passed, 1 skipped**.
  - connector-install: 12 tests (ready/install/unavailable/needs-host/locked/foreign-target/backup/stale removal).
  - dg-view: 3 new tests.
  - ipc: 6 new tests (confirmation and locale, cancel, locked, single-flight, no installer).
- `scripts/degram-build.test.mjs`: the new bundling tests pass. Two pre-existing 5 s timeouts (`before-build never
  generates MSIX...` and `degram updater strategy...`) fail identically on the unchanged tree.
- `npm run typecheck`: clean. ESLint on the changed files is at or below the baseline counts; no new findings.
- `ui-v2`:
  - `node --test ui-v2/tests/*.test.mjs`: 384/385. `browser-language.test.mjs` also fails on the unchanged tree
    (`Cannot set property navigator`).
  - Headless `run-grants.mjs host`: 11/11 PASS, including the new `GRANTS-host-installed-column`.
  - `npm run build`: OK.
  - `npm test` itself fails before running any test: `node --test ui-v2/tests/` with a directory argument.
    This is pre-existing.
- `python -m unittest discover -s tools/degram/tests`: 32 OK.
- End to end on real payloads:
  - A staged build (`dotnet build -f net48` at `84c90d5`) gave 16 Grasshopper files and 89 Revit files.
  - The bundled installer was run against a temporary `%APPDATA%`:
    `needs-host` → (pyRevit config present) `install` → `ready` for both. A reinstall made one backup.
  - The installed Revit file set is identical to `install.py --dry-run` (49/49).

## Not verified / not done

- No DeGram installer was built or launched, and nothing was installed into the real `%APPDATA%`. Desktop
  launch/build needs a fresh owner decision (CLAUDE.md boundaries). The live check of the dialog and the column
  inside DeGram is open.
- The child commit is not pushed. The framework gitlink is not bumped; it may be bumped only after the commit is on
  the fork.
- `D:\dgb\run-build.sh` is outside the repository and was not edited. To bundle current add-ins, run the staging
  script and add:
  ```sh
  export DEGRAM_DG_GRASSHOPPER_SOURCE='<out>\dg-grasshopper'
  export DEGRAM_REVIT_MCP_SOURCE='<out>\dg-revit-connector'
  ```
- The staging build left untracked `net48` output under `DG/src/*/bin|obj/{Debug,Release}/net48` (build artefacts,
  not committed).
