# Reasoner Value Analysis & Inconsistency Auto-Repair Mechanism

**Date:** 2026-07-13 · **Status:** analysis + design proposal (input for a future phase; 825–829 block or v9.0 insert)
**Question:** The reasoner is proposed to (a) validate newly generated/edited OntoGraph content and (b) help validate design states — without overcomplicating the system. What is its *real* value today, what is missing, and if it finds inconsistencies, how should the system handle them — including auto-repair with operator control?

---

## 1. Evidence: what the reasoner actually sees today (live probes, 2026-07-13)

All probes ran through the in-app browser against the live stack (`POST /reasoner/consistency` via the nginx proxy; Neo4j seeding/cleanup via `/neo4j/db/neo4j/tx/commit`).

| Probe | consistent | subClassOf | domain | range | disjointWith | classDecl | stripped SWRL rules |
|---|---|---|---|---|---|---|---|
| `v8-ui-smoke` (16 rules, richest project) | true | 65 | 101 | 140 | 2 | 89 | 5 |
| `uat-empty-probe` (project with zero data) | true | 65 | 101 | 110 | 2 | 79 | 0 |
| `uat-reasoner-probe` (seeded `SlidingDoor SUBCLASS_OF Door` **and** `SUBCLASS_OF Window`) | **true** | **65** | 101 | 110 | 2 | 80 | 0 |

Three findings follow directly:

1. **All 65 `subClassOf` axioms come from the static TBox** (`ontology/DesignGrammar-V7.owl`). A live project contributes only class/property *declarations*, labels, and datatype ranges (`v8-ui-smoke` adds +10 classDecl, +30 range, **+0 subClassOf**). Declarations alone cannot contradict anything.
2. **The taxonomy blind spot is real.** The seeded probe expressed *exactly* the logic that the 822 UAT proved renders **Inconsistent** when written into `ontology/dg-disjointness.ttl` (`SlidingDoor ⊑ Door ⊓ Window` with `Door owl:disjointWith Window`). Expressed as live Neo4j `SUBCLASS_OF` edges, HermiT reports **consistent** — `ontology_export.py` exports OntoGraph flat and never sees the edges (`subClassOf` count unchanged at 65). This is the documented consequence of ADR-820-1, now demonstrated end-to-end against the running system.
3. **Most architect rules don't participate in OWL reasoning either.** HermiT rejects SWRL builtin atoms, so the export strips builtin-using rules before reasoning (5 stripped in `v8-ui-smoke`). DG's dominant rule pattern is quantitative thresholds (`swrlb:greaterThan` …) — precisely the stripped kind.

**Bottom line:** today, *no possible live-project edit — new class, new rule, rule edit — can make the consistency check fail.* The check currently validates the platform's own vocabulary (static TBox + curated disjointness overlay), not the newly generated/edited OntoGraph. The only genuine failure channel is an error introduced during curation of `dg-disjointness.ttl` / the V7 TBox.

## 2. Value assessment

### Real value already shipped (keep)

- **Schema-sanity guard over the platform TBox + curated disjointness** — catches curation mistakes; cheap; proven non-trivial (820 spike, 822 UAT Inconsistent render).
- **Honest failure semantics** — kill-on-timeout → "Inconclusive", cancel → distinct "Cancelled", fresh (uncached) re-runs. All three proven live (822-UAT.md, 2026-07-13). This trust property is a prerequisite for any future auto-repair: a repair loop built on a reasoner that can silently hang or return stale verdicts would be dangerous.
- **SHACL data-integrity on every publish** (Phase 823) — this is where "help validate design states" is *already real*: 8 NodeShapes validate DesignState/Run/Rule structure per run, findings surface through ErrorMessageTemplates with Solibri-style severity. Closed-world SHACL is the correct formalism for instance-data integrity; `spec/RULE-PARTITION-POLICY.md` (D-12) draws exactly this line.
- **Architecture** — the isolated sidecar (ADR-820-2) and the provenance-faithful LPG→OWL export make every increment below cheap. None of this needs rework.

### Claimed value that is NOT yet real (the gap)

- **"Reasoner validates newly generated/edited OntoGraph"** — false today (Section 1). ADR-820-1 deferred LLM-ingestion axiom emission "until the axiom requirements are proven in practice." The probe above *is* that proof: without a taxonomy channel from ingestion to export, the reasoner cannot deliver the proposed value, no matter how good the repair mechanics are.

### Overcomplication guardrails (what NOT to build)

