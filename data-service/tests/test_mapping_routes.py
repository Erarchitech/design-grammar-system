"""Route tests for /mapping/* (Phase 1303 MVP slice, plan 02).

The low-level persistence functions of mapping_store are replaced with an
in-memory store and the Neo4j driver with a stub, so the routes, the
orchestration in mapping_store and the engine run for real without Neo4j.
Credentials are a real admin session from conftest (D-20).
"""

from __future__ import annotations

import os
import sys
from contextlib import contextmanager

import pytest
from fastapi.testclient import TestClient

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
os.environ.setdefault("LLM_MASTER_SECRET", "test-master-secret")

import auth  # noqa: E402
import app as app_module  # noqa: E402
from app import app  # noqa: E402
import mapping_engine  # noqa: E402
import mapping_fixtures as fx  # noqa: E402
import mapping_store  # noqa: E402

client = TestClient(app)
CSRF = {auth.CSRF_HEADER: "1"}
PROJECT = "v12-hexagonal-facade-01"


class FakeStore:
    def __init__(self):
        self.sessions = {}
        self.decisions = []
        self.profiles = {}
        self.role_links = {}
        self.applies = []

    # reads of the project graph
    def fetch_classes(self, session, project):
        return fx.facade_classes()

    def fetch_rule_rows(self, session, project):
        return fx.facade_rule_rows()

    def fetch_class_rules(self, session, project):
        return dict(fx.EXTRA_RULE_CLASSES)

    def fetch_properties(self, session, project, constraints):
        classes_of = {}
        for c in constraints:
            classes_of.setdefault(c.prop_local, set()).add(c.class_local)
        return [mapping_engine.PropertyInfo(f"ex:{p}", p, tuple(sorted(cs))) for p, cs in sorted(classes_of.items())]

    # profiles
    def fetch_profiles(self, session, project):
        return [dict(p) for k, p in sorted(self.profiles.items()) if k[0] == project]

    def save_profile(self, session, project, profile, decision_id=None):
        self.profiles[(project, profile["profileId"])] = dict(profile)
        self.role_links[profile["profileId"]] = list(profile.get("roles") or [])

    # sessions
    def save_session(self, session, project, platform, label, descriptors, result, actor, created_at, context):
        sid = f"ms-{len(self.sessions) + 1:012d}"
        self.sessions[(project, sid)] = {
            "sessionId": sid,
            "project": project,
            "platform": platform,
            "label": label,
            "createdAt": created_at,
            "createdBy": actor,
            "context": context,
            "descriptors": mapping_store.unpack(mapping_store.pack(descriptors)),
            "result": mapping_store.unpack(mapping_store.pack(result)),
        }
        return sid

    def load_session(self, session, project, session_id):
        s = self.sessions.get((project, session_id))
        return None if s is None else {**s, "descriptors": list(s["descriptors"]), "result": dict(s["result"])}

    def latest_applied_session_id(self, session, project, platform="grasshopper"):
        rows = [
            s
            for (p, _), s in self.sessions.items()
            if p == project and s.get("platform") == platform and s.get("appliedAt")
        ]
        rows.sort(key=lambda s: (s["appliedAt"], s["sessionId"]), reverse=True)
        return rows[0]["sessionId"] if rows else None

    def update_session_result(self, session, project, session_id, result, at):
        self.sessions[(project, session_id)]["result"] = result
        self.sessions[(project, session_id)]["updatedAt"] = at

    def record_apply(self, session, project, session_id, actor, at, count):
        self.applies.append((project, session_id, actor, count))
        self.sessions[(project, session_id)]["appliedAt"] = at

    def list_sessions(self, session, project, limit):
        rows = [s for (p, _), s in sorted(self.sessions.items()) if p == project]
        return [
            {"sessionId": s["sessionId"], "project": project, "summary": s["result"]["summary"],
             "document": mapping_store.document_of(s["platform"], s["label"])}
            for s in rows[::-1][:limit]
        ]

    def save_decision(self, session, project, session_id, decision):
        self.decisions.append((project, session_id, decision))

    def fetch_decisions(self, session, project, session_id):
        rows = [dict(d) for p, sid, d in self.decisions if p == project and sid == session_id]
        return sorted(rows, key=lambda d: (d["decidedAt"], d["decisionId"]), reverse=True)

    def mark_decisions_undone(self, session, project, session_id, decision_ids, actor, at):
        for p, sid, d in self.decisions:
            if p == project and sid == session_id and d["decisionId"] in decision_ids:
                d["undoneAt"], d["undoneBy"] = at, actor


