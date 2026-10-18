# -*- coding: utf-8 -*-
"""Transport hygiene shared by both halves of the DG Revit connector.

The Design Grammars owner lifted every Revit restriction on 2026-10-18
(D-45), so this module no longer allowlists routes or tools: the extension
registers all of them and the MCP server exposes all of them. What remains is
transport hygiene, not a Revit restriction:

* the pyRevit Routes host must be loopback before the extension registers
  anything (``configured_routes_host`` / ``is_loopback_host``);
* the MCP client refuses a non-loopback ``REVIT_HOST`` or a Routes server that
  answers on a non-loopback local address;
* ``DEGRAM_MODE=1`` allows the stdio transport only, so no HTTP/SSE port is
  ever opened for DeGram.

Keep this file free of f-strings, type hints and third-party imports: it must
load under IronPython as well as CPython. The async client lives in main.py.
"""

import os
import socket

#: Structured outcome codes returned by the MCP half and the document routes.
#: SETUP_INCOMPLETE carries a ``reason``: ROUTES_NOT_LOOPBACK,
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


# --- structured outcomes ------------------------------------------------------

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
    """In DeGram mode only stdio is allowed: no HTTP/SSE port (1301 D-11)."""
    if degram_mode(env) and transport != "stdio":
        raise DegramModeError(
            "DEGRAM_TRANSPORT_REFUSED: DEGRAM_MODE=1 allows stdio only, "
            "got '{}' (no HTTP/SSE port may be opened)".format(transport))


# --- MCP side: loopback probe -------------------------------------------------

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
