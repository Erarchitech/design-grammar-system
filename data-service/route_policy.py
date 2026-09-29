"""Deny-by-default route policy table (Phase 1205 "Security and Tenancy
Release Gate", D-03).

This module maps ``(method, route path template)`` to a :class:`RoutePolicy`.
``auth.require_principal`` looks up the policy for the route it is guarding
via ``request.scope["route"].path`` + ``request.method``; a route with no
entry here fails closed with 403 ``ROUTE_UNCLASSIFIED``.

Plan 1205-10 completed the table: every route in ``app.py`` plus the four
``/auth/*`` routes is classified here, and ``tests/test_route_inventory.py``
proves the table and the registered routes agree in both directions (D-14).
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
            ``"path"``, ``"body"``, ``"query"``, ``"filtered"`` (no project
            authorization; the handler filters its own output by membership),
            or ``"resource:<name>"`` (looked up in RESOURCE_RESOLVERS) -- or
            ``None`` for a route that carries no project scoping at all.
        min_role: the minimum membership role a "member"-permitted user
            principal needs (``role_satisfies`` semantics), or ``None`` when
            the route is not role-gated (e.g. a session-only route).
    """

    principals: frozenset[str]
    project_source: str | None = None
    min_role: str | None = None


# Registry of resource-project resolvers, keyed by name. A resolver takes the
# current Request and returns the owning project string, or ``None`` when the
# resource does not exist (it may be async). The paired ``not_found`` factory
# builds the HTTPException that answers BOTH an unknown resource and an
# unauthorised one, so a caller cannot tell the two apart (D-15 no-leak rule,
# ALGN12-20: no route reveals another project's credential/note/execution).
ResolverFn = Callable[[Any], "Awaitable[str | None] | str | None"]
NotFoundFn = Callable[[], Exception]
RESOURCE_RESOLVERS: dict[str, tuple[ResolverFn, NotFoundFn]] = {}


def register_resource_resolver(
    name: str, resolve: ResolverFn, not_found: NotFoundFn
) -> None:
    """Register a resource-project resolver under `name` for use by a
    RoutePolicy with ``project_source == f"resource:{name}"``."""
    RESOURCE_RESOLVERS[name] = (resolve, not_found)


def _p(
    *principals: str, source: str | None = None, role: str | None = None
) -> RoutePolicy:
    return RoutePolicy(
        principals=frozenset(principals), project_source=source, min_role=role
    )


_PUB = PRINCIPAL_PUBLIC
_SES = PRINCIPAL_SESSION
_ADM = PRINCIPAL_ADMIN
_MEM = PRINCIPAL_MEMBER
_CON = PRINCIPAL_CONNECTOR
_SVC = PRINCIPAL_SERVICE
_SELF = PRINCIPAL_CONNECTOR_SELF

