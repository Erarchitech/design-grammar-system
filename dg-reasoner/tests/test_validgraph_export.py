"""Unit tests for dg-reasoner/valid_graph_export.py (D-04/D-05, Phase 823 Plan 01).

Runs entirely offline -- no docker, no live Neo4j. `FixtureSession` and the
small edge-case session shims below duck-type the `neo4j.Session.run()`
contract `build_valid_graph()` expects, mirroring the exact
`FixtureSession`/`_FakeResult` pattern established in
`dg-reasoner/tests/test_ontology_export.py`. Dispatch is by query IDENTITY
(the module's query constants), not Cypher re-parsing -- test-only shim, not
a Cypher engine.

RED state (before Task 2's implementation lands): every test below fails
with an ImportError/ModuleNotFoundError because `valid_graph_export` does
not exist yet -- proving these tests exercise real code, not vacuous
assertions.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from rdflib import Graph, Literal as RDFLiteral, URIRef
from rdflib.namespace import OWL, RDF, RDFS, XSD

import valid_graph_export as vge  # noqa: E402  (module under test -- RED until Task 2)

FIXTURE_PATH = Path(__file__).resolve().parent / "fixtures" / "valid_graph_fixture.json"
PROJECT = "fixture-proj"
RUN_ID = "RUN_001"


class _FakeResult(list):
    """Mimics `neo4j.Result`: iterable, plus `.single()` for scalar queries."""

    def single(self):
        return self[0] if self else None


class FixtureSession:
    """Duck-types `neo4j.Session.run()` over the committed valid_graph_fixture.json.

    Dispatches on query IDENTITY (`valid_graph_export.RUN_QUERY` /
    `.DESIGNSTATE_QUERY`), exactly mirroring `test_ontology_export.py`'s
    `FixtureSession`.
    """

    def __init__(self, fixture: dict):
        self._fixture = fixture

    def run(self, query: str, **params):
        project = params.get("project")

        if query is vge.RUN_QUERY:
            run_id = params.get("runId")
            if project == self._fixture.get("project") and run_id == self._fixture.get("runId"):
                row = {
                    "statePayloadJson": self._fixture.get("statePayloadJson"),
                    "validStatus": self._fixture.get("validStatus"),
                    "sendStatus": self._fixture.get("sendStatus"),
                }
                return _FakeResult([row])
            return _FakeResult([])

        if query is vge.DESIGNSTATE_QUERY:
            # Current live data never carries DesignState/Run graph nodes
            # (cypher_template.txt: document-only) -- this branch is a
            # deliberate no-op per the defensive label-scoped read mandate.
            return _FakeResult([])

        raise ValueError(f"FixtureSession: unrecognized query:\n{query}")


class EmptyPayloadSession:
    """Run row exists but `statePayloadJson` is null -- must not raise (D-04)."""

    def run(self, query: str, **params):
        if query is vge.RUN_QUERY:
            return _FakeResult([{"statePayloadJson": None, "validStatus": None, "sendStatus": None}])
        if query is vge.DESIGNSTATE_QUERY:
            return _FakeResult([])
        raise ValueError(f"EmptyPayloadSession: unrecognized query:\n{query}")


class MissingRunSession:
    """No `ValidationRun` row at all for the requested (project, runId) -- must not raise."""

    def run(self, query: str, **params):
        if query is vge.RUN_QUERY:
            return _FakeResult([])
        if query is vge.DESIGNSTATE_QUERY:
            return _FakeResult([])
        raise ValueError(f"MissingRunSession: unrecognized query:\n{query}")


def _load_fixture() -> dict:
    return json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))


def _walk_list(graph: Graph, head) -> list:
    """Walk an rdf:first/rdf:rest chain into a Python list."""
    items = []
    node = head
    while node is not None and node != RDF.nil:
        items.append(graph.value(node, RDF.first))
        node = graph.value(node, RDF.rest)
    return items


@pytest.fixture(scope="module")
def built_graph():
    """Build via build_valid_graph(), serialize to Turtle, parse it back (D-14-style round-trip)."""
    fixture = _load_fixture()
    session = FixtureSession(fixture)
    graph, minted = vge.build_valid_graph(session, PROJECT, RUN_ID)
    turtle_text = graph.serialize(format="turtle")

    parsed = Graph()
    parsed.parse(data=turtle_text, format="turtle")
    return parsed, minted


def test_fixture_envelope_has_all_three_state_kinds():
    fixture = _load_fixture()
    envelope = json.loads(fixture["statePayloadJson"])
    assert envelope["objStates"]
    assert envelope["paramStates"]
    assert envelope["propStates"]


def test_exactly_one_of_each_state_kind_and_run(built_graph):
    graph, _minted = built_graph
    assert len(list(graph.subjects(RDF.type, vge.DGV.ObjState))) == 1
    assert len(list(graph.subjects(RDF.type, vge.DGV.ParamState))) == 1
    assert len(list(graph.subjects(RDF.type, vge.DGV.PropState))) == 1
    assert len(list(graph.subjects(RDF.type, vge.DGV.Run))) == 1


def test_state_individual_iris_match_mint_and_carry_labels(built_graph):
    graph, _minted = built_graph

    obj_iri = vge.mint(PROJECT, "state", "OS_obj001")
    assert (obj_iri, RDF.type, vge.DGV.ObjState) in graph
    assert graph.value(obj_iri, RDFS.label) is not None

    param_iri = vge.mint(PROJECT, "state", "DS_param001")
    assert (param_iri, RDF.type, vge.DGV.ParamState) in graph
    assert graph.value(param_iri, RDFS.label) is not None

    prop_iri = vge.mint(PROJECT, "state", "PS_prop001")
    assert (prop_iri, RDF.type, vge.DGV.PropState) in graph
    assert graph.value(prop_iri, RDFS.label) is not None


def test_run_individual_carries_send_and_valid_status(built_graph):
    graph, _minted = built_graph

    run_iri = vge.mint(PROJECT, "run", RUN_ID)
    assert (run_iri, RDF.type, vge.DGV.Run) in graph
    assert graph.value(run_iri, vge.DGV.sendStatus) == RDFLiteral(True, datatype=XSD.boolean)

    valid_status_head = graph.value(run_iri, vge.DGV.validStatus)
    assert valid_status_head is not None
    items = _walk_list(graph, valid_status_head)
    assert items == [
        RDFLiteral(True, datatype=XSD.boolean),
        RDFLiteral(False, datatype=XSD.boolean),
    ]


def test_has_state_links_parent_designstate_to_each_child(built_graph):
    graph, _minted = built_graph

    parent_iri = vge.mint(PROJECT, "state", "DS_root001")
    children = set(graph.objects(parent_iri, vge.DGV.hasState))
    assert children == {
        vge.mint(PROJECT, "state", "OS_obj001"),
        vge.mint(PROJECT, "state", "DS_param001"),
        vge.mint(PROJECT, "state", "PS_prop001"),
    }


def test_all_different_covers_every_minted_individual(built_graph):
    graph, minted = built_graph

    all_diff_nodes = list(graph.subjects(RDF.type, OWL.AllDifferent))
    assert len(all_diff_nodes) == 1

    members_head = graph.value(all_diff_nodes[0], OWL.distinctMembers)
    members = _walk_list(graph, members_head)
    assert len(members) == len(minted) == 4
    assert set(members) == set(minted)


def test_missing_state_payload_json_does_not_raise_and_yields_zero_state_individuals():
    graph, _minted = vge.build_valid_graph(EmptyPayloadSession(), PROJECT, RUN_ID)
    assert len(list(graph.subjects(RDF.type, vge.DGV.ObjState))) == 0
    assert len(list(graph.subjects(RDF.type, vge.DGV.ParamState))) == 0
    assert len(list(graph.subjects(RDF.type, vge.DGV.PropState))) == 0


def test_missing_run_row_does_not_raise_and_yields_zero_state_individuals():
    graph, _minted = vge.build_valid_graph(MissingRunSession(), PROJECT, "NOPE")
    assert len(list(graph.subjects(RDF.type, vge.DGV.ObjState))) == 0
    assert len(list(graph.subjects(RDF.type, vge.DGV.ParamState))) == 0
    assert len(list(graph.subjects(RDF.type, vge.DGV.PropState))) == 0


def test_add_all_different_is_noop_on_empty_list():
    graph = Graph()
    vge.add_all_different(graph, [])
    assert len(list(graph.subjects(RDF.type, OWL.AllDifferent))) == 0


def test_add_all_different_emits_distinct_members_list():
    graph = Graph()
    individuals = [URIRef("http://example.org/a"), URIRef("http://example.org/b")]
    vge.add_all_different(graph, individuals)

    all_diff_nodes = list(graph.subjects(RDF.type, OWL.AllDifferent))
    assert len(all_diff_nodes) == 1
    members = _walk_list(graph, graph.value(all_diff_nodes[0], OWL.distinctMembers))
    assert members == individuals
