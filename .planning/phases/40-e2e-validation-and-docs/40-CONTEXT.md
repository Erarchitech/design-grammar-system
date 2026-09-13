# Phase 40: E2E Validation and Docs - Context

**Gathered:** 2026-07-28
**Status:** Ready for planning

<domain>
## Phase Boundary

Phase 40 proves the v9.0 intelligence chain runs **live, end to end, in one session on real Docker
under a cloud provider**, and writes down everything v9.0 added. Two chains, one provider drill,
one docs sweep, one traceability close-out.

**In scope:**

- E2E chain 1 (browser + Docker): NL rule → cloud-LLM ingest (context layer + Cypher validation) →
  graph → GH validation → Speckle publish
- E2E chain 2 (Rhino + Docker): object marked + entities tagged → LLM recognition → on-canvas
  preview → confirm → Computgraph publish → structure validation → generated inputs accepted →
  applied via PARAMETER REINSTATE → validation run
- Provider-switch drill: Claude ↔ OpenAI-compatible ↔ Ollama through the settings panel only,
  mid-session, no container restarts
- Docs: CLAUDE.md, `spec/`, `DG_OBSIDIAN/`, a v9.0 component reference, graphify refresh
- Requirement traceability close-out for the whole v9.0 milestone

**V8 publication-contract preflight gate:** Phase 40 performs a narrow closeout preflight for the future v11.0 contract. It checks V8 version and filenames, five-layer terminology, scope-bearing count language, TBox/ABox/LPG/RDF/SHACL/HermiT/determinism evidence boundaries, literal namespace/DOI status, and graphify source-commit scope. It does not import the full v11.0 bundle, perform the repository-wide migration, or create active v11.0 phase directories. E2E success is evidence within declared evaluator scopes; provider switching does not prove model-output equivalence; missing or unavailable evidence is recorded as a non-verdict disposition.

**Out of scope** (locked during discussion):

- Executing Phases 30 or 31 — they are deferred with a written record, not built here
- Resolving UAT decisions D1 (partial-publish semantics), D2 (re-tag duplicate), D3
  (PreviewRegistry undo-awareness) — design changes, routed to backlog
