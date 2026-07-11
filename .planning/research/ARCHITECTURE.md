# Architecture Research: OWL 2 DL Reasoning + SHACL Integration, CONNECTOR Credential Wiring

**Domain:** RDF/OWL reasoning integration into a Neo4j-property-graph system (AEC compliance-checking); Grasshopper plugin credential wiring
**Researched:** 2026-07-11
**Confidence:** MEDIUM-HIGH (integration pattern and library choices are HIGH confidence, well-documented; the exact shape of DG's Neo4j→OWL translation is MEDIUM confidence — it depends on a codebase gap this research surfaced, see Critical Finding below)

## Critical Finding: The "OWL source of truth" question has a definitive answer, and it changes the plan

`ontology/DesignGrammar-V7.owl` and the live Neo4j graph are **not** two views of the same data. They encode two different things:

- **`DesignGrammar-V7.owl`** is the **meta-schema** — the fixed structural ontology of DG itself: the four graph-layer hubs (`dg:Ontograph`, `dgm:Metagraph`, `dgv:Validgraph`, `dgs:SpecGraph`), the state-trio classes (`ObjState`/`ParamState`/`PropState`), `Run`, `ReStatus`, etc. It is hand-maintained, versioned by `apply_v7_rename.py` and friends, and consumed **only** by `ontology/export_to_markdown_v7.py` to produce `DesignGrammar-V7.md` for documentation. No runtime service (`data-service`, n8n, Grasshopper) reads this file. It explicitly documents its own limits: *"Domain-specific classes (Building, UrbanBlock, etc.) are dynamically generated"* and are **not defined in the OWL file** (`DesignGrammar-V7.owl` line ~265).
- **Live Neo4j `OntoGraph`** holds exactly those dynamically-generated, per-project domain terms (`Class`, `DatatypeProperty`, `ObjectProperty` nodes with `iri`/`label`/`SWRL_label`). Confirmed against `cypher_template.txt` and `training/dataset_schema.json`: these nodes carry `range` as a **flat string property** (e.g. `"xsd:decimal"`), not a real `rdfs:range` edge to a class. There is **no `rdfs:subClassOf`, no `rdfs:domain`/`rdfs:range` relationship, no `owl:disjointWith`, no cardinality restriction** anywhere in the live OntoGraph today — it is a flat vocabulary of named terms, not an axiomatized TBox.

**Consequence for reasoning value:** OWL 2 DL reasoners (HermiT/Pellet) prove their worth by detecting unsatisfiable classes and incoherent property usage — but that requires axioms to reason *over*. Running HermiT against a translation of today's flat OntoGraph will almost always report "consistent, nothing to say" — not because the ontology is correct, but because it has no axioms rich enough to be inconsistent. **This is the most important thing the roadmap needs to know before committing to a UI-facing "Run Reasoner" button**: either (a) the LLM rule-ingestion pipeline needs to start emitting real domain/range/subclass/disjointness triples into OntoGraph (a schema change, `n8n/workflows/rules-to-metagraph.json` + prompt changes), or (b) the reasoning step's practical value for v8.2 is scoped down to *structural sanity* (e.g. detect a `DatatypeProperty` referencing a `range` that no `Class`/XSD datatype resolves to, or a `REFERS_TO` dangling reference) rather than true DL satisfiability checking. Recommend the roadmap treat this as an explicit, named decision rather than an assumption — see Build Order below.

**Useful side-finding:** DG's Metagraph (`Rule`/`Atom`/`Var`/`Literal`/`Builtin` + `HAS_BODY`/`HAS_HEAD`/`REFERS_TO`/`ARG`) is a bespoke re-invention of the **standard W3C SWRL RDF vocabulary** (`http://www.w3.org/2003/11/swrl#`: `swrl:Imp`, `swrl:body`/`swrl:head` → `swrl:AtomList`, `swrl:ClassAtom`, `swrl:DatavaluedPropertyAtom`, `swrl:BuiltinAtom`, `swrl:argument1`/`argument2`, `swrl:Variable`). The Neo4j→RDF translation of Metagraph is therefore a **known, near-1:1 structural mapping**, not something to invent from scratch. This lowers risk on the Metagraph side even though the OntoGraph side (above) is the harder problem.

## Standard Architecture

### System Overview

```
┌──────────────────────────────────────────────────────────────────────────┐
│  Neo4j (bolt://neo4j:7687)                                                │
│  OntoGraph (Class/DatatypeProperty/ObjectProperty, flat — no axioms)      │
│  Metagraph (Rule/Atom/Var/Literal/Builtin — SWRL-vocabulary-shaped)       │
│  ValidGraph (DesignState/Run — instance/ABox-shaped data to SHACL-check)  │
└───────────────────────────────┬────────────────────────────────────────┘
                                 │ Cypher (n10s.rdf.export.* OR custom Python
                                 │ serializer), project-scoped
                                 ▼
┌──────────────────────────────────────────────────────────────────────────┐
│  data-service (Python FastAPI, existing container)                        │
│  new module: reasoning.py — orchestrates translation + calls sidecar      │
│  new module: shacl_validator.py — pySHACL, in-process (pure Python)       │
│  existing: reasoner.py (registry/settings), connectors.py (credentials)   │
└───────────────────────────────┬────────────────────────────────────────┘
                                 │ HTTP (synchronous, matches existing
                                 │ data-service → n8n / → Speckle pattern)
                                 ▼
┌──────────────────────────────────────────────────────────────────────────┐
│  NEW sidecar: dg-reasoner (Python + headless JRE, new container)          │
│  owlready2 → sync_reasoner() [HermiT default] / sync_reasoner_pellet()    │
│  loads: DesignGrammar-V7.owl (meta-schema, static import)                 │
│        + translated project OntoGraph/Metagraph RDF (dynamic)             │
│  POST /reason/consistency  → {consistent, unsatisfiable_classes[], ...}   │
└───────────────────────────────┬────────────────────────────────────────┘
                                 │ results
                                 ▼
                     data-service persists run result
                                 │
                                 ▼
             ui-v2 Reasoner screen (existing GET/PUT /reasoner/settings
             extended with POST /reasoner/run + result display)
```

Grasshopper plugin is **not** in this pipeline at all — see Anti-Pattern below.

### Component Responsibilities

| Component | Responsibility | Typical Implementation |
|-----------|-----------------|-------------------------|
| Neo4j → RDF translator | Project-scoped Cypher read of OntoGraph+Metagraph, serialize to RDF/Turtle | neosemantics (`n10s`) plugin's `n10s.rdf.export.cypher()` with a custom URI mapping (`n10s.mapping.add`), invoked from `data-service` over the existing bolt driver — avoids hand-rolling RDF serialization |
| Static TBox merge | Combine `DesignGrammar-V7.owl` (meta-schema axioms) with the translated dynamic OntoGraph as one ontology graph before reasoning | Simple `owl:imports` or textual RDF graph union at load time inside the sidecar |
| OWL 2 DL reasoner | Consistency check, class satisfiability, TBox coherence | `owlready2` (Python) wrapping HermiT (bundled, default) and Pellet (via `sync_reasoner_pellet`, subprocess to bundled `pellet.jar`) — both reachable through one Python API, matching the existing `hermit`/`pellet` ids already in `reasoner.py` |
| SHACL validator | Data-level / instance-level shape validation (ValidGraph DesignState/Run instance data, or rule-authored shapes) | `pySHACL` (RDFLib project) — pure Python, actively maintained (releases into Jan 2026), no JVM dependency |
| Reasoning sidecar | Isolate JVM lifecycle (HermiT/Pellet subprocess) from the primary FastAPI process; own container in docker-compose | New service, Python base image + `default-jre-headless`, small FastAPI wrapping owlready2 + pySHACL |
| data-service | Orchestration: pull Neo4j data, call sidecar, persist/return results; existing `reasoner.py` settings registry extends to store run history | Existing FastAPI app, new router module |
| Grasshopper CONNECTOR | Bolt connection (unchanged) + optional best-effort heartbeat to platform (new, additive) | C# component, existing `Neo4jConnectorService` + new optional HTTP call to `/connectors/heartbeat` |

## Recommended Project Structure

```
data-service/
├── app.py                    # add routers: /reasoner/run, /shacl/validate (proxy to sidecar)
├── reasoner.py                # existing registry/settings — extend with run-history persistence
├── ontology_export.py         # NEW: Cypher → n10s export call, project-scoped, returns RDF/Turtle
├── connectors.py              # unchanged — already supports "grasshopper" connector_id
└── requirements.txt            # no JVM deps added here — stays lean

dg-reasoner/                   # NEW sidecar service directory
├── Dockerfile                 # python:3.11-slim + default-jre-headless
├── app.py                     # FastAPI: POST /reason/consistency, POST /shacl/validate
├── reasoning.py                # owlready2 sync_reasoner / sync_reasoner_pellet wrapper
├── shacl.py                    # pySHACL wrapper (could also live in data-service — see trade-off note)
├── static/DesignGrammar-V7.owl # mounted/copied meta-schema TBox
└── requirements.txt            # owlready2, pyshacl, rdflib, fastapi, uvicorn

docker-compose.yml
└── + dg-reasoner service, depends_on: neo4j; called by data-service over HTTP
```

### Structure Rationale

- **New sidecar, not embedded in `data-service`:** HermiT/Pellet require a JVM (owlready2 shells out via `subprocess`). Adding a JRE + Java reasoner jars to `data-service`'s image bloats it and couples an unrelated failure mode (JVM crash/hang during reasoning) to the process that also serves Speckle publish and validation-run retrieval — those are on the hot path for the Grasshopper VALIDATOR/VALIDATION GRAPH components and should stay unaffected by reasoning workload. This also matches DG's existing docker-compose philosophy: one container per concern (n8n, ollama, speckle-* are already split out this way).
- **pySHACL could go either place** — it's pure Python, no JVM, genuinely lightweight. Putting it in the same new sidecar (rather than in `data-service`) is still recommended for this milestone because it keeps all "RDF/OWL toolkit" code and its `rdflib` dependency tree in one new, clearly-scoped service, rather than adding an RDF-processing dependency to `data-service`'s existing surface. If profiling later shows the sidecar round-trip is unnecessary overhead for SHACL-only checks, moving `shacl_validator.py` into `data-service` directly is a low-risk follow-up (no JVM dependency to isolate).
- **`ontology_export.py` in `data-service`, not the sidecar:** the Neo4j bolt driver and project-scoping logic already live in `data-service`; the sidecar should stay a stateless reasoning engine, not a second thing that talks to Neo4j.

## Architectural Patterns

### Pattern 1: Reasoning-as-sidecar over synchronous HTTP

**What:** A dedicated, JVM-carrying microservice exposes a small stateless HTTP API (`POST /reason/consistency`, `POST /shacl/validate`) that `data-service` calls synchronously, mirroring the existing `data-service → n8n` and `data-service → Speckle` call patterns already in this codebase.
**When to use:** When a specific capability has a heavyweight/foreign-runtime dependency (JVM here) that the rest of the stack doesn't otherwise need.
**Trade-offs:** +Isolates blast radius, keeps `data-service` image lean, easy to scale/restart independently. −One more container in an already-12+-service `docker-compose.yml`; adds one network hop and one more thing to keep alive.

**Example (sidecar contract):**
```python
# dg-reasoner/app.py
@app.post("/reason/consistency")
def reason_consistency(payload: OntologyPayload):
    onto = load_ontology_from_ttl(payload.static_owl + payload.dynamic_ttl)
    with onto:
        sync_reasoner(reasoner=payload.reasoner_id)  # "hermit" default, "pellet" alt
    return {
        "consistent": onto.inconsistent_classes() == [],
        "unsatisfiable_classes": [c.iri for c in onto.inconsistent_classes()],
    }
```

### Pattern 2: Cypher-scoped RDF export via neosemantics, not hand-rolled serialization

**What:** Install the `n10s` (neosemantics) Neo4j plugin, define a URI mapping (`n10s.mapping.add`) that maps DG's `iri` property values to real IRIs, then call `n10s.rdf.export.cypher("MATCH ... WHERE project = $p RETURN *", {p: project})` to get project-scoped RDF/Turtle directly out of Neo4j.
**When to use:** Whenever the export needs to be project-scoped, kept in sync with schema changes, and not duplicated as a second hand-maintained serializer.
**Trade-offs:** +No custom serialization code to maintain, `n10s` is the de facto standard tool for this exact job. −Requires adding the `n10s` jar to the Neo4j image/plugins volume (one more moving part, but it lives entirely inside the already-owned `neo4j` service — no new container).

### Pattern 3: SWRL RDF vocabulary as the Metagraph translation target

**What:** Map `Rule`→`swrl:Imp`, `HAS_BODY`/`HAS_HEAD`→`swrl:body`/`swrl:head` (`swrl:AtomList`), `Atom` (by kind)→`swrl:ClassAtom`/`swrl:DatavaluedPropertyAtom`/`swrl:BuiltinAtom`, `ARG`→`swrl:argument1`/`argument2`, `Var`→`swrl:Variable`.
**When to use:** For the Metagraph half of the Neo4j→RDF translation — the OntoGraph half has no equivalent standard shortcut (see Critical Finding).
**Trade-offs:** +Standard, tool-recognized vocabulary (Protégé, OWL API SWRL support). −SWRL rule *execution* (not just structural representation) is only supported by Pellet among the two reasoners in scope, and is out of scope for v8.2 per PROJECT.md (TBox-only: satisfiability/domain-range/coherence, not rule firing) — don't let this pattern tempt scope creep into "run the actual SWRL rules through the reasoner" this milestone.

## Data Flow

### Reasoning Run Flow (Reasoner screen "Run" action, replacing the v8.1 placeholder)

```
[User clicks "Run" on Reasoner screen, project X selected]
    ↓
ui-v2 Reasoner screen → POST /reasoner/run {project: "X", reasoner: "hermit"}
    ↓
data-service: ontology_export.py
    → Cypher via existing bolt driver: n10s.rdf.export.cypher(project-scoped query)
    → returns Turtle for OntoGraph (Classes/DatatypeProperties/ObjectProperties)
    → and Metagraph (Rules/Atoms via SWRL vocabulary mapping, Pattern 3)
    ↓
data-service: POST http://dg-reasoner:PORT/reason/consistency
    { static_owl: <DesignGrammar-V7.owl bytes>, dynamic_ttl: <above>, reasoner_id: "hermit" }
    ↓
dg-reasoner: owlready2 loads combined graph, sync_reasoner(reasoner="hermit")
    → { consistent: bool, unsatisfiable_classes: [...], explanations: [...] }
    ↓
data-service: persist run result (extend reasoner-settings.json pattern or new
    reasoner-runs.json, mirrors connectors.py's JSON-file persistence style)
    ↓
ui-v2: displays consistency result, unsatisfiable classes, explanations
```

### SHACL Validation Flow (data-level / instance validation, separate from OWL reasoning)

```
[Rule authored / DesignState published by VALIDATOR]
    ↓
data-service: shacl_validator.py (or dg-reasoner /shacl/validate)
    pulls ValidGraph DesignState/Run instance data + a SHACL shapes graph
    (shapes authored per-rule or derived from OntoGraph's now-flat schema —
    this is the natural place to ALSO capture domain/range/cardinality
    constraints if OntoGraph itself isn't extended with real axioms, see
    Critical Finding option (b))
    ↓
pySHACL validate(data_graph, shapes_graph) → conformance report
    ↓
Surfaced alongside SWRL VALIDATOR results — complementary, not a replacement
    (SHACL = closed-world instance shape checking; SWRL VALIDATOR = the
    existing rule-body/rule-head compliance check; OWL DL reasoner = open-world
    TBox coherence)
```

### CONNECTOR Component Credential Flow (new, additive)

```
[v8.1 Connectors screen] → POST /connectors/grasshopper/credentials
    → { credential_id, token: "dgc_..." }  (shown once, user pastes into GH canvas)
    ↓
[Grasshopper CONNECTOR component] new optional input "PlatformToken"
    ↓
SolveInstance (unchanged bolt path):
    Neo4jConnectorService.TryConnectAsync(Uri, User, Password, Database)
    → sets Database output exactly as today, regardless of token presence
    ↓
SolveInstance (new, parallel, best-effort):
    if PlatformToken is non-empty AND Connect==true:
        fire-and-forget POST /connectors/heartbeat
        Header: Authorization: Bearer <PlatformToken>
        → 200 { connector_id: "grasshopper", status: "active" }  (updates
          Connectors-screen "last_connection"/status — no effect on GH canvas)
        → 401 on bad/revoked token: log/surface as a non-blocking warning,
          bolt connection is UNAFFECTED
```

## Scaling Considerations

| Scale | Architecture Adjustments |
|-------|---------------------------|
| Single project, on-demand reasoning | Current sidecar-per-request pattern is fine — HermiT/Pellet runs as a short-lived subprocess per call, no persistent JVM needed |
| Multiple projects, reasoning triggered on every rule save | Consider caching the static `DesignGrammar-V7.owl` parse inside the sidecar process (owlready2 world) instead of re-parsing per request; still stateless per-project dynamic TTL |
| Frequent/interactive reasoning (e.g. live-as-you-type) | Would justify a persistent JVM process behind the sidecar (avoid subprocess spin-up cost each call) — not needed for v8.2's "run at rule-authoring time" trigger cadence described in PROJECT.md |

### Scaling Priorities

1. **First bottleneck:** JVM subprocess spin-up latency (HermiT/Pellet cold-start per reasoning call). Acceptable for an explicit "Run Reasoner" button click; would need a warm/pooled process if reasoning becomes automatic-on-every-save.
2. **Second bottleneck:** OntoGraph translation completeness (Critical Finding) — this is a correctness bottleneck, not a performance one, and will surface before any scale bottleneck does.

## Anti-Patterns

### Anti-Pattern 1: Running the OWL reasoner inside the Grasshopper (C#) plugin

**What people might try:** Since the CONNECTOR component already makes direct Neo4j bolt calls, it's tempting to also run reasoning there, close to the geometry.
**Why it's wrong:** HermiT/Pellet are Java (OWL API); there is no first-class .NET binding. Bridging via IKVM or a bundled JRE inside a Rhino/Grasshopper plugin process is fragile, bloats the `.gha` distribution, and ties reasoner lifecycle to Rhino's process — a crash or hang in reasoning would take down the user's Grasshopper session. Reasoning is also inherently a per-project, not per-solve, operation (rule-authoring time, not geometry-solve time per PROJECT.md) — it doesn't belong on the GH canvas's hot path at all.
**Do this instead:** Reasoning stays entirely server-side (`data-service` + `dg-reasoner` sidecar). The Reasoner screen in `ui-v2` is the only new consumer; Grasshopper is unaffected by this milestone's reasoning work.

### Anti-Pattern 2: Treating the platform-issued connector token as Neo4j authentication

**What people might try:** Since the token is new and "platform-issued," it's tempting to have the CONNECTOR component use it to fetch/derive Neo4j credentials, or to require it before allowing a bolt connection at all.
**Why it's wrong:** The v8.1 heartbeat contract (`POST /connectors/heartbeat`, `connectors.py`) is explicitly a **status/liveness signal**, not an authentication or credential-vesting mechanism — it authenticates only against `data-service`'s own token store (SHA-256 hash match), has zero knowledge of Neo4j credentials, and gating bolt connections on it would break offline/local-dev workflows (no platform reachable) and any existing `.gh` canvas that doesn't yet have the token wired in — a regression PROJECT.md's "zero v8.0 regressions" precedent explicitly guards against repeating.
**Do this instead:** Token and bolt credentials are **parallel, independent inputs** (see Data Flow above) — token drives only the Connectors-screen status dot; bolt inputs drive the actual `Database` output used by DESIGN STATE/VALIDATOR/etc. Token is optional; its absence is a no-op, not a failure.

## Integration Points

### External Services

| Service | Integration Pattern | Notes |
|---------|----------------------|-------|
| `dg-reasoner` (new sidecar) | Synchronous HTTP from `data-service`, same pattern as existing Speckle/n8n calls | New docker-compose service; needs `default-jre-headless` + `owlready2` + `pyshacl` |
| `neosemantics` (n10s, Neo4j plugin) | Cypher procedure calls (`n10s.rdf.export.cypher`) over the existing bolt driver `data-service` already holds | Plugin jar added to the `neo4j` service's plugins volume — no new container, but a `neo4j` image/config change |
| HermiT (via owlready2, bundled) | In-process default reasoner inside `dg-reasoner`, invoked via `sync_reasoner()` | Upstream HermiT itself hasn't been updated in ~6 years but remains the de facto standard (Protégé default, still shipped by owlready2) — HIGH confidence it's "the" standard choice, MEDIUM confidence on long-term upstream health |
| Pellet (via owlready2, bundled) | Alternate reasoner, `sync_reasoner_pellet()`, same in-process pattern | Also long-stalled upstream but still the standard SWRL-DL-safe-rule-capable option if future work needs actual rule execution (not needed for v8.2 scope) |
| pySHACL | In-process Python call (either inside `dg-reasoner` or `data-service` — see Structure Rationale) | Actively maintained (RDFLib org, releases into 2026), pure Python, no JVM |

### Internal Boundaries

| Boundary | Communication | Notes |
|----------|----------------|-------|
| `data-service` ↔ `dg-reasoner` | Synchronous HTTP, request/response, no queue (consistent with CLAUDE.md's "no message queue" decision) | Payload = static OWL bytes + dynamic Turtle + reasoner id; response = structured JSON result |
| `data-service` ↔ Neo4j (for RDF export) | Existing bolt driver, new Cypher calls to `n10s.rdf.export.cypher` | Reuses existing connection, no new credential surface |
| Grasshopper CONNECTOR ↔ `data-service` | Two independent calls: (1) existing direct Neo4j bolt (unchanged), (2) new optional HTTP heartbeat with `Authorization: Bearer dgc_...` | Confirmed exact contract from `data-service/app.py` `connector_heartbeat()` — header parsing is `Authorization: Bearer <token>`, already generic across all 14 registered connector ids including `"grasshopper"` |
| Reasoner screen (`ui-v2`) ↔ `data-service` | Existing `GET/PUT /reasoner/settings` (registry + selection) extends with a new `POST /reasoner/run` and `POST /shacl/validate` (or a combined `/reasoner/run` that returns both) | `reasoner.py`'s registry already has `status: "placeholder"` per reasoner — flip to `"integrated"` once wired, matching the code comment's stated intent |

## Suggested Build Order (informs roadmap phase sequencing)

This is presented here because the milestone context explicitly asks for it, and because it is blocking: skipping straight to UI wiring risks building a "Run Reasoner" button that always reports "consistent" and teaches users to distrust it.

1. **Spike/decision phase (architecture-only, no UI): resolve the Critical Finding.** Prototype the Neo4j→RDF translation for one real project's OntoGraph + Metagraph, load it into owlready2 alongside `DesignGrammar-V7.owl`, run HermiT, and confirm what it actually reports. Explicitly decide: (a) extend the LLM ingestion schema/prompts to emit real domain/range/subclass/disjoint axioms into OntoGraph, or (b) scope v8.2's reasoning to structural/referential checks only, or (c) some hybrid (author axioms by hand per project as a new authoring surface). This decision changes the shape of every phase after it.
2. **`dg-reasoner` sidecar skeleton + `n10s` plugin wiring.** Stand up the new container, install `n10s` on the `neo4j` service, prove the Cypher→RDF→owlready2→HermiT round trip end-to-end on a toy example (independent of the Critical Finding decision — this is pure plumbing).
3. **OntoGraph/Metagraph translation implementation**, shaped by step 1's decision.
4. **`/reasoner/run` endpoint + Reasoner screen UI wiring** (replace placeholder, per PROJECT.md's stated goal), consuming step 3's translator.
5. **SHACL layer** (`pySHACL`) — lower risk, can run in parallel with steps 1-3 once the ValidGraph instance-data extraction is defined; shapes can be authored independently of the OWL TBox question.
6. **CONNECTOR component token wiring** — fully independent of steps 1-5 (no shared code path), can be built and shipped in parallel at any point; the contract is already fully specified by the existing `/connectors/heartbeat` endpoint with zero backend changes required.

Steps 1-2 are the "likely needs deeper research" flag for the roadmap — everything from step 3 onward is comparatively standard integration work once the translation shape is settled.

## Sources

- [neosemantics (n10s) — Neo4j Labs](https://neo4j.com/labs/neosemantics/) — RDF import/export plugin for Neo4j, on-demand Cypher-scoped export, custom URI mapping — MEDIUM-HIGH confidence (official Neo4j Labs docs)
- [neosemantics GitHub](https://github.com/neo4j-labs/neosemantics) — confirms OWL2/RDFS/SKOS support, SHACL validation hooks exist at the plugin level too — MEDIUM confidence (community project under Neo4j Labs, not core product)
- [Owlready2 documentation — Reasoning](https://owlready2.readthedocs.io/en/latest/reasoning.html) — `sync_reasoner()` (HermiT default) and `sync_reasoner_pellet()`, both JVM-subprocess based, bundled jars — HIGH confidence (official docs)
- ["OWL Reasoners still useable in 2023" (arXiv 2309.06888)](https://arxiv.org/pdf/2309.06888) — HermiT upstream repo has had no commits in ~6 years but remains widely embedded/used (e.g. Protégé default) — MEDIUM confidence (single survey paper, but consistent with owlready2's continued bundling)
- [pySHACL GitHub (RDFLib)](https://github.com/RDFLib/pySHACL) — actively maintained, releases into January 2026, pure Python, uses `rdflib` + `OWL-RL` for OWL2-RL profile expansion — HIGH confidence (verified release cadence)
- AEC/BIM compliance-checking precedent: SHACL-over-ifcOWL patterns and "Semantic BIM Reasoner" (SBIM-Reasoner) architectures in the linked-building-data / BIM literature confirm SHACL (data-level shape validation) + OWL reasoning (TBox coherence) as complementary, commonly co-deployed layers in this exact domain — MEDIUM confidence (academic sources, pattern-level not code-level)
- Direct codebase inspection: `ontology/DesignGrammar-V7.owl`, `ontology/V7-INVESTIGATION.md`, `ontology/export_to_markdown_v7.py`, `cypher_template.txt`, `training/dataset_schema.json`, `spec/DATABASE.md`, `data-service/connectors.py`, `data-service/reasoner.py`, `data-service/app.py` (lines ~1057-1158), `DG/src/DG.Grasshopper/Components/ConnectorComponent.cs`, `docker-compose.yml` — HIGH confidence (primary source, this repository)

---
*Architecture research for: OWL 2 DL reasoning + SHACL validation integration; Grasshopper CONNECTOR credential wiring (Design Grammar System v8.2)*
*Researched: 2026-07-11*
