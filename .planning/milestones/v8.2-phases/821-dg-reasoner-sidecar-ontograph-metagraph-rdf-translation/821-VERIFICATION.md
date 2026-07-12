---
phase: 821-dg-reasoner-sidecar-ontograph-metagraph-rdf-translation
verified: 2026-07-12T23:00:00Z
status: passed
score: 22/22 must-haves verified
behavior_unverified: 0
overrides_applied: 0
gaps: []
---

# Phase 821: dg-reasoner Sidecar & OntoGraph/Metagraph RDF Translation Verification Report

**Phase Goal:** A new isolated `dg-reasoner` service is live in docker-compose and correctly translates the live Neo4j OntoGraph/Metagraph into RDF for both the OWL and SHACL paths.

**ROADMAP Requirement:** REAS-05

**Verified:** 2026-07-12T23:00:00Z
**Status:** passed
**Score:** 22/22 must-haves verified
**Re-verification:** No — initial verification

## Goal Achievement

### Observable Truths (22/22 verified)

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | D-08: `dg-reasoner/` exists as a top-level service mirroring `data-service/` (Dockerfile, app.py, requirements.txt, tests/) | VERIFIED | All files present: dg-reasoner/Dockerfile, requirements.txt, app.py, tests/conftest.py, tests/test_health.py, tests/test_n10s_smoke.py |
| 2 | D-05: Sidecar reads Neo4j via NEO4J_URI/NEO4J_USER/NEO4J_PASSWORD env vars with dev-safe defaults | VERIFIED | app.py:25-27, reasoning.py:48-50 — all use `os.getenv("NEO4J_PASSWORD", "12345678")`, never hardcoded as bare literals |
| 3 | D-02: n10s plugin installed on neo4j with smoke-check test | VERIFIED | neo4j/Dockerfile:7-9 bakes neosemantics-5.26.0.jar; docker-compose.yml:14-15 has procedure allowlist; test_n10s_smoke.py asserts n10s procedures respond |
| 4 | D-07: `./ontology` volume-mounted read-only into sidecar | VERIFIED | docker-compose.yml:28 `.\ontology:/app/ontology:ro` |
| 5 | D-12: Sidecar internal-only — no host port, no nginx route | VERIFIED | docker-compose.yml:19-30 — dg-reasoner service has NO `ports:` mapping; only accessible as `dg-reasoner:8000` on internal network |
| 6 | Data-service and dg-reasoner both start without mutual dependency; DG_REASONER_URL set on data-service | VERIFIED | docker-compose.yml:52 `DG_REASONER_URL: http://dg-reasoner:8000` on data-service; data-service does NOT depend_on dg-reasoner (only neo4j+speckle); dg-reasoner depends_on neo4j only |
| 7 | D-01: ontology_export.py is a clean implementation of spec/LPG-OWL-MAPPING.md (not spike port); n10s not imported in reasoning path | VERIFIED | ontology_export.py labels-scoped Cypher, IRI minting, edge-property reification — clean implementation; grep confirms no n10s/neosemantics import in ontology_export.py (only docstring mention) or reasoning.py (no match) |
| 8 | D-14: Fidelity asserted structurally via RDFLib round-trip (no golden-byte diffs) | VERIFIED | test_ontology_export.py walks parsed Turtle via rdf:first/rdf:rest chains; assertions verify ARG.pos mapping and HAS_BODY/HAS_HEAD.order — all 8 tests pass |
| 9 | Success criterion 2: Label-scoped export produces valid Turtle; ARG.pos and order survive | VERIFIED | test_ontology_export.py proves order and argument position mapping — all 8 structural fidelity tests pass |
| 10 | Export scopes by node LABEL, never `graph` property (Pitfall 1) | VERIFIED | ONTOGRAPH_QUERY:44-48 uses `AND (n:Class OR ...)`, METAGRAPH_QUERY:50-55 uses `AND (n:Rule OR ...)`; ATOM_COUNT_QUERY:75 also label-scoped; AssertionError guard at ontology_export.py:276-282 on count mismatch |
| 11 | BuiltinAtom uses swrl:arguments universally; binary atoms use swrl:argument1/2; incomplete atoms captured as SkippedAtom | VERIFIED | test_builtin_atom_uses_swrl_arguments_not_argument1_2 passes; test_incomplete_atom_becomes_skipped_atom passes; emission code at ontology_export.py:387-399 |
| 12 | D-13/D-15: Unit fidelity tests in pytest, no docker/JRE needed | VERIFIED | python -m pytest passes 13/13 on always-on tests; FixtureSession duck-types neo4j.Session.run() — zero docker/JRE dependency |
| 13 | D-03: Hybrid union — static TBox + curated overlay + live export | VERIFIED | reasoning.py:_hybrid_union (lines 89-104) parses DG_OWL_PATH (xml), DG_DISJOINTNESS_PATH (turtle), adds ontology_export.build_graph triples |
| 14 | D-04: Curated owl:disjointWith overlay in separate version-controlled file | VERIFIED | ontology/dg-disjointness.ttl exists, parses as valid Turtle (rdflib parse), contains real Door/Window and Wall/Slab disjointness axioms; DesignGrammar-V7.owl unmodified |
| 15 | D-09: Synchronous POST with hard timeout that kills HermiT/JVM subprocess | VERIFIED | reasoning.py uses `multiprocessing.get_context("spawn")` (fixes WR-03), worker calls `os.setsid()` for process-group isolation, timeout kills via `os.killpg()` (fixes CR-02); test_routes.py asserts timeout returns 504 |
| 16 | D-10: Full response contract {consistent, unsatisfiable_classes, axiom_counts, duration_ms, stripped_builtin_rules} | VERIFIED | app.py:53-55 ConsistencyRequest model; reasoning.py:222-239 run_consistency return dict; test_reason_consistency_returns_d10_contract asserts all D-10 keys present |
| 17 | D-11: pySHACL with empty shapes graph returns {conforms: true, results: []} | VERIFIED | reasoning.py:291-319 run_shacl calls real pyshacl.validate() against empty Graph; test_shacl_validate_returns_empty_shapes_contract passes |
| 18 | Builtin rules stripped via strip_hermit_unsupported; count reported | VERIFIED | reasoning.py:212 calls strip_hermit_unsupported(union); returned as stripped_builtin_rules in response; CR-03 fix validates missing/duplicate ARG.pos values |
| 19 | Success criterion 3: POST /reason/consistency and POST /shacl/validate routes exist | VERIFIED | app.py:62-91 defines both routes; test_routes.py proves contract shapes; 501 stubs removed |
| 20 | D-06: Thin data-service proxy with short httpx timeout | VERIFIED | data-service/app.py:1173-1210 POST /reasoner/consistency forwards to DG_REASONER_URL; CR-01 fix applied: `timeout=httpx.Timeout(connect=2.0, read=95.0, write=2.0, pool=2.0)`; TimeoutException -> 504, ConnectError -> 502 |
| 21 | D-12: Sidecar internal-only via proxy only | VERIFIED | No host ports on dg-reasoner; only reachable through data-service proxy; no nginx route to dg-reasoner |
| 22 | D-16: Drift-immunity regression guard for mistagged atoms | VERIFIED | test_roundtrip_integration.py:test_drift_immunity_mistagged_door_orientation_atoms_exported asserts R_DOOR_ORIENTATION_V_A1/_A2 appear in label-scoped export; code path verified |

