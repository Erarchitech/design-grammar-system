"""F-01 (2026-10-29): rule-check jobs DG queues for this sign-in, pulled by the poll thread, run in Revit by the
ExternalEvent handler and answered from a background thread. Offline: the Revit API and DG are faked."""

import importlib
from types import SimpleNamespace

import pytest

from test_runner import FakeDocument, fake_uiapp, signed_in  # noqa: F401 - fixtures below
from test_runner import runner, store, revit_io  # noqa: F401

PROGRAM = '''
def run(doc, family_filter, with_context):
    return {"document": doc.Title, "properties": [], "report": ["filter %s" % family_filter],
            "boxes": [{"uniqueId": "u1", "label": "Box [1]", "values": [1], "mesh": None}],
            "context": [{"label": "OST_Walls|w %d" % i, "geometry": None} for i in range(7)] if with_context else []}
'''


class JobClient(object):
    def __init__(self, job=None):
        self.job = job
        self.results = []
        self.contexts = []
        self.next_calls = 0

    def next_job(self, url, token, project):
        self.next_calls += 1
        job, self.job = self.job, None
        return {"job": job}

    def post_job_result(self, url, token, project, job_id, ok, result, error):
        self.results.append((token, project, job_id, ok, result, error))
        return {"status": "done"}

    def post_job_context(self, url, token, project, job_id, elements, done):
        self.contexts.append((len(elements), done))
        return {}

    def get_session(self, *args):
        raise AssertionError("no mapping session is open")


@pytest.fixture()
def check_jobs(runner):  # noqa: F811
    return importlib.import_module("dg_connector.check_jobs")


def _entry(check_jobs, store, kind="check", payload=None):  # noqa: F811
    job = {"id": "job-1", "project": "str-openings-01", "kind": kind,
           "payload": payload if payload is not None else {"script": PROGRAM, "boxFamilyFilter": "Box",
                                                            "withContext": True}}
    return {"kind": check_jobs.JOB_KIND, "job": job, "tokenKey": check_jobs.token_key(store.get("token")),
            "url": "http://localhost:8000", "project": "str-openings-01"}


def test_the_poll_queues_a_job_even_without_a_mapping_session(runner, store, check_jobs):  # noqa: F811
    signed_in(store, project="str-openings-01", session_id=None)
    client = JobClient({"id": "job-1", "kind": "check", "payload": {}})
    runner.poll_step(store=store, client=client)
    queued = runner.queued_jobs()
    assert client.next_calls == 1 and len(queued) == 1
    assert queued[0]["kind"] == check_jobs.JOB_KIND and queued[0]["job"]["id"] == "job-1"
    assert "token" not in queued[0] and queued[0]["tokenKey"] == check_jobs.token_key("dgk_session-token")


def test_an_older_client_without_jobs_is_left_alone(runner, store, check_jobs):  # noqa: F811
    signed_in(store, session_id=None)
    assert check_jobs.poll(store, SimpleNamespace(), lambda job: None, lambda: None) is None


def test_a_check_runs_the_program_in_revit_and_answers_values_then_context_chunks(store, check_jobs,  # noqa: F811
                                                                                   monkeypatch):
    signed_in(store, project="str-openings-01", session_id=None)
    monkeypatch.setattr(check_jobs, "CONTEXT_CHUNK", 3)
    entry = _entry(check_jobs, store)
    outcome = check_jobs.run(fake_uiapp(FakeDocument(title="DG-DemoProject-2-openings_R26")), entry, store)
    ok, result, error, context = outcome
    assert ok and error is None and "context" not in result
    assert result["document"] == "DG-DemoProject-2-openings_R26" and result["report"] == ["filter Box"]
    assert len(context) == 7
    client = JobClient()
    check_jobs.send_later(client, entry, outcome, store, start_thread=False)
    assert client.results[0][2:4] == ("job-1", True)
    assert client.contexts == [(3, False), (3, False), (1, True)]


def test_a_failing_program_is_answered_as_a_failure(store, check_jobs):  # noqa: F811
    signed_in(store, session_id=None)
    entry = _entry(check_jobs, store, payload={"script": "def run(doc, f, c):\n    raise ValueError('no walls')\n"})
    ok, result, error, context = check_jobs.run(fake_uiapp(FakeDocument()), entry, store)
    assert not ok and result is None and "no walls" in error
    client = JobClient()
    check_jobs.send(client, entry, (ok, result, error, context), store)
    assert client.results[0][3:] == (False, None, error) and client.contexts == []


def test_without_an_active_project_the_check_says_so(store, check_jobs):  # noqa: F811
    signed_in(store, session_id=None)
    ok, _result, error, _context = check_jobs.run(fake_uiapp(None), _entry(check_jobs, store), store)
    assert not ok and "open the model" in error


def test_a_job_of_an_earlier_sign_in_is_dropped(store, check_jobs):  # noqa: F811
    signed_in(store, session_id=None)
    entry = _entry(check_jobs, store)
    store.set("token", "dgk_new-sign-in")
    assert check_jobs.run(fake_uiapp(FakeDocument()), entry, store) is None
    client = JobClient()
    check_jobs.send(client, entry, (True, {}, None, []), store)
    assert client.results == []


