# V8 Publication Contract — Milestone Integration Assessment

**Date:** 2026-09-13  
**Status:** Assessment only; no GSD phase artifacts created and no implementation started.

## Executive assessment

The proposed V8 publication-contract work should **not** be added to v9.0, v9.1, or v10.0 as an implementation phase. It is a cross-cutting **release/publication-integrity workstream** that cuts across already completed v9.0 foundations, future v9.1 presentation/orchestration work, and future v10.0 script-generation work.

Recommended disposition:

1. **Immediate prerequisite gate before activating or executing downstream work:** create a small, separately governed publication-contract alignment milestone after the currently planned v10.0 boundary, but allow a narrowly scoped **preflight compatibility slice** before v9.1/v10.0 activation.
2. Do not represent the entire V8 synchronization as a normal v9.0 phase: v9.0 is already structurally complete except for stale planning/UAT/verification bookkeeping and Phase 40 closeout.
3. Do not embed it in v9.1: v9.1 is a UI/component-composition milestone and assumes the v9.0 Computgraph contracts are stable.
4. Do not embed it in v10.0: v10.0 adds topology persistence, component knowledge, write commands, generation, editing, and graph-native structure rules; mixing publication-contract migration with those new runtime capabilities would make causality and verification unclear.
5. Treat the V8 contract as a **cross-milestone compatibility and publication baseline**. Its normative checks should gate downstream milestones, while the broader repository and manuscript synchronization should be executed as a distinct milestone/workstream.

The main reason is semantic rather than administrative: R15.4 now fixes evidence boundaries that affect the interpretation of existing and future features. Those boundaries must be established before new claims are layered on top, but they do not constitute the same product capability as v9.1 or v10.0.

## Current baseline

### GSD and milestone state

- Active milestone in `.planning/PROJECT.md`, `.planning/ROADMAP.md`, `.planning/REQUIREMENTS.md`, and `.planning/STATE.md`: **v9.0 AI Workflow Intelligence**.
- `STATE.md` says Phase 40 is the frontier and planning is stopped at “Phase 40 context gathered”.
- The roadmap lists v9.0 Phases 28–40, with Phases 29, 32, 32.1, 33, 34, 36, 37, 38, and 39 represented as complete or effectively complete in the detailed phase material, while the progress table remains stale for some of them.
- Phase 40 is still the formal v9.0 closeout phase: live E2E, provider switching, documentation, and graphify refresh.
- v9.1 is isolated and explicitly must not activate while v9.0 is in flight. It contains Phases 910–917 and 41 requirements.
- v10.0 is isolated and explicitly must not activate while v9.0 is in flight. It contains Phases 41–49 and 31 requirements.
- `.planning/release-map.json` does not exist. Therefore any new global phase number must not be treated as established solely by inference.

### Working-tree condition

The current repository has a very large dirty working tree, including changes and untracked files from parallel sessions, generated/build outputs, publication artefacts, GSD files, and graphify outputs. The current branch is `master`, at commit `5fc6c09aae42a307834ab6c54842ce9ef9a64319`, and is ahead of `origin/master` by 17 commits.

The tree must be treated as a shared workspace. Any future implementation needs an explicit baseline manifest and file-selection strategy; `git clean`, reset, broad checkout, or mass restoration is unsafe.

### Publication baseline

The publication repository is identified by the user as the current source of the V8 contract:

- commit: `aae01e5ee29d5ec778af57b4db4d2e19e08e0ef1`;
- deposit release: `1.1.0`;
- ontology schema: `8.0`;
- supersedes: `1.0.1`;
- five layers: `Ontograph`, `Metagraph`, `ComputGraph`, `ValidGraph`, `SpecGraph`;
- core counts: `62` classes, `43` object properties, `68` datatype properties;
- alignment counts: `9` equivalent classes, `9` subclass axioms, `4` equivalent properties, `16` subproperty axioms;
- companion artefacts: `17` SHACL node shapes and `2` asserted disjointness triples;
- archival DOI: not assigned;
- namespace: `http://example.org/design-grammar#`, development placeholder.

