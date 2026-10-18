# -*- coding: utf-8 -*-
"""Apply loop and connector commands of the DG Revit connector (D-47, D-50).

The connector behaves like CONNECTOR in Grasshopper: it signs in, creates one
mapping session on command, polls it, paints element states into the session
view, and applies the session ten seconds after the newest answer.

The hard rule of this module is *where* Revit is written:

* the **poll thread** never touches the Revit API. It reads the session from
  DG (a network call), decides with the pure :func:`dg_connector.loop.next_action`,
  and then only *queues a job* and calls ``ExternalEvent.Raise()``;
* the **ExternalEvent handler** (:class:`_Handler`, an ``IExternalEventHandler``)
  runs inside the Revit API context on the main thread and executes the queued
  jobs, each in its own transaction (in :mod:`dg_connector.revit_io`);
* a job writes only into the document the session was created in, found by its
  ``CreationGUID`` / ``PathName`` among the open documents. When that document
  is closed the job is dropped and the loop stops for the session: the
  connector never writes into another document (contract section 8.4).

``poll_step`` needs no Revit at all and the handler's ``Execute`` can be called
directly, so the whole loop is testable offline.

Engines. pyRevit runs ``startup.py``, every ribbon button and every Routes
handler in IronPython engines whose module globals are not shared. The
connector state (token, session, document identity, message) therefore lives
in :mod:`dg_connector.state` (AppDomain-backed). The poll thread, its job queue
and its ExternalEvent belong to the engine that ran :func:`install` (the
startup engine; the Routes handlers run there too). A pyRevit reload runs
``startup.py`` again in a new engine: the new install takes over polling via
an AppDomain owner token, and the old thread stops at its next turn, so two
threads never both apply a session.

Commands (the bodies of the four Routes and the four ribbon buttons):

``start_mapping(uiapp)``
    Read the scope, create the DG session, colour immediately.
``mapping_status(uiapp)``
    The state snapshot plus the active document key and the last message.
``show(uidoc, doc, unique_ids)``
    Select and zoom to the given UniqueIds.
``clear(uiapp)``
    Remove the connector's graphic overrides from the session view.

Python 3.4 syntax (IronPython 3.4 under Revit).
"""

import hashlib
import logging
import os
import threading
import time
import uuid

from pyrevit import UI

from . import descriptors
from . import dg_client
from . import docs
from . import loop
from . import revit_io
from . import state as state_module

logger = logging.getLogger(__name__)

#: Name of the handler in Revit's ExternalEvent list.
HANDLER_NAME = "DG mapping"

#: The shared-parameter file shipped at the extension root.
SHARED_PARAMETER_FILE = "DG_SharedParameters.txt"

#: AppDomain data key naming the install that owns the poll thread.
POLL_OWNER_KEY = "DG.RevitConnector.PollOwner"

#: Messages the ribbon, the Routes and DeGram show.
MESSAGE_NOT_SIGNED_IN = "Sign in to DG first (DG → Вход)"
MESSAGE_NO_PROJECT = "Open a saved Revit project first (a family document cannot be mapped)"
MESSAGE_SIGN_IN_EXPIRED = "DG sign-in expired: sign in again"
MESSAGE_NO_SESSION = "No DG mapping session is open; nothing to clear"
MESSAGE_EMPTY_SCOPE = ("DG: nothing to map: select elements, or open a view that shows "
                       "model elements")

# --- process-wide wiring (per engine, see the module docstring) ----------------

#: The handler, the ExternalEvent, the poll thread and its owner token of this
#: engine (one-item lists: append-once flags).
_HANDLER = []
_EXTERNAL_EVENT = []
_THREAD = []
_OWNER = []

#: Jobs queued by the poll thread and run by the handler's ``Execute``.
_JOBS = []
_LOCK = threading.RLock()

#: Held while the handler runs jobs, so two ``Execute`` calls never interleave.
_RUN_LOCK = threading.RLock()

#: Session ids the loop stopped on (applied, or the document was closed).
_DONE_SESSIONS = set()

#: SHA-1 of tokens DG rejected: polling waits for a new sign-in. Only hashes are
#: kept, so this set never holds a token.
_REJECTED_TOKENS = set()

#: Extension directory (holds ``DG_SharedParameters.txt``) and an injected client.
_EXTENSION_DIR = []
_CLIENT = []

#: Stand-in for AppDomain data outside Revit (CPython tests).
_LOCAL_SLOTS = {}


