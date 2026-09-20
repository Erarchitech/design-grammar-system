---
phase: 1200-contract-status-vocabulary-evidence-envelope-and-golden-fixt
plan: 02
subsystem: testing
tags: [golden-fixture, neo4j-seed, docker-compose, jsonschema, de-01]

# Dependency graph
requires:
  - phase: 1200-01
    provides: spec/EVIDENCE-CONTRACT.md (8-status vocabulary, D-09/D-10/D-11 freeze policy), spec/evidence-contract.schema.json ($defs.CanonicalStatus)
provides:
  - fixtures/golden/fixture.json — the one frozen cross-service fixture (one rule, all four Metagraph atom types, two mixed-outcome objects, one zero-binding object, a three-kind Design State, a geometry reference, an ordered expectedOutcomes table)
  - fixtures/golden/MANIFEST.md — freeze record (v1.0.0), pre-declaring the by-design C#-leg unsupported/error ObjectPropertyAtom result
  - fixtures/golden/canonical-vectors.json — 5 verified SHA-256 golden vectors (3 scalarTuple, 2 canonicalJson) for the canonicalization convention
  - fixtures/golden/seed.cypher — scripted, idempotent Neo4j seed path for the persisted-replay DE-01 leg
  - dg-reasoner container read-only access to fixtures/golden/ via a new docker-compose.yml mount
  - jsonschema>=4.20,<5 pinned in both data-service and dg-reasoner requirements.txt
affects: [1200-03, 1200-04, 1200-05, 1201, 1202, 1203, 1204, 1205]

# Tech tracking
tech-stack:
  added: ["jsonschema>=4.20,<5 (data-service, dg-reasoner)"]
  patterns:
    - "Golden-vector duplication (not shared-file import) for canonical-hash test data, mirroring DgIdMintingService/compute_dg_id convention"
    - "Static, checked-in, literal-value Cypher seed script (never a parameterized runtime query itself), matching test/seed_designstates.cypher / test/seed_validation_run.cypher"
    - "Narrow, single-purpose read-only bind mount (./fixtures:/app/fixtures:ro) rather than a broad repo-root mount, for a sidecar container with no existing repo access"

key-files:
  created:
    - fixtures/golden/fixture.json
    - fixtures/golden/MANIFEST.md
    - fixtures/golden/canonical-vectors.json
    - fixtures/golden/seed.cypher
  modified:
    - docker-compose.yml
    - data-service/requirements.txt
    - dg-reasoner/requirements.txt

key-decisions:
  - "OBJ_GOLD_EMPTY assigned class ex:Site (not ex:Building) so the rule's ClassAtom structurally never matches it, making no_population an asserted rather than merely-defined outcome"
  - "ObjectPropertyAtom (R_GOLD_HEIGHT_MAX_75_V_A4) seeded at the data level in both fixture.json and seed.cypher; MANIFEST.md pre-declares the C# leg's expected unsupported/error result as by-design, not a defect, per Phase 1201 ALGN12-05's future scope"
  - "canonical-vectors.json digests computed programmatically (hashlib.sha256 over UTF-8 bytes) and verified by the plan's own recompute-and-compare check, never hand-invented"
  - "docker-compose.yml dg-reasoner mount kept narrow (./fixtures:/app/fixtures:ro), explicitly rejecting a broader /mnt/repo-style mount per the plan's threat disposition (T-1200-08, accept/low)"

patterns-established:
  - "fixtures/golden/ is the single source of truth for the DE-01 cross-service fixture; per-service copies are forbidden (D-09) and no plan should create one"

requirements-completed: [ALGN12-03]

coverage:
  - id: D1
    description: "fixtures/golden/fixture.json contains exactly one Rule with four Atom entries whose type set is {ClassAtom, DataPropertyAtom, BuiltinAtom, ObjectPropertyAtom}, two mixed-outcome objects plus a zero-binding no_population case, a three-kind Design State, a geometry reference, and an ordered expectedOutcomes table"
    requirement: "ALGN12-03"
    verification:
      - kind: other
        ref: "1200-02-PLAN.md Task 1 automated check (python shape/ordering assertions + grep for ObjectPropertyAtom/1201/1.0.0 in MANIFEST.md) — ran directly, passed"
        status: pass
    human_judgment: false
  - id: D2
    description: "fixtures/golden/canonical-vectors.json holds 5 fixed input/expected-digest pairs (3 scalarTuple, 2 canonicalJson) with every sha256Upper a real, recomputed SHA-256 uppercase hex digest"
    requirement: "ALGN12-03"
    verification:
      - kind: other
        ref: "1200-02-PLAN.md Task 1 automated check (hashlib.sha256 recompute-and-compare over every vector) — ran directly, passed"
        status: pass
    human_judgment: false
  - id: D3
    description: "fixtures/golden/seed.cypher projects the fixture into Neo4j with a boxed PURPOSE/EXECUTION METHOD/DEV DATABASES ONLY header, an idempotent DETACH DELETE teardown, >=8 MERGE statements, project scoping on every node-creating statement, and no evidenceEnvelopeJson on the seeded Run"
    verification:
      - kind: other
        ref: "1200-02-PLAN.md Task 2 automated check (grep + python statement-parsing assertion) — ran directly, passed; MERGE count 34"
        status: pass
    human_judgment: false
  - id: D4
    description: "docker-compose.yml's dg-reasoner service gains a narrow ./fixtures:/app/fixtures:ro mount; jsonschema>=4.20,<5 pinned in both data-service and dg-reasoner requirements.txt"
    verification:
      - kind: other
        ref: "1200-02-PLAN.md Task 3 automated check (python regex block-extraction + grep count) — ran directly, passed"
        status: pass
      - kind: manual_procedural
        ref: "docker compose up -d dg-reasoner && docker compose exec -T dg-reasoner test -f /app/fixtures/golden/fixture.json"
        status: unknown
    human_judgment: true
    rationale: "Docker Desktop's engine was not running in the execution environment this session (docker CLI present, daemon unreachable at the named pipe); the live in-container mount round-trip could not be executed. The compose-file change is mechanically verified correct and mirrors the existing ./ontology:/app/ontology:ro line exactly, but a human with a running Docker Desktop must confirm the live check before this is treated as fully closed."

