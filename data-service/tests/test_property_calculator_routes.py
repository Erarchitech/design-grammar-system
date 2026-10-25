"""Route tests for /scripts/property-calculators/{candidates,confirm,reject,retire} (Phase 1303-17, DGOPN-05).

The store functions of property_calculator_store are replaced with an in-memory recorder and the Neo4j driver with a
stub, so the routes, the candidate read model and the real auth/route-policy dependency run without Neo4j. The store's
own transactions are tested in test_property_calculator_store.py. Credentials are real: the admin session of conftest,
a project editor and a project viewer minted through the auth store, a delegated ``dgd_`` token and a connector token.
"""

from __future__ import annotations

import hashlib
import json
import os
import sys
from contextlib import contextmanager

import pytest
from fastapi.testclient import TestClient

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
os.environ.setdefault("LLM_MASTER_SECRET", "test-master-secret")

import app as app_module  # noqa: E402
import auth  # noqa: E402
import auth_fixtures  # noqa: E402
import delegation  # noqa: E402
import property_calculator_llm  # noqa: E402
import property_calculator_store as store  # noqa: E402
import property_scripts  # noqa: E402
import route_policy  # noqa: E402
from app import app  # noqa: E402

client = TestClient(app)
CSRF = {auth.CSRF_HEADER: "1"}

PROJECT = "calc-proj"
DG = "https://w3id.org/dg#"
IRI = DG + "hasOpeningHeightMm"
OTHER_IRI = DG + "hasBeamIntersectionCount"
SHA = "a" * 64
CID = "CC-0123456789abcdef"
COMPANY = "ACME-SECRET-NAME"
BASE = "/scripts/property-calculators"
EDITOR = "calc-editor@dg.local"
VIEWER = "calc-viewer@dg.local"


def _payload(*values, iri=IRI):
    props = [{"stateId": f"PS_{i}", "ruleIri": "R1", "dataPropertyIri": iri, "objectRef": f"box-{i}",
              "propValue": {"value": v, "type": "double"}} for i, v in enumerate(values)]
    objs = [{"stateId": f"OS_{i}", "objectRef": f"box-{i}", "label": f"Box [{i}]"} for i in range(len(values))]
    return json.dumps({"version": "2", "objStates": objs, "propStates": props})


def _run(run_id="VR-1", created="2026-10-22T10:00:00Z", values=(100.0, 250.5, 90.0), iri=IRI):
    return {"runId": run_id, "createdAt": created, "statePayloadJson": _payload(*values, iri=iri)}


def _candidate_row(iri=IRI, **extra):
    row = {"dataPropertyIri": iri, "function": "calc_gen_0123456789",
           "source": "def calc_gen_0123456789(ctx, box, params):\n    return 1\n", "sha256": SHA, "unit": "mm",
           "explanation": "tallest", "provider": "fake", "model": "m", "createdAt": "2026-10-22T09:00:00Z",
           "createdBy": "owner", "catalogueId": None, "sourceRunId": None, "retired": False}
    row.update(extra)
    return row


class Env:
    """Everything the routes read or write, with the calls recorded."""

    def __init__(self):
        self.company = COMPANY
        self.candidates = []
        self.blocked = {}
        self.entries = []
        self.runs = {"VR-1": _run()}
        self.latest = "VR-1"
        self.run_reads = []
        self.rules = [{"ruleId": "R1", "classes": [], "dataProperties": [{"iri": IRI, "label": "hasOpeningHeightMm"}]}]
        self.verdict_calls = []
        self.retired = set()  # iris whose project copy is a retired catalogue copy
        self.confirm_calls = []
        self.reject_calls = []
        self.retire_calls = []
        self.regenerate_calls = []
        self.error = {}  # store function name -> CalculatorReviewError to raise


