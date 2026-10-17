---
tags: [debugging, rhino, grasshopper, rhinocode, phase-1303]
date: 2026-10-17
status: fixed in code, not yet run in a live Rhino
---

# RhinoCode script passes no arguments to the Python script

**Symptom.** The demo helper `dgmap_run_act.py` chose its act from `sys.argv` (`… script dgmap_run_act.py v2`). `RhinoCode.exe script --help` prints only `Usage: rhinocode script <PATH>`, so the act name never reaches the script. Every run would have used the default act. The wiring script also read an optional log path from `sys.argv[1]`, which inside Rhino may hold anything.

**Related pitfalls.** stdout is not returned and a script error still exits 0, so everything must be logged to a file. Rhino keeps Python modules loaded between runs, so an edited helper module is not picked up again unless it is reloaded.

**Fix.**
- The acts moved into the library `test/v12-hexagonal-facade-01/mapping-demo/rhinocode/dgmap_acts.py`, which has no module-level run.
- Each action has its own wrapper: `dgmap_act_v1.py` … `dgmap_act_v4.py`, `dgmap_act_validate_v1.py`, `dgmap_refresh.py`, `dgmap_apply.py`, `dgmap_reset_v1.py`.
- Each wrapper adds its own folder to `sys.path`, with a fixed-path fallback if the runner sets no `__file__`. It calls `importlib.reload` on the helpers and writes import failures to `%TEMP%\dgmap-rhinocode.log`.
- `dgmap_wire.py` always logs to that file.
- Each act now sets both variant sliders and leaves the variant on the canvas, so its colours are visible. If the act fails, the previous values are restored and `Run` is cleared.

**Verification.** A host smoke test with stubbed Grasshopper objects ran the wiring, all 8 actions, a simulated failure (sliders restored) and the refusal on a non-copy definition. A live run in Rhino is part of the 18.10 rehearsal.

Related: [[sessions/2026-10-17 Phase 1303 mapping MVP built and deployed locally, rehearsal guide ready|session]], `test/v12-hexagonal-facade-01/mapping-demo/GH-RUNBOOK.md`.
