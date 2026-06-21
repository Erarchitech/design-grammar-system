---
community_id: 49
nodes_count: 14
tags: [graphify/community, remove-all-test-notes-from-neo4j]
graphify_snapshot: graphify-2026-06-22
---

# Remove all test notes from Neo4j.

> Автоматически сгенерировано graphify. **14 nodes**, типы: code=7, rationale=7

## Ключевые узлы

- **Phase 02 Verification: data-service CRUD + Folder Ingest Tests all 5 success cri** `L1` — test/test_knowledge_crud.py
- **SC-1: POST /knowledge/ingest/folder creates KnowledgeNote nodes from .md files.** `L17` — test/test_knowledge_crud.py
- **SC-5: All knowledge endpoints reachable through Nginx /data-service/ proxy.** `L101` — test/test_knowledge_crud.py
- **SC-3: GET /knowledge/notes/{project} returns list of note titles and IDs.** `L42` — test/test_knowledge_crud.py
- **SC-2: A path outside the allowed mount root is rejected with HTTP 403.** `L32` — test/test_knowledge_crud.py
- **SC-4: GET, PUT, DELETE on /knowledge/note/{id} work correctly.** `L56` — test/test_knowledge_crud.py
- **test_sc2_path_traversal_rejected()** `L31` — test/test_knowledge_crud.py
- **Remove all test notes from Neo4j.** `L110` — test/test_knowledge_crud.py
- **test_sc4_crud_operations()** `L55` — test/test_knowledge_crud.py
- **test_sc1_folder_ingest()** `L16` — test/test_knowledge_crud.py
- **test_knowledge_crud.py** `L1` — test/test_knowledge_crud.py
- **test_sc5_nginx_proxy()** `L100` — test/test_knowledge_crud.py
- ... и ещё 2 узлов

## Связанные curated notes

- [[Data-service is a FastAPI MCP bridge to Neo4j and Speckle]]
- [[Deployment uses Docker Compose with nginx reverse proxy]]

## Смотрите также

- [[../Graph Index|Graph Index]] — все сообщества

---

*Сгенерировано: export_graphify_conceptual.py · Источник: graphify community detection*
