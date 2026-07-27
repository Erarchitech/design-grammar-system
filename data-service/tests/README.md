# data-service/tests — Run Story

Two tiers. Both are pytest, both live under this directory — the split is
about **where** they run, not a separate framework or config file.

## Unit tier (host, no container, no Neo4j)

```bash
python -m pytest data-service/tests/ -q
```

Run from the repository root on the host. Needs no container and no Neo4j —
this is the per-commit gate.

**Measured 2026-07-27:** 492 passed, 4 failed, 1 skipped, 1 deselected in
25.93s (real 26.9s).

The 4 failures are `test_dg_context.py`'s pre-existing Neo4j-dependent tests
(`TestContextEndpoints::test_post_assemble_returns_200_for_valid_type`,
`TestContextEndpoints::test_get_debug_matches_post_assemble_body`,
`TestDeterminism::test_repeated_assemble_calls_are_byte_identical`,
`TestDeterminism::test_get_debug_and_post_assemble_are_equal_for_graph_query`)
— **they fail rather than skip** when run from the host, because the `neo4j`
hostname only resolves inside the compose network (see Integration tier
below). This is a known, accepted baseline, not a regression to chase down
before every commit. Phase 37's structural checks (`test_cg_structure_checks.py`,
added in a later 37 plan) join this same category: any test that needs a real
Cypher pattern-match against live data cannot run from the host.

## Integration tier (compose network, live Neo4j)

```bash
docker compose exec data-service python -m pytest tests/ -q
```

Requires the compose network — `neo4j` only resolves as a hostname inside it.
Run this before opening a PR that touches Neo4j-reading/writing code, and
after every Phase 37 plan wave per `37-VALIDATION.md`'s sampling rate.

**Measured 2026-07-27:** 474 passed, 1 skipped, 1 deselected in 6.70s
(real 8.2s including `docker compose exec` overhead).

**Known gotcha — image staleness:** the running `data-service` container is
built from whatever `data-service/` snapshot was last baked into its image
(same class of issue as the documented `design-grammars` `--no-cache`
gotcha). New test files added on the host (like this phase's `cg_fixtures.py`
/ `consult_cassette.py` / `test_cg_fixtures.py`) are **not** visible inside
the container until it is rebuilt — the container has no live bind-mount for
`data-service/tests/`. That is why the integration-tier count above (476
collected) is lower than the host-tier count (498 collected): the container's
last build predates this plan's new files. Rebuild before relying on the
container run to cover new test files:

```bash
docker compose build --no-cache data-service && docker compose up -d data-service
```

## Phase 37 additions

- `cg_fixtures.py` — parser-faithful Frame cgContextJson v1 envelope builders
  (`frame_cg_context()` plus three mutated variants). No Neo4j, no `app`
  import — pure data.
- `consult_cassette.py` — a deterministic, network-free `LLMAdapter` double
  (`ConsultCassetteAdapter`) for the `/computgraph/consult` path. No live LLM
  call, no `live` pytest marker.
- `FIXTURE_PROJECT` isolation convention — `cg_fixtures.py` publishes under
  `"p37-structure"`, distinct from `test_computgraph_publish.py`'s
  `GOLDEN_PROJECT` (`"p1"`). **Rule: any test that publishes into a live
  Neo4j must scope itself to a project string no other suite uses**, so
  suites sharing one Neo4j instance never cross-contaminate each other's node
  counts or assertions.

## Phase 39 additions

Two host-tier modules and one integration module, all for the DesignState
Auto-Validation watcher (`dsav_watcher.py`).

- `dsav_fixtures.py` — DesignState v2 envelope builders, `dg-reasoner` SHACL
  verdict builders, and `DsavFixtureSession`, a duck-typed Neo4j session that
  dispatches by *query identity* (`poll_once()` issues several distinct
  queries per tick, unlike the single-query doubles elsewhere in this suite).
  No pytest import, no Neo4j, no `app` import — pure data.
