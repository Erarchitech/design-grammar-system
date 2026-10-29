---
tags: [debugging, v13.0, revit, mapping, degram]
date: 2026-10-29
---

# Revit re-read with a leftover selection mapped only the selected element (F-10)

## Symptom

New elements were added in Revit, and then «Прочитать модель заново» was clicked in DeGram. The mapping was applied
automatically to the one selected element only. The other new elements got neither a mapping nor proposals.

## Cause

- `collect_scope` in `apps/dg-revit-connector/lib/dg_connector/revit_io.py` reads the selection when it is not empty,
  and the active view only otherwise (D-48).
- With one element selected, the new session held one element.
- That element's group got its remembered mapping. The other elements were never sent to DG.
- Leftover selections are easy to create: a DeGram row click calls `show_elements`, which selects the group's elements
  in Revit.
- Nothing reported the scope. DeGram showed only "Mapping started".

## Fix

- `start_mapping` returns `scope` and `read`, and its message names a selection-only read (`21f03b8`).
- DeGram passes both fields through `degram.mapping.start`. The mapping panel shows a warning to clear the selection
  and read again (`3bf67d55`).
- Workaround on an older build: press Esc in Revit before reading again.

## Lesson

A scope rule that depends on hidden UI state (the Revit selection) must be reported to the user every time it applies.
A count like "1 element read" in a muted status line is not enough.

Related: [[knowledge/decisions/A Revit mapping read keeps the selection scope and DeGram warns when only the selection was read (F-10)|decision]].