R15.4 section K/L/M already defines the intended manuscript-side contract. The principal manuscript remains `Publications/T1_ITcon_DG_Draft_R15.4.docx`; the merged V8 DOCX is a comparison/working derivative.

### Knowledge-vault and graphify baseline

`DG_OBSIDIAN` already records the decisive conceptual change: three alignment modules rather than three ontology extension modules; BOT is subsumed through the topology alignment; IFC/bSDD is a classification/procedural boundary; Topologic is not to be represented as a claim about a formal external versioned OWL ontology unless the deposited evidence supports that claim.

`DG_OBSIDIAN/dissemination/consistency-map.md` still describes older publication anchors such as V4/V7 and marks v8.2 reasoner/SHACL and DG ID as not yet covered by publications. That is evidence of documentation drift that the proposed work must address, but it also shows why this work is a dissemination/dependency synchronization problem rather than a single v9/v10 feature.

The current root `graphify-out/GRAPH_REPORT.md` is dated 2026-09-13 and reports extraction from commit `5fc6c09a`, matching the current HEAD. It reports `15,501` nodes, `23,562` edges, and `1,166` communities, with `93%` extracted and `7%` inferred edges. However, graphify is commit-based and does not by itself prove that the extensive uncommitted working-tree changes are represented. A future graphify refresh must therefore occur after the selected contract changes, with the report and source commit recorded together.

## Relationship to v9.0 unfinished work

### Phase 40 — E2E Validation and Docs

**Relationship:** direct dependency and likely first gate, but not the right owner for the full V8 migration.

Phase 40 already owns documentation, graphify refresh, provider switching, and the final v9.0 E2E chain. The V8 contract affects its claims and documentation, especially:

- the ontology version and filenames embedded in context assembly;
- distinction between static ontology/TBox content and runtime graph/ABox data;
- SHACL as a companion structural/data-integrity graph;
- limits of HermiT evidence;
- deterministic execution wording;
- interoperability wording;
- manifest and repository availability status.

**Recommendation:** add a **contract preflight gate** to Phase 40 closeout, not the complete V8 synchronization. Phase 40 should not be declared publication-ready while its docs and graphify output still describe a materially older contract. The full multi-service migration should be scheduled separately if it exceeds documentation and verification changes.

### Phase 35 — Recognition and on-canvas proposal preview

**Relationship:** high semantic dependency, limited direct implementation dependency.

Phase 35 uses the Computgraph concept catalog, proposal schemas, provenance, and deterministic Tier 0 logic. V8 changes can affect names, layer terminology, provenance interpretation, and claims about deterministic re-execution. They must not silently change the frozen evaluation corpus, model-quality thresholds, or the trust boundary.

**Potentially obsolete or misleading items:**

- any claim that the full LLM recognition pipeline is deterministic;
- any claim that a successful proposal or zero structural findings establishes regulatory compliance;
- any terminology that treats an alignment module as a runtime ontology extension.

**Disposition:** preserve the implemented Phase 35 behavior; add V8 compatibility assertions and update evidence language. Do not reopen the quality-remediation architecture unless a concrete schema incompatibility is found.

### Phase 37 — Script Structure Validation MVP

**Relationship:** direct semantic dependency.

Phase 37 has deterministic Cypher checks, rule-mapped checks, and `/computgraph/consult`. The V8 contract reinforces the distinction between deterministic structural checking and LLM-assisted consultation. It also requires explicit incomplete/unsupported outcomes rather than treating absent evidence as pass.

**Disposition:** keep Phase 37 as the MVP foundation, but treat its status taxonomy and documentation as a likely early implementation target for the V8 contract. The existing roadmap/STATE drift for Phase 37 should be corrected separately from runtime changes.

### Phase 38 — AI-generated Grasshopper inputs

**Relationship:** direct semantic dependency.

