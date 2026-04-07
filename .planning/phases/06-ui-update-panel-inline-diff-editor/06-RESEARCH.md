# Phase 6: UI Update Panel + Inline Diff Editor - Research

**Researched:** 2026-04-07
**Domain:** Single-file React 18 SPA modification (no build step) — Update Knowledge panel with multi-step flow, checkbox candidate list, inline diff viewer, and sequential note editor
**Confidence:** HIGH

---

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

**Candidate List & Selection**
- D-01: Candidate notes displayed as a vertical checkbox list — each row shows a checkbox, note title, and relevance score badge
- D-02: Title only in the candidate list — no content preview (content shown after Propose step)
- D-03: "Select all / Deselect all" toggle link above the checkbox list
- D-04: Empty state when no candidates match: inline message in the list area ("No matching notes found. Try a different description.")

**Diff + Editor Layout**
- D-05: Stacked layout — diff preview panel above, editable textarea below. Fits the narrow sidebar and matches existing vertical layout patterns (Response + Cypher panels)
- D-06: Diff styling is GitHub-style red/green — deletions with red background, additions with green background. CSS classes `diff-del` and `diff-ins` on spans from backend `diffHtml` are styled accordingly
- D-07: Diff panel is collapsible — small "Show diff" / "Hide diff" toggle. Saves vertical space once user is confident in their edits
- D-08: Textarea pre-populated with the LLM's proposed text (not the original). User edits from the proposed version. Matches Phase 4 D-09 (client sends final edited text)

**Multi-Note Editing Flow**
- D-09: Sequential review — after Propose, show one note at a time with "Next note" / "Previous note" navigation buttons
- D-10: "Skip this note" button available per note — skipped notes are excluded from the final Confirm batch
- D-11: Summary view before final Confirm — shows list of note titles with "changed" / "skipped" status badges. Confirm button below the summary
- D-12: Batch confirm — single "Confirm All" button sends all non-skipped edited notes to the backend in one API call

**Propose Step Waiting UX**
- D-13: Step indicators reused from Phase 5 pattern with update-specific labels: "Fetching note content...", "Generating edits...", "Computing diff...". Progress bar fills as steps complete
- D-14: During the wait, the candidate list stays visible but dimmed/disabled. Step indicators appear below. When complete, the view transitions to the diff+editor view
- D-15: Inline success notification after Confirm — green message in the Response area listing updated note titles ("Updated: [Title 1], [Title 2]"). Panel resets to prompt input
- D-16: "Back to search" button at the top of the diff/editor view — lets users abandon the current edit and return to the prompt input for a new Match query

### Claude's Discretion
- Exact CSS for red/green diff backgrounds (specific hex values, border radius, padding)
- Step indicator label wording refinements
- Textarea dimensions and auto-resize behavior
- Navigation button styling and positioning
- Summary view layout details
- How to handle the case where the LLM proposes no changes (hasChanges: false)
- Whether to show the note title as a header above each diff+editor view

### Deferred Ideas (OUT OF SCOPE)

None — discussion stayed within phase scope.

</user_constraints>

---

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| UIST-04 | Update Knowledge mode shows a prompt field for node matching, a node selection area, an Edit button, an inline diff editor, and a Confirm button | Covered by D-01–D-16: three-step flow (Match → Propose → Confirm), checkbox list (D-01), Edit triggers Propose (D-13/D-14), inline diff+editor (D-05–D-08), Confirm batch (D-12) |

</phase_requirements>

---

## Summary

Phase 6 is a pure front-end change, identical in nature to Phase 5. The sole modification target is `graph-viewer/index.html` (currently 3106 lines). No new backend endpoints, no Docker changes, no new npm packages, no build step. The three backend endpoints required by this phase (`/knowledge/update/match`, `/knowledge/update/propose`, `/knowledge/update/confirm`) were built in Phase 4 and are already routable via the Nginx proxy at `/data-service/knowledge/update/*`.

