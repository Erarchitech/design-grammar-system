# -*- coding: utf-8 -*-
"""DG Revit connector guarantees, proven offline (no Revit, no pyRevit).

Both halves are covered:

* the pyRevit extension (``startup.py``) registers every route module under the
  Routes API name ``dg_revit``, writes included, and registers nothing at all
  unless the Routes host is loopback;
* the MCP server (``main.mcp``) exposes every upstream tool plus the four DG
  connector tools, and refuses non-stdio transports when launched for DeGram.

The fake Revit runtime lives in ``pyrevit_stubs.py`` so
``test_degram_documents.py`` can share it.
"""

import ast
import asyncio
import importlib
import inspect
import json
import os
import pkgutil
import subprocess
import sys

import pytest

import dg_transport as dt
from pyrevit_stubs import ROOT, install_pyrevit_stubs, load_startup

CONTRACT = os.path.join(ROOT, "tests", "tool_contract.json")

UPSTREAM_ROUTE_MODULES = (
    "status", "model_info", "views", "placement", "colors", "code_execution",
    "building", "editing", "structure", "annotation", "analysis",
    "documentation", "rooms", "view_management", "tags", "transforms", "mep",
    "parameters", "interop", "detail", "clash", "document", "documents",
)

#: Routes that must exist because the owner lifted every Revit restriction on
#: 2026-10-18 (D-45): parameter writes, element creation and deletion, colour
#: and graphic overrides, code execution, loading and export.
WRITE_ROUTE_FRAGMENTS = (
    "/execute_code/",
    "/save_document/",
    "/set_parameter/",
    "/delete_elements/",
    "/modify_element/",
    "/place_family/",
    "/color_splash/",
    "/clear_colors/",
    "/transform_elements/",
    "/load_family/",
    "/export_ifc/",
)

DG_TOOLS = {
    "dg_mapping_status",
    "dg_start_mapping",
    "dg_show_elements",
    "dg_clear_mapping_colours",
}


def run(coro):
    return asyncio.run(coro)


# --- pyRevit side: route inventory ---------------------------------------------

def declared_route_modules():
    """(module, register function) of every route module on disk, by AST scan."""
    folder = os.path.join(ROOT, "dg_revit_mcp")
    found = []
    for name in sorted(os.listdir(folder)):
        if not name.endswith(".py") or name == "__init__.py":
            continue
        with open(os.path.join(folder, name), encoding="utf-8") as handle:
            tree = ast.parse(handle.read())
        for node in tree.body:
            if (isinstance(node, ast.FunctionDef)
                    and node.name.startswith("register_")
                    and node.name.endswith("_routes")):
                found.append((name[:-3], node.name))
    return found


class _Recorder(object):
    """Records what one register function declares, without pyRevit."""

    def __init__(self):
        self.routes = []

    def route(self, pattern, methods=("GET",)):
        def decorator(func):
            for method in methods:
                self.routes.append((method, pattern, func))
            return func

        return decorator


def declared_routes(module_name, function_name):
    module = importlib.import_module("dg_revit_mcp." + module_name)
    recorder = _Recorder()
    getattr(module, function_name)(recorder)
    return recorder.routes


def test_startup_uses_the_dg_revit_api_name(monkeypatch):
    install_pyrevit_stubs(monkeypatch)
    importlib.import_module("startup")
    assert sys.modules["pyrevit.routes"].API.names == ["dg_revit"]


def test_startup_registers_every_route_module_on_disk(monkeypatch):
    startup, registry = load_startup(monkeypatch)
    declared_modules = {module for module, _ in declared_route_modules()}
    assert set(UPSTREAM_ROUTE_MODULES) <= declared_modules
    assert {module for module, _ in startup.ROUTE_MODULES} == declared_modules

    declared = set()
    for module_name, function_name in declared_route_modules():
        declared |= {(method, pattern) for method, pattern, _ in
                     declared_routes(module_name, function_name)}
    registered = {(method, pattern) for method, pattern, _ in registry}
    assert registered == declared
    assert len(registry) == len(declared)  # no route registered twice
    assert len(declared) >= 50  # the whole upstream surface, documents included


def test_write_routes_are_registered(monkeypatch):
    """D-45: writes, code execution and export are registered, not dropped."""
    _, registry = load_startup(monkeypatch)
    patterns = [pattern for _, pattern, _ in registry]
    for fragment in WRITE_ROUTE_FRAGMENTS:
        assert any(fragment in pattern for pattern in patterns), fragment
    create_like = [p for p in patterns if p.startswith("/create_")]
    assert len(create_like) >= 14  # create_* route families


def test_documents_read_routes_are_kept(monkeypatch):
    _, registry = load_startup(monkeypatch)
    patterns = {pattern for _, pattern, _ in registry}
    assert {"/list_open_documents/", "/selection_snapshot/"} <= patterns


