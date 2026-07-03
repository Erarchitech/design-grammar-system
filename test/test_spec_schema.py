"""
Phase 1 verification: SpecGraph schema foundation.
Run: python test/test_spec_schema.py
Requires: neo4j Python driver, running Neo4j instance.
"""
import os
import sys
import uuid
from neo4j import GraphDatabase

NEO4J_URI = os.getenv("NEO4J_URI", "bolt://localhost:7687")
NEO4J_USER = os.getenv("NEO4J_USER", "neo4j")
NEO4J_PASSWORD = os.getenv("NEO4J_PASSWORD", "12345678")

TEST_PROJECT = f"_test_schema_{uuid.uuid4().hex[:8]}"
SPEC_GRAPH = "SpecGraph"


def main():
    driver = GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASSWORD))
    passed = 0
    failed = 0

    try:
        # --- Ensure full-text index exists ---
        with driver.session() as s:
            s.run(
                "CREATE FULLTEXT INDEX spec_note_search IF NOT EXISTS "
                "FOR (n:SpecNote) ON EACH [n.title, n.content]"
            ).consume()

        # SC-1: SpecNote MERGE with all required properties
        note_id = f"note-{uuid.uuid4().hex[:8]}"
        with driver.session() as s:
            s.run(
                "MERGE (n:SpecNote {noteId: $noteId, project: $project, graph: $graph}) "
                "SET n.title = $title, n.content = $content, n.source = $source, "
                "    n.tags = $tags, n.createdAt = datetime(), n.updatedAt = datetime()",
                {
                    "noteId": note_id,
                    "project": TEST_PROJECT,
                    "graph": SPEC_GRAPH,
                    "title": "Test Note",
                    "content": "This is test content for schema verification",
                    "source": "test-script",
                    "tags": ["test", "schema"],
                },
            ).consume()
            record = s.run(
                "MATCH (n:SpecNote {noteId: $noteId, project: $project, graph: $graph}) "
                "RETURN n.title AS title, n.content AS content, n.source AS source",
                {"noteId": note_id, "project": TEST_PROJECT, "graph": SPEC_GRAPH},
            ).single()
        assert record is not None, "SpecNote not found after MERGE"
        assert record["title"] == "Test Note"
        assert record["content"] == "This is test content for schema verification"
        assert record["source"] == "test-script"
        print("  PASS  SC-1: SpecNote MERGE with all properties")
        passed += 1

        # SC-2: SpecTag + TAGGED_WITH relationship
        with driver.session() as s:
            s.run(
                "MERGE (t:SpecTag {name: $name, project: $project, graph: $graph})",
                {"name": "test", "project": TEST_PROJECT, "graph": SPEC_GRAPH},
            ).consume()
            s.run(
                "MATCH (n:SpecNote {noteId: $noteId, project: $project}) "
                "MATCH (t:SpecTag {name: $tagName, project: $project}) "
                "MERGE (n)-[:TAGGED_WITH]->(t)",
                {"noteId": note_id, "tagName": "test", "project": TEST_PROJECT},
            ).consume()
            record = s.run(
                "MATCH (n:SpecNote {noteId: $noteId, project: $project})"
                "-[:TAGGED_WITH]->(t:SpecTag) RETURN t.name AS name",
                {"noteId": note_id, "project": TEST_PROJECT},
            ).single()
        assert record is not None, "TAGGED_WITH relationship not found"
        assert record["name"] == "test"
        print("  PASS  SC-2: SpecTag + TAGGED_WITH relationship")
        passed += 1

        # SC-3: SpecSession with required properties
        session_id = f"sess-{uuid.uuid4().hex[:8]}"
        with driver.session() as s:
            s.run(
                "MERGE (sess:SpecSession {sessionId: $sessionId, project: $project, graph: $graph}) "
                "SET sess.mode = $mode, sess.prompt = $prompt, sess.result = $result, "
                "    sess.createdAt = datetime()",
                {
                    "sessionId": session_id,
                    "project": TEST_PROJECT,
                    "graph": SPEC_GRAPH,
                    "mode": "insert",
                    "prompt": "test prompt",
                    "result": "test result",
                },
            ).consume()
            record = s.run(
                "MATCH (sess:SpecSession {sessionId: $sessionId, project: $project, graph: $graph}) "
                "RETURN sess.mode AS mode, sess.prompt AS prompt, sess.result AS result",
                {"sessionId": session_id, "project": TEST_PROJECT, "graph": SPEC_GRAPH},
            ).single()
        assert record is not None, "SpecSession not found after MERGE"
        assert record["mode"] == "insert"
        assert record["prompt"] == "test prompt"
        assert record["result"] == "test result"
        print("  PASS  SC-3: SpecSession with mode, prompt, result, createdAt")
        passed += 1

        # SC-4: Full-text search returns scored results filtered by project
        # Allow index to catch up (index is eventually consistent)
        import time
        time.sleep(2)
        with driver.session() as s:
            records = s.run(
                "CALL db.index.fulltext.queryNodes('spec_note_search', $query) "
                "YIELD node, score "
                "WHERE node.project = $project "
                "RETURN node.noteId AS noteId, node.title AS title, score",
                {"query": "schema verification", "project": TEST_PROJECT},
            ).data()
        assert len(records) > 0, "Full-text search returned no results"
        assert records[0]["noteId"] == note_id
        assert records[0]["score"] > 0
        print("  PASS  SC-4: Full-text search with project filter returns scored results")
        passed += 1

        # SC-5: Graph isolation — no cross-contamination
        with driver.session() as s:
            cross = s.run(
                "MATCH (n {graph: $graph}) "
                "WHERE n:Rule OR n:Atom OR n:Var OR n:Literal OR n:Builtin "
                "   OR n:Class OR n:DatatypeProperty OR n:ObjectProperty "
                "RETURN count(n) AS cnt",
                {"graph": SPEC_GRAPH},
            ).single()
        assert cross["cnt"] == 0, f"Found {cross['cnt']} SWRL nodes with graph:'SpecGraph'"
        print("  PASS  SC-5: No Metagraph/OntoGraph/ValidGraph nodes in SpecGraph")
        passed += 1

    except Exception as e:
        print(f"  FAIL  {e}")
        failed += 1
    finally:
        # Cleanup test data
        with driver.session() as s:
            s.run(
                "MATCH (n {project: $project, graph: $graph}) DETACH DELETE n",
                {"project": TEST_PROJECT, "graph": SPEC_GRAPH},
            ).consume()
        driver.close()

    print(f"\nResults: {passed} passed, {failed} failed out of 5")
    sys.exit(0 if failed == 0 else 1)


if __name__ == "__main__":
    main()
