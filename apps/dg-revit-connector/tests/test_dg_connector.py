# -*- coding: utf-8 -*-
"""Offline tests of the pure DG Revit connector library (plan 1303-11 task 2).

No Revit, no network, no credentials: the DG data service is a fake opener and
the fixtures are the synthetic revit-mcp samples of plan 1303-04, so the ported
descriptor rules are checked against ``tools/mapping/revit_read.py`` itself.
"""

import datetime
import json
import os
import socket
import sys
import urllib.error

import pytest

HERE = os.path.dirname(os.path.abspath(__file__))
APP_ROOT = os.path.dirname(HERE)
REPO_ROOT = os.path.dirname(os.path.dirname(APP_ROOT))
LIB_DIR = os.path.join(APP_ROOT, "lib")
MAPPING_DIR = os.path.join(REPO_ROOT, "tools", "mapping")
FIXTURE_DIR = os.path.join(MAPPING_DIR, "tests", "fixtures")

if LIB_DIR not in sys.path:
    sys.path.insert(0, LIB_DIR)

from dg_connector import descriptors, dg_client, docs, loop, palette  # noqa: E402
from dg_connector import state as connector_state  # noqa: E402

SNAPSHOT_FIXTURE = os.path.join(FIXTURE_DIR, "selection_snapshot_sample.json")
PROPERTIES_FIXTURE = os.path.join(FIXTURE_DIR, "element_properties_sample.json")

NOW = datetime.datetime(2026, 10, 18, 9, 0, 30)


# --- fixtures -----------------------------------------------------------------

def _load_json(path):
    with open(path, "r", encoding="utf-8") as handle:
        return json.load(handle)


def _revit_read():
    """The reference implementation of the descriptor rules (read only)."""
    if MAPPING_DIR not in sys.path:
        sys.path.insert(0, MAPPING_DIR)
    import revit_read
    return revit_read


@pytest.fixture(scope="module")
def snapshot():
    return _load_json(SNAPSHOT_FIXTURE)


@pytest.fixture(scope="module")
def properties_by_id():
    saved = _load_json(PROPERTIES_FIXTURE)
    return dict((response["element_id"], response)
                for response in saved["responses"] if isinstance(response, dict))


def element_rows(snapshot, properties_by_id, adaptive_counts=None):
    """Rows in the ``descriptors`` row contract, built from the two fixtures."""
    adaptive_counts = adaptive_counts or {}
    rows = []
    for element in snapshot["elements"]:
        properties = properties_by_id.get(element.get("elementId")) or {}
        rows.append({
            "uniqueId": element.get("uniqueId"),
            "elementId": element.get("elementId"),
            "category": element.get("category") or properties.get("category") or "",
            "family": properties.get("family") or "",
            "typeName": element.get("typeName") or properties.get("type") or "",
            "parameters": list(element.get("parameters") or []),
            "typeParameters": [{"name": parameter.get("name"), "value": parameter.get("value")}
                               for parameter in (properties.get("parameters") or [])],
            "adaptivePointCount": adaptive_counts.get(element.get("uniqueId")),
        })
    return rows


# --- descriptors: parity with tools/mapping/revit_read.py ---------------------

def test_descriptor_parity_with_revit_read(snapshot, properties_by_id):
    revit_read = _revit_read()
    reference = revit_read.snapshot_to_descriptors(snapshot, properties_by_id)
    actual = descriptors.rows_to_descriptors(element_rows(snapshot, properties_by_id))
    assert actual == reference
    assert len(actual) == len(snapshot["elements"])


def test_descriptor_geometry_only_for_adaptive_components(snapshot, properties_by_id):
    revit_read = _revit_read()
    adaptive = {"5f3c1a2e-0000-4000-8000-000000100101-0001b00": 6,
                "5f3c1a2e-0000-4000-8000-000000100107-0001b30": 3}
    expected = revit_read.snapshot_to_descriptors(snapshot, properties_by_id)
    for descriptor in expected:
        if descriptor["nativeId"] in adaptive:
            descriptor["geometry"] = {"vertexCount": adaptive[descriptor["nativeId"]]}

    actual = descriptors.rows_to_descriptors(
        element_rows(snapshot, properties_by_id, adaptive_counts=adaptive))
    assert actual == expected
    for descriptor in actual:
        if descriptor["nativeId"] in adaptive:
            assert descriptor["geometry"] == {"vertexCount": adaptive[descriptor["nativeId"]]}
        else:
            assert "geometry" not in descriptor


