# Stack Research

**Domain:** OWL 2 DL reasoning + SHACL validation for a Python FastAPI service (Design Grammar System v8.2)
**Researched:** 2026-07-11
**Confidence:** MEDIUM (web search + official PyPI metadata cross-checked across multiple independent sources; Context7/Exa MCP tools were unavailable in this session, Perplexity MCP returned 401 — see Gaps)

## Recommended Stack

### Core Technologies

| Technology | Version | Purpose | Why Recommended |
|------------|---------|---------|-----------------|
| **Owlready2** | 0.51 (2026-06-22) | Load `DesignGrammar-V7.owl`, run real OWL 2 DL reasoning (class satisfiability, property domain/range coherence, TBox consistency) | Only Python package that gives genuine OWL 2 DL completeness — it embeds HermiT (and Pellet) as bundled JARs and drives them via `sync_reasoner()`/`sync_reasoner_pellet()`, so you get Java-grade reasoning correctness with a Python call, no separate service to stand up, deploy, or version-pin against a triple store |
| **HermiT** (bundled inside Owlready2) | ships with Owlready2 0.51's `hermit/` dir | Default OWL 2 DL reasoner — consistency checking, classification | Reference-quality hypertableau reasoner; in published reasoner benchmarks it is the strongest of the classic open reasoners for consistency checking (on par with or ahead of Pellet), and it's the one Owlready2 calls by default — zero extra config |
| **Openllet** (not stock Pellet) | latest tag from `Galigator/openllet` | Second OWL 2 DL reasoner for cross-validation / incremental classification, if a second engine is wanted per the milestone's "HermiT and/or Pellet" phrasing | Stock Pellet (`stardog-union/pellet`) is effectively unmaintained (dual AGPL/commercial, infrequent releases) and scores worst in reliability benchmarks (datatype/syntax errors on ~17% of test ontologies). Openllet is Pellet 2.0's actively-referenced community fork, measurably more reliable, and is drop-in swappable for Owlready2's `sync_reasoner_pellet()` JAR path — use it instead of, not alongside, "Pellet" |
| **pySHACL** | 0.40.0 | SHACL Core + SHACL-SPARQL validation of design-rule/instance RDF data | Pure Python, no JVM, actively maintained (RDFLib org), pip-installable, sufficient feature coverage for data-shape validation (min/max count, datatype, pattern, node/property shapes, SPARQL-based constraints) — this is the layer requested for "data-level design-rule/instance validation" |
| **RDFLib** | 7.6.0 (2026-02-13) | RDF graph container that Owlready2's quadstore, pySHACL, and any Neo4j→RDF export code share as the common in-memory graph type | Already a transitive dependency of pySHACL (`rdflib>=7.3.0,<8.0`); pinning it explicitly keeps the two libraries' RDF graph objects interoperable |
| **owlrl** | 7.6.2 (2026-07-08) | OWL 2 RL forward-chaining expansion — pySHACL's own dependency, and optionally a cheap pre-pass before SHACL validation | Pull in transitively via pySHACL; do **not** treat it as a substitute for HermiT/Openllet — it only implements the RL profile (incomplete), not full DL satisfiability/consistency checking, so it cannot fulfil the "TBox integrity" requirement on its own |

### JVM Dependency (needed, but scoped down)

| Component | Version | Purpose | Why Recommended |
|-----------|---------|---------|-----------------|
| **OpenJDK headless JRE** | 17-jre-headless (Debian package, matches `python:3.11-slim`'s apt base) | Runtime for the HermiT/Openllet JARs that Owlready2 shells out to | HermiT's own compatibility floor is Java 1.5+, so any current LTS JRE works — pick 17 because it's what Debian bookworm/trixie (the base under `python:3.11-slim`) ships as `openjdk-17-jre-headless`, keeping the `apt-get install` list short and matching what most current Debian mirrors carry. Adds ~200MB to the image layer, no persistent Java process — the JVM starts, reasons, and exits per `sync_reasoner()` call inside the same FastAPI process's subprocess |

## Supporting Libraries

| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| `owlready2[NLTK]` extras — **skip** | — | NLTK/nlp integration | Not needed; DG doesn't need Owlready2's NL-annotation features |
| `rdflib-jsonld` / `pyoxigraph` (pySHACL extras) | optional | Faster/alternate RDF store backends for pySHACL (`oxigraph` extra) | Only if the `DesignGrammar-V7.owl` TBox plus a Neo4j-derived ABox export grows large enough that RDFLib's default in-memory store becomes a bottleneck (unlikely at DG's current 3,130-line/182KB ontology scale) |
| `pyduktape2` (pySHACL `js` extra) | optional | SHACL-JS constraint components | Skip unless a future rule author needs JS-based SHACL constraints — DG's rule shapes so far map cleanly to SHACL Core/SPARQL |