The implementation adds an "Update Knowledge" branch to the `knowledgeMode === "update"` conditional inside `GraphViewerPage`. It introduces six new state variables (candidates list, selected note IDs, update sub-view, diff results array, current note index, editor text), three new async handler functions (submitMatch, submitPropose, submitConfirm), and renders a three-view panel that transitions between: (1) prompt + candidate list, (2) propose-in-progress (dimmed list + step indicators), and (3) sequential diff+editor+navigation. Styling for `.diff-del` and `.diff-ins` CSS classes is the only new CSS required.

The highest-risk area is the multi-note sequential review state machine. Six states interact: `updateView` (which phase the panel is in), `updateCandidates`, `selectedNoteIds`, `updateDiffs`, `currentNoteIndex`, and `editedContents` (a map from noteId → edited text). The planner must linearize these into a clear wave structure that builds each view incrementally and tests state transitions end-to-end before the confirm call.

**Primary recommendation:** Implement in three waves: Wave 1 adds "update" to `KNOWLEDGE_OPTIONS` and renders the Match phase (prompt + candidate list + Edit button). Wave 2 adds the Propose phase (step indicators + diff+editor+navigation). Wave 3 adds the Summary + Confirm phase and success notification. Each wave is independently runnable with a browser smoke test.

---

## Standard Stack

### Core

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| React 18 | CDN (already loaded) | UI rendering | Project constraint — single-file SPA, no build step |
| React.createElement | — | All JSX replaced | Project constraint — `const e = React.createElement` pattern throughout |
| `dangerouslySetInnerHTML` | React built-in | Rendering server-generated `diffHtml` spans | Required — backend returns raw HTML with `<span class="diff-del/ins">` |

[VERIFIED: grep of app.py lines 50-71] The `word_diff_html` function outputs `<span class="diff-del">word</span>` and `<span class="diff-ins">word</span>`. No third-party diff library is needed client-side — the diff HTML is pre-computed server-side.

### Supporting

| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| `getDataServiceBaseUrl()` | — (already present) | Build URLs for all three update endpoints | All Match/Propose/Confirm fetch calls |
| `window.GRAPH_CONFIG` | — (already present) | Project name, auth config | Extract `project` for every API payload |

### Alternatives Considered

| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| `dangerouslySetInnerHTML` for diff | Client-side diff library (diff2html, jsdiff) | Requires CDN addition or build step; backend already produces HTML — unnecessary |
| Stacked diff+textarea layout | Side-by-side layout | Side-by-side doesn't fit 394px sidebar width; stacked is the locked decision (D-05) |
| Sequential note review | Show all notes at once | Locked decision (D-09); all-at-once would overwhelm narrow sidebar |

**Installation:** None. All required libraries are already present. [VERIFIED: index.html inspection]

---

## Architecture Patterns

### Recommended Project Structure

No new files. All changes are in `graph-viewer/index.html`. The update panel follows the existing inlined-component pattern:

```
graph-viewer/index.html
├── Line ~942: KNOWLEDGE_OPTIONS array  ← add "update" option here
├── Line ~1380: State declarations      ← add 6 new update-specific state vars
├── Line ~1419: Step label arrays       ← add knowledgeUpdateSteps array
├── Line ~1900: Handler functions       ← add submitMatch, submitPropose, submitConfirm
└── Line ~2874: knowledgeMode branches  ← add knowledgeMode === "update" branch
```

### Pattern 1: Adding "update" to KNOWLEDGE_OPTIONS

**What:** Extend the existing options array — the mode dropdown rendering iterates this array automatically.
**When to use:** Any time a new knowledge mode is added.

```javascript
// [VERIFIED: index.html line 948]
const KNOWLEDGE_OPTIONS = [
  { value: "insert", label: "Insert Knowledge" },
  { value: "query",  label: "Query Knowledge"  },
  { value: "update", label: "Update Knowledge" }  // ADD THIS
];
```

### Pattern 2: Update Panel State Variables

**What:** Six new state variables scoped to the Update Knowledge flow.
**When to use:** Declare alongside existing knowledge state at line ~1380.

