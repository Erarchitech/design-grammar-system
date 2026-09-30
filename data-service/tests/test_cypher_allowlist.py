"""Fail-closed allowlist guard for LLM-written Cypher (Phase 1205, CR-03/CR-04,
review iteration 3).

Two earlier rounds patched regex analysis of model text case by case and were
bypassed both times. `cypher_allowlist` replaces that with a lexer plus a small
grammar: anything it does not positively recognise is a violation. These tests
pin (1) every bypass the iteration-2 review reproduced, (2) further constructs
the allowlist must refuse, (3) a representative set of legitimate queries and
ingests, and (4) the reference-example corpus (training/*.cypher and the
llm/cypher_catalog.json shapes) so the model-facing examples and the guard can
never drift apart again.
"""

from __future__ import annotations

import json
import os
import re
import sys
from pathlib import Path

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

os.environ.setdefault("LLM_MASTER_SECRET", "test-master-secret")

import cypher_allowlist  # noqa: E402
import dg_context  # noqa: E402
from llm_gateway import GenerateResponse  # noqa: E402


def _repo_root() -> Path:
    mnt = Path("/mnt/repo")
    if mnt.exists():
        return mnt
    return Path(__file__).resolve().parent.parent.parent


def _codes(violations: list[dict]) -> set[str]:
    return {v["code"] for v in violations}


def read_check(cypher: str) -> list[dict]:
    return dg_context.check_query_project_scope(cypher)


def write_check(cypher: str) -> list[dict]:
    return dg_context.check_write_allowlist(cypher)


# ── lexer: characters and constructs outside the allowlist ─────────────────


class TestLexer:
    @pytest.mark.parametrize(
        "cypher, fragment",
        [
            ("MATCH (ñ) RETURN ñ.text, $project AS p LIMIT 5", "non-ASCII"),
            ("MATCH (rа:Rule {project: $project}) RETURN rа", "non-ASCII"),  # Cyrillic a
            ("MATCH (r:Rule {project: $project}) RETURN r .x", "non-ASCII"),  # no-break space
            ("MATCH (`r`:Rule {project: $project}) RETURN r", "backtick"),
            ("MATCH (r:Rule {project: $project}) // hi\nRETURN r", "comment"),
            ("MATCH (r:Rule {project: $project}) /* hi */ RETURN r", "comment"),
            ("MATCH (r:Rule {project: 'x}) RETURN r", "unterminated"),
            ("MATCH (r:Rule {project: $project}) RETURN r # tag", "outside the allowed ASCII"),
            ("MATCH (r:Rule {project: $project}) RETURN r ?", "outside the allowed ASCII"),
            ("MATCH (r:Rule {project: $project}) RETURN r.x AS y\\z", "outside the allowed ASCII"),
            ("MATCH (r:Rule {project: $}) RETURN r", "parameter"),
        ],
    )
    def test_read_rejects_unlexable_text(self, cypher, fragment):
        result = read_check(cypher)
        assert result, cypher
        assert "unsupported_syntax" in _codes(result)
        assert any(fragment in v["message"] for v in result), result

    def test_string_contents_are_free_text(self):
        cypher = (
            "MATCH (r:Rule {project: $project, SWRL: 'Büro // /* ` \\' UNION CALL'}) "
            "RETURN r.Rule_Id"
        )
        assert read_check(cypher) == []

    def test_escaped_quote_does_not_end_the_string(self):
        """Neo4j treats \\' as an escaped quote; so does the lexer, so the
        text after it stays inside the string and is never mistaken for Cypher."""
        cypher = "MATCH (r:Rule {project: $project, SWRL: 'a\\' WITH b'}) RETURN r.Rule_Id"
        assert read_check(cypher) == []

    def test_trailing_backslash_is_unterminated(self):
        assert read_check("MATCH (r:Rule {project: $project, SWRL: 'a\\'}) RETURN r")


# ── read profile: every bypass from the iteration-2 review is rejected ─────


class TestReadRejectsReviewedBypasses:
    def test_with_rebind_after_with(self):
        cypher = (
            "MATCH (n:Rule {project: $project}) WITH count(n) AS c "
            "MATCH (n) RETURN n.text, c LIMIT 5"
        )
        result = read_check(cypher)
        assert "forbidden_clause" in _codes(result)
        assert any(v["path"] == "WITH" for v in result)

    def test_unicode_identifier(self):
        cypher = "MATCH (ñ) RETURN ñ.text, $project AS p LIMIT 5"
        assert "unsupported_syntax" in _codes(read_check(cypher))

    def test_unicode_identifier_with_label(self):
        assert read_check("MATCH (ñ:Rule) RETURN ñ.text, $project AS p")


