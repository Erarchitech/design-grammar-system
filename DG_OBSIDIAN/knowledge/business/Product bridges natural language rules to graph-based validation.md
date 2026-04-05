---
tags: [business, product, vision]
date: 2026-04-05
---

# Product Bridges Natural Language Rules to Graph-Based Validation

## Core Concept

The product's differentiator is the **NL → SWRL → Graph → 3D validation** pipeline. Users state rules in English; the system handles the formal logic translation, graph storage, and geometric validation.

## Three Interfaces

| Interface | Users | Purpose |
|-----------|-------|---------|
| **Web UI** (Design Grammars) | Planners, reviewers | Define rules, query graph, visualize ontology/metagraph |
| **Grasshopper Plugin** (DG) | Computational designers | Load rules, bind geometry, evaluate, publish results |
| **Model Viewer** | All | 3D validation overlay on BIM models |

## Key Technical Differentiators

- **LLM-powered** — no manual SWRL authoring; inference-time prompt engineering
- **Knowledge graph** — rules decomposed into reusable ontology terms (Classes, Properties)
- **Speckle integration** — results visible in 3D, not just spreadsheets
- **Project-scoped** — multiple projects with isolated rule sets in one deployment

## Product Maturity

Currently in **active development / early prototype** stage:
- Auth is client-side only (localStorage)
- LLM accuracy varies; requires validation of generated Cypher
- Model Viewer has known visual bugs
- No pricing or licensing model yet

## Related

- [[Design Grammars automates architectural compliance checking]]
- [[Target audience is architects and urban planners]]
- [[LLM prompts embed schema constraints instead of fine-tuning]]
