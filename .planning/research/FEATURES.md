# Feature Research

**Domain:** Project Knowledge Graph — LLM-assisted knowledge management integrated into an architecture design system (Design Grammar System v1.1)
**Researched:** 2026-04-05
**Confidence:** MEDIUM (domain patterns verified via Neo4j LLM Graph Builder, Obsidian, and AEC knowledge tools; specific integration patterns are reasoned from those references)

---

## Feature Landscape

### Table Stakes (Users Expect These)

Features users assume exist. Missing these = product feels incomplete for a knowledge management tool in a professional AEC context.

| Feature | Why Expected | Complexity | Notes |
|---------|--------------|------------|-------|
| Insert knowledge via NL prompt | Matches Insert Rules UX already present — users expect same pattern | LOW | Route through same n8n/Ollama pipeline; persist as `KnowledgeNode` label in Neo4j |
| Insert knowledge from local markdown files | Obsidian-trained users treat local .md files as primary source; folder import is baseline | MEDIUM | Requires backend file path input or drag-drop; parse frontmatter + body; chunk if large |
| Query knowledge in natural language | Core value of any LLM-backed knowledge tool — ask a question, get an answer | LOW | Same Ollama query loop; knowledge subgraph only; answer rendered in sidebar Response field |
| Graph visualization of knowledge nodes | Users expect to see knowledge as connected graph — this is the DGS signature interaction | LOW | NeoVis already present; filter by `graph:"knowledge"` property; no new library needed |
| Project isolation | All knowledge scoped to project, same as SWRL rules — without this, graph pollutes across projects | LOW | Property `project` + `graph:"knowledge"` on every KnowledgeNode; already-established pattern |
| Session history: browsable list of interactions | Chat/tool history is now a universal expectation in LLM tools — prompt, result, mode, timestamp | MEDIUM | Persist as `Session` nodes in Neo4j or lightweight JSON store; ordered chronologically; filterable by mode |
| UI mode restructuring: Validation vs Project Knowledge | Users need orientation — mixing rule atoms and knowledge notes in one sidebar is confusing | LOW | Sidebar section headers; no routing change needed; grouping is cosmetic + logical |
| Clear visual distinction between Knowledge graph and SWRL graph | Two distinct data models in one Neo4j DB — must not appear as one undifferentiated blob | MEDIUM | Node color/shape differentiation in NeoVis config; legend; filter panel |

### Differentiators (Competitive Advantage)

Features that set DGS apart. Not universally expected, but valuable for architecture professional users.

| Feature | Value Proposition | Complexity | Notes |
|---------|-------------------|------------|-------|
| LLM-driven node matching for Update Knowledge | User describes what to change in NL; LLM finds the matching graph nodes — no manual graph traversal needed | HIGH | LLM generates Cypher to identify candidate nodes; return candidate set; show isolated subgraph; user confirms selection |
| Inline diff editor with red-highlighted LLM changes | User sees exactly what the LLM proposes to change before committing — builds trust, prevents silent corruption | HIGH | contenteditable or `<pre>` with `<span class="change-new">` red spans; no Vite needed; no CodeMirror dependency needed |
| Subgraph isolation on node selection | Clicking "select these nodes" collapses graph to only the affected nodes + their neighbors — reduces cognitive load during updates | MEDIUM | NeoVis `updateWithCypher` filter; existing pattern used by Graph Viewer already |
| Validation + Knowledge in same project context | Design rules AND project notes live side-by-side; users can query "what rule governs X?" and "what did we decide about X?" in one tool | LOW | Architectural value: same project ID links both graphs; cross-mode query is a roadmap item |
| Session tracking with mode tagging | Every insert/update/query tagged by mode (insert-knowledge, update-knowledge, query-knowledge); filterable history gives audit trail useful for AEC compliance contexts | MEDIUM | Add `mode` property to Session node; filter UI in history panel |
| Load knowledge from Obsidian vault path | DGS already uses an Obsidian vault internally (DG_OBSIDIAN/); exposing this as a user-facing input path bridges internal and user workflows | MEDIUM | Accept folder path in insert form; walk directory for .md files; skip system folders |

### Anti-Features (Commonly Requested, Often Problematic)