def _store():
    """The process-wide connector state (AppDomain-backed inside Revit)."""
    return state_module.state


def _text(value):
    return "" if value is None else str(value)


def _plural(count, word):
    return "{} {}{}".format(count, word, "" if count == 1 else "s")


def _client(client=None):
    if client is not None:
        return client
    if _CLIENT:
        return _CLIENT[0]
    return dg_client


def _base_url(store):
    return _text(store.get("url")).strip() or dg_client.DEFAULT_BASE_URL


def _token_key(token):
    return hashlib.sha1(_text(token).encode("utf-8")).hexdigest()


def _shared_parameter_file():
    if not _EXTENSION_DIR:
        return None
    return os.path.join(_EXTENSION_DIR[0], SHARED_PARAMETER_FILE)


def _error_text(error):
    """Message of a failed call (DgClientError messages are already scrubbed)."""
    return _text(getattr(error, "message", None)) or _text(error)


# --- AppDomain slot of the poll owner -----------------------------------------

def _appdomain():
    try:
        import clr  # noqa: F401 - only exists under IronPython
        from System import AppDomain
        return AppDomain.CurrentDomain
    except Exception:
        return None


def _read_slot(key):
    domain = _appdomain()
    if domain is not None:
        try:
            value = domain.GetData(key)
            return None if value is None else _text(value)
        except Exception:
            pass
    return _LOCAL_SLOTS.get(key)


def _write_slot(key, value):
    domain = _appdomain()
    if domain is not None:
        try:
            domain.SetData(key, value)
            return
        except Exception:
            pass
    _LOCAL_SLOTS[key] = value


def owns_polling():
    """True while this engine's install is the newest; True when nothing was installed."""
    if not _OWNER:
        return True
    return _read_slot(POLL_OWNER_KEY) == _OWNER[0]


# --- queued jobs --------------------------------------------------------------

def _queue_job(job):
    """Append one job for the ExternalEvent handler; returns it."""
    with _LOCK:
        _JOBS.append(job)
    return job


def queued_jobs():
    """Copy of the jobs waiting for the handler (tests, diagnostics)."""
    with _LOCK:
        return list(_JOBS)


def take_jobs():
    """Remove and return every queued job, oldest first."""
    with _LOCK:
        jobs = list(_JOBS)
        del _JOBS[:]
    return jobs


def _raise_event():
    """Ask Revit to run the handler on the main thread; never raises."""
    if not _EXTERNAL_EVENT:
        return False
    try:
        _EXTERNAL_EVENT[0].Raise()
        return True
    except Exception as error:
        logger.warning("DG: raising the connector ExternalEvent failed: %s", _text(error))
        return False


def _session_identity(store):
    """The session/document identity every job carries."""
    return {
        "sessionId": _text(store.get("sessionId")),
        "documentKey": _text(store.get("documentKey")),
        "creationGuid": _text(store.get("creationGuid")),
        "pathName": _text(store.get("documentPath")),
        "viewId": _text(store.get("viewId")),
    }


def _queue_colour_job(store, session, reason):
    """Queue the colour job of ``session``; 1 when a job was queued."""
    states = loop.states_by_uid(session)
    if not states:
        return 0
    job = _session_identity(store)
    job.update({"kind": "colours", "reason": reason, "states": states})
    _queue_job(job)
    return 1


def _queue_parameters_job(store, session, applied):
    """Queue the ``DG_Class`` / ``DG_MappingState`` job of ``session``."""
    states = loop.states_by_uid(session)
    if not states:
        return 0
    job = _session_identity(store)
    job.update({"kind": "parameters", "applied": applied,
                "roles": loop.roles_by_uid(session), "states": states})
    _queue_job(job)
    return 1


def _mark_done(session_id):
    if session_id:
        with _LOCK:
            _DONE_SESSIONS.add(session_id)


def _is_done(session_id):
    with _LOCK:
        return session_id in _DONE_SESSIONS


# --- poll step ----------------------------------------------------------------

