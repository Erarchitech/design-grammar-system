---
phase: 821-dg-reasoner-sidecar-ontograph-metagraph-rdf-translation
plan: 01
subsystem: infra
tags: [docker-compose, fastapi, neo4j, n10s, neosemantics, sidecar, python]

# Dependency graph
requires:
  - phase: 820-reasoning-stack-architecture-decision-ontograph-axiom-scopin
    provides: pinned stack versions (owlready2/rdflib/pyshacl/owlrl), HermiT+JRE reproduction proof, ADR-820-1/2 (hybrid scoping, sidecar confirmed)
provides:
  - dg-reasoner/ sidecar package (Dockerfile, pinned requirements.txt, FastAPI app.py skeleton, tests/)
  - dg-reasoner docker-compose service wired internal-only (no host port) with ./ontology read-only mount and neo4j bolt creds
  - neo4j service rebuilt from a custom neo4j/Dockerfile with the n10s (neosemantics) plugin baked in and smoke-verified
  - data-service DG_REASONER_URL env var for the Plan 04 proxy route
affects: [821-02-translator, 821-03-reasoning-routes, 821-04-data-service-proxy, 822-owl-2-dl-reasoning-integration]

# Tech tracking
tech-stack:
  added: [owlready2==0.51, rdflib==7.6.0, pyshacl==0.40.0, owlrl==7.6.2, neo4j==6.2.0 (dg-reasoner), neosemantics 5.26.0 jar (neo4j plugin), openjdk-21-jre-headless]
  patterns: [sidecar mirrors data-service/ Dockerfile+requirements+app.py+tests/ shape, env-driven Neo4j bolt connection with dev-safe os.getenv defaults, internal-only docker-compose service (no host port, no nginx route)]

key-files:
  created:
    - dg-reasoner/Dockerfile
    - dg-reasoner/requirements.txt
    - dg-reasoner/app.py
    - dg-reasoner/tests/conftest.py
    - dg-reasoner/tests/test_health.py
    - dg-reasoner/tests/test_n10s_smoke.py
    - neo4j/Dockerfile
  modified:
    - docker-compose.yml

key-decisions:
  - "Debian trixie (python:3.11-slim base) dropped openjdk-17-jre-headless from apt; substituted openjdk-21-jre-headless per the plan's documented fallback (verified via live docker build, apt-cache search confirms 17 is absent, only 21/25 present)"
  - "Pinned starlette<1.0.0 and added httpx to dg-reasoner/requirements.txt: unpinned fastapi resolves starlette>=1.0 whose TestClient now requires a new PyPI package `httpx2` instead of the well-established `httpx` (already vetted, used by data-service); pinning avoids introducing an unreviewed new package purely to satisfy a test-only transport dependency"
  - "n10s installed via a custom neo4j/Dockerfile (FROM neo4j:5.26 + wget-fetched neosemantics-5.26.0.jar), not NEO4J_PLUGINS auto-download, per RESEARCH.md's flakiness warning (docker-neo4j#489); confirmed neo4j:5.26 base image lacks curl but has wget, adjusted fetch command accordingly"

patterns-established:
  - "Sidecar env-var contract identical to data-service (NEO4J_URI/NEO4J_USER/NEO4J_PASSWORD via os.getenv with matching dev defaults, never hardcoded elsewhere)"
  - "Stub routes return 501 + {status: not-implemented, plan: <next-plan-id>} to declare contract surface before real logic lands"

requirements-completed: [REAS-05]

