# Phase 820 Spike — OntoGraph Axiom-Scoping Proof (THROWAWAY)

Empirical evidence for REAS-04's hybrid axiom-scoping decision:

- **Part (a)** `run_naive.py` — a naive flat export of live OntoGraph/Metagraph data
  reasons as trivially "consistent" (the documented false positive: no axioms connect
  the flat domain terms, so nothing can be unsatisfiable).
- **Part (b)** `run_hybrid.py` — the hybrid approach (static `DesignGrammar-V7.owl`
  TBox + live export + curated `ex:Door owl:disjointWith ex:Window` + seeded
  `ex:SlidingDoor rdfs:subClassOf` both) makes HermiT flag `ex:SlidingDoor` as
  unsatisfiable — the non-trivial result the naive export missed.

> **This spike is throwaway.** It is explicitly NOT the seed of `dg-reasoner` —
> Phase 821 builds clean against `spec/LPG-OWL-MAPPING.md`.

## Environment variables (never hardcode the password)

| Variable | Default | Notes |
|---|---|---|
| `NEO4J_URI` | `bolt://neo4j:7687` | Works on the docker-compose network; use `bolt://host.docker.internal:7687` or `bolt://localhost:7687` from outside it |
| `NEO4J_USER` | `neo4j` | |
| `NEO4J_PASSWORD` | `12345678` | Dev-only default matching `docker-compose.yml`'s `NEO4J_AUTH`; set the env var for anything non-dev |
| `PROJECT` | `v8-ui-smoke` | Target project (the one with the most rules per RESEARCH); can also be passed as `python export.py <project>` |
| `DG_OWL_PATH` | `<repo>/ontology/DesignGrammar-V7.owl` | Static TBox location (auto-resolved from the spike dir) |

**Caution:** the spike targets `v8-ui-smoke` (QA/smoke-test data). If you re-run it
against a real client project, do NOT commit the exported `.ttl` files — they contain
that project's rule bodies (T-820-02).

## JRE-17 throwaway container (required for the reasoner steps)

No JRE is installed on the dev host. Owlready2's `sync_reasoner()` shells out to its
bundled HermiT JAR, which needs Java 17. Run the whole spike inside a throwaway
container instead of installing a JRE on the host:

```bash
# 1. Find the compose network (so bolt://neo4j:7687 resolves):
docker network ls   # -> design-grammar-system_default

# 2. Run the spike (from the repo root; mounts the repo at /repo):
docker run --rm --network design-grammar-system_default \
  -v "<absolute-repo-path>:/repo" \
  -w /repo/.planning/phases/820-reasoning-stack-architecture-decision-ontograph-axiom-scopin/spike \
  python:3.11-slim bash -c "\
    apt-get update -qq && apt-get install -y -qq openjdk-17-jre-headless && \
    pip install -q -r requirements.txt && \
    python export.py --hybrid && \
    python run_naive.py && python run_hybrid.py"
```

If the container cannot join the compose network, fall back to
`-e NEO4J_URI=bolt://host.docker.internal:7687` (Neo4j publishes 7687 to the host).

The export step alone (`python export.py`) needs no JRE — only the two `run_*.py`
reasoner steps do.

## Run order

1. `pip install -r requirements.txt` (pinned: `owlready2==0.51`, `rdflib==7.6.0`, `neo4j==6.2.0`)
2. `python export.py` — writes `output/naive_export.ttl` + `output/axiom_counts.txt`
3. `python export.py --hybrid` — additionally writes `output/hybrid_export.ttl`
4. `python run_naive.py` — expect **no** inconsistent classes → `output/naive_result.txt`
5. `python run_hybrid.py` — expect **ex:SlidingDoor unsatisfiable** → `output/hybrid_result.txt`

## Key design points

- **Label-scoped Cypher (Pitfall 1):** the export scopes by node label
  (`n:Rule OR n:Atom OR ...`), never by the `graph` property — live `v8-ui-smoke`
  data has two `R_DOOR_ORIENTATION_V` atoms mistagged `graph:'OntoGraph'` that a
  `{project, graph:'Metagraph'}` query would silently drop. `export.py` asserts the
  exported atom count equals an independent label-based count.
- **rdflib-parsed axiom counts (Pitfall 2):** `axiom_counts.txt` counts actual RDF
  triples via a parser, not grep line-matches.
- **TBox-only contradiction (Pitfall 4):** no individuals are minted; the seeded
  contradiction lives entirely in class axioms.
- **Turtle → NTriples conversion in the run scripts:** Owlready2 cannot parse
  Turtle (it reads RDF/XML, OWL/XML, NTriples only), so `run_naive.py`/`run_hybrid.py`
  convert the canonical `.ttl` evidence files to `.nt` via rdflib before loading.
