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

## The runner finding

There is no standing CI job. `.github/` has no `workflows/` directory, so
neither tier runs automatically on push or PR — this is a known, accepted
gap, not an oversight to silently work around. Until a CI job exists, a
developer must run both commands above manually before opening a PR:

```bash
python -m pytest data-service/tests/ -q
docker compose exec data-service python -m pytest tests/ -q
```