Phase 38 already distinguishes determinable from geometry-required rules and uses server-side revalidation. V8 adds a stronger publication boundary:

- generated candidates are not evidence that the complete LLM pipeline is deterministic;
- `VALID`, `INVALID`, `INCOMPLETE`, `UNSUPPORTED`, and `SKIPPED_WITH_REASON` are needed for malformed or insufficient input conditions;
- a candidate satisfying a frozen formal rule is not equivalent to regulatory compliance;
- provenance must distinguish formal-artifact execution from model generation.

**Disposition:** retain Phase 38 functionality; integrate status/evidence refinements through a shared contract layer rather than rewriting the generation design.

### Phase 39 — DesignState auto-validation investigation

**Relationship:** direct risk and evidence dependency.

Phase 39 already found that auto-runs are SHACL-validated before their own `ValidStatus` is written, producing uniformly all-false verdicts. This finding is important for V8 because it demonstrates why `FAIL` cannot be the default interpretation of missing or incomplete evidence.

**Disposition:** keep Phase 39 as an investigation/prototype, not a production compliance claim. The V8 work should formalize fail-closed statuses and preserve the open design question. It should not silently convert the prototype into a regulatory or universal validation guarantee.

### Phases 29–31

- Phase 29's context assembler and Cypher validator are directly affected by V8 filenames, layer names, and schema boundaries.
- Phase 30's orchestration decision is largely orthogonal; V8 should not decide n8n vs OpenClaw.
- Phase 31 is not implemented and is potentially affected by the need to distinguish LLM generation, formal validation, and runtime graph projection.

**Disposition:** do not revive Phase 30/31 merely to perform V8 alignment. Add V8 contract fixtures to any future Phase 31 implementation and keep orchestration choice independent.

## Relationship to v9.1

v9.1 is a surface/integration milestone that fronts existing v9.0 services through one DG CHAT node and `/dg-` commands. Its design explicitly reuses:

- the v9.0 listener and bridge;
- the v9.0 serialization path;
- the existing recognition and preview pipeline;
- the existing publish endpoint;
- the existing confirmation trust model.

This makes V8 a **pre-activation compatibility gate** for v9.1, not a v9.1 phase.

### Specific v9.1 impacts

- **910–911:** listener lifecycle and chat status should expose `NOT_CHECKED`, `DATA_INCOMPLETE`, provider-unavailable, and project-unresolved states without implying failed ontology validation.
- **912:** selection context must state truncation and scope explicitly; no claim of deterministic whole-pipeline behavior.
- **913:** risk classification and confirmation must distinguish read-only formal checks, previews, mutations, and publishing.
- **914–915:** tag/mark/recognize/publish commands must preserve the boundary between local representations, runtime identity bindings, and deposited OWL declarations.
- **916:** deprecation documentation must not claim that the legacy components and V8 publication artifacts are the same compatibility surface.
- **917:** E2E must report publication-contract version and evidence status as part of the verification record.

### Potential contradiction

v9.1 says the trust model is inherited “verbatim” from v9.0. The V8 contract does not invalidate that trust model, but it narrows what successful preview, confirmation, publishing, and validation may be claimed to prove. v9.1 should therefore inherit the operational sequence while updating its evidence language.

**Recommendation:** do not alter v9.1 phase numbering or scope. Add a formal activation prerequisite: V8 contract preflight passes for the shared schemas, status taxonomy, filenames, and evidence boundaries.

## Relationship to v10.0

v10.0 is the first milestone that introduces new runtime semantics capable of materially expanding the publication claims:

- persisted node/wire substrate and topology queries;
- component knowledge base;
- bridge write commands;
- cluster introspection;
- script generation and editing;
- graph-native structure rules;
- multi-turn consulting.

The V8 contract is relevant to all of them, but it is not equivalent to any of them.

### Main integration points