## Development Tools

| Tool | Purpose | Notes |
|------|---------|-------|
| `apt-get install openjdk-17-jre-headless` in `data-service/Dockerfile` | Provides the JVM that Owlready2's bundled HermiT/Openllet JARs shell out to | One line added to the existing `apt-get install build-essential` step — no new base image, no new compose service |

## Installation

```bash
# data-service/Dockerfile — add before pip install
RUN apt-get update && apt-get install -y \
    build-essential \
    openjdk-17-jre-headless \
    && rm -rf /var/lib/apt/lists/*
```

```txt
# data-service/requirements.txt — additions
owlready2==0.51
pyshacl==0.40.0
rdflib==7.6.0
owlrl==7.6.2
```

```bash
pip install owlready2==0.51 pyshacl==0.40.0 rdflib==7.6.0 owlrl==7.6.2
```

No Grasshopper/C# NuGet additions needed for the reasoning/SHACL work — that's entirely `data-service`-side (see below for the CONNECTOR credential wiring, which also needs no new packages).

## Alternatives Considered

| Recommended | Alternative | When to Use Alternative |
|-------------|-------------|--------------------------|
| Owlready2 (embeds HermiT/Pellet JARs, subprocess-per-call) | Apache Jena + Fuseki as a live triple-store/SPARQL endpoint, HermiT via hand-rolled OWL API | Only if DG later needs a public/external SPARQL endpoint serving RDF consumers beyond `data-service` itself, or needs a persistent queryable triple store independent of Neo4j — not indicated by current scope, since Neo4j remains the OntoGraph/Metagraph source of truth |
| pySHACL (pure Python) | TopBraid SHACL API (Java, Jena-based) | Only if a specific SHACL Advanced Feature pySHACL genuinely lacks becomes a hard requirement (custom target types, SHACL-JS, user-defined SPARQL functions) — adopting it means a *second* independent JVM dependency path alongside Owlready2's |
| HermiT as primary reasoner | ELK | Only as an optional fast pre-classification pass ahead of HermiT if the ontology grows large enough that HermiT's tableau classification becomes slow — not the case at DG's current size (3,130-line OWL file). ELK is EL-profile-only; using it alone risks silently missing consistency violations outside EL, since DG's ontology is not guaranteed EL-expressible |
| Owlready2 subprocess model | JPype / Py4j in-process JVM embedding | Only if reasoning becomes a high-frequency hot-path needing lower call latency than a subprocess launch — not the case here (reasoning runs at rule-authoring time, not per-request). JPype couples the JVM lifecycle to the FastAPI process itself (a JVM crash/OOM can take down the Python process), a worse failure-isolation story than Owlready2's subprocess-per-call |
| Everything inside `data-service` | A separate Java sidecar HTTP microservice (13th+ docker-compose service running Jena/OWL API/TopBraid behind a REST wrapper) | Only reconsider if reasoning load becomes CPU-heavy enough to need independent scaling from `data-service` — not indicated by DG's current ontology size or usage pattern |

## What NOT to Use

