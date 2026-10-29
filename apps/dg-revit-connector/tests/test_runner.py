# -*- coding: utf-8 -*-
"""The Revit side of the connector, exercised offline.

Two things are proven here, without Revit, pyRevit or a network:

* the **apply loop** (``runner.poll_step``) decides and queues, and never writes
  to Revit itself: a colour job stays queued until the ``ExternalEvent``
  handler's ``Execute`` runs it on the main thread;
* the **commands** (``start_mapping``, ``mapping_status``, ``show``, ``clear``)
  and the **writers** (``revit_io.apply_colours``, ``revit_io.write_parameters``,
  ``revit_io.element_row``) do the right thing, with the Revit calls faked at
  the module seam.

The fake DG client replays canned answers, so the poll logic is tested against
exactly the ``MappingSession`` shapes ``loop`` expects.
"""

import datetime
import importlib
import json
import os
import sys
from types import SimpleNamespace

import pytest

HERE = os.path.dirname(os.path.abspath(__file__))
APP_ROOT = os.path.dirname(HERE)
LIB_DIR = os.path.join(APP_ROOT, "lib")

if LIB_DIR not in sys.path:
    sys.path.insert(0, LIB_DIR)

from pyrevit_stubs import install_pyrevit_stubs  # noqa: E402

NOW = datetime.datetime(2026, 10, 18, 9, 30, 0)


# --- fake Revit ------------------------------------------------------------------

class FakeId(object):
    def __init__(self, value):
        self.Value = value


class FakeView(object):
    def __init__(self, view_id=900):
        self.Id = FakeId(view_id)
        self.overrides = {}


class FakeCategory(object):
    def __init__(self, name="Generic Models", category_id=1, allows=True):
        self.Name = name
        self.Id = FakeId(category_id)
        self.AllowsBoundParameters = allows
        self.CategoryType = "Model"


class FakeDocument(object):
    def __init__(self, title="Tower", path="C:\\p\\tower.rvt", guid="guid-1",
                 active_view=None, family=False):
        self.Title = title
        self.PathName = path
        self.CreationGUID = guid
        self.ActiveView = active_view if active_view is not None else FakeView()
        self.IsFamilyDocument = family
        self.elements = {}

    def GetElement(self, key):
        if hasattr(key, "Value"):
            return self.elements.get(key.Value)
        return self.elements.get(key)


def fake_uiapp(document=None, uidoc=None):
    documents = [document] if document is not None else []
    if uidoc is None and document is not None:
        uidoc = SimpleNamespace(Document=document,
                                Selection=SimpleNamespace(GetElementIds=lambda: []),
                                ShowElements=lambda ids: None)
    return SimpleNamespace(Application=SimpleNamespace(Documents=documents),
                           ActiveUIDocument=uidoc)


# --- fake DG service ---------------------------------------------------------------

class FakeClient(object):
    """Replays canned answers; records every call. The last answer is sticky."""

    def __init__(self, sessions=None, apply_result=None, create_result=None):
        self.sessions = list(sessions or [])
        self.apply_result = {} if apply_result is None else apply_result
        self.create_result = ({"sessionId": "ms-0123456789ab"} if create_result is None
                              else create_result)
        self.get_calls = []
        self.apply_calls = []
        self.create_calls = []
        self.receipts = []
        self.receipt_error = None

    def acknowledge_batch(self, url, token, project, session_id, batch_id, delivery):
        self.receipts.append((batch_id, delivery))
        if self.receipt_error:
            raise self.receipt_error
        for s in self.sessions:
            if isinstance(s, dict):
                for batch in s.get("batches") or []:
                    if batch["batchId"] == batch_id:
                        batch["delivery"] = delivery
        return {"batchId": batch_id, "delivery": delivery}

    def get_session(self, url, token, project, session_id):
        self.get_calls.append((url, token, project, session_id))
        if not self.sessions:
            raise AssertionError("unexpected get_session({})".format(session_id))
        answer = self.sessions.pop(0) if len(self.sessions) > 1 else self.sessions[0]
        if isinstance(answer, BaseException):
            raise answer
        return answer

    def apply_session(self, url, token, project, session_id):
        self.apply_calls.append((url, token, project, session_id))
        if isinstance(self.apply_result, BaseException):
            raise self.apply_result
        return self.apply_result

    def create_session(self, url, token, body):
        self.create_calls.append((url, token, body))
        if isinstance(self.create_result, BaseException):
            raise self.create_result
        return self.create_result


class FakeEvent(object):
    """Stands in for ``UI.ExternalEvent``: records Raise, runs nothing."""

    def __init__(self):
        self.raises = 0

    def Raise(self):
        self.raises += 1


def element(native_id, state, labels=("A",)):
    return {"nativeId": native_id, "groupId": "G-1", "state": state,
            "roles": [{"classIri": "ex:" + label, "label": label} for label in labels]}


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


# --- fixtures ----------------------------------------------------------------------

@pytest.fixture()
def runner(monkeypatch):
    """The runner module with a fresh, empty process state."""
    install_pyrevit_stubs(monkeypatch)
    module = importlib.import_module("dg_connector.runner")
    monkeypatch.setattr(module, "_JOBS", [])
    monkeypatch.setattr(module, "_DONE_SESSIONS", set())
    monkeypatch.setattr(module, "_REJECTED_TOKENS", set())
    monkeypatch.setattr(module, "_HANDLER", [])
    monkeypatch.setattr(module, "_EXTERNAL_EVENT", [])
    monkeypatch.setattr(module, "_THREAD", [])
    monkeypatch.setattr(module, "_OWNER", [])
    monkeypatch.setattr(module, "_LOCAL_SLOTS", {})
    monkeypatch.setattr(module, "_EXTENSION_DIR", [])
    monkeypatch.setattr(module, "_CLIENT", [])
    return module


@pytest.fixture()
def store(runner):
    """A clean connector state (the memory backend outside Revit)."""
    from dg_connector import state as connector_state
    connector_state.ConnectorState().clear()
    yield connector_state.ConnectorState()
    connector_state.ConnectorState().clear()


@pytest.fixture()
def loop_module(runner):
    return importlib.import_module("dg_connector.loop")


@pytest.fixture()
def dg_client(runner):
    return importlib.import_module("dg_connector.dg_client")


@pytest.fixture()
def revit_io(runner):
    return importlib.import_module("dg_connector.revit_io")


def signed_in(store, project="v12-hexagonal-facade-01", session_id="ms-0123456789ab"):
    store.set("url", "http://localhost:8000")
    store.set("token", "dgk_session-token")
    store.set("project", project)
    store.set("user", "owner")
    if session_id:
        store.set("sessionId", session_id)
    return store


def with_session_document(store, document, view_id=900):
    """Store the identity of ``document`` and its view as start_mapping would."""
    store.set("documentKey", "tower")
    store.set("creationGuid", document.CreationGUID)
    store.set("documentPath", document.PathName)
    store.set("viewId", str(view_id))
    view = FakeView(view_id)
    document.elements[view_id] = view
    return view


@pytest.fixture()
def element_ids(revit_io, monkeypatch):
    """ElementId construction is a Revit API call: build the fake id instead."""
    monkeypatch.setattr(revit_io, "element_id", lambda value: FakeId(int(value)))


# --- poll: recolour ---------------------------------------------------------------

def test_poll_recolours_on_a_state_change_and_stores_the_digest(runner, store, loop_module):
    signed_in(store)
    session = mapping_session([element("u1", "suggested")], open_questions=1)
    client = FakeClient([session])

    outcome = runner.poll_step(store, client, NOW)
    assert outcome["action"] == "recolour"
    assert outcome["queued"] == 1
    jobs = runner.queued_jobs()
    assert [job["kind"] for job in jobs] == ["colours"]
    assert jobs[0]["states"] == {"u1": "suggested"}
    assert store.get("lastDigest") == loop_module.session_digest(session)

    runner.take_jobs()
    assert runner.poll_step(store, client, NOW)["action"] == "idle"
    assert runner.queued_jobs() == []  # nothing changed, nothing to paint

    session["elements"][0]["state"] = "confirmed"
    again = runner.poll_step(store, client, NOW)
    assert again["action"] == "recolour"
    assert runner.queued_jobs()[0]["states"] == {"u1": "confirmed"}
    assert store.get("lastDigest") == loop_module.session_digest(session)


