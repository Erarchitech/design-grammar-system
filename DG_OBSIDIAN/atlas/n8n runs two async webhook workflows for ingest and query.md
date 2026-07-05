---
tags: [atlas, n8n, workflow, llm]
date: 2026-04-05
graphify_communities: ["Build Full-Text Cypher", "Community 12", "Community 177", "Community 214", "Knowledge Webhook Field Name Mismatch Causes Stale LLM Ou...", "Phase 3: n8n Knowledge Workflows + LLM Ingest/Query", "Prepare Graph Payload", "Return an HTTPException with a structured JSON detail bod...", "SC-2: POST to knowledge-query webhook returns an NL answe...", "Validation Endpoints (publish/runs/view)", "knowledge-ingest.json", "knowledge-update.json"]
---

# n8n Runs Two Async Webhook Workflows for Ingest and Query

Both workflows are defined in `n8n/workflows/` and receive HTTP webhooks from the SPA UI. They use Ollama for LLM inference and report progress via data-service execution tracking.

## Workflow 1: Rules Ingest (`rules-to-metagraph.json`)

**Webhook**: `POST /webhook/dg/rules-ingest`  
**Purpose**: Convert NL design rules → SWRL → Cypher → Neo4j

### Pipeline (13 nodes)

1. **Ingest Rules** (Webhook) — receive `{rules_text, project}`
2. **Set Input Defaults** — extract/default all parameters
3. **Fetch Existing Entities** — query Neo4j for existing Classes, Properties, Rules
4. **Build LLM Prompt** — construct 4000+ char prompt with schema, few-shot, existing entities
5. **Ollama Generate** — call `POST /api/generate` with llama3.1
6. **Parse LLM Output** — validate Cypher (bracket nesting, dedup, consolidate)
7. **Prepare Graph Payload** — assemble cleanup (edits) + main Cypher
8. **Execute LLM Cypher** — run against Neo4j HTTP tx/commit
9. **Annotate Graph Props** — tag `graph`/`project` on orphaned nodes
10. **Build Response** — format success message with MERGE counts
11. **Store Result** — persist to data-service `/execution-result`
12. **Respond Ack** — immediate 200 to UI

### Edit Mode

Detects keywords (`edit`, `update`, `change`, `modify`), extracts Rule_Id, generates MATCH-DELETE cleanup for old atoms before re-creating.

## Workflow 2: Graph Query (`graph-query-mcp.json`)

**Webhook**: `POST /webhook/dg/graph-query`  
**Purpose**: NL question → Cypher → Neo4j → NL answer

### Pipeline (15 nodes)

1. **Ingest Prompt** — receive `{prompt, project}`
2. **Fetch Graph Context (MCP)** — call `/mcp` `neo4j_schema` tool for live schema
3. **Build Cypher Prompt** — construct prompt with live schema + v3 data model + guidance
4. **Generate Cypher** — Ollama returns `{"cypher":"..."}`
5. **Parse Cypher** — validate against schema; smart overrides for common patterns
6. **Run Cypher (MCP)** — call `/mcp` `neo4j_query` tool (read-only)
7. **Build Answer Prompt** — results + original question
8. **Generate Answer** — Ollama summarizes
9. **Parse Answer** — extract text, fallback to numeric patterns
10. **Store Result** — persist execution

### Smart Overrides

- "list rules" → forces standard Rule listing query
- Numeric keywords (height, maximum, etc.) → keyword-matching on `Rule.text`

## Related

- [[Ollama runs local LLM inference for Cypher generation]]
- [[LLM prompts embed schema constraints instead of fine-tuning]]
- [[Async polling pattern for n8n workflow execution tracking]]
- [[LLM Cypher output needs bracket nesting validation]]

<!-- graphify:connections:start -->
## Graph connections

- [[graphify/communities/Build Full-Text Cypher|Build Full-Text Cypher]]
- [[graphify/communities/Community 12|Community 12]]
- [[graphify/communities/Community 177|Community 177]]
- [[graphify/communities/Community 214|Community 214]]
- [[graphify/communities/Knowledge Webhook Field Name Mismatch Causes Stale LLM Ou...|Knowledge Webhook Field Name Mismatch Causes Stale LLM Ou...]]
- [[graphify/communities/Phase 3 n8n Knowledge Workflows + LLM IngestQuery|Phase 3: n8n Knowledge Workflows + LLM Ingest/Query]]
- [[graphify/communities/Prepare Graph Payload|Prepare Graph Payload]]
- [[graphify/communities/Return an HTTPException with a structured JSON detail bod...|Return an HTTPException with a structured JSON detail bod...]]
- [[graphify/communities/SC-2 POST to knowledge-query webhook returns an NL answe...|SC-2: POST to knowledge-query webhook returns an NL answe...]]
- [[graphify/communities/Validation Endpoints (publishrunsview) (259)|Validation Endpoints (publish/runs/view)]]
- [[graphify/communities/knowledge-ingest.json|knowledge-ingest.json]]
- [[graphify/communities/knowledge-update.json|knowledge-update.json]]
<!-- graphify:connections:end -->
