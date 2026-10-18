---
phase: 1303-pravilo-gh-obekt
plan: "13"
status: complete
completed: 2026-10-18
requirements: [DGMAP-06]
component_commits: [1aa3b39cd62e1500e63d7b674eb65297179e34a0]
connector_export_commit: 8c69edf
executor: "DSH Flash and Claude implementation/review; controller integration, acceptance, commit, build and launch"
---

# 1303-13 Summary — DeGram with the DG Revit connector

## Delivered

- DeGram accepts every `mcp__revit__*` tool from its configured Revit server. Other server/tool restrictions remain unchanged. The child stays stdio-only in `DEGRAM_MODE=1`.
- The Mapping service and RPC support Revit connector status, start/read-again, session matching by document key, and resolving a stream row to UniqueIds for select/zoom. Grasshopper retains its existing start/focus path.
- The Mapping sub-tab has RU/EN Revit status, sign-in guidance, start/read-again and clickable stream rows. Read-again waits for a different session id.
- Source committed only in `D:\dgb\src`, branch `feature/mapping-mvp`: `1aa3b39c`. No push or framework gitlink bump.

## Controller verification

Before the build:
- Focused DeGram Python suites: **299 passed, 1 skipped**.
- `vitest run src/degram`: **319 passed, 1 skipped, 1 failed**. An explicit rerun confirmed the known `ru-catalog-completeness.test.ts` settings assertion (`settings.plugins.installModal.repoPlaceholder`, identical URL placeholder in EN/RU). No new green all-suite claim.
- Renderer and Electron TypeScript checks passed. Generated-contract tests and changed-file lint passed in the implementation review.
- Framework-side connector suite: **400 passed**; mapping suite: **63 passed** (recorded in plans 11/12).

Build and launch:
- `D:\dgb\run-build.sh` uses the clean framework export `D:\dgb\dg-revit-connector-src\8c69edf`; previous driver retained as `run-build.sh.pre-1303-13`.
- Build log: start `2026-10-18T21:32:35Z`, component `1aa3b39cd62e1500e63d7b674eb65297179e34a0`; **exit 0 at `2026-10-18T21:49:31Z`**.
- Binary: `D:\dgb\src\apps\desktop\release\win-unpacked\DeGram.exe`, 213,939,200 bytes.
- Controller compared **88 exported/bundled files** byte-for-byte by SHA-256. Required Python/XAML/YAML/shared-parameter payload present; no mismatches.
- Launched on 2026-10-18 from this exact unpacked directory with `HERMES_*` and `ELECTRON_RUN_AS_NODE` removed. Adapter path explicitly pinned to the bundled `resources\revit-mcp`; `PYTHONDONTWRITEBYTECODE=1`. The MCP interpreter is the existing original adapter venv, used read-only; no package installation.
- Main PID 54760: window title `DeGram`, `Responding=true`. Backend image is under this build's `resources\agent-payload`. Installed Hermes processes were observed but neither stopped nor modified.
- A **separate controller stdio MCP session against the exact bundled `main.py`**, not an internal Desktop RPC, initialized as `DG Revit Connector` and listed **54 tools**. All four DG tools were present: `dg_mapping_status`, `dg_start_mapping`, `dg_show_elements`, `dg_clear_mapping_colours`. Write registrations included `set_parameter`, `delete_elements`, creation tools and `execute_revit_code`; no write tool was invoked.
- `dg_mapping_status` returned the structured code **`BRIDGE_OFF`** for `http://127.0.0.1:48884/dg_revit`. Revit was not running. This is the accepted plan-13 bridge-off condition, not live mapping acceptance or proof that Desktop has already invoked this adapter.

## Workspace and boundaries

`python tools/degram/workspace.py verify` fails in this worktree with `Missing context: ...\apps\degram\AGENTS.md` because its component submodule is not checked out. Plan 13's pre-existing context explicitly assigns component work to the owner-authorized standalone build clone `D:\dgb\src`, as in plan 10. No missing submodule was initialized and no generated context was installed to bypass the failure.

The main checkout/1309 source was not edited or committed. The runtime Python path above is a read-only dependency, not a component source change. No Hermes profile files were inspected. No LLM request, profile activation, mapping session creation, model edit or Revit write was performed by the launch/probe.

## Handoff to plan 14 — blocking human action

The previous actual pyRevit installation command was denied by the permission mechanism as `Unauthorized Persistence`. It has **not** been retried through another tool or process. Plan 14 cannot proceed until installation is performed by the owner or explicitly allowed through the permission mechanism.

Prepared local model copy: `D:\dgb\revit-models\AdaptComponent_V18-dg-mapping.rvt` (SHA-256 recorded in plan-14 checkpoint). Owner installation, opening the copy, pyRevit reload and DG ribbon sign-in remain outstanding. Real family counts/adaptive-point counts, gold, colours/shared parameters, select/zoom, read 2 and precision/recall are **not verified**. UAT test 12 remains open; demo profiles stay retired.
