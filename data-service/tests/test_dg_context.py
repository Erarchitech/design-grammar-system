"""Tests for the Cypher expression catalog loader (Phase 29: CTXA-02).

Follows the existing test pattern from test_reasoner.py: FastAPI TestClient
boilerplate header, sys.path.insert, monkeypatch-based file-path isolation
for the negative-path (missing/malformed catalog) cases.
"""

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
import dg_context  # noqa: E402
from app import app  # noqa: E402
from llm_gateway import GenerateResponse  # noqa: E402

client = TestClient(app, raise_server_exceptions=False)


@pytest.fixture
def catalog_path(tmp_path, monkeypatch):
    """Redirect dg_context.CYPHER_CATALOG_FILE to a per-test temp path.

    The real repo-root catalog (llm/cypher_catalog.json) is a read-only
    artifact -- the happy-path tests read it directly with no monkeypatch.
    This fixture is opt-in (not autouse) and only used by the negative-path
    tests below that need to point CYPHER_CATALOG_FILE at a missing or
    malformed file.
    """
    fake_path = tmp_path / "cypher_catalog.json"
    monkeypatch.setattr(dg_context, "CYPHER_CATALOG_FILE", fake_path)
    return fake_path


# ── Real catalog loads and exposes all 6 shapes ──


class TestCypherCatalog:
    def test_real_catalog_exposes_expected_shape_ids(self):
        """load_cypher_catalog() against the real repo file returns all six shapes."""
        catalog = dg_context.load_cypher_catalog()
        assert catalog["version"] == 1
        ids = {shape["id"] for shape in catalog["shapes"]}
        assert ids == dg_context.EXPECTED_SHAPE_IDS

    def test_every_shape_has_required_keys(self):
        """Every shape object carries id/name/description/swrl_pattern/cypher_template/worked_example."""
        required_keys = {
            "id",
            "name",
            "description",
            "swrl_pattern",
            "cypher_template",
            "worked_example",
        }
        catalog = dg_context.load_cypher_catalog()
        for shape in catalog["shapes"]:
            assert required_keys <= set(shape), f"shape {shape.get('id')} missing keys"

    def test_existence_count_var_merge_keys_on_project(self):
        """Pitfall 1 regression guard: existence_count Var MERGE includes project."""
        catalog = dg_context.load_cypher_catalog()
        existence_count = next(s for s in catalog["shapes"] if s["id"] == "existence_count")
        assert "project" in existence_count["cypher_template"]
        assert "project" in existence_count["worked_example"]

    def test_cypher_shape_ids_module_constant_matches_expected(self):
        """CYPHER_SHAPE_IDS (computed at import time) matches EXPECTED_SHAPE_IDS."""
        assert dg_context.CYPHER_SHAPE_IDS == dg_context.EXPECTED_SHAPE_IDS

    def test_missing_catalog_file_degrades_to_empty_catalog(self, catalog_path):
        """load_cypher_catalog() against a non-existent path never raises."""
        # catalog_path fixture points CYPHER_CATALOG_FILE at a tmp_path file
        # that is never created -- exercises the "missing file" branch.
        result = dg_context.load_cypher_catalog()
        assert result == {"version": 0, "shapes": []}

    def test_malformed_catalog_file_degrades_to_empty_catalog(self, catalog_path):
        """load_cypher_catalog() against malformed (non-JSON) content never raises."""
        catalog_path.write_text("{not valid json", encoding="utf-8")
        result = dg_context.load_cypher_catalog()
        assert result == {"version": 0, "shapes": []}

    def test_catalog_file_with_wrong_shape_degrades_to_empty_catalog(self, catalog_path):
        """A parseable JSON file that isn't a {version, shapes:[...]} dict also degrades safely."""
        catalog_path.write_text(json.dumps(["not", "a", "dict"]), encoding="utf-8")
        result = dg_context.load_cypher_catalog()
        assert result == {"version": 0, "shapes": []}


# ── assemble_context() -- deterministic context assembler (Phase 29-03: CTXA-01/04/05) ──


class FixtureSession:
    """Duck-types `neo4j.Session.run(query, **params)` with zero live Neo4j.

    Mirrors the FixtureSession precedent in dg-reasoner/tests/test_ontology_export.py
    (STATE.md Phase 821 Plan 02) -- returns a fixed list of existing-entity rows
    regardless of the query text, just records the last `project` kwarg it was
    called with so tests can assert the bound-parameter contract (T-29-03a).
    """

    def __init__(self, rows: list[dict] | None = None):
        self._rows = rows if rows is not None else []
        self.last_project: str | None = None

    def run(self, query: str, **params):
        self.last_project = params.get("project")
        return list(self._rows)