duration: ~15min
completed: 2026-09-20
status: complete
---

# Phase 1200 Plan 02: Golden Fixture, Seed Script, and Fixture Reachability Summary

**Frozen `fixtures/golden/` cross-service fixture (one rule, all four Metagraph atom types including the deliberately-unsupported `ObjectPropertyAtom`, two mixed-outcome objects, a zero-binding `no_population` object, a three-kind Design State, a geometry reference) plus its Neo4j seed script, freeze manifest, 5 verified canonical-hash golden vectors, and the config wiring (`docker-compose.yml` fixture mount + `jsonschema` pins) that makes it reachable from all four DE-01 legs.**

## Performance

- **Duration:** ~15 min
- **Started:** 2026-09-20T07:35:17Z
- **Completed:** 2026-09-20T07:42:22Z
- **Tasks:** 3
- **Files modified:** 7 (4 created, 3 modified)

## Accomplishments
- Created `fixtures/golden/fixture.json`: one rule (`R_GOLD_HEIGHT_MAX_75_V`), all four atom types (`ClassAtom`, `DataPropertyAtom`, `BuiltinAtom` using the C#-supported `swrlb:greaterThan` predicate, and `ObjectPropertyAtom` present at the data level), three objects (`OBJ_GOLD_PASS` expecting `passed`, `OBJ_GOLD_FAIL` expecting `failed`, `OBJ_GOLD_EMPTY` — of a non-matching class — expecting `no_population`), a three-kind Design State (`ObjState`/`ParamState`/`PropState` via `HAS_STATE`), a geometry reference (Speckle object id + bounding box, not inline mesh), and an `expectedOutcomes` table ordered lexicographically by `objectId`
- Created `fixtures/golden/MANIFEST.md`: `FIXTURE_VERSION 1.0.0`, freeze date, a change-reason log table, the freeze policy (content changes require a version bump; Phases 1201-1205 verify against it and do not edit it), an up-front "Expected non-results by design" section naming the `ObjectPropertyAtom`/Phase 1201/`ALGN12-05` non-result explicitly, and a per-leg reachability table
- Created `fixtures/golden/canonical-vectors.json`: 5 golden vectors (3 `scalarTuple` including the reproduced shipped dgId vector plus two of the fixture's own object dgIds; 2 `canonicalJson` exercising key ordering, integer/decimal formatting, and NFC normalization) — every `sha256Upper` computed via real `hashlib.sha256` over UTF-8 bytes and verified by recompute-and-compare
- Created `fixtures/golden/seed.cypher`: boxed PURPOSE/EXECUTION METHOD/`DEV DATABASES ONLY` header matching the `test/seed_*.cypher` precedent, an idempotent `MATCH (n {project:'DG-1200-GOLDEN'}) DETACH DELETE n` teardown, 34 `MERGE` statements (Rule, 4 Atoms, Vars/Literals, HAS_BODY/ARG edges, 3 Objects with dgId/cgId, the 3-kind DesignState composition, and a Run node), every statement scoped to `project: 'DG-1200-GOLDEN'`, `evidenceEnvelopeJson` deliberately left unset on the seeded Run, and an explicit in-file note requiring parameterized Cypher from any executor of fixture-derived values
- Wired reachability: added `./fixtures:/app/fixtures:ro` to the `dg-reasoner` service in `docker-compose.yml` (narrow mount, styled exactly like the adjacent `./ontology:/app/ontology:ro`), and pinned `jsonschema>=4.20,<5` in both `data-service/requirements.txt` and `dg-reasoner/requirements.txt`

## Task Commits

Each task was committed atomically:

1. **Task 1: Create the golden fixture, its manifest, and the canonical-hash golden vectors** - `1f443d7` (feat)
2. **Task 2: Write the Neo4j seed script for the persisted-replay leg** - `d68869e` (feat)
3. **Task 3: Make the shared fixture reachable — dg-reasoner mount and jsonschema pins** - `2ec49e8` (feat)

## Files Created/Modified
- `fixtures/golden/fixture.json` - the frozen cross-service fixture
- `fixtures/golden/MANIFEST.md` - freeze record and by-design non-result disclosure
- `fixtures/golden/canonical-vectors.json` - 5 verified canonical-hash golden vectors
- `fixtures/golden/seed.cypher` - scripted Neo4j seed path for the persisted-replay leg
- `docker-compose.yml` - added the dg-reasoner `./fixtures:/app/fixtures:ro` mount
- `data-service/requirements.txt` - pinned `jsonschema>=4.20,<5`
- `dg-reasoner/requirements.txt` - pinned `jsonschema>=4.20,<5`

## Decisions Made
- `OBJ_GOLD_EMPTY` is class `ex:Site` (not `ex:Building`) so the rule's `ClassAtom` structurally never matches it — the `no_population` outcome is asserted by construction, not merely labeled.
- The `BuiltinAtom` uses `swrlb:greaterThan`, confirmed present in `DG/src/DG.Core/Validation/RuleEvaluator.cs`'s `EvaluateBuiltin` switch, so the pass/fail objects genuinely evaluate rather than throwing `NotSupportedException`.
- `ObjectPropertyAtom` is included in both `fixture.json` and `seed.cypher` at the data level per the plan's explicit prohibition against removing it to dodge an `unsupported` result — `MANIFEST.md`'s "Expected non-results by design" section is the disclosure mechanism.
- The `dg-reasoner` mount is deliberately narrow (`./fixtures` only), not the broader `/mnt/repo` pattern `data-service` already uses — matches the plan's explicit instruction and the threat model's T-1200-08 disposition (accept/low, narrower-than-data-service).

## Deviations from Plan

None in the produced artifacts — Tasks 1, 2, and 3 were executed exactly as specified, and all *static* automated verify/acceptance criteria in the plan passed on first attempt (fixture shape assertions, canonical-vector digest recomputation, seed-script grep/statement-parsing checks, compose block extraction, jsonschema grep counts).

**One environment-driven partial exception, disclosed rather than silently skipped:** Task 3's `<verify>` block includes a live step (`docker compose up -d dg-reasoner && docker compose exec -T dg-reasoner test -f /app/fixtures/golden/fixture.json`). Docker Desktop's engine was not running in this execution environment this session — the `docker`/`docker compose` CLI binaries are present and functional (`docker compose version` succeeds), but the daemon is unreachable at its named pipe (`open //./pipe/dockerDesktopLinuxEngine: The system cannot find the file specified`), and no GUI application can be launched from this shell to start it. This is an environment gate, not a code defect: the `docker-compose.yml` edit is mechanically verified correct (regex-extracted `dg-reasoner` block contains `./fixtures:/app/fixtures:ro`; diff is a clean 4-line insertion), and it copies the exact style of the pre-existing `./ontology:/app/ontology:ro` line the plan required. The live in-container round-trip is recorded as `status: unknown` / `human_judgment: true` in this SUMMARY's coverage block (D4) rather than asserted as passed. No deviation-rule fix was attempted or needed — there is no code path to auto-fix a stopped local Docker Desktop application.

## Issues Encountered
None beyond the Docker Desktop environment gate documented above. One transient tooling issue during authoring (not shipped in any committed artifact): `python -c` invocations without an explicit `encoding='utf-8'` argument to `open()` mis-decoded the non-ASCII characters in `canonical-vectors.json` on this Windows console (default cp1251 codepage), producing false digest mismatches during self-authored verification. Re-running the identical check with `encoding='utf-8'` explicit confirmed all 5 digests are correct; the shipped file and its digests were never wrong, only my first ad-hoc verification command's file-reading was.

## Next Phase Readiness
- `fixtures/golden/fixture.json`, `MANIFEST.md`, `canonical-vectors.json`, and `seed.cypher` are committed and ready for plans 1200-03 (envelope wiring/persistence), 1200-04 (DG.Core Contracts DTOs + canonicalization helper, which duplicates the canonical-vectors.json literals into `DG.Tests`), and 1200-05 (the DE-01 runner that drives all four legs against this fixture).
- The `dg-reasoner`/`data-service` fixture-reachability config changes are committed; a human with a running Docker Desktop should confirm the live `docker compose exec -T dg-reasoner test -f /app/fixtures/golden/fixture.json` check before 1200-05's DE-01 runner is exercised live against the containerized `dg-reasoner` leg. `data-service`'s existing `.:/mnt/repo:ro` mount already reaches `fixtures/golden/` with no change required.
- No blockers for continuing to 1200-03.

---
*Phase: 1200-contract-status-vocabulary-evidence-envelope-and-golden-fixt*
*Completed: 2026-09-20*

## Self-Check: PASSED

All created files and task commit hashes verified present on disk and in git log:
- FOUND: fixtures/golden/fixture.json
- FOUND: fixtures/golden/MANIFEST.md
- FOUND: fixtures/golden/canonical-vectors.json
- FOUND: fixtures/golden/seed.cypher
- FOUND: 1f443d7 (Task 1 commit)
- FOUND: d68869e (Task 2 commit)
- FOUND: 2ec49e8 (Task 3 commit)
