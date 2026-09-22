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
#
# Re-derived Phase 1203-02 (D-09 length-prefix encoding replaces the naive pipe-join): the
# pre-fix value was "dg:BC8E62EE137E2B56"; this is the post-fix value under the final
# EncodeHashInput / _encode_hash_input contract. DgIdMintingServiceTests.cs's
# Mint_KnownVector_MatchesExpectedDgId and test_computgraph_publish.py's GOLDEN_DG_ID were
# updated to the same value in the same commit.
GOLDEN_PROJECT = "p1"
GOLDEN_DEFINITION_ID = "frame.gh"
GOLDEN_CG_ID = "cg:1:proc:11_Proc"
GOLDEN_DG_ID = "dg:0F31CD18542F0252"

_OP_RE = re.compile(r"op=(\w+)")

# Extracts the entity label from mint_identity's anchor MERGE, e.g.
# "MERGE (e:Object {cgId: $cgId, ...})" -> "Object". Empty string if the anchor
# carries no label at all (the pre-fix, label-less shape this regression guards
# against) -- (?:) makes the label group optional so the pattern still matches
# the old "MERGE (e {cgId: ...})" shape without erroring.
_MINT_LABEL_RE = re.compile(r"MERGE\s*\(\s*e\s*(?::(\w+))?\s*\{")


def _extract_mint_label(query: str) -> str:
    match = _MINT_LABEL_RE.search(query)
    return (match.group(1) if match and match.group(1) else "") or ""


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
        # Shared properties keyed by (dgid, property_name, project)
        self.shared_props: dict[tuple[str, str, str], dict] = {}
        # Full node-identity store (label, cgId, definitionId, project) -> node dict.
        # Unlike entity_by_dgid (keyed only by dgId, which can't distinguish a
        # labelled node from a label-less one occupying the "same" logical anchor),
        # this models real Neo4j MERGE semantics: two MERGEs coincide on ONE node
        # only if their (label, key-properties) match exactly. This is what lets
        # the CR-01 regression prove "one node" vs "two nodes" rather than just
        # "one dgId eventually resolves" (which a label-less-then-labelled pair of
        # nodes could still satisfy by coincidence of the dgId value alone).
        self.entities_by_key: dict[tuple[str, str, str, str], dict] = {}
        # label-less legacy anchor key -> node dict (pre-fix shape, kept only so
        # the regression test can construct the "before" scenario explicitly if
        # needed; mint_identity itself never writes here post-fix).
        self.legacy_entities_by_key: dict[tuple[str, str, str], dict] = {}

    def execute(self, op: str, query: str, params: dict) -> list[dict]:
        self.calls.append((op, query, dict(params)))
        if op == "MINT":
            self.entity_by_dgid[(params["dgId"], params["project"])] = True
            label = _extract_mint_label(query)
            key = (label, params["cgId"], params["definitionId"], params["project"])
            node = self.entities_by_key.setdefault(key, {"reps": []})
            node["dgId"] = params["dgId"]
            node["label"] = label
            node["cgId"] = params["cgId"]
            node["definitionId"] = params["definitionId"]
            node["project"] = params["project"]
            node["graph"] = "Computgraph"
            return []
        if op == "PUBLISH_TEST":
            # Simulates a publish-shaped MERGE: same label + same three-part key as
            # the real publish writers in computgraph_publish.py. Coincides with a
            # prior MINT on the SAME key (proving CR-01 fixed) or creates a second,
            # disjoint node (proving CR-01 broken, pre-fix).
            key = (
                params["label"],
                params["cgId"],
                params["definitionId"],
                params["project"],
            )
            node = self.entities_by_key.setdefault(key, {"reps": []})
            node["label"] = params["label"]
            node["cgId"] = params["cgId"]
            node["definitionId"] = params["definitionId"]
            node["project"] = params["project"]
            node["publishedName"] = params["publishedName"]
            node["graph"] = "Computgraph"
            # Re-point every representation currently bound to this dgId (if any
            # was minted under this exact key) so "reachable from the published
            # entity" can be asserted structurally, not just via the dgId string.
            if "dgId" in node:
                node["reps"] = [
                    r for r in self.reps if r["dgId"] == node["dgId"]
                ]
            return [{"dgId": node.get("dgId")}]
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
        if op == "SP_ENTITY_CHECK":
            if self.entity_by_dgid.get((params["dgId"], params["project"])):
                return [{"dgId": params["dgId"]}]
            return []
        if op == "SP_WRITE":
            key = (params["dgId"], params["propertyName"], params["project"])
            self.shared_props[key] = {
                "dgId": params["dgId"],
                "propertyName": params["propertyName"],
                "value": params["value"],
                "platform": params["platform"],
                "connector": params["connector"],
                "writtenAt": "2026-07-18T12:00:00Z",
                "project": params["project"],
            }
            return []
        if op == "SP_READ":
            key = (params["dgId"], params["propertyName"], params["project"])
            sp = self.shared_props.get(key)
            if sp:
                return [
                    {
                        "value": sp["value"],
                        "platform": sp["platform"],
                        "connector": sp["connector"],
                        "written_at": sp["writtenAt"],
                    }
                ]
            return []
        if op == "SP_LIST":
            return [
                {
                    "property_name": sp["propertyName"],
                    "value": sp["value"],
                    "platform": sp["platform"],
                    "connector": sp["connector"],
                    "written_at": sp["writtenAt"],
                }
                for sp in self.shared_props.values()
                if sp["dgId"] == params["dgId"] and sp["project"] == params["project"]
            ]
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


