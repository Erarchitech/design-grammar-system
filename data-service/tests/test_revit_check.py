"""F-01 (2026-10-29): rule checks of a Revit model without Grasshopper. The server queues a job for the caller's own
DG Revit connector (never calls a PC), the connector answers the computed values, dg-evaluator judges them, every rule
is published and the connector is asked to paint; DeGram keeps reading finished/status/summary."""

from __future__ import annotations

import os
import sys
import threading
import types

import pytest
from fastapi import HTTPException

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import app as app_module  # noqa: E402
import connector_jobs  # noqa: E402
import revit_check  # noqa: E402

PROJECT = "str-openings-01"
PROPS = [{"key": "P1", "ruleId": "R_BEAM", "dataPropertyIri": "dg:hasBeamIntersectionCount"},
         {"key": "P2", "ruleId": "R_CLEAR", "dataPropertyIri": "dg:hasMinOpeningClearanceMm"}]
MESH = {"units": "mm", "items": [{"kind": "mesh", "vertices": [0, 0, 0, 1, 0, 0, 0, 1, 0], "faces": [[0, 1, 2]]}]}
RESULT = {
    "document": "DG-DemoProject-2-openings_R26",
    "properties": PROPS,
    "boxes": [{"uniqueId": "u1", "label": "Box : 300 [1]", "values": [1, 250.5], "mesh": MESH},
              {"uniqueId": "u2", "label": "Box : 300 [2]", "values": [0, None], "mesh": None},
              {"uniqueId": "u3", "label": "Box : 300 [3]", "values": [True, "x"], "mesh": MESH}],
    "report": ["document: DG-DemoProject-2-openings_R26", "boxes: 3"],
}
EVALUATED = {
    "stateId": "DS_1",
    "runs": [
        {"ruleId": "R_BEAM", "ruleName": "Beams", "status": "failed", "report": "violated by 1",
         "validStatusNames": ["failed", "passed", "unknown"],
         "publish": {"project": PROJECT, "rules": [{"ruleId": "R_BEAM"}],
                     "entities": [{"dgEntityId": "u1"}, {"dgEntityId": "u2"}, {"dgEntityId": "u3"}]}},
        {"ruleId": "R_CLEAR", "ruleName": "Clearance", "status": "failed", "report": "violated by 1",
         "validStatusNames": ["failed", "unknown", ""],
         "publish": {"project": PROJECT, "rules": [{"ruleId": "R_CLEAR"}], "entities": [{"dgEntityId": "u1"}]}},
    ],
    "missingRules": [],
}


@pytest.fixture(autouse=True)
def _clean():
    connector_jobs.reset()
    yield
    connector_jobs.reset()


def _http_request(user):
    return types.SimpleNamespace(state=types.SimpleNamespace(
        principal=types.SimpleNamespace(username=user, connector_id="revit")))


# --- the queue -----------------------------------------------------------------

def test_a_job_reaches_only_the_connector_of_the_user_who_asked():
    job = connector_jobs.submit(PROJECT, "engineer", "check", {"script": "x"})
    assert connector_jobs.take(PROJECT, "lead") is None
    assert connector_jobs.take("other-project", "engineer") is None
    taken = connector_jobs.take(PROJECT, "engineer")
    assert taken is job and taken["status"] == connector_jobs.TAKEN
    assert connector_jobs.get(job["id"], PROJECT, "lead") is None
    assert connector_jobs.get(job["id"], PROJECT, "engineer") is job


def test_polling_makes_the_connector_present_for_a_while(monkeypatch):
    clock = [100.0]
    monkeypatch.setattr(connector_jobs, "_now", lambda: clock[0])
    assert not connector_jobs.active(PROJECT, "engineer")
    connector_jobs.take(PROJECT, "engineer")
    assert connector_jobs.active(PROJECT, "engineer")
    clock[0] += connector_jobs.ACTIVE_S + 1
    assert not connector_jobs.active(PROJECT, "engineer")


def test_a_newer_request_replaces_a_queued_one_of_the_same_kind():
    first = connector_jobs.submit(PROJECT, "engineer", "paint", {"n": 1})
    second = connector_jobs.submit(PROJECT, "engineer", "paint", {"n": 2})
    assert first["status"] == connector_jobs.EXPIRED
    assert connector_jobs.take(PROJECT, "engineer") is second


def test_wait_returns_when_the_connector_answers():
    job = connector_jobs.submit(PROJECT, "engineer", "check", {})
    threading.Timer(0.05, lambda: connector_jobs.complete(job, True, {"boxes": []})).start()
    assert connector_jobs.wait(job, 5.0)
    assert job["status"] == connector_jobs.DONE


# --- pure steps ----------------------------------------------------------------