class TestContextAssemble:
    def _req(self, **kwargs) -> dg_context.ContextAssembleRequest:
        defaults = {"type": "rule_ingest", "project": "TestA", "rules_text": None, "question": None}
        defaults.update(kwargs)
        return dg_context.ContextAssembleRequest(**defaults)

    def test_rule_ingest_max_height_selects_max_limit_shape_and_concepts(self):
        """(a) 'maximum building height 75 m' -> max_limit shape + building-height concepts."""
        req = self._req(type="rule_ingest", rules_text="Maximum building height is 75 meters")
        context = dg_context.assemble_context(req, session=FixtureSession())

        shape_ids = {shape["id"] for shape in context["selected_cypher_shapes"]}
        assert "max_limit" in shape_ids

        serialized = json.dumps(context).lower()
        assert "building" in serialized
        assert "height" in serialized

    def test_graph_query_design_states_surfaces_v4_kind_enum(self):
        """(b) a graph_query about design states contains the three DesignState kinds."""
        req = self._req(
            type="graph_query",
            project="TestA",
            question="What design states exist for this project?",
        )
        context = dg_context.assemble_context(req, session=FixtureSession())

        assert context["validgraph"]["design_state_kinds"] == ["ObjState", "ParamState", "PropState"]
        serialized = json.dumps(context)
        assert "ObjState" in serialized
        assert "ParamState" in serialized
        assert "PropState" in serialized

    def test_rule_edit_contains_rule_id_regenerate_and_preservation_guidance(self):
        """(c) rule_edit context documents Rule_Id-regenerate + MATCH-DELETE + iri/SWRL_label preservation."""
        req = self._req(type="rule_edit", rules_text="Change maximum height to 80m")
        context = dg_context.assemble_context(req, session=FixtureSession())

        guidance = context["edit_guidance"]
        serialized = json.dumps(guidance)
        assert "Rule_Id" in serialized
        assert "MATCH-DELETE" in serialized
        assert "iri" in serialized
        assert "SWRL_label" in serialized

    def test_unknown_type_raises_value_error(self):
        """(d) an unknown `type` raises ValueError (app.py maps this to CONTEXT_TYPE_INVALID)."""
        req = dg_context.ContextAssembleRequest.model_construct(
            type="bogus_type", project="TestA", rules_text=None, question=None
        )
        with pytest.raises(ValueError):
            dg_context.assemble_context(req, session=FixtureSession())

    def test_live_entity_union_uses_injectable_session_and_binds_project(self):
        """The live-entity union runs against an injectable session -- no live Neo4j required."""
        fixture_rows = [
            {"nodeLabel": "Class", "iri": "ex:Building", "label": "Building", "swrl_label": "", "range": ""},
        ]
        session = FixtureSession(rows=fixture_rows)
        req = self._req(type="rule_ingest", project="fixture-proj", rules_text="Maximum height 75")
        context = dg_context.assemble_context(req, session=session)

        assert context["existing_entities"] == fixture_rows
        assert session.last_project == "fixture-proj"

    def test_all_four_layers_and_swrl_conventions_present(self):
        """assemble_context() returns a dict with all four per-layer keys + SWRL + selected shapes."""
        req = self._req(type="rule_ingest", rules_text="Maximum height 75")
        context = dg_context.assemble_context(req, session=FixtureSession())

        for key in ("ontograph", "metagraph", "validgraph", "computgraph", "swrl_conventions", "selected_cypher_shapes"):
            assert key in context


# ── /context/assemble + /context/debug endpoints (Phase 29-03: D-01/D-04) ──