def test_status_route_declares_api_context(monkeypatch):
    _, registry = load_startup(monkeypatch)
    by_path = {p: f for _, p, f in registry}
    assert set(inspect.signature(by_path["/status/"]).parameters) & {"doc", "uiapp"}


@pytest.mark.parametrize("host", ["0.0.0.0", "192.168.1.10", "::", "example.com", "", None])
def test_startup_registers_nothing_when_host_is_not_loopback(monkeypatch, host):
    startup, registry = load_startup(monkeypatch, routes_host=host)
    assert registry == []
    assert startup.register_routes() == []


@pytest.mark.parametrize("host", ["127.0.0.1", "localhost", "::1", "127.0.0.2", '"127.0.0.1"'])
def test_startup_registers_when_host_is_loopback(monkeypatch, host):
    _, registry = load_startup(monkeypatch, routes_host=host)
    assert len(registry) >= 50


def test_startup_registers_nothing_when_host_cannot_be_read(monkeypatch):
    install = install_pyrevit_stubs(monkeypatch)
    cfg = sys.modules["pyrevit.userconfig"]

    class Broken(object):
        @property
        def routes_host(self):
            raise RuntimeError("config unreadable")

    cfg.user_config = Broken()
    importlib.import_module("startup")
    assert install == []


# --- pyRevit side: IronPython 3.4 syntax ----------------------------------------

# Syntax newer than Python 3.4: pyRevit runs these files on IronPython 3.4,
# which cannot parse them, so the whole extension fails to load (1301 UAT G-9).
_NOT_IRONPYTHON = (ast.AsyncFunctionDef, ast.AsyncFor, ast.AsyncWith, ast.Await,
                   ast.JoinedStr, ast.AnnAssign, ast.NamedExpr)


def _ironpython_modules():
    names = ["startup.py", "dg_transport.py"]
    folder = os.path.join(ROOT, "dg_revit_mcp")
    names += sorted(os.path.join("dg_revit_mcp", name)
                    for name in os.listdir(folder) if name.endswith(".py"))
    return names


@pytest.mark.parametrize("relpath", _ironpython_modules())
def test_pyrevit_side_modules_parse_under_ironpython(relpath):
    with open(os.path.join(ROOT, relpath), encoding="utf-8") as handle:
        tree = ast.parse(handle.read())
    found = []
    for node in ast.walk(tree):
        if isinstance(node, _NOT_IRONPYTHON):
            found.append((type(node).__name__, node.lineno))
        elif isinstance(node, (ast.FunctionDef, ast.Lambda)):
            args = node.args
            annotated = [a for a in args.args + args.kwonlyargs if a.annotation is not None]
            if annotated or getattr(node, "returns", None) is not None:
                found.append(("annotation", node.lineno))
    assert found == []


@pytest.mark.parametrize("relpath", ["startup.py", "dg_transport.py"] + sorted(
    os.path.join("dg_revit_mcp", name)
    for name in os.listdir(os.path.join(ROOT, "dg_revit_mcp")) if name.endswith(".py")))
def test_pyrevit_side_modules_have_no_f_strings(relpath):
    with open(os.path.join(ROOT, relpath), encoding="utf-8") as handle:
        source = handle.read()
    # An f-string is a JoinedStr node, whichever quote/prefix spelling it uses.
    assert not any(isinstance(node, ast.JoinedStr) for node in ast.walk(ast.parse(source)))


_SIBLINGS = {name[:-3] for name in os.listdir(os.path.join(ROOT, "dg_revit_mcp"))
             if name.endswith(".py")}


@pytest.mark.parametrize("name", sorted(_SIBLINGS))
def test_route_modules_import_siblings_relatively(name):
    # ``from utils import`` inside the package is an implicit relative import:
    # IronPython 2.7 resolves it, IronPython 3.4 does not (1301 UAT G-10).
    with open(os.path.join(ROOT, "dg_revit_mcp", name + ".py"), encoding="utf-8") as handle:
        tree = ast.parse(handle.read())
    implicit = [node.lineno for node in ast.walk(tree)
                if isinstance(node, ast.ImportFrom) and node.level == 0
                and (node.module or "").split(".")[0] in _SIBLINGS]
    implicit += [node.lineno for node in ast.walk(tree) if isinstance(node, ast.Import)
                 for alias in node.names if alias.name.split(".")[0] in _SIBLINGS]
    assert implicit == []


# --- tool layer -----------------------------------------------------------------

def registered_tools():
    import main

    return {t.name: t for t in run(main.mcp.list_tools())}


def test_every_upstream_tool_and_the_dg_tools_are_registered():
    tools = registered_tools()
    assert DG_TOOLS <= set(tools)
    assert len(tools) >= 54  # 48 upstream + degram_tools (2) + DG connector (4)
    assert {"get_revit_status", "get_revit_model_info", "get_element_properties",
            "list_levels", "get_current_view_info", "list_category_parameters",
            "list_open_documents", "get_selection_snapshot"} <= set(tools)


