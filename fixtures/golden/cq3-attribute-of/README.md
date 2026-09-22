# fixtures/golden/cq3-attribute-of/ — CQ3 Bidirectional Bridge Fixture

**Added:** Phase 1203 plan 06 (D-14), requirement ALGN12-14.

## What this is

A dedicated, single-triple fixture demonstrating that the rule–parameter bridge
(`ATTRIBUTE_OF`, added by Phase 1203-04) is queryable in **both directions** —
forward (rule to its governing parameter) and reverse (parameter back to the
rule that governs it) — against a real Neo4j graph, project-scoped.

This is the phase's exit evidence for the ROADMAP gate reading "both query
directions are evidenced." Forward alone would not close that gate: the
reverse direction (parameter to governing rule) is precisely what
`inputBindings` as a config file could never answer on its own, and is the
concrete capability `ATTRIBUTE_OF` adds once persisted in the graph.

## Traceability to PAPER-C-032

This fixture reproduces the exact triple named in
`docs/reviews/theory-implementation-alignment/evidence/paper-claims.json`'s
`PAPER-C-032` entry (paper location P125, T02 CQ3):

> "CQ3 is demonstrated by a single row tracing
> `R_BUILDING_MIN_DISTANCE_12_V`/`A2`/`hasDistanceM` to parameter `SepDist` of
> type `Variable`."

The seeded identifiers (`R_BUILDING_MIN_DISTANCE_12_V`, the `A2`
`DataPropertyAtom` carrying `hasDistanceM`, and the `SepDist` parameter of
`paramKind: 'Variable'`) are reproduced verbatim from that claim, not
approximated.

