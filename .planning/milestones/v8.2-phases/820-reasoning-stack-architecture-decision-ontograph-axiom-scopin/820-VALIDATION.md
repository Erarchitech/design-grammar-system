---
phase: 820
slug: reasoning-stack-architecture-decision-ontograph-axiom-scopin
status: approved
nyquist_compliant: true
wave_0_complete: false
created: 2026-07-11
approved: 2026-07-11
---

# Phase 820 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.
>
> **Phase character:** This phase ships no production code and no conventional unit-test
> suite — it ships two durable documents (`spec/LPG-OWL-MAPPING.md`, `820-DECISION.md`),
> two PROJECT.md Key Decisions edits, and one throwaway `spike/`. The "tests" for REAS-04
> are the spike's own reasoner-output assertions (`run_naive.py` / `run_hybrid.py`) plus
> grep-based structural checks over the two docs, backed by human review of their semantic
> correctness. `workflow.nyquist_validation` is absent from `.planning/config.json`
> (treated as enabled), so this contract documents the phase's actual verification
> mechanism rather than a pytest/xUnit suite. Source: `820-RESEARCH.md § Validation
> Architecture`.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | None — doc/spike phase. The spike's own `inconsistent_classes()` assertions serve as its "test"; the two documents are verified by grep for required structural elements plus manual semantic review. |
| **Config file** | none — spike scripts + docs are created in-phase (see Wave 0 Requirements) |
| **Quick run command** | `python spike/run_naive.py && python spike/run_hybrid.py` (inside the JRE-17 throwaway container per Plan 01) |
| **Full suite command** | same — the spike has exactly two runs, both required (naive expects trivially consistent; hybrid expects `ex:SlidingDoor` unsatisfiable) |
| **Estimated runtime** | ~30 seconds (HermiT load + reason over a small TBox; doc greps are sub-second) |

**Container note:** Owlready2 shells out to a bundled HermiT JAR needing a JRE, and no JRE
is installed on the dev host. The two run commands execute inside a throwaway container
(`python:3.11-slim` + `apt-get install -y openjdk-17-jre-headless`) attached to the
docker-compose network so `bolt://neo4j:7687` resolves. Full reproduction steps live in
`spike/README.md` (produced by Plan 01, Task 2).

---

## Sampling Rate

- **After every task commit (spike tasks):** re-run `python spike/run_naive.py && python spike/run_hybrid.py` after any change to `export.py`'s Cypher scoping — confirm the naive/hybrid before-after contrast still holds.
- **After every task commit (doc tasks):** re-run that task's grep gate against the doc it wrote (`spec/LPG-OWL-MAPPING.md`, `820-DECISION.md`, `.planning/PROJECT.md`).
- **After every plan wave:** both spike scripts must produce their expected before/after result before `820-DECISION.md` (Plan 03) is finalized; Plan 03 (wave 2) depends on Plan 01 + Plan 02 (wave 1).
- **Before `/gsd-verify-work`:** confirm both spike outputs exist as captured evidence (`spike/output/naive_result.txt`, `spike/output/hybrid_result.txt`, `spike/output/axiom_counts.txt`), plus that `spec/LPG-OWL-MAPPING.md` and both PROJECT.md Key Decisions edits exist.
- **Max feedback latency:** ~30 seconds (bounded by the two reasoner runs).

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| 820-01-01 | 01 | 1 | REAS-04 | T-820-SC | Package legitimacy human-confirmed on pypi.org before any `pip install`; never auto-approved | manual (blocking-human gate) | N/A — human gate, no automated command (see Manual-Only Verifications) | N/A (gate) | ⬜ pending |
| 820-01-02 | 01 | 1 | REAS-04 | T-820-01 | NEO4J_URI/USER/PASSWORD read from env only; literal password never inlined outside an `os.getenv` default | scripted assertion + file check | `test -s spike/output/naive_export.ttl && test -s spike/output/axiom_counts.txt && grep -qi "disjointWith" spike/output/axiom_counts.txt && grep -q "swrl:Imp" spike/output/naive_export.ttl` | ❌ W0 (script + output created this phase) | ⬜ pending |
| 820-01-03 | 01 | 1 | REAS-04 (spike proof a+b) | T-820-02 | TBox-only reasoning; captured output cites class names/counts only, no credentials | scripted assertion (reasoner output) | `test -s spike/output/naive_result.txt && test -s spike/output/hybrid_result.txt && grep -qi "SlidingDoor" spike/output/hybrid_result.txt` | ❌ W0 (run scripts + output created this phase) | ⬜ pending |
| 820-02-01 | 02 | 1 | REAS-04 (mapping spec) | T-820-04 | Live arity Cypher run with env creds, never hardcoded in the committed spec | grep structural + manual review | `test -s spec/LPG-OWL-MAPPING.md && grep -q "swrl:Imp" spec/LPG-OWL-MAPPING.md && grep -q "swrl:AtomList" spec/LPG-OWL-MAPPING.md && grep -q "swrl:argument1" spec/LPG-OWL-MAPPING.md && grep -q "swrl:arguments" spec/LPG-OWL-MAPPING.md && grep -qi "HAS_BODY" spec/LPG-OWL-MAPPING.md && grep -qi "ARG" spec/LPG-OWL-MAPPING.md` | ❌ W0 (spec created this phase) | ⬜ pending |
| 820-02-02 | 02 | 1 | REAS-04 (mapping spec) | T-820-03 | Illustrative examples are schema-derived, not live client rule bodies | grep structural + manual review | `grep -q "owl:Class" spec/LPG-OWL-MAPPING.md && grep -q "owl:AllDifferent" spec/LPG-OWL-MAPPING.md && grep -qi "distinctMembers" spec/LPG-OWL-MAPPING.md && grep -qi "informative" spec/LPG-OWL-MAPPING.md && grep -qi "ValidGraph" spec/LPG-OWL-MAPPING.md` | ❌ W0 (spec extended this phase) | ⬜ pending |
| 820-03-01 | 03 | 2 | REAS-04 (Key Decision) | T-820-05 | Evidence cites axiom counts + HermiT class names only — no connection strings/credentials/raw rule bodies | grep structural + manual review | `test -s 820-DECISION.md && grep -qi "Evidence" 820-DECISION.md && grep -qi "SlidingDoor" 820-DECISION.md && grep -qi "sidecar" 820-DECISION.md && grep -q "LPG-OWL-MAPPING.md" 820-DECISION.md` | ❌ W0 (decision doc created this phase) | ⬜ pending |
| 820-03-02 | 03 | 2 | REAS-04 (Key Decision) | T-820-06 | Scoped Edit matching exact existing row text; no whole-table Write | grep structural + manual review | `grep -q "820-DECISION.md" .planning/PROJECT.md && grep -q "LPG-OWL-MAPPING.md" .planning/PROJECT.md && grep "dg-reasoner" .planning/PROJECT.md | grep -q "Shipped" && grep -qi "hybrid" .planning/PROJECT.md` | ❌ W0 (PROJECT.md edited this phase) | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

