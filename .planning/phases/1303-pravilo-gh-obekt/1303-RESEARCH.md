# Phase 1303: Правило ↔ GH ↔ объект — Research (plan 1303-16, decision D-54 ONLY)

> **Scope note.** This research covers **plan 1303-16 (D-54: a generated property calculator joins the shared catalogue only after the operator confirms its result on a model) only**. It is not research for the whole phase. Plans 1303-01..15 are the baseline and are not re-researched.

**Researched:** 2026-10-20
**Worktree / branch:** `C:\Users\Admin\source\repos\dg-mapping`, `feature/mapping-mvp` (HEAD `ae32f23`)
**Domain:** data-service Python (Neo4j, FastAPI route policy), ui-v2 React panel, DeGram component tool (separate repo `D:\dgb\src`)
**Confidence:** HIGH for current-code facts (read at file:line); MEDIUM for the run-sample data path (objectRef shape not yet seen live); the design recommendations are mine and marked as such.

Labels: `[VERIFIED: file:line]` = read in this session; `[VERIFIED: ran]` = command executed in this session; `[CITED: x]` = taken from a named document; `[ASSUMED]` = not verified, needs confirmation.

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions (verbatim, D-54; `1303-CONTEXT.md:211-221`)

- **D-54: A generated calculator joins the shared catalogue only after the operator confirms its result on a model.**
  - Problem: the vetted catalogue (`data-service/property_calculators/catalogue.json` + `*.py.tmpl`) is static and grows only by hand. A calculator the LLM writes for an uncovered property is checked for safety (AST contract), not for correctness, and stays in one project (`PropertyCalculator`, `origin: generated`). The ingest vocabulary knows only catalogue properties, so the LLM invents names for new concepts (`hasMinHostOpeningClearanceMm`).
  - Decision: promotion after confirmation.
    1. After a run, the operator sees for a generated calculator its source, the values it produced on sample boxes and the rule verdicts; they confirm or reject it (Web UI, DeGram tool).
    2. A confirmed calculator moves to a shared catalogue stored in Neo4j (not the file): source, sha256, property name, unit, the Revit categories it reads, provenance (project, run id, confirmedBy/At).
    3. Its property joins the ingest vocabulary (`SWRL_CONVENTIONS.computable_form.computable_properties`), so later rules and projects reuse it by name without the LLM.
    4. A rejected calculator is retired (`status: rejected`) and the property is regenerated or marked unsupported.
    5. The file catalogue stays the vetted seed; the Neo4j catalogue extends it. Resolution order: file catalogue, shared catalogue, project-stored, LLM generation.
  - Not yet built. To be planned and executed in the next session (todo `2026-10-20-promote-confirmed-generated-calculators-to-catalogue.md`).

Other locked constraints from the same CONTEXT that bind plan 16 (excerpted; `1303-CONTEXT.md` line in brackets):
- D-01 [19]: work only in the worktree branch `feature/mapping-mvp`; no change in the main folder or on `feature/hosting-dg-pilot`.
- D-30 / D-53 [66, 206-209]: rollout by `git archive` of the branch HEAD → `docker build --no-cache` → `docker compose -p design-grammar-system ... up -d --no-build --no-deps data-service design-grammars`; rollback tags kept; "DG.gha is not touched by this work". **The design below needs no DG.gha change.**
- D-41 [164]: the DeGram delegated principal acts for its bound project with the user's stored role; D-43 / D-46 [166, 174]: DeGram changes are committed in the build clone `D:\dgb\src` on `feature/mapping-mvp`, no push, no gitlink bump, no `hermes update`, no write to the installed Hermes profile, unsigned local build launched with a scrubbed environment.
- D-11 [33]: repeatable results — no clock/random/LLM input on the deterministic path.

### Claude's Discretion
- Exact feature names, weights, thresholds as constants with tests; module layout inside `data-service/` and component structure inside `ui-v2/`; colour palette (CONTEXT `### Claude's Discretion`, lines 70-73). For plan 16: node/route names, storage layout, the sample-size cap and the UI layout are mine to recommend.

### Deferred Ideas (OUT OF SCOPE)
- Colour/view filters/legends in Revit; LLM vote for Revit family groups; Revit auto sessions on `DocumentChanged`; separate GitHub repo for the connector; fate of `apps/revit-mcp`; bSDD client; label models/conformal calibration/ML; collaborative sessions; native DG.gha components replacing script components; DGBN-01/02/04/06; **the full Schema Change Propagation list for the new mapping labels** (CONTEXT `<deferred>` 136-145).
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| (none owns D-54) | `REQUIREMENTS.md:130-133` defines DGOPN-01..04 only. DGOPN-02 says "каталог проверенных калькуляторов ... выбор и параметризация по DataProperty правил" and describes generation and placing, not human confirmation or promotion. DGMAP-01..06 and DGBN-01..06 are unrelated. | **No existing ID covers D-54.** See Open Question 1: owner decides between amending DGOPN-02 and adding a new ID (e.g. DGOPN-05). I do not invent one. |
</phase_requirements>

## Summary

Today the calculator resolution is a pure function, `property_scripts.resolve(rules, catalogue, chooser, stored, generator)` [VERIFIED: data-service/property_scripts.py:211-272]. Order inside it: file catalogue (alias, vocabulary near-match, optional chooser) → project-stored `PropertyCalculator` → LLM generator. A generated calculator is validated by the AST contract `property_calculator_llm.validate_function` and persisted per project as `(:PropertyCalculator {project, dataPropertyIri, origin:'generated', source, sha256, function, status})` [VERIFIED: property_calculator_store.py:24-33, 100-115]. Nothing marks it as reviewed, nothing carries its unit or explanation, and nothing shares it. The ingest vocabulary is a **module-level constant** built once at import from `catalogue.json` [VERIFIED: dg_knowledge.py:123-134] and is JSON-stringified whole into the n8n ingest prompt [VERIFIED: n8n/workflows/rules-to-metagraph.json, node "Build LLM Prompt": `swrl_conventions: context.swrl_conventions`], so a dynamic extension merged inside `dg_context.assemble_context` reaches the LLM with **no n8n change and no workflow re-publish**.

D-54 therefore needs five small, separable pieces: (1) a review state on the project calculator plus a candidates read that shows source, sample values and verdicts; (2) a confirm gate that writes a global `(:CatalogueCalculator)`; (3) a new `shared` input to `resolve()` between the file catalogue and `stored`; (4) a deterministic merge of active catalogue entries into `computable_properties` in `assemble_context`; (5) reject/retire with no regeneration loop. UI is a new block in `PropertyCheckCard` (MappingPanel.jsx:943-1030). DeGram needs a component change **only** if the operator must confirm from DeGram; the data-service routes are enough for everything else. I recommend that the agent tool gets read-only access and the confirm/reject click stays human (Open Question 3).

Three **pre-existing defects** found while reading must be fixed inside plan 16 because promotion makes them load-bearing: (a) `tools/de01/tests/test_reproducibility_scope_drift.py` fails now — plan 15 added an LLM call site `property_calculator_llm.py|generate_calculator` that is not in the machine-checked block of `spec/REPRODUCIBILITY.md` [VERIFIED: ran]; (b) the generic graph-edit route lets an editor change `PropertyCalculator.source` (the label is not in `LOCKED_NODE_LABELS`) and nothing re-checks `sha256` at resolve time [VERIFIED: app.py:5629-5636, property_scripts.py:194-208]; (c) `property_calculator_store.save` always sets `status='active'`, so a rejected calculator is silently revived by the next regeneration [VERIFIED: property_calculator_store.py:28].

**Primary recommendation:** add a global `(:CatalogueCalculator)` (own `graph` value registered in `CLAIM_UNTAGGED_SHARED_GRAPHS`, **no `project` property**, provenance in `sourceProject`), a `shared` argument to `resolve()` loaded by a new store function and integrity-checked (sha256 + AST re-run) at resolve time, a deterministic vocabulary merge in `assemble_context`, four routes (`GET candidates`, `POST confirm`, `POST reject`, `POST retire`) with their route-policy/SECURITY-BOUNDARY/inventory rows, and a review block in `PropertyCheckCard`. Take per-box sample values from the published run's `statePayloadJson.propStates`, not from a DG.gha change.

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| Calculator resolution order, integrity check | API / Backend (`property_scripts.py`) | Database (store loads) | Pure function, takes `stored` and `shared` dicts; no Neo4j inside `resolve()` [VERIFIED: property_scripts.py:211] |
| Review state, confirm/reject/retire, idempotency | API / Backend (new store functions, `execute_write`) | Database / Storage | Same pattern as `mapping_store.lock_session` + apply idempotency [VERIFIED: mapping_store.py:938-943, 979-1026] |
| Shared catalogue persistence | Database / Storage (Neo4j, global node) | — | D-54 point 2 |
| Ingest vocabulary | API / Backend (`dg_context.assemble_context`) | n8n (passes it through unchanged) | Only place with a session; n8n stringifies the dict [VERIFIED] |
| Sample values and verdicts for the confirm screen | API / Backend (reads `ValidationRun`, `ValidationEntity`) | Database | Persisted run data; avoids a canvas round trip and a DG.gha change |
| Confirm/reject UI | Browser / Client (`ui-v2` MappingPanel) | — | Plan-10 card pattern |
| Agent-side listing (and confirm, if allowed) | DeGram component (`D:\dgb\src`, separate repo) | API / Backend | `degram_property_check` lives in the component and only relays to DG routes with the delegated token [VERIFIED: D:\dgb\src degram_variant/dg_client.py:186-203] |
| Calculator execution | Revit/Rhino.Inside via GH script | — | Unchanged; promoted source is embedded by `assemble` exactly like a stored one |

