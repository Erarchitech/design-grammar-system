"""Offline production GH bytes -> authenticated publish -> persist -> view -> C#.

The source-linked harness replaces only null Rhino geometry. External services are
faked at their I/O seams; neither store_validation_run nor evidence persistence,
request admission, auth, envelope creation, view projection or C# reader is mocked.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
import socket
import subprocess
import threading

from fastapi.testclient import TestClient
import jsonschema
import pytest

import app
import evidence_contract
from speckle_validation import SpeckleConnectionSettings

ROOT = Path(__file__).resolve().parents[2]
HARNESS = ROOT / "DG/tests/DG.PublishWireHarness/DG.PublishWireHarness.csproj"
client = TestClient(app.app)  # conftest supplies a real temporary admin session + CSRF


@pytest.fixture(scope="session")
def wire_harness():
    # Restore existing declared dependencies from the local cache only; never
    # consult a package feed from this offline tracer.
    subprocess.run(
        ["dotnet", "restore", str(HARNESS), "--source", str(HARNESS.parent),
         "-p:NuGetAudit=false", "-v", "quiet"],
        cwd=ROOT, check=True, capture_output=True, timeout=120,
    )
    subprocess.run(
        ["dotnet", "build", str(HARNESS), "--no-restore", "-v", "quiet"],
        cwd=ROOT, check=True, capture_output=True, timeout=120,
    )
    dll = HARNESS.parent / "bin/Debug/net9.0/DG.PublishWireHarness.dll"

    def invoke(*args, input_bytes=None):
        return subprocess.run(
            ["dotnet", str(dll), *args], input=input_bytes, cwd=ROOT,
            check=True, capture_output=True, timeout=30,
        ).stdout

    return invoke


@pytest.fixture(autouse=True)
def refuse_network(monkeypatch):
    def blocked(*args, **kwargs):
        raise AssertionError("Outbound network is forbidden in the wire tracer")

    # Windows implements socketpair with a loopback self-pipe for asyncio.
    # Permit only that synchronous stdlib operation, not arbitrary localhost I/O.
    local = threading.local()
    real_pair, real_connect = socket.socketpair, socket.socket.connect

    def self_pipe(*args, **kwargs):
        local.self_pipe = True
        try:
            return real_pair(*args, **kwargs)
        finally:
            local.self_pipe = False

    def connect(sock, address):
        if getattr(local, "self_pipe", False):
            return real_connect(sock, address)
        return blocked()

    # TestClient's ASGI transport needs no socket connections. Catch HTTP, Bolt,
    # and DNS fallthrough rather than merely trusting every mock was installed.
    monkeypatch.setattr(socket, "socketpair", self_pipe)
    monkeypatch.setattr(socket.socket, "connect", connect)
    monkeypatch.setattr(socket.socket, "connect_ex", blocked)
    monkeypatch.setattr(socket, "create_connection", blocked)
    monkeypatch.setattr(socket, "getaddrinfo", blocked)


class CapturedGraph:
    """Bounded external-I/O double, not a Cypher engine or persistence substitute."""

    def __init__(self):
        self.runs = {}
        self.entities = {}
        self.evidence_writes = []
        self.evidence_reads = []
        self.all_writes = []
        self.speckle_payloads = []
        self.drop_evidence = False
        self.config = {"speckleProjectId": "sp-wire", "baseModelId": "bm-wire",
                       "validationModelId": "vm-wire", "baseModelName": "wire"}

    @staticmethod
    def key(params):
        assert params["graph"] == app.VALIDATION_GRAPH
        assert params["project"] == "P_WIRE"
        return params["graph"], params["project"], params["runId"]

    def write(self, query, parameters=None):
        p = parameters or {}
        self.all_writes.append((query, p))
        assert "graph:$graph" in query and "project:$project" in query
        if "cfg:IntegrationConfig" in query:
            self.config = {k: p[k] for k in self.config}
            return
        key = self.key(p)
        assert "runId:$runId" in query
        if "SET run.evidenceEnvelopeJson = $evidenceEnvelopeJson" in query:
            self.evidence_writes.append((key, p["evidenceEnvelopeJson"]))
            if not self.drop_evidence:
                self.runs[key]["evidenceEnvelopeJson"] = p["evidenceEnvelopeJson"]
        elif "run.rulesJson = $rulesJson" in query:
            self.runs[key] = dict(p)
        elif "UNWIND $entities AS entity" in query:
            self.entities[key] = p["entities"]
        elif "run.shaclReportJson = $shaclReportJson" in query:
            self.runs[key]["shaclReportJson"] = p["shaclReportJson"]
        else:
            raise AssertionError("Unexpected write query in wire tracer")

    def read_single(self, query, parameters=None):
        p = parameters or {}
        if "cfg:IntegrationConfig" in query:
            assert p == {"graph": app.VALIDATION_GRAPH, "project": "P_WIRE"}
            return dict(self.config)
        assert "run.evidenceEnvelopeJson AS evidenceEnvelopeJson" in query
        key = self.key(p)
        run = self.runs.get(key)
        if run is not None:
            self.evidence_reads.append((key, run.get("evidenceEnvelopeJson")))
            return dict(run)
        return None

    def read_many(self, query, parameters=None):
        assert "ve:ValidationEntity" in query
        return self.entities.get(self.key(parameters), [])


@pytest.fixture
def captured_graph(monkeypatch):
    graph = CapturedGraph()
    monkeypatch.setattr(app, "write_query", graph.write)
    # The actual app names its read I/O seams read_single/read_many, not read_query.
    monkeypatch.setattr(app, "read_single", graph.read_single)
    monkeypatch.setattr(app, "read_many", graph.read_many)
    settings = SpeckleConnectionSettings(
        base_url="http://speckle.invalid", internal_url="http://speckle.invalid",
        write_token="wire-test-only", read_token="", dg_base_url="http://dg.invalid",
    )
    monkeypatch.setattr(app, "get_speckle_settings", lambda: settings)
    monkeypatch.setattr(app, "build_client", lambda *a: object())
    monkeypatch.setattr(app, "get_or_create_validation_model_id", lambda *a: "vm-wire")
    monkeypatch.setattr(app, "get_latest_model_version_id", lambda *a: "bv-wire")
    def capture_speckle(*args, **kwargs):
        graph.speckle_payloads.append(kwargs)
        return {
            "baseVersionId": "bv-wire", "validationModelId": "vm-wire",
            "validationVersionId": "vv-wire", "modelViewerUrl": "http://dg.invalid/view",
            "baseResourceUrl": "http://speckle.invalid/base",
            "validationResourceUrl": "http://speckle.invalid/validation",
        }
    monkeypatch.setattr(app, "publish_validation_version", capture_speckle)
    monkeypatch.setattr(app, "_call_shacl_validate", lambda *a: {"status": "unavailable"})
    return graph


def roundtrip(wire_harness, captured_graph, scenario, *, request_bytes=None):
    if request_bytes is None:
        request_bytes = wire_harness("emit", scenario)
    admitted = app.ValidationPublishRequest.model_validate(json.loads(request_bytes))
    assert admitted.project == "P_WIRE"
    response = client.post("/validation/publish", content=request_bytes,
                           headers={"Content-Type": "application/json"})
    assert response.status_code == 200, response.text
    key = app.VALIDATION_GRAPH, admitted.project, response.json()["runId"]
    assert key in captured_graph.runs, "Actual store_validation_run write was omitted"
    writes = [raw for identity, raw in captured_graph.evidence_writes if identity == key]
    assert len(writes) == 1, "Actual persist_evidence_envelope write was omitted"
    raw = writes[0]
    assert captured_graph.runs[key].get("evidenceEnvelopeJson") == raw, "Evidence was not stored"
    envelope = json.loads(raw)
    jsonschema.validate(envelope, evidence_contract.load_contract_schema())
    view = client.get(f"/validation/view/{admitted.project}/{key[2]}")
    assert view.status_code == 200, view.text
    assert captured_graph.evidence_reads == [(key, raw)]
    assert view.json()["evidenceEnvelope"] == envelope
    persisted_bytes = raw.encode("utf-8")
    read = json.loads(wire_harness("read", input_bytes=persisted_bytes))
    assert read["inputSha256"] == hashlib.sha256(persisted_bytes).hexdigest()
    assert read["envelopePresent"] is True
    assert read["collisions"] == []
    assert all(not v["duplicate"] for v in read["verdicts"])
    return envelope, read


def test_zero_rows_preserves_separate_rule_outcomes(wire_harness, captured_graph):
    request = json.loads(wire_harness("emit", "zero_rows"))
    assert request.get("evidenceContractVersion") == "2.0.0"
    assert request["entities"] == []
    envelope, read = roundtrip(wire_harness, captured_graph, "zero_rows")
    assert envelope["contractVersion"] == "2.0.0"
    assert envelope["rows"] == []
    assert {r["ruleId"]: r["canonicalStatus"] for r in envelope["ruleResults"]} == {
        "R_WIRE": "no_population", "R_EMPTY_B": "no_population", "R_MISSING": "not_evaluated",
    }
    assert envelope["canonicalStatus"] == "not_evaluated"
    assert read["verdicts"] == []


@pytest.mark.parametrize("scenario", ["unsupported", "diagnostics"])
def test_diagnostics_core_wire_persist_view(wire_harness, captured_graph, scenario):
    core = json.loads(wire_harness("core", scenario))
    request = json.loads(wire_harness("emit", scenario))
    # Genuine evaluator Message / BindingResult.Detail and builder warnings,
    # not handwritten diagnostic payloads or a substituted producer mapper.
    rules = {r["RuleId"]: r for r in core["RuleResults"]}
    entities = {e["DgEntityId"]: e for e in core["Entities"]}
    assert all(r["Detail"] for r in rules.values())
    for result in request["ruleResults"]:
        original = rules[result["ruleId"]]
        assert result.get("detail") == original["Detail"]
        assert result["warnings"] == original["Warnings"]
    for entity in request["entities"]:
        original = entities[entity["dgEntityId"]]
        assert entity["canonicalDetails"] == original["CanonicalDetails"]
        assert entity["canonicalWarnings"] == original["CanonicalWarnings"]
        assert all(original["CanonicalDetails"].values())
    if scenario == "diagnostics":
        assert rules["R_LEGACY"]["Warnings"] == ["typed_binding_outcome_unavailable"]
        assert entities["OBJ_DIAG"]["CanonicalWarnings"]["R_LEGACY"] == rules["R_LEGACY"]["Warnings"]
    envelope, read = roundtrip(wire_harness, captured_graph, scenario)
    for result in envelope["ruleResults"]:
        original = rules[result["ruleId"]]
        assert result["detail"] == original["Detail"]
        assert result["warnings"] == original["Warnings"]
    for row in envelope["rows"]:
        original = entities[row["objectId"]]
        assert row["detail"] == original["CanonicalDetails"][row["ruleId"]]
        assert row["warnings"] == original["CanonicalWarnings"][row["ruleId"]]
    assert {v["status"] for v in read["verdicts"]} == {
        "unsupported" if scenario == "unsupported" else "unknown"
    }


def test_supported_tracer(wire_harness, captured_graph):
    envelope, read = roundtrip(wire_harness, captured_graph, "supported")
    assert {(r["ruleId"], r["objectId"]): r["canonicalStatus"] for r in envelope["rows"]} == {
        ("R_WIRE", "OBJ_PASS"): "passed", ("R_WIRE", "OBJ_FAIL"): "failed",
    }
    assert {v["objectId"]: v["status"] for v in read["verdicts"]} == {
        "OBJ_PASS": "passed", "OBJ_FAIL": "failed",
    }


def test_supported_tracer_detects_lost_persistence_despite_http_200(wire_harness, captured_graph):
    captured_graph.drop_evidence = True
    with pytest.raises(AssertionError, match="Evidence was not stored"):
        roundtrip(wire_harness, captured_graph, "supported")


@pytest.mark.dg_principal("none")
def test_supported_tracer_rejects_unauthenticated_publish(wire_harness, captured_graph):
    response = client.post("/validation/publish", content=wire_harness("emit", "supported"),
                           headers={"Content-Type": "application/json"})
    assert response.status_code == 401
    assert captured_graph.runs == {}
    assert captured_graph.evidence_writes == []
    assert captured_graph.all_writes == []


def test_supported_tracer_network_guard_blocks_localhost_too():
    with socket.socket() as sock:
        with pytest.raises(AssertionError, match="Outbound network is forbidden"):
            sock.connect(("127.0.0.1", 1))


def test_unsupported_survives_production_wire(wire_harness, captured_graph):
    # Original plan01 Unsupported -> passed RED, retained after plan02's fix.
    envelope, read = roundtrip(wire_harness, captured_graph, "unsupported")
    assert len(envelope["rows"]) == 1
    row = envelope["rows"][0]
    assert (row["ruleId"], row["objectId"]) == ("R_WIRE", "OBJ_UNSUPPORTED")
    actual = row["canonicalStatus"]
    assert {v["objectId"]: v["status"] for v in read["verdicts"]} == {
        "OBJ_UNSUPPORTED": actual,
    }
    assert actual == "unsupported", f"Production-wire regression: expected unsupported, got {actual}"
    assert {v["objectId"]: v["status"] for v in read["verdicts"]} == {
        "OBJ_UNSUPPORTED": "unsupported",
    }


@pytest.mark.parametrize("scenario,rule_status,objects", [
    ("mixed_shortcircuit", "unsupported", {"OBJ_PASS": "passed", "OBJ_FAIL": "unsupported"}),
    ("unknown", "unknown", {"OBJ_UNKNOWN": "unknown"}),
    ("error", "error", {"OBJ_ERROR": "error"}),
    ("missing_result", "not_evaluated", {"OBJ_MISSING": "not_evaluated"}),
    ("legacy_only", "unknown", {"OBJ_LEGACY": "unknown"}),
    ("empty_typed", "unknown", {"OBJ_LEGACY": "unknown"}),
    ("missing_association", "unknown", {"OBJ_PASS": "passed", "OBJ_FAIL": "unknown"}),
    ("no_refs", "failed", {}),
    ("repeated_refs", "failed", {"OBJ_SHARED": "failed", "OBJ_A": "passed", "OBJ_B": "passed"}),
    ("contract_injected_indeterminate", "indeterminate", {"OBJ_INJECTED": "indeterminate"}),
])
def test_outcome_matrix(wire_harness, captured_graph, scenario, rule_status, objects):
    envelope, read = roundtrip(wire_harness, captured_graph, scenario)
    assert {r["ruleId"]: r["canonicalStatus"] for r in envelope["ruleResults"]} == {"R_WIRE": rule_status}
    assert {r["objectId"]: r["canonicalStatus"] for r in envelope["rows"]} == objects
    assert len(envelope["rows"]) == len(objects)
    assert {v["objectId"]: v["status"] for v in read["verdicts"]} == objects
    if scenario in {"legacy_only", "empty_typed", "missing_association"}:
        assert "typed_binding_outcome_unavailable" in envelope["ruleResults"][0]["warnings"]
        for row in envelope["rows"]:
            if row["canonicalStatus"] == "unknown":
                assert row["warnings"] == ["typed_binding_outcome_unavailable"]
                assert row["detail"]


def test_zero_rows_mixed_with_real_objects(wire_harness, captured_graph):
    envelope, read = roundtrip(wire_harness, captured_graph, "mixed_zero_rows")
    assert {r["ruleId"]: r["canonicalStatus"] for r in envelope["ruleResults"]} == {
        "R_WIRE": "failed", "R_EMPTY_A": "no_population", "R_EMPTY_B": "no_population",
    }
    assert {(r["ruleId"], r["objectId"]) for r in envelope["rows"]} == {
        ("R_WIRE", "OBJ_PASS"), ("R_WIRE", "OBJ_FAIL"),
    }
    assert {v["objectId"]: v["status"] for v in read["verdicts"]} == {
        "OBJ_PASS": "passed", "OBJ_FAIL": "failed",
    }


# Hand-mutated negative request controls, explicitly NOT producer proof.
@pytest.mark.parametrize("version", [None, True, 2, 2.0, "2", "2.0.0 ", "1", "1.0.0", "3.0.0", {}, []])
def test_invalid_new_mode_version(wire_harness, captured_graph, version):
    payload = json.loads(wire_harness("emit", "supported"))
    payload["evidenceContractVersion"] = version
    response = client.post("/validation/publish", json=payload)
    assert response.status_code == 422, response.text
    assert captured_graph.all_writes == []


@pytest.mark.parametrize("mutation", [
    "duplicate_rule", "duplicate_result", "duplicate_entity", "duplicate_entity_rule",
    "no_rules", "no_results", "foreign_result", "bool_rule_id",
    "foreign_entity_rule", "absent_map", "null_map", "empty_map", "extra_map_key",
    "missing_rule_status", "invalid_rule_status", "bool_rule_status", "int_rule_status",
    "invalid_pair_status", "bool_pair_status", "int_pair_status", "space_pair_status",
    "missing_warnings", "null_warnings", "invalid_warning", "null_detail", "int_detail",
    "foreign_warning", "foreign_detail", "invalid_pair_warning", "invalid_pair_detail",
])
def test_invalid_new_mode_rejected_without_any_write(wire_harness, captured_graph, mutation):
    payload = json.loads(wire_harness("emit", "supported"))
    result, entity = payload["ruleResults"][0], payload["entities"][0]
    if mutation.startswith("duplicate_"):
        name = {"duplicate_rule": "rules", "duplicate_result": "ruleResults", "duplicate_entity": "entities"}.get(mutation)
        if name:
            payload[name].append(payload[name][0])
        else:
            entity["ruleIds"].append("R_WIRE")
    elif mutation == "no_rules": payload["rules"] = []
    elif mutation == "no_results": payload["ruleResults"] = []
    elif mutation == "foreign_result": result["ruleId"] = "FOREIGN"
    elif mutation == "bool_rule_id": payload["rules"][0]["ruleId"] = True
    elif mutation == "foreign_entity_rule": entity["ruleIds"] = ["FOREIGN"]
    elif mutation == "absent_map": entity.pop("canonicalStatuses")
    elif mutation == "null_map": entity["canonicalStatuses"] = None
    elif mutation == "empty_map": entity["canonicalStatuses"] = {}
    elif mutation == "extra_map_key": entity["canonicalStatuses"]["FOREIGN"] = "passed"
    elif mutation == "missing_rule_status": result.pop("canonicalStatus")
    elif mutation in {"invalid_rule_status", "bool_rule_status", "int_rule_status"}:
        result["canonicalStatus"] = {"invalid_rule_status": "Passed", "bool_rule_status": True, "int_rule_status": 1}[mutation]
    elif mutation in {"invalid_pair_status", "bool_pair_status", "int_pair_status", "space_pair_status"}:
        entity["canonicalStatuses"]["R_WIRE"] = {"invalid_pair_status": "Passed", "bool_pair_status": False,
            "int_pair_status": 0, "space_pair_status": " passed "}[mutation]
    elif mutation == "missing_warnings": result.pop("warnings")
    elif mutation == "null_warnings": result["warnings"] = None
    elif mutation == "invalid_warning": result["warnings"] = [True]
    elif mutation == "null_detail": result["detail"] = None
    elif mutation == "int_detail": result["detail"] = 1
    elif mutation == "foreign_warning": entity["canonicalWarnings"]["FOREIGN"] = []
    elif mutation == "foreign_detail": entity["canonicalDetails"]["FOREIGN"] = "x"
    elif mutation == "invalid_pair_warning": entity["canonicalWarnings"]["R_WIRE"] = [1]
    elif mutation == "invalid_pair_detail": entity["canonicalDetails"]["R_WIRE"] = False
    else: raise AssertionError(mutation)
    response = client.post("/validation/publish", json=payload)
    assert response.status_code == 422, response.text
    assert captured_graph.all_writes == []


@pytest.mark.dg_principal("none")
def test_invalid_new_mode_foreign_project_real_auth_no_write(wire_harness, captured_graph):
    import auth_fixtures
    username = "wire-foreign@dg.local"
    auth_fixtures.make_user(username, memberships={"P_FOREIGN": "owner"})
    undo = auth_fixtures.authorize_client(client, ("user", username))
    try:
        response = client.post("/validation/publish", content=wire_harness("emit", "supported"),
                               headers={"Content-Type": "application/json"})
        assert response.status_code == 403, response.text
        assert captured_graph.all_writes == []
    finally:
        undo()


@pytest.mark.parametrize("map_kind", ["absent", "null", "invalid"])
def test_legacy_absent_version_fallback_unchanged(wire_harness, captured_graph, map_kind):
    payload = json.loads(wire_harness("emit", "supported"))
    payload.pop("evidenceContractVersion")
    for result in payload["ruleResults"]:
        for name in ("canonicalStatus", "warnings", "detail"): result.pop(name, None)
    for entity in payload["entities"]:
        entity.pop("canonicalWarnings")
        entity.pop("canonicalDetails")
        if map_kind == "absent": entity.pop("canonicalStatuses")
        elif map_kind == "null": entity["canonicalStatuses"] = None
        else: entity["canonicalStatuses"] = {"R_WIRE": "not-a-status"}
    envelope, read = roundtrip(wire_harness, captured_graph, "legacy-control",
                               request_bytes=json.dumps(payload).encode())
    assert envelope["contractVersion"] == "1.0.0"
    assert "ruleResults" not in envelope
    assert {v["objectId"]: v["status"] for v in read["verdicts"]} == {"OBJ_PASS": "passed", "OBJ_FAIL": "failed"}
    assert app.build_rules_summary(app.ValidationPublishRequest.model_validate(payload)) == [
        {"ruleId": "R_WIRE", "ruleName": "", "ruleDescription": "", "passed": False}
    ]


@pytest.mark.parametrize("scenario", ["supported", "unsupported", "diagnostics", "legacy_only", "error"])
def test_legacy_fields_preserved_independently(wire_harness, captured_graph, scenario):
    core = json.loads(wire_harness("core", scenario))
    payload = json.loads(wire_harness("emit", scenario))
    for source, wire in zip(core["RuleResults"], payload["ruleResults"], strict=True):
        assert {k: wire[k] for k in ("ruleId", "passed", "failedEntityIds", "passedEntityIds")} == {
            "ruleId": source["RuleId"], "passed": source["Passed"],
            "failedEntityIds": source["FailedEntityIds"], "passedEntityIds": source["PassedEntityIds"],
        }
    for source, wire in zip(core["Entities"], payload["entities"], strict=True):
        for key in ("DgEntityId", "DisplayName", "Geometry", "RuleIds", "FailedRuleIds", "PassedRuleIds", "OverallStatus"):
            assert wire[key[0].lower() + key[1:]] == source[key]
    assert payload["validStatus"] == [True, False, True]
    roundtrip(wire_harness, captured_graph, scenario)
    run = next(iter(captured_graph.runs.values()))
    assert run["validStatus"] == [True, False, True]
    summaries = json.loads(run["rulesJson"])
    assert [s["passed"] for s in summaries] == [s["passed"] for s in payload["ruleResults"]]
    for stored, wire in zip(captured_graph.speckle_payloads[0]["entities"], payload["entities"], strict=True):
        for key in ("ruleIds", "failedRuleIds", "passedRuleIds", "overallStatus"):
            assert stored[key] == wire[key]
    expected_legacy_rows = {
        (entity["dgEntityId"], rule_id): status
        for entity in payload["entities"]
        for field, status in (("passedRuleIds", "passed"), ("failedRuleIds", "failed"))
        for rule_id in entity[field]
    }
    assert {(row["dgEntityId"], row["ruleId"]): row["status"]
            for row in next(iter(captured_graph.entities.values()))} == expected_legacy_rows
    # Fixed pre-canonical legacy behavior: old pair lists say passed despite
    # the rule's false boolean. Do not replace them with canonical-to-bool.
    if scenario in {"unsupported", "diagnostics"}:
        assert payload["ruleResults"][0]["passed"] is False
        assert payload["entities"][0]["failedRuleIds"] == []
        assert "R_WIRE" in payload["entities"][0]["passedRuleIds"]
        assert payload["entities"][0]["overallStatus"] == "passed"


def test_invalid_new_mode_swallowed_sidecar_exception_is_detected(wire_harness, captured_graph, monkeypatch):
    original = captured_graph.write
    def fail_external_evidence_write(query, parameters=None):
        if "SET run.evidenceEnvelopeJson" in query:
            raise OSError("test-only external evidence persistence failure")
        return original(query, parameters)
    monkeypatch.setattr(app, "write_query", fail_external_evidence_write)
    with pytest.raises(AssertionError, match="Actual persist_evidence_envelope write was omitted"):
        roundtrip(wire_harness, captured_graph, "supported")


def test_new_mode_canonical_wins_contradictory_legacy_lists(wire_harness, captured_graph):
    # Explicit hand-mutated precedence control, not evaluator outcome evidence.
    payload = json.loads(wire_harness("emit", "supported"))
    for entity in payload["entities"]:
        entity["failedRuleIds"] = ["R_WIRE", "LEGACY_ONLY"]
        entity["passedRuleIds"] = ["R_WIRE", "LEGACY_ONLY"]
        entity["overallStatus"] = "failed"
    envelope, read = roundtrip(wire_harness, captured_graph, "precedence-control",
                               request_bytes=json.dumps(payload).encode())
    assert {(r["ruleId"], r["objectId"]): r["canonicalStatus"] for r in envelope["rows"]} == {
        ("R_WIRE", "OBJ_PASS"): "passed", ("R_WIRE", "OBJ_FAIL"): "failed",
    }
    assert {v["objectId"]: v["status"] for v in read["verdicts"]} == {"OBJ_PASS": "passed", "OBJ_FAIL": "failed"}


def test_legacy_version_absence_is_not_sniffed_from_new_fields(wire_harness, captured_graph):
    payload = json.loads(wire_harness("emit", "supported"))
    payload.pop("evidenceContractVersion")
    envelope, _ = roundtrip(wire_harness, captured_graph, "absent-version-control",
                            request_bytes=json.dumps(payload).encode())
    assert envelope["contractVersion"] == "1.0.0"
    assert "ruleResults" not in envelope
