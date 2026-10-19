"""Explicit partial commits; no live graph, CAD or inference is used."""

import copy

import pytest

from test_mapping_routes import (CSRF, PROJECT, _commit, _create, _decide,
                                 client, fake_store, fx, mapping_store)


def partial():
    s = _create(fx.facade_v1_descriptors()).json()
    q = next(q for q in s["questions"] if q["type"] == "batch-assign")
    ids = [i["itemId"] for i in q["items"][:2]]
    r = _decide(s["sessionId"], q["questionId"], "accept-all", groupIds=ids)
    assert r.status_code == 200, r.text
    return r.json()["session"]


def test_partial_commit_is_explicit_exact_and_idempotent(fake_store):
    s = partial()
    sid = s["sessionId"]
    assert s["questions"] and not fake_store.profiles and not s["batches"]
    expected = {e["nativeId"] for e in s["elements"] if e["state"] == "confirmed"}
    r = _commit(sid, snapshot=s, request_id="one-click")
    assert r.status_code == 200, r.text
    batch = r.json()
    assert {e["nativeId"] for e in batch["payload"]["elements"]} == expected
    assert batch["payload"]["applied"] == len(expected)
    assert batch["delivery"]["state"] == "queued"
    profiles = copy.deepcopy(fake_store.profiles)
    retry = _commit(sid, snapshot=s, request_id="one-click")
    assert retry.status_code == 200 and retry.json() == batch
    assert fake_store.profiles == profiles
    fresh = client.get(f"/mapping/sessions/{sid}", params={"project": PROJECT}).json()
    assert fresh["questions"] and not fresh["pendingAnswerIds"]
    assert all(not a["undoable"] for a in fresh["answers"])
    q = next(q for q in fresh["questions"] if q["type"] == "batch-assign")
    updated = _decide(sid, q["questionId"], "accept-all").json()["session"]
    second = _commit(sid, snapshot=updated, request_id="second-click")
    assert second.status_code == 200, second.text
    assert not expected.intersection(e["nativeId"] for e in second.json()["payload"]["elements"])
    assert len(fake_store.sessions[(PROJECT, sid)]["batches"]) == 2


def test_ten_proposals_four_accepted_writes_exactly_four(fake_store):
    s = _create(fx.facade_v1_descriptors()).json()
    sid = s["sessionId"]
    stored = fake_store.sessions[(PROJECT, sid)]
    template = copy.deepcopy(s["elements"][0])
    elements = []
    for i in range(10):
        nid = f"proposal-{i}"
        elements.append({**template, "nativeId": nid, "state": "confirmed" if i < 4 else "auto",
                         "roles": [{"classIri": "ex:HexagonalUnit"}]})
        if i < 4:
            fake_store.save_decision(None, PROJECT, sid, {
                "decisionId": f"D-{i}", "answerId": f"A-{i}", "groupId": f"G-{i}",
                "roles": ["ex:HexagonalUnit"], "memberIds": [nid], "decidedAt": str(i),
                "answer": {"items": [{"proposal": {"iri": "ex:HexagonalUnit"}}]},
            })
    stored["result"]["elements"] = elements
    stored["result"]["decided"] = {f"proposal-{i}": ["ex:HexagonalUnit"] for i in range(4)}
    assert not stored.get("batches") and not fake_store.profiles
    response = _commit(sid)
    assert response.status_code == 200, response.text
    batch = response.json()
    assert len(batch["answerIds"]) == 4
    assert batch["payload"]["applied"] == 4
    assert {e["nativeId"] for e in batch["payload"]["elements"]} == {f"proposal-{i}" for i in range(4)}
    assert batch["delivery"] == {"state": "queued"}


def test_revit_population_reference_uses_committed_subset_not_draft_remainder(fake_store):
    s = partial()
    batch = _commit(s["sessionId"], snapshot=s).json()
    expected = mapping_store.engine.populations_of({"elements": [
        {**el, "state": "confirmed", "roles": [{"classIri": iri} for iri in el["roles"]]}
        for el in batch["payload"]["elements"]
    ]})
    # A later accepted answer remains a draft and must not alter the cross-platform reference.
    fresh = client.get(f"/mapping/sessions/{s['sessionId']}", params={"project": PROJECT}).json()
    q = next(q for q in fresh["questions"] if q["type"] == "batch-assign")
    assert _decide(s["sessionId"], q["questionId"], "accept-all").status_code == 200
    response = _create(fx.facade_v1_descriptors(), platform="revit",
                       context={"populationsFromSessionId": s["sessionId"]})
    assert response.status_code == 200, response.text
    stored = fake_store.sessions[(PROJECT, response.json()["sessionId"])]
    assert stored["context"]["populations"] == expected


