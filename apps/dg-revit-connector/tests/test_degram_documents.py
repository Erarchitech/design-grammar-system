# -*- coding: utf-8 -*-
"""Document enumeration, identity-pinned selection snapshot and fail-closed client.

Offline only: fake Revit objects stand in for the Revit API, a mocked httpx
transport stands in for pyRevit Routes, and the probe's ``_connect`` seam is
monkeypatched for the loopback probe (asyncio itself needs real sockets).
"""

import asyncio
import importlib
import json
import socket
import sys
from types import SimpleNamespace

import httpx
import pytest

import degram_readonly as dro
from test_degram_readonly import install_pyrevit_stubs, load_startup


def run(coro):
    return asyncio.run(coro)


# --- fake Revit ---------------------------------------------------------------

class FakeId(object):
    def __init__(self, value):
        self.Value = value


class FakeParam(object):
    def __init__(self, name, storage, value=None, display=None, unit=None, has_value=True):
        self.Definition = SimpleNamespace(Name=name)
        self.StorageType = storage
        self._value = value
        self._display = display
        self._unit = unit
        self.HasValue = has_value

    def AsString(self):
        return self._value

    def AsInteger(self):
        return self._value

    def AsDouble(self):
        return self._value

    def AsElementId(self):
        return FakeId(self._value)

    def AsValueString(self):
        return self._display

    def GetUnitTypeId(self):
        return self._unit


class FakeElement(object):
    def __init__(self, eid, unique_id, category, type_name, params):
        self.Id = FakeId(eid)
        self.UniqueId = unique_id
        self.Category = SimpleNamespace(Name=category) if category else None
        self._type_name = type_name
        self._params = params

    def GetTypeId(self):
        return "type:" + self._type_name if self._type_name else None

    def GetOrderedParameters(self):
        return list(self._params)


class FakeDoc(object):
    def __init__(self, title, path, guid, modified=False, linked=False, family=False, elements=()):
        self.Title = title
        self.PathName = path
        self.CreationGUID = guid
        self.IsModified = modified
        self.IsLinked = linked
        self.IsFamilyDocument = family
        self._elements = {e.Id.Value: e for e in elements}
        self._type_names = {}
        for e in elements:
            if e._type_name:
                self._type_names["type:" + e._type_name] = SimpleNamespace(Name=e._type_name)

    def GetElement(self, eid):
        if isinstance(eid, str):
            return self._type_names.get(eid)
        return self._elements.get(eid.Value)


def make_uiapp(docs, active_index=0, selected=()):
    active = docs[active_index] if docs else None
    uidoc = None
    if active is not None:
        uidoc = SimpleNamespace(
            Document=active,
            Selection=SimpleNamespace(GetElementIds=lambda: [FakeId(i) for i in selected]))
    app = SimpleNamespace(Application=SimpleNamespace(Documents=list(docs)), ActiveUIDocument=uidoc)
    return app, uidoc


@pytest.fixture
def documents(monkeypatch):
    registry = install_pyrevit_stubs(monkeypatch)
    module = importlib.import_module("revit_mcp.documents")
    monkeypatch.setattr(module, "_unit_label", lambda param: "mm" if param._unit else "")
    handlers = {}
    api = sys.modules["pyrevit.routes"].API("revit_mcp")
    module.register_document_read_routes(api)
    for method, pattern, func in registry:
        handlers[pattern] = func
    return SimpleNamespace(module=module, list=handlers["/list_open_documents/"],
                           snapshot=handlers["/selection_snapshot/"])


WALL = FakeElement(101, "uid-101", "Walls", "Generic - 200mm", [
    FakeParam("Mark", "String", "W-1", "W-1"),
    FakeParam("Width", "Double", 0.65617, "200 mm", unit="mm-id"),
    FakeParam("Room Bounding", "Integer", 1, "Yes"),
    FakeParam("Base Constraint", "ElementId", 311, "Level 1"),
    FakeParam("Comments", "String", None, None, has_value=False),
])
DOOR = FakeElement(102, "uid-102", "Doors", "M_Single-Flush 0915", [
    FakeParam("Mark", "String", "D-1", "D-1"),
    FakeParam("Fire Rating", "String", "EI30", "EI30"),
])


