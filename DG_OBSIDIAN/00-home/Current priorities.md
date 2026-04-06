---
tags: [home, priorities]
date: 2026-04-05
---

# Current Priorities

## Active

1. **v1.1 Phase 01 human verification** — run `python test/test_knowledge_schema.py` against live Neo4j and verify startup hook creates index. See `01-HUMAN-UAT.md`.
2. **v1.1 Phase 02: data-service CRUD + Folder Ingest** — REST endpoints for note CRUD, folder-based .md ingest. Next phase to plan/execute.
3. **Model Viewer visual bugs** — rotation/mixed state in validation viewport needs fixing. See [[Model viewer needs rotation fix and validation management]].
4. **Model Viewer as parallel view** — rebuild so it opens from Project page alongside Graph Viewer.

## Upcoming

- v1.1 Phases 3–7 (LLM workflows, update flow, UI panels, session history)
- Improve LLM Cypher generation accuracy (schema constraint adherence)
- Add more few-shot examples to [[n8n orchestrates LLM-powered rule ingestion and graph queries|ingest prompt]]
- Harden [[Passwords hashed client-side with SubtleCrypto SHA-256|authentication]] with server-side auth
- Consider localStorage quota management for run screenshots/settings (prune old data)

## Completed Recently

- **Per-run graphics state & screenshots** — each validation run saves/restores its own Graphics Settings Bar state and viewport thumbnail. See [[Per-run graphics state and screenshot persistence]].
- **Screenshot tiles across all pages** — Project tiles on All Projects page, Grammar Viewer and Model Viewer tiles on Project page all show captured viewport screenshots with cover-crop aspect ratio.
- Validation management — delete for validation runs in Model Viewer
- Multi-page SPA with RegisterPage → HomePage → ProjectPage → GraphViewerPage
- Speckle integration for validation overlay publishing
- Grasshopper VALIDATOR component with optional data-service publish
- v3 schema migration (Rule_Id, Atom_Id, SWRL_label)
