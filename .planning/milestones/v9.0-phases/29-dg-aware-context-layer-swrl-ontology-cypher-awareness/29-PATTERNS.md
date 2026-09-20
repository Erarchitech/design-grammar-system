# Phase 29: DG-Aware Context Layer - Pattern Map

**Mapped:** 2026-07-12
**Files analyzed:** 6 (3 new Python, 1 new JSON catalog, 2 modified n8n workflows; `app.py` counted as modified target, not separately new)
**Analogs found:** 6 / 6

## File Classification

| New/Modified File | Role | Data Flow | Closest Analog | Match Quality |
|---|---|---|---|---|
| `data-service/dg_context.py` | service/module (registry + assembler + validator) | request-response (assembly) + transform (Cypher validation) | `data-service/reasoner.py` (registry+settings) and `data-service/connectors.py` (Pydantic models + lifecycle functions) | exact (layout) |
| `llm/cypher_catalog.json` (or `data-service/llm/cypher_catalog.json` — resolve path per Open Question 2) | config (versioned data artifact) | file-I/O (read-only) | `data-service/data/reasoner-settings.json`-style JSON store pattern (structurally: `{version, shapes:[...]}` vs. flat dict) — no exact JSON-catalog analog exists; closest is the *load* half of `reasoner.load_settings()` | role-match |
| `data-service/tests/test_dg_context.py` | test | request-response (TestClient) + unit (pure functions) | `data-service/tests/test_reasoner.py` | exact |
| `data-service/app.py` (add routes: `/context/assemble`, `/context/debug`, and the single n8n-facing generate+validate+retry endpoint) | controller (FastAPI route registration) | request-response | `app.py`'s own `/reasoner/settings`, `/reasoner/consistency`, `/connectors` blocks (lines 1160-1189, 1196-1242, 1086-1153) | exact |
| `n8n/workflows/rules-to-metagraph.json` ("Build LLM Prompt", "Fetch Existing Entities", "Parse LLM Output" nodes) | route/middleware (workflow orchestration, becomes thin HTTP caller) | request-response | itself (pre-Phase-29 version) — being slimmed, not replaced by a different codebase pattern | exact (self) |
| `n8n/workflows/graph-query-mcp.json` ("Build Cypher Prompt", "Smart Overrides" nodes) | route/middleware | request-response | itself (pre-Phase-29 version), plus `rules-to-metagraph.json`'s sibling nodes for the shared thin-caller shape | exact (self) |

## Pattern Assignments

### `data-service/dg_context.py` (service module, request-response + transform)

**Analogs:** `data-service/reasoner.py` (registry/settings persistence shape) + `data-service/connectors.py` (Pydantic request/response models + lifecycle functions) + `data-service/app.py:996-1027` (`llm_generate`, in-process adapter-call shape for the retry loop)

**Module header / docstring pattern** (`reasoner.py` lines 1-16):
```python
"""Reasoner registry and settings persistence — HermiT/Pellet placeholder selection.

Mirrors the connectors.py / llm_gateway settings-persistence style: JSON file
under DATA_DIR, small load/save helpers, module-level file path constant.
...
"""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any
```
Apply the same self-documenting header to `dg_context.py`, stating explicitly it mirrors `reasoner.py`/`connectors.py`'s module layout and that the SWRL/Computgraph blocks are read-only Python data (per CONTEXT.md Discretion note), while `llm/cypher_catalog.json` is the one externally-versioned artifact.

**Registry-as-module-constant pattern** (`reasoner.py` lines 18-35):
```python
REASONER_REGISTRY: list[dict[str, str]] = [
    {"id": "hermit", "name": "HermiT", "description": "...", "status": "integrated"},
    {"id": "pellet", "name": "Pellet", "description": "...", "status": "placeholder"},
]
REASONER_IDS: set[str] = {r["id"] for r in REASONER_REGISTRY}
```
Use this exact shape for the SWRL convention block and the parsed Computgraph catalog: a module-level `list[dict]` or `dict` constant, built once, plus a derived `set`/index for O(1) lookups (e.g. `CYPHER_SHAPE_IDS`, mirroring `CONNECTOR_IDS`/`REASONER_IDS`).

