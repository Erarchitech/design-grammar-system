# -*- coding: utf-8 -*-
"""DeGram read-only guard for the Revit MCP fork (phase 1301, D-10/D-11/D-13/D-23).

One module, imported from BOTH halves of the adapter, so the two allowlists
cannot drift apart:

* the pyRevit extension (``startup.py``, IronPython) registers only the routes
  in ``ALLOWED_ROUTES`` and nothing at all unless the Routes host is loopback;
* the MCP server (``main.py`` + ``tools/``, CPython) registers only the tools in
  ``ALLOWED_TOOLS``, refuses non-stdio transports in DeGram mode, and probes
  that port 48884 does not answer on any non-loopback local address.

Keep this file free of f-strings, type hints and third-party imports: it must
load under IronPython as well as CPython. The async client lives in main.py.
"""

import json
import os
import socket

# --- allowlists ---------------------------------------------------------------

#: MCP tools exposed to the agent. Every name is a read verb.
ALLOWED_TOOLS = frozenset([
    "get_revit_status",
    "get_revit_model_info",
    "list_open_documents",
    "get_selection_snapshot",
    "get_element_properties",
    "list_levels",
    "get_current_view_info",
    "list_category_parameters",
])

#: (HTTP method, route pattern) pairs the pyRevit extension may register.
#: POST appears twice only because the request needs a body; both routes read.
ALLOWED_ROUTES = frozenset([
    ("GET", "/status/"),
    ("GET", "/model_info/"),
    ("GET", "/list_open_documents/"),
    ("POST", "/selection_snapshot/"),
    ("GET", "/element_properties/<element_id>"),
    ("GET", "/list_levels/"),
    ("GET", "/current_view_info/"),
    ("POST", "/list_category_parameters/"),
])

#: Route modules that back allowed routes: (module under revit_mcp, register function).
#: Several are mixed read/write modules; ReadOnlyApi drops the write routes they
#: declare, so a write handler is imported but never reachable.
ALLOWED_ROUTE_MODULES = (
    ("status", "register_status_routes"),
    ("model_info", "register_model_info_routes"),
    ("documents", "register_document_read_routes"),
    ("views", "register_views_routes"),
    ("placement", "register_placement_routes"),
    ("parameters", "register_parameter_routes"),
    ("colors", "register_color_routes"),
)

#: Structured outcome codes returned by the MCP half and the document routes.
#: SETUP_INCOMPLETE carries a ``reason``: ROUTES_NOT_LOOPBACK (D-23),
#: REVIT_HOST_NOT_LOOPBACK or NO_DOCUMENT_OPEN.
ERROR_CODES = frozenset([
    "BUSY",
    "BRIDGE_OFF",
    "EXTENSION_NOT_LOADED",
    "ROUTES_DISABLED",
    "SETUP_INCOMPLETE",
    "IDENTITY_MISMATCH",
    "DOCUMENT_NOT_OPEN",
    "BAD_REQUEST",
    "ROUTE_ERROR",
])

ROUTES_PORT = 48884
PROBE_TIMEOUT_SECONDS = 0.3


# --- loopback helpers ---------------------------------------------------------

def _clean_host(host):
    text = "" if host is None else str(host).strip().strip('"').strip("'").strip()
    if text.startswith("[") and text.endswith("]"):
        text = text[1:-1]
    return text.split("%")[0].lower()


def is_loopback_host(host):
    """True only for an explicit loopback name or address. Unknown/empty is not loopback."""
    text = _clean_host(host)
    if not text:
        return False
    if text == "localhost" or text == "::1":
        return True
    if text.startswith("::ffff:"):  # IPv4-mapped IPv6
        text = text[len("::ffff:"):]
    if text in ("0:0:0:0:0:0:0:1", "0000:0000:0000:0000:0000:0000:0000:0001"):
        return True
    parts = text.split(".")
    if len(parts) == 4 and parts[0] == "127":
        try:
            return all(0 <= int(p) <= 255 for p in parts)
        except ValueError:
            return False
    return False


def _is_unspecified(addr):
    return _clean_host(addr) in ("", "0.0.0.0", "::", "0:0:0:0:0:0:0:0")


def configured_routes_host():
    """The pyRevit Routes host from the user config, or None when it cannot be read."""
    try:
        from pyrevit.userconfig import user_config

        return user_config.routes_host
    except Exception:
        return None


# --- pyRevit side: route allowlist -------------------------------------------