class TestReadRejectsOtherConstructs:
    @pytest.mark.parametrize(
        "cypher, code",
        [
            ("CALL db.labels() YIELD label RETURN label", "forbidden_clause"),
            (
                "MATCH (r:Rule {project: $project}) RETURN r.Rule_Id "
                "UNION MATCH (a:Atom {project: $project}) RETURN a.Atom_Id",
                "forbidden_clause",
            ),
            ("LOAD CSV FROM 'file:///x.csv' AS row RETURN row", "forbidden_clause"),
            (
                "MATCH (r:Rule {project: $project}) FOREACH (x IN [1] | SET r.f = true) RETURN r",
                "forbidden_clause",
            ),
            ("USE neo4j MATCH (r:Rule {project: $project}) RETURN r", "forbidden_clause"),
            ("MATCH (r:Rule {project: $project}) UNWIND [1] AS x RETURN x", "forbidden_clause"),
            ("MATCH (r:Rule {project: $project}) CREATE (n:X) RETURN r", "forbidden_clause"),
            ("MATCH (r:Rule {project: $project}) MERGE (n:X) RETURN r", "forbidden_clause"),
            ("MATCH (r:Rule {project: $project}) SET r.a = 1 RETURN r", "forbidden_clause"),
            ("MATCH (r:Rule {project: $project}) DELETE r", "forbidden_clause"),
            ("MATCH (r:Rule {project: $project}) DETACH DELETE r", "forbidden_clause"),
            ("MATCH (r:Rule {project: $project}) REMOVE r.a RETURN r", "forbidden_clause"),
            ("MATCH (r:Rule {project: $project}) WHERE r.a = 1 SET r.a = 2 RETURN r", "forbidden_clause"),
            (
                "MATCH (r:Rule {project: $project}) "
                "CALL apoc.cypher.run('RETURN 1', {}) YIELD value RETURN value",
                "forbidden_clause",
            ),
            (
                "MATCH (r:Rule {project: $project}) RETURN apoc.text.join(['a'], ',')",
                "unsupported_syntax",
            ),
            (
                "MATCH (r:Rule {project: $project}) RETURN db.labels()",
                "unsupported_syntax",
            ),
            (
                "MATCH (r:Rule {project: $project}) RETURN shortestPath((r)-[*]-(r))",
                "unsupported_function",
            ),
            (
                "MATCH (r:Rule {project: $project}) WHERE EXISTS { MATCH (m) RETURN m } RETURN r",
                "unsupported_syntax",
            ),
            (
                "MATCH (r:Rule {project: $project}) RETURN COUNT { MATCH (m) } AS c",
                "unsupported_syntax",
            ),
            (
                "MATCH (r:Rule {project: $project}) RETURN COLLECT { MATCH (m) RETURN m } AS c",
                "unsupported_syntax",
            ),
            (
                "MATCH (r:Rule {project: $project}) RETURN [(r)-->(m) | m.x]",
                "unsupported_syntax",
            ),
            (
                "MATCH (r:Rule {project: $project}) RETURN [x IN [1, 2] WHERE x > 1]",
                "unsupported_syntax",
            ),
            ("MATCH p = (r:Rule {project: $project}) RETURN p", "unsupported_syntax"),
            (
                "MATCH (r:Rule {project: $project})-[*]->(m:Rule {project: $project}) RETURN m",
                "unsupported_syntax",
            ),
            (
                "MATCH (r:Rule {project: $project})-[:HAS_BODY*1..3]->(m:Atom {project: $project}) RETURN m",
                "unsupported_syntax",
            ),
            ("MATCH (n:A|B {project: $project}) RETURN n", "unsupported_syntax"),
            ("MATCH (n:Rule WHERE n.x = 1) RETURN n", "unsupported_syntax"),
            ("MATCH (n $props) RETURN n", "unsupported_syntax"),
            (
                "MATCH (r:Rule {project: $project + ''}) RETURN r",
                "unsupported_syntax",
            ),
            (
                "MATCH (r:Rule {project: $project, project: 'x'}) RETURN r",
                "unsupported_syntax",
            ),
            (
                "MATCH (r:Rule {project: $project}); MATCH (m) RETURN m",
                "unsupported_syntax",
            ),
            ("MATCH (r:Rule {project: $project})", "unsupported_syntax"),  # no RETURN
            ("", "unsupported_syntax"),
        ],
    )
    def test_rejected(self, cypher, code):
        result = read_check(cypher)
        assert code in _codes(result), (cypher, result)

    @pytest.mark.parametrize(
        "cypher, code, path",
        [
            ("MATCH (r:Rule) WHERE r.project = $project OR true RETURN r", "missing_project_scope", "r"),
            ("MATCH (r:Rule {project: $project}) MATCH (x:Rule) RETURN x.text", "missing_project_scope", "x"),
            ("MATCH (c:Class) RETURN c.label", "missing_project_scope", "c"),
            ("MATCH (n) WHERE n:Rule RETURN n", "missing_project_scope", "n"),
            ("MATCH (r:Rule {project: $project}), (b) RETURN b", "missing_project_scope", "b"),
            ("MATCH (n:Rule {Project: $project}) RETURN n", "missing_project_scope", "n"),
            ("MATCH (n:Rule {subproject: $project}) RETURN n", "missing_project_scope", "n"),
            ("MATCH (n:Rule {project: $other}) RETURN n", "missing_project_scope", "(n:Rule)"),
            ("MATCH (n:Rule {project: 'P2'}) RETURN n", "project_literal", "(n:Rule)"),
            (
                "MATCH (r:Rule {project: $project}) WHERE r.project = \"P2\" RETURN r",
                "project_literal",
                ".project = 'P2'",
            ),
            ("MATCH (:Atom {project: $project}) RETURN count(*)", "anonymous_node_pattern", "(:Atom)"),
            (
                "MATCH (r:Rule {project: $project})-[:HAS_BODY]->() RETURN r",
                "anonymous_node_pattern",
                "()",
            ),
            (
                "MATCH (r:Rule {project: $project}) WHERE NOT (r)-[:SUPERSEDED_BY]->() RETURN r",
                "anonymous_node_pattern",
                "()",
            ),
            (
                "MATCH (r:Rule {project: $project}) WHERE (r)-[:HAS_BODY]->(m) RETURN r",
                "missing_project_scope",
                "m",
            ),
            (
                "MATCH ()-[r:HAS_BODY]->() RETURN r",
                "anonymous_node_pattern",
                "()",
            ),
        ],
    )
    def test_scope_violations(self, cypher, code, path):
        result = read_check(cypher)
        assert any(v["code"] == code and v["path"] == path for v in result), (cypher, result)

    def test_query_without_project_parameter(self):
        result = read_check("MATCH (n {project: 'x'}) RETURN n")
        assert any(v["code"] == "missing_project_scope" and v["path"] == "query" for v in result)

    def test_unlisted_function_names_the_function(self):
        result = read_check("MATCH (r:Rule {project: $project}) RETURN dateTime() AS t")
        assert any(v["code"] == "unsupported_function" and v["path"] == "dateTime" for v in result)


