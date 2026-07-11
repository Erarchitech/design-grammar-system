# Project Research Summary

**Project:** Design Grammar System — v8.2 Connector Integration & Reasoning Engine
**Domain:** OWL 2 DL ontology reasoning + SHACL instance validation bolted onto a Neo4j-native property-graph compliance system, plus credential-gated Grasshopper connector wiring
**Researched:** 2026-07-11
**Confidence:** MEDIUM-HIGH

## Executive Summary

v8.2 adds three tightly-related capabilities to the already-shipped v8.1 platform: (1) real OWL 2 DL reasoning (HermiT/Pellet via Owlready2) replacing the v8.1 Reasoner screen's inert placeholder selector, (2) a SHACL validation layer running alongside — not replacing — the existing bespoke-regex SWRL VALIDATOR, and (3) wiring the Grasshopper CONNECTOR component to the v8.1 Connector Credential Backend so it stops taking raw Neo4j credentials with no relationship to the platform's credential system. All three are standard, well-documented technology choices (Owlready2 + pySHACL, both Python-native or JVM-subprocess), but the *integration* is genuinely hard: DG's live Neo4j `OntoGraph` is a flat vocabulary with no `rdfs:subClassOf`/`domain`/`range`/`disjointWith` axioms today, so a naive reasoner run over it will report "consistent" trivially — not because the ontology is sound, but because it has nothing to reason over. This is the single most important finding across all four research files and must be resolved as an explicit early decision, not discovered mid-build.

The recommended approach: run OWL reasoning and SHACL validation in a **new sidecar service (`dg-reasoner`)**, isolated from `data-service`'s FastAPI hot path, called synchronously over HTTP exactly like the existing `data-service → n8n`/`data-service → Speckle` patterns. STACK.md argued for embedding Owlready2 + a headless JRE directly inside `data-service` to avoid a 13th compose service; ARCHITECTURE.md argued for a dedicated sidecar to isolate the JVM subprocess lifecycle from Speckle-publish/validation-run traffic. **This summary resolves in favor of the sidecar** — see "Architecture Decision: Sidecar vs Embedded" below — because PITFALLS.md's Pitfall 2 (reasoner timeout/blowup under cyclic axioms or growing ABox) makes failure isolation a correctness requirement, not just tidiness, and the milestone explicitly risks unbounded ontology growth as architects author more rules.

Key risks, in order of how early they must be resolved: (1) the OntoGraph axiom gap must be scoped (extend LLM ingestion to emit real axioms vs. scope reasoning to structural checks only) before any reasoner UI work starts; (2) TBox (schema) reasoning and ABox (instance/design) validation must be kept as two visibly distinct checks, never merged into one pass/fail badge, or architects will misread "ontology schema OK" as "my building design is compliant"; (3) SHACL and the existing SWRL VALIDATOR must have a documented rule-partition or precedence policy before either checks real rules, to avoid silent double-authoring and disagreeing verdicts; (4) the CONNECTOR component's credential change must follow DG's own established breaking-change discipline (additive ports, GUID preservation, release-notes migration table) — this project has already been burned by exactly this class of change (v7.0 CLASSIFICATOR/VALIDATION RUNS GUID breakage) and has a documented playbook to reuse.

## Key Findings

### Recommended Stack

Owlready2 0.51 (embeds HermiT as default reasoner, Openllet as the maintained Pellet fork for a second engine) is the only Python library offering genuine OWL 2 DL completeness — no pure-Python library (owlrl included) implements full DL satisfiability/consistency checking, only the incomplete OWL 2 RL profile. pySHACL 0.40.0 is pure Python, no JVM, and handles SHACL Core + SHACL-SPARQL for instance-level validation. Both share RDFLib 7.6.0 as their common in-memory graph type, so a single Neo4j→RDF projection step can feed both engines. A headless JRE (OpenJDK 17) is unavoidable for HermiT/Openllet, since they run as JAR subprocesses Owlready2 shells out to per `sync_reasoner()` call — but the JVM is transient (starts, reasons, exits), not a standing server, so it does not need Jena/Fuseki/TopBraid-style always-on infrastructure. No new NuGet packages are needed on the Grasshopper/C# side — `System.Net.Http.Json` already establishes the `data-service`-calling pattern in `ValidationPublishClient.cs`, directly reusable for CONNECTOR's new credential-heartbeat call.

