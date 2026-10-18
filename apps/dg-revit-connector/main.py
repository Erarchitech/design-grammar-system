# -*- coding: utf-8 -*-
"""Revit MCP Server - entry point.

Exposes Revit to MCP clients. Every tool forwards to an HTTP endpoint served by
the revit-mcp pyRevit extension (``startup.py`` + ``revit_mcp/``) running
inside Revit.

Usage:
    uv run main.py                     # stdio (Claude Desktop / Claude Code)
    uv run main.py --http              # streamable HTTP on /mcp
    uv run main.py --sse               # legacy SSE on /sse + /messages/
    uv run main.py --combined          # streamable HTTP and SSE together

Environment:
    REVIT_HOST  host running Revit + pyRevit Routes   (default: localhost)
    REVIT_PORT  pyRevit Routes port                   (default: 48884)
    MCP_HOST    bind address for --http/--sse modes   (default: 127.0.0.1)
    MCP_PORT    port for --http/--sse modes           (default: 8000)
    DEGRAM_MODE 1 = launched by DeGram: stdio only, --http/--sse/--combined
                are refused (phase 1301 D-11)

This fork is read-only: only the tools in degram_readonly.ALLOWED_TOOLS exist.
"""

import argparse
import asyncio
import base64
import json
import os
import sys
from typing import Any, Dict, Optional, Union

import httpx
from mcp.server.fastmcp import FastMCP, Image

import degram_readonly

REVIT_HOST = os.environ.get("REVIT_HOST", "localhost")
REVIT_PORT = int(os.environ.get("REVIT_PORT", "48884"))
MCP_HOST = os.environ.get("MCP_HOST", "127.0.0.1")
MCP_PORT = int(os.environ.get("MCP_PORT", "8000"))

API_ROOT = "http://{}:{}/revit_mcp".format(REVIT_HOST, REVIT_PORT)
DEFAULT_TIMEOUT = 30.0
IMAGE_TIMEOUT = 60.0