## Standard Stack

No new packages. Everything is stdlib / already pinned in the repo.

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| Python | 3.14.2 on host [VERIFIED: ran `python --version`] | data-service | existing |
| FastAPI + pydantic + neo4j driver | as in `data-service/requirements.txt` [ASSUMED: not re-read; versions untouched] | routes, models, Cypher | existing |
| `ast`, `hashlib`, `json` (stdlib) | — | AST contract re-run, sha256, payload parse | already used by `property_calculator_llm.py` |
| React 18 + Vite 5 | `ui-v2/package.json` [VERIFIED: ui-v2/package.json] | Mapping panel block | existing |
| node:test | node v20.20.0 [VERIFIED: ran] | UI helper tests | existing (`npm --prefix ui-v2 test`) |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| Global `CatalogueCalculator` node | Extend `catalogue.json` by a git commit | Static; this is exactly the problem D-54 solves. Rejected by D-54 point 2. |
| Sample values from `statePayloadJson.propStates` | Add per-box sample lines to the calculator `Report` (template change) | Needs no run publish, but changes every assembled calculator sha256 (re-place chain), and the report is not persisted. Use only as fallback if objectRef cannot be mapped (Pitfall 9). |
| Review fields as properties on `PropertyCalculator` | A new `PropertyCalculatorReview` label | Extra label = extra schema/LOCKED/spec surface for little gain. Use properties. |

**Installation:** none. **Package Legitimacy Audit:** no external packages are added by this plan; the audit is not applicable. (`gsd-tools query package-legitimacy` not run: nothing to check.)

## Architecture Patterns

### System Architecture Diagram

```
 Web UI Mapping panel ──(editor cookie+CSRF)──┐        DeGram Desktop / agent (delegated dgd_)
 PropertyCheckCard: "Review generated         │                      │ (component repo; optional)
 calculators"                                 ▼                      ▼
                                   GET  /scripts/property-calculators/candidates?project&runId
                                   POST /scripts/property-calculators/confirm | reject | retire
                                                  │
              ┌───────────────────────────────────┼──────────────────────────────────────┐
              ▼                                   ▼                                      ▼
   project PropertyCalculator            ValidationRun (statePayloadJson.propStates)   CatalogueCalculator (GLOBAL,
   (origin generated, sha256, review*)   ValidationEntity (ruleId,status per box)      graph 'CalculatorCatalogue',
              │                                   │                                    no `project` prop)
              │   confirm gate: editor of project · runId is a published run of THIS project containing the
              │   property · sha256 == project calc sha256 · validate_function(source) re-run · unique active
              │   (company, propertyKey) else 409 · single execute_write, MERGE on sha256 → idempotent
              ▼
   resolve(rules, file_catalogue, chooser, stored, shared, generator)
      1 file catalogue (alias, vocab near-match, chooser)
      2 shared  ── integrity: sha256(source)==sha256 field AND validate_function ── fail → skip + warning
      3 project-stored (review != rejected)
      4 LLM generator (only if property not in rejected set; regenerate is explicit)
              │
              ▼
   assemble() → GH calculator script (unchanged; origin 'generated' binding shape reused)

 Ingest vocabulary:  n8n "Build LLM Prompt" ──► POST /context/assemble ──► dg_context.assemble_context
                      computable_form.computable_properties = file vocabulary + ACTIVE CatalogueCalculator rows
                      (deep copy, ORDER BY propertyKey, sha256; never mutates the module constant)
```

### Recommended file layout
```
data-service/
├── property_calculator_store.py   # + load_catalogue(), review/confirm/reject/retire writes, review fields in LOAD/SAVE
├── property_scripts.py            # + `shared` param in resolve(); + _from_shared(); generate()/ensure_rule_classes() load it
├── property_calculator_llm.py     # + validate_function(source, name=...) so stored calc_gen_<hex> can be re-validated
├── property_calculator_review.py  # NEW (optional): candidates assembly (samples, stats, verdicts) – pure functions
├── dg_context.py                  # assemble_context: merge dynamic vocabulary
├── app.py                         # 4 routes; CLAIM_UNTAGGED_SHARED_GRAPHS; LOCKED_NODE_LABELS
├── route_policy.py                # 4 rows
└── tests/ (test_property_scripts.py, test_property_calculator_review.py NEW, test_dg_context.py, ...)
ui-v2/src/lib/mappingApi.js · ui-v2/src/screens/MappingPanel.jsx · ui-v2/src/i18n/dict/screens.js · ui-v2/tests/mapping-api.test.mjs
spec/DATABASE.md · spec/LPG-OWL-MAPPING.md · spec/SECURITY-BOUNDARY.md · spec/REPRODUCIBILITY.md
```

### Answers to the eleven questions

**Q1. Current resolution.** [VERIFIED: property_scripts.py]
- `resolve(rules, catalogue, chooser=None, stored=None, generator=None) -> {"boxClass", "resolved", "unsupported"}` (211-272). It requires exactly one box class (BOX_CLASS_AMBIGUOUS). Per rule, per body DataProperty sorted by iri:
  1. `fresh` cache per iri (231-236).
  2. `resolve_property(dp, catalogue, chooser)` (116-155): alias regex on the IRI **local name lower-cased** (the label may be a description), then `class_duplicates.property_reason(raw_name, vocab_entry)` against `catalogue["vocabulary"]` → `resolvedBy: "vocabulary-near-match"`, then the optional chooser. A hit becomes `{origin:"catalogue", new: not same-as-stored}`.
  3. `stored[dp["iri"]]` through `_from_stored` (194-208). A generated record needs `source` and `function`; **it is not integrity-checked** (no sha256 recompute, no AST re-run).
  4. `generator(dp, rules_for_dp, box_label)` (247-259): on `status == "ok"` the binding is `{calculator: "generated:<sha256[:10]>", params: {}, resolvedBy: "llm", origin: "generated", function, source, sha256, provider, model, explanation, new: True}`. **`unit` from the LLM answer is dropped here** (251-254); `explanation` is kept in the binding but not persisted.
  5. else `unsupported` with reason `"no catalogue calculator"` or `"generation <status>: <error>"`.
- Order is decided at lines 236-259 of `resolve`; the file catalogue **wins over a stored generated calculator** (comment 233-235; test `test_wording_variant_binds_to_the_vetted_calculator_and_replaces_a_generated_one`).
- Callers: `generate()` (444-481: `load_active` → `resolve` → `context_classes` → optional `store`) and `ensure_rule_classes()` (403-441, runs after every ingest in a daemon thread, app.py:3820-3838). Both call `property_calculator_store.load_active(session, project)` and pass `stored=`.
- `read_categories` (161-174) and `context_classes` (177-186) already handle `origin == "generated"` by AST (`categories_in`), so a shared binding with the generated shape needs no change there.

