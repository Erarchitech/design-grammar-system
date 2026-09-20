# Phase 39: DesignState Auto-Validation Investigation - Context

**Gathered:** 2026-07-27
**Status:** Ready for planning

<domain>
## Phase Boundary

Deliver an evidence-based answer to "can validation run automatically when a DesignState is captured?" — a comparison of the three trigger architectures (DSAV-01), a working prototype of the chosen one that closes the loop hands-off on live Docker with its guardrails demonstrated (DSAV-02), and an ADR that records the choice, the rejected options, and the follow-up-milestone scope (DSAV-03).

This is an **investigation phase**. Production hardening is explicitly out of scope per REQUIREMENTS.md ("Investigation + prototype + ADR only"). Code ships behind an off-by-default per-project flag.

**Not in scope:** full auto-validation implementation, SWRL rule evaluation server-side, GH component wiring, UI surfaces for auto-runs.

</domain>

<decisions>
## Implementation Decisions

### Carried in from `39-PRE-DECISIONS.md` (not re-litigated)

- **D-A (locked before this discussion):** prototype targets **path (b) — data-service watcher**. Paths (a) GH capture-time hook and (c) Neo4j write-event trigger are compared on paper only.
- **D-B (locked before this discussion):** prototype depth is **spike quality, ADR-scoped**. Guardrails demonstrated, not merely described; code off-by-default; hardening deferred by the ADR.

### Trigger source — what the watcher watches

**Blocking finding that reshapes the roadmap's premise:** there is no DesignState write to observe. `:DesignState` nodes do not exist in the live graph — Phase 29 recorded materializing them as FLAGGED BACKLOG needing explicit human sign-off and its own phase. A DesignState reaches Neo4j only as `statePayloadJson` on a `:ValidationRun`, written by `store_validation_run()` ([data-service/app.py:455](../../../data-service/app.py#L455)), and only via `/validation/publish` — which is *already* a completed validation run. A watcher on "DesignState writes" as literally worded has nothing to watch.

- **D-01:** The capture event is a **`:ValidationRun` row with `status:'captured'`** — `statePayloadJson` populated, no Speckle publish, no verdict yet. The watcher picks up `captured` rows and completes them into real runs. Reuses the existing row shape, key (`{graph, project, runId}`), and properties. **No new label, no schema-propagation sweep** across the ~10 files CLAUDE.md lists. Accepted cost: `status` becomes a small state machine and a "run that hasn't run" is semantically muddy — call this out in the ADR.
- **D-02:** The capture row is written by a **simulated client** — a new `POST /designstate/capture` endpoint plus a curl/pytest driver that posts a real `statePayloadJson` v2 envelope. **No GH component wiring, no live Rhino.** This preserves D-A's entire rationale (avoid the deferred-in-Rhino-UAT pattern of Phase 33 plan 04, Phase 34-02/03, Phase 824) and keeps SC1 fully verifiable on live Docker. The GH-side capture path (DESIGN STATE has no network client today; only VALIDATOR has `ValidationPublishClient`) is **named in the ADR as follow-up milestone scope** — deferred explicitly, not dropped silently.
- **D-03:** The watcher is an **in-process daemon poll thread** started at app startup behind the off-by-default flag, polling Neo4j for `status='captured'` rows past a cursor. Matches data-service's prevailing sync-`def` style; no new dependency; no n8n workflow (that surface is already flagged drift-prone in CLAUDE.md, and Phase 30 has not yet settled whether n8n stays the orchestrator). **The poll body must be factored as a pure function** so tests drive it directly without the thread — deterministic tests plus a genuinely hands-off daemon for SC1.
- **D-04:** DSAV-01's comparison is **measured for path (b), analytic for (a) and (c)**. Real numbers from the prototype: capture→run latency, debounce collapse ratio, runs-per-minute under a rapid-capture burst. Paths (a)/(c) get reasoned estimates anchored to those measurements plus their recorded blockers.

### Validation engine — what actually runs the validation

**Second blocking finding:** data-service cannot evaluate SWRL rules. Rule evaluation is C# (`RuleEvaluator` in DG.Core, driven by the VALIDATOR component); `/validation/publish` only *receives* already-computed `failedRuleIds`. The server-side components that can judge anything are SHACL (`/shacl/validate` → dg-reasoner) and the OWL reasoner.

