"""Named graph endpoints (Phase 1205 plan 12, ALGN12-17/ALGN12-18; D-06).

The seven endpoints that replace the browser's former direct Cypher sites:
GET /graph/{project}, POST /graph/{project}/claim-untagged,
PUT /graph/{project}/node/{node_id}/property, GET /rules/{project},
GET /rules/{project}/{rule_id}, GET /validation/view/{project}/{run_id}/entity/
{dg_entity_id} and GET /computgraph/candidates/{project}.

The Neo4j helpers are monkeypatched to capture the statement text and its
parameters; the tests assert each statement is a fixed string that never
contains the project value (it travels only as a bound parameter), and that
the property endpoint and the claim carve-out cannot move nodes across
tenants. Credentials are real sessions (D-20).
"""

from __future__ import annotations

import os
import sys

import pytest
from fastapi.testclient import TestClient

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

os.environ.setdefault("LLM_MASTER_SECRET", "test-master-secret")

import auth  # noqa: E402
import connectors  # noqa: E402
import app as app_module  # noqa: E402
from app import app  # noqa: E402
import auth_fixtures  # noqa: E402

DG_TEST_PRINCIPAL = "none"

CSRF = {auth.CSRF_HEADER: "1"}
PROJECT = "TenantAlpha"  # distinctive so a literal leak into a statement is detectable


@pytest.fixture(autouse=True)
def _isolated_stores(tmp_path, monkeypatch):
    monkeypatch.setattr(auth, "USERS_FILE", tmp_path / "auth-users.json")
    monkeypatch.setattr(auth, "SESSIONS_FILE", tmp_path / "auth-sessions.json")
    monkeypatch.setattr(auth, "MEMBERSHIPS_FILE", tmp_path / "auth-memberships.json")
    monkeypatch.setattr(auth, "INVITES_FILE", tmp_path / "auth-invites.json")
    monkeypatch.setattr(connectors, "CREDENTIALS_FILE", tmp_path / "connector-credentials.json")


@pytest.fixture
def db(monkeypatch):
    """Capture every graph statement. ``many`` is a list of result sets handed
    out in call order (the last one repeats); ``single``/``write`` are the
    single-row results."""
    state = {"many": [[]], "single": None, "write": None, "calls": []}

    def fake_many(query, parameters=None):
        index = sum(1 for kind, *_ in state["calls"] if kind == "many")
        state["calls"].append(("many", query, parameters))
        return list(state["many"][min(index, len(state["many"]) - 1)])

    def fake_single(query, parameters=None):
        state["calls"].append(("single", query, parameters))
        return state["single"]

    def fake_write(query, parameters=None):
        state["calls"].append(("write", query, parameters))
        return state["write"]

    monkeypatch.setattr(app_module, "read_many", fake_many)
    monkeypatch.setattr(app_module, "read_single", fake_single)
    monkeypatch.setattr(app_module, "write_single", fake_write)
    return state


@pytest.fixture
def client():
    return TestClient(app, raise_server_exceptions=False)


def _headers(username="user@dg.local", role="editor", project=PROJECT):
    auth_fixtures.make_user(username, memberships={project: role})
    token = auth_fixtures.session_cookie_for(auth.normalize_username(username))
    return {"Cookie": f"{auth.SESSION_COOKIE_NAME}={token}", **CSRF}


def _code(response):
    detail = response.json().get("detail")
    return detail.get("code") if isinstance(detail, dict) else None


class TestGraph:
    def test_returns_nodes_and_rels_with_bound_project(self, client, db):
        db["many"] = [
            [{"id": 5, "labels": ["Rule"], "props": {"Rule_Id": "R_X", "project": PROJECT}}],
            [{"source": 5, "type": "HAS_BODY", "target": 6}],
        ]

        response = client.get(f"/graph/{PROJECT}", headers=_headers(role="viewer"))

        assert response.status_code == 200
        assert response.json() == {
            "nodes": [{"id": 5, "labels": ["Rule"], "props": {"Rule_Id": "R_X", "project": PROJECT}}],
            "rels": [{"source": 5, "type": "HAS_BODY", "target": 6}],
        }
        (_, node_query, node_params), (_, rel_query, rel_params) = db["calls"]
        assert "n.project = $project" in node_query and "LIMIT 2000" in node_query
        assert "a.project = $project" in rel_query and "b.project = $project" in rel_query
        assert "LIMIT 8000" in rel_query
        assert node_params == {"project": PROJECT} and rel_params == {"project": PROJECT}

    def test_driver_only_property_types_are_serialised(self, client, db):
        class FakeDate:
            def iso_format(self):
                return "2026-09-29T00:00:00Z"

        db["many"] = [[{"id": 1, "labels": ["X"], "props": {"when": FakeDate()}}], []]

        response = client.get(f"/graph/{PROJECT}", headers=_headers(role="viewer"))

        assert response.status_code == 200
        assert response.json()["nodes"][0]["props"] == {"when": "2026-09-29T00:00:00Z"}


