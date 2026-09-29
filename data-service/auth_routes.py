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

from fastapi import APIRouter, Depends, Request, Response
from pydantic import BaseModel

import auth

router = APIRouter(dependencies=[Depends(auth.require_principal)])

_LOGGER = logging.getLogger(__name__)

# A fixed, module-level dummy password hash. Verifying an unknown username
# against this instead of short-circuiting keeps the scrypt cost -- and
# therefore the response timing -- identical to a known-username/wrong-password
# failure (D-01, T-1205-07-05 anti-enumeration).
_DUMMY_PASSWORD_HASH = auth.hash_password(secrets.token_urlsafe(32))


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
def login(payload: LoginRequest, response: Response):
    try:
        normalized = auth.normalize_username(payload.username)
    except ValueError:
        normalized = None

    user = auth.get_user(normalized) if normalized else None
    stored_hash = user["password_hash"] if user is not None else _DUMMY_PASSWORD_HASH
    password_ok = auth.verify_password(payload.password, stored_hash)

    if user is None or not password_ok:
        # Identical message and code for "unknown user" and "wrong password"
        # (T-1205-07-05) -- never reveals which case occurred.
        raise auth.auth_error(
            "Incorrect username or password.",
            "Check your credentials and try again.",
            "AUTH_FAILED",
            401,
        )

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
    user = auth.get_user(principal.username or "")
    if user is None or not auth.verify_password(payload.currentPassword, user["password_hash"]):
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
    auth.set_password(user["username"], payload.newPassword)
    auth.revoke_user_sessions(user["username"], except_token_hash=principal.session_hash)
    return None