```javascript
// Source: inferred from existing knowledgeMode/knowledgeResponseText pattern (lines 1380-1391)
const [updateView, setUpdateView] = React.useState("match");
// values: "match" | "proposing" | "review" | "summary" | "done"

const [updateCandidates, setUpdateCandidates] = React.useState([]);
// [{noteId, title, score}] — from /match response

const [selectedNoteIds, setSelectedNoteIds] = React.useState([]);
// string[] — noteIds user checked

const [updateDiffs, setUpdateDiffs] = React.useState([]);
// [{noteId, title, originalContent, proposedContent, diffHtml, hasChanges, updatedAt}]

const [currentNoteIndex, setCurrentNoteIndex] = React.useState(0);
// index into updateDiffs for sequential review

const [editedContents, setEditedContents] = React.useState({});
// {[noteId]: string} — user's final text per note (initially = proposedContent)

const [skippedNoteIds, setSkippedNoteIds] = React.useState([]);
// noteIds the user clicked "Skip" on
```

[ASSUMED: Specific state variable names are planner discretion — the structure above matches the backend contract and D-09 through D-12 requirements]

### Pattern 3: Match Phase — Checkbox Candidate List

**What:** After `submitMatch`, render candidates as checkboxes with a score badge. Includes Select All / Deselect All and empty state.
**When to use:** `updateView === "match"` with non-empty `updateCandidates`.

```javascript
// Source: existing checkbox patterns not in codebase — use standard React.createElement for inputs
// [VERIFIED: index.html — no existing checkbox list, this is new]
e("div", { className: "candidate-list" },
  e("button", {
    type: "button",
    className: "secondary-btn",
    style: { margin: "0 0 8px 0", fontSize: "12px" },
    onClick: toggleSelectAll
  }, selectedNoteIds.length === updateCandidates.length ? "Deselect all" : "Select all"),
  updateCandidates.map(function(c) {
    return e("label", { key: c.noteId, className: "candidate-row" },
      e("input", {
        type: "checkbox",
        checked: selectedNoteIds.includes(c.noteId),
        onChange: function() { toggleCandidate(c.noteId); }
      }),
      e("span", { className: "candidate-title" }, c.title),
      e("span", { className: "candidate-score" }, c.score.toFixed(2))
    );
  })
)
```

### Pattern 4: Diff Rendering with dangerouslySetInnerHTML

**What:** The backend returns pre-built HTML from `word_diff_html()`. Render it with React's `dangerouslySetInnerHTML`.
**When to use:** `updateView === "review"` — diff panel above the textarea.

```javascript
// Source: [VERIFIED: app.py lines 50-71] — diffHtml contains <span class="diff-del"> and <span class="diff-ins">
e("div", {
  className: "diff-preview",
  dangerouslySetInnerHTML: { __html: updateDiffs[currentNoteIndex]?.diffHtml || "" }
})
```

CSS classes needed (discretion area for exact values):
```css
/* [ASSUMED: values — see Discretion section] */
.diff-del { background: rgba(220, 38, 38, 0.18); color: #fca5a5; text-decoration: line-through; border-radius: 3px; padding: 0 2px; }
.diff-ins { background: rgba(34, 197, 94, 0.18); color: #86efac; font-weight: 700; border-radius: 3px; padding: 0 2px; }
.diff-preview { font-size: 13px; line-height: 1.6; padding: 10px; background: #0b0f19; border: 1px solid #283143; border-radius: 8px; margin-bottom: 8px; white-space: pre-wrap; word-break: break-word; }
```

### Pattern 5: Propose Step — Reuse Step Indicator Infrastructure

**What:** Reuse `knowledgeProgress`, `knowledgeStep`, `knowledgeStepTimes`, `setKnowledgeWorkflowStep()` for the Propose phase wait state.
**When to use:** `updateView === "proposing"` — candidate list visible but dimmed, step indicators below.

```javascript
// Source: [VERIFIED: index.html lines 1419-1433, 1743-1772]
const knowledgeUpdateSteps = [
  "Fetching note content...",
  "Generating edits...",
  "Computing diff...",
  "Complete"
];
```

