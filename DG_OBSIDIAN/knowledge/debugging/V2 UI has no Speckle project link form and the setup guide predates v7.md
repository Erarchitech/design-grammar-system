---
tags: [debugging, ui-v2, speckle, docs, open]
date: 2026-10-01
status: open
---

# V2 UI has no Speckle project link form and the setup guide predates v7

## Findings

1. **No UI to link a DG project to a Speckle project/model.** The legacy SPA had a "Model Viewer" card with *Speckle Project Id / Base Model Id / Save Speckle Link*. `ui-v2/src` has no caller of `PUT /integration/speckle/project/{project}`. ModelScreen only displays `baseModelId` / `validationModelId`. The remaining paths are:
   - the API route (owner role, session auth since Phase 1205);
   - implicit auto-config on the first manual publish from `SPECKLE_PROJECT_ID` + `SPECKLE_BASE_MODEL_ID` in the data-service env (`_auto_configure_integration`). This path binds **every** new project to the same default base model.
2. **`docs/UPDATED_SYSTEM_SETUP_AND_TEST.md` is stale.** It still describes CLASSIFICATOR (removed in v7), CONNECTOR with a Neo4j URL/user/password (replaced by a single `dgc_` platform token in Phase 825/1205), `graph:'ValidationGraph'` Cypher and the legacy `/model-viewer/` route. A user following it will fail at the GH wiring step.
3. **Stale plugin deployment went unnoticed.** `%APPDATA%\Grasshopper\Libraries\DG\DG.gha` was dated 2026-07-26 while v12 was deployed. Server and plugin versions are not checked against each other. The fix was a Release rebuild + copy + SHA256 match.

## Suggested fixes

- Add a Speckle link panel to ModelScreen or ProjectsScreen (owner only).
- Rewrite or replace the setup guide. `test/v12-hexagonal-facade-01/README.md` currently serves as the working sequence.
- Have CONNECTOR report its plugin version through the heartbeat, so the server can flag an outdated client.

Related: [[sessions/2026-10-04 v12 hexagonal facade full-cycle test setup]]