def test_compute_dg_id_pipe_boundary_shift_does_not_collide():
    """CR-02 collision regression: two tuples sharing the same naive pipe-join must not
    collide once the hash input is length-prefixed.

    Tuple A = ("a|b", "c", "d") and tuple B = ("a", "b|c", "d") both naively join to
    "a|b|c|d" -- under the pre-fix implementation (``input_str = f"{project}|{definition_id}|
    {cg_id}"``) these two calls would hash the identical string and collide (assert equal, not
    assert not-equal). Under the length-prefix encoding, A encodes to "3:a|b|1:c|1:d" and B
    encodes to "1:a|3:b|c|1:d" -- different strings, different hashes. This test only passes
    against the length-prefix fix; it fails against the naive-join implementation it replaces.
    """
    a = dg_identity.compute_dg_id("a|b", "c", "d")
    b = dg_identity.compute_dg_id("a", "b|c", "d")
    assert a != b


# ── mint idempotency ──


def test_mint_identity_idempotent(registry):
    """Two mints of the same triple return the same dgId; the MERGE is parameterized."""
    session = _session(registry)
    first = dg_identity.mint_identity(session, GOLDEN_PROJECT, GOLDEN_DEFINITION_ID, GOLDEN_CG_ID, "Object")
    second = dg_identity.mint_identity(session, GOLDEN_PROJECT, GOLDEN_DEFINITION_ID, GOLDEN_CG_ID, "Object")
    assert first == second == GOLDEN_DG_ID
    # project threaded as a bound parameter on the mint MERGE (T-32.1-03c)
    assert session.last_params is not None and "project" in session.last_params
    # only one entity row upserted — idempotent, not duplicated
    assert len(registry.entity_by_dgid) == 1


def test_mint_identity_tags_graph_computgraph(registry):
    """A node written by mint_identity carries graph = 'Computgraph' (WR-01)."""
    session = _session(registry)
    dg_identity.mint_identity(session, "proj", "wall.gh", "cg:1:obj:wall", "Object")
    mint_queries = [q for (op, q, _p) in registry.calls if op == "MINT"]
    assert mint_queries, "expected a MINT-tagged query"
    assert any("graph" in q and "Computgraph" in q for q in mint_queries)
    key = ("Object", "cg:1:obj:wall", "wall.gh", "proj")
    assert registry.entities_by_key[key]["graph"] == "Computgraph"


def test_mint_identity_rejects_unknown_entity_kind(registry):
    """Minting with an unrecognized entity kind is rejected, not silently accepted."""
    session = _session(registry)
    with pytest.raises(dg_identity.DgIdentityError) as exc_info:
        dg_identity.mint_identity(session, "proj", "wall.gh", "cg:1:obj:wall", "NotARealKind")
    assert exc_info.value.code == "DGID_INVALID_ENTITY_KIND"
    # nothing was written
    assert len(registry.entity_by_dgid) == 0


# ── mint-bind-publish coincidence (CR-01 regression) ──


def _publish_shaped_merge(session: "FixtureSession", *, label: str, cg_id: str,
                           definition_id: str, project: str, published_name: str) -> str | None:
    """Runs a MERGE shaped exactly like the real publish writers in
    computgraph_publish.py: same label, same three-part key
    (cgId, definitionId, project). Returns the dgId found on the resulting node
    (None if the node has never been minted under this exact key).

    This is NOT a call into mint_identity — it simulates the SEPARATE publish
    write path (_publish_object / _publish_procedures / etc.) that Phase 36
    performs after a caller has already pre-minted the entity. The whole point
    of the CR-01 regression is that these are two independently-issued MERGEs
    that must address the SAME node.
    """
    result = session.run(
        f"""
        MERGE (o:{label} {{cgId: $cgId, definitionId: $definitionId, project: $project}})
        SET o.publishedName = $publishedName,
            o.graph = 'Computgraph'
        // op=PUBLISH_TEST
        """,
        {
            "label": label,
            "cgId": cg_id,
            "definitionId": definition_id,
            "project": project,
            "publishedName": published_name,
        },
    )
    record = result.single()
    return record["dgId"] if record else None