Because `/knowledge/update/propose` is a **synchronous** FastAPI endpoint (not via n8n webhook), the Propose step does NOT use `startKnowledgePollingResult()`. It uses a direct `await fetch(...)` call. Progress bar advances at 25/50/75/100% manually via `setKnowledgeProgress()` before and after the call.

[VERIFIED: app.py lines 1215-1247] The `/knowledge/update/propose` endpoint is a plain `@app.post` — no n8n webhook invocation from the client side. (The endpoint internally calls `call_n8n_sync()` to reach Ollama, but the client just awaits the HTTP response synchronously.)

### Pattern 6: Confirm Payload Construction

**What:** Build payload from non-skipped notes, using `editedContents[noteId]` for final text and `updatedAt` from Propose response for optimistic locking.
**When to use:** User clicks "Confirm All" in summary view.

```javascript
// Source: [VERIFIED: app.py lines 1250-1302]
// Backend expects: {notes: [{noteId, content, updatedAt}], project, prompt}
const notesToConfirm = updateDiffs
  .filter(d => !skippedNoteIds.includes(d.noteId))
  .map(d => ({
    noteId: d.noteId,
    content: editedContents[d.noteId] ?? d.proposedContent,
    updatedAt: d.updatedAt
  }));
const payload = {
  notes: notesToConfirm,
  project: project || "default-project",
  prompt: knowledgePromptText
};
```

### Pattern 7: Optimistic Locking 409 Handling

**What:** The Confirm endpoint returns HTTP 409 if a note was modified externally since the Propose step. The UI must surface this clearly.
**When to use:** In the `catch` / `!res.ok` branch of `submitConfirm`.

```javascript
// Source: [VERIFIED: app.py lines 1267-1271]
if (res.status === 409) {
  setKnowledgeResponseText("Conflict: " + (data?.detail || "Note was modified externally. Reload and retry."));
} else {
  setKnowledgeResponseText("Error: " + (data?.detail || res.status));
}
```

### Pattern 8: hasChanges: false Handling (Discretion)

**What:** When the LLM proposes no changes (`hasChanges === false`), the diff is empty and `diffHtml` is effectively the original text with no spans.
**When to use:** In the sequential review view, when `updateDiffs[currentNoteIndex].hasChanges === false`.

Recommended approach (discretion): Show a note-level banner "No changes proposed" in the diff area; textarea still contains the original content; user can Skip or manually edit.

### Anti-Patterns to Avoid

- **Polling `/execution-result/` for the Propose step:** The `/knowledge/update/propose` call is synchronous FastAPI — it blocks until the LLM finishes. Do NOT use `startKnowledgePollingResult()` for this step. [VERIFIED: app.py lines 1215-1247 — no `executionId` in response]
- **Rendering all notes simultaneously:** D-09 mandates sequential review. Do not map over `updateDiffs` and show all at once.
- **Sending original content on Confirm:** D-08 and Phase 4 D-09 require sending the user's edited text (from `editedContents`), not `proposedContent` or `originalContent`.
- **Resetting `knowledgePromptText` before Confirm:** The prompt is needed for the `prompt` field in the Confirm payload. Do not clear it until after a successful Confirm response.
- **XSS exposure through diffHtml:** The `diffHtml` string comes from the server (trusted backend, internal Docker network). Using `dangerouslySetInnerHTML` is acceptable here. [ASSUMED: No user-supplied HTML escapes into diffHtml — verify app.py escapes note content before diff]

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Word-level diff computation | Client-side diff logic | Backend `word_diff_html()` already built in Phase 4 | Server computes diff; client only renders the HTML output |
| Diff HTML styling | Custom diff renderer | CSS classes on existing `<span class="diff-del/ins">` elements | Backend produces class-annotated spans; just add two CSS rules |
| Optimistic locking | Client-side version tracking | Send `updatedAt` from Propose response to Confirm endpoint | Backend enforces the lock via 409; client just passes the token through |
| Async orchestration | Custom promise queue | Direct `await fetch()` for Match and Confirm; sequential `for` loop inside `submitPropose` for per-note LLM calls | Backend handles all async internally |