- **Phase 41:** distinguish persisted Computgraph substrate/ABox from ontology declarations/TBox and from RDF/OWL projection.
- **Phase 42:** version the component KB independently from the ontology schema and include it in provenance; do not imply that KB coverage equals ontology alignment or exchange interoperability.
- **Phase 43:** fail-closed write refusal must use explicit unsupported/incomplete reasons; a valid command does not prove semantic correctness of the resulting model.
- **Phase 44:** cluster introspection requires an explicit boundary between local runtime structure and deposited ontology claims.
- **Phase 45:** generated blocks are proposals; component-KB validation and formal-rule validation must remain separate evidence channels.
- **Phase 46:** old/new graph diffs are runtime change evidence, not proof of OWL semantic equivalence.
- **Phase 47:** graph-native structure rules must define their relation to SHACL and the SWRL validator through an explicit rule partition; otherwise V8's evidence boundaries are violated.
- **Phase 48:** consulting must cite actual graph entities and validation statuses; LLM responses cannot be treated as deterministic execution evidence.
- **Phase 49:** E2E and docs must report the V8 contract version and all unresolved evidence blockers.

### Potentially obsolete v10.0 assumptions

The following assumptions should be reviewed before v10.0 activation:

1. “`cg-context-2`, additive” is safe only if the compatibility policy specifies how V8 schema/version metadata propagate through serializers and old consumers.
2. “Structure validation history” must not reuse `Run` conventions ambiguously if the publication contract distinguishes runtime validation records from formal ontology evidence.
3. “Ollama fallback across all v10.0 flows” does not imply identical model outputs or deterministic LLM behavior; only the formal, frozen execution leg can carry deterministic re-execution claims.
4. “Rule-aware” generation and consulting must report `INSUFFICIENT_DATA`, `UNSUPPORTED`, and `SKIPPED_WITH_REASON` rather than converting missing KB, topology, or ontology evidence into a guessed action.
5. “IFC-referenced” identity binding must not be expanded into full IFC exchange interoperability without a separate artifact and evidence program.

**Recommendation:** preserve v10.0 as a separate capability milestone, but revise its activation gate and phase contracts after the V8 baseline is accepted.

## Contradiction and obsolescence matrix

| Existing item | Tension with V8 | Assessment | Action |
|---|---|---|---|
| V9 references to `DesignGrammar-V7.owl` as current ontology | V8 manifest and R15.4 identify V8 as publication target | Obsolete for publication-facing claims; may remain historical/runtime compatibility reference | Mark historical or compatibility-scoped; do not global-replace blindly |
| Generic “extension module” language | R15.4 requires alignment-module distinctions | Contradictory where referring to V8 publication bundle | Replace with module-specific recording form |
| BOT described as IFC/bSDD classification module | Explicitly rejected by V8 contract | Obsolete/contradictory | Correct in docs, prompts, tests, and article alignment checks |
| Topologic described as a formal external OWL ontology | Unsupported by deposited evidence as currently scoped | Contradictory | Describe local documented-vocabulary representation unless evidence is expanded |
| Zero SHACL violations interpreted as compliance | V8 explicitly narrows SHACL evidence | Unsafe claim | Limit to structural/data-integrity conformance |
| HermiT described as executing the complete DG rule corpus | V8 limits HermiT to selected TBox/overlay | Contradictory | Separate OWL consistency, SWRL subset, and DG validator evidence |
| Deterministic LLM pipeline claim | V8 limits determinism to frozen formal artifact/configuration | Overbroad | Narrow claims and add tests for frozen execution scope |
| IFC class correspondence described as full interoperability | V8 excludes complete exchange interoperability | Overbroad | Limit to semantic alignment/identity binding; list future work |
| Runtime ABox counts conflated with OWL declaration counts | Manifest counts are static declaration IRIs | Contradictory | Add scope-bearing count checks |
| v9.1 “inherits v9.0 trust model verbatim” | Operationally valid, evidentially incomplete | Needs qualification | Preserve propose/preview/confirm/apply, update evidence semantics |
| v10.0 graph-native rule grammar alongside SHACL/SWRL | Risk of overlapping rule ownership | Unresolved design boundary | Require explicit partition and status contract before Phase 47 |
| Phase 40 progress table says some completed phases are in progress | GSD bookkeeping drift | Administrative contradiction | Correct during a dedicated planning/documentation pass, preserving history |
| `DG_OBSIDIAN/dissemination/consistency-map.md` still centers V4/V7 | V8/R15.4 now changes publication anchors | Documentation drift | Update after contract decision and verify graphify propagation |
| Current graphify report matches HEAD but not necessarily dirty tree | Graph report cannot prove uncommitted changes are included | Verification limitation | Refresh only after selected changes; record source commit and scope |

