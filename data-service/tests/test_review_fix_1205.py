"""Regression tests for the 1205 code-review fix round (REVIEW.md CR-*/WR-*).

Pure pytest, no Neo4j / LLM. Authentication uses the real ``auth`` /
``auth_fixtures`` machinery (D-20); nothing here overrides the auth dependency.
"""

from __future__ import annotations

import os
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

os.environ.setdefault("LLM_MASTER_SECRET", "test-master-secret")

import app as app_module  # noqa: E402
import auth  # noqa: E402


# --------------------------------------------------------------------------
# CR-01: /validation/view must not leak a server-wide / write Speckle token
# --------------------------------------------------------------------------

_RUN = {
    "runId": "run-1",
    "speckleProjectId": "sp",
    "baseModelId": "bm",
    "baseVersionId": "bv",
    "validationModelId": "vm",
    "validationVersionId": "vv",
    "baseResourceUrl": "u1",
    "validationResourceUrl": "u2",
    "modelViewerUrl": "u3",
}


@pytest.fixture
def speckle_env(monkeypatch):
    monkeypatch.setattr(app_module, "load_persisted_speckle_settings", lambda: {})
    monkeypatch.setenv("SPECKLE_WRITE_TOKEN", "write-secret-token")
    monkeypatch.delenv("SPECKLE_READ_TOKEN", raising=False)


class TestCr01SpeckleReadToken:
    def test_read_token_never_falls_back_to_write_token(self, speckle_env):
        settings = app_module.get_speckle_settings()
        assert settings.write_token == "write-secret-token"
        assert settings.read_token == ""

    def test_view_payload_omits_token_for_user_when_only_write_token_set(self, speckle_env):
        user = auth.Principal(kind="user", username="v@dg.local")
        payload = app_module.build_view_payload("p", _RUN, {}, principal=user)
        assert payload["readToken"] is None
        assert "write-secret-token" not in repr(payload)

    def test_view_payload_gives_read_token_to_user_only(self, speckle_env, monkeypatch):
        monkeypatch.setenv("SPECKLE_READ_TOKEN", "read-only-token")
        user = auth.Principal(kind="user", username="v@dg.local")
        connector = auth.Principal(kind="connector", bound_project="p", credential_id="c1")
        assert app_module.build_view_payload("p", _RUN, {}, principal=user)["readToken"] == "read-only-token"
        assert app_module.build_view_payload("p", _RUN, {}, principal=connector)["readToken"] is None

    def test_view_payload_fails_closed_without_principal(self, speckle_env, monkeypatch):
        monkeypatch.setenv("SPECKLE_READ_TOKEN", "read-only-token")
        assert app_module.build_view_payload("p", _RUN, {})["readToken"] is None
