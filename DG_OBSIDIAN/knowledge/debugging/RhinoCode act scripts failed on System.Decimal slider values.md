---
tags: [debugging, rhinocode, grasshopper, phase-1303]
date: 2026-10-18
status: fixed (c3e673c)
---

# RhinoCode act scripts failed on System.Decimal slider values

**Symptom.** The first live run of `test/v12-hexagonal-facade-01/mapping-demo/rhinocode/dgmap_act_v2.py` logged `act v2: failed, sliders restored {}` and `TypeError: float() argument must be a string or a number, not 'Decimal'` in `dgmap_common.set_slider`. No slider was changed.

**Cause.** In Rhino 8 CPython (pythonnet), `GH_NumberSlider.CurrentValue` is a `System.Decimal`, and Python's `float()` does not accept it. The act wrappers had never been run live before.

**Fix (`c3e673c`).** `old = System.Decimal.ToDouble(s.CurrentValue)`. V2 and the reset to V1 then ran.

**Lesson.** Convert .NET numeric types explicitly in RhinoCode scripts (`System.Decimal.ToDouble`, `System.Convert.ToDouble`), and run every wrapper once before a demo.

Related: [[knowledge/debugging/RhinoCode script passes no arguments to the Python script|RhinoCode passes no arguments]], [[sessions/2026-10-18 Phase 1303 proposal cards, DeGram mapping sub-tab and live rehearsal through V2|session]].
