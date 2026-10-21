---
tags: [debugging, docker, deployment, phase-1303]
date: 2026-10-21
status: restored in the same session
---

# Rebuilding data-service from the main folder replaced the mapping release image

**What happened.**
- To deploy a fix, `docker compose build data-service && docker compose up -d data-service` was run in `C:\Users\Admin\source\repos\design-grammar-system`. That folder holds `feature/hosting-dg-pilot`.
- The live stack ran `dg-mapping-data-service:b7bcbf0` through `D:\dgb\mapping-release-b7bcbf0\compose.mapping-images.yml`.
- The rebuild replaced it with hosting-branch code that has no calculator or mapping modules (`property_calculator_store.py`, `property_scripts.py`). For about 20 minutes the mapping UI (`dg-mapping-ui:b7bcbf0`) talked to a data-service without its endpoints.

**Recovery.** `docker compose -f docker-compose.yml -f D:\dgb\mapping-release-b7bcbf0\compose.mapping-images.yml up -d data-service`; confirmed with `docker inspect`.

**Rule.**
- Before rebuilding or recreating any service, read its image with `docker inspect <svc> --format '{{.Config.Image}}'`.
- If it is a `dg-mapping-*` image:
  1. make the change in the `dg-mapping` worktree;
  2. commit it;
  3. build from `git archive <sha>:data-service`;
  4. start it through a new `D:\dgb\mapping-release-<sha>` override.
- The previous override is the rollback.

Session: [[sessions/2026-10-21 Multi-participant rules design, plans 1303-19 to 23 and Graph Viewer cap fix]].
