"""Phase 1301 plan 08, task 2 (D-17, 1300 D-06, DGCL-07): the per-project
provider-export policy store and its admin routes.

The relay-side enforcement (deny before any provider contact, consent, scope
header) lives in ``test_degram_relay.py``; this file covers the store and the
``GET``/``PUT /projects/{project}/degram-policy`` routes.
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
import degram_policy  # noqa: E402
import app as app_module  # noqa: E402
from app import app  # noqa: E402
import auth_fixtures  # noqa: E402

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
    monkeypatch.setenv("DG_DATA_DIR", str(tmp_path / "data"))


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


# -- store ----------------------------------------------------------------------


def test_policy_defaults_to_deny_for_an_unknown_project():
    assert degram_policy.policy_for_project("P1") == {
        "providerExportAllowed": False,
        "wholeDefinitionAllowed": False,
    }
    assert degram_policy.policy_for_project("") == {
        "providerExportAllowed": False,
        "wholeDefinitionAllowed": False,
    }


def test_set_policy_round_trips_per_project_and_merges_fields():
    degram_policy.set_policy("P1", provider_export_allowed=True)
    assert degram_policy.policy_for_project("P1") == {
        "providerExportAllowed": True,
        "wholeDefinitionAllowed": False,
    }
    degram_policy.set_policy("P1", whole_definition_allowed=True)
    assert degram_policy.policy_for_project("P1") == {
        "providerExportAllowed": True,
        "wholeDefinitionAllowed": True,
    }
    assert degram_policy.policy_for_project("P2")["providerExportAllowed"] is False
    degram_policy.set_policy("P1", provider_export_allowed=False)
    assert degram_policy.policy_for_project("P1")["providerExportAllowed"] is False


def test_store_file_name_and_atomic_write_leave_no_temp_file():
    degram_policy.set_policy("P1", provider_export_allowed=True, updated_by="root@dg.local")
    path = degram_policy.policy_path()
    assert path.name == "degram-policy.json"
    data = json.loads(path.read_text(encoding="utf-8"))
    row = data["policies"][0]
    assert row["project"] == "P1" and row["providerExportAllowed"] is True
    assert row["updatedBy"] == "root@dg.local"
    assert not list(path.parent.glob("*.tmp"))


@pytest.mark.parametrize("content", ["not json", "[]", '{"policies": "x"}', '{"policies": [1, null]}'])
def test_corrupt_store_denies_by_default(content):
    path = degram_policy.policy_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")
    assert degram_policy.policy_for_project("P1")["providerExportAllowed"] is False


def test_non_boolean_row_values_do_not_grant_anything():
    path = degram_policy.policy_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps({"policies": [{"project": "P1", "providerExportAllowed": "true",
                                  "wholeDefinitionAllowed": 1}]}),
        encoding="utf-8",
    )
    assert degram_policy.policy_for_project("P1") == {
        "providerExportAllowed": False,
        "wholeDefinitionAllowed": False,
    }


def test_set_policy_refuses_non_boolean_input():
    with pytest.raises(ValueError):
        degram_policy.set_policy("P1", provider_export_allowed="yes")  # type: ignore[arg-type]
    with pytest.raises(ValueError):
        degram_policy.set_policy("", provider_export_allowed=True)


# -- routes -----------------------------------------------------------------------


def test_policy_routes_are_admin_only(client):
    owner = _headers("owner@dg.local", memberships={"P1": "owner"})
    for method in ("get", "put"):
        kwargs = {"json": {"providerExportAllowed": True}} if method == "put" else {}
        denied = getattr(client, method)("/projects/P1/degram-policy", headers=owner, **kwargs)
        assert denied.status_code == 403 and _code(denied) == "ADMIN_REQUIRED"
        anonymous = getattr(client, method)("/projects/P1/degram-policy", **kwargs)
        assert anonymous.status_code == 401
    assert degram_policy.policy_for_project("P1")["providerExportAllowed"] is False


def test_admin_reads_defaults_then_sets_and_reads_back(client):
    admin = _headers("root@dg.local", admin=True)
    got = client.get("/projects/P1/degram-policy", headers=admin)
    assert got.status_code == 200
    assert got.json() == {"project": "P1", "providerExportAllowed": False, "wholeDefinitionAllowed": False}
    put = client.put(
        "/projects/P1/degram-policy",
        json={"providerExportAllowed": True, "wholeDefinitionAllowed": True},
        headers=admin,
    )
    assert put.status_code == 200
    assert put.json() == {"project": "P1", "providerExportAllowed": True, "wholeDefinitionAllowed": True}
    assert client.get("/projects/P1/degram-policy", headers=admin).json() == put.json()
    only_one = client.put("/projects/P1/degram-policy", json={"wholeDefinitionAllowed": False}, headers=admin)
    assert only_one.json()["providerExportAllowed"] is True
    row = json.loads(degram_policy.policy_path().read_text(encoding="utf-8"))["policies"][0]
    assert row["updatedBy"] == "root@dg.local"


@pytest.mark.parametrize(
    "payload",
    [{"providerExportAllowed": "yes"}, {"wholeDefinitionAllowed": 1.5}, {"providerExportAllowed": [True]}],
)
def test_put_rejects_non_boolean_values(client, payload):
    response = client.put("/projects/P1/degram-policy", json=payload,
                          headers=_headers("root@dg.local", admin=True))
    assert response.status_code == 422
    assert degram_policy.policy_for_project("P1")["providerExportAllowed"] is False


def test_put_with_no_field_is_422(client):
    response = client.put("/projects/P1/degram-policy", json={},
                          headers=_headers("root@dg.local", admin=True))
    assert response.status_code == 422 and _code(response) == "DEGRAM_POLICY_INVALID"


def test_put_rejects_an_invalid_project_name(client):
    admin = _headers("root@dg.local", admin=True)
    for name in ("-bad", "a" * 80):
        response = client.put(f"/projects/{name}/degram-policy",
                              json={"providerExportAllowed": True}, headers=admin)
        assert response.status_code == 422 and _code(response) == "PROJECT_NAME_INVALID"