@pytest.fixture(autouse=True)
def env(monkeypatch):
    e = Env()

    def get_validation_run(project, run_id=None):
        e.run_reads.append((project, run_id))
        key = run_id or e.latest
        return e.runs.get(key) if project == PROJECT else None

    def raising(name):
        if name in e.error:
            raise e.error[name]

    def confirm(session, **kw):
        e.confirm_calls.append(kw)
        raising("confirm")
        retired = kw["data_property_iri"] in e.retired
        if retired and kw["allow_reconfirm"] is not True:  # the plan 1303-16 rule (D-60)
            raise store.CalculatorReviewError("CATALOGUE_RECONFIRM_OWNER_REQUIRED", 403,
                                              "only an owner confirms a retired calculator again")
        return {"catalogueId": CID, "entry": {"sourceProject": PROJECT, "confirmedBy": "someone"},
                "alreadyConfirmed": False, "reconfirmed": retired, "reactivatedCopies": 2 if retired else 0}

    def reject(session, **kw):
        e.reject_calls.append(kw)
        raising("reject")
        if kw["data_property_iri"] in e.retired:  # D-60: a retired copy is never rejected, with or without regenerate
            raise store.CalculatorReviewError("CALCULATOR_IN_CATALOGUE", 409,
                                              "the calculator belongs to the company catalogue")
        return {"alreadyRejected": False, "regenerate": kw["regenerate"], "rejectedSha256s": [kw["sha256"]]}

    def regenerate(session, **kw):
        e.regenerate_calls.append(kw)
        raising("regenerate")
        return {"regenerate": True, "alreadyRequested": False}

    def retire(session, **kw):
        e.retire_calls.append(kw)
        raising("retire")
        return {"catalogueId": kw["catalogue_id"], "retiredCopies": 3, "alreadyRetired": False}

    def verdict_counts(session, project, run_id, rule_ids):
        e.verdict_calls.append((project, run_id, list(rule_ids)))
        return [{"ruleId": "R1", "status": "violation", "count": 2}, {"ruleId": "R1", "status": "pass", "count": 1}]

    class _Session:
        def execute_write(self, fn, *a, **k):
            raise AssertionError("the store functions are stubbed; no transaction expected")

    class _Driver:
        @contextmanager
        def session(self):
            yield _Session()

    monkeypatch.setattr(app_module, "driver", _Driver())
    monkeypatch.setattr(app_module, "get_validation_run", get_validation_run)
    monkeypatch.setattr(store, "company_of", lambda project: e.company)
    monkeypatch.setattr(store, "load_candidates", lambda session, project: [dict(c) for c in e.candidates])
    monkeypatch.setattr(store, "load_blocked", lambda session, project: dict(e.blocked))
    monkeypatch.setattr(store, "load_catalogue_entries", lambda session, company: [dict(x) for x in e.entries]
                        if company else [])
    monkeypatch.setattr(store, "load_verdict_counts", verdict_counts)
    monkeypatch.setattr(store, "confirm", confirm)
    monkeypatch.setattr(store, "reject", reject)
    monkeypatch.setattr(store, "retire", retire)
    monkeypatch.setattr(store, "regenerate", regenerate)
    monkeypatch.setattr(property_scripts, "load_rules", lambda session, project, ids: e.rules)
    monkeypatch.setattr(property_calculator_llm, "generate_calculator",
                        lambda *a, **k: pytest.fail("a calculator route must never call the generator or the LLM"))
    return e


def _user_client(username, role):
    auth_fixtures.make_user(username, memberships={PROJECT: role})
    c = TestClient(app)
    auth_fixtures.authorize_client(c, ("user", username))
    return c


def _confirm_body(**over):
    body = {"project": PROJECT, "dataPropertyIri": IRI, "sha256": SHA, "runId": "VR-1",
            "meaning": "tallest opening height", "unit": "mm"}
    body.update(over)
    return body


def _code(response):
    return response.json()["detail"]["code"]


# --------------------------------------------------------------------------------------------------------------
# candidates
# --------------------------------------------------------------------------------------------------------------


def test_candidates_show_source_samples_verdicts_and_the_newest_run(env):
    env.candidates = [_candidate_row()]
    r = client.get(f"{BASE}/candidates", params={"project": PROJECT})
    assert r.status_code == 200, r.text
    body = r.json()
    assert set(body) == {"project", "companyAssigned", "canRetire", "run", "candidates", "blocked", "catalogue"}
    assert body["companyAssigned"] is True and body["run"] == {"runId": "VR-1", "createdAt": "2026-10-22T10:00:00Z"}
    (candidate,) = body["candidates"]
    assert candidate["source"].startswith("def calc_gen_") and candidate["sha256"] == SHA
    assert candidate["stats"] == {"n": 3, "numeric": 3, "min": 90.0, "max": 250.5}
    assert [s["value"] for s in candidate["samples"]] == [100.0, 250.5, 90.0]
    assert candidate["verdicts"] == [{"ruleId": "R1", "counts": {"pass": 1, "violation": 2}}]
    assert candidate["ruleIds"] == ["R1"] and candidate["runNewerThanCalculator"] is True
    assert candidate["retired"] is False and candidate["catalogueId"] is None
    assert env.verdict_calls == [(PROJECT, "VR-1", ["R1"])]


