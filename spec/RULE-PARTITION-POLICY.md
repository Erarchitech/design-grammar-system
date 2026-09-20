# Rule Partition & Precedence Policy (SWRL VALIDATOR vs SHACL)

## Overview

This document is the **normative partition contract** between DG's two validation systems: the SWRL-based VALIDATOR (architect-authored design-compliance rules, evaluated by the Grasshopper plugin against the metagraph Rule corpus) and the SHACL validation layer (structural data-integrity of ValidGraph/Metagraph instance data, evaluated server-side by `dg-reasoner` on every publish). It fulfills requirement **SHCL-01** ("a documented rule-partition/precedence policy between the two") and closes decisions **D-11/D-12/D-13/D-14** from `.planning/phases/823-shacl-validation-layer/823-CONTEXT.md`.

**Normative scope:**
- [Partition Line](#partition-line-d-12) -- what SWRL owns vs. what SHACL owns
- [What Belongs Where](#what-belongs-where-decision-table) -- decision table for future rule categories
- [Precedence & Single-Authoring](#precedence--single-authoring-d-13) -- the remedy for disagreement is re-homing, never merging
- [Computgraph Structural Checks (Phase 37)](#computgraph-structural-checks-phase-37) -- the third validation surface, evaluated by Cypher over the LPG-native Computgraph, that neither SWRL nor SHACL can reach
- [Input Generation Bindings (Phase 38)](#input-generation-bindings-phase-38) -- the fourth rule-corpus consumer, which reads a Rule's SWRL threshold to bound AI-generated candidates and authors nothing
- [Corpus-Level Authoring-Time Conflict Check](#corpus-level-authoring-time-conflict-check-debug-session-rule-ingest-no-conflict-check-2026-09-19) -- the fifth surface, a pre-write gate that detects a new rule's grounding signature colliding with an existing rule, closing a paper §4 preview/confirm conformance gap
- [Enforcement](#enforcement-d-14) -- documentation + review discipline this phase, linter deferred
- [How SHACL Findings Surface](#how-shacl-findings-surface) -- severity mapping and message house style

Related specs: `spec/LPG-OWL-MAPPING.md` (§"ValidGraph to RDF Sketch" -- the RDF ABox this policy's SHACL side validates), `spec/DATABASE.md` (§Graph Separation -- the LPG schema SHACL shapes constrain), `ontology/dg-shapes.ttl` (the SHACL shapes artifact this policy governs the contents of), `spec/SWRL-SUBSET.md` (Phase 1201 -- the implemented C# evaluator subset within the SWRL side of this policy's partition line).

---

## Out-of-Scope Framing

Per `.planning/REQUIREMENTS.md`'s Out-of-Scope table: **"Replacing the SWRL VALIDATOR with SHACL"** is explicitly excluded this milestone -- "SHACL ships as a complementary, additive validation layer... SWRL already encodes DG's rule semantics (violation-inverted body atoms) and a wholesale swap is a separate future-milestone decision." This policy exists precisely because two validation systems now coexist: without a partition line, the same real-world constraint could be authored twice, in two different formalisms, with no reconciliation path. This document is that reconciliation path -- it prevents drift rather than resolving it after the fact.

---

## Partition Line (D-12)

**The SWRL VALIDATOR owns architect-authored design-compliance rules** -- quantitative geometry/parameter constraints originating from natural-language ingestion (`POST /n8n/webhook/dg/rules-ingest` -> LLM -> SWRL atoms -> the metagraph `Rule` corpus). These are business rules: they encode what a *specific project* or *regulation* requires (e.g. "maximum building height is 75 meters"), they are dynamically authored per project, and their evaluation follows DG's established violation-inverted-body-atom semantics (see `spec/DATABASE.md` §Violation Pattern).

**SHACL owns structural data-integrity of instance data** -- schema conformance of the DesignState/Run/Rule graph structure itself (ValidGraph and Metagraph node/relationship shape), independent of any project's business content. These are integrity invariants: they hold for *every* project regardless of what a *specific project* or *regulation* requires (e.g. "every `PropState` must reference a resolvable `DataProperty`"). The Phase 39 auto-validation path remains on this SHACL side of the boundary; its known pre-write `RunStatusShape_valid` self-violation is documented as **F-39-01** in `spec/DATABASE.md`, not repaired by changing the partition policy or shape logic.

The distinguishing question: **does this constraint express a real-world design requirement (architect intent), or a structural precondition for the data to be interpretable at all (system integrity)?** The former is SWRL's domain; the latter is SHACL's.

---

## What Belongs Where (Decision Table)

| Rule Category | Example | System | Rationale |
|---|---|---|---|
| Quantitative geometry/parameter limit | "Maximum building height is 75 meters" | **SWRL** | Architect-authored, project-specific business content; matches the existing violation-inverted-body-atom SWRL pattern (`swrlb:greaterThan`) |
| Value-range-from-regulation | "Living unit area between 28 and 45 m²" | **SWRL** | Regulatory/business constraint expressed as two SWRL rules (min + max) per DG's established two-rule pattern (`spec/DATABASE.md` §Violation Pattern, "Between min and max") |
| Required-property-present | "Every `PropState` has a non-null `PropValue`" | **SHACL** | Structural completeness of the data model itself, independent of any project's authored rules -- holds universally |
| Enum membership | "`DesignState.kind` ∈ {ObjState, ParamState, PropState}" | **SHACL** | Schema conformance check on a stored value's domain -- not a design-compliance judgment, a data-validity precondition |
| Referential resolvability | "Every `Atom.REFERS_TO` target exists and is reachable" | **SHACL** | Graph-structural integrity (dangling references break downstream RDF translation); no architect ever "authors" this constraint |
| Rule structural integrity | "`Rule.Rule_Id` is present and matches the `R_<DOMAIN>_<PROPERTY>_<LIMIT>_V` format; body atom `order` is contiguous from 1" | **SHACL** | Validates the *shape* of a Rule node, not the *content* (truth) of its design constraint -- SHACL never evaluates whether the rule's SWRL logic is correct or whether a design satisfies it |
| Object/count/enum comparisons between design entities | "Corridor width must exceed 1.2 meters" | **SWRL** | Architect-authored geometric/parametric comparison against BIM data -- same pattern as height/area rules |
| Boolean run-record completeness | "`Run` has both `ValidStatus` (list) and `SendStatus` (boolean)" | **SHACL** | Run-record shape invariant enforced regardless of project content |
| Identity-registry data integrity | "`Representation.platform` ∈ {Grasshopper, Revit, IFC, Speckle}; `SharedProperty.dgId` matches `dg:` + 16 uppercase hex" | **SHACL** | Structural data-integrity constraints on Computgraph registry node properties (phase 32.1) — platform/nativeIdKind enum membership, dgId format pattern, required provenance fields; no architect-authored business content, purely schema conformance of the identity layer |
| Script/Computgraph structural shape (LPG-native, no RDF projection) | "Every `Procedure` has at least one `Interface`"; "no orphan `Pattern`" | **Cypher (`data-service/cg_structure_checks.py`)** | Computgraph is a Neo4j LPG partition with no RDF/OWL translation, unlike ValidGraph/Metagraph, so the SHACL path cannot reach this data; the checks are LLM-free Cypher pattern-matches over the published graph, analogous in spirit to SHACL's data-integrity role but scoped to a layer SHACL cannot address |
| Rule-mapped script-structure requirement | "A Frame `Algorithm` must contain a *Truss* `Procedure`" | **Cypher, referencing a Metagraph `Rule` by id (`llm/structure_rules.json`)** | Architect-authored intent like SWRL but evaluated against Computgraph shape rather than BIM geometry or parameters; the SWRL violation-inverted-body-atom machinery has no Computgraph equivalent, and `Rule_Id` is reused as a foreign key only, never SWRL semantics |

**Test for new rule categories not listed above:** if the constraint could only be evaluated by inspecting BIM geometry, project parameters, or an architect's stated intent, it belongs to SWRL. If the constraint holds purely by inspecting the shape of the graph data (labels, required properties, enum domains, reference resolvability) with zero project-specific business content, it belongs to SHACL.

---

## Precedence & Single-Authoring (D-13)

**Single-authoring principle:** no business rule exists in both systems simultaneously. SHACL shapes never re-encode a design-compliance constraint that SWRL already evaluates (see [Enforcement](#enforcement-d-14)), and SWRL rules never assert data-structural facts that are SHACL's responsibility.

**Consequence:** because no rule is dual-authored, a disagreement between a SWRL verdict and a SHACL finding can only mean one thing -- **mis-categorization**. Either a business rule was incorrectly shaped into SHACL, or a structural check was incorrectly authored as a SWRL rule. In either case:

- **The remedy is re-homing the rule to its correct system.** Move the mis-categorized rule (delete it from the wrong system, author it correctly in the right one).
- **The remedy is never merging or overriding verdicts.** There is no reconciliation logic, no "SHACL wins" or "SWRL wins" tie-breaker at the verdict level, because a correctly-partitioned system produces no ties to break.

**Authority split (for the narrow case where both systems happen to touch the same node, e.g. a `Rule` node's structural shape vs. its SWRL semantics):**
- For **design compliance** (does the building/design satisfy this constraint?) -- **SWRL is authoritative.**
- For **data integrity** (is this graph data well-formed and interpretable?) -- **SHACL is authoritative.**

These two questions are orthogonal by construction (per the partition line above), so this split is a clarification of scope, not a conflict-resolution mechanism.

---

## Computgraph Structural Checks (Phase 37)

This is an addendum, not a new numbered decision -- no `D-` number is assigned, because no Phase 37 CONTEXT decision letter maps to this point.

A third validation surface evaluates the **Computgraph** -- the Object / Behavior / Algorithm / Procedure / Pattern / Parameter / Interface LPG layer established in Phase 36 -- which has no RDF/OWL projection.

Neither of the two existing systems has a path to that data: the SWRL VALIDATOR evaluates BIM and parameter data against the Metagraph Rule corpus, and SHACL evaluates the OntoGraph/Metagraph RDF ABox through `ontology/dg-shapes.ttl`. Structural and rule-mapped script-structure checks are therefore evaluated by deterministic, parameterized Cypher in `data-service/cg_structure_checks.py`, and reported through the same `violation` / `warning` / `info` severity mapping the SHACL section already defines below -- see [How SHACL Findings Surface](#how-shacl-findings-surface) rather than a new taxonomy.

**Severity assignment for this third system:**
- `violation` -- structural breakage that would make the script uninterpretable to downstream tooling (orphan Pattern, Procedure without Interface, dangling `PARAM_LINK`, Algorithm without Procedure)
- `warning` -- a rule-mapped structural requirement that fails while the graph itself is well-formed
- `info` -- annotation-convention normalization surfaced from the publish envelope's preserved warnings

This is not a fourth reconciliation problem: the single-authoring principle extends to the third system by construction, because its subject graph is disjoint from the other two -- no rule can exist in two of the three systems simultaneously.

The scope boundary that keeps it that way: the structure-rule vocabulary is restricted to presence, kind, type and relationship checks. A value-threshold comparison over Computgraph data is SWRL scope, not a structural check, and must never appear in a `llm/structure_rules.json` mapping entry's parameters.

Results are ephemeral -- recomputed per request, never persisted onto the existing `Run` node, because a script-structure snapshot and a BIM design-state run are different subjects.

---

## Input Generation Bindings (Phase 38)

This is an addendum, not a new numbered decision -- no `D-` number is assigned, because no Phase 38 CONTEXT decision letter maps to a partition-policy decision.

Phase 38 adds a **fourth consumer** of the rule corpus that is **not** a fourth validation system. Input generation *reads* a Rule's SWRL atoms to recover the numeric limit a candidate must respect, and *authors* nothing. The verdict on whether a design satisfies the rule remains the SWRL VALIDATOR's, after geometry solves.

**Single-authoring is upheld by construction.** The threshold exists in exactly one place -- the Rule's `Literal` atom -- and is read at generation time, never denormalized into `llm/structure_rules.json` or any other artifact (D-10). Cross-reference `_FORBIDDEN_PARAM_KEYS` in `data-service/cg_structure_checks.py`: the same fence that keeps value thresholds out of structure rules keeps them out of input bindings.

**Binding artifact shape and location.** The binding data lives in a **new sibling top-level key `inputBindings`** in the existing `llm/structure_rules.json`, NOT as new entries in `mappings[]`. Every `mappings[]` operation compiles to a Cypher *check* and `STRUCTURE_RULE_OPERATIONS` is a closed frozenset of four, whereas a binding is a *selector*, not a check -- a different shape belongs in a different key. `load_structure_rules()` returns the full payload and only requires `mappings` to be a list, so Phase 37's validator never sees the new key and needs zero changes (D-07).

**`inputBindings` entry schema** (each entry is one object in the `inputBindings` array):

| Field | Type | Required | Description |
|---|---|---|---|
| `ruleId` | string | yes | A Metagraph `Rule_Id` |
| `determinability` | enum | yes | `direct-parameter` \| `monotone-bound` \| `geometry-required` |
| `parameters` | array of string | yes | The Computgraph parameter names the rule constrains |
| `metricExpression` | string | only for `monotone-bound` | The expression relating the constrained metric to `parameters` |
| `monotoneIn` | array of string | only for `monotone-bound` | The subset of `parameters` the metric is provably monotone increasing in |
| `description` | string | yes | Human-readable summary |

**The default.** A rule with no `inputBindings` entry is treated as `geometry-required` -- the safe direction, because it can only ever under-claim (D-08). An unmapped rule's `determinabilityClass` therefore defaults to `geometry-required`, never to `direct-parameter` or `monotone-bound`.

**Scope fence.** An `inputBindings` entry declares *which parameters* and *what kind of determinability*. It must never carry a numeric limit, comparison operator, or threshold value. Those are SWRL scope, exactly as `_FORBIDDEN_PARAM_KEYS` fences `mappings[].params` above.

---

## Corpus-Level Authoring-Time Conflict Check (debug session rule-ingest-no-conflict-check, 2026-09-19)

This is an addendum, not a new numbered decision -- no `D-` number is assigned, because no CONTEXT decision letter maps to a partition-policy decision for this fix.

This is a **fifth surface**, alongside SWRL VALIDATOR, SHACL, Computgraph Structural Checks (Phase 37), and Input Generation Bindings (Phase 38). It is **not a validation system** in the sense the first two are (it never judges whether a design satisfies a rule, and never judges the structural shape of the graph) -- it is an **authoring-time gate** that runs once, before a new `Rule` is ever written, closing a conformance gap between paper T1 ITcon R15.6 §4's normative five-stage authoring process (`tag -> recognise -> preview -> confirm -> publish`) and a shipped pipeline that implemented only `tag -> recognise -> publish`.

**What it checks.** Whether an about-to-be-authored rule shares its **(Class, DatatypeProperty, comparator)** grounding signature with a `Rule` already in the project's corpus -- the paper's own grounding triple ([P138]: "the identified constraint type ... determines the corresponding sequence of SWRL atoms"). Comparator is part of the key by construction, so the sanctioned min+max range decomposition ([P109]: "range constraints are broken down into separate lower and upper constraints") is never flagged -- a `swrlb:lessThan` rule and a `swrlb:greaterThan` rule on the same Class+DatatypeProperty are two different grounding signatures, not a collision.

**Why it is neither SWRL nor SHACL.** Per the [Partition Line](#partition-line-d-12) and [decision table](#what-belongs-where-decision-table) above: SHACL validates a Rule node's own *shape* (`Rule_Id` format, atom order) and "never evaluates whether the rule's SWRL logic is correct" -- this check compares TWO rules' semantic content to each other, which is neither a shape check nor a design-compliance evaluation against BIM/parameter data. SWRL owns evaluating a design against a rule, not comparing rules to each other. This check's subject is the rule corpus itself, at authoring time, before either system ever sees the new rule.

**Deliberately LLM-free.** Unlike semantic rule deletion's `select_rules_for_deletion()` (which reasons over open-ended NL deletion requests), this check resolves grounding deterministically: `data-service/dg_context.check_rule_conflict()` derives a candidate (Class, DatatypeProperty, comparator) triple from the incoming NL text using ONLY vocabulary this project's own Rule corpus already references (`fetch_project_rule_vocabulary()`, deliberately not `fetch_existing_entities()` alone -- see that function's docstring for the cross-project OntoGraph-tagging quirk it avoids), plus a fixed comparator-keyword table per [P109]. An unresolved/ambiguous grounding always reports "no conflict" rather than guessing -- a false negative degrades to the pre-fix behavior (silent duplicate), while a false positive would block legitimate authoring outright; the two failure modes are not symmetric, so ambiguity resolves toward the less disruptive one.

**Where it runs.** A new synchronous `POST /rules/check-conflict` in `data-service`, called by the `ui-v2` client BEFORE it POSTs to the n8n `rules-ingest` webhook. The n8n workflow and its execution model are unmodified. The dialog (Replace / Update / Keep both / Cancel) is pure client state in `ui-v2` -- no new n8n execution status, no resume endpoint -- mirroring the two-call split semantic rule deletion already established (`resolve-deletion` selection-only, `bulk-delete` confirm-only).

**Replace/Update never deletes.** Per [P129] ("versioned proposals, operator or ontology-steward approval, provenance recording") and [P139] ("approved results are recorded in the project graph together with provenance"), choosing Replace or Update records a new `SUPERSEDED_BY` relationship (old `Rule` -> new `Rule`) with `supersededAt`/`actor`/`prompt` provenance properties, instead of deleting the old `Rule`. Keep both authors the new rule with no supersede edge, and records `acceptedOverlapWith`/`acceptedOverlapAt`/`acceptedOverlapBy` properties on the new rule as a provenance-only annotation. Cancel writes nothing.

**Superseded-rule exclusion is load-bearing, not cosmetic.** A superseded rule that remained visible to the SWRL VALIDATOR's rule-corpus loader would keep firing alongside its replacement -- reproducing the exact bug this gate exists to close, in a new form. `WHERE NOT EXISTS { (r)-[:SUPERSEDED_BY]->() }` is therefore applied in three places: `DG.Core.Data.Neo4jRuleRepository.RulesQuery` (C#, the SWRL VALIDATOR's own corpus loader), `dg_context._RULE_CONFLICT_QUERY` (so a past revision cannot collide with itself forever), and `dg_context._RULES_FOR_SELECTION_QUERY` (so semantic rule deletion cannot re-select an already-retired rule).

**Schema change.** `SUPERSEDED_BY` is a new Metagraph relationship type. Per CLAUDE.md's Schema Change Propagation checklist, this addendum is accompanied by updates to `spec/DATABASE.md`, `ontology/dg-shapes.ttl`, `cypher_template.txt`, `training/dataset_schema.json`, `.github/copilot-instructions.md`, and `README.md`.

---

## Enforcement (D-14)

Enforcement in Phase 823 is **documentation and review discipline**, not tooling:

- This policy document is the reference reviewers consult when a new SHACL shape or a new SWRL rule category is proposed.
- Shape authors adding to `ontology/dg-shapes.ttl` must confirm each new shape against the [What Belongs Where](#what-belongs-where-decision-table) table before merging.
- **An automated shape-vs-rule overlap linter is explicitly deferred** -- it is a named future item (tracked alongside `REAS-F03` TBox->SHACL auto-derivation in `.planning/REQUIREMENTS.md` Future Requirements), not a promise made by this phase. No CI gate currently checks for partition violations; this is a known, accepted gap for v8.2.

---

## How SHACL Findings Surface

SHACL findings are mapped once, at the source, to DG's existing severity/message conventions -- never exposed as raw RDF/SHACL vocabulary to architects (per `.planning/REQUIREMENTS.md` Out-of-Scope: "Exposing raw SHACL/RDF validation report JSON in the UI").

**Severity mapping** (Solibri-style):

| SHACL Severity | DG Severity | Color |
|---|---|---|
| `sh:Violation` | violation | red |
| `sh:Warning` | warning | orange |
| `sh:Info` | info | yellow |

**Message house style:** every SHACL finding is translated through the same **What+Where+How-to-fix** pattern used by `ErrorMessageTemplates` (`DG/src/DG.Core/Services/ErrorMessageTemplates.cs`) for all other DG error surfaces -- `sh:focusNode`, `sh:sourceShape`, and raw IRIs never appear in architect-facing fields; focus nodes are resolved to human labels with local-name fallback before display.

**Shapes artifact:** the SHACL shapes this policy governs live in version-controlled `ontology/dg-shapes.ttl`, loaded by the `dg-reasoner` sidecar from the read-only `./ontology` volume mount (same overlay pattern as the static OWL TBox). Shape scope is data-integrity only per [What Belongs Where](#what-belongs-where-decision-table) -- no architect-authored business rule may be re-encoded as a shape.

---

## Consistency & Propagation

This policy is coupled to the graph schema (`spec/DATABASE.md`) and the RDF mapping contract (`spec/LPG-OWL-MAPPING.md`). Any change to either -- new node labels, new relationship properties, new `Atom.type` values -- should trigger a review of whether the [decision table](#what-belongs-where-decision-table) needs a new row. See `CLAUDE.md`'s Schema Change Propagation checklist, which now references this document. A schema change that adds or reshapes a Computgraph node/relationship should also trigger a review of whether [Computgraph Structural Checks (Phase 37)](#computgraph-structural-checks-phase-37) needs a new row or an updated check. The same schema change should also trigger a review of whether [Input Generation Bindings (Phase 38)](#input-generation-bindings-phase-38) needs updating -- a new or reshaped Rule category may need a new `inputBindings` entry, or may need its `determinability` reclassified.