class TestClaimUntagged:
    def test_claims_only_untagged_nodes(self, client, db):
        db["write"] = {"claimed": 3}

        response = client.post(f"/graph/{PROJECT}/claim-untagged", headers=_headers())

        assert response.status_code == 200
        assert response.json() == {"claimed": 3}
        kind, query, params = db["calls"][0]
        assert kind == "write"
        assert "n.project IS NULL" in query
        assert "default-project" not in query
        assert PROJECT not in query
        assert params == {"project": PROJECT}

    def test_statement_never_matches_a_named_project(self):
        query = app_module.CLAIM_UNTAGGED_QUERY
        assert query.count("IS NULL") == 1
        assert "OR" not in query.upper().replace("RETURN", "")
        assert "default-project" not in query

    def test_viewer_cannot_claim(self, client, db):
        response = client.post(f"/graph/{PROJECT}/claim-untagged", headers=_headers(role="viewer"))

        assert response.status_code == 403
        assert db["calls"] == []


class TestNodeProperty:
    URL = f"/graph/{PROJECT}/node/5/property"

    def test_updates_matching_id_and_project(self, client, db):
        db["write"] = {"props": {"label": "x", "project": PROJECT}}

        response = client.put(self.URL, json={"key": "label", "value": "x"}, headers=_headers())

        assert response.status_code == 200
        assert response.json() == {"props": {"label": "x", "project": PROJECT}}
        kind, query, params = db["calls"][0]
        assert kind == "write"
        assert "id(n) = $id" in query and "n.project = $project" in query
        assert "n[$key] = $value" in query
        assert PROJECT not in query and "label" not in query
        assert params == {"id": 5, "project": PROJECT, "key": "label", "value": "x"}

    @pytest.mark.parametrize("key", ["project", "graph"])
    def test_protected_keys_are_refused_before_any_write(self, client, db, key):
        response = client.put(self.URL, json={"key": key, "value": "other"}, headers=_headers())

        assert response.status_code == 403
        assert _code(response) == "PROTECTED_PROPERTY"
        assert db["calls"] == []

    @pytest.mark.parametrize("key", ["a-b", "", "1abc", "a b", "a]) DETACH DELETE n //", "x" * 65])
    def test_invalid_keys_are_rejected(self, client, db, key):
        response = client.put(self.URL, json={"key": key, "value": 1}, headers=_headers())

        assert response.status_code == 422
        assert _code(response) == "NODE_KEY_INVALID"
        assert db["calls"] == []

    @pytest.mark.parametrize("value", [{"a": 1}, [1, 2], [{"a": 1}]])
    def test_object_and_array_values_are_rejected(self, client, db, value):
        response = client.put(self.URL, json={"key": "label", "value": value}, headers=_headers())

        assert response.status_code == 422
        assert _code(response) == "PROPERTY_VALUE_INVALID"
        assert db["calls"] == []

    @pytest.mark.parametrize("value", ["text", 3, 2.5, True, None])
    def test_scalar_values_are_accepted(self, client, db, value):
        db["write"] = {"props": {"label": value}}

        response = client.put(self.URL, json={"key": "label", "value": value}, headers=_headers())

        assert response.status_code == 200
        assert db["calls"][0][2]["value"] == value

    def test_no_matching_row_is_node_not_found(self, client, db):
        db["write"] = None

        response = client.put(self.URL, json={"key": "label", "value": "x"}, headers=_headers())

        assert response.status_code == 404
        assert _code(response) == "NODE_NOT_FOUND"

    def test_viewer_cannot_edit(self, client, db):
        response = client.put(
            self.URL, json={"key": "label", "value": "x"}, headers=_headers(role="viewer")
        )

        assert response.status_code == 403
        assert db["calls"] == []


