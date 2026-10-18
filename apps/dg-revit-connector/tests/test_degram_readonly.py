# -*- coding: utf-8 -*-
"""Read-only guarantees of the DeGram fork, proven offline (no Revit, no pyRevit).

Both layers are covered:

* the pyRevit extension (``startup.py``) registers exactly the allowlisted
  routes, and registers nothing at all unless the Routes host is loopback;
* the MCP server (``main.mcp``) exposes exactly the allowlisted tools and
  refuses non-stdio transports when launched for DeGram.

``install_pyrevit_stubs`` is reused by ``test_degram_documents.py``.
"""

import ast
import asyncio
import importlib
import inspect
import json
import os
import pkgutil
import re
import subprocess
import sys
import types
import urllib
from types import SimpleNamespace

import pytest

import degram_readonly as dro

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CONTRACT = os.path.join(ROOT, "tests", "tool_contract.json")

EXPECTED_TOOLS = {
    "get_revit_status",
    "get_revit_model_info",
    "list_open_documents",
    "get_selection_snapshot",
    "get_element_properties",
    "list_levels",
    "get_current_view_info",
    "list_category_parameters",
}

EXPECTED_ROUTES = {
    ("GET", "/status/"),
    ("GET", "/model_info/"),
    ("GET", "/list_open_documents/"),
    ("POST", "/selection_snapshot/"),
    ("GET", "/element_properties/<element_id>"),
    ("GET", "/list_levels/"),
    ("GET", "/current_view_info/"),
    ("POST", "/list_category_parameters/"),
}


def run(coro):
    return asyncio.run(coro)


# --- pyRevit stubs ------------------------------------------------------------

class _AnyMeta(type):
    """Metaclass so ``DB.Anything.Whatever`` resolves to another dummy class."""

    def __getattr__(cls, name):
        if name.startswith("__"):
            raise AttributeError(name)
        return _any_class(name)


def _any_class(name):
    return _AnyMeta(str(name), (), {})


class _AnyModule(types.ModuleType):
    def __getattr__(self, name):
        if name.startswith("__"):
            raise AttributeError(name)
        return _any_class(name)


class _FakeAPI(object):
    """Stand-in for ``pyrevit.routes.API`` that records what gets registered."""

    registry = None  # set per install

    def __init__(self, name):
        self.name = name

    def route(self, pattern, methods=("GET",)):
        def decorator(func):
            for method in methods:
                type(self).registry.append((method, pattern, func))
            return func

        return decorator


def install_pyrevit_stubs(monkeypatch, routes_host="127.0.0.1"):
    """Install fake ``pyrevit``/``System``/``utils`` modules; return the route registry."""
    registry = []
    fake_api = type("FakeAPI", (_FakeAPI,), {"registry": registry})

    def make_response(data=None, status=200, headers=None):
        return SimpleNamespace(data=data, status=status)

    routes = types.ModuleType("pyrevit.routes")
    routes.API = fake_api
    routes.make_response = make_response

    db = _AnyModule("pyrevit.DB")
    revit = types.ModuleType("pyrevit.revit")
    revit.doc = None
    revit.db = types.ModuleType("pyrevit.revit.db")
    revit.db.ProjectInfo = _any_class("ProjectInfo")
    revit.db.query = _AnyModule("pyrevit.revit.db.query")

    userconfig = types.ModuleType("pyrevit.userconfig")
    userconfig.user_config = SimpleNamespace(routes_host=routes_host)

    pyrevit = types.ModuleType("pyrevit")
    pyrevit.routes = routes
    pyrevit.DB = db
    pyrevit.revit = revit

    system = _AnyModule("System")
    system.Collections = _AnyModule("System.Collections")
    system.Collections.Generic = _AnyModule("System.Collections.Generic")

    stubs = {
        "pyrevit": pyrevit,
        "pyrevit.routes": routes,
        "pyrevit.DB": db,
        "pyrevit.revit": revit,
        "pyrevit.revit.db": revit.db,
        "pyrevit.revit.db.query": revit.db.query,
        "pyrevit.userconfig": userconfig,
        "System": system,
        "System.Collections": system.Collections,
        "System.Collections.Generic": system.Collections.Generic,
    }
    for name, module in stubs.items():
        monkeypatch.setitem(sys.modules, name, module)
    # route modules do ``from utils import ...`` (extension lib path) and a py2
    # ``from urllib import unquote``
    monkeypatch.syspath_prepend(os.path.join(ROOT, "revit_mcp"))
    monkeypatch.setattr(urllib, "unquote", lambda s: s, raising=False)
    # force a fresh import of everything that bound the previous stubs
    for name in list(sys.modules):
        if name == "startup" or name == "utils" or name.startswith("revit_mcp"):
            monkeypatch.delitem(sys.modules, name, raising=False)
    return registry


def load_startup(monkeypatch, routes_host="127.0.0.1"):
    registry = install_pyrevit_stubs(monkeypatch, routes_host)
    startup = importlib.import_module("startup")
    return startup, registry