class ReadOnlyApi(object):
    """Proxy over ``pyrevit.routes.API`` that registers allowlisted routes only.

    Only ``route`` is exposed; any other attribute raises AttributeError so a
    forked module cannot reach around the filter.
    """

    def __init__(self, api, allowed=None):
        self._api = api
        self._allowed = ALLOWED_ROUTES if allowed is None else allowed
        self.registered = []
        self.dropped = []

    def route(self, pattern, methods=None):
        wanted = [str(m).upper() for m in (methods if methods else ["GET"])]
        keep = [m for m in wanted if (m, pattern) in self._allowed]
        for m in wanted:
            if m not in keep:
                self.dropped.append((m, pattern))

        def decorator(func):
            if keep:
                self._api.route(pattern, methods=keep)(func)
                for m in keep:
                    self.registered.append((m, pattern))
            return func

        return decorator


# --- MCP side: tool allowlist -------------------------------------------------

class ReadOnlyToolRegistry(object):
    """Proxy over FastMCP whose ``tool`` decorator drops non-allowlisted names.

    Mixed modules can still be imported and registered through it: the
    decorated function stays callable but never becomes an MCP tool.
    """

    def __init__(self, mcp, allowed=None):
        self._mcp = mcp
        self._allowed = ALLOWED_TOOLS if allowed is None else allowed

    def tool(self, *args, **kwargs):
        real = self._mcp.tool(*args, **kwargs)
        explicit = kwargs.get("name")
        if explicit is None and args and isinstance(args[0], str):
            explicit = args[0]

        def decorator(func):
            name = explicit or func.__name__
            if name in self._allowed:
                return real(func)
            return func

        return decorator


def is_outcome(value):
    return (isinstance(value, dict) and value.get("status") == "error"
            and isinstance(value.get("code"), str))


def error_outcome(code, message, **extra):
    outcome = {"status": "error", "code": code, "error": message}
    outcome.update(extra)
    return outcome


# --- MCP side: transport guard -----------------------------------------------

class DegramModeError(Exception):
    """Raised when the server is asked to do something DeGram mode forbids."""


def degram_mode(env=None):
    env = os.environ if env is None else env
    return str(env.get("DEGRAM_MODE", "")).strip() == "1"


def enforce_transport(transport, env=None):
    """D-11: in DeGram mode only stdio is allowed."""
    if degram_mode(env) and transport != "stdio":
        raise DegramModeError(
            "DEGRAM_TRANSPORT_REFUSED: DEGRAM_MODE=1 allows stdio only, "
            "got '{}' (no HTTP/SSE port may be opened)".format(transport))


# --- MCP side: loopback probe (D-23) ------------------------------------------

def local_addresses(hostname=None):
    """Non-loopback, non-wildcard addresses of this machine."""
    hostname = hostname or socket.gethostname()
    found = set()
    try:
        for info in socket.getaddrinfo(hostname, None):
            found.add(str(info[4][0]))
    except Exception:
        pass
    try:
        found.update(socket.gethostbyname_ex(hostname)[2])
    except Exception:
        pass
    return sorted(a for a in found if not is_loopback_host(a) and not _is_unspecified(a))


def _connect(addr, port, timeout):
    """True when a TCP connect to (addr, port) succeeds within ``timeout`` seconds."""
    family = socket.AF_INET6 if ":" in addr else socket.AF_INET
    sock = socket.socket(family, socket.SOCK_STREAM)
    try:
        sock.settimeout(timeout)
        sock.connect((addr.split("%")[0], port))
        return True
    except Exception:
        return False
    finally:
        try:
            sock.close()
        except Exception:
            pass


def probe_non_loopback(port=ROUTES_PORT, timeout=PROBE_TIMEOUT_SECONDS, addresses=None):
    """Return the first non-loopback local address answering on ``port``, else None."""
    for addr in (local_addresses() if addresses is None else addresses):
        if _connect(addr, port, timeout):
            return addr
    return None


def pyrevit_config_path(env=None):
    env = os.environ if env is None else env
    explicit = env.get("PYREVIT_CONFIG")
    if explicit:
        return explicit
    appdata = env.get("APPDATA")
    return os.path.join(appdata, "pyRevit", "pyRevit_config.ini") if appdata else None


def read_routes_config(path=None):
    """``{"enabled": bool|None, "host": str|None}`` from the pyRevit ini, best effort."""
    result = {"enabled": None, "host": None}
    path = path or pyrevit_config_path()
    if not path or not os.path.isfile(path):
        return result
    try:
        import configparser

        parser = configparser.ConfigParser(interpolation=None)
        parser.read(path, encoding="utf-8")
        if parser.has_section("routes"):
            if parser.has_option("routes", "enabled"):
                result["enabled"] = parser.get("routes", "enabled").strip().strip('"').lower() == "true"
            if parser.has_option("routes", "host"):
                result["host"] = _clean_host(parser.get("routes", "host"))
    except Exception:
        pass
    return result
