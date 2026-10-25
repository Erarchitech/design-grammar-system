# Phase 1205: Security and Tenancy Release Gate - Pattern Map

**Mapped:** 2026-09-28
**Files analyzed:** 15 (new/modified, per CONTEXT.md D-01..D-20 + RESEARCH.md project structure)
**Analogs found:** 15 / 15 (all have a strong same-repo analog; none in "No Analog Found")

## File Classification

| New/Modified File | Role | Data Flow | Closest Analog | Match Quality |
|---|---|---|---|---|
| `data-service/auth.py` (NEW) | service/middleware | CRUD + request-response | `data-service/connectors.py` | exact (same author intent: token mint/hash/persist) |
| `data-service/app.py` (router refactor: `@app.*` → `@router.*`, add `Depends(require_principal)`) | controller | request-response | `data-service/app.py:2513-2560` (`/designstate/capture`) | exact — this route already implements the exact D-03/D-04 idiom being generalized |
| `data-service/connectors.py` (unchanged, reused for `dgc_` verification) | service | CRUD | — (itself) | n/a, reused as-is |
| `data-service/tests/conftest.py` (add `authorized_client` fixture) | test | request-response | current `conftest.py` (CLI options/markers only, no client fixture) + any of the 8 module-level `TestClient` test files | role-match (extends existing conftest pattern; no fixture precedent, so structure from `httpx.Client(headers=...)` idiom in `tools/de01/legs.py`) |
| `data-service/tests/test_route_inventory.py` (NEW) | test | batch/static-analysis | `tools/de01/tests/test_reproducibility_scope_drift.py` (fenced-block parser + AST/route cross-check) | exact |
| `data-service/tests/test_cross_project_matrix.py` (NEW) | test | request-response, batch | `data-service/tests/test_designstate_capture.py` (per RESEARCH.md; project-mismatch 403 test) | role-match |
| `data-service/tests/test_static_proxy_boundary.py` (NEW) | test | file-I/O (static parse) | none existing that parses `nginx.conf`/`docker-compose.yml` — nearest is `test_reproducibility_scope_drift.py`'s "parse a text file, assert a shape" idiom | partial (parsing pattern transfers, target file differs) |
| `spec/SECURITY-BOUNDARY.md` (NEW) | config/spec | file-I/O | `spec/REPRODUCIBILITY.md`, `spec/SWRL-SUBSET.md` | exact |
| `ui-v2/src/lib/auth.js` (REWRITTEN — thin client of `/auth/login`,`/auth/logout`) | provider/hook | request-response | `ui-v2/src/lib/connectorsApi.js` (named data-service endpoint client) | exact |
| `ui-v2/src/lib/graphApi.js` (executeCypher + Neo4j DEFAULTS deleted; 7 named endpoints added) | service/hook | CRUD (was ad hoc Cypher, becomes REST) | `ui-v2/src/lib/connectorsApi.js` (`base()`/`getJson()`/named calls) | exact |
| `ui-v2/src/lib/modelApi.js` (2 call sites converted to named endpoints) | service/hook | CRUD | `ui-v2/src/lib/connectorsApi.js` | exact |
| `ui-v2/src/lib/inputGenApi.js` (1 call site converted) | service/hook | CRUD | `ui-v2/src/lib/connectorsApi.js` | exact |
| `DG/src/DG.Grasshopper/Validation/ValidationPublishClient.cs` (add `Authorization: Bearer dgc_...`) | service (HTTP client) | request-response | `DG/src/DG.Core/Data/ConnectorHeartbeatClient.cs` (Bearer header pattern) | exact |
| `DG/src/DG.Grasshopper/Validation/ComputgraphPublishClient.cs` (add Bearer header) | service (HTTP client) | request-response | `DG/src/DG.Core/Data/ConnectorHeartbeatClient.cs` | exact |
| `DG/src/DG.Grasshopper/*ConnectorComponent.cs` (token input port, unchanged shape, reused) | component (GH) | event-driven | itself — no change needed, already has the token port per Correction 5 | n/a |
| `docker-compose.yml` (`${VAR:?}` required secrets, ports → 127.0.0.1) + `docker-compose.multi-user.yml` (NEW override) | config | batch/config | `docker-compose.yml` itself (existing service blocks) — no in-repo override-file precedent, pattern taken from Docker Compose reference (RESEARCH.md "Deployment Profile Mechanics") | partial — no existing override file in repo to copy from |
| `.env.example` (NEW) | config | file-I/O | none in repo today (verified absent) — modeled directly on the `docker-compose.yml` secret inventory (Correction 6) | no close in-repo analog, but trivial (flat KEY=placeholder list) |

