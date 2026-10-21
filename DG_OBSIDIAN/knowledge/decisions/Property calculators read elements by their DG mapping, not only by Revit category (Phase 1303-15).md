---
tags: [decision, phase-1303, revit, property-calculator, mapping]
date: 2026-10-21
status: implemented (commit 72e5f79)
---

# Property calculators read elements by their DG mapping, not only by Revit category (Phase 1303-15)

**Context.** The column rule reported 0 violations, while boxes 4861769, 4861053 and 4861787 clearly cross column 4711685. That column is modelled as a wall (category «Стены», type «В25 250мм Пилон») and is a column only through the DG mapping (`DG_Class = Column`). The model has no element in `OST_StructuralColumns` or `OST_Columns`, but 284 elements mapped as Column. The calculator read only the categories behind the Column class, so it never saw the pylons, and the column run showed no column in the Model Viewer.

**Decision.** The DG mapping outranks the Revit category in `ModelContext.candidates()` (`data-service/property_calculators/calculator_shell.py.tmpl`):
- An element whose `DG_Class` names the class behind the requested categories (catalogue `categoryClasses`) is read whatever its category. These elements are found once per run in the categories `DG_Class` is bound to.
- An element of a requested category whose `DG_Class` names *another* catalogue class leaves that category. A pylon mapped Column is not a wall, so it is not a host wall for R3/R4.
- An element whose `DG_Class` is not a catalogue class (e.g. a subclass) stays in its category.
- A mapping with `DG_MappingState = rejected` does not reclassify.
- The context label carries the category the element was read as (`OST_Columns|Стены : … [4711685]`), so the Model Viewer shows it with the column rule.
- The calculator report lists `inventory DG_Class <class>: n`.

**Effect (live, 2026-10-21).**
- R2 columns: 0 → 4 violations, including the three boxes the owner named.
- R1 beams: 0 → 1. 90 elements are mapped as Beam against 86 in the framing category.

**Why.** Mapping is DG's statement of what an element *is*. A Revit category is only how it was modelled, and structural models often model pylons as walls.

Related: [[sessions/2026-10-21 Phase 1303-15 MEP opening boxes checked in Revit through Rhino.Inside and VALIDATOR|session]], test `test_an_element_mapped_to_a_class_is_read_as_that_class_whatever_its_revit_category`.
