# -*- coding: UTF-8 -*-
"""Rule-check jobs DG queues for this sign-in (F-01, 2026-10-29).

The server never calls the PC: on the multi-user stand it could not (host.docker.internal was the server, and the
Grasshopper listener only listens on its own loopback). The poll thread asks DG for the next job of this connector
session (``GET /connector/jobs/next``); the ExternalEvent handler runs it in Revit; a short background thread posts
the answer, so no HTTP call ever holds Revit's main thread.

Jobs:

* ``check`` -- execute the property-check program DG generated for the project's rules (plain Revit API, the same
  calculators the Grasshopper chain used) and answer per box its UniqueId, label, values and mesh; the context
  meshes follow in chunks.
* ``paint`` -- colour the verdict in the active view (red / grey / green, element lines stay black) and write
  ``DG_Violation``.
* ``clear`` -- remove the colours of the last check and empty ``DG_Violation``.
* ``snapshot`` -- after a confirmed mapping was written (Phase 1303-26): execute the read-only snapshot program DG
  generated and answer the model fingerprint; one mesh per mapping-session element follows in chunks.

Runs under every pyRevit engine: IronPython 2.7, IronPython 3.4 and CPython 3 (pythonnet). Standard library and the
Revit API only; Python 2.7 syntax (no f-strings, annotations or walrus).
"""

import hashlib
import logging
import threading

from . import dg_client
from . import revit_io

logger = logging.getLogger(__name__)

#: Kind of the handler job that carries a DG check job.
JOB_KIND = "dg_check_job"

#: Context elements per POST, so one answer never becomes a single huge request.
CONTEXT_CHUNK = 150

#: State key with the UniqueIds the last check painted (';'-joined), for ``clear``.
PAINTED_KEY = "checkPainted"

#: Name the generated program is compiled under (tracebacks name it).
PROGRAM_NAME = "<dg-property-check>"


def _text(value):
    if value is None:
        return u""
    try:
        if isinstance(value, unicode):  # noqa: F821 - IronPython 2
            return value
        if isinstance(value, str):
            return value.decode("utf-8", "replace")
    except NameError:
        if isinstance(value, str):
            return value
    try:
        return unicode(value)  # noqa: F821 - IronPython 2
    except NameError:
        return str(value)


def token_key(token):
    return hashlib.sha1(_text(token).encode("utf-8")).hexdigest()


# --- poll thread ---------------------------------------------------------------

def poll(store, client, queue, raise_event):
    """Ask DG for the next job of this sign-in and hand it to the Revit handler -> the job kind or None.

    ``client`` needs ``next_job``; an older client without it (offline tests) is skipped. Never touches Revit."""
    token = _text(store.get("token")).strip()
    project = _text(store.get("project")).strip()
    if not token or not project or not hasattr(client, "next_job"):
        return None
    url = _text(store.get("url")).strip() or dg_client.DEFAULT_BASE_URL
    answer = client.next_job(url, token, project)
    job = answer.get("job") if isinstance(answer, dict) else None
    if not isinstance(job, dict) or not job.get("id"):
        return None
    queue({"kind": JOB_KIND, "job": job, "tokenKey": token_key(token), "url": url, "project": project})
    raise_event()
    return _text(job.get("kind"))


# --- Revit main thread -----------------------------------------------------------

def _program(source, entry):
    namespace = {"__name__": "dg_property_check"}
    exec(compile(_text(source), PROGRAM_NAME, "exec"), namespace)
    function = namespace.get(entry)
    if not callable(function):
        raise ValueError("the DG program defines no {}()".format(entry))
    return function


def execute_program(source, doc, family_filter, with_context, categories=None):
    """Run the generated property-check program against ``doc`` -> its answer dict.

    The program defines ``run(doc, family_filter, with_context[, categories])``; it is compiled and executed in a
    fresh namespace of its own (it imports only math, hashlib, clr, System and the Revit API). The categories of the
    latest model snapshot (Phase 1303-26) are passed only when DG sent them, so an older program keeps working."""
    runner = _program(source, "run")
    if categories is None:
        return runner(doc, family_filter, with_context)
    return runner(doc, family_filter, with_context, list(categories))


def execute_snapshot(source, doc, unique_ids, categories):
    """Run the read-only snapshot program DG generated -> (answer without elements, elements)."""
    answer = _program(source, "snapshot")(doc, list(unique_ids or []), list(categories or []))
    if not isinstance(answer, dict):
        raise ValueError("the DG snapshot program answered no result")
    elements = list(answer.pop("elements", None) or [])
    return answer, elements