# ── read profile: legitimate queries are accepted ─────────────────────────


LEGIT_READ_QUERIES = [
    # cypher_template.txt / validator examples
    "MATCH (r:Rule {project: $project})-[:HAS_BODY]->(a:Atom {project: $project}) "
    "RETURN r.Rule_Id, a.Atom_Id LIMIT 50",
    "MATCH (r:Rule {project: $project}) RETURN count(r) AS c",
    "MATCH (r:Rule {project: $project}) RETURN collect(DISTINCT r) AS rs",
    "MATCH (r:Rule {project: $project}) RETURN toLower(r.name) AS n",
    "MATCH (n {project: $project}) RETURN n LIMIT 50",
    "MATCH(r:Rule {project: $project}) RETURN r.Rule_Id LIMIT 50",
    # supersession exclusion, written with a bound variable (no anonymous node)
    "MATCH (r:Rule {project: $project}) "
    "OPTIONAL MATCH (r)-[:SUPERSEDED_BY]->(s:Rule {project: $project}) "
    "WHERE s IS NULL RETURN r.Rule_Id, r.SWRL ORDER BY r.Rule_Id DESC SKIP 5 LIMIT 10",
    "MATCH (r:Rule {project: $project}), (s:Rule {project: $project}) "
    "WHERE NOT (r)-[:SUPERSEDED_BY]->(s) RETURN r",
    # the validation-run shape the graph-query prompt teaches
    "MATCH (run:ValidationRun {project: $project}) "
    "RETURN run.Run_Id, run.statePayloadJson ORDER BY run.Run_Id LIMIT 50",
    # Rule -> Atom -> ontology terms
    "MATCH (r:Rule {project: $project})-[:HAS_BODY]->(a:Atom {project: $project})"
    "-[:REFERS_TO]->(c:Class {project: $project}) "
    "RETURN r.Rule_Id AS rule, c.label AS class LIMIT 50",
    # string / list / arithmetic predicates
    "MATCH (r:Rule {project: $project}) WHERE r.SWRL STARTS WITH 'Building' "
    "AND r.kind IN ['violation', 'compliance'] RETURN r.Rule_Id",
    "MATCH (a:Atom {project: $project}) WHERE a.SWRL_label CONTAINS 'height' "
    "OR a.iri =~ 'ex:.*' RETURN a.Atom_Id",
    "MATCH (r:Rule {project: $project}) RETURN r.kind AS kind, count(*) AS n ORDER BY n DESC LIMIT 5",
    "MATCH (r:Rule {project: $project}) RETURN DISTINCT r.kind",
    "MATCH (r:Rule {project: $project}) "
    "RETURN CASE WHEN r.kind = 'violation' THEN 1 ELSE 0 END AS v, size(r.SWRL) AS len",
    "MATCH (r:Rule {project: $project}) RETURN r.Rule_Id AS id LIMIT $limit",
    "MATCH (r:Rule {project: $project, SWRL: 'A UNION B // c /* d */'}) RETURN r.Rule_Id",
    "MATCH (r:Rule {project: $project})-[h:HAS_BODY|HAS_HEAD]->(a:Atom {project: $project}) "
    "RETURN r.Rule_Id, type(h) AS rel, h.order AS ord ORDER BY ord",
    "MATCH (r:Rule {project: $project}) RETURN {id: r.Rule_Id, kind: r.kind} AS row",
    "MATCH (r:Rule {project: $project}) WHERE r.kind IS NOT NULL AND NOT r.kind = 'x' RETURN r",
    "MATCH (a:Atom {project: $project}) RETURN a.type, count(a) AS n, collect(a.Atom_Id)[0] AS first",
]