def test_candidates_never_return_the_company_name(env):
    env.candidates = [_candidate_row()]
    env.entries = [{"catalogueId": CID, "propertyKey": "hasopeningheightmm", "propertyName": "hasOpeningHeightMm",
                    "sha256": SHA, "unit": "mm", "meaning": "tallest", "sourceProject": PROJECT,
                    "confirmedBy": "owner@dg.local", "confirmedAt": "2026-10-22T10:00:00Z"}]
    assert COMPANY not in client.get(f"{BASE}/candidates", params={"project": PROJECT}).text


def test_candidates_without_a_company_say_so_and_list_no_catalogue(env):
    env.company = None
    env.entries = [{"catalogueId": CID, "propertyKey": "k", "propertyName": "p"}]
    body = client.get(f"{BASE}/candidates", params={"project": PROJECT}).json()
    assert body["companyAssigned"] is False and body["catalogue"] == []


def test_candidates_unknown_run_is_404(env):
    r = client.get(f"{BASE}/candidates", params={"project": PROJECT, "runId": "VR-OTHER"})
    assert r.status_code == 404 and _code(r) == "CALCULATOR_RUN_NOT_FOUND"
    assert set(r.json()["detail"]) == {"error", "hint", "code"}


def test_candidates_run_of_another_project_is_not_found(env):
    """The route reads a run only through the request project: VR-1 belongs to PROJECT, not to the other project."""
    r = client.get(f"{BASE}/candidates", params={"project": "other-proj", "runId": "VR-1"})
    assert r.status_code == 404 and _code(r) == "CALCULATOR_RUN_NOT_FOUND"
    assert env.run_reads == [("other-proj", "VR-1")]
    own = client.get(f"{BASE}/candidates", params={"project": PROJECT, "runId": "VR-1"})
    assert own.status_code == 200 and own.json()["run"]["runId"] == "VR-1"


def test_candidates_catalogue_provenance_reaches_owners_only(env):
    env.entries = [{"catalogueId": CID, "propertyKey": "hasopeningheightmm", "propertyName": "hasOpeningHeightMm",
                    "sha256": SHA, "unit": "mm", "meaning": "tallest", "sourceProject": "other-proj",
                    "confirmedBy": "owner@dg.local", "confirmedAt": "2026-10-22T10:00:00Z"}]
    owner = client.get(f"{BASE}/candidates", params={"project": PROJECT}).json()
    assert owner["canRetire"] is True
    assert owner["catalogue"][0]["sourceProject"] == "other-proj"
    assert owner["catalogue"][0]["confirmedBy"] == "owner@dg.local"
    editor = _user_client(EDITOR, "editor").get(f"{BASE}/candidates", params={"project": PROJECT}).json()
    assert editor["canRetire"] is False
    assert "sourceProject" not in editor["catalogue"][0] and "confirmedBy" not in editor["catalogue"][0]
    assert editor["catalogue"][0]["catalogueId"] == CID and editor["catalogue"][0]["meaning"] == "tallest"


def test_candidates_blocked_excludes_retired(env):
    retired_iri = DG + "hasRetiredMm"
    env.blocked = {
        IRI: {"status": "rejected", "sha256": SHA, "sha256s": [SHA], "reason": "wrong unit", "by": "u",
              "regenerate": True},
        retired_iri: {"status": "retired", "sha256": "b" * 64, "sha256s": [], "reason": "obsolete", "by": "o",
                      "regenerate": False},
        OTHER_IRI: {"status": "active", "sha256": "c" * 64, "sha256s": ["d" * 64], "reason": None, "by": None,
                    "regenerate": False},
    }
    env.candidates = [_candidate_row(retired_iri, retired=True, catalogueId=CID, sha256="b" * 64)]
    body = client.get(f"{BASE}/candidates", params={"project": PROJECT}).json()
    assert [b["dataPropertyIri"] for b in body["blocked"]] == [IRI]
    assert body["blocked"][0] == {"dataPropertyIri": IRI, "propertyName": "hasOpeningHeightMm", "status": "rejected",
                                  "sha256": SHA, "reason": "wrong unit", "by": "u", "regenerate": True}
    listed = [c for c in body["candidates"] if c["dataPropertyIri"] == retired_iri]
    assert len(listed) == 1 and listed[0]["retired"] is True and listed[0]["catalogueId"] == CID
    assert retired_iri not in [b["dataPropertyIri"] for b in body["blocked"]]