| Avoid | Why | Use Instead |
|-------|-----|-------------|
| **Apache Jena + Fuseki as a live triple-store/SPARQL-endpoint service** | Turns reasoning from a stateless library call into a standing JVM server: a new docker-compose service, ~1.2GB default JVM heap, its own health checks, port, and a second source of truth to keep in sync with Neo4j. DG's existing decision (`Single Neo4j DB with project isolation`) is that Neo4j *is* the source of truth for both OntoGraph (schema) and instance data — Jena would duplicate that role for no functional gain, since Owlready2 gets you the same HermiT/Pellet reasoning without a server | Owlready2, loading `ontology/DesignGrammar-V7.owl` as a reasoning-time side artifact |
| **HermiT via raw OWL API (hand-rolled Java)** | The proposed stack calls for "HermiT via OWL API" — but that's exactly what Owlready2's bundled `hermit/HermiT.jar` CLI wrapper already does internally (serializes to N-Triples, invokes HermiT's command-line interface, parses inferred axioms back). Writing a custom OWL API integration duplicates Owlready2's `reasoning.py` for no added capability | `owlready2.sync_reasoner()` / `sync_reasoner_pellet()` |
| **TopBraid SHACL API (Java, Jena-based)** | More SHACL-Advanced-Features-complete than pySHACL (custom target types, SHACL-JS, user-defined SPARQL functions) but it's a Jena-dependent JAR — adopting it means a *second* JVM dependency path alongside Owlready2's, doubling the JVM surface for marginal spec coverage DG doesn't need yet | pySHACL |
| **ELK as the primary/only reasoner** | EL-profile only — sound and complete solely for OWL 2 EL. DG's ontology encodes property domain/range coherence and TBox restrictions typical of a light DL ontology, not guaranteed to be EL-expressible; using ELK alone risks silently missing consistency violations outside EL | HermiT as primary; ELK only as an optional pre-classifier if scale later demands it |
| **JPype / Py4j in-process JVM embedding** | Lower call latency than a subprocess launch but couples the JVM lifecycle to the FastAPI process (crashes/OOMs in the JVM can take down the Python process; multiprocess/uvicorn worker interaction is a known pain point), buying nothing Owlready2 doesn't already provide for occasional, rule-authoring-time reasoning calls | Owlready2's subprocess-per-call model — simpler failure isolation |
| **A separate Java sidecar HTTP microservice** | Matches DG's "no message queue, synchronous HTTP" philosophy on paper, but adds a whole new service to the 12+-service compose stack, a new nginx route, its own Dockerfile/base image, and a network hop for what is, in Owlready2, a single Python function call | Keep reasoning inside `data-service` |

## Stack Patterns by Variant

**If DG later needs a public/external SPARQL endpoint (RDF consumers beyond `data-service`):**
- Add Apache Jena Fuseki as its own compose service at that point
- Because that's a genuinely different requirement (live queryable triple store for third parties) than the milestone's rule-authoring-time TBox consistency check, and shouldn't be bundled into this decision preemptively

**If a specific SHACL Advanced Feature becomes a hard requirement (SHACL-JS, custom target types, user-defined SPARQL functions):**
- Reconsider TopBraid SHACL API as a sidecar
- Because pySHACL's Core+SPARQL coverage is sufficient for DG's current rule-shape patterns, but is not 100% spec-complete

## JVM-vs-Python Verdict

**A JVM (JRE) is unavoidable if "real OWL 2 DL reasoning" is the goal — but only as a headless runtime `apt-get install`'d into the existing `data-service` container, not as a new service.**

No pure-Python library implements complete OWL 2 DL reasoning today. `owlrl`/RDFLib+OWL-RL only cover the OWL 2 RL profile (forward-chaining, incomplete for full DL — cannot certify TBox consistency or full class satisfiability, which is explicitly what the milestone asks for). So the real choice isn't "JVM vs. no JVM," it's **"JVM as an embedded, per-call subprocess (Owlready2) vs. JVM as a standing server (Jena/Fuseki/TopBraid)."**

- Owlready2 already ships HermiT and Pellet as JARs and shells out to `java` as a subprocess per `sync_reasoner()` call. This means:
  - `data-service`'s Dockerfile needs one added line: `apt-get install -y openjdk-17-jre-headless` (~200MB layer, no new compose service, no new port, no new nginx route).
  - The JVM process is transient — it starts, reasons over the ontology, prints inferred triples to stdout, and exits. It does not sit resident consuming RAM between requests, unlike Fuseki's persistent ~1.2GB-heap server.
  - Docker Compose footprint stays at the current service count (`data-service`, `neo4j`, `n8n`, `ollama`, `speckle-*`, the UI container); only the `data-service` image grows.
- The full RDF/OWL-native stack the user proposed (Jena as triple store + HermiT via OWL API + TopBraid SHACL + ELK) is the *general-purpose semantic-web toolkit* answer, appropriate when you need a live SPARQL endpoint serving external RDF consumers. DG doesn't — Neo4j remains the single source of truth for both the OntoGraph schema and Metagraph/rule data, and `DesignGrammar-V7.owl` is already a periodically-regenerated *export artifact* (produced by `ontology/apply_v7_rename.py` → `ontology/make_export_v7.py`, not a live Neo4j-synced triple store). Reasoning only needs to run against that TBox export at rule-authoring time, which is exactly Owlready2's use case: load a `.owl` file, reason, read back inferred axioms/inconsistencies, discard the in-memory graph.

**Recommendation: Owlready2 (HermiT default, Openllet optional second engine) + pySHACL. Skip Jena/Fuseki/TopBraid entirely.** Revisit only if DG later needs a public SPARQL endpoint or SHACL Advanced Features that pySHACL genuinely lacks.

## Architecture Note (bearing on how the stack gets wired in)

- `ontology/DesignGrammar-V7.owl` (182KB, 3,130 lines, valid RDF/XML OWL, confirmed by direct read) plus its `-BOT-extension`, `-Topologic-extension`, and `-standards-extension` siblings are already real, versioned OWL files — not a stub. They're regenerated by scripts (`apply_v7_rename.py`, `apply_v7_extensions.py`, `make_export_v7.py`), i.e. a **build-time/manual export pipeline**, not something live-synced off Neo4j on every rule change.
- The milestone's reasoning scope (class satisfiability, property domain/range coherence, TBox integrity "at rule-authoring time") is a **TBox-only** concern — it only needs the schema-level `.owl` export, not a full ABox dump of every Neo4j rule/atom instance. This matches the downstream guidance: keep Neo4j as source of truth, treat the `.owl` file purely as a reasoning-time side artifact that `data-service/reasoner.py` loads with Owlready2 on demand (e.g. when a rule-authoring session requests a consistency check), not something requiring a persistent triple store.
- SHACL validation (data-level design-rule/instance checking) is a separate concern from TBox reasoning: it needs an RDF *data graph* representing the specific rules/atoms/design-state instances being checked, which today live only as Neo4j property-graph nodes (not RDF triples). This will require a small, scoped Cypher→RDF projection step (e.g. serialize the relevant `Rule`/`Atom`/`Var`/`Literal` subgraph to an in-memory RDFLib graph) feeding pySHACL — a phase-level design task, flagged here as the one piece of net-new "translation" code this milestone needs, not a stack gap.
- `data-service/reasoner.py` already has the right shape to extend: keep `REASONER_REGISTRY` (add `"status": "integrated"` once wired) and the JSON-settings persistence pattern; add the actual `owlready2` call behind the existing `hermit`/`pellet` (→ rename value or map to Openllet) ids rather than introducing a new settings file.

## Grasshopper / C# Side — Platform Credential in CONNECTOR

`DG/src/DG.Grasshopper/Components/ConnectorComponent.cs` (185 lines, `#if GRASSHOPPER_SDK`-gated) currently takes 6 raw inputs (`Neo4jURI`, `Neo4jUser`, `Neo4jPassword`, `Database`, `PROJECT NAME`, `Connect` trigger) and calls `INeo4jConnectorService.TryConnectAsync` directly against bolt — no relation to `data-service`'s credential system today. Separately, `DG/src/DG.Grasshopper/Validation/ValidationPublishClient.cs` already establishes the pattern for calling `data-service` from a GH component: a static `HttpClient`, `System.Net.Http.Json` (`PostAsJsonAsync`), `System.Text.Json` with camelCase naming, hitting `{dataServiceUrl}/validation/publish` directly on port 8000 (bypassing nginx, matching `docker-compose.yml`'s `data-service` port mapping `8000:8000`).

