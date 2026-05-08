# Phase 5: UI Mode Restructuring + Insert and Query Panels - Research

**Researched:** 2026-04-07
**Domain:** Single-file React 18 SPA modification (no build step) — sidebar restructuring, state management, async polling integration
**Confidence:** HIGH

---

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

- **D-01:** Two top-level tabs ("DesignRules" / "Specs&Notes") appear at the top of the sidebar, beneath the Project back button — tabs switch the entire sidebar content area
- **D-02:** Existing modes renamed: "Validation" section becomes "DesignRules" tab; new "Project Knowledge" section becomes "Specs&Notes" tab
- **D-03:** Within each tab, modes use the existing dropdown pattern — current `MODE_OPTIONS` dropdown stays for DesignRules (Insert Rules, Query Rules, Edit Rules), a new dropdown appears for Specs&Notes (Insert Knowledge, Query Knowledge)
- **D-04:** Tab styling matches existing `.prompt-tab` / `.prompt-tab.active` CSS classes (the Rules Prompt / Cypher Expression toggle pattern)
- **D-05:** No "new" badge or indicator on the Specs&Notes tab — treat as a normal UI element
- **D-06:** When switching between DesignRules and Specs&Notes tabs, all state persists — prompt text, response text, graph view, etc. are kept per-tab (not cleared)
- **D-07:** Graph View dropdown (OntoGraph / MetaGraph) is only visible when DesignRules tab is active — hidden in Specs&Notes modes (until Phase 7 adds KnowledgeGraph view)
- **D-08:** Two sub-tabs within the Insert Knowledge mode: "From Folder" and "From Prompt" — tab toggle pattern within the panel, similar to the existing Rules Prompt / Cypher Expression toggle
- **D-09:** "From Folder" shows a text input with placeholder hint (e.g., `/repo/docs`) and a help tooltip explaining which paths are accessible via Docker mount
- **D-10:** "From Prompt" shows a textarea for natural language input (same style as existing prompt textarea)
- **D-11:** Both sub-modes show results in the Response textarea with inline success messages: "Imported 12 notes" for folder, "Created note: [title]" for prompt
- **D-12:** Query Knowledge mode layout mirrors existing Query Rules — prompt textarea, submit button, Response textarea, and Cypher panel
- **D-13:** Uses workflow key `knowledge-query` with the existing `startPollingResult` async polling pattern
- **D-14:** Knowledge operations reuse the existing step indicator + progress bar pattern with knowledge-specific step labels
- **D-15:** Errors display in the Response textarea with the same styling as Rules errors

### Claude's Discretion

- Exact step labels for knowledge insert and query operations
- CSS for the top-level tab bar (dimensions, spacing) — must match `.prompt-tab` style
- State variable naming and React component refactoring approach
- How to handle the "Clear the Graph" button visibility in Specs&Notes modes
- Whether to refactor `GraphViewerPage` into sub-components or keep as one function

### Deferred Ideas (OUT OF SCOPE)

None — discussion stayed within phase scope.

</user_constraints>

---

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| UIST-01 | Existing modes (Insert Rules, Query Rules, Edit Rules) are grouped under a "DesignRules" section in the sidebar | Covered by D-01–D-03: `MODE_OPTIONS` array stays, wrapped in DesignRules tab |
| UIST-02 | New "Specs&Notes" section appears in the sidebar with Insert Knowledge and Query Knowledge modes | Covered by D-01–D-03: new `KNOWLEDGE_OPTIONS` array + second dropdown, both inside Specs&Notes tab |
| UIST-03 | Insert Knowledge mode shows a folder path input field and a prompt input field | Covered by D-08–D-11: two sub-tabs within Insert Knowledge panel |
| UIST-05 | Query Knowledge mode shows a prompt field and a Response display area | Covered by D-12–D-13: mirrors Query Rules layout with `knowledge-query` workflow key |

</phase_requirements>

---

## Summary

Phase 5 is a pure front-end change — no new backend endpoints, no Docker changes, no new libraries. The single modification target is `graph-viewer/index.html` (2575 lines, single-file React 18 SPA using `React.createElement`, no JSX, no build step). All backend infrastructure required by the new panels was built in Phases 2–3: folder ingest endpoint (`POST /knowledge/ingest/folder`), LLM knowledge insert via n8n webhook (`/webhook/dg/knowledge-ingest` with workflow key `knowledge-ingest`), and LLM knowledge query via n8n webhook (`/webhook/dg/knowledge-query` with workflow key `knowledge-query`). The execution-result polling endpoints already in use for Rules modes are reused as-is for Knowledge modes.

