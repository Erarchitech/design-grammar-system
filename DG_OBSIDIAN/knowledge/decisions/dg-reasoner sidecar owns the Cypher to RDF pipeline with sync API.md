---
tags: [decision, v8.2, phase-821, dg-reasoner, rdf, owl, api]
date: 2026-07-11
---

# dg-reasoner sidecar owns the Cypher→RDF pipeline with sync API

## Context

Phase 820 confirmed the isolated `dg-reasoner` sidecar (ADR-820-2) and the hybrid axiom-scoping approach (ADR-820-1), and produced the normative mapping spec `spec/LPG-OWL-MAPPING.md`. Phase 821 discussion (2026-07-11) had to settle where the translator lives, what role n10s plays, the API semantics, and the test strategy.

## Decision

1. **Custom translator, not n10s.** The production Cypher→RDF translation is custom Cypher + RDFLib code built clean against `spec/LPG-OWL-MAPPING.md`. n10s is installed on the `neo4j` service and smoke-verified only — it satisfies the ROADMAP criterion and stays available as a generic utility, but n10s's generic export (neo4j:// IRIs, flat triples) cannot produce the SWRL AtomList reification the spec mandates.
2. **Sidecar owns the whole pipeline.** `dg-reasoner` reads Neo4j directly over bolt (env-driven credentials like `data-service`) and runs Cypher → RDFLib → hybrid union → HermiT internally. `data-service` only calls `POST /reason/consistency {project}` through a thin proxy route with short timeouts.
3. **Sync API with hard timeout.** `/reason/consistency` blocks until HermiT finishes, bounded by a configurable server-side timeout that kills the JVM subprocess. Rich response: `{consistent, unsatisfiable_classes, axiom_counts, duration_ms, stripped_builtin_rules}`. No async job pattern in v8.2 (honors repo-wide "no message queue" decision).
4. **Hybrid union ships in 821.** The V7 TBox + curated `owl:disjointWith` overlay (`ontology/dg-disjointness.ttl`, separate file — V7.owl stays pristine) + live export is unioned and round-tripped through HermiT in this phase; 822 only wires the screen.
5. **Two-tier fidelity tests** in `dg-reasoner/tests/` (pytest): structural RDFLib assertions on a committed fixture (AtomList order vs `HAS_BODY/HAS_HEAD.order`, `swrl:argument1/2` vs `ARG.pos`) + a live integration round-trip on `v8-ui-smoke` that pins the two known-mistagged atoms (`R_DOOR_ORIENTATION_V_A1/_A2`) as a drift-immunity regression guard for label-scoped export.

## Rationale

- Splitting the pipeline (data-service exports, sidecar reasons) would re-bloat `data-service` — the exact thing the sidecar isolates.
- Sync-with-timeout keeps the 822 screen contract trivial; isolation is already provided by the container boundary + proxy timeouts.
- The rich response payload gives REAS-06 (pass/fail + unsatisfiable-class count) everything up front — zero contract churn in 822.

## Source

- `.planning/phases/821-dg-reasoner-sidecar-ontograph-metagraph-rdf-translation/821-CONTEXT.md` (D-01…D-16)
- [[decisions/Reasoning runs in isolated dg-reasoner sidecar not embedded in data-service|ADR-820-2]]
- [[decisions/v8.2 hybrid axiom-scoping spike proven|ADR-820-1]]
