"""pytest fixtures shared across dg-reasoner tests.

Registers the `integration` marker and a `neo4j_available()` helper so
integration tests skip cleanly when a live Neo4j instance isn't reachable
(no docker required for the always-on unit tier).
"""

from __future__ import annotations

import os

import pytest
from neo4j import GraphDatabase
from neo4j.exceptions import ServiceUnavailable

NEO4J_URI = os.getenv("NEO4J_URI", "bolt://neo4j:7687")
NEO4J_USER = os.getenv("NEO4J_USER", "neo4j")
NEO4J_PASSWORD = os.getenv("NEO4J_PASSWORD", "12345678")


def pytest_configure(config: pytest.Config) -> None:
    config.addinivalue_line(
        "markers", "integration: requires a live, reachable Neo4j instance"
    )


def neo4j_available() -> bool:
    """Best-effort reachability probe. Never raises."""
    try:
        driver = GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASSWORD))
        with driver.session() as session:
            session.run("RETURN 1", timeout=3).consume()
        driver.close()
        return True
    except (ServiceUnavailable, Exception):
        return False


@pytest.fixture(scope="session")
def neo4j_driver():
    """Session-scoped bolt driver for integration tests; skips if unreachable."""
    if not neo4j_available():
        pytest.skip("Neo4j is not reachable at %s" % NEO4J_URI)
    driver = GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASSWORD))
    yield driver
    driver.close()
