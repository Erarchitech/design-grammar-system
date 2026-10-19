# Explicit mapping confirmation — local rollout

Date: 2026-10-19. Scope: mapping worktree `feature/mapping-mvp`; standalone DeGram clone `D:\dgb\src`. No push and no installed Hermes changes.

## Source and behavior

- Framework source: `abee02e3460e48039f579016fda7e85b77989958`.
- DeGram source: `38d3e7e7b3d54509e92832b5b39481362455fed3`.
- Answers remain drafts. One shared confirmation commits the current accepted answer IDs, not rejected, unanswered or automatic suggestions. Remaining proposals stay open.
- The apply route admits project-bound delegated editor intent. Connector-only delivery receipts remain distinct from server commitment. Queued does not mean written to CAD.

## Observed rollout

- Clean source exported with `git archive abee02e` under `D:\dgb\mapping-release-abee02e`. Git archive's configured CRLF export was checked against archive bytes and normalized Git blobs.
- Only `data-service` and `design-grammars` were recreated in the existing Compose project, preserving the existing data mount and network. Other services were not recreated.
- Running data-service image: `sha256:5c42f00a6af2b4f895dc2856a53bf4eb02829441bd2b1ac2a7fe4221fbe6fc1a`.
- Running UI image: `sha256:5830acc57e6706a0119552c9f62f78f8441968ebb1ea238be1d818b3c276641f`.
- Both image revision labels identify the full framework commit. Live backend source hashes match the clean export. Loaded apply policy: member/delegated/connector, body project, editor minimum; the handler separately limits receipts to connectors.
- Live probes: backend `/` 200, UI `/` 200, anonymous mapping list 401, anonymous apply 401. Served split bundle `/assets/App-D6bHdMXH.js` contains the explicit confirmation copy.
- GH rebuilt from the archive; focused tests 28/28, rebuild 0 warnings / 0 errors. With Rhino closed, five approved DG assemblies/symbols were backed up and replaced. Installed `DG.gha` SHA-256: `244e8d1993c080c3c8b361ad68eb50274ad1f70d716f64c90fc10ee15437a80e`.
- With Revit closed and separate owner approval, only `dg-revit-connector.extension` was updated through the committed installer. All 48 installed source files match the archive. Previous extension: `D:\dgb\mapping-release-abee02e\revit-rollback\20261019T202642Z`. Other pyRevit extensions were not targeted.
- DeGram build driver now pins `D:\dgb\mapping-release-abee02e\apps\dg-revit-connector`, after separate approval of that one-line driver change.

## Checks and current limits

- Worktree backend/Revit regression: 593 passed. Targeted auth/mapping/security: 128 passed. Browser tests: 333 passed; Vite build completed.
- DeGram focused Python: 81 passed. Mapping renderer: 22 passed; changed-file lint and both TypeScript checks passed.
- Broader DeGram renderer: 324 passed, 1 skipped, 1 failed (`ru-catalog-completeness.test.ts`, English URL placeholder). Do not describe the full renderer suite as green.
- First Desktop build refused untracked generated `graphify-out`; it was preserved outside the clone, not committed or deleted. A second build was started. Packaged build and launch remain pending at this checkpoint.
- Clean archive backend/Revit tests: 576 passed, 1 skipped. The first archive test attempt lacked a committed Revit snapshot fixture (4 setup errors); exporting `tools/mapping` from the same commit resolved those errors. This subset omits the separate security-spec suite.
- Additional pytest inside the shared live container was denied and not run. Host tests and live hashes/probes are not a substitute for in-container tests.
- No CAD file was opened, mapping batch committed, paid LLM called, retired profile enabled or physical CAD transaction accepted by this rollout.

## Rollback

- Backend image: `dg-mapping-data-service:rollback-before-abee02e` (`82378ca11829…`).
- UI image: `dg-mapping-ui:rollback-before-abee02e` (`aae916eba822…`).
- Compose image overrides and rollback overrides: `D:\dgb\mapping-release-abee02e\compose.mapping-images.yml` and `compose.mapping-rollback.yml`.
- GH files: `D:\dgb\mapping-release-abee02e\gh-rollback`.
- Revit extension: backup path above. Restore only while Revit is closed; GH restore only while Rhino is closed.
