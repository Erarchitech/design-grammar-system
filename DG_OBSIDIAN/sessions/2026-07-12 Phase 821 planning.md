---
date: 2026-07-12
phase: 821
title: Phase 821 planning (dg-reasoner sidecar & RDF translation)
status: complete
---

# Session: Phase 821 Planning

## Work completed

**Phase 821 plan created** — dg-reasoner sidecar & OntoGraph/Metagraph RDF translation. Fully inline workflow (user preference, no subagents).

### Artifacts created

- **821-RESEARCH.md** (320+ lines) — consolidates all technical guidance: pinned stack (owlready2, rdflib, pyshacl, neo4j, exact versions with justification), architecture patterns (sidecar topology, reasoning pipeline, translation mechanics, hybrid TBox union, HermiT builtin stripping, timeout isolation, data-service proxy), n10s install (two approaches: volume-mount jar or custom Dockerfile), common pitfalls (Turtle vs NTriples, label-scoped export, drift-immunity), code examples (Cypher skeletons, AtomList builder, Owlready2 reasoning), validation architecture (2-tier: unit fidelity + integration round-trip), environment setup, scope fences.

- **821-VALIDATION.md** — Nyquist compliance: test infrastructure (pytest 7.x, conftest fixtures), sampling rate (per-task unit, per-wave full), per-task verification map (5 tasks across 4 plans), Wave 0 requirements (fixtures, markers), manual-only verification (isolation property), sign-off checklist.

- **821-01-PLAN.md** — Wave 1 (sidecar scaffold + n10s + compose wiring)
  - Task 1: Dockerfile, requirements.txt, FastAPI app.py, health + stub routes, /health unit test
  - Task 2: neo4j n10s install (pinned jar), docker-compose dg-reasoner service + mount + env, smoke test
  - 2 tasks, 2 files per task, acceptance criteria + automated verify

- **821-02-PLAN.md** — Wave 2 (clean Cypher→RDF translator + structural fidelity)
  - Task 1: ontology_export.py per spec/LPG-OWL-MAPPING.md, label-scoped Cypher, swrl:AtomList, strip_hermit_unsupported
  - Task 2: committed fixture (metagraph_fixture.json) + pytest assertions (order + argument positions survive)
  - 2 tasks, no docker/JRE for CI gate

- **821-03-PLAN.md** — Wave 3 (hybrid reasoning core + routes)
  - Task 1: curated dg-disjointness.ttl overlay (real owl:disjointWith axioms, not seeded contradiction)
  - Task 2: reasoning.py (hybrid union TBox + overlay + live export, HermiT under timeout via multiprocessing, pySHACL stub)
  - Task 3: app.py routes (/reason/consistency + /shacl/validate contracts), route tests (monkeypatch HermiT, no JRE)
  - 3 tasks, all unit-testable except live reasoning (integration tier)

- **821-04-PLAN.md** — Wave 4 (proxy + live round-trip proof)
  - Task 1: data-service proxy route (POST /reasoner/consistency, short httpx timeout, D-06/D-12 isolation)
  - Task 2: live integration round-trip (v8-ui-smoke project, drift-immunity assertion on R_DOOR_ORIENTATION_V atoms, D-16)
  - 2 tasks, integration tier only

### Verification gates passed

- ✅ **Decision coverage 16/16** — all D-01…D-16 decisions cited in must_haves
- ✅ **REAS-05 requirement** — covered by all 4 plans
- ✅ **Quality gate** — no fenced code blocks inside `<action>` tags
- ✅ **Task completeness** — every task has `read_first` + `acceptance_criteria` + `verify`
- ✅ **Goal-backward** — all 4 success criteria map to concrete plans/verify-commands

### Key decisions (no new ADRs — all locked in CONTEXT.md)

- **n10s installation:** pinned neo4j:5.26 + baked jar in Dockerfile (not flaky NEO4J_PLUGINS env, per docker-neo4j#489)
- **Real disjointness overlay:** not spike's seeded contradiction — genuine owl:disjointWith axioms for production
- **2-tier validation:** unit fidelity (CI-able, no JRE) + integration round-trip (live docker, with JRE)
- **Drift-immunity regression:** D-16 pins the two known-mistagged R_DOOR_ORIENTATION_V atoms as test assertion

### Memory update

Updated [[gsd-prefer-inline-over-subagents]] to record that user chose "Fully inline" for plan-phase 821 (reinforcing prior rejection of gsd-roadmapper subagent on 2026-07-02). Preference generalizes to plan-phase's researcher/planner/checker roles, not just roadmapper.

## Next steps

- Commit phase planning artifacts
- `/gsd-execute-phase 821` to run Plans 01–04 across Waves 1–4 (user's preference: inline, no subagents)
- After execute phase, `/gsd-verify-work` to confirm all success criteria met

## Session metadata

**Model:** claude-haiku-4-5-20251001 (user selected via `/model`)

**Changed files:** 6 plan/validation files + 1 memory file + STATE.md (touched by gsd-tools)
