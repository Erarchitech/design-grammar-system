# Phase 7: UI Session History Panel + NeoVis Knowledge View - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-04-08
**Phase:** 07-ui-session-history-panel-neovis-knowledge-view
**Areas discussed:** Session History placement, Session list layout & detail, Mode filter behavior, KnowledgeGraph view toggle, Restore behavior

---

## Session History Placement

| Option | Description | Selected |
|--------|-------------|----------|
| 4th mode in dropdown | Add 'Session History' to KNOWLEDGE_OPTIONS dropdown alongside insert/query/update | |
| Always-visible section below | Collapsible 'Recent Sessions' section always visible at bottom of sidebar | ✓ |
| Separate sub-tab | Second row of tabs within Specs&Notes: 'Actions' and 'History' | |

**User's choice:** Always-visible section below
**Notes:** None

### Follow-up: Section Size

| Option | Description | Selected |
|--------|-------------|----------|
| Fixed split with resize handle | Sessions section takes ~30% of sidebar height, scrollable independently | |
| Collapsible panel (collapsed by default) | Small collapsed bar showing count, expands on click. Default: collapsed | ✓ |
| Collapsible panel (expanded by default) | Same but opens expanded by default | |

**User's choice:** Collapsible panel (collapsed by default)

---

## Session List Layout & Detail

| Option | Description | Selected |
|--------|-------------|----------|
| Compact rows with expand-on-click | Mode badge, truncated prompt, relative date. Click to expand for full details | ✓ |
| Cards with preview | Small card with mode badge, full prompt, and result preview visible | |
| Plain text log | Simple text list, no expansion | |

**User's choice:** Compact rows with expand-on-click

### Follow-up: Expanded View

| Option | Description | Selected |
|--------|-------------|----------|
| Inline accordion | Expands below the row, pushes other entries down. Shows full details | ✓ |
| Detail overlay/modal | Side panel or modal overlay showing full session details | |
| Click-to-reuse (no detail) | Clicking copies prompt into active mode's textarea | |

**User's choice:** Inline accordion

---

## Mode Filter Behavior

| Option | Description | Selected |
|--------|-------------|----------|
| Chip toggles in header | Colored chips: 'All' · 'Insert' · 'Query' · 'Update' | |
| Dropdown filter | Small dropdown next to 'Session History' label | ✓ |
| No filter (show all) | Always show all sessions, mode visible via badge | |

**User's choice:** Dropdown filter

### Follow-up: Default Filter

| Option | Description | Selected |
|--------|-------------|----------|
| All modes (default) | Show all modes by default | ✓ |
| Match active mode | Auto-filter to match currently active knowledge mode | |

**User's choice:** All modes (default)

---

## KnowledgeGraph View Toggle

| Option | Description | Selected |
|--------|-------------|----------|
| Auto-switch only (current) | Keep current behavior: Specs&Notes auto-renders KnowledgeGraph. No dropdown change | ✓ |
| 3rd option in dropdown (both tabs) | Add 'KnowledgeGraph' to Graph View dropdown, visible in both tabs | |
| 3rd option (DesignRules only) | Add to dropdown but only show in DesignRules tab | |

**User's choice:** Auto-switch only (current)

---

## Restore Behavior (user-initiated addition)

User requested a "Restore" button per session entry during wrap-up.

| Option | Description | Selected |
|--------|-------------|----------|
| Full restore (prompt + result + mode switch) | Sets prompt, response, and switches knowledge mode to match session | ✓ |
| Prompt only (re-run needed) | Only fills prompt textarea | |
| Result only | Only shows stored result | |

**User's choice:** Full restore (prompt + result + mode switch)
**Notes:** Restore is non-destructive — reads from stored data, does not re-execute queries

---

## Claude's Discretion

- Collapsible panel CSS (height, background, border, expand/collapse icon)
- Mode badge chip colors per mode type
- Relative date formatting approach
- Max sessions to display / pagination strategy
- Restore button styling and positioning
- Accordion animation

## Deferred Ideas

None — discussion stayed within phase scope.
