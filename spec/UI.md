# UI Specification

## Main SPA (`graph-viewer/index.html`)

A **single HTML file** containing all CSS, JS, and React components. Uses `React.createElement` (no JSX, no bundler). React 18 loaded from CDN.

### Page Flow

```
RegisterPage → HomePage → ProjectPage → GraphViewerPage
                                       → Model Viewer (/model-viewer/)
```

Managed by `AppRouter` component via `page` state.

### Components

| Component | Purpose | Key State |
|-----------|---------|-----------|
| `AppRouter` | Root router, session restore from localStorage | `page`, `currentUser`, `currentProject` |
| `RegisterPage` | Login/Register with SHA-256 password hashing | `isRegister`, `email`, `password`, `error` |
| `HomePage` | Project grid with search, create, profile dropdown | `searchQuery`, `projects`, `showProfileMenu` |
| `ProjectPage` | Project detail with Grammar Viewer + Model Viewer tiles | `userProfile`, `projectData` |
| `GraphViewerPage` | 3-column layout: controls / NeoVis graph / detail panel | `mode`, `graphView`, `cypher`, `selected` |

### GraphViewerPage Modes

- **Insert Rules** — Send NL text to n8n ingest webhook
- **Query Rules** — Send NL question to n8n query webhook
- **Edit Rules** — Select existing rule, send edit with `"edit Rule_Id: ..."` prefix

### Graph Visualization

- NeoVis.js renders Neo4j graphs directly in browser via Bolt protocol
- Node colors and labels configured via `window.GRAPH_CONFIG` (from `config.template.js`)
- Click node → right panel shows properties with inline editing
- Right-click → context menu with delete option

### User & Project Storage

All client-side in `localStorage`:
- `dg_users`: `{ [email]: { passwordHash, name, surname, projects: [...] } }`
- `dg_current_user`: current session email
- Passwords hashed client-side with `SubtleCrypto.digest('SHA-256', ...)`

### Design System

- **Fonts:** Inter (400/500/600 body), Space Grotesk (500/600 headings)
- **Theme:** Dark with CSS custom properties (`--bg`, `--accent`, `--panel`, etc.)

---

## Model Viewer (`graph-viewer/model-viewer/`)

A **separate React + Vite app** for 3D validation visualization. Built during Docker image stage, served at `/model-viewer/`.

### Tech Stack

- React + JSX (via Vite)
- `@speckle/viewer` — 3D rendering engine (Three.js based)
- Extensions: CameraController, SelectionExtension, FilteringExtension

### Features

- **Validation run browser** — lists runs from data-service, clickable tiles
- **Rule-based filtering** — select a rule to isolate failing/passing entities
- **3D color coding** — configurable fail (red), pass (green), base (neutral) colors + opacity sliders
- **Isolate/Hide** — isolate selected entities or hide them from view
- **Speckle Connector panel** — configure project ID, base model ID, validation model ID
- **Speckle Settings** — manage base URL, write/read tokens

### URL Parameters

- `?project=<n>` — pre-select DG project
- `?runId=<id>` — load specific validation run
- `?ruleId=<id>` — pre-filter by rule

### Data Flow

```
Model Viewer
  → GET /data-service/validation/view/{project}         → manifest
  → GET /data-service/validation/runs/{project}          → run list
  → Speckle Server (3D model URLs from manifest)
```

### Known Issues

- Viewport shows mixed rotation states
- No rename/delete management for validation runs (planned)
