---
tags: [decision, ontology, architecture]
date: 2026-06-01
---

# Decision: DG Ontology Must Be Vendor-Neutral (except Grasshopper and IFC)

## Decision

The DG ontology files must **not** reference any specific third-party technology, platform, or product. Only two named exceptions are permitted: **Grasshopper** (the authoring environment the system is built for) and **IFC** (the open BIM exchange standard). External standard-vocabulary alignments (W3C/OGC: SWRL, PROV-O, SOSA, SHACL, SKOS, DCTerms, GeoSPARQL; BOT; Topologic) are legitimate links to open ontologies and are not coupling.

## Rationale

Baking a vendor name (e.g. Speckle) into DG-native properties and classes:
- Makes the ontology non-reusable with any other geometry/viewer platform.
- Conflates *what the concept is* with *how the current stack implements it*.
- Requires ontology revisions whenever the technology stack changes.

## What This Means Concretely

- Properties on `IntegrationConfig` / `ValidationRun` / `GeoRef` must describe generic roles (external project ID, external model version, source-system handle) — not vendor-specific IDs.
- Example ABox instances should use neutral provider values and generic handle formats.
- Comments must not mention Speckle, Rhino, or other specific products as the *only* possibility.

## Applied in v6.1

Renamed `dgv:speckleProjectId` → `dgv:externalProjectId`; scrubbed Speckle/Rhino from all DG-owned comments and ABox instances across the three V6 ontology files. See session note `[[sessions/2026-06-01 Ontology v6.1 vendor-neutralization]]`.
