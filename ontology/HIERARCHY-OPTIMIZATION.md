# Hierarchy Optimization — Reducing External Class Clutter

> Analysis of why Protégé shows ~134 ungrouped external classes after loading `[DesignGrammar.owl](DesignGrammar.owl)` v3.3 with its 7 imports, and ranked options for cleaning up the hierarchy view.

**Compiled:** 2026-05-15
**Scope:** Protégé class hierarchy view of DesignGrammar.owl with all 7 cross-ontology imports resolved (PROV-O, SOSA, SHACL, SKOS, DCTerms, GeoSPARQL, SWRL).

---

## 1. The problem, quantified

After loading the ontology with imports resolved (Path B catalog), Protégé's *Classes* tab shows:

| Source | Count | Location in hierarchy |
|---|---:|---|
| **DG classes** | 42 | Mostly under `dg:LayerEntity` hub (✅ clean after v3.3) |
| SWRL imports | ~13 | Under `swrl:Atom`, `swrl:Variable`, etc. — root-level alongside DG |
| PROV-O imports | ~30 | Under `prov:Influence`, `prov:Activity`, `prov:Entity`, `prov:Agent` |
| SOSA imports | ~10 | `sosa:Observation`, `sosa:FeatureOfInterest`, `sosa:Sample`, `sosa:Sensor`, etc. |
| SHACL imports | ~40+ | `sh:Shape` subtree, `sh:Severity`, ~25 `sh:ConstraintComponent` subtypes |
| SKOS imports | ~6 | `skos:Concept`, `skos:ConceptScheme`, etc. |
| DCTerms imports | ~30 | `dcterms:BibliographicResource`, `dcterms:FileFormat`, etc. — mostly **unused** by DG |
| GeoSPARQL imports | ~5 | `geo:SpatialObject`, `geo:Feature`, `geo:Geometry` |
| **Total visible** | **~176** | |
| **Of which DG actually aligns with** | **15** | (the ones receiving `subClassOf` / `equivalentClass` axioms) |
| **Pure passenger classes** | **~119** | Loaded by imports but not referenced anywhere in DG |

**Ratio: ~3× more "passenger" external classes than aligned ones.** This is the root cause of clutter.

---

## 2. Why we can't just move external classes under DG hubs

OWL has a hard constraint: **you cannot reorganize classes from a namespace you don't own without polluting global semantics.**

If we add `prov:Activity rdfs:subClassOf dg:ExternalEntity`, that becomes globally true. Anyone else importing **both** PROV-O and DG sees that PROV's Activity is now a subclass of a DG class — which is wrong from PROV's perspective and creates confusion in shared linked-data systems.

**This is called "ontology pollution" and is universally considered bad practice.** Tools like ROBOT explicitly flag it during quality checks. So options that pollute external classes (e.g. forcing them under our hubs) are **rejected outright** and not considered below.

What we CAN do without pollution:
1. Choose whether to import the external ontology at all
2. Choose how DG classes reference external classes (subClassOf, equivalentClass, seeAlso, no link)
3. Use Protégé view filters that don't touch the ontology
4. Split DG into multiple files with different import sets

---

## 3. Five viable options

Listed in decreasing order of recommendation. Each option lists what it does, the trade-offs, and what it costs to apply.

### Option A — Protégé view filters (zero ontology change) ⭐

**What:** Use Protégé's built-in *View* menu to filter the class hierarchy panel by namespace prefix or by "asserted only" / "imported ontology hidden" toggles.

**How:**
1. Open the ontology in Protégé.
2. *Window → Tabs → Class hierarchy* (or use the existing tab).
3. Right-click the hierarchy panel header → **Filter by URI** → enter `http://example.org/design-grammar` to show only DG entities.
4. Alternative: *Window → Tabs → Active ontology* → *Imports* → right-click each import → **Hide in class hierarchy**.

**Trade-offs:**
- ✅ Zero ontology changes — fully reversible.
- ✅ Preserves full cross-vocab reasoning (HermiT still sees everything).
- ✅ Each user can configure their own view.
- ❌ Filter is per-user, per-workspace — not shared via Git.
- ❌ Doesn't help non-Protégé tools (TopBraid, WebVOWL, GraphDB Workbench, etc.).

**Cost:** ~30 seconds per user.
**Recommended for:** Individual researchers who load the ontology occasionally.

---

### Option B — Split into two OWL files ⭐⭐ (recommended for the project)

**What:** Refactor into:
- **`DesignGrammar.owl`** — DG content only. No `owl:imports`. No cross-vocab alignment axioms. Pure DG ontology with 42 classes under 4 layer hubs.
- **`DesignGrammar-aligned.owl`** — A *facade* ontology containing only:
  - `owl:imports DesignGrammar.owl`
  - The 7 external `owl:imports`
  - The 49 alignment axioms (moved here from the main file)

**Result:** Users open whichever serves their purpose. Default workflow uses the lean DG file; alignment work uses the facade.

