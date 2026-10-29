---
tags: [session, v13.0, quick, revit, mapping, degram]
date: 2026-10-29
---

# Session: 2026-10-29 — Revit re-read with a leftover selection read one element, DeGram now warns (F-10)

## Goal

On the demo PC (PC-2, DeGram against the stand), the owner added new elements in Revit and clicked «Прочитать модель
заново» in DeGram. The mapping was applied automatically to only one element, the selected one. The other new elements
got neither a mapping nor proposals. Find the cause and fix it (`/gsd-audit-fix`, finding F-10 of quick 261029-dmt).

## What Was Done

- **Diagnosis from the code:**
  - The connector's `collect_scope` reads the Revit selection when one exists and the whole active view only when
    nothing is selected. This is the scope rule D-48.
  - One element was left selected, so the re-read sent only that element to DG.
  - Its group got the remembered mapping automatically. The other new elements were never read.
  - A DeGram row click also selects elements in Revit (`show_elements`), so DeGram can leave such a selection itself.
  - Nothing in DeGram said that only the selection was read.
  - The stand's sessions were not inspected: the permission layer refused the read-only SSH query.
- **Owner decision:** keep D-48 and warn explicitly. See
  [[knowledge/decisions/A Revit mapping read keeps the selection scope and DeGram warns when only the selection was read (F-10)|decision]].
- **Fix:**
  - Framework `21f03b8`: the connector's `start_mapping` returns `scope` (`selection` | `view`) and `read`. Its
    message says "only the Revit selection". The MCP tool docstring describes both fields.
  - Component `3bf67d55`, on `degram/milestone13`, pushed to the fork with the owner's authorization:
    - `degram.mapping.start` passes both fields (gateway contract regenerated);
    - the mapping panel shows a warning in the alert style: «Прочитаны только выделенные в Revit элементы (N). Снимите
      выделение в Revit и нажмите «Прочитать модель заново», чтобы прочитать весь вид.»
  - Framework `e3becb9`: gitlink bump; `workspace.py verify` passes.
  - Framework `7b5b27e`: F-10 recorded in `261029-dmt-SUMMARY.md`.
  - See [[knowledge/debugging/Revit re-read with a leftover selection mapped only the selected element (F-10)|debugging]].
- **Checks:**
  - connector pytest: 439 passed;
  - DeGram UI `src/degram`: 349 passed, tsc and eslint clean;
  - DeGram `tests/degram`: 517 passed, with 2 failures not caused by this change:
    - `test_revit_bridge::…overrides_the_placeholders` (profile ownership) also fails at the untouched `38e0e1ee`;
    - the lockdown socket-guard test fails only under full-suite load and passes alone.

## Decisions Made

- Owner: the read scope stays the selection, else the active view (D-48). DeGram only warns.
- Owner: commit the component change, push it to the fork and bump the gitlink.
- Owner: no DeGram build yet. More changes come first, then one build in another session.

## Issues Encountered

- The auto-mode permission layer refused the read-only SSH query to the stand's Neo4j, and once a local grep of
  `.planning`. The diagnosis therefore rests on the code and the owner's description.
- The contract generator writes CRLF, while the files are `eol=lf`. They were normalized to LF before the commit.
- Git printed "failed to delete …/worktrees/dgp-t" during the child commit. It comes from the automatic worktree prune
  and is harmless.

## Next Steps

1. The owner makes more changes. Then one DeGram build 0.1.17 (run `stage_connector_payloads.py` first). On the demo
   PC: install it and click «Установить» for Revit again.
2. Until that build: press Esc in Revit before «Прочитать модель заново».
3. The open items of the previous session stay: localhost data-service rebuild, stage 2 mapping view (F-06).

## Related Notes

- `.planning/quick/261029-dmt-multi-user-demo-test-fixes/261029-dmt-SUMMARY.md`
- [[sessions/2026-10-29 Demo PC Revit check fixed end to end, stand Speckle set up (F-08, F-09)|earlier session the same day]]
- Commits: `21f03b8`, `3bf67d55` (component), `e3becb9`, `7b5b27e`
