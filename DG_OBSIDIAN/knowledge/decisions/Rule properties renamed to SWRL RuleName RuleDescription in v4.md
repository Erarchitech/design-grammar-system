---
tags: [decision, schema, v7.0, v4]
date: 2026-07-03
---

# Rule properties renamed to SWRL/RuleName/RuleDescription in schema v4

## Decision

The v4 write side (`cypher_template.txt`, `training/dataset_schema.json`, both n8n prompts) emits the ontology-exact Rule property names in **PascalCase**: `SWRL` (was `text`), `RuleName` (was `title`), `RuleDescription` (new, optional) — matching `dgm:SWRL`/`dgm:RuleName`/`dgm:RuleDescription` from `ontology/port-iri-map-V7.md`.

Readers keep `coalesce(new, old)` for backward compatibility. Phase 14 patches the two coalesce lines in `DG/src/DG.Core/Data/Neo4jRuleRepository.cs`:
- `coalesce(r.swrl, r.text, '')` → `coalesce(r.SWRL, r.swrl, r.text, '')`
- `coalesce(r.title, r.name, r.Rule_Id)` → `coalesce(r.RuleName, r.title, r.name, r.Rule_Id)`

## Why

Three options were on the table: full rename now, SWRL-only minimal change, or documentation-only mapping (keep `text`/`title`, just note the ontology equivalence). Full rename won because a quick grep of `Neo4jRuleRepository.cs` showed the read-side was **already half-migrated** — it coalesces `r.swrl→r.text` and `r.title→r.name` — so the actual blast radius of a full rename was much smaller than assumed, and deferring it would leave the Rule schema half-migrated across two phases (14 then 18) for no benefit.

PascalCase (not lowercase `swrl`) was chosen deliberately so the DB property names match the port↔IRI contract exactly — worth a small C# patch rather than compromising the casing to fit the old lowercase coalesce.

## Consequences

- New rules ingested after Phase 14 carry `r.SWRL`/`r.RuleName`/`r.RuleDescription`; old rules keep `r.text`/`r.title` until re-ingested or migrated.
- `Neo4jRuleRepository.cs` must be patched in Phase 14 (not deferred to Phase 17/18) or current-component validation reads would see empty SWRL for newly-ingested rules.
- `data-service/app.py` does not touch these properties — confirmed via grep, no changes needed there for this rename.
- Phase 18 (RULE DECONSTRUCT rework) reads the real renamed properties directly instead of working around port-only names.

## See also

- [[sessions/2026-07-03 Phase 14 discuss - schema v4 propagation decisions|Session: Phase 14 discussion]]
- [[Ontology V7 full rename over incremental]] — the ontology-side rename this DB-side rename mirrors
- [[Graph schema v3 is the canonical data model]] — superseded by v4
