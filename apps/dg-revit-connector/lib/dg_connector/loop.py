# -*- coding: utf-8 -*-
"""Poll decision of the Revit apply loop (D-47, D-50, contract section 8.4).

The connector polls the open mapping session every :data:`POLL_SECONDS`. This
module is the pure brain of that loop: it looks at one MappingSession dict and
returns what the Revit side should do next. It has no clock, no network and no
Revit dependency, so the whole loop is testable offline.

``next_action(session, memo, now)`` returns::

    {"action": "recolour" | "apply" | "done" | "idle",
     "digest": "<sha1 of the element states>",
     "batch": <explicit queued batch, only for apply>}

Priority (highest first):

``done``
    ``session.appliedAt`` is set: the session is applied, the loop stops.
``recolour``
    The digest of ``(nativeId, state, sorted role IRIs)`` differs from
    ``memo["lastDigest"]`` - element states changed, paint the view. The
    caller recolours and then stores ``digest`` in ``memo["lastDigest"]``.
``apply``
    An explicit batch has queued delivery, even if other questions remain.
``idle``
    No committed batch awaits delivery. Answers and elapsed time never trigger
    a write; draft answers can still be undone.

``states_by_uid`` and ``roles_by_uid`` give the Revit writer the two lookups it
needs (``{nativeId: state}`` and ``{nativeId: [class label]}``); when a role
carries no label the local name of its ``classIri`` is used.

Standard library only; Python 2.7 / 3 syntax (pyRevit's IronPython 2.7 under Revit).
"""
from __future__ import unicode_literals

import datetime
import hashlib
import re

#: Seconds between two polls of the open session.
POLL_SECONDS = 3

#: Actions :func:`next_action` can return.
ACTIONS = ("recolour", "apply", "done", "idle")

_EPOCH_ORDINAL = (datetime.date(1970, 1, 1)).toordinal()

_ISO_RE = re.compile(
    r"^(\d{4})-(\d{2})-(\d{2})[Tt ](\d{2}):(\d{2})"
    r"(?::(\d{2})(?:\.(\d{1,6}))?)?"
    r"(Z|z|[+-]\d{2}:?\d{2})?$")


# --- small helpers ------------------------------------------------------------

def _text(value):
    """Keep IronPython 2 Unicode class labels intact for state digests."""
    if value is None:
        return u""
    try:
        if isinstance(value, unicode):
            return value
        if isinstance(value, str):
            return value.decode("utf-8", "replace")
    except NameError:
        if isinstance(value, str):
            return value
    try:
        return unicode(value)
    except NameError:
        return str(value)


def _datetime_to_epoch(moment):
    """Epoch seconds of a datetime; a naive datetime is read as UTC."""
    if moment.tzinfo is not None:
        offset = moment.utcoffset()
        if offset is not None:
            moment = moment - offset  # same wall clock, now in UTC
    days = moment.date().toordinal() - _EPOCH_ORDINAL
    return (days * 86400.0 + moment.hour * 3600 + moment.minute * 60 + moment.second
            + moment.microsecond / 1000000.0)


def to_epoch(value):
    """Epoch seconds of an ISO-8601 string, datetime or number, or None.

    Understands the ``...Z`` timestamps of the mapping API, fractional seconds
    and numeric offsets (``+03:00``); a missing offset means UTC. An
    unparseable value gives None instead of raising.
    """
    if isinstance(value, datetime.datetime):
        return _datetime_to_epoch(value)
    if isinstance(value, bool):
        return None
    if isinstance(value, (int, float)):
        return float(value)
    text = _text(value).strip()
    if not text:
        return None
    match = _ISO_RE.match(text)
    if match is None:
        try:
            return float(text)
        except ValueError:
            return None
    parts = [int(match.group(index)) for index in (1, 2, 3, 4, 5)]
    second = int(match.group(6) or 0)
    fraction = match.group(7)
    microsecond = int((fraction or "0").ljust(6, "0")[:6]) if fraction else 0
    zone = match.group(8)
    offset = 0
    if zone and zone.lower() != "z":
        digits = zone[1:].replace(":", "")
        offset = int(digits[:2]) * 3600 + int(digits[2:4]) * 60
        if zone[0] == "-":
            offset = -offset
    try:
        moment = datetime.datetime(parts[0], parts[1], parts[2], parts[3], parts[4],
                                   second, microsecond)
    except ValueError:
        return None
    return _datetime_to_epoch(moment) - offset