def test_poll_idles_without_a_signed_in_session(runner, store):
    client = FakeClient([])
    assert runner.poll_step(store, client, NOW)["action"] == "idle"
    store.set("sessionId", "ms-1")  # session without a token
    assert runner.poll_step(store, client, NOW)["action"] == "idle"
    store.set("token", "dgk_t")
    store.set("sessionId", None)
    assert runner.poll_step(store, client, NOW)["action"] == "idle"
    assert client.get_calls == []


# --- poll: apply --------------------------------------------------------------------

def committed(session, batch_id="batch-one"):
    session.setdefault("batches", []).append({
        "batchId": batch_id, "delivery": {"state": "queued"},
        "payload": {"applied": 1, "elements": [{"nativeId": "u1", "roles": ["ex:GlassPanel"]}]},
    })
    return session


def test_poll_queues_only_committed_subset(runner, store, loop_module):
    signed_in(store)
    runner._EXTERNAL_EVENT.append(FakeEvent())
    store.set("creationGuid", "guid-1")
    session = committed(mapping_session([element("u1", "confirmed"), element("u2", "auto")], open_questions=3))
    store.set("lastDigest", loop_module.session_digest(session))
    client = FakeClient([session])
    outcome = runner.poll_step(store, client, NOW)
    assert outcome["action"] == "apply" and outcome["queued"] == 1
    [job] = runner.queued_jobs()
    assert job["kind"] == "parameters" and job["batchId"] == "batch-one"
    assert job["roles"] == {"u1": ["GlassPanel"]} and job["states"] == {"u1": "confirmed"}
    assert job["creationGuid"] == "guid-1"
    assert not client.apply_calls and not client.receipts
    assert "waiting for the Revit transaction" in outcome["message"]
    assert runner.poll_step(store, client, NOW)["action"] == "idle"
    assert len(runner.queued_jobs()) == 1


def test_poll_never_auto_commits_even_when_all_answered(runner, store, loop_module):
    signed_in(store)
    session = mapping_session([element("u1", "confirmed"), element("u2", "auto")], open_questions=0)
    store.set("lastDigest", loop_module.session_digest(session))
    client = FakeClient([session])
    assert runner.poll_step(store, client, NOW)["action"] == "idle"
    assert not runner.queued_jobs() and not client.apply_calls


def test_poll_retries_receipt_not_cad_write(runner, store, dg_client, loop_module):
    signed_in(store)
    session = committed(mapping_session([element("u1", "confirmed")]))
    store.set("lastDigest", loop_module.session_digest(session))
    client = FakeClient([session])
    runner._remember_delivery(store, "batch-one", {"state": "written", "written": 1, "skipped": 0})
    client.receipt_error = dg_client.DgClientError("UNREACHABLE", "DG is down")
    assert runner.poll_step(store, client, NOW)["action"] == "error"
    client.receipt_error = None
    assert runner.poll_step(store, client, NOW)["action"] == "acknowledge"
    assert len(client.receipts) == 2 and not runner.queued_jobs() and not client.apply_calls


def startswith_dg(message):
    return isinstance(message, str) and message.startswith("DG: ")


def queue_committed_batch(runner, store, loop_module):
    signed_in(store)
    document = FakeDocument()
    with_session_document(store, document)
    runner._EXTERNAL_EVENT.append(FakeEvent())
    runner._EXTENSION_DIR[:] = [APP_ROOT]
    session = committed(mapping_session([element("u1", "confirmed"), element("u2", "auto")],
                                        open_questions=6))
    store.set("lastDigest", loop_module.session_digest(session))
    client = FakeClient([session])
    assert runner.poll_step(store, client, NOW)["action"] == "apply"
    return document, session, client


def test_handler_receipt_follows_atomic_write_and_allows_a_later_batch(
        runner, store, loop_module, revit_io, monkeypatch):
    document, session, client = queue_committed_batch(runner, store, loop_module)
    writes = []

    def write(doc, app, shared_file, roles, states, atomic=False):
        assert doc is document and atomic
        assert not client.receipts
        assert json.loads(store.get("batchDeliveries"))["batch-one"]["state"] == "executing"
        writes.append((roles, states))
        return {"written": len(states), "skipped": 0}

    monkeypatch.setattr(revit_io, "write_parameters", write)
    runner.run_jobs(fake_uiapp(document))
    assert writes == [({"u1": ["GlassPanel"]}, {"u1": "confirmed"})]
    assert not client.receipts  # the handler never sends HTTP
    assert runner.poll_step(store, client, NOW)["action"] == "acknowledge"
    assert client.receipts == [("batch-one", {"state": "written", "written": 1, "skipped": 0})]
    assert runner.poll_step(store, client, NOW)["action"] == "idle"

    committed(session, "batch-two")
    session["batches"][-1]["payload"]["elements"][0]["nativeId"] = "u2"
    assert runner.poll_step(store, client, NOW)["action"] == "apply"
    [job] = runner.queued_jobs()
    assert job["batchId"] == "batch-two" and set(job["roles"]) == {"u2"}


@pytest.mark.parametrize("failure", ["document", "shared-file", "transaction"])
def test_failed_batch_is_acknowledged_without_replaying(
        runner, store, loop_module, revit_io, monkeypatch, failure):
    document, session, client = queue_committed_batch(runner, store, loop_module)
    writes = []

    def write(*args, **kwargs):
        writes.append(1)
        raise RuntimeError("transaction rolled back")

    monkeypatch.setattr(revit_io, "write_parameters", write)
    if failure == "shared-file":
        runner._EXTENSION_DIR[:] = []
    runner.run_jobs(fake_uiapp(None if failure == "document" else document))
    assert writes == ([1] if failure == "transaction" else [])
    assert runner.poll_step(store, client, NOW)["action"] == "acknowledge"
    assert client.receipts == [("batch-one", {"state": "failed", "written": 0, "skipped": 1})]
    assert runner.poll_step(store, client, NOW)["action"] == "idle"
    assert not runner.queued_jobs()


@pytest.mark.parametrize("change", ["sign-out", "session", "token", "reload"])
def test_obsolete_queued_batch_never_writes(
        runner, store, loop_module, revit_io, monkeypatch, change):
    document, session, client = queue_committed_batch(runner, store, loop_module)
    writes = []
    monkeypatch.setattr(revit_io, "write_parameters", lambda *a, **kw: writes.append(1))
    if change == "sign-out":
        store.sign_out()
    elif change == "session":
        store.set("sessionId", "ms-another-session")
    elif change == "token":
        store.set("token", "dgk_new-session")
    else:
        runner._OWNER[:] = ["old-engine"]
        runner._write_slot(runner.POLL_OWNER_KEY, "new-engine")
    runner.run_jobs(fake_uiapp(document))
    assert not writes and not client.receipts


def test_uncertain_delivery_after_reload_is_visible_and_never_replayed(
        runner, store, loop_module):
    document, session, client = queue_committed_batch(runner, store, loop_module)
    runner.take_jobs()  # new engine has no copy of the old engine's pending queue
    outcome = runner.poll_step(store, client, NOW)
    assert outcome["action"] == "idle" and "not be replayed" in outcome["message"]
    assert not runner.queued_jobs() and not client.receipts


def test_reauthentication_does_not_replay_an_uncertain_cad_write(
        runner, store, loop_module):
    document, session, client = queue_committed_batch(runner, store, loop_module)
    runner.take_jobs()
    store.sign_out()
    signed_in(store)
    store.set("lastDigest", loop_module.session_digest(session))
    assert store.get("batchDeliveries") is None
    assert runner.poll_step(store, client, NOW)["action"] == "idle"
    assert not runner.queued_jobs() and not client.receipts