**Key insight:** All the hard problems (LLM invocation, diff computation, conflict detection, session recording) are already solved server-side by Phase 4 endpoints. Phase 6 is a state-machine UI layer on top of three simple REST calls.

---

## Runtime State Inventory

Step 2.5: SKIPPED — Phase 6 is a greenfield UI addition to an existing SPA. No renames, no refactors, no string replacements.

---

## Environment Availability

Step 2.6: No new external tools, services, CLIs, or runtimes. All backend endpoints already exist and are reachable via the running Docker stack. No environment audit required.

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| FastAPI `/knowledge/update/*` endpoints | All three API calls | Built in Phase 4 | — | — |
| Nginx proxy `/data-service/` | URL routing | Already configured | — | — |
| React 18 CDN | UI rendering | Already loaded | 18.x | — |

---

## Common Pitfalls

### Pitfall 1: Propose Timeout for Many Notes

**What goes wrong:** If the user selects many notes (up to 10 from the candidate list), `/knowledge/update/propose` calls the LLM once per note synchronously inside a `for` loop on the server. With llama3.1 taking 30-90s per note, the total request can exceed browser fetch timeouts.
**Why it happens:** `call_n8n_sync()` has a 120s timeout per note; 5 notes could take 10 minutes total.
**How to avoid:** The fetch call for Propose should use a long timeout or use `fetch` with no timeout on the client side (browser default is no timeout). Warn the user via step indicator wording: "Generating edits... (may take several minutes for multiple notes)".
**Warning signs:** Browser shows "ERR_EMPTY_RESPONSE" or "net::ERR_CONNECTION_RESET" with many notes selected.

[VERIFIED: app.py lines 1215-1247 — synchronous per-note loop; VERIFIED: app.py line 74 — `call_n8n_sync` timeout is 120s per call]

### Pitfall 2: State Leakage Between Update Sessions

**What goes wrong:** User does one update flow, success, panel resets to prompt. Old `updateDiffs`, `editedContents`, `skippedNoteIds`, `selectedNoteIds` still in state. New Match finds different candidates but old diff state bleeds through if view transitions are not reset.
**Why it happens:** React state is persistent across re-renders. Only an explicit reset clears it.
**How to avoid:** In the success handler after Confirm (or when user clicks "Back to search"), reset ALL six update state variables simultaneously: `setUpdateView("match")`, `setUpdateCandidates([])`, `setSelectedNoteIds([])`, `setUpdateDiffs([])`, `setCurrentNoteIndex(0)`, `setEditedContents({})`, `setSkippedNoteIds([])`.
**Warning signs:** Diff panel shows content from a previous note after a new Match.

### Pitfall 3: `dangerouslySetInnerHTML` and Missing CSS

**What goes wrong:** `diffHtml` renders but diff spans are visually invisible — words appear as plain text with no color highlighting.
**Why it happens:** `diff-del` and `diff-ins` CSS classes are not yet defined in the stylesheet. The HTML renders correctly in the DOM but has no applied styles.
**How to avoid:** Add `.diff-del` and `.diff-ins` CSS rules BEFORE testing the diff panel. This is Wave 1 work even if the diff panel itself is Wave 2.
**Warning signs:** Inspector shows `<span class="diff-del">word</span>` in DOM but no background color applied.

### Pitfall 4: Checkbox State vs. Candidate Index

**What goes wrong:** "Select all" sets `selectedNoteIds` to all candidate noteIds, but later "Deselect all" leaves behind stale IDs if the candidate list was re-fetched.
**Why it happens:** `selectedNoteIds` is a separate array that can drift out of sync with `updateCandidates`.
**How to avoid:** `toggleSelectAll` should derive from `updateCandidates.map(c => c.noteId)` every time, not from a cached set. "Select all" → `setSelectedNoteIds(updateCandidates.map(c => c.noteId))`. "Deselect all" → `setSelectedNoteIds([])`.
**Warning signs:** "Edit" button sends noteIds to Propose that are not in the current candidate list.

