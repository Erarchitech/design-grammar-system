# Multi-participant rule extraction — design

Status: approved by the owner 2026-10-21; work happens in the `dg-mapping`
worktree on `feature/mapping-mvp`. Nothing in this document is built yet.

## 1. Intent and why

Architects write rules about relations between several kinds of building
objects: *"An opening in a slab may not be closer than 500 mm to the outline
of the projection of columns and walls onto that slab."* Today the rule-ingest
LLM reduces every rule to **one class, one datatype property, one comparison**.
For the example above it produced

```
Opening(?o) ^ hasMinProjectionClearanceMm(?o, ?d) ^ swrlb:lessThan(?d, 500)
  -> hasProjectionClearanceViolation(?o, true)
```

`Slab`, `Column` and `Wall` and the relations between them never reach the
graph (live project `str-openings-01`, rule `R_OpeningSlabEdgeClearance500`,
2026-10-21). The architect sees a rule that does not say what he wrote, the
ontology has no `Slab` class, and the property-calculator generator (phase 1303,
`PropertyCalculator` nodes) gets no information about which objects take part
in the measured quantity.

The owner's requirement: the LLM must extract **all object classes** named in
the rule and **the relations between them**, not only the class of the checked
object.

### Why the current behaviour happens (root causes, verified 2026-10-21)

1. `cypher_template.txt` ("CYPHER TEMPLATE BLOCK") and all six shapes in
   `llm/cypher_catalog.json` show exactly one `C_Main` class. The LLM copies
   the example.
2. Shape selection (`data-service/dg_context.py` `_SHAPE_KEYWORD_PATTERNS`) is
   English-keyword substring matching. A Russian rule selects no shape, so the
   LLM falls back on the single-class template block.
3. The assembled prompt (`/context/assemble` → n8n "Build LLM Prompt") says
   "you MUST reuse existing entities" and never asks the model to enumerate
   participants or relations. `ObjectProperty` is allowed by the allowlist but
   never used (zero `ObjectProperty` nodes in `str-openings-01`).
4. The C# evaluator refuses `ObjectPropertyAtom` with `unsupported`
   (`spec/SWRL-SUBSET.md` §2) and aborts a rule at the first atom that is not a
   match (`RuleEvaluator.EvaluateBody`). A relation written naively into the
   body would turn a rule that is checkable today into `unsupported`.
5. Binding rows are built **per ObjState**: a row carries the object variables
   whose class equals that single ObjState's class
   (`DesignStateBindingService.BuildBindings`). A rule with two object
   variables (`?o` Opening, `?s` Slab) therefore yields rows where one variable
   is unbound → `unknown`. Multi-object joins do not exist.

## 2. Owner decisions (as given)

- **D1 (2026-10-21):** option (a): the evaluator treats object-property relations
  as preconditions that are *not* evaluated as constraints, so a rule with
  relations stays checkable; it must not turn `unsupported`.
- **D2 (2026-10-21):** every participant class of a rule is passed to the
  property calculator of the rule's measured property. The participants are what
  binds a calculator to the concrete model elements it computes over, once those
  elements are mapped to the classes.

## 3. Goals

- **G1 Participants.** For every rule the LLM extracts every physical/building
  object class the rule mentions (e.g. Opening, Slab, Column, Wall). Each is
  reused from the project's OntoGraph when it exists, otherwise created as a new
  `Class`. Rule text that names no object beyond the checked one still produces
  exactly today's single-class result.
- **G2 Relations.** The LLM extracts each relation between two participants as
  an `ObjectProperty` (reused or created) and as an `ObjectPropertyAtom` in the
  rule body, with a `ClassAtom` for each participant.
- **G3 One measured subject.** Exactly one variable is the *subject*: the
  variable in position 1 of the head (violation) atom. The measured quantity
  stays a `DatatypeProperty` on the subject, tested by a builtin, as today.
  Quantities that depend on other participants (clearance to a projected outline)
  are modelled as a single derived datatype property of the subject; the
  relations record which participants the derivation uses.
- **G4 Evaluator keeps such rules checkable.** Introduce the notion of a
  *context-only variable* (§4). Rules with participants and relations evaluate
  exactly like their one-class form, with the unverified participants and
  relations disclosed in the result text.
- **G5 Language-independent prompting.** The participant/relation instruction
  is part of every ingest prompt irrespective of shape selection, and the
  existing shapes get Russian keyword synonyms.
- **G6 Conflict check still keys on the subject.** `/rules/check-conflict`
  keeps its (Class, DatatypeProperty, comparator) key, where Class is the
  *subject's* class, never "the first class mentioned".
- **G7 Acceptance example.** Re-ingesting (Edit) `R_OpeningSlabEdgeClearance500`
  in `str-openings-01` yields a rule whose graph shows Opening, Slab, Column and
  Wall and the relations between them, and which still validates exactly as
  before against the same design state.

## 4. Semantics of option (a), refined against the code

*Context-only variable*: a variable that appears **only** in `ClassAtom` and
`ObjectPropertyAtom` atoms of the rule body, never in a `DataPropertyAtom`,
`BuiltinAtom` or head atom. (`?s`, `?c`, `?w` in the example; `?o` and `?d` are
not context-only.)