def test_descriptor_never_carries_bounding_boxes(snapshot, properties_by_id):
    rows = element_rows(snapshot, properties_by_id, adaptive_counts={
        "5f3c1a2e-0000-4000-8000-000000100101-0001b00": 6})
    for descriptor in descriptors.rows_to_descriptors(rows):
        geometry = descriptor.get("geometry")
        if geometry is not None:
            assert list(geometry.keys()) == ["vertexCount"]
        for banned in ("widthM", "heightM", "planarityDeviationM"):
            assert banned not in descriptor
            assert banned not in descriptor["parameters"]


def test_length_parameters_get_a_metre_copy():
    rows = [{
        "uniqueId": "uid-1", "elementId": 1, "category": "Generic Models",
        "family": "Panel", "typeName": "Glass",
        "parameters": [{"name": "Offset from Host", "storageType": "Double",
                        "unit": "Millimeters", "displayValue": "304.8 mm", "value": 1.0}],
        "typeParameters": [], "adaptivePointCount": None,
    }]
    descriptor = descriptors.rows_to_descriptors(rows)[0]
    assert descriptor["parameters"]["Offset from Host"] == "304.8 mm"
    assert descriptor["parameters"]["Offset from Host_m"] == 0.3048
    assert descriptor["name"] == "Panel : Glass"


def test_family_falls_back_to_the_family_parameter():
    rows = [{
        "uniqueId": "uid-1", "elementId": 1, "category": "Generic Models",
        "family": "", "typeName": "Glass",
        "parameters": [{"name": "Family and Type", "storageType": "String", "unit": None,
                        "displayValue": "Facade Panel Glass: Glass", "value": "Facade Panel Glass: Glass"}],
        "typeParameters": [], "adaptivePointCount": None,
    }]
    descriptor = descriptors.rows_to_descriptors(rows)[0]
    assert descriptor["family"] == "Facade Panel Glass"
    assert descriptor["name"] == "Facade Panel Glass : Glass"


def test_missing_family_name_sets_the_non_ascii_marker():
    rows = [{
        "uniqueId": "uid-1", "elementId": 1, "category": "Generic Models",
        "family": "Facade?", "typeName": "Glass", "parameters": [], "typeParameters": [],
        "adaptivePointCount": None,
    }]
    descriptor = descriptors.rows_to_descriptors(rows)[0]
    assert descriptor["parameters"][descriptors.NON_ASCII_MARKER] is True


def test_type_parameters_never_override_an_instance_parameter():
    rows = [{
        "uniqueId": "uid-1", "elementId": 1, "category": "Generic Models",
        "family": "Panel", "typeName": "Glass",
        "parameters": [{"name": "Mark", "storageType": "String", "unit": None,
                        "displayValue": "G-1", "value": "G-1"}],
        "typeParameters": [{"name": "Mark", "value": "TYPE-1"},
                           {"name": "Type Mark", "value": "G"},
                           {"name": "Bad?Name", "value": "ignored"},
                           {"name": "Empty", "value": "  "}],
        "adaptivePointCount": None,
    }]
    parameters = descriptors.rows_to_descriptors(rows)[0]["parameters"]
    assert parameters["Mark"] == "G-1"
    assert parameters["Type Mark"] == "G"
    assert "Bad?Name" not in parameters
    assert "Empty" not in parameters


def test_ifc_export_in_english_and_russian(snapshot, properties_by_id):
    by_uid = dict((descriptor["nativeId"], descriptor)
                  for descriptor in descriptors.rows_to_descriptors(element_rows(snapshot, properties_by_id)))
    english = by_uid["5f3c1a2e-0000-4000-8000-000000100105-0001b20"]
    russian = by_uid["5f3c1a2e-0000-4000-8000-000000100107-0001b30"]
    assert english["ifc"] == {"entity": "IfcPlate", "predefinedType": "CURTAIN_PANEL"}
    assert russian["ifc"] == {"entity": "IfcPlate", "predefinedType": None}
    assert "ifc" not in by_uid["5f3c1a2e-0000-4000-8000-000000100101-0001b00"]


def test_rows_to_descriptors_skips_missing_and_repeated_unique_ids():
    row = {"uniqueId": "uid-a", "elementId": 1, "category": "", "family": "", "typeName": "",
           "parameters": [], "typeParameters": [], "adaptivePointCount": None}
    rows = [row,
            dict(row),
            {"uniqueId": "  ", "elementId": 2},
            {"elementId": 3},
            "not a row",
            {"uniqueId": "uid-b", "elementId": 4, "category": "", "family": "", "typeName": "",
             "parameters": [], "typeParameters": [], "adaptivePointCount": None},
            {"uniqueId": "uid-c", "elementId": 5}]
    result = descriptors.rows_to_descriptors(rows)
    assert [descriptor["nativeId"] for descriptor in result] == ["uid-a", "uid-b", "uid-c"]
    assert descriptors.rows_to_descriptors(rows, max_elements=2) == result[:2]
    assert descriptors.rows_to_descriptors(rows, max_elements=0) == []
    with pytest.raises(ValueError):
        descriptors.rows_to_descriptors(rows, max_elements="many")