def _elements(session):
    if not isinstance(session, dict):
        return []
    elements = session.get("elements")
    if not isinstance(elements, list):
        return []
    return [element for element in elements if isinstance(element, dict)]


def _role_iris(element):
    iris = []
    records = element.get("roles")
    for role in records if isinstance(records, list) else []:
        if not isinstance(role, dict):
            continue
        iri = _text(role.get("classIri")).strip() or _text(role.get("label")).strip()
        if iri:
            iris.append(iri)
    return sorted(iris)


def _local_name(iri):
    """Local name of an IRI: the parts after the last ``#``, ``/`` or ``:``."""
    text = _text(iri).strip()
    for separator in ("#", "/", ":"):
        if separator in text:
            text = text.rsplit(separator, 1)[1]
    return text


def session_digest(session):
    """SHA-1 of the sorted ``(nativeId, state, sorted role IRIs)`` rows.

    The digest identifies the state of every element of the session; it changes
    exactly when a state or a role changes, so it is the "needs recolour" flag.
    Encoding, so any client can reproduce it: one ``nativeId|state|iri1,iri2``
    line per element, rows sorted as tuples, lines joined with ``"\\n"``,
    UTF-8, hex SHA-1. Elements without a nativeId are ignored.
    """
    rows = []
    for element in _elements(session):
        native_id = _text(element.get("nativeId")).strip()
        if not native_id:
            continue
        rows.append((native_id, _text(element.get("state")).strip(), tuple(_role_iris(element))))
    rows.sort()
    lines = ["{}|{}|{}".format(native_id, state, ",".join(iris)) for native_id, state, iris in rows]
    digest = hashlib.sha1("\n".join(lines).encode("utf-8"))
    return digest.hexdigest()


def next_action(session, memo, now=None):
    """What the Revit apply loop does next with ``session`` (see module docstring).

    ``memo`` is the caller's dict kept between polls; ``memo["lastDigest"]`` is
    the digest of the states the view was last painted with. On ``recolour``
    the caller stores the returned ``digest`` there. ``now`` is retained for
    compatibility with callers; time does not authorize delivery.
    """
    digest = session_digest(session)
    result = {"action": "idle", "digest": digest}
    if not isinstance(session, dict):
        return result
    if not isinstance(session.get("elements"), list) and not isinstance(session.get("summary"), dict):
        return result  # not a MappingSession answer: nothing to paint or decide
    if _text(session.get("appliedAt")).strip():
        result["action"] = "done"
        return result

    last_digest = memo.get("lastDigest") if isinstance(memo, dict) else None
    if last_digest != digest:
        result["action"] = "recolour"
        return result

    # Even a fully answered session is a draft until the owner's explicit commit.
    for batch in session.get("batches") or []:
        if isinstance(batch, dict) and (batch.get("delivery") or {}).get("state") == "queued":
            result["action"] = "apply"
            result["batch"] = batch
            break
    return result


def states_by_uid(session):
    """``{nativeId: state}`` of a MappingSession for the Revit colour writer."""
    states = {}
    for element in _elements(session):
        native_id = _text(element.get("nativeId")).strip()
        if native_id:
            states[native_id] = _text(element.get("state")).strip()
    return states


def roles_by_uid(session):
    """``{nativeId: [class label]}`` of a MappingSession for DG_Class."""
    roles = {}
    for element in _elements(session):
        native_id = _text(element.get("nativeId")).strip()
        if not native_id:
            continue
        labels = []
        records = element.get("roles")
        for role in records if isinstance(records, list) else []:
            if not isinstance(role, dict):
                continue
            label = _text(role.get("label")).strip() or _local_name(role.get("classIri"))
            if label and label not in labels:
                labels.append(label)
        roles[native_id] = labels
    return roles
