---
tags: [decision, ui-v2, model-viewer, speckle]
date: 2026-10-08
status: accepted
---

# Model Viewer shows only the validation model

**Decision (owner, 2026-10-07):** the Model Viewer has no Base model checkbox and never loads a run's base model; it loads only the validation model.

**Why:** projects auto-bound on first publish to the env defaults `SPECKLE_PROJECT_ID` / `SPECKLE_BASE_MODEL_ID`, so every run carried the Urban-Block model of another project (F18). Hiding it by filtering left its baked ground shadow behind (F19). The feature was outdated and in the way.

**How:** `ModelScreen.jsx` picks the validation URL from `view.viewerResources` using the payload's ids (`resolve_view_resources` lists base first, validation second, skipping a model without id/version). Runs still store `baseModelId`, and the Properties panel still shows it as text; a bind/unbind form for base models would be a separate task.

Related: [[knowledge/debugging/Model Viewer shows a foreign base model and a hard-coded tile property catalogue]]