class TestRules:
    def test_lists_rules_for_the_project(self, client, db):
        db["many"] = [[{"ruleId": "R_A", "text": "a(?x) -> b(?x)"}, {"ruleId": "R_B", "text": ""}]]

        response = client.get(f"/rules/{PROJECT}", headers=_headers(role="viewer"))

        assert response.status_code == 200
        assert response.json() == {
            "project": PROJECT,
            "rules": [{"ruleId": "R_A", "text": "a(?x) -> b(?x)"}, {"ruleId": "R_B", "text": ""}],
        }
        _, query, params = db["calls"][0]
        assert "r.project = $project" in query and "graph = 'Metagraph'" in query
        assert params == {"project": PROJECT}

    def test_rule_detail(self, client, db):
        db["single"] = {"swrl": "s", "name": "n", "description": None}

        response = client.get(f"/rules/{PROJECT}/R_X", headers=_headers(role="viewer"))

        assert response.status_code == 200
        assert response.json() == {"ruleId": "R_X", "swrl": "s", "name": "n", "description": ""}
        _, query, params = db["calls"][0]
        assert "$ruleId" in query and "r.project = $project" in query
        assert params == {"project": PROJECT, "ruleId": "R_X"}

    def test_unknown_rule_is_404(self, client, db):
        db["single"] = None

        response = client.get(f"/rules/{PROJECT}/R_MISSING", headers=_headers(role="viewer"))

        assert response.status_code == 404
        assert _code(response) == "RULE_NOT_FOUND"


class TestEntityStatuses:
    def test_statuses_for_one_entity(self, client, db):
        db["many"] = [[{"ruleId": "R_A", "status": "passed"}, {"ruleId": "R_B", "status": "failed"}]]

        response = client.get(
            f"/validation/view/{PROJECT}/RUN1/entity/E1", headers=_headers(role="viewer")
        )

        assert response.status_code == 200
        assert response.json() == {
            "statuses": [
                {"ruleId": "R_A", "status": "passed"},
                {"ruleId": "R_B", "status": "failed"},
            ]
        }
        _, query, params = db["calls"][0]
        assert "$runId" in query and "$dgEntityId" in query and "project:$project" in query
        assert params == {"project": PROJECT, "runId": "RUN1", "dgEntityId": "E1"}


class TestCandidates:
    ROW = {
        "stateId": "PS_1",
        "sourceRuleId": "R_X",
        "provider": "anthropic",
        "model": "m",
        "generatedAt": "2026-01-01",
        "acceptedAt": "2026-01-02",
        "strategy": "s",
    }

    def test_rule_id_is_a_bound_parameter(self, client, db):
        db["many"] = [[dict(self.ROW)]]

        response = client.get(
            f"/computgraph/candidates/{PROJECT}?ruleId=R_X", headers=_headers(role="viewer")
        )

        assert response.status_code == 200
        assert response.json() == {"candidates": [self.ROW]}
        _, query, params = db["calls"][0]
        assert "$ruleId" in query and "R_X" not in query
        assert params == {"project": PROJECT, "ruleId": "R_X"}

    def test_omitted_rule_id_binds_null(self, client, db):
        response = client.get(f"/computgraph/candidates/{PROJECT}", headers=_headers(role="viewer"))

        assert response.status_code == 200
        assert response.json() == {"candidates": []}
        assert db["calls"][0][2] == {"project": PROJECT, "ruleId": None}


ENDPOINTS = [
    ("GET", "/graph/{p}", None),
    ("POST", "/graph/{p}/claim-untagged", None),
    ("PUT", "/graph/{p}/node/5/property", {"key": "label", "value": "x"}),
    ("GET", "/rules/{p}", None),
    ("GET", "/rules/{p}/R_X", None),
    ("GET", "/validation/view/{p}/RUN1/entity/E1", None),
    ("GET", "/computgraph/candidates/{p}?ruleId=R_X", None),
]


@pytest.mark.parametrize("method,template,body", ENDPOINTS, ids=[f"{m} {t}" for m, t, _ in ENDPOINTS])
class TestEveryEndpoint:
    def test_project_travels_only_as_a_parameter(self, client, db, method, template, body):
        db["single"] = {"swrl": "s", "name": "n", "description": "d"}
        db["write"] = {"props": {}, "claimed": 0}
        kwargs = {"headers": _headers(role="owner")}
        if body is not None:
            kwargs["json"] = body

        response = client.request(method, template.format(p=PROJECT), **kwargs)

        assert response.status_code == 200, response.text
        assert db["calls"], "the endpoint must have run a statement"
        for _, query, params in db["calls"]:
            assert PROJECT not in query
            assert params["project"] == PROJECT

    def test_other_project_is_forbidden(self, client, db, method, template, body):
        kwargs = {"headers": _headers(project="Mine", role="owner")}
        if body is not None:
            kwargs["json"] = body

        response = client.request(method, template.format(p="Theirs"), **kwargs)

        assert response.status_code == 403
        assert _code(response) == "PROJECT_FORBIDDEN"
        assert db["calls"] == []

    def test_anonymous_is_rejected(self, client, db, method, template, body):
        kwargs = {"headers": CSRF}
        if body is not None:
            kwargs["json"] = body

        response = client.request(method, template.format(p=PROJECT), **kwargs)

        assert response.status_code == 401
        assert db["calls"] == []
