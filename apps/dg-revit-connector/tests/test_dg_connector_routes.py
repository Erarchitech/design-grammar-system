# -*- coding: utf-8 -*-
"""The four DG connector Routes of the pyRevit API ``dg_revit``.

Offline only: the pyRevit/Revit runtime is the stub of ``pyrevit_stubs``, and
the connector runner is monkeypatched, so a route test never runs a job, never
touches Revit and never opens a socket.

What is pinned here:

* ``startup.py`` registers the four DG routes beside every upstream Revit route
  when the Routes host is loopback, and registers nothing off loopback;
* ``POST /show_elements/`` validates its body (1..5000 non-empty strings) and
  answers 400 BAD_REQUEST *before* the runner or Revit is involved;
* the status, start and clear handlers delegate to the runner;
* an unexpected failure becomes a 500 ROUTE_ERROR envelope, never free text;
* no answer ever carries the connector token.
"""

import importlib
import json
import os
import sys
from types import SimpleNamespace

import pytest

HERE = os.path.dirname(os.path.abspath(__file__))
APP_ROOT = os.path.dirname(HERE)
LIB_DIR = os.path.join(APP_ROOT, "lib")

if LIB_DIR not in sys.path:
    sys.path.insert(0, LIB_DIR)

from pyrevit_stubs import install_pyrevit_stubs, load_startup  # noqa: E402

DG_ROUTES = {
    ("GET", "/mapping_status/"),
    ("POST", "/start_mapping/"),
    ("POST", "/show_elements/"),
    ("POST", "/clear_colours/"),
}

MAX_IDS = 5000


@pytest.fixture(autouse=True)
def clean_connector_state():
    """One shared memory state per test (the AppDomain store outside Revit)."""
    from dg_connector import state as connector_state
    connector_state.ConnectorState().clear()
    yield connector_state.ConnectorState()
    connector_state.ConnectorState().clear()


@pytest.fixture()
def store(clean_connector_state):
    """The shared connector state of this test (already cleared)."""
    from dg_connector import state as connector_state
    return connector_state.ConnectorState()


@pytest.fixture()
def registration(monkeypatch):
    """Register every route against the stubs -> (startup, registry)."""
    return load_startup(monkeypatch)


@pytest.fixture()
def handlers(registration):
    """The four DG route handlers, looked up by path."""
    _, registry = registration
    found = {}
    for method, pattern, func in registry:
        if (method, pattern) in DG_ROUTES:
            found[pattern] = func
    assert set(found) == {pattern for _method, pattern in DG_ROUTES}
    return found


@pytest.fixture()
def runner(monkeypatch):
    """The connector runner module, with its module state reset."""
    from dg_connector import runner as module
    monkeypatch.setattr(module, "_JOBS", [])
    monkeypatch.setattr(module, "_DONE_SESSIONS", set())
    monkeypatch.setattr(module, "_REJECTED_TOKENS", set())
    monkeypatch.setattr(module, "_EXTENSION_DIR", [])
    monkeypatch.setattr(module, "_CLIENT", [])
    monkeypatch.setattr(module, "_EXTERNAL_EVENT", [])
    monkeypatch.setattr(module, "_HANDLER", [])
    monkeypatch.setattr(module, "_THREAD", [])
    monkeypatch.setattr(module, "_OWNER", [])
    monkeypatch.setattr(module, "_LOCAL_SLOTS", {})
    return module


def test_a_success_envelope_never_carries_a_token(handlers, runner, monkeypatch):
    """Even if a runner result ever held a token, the route drops it."""
    monkeypatch.setattr(runner, "mapping_status",
                        lambda uiapp: {"signedIn": True, "token": "dgk_leak"})
    response = handlers["/mapping_status/"](fake_uiapp())
    assert "token" not in response.data
    assert "dgk_leak" not in json.dumps(response.data)


def body(payload):
    """A pyRevit request stand-in whose ``data`` is the raw (text/plain) body."""
    if isinstance(payload, (dict, list)):
        payload = json.dumps(payload)
    return SimpleNamespace(data=payload)


def fake_uiapp(document=None, uidoc=None):
    return SimpleNamespace(
        Application=SimpleNamespace(Documents=[document] if document else []),
        ActiveUIDocument=uidoc)


# --- registration ---------------------------------------------------------------

