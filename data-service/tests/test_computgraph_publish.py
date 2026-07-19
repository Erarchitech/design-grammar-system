"""Tests for the Computgraph publish endpoint (Phase 36-01: CGPD-01/02/03).

Follows the test_dg_identity.py header (sys.path.insert, LLM_MASTER_SECRET default,
TestClient(app, raise_server_exceptions=False)) and its duck-typed FakeGraph/FakeResult
session precedent -- extended here into a Computgraph-shaped in-memory store keyed by
(label, cgId|definitionId, project), dispatched by the `op=` comment tag each Cypher
statement computgraph_publish.py issues (`// op=PUBLISH_*`).

Cross-language parity anchor (reused from test_dg_identity.py): the dgId computed for
cgId "cg:1:proc:11_Proc" under (project "p1", definitionId "frame.gh") must equal
"dg:BC8E62EE137E2B56".
"""

from __future__ import annotations

import os
import re
import sys

import pytest
from fastapi.testclient import TestClient

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

os.environ.setdefault("LLM_MASTER_SECRET", "test-master-secret")

import app as app_module  # noqa: E402
import computgraph_publish  # noqa: E402
from app import app  # noqa: E402

client = TestClient(app, raise_server_exceptions=False)

# The exact dgId minted for this triple (cross-language parity anchor, reused from
# test_dg_identity.py's golden vector).
GOLDEN_PROJECT = "p1"
GOLDEN_DEFINITION_ID = "frame.gh"
GOLDEN_CG_ID = "cg:1:proc:11_Proc"
GOLDEN_DG_ID = "dg:BC8E62EE137E2B56"

_OP_RE = re.compile(r"op=(\w+)")

# Typed labels carry a `cgId` as their store key; Behavior/Algorithm use a
# definitionId/composite key instead and are excluded from the stale-cgId diff.
_TYPED_CGID_LABELS = {"Object", "Procedure", "Pattern", "Parameter", "Interface"}


class FakeResult:
    """Duck-types the slice of neo4j.Result the helpers use: .single() + iteration."""

    def __init__(self, rows: list[dict]):
        self._rows = list(rows)

    def single(self):
        return self._rows[0] if self._rows else None

    def __iter__(self):
        return iter(self._rows)


