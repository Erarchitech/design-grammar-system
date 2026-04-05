---
tags: [atlas, model-viewer, speckle, 3d]
date: 2026-04-05
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