# --- constants ------------------------------------------------------------------

def test_allowlists_are_exactly_the_expected_sets():
    assert set(dro.ALLOWED_TOOLS) == EXPECTED_TOOLS
    assert set(dro.ALLOWED_ROUTES) == EXPECTED_ROUTES
    assert len(dro.ALLOWED_TOOLS) == 8


def test_every_allowed_tool_is_a_read_verb():
    assert all(re.match(r"^(get|list)_", name) for name in dro.ALLOWED_TOOLS)


# Syntax newer than Python 3.4: pyRevit runs startup.py on IronPython 3.4, which
# cannot parse it, so the whole extension fails to load (1301 UAT G-9).
_NOT_IRONPYTHON = (ast.AsyncFunctionDef, ast.AsyncFor, ast.AsyncWith, ast.Await,
                   ast.JoinedStr, ast.AnnAssign, ast.NamedExpr)


@pytest.mark.parametrize("relpath", ["startup.py", "degram_readonly.py"] + sorted(
    os.path.join("revit_mcp", name)
    for name in os.listdir(os.path.join(ROOT, "revit_mcp")) if name.endswith(".py")))
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


_SIBLINGS = {name[:-3] for name in os.listdir(os.path.join(ROOT, "revit_mcp")) if name.endswith(".py")}


@pytest.mark.parametrize("name", sorted(_SIBLINGS))
def test_route_modules_import_siblings_explicitly(name):
    # ``from utils import`` inside the package is an implicit relative import:
    # IronPython 2.7 resolves it, IronPython 3.4 does not (1301 UAT G-10).
    with open(os.path.join(ROOT, "revit_mcp", name + ".py"), encoding="utf-8") as handle:
        tree = ast.parse(handle.read())
    implicit = [node.lineno for node in ast.walk(tree)
                if isinstance(node, ast.ImportFrom) and node.level == 0
                and (node.module or "").split(".")[0] in _SIBLINGS]
    implicit += [node.lineno for node in ast.walk(tree) if isinstance(node, ast.Import)
                 for alias in node.names if alias.name.split(".")[0] in _SIBLINGS]
    assert implicit == []


# --- route layer ----------------------------------------------------------------

def test_startup_registers_exactly_the_allowlisted_routes(monkeypatch):
    _, registry = load_startup(monkeypatch)
    assert {(m, p) for m, p, _ in registry} == EXPECTED_ROUTES
    assert len(registry) == len(EXPECTED_ROUTES)  # no duplicates


@pytest.mark.parametrize("forbidden", [
    "/execute_code/", "/save_document/", "/set_parameter/", "/color_splash/",
    "/clear_colors/", "/place_family/", "/create_wall/", "/delete_element/",
])
def test_mutating_routes_are_unreachable(monkeypatch, forbidden):
    _, registry = load_startup(monkeypatch)
    assert forbidden not in {p for _, p, _ in registry}


def test_no_registered_route_uses_a_mutating_method(monkeypatch):
    _, registry = load_startup(monkeypatch)
    assert {m for m, _, _ in registry} <= {"GET", "POST"}
    posts = {p for m, p, _ in registry if m == "POST"}
    # POST is only used to carry a body for two read routes
    assert posts == {"/selection_snapshot/", "/list_category_parameters/"}


def test_every_registered_handler_runs_in_api_context(monkeypatch):
    """Handlers must declare doc/uidoc/uiapp so pyRevit runs them via ExternalEvent."""
    _, registry = load_startup(monkeypatch)
    for method, pattern, func in registry:
        params = set(inspect.signature(func).parameters)
        assert params & {"doc", "uidoc", "uiapp"}, (method, pattern)


def test_status_and_model_info_declare_api_context(monkeypatch):
    _, registry = load_startup(monkeypatch)
    by_path = {p: f for _, p, f in registry}
    for path in ("/status/", "/model_info/"):
        assert set(inspect.signature(by_path[path]).parameters) & {"doc", "uiapp"}, path


@pytest.mark.parametrize("host", ["0.0.0.0", "192.168.1.10", "::", "example.com", "", None])
def test_startup_registers_nothing_when_host_is_not_loopback(monkeypatch, host):
    _, registry = load_startup(monkeypatch, routes_host=host)
    assert registry == []


@pytest.mark.parametrize("host", ["127.0.0.1", "localhost", "::1", "127.0.0.2", '"127.0.0.1"'])
def test_startup_registers_when_host_is_loopback(monkeypatch, host):
    _, registry = load_startup(monkeypatch, routes_host=host)
    assert len(registry) == len(EXPECTED_ROUTES)


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