class FakeGraph:
    """Stateful in-memory Computgraph store dispatched by the `op=` tag on each
    Cypher statement. Nodes keyed by (label, cgId_or_definitionId, project);
    relationships recorded as (type, fromKey, toKey) tuples. Records every
    (op, params) call so tests can assert bound-parameter / no-untagged-write
    contracts.
    """

    def __init__(self):
        self.nodes: dict[tuple[str, str, str], dict] = {}
        self.relationships: list[tuple[str, tuple, tuple]] = []
        self.calls: list[tuple[str, dict]] = []

    def _set_node(self, label: str, key: str, project: str, props: dict) -> tuple:
        node_key = (label, key, project)
        merged = dict(self.nodes.get(node_key, {}))
        for k, v in props.items():
            if v is None:
                merged.pop(k, None)
            else:
                merged[k] = v
        self.nodes[node_key] = merged
        return node_key

    def execute(self, op: str, params: dict) -> list[dict]:
        self.calls.append((op, dict(params)))

        if op == "PUBLISH_OBJECT":
            key = self._set_node(
                "Object",
                params["cgId"],
                params["project"],
                {
                    "objectName": params["objectName"],
                    "classIri": params.get("classIri"),
                    "dgId": params["dgId"],
                    "source": params["source"],
                    "definitionId": params["definitionId"],
                    "fileName": params["fileName"],
                    "publishedAt": params["publishedAt"],
                    "graph": "Computgraph",
                    "project": params["project"],
                    "provider": params.get("provider"),
                    "model": params.get("model"),
                    "confidence": params.get("confidence"),
                },
            )
            if params.get("classIri"):
                self.relationships.append(
                    ("REFERS_TO", key, ("Class", params["classIri"], None))
                )
            return []

        if op == "PUBLISH_BEHAVIOR":
            key = self._set_node(
                "Behavior",
                params["definitionId"],
                params["project"],
                {
                    "graph": "Computgraph",
                    "project": params["project"],
                    "definitionId": params["definitionId"],
                    "publishedAt": params["publishedAt"],
                },
            )
            obj_key = ("Object", params["objectCgId"], params["project"])
            self.relationships.append(("HAS_BEHAVIOR", obj_key, key))
            return []

        if op == "PUBLISH_ALGORITHM":
            behavior_key = ("Behavior", params["definitionId"], params["project"])
            for row in params["rows"]:
                key = self._set_node(
                    "Algorithm",
                    f'{row["index"]}|{params["definitionId"]}',
                    params["project"],
                    {
                        "algorithmName": row["name"],
                        "contextJson": row["contextJson"],
                        "graph": "Computgraph",
                        "project": params["project"],
                        "definitionId": params["definitionId"],
                        "publishedAt": params["publishedAt"],
                    },
                )
                self.relationships.append(("HAS_ALGORITHM", behavior_key, key))
            return []

        if op == "PUBLISH_PROCEDURE":
            for row in params["rows"]:
                key = self._set_node(
                    "Procedure",
                    row["cgId"],
                    params["project"],
                    {
                        "procedureName": row["name"],
                        "procIndex": row["index"],
                        "dgId": row["dgId"],
                        "source": row["source"],
                        "provider": row.get("provider"),
                        "model": row.get("model"),
                        "confidence": row.get("confidence"),
                        "definitionId": params["definitionId"],
                        "fileName": params["fileName"],
                        "publishedAt": params["publishedAt"],
                        "graph": "Computgraph",
                        "project": params["project"],
                    },
                )
                alg_key = ("Algorithm", f'{row["algIndex"]}|{params["definitionId"]}', params["project"])
                self.relationships.append(("HAS_PROCEDURE", alg_key, key))
            return []

        if op == "PUBLISH_PATTERN":
            for row in params["rows"]:
                key = self._set_node(
                    "Pattern",
                    row["cgId"],
                    params["project"],
                    {
                        "patternName": row["name"],
                        "dgId": row["dgId"],
                        "source": row["source"],
                        "provider": row.get("provider"),
                        "model": row.get("model"),
                        "confidence": row.get("confidence"),
                        "definitionId": params["definitionId"],
                        "fileName": params["fileName"],
                        "publishedAt": params["publishedAt"],
                        "graph": "Computgraph",
                        "project": params["project"],
                    },
                )
                proc_key = ("Procedure", row["procCgId"], params["project"])
                self.relationships.append(("HAS_PATTERN", proc_key, key))
            return []

        if op == "PUBLISH_PATTERN_HOST":
            for row in params["rows"]:
                child_key = ("Pattern", row["childCgId"], params["project"])
                host_key = ("Pattern", row["hostCgId"], params["project"])
                self.relationships.append(("PATTERN_HOST_TO", child_key, host_key))
            return []

        if op == "PUBLISH_PARAMETER":
            for row in params["rows"]:
                key = self._set_node(
                    "Parameter",
                    row["cgId"],
                    params["project"],
                    {
                        "parameterName": row["name"],
                        "paramKind": row["kind"],
                        "dataType": row.get("dataType"),
                        "domainMin": row.get("domainMin"),
                        "domainMax": row.get("domainMax"),
                        "domainStep": row.get("domainStep"),
                        "dgId": row["dgId"],
                        "source": row["source"],
                        "provider": row.get("provider"),
                        "model": row.get("model"),
                        "confidence": row.get("confidence"),
                        "definitionId": params["definitionId"],
                        "fileName": params["fileName"],
                        "publishedAt": params["publishedAt"],
                        "graph": "Computgraph",
                        "project": params["project"],
                    },
                )
                proc_key = ("Procedure", row["procCgId"], params["project"])
                self.relationships.append(("HAS_PARAMETER", proc_key, key))
            return []

        if op == "PUBLISH_INTERFACE":
            for row in params["rows"]:
                key = self._set_node(
                    "Interface",
                    row["cgId"],
                    params["project"],
                    {
                        "interfaceName": row["name"],
                        "ifaceType": row["ifaceType"],
                        "dgId": row["dgId"],
                        "source": row["source"],
                        "provider": row.get("provider"),
                        "model": row.get("model"),
                        "confidence": row.get("confidence"),
                        "definitionId": params["definitionId"],
                        "fileName": params["fileName"],
                        "publishedAt": params["publishedAt"],
                        "graph": "Computgraph",
                        "project": params["project"],
                    },
                )
                proc_key = ("Procedure", row["procCgId"], params["project"])
                self.relationships.append(("HAS_INTERFACE", proc_key, key))
            return []

        if op == "PUBLISH_PARAM_LINK":
            for row in params["rows"]:
                param_key = ("Parameter", row["paramCgId"], params["project"])
                iface_key = ("Interface", row["interfaceCgId"], params["project"])
                self.relationships.append(("PARAM_LINK", param_key, iface_key))
            return []

        if op == "PUBLISH_STALE_DIFF":
            current = set(params["currentCgIds"])
            stale = [
                key[1]
                for key in self.nodes
                if key[0] in _TYPED_CGID_LABELS
                and key[2] == params["project"]
                and self.nodes[key].get("definitionId") == params["definitionId"]
                and key[1] not in current
            ]
            return [{"cgId": cg_id} for cg_id in stale]

        return []