def test_candidates_retired_copy_uses_source_run_when_selected_run_has_no_values(env):
    env.runs = {"VR-NEW": _run("VR-NEW", "2026-10-22T10:00:00Z", values=()),
                "VR-OLD": _run("VR-OLD", "2026-10-21T12:00:00Z", values=(500.0, 700.0))}
    env.latest = "VR-NEW"
    env.candidates = [_candidate_row(retired=True, catalogueId=CID, sourceRunId="VR-OLD",
                                     createdAt="2026-10-21T09:00:00Z")]
    body = client.get(f"{BASE}/candidates", params={"project": PROJECT}).json()
    (candidate,) = body["candidates"]
    assert body["run"]["runId"] == "VR-NEW"
    assert candidate["run"] == {"runId": "VR-OLD", "createdAt": "2026-10-21T12:00:00Z"}
    assert candidate["stats"]["n"] == 2 and candidate["stats"]["max"] == 700.0
    assert candidate["retired"] is True and candidate["catalogueId"] == CID
    assert (PROJECT, "VR-OLD") in env.run_reads and all(p == PROJECT for p, _r in env.run_reads)
    assert env.verdict_calls == [(PROJECT, "VR-OLD", ["R1"])]


def test_candidates_retired_copy_keeps_the_selected_run_when_it_has_values(env):
    env.candidates = [_candidate_row(retired=True, catalogueId=CID, sourceRunId="VR-OLD")]
    body = client.get(f"{BASE}/candidates", params={"project": PROJECT}).json()
    assert body["candidates"][0]["run"]["runId"] == "VR-1"
    assert (PROJECT, "VR-OLD") not in env.run_reads


# --------------------------------------------------------------------------------------------------------------
# confirm
# --------------------------------------------------------------------------------------------------------------


def test_confirm_unassigned_company_is_422(env):
    env.company = None
    r = client.post(f"{BASE}/confirm", json=_confirm_body(), headers=CSRF)
    assert r.status_code == 422 and _code(r) == "CATALOGUE_COMPANY_REQUIRED" and env.confirm_calls == []


def test_confirm_unknown_run_is_404_and_writes_nothing(env):
    r = client.post(f"{BASE}/confirm", json=_confirm_body(runId="VR-NOPE"), headers=CSRF)
    assert r.status_code == 404 and _code(r) == "CALCULATOR_RUN_NOT_FOUND" and env.confirm_calls == []


def test_confirm_run_without_values_for_the_property_is_422(env):
    env.runs["VR-2"] = _run("VR-2", values=(1.0,), iri=OTHER_IRI)
    r = client.post(f"{BASE}/confirm", json=_confirm_body(runId="VR-2"), headers=CSRF)
    assert r.status_code == 422 and _code(r) == "CALCULATOR_RUN_INVALID" and env.confirm_calls == []


@pytest.mark.parametrize("meaning", ["   ", "\x00\x01", " \n\t "])
def test_confirm_meaning_empty_after_cleaning_is_422(env, meaning):
    r = client.post(f"{BASE}/confirm", json=_confirm_body(meaning=meaning), headers=CSRF)
    assert r.status_code == 422 and _code(r) == "CALCULATOR_INPUT_INVALID" and env.confirm_calls == []


def test_confirm_cleans_the_meaning_and_sends_the_contract_version(env):
    r = client.post(f"{BASE}/confirm", json=_confirm_body(meaning="  tallest \n opening\x00 height  "), headers=CSRF)
    assert r.status_code == 200, r.text
    (call,) = env.confirm_calls
    assert call["meaning"] == "tallest opening height"
    assert call["contract_version"] == property_scripts.load_catalogue()["version"]
    assert call["company"] == COMPANY and call["project"] == PROJECT and call["sha256"] == SHA
    assert call["run"] == {"runId": "VR-1", "createdAt": "2026-10-22T10:00:00Z"}
    assert call["actor"] == auth_fixtures.TEST_ADMIN_USERNAME