### Pitfall 5: Edit Button Without Selection

**What goes wrong:** User clicks "Edit" with no notes checked — the Propose call returns 400 ("noteIds must not be empty").
**Why it happens:** No validation before calling `/knowledge/update/propose`.
**How to avoid:** Disable the "Edit" button when `selectedNoteIds.length === 0`. Use `disabled: selectedNoteIds.length === 0` on the button element.
**Warning signs:** Error toast or 400 response in network tab.

### Pitfall 6: `updatedAt` Drift on Re-propose

**What goes wrong:** User reviews a note, goes "Back to search", does a new Match, and proposes again. The `updatedAt` in `updateDiffs` is stale (from the first Propose call). Confirm sends the old `updatedAt`, gets a 409.
**Why it happens:** State reset did not clear `updateDiffs`.
**How to avoid:** "Back to search" handler must reset `updateDiffs` (and all other update state) — see Pitfall 2.

---

## Code Examples

### Match Call

```javascript
// Source: [VERIFIED: app.py lines 1200-1212] — endpoint signature and response shape
const submitMatch = async () => {
  if (!knowledgePromptText.trim()) { setKnowledgeStatus("Prompt is required"); return; }
  if (knowledgeIsRunning) return;
  setKnowledgeIsRunning(true);
  setUpdateCandidates([]);
  setSelectedNoteIds([]);
  setKnowledgeStatus("Searching notes...");
  try {
    const base = getDataServiceBaseUrl();
    const res = await fetch(base + "/knowledge/update/match", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ prompt: knowledgePromptText.trim(), project: project || "default-project" })
    });
    const data = await res.json();
    if (!res.ok) { setKnowledgeStatus("Error: " + (data?.detail || res.status)); return; }
    setUpdateCandidates(data.candidates || []);
    setKnowledgeStatus(data.candidates?.length ? "Select notes to edit" : "No matches found");
  } catch (err) {
    setKnowledgeStatus("Error: " + err.message);
  } finally {
    setKnowledgeIsRunning(false);
  }
};
```

### Propose Call

```javascript
// Source: [VERIFIED: app.py lines 1215-1247] — synchronous response, no polling
const submitPropose = async () => {
  if (selectedNoteIds.length === 0) return;
  setUpdateView("proposing");
  setKnowledgeIsRunning(true);
  setKnowledgeProgress(25);
  setKnowledgeStatus("Fetching note content...");
  try {
    const base = getDataServiceBaseUrl();
    setKnowledgeProgress(50);
    setKnowledgeStatus("Generating edits...");
    const res = await fetch(base + "/knowledge/update/propose", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        noteIds: selectedNoteIds,
        prompt: knowledgePromptText.trim(),
        project: project || "default-project"
      })
    });
    setKnowledgeProgress(75);
    setKnowledgeStatus("Computing diff...");
    const data = await res.json();
    if (!res.ok) {
      setKnowledgeStatus("Error: " + (data?.detail || res.status));
      setUpdateView("match");
      return;
    }
    setUpdateDiffs(data.diffs || []);
    const initial = {};
    (data.diffs || []).forEach(d => { initial[d.noteId] = d.proposedContent; });
    setEditedContents(initial);
    setCurrentNoteIndex(0);
    setSkippedNoteIds([]);
    setKnowledgeProgress(100);
    setKnowledgeStatus("Review proposed changes");
    setUpdateView("review");
  } catch (err) {
    setKnowledgeStatus("Error: " + err.message);
    setUpdateView("match");
  } finally {
    setKnowledgeIsRunning(false);
  }
};
```

### Confirm Call