**Q2. LLM + store; what a confirm screen can show.**
- `property_calculator_llm.generate_calculator(data_property, rules, class_label, complete=None)` never raises; returns `{status: ok|invalid|unavailable, function, source, unit, explanation, provider, model, promptSha256}` (157-193). `finalize(source)` validates, then renames `calc_gen` → `calc_gen_<sha256(normalized)[:10]>` (125-130). `validate_function(source)` requires exactly one function **named `calc_gen`** (line 78: `body[0].name != FUNCTION_NAME`), so **a stored source (already renamed) fails `validate_function` as is** (Pitfall 4). `categories_in(source)` extracts `OST_*` constants by AST (114-122). Contract: no imports, no `With/Delete/...` nodes, no attributes in `FORBIDDEN_ATTRIBUTES`, no dunders, allowed globals only (26-41).
- Store node `(:PropertyCalculator {graph:'Computgraph', project, dataPropertyIri, calculator, origin, paramsJson, function, source, sha256, provider, model, createdAt, createdBy, status:'active'})`; merge key `(project, dataPropertyIri)`; `COMPUTED_BY` from the project `DatatypeProperty`; `READS_CLASS` to context classes (store 16-33, 38-46). `LOAD_QUERY` returns only `coalesce(status,'active') = 'active'` rows, keyed by `dataPropertyIri` (91-97). `SAVE_QUERY` sets `status = 'active'` on every save (line 28). `unit`, `explanation` and any review state are **not persisted** today.
- What exists for a confirm screen:
  | Datum | Where | Persisted? |
  |---|---|---|
  | Source, sha256, function, provider, model, createdBy/At | `PropertyCalculator` | yes |
  | min/max/n per property, errors, inventory | calculator script `Report` → LISTENER `calculatorReport` (calculator_shell.py.tmpl, last block; CanvasListenerComponent.cs:792) | no, live canvas only; **no per-box values** |
  | violating boxes `"name [id]: ruleIds"` | highlighter `Violations` → `violations` (CanvasListenerComponent.cs:800) | no |
  | per-rule/per-box booleans | VALIDATOR `ValidStatus` (cs:795), `ruleNames`, `validationRunId` (cs:797) | the run is persisted if `send` was true |
  | **per-box value of the property** | PROPERTY STATE = one PropState per (rule, property, value) with optional `ObjectRef` (PropertyStateComponent.cs:10-23, 67-68); lands in `ValidationRun.statePayloadJson` → `propStates[] {stateId, ruleIri, dataPropertyIri, objectRef, propValue{value,type,displayName}}` (design_state_projection.py:176-195) | **yes, when the run was published** (`send` defaults to true, app.py:2136) |
  | per-(rule, box) verdict | `ValidationEntity {runId, dgEntityId, ruleId, status}` (app.py:5693-5696) and the evidence envelope rows (EvidenceEnvelope.cs:80-102: no observed value) | yes |
  | run lookup | `get_validation_run(project, run_id=None)` returns the latest run when `run_id` is None (app.py:898-924); run ids also come back in `property_check_summary(...).validationRunIds` (app.py:2175, 2188) | yes |
  
  So the confirm screen can be built **entirely server-side from persisted data**: `candidates` = project generated calculators with review pending, joined with (a) `propStates` filtered by `dataPropertyIri` (sorted by objectRef, first N plus min/max/n over all), (b) `ValidationEntity` counts per rule status for the rules that use the property. The exact content of `objectRef` is `[ASSUMED]` (see Pitfall 9) and must be checked on the first live run.

**Q3. Ingest vocabulary.**
- Static module constant: `SWRL_CONVENTIONS["computable_form"]["computable_properties"] = _computable_vocabulary()` reads `catalogue.json["vocabulary"]` **once at import** (dg_knowledge.py:123-134). `swrl_conventions()` returns **the shared dict itself** (137-139) and `tests/test_dg_knowledge.py:50-52` asserts `is SWRL_CONVENTIONS`.
- Consumers: `dg_context.assemble_context` puts it in `context["swrl_conventions"]` (dg_context.py:491); n8n "Build LLM Prompt" does `JSON.stringify({ontograph, metagraph, swrl_conventions, selected_cypher_shapes})` [VERIFIED]. No other code reads `computable_properties` (grep over data-service). The LLM therefore sees whatever `assemble_context` returns.
- Merge point: inside `assemble_context` (it already has `session` for `fetch_existing_entities`, 342-359). Recommended: `conv = copy.deepcopy(dg_knowledge.swrl_conventions())`; set `conv["computable_form"]["computable_properties"] = file_vocab + shared_rows`, where `shared_rows` = active `CatalogueCalculator` of the project's company as `{"property","meaning","unit"}`, ordered by `propertyKey, sha256` (CTXA-05 byte determinism: `tests/test_dg_context.py` `TestDeterminism`). **Never mutate the module constant.** No cache: one tiny indexed read per assemble; a cache would need invalidation on confirm/retire.
- `meaning` goes into an LLM prompt. If it came from the LLM `explanation` it is an LLM-output-to-LLM-input channel (Pitfall 8): store an operator-confirmed `meaning` (≤160 chars, control chars stripped) captured at confirm time.
- Scope: global vs company vs project is an owner decision (Open Question 2). Only **confirmed, active** entries enter the vocabulary; an unconfirmed project calculator must not.

**Q4. Routes, policy, SECURITY-BOUNDARY.**
- Existing: `POST /scripts/property-calculator` (viewer), `/place` (editor), `GET /scripts/property-calculators` (viewer, query), `POST /scripts/property-check/run` (editor), `/status` (viewer), `POST /scripts/rule-classes` (editor) — all `_p(_MEM, _DEL, source=..., role=...)` [VERIFIED: route_policy.py:231-239]. Handlers: app.py:2071-2204, 3845-3851. `GET /scripts/property-calculators` returns `load_active` rows including `source` (app.py:2199-2204).
- A new route needs, all together: (1) row in `ROUTE_POLICIES` (a route without a row answers 403 `ROUTE_UNCLASSIFIED`, route_policy.py header); (2) the same row in the fenced `route-policy` block of `spec/SECURITY-BOUNDARY.md` §4.2 (format `METHOD|PATH|PRINCIPALS|SOURCE|ROLE`, principals sorted and `+`-joined, rows sorted by path then method; the block is compared field by field by `tests/test_security_boundary_spec.py`); (3) bump `len(ROUTE_POLICIES) == 129` in `tests/test_route_inventory.py:209` and extend its history comment; (4) the cross-project matrix (`tests/test_cross_project_matrix.py`) is generated from the table, so each project-scoped row is covered automatically (P1 editor asking for P2 → 403, etc.).
- Principals: roles are viewer < editor < owner; admin = owner everywhere [CITED: SECURITY-BOUNDARY.md §3.1]. Delegated principal is bound to one project and uses the user's stored role (§3.5); the mapping `apply` precedent admits delegated editor "intent only" (§3.9). A connector principal has no calculator routes.
- Machine-checked blocks: `public-routes`, `route-policy`, `known-default-secrets`, `published-ports` [VERIFIED: tests/test_security_boundary_spec.py:44]. Only `route-policy` changes. Add prose (a new §3.x "Calculator promotion") describing the confirm gate; prose is not machine-checked but is the contract text.
- Because a promoted calculator executes inside **other users' Revit sessions**, treat confirm as a code-promotion gate, not a convenience write. See Security Domain and Open Question 2.

**Q5. UI patterns.**
- `ProposalCard` (MappingPanel.jsx:588-719): collapsible card, header badge + title + count, body with option buttons, `status` block (progress/error via `describeError`), "Details" toggle. `AnswerCard` (723-762): collapsed summary with its own Undo button, `busy`/`error`/`undoing` props. `PropertyCheckCard` (943-1030) is the host: it already owns generate/run buttons and renders `resolved`/`unsupported` lines.
- API client: `placePropertyCheck(project)` and `runPropertyCheck(project, {clear})` in `ui-v2/src/lib/mappingApi.js:48-58`; calls go through `apiFetch(...)` with project in the body (POST) or query (GET) — the file header says why [VERIFIED: mappingApi.js:1-5].
- Primitives to reuse (all exported from `components/index.js`): `Button`, `Badge`, `CodeBlock` (monospace `<pre>`, display/CodeBlock.jsx), `Collapsible`, `Callout`, `KVRow`, `Chip`, `Dialog` (confirm modal; fixed 380 px width). Styling constants `CARD`, `BODY`, `MUTED`, `MONO`, `ERR_STYLE` exist at the top of MappingPanel.jsx.
- **Constraint:** the panel is collapsed by default and requests nothing until opened; exact-request browser tests rely on it (MappingPanel.jsx:27-29, D-29). Load candidates only on an explicit button in `PropertyCheckCard` (after "Run check"), never on mount.
- i18n: strings go into `src/i18n/dict/screens.js` with an RU value (existing pair: `"Generate check": "Сгенерировать проверку"` at line 198); the completeness/raw-text guard tests (`tests/i18n.test.mjs`, `tests/i18n-swept/*.json`) must stay green.

