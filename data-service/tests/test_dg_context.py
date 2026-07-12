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