def test_adaptive_count_must_be_a_positive_int():
    for count in (0, -3, True, "6", 3.0, None):
        row = {"uniqueId": "uid", "elementId": 1, "category": "", "family": "", "typeName": "",
               "parameters": [], "typeParameters": [], "adaptivePointCount": count}
        assert "geometry" not in descriptors.row_to_descriptor(row)


# --- docs ---------------------------------------------------------------------

def test_document_key_of_the_facade_model():
    assert docs.document_key("AdaptComponent_V18-dg-mapping.rvt") == "adaptcomponent_v18-dg-mapping"
    assert docs.document_key("AdaptComponent_V18-dg-mapping.RVT") == "adaptcomponent_v18-dg-mapping"


def test_document_key_keeps_cyrillic_letters():
    assert docs.document_key("\u0424\u0430\u0441\u0430\u0434_\u041e\u0440\u0438\u043e\u043d.rvt") == \
        "\u0444\u0430\u0441\u0430\u0434_\u043e\u0440\u0438\u043e\u043d"


def test_document_key_of_a_full_windows_path():
    path = "C:\\Users\\Admin\\Models\\AdaptComponent_V18-dg-mapping.rvt"
    assert docs.document_key(path) == "adaptcomponent_v18-dg-mapping"


def test_document_key_replaces_every_other_character():
    assert docs.document_key("Adapt Component (V18) #2.rvt") == "adapt-component--v18---2"
    assert docs.document_key("plan.ghx") == "plan"
    assert docs.document_key("plan.gh") == "plan"
    assert docs.document_key("  AdaptComponent_V18.rvt  ") == "adaptcomponent_v18"


def test_document_key_of_empty_input_is_revit():
    assert docs.document_key("") == "revit"
    assert docs.document_key("   ") == "revit"
    assert docs.document_key(None) == "revit"


def test_session_label_uses_the_middle_dot_and_local_time():
    label = docs.session_label("adaptcomponent_v18-dg-mapping",
                               datetime.datetime(2026, 10, 18, 9, 30, 5))
    assert label == "adaptcomponent_v18-dg-mapping \u00b7 09:30:05"
    assert label.split(" \u00b7 ") == ["adaptcomponent_v18-dg-mapping", "09:30:05"]


# --- palette ------------------------------------------------------------------

def test_palette_matches_the_grasshopper_colours():
    assert palette.STATE_COLOURS == {
        "confirmed": (0x2E, 0x7D, 0x32),
        "auto": (0x15, 0x65, 0xC0),
        "suggested": (0xF9, 0xA8, 0x25),
        "ambiguous": (0xE6, 0x51, 0x00),
        "unmapped": (0x9E, 0x9E, 0x9E),
    }
    for state_name, colour in palette.STATE_COLOURS.items():
        assert palette.colour_for(state_name) == colour
    assert palette.colour_for(" CONFIRMED ") == palette.STATE_COLOURS["confirmed"]


def test_palette_unknown_state_is_unmapped_grey():
    assert palette.colour_for("whatever") == (0x9E, 0x9E, 0x9E)
    assert palette.colour_for(None) == (0x9E, 0x9E, 0x9E)


# --- dg_client: fake transport -------------------------------------------------

class FakeResponse(object):
    """The answer surface the client uses: status/getcode, read(), headers, close."""

    def __init__(self, status, body="", headers=None):
        if isinstance(body, bytes):
            self._body = body
        else:
            self._body = (body or "").encode("utf-8")
        self.status = status
        self.headers = headers or {}
        self.closed = False

    def read(self):
        return self._body

    def getcode(self):
        return self.status

    def close(self):
        self.closed = True


class FakeOpener(object):
    """``opener(request, timeout)`` that replays canned answers and records requests."""

    def __init__(self, answers):
        self.answers = list(answers)
        self.requests = []
        self.timeouts = []

    def __call__(self, request, timeout):
        self.requests.append(request)
        self.timeouts.append(timeout)
        if not self.answers:
            raise AssertionError("unexpected request to {}".format(request.full_url))
        answer = self.answers.pop(0)
        if isinstance(answer, BaseException):
            raise answer
        return answer


def header(request, name):
    """Case-insensitive request header lookup (urllib capitalises header keys)."""
    for key, value in request.header_items():
        if key.lower() == name.lower():
            return value
    return None