The implementation adds a top-level tab state variable (`activeTab: "design-rules" | "specs-notes"`) to `GraphViewerPage`, a parallel set of knowledge-specific state variables (scoped to Specs&Notes interactions), a `KNOWLEDGE_OPTIONS` array mirroring `MODE_OPTIONS`, and three new panel rendering branches: Insert Knowledge (with its own sub-tab state), Query Knowledge, and a second mode dropdown for the Specs&Notes tab. All new UI must follow the `React.createElement` pattern — no JSX. The existing `.prompt-tab` / `.prompt-tab.active` CSS is reused for both the top-level tabs and the Insert Knowledge sub-tabs; no new CSS classes are strictly required.

The highest-risk area is state management: `GraphViewerPage` currently has a single flat set of state variables shared across all three modes. Adding Specs&Notes modes without cross-contaminating existing DesignRules state requires careful scoping. Per D-06, state persists across tab switches, meaning both tab contexts must live simultaneously in the component, not be conditionally reset.

**Primary recommendation:** Add `activeTab` state at the top of `GraphViewerPage`, add knowledge-specific state variables alongside (not replacing) existing ones, define `KNOWLEDGE_OPTIONS` adjacent to `MODE_OPTIONS`, and render the sidebar content conditionally on `activeTab`. Keep the component as one function — sub-component extraction is discretionary and not required for correctness.

---

## Standard Stack

### Core

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| React 18 | CDN (already loaded) | UI rendering | Project constraint — already in use |
| React.createElement | — | JSX replacement | Project constraint — no build step for main SPA |

**No new libraries required.** [VERIFIED: codebase inspection of `graph-viewer/index.html` lines 1–10 — React 18 loaded from CDN, no package.json at root]

### Installation

No installation step. All changes are edits to `graph-viewer/index.html`. After editing, run:

```bash
docker compose build --no-cache design-grammars && docker compose up -d design-grammars
```

(`--no-cache` is mandatory; Docker layer caching will serve the stale file otherwise.) [VERIFIED: CLAUDE.md "Known Gotchas"]

---

## Architecture Patterns

### Existing Sidebar Layout (lines 2316–2483)

The `GraphViewerPage` render function builds the left sidebar (`#left` div) in this order:

1. `gv-nav` — back button + project name
2. `h3` — "Grammar Viewer" title
3. `label` + `modeControl` — mode dropdown (built from `MODE_OPTIONS`)
4. Conditional edit-mode rule selector
5. Graph View select
6. Prompt tabs + textarea + action button
7. "Clear the Graph" danger button
8. Progress bar
9. Step indicators
10. Response textarea
11. Workflow Cypher textarea
12. Cypher Query input (query mode only)
13. Neo4j URI hint + status

[VERIFIED: codebase inspection of `graph-viewer/index.html` lines 2316–2483]

### Target Sidebar Layout After Phase 5

```
#left
├── gv-nav (unchanged)
├── h3 "Grammar Viewer" (unchanged)
├── [TOP-LEVEL TAB BAR]           ← NEW: "DesignRules" | "Specs&Notes"
│
│── if activeTab === "design-rules":
│     ├── label "Mode"
│     ├── modeControl (existing MODE_OPTIONS dropdown)
│     ├── edit-mode rule selector (conditional, unchanged)
│     ├── Graph View select (unchanged, D-07: shown only here)
│     ├── prompt tabs (Rules Prompt / Cypher Expression, unchanged)
│     ├── textarea + action button
│     ├── "Clear the Graph" button
│     ├── progress + steps + response + cypher
│     └── hint + status
│
└── if activeTab === "specs-notes":
      ├── label "Mode"
      ├── knowledgeModeControl (NEW: knowledge dropdown)
      │
      │── if knowledgeMode === "insert":
      │     ├── insert sub-tab bar (From Folder | From Prompt)
      │     ├── if insertTab === "folder": text input + Submit button
      │     ├── if insertTab === "prompt": textarea + Submit button
      │     ├── progress + steps + response textarea
      │     └── status
      │
      └── if knowledgeMode === "query":
            ├── textarea (NL question)
            ├── "Query Knowledge" button
            ├── progress + steps
            ├── Response textarea
            ├── Workflow Cypher textarea
            └── status
```