def test_confirm_caps_the_meaning_at_160(env):
    r = client.post(f"{BASE}/confirm", json=_confirm_body(meaning="m" * 400), headers=CSRF)
    assert r.status_code == 200 and env.confirm_calls[0]["meaning"] == "m" * 160


def test_confirm_without_unit_uses_stored_unit(env):
    body = _confirm_body()
    del body["unit"]
    for variant in (body, _confirm_body(unit=None), _confirm_body(unit="   "), _confirm_body(unit="\x00")):
        env.confirm_calls.clear()
        r = client.post(f"{BASE}/confirm", json=variant, headers=CSRF)
        assert r.status_code == 200, r.text
        assert env.confirm_calls[0]["unit"] is None  # the store falls back to the stored unit, or null
    # a store that falls back to the stored calculator unit is answered 200 and the unit is not invented here
    assert r.json()["catalogueId"] == CID


def test_confirm_cleans_non_blank_unit(env):
    r = client.post(f"{BASE}/confirm", json=_confirm_body(unit=" m \t m\x00 "), headers=CSRF)
    assert r.status_code == 200
    unit = env.confirm_calls[0]["unit"]
    assert unit == "m m" and len(unit) <= 40


def test_confirm_store_refusals_pass_through_as_error_hint_code(env):
    for code, status in (("CALCULATOR_CHANGED", 409), ("CALCULATOR_INTEGRITY", 409), ("CALCULATOR_RUN_INVALID", 422),
                         ("CATALOGUE_PROPERTY_TAKEN", 409), ("CALCULATOR_NOT_FOUND", 404),
                         ("CALCULATOR_NOT_PENDING", 409)):
        env.error["confirm"] = store.CalculatorReviewError(code, status, f"detail of {code}")
        r = client.post(f"{BASE}/confirm", json=_confirm_body(), headers=CSRF)
        assert r.status_code == status and _code(r) == code
        detail = r.json()["detail"]
        assert detail["error"] == f"detail of {code}" and detail["hint"]


def test_confirm_rejects_a_malformed_sha256(env):
    for bad in ("short", "A" * 64, "g" * 64):
        r = client.post(f"{BASE}/confirm", json=_confirm_body(sha256=bad), headers=CSRF)
        assert r.status_code == 422 and env.confirm_calls == []


def test_confirm_success_answers_catalogue_id_and_counts_without_the_company(env):
    r = client.post(f"{BASE}/confirm", json=_confirm_body(), headers=CSRF)
    assert r.status_code == 200
    assert r.json() == {"project": PROJECT, "dataPropertyIri": IRI, "catalogueId": CID, "alreadyConfirmed": False,
                        "reconfirmed": False, "reactivatedCopies": 0}
    assert COMPANY not in r.text


def test_confirm_retired_copy_answers_reconfirmed(env):
    env.retired.add(IRI)
    r = client.post(f"{BASE}/confirm", json=_confirm_body(), headers=CSRF)  # admin = owner
    assert r.status_code == 200, r.text
    assert r.json()["reconfirmed"] is True and r.json()["reactivatedCopies"] == 2
    assert env.confirm_calls[0]["allow_reconfirm"] is True


def test_reconfirm_retired_requires_owner(env):
    editor = _user_client(EDITOR, "editor")
    env.retired.add(IRI)
    refused = editor.post(f"{BASE}/confirm", json=_confirm_body(), headers=CSRF)
    assert refused.status_code == 403 and _code(refused) == "CATALOGUE_RECONFIRM_OWNER_REQUIRED"
    assert set(refused.json()["detail"]) == {"error", "hint", "code"}
    assert env.confirm_calls[-1]["allow_reconfirm"] is False
    assert env.retired == {IRI}  # nothing was written
    allowed = client.post(f"{BASE}/confirm", json=_confirm_body(), headers=CSRF)  # the admin is an owner
    assert allowed.status_code == 200 and allowed.json()["reconfirmed"] is True
    assert env.confirm_calls[-1]["allow_reconfirm"] is True
    # an editor's first confirm of a pending calculator still succeeds
    env.retired.clear()
    first = editor.post(f"{BASE}/confirm", json=_confirm_body(), headers=CSRF)
    assert first.status_code == 200 and first.json()["reconfirmed"] is False
    assert env.confirm_calls[-1]["allow_reconfirm"] is False


