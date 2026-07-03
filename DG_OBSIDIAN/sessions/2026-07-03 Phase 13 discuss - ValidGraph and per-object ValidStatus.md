---
tags: [session, phase-13, v7.0, ontology, discuss]
date: 2026-07-03
model: claude-opus-4-8
---

# 2026-07-03 — Phase 13 discussion: ValidGraph placement and per-object ValidStatus

## Context

Ran `/gsd-discuss-phase 13` (Ontology V7 and Contract Investigation). This phase's job is to resolve the PDF-internal conflicts flagged when the v7.0 milestone was initialized ([[sessions/2026-07-02 v7.0 milestone init from GH_DesignGrammars schema|prior session]]) and lock the naming contract phases 14–20 build on. Most of the rename (full V6→V7, state-trio names, port policy) was already decided at milestone init — this session only needed to resolve the two genuinely open conflicts plus two mechanical items I locked with recommendations.

## What was done

1. Loaded PROJECT.md / REQUIREMENTS.md / STATE.md / ROADMAP.md, the prior decision note ([[decisions/Ontology V7 full rename over incremental]]), and the milestone-init session note — no other CONTEXT.md files exist yet (Phase 13 is the first v7.0 phase discussed).
2. Confirmed the exact conflict spot in `cypher_template.txt` (lines 49-50, 113-116: `DesignState … graph='Metagraph'`).
3. Presented 4 gray areas; user selected **DesignState layer** and **Run status model** for live discussion, leaving **port↔IRI contract format** and **version marker + note home** for me to lock with recommendations.
4. Discussed and resolved both selected areas (see decisions below).
5. Wrote `13-CONTEXT.md` + `13-DISCUSSION-LOG.md` in `.planning/phases/13-ontology-v7-and-contract-investigation/`.

## Key decisions (user-confirmed)

- **DesignState moves from `graph='Metagraph'` to `graph='ValidGraph'`** — matches the PDF's `VALIDATION GRAPH` component reading Run/Status/DesignState from the ValidGraph handle. The PDF's *"only through Validator"* constraint is preserved; only the destination layer changes. User added an important refinement: **one DesignState can be linked to many Runs** (same state validated against different rules), and a DesignState must have **≥1 Run linked** whenever it's in ValidGraph (no orphans) — because Validator-only-write is the sole entry path.
- **`Run.ValidStatus` reshaped to a per-object Boolean array**, index-matched to the DesignState's ObjState list, instead of the originally-proposed single overall Boolean + separate text `Status` field. User: *"Make ValidStatus boolean only but for all objects in DesignState separately. So the list of boolean values in output."* No `Status` text enum — `VALIDATION GRAPH`'s `Status` output unifies to the same `ValidStatus` field (PDF's Boolean-vs-text naming treated as cosmetic, not two fields). `Run.SendStatus` stays a single Boolean per Run (orthogonal, publish success).
- Storage mechanics: `ValidStatus` as a **Boolean list property directly on Run** (not per-object edges, not embedded in statePayloadJson) — simplest read/write, reuses the index-matched list contract already used elsewhere in the schema.
- **Auto-locked (not discussed, recommendation accepted):** port↔IRI map ships as one markdown table `ontology/port-iri-map-V7.md` (successor of the non-machine-readable `GH-mapping.png`); V7 owl sets `versionInfo="7.0"` and drops the stale `Schema version: v3` comment; investigation note lives at `ontology/V7-INVESTIGATION.md`.

→ Full decision rationale: [[decisions/DesignState persists to ValidGraph not Metagraph|DesignState persists to ValidGraph not Metagraph]], [[decisions/Run ValidStatus is a per-object boolean array|Run ValidStatus is a per-object boolean array]]

## Result

`.planning/phases/13-ontology-v7-and-contract-investigation/13-CONTEXT.md` + `13-DISCUSSION-LOG.md` written (not yet committed — `commit_docs: false` in this project's GSD config, session-end commit handles it). `.planning/STATE.md` updated via `state.record-session`.

**Open item flagged for Phase 18:** the per-object `ValidStatus` array's *population* rule (does it cover all ObjStates in the DesignState, or only those matching the rule's target Class?) is not decided here — Phase 13 only locks the array shape and index-matching; binding semantics belong to VALIDATOR's rework (GHVL-04).

**Next:** `/gsd-plan-phase 13` (research likely skippable — internal restructuring driven by the user's own schema, same reasoning as the milestone-init session).

## Graph connections

- [[sessions/2026-07-02 v7.0 milestone init from GH_DesignGrammars schema|Prior session: v7.0 milestone init]] — where the conflicts this session resolves were first flagged
- [[decisions/Ontology V7 full rename over incremental|Ontology V7 full rename over incremental]] — the broader rename decision this phase implements
- [[decisions/DesignState persists to ValidGraph not Metagraph|DesignState persists to ValidGraph not Metagraph]]
- [[decisions/Run ValidStatus is a per-object boolean array|Run ValidStatus is a per-object boolean array]]
- [[Graph schema v3 is the canonical data model]] — superseded by the schema v4 this phase's decisions feed into
- [[DCM ComputationGraph as 5th ontology layer]] — same ontology, adjacent layer
