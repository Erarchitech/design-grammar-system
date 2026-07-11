---
phase: 821
slug: dg-reasoner-sidecar-ontograph-metagraph-rdf-translation
researched: 2026-07-12
confidence: HIGH
sources:
  - spec/LPG-OWL-MAPPING.md (normative mapping contract, REAS-04)
  - .planning/phases/820-.../820-DECISION.md (ADR-820-1 hybrid scoping, ADR-820-2 sidecar confirmed)
  - .planning/phases/820-.../spike/ (proven reference: export.py, README.md, run_*.py)
  - .planning/research/STACK.md + PITFALLS.md (pinned versions, known pitfalls)
  - data-service/ (structural template — Dockerfile, requirements.txt, app.py, reasoner.py)
  - docker-compose.yml (neo4j + data-service service definitions)
---

# Phase 821 — Research: dg-reasoner Sidecar & OntoGraph/Metagraph RDF Translation

> **What do I need to know to PLAN this phase well?** This consolidates the 820 spike
> evidence, the normative mapping spec, and the pinned stack into planning-ready guidance
> for building `dg-reasoner` clean. The spike code is throwaway reference, not a seed —
> Phase 821 builds against `spec/LPG-OWL-MAPPING.md`.

Requirement: **REAS-05** — a `dg-reasoner` sidecar in docker-compose exposing OWL 2 DL
consistency-check + SHACL-validation endpoints, isolated from `data-service`'s hot path.

---

## 1. Standard Stack (pinned, proven in the 820 spike)