def test_confirm_by_a_project_owner_member_passes_allow_reconfirm(env):
    owner = _user_client("calc-owner@dg.local", "owner")
    env.retired.add(IRI)
    r = owner.post(f"{BASE}/confirm", json=_confirm_body(), headers=CSRF)
    assert r.status_code == 200 and env.confirm_calls[-1]["allow_reconfirm"] is True


# --------------------------------------------------------------------------------------------------------------
# reject and retire
# --------------------------------------------------------------------------------------------------------------


def test_reject_cleans_the_reason_and_passes_regenerate(env):
    body = {"project": PROJECT, "dataPropertyIri": IRI, "sha256": SHA, "reason": "  wrong \n unit\x00 ",
            "regenerate": True}
    r = client.post(f"{BASE}/reject", json=body, headers=CSRF)
    assert r.status_code == 200, r.text
    (call,) = env.reject_calls
    assert call["reason"] == "wrong unit" and call["regenerate"] is True and call["sha256"] == SHA
    assert r.json() == {"project": PROJECT, "dataPropertyIri": IRI, "alreadyRejected": False, "regenerate": True,
                        "rejectedSha256s": [SHA]}
    body.pop("regenerate")
    client.post(f"{BASE}/reject", json=body, headers=CSRF)
    assert env.reject_calls[-1]["regenerate"] is False


def test_reject_blank_reason_is_422(env):
    body = {"project": PROJECT, "dataPropertyIri": IRI, "sha256": SHA, "reason": "  \x00 "}
    r = client.post(f"{BASE}/reject", json=body, headers=CSRF)
    assert r.status_code == 422 and _code(r) == "CALCULATOR_INPUT_INVALID" and env.reject_calls == []


def test_reject_regenerate_on_retired_copy_is_refused(env):
    env.retired.add(IRI)
    for regenerate in (True, False):
        body = {"project": PROJECT, "dataPropertyIri": IRI, "sha256": SHA, "reason": "no", "regenerate": regenerate}
        r = client.post(f"{BASE}/reject", json=body, headers=CSRF)
        assert r.status_code == 409 and _code(r) == "CALCULATOR_IN_CATALOGUE"
        assert set(r.json()["detail"]) == {"error", "hint", "code"}
    assert env.retired == {IRI}  # nothing was written; the generator was never called (the stub fails the test)


def test_retire_unassigned_company_is_422(env):
    env.company = None
    r = client.post(f"{BASE}/retire", json={"project": PROJECT, "catalogueId": CID, "reason": "obsolete"},
                    headers=CSRF)
    assert r.status_code == 422 and _code(r) == "CATALOGUE_COMPANY_REQUIRED" and env.retire_calls == []


def test_retire_calls_the_store_with_the_requesting_projects_company_and_a_clean_reason(env):
    r = client.post(f"{BASE}/retire", json={"project": PROJECT, "catalogueId": CID, "reason": " obsolete \n now\x00"},
                    headers=CSRF)
    assert r.status_code == 200, r.text
    (call,) = env.retire_calls
    assert call["company"] == COMPANY and call["project"] == PROJECT and call["catalogue_id"] == CID
    assert call["reason"] == "obsolete now"
    assert r.json() == {"project": PROJECT, "catalogueId": CID, "retiredCopies": 3, "alreadyRetired": False}
    assert COMPANY not in r.text


def test_retire_store_refusal_passes_through(env):
    env.error["retire"] = store.CalculatorReviewError("CATALOGUE_ENTRY_NOT_FOUND", 404, "no such catalogue entry")
    r = client.post(f"{BASE}/retire", json={"project": PROJECT, "catalogueId": CID, "reason": "x"}, headers=CSRF)
    assert r.status_code == 404 and _code(r) == "CATALOGUE_ENTRY_NOT_FOUND"


def test_retire_rejects_a_malformed_catalogue_id(env):
    r = client.post(f"{BASE}/retire", json={"project": PROJECT, "catalogueId": "CC-xyz", "reason": "x"},
                    headers=CSRF)
    assert r.status_code == 422 and env.retire_calls == []


def test_retire_needs_the_owner_role_of_the_requesting_project(env):
    body = {"project": PROJECT, "catalogueId": CID, "reason": "obsolete"}
    editor = _user_client(EDITOR, "editor").post(f"{BASE}/retire", json=body, headers=CSRF)
    assert editor.status_code == 403 and env.retire_calls == []
    owner = _user_client("calc-owner@dg.local", "owner").post(f"{BASE}/retire", json=body, headers=CSRF)
    assert owner.status_code == 200 and len(env.retire_calls) == 1