```javascript
// Source: [VERIFIED: app.py lines 1250-1302] — payload shape, 409 handling, success response
const submitConfirm = async () => {
  const notesToConfirm = updateDiffs
    .filter(d => !skippedNoteIds.includes(d.noteId))
    .map(d => ({
      noteId: d.noteId,
      content: editedContents[d.noteId] ?? d.proposedContent,
      updatedAt: d.updatedAt
    }));
  if (notesToConfirm.length === 0) {
    setKnowledgeStatus("All notes skipped — nothing to confirm");
    return;
  }
  setKnowledgeIsRunning(true);
  setKnowledgeStatus("Saving changes...");
  try {
    const base = getDataServiceBaseUrl();
    const res = await fetch(base + "/knowledge/update/confirm", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        notes: notesToConfirm,
        project: project || "default-project",
        prompt: knowledgePromptText.trim()
      })
    });
    const data = await res.json();
    if (!res.ok) {
      if (res.status === 409) {
        setKnowledgeResponseText("Conflict: " + (data?.detail || "Note was modified externally. Reload and retry."));
      } else {
        setKnowledgeResponseText("Error: " + (data?.detail || res.status));
      }
      return;
    }
    const titles = notesToConfirm
      .map(n => updateDiffs.find(d => d.noteId === n.noteId)?.title || n.noteId)
      .join(", ");
    setKnowledgeResponseText("Updated: " + titles);
    setKnowledgeStatus("Done");
    setUpdateView("match");
    setUpdateCandidates([]);
    setSelectedNoteIds([]);
    setUpdateDiffs([]);
    setCurrentNoteIndex(0);
    setEditedContents({});
    setSkippedNoteIds([]);
    setKnowledgePromptText("");
  } catch (err) {
    setKnowledgeResponseText("Error: " + err.message);
  } finally {
    setKnowledgeIsRunning(false);
  }
};
```

---

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Client-side diff libraries (diff2html, jsdiff) | Server-side difflib + `dangerouslySetInnerHTML` | Phase 4 design decision | No npm dependency; diff is always consistent with backend view |
| Single-step write | Three-step Match → Propose → Confirm | Phase 4 design decision | Prevents silent LLM overwrites; user reviews before any write |

**No deprecated approaches apply to this phase.**

---

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | `editedContents` as a `{[noteId]: string}` map is the right state shape for tracking per-note edits | Architecture Patterns / Pattern 2 | Low — any map-like structure works; naming is planner discretion |
| A2 | Diff HTML `<span>` content does not include user-controlled HTML (only whitespace-split words from note content) — `dangerouslySetInnerHTML` is safe | Architecture Patterns / Anti-Patterns | Medium — if note content contains HTML tags, they would be injected. Verify `word_diff_html` in app.py escapes HTML entities |
| A3 | The Propose endpoint has no client-visible timeout issue for ≤3 notes (typical use) | Common Pitfalls / Pitfall 1 | Low — architects are unlikely to select 8+ notes at once; the pitfall is documented for edge cases |

---

## Open Questions

1. **HTML escaping in `word_diff_html`**
   - What we know: `word_diff_html` splits on whitespace and wraps each word in `<span>` tags (app.py lines 50-71)
   - What's unclear: If a note's content contains `<`, `>`, or `&` characters, these are not escaped before being injected into `f'<span class="diff-del">{w}</span>'`. This could cause malformed HTML in the diff panel.
   - Recommendation: Check app.py `word_diff_html` — if `w` is not HTML-escaped, add `html.escape(w)` before interpolation. If already safe (notes are plain-text Markdown stored without HTML), document the assumption explicitly.

2. **Propose endpoint timeout for N notes**
   - What we know: Each note requires one LLM call via `call_n8n_sync` with 120s timeout; the loop is sequential (app.py lines 1222-1246)
   - What's unclear: The browser's default `fetch` timeout is none — but Nginx may have a proxy read timeout that terminates the connection before the LLM finishes for large batches
   - Recommendation: Check `graph-viewer/nginx.conf` for `proxy_read_timeout`. If it's the default (60s), large batches will silently fail at the proxy level.

---

## Validation Architecture

> `workflow.nyquist_validation` is absent from `.planning/config.json` — treating as enabled.

### Test Framework

| Property | Value |
|----------|-------|
| Framework | Browser smoke test (no automated test runner) |
| Config file | None — single-file SPA with no test infrastructure |
| Quick run command | `docker compose up -d design-grammars && open http://localhost:8080` |
| Full suite command | Manual walkthrough of all three Update Knowledge views |

