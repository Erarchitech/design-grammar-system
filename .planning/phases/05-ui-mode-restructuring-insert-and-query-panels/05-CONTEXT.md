# Phase 5: UI Mode Restructuring + Insert and Query Panels - Context

**Gathered:** 2026-04-07
**Status:** Ready for planning

<domain>
## Phase Boundary

Reorganize the Graph Viewer sidebar from a flat mode dropdown into a tabbed layout with two top-level tabs: "DesignRules" (existing validation modes) and "Specs&Notes" (new knowledge modes). Wire Insert Knowledge (folder import + NL prompt) and Query Knowledge panels to live backend endpoints built in Phases 2-3. No Update panel (Phase 6) and no Session History panel (Phase 7).

</domain>

<decisions>
## Implementation Decisions

### Sidebar Navigation
- **D-01:** Two top-level tabs ("DesignRules" / "Specs&Notes") appear at the top of the sidebar, beneath the Project back button — tabs switch the entire sidebar content area
- **D-02:** Existing modes renamed: "Validation" section becomes "DesignRules" tab; new "Project Knowledge" section becomes "Specs&Notes" tab
- **D-03:** Within each tab, modes use the existing dropdown pattern — current `MODE_OPTIONS` dropdown stays for DesignRules (Insert Rules, Query Rules, Edit Rules), a new dropdown appears for Specs&Notes (Insert Knowledge, Query Knowledge)
- **D-04:** Tab styling matches existing `.prompt-tab` / `.prompt-tab.active` CSS classes (the Rules Prompt / Cypher Expression toggle pattern)
- **D-05:** No "new" badge or indicator on the Specs&Notes tab — treat as a normal UI element

### State Management
- **D-06:** When switching between DesignRules and Specs&Notes tabs, all state persists — prompt text, response text, graph view, etc. are kept per-tab (not cleared)
- **D-07:** Graph View dropdown (OntoGraph / MetaGraph) is only visible when DesignRules tab is active — hidden in Specs&Notes modes (until Phase 7 adds KnowledgeGraph view)

### Insert Knowledge Panel
- **D-08:** Two sub-tabs within the Insert Knowledge mode: "From Folder" and "From Prompt" — tab toggle pattern within the panel, similar to the existing Rules Prompt / Cypher Expression toggle
- **D-09:** "From Folder" shows a text input with placeholder hint (e.g., `/repo/docs`) and a help tooltip explaining which paths are accessible via Docker mount
- **D-10:** "From Prompt" shows a textarea for natural language input (same style as existing prompt textarea)
- **D-11:** Both sub-modes show results in the Response textarea with inline success messages: "Imported 12 notes" for folder, "Created note: [title]" for prompt

### Query Knowledge Panel
- **D-12:** Query Knowledge mode layout mirrors existing Query Rules — prompt textarea, submit button, Response textarea, and Cypher panel
- **D-13:** Uses workflow key `knowledge-query` with the existing `startPollingResult` async polling pattern

### Async Polling UX
- **D-14:** Knowledge operations reuse the existing step indicator + progress bar pattern with knowledge-specific step labels (e.g., "Extracting title/tags...", "Writing to graph..." for insert; "Searching knowledge graph...", "Generating answer..." for query)
- **D-15:** Errors display in the Response textarea with the same styling as Rules errors

### Claude's Discretion
- Exact step labels for knowledge insert and query operations
- CSS for the top-level tab bar (dimensions, spacing) — must match `.prompt-tab` style
- State variable naming and React component refactoring approach
- How to handle the "Clear the Graph" button visibility in Specs&Notes modes
- Whether to refactor `GraphViewerPage` into sub-components or keep as one function

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Main UI (primary modification target)
- `graph-viewer/index.html` — Single-file React 18 SPA (~2425 lines); `MODE_OPTIONS` at line 942, `GraphViewerPage` component at line 1347, mode dropdown at line 2281, sidebar layout at line 2316
- `graph-viewer/config.template.js` — NeoVis config (env vars injected at runtime)

### Existing patterns to replicate
- `graph-viewer/index.html` lines 2394-2406 — Rules Prompt / Cypher Expression tab toggle (reference for tab styling and behavior)
- `graph-viewer/index.html` lines 1554-1676 — `startPollingResult` async polling pattern (reuse for knowledge operations with new workflow keys)
- `graph-viewer/index.html` lines 942-946 — `MODE_OPTIONS` array (extend or replicate for knowledge modes)

### Backend endpoints (already built)
- `data-service/app.py` — Knowledge CRUD endpoints at lines 934-1085 (folder ingest, note CRUD, sessions)
- `data-service/app.py` — Execution result polling at lines 893-928

### Upstream phase context
- `.planning/phases/03-n8n-knowledge-workflows-llm-ingest-and-query/03-CONTEXT.md` — D-07/D-08 (execution result workflow keys: `knowledge-ingest`, `knowledge-query`), D-09 (webhook paths)

### Proxy routing
- `graph-viewer/nginx.conf` — Reverse proxy routes; `/data-service/` and `/n8n/` already configured

### Requirements
- `.planning/REQUIREMENTS.md` — UIST-01, UIST-02, UIST-03, UIST-05

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- **Tab toggle pattern**: Lines 2394-2406 in `index.html` — `.prompt-tab` / `.prompt-tab.active` CSS classes and click handler pattern; reuse for both top-level tabs and Insert Knowledge sub-tabs
- **Mode dropdown**: `MODE_OPTIONS` array + `modeControl` dropdown at line 2281 — replicate for Specs&Notes modes
- **Async polling**: `startPollingResult()` function — reuse with workflow keys `knowledge-ingest` and `knowledge-query`
- **Response textarea**: Existing `responseText` state + textarea — mirror for knowledge responses
- **Step indicators**: Existing `steps` array + step display logic — define new step arrays for knowledge operations
- **Progress bar**: `.progress` CSS class + `progress` state — reuse as-is

### Established Patterns
- **React.createElement (no JSX)**: All UI via `const e = React.createElement` — knowledge UI must follow same pattern
- **State via hooks**: `useState`/`useEffect`/`useRef` in functional components — same approach for new state
- **CSS custom properties**: `:root` variables for theming — use existing variables for knowledge UI
- **Single-file architecture**: Everything in one `index.html` — new components are functions in the same file

### Integration Points
- **`GraphViewerPage` function**: The single component that renders the sidebar — new tabs and modes are added within this function
- **`getDataServiceBaseUrl()`**: Helper for building API URLs — reuse for knowledge endpoint calls
- **`fetchExistingRules()`**: Pattern for loading data from data-service — follow for any knowledge data fetching
- **Nginx proxy**: `/data-service/` proxy already routes to FastAPI — knowledge endpoints auto-available at `/data-service/knowledge/*`

</code_context>

<specifics>
## Specific Ideas

- Tab naming is user-specified: "DesignRules" (not "Validation") and "Specs&Notes" (not "Project Knowledge")
- Tab style must match the existing Rules Prompt / Cypher Expression toggle — no new visual patterns
- Insert Knowledge sub-tabs also follow the same toggle pattern ("From Folder" / "From Prompt")
- Folder path input should include a placeholder showing expected format and a tooltip about Docker-accessible paths

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope.

</deferred>

---

*Phase: 05-ui-mode-restructuring-insert-and-query-panels*
*Context gathered: 2026-04-07*
