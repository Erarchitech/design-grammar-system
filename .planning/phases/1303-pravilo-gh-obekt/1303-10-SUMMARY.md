---
phase: 1303-pravilo-gh-obekt
plan: "10"
status: complete
completed: 2026-10-18
requirements: [DGMAP-02, DGMAP-03, DGMAP-05]
executor: "controller (Claude) for the server, DG.gha, deployment and review; two Claude subagents (DSH hub unreachable) for the Web UI panel and the DeGram sub-tab, both reviewed and re-tested by the controller"
commits: [c8c24d2, 2a87093, a1ea659, 3cc9b35, 7867f98]
component_commits: ["93997683 (D:\\dgb\\src, feature/mapping-mvp, not pushed)"]
open: "UAT 11 (V2/V3), UAT 10 re-check of 7867f98 on the next cold start"
---

# 1303-10 Summary — proposal cards, per-answer undo, canvas tags, DeGram Mapping sub-tab

## What was built

**Server** (`c8c24d2`):
- Questions carry `title` / `titleRu` and `items`: one row per proposed component (stream source, calculation output, slider) with its GH InstanceGuid, count, proposal, alternatives and state.
- Sessions carry `answers` and the GH `document` key.
- `POST /mapping/sessions/{id}/undo` takes one answer back while the session is not applied: its decisions get `undoneAt`, the profiles it created are retired, and the confirmations and rejections it added are taken back. An applied session answers 409 `MAPPING_SESSION_APPLIED`, an unknown or already undone answer 404 `MAPPING_ANSWER_NOT_FOUND`.
- The DeGram delegated principal may read sessions and profiles and answer or undo for its bound project (route policy, SECURITY-BOUNDARY block, API.md, DATABASE.md, contract §7).

**DG.gha** (`2a87093`):
- `MappingCanvasTags` paints group-like frames and one tag per proposed component on the canvas; they are not document objects.
- CONNECTOR waits 10 s after the last answer before apply.
- New LISTENER bridge commands `focus_component`, `start_mapping` and `get_mapping_status`.

**Web UI** (`a1ea659`, subagent):
- `ProposalCard`, `AnswerCard` and `ItemRow`, each card collapsible on its own.
- `undoAnswer`; the full text sits behind «Подробнее».
- No start button: the Web UI shows existing sessions only.

**DeGram** (`93997683` in the build clone, subagent):
- «Меппинг» sub-tab under each document of «Модели»: progress bar, collapsible proposals and answers, coloured clickable component buttons (`degram.mapping.focus`), per-answer undo, «Запустить меппинг» for a Grasshopper document without a session.
- RPC `degram.mapping.*`: contract, generated TS/OpenRPC, lockdown allowlist.
- `dg_client` mapping calls; the `gh_bridge` allowlist is now every canvas bridge command (owner decision).

**Rehearsal fixes:**
- `7867f98`: sliders the LLM holds back are shown in the slider batch and decided with it.
- Demo prep: LISTENER (Run = True) added to the clean copy by `dgmap_add_listener.py`; the backup is `…-auto-mapping.pre-listener.gh`.

## Verification

- data-service, full suite on a1ea659: 5809 passed, 35 skipped. 4 failed (`test_dg_context`) and 25 errors (`neo4j:7687` DNS from the host) — the known baseline.
- data-service after `7867f98`: mapping tests 50/50; the 1094-test route, policy and boundary set passed on c8c24d2.
- DG: `dotnet build` DG.Grasshopper Release passed against the Rhino 8 SDK; the DLL contains the new types. Mapping and bridge tests 48/48.
- ui-v2: 331/331, build passes.
- DeGram, run by the controller:
  - Python `test_mapping`, `test_gh_bridge` and `test_generated`: 75 passed, 1 skipped;
  - vitest `src/degram`: 314 passed, 1 failed. The failure is `ru-catalog-completeness › settings`, in the shared settings catalog, which this plan did not touch; per the subagent's baseline it was there before;
  - `tsc -p .`, `tsc -p tsconfig.electron.json` and eslint on the changed files: clean.
- Deployment:
  - data-service `7867f98` (image `8c8c04a8…`) and UI `a1ea659` (`aae916eb…`) from `git archive`; the served code was checked in the containers;
  - DG.gha `3D1202A3…` installed while Rhino was closed;
  - DeGram `win-unpacked` build of `93997683` (10 min, exit 0) launched with a scrubbed environment.
- Live (rehearsal 2, `ms-56907a90d11f`):
  - the owner tested the mapping in DeGram: «всё работает как положено»;
  - the graph shows one undo and a re-answer, and apply 13 s after the last answer;
  - `get_mapping_status` and `focus_component` answered on the live canvas;
  - frames and tags were seen on the canvas render;
  - placement and VALIDATOR V1 11/11 PASS (see `1303-09-SUMMARY.md` and `PROTOCOL.md`).

## Decisions

D-39…D-43 in `1303-CONTEXT.md`. Claude's calls:
- tags are painted, not group objects;
- 10 s apply grace;
- the Revit sub-tab shows sessions only;
- DeGram reports DG refusals 400/404/409 as JSON-RPC errors with `data.code` (operational outcome vocabulary unchanged);
- slider rows the LLM held back carry no proposal.

## Open issues

- The session after placement asked 1 slider question and paid one LLM call (UAT 10). Fixed in `7867f98`; the live re-check comes with the next cold start.
- Frames and tags of tightly stacked parameters overlap neighbouring components (readable, crowded).
- Windows can refuse to raise the Grasshopper window from a background process. `focus_component` uses the TopMost toggle plus `Activate`; the owner reports the click works.
- The DeGram build overwrote `release\DeGram-Setup-0.1.11.exe` in the build clone; the installed 0.1.11 is untouched.
- The component commit is not pushed and the gitlink is not bumped (D-43). Both happen at the post-demo merge, with explicit authorization for the push.
- While checking the tags, a canvas render briefly captured the CONNECTOR Panels, including the password in plain text. The file was deleted at once; the owner was told and advised to change the password and remove the Panel before the demo.