class FixtureSession:
    """Duck-typed neo4j Session over a shared FakeGraph. Also a context manager.

    `execute_write` mirrors the real neo4j driver's explicit-transaction API: the
    passed function receives a `tx` object (here, `self` -- it exposes the same
    `.run()`), and every `tx.run()` call inside it is part of ONE transaction.
    """

    def __init__(self, graph: FakeGraph):
        self.graph = graph
        self.last_params: dict | None = None

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False

    def run(self, query: str, parameters: dict | None = None, **kwargs):
        params = dict(parameters or {})
        params.update(kwargs)
        self.last_params = params
        match = _OP_RE.search(query)
        op = match.group(1) if match else ""
        return FakeResult(self.graph.execute(op, params))

    def execute_write(self, func):
        return func(self)


class FakeDriver:
    """Duck-typed neo4j Driver whose .session() yields a FixtureSession over one graph."""

    def __init__(self, graph: FakeGraph):
        self.graph = graph

    def session(self):
        return FixtureSession(self.graph)


@pytest.fixture
def registry(monkeypatch):
    """Fresh in-memory Computgraph store, wired into app.driver so the HTTP route uses it."""
    graph = FakeGraph()
    monkeypatch.setattr(app_module, "driver", FakeDriver(graph))
    return graph


def _frame_cg_context(project: str = GOLDEN_PROJECT, definition_id: str = GOLDEN_DEFINITION_ID) -> dict:
    """A trimmed cgContextJson v1 envelope for the Frame fixture: 1 Object, 1
    Algorithm (index 1), 2 Procedures (11_Proc tagged / 12_Proc recognized), each
    with 1 Pattern/Parameter/Interface. One wire links the tagged Parameter's
    member to the tagged Interface's member (PARAM_LINK derivation). `untagged`
    carries distinct ids that must never reach the published store.
    """
    return {
        "schemaVersion": "cg-context-1",
        "project": project,
        "definition": {
            "documentId": definition_id,
            "fileName": "frame.gh",
            "capturedAt": "2026-07-08T00:00:00.0000000Z",
        },
        "object": {
            "name": "FRAME",
            "classIri": None,
            "source": "tagged",
            "dgId": None,
        },
        "algorithms": [
            {
                "index": 1,
                "name": "1_ALGORITHM",
                "procedures": [
                    {
                        "id": GOLDEN_CG_ID,
                        "index": 11,
                        "name": "11_Proc",
                        "source": "tagged",
                        "dgId": None,
                        "memberIds": [],
                        "patterns": [
                            {
                                "id": "cg:1:pat:11_Pat_DivideLine",
                                "label": "Pat",
                                "name": "DivideLine",
                                "hostPatternId": None,
                                "memberIds": ["n-divide-curve"],
                                "source": "tagged",
                                "dgId": None,
                            }
                        ],
                        "parameters": [
                            {
                                "id": "cg:1:param:11_Var_SpansCount",
                                "kind": "Variable",
                                "name": "SpansCount",
                                "dataType": "Integer",
                                "domain": {"min": 1, "max": 20, "step": 1},
                                "memberIds": ["n-spanscount"],
                                "source": "tagged",
                                "dgId": None,
                            }
                        ],
                        "interfaces": [
                            {
                                "id": "cg:1:intf:11_IntF_ParSplitAt",
                                "name": "ParSplitAt",
                                "ifaceType": "Input",
                                "memberIds": ["n-parsplit"],
                                "source": "tagged",
                                "dgId": None,
                            }
                        ],
                    },
                    {
                        "id": "cg:1:proc:12_Proc",
                        "index": 12,
                        "name": "12_Proc",
                        "source": "recognized",
                        "dgId": None,
                        "memberIds": [],
                        "provider": "anthropic",
                        "model": "claude-sonnet",
                        "confidence": 0.87,
                        "patterns": [
                            {
                                "id": "cg:1:pat:12_Pat_FooterBottom",
                                "label": "Pat",
                                "name": "FooterBottom",
                                "hostPatternId": None,
                                "memberIds": ["n-footer-bottom"],
                                "source": "recognized",
                                "provider": "anthropic",
                                "model": "claude-sonnet",
                                "confidence": 0.81,
                                "dgId": None,
                            }
                        ],
                        "parameters": [
                            {
                                "id": "cg:1:param:12_Var_HFooter",
                                "kind": "Variable",
                                "name": "HFooter",
                                "dataType": "Float",
                                "domain": None,
                                "memberIds": ["n-hfooter"],
                                "source": "recognized",
                                "provider": "anthropic",
                                "model": "claude-sonnet",
                                "confidence": 0.75,
                                "dgId": None,
                            }
                        ],
                        "interfaces": [
                            {
                                "id": "cg:1:intf:12_IntF_FooterFrame",
                                "name": "FooterFrame",
                                "ifaceType": "Output",
                                "memberIds": ["n-footerframe-intf"],
                                "source": "recognized",
                                "provider": "anthropic",
                                "model": "claude-sonnet",
                                "confidence": 0.79,
                                "dgId": None,
                            }
                        ],
                    },
                ],
            }
        ],
        "untagged": {
            "nodeIds": ["n-untagged-01"],
            "groups": [
                {"nickname": "Scratch notes", "memberIds": ["n-scratch-01", "n-scratch-02"]},
            ],
        },
        "nodes": [],
        "wires": [
            {"fromNode": "n-spanscount", "fromParam": "out0", "toNode": "n-parsplit", "toParam": "in0"},
        ],
        "warnings": [],
    }


