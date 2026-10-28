"""Auth routes (Phase 1205 "Security and Tenancy Release Gate", D-01):
POST /auth/login, POST /auth/logout, GET /auth/me, POST /auth/password.

This router carries the same deny-by-default `Depends(auth.require_principal)`
dependency as the tracer's one enforced project route -- the policy for each
of these four paths is seeded in route_policy.ROUTE_POLICIES, so unauthorized
access to *these* routes already fails closed even though the wide route-flip
is 1205-10's job.

No test-only bypass ships here (D-20): login always goes through
`auth.verify_password`, including a fixed dummy scrypt hash for an unknown
username so both branches cost the same derivation (T-1205-07-05 -- identical
401 message and timing for "wrong password" vs. "unknown user").
"""

from __future__ import annotations

import logging
import os
import secrets

import threading
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Request, Response
from pydantic import BaseModel

import auth
import company
import connector_session
import degram_grants
import degram_pairing
import delegation

router = APIRouter(dependencies=[Depends(auth.require_principal)])

_LOGGER = logging.getLogger(__name__)

# A fixed, module-level dummy password hash. Verifying an unknown username
# against this instead of short-circuiting keeps the scrypt cost -- and
# therefore the response timing -- identical to a known-username/wrong-password
# failure (D-01, T-1205-07-05 anti-enumeration).
_DUMMY_PASSWORD_HASH = auth.hash_password(secrets.token_urlsafe(32))


# WR-01: cap concurrent scrypt derivations (each is ~16 MB and CPU-bound) so a
# burst of unauthenticated logins cannot exhaust memory or the threadpool.
_SCRYPT_SLOTS = threading.BoundedSemaphore(int(os.environ.get("DG_SCRYPT_CONCURRENCY", "4")))
_SCRYPT_WAIT_SECONDS = 10


def _client_ip(request: Request) -> str:
    """nginx overwrites X-Real-IP with the peer address (the client address
    recovered from X-Forwarded-For when DG_TRUSTED_PROXIES is configured); fall
    back to the direct peer when the service is reached without the proxy."""
    real = (request.headers.get("x-real-ip") or "").strip()
    if real:
        return real[:64]
    return request.client.host if request.client else "unknown"


def _throttled_error(retry_after: int) -> HTTPException:
    exc = auth.auth_error(
        "Too many failed attempts.",
        f"Wait {retry_after} seconds before trying again.",
        "AUTH_THROTTLED",
        429,
    )
    exc.headers = {"Retry-After": str(retry_after)}
    return exc


def _verify_with_slot(password: str, stored_hash: str) -> bool:
    if not _SCRYPT_SLOTS.acquire(timeout=_SCRYPT_WAIT_SECONDS):
        exc = auth.auth_error("The server is busy.", "Retry in a few seconds.", "AUTH_BUSY", 429)
        exc.headers = {"Retry-After": "5"}
        raise exc
    try:
        return auth.verify_password(password, stored_hash)
    finally:
        _SCRYPT_SLOTS.release()


class LoginRequest(BaseModel):
    username: str
    password: str


class LoginResponse(BaseModel):
    username: str
    isAdmin: bool


class MembershipOut(BaseModel):
    project: str
    role: str
    company: str | None = None  # D-20: null when the project has no company


class MeResponse(BaseModel):
    username: str
    isAdmin: bool
    memberships: list[MembershipOut]


class PasswordChangeRequest(BaseModel):
    currentPassword: str
    newPassword: str


class DelegatedTokenRequest(BaseModel):
    project: str


def set_session_cookie(response: Response, token: str) -> None:
    """Set the dg_session cookie. Shared by login and accept-invite (app.py)
    so both paths issue identical cookie attributes."""
    ttl = int(os.environ.get("DG_SESSION_TTL_SECONDS", "43200"))
    response.set_cookie(
        key=auth.SESSION_COOKIE_NAME,
        value=token,
        max_age=ttl,
        path="/",
        httponly=True,
        samesite="strict",
        secure=auth.cookie_secure(),
    )