**Core technologies:**
- **Owlready2 0.51** (HermiT default, Openllet second engine) — real OWL 2 DL reasoning via bundled JAR subprocess; no live triple-store server needed
- **pySHACL 0.40.0** — SHACL Core + SPARQL instance validation, pure Python, no JVM, actively maintained
- **RDFLib 7.6.0 + owlrl 7.6.2** — shared RDF graph substrate between the OWL and SHACL paths; owlrl is a pySHACL dependency only, not a DL-reasoning substitute
- **neosemantics (n10s)** Neo4j plugin — project-scoped Cypher→RDF export (`n10s.rdf.export.cypher`), avoids hand-rolling a serializer
- **OpenJDK 17 headless JRE** — apt-installed runtime for the HermiT/Openllet JARs, ~200MB layer, no persistent process

### Expected Features

Two fundamentally different "reasoning" cadences must be kept separate in the UI/API from day one: OWL TBox consistency (schema-level, open-world, runs at rule-authoring time when the ontology changes) versus SHACL/SWRL ABox validation (instance-level, closed-world, runs every time a DesignState is checked). Conflating them into one status is the single most-repeated risk across FEATURES.md, ARCHITECTURE.md, and PITFALLS.md.

**Must have (table stakes):**
- Reasoner screen "Run check" action that actually reasons, replacing the v8.1 "integration pending" placeholder — binary pass/fail + unsatisfiable-class count is sufficient for v1
- SHACL violation results mapped through DG's existing ErrorMessageTemplates (What+Where+How-to-fix), never raw RDF/SHACL vocabulary shown to architects
- Severity levels (info/warning/violation) mapped to a Solibri-style red/orange/yellow treatment architects already recognize from BIM tooling
- CONNECTOR component accepts a single pasted platform credential/token, replacing manual Neo4j password entry — matches the Speckle/n8n "paste an opaque token" norm
- In-canvas error feedback when the credential is invalid/revoked/expired (reuse existing `AddRuntimeMessage`/ErrorMessageTemplates pattern)

**Should have (competitive):**
- Pre-emptive credential status display on CONNECTOR (live active/stale/revoked from the already-shipped `/connectors/heartbeat` endpoint) — exceeds both Solibri's and n8n's reactive-only credential UX
- Per-connector-type token scoping surfaced explicitly in the Grasshopper UX (already modeled server-side in the v8.1 14-connector registry, mostly UI-copy work)

**Defer (v2+):**
- Explanation/justification UX for why a class is unsatisfiable (Protege-style axiom justification translated to plain language) — ship pass/fail summary first
- TBox→SHACL shape auto-derivation (single source of truth generating both OWL constraints and SHACL shapes) — real open-world/closed-world tension, needs its own design pass
- SWRL→SHACL consolidation (retiring the bespoke VALIDATOR) — explicitly out of scope per milestone framing, SHACL ships as complementary only

### Architecture Approach

Reasoning runs as a synchronous HTTP call from `data-service` to a new dedicated sidecar (`dg-reasoner`), mirroring the existing `data-service → n8n`/`data-service → Speckle` call pattern and respecting CLAUDE.md's "no message queue" decision. Neo4j stays the single source of truth; `DesignGrammar-V7.owl` is loaded as a static meta-schema TBox, unioned at reasoning time with a project-scoped dynamic export of the live OntoGraph/Metagraph via `n10s.rdf.export.cypher`. The Metagraph (Rule/Atom/Var/Literal/Builtin) maps near-1:1 onto the standard W3C SWRL RDF vocabulary (`swrl:Imp`, `swrl:body`/`swrl:head`, `swrl:ClassAtom`, etc.) — a known, low-risk translation. The OntoGraph half has no such shortcut and is the harder, higher-risk translation (see Critical Finding below). Grasshopper is entirely outside this pipeline — reasoning is server-side only, triggered from the `ui-v2` Reasoner screen, never from a GH component's `SolveInstance`.