def two_docs():
    a = FakeDoc("Tower", "C:\\p\\tower.rvt", "aaaa-1111", modified=True, elements=[WALL, DOOR])
    b = FakeDoc("Podium", "", "bbbb-2222")
    return a, b


def body(identity, **extra):
    return SimpleNamespace(data=dict({"identity": identity}, **extra))


def tower_identity():
    return {"creationGuid": "aaaa-1111", "pathName": "C:\\p\\tower.rvt"}


# --- list_open_documents --------------------------------------------------------

def test_list_open_documents_skips_linked_and_family_documents(documents):
    a, b = two_docs()
    linked = FakeDoc("Link", "C:\\p\\link.rvt", "cccc-3333", linked=True)
    family = FakeDoc("Fam", "C:\\p\\f.rfa", "dddd-4444", family=True)
    app, _ = make_uiapp([a, linked, family, b], active_index=0)
    result = documents.list(app)
    assert result.status == 200
    rows = result.data["documents"]
    assert [r["title"] for r in rows] == ["Tower", "Podium"]
    assert rows[0] == {"title": "Tower", "pathName": "C:\\p\\tower.rvt", "creationGuid": "aaaa-1111",
                       "isActive": True, "isModified": True}
    assert rows[1]["pathName"] == "" and rows[1]["isActive"] is False


def test_list_open_documents_with_nothing_open(documents):
    app, _ = make_uiapp([])
    result = documents.list(app)
    assert result.status == 200 and result.data["documents"] == []


# --- get_selection_snapshot ------------------------------------------------------

def test_snapshot_returns_elements_with_typed_parameters(documents):
    a, b = two_docs()
    app, uidoc = make_uiapp([a, b], 0, selected=[101, 102])
    result = documents.snapshot(app, uidoc, body(tower_identity()))
    assert result.status == 200
    data = result.data
    assert data["status"] == "ok" and data["emptySelection"] is False
    assert data["identity"] == tower_identity()
    wall = data["elements"][0]
    assert (wall["uniqueId"], wall["elementId"], wall["category"], wall["typeName"]) == \
        ("uid-101", 101, "Walls", "Generic - 200mm")
    params = {p["name"]: p for p in wall["parameters"]}
    assert params["Width"] == {"name": "Width", "storageType": "Double", "unit": "mm",
                               "displayValue": "200 mm", "value": 0.65617}
    assert params["Mark"]["value"] == "W-1" and params["Mark"]["unit"] == ""
    assert params["Room Bounding"]["value"] == 1
    assert params["Base Constraint"]["value"] == 311 and params["Base Constraint"]["displayValue"] == "Level 1"
    assert params["Comments"]["value"] is None and params["Comments"]["displayValue"] == ""
    assert data["truncation"] == {"elementsTotal": 2, "elementsKept": 2, "parametersTruncated": 0,
                                  "maxElements": 200, "maxParameters": 50}


def test_snapshot_truncation_is_disclosed(documents):
    a, b = two_docs()
    app, uidoc = make_uiapp([a, b], 0, selected=[101, 102])
    result = documents.snapshot(app, uidoc, body(tower_identity(), max_elements=1, max_parameters=2))
    data = result.data
    assert len(data["elements"]) == 1
    assert len(data["elements"][0]["parameters"]) == 2
    assert data["elements"][0]["parametersTotal"] == 5
    assert data["truncation"]["elementsTotal"] == 2
    assert data["truncation"]["elementsKept"] == 1
    assert data["truncation"]["parametersTruncated"] == 3
    assert data["truncation"]["maxElements"] == 1 and data["truncation"]["maxParameters"] == 2


def test_snapshot_limits_are_clamped_not_trusted(documents):
    a, b = two_docs()
    app, uidoc = make_uiapp([a, b], 0, selected=[101])
    data = documents.snapshot(app, uidoc, body(tower_identity(), max_elements=10 ** 9, max_parameters="x")).data
    assert data["truncation"]["maxElements"] == documents.module.MAX_ELEMENTS_CAP
    assert data["truncation"]["maxParameters"] == documents.module.MAX_PARAMETERS_DEFAULT


