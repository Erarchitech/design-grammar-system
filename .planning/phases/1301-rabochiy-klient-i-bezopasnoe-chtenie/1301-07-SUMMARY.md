---
phase: 1301-rabochiy-klient-i-bezopasnoe-chtenie
plan: 07
subsystem: revit-adapter-read-only
tags: [revit-mcp, pyrevit-routes, allowlist, read-only, loopback, document-identity, fail-closed, tdd]
requires: [1301-03]
provides:
  - "apps/revit-mcp degram_readonly.py: ALLOWED_TOOLS (8), ALLOWED_ROUTES (8), ALLOWED_ROUTE_MODULES, ReadOnlyApi / ReadOnlyToolRegistry filters, enforce_transport, loopback probe, pyRevit config reader"
  - "pyRevit extension registers only the 8 allowlisted routes, and nothing unless the Routes host is loopback"
  - "MCP server exposes exactly the 8 allowlisted tools; stdio only under DEGRAM_MODE=1"
  - "list_open_documents / get_selection_snapshot (revit_mcp/documents.py, tools/degram_tools.py), identity-pinned on creationGuid + pathName"
  - "DegramClient: serialized calls, 30 s deadline to BUSY, structured outcomes, SETUP_INCOMPLETE/ROUTES_NOT_LOOPBACK before every read"
  - "DEGRAM.md and tests/tool_contract.json drift test"
affects: [1301-11, 1301-15]
tech-stack:
  added: []
  patterns:
    - "One allowlist module imported by both the IronPython extension and the CPython server, so the two layers cannot drift"
    - "Route filtering by proxy (ReadOnlyApi) rather than by deleting upstream modules: mixed read/write modules stay importable, their write routes are never registered"
    - "Structured outcome objects ({status:error, code, error, ...}) serialized to JSON text once, in a helper wrapper, instead of free-text Error: strings"
key-files:
  created:
    - apps/revit-mcp/degram_readonly.py
    - apps/revit-mcp/revit_mcp/documents.py
    - apps/revit-mcp/tools/degram_tools.py
    - apps/revit-mcp/tests/test_degram_readonly.py
    - apps/revit-mcp/tests/test_degram_documents.py
    - apps/revit-mcp/DEGRAM.md
    - .planning/phases/1301-rabochiy-klient-i-bezopasnoe-chtenie/1301-07-SUMMARY.md
  modified:
    - apps/revit-mcp/startup.py
    - apps/revit-mcp/main.py
    - apps/revit-mcp/tools/__init__.py
    - apps/revit-mcp/revit_mcp/status.py
    - apps/revit-mcp/revit_mcp/model_info.py
    - apps/revit-mcp/tests/tool_contract.json
key-decisions:
  - "Route allowlist is (method, pattern) pairs enforced by a proxy, not just a module list, because views/placement/parameters/colors mix read and write routes (set_parameter, color_splash, place_*)"
  - "tools/__init__.py lists only the six modules that host an allowed tool AND registers through ReadOnlyToolRegistry (belt and braces); unlisted upstream tool modules are never imported"
  - "Loopback refusal is code SETUP_INCOMPLETE with reason ROUTES_NOT_LOOPBACK (per the plan's D-23 truth); ROUTES_DISABLED and EXTENSION_NOT_LOADED are their own codes; NO_DOCUMENT_OPEN and REVIT_HOST_NOT_LOOPBACK are further SETUP_INCOMPLETE reasons"
  - "The structured client is a new subclass DegramClient in main.py; the upstream RevitClient and its tests are untouched"
  - "ROUTES_DISABLED is derived on a refused connection from [routes] enabled=false in pyRevit_config.ini, because pyRevit has no 'disabled' HTTP response (a disabled server does not listen)"
  - "Only get_selection_snapshot is identity-pinned; the other read tools read the active document (pyRevit limitation), documented as a residual in DEGRAM.md and handed to the plan 11 client"
requirements-completed: []
requirements-partial: [DGCL-04, DGCL-06]  # Revit adapter half (read-only allowlist, loopback, identity, snapshot); DeGram client wiring, picker UI and cancel are plans 11+
duration: ~45 min
completed: 2026-10-05
status: complete
---

# Phase 1301 Plan 07: Read-only, loopback-only, identity-addressed Revit adapter Summary

The Revit MCP fork now exists on the wire only as 8 read tools over 8 read routes: execute_code, save_document and every create/modify/delete/transform/tag/color/link/load/export route and tool are never registered, the extension registers nothing off loopback, the MCP server refuses reads when port 48884 answers on a non-loopback address, and selection reads are addressed by document identity (creationGuid + pathName) instead of "whatever is active".

