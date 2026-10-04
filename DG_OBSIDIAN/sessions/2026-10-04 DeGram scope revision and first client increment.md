---
tags: [session, DeGram, v13, implementation]
date: 2026-10-04
---

# Session: DeGram scope revision and first client increment

## Session summary

сессия: По решению владельца исключено сравнение DeGram с baseline из активного v13.0 и реализован первый изолированный read-only web-клиент на базе ui-v2; пользователь продолжит работу в следующей сессии.

## User decisions / authority

- Owner explicitly directed: «Мне не требуется сравнение DeGram с baseline в этом Milestone. Исключи вообще это из планов. И переходи к реальной разработке DeGram».
- Current-DG-vs-DeGram comparison, comparative participant arms, benefit thresholds and baseline-derived sample sizing are withdrawn from active v13.0 requirements/plans. The retired 1300-07 is superseded, not completed.
- Preserve functional correctness, independent expected results, safety/security, compatibility, Viewer regression, traceability, recovery, recipient and human release checks. Do not conflate comparisons of design alternatives or pre/post recovery with the withdrawn product benchmark.
- Phase 1300 remains incomplete. Historical approvals and dossier receipts do not automatically accept the changed scope; source pins that changed require explicit rebind/review. V8 and ownership gates remain for dependent semantic/native capabilities.
- User clarified the relationship to running Design Grammars: current Docker app at `http://localhost:8080/` is the existing DG server/web system; DeGram is intended as a new Hermes-derived Desktop client consuming DG data/auth/API, not a replacement web system. The new web surface is a limited reused-web component, not the actual Desktop app.
- Initial pilot constraints carried forward: system-wide pair `genpro` / `mimo-v2.5-pro` hidden from ordinary users; local single-user Docker profile; current PC and later reviewer PC; Revit 2024/Rhino 8; first CAD/graph path read-only; local files only/no Drive publication. Numeric budget limits deferred. These are not live readiness claims.

## Changes made

- Added `.planning/phases/1300-kontrakty-baseline-i-ownership/1300-SCOPE-REVISION.md` as the owner-authorized scope authority.
- Active requirements/control-plane and Phase 1300 plans/validator were revised. Active inventory: 8 plans, 22 tasks, 6 waves; 1300-07 removed from active execution and denied by the validator. No requirement IDs/owners were deleted or reassigned.
- Added Phase 1300 scope revision verification artifacts and a parent review note. Frozen source dossier files were preserved; changed source bindings require explicit review.
- Implemented a real restricted web workspace under `ui-v2/src/degram/`, wired at `/#degram` on the existing DG web origin after serving rebuilt UI assets. It uses existing DG login/session, authorized project list and graph-read APIs, displays a read-only graph/object properties, and has explicit empty/error/denied handling. It clears context on project changes/logout/access loss and filters provider/model/key metadata from inspection.
- This increment does not implement a standalone Hermes Desktop application, CAD adapters, server-side read-only enforcement, or any complete DGCL requirement. Existing admin/owner server privileges are unchanged. `http://localhost:8080/` remains on its current Docker image until an authorized rebuild/deploy; no container was rebuilt/restarted here.

## Verification actually executed

- Phase 1300 admission tests: `node --test .planning/phases/1300-kontrakty-baseline-i-ownership/1300-admission.test.mjs` — 67 passed, 0 failed.
- DeGram boundary + existing auth/API tests: `node --test ui-v2/tests/degram-boundary.test.mjs ui-v2/tests/api-security.test.mjs ui-v2/tests/auth-security.test.mjs` — 166 passed, 0 failed.
- Isolated browser harness: `node ui-v2/tests/run-degram.mjs parent-verified` — 22/22 cases passed using explicitly synthetic, finite API responses and network denial. This is offline client evidence, not live Docker/backend evidence.
- Production build: `npm --prefix ui-v2 run build` — exit 0; separate DeGram entry emitted. Existing large normal-App bundle warning remains.
- Structural cross-check: 51/51 requirement IDs mapped; eight phases; active Phase 1300 roster 8 plans/22 tasks, dependency ordering valid; `state.json` parsed.
- Scoped changed-file `git diff --check` passed. A wider repository check reports pre-existing whitespace in archived v12 REQUIREMENTS/ROADMAP, which this session did not touch.

## What was not done

No Docker rebuild/restart, deployment, live backend/DB/LLM call, CAD access or mutation, Drive publication, secret read, package install, Git staging/commit/push, branch change, or change to the user's installed Hermes/profile. The open Grasshopper `.gh` with the user's temporary Panels was not saved/closed/reverted.

## Next session: resume here

1. Read this note, current `.planning/STATE.md`, `.planning/ROADMAP.md`, `.planning/REQUIREMENTS.md`, `1300-SCOPE-REVISION.md`, `1300-PARENT-REVISION-REVIEW.md`, and `1301-01-SUMMARY.md`.
2. Begin by resolving the user's architectural question explicitly: the actual product is the Hermes-derived Desktop client integrated with Design Grammars; `/#degram` is only the first reusable UI slice. Discuss the next concrete Desktop integration step and locate/confirm the intended Hermes source repository before creating a Desktop shell.
3. Do not launch Docker or modify `http://localhost:8080/` unless the user explicitly authorizes rebuild/restart/deployment. If authorized, verify the target compose service/image and changes first.
4. Continue actual product work without restoring baseline-comparison experiments. Use tests-first; retain the existing V8/ownership and live-security gates for the capabilities they govern.
5. The read-only web increment is already exercised; do not repeat all browser tests unless relevant code changes. No Git commit was requested.
