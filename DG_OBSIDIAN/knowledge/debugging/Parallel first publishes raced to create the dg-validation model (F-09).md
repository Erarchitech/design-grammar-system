---
tags: [debugging, speckle, publish, concurrency, stand]
date: 2026-10-29
status: fixed in 2c5f5bc, deployed on the stand
---

# Parallel first publishes raced to create the dg-validation model (F-09)

## Symptom

- The first check after Speckle was set up on the stand failed with `PUBLISH_INTERNAL_ERROR` (error id
  `2e4a6d846dcc`) for 5 of the 6 rules.
- The data-service log showed `A branch with this name already exists` (`BRANCH_CREATE_ERROR`) from
  `get_or_create_validation_model_id`.

## Root cause

- `_publish_revit_runs` publishes every evaluated rule in parallel, as VALIDATOR does.
- On a fresh Speckle project there was no `dg-validation` model yet. Each publish listed the models, found none and
  created the model. Speckle accepted only the first create.
- On localhost the model had existed for months, so the race never showed there.

## Fix

- `2c5f5bc`: when the create fails, `get_or_create_validation_model_id` lists the models again and returns the
  `dg-validation` model another publish created. If none appeared, it raises the original error.
- Tests in `test_revit_check.py`:
  - 4 threads list before any create (barrier). Without the fix the test is red.
  - A failed create with no model still raises.

## Lesson

Any get-or-create against an external service that runs from a thread pool needs a re-read after a failed create.
Listing first is not enough.

## Related

- [[knowledge/debugging/Revit check failed with Name on pyRevit CPython because a FamilySymbol hides Element.Name (F-08)|F-08]]
- [[sessions/2026-10-29 Demo PC Revit check fixed end to end, stand Speckle set up (F-08, F-09)|session]]