This project has no automated test infrastructure for the frontend (no Jest, no Vitest, no Playwright). All verification is manual browser smoke testing, consistent with how Phases 2–5 were validated.

### Phase Requirements → Test Map

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| UIST-04 (Match) | Prompt → candidate list appears with checkboxes and score badges | manual | `docker compose build --no-cache design-grammars && docker compose up -d design-grammars` | N/A |
| UIST-04 (Propose) | Select notes → Edit → step indicators → diff+editor view | manual | Same build command | N/A |
| UIST-04 (Review) | Next/Previous/Skip navigation through notes | manual | Same | N/A |
| UIST-04 (Confirm) | Summary → Confirm All → success notification → panel reset | manual | Same | N/A |
| UIST-04 (Empty) | No matches → inline "No matching notes found" message | manual | Same | N/A |

### Sampling Rate

- **Per task commit:** `docker compose build --no-cache design-grammars && docker compose up -d design-grammars` + browser load check
- **Per wave merge:** Full manual walkthrough of the views built in that wave
- **Phase gate:** All four views exercised end-to-end with a real project before `/gsd-verify-work`

### Wave 0 Gaps

None — no test infrastructure gaps. Manual smoke testing is the established pattern for this project's SPA.

---

## Security Domain

This phase adds no authentication logic, no new secrets handling, no cryptographic operations, and no new data ingestion paths. All three endpoint calls go to the existing `data-service` via the existing Nginx proxy with no new auth requirements.

| ASVS Category | Applies | Standard Control |
|---------------|---------|-----------------|
| V2 Authentication | No | — |
| V3 Session Management | No | — |
| V4 Access Control | No | Existing project isolation enforced server-side |
| V5 Input Validation | Yes (minimal) | Match prompt is required (non-empty); Edit button disabled with no selection |
| V6 Cryptography | No | — |

**Known threat pattern for this phase:** `dangerouslySetInnerHTML` with backend-generated `diffHtml`. The diff HTML originates from note content stored in Neo4j. If note content was ingested via Phase 2/3 with unescaped HTML, it could be reflected into the diff panel. Mitigation: verify `html.escape()` in `word_diff_html` (Open Question 1).

---

## Sources

### Primary (HIGH confidence)
- `data-service/app.py` lines 50-71 — `word_diff_html` function and `diff-del`/`diff-ins` class names
- `data-service/app.py` lines 1200-1302 — all three update endpoints, exact request/response shapes, 409 optimistic locking, session recording
- `graph-viewer/index.html` lines 942-951 — `KNOWLEDGE_OPTIONS` array structure
- `graph-viewer/index.html` lines 1380-1433 — existing knowledge state variables and step label arrays
- `graph-viewer/index.html` lines 1743-1806 — `setKnowledgeWorkflowStep`, `finalizeKnowledgeWorkflowStep`, `applyKnowledgeProgressUpdate`, step/progress machinery
- `graph-viewer/index.html` lines 1900-2014 — `submitFolderIngest`, `submitKnowledgeIngest`, `requestKnowledge` handler patterns
- `graph-viewer/index.html` lines 2838-3005 — full Specs&Notes conditional rendering block

### Secondary (MEDIUM confidence)
- `.planning/phases/05-ui-mode-restructuring-insert-and-query-panels/05-RESEARCH.md` — established patterns for Phase 5 (same codebase, same approach)
- `.planning/phases/06-ui-update-panel-inline-diff-editor/06-CONTEXT.md` — all locked decisions

### Tertiary (LOW confidence)
- None — all critical claims were verified against source files in this session.

---

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — verified against actual file contents; no new libraries
- Architecture: HIGH — all API shapes verified from app.py; state machine follows locked decisions from CONTEXT.md
- Pitfalls: HIGH (Pitfalls 1-6) / MEDIUM (Pitfall 1 re: Nginx timeout — requires nginx.conf check)

**Research date:** 2026-04-07
**Valid until:** 2026-05-07 (stable — no third-party version churn; only internal codebase matters)