def test_startup_registers_the_four_dg_routes_on_loopback(registration):
    _, registry = registration
    registered = {(method, pattern) for method, pattern, _func in registry}
    assert DG_ROUTES <= registered
    assert len(registry) >= 50  # the upstream Revit surface is still there


def test_route_module_declares_exactly_the_four_routes(monkeypatch):
    install_pyrevit_stubs(monkeypatch)
    module = importlib.import_module("dg_revit_mcp.dg_connector_routes")

    class Recorder(object):
        def __init__(self):
            self.routes = []

        def route(self, pattern, methods=("GET",)):
            def decorator(func):
                for method in methods:
                    self.routes.append((method, pattern))
                return func

            return decorator

    recorder = Recorder()
    module.register_dg_connector_routes(recorder)
    assert set(recorder.routes) == DG_ROUTES
    assert len(recorder.routes) == 4


def test_nothing_is_registered_off_loopback(monkeypatch):
    _, registry = load_startup(monkeypatch, routes_host="0.0.0.0")
    assert registry == []


def test_handlers_declare_the_objects_they_need(handlers):
    import inspect

    status = inspect.signature(handlers["/mapping_status/"]).parameters
    start = inspect.signature(handlers["/start_mapping/"]).parameters
    show = inspect.signature(handlers["/show_elements/"]).parameters
    clear = inspect.signature(handlers["/clear_colours/"]).parameters
    assert "uiapp" in status
    assert "uiapp" in start
    assert {"uiapp", "uidoc", "doc", "request"} <= set(show)
    assert "uiapp" in clear


# --- show_elements: body validation --------------------------------------------

INVALID_BODIES = [
    None,
    {},
    {"uniqueIds": None},
    {"uniqueIds": "uid-a"},
    {"uniqueIds": [1]},
    {"uniqueIds": ["uid-a", 2]},
    {"uniqueIds": []},
    {"uniqueIds": ["", "   "]},
    {"uniqueIds": ["uid-{}".format(i) for i in range(MAX_IDS + 1)]},
]


@pytest.mark.parametrize("payload", INVALID_BODIES)
def test_show_elements_refuses_a_bad_body_without_touching_the_runner(
        handlers, runner, monkeypatch, payload):
    calls = []
    monkeypatch.setattr(runner, "show", lambda *args, **kwargs: calls.append(args) or {})
    response = handlers["/show_elements/"](fake_uiapp(), None, None, body(payload))
    assert response.status == 400
    assert response.data["status"] == "error"
    assert response.data["code"] == "BAD_REQUEST"
    assert response.data["error"]
    assert calls == []  # the runner (and with it Revit) was never reached


def test_show_elements_refuses_a_body_that_is_not_json(handlers, runner, monkeypatch):
    monkeypatch.setattr(runner, "show", lambda *a, **k: pytest.fail("runner called"))
    response = handlers["/show_elements/"](fake_uiapp(), None, None,
                                           SimpleNamespace(data=b"{not json"))
    assert response.status == 400 and response.data["code"] == "BAD_REQUEST"


def test_show_elements_accepts_the_cap_and_delegates(handlers, runner, monkeypatch):
    seen = {}
    ids = ["uid-{}".format(i) for i in range(MAX_IDS)]

    def fake_show(uidoc, doc, unique_ids):
        seen["ids"] = unique_ids
        seen["uidoc"] = uidoc
        seen["doc"] = doc
        return {"found": 2, "shown": 2, "missing": []}

    monkeypatch.setattr(runner, "show", fake_show)
    response = handlers["/show_elements/"](fake_uiapp(), "UIDOC", "DOC",
                                           body({"uniqueIds": ids}))
    assert response.status == 200
    assert response.data["status"] == "ok"
    assert response.data["found"] == 2 and response.data["shown"] == 2
    assert seen["ids"] == ids
    assert seen["uidoc"] == "UIDOC" and seen["doc"] == "DOC"


def test_show_elements_trims_the_ids(handlers, runner, monkeypatch):
    seen = {}
    monkeypatch.setattr(runner, "show",
                        lambda uidoc, doc, ids: seen.setdefault("ids", ids) or {})
    handlers["/show_elements/"](fake_uiapp(), None, None,
                                body({"uniqueIds": [" uid-a ", "uid-b"]}))
    assert seen["ids"] == ["uid-a", "uid-b"]


