---
tags: [debugging, phase-1303, rhino-inside, revit, validator]
date: 2026-10-21
status: fixed (commits f0f02ff, 4b03c61, 9023b6e)
---

# Highlighter Revit writes re-solved Rhino.Inside and VALIDATOR republished in a loop

**Symptom.** About 148 validation runs appeared in the Model Viewer from one check, and Grasshopper kept solving.

**Cause.** The toggles stayed on after the check. Each highlighter transaction (colour overrides + `DG_Violation`) changed the Revit document. Rhino.Inside.Revit expires its Revit-reading components on a document change, so the chain solved again. VALIDATOR published again, and the highlighter painted again.

**Fixes, in order.**
1. The highlighter writes Revit only when the verdict changed. A digest is kept in `AppDomain.CurrentDomain` under `DG.Highlighter.LastDigest`, and an unchanged result writes nothing. This breaks the loop at its source.
2. A server-side toggle reset through `run_property_check` expired components in the middle of a solution ("object expired during a solution"), so it was removed.
3. The listener sets the toggles directly and only between solutions. During a solution it answers BUSY, and data-service retries. Setting them in a ScheduleSolution callback left them unapplied.

**Still open.** The listener's own one-shot SolutionEnd reset did not fire once a Revit dialog had held the transaction. To be checked on a clean run.

Related: [[sessions/2026-10-21 Phase 1303-15 MEP opening boxes checked in Revit through Rhino.Inside and VALIDATOR|session]], `data-service/property_calculators/highlighter.py.tmpl`.
