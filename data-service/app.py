from fastapi import FastAPI
from neo4j import GraphDatabase
import os

app = FastAPI()

# Подключение к Neo4j
NEO4J_URI = os.getenv("NEO4J_URI", "bolt://neo4j:7687")
NEO4J_USER = os.getenv("NEO4J_USER", "neo4j")
NEO4J_PASSWORD = os.getenv("NEO4J_PASSWORD", "12345678")

driver = GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASSWORD))

@app.get("/")
def read_root():
    return {"status": "Data Service is running"}

@app.post("/create_node/")
def create_node(label: str, name: str):
    with driver.session() as session:
        session.run(f"CREATE (n:{label} {{name: $name}})", name=name)
    return {"status": f"Node {name} with label {label} created"}