def test_snapshot_empty_selection_is_ok(documents):
    a, b = two_docs()
    app, uidoc = make_uiapp([a, b], 0, selected=[])
    result = documents.snapshot(app, uidoc, body(tower_identity()))
    assert result.status == 200
    assert result.data["emptySelection"] is True and result.data["elements"] == []
    assert result.data["truncation"]["elementsTotal"] == 0


def test_snapshot_pinned_document_not_open(documents):
    a, b = two_docs()
    app, uidoc = make_uiapp([a, b], 0, selected=[101])
    result = documents.snapshot(app, uidoc, body({"creationGuid": "zzzz-9999", "pathName": ""}))
    assert result.status == 409
    assert result.data["code"] == "DOCUMENT_NOT_OPEN" and result.data["status"] == "error"
    assert "elements" not in result.data  # nothing from any other document


def test_snapshot_open_but_not_active_is_identity_mismatch(documents):
    a, b = two_docs()
    app, uidoc = make_uiapp([a, b], active_index=1, selected=[101])  # Podium active
    result = documents.snapshot(app, uidoc, body(tower_identity()))
    assert result.status == 409 and result.data["code"] == "IDENTITY_MISMATCH"
    assert result.data["reason"] == "NOT_ACTIVE_DOCUMENT"
    assert "elements" not in result.data


def test_snapshot_path_differs_is_identity_mismatch(documents):
    a, b = two_docs()
    app, uidoc = make_uiapp([a, b], 0, selected=[101])
    result = documents.snapshot(app, uidoc, body({"creationGuid": "aaaa-1111", "pathName": "C:\\p\\copy.rvt"}))
    assert result.data["code"] == "IDENTITY_MISMATCH" and result.data["reason"] == "PATH_DIFFERS"


def test_snapshot_save_as_twins_are_told_apart_by_path(documents):
    original = FakeDoc("Tower", "C:\\p\\tower.rvt", "aaaa-1111", elements=[WALL])
    twin = FakeDoc("Tower2", "C:\\p\\tower2.rvt", "aaaa-1111", elements=[DOOR])
    app, uidoc = make_uiapp([original, twin], active_index=1, selected=[102])
    ok = documents.snapshot(app, uidoc, body({"creationGuid": "aaaa-1111", "pathName": "C:\\p\\tower2.rvt"}))
    assert ok.status == 200 and ok.data["elements"][0]["elementId"] == 102
    wrong = documents.snapshot(app, uidoc, body({"creationGuid": "aaaa-1111", "pathName": "C:\\p\\tower.rvt"}))
    assert wrong.data["code"] == "IDENTITY_MISMATCH"


def test_snapshot_guid_compare_is_case_insensitive(documents):
    a, b = two_docs()
    app, uidoc = make_uiapp([a, b], 0, selected=[101])
    result = documents.snapshot(app, uidoc, body({"creationGuid": "AAAA-1111", "pathName": a.PathName}))
    assert result.status == 200


def test_snapshot_unsaved_document_is_pinned_by_guid_and_empty_path(documents):
    a, b = two_docs()
    app, uidoc = make_uiapp([a, b], active_index=1, selected=[])
    result = documents.snapshot(app, uidoc, body({"creationGuid": "bbbb-2222", "pathName": ""}))
    assert result.status == 200


@pytest.mark.parametrize("payload", [
    None, {}, {"identity": None}, {"identity": {}}, {"identity": {"creationGuid": ""}},
    {"identity": "aaaa-1111"}, {"identity": {"pathName": "C:\\p\\tower.rvt"}},
])
def test_snapshot_requires_an_identity(documents, payload):
    a, b = two_docs()
    app, uidoc = make_uiapp([a, b], 0, selected=[101])
    result = documents.snapshot(app, uidoc, SimpleNamespace(data=payload))
    assert result.status == 400 and result.data["code"] == "BAD_REQUEST"


def test_snapshot_accepts_a_json_string_body(documents):
    a, b = two_docs()
    app, uidoc = make_uiapp([a, b], 0, selected=[101])
    raw = json.dumps({"identity": tower_identity()})
    assert documents.snapshot(app, uidoc, SimpleNamespace(data=raw)).status == 200


def test_snapshot_accepts_a_text_plain_bytes_body(documents):
    # Under IronPython 3.4 a text/plain body reaches the route unparsed, as bytes (G-12).
    a, b = two_docs()
    app, uidoc = make_uiapp([a, b], 0, selected=[101])
    raw = json.dumps({"identity": tower_identity()}).encode("utf-8")
    assert documents.snapshot(app, uidoc, SimpleNamespace(data=raw)).status == 200