**No new NuGet packages required** — `System.Net.Http`/`System.Net.Http.Json`/`System.Text.Json` are already referenced and used exactly this way in `ValidationPublishClient.cs`.

| Addition | Purpose | Why this shape |
|----------|---------|-----------------|
| New `pManager.AddTextParameter("Credential", "Token", "Platform-issued connector credential (dgc_...)", ...)` input | Accept the `dgc_`-prefixed token minted by the v8.1 Connectors screen (`data-service/connectors.py::create_credential`) | Token format, SHA-256-hash-at-rest, and `dgc_` prefix are an already-shipped, tested pattern (`CredentialCreatedResponse`) — reuse it verbatim rather than inventing a second credential shape for Grasshopper |
| A small `ConnectorCredentialClient` (mirrors `ValidationPublishClient`'s static-`HttpClient` shape) calling `POST {dataServiceUrl}/connectors/heartbeat` with `Authorization: Bearer {token}` | Validate the token and report connector liveness before/alongside the bolt connect attempt | This endpoint already exists (`data-service/app.py:1105`, `connector_heartbeat`), is bearer-token-authenticated, returns 401 on invalid/revoked tokens (`CONNB-03`), and derives `active`/`stale`/`never_connected` status server-side — no new backend endpoint needed for credential *validation* |
| **Open design question (not a stack gap, a phase-level decision):** the heartbeat endpoint authenticates and timestamps a token but does not currently *vend* Neo4j bolt URI/user/password. Today those still need to come from explicit inputs or environment/config. Decide in phase planning whether (a) CONNECTOR keeps explicit Neo4j fields alongside the new credential input (credential = auth/telemetry only, current milestone scope), or (b) a new `data-service` endpoint is added later to exchange a `dgc_` token for provisioned Neo4j connection details (bigger scope, likely out of v8.2) | — | Flagging so the roadmap doesn't silently assume credential-vending is in scope; the connector registry already lists `grasshopper` as connector id `"grasshopper"` under `"VPL Platforms"`, so wiring CONNECTOR to call `/connectors/heartbeat` with that context is consistent with the existing 14-connector/5-category model |

## Version Compatibility

| Package A | Compatible With | Notes |
|-----------|-----------------|-------|
| `pyshacl==0.40.0` | `rdflib>=7.3.0,<8.0`, `owlrl>=7.6.2,<8`, Python >=3.9 | Pin `rdflib==7.6.0` and `owlrl==7.6.2` to stay inside pySHACL's declared ranges |
| `owlready2==0.51` | Python 3 (any recent 3.x incl. 3.11, matching `data-service`'s `python:3.11-slim` base); bundled HermiT/Pellet JARs need Java 1.5+ | Any current OpenJDK LTS (17, or 11/21) satisfies HermiT's floor — 17 recommended purely for matching Debian bookworm/trixie's default `openjdk-17-jre-headless` apt package under `python:3.11-slim` |
| `openjdk-17-jre-headless` (apt) | `python:3.11-slim` (Debian-based) | Headless variant avoids pulling in X11/GUI deps; confirm the exact package name against whichever Debian release `python:3.11-slim` currently tracks at build time (`apt-cache search openjdk`) since Debian's default-JDK alias can shift between bookworm/trixie |
| Owlready2 + pySHACL sharing RDFLib graphs | Both accept/produce standard RDFLib `Graph` objects | If a rules/atoms subgraph is serialized once into an RDFLib graph, both the OWL-reasoning path and the SHACL-validation path can consume it without a second parse — worth designing the Cypher→RDF projection step as a single shared function rather than two |

## Sources

- https://pypi.org/pypi/owlready2/json — official PyPI metadata, version/date confirmed directly (HIGH-confidence source, MEDIUM-confidence overall tier per this session's classify-confidence seam since fetched via WebFetch not Context7)
- https://pypi.org/pypi/pyshacl/json — official PyPI metadata, version + `requires_dist` confirmed directly
- https://pypi.org/pypi/rdflib/json — official PyPI metadata, version/date confirmed directly
- https://pypi.org/pypi/owlrl/json — official PyPI metadata, version/date confirmed directly
- https://owlready2.readthedocs.io/en/latest/reasoning.html — Owlready2 reasoning docs (sync_reasoner/sync_reasoner_pellet, JVM requirement, HermiT default)
- https://github.com/pwin/owlready2/tree/master/hermit — bundled HermiT jar/readme, Java 1.5+ compatibility note
- https://github.com/RDFLib/pySHACL — pySHACL README/repo, pure-Python SHACL validator claim
- https://github.com/TopQuadrant/shacl — TopBraid SHACL API scope (SHACL Advanced Features, SPARQL functions) vs pySHACL
- https://github.com/Galigator/openllet — Openllet as maintained Pellet 2.0 fork
- https://github.com/stardog-union/pellet — stock Pellet repo, confirms low release cadence
- arxiv.org/pdf/2309.06888 ("OWL Reasoners still useable in 2023") and DMKG/ISWC OWL2Bench-style reasoner comparison papers surfaced via WebSearch — Konclude/HermiT/Pellet/Openllet/ELK relative performance and reliability
- Apache Jena Fuseki Docker docs (`jena.apache.org/documentation/fuseki2/fuseki-docker.html`, `hub.docker.com/r/stain/jena-fuseki`) — default ~1200MiB JVM heap, standing-server deployment shape
- `data-service/reasoner.py`, `data-service/connectors.py`, `data-service/app.py` (this repo) — existing placeholder registry, credential/token pattern, `/connectors/heartbeat` endpoint (read directly, not web-sourced)
- `DG/src/DG.Grasshopper/Components/ConnectorComponent.cs`, `DG/src/DG.Grasshopper/Validation/ValidationPublishClient.cs` (this repo) — existing CONNECTOR component shape and the established HttpClient-to-data-service pattern
- `ontology/DesignGrammar-V7.owl` + `ontology/apply_v7_rename.py`, `ontology/make_export_v7.py` (this repo) — confirmed real RDF/XML OWL export artifact and its scripted (not live-synced) generation pipeline

---
*Stack research for: OWL 2 DL reasoning + SHACL validation, data-service (Python/FastAPI), v8.2 Connector Integration & Reasoning Engine*
*Researched: 2026-07-11*
