# Pitfalls Research

**Domain:** Bolting real OWL 2 DL reasoning (HermiT/Pellet) + SHACL onto a Neo4j-native property-graph ontology with an existing bespoke SWRL validator; changing a shipped Grasshopper component's credential inputs
**Researched:** 2026-07-11
**Confidence:** MEDIUM (web-sourced OWL/RDF/SHACL claims, cross-checked across independent searches) / HIGH (project-specific facts — read directly from `DG/src/DG.Grasshopper/Components/ConnectorComponent.cs` and `docs/RELEASE-NOTES-v7.0.md`)

> Note: this file supersedes the prior (2026-05-11) v3.0-era pitfalls research, which covered a component plan since superseded per `.planning/PROJECT.md`'s Out of Scope section ("v3.0 Phases 8–12 component plan... superseded 2026-07-02 by the GH_DesignGrammars.pdf schema"). This version researches the active v8.2 milestone: CONNECTOR credential integration and the OWL 2 DL + SHACL reasoning engine.

## Critical Pitfalls

### Pitfall 1: Property-graph → RDF translation silently drops or distorts semantics

**What goes wrong:**
Neo4j edge properties, multi-valued node properties, and n-ary relationships (e.g. `Atom -ARG-> Var` with a `pos` property, `HAS_BODY`/`HAS_HEAD` with `order`) have no direct RDF triple equivalent — RDF can only attach that kind of qualifier via reification or extra blank nodes, and a hand-rolled Neo4j→RDF exporter easily drops the qualifier silently (the triple `atom -refersTo-> class` gets exported, but `pos`/`order` — which encode SWRL body/head sequencing — do not, unless explicitly modeled). Because the failure is silent (the export succeeds, produces valid Turtle/OWL, and the reasoner runs "fine"), it is discovered only when a reasoning result depends on ordering or edge-qualifier data that never made it into the RDF graph.

**Why it happens:**
LPGs (property graphs) do not carry OWL's model-theoretic semantics or open-world assumption, and there is no standardized LPG↔OWL mapping — every project hand-rolls its own, and hand-rolled exporters optimize for "gets a consistent ontology out" rather than "preserves every property-graph fact." This project's `DesignGrammar-V7.owl` is already a maintained-separately export (see `ontology/export_to_markdown_v7.py`), not a live projection of the Neo4j graph, so the translation-fidelity problem is not hypothetical — it already exists as a batch/static artifact and would need to become either a live incremental exporter or an accepted staleness window.

**How to avoid:**
- Write an explicit LPG→OWL mapping spec (which Neo4j labels/props/rel-types map to which OWL classes/ObjectProperties/DatatypeProperties/reified axioms) before writing exporter code — do not let the mapping emerge implicitly from exporter code.
- For any edge property that carries meaning DL reasoning needs (`order`, `pos`), either reify explicitly (n-ary relation pattern) or exclude it from the reasoning scope and document that exclusion — never let it drop silently.
- Add a round-trip fidelity check: export a known Neo4j fixture subgraph, reason over it, and assert the reasoner's view of key facts (class memberships, property assertions) matches hand-computed expectations from the original graph.
- Treat `DesignGrammar-V7.owl` (or its successor) as either the single source of truth that Neo4j is generated *from*, or explicitly as a downstream, possibly-stale export used only for TBox/schema reasoning — never let both directions of sync exist implicitly.

**Warning signs:**
- Reasoner "passes" (ontology reported consistent) but a rule author's SWRL atom order (`ARG.pos`) or body/head order (`HAS_BODY.order`/`HAS_HEAD.order`) produces different behavior in VALIDATOR than in the OWL reasoning result for the same rule.
- Exporter script has no test asserting a specific edge-property fact survived translation.