class TestContextEndpoints:
    def test_post_assemble_returns_200_for_valid_type(self):
        response = client.post(
            "/context/assemble",
            json={
                "type": "rule_ingest",
                "project": "phase29-endpoint-test",
                "rules_text": "Maximum building height is 75 meters",
                "question": None,
            },
        )
        assert response.status_code == 200
        body = response.json()
        assert body["type"] == "rule_ingest"
        assert any(shape["id"] == "max_limit" for shape in body["selected_cypher_shapes"])

    def test_post_assemble_unknown_type_returns_structured_422(self):
        response = client.post(
            "/context/assemble",
            json={"type": "bogus_type", "project": "phase29-endpoint-test"},
        )
        assert response.status_code == 422
        detail = response.json()["detail"]
        assert detail["code"] == "CONTEXT_TYPE_INVALID"

    def test_get_debug_matches_post_assemble_body(self):
        params = {
            "type": "rule_ingest",
            "project": "phase29-endpoint-test",
            "rules_text": "Maximum building height is 75 meters",
        }
        post_response = client.post("/context/assemble", json={**params, "question": None})
        get_response = client.get("/context/debug", params=params)

        assert get_response.status_code == 200
        assert get_response.json() == post_response.json()


class TestDeterminism:
    def test_repeated_assemble_calls_are_byte_identical(self):
        """CTXA-05: the same /context/assemble request issued twice yields byte-identical JSON."""
        payload = {
            "type": "rule_ingest",
            "project": "phase29-determinism-test",
            "rules_text": "Maximum building height is 75 meters",
            "question": None,
        }
        first = client.post("/context/assemble", json=payload)
        second = client.post("/context/assemble", json=payload)

        assert first.status_code == 200
        assert second.status_code == 200
        assert json.dumps(first.json(), sort_keys=False) == json.dumps(second.json(), sort_keys=False)

    def test_get_debug_and_post_assemble_are_equal_for_graph_query(self):
        """GET /context/debug and POST /context/assemble share one code path (D-04)."""
        params = {
            "type": "graph_query",
            "project": "phase29-determinism-test",
            "question": "What design states exist for this project?",
        }
        post_response = client.post("/context/assemble", json={**params, "rules_text": None})
        get_response = client.get("/context/debug", params=params)

        assert get_response.status_code == 200
        assert json.dumps(get_response.json(), sort_keys=False) == json.dumps(post_response.json(), sort_keys=False)


# ── VALIDGRAPH_CONCEPTS -- real ValidationRun/statePayloadJson shape ──
#
# Phase 29-06 gap closure: converges the schema description fed to the LLM to
# the REAL shipped shape (app.py store_validation_run()/list_validation_runs()),
# not the aspirational :DesignState/:Run nodes that caused the "no design
# states found" bug (29-UAT.md Success Criterion 4).


class TestValidgraphConceptsRealShape:
    def test_node_labels_describe_validationrun_not_designstate(self):
        """VALIDGRAPH_CONCEPTS.node_labels reflects ValidationRun/ValidationEntity
        (the real shape); DesignState/Run (aspirational, never-materialized nodes)
        are removed."""
        node_labels = dg_context.VALIDGRAPH_CONCEPTS["node_labels"]
        assert "ValidationRun" in node_labels
        assert "ValidationEntity" in node_labels
        assert "DesignState" not in node_labels
        assert "Run" not in node_labels

    def test_design_state_kinds_preserved(self):
        """design_state_kinds still describes the v4 kind enum -- now framed as
        statePayloadJson entry kinds, not node labels (29-03's existing
        assertion this preserves)."""
        assert dg_context.VALIDGRAPH_CONCEPTS["design_state_kinds"] == ["ObjState", "ParamState", "PropState"]


# ── validate_cypher() -- schema + verb-policy validator (Phase 29-04: CTXA-04) ──
#
# CTXA-04 is the phase's PRIMARY security control (T-29-01/T-29-02 mitigation,
# 29-04-PLAN.md threat_model). These tests are the acceptance bar for that
# mitigation -- do not weaken or skip the verb-policy cases.


