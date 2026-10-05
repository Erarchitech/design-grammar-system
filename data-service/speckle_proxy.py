"""Project-authorised Speckle geometry proxy (Phase 1301 plan 09, D-21, DGCL-03).

Before this module ``/validation/view`` handed every interactive caller the one Speckle
read token of the whole Speckle server, and the embedded DeGram view would have
inherited it. Now the browser never holds a Speckle credential:

* ``resolve_view_resources`` does, server side and with the read token, the model/version
  to root-object resolution the viewer's ``UrlHelper`` used to do in the browser, and
  returns concrete object URLs that already point at this proxy
  (``/data-service/speckle-proxy/{project}/objects/{speckleProjectId}/{objectId}``).
* ``proxy_objects`` streams the object endpoints the Speckle object loader calls, for the
  Speckle project bound to the caller's DG project only. A request for any other Speckle
  project answers 403 ``SPECKLE_PROJECT_FORBIDDEN`` before Speckle is contacted.

The route handlers live in ``app.py`` (they need the Neo4j binding lookup and the
settings); this module takes both as arguments so it has no ``app`` import. Every
upstream hop goes through ``_transport_factory`` so tests inject an
``httpx.MockTransport`` and never open a connection.

Never log or echo the token: every error below carries a fixed code and message, never
the upstream body or an exception string that could include a header.
"""

from __future__ import annotations

import json
import logging
import os
import re
from typing import Any, AsyncIterator
from urllib.parse import quote

import anyio
import httpx
from fastapi import HTTPException
from fastapi.responses import StreamingResponse

_LOGGER = logging.getLogger(__name__)

# Speckle object ids are 32 lowercase hex characters (the object hash).
OBJECT_ID_PATTERN = re.compile(r"^[0-9a-f]{32}$")

# The object loader batches 15000 ids per request; one request never needs more.
MAX_OBJECT_IDS = 20000
# 20000 ids at 34 bytes each is under 700 KiB; 4 MiB leaves room for an attribute mask.
MAX_BODY_BYTES = 4 * 1024 * 1024

UPSTREAM_TIMEOUT = httpx.Timeout(connect=10.0, read=60.0, write=30.0, pool=10.0)
RESOLVE_TIMEOUT = httpx.Timeout(10.0)

ERR_FORBIDDEN = "SPECKLE_PROJECT_FORBIDDEN"
ERR_UNBOUND = "SPECKLE_PROJECT_UNBOUND"
ERR_UPSTREAM = "SPECKLE_UPSTREAM_ERROR"
ERR_NOT_CONFIGURED = "SPECKLE_NOT_CONFIGURED"
ERR_OBJECT_ID = "SPECKLE_OBJECT_ID_INVALID"
ERR_TOO_LARGE = "SPECKLE_BODY_TOO_LARGE"

KIND_OBJECT = "object"
KIND_SINGLE = "single"
KIND_STREAM = "object-stream"
KIND_GETOBJECTS = "getobjects"
_GET_KINDS = {KIND_OBJECT, KIND_SINGLE}
_POST_KINDS = {KIND_STREAM, KIND_GETOBJECTS}

_VERSION_QUERY = (
    "query ViewerUrlHelperModelVersion($modelId: String!, $projectId: String!, "
    "$versionId: String!) { project(id: $projectId) { model(id: $modelId) "
    "{ version(id: $versionId) { referencedObject } } } }"
)


def _transport_factory() -> httpx.AsyncBaseTransport | httpx.BaseTransport | None:
    """Test seam. Production returns ``None`` (the real network); tests replace this
    with a callable returning an ``httpx.MockTransport``."""
    return None


def proxy_error(status: int, code: str, error: str, hint: str) -> HTTPException:
    """Same ``{error, hint, code}`` detail shape as ``auth.auth_error``."""
    return HTTPException(status_code=status, detail={"error": error, "hint": hint, "code": code})


def public_prefix() -> str:
    """Path the browser reaches this data-service under (the nginx ``/data-service/``
    location). Overridable for a deployment that mounts it elsewhere."""
    value = os.getenv("DG_DATA_SERVICE_PUBLIC_PREFIX", "/data-service").strip().rstrip("/")
    return value if value.startswith("/") else f"/{value}"


def proxy_object_url(project: str, speckle_project_id: str, object_id: str) -> str:
    return (
        f"{public_prefix()}/speckle-proxy/{quote(project, safe='')}"
        f"/objects/{quote(speckle_project_id, safe='')}/{object_id}"
    )


def _graphql_url(settings: Any) -> str:
    return f"{str(settings.internal_url).rstrip('/')}/graphql"


