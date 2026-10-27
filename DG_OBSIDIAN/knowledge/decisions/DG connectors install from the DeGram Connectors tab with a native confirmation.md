---
tags: [decision, degram, connectors, revit, grasshopper, security, v13.0]
date: 2026-10-27
status: implemented (component ba10f004, framework c286c91); live check in DeGram open
---

# DG connectors install from the DeGram Connectors tab with a native confirmation

## Context

Users had to install the DG add-ins by hand:

- Revit: `python install.py` for the pyRevit extension;
- Grasshopper: copy `DG.gha` into the Libraries folder.

The owner's requirement (2026-10-27) is that the user never runs a script. A connector installs from DeGram's
«Коннекторы» tab with one button, and the tab shows **Ready** when the connector is already installed.

## Decision (owner, 2026-10-27)

1. **Installable connectors: Revit and Grasshopper.** Every other registry row shows «—».
2. **Revit installs only the pyRevit extension.** It uses the `install.py` copy set and goes to
   `%APPDATA%\pyRevit\Extensions\dg-revit-connector.extension`. The MCP Python environment is not touched: it needs a
   package install, which is outside the authorized boundary.
3. **Grasshopper installs the bundled net48 plugin** to `%APPDATA%\Grasshopper\Libraries\DG`. Rhino 8 and
   Rhino.Inside.Revit 2024 both load that build.
4. **The request comes from the untrusted DG page and is never an authority.** The DG view keeps its no-preload
   design. The page only sets closed-vocabulary URL fragments (`#degram-connectors-check`,
   `#degram-install=revit|grasshopper`). Main shows a **native confirmation dialog** before writing anything, then
   answers with `#degram-installed=<id>:<state>`.
5. Paths come only from the two fixed packages and fixed targets. Nothing from the page reaches a path. The installer:
   - refuses a target that is not an earlier installation;
   - stops before any change when a file is held (Rhino or Revit running);
   - backs up the previous copy to `%LOCALAPPDATA%\DG\connector-backups\<id>\<UTC>`;
   - runs one dialog at a time.
6. **Ready** means every bundled file is present in the target with the same SHA-256.
7. **The build always bundles the current add-ins.**
   - `tools/degram/stage_connector_payloads.py` builds DG net48 at the current commit and stages both payloads with a
     manifest (commit, dirty flag, hashes).
   - The DeGram build reads them from `DEGRAM_DG_GRASSHOPPER_SOURCE` and `DEGRAM_REVIT_MCP_SOURCE`.
   - Without `DG.gha` nothing is bundled, and the column says «Нет в этой сборке DeGram» instead of installing a
     stale copy.

## Consequences

- `docs/degram/CLEAN-INSTALL.md` step 2 is the button. Manual `install.py` stays a developer fallback.
- Every DeGram build needs the staging step first. `D:\dgb\run-build.sh` lies outside the repository; add the two
  exports there.
- An older DeGram that lacks the feature never answers the check, so the column stays at «—». It does not break.

## Related

- [[sessions/2026-10-27 DG connectors install from the DeGram Connectors tab]]
- [[knowledge/debugging/DeGram installers bundled a stale revit-mcp copy from the build folder]]
- [[knowledge/decisions/DeGram Phase 1301 client isolation, auth relay and Revit MCP fork]]