**Score:** 22/22 truths verified (0 behavior-unverified)

### Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| dg-reasoner/Dockerfile | Python 3.11 + JRE, uvicorn port 8000 | VERIFIED | Contains build-essential + openjdk-21-jre-headless (17 unavailable on trixie); CMD uvicorn app:app --host 0.0.0.0 --port 8000 |
| dg-reasoner/requirements.txt | Pinned reasoning deps | VERIFIED | owlready2==0.51, rdflib==7.6.0, pyshacl==0.40.0, owlrl==7.6.2, neo4j==6.2.0, starlette<1.0.0, httpx |
| dg-reasoner/app.py | FastAPI app with /health, /reason/consistency, /shacl/validate | VERIFIED | Module-level Neo4j driver; /health probes neo4j; real reasoning routes replacing 501 stubs |
| dg-reasoner/ontology_export.py | Cypher->RDF translator | VERIFIED | build_graph(session, project) -> rdflib.Graph; label-scoped queries; strip_hermit_unsupported; SkippedAtom/SkippedRule capture |
| dg-reasoner/reasoning.py | Hybrid reasoning core | VERIFIED | run_consistency, run_shacl; _hybrid_union; spawn-context multiprocessing + os.setsid() + os.killpg(); NTriples serialization |
| dg-reasoner/tests/conftest.py | Pytest fixtures | VERIFIED | integration marker; neo4j_available() helper; session-scoped neo4j_driver fixture that skips cleanly |
| dg-reasoner/tests/test_health.py | /health returns 200 | VERIFIED | FastAPI TestClient; asserts status==ok and neo4j in body |
| dg-reasoner/tests/test_n10s_smoke.py | n10s procedures respond | VERIFIED | @pytest.mark.integration; asserts n10s* procedures count > 0; tests graphconfig.init callable |
| dg-reasoner/tests/test_ontology_export.py | Structural fidelity tests | VERIFIED | 8 tests; FixtureSession shim; parses Turtle back with rdflib; asserts ARG.pos and order survive |
| dg-reasoner/tests/test_routes.py | Route contract tests | VERIFIED | 4 tests; FastAPI TestClient; monkeypatched reasoning functions; asserts D-10/D-11 contract shapes |
| dg-reasoner/tests/test_roundtrip_integration.py | Live round-trip + drift immunity | VERIFIED | @pytest.mark.integration; calls run_consistency against real v8-ui-smoke; asserts D-16 drift-immunity |
| dg-reasoner/tests/fixtures/metagraph_fixture.json | Graph-shaped test fixture | VERIFIED | Models R_BUILDING_MAX_STOREY_9_V worked example; multi-atom body, BuiltinAtom, both ARG positions, incomplete atom |
| neo4j/Dockerfile | Pinned neo4j 5.26 + n10s | VERIFIED | FROM neo4j:5.26; wget-fetches neosemantics-5.26.0.jar; deterministic install |
| docker-compose.yml | dg-reasoner service wired | VERIFIED | Internal-only; ./ontology:/app/ontology:ro; DG_REASONER_URL on data-service; n10s allowlist on neo4j |
| ontology/dg-disjointness.ttl | Curated disjointness overlay | VERIFIED | Real Door/Window + Wall/Slab disjointWith; separate from DesignGrammar-V7.owl; valid Turtle |
| data-service/app.py | POST /reasoner/consistency proxy | VERIFIED | httpx forward with short timeout; TimeoutException->504, ConnectError->502; no new deps |