- **No continuous/background reasoning.** DL reasoning is worst-case exponential; event-driven checks at the only moments content changes (ingest/edit) cover 100% of the value at ~zero standing cost.
- **No OWL reasoning over design-state ABox for compliance.** The SWRL VALIDATOR owns design compliance; SHACL owns integrity (partition policy D-12/D-13, single-authoring principle). Adding an OWL ABox path would create the double-authoring problem the policy exists to prevent, plus open-world semantics surprises (OWL will not flag a missing property; SHACL will).
- **No LLM-auto-applied repairs.** Empirical evidence (see §5 refs) shows LLMs are not reliable for unsupervised graph repair — valid-looking but wrong fixes, hallucination. LLMs stay in the *explain/suggest* role.

## 3. Making the proposed value real — three minimal increments

**V1 — Event-driven consistency gate (no new infra).** After each `rules-ingest` / rule-edit n8n flow completes, `data-service` fires `POST /reason/consistency {project}` asynchronously and attaches the verdict to the session-history entry (badge: consistent / inconsistent / inconclusive). The endpoint, proxy, timeout ceiling, and UI verdict vocabulary all exist. The Reasoner screen's manual "Run check" remains as the on-demand re-check. *Value: contradictions are caught at the moment content changes, not when someone remembers to press a button.*

**V2 — Give the reasoner something to see: taxonomy emission on ingest.** Extend the ingestion prompt/schema so the LLM emits `SUBCLASS_OF` edges (and flags candidate disjointness for *curation*, never auto-inserting it) when a rule's language asserts taxonomy ("a sliding door is a door"). Extend `ontology_export.py` to map `SUBCLASS_OF → rdfs:subClassOf` (one Cypher query + one triple-emit branch; the mapping spec §OntoGraph already anticipates reification patterns). This is ADR-820-1's deferred item with its activation condition now met. Cost is the known 9-file schema-propagation checklist — schedule as its own phase (825–829 reserved block is free) rather than folding into v9.0 work. **V2 is the prerequisite for any repair mechanism being worth building** — without it there is nothing project-specific to repair.

**V3 — Design-state assistance stays SHACL-side.** Grow `ontology/dg-shapes.ttl` incrementally (referential resolvability, enum domains, run-record completeness are shipped; add shapes as new invariants appear). Do not open an OWL ABox path.

## 4. Inconsistency handling: detect → explain → propose → repair, with operator control

When (post-V2) a live inconsistency occurs, "Schema inconsistent — 1 unsatisfiable class: SlidingDoor" is a verdict, not a remedy. The pipeline below turns it into one. Design constraints honored: architects have no semantic-web background (raw axioms never surface), all mutations reuse existing conventions (rule_edit MATCH-DELETE cleanup, ErrorMessageTemplates, session history), and autonomy is staged.

### 4.1 Explanation — justification extraction

A *justification* is a minimal axiom subset sufficient for the contradiction (Horridge/Parsia; "laconic" variants strip superfluous axiom parts). No Python library computes justifications natively (owlready2 has no explanation API; the OWL API explanation stack is Java). **This does not matter at DG's scale.** The axiom space partitions by provenance:

| Bucket | Size | Repair-eligible? |
|---|---|---|
| Static TBox (`DesignGrammar-V7.owl`) | ~400 axioms, version-controlled, trusted | Never automatically |
| Curated overlay (`dg-disjointness.ttl`) | handful, human-curated | Never automatically |
| **Live project export** | ~10–100 triples, LLM-generated, provenance-tagged | **Yes — the suspect set** |

Black-box axiom pinpointing (delete-and-retest with binary search / QuickXplain-style narrowing) over *only the suspect set* needs O(log n) reasoner calls per MUPS at ~2 s per call — seconds, not minutes. Each suspect triple already maps back to a graph element (IRI ↔ node identity per `spec/LPG-OWL-MAPPING.md`), so a justification arrives as a set of `{Class node, SUBCLASS_OF edge, Rule_Id}` references — directly renderable and directly mutable.

### 4.2 Repair candidate generation & ranking