class TestValidator:
    def test_clean_ingest_cypher_from_real_catalog_validates_true(self):
        """A real, fully-instantiated worked_example (max_limit) validates clean."""
        catalog = dg_context.load_cypher_catalog()
        max_limit = next(s for s in catalog["shapes"] if s["id"] == "max_limit")
        result = dg_context.validate_cypher(max_limit["worked_example"], "rule_ingest")
        assert result == {"valid": True, "violations": []}

    def test_unknown_label_is_caught(self):
        cypher = "MERGE (x:BogusThing {iri: 'ex:Foo'})\nSET x.project = 'p', x.graph = 'OntoGraph'"
        result = dg_context.validate_cypher(cypher, "rule_ingest")
        assert result["valid"] is False
        codes = {v["code"] for v in result["violations"]}
        assert "unknown_label" in codes

    def test_unknown_relationship_is_caught(self):
        cypher = (
            "MERGE (r:Rule {Rule_Id: 'R_X_V'})\n"
            "MERGE (a:Atom {Atom_Id: 'R_X_V_A1'})\n"
            "MERGE (r)-[:BOGUS_REL {`order`: 1}]->(a)"
        )
        result = dg_context.validate_cypher(cypher, "rule_ingest")
        assert result["valid"] is False
        codes = {v["code"] for v in result["violations"]}
        assert "unknown_relationship" in codes

    def test_bad_kind_enum_is_caught(self):
        cypher = (
            "MERGE (ds:DesignState {StateId: 'x', project: 'p'})\n"
            "SET ds.kind = 'Bogus'"
        )
        result = dg_context.validate_cypher(cypher, "rule_ingest")
        assert result["valid"] is False
        codes = {v["code"] for v in result["violations"]}
        assert "bad_kind_enum" in codes

    def test_unbalanced_brackets_is_caught(self):
        cypher = "MERGE (r:Rule {Rule_Id: 'R_X_V'}\nSET r.SWRL = 'test'"
        result = dg_context.validate_cypher(cypher, "rule_ingest")
        assert result["valid"] is False
        codes = {v["code"] for v in result["violations"]}
        assert "unbalanced_brackets" in codes

    def test_rule_keyed_on_id_instead_of_rule_id_is_caught(self):
        cypher = "MERGE (r:Rule {id: 'R_X_V'})\nSET r.SWRL = 'test'"
        result = dg_context.validate_cypher(cypher, "rule_ingest")
        assert result["valid"] is False
        codes = {v["code"] for v in result["violations"]}
        assert "bad_key_name" in codes

    def test_atom_keyed_on_id_instead_of_atom_id_is_caught(self):
        cypher = "MERGE (a1:Atom {id: 'R_X_V_A1'})\nSET a1.type = 'ClassAtom'"
        result = dg_context.validate_cypher(cypher, "rule_ingest")
        assert result["valid"] is False
        codes = {v["code"] for v in result["violations"]}
        assert "bad_key_name" in codes

    def test_datatype_property_label_instead_of_swrl_label_is_caught(self):
        cypher = "MERGE (dp:DatatypeProperty {iri: 'ex:height'})\nSET dp.label = 'height'"
        result = dg_context.validate_cypher(cypher, "rule_ingest")
        assert result["valid"] is False
        codes = {v["code"] for v in result["violations"]}
        assert "bad_key_name" in codes

    def test_var_merge_missing_project_is_caught(self):
        """Pitfall 1 regression guard: existence_count-style Var MERGE without project."""
        cypher = "MERGE (vCount:Var {name: '?count'})\nSET vCount.graph = 'Metagraph'"
        result = dg_context.validate_cypher(cypher, "rule_ingest")
        assert result["valid"] is False
        codes = {v["code"] for v in result["violations"]}
        assert "missing_project_key" in codes

    def test_ingest_detach_delete_is_disallowed_verb(self):
        """T-29-02: ingest/edit may ONLY emit MERGE/SET."""
        cypher = "MERGE (r:Rule {Rule_Id: 'R_X_V'})\nDETACH DELETE r"
        result = dg_context.validate_cypher(cypher, "rule_ingest")
        assert result["valid"] is False
        codes = {v["code"] for v in result["violations"]}
        assert "disallowed_verb" in codes

    def test_edit_detach_delete_is_disallowed_verb(self):
        cypher = "MERGE (r:Rule {Rule_Id: 'R_X_V'})\nDETACH DELETE r"
        result = dg_context.validate_cypher(cypher, "rule_edit")
        assert result["valid"] is False
        codes = {v["code"] for v in result["violations"]}
        assert "disallowed_verb" in codes

    def test_graph_query_write_verbs_are_disallowed(self):
        """T-29-01/T-29-02: graph_query must be fully read-only (is_write_query() precedent)."""
        cypher = "MATCH (r:Rule) SET r.kind = 'x' DELETE r"
        result = dg_context.validate_cypher(cypher, "graph_query")
        assert result["valid"] is False
        codes = {v["code"] for v in result["violations"]}
        assert "disallowed_verb" in codes

    def test_graph_query_read_only_cypher_has_no_disallowed_verb_violation(self):
        cypher = "MATCH (r:Rule {graph: 'Metagraph'}) RETURN r.Rule_Id AS id LIMIT 50"
        result = dg_context.validate_cypher(cypher, "graph_query")
        codes = {v["code"] for v in result["violations"]}
        assert "disallowed_verb" not in codes

    def test_unknown_request_type_raises_value_error(self):
        with pytest.raises(ValueError):
            dg_context.validate_cypher("MERGE (r:Rule {Rule_Id: 'X'})", "bogus_type")

    # ── 29-06 gap closure: ValidationRun/HAS_ENTITY allow-list convergence ──

    def test_validationrun_match_is_allowed_for_graph_query(self):
        """The REAL shipped shape (ValidationRun.statePayloadJson, matching
        app.py's store_validation_run()) validates clean for graph_query."""
        cypher = "MATCH (run:ValidationRun {project:'p'}) RETURN run.statePayloadJson LIMIT 50"
        result = dg_context.validate_cypher(cypher, "graph_query")
        codes = {v["code"] for v in result["violations"]}
        assert "unknown_label" not in codes

    def test_has_entity_relationship_is_allowed_for_graph_query(self):
        """HAS_ENTITY (ValidationRun -> ValidationEntity, app.py store_validation_run())
        is an allowed relationship; ValidationEntity is an allowed label."""
        cypher = "MATCH (run:ValidationRun)-[:HAS_ENTITY]->(ve:ValidationEntity) RETURN ve LIMIT 50"
        result = dg_context.validate_cypher(cypher, "graph_query")
        codes = {v["code"] for v in result["violations"]}
        assert "unknown_label" not in codes
        assert "unknown_relationship" not in codes

    def test_designstate_match_is_rejected_as_unknown_label_for_graph_query(self):
        """Regression guard for THIS gap: a MATCH (:DesignState ...) query --
        the exact aspirational pattern the LLM was generating that silently
        returned zero rows (29-UAT.md Success Criterion 4 root cause) -- must
        now be rejected as unknown_label, turning a silent empty result into
        corrective-feedback retry (CTXA-04, D-08)."""
        cypher = "MATCH (ds:DesignState {project:'p'}) RETURN ds LIMIT 50"
        result = dg_context.validate_cypher(cypher, "graph_query")
        assert result["valid"] is False
        codes = {v["code"] for v in result["violations"]}
        assert "unknown_label" in codes