def cookie_answer(value="abc123"):
    return FakeResponse(200, "{}", {"Set-Cookie": "{}={}; Path=/; HttpOnly".format(
        dg_client.SESSION_COOKIE_NAME, value)})


def mint_answer(token="dgk_session-token", project="v12-hexagonal-facade-01"):
    return FakeResponse(200, json.dumps({
        "token": token,
        "project": project,
        "expiresAt": "2026-10-18T10:00:00Z",
        "neo4j": {"uri": "bolt://neo4j:7687", "user": "neo4j", "password": "db-secret"},
    }))


def test_sign_in_mints_a_revit_connector_session():
    opener = FakeOpener([cookie_answer(), mint_answer(), FakeResponse(200, "{}")])
    result = dg_client.sign_in("http://localhost:8000", "owner", "hunter2",
                               "v12-hexagonal-facade-01", opener=opener)

    assert result == {"token": "dgk_session-token",
                      "project": "v12-hexagonal-facade-01",
                      "expiresAt": "2026-10-18T10:00:00Z"}
    assert sorted(result.keys()) == ["expiresAt", "project", "token"]

    login, mint, logout = opener.requests
    assert login.full_url == "http://localhost:8000/auth/login"
    assert login.get_method() == "POST"
    assert json.loads(login.data.decode("utf-8")) == {"username": "owner", "password": "hunter2"}
    assert header(login, "Content-Type") == "application/json"
    assert header(login, "X-DG-CSRF") == "1"

    assert mint.full_url == "http://localhost:8000/auth/connector-session"
    assert json.loads(mint.data.decode("utf-8")) == {"project": "v12-hexagonal-facade-01",
                                                     "connector_id": "revit"}
    assert header(mint, "Cookie") == "dg_session=abc123"
    assert header(mint, "X-DG-CSRF") == "1"
    assert header(mint, "Authorization") is None

    assert logout.full_url == "http://localhost:8000/auth/logout"
    assert header(logout, "Cookie") == "dg_session=abc123"
    assert opener.timeouts == [15.0, 15.0, 15.0]


def test_sign_in_trailing_slash_and_connector_id_override():
    opener = FakeOpener([cookie_answer(), mint_answer(), FakeResponse(200, "{}")])
    dg_client.sign_in("http://127.0.0.1:8000/", "owner", "pw", "p1", connector_id=" revit ",
                      opener=opener)
    assert opener.requests[0].full_url == "http://127.0.0.1:8000/auth/login"
    assert json.loads(opener.requests[1].data.decode("utf-8"))["connector_id"] == "revit"


def test_unicode_project_is_utf8_percent_encoded_in_a_session_query():
    opener = FakeOpener([FakeResponse(200, json.dumps({"sessionId": "ms-1"}))])
    project = "фасад"
    dg_client.get_session("http://127.0.0.1:8000", "dgk_token", project, "ms-1", opener=opener)
    assert "project=%D1%84%D0%B0%D1%81%D0%B0%D0%B4" in opener.requests[0].full_url


@pytest.mark.parametrize("base_url", ["http://localhost:8000", "http://127.0.0.1:8000",
                                      "http://[::1]:8000", "https://dg.example"])
def test_sign_in_allowed_transports(base_url):
    opener = FakeOpener([cookie_answer(), mint_answer(), FakeResponse(200, "{}")])
    result = dg_client.sign_in(base_url, "owner", "pw", "p1", opener=opener)
    assert result["token"] == "dgk_session-token"
    assert opener.requests[0].full_url == base_url + "/auth/login"


@pytest.mark.parametrize("base_url", ["http://192.168.1.5:8000", "http://dg.example:8000",
                                      "http://10.0.0.7:8000"])
def test_insecure_transport_is_refused_before_any_request(base_url):
    opener = FakeOpener([])
    with pytest.raises(dg_client.DgClientError) as info:
        dg_client.sign_in(base_url, "owner", "hunter2", "p1", opener=opener)
    assert info.value.code == "INSECURE_TRANSPORT"
    assert info.value.status is None
    assert info.value.server_code is None
    assert opener.requests == []
    assert "hunter2" not in str(info.value)


@pytest.mark.parametrize("base_url", ["http://owner:secret@localhost:8000",
                                      "http://localhost:8000?project=p1",
                                      "localhost:8000"])
def test_unusable_base_urls_are_refused_before_any_request(base_url):
    opener = FakeOpener([])
    with pytest.raises(dg_client.DgClientError) as info:
        dg_client.sign_in(base_url, "owner", "hunter2", "p1", opener=opener)
    assert info.value.code == "UNREACHABLE"
    assert opener.requests == []
    assert "secret" not in str(info.value)
    assert "hunter2" not in str(info.value)