def test_mint_then_publish_merge_coincides_on_one_node(registry):
    """Mint an entity, then run a publish-shaped MERGE for the SAME entity: exactly
    one node must exist afterward, carrying both the dgId and the published
    properties (CR-01)."""
    session = _session(registry)
    dg_id = dg_identity.mint_identity(session, "proj", "wall.gh", "cg:1:obj:wall", "Object")

    _publish_shaped_merge(
        session,
        label="Object",
        cg_id="cg:1:obj:wall",
        definition_id="wall.gh",
        project="proj",
        published_name="North Wall",
    )

    key = ("Object", "cg:1:obj:wall", "wall.gh", "proj")
    # Exactly one node under this key — mint and publish coincided.
    assert len(registry.entities_by_key) == 1
    node = registry.entities_by_key[key]
    assert node["dgId"] == dg_id
    assert node["publishedName"] == "North Wall"
    assert node["graph"] == "Computgraph"


def test_mint_then_bind_then_publish_preserves_binding(registry):
    """Mint, bind a native-id representation, then run a publish-shaped MERGE: the
    representation binding must still be reachable from the published entity
    afterward (CR-01's central regression).

    Written against the PRE-FIX code (label-less mint anchor), this test FAILS:
    the label-less mint anchor and the labelled publish-shaped MERGE address two
    DIFFERENT nodes (registry.entities_by_key would hold two entries, one keyed
    by label="" and one by label="Object"), so the representation bound to the
    label-less node is orphaned and never appears on the node the publish-shaped
    MERGE returns/updates. Only the label-aware fix makes them coincide on one
    node, keeping the binding reachable.
    """
    session = _session(registry)
    dg_id = dg_identity.mint_identity(session, "proj", "wall.gh", "cg:1:obj:wall", "Object")

    dg_identity.bind_representation(
        session, dg_id, "Grasshopper", "InstanceGuid", "gh-guid-wall", "grasshopper", "proj"
    )

    _publish_shaped_merge(
        session,
        label="Object",
        cg_id="cg:1:obj:wall",
        definition_id="wall.gh",
        project="proj",
        published_name="North Wall",
    )

    key = ("Object", "cg:1:obj:wall", "wall.gh", "proj")
    assert len(registry.entities_by_key) == 1, (
        "mint and publish must coincide on exactly one node — CR-01 regression"
    )
    published_node = registry.entities_by_key[key]
    assert published_node["dgId"] == dg_id

    # The binding is still reachable from the published entity: resolving the
    # native id still returns this same dgId, and the node's own rep list
    # (re-derived by the publish-shaped MERGE from the live dgId) is non-empty.
    assert dg_identity.resolve_native_id(session, "Grasshopper", "gh-guid-wall", "proj") == dg_id
    assert published_node["reps"], "representation must still be reachable from the published entity"
    assert published_node["reps"][0]["nativeId"] == "gh-guid-wall"


# ── cross-platform same-dgId resolution (DGID-03) ──


def test_cross_platform_bind_resolve_same_dgId(registry):
    """A Grasshopper InstanceGuid and a Revit UniqueId bound to one dgId both resolve to it."""
    session = _session(registry)
    dg_id = dg_identity.mint_identity(session, "proj", "wall.gh", "cg:1:obj:wall", "Object")

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
    dg_a = dg_identity.mint_identity(session, "proj", "a.gh", "cg:1:obj:a", "Object")
    dg_b = dg_identity.mint_identity(session, "proj", "b.gh", "cg:1:obj:b", "Object")
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
    dg_a = dg_identity.mint_identity(session, "proj", "a.gh", "cg:1:obj:a", "Object")
    dg_b = dg_identity.mint_identity(session, "proj", "b.gh", "cg:1:obj:b", "Object")

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
    dg_id = dg_identity.mint_identity(session, "p1", "a.gh", "cg:1:obj:a", "Object")
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
    dg_id = dg_identity.mint_identity(session, "proj", "a.gh", "cg:1:obj:a", "Object")
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


# ── shared-property cross-platform flow (DGID-04) ──


