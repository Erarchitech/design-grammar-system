"""Phase 1303-24 (D-67): one run_property_check per request, no blind retry after BUSY, a poll for the end of a long
solution, and a refusal to start while SendValid is already on (live 2026-10-25: BUSY retries queued further
solutions, the status was read mid-solution, and a SendValid left True published 50 runs in 54 minutes)."""

from __future__ import annotations

import os
import sys

import pytest
from fastapi import HTTPException

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import app as app_module  # noqa: E402
import gh_bridge  # noqa: E402


def _busy():
    return HTTPException(status_code=502, detail={"error": "Canvas UI thread did not respond within 10000 ms (busy).",
                                                  "hint": "x", "code": "BUSY"})


def _request(**kw):
    return app_module.PropertyCheckRunRequest(project="p", refresh=False, **kw)


class _Bridge:
    """Scripted listener: run answers and status answers in order; every call is recorded."""

    def __init__(self, monkeypatch, run, statuses):
        self.runs = []
        self.status_calls = 0
        self._run = run
        self._statuses = list(statuses)
        monkeypatch.setattr(gh_bridge, "run_property_check", self.run_property_check)
        monkeypatch.setattr(gh_bridge, "get_property_check_status", self.get_property_check_status)

    def run_property_check(self, params):
        self.runs.append(dict(params))
        if isinstance(self._run, Exception):
            raise self._run
        return dict(self._run)

    def get_property_check_status(self, project):
        self.status_calls += 1
        item = self._statuses.pop(0) if len(self._statuses) > 1 else self._statuses[0]
        if isinstance(item, Exception):
            raise item
        return item


@pytest.fixture(autouse=True)
def _quiet(monkeypatch):
    monkeypatch.setattr(app_module, "CHECK_POLL_S", 0)

    class NoThread:
        def __init__(self, target, args, daemon):
            pass

        def start(self):
            pass

    monkeypatch.setattr(app_module.threading, "Thread", NoThread)
    monkeypatch.setattr(app_module, "PUBLISH_POLL_S", 0)
    monkeypatch.setattr(app_module, "_publish_check_context", lambda project, runs: None)


IDLE = {"toggles": {"Run": True, "SendValid": False, "Paint": False, "Clear": False}, "solutionsEnded": 4}


def test_busy_is_answered_with_503_and_never_with_a_second_run(monkeypatch):
    bridge = _Bridge(monkeypatch, _busy(), [IDLE])
    with pytest.raises(HTTPException) as err:
        app_module.post_property_check_run(_request(send=False), request=None)
    assert err.value.status_code == 503 and err.value.detail["code"] == "CANVAS_BUSY"
    assert len(bridge.runs) == 1


def test_the_old_blind_retry_helper_is_gone():
    assert not hasattr(app_module, "_run_check_retrying_busy")
    assert not hasattr(app_module, "BUSY_ATTEMPTS")


def test_a_check_is_refused_while_sendvalid_is_already_on(monkeypatch):
    armed = {"toggles": {"SendValid": True}, "solutionsEnded": 1}
    bridge = _Bridge(monkeypatch, {"finished": True}, [armed])
    with pytest.raises(HTTPException) as err:
        app_module.post_property_check_run(_request(), request=None)
    assert err.value.status_code == 409 and err.value.detail["code"] == "SEND_VALID_ARMED"
    assert bridge.runs == []


def test_a_busy_canvas_before_the_run_starts_nothing(monkeypatch):
    bridge = _Bridge(monkeypatch, {"finished": True}, [_busy()])
    with pytest.raises(HTTPException) as err:
        app_module.post_property_check_run(_request(send=False), request=None)
    assert err.value.status_code == 503 and err.value.detail["code"] == "CANVAS_BUSY"
    assert bridge.runs == []


def test_an_unreachable_listener_before_the_run_is_left_to_the_run_itself(monkeypatch):
    gone = HTTPException(status_code=503, detail={"error": "x", "hint": "y", "code": "GH_BRIDGE_UNREACHABLE"})
    bridge = _Bridge(monkeypatch, gone, [gone])
    with pytest.raises(HTTPException) as err:
        app_module.post_property_check_run(_request(send=False), request=None)
    assert err.value.detail["code"] == "GH_BRIDGE_UNREACHABLE" and len(bridge.runs) == 1


def test_a_long_solution_is_polled_until_its_counter_moves(monkeypatch):
    run = {"finished": False, "send": False, "clear": False, "paint": True, "status": None, "solutionsEndedBefore": 4}
    done = {"toggles": {"SendValid": False}, "solutionsEnded": 5, "boxes": 313, "violations": [],
            "validationRunId": [], "messages": []}
    bridge = _Bridge(monkeypatch, run, [IDLE, _busy(), _busy(), done])
    out = app_module.post_property_check_run(_request(send=False), request=None)
    assert len(bridge.runs) == 1 and bridge.status_calls == 4  # guard read + two BUSY polls + the answer
    assert out["finished"] is True and out["status"]["boxes"] == 313 and out["summary"]["ok"] is True


def test_a_poll_that_never_sees_the_end_leaves_the_check_unfinished_and_not_ok(monkeypatch):
    run = {"finished": False, "send": False, "clear": False, "paint": True, "status": None, "solutionsEndedBefore": 4}
    bridge = _Bridge(monkeypatch, run, [IDLE, _busy()])
    with pytest.raises(HTTPException) as err:
        app_module.post_property_check_run(_request(send=False), request=None)
    assert err.value.status_code == 422 and err.value.detail["code"] == "PROPERTY_CHECK_FAILED"
    assert "did not finish" in " ".join(err.value.detail["problems"])
    assert bridge.status_calls == 1 + app_module.CHECK_POLL_ATTEMPTS
    assert len(bridge.runs) == 1


