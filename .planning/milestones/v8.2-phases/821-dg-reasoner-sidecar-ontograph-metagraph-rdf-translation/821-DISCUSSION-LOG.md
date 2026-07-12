# Phase 821: dg-reasoner Sidecar & OntoGraph/Metagraph RDF Translation - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-07-11
**Phase:** 821-dg-reasoner-sidecar-ontograph-metagraph-rdf-translation
**Areas discussed:** n10s role vs custom translator, Data-flow topology, API contract & exposure, Fidelity-test strategy

---

## n10s Role vs Custom Translator

| Option | Description | Selected |
|--------|-------------|----------|
| Custom Cypher+RDFLib | Translator is custom code per spec/LPG-OWL-MAPPING.md (spike-proven, built clean); n10s installed but not in the reasoning path | ✓ |
| n10s as primary + post-process | n10s RDF export as base, transformed into the spec's mapping | |
| Drop n10s entirely | Skip n10s — would deviate from the ROADMAP success criterion | |

**User's choice:** Custom Cypher+RDFLib (Recommended)

| Option | Description | Selected |
|--------|-------------|----------|
| Install + smoke-verify | Plugin in docker-compose, graph-config init, smoke check n10s procedures respond | ✓ |
| Install + working RDF endpoint | Also verify n10s HTTP /rdf endpoint returns Turtle for a project-scoped query | |
| You decide | Claude picks the minimal footprint | |

**User's choice:** Install + smoke-verify (Recommended)

| Option | Description | Selected |
|--------|-------------|----------|
| 821 ships union too | Bundle V7 TBox + curated disjointWith; round-trip test runs full hybrid union through HermiT | ✓ |
| 821 = live export only | Feed only live export to HermiT (trivially consistent); union deferred to 822 | |
| You decide | Claude weighs criterion wording during planning | |

**User's choice:** 821 ships union too (Recommended)

| Option | Description | Selected |
|--------|-------------|----------|
| Separate overlay file | ontology/dg-disjointness.ttl unioned at load time; V7.owl stays pristine | ✓ |
| Edit V7.owl in place | Add owl:disjointWith directly into the 182KB generated export | |
| You decide | Either way axioms are design-time artifacts per ADR-820-1 | |

**User's choice:** Separate overlay file (Recommended)

---

## Data-Flow Topology

| Option | Description | Selected |
|--------|-------------|----------|
| Sidecar reads Neo4j | dg-reasoner gets bolt access and owns the whole pipeline; data-service just calls the endpoint | ✓ |
| data-service exports, pushes RDF | Translator in data-service; sidecar receives Turtle and only reasons | |
| Shared library, both can run it | Translator as a shared Python package | |

**User's choice:** Sidecar reads Neo4j (Recommended)

| Option | Description | Selected |
|--------|-------------|----------|
| Thin proxy route now | data-service passthrough with short timeouts; proves reachability concretely | ✓ |
| Healthcheck-level proof only | data-service pings sidecar /health in a test; no proxy until 822 | |
| You decide | Smallest honest interpretation of "reachable" | |

**User's choice:** Thin proxy route now (Recommended)

| Option | Description | Selected |
|--------|-------------|----------|
| Volume-mount ./ontology | Read-only mount; disjointness edit = restart, no rebuild | ✓ |
| Bake into Docker image | COPY at build time; every edit needs a rebuild | |
| You decide | — | |

**User's choice:** Volume-mount ./ontology (Recommended)

| Option | Description | Selected |
|--------|-------------|----------|
| Top-level dg-reasoner/ | New sibling of data-service/ mirroring the service convention | ✓ |
| Subpackage of data-service | Blurs the isolation the sidecar exists for | |
| You decide | — | |

**User's choice:** Top-level dg-reasoner/ (Recommended)

---

## API Contract & Exposure

| Option | Description | Selected |
|--------|-------------|----------|
| Sync with hard timeout | Blocks until HermiT finishes, bounded by configurable server-side timeout killing the JVM subprocess | ✓ |
| Async job pattern | POST returns job id; poll for status | |
| Sync now, async-ready shape | Sync semantics with status field in envelope | |

**User's choice:** Sync with hard timeout (Recommended)

| Option | Description | Selected |
|--------|-------------|----------|
| {project} in, rich result out | Request {project, engine?}; response {consistent, unsatisfiable_classes, axiom_counts, duration_ms, stripped_builtin_rules} | ✓ |
| Minimal bool now | {consistent: bool} only; 822 extends | |
| You decide | Shaped by REAS-06's needs | |

**User's choice:** {project} in, rich result out (Recommended)

| Option | Description | Selected |
|--------|-------------|----------|
| Real pySHACL, placeholder shapes | Full pipeline with empty shapes graph → {conforms: true, results: []}; 823 swaps in shapes | ✓ |
| Honest 501 stub | Route exists, returns 501 | |
| You decide | — | |

**User's choice:** Real pySHACL, placeholder shapes (Recommended)

| Option | Description | Selected |
|--------|-------------|----------|
| Internal-only | Docker-network reachable via data-service proxy; no nginx route | ✓ |
| Add /dg-reasoner/ nginx route now | Direct browser exposure like /data-service | |
| You decide | — | |

**User's choice:** Internal-only (Recommended)

---

## Fidelity-Test Strategy

| Option | Description | Selected |
|--------|-------------|----------|
| Both: fixture + live | Unit fidelity tests on committed fixture + integration round-trip against live Neo4j (v8-ui-smoke) | ✓ |
| Live Neo4j only | All tests hit running docker neo4j; flaky when stack is down | |
| Fixture only + manual live run | Live round-trip as documented manual step | |

**User's choice:** Both: fixture + live (Recommended)

| Option | Description | Selected |
|--------|-------------|----------|
| Structural via RDFLib | Parse Turtle back; walk swrl:AtomList order and argument1/2 vs ARG.pos | ✓ |
| Golden-file diff | Byte-for-byte comparison; brittle | |
| Both structural + golden | Structural + one golden canary | |

**User's choice:** Structural via RDFLib (Recommended)

| Option | Description | Selected |
|--------|-------------|----------|
| dg-reasoner/tests/, pytest | Mirrors data-service/tests/; live test marked @pytest.mark.integration, skipped when Neo4j unreachable | ✓ |
| Central test/ directory | Repo top-level test/ dir | |
| You decide | — | |

**User's choice:** dg-reasoner/tests/, pytest (Recommended)

| Option | Description | Selected |
|--------|-------------|----------|
| Yes, assert drift-immunity | Live test pins the two known-mistagged v8-ui-smoke atoms (R_DOOR_ORIENTATION_V_A1/_A2) as a regression guard for label-scoped export | ✓ |
| No, generic counts only | Totals-only checks, less coupled to one project's data | |
| You decide | — | |

**User's choice:** Yes, assert drift-immunity (Recommended)

---

## Claude's Discretion

- Sidecar port, timeout default, JVM/container memory limits, health endpoint, error envelope, logging
- Unit-test fixture content (must exercise multi-atom body, BuiltinAtom, both ARG positions)
- Web framework choice (FastAPI recommended for consistency)
- How builtin-atom stripping is logged/reported (count field required in payload)

## Deferred Ideas

- Async job pattern for long-running reasoning — revisit if real ontologies exceed the sync timeout
- nginx exposure of the sidecar — Phase 822 decides UI reachability
- n10s-based secondary export endpoint — only if a concrete consumer appears
- LLM-ingestion axiom emission — already deferred out of v8.2 (ADR-820-1)
