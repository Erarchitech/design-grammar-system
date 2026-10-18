# -*- coding: UTF-8 -*-
"""
Document enumeration and identity-pinned selection snapshot (DeGram, D-13/D-14).

pyRevit Routes only knows the *active* document. These two read routes make the
document explicit:

* ``GET  /list_open_documents/`` lists every open non-linked, non-family project
  document with the identity fields a client pins on (creationGuid + pathName).
* ``POST /selection_snapshot/`` reads the current selection of the pinned
  document, and only of that document: when the pinned document is not open the
  outcome is DOCUMENT_NOT_OPEN, when it is open but is not the active UI
  document (or its path differs) the outcome is IDENTITY_MISMATCH. Nothing from
  any other document is ever returned.

Both handlers declare ``uiapp`` (and ``uidoc``) so pyRevit runs them on the Revit
API thread through ExternalEvent. Neither opens a transaction or changes
anything. Syntax is kept IronPython 2.7 / CPython compatible (no f-strings).
"""

import json
import logging

from pyrevit import routes, DB

from .utils import get_element_id_value, parse_request_data

logger = logging.getLogger(__name__)

MAX_ELEMENTS_DEFAULT = 200
MAX_ELEMENTS_CAP = 1000
MAX_PARAMETERS_DEFAULT = 50
MAX_PARAMETERS_CAP = 200


# --- small helpers ------------------------------------------------------------

def _text(value):
    """Unicode-safe text; None becomes an empty string."""
    if value is None:
        return ""
    try:
        return str(value)
    except Exception:
        return ""


def _guid(doc):
    return _text(doc.CreationGUID).lower()


def _norm_path(path):
    return _text(path).replace("/", "\\").lower()


def _clamp(value, default, cap):
    if isinstance(value, bool):
        return default
    try:
        number = int(value)
    except (TypeError, ValueError):
        return default
    return max(0, min(number, cap))


def _error(code, message, status, **extra):
    data = {"status": "error", "code": code, "error": message}
    data.update(extra)
    return routes.make_response(data=data, status=status)


def _read_body(request):
    return parse_request_data(getattr(request, "data", None))


def _open_documents(uiapp):
    """Open project documents: linked and family documents are skipped."""
    found = []
    for doc in uiapp.Application.Documents:
        if getattr(doc, "IsLinked", False) or getattr(doc, "IsFamilyDocument", False):
            continue
        found.append(doc)
    return found


def _same_document(a, b):
    return (_guid(a) == _guid(b)
            and _norm_path(a.PathName) == _norm_path(b.PathName)
            and _text(a.Title) == _text(b.Title))


def _document_row(doc, active):
    return {
        "title": _text(doc.Title),
        "pathName": _text(doc.PathName),
        "creationGuid": _text(doc.CreationGUID),
        "isActive": bool(active is not None and _same_document(doc, active)),
        "isModified": bool(doc.IsModified),
    }


# --- parameter / element reading ---------------------------------------------

def _unit_label(param):
    """Display label of the parameter's unit, or "" when it has none (Revit 2022+ ForgeTypeId)."""
    try:
        unit_id = param.GetUnitTypeId()
    except Exception:
        return ""
    if unit_id is None:
        return ""
    try:
        return _text(DB.LabelUtils.GetLabelForUnit(unit_id))
    except Exception:
        try:
            return _text(unit_id.TypeId)
        except Exception:
            return ""


def _raw_value(param, storage):
    """Raw value by storage type: strings as text, numbers as numbers, ids as ints."""
    if storage == "String":
        value = param.AsString()
        return None if value is None else _text(value)
    if storage == "Integer":
        return int(param.AsInteger())
    if storage == "Double":
        return float(param.AsDouble())  # Revit internal units; see displayValue/unit
    if storage == "ElementId":
        return get_element_id_value(param.AsElementId())
    return None


def _parameter_row(param):
    storage = _text(param.StorageType)
    row = {
        "name": _text(param.Definition.Name),
        "storageType": storage,
        "unit": _unit_label(param) if storage == "Double" else "",
        "displayValue": "",
        "value": None,
    }
    if not param.HasValue:
        return row
    try:
        row["displayValue"] = _text(param.AsValueString() if storage != "String" else param.AsString())
    except Exception:
        row["displayValue"] = ""
    try:
        row["value"] = _raw_value(param, storage)
    except Exception:
        row["value"] = None
    return row


def _type_name(doc, element):
    try:
        type_id = element.GetTypeId()
        if not type_id or type_id == DB.ElementId.InvalidElementId:
            return ""
        type_element = doc.GetElement(type_id)
        if type_element is None:
            return ""
        try:
            return _text(type_element.Name)
        except AttributeError:
            return _text(DB.Element.Name.__get__(type_element))
    except Exception:
        return ""


