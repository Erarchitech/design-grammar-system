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
            "MATCH (r:Rule {project: $project, SWRL: 'Büro // /* ` \" UNION CALL'}) "
            "RETURN r.Rule_Id"
        )
        assert read_check(cypher) == []

    def test_backslash_in_a_string_is_refused_not_interpreted(self):
        """The lexer does not mirror Neo4j's backslash escapes (they would let
        the two disagree on where a string ends); it refuses the backslash."""
        cypher = "MATCH (r:Rule {project: $project, SWRL: 'a\\' WITH b'}) RETURN r.Rule_Id"
        result = read_check(cypher)
        assert "unsupported_syntax" in _codes(result)
        assert any("backslash" in v["message"] for v in result), result

    def test_trailing_backslash_is_refused(self):
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
            # pattern predicates / pattern expressions are rejected outright
            # (1205 review iteration 4, CR-02): the only way to a relationship
            # is a MATCH clause, where every node must carry {project: $project}
            (
                "MATCH (r:Rule {project: $project}) WHERE NOT (r)-[:SUPERSEDED_BY]->() RETURN r",
                "unsupported_syntax",
            ),
            (
                "MATCH (r:Rule {project: $project}), (s:Rule {project: $project}) "
                "WHERE NOT (r)-[:SUPERSEDED_BY]->(s) RETURN r",
                "unsupported_syntax",
            ),
            (
                "MATCH (r:Rule {project: $project}) WHERE (r)-[:HAS_BODY]->(m) RETURN r",
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
                "unsupported_syntax",  # a ';' between clauses is refused outright
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

    def test_one_trailing_separator_is_accepted(self):
        cypher = (
            "MERGE (r:Rule {Rule_Id: 'R_A', project: $project, graph: 'Metagraph'})\n"
            "MERGE (a:Atom {Atom_Id: 'R_A_A1', project: $project, graph: 'Metagraph'})\n"
            "MERGE (r)-[:HAS_BODY {order: 1}]->(a);"
        )
        assert write_check(cypher) == []
        assert write_check(cypher + "\n  ") == []

    def test_separator_between_clauses_is_refused(self):
        cypher = (
            "MERGE (r:Rule {Rule_Id: 'R_A', project: $project, graph: 'Metagraph'});\n"
            "MERGE (a:Atom {Atom_Id: 'R_A_A1', project: $project, graph: 'Metagraph'});\n"
            "MERGE (r)-[:HAS_BODY {order: 1}]->(a);"
        )
        result = write_check(cypher)
        assert "unsupported_syntax" in _codes(result)
        assert any("between clauses" in v["message"] for v in result), result

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


# ── 1205 review iteration 4: CR-01 (STARTS/ENDS ... WITH) ─────────────────

_TWO_NODES = "MATCH (a:Rule {project: $project}), (b:Rule {project: $project}) "


class TestStartsEndsWithIsAnOperatorNotAWord:
    """`STARTS WITH` / `ENDS WITH` exist only in operator position after a
    complete operand. A `WITH` in any other position is always the forbidden
    clause, whatever text precedes it (property name, label, variable)."""

    @pytest.mark.parametrize(
        "where",
        [
            # the reviewer's reproduction: a property NAMED starts / ends
            "a.project = $project OR a.starts WITH a",
            "a.ends WITH a",
            # case variants
            "a.STARTS WITH a",
            "a.Starts With a",
            "a.ENDS WITH a",
            "a.eNdS wItH a",
            # a label named starts / ends
            "a:starts WITH a",
            "a:ENDS WITH a",
            # a variable named starts / ends
            "starts WITH a",
            "ends WITH a",
            # any other preceding token
            "a.name WITH a",
            "a.x = 1 WITH a",
            "a.x IS NULL WITH a",
            "(a.x) WITH a",
            "a.x STARTS WITH 'x' WITH a",
            "a.x = 'starts' WITH a",
            "a.x IN [1] WITH a",
        ],
    )
    def test_with_clause_smuggled_after_a_starts_lookalike_is_rejected(self, where):
        cypher = f"{_TWO_NODES}WHERE {where}\nMATCH (b)\nRETURN b.secret"
        result = read_check(cypher)
        assert any(v["code"] == "forbidden_clause" and v["path"] == "WITH" for v in result), (
            where,
            result,
        )

    def test_review_reproduction_is_rejected_exactly(self):
        cypher = (
            "MATCH (a:Rule {project: $project}), (b:Rule {project: $project})\n"
            "WHERE a.project = $project OR a.starts WITH a\n"
            "MATCH (b)\n"
            "RETURN b.secret"
        )
        assert "forbidden_clause" in _codes(read_check(cypher))

    @pytest.mark.parametrize(
        "where",
        [
            "a.name STARTS WITH 'x'",
            "a.name ENDS WITH 'x'",
            "a.name starts with 'x'",
            "a.name Ends With a.other",
            "a.starts STARTS WITH 'x'",  # a property named starts as the LEFT operand
            "a.name STARTS WITH 'x' AND a.name ENDS WITH 'y'",
            "NOT a.name STARTS WITH $project",
            "(a.name) STARTS WITH 'x'",
            "toLower(a.name) STARTS WITH toLower('X')",
        ],
    )
    def test_real_operator_still_parses(self, where):
        assert read_check(f"{_TWO_NODES}WHERE {where} RETURN a.Rule_Id") == [], where

    @pytest.mark.parametrize(
        "where",
        ["a.name STARTS 'x'", "a.name STARTS", "a.name ENDS a", "a.name STARTS WITH"],
    )
    def test_starts_ends_without_with_is_rejected(self, where):
        assert read_check(f"{_TWO_NODES}WHERE {where} RETURN a") != [], where

    def test_with_is_forbidden_at_every_position(self):
        for cypher in (
            "MATCH (a:Rule {project: $project}) WITH a RETURN a",
            "MATCH (a:Rule {project: $project}) RETURN a WITH a",
            "MATCH (a:Rule {project: $project}) RETURN a.x AS with",
            "MATCH (a:Rule {project: $project}) RETURN with",
            "MATCH (a:Rule {project: $project}) RETURN a.x STARTS WITH 'x' WITH a",
            "MATCH (a:Rule {project: $project}) RETURN [a.x WITH a]",
            "MATCH (a:Rule {project: $project}) RETURN size(a.x WITH a)",
        ):
            assert read_check(cypher), cypher

    def test_write_profile_rejects_with_after_a_starts_lookalike(self):
        cypher = (
            "MATCH (a:Rule {Rule_Id: 'R_A', project: $project}) "
            "MERGE (b:Atom {Atom_Id: 'x', project: $project}) SET a.starts WITH a"
        )
        assert write_check(cypher)


# ── 1205 review iteration 4: CR-02 (one node-shape reader, no IS syntax) ──


class TestNodeShapeReaderRejectsEverythingItDoesNotRecognise:
    @pytest.mark.parametrize(
        "cypher",
        [
            # the reviewer's reproductions
            "MATCH (a:Rule {project: $project}) "
            "WHERE (a IS Rule)-->({secret:'pb-SECRET-FOREIGN'}) RETURN 'x' AS r",
            "MATCH (a:Rule {project: $project}) "
            "WHERE (IS Rule)-->({secret:'pb-atom-secret'}) RETURN 'GLOBAL-ORACLE' AS r",
            # IS label syntax in every position a node or relationship appears
            "MATCH (a IS Rule {project: $project}) RETURN a",
            "MATCH (a IS Rule) RETURN a",
            "MATCH (IS Rule {project: $project}) RETURN 1 AS x",
            "OPTIONAL MATCH (a IS Rule {project: $project}) RETURN a",
            "MATCH (a:Rule {project: $project})-[r IS HAS_BODY]->(b:Atom {project: $project}) RETURN a",
            "MATCH (a:Rule {project: $project})-[:HAS_BODY]->(b IS Atom {project: $project}) RETURN a",
            "MATCH (a:Rule {project: $project}) RETURN (a IS Rule)-->(b) AS x",
            "MATCH (a:Rule {project: $project}) RETURN size((a IS Rule)-->(b)) AS x",
            "MATCH (a:Rule {project: $project}) RETURN exists((a IS Rule)-->(b)) AS x",
            "MATCH (a:Rule {project: $project}) WHERE a IS Rule RETURN a",
            "MATCH (a:Rule {project: $project}) WHERE a IS :: STRING RETURN a",
            "MATCH (a:Rule {project: $project}) WHERE a IS TYPED STRING RETURN a",
            # Neo4j 5 label expressions
            "MATCH (a:Rule|Atom {project: $project}) RETURN a",
            "MATCH (a:Rule&Atom {project: $project}) RETURN a",
            "MATCH (a:!Rule {project: $project}) RETURN a",
            "MATCH (a:% {project: $project}) RETURN a",
            "MATCH (a:(Rule|Atom) {project: $project}) RETURN a",
            "MATCH (a {project: $project}) WHERE a:Rule|Atom RETURN a",
            "MATCH (a {project: $project}) WHERE a:Rule&Atom RETURN a",
            "MATCH (a {project: $project}) WHERE a:!Rule RETURN a",
            "MATCH (a {project: $project}) WHERE a:% RETURN a",
            "MATCH (a:Rule {project: $project})-[r:HAS_BODY&HAS_HEAD]->(b:Atom {project: $project}) RETURN a",
            "MATCH (a:Rule {project: $project})-[r:!HAS_BODY]->(b:Atom {project: $project}) RETURN a",
            "MATCH (a:Rule {project: $project})-[r:%]->(b:Atom {project: $project}) RETURN a",
            "MATCH (a:Rule {project: $project})-[r:(HAS_BODY)]->(b:Atom {project: $project}) RETURN a",
            # inline WHERE and parameter maps
            "MATCH (a:Rule {project: $project} WHERE a.x = 1) RETURN a",
            "MATCH (a:Rule {project: $project})-[r:HAS_BODY WHERE r.order = 1]->(b:Atom {project: $project}) RETURN a",
            "MATCH (a:Rule $p) RETURN a",
            # path quantifiers and parenthesised path patterns
            "MATCH ((a:Rule {project: $project})-[:HAS_BODY]->(b:Atom {project: $project}))+ RETURN a",
            "MATCH (a:Rule {project: $project})-[:HAS_BODY]->+(b:Atom {project: $project}) RETURN a",
            "MATCH (a:Rule {project: $project})-[:HAS_BODY]->{1,3}(b:Atom {project: $project}) RETURN a",
            "MATCH (a:Rule {project: $project}) (()-[:HAS_BODY]->()){1,3} RETURN a",
        ],
    )
    def test_rejected(self, cypher):
        assert read_check(cypher), cypher

    @pytest.mark.parametrize(
        "predicate",
        [
            "(a)-[:X]->(b)",
            "(a)-[:X]-(b)",
            "(a)<-[:X]-(b)",
            "(a)-->(b)",
            "(a)--(b)",
            "(a)<--(b)",
            "(a)-[]->(b)",
            "(a)-[:X]->({secret: 'pb'})",
            "(a)-[:X]-({secret: 'pb'})",
            "(a)-->({secret: 'pb'})",
            "(a) < - [:X] - ({secret: 'pb'})",
            "(a) - - ({secret: 'pb'})",
            "(a)-[:X]->(b:Rule {project: $project})",
            "(a)-[:X]->(:Rule {project: $project})",
            "({secret: 'pb'})-->(a)",
            "(:Rule {secret: 'pb'})-->(a)",
            "(:Rule)-->(a)",
            "()-->()",
            "(a)-[:X]->()-[:Y]->()",
        ],
    )
    def test_pattern_predicates_and_expressions_are_rejected_everywhere(self, predicate):
        """A pattern outside MATCH is rejected entirely (no node in it could be
        held to the {project: $project} rule), wherever an expression may sit."""
        base = "MATCH (a:Rule {project: $project}), (b:Rule {project: $project}) "
        for cypher in (
            f"{base}WHERE {predicate} RETURN a",
            f"{base}WHERE NOT {predicate} RETURN a",
            f"{base}WHERE a.x = 1 AND {predicate} RETURN a",
            f"{base}WHERE a.x = 1 OR NOT ({predicate}) RETURN a",
            f"{base}RETURN {predicate} AS p",
            f"{base}RETURN exists({predicate}) AS p",
            f"{base}RETURN size({predicate}) AS p",
            f"{base}RETURN coalesce({predicate}, false) AS p",
            f"{base}RETURN [{predicate}] AS p",
            f"{base}RETURN {{p: {predicate}}} AS p",
            f"{base}RETURN CASE WHEN {predicate} THEN 1 ELSE 0 END AS p",
            f"{base}RETURN a ORDER BY {predicate}",
            f"{base}RETURN a LIMIT size({predicate})",
            f"MATCH (a:Rule {{project: $project}}) OPTIONAL MATCH (a)-[:X]->(b:Rule {{project: $project}}) "
            f"WHERE {predicate} RETURN a",
        ):
            assert read_check(cypher), cypher

    def test_relationship_reachable_only_through_match(self):
        """The supported way to ask 'does a have an outgoing X edge' is an
        OPTIONAL MATCH with a scoped far node."""
        cypher = (
            "MATCH (a:Rule {project: $project}) "
            "OPTIONAL MATCH (a)-[:SUPERSEDED_BY]->(s:Rule {project: $project}) "
            "WHERE s IS NULL RETURN a.Rule_Id"
        )
        assert read_check(cypher) == []

    def test_unscoped_far_node_of_a_match_chain_is_still_a_violation(self):
        result = read_check("MATCH (a:Rule {project: $project})-[:X]->(b) RETURN b.secret")
        assert any(v["code"] == "missing_project_scope" and v["path"] == "b" for v in result)

    def test_write_profile_shares_the_node_shape_reader(self):
        for cypher in (
            "MERGE (a IS Rule {Rule_Id: 'R_X', project: $project})",
            "MERGE (a:Rule|Atom {Rule_Id: 'R_X', project: $project})",
            "MERGE (a:Rule {Rule_Id: 'R_X', project: $project}) "
            "MERGE (a)-[r IS HAS_BODY]->(b:Atom {Atom_Id: 'A', project: $project})",
        ):
            assert write_check(cypher), cypher


# ── 1205 review iteration 4: structural invariant ─────────────────────────


def _paren_spans(toks):
    """Independent of the parser: (open_index, close_index) for every `(`."""
    stack, spans = [], []
    for index, tok in enumerate(toks):
        if tok.kind == "PUNCT" and tok.text == "(":
            stack.append(index)
        elif tok.kind == "PUNCT" and tok.text == ")" and stack:
            spans.append((stack.pop(), index))
    return spans


def _relationship_adjacent(toks, open_index, close_index) -> bool:
    """True when the lexer alone shows a relationship dash next to this
    parenthesis -- i.e. it is (an endpoint of) a pattern."""

    def punct(index):
        if 0 <= index < len(toks) and toks[index].kind == "PUNCT":
            return toks[index].text
        return None

    if open_index > 0 and toks[open_index - 1].kind == "IDENT":
        return False  # a function call, not a pattern endpoint
    after = (punct(close_index + 1) == "-" and punct(close_index + 2) in ("-", "[")) or (
        punct(close_index + 1) == "<" and punct(close_index + 2) == "-"
    )
    before = (punct(open_index - 1) == ">" and punct(open_index - 2) == "-") or (
        punct(open_index - 1) == "-" and punct(open_index - 2) in ("-", "]")
    )
    return before or after


def _assert_structurally_sound(cypher: str) -> None:
    """For an ACCEPTED read query: every `(` the lexer sees was classified by
    the parser, every node pattern the reader processed is scoped, and every
    parenthesis the lexer shows next to a relationship dash was read as a node
    pattern (not waved through as a grouping)."""
    violations, parser = cypher_allowlist.analyze(cypher, mode="read")
    assert violations == [], (cypher, violations)
    assert parser is not None
    toks = parser.toks
    for index, tok in enumerate(toks):
        if tok.kind == "PUNCT" and tok.text == "(":
            assert parser.paren_kind.get(index) in ("node", "call", "group"), (cypher, tok.pos)
    assert all(scoped for _, _, scoped in parser.node_patterns), (cypher, parser.node_patterns)
    for open_index, close_index in _paren_spans(toks):
        if _relationship_adjacent(toks, open_index, close_index):
            assert parser.paren_kind[open_index] == "node", (cypher, toks[open_index].pos)


class TestStructuralInvariant:
    @pytest.mark.parametrize("cypher", LEGIT_READ_QUERIES)
    def test_every_accepted_legit_query_is_structurally_sound(self, cypher):
        _assert_structurally_sound(cypher)

    def test_audit_fails_a_query_whose_parenthesis_was_never_classified(self):
        toks = cypher_allowlist.tokenize(
            "MATCH (a:Rule {project: $project}) RETURN a.x", cypher_allowlist._READ_HOW
        )
        parser = cypher_allowlist._Parser(toks, how="h", mode="read")
        result = cypher_allowlist._audit(parser)  # nothing was parsed
        assert any(v["code"] == "unsupported_syntax" for v in result)

    def test_audit_fails_a_node_pattern_that_was_not_proven_scoped(self):
        toks = cypher_allowlist.tokenize("RETURN 1", cypher_allowlist._READ_HOW)
        parser = cypher_allowlist._Parser(toks, how="h", mode="read")
        parser.node_patterns.append((0, "(x)", False))
        assert any(v["code"] == "missing_project_scope" for v in cypher_allowlist._audit(parser))

    def test_audit_is_clean_for_a_fully_parsed_query(self):
        violations, parser = cypher_allowlist.analyze(LEGIT_READ_QUERIES[0], mode="read")
        assert violations == []
        assert cypher_allowlist._audit(parser) == []

    def test_a_parenthesis_inside_an_expression_is_never_a_node_pattern(self):
        _, parser = cypher_allowlist.analyze(
            "MATCH (a:Rule {project: $project}) WHERE (a.x = 1) AND size(a.l) > 0 RETURN a",
            mode="read",
        )
        assert sorted(parser.paren_kind.values()) == ["call", "group", "node"]


# Hostile node-pattern snippets, none of which may be accepted in ANY slot of
# an otherwise valid query: each holds (or hides) a node that is not proven to
# carry {project: $project}.
HOSTILE_NODE_SNIPPETS = [
    "(b)",
    "(b:Rule)",
    "(b {secret: 'x'})",
    "(b:Rule {secret: 'x'})",
    "(b:Rule {project: 'pb'})",
    "(b:Rule {project: $other})",
    "({secret: 'x'})",
    "(:Rule {secret: 'x'})",
    "()",
    "(b IS Rule)",
    "(IS Rule)",
    "(b IS Rule {secret: 'x'})",
    "(b:Rule|Atom)",
    "(b:Rule&Atom {secret: 'x'})",
    "(b:!Rule)",
    "(b:% {secret: 'x'})",
    "(b WHERE b.secret = 'x')",
    "(b:Rule WHERE b.secret = 'x')",
    "(b $props)",
    "((b))",
    "(`b`:Rule {project: $project})",
]

HOSTILE_SLOTS = [
    "MATCH (a:Rule {{project: $project}}) WHERE (a)-[:X]->{n} RETURN a",
    "MATCH (a:Rule {{project: $project}}) WHERE (a)<-[:X]-{n} RETURN a",
    "MATCH (a:Rule {{project: $project}}) WHERE NOT (a)-->{n} RETURN a",
    "MATCH (a:Rule {{project: $project}}) WHERE {n}-->(a) RETURN a",
    "MATCH (a:Rule {{project: $project}}) WHERE {n}--(a) RETURN a",
    "MATCH (a:Rule {{project: $project}}) WHERE {n}-[:X]->(a) RETURN a",
    "MATCH (a:Rule {{project: $project}}) RETURN (a)-[:X]->{n} AS p",
    "MATCH (a:Rule {{project: $project}}) RETURN exists((a)-->{n}) AS p",
    "MATCH (a:Rule {{project: $project}}) RETURN size((a)-->{n}) AS p",
    "MATCH (a:Rule {{project: $project}}) RETURN [(a)-->{n} | 1] AS p",
    "MATCH (a:Rule {{project: $project}}) RETURN a ORDER BY size((a)-->{n})",
    "MATCH (a:Rule {{project: $project}}) OPTIONAL MATCH (a)-[:X]->{n} RETURN a",
    "MATCH (a:Rule {{project: $project}}) MATCH (a)-[:X]->{n} RETURN a",
    "MATCH (a:Rule {{project: $project}})-[:X]->{n} RETURN a",
    "MATCH {n}-[:X]->(a:Rule {{project: $project}}) RETURN a",
    "MATCH (a:Rule {{project: $project}}), {n} RETURN a",
    "MATCH (a:Rule {{project: $project}}) WHERE a.x = {n} RETURN a",
    "MATCH (a:Rule {{project: $project}}) RETURN {n} AS p",
    "MATCH (a:Rule {{project: $project}}) RETURN coalesce({n}, 1) AS p",
    "MATCH (a:Rule {{project: $project}}) RETURN CASE WHEN {n} THEN 1 ELSE 0 END AS p",
]


# A lone parenthesised value is an ordinary expression grouping, not a pattern
# (a pattern needs a relationship). These spellings are therefore legitimate in
# the plain value slots (`a.x = {n}`, `RETURN {n}`, `coalesce({n}, 1)`, CASE);
# what must never happen is one of them being read as a node that escapes the
# project rule inside a relationship.
_VALUE_SLOT_MARKERS = ("a.x = {n}", "RETURN {n} AS p", "coalesce({n}", "WHEN {n} THEN")
_GROUPING_LOOKALIKES = {"(b)", "(b:Rule)", "({secret: 'x'})", "((b))"}


class TestHostileNodePatternMatrix:
    @pytest.mark.parametrize("slot", HOSTILE_SLOTS)
    @pytest.mark.parametrize("snippet", HOSTILE_NODE_SNIPPETS)
    def test_no_hostile_node_pattern_is_accepted_in_any_slot(self, slot, snippet):
        if snippet in _GROUPING_LOOKALIKES and any(m in slot for m in _VALUE_SLOT_MARKERS):
            pytest.skip("a lone parenthesised value is an expression grouping")
        cypher = slot.format(n=snippet)
        assert read_check(cypher), cypher


_FUZZ_VOCABULARY = [
    "(", ")", "-", "--", "-->", "<--", "->", "<-", "[", "]", "{", "}", ":", ",", ".", "|", "&",
    "IS", "NOT", "NULL", "WITH", "STARTS", "ENDS", "MATCH", "OPTIONAL", "WHERE", "RETURN", "AND", "OR",
    "IN", "CASE", "WHEN", "THEN", "ELSE", "END", "count", "size", "exists", "collect", "$project",
    "project", "b", "c", "a.x", "a.starts", "a.ends", "'x'", "1", "=", "<>", "<", ">", "=~", "+", "*",
    "{secret: 'x'}", "(b)", "(b:Rule)", "({secret: 'x'})", "(a)-[:X]->(b)", "(a)-->()", "DISTINCT",
    "Rule", "a", "s",
]


def _mutations(seed_queries: list[str], count: int) -> list[str]:
    import random

    rng = random.Random(1205)
    out = []
    for _ in range(count):
        toks = rng.choice(seed_queries).split(" ")
        for _ in range(rng.randint(1, 3)):
            op = rng.choice(("insert", "delete", "replace", "duplicate", "swap"))
            at = rng.randrange(len(toks) + 1)
            if op == "insert":
                toks.insert(at, rng.choice(_FUZZ_VOCABULARY))
            elif op == "delete" and toks:
                toks.pop(min(at, len(toks) - 1))
            elif op == "replace" and toks:
                toks[min(at, len(toks) - 1)] = rng.choice(_FUZZ_VOCABULARY)
            elif op == "duplicate" and toks:
                i = min(at, len(toks) - 1)
                toks.insert(i, toks[i])
            elif op == "swap" and len(toks) > 1:
                i = min(at, len(toks) - 2)
                toks[i], toks[i + 1] = toks[i + 1], toks[i]
        out.append(" ".join(toks))
    return out


class TestPropertyStyleInvariant:
    def test_every_accepted_mutation_of_a_legit_query_is_structurally_sound(self):
        """Seeded mutation fuzz: whatever the mutated text is, if the allowlist
        accepts it then no node pattern escaped the shape reader."""
        accepted = 0
        for cypher in _mutations(LEGIT_READ_QUERIES, 6000):
            if read_check(cypher):
                continue
            accepted += 1
            _assert_structurally_sound(cypher)
        assert accepted > 0, "the mutation corpus accepted nothing; the test checks nothing"
        print(f"mutation fuzz: {accepted} accepted queries checked")


# ── 1205 review iteration 4: WR-01 (nesting ceiling, never raises) ────────

_DEEP_HEAD = "MATCH (a:Rule {project: $project}) "


def _deep_shapes(n: int) -> dict[str, str]:
    return {
        "parens": _DEEP_HEAD + "WHERE " + "(" * n + "a.x = 1" + ")" * n + " RETURN a",
        "lists": _DEEP_HEAD + "RETURN " + "[" * n + "1" + "]" * n,
        "maps": _DEEP_HEAD + "RETURN " + "{k: " * n + "1" + "}" * n,
        "calls": _DEEP_HEAD + "RETURN " + "size(" * n + "a.x" + ")" * n,
        "case": _DEEP_HEAD + "RETURN " + "CASE WHEN true THEN " * n + "1" + " END" * n,
        "index": _DEEP_HEAD + "RETURN a.x" + "[0" * n + "]" * n,
    }


class TestNestingDepthCeiling:
    @pytest.mark.parametrize("shape", sorted(_deep_shapes(1)))
    def test_about_a_thousand_levels_is_a_violation_not_an_exception(self, shape):
        result = read_check(_deep_shapes(1000)[shape])
        assert any(v["code"] == "unsupported_syntax" for v in result), shape
        assert any("deeper" in v["message"] or "nests" in v["message"] for v in result), shape

    @pytest.mark.parametrize("shape", sorted(_deep_shapes(1)))
    def test_the_ceiling_is_exact(self, shape):
        ceiling = cypher_allowlist.MAX_NESTING_DEPTH
        assert read_check(_deep_shapes(ceiling - 2)[shape]) == [], shape
        assert read_check(_deep_shapes(ceiling + 1)[shape]) != [], shape

    def test_ordinary_queries_nest_far_below_the_ceiling(self):
        assert cypher_allowlist.MAX_NESTING_DEPTH >= 32
        assert read_check(_deep_shapes(8)["parens"]) == []

    def test_a_python_recursion_error_becomes_a_violation(self, monkeypatch):
        def explode(self):
            raise RecursionError("simulated")

        monkeypatch.setattr(cypher_allowlist._Parser, "parse_read", explode)
        result = read_check("MATCH (a:Rule {project: $project}) RETURN a")
        assert [v["code"] for v in result] == ["unsupported_syntax"]

    def test_an_unexpected_exception_is_refused_not_raised(self, monkeypatch):
        def explode(self):
            raise ZeroDivisionError("bug")

        monkeypatch.setattr(cypher_allowlist._Parser, "parse_write", explode)
        result = write_check("MERGE (r:Rule {Rule_Id: 'R_X', project: $project})")
        assert [v["code"] for v in result] == ["unsupported_syntax"]

    def test_oversized_text_is_refused(self):
        huge = "MATCH (a:Rule {project: $project}) RETURN " + "a.x, " * 60000 + "a.y"
        assert len(huge) > cypher_allowlist.MAX_QUERY_CHARS
        assert any("longer than" in v["message"] for v in read_check(huge))

    def test_flat_long_queries_are_linear_not_recursive(self):
        many = "MATCH (a:Rule {project: $project}) RETURN " + ", ".join(["a.x"] * 5000)
        assert read_check(many) == []
        chain = "MATCH (a:Rule {project: $project}) WHERE " + " AND ".join(["a.x = 1"] * 5000) + " RETURN a"
        assert read_check(chain) == []


class TestForbiddenClauseWordsIncludeCypher25:
    @pytest.mark.parametrize("word", ["FOR", "LET", "FILTER", "NEXT", "OFFSET", "CYPHER"])
    def test_word_is_forbidden_as_a_clause_and_inside_expressions(self, word):
        assert word in cypher_allowlist.FORBIDDEN_CLAUSE_WORDS
        for cypher in (
            f"MATCH (a:Rule {{project: $project}}) {word} a RETURN a",
            f"MATCH (a:Rule {{project: $project}}) RETURN a {word} 1",
            f"MATCH (a:Rule {{project: $project}}) WHERE a.x = 1 {word.lower()} x RETURN a",
            f"{word} x MATCH (a:Rule {{project: $project}}) RETURN a",
        ):
            assert any(v["code"] == "forbidden_clause" for v in read_check(cypher)), cypher
        assert any(
            v["code"] == "forbidden_clause"
            for v in write_check(f"MERGE (r:Rule {{Rule_Id: 'R_X', project: $project}}) {word} r")
        )


# ── 1205 review iteration 4: string-literal escapes (lexer vs Neo4j) ──────

_BS = "\\"


class TestStringLiteralsAgreeWithNeo4jOnWhereTheyEnd:
    """Neo4j honours backslash escapes (escaped quotes, \\n, \\uXXXX ...) and may
    decode unicode escapes before tokenising. Mirroring all of that is how a
    lexer ends a string one character away from the server. Both profiles
    instead refuse every construct the two could disagree on."""

    @pytest.mark.parametrize(
        "literal",
        [
            "'a" + _BS + "' WITH b'",  # escaped single quote
            '"a' + _BS + '" WITH b"',  # escaped double quote
            "'a" + _BS + _BS + "'",  # escaped backslash
            "'a" + _BS + "n b'",  # newline escape
            "'a" + _BS + "tb'",
            "'" + _BS + "u0027 WITH b'",  # 4-digit unicode escape (a quote)
            "'" + _BS + "U00000027 WITH b'",  # 8-digit unicode escape
            "'" + _BS + "x27'",
            "'" + _BS + "0'",
            "'a" + _BS + "'",  # backslash right before the closing quote
            "'" + _BS + "'",
        ],
    )
    def test_read_profile_refuses_any_backslash_in_a_string(self, literal):
        cypher = f"MATCH (r:Rule {{project: $project, SWRL: {literal}}}) RETURN r.Rule_Id"
        result = read_check(cypher)
        assert result, literal
        assert "unsupported_syntax" in _codes(result)

    @pytest.mark.parametrize(
        "literal",
        [
            "'a" + _BS + "' WITH b'",
            '"a' + _BS + '" WITH b"',
            "'" + _BS + "u0027 WITH b'",
            "'a" + _BS + "'",
        ],
    )
    def test_write_profile_refuses_any_backslash_in_a_string(self, literal):
        cypher = (
            "MERGE (r:Rule {Rule_Id: 'R_X', project: $project, graph: 'Metagraph'}) "
            f"SET r.SWRL = {literal}"
        )
        result = write_check(cypher)
        assert result, literal
        assert "unsupported_syntax" in _codes(result)

    def test_unicode_escape_outside_a_string_is_refused_too(self):
        cypher = "MATCH (r:Rule {project: $project}) WHERE r.x = " + _BS + "u0027a" + _BS + "u0027 RETURN r"
        assert "unsupported_syntax" in _codes(read_check(cypher))

    @pytest.mark.parametrize("literal", ["'a''b'", '"a""b"', "''''", "'a' 'b'"])
    def test_doubled_or_adjacent_quotes_are_refused(self, literal):
        cypher = f"MATCH (r:Rule {{project: $project, SWRL: {literal}}}) RETURN r.Rule_Id"
        assert read_check(cypher), literal
        assert write_check(
            "MERGE (r:Rule {Rule_Id: 'R_X', project: $project, graph: 'Metagraph'}) "
            f"SET r.SWRL = {literal}"
        ), literal

    def test_doubled_quote_message_names_the_problem(self):
        result = read_check("MATCH (r:Rule {project: $project, SWRL: 'a''b'}) RETURN r")
        assert any("doubled quote" in v["message"] for v in result), result

    @pytest.mark.parametrize(
        "text",
        [
            "a" + chr(0) + "b",
            "a" + chr(7) + "b",
            "a" + chr(0x1B) + "b",
            "a" + chr(0x7F) + "b",
        ],
    )
    def test_control_characters_inside_a_string_are_refused(self, text):
        assert read_check(f"MATCH (r:Rule {{project: $project, SWRL: '{text}'}}) RETURN r")

    def test_the_other_quote_character_and_plain_punctuation_are_ordinary_content(self):
        cypher = (
            "MATCH (r:Rule {project: $project, SWRL: 'say \"hi\"; done -- // /* x */ UNION'}) "
            "RETURN r.Rule_Id"
        )
        assert read_check(cypher) == []
        cypher = "MATCH (r:Rule {project: $project, SWRL: \"it's; fine\"}) RETURN r.Rule_Id"
        assert read_check(cypher) == []

    def test_multi_line_strings_end_where_neo4j_ends_them(self):
        cypher = "MATCH (r:Rule {project: $project, SWRL: 'line one\nline two WITH b'}) RETURN r.Rule_Id"
        assert read_check(cypher) == []

    def test_string_contents_never_leak_into_the_token_stream(self):
        toks = cypher_allowlist.tokenize("RETURN 'a WITH b; MATCH (x)' AS s", "h")
        assert [t.kind for t in toks] == ["IDENT", "STRING", "IDENT", "IDENT"]
        assert toks[1].text == "a WITH b; MATCH (x)"

    def test_catalog_and_reference_corpus_contain_no_backslash(self):
        """The reference examples never needed an escape, so refusing them costs
        the model nothing."""
        for shape in dg_context.load_cypher_catalog()["shapes"]:
            for field in ("cypher_template", "worked_example"):
                assert _BS not in shape[field], (shape["id"], field)
        for name in TestReferenceExampleCorpus.FILES:
            path = _repo_root() / "training" / name
            if path.exists():
                assert _BS not in path.read_text(encoding="utf-8"), name


# ── 1205 review iteration 4: WR-04 / WR-05 (statement separators) ─────────


class TestStatementSeparators:
    """The n8n graph-query workflow appends ` LIMIT 50`; the n8n rules-ingest
    workflow chains clauses into one statement. Neither may depend on text
    processing that mirrors the lexer's quoting rules, so the allowlist itself
    refuses every `;` that could matter."""

    @pytest.mark.parametrize(
        "cypher",
        [
            "MATCH (r:Rule {project: $project}) RETURN r.Rule_Id;",
            "MATCH (r:Rule {project: $project}) RETURN r.Rule_Id ;  ",
            "MATCH (r:Rule {project: $project}) RETURN r.Rule_Id LIMIT 5;",
            "MATCH (r:Rule {project: $project}) RETURN r.Rule_Id;;",
            "MATCH (r:Rule {project: $project}) RETURN r.Rule_Id; MATCH (m:Rule {project: $project}) RETURN m",
            "MATCH (r:Rule {project: $project}); RETURN r",
            "; MATCH (r:Rule {project: $project}) RETURN r",
            "MATCH (r:Rule {project: $project}) WHERE r.x = 1; RETURN r",
        ],
    )
    def test_read_profile_refuses_every_semicolon(self, cypher):
        result = read_check(cypher)
        assert "unsupported_syntax" in _codes(result), cypher

    def test_semicolon_inside_a_string_is_content_not_a_separator(self):
        cypher = "MATCH (r:Rule {project: $project, SWRL: 'a; b;'}) RETURN r.Rule_Id"
        assert read_check(cypher) == []
        cypher = (
            "MERGE (r:Rule {Rule_Id: 'R_X', project: $project, graph: 'Metagraph'}) "
            "SET r.SWRL = 'Building(?b) ^ height(?b, ?h); more', r.kind = \"a;b\";"
        )
        assert write_check(cypher) == []

    @pytest.mark.parametrize(
        "cypher",
        [
            "MERGE (r:Rule {Rule_Id: 'R_X', project: $project}); MERGE (a:Atom {Atom_Id: 'A', project: $project})",
            "MERGE (r:Rule {Rule_Id: 'R_X', project: $project});; ",
            "; MERGE (r:Rule {Rule_Id: 'R_X', project: $project})",
            "MERGE (r:Rule {Rule_Id: 'R_X', project: $project}) SET r.a = 'x'; SET r.b = 'y'",
            "MERGE (r:Rule {Rule_Id: 'R_X', project: $project})\n;\nMERGE (a:Atom {Atom_Id: 'A', project: $project})",
        ],
    )
    def test_write_profile_refuses_a_separator_anywhere_but_last(self, cypher):
        assert "unsupported_syntax" in _codes(write_check(cypher)), cypher

    def test_a_validated_write_statement_has_no_separator_but_the_last_token(self):
        toks = cypher_allowlist.tokenize(HEIGHT_RULE, "h")
        semis = [i for i, t in enumerate(toks) if t.kind == "PUNCT" and t.text == ";"]
        assert semis in ([], [len(toks) - 1])
        assert write_check(HEIGHT_RULE) == []

    def test_retry_feedback_teaches_the_no_separator_rule(self):
        result = write_check(
            "MERGE (r:Rule {Rule_Id: 'R_A', project: $project}); MERGE (a:Atom {Atom_Id: 'A', project: $project})"
        )
        assert any("one trailing ';'" in v["message"] for v in result), result


# ── 1205 review iteration 4: WR-02 (examples are valid allowlist input) ───


def _template_block() -> str:
    text = (_repo_root() / "cypher_template.txt").read_text(encoding="utf-8").replace("\r\n", "\n")
    start = text.index("CYPHER TEMPLATE BLOCK") + len("CYPHER TEMPLATE BLOCK")
    end = text.index("QUALITY CHECKS")
    return text[start:end].strip()


def _instantiate(block: str) -> str:
    """Fill the `<PLACEHOLDER>` slots of the template block with sample values."""
    samples = {
        "CLASS_NAME": "Building",
        "PROPERTY_NAME": "height",
        "BUILTIN_NAME": "greaterThan",
        "VIOLATION_PROPERTY": "heightExceedsMax",
        "RULE_ID": "R_URB_HEIGHT_MAX_75_V",
        "SWRL_EXPRESSION": "Building(?b) ^ height(?b, ?h) -> heightExceedsMax(?b, true)",
        "ENTITY_VAR": "b",
        "VALUE_VAR": "h",
        "THRESHOLD": "75",
        "xsd:decimal|xsd:integer|xsd:boolean": "xsd:decimal",
        "xsd:decimal|xsd:integer": "xsd:decimal",
    }
    for key, value in samples.items():
        block = block.replace(f"<{key}>", value)
    assert "<" not in block.replace("->", "").replace("<-", ""), block
    return block


class TestModelFacingExamplesAreValidAllowlistInput:
    """The Cypher the model is shown as a positive pattern must itself pass the
    allowlist that will grade its output -- verbatim, with no header stripping."""

    def test_every_catalog_example_passes_the_write_profile_as_shown(self):
        shapes = dg_context.load_cypher_catalog()["shapes"]
        assert len(shapes) == 6
        for shape in shapes:
            for field in ("cypher_template", "worked_example"):
                text = shape[field]
                violations = write_check(text)
                assert violations == [], (shape["id"], field, violations)

    def test_no_model_facing_cypher_string_carries_a_comment_or_narration_line(self):
        for shape in dg_context.load_cypher_catalog()["shapes"]:
            for field in ("cypher_template", "worked_example"):
                text = shape[field]
                assert not any(line.lstrip().startswith(("--", "//", "/*")) for line in text.split("\n")), (
                    shape["id"],
                    field,
                )
                assert ";" not in text.rstrip().rstrip(";"), (shape["id"], field, "interior ';'")
            assert isinstance(shape.get("narration"), str) and shape["narration"], shape["id"]

    def test_narration_never_shows_a_literal_project_to_copy(self):
        for shape in dg_context.load_cypher_catalog()["shapes"]:
            assert not re.search(r"project:\s*'", shape["narration"]), shape["id"]

    def test_cypher_template_txt_block_passes_the_write_profile(self):
        assert write_check(_instantiate(_template_block())) == []

    def test_cypher_template_participants_section_passes_the_write_profile(self):
        """Plan 1303-20 (D-61): the PARTICIPANTS AND RELATIONS section sits after
        QUALITY CHECKS (so _template_block() is unchanged) and its participant
        MERGE example is valid allowlist input once instantiated."""
        text = (_repo_root() / "cypher_template.txt").read_text(encoding="utf-8").replace("\r\n", "\n")
        assert text.index("QUALITY CHECKS") < text.index("PARTICIPANTS AND RELATIONS")
        section = text[text.index("PARTICIPANTS AND RELATIONS"):]
        assert "PARTICIPANT MERGE EXAMPLE" not in _template_block()
        for needle in ("ObjectPropertyAtom", "domain", "range", "outline", "never"):
            assert needle.lower() in section.lower(), needle
        example = section[section.index("PARTICIPANT MERGE EXAMPLE") + len("PARTICIPANT MERGE EXAMPLE"):].strip()
        samples = {
            "CLASS_NAME": "Opening",
            "PARTICIPANT_CLASS": "Slab",
            "RELATION_NAME": "hostedBy",
            "RULE_ID": "R_STR_OPENING_CLEARANCE_MIN_500_V",
            "ENTITY_VAR": "o",
            "PARTICIPANT_VAR": "s",
        }
        for key, value in samples.items():
            example = example.replace(f"<{key}>", value)
        assert "<" not in example, example
        assert "OP_Rel.domain = 'ex:Opening'" in example and "OP_Rel.range = 'ex:Slab'" in example
        assert write_check(example) == []

    def test_every_catalog_worked_example_passes_the_full_ingest_validator(self):
        for shape in dg_context.load_cypher_catalog()["shapes"]:
            result = dg_context.validate_cypher(shape["worked_example"], "rule_ingest", project="p")
            assert result["valid"] is True, (shape["id"], result["violations"])

    def test_a_graph_query_reference_shape_passes_the_read_profile(self):
        """Every read query the n8n graph-query prompt teaches (the supersession
        exclusion via OPTIONAL MATCH ... IS NULL, the ValidationRun read) is
        accepted by the read profile."""
        for cypher in (
            "MATCH (r:Rule {project: $project}) "
            "OPTIONAL MATCH (r)-[:SUPERSEDED_BY]->(s:Rule {project: $project}) "
            "WHERE s IS NULL RETURN r.Rule_Id LIMIT 50",
            "MATCH (run:ValidationRun {project: $project}) "
            "RETURN run.Run_Id, run.statePayloadJson ORDER BY run.Run_Id LIMIT 50",
        ):
            assert read_check(cypher) == []
