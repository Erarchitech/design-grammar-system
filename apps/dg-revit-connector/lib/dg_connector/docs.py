# -*- coding: utf-8 -*-
from __future__ import unicode_literals

"""Document key and session label (D-48, contract section 8.2).

The Grasshopper connector labels a mapping session with the key of the
Grasshopper document; the Revit connector does the same with the file name of
the ``.rvt`` project. The rule is the Grasshopper ``DocumentKey`` rule:

* take the file name: drop every directory part (Windows ``\\`` and ``/``);
* drop a trailing ``.rvt`` / ``.rfa`` / ``.gh`` / ``.ghx`` (case-insensitive);
* trim, lower-case;
* replace every character that is not alphanumeric, ``-`` or ``_`` with ``-``
  (Cyrillic letters are alphanumeric, so they survive).

``AdaptComponent_V18-dg-mapping.rvt`` -> ``adaptcomponent_v18-dg-mapping``.

The session label is ``"<key> · HH:MM:SS"`` with the local time of the
``datetime`` that is passed in.

Standard library only; Python 3.4 syntax (IronPython 3.4 under Revit).
"""

import datetime
import re

#: Key used when there is no file name at all (an unsaved document).
DEFAULT_KEY = "revit"

#: Label separator: space, U+00B7 MIDDLE DOT, space.
LABEL_SEPARATOR = " \u00b7 "

DOCUMENT_EXTENSIONS = (".rvt", ".rfa", ".gh", ".ghx")

_PATH_SPLIT = re.compile(r"[\\/]")


def _file_name(path_or_title):
    """Last path segment of ``path_or_title``, or "" when it has none."""
    parts = [part for part in _PATH_SPLIT.split(_text(path_or_title)) if part]
    return parts[-1] if parts else ""


def _text(value):
    """Text without converting IronPython 2 Unicode through an ASCII str."""
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


def _strip_extension(name):
    lowered = name.lower()
    for extension in DOCUMENT_EXTENSIONS:
        if lowered.endswith(extension):
            return name[:-len(extension)]
    return name


def document_key(path_or_title):
    """Document key of a Revit/Grasshopper path, file name or document title.

    ``document_key("C:\\\\Models\\\\AdaptComponent_V18-dg-mapping.rvt")`` and
    ``document_key("AdaptComponent_V18-dg-mapping.rvt")`` both give
    ``"adaptcomponent_v18-dg-mapping"``. An empty input gives ``"revit"``.
    """
    name = _strip_extension(_file_name(path_or_title).strip()).strip()
    if not name:
        return DEFAULT_KEY
    characters = []
    for character in name.lower():
        if character.isalnum() or character == "-" or character == "_":
            characters.append(character)
        else:
            characters.append("-")
    return "".join(characters)


def session_label(key, now=None):
    """``"<key> · HH:MM:SS"`` for the local time of the datetime ``now``.

    ``now`` defaults to the current local time. A missing or empty key falls
    back to ``"revit"`` so the label is never just the time.
    """
    label_key = _text(key).strip() or DEFAULT_KEY
    if now is None:
        now = datetime.datetime.now()
    stamp = now.strftime("%H:%M:%S")
    return "{}{}{}".format(label_key, LABEL_SEPARATOR, stamp)
