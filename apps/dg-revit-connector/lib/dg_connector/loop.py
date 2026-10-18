# -*- coding: utf-8 -*-
"""Poll decision of the Revit apply loop (D-47, D-50, contract section 8.4).

The connector polls the open mapping session every :data:`POLL_SECONDS`. This
module is the pure brain of that loop: it looks at one MappingSession dict and
returns what the Revit side should do next. It has no clock, no network and no
Revit dependency, so the whole loop is testable offline.

``next_action(session, memo, now)`` returns::

    {"action": "recolour" | "wait-grace" | "apply" | "done" | "idle",
     "digest": "<sha1 of the element states>",
     "secondsLeft": <float, only for wait-grace>}

Priority (highest first):

``done``
    ``session.appliedAt`` is set: the session is applied, the loop stops.
``recolour``
    The digest of ``(nativeId, state, sorted role IRIs)`` differs from
    ``memo["lastDigest"]`` - element states changed, paint the view. The
    caller recolours and then stores ``digest`` in ``memo["lastDigest"]``.
``wait-grace``
    ``summary.openQuestions == 0``, the session is not applied, and less than
    :data:`GRACE_SECONDS` have passed since the newest ``answers[].decidedAt``
    (or since ``createdAt`` when there is no answer yet): the last answer can
    still be undone, so apply waits. ``secondsLeft`` is what remains.
``apply``
    No open question, not applied, grace elapsed: apply now.
``idle``
    Anything else: open questions remain, or the session is not usable yet.

``states_by_uid`` and ``roles_by_uid`` give the Revit writer the two lookups it
needs (``{nativeId: state}`` and ``{nativeId: [class label]}``); when a role
carries no label the local name of its ``classIri`` is used.

Standard library only; Python 3.4 syntax (IronPython 3.4 under Revit).
"""

import datetime
import hashlib
import re

#: Seconds the connector waits after the newest answer before it applies, so
#: the answer can still be undone (D-40 analogue).
GRACE_SECONDS = 10

#: Seconds between two polls of the open session.
POLL_SECONDS = 3

#: Actions :func:`next_action` can return.
ACTIONS = ("recolour", "wait-grace", "apply", "done", "idle")

_EPOCH_ORDINAL = (datetime.date(1970, 1, 1)).toordinal()

_ISO_RE = re.compile(
    r"^(\d{4})-(\d{2})-(\d{2})[Tt ](\d{2}):(\d{2})"
    r"(?::(\d{2})(?:\.(\d{1,6}))?)?"
    r"(Z|z|[+-]\d{2}:?\d{2})?$")


# --- small helpers ------------------------------------------------------------

def _text(value):
    return "" if value is None else str(value)


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


def _open_questions(session):
    """``summary.openQuestions`` as an int, or None when it is not reported."""
    if not isinstance(session, dict):
        return None
    summary = session.get("summary")
    if not isinstance(summary, dict):
        return None
    count = summary.get("openQuestions")
    if isinstance(count, bool) or not isinstance(count, int):
        return None
    return count


def _grace_reference(session):
    """Epoch seconds of the newest answer, else of the session creation, or None."""
    newest = None
    answers = session.get("answers")
    for answer in answers if isinstance(answers, list) else []:
        if not isinstance(answer, dict):
            continue
        moment = to_epoch(answer.get("decidedAt"))
        if moment is not None and (newest is None or moment > newest):
            newest = moment
    if newest is not None:
        return newest
    return to_epoch(session.get("createdAt"))


def next_action(session, memo, now=None):
    """What the Revit apply loop does next with ``session`` (see module docstring).

    ``memo`` is the caller's dict kept between polls; ``memo["lastDigest"]`` is
    the digest of the states the view was last painted with. On ``recolour``
    the caller stores the returned ``digest`` there. ``now`` is a datetime
    (naive means UTC) or an epoch number; it defaults to the current UTC time.
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

    if _open_questions(session) != 0:
        return result  # answers are still missing (or the summary is unusable)

    reference = _grace_reference(session)
    moment = to_epoch(now) if now is not None else _datetime_to_epoch(datetime.datetime.utcnow())
    if reference is not None and moment is not None:
        elapsed = moment - reference
        if elapsed < GRACE_SECONDS:
            seconds_left = GRACE_SECONDS - elapsed
            if seconds_left > GRACE_SECONDS:  # decidedAt in the future: clock skew
                seconds_left = float(GRACE_SECONDS)
            if seconds_left < 0:
                seconds_left = 0.0
            result["action"] = "wait-grace"
            result["secondsLeft"] = round(seconds_left, 3)
            return result
    result["action"] = "apply"
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