| Feature | Why Requested | Why Problematic | Alternative |
|---------|---------------|-----------------|-------------|
| Real-time collaborative editing of knowledge nodes | Seems natural for team tools | Requires WebSocket infrastructure, conflict resolution, presence awareness — none of which exist in DGS; heavy lift, out of scope for v1.1 | Single-writer model with session history is sufficient for architect workflow; add collab in v2 if validated |
| RAG (vector embeddings + semantic search) | Appears to give "smarter" answers | Adds vector DB or embedding pipeline; conflicts with constraint "No RAG system"; Ollama + Neo4j full-text search is adequate for note-scale data | Full-text search via Neo4j `CONTAINS` or full-text index; LLM interprets retrieved text |
| Rich markdown editor (WYSIWYG, toolbar) | Users familiar with Notion/Confluence expect formatting UI | Requires a third-party editor library (Quill, TipTap, ProseMirror) or a Vite sub-app; inconsistent with no-JSX-build constraint for main SPA | Plain `<textarea>` for input; rendered `<pre>` with red-span diffs for review; inline contenteditable for confirm step — sufficient for note editing |
| Knowledge graph auto-layout on every update | Users want graph to "look clean" automatically | Auto-layout causes jarring redraws; NeoVis/vis.js physics already handles initial layout; re-running on every update is disorienting | Let physics stabilize naturally on initial load; persist node positions for revisited graphs |
| Knowledge nodes linked to SWRL Rule atoms in the same graph view | Conceptually appealing — "see what rule is connected to this design note" | Two data models (ontology atoms vs markdown notes) have incompatible visual representations; mixed graph is confusing without careful design | Separate graph views per graph type; cross-reference via shared project ID; v2 feature to add cross-links |
| Versioned history of individual knowledge node content | Git-like change history per node | Requires storing diffs or snapshots in Neo4j; high storage and query complexity for marginal gain at note-scale | Session history captures "what was changed and when" at interaction level; full node versioning deferred to v2 |

---

## Feature Dependencies

```
[Insert Knowledge (markdown file)]
    └──requires──> [File path input + backend walk] (data-service endpoint)
                       └──requires──> [KnowledgeNode label schema in Neo4j]

[Insert Knowledge (NL prompt)]
    └──requires──> [KnowledgeNode label schema in Neo4j]
    └──requires──> [n8n knowledge-ingest workflow (new or extended)]

[Update Knowledge]
    └──requires──> [Insert Knowledge] (nodes must exist before updating)
    └──requires──> [LLM node-matching Cypher generation]
    └──requires──> [Subgraph isolation view in NeoVis]
    └──requires──> [Inline diff editor component]

[Inline diff editor]
    └──requires──> [LLM proposed text output] (structured: original + proposed)

[Query Knowledge]
    └──requires──> [KnowledgeNode label schema in Neo4j]
    └──requires──> [LLM Cypher generation for knowledge subgraph]

[Session History]
    └──requires──> [Insert Knowledge] (to have sessions to store)
    └──requires──> [Query Knowledge] (to have sessions to store)
    └──requires──> [Update Knowledge] (to have sessions to store)

[UI mode restructuring]
    └──independent──> [all new features] (cosmetic, can ship first as scaffold)

[Subgraph isolation] ──enhances──> [Update Knowledge]
[Session mode tagging] ──enhances──> [Session History]
[Project isolation] ──required by──> [all Knowledge features] (already exists, enforce via property)
```

### Dependency Notes

- **Insert Knowledge requires KnowledgeNode schema:** New node label(s) needed before any other knowledge feature can function. This is the foundational schema decision for v1.1.
- **Update Knowledge requires Insert Knowledge:** Cannot update nodes that don't exist; Insert must ship and be testable first.
- **Update Knowledge requires Inline diff editor:** The review-and-confirm UX is the safety mechanism; shipping Update without it risks silent LLM corruption of notes.
- **Session History requires all three modes:** Its value compounds as the other modes ship; implement storage from day one but surface the UI after Insert is stable.
- **UI mode restructuring is independent:** Cosmetic grouping can ship immediately as a scaffold without any backend changes. Recommended as Phase 1 to give users orientation before new features appear.

---

## MVP Definition

### Launch With (v1.1 core)

Minimum viable product — what's needed to validate the concept.

- [ ] **KnowledgeNode schema** — foundational; nothing else works without distinct labeling in Neo4j
- [ ] **UI mode restructuring** — Validation / Project Knowledge sidebar grouping; gives users orientation; zero backend cost
- [ ] **Insert Knowledge via NL prompt** — primary entry point; validates LLM-to-knowledge-graph pipeline
- [ ] **Insert Knowledge from local markdown folder** — architects have existing notes; folder import unlocks real adoption
- [ ] **Query Knowledge** — closes the loop: insert then ask; validates the knowledge graph has utility
- [ ] **Session history storage** — store from day one; losing interaction history is not recoverable retroactively

### Add After Validation (v1.1 extended)

Features to add once Insert + Query are confirmed working.

- [ ] **Update Knowledge with node matching** — trigger: users complain that re-inserting updated notes creates duplicates
- [ ] **Inline diff editor** — required companion to Update; trigger: Update ships
- [ ] **Subgraph isolation on node selection** — trigger: Update ships and graph with many nodes becomes hard to navigate
- [ ] **Session history UI (browsable panel)** — trigger: enough sessions exist to make browsing useful

### Future Consideration (v2+)

Features to defer until v1.1 is validated.

- [ ] **Cross-graph linking (Knowledge ↔ Rules)** — defer: requires resolved UX model for mixed graph display
- [ ] **Obsidian vault path as live sync source** — defer: two-way sync is complex; one-time import is sufficient for v1.1
- [ ] **Versioned node history** — defer: session log provides adequate audit trail for current user scale
- [ ] **Collaborative editing** — defer: single-writer model is sufficient; collab requires infrastructure investment

