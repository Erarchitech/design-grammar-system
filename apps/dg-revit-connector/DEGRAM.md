# DG Revit connector for DeGram

This fork is the Revit adapter of the DeGram agent (Design Grammar System). It is
**loopback-only and stdio-only**, and since the owner decision of 2026-10-18
(D-45) it is **not read-only**: every upstream route and tool is registered,
writes included. Provenance and the full list of Design Grammars changes are in
[UPSTREAM.md](UPSTREAM.md); install and usage are in [README.md](README.md).

There is no allowlist module any more. `degram_readonly.py` is gone;
`dg_transport.py` keeps only the loopback helpers, the structured outcome codes
and the `DEGRAM_MODE` stdio-only guard, and is imported by both halves.

## Two layers

| Layer | Where | Behaviour |
|---|---|---|
| pyRevit extension (IronPython 3.4, inside Revit) | `startup.py`, `dg_revit_mcp/` | Registers every route module under the Routes API name `dg_revit`; registers nothing at all unless the Routes host is loopback |
| MCP server (CPython, stdio child of DeGram) | `main.py`, `tools/` | Registers every tool module (48 upstream tools, 2 identity-pinned document tools, 4 DG connector tools); talks to `http://<REVIT_HOST>:<REVIT_PORT>/dg_revit` |

## Tool surface

`python -c "import asyncio, main; [print(t.name) for t in asyncio.run(main.mcp.list_tools())]"`
lists the exact set (54 names). The write-capable tools include
`execute_revit_code`, `delete_elements`, `modify_element`, `set_parameter`,
`save_document`, `place_family`, `load_family`, `color_splash`, `clear_colors`,
`transform_elements`, `create_*` (levels, grids, rooms, views, sheets,
schedules, ducts, pipes, walls/line-based and surface-based elements), `link_file`
and `export_*`. DeGram may use all of them; in DeGram the `tools.include` list of
`config_template.yaml` and `lockdown.REVIT_TOOL_NAMES` must name every tool of
this fork, otherwise the agent tool set silently omits some.

### DG connector tools

| Tool | Route | Purpose |
|---|---|---|
| `dg_mapping_status` | `GET /mapping_status/` | Sign-in state, open mapping session, label, element count, progress |
| `dg_start_mapping` | `POST /start_mapping/` | Reads the selection (else the visible model instances of the active view, ≤ 5000), starts a DG mapping session, colours by state |
| `dg_show_elements` | `POST /show_elements/` | Selects the given `unique_ids` (≤ 5000) and zooms the active view to them |
| `dg_clear_mapping_colours` | `POST /clear_colours/` | Removes the mapping graphic overrides from the active view |

`dg_show_elements` refuses an empty list and more than 5000 ids itself, with a
`BAD_REQUEST` outcome, before any HTTP call. The routes are added by a later task
of plan 1303-11; until `dg_revit_mcp/dg_connector_routes.py` exists, `startup.py`
registers every Revit route and these four tools answer `EXTENSION_NOT_LOADED`.

## Transport (1301 D-11)

With `DEGRAM_MODE=1` only stdio is accepted. `--http`, `--sse`, `--combined`
exit with status 2 and `DEGRAM_TRANSPORT_REFUSED` on stderr; no MCP network port
is opened. DeGram launches the server with its bundled Python and
`DEGRAM_MODE=1`.

## Identity contract (1301 D-13, D-14)

pyRevit Routes only knows the *active* document. `list_open_documents` returns
every open non-linked, non-family project document:

```json
{"status": "ok", "documents": [
  {"title": "...", "pathName": "", "creationGuid": "...", "isActive": true, "isModified": false}]}
```

`pathName` is empty for an unsaved project. A client pins `{creationGuid,
pathName}`. `creationGuid` alone is not unique (a Save-As copy shares it), so the
pair is the identity; unsaved twins are told apart by the client (they have
different titles and an empty path, so the picker should disable them).

`get_selection_snapshot(identity, max_elements=200, max_parameters=50)` reads the
selection of the pinned document and of no other:

| Situation | Outcome |
|---|---|
| no document with that `creationGuid` is open | `DOCUMENT_NOT_OPEN` |
| open, but `pathName` differs | `IDENTITY_MISMATCH` (`reason: PATH_DIFFERS`) |
| open, matching, but not the active UI document | `IDENTITY_MISMATCH` (`reason: NOT_ACTIVE_DOCUMENT`) |
| `identity.creationGuid` missing | `BAD_REQUEST` |
| empty selection | ok, `emptySelection: true`, `elements: []` |
| otherwise | ok with `elements` |

