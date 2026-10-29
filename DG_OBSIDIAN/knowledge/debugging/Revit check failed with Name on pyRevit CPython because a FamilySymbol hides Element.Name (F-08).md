---
tags: [debugging, revit, pyrevit, pythonnet, property-calculators, stand]
date: 2026-10-29
status: fixed in 93e3c11, deployed on the stand
---

# Revit check failed with Name on pyRevit CPython because a FamilySymbol hides Element.Name (F-08)

## Symptom

- Every Revit check from the demo PC (PC-2, DeGram in Demo mode against the stand) failed with
  `REVIT_CHECK_FAILED: Name`, also after the scripts were prepared again.
- DeGram reported that all 6 calculators were prepared, but no check result came back.

## Root cause

- The text `Name` is the job error the DG Revit connector sends back: `str(exception)` of the generated
  property-check program.
- Under pythonnet (pyRevit's CPython engine), `FamilySymbol`/`ElementType` declares a set-only `Name`. It hides the
  inherited `Element.Name` getter, so `e.Symbol.Name` raises `AttributeError('Name')`.
- `inventory()` in `model_context.py.tmpl` reads `e.Symbol.Name` for every Generic Model instance on every check, so
  the check always failed on that engine. On IronPython the read works, which is why the dev PC never showed it.
- The connector already had the workaround in `revit_io._type_name` (`DB.Element.Name.__get__`). The generated
  program did not.

## Fix

- `93e3c11`: new `element_name()` in the shared `model_context.py.tmpl`. It tries `.Name`, and on `AttributeError`
  falls back to `DB.Element.Name.__get__`.
- Every type and element name read in `revit_shell.py.tmpl` and `calculator_shell.py.tmpl` goes through it.
  Catalogue `1303-15.5`.
- Regression test `test_type_names_are_read_through_element_name_which_survives_pythonnet`:
  - fails if any generated program reads `X.Symbol.Name` directly;
  - executes `element_name` against a pythonnet-like symbol.

## Lesson

Generated Revit code runs under every pyRevit engine. Read a type name through `element_name()` and never through
`.Name` on an `ElementType`. When the connector code has an engine workaround, check the generated templates for the
same pattern.

## Related

- [[knowledge/debugging/Parallel first publishes raced to create the dg-validation model (F-09)|F-09]]
- [[sessions/2026-10-29 Demo PC Revit check fixed end to end, stand Speckle set up (F-08, F-09)|session]]