@pytest.fixture(autouse=True)
def fake_store(monkeypatch):
    store = FakeStore()
    for name in (
        "fetch_classes",
        "fetch_rule_rows",
        "fetch_class_rules",
        "fetch_properties",
        "fetch_profiles",
        "save_profile",
        "save_session",
        "load_session",
        "latest_applied_session_id",
        "update_session_result",
        "record_apply",
        "list_sessions",
        "save_decision",
        "fetch_decisions",
        "mark_decisions_undone",
    ):
        monkeypatch.setattr(mapping_store, name, getattr(store, name))

    class _Driver:
        @contextmanager
        def session(self):
            yield None

    monkeypatch.setattr(app_module, "driver", _Driver())
    return store


def _create(descriptors, **extra):
    body = {"project": PROJECT, "platform": "grasshopper", "label": "test", "elements": descriptors, **extra}
    return client.post("/mapping/sessions", json=body, headers=CSRF)


def _decide(session_id, question_id, option_id, **extra):
    body = {"project": PROJECT, "questionId": question_id, "optionId": option_id, **extra}
    return client.post(f"/mapping/sessions/{session_id}/decisions", json=body, headers=CSRF)


def _learn(store):
    r = _create(fx.facade_v1_descriptors())
    assert r.status_code == 200, r.text
    s = r.json()
    batch = next(q for q in s["questions"] if q["type"] == "batch-assign")
    r1 = _decide(s["sessionId"], batch["questionId"], "accept-all")
    assert r1.status_code == 200, r1.text
    mod = next(q for q in r1.json()["session"]["questions"] if q["type"] == "mapping-or-design")
    r2 = _decide(s["sessionId"], mod["questionId"], "class:ex:GroundFloorUnit")
    assert r2.status_code == 200, r2.text
    return s["sessionId"], r2.json()


def test_create_v1_session_two_questions():
    r = _create(fx.facade_v1_descriptors())
    assert r.status_code == 200, r.text
    s = r.json()
    assert s["sessionId"].startswith("ms-")
    assert s["project"] == PROJECT and s["platform"] == "grasshopper" and s["createdBy"]
    assert s["summary"]["openQuestions"] == 2
    assert sorted(q["type"] for q in s["questions"]) == ["batch-assign", "mapping-or-design"]
    assert "decided" not in s and "splits" not in s


def test_decisions_confirm_everything_and_store_profiles(fake_store):
    sid, out = _learn(fake_store)
    session = out["session"]
    assert session["summary"]["confirmed"] == 376 and session["summary"]["openQuestions"] == 0
    assert all(p["source"] == "learned" for p in out["profiles"])
    assert len(fake_store.decisions) == 5
    assert len(fake_store.profiles) == 5
    assert all(d["sessionId"] == sid for _, _, d in fake_store.decisions)
    assert "ex:GroundFloorUnit" in {r for roles in fake_store.role_links.values() for r in roles}
    assert all("memberIds" not in d for d in out["decisions"])


