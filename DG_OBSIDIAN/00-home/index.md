---
tags: [home, moc]
date: 2026-07-12
---

# Design Grammar System � Knowledge Vault

Welcome to the DG knowledge base. This vault documents architecture, decisions, integrations, patterns, and operational knowledge for the **Design Grammar System** project.

## Map of Contents

- [[sessions/2026-10-13 DeGram language setting and local test build|DeGram language setting and unpacked test build — manual acceptance open]] (2026-10-13)
- [[sessions/2026-10-12 Building code integration research and v14 planning|Building-code integration research and future v14.0 GSD plan]] (2026-10-12)
- [[knowledge/decisions/Building code integration is isolated as future v14.0|Decision: normative integration is a separate, unactivated v14.0 milestone]] (2026-10-12)
### Atlas (Architecture & Stack)
- [[degram/index|DeGram — integrated Desktop component, shared GSD/context and official upstream fork]]
- [[Architecture is a microservices Docker pipeline]]
- [[Technology stack spans C-Sharp Grasshopper and Python FastAPI and React SPA]]
- [[Neo4j stores ontology and metagraph in a single database]]
- [[Graph schema v4 is the canonical data model]]
- [[archive/Graph schema v3 is the canonical data model (archived)|Graph schema v3 (archived)]]
- [[Deployment uses Docker Compose with nginx reverse proxy]]
- [[UI is a single-file React 18 SPA with no build step]]
- [[Model Viewer is a Vite-built Speckle 3D viewer]]
- [[DG Grasshopper plugin bridges Rhino to Neo4j validation pipeline]]
- [[Data-service is a FastAPI MCP bridge to Neo4j and Speckle]]
- [[n8n runs two async webhook workflows for ingest and query]]
- [[LLM Gateway provides provider-agnostic generation with Anthropic OpenAI and Ollama adapters]]

### Integrations
- [[Neo4j provides graph storage with project-scoped isolation]]
- [[n8n orchestrates LLM-powered rule ingestion and graph queries]]
- [[Ollama runs local LLM inference for Cypher generation]]
- [[Speckle hosts 3D BIM models for validation overlay]]
- [[NeoVis renders interactive graph visualization in browser]]
- [[FastAPI data-service bridges MCP Neo4j and Speckle]]

### Debugging
- [[knowledge/debugging/GSD must_haves parse 0 truths when plan files have CRLF line endings|GSD must_haves parse 0 truths when plan files have CRLF line endings]] (2026-10-12)
- [[knowledge/debugging/DeGram sidebar session list hidden because scope session rows had no profile (F-04)|DeGram sidebar session list hidden: scope session rows had no profile (F-04, fixed in 0.1.11)]] (2026-10-12)
- [[knowledge/debugging/DeGram project pick refused without a grant while the DG page kept the refused project|DeGram project pick refused without a grant while the DG page kept the refused project (signal race unproven)]] (2026-10-12)
- [[knowledge/debugging/DeGram boot error because a scope profile was remembered as the primary profile (F-03)|DeGram boot error: a scope profile remembered as the primary profile (F-03, fixed in 0.1.11, owner pass 2026-10-12)]] (2026-10-11)
- [[knowledge/debugging/DeGram refused project pick released the open project first (F-07)|DeGram refused project pick released the open project first (F-07, fixed in 0.1.11, owner pass 2026-10-12)]] (2026-10-11)
- [[knowledge/debugging/DeGram left-scope backend restarted by the renderer reconnect ladder (G-25)|DeGram left-scope backend restarted by the renderer reconnect ladder; scope gate (G-25, fixed in 0.1.10)]] (2026-10-11)
- [[knowledge/debugging/DeGram 0.1.7 shows compact read-only viewer after project selection|DeGram 0.1.7 live UAT blocked at project open — root cause F-01, fixed in 0.1.8]] (2026-10-11)
- [[knowledge/debugging/DeGram reopened chats came back empty because the transcript read is REST-locked|DeGram reopened chats came back empty: REST transcript read locked (F-02, fixed in 0.1.9)]] (2026-10-11)