**Trade-offs:**
- ✅ **Clean Protégé view by default** — opening `DesignGrammar.owl` shows only DG classes.
- ✅ **Full alignment preserved** — opening `DesignGrammar-aligned.owl` brings in everything.
- ✅ **Standard W3C pattern** — SOSA does this (sosa.ttl core + ssn.ttl extension), as do FOAF, DCAT, others.
- ✅ **Clear separation of concerns** — "what DG is" vs "how DG relates to standards".
- ✅ **Modular reasoning** — verify DG consistency without external vocabs; verify alignment consistency separately.
- ✅ **Smaller default file** — faster to load, easier to read.
- ❌ Two files to maintain. Adding a new alignment goes into the facade file, not the main one.
- ❌ Catalog needs entries for both ontology IRIs.
- ❌ External tools need to know which file to load for their use case.

**Cost:** ~1 hour refactor (I can do it in one pass).

**Recommended for:** This project, going forward. The split mirrors the actual division of intent (DG itself ≠ DG's interop story).

#### Sketch of resulting files

```
ontology/
├── DesignGrammar.owl              ← DG core (lean, ~150 KB → ~120 KB after stripping alignments)
├── DesignGrammar-aligned.owl      ← Alignment facade (~20 KB, mostly imports + axioms)
└── catalog-v001.xml               ← Maps both IRIs + 7 externals
```

`DesignGrammar-aligned.owl` looks like:

```xml
<owl:Ontology rdf:about="http://example.org/design-grammar/aligned">
    <rdfs:label xml:lang="en">DG Aligned (cross-vocab facade)</rdfs:label>
    <owl:imports rdf:resource="http://example.org/design-grammar"/>
    <owl:imports rdf:resource="http://www.w3.org/2003/11/swrl"/>
    <owl:imports rdf:resource="http://www.w3.org/ns/prov-o#"/>
    <!-- ... 5 more imports ... -->
</owl:Ontology>

<!-- All 49 alignment axioms relocated here -->
<owl:Class rdf:about="&dgm;Rule">
    <owl:equivalentClass rdf:resource="&swrl;Imp"/>
</owl:Class>
<owl:Class rdf:about="&dgv;ValidationRun">
    <rdfs:subClassOf rdf:resource="&prov;Activity"/>
    <rdfs:subClassOf rdf:resource="&sh;ValidationReport"/>
</owl:Class>
<!-- ... etc. for the other 13 DG classes that align ... -->
```

---

### Option C — ROBOT module extraction (advanced, production-grade)

**What:** Use the [ROBOT](https://robot.obolibrary.org/) ontology tool to extract a **minimal module** from each external ontology containing only the classes/properties DG actually references — then import the small module instead of the full vocab.

**How:**
1. Install ROBOT: `brew install robot` or [download JAR](https://robot.obolibrary.org/).
2. For each external vocab, extract a SLME (Semantic Locality Module Extraction) module:
   ```bash
   robot extract --method MIREOT \
       --input prov-o.owl \
       --term http://www.w3.org/ns/prov#Activity \
       --term http://www.w3.org/ns/prov#Entity \
       --term http://www.w3.org/ns/prov#generated \
       --term http://www.w3.org/ns/prov#startedAtTime \
       --output ontology/imports/prov-o-module.owl
   ```
3. Update `catalog-v001.xml` to redirect each import to its local module file.

**Result:** Each external "import" loads only the 2-5 classes DG aligns with, not the full 30+ classes of the vocabulary.

**Trade-offs:**
- ✅ **Dramatic reduction in external clutter** — ~119 passenger classes → 0.
- ✅ **Full reasoning preserved** — module contains the upper closure (parents + needed properties).
- ✅ **Self-contained** — no internet needed after extraction.
- ❌ Requires ROBOT installed (~50 MB Java tool) plus one-time extraction.
- ❌ Modules need re-extraction if you align with new external classes later.
- ❌ More complex repo setup.
- ❌ Not idiomatic for small ontologies — usually reserved for biomedical / large OBO Foundry vocabs.

**Cost:** ~2 hours initial setup + 5 minutes per re-extraction. CI integration possible.

**Recommended for:** Production deployment where the ontology is published and consumed by multiple downstream systems. **Overkill for the current single-team workflow.**

---

### Option D — Remove all `owl:imports`, keep alignment IRIs as dangling references

**What:** Strip the 7 `owl:imports` from the ontology. Leave the 49 alignment axioms in place, but they now reference external IRIs that aren't loaded.

**Trade-offs:**
- ✅ Cleanest possible Protégé view — only DG classes appear, no external ones.
- ✅ Zero external dependencies.
- ❌ **Alignment axioms become semantically inert.** HermiT treats unknown IRIs as unspecified individuals — no inference flows through them.
- ❌ External consumers of DG see "references to PROV-O that aren't actually verified."
- ❌ Loses the **primary benefit of declaring alignments** — reasoner-checked interop.

**Cost:** Delete 7 lines.
**Recommended for:** Demo / NotebookLM scenarios where alignments are purely human-facing documentation. **Not for serious interop.**

---

### Option E — Annotation-based filtering (lukewarm, mostly for big vocabs)

**What:** Add a custom annotation property `dg:passengerClass` and tag every imported class that DG doesn't directly use. Then Protégé's "Filter by annotation" feature can hide them.

**Trade-offs:**
- ✅ More precise than namespace filtering — hides only *unused* external classes.
- ❌ Requires annotating ~119 external classes — automated via script but still ontology churn.
- ❌ Mild form of pollution: we'd be adding annotations to PROV-O classes from outside.
- ❌ Annotation is dropped if external ontologies are re-fetched.

**Cost:** Medium (script work).
**Recommended for:** None — Option B accomplishes the same effect more cleanly.

---

## 4. Comparison matrix

| Criterion | A: View filter | **B: Split files** | C: ROBOT module | D: Strip imports | E: Annotations |
|---|---|---|---|---|---|
| Clean Protégé view by default | ❌ (per-user) | ✅ | ✅ | ✅ | ✅ (with filter) |
| Preserves alignment reasoning | ✅ | ✅ | ✅ | ❌ | ✅ |
| External tool friendly | ❌ | ✅ | ✅ | ✅ | ⚠️ |
| Zero ontology pollution | ✅ | ✅ | ✅ | ✅ | ⚠️ (mild) |
| Reversible | ✅ | ✅ (merge files) | ✅ | ⚠️ | ✅ |
| Long-term maintenance burden | None | Low | Medium | Low | Medium |
| Initial cost | 30 sec | 1 hour | 2+ hours | 5 min | 1+ hour |
| Idiomatic for project size | ✅ | ✅ | ⚠️ (overkill) | ❌ | ❌ |

---

## 5. Recommendation: Option B (split files)

**Why Option B fits this project best:**

1. **Single source of truth preserved.** No content is duplicated; alignments simply move to a different file.
2. **Workflow-appropriate.** When you're working on DG itself (adding classes, refining axioms), you load `DesignGrammar.owl` — clean. When you're auditing alignments or integrating with PROV-aware tooling, you load `DesignGrammar-aligned.owl`.
3. **Matches user mental models.** Most users don't care about cross-vocab axioms day-to-day. Hiding them by default until needed reduces cognitive load.
4. **Composable for downstream.** A downstream consumer who wants only DG can import `DesignGrammar.owl`. A consumer building a full PROV/SHACL/SOSA-integrated knowledge graph imports `DesignGrammar-aligned.owl`. Same ontology, two entry points.
5. **Idiomatic.** SOSA, FOAF, DCAT, BFO, and most modern W3C ontologies use this layering. New users will recognize the pattern.
6. **Cheapest among "clean" options.** A one-hour refactor vs. multi-hour ROBOT setup, with similar outcome.

### Why NOT Option A as the primary recommendation

View filtering works fine for solo Protégé use but **doesn't help anyone who consumes the ontology outside Protégé** — TopBraid Composer, WebVOWL, GraphDB Workbench, custom triplestore loaders, NotebookLM. They all see the unfiltered structure. If even one external consumer is in scope, Option B is strictly better.

### Why NOT Option C

ROBOT module extraction is the **best technical answer** but the operational burden (Java tool, re-extraction on alignment changes, larger repo) exceeds the visual-clutter problem it solves for a 42-class ontology. Reconsider if DG grows past ~200 classes or gets published to a public registry.

---

## 6. Application plan for Option B (if approved)

If you say "apply Option B", the steps are:

1. **Create `[DesignGrammar-aligned.owl](DesignGrammar-aligned.owl)`** — new file with header, 1+7 imports, and the 49 alignment axioms.
2. **Strip from `[DesignGrammar.owl](DesignGrammar.owl)`:**
   - 7 `owl:imports` declarations (lines under `<owl:Ontology>` block)
   - All `owl:equivalentClass` / `rdfs:subClassOf` / `owl:equivalentProperty` / `rdfs:subPropertyOf` axioms referencing external namespaces (~49 total)
   - Update version: 3.3 → 4.0 (breaking change in import structure)
3. **Update `[catalog-v001.xml](catalog-v001.xml)`** — add entry mapping `http://example.org/design-grammar/aligned` → `DesignGrammar-aligned.owl`.
4. **Update `[ONTOLOGY-ALIGNMENT.md](ONTOLOGY-ALIGNMENT.md)`** — document the new two-file pattern, explain when to load which.
5. **Regenerate `[DesignGrammar.md](DesignGrammar.md)`** — auto-export now reflects clean structure.
6. **Verify Protégé:** open core file → 42 classes under 4 hubs, no external clutter. Open aligned file → full hierarchy with imports.

Everything is reversible — the alignment file can be merged back into the core via a script if requirements change later.

---

## 7. Decision required

Pick the path:

| Option | Apply now? |
|---|---|
| **A** — UI filters only | No ontology work; you configure Protégé yourself. |
| **B** — Split into two files ⭐ | I refactor in ~1 hour, hand back clean structure. |
| **C** — ROBOT modules | I write the extraction script + catalog; you install ROBOT and run once. |
| **D** — Strip imports | I remove 7 lines, you accept semantic loss. |
| Stay on v3.3 | No action; live with current state. |

State the choice and I'll execute.