def test_sign_in_rejected():
    opener = FakeOpener([FakeResponse(401, json.dumps({"code": "AUTH_INVALID", "error": "bad login"}))])
    with pytest.raises(dg_client.DgClientError) as info:
        dg_client.sign_in("http://localhost:8000", "owner", "hunter2", "p1", opener=opener)
    assert info.value.code == "REJECTED"
    assert info.value.status == 401
    assert "AUTH_INVALID" in str(info.value)
    assert len(opener.requests) == 1  # no cookie captured, so no logout


def test_sign_in_throttled():
    opener = FakeOpener([FakeResponse(429, json.dumps({"code": "AUTH_THROTTLED"}))])
    with pytest.raises(dg_client.DgClientError) as info:
        dg_client.sign_in("http://localhost:8000", "owner", "pw", "p1", opener=opener)
    assert info.value.code == "THROTTLED"
    assert info.value.status == 429


def test_sign_in_without_a_session_cookie_is_unreachable():
    opener = FakeOpener([FakeResponse(200, "{}")])
    with pytest.raises(dg_client.DgClientError) as info:
        dg_client.sign_in("http://localhost:8000", "owner", "pw", "p1", opener=opener)
    assert info.value.code == "UNREACHABLE"
    assert "dg_session" in str(info.value)
    assert len(opener.requests) == 1


@pytest.mark.parametrize("status,code", [(401, "REJECTED"), (403, "FORBIDDEN"),
                                         (422, "PROJECT_REQUIRED"), (429, "THROTTLED"),
                                         (500, "HTTP_ERROR")])
def test_mint_status_mapping_and_logout_is_always_attempted(status, code):
    body = json.dumps({"code": "SERVER_CODE", "hint": "server hint"})
    opener = FakeOpener([cookie_answer(), FakeResponse(status, body), FakeResponse(200, "{}")])
    with pytest.raises(dg_client.DgClientError) as info:
        dg_client.sign_in("http://localhost:8000", "owner", "pw", "p1", opener=opener)
    assert info.value.code == code
    assert info.value.status == status
    assert info.value.server_code == "SERVER_CODE"
    assert "SERVER_CODE" in str(info.value)
    assert "server hint" in str(info.value)
    assert len(opener.requests) == 3
    assert opener.requests[2].full_url == "http://localhost:8000/auth/logout"


def test_logout_also_runs_when_the_mint_answer_is_malformed():
    opener = FakeOpener([cookie_answer(), FakeResponse(200, "not json"), FakeResponse(200, "{}")])
    with pytest.raises(dg_client.DgClientError) as info:
        dg_client.sign_in("http://localhost:8000", "owner", "pw", "p1", opener=opener)
    assert info.value.code == "UNREACHABLE"
    assert opener.requests[-1].full_url == "http://localhost:8000/auth/logout"


def test_mint_token_must_carry_the_dg_prefix():
    opener = FakeOpener([cookie_answer(), FakeResponse(200, json.dumps({"token": "not-a-dg-token"})),
                         FakeResponse(200, "{}")])
    with pytest.raises(dg_client.DgClientError) as info:
        dg_client.sign_in("http://localhost:8000", "owner", "pw", "p1", opener=opener)
    assert info.value.code == "UNREACHABLE"
    assert "dgk_" in str(info.value)


def test_network_failure_and_timeout_are_unreachable():
    opener = FakeOpener([urllib.error.URLError(socket.error("connection refused"))])
    with pytest.raises(dg_client.DgClientError) as info:
        dg_client.sign_in("http://localhost:8000", "owner", "pw", "p1", opener=opener)
    assert info.value.code == "UNREACHABLE"
    assert info.value.status is None

    opener = FakeOpener([socket.timeout("timed out")])
    with pytest.raises(dg_client.DgClientError) as info:
        dg_client.sign_in("http://localhost:8000", "owner", "pw", "p1", opener=opener)
    assert info.value.code == "UNREACHABLE"


def test_password_and_token_never_reach_an_exception():
    password = "hunter2-very-secret"
    opener = FakeOpener([FakeResponse(
        401, json.dumps({"code": "AUTH_INVALID", "error": "wrong password " + password}))])
    with pytest.raises(dg_client.DgClientError) as info:
        dg_client.sign_in("http://localhost:8000", "owner", password, "p1", opener=opener)
    assert password not in str(info.value)
    assert password not in repr(info.value)
    assert password not in info.value.message
    assert dg_client.REDACTED in str(info.value)

    token = "dgk_do-not-leak-me"
    opener = FakeOpener([FakeResponse(400, json.dumps({
        "code": "MAPPING_INPUT_INVALID", "error": "bad body for " + token}))])
    with pytest.raises(dg_client.DgClientError) as info:
        dg_client.create_session("http://localhost:8000", token, {"project": "p1"}, opener=opener)
    assert token not in str(info.value)
    assert token not in repr(info.value)
    assert dg_client.REDACTED in str(info.value)