def _auth_headers(settings: Any) -> dict[str, str]:
    return {"Authorization": f"Bearer {settings.read_token}"}


def _resolve_root_object(
    client: httpx.Client, settings: Any, speckle_project_id: str, model_id: str, version_id: str
) -> str:
    response = client.post(
        _graphql_url(settings),
        headers={**_auth_headers(settings), "Content-Type": "application/json"},
        json={
            "query": _VERSION_QUERY,
            "variables": {"projectId": speckle_project_id, "modelId": model_id, "versionId": version_id},
        },
    )
    if response.status_code != 200:
        raise ValueError(f"graphql status {response.status_code}")
    data = response.json().get("data") or {}
    version = ((data.get("project") or {}).get("model") or {}).get("version") or {}
    referenced = version.get("referencedObject")
    if not isinstance(referenced, str) or not OBJECT_ID_PATTERN.match(referenced):
        raise ValueError("referencedObject is not a Speckle object hash")
    return referenced


def resolve_view_resources(
    project: str, run: dict[str, Any], settings: Any, bound_project_id: str | None
) -> tuple[list[str], str | None]:
    """Resolve the run's base and validation model versions to DG-proxy object URLs.

    Returns ``(urls, error_code)``. ``urls`` is empty whenever ``error_code`` is set, so a
    viewer never loads half a model. Nothing here ever places a credential in the result:
    the URLs name only the DG project, the bound Speckle project and an object hash.
    """
    if not getattr(settings, "read_token", ""):
        return [], ERR_NOT_CONFIGURED
    if not bound_project_id:
        return [], ERR_UNBOUND
    speckle_project_id = str(run.get("speckleProjectId") or "").strip()
    if speckle_project_id != bound_project_id:
        return [], ERR_FORBIDDEN

    pairs = [
        (run.get("baseModelId"), run.get("baseVersionId")),
        (run.get("validationModelId"), run.get("validationVersionId")),
    ]
    urls: list[str] = []
    try:
        with httpx.Client(transport=_transport_factory(), timeout=RESOLVE_TIMEOUT, follow_redirects=False) as client:
            for model_id, version_id in pairs:
                if not model_id or not version_id:
                    continue
                object_id = _resolve_root_object(client, settings, speckle_project_id, str(model_id), str(version_id))
                urls.append(proxy_object_url(project, speckle_project_id, object_id))
    except (httpx.HTTPError, ValueError, KeyError, TypeError, AttributeError) as exc:
        # Class name only: an httpx error string can carry the request URL, and a
        # parser error can carry upstream text. Neither is ever the token, but the
        # fixed shape keeps that a guarantee rather than a hope.
        _LOGGER.warning("speckle_proxy: view resource resolution failed (%s)", type(exc).__name__)
        return [], ERR_UPSTREAM
    return urls, None


def _check_bound_project(speckle_project_id: str, bound_project_id: str | None) -> None:
    if not bound_project_id:
        raise proxy_error(
            404,
            ERR_UNBOUND,
            "No Speckle project is bound to this DG project.",
            "Bind a Speckle project in the project's Speckle integration settings.",
        )
    if speckle_project_id != bound_project_id:
        raise proxy_error(
            403,
            ERR_FORBIDDEN,
            "That Speckle project is not bound to this DG project.",
            "Request geometry only for the Speckle project the DG project is bound to.",
        )


def _invalid_ids(message: str) -> HTTPException:
    return proxy_error(422, ERR_OBJECT_ID, message, "Send 32-character lowercase hexadecimal Speckle object ids.")


def _parse_ids(raw: Any) -> list[str]:
    if not isinstance(raw, list) or not raw:
        raise _invalid_ids("objectIds must be a non-empty list.")
    if len(raw) > MAX_OBJECT_IDS:
        raise _invalid_ids("Too many object ids in one request.")
    for item in raw:
        if not isinstance(item, str) or not OBJECT_ID_PATTERN.match(item):
            raise _invalid_ids("Every object id must be a Speckle object hash.")
    return list(raw)


