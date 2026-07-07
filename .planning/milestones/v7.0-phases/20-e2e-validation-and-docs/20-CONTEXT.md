# Phase 20: E2E Validation and Docs - Context

**Gathered:** 2026-07-05
**Status:** Ready for planning

<domain>
## Phase Boundary

Milestone wrap-up phase — the final phase of v7.0. Validates the full live pipeline end-to-end, documents every breaking change for canvas migration, refreshes all repo/AI-assistant docs to schema v4 and the 14-component set, and updates the knowledge vault. No new components — this is about testing, documenting, and releasing what Phases 13–19 built.

**In scope (E2E-01..04):**
- **E2E live chain validation** — Manual checklist with Docker-side automation, fresh + existing test data, full chain with all outputs verified, critical bugs fixed inline
- **Release notes** — Dedicated `docs/RELEASE-NOTES-v7.0.md` with full per-component re-wiring guide (ASCII wiring diagrams), breakage table, new features summary, and upgrade steps
- **Repo/AI docs update** — Targeted updates per doc: CLAUDE.md (schema + factual sections), `.github/copilot-instructions.md` (full schema + components rewrite), `spec/DATABASE.md`, `README.md` — verified via SC#3 grep gate + manual review
- **DG_OBSIDIAN + graphify refresh** — Archive stale notes, regenerate graphify via `scripts/refresh_graphify.sh`, update vault index + session note + priorities

**Out of scope (belongs in other phases):**
- New components, features, or bug fixes unrelated to E2E validation failures
- v4.0 BOT Ontology Bridge (separate milestone)
- v9.0 AI Workflow Intelligence (separate milestone)
- Fine-tuning or LLM pipeline changes

**Already locked upstream (do NOT re-open):**
- All 14 component contracts, port IRIs, and GUIDs — Phases 13–19
- Schema v4 contract (state kinds, Run properties, rule-level SWRL) — Phase 14
- SpecGraph runtime rename — Phase 15
- DesignState 3-part composition — Phase 16
- Graph access component contracts — Phase 17
- Validator contract (ValidStatus, SendStatus, DesignState-driven binding) — Phase 18
- Deconstruct/reinstate component contracts — Phase 19
- CLASSIFICATOR eliminated, VALIDATION RUNS replaced, REINSTATE reworked — Phases 17–19
- Canvas breakage is expected and intentional — v7.0 is a breaking-change milestone
</domain>

<decisions>
## Implementation Decisions

### E2E Test Scope & Failure Handling (Area 1)
- **D-01:** **Manual checklist + Docker automation.** GH-side: scripted walkthrough with explicit steps, expected outputs, and pass/fail per checkpoint. Docker-side: automated via curl/Cypher checks (rule ingest round-trip, Neo4j state verification, data-service publish endpoints).
- **D-02:** **Both fresh + existing test data.** Fresh fixture: 2–3 representative rules (height, area, material) + simple test geometry, clean baseline, reproducible. Existing project data as secondary smoke test to catch regressions.
- **D-03:** **Fix critical bugs inline.** If the chain breaks (component crashes, data mismatch, publish failure), fix as part of Phase 20. The E2E validation IS the last chance to catch v7.0 bugs before release.
- **D-04:** **Full chain, all outputs verified.** Every checklist step produces correct output: rule ingest creates valid Cypher, METAGRAPH returns rules, RULE DECONSTRUCT partitions correctly, STATE components produce correct state, VALIDATOR publishes with correct ValidStatus/SendStatus, VALIDATION GRAPH reads back intact, PARAMETER REINSTATE applies parameters. No component errors, no data loss.