def json_body(data: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    """Request kwargs for a JSON POST body that pyRevit Routes passes through.

    pyRevit parses ``application/json`` bodies itself and that parse fails under
    IronPython 3.4 before the route runs, so the body goes as ``text/plain`` and
    the route parses it (``revit_mcp.utils.parse_request_data``; 1301 UAT G-12).
    """
    return {
        "content": json.dumps(data or {}, ensure_ascii=False).encode("utf-8"),
        "headers": {"Content-Type": "text/plain; charset=utf-8"},
    }

UNREACHABLE_HINT = (
    "Error: cannot reach Revit at {root}.\n"
    "Check that:\n"
    "  1. Revit is open with a project (not just the start screen)\n"
    "  2. pyRevit Routes Server is enabled (pyRevit tab > Settings > Routes)\n"
    "  3. the revit-mcp pyRevit extension is installed and loaded\n"
    "Test in a browser: {root}/status/"
)
NOT_FOUND_HINT = (
    "Error: Revit does not provide the route '{path}' (HTTP 404).\n"
    "The pyRevit extension loaded in Revit is probably missing or a different "
    "version from this server. Reinstall the extension from this repository "
    "and reload pyRevit."
)
TIMEOUT_HINT = (
    "Error: Revit did not answer '{path}' within {secs:.0f}s.\n"
    "Revit may be busy or blocked by an open dialog; check the Revit window."
)

Payload = Dict[str, Any]
Result = Union[Payload, str]


class RevitClient(object):
    """Async HTTP client for the revit-mcp routes.

    One pooled connection is shared by all tool calls. Methods never raise:
    failures come back as an ``"Error: ..."`` string the model can read.
    """

    def __init__(self, root: str = API_ROOT):
        self.root = root
        self._http: Optional[httpx.AsyncClient] = None

    def _session(self) -> httpx.AsyncClient:
        if self._http is None or self._http.is_closed:
            self._http = httpx.AsyncClient(
                base_url=self.root,
                limits=httpx.Limits(max_connections=20, max_keepalive_connections=10),
            )
        return self._http

    async def _send(self, method: str, path: str, timeout: float, **kwargs) -> Union[httpx.Response, str]:
        try:
            return await self._session().request(method, path, timeout=timeout, **kwargs)
        except (httpx.ConnectError, httpx.ConnectTimeout):
            return UNREACHABLE_HINT.format(root=self.root)
        except httpx.TimeoutException:
            return TIMEOUT_HINT.format(path=path, secs=timeout)
        except httpx.HTTPError as exc:
            return "Error: request to {} failed: {}".format(path, exc)

    @staticmethod
    def _decode(path: str, response: Union[httpx.Response, str]) -> Result:
        if isinstance(response, str):
            return response
        if response.status_code == 404:
            return NOT_FOUND_HINT.format(path=path)
        try:
            body = response.json()
        except ValueError:
            return "Error: {} - {}".format(response.status_code, response.text)
        if response.status_code >= 400 and isinstance(body, dict) and "error" not in body:
            body = dict(body, error="HTTP {}".format(response.status_code))
        return body

    async def get(self, path: str, ctx=None, timeout: float = DEFAULT_TIMEOUT,
                  params: Optional[Payload] = None) -> Result:
        """GET a route and return its decoded JSON (or an error string)."""
        return self._decode(path, await self._send("GET", path, timeout, params=params))

    async def post(self, path: str, data: Optional[Payload] = None, ctx=None,
                   timeout: float = DEFAULT_TIMEOUT) -> Result:
        """POST a JSON body to a route and return its decoded JSON (or an error string)."""
        return self._decode(path, await self._send("POST", path, timeout, **json_body(data)))

    async def image(self, path: str, ctx=None) -> Union[Image, str]:
        """GET a route that returns ``{"image_data": <base64 png>}`` as an MCP image."""
        result = self._decode(path, await self._send("GET", path, IMAGE_TIMEOUT))
        if isinstance(result, str):
            return result
        encoded = result.get("image_data") if isinstance(result, dict) else None
        if not encoded:
            return "Error: {}".format(result.get("error") if isinstance(result, dict) else result)
        return Image(data=base64.b64decode(encoded), format="png")


class DegramClient(RevitClient):
    """Fail-closed, serialized client that returns structured outcomes (phase 1301).

    * every call runs under one asyncio lock; waiting for it longer than
      ``lock_timeout`` (30 s) is BUSY;
    * before each read it refuses with SETUP_INCOMPLETE when REVIT_HOST, the
      configured pyRevit Routes host, or a live probe of this machine's
      non-loopback addresses says port 48884 is not loopback-only (D-23);
    * failures are ``{"status": "error", "code": ..., "error": ...}`` objects,
      never free-text ``Error:`` strings; there is no automatic retry.
    """

    def __init__(self, root: str = API_ROOT, host: str = REVIT_HOST, port: int = REVIT_PORT):
        super().__init__(root)
        self.host = host
        self.port = port
        self.lock_timeout = DEFAULT_TIMEOUT
        self._lock: Optional[asyncio.Lock] = None
        self._lock_loop = None

    def _the_lock(self) -> asyncio.Lock:
        loop = asyncio.get_running_loop()
        if self._lock is None or self._lock_loop is not loop:
            self._lock, self._lock_loop = asyncio.Lock(), loop
        return self._lock

    async def setup_problem(self) -> Optional[Payload]:
        """None when reads may proceed, else the refusal outcome."""
        out = degram_readonly.error_outcome
        if not degram_readonly.is_loopback_host(self.host):
            return out("SETUP_INCOMPLETE", "REVIT_HOST must be a loopback address; refusing to read",
                       reason="REVIT_HOST_NOT_LOOPBACK", host=self.host)
        configured = degram_readonly.read_routes_config().get("host")
        if configured is not None and not degram_readonly.is_loopback_host(configured):
            return out("SETUP_INCOMPLETE",
                       "pyRevit Routes host is not loopback; set host = 127.0.0.1 and restart Revit",
                       reason="ROUTES_NOT_LOOPBACK", host=configured)
        answering = await asyncio.to_thread(degram_readonly.probe_non_loopback, self.port)
        if answering:
            return out("SETUP_INCOMPLETE",
                       "pyRevit Routes answers on a non-loopback address; set host = 127.0.0.1 and restart Revit",
                       reason="ROUTES_NOT_LOOPBACK", address=answering, port=self.port)
        return None

    def _outcome(self, path: str, response: httpx.Response) -> Union[Payload, list]:
        out = degram_readonly.error_outcome
        status = response.status_code
        try:
            body = response.json()
        except ValueError:
            body = None
        if degram_readonly.is_outcome(body):
            return body  # a route already answered with a structured outcome
        if status in (406, 408):
            return out("BUSY", "Revit refused or timed out the request (a dialog may be open)",
                       path=path, httpStatus=status)
        if status == 404 and not (isinstance(body, dict) and "error" in body):
            return out("EXTENSION_NOT_LOADED",
                       "Revit does not provide this route; the revit-mcp pyRevit extension is not loaded "
                       "or is a different version", path=path)
        if status == 503 and isinstance(body, dict) and "No active Revit document" in str(body.get("error")):
            return out("SETUP_INCOMPLETE", "No Revit project document is open",
                       reason="NO_DOCUMENT_OPEN", path=path)
        if status >= 400 or not isinstance(body, (dict, list)):
            message = None
            if isinstance(body, dict):
                message = body.get("error") or (body.get("exception") or {}).get("message")
            message = message or response.text[:300] or "HTTP {}".format(status)
            return out("ROUTE_ERROR", str(message), path=path, httpStatus=status)
        return body

    async def _call(self, method: str, path: str, timeout: float, **kwargs):
        out = degram_readonly.error_outcome
        lock = self._the_lock()
        try:
            await asyncio.wait_for(lock.acquire(), self.lock_timeout)
        except asyncio.TimeoutError:
            return out("BUSY", "Another Revit read is still in progress", path=path)
        try:
            problem = await self.setup_problem()
            if problem is not None:
                return problem
            try:
                response = await self._session().request(method, path, timeout=timeout, **kwargs)
            except (httpx.ConnectError, httpx.ConnectTimeout):
                if degram_readonly.read_routes_config().get("enabled") is False:
                    return out("ROUTES_DISABLED", "pyRevit Routes are disabled in the pyRevit settings",
                               path=path)
                return out("BRIDGE_OFF", "Cannot reach Revit at {}".format(self.root), path=path)
            except httpx.TimeoutException:
                return out("BUSY", "Revit did not answer within {:.0f}s".format(timeout), path=path)
            except httpx.HTTPError as exc:
                return out("ROUTE_ERROR", "request failed: {}".format(exc), path=path)
            return self._outcome(path, response)
        finally:
            lock.release()

    async def get(self, path: str, ctx=None, timeout: float = DEFAULT_TIMEOUT,
                  params: Optional[Payload] = None):
        return await self._call("GET", path, timeout, params=params)

    async def post(self, path: str, data: Optional[Payload] = None, ctx=None,
                   timeout: float = DEFAULT_TIMEOUT):
        return await self._call("POST", path, timeout, **json_body(data))

    async def image(self, path: str, ctx=None):
        return json.dumps(degram_readonly.error_outcome(
            "ROUTE_ERROR", "images are not available in read-only DeGram mode", path=path))


revit = DegramClient()
mcp = FastMCP(
    "Revit MCP Server",
    host=MCP_HOST,
    port=MCP_PORT,
    stateless_http=True,
    json_response=True,
)

from tools import register_tools  # noqa: E402  (needs `mcp` defined first)

register_tools(mcp, revit.get, revit.post, revit.image)


async def serve_http_and_sse() -> None:
    """Serve streamable HTTP (/mcp) and SSE (/sse, /messages/) from one app.

    The streamable-HTTP app owns the lifespan that starts its session manager,
    so the SSE routes are mounted onto it rather than the other way round.
    """
    import uvicorn

    app = mcp.streamable_http_app()
    app.routes.extend(mcp.sse_app().routes)
    config = uvicorn.Config(app, host=MCP_HOST, port=MCP_PORT,
                            log_level=mcp.settings.log_level.lower())
    await uvicorn.Server(config).serve()


def parse_args(argv=None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Revit MCP Server")
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--http", "--streamable-http", dest="transport", action="store_const",
                      const="streamable-http", help="serve streamable HTTP on /mcp")
    mode.add_argument("--sse", dest="transport", action="store_const", const="sse",
                      help="serve legacy SSE on /sse and /messages/")
    mode.add_argument("--combined", dest="transport", action="store_const", const="combined",
                      help="serve streamable HTTP and SSE together")
    parser.set_defaults(transport="stdio")
    return parser.parse_args(argv)


if __name__ == "__main__":
    transport = parse_args().transport
    try:
        degram_readonly.enforce_transport(transport)
    except degram_readonly.DegramModeError as exc:
        print(str(exc), file=sys.stderr)
        sys.exit(2)
    if degram_readonly.degram_mode():
        # stdout is the MCP channel; report on stderr. Reads re-check before every call.
        answering = degram_readonly.probe_non_loopback(REVIT_PORT)
        if answering:
            print("SETUP_INCOMPLETE ROUTES_NOT_LOOPBACK: port {} answers on {}; reads are refused".format(
                REVIT_PORT, answering), file=sys.stderr)
    if transport == "combined":
        import anyio

        print("Serving streamable HTTP (/mcp) and SSE (/sse, /messages/) on http://{}:{}".format(MCP_HOST, MCP_PORT))
        anyio.run(serve_http_and_sse)
    else:
        mcp.run(transport=transport)