## Recommended milestone placement

### Option A — integrate into Phase 40

**Advantages:** Phase 40 already owns docs, graphify, and v9.0 closeout.  
**Disadvantages:** too broad for Phase 40; would combine E2E runtime verification, documentation closeout, manuscript alignment, ontology migration, and status-taxonomy changes. It would make the already-stale v9.0 state harder to interpret and could delay closeout indefinitely.

**Verdict:** accept only a narrow V8 preflight and documentation gate, not the complete implementation.

### Option B — integrate into v9.1

**Advantages:** v9.1 consumes the affected Computgraph/bridge/publish surfaces.  
**Disadvantages:** v9.1's purpose is a unified chatbot surface; V8 is broader and includes publication repository, manuscript, OWL modules, SHACL, LPG mapping, and claim evidence. It would burden a UI milestone with unrelated ontology governance.

**Verdict:** reject as the primary home; retain only a v9.1 activation dependency.

### Option C — integrate into v10.0

**Advantages:** v10.0 is the next major semantic/runtime expansion and can consume the stabilized contract.  
**Disadvantages:** v10.0 already has a large, coherent feature program; combining contract migration with write/generation/editing makes failure attribution and scope control poor.

**Verdict:** use V8 as a prerequisite gate and update v10.0 plans, not as a v10.0 phase.

### Option D — separate milestone immediately after v10.0

**Advantages:** clean ownership, full repository-wide scope, clear publication baseline, independent verification report, no contamination of v9.0/v9.1/v10.0 feature plans.  
**Disadvantages:** downstream work could proceed against an unstable contract unless a preflight gate is defined now.

**Verdict:** **recommended**. Establish the separate milestone after v10.0 in the roadmap, while defining a small mandatory contract preflight before v9.1 and v10.0 activation.

### Option E — separate milestone before v9.1

**Advantages:** stabilizes the contract before any future consumer expands it.  
**Disadvantages:** delays v9.1 and v10.0; publication alignment is urgent because R15.4 already defines the new target.

**Verdict:** technically safest if the goal is one canonical source before further development. If schedule pressure matters, use the hybrid recommendation below.

## Recommended hybrid integration strategy

1. **Now, without activating a new GSD phase:** approve the architecture decision that V8 is a cross-milestone contract baseline and not a v9.0/v9.1/v10.0 feature phase.
2. **Phase 40 closeout:** add only a contract preflight checklist covering filenames, version markers, evidence wording, count scopes, and graphify freshness. Do not migrate the entire repository under Phase 40 unless the implementation is demonstrably documentation-only.
3. **Before v9.1 activation:** require a lightweight compatibility gate for shared v9.0 APIs, serializers, status values, provenance, and publication-facing terminology.
4. **Before v10.0 activation:** require a stronger gate for LPG/OWL projection, SHACL/SWRL partition, deterministic execution scope, identity bindings, and fail-closed outcomes.
5. **After v10.0:** execute the full independent V8 Publication Contract Alignment milestone, including repository bundle transfer, all dependent reference synchronization, consistency checks, article-plan integration, and final verification report.
6. **Only after the full milestone:** consider promoting a new publication contract version or changing the namespace/DOI status. Until then, keep the manifest values literal and do not infer an archival DOI or permanent namespace.

