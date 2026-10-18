#! python3
"""Shared helpers for the DG MAPPING RhinoCode scripts (Phase 1303 MVP slice).

Run inside the open Rhino 8 with
    "C:\\Program Files\\Rhino 8\\System\\RhinoCode.exe" script <full path to a dgmap_*.py>

stdout does not come back from RhinoCode and errors still exit 0, so every
script writes a step log (and JSON evidence lines) to a file. All scripts
refuse to touch a definition whose file name does not end with "-mapping.gh"
(the copy of the facade definition); the original stays untouched.
"""

import datetime
import json
import os
import traceback

import Grasshopper
from Grasshopper.Kernel.Special import GH_NumberSlider
from Grasshopper.Kernel.Types import GH_Boolean, GH_String

DEFAULT_LOG = os.path.join(os.environ.get("TEMP", "."), "dgmap-rhinocode.log")
MAPPING_NICK = "DG MAPPING"
STREAM_INPUTS = ("HU", "GU", "PB", "PA", "F", "LZ")


def log(path, message):
    stamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    with open(path, "a", encoding="utf-8") as handle:
        handle.write("{} {}\n".format(stamp, message))


def evidence(path, payload):
    with open(path, "a", encoding="utf-8") as handle:
        handle.write("EVIDENCE " + json.dumps(payload, ensure_ascii=False, sort_keys=True) + "\n")


def gh_document():
    canvas = Grasshopper.Instances.ActiveCanvas
    if canvas is None or canvas.Document is None:
        raise RuntimeError("no active Grasshopper document")
    return canvas.Document


def require_copy(doc):
    path = doc.FilePath or ""
    if not path.lower().endswith("-mapping.gh"):
        raise RuntimeError("refusing to run on {!r}: open the -mapping.gh copy of the facade definition".format(path))
    return path


def objects_by_nickname(doc, nickname):
    return [o for o in doc.Objects if getattr(o, "NickName", None) == nickname]


def one_by_nickname(doc, nickname):
    found = objects_by_nickname(doc, nickname)
    if len(found) != 1:
        raise RuntimeError("expected exactly one object nicknamed {!r}, found {}".format(nickname, len(found)))
    return found[0]


def input_param(component, name):
    for param in component.Params.Input:
        if param.Name == name or param.NickName == name:
            return param
    raise RuntimeError("{!r} has no input {!r}".format(component.NickName, name))


def output_param(component, name):
    for param in component.Params.Output:
        if param.Name == name or param.NickName == name:
            return param
    raise RuntimeError("{!r} has no output {!r}".format(component.NickName, name))


def slider(doc, nickname):
    for o in objects_by_nickname(doc, nickname):
        if isinstance(o, GH_NumberSlider):
            return o
    raise RuntimeError("no number slider nicknamed {!r}".format(nickname))


def set_slider(doc, nickname, value):
    import System

    s = slider(doc, nickname)
    # Rhino 8 CPython: CurrentValue is a System.Decimal, which float() does not accept.
    old = System.Decimal.ToDouble(s.CurrentValue)
    s.SetSliderValue(System.Decimal(value))
    return old


def set_input_value(component, name, value):
    """Set a persistent value on an unwired script input (bool or string)."""
    param = input_param(component, name)
    if param.SourceCount > 0:
        raise RuntimeError("input {!r} is wired; set the source instead".format(name))
    param.PersistentData.Clear()
    goo = GH_Boolean(bool(value)) if isinstance(value, bool) else GH_String(str(value))
    param.PersistentData.Append(goo)
    param.ExpireSolution(False)


def solve(doc):
    doc.NewSolution(False)


def pulse(doc, component, name):
    """Rising edge on a bool input: True, solve, False, solve."""
    set_input_value(component, name, True)
    solve(doc)
    set_input_value(component, name, False)
    solve(doc)


def read_output(component, name):
    data = output_param(component, name).VolatileData
    values = []
    for branch in data.Branches:
        for goo in branch:
            values.append(goo.ScriptVariable() if goo is not None else None)
    return values


def run_main(main, log_path):
    try:
        main(log_path)
        log(log_path, "OK")
    except Exception:  # noqa: BLE001 - RhinoCode hides errors; record them
        log(log_path, "FAILED\n" + traceback.format_exc())
