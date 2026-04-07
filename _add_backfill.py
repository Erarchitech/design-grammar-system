"""Add backfill for existing knowledge nodes missing INSTANCE_OF links."""
import pathlib

p = pathlib.Path("data-service/app.py")
c = p.read_text(encoding="utf-8")

old = (
    "        session.run(\n"
    "            \"MERGE (c:KnowledgeClass {name: 'KnowledgeSession', graph: 'KnowledgeGraph'}) \"\n"
    "            \"SET c.label = 'KnowledgeSession'\"\n"
    "        ).consume()"
)

new = (
    "        session.run(\n"
    "            \"MERGE (c:KnowledgeClass {name: 'KnowledgeSession', graph: 'KnowledgeGraph'}) \"\n"
    "            \"SET c.label = 'KnowledgeSession'\"\n"
    "        ).consume()\n"
    "        # Backfill: connect any existing nodes that lack INSTANCE_OF links\n"
    "        session.run(\n"
    "            \"MATCH (n:KnowledgeNote) WHERE NOT (n)-[:INSTANCE_OF]->(:KnowledgeClass) \"\n"
    "            \"WITH n \"\n"
    "            \"MERGE (c:KnowledgeClass {name: 'KnowledgeNote', graph: 'KnowledgeGraph'}) \"\n"
    "            \"MERGE (n)-[:INSTANCE_OF]->(c)\"\n"
    "        ).consume()\n"
    "        session.run(\n"
    "            \"MATCH (s:KnowledgeSession) WHERE NOT (s)-[:INSTANCE_OF]->(:KnowledgeClass) \"\n"
    "            \"WITH s \"\n"
    "            \"MERGE (c:KnowledgeClass {name: 'KnowledgeSession', graph: 'KnowledgeGraph'}) \"\n"
    "            \"MERGE (s)-[:INSTANCE_OF]->(c)\"\n"
    "        ).consume()"
)

assert old in c, "Could not find target block"
c = c.replace(old, new)
p.write_text(c, encoding="utf-8")
print("Backfill added to ensure_knowledge_indexes")
