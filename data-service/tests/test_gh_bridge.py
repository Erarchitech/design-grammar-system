"""Tests for the gh_bridge.py TCP client (Phase 33 Plan 03: BRDG-02/BRDG-04).

Follows the existing test pattern from test_reasoner.py: FastAPI TestClient
style monkeypatching, but here the target is a raw `socket.create_connection`
call — no real socket is ever opened. Mirrors the module's own composed
example in 33-RESEARCH.md.
"""

from __future__ import annotations

import json
import os
import socket
import sys

import pytest
from fastapi import HTTPException

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

os.environ.setdefault("LLM_MASTER_SECRET", "test-master-secret")

import gh_bridge  # noqa: E402


class _FakeMakefile:
    """Minimal stand-in for `socket.makefile("r", ...)` — only .readline(n) used."""

    def __init__(self, line: str | None = None, raise_exc: Exception | None = None):
        self._line = line
        self._raise_exc = raise_exc

    def readline(self, size=-1):
        if self._raise_exc is not None:
            raise self._raise_exc
        return self._line


class _FakeSocket:
    """Minimal stand-in for the object returned by `socket.create_connection(...)`.

    Supports the `with socket.create_connection(...) as sock:` context-manager
    usage plus `.settimeout()`, `.sendall()`, `.makefile()`.
    """

    def __init__(self, line: str | None = None, read_exc: Exception | None = None):
        self.sent = []
        self.timeouts = []
        self._makefile = _FakeMakefile(line=line, raise_exc=read_exc)

    def __enter__(self):
        return self

    def __exit__(self, *exc_info):
        return False

    def settimeout(self, value):
        self.timeouts.append(value)

    def sendall(self, data):
        self.sent.append(data)

    def makefile(self, mode, encoding=None):
        return self._makefile


def _ok_envelope_line(result: dict) -> str:
    return json.dumps({"bridge": "dg", "version": 1, "status": "ok", "result": result}) + "\n"


def _error_envelope_line(message: str, code: str) -> str:
    return (
        json.dumps(
            {
                "bridge": "dg",
                "version": 1,
                "status": "error",
                "error": {"message": message, "code": code},
            }
        )
        + "\n"
    )


# ── Success path ──


class TestCallSuccess:
    def test_get_canvas_context_returns_result_payload(self, monkeypatch):
        """A valid status=='ok' envelope returns the `result` dict — no raise."""
        canned = _ok_envelope_line({"documentId": "d1", "procedures": []})
        fake_sock = _FakeSocket(line=canned)

        captured_connect = {}

        def fake_create_connection(address, timeout=None):
            captured_connect["address"] = address
            captured_connect["timeout"] = timeout
            return fake_sock

        monkeypatch.setattr(gh_bridge.socket, "create_connection", fake_create_connection)

        result = gh_bridge.get_canvas_context("p1")

        assert result == {"documentId": "d1", "procedures": []}
        assert captured_connect["address"] == (gh_bridge.GH_BRIDGE_HOST, gh_bridge.GH_BRIDGE_PORT)
        assert captured_connect["timeout"] == gh_bridge.CONNECT_TIMEOUT_SECONDS
        assert gh_bridge.READ_TIMEOUT_SECONDS in fake_sock.timeouts
        # Request line sent as newline-terminated UTF-8 JSON matching the wire contract.
        sent_bytes = fake_sock.sent[0]
        sent = json.loads(sent_bytes.decode("utf-8").rstrip("\n"))
        assert sent == {"type": "get_canvas_context", "parameters": {"project": "p1"}}

    def test_preview_structure_stub_returns_without_raising(self, monkeypatch):
        """The preview_structure stub result (supported == False) flows through untouched."""
        canned = _ok_envelope_line({"supported": False})
        fake_sock = _FakeSocket(line=canned)
        monkeypatch.setattr(
            gh_bridge.socket, "create_connection", lambda address, timeout=None: fake_sock
        )

        result = gh_bridge.preview_structure({"nodes": []})

        assert result == {"supported": False}

    def test_clear_preview_stub_returns_without_raising(self, monkeypatch):
        canned = _ok_envelope_line({"supported": False})
        fake_sock = _FakeSocket(line=canned)
        monkeypatch.setattr(
            gh_bridge.socket, "create_connection", lambda address, timeout=None: fake_sock
        )

        result = gh_bridge.clear_preview()

        assert result == {"supported": False}