def test_pending_revit_transaction_never_claims_a_terminal_delivery(
        runner, store, loop_module, revit_io, monkeypatch):
    document, session, client = queue_committed_batch(runner, store, loop_module)

    def pending(*args, **kwargs):
        raise revit_io.TransactionPendingError("Pending")

    monkeypatch.setattr(revit_io, "write_parameters", pending)
    runner.run_jobs(fake_uiapp(document))
    assert json.loads(store.get("batchDeliveries"))["batch-one"] == {"state": "executing"}
    assert "unconfirmed" in store.get("message")
    assert runner.poll_step(store, client, NOW)["action"] == "idle"
    assert not client.receipts and not runner.queued_jobs()


@pytest.mark.parametrize("event_status", ["Denied", "TimedOut", "exception"])
def test_rejected_external_event_reports_failure_without_leaving_a_write_job(
        runner, store, loop_module, event_status):
    signed_in(store)
    session = committed(mapping_session([element("u1", "confirmed")]))
    store.set("lastDigest", loop_module.session_digest(session))

    class RejectedEvent(object):
        def Raise(self):
            if event_status == "exception":
                raise RuntimeError("event unavailable")
            return event_status

    runner._EXTERNAL_EVENT.append(RejectedEvent())
    client = FakeClient([session])
    assert runner.poll_step(store, client, NOW)["action"] == "error"
    assert not runner.queued_jobs()
    assert runner.poll_step(store, client, NOW)["action"] == "acknowledge"
    assert client.receipts == [("batch-one", {"state": "failed", "written": 0, "skipped": 1})]


# --- poll: failures -------------------------------------------------------------------

def test_poll_rejected_stops_with_the_sign_in_message(runner, store, dg_client):
    signed_in(store)
    error = dg_client.DgClientError("REJECTED", "connector token expired")
    client = FakeClient([error])

    outcome = runner.poll_step(store, client, NOW)
    assert outcome["action"] == "stop"
    assert outcome["message"] == "DG sign-in expired: sign in again"
    assert store.get("message") == runner.MESSAGE_SIGN_IN_EXPIRED

    # the session is not polled again with that token, which is left for the operator
    assert runner.poll_step(store, client, NOW)["action"] == "stop"
    assert len(client.get_calls) == 1
    assert store.get("token") == "dgk_session-token"
    # only a hash of the rejected token is remembered
    assert "dgk_session-token" not in repr(runner._REJECTED_TOKENS)


def test_a_new_sign_in_resumes_polling_after_a_rejection(runner, store, dg_client):
    signed_in(store)
    session = mapping_session([element("u1", "suggested")], open_questions=1)
    client = FakeClient([dg_client.DgClientError("REJECTED", "expired"), session])
    assert runner.poll_step(store, client, NOW)["action"] == "stop"

    store.set("token", "dgk_fresh-token")  # what the «Вход» button stores
    outcome = runner.poll_step(store, client, NOW)
    assert outcome["action"] == "recolour"
    assert client.get_calls[-1][1] == "dgk_fresh-token"


def test_a_stale_install_does_not_apply(runner, store, loop_module):
    """After a pyRevit reload only the newest install's thread applies."""
    signed_in(store)
    runner._EXTERNAL_EVENT.append(FakeEvent())
    session = committed(mapping_session([element("u1", "confirmed")], open_questions=0))
    store.set("lastDigest", loop_module.session_digest(session))
    client = FakeClient([session], apply_result={"applied": 1})
    runner._OWNER[:] = ["old-engine"]
    runner._write_slot(runner.POLL_OWNER_KEY, "new-engine")

    assert runner.owns_polling() is False
    assert runner.poll_step(store, client, NOW)["action"] == "idle"
    assert client.apply_calls == []

    runner._write_slot(runner.POLL_OWNER_KEY, "old-engine")
    assert runner.poll_step(store, client, NOW)["action"] == "apply"
    assert not client.apply_calls and len(runner.queued_jobs()) == 1


def test_the_poll_loop_stops_when_a_newer_install_owns_polling(runner, monkeypatch):
    runner._write_slot(runner.POLL_OWNER_KEY, "me")
    steps = []
    monkeypatch.setattr(runner, "poll_step", lambda: steps.append(1))

    def sleep(seconds):
        assert seconds == 3
        if len(steps) == 2:
            runner._write_slot(runner.POLL_OWNER_KEY, "a-reloaded-engine")

    runner._poll_loop("me", sleep=sleep)  # returns instead of looping forever
    assert len(steps) == 2


def test_poll_other_errors_keep_polling(runner, store, dg_client):
    signed_in(store)
    error = dg_client.DgClientError("UNREACHABLE", "DG did not answer in 60 s")
    session = mapping_session([element("u1", "suggested")], open_questions=1)
    client = FakeClient([error, session])

    first = runner.poll_step(store, client, NOW)
    assert first["action"] == "error"
    assert "DG did not answer" in first["message"]
    assert store.get("message") == first["message"]

    second = runner.poll_step(store, client, NOW)
    assert second["action"] == "recolour"
    assert len(client.get_calls) == 2


def test_poll_keeps_a_recent_answer_as_a_draft(runner, store, loop_module):
    signed_in(store)
    session = mapping_session([element("u1", "confirmed")], open_questions=0,
                              created_at="2026-10-18T09:29:55Z")
    store.set("lastDigest", loop_module.session_digest(session))
    client = FakeClient([session])
    outcome = runner.poll_step(store, client, NOW)  # 5 s after creation
    assert outcome["action"] == "idle"
    assert outcome["queued"] == 0
    assert runner.queued_jobs() == []


def test_poll_reports_done_for_an_applied_session(runner, store):
    signed_in(store)
    session = mapping_session([element("u1", "confirmed")], applied_at="2026-10-18T09:00:10Z")
    client = FakeClient([session])
    outcome = runner.poll_step(store, client, NOW)
    assert outcome["action"] == "done"
    assert "applied" in outcome["message"]


# --- jobs only run in the handler ---------------------------------------------------

def test_no_job_runs_on_the_poll_thread(runner, store, revit_io, monkeypatch, element_ids):
    signed_in(store)
    document = FakeDocument()
    view = with_session_document(store, document)
    coloured = []

    def fake_apply(target, target_view, states):
        coloured.append((target, target_view, states))
        return len(states)

    monkeypatch.setattr(revit_io, "apply_colours", fake_apply)
    event = FakeEvent()
    runner._EXTERNAL_EVENT.append(event)
    session = mapping_session([element("u1", "suggested")], open_questions=1)

    runner.poll_step(store, FakeClient([session]), NOW)
    assert [job["kind"] for job in runner.queued_jobs()] == ["colours"]
    assert coloured == []       # the poll thread wrote nothing to Revit
    assert event.raises == 1    # it only asked Revit to run the handler

    runner._Handler().Execute(fake_uiapp(document))
    assert coloured == [(document, view, {"u1": "suggested"})]
    assert runner.queued_jobs() == []  # the handler consumed the queue
    assert "coloured 1 element" in store.get("message")


def test_the_handler_is_the_revit_external_event_interface(runner):
    # The stub hands out a fresh dummy class per attribute access, so the base
    # is pinned by name: Revit's interface is IExternalEventHandler (there is
    # no ExternalEventHandler class in Autodesk.Revit.UI).
    assert [base.__name__ for base in runner._Handler.__bases__] == ["IExternalEventHandler"]
    assert runner._Handler().GetName() == "DG mapping"


def test_the_colour_job_uses_the_stored_view_id(runner, store, revit_io, monkeypatch,
                                                element_ids):
    signed_in(store)
    seen = {}
    monkeypatch.setattr(revit_io, "apply_colours",
                        lambda document, view, states: seen.setdefault("view", view) or 1)
    document = FakeDocument()
    stored_view = FakeView(77)
    document.elements[77] = stored_view

    runner._queue_job({"kind": "colours", "states": {"u1": "auto"},
                       "creationGuid": "guid-1", "pathName": document.PathName,
                       "viewId": "77"})
    runner._Handler().Execute(fake_uiapp(document))
    assert seen["view"] is stored_view  # not document.ActiveView


