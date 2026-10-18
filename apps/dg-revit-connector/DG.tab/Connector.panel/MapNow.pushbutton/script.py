# -*- coding: UTF-8 -*-
"""«Меппинг DG» - start a mapping session for the active model (D-47, D-48).

Reads the scope (the selection, else the model instances visible in the active
view, at most 5000), posts the descriptors to DG, colours the elements by
mapping state and reports the outcome. The apply loop of
``lib/dg_connector/runner.py`` takes the session from there.
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
        result = runner.start_mapping(__revit__)
    except Exception as error:
        forms.alert("DG mapping failed:\n{}".format(error), title="DG")
        return
    message = ""
    if isinstance(result, dict):
        message = result.get("message") or ""
    forms.alert(message or "DG mapping finished.", title="DG")


main()
