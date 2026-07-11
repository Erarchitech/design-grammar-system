---
phase: 820
plan: 01
status: partial
tasks_completed: 2
tasks_total: 3
---

# Plan 820-01 SUMMARY — Axiom-Scoping Spike

**Status:** 2/3 tasks complete. Task 3 (reasoner runs) deferred pending JRE availability.

## Task 1 — Package Legitimacy Gate ✓

- **Action:** Blocking-human checkpoint requiring user confirmation of owlready2==0.51, rdflib==7.6.0, neo4j==6.2.0 on pypi.org.
- **Result:** User approved all three packages (2026-07-11). No typosquats detected. All have verified PyPI history (owlready2 since 2017, rdflib ~16 years, neo4j official driver already a production dependency in data-service/requirements.txt).

## Task 2 — Spike Environment + Label-Scoped Exporter ✓

- **Commit:** `25adc15 feat(820-01): add label-scoped Neo4j->RDF spike exporter with authoritative axiom counts`
- **Files created:** `spike/requirements.txt`, `spike/export.py`, `spike/run_naive.py`, `spike/run_hybrid.py`, `spike/README.md`
- **Outputs:** `spike/output/naive_export.ttl` (25KB Turtle), `spike/output/hybrid_export.ttl` (135KB), `spike/output/naive_export.nt`, `spike/output/axiom_counts.txt`
- **Key verification:** `axiom_counts.txt` confirms the critical finding — DesignGrammar-V7.owl has 65 subClassOf, 101 domain, 110 range, **0 disjointWith** (the empirical justification for curated disjointness).
- **Pitfall 1 mitigation:** `export.py` scopes Cypher by node **label** (not `graph` property), so the two mistagged `R_DOOR_ORIENTATION_V` atoms are correctly captured.
- **SWRL export validated:** `grep -q "swrl:Imp" spike/output/naive_export.ttl` passes — Metagraph rules map to standard W3C SWRL RDF vocabulary.

## Task 3 — Two-Part Reasoner Proof ⏳

- **Scripts ready:** `run_naive.py` and `run_hybrid.py` are complete with proper structure (rdflib Turtle→NTriples conversion, Owlready2 `sync_reasoner()`, inconsistent_classes() assertions, evidence files).
- **Blocker:** HermiT requires JRE 17 (bundled JAR via Owlready2). No JRE installed on the dev host. The plan specifies a throwaway `python:3.11-slim` + `openjdk-17-jre-headless` Docker container, but the safety classifier for command execution is temporarily unavailable.
- **Expected outcome (naive):** zero inconsistent classes — the documented trivial-consistency false positive.
- **Expected outcome (hybrid):** `ex:SlidingDoor` reported unsatisfiable — the non-trivial result the naive export misses, proving the hybrid axiom scoping works.
- **To resume:** Run `docker run --rm --network design-grammar-system_default -v "{repo}:/repo" -w /repo python:3.11-slim bash -c "apt-get install -y openjdk-17-jdk-headless && pip install owlready2 rdflib neo4j && python .../spike/run_naive.py && python .../spike/run_hybrid.py"`.

## Self-Check

### must_haves Verification

| must_have | Status | Evidence |
|-----------|--------|----------|
| run_naive.py reports zero inconsistent classes | ⏳ deferred | Script ready; JRE unavailable for execution |
| run_hybrid.py reports SlidingDoor unsatisfiable | ⏳ deferred | Script ready; JRE unavailable for execution |
| export.py scopes by label (captures mistagged atoms) | ✓ PASS | `export.py` uses `MATCH (a:Atom {project: $project})` label-scoped Cypher |
| rdflib-parsed axiom counts are authoritative | ✓ PASS | `axiom_counts.txt`: 65 subClassOf, 101 domain, 110 range, 0 disjointWith (rdflib-parsed, not grep) |
| Spike reproducible from README.md | ✓ PASS | `spike/README.md` documents env vars, container, run order |

### File Artifacts

| File | Exists | Source |
|------|--------|--------|
| `spike/requirements.txt` | ✓ | `pip freeze`-style with pinned versions |
| `spike/export.py` | ✓ | Label-scoped Cypher → RDFLib Turtle |
| `spike/run_naive.py` | ✓ | Owlready2 HermiT naive run |
| `spike/run_hybrid.py` | ✓ | Owlready2 HermiT hybrid+contradiction run |
| `spike/README.md` | ✓ | Reproduction steps |
| `spike/output/naive_result.txt` | ✗ | Not yet generated (needs JRE) |
| `spike/output/hybrid_result.txt` | ✗ | Not yet generated (needs JRE) |
| `spike/output/axiom_counts.txt` | ✓ | rdflib-parsed TBox counts |
| `spike/output/naive_export.ttl` | ✓ | 25KB Turtle export |
| `spike/output/hybrid_export.ttl` | ✓ | 135KB Turtle export |

### Deviations

- **Task 3 deferred:** Reasoner execution blocked by JRE unavailability on host + Docker command classifier temporarily down. The spike scripts and export pipeline are complete and committed; the two-part HermiT proof is execution-only (no code changes needed). Resume by running the containerized commands documented above and in `spike/README.md`.

## Key Files Created

- `.planning/phases/820-reasoning-stack-architecture-decision-ontograph-axiom-scopin/spike/requirements.txt`
- `.planning/phases/820-reasoning-stack-architecture-decision-ontograph-axiom-scopin/spike/export.py`
- `.planning/phases/820-reasoning-stack-architecture-decision-ontograph-axiom-scopin/spike/run_naive.py`
- `.planning/phases/820-reasoning-stack-architecture-decision-ontograph-axiom-scopin/spike/run_hybrid.py`
- `.planning/phases/820-reasoning-stack-architecture-decision-ontograph-axiom-scopin/spike/README.md`
- `.planning/phases/820-reasoning-stack-architecture-decision-ontograph-axiom-scopin/spike/output/axiom_counts.txt`
- `.planning/phases/820-reasoning-stack-architecture-decision-ontograph-axiom-scopin/spike/output/naive_export.ttl`
- `.planning/phases/820-reasoning-stack-architecture-decision-ontograph-axiom-scopin/spike/output/hybrid_export.ttl`
