"""Offline tests for tools/mapping/revit_read.py (Phase 1303 plan 04).

No Revit and no network: requests go to a stub opener.
"""

import io
import json
import sys
import tempfile
import unittest
import urllib.error
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))

import revit_read as rr  # noqa: E402

SNAPSHOT = HERE / "fixtures" / "selection_snapshot_sample.json"
PROPERTIES = HERE / "fixtures" / "element_properties_sample.json"


def _load(path):
    return json.loads(path.read_text(encoding="utf-8"))


class _Response:
    def __init__(self, status, body):
        self.status = status
        self._raw = json.dumps(body).encode("utf-8")

    def read(self):
        return self._raw

    def close(self):
        pass


class StubOpener:
    """Records requests and answers from a route → body map."""

    def __init__(self, routes):
        self.routes = routes
        self.requests = []

    def __call__(self, request, timeout=None):
        self.requests.append((request.get_method(), request.full_url, dict(request.header_items()), request.data, timeout))
        path = request.full_url.split("/revit_mcp/", 1)[1]
        status, body = self.routes[path] if path in self.routes else (404, {"error": "unknown"})
        return _Response(status, body)


def _routes():
    snapshot = _load(SNAPSHOT)
    routes = {
        "status/": (200, {"status": "active", "health": "healthy", "revit_available": True}),
        "list_open_documents/": (200, {"status": "success", "documents": [
            {"title": "facade", "pathName": snapshot["identity"]["pathName"], "creationGuid": snapshot["identity"]["creationGuid"], "isActive": True, "isModified": False},
            {"title": "other", "pathName": "C:\\other.rvt", "creationGuid": "x", "isActive": False, "isModified": False},
        ]}),
        "selection_snapshot/": (200, snapshot),
    }
    for response in _load(PROPERTIES)["responses"]:
        routes["element_properties/{}".format(response["element_id"])] = (200, response)
    return routes


class ConversionTests(unittest.TestCase):
    def setUp(self):
        self.snapshot = _load(SNAPSHOT)
        self.properties = {r["element_id"]: r for r in _load(PROPERTIES)["responses"]}

    def test_fields_and_units(self):
        descriptors = rr.snapshot_to_descriptors(self.snapshot, self.properties)
        self.assertEqual(len(descriptors), 8)
        first = descriptors[0]
        self.assertEqual(first["nativeId"], self.snapshot["elements"][0]["uniqueId"])
        self.assertEqual(first["platform"], "revit")
        self.assertEqual(first["category"], "Generic Models")
        self.assertEqual(first["family"], "Facade_Module_Hex")
        self.assertEqual(first["type"], "Hex")
        self.assertEqual(first["name"], "Facade_Module_Hex : Hex")
        self.assertEqual(first["parameters"]["Mark"], "Hex-1")
        self.assertAlmostEqual(first["parameters"]["Offset from Host_m"], 0.3048)
        self.assertEqual(first["parameters"]["Type Mark"], "H")
        self.assertNotIn("Comments", first["parameters"])  # empty values are dropped

    def test_ifc_parameters_en_and_ru(self):
        descriptors = {d["parameters"]["Mark"]: d for d in rr.snapshot_to_descriptors(self.snapshot, self.properties)}
        self.assertEqual(descriptors["Glass-1"]["ifc"], {"entity": "IfcPlate", "predefinedType": "CURTAIN_PANEL"})
        self.assertEqual(descriptors["Tri-1"]["ifc"], {"entity": "IfcPlate", "predefinedType": None})
        self.assertNotIn("ifc", descriptors["Glass-2"])

    def test_missing_properties_tolerated(self):
        descriptors = rr.snapshot_to_descriptors(self.snapshot)
        self.assertEqual(len(descriptors), 8)
        self.assertNotIn("family", descriptors[0])
        self.assertEqual(descriptors[0]["type"], "Hex")

    def test_non_ascii_marker(self):
        element = dict(self.snapshot["elements"][0], category="Обобщ?нные модели")
        descriptor = rr.element_to_descriptor(element)
        self.assertIs(descriptor["parameters"][rr.NON_ASCII_MARKER], True)

    def test_skips_elements_without_unique_id_and_duplicates(self):
        snap = dict(self.snapshot)
        snap["elements"] = [self.snapshot["elements"][0], dict(self.snapshot["elements"][0]), {"elementId": 1}]
        self.assertEqual(len(rr.snapshot_to_descriptors(snap)), 1)


class RouteAllowlistTests(unittest.TestCase):
    def test_refuses_write_routes(self):
        for method, path in (("POST", "set_parameter/"), ("POST", "color_splash/"), ("POST", "modify_element/"),
                             ("POST", "delete_elements/"), ("GET", "export_ifc/"), ("POST", "status/"),
                             ("GET", "element_properties/abc"), ("GET", "element_properties/1/../set_parameter")):
            with self.assertRaises(rr.PathNotAllowedError, msg=(method, path)):
                rr.check_route(method, path)

    def test_allows_read_routes(self):
        self.assertEqual(rr.check_route("GET", "status/"), "status/")
        self.assertEqual(rr.check_route("POST", "selection_snapshot/"), "selection_snapshot/")
        self.assertEqual(rr.check_route("GET", "element_properties/100101"), "element_properties/")

    def test_base_must_be_loopback(self):
        for base in ("http://10.0.0.5:48884/revit_mcp", "https://127.0.0.1:48884/revit_mcp", "http://user:pw@127.0.0.1/x"):
            with self.assertRaises(ValueError, msg=base):
                rr.RevitReadClient(base=base)


