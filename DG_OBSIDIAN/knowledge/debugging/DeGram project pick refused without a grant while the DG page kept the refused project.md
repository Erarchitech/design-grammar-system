---
tags: [debugging, degram, phase-1301, grants, ux]
date: 2026-10-12
status: partly open (the signal race is a hypothesis)
---

# DeGram project pick refused without a grant while the DG page kept the refused project

## Symptom

Owner, 0.1.11 UAT: «Проект переключается через меню, но в сессии остается один и тот же проект, история сессий не меняется».

## Findings (desktop.log + data-service log, 2026-10-12)

- Four picks of `degram-uat-b` / `degram-uat-c` between 08:52 and 08:53 each ended as `POST /auth/degram/session-exchange` 403 within about 60 ms (`#degram-state=connecting` then `ready`); a real switch takes about 8 s. `degram-grants.json` holds grants only for `v12-hexagonal-facade-01`, so the refusal is correct and the chat staying on v12 is the F-07 behaviour (D-39: every project needs an owner/admin grant).
- The DG page itself loaded the refused project (`GET /graph/degram-uat-c`) each time. It returned to v12 after the two `degram-uat-b` picks (08:52:18, 08:53:19) but not after the two `degram-uat-c` picks.
- DeGram logs nothing for a refused selection (no `scope ready`, no refusal line), so the refusal is visible only in the data-service log.

## Hypothesis (unproven)

After a refusal main sends `#degram-project=<open>` and then `#degram-state=ready` back to back (`electron/degram/ipc.ts` `settleAfterSelection`, `dg-view.ts` `signal`). `ui-v2/src/App.jsx` reads `window.location.hash` when `hashchange` fires, not `event.newURL`, and clears the hash after each signal, so when the second signal lands first the project signal is lost. The 0.06 s gap and the b/c pattern fit; no test reproduces it.

## Next

A failing browser test (two hashes set in a row in host mode must still apply the project), then read the signal from `event.newURL`. The DG page is served by the `design-grammars` container, so only that container needs a rebuild. Consider a DeGram log line for a refused selection.

## Related

- [[knowledge/debugging/DeGram refused project pick released the open project first (F-07)]]
- [[sessions/2026-10-12 Phase 1301 gap plans 37-41 executed, DeGram 0.1.11 built and UAT result]]
