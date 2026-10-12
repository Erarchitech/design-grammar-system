"""Project landing summary route (Phase 1308 plan 02, WEBUI-05; D-19).

GET /projects/{project}/summary answers counts only: graph classes, properties
and rules of the path project plus the number of active connector accesses and
DeGram grants. The Neo4j read is monkeypatched to capture the statement and its
bound parameters; the grant counts come from the real file-backed stores.
"""

from __future__ import annotations

import os
import sys

import pytest
from fastapi.testclient import TestClient

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

os.environ.setdefault("LLM_MASTER_SECRET", "test-master-secret")

import auth  # noqa: E402
import connector_access  # noqa: E402
import connectors  # noqa: E402
import degram_grants  # noqa: E402
import app as app_module  # noqa: E402
from app import app  # noqa: E402
import auth_fixtures  # noqa: E402

DG_TEST_PRINCIPAL = "none"

CSRF = {auth.CSRF_HEADER: "1"}
PROJECT = "TenantAlpha"  # distinctive so a literal leak into a statement is detectable
CONNECTOR = sorted(connectors.CONNECTOR_IDS)[0]


@pytest.fixture(autouse=True)
def _isolated_stores(tmp_path, monkeypatch):
    monkeypatch.setattr(auth, "USERS_FILE", tmp_path / "auth-users.json")
    monkeypatch.setattr(auth, "SESSIONS_FILE", tmp_path / "auth-sessions.json")
    monkeypatch.setattr(auth, "MEMBERSHIPS_FILE", tmp_path / "auth-memberships.json")
    monkeypatch.setattr(auth, "INVITES_FILE", tmp_path / "auth-invites.json")
    monkeypatch.setattr(connectors, "CREDENTIALS_FILE", tmp_path / "connector-credentials.json")


@pytest.fixture
def graph(monkeypatch):
    """Capture the summary read; ``row`` is what the driver returns."""
    state = {"row": {"classes": 0, "properties": 0, "rules": 0}, "calls": []}

    def fake_single(query, parameters=None):
        state["calls"].append((query, parameters))
        return state["row"]

    monkeypatch.setattr(app_module, "read_single", fake_single)
    return state


@pytest.fixture
def client():
    return TestClient(app, raise_server_exceptions=False)


def _headers(username, *, admin=False, memberships=None):
    auth_fixtures.make_user(username, is_admin=admin, memberships=memberships)
    token = auth_fixtures.session_cookie_for(auth.normalize_username(username))
    return {"Cookie": f"{auth.SESSION_COOKIE_NAME}={token}", **CSRF}