## Pattern Assignments

### `data-service/auth.py` (service/middleware, CRUD + request-response)

**Analog:** `data-service/connectors.py` (full file read, lines 1-270)

**Imports pattern** (connectors.py lines 12-23):
```python
from __future__ import annotations

import hashlib
import json
import os
import secrets
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

from pydantic import BaseModel
```
Use identically in `auth.py` — same stdlib-only toolkit covers scrypt (`hashlib.scrypt`), session token minting (`secrets.token_urlsafe`), and JSON persistence.

**Persistence pattern** (connectors.py lines 104-135):
```python
DATA_DIR = Path(os.getenv("DG_DATA_DIR", "/app/data"))
CREDENTIALS_FILE = DATA_DIR / "connector-credentials.json"

def load_credentials() -> list[dict[str, Any]]:
    if not CREDENTIALS_FILE.exists():
        return []
    try:
        payload = json.loads(CREDENTIALS_FILE.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return []
    if not isinstance(payload, dict):
        return []
    credentials = payload.get("credentials")
    if not isinstance(credentials, list):
        return []
    return [c for c in credentials if isinstance(c, dict)]

def save_credentials(credentials: list[dict[str, Any]]) -> None:
    CREDENTIALS_FILE.parent.mkdir(parents=True, exist_ok=True)
    CREDENTIALS_FILE.write_text(
        json.dumps({"credentials": credentials}, indent=2),
        encoding="utf-8",
    )
```
Copy this shape three times (or once, generalized) for `users.json`, `sessions.json`, `memberships.json` under the same `DATA_DIR`. Same fail-soft-to-empty-list read behavior, same `mkdir(parents=True, exist_ok=True)` write behavior.

**Token/hash-at-rest pattern** (connectors.py lines 138-148, 212-223):
```python
TOKEN_PREFIX = "dgc_"

def generate_token() -> str:
    return TOKEN_PREFIX + secrets.token_urlsafe(32)

def hash_token(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()

def authenticate_token(token: str) -> dict[str, Any] | None:
    if not token:
        return None
    digest = hash_token(token)
    for record in load_credentials():
        if record.get("token_hash") == digest and not record.get("revoked"):
            return record
    return None
```
D-01's session token follows this exactly: `secrets.token_urlsafe(32)` (no prefix needed, or use `dgs_` to mirror `dgc_`), hash-at-rest with SHA-256 (session tokens, unlike passwords, don't need scrypt — they're already high-entropy random, matching `connectors.py`'s own reasoning in its module docstring: "hashing beats encryption here because we never need the plaintext back"). Passwords (D-01) need `hashlib.scrypt` + per-user `os.urandom` salt instead — new code, no in-repo analog, but stdlib-only per RESEARCH.md.

**Revocation pattern** (connectors.py lines 193-209):
```python
def revoke_credential(connector_id: str, credential_id: str) -> bool:
    credentials = load_credentials()
    changed = False
    for record in credentials:
        if (record.get("connector_id") == connector_id
                and record.get("credential_id") == credential_id):
            record["revoked"] = True
            changed = True
    if changed:
        save_credentials(credentials)
    return changed
```
`/auth/logout` (D-01) should mirror this: mark the session record revoked/deleted, not just tell the browser to drop the cookie.

---

### `data-service/app.py` — router refactor + `require_principal` dependency (controller, request-response)

**Analog:** `data-service/app.py:2513-2560` (`/designstate/capture`) — this is the ONE existing route that already does what D-03/D-04 must generalize.