**Q6. DeGram.**
- `degram_property_check` is **component code in the DeGram build clone**, not in this worktree and not in data-service: `D:\dgb\src\tools\degram_tools.py` (`PROPERTY_CHECK_ACTIONS = ("generate","run","clear","status")`, `_property_check`, schema `enum`), `degram_variant/dg_client.py:186-203` (`DgClient.property_check(action)` posts to `/scripts/property-calculator/place`, `/scripts/property-check/run` (with `clear`), `/scripts/property-check/status` with the delegated token, body `{project, ...}`), `degram_variant/lockdown.py:42-43` (tool-name allowlist), `toolsets.py`; commit `b619e02e` on `feature/mapping-mvp` [VERIFIED: git show in D:\dgb\src].
- **A component change is needed only if DeGram must list/confirm/reject.** The DG adapter MCP surface is not involved: DG routes are reached through `DgClient` with the delegated token; no data-service-side "tool surface" exists for it. Adding an **action** to the existing tool (`candidates`, and optionally `confirm`/`reject` with `dataPropertyIri` + `sha256`) changes `PROPERTY_CHECK_ACTIONS`, the schema, `DgClient.property_check` routes, and tests; it does **not** change the tool-name sets that `tests/degram/test_lockdown.py:91` and `test_revit_bridge.py:275` pin. A Desktop-UI confirm button would follow the existing precedent `apps/desktop/src/degram/mapping-panel.tsx` (commit `38d3e7e7`, explicit confirm of accepted batches).
- Repository: **component** (`D:\dgb\src`, branch `feature/mapping-mvp`, no push, no gitlink bump, D-43/D-46). Live verification needs a Desktop rebuild and a scrubbed-environment launch, which are separate owner approvals [CITED: 1303-EXPLICIT-CONFIRMATION-ROLLOUT.md]. Recommend plan 16 splits into framework tasks first (complete and releasable without DeGram) and one gated component task.

**Q7. Schema propagation for a new global node.**
- Is any existing node global? Yes: `SpecClass` in `graph:'SpecGraph'` has no `project` by design, and `CLAIM_UNTAGGED_SHARED_GRAPHS = ["SpecGraph"]` keeps `POST /graph/{project}/claim-untagged` (editor) from tagging it (app.py:5673-5679, CLAIM_UNTAGGED_QUERY `MATCH (n) WHERE n.project IS NULL AND NOT coalesce(n.graph,'') IN $sharedGraphs SET n.project = $project`). `Builtin` is also shared (key `iri`). **A global `CatalogueCalculator` without a listed `graph` value would be claimed into the first project that clicks "claim untagged".** (Pitfall 1.)
- Project isolation tests: `GRAPH_NODES_QUERY` and every project read filter by `n.project = $project` (app.py:5647-5651), so a node with no `project` never appears in a project graph or its cascade; therefore **do not name the provenance field `project`** — use `sourceProject`.
- Checklist from CLAUDE.md, with decision:

  | File | Applies? | Reason |
  |---|---|---|
  | `spec/DATABASE.md` | **Yes** | New label + new properties on `PropertyCalculator` (review fields); precedent: plan 15 documented `PropertyCalculator` here as "experimental" (DATABASE.md:612-616) |
  | `spec/LPG-OWL-MAPPING.md` | **Yes** | One row "`CatalogueCalculator` node — not exported", like the `PropertyCalculator` row (LPG-OWL-MAPPING.md:376) |
  | `spec/SECURITY-BOUNDARY.md` | **Yes** | New route rows (machine-checked) + prose for the gate; also a note on the global-node/company scoping decision |
  | `spec/REPRODUCIBILITY.md` | **Yes (fix)** | Register `property_calculator_llm.py|generate_calculator|model-dependent-unmeasured` and change "exactly nine lines" to ten; drift test is red today (Pitfall 2) |
  | `ontology/dg-shapes.ttl` | No | Shapes validate exported OWL/RDF data; neither `PropertyCalculator` nor `MappingProfile` has a shape (grep over the file: none), and the new node is "not exported" |
  | `cypher_template.txt`, `training/dataset_schema.json`, `llm/structure_rules.json` | No | They describe what the LLM ingest writes; the ingest never writes calculators. Plan 15's own propagation touched only DATABASE.md + LPG-OWL-MAPPING.md (commit `34fb3ea`) |
  | n8n workflow prompts, `config.template.js` | No | The vocabulary reaches the prompt through `assemble_context`; the workflow is unchanged [VERIFIED] |
  | `.github/copilot-instructions.md`, `README.md` | No (optional one-line) | No LLM-visible schema change; mention only if the owner wants the new routes listed |
  | `data-service/app.py` Cypher | Yes | The code itself; plus `LOCKED_NODE_LABELS` (add `PropertyCalculator`, `CatalogueCalculator`) and `CLAIM_UNTAGGED_SHARED_GRAPHS` |
  | `dg_context.ALLOWED_LABELS/RELATIONSHIPS` | No | They constrain **LLM-generated** Cypher; the LLM must not write these labels, so do not add them |
  | `dg-reasoner` exporters | No code change | Exporters match by explicit label sets with `n.project = $project` (ontology_export.py:44-55, valid_graph_export.py:53), so the new label is not read [VERIFIED: grep] |
  | `spec/EVIDENCE-CONTRACT.md`, `RULE-PARTITION-POLICY.md`, `SWRL-SUBSET.md` | No | No status, partition or atom-type change |
  
  No new **relationship** is recommended: link the project calculator to the catalogue entry by a string property (`catalogueId`) so a project-scoped traversal can never reach a global node and a project cascade can never delete it.

**Q8. Rejection path.**
- `load_active` already drops `status != 'active'` (store 17), so a rejected project calculator is excluded from `stored`. But `resolve` then falls through to the generator, `generate_calculator` (temperature 0) probably returns the **same source**, and `save` does `MERGE ... SET pc.status = 'active'` on the same key (store 24-28): the rejected calculator comes back as pending with its history overwritten (Pitfall 3).
- Recommended behaviour:
  1. Reject (`POST .../reject {project, dataPropertyIri, sha256, reason?, regenerate?: false}`): sets `status='rejected'`, `reviewStatus='rejected'`, `reviewedBy/At/Reason`, and appends `sha256` to `rejectedSha256Json` (a property on the node; it survives later `save`s because `SAVE_QUERY` only SETs listed fields).
  2. `SAVE_QUERY` must keep `status`/review fields when the incoming `sha256` equals the stored one, and reset to `status='active', reviewStatus='pending'` only for a **different** sha256.
  3. `resolve` gets the property's `rejectedSha256` set via `stored`-like input; when the generator returns a source whose sha256 is in the set, the property is `unsupported` with reason `"regenerated source was already rejected"`. No automatic regeneration loop: a rejected property is reported `unsupported: rejected by <user>` on later runs until the operator asks for **explicit regenerate** (`regenerate: true` on the reject call or a dedicated action), which passes the reason to the LLM and bumps `promptSha256`.
  4. Rejecting never touches the shared catalogue.

**Q9. Determinism and safety of promotion.**
- Byte identity: at confirm, copy `source` verbatim from the **project row read inside the write transaction** and require the request's `sha256` to equal it (and `sha256(source.encode('utf-8'))` to equal the stored `sha256`). At every resolve, recompute `sha256(source)` and compare with the stored field, then re-run the AST contract; mismatch → entry skipped, `warnings` list on the resolution, never used silently. (`_from_stored` does neither today.)
- AST re-run needs a rename shim: `validate_function` insists on the name `calc_gen`, while stored sources are `calc_gen_<hex>`. Add an optional `name` parameter (or a helper that validates a renamed source) rather than string-replacing in callers. `finalize` normalises with `ast.unparse`, so a promoted source must also be a fixed point: `ast.unparse(ast.parse(source)).strip() + "\n" == source`.
- Contract drift: the shell/`ctx` API (`catalogue.json.version` is `1303-15.3`) and `ALLOWED_GLOBALS` can change after confirmation. Store `contractVersion` (= the catalogue version at confirmation) on the entry and compare at resolve; if different, re-validate and warn (do not silently run a calculator confirmed against another shell).
- Concurrency/idempotency: use one `session.execute_write` with a lock step on the project calculator (`SET pc.reviewLock = coalesce(pc.reviewLock,0) + 1`, the pattern of `mapping_store.lock_session`, 938-943), then `MERGE (c:CatalogueCalculator {sha256:$sha})`. Same sha, same property, same company → return the existing entry (double click, two operators = same result, `alreadyConfirmed: true`, HTTP 200). Different sha for the same `(company, propertyKey)` while one is active → 409 `CATALOGUE_PROPERTY_TAKEN` (the operator retires the old one first); this keeps `resolve` deterministic (exactly one active entry per key). The repo manages no Neo4j constraints (grep: only an n10s smoke test), so uniqueness is enforced by the locked transaction, not by a DB constraint.
- Undo: `POST .../retire {project, catalogueId, reason}` (owner) sets `status='retired', retiredBy/At/Reason`; it never deletes. Project calculators carrying that `catalogueId` are set to `status='retired'` in the same transaction so the next run regenerates or reports unsupported (decision for the owner: cascade or leave project copies, Open Question 5). Retired entries leave the vocabulary at once.

