#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Read-only Revit selection reader for DG mapping (Phase 1303 plan 04; D-20, D-27).

Reads the elements the owner selected in Revit through the read-only revit-mcp
pyRevit routes on loopback (``http://127.0.0.1:48884/revit_mcp/``) and turns
them into mapping ElementDescriptors (1303-API-CONTRACT.md section 1).

The CLI writes the body of ``POST /mapping/sessions`` (contract section 2) to a
file that the owner imports in the Web UI (Projects -> Mapping). This module
never talks to DG, never reads, stores or sends credentials, and never requests
a Revit route outside ``ALLOWED_PATHS``.

Usage::

    python tools/mapping/revit_read.py --out act3-revit.json
    python tools/mapping/revit_read.py --dry-run-fixture snapshot.json --out dry.json

Standard library only; Python 3.11+.
"""

import argparse
import http.client
import ipaddress
import json
import math
import re
import sys
import threading
import urllib.error
import urllib.parse
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from pathlib import Path

DEFAULT_BASE = "http://127.0.0.1:48884/revit_mcp"
DEFAULT_TIMEOUT = 30.0
DEFAULT_PROJECT = "v12-hexagonal-facade-01"
DEFAULT_LABEL = "act3-revit"
PLATFORM = "revit"

#: The only Revit routes this module may request; every one is a read.
#: ``element_properties/`` is followed by a numeric element id, the other three
#: are exact paths. Checked before every request (``check_route``).
ALLOWED_PATHS = ("status/", "list_open_documents/", "selection_snapshot/", "element_properties/")
_ELEMENT_PROPERTIES = "element_properties/"
#: HTTP method of each allowed route (revit-mcp ``degram_readonly.ALLOWED_ROUTES``).
_ROUTE_METHOD = {
    "status/": "GET",
    "list_open_documents/": "GET",
    "selection_snapshot/": "POST",
    "element_properties/": "GET",
}
_ELEMENT_ID_RE = re.compile(r"[1-9][0-9]{0,18}")

#: Server-side caps of selection_snapshot (revit-mcp documents.py).
MAX_ELEMENTS_CAP = 1000
MAX_PARAMETERS_CAP = 200

FEET_TO_METRES = 0.3048

#: IFC export parameter names (EN and RU UI) -> ifc.entity / ifc.predefinedType.
IFC_ENTITY_PARAMETERS = ("IfcExportAs", "Export to IFC As", "Экспорт в IFC как", "Экспортировать в IFC как")
IFC_PREDEFINED_TYPE_PARAMETERS = ("IfcExportType", "Export Type to IFC As", "Тип экспорта в IFC")
_IFC_ENTITY_KEYS = frozenset(n.casefold() for n in IFC_ENTITY_PARAMETERS)
_IFC_PREDEFINED_KEYS = frozenset(n.casefold() for n in IFC_PREDEFINED_TYPE_PARAMETERS)

#: Instance parameters that may carry a Unicode-safe family name in the snapshot
#: (element_properties replaces every non-ASCII character with "?").
FAMILY_PARAMETERS = ("Family", "Семейство")
FAMILY_AND_TYPE_PARAMETERS = ("Family and Type", "Семейство и типоразмер")

NON_ASCII_MARKER = "_nonAscii"

# Unit labels (LabelUtils.GetLabelForUnit, or a ForgeTypeId string as fallback).
_NOT_LENGTH_MARKERS = (
    "square", "cubic", "квадрат", "кубич", "radian", "degree", "радиан", "градус",
    "second", "секунд", "minute", "hour", " per ", "/", "newton", "ньютон", "kip",
    "pound", "фунт", "watt", "ватт", "pascal", "паскал",
)
_LENGTH_MARKERS = (
    "millimet", "centimet", "decimet", "meter", "metre", "feet", "foot", "inch",
    "миллиметр", "сантиметр", "дециметр", "метр", "фут", "дюйм",
)
_LENGTH_TOKENS = frozenset(["mm", "cm", "dm", "m", "ft", "in", "мм", "см", "дм", "м"])


class RevitReadError(Exception):
    """A Revit read failed. ``status`` is the HTTP status or None (no response)."""

    def __init__(self, status, code, detail):
        self.status = status
        self.code = str(code)
        self.detail = "" if detail is None else str(detail)
        super().__init__("{}: {}".format(self.code, self.detail) if self.detail else self.code)


class PathNotAllowedError(RevitReadError):
    """Refused before any network activity: the route is not in ALLOWED_PATHS."""

    def __init__(self, method, path):
        super().__init__(None, "PATH_NOT_ALLOWED",
                         "refusing {} {!r}: only {} may be requested".format(method, path, ", ".join(ALLOWED_PATHS)))


# --- small helpers ------------------------------------------------------------

def _text(value):
    return "" if value is None else str(value)


def ascii_fold(text):
    """Text as element_properties reports it: every non-ASCII character becomes "?"."""
    return "".join(ch if ord(ch) < 128 else "?" for ch in _text(text))


def _utc_now():
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _is_number(value):
    return isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(value)


def check_route(method, path):
    """Return the ALLOWED_PATHS entry for ``method path``; raise PathNotAllowedError otherwise."""
    method = _text(method).upper()
    if isinstance(path, str):
        for allowed in ALLOWED_PATHS:
            if allowed == _ELEMENT_PROPERTIES:
                matched = (path.startswith(allowed)
                           and _ELEMENT_ID_RE.fullmatch(path[len(allowed):]) is not None)
            else:
                matched = path == allowed
            if matched:
                if _ROUTE_METHOD[allowed] != method:
                    break
                return allowed
    raise PathNotAllowedError(method, path)


def _is_loopback_host(host):
    text = _text(host).strip().lower()
    if text == "localhost":
        return True
    try:
        return ipaddress.ip_address(text).is_loopback
    except ValueError:
        return False


def _require_loopback_base(base):
    parts = urllib.parse.urlsplit(_text(base))
    if parts.scheme != "http" or parts.username or parts.password or parts.query or parts.fragment:
        raise ValueError("Revit base URL must be a plain http:// loopback URL, got {!r}".format(base))
    if not _is_loopback_host(parts.hostname):
        raise ValueError("Revit base URL must point to loopback (127.0.0.1), got {!r}".format(base))
    parts.port  # noqa: B018 - raises ValueError for an invalid port


class _RefuseRedirect(urllib.request.HTTPRedirectHandler):
    """A redirect could lead outside ALLOWED_PATHS: never follow one."""

    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


def _default_opener():
    # No proxy (a loopback read never leaves the machine) and no redirects.
    return urllib.request.build_opener(urllib.request.ProxyHandler({}), _RefuseRedirect())


def _decode(path, status, raw):
    """Decoded JSON object of a 2xx response; RevitReadError for everything else."""
    text = bytes(raw).decode("utf-8", "replace") if isinstance(raw, (bytes, bytearray)) else _text(raw)
    body = None
    if text.strip():
        try:
            body = json.loads(text)
        except ValueError:
            body = None
    if isinstance(body, dict) and body.get("status") == "error" and isinstance(body.get("code"), str):
        # structured outcome of a DeGram route: BAD_REQUEST, DOCUMENT_NOT_OPEN, IDENTITY_MISMATCH, ROUTE_ERROR
        raise RevitReadError(status, body["code"], body.get("error") or "")
    ok = isinstance(status, int) and 200 <= status < 300
    if ok and isinstance(body, dict):
        return body
    message = ""
    if isinstance(body, dict):
        exception = body.get("exception")
        message = _text(body.get("error")) or (
            _text(exception.get("message")) if isinstance(exception, dict) else _text(exception))
    message = message or text[:300] or "HTTP {}".format(status)
    if status in (406, 408):
        raise RevitReadError(status, "BUSY", "Revit refused or timed out {} ({})".format(path, message))
    if status == 404:
        if isinstance(body, dict) and "error" in body:
            raise RevitReadError(status, "NOT_FOUND", message)
        raise RevitReadError(status, "EXTENSION_NOT_LOADED",
                             "Revit does not provide {}; the revit-mcp pyRevit extension is not loaded".format(path))
    if status == 503 and "No active Revit document" in message:
        raise RevitReadError(status, "SETUP_INCOMPLETE", "No Revit project document is open")
    if ok:
        raise RevitReadError(status, "BAD_RESPONSE", "{} did not return a JSON object".format(path))
    raise RevitReadError(status, "ROUTE_ERROR", message)


def _clamp(value, cap, name):
    if isinstance(value, bool) or not isinstance(value, int):
        raise RevitReadError(None, "BAD_REQUEST", "{} must be an integer".format(name))
    return max(1, min(value, cap))


def _pinned_identity(identity):
    if not isinstance(identity, dict) or not _text(identity.get("creationGuid")).strip():
        raise RevitReadError(None, "BAD_REQUEST", "identity.creationGuid is required (see pick_identity)")
    return {"creationGuid": _text(identity.get("creationGuid")).strip(),
            "pathName": _text(identity.get("pathName"))}


def _element_id(value):
    if isinstance(value, bool):
        value = None
    if isinstance(value, int) and value > 0:
        return value
    if isinstance(value, str) and _ELEMENT_ID_RE.fullmatch(value):
        return int(value)
    raise RevitReadError(None, "BAD_REQUEST", "element id must be a positive integer, got {!r}".format(value))


# --- read client --------------------------------------------------------------

class RevitReadClient(object):
    """Blocking client for the four read routes of the revit-mcp pyRevit extension.

    Every request is checked against ALLOWED_PATHS before it is built, carries
    ``timeout`` seconds, and POST bodies go as JSON with
    ``Content-Type: text/plain; charset=utf-8`` (pyRevit under IronPython 3.4
    cannot parse application/json; revit-mcp utils.parse_request_data).

    pyRevit Routes runs API-context handlers one at a time on the Revit API
    thread through ONE shared ExternalEvent handler, so concurrent requests can
    overwrite each other; the client therefore sends one request at a time.
    ``opener(request, timeout=...)`` is injectable for offline tests.
    """

    def __init__(self, base=DEFAULT_BASE, timeout=DEFAULT_TIMEOUT, opener=None):
        _require_loopback_base(base)
        timeout = float(timeout)
        if not (timeout > 0 and math.isfinite(timeout)):
            raise ValueError("timeout must be a positive number of seconds")
        self.base = _text(base).rstrip("/") + "/"
        self.timeout = timeout
        self._open = opener if opener is not None else _default_opener().open
        self._lock = threading.Lock()

    # -- routes --

    def status(self):
        """GET status/ -> ``{status, health, revit_available, document_title, api_name}``."""
        return self._request("GET", "status/")

    def list_open_documents(self):
        """GET list_open_documents/ -> ``{status, documents: [{title, pathName, creationGuid, isActive, isModified}]}``."""
        body = self._request("GET", "list_open_documents/")
        if not isinstance(body.get("documents"), list):
            raise RevitReadError(200, "BAD_RESPONSE", "list_open_documents returned no documents list")
        return body

    def selection_snapshot(self, identity, max_elements=MAX_ELEMENTS_CAP, max_parameters=MAX_PARAMETERS_CAP):
        """POST selection_snapshot/ for the pinned document -> ``{status, emptySelection, elements, truncation, identity}``."""
        pinned = _pinned_identity(identity)
        payload = {
            "identity": pinned,
            "max_elements": _clamp(max_elements, MAX_ELEMENTS_CAP, "max_elements"),
            "max_parameters": _clamp(max_parameters, MAX_PARAMETERS_CAP, "max_parameters"),
        }
        body = self._request("POST", "selection_snapshot/", payload)
        if not isinstance(body.get("elements"), list):
            raise RevitReadError(200, "BAD_RESPONSE", "selection_snapshot returned no elements list")
        echoed = body.get("identity")
        if isinstance(echoed, dict) and \
                _text(echoed.get("creationGuid")).strip().lower() != pinned["creationGuid"].lower():
            raise RevitReadError(200, "IDENTITY_MISMATCH", "selection_snapshot answered for another document")
        return body

    def element_properties(self, element_id):
        """GET element_properties/<id> -> ``{status, element_id, category, family, type, parameters, ...}``."""
        eid = _element_id(element_id)
        body = self._request("GET", "{}{}".format(_ELEMENT_PROPERTIES, eid))
        if body.get("element_id") != eid:
            raise RevitReadError(200, "RESPONSE_MISMATCH",
                                 "asked for element {}, got {!r}".format(eid, body.get("element_id")))
        return body

    # -- transport --

    def _request(self, method, path, payload=None):
        check_route(method, path)
        headers = {"Accept": "application/json"}
        data = None
        if method == "POST":
            data = json.dumps({} if payload is None else payload, ensure_ascii=False).encode("utf-8")
            headers["Content-Type"] = "text/plain; charset=utf-8"
        request = urllib.request.Request(self.base + path, data=data, headers=headers, method=method)
        with self._lock:
            status, raw = self._send(request, path)
        return _decode(path, status, raw)

    def _send(self, request, path):
        busy = "Revit did not answer {} within {:g} s (a dialog may be open)".format(path, self.timeout)
        try:
            response = self._open(request, timeout=self.timeout)
        except urllib.error.HTTPError as exc:
            try:
                raw = exc.read()
            except Exception:
                raw = b""
            return exc.code, raw
        except urllib.error.URLError as exc:
            if isinstance(exc.reason, TimeoutError):
                raise RevitReadError(None, "BUSY", busy)
            raise RevitReadError(None, "BRIDGE_OFF", "cannot reach Revit at {} ({})".format(self.base, exc.reason))
        except TimeoutError:
            raise RevitReadError(None, "BUSY", busy)
        except (OSError, http.client.HTTPException) as exc:
            raise RevitReadError(None, "BRIDGE_OFF", "cannot reach Revit at {} ({})".format(self.base, exc))
        try:
            status = getattr(response, "status", None)
            if status is None:
                status = response.getcode()
            raw = response.read()
        except TimeoutError:
            raise RevitReadError(None, "BUSY", busy)
        except (OSError, http.client.HTTPException) as exc:
            raise RevitReadError(None, "ROUTE_ERROR", "reading {} failed: {}".format(path, exc))
        finally:
            close = getattr(response, "close", None)
            if callable(close):
                close()
        return status, raw


def pick_identity(documents):
    """The single active document as ``{creationGuid, pathName}``.

    ``documents`` is the list_open_documents response or its ``documents`` list.
    """
    rows = documents.get("documents") if isinstance(documents, dict) else documents
    rows = [row for row in (rows or []) if isinstance(row, dict)]
    active = [row for row in rows if row.get("isActive") is True]
    if not active:
        raise RevitReadError(None, "NO_ACTIVE_DOCUMENT",
                             "no open Revit project document is active ({} open)".format(len(rows)))
    if len(active) > 1:
        raise RevitReadError(None, "AMBIGUOUS_ACTIVE_DOCUMENT",
                             "{} open documents report isActive".format(len(active)))
    guid = _text(active[0].get("creationGuid")).strip()
    if not guid:
        raise RevitReadError(None, "BAD_RESPONSE", "the active document has no creationGuid")
    return {"creationGuid": guid, "pathName": _text(active[0].get("pathName"))}


# --- conversion ---------------------------------------------------------------

def is_length_unit(label):
    """True when a Double parameter's unit label is a length unit (raw value = feet)."""
    text = " {} ".format(_text(label).strip().lower())
    if not text.strip():
        return False
    if any(marker in text for marker in _NOT_LENGTH_MARKERS):
        return False
    if any(marker in text for marker in _LENGTH_MARKERS):
        return True
    return any(token in _LENGTH_TOKENS for token in re.split(r"[^a-zа-яё]+", text))


def length_in_metres(row):
    """Metres for a snapshot parameter row holding a length, else None.

    The snapshot ``value`` of a Double parameter is Revit's internal value, which
    is always feet for lengths whatever the display unit (``displayValue``/``unit``).
    """
    if _text(row.get("storageType")) != "Double" or not is_length_unit(row.get("unit")):
        return None
    value = row.get("value")
    if not _is_number(value):
        return None
    return round(float(value) * FEET_TO_METRES, 9)


def _parameter_value(row):
    display = row.get("displayValue")
    if isinstance(display, str) and display.strip():
        return display
    value = row.get("value")
    if isinstance(value, str):
        return value if value.strip() else None
    return value if _is_number(value) else None


def _ifc_split(text, entity_parameter):
    head, _, tail = text.partition(".")
    if head[:3].lower() == "ifc":  # "IfcPlate" or "IfcPlate.CURTAIN_PANEL"
        return head.strip(), (tail.strip() or None)
    if entity_parameter:  # e.g. "DontExport"
        return text, None
    return None, text  # a predefined type such as "USERDEFINED"


def ifc_from_parameters(pairs):
    """``{entity, predefinedType}`` from (name, value) pairs in priority order, or None.

    The first non-empty value wins per field. A predefined-type parameter whose
    value names an entity ("Ifc...") is used as an entity hint instead.
    """
    entity = predefined = None
    for name, value in pairs:
        key = _text(name).strip().casefold()
        if key in _IFC_ENTITY_KEYS:
            entity_parameter = True
        elif key in _IFC_PREDEFINED_KEYS:
            entity_parameter = False
        else:
            continue
        text = _text(value).strip()
        if not text:
            continue
        found_entity, found_predefined = _ifc_split(text, entity_parameter)
        if entity is None and found_entity:
            entity = found_entity
        if predefined is None and found_predefined:
            predefined = found_predefined
    if entity is None and predefined is None:
        return None
    return {"entity": entity, "predefinedType": predefined}


def _family_from_snapshot(rows):
    """Unicode-safe family name from snapshot instance parameters, or ""."""
    for row in rows:
        name = _text(row.get("name")).strip()
        value = _text(row.get("displayValue")).strip()
        if not value:
            continue
        if name in FAMILY_PARAMETERS:
            return value
        if name in FAMILY_AND_TYPE_PARAMETERS and ": " in value:
            return value.split(": ", 1)[0].strip()
    return ""


def element_to_descriptor(element, properties=None):
    """One snapshot element (+ its optional element_properties response) -> ElementDescriptor."""
    native_id = _text(element.get("uniqueId")).strip()
    if not native_id:
        return None
    rows = [row for row in (element.get("parameters") or []) if isinstance(row, dict)]
    category = _text(element.get("category"))
    type_name = _text(element.get("typeName"))
    family = ""
    if isinstance(properties, dict):
        family = _text(properties.get("family"))
        category = category or _text(properties.get("category"))
        type_name = type_name or _text(properties.get("type"))
    if not family or "?" in family:
        family = _family_from_snapshot(rows) or family

    parameters = {}
    for row in rows:
        name = _text(row.get("name")).strip()
        value = _parameter_value(row)
        if name and value is not None and name not in parameters:
            parameters[name] = value
    for row in rows:
        metres = length_in_metres(row)
        name = _text(row.get("name")).strip()
        if name and metres is not None:
            parameters.setdefault(name + "_m", metres)

    property_rows = []
    if isinstance(properties, dict):
        property_rows = [p for p in (properties.get("parameters") or []) if isinstance(p, dict)]
        for prop in property_rows:  # mostly type parameters; snapshot rows are instance-only
            name = _text(prop.get("name")).strip()
            value = _text(prop.get("value"))
            if name and "?" not in name and value.strip() and name not in parameters:
                parameters[name] = value

    pairs = [(row.get("name"), _parameter_value(row)) for row in rows]
    pairs += [(prop.get("name"), prop.get("value")) for prop in property_rows]
    ifc = ifc_from_parameters(pairs)

    if any("?" in text for text in (category, family, type_name)):
        parameters[NON_ASCII_MARKER] = True

    descriptor = {"nativeId": native_id, "platform": PLATFORM}
    if category:
        descriptor["category"] = category
    if family:
        descriptor["family"] = family
    if type_name:
        descriptor["type"] = type_name
    if family and type_name:
        descriptor["name"] = "{} : {}".format(family, type_name)
    if ifc is not None:
        descriptor["ifc"] = ifc
    descriptor["parameters"] = parameters
    return descriptor


def _properties_lookup(properties_by_element_id):
    lookup = {}
    for key, value in (properties_by_element_id or {}).items():
        try:
            lookup[_element_id(key)] = value
        except RevitReadError:
            continue
    return lookup


def snapshot_to_descriptors(snapshot, properties_by_element_id=None):
    """selection_snapshot response (+ element_properties responses by element id) -> descriptors.

    Elements without a uniqueId and repeated uniqueIds are skipped; order is kept.
    """
    elements = snapshot.get("elements") if isinstance(snapshot, dict) else None
    if not isinstance(elements, list):
        raise ValueError("snapshot has no 'elements' list")
    lookup = _properties_lookup(properties_by_element_id)
    descriptors, seen = [], set()
    for element in elements:
        if not isinstance(element, dict):
            continue
        properties = None
        try:
            properties = lookup.get(_element_id(element.get("elementId")))
        except RevitReadError:
            pass
        descriptor = element_to_descriptor(element, properties)
        if descriptor is None or descriptor["nativeId"] in seen:
            continue
        seen.add(descriptor["nativeId"])
        descriptors.append(descriptor)
    return descriptors


def properties_mismatch(element, properties):
    """Why an element_properties response does not belong to a snapshot element, or None.

    element_properties reads the active document by element id only, so a
    document switched during the read would answer for a different element.
    """
    try:
        same_element = _element_id(properties.get("element_id")) == _element_id(element.get("elementId"))
    except RevitReadError:
        same_element = False
    if not same_element:
        return "element_id {!r} != {!r}".format(properties.get("element_id"), element.get("elementId"))
    for snapshot_key, properties_key in (("category", "category"), ("typeName", "type")):
        expected = ascii_fold(element.get(snapshot_key))
        actual = _text(properties.get(properties_key))
        if expected and actual and expected != actual:
            return "{} differs: snapshot {!r}, element_properties {!r}".format(properties_key, expected, actual)
    return None


def _failure(element, code, detail):
    return {"elementId": element.get("elementId"), "uniqueId": element.get("uniqueId"),
            "code": code, "detail": detail}


def collect_properties(elements, fetch, max_workers=1):
    """Call ``fetch(element_id)`` per element; return ``(properties_by_id, failures, requested)``.

    Failures are recorded per element and never raised. ``max_workers`` > 1 uses
    a thread pool (the Revit client still sends one request at a time).
    """
    targets = []
    for element in elements:
        try:
            _element_id(element.get("elementId"))
        except RevitReadError:
            continue
        targets.append(element)

    def one(element):
        eid = element["elementId"]
        try:
            properties = fetch(eid)
        except RevitReadError as exc:
            return eid, None, _failure(element, exc.code, exc.detail)
        except Exception as exc:  # never fatal: record and continue
            return eid, None, _failure(element, "CLIENT_ERROR", str(exc))
        if not isinstance(properties, dict):
            return eid, None, _failure(element, "BAD_RESPONSE", "element_properties returned no object")
        reason = properties_mismatch(element, properties)
        if reason:
            return eid, None, _failure(element, "ELEMENT_MISMATCH", reason)
        return eid, properties, None

    workers = max(1, int(max_workers))
    if workers == 1 or len(targets) <= 1:
        results = [one(element) for element in targets]
    else:
        with ThreadPoolExecutor(max_workers=min(workers, len(targets))) as pool:
            results = list(pool.map(one, targets))
    by_id, failures = {}, []
    for eid, properties, failure in results:
        if failure is not None:
            failures.append(failure)
        else:
            by_id[eid] = properties
    return by_id, failures, len(targets)


def read_selection(client, with_properties=True, max_workers=1,
                   max_elements=MAX_ELEMENTS_CAP, max_parameters=MAX_PARAMETERS_CAP):
    """Read the current Revit selection -> ``(identity, descriptors, truncation)``.

    ``truncation`` is the snapshot's truncation block plus ``propertiesRequested``
    and ``propertiesFailed`` (per-element element_properties failures).
    """
    client.status()
    identity = pick_identity(client.list_open_documents())
    snapshot = client.selection_snapshot(identity, max_elements=max_elements, max_parameters=max_parameters)
    elements = [element for element in snapshot.get("elements") or [] if isinstance(element, dict)]
    truncation = dict(snapshot.get("truncation") or {})
    properties = None
    if with_properties:
        properties, failures, requested = collect_properties(elements, client.element_properties, max_workers)
        truncation["propertiesRequested"] = requested
        truncation["propertiesFailed"] = failures
    descriptors = snapshot_to_descriptors(snapshot, properties)
    echoed = snapshot.get("identity")
    if isinstance(echoed, dict) and _text(echoed.get("creationGuid")).strip():
        identity = {"creationGuid": _text(echoed.get("creationGuid")),
                    "pathName": _text(echoed.get("pathName"))}
    return identity, descriptors, truncation


# --- upload body, fixtures and CLI ---------------------------------------------

def build_upload_body(project, label, identity, descriptors, truncation=None, read_at=None, dry_run=False):
    """Body of POST /mapping/sessions (1303-API-CONTRACT section 2) plus a ``source`` block."""
    identity = identity if isinstance(identity, dict) else {}
    source = {
        "document": _text(identity.get("pathName")),
        "creationGuid": _text(identity.get("creationGuid")),
        "readAt": read_at or _utc_now(),
    }
    if dry_run:
        source["dryRun"] = True
    if truncation:
        source["truncation"] = truncation
    return {"project": project, "platform": PLATFORM, "label": label, "source": source,
            "elements": list(descriptors)}


def _load_json(path):
    with open(path, "r", encoding="utf-8-sig") as handle:
        return json.load(handle)


def load_properties_fixture(path):
    """element_properties responses saved as ``{"responses": [...]}`` or a list -> ``{element_id: response}``."""
    data = _load_json(path)
    responses = data.get("responses") if isinstance(data, dict) else data
    if not isinstance(responses, list):
        raise ValueError("{}: expected a 'responses' list of element_properties bodies".format(path))
    by_id = {}
    for response in responses:
        if isinstance(response, dict):
            try:
                by_id[_element_id(response.get("element_id"))] = response
            except RevitReadError:
                continue
    return by_id


def convert_fixture(snapshot_path, properties_path=None):
    """Offline conversion of a saved selection_snapshot -> ``(identity, descriptors, truncation)``."""
    snapshot = _load_json(snapshot_path)
    if not isinstance(snapshot, dict) or not isinstance(snapshot.get("elements"), list):
        raise ValueError("{}: not a selection_snapshot response (no 'elements' list)".format(snapshot_path))
    elements = [element for element in snapshot["elements"] if isinstance(element, dict)]
    truncation = dict(snapshot.get("truncation") or {})
    properties = None
    if properties_path:
        saved = load_properties_fixture(properties_path)

        def fetch(eid):
            if eid not in saved:
                raise RevitReadError(None, "NOT_IN_FIXTURE", "no saved element_properties response")
            return saved[eid]

        properties, failures, requested = collect_properties(elements, fetch)
        truncation["propertiesRequested"] = requested
        truncation["propertiesFailed"] = failures
    identity = snapshot.get("identity") if isinstance(snapshot.get("identity"), dict) else {}
    return identity, snapshot_to_descriptors(snapshot, properties), truncation


_HINTS = {
    "BRIDGE_OFF": "Open Revit with the facade model, enable pyRevit Routes (host 127.0.0.1) and load the "
                  "revit-mcp extension; check http://127.0.0.1:48884/revit_mcp/status/ in a browser.",
    "EXTENSION_NOT_LOADED": "The revit-mcp pyRevit extension is not loaded or is another version; reload pyRevit.",
    "SETUP_INCOMPLETE": "Open the facade project in Revit (not only the start screen).",
    "NO_ACTIVE_DOCUMENT": "Make the facade project the active Revit document.",
    "AMBIGUOUS_ACTIVE_DOCUMENT": "Close the other open copies of the project and retry.",
    "IDENTITY_MISMATCH": "The active Revit document changed during the read; activate the facade model and retry.",
    "DOCUMENT_NOT_OPEN": "The facade model was closed during the read; open it, select the elements and retry.",
    "BUSY": "Close any open Revit dialog, finish the current command (Esc) and retry; "
            "a large selection may need --timeout 120.",
}


def _summary(out, identity, descriptors, truncation, with_properties):
    lines = ["Revit document: {} (creationGuid {})".format(
        _text(identity.get("pathName")) or "<unsaved>", _text(identity.get("creationGuid")))]
    total = truncation.get("elementsTotal")
    kept = truncation.get("elementsKept")
    lines.append("Descriptors: {} (selected {}, read {})".format(len(descriptors), total, kept))
    if _is_number(total) and _is_number(kept) and total > kept:
        lines.append("WARNING: only {} of {} selected elements were read (cap {}).".format(
            kept, total, truncation.get("maxElements")))
    if truncation.get("parametersTruncated"):
        lines.append("Note: {} parameters were dropped by the per-element cap {}.".format(
            truncation.get("parametersTruncated"), truncation.get("maxParameters")))
    counts = {}
    for descriptor in descriptors:
        key = (descriptor.get("category") or "(no category)", descriptor.get("family") or "(no family)")
        counts[key] = counts.get(key, 0) + 1
    lines.append("By category / family:")
    for (category, family), count in sorted(counts.items()):
        lines.append("  {} / {}: {}".format(category, family, count))
    marked = sum(1 for d in descriptors if d["parameters"].get(NON_ASCII_MARKER))
    if marked:
        lines.append("Note: {} elements have non-ASCII names reported as '?' ({}).".format(marked, NON_ASCII_MARKER))
    if with_properties:
        failed = truncation.get("propertiesFailed") or []
        lines.append("element_properties: requested {}, failed {}".format(
            truncation.get("propertiesRequested", 0), len(failed)))
        codes = {}
        for failure in failed:
            codes[failure["code"]] = codes.get(failure["code"], 0) + 1
        for code, count in sorted(codes.items()):
            lines.append("  {}: {}".format(code, count))
    lines.append("Wrote {}".format(out))
    lines.append("Next: Web UI -> Projects -> Mapping -> Import descriptors (JSON).")
    return "\n".join(lines)


def build_parser():
    parser = argparse.ArgumentParser(
        prog="revit_read.py",
        description="Read the elements selected in Revit through the read-only revit-mcp routes on "
                    "127.0.0.1:48884 and write a DG mapping upload file (POST /mapping/sessions body). "
                    "Never writes to Revit, never contacts DG, never handles credentials.")
    parser.add_argument("--out", required=True, help="upload file to write (JSON)")
    parser.add_argument("--project", default=DEFAULT_PROJECT, help="DG project (default %(default)s)")
    parser.add_argument("--label", default=DEFAULT_LABEL, help="session label (default %(default)s)")
    parser.add_argument("--no-properties", action="store_true",
                        help="skip element_properties calls (faster; no family names)")
    parser.add_argument("--workers", type=int, default=1,
                        help="element_properties worker threads (default 1 = sequential)")
    parser.add_argument("--timeout", type=float, default=DEFAULT_TIMEOUT,
                        help="seconds per Revit request (default %(default)s)")
    parser.add_argument("--dry-run-fixture", metavar="SNAPSHOT_JSON",
                        help="convert a saved selection_snapshot response instead of reading Revit")
    parser.add_argument("--properties-fixture", metavar="PROPERTIES_JSON",
                        help="with --dry-run-fixture: saved element_properties responses")
    return parser


def main(argv=None, client=None):
    parser = build_parser()
    args = parser.parse_args(argv)
    if args.properties_fixture and not args.dry_run_fixture:
        parser.error("--properties-fixture needs --dry-run-fixture")
    if args.workers < 1:
        parser.error("--workers must be at least 1")
    if not (args.timeout > 0 and math.isfinite(args.timeout)):
        parser.error("--timeout must be a positive number")
    if not args.project.strip() or not args.label.strip():
        parser.error("--project and --label must not be empty")
    for stream in (sys.stdout, sys.stderr):
        reconfigure = getattr(stream, "reconfigure", None)
        if callable(reconfigure):
            reconfigure(errors="replace")

    with_properties = not args.no_properties
    try:
        if args.dry_run_fixture:
            identity, descriptors, truncation = convert_fixture(args.dry_run_fixture, args.properties_fixture)
            with_properties = bool(args.properties_fixture)
        else:
            if client is None:
                client = RevitReadClient(timeout=args.timeout)
            identity, descriptors, truncation = read_selection(
                client, with_properties=with_properties, max_workers=args.workers)
    except RevitReadError as exc:
        print("error: Revit read failed: {}".format(exc), file=sys.stderr)
        if exc.code in _HINTS:
            print("hint: " + _HINTS[exc.code], file=sys.stderr)
        return 1
    except (OSError, ValueError) as exc:
        print("error: {}".format(exc), file=sys.stderr)
        return 1

    if not descriptors:
        print("error: nothing to write: the Revit selection is empty (select the facade elements in "
              "Revit, then run again).", file=sys.stderr)
        return 3

    body = build_upload_body(args.project.strip(), args.label.strip(), identity, descriptors,
                             truncation, dry_run=bool(args.dry_run_fixture))
    out = Path(args.out)
    try:
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(json.dumps(body, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n")
    except OSError as exc:
        print("error: cannot write {}: {}".format(out, exc), file=sys.stderr)
        return 1
    print(_summary(out, identity, descriptors, truncation, with_properties))
    return 0


if __name__ == "__main__":
    sys.exit(main())