# --- dg_client: session routes and sign-out ------------------------------------

def test_sign_out_returns_true_on_no_content():
    opener = FakeOpener([FakeResponse(204, "")])
    assert dg_client.sign_out("http://localhost:8000", "dgk_token", opener=opener) is True
    request = opener.requests[0]
    assert request.full_url == "http://localhost:8000/auth/connector-session"
    assert request.get_method() == "DELETE"
    assert header(request, "Authorization") == "Bearer dgk_token"
    assert header(request, "X-DG-CSRF") == "1"


@pytest.mark.parametrize("answer", [FakeResponse(401, "{}"), FakeResponse(500, "boom"),
                                    urllib.error.URLError(socket.error("down"))])
def test_sign_out_never_raises_and_is_false_on_trouble(answer):
    opener = FakeOpener([answer])
    assert dg_client.sign_out("http://localhost:8000", "dgk_token", opener=opener) is False


def test_sign_out_refuses_insecure_transport_and_an_empty_token():
    opener = FakeOpener([])
    assert dg_client.sign_out("http://192.168.1.5:8000", "dgk_token", opener=opener) is False
    assert dg_client.sign_out("http://localhost:8000", "", opener=opener) is False
    assert opener.requests == []


def test_create_session_posts_the_body_with_the_bearer():
    body = {"project": "p1", "platform": "revit", "label": "adaptcomponent_v18 \u00b7 09:00:00",
            "elements": [{"nativeId": "uid-1", "platform": "revit"}]}
    opener = FakeOpener([FakeResponse(201, json.dumps({"sessionId": "ms-0123456789ab"}))])
    result = dg_client.create_session("http://localhost:8000", "dgk_token", body, opener=opener)
    assert result == {"sessionId": "ms-0123456789ab"}
    request = opener.requests[0]
    assert request.full_url == "http://localhost:8000/mapping/sessions"
    assert request.get_method() == "POST"
    assert header(request, "Authorization") == "Bearer dgk_token"
    assert json.loads(request.data.decode("utf-8")) == body
    assert opener.timeouts == [60.0]


def test_get_session_uses_a_project_query():
    opener = FakeOpener([FakeResponse(200, json.dumps({"sessionId": "ms-0123456789ab"}))])
    result = dg_client.get_session("http://localhost:8000/", "dgk_token",
                                   "v12-hexagonal-facade-01", "ms-0123456789ab", opener=opener)
    assert result["sessionId"] == "ms-0123456789ab"
    request = opener.requests[0]
    assert request.full_url == ("http://localhost:8000/mapping/sessions/ms-0123456789ab"
                                "?project=v12-hexagonal-facade-01")
    assert request.get_method() == "GET"
    assert request.data is None
    assert header(request, "Authorization") == "Bearer dgk_token"
    assert opener.timeouts == [60.0]


def test_acknowledge_batch_posts_only_the_delivery_receipt():
    delivery = {"state": "written", "written": 4, "skipped": 0}
    opener = FakeOpener([FakeResponse(200, json.dumps({"batchId": "batch-four", "delivery": delivery}))])
    result = dg_client.acknowledge_batch(
        "http://localhost:8000", "dgk_token", "p1", "ms-0123456789ab", "batch-four", delivery,
        opener=opener)
    assert result["delivery"] == delivery
    [request] = opener.requests
    assert request.get_method() == "POST"
    assert request.full_url == "http://localhost:8000/mapping/sessions/ms-0123456789ab/apply"
    assert json.loads(request.data.decode("utf-8")) == {
        "project": "p1", "batchId": "batch-four", "delivery": delivery,
    }
    assert header(request, "Authorization") == "Bearer dgk_token"
    assert header(request, "X-DG-CSRF") == "1"


def test_apply_session_posts_the_project():
    opener = FakeOpener([FakeResponse(200, json.dumps({"applied": 2}))])
    result = dg_client.apply_session("http://localhost:8000", "dgk_token",
                                     "v12-hexagonal-facade-01", "ms-0123456789ab", opener=opener)
    assert result == {"applied": 2}
    request = opener.requests[0]
    assert request.full_url == ("http://localhost:8000/mapping/sessions/ms-0123456789ab/apply")
    assert request.get_method() == "POST"
    assert json.loads(request.data.decode("utf-8")) == {"project": "v12-hexagonal-facade-01"}
    assert header(request, "Authorization") == "Bearer dgk_token"