### Decisions
- [[knowledge/decisions/Interface language is switched only in DeGram settings, Russian and English only (D-50..D-54)|Interface language is switched only in DeGram settings, Russian and English only (D-50..D-54, Phase 1308)]] (2026-10-12)
- [[knowledge/decisions/Connector access is a per-connector grant without tokens, owner and admin exempt (D-49)|Connector access is a per-connector grant without tokens, owner and admin exempt; add-in signs in with the account (D-49, Phase 1308)]] (2026-10-12)
- [[knowledge/decisions/DeGram connectors table and per-connector access requests (D-45..D-48)|DeGram connectors table, per-connector access requests, one centred sphere, grant separate from membership (D-45..D-48)]] (2026-10-11)
- [[knowledge/decisions/Service images are rebuilt from a clean git export of HEAD, not the dirty working tree|Service images are rebuilt from a clean git export of HEAD, not the dirty working tree]] (2026-10-11)
- [[knowledge/decisions/DeGram access is granted by the project owner, not pasted by the user|DeGram access is granted by the project owner; ring-centre pill, DeGram sidebar, Модели screen (D-39..D-44)]] (2026-10-11)
- [[knowledge/decisions/DeGram 0.1.7 live recheck deferred while Phase 1302 begins|DeGram 0.1.7 live recheck is deferred while Phase 1302 begins]] (2026-10-10)
- [[knowledge/decisions/DeGram pins one document per bridge|DeGram pins one document per bridge: Revit model and GH definition together (D-29)]] (2026-10-09)
- [[knowledge/decisions/DeGram 0.1.6 back-fills legacy profile manifests and cleans the rest once|DeGram 0.1.6 back-fills legacy profile manifests and cleans the rest once (D-30)]] (2026-10-09)
- [[knowledge/decisions/Landing opening sequence and Michroma display face|Main window opens with a clockwise current, nodes one by one, Michroma hero (owner-tuned)]] (2026-10-08)
- [[knowledge/decisions/Model Viewer shows only the validation model|Model Viewer shows only the validation model; Base model checkbox removed (F18, F19)]] (2026-10-08)
- [[knowledge/decisions/DeGram keeps the DG sign-in and finishes Phase 1301 on one PC|DeGram keeps the DG sign-in, pairing without expiry (D-27); reviewer PC moves to the last v13.0 phase (D-28)]] (2026-10-07)
- [[knowledge/decisions/DeGram payload ships only what variant degram can use|DeGram payload: only Python, pm-required tools and six extras; installer 1.9 GB → 490 MB]] (2026-10-07)
- [[knowledge/decisions/DeGram rebrands Hermes at the catalog and the rendered interface|DeGram rebrands Hermes at the catalog and the rendered interface; language without /api/config]] (2026-10-07)
- [[knowledge/decisions/DeGram connects through a user-bound pairing connector in the Connectors tab|DeGram connector: user-bound pairing token dgp_ from the Connectors tab, exchanged for dgd_ (D-25, D-26)]] (2026-10-06; done, plan 17, verified live 2026-10-07)
- [[knowledge/decisions/DeGram relay takes its model and key from the Web UI LLM settings|DeGram relay takes endpoint, model and key from the Web UI LLM settings (D-24)]] (2026-10-06)
- [[knowledge/decisions/DeGram product identity follows the Gena fork lessons|DeGram identity: own icon, Erarchitech vendor, pilot 0.x version; Genpro/Gena reference only]] (2026-10-06)
- [[knowledge/decisions/ValidGraph inline reader reads both parameter shapes, D-09 exclusion lifted|ValidGraph inline reader reads both parameters[] shapes — Phase 1202 D-09 exclusion lifted (2026-10-05)]]
- [[knowledge/decisions/DeGram Phase 1301 execution authorizations and narrowed baseline|DeGram Phase 1301 execution: owner authorizations, narrowed baseline, stop on isolation failure]]
- [[knowledge/decisions/DeGram Phase 1301 adds company scope, Speckle proxy, registry allowlist and loopback-only Revit|DeGram Phase 1301: company map, server Speckle proxy, registry tool allowlist, loopback-only Revit (D-20..D-23)]] (2026-10-04; planned, implementation OPEN)
- [[knowledge/decisions/DeGram Desktop uses a DG theme preset, text wordmark and Russian-first copy|DeGram Desktop: DG theme preset, «DeGram» wordmark, ru-first copy, DG web as a shell page]] (2026-10-04; UI-SPEC approved, implementation OPEN)
- [[knowledge/decisions/DeGram Phase 1301 client isolation, auth relay and Revit MCP fork|DeGram Phase 1301: isolated degram variant, delegated-token LLM relay, read-only Revit MCP fork]] (2026-10-04; discussion captured, implementation OPEN)
- [[knowledge/decisions/DeGram work runs from the framework root with generated child routing|DeGram: work from the framework root; child .hermes.md generated from a framework template]] (2026-10-04)
- [[knowledge/decisions/Architect rules are reshaped to the v12 evaluator boundary before ingest|Architect rules reshaped to the v12 evaluator boundary: range → two rules, strings → numeric proxies, generative rules excluded]] (2026-10-03, facade test)
- [[knowledge/decisions/DeGram Phase 1300 decisions require V8 and server-owned graphs|DeGram Phase 1300: V8 MVP profile, system-managed LLM, server graphs and bounded Revit writes]] (2026-10-03; discussion captured, technical acceptance OPEN)
- [[knowledge/decisions/v12 administrative closeout preserves accepted open technical debt|v12.0: административное закрытие с OPEN долгами, не technical PASS]] (2026-10-02)
- [[knowledge/decisions/Evidence v2 preserves rule outcomes and keeps legacy projections separate|Evidence v2: typed outcomes, zero-row rules и совместимость legacy]] (2026-09-30, Phase 1205.1)
- [[knowledge/decisions/DeGram approved process and company-project rule scope|DeGram: согласованный процесс, классы компании, правила проекта и lessons learned]] (2026-09-30)
- [[knowledge/decisions/Self-registration is local-profile only, invite-only in multi-user|Self-registration is local-profile only, invite-only in multi-user]] (2026-09-30, D-05 amendment)
- [[knowledge/decisions/LLM-written Cypher is guarded by a grammar allowlist, not a blocklist|LLM-written Cypher: grammar allowlist, not blocklist]] (2026-09-30)
- [[archive/Single-file React SPA avoids build tooling for main UI (archived)|Single-file React SPA (v1–v7, archived)]] — superseded by v8.0
- [[decisions/V8 frontend build supersedes no-JSX pattern|V8.0: Vite+React+JSX app replaces no-build pattern]]
- [[SWRL parsing is bespoke regex not vendor OWL library]]
- [[Project isolation uses property filtering not separate databases]]
- [[LLM prompts embed schema constraints instead of fine-tuning]]
- [[knowledge/decisions/DesignState movement typing requires design-space membership|DesignState movement typing needs design-space membership]] — pairwise state diffs cannot type FBS movement
- [[knowledge/decisions/Cited artefacts go to a separate deposit, not the development repository|Cited artefacts go to a separate deposit]] — papers never cite the dev repo; two-licence pattern, verify counts against the deposit
- [[knowledge/decisions/Alignment modules over extension modules in the DG ontology|Alignment modules over extension modules]] — three alignment modules, none extension; `top:` for relations, IFC/bSDD for classification, BOT subsumed rather than bridged; `ontology/` must be rebuilt to match
- [[knowledge/debugging/Word silently reverts scripted docx edits while the file is open|Word silently reverts scripted .docx edits]] — a `~$` lock is not advisory; rebuild, never restore
- [[Passwords hashed client-side with SubtleCrypto SHA-256]]
- [[Validation results publish to Speckle as overlay versions]]
- [[Violation rules invert the constraint in SWRL body]]
- [[Per-run graphics state and screenshot persistence]]
- [[Knowledge workflows use hybrid search-then-summarize for queries]]
- [[Update flow uses three-step match-propose-confirm with server-side diff]]
- [[DesignRuleSession nodes stored in Metagraph]]
- [[ResizeObserver wires Speckle viewer.resize on host element]]
- [[archive/ValidationRunsStrip component with per-project localStorage persistence (archived)|ValidationRunsStrip (archived — replaced by VALIDATION GRAPH)]]
- [[DCM ComputationGraph as 5th ontology layer]]
- [[decisions/v3.0 vendor-neutral rename deferred|v3.0 vendor-neutral rename deferred]]
- [[decisions/Worktree execution disabled due to commit_docs conflict|Worktree execution disabled due to commit_docs conflict]]
- [[decisions/Ontology V7 full rename over incremental|Ontology V7 full rename over incremental]]
- [[decisions/DesignState persists to ValidGraph not Metagraph|DesignState persists to ValidGraph not Metagraph]]
- [[decisions/Run ValidStatus is a per-object boolean array|Run ValidStatus is a per-object boolean array]]
- [[decisions/Rule properties renamed to SWRL RuleName RuleDescription in v4|Rule properties renamed to SWRL RuleName RuleDescription in v4]]
- [[decisions/Kind migration deletes orphan DesignStates on ValidGraph move|Kind migration deletes orphan DesignStates on ValidGraph move]]
- [[decisions/ValidationGraph runtime renamed to ValidGraph per D-14|D-14 — ValidationGraph runtime renamed to ValidGraph]]
- [[decisions/SpecGraph migration matches ValidGraph rename pattern with full index recreation|SpecGraph migration matches ValidGraph rename pattern with full index recreation]]
- [[decisions/Phase 16 DesignState aggregate and statePayloadJson v2|Phase 16: DesignState aggregate + statePayloadJson v2]]
- [[decisions/Phase 17 Graph Access Components layer handles and repository design|Phase 17: Graph Access Components — layer handles + repository design]]
- [[decisions/Phase 18 Rules and Validator Rework decisions|Phase 18: Rules and Validator Rework — ValidStatus per-ObjState, DesignStateBindingService, CLASSIFICATOR purge]]
- [[decisions/Phase 19 Deconstruct and Reinstate Components decisions|Phase 19: Deconstruct and Reinstate Components — REINSTATE Target, StateStatus, DECONSTRUCT error contract]]
- [[decisions/Phase 20 E2E Validation and Docs context decisions|Phase 20: E2E Validation and Docs — E2E scope, release notes, docs strategy, vault refresh]]
- [[decisions/Per-object property binding via PropState.ObjectRef|Per-object property binding via PropState.ObjectRef (v7.0)]]
- [[decisions/V8 frontend build supersedes no-JSX pattern|Phase 21 (v8.0): Design System Foundation — Vite+React+JSX, full component library, specimen page, new app directory]]
- [[decisions/Global phase numbering continues across milestones|Global phase numbering continues across milestones (v7.0:13-20 → v8.0:21-27 → v9.0:28-40 → v10.0:41-49)]]
- [[decisions/Milestone-derived phase numbering convention|Milestone-derived phase numbering vX.Y → X·100+Y·10 (v8.1:810-819, max 10 per milestone)]]
- [[decisions/Content module glob uses numeric prefix pattern|Content module glob uses numeric prefix [0-9][0-9]-* pattern]]
- [[decisions/Reasoning runs in isolated dg-reasoner sidecar not embedded in data-service|v8.2: Reasoning runs in isolated dg-reasoner sidecar, not embedded in data-service]]
- [[decisions/v8.2 hybrid axiom-scoping spike proven|v8.2: Hybrid axiom-scoping (static TBox ∪ live export + curated disjointness)]]
- [[decisions/dg-reasoner sidecar owns the Cypher to RDF pipeline with sync API|Phase 821 (v8.2): dg-reasoner owns Cypher→RDF pipeline — custom translator, sync API, hybrid union in 821]]
- [[decisions/reasoner-screen-phases-checks-results|Phase 822 (v8.2): Reasoner Screen — four-state verdict display, per-card Run on HermiT, in-session result persistence]]
- [[decisions/Phase 822 monochromatic verdict mapping onto DSYS-01|Phase 822: Monochromatic verdict mapping — weight/opacity/glyph instead of green/amber hue]]
- [[decisions/Phase 823 SHACL validation layer design decisions|Phase 823: SHACL Validation Layer — 8 design decisions]]
- [[decisions/Phase 824 CONNECTOR credential integration decisions|Phase 824: CONNECTOR Credential Integration — 4 design decisions (DG.Core heartbeat logic, dgc_ prefix guard, heartbeat-only auth, additive-end input order)]]
- [[decisions/Phase 32.1 DG ID cross-platform identity design|Phase 32.1 (v9.0): DG ID cross-platform identity — dgId wraps cgId, Representation registry, SharedProperty provenance, Revit binds via UniqueId not ElementId]]
- [[decisions/DG ID cross-platform identity scheme|Phase 32.1 (v9.0): DG ID scheme ADR (DGID-06) — positioning against Rhino.Inside.Revit, Speckle, IFC GlobalId, Revit UniqueId, BHoM]]
- [[decisions/Phase 36 Computgraph publish avoids mint_identity|Phase 36 (v9.0): Computgraph publish uses compute_dg_id, NOT mint_identity — prevents label-less MERGE anchor duplicates]]
- [[decisions/Graph Viewer search bar adaptive value dropdown|Graph Viewer search bar: Combobox primitive — data-derived value list, open-ended (free text preserved), no engine changes]]
- [[decisions/Phase 35 recognition quality remediation — hybrid Tier 0 Tier 1 architecture and pytest eval|Phase 35 (v9.0): Hybrid Tier 0 deterministic + Tier 1 LLM; pytest fixture-driven eval; labelling flywheel; sub-model training deferred]]
- [[decisions/Phase 35 Corpus A frozen as-is, Frame Truss binaries not committed|Phase 35 (v9.0): Corpus A not re-grounded on recovered Frame/Truss source; *.gh/*.3dm gitignored (20 MB .3dm never committed)]]
- [[decisions/Phase 37 structure validation — rule-mapping file-first, severity taxonomy, ephemeral results|Phase 37 (v9.0): Rule-mapping file-first (`llm/structure_rules.json`), severity taxonomy reuses SHACL, results ephemeral for MVP]]
- [[decisions/Phase 39 DesignState auto-validation — data-service watcher, SHACL verdict, guardrails|Phase 39 (v9.0): DesignState auto-validation — data-service watcher (paths a/c empirically blocked), SHACL verdict as the only server-side judge, three per-project guardrails; SHACL/SWRL coverage gap is the headline open finding]]
- [[knowledge/decisions/Live-infrastructure GSD plans run by the orchestrator directly, never DSH|Phase 1204 (v12.0): live-infra plans (Docker restarts, real LLM cost, D-28 key handling) run by the orchestrator directly, never DSH]]
- [[knowledge/decisions/1204-09 scoped to rule-ingest only, recognition prompt construction deferred|Phase 1204 (v12.0): 1204-09 scoped to rule-ingest only — faithfully reproducing recognition's internal prompt construction deferred]]

### Debugging
- [[knowledge/debugging/DeGram chat stays on the first scope profile after a project or company change|DeGram chat stays on the first scope profile; other projects fail closed with CREDENTIALS_MISSING (G-7)]] (2026-10-09, open)
- [[knowledge/debugging/DeGram Revit adapter could not load under pyRevit IronPython 3.4|DeGram Revit adapter unloadable under pyRevit IronPython 3.4: disabled by default, async def, implicit imports, urllib, JSON body (G-8..G-12)]] (2026-10-09, fixed in working tree)
- [[knowledge/debugging/DeGram installers bundled a stale revit-mcp copy from the build folder|DeGram installers 0.1.0-0.1.5 bundled a stale D:\dgb\revit-mcp copy (no DEGRAM_REVIT_MCP_SOURCE)]] (2026-10-09, fix planned in 1301-23)
- [[knowledge/debugging/Backslashes lost in a shell edit corrupted the DeGram build adapter path|Backslashes lost in a shell edit corrupted the DeGram build adapter path (CR in DEGRAM_REVIT_MCP_SOURCE)]] (2026-10-09)
- [[knowledge/debugging/Model Viewer camera reset and Design State jump on run switch|Model Viewer: Speckle emits no Stationary event, run switch re-framed the camera, Design State persisted per run]] (2026-10-08, fixed)
- [[knowledge/debugging/DeGram graph tool answer was spilled to a file the agent cannot read|DeGram graph tool: 8.6 MB graph, rules read after graph, answer spilled past the agent's 100K-char threshold (G-1)]] (2026-10-07, fixed)
- [[knowledge/debugging/Kaspersky on PC1 blocks the DeGram installer and the installed executable by path|Kaspersky on PC1 terminates the DeGram installer and resets the installed DeGram.exe by path]] (2026-10-07, open, environment)
- [[knowledge/debugging/DESIGN STATE and VALIDATOR assumed one class per Design State|DESIGN STATE/VALIDATOR: length guard and index-matched ValidStatus assumed one class per Design State (F15/F16)]] (2026-10-05, fixed)
- [[knowledge/debugging/Reinstate from ValidGraph read null parameters and wrote zeros into sliders|REINSTATE from ValidGraph: null parameters (D-09 silent reader) written as zeros; labels lost (F23–F25)]] (2026-10-05, fixed, install pending)
- [[knowledge/debugging/CONNECTOR caches an unreachable heartbeat until the token or Go changes|CONNECTOR: cached Unreachable heartbeat survives data-service restart (F14)]] (2026-10-05, open)
- [[knowledge/debugging/Rule ingest blends a rule invented from a bare Rule_Id into the existing rule|Rule ingest: bare Rule_Id → invented rule MERGEd into existing one; ID/recognition findings (F13, F6/F9–F12)]] (2026-10-05, open)
- [[knowledge/debugging/Grasshopper Panels can neither be captured as parameters nor safely carry tokens|GH Panels: not capturable by PARAMETER STATE; token via Panel persists in .gh (F7/F17)]] (2026-10-05, open)
- [[knowledge/debugging/Model Viewer shows a foreign base model and a hard-coded tile property catalogue|Model Viewer: foreign base model, shadow, black preview, camera reset, hard-coded tile props (F18–F22)]] (2026-10-05, open)
- [[knowledge/debugging/DeGram first launch put its own hermes command first in the user PATH|DeGram put its own hermes.cmd first in the user PATH — expose_cli Windows branch before the bundle skip (F-07)]] (2026-10-06, fixed)
- [[knowledge/debugging/Commit build driver overrode the DeGram icon, version and vendor|Commit build driver overrode DeGram icon, version and vendor — verify the packaged exe]] (2026-10-06, fixed)
- [[knowledge/debugging/Electron app exits silently when launched from VS Code shell with ELECTRON_RUN_AS_NODE|Electron app exits silently (exit 0) from a VS Code shell — remove ELECTRON_RUN_AS_NODE via ProcessStartInfo]]
- [[knowledge/debugging/Packaged DeGram ignored the degram variant and attached to the live Hermes|Packaged DeGram ignored the degram variant and attached to the live Hermes — identity gate, scrubbed env]]
- [[knowledge/debugging/GH deadline test patched the clock only after the first request|GH deadline test: clock patched only after the first request — flaky 30 s wait]]
- [[knowledge/debugging/OBJECT STATE index ObjectRefs collide across classes for computed geometry|OBJECT STATE: index ObjectRefs (obj_i) collide across classes for computed geometry]] (2026-10-03, open)
- [[knowledge/debugging/V2 UI has no Speckle project link form and the setup guide predates v7|V2 UI: no Speckle project link form; setup guide predates v7; stale DG.gha unnoticed]] (2026-10-01, open)
- [[knowledge/debugging/Windows auth store atomic replace can fail on reader sharing locks|Windows auth store: sharing conflict при atomic replace и bounded retry]] (2026-10-02)
- [[knowledge/debugging/Typed non-verdicts can become passed at the GH publication boundary|GH wire: Unsupported превращался в passed; raw JSON и межъязыковой admission]] (2026-09-30)
- [[sessions/2026-09-30 v12 audit and Phase 1205.1 canonical status closure|Сессия: v12 audit и verified closure 1205.1]]
- [[knowledge/debugging/Blocklist checks over LLM-written Cypher were bypassed three times|Blocklist checks over LLM-written Cypher bypassed three times]] (2026-09-30)
- [[Docker layer caching can serve stale index.html]]
- [[Browser cache prevents seeing UI updates after rebuild]]
- [[Neo4j node tagging required after n8n ingestion]]
- [[LLM Cypher output needs bracket nesting validation]]
- [[Edit mode requires cleanup of old atoms before re-creation]]
- [[docker-compose depends_on cycle with n8n and data-service]]
- [[Knowledge webhook field name mismatch causes stale LLM output]]
- [[Layout overflow guards required for resizable flex children]]
- [[Worktree branch commits with spurious deletions]]
- [[Stale index name in spec-query n8n workflow]]
- [[debugging/n8n workflows had a fatal quote bug and silent project-scoping failure|n8n workflows: fatal quote bug + silent project-scoping failure]]
- [[debugging/get_adapter ignores baseUrl from settings|get_adapter() ignores baseUrl — DeepSeek key sent to OpenAI]]
- [[debugging/Model Viewer validation objects not found in Speckle world tree|Model Viewer: validation objects not found in Speckle world tree]]
- [[debugging/Glob pattern star star star star matched zero content modules|Glob pattern ##-*.js matched zero content modules (Phase 815 code review)]]
- [[debugging/code-review-821-proxy-timeout-orphaned-jvms-arg-pos|Phase 821 code review: proxy timeout mismatch, orphaned JVMs, silent ARG.pos data loss]]
- [[debugging/CR-01 validStatus truthy check causes false SHACL violations|CR-01: truthy valid_status check causes false-positive SHACL Violations on empty ValidStatus]]
- [[debugging/graph-query-design-states-schema-mismatch|Phase 29 graph_query design-state bug: schema mismatch between aspirational :DesignState nodes and production ValidationRun.statePayloadJson]]
- [[debugging/perplexity-mcp-parallel-call-crashes-browser-profile|Perplexity MCP: parallel calls crash the shared Chrome profile lock]]
- [[debugging/Phase 36 schema doc bugs|Phase 36: Schema doc bugs — HAS_INTERFACE direction, PARAM_LINK direction, Algorithm merge key (runtime was correct, docs were stale)]]
- [[debugging/Column flex dropdown rows overlap instead of scrolling|Column flex + maxHeight: rows compress instead of scrolling (text overlaps, no scrollbar) — fix with flex: none on children]]
- [[debugging/Phase 35 F3 grammar-as-filter inversion — the few-shot itself teaches the failure|Phase 35 F3: the sole few-shot example demonstrates grammar-as-filter; model faithfully executes the failure mode. Fixed by: system prompt + grammar-stated-twice + counterexample few-shot]]
- [[debugging/Phase 35-36 dataType inference gap breaks publish (F5)|F5: bare Number component infers null dataType with no warning — accepted proposal 422s the whole Phase 36 publish]]
- [[debugging/Phase 36 provider-model-confidence never persisted (F6)|F6: provider/model/confidence structurally unpersistable for recognized nodes — accept path drops them, models have no such fields]]
- [[debugging/Phase 36 data-service image predated the phase (F7)|F7: data-service image predated Phase 36 — /computgraph/publish 404'd until rebuilt]]
- [[debugging/Phase 35 latent parser bug — pattern host resolved by document order|Latent: ComputeHostPatternIds picks a host by document order, so a Procedure listing a transitively-nested pattern silently drops PATTERN_HOST_TO. Fix planned as 35-16]]
- [[debugging/Phase 35 R4 interface rule unreachable on live Grasshopper data|Phase 35: R4 Interface rule matches on `name.startswith("Param")`, but no real GH component ever displays as "Param..." — rule is unreachable on live canvases, and its only test feeds a fictitious name that hides the bug]]
- [[knowledge/debugging/Python module-identity mismatch silently defeats a monkeypatch|Phase 1204: bare `import cassette` vs. `from recognition_eval import cassette` bound two separate sys.modules entries — patching one's `_FIXTURES_ROOT` never touched the module the codebase actually calls into]]
- [[knowledge/debugging/D-24 report schema had no item dimension, risking misleading pooled metrics|Phase 1204: report_schema_llm.json's providerStrata had no item dimension — pooling 5 different rule-ingest prompts would have produced a substantively misleading near-zero agreement figure]]

### Patterns
- [[knowledge/patterns/GSD wave barriers can block independent preparation before external approval|GSD wave barriers: separate draft preparation from late external acceptance]] — Phase1300 verified planning, not runtime acceptance
- [[Async polling pattern for n8n workflow execution tracking]]
- [[Cypher MERGE idempotent node creation pattern]]
- [[Config injection via entrypoint.sh sed replacement]]
- [[Grasshopper async component with ScheduleSolution polling]]
- [[Pydantic models validate all API boundaries]]
- [[Conditional compilation guards Grasshopper SDK availability]]
- [[Pure grouping adapter testable as plain function]]

### Business
- [[Design Grammars automates architectural compliance checking]]
- [[Target audience is architects and urban planners]]
- [[Product bridges natural language rules to graph-based validation]]

### Research (State of the Art)
- [[research/index|Research MOC — SoA taxonomy, conspects, keywords]] (merged from 02_PhD_2024 vault, 2026-07-18)

### Dissemination (Publications & Talks)
- [[dissemination/index|Dissemination MOC — venue status board + ITcon series T1–T4]]
- [[dissemination/consistency-map|Consistency map — публикации ↔ dev-артефакты]]
- [[dissemination/Series coherence map|Карта согласованности серии T1–T4]]
- [[dissemination/T1 — Онтологический фреймворк|T1]] · [[dissemination/T2 — Кодирование правил|T2]] · [[dissemination/T3 — Отслеживание состояний|T3]] · [[dissemination/T4 — Дизайн-пространство|T4]]
- **Revision rounds:** [[dissemination/revisions/T1 R11-R12 — integrity restoration|T1 R11→R12 — integrity restoration]] · [[dissemination/revisions/T1 R14.3 — R14.4 package port and C45 resolution|T1 R14.3 — R14.4 package port and C45]]

### Tools & Infrastructure
- [[Graphify-CGD-Obsidian integration improvement plan|Graphify ↔ CGD ↔ Obsidian — план интеграции]]
- [[graphify/Graph Index|Graphify Knowledge Graph — индекс по сообществам]]
- [[graphify/Graph Connections Dashboard|Graph Connections Dashboard (Dataview)]]
- [[graphify/GSD and Neo4j integration|GSD ↔ graphify и Neo4j интеграция]]
- `graphify-out/` — сырой граф (1836 nodes, 198 communities); regen заметок: `scripts/refresh_graphify.sh`

### Operational
- [[sessions/2026-10-12 Phase 1308 executed plans 01-10, 12, 13, 16, 23 (14 of 24)|2026-10-12 Phase 1308 executed — 14 of 24 plans (waves 1–3, plan 13); dgk_ sessions, dgc_ retired, i18n layer; paused by the owner]]
- [[sessions/2026-10-12 Phase 1308 planned, 24 plans, language switch moved to DeGram settings|2026-10-12 Phase 1308 planned — 24 plans in 10 waves, language switch moved to DeGram settings (D-50..D-54)]]
- [[sessions/2026-10-12 Phase 1301 gap plans 37-41 executed, DeGram 0.1.11 built and UAT result|2026-10-12 Phase 1301 gap plans 37–41 executed, DeGram 0.1.11 built; owner UAT steps 1–5, 7 pass, step 6 became D-49]]
- [[sessions/2026-10-11 DeGram 0.1.10 UAT and 0.1.11 fix round planned|2026-10-11 DeGram 0.1.10 UAT (7 pass, 4 fail) and the 0.1.11 fix round planned (plans 37–41, D-45..D-48)]]
- [[sessions/2026-10-11 Phase 1301 gap round executed and DeGram 0.1.10 built|2026-10-11 Phase 1301 gap plans 33–36 executed, DeGram 0.1.10 built and services rebuilt from clean HEAD; owner live UAT pending]]
- [[sessions/2026-10-11 Phase 1301 plans 31-32 and plan 33 blocked|2026-10-11 Phase 1301 plans 31–32 offline-complete; plan 33 blocked by denied pairing-panel deletion and failing full checks]]
- [[sessions/2026-10-09 Phase 1301 live UAT on PC1 and the 0.1.6 gap list|2026-10-09 Phase 1301 live UAT on PC1 — DGCL-01/03 pass, 04 bridge layer pass after adapter fixes, 02 fails (G-7), gaps G-3..G-17, D-29]]
- [[sessions/2026-10-09 Phase 1301 gap-closure plans for DeGram 0.1.6|2026-10-09 Phase 1301 gap-closure plans 18-23 for 0.1.6 — G-3..G-17, D-29, D-30 pending]]
- [[sessions/2026-10-09 Phase 1301 gap plans 18-23 executed and DeGram 0.1.6 shipped|2026-10-09 Phase 1301 gap plans 18-23 executed — 0.1.6 pushed, built, installed; D-30 decided; live recheck open]]
- [[sessions/2026-10-08 Server hosting research for DG reviewers|2026-10-08 DG hosting research + university lab server plan (16 tasks, dependency graph verified)]]
- [[sessions/2026-10-07 PhD progress report supersession and NotebookLM materials|2026-10-07 PhD report 071026 supersedes 051026, dates removed, source preserved; NotebookLM and infographic sources prepared]]
|- [[sessions/2026-10-07 Phase 1301 DeGram pairing connector, rules read fix, 490 MB installer and no Hermes name|2026-10-07 Phase 1301 — plan 17 pairing connector done, G-1/F-11 closed live, installer 490 MB, no Hermes name, 0.1.4 approved]]
- [[sessions/2026-10-06 Phase 1301 audit-fix, DeGram identity and isolation beside open Hermes|2026-10-06 Phase 1301 audit-fix: Gena lessons, DeGram icon/version/vendor, isolation beside open Hermes proven, branches pushed, relay from Web UI settings, plan 17 pairing connector]]
- [[sessions/2026-10-06 Phase 1301 plan 15 rebuild and DeGram isolation proven beside Hermes|2026-10-06 Phase 1301: installer rebuilt from 910a060d, DeGram isolation proven beside Hermes, relay probe added, plan 16 started]]
- [[sessions/2026-10-05 Phase 1301 executed through plan 14, plan 15 launch failed isolation|2026-10-05 Phase 1301: executed through plan 14; plan 15 launch failed isolation, nothing pushed]]
- [[sessions/2026-10-04 Phase 1301 planned|2026-10-04 Phase 1301: researched and planned — 15 plans / 8 waves, D-20..D-23, all gates pass]]
- [[sessions/2026-10-04 Phase 1301 UI design contract|2026-10-04 Phase 1301: UI-SPEC approved — DG theme preset, wordmark, ru-first copy, DG page, 47 UI states resolved]]
- [[sessions/2026-10-04 Phase 1301 context gathered|2026-10-04 Phase 1301: context gathered — runtime isolation, auth relay, Revit MCP fork, LLM context card]]
- [[sessions/2026-10-04 DeGram automatic context and planning routing|2026-10-04 DeGram: automatic context installed in AGENTS.md/CLAUDE.md/.hermes.md, verified from three cwds]]
- [[sessions/2026-10-04 Phase 1301 planning gated on context and UI-SPEC|2026-10-04 Phase 1301: planning stopped at gates; discuss → UI-SPEC → plan order chosen]]
- [[sessions/2026-10-04 DeGram official fork and framework workspace|2026-10-04 DeGram: official Hermes fork, pinned framework workspace, explicit-context blocker]]
- [[sessions/2026-10-04 DeGram scope revision and first client increment|2026-10-04 DeGram: comparative baseline removed; first isolated read-only web client tested, Desktop integration next]]
- [[sessions/2026-10-05 v12 hexagonal facade test steps 2-8 and five DG fixes|2026-10-05 v12 hexagonal facade test: steps 2–7 passed (44/44 runs match), step 8 blocked, five DG defects fixed (F15/F16/F23/F24/F25)]]
- [[sessions/2026-10-04 v12 hexagonal facade full-cycle test setup|2026-10-04 v12 hexagonal facade full-cycle test: setup, 8 rules approved, paused at step 2]]
- [[sessions/2026-10-03 Phase 1300 planning verified|2026-10-03 Phase 1300 planning: 9 plans, 25 tasks, 7 waves; independent check PASSED]]
- [[sessions/2026-10-03 v13 activation and Phase 1300 context|2026-10-03 v13.0 activation and Phase 1300: 27 owner decisions, Ready for planning]]
- [[sessions/2026-10-02 v12 override closeout with accepted debt|2026-10-02 v12.0 — reaudit, offline repair и override closeout с принятыми долгами]]
- [[sessions/_template|Session log template]]
- [[sessions/2026-09-30 DeGram process approved and bilingual diagrams|2026-09-30 DeGram — согласование процесса и схемы RU/EN]]
- [[sessions/2026-04-05 Project specification and CLAUDE.md creation|2026-04-05 Spec & CLAUDE.md]]
- [[sessions/2026-04-05 Obsidian vault creation|2026-04-05 Vault creation]]
- [[sessions/2026-04-05 Model Viewer screenshot and per-run graphics state|2026-04-05 MV screenshots & per-run gfx]]
- [[sessions/2026-04-06 Phase 01 KnowledgeGraph schema execution|2026-04-06 Phase 01 execution]]
- [[sessions/2026-04-06 Phase 02 data-service CRUD and folder ingest execution|2026-04-06 Phase 02 execution]]
- [[sessions/2026-04-06 Phase 03 context and planning|2026-04-06 Phase 03 context & planning]]
- [[sessions/2026-04-06 Phase 03 n8n knowledge workflows execution|2026-04-06 Phase 03 execution]]
- [[sessions/2026-04-06 Phase 04 context and planning|2026-04-06 Phase 04 context & planning]]
- [[sessions/2026-04-07 Phase 04 update-flow-endpoints execution|2026-04-07 Phase 04 execution]]
- [[sessions/2026-04-07 Phase 05 UI mode restructuring execution|2026-04-07 Phase 05 execution]]
- [[sessions/2026-04-08 Phase 06 execution and Phase 07 context|2026-04-08 Phase 06 execution & Phase 07 context]]
- [[sessions/2026-04-08 Phase 07 UI-SPEC design contract|2026-04-08 Phase 07 UI-SPEC]]
- [[sessions/2026-04-08 Phase 07 planning|2026-04-08 Phase 07 planning]]
- [[sessions/2026-04-08 Collapsible Workflow Cypher panels|2026-04-08 Collapsible Workflow Cypher panels]]
- [[sessions/2026-05-10 Phase 05 model-viewer grouping execution|2026-05-10 Phase 05 (v2.0) execution]]
- [[sessions/2026-05-30 PhD publications series T1-T4 drafts|2026-05-30 PhD publications T1–T4 drafts]]
- [[sessions/2026-06-01 Ontology v6.0 restructure — Core band, SpecGraph, partonomy|2026-06-01 Ontology v6.0 restructure]]
- [[sessions/2026-06-01 Ontology v6.1 vendor-neutralization|2026-06-01 Ontology v6.1 vendor-neutralization]]
- [[sessions/2026-06-22 Graphify-CGD-Obsidian integration Phase 1|2026-06-22 Graphify integration Phase 1]]
- [[sessions/2026-06-22 Graphify integration Phases 2-4|2026-06-22 Graphify integration Phases 2-4]]
- [[sessions/2026-06-23 v3.0 Phase 7 Schema Foundation execution|2026-06-23 v3.0 Phase 7 Schema Foundation execution]]
- [[sessions/2026-06-23 New PC Docker setup and n8n workflow fix|2026-06-23 New PC setup + n8n workflow fix]]
- [[sessions/2026-07-02 v7.0 milestone init from GH_DesignGrammars schema|2026-07-02 v7.0 milestone init from GH_DesignGrammars schema]]
- [[sessions/2026-07-03 Phase 13 discuss - ValidGraph and per-object ValidStatus|2026-07-03 Phase 13 discuss — ValidGraph & per-object ValidStatus]]
- [[sessions/2026-07-03 Phase 13 planning - 4 plans across 3 waves|2026-07-03 Phase 13 planning — 4 plans across 3 waves]]
- [[sessions/2026-07-03 Phase 13 execution and Nyquist validation|2026-07-03 Phase 13 execution + Nyquist validation]]
- [[sessions/2026-07-03 Phase 14 planning - 7 plans across 3 waves|2026-07-03 Phase 14 planning — 7 plans across 3 waves]]
- [[sessions/2026-07-03 Phase 15 discuss - SpecGraph rename decisions|2026-07-03 Phase 15 discuss — SpecGraph rename decisions]]
- [[sessions/2026-07-04 Phase 15 execution|2026-07-04 Phase 15 execution — SpecGraph Runtime Rename]]
- [[sessions/2026-07-04 Phase 16 discuss - DG.Core state models and state components|2026-07-04 Phase 16 discuss — DG.Core state models and state components]]
- [[sessions/2026-07-04 Phase 16 planning - 6 plans across 3 waves|2026-07-04 Phase 16 planning — 6 plans across 3 waves]]
- [[sessions/2026-07-04 Phase 16 execution - 6 plans all complete|2026-07-04 Phase 16 execution — all 6 plans complete]]
- [[sessions/2026-07-04 Phase 17 discuss - Graph Access Components|2026-07-04 Phase 17 discuss — Graph Access Components]]
- [[sessions/2026-07-04 Phase 17 planning|2026-07-04 Phase 17 planning — 4 plans, 2 waves]]
- [[sessions/2026-07-04 Phase 17 execution — Graph Access Components|2026-07-04 Phase 17 execution — Graph Access Components]]
- [[sessions/2026-07-04 Phase 18 discuss - Rules and Validator Rework|2026-07-04 Phase 18 discuss — Rules and Validator Rework]]
- [[sessions/2026-07-04 Phase 18 planning — research|2026-07-04 Phase 18 planning — research]]
- [[sessions/2026-07-04 Phase 18 UI design contract|2026-07-04 Phase 18 UI design contract — UI-SPEC approved]]
- [[sessions/2026-07-05 Phase 18 execution — Rules and Validator Rework|2026-07-05 Phase 18 execution — 5 plans complete, 9/9 verified]]
- [[sessions/2026-07-05 Phase 19 discuss — Deconstruct and Reinstate Components|2026-07-05 Phase 19 discuss — Deconstruct and Reinstate Components]]
- [[sessions/2026-07-05 Phase 19 execution — Deconstruct and Reinstate Components|2026-07-05 Phase 19 execution — 3 plans complete, 19/19 verified, all 6 code review issues fixed]]
- [[sessions/2026-07-05 Phase 18 planning — 5 plans 2 waves with Path A ClassIri|2026-07-05 Phase 18 planning — 5 plans, 2 waves, Path A ClassIri]]
- [[sessions/2026-07-04 Phase 15 planning — SpecGraph Runtime Rename (replan)|2026-07-04 Phase 15 replan — SpecGraph Runtime Rename]]
- [[sessions/2026-07-05 Phase 20 discuss — E2E Validation and Docs|2026-07-05 Phase 20 discuss — E2E Validation and Docs]]
- [[sessions/2026-07-05 Phase 20 planning — 3 plans, all verified|2026-07-05 Phase 20 planning — 3 plans, all verified]]
- [[sessions/2026-07-05 Phase 20 E2E Validation and Docs|2026-07-05 Phase 20 execution — E2E validation, release notes, docs update, vault refresh]]
- [[sessions/2026-07-06 v9.0 Phase 01 planning|2026-07-06 v9.0 Phase 01 planning — research + 3 plans, ready for execution]]
- [[sessions/2026-07-07 v9.0 Phase 01 execution|2026-07-07 v9.0 Phase 01 execution — 3 plans complete, 6/7 verified, code review fixed]]
- [[sessions/2026-07-07 DesignStateLabel input and output|2026-07-07 DesignStateLabel input/output]]
- [[sessions/2026-07-07-LABEL-component|2026-07-07 LABEL component]]
- [[sessions/2026-07-07 METAGRAPH input rename fix|2026-07-07 METAGRAPH input rename fix]]
- [[sessions/2026-07-08 Per-object property binding and Speckle auto-config|2026-07-08 Per-object property binding & Speckle auto-config]]
- [[sessions/2026-07-08 audit-fix and Phase 27 Speckle 3D embed plan|2026-07-08 Audit-fix classification + Phase 27 Speckle 3D embed]]
- [[sessions/2026-07-08 Phase 27 Speckle 3D embed execution|2026-07-08 Phase 27 Speckle 3D embed — execution]]
- [[sessions/2026-07-08 Model Viewer filter/coloring regression|2026-07-08 Model Viewer filter/coloring regression]]
- [[sessions/2026-07-08 v8.0 Phases 21-26 autonomous execution|2026-07-08 v8.0 Phases 21–26 autonomous execution + n8n bug fixes + CLAUDE.md LLM gateway correction]]
- [[decisions/Phase 27 Speckle 3D embed design decisions|2026-07-08 Phase 27 — 6 Speckle 3D embed decisions]]
- [[sessions/2026-07-09 GH component subcategory grouping|2026-07-09 GH component tool panel grouping — Graph / States / Actions]]
- [[sessions/2026-07-11 Session History panel with Restore points|2026-07-11 Session History panel + Restore points]]
- [[sessions/2026-07-11 Landing hero title shrink quick task|2026-07-11 Landing hero title shrink — Quick task 260711-gtz]]
- [[sessions/2026-07-11 v9.0-v10.0 global phase renumbering|2026-07-11 v9.0/v10.0 global phase renumbering + v8.0 consistency fix]]
- [[sessions/2026-07-11 v8.1 milestone init and phases 810-813|2026-07-11 v8.1 milestone init + phases 810–813 execution]]
- [[sessions/2026-07-11 Phase 814 Reasoner Screen execution + 815-816 progress|2026-07-11 Phase 814 Reasoner Screen + 815-816 progress]]
- [[sessions/2026-07-11 Phase 815 DG API Documentation execution|2026-07-11 Phase 815 DG API Documentation execution]]
- [[sessions/2026-07-11 Phase 816 Integration & Deployment execution|2026-07-11 Phase 816 Integration & Deployment execution]]
- [[sessions/2026-07-11 v8.2 milestone init — Connector Integration and Reasoning Engine|2026-07-11 v8.2 milestone init — Connector Integration & Reasoning Engine]]
- [[sessions/2026-07-11 Phase 820 execution — Reasoning-Stack Architecture Decision and OntoGraph Axiom Scoping|2026-07-11 Phase 820 execution — Reasoning-Stack Architecture Decision & OntoGraph Axiom Scoping]]
- [[sessions/2026-07-11 Phase 821 context discussion — dg-reasoner sidecar and RDF translation|2026-07-11 Phase 821 context discussion — dg-reasoner sidecar & RDF translation]]
- [[sessions/2026-07-12 Phase 822 UI-SPEC|2026-07-12 Phase 822 UI design contract — monochromatic verdict reconciliation]]
- [[sessions/2026-07-12 Phase 821 execution — dg-reasoner sidecar, code review, full verification|2026-07-12 Phase 821 execution — dg-reasoner sidecar, code review findings, full verification]]
- [[sessions/2026-07-12 Phase 822 planning — OWL 2 DL Reasoner Screen Wiring|2026-07-12 Phase 822 planning — OWL 2 DL Reasoner Screen Wiring, 4 plans across 3 waves]]
- [[sessions/2026-07-12 Phase 823 SHACL Validation Layer execution|2026-07-12 Phase 823 execution — SHACL Validation Layer, 6 plans across 4 waves]]
- [[sessions/2026-07-12 Phase 824 CONNECTOR Credential Integration execution|2026-07-12 Phase 824 execution — CONNECTOR platform-token heartbeat, 2 plans, code-complete, in-Rhino UAT deferred]]
- [[sessions/2026-07-12 Phase 29 UAT diagnosis and fix planning|2026-07-12 Phase 29 UAT diagnosis and fix planning — graph_query design-state schema mismatch root cause + 3 fix plans (29-06/29-07/29-08)]]
- [[sessions/2026-07-13 Phase 32.1 DG ID cross-platform identity planning|2026-07-13 Phase 32.1 planning — DG ID cross-platform identity, Perplexity SOTA research (Rhino.Inside.Revit/Speckle/IFC/BHoM), 7 plans across 3 waves, verified]]
- [[sessions/2026-07-18 Phase 32.1 Wave 1 execution|2026-07-18 Phase 32.1 Wave 1 — minting core, spec+ADR, identity API; golden vector confirmed]]
- [[sessions/2026-07-18 Phase 32.1 complete — all 7 plans executed|2026-07-18 Phase 32.1 COMPLETE — 7/7 plans, 290 C# + 15 Python tests, cross-language parity verified]]
- [[inbox/Model viewer needs rotation fix and validation management|Inbox items]]
- [[sessions/2026-07-19 Phase 36 Computgraph Persistence and Graph Layer Display|2026-07-19 Phase 36 — Computgraph Persistence & Graph Layer Display (autonomous execution, 4 plans, 12 commits, 15/15 verified)]]
- [[sessions/2026-07-25 Graph Viewer search bar adaptive value dropdown|2026-07-25 Graph Viewer search bar — adaptive value dropdown (quick 260723-tgi, new Combobox primitive, flex-shrink overlap fix)]]
- [[sessions/2026-07-26 v9.0 UAT Group 4 E2E spine — publish, idempotency, provenance|2026-07-26 v9.0 UAT Group 4 E2E spine — publish/idempotency/provenance verified on UrbanBlock, 3 new findings (F5/F6/F7)]]
- [[sessions/2026-07-26 Phase 35 SC1 remediation — planning and Wave 1 execution|2026-07-26 Phase 35 SC1 remediation — 12 plans authored, Wave 1 executed (7 commits): schemas, gateway controls, the prompt/few-shot fix, fixture repair, G12 gate]]
- [[sessions/2026-07-26 Phase 35 Wave 3 execution — two-tier orchestrator, Corpus B frozen, R4 defect found|2026-07-26 Phase 35 Wave 3 execution — 35-12 two-tier orchestrator (433 tests), Corpus B hand-annotated + frozen on live UrbanBlock_V7 (4 pull round-trips), Frame/Truss source recovered, R4 rule found unreachable on live data]]
- [[sessions/2026-08-31 T1 ITcon tone revision — rhetorical register neutralisation|2026-08-31 T1 ITcon tone revision — 99 edits neutralising evaluative language, clefts 12→1, promotional adjectives 7→0]]
- [[sessions/2026-08-31 T1 R14.3 — R14.4 package port, FBS mapping and C45|2026-08-31 T1 R14.3 — R14.4 S2 port (FBS↔Design State mapping) and C45 resolved on a corrected, non-linear model; R14.4's derivation rule rejected as unsound]]
- [[sessions/2026-08-31 T1 R14.3 — C55 repository reference and the ontology deposit|2026-08-31 T1 R14.3 — C55 resolved; citable deposit Erarchitech/design-grammar-ontology v1.0.1 created (Apache-2.0 + CC BY 4.0), Table 3 and Annex C recounted against it]]
- [[sessions/2026-09-07 T1 R15.2 — AU-R151-TOPO alignment-module architecture|2026-09-07 T1 R15.2 — `AU-R151-TOPO` at the gate: Topologic's published OWL ontology found, three alignment modules replace three extension modules, BOT subsumed, IFC via bSDD; 20 edits + Figure 2, joint apply planned]]
- [[sessions/2026-09-13 v11.0 V8 publication contract planning|2026-09-13 v11.0 — V8 publication contract milestone and phases 1101–1109 planned; early activation gates defined]]
- [[sessions/2026-09-14 T1 ITcon R15.4 — architecture and figures planning|2026-09-14 T1 ITcon R15.4 — architecture and figures planning]]
- [[sessions/2026-09-15 T1 ITcon R15.4 — H14 and architecture wording|2026-09-15 T1 ITcon R15.4 — H14 and architecture wording]]
- [[sessions/2026-09-19 T1 ITcon R15.6 title and keywords finalisation|2026-09-19 T1 R15.6 — title & keywords]]
- [[sessions/2026-09-19 Theory–implementation alignment audit and GSD planning|2026-09-19 Theory–Implementation Alignment audit + GSD sequencing]]
- [[sessions/2026-09-20 v9.0 override closeout and v12.0 activation|2026-09-20 v9.0 override closeout + v12.0 activation]]
- [[sessions/2026-09-28 Phase 1204 execution complete — determinism and LLM reproducibility benchmark|2026-09-28 Phase 1204 execution complete — 9/9 plans, D-08 gate genuinely failed (disclosed), live LLM sampling, gsd-verifier 12/12]]
- [[sessions/2026-09-30 Phase 1205 security and tenancy release gate complete|2026-09-30 Phase 1205 complete — 19/19 plans, server-side tenancy, grammar allowlist for LLM Cypher, multi-user gate-pass]]

### Archive
- [[archive/|DG_OBSIDIAN archive]] — stale notes for deleted/renamed v7.0 components (CLASSIFICATOR, VALIDATION RUNS, REINSTATE, v3.0-phase plans)

> ℹ️ **v7.0 milestone complete (2026-07-05).** 8 phases (13–20), 34 plans, 39 requirements satisfied. **v8.0 shipped (2026-07-07)**, Phase 27 (Speckle 3D embed) added post-ship 2026-07-08 — 7 phases (21–27), 28/28 requirements. **v8.1 complete (2026-07-11)** — 7 phases (810–816), 23 requirements, all 7 phases executed and verified; formal `/gsd-complete-milestone` archive still pending. **v8.2 initialized (2026-07-11)** — Connector Integration & Reasoning Engine, 5 phases (820–824), 7 requirements, ready to plan Phase 820. **v9.0 (Phases 28–40, paused)** — Phase 36 ✅ COMPLETE (2026-07-19). Phases 37 (context ready, needs plan) and 38–40 (need discuss). **v10.0 (Phases 41–49, isolated)** renumbered 2026-07-11 to continue global phase numbering.