**Major components:**
1. **`dg-reasoner` (new sidecar)** — Python + headless JRE container; wraps Owlready2 (`sync_reasoner()`/`sync_reasoner_pellet()`) and pySHACL behind `POST /reason/consistency` and `POST /shacl/validate`; stateless, no Neo4j access of its own
2. **`data-service/ontology_export.py` (new module)** — project-scoped Cypher→RDF export via `n10s`, owns the Neo4j bolt driver connection; orchestrates calls to the sidecar and persists run results (extends `reasoner.py`'s existing JSON-settings pattern)
3. **`neo4j` + `n10s` plugin** — RDF export capability added to the existing Neo4j service (plugin jar in the plugins volume), no new container
4. **CONNECTOR component (`ConnectorComponent.cs`)** — two independent, parallel flows: unchanged bolt connection (raw Neo4j creds) plus a new optional best-effort heartbeat call using the platform token; token never gates or substitutes for bolt credentials
5. **`ui-v2` Reasoner screen** — extends existing `GET/PUT /reasoner/settings` with `POST /reasoner/run`, displays two clearly separated statuses (schema consistency vs. design/SHACL validation)

### Critical Pitfalls

1. **OntoGraph has no real axioms today (Critical Finding, both ARCHITECTURE.md and effectively STACK.md)** — running HermiT against a naive export of the live flat vocabulary will report "consistent" trivially. Must be resolved as an explicit spike/decision before any reasoner UI work: either extend LLM ingestion to emit real domain/range/subclass/disjoint triples, or scope v8.2 reasoning down to structural/referential sanity checks (dangling `range`, orphaned `REFERS_TO`), or a hybrid. This is the load-bearing decision the entire milestone's later phases depend on.
2. **Property-graph → RDF translation silently drops edge-property semantics** (`ARG.pos`, `HAS_BODY/HAS_HEAD.order`) — RDF has no native equivalent for edge properties without explicit reification; a hand-rolled exporter can produce valid, "successful" Turtle that has quietly lost ordering data the reasoner result then contradicts. Avoid by writing an explicit LPG→OWL mapping spec first and adding round-trip fidelity tests against known fixtures.
3. **Reasoner timeout/blowup treated as an edge case** — HermiT/Pellet are worst-case exponential and can hang or exhaust memory on cyclic axioms or growing ABox data; must never be called synchronously inside a request handler or GH `SolveInstance`. Reuse `ConnectorComponent`'s existing async-task-plus-`ExpireSolution` pattern; timeout must produce a distinct "unknown" result, never silently read as pass or fail.
4. **TBox/ABox conflation surfaced as one badge** — "ontology schema consistent" and "this specific design is compliant" are different reasoning tasks with different triggers and failure meanings; merging them into a single status will mislead architects into treating a schema-only green check as a design-compliance pass.
5. **SWRL VALIDATOR and SHACL disagree with no defined precedence** — SHACL is closed-world, SWRL/VALIDATOR is effectively closed-world-in-practice-but-hand-built, and nothing guarantees the two engines agree on edge cases (missing properties, cardinality on absent data). Partition rule categories by kind (structural/shape → SHACL, domain compliance → SWRL VALIDATOR) rather than building an arbitration layer; never author the same business rule twice.
6. **CONNECTOR credential change breaks saved .gh canvases without a migration path** — Grasshopper resolves wires by parameter name and position; any port reorder/removal is a breaking change regardless of code-diff size. This project has an established playbook (v7.0 CONNECTOR port-rename release notes) — follow it exactly: prefer additive new input over replacing existing ports, keep the same ComponentGuid, and if any port shifts, ship a release-notes migration table before merge.

## Implications for Roadmap

### Architecture Decision: Sidecar vs Embedded (resolving the STACK.md / ARCHITECTURE.md conflict)

**Decision: separate `dg-reasoner` sidecar service, not embedded in `data-service`.**

Both research files agree on the libraries (Owlready2 wrapping HermiT/Openllet, pySHACL) and agree the JVM only needs to exist as a transient per-call subprocess, not a standing server — the disagreement is purely process/container placement:

- STACK.md's embedded approach avoids a 13th docker-compose service and a network hop, and is defensible in isolation — the JVM subprocess is short-lived either way.
- ARCHITECTURE.md's sidecar approach isolates the JVM subprocess's failure modes (hang, OOM, crash) from `data-service`'s hot path, which also serves Speckle publish and validation-run retrieval for the Grasshopper VALIDATOR/VALIDATION GRAPH components — traffic that must stay unaffected by reasoning workload.

**Tradeoff accepted:** one more container in an already-12+-service `docker-compose.yml`, one more network hop, one more Dockerfile to maintain. This is accepted because PITFALLS.md's Pitfall 2 (reasoner timeout/blowup) is not a hypothetical — DL reasoning is worst-case exponential and DG's rule corpus grows unboundedly with no current size cap, and a JVM hang/crash inside `data-service`'s own process would take down Speckle publish and validation-run retrieval alongside it. The sidecar's failure-isolation property directly prevents that blast radius. pySHACL (pure Python, no JVM) is co-located in the same sidecar per ARCHITECTURE.md's rationale — it keeps all RDF-toolkit dependencies (`rdflib`, `owlrl`) in one new, clearly-scoped service rather than adding an RDF-processing dependency surface to `data-service` itself; moving `shacl_validator.py` back into `data-service` later is a low-risk follow-up if the sidecar round-trip proves unnecessary for SHACL-only checks (no JVM to isolate for that path).

This decision should be recorded as a PROJECT.md Key Decision before phase planning begins.

### Phase 1: Reasoning-Stack Architecture Decision & OntoGraph Axiom Scoping
**Rationale:** Everything downstream depends on resolving the Critical Finding (OntoGraph has no real axioms) and the LPG→OWL mapping spec (Pitfalls 1, 5). Skipping straight to UI wiring risks building a "Run Reasoner" button that always reports "consistent" and teaches users to distrust it.
**Delivers:** Written decision on axiom-scoping option (extend LLM ingestion / scope to structural checks / hybrid); explicit LPG→OWL mapping spec covering edge-property reification and UNA handling; documented in PROJECT.md Key Decisions
**Addresses:** Prerequisite for both OWL reasoning and SHACL features in FEATURES.md's MVP list
**Avoids:** Pitfall 1 (silent RDF translation data loss), Pitfall 5 (UNA gap)

### Phase 2: `dg-reasoner` Sidecar Skeleton + `n10s` Plumbing
**Rationale:** Pure plumbing, independent of Phase 1's axiom-scoping decision — stand up the container and prove the Cypher→RDF→Owlready2→HermiT round trip on a toy example before wiring real project data through it.
**Delivers:** New `dg-reasoner` service in docker-compose (Python + headless JRE), `n10s` plugin installed on the `neo4j` service, `POST /reason/consistency` skeleton endpoint
**Uses:** Owlready2, HermiT (default), n10s (STACK.md, ARCHITECTURE.md)
**Implements:** Reasoning-as-sidecar pattern (Architecture Pattern 1)

### Phase 3: OntoGraph/Metagraph → RDF Translation
**Rationale:** Shaped directly by Phase 1's decision; Metagraph translation is low-risk (SWRL vocabulary mapping already known), OntoGraph translation is the harder piece this phase must implement carefully.
**Delivers:** `data-service/ontology_export.py` — project-scoped Cypher→RDF export feeding both the OWL and SHACL paths from one shared RDFLib graph
**Implements:** Pattern 2 (Cypher-scoped RDF export) and Pattern 3 (SWRL vocabulary mapping)
**Avoids:** Pitfall 1 (fidelity tests for `order`/`pos` edge properties), Pitfall 5 (UNA declarations in the exporter)

### Phase 4: OWL 2 DL Reasoning Integration + Reasoner Screen Wiring
**Rationale:** Consumes Phase 3's translator; replaces the v8.1 placeholder selector per the explicit milestone goal.
**Delivers:** `POST /reasoner/run` endpoint, async task pattern (reusing `ConnectorComponent`'s existing background-task/`ExpireSolution` precedent) with configurable timeout, `ui-v2` Reasoner screen showing pass/fail + unsatisfiable-class count as a distinctly-labeled "schema consistency" status
**Addresses:** FEATURES.md table stakes — "Run check" action, consistency summary
**Avoids:** Pitfall 2 (synchronous reasoner call / no timeout), Pitfall 3 (TBox/ABox conflation — must ship as a visibly separate status from SHACL/SWRL results)

### Phase 5: SHACL Validation Layer
**Rationale:** Lower risk than OWL reasoning, can run partially in parallel with Phases 1–4 once ValidGraph instance-data extraction is defined; shapes can be authored independently of the OWL TBox question. Must land the SWRL/SHACL precedence decision before shipping more than a demo rule.
**Delivers:** `POST /shacl/validate` (pySHACL), severity-mapped results surfaced through existing ErrorMessageTemplates, written rule-partition/precedence decision vs. SWRL VALIDATOR
**Addresses:** FEATURES.md table stakes — SHACL violation surfacing, severity levels
**Avoids:** Pitfall 4 (SWRL/SHACL disagreement with no precedence) — must produce this as a written Key Decision, not just a working prototype

### Phase 6: CONNECTOR Credential Integration
**Rationale:** Fully independent of Phases 1–5 (no shared code path); the backend contract (`/connectors/heartbeat`) already exists from v8.1 Phase 812 with zero backend changes required. Can be built and shipped in parallel at any point.
**Delivers:** New optional `PlatformCredential`/token input on `ConnectorComponent`, additive (existing raw-credential inputs preserved, same ComponentGuid), in-canvas error feedback on invalid/revoked token, security review confirming no raw credential in `BuildRequestKey`/logs/status text
**Addresses:** FEATURES.md table stakes — credential input, in-canvas error feedback; should-have — pre-emptive status display
**Avoids:** Pitfall 6 (canvas breakage — additive-only port design, release-notes migration table if any port shifts), Pitfall 7 (credential treated as weak plaintext secret)

### Phase Ordering Rationale

- Phases 1–4 are strictly sequential (each depends on the prior phase's output) because the OntoGraph axiom gap is a correctness blocker, not a nice-to-have — this is the "likely needs deeper research" segment of the roadmap per ARCHITECTURE.md's Suggested Build Order.
- Phase 5 (SHACL) can start once ValidGraph instance-data extraction is defined, independent of exactly how Phase 1's axiom question resolves — SHACL shapes don't need TBox axioms to be authored.
- Phase 6 (CONNECTOR) has zero shared code with Phases 1–5 and can run fully in parallel from day one — it's the lowest-risk, most self-contained piece of the milestone and should not be sequenced behind the reasoning work.
- This ordering directly avoids Pitfall 3 (TBox/ABox conflation) by keeping the OWL-reasoning phase (schema-level) and the SHACL phase (instance-level) as separately deliverable, separately statused work, never merged into one "add reasoning" phase.

### Research Flags

Needs research during planning (`--research-phase`):
- **Phase 1** — the OntoGraph axiom-scoping decision is genuinely open-ended (extend LLM ingestion vs. scope down vs. hybrid) and has no single documented right answer; needs a prototype/spike, not just a literature read
- **Phase 3** — the OntoGraph half of the LPG→OWL translation has no standard shortcut (unlike Metagraph's SWRL-vocabulary mapping) and is where Pitfall 1's silent data-loss risk concentrates

Standard patterns (skip research-phase):
- **Phase 2** — sidecar skeleton + n10s wiring is well-documented, standard Docker/FastAPI plumbing
- **Phase 4** — once Phase 3's translator exists, Owlready2's `sync_reasoner()` API is HIGH-confidence, official-docs-verified
- **Phase 5** — pySHACL's API is standard and well-documented; the precedence *decision* needs discussion but not technical research
- **Phase 6** — CONNECTOR's HTTP-calling pattern already exists verbatim in `ValidationPublishClient.cs`; this is a direct-reuse implementation task

## Confidence Assessment

| Area | Confidence | Notes |
|------|------------|-------|
| Stack | MEDIUM | PyPI metadata and official docs confirmed directly (HIGH-tier sources), but Context7/Exa MCP tools were unavailable this session and Perplexity MCP returned 401 — library choices are solid, exact version pinning should be re-verified at implementation time |
| Features | MEDIUM | Vendor docs (Solibri, W3C SHACL spec, Protege, n8n community, Speckle docs) cross-checked across independent sources; no HIGH-confidence primary-doc lookups this pass |
| Architecture | MEDIUM-HIGH | Integration pattern and library choices are HIGH confidence (well-documented); the exact shape of the Neo4j→OWL translation is MEDIUM confidence, gated on the Phase 1 spike this summary flags |
| Pitfalls | MEDIUM (web sources) / HIGH (project-specific facts) | OWL/RDF/SHACL general pitfalls are web-sourced and cross-checked (MEDIUM); CONNECTOR breaking-change precedent and current code patterns are read directly from `ConnectorComponent.cs` and `docs/RELEASE-NOTES-v7.0.md` (HIGH) |

**Overall confidence:** MEDIUM-HIGH

### Gaps to Address

- **OntoGraph axiom scope (Critical Finding):** Not resolvable from research alone — requires a Phase 1 spike against a real project's data before phase 2+ can be planned in detail. Flagged explicitly as the roadmap's first gating decision.
- **HermiT/Openllet long-term maintenance health:** HermiT upstream has had no commits in ~6 years (still the de facto Protege default, still bundled by Owlready2) and stock Pellet is effectively unmaintained (Openllet is the recommended fork). Acceptable for v8.2 given no better-maintained OWL 2 DL alternative exists, but worth re-checking at a future milestone if reasoning becomes business-critical.
- **Sidecar vs embedded reversibility:** If reasoning load turns out to be very light in practice (small ontologies, infrequent runs), the sidecar's extra container/network-hop cost may be reconsidered — but start with the sidecar per the Pitfall-2-driven reasoning above; do not default to embedding without re-running that tradeoff analysis.
- **Exact JDK/Debian package name drift:** `openjdk-17-jre-headless` is confirmed for `python:3.11-slim`'s current Debian base, but Debian's default-JDK alias can shift between bookworm/trixie — verify at Dockerfile-write time via `apt-cache search openjdk`.

## Sources

### Primary (HIGH confidence)
- https://pypi.org/pypi/owlready2/json, https://pypi.org/pypi/pyshacl/json, https://pypi.org/pypi/rdflib/json, https://pypi.org/pypi/owlrl/json — official PyPI metadata
- https://owlready2.readthedocs.io/en/latest/reasoning.html — Owlready2 reasoning docs
- https://github.com/RDFLib/pySHACL — pySHACL repo, release cadence into 2026
- Direct codebase reads: `data-service/reasoner.py`, `data-service/connectors.py`, `data-service/app.py`, `DG/src/DG.Grasshopper/Components/ConnectorComponent.cs`, `DG/src/DG.Grasshopper/Validation/ValidationPublishClient.cs`, `ontology/DesignGrammar-V7.owl`, `cypher_template.txt`, `training/dataset_schema.json`, `docs/RELEASE-NOTES-v7.0.md`, `ui-v2/src/screens/ReasonerScreen.jsx`, `.planning/PROJECT.md`

### Secondary (MEDIUM confidence)
- https://neo4j.com/labs/neosemantics/, https://github.com/neo4j-labs/neosemantics — n10s RDF export plugin
- https://github.com/Galigator/openllet, https://github.com/stardog-union/pellet — Openllet vs stock Pellet maintenance comparison
- https://help.solibri.com — severity-level UX conventions
- https://w3.org/TR/shacl12-ui/ — SHACL vocabulary and UI conventions
- arXiv 2309.06888 ("OWL Reasoners still useable in 2023"), ORE 2015 Competition Report — reasoner performance/reliability benchmarks
- arXiv 2507.12286 — SHACL/OWL open-world/closed-world semantics tension

### Tertiary (LOW confidence)
- General web survey of HermiT/Pellet/Openllet/ELK maintenance status — dated 2023 baseline extrapolated forward; recommend re-verifying at implementation time

---
*Research completed: 2026-07-11*
*Ready for roadmap: yes*