**Q10. Test infrastructure.**
- Existing tests and style: `tests/test_property_scripts.py` (fake `_Session` dispatching on **substrings of the Cypher text**, lines ~150-175: `"READS_CLASS"`, `"PropertyCalculator"` + `MERGE`, `"PropertyCalculator"`, everything else returns the rule rows), `tests/test_property_calculator_llm.py` (pure AST tests with `complete=` injection), `tests/test_dg_knowledge.py:269-277`, `tests/test_dg_context.py` (`FixtureSession` returns the **same rows for every query**, lines 108-122), `tests/test_mapping_routes.py` (TestClient + in-memory fake store + stub driver; real admin session from `conftest`).
- Host baseline [VERIFIED: ran]: `pytest tests/test_property_scripts.py tests/test_property_calculator_llm.py tests/test_dg_knowledge.py tests/test_route_inventory.py tests/test_security_boundary_spec.py` → **1181 passed**; `tests/test_dg_context.py` → **62 passed, 4 failed** (the endpoint/determinism tests that need `neo4j:7687`; this is the known environment baseline); `tools/de01/tests` → **172 passed, 2 failed**: `test_reproducibility_scope_drift` (real regression from plan 15, fix in plan 16) and `test_de01_runner_against_golden_fixture_has_zero_silent_disagreements` (cause not investigated; `[ASSUMED]` environment, not related to calculators). The "25 `neo4j:7687` DNS errors" figure is [CITED: task brief] and was not reproduced in the subset I ran.
- Because the 4 failing `test_dg_context` tests are exactly the endpoint tests that would exercise the dynamic vocabulary, **the vocabulary merge must also be verified inside the container or live** (Validation Architecture, V6).
- ui-v2: `npm --prefix ui-v2 test` (= `cd .. && node --test ui-v2/tests/`), `node --test ui-v2/tests/mapping-api.test.mjs` passes 26/26 [VERIFIED: ran]; `npm --prefix ui-v2 run build`; browser tests `ui-v2/tests/run-panel.mjs` need an installed Chrome/Edge (`projects-panel.browser.jsx`, fake fetch, CSP `connect-src 'none'`).
- Live pattern [CITED: 1303-EXPLICIT-CONFIRMATION-ROLLOUT.md, CONTEXT D-30]: `git archive <commit>` into a clean folder, `docker build --no-cache`, rollback tags, `docker compose ... up -d --no-build --no-deps data-service design-grammars`, then check the **served** code hash inside the container and probe anonymous routes (401). Owner rule: fixes are deployed and re-tested live (memory `feedback-deploy-and-verify-live`). Docker 29.1.3 is running with `data-service`, `design-grammars`, `neo4j`, `n8n` up [VERIFIED: ran `docker ps`].

**Q11. Requirement ID.** None owns D-54 (see `<phase_requirements>`). Flagged as Open Question 1.

### Pattern 1: shared input to the pure resolver
**What:** `resolve(rules, catalogue, chooser, stored, generator, shared=None, rejected=None)`; `shared: dict[str, dict]` keyed by `propertyKey` (lower-cased IRI local name, the same normalisation as the alias match at property_scripts.py:120-121), loaded by `property_calculator_store.load_catalogue(session, company)`. A shared hit is turned into the existing generated binding shape so `assemble`, `read_categories`, `context_classes` and the placement need no change:
```python
# sketch; resolve() step between the file catalogue and `stored`
if binding is None:
    entry = (shared or {}).get(local_name(dp["iri"]).lower())
    checked = _from_shared(entry) if entry else None      # sha256 + AST re-run, returns None + warning on mismatch
    if checked:
        previous = stored.get(dp["iri"])
        same = previous is not None and previous.get("sha256") == checked["sha256"]
        binding = {**checked, "resolvedBy": "shared", "new": not same}   # `new` => save into the PROJECT store too
```
**Important:** a shared binding must still be written to the project's `PropertyCalculator` (set `catalogueId`, `reviewStatus='confirmed'`): `save_context_classes` does `MATCH (pc:PropertyCalculator {project, dataPropertyIri})` (store 43), so without the project node the READS_CLASS edges and `COMPUTED_BY` are never created.

### Pattern 2: vocabulary merge without touching the constant
```python
# dg_context.assemble_context (sketch)
conv = copy.deepcopy(dg_knowledge.swrl_conventions())
conv["computable_form"]["computable_properties"] += property_calculator_store.vocabulary_rows(session, company)
context["swrl_conventions"] = conv
```
`vocabulary_rows` must be tolerant: `try/except` → `[]` and keep only rows that contain `propertyKey` (the test `FixtureSession` returns entity rows for any query, Pitfall 6), with `ORDER BY propertyKey, sha256`.

### Anti-Patterns to Avoid
- **A `project` property on `CatalogueCalculator`**: makes it a project node (listed, cascaded, claimable). Use `sourceProject`.
- **`MERGE` + `SET status='active'` on re-save** (Pitfall 3).
- **Reusing the n8n workflow for the vocabulary** (a new n8n node, re-publish): unnecessary, the dict is already stringified.
- **Per-box values via a DG.gha/LISTENER change**: breaks D-53's "DG.gha not touched" and needs a Rhino restart; the published run already carries the values.
- **Letting an agent confirm its own generated code** without a human step (Open Question 3).

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Source safety re-check | A second validator | `property_calculator_llm.validate_function` (+ a `name` parameter) and `categories_in` | One contract; two validators drift |
| Source identity | Timestamps/ids | `hashlib.sha256(source.encode("utf-8"))` as in `resolve` (property_scripts.py:250) | Same digest already stored, byte identity |
| Idempotent confirm | An app-level lock or a "pending" flag | One `execute_write` with the lock-by-SET pattern + `MERGE` on `sha256` (mapping_store.py:938-1026) | The repo's proven pattern; no constraint tooling exists |
| Request/revision conflict handling | New error vocabulary | `_structured_error_response(error, hint, code, status)` and the `{error,hint,code}` shape (app.py:933-935) | Route tests and UI `describeError` expect it |
| Near-duplicate property names | New fuzzy matcher | `class_duplicates.property_reason` (used by `resolve_property`, property_scripts.py:131-143) | Already decides "same measure, wording differs" |
| Actor name | Reading headers | `_mapping_actor(request)` (app.py:5957-5959) | Works for session, delegated and connector principals |
| Company of a project | A Neo4j property | `company.company_for_project(project)` (company.py:53), a JSON store | Company is not a graph attribute (company.py docstring) |
| Run/verdict reading | New Cypher on run internals | `get_validation_run`, `ENTITY_STATUSES_QUERY`, `design_state_projection` shapes | Existing read models |

**Key insight:** the heavy parts (AST contract, sha256 identity, project-isolated store, resolver, UI card) exist. Plan 16 is a state machine (pending → confirmed/rejected → retired) wrapped around them, plus one new input in the resolver and one merge in the assembler.

## Runtime State Inventory

Not a rename/refactor phase, but the change adds stateful artifacts. Explicit answers:

| Category | Items Found | Action Required |
|----------|-------------|-----------------|
| Stored data | Existing `(:PropertyCalculator)` rows from plan 15 live runs (project `str-openings-01` and others) have no review fields and no `unit`/`explanation` | Code: treat absent `reviewStatus` as `pending` for `origin: generated`; no migration needed. Catalogue-origin rows are never candidates |
| Live service config | n8n ingest workflow stringifies `swrl_conventions` (unchanged); live `data-service` image must be rebuilt for new routes/merge | Rebuild/recreate `data-service` and `design-grammars` per D-30; **no n8n re-publish** (verify by reading the served `/context/assemble` output) |
| OS-registered state | None — verified by reading: no scheduled task or service embeds calculator names | None |
| Secrets/env vars | None; no new env var | None |
| Build artifacts | DeGram packaged build (component) carries the old tool schema if the optional DeGram task is done | Rebuild `win-unpacked` only for the component task (owner approval) |

## Common Pitfalls

### Pitfall 1: A global node gets claimed by a project
**What goes wrong:** `POST /graph/{project}/claim-untagged` sets `n.project` on every node with `project IS NULL` whose `graph` is not in `CLAIM_UNTAGGED_SHARED_GRAPHS` [VERIFIED: app.py:5673-5679]. A `CatalogueCalculator` without a registered `graph` value is stolen by the first editor who clicks it, then vanishes from every other project and enters its graph view.
**How to avoid:** give it `graph: 'CalculatorCatalogue'` and add that value to `CLAIM_UNTAGGED_SHARED_GRAPHS`; add a test that the claim query leaves it untouched. Never write a `project` property on it.
**Warning signs:** a catalogue entry that suddenly appears in `GET /graph/{project}`.

