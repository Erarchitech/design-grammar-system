#! python3
"""Run one demo act on the -mapping.gh copy (Phase 1303 MVP slice).

Usage: RhinoCode.exe script <this file> <act> [log file] [--keep]
  act: v1 | v2 | v3 | v4 | refresh | apply
    v1  Module Width F1 = 6000 (cold start; GU sent as HU, reproduces F5)
    v2  Module Width F1 = 4400 (R2 x12, R7 x57 as design signals)
    v3  Module Width F1 = 10000 (R1 x4)
    v4  Наклон нечет сот = 0 (R6 x14)
    refresh / apply  pulse Refresh or Apply on the current session (after answers in the Web UI)
Sliders are restored in finally unless --keep is given. Each run appends an EVIDENCE line
(act, sessionId, summary, open questions) to the log; the token is never read.
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import dgmap_common as c  # noqa: E402

WIDTH = "Module Width F1"
ODD_TILT = "Наклон нечет сот"
ACTS = {
    "v1": {"sliders": {WIDTH: 6000}, "key": "facade-v1", "label": "act1-cold-start-v1"},
    "v2": {"sliders": {WIDTH: 4400}, "key": "facade-v2", "label": "act2-learned-v2"},
    "v3": {"sliders": {WIDTH: 10000}, "key": "facade-v3", "label": "act2-learned-v3"},
    "v4": {"sliders": {ODD_TILT: 0}, "key": "facade-v4", "label": "act2-learned-v4"},
}


def _outputs(mapping):
    def first(name):
        values = c.read_output(mapping, name)
        return values[0] if values else None

    return {
        "sessionId": first("SessionIdOut"),
        "summary": first("Summary"),
        "questions": first("Questions"),
        "classNames": c.read_output(mapping, "ClassNames"),
        "log": first("Log"),
    }


def main(log_path):
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    keep = "--keep" in sys.argv
    act = args[0] if args else "v1"
    doc = c.gh_document()
    c.log(log_path, "act {}: definition {}".format(act, c.require_copy(doc)))
    mapping = c.one_by_nickname(doc, c.MAPPING_NICK)
    if act in ("refresh", "apply"):
        c.pulse(doc, mapping, act.capitalize())
        out = _outputs(mapping)
        c.evidence(log_path, dict(out, act=act))
        return
    spec = ACTS[act]
    restore = {}
    try:
        for name, value in spec["sliders"].items():
            restore[name] = c.set_slider(doc, name, value)
        c.set_input_value(mapping, "GuAsHu", True)
        c.set_input_value(mapping, "DefinitionKey", spec["key"])
        c.set_input_value(mapping, "Label", spec["label"])
        c.solve(doc)
        c.pulse(doc, mapping, "Run")
        out = _outputs(mapping)
        c.evidence(log_path, dict(out, act=act, sliders=spec["sliders"]))
    finally:
        if not keep:
            for name, value in restore.items():
                c.set_slider(doc, name, value)
            c.solve(doc)
            c.log(log_path, "act {}: sliders restored {}".format(act, restore))


c.run_main(main, next((a for a in sys.argv[2:] if not a.startswith("--")), c.DEFAULT_LOG))