### Pattern 1: Top-Level Tab Bar (new, reusing existing CSS)

**What:** Two-button tab bar immediately below the `gv-nav`, switching `activeTab` state.

**CSS reused:** `.prompt-tabs` (grid container) and `.prompt-tab` / `.prompt-tab.active` classes — identical pattern to the Rules Prompt / Cypher Expression toggle at lines 2394–2406.

**Example (React.createElement):**
```javascript
// Source: pattern derived from graph-viewer/index.html lines 2394-2406
const [activeTab, setActiveTab] = React.useState("design-rules");

const topTabBar = e("div", { className: "prompt-tabs" },
  e("button", {
    type: "button",
    className: activeTab === "design-rules" ? "prompt-tab active" : "prompt-tab",
    onClick: () => setActiveTab("design-rules")
  }, "DesignRules"),
  e("button", {
    type: "button",
    className: activeTab === "specs-notes" ? "prompt-tab active" : "prompt-tab",
    onClick: () => setActiveTab("specs-notes")
  }, "Specs\u0026Notes")
);
```

Note: Place the tab bar after `gv-nav` and `h3`, before mode control. The `&` in "Specs&Notes" must be the Unicode escape `\u0026` (or the literal `&`) — do not use HTML entity `&amp;` inside `React.createElement` string arguments.

[VERIFIED: codebase inspection of index.html lines 257–278 for CSS, lines 2394–2406 for usage pattern]

### Pattern 2: Knowledge Mode Options Array + Dropdown

**What:** A `KNOWLEDGE_OPTIONS` array parallel to `MODE_OPTIONS`, plus state variables `knowledgeMode` and `isKnowledgeModeMenuOpen`, plus a `knowledgeModeDropdownRef`. A new `knowledgeModeControl` variable built from the same template as `modeControl`.

```javascript
// Source: pattern derived from index.html lines 942-946
const KNOWLEDGE_OPTIONS = [
  { value: "insert", label: "Insert Knowledge" },
  { value: "query", label: "Query Knowledge" }
];

// New state (alongside existing state variables)
const [knowledgeMode, setKnowledgeMode] = React.useState("insert");
const [isKnowledgeModeMenuOpen, setIsKnowledgeModeMenuOpen] = React.useState(false);
const knowledgeModeDropdownRef = React.useRef(null);
```

The outside-click handler pattern (lines 1431–1440) must be replicated for `knowledgeModeDropdownRef`.

[VERIFIED: codebase inspection of index.html lines 942–946, 1431–1440, 2281–2314]

### Pattern 3: Insert Knowledge Panel

**What:** An `insertTab` state variable (`"folder"` | `"prompt"`) drives a sub-tab bar (From Folder / From Prompt) rendered using `.prompt-tabs` / `.prompt-tab` — the same CSS class pair used by the top-level tabs and the Rules Prompt toggle.

**From Folder sub-panel:**
- `text` input (not textarea) with `placeholder="/repo/docs"` and a `.hint` below explaining Docker-mounted paths
- The mounted root is `.:/mnt/repo:ro` — so a path like `DG_OBSIDIAN` resolves to `/mnt/repo/DG_OBSIDIAN` inside the container; the UI tooltip should convey this
- Submit calls `POST /data-service/knowledge/ingest/folder` with `{project, path}`
- On success: `setKnowledgeResponseText("Imported " + data.inserted + " notes")`

**From Prompt sub-panel:**
- Textarea (same `.prompt-input` class) for NL input
- Submit POSTs to n8n webhook `/n8n/webhook/dg/knowledge-ingest` with `{prompt, project}`
- Polls via `startPollingLatest("knowledge-ingest", "knowledge-ingest")`
- On completion: reads `payload.title` from execution result; sets `"Created note: " + payload.title`

[VERIFIED: codebase inspection — folder endpoint at app.py line 1010, polling pattern at index.html lines 1615–1676, docker-compose.yml line 36 for volume mount]

### Pattern 4: Query Knowledge Panel

