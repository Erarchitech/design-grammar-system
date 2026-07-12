# Phase 821: dg-reasoner Sidecar & OntoGraph/Metagraph RDF Translation - Context

**Gathered:** 2026-07-11
**Status:** Ready for planning

<domain>
## Phase Boundary

Phase 821 stands up the isolated `dg-reasoner` sidecar container (Python + headless JRE 17) in docker-compose, installs the `n10s` plugin on the `neo4j` service, and implements the project-scoped Cypher→RDF translation per `spec/LPG-OWL-MAPPING.md` — proven end-to-end by a real project export round-tripping through RDFLib → Owlready2 → HermiT without error. Routes `POST /reason/consistency` and `POST /shacl/validate` exist on the sidecar and are reachable from `data-service`. Fidelity tests confirm `Atom.ARG.pos` and `HAS_BODY/HAS_HEAD.order` survive translation.

**Not in this phase:** Reasoner-screen wiring and user-facing consistency UX (Phase 822); real SHACL shapes, severity mapping, and ErrorMessageTemplates surfacing (Phase 823); any LLM-ingestion axiom emission (deferred out of v8.2 per ADR-820-1).

</domain>

<decisions>
## Implementation Decisions

### Translator & n10s Role
- **D-01:** The production translator is **custom Cypher + RDFLib** built clean against `spec/LPG-OWL-MAPPING.md` (the 820 spike's proven approach; spike code itself is throwaway). n10s is NOT in the reasoning path.
- **D-02:** n10s scope = **install + smoke-verify**: add the plugin to the `neo4j` service in docker-compose, run graph-config init, and add a smoke check that n10s procedures respond. No production code depends on it — it satisfies the ROADMAP criterion and remains a generic RDF utility/escape hatch.
- **D-03:** **Phase 821 ships the hybrid union too** (static `DesignGrammar-V7.owl` TBox + curated disjointness + live project export, per ADR-820-1). The round-trip test runs the full hybrid union through HermiT — Phase 822 only wires results to the screen.
- **D-04:** Curated `owl:disjointWith` axioms live in a **separate version-controlled overlay file** (e.g. `ontology/dg-disjointness.ttl`) unioned at load time. `DesignGrammar-V7.owl` stays a pristine export.

### Data-Flow Topology
- **D-05:** **The sidecar reads Neo4j directly over bolt** (NEO4J_URI/auth env vars like `data-service`) and owns the whole pipeline: Cypher → RDFLib → union → HermiT. `data-service` just calls `POST /reason/consistency {project}`.
- **D-06:** Reachability criterion is satisfied by a **thin proxy route in data-service now** (e.g. `/reasoner/consistency` → `http://dg-reasoner:<port>/reason/consistency`) with a short connect/read timeout so a sidecar hang never blocks the Speckle-publish/validation hot path. 822 builds the real UX on top.
- **D-07:** The static TBox reaches the container via **read-only volume-mount of `./ontology`** in docker-compose — disjointness curation is edit + restart, no image rebuild.
- **D-08:** Repo layout: **top-level `dg-reasoner/`** mirroring `data-service/` (`Dockerfile`, `app.py`, `ontology_export.py`, `requirements.txt`, `tests/`).

### API Contract & Exposure
- **D-09:** `POST /reason/consistency` is **synchronous with a hard server-side timeout** (~60–120s, configurable) that kills the HermiT/JVM subprocess and returns a clean timeout JSON (504-style). No async job pattern in v8.2.
- **D-10:** Request payload: `{"project": "..."}` plus optional `engine` field defaulting to `hermit` (future-proofs 822's engine choice). Response: `{consistent, unsatisfiable_classes: [...], axiom_counts: {...}, duration_ms, stripped_builtin_rules}` — everything REAS-06's pass/fail + unsat-count display needs, so 822 has zero contract churn.
- **D-11:** `POST /shacl/validate` runs the **real pySHACL pipeline with a placeholder/empty shapes graph**, returning `{conforms: true, results: []}`. Phase 823 swaps in real shapes + severity mapping; the plumbing is proven now.
- **D-12:** The sidecar is **internal-only** — reachable on the docker network via data-service's proxy. No nginx route in 821; 822 decides how the UI reaches it.

### Fidelity-Test Strategy
- **D-13:** **Two test tiers**: (a) unit-level fidelity tests on a small committed fixture (known graph-shaped input → structural assertions; deterministic, CI-able without docker); (b) an integration round-trip against **live docker Neo4j (`v8-ui-smoke`, 16 rules)** → HermiT, satisfying the "real project, not a toy fixture" criterion.
- **D-14:** Fidelity assertions are **structural via RDFLib**: parse the produced Turtle back, walk each `swrl:AtomList` and assert atom sequence matches `HAS_BODY`/`HAS_HEAD` `order`; assert `swrl:argument1`/`swrl:argument2` match `ARG.pos` 1/2. No golden-file byte diffs.
- **D-15:** Tests live in **`dg-reasoner/tests/` using pytest** (mirrors `data-service/tests/`); live integration test is marked (e.g. `@pytest.mark.integration`) and skipped when Neo4j is unreachable.
- **D-16:** The live round-trip test **asserts drift-immunity**: the two known-mistagged `v8-ui-smoke` atoms (`R_DOOR_ORIENTATION_V_A1/_A2`, carrying `graph:'OntoGraph'` instead of `'Metagraph'`) MUST appear in the export — turning 820's data-quality finding into a regression guard for the label-scoped-export mandate.

### Claude's Discretion
- Sidecar port number, exact timeout default, JVM/container memory limits, health-endpoint shape, error envelope details, logging.
- Exact fixture content for unit tests (must exercise ≥1 rule with multi-atom body, a BuiltinAtom, and both ARG positions).
- FastAPI vs other Python framework for the sidecar (FastAPI recommended for consistency with `data-service`).
- How the builtin-atom stripping (HermiT limitation, confirmed in spike) is logged/reported in the response (`stripped_builtin_rules` count is required in the payload).

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Mapping & Architecture (normative)
- `spec/LPG-OWL-MAPPING.md` — THE normative LPG→OWL contract: SWRL RDF vocabulary mapping, `ARG.pos` → `swrl:argument1/2`, `HAS_BODY/HAS_HEAD.order` → `rdf:List`/`swrl:AtomList`, IRI minting, namespace separation, **label-scoped export mandate** (never scope by the `graph` property), UNA/`owl:AllDifferent` handling
- `.planning/phases/820-reasoning-stack-architecture-decision-ontograph-axiom-scopin/820-DECISION.md` — ADR-820-1 (hybrid axiom scoping) + ADR-820-2 (sidecar confirmed) + the data-quality drift note (mistagged atoms) that D-16's regression guard encodes

### Spike Evidence & Reproduction (reference, code is throwaway)
- `.planning/phases/820-reasoning-stack-architecture-decision-ontograph-axiom-scopin/spike/README.md` — exact HermiT/JRE-17 reproduction steps, Owlready2 `sync_reasoner()` subprocess mechanics, builtin-rule stripping
- `.planning/phases/820-reasoning-stack-architecture-decision-ontograph-axiom-scopin/spike/export.py` — reference Cypher extraction + rdflib construction (do NOT copy verbatim; rebuild clean per spec)

### Static TBox
- `ontology/DesignGrammar-V7.owl` — 182KB static meta-schema TBox (65 subClassOf, 101 domain, 110 range, 0 disjointWith as of 2026-07-11); volume-mounted into the sidecar per D-07

### Schema & Research
- `training/dataset_schema.json` + `cypher_template.txt` — graph schema v4 single source of truth (node labels, key properties, relationship properties)
- `.planning/research/` (STACK/PITFALLS/SUMMARY) — pinned library versions (RDFLib 7.6.0, Owlready2 0.51, pySHACL 0.40.0), known pitfalls

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `data-service/` service layout (Dockerfile, app.py, requirements.txt, tests/) — the structural template for `dg-reasoner/` (D-08)
- `data-service/app.py` Neo4j bolt connection pattern (env-driven NEO4J_URI/auth) — reuse for the sidecar's direct reads (D-05)
- `data-service/reasoner.py` — existing v8.1 reasoner-settings persistence (`GET/PUT /reasoner/settings`); the thin proxy route (D-06) lands beside it
- `docker-compose.yml` — 12+ service orchestration; `dg-reasoner` becomes a new service; `neo4j` service gains the n10s plugin config (D-02)

### Established Patterns
- Project isolation via `project` property on every node — the export MUST be project-scoped
- Label-scoped Cypher extraction (never the `graph` property) per the mapping spec — known tagging drift makes graph-property scoping silently lossy
- Synchronous HTTP with timeouts (no message queue) — repo-wide Key Decision, honored by D-09
- pytest in per-service `tests/` dirs — D-15 follows

### Integration Points
- `docker-compose.yml`: new `dg-reasoner` service + n10s plugin on `neo4j` + `./ontology` volume mount
- `data-service`: thin proxy route → `http://dg-reasoner:<port>` (internal docker network only)
- Phase 822 consumes: the rich `/reason/consistency` response contract (D-10)
- Phase 823 consumes: the working pySHACL pipeline with swap-in shapes (D-11)

</code_context>

<specifics>
## Specific Ideas

- The round-trip proof must run the FULL hybrid union (TBox + disjointness overlay + live export) through HermiT — a trivially-consistent live-only export is explicitly not enough (that was 820's documented false positive).
- The drift-immunity assertion (D-16) intentionally pins the two known-mistagged `v8-ui-smoke` atoms so any future regression to graph-property scoping fails loudly.

</specifics>

<deferred>
## Deferred Ideas

- Async job pattern for long-running reasoning (submit/poll) — revisit if real ontologies exceed the sync timeout in practice.
- nginx exposure of the sidecar (`/dg-reasoner/` route) — Phase 822 decides UI reachability.
- n10s-based secondary export endpoint — installed capability exists; wire it up only if a concrete consumer appears.
- LLM-ingestion axiom emission — already deferred out of v8.2 per ADR-820-1.

</deferred>

---

*Phase: 821-dg-reasoner Sidecar & OntoGraph/Metagraph RDF Translation*
*Context gathered: 2026-07-11*