def test_a_colour_job_whose_view_is_gone_writes_nothing(runner, store, revit_io, monkeypatch,
                                                        element_ids):
    signed_in(store)
    called = []
    monkeypatch.setattr(revit_io, "apply_colours",
                        lambda document, view, states: called.append(view) or 0)
    document = FakeDocument()
    runner._queue_job({"kind": "colours", "states": {"u1": "auto"},
                       "creationGuid": "guid-1", "pathName": document.PathName,
                       "viewId": "4242"})
    runner._Handler().Execute(fake_uiapp(document))
    assert called == []
    assert "no longer exists" in store.get("message")


def test_a_job_for_a_document_that_is_not_open_is_dropped(runner, store, revit_io, monkeypatch):
    signed_in(store)
    called = []
    monkeypatch.setattr(revit_io, "apply_colours",
                        lambda document, view, states: called.append(states) or 0)
    runner._queue_job({"kind": "colours", "states": {"u1": "auto"},
                       "sessionId": "ms-0123456789ab",
                       "documentKey": "other", "creationGuid": "guid-other",
                       "pathName": "C:\\p\\other.rvt", "viewId": None})
    runner._Handler().Execute(fake_uiapp(FakeDocument(guid="guid-1",
                                                      path="C:\\p\\tower.rvt")))
    assert called == []
    assert "not open" in store.get("message")
    assert runner.queued_jobs() == []
    # a closed document stops the loop for its session
    assert runner.poll_step(store, FakeClient([]), NOW)["action"] == "done"


def test_a_job_without_a_document_identity_never_writes(runner, store, revit_io, monkeypatch):
    """No GUID and no path: the job must not fall back to whatever document is open."""
    signed_in(store)
    called = []
    monkeypatch.setattr(revit_io, "apply_colours",
                        lambda document, view, states: called.append(document) or 1)
    runner._queue_job({"kind": "colours", "states": {"u1": "auto"},
                       "creationGuid": "", "pathName": "", "viewId": "900"})
    runner._Handler().Execute(fake_uiapp(FakeDocument()))
    assert called == []
    assert "not open" in store.get("message")


def test_a_save_as_twin_does_not_receive_the_job(runner, store, revit_io, monkeypatch,
                                                 element_ids):
    """Same CreationGUID, other path: a Save-As copy is another document."""
    signed_in(store)
    called = []
    monkeypatch.setattr(revit_io, "apply_colours",
                        lambda document, view, states: called.append(document) or 1)
    twin = FakeDocument(guid="guid-1", path="C:\\p\\tower-copy.rvt")
    twin.elements[900] = FakeView(900)
    runner._queue_job({"kind": "colours", "states": {"u1": "auto"},
                       "creationGuid": "guid-1", "pathName": "C:\\p\\tower.rvt",
                       "viewId": "900"})
    runner._Handler().Execute(fake_uiapp(twin))
    assert called == []


def test_a_parameter_job_writes_with_the_shipped_shared_parameter_file(
        runner, store, revit_io, monkeypatch):
    signed_in(store)
    seen = {}

    def fake_write(document, app, shared_file, roles, states):
        seen.update({"document": document, "app": app, "shared_file": shared_file,
                     "roles": roles, "states": states})
        return {"written": 2, "skipped": 1, "categories": 1}

    monkeypatch.setattr(revit_io, "write_parameters", fake_write)
    extension_dir = os.path.join(APP_ROOT, "installed")
    monkeypatch.setattr(runner, "_EXTENSION_DIR", [extension_dir])
    document = FakeDocument()
    uiapp = fake_uiapp(document)
    runner._queue_job({"kind": "parameters", "applied": 3, "roles": {"u1": ["GlassPanel"]},
                       "states": {"u1": "confirmed"}, "creationGuid": "guid-1",
                       "pathName": document.PathName})
    runner._Handler().Execute(uiapp)

    assert seen["document"] is document
    assert seen["app"] is uiapp.Application
    assert seen["shared_file"] == os.path.join(extension_dir, "DG_SharedParameters.txt")
    assert seen["roles"] == {"u1": ["GlassPanel"]}
    assert seen["states"] == {"u1": "confirmed"}
    assert store.get("message") == (
        "DG applied 3 elements; DG_Class / DG_MappingState written on 2 elements (1 skipped)")


def test_a_failing_job_is_reported_not_raised(runner, store, revit_io, monkeypatch,
                                              element_ids):
    signed_in(store)

    def boom(*args, **kwargs):
        raise RuntimeError("transaction failed")

    monkeypatch.setattr(revit_io, "apply_colours", boom)
    document = FakeDocument()
    document.elements[900] = FakeView(900)
    runner._queue_job({"kind": "colours", "states": {"u1": "auto"},
                       "creationGuid": "guid-1", "pathName": document.PathName,
                       "viewId": "900"})
    runner._queue_job({"kind": "colours", "states": {"u2": "auto"},
                       "creationGuid": "guid-1", "pathName": document.PathName,
                       "viewId": "900"})
    assert runner.run_jobs(fake_uiapp(document)) == 2  # the second job still ran
    assert "colours job failed (transaction failed)" in store.get("message")


# --- install ------------------------------------------------------------------------

def test_install_creates_one_handler_and_one_event(runner, monkeypatch):
    first = runner.install(None, "C:\\ext", start_thread=False,
                           external_event=FakeEvent())
    second = runner.install(None, "C:\\ext", start_thread=False,
                            external_event=FakeEvent())
    assert first is second
    assert runner._HANDLER == [first]
    assert len(runner._EXTERNAL_EVENT) == 1
    assert runner._THREAD == []  # start_thread=False: no thread
    assert runner._EXTENSION_DIR == ["C:\\ext"]


def test_install_starts_exactly_one_daemon_poll_thread(runner, monkeypatch):
    import threading
    release = threading.Event()
    started = []

    def fake_loop(owner):
        started.append(owner)
        release.wait(5)

    monkeypatch.setattr(runner, "_poll_loop", fake_loop)
    try:
        runner.install(None, "C:\\ext", start_thread=True, external_event=FakeEvent())
        runner.install(None, "C:\\ext", start_thread=True, external_event=FakeEvent())
        assert len(runner._THREAD) == 1
        assert runner._THREAD[0].daemon is True
        assert len(started) == 1
        # the install owns polling: its owner token is the published one
        assert started[0] == runner._OWNER[0]
        assert runner._read_slot(runner.POLL_OWNER_KEY) == runner._OWNER[0]
        assert runner.owns_polling() is True
    finally:
        release.set()
        runner._THREAD[0].join(5)


def test_a_reload_takes_over_polling(runner, monkeypatch):
    """A second engine (pyRevit reload) publishes a new owner; the first one yields."""
    monkeypatch.setattr(runner, "_poll_loop", lambda owner: None)
    runner.install(None, "C:\\ext", start_thread=True, external_event=FakeEvent())
    first_owner = runner._OWNER[0]
    runner._THREAD[0].join(5)

    # what a fresh engine's module state looks like, sharing the AppDomain slot
    monkeypatch.setattr(runner, "_THREAD", [])
    monkeypatch.setattr(runner, "_OWNER", [])
    runner.install(None, "C:\\ext", start_thread=True, external_event=FakeEvent())
    runner._THREAD[0].join(5)
    assert runner._OWNER[0] != first_owner
    assert runner._read_slot(runner.POLL_OWNER_KEY) == runner._OWNER[0]


# --- start_mapping ------------------------------------------------------------------

ROWS = [{
    "uniqueId": "uid-a",
    "elementId": 101,
    "category": "Generic Models",
    "family": "Panel",
    "typeName": "Glass",
    "parameters": [{"name": "Mark", "storageType": "String", "unit": "",
                    "displayValue": "G-1", "value": "G-1"}],
    "typeParameters": [],
    "adaptivePointCount": None,
}]


def test_start_mapping_refuses_without_a_sign_in(runner, store):
    client = FakeClient([])
    outcome = runner.start_mapping(fake_uiapp(FakeDocument()), client=client, now=NOW)
    assert outcome["started"] is False
    assert outcome["message"] == runner.MESSAGE_NOT_SIGNED_IN
    assert "Sign in to DG first" in outcome["message"]
    assert client.create_calls == []