**Scope disclaimer (preserved from the manuscript's own claim, per
`PAPER-C-032`'s `required_semantics`):** this evidence demonstrates that this
fixture's bridge is **populated and queryable** — it records ComputGraph
structure. It does **not** claim general design-space exploration capability,
solver equivalence, or executable design semantics. Treat a passing run here
as proof of representation, nothing wider.

## Project namespace

Every seeded node lives under `project: 'DG-1203-CQ3'` — a namespace used by
no other fixture under `fixtures/golden/`. This makes cross-project isolation
demonstrable: running either query below with a different project value
returns zero rows, proving the graph enforces per-project scoping rather than
merely never having collided by chance.

## Relationship to `fixtures/golden/fixture.json` — this is a SIBLING, not an edit

This fixture is additive and separate from the frozen `fixtures/golden/fixture.json`
(1200 D-11, `../MANIFEST.md`'s freeze policy). `fixture.json`, `seed.cypher`,
and `canonical-vectors.json` are untouched by this fixture — verified by
`git diff --exit-code --quiet fixtures/golden/fixture.json`. This mirrors the
precedent `fixtures/golden/parser/` (Phase 1201 plan 04) and
`fixtures/golden/replay/` (Phase 1202) both set: a new corpus lives in its own
subdirectory, under its own lighter change-reason discipline, rather than by
editing the frozen trio to make a later phase's own gate pass.

## Seeding method — graph-level, not via the publish path

**`seed-cq3.cypher` creates the `ATTRIBUTE_OF` edge directly as graph-level
fixture data.** It does not invoke `data-service`'s
`computgraph_publish.publish_structure` (the `inputBindings` ->
`_attribute_of_from_bindings` -> `_publish_attribute_of` derivation path).

This is a deliberate scoping choice, stated plainly per this fixture's own
prohibition against implying otherwise:

- **Derivation** (that `inputBindings` correctly resolves a rule to its bound
  parameter names, and that `_publish_attribute_of` correctly MERGEs the
  resulting edge from a live publish) is covered by Phase 1203-04's tests in
  `data-service/tests/test_computgraph_publish.py`, specifically:
  - `test_attribute_of_forward_query_returns_governing_parameter_name`
  - `test_attribute_of_reverse_query_returns_governing_rule_and_atom`
  - `test_attribute_of_cross_project_isolation_no_edge`
  - `test_attribute_of_republish_is_idempotent`
- **Queryability** (that once the edge exists in a real Neo4j graph — however
  it got there — both the forward and reverse query shapes return the correct
  single row, matching the manuscript's own recorded claim shape) is covered
  **here**, by this fixture and `data-service/tests/test_cq3_attribute_of.py`.

Neither artifact is presented as covering the other's claim. Together they
evidence the full path: derivation (1203-04) + queryability (this fixture).

The seeded edge's shape mirrors exactly what `_publish_attribute_of` writes —
same MATCH pattern (`Rule` by `Rule_Id`+`project`, `HAS_BODY`-then-type-filtered
`Atom`, `Parameter` by `cgId`+`definitionId`+`project`), same provenance
properties (`derivedFromRuleId`, `source`, `determinability`) — so a query
written against this fixture is a query that would work against real
published data.

## How to load the fixture

Dev databases only:

```bash
cypher-shell -a bolt://localhost:7687 -u neo4j -p <password> -f fixtures/golden/cq3-attribute-of/seed-cq3.cypher
```

Or against the running compose stack (`MSYS_NO_PATHCONV=1` required on Git
Bash for `docker exec`/`cp` absolute-path rewriting):

```bash
MSYS_NO_PATHCONV=1 docker compose exec -T neo4j cypher-shell -u neo4j -p 12345678 -f /dev/stdin < fixtures/golden/cq3-attribute-of/seed-cq3.cypher
```

Teardown (idempotent, run before re-seeding or to remove entirely):

```cypher
MATCH (n {project: 'DG-1203-CQ3'}) DETACH DELETE n
```

## Forward query — rule to governing parameter

Starts from the rule id and project, traverses `HAS_BODY` to the atom
filtered on `type = 'DataPropertyAtom'`, then `ATTRIBUTE_OF` to the parameter.

```cypher
MATCH (r:Rule {Rule_Id: 'R_BUILDING_MIN_DISTANCE_12_V', project: 'DG-1203-CQ3'})
MATCH (r)-[:HAS_BODY]->(a:Atom {type: 'DataPropertyAtom'})
MATCH (a)-[:ATTRIBUTE_OF]->(p:Parameter)
RETURN p.parameterName AS parameterName, p.paramKind AS parameterKind, p.cgId AS parameterCgId
```

**Expected: exactly one row** — `parameterName: "SepDist"`,
`parameterKind: "Variable"`, `parameterCgId: "cg:1:param:cq3_SepDist"`.

## Reverse query — parameter to governing rule

Starts from the parameter's key, traverses `ATTRIBUTE_OF` backwards to the
atom and `HAS_BODY` backwards to the rule.

```cypher
MATCH (p:Parameter {cgId: 'cg:1:param:cq3_SepDist', definitionId: 'cq3-fixture.gh', project: 'DG-1203-CQ3'})
MATCH (a:Atom)-[:ATTRIBUTE_OF]->(p)
MATCH (r:Rule)-[:HAS_BODY]->(a)
RETURN r.Rule_Id AS ruleId, a.Atom_Id AS atomId, a.type AS atomType
```

**Expected: exactly one row** — `ruleId: "R_BUILDING_MIN_DISTANCE_12_V"`,
`atomId: "R_BUILDING_MIN_DISTANCE_12_V_A2"`, `atomType: "DataPropertyAtom"`.

## Cross-project isolation check

Re-run either query above substituting `project: 'DG-1203-CQ3-OTHER'` (a
project that was never seeded). **Expected: zero rows** for both directions.

## Expectation source of truth

`expected-cq3.json` in this directory captures all of the above as committed
data — the forward query, reverse query, their exact expected single rows,
and the cross-project zero-row expectation — read by
`data-service/tests/test_cq3_attribute_of.py` so the automated test asserts
against a committed expectation file rather than literals embedded in test
code.

## Automated test

`data-service/tests/test_cq3_attribute_of.py` loads `expected-cq3.json` and
seeds an in-memory graph mirroring `seed-cq3.cypher`'s shape (following the
`FakeGraph`/`FixtureSession` mocking style established in
`data-service/tests/test_computgraph_publish.py`), then asserts:

- the forward query direction returns exactly one row matching the expected
  parameter name/kind/cgId;
- the reverse query direction returns exactly one row matching the expected
  rule id and atom id/type;
- the same queries against a different project return zero rows.

## Freeze status

This fixture is **not frozen** the way `fixture.json` is. It is this plan's
own deliverable. A later phase may extend it without a version-bump ceremony,
but should log the change in the Change-Reason Log below — the same "log why"
discipline `fixtures/golden/parser/README.md` and
`fixtures/golden/replay/README.md` established.

## Change-Reason Log

| Date | Reason | Changed by |
|---|---|---|
| 2026-09-22 | Initial fixture — CQ3 bidirectional bridge evidence for D-14, reproducing PAPER-C-032's exact rule/atom/parameter triple in a dedicated project namespace (`DG-1203-CQ3`). Seeded graph-level (not via the publish path); derivation is covered separately by Phase 1203-04's `test_computgraph_publish.py` suite. | Phase 1203-06 executor |