class TestProjectSummary:
    def test_viewer_gets_exactly_the_counts_shape(self, client, graph):
        viewer = _headers("vw@dg.local", memberships={PROJECT: "viewer"})
        graph["row"] = {"classes": 7, "properties": 16, "rules": 12}

        response = client.get(f"/projects/{PROJECT}/summary", headers=viewer)

        assert response.status_code == 200
        body = response.json()
        assert set(body) == {"project", "graph", "connectors"}
        assert set(body["graph"]) == {"classes", "properties", "rules"}
        assert set(body["connectors"]) == {"grantsIssued"}
        assert body == {
            "project": PROJECT,
            "graph": {"classes": 7, "properties": 16, "rules": 12},
            "connectors": {"grantsIssued": 0},
        }

    def test_non_member_is_forbidden_and_admin_is_allowed(self, client, graph):
        stranger = _headers("stranger@dg.local", memberships={"Other": "owner"})
        admin = _headers("root@dg.local", admin=True)

        assert client.get(f"/projects/{PROJECT}/summary", headers=stranger).status_code == 403
        assert graph["calls"] == []
        assert client.get(f"/projects/{PROJECT}/summary", headers=admin).status_code == 200

    def test_query_is_project_scoped_and_parameterized(self, client, graph):
        viewer = _headers("vw@dg.local", memberships={PROJECT: "viewer"})

        client.get(f"/projects/{PROJECT}/summary", headers=viewer)

        assert len(graph["calls"]) == 1
        query, parameters = graph["calls"][0]
        assert parameters == {"project": PROJECT}
        assert PROJECT not in query
        assert query is app_module.PROJECT_SUMMARY_QUERY
        assert "n.project = $project" in query
        assert "n:DatatypeProperty OR n:ObjectProperty" in query
        assert "n.graph = 'Metagraph'" in query

    def test_property_nodes_are_counted_once_and_rules_only_in_the_metagraph(self):
        query = app_module.PROJECT_SUMMARY_QUERY
        # one CASE over the OR, so a node carrying both labels adds one
        assert query.count("n:DatatypeProperty") == 1
        assert query.count("n:ObjectProperty") == 1
        assert query.count("AS properties") == 1
        assert "n:Rule AND n.graph = 'Metagraph'" in query
        for forbidden in ("CREATE", "MERGE", "DELETE", "SET ", "REMOVE"):
            assert forbidden not in query.upper()

    def test_empty_project_answers_zeros(self, client, graph):
        viewer = _headers("vw@dg.local", memberships={PROJECT: "viewer"})
        graph["row"] = {"classes": None, "properties": None, "rules": None}

        response = client.get(f"/projects/{PROJECT}/summary", headers=viewer)

        assert response.status_code == 200
        assert response.json() == {
            "project": PROJECT,
            "graph": {"classes": 0, "properties": 0, "rules": 0},
            "connectors": {"grantsIssued": 0},
        }

    def test_a_missing_row_answers_zeros(self, client, graph):
        viewer = _headers("vw@dg.local", memberships={PROJECT: "viewer"})
        graph["row"] = None

        response = client.get(f"/projects/{PROJECT}/summary", headers=viewer)

        assert response.status_code == 200
        assert response.json()["graph"] == {"classes": 0, "properties": 0, "rules": 0}

    def test_grants_issued_counts_only_active_rows_of_this_project(self, client, graph):
        owner = _headers("owner@dg.local", memberships={PROJECT: "owner", "Other": "owner"})
        auth_fixtures.make_user("a@dg.local", memberships={PROJECT: "editor", "Other": "editor"})
        auth_fixtures.make_user("b@dg.local", memberships={PROJECT: "editor"})
        auth_fixtures.make_user("c@dg.local", memberships={PROJECT: "viewer"})

        # active: one connector access (a), one DeGram grant (b)
        connector_access.issue_access(PROJECT, "a@dg.local", CONNECTOR, "owner@dg.local")
        degram_grants.issue_grant(PROJECT, "b@dg.local", "label", "purpose", "owner@dg.local")
        # not counted: a revoked access, an access of a removed member
        revoked = connector_access.issue_access(PROJECT, "b@dg.local", CONNECTOR, "owner@dg.local")
        assert connector_access.revoke_access(PROJECT, revoked["access_id"], "owner@dg.local")
        connector_access.issue_access(PROJECT, "c@dg.local", CONNECTOR, "owner@dg.local")
        auth.remove_membership("c@dg.local", PROJECT)
        # not counted: another project's access and grant
        connector_access.issue_access("Other", "a@dg.local", CONNECTOR, "owner@dg.local")
        degram_grants.issue_grant("Other", "a@dg.local", "label", "purpose", "owner@dg.local")

        response = client.get(f"/projects/{PROJECT}/summary", headers=owner)

        assert response.status_code == 200
        assert response.json()["connectors"] == {"grantsIssued": 2}

    def test_answer_carries_no_names_or_ids(self, client, graph):
        owner = _headers("owner@dg.local", memberships={PROJECT: "owner"})
        auth_fixtures.make_user("a@dg.local", memberships={PROJECT: "editor"})
        connector_access.issue_access(PROJECT, "a@dg.local", CONNECTOR, "owner@dg.local")
        graph["row"] = {
            "classes": 1,
            "properties": 2,
            "rules": 3,
            "names": ["SecretClass"],
            "ruleText": "secret rule",
        }

        response = client.get(f"/projects/{PROJECT}/summary", headers=owner)

        text = response.text
        for leaked in ("SecretClass", "secret rule", "a@dg.local", "access_id", CONNECTOR):
            assert leaked not in text

    def test_invalid_project_name_is_422(self, client, graph):
        admin = _headers("root@dg.local", admin=True)

        response = client.get("/projects/-bad/summary", headers=admin)

        assert response.status_code == 422
        assert graph["calls"] == []