def poll_step(store=None, client=None, now=None):
    """One poll iteration: read the session, decide, queue jobs -> outcome dict.

    The whole brain of the background loop without a thread, a Revit API or a
    clock of its own: it takes the state store, a ``dg_client``-like client
    and ``now`` (a datetime, naive = UTC, or epoch seconds).

    Outcome ``{"action", "queued", ...}``; action is ``recolour``, ``apply``,
    ``done``, ``wait-grace``, ``idle`` (see :func:`dg_connector.loop.next_action`),
    ``stop`` (DG rejected the token: polling waits for a new sign-in) or
    ``error`` (a DG call failed; the next poll tries again).
    """
    store = _store() if store is None else store
    client = _client(client)
    session_id = _text(store.get("sessionId")).strip()
    token = _text(store.get("token")).strip()
    if not session_id or not token:
        return {"action": "idle", "queued": 0}
    if _token_key(token) in _REJECTED_TOKENS:
        return {"action": "stop", "queued": 0, "message": MESSAGE_SIGN_IN_EXPIRED}
    if _is_done(session_id):
        return {"action": "done", "queued": 0}

    url = _base_url(store)
    project = _text(store.get("project"))
    try:
        session = client.get_session(url, token, project, session_id)
        decision = loop.next_action(session, {"lastDigest": store.get("lastDigest")}, now)
    except Exception as error:  # a DG failure or a broken answer: never kill the thread
        return _poll_failure(store, error, token)
    action = decision.get("action")

    if action == "recolour":
        queued = _queue_colour_job(store, session, "recolour")
        store.set("lastDigest", decision.get("digest"))
        if queued:
            _raise_event()
        return {"action": "recolour", "queued": queued, "digest": decision.get("digest")}

    if action == "apply":
        if not owns_polling():  # a reload installed a newer poll thread: it applies
            return {"action": "idle", "queued": 0}
        return _apply(store, client, session, session_id, url, project, token)

    if action == "done":
        _mark_done(session_id)
        message = "DG mapping session {} is applied; the connector stopped polling it".format(
            session_id)
        store.set("message", message)
        return {"action": "done", "queued": 0, "message": message}

    outcome = {"action": action, "queued": 0}
    if "secondsLeft" in decision:
        outcome["secondsLeft"] = decision["secondsLeft"]
    return outcome


def _poll_failure(store, error, token):
    """A failed DG call -> outcome; REJECTED stops polling until a new sign-in."""
    if _text(getattr(error, "code", "")) == "REJECTED":
        with _LOCK:
            _REJECTED_TOKENS.add(_token_key(token))
        store.set("message", MESSAGE_SIGN_IN_EXPIRED)
        return {"action": "stop", "queued": 0, "message": MESSAGE_SIGN_IN_EXPIRED}
    text = _error_text(error)
    message = "DG: {}".format(text) if text else "DG: the connector call failed"
    store.set("message", message)
    return {"action": "error", "queued": 0, "message": message}


def _apply(store, client, session, session_id, url, project, token):
    """POST apply, read the session again, queue colours + parameters, stop polling."""
    try:
        applied = client.apply_session(url, token, project, session_id)
    except Exception as error:
        return _poll_failure(store, error, token)
    try:
        refreshed = client.get_session(url, token, project, session_id)
    except Exception:
        refreshed = session  # the states are the same; only appliedAt is missing
    count = _applied_count(applied, refreshed)
    _mark_done(session_id)
    message = "DG applied {}".format(_plural(count, "element"))
    store.set("message", message)
    queued = _queue_colour_job(store, refreshed, "apply")
    queued += _queue_parameters_job(store, refreshed, count)
    store.set("lastDigest", loop.session_digest(refreshed))
    if queued:
        _raise_event()
    return {"action": "apply", "queued": queued, "applied": count, "message": message}


def _applied_count(applied, session):
    """``applied`` of the MappingApplyResult (contract section 5), else the element count."""
    if isinstance(applied, dict):
        value = applied.get("applied")
        if isinstance(value, int) and not isinstance(value, bool):
            return value
    elements = session.get("elements") if isinstance(session, dict) else None
    return len(elements) if isinstance(elements, list) else 0


# --- documents and views ------------------------------------------------------

def _documents(uiapp):
    try:
        return list(uiapp.Application.Documents)
    except Exception:
        return []


def _norm_path(path):
    return _text(path).replace("/", "\\").strip().lower()


def _path_name(document):
    try:
        return _text(document.PathName)
    except Exception:
        return ""


def _guid_of(document):
    try:
        return _text(document.CreationGUID).strip().lower()
    except Exception:
        return ""