def clear_session_cookie(response: Response) -> None:
    """Expire the dg_session cookie (logout)."""
    response.delete_cookie(key=auth.SESSION_COOKIE_NAME, path="/")


@router.post("/auth/login", response_model=LoginResponse)
def login(payload: LoginRequest, request: Request, response: Response):
    try:
        normalized = auth.normalize_username(payload.username)
    except ValueError:
        normalized = None

    # WR-01: throttle BEFORE the scrypt derivation so a locked-out caller
    # costs nothing. Both keys apply to unknown usernames too (no enumeration).
    ip_limit = auth.ip_throttle_limit()
    ip_key = f"ip:{_client_ip(request)}" if ip_limit > 0 else None
    user_key = f"user:{normalized}" if normalized else None
    retry_after = max(
        auth.throttle_retry_after(ip_key) if ip_key else 0,
        auth.throttle_retry_after(user_key) if user_key else 0,
    )
    if retry_after > 0:
        raise _throttled_error(retry_after)

    user = auth.get_user(normalized) if normalized else None
    stored_hash = user["password_hash"] if user is not None else _DUMMY_PASSWORD_HASH
    password_ok = _verify_with_slot(payload.password, stored_hash)

    if user is None or not password_ok:
        if ip_key:
            auth.throttle_record_failure(ip_key, limit=ip_limit)
        if user_key:
            auth.throttle_record_failure(user_key, limit=auth.THROTTLE_LIMIT_USER)
        # Identical message and code for "unknown user" and "wrong password"
        # (T-1205-07-05) -- never reveals which case occurred.
        raise auth.auth_error(
            "Incorrect username or password.",
            "Check your credentials and try again.",
            "AUTH_FAILED",
            401,
        )

    auth.throttle_clear(user_key)
    token = auth.create_session(user["username"])
    set_session_cookie(response, token)
    return LoginResponse(username=user["username"], isAdmin=bool(user.get("is_admin")))


class RegisterRequest(BaseModel):
    # Only these two fields are read; any other key in the body (for example a
    # client-supplied `is_admin`) is ignored by pydantic and never reaches the
    # store.
    username: str
    password: str


class AuthOptionsResponse(BaseModel):
    selfRegistration: bool


@router.get("/auth/options", response_model=AuthOptionsResponse)
def auth_options():
    """Public: which optional sign-in paths this deployment offers. Carries no
    secret and no user information. Fails closed -- an unreadable toggle
    reports registration as off."""
    return AuthOptionsResponse(selfRegistration=auth._self_registration_open())


def _registration_invalid(hint: str = "Choose a different username or password and try again.") -> HTTPException:
    """The one generic answer for every registration failure; never reveals
    whether the username already exists."""
    return auth.auth_error("Registration could not be completed.", hint, "REGISTRATION_INVALID", 400)


