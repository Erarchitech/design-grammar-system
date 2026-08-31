---
tags: [decision, ontology, design-state, design-space, fbs, dissemination, t1, t3, t4]
date: 2026-08-31
---

# DesignState movement typing requires design-space membership

## Decision

A typed relation between Design States — one that names *how* a scheme moved, in Gero's
formulation/reformulation sense — **cannot be derived from a pairwise comparison of two states**.
It requires one additional property the schema does not carry: **which design space and partition
each state belongs to**.

Recorded while resolving comment C45 on `T1_ITcon_DG_Draft_R14.3.docx`. T1 § 6.1 now states this
precondition rather than the derivation rule that `R14.4` proposed.

## Why the pairwise derivation fails

`R14.4` § 6.1 had specified a rule: *a typed relation between successive Design States, whose type
follows from the states themselves* —

- `PropState` differs → Function recast → **reformulation**
- `ObjState` or `ParamState` differs while Function holds → **refinement**

Two independent defects:

**1. There is no single successor.** A Design State trail is not necessarily forward or backward.
States may be:

- **alternatives within one design space** — three facade options explored side by side;
- **members of different design spaces** — one set describing facade design, another the plan layout
  of the same building;
- **separated by typology inside one design space** — a hexagonal glazed facade set beside a timber
  structural facade set, for the same object.

`CapturedAtUtc` gives a total time order (required and validated — see
`DG/src/DG.Core/Serialization/DesignStateJsonSerializer.cs`), but time-ordering two alternatives does
not make them a movement.

**2. Reformulation redefines a state space, not a link between two states.** In the situated-FBS
framework the reformulation types are `S→S'`, `S→Be'`, `S→F'` — each *redefines what counts as a
candidate*. So a differing `PropState` is ambiguous between:

- an alternative admitted by the *current, unchanged* Function space, and
- evidence that the Function space itself was recast.

A pairwise diff cannot separate these. `R14.4`'s rule reads the first case as the second.

## What the schema would need

Partition membership on the state — enough to answer *"are these two states comparable at all?"*
before asking *"how do they differ?"* Given that:

- a difference **within** one partition reads as refinement, its Function intact;
- a change **of** partition is where reformulation shows up;
- states in **different design spaces** (facade vs plan) are not on a common axis and should not be
  compared as movement at all.

Terminology from the design-theory literature, for whoever implements this: **design space** /
**sub-space**; **alternative set** (mutually exclusive, one selected) vs **variant set** (retained in
parallel); **partitioned design space by typology** (`DS = ⋃ᵢ DSᵢ`); **design trajectory** for the
temporal axis. The summary distinction is *branching in space* vs *movement in time*.

## Publication boundary

Per [[../../dissemination/Series coherence map|Series coherence map]] this belongs to the companion
papers, not T1:

| Concept | T1 | T3 | T4 |
|---|---|---|---|
| OntoGraph/Metagraph schema | **defines** | ref | ref |
| DesignStateSnapshot, REINSTATE | — | **defines** | ref |
| DesignSpaceGraph, MetricSpec | — | — | **defines** |

- **T3** already owns non-linear navigation — its case study is *3 massing alternatives, 9 runs* with
  REINSTATE for exactly this.
- **T4** owns the design space itself: `Σ = collection of DesignSpacePoint`, the `DesignSpaceGraph`
  fourth layer, partitioning, metrics.

T1 therefore names the requirement and formalises nothing — no `DesignSpaceGraph`, no `MetricSpec`,
no forward citation.

## Consequences

- **Schema (future).** `DesignState` needs partition/design-space membership before any movement
  relation can be typed. This is a prerequisite for T4's `DesignSpaceGraph`, not an alternative to it.
- **No implementation change now.** T1 fixes a pre-implementation stage; the paper is the foundation
  for later schema changes rather than a description of shipped behaviour.
- **Avoid the phrasing.** `an ordered series DS_t0 … DS_tn` and `the route a scheme travelled` both
  presume a single trajectory. Both were removed from T1 § 3.3 for this reason.

## Related

- [[../../dissemination/revisions/T1 R14.3 — R14.4 package port and C45 resolution|Revision log — R14.3]]
- [[../../sessions/2026-08-31 T1 R14.3 — R14.4 package port, FBS mapping and C45|Session note]]
- [[DesignState persists to ValidGraph not Metagraph]]
- [[../../dissemination/T3 — Отслеживание состояний]] · [[../../dissemination/T4 — Дизайн-пространство]]
