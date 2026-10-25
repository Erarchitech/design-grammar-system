---
phase: 1205-security-and-tenancy-release-gate
plan: "09"
subsystem: security
tags: [docker-compose, secrets-management, network-boundary, multi-user-profile, dockerignore]

requires:
  - phase: 1205-01
    provides: ".env key inventory (.env.example), secrets_policy known-default lists, owner-created .env"
provides:
  - "docker-compose.yml with every secret as a required ${VAR:?} interpolation (no literals, no fallbacks)"
  - "127.0.0.1 binding for 7474/7687/8000/8001/5678/9000/9001/11435; only 8080 and 8090 on all interfaces"
  - "docker-compose.multi-user.yml: DG_DEPLOYMENT=multi-user plus !reset of neo4j and n8n publishes"
  - "UI container (design-grammars) with no Neo4j/n8n/Speckle-token environment"
  - "data-service/.dockerignore excluding data/ and .env from image layers"
  - "data-service/tests/test_compose_boundary.py: static boundary test with induced-failure proofs"
affects: ["1205-15 (config.js/entrypoint cleanup)", "1205-18 (live rotation + boundary proof)", "1205-19 (owner multi-user checkpoint)"]

tech-stack:
  added: []
  patterns:
    - "Stdlib indentation parser for compose files (CRLF tolerant, !reset aware) instead of yaml.safe_load"
    - "Induced-failure tests: mutate the compose text and assert the same check functions fire"

key-files:
  created:
    - docker-compose.multi-user.yml
    - data-service/tests/test_compose_boundary.py
  modified:
    - docker-compose.yml
    - data-service/.dockerignore

key-decisions:
  - "Multi-user override uses the Compose !reset tag because ports are concatenated, not replaced, across -f files (correcting the RESEARCH merge claim); verified with Compose v2.40.3"
  - "Known-default literal check is scoped: 12345678/minioadmin may appear nowhere in the file, but bare usernames (neo4j, speckle) are only rejected as values of secret-named keys, since NEO4J_USER/POSTGRES_USER are legitimate non-secret values"
  - "Compose renders for verification use --env-file .env.example; the live .env was never opened or rendered"

patterns-established:
  - "Boundary tests name keys/services only in assert messages, never values"

requirements-completed: []  # ALGN12-18 and ALGN12-19 span many plans (live proof lands in 1205-18/19); intentionally NOT marked complete

coverage:
  - id: D1
    description: "Required-secret interpolation, loopback bindings, UI env cleanup, multi-user override (Task 1)"
    requirement: "ALGN12-18, ALGN12-19"
    verification:
      - kind: automated
        ref: "docker compose --env-file .env.example [-f docker-compose.multi-user.yml] config -q -- exit 0; JSON assertion printed ok (multi-user publishes only 8080/8090 on all interfaces, neo4j and n8n publish nothing)"
        status: pass
      - kind: automated
        ref: "empty untracked env file render exits 1 naming required variable NEO4J_PASSWORD"
        status: pass
      - kind: manual_procedural
        ref: "docker compose up -d with the owner .env: all 15 containers Up, data-service 200 on :8000 (after one restart, see Issues)"
        status: pass
    human_judgment: false
  - id: D2
    description: "Static compose/dockerignore boundary test (Task 2)"
    requirement: "ALGN12-18, ALGN12-19"
    verification:
      - kind: unit
        ref: "data-service/tests/test_compose_boundary.py -- 19 passed on host and 19 passed in-container"
        status: pass
    human_judgment: false

duration: ~25min
completed: 2026-09-29
status: complete
---

# Phase 1205 Plan 09: Compose Secrets, Loopback Bindings, and Multi-User Override Summary

**docker-compose.yml now requires every secret from the gitignored .env via `${VAR:?}` (including inside the three Speckle Postgres URLs), binds all internal ports to 127.0.0.1, and a new `docker-compose.multi-user.yml` uses `!reset` to withhold the Neo4j and n8n publishes and switch data-service to `DG_DEPLOYMENT=multi-user`; a 19-test static boundary test machine-checks it.**

## Accomplishments

- **D-10:** neo4j, dg-reasoner, data-service, n8n, speckle-postgres, speckle-minio, speckle-server and the webhook/fileimport services take their secrets as `${VAR:?set VAR in .env (see .env.example)}`. The committed Neo4j default, the MinIO defaults, the personal n8n login and the `speckle` Postgres password are gone from the file (`grep -c "12345678\|minioadmin"` returns 0). data-service gains `DG_SERVICE_TOKEN`, `DG_BOOTSTRAP_ADMIN_USER/PASSWORD` (required), `DG_DEPLOYMENT` (default `local`) and `DG_COOKIE_SECURE` (default `false`). Speckle read/write tokens remain optional `${VAR:-}`.
- **D-09:** 7474, 7687, 8000, 8001, 5678, 9000, 9001 and 11435 publish on `127.0.0.1` only. 8080 (UI) and 8090 (Speckle ingress) keep all-interface binding.
- **D-07/D-09:** `docker-compose.multi-user.yml` sets `ports: !reset []` on neo4j and n8n and `DG_DEPLOYMENT: multi-user` on data-service. A `config --format json` assertion confirms the merged multi-user render publishes only 8080 and 8090 on all interfaces.
- **n8n** now receives `DG_SERVICE_TOKEN`, `NEO4J_USER`, `NEO4J_PASSWORD` and `N8N_BLOCK_ENV_ACCESS_IN_NODE=false` (for the 1205-05 workflows). **design-grammars** receives only `DATA_SERVICE_URL` and `SPECKLE_BASE_URL` and depends only on data-service.
- **Image hygiene:** `data-service/.dockerignore` excludes `data/`, `.env`, `*.env`, `.pytest_cache/` (`tests/` stays in the image).
- **Test:** `test_compose_boundary.py` covers the port sets, required interpolations (every secret-named key, and each postgres URL), known-default literal/digest absence, UI env, n8n env, override, dockerignore, CRLF tolerance, and 7 induced-failure tests. Run against the pre-plan compose text, the same check functions report 10 binding, 37 required-secret and 18 known-default problems, confirming the checks are not vacuous.