def test_the_evaluator_gets_every_box_and_only_numeric_values():
    body = revit_check.evaluator_request(PROJECT, {"iri": "dg:OpeningBox", "label": "OpeningBox"}, RESULT, "doc")
    assert body["classIri"] == "dg:OpeningBox" and body["ruleIds"] == ["R_BEAM", "R_CLEAR"]
    assert [o["ref"] for o in body["objects"]] == ["u1", "u2", "u3"]
    assert body["values"] == [
        {"ruleId": "R_BEAM", "dataPropertyIri": "dg:hasBeamIntersectionCount", "ref": "u1", "value": 1},
        {"ruleId": "R_CLEAR", "dataPropertyIri": "dg:hasMinOpeningClearanceMm", "ref": "u1", "value": 250.5},
        {"ruleId": "R_BEAM", "dataPropertyIri": "dg:hasBeamIntersectionCount", "ref": "u2", "value": 0},
    ]


def test_box_meshes_land_on_their_entities_without_touching_the_evaluator_answer():
    body = revit_check.with_geometry(EVALUATED["runs"][0]["publish"], RESULT)
    by_id = {e["dgEntityId"]: e for e in body["entities"]}
    assert by_id["u1"]["geometry"] == MESH and "geometry" not in by_id["u2"]
    assert "geometry" not in EVALUATED["runs"][0]["publish"]["entities"][0]


def test_a_box_without_data_is_no_verdict_never_a_violation():
    by_ref = revit_check.verdicts(EVALUATED, RESULT)
    assert by_ref == {"u1": {"broken": ["R_BEAM", "R_CLEAR"], "open": []},
                      "u2": {"broken": [], "open": ["R_CLEAR"]},
                      "u3": {"broken": [], "open": ["R_BEAM"]}}
    status = revit_check.check_status(RESULT, EVALUATED, ["run-1"], by_ref, [])
    assert status["boxes"] == 3 and status["violations"] == ["Box : 300 [1]: R_BEAM, R_CLEAR"]
    assert status["validationRunId"] == ["run-1"] and status["platform"] == "Revit"


# --- the route ----------------------------------------------------------------

def _generated():
    return {"boxClass": {"iri": "dg:OpeningBox", "label": "OpeningBox"}, "resolved": [], "unsupported": [],
            "revit": {"source": "def run(doc, family_filter, with_context):\n    return {}\n", "sha256": "abc",
                      "properties": PROPS}}


def _connector(answer, seen):
    """A connector thread: polls once the check is queued, answers it, then takes the paint job."""
    def work():
        for _ in range(200):
            job = connector_jobs.take(PROJECT, "engineer")
            if job is not None:
                seen.append(job["kind"])
                if job["kind"] == "check":
                    connector_jobs.complete(job, *answer)
                    return
            threading.Event().wait(0.01)
    thread = threading.Thread(target=work, daemon=True)
    thread.start()
    return thread


@pytest.fixture
def stubs(monkeypatch):
    published = []
    monkeypatch.setattr(app_module, "_generate_property_scripts", lambda *a, **k: _generated())
    monkeypatch.setattr(app_module, "_evaluate_check", lambda body: EVALUATED)
    monkeypatch.setattr(app_module, "publish_validation",
                        lambda payload: published.append(payload) or {"runId": "run-" + payload.rules[0].ruleId})
    monkeypatch.setattr(app_module, "_record_check_source", lambda *a: None)
    monkeypatch.setattr(app_module, "_publish_revit_context", lambda *a: None)
    return published


def test_the_check_runs_in_the_callers_revit_and_answers_degram_s_contract(stubs):
    connector_jobs.touch(PROJECT, "engineer")
    seen = []
    thread = _connector((True, RESULT), seen)
    out = app_module.post_property_check_run(app_module.PropertyCheckRunRequest(project=PROJECT),
                                             _http_request("engineer"))
    thread.join(2)
    assert seen == ["check"]
    assert out["finished"] is True and out["summary"]["ok"] is True
    assert sorted(out["summary"]["validationRunIds"]) == ["run-R_BEAM", "run-R_CLEAR"]
    assert out["status"]["boxes"] == 3 and out["status"]["violations"] == ["Box : 300 [1]: R_BEAM, R_CLEAR"]
    assert {p.rules[0].ruleId for p in stubs} == {"R_BEAM", "R_CLEAR"}
    beam = next(p for p in stubs if p.rules[0].ruleId == "R_BEAM")
    assert next(e for e in beam.entities if e.dgEntityId == "u1").geometry is not None
    paint = connector_jobs.take(PROJECT, "engineer")
    assert paint["kind"] == "paint" and paint["payload"]["verdicts"]["u1"]["broken"] == ["R_BEAM", "R_CLEAR"]
    assert connector_jobs.last_status(PROJECT)["boxes"] == 3