### Pitfall 2: Reproducibility drift test is already red
**What goes wrong:** `tools/de01/tests/test_reproducibility_scope_drift.py` fails with "in code but not documented: `property_calculator_llm.py|generate_calculator`" [VERIFIED: ran]. The scan counts any `X.generate(...)` call on a name containing `adapter` in `data-service/*.py`.
**How to avoid:** Wave 0 task: add the row `property_calculator_llm.py|generate_calculator|model-dependent-unmeasured` to the fenced block of `spec/REPRODUCIBILITY.md` (and fix the prose "exactly nine lines"); plan 16 adds a regenerate path that reuses this call site, so the registration is in scope. Do not add a new `adapter.generate` call elsewhere.

### Pitfall 3: Reject is silently undone
**What goes wrong:** `SAVE_QUERY` always sets `pc.status = 'active'` and overwrites `source`/`sha256` (property_calculator_store.py:24-33). After a reject, the next place/run regenerates (temperature 0 → likely identical source), re-activates the calculator and the operator is asked about the same code forever, with the history lost.
**How to avoid:** Q8 design: review fields survive saves; status reset only on a different sha256; `rejectedSha256Json` guard; explicit regenerate.

### Pitfall 4: Stored source fails the AST contract
**What goes wrong:** `validate_function` requires the function name `calc_gen`; stored/promoted sources are named `calc_gen_<hex>` (line 78 vs `finalize` 125-130). A naive re-validation at promotion or resolve rejects every genuine calculator.
**How to avoid:** add a `name` argument (default `FUNCTION_NAME`) or validate after an AST-level rename; test with a stored source from `finalize`.

### Pitfall 5: `unit`/`explanation` never persisted; `new` flag only for catalogue/LLM
**What goes wrong:** D-54 point 2 needs `unit`. The LLM answer carries it, `resolve` drops it (property_scripts.py:251-254) and `save` has no field for it. A confirm built later cannot recover it.
**How to avoid:** carry `unit`/`explanation` into the binding and add them to `SAVE_QUERY`/`LOAD_QUERY`; existing rows without them show `unit: null` (operator may supply/confirm the unit at confirm time).

### Pitfall 6: Test doubles that answer every query
**What goes wrong:** `test_dg_context.FixtureSession.run` returns the same rows for any Cypher (108-122) and `test_property_scripts._Session.run` falls through to `return _Result(self.rows)` for unknown queries. A new `CatalogueCalculator` query would receive entity or rule rows and either crash or produce phantom vocabulary.
**How to avoid:** `load_catalogue`/`vocabulary_rows` filter on required keys and catch exceptions; extend `_Session` with an explicit `"CatalogueCalculator"` branch; keep the 62 passing `test_dg_context` tests green.

### Pitfall 7: Editors can rewrite stored source through the generic graph route
**What goes wrong:** `PUT /graph/{project}/node/{id}/property` (editor) refuses only `LOCKED_NODE_LABELS` and protected keys; `PropertyCalculator` is not locked, and `source`/`sha256` are not protected keys [VERIFIED: app.py:5629-5636, 5680-5684, PROTECTED_NODE_KEYS_CI list]. An edited `source` bypasses the AST contract and runs in Rhino at the next check. CONTEXT D-32 already put the three mapping labels into this list as precedent.
**How to avoid:** add `PropertyCalculator` and `CatalogueCalculator` to `LOCKED_NODE_LABELS`, and the resolve-time sha256 + AST re-check (Q9). Test that the node-property route refuses both labels.

### Pitfall 8: LLM text flows into the next LLM prompt
**What goes wrong:** `meaning` in `computable_properties` is part of the ingest prompt. If it is the raw LLM `explanation`, a generated calculator can carry instructions into every later ingest in every project.
**How to avoid:** operator-confirmed `meaning` (≤160 chars, single line, control characters stripped), shown at the confirm step; test the sanitiser.

### Pitfall 9: The run data may not give per-box values the way I expect
**What goes wrong:** `statePayloadJson.propStates[].objectRef` is documented only as "per-object link ... so the value binds only to its object" (PropertyStateComponent.cs:67-68) and `design_state_projection.py:183-190`. Whether `objectRef` equals the Revit UniqueId, the OBJECT STATE id or a composite is `[ASSUMED]`; a run published without the ObjState link has no object at all.
**How to avoid:** first task of the live check (V5) prints one real `propStates` entry of a `str-openings-01` run; map `objectRef` → box label via the run's `objStates` (same payload). Fallback if it cannot be mapped: add up to N `sample <property> <uid> <label> = <value>` lines to the calculator `Report` (calculator_shell.py.tmpl) — a template change that bumps the catalogue version and re-places chains, so use it only as a fallback.

### Pitfall 10: The confirm is not tied to the run that justified it
**What goes wrong:** the calculator that produced a run's values is not recorded in the run (the canvas sha covers the whole assembled script, not one function). An operator could confirm a calculator that was never run, or one regenerated after the run.
**How to avoid:** confirm requires `runId` (project-scoped, existing, `createdAt >= pc.createdAt`, with propStates for the property) and the exact `sha256` the screen showed; store `sourceRunId`. This is a heuristic gate, not proof of execution; say so in the spec (Open Question 4 asks whether the owner wants a stronger binding).

### Pitfall 11: Route inventory and boundary spec go red together
**What goes wrong:** adding a route without the policy row → 403 at runtime; with the row but without the SECURITY-BOUNDARY block row → `test_security_boundary_spec.py` fails; without bumping 129 → `test_policy_table_size` fails.
**How to avoid:** one task edits `route_policy.py`, the §4.2 block (sorted by path then method) and `test_route_inventory.py:209` together.

## Code Examples

### Confirm, one transaction (sketch of the contract, not final code)
```python
def confirm(tx, project, data_property_iri, sha256, run_id, actor, company, meaning, unit):
    row = tx.run("MATCH (pc:PropertyCalculator {project:$p, dataPropertyIri:$d}) "
                 "SET pc.reviewLock = coalesce(pc.reviewLock,0)+1 "          # serialises two operators
                 "RETURN pc.source AS source, pc.sha256 AS sha256, pc.function AS function, "
                 "pc.origin AS origin, pc.status AS status", p=project, d=data_property_iri).single()
    if not row or row["origin"] != "generated" or row["sha256"] != sha256:
        raise ReviewError("CALCULATOR_CHANGED", 409)                          # operator must re-open the screen
    if hashlib.sha256(row["source"].encode("utf-8")).hexdigest() != sha256:
        raise ReviewError("CALCULATOR_INTEGRITY", 409)
    validate_renamed(row["source"], row["function"])                          # AST contract re-run
    # MERGE on sha256; reject if another active entry holds (company, propertyKey)
```
Source for the pattern: `data-service/mapping_store.py:938-943` (lock) and `:979-1026` (idempotent commit with `requestId`/`revision` conflict codes).

### Candidate samples from a run
```python
payload = json.loads(run["statePayloadJson"])
rows = [(ps["objectRef"], ps["propValue"]["value"]) for ps in payload.get("propStates", [])
        if ps.get("dataPropertyIri") == data_property_iri and isinstance(ps.get("propValue"), dict)]
rows.sort()                      # deterministic: by objectRef; return first N and n/min/max over all
```
Source: shapes in `data-service/design_state_projection.py:176-195`, `app.py:983-1000`.

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Catalogue edited by hand (`catalogue.json`) | Confirmed generated calculators extend a Neo4j catalogue (D-54) | 2026-10-20 | Vocabulary grows from human-checked results; ingest reuses names |
| "LLM never emits code" (plan-15 T-15-01) | LLM-written calculator under an AST contract (amendment A-2) | 2026-10-20 | Safety by contract only; correctness by operator confirmation (this plan) |

**Deprecated:** none.

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | `propStates[].objectRef` can be mapped to a Revit box (UniqueId/label) via the run's `objStates` | Q2, Pitfall 9 | Samples cannot be shown from the run; fallback = Report sample lines (template change) |
| A2 | The published run (SendValid true, the default) always carries propStates for generated properties | Q2 | Candidate screen shows no samples until a run with `send=true`; UI must say so |
| A3 | Shared catalogue scoped by company (JSON store attribute) rather than truly global | Q3, Open Q2 | If owner wants fully global, drop the `company` filter (trivial); if per-project, D-54 point 3 ("later rules and projects reuse it") is violated |
| A4 | Confirming from the DeGram **agent** is not wanted without a human click | Q6, Open Q3 | If the owner wants the agent to confirm, add `confirm`/`reject` actions to `degram_property_check` and accept that the LLM can approve its own code |
| A5 | A calculator confirmed under shell contract `1303-15.3` stays valid while the version string is unchanged | Q9 | Shell API changes without a version bump would run stale promoted code; enforce a version bump rule in the spec |
| A6 | `test_de01_runner_against_golden_fixture...` failure is environmental and unrelated | Q10 | A second real regression hidden under the baseline |
| A7 | `data-service/requirements.txt` versions are untouched by this plan (not re-read) | Standard Stack | None expected |
| A8 | One retire cascades to project copies (status retired) | Q9, Open Q5 | If the owner prefers copies to stay usable, projects keep running a retired calculator |