---

## Feature Prioritization Matrix

| Feature | User Value | Implementation Cost | Priority |
|---------|------------|---------------------|----------|
| UI mode restructuring | MEDIUM | LOW | P1 |
| KnowledgeNode schema (Neo4j labels) | HIGH | LOW | P1 |
| Insert Knowledge via NL prompt | HIGH | LOW | P1 |
| Insert Knowledge from markdown folder | HIGH | MEDIUM | P1 |
| Query Knowledge | HIGH | LOW | P1 |
| Session history storage | MEDIUM | LOW | P1 |
| Session history browsable UI | MEDIUM | MEDIUM | P2 |
| Update Knowledge — LLM node matching | HIGH | HIGH | P2 |
| Inline diff editor (red-span review) | HIGH | MEDIUM | P2 |
| Subgraph isolation (NeoVis filter) | MEDIUM | MEDIUM | P2 |
| Obsidian vault path input | LOW | MEDIUM | P3 |
| Cross-graph linking (Knowledge ↔ Rules) | MEDIUM | HIGH | P3 |
| Versioned node history | LOW | HIGH | P3 |

**Priority key:**
- P1: Must have for v1.1 launch
- P2: Should have, add when P1 stable
- P3: Nice to have, future consideration

---

## Competitor Feature Analysis

| Feature | Obsidian (desktop) | Neo4j LLM Graph Builder | DGS Approach |
|---------|--------------------|-------------------------|--------------|
| Knowledge input | Markdown files, manual linking | PDF/URL drag-drop, LLM extracts | NL prompt + local folder path |
| Graph visualization | Interactive canvas, bidirectional links | Neo4j Bloom, node/relationship labels | NeoVis.js (existing), filtered by `graph:"knowledge"` |
| Query | Search + backlinks, no NL | Parallel retrievers (local + global) | Ollama NL query → Cypher → answer in sidebar |
| Update workflow | Direct markdown edit in editor | Re-ingest document | LLM node-matching → subgraph isolation → inline diff review |
| Session history | None (file system is the log) | None exposed to user | Explicit `Session` node storage per interaction |
| Collaboration | Single-user by default (sync via paid plugin) | Single-user (per-session isolation) | Single-user, project-scoped |
| Integration with design rules | None | None | Same project ID links knowledge graph and SWRL rules |

**Key differentiation:** DGS's update workflow (LLM matches nodes → user confirms selection → inline diff → user confirms changes) is more deliberate than both Obsidian (direct edit) and Neo4j Builder (full re-ingest). This suits an architecture compliance context where accidental overwrites of design rationale are costly.

---

## Dependency on Existing System

| New Feature | Existing Component Used | Integration Point |
|-------------|------------------------|-------------------|
| Insert Knowledge (NL) | n8n + Ollama + Neo4j | New n8n workflow or extend existing; same webhook pattern |
| Insert Knowledge (folder) | data-service FastAPI | New endpoint `/knowledge/ingest`; walk .md files, POST to Neo4j |
| Query Knowledge | n8n + Ollama + Neo4j | New n8n workflow; same sidebar Response field pattern |
| Update Knowledge | data-service + Ollama + Neo4j | New endpoint `/knowledge/match`; LLM generates Cypher match |
| Inline diff editor | Main UI (index.html) | New component using `contenteditable` or `<pre>` + red spans; no build step |
| Session history | Neo4j or data-service | `Session` node or append-only JSON; `mode`, `prompt`, `result`, `date`, `projectId` |
| UI restructuring | graph-viewer/index.html | Sidebar section headers; no backend change |
| Subgraph isolation | NeoVis.js config | `updateWithCypher` call with filtered node IDs; existing pattern |

---

## Sources

- [Top Graph-Based Knowledge Management Tools 2025](https://blog.knowing.app/posts/top-graph-based-knowledge-management-tools-2025/)
- [Neo4j LLM Knowledge Graph Builder — First Release of 2025](https://neo4j.com/blog/developer/llm-knowledge-graph-builder-release/)
- [Obsidian (software) — Wikipedia](https://en.wikipedia.org/wiki/Obsidian_(software))
- [Obsidian in 2025: Knowledge Management Tool](https://productivitywork.com/obsidian-in-2025-the-revolutionary-knowledge-management-tool-thats-transforming-how-we-think-and-learn/)
- [Building a Visual Diff System for AI Edits](https://medium.com/illumination/building-a-visual-diff-system-for-ai-edits-like-git-blame-for-llm-changes-171899c36971)
- [LLM Knowledge Graph Builder Front-End Architecture](https://medium.com/neo4j/llm-knowledge-graph-builder-frontend-architecture-and-integration-99922318a90b)
- [Best Practices: Knowledge Management for AEC Firms](https://www.knowledge-architecture.com/aec-knowledge-management)
- [LLM-empowered knowledge graph construction: A survey](https://arxiv.org/html/2510.20345v1)

---
*Feature research for: Project Knowledge Graph module — Design Grammar System v1.1*
*Researched: 2026-04-05*
