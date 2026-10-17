#! python3
"""Demo acts on the -mapping.gh copy (Phase 1303 MVP slice) — library, no module-level run.

`rhinocode script <PATH>` passes no script arguments, so every act has its own wrapper
(dgmap_act_v1.py … dgmap_act_v4.py, dgmap_act_validate_v1.py, dgmap_refresh.py, dgmap_apply.py,
dgmap_reset_v1.py) that calls `run_logged(act)`.
  v1           V1: Module Width F1 = 6000, Наклон нечет сот = +1 (cold start; GU sent as HU, F5)
  v2 / v3      V2: F1 = 4400 (R2 x12, R7 x57) / V3: F1 = 10000 (R1 x4), нечёт +1
  v4           V4: F1 = 6000, Наклон нечет сот = 0 (R6 x14)
  validate-v1  V1 again under its own label, before Apply (act 4)
  refresh / apply  pulse Refresh or Apply on the current session (after answers in the Web UI)
  reset-v1     sliders back to V1, no request
Each act sets both variant sliders, so the result does not depend on the previous act, and
leaves the variant on the canvas so its colours can be shown; if the act fails, the previous
slider values are restored. Each run appends an EVIDENCE line (act, sessionId, summary, open
questions) to the log; the token is never read.
"""

import dgmap_common as c

WIDTH = "Module Width F1"
ODD_TILT = "Наклон нечет сот"
V1 = {WIDTH: 6000, ODD_TILT: 1}
ACTS = {
    "v1": {"sliders": V1, "key": "facade-v1", "label": "act1-cold-start-v1"},
    "v2": {"sliders": {WIDTH: 4400, ODD_TILT: 1}, "key": "facade-v2", "label": "act2-learned-v2"},
    "v3": {"sliders": {WIDTH: 10000, ODD_TILT: 1}, "key": "facade-v3", "label": "act2-learned-v3"},
    "v4": {"sliders": {WIDTH: 6000, ODD_TILT: 0}, "key": "facade-v4", "label": "act2-learned-v4"},
    "validate-v1": {"sliders": V1, "key": "facade-v1", "label": "act4-validate-v1"},
    "reset-v1": {"sliders": V1},
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


def run(act, log_path):
    doc = c.gh_document()
    c.log(log_path, "act {}: definition {}".format(act, c.require_copy(doc)))
    mapping = c.one_by_nickname(doc, c.MAPPING_NICK)
    if act in ("refresh", "apply"):
        c.pulse(doc, mapping, act.capitalize())
        c.evidence(log_path, dict(_outputs(mapping), act=act))
        return
    spec = ACTS[act]
    previous = {}
    try:
        for name, value in spec["sliders"].items():
            previous[name] = c.set_slider(doc, name, value)
        if "key" in spec:
            c.set_input_value(mapping, "GuAsHu", True)
            c.set_input_value(mapping, "DefinitionKey", spec["key"])
            c.set_input_value(mapping, "Label", spec["label"])
        c.solve(doc)
        if "key" in spec:
            c.pulse(doc, mapping, "Run")
            c.evidence(log_path, dict(_outputs(mapping), act=act, sliders=spec["sliders"]))
    except Exception:
        try:
            if "key" in spec:
                c.set_input_value(mapping, "Run", False)
            for name, value in previous.items():
                c.set_slider(doc, name, value)
            c.solve(doc)
            c.log(log_path, "act {}: failed, sliders restored {}".format(act, previous))
        except Exception:  # noqa: BLE001 - keep the original error for the log
            c.log(log_path, "act {}: failed, and restoring the sliders failed too".format(act))
        raise
    c.log(log_path, "act {}: canvas left on {} (was {})".format(act, spec["sliders"], previous))


def run_logged(act, log_path=None):
    c.run_main(lambda path: run(act, path), log_path or c.DEFAULT_LOG)
