#! python3
"""Plan 1303-10 demo prep: put a DG LISTENER (canvas bridge for DeGram, 127.0.0.1:8720) with Run = True
on the open -auto-mapping.gh copy and save it. A backup of the file is written next to it first
(<name>.pre-listener.gh, git-ignored like every .gh). Nothing else on the canvas is read or changed.

Run: "C:\\Program Files\\Rhino 8\\System\\RhinoCode.exe" script <full path to this file>
Log: %TEMP%\\dgmap-rhinocode.log
"""

import os
import shutil
import traceback

import System
import Grasshopper
from Grasshopper.Kernel import GH_DocumentIO
from Grasshopper.Kernel.Types import GH_Boolean

LOG = os.path.join(os.environ.get("TEMP", "."), "dgmap-rhinocode.log")
LISTENER_GUID = System.Guid("B0F26347-BB77-4593-A192-7BC3B0BC6169")


def log(message):
    import datetime

    with open(LOG, "a", encoding="utf-8") as handle:
        handle.write("{} add-listener: {}\n".format(datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"), message))


def main():
    canvas = Grasshopper.Instances.ActiveCanvas
    doc = canvas.Document if canvas is not None else None
    if doc is None:
        raise RuntimeError("no active Grasshopper document")
    path = doc.FilePath or ""
    if not path.lower().endswith("-auto-mapping.gh"):
        raise RuntimeError("refusing to run on {!r}: open the -auto-mapping.gh copy".format(path))
    existing = [o for o in doc.Objects if o.ComponentGuid == LISTENER_GUID]
    if existing:
        log("LISTENER already on the canvas ({}), nothing to do".format(len(existing)))
        return
    backup = path[: -len(".gh")] + ".pre-listener.gh"
    shutil.copy2(path, backup)
    log("backup {}".format(backup))

    listener = Grasshopper.Instances.ComponentServer.EmitObject(LISTENER_GUID)
    if listener is None:
        raise RuntimeError("DG LISTENER is not loaded (DG.gha)")
    listener.CreateAttributes()
    xs = [o.Attributes.Bounds.Left for o in doc.Objects if o.Attributes is not None]
    ys = [o.Attributes.Bounds.Bottom for o in doc.Objects if o.Attributes is not None]
    listener.Attributes.Pivot = System.Drawing.PointF(min(xs) if xs else 0.0, (max(ys) if ys else 0.0) + 150.0)
    run = listener.Params.Input[0]
    run.PersistentData.Clear()
    run.PersistentData.Append(GH_Boolean(True))
    doc.AddObject(listener, False)
    listener.ExpireSolution(True)
    saved = GH_DocumentIO(doc).SaveQuiet(path)
    log("LISTENER {} added at {}, Run = True, saved = {}".format(listener.InstanceGuid, listener.Attributes.Pivot, saved))


try:
    main()
except Exception:  # noqa: BLE001 - RhinoCode hides errors; record them
    log("FAILED\n" + traceback.format_exc())
