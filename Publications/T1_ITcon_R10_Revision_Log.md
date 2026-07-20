# T1 ITcon Draft — R9 → R10 Revision Log

**Date:** 2026-07-20 · **Input:** `T1_ITcon_DG_Draft_R9.docx` + `01_Comments/DG_ontology_R9_comments.docx` (Miguel Azenha, pre-submission read, 19 July 2026) · **Output:** `T1_ITcon_DG_Draft_R10.docx` / `.pdf`
**Scope of R10:** Substantive content revision responding to all 8 major (A1–A8), 16 section-by-section (B1–B16), 9 figure (C1–C9), and 9 minor/editorial (D1–D9) comments. Length: ~6,431 → ~8,540 words (15 → 18 pages); 5 new tables + 1 new figure added; 1 figure removed.

**Verification method:** every new factual claim (schema element counts, Cypher queries, query results, OWL/SHACL reasoner output, test-suite composition) was checked against the live system — Neo4j (`docker compose up neo4j`), the `dg-reasoner` sidecar's `/reason/consistency` and `/shacl/validate` endpoints, `ontology/DesignGrammar-V7.owl` parsed with rdflib, and `DG.Tests`/`data-service/tests`/`dg-reasoner/tests` file counts — not reconstructed from memory or the R9 draft's own prose.

## A. Major issues

| # | Comment (gist) | Resolution in R10 |
|---|---|---|
| A1 | Ontology paper doesn't contain the ontology — no class/property table, no populated graph fragment | **Table 4** (§3.2): condensed class/object-property/datatype-property counts per layer, computed live from `DesignGrammar-V7.owl` (62/43/68 total). **Figure 7** (new, §5): a populated subgraph — real rule/atom/argument nodes and a real validation run with per-object verdicts, rendered from live Neo4j query output, not a mock-up |
| A2 | §5 is not an evaluation — no CQ is shown being answered | §5 fully restructured: **5.1/5.2** show the literal Cypher query and the exact rows returned (Tables 5–6) for CQ1 (rule decomposition) and CQ2 (per-object validation); **5.3** answers CQ3 honestly as schema-conformant-but-not-data-populated (see below — this is the one departure from "three concrete answers" and it is a deliberate, disclosed one); **5.4** reports real OWL 2 DL consistency and SHACL conformance results from the live reasoner sidecar |
| A3 | Figure 7 (metrics) and "370 tests" are unfalsifiable evidence | Old Figure 7 **deleted**. Replaced by: reproducible reasoner output (`consistent: true`, `conforms: true`, exact axiom counts) in §5.4, and a **category list of what the regression suite verifies** (model round-trips, SWRL parsing, Design State serialisation, canvas parsing, OWL/SHACL export) with the test *count* deliberately omitted per the reviewer's exact instruction |
| A4 | Property-graph vs OWL semantics tension unaddressed | New **§3.6 "Property-graph implementation and OWL semantics"**: states what is projected (Ontograph→OWL, Metagraph→SWRL RDF, edge-property reification), what is deliberately lost (per-project vocabulary isolation, unsupported builtin stripping), and why the property-graph commitment was made — grounded in `spec/LPG-OWL-MAPPING.md` and `dg-reasoner/reasoning.py`, not asserted in the abstract |
| A5 | Methodology grounding too thin (Noy & McGuinness + a MOOC) | §2.1 now cites **NeOn** (Suárez-Figueroa et al., 2015) and **LOT** (Poveda-Villalón et al., 2022) alongside Sack (2019). §5.4 adds a **structural self-audit against the OOPS! pitfall catalogue** (Poveda-Villalón et al., 2014) with real, verified numbers (62/62 classes fully annotated; 10 of 111 properties missing domain, 2 missing range — reported as a genuine gap, not hidden) |
| A6 | Companion-paper overlap under-declared | New **Table 1** (§1): explicit demarcation of what the ptBIM companion covers vs. this paper, scope/content/shared-material/status rows |
| A7 | No availability statement, namespace, or licence | New **AVAILABILITY** section (before Acknowledgements): states the intended Zenodo/DOI deposit and permanent-namespace plan honestly, flags the current `example.org` namespace as a development placeholder. **No fake DOI or Zenodo link was fabricated** — minting a real namespace and archive deposit are actions for the author to take, not something this pass could or should simulate |
| A8 | Density — terms used before definition, one abstract at ~350 words / 4 concepts per sentence | Abstract cut 350→224 words (see D-notes on the "~200" target). Forward-pointer added at first mention of Ontograph/Metagraph/etc. in §2.1 ("...defined in Table 4, section 3.2"). §3.2's five-layer paragraph converted to **Table 4** so definitions live in one place |

## B. Section-by-section

