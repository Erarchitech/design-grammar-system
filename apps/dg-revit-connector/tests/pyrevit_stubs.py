# -*- coding: utf-8 -*-
"""Fake pyRevit / Revit runtime for the offline tests of the extension half.

The route modules import ``pyrevit``, ``System`` and (interop) ``clr`` at import
time, so a test that imports ``startup`` or any ``dg_revit_mcp.<module>`` needs
those names in ``sys.modules`` first. :func:`install_pyrevit_stubs` installs
them and returns the list that records every registered route.

Shared by ``test_dg_transport.py`` and ``test_degram_documents.py``.
"""

import importlib
import os
import sys
import types
from types import SimpleNamespace

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


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
    names = None  # API names the extension asked for, per install

    def __init__(self, name):
        self.name = name
        type(self).names.append(name)

    def route(self, pattern, methods=("GET",)):
        def decorator(func):
            for method in methods:
                type(self).registry.append((method, pattern, func))
            return func

        return decorator


def install_pyrevit_stubs(monkeypatch, routes_host="127.0.0.1"):
    """Install fake ``pyrevit``/``System``/``clr`` modules; return the route registry."""
    registry = []
    names = []
    fake_api = type("FakeAPI", (_FakeAPI,), {"registry": registry, "names": names})

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

    clr = _AnyModule("clr")  # .NET interop module of IronPython

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
        "clr": clr,
    }
    for name, module in stubs.items():
        monkeypatch.setitem(sys.modules, name, module)
    # force a fresh import of everything that bound the previous stubs
    for name in list(sys.modules):
        if name == "startup" or name == "dg_revit_mcp" or name.startswith("dg_revit_mcp."):
            monkeypatch.delitem(sys.modules, name, raising=False)
    return registry


def load_startup(monkeypatch, routes_host="127.0.0.1"):
    """Import ``startup`` against fresh stubs; return (module, route registry)."""
    registry = install_pyrevit_stubs(monkeypatch, routes_host)
    startup = importlib.import_module("startup")
    return startup, registry
