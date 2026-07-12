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