**Auth + bound-project check pattern** (app.py lines 2513-2558, verbatim):
```python
@app.post("/designstate/capture", status_code=202)
def capture_design_state(request: Request, payload: DesignStateCaptureRequest):
    auth_header = request.headers.get("Authorization", "")
    token = auth_header[len("Bearer "):].strip() if auth_header.startswith("Bearer ") else ""
    record = connectors.authenticate_token(token) if token.startswith(connectors.TOKEN_PREFIX) else None
    if record is None:
        raise _structured_error_response(
            "Invalid or revoked connector token.",
            "Create a new credential via POST /connectors/{connector_id}/credentials.",
            "CONNECTOR_AUTH_FAILED",
            401,
        )
    # T-39-02. The message is deliberately generic (T-39-06): it names neither
    # the credential's bound project nor the requested one, so this endpoint
    # cannot be used to probe which projects exist or which project a stolen
    # token belongs to.
    if (record.get("project") or "default-project") != payload.project:
        raise _structured_error_response(
            "This connector token is not authorized for the requested project.",
            "Create a credential scoped to the project you are capturing into, via "
            "POST /connectors/{connector_id}/credentials.",
            "CAPTURE_PROJECT_MISMATCH",
            403,
        )
```
Key details to preserve when generalizing into `require_principal`:
- Uses `connectors.authenticate_token`, NOT `record_heartbeat` (heartbeat stamps liveness; a plain auth check must not).
- 401 for invalid/unknown token vs 403 for wrong-project — same two-step order every new dependency should follow (auth first, then authorization).
- Error message is deliberately generic — never names which project exists or which project a token is bound to (anti-enumeration, T-39-06). Apply this house style to every new 401/403 in `require_principal` and the new named endpoints.
- **Do not double-wrap this specific route** — RESEARCH.md Route #37 note: `/designstate/capture` already does its own authorization; the new global dependency must recognize it (e.g., put it on the D-17 allowlist as "connector-token, self-checked" or let the dependency subsume it and delete the inline check — planner's call, but not both).

**Error shape helper** (app.py lines 710-715, verbatim):
```python
def _structured_error_response(error: str, hint: str, code: str, status_code: int = 500) -> HTTPException:
    """Return an HTTPException with a structured JSON detail body (error, hint, code)."""
    return HTTPException(
        status_code=status_code,
        detail={"error": error, "hint": hint, "code": code},
    )
```
Every new 401 (`AUTH_REQUIRED`), 403 (`PROJECT_FORBIDDEN`), and body/path mismatch (`PROJECT_MISMATCH`) response should be raised through this exact helper — it's already imported/available everywhere in `app.py`.

**Router-level dependency pattern (NEW, no direct in-repo precedent — from RESEARCH.md Pattern 1, safe mechanical approach):**
```python
# data-service/auth.py
from fastapi import APIRouter, Depends, Request

PUBLIC_PATHS = {"/", "/connectors/heartbeat", "/auth/login"}

async def require_principal(request: Request):
    if request.url.path in PUBLIC_PATHS:
        return None
    # 1. session cookie -> user principal (data-service/auth.py sessions store)
    # 2. Authorization: Bearer dgc_... -> connector principal (connectors.authenticate_token)
    # 3. X-<internal-header> -> internal-service principal (new, service-token store)
    # else: raise _structured_error_response(..., "AUTH_REQUIRED", 401)
    ...
```
```python
# data-service/app.py
router = APIRouter(dependencies=[Depends(require_principal)])
# mechanical rename: @app.(get|post|put|delete)( -> @router.\1(
app.include_router(router)
```
This is a regex-scriptable rename across all 65 `@app.*` decorators — no per-route hand-editing. Every decorator becomes `@router.*`; body code is unchanged except where a route needs `principal` or an explicit project-membership check.

---

### `data-service/tests/conftest.py` — `authorized_client` fixture (test, request-response)

**Analog:** current `conftest.py` (full file, 84 lines, read above) has zero client fixtures today — only CLI options (`--corpus`, `--arm`, etc.) and `live`/`eval`/`integration` markers via `pytest_addoption`/`pytest_configure`/`pytest_collection_modifyitems`. There is no fixture precedent in this file to copy verbatim; the new fixture is modeled on `httpx.Client(headers=...)` default-header usage already established in `tools/de01/legs.py` for DE-01's own service-token/config-driven `base_url` pattern (per RESEARCH.md; not re-read this session — verify `legs.py:185-298` at plan time before writing the exact `httpx.Client(...)` call).

