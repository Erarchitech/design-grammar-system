---
tags: [debugging, grasshopper, parameterstate, security, open]
date: 2026-10-05
status: open
---

# Grasshopper Panels can neither be captured as parameters nor safely carry tokens (F7, F17)

## F7 — PARAMETER STATE / REINSTATE do not support Panel

The facade drove its module widths from a **Panel** holding a list of numbers (one per facade).

- PARAMETER STATE accepts only scalars (number/int/bool) with item access (`ParameterStateComponent.UnwrapScalar`). Panel outputs `GH_String`, so the component warns "type unsupported" and captures nothing. A list on an item input would also multiply the snapshots.
- PARAMETER REINSTATE writes only to `GH_NumberSlider` / `GH_BooleanToggle`. For a Panel it adds volatile data, which the next solution overwrites.

**Workaround used:** one slider per facade (`Module Width F1…F5`), joined with `Merge` into the old receiver.

## F17 — a token in a Panel ends up in the .gh

The `Platform Token` input (`NonPersistentStringParam`) strips its value on save. If the token comes from a **Panel**, though, the Panel persists its text, and the token was found in the saved `.gh`. The file was in `.gitignore` and never committed, and the owner accepted the risk for the test project. CONNECTOR/VALIDATOR give no warning about a persistent token source.

**Proposed:** warn when the token source is a `GH_Panel` or another persisted parameter, and document "paste via Set value, never a Panel".

## Related

- [[sessions/2026-10-05 v12 hexagonal facade test steps 2-8 and five DG fixes]]
