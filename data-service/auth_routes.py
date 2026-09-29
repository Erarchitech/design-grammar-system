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

from fastapi import APIRouter, Depends, HTTPException, Request, Response
from pydantic import BaseModel

import auth

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
    """nginx overwrites X-Real-IP with the peer address; fall back to the
    direct peer when the service is reached without the proxy."""
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


class MeResponse(BaseModel):
    username: str
    isAdmin: bool
    memberships: list[MembershipOut]


class PasswordChangeRequest(BaseModel):
    currentPassword: str
    newPassword: str


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
    ip_key = f"ip:{_client_ip(request)}"
    user_key = f"user:{normalized}" if normalized else None
    retry_after = max(
        auth.throttle_retry_after(ip_key),
        auth.throttle_retry_after(user_key) if user_key else 0,
    )
    if retry_after > 0:
        raise _throttled_error(retry_after)

    user = auth.get_user(normalized) if normalized else None
    stored_hash = user["password_hash"] if user is not None else _DUMMY_PASSWORD_HASH
    password_ok = _verify_with_slot(payload.password, stored_hash)

    if user is None or not password_ok:
        auth.throttle_record_failure(ip_key, limit=auth.THROTTLE_LIMIT_IP)
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


@router.post("/auth/logout", status_code=204)
def logout(request: Request, response: Response):
    token = request.cookies.get(auth.SESSION_COOKIE_NAME)
    if token:
        auth.revoke_session(token)
    clear_session_cookie(response)
    return None


@router.get("/auth/me", response_model=MeResponse)
def me(request: Request):
    principal = request.state.principal
    memberships = auth.list_memberships(principal.username or "")
    return MeResponse(
        username=principal.username or "",
        isAdmin=principal.is_admin,
        memberships=[MembershipOut(**m) for m in memberships],
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
    return None
