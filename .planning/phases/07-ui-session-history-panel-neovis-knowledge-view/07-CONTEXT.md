# Phase 7: UI Session History Panel + NeoVis Knowledge View - Context

**Gathered:** 2026-04-08
**Status:** Ready for planning

<domain>
## Phase Boundary

Add a browsable session history panel to the Specs&Notes sidebar and ensure KnowledgeGraph nodes are visually distinct in the graph viewer. Architects can browse past knowledge interactions (insert, query, update), filter by mode, expand entries to see details, and restore a previous session's state into the current UI. NeoVis configuration for KnowledgeGraph nodes is already built — this phase wires the Graph View behavior and verifies the visual distinction.

</domain>

<decisions>
## Implementation Decisions

### Session History Placement
- **D-01:** Session History is an always-visible collapsible panel at the bottom of the Specs&Notes sidebar — visible regardless of which knowledge mode (insert/query/update) is active
- **D-02:** The panel is collapsed by default, showing a header bar with "Session History" label and a count badge (e.g., "Session History (12)")
- **D-03:** Session History is NOT a 4th mode in KNOWLEDGE_OPTIONS — it stays outside the mode dropdown as a persistent section

### Session List Layout & Detail
- **D-04:** Compact rows with expand-on-click — each row shows a colored mode badge (chip), truncated prompt text, and relative date ("2h ago")
- **D-05:** Clicking a row expands it inline (accordion style) showing full prompt, full result text, and timestamp; pushes other entries down; collapse button to close
- **D-06:** Each session entry has a small "Restore" button visible in the compact row (not just in expanded view)

### Restore Behavior
- **D-07:** Restore performs a full state restoration — sets the prompt textarea to the session's prompt, the response area to the session's result, and switches the knowledge mode dropdown to match the session's mode (insert/query/update)
- **D-08:** Restore is a non-destructive read from stored session data — it does not re-execute the query or trigger any backend calls

### Mode Filter
- **D-09:** A small dropdown next to the "Session History" label in the collapsible header bar, showing "All modes ▼" / "Insert" / "Query" / "Update"
- **D-10:** Default filter state is "All modes" — shows all sessions regardless of type
- **D-11:** Filtering is client-side — all sessions are fetched once, then filtered in memory by mode

### KnowledgeGraph View Toggle
- **D-12:** Keep current auto-switch behavior — switching to Specs&Notes tab automatically renders KnowledgeGraph. No explicit "KnowledgeGraph" option added to the Graph View dropdown
- **D-13:** Graph View dropdown remains 2-option (OntoGraph / MetaGraph) and only visible in DesignRules tab (per Phase 5 D-07)
- **D-14:** NeoVis colors for KnowledgeNote (teal #4ecdc4), KnowledgeTag (yellow #ffe66d), KnowledgeSession (purple #a78bfa), KnowledgeClass (pink #f472b6) are already configured in `config.template.js` — no changes needed, just verification

### Claude's Discretion
- Exact CSS for collapsible panel header (height, background, border, expand/collapse icon)
- Mode badge chip colors per mode type (insert/query/update)
- Relative date formatting approach (built-in vs small utility function)
- Maximum number of sessions to display (pagination vs "load more" vs show all)
- Restore button styling and positioning within compact rows
- Accordion expand/collapse animation (if any)

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Main UI (primary modification target)
- `graph-viewer/index.html` — Single-file React 18 SPA; `KNOWLEDGE_OPTIONS` at line 976, `GraphViewerPage` at line 1351, Specs&Notes tab content at line 2770+, `activeTab` state at line 1408
- `graph-viewer/index.html` lines 2770-2779 — Auto-switch to KnowledgeGraph Cypher when Specs&Notes tab is active (reference for D-12)
- `graph-viewer/index.html` lines 2896-2907 — DesignRules / Specs&Notes tab toggle pattern

### NeoVis configuration (already built — verify only)
- `graph-viewer/config.template.js` lines 51-54 — KnowledgeNote, KnowledgeTag, KnowledgeSession, KnowledgeClass visGroup colors
- `graph-viewer/config.template.js` lines 29-32 — Knowledge node label configuration

### Backend endpoint (already built)
- `data-service/app.py` lines 1186-1195 — `GET /knowledge/sessions/{project}` returns `{project, sessions: [{sessionId, mode, prompt, result, createdAt}]}`

### Upstream phase context
- `.planning/phases/05-ui-mode-restructuring-insert-and-query-panels/05-CONTEXT.md` — D-01 through D-07 define tab structure, mode dropdown, and Graph View visibility rules
- `.planning/phases/06-ui-update-panel-inline-diff-editor/06-CONTEXT.md` — D-01 (vertical list pattern), D-13 (step indicators pattern)

### Requirements
- `.planning/REQUIREMENTS.md` — UIST-06, HSTY-02, HSTY-03, INFR-04

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- **Mode badge pattern**: Phase 6's candidate list uses chips/badges — reuse for session mode indicators
- **Collapsible panel**: No existing collapsible section in sidebar — new pattern, but simple CSS + useState toggle
- **`getDataServiceBaseUrl()`**: Helper for API calls — use for `GET /knowledge/sessions/{project}`
- **`buildCypher("KnowledgeGraph")`**: Already implemented at line 1358 — returns correct Cypher for knowledge nodes
- **Tab toggle CSS**: `.prompt-tab` / `.prompt-tab.active` classes — reuse naming for collapsible header styling consistency

### Established Patterns
- **React.createElement (no JSX)**: All UI follows `const e = React.createElement` — session history panel must follow same pattern
- **State via hooks**: `useState` for collapsed/expanded, session list, filter, expanded entry ID
- **Fetch pattern**: `try/catch` around `fetch()` with error state — same for session list fetching
- **Auto-refresh via useEffect**: Existing `useEffect` for tab switch (line 2770) — add session fetch on Specs&Notes mount

### Integration Points
- **Specs&Notes tab content area**: New session panel goes below the existing mode-specific panel content (insert/query/update panels)
- **`knowledgeMode` state**: Restore action needs to call `setKnowledgeMode()` to switch modes
- **`knowledgePromptText` / `knowledgeResponseText`**: Restore fills these existing state variables
- **Nginx proxy**: `/data-service/` already routes — sessions endpoint is auto-available

</code_context>

<specifics>
## Specific Ideas

- Restore button is a key UX feature — must be visible in the compact row, not hidden inside the expanded accordion
- "Session History (12)" count badge in the collapsed header gives users immediate awareness of interaction history without expanding
- Dropdown filter chosen over chips for minimal space usage in the collapsible header bar

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope.

</deferred>

---

*Phase: 07-ui-session-history-panel-neovis-knowledge-view*
*Context gathered: 2026-04-08*
