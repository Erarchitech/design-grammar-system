"""Tests for the graph_query project-scope validator (Phase 1205-06: ALGN12-17).

Follows the existing test pattern from test_dg_context.py: sys.path insert
for the data-service package, an LLM_MASTER_SECRET env default, and a
recording fake adapter for generate_validated_cypher's retry loop. No
FastAPI TestClient is needed here -- wiring these checks into the actual
routes (/context/generate-cypher, /mcp) happens in 1205-14, out of this
plan's scope.
"""

from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

os.environ.setdefault("LLM_MASTER_SECRET", "test-master-secret")

import dg_context  # noqa: E402
from llm_gateway import GenerateResponse  # noqa: E402


def _codes(violations: list[dict]) -> set[str]:
    return {v["code"] for v in violations}


# ── check_query_project_scope() -- valid (no violations) ───────────────────


class TestScopeValidatorValid:
    def test_project_scoped_chain_has_no_violations(self):
        cypher = (
            "MATCH (r:Rule {project: $project})-[:HAS_BODY]->"
            "(a:Atom {project: $project}) RETURN r.Rule_Id, a.Atom_Id LIMIT 50"
        )
        assert dg_context.check_query_project_scope(cypher) == []

    def test_shared_vocabulary_exempt_and_anonymous_node_carries_map(self):
        cypher = (
            "MATCH (r:Rule {project: $project})-[:HAS_BODY]->"
            "(:Atom {project: $project})-[:REFERS_TO]->(c:Class) "
            "RETURN r.Rule_Id, c.label"
        )
        assert dg_context.check_query_project_scope(cypher) == []

    def test_unlabeled_variable_with_inline_map_is_valid(self):
        cypher = "MATCH (n {project: $project}) RETURN n"
        assert dg_context.check_query_project_scope(cypher) == []


# ── missing_project_scope ───────────────────────────────────────────────────


class TestScopeValidatorMissingProjectScope:
    def test_where_predicate_bypass_does_not_count_as_scope(self):
        """A WHERE predicate can be widened with OR -- only an inline map counts."""
        cypher = "MATCH (r:Rule) WHERE r.project = $project OR true RETURN r"
        result = dg_context.check_query_project_scope(cypher)
        assert "missing_project_scope" in _codes(result)

    def test_second_variable_unscoped(self):
        cypher = (
            "MATCH (r:Rule {project: $project}) MATCH (x:Rule) RETURN x.text"
        )
        result = dg_context.check_query_project_scope(cypher)
        violations = [v for v in result if v["code"] == "missing_project_scope"]
        assert any(v["path"] == "x" for v in violations)
        assert not any(v["path"] == "r" for v in violations)

    def test_no_project_token_at_all(self):
        cypher = "MATCH (c:Class) RETURN c.label"
        result = dg_context.check_query_project_scope(cypher)
        assert any(v["code"] == "missing_project_scope" and v["path"] == "query" for v in result)

    def test_unlabeled_variable_scoped_only_via_where_label_is_missing_scope(self):
        cypher = "MATCH (n) WHERE n:Rule RETURN n"
        result = dg_context.check_query_project_scope(cypher)
        assert "missing_project_scope" in _codes(result)


# ── anonymous_node_pattern ───────────────────────────────────────────────────


class TestScopeValidatorAnonymousNodePattern:
    def test_anonymous_relationship_target_without_map(self):
        cypher = "MATCH (r:Rule {project: $project})-[:HAS_BODY]->() RETURN r"
        result = dg_context.check_query_project_scope(cypher)
        assert "anonymous_node_pattern" in _codes(result)
        assert "missing_project_scope" not in _codes(result)

    def test_anonymous_labeled_node_without_map(self):
        cypher = "MATCH (:Atom) RETURN count(*)"
        result = dg_context.check_query_project_scope(cypher)
        assert "anonymous_node_pattern" in _codes(result)


# ── project_literal ──────────────────────────────────────────────────────────


class TestScopeValidatorProjectLiteral:
    def test_inline_map_literal_is_project_literal(self):
        cypher = "MATCH (r:Rule {project: 'P2'}) RETURN r"
        result = dg_context.check_query_project_scope(cypher)
        assert "project_literal" in _codes(result)

    def test_dot_comparison_literal_is_project_literal(self):
        cypher = (
            "MATCH (r:Rule {project: $project}) WHERE r.project = \"P2\" "
            "RETURN r.Rule_Id LIMIT 50"
        )
        result = dg_context.check_query_project_scope(cypher)
        assert "project_literal" in _codes(result)


# ── forbidden_clause ──────────────────────────────────────────────────────────