def test_start_mapping_refuses_an_unsaved_or_family_document(runner, store):
    signed_in(store)
    client = FakeClient([])
    unsaved = runner.start_mapping(fake_uiapp(FakeDocument(path="")), client=client, now=NOW)
    assert unsaved["started"] is False
    assert unsaved["message"] == runner.MESSAGE_NO_PROJECT
    family = runner.start_mapping(fake_uiapp(FakeDocument(family=True)), client=client, now=NOW)
    assert family["started"] is False
    assert client.create_calls == []


def test_start_mapping_builds_the_body_and_label(runner, store, revit_io, monkeypatch):
    signed_in(store)
    document = FakeDocument(title="AdaptComponent_V18",
                            path="C:\\models\\AdaptComponent_V18-dg-mapping.rvt",
                            guid="guid-1", active_view=FakeView(77))
    monkeypatch.setattr(revit_io, "collect_scope",
                        lambda doc, uidoc, max_elements=5000: (["e1", "e2", "e3", "e4"], 6))
    monkeypatch.setattr(revit_io, "read_rows", lambda doc, elements: (ROWS, 2))
    coloured = []
    monkeypatch.setattr(revit_io, "apply_colours",
                        lambda doc, view, states: coloured.append((doc, view, states))
                        or len(states))
    session = mapping_session([element("uid-a", "suggested", ("Panel",)),
                               element("uid-b", "confirmed", ("Glass",))],
                              open_questions=1)
    client = FakeClient(create_result=session)

    outcome = runner.start_mapping(fake_uiapp(document), client=client, now=NOW)

    assert outcome["started"] is True
    assert outcome["sessionId"] == "ms-0123456789ab"
    url, token, request_body = client.create_calls[0]
    assert url == "http://localhost:8000" and token == "dgk_session-token"
    assert request_body["project"] == "v12-hexagonal-facade-01"
    assert request_body["platform"] == "revit"
    assert request_body["label"] == "adaptcomponent_v18-dg-mapping \u00b7 09:30:00"
    assert [descriptor["nativeId"] for descriptor in request_body["elements"]] == ["uid-a"]
    assert request_body["elements"][0]["platform"] == "revit"

    assert store.get("sessionId") == "ms-0123456789ab"
    assert store.get("documentKey") == "adaptcomponent_v18-dg-mapping"
    assert store.get("documentPath") == document.PathName
    assert store.get("creationGuid") == "guid-1"
    assert store.get("viewId") == "77"
    assert coloured and coloured[0][2] == {"uid-a": "suggested", "uid-b": "confirmed"}

    message = outcome["message"]
    assert "1 element read" in message
    assert "2 skipped" in message
    assert "2 beyond the 5000-element cap" in message
    assert "1 open question" in message
    assert store.get("message") == message
    # painted at once, so the poll loop does not paint the same states again
    assert store.get("lastDigest") == runner.loop.session_digest(session)


def one_row_scope(revit_io, monkeypatch):
    monkeypatch.setattr(revit_io, "collect_scope",
                        lambda doc, uidoc, max_elements=5000: (["e1"], 1))
    monkeypatch.setattr(revit_io, "read_rows", lambda doc, elements: (ROWS, 0))


def test_start_mapping_refuses_an_empty_scope_without_calling_dg(runner, store, revit_io,
                                                                monkeypatch):
    signed_in(store, session_id=None)
    monkeypatch.setattr(revit_io, "collect_scope",
                        lambda doc, uidoc, max_elements=5000: ([], 0))
    monkeypatch.setattr(revit_io, "read_rows", lambda doc, elements: ([], 0))
    client = FakeClient()
    outcome = runner.start_mapping(fake_uiapp(FakeDocument()), client=client, now=NOW)
    assert outcome["started"] is False
    assert outcome["message"] == runner.MESSAGE_EMPTY_SCOPE
    assert client.create_calls == []


def test_start_mapping_reports_a_dg_refusal(runner, store, dg_client, revit_io, monkeypatch):
    signed_in(store, session_id=None)
    one_row_scope(revit_io, monkeypatch)
    error = dg_client.DgClientError("HTTP_ERROR", "MAPPING_INPUT_INVALID")
    client = FakeClient(create_result=error)
    outcome = runner.start_mapping(fake_uiapp(FakeDocument()), client=client, now=NOW)
    assert outcome["started"] is False
    assert len(client.create_calls) == 1
    assert "MAPPING_INPUT_INVALID" in outcome["message"]
    assert "dgk_session-token" not in outcome["message"]
    assert store.get("sessionId") is None  # no session was adopted


def test_start_mapping_reports_an_expired_sign_in(runner, store, dg_client, revit_io,
                                                  monkeypatch):
    signed_in(store, session_id=None)
    one_row_scope(revit_io, monkeypatch)
    client = FakeClient(create_result=dg_client.DgClientError("REJECTED", "AUTH_INVALID"))
    outcome = runner.start_mapping(fake_uiapp(FakeDocument()), client=client, now=NOW)
    assert outcome["started"] is False
    assert outcome["message"] == runner.MESSAGE_SIGN_IN_EXPIRED


def test_start_mapping_keeps_the_open_session_when_creation_fails(runner, store, dg_client,
                                                                  revit_io, monkeypatch):
    signed_in(store)  # sessionId "ms-0123456789ab"
    one_row_scope(revit_io, monkeypatch)
    client = FakeClient(create_result=dg_client.DgClientError("UNREACHABLE", "DG is down"))
    outcome = runner.start_mapping(fake_uiapp(FakeDocument()), client=client, now=NOW)
    assert outcome["started"] is False
    assert store.get("sessionId") == "ms-0123456789ab"


def test_start_mapping_survives_a_colour_failure(runner, store, revit_io, monkeypatch):
    signed_in(store)

    def boom(*args, **kwargs):
        raise RuntimeError("view is not editable")

    one_row_scope(revit_io, monkeypatch)
    monkeypatch.setattr(revit_io, "apply_colours", boom)
    store.set("lastDigest", "digest-of-an-earlier-session")
    session = mapping_session([element("uid-a", "suggested")], open_questions=0)
    outcome = runner.start_mapping(fake_uiapp(FakeDocument()),
                                   client=FakeClient(create_result=session), now=NOW)
    assert outcome["started"] is True  # the session is kept
    assert store.get("sessionId") == "ms-0123456789ab"
    # no digest: the poll loop will queue the colours again
    assert store.get("lastDigest") is None


# --- mapping_status, show, clear -------------------------------------------------------

def test_mapping_status_reports_the_document_and_the_message(runner, store):
    signed_in(store)
    store.set("message", "ready")
    status = runner.mapping_status(fake_uiapp(FakeDocument(path="C:\\p\\Tower.rvt")))
    assert status["signedIn"] is True
    assert status["document"] == "tower"
    assert status["connectorMessage"] == "ready"
    assert status["sessionId"] == "ms-0123456789ab"
    assert "token" not in status
    assert "dgk_session-token" not in json.dumps(status)


def test_mapping_status_without_an_active_document(runner, store):
    signed_in(store)
    status = runner.mapping_status(fake_uiapp())
    assert status["document"] is None
    assert status["connectorMessage"] == ""


def test_show_delegates_to_revit_io(runner, revit_io, monkeypatch):
    seen = {}
    monkeypatch.setattr(revit_io, "show_elements",
                        lambda uidoc, doc, unique_ids: seen.update(
                            {"uidoc": uidoc, "doc": doc, "ids": unique_ids})
                        or {"found": 1, "shown": 1, "missing": []})
    result = runner.show("UIDOC", "DOC", ["uid-a"])
    assert result == {"found": 1, "shown": 1, "missing": []}
    assert seen == {"uidoc": "UIDOC", "doc": "DOC", "ids": ["uid-a"]}


def test_clear_without_a_session_clears_nothing(runner, store):
    outcome = runner.clear(fake_uiapp(FakeDocument()))
    assert outcome == {"cleared": 0, "message": runner.MESSAGE_NO_SESSION}
    assert "No DG mapping session" in outcome["message"]


