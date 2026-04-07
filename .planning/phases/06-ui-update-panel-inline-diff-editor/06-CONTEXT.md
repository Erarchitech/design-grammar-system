# Phase 6: UI Update Panel + Inline Diff Editor - Context

**Gathered:** 2026-04-07
**Status:** Ready for planning

<domain>
## Phase Boundary

Add "Update Knowledge" mode to the Specs&Notes tab in the Graph Viewer sidebar. Architects can describe what to change, see a selectable list of matching notes, review a GitHub-style colored diff, edit the proposed text in a textarea, and confirm the write. The three backend endpoints (match, propose, confirm) are already built in Phase 4 — this phase wires the UI to them.

</domain>

<decisions>
## Implementation Decisions

### Candidate List & Selection
- **D-01:** Candidate notes displayed as a vertical checkbox list — each row shows a checkbox, note title, and relevance score badge
- **D-02:** Title only in the candidate list — no content preview (content shown after Propose step)
- **D-03:** "Select all / Deselect all" toggle link above the checkbox list
- **D-04:** Empty state when no candidates match: inline message in the list area ("No matching notes found. Try a different description.")

### Diff + Editor Layout
- **D-05:** Stacked layout — diff preview panel above, editable textarea below. Fits the narrow sidebar and matches existing vertical layout patterns (Response + Cypher panels)
- **D-06:** Diff styling is GitHub-style red/green — deletions with red background, additions with green background. Note: this overrides the success criteria's "red strikethrough + red bold" wording; the CSS classes on the backend-generated `diffHtml` spans will be styled with red/green backgrounds instead
- **D-07:** Diff panel is collapsible — small "Show diff" / "Hide diff" toggle. Saves vertical space once the user is confident in their edits
- **D-08:** Textarea pre-populated with the LLM's proposed text (not the original). User edits from the proposed version. Matches Phase 4 D-09 (client sends final edited text)

### Multi-Note Editing Flow
- **D-09:** Sequential review — after Propose, show one note at a time with "Next note" / "Previous note" navigation buttons
- **D-10:** "Skip this note" button available per note — skipped notes are excluded from the final Confirm batch
- **D-11:** Summary view before final Confirm — shows list of note titles with "changed" / "skipped" status badges. Confirm button below the summary
- **D-12:** Batch confirm — single "Confirm All" button sends all non-skipped edited notes to the backend in one API call

### Propose Step Waiting UX
- **D-13:** Step indicators reused from Phase 5 pattern with update-specific labels: "Fetching note content...", "Generating edits...", "Computing diff...". Progress bar fills as steps complete
- **D-14:** During the wait, the candidate list stays visible but dimmed/disabled. Step indicators appear below. When complete, the view transitions to the diff+editor view
- **D-15:** Inline success notification after Confirm — green message in the Response area listing updated note titles ("Updated: [Title 1], [Title 2]"). Panel resets to prompt input
- **D-16:** "Back to search" button at the top of the diff/editor view — lets users abandon the current edit and return to the prompt input for a new Match query

### Claude's Discretion
- Exact CSS for red/green diff backgrounds (specific hex values, border radius, padding)
- Step indicator label wording refinements
- Textarea dimensions and auto-resize behavior
- Navigation button styling and positioning
- Summary view layout details
- How to handle the case where the LLM proposes no changes (hasChanges: false)
- Whether to show the note title as a header above each diff+editor view

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Main UI (primary modification target)
- `graph-viewer/index.html` — Single-file React 18 SPA (~3106 lines); `KNOWLEDGE_OPTIONS` at line 948, Specs&Notes tab content starts at line 2838, existing mode dropdown and panel patterns
- `graph-viewer/index.html` lines 2876-2886 — Insert Knowledge tab toggle pattern (reference for sub-panel UI patterns)
- `graph-viewer/index.html` lines 2698-2708 — Top-level DesignRules / Specs&Notes tab toggle (reference for tab styling)

### Backend endpoints (already built — Phase 4)
- `data-service/app.py` lines 1200-1212 — `POST /knowledge/update/match` returns `{candidates: [{noteId, title, score}]}`
- `data-service/app.py` lines 1215-1247 — `POST /knowledge/update/propose` returns `{diffs: [{noteId, title, originalContent, proposedContent, diffHtml, hasChanges, updatedAt}]}`
- `data-service/app.py` lines 1250-1294 — `POST /knowledge/update/confirm` accepts `{notes: [{noteId, content, updatedAt}], project, prompt}` with optimistic locking

### Upstream phase context
- `.planning/phases/04-update-flow-endpoints/04-CONTEXT.md` — D-04 through D-12 define the backend contract (diff computation, optimistic locking, n8n routing, session tracking)
- `.planning/phases/05-ui-mode-restructuring-insert-and-query-panels/05-CONTEXT.md` — D-01 through D-15 define the sidebar tab structure, state management, and async polling patterns this phase extends

### Proxy routing
- `graph-viewer/nginx.conf` — `/data-service/` proxy already routes to FastAPI; update endpoints auto-available at `/data-service/knowledge/update/*`

### Requirements
- `.planning/REQUIREMENTS.md` — UIST-04 (Update Knowledge mode UI)

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- **Tab toggle pattern**: `.prompt-tab` / `.prompt-tab.active` CSS classes and click handler — reuse for any sub-navigation within the Update panel
- **Mode dropdown**: `KNOWLEDGE_OPTIONS` array at line 948 — needs "update" option added (`{ value: "update", label: "Update Knowledge" }`)
- **Step indicators**: Existing `steps` array + step display logic + progress bar — reuse with update-specific step labels
- **Response textarea**: Existing pattern for displaying results — reuse for success notification after Confirm
- **`getDataServiceBaseUrl()`**: Helper for building API URLs — use for all three update endpoint calls

### Established Patterns
- **React.createElement (no JSX)**: All UI via `const e = React.createElement` — Update panel follows same pattern
- **State via hooks**: `useState` for panel state (candidates, selected notes, current note index, diff data, editor content)
- **Fetch + error handling**: `try/catch` around `fetch` calls with `setError()` — same for Match/Propose/Confirm calls
- **Async polling**: `startPollingResult()` for Propose step if routed through execution-result (or direct fetch if synchronous)

### Integration Points
- **`GraphViewerPage` function**: The Specs&Notes tab content (line 2838+) — Update Knowledge mode panel goes here alongside Insert and Query
- **`KNOWLEDGE_OPTIONS` array**: Add "update" mode option
- **Nginx proxy**: `/data-service/` proxy routes — update endpoints are already reachable

</code_context>

<specifics>
## Specific Ideas

- Diff styling explicitly chosen as GitHub-style red/green (not the red-only approach from the original spec text) — this is a deliberate user preference override
- Select all/deselect all toggle was specifically requested despite the small candidate list size

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope.

</deferred>

---

*Phase: 06-ui-update-panel-inline-diff-editor*
*Context gathered: 2026-04-07*