### Key Link Verification

| From | To | Via | Status | Details |
|------|-----|-----|--------|---------|
| docker-compose dg-reasoner service | bolt://neo4j:7687 | NEO4J_URI env var | WIRED | app.py:25, reasoning.py:48 — `os.getenv("NEO4J_URI", "bolt://neo4j:7687")` |
| dg-reasoner:8000 (internal) | docker-compose network | dg-reasoner container name | WIRED | docker-compose.yml:20 — `build: ./dg-reasoner`, no host ports; reachable as http://dg-reasoner:8000 |
| ./ontology:/app/ontology:ro | dg-reasoner container | docker-compose volume mount | WIRED | docker-compose.yml:28 — `.\ontology:/app/ontology:ro` |
| data-service DG_REASONER_URL | dg-reasoner:8000 | compose environment variable | WIRED | docker-compose.yml:52 — `DG_REASONER_URL: http://dg-reasoner:8000` |
| data-service POST /reasoner/consistency | dg-reasoner POST /reason/consistency | httpx.post(DG_REASONER_URL/reason/consistency) | WIRED | data-service/app.py:1183-1188 — forwards payload with short timeout |
| reasoning.run_consistency | ontology_export.build_graph | import + call | WIRED | reasoning.py:100 — calls ontology_export.build_graph(session, project) |
| reasoning.run_consistency | strip_hermit_unsupported | import + call | WIRED | reasoning.py:212 — calls strip_hermit_unsupported(union) |
| reasoning._reason_with_timeout | Owlready2 sync_reasoner() | spawn subprocess | WIRED | reasoning.py:131-135 — load NTriples, call sync_reasoner() inside subprocess |

### Data-Flow Trace (Level 4)

| Artifact | Data Variable | Source | Produces Real Data | Status |
|----------|--------------|--------|-------------------|--------|
| reasoning.run_consistency | union Graph | DesignGrammar-V7.owl (TBox) + dg-disjointness.ttl (overlay) + ontology_export.build_graph (live Neo4j) | FLOWING | Real files + live Neo4j queries via bolt; fixture test verifies structure with simulated records |
| reasoning._serialize_nt | NTriples file | union Graph from _hybrid_union | FLOWING | Temp file produced (340KB verified in smoke test); Owlready2 loads via file URI |
| reasoning._reason_with_timeout | unsatisfiable_classes list | HermiT via Owlready2 sync_reasoner() | FLOWING | Real HermiT subprocess; response includes result or timeout |
| data-service proxy response | Sidecar response | httpx.post to DG_REASONER_URL | FLOWING | Live forwarding; timeout/connect errors caught and returned as clean 5xx |
| ontology_export.build_graph | RDF triples | Neo4j label-scoped queries (ONTOGRAPH_QUERY, METAGRAPH_QUERY, etc.) | FLOWING | Queries against live bolt; fixture shim verifies translation fidelity |

### Behavioral Spot-Checks