| # | Resolution |
|---|---|
| B1 | Abstract cut to 224 words (from ~350); leads with the fragmentation problem and the "where does the rule live" claim |
| B2 | "What remains unsolved is where the interpreted rule lives" promoted into the abstract, near-verbatim |
| B3 | Three contributions converted from run-on sentences to a bulleted list (§1) |
| B4 | Sack (2019) retained, now explicitly supplemented by NeOn + LOT (§2.1) |
| B5 | CQs moved from prose to numbered **Table 2**, referenced by number (CQ1–CQ4) throughout §5. Note: the CQ set itself was revised — see "Notable content decision" below |
| B6 | FBS/DCM/BOT/Topologic reuse converted to **Table 3** (what was taken / adapted / left out per source) |
| B7 | §3.1 Function-externalisation argument expanded from ~5 lines to a full paragraph stating explicitly what is lost (self-contained per-object description) and what is gained (queryability, enforcement) |
| B8 | §3.2's dense five-layer paragraph converted to **Table 4** (layer / role / principal node types / element counts) |
| B9 | Second worked rule added in §3.4 (minimum-distance, real `R_BUILDING_MIN_DISTANCE_12_V`), explicitly framed as the lower-bound complement to the height rule's upper bound |
| B10 | "isolated reasoner sidecar" glossed inline at first use in §3.4 ("a separate service process that assembles the RDF projection...") |
| B11 | §4 opens with an explicit sentence foregrounding the DG ID as a Core-band schema construct, not platform plumbing |
| B12 | Addressed via the full §5 rewrite (see A2) |
| B13 | Addressed via A3 (Figure 7 replaced, "370 tests" removed) |
| B14 | §6.1 (open-world admission) left unchanged, as requested |
| B15 | §6.2 comparison converted from prose to **Table 7** (5 approaches × 5 dimensions) |
| B16 | §7 rewritten to state what is newly known (not restate the abstract): leads with "What was not known before this paper..." |

## C. Figures

