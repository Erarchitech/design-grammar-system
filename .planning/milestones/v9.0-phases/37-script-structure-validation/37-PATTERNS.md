# Phase 37: Script Structure Validation MVP - Pattern Map

**Mapped:** 2026-07-27
**Files analyzed:** 9
**Analogs found:** 9 / 9

## File Classification

| New/Modified File | Role | Data Flow | Closest Analog | Match Quality |
|---|---|---|---|---|
| `data-service/cg_structure_checks.py` (NEW) | service (deterministic Cypher checks) | request-response / batch-read | `data-service/computgraph_publish.py` (session-injection discipline) + `dg-reasoner/reasoning.py` (Phase 821, injectable-session tests) | exact (role+flow) |
| `llm/structure_rules.json` (NEW) | config (versioned declarative artifact) | transform (compiled to Cypher templates) | `llm/cypher_catalog.json` | exact (sibling convention) |
| `load_structure_rules()` (NEW fn, in `cg_structure_checks.py`) | utility (defensive catalog loader) | transform | `dg_context.load_cypher_catalog()` (L75-91) | exact |
| `data-service/app.py` (MODIFY: `POST /computgraph/validate`, `POST /computgraph/consult`) | route/controller | request-response | existing `POST /computgraph/publish` route (L1391-1418) + `ComputgraphPublishRequest` (L1375-1388) | exact |
| `fetch_computgraph_subgraph()` (NEW fn, `dg_context.py` or `cg_structure_checks.py`) | service (live scoped graph read) | request-response | `dg_context.fetch_existing_entities()` (L339-356) / `fetch_existing_design_states()` (L418-449) | exact |
| `/consult` gateway call (NEW, inside route handler) | service (in-process LLM call) | request-response | `dg_context.generate_validated_cypher()` in-process sequence (L880-922, esp. L906-915) | exact |
| `data-service/tests/test_cg_structure_checks.py` (NEW) | test | request-response (route-shape) + integration (live Neo4j) | `data-service/tests/test_computgraph_publish.py` (`FakeGraph`/`FixtureSession`/`_frame_cg_context()`) | exact |
| `/consult` test cassette (NEW fixture) | test fixture (record/replay) | request-response | `data-service/tests/recognition_eval/cassette.py` (`CassetteAdapter`, L119+) | role-match |
| `spec/RULE-PARTITION-POLICY.md` (MODIFY) | config/doc (decision table) | — | the doc's own existing "What Belongs Where (Decision Table)" (L36-46) + "How SHACL Findings Surface" severity table (L85-89) | exact (self-analog) |

## Pattern Assignments

### `data-service/cg_structure_checks.py` (service, request-response/batch-read)

**Analog:** `data-service/computgraph_publish.py` (session-injection + parameterized-Cypher discipline) and `dg-reasoner/reasoning.py` (Phase 821 precedent, cited in RESEARCH.md L317 for "functions accept an injectable session param... tests bypass live Neo4j entirely" — not re-read here, already verified by research).

**Imports pattern** (mirror `computgraph_publish.py` L48-56):
```python
from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any

from dg_identity import compute_dg_id  # only if a check needs dgId re-derivation
```

