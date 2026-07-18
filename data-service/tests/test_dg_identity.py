"""Tests for the cross-platform identity registry (Phase 32.1-03: DGID-02/03/05).

Follows the test_dg_context.py header (sys.path.insert, LLM_MASTER_SECRET default,
TestClient(app, raise_server_exceptions=False)) and its duck-typed FixtureSession
precedent — but here the fixture is a *stateful* in-memory registry so bind→resolve
round-trips, detach-frees-binding, and the anti-misbinding guard are exercised with
zero live Neo4j.

Cross-language parity anchor: compute_dg_id must equal the golden vector minted by
DG.Core DgIdMintingService.Mint (Convert.ToHexString → UPPERCASE hex, first 16). The
literal below is reproduced from the documented contract SHA-256(project|definitionId|
cgId) → dg:+first16hex-uppercase and was cross-checked against DG/src/DG.Core/Models/
Identity/DgIdMintingService.cs directly.
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
import dg_identity  # noqa: E402
from app import app  # noqa: E402

client = TestClient(app, raise_server_exceptions=False)

# The exact dgId minted by DG.Core for this triple (cross-language parity anchor).
GOLDEN_PROJECT = "p1"
GOLDEN_DEFINITION_ID = "frame.gh"
GOLDEN_CG_ID = "cg:1:proc:11_Proc"
GOLDEN_DG_ID = "dg:BC8E62EE137E2B56"

_OP_RE = re.compile(r"op=(\w+)")


class FakeResult:
    """Duck-types the slice of neo4j.Result the helpers use: .single() + iteration."""

    def __init__(self, rows: list[dict]):
        self._rows = list(rows)

    def single(self):
        return self._rows[0] if self._rows else None

    def __iter__(self):
        return iter(self._rows)


class FakeGraph:
    """Stateful in-memory registry keyed by the `op=` tag on each Cypher statement.

    Models entities (dgId ↔ project) and Representation nodes so the identity helpers
    run end-to-end with no live Neo4j. Records every (op, query, params) call so tests
    can assert the bound-parameter and no-entity-write contracts.
    """

    def __init__(self):
        self.entity_by_dgid: dict[tuple[str, str], bool] = {}
        self.reps: list[dict] = []
        self.rep_index: dict[tuple[str, str, str], dict] = {}
        self.calls: list[tuple[str, str, dict]] = []

    def execute(self, op: str, query: str, params: dict) -> list[dict]:
        self.calls.append((op, query, dict(params)))
        if op == "MINT":
            self.entity_by_dgid[(params["dgId"], params["project"])] = True
            return []
        if op == "RESOLVE":
            for r in self.reps:
                if (
                    r["nativeId"] == params["nativeId"]
                    and r["platform"] == params["platform"]
                    and r["project"] == params["project"]
                ):
                    return [{"dgId": r["dgId"]}]
            return []
        if op == "ENTITY_CHECK":
            if self.entity_by_dgid.get((params["dgId"], params["project"])):
                return [{"dgId": params["dgId"]}]
            return []
        if op == "BIND":
            key = (params["nativeId"], params["platform"], params["project"])
            if key not in self.rep_index:
                rep = {
                    "nativeId": params["nativeId"],
                    "platform": params["platform"],
                    "project": params["project"],
                    "nativeIdKind": params["nativeIdKind"],
                    "connector": params["connector"],
                    "boundAt": "2026-01-01T00:00:00Z",
                    "dgId": params["dgId"],
                }
                self.reps.append(rep)
                self.rep_index[key] = rep
            return []
        if op == "LIST":
            return [
                {
                    "platform": r["platform"],
                    "native_id_kind": r["nativeIdKind"],
                    "native_id": r["nativeId"],
                    "connector": r["connector"],
                    "bound_at": r["boundAt"],
                }
                for r in self.reps
                if r["dgId"] == params["dgId"] and r["project"] == params["project"]
            ]
        if op == "DETACH_COUNT":
            n = sum(
                1
                for r in self.reps
                if r["dgId"] == params["dgId"]
                and r["platform"] == params["platform"]
                and r["nativeId"] == params["nativeId"]
                and r["project"] == params["project"]
            )
            return [{"cnt": n}]
        if op == "DETACH":
            remaining = []
            for r in self.reps:
                if (
                    r["dgId"] == params["dgId"]
                    and r["platform"] == params["platform"]
                    and r["nativeId"] == params["nativeId"]
                    and r["project"] == params["project"]
                ):
                    self.rep_index.pop(
                        (r["nativeId"], r["platform"], r["project"]), None
                    )
                    continue
                remaining.append(r)
            self.reps = remaining
            return []
        return []


class FixtureSession:
    """Duck-typed neo4j Session over a shared FakeGraph. Also a context manager."""

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
        return FakeResult(self.graph.execute(op, query, params))


class FakeDriver:
    """Duck-typed neo4j Driver whose .session() yields a FixtureSession over one graph."""

    def __init__(self, graph: FakeGraph):
        self.graph = graph

    def session(self):
        return FixtureSession(self.graph)


@pytest.fixture
def registry(monkeypatch):
    """Fresh in-memory registry, wired into app.driver so the HTTP routes use it."""
    graph = FakeGraph()
    monkeypatch.setattr(app_module, "driver", FakeDriver(graph))
    return graph


def _session(graph: FakeGraph) -> FixtureSession:
    return FixtureSession(graph)


# ── compute_dg_id parity (cross-language golden vector) ──


def test_compute_dg_id_matches_dotnet_golden_vector():
    """compute_dg_id reproduces the exact DG.Core DgIdMintingService golden vector.

    Cross-language parity anchor — must equal the DgIdMintingServiceTests golden
    vector (SHA-256 uppercase hex, first 16, dg: prefix).
    """
    assert (
        dg_identity.compute_dg_id(GOLDEN_PROJECT, GOLDEN_DEFINITION_ID, GOLDEN_CG_ID)
        == GOLDEN_DG_ID
    )


def test_compute_dg_id_project_scopes_the_hash():
    """A different project for the same definitionId+cgId yields a distinct dgId."""
    a = dg_identity.compute_dg_id("p1", GOLDEN_DEFINITION_ID, GOLDEN_CG_ID)
    b = dg_identity.compute_dg_id("p2", GOLDEN_DEFINITION_ID, GOLDEN_CG_ID)
    assert a != b


# ── mint idempotency ──


def test_mint_identity_idempotent(registry):
    """Two mints of the same triple return the same dgId; the MERGE is parameterized."""
    session = _session(registry)
    first = dg_identity.mint_identity(session, GOLDEN_PROJECT, GOLDEN_DEFINITION_ID, GOLDEN_CG_ID)
    second = dg_identity.mint_identity(session, GOLDEN_PROJECT, GOLDEN_DEFINITION_ID, GOLDEN_CG_ID)
    assert first == second == GOLDEN_DG_ID
    # project threaded as a bound parameter on the mint MERGE (T-32.1-03c)
    assert session.last_params is not None and "project" in session.last_params
    # only one entity row upserted — idempotent, not duplicated
    assert len(registry.entity_by_dgid) == 1


# ── cross-platform same-dgId resolution (DGID-03) ──


def test_cross_platform_bind_resolve_same_dgId(registry):
    """A Grasshopper InstanceGuid and a Revit UniqueId bound to one dgId both resolve to it."""
    session = _session(registry)
    dg_id = dg_identity.mint_identity(session, "proj", "wall.gh", "cg:1:obj:wall")

    dg_identity.bind_representation(
        session, dg_id, "Grasshopper", "InstanceGuid", "gh-guid-1", "grasshopper", "proj"
    )
    dg_identity.bind_representation(
        session, dg_id, "Revit", "UniqueId", "revit-uid-1", "revit", "proj"
    )

    assert dg_identity.resolve_native_id(session, "Grasshopper", "gh-guid-1", "proj") == dg_id
    assert dg_identity.resolve_native_id(session, "Revit", "revit-uid-1", "proj") == dg_id


# ── anti-misbinding guard (T-32.1-03b, DGID-05) ──


def test_ambiguous_bind_rejected(registry):
    """Binding a native id already bound to a DIFFERENT dgId returns HTTP 409, never a repoint."""
    session = _session(registry)
    dg_a = dg_identity.mint_identity(session, "proj", "a.gh", "cg:1:obj:a")
    dg_b = dg_identity.mint_identity(session, "proj", "b.gh", "cg:1:obj:b")
    assert dg_a != dg_b

    dg_identity.bind_representation(
        session, dg_a, "Grasshopper", "InstanceGuid", "shared-guid", "grasshopper", "proj"
    )

    resp = client.post(
        "/identity/bind",
        json={
            "dg_id": dg_b,
            "platform": "Grasshopper",
            "native_id_kind": "InstanceGuid",
            "native_id": "shared-guid",
            "connector": "grasshopper",
            "project": "proj",
        },
    )
    assert resp.status_code == 409
    assert resp.json()["detail"]["code"] == "DGID_AMBIGUOUS_BINDING"
    # the native id is still bound to dg_a — no silent repoint
    assert dg_identity.resolve_native_id(session, "Grasshopper", "shared-guid", "proj") == dg_a


# ── detach preserves dgId + frees the binding (DGID-02) ──


def test_detach_preserves_dgid_and_frees_binding(registry):
    """Detach removes only the representation; dgId is untouched; native id re-binds (to a different dgId)."""
    session = _session(registry)
    dg_a = dg_identity.mint_identity(session, "proj", "a.gh", "cg:1:obj:a")
    dg_b = dg_identity.mint_identity(session, "proj", "b.gh", "cg:1:obj:b")

    dg_identity.bind_representation(
        session, dg_a, "Grasshopper", "InstanceGuid", "guid-x", "grasshopper", "proj"
    )

    resp = client.delete(
        f"/identity/{dg_a}/representations",
        params={"platform": "Grasshopper", "native_id": "guid-x", "project": "proj"},
    )
    assert resp.status_code == 200
    assert resp.json() == {"detached": True}

    # (a) the entity dgId is untouched: no detach-op query wrote the entity node
    detach_queries = [q for (op, q, _p) in registry.calls if op == "DETACH"]
    assert detach_queries, "expected a DETACH-tagged query"
    for q in detach_queries:
        assert "SET " not in q and "e.dgId =" not in q
    assert registry.entity_by_dgid.get((dg_a, "proj")) is True

    # (b) resolve for the freed native id now misses
    assert dg_identity.resolve_native_id(session, "Grasshopper", "guid-x", "proj") is None

    # (c) the freed native id re-binds — even to a DIFFERENT dgId — without a 409
    rebind = client.post(
        "/identity/bind",
        json={
            "dg_id": dg_b,
            "platform": "Grasshopper",
            "native_id_kind": "InstanceGuid",
            "native_id": "guid-x",
            "connector": "grasshopper",
            "project": "proj",
        },
    )
    assert rebind.status_code == 200
    assert dg_identity.resolve_native_id(session, "Grasshopper", "guid-x", "proj") == dg_b


def test_detach_unknown_binding_returns_not_found(registry):
    """DELETE for a never-bound native id surfaces a structured 404 DGID_NOT_FOUND."""
    resp = client.delete(
        "/identity/dg:DEADBEEFDEADBEEF/representations",
        params={"platform": "Grasshopper", "native_id": "never-bound", "project": "proj"},
    )
    assert resp.status_code == 404
    assert resp.json()["detail"]["code"] == "DGID_NOT_FOUND"


# ── project isolation (T-32.1-03c) ──


def test_resolve_is_project_scoped(registry):
    """A binding under project p1 never leaks to a resolve under project p2."""
    session = _session(registry)
    dg_id = dg_identity.mint_identity(session, "p1", "a.gh", "cg:1:obj:a")
    dg_identity.bind_representation(
        session, dg_id, "Grasshopper", "InstanceGuid", "guid-iso", "grasshopper", "p1"
    )

    # helper-level: p2 resolve misses
    assert dg_identity.resolve_native_id(session, "Grasshopper", "guid-iso", "p2") is None

    # route-level: p2 resolve returns a structured 404, no p1 dgId leaks
    resp = client.get(
        "/identity/resolve",
        params={"platform": "Grasshopper", "native_id": "guid-iso", "project": "p2"},
    )
    assert resp.status_code == 404
    assert dg_id not in resp.text


def test_resolve_miss_returns_dgid_not_found(registry):
    """An unbound native id surfaces a structured 404 DGID_NOT_FOUND via the route."""
    resp = client.get(
        "/identity/resolve",
        params={"platform": "Revit", "native_id": "unbound", "project": "proj"},
    )
    assert resp.status_code == 404
    assert resp.json()["detail"]["code"] == "DGID_NOT_FOUND"


# ── list representations round-trip ──


def test_list_representations_round_trip(registry):
    """GET /identity/{dg_id}/representations returns every bound representation."""
    session = _session(registry)
    dg_id = dg_identity.mint_identity(session, "proj", "a.gh", "cg:1:obj:a")
    dg_identity.bind_representation(
        session, dg_id, "Grasshopper", "InstanceGuid", "g1", "grasshopper", "proj"
    )
    dg_identity.bind_representation(
        session, dg_id, "Revit", "UniqueId", "r1", "revit", "proj"
    )

    resp = client.get(f"/identity/{dg_id}/representations", params={"project": "proj"})
    assert resp.status_code == 200
    platforms = {row["platform"] for row in resp.json()}
    assert platforms == {"Grasshopper", "Revit"}