## What was built

- **Task 1 (tracer), component `b6cdde8`.** `degram_readonly.py` holds `ALLOWED_TOOLS`, `ALLOWED_ROUTES`, `ALLOWED_ROUTE_MODULES`. `startup.py` reads `user_config.routes_host` and registers nothing unless it is explicitly loopback (unreadable or unset counts as not loopback); otherwise it calls only the seven allowed `register_*` functions through `ReadOnlyApi`, which drops every other route declaration of the mixed modules. `tools/__init__.py` lists six modules and registers through `ReadOnlyToolRegistry`. `main.py` refuses `--http/--sse/--combined` when `DEGRAM_MODE=1` (exit 2, `DEGRAM_TRANSPORT_REFUSED` on stderr). `status` and `model_info` handlers now take `doc` so pyRevit runs them through ExternalEvent (they used `revit.doc` off the API context). `tool_contract.json` regenerated to the 8 tools. `documents.py` was a declared skeleton (routes and API-context signatures fixed, 501 body).
- **Task 2, component `937384f`.** `documents.py` implements `list_open_documents` (skips linked and family documents; title, pathName, creationGuid, isActive, isModified) and `selection_snapshot` (DOCUMENT_NOT_OPEN, IDENTITY_MISMATCH with reason PATH_DIFFERS / NOT_ACTIVE_DOCUMENT, BAD_REQUEST, empty selection ok; uniqueId, elementId, category, typeName, parameters with storage type, unit, display value and raw value; limits clamped to 1000/200 with `truncation` disclosing totals and cuts). `DegramClient` in `main.py`: one asyncio lock (waiting past 30 s is BUSY), refusal before every read from REVIT_HOST, configured pyRevit host, or the probe (`getaddrinfo` + `gethostbyname_ex` over the host name, 300 ms connect per non-loopback address), transport mapping (timeout/406/408 BUSY, refused BRIDGE_OFF or ROUTES_DISABLED, 404 EXTENSION_NOT_LOADED, 503 no-document SETUP_INCOMPLETE, other ROUTE_ERROR), no retry. `DEGRAM.md` documents allowlists, identity contract, codes, loopback rule and the install steps (pyRevit 6.5.3).

## TDD

Task 1 RED: `tests/test_degram_readonly.py` failed at collection (`degram_readonly` missing). GREEN: 62 tests passing in the component after the contract regeneration. Task 2 RED: `tests/test_degram_documents.py` against the committed skeleton gave 21 failures and 22 fixture errors. GREEN: full component suite **110 passed** (22 upstream baseline plus 88 new: 40 in test_degram_readonly, 48 in test_degram_documents), `uv run --frozen pytest -q`, no Revit, no pyRevit, no network.

## Verification

- Exact-set tests: tools registered by FastMCP == ALLOWED_TOOLS == keys of `tool_contract.json`; routes registered through a stubbed `pyrevit.routes.API` (the real `views`, `placement`, `parameters`, `colors`, `status`, `model_info` modules imported under stubs) == ALLOWED_ROUTES; every upstream tool module registered through the wrapper yields only allowlisted names while the raw registration proves `execute_revit_code`, `save_document`, `set_parameter` exist upstream; no tool name has a mutating verb; forbidden routes parametrized as unreachable; every registered handler declares doc/uidoc/uiapp.
- Loopback: extension registers nothing for host `0.0.0.0`, a LAN address, `::`, a name, empty or unreadable; registers for `127.0.0.1`, `localhost`, `::1`, `127.0.0.2`, quoted. Probe with `_connect` patched to answer on a LAN address gives SETUP_INCOMPLETE/ROUTES_NOT_LOOPBACK and no request reaches the HTTP transport; a real-socket test covers `_connect` itself.
- Transport: `DEGRAM_MODE=1 python main.py --http|--sse|--combined` exits non-zero with `DEGRAM_TRANSPORT_REFUSED` (real subprocess).
- Smoke (stdio, `DEGRAM_MODE=1`, no Revit running): the server lists exactly the 8 tools and `list_open_documents` returns the structured `{"status":"error","code":"BRIDGE_OFF",...}`.
- `git -C apps/revit-mcp status --short` clean; no push; gitlink not bumped.

## Deviations from Plan

**1. [Rule 3 - Blocking] Mixed route modules need route-level filtering**
- **Issue:** the plan's `ALLOWED_ROUTE_MODULES` (module to register function) cannot alone keep write routes out: `parameters.py` also declares `set_parameter`, `colors.py` `color_splash`/`clear_colors`, `placement.py` the place routes, and `views.py` non-allowlisted reads.
- **Fix:** added `ALLOWED_ROUTES` (method, pattern) and the `ReadOnlyApi` proxy; the module list stays as the plan describes.
- **Files:** `degram_readonly.py`, `startup.py`.