## Task Commits

1. **Task 1: Compose secrets, bindings, UI env, multi-user override** - `ae1fa7a` (feat)
2. **Task 2: Static boundary test** - `8059da0` (test)

## Verification Results

- `docker compose --env-file .env.example -f docker-compose.yml config -q` -> exit 0; same with the multi-user override -> exit 0 and JSON assertion `ok`.
- `docker compose --env-file <empty tmp file> -f docker-compose.yml config -q` -> exit 1: "required variable NEO4J_PASSWORD is missing a value: set NEO4J_PASSWORD in .env (see .env.example)".
- `python -m pytest data-service/tests/test_compose_boundary.py -q` -> 19 passed (host).
- In-container: the new test was copied into the running container with `docker cp` (image not rebuilt), `pytest tests/test_compose_boundary.py` -> 19 passed. Full in-container baseline: **1207 passed, 1 skipped, 12 failed, 8 deselected** = the 1188 baseline plus the 19 new tests, with exactly the 12 known environmental failures (10 in test_cq3_attribute_of.py, test_repeat_sweep.py::test_llm_report_schema_has_no_shared_or_accuracy_fields, test_evidence_contract.py::...::test_never_raises_on_garbage_input). No regression.
- No render of the live `.env` was printed; `.env` was never opened.

## Live Stack State After Recreate

`docker compose up -d` (base file, local profile) recreated neo4j, dg-reasoner, data-service, n8n, ollama, speckle-minio and design-grammars; the rest were unchanged. Final state: all 15 containers Up; `curl http://localhost:8000/` -> 200 (data-service), UI :8080 -> 200, n8n /healthz -> 200, Neo4j browser :7474 -> 200. `docker ps` shows the loopback publishes (`127.0.0.1:5678`, `:7474`, `:7687`, `:8001`, `:9000-9001`, `:11435`) and all-interface only for 8080 and 8090. The multi-user override was validated statically only (not brought up; that is plan 1205-19).

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Test fixtures were CRLF-sensitive**
- **Found during:** Task 2
- **Issue:** `Path.read_text` normalises CRLF to LF, so mutation tests written with `\r\n` did not mutate and the first attempt failed; the parser's CRLF tolerance was untested.
- **Fix:** the base text fixture normalises to LF via bytes decoding, mutations use LF, and a dedicated `test_parser_is_crlf_tolerant` converts to CRLF and asserts an identical parse.
- **Files modified:** `data-service/tests/test_compose_boundary.py`
- **Committed in:** `8059da0`

### Notes

- The plan marks Task 2 `tdd="true"`, but its subject is the compose file produced by Task 1, so the test was written after Task 1 and its non-vacuity was proven by induced-failure tests plus a run against `HEAD~1:docker-compose.yml` (no separate RED commit).

## Issues Encountered

- **data-service exited on the first recreate** (exit 3, `ServiceUnavailable: neo4j:7687 connection refused`). Cause: neo4j was recreated in the same `up` and data-service opened its Neo4j connection at startup before Bolt was listening; `depends_on` has no health condition and data-service has no restart policy. `docker compose up -d data-service` brought it up cleanly. This is a pre-existing cold-start race, not caused by the interpolation change; not fixed here (out of scope). Recorded for 1205-18/19: a multi-user cold start will hit the same race.
- The running data-service image predates this plan's `.dockerignore` and does not contain the new test until the next rebuild (`docker compose build --no-cache data-service`); it was run in-container via `docker cp`.

## Known Follow-ups (handed to later plans)

- `ui-v2/entrypoint.sh` still falls back to `neo4jPassword: "${NEO4J_PASSWORD:-12345678}"` and `neo4jUser`/n8n defaults when the UI env is absent. With this plan's env cleanup the UI now always receives that literal in `config.js`. It matches the current live Neo4j password only as long as that value is unchanged; 1205-15 (D-12) removes credentials from `config.js` and 1205-18 rotates the live values, so these must land together or the UI's direct Neo4j calls will break after rotation.
- `.env.example`/`ui-v2` interplay is otherwise unchanged. Live rotation of the ten `PENDING_ROTATION_KEYS` remains 1205-18.

## Requirements

ALGN12-18 and ALGN12-19 are **not** marked complete: each spans several plans (live boundary proof in 1205-18/19, config.js cleanup in 1205-15, spec in 1205-16).

## Threat Flags

None. No new network endpoint or trust boundary beyond those in the plan's threat model (T-1205-09-01..04 mitigated by this plan; -05/-06 accepted as documented).

## Known Stubs

None.

## Self-Check: PASSED

Files found: `docker-compose.yml`, `docker-compose.multi-user.yml`, `data-service/.dockerignore`, `data-service/tests/test_compose_boundary.py`. Commits `ae1fa7a` and `8059da0` found in git log.
