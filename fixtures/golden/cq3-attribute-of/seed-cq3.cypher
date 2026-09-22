// ============================================================================
// Seed: CQ3 fixture — ATTRIBUTE_OF bidirectional bridge (Phase 1203-06, D-14)
// ============================================================================
//
// PURPOSE
//   Reproduces PAPER-C-032's exact triple (docs/reviews/theory-implementation-
//   alignment/evidence/paper-claims.json, paper location P125/T02 CQ3):
//   "CQ3 is demonstrated by a single row tracing
//   R_BUILDING_MIN_DISTANCE_12_V/A2/hasDistanceM to parameter SepDist of type
//   Variable." This script seeds that one rule, its DataPropertyAtom, and its
//   governing parameter, connected by HAS_BODY and ATTRIBUTE_OF, so both the
//   forward (rule -> parameter) and reverse (parameter -> rule) queries can be
//   run against a live Neo4j and each return exactly one row.
//
//   This fixture is GRAPH-LEVEL, SEEDED DIRECTLY — it creates the ATTRIBUTE_OF
//   edge itself rather than by invoking data-service's publish path
//   (computgraph_publish.publish_structure / _publish_attribute_of). The
//   derivation path (inputBindings -> _attribute_of_from_bindings ->
//   _publish_attribute_of) is covered separately by Phase 1203-04's tests in
//   data-service/tests/test_computgraph_publish.py (see that file's
//   "ALGN12-14: ATTRIBUTE_OF derivation" and "-- both query directions"
//   sections, e.g. test_attribute_of_forward_query_returns_governing_parameter_name
//   and test_attribute_of_reverse_query_returns_governing_rule_and_atom). This
//   fixture and that suite evidence two different things: derivation is proven
//   there; queryability of the resulting shape against a real graph is proven
//   here. Neither substitutes for the other.
//
//   The seeded edge's shape (MATCH pattern, key properties, provenance fields)
//   mirrors exactly what data-service/computgraph_publish.py's
//   _publish_attribute_of MERGE statement produces, so a query written against
//   this fixture is a query that would work against real published data:
//     MATCH (r:Rule {Rule_Id: $ruleId, project: $project})
//     MATCH (r)-[:HAS_BODY]->(a:Atom {type: 'DataPropertyAtom'})
//     MATCH (p:Parameter {cgId: $paramCgId, definitionId: $definitionId, project: $project})
//     MERGE (a)-[rel:ATTRIBUTE_OF]->(p)
//       SET rel.derivedFromRuleId = ..., rel.source = ..., rel.determinability = ...
//
// PROJECT NAMESPACE
//   Every node below is scoped to project: 'DG-1203-CQ3' — a namespace used by
//   no other fixture under fixtures/golden/ (verified: this string appears in
//   no other file in that tree). This makes the cross-project isolation
//   property demonstrable rather than incidental: a query for a DIFFERENT
//   project value against this same graph returns zero rows.
//
// EXECUTION METHOD
//   Dev databases only. Run as a single block in Neo4j Browser (paste all +
//   Ctrl+Enter) — statements are semicolon-separated with a blank line after
//   each, matching fixtures/golden/replay/seed-replay.cypher's convention.
//
//   Or via cypher-shell against a dev instance:
//     cypher-shell -a bolt://localhost:7687 -u neo4j -p <password> -f fixtures/golden/cq3-attribute-of/seed-cq3.cypher
//
//   Or via the running compose stack (MSYS_NO_PATHCONV=1 needed on Git Bash
//   for docker exec/cp path rewriting):
//     MSYS_NO_PATHCONV=1 docker compose exec -T neo4j cypher-shell -u neo4j -p 12345678 -f /dev/stdin < fixtures/golden/cq3-attribute-of/seed-cq3.cypher
//
// TEARDOWN (idempotent — run before re-seeding, or to remove the fixture entirely)
//   MATCH (n {project: 'DG-1203-CQ3'}) DETACH DELETE n
//
// PARAMETERIZATION DISCIPLINE (T-1203-06-01, carried forward from seed.cypher /
// seed-replay.cypher)
//   This file is a static, checked-in, dev-only script with literal values —
//   not a parameterized runtime query. ANY Python or C# code that *executes*
//   this file, or reconstructs equivalent statements from fixture-derived
//   values at runtime, MUST pass those values as a parameter dict and MUST
//   NEVER string-interpolate them into query text.
//
// ============================================================================

// ---- Step 1: Rule ----
MERGE (rule:Rule {Rule_Id: 'R_BUILDING_MIN_DISTANCE_12_V', project: 'DG-1203-CQ3'})
  SET rule.graph = 'Metagraph',
      rule.kind = 'Constraint',
      rule.RuleName = 'CQ3 fixture minimum building separation distance',
      rule.RuleDescription = 'Minimum separation distance between buildings must not be less than the governing SepDist parameter',
      rule.SWRL = 'Building(?b1) ^ Building(?b2) ^ hasDistanceM(?b1, ?b2, ?d) ^ swrlb:lessThan(?d, 12) -> Violation(?b1)'
;

// ---- Step 2: Atoms ----
// A1 (ClassAtom) and A2 (DataPropertyAtom, the constraining atom PAPER-C-032
// names) are both seeded so HAS_BODY has more than one body atom to
// disambiguate against -- matching the real ingest convention that a rule's
// body is a list of atoms, not a single one. Only A2 is the DataPropertyAtom
// ATTRIBUTE_OF attaches to.
MERGE (a1:Atom {Atom_Id: 'R_BUILDING_MIN_DISTANCE_12_V_A1', project: 'DG-1203-CQ3'})
  SET a1.graph = 'Metagraph', a1.type = 'ClassAtom', a1.SWRL_label = 'Building(?b1)'
