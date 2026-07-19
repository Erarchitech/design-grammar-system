"""TCP client for the DG CANVAS LISTENER bridge (Phase 33 Plan 03: BRDG-02/BRDG-04).

Speaks the locked wire contract (identical to Plan 01's C# listener):
newline-terminated UTF-8 JSON request `{"type": ..., "parameters": {...}}`,
single-line JSON response envelope
`{"bridge":"dg","version":1,"status":"ok"|"error", ...}`.

This is a raw `socket` client, not `httpx` — the bridge speaks newline-JSON
TCP, not HTTP (33-RESEARCH.md "Standard Stack"). Connect/read are both
explicitly bounded so a refused connection or a hung/never-terminating
listener degrades to a fast, structured 503 — never a hang (T-33-06).

`_structured_error_response` is imported lazily inside `_call` (not at module
scope) to avoid a circular import: `app.py` imports this module at module
scope (`import gh_bridge`), so importing `app` back at this module's own
import time would deadlock the import graph. Importing it inside the
function body defers the lookup until `app` has finished loading.
"""

from __future__ import annotations

import json
import os
import socket
from typing import Any

GH_BRIDGE_HOST = os.getenv("GH_BRIDGE_HOST", "host.docker.internal")
GH_BRIDGE_PORT = int(os.getenv("GH_BRIDGE_PORT", "8720"))
CONNECT_TIMEOUT_SECONDS = 5.0
READ_TIMEOUT_SECONDS = 30.0
# Guards the readline() call so a malformed, oversized, or never-terminating
# response cannot exhaust memory or hang the request (T-33-06).
MAX_RESPONSE_BYTES = 10 * 1024 * 1024  # 10 MiB


def _call(command_type: str, parameters: dict) -> dict:
    """Send one `{type, parameters}` request line, read one response line.

    Returns the envelope's `result` payload on `status == "ok"`. Raises a
    structured HTTPException (502) on `status == "error"`, or (503,
    GH_BRIDGE_UNREACHABLE) on any connect/read failure — bounded, never a hang.
    """
    from app import _structured_error_response

    try:
        with socket.create_connection(
            (GH_BRIDGE_HOST, GH_BRIDGE_PORT), timeout=CONNECT_TIMEOUT_SECONDS
        ) as sock:
            sock.settimeout(READ_TIMEOUT_SECONDS)
            request = json.dumps({"type": command_type, "parameters": parameters}) + "\n"
            sock.sendall(request.encode("utf-8"))
            buffered = sock.makefile("r", encoding="utf-8")
            line = buffered.readline(MAX_RESPONSE_BYTES)
            if not line:
                raise ConnectionError("Bridge closed the connection without a response.")
    except (ConnectionRefusedError, socket.timeout, OSError) as exc:
        raise _structured_error_response(
            f"Grasshopper bridge unreachable at {GH_BRIDGE_HOST}:{GH_BRIDGE_PORT}: {exc}",
            "Start Rhino and enable DG CANVAS LISTENER (port 8720).",
            "GH_BRIDGE_UNREACHABLE",
            503,
        ) from exc

    # A readline() that hit the bound returns a *truncated* line with no trailing
    # newline -- surface that as a structured 502 instead of letting the fragment
    # fall through to json.loads and become an unhandled 500 (WR-04). Note the
    # file object is text-mode, so the bound is a character count, not bytes.
    if not line.endswith("\n") and len(line) >= MAX_RESPONSE_BYTES:
        raise _structured_error_response(
            f"Grasshopper bridge response exceeded the {MAX_RESPONSE_BYTES}-character bound.",
            "Check the DG CANVAS LISTENER version (wire protocol v1).",
            "GH_BRIDGE_BAD_RESPONSE",
            502,
        )

    # Malformed or non-object responses must map to structured errors, never an
    # unhandled 500 (T-33-06, WR-04).
    try:
        envelope: dict[str, Any] = json.loads(line)
    except ValueError as exc:
        raise _structured_error_response(
            f"Grasshopper bridge returned a malformed response: {exc}",
            "Check the DG CANVAS LISTENER version (wire protocol v1).",
            "GH_BRIDGE_BAD_RESPONSE",
            502,
        ) from exc

    if not isinstance(envelope, dict):
        raise _structured_error_response(
            "Grasshopper bridge returned a non-object response.",
            "Check the DG CANVAS LISTENER version (wire protocol v1).",
            "GH_BRIDGE_BAD_RESPONSE",
            502,
        )

    if envelope.get("status") == "error":
        err = envelope.get("error") or {}
        raise _structured_error_response(
            str(err.get("message", "The bridge returned an error.")),
            "The listener rejected the command.",
            str(err.get("code", "GH_BRIDGE_ERROR")),
            502,
        )

    return envelope.get("result", envelope)


def get_canvas_context(project: str) -> dict:
    """Return the live cgContextJson v1 document from the canvas (unstamped)."""
    return _call("get_canvas_context", {"project": project})


def get_selection() -> dict:
    """Return `{"selection": [...]}` — currently-selected instance GUIDs."""
    return _call("get_selection", {})


def preview_structure(structure: dict) -> dict:
    """Forward a recognized-structure preview request to the DG CANVAS
    LISTENER and return its live preview result unchanged (e.g.
    `{"previewed": N}`)."""
    return _call("preview_structure", structure)


def clear_preview() -> dict:
    """Forward a clear-preview request to the DG CANVAS LISTENER and return
    its live result unchanged (e.g. `{"cleared": True}`)."""
    return _call("clear_preview", {})


def get_preview_status() -> dict:
    """Forward a preview-status request to the DG CANVAS LISTENER and return
    its live pending-proposal result unchanged."""
    return _call("get_preview_status", {})
