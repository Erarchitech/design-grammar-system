"""Jobs for the DG Revit connector: the server never calls a user's PC, the connector pulls (F-01, 2026-10-29).

On the multi-user stand data-service runs on the server, so host.docker.internal:8720 was the server itself and every
rule check from DeGram failed with GH_BRIDGE_UNREACHABLE. A check of a Revit model is now a job: data-service queues
it for the Revit connector of the user who asked (never another user's Revit), the connector picks it up on its poll
over HTTPS with its own dgk_ session, runs the property calculators natively in Revit and posts the values back.

Process memory only: data-service runs one uvicorn worker, a check lives seconds, and a job lost to a restart is
simply asked for again. A connector counts as present while it polled within ``ACTIVE_S``.
"""

from __future__ import annotations

import threading
import time
import uuid
from typing import Any

ACTIVE_S = 20.0
JOB_TTL_S = 15 * 60.0

QUEUED = "queued"
TAKEN = "taken"
DONE = "done"
FAILED = "failed"
EXPIRED = "expired"

_lock = threading.Condition()
_jobs: dict[str, dict] = {}
_seen: dict[tuple[str, str, str], float] = {}
_last_status: dict[str, dict] = {}


def _key(project: str, user: str, connector_id: str) -> tuple[str, str, str]:
    return (str(project), str(user or ""), str(connector_id or ""))


def _now() -> float:
    return time.monotonic()


def _prune(now: float) -> None:
    for job_id in [j for j, job in _jobs.items() if now - job["created"] > JOB_TTL_S]:
        _jobs.pop(job_id, None)


def touch(project: str, user: str, connector_id: str = "revit") -> None:
    with _lock:
        _seen[_key(project, user, connector_id)] = _now()


def active(project: str, user: str, connector_id: str = "revit") -> bool:
    """True while the user's connector for the project polled within ACTIVE_S."""
    with _lock:
        seen = _seen.get(_key(project, user, connector_id))
        return seen is not None and _now() - seen <= ACTIVE_S


def submit(project: str, user: str, kind: str, payload: dict, connector_id: str = "revit") -> dict:
    """Queue a job for the user's connector. A newer job of the same kind replaces a queued one not yet taken."""
    with _lock:
        now = _now()
        _prune(now)
        for job in _jobs.values():
            if (job["status"] == QUEUED and job["kind"] == kind
                    and _key(job["project"], job["user"], job["connector"]) == _key(project, user, connector_id)):
                job["status"] = EXPIRED
                job["error"] = "replaced by a newer request"
        job = {"id": uuid.uuid4().hex, "project": project, "user": user, "connector": connector_id, "kind": kind,
               "payload": payload, "status": QUEUED, "created": now, "taken": None, "result": None, "error": None,
               "context": [], "contextDone": False}
        _jobs[job["id"]] = job
        _lock.notify_all()
        return job


def take(project: str, user: str, connector_id: str = "revit") -> dict | None:
    """The oldest queued job of this connector, marked taken; also records the poll."""
    with _lock:
        now = _now()
        _seen[_key(project, user, connector_id)] = now
        _prune(now)
        mine = [j for j in _jobs.values() if j["status"] == QUEUED
                and _key(j["project"], j["user"], j["connector"]) == _key(project, user, connector_id)]
        if not mine:
            return None
        job = min(mine, key=lambda j: j["created"])
        job["status"] = TAKEN
        job["taken"] = now
        _lock.notify_all()
        return job


def get(job_id: str, project: str, user: str, connector_id: str = "revit") -> dict | None:
    """The job when it belongs to exactly this connector; None for an unknown or foreign job (no difference shown)."""
    with _lock:
        job = _jobs.get(job_id)
        if job is None or _key(job["project"], job["user"], job["connector"]) != _key(project, user, connector_id):
            return None
        return job


def complete(job: dict, ok: bool, result: Any = None, error: str | None = None) -> None:
    with _lock:
        if job["status"] in (DONE, FAILED, EXPIRED):
            return
        job["status"] = DONE if ok else FAILED
        job["result"] = result
        job["error"] = None if ok else (error or "the connector reported a failure")
        _lock.notify_all()


def add_context(job: dict, elements: list[dict], done: bool) -> None:
    with _lock:
        job["context"].extend(elements)
        if done:
            job["contextDone"] = True
        _lock.notify_all()


def wait(job: dict, timeout_s: float, until: str = "finished") -> bool:
    """Block until the job finished (``until="finished"``) or its context arrived (``"context"``); False on timeout."""
    deadline = _now() + timeout_s
    with _lock:
        while True:
            if until == "context" and (job["contextDone"] or job["status"] in (FAILED, EXPIRED)):
                return job["contextDone"]
            if until == "finished" and job["status"] in (DONE, FAILED, EXPIRED):
                return True
            left = deadline - _now()
            if left <= 0:
                return False
            _lock.wait(left)


def expire(job: dict, reason: str) -> None:
    with _lock:
        if job["status"] in (QUEUED, TAKEN):
            job["status"] = EXPIRED
            job["error"] = reason
            _lock.notify_all()


def remember_status(project: str, status: dict) -> None:
    with _lock:
        _last_status[project] = status


def last_status(project: str) -> dict | None:
    with _lock:
        return _last_status.get(project)


def public(job: dict) -> dict:
    """What the connector receives for a job."""
    return {"id": job["id"], "project": job["project"], "kind": job["kind"], "payload": job["payload"]}


def reset() -> None:
    """Tests only."""
    with _lock:
        _jobs.clear()
        _seen.clear()
        _last_status.clear()
