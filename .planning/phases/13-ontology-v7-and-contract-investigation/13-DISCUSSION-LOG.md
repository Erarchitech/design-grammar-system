# Phase 13: Ontology V7 and Contract Investigation - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-07-03
**Phase:** 13-ontology-v7-and-contract-investigation
**Areas discussed:** DesignState layer, Run status model
**Areas auto-locked (not discussed):** Port↔IRI contract format, Version marker + investigation-note home

---

## Area selection

| Option | Description | Selected |
|--------|-------------|----------|
| DesignState layer | Conflict (b): Metagraph vs ValidGraph placement | ✓ |
| Run status model | Conflict (a): ValidStatus Boolean vs Status text | ✓ |
| Port↔IRI contract format | ONTO-06 deliverable shape | (auto-locked) |
| Version marker + note home | Conflict (c) + investigation-note location | (auto-locked) |

---

## DesignState layer — where does a DesignState node live?

| Option | Description | Selected |
|--------|-------------|----------|
| ValidGraph | Move to `graph='ValidGraph'`; VALIDATOR writes on publish; VALIDATION GRAPH reads from ValidGraph handle (matches PDF wiring); one-time re-tag migration | ✓ |
| Keep in Metagraph | Stay `graph='Metagraph'`; VALIDATION GRAPH must read via Metagraph handle (deviates from PDF wiring) | |
| Dual-layer link | Authored in Metagraph, linked/copied into ValidGraph on publish | |

**User's choice:** ValidGraph
**Notes:** Cleanest — aligns read and write paths with the PDF component wiring; DesignState is run/validation data, not rule/spec data.

### Follow-up: DesignState lifecycle — how does it enter ValidGraph?

| Option | Description | Selected |
|--------|-------------|----------|
| Run-linked only | Persisted only by VALIDATOR on publish, always attached to a Run; no orphans | ✓ (refined) |
| Free-standing allowed | Can be persisted independently of a Run | |

**User's choice (refined):** *"Make Run-linked only but take into account that one DesignState can be linked to many Runs of different rules validations. Important: DesignState passes to ValidGraph only through Validator, so at least one run must be linked to DesignState when DesignState is stored in ValidGraph."*
**Notes:** Cardinality is one-DesignState-to-many-Runs (same state validated against different rules, MERGE'd by StateId+project). No-orphan invariant is a hard constraint.

---

## Run status model — validation outcome field shape

| Option | Description | Selected |
|--------|-------------|----------|
| 3 fields: ValidStatus + Status + SendStatus | Boolean + text enum + Boolean (ONTO-04 proposal) | |
| Status text only | Drop ValidStatus, derive boolean from text | |
| ValidStatus boolean only | Drop Status text; VALIDATION GRAPH shows derived string | ✓ (refined) |

**User's choice (refined):** *"Make ValidStatus boolean only but for all objects in DesignState separately. So the list of boolean values in output."*
**Notes:** Reshaped from a single overall boolean to a **per-object Boolean list** — one element per ObjState.

### Follow-up: list alignment + VALIDATION GRAPH "Status" name

| Option | Description | Selected |
|--------|-------------|----------|
| Index-matched to ObjState list | `ValidStatus[i]` ↔ i-th ObjState; VALIDATION GRAPH "Status" unified to same field | ✓ |
| Keyed by ObjectRef/Label | Each boolean paired with its object's ref | |
| Boolean list + derived text summary | Extra computed text output | |

**User's choice:** Index-matched to ObjState list
**Notes:** PDF's ValidStatus/Status name difference recorded as cosmetic; unified to `ValidStatus`.

### Follow-up: per-object ValidStatus storage

| Option | Description | Selected |
|--------|-------------|----------|
| Boolean array property on Run | `Run.ValidStatus = [true,false,...]` list property, index-matched | ✓ |
| Per-object edge with boolean | `Run-[:VALIDATED {valid}]->ObjState` | |
| Embed in statePayloadJson | Store results inside serialized payload | |

**User's choice:** Boolean array property on Run
**Notes:** Lowest migration/query surface; Phase 14 writes the actual Cypher.

### Follow-up: SendStatus scope

| Option | Description | Selected |
|--------|-------------|----------|
| Single Boolean per Run | One publish-success value per run | ✓ |
| Per-object Boolean array | Mirror ValidStatus | |

**User's choice:** Single Boolean per Run
**Notes:** Publishing is one operation per run; orthogonal to per-object ValidStatus.

---

## Claude's Discretion
- Exact relationship type/direction/label for the Run→DesignState link (Phase 14 cypher design).
- Column ordering/formatting of `port-iri-map-V7.md`.
- Whether the stale `v3` ontology comment is deleted vs. rewritten to `v7`.

## Auto-locked resolutions (recommendation accepted implicitly via "Ready for context")
- **Port↔IRI map:** `ontology/port-iri-map-V7.md` — single markdown table (`Component | Port | Direction | V7 IRI | Layer | Notes`), all 14 components; supersedes `GH-mapping.png`.
- **Version marker:** V7 owl `owl:versionInfo = "7.0"`; remove stale `Schema version: v3` comment; single version source = `versionInfo`.
- **Investigation note home:** `ontology/V7-INVESTIGATION.md`; condensed decision mirrored to `DG_OBSIDIAN/knowledge/decisions/` at session-save.

## Deferred Ideas
- Research flag (Phase 18): per-object ValidStatus *population* semantics — all ObjStates vs. only rule-target-Class objects. Shape + index-matching locked here; binding rule belongs to Phase 18.
