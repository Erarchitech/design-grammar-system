---
tags: [debugging, ui-v2, model-viewer, speckle, open]
date: 2026-10-05
status: open
---

# Model Viewer shows a foreign base model and a hard-coded tile property catalogue (F18–F22)

The owner observed these in step 7 of the test `v12-hexagonal-facade-01`. The validation colouring itself was correct.

- **F18 — foreign base model.** With **Base model** on, the Urban-Block model from another project is overlaid. Cause: the project auto-bound on first publish to `SPECKLE_PROJECT_ID` / `SPECKLE_BASE_MODEL_ID` from env (`44088eefc6` / `4c546c0771`), and all 44 `ValidationRun`s carry that `baseModelId`. There is no V2 UI form to bind or unbind a Speckle project/model (see [[knowledge/debugging/V2 UI has no Speckle project link form and the setup guide predates v7]]). The base-model feature is outdated and gets in the way.
- **F19 — leftover shadow.** With Base model off, its geometry disappears but its **shadow stays**.
- **F20 — black preview.** After switching to another Validation Run, the viewport stays in preview mode with a **black background** although the background is white.
- **F21 — camera reset.** Returning to the previous Validation Run **resets the camera** to its default.
- **F22 — hard-coded tile properties.** Design States → Tile properties lists 9 urban properties (Height, GFA, Units, Storeys, Site coverage, Setback, Glazing ratio, Daylight factor, Parking ratio). This is the fixed `PROPSTATES` catalogue in `ui-v2/src/screens/ModelScreen.jsx:74-84`, not the project's PropStates. The caption `bolt://dg-meta:7687` is hard-coded too (`:632`). None of them matches this project's properties.

## Related

- [[sessions/2026-10-05 v12 hexagonal facade test steps 2-8 and five DG fixes]]