class TestScopeValidatorForbiddenClause:
    def test_call_db_labels_is_forbidden(self):
        cypher = "CALL db.labels() YIELD label RETURN label"
        result = dg_context.check_query_project_scope(cypher)
        assert "forbidden_clause" in _codes(result)

    def test_union_is_forbidden(self):
        cypher = (
            "MATCH (r:Rule {project: $project}) RETURN r.Rule_Id "
            "UNION MATCH (a:Atom {project: $project}) RETURN a.Atom_Id"
        )
        result = dg_context.check_query_project_scope(cypher)
        assert "forbidden_clause" in _codes(result)

    def test_load_csv_is_forbidden(self):
        cypher = "LOAD CSV FROM 'file:///x.csv' AS row RETURN row"
        result = dg_context.check_query_project_scope(cypher)
        assert "forbidden_clause" in _codes(result)

    def test_foreach_is_forbidden(self):
        cypher = (
            "MATCH (r:Rule {project: $project}) "
            "FOREACH (x IN [1] | SET r.flag = true) RETURN r"
        )
        result = dg_context.check_query_project_scope(cypher)
        assert "forbidden_clause" in _codes(result)

    def test_use_is_forbidden(self):
        cypher = "USE neo4j MATCH (r:Rule {project: $project}) RETURN r.Rule_Id"
        result = dg_context.check_query_project_scope(cypher)
        assert "forbidden_clause" in _codes(result)

    def test_apoc_cypher_run_is_forbidden(self):
        cypher = (
            "MATCH (r:Rule {project: $project}) "
            "CALL apoc.cypher.run('RETURN 1', {}) YIELD value RETURN value"
        )
        result = dg_context.check_query_project_scope(cypher)
        assert "forbidden_clause" in _codes(result)

    def test_forbidden_keyword_inside_quoted_literal_is_not_flagged(self):
        cypher = (
            "MATCH (r:Rule {project: $project, SWRL: 'A UNION B'}) "
            "RETURN r.Rule_Id"
        )
        result = dg_context.check_query_project_scope(cypher)
        assert "forbidden_clause" not in _codes(result)


# ── function-call parentheses never create a false violation ───────────────


class TestScopeValidatorFunctionCallsSafe:
    def test_count_function_call_on_already_scoped_variable(self):
        cypher = "MATCH (r:Rule {project: $project}) RETURN count(r) AS c"
        assert dg_context.check_query_project_scope(cypher) == []

    def test_collect_distinct_on_already_scoped_variable(self):
        cypher = "MATCH (r:Rule {project: $project}) RETURN collect(DISTINCT r) AS rs"
        assert dg_context.check_query_project_scope(cypher) == []

    def test_tolower_property_access_on_already_scoped_variable(self):
        cypher = "MATCH (r:Rule {project: $project}) RETURN toLower(r.name) AS n"
        assert dg_context.check_query_project_scope(cypher) == []


# ── validate_cypher() -- backward compatibility + project wiring ───────────


class TestValidateCypherGraphQueryProjectWiring:
    def test_without_project_matches_todays_behavior(self):
        """An unscoped query that WOULD fail the new checks must still pass
        when no project is supplied -- byte-identical to pre-1205-06."""
        cypher = "MATCH (r:Rule {graph: 'Metagraph'}) RETURN r.Rule_Id AS id LIMIT 50"
        result = dg_context.validate_cypher(cypher, "graph_query")
        assert result["valid"] is True
        assert result["violations"] == []

    def test_with_project_appends_scope_violations(self):
        cypher = "MATCH (r:Rule {graph: 'Metagraph'}) RETURN r.Rule_Id AS id LIMIT 50"
        result = dg_context.validate_cypher(cypher, "graph_query", project="p")
        assert result["valid"] is False
        assert "missing_project_scope" in _codes(result["violations"])


# ── generate_validated_cypher() -- project passed through every attempt ────


class _FakeAdapterForScopeRetry:
    """Records every prompt it was called with; returns queued texts in
    order (test_dg_context.py's _FakeAdapterForRetry precedent, retargeted
    for the project-scope retry scenario)."""

    def __init__(self, texts: list[str]):
        self._texts = list(texts)
        self.prompts_seen: list[str] = []
        self.call_count = 0

    def generate(self, req, api_key):
        self.call_count += 1
        self.prompts_seen.append(req.prompt)
        text = self._texts.pop(0)
        return GenerateResponse(text=text, provider="fake", model="fake-model", usage={})


class TestGenerateValidatedCypherProjectWiring:
    def test_project_passed_through_every_attempt_and_feedback_names_violation(self, monkeypatch):
        unscoped = "MATCH (r:Rule) RETURN r.Rule_Id LIMIT 50"
        scoped = "MATCH (r:Rule {project: $project}) RETURN r.Rule_Id LIMIT 50"
        fake_adapter = _FakeAdapterForScopeRetry([unscoped, scoped])
        monkeypatch.setattr(dg_context, "get_adapter", lambda provider, base_url=None: fake_adapter)

        result = dg_context.generate_validated_cypher(
            "find all rules", "graph_query", project="p"
        )

        assert result["valid"] is True
        assert result["cypher"] == scoped
        assert result["attempts"] == 2
        assert fake_adapter.call_count == 2
        assert "missing_project_scope" in fake_adapter.prompts_seen[1]

    def test_without_project_scope_violations_never_surface(self, monkeypatch):
        unscoped = "MATCH (r:Rule) RETURN r.Rule_Id LIMIT 50"
        fake_adapter = _FakeAdapterForScopeRetry([unscoped])
        monkeypatch.setattr(dg_context, "get_adapter", lambda provider, base_url=None: fake_adapter)

        result = dg_context.generate_validated_cypher("find all rules", "graph_query")

        assert result["valid"] is True
        assert result["attempts"] == 1
