"""Tests for the SWRL convention block + Computgraph concept catalog
(Phase 29: CTXA-03, and the Computgraph portion of CTXA-01).

Follows the existing test pattern from test_dg_context.py / test_reasoner.py:
FastAPI TestClient boilerplate header, sys.path.insert. TestComputgraphCatalog
parses the REAL DesignGrammar-V7.owl file (no synthetic fixture) so parser
tests catch real-file DOCTYPE/entity issues (RESEARCH.md Pitfall 4).
"""

from __future__ import annotations

import os
import sys

import httpx
import pytest
from fastapi.testclient import TestClient

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

os.environ.setdefault("LLM_MASTER_SECRET", "test-master-secret")

import app as app_module  # noqa: E402
import dg_knowledge  # noqa: E402
from app import app  # noqa: E402

client = TestClient(app, raise_server_exceptions=False)


def _iter_strings(value):
    """Recursively yield every string leaf value in a nested dict/list structure."""
    if isinstance(value, str):
        yield value
    elif isinstance(value, dict):
        for v in value.values():
            yield from _iter_strings(v)
    elif isinstance(value, (list, tuple)):
        for v in value:
            yield from _iter_strings(v)


# ── SWRL convention block (CTXA-03) ──


class TestSwrlConventions:
    def test_swrl_conventions_importable_and_dict(self):
        """dg_knowledge imports without error and SWRL_CONVENTIONS is a dict."""
        assert isinstance(dg_knowledge.SWRL_CONVENTIONS, dict)

    def test_swrl_conventions_accessor_returns_same_object(self):
        """swrl_conventions() is the shared entry point for assembler + tests."""
        assert dg_knowledge.swrl_conventions() is dg_knowledge.SWRL_CONVENTIONS

    def test_encodes_violation_inversion_flag(self):
        conv = dg_knowledge.swrl_conventions()
        assert conv["violation_inversion"]["flag"] is True
        assert "VIOLATED" in conv["violation_inversion"]["statement"]

    def test_encodes_atom_ordering_rule_referencing_order(self):
        conv = dg_knowledge.swrl_conventions()
        ordering = conv["atom_ordering"]
        assert ordering["property"] == "order"
        assert "HAS_BODY" in ordering["relationship_types"]
        assert "HAS_HEAD" in ordering["relationship_types"]
        assert "`order`" in ordering["statement"]

    def test_encodes_arg_rule_referencing_pos(self):
        conv = dg_knowledge.swrl_conventions()
        args = conv["argument_rules"]
        assert args["relationship_type"] == "ARG"
        assert args["property"] == "pos"
        assert "`pos`" in args["statement"]

    def test_encodes_var_merge_rule_referencing_name_and_project(self):
        conv = dg_knowledge.swrl_conventions()
        args = conv["argument_rules"]
        assert set(args["var_merge_keys"]) == {"name", "project"}
        assert "project" in args["var_merge_statement"]

    def test_encodes_naming_quirks(self):
        conv = dg_knowledge.swrl_conventions()
        quirks = conv["naming_quirks"]
        assert "Rule_Id" in quirks
        assert "Atom_Id" in quirks
        assert "SWRL_label" in quirks
        assert set(quirks["reserved_relationship_properties"]) == {"order", "pos"}

    def test_block_is_addressable_data_not_single_prose_blob(self):
        """Each convention must be reachable via its own top-level key."""
        conv = dg_knowledge.swrl_conventions()
        expected_top_level_keys = {
            "violation_inversion",
            "atom_ordering",
            "argument_rules",
            "naming_quirks",
        }
        assert expected_top_level_keys <= set(conv.keys())
        for key in expected_top_level_keys:
            assert isinstance(conv[key], dict)


# ── Computgraph concept catalog (forward-prep, D-14/D-15) ──


