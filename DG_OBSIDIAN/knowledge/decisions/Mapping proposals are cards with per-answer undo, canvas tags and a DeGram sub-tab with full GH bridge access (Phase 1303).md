---
tags: [decision, mapping, phase-1303, degram, security, grasshopper]
date: 2026-10-18
status: accepted
---

# Mapping proposals are cards with per-answer undo, canvas tags and a DeGram sub-tab with full GH bridge access (Phase 1303)

**Context.** After the first live answers on 2026-10-18 the owner found the mapping report hard to decide on. It had too much text, and it was unclear which canvas elements were proposed. One wrong answer (Panels C) could not be taken back. Plan 1303-10; decisions D-39…D-43 in `.planning/phases/1303-pravilo-gh-obekt/1303-CONTEXT.md`.

**Decision.**
- **D-39 — cards.** A proposal is a short title plus one row per proposed canvas component (element stream = its source parameter, calculation output, slider). Each row carries the GH InstanceGuid, count, proposal, alternatives and state. Proposals and answers collapse one by one. Every answer has its own undo while the session is not applied. The undo marks the decisions undone, retires the profiles the answer created and takes back the confirmations and rejections it added. The full text sits behind «Подробнее». The Web UI shows existing sessions only and has no clickable components.
- **D-40 — canvas tags.** CONNECTOR paints a group-like frame and one tag per proposed component. They are painted, not document objects: nothing is saved into the .gh and nothing enters undo. They are cleared on apply. After the last answer CONNECTOR waits 10 s before apply.
- **D-41 — DeGram boundary widened (owner decision).** The DeGram delegated principal reads mapping sessions and profiles and answers or undoes for its bound project, with the user's stored role. DeGram has full access to the Grasshopper canvas bridge (owner: «полный доступ», including creating and editing components); this plan built only `focus_component`, `start_mapping` and `get_mapping_status`. Route policy and `spec/SECURITY-BOUNDARY.md` were updated.
- **D-42 — DeGram «Модели → Меппинг».** Under each connected model: progress, cards, coloured clickable component buttons (Grasshopper to the front, select, zoom), per-answer undo, and «Запустить меппинг» for a Grasshopper model without a session. A Revit model shows existing sessions only.
- **D-43 — component work.** DeGram changes are committed in the build clone `D:\dgb\src` (`feature/mapping-mvp`), not pushed and with no gitlink bump before the post-demo merge. An unsigned local test build is used for the demo.

**Consequences.**
- Server: `title`/`titleRu`/`items`, `answers`, `document`, `POST /mapping/sessions/{id}/undo`; `GET /mapping/profiles` lists active profiles only. DG.gha: `MappingCanvasTags`, 10 s apply grace, three bridge commands. ui-v2 and DeGram render the same cards.
- Revit rows are not clickable. Selecting in Revit would be a UI write, which D-10 and D-20 forbid until a new owner decision.
- Verified live on 2026-10-18 (rehearsal 2, `ms-56907a90d11f`): one undo and a re-answer, apply 13 s after the last answer, placement, VALIDATOR V1 11/11. Owner: «меппинг протестирован в DeGram — всё работает как положено».

Related: [[knowledge/decisions/Mapping is proposed with an LLM and CONNECTOR places DG components bound by identity (Phase 1303)|D-33…D-38]], [[sessions/2026-10-18 Phase 1303 proposal cards, DeGram mapping sub-tab and live rehearsal through V2|session]].