**Session-injection + parameterized-Cypher discipline** (verbatim structural precedent, `computgraph_publish.py` L63, L610-628 — this is the pattern EVERY check function must copy):
```python
def publish_structure(session: Any, project: str, cg_context: dict) -> dict:
    ...
    session.execute_write(_write)
    stale_entity_ids = _find_stale_entities(session, project, definition_id, params["allCgIds"])
    ...

def _find_stale_entities(session: Any, project: str, definition_id: str, current_cg_ids: list[str]) -> list[str]:
    """Read-only report... NO deletion Cypher..."""
    result = session.run(
        """
        MATCH (n {definitionId: $definitionId, project: $project, graph: 'Computgraph'})
        WHERE n.cgId IS NOT NULL AND NOT n.cgId IN $currentCgIds
        RETURN DISTINCT n.cgId AS cgId
        // op=PUBLISH_STALE_DIFF
        """,
        {
            "definitionId": definition_id,
            "project": project,
            "currentCgIds": current_cg_ids,
        },
    )
    return [record["cgId"] for record in result]
```
**Discipline to copy exactly:**
1. `session: Any` is always the first param, no lazy-connect default inside the check function itself — caller (route handler) owns the session (matches `computgraph_publish.py`'s "caller owns the session" and `dg_context.fetch_existing_entities()`'s dual-mode session pattern below).
2. Every `session.run(...)` call passes `{"project": project, "definitionId": definition_id, ...}` as a **bound parameter dict** — never f-string/`.format()`/`%` interpolation into Cypher text (T-36-01 precedent; RESEARCH.md's T-37 cross-project-leakage risk is exactly this discipline, extended).
3. A trailing `// op=<TAG>` Cypher comment on every query, for future FakeGraph-style dispatch in unit tests (route-shape tier only — see Pitfall 2 below for why this can't replace live-Neo4j tests for read-pattern checks).

**Every check function should look like RESEARCH.md's Pattern 1** (already given verbatim in RESEARCH.md, reproduced here as the literal target):
```python
def check_orphan_patterns(session: Any, project: str, definition_id: str) -> list[dict]:
    result = session.run(
        """
        MATCH (pn:Pattern {project: $project, definitionId: $definitionId})
        WHERE NOT ()-[:HAS_PATTERN]->(pn)
        RETURN pn.cgId AS cgId, pn.patternName AS name
        // op=CHECK_ORPHAN_PATTERN
        """,
        {"project": project, "definitionId": definition_id},
    )
    return [
        {
            "checkId": "orphan_pattern",
            "severity": "violation",
            "message": (
                f"Pattern '{row['name']}' has no owning Procedure. "
                f"Where: Pattern cgId={row['cgId']}. "
                "How to fix: re-tag this Pattern under a Procedure group and re-publish."
            ),
            "entities": [{"label": "Pattern", "cgId": row["cgId"], "name": row["name"]}],
        }
        for row in result
    ]
```

**Convention-compliance check is the one exception — reads JSON, not Cypher pattern** (per RESEARCH.md Pitfall 1, `computgraph_publish.py` L150-151, L161):
```python
# _storage_ctx strips only 'untagged'; 'warnings' survives into Algorithm.contextJson:
_storage_ctx = {k: v for k, v in cg_context.items() if k != "untagged"}
context_json = json.dumps(_storage_ctx, sort_keys=True)
# ... written as Algorithm.contextJson (computgraph_publish.py L161)
```
Implement as: fetch `Algorithm.contextJson` via a simple `MATCH (a:Algorithm {project:$project, definitionId:$definitionId}) RETURN a.algIndex, a.contextJson`, `json.loads()` each row in Python, inspect the envelope's top-level `warnings: string[]` array. Never `WHERE name CONTAINS 'Emr'` — the raw tag string never reaches the published graph (normalization already happened in `CanvasAnnotationParser.cs` pre-publish).

**Rule-mapped checks (SVAL-02) — declarative operation dispatch, RESEARCH.md Pattern 2 (already concrete, reproduced verbatim as the literal target):**
```python
# structure_rules.json entry:
# {"ruleId": "R_STRUCT_FRAME_TRUSS", "operation": "requiresProcedure", "params": {"namePattern": "*Truss*"}}

_OPERATION_TEMPLATES = {
    "requiresProcedure": """
        MATCH (a:Algorithm {project: $project, definitionId: $definitionId})
        OPTIONAL MATCH (a)-[:HAS_PROCEDURE]->(pr:Procedure)
          WHERE pr.procedureName CONTAINS $namePattern
        RETURN a.algIndex AS algIndex, collect(pr.cgId) AS matchingProcedureCgIds
        // op=RULE_REQUIRES_PROCEDURE
    """,
    # ... requiresParameter, forbidsOrphan, requiresInterface
}
```
Never let a `structure_rules.json` entry embed raw Cypher — operation name + params only.

**Error handling / defensive checks (currently-unreachable-but-cheap):** `Parameter without dataType` and `Object without HAS_BEHAVIOR` are pre-empted by `_build_publish_params`'s `ValueError` at publish time (`computgraph_publish.py` L217-... raises on unrecognized `paramKind`/`dataType`) — implement as trivial Cypher `WHERE` guards anyway (RESEARCH.md Open Question 2 recommends keeping them, cheap defensive insurance).

---

### `llm/structure_rules.json` (config, transform)

**Analog:** `llm/cypher_catalog.json` — top-level shape to mirror exactly:
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
**Adapt field names** for `structure_rules.json` (per RESEARCH.md's Open-for-Planning Item 1 resolution):
```json
{
  "version": 1,
  "mappings": [
    {
      "ruleId": "R_STRUCT_FRAME_TRUSS",
      "operation": "requiresProcedure",
      "params": {"namePattern": "*Truss*"}
    }
  ]
}
```
Top-level key is `mappings` (a list), matching `cypher_catalog.json`'s `shapes` (a list) 1:1 in spirit — same `{"version": <int>, "<array-key>": [...]}` envelope shape.

---

### `load_structure_rules()` (utility, defensive loader)

**Analog:** `dg_context.load_cypher_catalog()` (L75-91) — exact pattern to mirror, already given concretely in RESEARCH.md's "Code Examples" section:
```python
# Source: data-service/dg_context.py load_cypher_catalog() (L75-91) -- exact pattern to mirror
def load_structure_rules() -> dict[str, Any]:
    if not STRUCTURE_RULES_FILE.exists():
        return {"version": 0, "mappings": []}
    try:
        payload = json.loads(STRUCTURE_RULES_FILE.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {"version": 0, "mappings": []}
    if not isinstance(payload, dict) or not isinstance(payload.get("mappings"), list):
        return {"version": 0, "mappings": []}
    return payload
```
**Path resolution** — copy the Docker-mount-aware pattern verbatim (`dg_context.py` L57-61):
```python
CYPHER_CATALOG_FILE = (
    Path(os.getenv("DG_KNOWLEDGE_REPO_ROOT", str(Path(__file__).resolve().parent.parent)))
    / "llm"
    / "cypher_catalog.json"
)
```
→ `STRUCTURE_RULES_FILE = ... / "llm" / "structure_rules.json"`, same `DG_KNOWLEDGE_REPO_ROOT` env var / `/mnt/repo` volume-mount convention. Also mirror the derived module-level index pattern (`dg_context.py` L94-103, `cypher_shape_ids()` / `CYPHER_SHAPE_IDS`) if a `rule_id`-index is useful for `/computgraph/validate`'s dispatch.

---

### `data-service/app.py` — `POST /computgraph/validate`, `POST /computgraph/consult` (route/controller, request-response)

**Analog:** existing `POST /computgraph/publish` route (`app.py` L1391-1418) + its Pydantic request model (L1375-1388).

**Request model pattern** (mirror L1375-1388):
```python
class ComputgraphPublishRequest(BaseModel):
    project: str
    cgContext: dict
```
→ `ComputgraphValidateRequest(BaseModel): project: str; definitionId: str | None = None`
→ `ComputgraphConsultRequest(BaseModel): project: str; definitionId: str; question: str`

**Route + structured-error pattern** (verbatim target, L1391-1418):
```python
@app.post("/computgraph/publish")
def post_computgraph_publish(payload: ComputgraphPublishRequest):
    """Thin route -- opens its own session (so the whole write is one
    transaction), delegates to computgraph_publish.publish_structure(), and
    returns {status, publishedCounts, staleEntityIds}."""
    try:
        with driver.session() as session:
            return computgraph_publish.publish_structure(
                session, payload.project, payload.cgContext
            )
    except ValueError as exc:
        raise _structured_error_response(
            str(exc),
            "Check the submitted cgContext shape (cgContextJson v1 envelope).",
            "COMPUTGRAPH_PUBLISH_REQUEST_INVALID",
            422,
        )
    except Exception as exc:
        raise _structured_error_response(
            str(exc),
            "Check Neo4j availability and the publish payload.",
            "COMPUTGRAPH_PUBLISH_FAILED",
            502,
        )
```
Copy this exact try/except-`ValueError`(422)/except-`Exception`(502) + `_structured_error_response(message, hint, code, status)` shape for both new routes — same as `_context_type_invalid_error()` pattern at L1426-1432 for `/context/assemble`.

**`/computgraph/validate` route body:** open one session, call each `cg_structure_checks.py` check function, assemble `findings[]` + `ruleResults[]` into the report JSON contract (RESEARCH.md L206-226) — thin route, all logic delegated, matching the `publish_structure()` delegation discipline above.

**`/computgraph/consult` route body:** call `fetch_computgraph_subgraph()` (new), assemble prompt, call gateway in-process (see below), run the grounding post-check, return the response shape (RESEARCH.md L169-180).

---

### `fetch_computgraph_subgraph()` (service, request-response — NEW fn, live scoped read)

**Analog:** `dg_context.fetch_existing_entities()` (L339-356) — dual-mode session pattern to mirror exactly:
```python
def fetch_existing_entities(project: str, session: Any = None) -> list[dict[str, Any]]:
    """`session` is duck-typed to the `neo4j.Session.run(query, **params)`
    contract... Pass a FixtureSession in unit tests for zero live Neo4j;
    omit it in production and this lazily opens a real session against this
    module's own driver."""
    if session is not None:
        result = session.run(_EXISTING_ENTITIES_QUERY, project=project)
        return [dict(record) for record in result]
    with _get_driver().session() as live_session:
        result = live_session.run(_EXISTING_ENTITIES_QUERY, project=project)
        return [dict(record) for record in result]
```
Adapt to accept both `project` AND `definition_id` (unlike `fetch_existing_entities`'s project-only scope) — this is the security-critical addition per RESEARCH.md's Known Threat Patterns table ("Cross-project data leakage... `fetch_computgraph_subgraph` must scope every Cypher `MATCH` by both `project` AND `definitionId`").

**Determinism discipline** — mirror `fetch_existing_design_states()`'s explicit `ORDER BY` (L407-414, `_EXISTING_DESIGN_STATES_QUERY`): `"...ORDER BY run.createdAt DESC, run.runId LIMIT 25"`. `fetch_computgraph_subgraph` must use an equivalent deterministic `ORDER BY` on entity `cgId`/`name` — no embeddings, no timestamps, no set-derived collections (CTXA-05 discipline, cited in RESEARCH.md L165).

**Do NOT** add a 4th value to `CONTEXT_REQUEST_TYPES` (`dg_context.py` L108: `{"rule_ingest", "rule_edit", "graph_query"}`) or route through `assemble_context()` (L455+, dispatches on `req.type in CONTEXT_REQUEST_TYPES`, raises `ValueError` otherwise) — write a dedicated function instead, called directly by the new route.

---

### `/consult` gateway call (service, request-response — in-process LLM call)

**Analog:** `dg_context.generate_validated_cypher()`'s in-process call sequence (L880-922). The exact sequence to reuse verbatim (already given concretely in RESEARCH.md's Code Examples, reproduced here):
```python
master_secret = os.getenv("LLM_MASTER_SECRET", "")
settings = load_persisted_llm_settings()
provider, model, api_key = resolve_active_provider(settings, master_secret)
adapter = get_adapter(provider, settings.get("baseUrl"))

req = GenerateRequest(prompt=consult_prompt, model=model, provider=provider)
response = adapter.generate(req, api_key)
```
**Never** re-POST to `/llm/generate` — this is an explicit anti-pattern RESEARCH.md flags twice (Architecture Patterns "Anti-Patterns to Avoid", Don't Hand-Roll table row 2: reuse `resolve_active_provider()` + `get_adapter()`, never build a new provider-selection helper).

**Grounding post-check (flag, don't block):** plain Python string-containment — extract entity names from the assembled subgraph (from `fetch_computgraph_subgraph()`'s result), scan the LLM answer text for each, populate `citedEntities`/`ungroundedMentions`/`groundedCount` per RESEARCH.md's response shape (L169-180). No claim/triple-decomposition pipeline (explicitly out of scope, Don't Hand-Roll table row 3).

---

### `data-service/tests/test_cg_structure_checks.py` (test — two-tier)

**Analog:** `data-service/tests/test_computgraph_publish.py` — header/setup convention (L1-31), `FakeResult`/`FakeGraph`/`FixtureSession`/`FakeDriver` harness (L47-325), and `_frame_cg_context()` fixture builder (L328-459+).

**Header/setup pattern to copy verbatim** (L14-31):
```python
from __future__ import annotations

import os
import re
import sys

import pytest
from fastapi.testclient import TestClient

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

os.environ.setdefault("LLM_MASTER_SECRET", "test-master-secret")

import app as app_module  # noqa: E402
import computgraph_publish  # noqa: E402
from app import app  # noqa: E402

client = TestClient(app, raise_server_exceptions=False)
```

**`FakeGraph`/`FixtureSession`/`FakeDriver` route-shape tier** (L47-325) — reuse the exact `op=` regex-dispatch harness:
```python
_OP_RE = re.compile(r"op=(\w+)")

class FakeResult:
    def __init__(self, rows: list[dict]):
        self._rows = list(rows)
    def single(self):
        return self._rows[0] if self._rows else None
    def __iter__(self):
        return iter(self._rows)

class FakeGraph:
    def __init__(self):
        self.nodes: dict[tuple[str, str, str], dict] = {}
        self.relationships: list[tuple[str, tuple, tuple]] = []
        self.calls: list[tuple[str, dict]] = []
    def _set_node(self, label, key, project, props): ...
    def execute(self, op: str, params: dict) -> list[dict]:
        self.calls.append((op, dict(params)))
        if op == "PUBLISH_OBJECT":
            ...
```
Use this ONLY for route-shape/response-shape tests (does the endpoint return the right JSON structure given a canned check-function result) — **per RESEARCH.md Pitfall 2, FakeGraph cannot substitute for real Cypher pattern-match correctness** (it duck-types a fixed op-tag dispatch, not a real Cypher interpreter). SVAL-01/02's `WHERE NOT (...)->()` multi-hop reads must be tested against live Neo4j inside the docker-compose network.

**`_frame_cg_context()` fixture builder — the exact base to derive SC1/SC2 mutated variants from** (L328-459+):
```python
def _frame_cg_context(project: str = GOLDEN_PROJECT, definition_id: str = GOLDEN_DEFINITION_ID) -> dict:
    """A trimmed cgContextJson v1 envelope for the Frame fixture: 1 Object, 1
    Algorithm (index 1), 2 Procedures (11_Proc tagged / 12_Proc recognized), each
    with 1 Pattern/Parameter/Interface. One wire links the tagged Parameter's
    member to the tagged Interface's member (PARAM_LINK derivation)."""
    return {
        "schemaVersion": "cg-context-1",
        "project": project,
        "definition": {"documentId": definition_id, "fileName": "frame.gh", ...},
        "object": {"name": "FRAME", "classIri": None, "source": "tagged", "dgId": None},
        "algorithms": [
            {
                "index": 1, "name": "1_ALGORITHM",
                "procedures": [
                    {
                        "id": GOLDEN_CG_ID, "index": 11, "name": "11_Proc", "source": "tagged",
                        "patterns": [...], "parameters": [...],
                        "interfaces": [
                            {"id": "cg:1:intf:11_IntF_ParSplitAt", "name": "ParSplitAt",
                             "ifaceType": "Input", "memberIds": ["n-parsplit"], "source": "tagged", ...}
                        ],
                    },
                    {"id": "cg:1:proc:12_Proc", "index": 12, "name": "12_Proc", "source": "recognized", ...},
                ],
            }
        ],
        "untagged": {...},  # must never reach the published store
        "nodes": [], "wires": [...],
    }
```
**How to derive the two required test variants per RESEARCH.md's Wave 0 Gaps and CONTEXT.md's verification sketch:**
1. **SC1 (Interface removal from `11_Proc`):** deep-copy the dict returned by `_frame_cg_context()`, then delete the `"interfaces"` list (or set it to `[]`) on the first procedure entry (`procedures[0]`, `name == "11_Proc"`), before calling `publish_structure()`/`POST /computgraph/publish`. Expected: `procedure_without_interface` check fires for `cgId=GOLDEN_CG_ID`.
2. **SC2 (`12_Proc` group entirely absent):** deep-copy, then remove `procedures[1]` (the `"12_Proc"` / `source: "recognized"` entry) entirely from `algorithms[0]["procedures"]` before publishing. Publish this as a **second, distinct `definitionId`** (e.g. `"frame-no-footer.gh"`) alongside the full Frame fixture (published under `GOLDEN_DEFINITION_ID`) in the same test Neo4j — then run the `requiresProcedure`/`R_STRUCT_FRAME_TRUSS`-style rule mapped to `*Footer*` against both: passes on the full Frame, fails on the copy missing `12_Proc`.

**`registry` fixture pattern** (L320-325) — reuse for wiring `FakeDriver` into `app_module.driver`:
```python
@pytest.fixture
def registry(monkeypatch):
    graph = FakeGraph()
    monkeypatch.setattr(app_module, "driver", FakeDriver(graph))
    return graph
```

---

### `/consult` test cassette (test fixture, request-response — record/replay)

**Analog:** `data-service/tests/recognition_eval/cassette.py` — `CassetteAdapter` class (L119+), `CassetteMissError`/`CassetteWriteError` (L102-117). Use this to provide a deterministic LLM response fixture for SC3 (`/consult` cites `11_Var_HTotal`) without a live LLM call in CI — wrap/monkeypatch the adapter the new `/consult` route resolves via `get_adapter()` with a `CassetteAdapter` instance keyed on the consult prompt, exactly as existing recognition-eval tests do for `cg_recognition.py`'s LLM calls (`_FakeAdapterForRetry` in `test_cg_recognition.py` L384 is the sibling in-process fake-adapter precedent, not re-read here — same substitution point: `adapter.generate(req, api_key)`).

---

### `spec/RULE-PARTITION-POLICY.md` (config/doc, decision-table update)

**Analog:** the document's own existing "What Belongs Where (Decision Table)" (L36-46) and "How SHACL Findings Surface" severity table (L85-89) — extend both, do not restructure.

**Existing decision-table row format** (L38, reproduce exactly for the new rows):
```
| Rule Category | Example | System | Rationale |
|---|---|---|---|
| Quantitative geometry/parameter limit | "Maximum building height is 75 meters" | **SWRL** | Architect-authored, project-specific business content... |
```
**New rows to append** (RESEARCH.md L106-110, already drafted verbatim — copy directly):
```
| Script/Computgraph structural shape (LPG-native, no RDF projection) | "Every `Procedure` has at least one `Interface`"; "no orphan `Pattern`" | **Cypher (`cg_structure_checks.py`)** | Computgraph is a Neo4j LPG partition with no RDF/OWL translation (unlike ValidGraph/Metagraph); SHACL has no path to this data... |
| Rule-mapped script-structure requirement | "A Frame `Algorithm` must contain a *Truss* `Procedure`" | **Cypher, referencing a Metagraph `Rule` by id (`llm/structure_rules.json`)** | Architect-authored intent (like SWRL) but evaluated against Computgraph shape, not BIM geometry/parameters... |
```
**Existing severity table** (L85-89) to reuse verbatim, not modify — SVAL findings' `severity` field values map onto it directly:
```
| SHACL Severity | DG Severity | Color |
|---|---|---|
| `sh:Violation` | violation | red |
| `sh:Warning` | warning | orange |
| `sh:Info` | info | yellow |
```

## Shared Patterns

### Session-injection discipline (cross-cutting: `cg_structure_checks.py`, `fetch_computgraph_subgraph()`)
**Source:** `data-service/computgraph_publish.py` (whole-module docstring L41-45) + `dg_context.fetch_existing_entities()` L339-356
**Apply to:** every new function that touches Neo4j in this phase
```python
# Security: every session.run/tx.run call receives parameters as a dict --
# entity names, ids are NEVER f-string/%/.format interpolated into query text.
if session is not None:
    result = session.run(QUERY, project=project, definitionId=definition_id)
else:
    with _get_driver().session() as live_session:
        result = live_session.run(QUERY, project=project, definitionId=definition_id)
```

### Structured error response (cross-cutting: both new routes)
**Source:** `data-service/app.py` L1405-1418 (`_structured_error_response(message, hint, code, status)`)
**Apply to:** `POST /computgraph/validate`, `POST /computgraph/consult`
```python
except ValueError as exc:
    raise _structured_error_response(str(exc), "<hint>", "<CODE>_INVALID", 422)
except Exception as exc:
    raise _structured_error_response(str(exc), "<hint>", "<CODE>_FAILED", 502)
```

### Defensive versioned-artifact loader (cross-cutting: `structure_rules.json`)
**Source:** `data-service/dg_context.py` L75-103 (`load_cypher_catalog()` + `cypher_shape_ids()` + `CYPHER_SHAPE_IDS` module constant)
**Apply to:** `load_structure_rules()` in `cg_structure_checks.py`
```python
def load_structure_rules() -> dict[str, Any]:
    if not STRUCTURE_RULES_FILE.exists():
        return {"version": 0, "mappings": []}
    try:
        payload = json.loads(STRUCTURE_RULES_FILE.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {"version": 0, "mappings": []}
    if not isinstance(payload, dict) or not isinstance(payload.get("mappings"), list):
        return {"version": 0, "mappings": []}
    return payload
```

### In-process LLM gateway call (cross-cutting: `/consult` only — validate path stays LLM-free)
**Source:** `data-service/dg_context.py` L906-915 (`generate_validated_cypher()`)
**Apply to:** `POST /computgraph/consult` route handler
```python
master_secret = os.getenv("LLM_MASTER_SECRET", "")
settings = load_persisted_llm_settings()
provider, model, api_key = resolve_active_provider(settings, master_secret)
adapter = get_adapter(provider, settings.get("baseUrl"))
req = GenerateRequest(prompt=consult_prompt, model=model, provider=provider)
response = adapter.generate(req, api_key)
```
**Gate check (SC4):** `grep -c "llm_gateway\|adapter.generate" data-service/cg_structure_checks.py` must return 0 — this call belongs ONLY in the `/consult` code path.

### Severity taxonomy (cross-cutting: every SVAL finding's `severity` field)
**Source:** `spec/RULE-PARTITION-POLICY.md` L85-89 (SHACL's `{violation, warning, info}` mapping, reused verbatim)
**Apply to:** every finding in `cg_structure_checks.py`'s output
| SVAL Severity | When used |
|---|---|
| `violation` | Orphan Pattern, Procedure without Interface, dangling PARAM_LINK, Algorithm without Procedure |
| `warning` | Rule-mapped structural requirement fails (SVAL-02) |
| `info` | Annotation-convention normalization surfaced from `Algorithm.contextJson.warnings` |

### Message discipline (What+Where+How-to-fix)
**Source:** `data-service/dg_context.py` `validate_cypher()` violation messages (L692-700, cited by RESEARCH.md, not re-read — already verified)
**Apply to:** every SVAL finding's `message` field — three-part structure, not a bare string, matching the `check_orphan_patterns` example above.

## No Analog Found

None — every new/modified file in this phase has a direct, verified codebase analog (Phase 36/29/821/35-13 precedents cover session-injection, versioned-artifact loading, route/error shaping, test harnesses, and cassette-based LLM fixtures).

## Metadata

**Analog search scope:** `data-service/` (computgraph_publish.py, dg_context.py, app.py, llm_gateway.py, gh_bridge.py, tests/), `llm/cypher_catalog.json`, `spec/RULE-PARTITION-POLICY.md`, `data-service/tests/recognition_eval/cassette.py`
**Files scanned:** graphify BFS queries (2, ~500 nodes total) + 6 direct file reads (computgraph_publish.py x2 ranges, dg_context.py x3 ranges, app.py x1 range, test_computgraph_publish.py x2 ranges, cypher_catalog.json head, cassette.py grep, RULE-PARTITION-POLICY.md grep)
**Pattern extraction date:** 2026-07-27