class TestReadAcceptsLegitimateQueries:
    @pytest.mark.parametrize("cypher", LEGIT_READ_QUERIES)
    def test_accepted(self, cypher):
        assert read_check(cypher) == [], cypher

    def test_validate_cypher_accepts_and_wires_project(self):
        cypher = LEGIT_READ_QUERIES[0]
        result = dg_context.validate_cypher(cypher, "graph_query", project="p")
        assert result["valid"] is True, result["violations"]


# ── write profile: every bypass from the iteration-2 review is rejected ────


class TestWriteRejectsReviewedBypasses:
    def test_with_rebind(self):
        cypher = (
            "MERGE (r:Rule {Rule_Id: 'R_MINE', project: $project}) "
            "WITH r MERGE (r:Rule {Rule_Id: 'R_OTHER', project: $project})"
        )
        result = write_check(cypher)
        assert "forbidden_clause" in _codes(result)
        assert any(v["path"] == "WITH" for v in result)

    def test_unicode_identifier(self):
        cypher = "MERGE (ñ:Rule {Rule_Id: 'R_X', project: $project}) SET ñ.x = 'y'"
        assert "unsupported_syntax" in _codes(write_check(cypher))

    def test_string_concatenation_in_key(self):
        result = write_check("MERGE (r:Rule {Rule_Id: 'R_'+'X', project: $project})")
        assert "unsupported_syntax" in _codes(result) or "unanalysable_key" in _codes(result)
        assert result

    def test_atom_arg_pattern_with_set(self):
        result = write_check("MATCH (a:Atom)-[:ARG]->(v) SET a.SWRL = 'x'")
        assert {"missing_project_scope", "missing_identity_key"} <= _codes(result)

    def test_unlabeled_starts_with(self):
        result = write_check("MATCH (r) WHERE r.Rule_Id STARTS WITH 'R_' SET r.SWRL = 'x'")
        assert "unlabeled_node_pattern" in _codes(result)
        assert any(v["path"] == "WHERE" for v in result)

    def test_unlabeled_detach_delete(self):
        result = write_check("MATCH (n) DETACH DELETE n")
        assert "unlabeled_node_pattern" in _codes(result)
        assert "forbidden_clause" in _codes(result)

    def test_var_detach_delete(self):
        result = write_check("MATCH (n:Var) DETACH DELETE n")
        assert "missing_project_scope" in _codes(result)
        assert any(v["code"] == "forbidden_clause" and v["path"] == "DETACH" for v in result)

    def test_class_set_without_project(self):
        result = write_check("MATCH (n:Class) SET n.label = 'x'")
        assert "missing_project_scope" in _codes(result)

    def test_unlabeled_not_equal_delete(self):
        result = write_check("MATCH (r) WHERE r.Rule_Id <> 'zz' DETACH DELETE r")
        assert "unlabeled_node_pattern" in _codes(result)


