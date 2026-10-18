#! python3
"""Demo acts on the -mapping.gh copy (Phase 1303) — library, no module-level run.

Since 1303-08 the mapping is proposed automatically by CONNECTOR (no DG MAPPING component):
an act only puts the variant sliders on the canvas; a few seconds later CONNECTOR has sent
the new canvas state to DG. `rhinocode script <PATH>` passes no script arguments, so every
action has its own wrapper (dgmap_act_v1.py … dgmap_act_v4.py, dgmap_act_validate_v1.py,
dgmap_refresh.py, dgmap_apply.py, dgmap_reset_v1.py) that calls `run_logged(act)`.
  v1           V1: Module Width F1 = 6000, Наклон нечет сот = +1
  v2 / v3      V2: F1 = 4400 (R2 x12, R7 x57) / V3: F1 = 10000 (R1 x4), нечёт +1
  v4           V4: F1 = 6000, Наклон нечет сот = 0 (R6 x14)
  validate-v1  V1 again (act 4)
  refresh / apply  write what CONNECTOR shows (Mapping, ClassNames, Sliders) to the log
  reset-v1     sliders back to V1
Each act sets both variant sliders and leaves the variant on the canvas; if the act fails, the
previous slider values are restored. The token is never read.
"""

import dgmap_common as c

WIDTH = "Module Width F1"
ODD_TILT = "Наклон нечет сот"
V1 = {WIDTH: 6000, ODD_TILT: 1}
ACTS = {
    "v1": V1,
    "v2": {WIDTH: 4400, ODD_TILT: 1},
    "v3": {WIDTH: 10000, ODD_TILT: 1},
    "v4": {WIDTH: 6000, ODD_TILT: 0},
    "validate-v1": V1,
    "reset-v1": V1,
}


def connector(doc):
    found = [o for o in doc.Objects if type(o).__name__ == "ConnectorComponent"]
    if len(found) != 1:
        raise RuntimeError("expected exactly one CONNECTOR, found {}".format(len(found)))
    return found[0]


def report(doc, log_path, act):
    conn = connector(doc)

    def first(name):
        values = c.read_output(conn, name)
        return values[0] if values else None

    c.evidence(
        log_path,
        {
            "act": act,
            "message": getattr(conn, "Message", None),
            "mapping": first("Mapping"),
            "classNames": c.read_output(conn, "ClassNames"),
            "sliders": c.read_output(conn, "Sliders"),
        },
    )


def run(act, log_path):
    doc = c.gh_document()
    c.log(log_path, "act {}: definition {}".format(act, c.require_copy(doc)))
    if act in ("refresh", "apply"):
        report(doc, log_path, act)
        return
    sliders = ACTS[act]
    previous = {}
    try:
        for name, value in sliders.items():
            previous[name] = c.set_slider(doc, name, value)
        c.solve(doc)
    except Exception:
        try:
            for name, value in previous.items():
                c.set_slider(doc, name, value)
            c.solve(doc)
            c.log(log_path, "act {}: failed, sliders restored {}".format(act, previous))
        except Exception:  # noqa: BLE001 - keep the original error for the log
            c.log(log_path, "act {}: failed, and restoring the sliders failed too".format(act))
        raise
    c.log(log_path, "act {}: canvas left on {} (was {}); CONNECTOR maps it in a few seconds".format(act, sliders, previous))


def run_logged(act, log_path=None):
    c.run_main(lambda path: run(act, path), log_path or c.DEFAULT_LOG)
