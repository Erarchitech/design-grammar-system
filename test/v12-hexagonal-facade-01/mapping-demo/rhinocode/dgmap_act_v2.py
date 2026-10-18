#! python3
"""Act 2 - V2 on the canvas (Module Width F1 = 4400); learned profiles map it.

Run: "C:\\Program Files\\Rhino 8\\System\\RhinoCode.exe" script <full path to this file>
RhinoCode passes no script arguments, so the act is fixed here. Log: %TEMP%\\dgmap-rhinocode.log
"""

import importlib
import os
import sys
import traceback

ACT = "v2"
FALLBACK_DIR = r"C:\Users\Admin\source\repos\dg-mapping\test\v12-hexagonal-facade-01\mapping-demo\rhinocode"

try:
    HERE = os.path.dirname(os.path.abspath(__file__))
except NameError:  # a runner that does not set __file__
    HERE = FALLBACK_DIR
try:
    if HERE not in sys.path:
        sys.path.insert(0, HERE)
    import dgmap_common
    import dgmap_acts

    importlib.reload(dgmap_common)  # Rhino keeps modules loaded between runs
    importlib.reload(dgmap_acts)
    dgmap_acts.run_logged(ACT)
except Exception:  # noqa: BLE001 - RhinoCode hides errors; record them
    with open(os.path.join(os.environ.get("TEMP", "."), "dgmap-rhinocode.log"), "a", encoding="utf-8") as handle:
        handle.write("act {}: wrapper FAILED\n{}".format(ACT, traceback.format_exc()))
