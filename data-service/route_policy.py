"""Deny-by-default route policy table (Phase 1205 "Security and Tenancy
Release Gate", D-03).

This module maps ``(method, route path template)`` to a :class:`RoutePolicy`.
``auth.require_principal`` looks up the policy for the route it is guarding
via ``request.scope["route"].path`` + ``request.method``; a route with no
entry here fails closed with 403 ``ROUTE_UNCLASSIFIED``.

This is the 1205-07 tracer-slice seed: only the routes this plan's tests
exercise (the public/auth surface plus the one enforced project route) are
seeded. Plan 1205-10 expands the table to the full route inventory.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Awaitable, Callable

# ── Principal tokens ──
#
# These are matched against the *policy*, not the resolved Principal.kind
# directly -- a "user" kind principal is permitted by any of session/admin/
# member (auth.require_principal decides which one actually applies); a
# "connector" kind principal is permitted only by "connector"; a "service"
# kind principal only by "service". "public"/"connector-self" bypass
# credential resolution entirely (anonymous principal).
PRINCIPAL_PUBLIC = "public"
PRINCIPAL_CONNECTOR_SELF = "connector-self"
PRINCIPAL_SESSION = "session"
PRINCIPAL_ADMIN = "admin"
PRINCIPAL_MEMBER = "member"
PRINCIPAL_CONNECTOR = "connector"
PRINCIPAL_SERVICE = "service"


@dataclass(frozen=True)
class RoutePolicy:
    """One route's authorization policy.

    Attributes:
        principals: the set of principal tokens permitted on this route.
        project_source: where the route's project value is declared --
            ``"path"``, ``"body"``, ``"query"``, ``"filtered"``, or
            ``"resource:<name>"`` (looked up in RESOURCE_RESOLVERS) -- or
            ``None`` for a route that carries no project scoping at all.
        min_role: the minimum membership role a "member"-permitted user
            principal needs (``role_satisfies`` semantics), or ``None`` when
            the route is not role-gated (e.g. a session-only route).
    """

    principals: frozenset[str]
    project_source: str | None = None
    min_role: str | None = None


# Registry of resource-project resolvers, keyed by name. A resolver takes the
# current Request and returns the owning project string (or raises its own
# 404 HTTPException when the resource does not exist). Empty here -- filled
# in by 1205-10 as the wide route-inventory flip needs "resource:<name>"
# project sources for routes whose project cannot be read directly from the
# path/query/body (Claude's discretion per 1205-CONTEXT.md).
RESOURCE_RESOLVERS: dict[str, Callable[[Any], Awaitable[str] | str]] = {}


def register_resource_resolver(
    name: str, fn: Callable[[Any], Awaitable[str] | str]
) -> None:
    """Register a resource-project resolver under `name` for use by a
    RoutePolicy with ``project_source == f"resource:{name}"``."""
    RESOURCE_RESOLVERS[name] = fn


# ── Seeded table (D-03) ──
#
# Tracer slice only: GET / (health), the four /auth/* routes, and the one
# enforced project route (GET /validation/runs/{project}, the Model Viewer's
# read path). Everything else in app.py's 65 routes is still unclassified at
# this point in the phase and is NOT wrapped with the require_principal
# dependency yet (1205-10 does the wide flip) -- so this table's incompleteness
# is not itself a live gap: an unwrapped route simply has no dependency to
# consult this table at all.
ROUTE_POLICIES: dict[tuple[str, str], RoutePolicy] = {
    ("GET", "/"): RoutePolicy(principals=frozenset({PRINCIPAL_PUBLIC})),
    ("POST", "/auth/login"): RoutePolicy(principals=frozenset({PRINCIPAL_PUBLIC})),
    ("POST", "/auth/logout"): RoutePolicy(principals=frozenset({PRINCIPAL_SESSION})),
    ("GET", "/auth/me"): RoutePolicy(principals=frozenset({PRINCIPAL_SESSION})),
    ("POST", "/auth/password"): RoutePolicy(principals=frozenset({PRINCIPAL_SESSION})),
    ("GET", "/validation/runs/{project}"): RoutePolicy(
        principals=frozenset({PRINCIPAL_MEMBER}),
        project_source="path",
        min_role="viewer",
    ),
}


def policy_for(method: str, path: str | None) -> RoutePolicy | None:
    """Look up the policy for `(method, path template)`. None if unclassified
    or if `path` is falsy (no route was matched)."""
    if not path:
        return None
    return ROUTE_POLICIES.get((method.upper(), path))