**Phase to address:**
Reasoning-stack architecture decision phase (the phase that decides the RDF/OWL integration path against the Neo4j-encoded ontology per PROJECT.md's stated v8.2 goal) — the mapping spec must exist before any HermiT/Pellet wiring phase starts.

---

### Pitfall 2: Reasoner timeout/blowup treated as an edge case instead of a designed-for constraint

**What goes wrong:**
OWL 2 DL reasoners (HermiT, Pellet) can blow up in both memory and time on ontologies with cyclic axioms, nominals, or large ABoxes — published reasoner competition results show reasoners timing out or exhausting memory on ontologies with large cyclic axiom sets, and HermiT specifically underperforms Pellet on ABox-heavy ontologies with nominals because HermiT is not optimized for ABox reasoning. If the reasoning call is wired synchronously into the rule-authoring or validation path (the natural place to put it, given VALIDATOR's synchronous evaluate-then-publish pattern), a single pathological rule set or a growing ABox (every ObjState/PropState eventually referenced as an individual) can hang the UI or the Grasshopper solve.

**Why it happens:**
Teams new to DL reasoners assume "consistency check" is cheap because it sounds like schema validation. In reality, DL reasoning complexity is worst-case exponential (SHOIN/SROIQ), and this project's rule corpus grows unboundedly over the project's life (every architect-authored rule adds Atoms/Vars; nothing currently caps ontology size).

**How to avoid:**
- Never call the reasoner synchronously in a request/response or Grasshopper-solve path. This project already has the pattern for exactly this problem — `ConnectorComponent` runs `TryConnectAsync` on a background `Task` and re-triggers `ExpireSolution` on completion rather than blocking `SolveInstance`. Reuse that async-task-plus-poll pattern for reasoner invocation instead of inventing a new one.
- Set an explicit, configurable timeout ceiling per reasoning call, with a "reasoning timed out / result unknown" outcome distinct from both "consistent" and "inconsistent" — never let a timeout silently present as either verdict.
- Separate TBox-only reasoning (run on every ontology edit — small, must stay fast) from ABox/instance reasoning (run on-demand or batched — large, expected to be slower); do not force both into the same request.
- Consider ELK (mentioned in PROJECT.md as an optional pre-classifier) specifically to absorb the cheap, frequent TBox-consistency checks and reserve HermiT/Pellet for cases ELK's OWL EL profile cannot express.

**Warning signs:**
- Reasoning is invoked inline inside a component's `SolveInstance` or a synchronous FastAPI request handler with no timeout parameter.
- No distinction in the API/UI between "reasoner says consistent," "reasoner says inconsistent," and "reasoner did not finish."

**Phase to address:**
OWL 2 DL reasoning integration phase — the phase implementing HermiT/Pellet wiring; timeout/async design must be part of the phase's acceptance criteria, not a follow-up hardening pass.

---

### Pitfall 3: Conflating TBox consistency with ABox/instance (design) validation

**What goes wrong:**
"Ontology reasoning is green" gets reported to the architect as "your design is valid," when TBox consistency (is the *schema* — the classes, property domains/ranges — logically coherent) and ABox/instance validation (does *this specific design's data* — this building's height, this object's class assertions — satisfy the constraints) are different reasoning tasks with different complexity, different triggers, and different failure meanings. TBox reasoning should be cheap and can run on every rule-authoring edit; ABox reasoning is data-dependent, scales with the number of captured DesignStates/PropStates, and must be re-run whenever instance data changes, not just when the ontology schema changes.

**Why it happens:**
The word "consistency" is used for both, and a v8.1 Reasoner selector UI already exists that just persists a HermiT/Pellet *choice* without distinguishing what kind of check that choice will perform (`ReasonerScreen.jsx` comment: "selection is persisted server-side but does not yet drive validation" — i.e. today it's a no-op preference, not a wired check of any kind). If v8.2 wires it in without first deciding TBox vs ABox scope, the natural failure mode is wiring only TBox reasoning (cheap, demoable) and letting the UI imply it also validates individual designs.

**How to avoid:**
- Explicitly name and separately surface two checks in the UI/API contract: "ontology schema consistency" (TBox — class satisfiability, property domain/range coherence, run at rule-authoring time per PROJECT.md's stated scope) and "design/instance validation" (ABox — the actual VALIDATOR/SHACL layer's job, run at design-check time).
- Do not let OWL reasoning replace or shadow VALIDATOR's existing SWRL-based instance validation — PROJECT.md already scopes OWL reasoning to "rule-authoring time" (TBox) and SHACL/SWRL to "data-level design-rule/instance validation" (ABox). Keep that boundary explicit in the implementation, not just the planning doc.
- Reflect the TBox/ABox distinction in whatever UI shows reasoning status — separate "Ontology OK" (TBox) from "Design OK" (ABox/SHACL/SWRL) badges, never a single merged status.

**Warning signs:**
- A single boolean/status field in the API response is used for both "reasoner ran without error" and "this design passes constraints."
- Reasoner invocation happens once at rule save and its result is cached and shown at design-validation time without re-running against current instance data.

**Phase to address:**
Reasoning-stack architecture decision phase (scope definition) and OWL 2 DL reasoning integration phase (implementation) jointly — the scope boundary must be a written decision before code, per this project's existing Key Decisions table convention in PROJECT.md.

---

### Pitfall 4: SWRL VALIDATOR and SHACL disagree with no defined precedence

**What goes wrong:**
SHACL validates under the closed-world assumption (CWA) — anything not explicitly asserted is treated as false/violated — while SWRL (like the OWL/DL layer it typically sits alongside) is open-world (OWA) — absence of a fact means "unknown," not "false." The existing VALIDATOR is *also* effectively closed-world in practice (it evaluates concrete Cypher-sourced bindings, not open-world entailment), but it is hand-built regex/Cypher logic, not a standard SHACL engine, so its closed-world behavior and pySHACL/TopBraid's closed-world behavior are not guaranteed to agree on edge cases (missing properties, cardinality on absent data, multi-valued properties). Two validation layers that both claim to check "is this design compliant" can produce different pass/fail verdicts for the same design state with no documented rule for which one wins.

**Why it happens:**
SHACL and SWRL/VALIDATOR are reached for the same underlying need (constraint checking) via different technical justifications (SHACL = "the standard, get it for free"; SWRL VALIDATOR = "already shipped, avoid vendor OWL libs" per this project's existing Key Decision). Teams add the second system to get standards compliance or authoring convenience without first deciding whether the two systems check the *same* rule set (duplication) or *disjoint* rule sets (partition), and without deciding what happens when both check the same rule and disagree.

**How to avoid:**
- Decide and document, before implementation, whether SHACL and SWRL VALIDATOR check the **same** rules (in which case one must be authoritative and the other advisory/redundant) or **partitioned** rule categories (e.g. SHACL for structural/cardinality/datatype shape constraints, SWRL VALIDATOR for the project's existing domain-specific compliance rules like `R_URB_HEIGHT_MAX_75_V`). Partitioning by rule *kind* avoids double-authoring and avoids precedence ambiguity entirely — it is the cheaper and safer default versus building an arbitration layer.
- If any overlap is unavoidable, define an explicit precedence rule (e.g. "SWRL VALIDATOR result is authoritative for publish/Speckle color-coding; SHACL result is advisory-only, surfaced as a separate warning") and encode it, don't leave it as tribal knowledge.
- Never author the same business rule twice in both SWRL and SHACL — if a rule genuinely needs both structural (SHACL) and domain-logic (SWRL) checking, split it into two distinct, separately-named rules rather than duplicating one rule's intent across two languages, so a disagreement is diagnosable (name tells you which layer is which) instead of silent (both call themselves "the height rule").
- Do not use SHACL rules/SHACL-AF that write inferred triples back into the reasoning graph without deciding which world-assumption governs the resulting mixed system — that combination is a genuinely unresolved semantics problem in the field, not just an engineering detail to patch later.

**Warning signs:**
- Two different "pass/fail" badges for the same design state in the UI, with no visible label distinguishing which validation layer produced which.
- A rule exists in both a SWRL atom chain (Neo4j Metagraph) and a SHACL shape file with overlapping subject/predicate coverage.
- No test in the codebase exercises "SHACL says pass, SWRL VALIDATOR says fail" (or vice versa) as an explicit scenario.

**Phase to address:**
SHACL validation layer phase — the phase that "investigates SHACL alongside the existing SWRL-based VALIDATOR" per PROJECT.md must produce the partition/precedence decision as a Key Decision entry, not just a working prototype.

---

### Pitfall 5: Unique Name Assumption gap causes silent over-merging or under-merging of individuals

**What goes wrong:**
OWL does not assume the Unique Name Assumption (UNA) by default — two differently-IRI'd individuals are not automatically inferred distinct unless explicitly declared `owl:differentFrom` (or the ontology uses cardinality constraints that force distinctness). Neo4j nodes are distinct by construction (each has its own internal identity/`iri`/`Atom_Id`/`StateId`), but once exported to RDF and fed to a DL reasoner, that Neo4j-native distinctness is not automatically preserved as OWL distinctness — a reasoner is logically permitted to treat two individuals as possibly-identical unless told otherwise, which can produce reasoning results (e.g. class-membership inferences, cardinality violations/non-violations) that don't match what the property graph "obviously" shows.

**Why it happens:**
This is one of the most common surprises for teams moving from a graph database (where node identity is intrinsic and closed) to OWL/DL (where identity is an open, provable fact) — Pellet in particular was built to do ABox reasoning specifically *without* UNA, meaning it will actively try same-as inference unless constrained.

**How to avoid:**
- When exporting Neo4j individuals to OWL, either declare all exported individuals pairwise `owl:differentFrom` in bulk (feasible for TBox-scale exports, expensive at ABox scale) or use `owl:AllDifferent`/`owl:distinctMembers` for the export batch, or configure the reasoner's UNA-emulation option if available (HermiT/Pellet both support this).
- Document explicitly which world's identity rules apply to which layer: Neo4j (implicit UNA, always), OWL/DL reasoning (no UNA unless declared), so implementers don't assume DL "knows" what Neo4j already guarantees.

**Warning signs:**
- Individual/instance-level reasoning results (ABox) that seem to merge or conflate two design states/objects that are clearly distinct in Neo4j.
- No `owl:differentFrom`/`AllDifferent` axioms anywhere in the exported ontology despite it having individuals.

**Phase to address:**
Reasoning-stack architecture decision phase — UNA handling must be part of the LPG→OWL mapping spec from Pitfall 1, not an afterthought discovered during ABox reasoning debugging.

---

### Pitfall 6: CONNECTOR credential-input change breaks saved .gh canvases without a migration path (this project's established breaking-change pattern applies directly)

**What goes wrong:**
`ConnectorComponent.cs` currently exposes 6 inputs in this exact order: `Neo4jURI` (item 0), `Neo4jUser` (1), `Neo4jPassword` (2), `Database` (3), `PROJECT NAME` (4), `Connect` (5) — with `GH_InputParamManager` reading positionally via `da.GetData(0..5, ...)`. Grasshopper resolves saved-canvas wire connections by parameter **name and position**, not by semantic meaning. Introducing a platform-issued credential (e.g. a single opaque token/handle replacing the three raw-credential inputs, or an additional input inserted before existing ones) shifts every subsequent `da.GetData(n, ...)` index and every downstream wire target — this is precisely the class of change this project has already classified as breaking (see `docs/RELEASE-NOTES-v7.0.md`'s CONNECTOR section: even a same-GUID, port-*rename*-only change ("Before/After" wiring diagrams for ServerURI→Neo4jURI etc.) was called out explicitly with a port-mapping table in a dedicated release-notes document). Silently shipping the change without following that pattern will reproduce exactly the "disconnected wires where port names changed" symptom the v7.0 notes describe for CONNECTOR, at production scale, since v8.0/v8.1 are already live with saved canvases depending on the current 6-input contract.

**Why it happens:**
"Just add a credential input" or "swap 3 raw fields for 1 token field" looks like a small, additive change from the component-code side, but Grasshopper's canvas persistence model makes any input reordering, removal, or type change (text → generic credential-handle parameter) a breaking change regardless of how small the code diff is. The team's own precedent (VALIDATION RUNS getting a new GUID; CLASSIFICATOR removed with no replacement GUID; CONNECTOR's v7.0 port renames requiring an explicit before/after table despite keeping the same GUID) shows this project already knows the cost — the risk is specifically *forgetting to apply the known pattern* on this specific change because it "just" touches credentials.

**How to avoid:**
- Treat this exactly like the v7.0 CONNECTOR port rename: **keep the same ComponentGuid** (`24E78A17-4533-44E7-8931-1224A70A1B36`) if at all possible so the component itself still loads on old canvases (v7.0's precedent: CONNECTOR kept its GUID across the ServerURI→Neo4jURI rename), but treat the port-level change as fully breaking and require a release-notes entry with a Before/After wiring diagram and a port-mapping table, following the exact structure of the v7.0 CONNECTOR section.
- Prefer **additive, backward-compatible** port design over replacement: add a new optional input (e.g. `PlatformCredential`) alongside the existing 4 raw-credential inputs rather than removing `Neo4jURI`/`Neo4jUser`/`Neo4jPassword`/`Database`. Wire the component's internal logic to prefer the platform credential when supplied and fall back to raw fields when not — this lets old canvases keep working unmodified while new canvases opt in, avoiding a breaking release entirely. This project's own experience (VALIDATOR's port table explicitly marks preserved "non-overlapping extras" as the pattern to keep, vs. removed/replaced ports as the pattern that breaks canvases) supports additive-over-replacement as the lower-risk default.
- If a token/handle *must* replace raw fields (e.g. for security reasons — raw passwords should not be typed into every canvas), stage it as a deprecation: ship the new input additively first, mark the raw-credential inputs deprecated in a release note, and only remove them in a later major version with its own GUID/port migration table — never both add and remove credential inputs in the same release.
- If any positional index shifts anyway, write the GUID/port migration table (old port → new port, old GUID → new GUID or "unchanged") into a new `docs/RELEASE-NOTES-v8.2.md` before merging, following the v7.0 document's structure exactly (Breaking Changes section, ASCII before/after wiring, port-mapping table, Appendix GUID Reference).

**Warning signs:**
- A PR touches `RegisterInputParams` order/count in `ConnectorComponent.cs` with no corresponding `docs/RELEASE-NOTES-v8.2.md` entry.
- `ConnectorComponentPortContractTests.cs` (the existing test file guarding CONNECTOR's port contract) is modified to match new behavior instead of failing and prompting a migration-table conversation.
- No entry added to PROJECT.md's Key Decisions table documenting whether the change is additive or breaking and why.

**Phase to address:**
CONNECTOR component credential-integration phase — must explicitly decide additive-vs-breaking before touching `RegisterInputParams`, and must produce a release-notes/migration-table artifact if any port shifts, mirroring the v7.0 precedent this project already established for itself.

---

### Pitfall 7: Platform-issued credential token treated as "just another string input," inheriting raw-credential's weak handling

**What goes wrong:**
The current `ConnectorComponent` stores raw `Neo4jPassword` as a plain-text default value (`"12345678"`) baked into the component's field initializer and echoed straight through `WithStatus`/`BuildRequestKey` (which concatenates URI/user/password/database/project into a cache key). If a platform-issued credential (a bearer token, API key, or similar) is added as "just another text input" using the same pattern, it inherits the same weaknesses at a *worse* blast radius: a long-lived platform credential embedded in a saved `.gh` file is more dangerous to leak than a local Neo4j dev password, because it may grant access to the whole platform's connector fleet, not just one local database, and `.gh` files are commonly shared between colleagues or checked into version control without anyone treating them as secrets.

**Why it happens:**
The existing CONNECTOR code has no secret-handling special-casing today (raw password is a plain `AddTextParameter`), so the path of least resistance for adding a platform credential is to copy that pattern rather than introduce credential-specific handling (masking, short-lived tokens, no-plaintext-in-cache-key).

**How to avoid:**
- Do not put the platform credential's raw value into `BuildRequestKey` or any other string that gets logged, cached as a dictionary key, or included in error messages — use an opaque reference/hash, not the credential value itself.
- Design the platform credential input to accept a short-lived reference (e.g. a credential *ID* minted from the v8.1 Connectors screen, per PROJECT.md's stated design) rather than the raw secret itself — the actual secret should stay server-side (in `data-service/connectors.py`'s existing credential store), with the Grasshopper component only ever holding an opaque handle.
- If the raw-credential inputs remain (per the additive approach in Pitfall 6), do not silently prefer whichever is non-empty without validating — an empty platform-credential field falling through to a stale hardcoded password default is a silent security regression, not graceful degradation.

**Warning signs:**
- The new credential input is typed as `AddTextParameter` with a non-empty default value (mirrors the exact anti-pattern already present for `Neo4jPassword`).
- Credential value appears in `BuildRequestKey`, `Message`, or any Grasshopper component tooltip/status string.

**Phase to address:**
CONNECTOR component credential-integration phase — should include an explicit security review step given the existing plaintext-password precedent in the same file.

---

## Technical Debt Patterns

| Shortcut | Immediate Benefit | Long-term Cost | When Acceptable |
|----------|--------------------|-----------------|------------------|
| Reuse `DesignGrammar-V7.owl`'s existing static export script as the reasoning input instead of building a live/incremental Neo4j→RDF exporter | Fast to wire, no new export infrastructure | Reasoning runs against a stale snapshot; rule-authoring UI can show "consistent" while the live graph has since drifted | Only for the first reasoning-integration milestone, with an explicit "export freshness" indicator in the UI and a documented re-export trigger (e.g. on every rule save) |
| Skip UNA declarations (Pitfall 5) for the first reasoning pass | Simpler exporter, faster to ship | Silent same-as merging risk in ABox reasoning results that surfaces only when instance-level checks are added later | Acceptable only while reasoning scope is TBox-only (per Pitfall 3's scoping); must be closed before any ABox/instance reasoning ships |
| Ship SHACL and SWRL VALIDATOR covering overlapping rule sets "for now, sort out precedence later" | Faster SHACL prototype, no upfront rule-partitioning design work | Silent double-authoring and unpredictable dual-verdict UX (Pitfall 4) that gets progressively more expensive to unwind as more rules accumulate in both systems | Never — partition rule categories before either system ships more than a demo rule |
| Add platform-credential input additively without removing raw-credential inputs, "clean up later" | Zero canvas breakage (Pitfall 6's recommended default) | Two credential paths to maintain and secure indefinitely; raw fields remain a lingering plaintext-secret surface (Pitfall 7) | Acceptable long-term if the raw fields are clearly deprecated in docs and monitored for usage, not merely "acceptable for now" |

## Integration Gotchas

| Integration | Common Mistake | Correct Approach |
|-------------|-----------------|-------------------|
| Neo4j → RDF/OWL export | Hand-roll a one-off exporter with no explicit mapping spec, discover missing edge-property semantics only when a reasoning result looks wrong | Write and review the LPG→OWL mapping spec first (Pitfall 1); add round-trip fidelity tests against known fixtures |
| HermiT / Pellet reasoner invocation | Call synchronously inside a request/Grasshopper-solve path with no timeout | Reuse `ConnectorComponent`'s existing async-task-plus-`ExpireSolution` pattern; enforce a configurable timeout with a distinct "timed out" result state (Pitfall 2) |
| SHACL engine (pySHACL / TopBraid) alongside SWRL VALIDATOR | Let both check the same rules with no documented precedence | Partition rule categories (structural/shape → SHACL; domain compliance → SWRL VALIDATOR) or, if overlap is unavoidable, document and enforce an explicit precedence (Pitfall 4) |
| Grasshopper CONNECTOR ↔ platform Connectors screen (credential minting) | Treat the new credential input as a drop-in replacement for existing raw-credential ports, shifting positional indices | Add additively (new optional input, old inputs preserved) or follow the full v7.0 release-notes/migration-table pattern if replacement is unavoidable (Pitfall 6) |
| Reasoner selection UI (`ReasonerScreen.jsx`) → actual reasoning wiring | Wire real HermiT/Pellet calls behind the existing "selection persisted, not yet driving validation" UI without updating its copy/state, so users can't tell placeholder from live | Update the UI's status language and add a visible "TBox schema check" vs "design validation" distinction the moment real wiring lands (Pitfall 3) |

## Performance Traps

| Trap | Symptoms | Prevention | When It Breaks |
|------|----------|------------|-----------------|
| Synchronous reasoner call in the rule-authoring or validation request path | UI hangs or times out on rule save/design validate; Grasshopper solve freezes | Async task pattern with timeout ceiling (Pitfall 2) | Breaks as soon as the rule corpus or ABox (captured DesignStates) grows past whatever small fixture was used in dev testing — not a fixed threshold, but the pattern is fragile from day one |
| ABox reasoning re-run on every minor design-state change | Reasoning latency grows with number of captured ObjState/ParamState/PropState nodes referenced as individuals | Scope ABox reasoning to on-demand/batched triggers, not every Neo4j write (Pitfall 3) | Becomes noticeable once a project accumulates enough validation runs that the exported ABox is no longer trivially small — track export size, not just rule count |
| Cyclic axioms in the exported ontology (e.g. from bidirectional Neo4j relationship modeling) | Reasoner memory usage balloons or reasoner never returns | Detect and flag cyclic class hierarchies before sending to the reasoner; consider ELK pre-classification to catch cheap inconsistencies first | Reasoner competition data shows this is a known failure mode even for moderately sized ontologies, not just huge ones — test with the project's actual rule corpus shape, not a toy ontology |

## Security Mistakes

| Mistake | Risk | Prevention |
|---------|------|------------|
| Platform credential token embedded as plain text in `.gh` file (same pattern as today's raw password default) | Token leaks via file-sharing/version control grant platform-wide access, not just local dev DB access | Use short-lived credential references/IDs, not raw secret values, in the component's persisted fields (Pitfall 7) |
| Credential value included in cache/request keys (`BuildRequestKey` pattern) or status/error messages | Secret exposure via logs, error dialogs, or Grasshopper component tooltips | Hash or reference credentials in any string that could be logged or displayed; never concatenate raw secret into a key |
| SHACL/SWRL reasoning results exposing internal rule/ontology structure in error messages surfaced to architects | Information disclosure about proprietary rule logic or ontology internals to end users | Keep reasoner/validator diagnostic detail server-side; surface only user-actionable summaries to the Grasshopper/UI layer, consistent with this project's existing ErrorMessageTemplates What+Where+How-to-fix pattern |

## UX Pitfalls

| Pitfall | User Impact | Better Approach |
|---------|--------------|-------------------|
| Reasoner selector UI (already live since v8.1) starts driving real reasoning without any visible change in wording/state from its current "selection persisted, not yet active" framing | Architects can't tell whether a green "consistent" result reflects a real check or the old no-op placeholder — erodes trust in the whole reasoning feature at the exact moment it becomes real | Change the UI copy and add a distinct status the moment real reasoning is wired in (Pitfall 3); never let "placeholder" and "live" look identical |
| Single merged pass/fail badge covering both OWL TBox consistency and SHACL/SWRL ABox validation | Architect can't diagnose which layer failed, or worse, sees "pass" from one layer and doesn't realize the other layer also ran and disagreed | Separate, clearly labeled statuses per layer (schema consistency vs. design validation vs. SHACL shape conformance) |
| Grasshopper canvas silently shows disconnected wires after a CONNECTOR change with no in-canvas guidance | Architects with production canvases hit missing-component/disconnected-wire panic with no explanation, exactly as the v7.0 notes describe for CLASSIFICATOR/VALIDATION RUNS | Follow the v7.0 release-notes pattern precisely: dedicated upgrade guide, before/after wiring diagrams, explicit "Step 1..N" re-wiring instructions (Pitfall 6) |

## "Looks Done But Isn't" Checklist

- [ ] **OWL reasoner integration:** Often missing ABox/instance realization entirely (only TBox consistency wired) — verify the reasoner actually classifies individuals, not just schema, if ABox scope is claimed (Pitfall 3)
- [ ] **Neo4j→RDF exporter:** Often missing fidelity tests for edge-property data (`order`, `pos`) — verify a known fixture's ordering-dependent facts survive translation (Pitfall 1)
- [ ] **SHACL integration:** Often missing a documented precedence/partition decision — verify a written rule (in PROJECT.md's Key Decisions or equivalent) states how SHACL and SWRL VALIDATOR divide or arbitrate rule coverage (Pitfall 4)
- [ ] **CONNECTOR credential migration:** Often missing a release-notes/migration-table artifact — verify `docs/RELEASE-NOTES-v8.2.md` (or equivalent) exists with a port-mapping table if any CONNECTOR port shifted, per the v7.0 precedent (Pitfall 6)
- [ ] **Reasoner timeout handling:** Often missing a distinct "timed out / unknown" outcome — verify the API/UI cannot conflate "reasoning inconclusive" with either "consistent" or "inconsistent" (Pitfall 2)
- [ ] **Platform credential handling:** Often missing secret-safe logging/caching — verify no raw credential value appears in `BuildRequestKey`-style concatenated strings, logs, or UI status text (Pitfall 7)

## Recovery Strategies

| Pitfall | Recovery Cost | Recovery Steps |
|---------|-----------------|------------------|
| Canvas breakage from unreviewed CONNECTOR port change (Pitfall 6) | MEDIUM | Follow the exact v7.0 recovery pattern: write a dedicated release-notes doc with before/after wiring diagrams and a port-mapping table retroactively; if GUID changed, consider whether a compatibility shim (dual-GUID load path) is feasible, as was *not* done for CLASSIFICATOR (accepted as a hard break) but *was* effectively achieved for CONNECTOR in v7.0 (same GUID, renamed ports) |
| RDF translation silently dropped edge-property data (Pitfall 1) | MEDIUM | Add the missing fidelity test, patch the exporter, re-export, and re-run any reasoning that depended on the dropped data; audit prior reasoning results for false confidence |
| SWRL/SHACL disagreement discovered in production with no precedence rule (Pitfall 4) | HIGH | Retroactively partition or rank the two systems' rule coverage, re-validate all affected design states under the corrected precedence, and communicate to architects which prior "pass" results may need re-review |
| UNA gap caused unexpected individual merging in ABox reasoning (Pitfall 5) | LOW–MEDIUM | Add `owl:AllDifferent`/`owl:differentFrom` declarations to the exporter, re-run affected reasoning; low cost if caught before ABox reasoning is exposed to end users, medium if architects already saw incorrect merged results |

## Pitfall-to-Phase Mapping

| Pitfall | Prevention Phase | Verification |
|---------|--------------------|----------------|
| Silent RDF translation data loss (Pitfall 1) | Reasoning-stack architecture decision phase | LPG→OWL mapping spec exists and is reviewed; round-trip fidelity test passes on a known fixture |
| Reasoner timeout/blowup (Pitfall 2) | OWL 2 DL reasoning integration phase | Reasoning call is async (task-based, not inline `SolveInstance`/sync request); timeout produces a distinct "unknown" result, not silent success/failure |
| TBox/ABox conflation (Pitfall 3) | Reasoning-stack architecture decision + OWL 2 DL reasoning integration phases | UI/API exposes two distinct statuses (schema consistency vs. design validation); documented as a Key Decision in PROJECT.md |
| SWRL/SHACL conflicting verdicts, duplicated authoring, unclear precedence (Pitfall 4) | SHACL validation layer phase | Written partition/precedence decision exists; no rule is authored in both formalisms without an explicit, tested precedence outcome |
| UNA gap (Pitfall 5) | Reasoning-stack architecture decision phase | Exporter emits distinctness declarations (or documented reasoner UNA-emulation config) before any ABox reasoning ships |
| CONNECTOR canvas breakage (Pitfall 6) | CONNECTOR component credential-integration phase | Either zero port/index changes to existing 4 raw-credential inputs (additive-only), or a `docs/RELEASE-NOTES-v8.2.md` with full before/after wiring + port-mapping table exists before merge |
| Platform credential handling as weak secret (Pitfall 7) | CONNECTOR component credential-integration phase | Security review step confirms no raw credential value in cache keys, logs, or UI text; credential input uses a reference/ID, not a raw secret |

## Sources

- `DG/src/DG.Grasshopper/Components/ConnectorComponent.cs` — direct read, confirms current 6-input positional contract (`Neo4jURI`, `Neo4jUser`, `Neo4jPassword`, `Database`, `PROJECT NAME`, `Connect`), plaintext password default, `BuildRequestKey` concatenation pattern, existing async-task connection pattern (HIGH confidence — primary source)
- `docs/RELEASE-NOTES-v7.0.md` — direct read, this project's established breaking-change/migration-table convention for Grasshopper components, including the CONNECTOR port-rename precedent (HIGH confidence — primary source)
- `ui-v2/src/screens/ReasonerScreen.jsx`, `data-service/reasoner.py` — direct read, confirms Reasoner selector is currently a persisted-but-inert placeholder (HIGH confidence — primary source)
- `.planning/PROJECT.md` — direct read, v8.2 milestone scope and existing Key Decisions conventions (HIGH confidence — primary source)
- [Practical Advice for Ontology Engineering on RDF & Property Graphs](https://gdotv.com/blog/ontology-modelling-rdf-property-graphs/) — LPG/OWL semantic mismatch (MEDIUM confidence — cross-checked against multiple independent search results)
- [Proposed strategy for semantics in RDF* and Property Graphs](https://douroucouli.wordpress.com/2019/07/11/proposed-strategy-for-semantics-in-rdf-and-property-graphs/) — edge-property reification gap (MEDIUM confidence)
- [SHACL Validation in the Presence of Ontologies: Semantics and Rewriting Techniques](https://arxiv.org/pdf/2507.12286) — OWA/CWA mismatch between SHACL and OWL/SWRL (MEDIUM confidence, peer-reviewed preprint, cross-checked)
- [Open World vs Closed World: Modeling OWL and SHACL Semantics](https://volodymyrpavlyshyn.medium.com/open-world-vs-closed-world-modeling-owl-and-shacl-semantics-in-agda-f4601229630b) — practical OWA/CWA guidance (MEDIUM confidence)
- [The OWL Reasoner Evaluation (ORE) 2015 Competition Report](https://pmc.ncbi.nlm.nih.gov/articles/PMC6044265/) — reasoner timeout/memory-exhaustion data on cyclic/large ABox ontologies, HermiT vs Pellet ABox performance (MEDIUM confidence, peer-reviewed)
- [Comparison of Reasoners for large Ontologies in the OWL ...](https://semantic-web-journal.net/sites/default/files/swj120.pdf) — reasoner scaling behavior (MEDIUM confidence, peer-reviewed)
- [The Fundamental Importance of Keeping an ABox and TBox Split](https://www.mkbergman.com/489/ontology-best-practices-for-data-driven-applications-part-2/) — TBox/ABox distinction and common conflation mistake (MEDIUM confidence)
- Pellet UNA design rationale (via ISWC poster/CEUR paper search results) — Pellet's explicit no-UNA ABox reasoning (MEDIUM confidence, cross-checked against reasoner documentation search results)

---
*Pitfalls research for: Design Grammar System v8.2 — Connector Integration & Reasoning Engine*
*Researched: 2026-07-11*
