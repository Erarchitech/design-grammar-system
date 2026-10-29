---
tags: [decision, v13.0, revit, mapping, degram]
date: 2026-10-29
---

# A Revit mapping read keeps the selection scope and DeGram warns when only the selection was read (F-10)

## Context

The DG Revit connector reads the selection when one exists, otherwise every model element visible in the active view
(D-48, `1303-CONTEXT.md`). On the demo PC, a leftover selection of one element made «Прочитать модель заново» read only
that element. New elements got no proposals, and nothing said why. A DeGram row click also selects elements in Revit,
so DeGram can leave such a selection itself.

## Options considered

1. DeGram always reads the whole view and ignores the selection; the Revit ribbon keeps the selection scope.
2. Ignore only a selection that DG itself made through a row click.
3. Keep D-48 and warn explicitly when only the selection was read.

## Decision (owner, 2026-10-29)

Option 3. D-48 is unchanged.
- The connector's `start_mapping` reports `scope` (`selection` | `view`) and `read`.
- DeGram shows an alert-style warning: «Прочитаны только выделенные в Revit элементы (N). Снимите выделение в Revit и
  нажмите «Прочитать модель заново», чтобы прочитать весь вид.»

## Consequences

- Reading a selection on purpose still works from both DeGram and the ribbon.
- The user must clear the selection to read the whole view. The warning says how.
- Commits: framework `21f03b8`, component `3bf67d55`, gitlink `e3becb9`.

Related: [[knowledge/debugging/Revit re-read with a leftover selection mapped only the selected element (F-10)|debugging note]].
