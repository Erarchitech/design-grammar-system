# Requirements: Design Grammar System v1.1 — Project Knowledge Graph

**Defined:** 2026-04-05
**Core Value:** Architects can store, update, and query project knowledge via natural language alongside their design validation rules — all within one integrated tool.

## v1.1 Requirements

Requirements for Project Knowledge Graph milestone. Each maps to roadmap phases.

### Schema

- [ ] **SCHM-01**: Neo4j stores KnowledgeNote nodes with `graph:"KnowledgeGraph"` label, project-isolated via `project` property
- [ ] **SCHM-02**: Neo4j stores KnowledgeTag nodes linked to KnowledgeNote via TAGGED_WITH relationship
- [ ] **SCHM-03**: Neo4j stores KnowledgeSession nodes tracking every knowledge interaction (prompt, result, mode, date)
- [ ] **SCHM-04**: Neo4j full-text index on KnowledgeNote `title` and `content` fields is created at data-service startup

### Insert Knowledge

- [ ] **INSK-01**: User can insert knowledge via natural language prompt — LLM extracts title, tags, content and creates KnowledgeNote nodes
- [ ] **INSK-02**: User can insert knowledge from a local repository folder — data-service reads `.md` files and creates KnowledgeNote nodes
- [ ] **INSK-03**: Folder path input is validated server-side to prevent path traversal outside allowed root
- [ ] **INSK-04**: Each insert operation creates a KnowledgeSession node recording prompt, result, and timestamp

### Update Knowledge

- [ ] **UPDK-01**: User types an update prompt; LLM identifies matching KnowledgeNote nodes via full-text search and returns candidate list
- [ ] **UPDK-02**: Matching nodes are isolated in the graph view; user selects one or several nodes
- [ ] **UPDK-03**: User clicks Edit; LLM proposes edits to selected notes with changes highlighted in red
- [ ] **UPDK-04**: User reviews proposed changes in an inline text editor (textarea + diff panel with red-highlighted changes)
- [ ] **UPDK-05**: User clicks Confirm to save changes to Neo4j; sidebar notification lists affected nodes
- [ ] **UPDK-06**: Each update operation creates a KnowledgeSession node recording the interaction

### Query Knowledge

- [ ] **QRYK-01**: User types a natural language question; LLM searches knowledge graph via full-text index and returns NL answer in sidebar Response field
- [ ] **QRYK-02**: Cypher query used for the search is displayed in the Cypher panel
- [ ] **QRYK-03**: Each query operation creates a KnowledgeSession node recording the interaction

### Session History

- [ ] **HSTY-01**: All knowledge interactions (insert, update, query) are automatically saved with prompt, result contents, date tags, and mode identifier
- [x] **HSTY-02**: Session history is browsable in the UI in reverse-chronological order, filterable by mode
- [x] **HSTY-03**: Session history persists in Neo4j (not localStorage) and survives browser data clears

### UI Structure

- [ ] **UIST-01**: Existing modes (Insert Rules, Query Rules, Edit Rules) are grouped under a "Validation" section in the sidebar
- [ ] **UIST-02**: New "Project Knowledge" section appears in the sidebar with Insert Knowledge, Update Knowledge, and Query Knowledge modes
- [ ] **UIST-03**: Insert Knowledge mode shows a folder path input field and a prompt input field
- [ ] **UIST-04**: Update Knowledge mode shows a prompt field for node matching, a node selection area, an Edit button, an inline diff editor, and a Confirm button
- [ ] **UIST-05**: Query Knowledge mode shows a prompt field and a Response display area
- [x] **UIST-06**: Session History is accessible as a browsable panel showing past interactions

### Backend Infrastructure

- [ ] **INFR-01**: data-service exposes `/knowledge/*` REST endpoint group (ingest, CRUD, update flow, query, sessions)
- [ ] **INFR-02**: Two new n8n workflows handle knowledge-ingest and knowledge-query via existing webhook + Ollama + Neo4j pattern
- [ ] **INFR-03**: Docker Compose mounts a read-only volume for repository folder access by data-service
- [ ] **INFR-04**: NeoVis config supports visualizing KnowledgeGraph nodes with distinct colors/shapes from SWRL metagraph nodes

## v2 Requirements

Deferred to future release. Tracked but not in current roadmap.

### Cross-Graph

- **XGRP-01**: Knowledge nodes can be linked to SWRL Rule atoms for cross-domain queries
- **XGRP-02**: Mixed graph view shows both Knowledge and SWRL nodes with visual distinction

### Advanced Knowledge

- **ADVK-01**: Versioned history of individual knowledge node content (git-like diffs per node)
- **ADVK-02**: Obsidian vault path as live sync source (two-way sync with local `.md` files)
- **ADVK-03**: RAG-based semantic search when vault grows beyond full-text search capacity

### Collaboration

- **COLB-01**: Multiple users can edit knowledge nodes with conflict resolution
- **COLB-02**: Real-time presence indicators show who is editing which node

## Out of Scope

| Feature | Reason |
|---------|--------|
| RAG / vector embeddings | Explicitly excluded — Neo4j full-text search sufficient for note-scale data; no embedding model served |
| Rich WYSIWYG editor (CodeMirror, Monaco) | Requires npm build step — violates no-JSX constraint for main SPA |
| New Docker service for knowledge | data-service already has Neo4j driver and execution-result store — new container adds ops complexity for no gain |
| LangChain / AI Agent n8n nodes | Breaks existing plain HTTP-node workflow pattern |
| Grasshopper integration for knowledge | Knowledge is informational only — no validation path needed |
| Mobile app for knowledge | Desktop/web-first for architect workflows |
| Knowledge node content > 100KB | Ollama context window limitation; truncate before LLM processing |

## Traceability

Which phases cover which requirements. Updated during roadmap creation.

| Requirement | Phase | Status |
|-------------|-------|--------|
| SCHM-01 | Phase 1 | Pending |
| SCHM-02 | Phase 1 | Pending |
| SCHM-03 | Phase 1 | Pending |
| SCHM-04 | Phase 1 | Pending |
| INSK-02 | Phase 2 | Pending |
| INSK-03 | Phase 2 | Pending |
| INFR-01 | Phase 2 | Pending |
| INFR-03 | Phase 2 | Pending |
| INSK-01 | Phase 3 | Pending |
| INSK-04 | Phase 3 | Pending |
| QRYK-01 | Phase 3 | Pending |
| QRYK-02 | Phase 3 | Pending |
| QRYK-03 | Phase 3 | Pending |
| INFR-02 | Phase 3 | Pending |
| HSTY-01 | Phase 3 | Pending |
| UPDK-01 | Phase 4 | Pending |
| UPDK-02 | Phase 4 | Pending |
| UPDK-03 | Phase 4 | Pending |
| UPDK-04 | Phase 4 | Pending |
| UPDK-05 | Phase 4 | Pending |
| UPDK-06 | Phase 4 | Pending |
| UIST-01 | Phase 5 | Pending |
| UIST-02 | Phase 5 | Pending |
| UIST-03 | Phase 5 | Pending |
| UIST-05 | Phase 5 | Pending |
| UIST-04 | Phase 6 | Pending |
| UIST-06 | Phase 7 | Complete |
| HSTY-02 | Phase 7 | Complete |
| HSTY-03 | Phase 7 | Complete |
| INFR-04 | Phase 7 | Pending |

**Coverage:**
- v1.1 requirements: 30 total
- Mapped to phases: 30
- Unmapped: 0 ✓

---
*Requirements defined: 2026-04-05*
*Last updated: 2026-04-05 after initial definition*
