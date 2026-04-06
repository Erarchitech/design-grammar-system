---
tags: [home, priorities]
date: 2026-04-05
---

# Current Priorities

## Active

1. **v1.1 Phase 03: Execute** — run `/gsd-execute-phase 3`. Two plans: knowledge-ingest workflow + sessions endpoint (wave 1), knowledge-query workflow + E2E verify (wave 2). After execution, import workflow JSONs into n8n.
2. **v1.1 Phase 02 human verification** — run `python test/test_knowledge_crud.py` against live Docker stack. See `02-HUMAN-UAT.md`.
3. **v1.1 Phase 01 human verification** — run `python test/test_knowledge_schema.py` against live Neo4j. See `01-HUMAN-UAT.md`.
4. **Model Viewer visual bugs** — rotation/mixed state in validation viewport needs fixing. See [[Model viewer needs rotation fix and validation management]].
5. **Model Viewer as parallel view** — rebuild so it opens from Project page alongside Graph Viewer.

## Upcoming

- v1.1 Phases 4–7 (update flow, UI panels, session history)
- Improve LLM Cypher generation accuracy (schema constraint adherence)
- Add more few-shot examples to [[n8n orchestrates LLM-powered rule ingestion and graph queries|ingest prompt]]
- Harden [[Passwords hashed client-side with SubtleCrypto SHA-256|authentication]] with server-side auth
- Consider localStorage quota management for run screenshots/settings (prune old data)

## Completed Recently

- **v1.1 Phase 03: Context + Planning** — discussed 4 gray areas (LLM prompt design, query strategy, n8n wiring, session tracking), 11 decisions locked, researched, 2 plans created and verified.
- **v1.1 Phase 02: data-service CRUD + Folder Ingest** — folder ingest endpoint, 4 CRUD endpoints, verification script. All automated checks passed, human UAT pending.
- **Per-run graphics state & screenshots** — each validation run saves/restores its own Graphics Settings Bar state and viewport thumbnail. See [[Per-run graphics state and screenshot persistence]].
- **Screenshot tiles across all pages** — Project tiles on All Projects page, Grammar Viewer and Model Viewer tiles on Project page all show captured viewport screenshots with cover-crop aspect ratio.
- Validation management — delete for validation runs in Model Viewer
- Multi-page SPA with RegisterPage → HomePage → ProjectPage → GraphViewerPage
- Speckle integration for validation overlay publishing
- Grasshopper VALIDATOR component with optional data-service publish
- v3 schema migration (Rule_Id, Atom_Id, SWRL_label)