# ── generate_validated_cypher() -- bounded retry loop (Phase 29-04: D-06/D-07) ──

_VALID_CYPHER = (
    "MERGE (r:Rule {Rule_Id: 'R_TEST_1_V'})\n"
    "SET r.SWRL = 'x', r.project = 'p', r.graph = 'Metagraph'\n"
    "MERGE (v:Var {name: '?b', project: 'p'})\n"
    "SET v.graph = 'Metagraph'"
)

# Invalid for two independent reasons (bad_key_name + disallowed_verb) -- any
# retry-loop test just needs this to fail validate_cypher(), not isolate why.
_INVALID_CYPHER = "MERGE (r:Rule {id: 'R_TEST_1_V'}) DETACH DELETE r"


class _FakeAdapterForRetry:
    """Stand-in for an llm_gateway LLMAdapter -- returns queued response texts
    in order and records every prompt it was called with, so tests can assert
    both the attempt count and that corrective feedback was actually appended
    on retry (per TestReasonerConsistencyProxy's monkeypatch.setattr pattern,
    retargeted from httpx.post to the adapter itself, per RESEARCH.md)."""

    def __init__(self, texts: list[str]):
        self._texts = list(texts)
        self.prompts_seen: list[str] = []
        self.call_count = 0

    def generate(self, req, api_key):
        self.call_count += 1
        self.prompts_seen.append(req.prompt)
        text = self._texts.pop(0)
        return GenerateResponse(text=text, provider="fake", model="fake-model", usage={})