def test_sliders_measures_llm_and_bindings(fake_store, monkeypatch):
    calls = []

    def fake_propose(elements, measures, parameters, classes, properties, constraints):
        calls.append(len(elements))
        return {"status": "ok", "provider": "fake", "model": "fake-1",
                "objects": {}, "parameters": {"gh:doc:slider:ribs": {"isParameter": False, "confidence": 0.9, "reason": "helper"}},
                "measures": {"gh:doc:measure:ar": {"propertyIri": "ex:hasAspectRatio", "stream": "PB", "confidence": 0.9, "reason": "AR"}}}

    monkeypatch.setattr(mapping_store.mapping_llm, "propose_mapping", fake_propose)
    monkeypatch.setattr(mapping_store, "LLM_ASYNC", False)
    d = fx.facade_v1_descriptors()
    for el in d:
        el["stream"] = el["nativeId"].split(":")[2]
    params = [{"nativeId": f"gh:doc:slider:mw{i}", "name": f"Module Width F{i}"} for i in range(1, 4)]
    params.append({"nativeId": "gh:doc:slider:ribs", "name": "КолВо ребер"})
    measures = [{"nativeId": "gh:doc:measure:ar", "name": "AR", "component": "measure", "count": 125,
                 "streams": [{"stream": "PB", "pathMatch": True, "agreement": {"hasAspectRatio": 1.0}}]}]
    r = _create(d, parameters=params, measures=measures, context={"llm": True})
    assert r.status_code == 200, r.text
    s = r.json()
    assert calls == [376] and s["llm"]["status"] == "ok" and s["llm"]["model"] == "fake-1"
    ribs = next(p for p in s["parameters"] if p["name"] == "КолВо ребер")
    assert ribs["state"] == "unmapped" and ribs["reason"] == "helper"
    qp = next(q for q in s["questions"] if q["type"] == "batch-parameters")
    qm = next(q for q in s["questions"] if q["type"] == "batch-measures")
    sid = s["sessionId"]
    for q in (next(q for q in s["questions"] if q["type"] == "batch-assign"),):
        assert _decide(sid, q["questionId"], "accept-all").status_code == 200
    mod = next(q for q in _decide(sid, qp["questionId"], "accept-all").json()["session"]["questions"] if q["type"] == "mapping-or-design")
    assert _decide(sid, qm["questionId"], "accept-all").status_code == 200
    final = _decide(sid, mod["questionId"], "class:ex:GroundFloorUnit").json()["session"]
    assert final["summary"]["openQuestions"] == 0
    assert {p["state"] for p in final["parameters"] if p["name"] != "КолВо ребер"} == {"confirmed"}
    assert final["measures"][0]["state"] == "confirmed"
    assert calls == [376], "the recorded proposal is reused, not asked again"
    applied = client.post(f"/mapping/sessions/{sid}/apply", json={"project": PROJECT}, headers=CSRF).json()
    assert {p["name"] for p in applied["parameters"]} == {"Module Width F1", "Module Width F2", "Module Width F3"}
    assert {b["ruleId"] for b in applied["bindings"]} == {"R_GLASS_ASPECTRATIO_MIN_1.3_V", "R_GLASS_ASPECTRATIO_MAX_6_V"}
    # A later variant is fully learned: no open question, so no LLM call.
    r2 = _create(fx.facade_v2_descriptors(), parameters=[{"nativeId": "gh:doc2:slider:mw", "name": "Module Width F4"}], context={"llm": True})
    assert r2.json()["parameters"][0]["state"] == "auto" and r2.json()["summary"]["openQuestions"] == 0
    assert calls == [376]
    bad = _create(fx.facade_v1_descriptors(), measures=[{"nativeId": "x"}])
    assert bad.status_code == 400 and bad.json()["detail"]["code"] == "MAPPING_INPUT_INVALID"