class ClientTests(unittest.TestCase):
    def test_requests_are_read_only_with_text_plain_and_timeout(self):
        opener = StubOpener(_routes())
        client = rr.RevitReadClient(timeout=12, opener=opener)
        identity, descriptors, truncation = rr.read_selection(client)
        self.assertEqual(len(descriptors), 8)
        self.assertEqual(truncation["propertiesRequested"], 8)
        self.assertEqual(truncation["propertiesFailed"], [])
        self.assertEqual(identity["creationGuid"], "0f0e0d0c-1111-2222-3333-444455556666")
        for method, url, headers, data, timeout in opener.requests:
            self.assertTrue(url.startswith("http://127.0.0.1:48884/revit_mcp/"))
            self.assertEqual(timeout, 12.0)
            rr.check_route(method, url.split("/revit_mcp/", 1)[1])
            if method == "POST":
                self.assertEqual(headers.get("Content-type"), "text/plain; charset=utf-8")
                body = json.loads(data.decode("utf-8"))
                self.assertEqual(body["identity"]["creationGuid"], identity["creationGuid"])
                self.assertEqual((body["max_elements"], body["max_parameters"]), (1000, 200))

    def test_structured_error_and_unreachable(self):
        routes = _routes()
        routes["selection_snapshot/"] = (409, {"status": "error", "code": "IDENTITY_MISMATCH", "error": "PATH_DIFFERS"})
        client = rr.RevitReadClient(opener=StubOpener(routes))
        with self.assertRaises(rr.RevitReadError) as ctx:
            rr.read_selection(client)
        self.assertEqual(ctx.exception.code, "IDENTITY_MISMATCH")

        def refuse(request, timeout=None):
            raise urllib.error.URLError(ConnectionRefusedError("refused"))

        with self.assertRaises(rr.RevitReadError) as ctx:
            rr.RevitReadClient(opener=refuse).status()
        self.assertEqual(ctx.exception.code, "BRIDGE_OFF")

    def test_element_property_failure_is_recorded_not_fatal(self):
        routes = _routes()
        first = _load(SNAPSHOT)["elements"][0]["elementId"]
        routes["element_properties/{}".format(first)] = (500, {"error": "boom"})
        _, descriptors, truncation = rr.read_selection(rr.RevitReadClient(opener=StubOpener(routes)))
        self.assertEqual(len(descriptors), 8)
        self.assertEqual([f["code"] for f in truncation["propertiesFailed"]], ["ROUTE_ERROR"])

    def test_pick_identity_errors(self):
        with self.assertRaises(rr.RevitReadError) as none:
            rr.pick_identity({"documents": [{"isActive": False, "creationGuid": "a"}]})
        self.assertEqual(none.exception.code, "NO_ACTIVE_DOCUMENT")
        with self.assertRaises(rr.RevitReadError) as many:
            rr.pick_identity([{"isActive": True, "creationGuid": "a"}, {"isActive": True, "creationGuid": "b"}])
        self.assertEqual(many.exception.code, "AMBIGUOUS_ACTIVE_DOCUMENT")


class CliTests(unittest.TestCase):
    def test_dry_run_writes_upload_body(self):
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp) / "upload.json"
            stdout, stderr = io.StringIO(), io.StringIO()
            with redirect_stdout(stdout), redirect_stderr(stderr):
                code = rr.main(["--dry-run-fixture", str(SNAPSHOT), "--properties-fixture", str(PROPERTIES), "--out", str(out), "--label", "act3-test"])
            self.assertEqual(code, 0, stderr.getvalue())
            body = json.loads(out.read_text(encoding="utf-8"))
        self.assertEqual(body["platform"], "revit")
        self.assertEqual(body["project"], "v12-hexagonal-facade-01")
        self.assertEqual(body["label"], "act3-test")
        self.assertTrue(body["source"]["dryRun"])
        self.assertEqual(len(body["elements"]), 8)
        self.assertNotIn("token", json.dumps(body).lower())
        self.assertIn("Facade_Module_Hex", stdout.getvalue())

    def test_live_read_through_injected_client(self):
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp) / "upload.json"
            with redirect_stdout(io.StringIO()), redirect_stderr(io.StringIO()):
                code = rr.main(["--out", str(out)], client=rr.RevitReadClient(opener=StubOpener(_routes())))
            self.assertEqual(code, 0)
            body = json.loads(out.read_text(encoding="utf-8"))
        self.assertNotIn("dryRun", body["source"])
        self.assertEqual(body["source"]["creationGuid"], "0f0e0d0c-1111-2222-3333-444455556666")


if __name__ == "__main__":
    unittest.main()