def test_snapshot_never_reads_when_no_document_is_active(documents):
    a, _ = two_docs()
    app = SimpleNamespace(Application=SimpleNamespace(Documents=[a]), ActiveUIDocument=None)
    result = documents.snapshot(app, None, body(tower_identity()))
    assert result.data["code"] == "IDENTITY_MISMATCH" and result.data["reason"] == "NOT_ACTIVE_DOCUMENT"


def test_document_handlers_declare_api_context(documents):
    import inspect

    assert "uiapp" in inspect.signature(documents.list).parameters
    assert {"uiapp", "uidoc"} <= set(inspect.signature(documents.snapshot).parameters)


# --- MCP client: structured outcomes ---------------------------------------------

@pytest.fixture
def no_machine_config(monkeypatch):
    """Isolate from this PC's pyRevit config and network."""
    monkeypatch.setattr(dro, "read_routes_config", lambda path=None: {"enabled": None, "host": None})
    monkeypatch.setattr(dro, "probe_non_loopback", lambda port=48884, **k: None)


def client_with(handler):
    import main

    client = main.DegramClient("http://127.0.0.1:48884/revit_mcp", host="127.0.0.1", port=48884)
    client._http = httpx.AsyncClient(base_url=client.root, transport=httpx.MockTransport(handler))
    return client


def test_timeout_maps_to_busy(no_machine_config):
    def handler(request):
        raise httpx.ReadTimeout("slow", request=request)

    out = run(client_with(handler).get("/model_info/"))
    assert out["status"] == "error" and out["code"] == "BUSY"


def test_connection_refused_maps_to_bridge_off(no_machine_config):
    def handler(request):
        raise httpx.ConnectError("refused", request=request)

    out = run(client_with(handler).get("/status/"))
    assert out["code"] == "BRIDGE_OFF"


def test_connection_refused_with_routes_disabled_in_config(monkeypatch, no_machine_config):
    monkeypatch.setattr(dro, "read_routes_config", lambda path=None: {"enabled": False, "host": "127.0.0.1"})

    def handler(request):
        raise httpx.ConnectError("refused", request=request)

    assert run(client_with(handler).get("/status/"))["code"] == "ROUTES_DISABLED"


def test_404_maps_to_extension_not_loaded(no_machine_config):
    out = run(client_with(lambda r: httpx.Response(404, text="API is not defined")).get("/status/"))
    assert out["code"] == "EXTENSION_NOT_LOADED"
    out = run(client_with(lambda r: httpx.Response(404, json={"exception": {"message": "x"}})).get("/status/"))
    assert out["code"] == "EXTENSION_NOT_LOADED"


def test_handler_404_with_error_body_is_a_route_error(no_machine_config):
    out = run(client_with(lambda r: httpx.Response(404, json={"error": "Element not found."}))
              .get("/element_properties/9"))
    assert out["code"] == "ROUTE_ERROR" and out["error"] == "Element not found."


def test_routes_disabled_response_passes_through(no_machine_config):
    body_ = {"status": "error", "code": "ROUTES_DISABLED", "error": "disabled"}
    out = run(client_with(lambda r: httpx.Response(503, json=body_)).get("/status/"))
    assert out == body_


@pytest.mark.parametrize("status", [406, 408])
def test_host_timeout_or_denial_is_busy(no_machine_config, status):
    out = run(client_with(lambda r: httpx.Response(status, json={"exception": {"message": "x"}})).get("/status/"))
    assert out["code"] == "BUSY"


def test_no_document_503_is_setup_incomplete(no_machine_config):
    payload = {"status": "unhealthy", "error": "No active Revit document"}
    out = run(client_with(lambda r: httpx.Response(503, json=payload)).get("/status/"))
    assert out["code"] == "SETUP_INCOMPLETE" and out["reason"] == "NO_DOCUMENT_OPEN"


def test_success_payload_is_returned_untouched(no_machine_config):
    out = run(client_with(lambda r: httpx.Response(200, json={"documents": []})).get("/list_open_documents/"))
    assert out == {"documents": []}


