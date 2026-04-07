# Roadmap: Design Grammar System v1.1 — Project Knowledge Graph

## Overview

This milestone adds an Obsidian-style Project Knowledge graph to the existing Design Grammar System. Architects can store, update, and query project knowledge via natural language alongside their SWRL validation rules — all within the same tool, same Neo4j database, same Docker stack. The work is purely additive: seven phases move from schema foundation through backend CRUD and LLM workflows to UI panels, with no changes to the existing validation pipeline.

## Milestones

- 🚧 **v1.1 Project Knowledge Graph** — Phases 1–7 (in progress)

## Phases

### v1.1 Project Knowledge Graph

- [ ] **Phase 1: Neo4j Schema Foundation** — Define KnowledgeNote, KnowledgeTag, KnowledgeSession node shapes and full-text index; establish `graph:"KnowledgeGraph"` isolation convention
- [ ] **Phase 2: data-service CRUD + Folder Ingest** — REST endpoints for note CRUD, folder-based .md ingest, session write/read; testable without LLM
- [ ] **Phase 3: n8n Knowledge Workflows + LLM Ingest and Query** — Two new n8n workflows wiring NL insert and NL query through Ollama to Neo4j; session tracking on every interaction
- [ ] **Phase 4: Update Flow Endpoints** — Three-step Match → Propose → Confirm backend; LLM node matching, server-computed diff, confirmed write path
- [ ] **Phase 5: UI Mode Restructuring + Insert and Query Panels** — Sidebar grouped into Validation and Project Knowledge sections; Insert and Query panels wired to live endpoints
- [ ] **Phase 6: UI Update Panel + Inline Diff Editor** — Three-step Update UI with node candidate list, red-highlighted diff preview, and Confirm flow
- [ ] **Phase 7: UI Session History Panel + NeoVis Knowledge View** — Browsable session history panel; NeoVis config extended to visualize KnowledgeGraph nodes distinctly

## Phase Details

### Phase 1: Neo4j Schema Foundation
**Goal**: The KnowledgeGraph partition exists in Neo4j with correct node shapes, relationships, and a working full-text index — ready for all subsequent phases to write against
**Depends on**: Nothing (first phase)
**Requirements**: SCHM-01, SCHM-02, SCHM-03, SCHM-04
**Success Criteria** (what must be TRUE):
  1. A `KnowledgeNote` node can be MERGE'd to Neo4j with `graph:"KnowledgeGraph"`, `project`, `noteId`, `title`, `content`, `tags`, `source`, `createdAt`, `updatedAt` properties
  2. A `KnowledgeTag` node can be created and linked to a `KnowledgeNote` via `TAGGED_WITH` relationship
  3. A `KnowledgeSession` node can be written with `mode`, `prompt`, `result`, and `createdAt` properties
  4. Full-text search query `CALL db.index.fulltext.queryNodes('knowledge_note_search', $query)` returns scored results filtered by `project` property
  5. No existing `Metagraph`, `OntoGraph`, or `ValidationGraph` nodes appear in queries filtering on `graph:"KnowledgeGraph"`
**Plans**: 1 plan
Plans:
- [x] 01-01-PLAN.md — Schema foundation + full-text index + verification

### Phase 2: data-service CRUD + Folder Ingest
**Goal**: Architects can load local markdown files into the knowledge graph and retrieve, update, or delete notes via REST — all verifiable without any LLM or n8n involvement
**Depends on**: Phase 1
**Requirements**: INSK-02, INSK-03, INFR-01, INFR-03
**Success Criteria** (what must be TRUE):
  1. POST `/knowledge/ingest/folder` with a valid path walks `.md` files inside the Docker-mounted repo directory and creates `KnowledgeNote` nodes in Neo4j; returns `{inserted: N, skipped: M}`
  2. A path outside the allowed mount root is rejected with HTTP 403
  3. GET `/knowledge/notes/{project}` returns a list of note titles and IDs for the given project
  4. GET, PUT, and DELETE on `/knowledge/note/{id}` read, update, and remove individual notes from Neo4j
  5. All knowledge endpoints are reachable through the existing Nginx `/data-service/` proxy without new proxy rules
**Plans**: 2 plans
Plans:
- [x] 02-01-PLAN.md — Docker volume mount + folder ingest endpoint with path traversal protection
- [x] 02-02-PLAN.md — CRUD endpoints (list, get, update, delete) + verification test script
**UI hint**: no

### Phase 3: n8n Knowledge Workflows + LLM Ingest and Query
**Goal**: Architects can insert knowledge via a natural language prompt and ask natural language questions — both routes go through Ollama and return results through the existing async polling pattern
**Depends on**: Phase 2
**Requirements**: INSK-01, INSK-04, QRYK-01, QRYK-02, QRYK-03, INFR-02, HSTY-01
**Success Criteria** (what must be TRUE):
  1. Submitting a natural language prompt to POST `/knowledge/ingest/prompt` causes Ollama to extract a title, tags, and content, and a `KnowledgeNote` node appears in Neo4j within the async polling round-trip
  2. Submitting a natural language question to POST `/knowledge/query` returns a human-readable answer drawn from matching notes, plus the Cypher query used for the search
  3. Every insert-prompt and query operation automatically writes a `KnowledgeSession` node with `mode`, `prompt`, `result`, and `createdAt` populated
  4. GET `/knowledge/sessions/{project}` returns all sessions written so far in reverse-chronological order
**Plans**: 2 plans
Plans:
- [x] 03-01-PLAN.md — Test scaffold + sessions endpoint + knowledge-ingest n8n workflow
- [x] 03-02-PLAN.md — Knowledge-query n8n workflow + end-to-end verification