coverage:
  - id: D1
    description: "dg-reasoner sidecar package exists (Dockerfile, requirements.txt, app.py, tests/), mirrors data-service/ shape, and its Docker image builds successfully with Python 3.11 + headless JRE"
    requirement: "REAS-05"
    verification:
      - kind: unit
        ref: "dg-reasoner/tests/test_health.py#test_health_returns_ok"
        status: pass
      - kind: other
        ref: "docker compose build dg-reasoner (exit 0)"
        status: pass
    human_judgment: false
  - id: D2
    description: "Sidecar reads Neo4j directly over bolt using NEO4J_URI/NEO4J_USER/NEO4J_PASSWORD env vars (dev default neo4j/12345678), same pattern as data-service; GET /health reports neo4j reachability"
    requirement: "REAS-05"
    verification:
      - kind: integration
        ref: "docker exec dg-reasoner curl-equivalent GET /health -> {\"status\":\"ok\",\"neo4j\":\"up\"}"
        status: pass
    human_judgment: false
  - id: D3
    description: "neo4j service has the n10s plugin installed and a smoke check confirms n10s procedures respond (SHOW PROCEDURES ... STARTS WITH 'n10s' count > 0); graphconfig.init is callable"
    requirement: "REAS-05"
    verification:
      - kind: integration
        ref: "dg-reasoner/tests/test_n10s_smoke.py#test_n10s_procedures_registered"
        status: pass
      - kind: integration
        ref: "dg-reasoner/tests/test_n10s_smoke.py#test_n10s_graphconfig_init_callable"
        status: pass
    human_judgment: false
  - id: D4
    description: "./ontology is volume-mounted read-only into the sidecar so DesignGrammar-V7.owl reaches the container without an image rebuild"
    requirement: "REAS-05"
    verification:
      - kind: other
        ref: "docker-compose.yml dg-reasoner.volumes: ./ontology:/app/ontology:ro (grep-verified)"
        status: pass
    human_judgment: false
  - id: D5
    description: "dg-reasoner is internal-only (no host port mapping, no nginx route); reachable on the docker network as dg-reasoner:8000"
    requirement: "REAS-05"
    verification:
      - kind: other
        ref: "docker port dg-reasoner (empty output, confirming no host port mapping)"
        status: pass
    human_judgment: false
  - id: D6
    description: "dg-reasoner and data-service both start under docker compose without the sidecar altering data-service startup; DG_REASONER_URL is set on data-service"
    requirement: "REAS-05"
    verification:
      - kind: integration
        ref: "docker compose up -d neo4j dg-reasoner data-service (all start cleanly); docker exec data-service printenv DG_REASONER_URL -> http://dg-reasoner:8000; GET /docs returns 200"
        status: pass
    human_judgment: false

duration: 40min
completed: 2026-07-11
status: complete
---

# Phase 821 Plan 01: dg-reasoner Sidecar Scaffold & n10s Install Summary

**dg-reasoner sidecar (Python 3.11 + headless JRE) mirroring data-service, wired internal-only into docker-compose with a pinned n10s-equipped neo4j image, ./ontology read-only mount, and a working /health endpoint that confirms live bolt connectivity.**

## Performance

- **Duration:** ~40 min
- **Started:** 2026-07-11T21:28:00Z (approx.)
- **Completed:** 2026-07-11T22:08:01Z
- **Tasks:** 2
- **Files modified:** 8 (7 created, 1 modified)