def recording_clear(revit_io, monkeypatch):
    seen = {}
    monkeypatch.setattr(revit_io, "clear_colours",
                        lambda doc, view, unique_ids: seen.update(
                            {"doc": doc, "view": view, "ids": list(unique_ids)})
                        or len(unique_ids))
    return seen


def test_clear_removes_the_session_overrides(runner, store, revit_io, monkeypatch, element_ids):
    signed_in(store)
    document = FakeDocument()
    view = with_session_document(store, document)
    store.set("lastDigest", "painted")
    session = mapping_session([element("u1", "confirmed"), element("u2", "auto")])
    seen = recording_clear(revit_io, monkeypatch)
    outcome = runner.clear(fake_uiapp(document), client=FakeClient([session]))
    assert outcome["cleared"] == 2
    assert seen == {"doc": document, "view": view, "ids": ["u1", "u2"]}
    assert outcome["message"] == "DG cleared the mapping colours of 2 elements"
    # the poll loop must not repaint what was just cleared
    assert store.get("lastDigest") == "painted"


def test_clear_finds_the_colours_in_the_view_when_dg_cannot_be_read(
        runner, store, dg_client, revit_io, monkeypatch, element_ids):
    signed_in(store)
    document = FakeDocument()
    view = with_session_document(store, document)
    monkeypatch.setattr(revit_io, "palette_overridden_ids",
                        lambda doc, scanned_view: ["u7"] if scanned_view is view else [])
    seen = recording_clear(revit_io, monkeypatch)
    client = FakeClient([dg_client.DgClientError("UNREACHABLE", "DG is down")])
    outcome = runner.clear(fake_uiapp(document), client=client)
    assert outcome["cleared"] == 1
    assert seen["ids"] == ["u7"]
    assert "found by colour in the view" in outcome["message"]
    assert "DG is down" in outcome["message"]
    assert "dgk_session-token" not in outcome["message"]


def test_clear_never_touches_another_document(runner, store, revit_io, monkeypatch,
                                              element_ids):
    """The session's document is closed and another one is active: nothing is cleared."""
    signed_in(store)
    with_session_document(store, FakeDocument())
    other = FakeDocument(title="Other", path="C:\\p\\other.rvt", guid="guid-2")
    other.elements[900] = FakeView(900)  # same view id, other document
    seen = recording_clear(revit_io, monkeypatch)
    outcome = runner.clear(fake_uiapp(other), client=FakeClient([]))
    assert outcome["cleared"] == 0
    assert "not open" in outcome["message"]
    assert seen == {}


# --- revit_io: element rows -----------------------------------------------------------

class FakeRevitParam(object):
    def __init__(self, name, storage, value=None, display=None):
        self.Definition = SimpleNamespace(Name=name)
        self.StorageType = storage
        self.HasValue = True
        self._value = value
        self._display = display

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
        return None


class BrokenParam(object):
    @property
    def Definition(self):
        raise RuntimeError("broken definition")


class FakeRevitElement(object):
    def __init__(self, unique_id, element_id, category="Generic Models", params=()):
        self.UniqueId = unique_id
        self.Id = FakeId(element_id)
        self.Category = FakeCategory(name=category) if category else None
        self._params = list(params)

    def GetTypeId(self):
        return None

    def GetOrderedParameters(self):
        return list(self._params)


def test_element_row_reads_the_contract_shape(runner, revit_io):
    revit_element = FakeRevitElement("uid-101", 101, "Generic Models", [
        FakeRevitParam("Mark", "String", "G-1", "G-1"),
        FakeRevitParam("Count", "Integer", 3, "3"),
        BrokenParam(),
    ])
    row = revit_io.element_row(FakeDocument(), revit_element)
    assert row["uniqueId"] == "uid-101"
    assert row["elementId"] == 101
    assert row["category"] == "Generic Models"
    assert row["family"] == ""
    assert row["typeName"] == ""
    assert row["adaptivePointCount"] is None
    assert row["skippedParameters"] == 1  # the broken one was skipped, not raised
    names = [parameter["name"] for parameter in row["parameters"]]
    assert names == ["Mark", "Count"]
    assert row["parameters"][0] == {"name": "Mark", "storageType": "String", "unit": "",
                                    "displayValue": "G-1", "value": "G-1"}
    assert row["parameters"][1]["value"] == 3


def test_read_rows_skips_unreadable_elements(runner, revit_io):
    good = FakeRevitElement("uid-a", 1)
    rows, skipped = revit_io.read_rows(FakeDocument(), [good, None, "not an element"])
    assert [row["uniqueId"] for row in rows] == ["uid-a"]
    assert skipped == 2


# --- fake Revit API for the writers ----------------------------------------------------

class FakeTransactionStatus(object):
    Started = "started"
    Committed = "Committed"


class FakeTransaction(object):
    instances = []

    def __init__(self, doc, name):
        self.doc = doc
        self.name = name
        self.status = None
        self.committed = False
        self.rolled_back = False
        FakeTransaction.instances.append(self)

    def Start(self):
        self.status = FakeTransactionStatus.Started

    def Commit(self):
        self.status = FakeTransactionStatus.Committed
        self.committed = True
        return self.status

    def RollBack(self):
        self.status = "rolledback"
        self.rolled_back = True

    def GetStatus(self):
        return self.status


class FakeColor(object):
    def __init__(self, red, green, blue):
        self.Red = red
        self.Green = green
        self.Blue = blue


class FakeOverride(object):
    def __init__(self):
        self.surface_pattern = None
        self.cut_pattern = None
        self.surface_colour = None
        self.cut_colour = None
        self.projection_colour = None

    def SetSurfaceForegroundPatternId(self, value):
        self.surface_pattern = value

    def SetCutForegroundPatternId(self, value):
        self.cut_pattern = value

    def SetSurfaceForegroundPatternColor(self, value):
        self.surface_colour = value

    def SetCutForegroundPatternColor(self, value):
        self.cut_colour = value

    def SetProjectionLineColor(self, value):
        self.projection_colour = value


class FakePattern(object):
    def __init__(self, element_id=555, solid=True):
        self.Id = FakeId(element_id)
        self._solid = solid

    def GetFillPattern(self):
        return SimpleNamespace(IsSolidFill=self._solid)


class FakeDB(object):
    """The slice of ``pyrevit.DB`` the writers use."""

    Transaction = FakeTransaction
    TransactionStatus = FakeTransactionStatus
    Color = FakeColor
    OverrideGraphicSettings = FakeOverride
    GroupTypeId = SimpleNamespace(Data="data")
    FillPatternElement = "FillPatternElement"

    def __init__(self, patterns=None):
        self.patterns = list(patterns if patterns is not None else [FakePattern()])

    def FilteredElementCollector(self, doc):
        patterns = self.patterns

        class Collector(object):
            def OfClass(self, cls):
                return patterns

        return Collector()


class FakeColourElement(object):
    def __init__(self, unique_id, element_id):
        self.UniqueId = unique_id
        self.Id = FakeId(element_id)


class FakeColourDocument(object):
    def __init__(self, elements):
        self.elements = dict((element.UniqueId, element) for element in elements)

    def GetElement(self, key):
        return self.elements.get(key)


class FakeColourView(object):
    def __init__(self):
        self.overrides = {}

    def SetElementOverrides(self, element_id, settings):
        self.overrides[element_id.Value] = settings


def test_apply_colours_uses_the_palette_in_one_transaction(runner, revit_io, monkeypatch):
    from dg_connector import palette
    FakeTransaction.instances = []
    monkeypatch.setattr(revit_io, "DB", FakeDB([FakePattern(555)]))
    document = FakeColourDocument([FakeColourElement("uid-a", 11),
                                   FakeColourElement("uid-b", 12)])
    view = FakeColourView()

    coloured = revit_io.apply_colours(document, view, {"uid-a": "confirmed",
                                                       "uid-b": "ambiguous"})
    assert coloured == 2
    assert [transaction.name for transaction in FakeTransaction.instances] == [
        "DG mapping colours"]
    assert FakeTransaction.instances[0].committed is True
    settings = view.overrides[11]
    assert (settings.surface_colour.Red, settings.surface_colour.Green,
            settings.surface_colour.Blue) == palette.STATE_COLOURS["confirmed"]
    assert settings.surface_pattern is not None
    assert settings.cut_pattern is not None
    # Lines keep the view's black so painted elements do not merge (F-04).
    assert settings.projection_colour is None