**Pattern to add:**
```python
import pytest
from fastapi.testclient import TestClient
from data_service.app import app  # adjust import path to match module layout

@pytest.fixture
def authorized_client():
    """TestClient pre-authenticated as the bootstrap admin (D-05), reused by
    every test file that currently constructs its own module-level TestClient."""
    client = TestClient(app, raise_server_exceptions=False)
    # login once, reuse the session cookie for every subsequent request
    client.post("/auth/login", json={"username": "...", "password": "..."})
    return client
```
RESEARCH.md flags this as a wide-reaching, mechanical rewrite across the ~8+ files with a module-level `client = TestClient(app)` — size as its own wave, not folded into one plan.

---

### `data-service/tests/test_route_inventory.py` (NEW) (test, batch/static-analysis)

**Analog:** `tools/de01/tests/test_reproducibility_scope_drift.py` (fenced-block parser, lines 1-30 read above)

**Fenced-block parsing pattern** (verbatim):
```python
START_MARKER = "<!-- reproducibility:llm-call-sites:start -->"
END_MARKER = "<!-- reproducibility:llm-call-sites:end -->"

def load_fenced_call_sites() -> dict[str, str]:
    text = SPEC_PATH.read_text(encoding="utf-8")
    start = text.index(START_MARKER)
    end = text.index(END_MARKER)
    body = text[start + len(START_MARKER):end]
    result = {}
    for line in body.splitlines():
        line = line.strip()
        if not line or line.startswith("```"):
            continue
        parts = line.split("|")
        if len(parts) != 3:
            continue
        ...
    return result
```
`test_route_inventory.py` copies this exact parse shape for `spec/SECURITY-BOUNDARY.md`'s `security-boundary:public-routes:start/:end` block (3-field `METHOD|PATH|PRINCIPAL` lines instead of `file|function|scope_class`), then cross-checks it against `app.routes` (FastAPI's route list) — mirroring the "nothing in code that isn't in the block, nothing in the block that isn't in the code" bidirectional assertion this analog already implements.

---

### `data-service/tests/test_cross_project_matrix.py` (NEW) (test, request-response/batch)

**Analog:** `/designstate/capture`'s bound-project-mismatch behavior (see above) is the assertion shape to generalize: call every project-scoped route with a P2 project from a P1-only caller/token, assert 403 with the same generic anti-enumeration message pattern. Build the two-user/two-project fixture (D-15) on top of the new `authorized_client` fixture, parametrized over the Route Inventory table in RESEARCH.md (65 routes, project source column).

---

### `spec/SECURITY-BOUNDARY.md` (NEW) (config/spec, file-I/O)

**Analog:** `spec/REPRODUCIBILITY.md` lines 164-179 (fenced block + exclusion-note convention, verbatim):
````markdown
<!-- reproducibility:llm-call-sites:start -->
```
app.py|llm_generate|model-dependent-unmeasured
app.py|test_llm_settings|model-dependent-unmeasured
cg_recognition.py|recognize_structure|measured
...
```
<!-- reproducibility:llm-call-sites:end -->

Excluded as non-generative: `llm_gateway.py|list_models_for_provider` is excluded as
non-generative — it calls `get_adapter` only and never calls `.generate`, so it lists models
and produces no model output. It is recorded here as an exclusion note...
````
`spec/SECURITY-BOUNDARY.md` copies this exact two-part shape:
1. An `<!-- security-boundary:public-routes:start/:end -->` fenced block, one `METHOD|PATH|PRINCIPAL` line per public route (health, `/auth/login`, `/connectors/heartbeat`, etc.) — this is the D-14 test's source of truth.
2. A prose "excluded"/carve-out section immediately after the block, for cases like D-06's `tagProjectNodes`→`/graph/{project}/claim-untagged` cross-project write exception, mirroring how REPRODUCIBILITY.md documents `list_models_for_provider` as excluded rather than silently omitting it.

Also model the document's overall structure (trust zones, deployment profiles, principal types, known-default secret list, rotation procedure sections) on `spec/SWRL-SUBSET.md`'s normative-spec layout (not re-read this session for line-level detail; both `SWRL-SUBSET.md` and `REPRODUCIBILITY.md` are confirmed by CONTEXT.md/RESEARCH.md to share this pattern — read `SWRL-SUBSET.md` in full at plan/execution time for the surrounding prose-section headings).

---

### `ui-v2/src/lib/auth.js` (REWRITTEN) / `graphApi.js`, `modelApi.js`, `inputGenApi.js` (endpoint conversions) (provider/service, request-response)

**Analog:** `ui-v2/src/lib/connectorsApi.js` (not re-read this file directly this session, but its shape is visible via graphify: `base()` at line 8, `getJson()` at line 10, `listConnectors()` at line 27, `createCredential()` at line 33, `revokeCredential()` at line 56 — a small helper-wrapped-`fetch` client with a named function per endpoint). This is the exact target shape for the 7 new named endpoints replacing `executeCypher`.

**Current anti-pattern being replaced** (`graphApi.js` lines 1-34, verbatim — DELETE this shape entirely per D-06):
```javascript
const DEFAULTS = {
  neo4jHttp: "/neo4j",
  neo4jUser: "neo4j",
  neo4jPassword: "12345678",
  n8nWebhook: "/n8n/webhook/dg/rules-ingest",
  n8nQueryWebhook: "/n8n/webhook/dg/graph-query",
  dataServiceUrl: "/data-service"
};