### Phase 4: Update Flow Endpoints
**Goal**: The three-step update backend is live — an architect can describe what to change, receive a list of matching notes, get a diff-annotated proposed edit, and confirm the write — with no LLM output silently overwriting Neo4j
**Depends on**: Phase 3
**Requirements**: UPDK-01, UPDK-02, UPDK-03, UPDK-04, UPDK-05, UPDK-06
**Success Criteria** (what must be TRUE):
  1. POST `/knowledge/update/match` with a natural language prompt returns a candidate list of `KnowledgeNote` node IDs and titles ranked by full-text relevance
  2. POST `/knowledge/update/propose` with selected node IDs returns diff-annotated content per note, with additions and deletions marked as HTML spans
  3. POST `/knowledge/update/confirm` with reviewed content writes the new text to Neo4j and returns the list of affected node IDs; the original content is not overwritten until this call succeeds
  4. Each confirmed update creates a `KnowledgeSession` node recording the prompt and affected nodes
**Plans**: 1 plan
Plans:
- [ ] 01-01-PLAN.md — Schema foundation + full-text index + verification

### Phase 5: UI Mode Restructuring + Insert and Query Panels
**Goal**: The sidebar is reorganized into Validation and Project Knowledge sections; architects can insert knowledge via folder path or NL prompt and query the knowledge graph entirely from the browser
**Depends on**: Phase 3
**Requirements**: UIST-01, UIST-02, UIST-03, UIST-05
**Success Criteria** (what must be TRUE):
  1. The sidebar shows a "Validation" section containing the existing Insert Rules, Query Rules, and Edit Rules modes — existing functionality is unchanged
  2. The sidebar shows a "Project Knowledge" section with Insert Knowledge and Query Knowledge modes visible
  3. In Insert Knowledge mode, the user can enter a folder path and submit it; the panel shows the number of notes imported
  4. In Insert Knowledge mode, the user can type a natural language prompt and submit it; the panel shows the created note title via async polling
  5. In Query Knowledge mode, the user can type a question and see a natural language answer in the Response field and the Cypher query in the Cypher panel
**Plans**: 2 plans
Plans:
- [ ] 05-01-PLAN.md � Sidebar restructuring + knowledge state + Insert Knowledge panel
- [ ] 05-02-PLAN.md � Query Knowledge panel + full verification checkpoint
**UI hint**: yes

### Phase 6: UI Update Panel + Inline Diff Editor
**Goal**: Architects can execute the full three-step update flow in the browser — describe what to change, see matching nodes highlighted, review red-highlighted diff, and confirm the edit
**Depends on**: Phase 4
**Requirements**: UIST-04
**Success Criteria** (what must be TRUE):
  1. In Update Knowledge mode, submitting a prompt shows a selectable list of candidate note titles
  2. After selecting one or more nodes and clicking Edit, the panel renders the LLM-proposed changes with deletions shown in red strikethrough and additions in red bold — no confirmed write has occurred yet
  3. The diff panel sits adjacent to an editable textarea containing the proposed text; the user can modify the textarea before confirming
  4. Clicking Confirm sends the final text to the backend and the sidebar shows a notification listing the updated node titles
**Plans**: 2 plans
Plans:
- [ ] 06-01-PLAN.md — CSS + state + Match view + Propose handler
- [ ] 06-02-PLAN.md — Review view + Summary + Confirm + verification checkpoint
**UI hint**: yes

### Phase 7: UI Session History Panel + NeoVis Knowledge View
**Goal**: Architects can browse their past knowledge interactions in the UI and see KnowledgeNote and KnowledgeTag nodes rendered distinctly in the graph viewer
**Depends on**: Phase 6
**Requirements**: UIST-06, HSTY-02, HSTY-03, INFR-04
**Success Criteria** (what must be TRUE):
  1. Session History is accessible as a panel in the sidebar showing all past interactions in reverse-chronological order with mode tag, prompt text, and date visible per entry
  2. The session list can be filtered by mode (insert, update, query) and the list updates immediately on filter change
  3. Session history survives a browser data clear and hard refresh — data comes from Neo4j, not localStorage
  4. In the Graph Viewer, `KnowledgeNote` and `KnowledgeTag` nodes are visually distinct from SWRL metagraph nodes (different color); a NeoVis query filtered to `graph:"KnowledgeGraph"` returns only knowledge nodes
**Plans**: 1 plan
Plans:
- [ ] 01-01-PLAN.md — Schema foundation + full-text index + verification
**UI hint**: yes

## Progress

**Execution Order:** 1 → 2 → 3 → 4 → 5 → 6 → 7

| Phase | Milestone | Plans Complete | Status | Completed |
|-------|-----------|----------------|--------|-----------|
| 1. Neo4j Schema Foundation | v1.1 | 1/1 | Complete | 2026-04-06 |
| 2. data-service CRUD + Folder Ingest | v1.1 | 0/2 | Planning complete | - |
| 3. n8n Knowledge Workflows | v1.1 | 0/2 | Planning complete | - |
| 4. Update Flow Endpoints | v1.1 | 0/? | Not started | - |
| 5. UI Mode Restructuring + Insert and Query Panels | v1.1 | 0/2 | Planning complete | - |
| 6. UI Update Panel + Inline Diff Editor | v1.1 | 0/2 | Planning complete | - |
| 7. UI Session History Panel + NeoVis Knowledge View | v1.1 | 0/? | Not started | - |

---
*Roadmap created: 2026-04-06*
*Milestone: v1.1 Project Knowledge Graph*
*Coverage: 30/30 v1.1 requirements mapped*