- **D-05:** The auto-run's verdict comes from the **existing SHACL / dg-reasoner path**. Confirmed fit during scouting: [dg-reasoner/valid_graph_export.py:43](../../../dg-reasoner/valid_graph_export.py#L43) builds its ABox **directly from `run.statePayloadJson`**, so a `status:'captured'` row is SHACL-validatable with **zero new export work**. Fully server-side, no Rhino, no second evaluator. Rejected: driving Grasshopper back through the Phase 33 canvas bridge (deliberately read-only — `CanvasCommandDispatcher`'s handler dictionary means write commands require a deliberate code change; also needs live Rhino, inverting the dependency so "auto" only works while a canvas is open) and porting a minimal SWRL evaluator to Python (creates a second evaluator that can silently disagree with the C# one — the exact divergence hazard Phase 35-12 solved by single-sourcing `GRAMMAR_CITATION_PATTERNS`).
- **D-06:** **The SHACL/SWRL coverage gap is accepted and becomes the headline ADR finding.** The shapes in `ontology/dg-shapes.ttl` target state well-formedness (`DsKindLabelShape`, `PropStateCompletenessShape`, `ObjStateObjectRefShape`, `RunStatusShape`) — *not* design compliance like "height ≤ 75 m". So a SHACL-verdicted auto-run answers "is this captured state well-formed?", not "does this design comply?". The prototype proves the **mechanism** (capture → auto-run → verdict → persist → optionally publish); the ADR states the partition limit plainly and makes **closing the SWRL gap follow-up milestone item #1**. Rejected: adding a Rule-derived design-compliance shape to `dg-shapes.ttl` — `spec/RULE-PARTITION-POLICY.md` governs whether such a rule belongs to SHACL at all, and re-deciding the partition line inside an investigation phase is out of bounds.
- **D-07:** A completed auto-run **derives `ValidStatus` from the SHACL report** — focus-node results mapped back to ObjStates where resolvable — so existing readers (VALIDATION GRAPH component, ui-v2 ModelScreen, `/validation/view/*`) keep working unchanged. It **must also stamp `run.trigger='auto'` and `run.verdictSource='shacl'`** so a SHACL well-formedness verdict can never be misread downstream as a SWRL rule verdict. Provenance-on-generated-artifacts matches the Phase 38 pattern.
- **D-08:** If the SHACL sidecar is down or times out, the row **stays `status:'captured'` and is retried with bounded backoff**, then marked `status:'failed'` with a reason. This deliberately **departs from** the Phase 823 Plan 03 degrade-never-raise precedent (`shacl:{status:'unavailable'}`, run completes anyway): an auto-run that silently completes with no verdict is a worse failure mode than a manual one, because nobody clicked anything to watch it. Requires an attempt counter on the row so retries cannot loop forever.

### Speckle coupling of auto-runs

**Third finding:** `/validation/publish` mints a Speckle version *before* persisting and 404s outright (`SPECKLE_CONFIG_MISSING`) if Speckle isn't configured. Routing auto-runs through it makes every capture a Speckle version — publish-flood is the default behavior, not a risk to mitigate.

- **D-09:** Auto-runs are **persist-only by default; Speckle publish is opt-in** behind a separate per-project flag. This makes SC2's no-flood guarantee **structural rather than a tuning exercise**, and removes the Speckle-config hard dependency so auto-validation works on projects with no Speckle wiring at all.
- **D-10:** **No new persist-without-publish function is needed.** The capture already `MERGE`d the `ValidationRun {graph, project, runId}` row, so completing it is a `SET` of verdict fields + status **in place**. `store_validation_run()` stays byte-for-byte untouched — zero regression surface on the shipped manual publish path (v2.0-era load-bearing code). Rejected: making `publish_result` optional in `store_validation_run` (edits the shipped path, makes every Speckle field conditionally null for readers that assume otherwise) and a parallel `store_auto_validation_run` (duplicated MERGE that can drift).
- **D-11:** The prototype **demos the publish leg exactly once** with the auto-publish flag on — gives SC1 its literal "and (if enabled) publishes to Speckle" evidence and produces one **real measured** Speckle-noise data point for DSAV-01 instead of an estimate. Everything else runs persist-only. Requires a working Speckle config in the dev stack for that single run.
- **D-12:** Auto-runs **stay visible in the normal run list** (`/validation/runs/{project}`, VALIDATION GRAPH component, ui-v2 Model screen); `run.trigger='auto'` is the only distinction, and the off-by-default flag means no existing project sees them unless deliberately enabled. Filtering/badging is a new capability for the follow-up milestone — and the UI gate already returned `frontend: false` for this phase. **Run-list pollution is recorded in the ADR as a known consequence.**

### Guardrail state

- **D-13:** Config lives on an **`IntegrationConfig` row with `provider:'AutoValidation'`**. The node is already keyed `{graph, provider, project}` ([data-service/app.py:430](../../../data-service/app.py#L430)), so a second provider row reuses the exact label, merge pattern, and per-project scoping with **zero change to the Speckle config shape** and no new label to propagate. Absent row = disabled, which is the correct default (`_auto_configure_integration`'s implicit-create precedent must NOT be extended here). Rejected: adding fields to the `provider:'Speckle'` row — that welds auto-validation config to Speckle config, contradicting D-09; and a `DG_DATA_DIR` settings file (the `/llm/settings`, `/reasoner/settings` precedent is global, but DSAV-03 requires per-project).
- **D-14:** Debounce semantics are **trailing-edge coalesce — newest wins**. Within the window only the newest captured row per project is validated; superseded rows are marked **`status:'superseded'`, not deleted**. Matches what an architect actually wants (validate where I ended up, not every slider twitch), leaves an auditable trail of what was skipped, and yields a directly measurable collapse ratio for SC2 (N captures in → 1 run out). Rejected: leading-edge (verdict describes a state already moved past) and delay-and-run-all (converts a burst into a backlog instead of suppressing it).
- **D-15:** Runtime counters (debounce timer state, per-project rate-limit window) are held **in-memory in the watcher process**, keyed by project. No write amplification against the very database the watcher polls; single-instance data-service means there is no multi-worker case to justify shared state yet. **Restart resets the window — record this as an explicit ADR line** for the follow-up milestone rather than solving it speculatively.
- **D-16:** **Artifact placement:** the DSAV-01 investigation note (comparison table, measurements, recorded blockers) lives at `.planning/milestones/v9.0-phases/39-designstate-auto-validation-investigation/` where researcher and planner already read; the DSAV-03 ADR is filed to `DG_OBSIDIAN/knowledge/decisions/` per the roadmap deliverable and the CLAUDE.md session protocol, cross-linked to the note. Phase 40's deliverables expect the Phase 39 decision already filed in the vault.

### Claude's Discretion

None — every question in this discussion was answered with an explicit choice.

### Open for the planner (NOT decided here)

- **Capture-endpoint authentication is unresolved and is the highest-severity item in the threat model.** `POST /designstate/capture` is a new unauthenticated write-amplifier endpoint: an anonymous POST can enqueue a validation run and (with publish enabled) a Speckle version. The security contribution is active at ASVS L1 with block-on-`high`, so **plans MUST carry a `<threat_model>` block** covering at minimum: authentication of the capture endpoint (candidate: reuse the Phase 825 project-scoped connector token, already issued to GH clients), per-project scoping so one project cannot enqueue captures for another, rate-limit bypass, and publish-flood. The user deliberately left the auth mechanism to planning rather than locking it in discussion.

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Phase inputs
- `.planning/milestones/v9.0-phases/39-designstate-auto-validation-investigation/39-PRE-DECISIONS.md` — D-A (path (b) prototype) and D-B (spike depth, ADR-scoped), plus the Perplexity/UI-gate/security notes. Locked before this discussion; do not re-litigate.
- `.planning/ROADMAP.md` § Phase 39 — deliverables and the three success criteria
- `.planning/REQUIREMENTS.md` § DSAV (lines 102–106, 127, 170) — DSAV-01/02/03 and the explicit out-of-scope boundary

### Rule ownership and schema
- `spec/RULE-PARTITION-POLICY.md` — **normative** on which validation system (SWRL VALIDATOR vs. SHACL) owns a given rule category. Load-bearing for D-05/D-06: consult before touching a shape or claiming rule coverage.
- `spec/DATABASE.md` — ValidGraph schema, `statePayloadJson` / `rulesJson` / `shaclReportJson` as schema-propagation surfaces
- `CLAUDE.md` § Graph Schema v4 + § Schema Change Propagation — the ~10-file sweep D-01 and D-13 are explicitly designed to avoid triggering
- `ontology/dg-shapes.ttl` — the SHACL shapes; D-06's coverage-gap finding rests on what these actually target

### Code the prototype touches
- `data-service/app.py:455` `store_validation_run()` — the row shape D-01 reuses; **must stay untouched** per D-10
- `data-service/app.py:1818` `publish_validation()` — the Speckle-before-persist ordering and `SPECKLE_CONFIG_MISSING` 404 that motivate D-09
- `data-service/app.py:430` `upsert_integration_config()` / `data-service/app.py:415` `get_integration_config()` — the `{graph, provider, project}` key shape D-13 reuses
- `data-service/app.py:1796` `_persist_shacl_report()` and `data-service/app.py:1749` `_call_shacl_validate()` — the Phase 823 SHACL proxy path D-05 builds on and D-08 deliberately departs from

> **Line numbers re-verified 2026-07-27 at plan time.** The four entries above were stale by ~50–100 lines as originally written; the PLAN.md files cite the corrected values throughout. Re-derive with `grep -n "^def " data-service/app.py` if `app.py` shifts again.
- `dg-reasoner/valid_graph_export.py:43` — ABox built from `run.statePayloadJson`; the confirmation that D-05 needs no new export work

### Prior decisions this phase depends on
- `.planning/STATE.md` § Accumulated Context — Phase 29's "FLAGGED BACKLOG: materializing first-class `:DesignState` nodes needs explicit human sign-off and its own phase" (the reason D-01 exists) and Phase 13's `ValidStatus` Boolean-list contract (the reason D-07 exists)
- `.planning/milestones/v9.0-phases/` / `.planning/milestones/v9.0-phases/33-dg-canvas-bridge/` — Phase 33 Plan 01's read-only `CanvasCommandDispatcher` decision, which rules out the bridge-driven option in D-05

### Output destinations
- `.planning/milestones/v9.0-phases/39-designstate-auto-validation-investigation/` — DSAV-01 investigation note (per D-16)
- `DG_OBSIDIAN/knowledge/decisions/` — DSAV-03 ADR (per D-16); see `DG_OBSIDIAN/00-home/index.md` for vault conventions

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- **`ValidationRun` node + `store_validation_run()` row shape** — the capture row (D-01) and the completed auto-run reuse it wholesale; `status`, `ValidStatus`, `SendStatus`, `statePayloadJson`, `shaclReportJson` all already exist.
- **`IntegrationConfig {graph, provider, project}`** — provider-scoped key means auto-validation config is an additive second row, not a schema change (D-13).
- **`_call_shacl_validate()` + `_persist_shacl_report()`** — the entire SHACL round-trip already exists on the publish path; the watcher calls the same helpers.
- **`dg-reasoner/valid_graph_export.py`** — reads `run.statePayloadJson` directly, so it validates a captured row with no modification.
- **Phase 825 project-scoped connector token** (`/connectors/heartbeat`) — the strongest existing candidate for authenticating `POST /designstate/capture`; already issued to GH clients and already project-scoped.

### Established Patterns
- **Sync-`def` FastAPI throughout** — sync `httpx` with explicit `httpx.Timeout`, no async job runner anywhere in data-service. D-03's daemon thread respects this; do not introduce asyncio.
- **Parameterized `MERGE`/`SET`, never string-interpolated Cypher** — `_persist_shacl_report` is the template.
- **Degrade-never-raise around the SHACL sidecar** (Phase 823 Plan 03) — D-08 deliberately departs from it for auto-runs; the departure must be justified in the plan, not applied silently.
- **Provenance properties on generated artifacts** (Phase 38 pattern) — `trigger` / `verdictSource` in D-07 follow it.
- **Single-source guardrail logic** (Phase 35-12) — the reason a second SWRL evaluator was rejected in D-05.

### Integration Points
- **New:** `POST /designstate/capture` — writes the `status:'captured'` row. The phase's only new public surface, and the threat model's primary target.
- **New:** watcher poll thread, started at app startup, gated by the per-project `provider:'AutoValidation'` flag; poll body factored as a pure function.
- **Modified in place:** the captured `ValidationRun` row is completed via `SET` — no other write path changes.
- **Unchanged:** `/validation/publish`, `store_validation_run()`, `ontology/dg-shapes.ttl`, the canvas bridge, all C#.

### Environment constraints (evidence for DSAV-01's rejected options)
- `neo4j:5.26` **Community** ([neo4j/Dockerfile](../../../neo4j/Dockerfile)) — Neo4j CDC is not a Community feature.
- **APOC is allowlisted but never installed** — `docker-compose.yml` sets `NEO4J_dbms_security_procedures_unrestricted/allowlist` to `n10s.*,apoc.*`, but the Dockerfile fetches only the neosemantics jar. Path (c) would require installing APOC and enabling `apoc.trigger.enabled` in `apoc.conf`.
- Per Perplexity research (2026-07-27, orchestrator-run): the reliable APOC-trigger pattern for external side effects is **trigger → outbox node → external worker → HTTP**, which structurally collapses into path (b). Sources: [Neo4j APOC triggers](https://neo4j.com/docs/apoc/current/background-operations/triggers/), [Neo4j CDC docs](https://neo4j.com/docs/cdc/current/), [Operations Manual — editions](https://neo4j.com/docs/operations-manual/current/introduction/). This is the evidence backing D-04's "analytic + recorded blockers" treatment of path (c) — the researcher does not need to re-derive it (and cannot reach the capital-`P` Perplexity server from a subagent).

</code_context>

<specifics>
## Specific Ideas

- **"N captures in, 1 run out"** is the shape of SC2's evidence — the debounce collapse ratio must be a measured number, not a described design (D-14).
- Superseded captures are **marked, not deleted** — the skipped-work trail is itself part of the investigation's evidence.
- The ADR's rejected-options section should carry the *empirical* blockers found here (Community edition, APOC absent, bridge read-only by design, no server-side SWRL evaluator), not generic trade-off prose.
- The single publish-enabled run is deliberate: one real Speckle version beats three columns of estimated noise.

</specifics>

<deferred>
## Deferred Ideas

- **GH-side capture wiring** — a network client on DESIGN STATE (or a CAPTURE toggle on VALIDATOR) so a real canvas capture fires the loop. Named in the ADR as follow-up milestone scope; deliberately excluded to keep the prototype Rhino-free (D-02).
- **Closing the SWRL coverage gap** — bridge write-command or headless evaluator so auto-validation reaches design-compliance rules, not just state well-formedness. **ADR follow-up item #1** (D-06).
- **First-class `:DesignState` nodes in ValidGraph** — still the Phase-29-flagged backlog item needing explicit human sign-off and its own phase. D-01 routes around it rather than resolving it.
- **Design-compliance SHACL shapes** — blocked on `spec/RULE-PARTITION-POLICY.md`; re-deciding the SWRL/SHACL partition line does not belong in an investigation phase.
- **UI treatment of auto-runs** — filtering or badging `trigger:'auto'` runs in ui-v2 / VALIDATION GRAPH. Follow-up milestone; UI gate returned `frontend: false` for this phase (D-12).
- **Guardrail durability across restarts** — persisting debounce/rate-limit windows so a data-service restart cannot reopen the floodgate. Explicit ADR line, not prototype work (D-15).
- **Retention cap on auto-runs** — pruning older auto-runs per project. Considered during the run-list discussion; a fourth guardrail beyond the three DSAV-03 names, and pruning is a destructive write.
- **Empirically verifying path (c)'s blocker** — actually installing APOC + `apoc.trigger` to convert "looks foreclosed" into a tested verdict. Considered and declined as a detour outside the chosen path (D-04).

</deferred>

---

*Phase: 39-designstate-auto-validation-investigation*
*Context gathered: 2026-07-27*
