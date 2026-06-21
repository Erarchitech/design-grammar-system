---
tags: [atlas, model-viewer, speckle, 3d]
date: 2026-04-05
graphify_communities: ["Model Viewer (graph-viewer/model-viewer/)", "Model Viewer is a Vite-built Speckle 3D Viewer", "Per-Run Graphics State and Screenshot Persistence", "Product Bridges Natural Language Rules to Graph-Based Val...", "SpeckleProjectConfigPayload", "Validation Endpoints (publish/runs/view)", "ValidationGeometryPayload", "Worktree Branch Commits with Spurious Deletions", "code: 17 nodes", "extractErrorMessage()", "v2.0 Gap Closure Retrospective"]
---

# Model Viewer is a Vite-Built Speckle 3D Viewer

Located in `graph-viewer/model-viewer/`, this is a separate React + Vite app for 3D validation visualization. It's built during the Docker image stage and served at `/model-viewer/`.

## Tech Stack

- React + JSX (via Vite)
- `@speckle/viewer` — 3D rendering engine (Three.js based)
- Extensions: CameraController, SelectionExtension, FilteringExtension

## Features

- **Validation run browser** — lists runs from data-service, clickable tiles
- **Rule-based filtering** — select a rule to isolate failing/passing entities
- **3D color coding** — configurable fail (red), pass (green), base (neutral) colors + opacity sliders
- **Isolate/Hide** — isolate selected entities or hide them from view
- **Speckle Connector panel** — configure project ID, base model ID, validation model ID
- **Speckle Settings** — manage base URL, write/read tokens

## Data Flow

```
model-viewer → /data-service/validation/view/{project} → manifest
             → /data-service/validation/runs/{project} → run list
             → Speckle Server (3D model URLs from manifest)
```

## URL Parameters

- `?project=<name>` — pre-select DG project
- `?runId=<id>` — load specific validation run
- `?ruleId=<id>` — pre-filter by rule

## Known Issues

- Viewport shows mixed rotation states. See [[Model viewer needs rotation fix and validation management]].
- No rename/delete management for validation runs (planned).

## Related

- [[Speckle hosts 3D BIM models for validation overlay]]
- [[Validation results publish to Speckle as overlay versions]]
- [[Architecture is a microservices Docker pipeline]]

<!-- graphify:connections:start -->
## Graph connections

- [[graphify/communities/Model Viewer (graph-viewermodel-viewer)|Model Viewer (graph-viewer/model-viewer/)]]
- [[graphify/communities/Model Viewer is a Vite-built Speckle 3D Viewer|Model Viewer is a Vite-built Speckle 3D Viewer]]
- [[graphify/communities/Per-Run Graphics State and Screenshot Persistence|Per-Run Graphics State and Screenshot Persistence]]
- [[graphify/communities/Product Bridges Natural Language Rules to Graph-Based Val...|Product Bridges Natural Language Rules to Graph-Based Val...]]
- [[graphify/communities/SpeckleProjectConfigPayload|SpeckleProjectConfigPayload]]
- [[graphify/communities/Validation Endpoints (publishrunsview) (51)|Validation Endpoints (publish/runs/view)]]
- [[graphify/communities/ValidationGeometryPayload|ValidationGeometryPayload]]
- [[graphify/communities/Worktree Branch Commits with Spurious Deletions|Worktree Branch Commits with Spurious Deletions]]
- [[graphify/communities/code 17 nodes|code: 17 nodes]]
- [[graphify/communities/extractErrorMessage()|extractErrorMessage()]]
- [[graphify/communities/v2.0 Gap Closure Retrospective|v2.0 Gap Closure Retrospective]]
<!-- graphify:connections:end -->
