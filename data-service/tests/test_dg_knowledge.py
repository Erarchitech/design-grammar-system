"""Tests for the SWRL convention block + Computgraph concept catalog
(Phase 29: CTXA-03, and the Computgraph portion of CTXA-01).

Follows the existing test pattern from test_dg_context.py / test_reasoner.py:
FastAPI TestClient boilerplate header, sys.path.insert. TestComputgraphCatalog
(added alongside the Computgraph parser in this same plan) parses the REAL
DesignGrammar-V7.owl file (no synthetic fixture) so parser tests catch
real-file DOCTYPE/entity issues (RESEARCH.md Pitfall 4).
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