def test_viewer_cannot_confirm_or_reject_but_can_list(env):
    viewer = _user_client(VIEWER, "viewer")
    assert viewer.get(f"{BASE}/candidates", params={"project": PROJECT}).status_code == 200
    assert viewer.post(f"{BASE}/confirm", json=_confirm_body(), headers=CSRF).status_code == 403
    body = {"project": PROJECT, "dataPropertyIri": IRI, "sha256": SHA, "reason": "no"}
    assert viewer.post(f"{BASE}/reject", json=body, headers=CSRF).status_code == 403
    assert env.confirm_calls == [] and env.reject_calls == []


# --------------------------------------------------------------------------------------------------------------
# D-57: the LLM and the DeGram agent never decide
# --------------------------------------------------------------------------------------------------------------


def _delegated_headers():
    auth_fixtures.make_user(EDITOR, memberships={PROJECT: "editor"})
    cookie = auth_fixtures.session_cookie_for(EDITOR)
    token, _record = delegation.issue_delegated_token(
        session_hash=hashlib.sha256(cookie.encode()).hexdigest(), username=EDITOR, project=PROJECT)
    return {"Authorization": f"Bearer {token}"}


def test_delegated_principal_lists_candidates_but_never_decides(env):
    plain = TestClient(app)
    headers = _delegated_headers()
    listed = plain.get(f"{BASE}/candidates", params={"project": PROJECT}, headers=headers)
    assert listed.status_code == 200 and listed.json()["canRetire"] is False
    posts = [("confirm", _confirm_body()),
             ("reject", {"project": PROJECT, "dataPropertyIri": IRI, "sha256": SHA, "reason": "no"}),
             ("retire", {"project": PROJECT, "catalogueId": CID, "reason": "x"})]
    for name, body in posts:
        r = plain.post(f"{BASE}/{name}", json=body, headers={**headers, **CSRF})
        assert r.status_code == 403 and _code(r) == "PRINCIPAL_NOT_PERMITTED", name
    assert env.confirm_calls == [] and env.reject_calls == [] and env.retire_calls == []


def test_connector_principal_never_decides(env):
    plain = TestClient(app)
    token = auth_fixtures.connector_token_for(PROJECT)
    headers = {"Authorization": f"Bearer {token}", **CSRF}
    for name, body in (("confirm", _confirm_body()),
                       ("reject", {"project": PROJECT, "dataPropertyIri": IRI, "sha256": SHA, "reason": "no"}),
                       ("retire", {"project": PROJECT, "catalogueId": CID, "reason": "x"})):
        r = plain.post(f"{BASE}/{name}", json=body, headers=headers)
        assert r.status_code == 403, name
    assert env.confirm_calls == [] and env.reject_calls == [] and env.retire_calls == []


def test_d57_decision_rows_admit_member_only():
    policies = route_policy.ROUTE_POLICIES
    confirm = policies[("POST", "/scripts/property-calculators/confirm")]
    reject = policies[("POST", "/scripts/property-calculators/reject")]
    retire = policies[("POST", "/scripts/property-calculators/retire")]
    candidates = policies[("GET", "/scripts/property-calculators/candidates")]
    for row in (confirm, reject, retire):
        assert row.principals == frozenset({"member"})
        assert route_policy.PRINCIPAL_DELEGATED not in row.principals
        assert route_policy.PRINCIPAL_CONNECTOR not in row.principals
        assert row.project_source == "body"
    assert (confirm.min_role, reject.min_role) == ("editor", "editor")  # D-60: the owner check is in the handler
    assert retire.min_role == "owner"  # D-59
    assert candidates.principals == frozenset({"member", "delegated"})
    assert candidates.project_source == "query" and candidates.min_role == "viewer"


def test_security_boundary_lists_the_four_rows_verbatim():
    path = os.path.join(os.path.dirname(__file__), "..", "..", "spec", "SECURITY-BOUNDARY.md")
    text = open(path, encoding="utf-8").read()
    for row in ("GET|/scripts/property-calculators/candidates|delegated+member|query|viewer",
                "POST|/scripts/property-calculators/confirm|member|body|editor",
                "POST|/scripts/property-calculators/reject|member|body|editor",
                "POST|/scripts/property-calculators/retire|member|body|owner",
                "POST|/scripts/property-calculators/regenerate|member|body|editor"):
        assert text.count(row + "\n") == 1, row
    assert "### 3.10 Calculator promotion" in text