class TestRetryLoop:
    def test_first_attempt_valid_returns_attempts_1_no_retry(self, monkeypatch):
        fake_adapter = _FakeAdapterForRetry([_VALID_CYPHER])
        monkeypatch.setattr(dg_context, "get_adapter", lambda provider, base_url=None: fake_adapter)

        result = dg_context.generate_validated_cypher("write a height rule", "rule_ingest")

        assert result == {"valid": True, "cypher": _VALID_CYPHER, "attempts": 1}
        assert fake_adapter.call_count == 1

    def test_two_failures_then_success_reaches_attempt_3_with_feedback(self, monkeypatch):
        fake_adapter = _FakeAdapterForRetry([_INVALID_CYPHER, _INVALID_CYPHER, _VALID_CYPHER])
        monkeypatch.setattr(dg_context, "get_adapter", lambda provider, base_url=None: fake_adapter)

        result = dg_context.generate_validated_cypher("write a height rule", "rule_ingest")

        assert result["valid"] is True
        assert result["cypher"] == _VALID_CYPHER
        assert result["attempts"] == 3
        assert fake_adapter.call_count == 3
        # The third (final) prompt must carry the appended corrective feedback.
        assert "CORRECTIVE FEEDBACK" in fake_adapter.prompts_seen[2]
        assert "disallowed_verb" in fake_adapter.prompts_seen[2]
        # The very first prompt is the original, unmodified.
        assert fake_adapter.prompts_seen[0] == "write a height rule"

    def test_all_three_attempts_fail_returns_final_violations_bounded_at_3(self, monkeypatch):
        fake_adapter = _FakeAdapterForRetry([_INVALID_CYPHER, _INVALID_CYPHER, _INVALID_CYPHER])
        monkeypatch.setattr(dg_context, "get_adapter", lambda provider, base_url=None: fake_adapter)

        result = dg_context.generate_validated_cypher("write a height rule", "rule_ingest")

        assert result["valid"] is False
        assert result["attempts"] == 3
        assert len(result["violations"]) > 0
        # Bound honored: never more than 3 adapter calls (2 retries + original).
        assert fake_adapter.call_count == 3

    def test_retry_loop_never_calls_llm_generate_http_endpoint(self, monkeypatch):
        """The retry loop must call the adapter in-process -- never re-POST to
        /llm/generate (RESEARCH.md Anti-pattern guard)."""

        def fail_post(*args, **kwargs):
            raise AssertionError("generate_validated_cypher must not re-POST to /llm/generate")

        monkeypatch.setattr(app_module.httpx, "post", fail_post)
        fake_adapter = _FakeAdapterForRetry([_VALID_CYPHER])
        monkeypatch.setattr(dg_context, "get_adapter", lambda provider, base_url=None: fake_adapter)

        result = dg_context.generate_validated_cypher("write a height rule", "rule_ingest")

        assert result["valid"] is True

    def test_unknown_request_type_raises_value_error_without_touching_adapter(self, monkeypatch):
        def unexpected_get_adapter(provider, base_url=None):
            raise AssertionError("must not resolve an adapter for an unknown request type")

        monkeypatch.setattr(dg_context, "get_adapter", unexpected_get_adapter)

        with pytest.raises(ValueError):
            dg_context.generate_validated_cypher("write a rule", "bogus_type")


# ── POST /context/generate-cypher -- the single n8n-facing endpoint ──


class TestGenerateCypherEndpoint:
    def test_endpoint_returns_validated_cypher_for_mocked_valid_adapter(self, monkeypatch):
        fake_adapter = _FakeAdapterForRetry([_VALID_CYPHER])
        monkeypatch.setattr(dg_context, "get_adapter", lambda provider, base_url=None: fake_adapter)

        response = client.post(
            "/context/generate-cypher",
            json={"prompt": "write a height rule", "type": "rule_ingest", "project": "p"},
        )

        assert response.status_code == 200
        body = response.json()
        assert body["valid"] is True
        assert body["cypher"] == _VALID_CYPHER
        assert body["attempts"] == 1

    def test_endpoint_returns_structured_error_on_adapter_failure(self, monkeypatch):
        class _FailingAdapter:
            def generate(self, req, api_key):
                raise RuntimeError("simulated adapter failure")

        monkeypatch.setattr(dg_context, "get_adapter", lambda provider, base_url=None: _FailingAdapter())

        response = client.post(
            "/context/generate-cypher",
            json={"prompt": "write a height rule", "type": "rule_ingest", "project": "p"},
        )

        assert response.status_code == 502
        assert "code" in response.json()["detail"]

    def test_endpoint_unknown_type_returns_structured_422(self):
        response = client.post(
            "/context/generate-cypher",
            json={"prompt": "write a height rule", "type": "bogus_type", "project": "p"},
        )

        assert response.status_code == 422
        assert response.json()["detail"]["code"] == "CONTEXT_TYPE_INVALID"
