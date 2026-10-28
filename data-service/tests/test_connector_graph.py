"""Quick 261028-vm9: ``GET /connector-graph/{project}/{query_id}``, the read path the
Grasshopper CONNECTOR uses over HTTPS when the deployment withholds the Neo4j
bundle (multi-user profile).

Credentials are real ``dgk_`` sessions from the 1205-08 fixtures; the Neo4j
reader is monkeypatched to capture statement text and parameters.
"""

from __future__ import annotations

import os
import sys

import pytest
from fastapi.testclient import TestClient

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

os.environ.setdefault("LLM_MASTER_SECRET", "test-master-secret")

import auth  # noqa: E402
import connector_graph  # noqa: E402
import connectors  # noqa: E402
import app as app_module  # noqa: E402
from app import app  # noqa: E402
import auth_fixtures  # noqa: E402

DG_TEST_PRINCIPAL = "none"

CSRF = {auth.CSRF_HEADER: "1"}
PROJECT = "TenantAlpha"
OTHER = "TenantBeta"


@pytest.fixture(autouse=True)
def _isolated_stores(tmp_path, monkeypatch):
    monkeypatch.setattr(auth, "USERS_FILE", tmp_path / "auth-users.json")
    monkeypatch.setattr(auth, "SESSIONS_FILE", tmp_path / "auth-sessions.json")
    monkeypatch.setattr(auth, "MEMBERSHIPS_FILE", tmp_path / "auth-memberships.json")
    monkeypatch.setattr(auth, "INVITES_FILE", tmp_path / "auth-invites.json")
    monkeypatch.setattr(connectors, "CREDENTIALS_FILE", tmp_path / "connector-credentials.json")


@pytest.fixture
def db(monkeypatch):
    state = {"rows": [], "calls": []}

    def fake_many(query, parameters=None):
        state["calls"].append((query, parameters))
        return list(state["rows"])

    monkeypatch.setattr(app_module, "read_many", fake_many)
    return state


@pytest.fixture
def client():
    return TestClient(app, raise_server_exceptions=False)


def _bearer(token):
    return {"Authorization": f"Bearer {token}"}


def _code(response):
    detail = response.json().get("detail")
    return detail.get("code") if isinstance(detail, dict) else None


def test_connector_reads_a_named_query_for_its_bound_project(client, db):
    db["rows"] = [{"iri": "dg:Building", "label": "Building"}]
    token = auth_fixtures.connector_token_for(PROJECT)

    response = client.get(f"/connector-graph/{PROJECT}/classes", headers=_bearer(token))

    assert response.status_code == 200
    assert response.json() == {
        "project": PROJECT,
        "query": "classes",
        "rows": [{"iri": "dg:Building", "label": "Building"}],
    }
    ((statement, parameters),) = db["calls"]
    assert parameters == {"project": PROJECT}
    assert PROJECT not in statement
    assert "$project" in statement


def test_evidence_query_binds_the_run_id(client, db):
    db["rows"] = [{"evidenceEnvelopeJson": "{}"}]
    token = auth_fixtures.connector_token_for(PROJECT)

    response = client.get(f"/connector-graph/{PROJECT}/evidence?runId=RUN_1", headers=_bearer(token))

    assert response.status_code == 200
    ((statement, parameters),) = db["calls"]
    assert parameters == {"project": PROJECT, "runId": "RUN_1"}
    assert "RUN_1" not in statement


def test_evidence_without_a_run_id_is_422(client, db):
    token = auth_fixtures.connector_token_for(PROJECT)

    response = client.get(f"/connector-graph/{PROJECT}/evidence", headers=_bearer(token))

    assert response.status_code == 422
    assert _code(response) == "RUN_ID_REQUIRED"
    assert db["calls"] == []


def test_unknown_query_is_404_and_runs_nothing(client, db):
    token = auth_fixtures.connector_token_for(PROJECT)

    response = client.get(f"/connector-graph/{PROJECT}/MATCH (n) DETACH DELETE n", headers=_bearer(token))

    assert response.status_code in (404, 422)
    assert db["calls"] == []

    response = client.get(f"/connector-graph/{PROJECT}/nope", headers=_bearer(token))
    assert response.status_code == 404
    assert _code(response) == "GRAPH_QUERY_NOT_FOUND"
    assert db["calls"] == []


def test_connector_bound_to_another_project_is_forbidden(client, db):
    token = auth_fixtures.connector_token_for(OTHER)

    response = client.get(f"/connector-graph/{PROJECT}/rules", headers=_bearer(token))

    assert response.status_code == 403
    assert _code(response) == "PROJECT_FORBIDDEN"
    assert db["calls"] == []


def test_a_member_cookie_session_is_not_a_connector(client, db):
    auth_fixtures.make_user("viewer@dg.local", memberships={PROJECT: "viewer"})
    cookie = auth_fixtures.session_cookie_for(auth.normalize_username("viewer@dg.local"))

    response = client.get(
        f"/connector-graph/{PROJECT}/rules",
        headers={"Cookie": f"{auth.SESSION_COOKIE_NAME}={cookie}", **CSRF},
    )

    assert response.status_code == 403
    assert db["calls"] == []


def test_no_credential_is_401(client, db):
    response = client.get(f"/connector-graph/{PROJECT}/rules")

    assert response.status_code == 401
    assert db["calls"] == []


def test_every_statement_is_read_only_and_project_parameterised():
    for query_id, (statement, wants_run_id) in connector_graph.QUERIES.items():
        assert not app_module.is_write_query(statement), query_id
        assert "$project" in statement, query_id
        assert ("$runId" in statement) == wants_run_id, query_id


def test_row_fields_match_what_the_csharp_repositories_read():
    expected = {
        "rules": {"id", "name", "description", "kind", "text", "swrl", "project", "graph"},
        "atoms": {
            "ruleId", "relationType", "atomOrder", "atomId", "atomType", "predicateIri",
            "predicateLabel", "argPos", "argLabels", "varName", "litLex", "litDatatype",
        },
        "objects": {"iri", "label"},
        "classes": {"iri", "label"},
        "objProperties": {"iri", "label"},
        "dataProperties": {"iri", "label"},
        "runs": {"runId", "project", "createdAt", "rulesJson", "statePayloadJson"},
        "standaloneStates": {"stateId", "statePayloadJson", "acceptedAt"},
        "evidence": {"evidenceEnvelopeJson"},
    }
    assert set(connector_graph.QUERIES) == set(expected)
    import re

    for query_id, fields in expected.items():
        statement = connector_graph.QUERIES[query_id][0]
        returned = set(re.findall(r"\bAS\s+(\w+)", statement))
        assert returned == fields, f"{query_id}: {sorted(returned ^ fields)}"