**What:** Mirrors the existing "Query Rules" mode layout almost exactly. Reuses the same `startPollingLatest` call with workflow key `knowledge-query`. The `responseCypher` field shows the full-text search Cypher (per Phase 3 D-06).

```javascript
// Source: pattern derived from index.html lines 2063-2179, Phase 3 CONTEXT D-08/D-09
const requestKnowledge = async () => {
  // Same guard pattern as requestGrammar()
  const headers = { "Content-Type": "application/json" };
  if (cfg.n8nUser && cfg.n8nPassword) {
    headers["Authorization"] = "Basic " + btoa(`${cfg.n8nUser}:${cfg.n8nPassword}`);
  }
  const res = await fetch("/n8n/webhook/dg/knowledge-query", {
    method: "POST",
    headers,
    body: JSON.stringify({ prompt: knowledgeQueryText, project: project || "default-project" })
  });
  // ... accepted/polling branch same as requestGrammar
  startPollingLatest("knowledge-query", "query");
};
```

[VERIFIED: Phase 3 CONTEXT.md D-08/D-09, index.html lines 2063–2179]

### Pattern 5: Polling Completion Handler for Knowledge Modes

The existing `startPollingResult` and `startPollingLatest` use a `modeType` string to decide what to extract from `payload`:

```javascript
// Source: index.html lines 1568-1590
if (modeType === "query") {
  setResponseText(payload.answer || payload.response || "");
  setResponseCypher(payload.cypher || "");
}
```

Knowledge modes must route their responses to knowledge-specific state variables (not `responseText` / `responseCypher`) to avoid cross-contaminating DesignRules state. Two approaches:

**Option A (recommended):** Define separate `knowledgeResponseText`, `knowledgeResponseCypher` state variables. Pass different setter callbacks into new knowledge-specific polling functions, or use a new `modeType` value (e.g., `"knowledge-query"`, `"knowledge-ingest"`) with an extended branch.

**Option B:** Reuse `responseText`/`responseCypher` but reset on tab switch — violates D-06 (state must persist across tab switches).

Per D-06, Option A is mandatory. The simplest implementation: define `knowledgeResponseText` and `knowledgeResponseCypher` state variables and write thin wrappers `startKnowledgePollingLatest(workflowKey, modeType)` that call the shared polling infrastructure but set knowledge state variables.

[VERIFIED: D-06 from CONTEXT.md; index.html lines 1554–1677 for polling code]

### Anti-Patterns to Avoid

- **Sharing state variables between tabs:** `responseText`, `responseCypher`, `promptText`, `isRunning`, `progress`, `step`, `stepTimes` are currently shared across all three DesignRules modes. If they are also shared with Specs&Notes modes, switching tabs will wipe in-progress or completed results — violating D-06.
- **JSX syntax:** The entire file uses `React.createElement` (aliased as `e`). Adding any JSX will cause a parse error in the browser with no build step.
- **Forgetting `--no-cache`:** Docker layer caching will serve the old `index.html` — always rebuild with `docker compose build --no-cache design-grammars`.
- **Browser cache:** Hard-refresh (Ctrl+Shift+R) required after any `index.html` change during development.
- **HTML entities in `React.createElement` strings:** `&amp;` is not decoded inside string arguments. Use literal `&` or `\u0026`.

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Async polling | Custom polling loop | `startPollingLatest("knowledge-ingest" / "knowledge-query", ...)` | Already handles timeout, error, step, progress — 63 lines of edge-case handling |
| Folder path API call | Custom fetch logic | `POST /data-service/knowledge/ingest/folder` (already built in Phase 2) | INSK-02/INSK-03 already implemented; path traversal validation is server-side |
| Progress / step display | New progress UI | Reuse `.progress` div + `.steps` div + `setWorkflowStep()` / `setProgress()` | Identical pattern to existing modes |
| Tab styling | New CSS classes | `.prompt-tabs` / `.prompt-tab` / `.prompt-tab.active` | Already defined at lines 257–278; exact match to D-04 |
| Mode dropdown | New select element | Replicate `modeControl` pattern with `KNOWLEDGE_OPTIONS` | Consistent UX, ARIA attributes included, outside-click handling already patterned |

---

## Common Pitfalls

### Pitfall 1: Step Array Length Mismatch in `applyProgressUpdate`

**What goes wrong:** `applyProgressUpdate` reads `steps.length` from the closure, but `steps` is currently derived from `mode` (DesignRules modes). If the knowledge step arrays have different lengths, progress bar advances will misfire.