## Proposed work packages for the future milestone

These are integration work packages, not GSD phase files.

### WP1 — Baseline and safe-change boundary

- Capture HEAD, branch, dirty-path inventory, publication repository commit, and selected source hashes.
- Classify files as protected parallel work, generated output, runtime source, publication source, or eligible contract surface.
- Define an allowlist; prohibit broad V7→V8 replacement.

### WP2 — Contract inventory and machine checks

- Import the V8 manifest and selected ontology bundle.
- Build checks for counts, layer names, module filenames, catalogue entries, SHACL shapes, disjointness, namespace, and DOI status.
- Add a contract version record for generated/runtime payloads where appropriate.

### WP3 — Runtime boundary synchronization

- Audit `ontology/`, `spec/`, `data-service/`, `DG/`, Cypher, serializers, API contracts, n8n prompts, SHACL, tests, and fixtures.
- Separate TBox, ABox, LPG, RDF projection, SHACL graph, SWRL subset, and validator semantics.
- Add fail-closed status values and malformed/incomplete-rule outcomes without changing existing successful-path semantics unnecessarily.

### WP4 — v9/v10 compatibility contracts

- Add compatibility tests for v9.0 consumers and the planned v9.1/v10.0 extension points.
- Verify that `cgContextJson`, provenance, `dgId`, publish, consult, validation, and proposed write/generation contracts remain additive or explicitly versioned.
- Add the Phase 47 rule-partition prerequisite before graph-native structure rules are implemented.

### WP5 — Publication and manuscript alignment

- Preserve all existing K/L/M revision-plan items and add only necessary clarifications.
- Check R15.4 claims against the V8 manifest and exact deposited files.
- Keep the principal DOCX distinct from merged derivatives.
- Produce a claim-to-artifact matrix with explicit evidence boundaries.

### WP6 — Obsidian, dissemination, and graphify propagation

- Update the consistency map and relevant T1/dissemination notes after the contract is accepted.
- Add decision/debugging notes only for actual decisions/findings.
- Refresh graphify after selected changes; record graph source commit, extraction scope, and report path.

### WP7 — Verification and blockers

- Run machine checks, Python tests, C# tests/builds, serializer/API contract tests, and applicable document integrity checks.
- Run live checks only where credentials/environment and user authorization exist.
- Report unresolved human/live blockers explicitly; never convert them into passing evidence.

## Decision gates

The following decisions should be made before creating new GSD artifacts:

1. **Milestone placement:** approve the hybrid strategy: preflight gate before v9.1/v10.0, full standalone milestone after v10.0.
2. **Numbering:** do not reserve Phase 51 yet. First update/establish the roadmap's formal post-v10 numbering policy and decide whether the future BOT bridge occupies the next number.
3. **Phase 40 boundary:** decide whether its docs/graphify closeout may include a narrow V8 preflight.
4. **Runtime compatibility:** confirm that V7 references may remain where they are explicitly historical or runtime-compatibility scoped.
5. **Status taxonomy ownership:** decide whether common fail-closed statuses belong in a shared contract module/spec before future v9.1/v10.0 work.
6. **Article dependency:** decide whether manuscript alignment is a milestone acceptance criterion or a parallel dissemination deliverable tied to the same repository commit.
7. **Dirty-tree policy:** approve an allowlist-based implementation protocol for the shared working tree.

## Final recommendation

Do **not** create or execute Phase 51 yet. Do **not** insert the full V8 work into v9.0, v9.1, or v10.0. Record the V8 contract as a cross-milestone prerequisite and plan a dedicated publication/contract-alignment milestone after v10.0, with narrowly scoped compatibility gates required before v9.1 and v10.0 activation.

This keeps the feature milestones coherent, prevents R15.4 evidence boundaries from being diluted, preserves the existing v9/v10 architecture, and provides a single accountable place for repository, ontology, runtime, Obsidian, graphify, and manuscript synchronization.