def test_llm_refines_in_the_background_and_keeps_answers(fake_store, monkeypatch):
    started = []

    class DeferredThread:
        def __init__(self, target, args, daemon):
            started.append((target, args))

        def start(self):
            pass

    monkeypatch.setattr(mapping_store.threading, "Thread", DeferredThread)
    monkeypatch.setattr(mapping_store, "LLM_ASYNC", True)
    monkeypatch.setattr(
        mapping_store.mapping_llm,
        "propose_mapping",
        lambda *a: {"status": "ok", "model": "slow-1", "objects": {}, "parameters": {},
                    "measures": {"gh:doc:measure:hg": {"propertyIri": "ex:hasGapCount", "stream": "HU", "confidence": 0.9, "reason": "hex gaps"}}},
    )
    d = fx.facade_v1_descriptors()
    for el in d:
        el["stream"] = el["nativeId"].split(":")[2]
    measures = [{"nativeId": "gh:doc:measure:hg", "name": "HG", "count": 100,
                 "streams": [{"stream": "HU", "pathMatch": True, "constant": True, "agreement": {"hasGapCount": 1.0}}]}]
    s = _create(d, measures=measures, context={"llm": True}).json()
    assert s["llm"]["status"] == "pending" and len(started) == 1
    sid = s["sessionId"]
    batch = next(q for q in s["questions"] if q["type"] == "batch-assign")
    assert _decide(sid, batch["questionId"], "accept-all").status_code == 200

    updates = []

    def fake_run(session, query, params):
        updates.append(params["props"])
        stored = fake_store.sessions[(PROJECT, sid)]
        stored["context"] = mapping_store.json.loads(params["props"]["contextJson"])
        stored["result"] = mapping_store.unpack(params["props"]["resultZ"])
        return []

    monkeypatch.setattr(mapping_store, "_run", fake_run)
    monkeypatch.setattr(mapping_store, "_get_driver", lambda: app_module.driver)
    target, args = started[0]
    target(*args)
    refined = client.get(f"/mapping/sessions/{sid}", params={"project": PROJECT}).json()
    assert refined["llm"]["status"] == "ok" and refined["llm"]["model"] == "slow-1"
    hg = refined["measures"][0]
    assert hg["state"] == "suggested" and hg["property"]["label"] == "hasGapCount"
    # The answer given before the proposal arrived is kept.
    assert refined["summary"]["confirmed"] >= 351

    # A proposal landing after apply is recorded; the applied result stays as it was.
    fake_store.sessions[(PROJECT, sid)]["appliedAt"] = "2026-10-18T12:00:00Z"
    monkeypatch.setattr(
        mapping_store.mapping_llm,
        "propose_mapping",
        lambda *a: {"status": "ok", "model": "slow-2", "objects": {}, "parameters": {},
                    "measures": {"gh:doc:measure:hg": {"propertyIri": "ex:hasLevelOffsetM", "stream": "HU", "confidence": 1.0, "reason": "offset"}}},
    )
    target(*args)
    late = client.get(f"/mapping/sessions/{sid}", params={"project": PROJECT}).json()
    assert late["llm"]["model"] == "slow-2"
    assert late["measures"][0]["property"]["label"] == "hasGapCount"


def test_new_session_on_v2_uses_profiles(fake_store):
    _learn(fake_store)
    r = _create(fx.facade_v2_descriptors())
    s = r.json()
    assert s["summary"]["openQuestions"] == 0 and s["summary"]["auto"] == 376
    assert any(e["designSignals"] for e in s["elements"])


def test_apply_partition(fake_store):
    sid, _ = _learn(fake_store)
    r = client.post(f"/mapping/sessions/{sid}/apply", json={"project": PROJECT}, headers=CSRF)
    assert r.status_code == 200, r.text
    part = r.json()
    assert part["applied"] == 376
    assert {k: len(v) for k, v in part["byClass"].items()} == {
        "ex:BottomTriangularPanel": 125,
        "ex:Facade": 1,
        "ex:GlassPanel": 125,
        "ex:GroundFloorUnit": 25,
        "ex:HexagonalUnit": 100,
    }
    assert fake_store.applies and fake_store.applies[0][3] == 376


def test_get_and_list_sessions(fake_store):
    sid = _create(fx.facade_v1_descriptors()).json()["sessionId"]
    one = client.get(f"/mapping/sessions/{sid}", params={"project": PROJECT})
    assert one.status_code == 200 and one.json()["sessionId"] == sid
    many = client.get("/mapping/sessions", params={"project": PROJECT})
    assert many.status_code == 200 and many.json()["sessions"][0]["sessionId"] == sid


# Revit slice (D-48/D-49, plan 1303-12) -------------------------------------

V1_POPULATIONS = {
    "BottomTriangularPanel": [125],
    "Facade": [1],
    "GlassPanel": [125],
    "GroundFloorUnit": [25],
    "HexagonalUnit": [100],
}


def _apply(fake_store, session_id):
    r = client.post(f"/mapping/sessions/{session_id}/apply", json={"project": PROJECT}, headers=CSRF)
    assert r.status_code == 200, r.text
    return r.json()


def _stored_context(fake_store, session_id):
    return fake_store.sessions[(PROJECT, session_id)]["context"]