Each element has `uniqueId`, `elementId`, `category`, `typeName`, `parameters`
(`name`, `storageType`, `unit`, `displayValue`, `value`) and `parametersTotal`.
`truncation` discloses `elementsTotal`, `elementsKept`, `parametersTruncated`
and the effective `maxElements` / `maxParameters`. Limits are clamped to 1000
elements and 200 parameters; a non-numeric limit falls back to the default.
Instance parameters only; use `get_element_properties` (by `elementId`) for type
parameters. `value` of a Double parameter is the raw Revit internal value (feet
for lengths); `displayValue` is Revit's formatted string and `unit` its unit label.

Residual, by design of pyRevit: the upstream tools that take no identity read the
*active* document. The DeGram client pins the identity first and treats an
`IDENTITY_MISMATCH` from `get_selection_snapshot` as the signal that the user
switched documents.

## Structured outcomes

Failures are objects, never free-text `Error:` strings. The tool layer returns
them as JSON text: `{"status": "error", "code": "...", "error": "...", ...}`.

| Code | Meaning |
|---|---|
| `BUSY` | Revit did not answer within the deadline (30 s; status uses 10 s), refused the ExternalEvent (HTTP 406/408), or another call held the lock for 30 s |
| `BRIDGE_OFF` | connection to `127.0.0.1:48884` refused |
| `ROUTES_DISABLED` | connection refused and `pyRevit_config.ini` has `[routes] enabled = false`, or a route answered with this code |
| `EXTENSION_NOT_LOADED` | HTTP 404 on `/dg_revit/...` without a handler error body: the extension is missing, a different version, or the route is not built yet |
| `SETUP_INCOMPLETE` | with `reason`: `ROUTES_NOT_LOOPBACK`, `REVIT_HOST_NOT_LOOPBACK`, or `NO_DOCUMENT_OPEN` |
| `IDENTITY_MISMATCH`, `DOCUMENT_NOT_OPEN` | see the identity table |
| `BAD_REQUEST` | invalid request body or invalid tool argument |
| `ROUTE_ERROR` | any other route or transport failure (carries `httpStatus` when there is one) |

Calls are serialized by one asyncio lock. There is **no automatic retry**.

## Loopback rule (1301 D-23)

pyRevit Routes can listen on all interfaces with no authentication. Two checks:

1. **Extension side.** `startup.py` reads `user_config.routes_host` and
   registers **no routes** unless it is `127.0.0.1`, `localhost`, `::1` or another
   `127.x.x.x` address. An unreadable or unset host is treated as not loopback.
2. **MCP side, fail closed.** At startup and before every call the server
   refuses with `SETUP_INCOMPLETE` / `ROUTES_NOT_LOOPBACK` if `REVIT_HOST` is not
   loopback, if the pyRevit config host is not loopback, or if a 300 ms TCP
   connect to any of this machine's non-loopback addresses (from
   `getaddrinfo` and `gethostbyname_ex` on the host name) succeeds on port 48884.
   No request is sent in that case. The startup probe reports on stderr only
   (stdout is the MCP channel).

Residual risk, accepted: any process of the same user can still call the routes
on loopback. That now includes write routes, which is exactly what the owner
decision of 2026-10-18 permits; the loopback rule keeps them off the network.

## Drift tests

`tests/test_dg_transport.py` asserts that every route module declared on disk is
registered by `startup.py` under `dg_revit`, that every tool module is registered
by `main.mcp`, that the write tools are present, and that the names and input
schemas match `tests/tool_contract.json`. After adding or changing a tool on
purpose, regenerate the contract:

```
python -c "import asyncio, json, main; json.dump({t.name: t.inputSchema for t in asyncio.run(main.mcp.list_tools())}, open('tests/tool_contract.json', 'w', encoding='utf-8'), indent=2, sort_keys=True, ensure_ascii=False)"
```

Upstream `README.md` (kept below the "Upstream README" heading), `LLM.txt` and
`SECURITY.md` still describe the upstream project under its old names; this file,
[README.md](README.md) and [UPSTREAM.md](UPSTREAM.md) describe this fork.