- Fixing F-39-01 (auto-validation's constant-false verdicts) — Phase 39 scoped it to a follow-up
  milestone as item #1
- Rebuilding the Frame `.gh` fixture — architect decision 2026-07-26 stands; Corpus A is frozen

</domain>

<decisions>
## Implementation Decisions

### E2E execution vehicle

- **D-01:** Phase 40 **runs the existing runbook** rather than authoring a new one.
  `.planning/phases/v9.0-PIPELINE-UAT.md` (re-audited 2026-07-28) already sequences the two chains
  as Session A and Session B, with the traps, Cypher and dedup map worked out. Its own text says
  *"Session B is literally Phase 40's second E2E deliverable"* and *"this plan **is** its dry run"*.
  Plans wrap it; they do not restate it. A second copy would drift from the first.
- **D-02:** Results are recorded in **both** places. Each item's outcome goes into its owning
  `NN-UAT.md` (closing those phases' human items, as the runbook instructs), **and** Phase 40 writes
  its own `40-EVIDENCE.json` covering the two chain runs — timestamps, project string, provider,
  per-leg pass/fail, and explicit holes. Follows Phase 39's evidence-artifact precedent
  (39-03: unmeasured scenarios are recorded as holes; a fabricated datapoint corrupts the doc that
  cites it). Per-phase files alone would leave no single artifact proving "both chains, one session".
- **D-03:** The live session runs as a **blocking checkpoint inside a plan**
  (`checkpoint:human-verify`, gate=blocking) — the 33-04 precedent, where the architect ran all six
  checks personally and the executor did not self-approve. Phase 40's E2E **is** its deliverable, so
  deferring it to `/gsd-verify-work` would defer the phase itself. Rejected: the 33/34-02/34-03
  deferral pattern, which is right for a phase whose deliverable is code but wrong for one whose
  deliverable is the run.
- **D-04:** The SC1 pass criterion is **pre-registered before the run, not judged after it**.
  "Chain completes" = every leg produces its expected artifact and no *unexpected* error. Three
  already-measured findings are named up front as **expected observations, not chain failures**:
  F-39-01's constant-false auto verdicts, Phase 35 SC1's blocked frontier arms, and a possible G7
  `grammar_as_filter` block on live recognition (the runbook already calls that "a result, not a
  broken harness"). This closes the measure-quality-late failure mode that Phase 38-01 fixed by
  writing SC1 as literal thresholds.

### Milestone close-out with Phases 30 and 31 unbuilt

- **D-05:** v9.0 closes with a **formal deferral record**, not a descope and not a block. `ORCH-*`
  and `RING-*` requirements move to a named future milestone with the reason stated;
  `REQUIREMENTS.md` marks them **deferred** — not checked, not silently dropped. SC3 is restated as
  *"every v9.0 requirement is either checked off or carries a written deferral"*, which is the same
  honest-holes discipline the Phase 39 evidence artifacts already use. Rejected: blocking Phase 40
  behind two unstarted phases (an orchestration ADR plus a full ingest/edit rework), and cutting the
  requirements outright (loses the record that they were planned and why they were not built).
- **D-06:** The **traceability sweep is Phase 40's job**. SC3 demands "traceability complete", and a
  progress table contradicting the phase directories is precisely a traceability defect. In one pass
  Phase 40 reconciles: the `ROADMAP.md` progress table (Phase 37 still reads "Not started / 0 plans"
  though 6/6 plans executed with VERIFICATION, UAT and REVIEW files and live routes; 35 and 38 rows
  are also wrong), `REQUIREMENTS.md` checkboxes, and the deferral record — so the milestone's own
  records agree with each other.
- **D-07:** The deferral record lives in **two places, by role**. `REQUIREMENTS.md` gets a Deferred
  section listing each requirement, its owning unbuilt phase, and the target milestone — that is the
  file GSD tooling actually reads. Phase 40 also writes **`40-DEFERRALS.md`** holding the reasoning,
  which the milestone archive preserves alongside the phase.
- **D-08:** Of the runbook's five open decisions, Phase 40 **takes D4 and D5 and backlogs D1–D3**.
  D4 is literally an INTG-04 gap — Phase 39 added `trigger` / `verdictSource` / `capturedAt` /
  `completedAt` / `attempts` / `lastError` plus an `IntegrationConfig{provider:'AutoValidation'}`
  variant that `spec/DATABASE.md` documents nowhere. D5 is a one-line annotation on a stale figure in
  `39-03-SUMMARY.md:132`. D1–D3 are design changes (a publish-contract change, a tag-matching policy,
  a custom `IGH_UndoAction`) and belong in the v10.0 backlog alongside the deferral record.

### Provider-key dependency

- **D-09:** The provider-switch plan **opens with a blocking checkpoint** asking the architect to
  configure an Anthropic or genuine-OpenAI key in the ui-v2 AI Engine panel. Without it SC2 is
  unachievable by definition, and the same key also unblocks Phase 35 SC1, Phase 36 test 3
  provenance, and live recognition — one key unblocks four items, which is worth stopping for. The
  runbook already names this as *"the one prerequisite that gates almost everything"*.
- **D-10:** The S-A/3 frontier recognition sweep **runs in the same sitting but is credited to
  Phase 35**. The key is configured, the record-mode driver already exists, and the whole sweep costs
  roughly $0.08 — so running it is nearly free. Results are recorded to `35-UAT.md` and
  `35-EVAL-REPORT.md` and close **Phase 35's** SC1; Phase 40 does not claim them as its own success
  criteria and does not gate on the 0.60 ship gate.
- **D-11:** **Pre-registered no-key fallback:** if the key never materialises at the checkpoint, run
  the DeepSeek ↔ Ollama switch to prove the mechanism, record SC2 as **blocked-not-failed** with the
  missing-key reason in `40-EVIDENCE.json`, and let every other Phase 40 deliverable complete and
  commit. Same discipline Phase 35 SC1 already uses. Rejected: leaving Phase 40 open indefinitely
  behind an external dependency, and declaring the switch "mechanically proven" from unit tests —
  the live `n8n → gateway → provider API → Neo4j` path has never once run, which is the entire
  reason the drill exists.

### Docs surface and inventory

- **D-12:** The 5 new v9.0 Grasshopper components (DG CANVAS LISTENER, DG OBJECT MARKER, DG ENTITY
  TAG, DG STRUCTURE CONFIRM, DG COMPUTGRAPH PUBLISH) are documented in
  **`docs/RELEASE-NOTES-v9.0.md`**, following the established `docs/RELEASE-NOTES-v7.0.md` and
  `v8.0.md` per-component layout (name, ports, GUID, ASCII wiring diagram). v9.0 adds components
  rather than breaking them, but the layout carries and canvas authors already know where to look.
- **D-13:** INTG-04's missing **Phase 30 ADR is replaced by a deferral note** in
  `DG_OBSIDIAN/knowledge/decisions/` stating that the orchestration question (n8n vs OpenClaw) is
  unresolved and deferred, cross-linked to `40-DEFERRALS.md` and the existing research at
  `.planning/research/`. The requirement closes honestly — a reader learns the decision was not made
  rather than finding a dangling reference. Rejected: writing the ADR now from existing research,
  which decides Phase 30's entire deliverable inside a docs phase without the evaluation it was
  meant to rest on.
- **D-14:** CLAUDE.md and `spec/` get **targeted patches against a written inventory**, not a
  rewrite. Phase 40 first enumerates every doc surface v9.0 touched (LLM gateway, settings panel,
  canvas bridge, annotation convention, Computgraph labels/relations, the 5 components, D4's
  ValidationRun properties), then patches each in place. CLAUDE.md already carries most of this
  correctly; a full regeneration would churn correct text and risk regressing the hard-won gotchas
  and schema tables.
- **D-15:** SC4 is treated as **the executable check it is written as**: run
  `grep -ri "ollama" CLAUDE.md spec/`, read every hit, correct any line implying Ollama is the sole
  LLM path, and paste the final output into `40-EVIDENCE.json`. A grep gate that is never actually
  run is not a gate.

### Claude's Discretion

- **The DG Canvas Annotation Convention vault note** is a roadmap deliverable and does not exist yet
  (only `DG_OBSIDIAN/sessions/2026-07-18 phase-32-execution.md` mentions the convention). Its shape,
  depth, and placement within `DG_OBSIDIAN/knowledge/` are Claude's call — the grammar itself is
  already single-sourced in `DG/src/DG.Core/Parsing/CanvasAnnotationParser.cs` and the Phase 34-01
  consistency test, so the note documents rather than redefines it.
- **graphify refresh ordering** — `graphify update .` runs after the docs edits land so the graph
  reflects final text; whether it is its own plan task or folded into the docs plan is Claude's call.
- **Plan/wave decomposition** across the four work streams (E2E chains, provider drill, docs,
  traceability) is unconstrained beyond the checkpoint placement fixed in D-03 and D-09.

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### The E2E procedure itself (read first)

- `.planning/phases/v9.0-PIPELINE-UAT.md` — **the runbook Phase 40 executes.** Step 0 prerequisites
  (route-surface probe, `.gha` provenance check, test-suite gates), Session A (S-A/1–5), Session B
  (S-B/1–9), the dedup map of what must *not* be re-tested, the already-closed robustness table, the
  five open decisions D1–D5, and the deferred list. Per D-01 this is the procedure, not a reference.

### Phase scope and requirements

- `.planning/ROADMAP.md` §"Phase 40: E2E Validation and Docs" — goal, 4 deliverables, SC1–SC4, and
  the progress table D-06 reconciles
- `.planning/REQUIREMENTS.md` — INTG-01…INTG-04 (lines 110–113) and the traceability table (line 171)
- `.planning/STATE.md` — Deferred Verification table, Blockers/Concerns, and the Phase 37 ROADMAP
  drift note D-06 acts on

### Prior-phase decisions this phase depends on

- `.planning/phases/39-designstate-auto-validation-investigation/39-CONTEXT.md` — D-16 (ADR already
  filed to the vault), D-07 (`trigger`/`verdictSource` stamping, the properties D4 must document),
  D-09/D-12 (auto-runs persist-only, visible in the normal run list)
- `DG_OBSIDIAN/knowledge/decisions/Phase 39 DesignState auto-validation — data-service watcher, SHACL verdict, guardrails.md`
  — the filed ADR; **verified present**, so INTG-04's Phase 39 half is already satisfied
- `.planning/phases/38-ai-generated-grasshopper-script-inputs/38-CONTEXT.md` — D-01/D-02
  (`reinstateParameterId` derivation, exercised by S-B/6), D-04 (excluded-with-reason, never guessed)
- `.planning/research/REASONER-VALUE-AND-AUTOREPAIR.md` — the orchestration/reasoner analysis the
  D-13 deferral note cross-links

### Docs targets

- `docs/RELEASE-NOTES-v7.0.md` and `docs/RELEASE-NOTES-v8.0.md` — the per-component layout D-12 follows
- `CLAUDE.md` — service map, Graph Schema v4 tables, Known Gotchas, and the Schema Change Propagation
  checklist naming every file a structural change must touch
- `spec/DATABASE.md` — needs the Computgraph section plus D4's undocumented `:ValidationRun`
  properties (`spec/DATABASE.md:108` documents none of them)
- `spec/DG-ID.md` — scopes `dgId` to the five entity labels; the runbook's S-B/5 expectations rest on
  this ("Behavior and Algorithm carry no `source` and no `dgId` — correct by design")
- `spec/API.md` — `/computgraph/*` route contracts written in Phases 36–38
- `spec/RULE-PARTITION-POLICY.md` — governs the SWRL-vs-SHACL ownership line the F-39-01 note touches
- `DG_OBSIDIAN/00-home/index.md` and `DG_OBSIDIAN/00-home/Current priorities.md` — vault entry points
  per the CLAUDE.md session protocol

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets

- **`ui-v2/src/screens/AiEngineScreen.jsx` + `ui-v2/src/lib/llmApi.js` — the LLM settings panel
  already exists in ui-v2.** Provider select, model discovery (`GET /llm/models`), API key,
  **Base URL** (line 306, required for the OpenAI-compatible leg of the SC2 drill), save, and test
  connection are all shipped — built in v8.1 Phase 811, *after* the roadmap wrote "port from legacy
  panel if not done earlier". **That deliverable is done; only live verification remains.** Planners
  must not schedule a port.
- **`ui-v2/src/screens/apidocs/content/` (Phase 815)** — auto-registering `##-` content modules; not
  used for D-12 (that goes to release notes) but available if an in-app surface is ever wanted.
- **`.planning/phases/39-designstate-auto-validation-investigation/39-EVIDENCE.json`** — the shape
  `40-EVIDENCE.json` follows per D-02, including its `missing_measurements` holes convention.
- **`data-service/tests/test_recognition_eval.py`** record-mode driver — the D-10 sweep needs no new
  code; the arm/corpus harness and `REAL_ADAPTER_MAP` already exist from Phase 35-15.

### Established Patterns

- **Blocking human checkpoint over self-approval** — 33-04 (architect ran all six checks personally),
  34-02/34-03 (live UAT explicitly deferred rather than self-approved). D-03 adopts the 33-04 form.
- **Honest holes over fabricated datapoints** — 39-03 writes nothing rather than inventing a number;
  35-15 reports SC1 as *blocked on provider availability*, not computed from an incomplete arm set.
  D-04 and D-11 both inherit this.
- **Pre-registered numeric criteria** — 38-01 fixed SC1 as five literal thresholds specifically to
  close the measure-quality-late failure mode Phase 35 hit. D-04 applies the same discipline to a
  procedural criterion.
- **Schema Change Propagation checklist** (CLAUDE.md) — names every file a structural change must
  touch; D-14's inventory is built from it.

### Integration Points

- **Container freshness is a real, recurring failure mode.** F7 proved `/computgraph/publish` shipped
  code-complete but was never deployed — the first publish attempt 404'd. Step 0.2/0.3's rebuild +
  10-route `openapi.json` probe is non-negotiable before any E2E leg runs.
- **`.gha` provenance** — build, copy to `%APPDATA%\Grasshopper\Libraries\DG\`, *then* start Rhino
  (Rhino locks the file). Compare SHA256 and check Rhino's start time is later than the `.gha`
  timestamp; this exact check is what made the F4 retest trustworthy.
- **Two false-pass traps in Session B** — `PreviewRegistry` is in-process (a Rhino restart orphans
  any preview left on canvas), and DG STRUCTURE CONFIRM's `Pending`/`Status` outputs do not refresh
  on undo. Both are written up in the runbook; plans must carry them into the checkpoint text.
- **Rising-edge triggers** — DG COMPUTGRAPH PUBLISH, DG ENTITY TAG and PARAMETER REINSTATE all need
  the toggle dropped to False before each fire, or nothing happens.

</code_context>

<specifics>
## Specific Ideas

- **One project string for the whole run**, recorded up front (the runbook suggests `v9-final-uat`).
  Do **not** reuse `urbanblock-uat` — it holds the 2026-07-26 subgraph that remains evidence.
- **Fixture substitution is expected and must be stated, not hidden.** Every closed Group 2/3/4 test
  ran on **UrbanBlock_V7**, not the intended Frame definition. Session B runs on UrbanBlock_V7 for
  continuity; any "Frame" wording in a per-phase UAT file reads as "a canvas of this shape", and the
  substitution is noted in the `result:` line exactly as 35-UAT and 36-UAT did.
- **Write `result:` lines with single-line `expected:`.** `query audit-uat` silently drops UAT items
  written with `expected: |` block scalars — it reported 10 items across 5 files where the files
  actually held 24 across 9. Any UAT edit Phase 40 makes should use the CLI-visible form.
- **Scope live recognition with `procedure_index`.** A cold whole-canvas run on UrbanBlock (221
  untagged of 233) blows the adapter's 4096 `max_tokens`; guardrails G8/G9 now catch it honestly, but
  the run still fails to produce usable proposals.

</specifics>

<deferred>
## Deferred Ideas

- **D1 — F5(c) per-entity vs. all-or-nothing publish rejection** (Phases 35/36). Partial-write
  semantics change the `/computgraph/publish` response contract and interact with MERGE idempotency
  and stale-entity reporting. Off the critical path — the wholesale 422 is unreachable from the
  canvas because the publish component pre-flights null dataTypes. → v10.0 backlog.
- **D2 — partial-reselection re-tag creates a stray nested duplicate** (Phase 34).
  `EntityTagComponent.cs:246-263` requires an exact core-member set match. Needs a policy call:
  warn on partial match, or tolerate subset/superset with confirmation. → v10.0 backlog.
- **D3 — `PreviewRegistry` is not undo-aware** (Phase 35). A real fix needs a custom `IGH_UndoAction`
  — a design change, not a patch. → v10.0 backlog.
- **F-39-01 — auto-validation verdicts are a constant, not a judgement.** Auto-runs are
  SHACL-validated before their own `ValidStatus` is written, so every auto-run self-violates
  `RunStatusShape_valid` and the conservative unmapped fallback flips every ObjState false. Phase 39
  measured this deliberately and scoped the fix to follow-up milestone item #1. Phase 40 observes it,
  does not fix it (D-04).
- **Phases 30 and 31** — orchestration evaluation and the rules ingestion/editing upgrade. Deferred
  with `ORCH-*` / `RING-*` per D-05 and D-07.
- **Tier-0 rule coverage** — `cg_topology.classify()` abstains on every scoped candidate in both
  corpora, extending 35-14's R4 defect (`name.startswith('Param')` is unreachable on real GH data).
  Warrants its own plan; not a Phase 40 concern.
- **`migrations/2026-07-07_validationgraph_to_validgraph.cypher`** — still awaiting approval; v2.0-era
  runs (project `TestA`, 20 runs / 1148 entities) stay invisible to data-service. Not v9.0 scope,
  but it is the oldest standing item and Phase 40's close-out is a natural moment to raise it.

</deferred>

---

*Phase: 40-e2e-validation-and-docs*
*Context gathered: 2026-07-28*