def _build_post_body(kind: str, body: bytes) -> bytes:
    if len(body) > MAX_BODY_BYTES:
        raise proxy_error(413, ERR_TOO_LARGE, "The request body is too large.", "Request fewer objects at a time.")
    try:
        parsed = json.loads(body)
    except (ValueError, RecursionError):
        raise _invalid_ids("The request body must be JSON.") from None
    if not isinstance(parsed, dict):
        raise _invalid_ids("The request body must be a JSON object.")
    if kind == KIND_GETOBJECTS and "objects" in parsed:
        # Legacy wire shape: {"objects": "<json array string>"}.
        try:
            decoded = json.loads(parsed["objects"]) if isinstance(parsed["objects"], str) else parsed["objects"]
        except (ValueError, RecursionError):
            raise _invalid_ids("objects must be a JSON array of object ids.") from None
        ids = _parse_ids(decoded)
    else:
        ids = _parse_ids(parsed.get("objectIds"))
    if kind == KIND_GETOBJECTS:
        return json.dumps({"objects": json.dumps(ids)}).encode()
    forwarded: dict[str, Any] = {"objectIds": ids}
    if "attributeMask" in parsed:
        if not isinstance(parsed["attributeMask"], dict):
            raise _invalid_ids("attributeMask must be an object.")
        forwarded["attributeMask"] = parsed["attributeMask"]
    return json.dumps(forwarded).encode()


def _upstream_target(kind: str, speckle_project_id: str, object_id: str | None) -> tuple[str, str]:
    spid = quote(speckle_project_id, safe="")
    if kind == KIND_OBJECT:
        return "GET", f"/objects/{spid}/{object_id}"
    if kind == KIND_SINGLE:
        return "GET", f"/objects/{spid}/{object_id}/single"
    if kind == KIND_STREAM:
        return "POST", f"/api/v2/projects/{spid}/object-stream/"
    return "POST", f"/api/getobjects/{spid}"


def _upstream_failure() -> HTTPException:
    return proxy_error(
        502,
        ERR_UPSTREAM,
        "The Speckle server did not return the requested objects.",
        "Check that the Speckle server is reachable and the project still holds the model.",
    )


async def _close(response: httpx.Response, client: httpx.AsyncClient) -> None:
    # Shielded so a cancelled request (client disconnect) still releases the upstream
    # connection instead of leaking it.
    with anyio.CancelScope(shield=True):
        await response.aclose()
        await client.aclose()


async def _relay(response: httpx.Response, client: httpx.AsyncClient) -> AsyncIterator[bytes]:
    try:
        async for chunk in response.aiter_bytes():
            yield chunk
    finally:
        await _close(response, client)


async def proxy_objects(
    *,
    kind: str,
    speckle_project_id: str,
    bound_project_id: str | None,
    settings: Any,
    object_id: str | None = None,
    body: bytes | None = None,
) -> StreamingResponse:
    """Stream one Speckle object endpoint for the bound Speckle project only.

    Checks run in this order and always before Speckle is contacted: the DG project has a
    binding (404 unbound), the requested Speckle project equals it (403 forbidden), the
    object ids are hashes and the body is sane (422/413), the read token is configured
    (503). One upstream call per request, redirects never followed, the upstream body
    never echoed on failure.
    """
    if kind not in _GET_KINDS | _POST_KINDS:
        raise ValueError(f"unknown proxy kind {kind!r}")
    _check_bound_project(speckle_project_id, bound_project_id)
    if kind in _GET_KINDS:
        if not isinstance(object_id, str) or not OBJECT_ID_PATTERN.match(object_id):
            raise _invalid_ids("The object id must be a Speckle object hash.")
        payload = None
    else:
        payload = _build_post_body(kind, body or b"")
    if not getattr(settings, "read_token", ""):
        raise proxy_error(
            503,
            ERR_NOT_CONFIGURED,
            "Speckle geometry access is not configured.",
            "Ask an administrator to configure the Speckle server connection.",
        )

    method, path = _upstream_target(kind, speckle_project_id, object_id)
    headers = _auth_headers(settings)
    headers["Accept-Encoding"] = "identity"
    if payload is not None:
        headers["Content-Type"] = "application/json"
    headers["Accept"] = "application/json" if kind == KIND_OBJECT or kind == KIND_SINGLE else "text/plain"

    client = httpx.AsyncClient(
        base_url=str(settings.internal_url).rstrip("/"),
        transport=_transport_factory(),
        timeout=UPSTREAM_TIMEOUT,
        follow_redirects=False,
    )
    try:
        request = client.build_request(method, path, headers=headers, content=payload)
        response = await client.send(request, stream=True)
    except httpx.HTTPError as exc:
        await client.aclose()
        _LOGGER.warning("speckle_proxy: upstream request failed (%s)", type(exc).__name__)
        raise _upstream_failure() from None
    if response.status_code != 200:
        await _close(response, client)
        _LOGGER.warning("speckle_proxy: upstream answered %s", response.status_code)
        raise _upstream_failure()

    content_type = response.headers.get("content-type", "application/octet-stream")
    return StreamingResponse(
        _relay(response, client),
        status_code=200,
        media_type=None,
        headers={"Content-Type": content_type, "Cache-Control": "private, no-store"},
    )