@pytest.mark.parametrize("status,code", [(401, "REJECTED"), (403, "FORBIDDEN"),
                                         (422, "PROJECT_REQUIRED"), (500, "HTTP_ERROR")])
def test_session_route_status_mapping(status, code):
    body = json.dumps({"code": "MAPPING_SESSION_NOT_FOUND", "error": "no such session"})
    opener = FakeOpener([FakeResponse(status, body)])
    with pytest.raises(dg_client.DgClientError) as info:
        dg_client.get_session("http://localhost:8000", "dgk_token", "p1", "ms-1", opener=opener)
    assert info.value.code == code
    assert info.value.status == status
    assert info.value.server_code == "MAPPING_SESSION_NOT_FOUND"
    assert "MAPPING_SESSION_NOT_FOUND" in str(info.value)


def test_session_routes_require_a_token():
    opener = FakeOpener([])
    with pytest.raises(dg_client.DgClientError) as info:
        dg_client.create_session("http://localhost:8000", "", {"project": "p1"}, opener=opener)
    assert info.value.code == "REJECTED"
    assert opener.requests == []


# --- loop ---------------------------------------------------------------------

def element(native_id, state, iris):
    return {"nativeId": native_id, "groupId": "G-1", "state": state,
            "roles": [{"classIri": iri, "state": state} for iri in iris]}


def mapping_session(elements=None, open_questions=0, answers=None,
                    created_at="2026-10-18T09:00:00Z", applied_at=None):
    session = {
        "sessionId": "ms-0123456789ab",
        "project": "v12-hexagonal-facade-01",
        "platform": "revit",
        "createdAt": created_at,
        "summary": {"total": len(elements or []), "openQuestions": open_questions},
        "questions": [],
        "groups": [],
        "elements": elements or [],
    }
    if answers is not None:
        session["answers"] = answers
    if applied_at is not None:
        session["appliedAt"] = applied_at
    return session


def memo_of(session):
    return {"lastDigest": loop.session_digest(session)}


def test_loop_constants():
    assert "wait-grace" not in loop.ACTIONS
    assert not hasattr(loop, "GRACE_SECONDS")
    assert loop.POLL_SECONDS == 3


def test_loop_done_wins():
    session = mapping_session([element("u1", "confirmed", ["ex:A"])],
                              applied_at="2026-10-18T09:00:20Z")
    action = loop.next_action(session, {"lastDigest": "stale"}, NOW)
    assert action["action"] == "done"
    assert action["digest"] == loop.session_digest(session)
    assert "secondsLeft" not in action


def test_loop_recolours_on_the_first_poll_and_after_a_state_change():
    session = mapping_session([element("u1", "suggested", ["ex:A"])], open_questions=1)
    first = loop.next_action(session, {}, NOW)
    assert first["action"] == "recolour"
    assert first["digest"] == loop.session_digest(session)

    assert loop.next_action(session, memo_of(session), NOW)["action"] == "idle"

    painted = memo_of(session)
    session["elements"][0]["state"] = "confirmed"
    assert loop.next_action(session, painted, NOW)["action"] == "recolour"


def test_loop_digest_is_order_independent_and_role_aware():
    first = mapping_session([element("u1", "auto", ["ex:B", "ex:A"]),
                             element("u2", "unmapped", [])])
    second = mapping_session([element("u2", "unmapped", []),
                              element("u1", "auto", ["ex:A", "ex:B"])])
    assert loop.session_digest(first) == loop.session_digest(second)
    second["elements"][0]["state"] = "ambiguous"
    assert loop.session_digest(first) != loop.session_digest(second)


def test_loop_idles_while_questions_are_open():
    session = mapping_session([element("u1", "suggested", ["ex:A"])], open_questions=2)
    action = loop.next_action(session, memo_of(session), NOW)
    assert action["action"] == "idle"
    assert "secondsLeft" not in action


@pytest.mark.parametrize("seconds", [3, 10, 30, 3600])
def test_loop_never_applies_a_draft_after_any_delay(seconds):
    session = mapping_session([element("u1", "confirmed", ["ex:A"])], open_questions=0,
                              answers=[{"decidedAt": "2026-10-18T09:00:00Z"}])
    action = loop.next_action(session, memo_of(session),
                             datetime.datetime(2026, 10, 18, 9) + datetime.timedelta(seconds=seconds))
    assert action["action"] == "idle" and "secondsLeft" not in action