## Accomplishments
- `dg-reasoner/` scaffolded as a full mirror of `data-service/`'s shape (Dockerfile, requirements.txt, app.py, tests/), builds cleanly, and serves a passing `/health` unit test with zero docker/JRE dependency
- `neo4j/Dockerfile` bakes a version-matched neosemantics 5.26.0 jar onto `neo4j:5.26` — deterministic install immune to the documented `NEO4J_PLUGINS` auto-download flakiness (docker-neo4j#489)
- `docker-compose.yml` wires `dg-reasoner` as a fully internal service (no host port, no nginx route) with `./ontology:/app/ontology:ro` and Neo4j bolt creds, and adds `DG_REASONER_URL` to `data-service` for the Plan 04 proxy
- Live-verified end-to-end: both images build (exit 0), `neo4j` + `dg-reasoner` + `data-service` all start cleanly together, `/health` confirms real bolt connectivity from inside the sidecar container, and the n10s smoke test passes 2/2 against the live neo4j instance

## Task Commits

Each task was committed atomically:

1. **Task 1: Scaffold the dg-reasoner sidecar package (Dockerfile, requirements, FastAPI skeleton, health)** - `a76c16d` (feat)
2. **Task 2: Install n10s on neo4j (deterministic pinned jar) + docker-compose wiring + smoke-verify test** - `72d7f3b` (feat)

_No TDD tasks in this plan; both were straightforward `type="auto"` scaffolding/wiring tasks._

## Files Created/Modified
- `dg-reasoner/Dockerfile` - python:3.11-slim + build-essential + openjdk-21-jre-headless (JRE 17 fallback per trixie unavailability) + uvicorn launch
- `dg-reasoner/requirements.txt` - pinned owlready2/rdflib/pyshacl/owlrl/neo4j per RESEARCH.md, unpinned fastapi/uvicorn/pytest, plus starlette<1.0.0 + httpx (test-transport pin, see Deviations)
- `dg-reasoner/app.py` - FastAPI app; module-level Neo4j driver from env; `GET /health` (probes neo4j with a 3s-timeout `RETURN 1`); stub `POST /reason/consistency` + `POST /shacl/validate` returning 501
- `dg-reasoner/tests/conftest.py` - registers the `integration` pytest marker, `neo4j_available()` helper, session-scoped `neo4j_driver` fixture that skips cleanly when unreachable
- `dg-reasoner/tests/test_health.py` - FastAPI TestClient asserts `/health` returns 200 + `status: ok`
- `dg-reasoner/tests/test_n10s_smoke.py` - `@pytest.mark.integration`: asserts n10s procedures registered (count > 0) and `graphconfig.init()` is callable
- `neo4j/Dockerfile` - `FROM neo4j:5.26` + `wget`-fetched `neosemantics-5.26.0.jar` into `/var/lib/neo4j/plugins/`
- `docker-compose.yml` - `neo4j` now `build: ./neo4j` with n10s procedure-allowlist env; new `dg-reasoner` service (internal-only); `DG_REASONER_URL` added to `data-service`

## Decisions Made
- **JRE substitution:** `openjdk-17-jre-headless` is not available in Debian trixie's apt repos (confirmed via live `apt-cache search` inside `python:3.11-slim`); substituted `openjdk-21-jre-headless` per the plan's explicit documented fallback. HermiT's Java floor is 1.5+, so this is a proven-safe substitution (also validated in the 820 spike).
- **starlette pin (test-only):** unpinned `fastapi` resolves to a `starlette>=1.0` release whose `TestClient` now depends on a new PyPI package (`httpx2`) instead of the long-established `httpx`. Rather than silently installing an unreviewed new package to satisfy a test-only transport dependency, pinned `starlette<1.0.0` and added `httpx` (already a vetted dependency elsewhere in this repo, used identically by `data-service`). This keeps the dependency surface to packages already trusted in this codebase.
- **n10s install method:** used the "(B) tiny custom Dockerfile" option from RESEARCH.md §3 rather than `NEO4J_PLUGINS` auto-download, for determinism. Confirmed `neo4j:5.26` lacks `curl` but has `wget` (checked live), so the fetch command uses `wget -q ... -O ...` instead of `curl`.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] openjdk-17-jre-headless unavailable on Debian trixie, substituted openjdk-21-jre-headless**
- **Found during:** Task 1 (Dockerfile creation + build verification)
- **Issue:** `python:3.11-slim`'s base OS is Debian trixie (13), whose apt repos no longer carry `openjdk-17-jre-headless` (confirmed via `apt-cache search openjdk` inside a live container — only 21/25 present).
- **Fix:** Used `openjdk-21-jre-headless` instead, exactly as the plan's `<action>` block explicitly authorized as the fallback. Documented via an inline Dockerfile comment.
- **Files modified:** `dg-reasoner/Dockerfile`
- **Verification:** `docker build ./dg-reasoner` exits 0; image built and ran successfully.
- **Committed in:** `a76c16d` (Task 1 commit)

