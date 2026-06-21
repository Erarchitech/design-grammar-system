---
tags: [atlas, schema, v3, ontology, swrl]
date: 2026-04-05
graphify_communities: ["Graph Schema v3 is the Canonical Data Model", "LLM Prompt Engineering", "Match Step (Neo4j Full-Text Search, No LLM)", "Model Viewer (graph-viewer/model-viewer/)", "Phase 03 Validation Runs Summary", "Phase 3: n8n Knowledge Workflows + LLM Ingest/Query", "Product Bridges Natural Language Rules to Graph-Based Val...", "SpeckleProjectConfigPayload", "Validation Endpoints (publish/runs/view)", "Validation Endpoints (publish/runs/view)", "Validation Results Publish to Speckle as Overlay Versions", "Worktree Branch Commits with Spurious Deletions", "code: 17 nodes", "code: rule", "extractErrorMessage()", "n8n Workflow Orchestrator", "n8n Workflow Orchestrator for LLM Rule Ingestion and Queries", "v4.0 BOT Ontology Bridge"]
---

# Graph Schema v3 is the Canonical Data Model

The v3 schema (defined in `training/dataset_schema.json` and `cypher_template.txt`) is the single source of truth for all generated Cypher, UI labels, prompts, and validation logic.

## Schema Files

| File | Role |
|------|------|
| `cypher_template.txt` | v3 Cypher template with placeholders — LLM prompt source |
| `training/dataset_schema.json` | Formal JSON schema for node types, keys, properties |
| `training/updated_cypher_reference_examples_v3.cypher` | Complete reference Cypher examples |
| `graph-viewer/config.template.js` | NeoVis label/display configuration matching v3 |

## Rule ID Format

```
R_<DOMAIN>_<PROPERTY>_<LIMIT>_V
Example: R_URB_HEIGHT_MAX_75_V
```

## Atom ID Format

```
Body atoms: {Rule_Id}_A1, _A2, _A3, ...
Head atoms: {Rule_Id}_H1, _H2, ...
```

## IRI Prefixes

- `ex:` — domain terms (classes, properties, violation predicates)
- `swrlb:` — SWRL builtins (greaterThan, lessThan, equal, notEqual)

## Semantic Mapping (Violation Pattern)

| NL Phrase | SWRL Body Builtin | Meaning |
|-----------|-------------------|---------|
| "Maximum / at most X" | `swrlb:greaterThan(?val, X)` | Body fires when value exceeds limit |
| "Minimum / at least X" | `swrlb:lessThan(?val, X)` | Body fires when value is below limit |
| "Equal to X" | `swrlb:notEqual(?val, X)` | Body fires when value differs |
| "Between min and max" | Two separate rules | One for min, one for max |

See [[Violation rules invert the constraint in SWRL body]].

## Mandatory Propagation

When changing graph generation or query logic, update ALL:
1. `cypher_template.txt`
2. `training/dataset_schema.json`
3. n8n workflow prompts and validators
4. `graph-viewer/config.template.js` (NeoVis labels)
5. Any Cypher templates/parsing logic in Python/JS

## Related

- [[Neo4j stores ontology and metagraph in a single database]]
- [[LLM prompts embed schema constraints instead of fine-tuning]]
- [[Cypher MERGE idempotent node creation pattern]]

<!-- graphify:connections:start -->
## Graph connections

- [[graphify/communities/Graph Schema v3 is the Canonical Data Model|Graph Schema v3 is the Canonical Data Model]]
- [[graphify/communities/LLM Prompt Engineering|LLM Prompt Engineering]]
- [[graphify/communities/Match Step (Neo4j Full-Text Search, No LLM)|Match Step (Neo4j Full-Text Search, No LLM)]]
- [[graphify/communities/Model Viewer (graph-viewermodel-viewer)|Model Viewer (graph-viewer/model-viewer/)]]
- [[graphify/communities/Phase 03 Validation Runs Summary|Phase 03 Validation Runs Summary]]
- [[graphify/communities/Phase 3 n8n Knowledge Workflows + LLM IngestQuery|Phase 3: n8n Knowledge Workflows + LLM Ingest/Query]]
- [[graphify/communities/Product Bridges Natural Language Rules to Graph-Based Val...|Product Bridges Natural Language Rules to Graph-Based Val...]]
- [[graphify/communities/SpeckleProjectConfigPayload|SpeckleProjectConfigPayload]]
- [[graphify/communities/Validation Endpoints (publishrunsview) (51)|Validation Endpoints (publish/runs/view)]]
- [[graphify/communities/Validation Endpoints (publishrunsview)|Validation Endpoints (publish/runs/view)]]
- [[graphify/communities/Validation Results Publish to Speckle as Overlay Versions|Validation Results Publish to Speckle as Overlay Versions]]
- [[graphify/communities/Worktree Branch Commits with Spurious Deletions|Worktree Branch Commits with Spurious Deletions]]
- [[graphify/communities/code 17 nodes|code: 17 nodes]]
- [[graphify/communities/code rule|code: rule]]
- [[graphify/communities/extractErrorMessage()|extractErrorMessage()]]
- [[graphify/communities/n8n Workflow Orchestrator (197)|n8n Workflow Orchestrator]]
- [[graphify/communities/n8n Workflow Orchestrator for LLM Rule Ingestion and Queries|n8n Workflow Orchestrator for LLM Rule Ingestion and Queries]]
- [[graphify/communities/v4.0 BOT Ontology Bridge|v4.0 BOT Ontology Bridge]]
<!-- graphify:connections:end -->
