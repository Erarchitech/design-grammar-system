# Upstream provenance of the DG Revit connector

`apps/dg-revit-connector/` is Design Grammars' own fork of revit-mcp. This file
records where the code came from and what Design Grammars changed.

## Origin

| Field | Value |
|-------|-------|
| Origin repository | `Erarchitech/revit-mcp-server` |
| Origin branch | `degram/phase-1301` |
| Origin commit | `d8f0f24` |
| Origin project | revit-mcp: an MCP server and pyRevit extension that expose the Autodesk Revit API over pyRevit Routes |
| Upstream of the origin | `Demolinator/revit-mcp-server` |
| Upstream merge base | `74a8ddc` (the commit whose `startup.py` and `tools/__init__.py` carry the full route and tool registration this fork restores) |
| Copied | 2026-10-18 |
| Copy method | `git archive d8f0f24` extracted into `apps/dg-revit-connector/` as **plain files** |
| Submodule | none. `apps/dg-revit-connector` is committed directly in the Design Grammars repository; the main-folder submodule `apps/revit-mcp` is not this copy and was only read as the copy source. |
| Push | none. This copy has no GitHub repository of its own and was not pushed anywhere. |

The origin at `d8f0f24` is a "DeGram" fork that had locked the project down to a
read-only allowlist (8 routes, 8 tools). That lockdown is gone here; see below.

Upstream project: <https://github.com/Demolinator/revit-mcp-server> (MIT, see
`LICENSE`). Credits: Talal Ahmed, based on work by Juan D. Rodriguez and
Jean-Marc Couffin.

## Owner decision: all Revit restrictions lifted (2026-10-18, D-45)

The Design Grammars owner lifted every restriction on Revit explicitly:
«разрешить запись и редактирование параметров и создание и удаление элементов в
revit. сними все ограничения». This is the fresh explicit decision on CAD writes
that `CLAUDE.md` requires.

Consequences for this fork:

- every upstream pyRevit Routes handler is registered, writes included:
  parameter writes, element creation and deletion, colour and graphic
  overrides, selection, view operations and code execution;
- every upstream MCP tool is exposed, so an MCP client (DeGram, Claude Desktop,
  Claude Code, anything speaking MCP) can modify the model;
- the phase 1301 read-only allowlists (`degram_readonly.ALLOWED_TOOLS`,
  `ALLOWED_ROUTES`, `ALLOWED_ROUTE_MODULES`, `ReadOnlyApi`,
  `ReadOnlyToolRegistry`) do not apply to this fork and have been removed.

Kept as **transport hygiene**, not as a Revit restriction:

- the pyRevit Routes host must be loopback before the extension registers
  anything, and the MCP client refuses a non-loopback `REVIT_HOST` or a Routes
  server answering on a non-loopback local address;
- in DeGram (`DEGRAM_MODE=1`) the MCP server is a stdio child: `--http`,
  `--sse` and `--combined` are refused, so no HTTP/SSE port is opened.

## Design Grammars changes to the copy

1. **Package rename.** `revit_mcp/` → `dg_revit_mcp/`. The modules use relative
   imports internally, so only `startup.py`, the tests and the docs change. The
   rename avoids a top-level `revit_mcp` package collision with the
   still-installed `revit-mcp.extension` in the same IronPython runtime.
2. **Routes API name.** `startup.py` registers under the pyRevit Routes API name
   `dg_revit` (upstream: `revit_mcp`), so both extensions can run side by side:
   `/dg_revit/...` is this connector, `/revit_mcp/...` is the old one. The MCP
   server talks to `http://<REVIT_HOST>:<REVIT_PORT>/dg_revit`.
3. **Guards removed.** Every route module and every tool module is registered;
   `degram_readonly.py` is deleted. `dg_transport.py` keeps only the loopback
   helpers, the structured outcome codes and the `DEGRAM_MODE` stdio-only guard.
4. **New `dg_transport.py`** (IronPython 3.4 and CPython safe) replaces
   `degram_readonly.py` as the module imported by both halves.
5. **New DG connector MCP tools** in `tools/dg_connector_tools.py`:
   `dg_mapping_status`, `dg_start_mapping`, `dg_show_elements`,
   `dg_clear_mapping_colours`. They map onto the `dg_revit` routes
   `/mapping_status/`, `/start_mapping/`, `/show_elements/`, `/clear_colours/`.
   The routes themselves (`dg_revit_mcp/dg_connector_routes.py`) are added by a
   later task; `startup.py` registers them when the module exists and keeps
   working when it does not.
6. **Compatibility fixes needed to register everything:** `code_execution.py`
   imports `StringIO` from `io` when the Python 2 module is gone (IronPython
   3.4); `tools/view_tools.py` annotates the image tool's return type as `Any`
   so FastMCP does not try to build a Pydantic schema for `Image`; the
   `/status/` payload reports `api_name: dg_revit`.
7. **Tests.** `tests/test_degram_readonly.py` became `tests/test_dg_transport.py`
   (no allowlists left; it asserts that every declared route and tool is
   registered, writes included). The fake pyRevit runtime moved to
   `tests/pyrevit_stubs.py`. `tests/tool_contract.json` was regenerated from the
   new tool list. `tests/test_degram_documents.py` and `tests/test_offline.py`
   follow the new package and API names.

## Still to come (later tasks of plan 1303-11)

- `lib/dg_connector/` — the pure connector library that runs inside Revit:
  descriptors, document key and session label, palette, DG sign-in and session
  client, apply loop, state store;
- `DG.tab/` — the DG ribbon panel («Вход», «Меппинг DG», «Очистить цвета»,
  «Выход»);
- `dg_revit_mcp/dg_connector_routes.py`, `lib/dg_connector/revit_io.py`,
  `lib/dg_connector/runner.py`, `DG_SharedParameters.txt`;
- `install.py` — installer for `%APPDATA%\pyRevit\Extensions\dg-revit-connector.extension`
  with a backup of a previous copy.
