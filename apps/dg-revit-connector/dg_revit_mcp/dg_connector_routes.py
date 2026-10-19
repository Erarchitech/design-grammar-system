# -*- coding: UTF-8 -*-
"""DG connector routes of the pyRevit Routes API ``dg_revit`` (contract section 8.3).

Four routes, served beside every upstream Revit route:

===================================  ===================================
``GET  /mapping_status/``            sign-in, open session, document, message
``POST /start_mapping/``             read the scope, create the session, colour
``POST /show_elements/``             ``{uniqueIds: [...]}`` -> select + zoom
``POST /clear_colours/``             remove the connector's graphic overrides
===================================  ===================================

They map one-to-one onto the four MCP tools of ``tools/dg_connector_tools.py``.

Handlers declare ``uiapp`` (and ``uidoc``/``doc``/``request``) so pyRevit runs
them on the Revit API thread through an ExternalEvent. ``/show_elements/``
validates its body before touching the runner: 1..5000 non-empty strings, else
400 ``BAD_REQUEST``.

Every handler wraps an unexpected failure into
``{"status": "error", "code": "ROUTE_ERROR", "error": str(e)}`` with HTTP 500.
No answer ever carries the connector token: the state snapshot of the status
route never contains it and the DG client scrubs it from every error.

``dg_connector`` is imported lazily inside the handlers, because this module is
also imported by ``startup.py`` before the extension's ``lib`` path is on
``sys.path`` in some tooling contexts (and by the offline route tests).

Python 2.7 / 3 syntax (pyRevit's IronPython 2.7 under Revit).
"""

import logging

try:
    _TEXT_TYPES = (basestring,)
except NameError:
    _TEXT_TYPES = (str,)

from pyrevit import routes

from .utils import parse_request_data

logger = logging.getLogger(__name__)

#: Body-validation limits of ``/show_elements/`` (contract section 8.3).
MIN_UNIQUE_IDS = 1
MAX_UNIQUE_IDS = 5000


def _runner():
    """The connector runner module (imported lazily, see the module docstring)."""
    from dg_connector import runner
    return runner


def _error(code, message, status):
    return routes.make_response(
        data={"status": "error", "code": code, "error": message}, status=status)


def _ok(result):
    """A runner dict as a successful route payload (``status`` first, never a token)."""
    data = {"status": "ok"}
    if isinstance(result, dict):
        data.update(result)
    else:
        data["result"] = result
    data.pop("token", None)  # defence in depth: the runner never returns it either
    return routes.make_response(data=data)


def _read_body(request):
    return parse_request_data(getattr(request, "data", None))


def _unique_ids(payload):
    """``(unique_ids, None)`` or ``(None, error message)`` for a request body.

    The body is ``{"uniqueIds": ["<UniqueId>", ...]}``: 1..5000 non-empty
    strings. Everything else is refused here, before the runner or Revit is
    involved.
    """
    if not isinstance(payload, dict):
        return None, "the request body must be a JSON object {\"uniqueIds\": [...]}"
    values = payload.get("uniqueIds")
    if not isinstance(values, (list, tuple)):
        return None, "uniqueIds must be a list of Revit UniqueId strings"
    unique_ids = []
    for value in values:
        if not isinstance(value, _TEXT_TYPES):
            return None, "every UniqueId must be a string, got {}".format(type(value).__name__)
        text = value.strip()
        if not text:
            return None, "every UniqueId must be a non-empty string"
        unique_ids.append(text)
    if len(unique_ids) < MIN_UNIQUE_IDS:
        return None, ("uniqueIds is empty; pass at least one Revit UniqueId "
                      "(the selection else the visible model instances are the mapping scope)")
    if len(unique_ids) > MAX_UNIQUE_IDS:
        return None, "uniqueIds has {} ids, more than the {}-element limit of one mapping session".format(
            len(unique_ids), MAX_UNIQUE_IDS)
    return unique_ids, None


def register_dg_connector_routes(api):
    """Register the four DG connector routes under the ``dg_revit`` API."""

    @api.route("/mapping_status/", methods=["GET"])
    def mapping_status(uiapp):
        """Sign-in state, open session, active document and last message."""
        try:
            return _ok(_runner().mapping_status(uiapp))
        except Exception as error:
            logger.error("DG /mapping_status/ failed: %s", str(error))
            return _error("ROUTE_ERROR", str(error), 500)

    @api.route("/start_mapping/", methods=["POST"])
    def start_mapping(uiapp):
        """Read the mapping scope, create the DG session and colour the elements."""
        try:
            return _ok(_runner().start_mapping(uiapp))
        except Exception as error:
            logger.error("DG /start_mapping/ failed: %s", str(error))
            return _error("ROUTE_ERROR", str(error), 500)

    @api.route("/show_elements/", methods=["POST"])
    def show_elements(uiapp, uidoc, doc, request):
        """Select the given UniqueIds in Revit and zoom the active view to them."""
        try:
            unique_ids, problem = _unique_ids(_read_body(request))
            if problem is not None:
                return _error("BAD_REQUEST", problem, 400)
            return _ok(_runner().show(uidoc, doc, unique_ids))
        except Exception as error:
            logger.error("DG /show_elements/ failed: %s", str(error))
            return _error("ROUTE_ERROR", str(error), 500)

    @api.route("/clear_colours/", methods=["POST"])
    def clear_colours(uiapp):
        """Remove the connector's graphic overrides from the session view."""
        try:
            return _ok(_runner().clear(uiapp))
        except Exception as error:
            logger.error("DG /clear_colours/ failed: %s", str(error))
            return _error("ROUTE_ERROR", str(error), 500)
