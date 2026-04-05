---
tags: [business, product, compliance, architecture]
date: 2026-04-05
---

# Design Grammars Automates Architectural Compliance Checking

## What It Does

The Design Grammar System converts **natural language design rules** (e.g., "Maximum building height is 75 meters") into formal **SWRL (Semantic Web Rule Language) expressions** stored as a **knowledge graph** in Neo4j. These rules can then be evaluated against 3D BIM models via a Grasshopper plugin.

## Pipeline

```
Architect writes NL rule
  → LLM translates to SWRL + graph atoms
    → Stored in Neo4j (ontology + metagraph)
      → Grasshopper loads rules
        → Binds Rhino geometry to rule variables
          → Evaluates pass/fail per entity
            → Publishes validation overlay to Speckle 3D
```

## Value Proposition

- **No formal logic knowledge required** — architects write rules in plain English
- **Visual compliance dashboard** — 3D color-coded pass/fail on actual building models
- **Auditable rule graph** — every rule decomposed into inspectable atoms with relationships
- **Editable** — rules can be updated via NL edits, graph updates automatically

## Domain

Urban planning, architectural design compliance, building code verification.

## Related

- [[Target audience is architects and urban planners]]
- [[Product bridges natural language rules to graph-based validation]]
- [[Violation rules invert the constraint in SWRL body]]