**JSON load-with-defensive-fallback pattern** (`reasoner.py` lines 44-57, structurally identical to `connectors.py` lines 88-104):
```python
def load_settings() -> dict[str, Any]:
    if not REASONER_SETTINGS_FILE.exists():
        return {}
    try:
        payload = json.loads(REASONER_SETTINGS_FILE.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    if not isinstance(payload, dict):
        return {}
    return payload
```
Copy this exact defensive shape for `load_cypher_catalog()` (returns `{"version": 0, "shapes": []}` on missing/malformed file rather than raising) — matches CTXA-02's "loads and exposes all 6 shapes" requirement needing a stable, never-raising load path so `/context/debug` never 500s on a catalog file issue.

**Pydantic model pattern** (`connectors.py` lines 62-79):
```python
class CredentialCreatePayload(BaseModel):
    """Request body for POST /connectors/{connector_id}/credentials."""
    label: str | None = None

class CredentialCreatedResponse(BaseModel):
    """Response for credential creation — the ONLY time the token is visible."""
    credential_id: str
    token: str
```
Use this style (short docstring naming the exact endpoint it serves) for `ContextAssembleRequest` (`type: Literal["rule_ingest","rule_edit","graph_query"]`, `project: str`, `rules_text: str | None`, `question: str | None`) and its response model — field names/optionality driven by CONTEXT.md's three request types.

**In-process adapter-call / retry-loop pattern** (`app.py` lines 996-1027, `llm_generate`):
```python
master_secret = os.getenv("LLM_MASTER_SECRET", "")
settings = load_persisted_llm_settings()
provider, model, api_key = resolve_active_provider(settings, master_secret)
if req.provider is not None:
    provider = req.provider
if req.model is not None:
    model = req.model
req_with_model = GenerateRequest(prompt=req.prompt, system=req.system, model=model, provider=provider)
try:
    adapter = get_adapter(provider, settings.get("baseUrl"))
    response = adapter.generate(req_with_model, api_key)
    return response
except Exception as exc:
    error_msg, hint, code = map_provider_error(exc)
    raise _structured_error_response(error_msg, hint, code, 502)
```
`dg_context.py`'s retry orchestration function (RESEARCH.md's `generate_validated_cypher`) should replicate this exact `resolve_active_provider → get_adapter → adapter.generate` sequence as direct Python calls (import from `llm_gateway`), wrapped in a `for attempt in range(max_retries + 1)` loop, calling the local `validate_cypher()` after each `adapter.generate()` and appending structured violations to the prompt on failure — no second HTTP hop to `/llm/generate`.

**Lifecycle-function-with-ValueError pattern** (`connectors.py` lines 132-158, `create_credential`):
```python
def create_credential(connector_id: str, label: str | None = None) -> tuple[dict[str, Any], str]:
    if connector_id not in CONNECTOR_IDS:
        raise ValueError(f"Unknown connector: {connector_id}")
    ...
```
Use this "validate against a module-level ID set, raise `ValueError` on unknown, let the FastAPI route translate to `_structured_error_response`" pattern for `assemble_context()`'s `type` dispatch and any unknown-shape-id lookups inside the validator.

---

### `llm/cypher_catalog.json` (config, file-I/O)

**No exact JSON-catalog analog** — existing JSON stores (`reasoner-settings.json`, `connector-credentials.json`) are flat runtime state dicts, not versioned static content catalogs. Model the catalog itself directly on CONTEXT.md's locked shape:
```json
{
  "version": 1,
  "shapes": [
    {
      "id": "max_limit",
      "name": "Maximum Limit",
      "description": "...",
      "swrl_pattern": "...",
      "cypher_template": "...",
      "worked_example": "..."
    }
  ]
}
```
Load it with the `reasoner.py`-style defensive `load_*()` helper (see above). Path resolution: RESEARCH.md Open Question 2 flags that `data-service/Dockerfile`'s build context is `./data-service` per `docker-compose.yml:33` — verify whether the file must live at `data-service/llm/cypher_catalog.json` (safe, in-context) vs. repo-root `llm/` (needs a Dockerfile COPY/volume-mount change) before finalizing the load path constant.

---

### `data-service/tests/test_dg_context.py` (test)

**Analog:** `data-service/tests/test_reasoner.py` (full file — 222 lines)

**Boilerplate header** (lines 1-26):
```python
from __future__ import annotations

import json
import os
import sys

import httpx
import pytest
from fastapi.testclient import TestClient

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

os.environ.setdefault("LLM_MASTER_SECRET", "test-master-secret")

import app as app_module  # noqa: E402
import reasoner  # noqa: E402
from app import app  # noqa: E402

client = TestClient(app, raise_server_exceptions=False)
```
Copy verbatim, swapping `import reasoner` for `import dg_context`.