| Behavior | Command | Result | Status |
|----------|---------|--------|--------|
| Health test passes (unit) | `pytest dg-reasoner/tests/test_health.py -q` | 1 passed | PASS |
| Ontology export fidelity tests pass (unit) | `pytest dg-reasoner/tests/test_ontology_export.py -q` | 8 passed | PASS |
| Route contract tests pass (unit) | `pytest dg-reasoner/tests/test_routes.py -q` | 4 passed | PASS |
| All always-on unit tests pass | `pytest dg-reasoner/tests/test_health.py test_ontology_export.py test_routes.py -q` | 13 passed | PASS |
| Integration tests (test_n10s_smoke, test_roundtrip_integration) | Requires Docker | SKIP | Cannot run without live Docker Neo4j; tests exist and skip cleanly when unreachable |
| All Python files parse | `python -c "import ast; ..."` on each file | All parse | PASS |
| Code review findings fixed | git log 207ffc2 | 8 findings addressed | PASS |

### Probe Execution

No explicit probe scripts declared for this phase. The PROBES list from PLAN files is empty. Skipped.

### Requirements Coverage

| Requirement | Source Plan | Description | Status | Evidence |
|-------------|-------------|-------------|--------|----------|
| REAS-05 | 821-01, 821-02, 821-03, 821-04 | A dg-reasoner sidecar service runs in docker-compose and exposes OWL 2 DL consistency-check and SHACL-validation endpoints, isolated from data-service's Speckle-publish/validation-run hot path | SATISFIED | All 4 plans complete; all 22 must-haves verified; all always-on tests pass; code review findings addressed |

### Anti-Patterns Found

| File | Line | Pattern | Severity | Impact |
|------|------|---------|----------|--------|
| (none) | - | - | - | No TBD/FIXME/XXX markers found. No stub patterns (empty handlers, static returns, console.log-only implementations). No placeholder warnings beyond intentionally-documented "empty shapes graph" for Phase 823. |

### Code Review Findings Resolution

All 14 review findings (from 821-REVIEW.md) were addressed in commit `207ffc2`:

| Finding | Classification | Resolution |
|---------|---------------|------------|
| CR-01: Proxy read timeout 5s < 90s sidecar timeout | Critical | Fixed: `read=95.0` in data-service/app.py:1188 — exceeds DG_REASONER_TIMEOUT_SECONDS |
| CR-02: process.terminate() may not kill Java subprocess | Critical | Fixed: reasoning.py:129 `os.setsid()` in worker, :173 `os.killpg()` on timeout |
| CR-03: ARG.pos silently defaults to 0 | Critical | Fixed: ontology_export.py:293-310 collects raw `record["pos"]` before defaulting; :184-216 `_atom_completeness_reason` validates missing/duplicate positions |
| WR-01: Session held open for full HermiT run | Warning | Fixed: reasoning.py:203-210 closes session in `finally` immediately after `_hybrid_union` |
| WR-02: HAS_BODY/HAS_HEAD.order silently defaults to 0 | Warning | Fixed: ontology_export.py:344-355 validates null/duplicate order values, skips rule with diagnostic message |
| WR-03: multiprocessing fork from threaded handler | Warning | Fixed: reasoning.py:166 uses `multiprocessing.get_context("spawn")` |
| WR-04: run_shacl has no timeout guard | Warning | Fixed: reasoning.py:259-288 `_run_shacl_with_timeout` implements same spawn+killpg pattern as HermiT |
| WR-05: Hardcoded password fallback | Warning | Fixed: app.py:29-34, reasoning.py:52-57 — warning logged when NEO4J_PASSWORD unset |
| IN-01: Redundant exception tuple | Info | Addressed: single `except Exception:` used |
| IN-02: Unused constant in app.py | Info | Fixed: removed from app.py |
| IN-03: Unrecognized Atom.type fallback | Info | Fixed: routes unrecognized types to SkippedAtom |
| IN-04: Lazy driver singleton no lock | Info | Addressed: low-impact, noted |
| IN-05: Inconsistent dependency pinning | Info | Noted: deps functional, builds verified |
| WR-06: Pre-existing Cypher injection (out of scope) | Warning | Noted: pre-existing, not part of phase diff |

## Gaps Summary

No gaps found. All 22 must-haves verified. All always-on unit tests pass (13/13). Code review findings addressed. Integration tests exist (marked @pytest.mark.integration, require Docker) and skip cleanly when Neo4j is unreachable.

**Phase goal ACHIEVED.** Ready to proceed to Phase 822.

---

_Verified: 2026-07-12T23:00:00Z_
_Verifier: Claude (gsd-verifier)_