- **Binding construction** (`DesignStateBindingService`) excludes context-only
  variables from the object variables it binds, so no unbound-variable rows and
  no rows for objects of the participant classes.
- **Evaluation** (`RuleEvaluator.EvaluateAtom`): a `ClassAtom` whose subject is
  context-only, and an `ObjectPropertyAtom` whose arguments are context-only or
  the subject, count as matched without resolving the context-only variables.
  They are *asserted by the rule*, not independently verified; the rule's
  result detail states that, and no new status is added.
- An `ObjectPropertyAtom` that involves a variable which is **not** context-only
  and not the subject (multi-object join) keeps today's behaviour: `unsupported`.
  Likewise a context-only variable that is later given a `DataPropertyAtom`
  stops being context-only and the rule is `unknown`/`unsupported` as today.
- `UnsupportedAtom`, unknown builtins, missing variable values keep their
  current statuses.

Illustrative expected SWRL for the acceptance example (final form is the
builder's call within these rules):

```
Opening(?o) ^ Slab(?s) ^ hostedBy(?o, ?s) ^
Column(?c) ^ projectsOnto(?c, ?s) ^ Wall(?w) ^ projectsOnto(?w, ?s) ^
hasMinProjectionClearanceMm(?o, ?d) ^ swrlb:lessThan(?d, "500"^^xsd:integer)
  -> hasProjectionClearanceViolation(?o, true)
```

## 4a. Property calculators receive the participants (D2)

Today (branch `feature/mapping-mvp`, worktree `C:\Users\Admin\source\repos\dg-mapping`,
`data-service/property_scripts.py`, `property_calculator_store.py`):

- A calculator's classes are derived **bottom-up**: from the Revit categories
  its script reads (catalogue `reads`, or AST of an LLM-generated source), mapped
  through `catalogue.json` `categoryClasses` to class labels, then linked with
  `READS_CLASS`. The rule plays no part. Live result for
  `hasMinProjectionClearanceMm` in `str-openings-01`: `READS_CLASS` → Wall,
  Column, **Beam**; no Slab, although the rule speaks of columns and walls
  projected onto the slab.
- `resolve()` raises `BOX_CLASS_AMBIGUOUS` unless all rules in the request test
  exactly one class, and `link_calculators()` silently skips any rule with more
  than one class. A multi-participant rule would stop script generation for the
  whole project, not only for itself.

Required behaviour:

- **Top-down authority.** The rule's participants are authoritative for which
  classes a calculator reads. The subject's class is the *box class* (the
  element the property is computed for); the context-only participants are the
  classes it reads. `READS_CLASS` is written from them.
- **Box class = subject class.** `resolve()`/`generate()` group rules by subject
  class instead of requiring one class across all ClassAtoms; context
  participants no longer count towards `BOX_CLASS_AMBIGUOUS`. One-class rules
  behave exactly as today.
- **Relations travel with the participants.** Each participant passed to a
  calculator carries the relation that ties it to the subject or host
  (`hostedBy`, `projectsOnto`, …), so the generator and catalogue resolution
  know the role of each class (host slab vs projecting elements).
- **Elements come from mapping.** A calculator selects model elements by
  their mapped `DG_Class`, i.e. by participant class. Revit categories of a
  class come from the class/mapping side (`revitCategories`, mapping
  profiles), not from what a script happens to read.
- **Script reads are checked, not trusted.** The categories a stored or
  generated script reads (AST / catalogue `reads`) are compared with the
  participants' categories. A script that reads a class the rule does not name,
  or misses a participant, is reported as a mismatch and is not silently
  relinked.
- **Context classes created by DG.** The existing reuse by label and
  same-concept check (`class_duplicates`, e.g. Floor vs Slab) applies to
  participants too, so the rule ingest and the calculator side never create two
  classes for one concept.

## 5. Non-goals

- Verifying relations (geometric hosting/projection checks) or joining several
  objects into one binding row. Relations are declared, not checked.
- New relationship types (`DOMAIN`, `RANGE`, …). OntoGraph stays the flat
  vocabulary documented in `spec/LPG-OWL-MAPPING.md`; relation structure lives in
  the rule's atoms, which the Graph Viewer already draws. (My call: an optional
  `domain` string property is added to `ObjectProperty` next to its existing
  `range`.)
- A new evidence status, OWL inference, negation, disjunction semantics.
- Changing the violation pattern, Rule_Id format, or rule separation principle.
- Automatically re-ingesting existing rules; only the acceptance rule is redone.
- Changing the n8n webhook contract or the UI ingest flow.

## 6. Anti-goals (a failure even if it "works")

- A rule that evaluates today becoming `unsupported`/`unknown` because it gained
  participants.
- Classes invented for things that are not objects (an "outline", a "clearance",
  a "projection" is a derived geometric quantity, not a class).
- Ontology bloat: duplicate classes for synonyms of an existing class.
- Two-constraint rules merged into one because they share participants.

## 7. Constraints

