# -*- coding: UTF-8 -*-
"""«Очистить цвета» - remove the mapping graphic overrides (D-50).

Clears the solid-fill overrides the connector painted for the open mapping
session in the session view. The session, its answers and the
``DG_Class`` / ``DG_MappingState`` parameters are left alone.
"""

import os
import sys

from pyrevit import forms


def ensure_lib():
    """Put ``<extension>/lib`` first on sys.path and return it."""
    here = os.path.dirname(os.path.abspath(__file__))
    pushbutton = os.path.dirname(here)
    panel = os.path.dirname(pushbutton)
    tab = os.path.dirname(panel)
    extension = os.path.dirname(tab)
    lib = os.path.join(extension, "lib")
    if lib not in sys.path:
        sys.path.insert(0, lib)
    return lib


def main():
    ensure_lib()
    try:
        from dg_connector import runner
    except Exception as error:
        forms.alert("DG connector library failed to load:\n{}".format(error), title="DG")
        return
    try:
        result = runner.clear(__revit__)
    except Exception as error:
        forms.alert("Clearing the DG colours failed:\n{}".format(error), title="DG")
        return
    message = ""
    if isinstance(result, dict):
        message = result.get("message") or ""
    forms.alert(message or "DG colours cleared.", title="DG")


main()
