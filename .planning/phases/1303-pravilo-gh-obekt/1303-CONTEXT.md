# Phase 1303: Правило ↔ GH ↔ объект — Context (MVP slice: automated GH/Revit mapping)

**Gathered:** 2026-10-17
**Status:** Ready for planning — MVP slice only (demo 2026-10-19); full DGBN scope of 1303 stays TBD after the demo
**Source:** owner request via `/gsd-capture` (2026-10-17), owner answers in session, five read-only code investigations, research `docs/reviews/mapping-issue-investigation/Interactive Visual Mapping and Active-Learning UX for Design Grammars in Revit and Grasshopper.md`, todo `.planning/todos/pending/2026-10-17-deliver-automated-gh-and-revit-to-dg-mapping-mvp-by-19-10.md`

<domain>
## Phase Boundary (MVP slice)

The slice delivers, demo-grade, by 2026-10-19: elements from Grasshopper and from a read-only Revit model arrive in DG as descriptors; a deterministic mapping engine proposes multi-role DG class candidates from several evidence sources, groups elements, asks few consequence-framed questions per group, stores each answer as a decision and a learned profile, re-applies profiles deterministically (also across platforms), and turns applied roles into ObjStates for the existing VALIDATOR. The DG Web UI shows the queue, question card, progress and profiles; Rhino shows mapping state as preview colours. Requirements: DGMAP-01…06 (outside the 51 MVP IDs); partial progress on DGBN-03 and DGBN-05 only.

Not in the slice: DGBN-01 (GH still reads via Bolt), DGBN-02 exact rule-to-port binding with refusal semantics, DGBN-04 tag/mark commands, DGBN-06 reference `.gh` regression; any Revit write (colour overrides, parameters, selection writes — D-10, Phase 1306); a bSDD client; ML classifier training; conformal calibration; multi-user reconciliation; DG.gha component changes; DeGram (`apps/degram`) changes.
</domain>

<decisions>
## Implementation Decisions

### Isolation and process
- **D-01: Work only in the worktree branch.** Worktree `C:\Users\Admin\source\repos\dg-mapping`, branch `feature/mapping-mvp` from committed `535eb30`. No file change, stage or commit in the main folder or on `feature/hosting-dg-pilot`; Phase 1309 continues there in a parallel Hermes session. Untracked GSD tooling was copied into `.claude/` of the worktree and is never committed.
- **D-02: GSD stays in flat mode.** No GSD workstreams (`workstream.create` migrates ROADMAP/STATE/REQUIREMENTS/phases), no `/gsd-new-milestone`; numbering 1300–1307 is owner-fixed, so the slice lives in Phase 1303 (`1303-pravilo-gh-obekt`).
- **D-03: Merge after the demo.** The branch merges after 2026-10-19 and after a 1309 commit point; expected conflicts are limited to STATE.md, ROADMAP.md and REQUIREMENTS.md and are resolved by hand.
- **D-04: Entry-gate exception for the slice.** The slice starts without the 1302 exit and without an accepted 1300 profile; the 1303 entry gate remains mandatory for full phase acceptance.

### Scenario
- **D-05: GH + Revit live on hexagonal-facade.** Project `v12-hexagonal-facade-01`. A Revit model of the facade already exists, generated through Rhino.Inside.Revit: facade modules are Generic Model adaptive-point families, the frame is built in Grasshopper. The `.rvt` path is still to be supplied by the owner.
- **D-06: Gold labels from V1.** V1 = 376 elements: 100 HexagonalUnit, 25 GroundFloorUnit, 125 GlassPanel, 125 BottomTriangularPanel, 1 Facade (`3a-V1-summary.txt`). FacadeModule is a legitimate second role of the 100 HexagonalUnit geometries (A1).
- **D-07: Four demo acts.** (1) GH cold start feeding all 125 module outlines as one stream, reproducing F5 (`README.md:112`) and F12 (`:119`); (2) V2/V3 re-run, new geometry mapped by profiles; (3) live Revit read — all modules share the Generic Model category and a weak IFC class, so geometry and transferred profiles must separate them; (4) roles → OBJECT STATE → VALIDATOR, V1 11/11 PASS, contrasted with the documented mis-mapping.