### Release Notes Structure & Depth (Area 2)
- **D-05:** **Dedicated `docs/RELEASE-NOTES-v7.0.md`.** Standalone file with component-by-component breakage documentation, re-wiring guide, features summary, and upgrade instructions. Referenced from README.md.
- **D-06:** **Full re-wiring guide per changed/removed component.** Every affected component gets: old name → new name, what broke, ASCII wiring diagram showing old wiring vs new wiring, port-level mapping. Example groups: CLASSIFICATOR removal path (→ OBJECT STATE + PROPERTY STATE + DESIGN STATE), VALIDATION RUNS→VALIDATION GRAPH, REINSTATE→PARAMETER REINSTATE, CONNECTOR port renames.
- **D-07:** **Complete: breakage + features + upgrade.** Sections: (1) Breaking Changes — per-component re-wiring guide with ASCII diagrams, (2) New Features — 3-part state composition, SpecGraph layer, ontology-aligned ports, 14-component architecture, (3) Upgrade Guide — install new .gha, run DB migrations (kind rename, SpecGraph), open canvas and re-wire per Section 1.
- **D-08:** **ASCII wiring diagrams for re-wiring.** Text-only diagrams showing old → new wiring for each affected component group. Works in any editor, copy-paste friendly. Example:
  ```
  Before:  CONNECTOR → METAGRAPH → CLASSIFICATOR → VALIDATOR
  After:   CONNECTOR → GRAPH DECONSTRUCT → METAGRAPH → RULE DECONSTRUCT
                → OBJECT STATE + PROPERTY STATE → DESIGN STATE → VALIDATOR
  ```

### Docs Update Strategy & Depth (Area 3)
- **D-09:** **Targeted update per doc.** CLAUDE.md: update Graph Schema section (v3→v4), Schema Change Propagation list, Known Gotchas (new v7.0 gotchas), Tech Stack Summary. `.github/copilot-instructions.md`: full schema + components rewrite. `spec/DATABASE.md`: update labels/relationships/state kinds. `README.md`: update component count, milestone status, E2E reference. Not a full rewrite — preserved institutional knowledge stays.
- **D-10:** **copilot-instructions.md: Full schema + components rewrite.** Graph Schema section rewritten to v4: 3 state kinds (ObjState/ParamState/PropState), Run ValidStatus/SendStatus, rule-level SWRL/RuleName/RuleDescription, SpecGraph labels, ValidGraph layer. New Component Architecture section: 14 components with roles and wiring flow. Existing Patterns/Conventions updated for v7.0. This is the most impactful doc — it's what AI assistants read first.
- **D-11:** **CLAUDE.md: Update schema + factual sections.** Graph Schema v3→v4 section, Schema Change Propagation list (add data-service, copilot-instructions.md, README.md, spec/DATABASE.md), Known Gotchas (add v7.0 canvas breakage, old component GUIDs in saved .gh files), Tech Stack Summary (update component count: 5→14, add new model names). Architecture Quick Reference, Key Design Decisions, Repository Structure sections stay as-is (still accurate at overview level).
- **D-12:** **SC#3 grep gate + manual review.** Run `grep -ri "schema v3\|v3 schema"` over CLAUDE.md, `.github/copilot-instructions.md`, spec/, README.md — must return zero hits presenting v3 as current. Plus manual review of each doc for correct component names, labels, and property names. If grep finds anything, fix it.

### DG_OBSIDIAN & Graphify Refresh (Area 4)
- **D-13:** **Archive stale notes.** Move notes for deleted/renamed components (CLASSIFICATOR, VALIDATION RUNS, old REINSTATE) and v3.0-phase plans to `DG_OBSIDIAN/archive/`. Keep the vault clean. Link from `00-home/index.md` to archive. Notes that mention old names but are otherwise current get updated in-place.
- **D-14:** **Full graphify regeneration.** Run `scripts/refresh_graphify.sh` for a full regeneration. Picks up all renamed/deleted files from Phases 13–19. Community notes will match the current codebase — no CLASSIFICATOR, ValidationRunsComponent, or v3.0-phase references survive as "current."
- **D-15:** **Update vault index + session note + priorities.** Update `00-home/index.md` to reflect archived notes and v7.0 completion. Create session note for Phase 20 work. Update `00-home/Current priorities.md` to reflect milestone completion and next steps (v4.0 BOT Ontology Bridge). Follow the session protocol in CLAUDE.md.