def _find_document(uiapp, creation_guid, path_name):
    """The open project document of a session, or None. Never "the active one".

    With a ``CreationGUID`` the document must carry it (and, when a path is
    stored, that path too: a Save-As copy shares the GUID). Without a GUID the
    path alone decides. With neither nothing matches, so a job without an
    identity can never write anywhere.
    """
    guid = _text(creation_guid).strip().lower()
    path = _norm_path(path_name)
    if not guid and not path:
        return None
    for document in _documents(uiapp):
        if getattr(document, "IsLinked", False):
            continue
        if guid and _guid_of(document) != guid:
            continue
        if path and _norm_path(_path_name(document)) != path:
            continue
        return document
    return None


def _view_id_text(view):
    if view is None:
        return None
    try:
        return _text(revit_io.element_id_value(view.Id))
    except Exception:
        return None


def _stored_view(document, view_id):
    """The view a session was coloured in (stored element id), or None."""
    text = _text(view_id).strip()
    if document is None or not text:
        return None
    try:
        number = int(text)
    except ValueError:
        return None
    try:
        return document.GetElement(revit_io.element_id(number))
    except Exception:
        return None


def _active_document(uiapp):
    """(document, uidoc) of the active UI document, or (None, None)."""
    try:
        uidoc = uiapp.ActiveUIDocument
    except Exception:
        uidoc = None
    document = None
    if uidoc is not None:
        try:
            document = uidoc.Document
        except Exception:
            document = None
    return document, uidoc


def _document_key(document):
    return docs.document_key(_path_name(document) or _text(getattr(document, "Title", "")))


# --- the ExternalEvent handler -------------------------------------------------

def _session_document(uiapp, job):
    """The job's document, or None after stopping the loop with a message."""
    document = _find_document(uiapp, job.get("creationGuid"), job.get("pathName"))
    if document is None:
        _mark_done(_text(job.get("sessionId")))
        _store().set("message", (
            "DG: the document {} of the mapping session is not open; nothing was "
            "written and the connector stopped polling the session").format(
                _text(job.get("documentKey")) or "(unknown)"))
    return document


def _run_colour_job(uiapp, job):
    document = _session_document(uiapp, job)
    if document is None:
        return 0
    view = _stored_view(document, job.get("viewId"))
    if view is None:
        _store().set("message", "DG: the view the session was coloured in no longer "
                                "exists; the colours were not refreshed")
        return 0
    coloured = revit_io.apply_colours(document, view, job.get("states") or {})
    if job.get("reason") != "apply":  # after an apply the apply message stays visible
        _store().set("message", "DG coloured {}".format(_plural(coloured, "element")))
    return coloured


def _run_parameters_job(uiapp, job):
    document = _session_document(uiapp, job)
    if document is None:
        return 0
    shared_file = _shared_parameter_file()
    if not shared_file:
        _store().set("message", "DG: the shared-parameter file is unknown (connector not "
                                "installed); DG_Class / DG_MappingState were not written")
        return 0
    result = revit_io.write_parameters(document, uiapp.Application, shared_file,
                                       job.get("roles") or {}, job.get("states") or {})
    written = result.get("written", 0) if isinstance(result, dict) else 0
    skipped = result.get("skipped", 0) if isinstance(result, dict) else 0
    message = "DG applied {}; DG_Class / DG_MappingState written on {}".format(
        _plural(int(job.get("applied") or 0), "element"), _plural(written, "element"))
    if skipped:
        message += " ({} skipped)".format(skipped)
    _store().set("message", message)
    return written


def _run_job(uiapp, job):
    """Execute one queued job; a failure is reported, never raised."""
    try:
        if job.get("kind") == "parameters":
            return _run_parameters_job(uiapp, job)
        return _run_colour_job(uiapp, job)
    except Exception as error:
        message = "DG: the {} job failed ({})".format(_text(job.get("kind")), _text(error))
        logger.warning(message)
        _store().set("message", message)
        return 0


def run_jobs(uiapp):
    """Run every queued job, in order (the body of :meth:`_Handler.Execute`)."""
    with _RUN_LOCK:
        jobs = take_jobs()
        for job in jobs:
            _run_job(uiapp, job)
    return len(jobs)


class _Handler(UI.IExternalEventHandler):
    """Runs the queued DG jobs inside the Revit API context, on the main thread."""

    def Execute(self, uiapp):
        run_jobs(uiapp)

    def GetName(self):
        return HANDLER_NAME


# --- installation -------------------------------------------------------------