def test_loop_delivers_explicit_batch_while_other_questions_remain():
    session = mapping_session([element("u1", "confirmed", ["ex:A"])], open_questions=6)
    batch = {"batchId": "batch-one", "delivery": {"state": "queued"}, "payload": {}}
    session["batches"] = [batch]
    assert loop.next_action(session, memo_of(session), NOW)["batch"] == batch
    batch["delivery"] = {"state": "written", "written": 1, "skipped": 0}
    assert loop.next_action(session, memo_of(session), NOW)["action"] == "idle"


def test_loop_idles_without_a_session_or_a_summary():
    assert loop.next_action(None, {}, NOW)["action"] == "idle"
    assert loop.next_action({}, {}, NOW)["action"] == "idle"
    empty = {"elements": []}
    assert loop.next_action(empty, memo_of(empty), NOW)["action"] == "idle"


def test_loop_lookups():
    session = mapping_session([
        element("u1", "confirmed", ["ex:A"]),
        element("u2", "ambiguous", ["ex:B"]),
        {"nativeId": "u3", "state": "auto",
         "roles": [{"classIri": "http://example.org/vocab#GroundFloorUnit"}]},
        {"nativeId": "u4", "state": "unmapped", "roles": [{"label": "GlassPanel"}]},
        {"state": "confirmed"},
    ])
    assert loop.states_by_uid(session) == {"u1": "confirmed", "u2": "ambiguous",
                                           "u3": "auto", "u4": "unmapped"}
    assert loop.roles_by_uid(session) == {"u1": ["A"], "u2": ["B"],
                                          "u3": ["GroundFloorUnit"], "u4": ["GlassPanel"]}
    assert loop.to_epoch("2026-10-18T09:00:00Z") == loop.to_epoch(
        datetime.datetime(2026, 10, 18, 9, 0, 0))
    assert loop.to_epoch("2026-10-18T12:00:00+03:00") == loop.to_epoch(
        datetime.datetime(2026, 10, 18, 9, 0, 0))
    assert loop.to_epoch("not a timestamp") is None


# --- state --------------------------------------------------------------------

@pytest.fixture()
def store():
    connector_state.ConnectorState().clear()
    yield connector_state.ConnectorState()
    connector_state.ConnectorState().clear()


def test_state_backend_is_a_shared_dict_outside_revit(store):
    other = connector_state.ConnectorState()
    store.set("url", "http://localhost:8000")
    store.set("token", "dgk_secret-token")
    store.set("project", "v12-hexagonal-facade-01")
    other.set("user", "owner")
    assert store.get("user") == "owner"
    assert store.get("url") == "http://localhost:8000"
    assert store.is_signed_in() is True
    assert connector_state.backend_name() == "memory"


def test_state_snapshot_never_contains_the_token(store):
    store.set("url", "http://localhost:8000")
    store.set("token", "dgk_secret-token")
    store.set("project", "p1")
    store.set("sessionId", "ms-0123456789ab")
    snapshot = store.snapshot()
    assert snapshot["signedIn"] is True
    assert "token" not in snapshot
    assert snapshot["sessionId"] == "ms-0123456789ab"
    assert "dgk_secret-token" not in json.dumps(snapshot)
    assert "dgk_secret-token" not in repr(store)
    store.sign_out()
    assert "signedIn=False" in repr(store)
    assert "dgk_secret-token" not in repr(store)


def test_state_set_none_removes_a_key(store):
    store.set("message", "ready")
    assert store.get("message") == "ready"
    store.set("message", None)
    assert store.get("message") is None
    assert store.get("message", "fallback") == "fallback"


def test_state_clear_session_keeps_the_sign_in(store):
    store.set("url", "http://localhost:8000")
    store.set("token", "dgk_token")
    store.set("user", "owner")
    store.set("project", "p1")
    store.set("sessionId", "ms-0123456789ab")
    store.set("documentKey", "adaptcomponent_v18-dg-mapping")
    store.set("viewId", "123")
    store.clear_session()
    assert store.get("sessionId") is None
    assert store.get("documentKey") is None
    assert store.get("viewId") is None
    assert store.is_signed_in() is True
    assert store.get("project") == "p1"


def test_state_sign_out_keeps_the_url(store):
    store.set("url", "http://localhost:8000")
    store.set("token", "dgk_token")
    store.set("user", "owner")
    store.set("project", "p1")
    store.set("sessionId", "ms-0123456789ab")
    store.sign_out()
    assert store.is_signed_in() is False
    assert store.get("token") is None
    assert store.get("project") is None
    assert store.get("sessionId") is None
    assert store.get("url") == "http://localhost:8000"
    assert store.snapshot() == {"signedIn": False, "url": "http://localhost:8000"}
