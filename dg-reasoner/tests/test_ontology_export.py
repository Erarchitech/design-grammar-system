"""Structural fidelity tests for dg-reasoner/ontology_export.py (REAS-04/REAS-05, D-14).

Runs entirely offline -- no docker, no live Neo4j, no JRE. `FixtureSession`
duck-types the `neo4j.Session.run()` contract `build_graph()` expects
(iterable of mapping-like records, `.single()` on the result), sourcing its
answers from the committed graph-shaped fixture at
`dg-reasoner/tests/fixtures/metagraph_fixture.json` instead of a live bolt
connection. This exercises the exact same `build_graph` logic Plan 03's
reasoning/SHACL routes and the live CLI path both call.

Assertions are STRUCTURAL (D-14): the produced Turtle is serialized, parsed
back with rdflib, and walked via rdf:first/rdf:rest -- no golden-file byte
comparison.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from rdflib import Graph, Literal as RDFLiteral, URIRef
from rdflib.namespace import OWL, RDF

import ontology_export as oe

FIXTURE_PATH = Path(__file__).resolve().parent / "fixtures" / "metagraph_fixture.json"
PROJECT = "fixture-proj"


class _FakeResult(list):
    """Mimics `neo4j.Result`: iterable, plus `.single()` for scalar queries."""

    def single(self):
        return self[0] if self else None


class FixtureSession:
    """Duck-types `neo4j.Session.run()` over the committed graph-shaped fixture.

    Dispatches on query IDENTITY (the module's query constants), not by
    re-parsing Cypher -- this is a test-only shim, not a Cypher engine. Each
    branch reproduces exactly what the real label-scoped query would return
    against an equivalent live Neo4j graph.
    """

    def __init__(self, fixture: dict):
        self._nodes = {n["key"]: n for n in fixture["nodes"]}
        self._edges = fixture["edges"]

    def _props(self, key: str) -> dict:
        return self._nodes[key]["props"]

    def _labels(self, key: str) -> list:
        return self._nodes[key]["labels"]

    def _edges_of_type(self, edge_type: str, project: str):
        for edge in self._edges:
            if edge["type"] != edge_type:
                continue
            if self._props(edge["from"]).get("project") != project:
                continue
            yield edge

    def run(self, query: str, **params):
        project = params["project"]

        if query is oe.ONTOGRAPH_QUERY:
            rows = [
                {"labels": n["labels"], "props": n["props"]}
                for n in self._nodes.values()
                if n["props"].get("project") == project
                and set(n["labels"]) & {"Class", "DatatypeProperty", "ObjectProperty"}
            ]
            return _FakeResult(rows)

        if query is oe.METAGRAPH_QUERY:
            rows = [
                {"labels": n["labels"], "props": n["props"]}
                for n in self._nodes.values()
                if n["props"].get("project") == project
                and set(n["labels"]) & {"Rule", "Atom", "Var", "Literal", "Builtin"}
            ]
            return _FakeResult(rows)

        if query is oe.BODY_HEAD_QUERY:
            rows = []
            for edge in self._edges:
                if edge["type"] not in ("HAS_BODY", "HAS_HEAD"):
                    continue
                rule_props = self._props(edge["from"])
                if rule_props.get("project") != project:
                    continue
                rows.append({
                    "rule_id": rule_props["Rule_Id"],
                    "rel": edge["type"],
                    "ord": edge["props"]["order"],
                    "atom_id": self._props(edge["to"])["Atom_Id"],
                })
            return _FakeResult(rows)

        if query is oe.REFERS_QUERY:
            rows = []
            for edge in self._edges_of_type("REFERS_TO", project):
                target_props = self._props(edge["to"])
                rows.append({
                    "atom_id": self._props(edge["from"])["Atom_Id"],
                    "target_iri": target_props.get("iri"),
                })
            return _FakeResult(rows)

        if query is oe.ARG_QUERY:
            rows = []
            for edge in self._edges_of_type("ARG", project):
                rows.append({
                    "atom_id": self._props(edge["from"])["Atom_Id"],
                    "pos": edge["props"]["pos"],
                    "labels": self._labels(edge["to"]),
                    "props": self._props(edge["to"]),
                })
            return _FakeResult(rows)

        if query is oe.ATOM_COUNT_QUERY:
            count = sum(
                1 for n in self._nodes.values()
                if n["props"].get("project") == project and "Atom" in n["labels"]
            )
            return _FakeResult([{"n": count}])

        raise ValueError(f"FixtureSession: unrecognized query:\n{query}")


def _load_fixture() -> dict:
    return json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))


def _atom_iri(atom_id: str) -> URIRef:
    return oe.mint(PROJECT, "atom", atom_id)


def _rule_iri(rule_id: str) -> URIRef:
    return oe.mint(PROJECT, "rule", rule_id)


def _walk_list(graph: Graph, head) -> list:
    """Walk an rdf:first/rdf:rest chain (swrl:AtomList or plain rdf:List) into a Python list."""
    items = []
    node = head
    while node is not None and node != RDF.nil:
        items.append(graph.value(node, RDF.first))
        node = graph.value(node, RDF.rest)
    return items


@pytest.fixture(scope="module")
def turtle_graph() -> Graph:
    """Build via build_graph(), serialize to Turtle, parse it back (D-14 round-trip)."""
    fixture = _load_fixture()
    session = FixtureSession(fixture)
    built = oe.build_graph(session, PROJECT)
    turtle_text = built.serialize(format="turtle")

    parsed = Graph()
    parsed.parse(data=turtle_text, format="turtle")
    return parsed


def test_atom_count_guard_holds_for_fixture(turtle_graph):
    # build_graph() itself raises AssertionError on a Pitfall-1 mismatch --
    # the mere existence of `turtle_graph` (built by the module-scoped
    # fixture above) proves the exported-vs-independent atom count guard
    # passed for this fixture. This test also independently re-derives the
    # count from the raw fixture to document what "holds" means here.
    fixture = _load_fixture()
    atom_ids = {
        n["props"]["Atom_Id"] for n in fixture["nodes"]
        if n["props"].get("project") == PROJECT and "Atom" in n["labels"]
    }
    assert len(atom_ids) == 5  # a1, a2, a3, a5, and the deliberately-incomplete atom


def test_rule_is_swrl_imp_with_body_order_matching_has_body_order(turtle_graph):
    rule_iri = _rule_iri("R_BUILDING_MAX_STOREY_9_V")
    assert (rule_iri, RDF.type, oe.SWRL.Imp) in turtle_graph

    body_head = turtle_graph.value(rule_iri, oe.SWRL.body)
    body_atoms = _walk_list(turtle_graph, body_head)

    expected = [
        _atom_iri("R_BUILDING_MAX_STOREY_9_V_A1"),
        _atom_iri("R_BUILDING_MAX_STOREY_9_V_A2"),
        _atom_iri("R_BUILDING_MAX_STOREY_9_V_A3"),
    ]
    assert body_atoms == expected


def test_rule_head_order_matches_has_head_order(turtle_graph):
    rule_iri = _rule_iri("R_BUILDING_MAX_STOREY_9_V")
    head_head = turtle_graph.value(rule_iri, oe.SWRL.head)
    head_atoms = _walk_list(turtle_graph, head_head)
    assert head_atoms == [_atom_iri("R_BUILDING_MAX_STOREY_9_V_A5")]


def test_binary_atom_argument_positions_match_arg_pos(turtle_graph):
    a2 = _atom_iri("R_BUILDING_MAX_STOREY_9_V_A2")
    var_b = oe.mint(PROJECT, "var", "b")
    var_h = oe.mint(PROJECT, "var", "h")

    assert turtle_graph.value(a2, oe.SWRL.argument1) == var_b  # ARG pos:1
    assert turtle_graph.value(a2, oe.SWRL.argument2) == var_h  # ARG pos:2
    assert (a2, oe.SWRL.arguments, None) not in turtle_graph


def test_head_atom_argument2_is_typed_literal_matching_arg_pos(turtle_graph):
    a5 = _atom_iri("R_BUILDING_MAX_STOREY_9_V_A5")
    var_b = oe.mint(PROJECT, "var", "b")

    assert turtle_graph.value(a5, oe.SWRL.argument1) == var_b  # ARG pos:1
    assert turtle_graph.value(a5, oe.SWRL.argument2) == RDFLiteral(
        "true", datatype=oe.XSD.boolean
    )  # ARG pos:2


def test_builtin_atom_uses_swrl_arguments_not_argument1_2(turtle_graph):
    a3 = _atom_iri("R_BUILDING_MAX_STOREY_9_V_A3")
    assert (a3, RDF.type, oe.SWRL.BuiltinAtom) in turtle_graph
    assert (a3, oe.SWRL.argument1, None) not in turtle_graph
    assert (a3, oe.SWRL.argument2, None) not in turtle_graph

    args_head = turtle_graph.value(a3, oe.SWRL.arguments)
    assert args_head is not None
    args = _walk_list(turtle_graph, args_head)
    assert args == [
        oe.mint(PROJECT, "var", "h"),
        RDFLiteral("9", datatype=oe.XSD.integer),
    ]


def test_incomplete_atom_becomes_skipped_atom_and_is_excluded_from_swrl_imp(turtle_graph):
    incomplete_iri = _atom_iri("R_COLUMN_CONTINUITY_V_A3")
    assert (incomplete_iri, RDF.type, oe.DGM.SkippedAtom) in turtle_graph
    assert (incomplete_iri, RDF.type, oe.SWRL.BuiltinAtom) not in turtle_graph

    rule_iri = _rule_iri("R_BUILDING_MAX_STOREY_9_V")
    body_atoms = _walk_list(turtle_graph, turtle_graph.value(rule_iri, oe.SWRL.body))
    head_atoms = _walk_list(turtle_graph, turtle_graph.value(rule_iri, oe.SWRL.head))
    assert incomplete_iri not in body_atoms
    assert incomplete_iri not in head_atoms


def test_ontograph_class_and_datatype_property_are_declared(turtle_graph):
    assert (oe.EX.Building, RDF.type, OWL.Class) in turtle_graph
    assert (oe.EX.hasStoreyCount, RDF.type, OWL.DatatypeProperty) in turtle_graph