- `test_dsav_watcher.py` (host tier, 18 tests) — the whole capture → debounce
  → coalesce → verdict → complete/fail state machine with zero live Neo4j,
  zero thread and zero `time.sleep`.
- `test_designstate_capture.py` (host tier, 22 tests) — the
  `POST /designstate/capture` auth/project-binding/payload-cap matrix, the
  `lifespan` watcher wiring, and a pinned-source-hash guard proving
  `store_validation_run` is byte-for-byte unchanged.
- `test_dsav_live_loop.py` (**integration + live**, 6 tests) — the live-Docker
  evidence driver. It scrubs shared live rows; see its own section below.
- `test_dsav_publish_leg.py` (**integration + live tiers**, 1 test) — the
  single deliberate Speckle publish. **It writes to a real Speckle server.**
  See its own section below before running it.

### `p39-autoval` fixture-project reservation

Phase 39 reserves the live-Neo4j project string **`p39-autoval`**
(`dsav_fixtures.FIXTURE_PROJECT`), per the Phase 37 rule above. It must stay
distinct from `p37-structure` (`cg_fixtures.py`), `p1`
(`test_computgraph_publish.py`'s `GOLDEN_PROJECT`) and `default-project`;
`test_dsav_live_loop.py` asserts that distinctness at import time so a
rename cannot silently start trampling another suite's rows.

### `test_dsav_live_loop.py` — extra requirements

- **It is `live`-marked, so select it explicitly:**

  ```bash
  docker compose exec -T data-service python -m pytest \
      tests/test_dsav_live_loop.py -q -m "integration and live"
  ```

  The marker was added after Phase 39 Wave 4 (operator-authorized at the 39-04
  checkpoint). This module's `live_session` fixture **deletes every
  `:ValidationRun` and `:IntegrationConfig` scoped to `p39-autoval`** at both
  setup and teardown. While it was `integration`-only, a routine
  `pytest tests/ -q` collected it and silently destroyed the published run row
  Wave 4 had just measured. `live` makes running it a deliberate act — the
  same convention `test_dsav_publish_leg.py` uses.
- **Needs the full compose stack, including `dg-reasoner`.** Unlike the other
  integration tests it does not only need Neo4j: it drives HTTP against the
  running uvicorn process (whose `lifespan` owns the watcher daemon) and
  closes the loop through a real SHACL round-trip to the sidecar.
- **The image must be rebuilt before it can see the new files** — the same
  staleness gotcha documented above, but load-bearing here: a stale image
  runs neither the new tests nor the `lifespan`-started watcher they measure.
- **It writes its evidence to `/app/data/dsav-evidence.json`**, not into the
  repository, because `/mnt/repo` is mounted read-only. The host sees it at
  `data-service/data/dsav-evidence.json` (a gitignored directory that also
  holds connector credentials and encrypted LLM settings — copy out only the
  evidence file, never commit anything else from there). The path is
  overridable via `DSAV_EVIDENCE_PATH`; the HTTP target via
  `DSAV_TARGET_BASE_URL`.
- **It takes ~3m10s**, most of it deliberate wall-clock: a 60-second
  runs-per-minute measurement window plus two rate-limit-window drains.
- **Restart `data-service` between consecutive measured runs.** The watcher's
  rate-limit window lives in that process's memory (D-15), so a re-run inside
  60 seconds can start against a partly-full limiter.
- On the **host** tier this module produces 6 errors rather than skips, the
  same convention as `test_cg_structure_checks.py` — `neo4j` does not resolve
  there. It deliberately writes no evidence artifact when nothing was
  measured.

### `test_dsav_publish_leg.py` — mints a real Speckle version

This is the only module in the repository that creates a **real version on the
Speckle server**. Everything above it runs persist-only.

- **It is `live`-marked, and that marker is the safety mechanism.** `conftest.py`
  deselects every `live` item unless the caller passes an explicit `-m`
  expression, so a bare `pytest tests/ -q` can never mint a Speckle version by
  accident. Note the corollary: a broad `-m live` (e.g. for the recognition
  eval) **will** collect it. Select it by path when you mean it:

  ```bash
  docker compose exec -T data-service python -m pytest \
      tests/test_dsav_publish_leg.py -q -m "integration and live"
  ```

- **It turns the per-project `publishEnabled` flag on for exactly one capture**
  and resets it in unconditional teardown, then deletes both the
  `provider:'AutoValidation'` and `provider:'Speckle'` `IntegrationConfig` rows
  for `p39-autoval`. Teardown asserts zero `AutoValidation` rows remain: leaving
  the flag on would turn every future capture into a Speckle version.
- **It publishes into whichever Speckle project the dev stack already has
  configured.** `p39-autoval` is a synthetic string with no Speckle project of
  its own, so the module discovers an existing `provider:'Speckle'`
  `IntegrationConfig` row, proves the project and base model are readable with
  the write token, and points the fixture project at that same real Speckle
  project. One near-empty version is appended to that project's `dg-validation`
  model per run.
- **If Speckle is unconfigured it fails loudly rather than skipping**, with
  `speckle_config_missing` or `speckle_token_missing` in the message, and
  records a `blocked` evidence entry. No number is ever synthesized and Speckle
  is never mocked.
- **Its evidence goes to `/app/data/dsav-publish-evidence.json`**
  (`DSAV_PUBLISH_EVIDENCE_PATH`) — a separate file, so it can never overwrite
  the Wave 3 `dsav-evidence.json`. Speckle project and version ids are
  recorded; tokens never are.
- Phase 39 ran it **once**, on 2026-07-27, minting Speckle version
  `2ab708e884`. Re-running it mints another one.

**Measured 2026-07-27 (both tiers, after rebuilding the image):**

| Tier | Command | Result |
|------|---------|--------|
| Host | `python -m pytest data-service/tests/ -q` | 699 passed, 4 failed, 1 skipped, 1 deselected, 31 errors in 36.35s |
| Container | `docker compose exec -T data-service python -m pytest tests/ -q` | 734 passed, 1 skipped, 1 deselected in 204.56s |
| Container (Wave 4, publish leg added) | `docker compose exec -T data-service python -m pytest tests/ -q` | 734 passed, 1 skipped, **2** deselected in 206.17s |
| Container (Wave 4, after `live`-marking the live loop) | `docker compose exec -T data-service python -m pytest tests/ -q` | **728** passed, 1 skipped, **8** deselected in **8.88s** |
| Container (live loop, selected) | `… python -m pytest tests/test_dsav_live_loop.py -q -m "integration and live"` | 6 passed in 192.74s |
| Container (publish leg, selected) | `… python -m pytest tests/test_dsav_publish_leg.py -q -m "integration and live"` | 1 passed in 7.32s |

The default in-container run drops from 734 to **728 passed** and from 2 to
**8 deselected**: the six `test_dsav_live_loop.py` tests moved out of default
collection. That is the intended effect of the `live` marker, not a
regression — they still pass when selected, and the bare run is now 23×
faster because those six were nearly all of its wall-clock.

Both tiers now collect **736** — the container has caught up with the host.
The host tier's 4 failures are the documented `test_dg_context.py` baseline;
its 31 errors are the 25 pre-existing `neo4j`-DNS integration errors plus
this phase's 6 live-loop tests. All 36 resolve inside the compose network,
which is why the container tier is fully green.

## The runner finding

There is no standing CI job. `.github/` has no `workflows/` directory, so
neither tier runs automatically on push or PR — this is a known, accepted
gap, not an oversight to silently work around. Until a CI job exists, a
developer must run both commands above manually before opening a PR:

```bash
python -m pytest data-service/tests/ -q
docker compose exec data-service python -m pytest tests/ -q
```