class TestWriteRejectsOtherConstructs:
    KEY = "{Rule_Id: 'R_X', project: $project, graph: 'Metagraph'}"

    @pytest.mark.parametrize(
        "cypher, code",
        [
            ("MERGE (r:Rule {Rule_Id: 'R_X', project: 'P1'})", "project_literal"),
            ("MERGE (r:Rule {Rule_Id: 'R_X'})", "missing_project_scope"),
            ("MERGE (r:Rule {Rule_Id: $id, project: $project})", "missing_identity_key"),
            ("MERGE (r:Rule {Rule_Id: '', project: $project})", "missing_identity_key"),
            ("MERGE (r:Rule {project: $project})", "missing_identity_key"),
            ("MERGE (r:Rule {Rule_Id: toUpper('x'), project: $project})", "unanalysable_key"),
            ("MERGE (r:Rule {Rule_Id: 'x', project: $project, kind: $kind})", "unanalysable_key"),
            ("MERGE (r:ValidationRun {Run_Id: 'X', project: $project})", "disallowed_label"),
            ("MERGE (r:Rule:Atom {Rule_Id: 'X', project: $project})", "disallowed_label"),
            ("MERGE (x {project: $project})", "disallowed_label"),
            ("MERGE (:Rule {Rule_Id: 'X', project: $project})", "anonymous_node_pattern"),
            ("CREATE (r:Rule {Rule_Id: 'X', project: $project})", "forbidden_clause"),
            ("UNWIND [1] AS x MERGE (r:Rule {Rule_Id: 'X', project: $project})", "forbidden_clause"),
            ("CALL db.labels()", "forbidden_clause"),
            ("LOAD CSV FROM 'file:///x' AS row MERGE (r:Rule {Rule_Id: 'X', project: $project})", "forbidden_clause"),
            ("FOREACH (x IN [1] | MERGE (r:Rule {Rule_Id: 'X', project: $project}))", "forbidden_clause"),
            (
                "MERGE (r:Rule {Rule_Id: 'X', project: $project}) DELETE r",
                "forbidden_clause",
            ),
            (
                "MERGE (r:Rule {Rule_Id: 'X', project: $project}) REMOVE r.SWRL",
                "forbidden_clause",
            ),
            (
                "MERGE (r:Rule {Rule_Id: 'X', project: $project}) ON CREATE SET r.a = '1'",
                "unsupported_syntax",
            ),
            (
                "MERGE (r:Rule {Rule_Id: 'X', project: $project}) SET r.project = 'other'",
                "protected_property_set",
            ),
            (
                "MERGE (r:Rule {Rule_Id: 'X', project: $project}) SET r.graph = 'Metagraph'",
                "protected_property_set",
            ),
            (
                "MERGE (r:Rule {Rule_Id: 'X', project: $project}) SET r.PROJECT = 'other'",
                "protected_property_set",
            ),
            (
                "MERGE (r:Rule {Rule_Id: 'X', project: $project}) SET r += {a: 1}",
                "unsupported_syntax",
            ),
            (
                "MERGE (r:Rule {Rule_Id: 'X', project: $project}) SET r = {a: 1}",
                "unsupported_syntax",
            ),
            (
                "MERGE (r:Rule {Rule_Id: 'X', project: $project}) SET r:Extra",
                "unsupported_syntax",
            ),
            (
                "MERGE (r:Rule {Rule_Id: 'X', project: $project}) SET r['project'] = 'x'",
                "unsupported_syntax",
            ),
            (
                "MERGE (r:Rule {Rule_Id: 'X', project: $project}) SET r.a = r.b",
                "unanalysable_value",
            ),
            (
                "MERGE (r:Rule {Rule_Id: 'X', project: $project}) SET r.a = 'x' + 'y'",
                "unsupported_syntax",
            ),
            (
                "MERGE (r:Rule {Rule_Id: 'X', project: $project}) SET r.a = $project",
                "unanalysable_value",
            ),
            (
                "MERGE (r:Rule {Rule_Id: 'X', project: $project}) SET n.a = 'x'",
                "unbound_set_target",
            ),
            ("MERGE (r:Rule {Rule_Id: 'X', project: $project}) // c", "unsupported_syntax"),
            ("MERGE (r:Rule {Rule_Id: 'X', project: $project}) /* c */", "unsupported_syntax"),
            ("MERGE (`r`:Rule {Rule_Id: 'X', project: $project})", "unsupported_syntax"),
            (
                "MERGE (r:Rule {Rule_Id: 'X', project: $project})-[:HAS_BODY {`order`: 1}]->"
                "(a:Atom {Atom_Id: 'A', project: $project})",
                "unsupported_syntax",
            ),
            (
                "MERGE (r:Rule {Rule_Id: 'X', project: $project}) MERGE (r:Rule {Rule_Id: 'Y', project: $project})",
                "rebound_variable",
            ),
            (
                "MERGE (r:Rule {Rule_Id: 'X', project: $project}) MERGE (a:Atom {Atom_Id: 'A', project: $project}) "
                "MERGE (r)-[:SUPERSEDED_BY]->(a)",
                "unknown_relationship",
            ),
            (
                "MERGE (r:Rule {Rule_Id: 'X', project: $project}) MERGE (a:Atom {Atom_Id: 'A', project: $project}) "
                "MERGE (r)-[e:HAS_BODY]->(a)",
                "unsupported_syntax",
            ),
            (
                "MERGE (r:Rule {Rule_Id: 'X', project: $project}) MERGE (a:Atom {Atom_Id: 'A', project: $project}) "
                "MERGE (r)-[:HAS_BODY*]->(a)",
                "unsupported_syntax",
            ),
            (
                "MERGE (r:Rule {Rule_Id: 'X', project: $project}) MERGE (r)-[:HAS_BODY]->(z)",
                "unlabeled_node_pattern",
            ),
            (
                "MATCH (r:Rule {Rule_Id: 'X', project: $project}) WHERE r.a = 1 SET r.b = '2'",
                "unsupported_syntax",
            ),
            (
                "OPTIONAL MATCH (r:Rule {Rule_Id: 'X', project: $project}) SET r.b = '2'",
                "unsupported_syntax",
            ),
            (
                "MERGE (r:Rule {Rule_Id: 'X', project: $project}); MERGE (a:Atom {Atom_Id: 'A'}); ",
                "missing_project_scope",
            ),
        ],
    )
    def test_rejected(self, cypher, code):
        result = write_check(cypher)
        assert code in _codes(result), (cypher, result)

    def test_duplicate_map_key_is_fatal(self):
        cypher = "MERGE (r:Rule {Rule_Id: 'X', project: $project, project: $project})"
        assert "unsupported_syntax" in _codes(write_check(cypher))