### Confirmation and learning
- **D-08: Group answers are explicit confirmation.** A human answer to a group question (with rule consequences shown) is an explicit confirmation for every member; it supersedes, for this work, the per-binding rule of the 22.10 pilot plan.
- **D-09: Profiles are deterministic selectors.** MappingProfile = conjunction of feature predicates (platform optional, source/category/family/type, geometry kind, vertex or adaptive-point count, closure, z-band, parameter values) → set of class roles. Induced from the decided group by keeping features constant within the group and discriminative against other groups; instance-specific features (ids, coordinates) are excluded. Authored profiles (manual GH wiring, Revit category + parameters) are the same object with `source=authored`.
- **D-10: Confidence and auto-apply rule.** Profile confidence = (c + 4) / (c + r + 5) where c = confirmations and r = rejections (one human decision counts once, support records the element count). A profile auto-applies when confidence ≥ 0.8 and no rule-consistency conflict is present for the element; otherwise the element is queued. Defaults are configurable constants with tests.
- **D-11: Repeatable results.** The same descriptors and the same profile set must give the same groups, candidates, ordering and question text (no clock, random or LLM input on the deterministic path).

### Evidence and scoring
- **D-12: Evidence functions.** (a) profile match; (b) rule consistency — per-class constraints derived from the project's SWRL rules (class atom + datatype-property atom + builtin comparison + literal, e.g. HexagonalUnit/hasVertexCount = 6, GroundFloorUnit = 5, BottomTriangularPanel = 3; violation-pattern rules fire when the constraint is violated) give support when satisfied and a conflict flag when violated, never an automatic rejection; (c) geometry signature; (d) name tokens (GH output nickname or group name, Revit family/type name) against class labels and synonyms; (e) IFC entity / PredefinedType / IfcExportAs against per-class alignment hints held in engine configuration or authored profiles (no `:Class` schema change); (f) optional LLM vote.
- **D-13: Aggregation.** Weighted log-odds per (element, class); every class above the acceptance threshold becomes a candidate role (multi-label). An element is ambiguous when the top-two margin is below δ or any conflict flag is set. Classes declared `owl:disjointWith` (`ontology/dg-disjointness.ttl`, plus project-declared pairs) are never co-assigned and raise a question.

