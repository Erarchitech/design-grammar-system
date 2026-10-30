"""Phase 1303-26 (D-79..D-81): the model snapshot of a confirmed Revit mapping, offline with fakes."""

from __future__ import annotations

import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import model_snapshots as ms  # noqa: E402

PROJECT = "str-openings-01"
MESH = {"units": "mm", "items": [{"kind": "mesh", "vertices": [0, 0, 0, 1000.4, 2000, 3000], "faces": [[0, 1, 0]]}]}


def _meta(state="written", platform="revit", snapshot=None):
    batch = {"batchId": "b1", "delivery": {"state": state, "written": 2, "skipped": 0}}
    if snapshot:
        batch["snapshot"] = snapshot
    return {
        "platform": platform, "label": "DG-DemoProject-2-openings", "batches": [batch],
        "descriptors": [
            {"nativeId": "u-wall", "category": "Стены", "name": "Wall : 200", "elementId": 11},
            {"nativeId": "u-box", "category": "Обобщенные модели", "name": "Box : 300", "elementId": 12},
            {"nativeId": "u-door", "category": "Двери", "name": "Door", "elementId": 13},
        ],
        "result": {"elements": [
            {"nativeId": "u-wall", "state": "confirmed", "roles": [{"classIri": "ex:Wall", "label": "Wall"}]},
            {"nativeId": "u-box", "state": "auto", "roles": [{"classIri": "ex:OpeningBox", "label": "OpeningBox"},
                                                             {"classIri": "ex:Penetration"}]},
            {"nativeId": "u-door", "state": "unmapped", "roles": []},
        ]},
    }


class Harness:
    def __init__(self, meta, job_status="done", context=True, meshes=("u-wall", "u-box")):
        self.meta, self.marks, self.jobs, self.stored, self.published = meta, [], [], [], []
        self.job_status, self.context, self.meshes = job_status, context, meshes

    def load(self):
        return self.meta

    def mark(self, status):
        self.marks.append(status)

    def submit(self, payload):
        job = {"payload": payload, "status": self.job_status, "error": None if self.job_status == "done" else "boom",
               "result": {"document": "DG-Demo", "fingerprint": "f" * 64, "count": 2, "missing": ["u-door"]},
               "context": [{"uniqueId": u, "mesh": MESH} for u in self.meshes]}
        self.jobs.append(job)
        return job

    def wait(self, job, seconds, until):
        return until == "finished" or self.context

    def publish(self, state_id, document, nodes):
        self.published.append((state_id, document, nodes))
        return {"speckleProjectId": "sp", "speckleModelId": "sm", "speckleVersionId": "sv"}

    def store(self, props):
        self.stored.append(props)
        return props["StateId"]

    def take(self):
        return ms.take(PROJECT, "ms-1", "b1", load_session=self.load, mark=self.mark, submit=self.submit,
                       wait=self.wait, program=lambda: {"source": "def snapshot(): pass", "sha256": "s" * 64},
                       publish=self.publish, store=self.store, now=lambda: "2026-10-30T10:00:00Z")


def test_a_written_revit_batch_becomes_one_snapshot_with_a_speckle_version():
    h = Harness(_meta())
    status = h.take()
    assert status["status"] == "published" and status["stateId"] == ms.state_id(PROJECT, "ms-1", "b1")
    assert status["missing"] == 1 and status["meshes"] == 2
    job = h.jobs[0]["payload"]
    assert job["uniqueIds"] == ["u-wall", "u-box", "u-door"]
    assert job["categories"] == ["Двери", "Обобщенные модели", "Стены"]
    state_id, document, nodes = h.published[0]
    assert document == "DG-Demo" and [n["dgNativeId"] for n in nodes] == ["u-wall", "u-box"]
    box = nodes[1]
    assert box["dgClassIris"] == ["ex:OpeningBox", "ex:Penetration"]
    assert box["dgClassLabels"] == ["OpeningBox", "Penetration"] and box["dgMappingState"] == "auto"
    assert box["dgSnapshotId"] == state_id and box["dgRevitId"] == 12 and box["name"] == "Box : 300 [12]"
    props = h.stored[0]
    assert props["fingerprint"] == "f" * 64 and props["elementCount"] == 3 and props["speckleVersionId"] == "sv"
    envelope = json.loads(props["statePayloadJson"])
    assert envelope["version"] == "2" and envelope["stateId"] == state_id and envelope["propStates"] == []
    assert [o["ref"] for o in envelope["objStates"]] == ["u-wall", "u-box", "u-door"]
    assert envelope["objStates"][0]["bboxMm"] == [0, 0, 0, 1000, 2000, 3000]
    assert envelope["objStates"][2]["bboxMm"] is None
    assert [m["status"] for m in h.marks] == ["pending", "published"]