From the MUPS set, minimal hitting sets (Reiter's diagnosis framework) enumerate candidate repairs: remove one element from every justification. Rank candidates by:

1. **Suspect-first** — prefer touching the *newest* LLM-generated elements (ingest timestamp / session-history correlation); static TBox and curated overlay are never candidates in automated flows.
2. **Weaken over delete** — retagging `SlidingDoor SUBCLASS_OF Window` → removal of one parent edge beats deleting the class; deactivating a rule beats deleting it.
3. **Minimal change** — fewest graph mutations.

Each candidate compiles to a concrete, previewable Cypher mutation (MATCH-DELETE edge / retag property / `quarantined:true` flag), reusing the Phase-29-locked rule_edit cleanup convention.

### 4.3 Staged autonomy with operator control

| Level | Behavior | Mutation authority |
|---|---|---|
| **L0 Report** (default) | Verdict + plain-language justification through ErrorMessageTemplates (What + Where + How-to-fix): *"SlidingDoor cannot be both a Door and a Window — Doors are never Windows (platform rule). Introduced by rule R_DOOR_SLIDING_V ingested 2026-07-13. Fix: remove one parent or rehome the class."* | None |
| **L1 Propose** | Ranked repair candidates rendered as a **diff preview** (before/after subgraph) with one-click Apply → Cypher runs → **automatic re-check** confirms consistency → session-history audit entry (who/what/when/verdict). Aligns with the v9.0 Phase 31 RING-02 diff-preview design — build once, share the component. | Operator per-click |
| **L2 Auto-quarantine** (opt-in, per project) | Only for unambiguous cases (single justification, all-suspect axioms): system sets `quarantined:true` on the offending element — validation pipelines skip quarantined rules/classes — and notifies the operator with one-click restore. **Deactivation only; deletion always requires an operator.** | Reversible flag only |

The verdict-freshness property proven in the 822 UAT (re-run reflects the changed ontology, no caching) is what makes the L1 "apply → re-check → confirm" loop sound. An LLM may *draft* the plain-language explanation text (xpSHACL-style), but never selects or applies repairs — consistent with 2025 empirical findings that LLM graph-repair correctness is too low for unsupervised use.

### 4.4 SHACL findings (design-state side)

SHACL violations are structural integrity defects (dangling references, missing required properties) — their "repair" is fixing the *producer* (Grasshopper publish path, ingestion tagging), not mutating stored data. Keep L0-style reporting (already shipped: severity-mapped, template-worded); a per-finding "likely producer" hint (e.g., "published by Run X from canvas Y") is the highest-value cheap improvement. Auto-mutating instance data to satisfy shapes is explicitly out — it would mask producer bugs.

## 5. State-of-the-art references

- Justification-based explanation for OWL: [Horridge — Justification based explanation in ontologies](https://www.semanticscholar.org/paper/13682aeaa454f30e07002c779c937083848e9048); [Explaining Inconsistencies in OWL Ontologies (Horridge, Parsia, Sattler)](https://link.springer.com/chapter/10.1007/978-3-642-04388-8_11); [Laconic and Precise Justifications in OWL](https://link.springer.com/chapter/10.1007/978-3-540-88564-1_21); [Manchester explanation research overview](http://owl.cs.manchester.ac.uk/research/explanation/).
- Repair: [Kalyanpur, Parsia, Sirin, Cuenca Grau — Repairing Unsatisfiable Concepts in OWL Ontologies](http://www.cs.ox.ac.uk/people/bernardo.cuencagrau/publications/repair.pdf) (hitting-set repair, ranking heuristics); [Efficient MUS Enumeration with Applications to Axiom Pinpointing](https://arxiv.org/pdf/1505.04365); [sequential model-based diagnosis / interactive debugging (OntoDebug lineage)](https://arxiv.org/pdf/1711.05508).
- LLM-generated ontologies & HITL repair: [Graph Repairs with Large Language Models: An Empirical Study (2025)](https://arxiv.org/html/2507.03410) — LLM repair correctness "very low despite valid format"; interactive HITL systems recommended; [LLM-supported ontology & KG construction](https://arxiv.org/abs/2403.08345); [KG validation integrating LLMs and human-in-the-loop (2025)](https://www.sciencedirect.com/science/article/pii/S030645732500086X) — validation modules +20% precision.
- SHACL explanation/repair: [xpSHACL — Explainable SHACL validation via RAG + LLMs (VLDB-W 2025)](https://arxiv.org/html/2507.08432v1) (NL explanations of violation reports — matches our ErrorMessageTemplates direction); SHACL repair via answer-set programming (Ahmetaj et al., ISWC 2022); [SHACL/ShEx community survey](https://arxiv.org/pdf/2606.03502).

## 6. Recommendation summary

1. **Keep the reasoner narrow and event-driven.** No continuous reasoning, no OWL over design states. Its shipped value (platform-TBox sanity, honest timeout UX, SHACL integrity on publish) is real; preserve it.
2. **Close the value gap before building repair machinery:** V1 post-ingest/post-edit consistency gate (days of work, no schema change), then V2 taxonomy emission (own phase; the 9-file propagation is the whole cost; activation condition of ADR-820-1 is now empirically met).
3. **Ship inconsistency handling as L0 → L1 → (opt-in) L2**, with the suspect-set black-box pinpointing from §4.1 — feasible in pure Python at DG scale, no OWL API dependency.
4. **Never auto-delete; quarantine is the ceiling of autonomy.** All applied repairs are diff-previewed, audit-logged, and followed by an automatic re-check.

---
*Method note: live probes executed via the Claude in-app browser against the running stack (2026-07-13); Perplexity MCP was unavailable this session (API-key + browser-profile failures on both configured servers), so SOTA references were gathered via web search instead.*
