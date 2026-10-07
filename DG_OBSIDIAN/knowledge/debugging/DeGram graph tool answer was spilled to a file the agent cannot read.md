---
tags: [debugging, degram, phase-1301, agent, tool-budget]
date: 2026-10-07
status: fixed
---

# DeGram graph tool answer was spilled to a file the agent cannot read (G-1)

## Symptom

"List all rules" in DeGram: first "RESPONSE_TOO_LARGE" twice; after a first fix, one rule of twelve and "the project graph response was truncated… I can't access the saved spillover file".

## Causes (three stacked limits)

1. `GET /graph/{project}` for `v12-hexagonal-facade-01` answered 8.57 MB (2,000 nodes, `statePayloadJson` of validation records = 7.4 MB) > the DeGram client cap of 8 MiB → whole tool failed.
2. `degram_project_graph` read the rules only after the graph, so a failed graph read hid the rules.
3. The tool bounded its answer at 256 KiB, but the agent replaces any tool result above its per-result threshold (100K chars by default, `tools/budget_config.py`) by a 1,500-char preview and a spillover file. DeGram has no file tool (D-22), and the graph came before the rules in the answer.

## Fix

- Server `?compact=true` (property values > 2 KiB → size marker, validation records sorted last): 861 KB live. Framework `bb036a1`.
- Rules read independently; failures disclosed in `missing`. Component `5beb87d5`.
- Answer ≤ 60 % of the resolved threshold in characters, rules first and cut last. Live: 59,214 chars, 12/12 rules. Component `0614b41e`; confirmed live on 0.1.3.

## Lesson

A DeGram tool must fit the agent's result threshold, not only its own byte bound: a spilled result is lost for an agent without file tools.
