---
tags: [atlas, ui, react, spa]
date: 2026-04-05
graphify_communities: ["Fetch Graph Context (MCP)", "Prepare Graph Payload", "Worktree Branch Commits with Spurious Deletions", "code: 17 nodes", "n8n Workflow Orchestrator"]
---

# UI is a Single-File React 18 SPA with No Build Step

The main Design Grammars UI lives entirely in `graph-viewer/index.html` — a single HTML file containing all CSS, JS, and React components using `React.createElement` (no JSX, no bundler).

## Page Flow

```
RegisterPage → HomePage → ProjectPage → GraphViewerPage
                                       → Model Viewer (/model-viewer/)
```

Managed by `AppRouter` component via `page` state.

## Components

| Component | Purpose | Key State |
|-----------|---------|-----------|
| `AppRouter` | Root router, session restore from localStorage | `page`, `currentUser`, `currentProject` |
| `RegisterPage` | Login/Register with SHA-256 password hashing | `isRegister`, `email`, `password`, `error` |
| `HomePage` | Project grid with search, create, profile dropdown | `searchQuery`, `projects`, `showProfileMenu` |
| `ProjectPage` | Project detail with Grammar Viewer + Model Viewer tiles | `userProfile`, `projectData` |
| `GraphViewerPage` | 3-column layout: controls / NeoVis graph / detail panel | `mode`, `graphView`, `cypher`, `selected`, etc. |

## GraphViewerPage Modes

- **Insert Rules** — Send NL text to n8n ingest webhook
- **Query Rules** — Send NL question to n8n query webhook
- **Edit Rules** — Select existing rule, send edit to ingest with `"edit Rule_Id: ..."` prefix

## Graph Visualization

- NeoVis.js renders Neo4j graphs directly in browser
- Node colors and labels configured via `window.GRAPH_CONFIG` (from `config.template.js`)
- Click node → right panel shows properties with inline editing
- Right-click → context menu with delete option

## User & Project Storage

All client-side in `localStorage`:
- `dg_users`: `{ [email]: { passwordHash, name, surname, projects: [...] } }`
- `dg_current_user`: current session email

See [[Passwords hashed client-side with SubtleCrypto SHA-256]].

## Related

- [[Single-file React SPA avoids build tooling for main UI]]
- [[NeoVis renders interactive graph visualization in browser]]
- [[Async polling pattern for n8n workflow execution tracking]]

<!-- graphify:connections:start -->
## Graph connections

- [[graphify/communities/Fetch Graph Context (MCP)|Fetch Graph Context (MCP)]]
- [[graphify/communities/Prepare Graph Payload|Prepare Graph Payload]]
- [[graphify/communities/Worktree Branch Commits with Spurious Deletions|Worktree Branch Commits with Spurious Deletions]]
- [[graphify/communities/code 17 nodes|code: 17 nodes]]
- [[graphify/communities/n8n Workflow Orchestrator|n8n Workflow Orchestrator]]
<!-- graphify:connections:end -->
