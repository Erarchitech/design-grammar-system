---
tags: [debugging, DeGram, v13.0, phase-1301, testing, flaky]
date: 2026-10-05
status: fixed (child 7fdb4aae)
---

# GH deadline test patched the clock only after the first request

## Symptom

`apps/degram/tests/degram/test_cad_cancel.py::TestDeadlinesAndNoRetry::test_a_gh_read_with_no_answer_for_30_seconds_is_busy` failed in roughly half of the runs ("the clock is patched, the test must not wait 30 s": elapsed 30 s); the plan 11 agent had reported 331/331 green.

## Cause

The patched `gh_bridge._monotonic` added 31 s only once `gh.requests` was non-empty. `gh_bridge` computes `deadline = _monotonic() + READ_TIMEOUT_S` at the start of each read, so a second read inside the same preview started from the already shifted clock and really waited 30 s. Production code was correct; the test depended on when the fake recorded a request.

## Fix

Each clock read advances 31 s (`ticks` counter), so every read's deadline has passed by its next poll. 12/12 solo passes at ~2 s; whole file 25 passed. Committed in the component repo as `7fdb4aae`; noted in 1301-11-SUMMARY.

Lesson: re-run a suite yourself after an agent reports green; time-patched tests need a clock that is monotonic in calls, not in external state.