def test_write_and_read_shared_property_cross_platform(registry):
    """Ladybug-on-GH writes insulation; simulated Revit reads it via the shared dgId.

    This is the HEADLINE PROOF of DGID-04: a property computed by one platform
    (Grasshopper + Ladybug, writing insulation=0.035) is readable from ANY bound
    representation (simulated Revit consumer, keyed only by dgId). No Rhino runs.
    """
    # 1. Mint an entity (the facade panel in both GH and Revit)
    session = _session(registry)
    dg_id = dg_identity.mint_identity(session, "proj", "facade.gh", "cg:1:obj:panel_01", "Object")

    # 2. Bind both a GH and a simulated Revit representation to the SAME dgId
    dg_identity.bind_representation(
        session, dg_id, "Grasshopper", "InstanceGuid", "gh-panel-01", "grasshopper", "proj"
    )
    dg_identity.bind_representation(
        session, dg_id, "Revit", "UniqueId", "revit-panel-01", "revit", "proj"
    )

    # 3. GH side (Ladybug) computes and writes insulation = 0.035
    resp_write = client.post(
        f"/identity/{dg_id}/properties",
        params={"project": "proj"},
        json={
            "property_name": "insulation",
            "value": "0.035",
            "platform": "Grasshopper",
            "connector": "Ladybug",
        },
    )
    assert resp_write.status_code == 200
    assert resp_write.json()["value"] == "0.035"
    assert resp_write.json()["platform"] == "Grasshopper"

    # 4. Simulated Revit consumer reads the SAME property keyed only by dgId
    #    (no GH instance running — the property flows through the shared dgId)
    resp_read = client.get(
        f"/identity/{dg_id}/properties",
        params={"project": "proj", "property_name": "insulation"},
    )
    assert resp_read.status_code == 200
    body = resp_read.json()
    assert body["value"] == "0.035"
    # Provenance confirms the GH-side origin
    assert body["platform"] == "Grasshopper"
    assert body["connector"] == "Ladybug"


def test_write_and_read_multiple_properties(registry):
    """Write two shared properties on one dgId; list both."""
    session = _session(registry)
    dg_id = dg_identity.mint_identity(session, "proj", "panel.gh", "cg:1:obj:panel_01", "Object")

    client.post(
        f"/identity/{dg_id}/properties",
        params={"project": "proj"},
        json={
            "property_name": "insulation",
            "value": "0.04",
            "platform": "Grasshopper",
            "connector": "Ladybug",
        },
    )
    client.post(
        f"/identity/{dg_id}/properties",
        params={"project": "proj"},
        json={
            "property_name": "u_value",
            "value": "1.2",
            "platform": "Grasshopper",
            "connector": "Ladybug",
        },
    )

    resp = client.get(f"/identity/{dg_id}/properties", params={"project": "proj"})
    assert resp.status_code == 200
    data = resp.json()
    assert isinstance(data, list)
    names = {p["property_name"] for p in data}
    assert names == {"insulation", "u_value"}


def test_write_shared_property_is_idempotent(registry):
    """Writing the same (dgId, propertyName, project) twice updates in-place."""
    session = _session(registry)
    dg_id = dg_identity.mint_identity(session, "proj", "wall.gh", "cg:1:obj:wall_01", "Object")

    client.post(
        f"/identity/{dg_id}/properties",
        params={"project": "proj"},
        json={
            "property_name": "insulation",
            "value": "0.035",
            "platform": "Grasshopper",
            "connector": "Ladybug",
        },
    )
    # Re-write with different value
    client.post(
        f"/identity/{dg_id}/properties",
        params={"project": "proj"},
        json={
            "property_name": "insulation",
            "value": "0.050",
            "platform": "Grasshopper",
            "connector": "Ladybug-v2",
        },
    )

    resp = client.get(
        f"/identity/{dg_id}/properties",
        params={"project": "proj", "property_name": "insulation"},
    )
    assert resp.status_code == 200
    # Last write wins
    assert resp.json()["value"] == "0.050"
    assert resp.json()["connector"] == "Ladybug-v2"


def test_read_shared_property_not_found_for_unminted_dgid(registry):
    """Reading a property for an unminted dgId returns structured 404 DGID_NOT_FOUND."""
    resp = client.get(
        "/identity/dg:0000000000000000/properties",
        params={"project": "proj", "property_name": "insulation"},
    )
    assert resp.status_code == 404
    assert resp.json()["detail"]["code"] == "DGID_NOT_FOUND"


def test_read_shared_property_missing_property_returns_not_found(registry):
    """Reading a non-existent property name on a valid dgId returns 404."""
    session = _session(registry)
    dg_id = dg_identity.mint_identity(session, "proj", "roof.gh", "cg:1:obj:roof_01", "Object")

    resp = client.get(
        f"/identity/{dg_id}/properties",
        params={"project": "proj", "property_name": "nonexistent"},
    )
    assert resp.status_code == 404
    assert resp.json()["detail"]["code"] == "DGID_NOT_FOUND"