def test_later_batch_binding_context_contains_history_but_not_uncommitted_drafts(fake_store, monkeypatch):
    s = partial()
    first = _commit(s["sessionId"], snapshot=s).json()
    original = {el["nativeId"] for el in first["payload"]["elements"]}
    fresh = client.get(f"/mapping/sessions/{s['sessionId']}", params={"project": PROJECT}).json()
    q = next(q for q in fresh["questions"] if q["type"] == "batch-assign")
    updated = _decide(s["sessionId"], q["questionId"], "accept-all", groupIds=[q["items"][0]["itemId"]]).json()["session"]
    contexts = []
    real = mapping_store.engine.rule_bindings

    def capture(result, constraints):
        contexts.append(copy.deepcopy(result))
        return real(result, constraints)

    monkeypatch.setattr(mapping_store.engine, "rule_bindings", capture)
    second = _commit(s["sessionId"], snapshot=updated, request_id="binding-context")
    assert second.status_code == 200, second.text
    new = {el["nativeId"] for el in second.json()["payload"]["elements"]}
    assert original and new and not original.intersection(new)
    assert {el["nativeId"] for el in contexts[-1]["elements"]} == original | new
    assert {el["nativeId"] for el in second.json()["payload"]["elements"]} == new
    assert len(original | new) < len(updated["elements"])


def test_stale_revision_and_unknown_class_refuse_without_training(fake_store, monkeypatch):
    s = partial()
    stale = {**s, "revision": "0" * 24}
    assert _commit(s["sessionId"], snapshot=stale).status_code == 409
    monkeypatch.setattr(mapping_store, "fetch_classes", lambda *a: [])
    assert _commit(s["sessionId"], snapshot=s).status_code == 409
    assert not fake_store.profiles
    assert not fake_store.sessions[(PROJECT, s["sessionId"])].get("batches")


def test_no_implicit_or_empty_commit(fake_store):
    s = partial()
    r = client.post(f"/mapping/sessions/{s['sessionId']}/apply", json={"project": PROJECT}, headers=CSRF)
    assert r.status_code == 409
    assert not fake_store.profiles
    r = _commit(s["sessionId"], snapshot={**s, "pendingAnswerIds": []})
    assert r.status_code == 409


def test_receipt_requires_connector_and_valid_counts(fake_store):
    s = partial()
    batch = _commit(s["sessionId"], snapshot=s).json()
    total = batch["payload"]["applied"]
    r = client.post(f"/mapping/sessions/{s['sessionId']}/apply", json={
        "project": PROJECT, "batchId": batch["batchId"],
        "delivery": {"state": "written", "written": total, "skipped": 0},
    }, headers=CSRF)
    assert r.status_code == 403
    with pytest.raises(mapping_store.engine.MappingInputError):
        mapping_store.acknowledge_batch(None, PROJECT, s["sessionId"], batch["batchId"],
                                        {"state": "written", "written": 0, "skipped": total})
    receipt = {"state": "failed", "written": 0, "skipped": total}
    confirmed = mapping_store.acknowledge_batch(None, PROJECT, s["sessionId"], batch["batchId"], receipt)
    assert confirmed["delivery"] == receipt


def test_explicit_commit_does_not_reactivate_retired_demo_profiles(fake_store):
    s = partial()
    drafts = [p for _, _, d in fake_store.decisions
              for p in (d.get("answer") or {}).get("draftProfiles") or []]
    assert drafts
    retired = {p["profileId"]: {**copy.deepcopy(p), "state": "retired",
                               "retiredReason": "cold start for the demo"} for p in drafts}
    for pid, profile in retired.items():
        fake_store.profiles[(PROJECT, pid)] = profile
    response = _commit(s["sessionId"], snapshot=s)
    assert response.status_code == 200, response.text
    for pid, profile in retired.items():
        assert fake_store.profiles[(PROJECT, pid)] == profile


def test_historical_sessions_are_never_replayed(fake_store):
    s = partial()
    fake_store.sessions[(PROJECT, s["sessionId"])]["appliedAt"] = "2026-10-18T12:00:00Z"
    assert _commit(s["sessionId"], snapshot=s).status_code == 409
    assert not fake_store.profiles