def test_a_failure_in_revit_is_an_error_never_a_clean_model(stubs):
    connector_jobs.touch(PROJECT, "engineer")
    thread = _connector((False, None, "no active document"), [])
    with pytest.raises(HTTPException) as err:
        app_module.post_property_check_run(app_module.PropertyCheckRunRequest(project=PROJECT),
                                           _http_request("engineer"))
    thread.join(2)
    assert err.value.detail["code"] == "REVIT_CHECK_FAILED" and "no active document" in err.value.detail["error"]


def test_no_boxes_in_revit_is_reported_as_a_problem(stubs, monkeypatch):
    monkeypatch.setattr(app_module, "_evaluate_check", lambda body: {"runs": [], "missingRules": []})
    connector_jobs.touch(PROJECT, "engineer")
    thread = _connector((True, dict(RESULT, boxes=[])), [])
    with pytest.raises(HTTPException) as err:
        app_module.post_property_check_run(app_module.PropertyCheckRunRequest(project=PROJECT),
                                           _http_request("engineer"))
    thread.join(2)
    assert err.value.status_code == 422 and err.value.detail["code"] == "PROPERTY_CHECK_FAILED"


def test_on_the_server_without_a_signed_in_revit_the_check_says_so(monkeypatch):
    monkeypatch.setattr(app_module, "_DOCS_PROFILE", "multi-user")
    with pytest.raises(HTTPException) as err:
        app_module.post_property_check_run(app_module.PropertyCheckRunRequest(project=PROJECT),
                                           _http_request("engineer"))
    assert err.value.status_code == 409 and err.value.detail["code"] == "REVIT_NOT_CONNECTED"


def test_another_users_connector_does_not_make_the_check_run_in_revit(monkeypatch):
    connector_jobs.touch(PROJECT, "engineer")
    assert app_module._revit_check_target(PROJECT, _http_request("lead")) is False
    assert app_module._revit_check_target(PROJECT, _http_request("engineer")) is True


def test_the_connector_routes_refuse_a_foreign_job():
    job = connector_jobs.submit(PROJECT, "engineer", "check", {})
    with pytest.raises(HTTPException) as err:
        app_module.post_connector_job_result(job["id"], app_module.ConnectorJobResult(project=PROJECT),
                                             _http_request("lead"))
    assert err.value.status_code == 404
    answer = app_module.post_connector_job_result(job["id"], app_module.ConnectorJobResult(
        project=PROJECT, result={"boxes": []}), _http_request("engineer"))
    assert answer["status"] == connector_jobs.DONE
    nxt = app_module.get_connector_job_next(_http_request("engineer"), project=PROJECT)
    assert nxt == {"job": None}


def test_parallel_first_publishes_share_the_validation_model_one_of_them_created():
    """Live 2026-10-29 (stand, fresh Speckle project): the six rules publish in parallel, each listed no dg-validation
    model and created it; Speckle refused all but one ("A branch with this name already exists") and the check failed
    with PUBLISH_INTERNAL_ERROR."""
    import speckle_validation

    created = []

    class Models:
        def get_models(self, project_id):
            return types.SimpleNamespace(items=[types.SimpleNamespace(id=m, name="dg-validation") for m in created])

        def create(self, model_input):
            if created:
                raise RuntimeError("A branch with this name already exists")
            created.append("vm-1")
            return types.SimpleNamespace(id="vm-1")

    client = types.SimpleNamespace(model=Models())
    barrier = threading.Barrier(4)
    results, errors = [], []
    original = Models.get_models
    seen = threading.local()

    def listed_by_all(self, project_id):  # every thread lists once before any creates, as on the stand
        answer = original(self, project_id)
        if not getattr(seen, "listed", False):
            seen.listed = True
            barrier.wait(timeout=5)
        return answer

    Models.get_models = listed_by_all

    def publish():
        try:
            results.append(speckle_validation.get_or_create_validation_model_id(client, "sp", None))
        except Exception as exc:  # noqa: BLE001 - collected for the assertion
            errors.append(exc)

    threads = [threading.Thread(target=publish) for _ in range(4)]
    for t in threads:
        t.start()
    for t in threads:
        t.join(timeout=10)
    assert errors == [] and results == ["vm-1"] * 4


def test_a_failed_validation_model_create_still_raises_when_no_model_appeared():
    import speckle_validation

    class Models:
        def get_models(self, project_id):
            return types.SimpleNamespace(items=[])

        def create(self, model_input):
            raise RuntimeError("no permission")

    with pytest.raises(RuntimeError, match="no permission"):
        speckle_validation.get_or_create_validation_model_id(types.SimpleNamespace(model=Models()), "sp", None)