def test_revit_session_takes_populations_from_the_latest_applied_gh_session(fake_store):
    applied, _ = _learn(fake_store)
    _apply(fake_store, applied)
    # Newer sessions that must not win: an unapplied Grasshopper one and an applied Revit one.
    _create(fx.facade_v2_descriptors())
    first = _create(fx.revit_like_descriptors(), platform="revit", label="AdaptComponent_V18 · 10:00:00")
    assert first.status_code == 200, first.text
    _apply(fake_store, first.json()["sessionId"])

    second = _create(fx.revit_like_descriptors("r2"), platform="revit", label="AdaptComponent_V18 · 10:05:00")
    assert second.status_code == 200, second.text
    ctx = _stored_context(fake_store, second.json()["sessionId"])
    assert ctx["populationsFromSessionId"] == applied
    assert ctx["populations"] == V1_POPULATIONS


def test_explicit_populations_from_session_id_wins_for_a_revit_session(fake_store):
    # A cold session (no profiles yet, nothing confirmed), so its populations differ
    # from those of the applied session that would be the default.
    explicit = _create(fx.facade_v2_descriptors()).json()["sessionId"]
    applied, _ = _learn(fake_store)
    _apply(fake_store, applied)
    revit = _create(
        fx.revit_like_descriptors(), platform="revit", label="AdaptComponent_V18 · 10:10:00",
        context={"populationsFromSessionId": explicit},
    )
    assert revit.status_code == 200, revit.text
    ctx = _stored_context(fake_store, revit.json()["sessionId"])
    assert ctx["populationsFromSessionId"] == explicit
    assert ctx["populations"] == mapping_engine.populations_of(fake_store.sessions[(PROJECT, explicit)]["result"])
    assert ctx["populations"] != V1_POPULATIONS
    missing = _create(
        fx.revit_like_descriptors("r2"), platform="revit", context={"populationsFromSessionId": "ms-nope"}
    )
    assert missing.status_code == 404 and missing.json()["detail"]["code"] == "MAPPING_SESSION_NOT_FOUND"


def test_revit_session_without_an_applied_gh_session_gets_no_populations(fake_store):
    r = _create(fx.revit_like_descriptors(), platform="revit", label="AdaptComponent_V18 · 10:00:00")
    assert r.status_code == 200, r.text
    body = r.json()
    ctx = _stored_context(fake_store, body["sessionId"])
    assert "populationsFromSessionId" not in ctx and "populations" not in ctx
    assert not [e for g in body["groups"] for c in g["candidates"] for e in c["evidence"] if e["kind"] == "population"]


def test_revit_session_row_carries_its_document(fake_store):
    sid = _create(fx.revit_like_descriptors(), platform="revit", label="AdaptComponent_V18 · 10:00:00").json()["sessionId"]
    rows = client.get("/mapping/sessions", params={"project": PROJECT}).json()["sessions"]
    assert rows[0]["sessionId"] == sid and rows[0]["document"] == "AdaptComponent_V18"
    plain = _create(fx.revit_like_descriptors("r2"), platform="revit", label="AdaptComponent_V18")
    assert plain.json()["document"] is None


def test_document_of_is_widened_to_revit_and_leaves_grasshopper_as_it_was():
    assert mapping_store.document_of("revit", "AdaptComponent_V18 · 10:00:00") == "AdaptComponent_V18"
    assert mapping_store.document_of("revit", "AdaptComponent_V18") is None
    assert mapping_store.document_of("revit", " · 10:00:00") is None
    assert mapping_store.document_of("revit", "AdaptComponent_V18 · 10:00:00", [{"nativeId": "gh:doc:HU:{0;1}:0"}]) == "AdaptComponent_V18"
    assert mapping_store.document_of(None, "AdaptComponent_V18 · 10:00:00") is None
    assert mapping_store.document_of("grasshopper", "facade-copy · 10:54:09") == "facade-copy"
    assert mapping_store.document_of("grasshopper", "plain", [{"nativeId": "gh:doc:HU:{0;1}:0"}]) == "doc"
    assert mapping_store.document_of("grasshopper", "plain", [{"nativeId": "r-0001"}]) is None