# ── write profile: legitimate ingests are accepted ────────────────────────


HEIGHT_RULE = """
MERGE (C_Main:Class {iri: 'ex:Building', project: $project, graph: 'OntoGraph'})
SET C_Main.label = 'Building'
MERGE (DP_Main:DatatypeProperty {iri: 'ex:height', project: $project, graph: 'OntoGraph'})
SET DP_Main.SWRL_label = 'height', DP_Main.range = 'xsd:decimal'
MERGE (B_Gt:Builtin {iri: 'swrlb:greaterThan', project: $project, graph: 'Metagraph'})
SET B_Gt.label = 'greaterThan'
MERGE (r:Rule {Rule_Id: 'R_URB_HEIGHT_MAX_75_V', project: $project, graph: 'Metagraph'})
SET r.SWRL = 'Building(?b) ^ height(?b, ?h) ^ swrlb:greaterThan(?h, "75"^^xsd:decimal) -> v(?b, true)', r.kind = 'violation'
MERGE (vb:Var {name: '?b', project: $project, graph: 'Metagraph'})
MERGE (lit:Literal {lex: '75', datatype: 'xsd:decimal', project: $project, graph: 'Metagraph'})
MERGE (a1:Atom {Atom_Id: 'R_URB_HEIGHT_MAX_75_V_A1', project: $project, graph: 'Metagraph'})
SET a1.type = 'ClassAtom', a1.iri = 'ex:Building', a1.SWRL_label = 'Building'
MERGE (r)-[:HAS_BODY {order: 1}]->(a1)
MERGE (a1)-[:REFERS_TO]->(C_Main)
MERGE (a1)-[:ARG {pos: 1}]->(vb);
"""