| Package | Version | Role | Source of pin |
|---------|---------|------|---------------|
| `owlready2` | `0.51` | Loads TBox, runs HermiT via `sync_reasoner()`; exposes `inconsistent_classes()` | STACK.md + spike requirements.txt (proven) |
| `rdflib` | `7.6.0` | In-memory RDF graph the translator builds; shared with pySHACL | STACK.md (inside pySHACL's `>=7.3,<8` range) |
| `pyshacl` | `0.40.0` | Pure-Python SHACL Core+SPARQL validation (`POST /shacl/validate`) | STACK.md |
| `owlrl` | `7.6.2` | Transitive pySHACL dep; pin to stay in range (not a DL substitute) | STACK.md |
| `neo4j` | `6.2.0` | Bolt driver for label-scoped Cypher reads | spike requirements.txt (proven) |
| `fastapi` + `uvicorn` | (unpinned, mirror data-service) | Sidecar HTTP app | data-service/requirements.txt |
| `httpx` | (unpinned) | Only needed **in data-service** for the D-06 proxy — already a dep there | data-service/requirements.txt |
| **OpenJDK headless JRE** | `17` (apt `openjdk-17-jre-headless`) | Runtime HermiT's bundled JAR shells out to | STACK.md; spike proved JRE 21 also works (backward-compatible) |

**JRE note:** ROADMAP/CONTEXT specify "headless JRE 17". The 820 spike verified
`python:3.11-slim` (Debian trixie) + `openjdk-21-jre-headless` works (HermiT floor is Java 1.5+).
For the production image, pin `openjdk-17-jre-headless` per the ROADMAP criterion; if trixie's
apt no longer carries 17, `openjdk-21-jre-headless` is a proven fallback. Adds ~200MB, no
resident JVM — HermiT starts/reasons/exits per `sync_reasoner()` call.

`dg-reasoner/requirements.txt` (the clean sidecar set):
```
owlready2==0.51
rdflib==7.6.0
pyshacl==0.40.0
owlrl==7.6.2
neo4j==6.2.0
fastapi
uvicorn
```

**Package legitimacy:** all five pinned packages are established PyPI projects already
audited/approved in Phase 820 (owlready2 since 2017, rdflib 16-yr history, neo4j is the
official vendor driver already pinned in data-service; pyshacl/owlrl are RDFLib-org).
No new blocking-human legitimacy gate is needed — 820 cleared them.

---

## 2. Architecture Patterns

### 2.1 Sidecar topology (ADR-820-2, CONTEXT D-05/D-08)
Top-level `dg-reasoner/` mirroring `data-service/`: `Dockerfile`, `app.py`,
`ontology_export.py`, `reasoning.py` (owner's discretion on module split),
`requirements.txt`, `tests/`. The sidecar reads Neo4j **directly over bolt**
(same `NEO4J_URI/NEO4J_USER/NEO4J_PASSWORD` env vars as data-service) and owns the
whole pipeline: Cypher → RDFLib → hybrid union → HermiT. `data-service` only calls
`POST /reason/consistency {project}` through a thin proxy (D-06).

### 2.2 The end-to-end reasoning pipeline (per request)
```
POST /reason/consistency {project, engine=hermit}
  1. ontology_export.build_graph(session, project)   → rdflib.Graph (SWRL RDF, label-scoped)
  2. hybrid union: parse ontology/DesignGrammar-V7.owl (TBox) + ontology/dg-disjointness.ttl
                   (overlay) + the live export  → one rdflib.Graph
  3. strip_hermit_unsupported(graph)             → remove swrl:BuiltinAtom rules; count removed
  4. serialize graph to NTriples (temp file)     → Owlready2 CANNOT read Turtle
  5. owlready2 get_ontology("file://…nt").load(); sync_reasoner()   (subprocess w/ hard timeout)
  6. collect list(onto.inconsistent_classes())   → unsatisfiable_classes
  7. return {consistent, unsatisfiable_classes, axiom_counts, duration_ms, stripped_builtin_rules}
```

### 2.3 Translation mechanics (from `spec/LPG-OWL-MAPPING.md`, proven in spike `export.py`)
- **Label-scoped Cypher only** (never `graph` property). The two queries:
  ```cypher
  // Metagraph
  MATCH (n) WHERE n.project=$project AND (n:Rule OR n:Atom OR n:Var OR n:Literal OR n:Builtin) …
  // OntoGraph
  MATCH (n) WHERE n.project=$project AND (n:Class OR n:DatatypeProperty OR n:ObjectProperty) …
  ```
- **Node mapping:** `Rule`→`swrl:Imp`; `Atom.type`→`swrl:ClassAtom`/`DatavaluedPropertyAtom`/
  `IndividualPropertyAtom`/`BuiltinAtom`; `Var`→`swrl:Variable`; `Literal`→typed RDF literal;
  `Builtin`/`Class`/`Datatype`/`ObjectProperty`→reuse stored `iri`.
- **Edge reification (REAS-04 core):** `HAS_BODY`/`HAS_HEAD.order`→ordered `swrl:AtomList`
  (typed rdf:List first/rest chain); `ARG.pos`→`swrl:argument1/2` for binary atoms,
  `swrl:arguments` (rdf:List) **universally for BuiltinAtom** (arity varies: `continuousFromTo`,
  `towards` are 3-arg).
- **IRI minting:** `{base}/project/{project}/{rule|atom|var}/{key}`, base
  `http://example.org/design-grammar`; `ex:` domain vocab is a SEPARATE namespace from the
  `dg/dgm/dgv/dgs` meta-schema — do not conflate.
- **Namespace separation:** static TBox (`dg*:`) + domain vocab (`ex:`) + minted individuals
  are unioned only at reasoning time.

### 2.4 Hybrid union (ADR-820-1, CONTEXT D-03/D-04)
The live OntoGraph is a **flat vocabulary** (0 subClassOf/domain/range/disjointWith in Neo4j).
Real axioms come from the static TBox `ontology/DesignGrammar-V7.owl` (65 subClassOf, 101 domain,
110 range, **0 disjointWith**). Because disjointWith==0, consistency cannot meaningfully fail
without a curated overlay → `ontology/dg-disjointness.ttl` (D-04, new version-controlled file,
volume-mounted read-only per D-07). The round-trip proof runs the **full** union (TBox + overlay +
live export) so it is non-trivial — a live-only export is the 820-documented false positive.

### 2.5 HermiT builtin-atom stripping (mandatory, `spec/LPG-OWL-MAPPING.md` §Builtin exclusion)
HermiT rejects any ontology containing SWRL builtin atoms
(`java.lang.IllegalArgumentException: built-in atoms are not supported yet`). DG's violation
pattern is builtin-centric (nearly every rule has a `swrl:BuiltinAtom`), so the reasoner input
MUST strip every `swrl:Imp` transitively referencing a builtin atom, then prune orphaned
`swrl:Variable`/`swrl:Builtin`. The canonical export keeps the full mapping; only the reasoner
input is filtered. `stripped_builtin_rules` (the removed count) is a REQUIRED response field
(D-10). Reference: spike `export.py::strip_hermit_unsupported` (rebuild clean).

### 2.6 Timeout isolation (CONTEXT D-09)
`POST /reason/consistency` is synchronous with a hard server-side timeout (~60–120s, configurable
via env, e.g. `DG_REASONER_TIMEOUT_SECONDS`) that **kills the HermiT/JVM subprocess** and returns
a clean 504-style JSON. Owlready2 already shells HermiT out as a subprocess; enforce the wall-clock
bound by running `sync_reasoner()` inside a `multiprocessing.Process` (or `concurrent.futures`
process pool) joined with a timeout, then `terminate()` on expiry — killing the child kills its
java grandchild. No async job pattern in v8.2.

### 2.7 data-service proxy (CONTEXT D-06/D-12)
Thin route in `data-service/app.py` beside the existing `/reasoner/settings` (L1135-1158):
`POST /reasoner/consistency` → `httpx` POST to `http://dg-reasoner:8000/reason/consistency` with a
**short connect/read timeout** so a sidecar hang never blocks the Speckle-publish/validation hot
path. Sidecar is internal-only (no nginx route, no host port in 821). Env var
`DG_REASONER_URL=http://dg-reasoner:8000` (configurable). This proxy IS the "reachable from
data-service" success criterion; 822 builds the real UX on top.

---

## 3. n10s (neosemantics) install — install + smoke-verify ONLY (CONTEXT D-02)

n10s is **not** in the reasoning path (D-01 uses the custom RDFLib translator). Scope = add the
plugin to the `neo4j` service, verify its procedures respond. It remains a generic RDF
escape-hatch; no production code depends on it.

**Install method — deterministic (recommended):** `NEO4J_PLUGINS='["n10s"]'` auto-download is
documented but **flaky on some Neo4j 5.x** ([neo4j/docker-neo4j#489](https://github.com/neo4j/docker-neo4j/issues/489)
— n10s missing after `neo4j:5.18` install). Robust path per
[Labs install docs](https://neo4j.com/labs/neosemantics/installation/): drop a **pinned n10s jar**
into the plugins dir and allowlist its procedures. Two viable shapes (executor discretion):
  - **(A) mounted plugins volume** — `./neo4j/plugins:/plugins` with the pinned jar fetched by a
    documented one-liner (keeps `neo4j` as `image:`); OR
  - **(B) tiny custom `neo4j/Dockerfile`** — `FROM neo4j:5.26` + `curl` the matching n10s
    `5.26.x` jar into `/var/lib/neo4j/plugins/` (consistent with the repo's `build:` pattern for
    data-service/ui-v2; fully reproducible).

Recommend **pinning the neo4j image tag** (currently floating `neo4j:5`) to a specific `5.26.x`
LTS so the jar version matches — n10s releases are tagged per Neo4j version.

**Required config env** (compose `neo4j.environment`):
```
NEO4J_dbms_security_procedures_unrestricted: "n10s.*,apoc.*"   # if needed by the jar
NEO4J_dbms_security_procedures_allowlist: "n10s.*"             # (or whitelist on older tags)
```
`n10s.graphconfig.init()` requires a uniqueness constraint first:
`CREATE CONSTRAINT n10s_unique_uri IF NOT EXISTS FOR (r:Resource) REQUIRE r.uri IS UNIQUE`.

**Smoke-verify (the D-02 gate):** after the neo4j service is up, assert n10s procedures are
registered — `SHOW PROCEDURES YIELD name WHERE name STARTS WITH 'n10s' RETURN count(*)` returns
> 0; optionally create the constraint and `CALL n10s.graphconfig.init()` (writes only a
`_GraphConfig` node; harmless, off the production path). A pytest smoke test marked
`@pytest.mark.integration` (skipped when Neo4j unreachable) is the right home.

**Caveat:** graphconfig.init mutates the shared single Neo4j DB (adds `_GraphConfig`). Acceptable —
it is a config node, and n10s stays off DG's reasoning path. Note it in the plan.

---

## 4. Common Pitfalls (carried from 820 + spec)

1. **Turtle ≠ Owlready2 input.** Owlready2 reads RDF/XML, OWL/XML, NTriples only — **NOT Turtle**.
   Serialize the union to `.nt` via rdflib before `get_ontology(...).load()`. (Spike run scripts
   do exactly this.)
2. **Scope by label, never `graph` property.** Live `v8-ui-smoke` has two `R_DOOR_ORIENTATION_V`
   atoms mistagged `graph:'OntoGraph'`; a `{project, graph:'Metagraph'}` query silently drops them.
   Assert exported atom count == independent label-based count (spike does this).
2b. **Drift-immunity regression (D-16).** Those two mistagged atoms MUST appear in the export —
   the integration test pins them so any regression to graph-property scoping fails loudly.
3. **SWRL-incomplete atoms captured, not dropped.** Live data has atoms with zero `ARG` edges;
   OWL API/HermiT refuses argument-less atoms. Export them as annotated `SkippedRule`/`SkippedAtom`
   individuals (in the canonical TTL), excluded from the `swrl:Imp` mapping and from reasoner input.
4. **rdflib-parsed axiom counts, never grep.** Count RDF triples via a parser.
5. **HermiT needs the JRE.** Export alone needs no JRE; only `sync_reasoner()` does. The sidecar
   image bakes the JRE so this is intrinsic — but the *unit* fidelity tests (no reasoning) run
   JRE-free and are CI-able without docker.
6. **Never hardcode the Neo4j password.** Read from `os.getenv` with dev-safe defaults matching
   data-service. `dg-reasoner/` is committed to git.
7. **BuiltinAtom uses `swrl:arguments` (rdf:List) universally**, even for binary builtins — arity
   varies and the list form is strictly more general.

---

## 5. Code Examples (reference — rebuild clean per spec)

**Correct label-scoped export skeleton** (from spike `export.py`, the proven pattern):
```python
METAGRAPH_QUERY = """MATCH (n) WHERE n.project=$project
  AND (n:Rule OR n:Atom OR n:Var OR n:Literal OR n:Builtin)
  RETURN labels(n) AS labels, properties(n) AS props"""
# atom count guard (Pitfall 1):
if exported_atom_count != independent_label_count:
    raise AssertionError("scoping bug (Pitfall 1)")
```

**swrl:AtomList builder (preserves HAS_BODY/HAS_HEAD.order):**
```python
def make_atom_list(g, items):  # items already sorted by edge `order`
    if not items: return RDF.nil
    head = cur = BNode()
    for i, item in enumerate(items):
        g.add((cur, RDF.type, SWRL.AtomList)); g.add((cur, RDF.first, item))
        nxt = BNode() if i < len(items)-1 else RDF.nil
        g.add((cur, RDF.rest, nxt)); cur = nxt
    return head
```

**Owlready2 reasoning (Turtle→NT→load→reason):**
```python
g.serialize(destination=nt_path, format="nt")           # NOT turtle
onto = get_ontology(f"file://{nt_path}").load()
with onto:
    sync_reasoner()                                      # shells to HermiT JAR (needs JRE)
unsat = [c.iri for c in onto.inconsistent_classes()]    # excludes owl:Nothing per taste
```

**pySHACL (empty shapes → conforms):**
```python
from pyshacl import validate
conforms, results_graph, results_text = validate(data_graph, shacl_graph=empty_shapes_graph,
                                                  inference="none", advanced=False)
# empty shapes ⇒ conforms=True, results=[]  (D-11 plumbing proof)
```

---

## 6. Validation Architecture

> Nyquist Dimension 8 — how every success criterion is sampled by a test. Two tiers (CONTEXT
> D-13): deterministic unit fidelity (CI-able without docker) + a live integration round-trip.

| Tier | Home | Docker? | What it proves | Decisions |
|------|------|---------|----------------|-----------|
| **Unit fidelity** | `dg-reasoner/tests/test_ontology_export.py` | No | Structural: parse produced Turtle back with rdflib, walk each `swrl:AtomList` and assert atom sequence == `HAS_BODY`/`HAS_HEAD.order`; assert `swrl:argument1/2` == `ARG.pos` 1/2; BuiltinAtom uses `swrl:arguments`. Committed fixture exercises ≥1 multi-atom-body rule, a BuiltinAtom, both ARG positions. | D-13, D-14, D-15 |
| **n10s smoke** | `dg-reasoner/tests/test_n10s_smoke.py` (`@pytest.mark.integration`) | Yes (live neo4j) | n10s procedures respond; graphconfig init callable | D-02 |
| **Integration round-trip** | `dg-reasoner/tests/test_roundtrip_integration.py` (`@pytest.mark.integration`) | Yes (live neo4j + JRE) | Real `v8-ui-smoke` (16 rules) → Cypher export → RDFLib → hybrid union → Owlready2 → HermiT completes **without error** and returns a well-formed verdict; asserts drift-immunity (the 2 mistagged atoms present). | D-13, D-16 |

- **Structural assertions via RDFLib, no golden-file byte diffs** (D-14).
- Integration tests are **marked and skipped** when Neo4j is unreachable (D-15) — the unit tier is
  the always-on CI gate.
- **Sampling:** unit fidelity after every task commit; full pytest (incl. integration when docker
  is up) after each wave and before verify-work.

**Framework:** pytest (mirrors `data-service/tests/`). Quick command:
`pytest dg-reasoner/tests -m "not integration"`. Full: `pytest dg-reasoner/tests`.

---

## 7. Environment & Reproduction

- Compose network `design-grammar-system_default` — `bolt://neo4j:7687` resolves service-to-service.
- Dev creds (compose): `neo4j/12345678`. Never inline; `os.getenv` with these as defaults.
- Static TBox already exists: `ontology/DesignGrammar-V7.owl` (182KB), volume-mount `./ontology`
  read-only into the sidecar (D-07) so disjointness curation is edit+restart, no rebuild.
- On Windows + Git Bash prefix docker commands with `MSYS_NO_PATHCONV=1` (path mangling).
- `config.json` has `use_worktrees:false` → executors run sequentially on the main tree.

---

## 8. Scope Fences (NOT this phase)

- Reasoner-screen wiring / consistency UX → Phase 822 (REAS-06).
- Real SHACL shapes, severity mapping, ErrorMessageTemplates → Phase 823 (SHCL-01/02).
- LLM-ingestion axiom emission → deferred out of v8.2 (ADR-820-1).
- nginx exposure of the sidecar, async job pattern, n10s secondary export endpoint → deferred.