def test_profiles_list_and_authored(fake_store):
    _learn(fake_store)
    r = client.get("/mapping/profiles", params={"project": PROJECT})
    assert r.status_code == 200 and len(r.json()["profiles"]) == 5
    body = {"project": PROJECT, "platform": "revit", "selector": {"category": "Generic Models", "family": "Facade_Panel_Glass"}, "roles": ["ex:GlassPanel"]}
    a = client.post("/mapping/profiles", json=body, headers=CSRF)
    assert a.status_code == 200, a.text
    assert a.json()["source"] == "authored" and a.json()["confidence"] >= 0.8
    bad = client.post("/mapping/profiles", json={**body, "roles": ["ex:Nope"]}, headers=CSRF)
    assert bad.status_code == 400 and bad.json()["detail"]["code"] == "MAPPING_INPUT_INVALID"


def test_profiles_list_leaves_out_retired_profiles(fake_store):
    # Rehearsal 2026-10-18: profiles retired for a cold restart still showed in the Web UI
    # «Профили» table, which has no state column. The list shows the profiles that map.
    _learn(fake_store)
    key = sorted(fake_store.profiles)[0]
    fake_store.profiles[key]["state"] = "retired"
    listed = client.get("/mapping/profiles", params={"project": PROJECT}).json()["profiles"]
    assert len(listed) == 4 and key[1] not in {p["profileId"] for p in listed}


def test_answers_are_listed_and_undo_restores_the_question(fake_store):
    # Plan 1303-10: every answer is listed with its rows and has its own undo.
    r = _create(fx.facade_v1_descriptors(), label="facade-copy · 10:54:09")
    sid = r.json()["sessionId"]
    assert r.json()["document"] == "facade-copy" and r.json()["answers"] == []
    batch = next(q for q in r.json()["questions"] if q["type"] == "batch-assign")
    assert batch["titleRu"] and len(batch["items"]) == 4
    s1 = _decide(sid, batch["questionId"], "accept-all").json()["session"]
    [answer] = s1["answers"]
    assert answer["questionId"] == batch["questionId"] and answer["type"] == "batch-assign" and answer["undoable"] is True
    assert sorted(i["name"] for i in answer["items"]) == sorted(i["name"] for i in batch["items"])
    assert all(i["state"] == "confirmed" and i["proposal"] for i in answer["items"])
    assert s1["summary"]["openQuestions"] == 1 and len(fake_store.profiles) == 4
    listed = client.get("/mapping/sessions", params={"project": PROJECT}).json()["sessions"]
    assert listed[0]["document"] == "facade-copy"
    undone = client.post(f"/mapping/sessions/{sid}/undo", json={"project": PROJECT, "answerId": answer["answerId"]}, headers=CSRF)
    assert undone.status_code == 200, undone.text
    s2 = undone.json()
    assert s2["answers"] == [] and s2["summary"]["openQuestions"] == 2
    assert any(q["type"] == "batch-assign" for q in s2["questions"]) and s2["summary"]["confirmed"] == 0
    # The profiles the answer created are retired, not deleted; an undone answer cannot be undone twice.
    assert {p["state"] for p in fake_store.profiles.values()} == {"retired"}
    assert all(d.get("undoneAt") for _, _, d in fake_store.decisions)
    again = client.post(f"/mapping/sessions/{sid}/undo", json={"project": PROJECT, "answerId": answer["answerId"]}, headers=CSRF)
    assert again.status_code == 404 and again.json()["detail"]["code"] == "MAPPING_ANSWER_NOT_FOUND"
    # The same answer again switches the retired profiles back on.
    s3 = _decide(sid, batch["questionId"], "accept-all").json()["session"]
    assert len(s3["answers"]) == 1 and {p["state"] for p in fake_store.profiles.values()} == {"active"}