def install(uiapp, extension_dir, client=None, start_thread=True,
            external_event=None, handler=None):
    """Create the handler, the ExternalEvent and the poll thread once; idempotent.

    Called from ``startup.py`` with ``__revit__`` and the extension directory.
    A second call in the same engine reuses everything. A call from a new
    engine (pyRevit reload) becomes the poll owner: the previous engine's
    thread sees the new owner token and stops.

    ``client``, ``start_thread``, ``external_event`` and ``handler`` exist for
    the offline tests; production passes only the first two arguments.
    """
    with _LOCK:
        _EXTENSION_DIR[:] = [_text(extension_dir)] if extension_dir else []
        if client is not None:
            _CLIENT[:] = [client]
        if not _HANDLER:
            _HANDLER.append(handler if handler is not None else _Handler())
        if not _EXTERNAL_EVENT:
            event = external_event
            if event is None:
                try:
                    event = UI.ExternalEvent.Create(_HANDLER[0])
                except Exception as error:
                    logger.error("DG: creating the connector ExternalEvent failed: %s",
                                 _text(error))
                    event = None
            if event is not None:
                _EXTERNAL_EVENT.append(event)
        if start_thread and not (_THREAD and _THREAD[0].is_alive()):
            owner = uuid.uuid4().hex
            _OWNER[:] = [owner]
            _write_slot(POLL_OWNER_KEY, owner)
            thread = threading.Thread(target=_poll_loop, args=(owner,),
                                      name="dg-connector-poll")
            thread.daemon = True
            thread.start()
            _THREAD[:] = [thread]
            logger.info("DG connector installed: polling every %s s", loop.POLL_SECONDS)
    return _HANDLER[0]


def _poll_loop(owner, sleep=time.sleep):
    """The daemon poll thread: read the session, queue jobs, never touch Revit."""
    while _read_slot(POLL_OWNER_KEY) == owner:
        try:
            poll_step()
        except Exception as error:  # the loop outlives any single failure
            logger.warning("DG: poll step failed: %s", _text(error))
        sleep(loop.POLL_SECONDS)
    logger.info("DG: a newer connector install took over polling; this thread stops")


# --- commands -----------------------------------------------------------------

def _refused(store, message):
    store.set("message", message)
    return {"started": False, "sessionId": None, "message": message}


def start_mapping(uiapp, client=None, now=None):
    """Start a DG mapping session for the active model -> ``{started, sessionId, message}``.

    Runs in the Revit API context (a Routes handler or a ribbon button). Needs a
    signed-in connector. Reads the scope (selection, else the visible model
    instances, at most 5000), builds descriptors, posts
    ``{project, platform: "revit", label, elements}``, stores the session and
    document identity and colours the elements in the active view. ``now`` is
    the local time of the label (default: now).
    """
    store = _store()
    if not store.is_signed_in():
        return _refused(store, MESSAGE_NOT_SIGNED_IN)

    document, uidoc = _active_document(uiapp)
    if document is None or getattr(document, "IsFamilyDocument", False) \
            or not _path_name(document).strip():
        return _refused(store, MESSAGE_NO_PROJECT)
    try:
        view = document.ActiveView
    except Exception:
        view = None

    try:
        elements, total = revit_io.collect_scope(document, uidoc, descriptors.MAX_ELEMENTS)
        rows, skipped = revit_io.read_rows(document, elements)
    except Exception as error:
        return _refused(store, "DG: reading the model failed ({})".format(_text(error)))
    element_descriptors = descriptors.rows_to_descriptors(rows, descriptors.MAX_ELEMENTS)
    if not element_descriptors:
        return _refused(store, MESSAGE_EMPTY_SCOPE)
    truncated = max(0, total - len(elements))

    key = _document_key(document)
    body = {
        "project": _text(store.get("project")),
        "platform": descriptors.PLATFORM,
        "label": docs.session_label(key, now),
        "elements": element_descriptors,
    }
    token = _text(store.get("token"))
    try:
        session = _client(client).create_session(_base_url(store), token, body)
    except Exception as error:
        if _text(getattr(error, "code", "")) == "REJECTED":
            return _refused(store, MESSAGE_SIGN_IN_EXPIRED)
        return _refused(store, "DG: starting the mapping session failed ({})".format(
            _error_text(error)))
    session_id = _text(session.get("sessionId") if isinstance(session, dict) else "").strip()
    if not session_id:
        return _refused(store, "DG: the mapping session answer carried no sessionId")

    store.clear_session()  # also clears lastDigest of the previous session
    store.set("sessionId", session_id)
    store.set("documentKey", key)
    store.set("documentPath", _path_name(document))
    store.set("creationGuid", _text(getattr(document, "CreationGUID", "")))
    store.set("viewId", _view_id_text(view))
    with _LOCK:
        _DONE_SESSIONS.discard(session_id)

    coloured = 0
    try:
        coloured = revit_io.apply_colours(document, view, loop.states_by_uid(session))
        store.set("lastDigest", loop.session_digest(session))
    except Exception as error:  # lastDigest stays empty, so the poll loop repaints
        logger.warning("DG: colouring the new session failed: %s", _text(error))

    message = _started_message(key, len(element_descriptors), coloured, truncated, skipped,
                               _open_questions(session))
    store.set("message", message)
    return {"started": True, "sessionId": session_id, "message": message}