- LLM output stays inside the existing Cypher allowlist
  (`data-service/cypher_allowlist.py`): MERGE/SET/MATCH only, one statement, no
  new labels or relationship types. Every atom has exactly one `REFERS_TO`.
- Rule-ingest remains `model-dependent` in `spec/REPRODUCIBILITY.md`; that
  contract's machine-checked block must still hold.
- Schema Change Propagation (CLAUDE.md) applies: `cypher_template.txt`,
  `llm/cypher_catalog.json`, `training/dataset_schema.json` and training data,
  n8n prompt text, `spec/DATABASE.md`, `spec/LPG-OWL-MAPPING.md`,
  `spec/SWRL-SUBSET.md` (including its two machine-checked fenced blocks and the
  conformance tests), `spec/EVIDENCE-CONTRACT.md` if the result detail wording
  is contractual, `ontology/dg-shapes.ttl`, `.github/copilot-instructions.md`,
  `README.md`.
- Prompt logic lives in `data-service` (`dg_context.py`, `llm/`), not n8n; live
  n8n workflows have drifted from `n8n/workflows/*.json`, so no change may depend
  on editing the live workflow.
- GH canvas compatibility: `Neo4jRuleRepository` and `VariableTypeInferrer` (which
  classes any `ClassAtom`/`ObjectPropertyAtom` argument as Object) must keep
  working for old one-class rules.

## 8. Verification

- Golden parser/evaluator fixtures and `SwrlSubsetConformanceTests` cover: a
  one-class rule unchanged; a rule with context participants and relations
  evaluated like its one-class form; a multi-object join still `unsupported`.
- `data-service` tests: Russian rule text reaches the participant instruction;
  allowlist accepts the new output shape; conflict check keys on the subject.
- Live: Edit `R_OpeningSlabEdgeClearance500` in `str-openings-01` against the
  rebuilt stack; Graph Viewer shows the four classes and the relations; the
  validation result for the existing design state is unchanged.
- Calculators: a project mixing one-class and multi-participant rules generates
  scripts without `BOX_CLASS_AMBIGUOUS`; the calculator of
  `hasMinProjectionClearanceMm` is linked to the rule's participants and its
  Beam/Slab mismatch with the stored script is reported.

## 8a. Calls made after the builder check (author's calls, not owner decisions)

- **Canvas.** Context-only variables are hidden from the Grasshopper
  `RuleDeconstruct` "Objects" outputs and from binding, using one shared
  classifier in `DG.Core` used by the binder, the evaluator and the deconstruct
  component. Participant classes need no ObjStates and no Computgraph Objects;
  they are pure ontology entries. G7 therefore holds on the canvas as well.
- **Subject choice.** The subject is the object the rule flags as non-compliant
  (the head's position-1 variable). A quantity that genuinely involves two
  objects is always collapsed into one derived datatype property of the subject;
  the LLM never emits a multi-object join and never refuses for that reason.
- **"Unchanged result" (G7)** means status, failing bindings and rule identity
  unchanged. The disclosure wording is a detail/message text, not a stable field:
  it is not pinned by a golden fixture or SHACL shape unless the builder finds
  `spec/EVIDENCE-CONTRACT.md` already pins detail text, in which case the
  builder updates that contract and fixtures in the same change.
- **Reuse matching** stays prompt-driven by semantic match against the existing
  entity list. New classes use English PascalCase IRIs like the existing ones.
  No language detection. Russian synonyms are added to the six existing shapes
  only.
- **Acceptance gate.** All logic is tested deterministically (stubbed LLM output
  through the allowlist, parser and evaluator). The Edit of
  `R_OpeningSlabEdgeClearance500` is a live check with the project's configured
  provider; up to three attempts, reported honestly, not a CI gate.
- **Orphan ontology nodes.** `Class` and `ObjectProperty` nodes are
  project-scoped vocabulary shared across rules. Edit and rule delete do not
  remove them (same as `Class`/`DatatypeProperty` today). `domain` is written
  with MERGE+SET on creation and is idempotent.

- **Calculator calls (D2).**
  - A calculator stays keyed by (project, dataPropertyIri). If several active
    rules use one property with different participant sets, its `READS_CLASS` is
    the union and the difference is reported.
  - A stored generated calculator whose script reads disagree with the
    participants is marked stale. It is regenerated only through the existing
    generation flow with the owner's confirmation, because generation is a paid
    LLM call. For the acceptance rule this means the Beam/Slab mismatch is
    reported, not quietly fixed.
- **No `USED_WITH` usage edges now.** Rule atoms and `READS_CLASS` already
  record usage. Governed domains and ranges belong to the phase 1302 company
  vocabulary.
- **Where the work happens.** Calculator code exists only on
  `feature/mapping-mvp`, so the whole change is built in the `dg-mapping`
  worktree on that branch, not on `feature/hosting-dg-pilot`.

## 9. Left to the builder

Prompt wording; new catalog shape name(s) and few-shot examples; how context-only
variables are represented in the C# model; exact result-detail text; Russian
synonym list; how `domain` is written; test fixtures; migration of the
acceptance rule.
