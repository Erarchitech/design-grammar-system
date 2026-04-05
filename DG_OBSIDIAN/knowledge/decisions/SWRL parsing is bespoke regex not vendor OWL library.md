---
tags: [decision, parsing, swrl, architecture]
date: 2026-04-05
---

# SWRL Parsing is Bespoke Regex Not Vendor OWL Library

## Decision

The `SwrlRuleParser` (in `DG.Core/Parsing/`) parses SWRL expressions using handwritten regex and string splitting — no external OWL, SPARQL, or SWRL parsing libraries.

## Algorithm

```
Input: "Building(?b)^hasHeightM(?b,?h)^swrlb:greaterThan(?h,75)->violatesMaxHeight(?b,true)"
  → Split by "->" → body | head
  → Split body/head by "^" → atom texts
  → Per atom: regex ^(?<predicate>[^(]+)\((?<args>.*)\)$
  → Classify: swrlb: → BuiltinAtom; 1 arg → ClassAtom; 2+ → DataPropertyAtom
  → Arguments: ? prefix → Variable; numeric → Literal(decimal/integer); else → String
  → Deduplicate variables across sides
```

## Rationale

- **Minimal dependency footprint** — DG.Core has only `Neo4j.Driver` as external dependency
- **Targeted parsing** — only needs the SWRL subset used by design grammars (not full OWL)
- **No Java/JVM** — standard OWL libraries (OWL API, SWRL API) are Java; C# equivalents are scarce
- **Control** — custom heuristics for literal type inference (boolean, decimal vs integer, xsd types)

## Trade-offs

- **Limited SWRL coverage** — only handles `ClassAtom`, `DataPropertyAtom`, `BuiltinAtom` patterns
- **Fragile to edge cases** — nested parentheses or unusual IRI characters could break regex
- **No formal grammar** — no BNF/PEG spec; changes require understanding regex internals

## Related

- [[DG Grasshopper plugin bridges Rhino to Neo4j validation pipeline]]
- [[Graph schema v3 is the canonical data model]]