### Claude's Discretion
- Exact E2E checklist steps and checkpoint format
- Exact release notes wording, section structure, and ASCII diagram content
- Which specific DG_OBSIDIAN notes get archived vs updated in-place (discovery left to planner/researcher)
- README.md and spec/DATABASE.md update specifics (scope defined, exact content TBD)
- Session note title and structure (follow existing Obsidian session note format)
- Whether to create a combined Docker-side E2E test script or inline curl commands in the checklist
- Exact grep patterns for SC#3 verification gate
- Order of operations: E2E validation should run first (may surface bugs requiring fixes), then docs update, then release notes (docs reference validated reality), then DG_OBSIDIAN refresh last
</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Requirements & roadmap
- `.planning/REQUIREMENTS.md` — E2E-01..04 (end-to-end and docs requirements)
- `.planning/ROADMAP.md` — Phase 20 goal + 5 success criteria + full E2E chain path
- `.planning/PROJECT.md` — key decisions: project isolation, DB labels unchanged, port-IRI contract, canvas breakage policy

### Prior phase context (decisions carried forward — all 7 phases)
- `.planning/milestones/v7.0-phases/13-ontology-v7-and-contract-investigation/13-CONTEXT.md` — D-01..D-11: DesignState layer placement (ValidGraph), MERGE by StateId+project, ValidStatus per-ObjState Boolean array, component GUIDs, port-IRI map
- `.planning/milestones/v7.0-phases/14-graph-schema-v4-propagation/14-CONTEXT.md` — D-01 (no Status text field), D-14 (ValidGraph runtime literal), D-06 (coalesce read pattern)
- `.planning/milestones/v7.0-phases/15-specgraph-runtime-rename/15-CONTEXT.md` — SpecGraph rename scope, labels preserved
- `.planning/milestones/v7.0-phases/16-dg-core-state-models-and-state-components/16-CONTEXT.md` — D-01/D-02 (DesignState = independent bags), D-04 (deterministic StateId), D-05/D-06 (statePayloadJson v2), D-08/D-10 (PropState rule-scoped)
- `.planning/milestones/v7.0-phases/17-graph-access-components/17-CONTEXT.md` — D-01 (individual handle types), D-02 (METAGRAPH Objects via REFERS_TO→Class), D-03/D-04/D-05 (VALIDATION GRAPH Run/Status/DesignState outputs)
- `.planning/milestones/v7.0-phases/18-rules-and-validator-rework/18-CONTEXT.md` — D-01/D-02 (ValidStatus per-ObjState Boolean list, non-matching excluded from AND), D-03 (DesignStateBindingService), D-09 (CLASSIFICATOR fully purged), cross-phase notes for release notes content
- `.planning/milestones/v7.0-phases/19-deconstruct-and-reinstate-components/19-CONTEXT.md` — D-01/D-02 (REINSTATE Target input required), D-04/D-05 (StateStatus index-matched, Parameters = all), D-07 (DECONSTRUCT Warning+empty outputs), cross-phase notes for release notes content

### Ontology & component contract
- `ontology/port-iri-map-V7.md` — per-port IRI contract for all 14 components. **MUST read** for release notes accuracy.
- `ontology/DesignGrammar-V7.owl` — V7 ontology: all classes, properties, state kinds. Source of truth for doc updates.
- `ontology/V7-INVESTIGATION.md` — conflict resolutions (ValidStatus vs Status, DesignState layer placement, version marker)
- `ontology/GH_DesignGrammars.pdf` — 14-component schema with wiring diagrams. Reference for release notes diagrams.

### Docs to update
- `CLAUDE.md` — Graph Schema section (currently v3), Schema Change Propagation list, Known Gotchas, Tech Stack Summary
- `.github/copilot-instructions.md` — currently mandates "v3 as source of truth." **Full schema + components rewrite required.**
- `spec/DATABASE.md` — labels, relationships, state kinds
- `README.md` — component count, milestone status, E2E reference

### Knowledge vault
- `DG_OBSIDIAN/00-home/index.md` — vault index to update
- `DG_OBSIDIAN/00-home/Current priorities.md` — priorities to update for milestone completion
- `DG_OBSIDIAN/knowledge/` — component notes, schema notes, debugging notes — some need archiving
- `scripts/refresh_graphify.sh` — graphify regeneration script

