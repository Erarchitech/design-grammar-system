"""Phase 1301 plan 05, task 1 (DGCL-02, D-20): the admin-assigned
project -> company map.

Covers the store (``company.py``), the admin-only ``PUT /projects/{project}/company``
route, and the ``company`` field on ``GET /projects`` rows and ``GET /auth/me``
memberships. Requests carry real cookies minted through the 1205-08 fixtures;
there is no dependency override and no app-side bypass.
"""

from __future__ import annotations

import json
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
import company  # noqa: E402

DG_TEST_PRINCIPAL = "none"

CSRF = {auth.CSRF_HEADER: "1"}


@pytest.fixture(autouse=True)
def _isolated_stores(tmp_path, monkeypatch):
    monkeypatch.setattr(auth, "USERS_FILE", tmp_path / "auth-users.json")
    monkeypatch.setattr(auth, "SESSIONS_FILE", tmp_path / "auth-sessions.json")
    monkeypatch.setattr(auth, "MEMBERSHIPS_FILE", tmp_path / "auth-memberships.json")
    monkeypatch.setattr(auth, "INVITES_FILE", tmp_path / "auth-invites.json")
    monkeypatch.setattr(connectors, "CREDENTIALS_FILE", tmp_path / "connector-credentials.json")
    monkeypatch.setattr(app_module, "read_many", lambda *a, **k: [])
    monkeypatch.setattr(app_module, "read_single", lambda *a, **k: None)


@pytest.fixture
def client():
    return TestClient(app, raise_server_exceptions=False)


def _headers(username, *, admin=False, memberships=None):
    auth_fixtures.make_user(username, is_admin=admin, memberships=memberships)
    token = auth_fixtures.session_cookie_for(auth.normalize_username(username))
    return {"Cookie": f"{auth.SESSION_COOKIE_NAME}={token}", **CSRF}


def _code(response):
    detail = response.json().get("detail")
    return detail.get("code") if isinstance(detail, dict) else None


# -- store ------------------------------------------------------------------


def test_set_then_read_company(tmp_path):
    company.set_project_company("p1", "acme")
    assert company.company_for_project("p1") == "acme"


def test_unknown_project_has_no_company():
    assert company.company_for_project("never-assigned") is None


def test_reassignment_replaces_the_row():
    company.set_project_company("p1", "acme")
    company.set_project_company("p1", "globex")
    assert company.company_for_project("p1") == "globex"
    assert company.all_companies() == {"p1": "globex"}


def test_store_file_is_written_atomically_with_no_temp_left(tmp_path):
    company.set_project_company("p1", "acme")
    store = tmp_path / "auth-project-companies.json"
    assert store.exists()
    assert json.loads(store.read_text(encoding="utf-8"))["companies"][0]["company"] == "acme"
    leftovers = [p.name for p in tmp_path.iterdir() if ".tmp-" in p.name]
    assert leftovers == []
    if os.name != "nt":
        assert (store.stat().st_mode & 0o777) == 0o600


def test_company_is_trimmed_and_validated():
    assert company.set_project_company("p1", "  acme  ")["company"] == "acme"
    for bad in ("", "   ", "x" * (company.COMPANY_MAX_LENGTH + 1), "bad\nname"):
        with pytest.raises(ValueError):
            company.set_project_company("p1", bad)
    company.set_project_company("p2", "x" * company.COMPANY_MAX_LENGTH)


# -- PUT /projects/{project}/company ---------------------------------------


def test_admin_assigns_company(client):
    admin = _headers("root@dg.local", admin=True)
    response = client.put("/projects/P1/company", json={"company": "Acme"}, headers=admin)
    assert response.status_code == 200, response.text
    assert response.json() == {"project": "P1", "company": "Acme"}
    assert company.company_for_project("P1") == "Acme"


def test_non_admin_owner_is_403_admin_required(client):
    owner = _headers("owner@dg.local", memberships={"P1": "owner"})
    response = client.put("/projects/P1/company", json={"company": "Acme"}, headers=owner)
    assert response.status_code == 403
    assert _code(response) == "ADMIN_REQUIRED"
    assert company.company_for_project("P1") is None


def test_connector_and_service_are_403(client):
    token = auth_fixtures.connector_token_for("P1")
    connector = client.put(
        "/projects/P1/company",
        json={"company": "Acme"},
        headers={"Authorization": f"Bearer {token}"},
    )
    service = client.put(
        "/projects/P1/company",
        json={"company": "Acme"},
        headers=auth_fixtures.service_headers(),
    )
    for response in (connector, service):
        assert response.status_code == 403
        assert _code(response) == "PRINCIPAL_NOT_PERMITTED"
    assert company.company_for_project("P1") is None


def test_no_credential_is_401(client):
    response = client.put("/projects/P1/company", json={"company": "Acme"})
    assert response.status_code == 401


def test_cookie_put_without_csrf_is_403(client):
    admin = _headers("root@dg.local", admin=True)
    admin.pop(auth.CSRF_HEADER)
    response = client.put("/projects/P1/company", json={"company": "Acme"}, headers=admin)
    assert response.status_code == 403
    assert _code(response) == "CSRF_HEADER_REQUIRED"


@pytest.mark.parametrize("value", ["", "   ", "x" * 121])
def test_invalid_company_is_422(client, value):
    admin = _headers("root@dg.local", admin=True)
    response = client.put("/projects/P1/company", json={"company": value}, headers=admin)
    assert response.status_code == 422
    assert _code(response) == "COMPANY_INVALID"
    assert company.company_for_project("P1") is None


def test_missing_company_field_is_422(client):
    admin = _headers("root@dg.local", admin=True)
    response = client.put("/projects/P1/company", json={}, headers=admin)
    assert response.status_code == 422


def test_invalid_project_name_is_422(client):
    admin = _headers("root@dg.local", admin=True)
    response = client.put("/projects/.hidden/company", json={"company": "Acme"}, headers=admin)
    assert response.status_code == 422
    assert _code(response) == "PROJECT_NAME_INVALID"


# -- company on project and membership reads -------------------------------


def test_projects_rows_carry_company_or_null(client):
    company.set_project_company("P1", "Acme")
    user = _headers("u@dg.local", memberships={"P1": "viewer", "P2": "editor"})
    response = client.get("/projects", headers=user)
    assert response.status_code == 200
    rows = {row["project"]: row for row in response.json()["projects"]}
    assert rows["P1"]["company"] == "Acme"
    assert rows["P2"]["company"] is None
    assert rows["P1"]["role"] == "viewer"


def test_admin_projects_rows_carry_company(client):
    auth_fixtures.make_user("m@dg.local", memberships={"P1": "owner"})
    company.set_project_company("P1", "Acme")
    admin = _headers("root@dg.local", admin=True)
    rows = {r["project"]: r for r in client.get("/projects", headers=admin).json()["projects"]}
    assert rows["P1"]["company"] == "Acme"


def test_auth_me_memberships_carry_company_or_null(client):
    company.set_project_company("P1", "Acme")
    user = _headers("u@dg.local", memberships={"P1": "viewer", "P2": "editor"})
    response = client.get("/auth/me", headers=user)
    assert response.status_code == 200
    memberships = {m["project"]: m for m in response.json()["memberships"]}
    assert memberships["P1"]["company"] == "Acme"
    assert memberships["P2"]["company"] is None
    assert memberships["P1"]["role"] == "viewer"