# ── CGPD-01: publish yields the full labeled/relationship subgraph, project-scoped ──


def test_publish_frame_structure():
    graph = FakeGraph()
    session = FixtureSession(graph)
    cg_context = _frame_cg_context()

    result = computgraph_publish.publish_structure(session, GOLDEN_PROJECT, cg_context)

    assert result["status"] == "published"
    counts = result["publishedCounts"]
    assert counts["object"] == 1
    assert counts["algorithms"] == 1
    assert counts["procedures"] == 2
    assert counts["patterns"] == 2
    assert counts["parameters"] == 2
    assert counts["interfaces"] == 2

    assert ("Object", "obj:FRAME", GOLDEN_PROJECT) in graph.nodes
    assert ("Behavior", GOLDEN_DEFINITION_ID, GOLDEN_PROJECT) in graph.nodes
    assert ("Algorithm", f"1|{GOLDEN_DEFINITION_ID}", GOLDEN_PROJECT) in graph.nodes
    assert ("Procedure", GOLDEN_CG_ID, GOLDEN_PROJECT) in graph.nodes
    assert ("Procedure", "cg:1:proc:12_Proc", GOLDEN_PROJECT) in graph.nodes
    assert ("Pattern", "cg:1:pat:11_Pat_DivideLine", GOLDEN_PROJECT) in graph.nodes
    assert ("Parameter", "cg:1:param:11_Var_SpansCount", GOLDEN_PROJECT) in graph.nodes
    assert ("Interface", "cg:1:intf:11_IntF_ParSplitAt", GOLDEN_PROJECT) in graph.nodes

    for key, props in graph.nodes.items():
        assert props["graph"] == "Computgraph"
        assert props["project"] == GOLDEN_PROJECT

    rel_types = {r[0] for r in graph.relationships}
    assert {
        "HAS_BEHAVIOR",
        "HAS_ALGORITHM",
        "HAS_PROCEDURE",
        "HAS_PATTERN",
        "HAS_PARAMETER",
        "HAS_INTERFACE",
        "PARAM_LINK",
    } <= rel_types

    assert (
        "PARAM_LINK",
        ("Parameter", "cg:1:param:11_Var_SpansCount", GOLDEN_PROJECT),
        ("Interface", "cg:1:intf:11_IntF_ParSplitAt", GOLDEN_PROJECT),
    ) in graph.relationships