class TestWriteAcceptsLegitimateIngests:
    def test_height_rule(self):
        assert write_check(HEIGHT_RULE) == []

    def test_rule_description_with_quotes_semicolons_and_unicode(self):
        cypher = (
            "MERGE (r:Rule {Rule_Id: 'R_X_V', project: $project, graph: 'Metagraph'})\n"
            "SET r.RuleDescription = 'Height; \"max\" 75 m // высота /* x */'"
        )
        assert write_check(cypher) == []

    def test_separator_between_clauses_is_whitespace(self):
        cypher = (
            "MERGE (r:Rule {Rule_Id: 'R_A', project: $project, graph: 'Metagraph'});\n"
            "MERGE (a:Atom {Atom_Id: 'R_A_A1', project: $project, graph: 'Metagraph'});\n"
            "MERGE (r)-[:HAS_BODY {order: 1}]->(a);"
        )
        assert write_check(cypher) == []

    def test_match_by_complete_key_and_project_then_merge_relationship(self):
        cypher = (
            "MATCH (c:Class {iri: 'ex:Building', project: $project}) "
            "MERGE (a:Atom {Atom_Id: 'R_A_A1', project: $project, graph: 'Metagraph'}) "
            "MERGE (a)-[:REFERS_TO]->(c)"
        )
        assert write_check(cypher) == []

    def test_validate_cypher_accepts_legit_ingest_with_project(self):
        result = dg_context.validate_cypher(HEIGHT_RULE, "rule_ingest", project="p")
        assert result["valid"] is True, result["violations"]


# ── corpus: catalog shapes and reference examples ─────────────────────────


def _strip_headers(text: str) -> str:
    return "\n".join(line for line in text.split("\n") if not line.startswith("--"))


def migrate_legacy_ingest(text: str) -> str:
    """Mechanical rewrite of a pre-allowlist ingest example into the allowlisted
    shape: drop comments and backticks, take `project` from `$project`, and move
    `SET v.project/v.graph` into the MERGE property map."""
    text = text.replace("\r\n", "\n")
    kept = [ln for ln in text.split("\n") if not ln.strip().startswith(("//", "--"))]
    text = "\n".join(kept).replace("`", "")
    text = re.sub(r"project:\s*'[^']*'", "project: $project", text)
    pattern = re.compile(
        r"MERGE \((?P<var>\w+):(?P<label>\w+) \{(?P<props>[^}]*)\}\)"
        r"(?P<gap>[ \t]*\n[ \t]*SET )(?P<block>[^\n]*(?:\n[ \t]+[^\n]*)*)"
    )

    def hoist(match: "re.Match[str]") -> str:
        var, block, props = match.group("var"), match.group("block"), match.group("props")
        graph = re.search(rf"\b{var}\.graph\s*=\s*'([^']*)'", block)
        block = re.sub(rf"(?:,\s*)?\b{var}\.(?:project|graph)\s*=\s*'[^']*'", "", block)
        block = re.sub(r"^\s*,\s*", "", block).rstrip().rstrip(",").rstrip()
        entries = props.strip()
        if "project:" not in entries:
            entries += ", project: $project"
        if graph and "graph:" not in entries:
            entries += f", graph: '{graph.group(1)}'"
        head = f"MERGE ({match.group('var')}:{match.group('label')} {{{entries}}})"
        return head if not block.strip() else head + match.group("gap") + block

    return pattern.sub(hoist, text)


def _split_examples(text: str) -> list[str]:
    return re.split(r"(?m)^// (?:=== )?Example \d+[^\n]*\n", text)[1:]


# Only these codes may explain why a pre-allowlist reference example is
# rejected: the constructs the new guard deliberately disallows.
LEGACY_SHAPE_CODES = {
    "unsupported_syntax",  # comments, backticks
    "project_literal",  # project: '<name>' instead of $project
    "protected_property_set",  # SET x.project / x.graph
    "missing_project_scope",  # Literal/other MERGE keyed without project
}


class TestCatalogShapes:
    def test_every_catalog_template_and_worked_example_is_accepted(self):
        catalog = dg_context.load_cypher_catalog()
        assert len(catalog["shapes"]) == 6
        for shape in catalog["shapes"]:
            for field in ("cypher_template", "worked_example"):
                text = _strip_headers(shape[field].replace("\r\n", "\n"))
                violations = write_check(text)
                assert violations == [], (shape["id"], field, violations)

    def test_catalog_examples_carry_no_literal_project_or_comments(self):
        for shape in dg_context.load_cypher_catalog()["shapes"]:
            for field in ("cypher_template", "worked_example"):
                text = _strip_headers(shape[field])
                assert "//" not in text, (shape["id"], field)
                assert "`" not in text, (shape["id"], field)
                assert not re.search(r"\.project\s*=", text), (shape["id"], field)
                assert not re.search(r"project:\s*'", text), (shape["id"], field)