export function getConfig() {
  return { ...DEFAULTS, ...(window.GRAPH_CONFIG || {}) };
}

export async function executeCypher(statement, parameters = {}) {
  const cfg = getConfig();
  const res = await fetch(cfg.neo4jHttp + "/db/neo4j/tx/commit", {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      Authorization: "Basic " + btoa(`${cfg.neo4jUser}:${cfg.neo4jPassword}`)
    },
    body: JSON.stringify({ statements: [{ statement, parameters }] })
  });
  ...
}
```
Every call site built on `executeCypher` (`fetchGraph` lines 41-58, `tagProjectNodes` lines 63-69, `updateNodeProp` lines 73-79, `fetchRules` lines 82-90, plus `fetchProjects` at line 268, `modelApi.js:39,50`, `inputGenApi.js:71`) is replaced by a named function calling a data-service REST endpoint instead, e.g.:
```javascript
// New shape, modeled on connectorsApi.js's getJson()/base() pattern
export async function fetchGraph(project) {
  const res = await fetch(`/data-service/graph/${encodeURIComponent(project)}`, {
    credentials: "include"
  });
  if (!res.ok) throw new Error((await res.json().catch(() => null))?.detail?.error || res.statusText);
  return res.json(); // { nodes, rels }
}
```
Every `fetch` call must add `credentials: "include"` (D-01 cookie flow — same-origin via nginx, confirmed no CORS needed) and must NOT set Basic-auth or any Neo4j credential header. `auth.js` becomes: `login(username, password)` → `POST /data-service/auth/login`, `logout()` → `POST /data-service/auth/logout`, `getCurrentUser()` reading from a `/auth/me`-style endpoint or a returned principal — replacing the current `localStorage.dg_users`/`SHA-256("dg_salt_"+password)` scheme entirely.

---

### `DG/src/DG.Grasshopper/Validation/{ValidationPublishClient,ComputgraphPublishClient}.cs` (service HTTP client, request-response)

**Analog:** `DG/src/DG.Core/Data/ConnectorHeartbeatClient.cs` (full file, 141 lines, read above)

**Bearer header pattern to copy** (lines 44-48, verbatim):
```csharp
using var request = new HttpRequestMessage(
    HttpMethod.Post,
    $"{NormalizeUrl(dataServiceUrl)}/connectors/heartbeat");
