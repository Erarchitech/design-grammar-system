---
tags: [debugging, DeGram, v13.0, phase-1301, revit, pyrevit, ironpython]
date: 2026-10-09
status: fixed in the apps/revit-mcp working tree (not committed); live-verified through a copied extension
---

# DeGram Revit adapter could not load under pyRevit IronPython 3.4

## Symptom

On PC1 the Revit segment stayed «настройка» (setup-incomplete) with Revit 2024 open, Routes on and listening on 127.0.0.1:48884; `GET /revit_mcp/status/` answered `RouteHandlerNotDefinedException`.

## Cause — five layers, found one after another

pyRevit 6.5.3 on PC1 runs extension scripts on **IronPython 3.4** (`Building on IronPython engine: 342`). The fork inherited code written for IronPython 2.7, and the offline tests ran it on CPython with `revit_mcp/` on `sys.path`, which hid all of it.

1. **G-8** `extension.json` kept upstream `"builtin": "True", "default_enabled": "False"` → pyRevit writes `[revit-mcp.extension] disabled = true` on first discovery and never runs `startup.py`.
2. **G-9** `degram_readonly.py` (imported by `startup.py`) held `structured_helper` with `async def`/`await` → import fails (`Startup script returned non-zero result … 2`).
3. **G-10** 21 route modules used `from utils import …` (implicit relative import, 2.7 only) → `No module named 'utils'`.
4. **G-11** `revit_mcp/views.py` `from urllib import unquote` → registration aborted after the third module.
5. **G-12** pyRevit Routes itself parses `application/json` bodies with `json.loads(bytes)`, which IronPython 3.4 rejects before the route runs → every POST read (selection snapshot) failed. The owner's GenproMM fork already used the workaround.

## Fix

- `extension.json`: builtin False, default_enabled True.
- `structured_helper` moved to `tools/__init__.py` (CPython MCP side).
- `from .utils import` in all route modules; `urllib.parse` with a 2.7 fallback.
- Client `json_body()` sends `text/plain; charset=utf-8`; `revit_mcp/utils.parse_request_data` accepts bytes/str/dict.
- New tests: AST scan of IronPython-side modules for 3.5+ syntax, explicit sibling imports, bytes body, client content type. Suite 163 passed.
- Live: `Registered 8 read routes; dropped 10 non-allowlisted route declarations`; write routes absent; selection snapshot returns the selected elements.

## Lesson

A module that runs inside pyRevit must be tested against the engine pyRevit actually uses. Static AST checks for the engine's grammar are cheap; a CPython import test with a patched `sys.path` proves nothing about the Revit side.

## Related

- [[sessions/2026-10-09 Phase 1301 live UAT on PC1 and the 0.1.6 gap list]]
- `.planning/phases/1301-rabochiy-klient-i-bezopasnoe-chtenie/1301-UAT.md` (G-8..G-12)