def test_a_listener_without_the_counter_is_not_polled(monkeypatch):
    run = {"finished": False, "send": False, "clear": False, "paint": True,
           "status": {"boxes": 2, "violations": [], "validationRunId": [], "messages": []}}
    bridge = _Bridge(monkeypatch, run, [IDLE])
    with pytest.raises(HTTPException) as err:
        app_module.post_property_check_run(_request(send=False), request=None)
    assert bridge.status_calls == 1  # the guard read only: no poll without the counter
    assert "did not finish" in " ".join(err.value.detail["problems"])


def test_the_end_of_a_run_is_its_verdict_not_the_first_solution_end(monkeypatch):
    """Phase 1303-25 (D-70), live 2026-10-25: after a fresh placement the first solution had no rules (METAGRAPH loads
    asynchronously); the listener keeps the one-shot armed (oneShotPending) until the solution with the verdict."""
    run = {"finished": False, "send": False, "clear": False, "paint": True, "status": None, "solutionsEndedBefore": 4}
    no_rules = {"toggles": {"SendValid": False}, "solutionsEnded": 5, "oneShotPending": True, "boxes": 313,
                "violations": [], "validationRunId": [], "messages": ["error VALIDATOR: Rule input is required."]}
    verdict = {"toggles": {"SendValid": False}, "solutionsEnded": 6, "oneShotPending": False, "boxes": 313,
               "violations": [], "validationRunId": [], "messages": []}
    bridge = _Bridge(monkeypatch, run, [IDLE, no_rules, verdict])
    out = app_module.post_property_check_run(_request(send=False), request=None)
    assert len(bridge.runs) == 1 and bridge.status_calls == 3
    assert out["finished"] is True and out["status"]["solutionsEnded"] == 6 and out["summary"]["ok"] is True


def test_the_status_is_read_again_once_the_published_runs_are_found(monkeypatch):
    """Phase 1303-25 (D-70): the status the run answered can be older than the publishing solution; a stale error
    must not fail a check whose runs were published."""
    stale = {"boxes": 313, "violations": [], "validationRunId": ["", ""], "ruleNames": ["R1", "R2"],
             "messages": ["error VALIDATOR: Rule input is required."]}
    run = {"finished": True, "send": True, "clear": False, "paint": True, "status": stale, "solutionsEndedBefore": 4}
    fresh = {"toggles": {"SendValid": False}, "solutionsEnded": 7, "oneShotPending": False, "boxes": 313,
             "violations": [], "validationRunId": ["", ""], "ruleNames": ["R1", "R2"], "messages": []}
    bridge = _Bridge(monkeypatch, run, [IDLE, fresh])
    monkeypatch.setattr(app_module, "read_many", lambda query, params=None: [{"runId": "VR-1"}, {"runId": "VR-2"}])
    monkeypatch.setattr(app_module, "_record_check_source", lambda project, runs, report: None)
    out = app_module.post_property_check_run(_request(), request=None)
    assert out["summary"]["ok"] is True and out["summary"]["validationRunIds"] == ["VR-1", "VR-2"]
    assert out["status"]["solutionsEnded"] == 7 and len(bridge.runs) == 1


def test_after_a_fresh_placement_the_check_waits_for_the_placement_solution(monkeypatch):
    """Live 2026-10-25 16:45: the chain was placed with a newly generated calculator, the placement's solution was still
    running, the pre-run read answered BUSY and the check returned 503 without running. After a placement only the
    status READ is repeated until the canvas is free; the run itself is still sent once."""
    generated = {"calculator": {"sha256": "new"}, "placement": {}, "highlighter": {"sha256": "h"}}
    monkeypatch.setattr(app_module, "_generate_property_scripts", lambda payload, **kw: generated)
    monkeypatch.setattr(app_module, "_mapping_actor", lambda request: "tester")
    placed = []
    monkeypatch.setattr(app_module, "_place_property_scripts", lambda project, gen: placed.append(project) or {"ok": True})
    run = {"finished": True, "send": False, "clear": False, "paint": True,
           "status": {"boxes": 313, "violations": [], "validationRunId": [], "messages": []}}
    bridge = _Bridge(monkeypatch, run, [IDLE, _busy(), _busy(), IDLE])
    out = app_module.post_property_check_run(app_module.PropertyCheckRunRequest(project="p", send=False), request=None)
    assert placed == ["p"] and len(bridge.runs) == 1
    assert bridge.status_calls == 4  # canvas sha read, two BUSY reads while the placement solves, the free read
    assert out["finished"] is True and out["refreshed"] == {"ok": True}


def test_a_placement_solution_that_never_ends_is_answered_with_503_and_no_run(monkeypatch):
    generated = {"calculator": {"sha256": "new"}, "placement": {}, "highlighter": {"sha256": "h"}}
    monkeypatch.setattr(app_module, "_generate_property_scripts", lambda payload, **kw: generated)
    monkeypatch.setattr(app_module, "_mapping_actor", lambda request: "tester")
    monkeypatch.setattr(app_module, "_place_property_scripts", lambda project, gen: {"ok": True})
    bridge = _Bridge(monkeypatch, {"finished": True}, [IDLE, _busy()])
    with pytest.raises(HTTPException) as err:
        app_module.post_property_check_run(app_module.PropertyCheckRunRequest(project="p", send=False), request=None)
    assert err.value.status_code == 503 and err.value.detail["code"] == "CANVAS_BUSY"
    assert bridge.runs == [] and bridge.status_calls == 1 + app_module.CHECK_POLL_ATTEMPTS