### Infrastructure
- `docker-compose.yml` — all service definitions for Docker-side E2E automation
- `test/` — existing test data and fixtures
</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- **Docker compose stack** (`docker-compose.yml`): 12+ services already orchestrated. Docker-side E2E automation: `docker compose up -d`, curl rule ingest webhook, verify Neo4j via Cypher, check data-service endpoints. No new infrastructure needed.
- **Existing test data** (`test/`): Ad-hoc test scripts, fixtures, and test rules from v2.0/v3.0 development. Can serve as secondary smoke test data.
- **Phase 13–19 components**: All 14 GH components exist and are tested. The E2E checklist wires them together — no component changes unless bugs found.
- **n8n workflows** (`n8n/workflows/`): Rule ingest and graph query workflows already updated to v4 schema (Phase 14). E2E Docker automation uses these directly.
- **data-service endpoints** (`data-service/app.py`): Validation publish/list/delete/view endpoints already adapted to v2 payloads (Phase 18). Docker-side verification curls these.

### Established Patterns
- **ErrorMessageTemplates What+Where+How-to-fix pattern**: Release notes re-wiring instructions follow a similar structure — What changed, Where (which component), How to fix (re-wire steps).
- **Obsidian session protocol** (CLAUDE.md): Session note creation, index update, priorities update. Follow this for Phase 20 session note.
- **Markdown docs convention**: All project docs are markdown. Release notes, updated docs, and session notes stay in markdown.
- **Schema Change Propagation list** (CLAUDE.md): Lists every artifact requiring updates on schema changes. Phase 20 extends this list to include the docs being updated.

### Integration Points
- **Docker → Neo4j**: Direct Cypher verification — `docker compose exec` or HTTP API to check graph state after rule ingest, verify statePayloadJson v2 format, confirm SpecGraph labels.
- **Docker → n8n → Ollama → Neo4j**: Rule ingest round-trip — curl webhook → n8n builds prompt → Ollama generates Cypher → n8n executes → Neo4j. Verify generated Cypher validates against v4 template.
- **Docker → data-service**: Validation publish verification — curl `/validation/publish` endpoint, check response, verify Neo4j ValidationRun node created with correct ValidStatus/SendStatus.
- **Grasshopper plugin**: Manual GH-side walkthrough — wire 14 components, trigger validation, verify outputs on canvas. No automation possible without Rhino scripting.
- **DG_OBSIDIAN → graphify**: `scripts/refresh_graphify.sh` reads DG_OBSIDIAN for community notes. After archiving stale notes, regeneration produces clean graph.
- **Docs → codebase**: Updated docs reference v4 schema + 14-component set. grep gate verifies no stale v3 references survive.
</code_context>

<specifics>
## Specific Ideas

- **E2E should run first, then docs.** The E2E validation may surface bugs requiring code fixes. Docs and release notes should document the validated reality, not the expected one. Order: E2E → fix bugs → docs update → release notes → DG_OBSIDIAN refresh.
- **Release notes audience is architects**, not developers. Use plain language, focus on what changed on their canvas, provide concrete re-wiring steps. Avoid ontology IRIs and implementation details — those go in port-IRI map and developer docs.
- **The E2E checklist is both a test tool AND a release artifact.** Architects can use it to verify their own v7.0 installation. Write it to be reusable beyond development.
- **SC#3 grep gate is a hard blocker.** If `grep -ri "schema v3\|v3 schema"` finds anything presenting v3 as current, the phase is not done. This is the mechanical verification that all docs agree on v4.
- **Graphify regeneration is the final step** — it captures the codebase state after all Phase 20 changes are committed. Running it earlier would miss the docs/release notes changes.
</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope.

### Cross-phase notes (not scope changes)
- **v4.0 BOT Ontology Bridge**: Next milestone after v7.0 ships. DG_OBSIDIAN priorities update should note this as the next active work.
- **v9.0 AI Workflow Intelligence**: Future milestone, pending v7.0 completion. Not impacted by Phase 20.
- **Canvas breakage is permanent**: v7.0 is a breaking-change milestone. Old .gh files referencing CLASSIFICATOR, VALIDATION RUNS, or old REINSTATE will show missing-component placeholders. Release notes document re-wiring — no backward-compat shims.
</deferred>

---

*Phase: 20-e2e-validation-and-docs*
*Context gathered: 2026-07-05*
