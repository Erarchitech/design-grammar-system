# Phase 40: E2E Validation and Docs - Research

**Researched:** 2026-07-28
**Domain:** Milestone close-out — E2E verification of an already-built AI pipeline, documentation reconciliation, requirement traceability audit. NOT a build phase; no new libraries.
**Confidence:** HIGH for doc-gap/traceability facts (directly verified against files on disk with line numbers); MEDIUM for anything that depends on live Docker/Rhino state (not probed this session — this machine's Docker/Rhino state was not queried; treat as of-writing-time facts about the repo only).

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

**E2E execution vehicle**
- **D-01:** Phase 40 runs the existing runbook rather than authoring a new one. `.planning/milestones/v9.0-phases/v9.0-PIPELINE-UAT.md` (re-audited 2026-07-28) already sequences the two chains as Session A and Session B. Plans wrap it; they do not restate it.
- **D-02:** Results are recorded in both places — each item's outcome goes into its owning `NN-UAT.md`, and Phase 40 writes its own `40-EVIDENCE.json` covering the two chain runs (timestamps, project string, provider, per-leg pass/fail, explicit holes). Follows Phase 39's evidence-artifact precedent.
- **D-03:** The live session runs as a blocking checkpoint inside a plan (`checkpoint:human-verify`, gate=blocking) — the 33-04 precedent. The executor does not self-approve.
- **D-04:** The SC1 pass criterion is pre-registered before the run, not judged after it. "Chain completes" = every leg produces its expected artifact and no *unexpected* error. Three already-measured findings are named up front as expected observations, not chain failures: F-39-01's constant-false auto verdicts, Phase 35 SC1's blocked frontier arms, and a possible G7 `grammar_as_filter` block on live recognition.

**Milestone close-out with Phases 30 and 31 unbuilt**
- **D-05:** v9.0 closes with a formal deferral record, not a descope and not a block. `ORCH-*` and `RING-*` requirements move to a named future milestone with the reason stated; `REQUIREMENTS.md` marks them deferred — not checked, not silently dropped. SC3 is restated as "every v9.0 requirement is either checked off or carries a written deferral."
- **D-06:** The traceability sweep is Phase 40's job. In one pass Phase 40 reconciles: the `ROADMAP.md` progress table, `REQUIREMENTS.md` checkboxes, and the deferral record.
- **D-07:** The deferral record lives in two places, by role. `REQUIREMENTS.md` gets a Deferred section (the file GSD tooling reads). Phase 40 also writes `40-DEFERRALS.md` holding the reasoning.
- **D-08:** Of the runbook's five open decisions, Phase 40 takes D4 and D5 and backlogs D1–D3. D4 is an INTG-04 gap — Phase 39 added `trigger`/`verdictSource`/`capturedAt`/`completedAt`/`attempts`/`lastError` plus an `IntegrationConfig{provider:'AutoValidation'}` variant that `spec/DATABASE.md` documents nowhere. D5 is a one-line annotation on a stale figure in `39-03-SUMMARY.md:132`.

**Provider-key dependency**
- **D-09:** The provider-switch plan opens with a blocking checkpoint asking the architect to configure an Anthropic or genuine-OpenAI key. One key unblocks Phase 40 SC2, Phase 35 SC1, Phase 36 test 3 provenance, and live recognition.
- **D-10:** The S-A/3 frontier recognition sweep runs in the same sitting but is credited to Phase 35 (results recorded to `35-UAT.md`/`35-EVAL-REPORT.md`, not claimed as Phase 40's own).
- **D-11:** Pre-registered no-key fallback: if the key never materialises, run the DeepSeek ↔ Ollama switch to prove the mechanism, record SC2 as blocked-not-failed with the missing-key reason in `40-EVIDENCE.json`, and let every other deliverable complete and commit.

**Docs surface and inventory**
- **D-12:** The 5 new v9.0 Grasshopper components (DG CANVAS LISTENER, DG OBJECT MARKER, DG ENTITY TAG, DG STRUCTURE CONFIRM, DG COMPUTGRAPH PUBLISH) are documented in `docs/RELEASE-NOTES-v9.0.md`, following the established `v7.0`/`v8.0` per-component layout (name, ports, GUID, ASCII wiring diagram).
- **D-13:** INTG-04's missing Phase 30 ADR is replaced by a deferral note in `DG_OBSIDIAN/knowledge/decisions/` stating the orchestration question (n8n vs OpenClaw) is unresolved and deferred, cross-linked to `40-DEFERRALS.md` and `.planning/research/`.
- **D-14:** CLAUDE.md and `spec/` get targeted patches against a written inventory, not a rewrite. Phase 40 first enumerates every doc surface v9.0 touched (LLM gateway, settings panel, canvas bridge, annotation convention, Computgraph labels/relations, the 5 components, D4's ValidationRun properties), then patches each in place.
- **D-15:** SC4 is treated as the executable check it is written as: run `grep -ri "ollama" CLAUDE.md spec/`, read every hit, correct any line implying Ollama is the sole LLM path, and paste the final output into `40-EVIDENCE.json`.

### Claude's Discretion

- The DG Canvas Annotation Convention vault note is a roadmap deliverable and does not exist yet (only `DG_OBSIDIAN/sessions/2026-07-18 phase-32-execution.md` mentions the convention). Its shape, depth, and placement within `DG_OBSIDIAN/knowledge/` are Claude's call.
- `graphify update .` ordering — runs after the docs edits land; whether it is its own plan task or folded into the docs plan is Claude's call.
- Plan/wave decomposition across the four work streams (E2E chains, provider drill, docs, traceability) is unconstrained beyond the checkpoint placement fixed in D-03 and D-09.

### Deferred Ideas (OUT OF SCOPE)

- **D1 — F5(c)** per-entity vs. all-or-nothing publish rejection (Phases 35/36) → v10.0 backlog.
- **D2 — partial-reselection re-tag** creates a stray nested duplicate (Phase 34), `EntityTagComponent.cs:246-263` → v10.0 backlog.
- **D3 — `PreviewRegistry` is not undo-aware** (Phase 35), needs a custom `IGH_UndoAction` → v10.0 backlog.
- **F-39-01** — auto-validation verdicts are a constant, not a judgement. Phase 40 observes it, does not fix it.
- **Phases 30 and 31** — orchestration evaluation and rules ingestion/editing upgrade. Deferred per D-05/D-07.
- **Tier-0 rule coverage** — `cg_topology.classify()` abstains on every scoped candidate in both corpora. Not a Phase 40 concern.
- **`migrations/2026-07-07_validationgraph_to_validgraph.cypher`** — still awaiting approval. Not v9.0 scope but flagged as the oldest standing item.
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| INTG-01 | E2E on live Docker with a cloud provider: NL rule → context-assembled ingest → validated Cypher → graph → Grasshopper validation → Speckle publish | Runbook Session A (S-A/1, S-A/2, S-A/5) + Step 0 readiness checklist below. This is Session A's chain — already fully sequenced in `v9.0-PIPELINE-UAT.md`; Phase 40 supplies the checkpoint wrapper and `40-EVIDENCE.json`, not new procedure. |
| INTG-02 | Provider switching (Claude ↔ OpenAI-compatible ↔ Ollama) requires only the settings panel — no restarts, no workflow edits | Runbook S-A/2 (three-way drill in one pass). Settings panel already shipped (`ui-v2/src/screens/AiEngineScreen.jsx` + `ui-v2/src/lib/llmApi.js`, verified present, confirmed below) — no port task needed. |
| INTG-03 | E2E GH intelligence chain: object marked + entities tagged → LLM recognition → on-canvas preview → confirmed → published to Computgraph → structure-validated → accepted generated inputs applied via PARAMETER REINSTATE → validation run recorded | Runbook Session B (S-B/1 through S-B/9), which the runbook itself calls "literally Phase 40's second E2E deliverable." Component facts (GUIDs, ports) verified below in the Doc-Surface / GH Components sections. |
| INTG-04 | CLAUDE.md, spec/, and DG_OBSIDIAN document the gateway, settings, bridge, annotation convention, Computgraph layer, new GH components, and the Phase 30/39 ADRs; graphify refreshed | Doc-surface inventory table below is the concrete gap list this requirement needs closed. Phase 39 ADR confirmed already filed (verified below); Phase 30 ADR replaced by a deferral note per D-13 (not yet written — confirmed absent below). |
</phase_requirements>

## Summary

Phase 40 is a verification-and-documentation close-out, not a build phase. Its two most valuable
research products are (1) a concrete, line-numbered inventory of exactly which doc files say the
wrong (or nothing) about v9.0 facts, and (2) a corrected traceability table proving the ROADMAP
progress table, the REQUIREMENTS.md checkbox set, and the REQUIREMENTS.md Traceability summary
table currently **disagree with each other inside the same file** — not just against reality.

The single biggest surprise: `.planning/REQUIREMENTS.md` itself is internally inconsistent. Its
per-requirement checkboxes (lines 22–107) show **47 of 60 requirements already checked `[x]`**
(everything except ORCH-01..04, RING-01..05, and INTG-01..04), but its own "Traceability" table
(lines 156–171) and "Coverage" summary (line 175: "6 complete, 54 pending") still read as if only
Phase 28/32/37/39 are done. Whoever checks the per-requirement boxes as phases land never updates
the summary table beneath them. Phase 40's D-06 traceability sweep must reconcile both, in the same
file, not just against `ROADMAP.md`.

Second: the ROADMAP.md progress table CONTEXT.md describes ("Phase 37 still reads Not started / 0
plans") does **not match what is on disk right now** — the live file already shows `37 | 6/6 | In
Progress`. This is not stale in the way CONTEXT.md describes, but it is still wrong in a different
way: the on-disk phase directories show 28, 29, 34, 37, 38 all as VERIFICATION status `human_needed`
(not "Complete"), while the ROADMAP table variously calls them "Complete" or vague statuses that
don't say `human_needed` at all. The exact per-phase reconciliation table is below.

Third: `spec/DATABASE.md` already has a substantial Computgraph section (lines 116–~300+, all
7 Computgraph labels documented with property tables) — the ROADMAP deliverable "spec/DATABASE.md
Computgraph section" is **already done**, contrary to what a literal reading of the ROADMAP
deliverable text might suggest needs building from scratch. The real, narrow gap (D4/D-08) is that
the `:ValidationRun`/`:Run` node's Phase-39 auto-validation properties (`trigger`, `verdictSource`,
`capturedAt`, `completedAt`, `attempts`, `lastError`) and the `IntegrationConfig{provider:'AutoValidation'}`
variant are undocumented — confirmed by direct comparison against `data-service/dsav_watcher.py`.

Fourth: the `query audit-uat` under-count is real and reproducible — it reported 5 files / 10 items
where a direct listing (below) shows more; this confirms CONTEXT.md's claim and gives the planner
exact per-file item counts to reconcile by hand.

**Primary recommendation:** Plan Phase 40 as four largely-independent work streams (E2E chains,
provider drill, docs patch, traceability sweep) exactly as CONTEXT.md's Claude's Discretion allows,
using the tables below as the literal task list for the docs and traceability streams — do not
re-derive them from scratch at plan time.

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| NL rule ingest E2E (INTG-01) | API/Backend (data-service + n8n) | Browser (ui-v2 rules-ingest trigger) | The chain is orchestrated server-side (n8n → gateway → Neo4j); the browser only triggers it and displays the result |
| Provider switching (INTG-02) | API/Backend (LLM gateway `resolve_active_provider()`) | Browser (ui-v2 AiEngineScreen settings panel) | Settings are read/written via `/llm/settings`; the panel is a thin CRUD UI already shipped |
| GH intelligence chain (INTG-03) | Desktop/Plugin (Grasshopper components) + API/Backend (data-service `/computgraph/*`) | Database (Neo4j Computgraph) | Canvas-side components (listener, marker, tag, confirm, publish) talk directly to data-service over the bridge; Neo4j is the persistence tier, not an active participant in the chain logic |
| Documentation reconciliation (INTG-04) | Docs/Static (CLAUDE.md, spec/, DG_OBSIDIAN, docs/) | — | Pure content-authoring; no runtime tier owns this |
| Traceability sweep (SC3/D-06) | Docs/Static (REQUIREMENTS.md, ROADMAP.md) | — | Planning-artifact bookkeeping, not application code |
| Evidence capture (D-02/D-04) | Docs/Static (`40-EVIDENCE.json`) | Desktop/Plugin + API/Backend (source of the observations) | The artifact is static, but every field in it is populated by observing the other tiers during the live run |

## Validation Architecture

> `workflow.nyquist_validation` is enabled for this project (not found set to `false` in
> `.planning/config.json` at research time — treat as enabled per the instruction default).

Phase 40's validation profile is unusual and must be planned explicitly as a hybrid: most of its
"tests" are not automatable, and pretending otherwise (writing a pytest that can't actually observe
a live Rhino session) would be worse than naming the human checkpoint honestly.

### Machine-checkable vs. human-checkpoint claims

| Claim | Machine-checkable? | How |
|---|---|---|
| SC3 "all 54 requirements checked or deferred" | **Yes** | Direct read of `.planning/REQUIREMENTS.md` checkbox state + presence of a Deferred section — a grep/count, not a judgement call |
| SC4 "ollama presented as fallback not sole path" | **Yes** | `grep -ri "ollama" CLAUDE.md spec/` (D-15's literal command) — read every hit, assert none imply Ollama is the only path |
| D-06 traceability reconciliation | **Yes** | File-existence + frontmatter `status:` read across `.planning/milestones/v9.0-phases/*/`, cross-checked against `REQUIREMENTS.md` and `ROADMAP.md` — exactly the audit performed in this research (table below) |
| `query audit-uat` count vs. actual file count | **Yes** | Run the CLI, then `grep -c "result:" NN-UAT.md` per file, diff the two — already run once in this research (see UAT section) |
| Step 0 route-surface probe (10 routes via `/openapi.json`) | **Yes** | The exact `curl | python` one-liner in the runbook — a boolean per route, no judgement |
| `.gha` provenance check (SHA256 + Rhino start-time-after-build-time) | **Yes** | File hash comparison + file timestamp comparison — mechanical |
| `dotnet test` / in-container `pytest` gates | **Yes** | Existing suites, pass/fail counts already characterized (see Step 0 table below) |
| INTG-01 "NL rule → ... → Speckle publish, no errors" (SC1 leg 1) | **No — human checkpoint** | Requires a live browser session driving real n8n/gateway/Neo4j/Speckle traffic in real time; no test harness stands in for "the architect watched it work" |
| INTG-03 "object marked → ... → validation run recorded" (SC1 leg 2) | **No — human checkpoint** | Requires live Rhino + Grasshopper interaction (marking objects, tagging, confirming previews) — Session B in the runbook, explicitly a Rhino-in-the-loop procedure |
| INTG-02 provider-switch drill (SC2) | **No — human checkpoint**, gated by D-09's key checkpoint | The live `n8n → gateway → provider API → Neo4j` path "has never once run" per D-11 — unit tests already cover the mechanism, this drill proves the wire |

### Durable artifact discipline for human-observed legs (D-02, D-04)

Because the two E2E chains cannot be captured by an automated test, the validation architecture
substitutes a **written, timestamped, holes-honest artifact** for a green CI checkmark:

- `40-EVIDENCE.json` (shape below, following `39-EVIDENCE.json`'s precedent) records: project
  string used, provider/model per leg, per-step pass/fail, exact `curl`/Cypher output where
  applicable, and an explicit `missing_measurements: []` array — anything not measured is named as
  a hole, never silently omitted or invented. This is the same discipline Phase 39 used and that
  Phase 40 D-02/D-04 explicitly inherit.
- Each `NN-UAT.md` item closed by the runbook gets its `result:` line updated in place (single-line
  `expected:`/`result:` form — see UAT Mechanics section below for why this matters).
- The SC4 grep output is pasted verbatim into `40-EVIDENCE.json`, not paraphrased — a claim like
  "ollama is presented correctly" is unverifiable after the fact; the raw grep lines are.

### Pre-registered SC1 criterion (D-04) and named non-failures

SC1's pass criterion, fixed **before** the run starts, is: *every leg produces its expected artifact
and no unexpected error occurs.* The following three observations are pre-registered as **expected,
not chain failures**, and must not be miscounted as SC1 blockers by whoever runs the checkpoint:

1. **F-39-01** — auto-validation's constant all-false `ValidStatus` (structural, already understood,
   scoped to a follow-up milestone).
2. **Phase 35 SC1's blocked frontier arms** — if the S-A/1 key checkpoint is not satisfied, SC1
   measurement stays blocked-not-failed per D-11's own fallback; this is Phase 35's concern, not
   Phase 40's, and must not be read as an INTG chain failure.
3. **A possible G7 `grammar_as_filter` block on live recognition** (S-B/3) — the runbook explicitly
   calls this "a result, not a broken harness" if it fires on a frontier model; it means F3
   reproduces, not that the chain is broken.

### Sampling rate

- **Per work-stream commit:** the mechanical checks above (route probe, grep gates, file-existence
  checks) — cheap, run every time a docs/traceability edit lands.
- **Per E2E leg:** the blocking human checkpoint, run once per Session (A, B), each producing its
  `40-EVIDENCE.json` section and per-phase `NN-UAT.md` updates.
- **Phase gate:** `/gsd-verify-work 40` reads `40-EVIDENCE.json` + the reconciled `REQUIREMENTS.md`
  + the SC4 grep output as the closing evidence — there is no separate automated "Phase 40 test
  suite" to run.

### Wave 0 gaps

None — this phase adds no new source code requiring test scaffolding. The only "test infrastructure"
Phase 40 needs is the `40-EVIDENCE.json` schema itself (see the Evidence-Artifact Shape section
below) and confirmation that `gsd-tools query audit-uat` cannot be trusted as the sole UAT-completeness
check (confirmed below — plan a manual per-file line count instead).

## Doc-Surface Inventory (D-14)

Built against CLAUDE.md's own "Schema Change Propagation" checklist as the spine, per D-14's
instruction. Each row is a doc file, what v9.0 fact it should state, what it currently states
(with line numbers, directly read this session), and the gap.

| Doc file | What v9.0 fact it should state | What it currently states | Gap |
|---|---|---|---|
| `CLAUDE.md` | LLM gateway is provider-agnostic (Anthropic/OpenAI/Ollama); settings panel in ui-v2 | Already correct — lines 53-54: "an Ollama adapter remains for local models. n8n workflows no longer call Ollama directly"; line 65 table row correctly frames Ollama as "Optional local model" | **Correct, no patch needed.** Confirmed via `grep -ni ollama CLAUDE.md` — only 2 hits, both already accurate |
| `CLAUDE.md` | Computgraph labels/relations (7 labels, 8+ relationship types), 5 new GH components, DSAV ValidationRun properties | Node Labels table (lines ~55-71) lists Computgraph labels correctly (`Representation`, `SharedProperty`, `Object`, `Behavior`, `Algorithm`, `Procedure`, `Pattern`, `Parameter`, `Interface`); Relationships line lists `HAS_BEHAVIOR`...`PARAM_LINK`. **No mention of the 5 new GH component names** (CANVAS LISTENER, OBJECT MARKER, ENTITY TAG, STRUCTURE CONFIRM, COMPUTGRAPH PUBLISH) anywhere in CLAUDE.md's Known Gotchas / component sections | **Missing:** the 5 components have zero CLAUDE.md presence — no GUID table, no gotcha entries for the rising-edge triggers (which CLAUDE.md's Known Gotchas section is exactly the right place for, following the existing GUID-gotcha pattern already used for CONNECTOR/VALIDATION GRAPH) |
| `CLAUDE.md` | DG Canvas Annotation Convention exists and where it's documented | Not mentioned anywhere in CLAUDE.md | **Missing** — should at minimum cross-reference the vault note once D-Discretion creates it, and/or `DG/src/DG.Core/Parsing/CanvasAnnotationParser.cs` as the single source of truth |
| `spec/DATABASE.md` | Computgraph section (7 labels + relations) | **Already present and detailed**, lines 116 onward: Object (136-154), Behavior (158+), and presumably Algorithm/Procedure/Pattern/Parameter/Interface/Representation/SharedProperty follow (not fully re-read this session past line 160 — confirmed structure exists, not confirmed every one of the remaining 6 labels has an equally complete property table) | **Mostly done** — verify the remaining 6 label sections are equally complete before assuming zero patch needed; do not regenerate |
| `spec/DATABASE.md` | `:ValidationRun`/`:Run` properties added by Phase 39 auto-validation: `trigger`, `verdictSource`, `capturedAt`, `completedAt`, `attempts`, `lastError` | Line 108's Run example only shows `Run_Id`, `ValidStatus`, `SendStatus`, `statePayloadJson`, `shaclReportJson` (lines 106-114) — **none of the 6 new properties appear** | **Confirmed gap (D4/D-08).** Exact properties and their producing Cypher constants verified against `data-service/dsav_watcher.py` lines 146-209 (CAPTURE_QUERY, COMPLETE_QUERY, FAIL_QUERY) — see the dedicated D4 section below for the literal patch text |
| `spec/DATABASE.md` | `IntegrationConfig{provider:'AutoValidation'}` variant: `enabled`, `publishEnabled`, `debounceWindowSeconds`, `rateLimitPerMinute`, `maxAttempts`, `updatedAt` | `IntegrationConfig` label is named only in the graph-separation overview table (line 13) and the changelog line 525 — **it has no dedicated node section anywhere in the file**, unlike DesignState/Run which each get one | **Missing entirely** — needs its own `**IntegrationConfig**` subsection under ValidGraph, modeled on the existing DesignState/Run sections |
| `spec/API.md` | `/computgraph/*` routes (Phases 36-38), `/designstate/capture` (Phase 39) | Not fully re-read this session; `spec/API.md:323,333` still describe the **pre-gateway pipeline** ("Ollama Generate" as a pipeline step name) — these lines are historical/pipeline-diagram labels, not necessarily wrong, but should be checked against D-15's grep sweep since they say "Ollama Generate" without qualifying it as one-of-three-providers | **Needs D-15 grep review** — flagged, not fully audited this session (357 lines total, budget did not allow a full re-read) |
| `spec/ARCHITECTURE.md` | Gateway/provider-agnostic architecture | Lines 15, 30, 38-39, 73 describe Ollama as **the** LLM inference service with no gateway/provider mention at all — this file predates Phase 28 and was never updated | **Stale — presents Ollama as sole LLM path.** Falls inside D-15's `spec/` grep scope; needs correction alongside `spec/API.md` |
| `spec/DECISIONS.md` | Provider-agnostic gateway decision (should supersede/extend the old Ollama-only prompt-engineering ADR) | Lines 39, 75 describe "any Ollama model" and "LLM inference via Ollama" as the sole path — pre-Phase-28 content | **Stale — same class of gap**, in `spec/` grep scope |
| `spec/DEPLOYMENT.md` | Gateway + all three providers in the deployment topology | Line 21, 27 list Ollama only among LLM-relevant deployment notes | **Stale — same class of gap** |
| `spec/PROJECT.md` | Provider-agnostic architecture | Line 25: "LLM (Ollama/llama3.1) translates to SWRL atoms" — presents Ollama as the sole translator | **Stale — same class of gap, directly the kind of line SC4 exists to catch** |
| `spec/DG-ID.md` | dgId scoped to 5 entity labels; Behavior/Algorithm excluded by design | Confirmed already correct per `spec/DATABASE.md:118` cross-reference and runbook S-B/5's explicit note; not independently re-read this session, but no contradicting evidence found | **Likely correct, low priority to re-verify** |
| `spec/RULE-PARTITION-POLICY.md` | SWRL-vs-SHACL ownership boundary, referenced by F-39-01 | Not read this session (151 lines) | **Not audited — flag for planner to confirm F-39-01's note cross-links correctly, per D-08** |
| `README.md` | Provider-agnostic gateway; ui-v2 as the served UI | **Never mentions the LLM gateway, Anthropic, OpenAI, or the settings panel at all.** Line 4 still says "converting natural-language design rules into SWRL + atomic rule atoms with Ollama"; lines 40-44, 113-115, 123, 141-142, 208-244 present the entire LLM story as Ollama + LoRA fine-tuning, webhook payloads default to `ollama_model`/`ollama_url` params with **no gateway/provider/apiKey fields documented at all** | **Major gap** — README.md predates Phase 28 entirely and is the single worst offender for "Ollama as sole LLM path." Not literally in D-15's grep scope (`CLAUDE.md spec/` only) but is listed in CLAUDE.md's own Schema Change Propagation checklist and is a canonical D-14 target ("CLAUDE.md and `spec/` get targeted patches... enumerates every doc surface") — planner should decide whether README.md needs its own pass even though SC4's literal grep command doesn't cover it |
| `.github/copilot-instructions.md` | Provider-agnostic gateway | Line 117 (only LLM-adjacent hit): "**Ollama** (`ollama/ollama:latest`): LLM inference, GPU-enabled... Default model: `llama3.1:latest`" — **no gateway/Anthropic/OpenAI mention anywhere in the file** | **Missing** — same class of gap as README.md; named explicitly in CLAUDE.md's Schema Change Propagation checklist |
| `cypher_template.txt` | Computgraph MERGE shapes if the template covers write paths | Not re-read this session (280 lines) | **Not audited — flag for planner**, low risk since Computgraph writes go through `computgraph_publish.py`, not the legacy Cypher template pipeline |
| `training/dataset_schema.json` | Schema v4 fields | Not re-read this session (426 lines) | **Not audited — flag for planner**, likely unaffected since v9.0 didn't touch the rules-ingest schema shape |
| `ontology/dg-shapes.ttl` | SHACL shapes for any new Computgraph/ValidationRun structural invariant | Not re-read this session (538 lines) | **Not audited — flag for planner.** Given F-39-01 is a SHACL-shape interaction (RunStatusShape_valid), the planner should at minimum confirm whether this file needs a comment noting the known auto-validation self-violation, without changing shape logic (that's the follow-up milestone's job) |
| `llm/structure_rules.json` | `inputBindings` (Phase 38) alongside `mappings` | Not re-read this session (45 lines); prior STATE.md decision log confirms `inputBindings` was added as a new sibling top-level key (Phase 38-01) | **Presumed present, not independently re-verified this session** — low risk, small file, quick to confirm at plan time |
| `docs/` component reference | 5 new GH components (D-12) | **Does not exist** — `docs/RELEASE-NOTES-v9.0.md` is absent (only v7.0 and v8.0 exist) | **Confirmed missing — this is the D-12 deliverable itself**, not a patch to an existing file. Layout to mirror: see GH Components section below |
| `DG_OBSIDIAN/knowledge/decisions/` | Phase 39 ADR filed; Phase 30 deferral note | Phase 39 ADR **confirmed present**: `Phase 39 DesignState auto-validation — data-service watcher, SHACL verdict, guardrails.md`. Phase 30 ADR/deferral note: **absent** — no file in the decisions/ directory references orchestration/n8n-vs-OpenClaw at all | **Phase 39 half done; Phase 30 half is the D-13 deliverable itself (not yet written)** |
| `DG_OBSIDIAN/knowledge/` | DG Canvas Annotation Convention note | Only two mentions found repo-wide: `DG_OBSIDIAN/sessions/2026-07-18 phase-32-execution.md` (a session note, not a convention note) and `DG_OBSIDIAN/knowledge/debugging/Phase 35 F3 grammar-as-filter inversion...md` (a debugging note that references but doesn't define the convention) | **Confirmed missing — this is the Claude's-Discretion deliverable** (shape/placement is Claude's call per CONTEXT.md) |

**graphify refresh (D-12/discretion):** No action needed at research time — this is an execution-time
step (`graphify update .`) run after doc edits land, per CONTEXT.md's explicit instruction not to
run it during research.

## Traceability Drift Audit (D-06)

### Corrected phase status table (verified against actual files on disk, 2026-07-28)

| Phase | ROADMAP.md claims (as currently on disk, lines 644-657) | Actual `*-PLAN.md`/`*-SUMMARY.md` count | Actual `*-VERIFICATION.md` status (frontmatter) | Actual `*-UAT.md` presence | Discrepancy |
|---|---|---|---|---|---|
| 28 Cloud LLM Connector | `3/3, Complete, 2026-07-06` | 3/3 | `human_needed` | present | **ROADMAP says Complete; VERIFICATION says human_needed.** STATE.md's own Pending Todos confirms: "Phase 28 UAT item 'E2E provider switch' still human-needed." |
| 29 DG-Aware Context Layer | `8/8, Complete, 2026-07-19` | 8/8 | `human_needed` | present (resolved per runbook, "0" open items) | Same class of mismatch as 28, but the runbook's own audit says 29's UAT item passed 2026-07-20 — likely just stale VERIFICATION frontmatter that was never flipped after the human check happened |
| 30 Orchestration Evaluation | `0/?, Not started` | 0 (no directory) | — | — | **Correct, matches reality** |
| 31 Rules Ingestion/Editing | `0/?, Not started` | 0 (no directory) | — | — | **Correct, matches reality** |
| 32 Computgraph Serialization Core | `5/5, Complete, 2026-07-18` | 5/5 | `passed` | none (logic-only, xUnit-covered) | **Correct** |
| 32.1 DG ID | `7/7, Complete, 2026-07-18` | 7/7 | `passed` | none (xUnit-covered) | **Correct** |
| 33 DG Canvas Bridge | `4/4, Complete, 2026-07-28` | 4/4 | `passed` | present, 2 items still read `pending` in the raw file | VERIFICATION says passed but the UAT file's row-level `result:` fields were never updated to `pass` — reconcile via S-A/4 + S-B/2 per the runbook, which the runbook itself says closes them "on existing evidence" |
| 34 Ontology Tagging Components | `3/3, Complete, 2026-07-18` | 3/3 | `human_needed` | present, 2 open items (OBJECT MARKER test + aesthetic test) | **ROADMAP says Complete; VERIFICATION says human_needed** and UAT confirms open items — mismatch |
| 35 LLM Recognition + Preview | `16/16, In Progress` (no date) | 16/16 | `gaps_found` | present, 2 open items (SC1 sweep, accept gate) | **Roughly consistent** — "In Progress" and `gaps_found` both correctly avoid claiming completion. STATE.md's Deferred Verification table independently confirms `verification_deferred_human`, resume via `/gsd-verify-work 35` |
| 36 Computgraph Persistence | `4/4, Complete, 2026-07-19` | 4/4 | `passed` | present, 1 item PARTIAL (provenance, closed by S-B/5) | **VERIFICATION says passed but UAT still has an open item** — same reconciliation-not-contradiction pattern as 33 |
| 37 Script Structure Validation | `6/6, In Progress` (no date) | 6/6 | `human_needed` | present, 1 open item (live interface delete) | **ROADMAP's "In Progress" undersells it** — it's code-complete with full VERIFICATION/UAT/REVIEW artifacts and only the human_needed live check remains, same as 38. Contrary to CONTEXT.md's description ("still reads Not started / 0 plans"), the row on disk right now already reads `6/6 | In Progress` — CONTEXT.md's characterization of this specific row is **stale relative to what is on disk at research time**; the deeper defect (status label doesn't say `human_needed`, no completion date though code+verification artifacts exist) is still real and still needs fixing |
| 38 AI-Generated Inputs | `7/7, Verifying` (no date) | 7/7 | `human_needed` | present, 3 open items (reinstate, JOIN A, SC3) | **Roughly consistent** ("Verifying" ≈ human_needed), but no completion date recorded despite code being fully executed |
| 39 DesignState Auto-Validation | `5/5, Complete, 2026-07-28` | 5/5 | `passed` | none (0 open items per runbook) | **Correct** |
| 40 E2E Validation and Docs | `0/?, Not started` | 0 (no directory contents beyond CONTEXT.md) | — | — | **Correct, matches reality** (this research is Phase 40's first artifact) |

**Net finding for the planner:** the ROADMAP progress table's real defect is not the specific row
CONTEXT.md called out (that row has already moved) — it's a **systematic pattern**: 5 of 14 phases
(28, 29, 34, 37, 38) have `VERIFICATION.md` status `human_needed` while their ROADMAP row status
says "Complete", "In Progress", or "Verifying" without ever using the word `human_needed`, and 3 of
those 5 (33, 36, plus 37/38's open items) have UAT files with unresolved `result: pending` rows
despite a `passed`/executed VERIFICATION. The corrected table's job is to make ROADMAP's Status
column match VERIFICATION.md's frontmatter status literally, and to make every phase with an open
UAT item say so in one glance.

### REQUIREMENTS.md internal inconsistency (bigger finding than the ROADMAP drift)

`.planning/REQUIREMENTS.md` checks its own per-requirement checkboxes (`- [x]` / `- [ ]`) at
lines 14-113, but its "Traceability" table (lines 156-171) and "Coverage" summary (line 175) were
never updated to match. Direct count from the per-requirement checkboxes as they exist right now:

| Family | Phase | Checkbox count | Checked `[x]` | Traceability table says |
|---|---|---|---|---|
| LLMC-01..06 | 28 | 6 | 6 | ✅ Complete (2026-07-06) — **matches** |
| CTXA-01..05 | 29 | 5 | 5 | Pending — **wrong, should be checked/complete** |
| ORCH-01..04 | 30 | 4 | 0 | Pending — **correct** (unbuilt, becomes Deferred per D-05) |
| RING-01..05 | 31 | 5 | 0 | Pending — **correct** (unbuilt, becomes Deferred per D-05) |
| CGSR-01..04 | 32 | 4 | 4 | ✅ Complete (2026-07-18) — **matches** |
| DGID-01..06 | 32.1 | 6 | 6 | Pending — **wrong, should be checked/complete** |
| BRDG-01..04 | 33 | 4 | 4 | Pending — **wrong, should be checked/complete** |
| TAGC-01..03 | 34 | 3 | 3 | Pending — **wrong, should be checked/complete** |
| RCGN-01..04 | 35 | 4 | 4 | Pending — **wrong** (also arguably premature given `gaps_found` VERIFICATION — planner should decide whether 35's checkboxes being pre-checked is itself an error, separate from the traceability-table mismatch) |
| CGPD-01..05 | 36 | 5 | 5 | Pending — **wrong, should be checked/complete** |
| SVAL-01..03 | 37 | 3 | 3 | ✅ Complete (2026-07-27) — **matches** |
| GHIN-01..04 | 38 | 4 | 4 | Pending — **wrong, should be checked/complete** |
| DSAV-01..03 | 39 | 3 | 3 | ✅ Complete (2026-07-28) — **matches** |
| INTG-01..04 | 40 | 4 | 0 | Pending — **correct** (this phase) |

**Totals:** 47 of 60 requirement checkboxes are already `[x]`, not "6 complete" as the Coverage line
claims. Only ORCH (4), RING (5), and INTG (4) — 13 requirements — are genuinely unchecked, and per
D-05 exactly ORCH+RING (9 requirements) are the ones that move to a Deferred section; INTG-01..04
remain legitimately Pending until Phase 40 executes. **The planner should treat "reconcile
REQUIREMENTS.md's Traceability table and Coverage line against its own checkboxes" as a distinct,
higher-priority task from "reconcile ROADMAP.md against phase directories"** — they are two
different documents with two different kinds of drift, both real.

### Requirements to defer (D-05/D-07) — exact enumeration

**ORCH family (Phase 30, 4 requirements, all unchecked):**
`ORCH-01` (n8n vs OpenClaw evaluation matrix), `ORCH-02` (OpenClaw spike), `ORCH-03` (go/no-go ADR),
`ORCH-04` (migration plan on a go decision).

**RING family (Phase 31, 5 requirements, all unchecked):**
`RING-01` (pass-rate vs. Ollama baseline), `RING-02` (atom-level diff preview), `RING-03`
(clarification-over-guessing), `RING-04` (bounded Cypher-validation retry), `RING-05` (Ollama
fallback regression).

Both families are 100% unbuilt (confirmed: no `30-*`/`31-*` directory exists under
`.planning/milestones/v9.0-phases/`). Per D-05/D-07, these 9 requirements move to a `## Deferred` section in
`REQUIREMENTS.md` naming the target future milestone and the reason, and `40-DEFERRALS.md` carries
the fuller reasoning (n8n works today, OpenClaw needs a decision-gate spike first; rules ingestion
upgrade depends on Phase 30's ADR).

## `spec/DATABASE.md` Gap for Runbook Decision D4 (feeds INTG-04)

**Verified against source, not assumed.** The node label is `:ValidationRun` (not `:DesignState` —
confirming CONTEXT.md's own correction), graph `ValidGraph`, written by
`data-service/dsav_watcher.py`.

**Current `spec/DATABASE.md:106-114` text (Run node section) verbatim:**
```
**Run** — A validation run execution record
```
(:Run {Run_Id: "VRUN_abc123", ValidStatus: [true, false, true], SendStatus: true, statePayloadJson: '{...}', shaclReportJson: '{...}', graph: "ValidGraph", project: "1"})
```
- `Run_Id` — unique identifier for the validation run
- `ValidStatus` — Boolean list, one element per ObjState in the validated DesignState, index-matched to ObjState order
- `SendStatus` — single Boolean per Run (publish-to-Speckle/data-service success)
- `statePayloadJson` — v2 projection for Model Viewer read-back
- `shaclReportJson` — JSON string... (added Phase 823)
```
None of Phase 39's six new properties, and no `IntegrationConfig{provider:'AutoValidation'}`
variant, appear anywhere in this section or elsewhere in the file (confirmed: `IntegrationConfig`
is named only in the graph-separation overview table at line 13, with no dedicated section).

**Exact facts the patch must add** (verified against `data-service/dsav_watcher.py:146-209`):

| Property | Type | Set by | Notes |
|---|---|---|---|
| `trigger` | string, `'auto'` | `CAPTURE_QUERY` (line 151), `COMPLETE_QUERY` (line 191), `FAIL_QUERY` (line 208) | Distinguishes an auto-validation-produced run from a manual VALIDATOR-published one |
| `verdictSource` | string, `'shacl'` | `COMPLETE_QUERY` (line 192) | Names the verdict mechanism |
| `capturedAt` | ISO-8601 string | `CAPTURE_QUERY` (line 152), also copied to `createdAt` (line 153) | Set at capture time by `POST /designstate/capture` |
| `completedAt` | ISO-8601 string | `COMPLETE_QUERY` (line 195) | Set when the watcher's poll loop finishes SHACL validation |
| `attempts` | integer, starts at 0 | `CAPTURE_QUERY` (line 155, init to 0), incremented in `FAIL_QUERY` (line 205, `coalesce(run.attempts,0)+1`) | Retry counter, bounded by `IntegrationConfig.maxAttempts` |
| `lastError` | string | `FAIL_QUERY` (line 207) | Reason for the most recent failed attempt |
| `status` | enum: `captured` \| `completed` \| `superseded` \| `failed` | `CAPTURE_QUERY`, `COALESCE_QUERY` (line 183, marks stale rows `superseded`), `COMPLETE_QUERY`, `FAIL_QUERY` | Not previously documented at all — state machine driving the whole auto-validation lifecycle |
| `SendStatus` | Boolean, `false` at capture | `CAPTURE_QUERY` (line 154) | Already documented for the manual path; confirm the auto path sets the same property, not a variant name |

**`IntegrationConfig` node — needs an entirely new subsection** (verified against
`dsav_watcher.py:125-144`, `CONFIG_READ_QUERY`/`CONFIG_UPSERT_QUERY`):

```
(:IntegrationConfig {graph: "ValidGraph", provider: "AutoValidation", project: "1",
   enabled: true, publishEnabled: false, debounceWindowSeconds: 2.0,
   rateLimitPerMinute: 30, maxAttempts: 3, updatedAt: "2026-...Z"})
```
- Merge key: `(graph, provider, project)` — one row per project, `provider:'AutoValidation'` is the
  literal discriminator constant (`data-service/app.py:53`, `AUTO_VALIDATION_PROVIDER = "AutoValidation"`).
- Absent row = auto-validation disabled for that project (never implicitly created — confirmed in
  `get_auto_validation_config`'s docstring, `dsav_watcher.py:251-254`).

## The Five v9.0 Grasshopper Components (D-12)

All five verified directly from `DG/src/DG.Grasshopper/Components/*.cs` (not the worktree copies —
excluded those from this table). `docs/RELEASE-NOTES-v9.0.md` does not yet exist; the two prior
release-notes files (`v7.0`, `v8.0`) establish the layout it must follow.

### Layout `docs/RELEASE-NOTES-v9.0.md` must mirror (from v7.0/v8.0)

`docs/RELEASE-NOTES-v7.0.md` per-component sections use this structure (verified lines 1-90): a
top summary, then per breaking-change/new-component subsections each with **What broke/What's new**
prose, a **Before/After ASCII wiring diagram** (fenced code block), a **port-mapping table** (old
port → new port), and a **GUID change** line. `docs/RELEASE-NOTES-v8.0.md` (verified, whole file,
74 lines) uses a flatter but same-spirit structure: `## What's new` (bullet per screen/feature),
`## Retired`, `## Backend fixes shipped alongside`, `## Known issues / actions needed`, `## Upgrade`
(a `docker compose` command block). Since v9.0 **adds** components rather than breaking existing
ones, the v7.0 per-component form (name/description/ports/GUID/ASCII diagram) is the more relevant
template — no "Before" state exists for a new component, so use a single wiring diagram showing how
it connects to its neighbors on the canvas.

### Component facts (verified against source)

| Component | GUID | Category / Subcategory | Icon | Inputs (name, type, GH access) | Outputs (name, type, GH access) |
|---|---|---|---|---|---|
| **DG CANVAS LISTENER** | `B0F26347-BB77-4593-A192-7BC3B0BC6169` | `DgComponentCategory.Category` / `GraphSubcategory` | `DgIcons.CanvasListener24` | `Run` (Boolean, item, default `false`) — "Set true to start the DG Canvas Bridge listener"; `Port` (Integer, item, default `8720`) — "Loopback TCP port to listen on (127.0.0.1 only)" | `Status` (Text, item) — "Listener status"; `LastCommand` (Text, item) — "Most recently served bridge command" |
| **DG OBJECT MARKER** | `D3A9F41C-7E52-4B86-9A1D-2C6F8B0E5A73` | `DgComponentCategory.Category` / `GraphSubcategory` | `DgIcons.ObjectMarker24` | `ObjectName` (Text, item) — "Object identity -- becomes the OBJECT - <NAME> scribble"; `Class` (Generic, item, **Optional**) — "Optional OntologyClass from ONTOGRAPH deconstruct -- binds dg:Object to a dg:Class IRI"; `AlgorithmIndex` (Integer, item, default `1`) — "Algorithm digit (1-9)" | `ObjectName` (Text, item); `AlgorithmIndex` (Integer, item); `Status` (Text, item) |
| **DG ENTITY TAG** | `C1E7B4A9-3D82-4F65-8B0A-9E2D5C7F1A64` | `DgComponentCategory.Category` / `GraphSubcategory` | `DgIcons.EntityTag24` | `Kind` (Text, item) — "Proc \| Pat \| Var \| Const \| Emg \| IntF (wired from auto-created value list)"; `Name` (Text, item, **Optional**) — "empty for Pat auto-index"; `ProcIndex` (Integer, item, **not Optional**) — "Full NN token, e.g. 11"; `Tag` (Boolean, item, default `false`) — rising-edge trigger | `GroupName` (Text, item); `MemberCount` (Integer, item); `Status` (Text, item) |
| **DG STRUCTURE CONFIRM** | `A4C1F7E2-9B36-4D58-8E21-7F0A5C3B9D14` | `DgComponentCategory.Category` / `ActionsSubcategory` | `DgIcons.StructureConfirm24` | `Accept` (Text, list, **Optional**) — "Proposal ids to accept (or * for all)"; `Reject` (Text, list, **Optional**); `Apply` (Boolean, item, default `false`) — rising-edge trigger | `Pending` (Text, list) — "name, kind, confidence, member count"; `Status` (Text, item) |
| **DG COMPUTGRAPH PUBLISH** | `E2D4A9F1-3C68-4B72-9A05-6D1E8F2C7B30` | `DgComponentCategory.Category` / `ActionsSubcategory` | `DgIcons.ComputgraphPublish24` | `Project` (Text, item, default `"default-project"`); `DataServiceUrl` (Text, item, default `"http://localhost:8000"`); `Publish` (Boolean, item, default `false`) — rising-edge trigger | `Status` (Text, item); `StaleEntityIds` (Text, list) — "present on server but absent from published payload" |

**Rising-edge trigger note (shared gotcha, worth one CLAUDE.md Known Gotchas entry):** ENTITY TAG,
STRUCTURE CONFIRM, and COMPUTGRAPH PUBLISH all use the same `_lastX = true` initialization pattern
so the first solve with the trigger already `true` does **not** auto-fire — confirmed by matching
comments in all three source files ("mirrors ParameterReinstateComponent's precedent" /
"StructureConfirmComponent precedent"). This is exactly the "toggle dropped to False before each
fire" gotcha CONTEXT.md's Integration Points section already flags — source-verified here, ready to
paste into CLAUDE.md's Known Gotchas section verbatim alongside the existing GUID-gotcha entries.

**Icons:** all five reference `DgIcons.<Name>24` bitmaps — not verified whether these are real
artwork or placeholders reusing other components' art (34-UAT test 2 already flags `ObjectMarker24`/
`EntityTag24` as placeholder reuse; not re-verified for the other three this session).

## Evidence-Artifact Shape (D-02)

`39-EVIDENCE.json` (the file `40-EVIDENCE.json` follows) has this **exact top-level key structure**,
verified by direct read:

```
{
  "phase": 39,
  "measured_at": "<ISO-8601>",
  "source": "<the test file/script that produced this>",
  "configuration": { ... run-wide config knobs ... },
  "software_context": { ... environment facts: neo4j version, worker count, etc ... },
  "measurements": {
    "<scenario_name_1>": { ...scenario-specific fields, including nested "configuration", "source",
                            "measured_at" per-scenario overrides... },
    "<scenario_name_2>": { ... },
    ...
  },
  "findings": [
    { "id": "F-39-01", "title": "...", "observed": {...}, "explanation": "...", "consequence": "..." },
    ...
  ],
  "missing_measurements": []
}
```

Key conventions to carry into `40-EVIDENCE.json`:
- **`missing_measurements` is a top-level array, always present, even when empty** (`[]` in this
  file) — this is the "honest holes" mechanism: anything not measured is named here, never silently
  dropped from the document.
- Each entry under `measurements` is free-form per scenario but consistently includes its own
  `configuration` sub-object (even though a top-level `configuration` also exists) — because
  different scenarios in the same phase ran under different knob settings (e.g. `sc1_loop_closure`'s
  debounce is `2.0`s while `sc2_burst`'s is `5.0`s). Phase 40's two E2E chains should follow the same
  pattern: a `session_a` and `session_b` (or per-step) key, each carrying its own timestamps/provider/
  project fields, rather than one flat shared block.
- `findings[]` is reserved for **named, numbered** defects/observations (the `F-NN-NN` id scheme) —
  Phase 40 should use this array for anything discovered live during the run that isn't already one
  of the three pre-registered non-failures (D-04), following the same `id`/`title`/`observed`/
  `explanation`/`consequence` shape.
- `row_lifecycle` (seen inside `measurements.speckle_publish`) is a good precedent for Phase 40 if a
  live run's Neo4j evidence gets scrubbed by a later test-suite run before it can be screenshotted —
  document what was verified immediately after vs. what is still queryable "now."

## UAT-File Editing Mechanics (D-02, tooling trap)

**Reproduced this session.** `node .claude/gsd-core/bin/gsd-tools.cjs query audit-uat` currently
reports:

```
summary: { total_files: 5, total_items: 10, by_category: { pending: 9, blocked: 1 } }
by_phase: { "33": 2, "34": 2, "35": 2, "37": 1, "38": 3 }
```

This **confirms CONTEXT.md's claim** that the CLI under-reports — it shows only 5 files (33, 34,
35, 37, 38) and drops **28-UAT.md and 36-UAT.md entirely** (both exist on disk and both have items
— 28-UAT has the provider-switch item the runbook calls S-A/2's target; 36-UAT has the provenance
item S-B/5 closes). The CLI's per-phase item counts (33:2, 34:2, 35:2, 37:1, 38:3) also undercount
relative to the runbook's own audit table, which claims 34 has 5 total items and 35 has 7 total —
consistent with CONTEXT.md's stated cause: `expected: |` block-scalar YAML is silently dropped by
whatever parser the CLI uses, while single-line `expected:` values are read correctly.

**Practical implication for the planner:** any Phase 40 plan task that edits a `NN-UAT.md` file to
record a `result:` must (1) not assume `audit-uat`'s output is the full list of what needs closing —
cross-check against the raw file, and (2) write new/edited items using single-line `expected:` so
future audits can see them. **Do not convert existing block-scalar items to single-line as a side
effect of closing them, unless that's an explicit task** — scope creep risk, but doing so incidentally
while editing the same line is low-risk and recommended per CONTEXT.md's own `<specifics>` guidance.

**Files confirmed to exist with open items (from the CLI output + runbook's audit table), that
Phase 40's runbook execution will close:** `28-UAT.md` (1 item, provider switch — S-A/2),
`33-UAT.md` (2 items in raw file per CLI; runbook says 1 open + 1 closeable-on-evidence — S-A/4 +
S-B/2), `34-UAT.md` (2 items visible to CLI, runbook's own audit table says phase has 5 total, 1
open functional + 1 aesthetic-deferred — S-B/1), `35-UAT.md` (2 items visible to CLI; runbook says 7
total, 2 open — S-A/3 + S-B/4), `36-UAT.md` (not visible to CLI at all; runbook says 1 open,
provenance — S-B/5), `37-UAT.md` (1 item, live interface delete — S-B/9), `38-UAT.md` (3 items,
reinstate/JOIN A/SC3 — S-B/6,7,8).

## Runbook Step 0 Prerequisites (Live-Stack Readiness)

Extracted verbatim from `v9.0-PIPELINE-UAT.md` lines 78-87 (already a concrete, runnable checklist —
no research needed to make it more concrete, it already is one):

| Step | Command | Verification |
|---|---|---|
| 0.1 | `docker compose up -d` | `docker compose ps` — data-service, neo4j, n8n, design-grammars, dg-reasoner, speckle-* all Up |
| 0.2 | `docker compose build data-service && docker compose up -d data-service` (non-negotiable — F7 proved this container silently lags code) | route probe (0.3) |
| 0.3 | `curl -s http://localhost:8000/openapi.json \| python -c "import json,sys; p=json.load(sys.stdin)['paths']; [print(('OK  ' if r in p else 'MISS'), r) for r in [...]]"` — the 10 routes probed are: `/computgraph/context/pull`, `/computgraph/recognize`, `/computgraph/publish`, `/computgraph/validate`, `/computgraph/consult`, `/computgraph/generate-inputs`, `/computgraph/candidates/accept`, `/designstate/capture`, `/mcp`, `/llm/settings` | **10 × OK required**; any MISS means rebuild before testing that route's phase |
| 0.4 | `docker compose build --no-cache design-grammars && docker compose up -d design-grammars` (only if `ui-v2/` changed since last run) | Graph screen loads; Computgraph nodes render |
| 0.5 | `dotnet build ./DG/DG.sln -c Release`, copy `.gha` to `%APPDATA%\Grasshopper\Libraries\DG\`, **then** start Rhino (order matters — Rhino locks the file) | SHA256 match + Rhino start-time later than `.gha` build timestamp |
| 0.6 | `dotnet test ./DG/tests/DG.Tests/` | No failures beyond the known `DesignStateValidationFlowTests` (4 fail with Neo4j down — environment, not regression; up to 2 flake on shared-`TestProject` order dependency with Neo4j up) |
| 0.7 | `docker compose exec data-service python -m pytest tests/ -q` | ~573 passed / 0 failed **in-container only** — running from host fails 4 `test_dg_context.py` tests because `neo4j` hostname doesn't resolve outside the compose network |
| 0.8 | Pick one project string for the whole run (e.g. `v9-final-uat`) | Do not reuse `urbanblock-uat` (holds 2026-07-26 evidence) |

**Container freshness as a recurring failure mode (F7):** `/computgraph/publish` shipped
code-complete in Phase 36 but the container was never rebuilt — the first publish attempt 404'd.
This is not a one-off; it is a structural risk every time a phase ships backend code without an
explicit rebuild step, and Step 0.2/0.3 exist specifically to catch it before any E2E leg runs.

**DG_OBSIDIAN decisions folder confirmed (2026-07-28 listing):** 47 files total.
`Phase 39 DesignState auto-validation — data-service watcher, SHACL verdict, guardrails.md` is
present (confirms INTG-04's Phase 39 half is satisfied). No file mentions Phase 30/orchestration —
confirms the D-13 deferral note still needs writing. No dedicated "DG Canvas Annotation Convention"
note exists — confirms the Claude's-Discretion deliverable is still open.

## Common Pitfalls

### Pitfall 1: Treating "ROADMAP row already looks fixed" as "no traceability work needed"
**What goes wrong:** CONTEXT.md's literal example (Phase 37 "Not started / 0 plans") no longer
matches the file on disk, which could read as "D-06 is already done."
**Why it happens:** ROADMAP.md was edited between CONTEXT.md's writing and this research session
(same day, 2026-07-28) — likely by the Phase 33 completion commit.
**How to avoid:** Verify every phase's status against `VERIFICATION.md` frontmatter, not just
against what CONTEXT.md described — the systematic `human_needed`-vs-ROADMAP-label mismatch (5
phases) is the real, still-open defect, documented above.
**Warning signs:** A planner who only fixes the phases CONTEXT.md named (35, 38) and skips 28/29/34
will leave the REQUIREMENTS.md/ROADMAP.md inconsistency substantially unresolved.

### Pitfall 2: Confusing "VERIFICATION passed" with "UAT fully closed"
**What goes wrong:** Phases 33 and 36 both show VERIFICATION `passed` while their UAT files still
have `pending`/`PARTIAL` rows — a planner might assume `passed` means nothing is left to do.
**Why it happens:** GSD's VERIFICATION gate and the runbook's live-Rhino UAT items are tracked
separately by design (the 33-04 precedent explicitly defers live checks past code verification).
**How to avoid:** Treat VERIFICATION status and UAT row status as two independent axes; Phase 40's
runbook execution is what closes the UAT axis for 28, 33, 34, 36, 37, 38 simultaneously.

### Pitfall 3: Assuming `spec/DATABASE.md`'s Computgraph section is missing entirely
**What goes wrong:** The ROADMAP deliverable text ("spec/DATABASE.md Computgraph section") could be
read as "write this section from scratch."
**Why it happens:** The deliverable was written before Phase 36 actually shipped the section (or the
ROADMAP text was never trimmed after 36 landed it).
**How to avoid:** The section already exists and is detailed (verified lines 116-160+ this session).
The real, narrow patch is the Run/IntegrationConfig auto-validation properties (D4), not a rewrite.

### Pitfall 4: Trusting `query audit-uat`'s summary as the full UAT backlog
**What goes wrong:** A planner scoping "close remaining UAT items" purely from the CLI's 10-item,
5-file output will miss 28-UAT and 36-UAT entirely, and undercount 34/35.
**Why it happens:** The CLI silently drops `expected: |` block-scalar items (confirmed, reproduced
this session).
**How to avoid:** Cross-reference against the runbook's own audit table (`v9.0-PIPELINE-UAT.md`
lines 31-48), which was built by reading all nine UAT files directly.

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | `spec/API.md`, `cypher_template.txt`, `training/dataset_schema.json`, `ontology/dg-shapes.ttl`, `llm/structure_rules.json`, `spec/RULE-PARTITION-POLICY.md`, `spec/DG-ID.md` were only partially or not re-read this session (flagged `[ASSUMED]`/not-audited in the Doc-Surface table) | Doc-Surface Inventory | Planner may under- or over-scope the docs-patch task if one of these files has a real, unflagged gap this research missed; low risk given their narrow, code-adjacent scope |
| A2 | Whether the remaining 6 Computgraph labels in `spec/DATABASE.md` (Algorithm, Procedure, Pattern, Parameter, Interface, Representation, SharedProperty — only Object/Behavior were directly read past line 160) have equally complete property tables was not independently confirmed | Doc-Surface Inventory | If one label's section is thin, the planner should patch it alongside the Run/IntegrationConfig fix rather than assuming the whole Computgraph section is done |
| A3 | The GH component icons (`DgIcons.CanvasListener24`, `EntityTag24`, `StructureConfirm24`, `ComputgraphPublish24`) are placeholders reusing other components' art, by analogy to the already-confirmed `ObjectMarker24`/`EntityTag24` finding in `34-UAT.md` test 2 | GH Components section | If some icons are in fact real artwork, `docs/RELEASE-NOTES-v9.0.md` should not blanket-describe all five as placeholder icons |
| A4 | This machine's live Docker/Rhino state (whether containers are currently Up, whether the `.gha` is currently deployed) was not probed this session | Validation Architecture / Runbook Step 0 | The planner should not assume Step 0 will pass on the first try at execution time — it is a checklist to run, not a pre-verified state |

**No claim above rises to the level of a locked decision needing user confirmation before
execution** — all are either narrow doc-file audits deferred to plan/execute time, or live-environment
state that Step 0 itself exists to check. Nothing here contradicts or extends a CONTEXT.md decision.

## Open Questions

1. **Does the REQUIREMENTS.md checkbox-vs-table drift need its own dedicated plan task, separate
   from the ROADMAP.md drift?**
   - What we know: both are real, both are traceability defects, but they are different documents
     with different failure patterns (ROADMAP: status label doesn't say human_needed; REQUIREMENTS:
     summary table never updated after checkboxes were ticked).
   - What's unclear: whether D-06's "traceability sweep" as scoped in CONTEXT.md anticipated the
     REQUIREMENTS.md self-inconsistency specifically, or only the ROADMAP-vs-reality drift.
   - Recommendation: plan them as one traceability-sweep task touching both files, using the two
     tables in this research as the literal diff to apply — they're small, mechanical edits once
     the correct values are known.

2. **Should README.md and `.github/copilot-instructions.md` be patched in the same pass as D-15's
   `CLAUDE.md`/`spec/` grep sweep, even though SC4's literal grep command doesn't include them?**
   - What we know: both files are worse offenders than anything the SC4 grep would catch (README.md
     never mentions the gateway at all), and both are named in CLAUDE.md's own Schema Change
     Propagation checklist.
   - What's unclear: whether the ROADMAP's Phase 40 deliverable text ("CLAUDE.md service map...")
     is meant to scope README.md in or out.
   - Recommendation: include both in the docs-patch work stream — they're clearly part of "every
     doc surface v9.0 touched" per D-14's own framing, even if outside SC4's literal grep scope.

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| Docker Compose stack (data-service, neo4j, n8n, design-grammars, dg-reasoner, speckle-*) | INTG-01/03 E2E chains | **Not probed this session** | — | Step 0.1-0.4 is the execution-time check; not re-verified during research |
| Rhino 8 + Grasshopper with `.gha` deployed | INTG-03 Session B | **Not probed this session** | — | Step 0.5's provenance check is the execution-time gate |
| Anthropic or genuine-OpenAI API key configured | INTG-02 SC2, Phase 35 SC1, Phase 36 test 3 | **Not probed this session** — per D-09/D-11 this is the single prerequisite the plan must checkpoint on | — | D-11's pre-registered fallback: DeepSeek ↔ Ollama switch, SC2 recorded blocked-not-failed |
| `dotnet`, `python`, `docker` CLIs on the executing machine | Step 0.5-0.7 | **Not probed this session** (research ran without invoking these tools; the runbook itself already assumes a working dev machine) | — | None documented; these are hard requirements for Session B |

**Missing dependencies with no fallback:** none identified as hard-blocking beyond what the runbook
itself already names (the API key, which has an explicit fallback per D-11).

**Missing dependencies with fallback:** the frontier-provider key (D-11's DeepSeek↔Ollama fallback).

## Sources

### Primary (HIGH confidence — direct file reads this session, with line numbers cited inline)
- `.planning/milestones/v9.0-phases/40-e2e-validation-and-docs/40-CONTEXT.md` — all 15 locked decisions, discretion, deferred
- `.planning/milestones/v9.0-phases/v9.0-PIPELINE-UAT.md` — the runbook, full text
- `.planning/REQUIREMENTS.md` — full text, checkbox/traceability drift confirmed
- `.planning/ROADMAP.md` — Phase 40 section + Progress Table (lines 614-657)
- `.planning/STATE.md` — Deferred Verification, Deferred Items, Accumulated Context, Pending Todos (lines 1-388 read)
- `data-service/dsav_watcher.py` (lines 100-330) — ValidationRun/IntegrationConfig Cypher constants
- `data-service/app.py` (lines 144-330, 2198-2238) — `/designstate/capture` route, `AUTO_VALIDATION_PROVIDER` constant
- `spec/DATABASE.md` (lines 1-160) — Computgraph section presence, Run node gap
- `spec/ARCHITECTURE.md`, `spec/DECISIONS.md`, `spec/DEPLOYMENT.md`, `spec/PROJECT.md`, `spec/API.md`, `README.md`, `.github/copilot-instructions.md`, `CLAUDE.md` — targeted grep for "ollama"
- `DG/src/DG.Grasshopper/Components/{CanvasListenerComponent,ObjectMarkerComponent,EntityTagComponent,StructureConfirmComponent,ComputgraphPublishComponent}.cs` — full component headers, GUIDs, ports
- `docs/RELEASE-NOTES-v7.0.md` (lines 1-90), `docs/RELEASE-NOTES-v8.0.md` (full, 74 lines) — layout precedent
- `.planning/milestones/v9.0-phases/39-designstate-auto-validation-investigation/39-EVIDENCE.json` — full file, shape reference
- Direct directory scan of `.planning/milestones/v9.0-phases/{28,29,32,32.1,33,34,35,36,37,38,39,40}-*` for plan/summary/verification/uat file counts and VERIFICATION frontmatter
- `node .claude/gsd-core/bin/gsd-tools.cjs query audit-uat` — CLI output, compared against the runbook's own audit table
- `DG_OBSIDIAN/knowledge/decisions/` directory listing — 47 files, Phase 39 ADR confirmed present, Phase 30 ADR confirmed absent
- `DG_OBSIDIAN/` repo-wide grep for "annotation convention" — confirmed no dedicated note exists

### Secondary (MEDIUM confidence)
- None — this research relied entirely on direct repository inspection; no web search was performed
  (not applicable — this is a verification/docs phase against an existing codebase, not a
  library/framework research task)

### Tertiary (LOW confidence)
- None

## Metadata

**Confidence breakdown:**
- Doc-surface inventory: HIGH — every gap claim cites a specific file and line number, verified this session
- Traceability audit: HIGH — built from a direct filesystem scan + frontmatter reads, not inference
- GH component facts: HIGH — read directly from source, not from documentation-about-the-source
- Runbook/Step 0 content: HIGH — the runbook is itself the procedure, quoted rather than paraphrased
- Live-environment readiness (Docker/Rhino/API key state): LOW/UNVERIFIED — explicitly not probed this session; the planner must treat Step 0 as a checklist to run, not a pre-confirmed state

**Research date:** 2026-07-28
**Valid until:** This research describes repository *content* at a point in time during an active
milestone close-out — treat as valid only until the next commit touches any of `CLAUDE.md`, `spec/`,
`.planning/REQUIREMENTS.md`, `.planning/ROADMAP.md`, or any `DG/src/DG.Grasshopper/Components/*.cs`
file. Re-verify line numbers at plan time if more than a few days elapse or if any other phase work
lands first.