**Why it happens:** `steps` is `mode === "query" ? querySteps : ingestSteps` — a closed-over derived value. Knowledge modes need their own step arrays.

**How to avoid:** Define `knowledgeInsertSteps` and `knowledgeQuerySteps` arrays. Write a `knowledgeSteps` derived variable analogous to `steps`. Pass the correct `steps` array to any polling wrapper that calls `applyProgressUpdate`, or inline a knowledge-specific progress applier.

**Warning signs:** Progress bar jumps to 100% immediately, or step counter never advances past step 1.

[VERIFIED: index.html lines 1373–1387, 1535–1543]

### Pitfall 2: Outside-Click Handler Not Registered for Knowledge Dropdown

**What goes wrong:** The knowledge mode dropdown stays open after clicking elsewhere on the page.

**Why it happens:** The existing `useEffect` for `modeDropdownRef` only covers the DesignRules dropdown. A second ref (`knowledgeModeDropdownRef`) needs its own outside-click handler.

**How to avoid:** Add a second `useEffect` following the same pattern as lines 1431–1440, listening on `knowledgeModeDropdownRef`.

[VERIFIED: index.html lines 1431–1440]

### Pitfall 3: `mode` Reset Effect Clearing Knowledge State

**What goes wrong:** The `useEffect` at lines 1407–1423 fires on `[mode]` changes and resets `responseText`, `responseCypher`, `promptText`, etc. If knowledge operations share those variables, switching DesignRules modes will silently clear knowledge panel output.

**Why it happens:** The reset effect is keyed to `mode`, which only tracks DesignRules modes — but all state variables are shared.

**How to avoid:** Keep knowledge state variables (`knowledgeResponseText`, `knowledgePromptText`, etc.) entirely separate from DesignRules state. The existing `useEffect` on `[mode]` does not touch knowledge-scoped variables.

[VERIFIED: index.html lines 1407–1423]

### Pitfall 4: `isRunning` Guard Blocks Both Tabs Simultaneously

**What goes wrong:** The `isRunning` flag is checked in both `sendRules` and `requestGrammar` before starting a workflow. If `isRunning` is shared, starting a query in Specs&Notes while a DesignRules workflow is running (or vice versa) will be silently blocked.

**Why it happens:** Single `isRunning` boolean shared across all modes.

**How to avoid:** Introduce a `knowledgeIsRunning` state variable for Specs&Notes operations. The DesignRules `isRunning` and knowledge `knowledgeIsRunning` operate independently.

[VERIFIED: index.html lines 1356, 1966, 2069]

### Pitfall 5: "Clear the Graph" Button Visibility in Specs&Notes

**What goes wrong:** The danger button at line 2425 clears the graph (deletes Neo4j nodes). Showing it in Specs&Notes modes is confusing — it still clears Metagraph/OntoGraph, not knowledge nodes.

**Why it happens:** The button is rendered unconditionally in the sidebar.

