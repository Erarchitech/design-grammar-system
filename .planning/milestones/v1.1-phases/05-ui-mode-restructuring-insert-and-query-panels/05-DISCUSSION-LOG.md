# Phase 5: UI Mode Restructuring + Insert and Query Panels - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-04-07
**Phase:** 05-ui-mode-restructuring-insert-and-query-panels
**Areas discussed:** Sidebar navigation pattern, Insert Knowledge panel layout, Async polling UX, Visual grouping style

---

## Sidebar Navigation Pattern

| Option | Description | Selected |
|--------|-------------|----------|
| Section headers with mode buttons | Two labeled sections with clickable mode buttons listed underneath. No dropdown. | |
| Two-level dropdown | Keep dropdown but add group headers inside (optgroup). | |
| Tabbed sections | Top-level tabs switch between sections. Each tab shows its own set of mode controls. | ✓ |

**User's choice:** Tabbed sections — with specific naming: "DesignRules" (not "Validation") and "Specs&Notes" (not "Project Knowledge"). Tabs appear at top of sidebar beneath the Project button. Each tab has its own set of mode controls.

| Option | Description | Selected |
|--------|-------------|----------|
| Always visible | Both sections show all modes at once. | |
| Collapsible accordion | Click section header to expand/collapse. | |
| You decide | Let Claude choose. | |

**User's choice:** Inactive section's modes must collapse. Current dropdown logic remains within each tab.

| Option | Description | Selected |
|--------|-------------|----------|
| Keep state | Graph view, prompt text, response persist when switching modes. | ✓ |
| Reset on section change | Clear prompt/response when switching between sections. | |
| You decide | Let Claude choose. | |

**User's choice:** Keep state.

| Option | Description | Selected |
|--------|-------------|----------|
| Always visible | Keep Graph View dropdown in all modes. | |
| Only in Validation | Hide Graph View when in Knowledge modes. | ✓ |
| You decide | Let Claude choose. | |

**User's choice:** Only in Validation (DesignRules tab).

---

## Insert Knowledge Panel Layout

| Option | Description | Selected |
|--------|-------------|----------|
| Tab toggle within panel | Two small tabs: "From Folder" and "From Prompt". Similar to existing Cypher/NL toggle. | ✓ |
| Stacked fields | Both inputs visible at once. | |
| Dropdown sub-mode | A small dropdown selects folder or prompt input. | |

**User's choice:** Tab toggle within panel.

| Option | Description | Selected |
|--------|-------------|----------|
| Text input only | Simple text field for typing/pasting folder path. | |
| Text input with example hint | Text field with placeholder and help tooltip about Docker-accessible paths. | ✓ |
| You decide | Let Claude choose. | |

**User's choice:** Text input with example hint.

| Option | Description | Selected |
|--------|-------------|----------|
| Inline success message | Show result in Response textarea. | ✓ |
| Toast notification | Brief auto-dismissing notification. | |
| You decide | Let Claude choose. | |

**User's choice:** Inline success message.

---

## Async Polling UX

| Option | Description | Selected |
|--------|-------------|----------|
| Reuse existing pattern | Same step indicators + progress bar with knowledge-specific step labels. | ✓ |
| Simplified spinner | Just a loading spinner with status text. | |
| You decide | Let Claude choose. | |

**User's choice:** Reuse existing pattern.

| Option | Description | Selected |
|--------|-------------|----------|
| Same as Rules errors | Show errors in Response textarea with red styling. | ✓ |
| You decide | Let Claude choose. | |

**User's choice:** Same as Rules errors.

---

## Visual Grouping Style

| Option | Description | Selected |
|--------|-------------|----------|
| Match existing prompt tabs | Same style as Rules Prompt / Cypher Expression toggle. | ✓ |
| Full-width pill tabs | Wider tabs with rounded pill shape. | |
| You decide | Let Claude choose. | |

**User's choice:** Match existing prompt tabs.

| Option | Description | Selected |
|--------|-------------|----------|
| No indicator | Treat as normal UI element. | ✓ |
| Subtle 'new' badge | Small dot that disappears after first use. | |
| You decide | Let Claude choose. | |

**User's choice:** No indicator.

---

## Claude's Discretion

- Exact step labels for knowledge insert and query operations
- CSS for the top-level tab bar (dimensions, spacing)
- State variable naming and React component refactoring approach
- "Clear the Graph" button visibility in Specs&Notes modes
- Whether to refactor GraphViewerPage into sub-components

## Deferred Ideas

None — discussion stayed within phase scope.