**2. [Rule 3 - Blocking] `socket.connect` monkeypatch breaks asyncio on Windows**
- **Issue:** patching `socket.socket.connect` (as the plan words the loopback probe test) also breaks the Proactor loop's own socketpair, so every test creating a loop failed.
- **Fix:** the probe connects through a module-level `_connect(addr, port, timeout)` seam that tests patch; one real-socket test exercises `_connect` itself. Behavior is the same as the plan's.
- **Files:** `degram_readonly.py`, `tests/test_degram_documents.py`.

**3. [Rule 2 - Missing critical] Additional fail-closed checks**
- Added REVIT_HOST must be loopback and a config-host check (`pyRevit_config.ini` `[routes] host`) in front of the live probe, and a stderr-only startup probe report in `__main__`. Also `image()` on `DegramClient` returns a refusal outcome (the image tool is not registered, but the helper is still passed in).

**4. New files outside the plan's `files_modified`**
- `tools/degram_tools.py` (the plan asks for "a DeGram tools module" without listing it) and `revit_mcp/documents.py` shipped as a skeleton in Task 1 so the contract and route set were stable. `test_offline.py` was not modified (still passes against the updated contract); structured outcomes live in a new `DegramClient` subclass so upstream `RevitClient` tests are unchanged.

**5. Plan-text reconciliation (not a code deviation)**
- Loopback refusal is `code: SETUP_INCOMPLETE` with `reason: ROUTES_NOT_LOOPBACK` (the truth text) rather than a top-level `ROUTES_NOT_LOOPBACK` code; plan 11 reads "SETUP_INCOMPLETE/ROUTES_NOT_LOOPBACK", consistent.

## Not verified (honest limits)

- No live Revit or pyRevit session was started (forbidden). The IronPython handlers (`documents.py`, status, model_info) are tested against fake Revit objects and stubbed `pyrevit` modules only: real behavior of `Document.CreationGUID`, `Parameter.GetUnitTypeId()` + `LabelUtils.GetLabelForUnit`, `Selection.GetElementIds()` and the ExternalEvent threading is unverified here and belongs to the UAT plan. `value` of Double parameters is the raw Revit internal value (documented).
- `read_routes_config()` uses `configparser`, which only exists under CPython; under IronPython 2.7 it falls back to "unknown" (the extension side does not use it; it reads `user_config.routes_host`).
- Upstream `README.md`, `LLM.txt`, `SECURITY.md` and `tests/live/*` still describe the unrestricted 48-tool server; DEGRAM.md states they do not apply to this fork. They were left untouched.

## Workspace verify note (expected condition)

`python tools/degram/workspace.py verify` now reports `Submodule gitlink does not match the selected component HEAD` for `apps/revit-mcp` (child HEAD `937384f` is two commits ahead of the pin `74a8ddca`). This is the expected condition per the owner authorization: plans 04 and 07 both advance children ahead of their pins until plan 15 pushes and bumps the gitlinks. It was not worked around and `workspace.py` was not edited.

## Known Stubs

None. (The Task 1 `documents.py` skeleton was replaced in Task 2.)

## Threat Flags

None beyond the register. T-1301-07-01/03 (execute_code and mutating routes): not registered, exact-set tests on both layers. T-1301-07-02: startup refuses non-loopback host, probe fail-closed (tested). T-1301-07-04: identity-pinned snapshot (tested). T-1301-07-05: serialized lock, 30 s BUSY, no retry (tested). T-1301-07-06: accepted, documented in DEGRAM.md.

## Commits

- Component (apps/revit-mcp, local branch `degram/phase-1301`, not pushed):
  - `b6cdde8` feat(1301-07): allowlisted read-only registration on both layers, stdio-only in DeGram mode
  - `937384f` feat(1301-07): identity-pinned document reads and fail-closed loopback client
- Framework: docs commit for this SUMMARY, STATE.md and ROADMAP.md (no gitlink bump).

## Self-Check: PASSED

- Files exist: `degram_readonly.py`, `revit_mcp/documents.py`, `tools/degram_tools.py`, `tests/test_degram_readonly.py`, `tests/test_degram_documents.py`, `DEGRAM.md` under `apps/revit-mcp`.
- Commits `b6cdde8` and `937384f` exist on `degram/phase-1301`; neither deleted files.
- `uv run --frozen pytest -q`: 110 passed; `git -C apps/revit-mcp status --short` empty.