class TestComputgraphCatalog:
    @pytest.fixture(autouse=True)
    def reset_cache(self, monkeypatch):
        """Reset the module-level parse-once cache before each test.

        The real cache is intentionally process-lifetime persistent in
        production; tests reset it so each test observes a clean parse
        (except the explicit cache-hit test below, which manages the
        cache state itself).
        """
        monkeypatch.setattr(dg_knowledge, "_COMPUTGRAPH_CACHE", None)

    def test_owl_file_resolves_and_exists(self):
        """COMPUTGRAPH_OWL_FILE resolves to the real, existing V7 OWL file."""
        assert dg_knowledge.COMPUTGRAPH_OWL_FILE.exists()
        assert dg_knowledge.COMPUTGRAPH_OWL_FILE.name == "DesignGrammar-V7.owl"

    def test_parses_without_error(self):
        """Parsing the real file never raises (no ParseError / undefined entity)."""
        catalog = dg_knowledge.load_computgraph_catalog()
        assert isinstance(catalog, dict)

    def test_returns_hub_class(self):
        catalog = dg_knowledge.load_computgraph_catalog()
        hub = catalog["hub"]
        assert hub["local_name"] == "dgc:Computgraph"
        assert hub["label"] == "Computgraph"
        assert hub["comment"]

    def test_returns_all_five_entity_classes(self):
        catalog = dg_knowledge.load_computgraph_catalog()
        entity_classes = catalog["entity_classes"]
        assert set(entity_classes.keys()) == {
            "Algorithm",
            "Procedure",
            "Pattern",
            "Parameter",
            "Interface",
        }
        for name, info in entity_classes.items():
            assert info["label"] == name, f"{name} label mismatch: {info}"
            assert info["iri"].startswith("http://example.org/design-grammar/comp#")

    def test_no_unresolved_dgc_entity_literal_survives(self):
        """Pitfall 4 guard: no returned string contains the unresolved '&dgc;' literal."""
        catalog = dg_knowledge.load_computgraph_catalog()
        for s in _iter_strings(catalog):
            assert "&dgc;" not in s, f"unresolved entity literal found: {s!r}"

    def test_includes_relations_and_enum_values(self):
        catalog = dg_knowledge.load_computgraph_catalog()
        assert len(catalog["relations"]) > 0
        assert len(catalog["enum_values"]) > 0
        relation_local_names = {r["local_name"] for r in catalog["relations"]}
        assert "dgc:hasAlgorithm" in relation_local_names
        assert "dgc:hasParameter" in relation_local_names

    def test_includes_annotation_convention_grammar(self):
        catalog = dg_knowledge.load_computgraph_catalog()
        convention = catalog["annotation_convention"]
        assert "patterns" in convention
        kinds = {p["kind"] for p in convention["patterns"]}
        assert {
            "Algorithm",
            "Procedure",
            "Pattern",
            "VariableParam",
            "ConstantParam",
            "EmergentParam",
            "Interface",
        } <= kinds

    def test_includes_source_provenance(self):
        catalog = dg_knowledge.load_computgraph_catalog()
        assert catalog["source_iri"] == "http://example.org/design-grammar/comp#Computgraph"
        assert catalog["source_file"].endswith("DesignGrammar-V7.owl")

    def test_second_call_does_not_reparse(self, monkeypatch):
        """A second load_computgraph_catalog() call hits the cache, no re-parse."""
        # reset_cache autouse fixture already cleared the cache for this test.
        parse_calls = {"count": 0}
        original_parse = dg_knowledge.ET.parse

        def counting_parse(*args, **kwargs):
            parse_calls["count"] += 1
            return original_parse(*args, **kwargs)

        monkeypatch.setattr(dg_knowledge.ET, "parse", counting_parse)

        first = dg_knowledge.load_computgraph_catalog()
        second = dg_knowledge.load_computgraph_catalog()

        assert parse_calls["count"] == 1
        assert first is second


# ── Phase 1205 plan 10: folder ingest never reads hidden repository paths ──


class TestIngestFolderHiddenPaths:
    """T-1205-10-05: the mounted repository holds `.secrets/`, `.env*`, `.git/`
    and `.claude/`; an admin-triggered folder ingest must skip any markdown
    file below a dot-prefixed path segment and say why."""

    def _seed(self, tmp_path):
        (tmp_path / "notes").mkdir()
        (tmp_path / "notes" / "public.md").write_text("# Public\nbody", encoding="utf-8")
        (tmp_path / "notes" / ".secrets").mkdir()
        (tmp_path / "notes" / ".secrets" / "leak.md").write_text("# Leak\nkey", encoding="utf-8")
        (tmp_path / ".secrets").mkdir()
        (tmp_path / ".secrets" / "root-leak.md").write_text("# Leak2\nkey", encoding="utf-8")

    def _patch(self, monkeypatch, tmp_path):
        writes: list[dict] = []
        monkeypatch.setattr(app_module, "KNOWLEDGE_REPO_ROOT", tmp_path)
        monkeypatch.setattr(
            app_module, "write_query", lambda q, p=None: writes.append(p or {})
        )
        return writes

    def test_hidden_segment_files_are_skipped_and_reported(self, tmp_path, monkeypatch):
        self._seed(tmp_path)
        writes = self._patch(monkeypatch, tmp_path)

        response = client.post(
            "/knowledge/ingest/folder", json={"project": "P1", "path": "notes"}
        )

        assert response.status_code == 200
        body = response.json()
        assert body["inserted"] == 1
        assert body["skippedHidden"] == 1
        assert body["skipped"] >= 1
        assert body["skippedFiles"] == [
            {"path": "notes/.secrets/leak.md", "reason": "hidden-path"}
        ]
        assert all("leak" not in str(p.get("source", "")) for p in writes)
        assert not any(p.get("content") and "key" in p["content"] for p in writes)

    def test_requesting_a_hidden_folder_directly_is_refused_too(self, tmp_path, monkeypatch):
        self._seed(tmp_path)
        writes = self._patch(monkeypatch, tmp_path)

        response = client.post(
            "/knowledge/ingest/folder", json={"project": "P1", "path": ".secrets"}
        )

        assert response.status_code == 200
        assert response.json()["inserted"] == 0
        assert response.json()["skippedHidden"] == 1
        assert writes == []

    @pytest.mark.dg_principal("none")
    def test_ingest_requires_an_admin(self, tmp_path, monkeypatch):
        self._seed(tmp_path)
        self._patch(monkeypatch, tmp_path)
        assert (
            client.post(
                "/knowledge/ingest/folder", json={"project": "P1", "path": "notes"}
            ).status_code
            == 401
        )
