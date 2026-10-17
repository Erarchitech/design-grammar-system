---
tags: [debugging, docker, data-service, neo4j]
date: 2026-10-17
status: open (workaround known)
---

# data-service exits at startup when Neo4j does not accept Bolt yet

**Symptom.** After Docker Desktop starts, or after `docker compose up`, the `data-service` container shows `Exited (3)`. The Web UI then returns 502 on `/data-service/...`, and the Mapping panel shows «Меппинг недоступен».

**Cause.** data-service connects to Neo4j while the app is starting. If Neo4j is still starting and not yet accepting Bolt on 7687, startup fails and uvicorn exits with code 3. In `docker-compose.yml`, `depends_on` only orders the container starts. Neo4j has no healthcheck and data-service has no `restart` policy, so nothing starts it again.

**Workaround.** Wait for `Started.` in `docker logs neo4j`, run `docker start data-service`, then hard-refresh the page (Ctrl+Shift+R).

**Proper fix (not done).** Add a Neo4j healthcheck with `depends_on: condition: service_healthy`, or retry the connection during startup. This was not changed in Phase 1303 because `docker-compose.yml` is also the basis of the 1309 hosting package; do it there or after the merge.

Related: [[knowledge/debugging/docker compose build alone leaves the old design-grammars container running|docker compose build alone leaves the old container]].