**2. [Rule 3 - Blocking] starlette>=1.0's TestClient requires new package `httpx2`; pinned starlette<1.0 + added httpx instead**
- **Found during:** Task 1 (running `test_health.py` inside the built image — collection error: `RuntimeError: The starlette.testclient module requires the httpx2 package to be installed`)
- **Issue:** Unpinned `fastapi`/`starlette` resolved to `starlette==1.3.1` (a real, current PyPI release), whose `TestClient` now imports a new package `httpx2` rather than the historical `httpx`. Installing an unfamiliar new package purely to unblock a test felt like unnecessary and unreviewed dependency-surface growth, even though `httpx2` verified as a legitimate, actively-released PyPI package (not a typosquat).
- **Fix:** Pinned `starlette<1.0.0` (resolves to `fastapi==0.139.0` + `starlette==0.52.1`) and added `httpx` (already a proven, repo-wide dependency — `data-service/requirements.txt` uses it identically) so `TestClient` uses the established transport.
- **Files modified:** `dg-reasoner/requirements.txt`
- **Verification:** Rebuilt image; `pytest tests/test_health.py -q` → 1 passed.
- **Committed in:** `a76c16d` (Task 1 commit)

**3. [Rule 3 - Blocking] neo4j:5.26 base image has no `curl`, only `wget`**
- **Found during:** Task 2 (drafting `neo4j/Dockerfile` with the plan's suggested `curl`-based fetch)
- **Issue:** `docker run --rm neo4j:5.26 sh -c "which curl"` returned nothing — the image (Debian trixie based) ships `wget` but not `curl`.
- **Fix:** Rewrote the plugin-fetch `RUN` line to use `wget -q <url> -O <dest>` instead of `curl -fsSL`.
- **Files modified:** `neo4j/Dockerfile`
- **Verification:** `docker build ./neo4j` exits 0; jar confirmed present at `/var/lib/neo4j/plugins/neosemantics-5.26.0.jar` (~12.8MB) via `docker run ... ls -la`.
- **Committed in:** `72d7f3b` (Task 2 commit)

---

**Total deviations:** 3 auto-fixed (all Rule 3 - blocking issues discovered via live docker build/test, all within the plan's own documented discretion/fallback language)
**Impact on plan:** All three were necessary to make the plan's own verification commands pass; no scope creep, no architectural changes, no new unreviewed dependencies (httpx was already trusted; wget/openjdk-21 are OS-level substitutions for unavailable packages).

## Issues Encountered
- Bash tool's own network stack (Windows Git Bash / schannel) could not complete HTTPS handshakes (`CRYPT_E_NO_REVOCATION_CHECK`), but Docker's internal network stack worked fine — used throwaway `alpine`/`python` containers to confirm the exact `neo4j:5.26` image tag and the exact neosemantics `5.26.0` GitHub release asset URL before writing `neo4j/Dockerfile`, rather than guessing.
- Pre-existing `neo4j` container (with existing `neo4j_data` volume, likely containing the `v8-ui-smoke` project data referenced in STATE.md) was recreated in place by `docker compose up -d neo4j` — the named volume was preserved (compose `up` only replaces the container, not the volume), so no live data was lost.

## User Setup Required

None - no external service configuration required. (Neo4j/dg-reasoner both run locally under docker-compose with dev-safe default credentials, matching existing repo convention.)

## Next Phase Readiness
- `dg-reasoner/` package, pinned dependency set, and running internal-only service now exist for Plan 02 (translator) and Plan 03 (reasoning/SHACL routes) to build directly on top of — no further scaffolding needed.
- `data-service` carries `DG_REASONER_URL=http://dg-reasoner:8000`, ready for Plan 04's thin proxy route.
- Stub routes (`POST /reason/consistency`, `POST /shacl/validate`) declare the exact contract surface Plan 03 will fill in with real HermiT/pySHACL logic.
- No blockers. One thing worth a passing note for Plan 02/03: `neo4j` container image tag is now pinned to `5.26` (was floating `neo4j:5`) — any future compose changes to the neo4j image must keep this in sync with the neosemantics jar version.

---
*Phase: 821-dg-reasoner-sidecar-ontograph-metagraph-rdf-translation*
*Completed: 2026-07-11*

## Self-Check: PASSED

All 7 created files verified present on disk (dg-reasoner/Dockerfile, requirements.txt, app.py, tests/conftest.py, tests/test_health.py, tests/test_n10s_smoke.py, neo4j/Dockerfile). Both task commits (`a76c16d`, `72d7f3b`) verified present in git log.
