---
tags: [debugging, phase-1303, data-service, validator, degram]
date: 2026-10-21
status: fixed (commit 726ae0b)
---

# A property check was started again while VALIDATOR was still uploading its runs

**Symptom.** A check from DeGram (12:53 UTC) published all four validation runs, but DeGram got `502` after ~120 s. No run received its model context (walls, beams, columns), so the column run showed boxes only.

**Cause.** VALIDATOR uploads its runs *after* the solution, one per rule, about 25 s apart (12:54:03 → 12:55:16). So, when the listener answered, SendValid was already off and no run existed yet, which is the normal state.

A guard added for the old DG.gha (before 588f740), `_send_reset_before_publish`, took that for "SendValid reset early, nothing published" and started the check again. The canvas was still publishing and answered BUSY. After 8 retries the BUSY error (502) escaped `post_property_check_run`, so the background context publish was never scheduled.

**Fix.** The guard is removed: the installed DG.gha (9023b6e) arms its reset correctly. Test `test_a_check_whose_runs_are_still_uploading_is_not_started_again` replays the sequence. The context of the four affected runs was added by hand with `_publish_check_context`.

**Lesson.** Do not infer "nothing was published" from the canvas state right after the solution: publishing is asynchronous. Read the runs from the graph.

Related: [[sessions/2026-10-21 Phase 1303-15 MEP opening boxes checked in Revit through Rhino.Inside and VALIDATOR|session]].
