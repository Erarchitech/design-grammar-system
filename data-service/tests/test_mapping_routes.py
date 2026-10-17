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

    def update_session_result(self, session, project, session_id, result, at):
        self.sessions[(project, session_id)]["result"] = result
        self.sessions[(project, session_id)]["updatedAt"] = at

    def record_apply(self, session, project, session_id, actor, at, count):
        self.applies.append((project, session_id, actor, count))

    def list_sessions(self, session, project, limit):
        rows = [s for (p, _), s in sorted(self.sessions.items()) if p == project]
        return [{"sessionId": s["sessionId"], "project": project, "summary": s["result"]["summary"]} for s in rows[::-1][:limit]]

    def save_decision(self, session, project, session_id, decision):
        self.decisions.append((project, session_id, decision))


@pytest.fixture(autouse=True)
def fake_store(monkeypatch):
    store = FakeStore()
    for name in (
        "fetch_classes",
        "fetch_rule_rows",
        "fetch_class_rules",
        "fetch_profiles",
        "save_profile",
        "save_session",
        "load_session",
        "update_session_result",
        "record_apply",
        "list_sessions",
        "save_decision",
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