### Grouping and questions
- **D-14: Groups and queue order.** Group signature = (platform, source/category/family/type, geometry kind, vertex/point count, sorted top candidate set). A group with mixed decisions splits by the feature with the highest information gain. Queue order = uncertainty × log(1 + n) × (1 + number of rules affected).
- **D-15: Three question types.** assign (one clear candidate below auto threshold), disambiguate roles (two or more plausible candidates; options: X / Y / both roles / split by feature / none), mapping-or-design (a candidate supported by name or profile contradicts the class's rules: "as HexagonalUnit these 25 outlines violate R12 ×25, as GroundFloorUnit R11 passes — mapping error or design error?"). Each question shows the evidence, the rules each option brings into scope and three representative native ids.
- **D-16: LLM role.** The LLM may paraphrase or explain a question (gateway, paid calls allowed 17–19.10); the deterministic template text is canonical and always shown or available; the LLM never decides and never answers a question.

### Persistence and API
- **D-17: Graph model (experimental, Computgraph).** New labels `MappingSession`, `MappingDecision`, `MappingProfile` (project-scoped, `graph:'Computgraph'`); applied roles as `(:Representation {nativeId, platform, project})-[:MAPPED_AS {classIri, state, confidence, source, decisionId, profileId, at}]->(:Class)`. Documented as experimental in `spec/DATABASE.md`, `spec/LPG-OWL-MAPPING.md`; the full Schema Change Propagation list is completed in post-demo 1303 hardening unless a test enforces an item now.
- **D-18: Routes.** `POST /mapping/sessions` (descriptors → session with groups and queue), `GET /mapping/sessions/{id}`, `POST /mapping/sessions/{id}/decisions`, `GET /mapping/profiles?project=`, `POST /mapping/sessions/{id}/apply` (writes `MAPPED_AS`, returns per-element roles for GH/Revit consumers). Callable by a signed-in member with project access (Web UI) and by the Grasshopper connector session; `spec/SECURITY-BOUNDARY.md` and the route policy are updated with their machine-checked blocks; a new LLM call site is registered in `spec/REPRODUCIBILITY.md` if that contract requires it.

### Platforms and UI
- **D-19: GH side is a script component.** A Rhino 8 C# script component modelled on `test/v12-hexagonal-facade-01/gh-measure-rules.cs`, in a COPY of the facade definition (`v12-hexagonal-facade-01-mapping.gh` in the worktree test folder, gitignored); no DG.gha rebuild; it reuses the CONNECTOR session; preview colours via the standard Custom Preview; outputs per-element roles/state/colour and geometry partitioned by class for the existing OBJECT STATE components. The script source is tracked as `test/v12-hexagonal-facade-01/gh-mapping-intake.cs`.
- **D-20: Revit side is read-only.** Elements are read through the read-only revit-mcp loopback routes or through Rhino.Inside read components; an adapter turns them into descriptors (UniqueId, category, family, type, adaptive point count when available, parameters, IfcExportAs when present). No Revit writes.
- **D-21: Web UI Mapping panel.** A Mapping screen/panel in `ui-v2` for the active project: queue, question card with consequences, progress (confirmed / auto by profile / ambiguous / unmapped), profile list; RU and EN strings with the existing completeness test kept green.

### Runtime and delivery
- **D-22: Authorized runtime (17–19.10).** Docker on this PC — rebuild `data-service` and `design-grammars` from a clean `git archive` export of the branch HEAD, Neo4j data preserved; live Rhino/GH through RhinoCode on the copy; read-only Revit; paid LLM calls through the gateway.
- **D-23: Workers.** Implementation goes to DSH Flash workers when the hub is reachable; at 2026-10-17 the hub was unreachable (`hub_reachable: false`), so either the owner starts DSH Desktop from the Start menu or execution falls back to Claude subagents, reported to the owner. The controller verifies every result (diff, tests) before commit.

### Evaluation
- **D-24: Demo protocol.** For each act record questions asked, precision/recall per class against D-06 gold labels, auto-apply share and run time; evidence under `test/v12-hexagonal-facade-01/mapping-demo/`. Targets: act 1 = 2 questions (D-26), act 2 = 0 questions, act 3 first Revit read ≤ one question per family/type group and a second Revit read 0 questions, V1 precision/recall 100%. Revit targets are bounded by the real family names, which are not known until the owner opens the model.

### Refinements from the integration investigation (2026-10-17)
- **D-25: Rule conflict blocks auto-apply only with an alternative.** A violated class constraint blocks auto-apply only when another candidate class is rule-consistent for the element (mapping-or-design question); otherwise the violation is reported as a design signal on the element and the profile still applies (V2/V3/V4 variant failures stay design results, not questions).
- **D-26: One batch question for clear groups.** Groups with a single candidate at confidence ≥ 0.8 and no blocking conflict are offered together in one `batch-assign` question; the answer may exclude groups. Expected V1 cold start: 2 questions (batch + the 25 pentagons).
- **D-27: Revit read path and evidence.** Read-only revit-mcp loopback routes at `http://127.0.0.1:48884/revit_mcp/`: the owner selects the facade elements in Revit, `selection_snapshot` (≤ 1000 elements, identity-pinned) plus `element_properties` per element for the family name. No route lists all elements or returns adaptive-point counts, so Revit evidence = family/type name tokens, parameters, IFC export parameter when present, and population match against the latest confirmed GH session of the project.
- **D-28: Connector session for the GH script.** The facade `.gh` still carries the pre-1308 CONNECTOR and a retired `dgc_` token; the copy gets a post-1308 CONNECTOR signed in by the owner (Username/Password, non-persistent). The script sends `Authorization: Bearer <CONNECTOR.Session>` (`dgk_`), wired directly, never through a Panel.
- **D-29: Web UI placement.** A Mapping panel inside ProjectsScreen for the active project; data loads only when the panel is opened (exact-request browser tests); strings go into the existing `src/i18n/dict/screens.js`; no new landing anchor or region.
- **D-30: Rebuild procedure.** As in Phase 1308 rollout: `git archive` of the branch HEAD (`data-service`, `ui-v2`) into a new empty folder, `docker build --no-cache` with tags `design-grammar-system-data-service` / `design-grammar-system-design-grammars`, then `docker compose up -d --no-build --no-deps data-service design-grammars` under compose project `design-grammar-system` (compose file and env of the main checkout used read-only, after comparing it with the branch version); probes as in `1308-ROLLOUT.md`.
- **D-31: API contract.** `1303-API-CONTRACT.md` fixes descriptor, session, question, decision, profile and apply shapes for all plans.
- **D-32: Persistence narrowed for the MVP (supersedes the graph model of D-17 and the apply write of D-18).** No `Representation`/`MAPPED_AS` writes in the slice: synthetic GH ids would violate the Representation nativeIdKind set (`InstanceGuid`/`UniqueId`/`GlobalId`/`ApplicationId`), and hundreds of nodes per apply would crowd the 2000-node `GET /graph/{project}` listing. The slice persists `MappingSession` (summary + compact result JSON), `MappingDecision`, `MappingProfile` and the edges `(:MappingSession)-[:HAS_DECISION]->(:MappingDecision)-[:CREATED_PROFILE]->(:MappingProfile)-[:ASSIGNS_ROLE]->(:Class)`, all project-scoped with `graph:'Computgraph'`; the three labels join `LOCKED_NODE_LABELS`. Element-level bindings live in the session result and in the apply response. `Representation`/`MAPPED_AS` move to post-demo 1303 hardening with DG-native GH InstanceGuid identity.

### Claude's Discretion
- Exact feature names, weights, δ and acceptance thresholds, as long as they are constants with tests.
- Module layout inside `data-service/` and component structure inside `ui-v2/`.
- Colour palette for mapping states, consistent between Web UI and Rhino.
</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Owner intent and research
- `.planning/todos/pending/2026-10-17-deliver-automated-gh-and-revit-to-dg-mapping-mvp-by-19-10.md` — owner request, findings, decisions
- `docs/reviews/mapping-issue-investigation/Interactive Visual Mapping and Active-Learning UX for Design Grammars in Revit and Grasshopper.md` — UX and active-learning research
- `.planning/REQUIREMENTS.md` — DGMAP-01…06, DGBN-03/05
- `.planning/milestones/v14.0-REQUIREMENTS.md` lines 45-47 — NMOD-01/02 (candidate signals, BindingProfile) — concepts only, no ownership transfer
- `DG_OBSIDIAN/knowledge/decisions/Alignment modules over extension modules in the DG ontology.md` — IFC referenced through bSDD, `skos:closeMatch`

### Grasshopper path
- `DG/src/DG.Grasshopper/Components/ObjectStateComponent.cs` — Object/Geometry/Label inputs, ObjectRef order (lines 49-68, 137-145, 201-211)
- `DG/src/DG.Core/Services/DesignStateBindingService.cs` — exact ClassIri binding (lines 43-92)
- `DG/src/DG.Core/Parsing/CanvasAnnotationParser.cs` — Computgraph Object without classIri (lines 130-134)
- `test/v12-hexagonal-facade-01/gh-measure-rules.cs`, `5-wiring.md`, `3a-V1-summary.txt`, `README.md`, `RULES.md`, `rules-approved.json` — facade definition, outputs, rules, failures F5/F12

### Revit path
- `C:\Users\Admin\source\repos\design-grammar-system\apps\revit-mcp\revit_mcp\documents.py` lines 173-199 — `get_selection_snapshot` (submodule checked out in the main folder only; read-only)
- `C:\Users\Admin\source\repos\design-grammar-system\apps\revit-mcp\revit_mcp\degram_readonly.py` lines 24-46 — read-only allowlist
- `.planning/phases/1301-rabochiy-klient-i-bezopasnoe-chtenie/1301-CONTEXT.md` — D-09..D-15 (fork, no write routes, document pinning, snapshot shape)

### Server and contracts
- `data-service/dg_identity.py` lines 107-108, 335-354 — Representation platform/nativeIdKind, bind MERGE
- `data-service/computgraph_publish.py` lines 565-603 — Object publish
- `spec/DG-ID.md` — binding model (native ids are bindings, not identity)
- `spec/SECURITY-BOUNDARY.md`, `spec/REPRODUCIBILITY.md`, `spec/DATABASE.md`, `spec/LPG-OWL-MAPPING.md` — contracts to update for new routes, LLM call site and labels
- `ontology/dg-disjointness.ttl` — Door ⊥ Window, Wall ⊥ Slab
</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- OBJECT STATE / DESIGN STATE / VALIDATOR chain: applied roles become ObjStates (one per role; StateId already depends on objectRef + classIri, so two roles of one element give two states).
- `/identity/bind` and `Representation` MERGE in `dg_identity.py`: identity of native elements per platform.
- Recognition preview pattern (`/computgraph/recognize`, `[?] name (NN%)` groups, STRUCTURE CONFIRM accept): precedent for proposals with confidence, but it excludes Object/Class kinds and persists no rejects.
- Phase 38 candidate accept (`cg_paramstate_store.py`): provenance fields to imitate (source, provider, model, confidence, determinabilityClass).
- `gh-measure-rules.cs`: working Rhino 8 C# script component in the same definition.
- revit-mcp `get_selection_snapshot`: uniqueId, elementId, category, typeName, parameters with units.

### Gaps the slice fills
- No mapping state, confidence, provenance, decision log or learning loop anywhere; no Revit mapping definition; no IFC field on `:Class`; no Rhino preview colouring in DG components.

### Integration Points
- data-service routes + route policy + SECURITY-BOUNDARY blocks; Neo4j project-scoped Cypher; LLM gateway for optional paraphrase.
- ui-v2 screen/sidebar, API client, i18n catalogs.
- GH script component in the facade copy; Revit loopback read or Rhino.Inside read.
</code_context>

<specifics>
## Specific Ideas

- Question card example (approved preview): group of 25 outlines from HU, 5 vertices, closed, z ≈ 0; candidates HexagonalUnit (output name) vs GroundFloorUnit (geometry); "as HexagonalUnit → R12 violated ×25; as GroundFloorUnit → R11 passes, R10 applies"; options GroundFloorUnit / HexagonalUnit — design error / both roles / split by feature; the answer creates profile `gh · HU · vertexCount=5 → GroundFloorUnit` with author, date, support 25.
- The owner's ambiguity example (an element that is both window and wall) maps here to GlassPanel exported as IfcWindow in some cases and IfcPlate in others, and to HexagonalUnit + FacadeModule as legitimate multi-role.
</specifics>

<deferred>
## Deferred Ideas

- Revit colour overrides / view filters / legends and writing `DG_MappingState` parameters (Revit write, Phase 1306 allowlist).
- bSDD lookup client and IFC/bSDD alignment fields on `:Class` (ontology module rebuild per the alignment decision).
- Label model over evidence sources (Snorkel-style source-accuracy estimation), conformal calibration of thresholds, ML classifiers on geometry.
- Collaborative sessions and reconciliation of conflicting decisions between users.
- Native DG.gha components replacing the script component; DGBN-01 HTTP-only addin path; DGBN-02/04/06.
- Full Schema Change Propagation list for the new labels (cypher_template, dataset_schema, n8n prompts, shapes, copilot-instructions, README).
</deferred>

## Owner amendment 2026-10-18 (supersedes D-19)

- **D-33: Mapping is proposed automatically; no mapping component.** A hand-built script component whose inputs are wired to one definition's streams is not automatic mapping. CONNECTOR (already on every DG canvas, holding the `dgk_` session) reads the open definition after sign-in and after every settled change (1.5 s debounce), sends a new session only when the canvas content fingerprint changed, colours elements in Rhino by mapping state (plugin display conduit, no Custom Preview), follows the answers given in the Web UI and applies the session when no question is left. New input `AutoMap` (default true); new outputs `Mapping`, `ByClass`, `ClassNames`, `ClassObjects`, `Sliders`. Built into DG.gha (owner choice "встроить в DG.gha сейчас"); the prototype script stays only as a fallback.
- **D-34: Element streams come from the canvas itself.** Geometry sources wired into DG components (OBJECT STATE etc.) are the streams; a definition without DG wiring falls back to visible terminal geometry. One element per branch (multi-branch data) or per item (single list).
- **D-35: Canvas text is mapping evidence.** Group names (nested groups included), scribble text (same group or within 250 canvas units), component names and nicknames, and the class an OBJECT STATE already names travel as `names` and count as word evidence (no acronyms from them). A small bilingual lexicon (Russian stems → English concept words) lets «Ширина соты», «панели» meet `hasWidthM`, `GlassPanel`.
- **D-36: Named sliders are proposed as DG datatype properties.** Sliders with a non-default nickname are sent as `parameters` (name, canvas text, value, domain). The engine scores them against the project's datatype properties (own name ×2, canvas text ×1, generic words such as "count" ×0.5), groups sliders by name stem (`Module Width F1…F5` → one question), asks `map-parameter` questions (property options + "Not a DG property") and learns parameter profiles (selector `{kind: parameter, nameStem}`), so a later definition is mapped automatically. Deterministic; an LLM semantic vote stays out of the slice.

## Owner clarification 2026-10-18, second (supersedes the slider half of D-36)

- **D-37: DG ontology roles on the canvas; the LLM proposes, a human confirms.** A number slider is a DG **Parameter** (PARAMETER STATE input, ParameterId = slider name), not a datatype property. A datatype **Property** value comes from the output of a calculation component (Area, a measure script); it is matched to a property by value agreement with the plugin's own geometry features (strong; weak for constant columns), the output name as the property's acronym or words, the canvas text, and the LLM. Element streams → classes keep the deterministic evidence plus the LLM vote, and a calculation output votes for its stream's class (its property → the classes whose rules use it; H on «bbox F» → hasTotalHeightM → Facade). A stream that duplicates another or is the union of two or more others (compared by element bounding boxes: «All panels», module surfaces over the 6-/5-module contours) is skipped when the canvas is read. Where one output agrees equally with several streams (a script reading Panels A and B, all zeros), the rule's class picks the stream when the rule is bound. One LLM proposal per session through the gateway (temperature 0), only when the deterministic pass leaves questions; it is validated against the digest, recorded in the session and reused for every recompute (call site `mapping_llm.py|propose_mapping`, spec/REPRODUCIBILITY.md). Questions: element groups, `batch-measures` / `map-measure`, `batch-parameters`. Automatic mapping is tested on a definition **without** DG states (`v12-hexagonal-facade-01-auto-mapping.gh`: DG states, VALIDATION GRAPH, REINSTATE, LISTENER and the 17 index List Items removed; Join Curves, Bounding Box and the measure script kept as model geometry and calculation).
- **D-38: After agreement CONNECTOR places the DG components; classes and rules are bound by identity.** On a definition without DG states, once the session is applied CONNECTOR places (one undo-free group «DG · автоматический меппинг (CONNECTOR)»): GRAPH DECONSTRUCT → METAGRAPH; one OBJECT STATE per class and measured stream (per class when none of its rules is measured; a PROPERTY STATE pairs one output with the elements of one stream, so a class's unmeasured streams are left out with a note) with Object = persistent text `class:<IRI>` and Geometry ← the stream (flattened); one RULE BY ID (new component, picks by Rule_Id) + PROPERTY STATE per rule binding (DataProperty = property IRI, PropValue ← the calculation output, ObjState ← the class's OBJECT STATE); PARAMETER STATE with one input per DG parameter; DESIGN STATE; VALIDATOR (SendValid = false, Token ← CONNECTOR.Session). No List Item index is placed anywhere, which closes the index-picker failure (classes added to the ontology shifted METAGRAPH Objects + List Item and put wrong classes into OBJECT STATE). OBJECT STATE accepts `class:<IRI>` text as a class.

---

*Phase: 1303-pravilo-gh-obekt (MVP slice)*
*Context gathered: 2026-10-17; amended 2026-10-18 (D-33..D-36, D-37..D-38)*
