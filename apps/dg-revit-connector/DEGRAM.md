# DeGram read-only mode of this fork

This fork of `Demolinator/revit-mcp-server` is the Revit adapter of the DeGram agent
(Design Grammar System, phase 1301). It is **read-only, loopback-only and
identity-addressed**. Upstream's write, execute and export surface is not
present at all: those routes and tools are never registered, so they do not
exist on the wire and cannot be reached by prompt, by another local process
or by an old client.

No write route is added before phase 1306. Nothing here is a feature flag: the
restrictions are unconditional in code; only the stdio-only rule is keyed to
`DEGRAM_MODE=1`.

## Two layers, one allowlist module

`degram_readonly.py` is imported by both halves, so the allowlists cannot drift:

| Layer | Where | Enforcement |
|---|---|---|
| pyRevit extension (IronPython, inside Revit) | `startup.py` | `ReadOnlyApi` registers only `ALLOWED_ROUTES`; nothing at all unless the Routes host is loopback |
| MCP server (CPython, stdio child of DeGram) | `main.py`, `tools/__init__.py` | `ReadOnlyToolRegistry` registers only `ALLOWED_TOOLS`; only modules hosting an allowed tool are imported |

Mixed upstream modules (`views`, `placement`, `parameters`, `colors`) are still
imported by the extension, but the proxy drops every route they declare that is
not allowlisted (`set_parameter`, `color_splash`, `place_*`, `get_view`, ...).
`ReadOnlyApi` exposes only `route`; any other attribute raises.

### Allowed tools (`ALLOWED_TOOLS`, 8)

`get_revit_status`, `get_revit_model_info`, `list_open_documents`,
`get_selection_snapshot`, `get_element_properties`, `list_levels`,
`get_current_view_info`, `list_category_parameters`.

### Allowed routes (`ALLOWED_ROUTES`, 8)

| Method | Route | Backs |
|---|---|---|
| GET | `/status/` | `get_revit_status` |
| GET | `/model_info/` | `get_revit_model_info` |
| GET | `/list_open_documents/` | `list_open_documents` |
| POST | `/selection_snapshot/` | `get_selection_snapshot` |
| GET | `/element_properties/<element_id>` | `get_element_properties` |
| GET | `/list_levels/` | `list_levels` |
| GET | `/current_view_info/` | `get_current_view_info` |
| POST | `/list_category_parameters/` | `list_category_parameters` |

The two POST routes only carry a request body; neither opens a transaction.
Every handler declares `doc`, `uidoc` or `uiapp`, which is what makes pyRevit run
it on the Revit API thread through ExternalEvent (`status` and `model_info` were
changed for this; they used `revit.doc` off the API context).

### Drift tests

`tests/test_degram_readonly.py` asserts exact equality between the allowlists,
the routes registered through a stubbed `pyrevit.routes.API`, the tools listed by
FastMCP and the keys of `tests/tool_contract.json`; it also checks that every
upstream tool module, registered through the wrapper, yields only allowlisted
names, and that no tool name has a mutating verb. If you add a tool on purpose,
add it to `ALLOWED_TOOLS`, `ALLOWED_ROUTES` (and the route module list), then
regenerate the contract:

```
uv run python -c "import asyncio, json, main; json.dump({t.name: t.inputSchema for t in asyncio.run(main.mcp.list_tools())}, open('tests/tool_contract.json', 'w'), indent=1, sort_keys=True)"
```

## Transport (D-11)

With `DEGRAM_MODE=1` only stdio is accepted. `--http`, `--sse`, `--combined`
exit with status 2 and `DEGRAM_TRANSPORT_REFUSED` on stderr; no MCP network port
is opened. DeGram launches the server with its bundled Python and
`DEGRAM_MODE=1`.

## Identity contract (D-13, D-14)

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

Residual, by design of pyRevit: the other read tools (`get_element_properties`,
`list_levels`, `get_current_view_info`, `list_category_parameters`,
`get_revit_model_info`) read the *active* document and take no identity. The
DeGram client (plan 11) pins the identity first and treats an
`IDENTITY_MISMATCH` from `get_selection_snapshot` as the signal that the user
switched documents.

## Structured outcomes

Failures are objects, never free-text `Error:` strings. The tool layer returns
them as JSON text: `{"status": "error", "code": "...", "error": "...", ...}`.

| Code | Meaning |
|---|---|
| `BUSY` | Revit did not answer within the deadline (30 s; status uses 10 s), refused the ExternalEvent (HTTP 406/408), or another read held the lock for 30 s |
| `BRIDGE_OFF` | connection to `127.0.0.1:48884` refused |
| `ROUTES_DISABLED` | connection refused and `pyRevit_config.ini` has `[routes] enabled = false`, or a route answered with this code |
| `EXTENSION_NOT_LOADED` | HTTP 404 on `/revit_mcp/...` without a handler error body: the extension is missing, a different version, or deliberately registered nothing |
| `SETUP_INCOMPLETE` | with `reason`: `ROUTES_NOT_LOOPBACK`, `REVIT_HOST_NOT_LOOPBACK`, or `NO_DOCUMENT_OPEN` |
| `IDENTITY_MISMATCH`, `DOCUMENT_NOT_OPEN` | see the identity table |
| `BAD_REQUEST` | invalid request body |
| `ROUTE_ERROR` | any other route or transport failure (carries `httpStatus` when there is one) |

Calls are serialized by one asyncio lock. There is **no automatic retry**.
`get_revit_status`, a read, is the only call with a 10 s deadline.

## Loopback rule (D-23)

pyRevit Routes can listen on all interfaces with no authentication. Two checks:

1. **Extension side.** `startup.py` reads `user_config.routes_host` and
   registers **no routes** unless it is `127.0.0.1`, `localhost`, `::1` or another
   `127.x.x.x` address. An unreadable or unset host is treated as not loopback.
2. **MCP side, fail closed.** At startup and before every read the server
   refuses with `SETUP_INCOMPLETE` / `ROUTES_NOT_LOOPBACK` if `REVIT_HOST` is not
   loopback, if the pyRevit config host is not loopback, or if a 300 ms TCP
   connect to any of this machine's non-loopback addresses (from
   `getaddrinfo` and `gethostbyname_ex` on the host name) succeeds on port 48884.
   No read request is sent in that case. The startup probe reports on stderr only
   (stdout is the MCP channel).

Residual risk, accepted (T-1301-07-06): any process of the same user can still
call the read routes on loopback. They return model data that user can already
open in Revit, and nothing mutates.

## Install (clean machine)

pyRevit is pinned to **6.5.3** (the version present on the development PC;
behavior of the extension against a live Revit session is **not** verified by
this repository's offline tests; a live check belongs to the UAT plan).

1. Install pyRevit 6.5.3.
2. Copy this repository's extension (`startup.py`, `degram_readonly.py`,
   `revit_mcp/`, `extension.json`) into a pyRevit extension folder, as for
   upstream.
3. In `%APPDATA%\pyRevit\pyRevit_config.ini` set under `[routes]`:
   `enabled = true`, `host = "127.0.0.1"`, `port = 48884`.
4. Restart Revit. The extension logs how many routes it registered; with a
   non-loopback host it logs an error and registers none.

Upstream README, `LLM.txt` and `SECURITY.md` still describe the unrestricted
upstream server (48 tools, `execute_revit_code`); they do not apply to this fork.