def test_paint_and_clear_go_through_revit_io(store, check_jobs, revit_io, monkeypatch):  # noqa: F811
    signed_in(store, session_id=None)
    calls = []
    monkeypatch.setattr(revit_io, "apply_check_colours",
                        lambda doc, view, verdicts, app, shared: calls.append(("paint", sorted(verdicts))) or
                        {"violations": 1, "noVerdict": 0})
    monkeypatch.setattr(revit_io, "clear_check_colours",
                        lambda doc, view, ids: calls.append(("clear", sorted(ids))) or len(ids))
    verdicts = {"u1": {"broken": ["R1"], "open": []}, "u2": {"broken": [], "open": []}}
    uiapp = fake_uiapp(FakeDocument())
    assert check_jobs.run(uiapp, _entry(check_jobs, store, "paint", {"verdicts": verdicts}), store)[0]
    assert check_jobs.run(uiapp, _entry(check_jobs, store, "clear", {}), store)[0]
    assert calls == [("paint", ["u1", "u2"]), ("clear", ["u1", "u2"])]
    assert store.get(check_jobs.PAINTED_KEY) == ""


def test_the_handler_runs_a_check_job_and_answers_off_the_main_thread(runner, store, check_jobs,  # noqa: F811
                                                                      monkeypatch):
    signed_in(store, project="str-openings-01", session_id=None)
    sent = []
    monkeypatch.setattr(check_jobs, "send_later", lambda client, entry, outcome, st: sent.append(outcome[0]))
    runner._queue_job(_entry(check_jobs, store))
    assert runner.run_jobs(fake_uiapp(FakeDocument())) == 1
    assert sent == [True]


def test_the_handler_class_declares_a_dotnet_namespace_for_pythonnet(runner):  # noqa: F811
    assert runner._Handler.__namespace__ == "DG.RevitConnector"


def test_check_colours_fill_red_grey_green_keep_lines_black_and_write_dg_violation(revit_io, monkeypatch):  # noqa: F811
    from test_runner import FakeColourDocument, FakeColourElement, FakeColourView, FakeDB, FakePattern
    from test_runner import FakeTransaction

    class Element(FakeColourElement):
        def __init__(self, unique_id, element_id):
            FakeColourElement.__init__(self, unique_id, element_id)
            self.written = None
            self.GroupId = None

        def LookupParameter(self, name):
            element = self
            return SimpleNamespace(Set=lambda value: setattr(element, "written", (name, value)) or True)

    FakeTransaction.instances = []
    monkeypatch.setattr(revit_io, "DB", FakeDB([FakePattern(555)]))
    elements = [Element("u1", 1), Element("u2", 2), Element("u3", 3)]
    view = FakeColourView()
    report = revit_io.apply_check_colours(FakeColourDocument(elements), view, {
        "u1": {"broken": ["R1", "R2"], "open": []}, "u2": {"broken": [], "open": ["R1"]},
        "u3": {"broken": [], "open": []}, "gone": {"broken": ["R1"], "open": []}})
    colours = dict((k, (v.surface_colour.Red, v.surface_colour.Green, v.surface_colour.Blue))
                   for k, v in view.overrides.items())
    assert colours == {1: revit_io.CHECK_RED, 2: revit_io.CHECK_GREY, 3: revit_io.CHECK_GREEN}
    assert all(v.projection_colour is None for v in view.overrides.values())  # F-04: lines stay black
    assert elements[0].written == ("DG_Violation", "R1;R2") and elements[2].written == ("DG_Violation", "")
    assert report["violations"] == 1 and report["noVerdict"] == 1 and report["missing"] == 1
    assert [t.name for t in FakeTransaction.instances] == [revit_io.CHECK_TRANSACTION]


# --- Phase 1303-26 (D-79..D-81): the model snapshot of a confirmed mapping ---------------------------------------

SNAPSHOT_PROGRAM = '''
def snapshot(doc, unique_ids, categories):
    return {"document": doc.Title, "fingerprint": "f" * 64, "count": len(categories),
            "elements": [{"uniqueId": u, "revitId": i, "mesh": None} for i, u in enumerate(unique_ids)],
            "missing": []}
'''


def test_a_snapshot_job_answers_the_fingerprint_then_the_meshes_in_chunks(store, check_jobs,  # noqa: F811
                                                                           monkeypatch):
    signed_in(store, project="str-openings-01", session_id=None)
    monkeypatch.setattr(check_jobs, "CONTEXT_CHUNK", 2)
    entry = _entry(check_jobs, store, kind="snapshot",
                   payload={"script": SNAPSHOT_PROGRAM, "uniqueIds": ["a", "b", "c"], "categories": ["Walls"]})
    outcome = check_jobs.run(fake_uiapp(FakeDocument(title="Model")), entry, store)
    ok, result, error, elements = outcome
    assert ok and error is None
    assert result == {"document": "Model", "fingerprint": "f" * 64, "count": 1, "missing": []}
    assert [e["uniqueId"] for e in elements] == ["a", "b", "c"]
    client = JobClient()
    check_jobs.send_later(client, entry, outcome, store, start_thread=False)
    assert client.results[0][2:4] == ("job-1", True)
    assert client.contexts == [(2, False), (1, True)]


def test_a_check_passes_the_snapshot_categories_only_when_dg_sent_them(store, check_jobs):  # noqa: F811
    signed_in(store, project="str-openings-01", session_id=None)
    program = PROGRAM + '''
def run(doc, family_filter, with_context, categories=None):
    return {"document": doc.Title, "boxes": [], "categories": categories}
'''
    plain = _entry(check_jobs, store, payload={"script": program, "boxFamilyFilter": "", "withContext": False})
    asked = _entry(check_jobs, store, payload={"script": program, "boxFamilyFilter": "", "withContext": False,
                                               "snapshotCategories": ["Walls"]})
    assert check_jobs.run(fake_uiapp(FakeDocument()), plain, store)[1]["categories"] is None
    assert check_jobs.run(fake_uiapp(FakeDocument()), asked, store)[1]["categories"] == ["Walls"]
    # an older program with the three-argument run() still works when DG sends no categories
    old = _entry(check_jobs, store)
    assert check_jobs.run(fake_uiapp(FakeDocument()), old, store)[0] is True