## Open Questions

1. **Which requirement owns D-54?** — Known: DGOPN-01..04 only (REQUIREMENTS.md:130-133); none mentions confirmation or promotion. Unclear: amend DGOPN-02's text or add DGOPN-05 (and the traceability row at REQUIREMENTS.md:181-214). Recommendation: owner decides before planning; I recommend a new **DGOPN-05** so DGOPN-04's "Акт 4 match gold" stays a closed acceptance, but I have not invented it.
2. **Scope of "shared"?** — D-54 says shared catalogue "in Neo4j", reused by "later rules and projects". Unclear: truly global vs per company. Projects carry a company (`company.py`, "not a tenancy layer"; company governance is Phase 1302). Source code and `sourceProject` names cross project boundaries, and the calculator executes in other users' Revit. Recommendation: key and filter by company (unassigned projects share one bucket), expose `sourceProject` only to owners/admins.
3. **May the DeGram agent confirm?** — D-54 says "Web UI, DeGram tool". The agent is an LLM and the generated code is LLM output. Recommendation: the tool lists candidates (read), the confirm/reject click is a human action in the Web UI or the DeGram Desktop panel (precedent: explicit batch confirm, commit `38d3e7e7`; SECURITY-BOUNDARY §3.9 "answering does not authorize a write"). Needs an owner decision because it changes what the delegated principal may do.
4. **How strong must "confirmed on a model" be?** — Today a run does not record which calculator produced its values (Pitfall 10). Recommendation: gate on `runId` + exact sha256 + run newer than the calculator; accept that this is a heuristic. A stronger binding needs the calculator sha in the published run (DG.gha change, excluded by D-53).
5. **Retire semantics.** — Cascade to project copies or leave them? Recommendation: cascade (status `retired`), owner role required.
6. **Who may retire / confirm?** — Recommendation: confirm = editor of the origin project (project-scoped row, delegated allowed per Q3 outcome); retire = owner (or admin). Needs owner confirmation.
7. **One active entry per property: 409 vs versioning.** — Recommendation: 409 `CATALOGUE_PROPERTY_TAKEN` (deterministic resolution). Versioned entries are possible but add a selection rule.

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| Python | data-service tests | ✓ | 3.14.2 | — |
| pytest | tests | ✓ | pytest 9.0.2 (from pyc name) | — |
| Node | ui-v2 tests/build | ✓ | v20.20.0 | — |
| Docker | live rollout | ✓ | 29.1.3, containers up (`data-service`, `design-grammars`, `neo4j`, `n8n`, ...) | — |
| Chrome/Edge | `run-panel.mjs` browser tests | ✓ (paths probed by the script; not run) [ASSUMED] | — | skip browser test, run node tests + build |
| Neo4j from host | tests needing `neo4j:7687` | ✗ (host cannot resolve `neo4j`) | — | run those tests/probes inside the container or live (owner memory: `docker exec` from PowerShell; use `MSYS_NO_PATHCONV` in Git Bash) |
| Rhino/Revit/GH LISTENER | live run that produces samples | owner machine [ASSUMED available per plan 15 state] | — | none: samples need a published run |
| `D:\dgb\src` DeGram clone | optional component task | ✓ | HEAD `b619e02e` | defer component task |

**Missing with no fallback:** none for the framework part. A live candidate screen needs a published run of a generated calculator (Rhino + Revit session), which the owner provides.

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest 9.0.2 on Python 3.14.2 (data-service); node:test (ui-v2); pytest in the DeGram clone for the component task |
| Config file | none beyond `data-service/tests/conftest.py` |
| Quick run command | `cd data-service && python -m pytest tests/test_property_scripts.py tests/test_property_calculator_llm.py tests/test_property_calculator_review.py tests/test_dg_knowledge.py tests/test_route_inventory.py tests/test_security_boundary_spec.py -q -p no:cacheprovider` |
| Full suite command | `cd data-service && python -m pytest tests -q -p no:cacheprovider` (expect the known env baseline: 4 `test_dg_context` failures + `neo4j:7687` DNS errors) plus `python -m pytest tools/de01/tests -q` and `npm --prefix ui-v2 test` and `npm --prefix ui-v2 run build` |

### Phase Requirements → Test Map (must-haves proposed for plan 16)
| ID | Behaviour | Test Type | Automated Command | File Exists? |
|----|-----------|-----------|-------------------|-------------|
| V1 | Resolution order file → shared → stored → LLM; shared entry beats a stored generated one; file alias beats shared; no LLM call when shared hits | unit | `pytest tests/test_property_scripts.py -k shared` | ❌ Wave 0 (extend file, new `_Session` branch for `CatalogueCalculator`) |
| V2 | Integrity at resolve: sha256 mismatch or AST failure → entry skipped with warning, never used; stored `calc_gen_<hex>` source re-validates | unit | `pytest tests/test_property_scripts.py tests/test_property_calculator_llm.py -k "integrity or rename"` | ❌ Wave 0 |
| V3 | Candidates: samples sorted by objectRef, n/min/max over all, verdict counts per rule from entity rows; empty when no run | unit (canned `statePayloadJson`) | `pytest tests/test_property_calculator_review.py` | ❌ Wave 0 (new file) |
| V4 | Confirm gate: wrong sha → 409, missing/foreign run → 422/404, AST failure → 409, name taken → 409, double confirm → same entry (`alreadyConfirmed`), two sequential operators → one node | unit + route (TestClient, stub driver as in `test_mapping_routes.py`) | `pytest tests/test_property_calculator_review.py tests/test_property_calculator_routes.py` | ❌ Wave 0 |
| V5 | Reject: excluded from `load_active`; later save with the same sha stays rejected; regenerated same sha → unsupported; different sha → pending; explicit regenerate passes the reason | unit | `pytest tests/test_property_scripts.py -k reject` | ❌ Wave 0 |
| V6 | Vocabulary merge: file vocabulary + active entries ordered by key; byte-identical twice; module constant not mutated (`swrl_conventions() is SWRL_CONVENTIONS` still true and unchanged after assemble); retired/other-company entries absent; `FixtureSession` rows do not leak in | unit + **live** | unit: `pytest tests/test_dg_context.py -k vocabulary tests/test_dg_knowledge.py`; live: `POST /context/assemble` inside the container, service token (4 host endpoint tests cannot run) | ❌ Wave 0 / live |
| V7 | Retire: entry leaves resolve and vocabulary, project copies follow the chosen cascade, history kept | unit | `pytest tests/test_property_scripts.py -k retire` | ❌ Wave 0 |
| V8 | Security: 4 policy rows == SECURITY-BOUNDARY block; inventory count; cross-project matrix auto-covers; `claim-untagged` leaves `CatalogueCalculator` untouched; `PropertyCalculator`/`CatalogueCalculator` refused by `PUT /graph/{project}/node/{id}/property`; `property` key `project` never written on the catalogue node | unit | `pytest tests/test_route_inventory.py tests/test_security_boundary_spec.py tests/test_cross_project_matrix.py tests/test_graph_routes.py -q` | partly ✅ (update counts) / ❌ new asserts |
| V9 | Reproducibility registry: scope-drift test green with `generate_calculator` registered | unit | `python -m pytest tools/de01/tests/test_reproducibility_scope_drift.py` | ✅ exists (red now) |
| V10 | UI: `mappingApi` helpers (`listCalculatorCandidates`, `confirmCalculator`, `rejectCalculator`, `retireCalculator`) send project in body/query and surface error codes; card renders source, samples, verdicts, confirm/reject; no request on mount | node + browser | `node --test ui-v2/tests/mapping-api.test.mjs`; `node ui-v2/tests/run-panel.mjs calc-review`; `npm --prefix ui-v2 test`; `npm --prefix ui-v2 run build` | partly ✅ (`mapping-api.test.mjs`); card test ❌ Wave 0 |
| V11 | i18n: every new string has RU; completeness + raw-text guard stay green | node | `npm --prefix ui-v2 test` | ✅ |
| V12 | Spec propagation: DATABASE.md/LPG-OWL-MAPPING.md rows exist | doc check | `grep -n CatalogueCalculator spec/DATABASE.md spec/LPG-OWL-MAPPING.md` | ❌ Wave 0 |
| V13 | **Live end-to-end** (owner-visible, in the deployed container): property with no catalogue entry → ingest rule → place+run with SendValid → candidates show source, ≥1 sample value, verdicts → confirm → `CatalogueCalculator` exists, no `project` property → second project ingests a rule in the same concept: prompt vocabulary contains the name, resolution `resolvedBy: "shared"`, **zero LLM calls** (provider log) → retire → next ingest no longer lists it | live | deployed stack per D-30; evidence in `test/str-openings-01/evidence/` | ❌ manual/owner |
| V14 | DeGram component (optional task): `candidates` action returns the same fields; refusal codes map; tool-name sets unchanged | unit (component) | in `D:\dgb\src`: `python -m pytest tests/degram -q` [ASSUMED command] | ❌ Wave 0 (component) |