@router.post("/auth/register", response_model=LoginResponse, status_code=201)
def register(payload: RegisterRequest, request: Request, response: Response):
    """Public, local-profile self-registration (amendment of D-05, 2026-09-30).

    The account is never an admin and holds no memberships; the new user
    creates their own projects through POST /projects. When self-registration
    is off this route answers 404 (auth.require_principal does so before the
    CSRF check; the guard below is defence in depth)."""
    if not auth._self_registration_open():
        raise HTTPException(status_code=404, detail="Not Found")

    try:
        normalized = auth.normalize_username(payload.username)
    except ValueError as exc:
        raise auth.auth_error(
            "That username is not valid.",
            "Use 3-254 characters: lowercase letters, digits and . _ @ + -.",
            "USERNAME_INVALID",
            422,
        ) from exc

    # Same counters as login: per-username always, per-address when configured.
    ip_limit = auth.ip_throttle_limit()
    ip_key = f"ip:{_client_ip(request)}" if ip_limit > 0 else None
    user_key = f"user:{normalized}"
    retry_after = max(
        auth.throttle_retry_after(ip_key) if ip_key else 0,
        auth.throttle_retry_after(user_key),
    )
    if retry_after > 0:
        raise _throttled_error(retry_after)

    def _fail(hint: str | None = None) -> HTTPException:
        if ip_key:
            auth.throttle_record_failure(ip_key, limit=ip_limit)
        auth.throttle_record_failure(user_key, limit=auth.THROTTLE_LIMIT_USER)
        return _registration_invalid(hint) if hint else _registration_invalid()

    try:
        auth.validate_password_policy(payload.password)
    except ValueError as exc:
        raise _fail(str(exc)) from exc

    if auth.get_user(normalized) is not None:
        # Spend the same scrypt cost as a real creation so timing does not
        # reveal that the username exists.
        _verify_with_slot(payload.password, _DUMMY_PASSWORD_HASH)
        raise _fail()

    if not _SCRYPT_SLOTS.acquire(timeout=_SCRYPT_WAIT_SECONDS):
        busy = auth.auth_error("The server is busy.", "Retry in a few seconds.", "AUTH_BUSY", 429)
        busy.headers = {"Retry-After": "5"}
        raise busy
    try:
        # create_user runs the duplicate check and the write under the store lock.
        user = auth.create_user(normalized, payload.password, is_admin=False)
    except ValueError as exc:
        raise _fail() from exc
    finally:
        _SCRYPT_SLOTS.release()

    token = auth.create_session(user["username"])
    set_session_cookie(response, token)
    return LoginResponse(username=user["username"], isAdmin=False)


@router.post("/auth/logout", status_code=204)
def logout(request: Request, response: Response):
    token = request.cookies.get(auth.SESSION_COOKIE_NAME)
    if token:
        auth.revoke_session(token)
        # D-08: every delegated token minted from this session dies with it.
        delegation.revoke_for_session(request.state.principal.session_hash or "")
    clear_session_cookie(response)
    return None


@router.post("/auth/delegated-token", status_code=201)
def mint_delegated_token(payload: DelegatedTokenRequest, request: Request, response: Response):
    """Phase 1301-05 (D-06): convert the caller's cookie session into a
    short-lived ``dgd_`` Bearer token bound to ONE project the caller is a
    member of. The route policy keeps the cookie + CSRF requirement (a Bearer
    caller is refused), and membership is the STORED role: an admin who is not a
    member gets 403 -- the token would carry no admin elevation anyway."""
    principal = request.state.principal
    project = payload.project
    if (
        not principal.username
        or not principal.session_hash
        or auth.get_role(principal.username, project) is None
    ):
        raise auth.auth_error(
            "Not authorized for the requested project.",
            "Request project access from a project owner.",
            "PROJECT_FORBIDDEN",
            403,
        )
    token, record = delegation.issue_delegated_token(
        session_hash=principal.session_hash,
        username=principal.username,
        project=project,
    )
    return _delegated_answer(response, token, record)


def _delegated_answer(response: Response, token: str, record: dict) -> dict:
    """The one answer shape of both delegated-token mints."""
    response.headers["Cache-Control"] = "no-store"
    return {
        "token": token,
        "project": record["project"],
        "company": record["company"],
        "expiresAt": datetime.fromtimestamp(record["expires_at"], tz=timezone.utc).strftime(
            "%Y-%m-%dT%H:%M:%SZ"
        ),
        "expiresInSeconds": delegation.DELEGATED_TOKEN_TTL_SECONDS,
    }