@pytest.mark.parametrize("name", [
    "execute_revit_code", "delete_elements", "modify_element", "set_parameter",
    "save_document", "place_family", "load_family", "color_splash", "clear_colors",
    "transform_elements", "create_level", "create_room", "link_file", "export_ifc",
])
def test_write_capable_tools_are_registered(name):
    """D-45: every upstream write tool is exposed; no read-only allowlist remains."""
    assert name in registered_tools()


def test_every_tool_module_on_disk_is_registered():
    """No registry guard: every tools/<name>_tools.py reaches main.mcp."""
    import tools
    from mcp.server.fastmcp import FastMCP

    async def noop(*args, **kwargs):
        return {}

    probe = FastMCP("probe")
    modules = [info.name for info in pkgutil.iter_modules(tools.__path__)
               if info.name.endswith("_tools")]
    assert len(modules) >= 24  # 22 upstream + degram_tools + dg_connector_tools
    for module_name in modules:
        module = importlib.import_module("tools." + module_name)
        for attr in dir(module):
            if not attr.startswith("register_") or not attr.endswith("_tools"):
                continue
            func = getattr(module, attr)
            helpers = [noop] * (len(inspect.signature(func).parameters) - 1)
            func(probe, *helpers)  # no wrapper, upstream behaviour
    assert {t.name for t in run(probe.list_tools())} == set(registered_tools())


def test_tool_contract_pins_the_registered_tools():
    """Drift test: tool_contract.json and the live server agree."""
    contract = json.load(open(CONTRACT, encoding="utf-8"))
    tools = registered_tools()
    assert set(contract) == set(tools)
    for name, tool in tools.items():
        assert contract[name] == tool.inputSchema, name


def test_every_tool_has_a_description():
    for tool in registered_tools().values():
        assert tool.description and len(tool.description.strip()) > 20, tool.name


def test_dg_show_elements_schema_takes_a_list_of_unique_ids():
    schema = registered_tools()["dg_show_elements"].inputSchema
    assert schema["properties"]["unique_ids"]["type"] == "array"
    assert schema["required"] == ["unique_ids"]


# --- transport guard ------------------------------------------------------------

@pytest.mark.parametrize("transport", ["streamable-http", "sse", "combined"])
def test_enforce_transport_refuses_network_transports_in_degram_mode(transport):
    with pytest.raises(dt.DegramModeError) as err:
        dt.enforce_transport(transport, {"DEGRAM_MODE": "1"})
    assert "DEGRAM_TRANSPORT_REFUSED" in str(err.value)


def test_enforce_transport_allows_stdio_and_non_degram_mode():
    assert dt.enforce_transport("stdio", {"DEGRAM_MODE": "1"}) is None
    assert dt.enforce_transport("sse", {}) is None
    assert dt.enforce_transport("sse", {"DEGRAM_MODE": "0"}) is None


@pytest.mark.parametrize("flag", ["--http", "--sse", "--combined"])
def test_degram_mode_process_exits_nonzero_on_network_transport(flag):
    env = dict(os.environ, DEGRAM_MODE="1")
    proc = subprocess.run([sys.executable, os.path.join(ROOT, "main.py"), flag],
                          cwd=ROOT, env=env, capture_output=True, text=True, timeout=60)
    assert proc.returncode != 0
    assert "DEGRAM_TRANSPORT_REFUSED" in proc.stderr


def test_read_only_guard_is_gone():
    """The read-only allowlists and their wrappers no longer exist."""
    assert not os.path.exists(os.path.join(ROOT, "degram_readonly.py"))
    for name in ("ALLOWED_TOOLS", "ALLOWED_ROUTES", "ALLOWED_ROUTE_MODULES",
                 "ReadOnlyApi", "ReadOnlyToolRegistry"):
        assert not hasattr(dt, name), name


# --- transport helpers ----------------------------------------------------------

@pytest.mark.parametrize("host", ["127.0.0.1", "localhost", "::1", "127.0.0.2", '"127.0.0.1"'])
def test_is_loopback_host_accepts_loopback(host):
    assert dt.is_loopback_host(host) is True


@pytest.mark.parametrize("host", ["0.0.0.0", "10.0.0.9", "::", "", None, "example.com", "127.0.0.256"])
def test_is_loopback_host_rejects_everything_else(host):
    assert dt.is_loopback_host(host) is False


def test_error_outcome_shape_and_is_outcome():
    outcome = dt.error_outcome("BAD_REQUEST", "nope", field="x")
    assert outcome == {"status": "error", "code": "BAD_REQUEST", "error": "nope", "field": "x"}
    assert dt.is_outcome(outcome) is True
    assert dt.is_outcome({"status": "ok", "code": "BAD_REQUEST"}) is False
    assert dt.is_outcome("Error: boom") is False
    assert "BAD_REQUEST" in dt.ERROR_CODES