# ── CGPD-02: re-publish is MERGE-idempotent ──


def test_republish_is_idempotent():
    graph = FakeGraph()
    session = FixtureSession(graph)
    cg_context = _frame_cg_context()

    computgraph_publish.publish_structure(session, GOLDEN_PROJECT, cg_context)
    keys_before = set(graph.nodes.keys())
    count_before = len(graph.nodes)

    computgraph_publish.publish_structure(session, GOLDEN_PROJECT, cg_context)
    keys_after = set(graph.nodes.keys())

    assert keys_after == keys_before
    assert len(graph.nodes) == count_before


# ── CGPD-03: every typed node carries queryable provenance ──


def test_provenance_properties_present():
    graph = FakeGraph()
    session = FixtureSession(graph)
    cg_context = _frame_cg_context()

    computgraph_publish.publish_structure(session, GOLDEN_PROJECT, cg_context)

    tagged = graph.nodes[("Procedure", GOLDEN_CG_ID, GOLDEN_PROJECT)]
    assert tagged["source"] == "tagged"
    assert tagged["definitionId"] == GOLDEN_DEFINITION_ID
    assert tagged["fileName"] == "frame.gh"
    assert tagged["publishedAt"]
    assert "provider" not in tagged
    assert "model" not in tagged
    assert "confidence" not in tagged

    recognized = graph.nodes[("Procedure", "cg:1:proc:12_Proc", GOLDEN_PROJECT)]
    assert recognized["source"] == "recognized"
    assert recognized["definitionId"] == GOLDEN_DEFINITION_ID
    assert recognized["fileName"] == "frame.gh"
    assert recognized["publishedAt"]
    assert recognized["provider"] == "anthropic"
    assert recognized["model"] == "claude-sonnet"
    assert recognized["confidence"] == 0.87


# ── dgId inline-compute parity with the golden vector ──


def test_dgid_matches_golden_vector():
    graph = FakeGraph()
    session = FixtureSession(graph)
    cg_context = _frame_cg_context()

    computgraph_publish.publish_structure(session, GOLDEN_PROJECT, cg_context)

    proc = graph.nodes[("Procedure", GOLDEN_CG_ID, GOLDEN_PROJECT)]
    assert proc["dgId"] == GOLDEN_DG_ID


# ── T-36-02: untagged entities never reach the published store ──


def test_untagged_never_published():
    graph = FakeGraph()
    session = FixtureSession(graph)
    cg_context = _frame_cg_context()

    computgraph_publish.publish_structure(session, GOLDEN_PROJECT, cg_context)

    published_ids = {key[1] for key in graph.nodes}
    for node_id in cg_context["untagged"]["nodeIds"]:
        assert node_id not in published_ids
    for group in cg_context["untagged"]["groups"]:
        for member_id in group["memberIds"]:
            assert member_id not in published_ids

    for _op, params in graph.calls:
        serialized = repr(params)
        assert "n-untagged-01" not in serialized
        assert "n-scratch-01" not in serialized
        assert "n-scratch-02" not in serialized