def test_show_elements_accepts_a_json_text_body(handlers, runner, monkeypatch):
    monkeypatch.setattr(runner, "show", lambda uidoc, doc, ids: {"found": 1, "shown": 1,
                                                                "missing": ["gone"]})
    response = handlers["/show_elements/"](fake_uiapp(), None, None,
                                           SimpleNamespace(data='{"uniqueIds": ["uid-a"]}'))
    assert response.status == 200
    assert response.data["missing"] == ["gone"]


def test_show_elements_accepts_unicode_unique_ids_from_decoded_json(handlers, runner, monkeypatch):
    seen = {}
    monkeypatch.setattr(runner, "show", lambda uidoc, doc, ids: seen.setdefault("ids", ids) or {})
    response = handlers["/show_elements/"](fake_uiapp(), None, None,
                                           SimpleNamespace(data='{"uniqueIds": ["фасад-элемент"]}'.encode("utf-8")))
    assert response.status == 200
    assert seen["ids"] == ["фасад-элемент"]


# --- the other three routes delegate -------------------------------------------

def test_mapping_status_delegates_to_the_runner(handlers, runner, monkeypatch):
    monkeypatch.setattr(runner, "mapping_status",
                        lambda uiapp: {"signedIn": True, "project": "p1",
                                       "document": "tower", "sessionId": "ms-1"})
    response = handlers["/mapping_status/"](fake_uiapp())
    assert response.status == 200
    assert response.data["status"] == "ok"
    assert response.data["signedIn"] is True
    assert response.data["document"] == "tower"


def test_start_mapping_delegates_to_the_runner(handlers, runner, monkeypatch):
    monkeypatch.setattr(runner, "start_mapping",
                        lambda uiapp: {"started": True, "sessionId": "ms-1",
                                       "message": "started"})
    response = handlers["/start_mapping/"](fake_uiapp())
    assert response.status == 200
    assert response.data["started"] is True
    assert response.data["sessionId"] == "ms-1"
    assert response.data["message"] == "started"


def test_clear_colours_delegates_to_the_runner(handlers, runner, monkeypatch):
    monkeypatch.setattr(runner, "clear",
                        lambda uiapp: {"cleared": 7, "message": "cleared"})
    response = handlers["/clear_colours/"](fake_uiapp())
    assert response.status == 200
    assert response.data["cleared"] == 7


# --- failures and secrets --------------------------------------------------------

@pytest.mark.parametrize("path", sorted({pattern for _m, pattern in DG_ROUTES}))
def test_a_runner_failure_becomes_a_route_error(handlers, runner, monkeypatch, path):
    def boom(*args, **kwargs):
        raise RuntimeError("route exploded")

    for name in ("mapping_status", "start_mapping", "show", "clear"):
        monkeypatch.setattr(runner, name, boom)
    arguments = [fake_uiapp()]
    if path == "/show_elements/":
        arguments = [fake_uiapp(), None, None, body({"uniqueIds": ["uid-a"]})]
    response = handlers[path](*arguments)
    assert response.status == 500
    assert response.data["status"] == "error"
    assert response.data["code"] == "ROUTE_ERROR"
    assert "route exploded" in response.data["error"]
    assert not response.data["error"].startswith("Error:")


def test_status_never_answers_with_the_token(handlers, store):
    store.set("url", "http://localhost:8000")
    store.set("token", "dgk_do-not-leak-me")
    store.set("project", "v12-hexagonal-facade-01")
    store.set("sessionId", "ms-0123456789ab")
    store.set("message", "ready")

    # The real runner call: only its Revit part is absent (no active document).
    response = handlers["/mapping_status/"](fake_uiapp())
    assert response.status == 200
    serialized = json.dumps(response.data)
    assert "dgk_do-not-leak-me" not in serialized
    assert "token" not in response.data
    assert response.data["signedIn"] is True
    assert response.data["sessionId"] == "ms-0123456789ab"
    assert response.data["connectorMessage"] == "ready"


def test_start_mapping_refusal_carries_no_token(handlers, store):
    # Not signed in: the real runner refuses before any network call.
    response = handlers["/start_mapping/"](fake_uiapp())
    assert response.status == 200
    assert response.data["started"] is False
    assert "Sign in to DG first" in response.data["message"]
    assert "dgk_" not in json.dumps(response.data)


def test_clear_colours_without_a_session_is_honest(handlers, store):
    response = handlers["/clear_colours/"](fake_uiapp())
    assert response.status == 200
    assert response.data["cleared"] == 0
    assert "No DG mapping session" in response.data["message"]
