# T1 ITcon Draft — R7 → R8 Revision Log

**Date:** 2026-07-19 · **Input:** `T1_ITcon_DG_Draft_R7.docx` (20 Word comments) · **Output:** `T1_ITcon_DG_Draft_R8.docx`
**Length:** ~8,410 → ~6,460 words total (body ≈ 6,900 → ≈ 5,200); Appendix A removed; 8 figures → 7.
**Figures master:** `figures/T1_ITcon_R8_figures.drawio` — one editable tab per figure, DG TO-BE design system (`diagrams/DESIGN-SYSTEM.md`); exports in `figures/r8/` (PNG @2x + SVG).

## Word-comment resolutions

| # | Comment (gist) | Resolution in R8 |
|---|---|---|
| 0 | Summary should respond to the opening challenge; state role of DG ontology for design-intent management | SUMMARY rewritten: opens with the fragmentation/handover challenge, second sentence answers it with the ontology's design-intent-management role |
| 1, 10 | OBS was a typo — check FBS as the known triad around the Object | Renamed throughout to **object-centred FBS core**: Object at the centre, FBS roles around it, Function externalized (§3.1, Figure 2, all mentions) |
| 2 | Contribution too generic; align with data-driven design | Contributions rewritten as 3 items explicitly framed as "contributions to data-driven design development" (§1, last para) |
| 3 | Ontology doesn't interpret — it's a shared code space | Rewritten: "An ontology is not an active interpreter. It is the shared code space of a knowledge graph — the agreed vocabulary and axioms that any interpreting agent … must follow" (§1); checked all other mentions |
| 4 | "Semantic core" repeated too often | Retained in title/summary identity only; body now varies: "shared semantic substrate", "shared conceptual foundation", "knowledge schema", "shared code space" |
| 5 | Mention modularity/scalability — new layers can map onto the core | Added to contribution (2) and §3.2: "the layer set is open-ended: an additional layer … can be mapped onto the same core without disturbing the existing schema" |
| 6 | Tautology "Design State … design" | Replaced with "parametric configurations of design objects are captured as time-stamped Design States" (Summary, contribution 3, Conclusion) |
| 7 | Merge contribution (4) into (2); generalize extension names (no BOT/Topologic) | Contributions collapsed 5 → 3; extensions described generically as "modular alignment extensions to external vocabularies" (names appear only once, in §2.3 methodology as examples) |
| 8 | Generalize DG ID in contributions — objects as identity spine across platforms | Contribution 3 now: "design objects act as identity carriers … separated representations of one conceptual object resolve to a single identity and share unique semantic properties, improving consistency and sustainability of design decisions"; "DG ID" named once, in §4 |
| 9 | Clarify context assembler | Defined inline (§1 briefly; §4 fully): "a service that compiles the current ontology catalog, the SWRL conventions, and a versioned library of parameterized query templates into the model's context" |
| 11, 13 | "Procedural design" incoherent; domain should be data-driven parametric design; scope RIBA Stages 1–3, not conceptual only | Domain revised (§2.2): "data-driven parametric design, spanning RIBA Plan of Work Stages 1 through 3 … extending into detailing and validation" (RIBA 2020 reference added) |
| 12 | §2.2 second paragraph repeats the first | Duplicate paragraph deleted; single specification paragraph remains |
| 14 | Sources-of-knowledge sentence repeats §2.3 and §3.2 | Deleted from §2.2; sources treated only in §2.3 |
| 15 | Remove Table A3; cite core-plus-extension pattern literature instead | Table A3 removed with the whole appendix; pattern now cited via Janowicz et al. (2019, SOSA/SSN) in §2.3 and §3.2 |
| 16 | Clarify extensions engage automatically by graph layer | Added (§3.2): "when new entities are ingested into a given graph layer, the extension aligned with that layer allocates them to the proper external classes" |
| 17 | What is pilot-scale use? | Defined (§3.2): "a single organization operating a handful of concurrent projects on one graph instance" |
| 18 | Avoid predicate-less sentences in use cases | §5.1–5.3 rewritten as flowing prose ("The first use case asks whether …"), no "Question./Ontology support." fragments |
| 19 | Remove Appendix A; reference GitHub ontology project instead | Appendix removed; §3 intro now: "The complete normative schema … is maintained as a versioned, open ontology project in the accompanying repository [reference to be added upon publication]" |

## Structural changes (beyond comments)

- **§2**: old 2.1 + 2.4 merged into "2.1 Development process and grounding"; milestone trajectory compressed, internal version numbers (v4…v10.0) dropped.
- **§3**: old 3.2 + 3.3 merged into "3.2 Five graph layers, modular packaging, and project isolation"; §3.6 Grasshopper walkthrough paragraph (OBJECT–FRAME) removed together with implementation property names (procedureOrder, paramLink, patternHostTo, statePayloadJson).
- **§4**: four subsections collapsed into one section; script-intelligence content reduced to two sentences; openBIM stage-3 positioning moved to §6.2.
- **§6**: old 6.2 + 6.3 merged into "6.2 Positioning and scalability"; duplicated open-world passage now appears only in §6.1.
- **Figures**: former FIG 6 (Grasshopper screenshot) + FIG 7 (lifecycle) merged into new **Figure 6** (lifecycle + ComputGraph mapping band); former FIG 8 metrics redrawn as new **Figure 7**. **Figure 3 overlap fixed** — cross-layer bridge labels (REFERS_TO / ATTRIBUTE_OF / VALIDATES) routed on separated segments below the layer boxes; "every layer references Core concepts" annotation has dedicated space.
- **References**: removed Rasmussen et al. (2017) and Publio & Labra Gayo (2025) (no longer cited); added Janowicz et al. (2019) and RIBA (2020).

## Coherence with ptBIM 2026 (Ermolenko et al., 2026)

- Positioning sentence sharpened (§1): the ptBIM paper presented the *system architecture* ("communication, data, and analysis layers") and case studies; this paper formalizes the shared knowledge schema — resolving the "five layers" ambiguity (system layers vs. five *graph* layers).
- Shared vocabulary kept aligned: 75 m SWRL example, violation-pattern encoding, project-scoped isolation, pilot-scale limitation, SWRL atom-coverage limitation.

## ITcon alignment (from comparison with accepted 2022–2025 ontology/KG papers)

Benchmarked against Palihakkara et al. 2025, Ghorbani & Messner 2025, Jäkel et al. 2025, Kone & Mahesh 2025, Wyke & Lindhard 2025, Bloch 2022 (research thread: perplexity.ai/search/20560357-6e21-41a3-9569-ecda9b8eec94):

- Section skeleton (Intro → Methodology → Ontology → Evaluation/use cases → Discussion → Conclusion) matches the accepted-paper norm (5–7 sections).
- SUMMARY brought toward the 200–300-word norm and rewritten as problem → approach → contribution.
- Ontology presented via conceptual diagrams, no schema dumps in main text (accepted papers put full artifacts in appendix or external repo — R8 uses the external ontology repo per comment 19).
- 7 figures — within the 4–10 norm.
- Note: accepted ITcon ontology papers run 17–36 pp (~12–24k words); R8 at ~6.5k words is compact for the venue — intentional per author decision to cut only duplication/overdetail.
