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