request.Headers.Authorization = new AuthenticationHeaderValue("Bearer", token);
```
Apply the identical `AuthenticationHeaderValue("Bearer", token)` line to `ValidationPublishClient.cs:36` and `ComputgraphPublishClient.cs:33` (their current unauthenticated `HttpRequestMessage` construction, per Correction 5) — same `TokenPrefix = "dgc_"` constant, same `NormalizeUrl` helper reuse if these classes don't already have one, same 401→`Rejected` / other-non-200→`Unreachable` status-code mapping shown at lines 55-70. Preserve the class's own doc-comment discipline: "The token flows only into the Authorization header — never into a field, log, or exception message."

## Shared Patterns

### Structured error responses
**Source:** `data-service/app.py:710-715` (`_structured_error_response`)
**Apply to:** every new 401/403 raised by `require_principal`, the D-15 cross-project matrix assertions, and any new named endpoint (D-06). Always `(error, hint, code, status_code)` with a generic, non-enumerating `error` message for anything auth-related (T-39-06 house style, demonstrated at `/designstate/capture`'s `CAPTURE_PROJECT_MISMATCH`).

### Token mint / hash-at-rest / JSON persistence
**Source:** `data-service/connectors.py` (whole file)
**Apply to:** `data-service/auth.py`'s users/sessions/memberships store (D-01/D-02/D-04). Same `DATA_DIR`-relative file, same load/save function pair, same "hash what you never need to read back" principle for session tokens (passwords need scrypt instead, per D-01, still stdlib).

### Bound-project equality check
**Source:** `data-service/app.py:2551-2558` (`/designstate/capture`)
**Apply to:** every project-scoped route's authorization step in `require_principal` / a shared `_authorize_project(principal, project)` helper — session-user membership check, connector-token bound-project check, and the D-15 test matrix all reuse this exact equality-then-generic-403 shape.

### Machine-checked fenced-block spec
**Source:** `spec/REPRODUCIBILITY.md:164-179` + `tools/de01/tests/test_reproducibility_scope_drift.py:1-30`
**Apply to:** `spec/SECURITY-BOUNDARY.md`'s D-17 public-route allowlist and `data-service/tests/test_route_inventory.py`'s D-14 parser/cross-check.

### Named REST client over raw fetch
**Source:** `ui-v2/src/lib/connectorsApi.js` (`base()`, `getJson()`, one function per endpoint)
**Apply to:** the rewritten `graphApi.js`, `modelApi.js`, `inputGenApi.js`, `auth.js` — every browser call becomes a small named async function hitting a fixed data-service path with `credentials: "include"`, no client-supplied Cypher, no embedded credential.

## No Analog Found

| File | Role | Data Flow | Reason |
|---|---|---|---|
| `docker-compose.multi-user.yml` | config | batch | No override-file precedent exists in this repo; RESEARCH.md's Docker Compose reference citation is the only source. Structure per RESEARCH.md "Deployment Profile Mechanics": redeclare `ports:` (omit non-UI/Speckle publishes) and set `DG_DEPLOYMENT: multi-user` in `environment:` (which merges key-by-key across `-f` layers, unlike arrays). |
| `.env.example` | config | file-I/O | Does not exist today (verified absent by RESEARCH.md). Trivial flat-file format; derive its key list directly from the docker-compose.yml secret inventory (Correction 6: `NEO4J_AUTH`/`NEO4J_PASSWORD`, n8n basic-auth password, `MINIO_*`, `POSTGRES_PASSWORD`, `LLM_MASTER_SECRET`, `SPECKLE_SESSION_SECRET`). |

## Metadata

**Analog search scope:** `data-service/` (app.py, connectors.py, tests/conftest.py), `tools/de01/tests/test_reproducibility_scope_drift.py`, `spec/REPRODUCIBILITY.md`, `ui-v2/src/lib/{graphApi,connectorsApi}.js`, `DG/src/DG.Core/Data/ConnectorHeartbeatClient.cs`; graphify query used to orient on `connectors.py`'s call graph before file reads (per project rule).
**Files scanned:** 7 read in full or targeted range (connectors.py full 270 lines; app.py targeted ranges 710-725, 2508-2568; graphApi.js lines 1-95; ConnectorHeartbeatClient.cs full 141 lines; conftest.py full 84 lines; REPRODUCIBILITY.md fenced block; test_reproducibility_scope_drift.py parser).
**Pattern extraction date:** 2026-09-28
