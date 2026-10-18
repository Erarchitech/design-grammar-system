---
phase: 1303-pravilo-gh-obekt
plan: "11"
status: complete (offline); live behaviour in 1303-14
completed: 2026-10-19
requirements: [DGMAP-01, DGMAP-04, DGMAP-06]
executor: "controller (Claude): vendoring, review, commits; DSH flash workers for tasks 1, 2 and 3; a Claude subagent finished task 3–4 after the DSH hub stopped answering and reviewed and fixed the worker's output"
commits: [1868d08, a7f5e9a, 778b228, 36418bc]
---

# 1303-11 Summary — the DG Revit connector (Design Grammars' own revit-mcp fork)

## What was built

- **Fork** `apps/dg-revit-connector/`:
  - A plain-file copy of `Erarchitech/revit-mcp-server` `degram/phase-1301` `d8f0f24`, itself a fork of `Demolinator/revit-mcp-server`, recorded in `UPSTREAM.md`.
  - The package is renamed `revit_mcp` → `dg_revit_mcp` so it does not collide with the still-installed `revit-mcp.extension` in one IronPython runtime.
  - The read-only guards are gone (owner decision D-45). The pyRevit side registers every upstream route under Routes API `dg_revit`, only on a loopback host.
  - The MCP side has 54 tools: 48 upstream including 31 write-capable (`modify_element`, `delete_elements`, `set_parameter`, `place_family`, `execute_revit_code`, …), 2 identity-pinned document reads, and 4 `dg_*`. It runs stdio-only in DEGRAM_MODE.
  - `degram_readonly.py` is replaced by `dg_transport.py`.
- **Library** `lib/dg_connector/` (Python 3.4 syntax, guarded by a test):
  - descriptors identical to `tools/mapping/revit_read.py`, plus `geometry.vertexCount` from the adaptive placement points;
  - DG sign-in as connector `revit` (login → mint → logout). A `neo4j` block in the answer is never read, and no secret appears in any message;
  - the apply decision (recolour / 10 s grace / apply / done);
  - AppDomain-shared state;
  - the GH palette and the document key.
- **Revit side:**
  - `revit_io`:
    - scope: the selection, else the model instances visible in the active view;
    - element rows;
    - solid-fill colour overrides;
    - the shared parameters `DG_Class` / `DG_MappingState`, bound from `DG_SharedParameters.txt` while the user's own shared-parameter file is restored afterwards;
    - selecting and showing elements.
  - `runner`:
    - `start_mapping`;
    - a 3 s poll thread;
    - writes only through one `ExternalEvent`;
    - jobs bound to the session document's identity;
    - one poll owner across pyRevit reloads.
  - Routes `/mapping_status/`, `/start_mapping/`, `/show_elements/`, `/clear_colours/`.
  - Ribbon DG → Connector: «Вход» (WPF dialog; the password is not kept), «Меппинг DG», «Очистить цвета», «Выход».
  - `install.py`: installs beside `revit-mcp.extension` into `%APPDATA%\pyRevit\Extensions\dg-revit-connector.extension` with a timestamped backup, and refuses overlapping targets.

## Verification

- `python -m pytest -q -p no:cacheprovider tests` in the connector folder: **400 passed**, run by the controller.
- `install.py --dry-run` into a temp target: a 48-file plan, nothing written.
- The main-folder submodule `apps/revit-mcp` was only read through `git archive`.
- **Not verified yet, live only (1303-14):**
  - every real Revit API call: collector, adaptive points, overrides, shared-parameter binding, selection/zoom;
  - `ExternalEvent` raised from a thread;
  - XAML dialog loading;
  - pyRevit reload behaviour.

## Process notes

- The DSH hub stopped answering for a while. Its jobs kept running, so a DSH worker and a Claude subagent overlapped on task 3. The subagent waited for the worker to finish before writing, then reviewed and fixed its output. Its fixes:
  - the handler interface (`UI.IExternalEventHandler`);
  - `ReInsert` category loss for built-in categories;
  - jobs that could reach another document;
  - the `clear()` document;
  - double poll threads after a reload;
  - the permanent stop after a rejected token;
  - failure-dialog suppression;
  - installer footguns.
- Open risks named by the subagent:
  - the AppDomain state dictionary has no cross-engine lock (low risk);
  - «Выход» clears the session, so «Очистить цвета» afterwards cannot find the session view;
  - the README tool-table row for `dg_clear_mapping_colours` still says "active view";
  - the grace depends on the Revit PC clock agreeing with DG's `decidedAt` (same PC here).
- Four empty sandbox directories `pytest-cache-files-*` with a sandbox ACL remain untracked; they could not be deleted from a normal shell.