def _open_questions(session):
    summary = session.get("summary") if isinstance(session, dict) else None
    count = summary.get("openQuestions") if isinstance(summary, dict) else None
    if isinstance(count, bool) or not isinstance(count, int):
        return None
    return count


def _started_message(key, read, coloured, truncated, skipped, open_questions):
    """One status line: elements, truncation, skips and open questions."""
    message = "DG mapping session for {}: {} read, {} coloured".format(
        key, _plural(read, "element"), coloured)
    if skipped:
        message += ", {} skipped".format(skipped)
    if truncated:
        message += ", {} beyond the {}-element cap".format(truncated, descriptors.MAX_ELEMENTS)
    if open_questions is None:
        message += "; open questions unknown"
    elif open_questions:
        message += "; {}".format(_plural(open_questions, "open question"))
    else:
        message += "; no open questions"
    return message


def mapping_status(uiapp=None):
    """State snapshot (never the token) + the active document key and the last message."""
    store = _store()
    snapshot = store.snapshot()
    document = None
    if uiapp is not None:
        document, _uidoc = _active_document(uiapp)
    snapshot["document"] = None if document is None else _document_key(document)
    snapshot["connectorMessage"] = _text(store.get("message"))
    snapshot.pop("token", None)
    return snapshot


def show(uidoc, doc, unique_ids):
    """Select the given UniqueIds and zoom the active view to them."""
    return revit_io.show_elements(uidoc, doc, unique_ids)


def _cleared(store, cleared, message):
    store.set("message", message)
    return {"cleared": cleared, "message": message}


def clear(uiapp=None, client=None):
    """Remove the connector's overrides in the session view -> ``{cleared, message}``.

    Runs in the Revit API context. The session's elements come from DG; when
    DG cannot be read (signed out, expired, unreachable) the session view is
    scanned for elements painted in the DG palette instead. Only the session's
    own document and view are touched; without an open session nothing is.
    The poll loop repaints only when element states change again.
    """
    store = _store()
    session_id = _text(store.get("sessionId")).strip()
    if not session_id:
        return _cleared(store, 0, MESSAGE_NO_SESSION)
    document = _find_document(uiapp, store.get("creationGuid"), store.get("documentPath"))
    if document is None:
        return _cleared(store, 0, "DG: the document {} of the mapping session is not open; "
                                  "nothing was cleared".format(
                                      _text(store.get("documentKey")) or "(unknown)"))
    view = _stored_view(document, store.get("viewId"))
    if view is None:
        return _cleared(store, 0, "DG: the view the session was coloured in no longer "
                                  "exists; nothing was cleared")

    unique_ids = None
    reason = ""
    if store.is_signed_in():
        try:
            session = _client(client).get_session(
                _base_url(store), _text(store.get("token")), _text(store.get("project")),
                session_id)
            unique_ids = list(loop.states_by_uid(session).keys())
        except Exception as error:
            reason = _error_text(error)
    else:
        reason = "not signed in"
    if unique_ids is None:
        unique_ids = revit_io.palette_overridden_ids(document, view)

    try:
        cleared = revit_io.clear_colours(document, view, unique_ids)
    except Exception as error:
        return _cleared(store, 0, "DG: clearing the colours failed ({})".format(_text(error)))
    message = "DG cleared the mapping colours of {}".format(_plural(cleared, "element"))
    if reason:
        message += " (found by colour in the view; the session was not read: {})".format(reason)
    return _cleared(store, cleared, message)
