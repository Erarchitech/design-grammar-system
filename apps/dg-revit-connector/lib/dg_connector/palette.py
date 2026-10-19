# -*- coding: utf-8 -*-
from __future__ import unicode_literals

"""Mapping state -> RGB colour, the Grasshopper/Rhino palette (D-50).

The Revit connector paints solid-fill graphic overrides in the active view with
exactly these colours, so a Revit view and a Grasshopper preview show the same
state the same way (``DG.Grasshopper/Mapping/MappingPreviewConduit.cs``).

Standard library only; Python 3.4 syntax (IronPython 3.4 under Revit).
"""

#: State name -> (red, green, blue), each 0..255.
STATE_COLOURS = {
    "confirmed": (0x2E, 0x7D, 0x32),   # green
    "auto": (0x15, 0x65, 0xC0),        # blue, assigned by a learned profile
    "suggested": (0xF9, 0xA8, 0x25),   # amber
    "ambiguous": (0xE6, 0x51, 0x00),   # orange
    "unmapped": (0x9E, 0x9E, 0x9E),    # grey
}

#: Colour of an element whose state is unknown or missing.
UNMAPPED_COLOUR = STATE_COLOURS["unmapped"]


def colour_for(state):
    """RGB tuple for a mapping state; an unknown or missing state is unmapped grey."""
    if state is None:
        key = u""
    else:
        try:
            key = state if isinstance(state, unicode) else unicode(state)
        except NameError:
            key = str(state)
        key = key.strip().lower()
    return STATE_COLOURS.get(key, UNMAPPED_COLOUR)