# ── Route table (D-03/D-14) ──
#
# Authoritative classification of every route. A route absent from this table
# answers 403 ROUTE_UNCLASSIFIED at runtime, and the bidirectional completeness
# test in tests/test_route_inventory.py fails the suite. Grouped by app.py
# section.
ROUTE_POLICIES: dict[tuple[str, str], RoutePolicy] = {
    # ── health + auth account routes (auth_routes.py) ──
    ("GET", "/"): _p(_PUB),
    ("POST", "/auth/login"): _p(_PUB),
    ("POST", "/auth/logout"): _p(_SES),
    ("GET", "/auth/me"): _p(_SES),
    ("POST", "/auth/password"): _p(_SES),
    # ── project tenancy + invitations (Phase 1205-12, D-02/D-05) ──
    ("POST", "/auth/invites"): _p(_MEM, source="body", role="owner"),
    ("POST", "/auth/accept-invite"): _p(_PUB),
    ("GET", "/projects"): _p(_SES, source="filtered"),
    ("POST", "/projects"): _p(_SES),
    ("GET", "/projects/{project}/members"): _p(_MEM, source="path", role="owner"),
    ("DELETE", "/projects/{project}/members/{username}"): _p(_MEM, source="path", role="owner"),
    # ── named graph endpoints (Phase 1205-12, D-06) ──
    ("GET", "/graph/{project}"): _p(_MEM, source="path", role="viewer"),
    ("POST", "/graph/{project}/claim-untagged"): _p(_MEM, source="path", role="editor"),
    ("PUT", "/graph/{project}/node/{node_id}/property"): _p(_MEM, source="path", role="editor"),
    ("GET", "/rules/{project}"): _p(_MEM, source="path", role="viewer"),
    ("GET", "/rules/{project}/{rule_id}"): _p(_MEM, source="path", role="viewer"),
    ("GET", "/validation/view/{project}/{run_id}/entity/{dg_entity_id}"): _p(
        _MEM, source="path", role="viewer"
    ),
    ("GET", "/computgraph/candidates/{project}"): _p(_MEM, source="path", role="viewer"),
    # ── integration / settings ──
    ("GET", "/integration/speckle/project/{project}"): _p(_MEM, source="path", role="viewer"),
    ("PUT", "/integration/speckle/project/{project}"): _p(_MEM, source="path", role="owner"),
    ("GET", "/settings/speckle"): _p(_ADM),
    ("PUT", "/settings/speckle"): _p(_ADM),
    # ── LLM gateway ──
    ("GET", "/llm/settings"): _p(_SES),
    ("PUT", "/llm/settings"): _p(_ADM),
    ("DELETE", "/llm/settings"): _p(_ADM),
    ("POST", "/llm/generate"): _p(_SVC),
    ("POST", "/llm/settings/test"): _p(_ADM),
    ("GET", "/llm/models"): _p(_ADM),
    # ── connectors ──
    ("GET", "/connectors"): _p(_SES, source="filtered"),
    ("POST", "/connectors/{connector_id}/credentials"): _p(_MEM, source="body", role="editor"),
    ("DELETE", "/connectors/{connector_id}/credentials/{credential_id}"): _p(
        _MEM, source="resource:credential", role="editor"
    ),
    ("POST", "/connectors/heartbeat"): _p(_SELF),
    # ── reasoner ──
    ("GET", "/reasoner/settings"): _p(_SES),
    ("PUT", "/reasoner/settings"): _p(_ADM),
    ("POST", "/reasoner/consistency"): _p(_MEM, source="body", role="viewer"),
    # ── computgraph ──
    ("POST", "/computgraph/context/pull"): _p(_MEM, source="body", role="viewer"),
    ("POST", "/computgraph/recognize"): _p(_MEM, source="body", role="viewer"),
    ("POST", "/computgraph/publish"): _p(_MEM, _CON, source="body", role="editor"),
    ("POST", "/computgraph/validate"): _p(_MEM, source="body", role="viewer"),
    ("POST", "/computgraph/consult"): _p(_MEM, source="body", role="viewer"),
    ("POST", "/computgraph/generate-inputs"): _p(_MEM, source="body", role="editor"),
    ("POST", "/computgraph/candidates/accept"): _p(_MEM, source="body", role="editor"),
    # ── context (n8n-only) ──
    ("POST", "/context/assemble"): _p(_SVC),
    ("GET", "/context/debug"): _p(_SVC),
    ("POST", "/context/generate-cypher"): _p(_SVC),
    # ── identity ──
    ("POST", "/identity/mint"): _p(_MEM, source="body", role="editor"),
    ("GET", "/identity/resolve"): _p(_MEM, source="query", role="viewer"),
    ("POST", "/identity/bind"): _p(_MEM, source="body", role="editor"),
    ("GET", "/identity/{dg_id}/representations"): _p(_MEM, source="query", role="viewer"),
    ("DELETE", "/identity/{dg_id}/representations"): _p(_MEM, source="query", role="editor"),
    ("POST", "/identity/{dg_id}/properties"): _p(_MEM, source="query", role="editor"),
    ("GET", "/identity/{dg_id}/properties"): _p(_MEM, source="query", role="viewer"),
    # ── designstate capture (connector token, own bound-project check) ──
    ("POST", "/designstate/capture"): _p(_SELF),
    # ── validation ──
    ("POST", "/validation/publish"): _p(_MEM, _CON, source="body", role="editor"),
    ("GET", "/validation/runs/{project}"): _p(_MEM, source="path", role="viewer"),
    ("DELETE", "/validation/run/{project}/{run_id}"): _p(_MEM, source="path", role="editor"),
    ("GET", "/validation/view/{project}"): _p(_MEM, _CON, source="path", role="viewer"),
    ("GET", "/validation/view/{project}/{run_id}"): _p(_MEM, _CON, source="path", role="viewer"),
    ("GET", "/validation/view/{project}/{run_id}/{rule_id}"): _p(
        _MEM, _CON, source="path", role="viewer"
    ),
    # ── n8n relay + execution results ──
    ("POST", "/mcp"): _p(_SVC),
    ("POST", "/execution-result"): _p(_SVC),
    ("GET", "/execution-result/{execution_id}"): _p(
        _SES, source="resource:execution", role="viewer"
    ),
    ("POST", "/workflows/rules-ingest"): _p(_MEM, source="body", role="editor"),
    ("POST", "/workflows/graph-query"): _p(_MEM, source="body", role="viewer"),
    # ── knowledge ──
    ("POST", "/knowledge/ingest/folder"): _p(_ADM),
    ("GET", "/knowledge/notes/{project}"): _p(_MEM, source="path", role="viewer"),
    ("GET", "/knowledge/note/{note_id}"): _p(_MEM, source="resource:note", role="viewer"),
    ("PUT", "/knowledge/note/{note_id}"): _p(_MEM, source="resource:note", role="editor"),
    ("DELETE", "/knowledge/note/{note_id}"): _p(_MEM, source="resource:note", role="editor"),
    # ── rules ──
    ("GET", "/rules/{project}/{rule_id}/delete-preview"): _p(_MEM, source="path", role="viewer"),
    ("DELETE", "/rules/{project}/{rule_id}"): _p(_MEM, source="path", role="editor"),
    ("POST", "/rules/resolve-deletion"): _p(_MEM, source="body", role="editor"),
    ("POST", "/rules/bulk-delete"): _p(_MEM, source="body", role="editor"),
    ("POST", "/rules/check-conflict"): _p(_MEM, source="body", role="viewer"),
    ("POST", "/rules/supersede"): _p(_MEM, source="body", role="editor"),
    ("POST", "/rules/accept-overlap"): _p(_MEM, source="body", role="editor"),
    # ── sessions + update flow ──
    ("GET", "/knowledge/sessions/{project}"): _p(_MEM, source="path", role="viewer"),
    ("POST", "/design-rule-sessions"): _p(_MEM, source="body", role="editor"),
    ("GET", "/design-rule-sessions/{project}"): _p(_MEM, source="path", role="viewer"),
    ("POST", "/knowledge/update/match"): _p(_MEM, source="body", role="viewer"),
    ("POST", "/knowledge/update/propose"): _p(_MEM, source="body", role="editor"),
    ("POST", "/knowledge/update/confirm"): _p(_MEM, source="body", role="editor"),
}


def policy_for(method: str, path: str | None) -> RoutePolicy | None:
    """Look up the policy for `(method, path template)`. None if unclassified
    or if `path` is falsy (no route was matched)."""
    if not path:
        return None
    return ROUTE_POLICIES.get((method.upper(), path))