@router.post("/auth/degram/session-exchange", status_code=201)
def exchange_degram_session(payload: DelegatedTokenRequest, request: Request, response: Response):
    """Phase 1301-30 (D-39): trade the caller's cookie session (+ CSRF) for a
    ``dgd_`` token of one project, but only when an owner or admin has granted
    the caller DeGram access to it (``degram_grants``). The stored membership is
    required (no admin elevation, like the cookie mint): 403 ``PROJECT_FORBIDDEN``
    for a non-member, 403 ``GRANT_REQUIRED`` for a member without an active
    grant, unless the member is the project's owner or a DG admin (exempt, no
    grant needed). The token's parent is the session, so logout ends it, and it
    records the grant, so revoking the grant ends it (an exempt token is
    re-checked against the owner/admin role instead). The answer is the cookie
    mint's plus ``username``."""
    principal = request.state.principal
    project = payload.project
    username = principal.username or ""
    if not username or not principal.session_hash or auth.get_role(username, project) is None:
        raise auth.auth_error(
            "Not authorized for the requested project.",
            "Request project access from a project owner.",
            "PROJECT_FORBIDDEN",
            403,
        )
    grant = degram_grants.active_grant(username, project)
    if grant is None and not degram_grants.is_exempt(username, project):
        raise degram_grants.grant_required()
    token, record = delegation.issue_delegated_token(
        session_hash=principal.session_hash,
        grant_id=grant["grant_id"] if grant else None,
        exempt=grant is None,
        username=username,
        project=project,
    )
    if grant:
        degram_grants.record_use(grant["grant_id"])
    return {**_delegated_answer(response, token, record), "username": record["username"]}


@router.post("/auth/degram/exchange", status_code=201)
def exchange_degram_pairing(request: Request):
    """Retired by D-39: the user-created ``dgp_`` pairing is replaced by owner/
    admin grants and ``POST /auth/degram/session-exchange``. The pairing token
    never resolves to a principal (``degram_pairing.authenticate_pairing``
    answers 401 ``PAIRING_RETIRED`` first); this handler is a second wall."""
    raise degram_pairing.pairing_retired()


@router.delete("/auth/delegated-token", status_code=204)
def revoke_delegated_token(request: Request):
    """Revoke the delegated token the caller presented (self-revoke)."""
    header = request.headers.get("Authorization", "")
    delegation.revoke_token(header[len("Bearer "):].strip() if header.startswith("Bearer ") else "")
    return None


@router.get("/auth/me", response_model=MeResponse)
def me(request: Request):
    principal = request.state.principal
    memberships = auth.list_memberships(principal.username or "")
    companies = company.all_companies()
    return MeResponse(
        username=principal.username or "",
        isAdmin=principal.is_admin,
        memberships=[
            MembershipOut(**m, company=companies.get(m["project"])) for m in memberships
        ],
    )


@router.post("/auth/password", status_code=204)
def change_password(request: Request, payload: PasswordChangeRequest):
    principal = request.state.principal
    pw_key = f"pw:{principal.username or ''}"
    retry_after = auth.throttle_retry_after(pw_key)
    if retry_after > 0:
        raise _throttled_error(retry_after)
    user = auth.get_user(principal.username or "")
    if user is None or not _verify_with_slot(payload.currentPassword, user["password_hash"]):
        auth.throttle_record_failure(pw_key, limit=auth.THROTTLE_LIMIT_PASSWORD)
        raise auth.auth_error(
            "Current password is incorrect.",
            "Re-enter your current password.",
            "PASSWORD_INCORRECT",
            403,
        )
    try:
        auth.validate_password_policy(payload.newPassword)
    except ValueError as exc:
        raise auth.auth_error(
            "New password does not meet the password policy.",
            str(exc),
            "PASSWORD_POLICY",
            422,
        ) from exc
    auth.throttle_clear(pw_key)
    auth.set_password(user["username"], payload.newPassword)
    auth.revoke_user_sessions(user["username"], except_token_hash=principal.session_hash)
    # D-08: a password change ends every delegated token of the user, including
    # those minted from the session that is kept.
    delegation.revoke_for_user(user["username"])
    connector_session.revoke_for_user(user["username"])
    return None