def test_a_second_acknowledgement_does_not_snapshot_again():
    published = {"status": "published", "stateId": "OS_x"}
    h = Harness(_meta(snapshot=published))
    assert h.take() == published and h.jobs == [] and h.marks == []
    pending = Harness(_meta(snapshot={"status": "pending", "stateId": "OS_x"}))
    assert pending.take()["status"] == "pending" and pending.jobs == []


def test_a_failed_delivery_or_a_grasshopper_session_is_not_snapshotted():
    for meta in (_meta(state="failed"), _meta(platform="grasshopper")):
        h = Harness(meta)
        assert h.take()["status"] == "skipped" and h.jobs == [] and h.marks == []


def test_revit_without_an_answer_marks_the_snapshot_failed_and_publishes_nothing():
    h = Harness(_meta(), job_status="expired")
    status = h.take()
    assert status["status"] == "failed" and "boom" in status["reason"]
    assert h.published == [] and h.stored == [] and h.marks[-1]["status"] == "failed"
    late = Harness(_meta(), context=False)
    assert late.take()["status"] == "failed" and late.published == []


def test_a_speckle_failure_is_recorded_never_raised():
    h = Harness(_meta())

    def publish(*args):
        raise RuntimeError("Speckle is down")

    h.publish = publish
    status = h.take()
    assert status == {"status": "failed", "stateId": ms.state_id(PROJECT, "ms-1", "b1"), "reason": "Speckle is down"}
    assert h.stored == []


def test_state_ids_are_deterministic_per_project_session_and_batch():
    a = ms.state_id(PROJECT, "ms-1", "b1")
    assert a.startswith("OS_") and len(a) == 19 and a == ms.state_id(PROJECT, "ms-1", "b1")
    assert a != ms.state_id(PROJECT, "ms-1", "b2") and a != ms.state_id("other", "ms-1", "b1")


def test_a_check_attaches_only_with_the_fingerprint_of_the_latest_snapshot():
    snap = {"StateId": "OS_1", "fingerprint": "f" * 64}
    assert ms.attach_decision(snap, {"fingerprint": "f" * 64}) == {"attached": True, "stateId": "OS_1"}
    changed = ms.attach_decision(snap, {"fingerprint": "e" * 64})
    assert not changed["attached"] and "changed" in changed["reason"]
    assert not ms.attach_decision(snap, {})["attached"]
    assert ms.attach_decision(None, {"fingerprint": "f" * 64}) == {"attached": False,
                                                                     "reason": "no model snapshot in the project"}


class FakeSession:
    def __init__(self, rows):
        self.rows, self.calls = rows, []

    def run(self, query, params):
        self.calls.append((query, params))
        return self.rows


def test_neo4j_writes_are_project_scoped_and_idempotent():
    s = FakeSession([{"stateId": "OS_1"}])
    assert ms.save(s, PROJECT, {"StateId": "OS_1", "label": "Mapping"}) == "OS_1"
    query, params = s.calls[0]
    assert "MERGE (ds:DesignState {graph:$graph, project:$project, StateId:$stateId})" in query
    assert "ON CREATE SET" in query
    assert params["props"]["source"] == "mapping-snapshot" and params["props"]["kind"] == "ObjState"
    assert params["props"]["project"] == PROJECT

    s = FakeSession([{"attached": 2}])
    assert ms.attach_runs(s, PROJECT, "OS_1", ["r1", "r2"]) == 2
    query, params = s.calls[0]
    assert "MERGE (run)-[:IN_SNAPSHOT]->(ds)" in query and "run.modelSnapshotId" in query
    assert params["project"] == PROJECT and params["runIds"] == ["r1", "r2"]
    assert ms.attach_runs(FakeSession([]), PROJECT, "OS_1", []) == 0