def test_read_only_api_drops_unlisted_routes_and_methods():
    seen = []

    class Api(object):
        def route(self, pattern, methods=("GET",)):
            def deco(f):
                seen.extend((m, pattern) for m in methods)
                return f
            return deco

    guard = dro.ReadOnlyApi(Api())

    @guard.route("/status/", methods=["GET", "POST", "DELETE"])
    def a(doc):
        return 1

    @guard.route("/execute_code/", methods=["POST"])
    def b(doc):
        return 2

    @guard.route("/list_levels/")  # default method is GET
    def c(doc):
        return 3

    assert seen == [("GET", "/status/"), ("GET", "/list_levels/")]
    assert a(None) == 1 and b(None) == 2  # decorated functions stay callable
    assert ("POST", "/execute_code/") in guard.dropped
    assert ("POST", "/status/") in guard.dropped


def test_read_only_api_exposes_nothing_but_route():
    guard = dro.ReadOnlyApi(SimpleNamespace(route=lambda *a, **k: None, add_route=print))
    with pytest.raises(AttributeError):
        guard.add_route


# --- tool layer -----------------------------------------------------------------

def registered_tools():
    import main

    return {t.name: t for t in run(main.mcp.list_tools())}


def test_registered_mcp_tools_equal_the_allowlist():
    assert set(registered_tools()) == EXPECTED_TOOLS


def test_tool_contract_pins_exactly_the_allowlist():
    """Drift test: tool_contract.json, the allowlist and the live server agree."""
    contract = json.load(open(CONTRACT, encoding="utf-8"))
    assert set(contract) == EXPECTED_TOOLS == set(registered_tools())
    for name, tool in registered_tools().items():
        assert contract[name] == tool.inputSchema, name


def test_no_registered_tool_has_a_mutating_name():
    mutating = re.compile(
        r"(create|place|modify|move|delete|remove|set_|execute|save|export|load|"
        r"transform|tag|color|link|rotate|copy|mirror|write|run_|batch|apply)")
    for name in registered_tools():
        assert not mutating.search(name), name


def test_every_tool_module_goes_through_the_wrapper():
    """Registering *every* tools module still yields only allowlisted names."""
    import tools
    from mcp.server.fastmcp import FastMCP

    async def noop(*a, **k):
        return {}

    unwrapped_names = set()
    guarded = FastMCP("probe")
    wrapped = dro.ReadOnlyToolRegistry(guarded)
    for info in pkgutil.iter_modules(tools.__path__):
        if not info.name.endswith("_tools"):
            continue
        module = importlib.import_module("tools." + info.name)
        for attr in dir(module):
            if not attr.startswith("register_") or not attr.endswith("_tools"):
                continue
            func = getattr(module, attr)
            n_helpers = len(inspect.signature(func).parameters) - 1
            helpers = [noop] * n_helpers
            func(wrapped, *helpers)  # through the wrapper
            raw = FastMCP("raw")
            func(raw, *helpers)  # upstream behaviour, for contrast
            unwrapped_names |= {t.name for t in run(raw.list_tools())}
    assert {t.name for t in run(guarded.list_tools())} <= EXPECTED_TOOLS
    # the contrast set proves the upstream mutating tools exist and were dropped
    assert {"execute_revit_code", "save_document", "set_parameter"} <= unwrapped_names


def test_tool_wrapper_drops_names_not_allowlisted():
    from mcp.server.fastmcp import FastMCP

    mcp = FastMCP("t")
    wrapped = dro.ReadOnlyToolRegistry(mcp, allowed=frozenset({"keep_me"}))

    @wrapped.tool()
    async def keep_me() -> str:
        """Keep this tool, it is allowlisted for the test."""
        return "k"

    @wrapped.tool()
    async def drop_me() -> str:
        """Drop this tool, it is not allowlisted for the test."""
        return "d"

    @wrapped.tool(name="renamed_drop")
    async def other() -> str:
        """Dropped through the explicit name."""
        return "o"

    assert {t.name for t in run(mcp.list_tools())} == {"keep_me"}
    assert run(drop_me()) == "d"  # the function itself is untouched


# --- transport guard ------------------------------------------------------------

@pytest.mark.parametrize("transport", ["streamable-http", "sse", "combined"])
def test_enforce_transport_refuses_network_transports_in_degram_mode(transport):
    with pytest.raises(dro.DegramModeError) as err:
        dro.enforce_transport(transport, {"DEGRAM_MODE": "1"})
    assert "DEGRAM_TRANSPORT_REFUSED" in str(err.value)


def test_enforce_transport_allows_stdio_and_non_degram_mode():
    dro.enforce_transport("stdio", {"DEGRAM_MODE": "1"})
    dro.enforce_transport("sse", {})
    dro.enforce_transport("sse", {"DEGRAM_MODE": "0"})


@pytest.mark.parametrize("flag", ["--http", "--sse", "--combined"])
def test_degram_mode_process_exits_nonzero_on_network_transport(flag):
    env = dict(os.environ, DEGRAM_MODE="1")
    proc = subprocess.run([sys.executable, os.path.join(ROOT, "main.py"), flag],
                          cwd=ROOT, env=env, capture_output=True, text=True, timeout=60)
    assert proc.returncode != 0
    assert "DEGRAM_TRANSPORT_REFUSED" in proc.stderr