def _active_document(uiapp):
    try:
        uidoc = uiapp.ActiveUIDocument
    except Exception:
        uidoc = None
    if uidoc is None:
        return None, None
    try:
        doc = uidoc.Document
    except Exception:
        return None, None
    if doc is None or getattr(doc, "IsFamilyDocument", False):
        return None, None
    try:
        view = doc.ActiveView
    except Exception:
        view = None
    return doc, view


def _check(doc, payload):
    answer = execute_program(payload.get("script"), doc, payload.get("boxFamilyFilter") or "",
                             bool(payload.get("withContext")), payload.get("snapshotCategories"))
    if not isinstance(answer, dict):
        raise ValueError("the DG check program answered no result")
    context = list(answer.pop("context", None) or [])
    return answer, context


def run(uiapp, entry, store, shared_file=None):
    """Execute one DG job in the Revit API context -> (ok, result, error, context); never raises.

    A job of an earlier sign-in (the token changed since it was taken) is dropped unanswered."""
    job = entry.get("job") or {}
    kind = _text(job.get("kind"))
    payload = job.get("payload") or {}
    if token_key(store.get("token")) != entry.get("tokenKey"):
        return None
    doc, view = _active_document(uiapp)
    try:
        if doc is None:
            raise ValueError("no Revit project is active: open the model and make its view active")
        if kind == "check":
            result, context = _check(doc, payload)
            store.set("message", "DG checked {} boxes in {}".format(len(result.get("boxes") or []),
                                                                    _text(result.get("document"))))
            return True, result, None, context
        if kind == "snapshot":
            result, elements = execute_snapshot(payload.get("script"), doc, payload.get("uniqueIds"),
                                                payload.get("categories"))
            store.set("message", "DG: model snapshot of {} elements read from {}".format(
                len(elements), _text(result.get("document"))))
            return True, result, None, elements
        if kind == "paint":
            verdicts = payload.get("verdicts") or {}
            report = revit_io.apply_check_colours(doc, view, verdicts, uiapp.Application, shared_file)
            store.set(PAINTED_KEY, ";".join(_text(u) for u in verdicts.keys()))
            store.set("message", "DG: {} boxes with violations, {} without a verdict".format(
                report.get("violations", 0), report.get("noVerdict", 0)))
            return True, {"report": report}, None, []
        if kind == "clear":
            painted = [u for u in _text(store.get(PAINTED_KEY)).split(";") if u]
            cleared = revit_io.clear_check_colours(doc, view, painted)
            store.set(PAINTED_KEY, "")
            return True, {"report": "cleared {} boxes".format(cleared)}, None, []
        raise ValueError("unknown DG job kind {!r}".format(kind))
    except Exception as error:
        message = _text(error) or error.__class__.__name__
        logger.warning("DG: the %s job failed: %s", kind, message)
        store.set("message", "DG: the {} job failed ({})".format(kind, message))
        return False, None, message, []


# --- answering (background thread) ---------------------------------------------

def send(client, entry, outcome, store):
    """Post the outcome of a job and its context chunks with the current sign-in; failures are logged, never raised.
    The job entry holds only a hash of the token it was taken with; a changed sign-in drops the answer."""
    if outcome is None:
        return
    ok, result, error, context = outcome
    job = entry.get("job") or {}
    url, project, job_id = entry.get("url"), entry.get("project"), job.get("id")
    token = _text(store.get("token")).strip()
    if not token or token_key(token) != entry.get("tokenKey"):
        return
    try:
        client.post_job_result(url, token, project, job_id, ok, result, error)
        if not ok:
            return
        chunks = [context[i:i + CONTEXT_CHUNK] for i in range(0, len(context), CONTEXT_CHUNK)] or [[]]
        if job.get("kind") in ("check", "snapshot"):
            for index, chunk in enumerate(chunks):
                client.post_job_context(url, token, project, job_id, chunk, index == len(chunks) - 1)
    except Exception as error:
        logger.warning("DG: answering the %s job failed: %s", _text(job.get("kind")), _text(error))


def send_later(client, entry, outcome, store, start_thread=True):
    """Answer on a daemon thread so the Revit main thread is free at once."""
    if not start_thread:
        send(client, entry, outcome, store)
        return None
    thread = threading.Thread(target=send, args=(client, entry, outcome, store), name="dg-connector-answer")
    thread.daemon = True
    thread.start()
    return thread