def test_apply_colours_counts_a_failing_element(runner, revit_io, monkeypatch):
    FakeTransaction.instances = []
    monkeypatch.setattr(revit_io, "DB", FakeDB())

    class BrokenView(object):
        def SetElementOverrides(self, element_id, settings):
            raise RuntimeError("view is locked")

    document = FakeColourDocument([FakeColourElement("uid-a", 11)])
    assert revit_io.apply_colours(document, BrokenView(), {"uid-a": "confirmed"}) == 0
    assert FakeTransaction.instances[0].committed is True  # the batch still commits


def test_clear_colours_clears_in_one_transaction(runner, revit_io, monkeypatch):
    FakeTransaction.instances = []
    monkeypatch.setattr(revit_io, "DB", FakeDB())
    document = FakeColourDocument([FakeColourElement("uid-a", 11),
                                   FakeColourElement("uid-b", 12)])
    view = FakeColourView()
    assert revit_io.clear_colours(document, view, ["uid-a", "uid-gone", "uid-b"]) == 2
    assert [transaction.name for transaction in FakeTransaction.instances] == [
        "DG mapping colours (clear)"]
    assert isinstance(view.overrides[11], FakeOverride)


def test_show_elements_selects_and_reports_missing(runner, revit_io):
    document = FakeColourDocument([FakeColourElement("uid-a", 11),
                                   FakeColourElement("uid-b", 12)])
    selected = {}

    class FakeSelection(object):
        def SetElementIds(self, element_ids):
            selected["ids"] = list(element_ids)

    shown = {}

    class FakeUidoc(object):
        Selection = FakeSelection()

        def ShowElements(self, element_ids):
            shown["ids"] = list(element_ids)

    result = revit_io.show_elements(FakeUidoc(), document, ["uid-a", "uid-gone", "uid-b"])
    assert result["found"] == 2
    assert result["shown"] == 2
    assert result["missing"] == ["uid-gone"]
    assert [element_id.Value for element_id in selected["ids"]] == [11, 12]
    assert [element_id.Value for element_id in shown["ids"]] == [11, 12]


def test_show_elements_without_a_uidoc_only_resolves(runner, revit_io):
    document = FakeColourDocument([FakeColourElement("uid-a", 11)])
    result = revit_io.show_elements(None, document, ["uid-a", "uid-gone"])
    assert result == {"found": 1, "shown": 0, "missing": ["uid-gone"]}


# --- write_parameters ---------------------------------------------------------------

class FakeSharedDefinition(object):
    def __init__(self, name):
        self.Name = name


class FakeDefinitions(object):
    def __init__(self, names):
        self._items = dict((name, FakeSharedDefinition(name)) for name in names)

    def get_Item(self, name):
        if name not in self._items:
            raise KeyError(name)
        return self._items[name]


class FakeSharedGroup(object):
    def __init__(self, name, definition_names):
        self.Name = name
        self.Definitions = FakeDefinitions(definition_names)


class FakeSharedGroups(object):
    def __init__(self, groups):
        self._groups = groups

    def get_Item(self, name):
        if name not in self._groups:
            raise KeyError(name)
        return self._groups[name]


class FakeDefinitionFile(object):
    def __init__(self, definition_names=("DG_Class", "DG_MappingState")):
        self.Groups = FakeSharedGroups({
            "DG": FakeSharedGroup("DG", definition_names),
        })


class FakeCategorySet(object):
    def __init__(self):
        self.categories = []

    def Insert(self, category):
        self.categories.append(category)
        return True


class FakeCreate(object):
    def NewCategorySet(self):
        return FakeCategorySet()

    def NewInstanceBinding(self, category_set):
        return SimpleNamespace(categories=category_set.categories)


class FakeApplication(object):
    def __init__(self, definition_names=("DG_Class", "DG_MappingState")):
        self.SharedParametersFilename = "C:\\users\\own-shared.txt"
        self.definition_names = definition_names
        self.opened = []
        self.Create = FakeCreate()

    def OpenSharedParameterFile(self):
        self.opened.append(self.SharedParametersFilename)
        return FakeDefinitionFile(self.definition_names)


class FakeTextParameter(object):
    def __init__(self):
        self.value = None

    def Set(self, value):
        self.value = value
        return True


class FakeWritableElement(object):
    def __init__(self, unique_id, element_id, category):
        self.UniqueId = unique_id
        self.Id = FakeId(element_id)
        self.Category = category
        self.parameters = {"DG_Class": FakeTextParameter(),
                           "DG_MappingState": FakeTextParameter()}

    def LookupParameter(self, name):
        return self.parameters.get(name)


class FakeBindingsIterator(object):
    def __init__(self, bindings):
        self._bindings = bindings
        self._index = -1

    def Reset(self):
        self._index = -1

    def MoveNext(self):
        self._index += 1
        return self._index < len(self._bindings)

    @property
    def Key(self):
        return self._bindings[self._index][0]

    @property
    def Current(self):
        return self._bindings[self._index][1]


class FakeParameterBindings(object):
    def __init__(self):
        self.bindings = []
        self.inserted = []
        self.reinserted = []

    def ForwardIterator(self):
        return FakeBindingsIterator(self.bindings)

    def Insert(self, definition, binding, group):
        self.inserted.append((definition.Name, binding, group))
        self.bindings.append((definition, binding))
        return True

    def ReInsert(self, definition, binding, group):
        self.reinserted.append((definition.Name, binding, group))
        self.bindings.append((definition, binding))
        return True


class FakeWritableDocument(object):
    def __init__(self, elements):
        self.elements = dict((element.UniqueId, element) for element in elements)
        self.ParameterBindings = FakeParameterBindings()

    def GetElement(self, key):
        return self.elements.get(key)


def writable_elements():
    category = FakeCategory("Generic Models", category_id=1)
    return FakeWritableElement("uid-a", 11, category), FakeWritableElement("uid-b", 12, category)


def test_write_parameters_binds_and_sets_the_two_parameters(runner, revit_io, monkeypatch):
    FakeTransaction.instances = []
    monkeypatch.setattr(revit_io, "DB", FakeDB())
    first, second = writable_elements()
    document = FakeWritableDocument([first, second])
    application = FakeApplication()
    shared_file = os.path.join(APP_ROOT, "DG_SharedParameters.txt")

    result = revit_io.write_parameters(
        document, application, shared_file,
        {"uid-a": ["GlassPanel", "Panel"], "uid-b": []},
        {"uid-a": "confirmed", "uid-b": "auto"})

    assert result == {"written": 2, "skipped": 0, "categories": 1}
    # the user's own shared-parameter file is restored, whatever happened
    assert application.SharedParametersFilename == "C:\\users\\own-shared.txt"
    assert application.opened == [shared_file]
    assert [name for name, _binding, _group in document.ParameterBindings.inserted] == [
        "DG_Class", "DG_MappingState"]
    assert [group for _name, _binding, group in document.ParameterBindings.inserted] == [
        "data", "data"]
    assert first.parameters["DG_Class"].value == "GlassPanel;Panel"
    assert first.parameters["DG_MappingState"].value == "confirmed"
    assert second.parameters["DG_Class"].value == ""
    assert second.parameters["DG_MappingState"].value == "auto"
    assert [transaction.name for transaction in FakeTransaction.instances] == [
        "DG mapping parameters"]
    assert FakeTransaction.instances[0].committed is True


def test_write_parameters_skips_elements_without_the_parameters(runner, revit_io, monkeypatch):
    FakeTransaction.instances = []
    monkeypatch.setattr(revit_io, "DB", FakeDB())
    first, second = writable_elements()
    second.parameters = {}  # the parameter is not bound for this element
    document = FakeWritableDocument([first, second])

    result = revit_io.write_parameters(
        document, FakeApplication(), "C:\\ext\\DG_SharedParameters.txt",
        {"uid-b": ["Panel"]}, {"uid-a": "confirmed", "uid-b": "auto"})
    assert result == {"written": 1, "skipped": 1, "categories": 1}