**Isolated-store fixture pattern** (lines 31-34):
```python
@pytest.fixture(autouse=True)
def isolated_store(tmp_path, monkeypatch):
    """Redirect reasoner settings persistence to a per-test temp file."""
    monkeypatch.setattr(reasoner, "REASONER_SETTINGS_FILE", tmp_path / "reasoner-settings.json")
```
Use for `dg_context.py`'s `CYPHER_CATALOG_FILE` constant if the catalog load path needs test isolation (likely — RESEARCH.md Wave-0-gap notes "the artifact itself must exist before any test can load it").

**Class-per-concern test grouping** (`TestRegistry`, `TestSelectReasoner`, `TestUnknownReasoner`, `TestReasonerConsistencyProxy`) — mirror with `TestContextAssemble`, `TestCypherCatalog`, `TestSwrlConventions`, `TestValidator`, `TestRetryLoop`, `TestDeterminism` per RESEARCH.md's Phase Requirements → Test Map (these six class names are already specified there — use them verbatim).

**Adapter-mocking pattern for the retry loop** (`TestReasonerConsistencyProxy`, lines 138-165, `monkeypatch.setattr(app_module.httpx, "post", fake_post)` targeting a module-level callable): apply the same `monkeypatch.setattr` technique but target `llm_gateway.get_adapter` (or the returned adapter's `.generate` method) instead of `httpx.post`, per RESEARCH.md's explicit guidance in the Wave 0 Gaps section.

---

### `data-service/app.py` (add `/context/assemble`, `/context/debug`, and the n8n-facing generate+validate endpoint)

**Analog:** `app.py`'s own `/reasoner/settings` GET/PUT pair (lines 1160-1189) for the simple assemble/debug shape, and `/reasoner/consistency` (lines 1196-1242, not fully shown here but referenced via `_structured_error_response` pattern) for the proxy-with-structured-errors shape.

**Simple GET/PUT registry-backed endpoint pair** (lines 1164-1189):
```python
@app.get("/reasoner/settings")
def get_reasoner_settings():
    """Return the reasoner registry and currently selected reasoner id."""
    settings = reasoner.load_settings()
    return {
        "reasoners": reasoner.REASONER_REGISTRY,
        "selected": settings.get("selected", None),
    }

@app.put("/reasoner/settings")
def put_reasoner_settings(payload: ReasonerSettingsPayload):
    """Persist the selected reasoner id. Rejects unknown ids with 422."""
    if payload.reasoner not in reasoner.REASONER_IDS:
        raise _structured_error_response(
            f"Unknown reasoner: {payload.reasoner}",
            f"Valid reasoner ids: {', '.join(sorted(reasoner.REASONER_IDS))}",
            "REASONER_NOT_FOUND",
            422,
        )
    reasoner.save_settings({"selected": payload.reasoner})
    return {"reasoners": reasoner.REASONER_REGISTRY, "selected": payload.reasoner}
```
Model `GET /context/debug` and `POST /context/assemble` directly on this: thin route body, all real logic delegated to `dg_context.assemble_context(...)`, `_structured_error_response` for unknown `type` values (`code="CONTEXT_TYPE_INVALID"` or similar, following the `REASONER_NOT_FOUND` naming convention).

**Section-comment convention** (lines 1155-1158, 1082-1084):
```python
# ---------------------------------------------------------------------------
# Reasoner settings endpoints (Phase 814: REAS-01..03)
# ---------------------------------------------------------------------------
```
Add an identical banner comment above the new routes: `# Context assembler endpoints (Phase 29: CTXA-01..05)`.

**Structured error helper** (`app.py:575-580`, reused not redefined):
```python
def _structured_error_response(error: str, hint: str, code: str, status_code: int = 500) -> HTTPException:
    return HTTPException(status_code=status_code, detail={"error": error, "hint": hint, "code": code})
```
Reuse directly (import already available at module scope in `app.py`) — do not redefine in `dg_context.py`; if `dg_context.py` needs to raise structured errors independent of FastAPI (e.g. from a pure function called by tests), return a plain `{code, message, path}` dict instead (per CONTEXT.md's validator violation shape) and let the `app.py` route wrap it.

**Import block addition** (mirrors `app.py:33-40`'s `from llm_gateway import (...)` and the existing `import reasoner` / `import connectors` module-level imports elsewhere in `app.py`): add `import dg_context` near the other sibling-module imports (`reasoner`, `connectors`) rather than `from dg_context import *`.

---

### `n8n/workflows/rules-to-metagraph.json` and `n8n/workflows/graph-query-mcp.json` (thin-caller reduction)

**Analog:** themselves, pre-Phase-29 — no cross-file pattern needed; RESEARCH.md's "Don't Hand-Roll" section already identifies the exact node-level logic to port out (bracket-nesting `hasValidNesting()`, label/rel/prop allow-list regexes, the "Fetch Existing Entities" Cypher query, "Smart Overrides" keyword matching) into `dg_context.py`. The remaining n8n node body becomes an HTTP Request node calling `POST /context/assemble` then string-joining the response into the final LLM prompt — follow whatever existing HTTP Request node in either workflow already calls `data-service` (e.g. the node calling `/llm/generate`) for header/auth/URL conventions.

**Pre-condition per RESEARCH.md Pitfall 2:** export the LIVE n8n workflow JSON before editing either file — the repo JSONs are confirmed to have drifted behind the live n8n instance (STATE.md Pending Todos, `versionCounter 22`). The plan should include a reconciliation task before touching these nodes.

## Shared Patterns

### Structured error / violation vocabulary
**Source:** `data-service/app.py:575-580` (`_structured_error_response`), reused convention from `REASONER_NOT_FOUND`/`CONNECTOR_NOT_FOUND`/`CONNECTOR_AUTH_FAILED` codes
**Apply to:** `/context/assemble`, `/context/debug`, and the new generate+validate endpoint — plus the validator's own `{valid, violations:[{code, message, path?}]}` shape (CONTEXT.md-locked), which is a peer/plural form of the same `{error, hint, code}` triple discipline.

### Module layout: registry constant → Pydantic models → load/save helpers → domain functions
**Source:** `data-service/reasoner.py` (full file) and `data-service/connectors.py` (full file)
**Apply to:** `dg_context.py` in its entirety — this is the single most load-bearing pattern for the new module; deviate only where CONTEXT.md explicitly forces a different shape (e.g. `llm/cypher_catalog.json` staying a standalone file rather than becoming Python literals).

### In-process adapter reuse (no internal HTTP round-trip)
**Source:** `data-service/app.py:996-1027` (`llm_generate`)
**Apply to:** the retry loop inside `dg_context.py` — call `resolve_active_provider()` + `get_adapter()` + `adapter.generate()` directly, imported from `llm_gateway`, never re-POST to `/llm/generate`.

### pytest TestClient + `sys.path.insert` + `isolated_store` fixture
**Source:** `data-service/tests/test_reasoner.py` (full file)
**Apply to:** `data-service/tests/test_dg_context.py` — copy the boilerplate header and fixture pattern verbatim; use `monkeypatch.setattr` for both file-path isolation and adapter-mocking (per `TestReasonerConsistencyProxy`'s `httpx.post` mock, retargeted to the LLM adapter).

## No Analog Found

| File | Role | Data Flow | Reason |
|------|------|-----------|--------|
| `llm/cypher_catalog.json` | config | file-I/O | No prior versioned static-content JSON catalog exists in the codebase (existing JSON stores are runtime state, not content catalogs) — structure comes directly from CONTEXT.md's locked `{version, shapes:[...]}` schema, not from a codebase analog. Load-helper *mechanics* still borrow from `reasoner.py`. |
| Computgraph/SWRL Python data blocks (submodule of `dg_context.py`) | config (in-memory) | transform (OWL parse → dict) | No existing OWL-parsing code confirmed in the repo at pattern-mapping time — RESEARCH.md flags `ontology/export_to_markdown_v7.py` as a possible reusable parser but this needs verification during implementation (RESEARCH.md Assumption A1); no fallback codebase pattern to cite here beyond stdlib `xml.etree.ElementTree` usage generically. |

## Metadata

**Analog search scope:** `data-service/*.py` (app.py, reasoner.py, connectors.py, llm_gateway.py), `data-service/tests/test_reasoner.py`, `n8n/workflows/*.json` (via RESEARCH.md's prior full reads), `cypher_template.txt`
**Files scanned:** app.py (full route index + 2 targeted reads), reasoner.py (full), connectors.py (full), test_reasoner.py (full)
**Pattern extraction date:** 2026-07-12
**Note on graphify:** `graphify query`/`graphify explain` were attempted first per repo convention; the indexed graph (`graphify-out/graph.json`) has no coverage of `data-service/*.py` (only DG_OBSIDIAN notes and JS/C# App() components resolved), so this mapping proceeded via direct Read/Grep against the files RESEARCH.md had already identified with exact line numbers.