def test_identity_mismatch_outcome_passes_through_with_its_code(no_machine_config):
    payload = {"status": "error", "code": "IDENTITY_MISMATCH", "reason": "NOT_ACTIVE_DOCUMENT", "error": "x"}
    out = run(client_with(lambda r: httpx.Response(409, json=payload)).post("/selection_snapshot/", {}))
    assert out == payload


def test_outcomes_never_use_free_text_error_strings(no_machine_config):
    def boom(request):
        raise httpx.ConnectError("refused", request=request)

    for handler in (boom, lambda r: httpx.Response(500, text="<html>oops</html>")):
        out = run(client_with(handler).get("/status/"))
        assert isinstance(out, dict) and out["status"] == "error" and out["code"] in dro.ERROR_CODES


def test_tool_returns_structured_json_not_error_text(no_machine_config):
    import main

    def boom(request):
        raise httpx.ConnectError("refused", request=request)

    from tools import structured_helper

    client = client_with(boom)
    helper = structured_helper(client.get)
    text = run(helper("/status/"))
    assert json.loads(text)["code"] == "BRIDGE_OFF"
    assert not text.startswith("Error:")


def test_get_selection_snapshot_tool_posts_identity_and_limits(no_machine_config):
    import main

    seen = {}

    def handler(request):
        seen["path"] = request.url.path
        seen["type"] = request.headers.get("content-type")
        seen["body"] = json.loads(request.content)
        return httpx.Response(200, json={"status": "ok", "elements": []})

    client = client_with(handler)
    tools = {t.name: t for t in run(main.mcp.list_tools())}
    assert "get_selection_snapshot" in tools
    from tools.degram_tools import register_degram_tools
    from mcp.server.fastmcp import FastMCP

    probe = FastMCP("probe")
    register_degram_tools(probe, client.get, client.post)
    result = run(probe.call_tool("get_selection_snapshot",
                                 {"identity": {"creationGuid": "g", "pathName": "p"}, "max_elements": 5}))
    text = result[0][0].text if isinstance(result, tuple) else result[0].text
    assert json.loads(text)["status"] == "ok"
    assert seen["path"].endswith("/selection_snapshot/")
    # Not application/json: pyRevit's own JSON parse fails under IronPython 3.4 (G-12).
    assert seen["type"].startswith("text/plain")
    assert seen["body"] == {"identity": {"creationGuid": "g", "pathName": "p"},
                            "max_elements": 5, "max_parameters": 50}


# --- MCP client: serialization -----------------------------------------------------

def test_calls_are_serialized_by_one_lock(no_machine_config):
    state = {"active": 0, "peak": 0}

    async def slow(request):
        state["active"] += 1
        state["peak"] = max(state["peak"], state["active"])
        await asyncio.sleep(0.05)
        state["active"] -= 1
        return httpx.Response(200, json={"ok": True})

    client = client_with(slow)

    async def go():
        return await asyncio.gather(*[client.get("/status/") for _ in range(5)])

    results = run(go())
    assert all(r == {"ok": True} for r in results)
    assert state["peak"] == 1


def test_waiting_for_the_lock_past_the_deadline_is_busy(no_machine_config):
    async def slow(request):
        await asyncio.sleep(0.3)
        return httpx.Response(200, json={"ok": True})

    client = client_with(slow)
    client.lock_timeout = 0.05

    async def go():
        return await asyncio.gather(client.get("/status/"), client.get("/status/"))

    first, second = run(go())
    assert first == {"ok": True}
    assert second["code"] == "BUSY"


def test_no_automatic_retry(no_machine_config):
    calls = []

    def handler(request):
        calls.append(1)
        raise httpx.ReadTimeout("slow", request=request)

    run(client_with(handler).get("/status/"))
    assert len(calls) == 1


# --- loopback fail-closed (D-23) ------------------------------------------------------