;

MERGE (a2:Atom {Atom_Id: 'R_BUILDING_MIN_DISTANCE_12_V_A2', project: 'DG-1203-CQ3'})
  SET a2.graph = 'Metagraph',
      a2.type = 'DataPropertyAtom',
      a2.iri = 'ex:hasDistanceM',
      a2.SWRL_label = 'hasDistanceM(?b1, ?b2, ?d)'
;

// H1 (head atom) deliberately reuses type = 'DataPropertyAtom', the same
// convention 1203-01's preflight observed in the real corpus (_A2 and _H1
// share type but not HAS_BODY/HAS_HEAD role) -- present here so the forward
// query's HAS_BODY-then-type-filter is proven to disambiguate the body
// occurrence from the head occurrence, not merely proven on a fixture with
// only one DataPropertyAtom in it.
MERGE (h1:Atom {Atom_Id: 'R_BUILDING_MIN_DISTANCE_12_V_H1', project: 'DG-1203-CQ3'})
  SET h1.graph = 'Metagraph',
      h1.type = 'DataPropertyAtom',
      h1.iri = 'ex:hasViolation',
      h1.SWRL_label = 'hasViolation(?b1)'
;

// ---- Step 3: HAS_BODY / HAS_HEAD (body atoms fire on violation, per convention) ----
MATCH (rule:Rule {Rule_Id: 'R_BUILDING_MIN_DISTANCE_12_V', project: 'DG-1203-CQ3'})
MATCH (a1:Atom {Atom_Id: 'R_BUILDING_MIN_DISTANCE_12_V_A1', project: 'DG-1203-CQ3'})
MERGE (rule)-[:HAS_BODY {order: 1}]->(a1)
;

MATCH (rule:Rule {Rule_Id: 'R_BUILDING_MIN_DISTANCE_12_V', project: 'DG-1203-CQ3'})
MATCH (a2:Atom {Atom_Id: 'R_BUILDING_MIN_DISTANCE_12_V_A2', project: 'DG-1203-CQ3'})
MERGE (rule)-[:HAS_BODY {order: 2}]->(a2)
;

MATCH (rule:Rule {Rule_Id: 'R_BUILDING_MIN_DISTANCE_12_V', project: 'DG-1203-CQ3'})
MATCH (h1:Atom {Atom_Id: 'R_BUILDING_MIN_DISTANCE_12_V_H1', project: 'DG-1203-CQ3'})
MERGE (rule)-[:HAS_HEAD {order: 1}]->(h1)
;

// ---- Step 4: Governing Parameter (Computgraph) ----
// paramKind 'Variable' matches PAPER-C-032's claim text verbatim ("parameter
// SepDist of type Variable"). definitionId is a dedicated CQ3 definition file
// name, distinct from every other fixture's definitionId, kept consistent
// with the definitionId used in the ATTRIBUTE_OF MERGE MATCH below.
MERGE (p:Parameter {cgId: 'cg:1:param:cq3_SepDist', definitionId: 'cq3-fixture.gh', project: 'DG-1203-CQ3'})
  SET p.parameterName = 'SepDist',
      p.paramKind = 'Variable',
      p.dataType = 'Float',
      p.domainMin = 0.0,
      p.domainMax = 50.0,
      p.domainStep = 0.5,
      p.dgId = 'dg:CQ3FIXTURESEPDIST01',
      p.graph = 'Computgraph',
      p.project = 'DG-1203-CQ3'
;

// ---- Step 5: ATTRIBUTE_OF — the bridge edge itself ----
// Mirrors _publish_attribute_of's exact MATCH/MERGE shape: Rule matched by
// Rule_Id + project, DataPropertyAtom reached via HAS_BODY + type filter
// (never by Atom_Id string alone), Parameter matched by its full
// (cgId, definitionId, project) key. Provenance fields set exactly as the
// real writer sets them from an _attribute_of_from_bindings row.
MATCH (r:Rule {Rule_Id: 'R_BUILDING_MIN_DISTANCE_12_V', project: 'DG-1203-CQ3'})
MATCH (r)-[:HAS_BODY]->(a:Atom {type: 'DataPropertyAtom', project: 'DG-1203-CQ3'})
MATCH (p:Parameter {cgId: 'cg:1:param:cq3_SepDist', definitionId: 'cq3-fixture.gh', project: 'DG-1203-CQ3'})
MERGE (a)-[rel:ATTRIBUTE_OF]->(p)
  SET rel.derivedFromRuleId = 'R_BUILDING_MIN_DISTANCE_12_V',
      rel.source = 'binding',
      rel.determinability = 'direct-parameter'
;

// ============================================================================
// VERIFICATION QUERIES (see README.md for the authoritative forward/reverse
// query text used by the automated test and the live checkpoint)
//
// Sanity check after seeding:
//   MATCH (n {project:'DG-1203-CQ3'}) RETURN count(n) -- expect > 0
//
// Teardown, then re-run the count query above -- expect 0:
//   MATCH (n {project: 'DG-1203-CQ3'}) DETACH DELETE n
//
// This script never targets any other fixture's project namespace -- confirm
// with: fixtures/golden/cq3-attribute-of/seed-cq3.cypher contains zero
// occurrences of 'DG-1200-GOLDEN' or 'DG-1202-REPLAY', and at least 5
// occurrences of 'DG-1203-CQ3'.
// ============================================================================