def test_snapshots_are_listed_as_design_state_groups():
    s = FakeSession([{"ds": {"StateId": "OS_1", "label": "Mapping · M", "capturedAtUtc": "2026-10-30T10:00:00Z",
                             "elementCount": 3, "mappingSessionId": "ms-1", "batchId": "b1", "document": "M"}}])
    groups = ms.list_snapshots(s, PROJECT)
    assert groups == [{"stateId": "OS_1", "kind": "snapshot", "label": "Mapping · M",
                       "capturedAtUtc": "2026-10-30T10:00:00Z", "parameterCount": 3, "elementCount": 3,
                       "mappingSessionId": "ms-1", "batchId": "b1", "document": "M"}]


# --- wiring in app.py and mapping_store ------------------------------------------------------------------------------

def _request(kind="connector"):
    from types import SimpleNamespace
    principal = SimpleNamespace(kind=kind, username="engineer", connector_id="revit")
    return SimpleNamespace(state=SimpleNamespace(principal=principal))


def _ack(monkeypatch, delivery_state):
    import app as app_module

    scheduled = []
    monkeypatch.setattr(app_module, "_mapping_call",
                        lambda fn, *args: {"batchId": "mb-1", "delivery": {"state": delivery_state}})
    monkeypatch.setattr(app_module, "_schedule_model_snapshot", lambda *args: scheduled.append(args))
    payload = app_module.MappingApplyRequest(project=PROJECT, batchId="mb-1",
                                             delivery={"state": delivery_state, "written": 1, "skipped": 0}
                                             if delivery_state == "written" else
                                             {"state": delivery_state, "written": 0, "skipped": 1})
    app_module.post_mapping_apply("ms-1", payload, _request())
    return scheduled


def test_a_written_receipt_schedules_the_snapshot_for_the_connector_that_wrote_it(monkeypatch):
    assert _ack(monkeypatch, "written") == [(PROJECT, "ms-1", "mb-1", "engineer", "revit")]


def test_a_failed_receipt_schedules_nothing(monkeypatch):
    assert _ack(monkeypatch, "failed") == []


def test_the_snapshot_status_is_kept_on_the_batch_and_does_not_change_the_session_revision(monkeypatch):
    import mapping_store

    meta = {"batches": [{"batchId": "b1", "delivery": {"state": "written"}}]}
    saved = []
    monkeypatch.setattr(mapping_store, "load_session", lambda session, project, sid: meta)
    monkeypatch.setattr(mapping_store, "save_batches", lambda session, project, sid, batches: saved.append(batches))
    before = mapping_store.session_revision(meta, {"x": 1}, [])
    mapping_store.set_batch_snapshot(None, PROJECT, "ms-1", "b1", {"status": "published", "stateId": "OS_1"})
    assert saved[0][0]["snapshot"] == {"status": "published", "stateId": "OS_1"}
    assert mapping_store.session_revision({"batches": saved[0]}, {"x": 1}, []) == before


def test_a_snapshot_node_carries_identity_classes_state_and_the_mesh():
    import speckle_validation

    node = speckle_validation.snapshot_node({"name": "Box : 300 [12]", "dgSnapshotId": "OS_1", "dgProject": PROJECT,
                                             "dgNativeId": "u-box", "dgRevitId": 12, "dgMappingState": "auto",
                                             "dgClassIris": ["ex:OpeningBox"], "dgClassLabels": ["OpeningBox"],
                                             "geometry": MESH})
    assert node["dgNativeId"] == "u-box" and node["dgSnapshotId"] == "OS_1" and node["dgRevitId"] == 12
    assert node["dgClassIris"] == ["ex:OpeningBox"] and node["dgMappingState"] == "auto"
    assert len(node["displayValue"]) == 1 and getattr(node, "dgEntityId", None) is None  # never a run entity
