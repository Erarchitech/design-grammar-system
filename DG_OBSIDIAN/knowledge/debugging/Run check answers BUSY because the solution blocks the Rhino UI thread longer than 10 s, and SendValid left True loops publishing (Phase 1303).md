---
tags: [debugging, phase-1303, grasshopper, canvas-listener, validator]
date: 2026-10-25
---

# Run check answers BUSY (UI thread blocked past 10 s); SendValid left True loops publishing

## Symptoms

- Web UI «Run check» and DeGram: `Canvas UI thread did not respond within 10000 ms (busy)`, then HTTP 422 `PROPERTY_CHECK_FAILED` with "no Box elements" and "VALIDATOR published no run" although the canvas held 313 boxes.
- With `SendValid` True set by hand, Grasshopper froze for 30+ minutes and 45 `ValidationRun` nodes appeared in one morning.

## Findings

- Reads through the listener (port 8720, `get_property_check_status`, `get_canvas_context`) answer in 0.0 s while idle. After `run_property_check` the UI thread is blocked about 24 s (the synchronous solution of the calculator over 313 boxes): a read queued meanwhile times out at 10 s, the next one answers after 14 s.
- `CanvasUiTimeoutMs = 10000` (`DG.Core/Bridge/CanvasBridgeProtocol.cs`) turns that into BUSY although the solution keeps running. `_run_check_retrying_busy` in `data-service/app.py` retries, which starts new solutions and resets the toggles; the status is then read mid-solution (0 boxes, no runs) and `property_check_summary` reports both problems.
- `SendValid` True makes every re-solve publish (about 33 s per rule, five rules); publishing happens on the UI thread and keeps re-triggering solutions, so the canvas stays frozen and runs pile up. The listener switches `SendValid` off itself only after its own one-shot run.
- Plugin diff since the previous build was only RULE DECONSTRUCT, so this is not a regression of f0e27a1; the solution simply takes longer than 10 s now.
- The component the owner could not find exists: group "DG · Проверка свойств (str-openings-01)", script type "Python 3 Script", nickname `DG PROPERTY CALCULATOR`. Palette search finds types, not canvas instances. `focus_component` with the instance id selects and centres it.

## Workaround

Do not repeat «Run check». For a published run: `SendValid` True, one F5, wait until the runs appear, then `SendValid` False at once. Never leave it True.

## Fix (planned, 1303-24)

Longer timeout for `run_property_check` (or an asynchronous start with status polling), no blind retry after BUSY in data-service, and a guard against a publish loop.

## Related

[[sessions/2026-10-25 Phase 1303 live acceptance of 18 and 23 — stack rolled to f0e27a1, acts 1-4, findings]]
