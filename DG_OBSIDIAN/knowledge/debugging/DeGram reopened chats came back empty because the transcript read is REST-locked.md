---
tags: [debugging, degram, phase-1301, live-uat]
date: 2026-10-11
---

# DeGram reopened chats came back empty because the transcript read is REST-locked

## Symptom

0.1.8: after switching projects and returning, earlier chats of the project could not be read back, although `state.db` of the scope profile held them (v12: 12 sessions, degram-uat-b: 5).

## Root cause

Desktop treats REST as the transcript authority. A cold resume runs `getLatestSessionMessages` (`GET /api/sessions/{id}/messages`) in parallel with `session.resume {defer_history: true, omit_messages: true}`. The gateway's deferred path (`_resume_deferred`) always answers `messages: []`. DeGram's REST lock allows only `/api/ws`, `/api/health`, `/api/status`, so the prefetch gets 403 `DEGRAM_LOCKED` and the view is built from the empty RPC answer.

## Fix

Component `e49c5d6a` (0.1.9): in variant degram the cold resume skips the REST prefetch and sends `session.resume` without `defer_history`/`omit_messages` (`_resume_cold`), which returns the full transcript over the allowlisted RPC. Test in `use-session-actions.test.tsx`.

## Lessons

- Verify which DB a symptom concerns before blaming code: the 0.1.9 «history lost» report was a correct D-19 purge after the tester removed themselves from v12 (data-service log `DELETE …/members/…` 204 at 10:31:11Z), and a different DG user than the earlier chats.
- Profile `createdAt` in `degram-scope.json` is preserved by `ensure`; a new value means the directory was deleted and recreated (purge).
- Plan 27 tested only the list; the reopen path needed its own test against the REST lock.