def test_non_loopback_listener_refuses_every_read(monkeypatch):
    monkeypatch.setattr(dro, "read_routes_config", lambda path=None: {"enabled": None, "host": None})
    monkeypatch.setattr(dro, "local_addresses", lambda hostname=None: ["192.168.1.50"])
    attempts = []

    def fake_connect(addr, port, timeout):
        attempts.append((addr, port))
        return addr == "192.168.1.50" and port == 48884

    monkeypatch.setattr(dro, "_connect", fake_connect)
    reads = []

    def handler(request):
        reads.append(request)
        return httpx.Response(200, json={"ok": True})

    out = run(client_with(handler).get("/status/"))
    assert out["status"] == "error" and out["code"] == "SETUP_INCOMPLETE"
    assert out["reason"] == "ROUTES_NOT_LOOPBACK"
    assert reads == []  # no read was issued
    assert ("192.168.1.50", 48884) in attempts


def test_loopback_only_listener_is_ok(monkeypatch):
    monkeypatch.setattr(dro, "read_routes_config", lambda path=None: {"enabled": None, "host": None})
    monkeypatch.setattr(dro, "local_addresses", lambda hostname=None: ["192.168.1.50", "fe80::1"])

    monkeypatch.setattr(dro, "_connect", lambda addr, port, timeout: False)
    out = run(client_with(lambda r: httpx.Response(200, json={"ok": True})).get("/status/"))
    assert out == {"ok": True}


def test_probe_returns_the_answering_address(monkeypatch):
    monkeypatch.setattr(dro, "_connect", lambda addr, port, timeout: addr == "10.0.0.7")
    assert dro.probe_non_loopback(48884, addresses=["10.0.0.5", "10.0.0.7"]) == "10.0.0.7"
    assert dro.probe_non_loopback(48884, addresses=["10.0.0.5"]) is None


def test_connect_uses_a_real_tcp_connect():
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.bind(("127.0.0.1", 0))
    server.listen(1)
    port = server.getsockname()[1]
    try:
        assert dro._connect("127.0.0.1", port, 0.3) is True
    finally:
        server.close()
    assert dro._connect("127.0.0.1", port, 0.3) is False  # nothing listens any more


def test_local_addresses_excludes_loopback_and_wildcards(monkeypatch):
    infos = [(2, 1, 6, "", ("127.0.0.1", 0)), (2, 1, 6, "", ("192.168.1.9", 0)),
             (23, 1, 6, "", ("::1", 0, 0, 0)), (2, 1, 6, "", ("0.0.0.0", 0))]
    monkeypatch.setattr(socket, "getaddrinfo", lambda *a, **k: infos)
    monkeypatch.setattr(socket, "gethostbyname_ex", lambda h: (h, [], ["10.1.1.1", "127.0.1.1"]))
    assert dro.local_addresses("pc") == ["10.1.1.1", "192.168.1.9"]


def test_config_host_not_loopback_refuses_reads(monkeypatch):
    monkeypatch.setattr(dro, "read_routes_config", lambda path=None: {"enabled": True, "host": "0.0.0.0"})
    monkeypatch.setattr(dro, "probe_non_loopback", lambda port=48884, **k: None)
    reads = []
    out = run(client_with(lambda r: reads.append(r) or httpx.Response(200, json={})).get("/status/"))
    assert out["code"] == "SETUP_INCOMPLETE" and out["reason"] == "ROUTES_NOT_LOOPBACK"
    assert reads == []


def test_non_loopback_revit_host_is_refused(monkeypatch, no_machine_config):
    import main

    client = main.DegramClient("http://10.0.0.9:48884/revit_mcp", host="10.0.0.9", port=48884)
    out = run(client.get("/status/"))
    assert out["code"] == "SETUP_INCOMPLETE" and out["reason"] == "REVIT_HOST_NOT_LOOPBACK"


def test_routes_config_reader(tmp_path):
    ini = tmp_path / "pyRevit_config.ini"
    ini.write_text('[routes]\nenabled = true\nhost = "127.0.0.1"\nport = 48884\n', encoding="utf-8")
    assert dro.read_routes_config(str(ini)) == {"enabled": True, "host": "127.0.0.1"}
    ini.write_text('[routes]\nenabled = false\nhost = "0.0.0.0"\n', encoding="utf-8")
    assert dro.read_routes_config(str(ini)) == {"enabled": False, "host": "0.0.0.0"}
    assert dro.read_routes_config(str(tmp_path / "missing.ini")) == {"enabled": None, "host": None}


def test_extension_registers_nothing_off_loopback_end_to_end(monkeypatch):
    _, registry = load_startup(monkeypatch, routes_host="0.0.0.0")
    assert registry == []
