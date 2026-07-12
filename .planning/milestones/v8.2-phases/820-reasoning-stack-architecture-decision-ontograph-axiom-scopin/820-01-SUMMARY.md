---
phase: 820
plan: 01
status: complete
tasks_completed: 3
tasks_total: 3
---

# Plan 820-01 SUMMARY — Axiom-Scoping Spike

**Status:** Complete ✓ — All 3 tasks done. Spike evidence captured.

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

## Task 3 — Two-Part Reasoner Proof ✓

- **Commit:** `99cf3a5 feat(820-01): fix run_hybrid.py builtin stripping + capture HermiT reasoner evidence`
- **Naive run result:** 0 inconsistent classes. ASSERTION PASS — "the naive export reasons as trivially 'consistent'." This is the documented FALSE POSITIVE: the flat export carries no subClassOf/domain/range/disjointWith axioms, so no class can be unsatisfiable.
- **Hybrid run result:** 2 inconsistent classes: `[owl.Nothing, ex.SlidingDoor]`. ASSERTION PASS — "HermiT caught the seeded TBox contradiction that the naive export could not express."
- **Fix applied:** `run_hybrid.py` was missing the `strip_hermit_unsupported()` call that `run_naive.py` had — HermiT crashes on SWRL builtin atoms. Added import + stripping step (5 builtin-using rules stripped from both runs).
- **Runtime:** throwaway Docker container (`python:3.11-slim` + `openjdk-21-jre-headless`). Naive: 0.43s HermiT. Hybrid: 1.23s HermiT.
- **Evidence files:** `spike/output/naive_result.txt`, `spike/output/hybrid_result.txt`

## Self-Check

### must_haves Verification

| must_have | Status | Evidence |
|-----------|--------|----------|
| run_naive.py reports zero inconsistent classes | ✓ PASS | HermiT output: `Inconsistent classes: []`, Count: 0, 0.43s runtime |
| run_hybrid.py reports SlidingDoor unsatisfiable | ✓ PASS | HermiT output: `Inconsistent classes: [owl.Nothing, ex.SlidingDoor]`, Count: 2, 1.23s runtime |
| export.py scopes by label (captures mistagged atoms) | ✓ PASS | `export.py` uses `MATCH (a:Atom {project: $project})` label-scoped Cypher |
| rdflib-parsed axiom counts are authoritative | ✓ PASS | `axiom_counts.txt`: 65 subClassOf, 101 domain, 110 range, 0 disjointWith (rdflib-parsed, not grep) |
| Spike reproducible from README.md | ✓ PASS | `spike/README.md` documents env vars, container, run order |

### File Artifacts

| File | Exists | Source |
|------|--------|--------|
| `spike/requirements.txt` | ✓ | `pip freeze`-style with pinned versions |
| `spike/export.py` | ✓ | Label-scoped Cypher → RDFLib Turtle |
| `spike/run_naive.py` | ✓ | Owlready2 HermiT naive run |
| `spike/run_hybrid.py` | ✓ | Owlready2 HermiT hybrid+contradiction run (fixed builtin stripping) |
| `spike/README.md` | ✓ | Reproduction steps |
| `spike/output/naive_result.txt` | ✓ | HermiT output: 0 inconsistent classes |
| `spike/output/hybrid_result.txt` | ✓ | HermiT output: SlidingDoor unsatisfiable |
| `spike/output/axiom_counts.txt` | ✓ | rdflib-parsed TBox counts |
| `spike/output/naive_export.ttl` | ✓ | 25KB Turtle export |
| `spike/output/hybrid_export.ttl` | ✓ | 135KB Turtle export |

### Deviations

- None. All tasks complete. The original executor crashed mid-Task 3 (session limit); the run_hybrid.py builtin-stripping fix and Docker-based reasoner execution were completed in the continuation session.

## Key Files Created

- `.planning/phases/820-reasoning-stack-architecture-decision-ontograph-axiom-scopin/spike/requirements.txt`
- `.planning/phases/820-reasoning-stack-architecture-decision-ontograph-axiom-scopin/spike/export.py`
- `.planning/phases/820-reasoning-stack-architecture-decision-ontograph-axiom-scopin/spike/run_naive.py`
- `.planning/phases/820-reasoning-stack-architecture-decision-ontograph-axiom-scopin/spike/run_hybrid.py`
- `.planning/phases/820-reasoning-stack-architecture-decision-ontograph-axiom-scopin/spike/README.md`
- `.planning/phases/820-reasoning-stack-architecture-decision-ontograph-axiom-scopin/spike/output/axiom_counts.txt`
- `.planning/phases/820-reasoning-stack-architecture-decision-ontograph-axiom-scopin/spike/output/naive_export.ttl`
- `.planning/phases/820-reasoning-stack-architecture-decision-ontograph-axiom-scopin/spike/output/hybrid_export.ttl`