def test_undo_is_refused_once_the_session_is_applied(fake_store):
    sid, out = _learn(fake_store)
    answers = out["session"]["answers"]
    assert len(answers) == 2 and all(a["undoable"] for a in answers)
    assert client.post(f"/mapping/sessions/{sid}/apply", json={"project": PROJECT}, headers=CSRF).status_code == 200
    s = client.get(f"/mapping/sessions/{sid}", params={"project": PROJECT}).json()
    assert [a["undoable"] for a in s["answers"]] == [False, False]
    r = client.post(f"/mapping/sessions/{sid}/undo", json={"project": PROJECT, "answerId": answers[0]["answerId"]}, headers=CSRF)
    assert r.status_code == 409 and r.json()["detail"]["code"] == "MAPPING_SESSION_APPLIED"


def test_undo_reverses_a_rejection_on_another_profile(fake_store):
    sid, _ = _learn(fake_store)
    # A second session where the pentagons are answered against the learned GroundFloorUnit profile.
    gfu = next(p for p in fake_store.profiles.values() if p["roles"] == ["ex:GroundFloorUnit"])
    gfu["confirmations"], gfu["rejections"] = 0, 1  # below auto-apply, so the pentagons are asked again
    r = _create(fx.facade_v1_descriptors())
    sid2 = r.json()["sessionId"]
    q = next(q for q in r.json()["questions"] if any(i["count"] == 25 for i in q["items"]))
    pent = next(i["itemId"] for i in q["items"] if i["count"] == 25)
    out = _decide(sid2, q["questionId"], "none", groupIds=[pent]).json()
    assert fake_store.profiles[(PROJECT, gfu["profileId"])]["rejections"] == 2
    aid = out["session"]["answers"][0]["answerId"]
    assert client.post(f"/mapping/sessions/{sid2}/undo", json={"project": PROJECT, "answerId": aid}, headers=CSRF).status_code == 200
    assert fake_store.profiles[(PROJECT, gfu["profileId"])]["rejections"] == 1
    assert fake_store.profiles[(PROJECT, gfu["profileId"])]["state"] == "active"


def test_error_codes():
    missing = client.get("/mapping/sessions/ms-nope", params={"project": PROJECT})
    assert missing.status_code == 404 and missing.json()["detail"]["code"] == "MAPPING_SESSION_NOT_FOUND"
    sid = _create(fx.facade_v1_descriptors()).json()["sessionId"]
    q = _decide(sid, "Q-missing", "none")
    assert q.status_code == 404 and q.json()["detail"]["code"] == "MAPPING_QUESTION_NOT_FOUND"
    qid = client.get(f"/mapping/sessions/{sid}", params={"project": PROJECT}).json()["questions"][0]["questionId"]
    bad = _decide(sid, qid, "class:ex:Nope")
    assert bad.status_code == 400 and bad.json()["detail"]["code"] == "MAPPING_OPTION_INVALID"
    big = _create([{"nativeId": f"n{i}"} for i in range(5001)])
    assert big.status_code == 400 and big.json()["detail"]["code"] == "MAPPING_TOO_MANY_ELEMENTS"
    dup = _create([{"nativeId": "a"}, {"nativeId": "a"}])
    assert dup.status_code == 400 and dup.json()["detail"]["code"] == "MAPPING_INPUT_INVALID"
    platform = client.post("/mapping/sessions", json={"project": PROJECT, "platform": "archicad", "elements": []}, headers=CSRF)
    assert platform.status_code == 422


def test_project_mismatch_between_query_and_body():
    sid = _create(fx.facade_v1_descriptors()).json()["sessionId"]
    r = client.post(f"/mapping/sessions/{sid}/apply?project=other-project", json={"project": PROJECT}, headers=CSRF)
    assert r.status_code in (400, 403, 409, 422)


def test_unauthenticated_is_refused():
    anon = TestClient(app)
    r = anon.post("/mapping/sessions", json={"project": PROJECT, "platform": "grasshopper", "elements": []}, headers=CSRF)
    assert r.status_code == 401


def test_store_pack_roundtrip_and_query_tags():
    payload = {"a": [1, 2, 3], "b": "текст"}
    assert mapping_store.unpack(mapping_store.pack(payload)) == payload
    for name in dir(mapping_store):
        if name.endswith("_QUERY"):
            text = getattr(mapping_store, name)
            assert "// op=mapping_" in text, name
            assert "$project" in text, name
            assert PROJECT not in text, name