*Paths in the Automated Command column are relative to repo root; the spike lives under
`.planning/phases/820-reasoning-stack-architecture-decision-ontograph-axiom-scopin/spike/`
(plans use the full path in their own `<verify>` blocks).*

---

## Wave 0 Requirements

Every REAS-04 verification target is created by this phase's own tasks — there is no
separable pre-execution test-scaffolding wave, so each Wave 0 item below is a phase
deliverable produced and verified in-flight (this is why `wave_0_complete: false` at
approval time). Carried over from `820-RESEARCH.md § Validation Architecture → Wave 0 Gaps`:

- [ ] `spike/export.py` — Cypher export scoped by node **label** (Pitfall 1 fix), created in Plan 01 Task 2
- [ ] `spike/run_naive.py` / `spike/run_hybrid.py` — the two-part spike proof scripts, created in Plan 01 Task 3
- [ ] `spec/LPG-OWL-MAPPING.md` — the durable mapping spec, created in Plan 02 (Tasks 1–2)
- [ ] `820-DECISION.md` — spike evidence write-up, created in Plan 03 Task 1
- [ ] JRE 17 availability for the reasoner runs — resolved via a throwaway `python:3.11-slim` + `openjdk-17-jre-headless` container (RESEARCH § Environment Availability), provisioned in Plan 01

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Package legitimacy of `owlready2==0.51`, `rdflib==7.6.0`, `neo4j==6.2.0` before `pip install` (Task 820-01-01) | REAS-04 (T-820-SC) | Supply-chain trust decision; the seam's downloads signal is genuinely unavailable, so a human confirms each package is an established, non-typosquat PyPI project. Blocking-human gate — never auto-approved. | 1. Open pypi.org/project/owlready2 — confirm 0.51, multi-year history (first release 2017), upstream repo. 2. pypi.org/project/rdflib — confirm 7.6.0, RDFLib org, 16-year history. 3. pypi.org/project/neo4j — confirm 6.2.0, official Neo4j vendor driver (already pinned in `data-service/requirements.txt`). 4. Confirm none are typosquats. Type "approved" to unblock the install. |
| Semantic correctness of the SWRL / reification / IRI / UNA mapping in `spec/LPG-OWL-MAPPING.md` (Tasks 820-02-01, 820-02-02) | REAS-04 (mapping spec) | The grep gates confirm the required SWRL/OWL terms are present, but the *correctness* of the mapping (edge-property reification of `ARG.pos` and `HAS_BODY/HAS_HEAD.order`, the `ex:` vs meta-schema namespace split, UNA handling) is documentation quality, reviewed by the planner / the Phase 821 reader before the real translator is built. | Read the spec end-to-end; confirm each Metagraph node/relationship maps to the correct SWRL RDF term, that the BuiltinAtom row reflects the live-verified arity, and that the label-scoping and UNA subsections are normatively stated. |
| Correctness of the two ADR entries and the PROJECT.md Key Decisions edits (Tasks 820-03-01, 820-03-02) | REAS-04 (Key Decision) | Greps confirm the required citations/terms exist, but the ADR reasoning quality and the accuracy of the flipped sidecar row / new hybrid row are decision-record correctness, reviewed by a human. | Read `820-DECISION.md`'s two ADR entries + Evidence subsections; confirm the evidence matches the captured spike output. Confirm PROJECT.md's `dg-reasoner` row now reads a `✓ Shipped — v8.2 Phase 820` outcome, the new hybrid row is present, and the CONNECTOR row is untouched. |

---

## Validation Sign-Off

- [x] All tasks have `<automated>` verify or Wave 0 dependencies — 6 of 7 tasks carry an automated grep/script gate; the one exception (820-01-01) is a checkpoint:human-verify gate with a documented `<human-check>`, exempt per the Nyquist checkpoint rule.
- [x] Sampling continuity: no 3 consecutive tasks without automated verify — only the single human gate lacks an automated command.
- [x] Wave 0 covers all MISSING references — the only MISSING automated command is the intentional blocking-human package gate; all deliverable files are tracked as Wave 0 items created in-phase.
- [x] No watch-mode flags — the two spike run commands are one-shot; no `--watch`.
- [x] Feedback latency < 30s
- [x] `nyquist_compliant: true` set in frontmatter

**Approval:** approved 2026-07-11