**How to avoid (per Claude's Discretion):** Recommended — show the button only when `activeTab === "design-rules"`. This avoids architect confusion without changing functionality.

[VERIFIED: index.html line 2425; CONTEXT.md "Claude's Discretion"]

### Pitfall 6: `n8nWebhook` Config Key for Knowledge Webhooks

**What goes wrong:** `sendRules` reads `cfg.n8nWebhook` for the rules-ingest endpoint. A naive copy would point knowledge ingest at the wrong webhook.

**Why it happens:** `config.template.js` defines specific keys per workflow; knowledge webhooks use conventional paths not stored in config.

**How to avoid:** For knowledge webhooks, use the hardcoded conventional paths directly: `/n8n/webhook/dg/knowledge-ingest` and `/n8n/webhook/dg/knowledge-query`. These are already routed through the existing Nginx `/n8n/` proxy.

[VERIFIED: Phase 3 CONTEXT.md D-09; nginx.conf lines 37–48]

---

## Code Examples

### Top-Level Tab Bar (complete)

```javascript
// Source: pattern from index.html lines 2394-2406 (Rules Prompt toggle)
// Place immediately after gv-nav and h3, before "label Mode"
e("div", { className: "prompt-tabs", style: { marginTop: "14px" } },
  e("button", {
    type: "button",
    className: activeTab === "design-rules" ? "prompt-tab active" : "prompt-tab",
    onClick: () => setActiveTab("design-rules")
  }, "DesignRules"),
  e("button", {
    type: "button",
    className: activeTab === "specs-notes" ? "prompt-tab active" : "prompt-tab",
    onClick: () => setActiveTab("specs-notes")
  }, "Specs&Notes")
)
```

### Folder Ingest Fetch (synchronous — no polling needed)

```javascript
// Source: data-service/app.py line 1010 — POST /knowledge/ingest/folder returns immediately
const submitFolderIngest = async () => {
  if (!folderPath.trim()) { setStatus("Path is required"); return; }
  if (knowledgeIsRunning) return;
  setKnowledgeIsRunning(true);
  setKnowledgeResponseText("");
  setStatus("Importing notes...");
  try {
    const base = getDataServiceBaseUrl();
    const res = await fetch(`${base}/knowledge/ingest/folder`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ project: project || "default-project", path: folderPath.trim() })
    });
    const data = await res.json();
    if (!res.ok) {
      setKnowledgeResponseText("Error: " + (data?.detail || res.status));
    } else {
      setKnowledgeResponseText("Imported " + data.inserted + " notes" +
        (data.skipped > 0 ? " (" + data.skipped + " skipped)" : ""));
    }
    setStatus("Done");
  } catch (err) {
    setKnowledgeResponseText("Error: " + err.message);
    setStatus("Failed");
  } finally {
    setKnowledgeIsRunning(false);
  }
};
```

### Knowledge-Specific Step Arrays

```javascript
// Source: pattern from index.html lines 1373-1387
const knowledgeInsertSteps = [
  "Send prompt",
  "Extracting title & tags",
  "Writing to graph",
  "Recording session",
  "Complete"
];
const knowledgeQuerySteps = [
  "Send question",
  "Searching knowledge graph",
  "Generating answer",
  "Recording session",
  "Complete"
];
```

### Docker Path Tooltip Content

```
Accessible paths: any subfolder of the repository root.
Example: "DG_OBSIDIAN" maps to /mnt/repo/DG_OBSIDIAN inside the service.
```

[VERIFIED: docker-compose.yml line 35-36 — `.:/mnt/repo:ro` mount; DG_KNOWLEDGE_REPO_ROOT=/mnt/repo]

---

## State Inventory for `GraphViewerPage`

All state variables that must be added. Existing variables are unchanged.

| Variable | Type | Initial Value | Scope |
|----------|------|--------------|-------|
| `activeTab` | string | `"design-rules"` | Top-level tab selection |
| `knowledgeMode` | string | `"insert"` | Specs&Notes mode dropdown |
| `isKnowledgeModeMenuOpen` | boolean | `false` | Specs&Notes dropdown open state |
| `insertTab` | string | `"folder"` | Insert Knowledge sub-tab |
| `folderPath` | string | `""` | Folder path input value |
| `knowledgePromptText` | string | `""` | Insert From Prompt / Query textarea |
| `knowledgeResponseText` | string | `""` | Specs&Notes response display |
| `knowledgeResponseCypher` | string | `""` | Query Knowledge cypher display |
| `knowledgeIsRunning` | boolean | `false` | Specs&Notes in-flight guard |
| `knowledgeProgress` | number | `0` | Progress bar for knowledge ops |
| `knowledgeStep` | number | `0` | Step indicator for knowledge ops |
| `knowledgeStepTimes` | array | `[]` | Per-step elapsed times |
| `knowledgeStatus` | string | `"Ready"` | Status line for Specs&Notes |

Refs needed:
- `knowledgeModeDropdownRef` — for outside-click handler
- `knowledgeStepRef` — mirrors `stepRef` for knowledge polling
- `knowledgeStepStartedAtRef` — mirrors `stepStartedAtRef`
- `knowledgePollRef` — mirrors `pollRef` for cleanup

[VERIFIED: derived from index.html lines 1347–1371 (existing state) and CONTEXT.md D-06]

---

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| Node.js | `--no-cache` build step | ✓ | v20.20.0 | — |
| Docker | Container rebuild | ✓ | 29.1.3 | — |
| data-service `/knowledge/ingest/folder` | Insert Knowledge (Folder) | Built in Phase 2 | — | — |
| n8n workflow `knowledge-ingest` | Insert Knowledge (Prompt) | Built in Phase 3 | — | — |
| n8n workflow `knowledge-query` | Query Knowledge | Built in Phase 3 | — | — |
| execution-result polling endpoints | All knowledge async ops | ✓ (app.py lines 969–1004) | — | — |

**Note:** The n8n workflows `knowledge-ingest` and `knowledge-query` are outputs of Phase 3, which is listed as a dependency of Phase 5. If Phase 3 is not yet executed, the Specs&Notes polling will receive `{"status": "unknown"}` from the execution-result endpoint — the UI handles this gracefully (shows "Workflow running..." indefinitely). The UI code itself does not depend on Phase 3 being complete.

[VERIFIED: docker-compose.yml; data-service/app.py lines 969–1004; Phase 3 CONTEXT.md D-07/D-08]

---

## Validation Architecture

`nyquist_validation` is absent from `.planning/config.json` — treated as enabled.

### Test Framework

| Property | Value |
|----------|-------|
| Framework | Python requests (integration tests, no pytest.ini — scripts in `test/`) |
| Config file | None — standalone scripts |
| Quick run command | `python test/test_phase05_ui_smoke.py` (Wave 0 gap — does not yet exist) |
| Full suite command | `python test/test_phase05_ui_smoke.py` |

The existing test pattern (see `test/test_knowledge_crud.py`) is HTTP integration tests against the running data-service. Phase 5 is purely front-end, so the most meaningful tests are either:
1. **Smoke tests via HTTP** — verify the Docker container serves the updated `index.html` with expected strings (tab labels, new CSS classes)
2. **Manual browser verification** — functional test of tab switching, form submission, polling UX

### Phase Requirements → Test Map

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| UIST-01 | Sidebar contains "DesignRules" tab label | smoke (curl/grep) | `python test/test_phase05_ui_smoke.py::test_design_rules_tab` | ❌ Wave 0 |
| UIST-02 | Sidebar contains "Specs&Notes" tab label | smoke (curl/grep) | `python test/test_phase05_ui_smoke.py::test_specs_notes_tab` | ❌ Wave 0 |
| UIST-03 | Insert Knowledge folder path input and prompt input present in HTML | smoke (curl/grep) | `python test/test_phase05_ui_smoke.py::test_insert_knowledge_ui` | ❌ Wave 0 |
| UIST-05 | Query Knowledge prompt and response area present in HTML | smoke (curl/grep) | `python test/test_phase05_ui_smoke.py::test_query_knowledge_ui` | ❌ Wave 0 |

Note: Pure UI state tests (tab switching behavior, polling UX) are manual-only — they require a running browser and cannot be asserted via HTTP response body inspection.

### Sampling Rate

- **Per task commit:** `python test/test_phase05_ui_smoke.py` (if service is running)
- **Per wave merge:** Same smoke test
- **Phase gate:** Full smoke test green + manual browser walkthrough before `/gsd-verify-work`

### Wave 0 Gaps

- [ ] `test/test_phase05_ui_smoke.py` — HTTP smoke test fetching `http://localhost:8080/` and asserting presence of "DesignRules", "Specs&Notes", folder path input placeholder, and Query Knowledge panel identifiers
- [ ] Framework install: `pip install requests` — already available from existing test scripts

---

## Security Domain

This phase has no new authentication surfaces, no new API endpoints, and no user-supplied data sent to Neo4j directly. All inputs from the Specs&Notes panel are forwarded to:
1. `POST /knowledge/ingest/folder` — path traversal validated server-side (INSK-03, already implemented in Phase 2 via `validate_ingest_path`)
2. n8n webhooks — forwarded to Ollama, not directly to Neo4j

| ASVS Category | Applies | Standard Control |
|---------------|---------|-----------------|
| V2 Authentication | No | — |
| V3 Session Management | No | — |
| V4 Access Control | No | — |
| V5 Input Validation | Yes (folder path) | Server-side in data-service (already implemented) — UI adds non-empty check only |
| V6 Cryptography | No | — |

No new security concerns introduced by this phase beyond those already addressed in Phase 2.

[VERIFIED: data-service/app.py line 1011 `validate_ingest_path(payload.path)`]

---

## Project Constraints (from CLAUDE.md)

| Constraint | Applies to Phase 5 |
|-----------|-------------------|
| No JSX build for main UI — all React via `React.createElement` | Yes — all new UI must use `e(...)` pattern |
| Single-file architecture — everything in `index.html` | Yes — new components are functions in the same file |
| CSS custom properties via `:root` variables | Yes — use `var(--accent)`, `var(--muted)`, etc. |
| Docker `--no-cache` required after HTML changes | Yes — mandatory rebuild command |
| Hard-refresh (Ctrl+Shift+R) after changes during dev | Yes — must clear browser cache |
| No new Docker services | Confirmed — Phase 5 is UI-only |
| Fonts: Inter (body), Space Grotesk (headings) | Use existing font classes; no new imports |

---

## Open Questions

1. **Knowledge polling completion handler scope**
   - What we know: `startPollingLatest` sets `responseText`/`responseCypher` (DesignRules state)
   - What's unclear: Whether to write a thin wrapper that redirects to `knowledgeResponseText`/`knowledgeResponseCypher`, or extend the `modeType` branch logic inside the existing polling function
   - Recommendation: Write a self-contained `startKnowledgePollingLatest` function that calls the same `fetch` loop but calls knowledge setters — avoids modifying a shared, working function

2. **Insert From Prompt polling completion payload**
   - What we know: Phase 3 D-11 says result is `{noteId, title, tags}` for insert
   - What's unclear: Whether the n8n workflow has been authored yet (Phase 3 is not yet executed) — the exact payload key name (`title` vs `note_title`) is unconfirmed
   - Recommendation: Code against `payload.title` (as stated in D-11), with a fallback to `payload.note_title || payload.noteId || "unknown"`

---

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | n8n workflows `knowledge-ingest` and `knowledge-query` post `{status, payload, step, progress, workflow}` to `/execution-result` using workflow keys exactly as specified in Phase 3 D-08 | Architecture Patterns (Pattern 4), Pitfall 6 | Polling will never complete; response will stay `{status: "unknown"}` — detected at first browser test |
| A2 | Insert completion payload key for the note title is `payload.title` | Code Examples (Folder Ingest), Open Questions | Success message shows blank — fallback chain mitigates |
| A3 | The "Clear the Graph" button should be hidden in Specs&Notes — no explicit decision in CONTEXT.md | Pitfall 5 | If user expects to see it in Specs&Notes, recommendation differs from implementation |

**Note:** A3 is explicitly listed as Claude's Discretion in CONTEXT.md — the recommendation to hide it is based on UX reasoning, not a locked decision.

---

## Sources

### Primary (HIGH confidence)

- `graph-viewer/index.html` (verified lines 1–2575) — full sidebar layout, CSS classes, state variables, polling patterns, mode dropdown implementation
- `data-service/app.py` (verified lines 969–1070) — execution-result endpoints, folder ingest endpoint
- `graph-viewer/nginx.conf` (verified) — proxy routing for `/data-service/` and `/n8n/`
- `docker-compose.yml` (verified lines 32–36) — `DG_KNOWLEDGE_REPO_ROOT=/mnt/repo`, `.:/mnt/repo:ro` volume mount
- `.planning/milestones/v1.1-phases/05-ui-mode-restructuring-insert-and-query-panels/05-CONTEXT.md` (verified) — all locked decisions
- `.planning/milestones/v1.1-phases/03-n8n-knowledge-workflows-llm-ingest-and-query/03-CONTEXT.md` (verified) — workflow keys D-08, webhook paths D-09, payload schema D-11
- `CLAUDE.md` (verified) — no-JSX constraint, Docker rebuild commands, Known Gotchas

### Secondary (MEDIUM confidence)

- React 18 `React.createElement` / hooks API — behavior consistent across project usage; no external verification needed given extensive in-codebase evidence

### Tertiary (LOW confidence)

- None — all claims are based on verified codebase inspection or explicit CONTEXT.md decisions

---

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — no new libraries; existing CDN React verified in file
- Architecture: HIGH — full sidebar layout read from source, all patterns verified in codebase
- Pitfalls: HIGH — derived from direct code inspection of state variables and effects
- Backend integration: HIGH — endpoints verified in app.py; workflow keys verified in Phase 3 CONTEXT

**Research date:** 2026-04-07
**Valid until:** 2026-05-07 (stable codebase; no external API dependencies in scope)