# ── Refusal / timeout -> bounded 503 GH_BRIDGE_UNREACHABLE ──


class TestUnreachableBridge:
    def test_connection_refused_maps_to_structured_503(self, monkeypatch):
        def fake_create_connection(address, timeout=None):
            raise ConnectionRefusedError("refused")

        monkeypatch.setattr(gh_bridge.socket, "create_connection", fake_create_connection)

        with pytest.raises(HTTPException) as exc_info:
            gh_bridge.get_canvas_context("p1")

        assert exc_info.value.status_code == 503
        detail = exc_info.value.detail
        assert detail["code"] == "GH_BRIDGE_UNREACHABLE"
        assert "DG CANVAS LISTENER" in detail["hint"]
        assert "8720" in detail["hint"] or str(gh_bridge.GH_BRIDGE_PORT) in detail["hint"]

    def test_read_timeout_maps_to_bounded_structured_503(self, monkeypatch):
        """A socket.timeout on read (not connect) maps to the same bounded 503 —
        never a hang. The fake raises immediately so this test completes in
        well under the real READ_TIMEOUT_SECONDS budget."""
        fake_sock = _FakeSocket(read_exc=socket.timeout("read timed out"))
        monkeypatch.setattr(
            gh_bridge.socket, "create_connection", lambda address, timeout=None: fake_sock
        )

        with pytest.raises(HTTPException) as exc_info:
            gh_bridge.get_selection()

        assert exc_info.value.status_code == 503
        assert exc_info.value.detail["code"] == "GH_BRIDGE_UNREACHABLE"

    def test_generic_os_error_maps_to_bounded_structured_503(self, monkeypatch):
        def fake_create_connection(address, timeout=None):
            raise OSError("network unreachable")

        monkeypatch.setattr(gh_bridge.socket, "create_connection", fake_create_connection)

        with pytest.raises(HTTPException) as exc_info:
            gh_bridge.get_canvas_context("p1")

        assert exc_info.value.status_code == 503
        assert exc_info.value.detail["code"] == "GH_BRIDGE_UNREACHABLE"


# ── Envelope status=="error" -> 502 carrying the listener's message/code ──


class TestErrorEnvelope:
    def test_error_envelope_maps_to_502_with_listener_code(self, monkeypatch):
        canned = _error_envelope_line("Unknown command type.", "UNKNOWN_COMMAND")
        fake_sock = _FakeSocket(line=canned)
        monkeypatch.setattr(
            gh_bridge.socket, "create_connection", lambda address, timeout=None: fake_sock
        )

        with pytest.raises(HTTPException) as exc_info:
            gh_bridge.get_canvas_context("p1")

        assert exc_info.value.status_code == 502
        detail = exc_info.value.detail
        assert detail["code"] == "UNKNOWN_COMMAND"
        assert "Unknown command type." in detail["error"]


# ── Empty response (connection closed without a line) ──


class TestEmptyResponse:
    def test_empty_line_maps_to_bounded_structured_503(self, monkeypatch):
        fake_sock = _FakeSocket(line="")
        monkeypatch.setattr(
            gh_bridge.socket, "create_connection", lambda address, timeout=None: fake_sock
        )

        with pytest.raises(HTTPException) as exc_info:
            gh_bridge.get_canvas_context("p1")

        assert exc_info.value.status_code == 503
        assert exc_info.value.detail["code"] == "GH_BRIDGE_UNREACHABLE"


# ── Source assertions (bounded reads, correct timeout wiring) ──


class TestSourceContract:
    def test_max_response_bytes_constant_exists_and_positive(self):
        assert gh_bridge.MAX_RESPONSE_BYTES > 0

    def test_readline_bounded_by_max_response_bytes(self, monkeypatch):
        """The readline call must pass MAX_RESPONSE_BYTES as a bound (T-33-06)."""
        canned = _ok_envelope_line({"ok": True})

        captured = {}

        class BoundedFakeMakefile(_FakeMakefile):
            def readline(self, size=-1):
                captured["size"] = size
                return super().readline(size)

        fake_sock = _FakeSocket(line=canned)
        fake_sock._makefile = BoundedFakeMakefile(line=canned)
        monkeypatch.setattr(
            gh_bridge.socket, "create_connection", lambda address, timeout=None: fake_sock
        )

        gh_bridge.get_canvas_context("p1")

        assert captured["size"] == gh_bridge.MAX_RESPONSE_BYTES
