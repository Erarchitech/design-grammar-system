"""Authorised-client helpers for the data-service suite (1205-08, D-20).

Every credential here is minted through the real ``auth`` / ``connectors``
functions against the (conftest-redirected) test store. Nothing here patches
``require_principal``, overrides an app dependency, or adds an app-side
bypass -- a test client authenticates exactly as production callers do.
"""

from __future__ import annotations

import os
import secrets
import sys
from typing import Any, Callable

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import auth  # noqa: E402
import connectors  # noqa: E402

TEST_ADMIN_USERNAME = "test-admin@dg.local"
CSRF_VALUE = "1"

# Cached test-admin session token; re-validated (and re-minted) on every use so
# a test that revokes it, or swaps the store, does not poison later tests.
_admin_token: str | None = None


def _random_password() -> str:
    return secrets.token_urlsafe(18)  # 24 chars, above PASSWORD_MIN_LENGTH


def make_user(
    username: str,
    *,
    is_admin: bool = False,
    memberships: dict[str, str] | None = None,
) -> dict[str, Any]:
    """Create a user (idempotent) and upsert its project memberships.

    Returns the stored user record; a freshly created user additionally
    carries its random ``password`` under that key.
    """
    normalized = auth.normalize_username(username)
    existing = auth.get_user(normalized)
    if existing is None:
        password = _random_password()
        record = auth.create_user(normalized, password, is_admin=is_admin)
        record = dict(record)
        record["password"] = password
    else:
        record = dict(existing)
    for project, role in (memberships or {}).items():
        auth.set_membership(normalized, project, role)
    return record


def session_cookie_for(username: str) -> str:
    """Mint a real session token (the ``dg_session`` cookie value)."""
    return auth.create_session(username)


def admin_session_token() -> str:
    """Session token of the shared test admin (created lazily)."""
    global _admin_token
    if auth.get_user(TEST_ADMIN_USERNAME) is None:
        make_user(TEST_ADMIN_USERNAME, is_admin=True)
        _admin_token = None
    if _admin_token is None or auth.resolve_session_principal(_admin_token) is None:
        _admin_token = auth.create_session(TEST_ADMIN_USERNAME)
    return _admin_token


def service_headers() -> dict[str, str]:
    """Header carrying the real (test-only) service token."""
    return {auth.SERVICE_TOKEN_HEADER: os.environ["DG_SERVICE_TOKEN"]}


def connector_token_for(project: str) -> str:
    """Create a real connector credential bound to ``project`` in the
    currently configured CREDENTIALS_FILE and return its plaintext token."""
    _record, token = connectors.create_credential("grasshopper", project=project)
    return token


def resolve_principal_name(marker_value: Any, module: Any) -> Any:
    """Marker beats module-level ``DG_TEST_PRINCIPAL`` beats ``"admin"``."""
    if marker_value is not None:
        return marker_value
    return getattr(module, "DG_TEST_PRINCIPAL", "admin")


def authorize_client(client: Any, principal: Any) -> Callable[[], None]:
    """Give ``client`` a real principal; return a callable that removes
    exactly what was added (cookie by name, the two headers), restoring any
    header value that was there before.

    ``principal``: ``"admin"``, ``"service"``, ``"none"`` or
    ``("user", username)``.
    """
    added_cookie = False
    previous_headers: dict[str, str | None] = {}

    def _set_header(name: str, value: str) -> None:
        previous_headers.setdefault(name, client.headers.get(name))
        client.headers[name] = value

    if principal == "none":
        pass
    elif principal == "service":
        for name, value in service_headers().items():
            _set_header(name, value)
    elif principal == "admin" or (
        isinstance(principal, tuple) and len(principal) == 2 and principal[0] == "user"
    ):
        if principal == "admin":
            token = admin_session_token()
        else:
            token = session_cookie_for(principal[1])
        client.cookies.set(auth.SESSION_COOKIE_NAME, token)
        added_cookie = True
        _set_header(auth.CSRF_HEADER, CSRF_VALUE)
    else:
        raise ValueError(f"unknown test principal: {principal!r}")

    def undo() -> None:
        if added_cookie:
            for cookie in list(client.cookies.jar):
                if cookie.name == auth.SESSION_COOKIE_NAME:
                    client.cookies.jar.clear(cookie.domain, cookie.path, cookie.name)
        for name, prior in previous_headers.items():
            if prior is None:
                client.headers.pop(name, None)
            else:
                client.headers[name] = prior

    return undo