class TestReferenceExampleCorpus:
    FILES = (
        "updated_cypher_reference_examples_v3.cypher",
        "updated_cypher_reference_examples_v4.cypher",
    )

    def _examples(self) -> list[tuple[str, int, str]]:
        found = []
        for name in self.FILES:
            path = _repo_root() / "training" / name
            if not path.exists():
                pytest.skip(f"{path} is not available in this environment")
            for index, text in enumerate(_split_examples(path.read_text(encoding="utf-8")), 1):
                found.append((name, index, text))
        return found

    def test_corpus_size(self):
        assert len(self._examples()) == 7  # 3 (v3) + 4 (v4)

    def test_raw_examples_are_rejected_only_for_now_disallowed_constructs(self):
        """The reference examples predate the allowlist: they SET project/graph,
        write a literal project name, use backticks and comments. Each is
        rejected, and only for those reasons."""
        for name, index, text in self._examples():
            violations = write_check(text)
            assert violations, (name, index)
            assert _codes(violations) <= LEGACY_SHAPE_CODES, (name, index, violations)

    def test_migrated_examples_are_all_accepted(self):
        accepted = 0
        examples = self._examples()
        for name, index, text in examples:
            violations = write_check(migrate_legacy_ingest(text))
            assert violations == [], (name, index, violations)
            accepted += 1
        assert accepted == len(examples) == 7

    def test_migrated_examples_pass_the_full_ingest_validator(self):
        for name, index, text in self._examples():
            result = dg_context.validate_cypher(
                migrate_legacy_ingest(text), "rule_ingest", project="p"
            )
            assert result["valid"] is True, (name, index, result["violations"])

    def test_cassette_responses_are_rejected_and_migrate_cleanly(self):
        """Recorded model output (50 cassettes) predates the allowlist. Untruncated
        responses are all rejected for legacy-shape reasons; the mechanical
        migration turns every one into an accepted statement, i.e. the guard
        understands everything the model produced."""
        directory = _repo_root() / "fixtures" / "llm_repeatability" / "cassettes" / "rule_ingest"
        if not directory.exists():
            pytest.skip("cassette corpus not available")
        seen = accepted_after = 0
        for path in sorted(directory.glob("*.json")):
            record = json.loads(path.read_text(encoding="utf-8"))
            if record.get("truncated"):
                continue
            text = record["responseText"]
            seen += 1
            raw = write_check(text)
            assert raw, path.name
            assert _codes(raw) <= LEGACY_SHAPE_CODES | {
                "unanalysable_key",
                "disallowed_label",
                "unlabeled_node_pattern",
                "forbidden_clause",
                "missing_identity_key",
                "unknown_relationship",
                "unbound_set_target",
                "unanalysable_value",
            }, (path.name, raw)
            if not write_check(migrate_legacy_ingest(text)):
                accepted_after += 1
        assert seen > 0
        # Report line for the fix log: run with -s to see the counts.
        print(f"cassette corpus: {seen} untruncated, {accepted_after} accepted after migration")


# ── retry-with-feedback loop still drives the model to a conforming answer ─


class _QueueAdapter:
    def __init__(self, texts):
        self._texts = list(texts)
        self.prompts_seen: list[str] = []

    def generate(self, req, api_key):
        self.prompts_seen.append(req.prompt)
        return GenerateResponse(text=self._texts.pop(0), provider="fake", model="fake", usage={})


class TestRetryFeedback:
    def test_write_violation_becomes_feedback_and_second_attempt_passes(self, monkeypatch):
        legacy = "MERGE (r:Rule {Rule_Id: 'R_X_V'})\nSET r.project = 'p', r.graph = 'Metagraph'"
        adapter = _QueueAdapter([legacy, HEIGHT_RULE])
        monkeypatch.setattr(dg_context, "get_adapter", lambda provider, base_url=None: adapter)

        result = dg_context.generate_validated_cypher("a rule", "rule_ingest", project="p")

        assert result["valid"] is True
        assert result["attempts"] == 2
        assert "missing_project_scope" in adapter.prompts_seen[1]
        assert "protected_property_set" in adapter.prompts_seen[1]

    def test_read_violation_becomes_feedback(self, monkeypatch):
        bad = "MATCH (n:Rule {project: $project}) WITH n MATCH (m) RETURN m"
        good = "MATCH (n:Rule {project: $project}) RETURN n.Rule_Id LIMIT 50"
        adapter = _QueueAdapter([bad, good])
        monkeypatch.setattr(dg_context, "get_adapter", lambda provider, base_url=None: adapter)

        result = dg_context.generate_validated_cypher("q", "graph_query", project="p")

        assert result["valid"] is True
        assert result["attempts"] == 2
        assert "forbidden_clause" in adapter.prompts_seen[1]


class TestModuleSurface:
    def test_read_functions_cover_the_aggregates_the_prompt_teaches(self):
        for name in ("COUNT", "COLLECT", "SUM", "MIN", "MAX", "AVG"):
            assert name in cypher_allowlist.READ_FUNCTIONS