def _element_row(doc, element, max_parameters):
    category = ""
    try:
        if element.Category:
            category = _text(element.Category.Name)
    except Exception:
        pass
    rows = []
    seen = set()
    for param in element.GetOrderedParameters():
        try:
            name = _text(param.Definition.Name)
            if name in seen:
                continue
            seen.add(name)
            rows.append(_parameter_row(param))
        except Exception:
            continue
    kept = rows[:max_parameters]
    return {
        "uniqueId": _text(element.UniqueId),
        "elementId": get_element_id_value(element),
        "category": category,
        "typeName": _type_name(doc, element),
        "parameters": kept,
        "parametersTotal": len(rows),
    }


def build_snapshot(doc, element_ids, max_elements, max_parameters):
    """Selection snapshot payload for ``doc`` (pure: no Revit API beyond reads)."""
    elements = []
    dropped_parameters = 0
    for element_id in list(element_ids)[:max_elements]:
        element = doc.GetElement(element_id)
        if element is None:
            continue
        row = _element_row(doc, element, max_parameters)
        dropped_parameters += row["parametersTotal"] - len(row["parameters"])
        elements.append(row)
    return {
        "emptySelection": len(element_ids) == 0,
        "elements": elements,
        "truncation": {
            "elementsTotal": len(element_ids),
            "elementsKept": len(elements),
            "parametersTruncated": dropped_parameters,
            "maxElements": max_elements,
            "maxParameters": max_parameters,
        },
    }


# --- routes -------------------------------------------------------------------

def register_document_read_routes(api):
    """Register the two DeGram read routes."""

    @api.route("/list_open_documents/", methods=["GET"])
    def list_open_documents(uiapp):
        """List open project documents with the identity fields clients pin on."""
        try:
            active_ui = getattr(uiapp, "ActiveUIDocument", None)
            active = active_ui.Document if active_ui is not None else None
            rows = [_document_row(d, active) for d in _open_documents(uiapp)]
            return routes.make_response(data={"status": "ok", "documents": rows})
        except Exception as e:
            logger.error("list_open_documents failed: %s", str(e))
            return _error("ROUTE_ERROR", str(e), 500)

    @api.route("/selection_snapshot/", methods=["POST"])
    def selection_snapshot(uiapp, uidoc, request):
        """Selection + parameters of the pinned, active document.

        Body: {"identity": {"creationGuid": ..., "pathName": ...},
               "max_elements": 200, "max_parameters": 50}
        """
        try:
            payload = _read_body(request)
            identity = payload.get("identity") if payload else None
            if not isinstance(identity, dict) or not _text(identity.get("creationGuid")).strip():
                return _error("BAD_REQUEST",
                              "identity.creationGuid is required (pin a document from list_open_documents)", 400)
            wanted_guid = _text(identity.get("creationGuid")).strip().lower()
            wanted_path = _norm_path(identity.get("pathName"))
            max_elements = _clamp(payload.get("max_elements"), MAX_ELEMENTS_DEFAULT, MAX_ELEMENTS_CAP)
            max_parameters = _clamp(payload.get("max_parameters"), MAX_PARAMETERS_DEFAULT, MAX_PARAMETERS_CAP)

            same_guid = [d for d in _open_documents(uiapp) if _guid(d) == wanted_guid]
            if not same_guid:
                return _error("DOCUMENT_NOT_OPEN", "The pinned document is not open in Revit", 409)
            exact = [d for d in same_guid if _norm_path(d.PathName) == wanted_path]
            if not exact:
                return _error("IDENTITY_MISMATCH",
                              "A document with this creationGuid is open but its pathName differs",
                              409, reason="PATH_DIFFERS")
            target = exact[0]
            active = uidoc.Document if uidoc is not None else None
            if active is None or not _same_document(target, active):
                return _error("IDENTITY_MISMATCH",
                              "The pinned document is open but is not the active document; "
                              "activate it in Revit and retry",
                              409, reason="NOT_ACTIVE_DOCUMENT")

            ids = list(uidoc.Selection.GetElementIds())
            data = build_snapshot(active, ids, max_elements, max_parameters)
            data["status"] = "ok"
            data["identity"] = {"creationGuid": _text(active.CreationGUID),
                                "pathName": _text(active.PathName)}
            return routes.make_response(data=data)
        except Exception as e:
            logger.error("selection_snapshot failed: %s", str(e))
            return _error("ROUTE_ERROR", str(e), 500)
