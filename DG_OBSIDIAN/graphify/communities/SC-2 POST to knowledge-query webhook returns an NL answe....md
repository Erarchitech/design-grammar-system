---
community_id: 42
nodes_count: 16
tags: [graphify/community, sc-2-post-to-knowledge-query-webhook-returns-an-nl]
graphify_snapshot: graphify-2026-06-22
---

# SC-2: POST to knowledge-query webhook returns an NL answe...

> Автоматически сгенерировано graphify. **16 nodes**, типы: code=8, rationale=8

## Ключевые узлы

- **Poll /execution-result/latest/{workflow} until status == 'completed' or timeout.** `L27` — test/test_phase03_knowledge_llm.py
- **SC-3: After SC-1 ingest, GET /knowledge/sessions/{project} contains an insert se** `L120` — test/test_phase03_knowledge_llm.py
- **SC-5: GET /knowledge/sessions/{project} returns correctly shaped session records** `L159` — test/test_phase03_knowledge_llm.py
- **Phase 03 Verification: n8n Knowledge Workflows + LLM Ingest and Query Tests all** `L1` — test/test_phase03_knowledge_llm.py
- **SC-4: POST to knowledge-ingest webhook returns HTTP 200 with status='accepted'.** `L138` — test/test_phase03_knowledge_llm.py
- **SC-2: POST to knowledge-query webhook returns an NL answer with Cypher.      S** `L86` — test/test_phase03_knowledge_llm.py
- **SC-1: POST to knowledge-ingest webhook creates a KnowledgeNote in Neo4j.** `L46` — test/test_phase03_knowledge_llm.py
- **Remove all test nodes from Neo4j for project 'test-phase03'.** `L179` — test/test_phase03_knowledge_llm.py
- **test_phase03_knowledge_llm.py** `L1` — test/test_phase03_knowledge_llm.py
- **test_sc5_sessions_endpoint()** `L158` — test/test_phase03_knowledge_llm.py
- **test_sc3_session_insert()** `L119` — test/test_phase03_knowledge_llm.py
- **_poll_execution_result()** `L26` — test/test_phase03_knowledge_llm.py
- ... и ещё 4 узлов

## Связанные curated notes

- [[n8n runs two async webhook workflows for ingest and query]]

## Смотрите также

- [[../Graph Index|Graph Index]] — все сообщества

---

*Сгенерировано: export_graphify_conceptual.py · Источник: graphify community detection*