### Sampling Rate
- **Per task commit:** the quick run command (≈1 min).
- **Per wave merge:** quick command + `tests/test_cross_project_matrix.py` + `tools/de01/tests` + `npm --prefix ui-v2 test`.
- **Phase gate:** full data-service suite (classify failures by cause against the known baseline, not by count), `npm --prefix ui-v2 run build`, V13 live pass.

### Wave 0 Gaps
- [ ] `data-service/tests/test_property_calculator_review.py` — candidates, confirm, reject, retire (fake session with explicit `CatalogueCalculator` branch)
- [ ] `data-service/tests/test_property_calculator_routes.py` (or extend an existing route test) — policy, 409/422 codes, matrix
- [ ] extend `test_property_scripts._Session` with a `CatalogueCalculator` branch so the old tests do not feed rule rows to the new loader
- [ ] `spec/REPRODUCIBILITY.md` row for `property_calculator_llm.py|generate_calculator` (fixes the red drift test)
- [ ] ui-v2 browser test fixture for the review card (extend `projects-panel.browser.jsx`; keep the "no request on mount" expectations)
- [ ] none needed: framework install

## Security Domain

`security_enforcement` is not disabled in the config (absent = enabled); `workflow.nyquist_validation` absent = enabled.

### Applicable ASVS Categories

| ASVS Category | Applies | Standard Control |
|---------------|---------|-----------------|
| V2 Authentication | no change | existing session/delegated/connector resolution |
| V3 Session Management | no change | `X-DG-CSRF` on cookie POSTs; delegated Bearer exempt (SECURITY-BOUNDARY §3.5) |
| V4 Access Control | **yes** | `route_policy` rows (deny-by-default), role gate editor/owner, project binding, company scope for the catalogue; cross-project matrix |
| V5 Input Validation | **yes** | pydantic models with length limits; `sha256` pattern `^[0-9a-f]{64}$`; `dataPropertyIri` bounded; `meaning` sanitised; AST re-validation of source |
| V6 Cryptography | no new use | sha256 as content identity (not a secret) |
| V10/V12 Malicious code / file | **yes** | promoted source is executed in other users' Rhino.Inside.Revit: AST contract at generation **and** at confirm **and** at resolve; sha256 integrity; locked labels |

### Known Threat Patterns for this stack

| Pattern | STRIDE | Standard Mitigation |
|---------|--------|---------------------|
| Editor edits `PropertyCalculator.source` via the generic node-property route | Tampering | add both labels to `LOCKED_NODE_LABELS`; sha256 + AST re-check at resolve (Pitfalls 7) |
| Rubber-stamp confirm of unreviewed/other code | Spoofing/Repudiation | confirm bound to exact sha256 + runId; `confirmedBy/At/runId` stored; append-only provenance; owner-only retire |
| Cross-tenant code sharing (company A's calculator runs in company B) | Information disclosure / Elevation | company-scoped catalogue; `sourceProject` hidden from non-owners (Open Q2) |
| Prompt injection via `meaning`/`explanation` into the ingest prompt | Tampering | operator-confirmed, sanitised, length-capped `meaning` (Pitfall 8) |
| Global node claimed by a project | Tampering | `CLAIM_UNTAGGED_SHARED_GRAPHS` (Pitfall 1) |
| Delegated agent approves its own generated code | Elevation | Open Q3 recommendation: human click for confirm |
| Double submit / race | Tampering | locked `execute_write`, `MERGE` on sha256 (Q9) |
| Stale calculator after shell contract change | Tampering | `contractVersion` check (Q9) |

## Sources

### Primary (HIGH confidence — read in this session)
- `data-service/property_scripts.py`, `property_calculator_store.py`, `property_calculator_llm.py`, `property_calculators/catalogue.json`, `calculator_shell.py.tmpl`, `highlighter.py.tmpl`
- `data-service/dg_knowledge.py` (1-145), `dg_context.py` (325-505), `app.py` (898-945, 2040-2210, 3815-3855, 4165-4205, 5615-5700, 5775-5800, 5950-5975), `route_policy.py`, `mapping_store.py` (938-1026), `company.py`
- `spec/SECURITY-BOUNDARY.md` (§3.1-3.9, §4.2), `spec/DATABASE.md` (606-650), `spec/LPG-OWL-MAPPING.md` (364-430), `spec/REPRODUCIBILITY.md` (156-215)
- `DG/src/DG.Grasshopper/Components/CanvasListenerComponent.cs` (750-804), `PropertyStateComponent.cs`, `DG/src/DG.Core/Contracts/EvidenceEnvelope.cs`
- `ui-v2/src/screens/MappingPanel.jsx` (1-60, 580-770, 935-1035), `ui-v2/src/lib/mappingApi.js` (1-120), `ui-v2/src/components/*`, `ui-v2/package.json`, `ui-v2/src/i18n/dict/screens.js`
- `D:\dgb\src` `degram_variant/dg_client.py`, `lockdown.py`, `tools/degram_tools.py`, `toolsets.py` (commit `b619e02e`)
- `.planning/phases/1303-pravilo-gh-obekt/1303-CONTEXT.md`, `1303-15-PLAN.md`, `1303-EXPLICIT-CONFIRMATION-ROLLOUT.md`; `.planning/REQUIREMENTS.md` (126-133, 181-214); `.planning/STATE.md` (587); the todo and the Obsidian decision note
- Commands run: `pytest` on the five-file subset (1181 passed), `tests/test_dg_context.py` (62 passed, 4 failed), `tools/de01/tests` (172 passed, 2 failed), `node --test ui-v2/tests/mapping-api.test.mjs` (26/26), `docker ps`, `python/node --version`

### Secondary (MEDIUM)
- n8n workflow JSON read through a short Python script (node "Build LLM Prompt") to confirm `JSON.stringify` of `swrl_conventions`.

### Tertiary (LOW)
- none; unverified items are in the Assumptions Log.

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — no new dependency; existing modules read at line level.
- Architecture: MEDIUM-HIGH — resolution, store, assembler, routes and UI verified; the sample data path (`objectRef`) and the catalogue scope are the open parts.
- Pitfalls: HIGH for 1-8, 11 (read or run); MEDIUM for 9-10.

**Research date:** 2026-10-20
**Valid until:** 2026-11-03 (the surrounding code changes daily on `feature/mapping-mvp`; re-read `property_scripts.py` and `route_policy.py` before planning if HEAD moves from `ae32f23`).

## Project Constraints (from CLAUDE.md)

- Schema Change Propagation list applies to every graph-structure change (see the decision table in Q7); new Neo4j structure must be reflected in `spec/DATABASE.md` and `spec/LPG-OWL-MAPPING.md` at minimum; the SHACL shapes and LLM-facing schema files are reviewed and excluded with reasons.
- `spec/SECURITY-BOUNDARY.md` must be consulted before adding a route, principal, published port or secret; its machine-checked fenced blocks must be updated with any route change.
- `spec/REPRODUCIBILITY.md` governs LLM call sites; its machine-checked block is currently out of sync (fix in plan 16).
- DeGram cross-repository rules: the committing repository is named per task (framework vs component); no push, no gitlink bump (D-43/D-46); DeGram preflight `python tools/degram/workspace.py verify` before any DeGram-touching task; never create `.planning/` inside `apps/degram`; component work is done in `D:\dgb\src`.
- Rebuild the V2 UI with `--no-cache`; do not trust stale images (verify the served code).
- `#if GRASSHOPPER_SDK` guards and DG.gha rebuilds are not part of this plan (D-53); `bin/obj` of `DG/` are tracked and appear modified in `git status`: do not stage them.
- Session protocol and commit rules (own files only, one commit per session) apply to the executing session, not to this research.
- Do not search `DG_OBSIDIAN/archive/`, `.planning/milestones/`, `graphify-out/communities`, `Publications/`; never read `.secrets/`; never sweep `apps/degram/` broadly (not done).