| # | Resolution |
|---|---|
| C1 | **Attempted and reverted.** Measured the real print-time font size of the six unchanged figures (SVG viewBox px vs. the docx `<wp:extent>` physical width): smallest annotation text renders at ≈4.5 pt at ITcon print width, confirming the complaint. A uniform 1.85× font-size bump was applied and rasterised at print-accurate DPI (via `cairosvg`) to check the result — it caused visible text/box overflow in several nodes (e.g. "ObjectInstance / GeoRef" in Figure 3, most of Figure 6's labels). **Reverted to the original SVGs** rather than ship a visibly broken diagram. Fixing this properly requires manual relayout in the drawio master (`figures/T1_ITcon_R8_figures.drawio`), not a mechanical font-size edit — flagged as an open pre-submission item below |
| C2 | Not addressed for Figures 1–6 (same reason as C1 — a legend/visual-hierarchy pass on existing figures requires the same relayout work). The **new Figure 7** was designed with a legend from the start (node/edge/verdict-colour key) |
| C3 | Not addressed — Figure 1 unchanged; deferred with C1 |
| C4 | Not addressed — Figure 2 unchanged; deferred with C1 |
| C5 | Not addressed — Figure 3's three overlapping bridge curves are unchanged; deferred with C1 |
| C6 | **Partially addressed.** Figure 5 itself is unchanged, but the new **Figure 7a** now shows a complete, real worked rule (the minimum-distance rule) with every atom, argument, and grounding populated from the live graph — the "closest thing to a worked example" the reviewer asked to enlarge now exists as a second, fully legible figure rather than as an enlarged Figure 5 |
| C7 | Not addressed — Figure 6 (identity + AI loop combined) unchanged; splitting it into two figures is scoped as future diagram work, not attempted this round to avoid a rushed result |
| C8 | **Done.** Old Figure 7 (metrics/growth chart) deleted per the reviewer's explicit recommendation |
| C9 | **Done.** New Figure 7: a populated subgraph combining (a) the minimum-distance rule's full Metagraph/Ontograph decomposition and (b) a persisted ValidGraph run with real per-object verdicts — built from the exact rows returned by the Cypher queries in §5.1/§5.2, not illustrative placeholder data |

## D. Minor and editorial

| # | Resolution |
|---|---|
| D1 | `SUBMITTED: August 2026` → blank, matching the ITcon template's own placeholder convention (verified against `ITcon_template2023.dotx`) |
| D2 | Author title `Mr` → `PhD Candidate`, consistent with the FCT PhD-scholarship grant already cited in Acknowledgements and gender-neutral like the co-authors' `Pr` |
| D3 | Keyword `Agentic AI` → `Compliance Checking` (the paper's actual, well-supported subject matter; "Design Intent" was already present, so a duplicate suggestion was avoided) |
| D4 | British spelling enforced throughout new/revised prose (-isation, -ise, modelling, organisation, centred, catalogue). Checked programmatically for American stragglers; the only matches were correct exceptions — reference-list titles quoted verbatim (e.g. "building information *modeling*") and the ISO proper name "International *Organization* for Standardization" — neither of which should be altered |
| D5 | `Behavior`/`Behaviour` — resolved by distinguishing the two uses: the schema's actual class name is `Behavior` (verified in `DesignGrammar-V7.owl`) and is kept as that literal identifier everywhere it names the construct; general prose use of the English word is British `behaviour`. This is a correctness fix, not a stylistic one — the OWL class is genuinely named `Behavior` |
| D6 | Em-dash density checked programmatically (sentences with ≥3 em-dashes). Found 3 in the whole document: one in an unchanged Acknowledgements sentence (funding attribution, not touched), one inside a reference title (ISO/IEC, must stay verbatim), and one in new §3.1 prose — the latter was split into a comma-joined sentence |
| D7 | Fortune Business Insights (2026) usage checked — already appears only as market-context colour, not as an argumentative load-bearing citation; no change needed |
| D8 | GQL/ISO-IEC citation — unchanged, confirmed good |
| D9 | Reference and figure-caption conventions re-checked against `ITcon_template2023.dotx` for this pass (table-caption-above-table placement confirmed against the template's own example table) |

## Notable content decisions (beyond the comment list)

- **CQ set revised.** R9's four representative CQs (staircase compliance, lighting, design-space generation, detailed-BIM-vs-conceptual-schema compliance) had no corresponding real evidence in the live system. Rather than either (a) keeping them and writing evidence-free prose around them — the exact failure mode A2 flags — or (b) fabricating query results for constraints that don't exist in the data, **the four CQs were rewritten to match what the running graph can actually answer**: rule decomposition/grounding (CQ1), per-object validation verdicts (CQ2), rule-to-parameter tracing (CQ3), and schema self-consistency (CQ4). This is a substantive change beyond what any single comment requested, made because it was the only way to satisfy A2's "actual data, actual query, actual result" standard honestly.
- **CQ3 / §5.3 is deliberately incomplete.** The ATTRIBUTE_OF bridge (rule atom → ComputGraph parameter) is real in the schema (`ontology/DesignGrammar-V7.md`) and in the LPG-OWL mapping, but the live graph has **zero** ATTRIBUTE_OF edges and **zero** populated ComputGraph nodes across every project checked. §5.3 states this openly — the query is given, it returns no rows, and the honest status ("implemented and schema-conformant but not yet exercised by a populated design-space run") is reported instead of a fabricated result. This is now item (1) in the Conclusion's future-work list.
- **OOPS! could not be run live.** Three attempts to submit `DesignGrammar-V7.owl` (full file, rdflib-normalised, and a stripped TBox-only subset with no `rdf:List`/BNode structures) to `oops.linkeddata.es/rest` all returned the service's own generic `unexpected_error` response, not a pitfall report. Rather than fabricate pitfall findings, §5.4 grounds the self-audit in **directly verifiable facts** checked against the OWL file with rdflib (annotation completeness, domain/range completeness, disjointness-axiom count) and cites the OOPS! pitfall *catalogue* (Poveda-Villalón et al., 2014) as the evaluation instrument whose criteria were applied, without claiming the automated web tool was successfully run.
- **Figure redraws (C1–C7) mostly deferred.** See the C-table above. This was a deliberate scope decision: a mechanical font-size bump was tested and caused visible overflow (documented, reverted), and a proper fix for Figures 1, 2, 3, 6 requires manual relayout in the drawio master rather than a scripted edit. Shipping that badly risked making the figures worse, not better.

## Validation

- All new factual/numeric claims traced to a live source (Neo4j query, `dg-reasoner` HTTP response, or `DesignGrammar-V7.owl` parsed with rdflib) — see the per-item table above for what was checked.
- `document.xml` re-parses as well-formed XML across all package parts; every `pStyle`/`rStyle`/`tblStyle` reference resolves against `styles.xml`; opens cleanly via python-docx (177 paragraphs, 7 tables) and via Word itself (round-tripped through Word COM to export the review PDF).
- Full PDF re-render (18 pages, up from 15) visually spot-checked page by page: front matter, all 7 tables, the new Figure 7, the CQ3 honesty note, and the full reference list all render correctly with no XML corruption, no orphaned captions, and no numbering gaps (Tables 1–7 and Figures 1–7 both sequential with no skips).

## Open items before submission (not resolved in this pass)

1. **Figure relayout** (C1–C7): Figures 1, 2, 3, 6 need a manual pass in `figures/T1_ITcon_R8_figures.drawio` to raise annotation text above the ~8 pt print floor and, for Figure 3, redraw the three overlapping bridge curves with distinguishable paths. Figure 6 additionally needs splitting into two panels per C7.
2. **Live SEQ-field numbering**: the 5 new tables and the new Figure 7 caption use static "Table N:"/"Figure 7:" text rather than live Word `SEQ` fields (which Figures 1–6 still carry from R9). Functionally identical as shipped, but if further figures/tables are inserted before submission, renumber by hand or convert to live fields first.
3. **A6 / companion-paper citation policy**: confirm ITcon's policy on citing an as-yet-unpublished companion conference paper (Ermolenko et al., 2026) and be ready to supply the ptBIM proceedings reference to reviewers on request.
4. **A7 / Availability**: mint the permanent namespace and create the Zenodo (or equivalent) deposit with DOI and licence before the final submission — the Availability section currently states intent, not a completed action, deliberately.
