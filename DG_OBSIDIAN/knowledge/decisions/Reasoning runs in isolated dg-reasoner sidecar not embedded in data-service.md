---
tags: [decisions, v8.2, architecture, reasoner]
date: 2026-07-11
---

# Reasoning runs in isolated dg-reasoner sidecar, not embedded in data-service

**Decision:** OWL 2 DL reasoning (Owlready2 wrapping HermiT/Openllet) and SHACL validation (pySHACL) run in a new, dedicated Docker Compose service (`dg-reasoner`), called synchronously over HTTP from `data-service` — mirroring the existing `data-service → n8n` / `data-service → Speckle` call pattern. Not embedded inside the `data-service` FastAPI process.

**Rationale:** Two v8.2 research files disagreed on process placement — `STACK.md` argued for embedding Owlready2 + a headless JRE directly inside `data-service` (avoids a 13th compose service); `ARCHITECTURE.md` argued for a dedicated sidecar (isolates the JVM subprocess's failure modes from `data-service`'s hot path). Resolved in favor of the sidecar because DL reasoning is worst-case exponential and DG's rule corpus grows unboundedly with no size cap — a JVM hang/OOM/crash inside `data-service`'s own process would take down Speckle publish and validation-run retrieval alongside it. The sidecar's failure-isolation property directly prevents that blast radius.

**Tradeoff accepted:** one more container in an already-12+-service `docker-compose.yml`, one more network hop, one more Dockerfile.

**Reversibility:** `pySHACL` (pure Python, no JVM) could move back into `data-service` later as a low-risk follow-up if the sidecar round-trip proves unnecessary for SHACL-only checks — no JVM to isolate for that path. The OWL/HermiT side is not expected to move.

**Scope:** Established for v8.2 (Phase 821: dg-reasoner Sidecar & OntoGraph/Metagraph RDF Translation). See `.planning/research/SUMMARY.md` for the full research trace.

**Date:** 2026-07-11 — established during v8.2 milestone init.