def test_atomic_write_requires_a_terminal_committed_transaction(runner, revit_io, monkeypatch):
    FakeTransaction.instances = []
    monkeypatch.setattr(revit_io, "DB", FakeDB())
    first, second = writable_elements()
    result = revit_io.write_parameters(
        FakeWritableDocument([first, second]), FakeApplication(), "C:\\ext\\DG_SharedParameters.txt",
        {"uid-a": ["Panel"]}, {"uid-a": "confirmed"}, atomic=True)
    assert result["written"] == 1 and result["skipped"] == 0
    assert FakeTransaction.instances[-1].committed
    assert second.parameters["DG_Class"].value is None


@pytest.mark.parametrize("missing", ["element", "parameter"])
def test_atomic_write_rolls_back_instead_of_partially_committing(
        runner, revit_io, monkeypatch, missing):
    FakeTransaction.instances = []
    monkeypatch.setattr(revit_io, "DB", FakeDB())
    first, second = writable_elements()
    if missing == "parameter":
        second.parameters = {}
    document = FakeWritableDocument([first] if missing == "element" else [first, second])
    with pytest.raises(RuntimeError, match="could not be written in full"):
        revit_io.write_parameters(document, FakeApplication(), "C:\\ext\\DG_SharedParameters.txt",
                                  {}, {"uid-a": "confirmed", "uid-b": "confirmed"}, atomic=True)
    transaction = FakeTransaction.instances[-1]
    assert transaction.rolled_back and not transaction.committed
    # These stubs verify transaction calls, not Revit's in-memory rollback implementation.


@pytest.mark.parametrize("status", ["RolledBack", "Pending"])
def test_atomic_write_does_not_report_noncommitted_status_as_success(
        runner, revit_io, monkeypatch, status):
    class NonCommittedTransaction(FakeTransaction):
        def Commit(self):
            self.status = status
            return status

    FakeTransaction.instances = []
    db = FakeDB()
    db.Transaction = NonCommittedTransaction
    monkeypatch.setattr(revit_io, "DB", db)
    first, _second = writable_elements()
    error = revit_io.TransactionPendingError if status == "Pending" else RuntimeError
    with pytest.raises(error):
        revit_io.write_parameters(FakeWritableDocument([first]), FakeApplication(),
                                  "C:\\ext\\DG_SharedParameters.txt", {},
                                  {"uid-a": "confirmed"}, atomic=True)
    assert FakeTransaction.instances[-1].rolled_back is (status != "Pending")


def test_write_parameters_restores_the_file_when_a_definition_is_missing(
        runner, revit_io, monkeypatch):
    FakeTransaction.instances = []
    monkeypatch.setattr(revit_io, "DB", FakeDB())
    first, _second = writable_elements()
    document = FakeWritableDocument([first])
    application = FakeApplication(definition_names=("DG_Class",))
    with pytest.raises(RuntimeError) as info:
        revit_io.write_parameters(document, application, "C:\\ext\\DG_SharedParameters.txt",
                                  {}, {"uid-a": "confirmed"})
    assert "DG_MappingState" in str(info.value)
    assert application.SharedParametersFilename == "C:\\users\\own-shared.txt"
    assert FakeTransaction.instances == []  # nothing was written


def test_write_parameters_needs_a_shared_parameter_file(runner, revit_io):
    document = FakeWritableDocument([])
    with pytest.raises(ValueError):
        revit_io.write_parameters(document, FakeApplication(), None, {}, {"u": "auto"})


class FakeBinding(object):
    """An existing InstanceBinding: Revit exposes its CategorySet as ``Categories``."""

    def __init__(self, categories):
        self.Categories = list(categories)


def test_rebinding_widens_and_never_narrows_an_existing_binding(runner, revit_io, monkeypatch):
    """Built-in categories are not Elements: the union must come from the binding."""
    monkeypatch.setattr(revit_io, "DB", FakeDB())
    walls = FakeCategory("Walls", category_id=-2000011)
    generic = FakeCategory("Generic Models", category_id=-2000151)
    document = FakeWritableDocument([])
    definition = FakeSharedDefinition("DG_Class")
    document.ParameterBindings.bindings.append((definition, FakeBinding([walls])))

    assert revit_io.bind_definition(document, FakeApplication(), definition, [generic]) is True
    assert document.ParameterBindings.inserted == []
    (name, binding, group), = document.ParameterBindings.reinserted
    assert name == "DG_Class" and group == "data"
    assert [category.Name for category in binding.categories] == ["Walls", "Generic Models"]


def test_binding_is_left_alone_when_every_category_is_bound(runner, revit_io, monkeypatch):
    monkeypatch.setattr(revit_io, "DB", FakeDB())
    generic = FakeCategory("Generic Models", category_id=-2000151)
    document = FakeWritableDocument([])
    definition = FakeSharedDefinition("DG_MappingState")
    document.ParameterBindings.bindings.append((definition, FakeBinding([generic])))

    same = FakeCategory("Generic Models", category_id=-2000151)
    assert revit_io.bind_definition(document, FakeApplication(), definition, [same]) is True
    assert document.ParameterBindings.inserted == []
    assert document.ParameterBindings.reinserted == []


def test_writer_transactions_never_open_a_failure_dialog(runner, revit_io, monkeypatch):
    seen = {}

    class Options(object):
        def SetForcedModalHandling(self, value):
            seen["modal"] = value

        def SetClearAfterRollback(self, value):
            seen["clear"] = value

        def SetFailuresPreprocessor(self, value):
            seen["preprocessor"] = value

    class QuietTransaction(FakeTransaction):
        def GetFailureHandlingOptions(self):
            return Options()

        def SetFailureHandlingOptions(self, options):
            seen["set"] = True

    fake_db = FakeDB()
    fake_db.Transaction = QuietTransaction
    monkeypatch.setattr(revit_io, "DB", fake_db)
    document = FakeColourDocument([FakeColourElement("uid-a", 11)])
    assert revit_io.apply_colours(document, FakeColourView(), {"uid-a": "auto"}) == 1
    assert seen["modal"] is False and seen["clear"] is True and seen["set"] is True
    assert isinstance(seen["preprocessor"], revit_io._QuietFailures)


class FakeOverridesView(object):
    """A view whose overrides are read back (``GetElementOverrides``)."""

    def __init__(self, colours):
        self.Id = FakeId(900)
        self._colours = colours

    def GetElementOverrides(self, element_id):
        colour = self._colours.get(element_id.Value)
        return SimpleNamespace(SurfaceForegroundPatternColor=colour)


def test_palette_overridden_ids_finds_only_dg_colours(runner, revit_io, monkeypatch):
    from dg_connector import palette

    elements = [FakeColourElement("uid-dg", 11), FakeColourElement("uid-user", 12),
                FakeColourElement("uid-plain", 13)]

    class ViewDB(FakeDB):
        def FilteredElementCollector(self, doc, view_id=None):
            class Collector(object):
                def WhereElementIsNotElementType(self):
                    return elements

            return Collector()

    monkeypatch.setattr(revit_io, "DB", ViewDB())

    def colour(rgb, valid=True):
        return SimpleNamespace(Red=rgb[0], Green=rgb[1], Blue=rgb[2], IsValid=valid)

    view = FakeOverridesView({
        11: colour(palette.STATE_COLOURS["ambiguous"]),
        12: colour((1, 2, 3)),                       # the user's own override
        13: colour((0, 0, 0), valid=False),           # no override at all
    })
    assert revit_io.palette_overridden_ids(FakeColourDocument(elements), view) == ["uid-dg"]
    assert revit_io.palette_overridden_ids(None, view) == []


def test_a_profile_batch_writes_auto_mapping_state():
    """Owner 2026-10-20: elements an active profile classified must get DG_Class and DG_MappingState too; the
    state written for a profile batch is 'auto', for a human confirmation 'confirmed'."""
    import inspect
    from dg_connector import runner

    source = inspect.getsource(runner._apply)
    assert 'state = "auto" if batch.get("source") == "profile" else "confirmed"' in source
    assert '"state": state,' in source