# --------------------------------------------------------------------------------------------------------------
# error-code split (plan 1303-18 copies it)
# --------------------------------------------------------------------------------------------------------------

STORE_CODES = {"CALCULATOR_NOT_FOUND", "CALCULATOR_NOT_PENDING", "CALCULATOR_CHANGED", "CALCULATOR_INTEGRITY",
               "CALCULATOR_RUN_INVALID", "CALCULATOR_IN_CATALOGUE", "CATALOGUE_PROPERTY_TAKEN", "CALCULATOR_NOT_RETIRED",
               "CATALOGUE_ENTRY_NOT_FOUND", "CATALOGUE_RECONFIRM_OWNER_REQUIRED"}
ROUTE_CODES = {"CALCULATOR_RUN_NOT_FOUND", "CALCULATOR_INPUT_INVALID", "CATALOGUE_COMPANY_REQUIRED"}


def test_every_calculator_error_code_has_a_hint():
    assert set(app_module._CALCULATOR_HINTS) == STORE_CODES | ROUTE_CODES
    assert len(app_module._CALCULATOR_HINTS) == 13 and all(app_module._CALCULATOR_HINTS.values())


def test_the_store_raises_only_codes_the_routes_have_hints_for():
    import inspect
    import re

    source = inspect.getsource(store)
    raised = set(re.findall(r'CalculatorReviewError\(\s*"([A-Z_]+)"', source))
    assert raised <= set(app_module._CALCULATOR_HINTS), raised - set(app_module._CALCULATOR_HINTS)


# --------------------------------------------------------------------------------------------------------------
# regenerate a retired copy (Phase 1303-24, D-68)
# --------------------------------------------------------------------------------------------------------------

def test_regenerate_cleans_the_reason_and_answers_the_request(env):
    body = {"project": PROJECT, "dataPropertyIri": IRI, "sha256": SHA, "reason": "  reads walls \n only\x00 "}
    r = client.post(f"{BASE}/regenerate", json=body, headers=CSRF)
    assert r.status_code == 200, r.text
    (call,) = env.regenerate_calls
    assert call["reason"] == "reads walls only" and call["sha256"] == SHA and call["data_property_iri"] == IRI
    assert r.json() == {"project": PROJECT, "dataPropertyIri": IRI, "regenerate": True, "alreadyRequested": False}


def test_regenerate_reason_is_optional_and_a_malformed_sha256_is_422(env):
    ok = client.post(f"{BASE}/regenerate", json={"project": PROJECT, "dataPropertyIri": IRI, "sha256": SHA},
                     headers=CSRF)
    assert ok.status_code == 200 and env.regenerate_calls[-1]["reason"] is None
    bad = client.post(f"{BASE}/regenerate", json={"project": PROJECT, "dataPropertyIri": IRI, "sha256": "xyz"},
                      headers=CSRF)
    assert bad.status_code == 422 and len(env.regenerate_calls) == 1


def test_regenerate_of_a_calculator_that_is_not_retired_is_409_with_a_hint(env):
    env.error["regenerate"] = store.CalculatorReviewError("CALCULATOR_NOT_RETIRED", 409, "not retired")
    r = client.post(f"{BASE}/regenerate", json={"project": PROJECT, "dataPropertyIri": IRI, "sha256": SHA},
                    headers=CSRF)
    assert r.status_code == 409 and _code(r) == "CALCULATOR_NOT_RETIRED"
    assert set(r.json()["detail"]) == {"error", "hint", "code"} and r.json()["detail"]["hint"]


def test_regenerate_never_calls_the_generator_and_a_viewer_cannot_use_it(env):
    viewer = _user_client(VIEWER, "viewer")
    body = {"project": PROJECT, "dataPropertyIri": IRI, "sha256": SHA}
    assert viewer.post(f"{BASE}/regenerate", json=body, headers=CSRF).status_code == 403
    assert env.regenerate_calls == []


def test_regenerate_policy_row_admits_member_editor_only():
    row = route_policy.ROUTE_POLICIES[("POST", "/scripts/property-calculators/regenerate")]
    assert row.principals == frozenset({"member"}) and row.project_source == "body" and row.min_role == "editor"
