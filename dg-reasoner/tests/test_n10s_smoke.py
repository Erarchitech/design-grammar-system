"""Integration smoke test: n10s (neosemantics) is installed on the neo4j
service and its procedures respond.

n10s is install + smoke-verify ONLY (D-02) -- it is NOT on the production
reasoning path (the custom Cypher->RDFLib translator owns that, per D-01).
This test just proves the plugin loaded and graphconfig.init is callable;
it writes only a harmless `_GraphConfig` node to the shared dev database.

Skipped cleanly when Neo4j is unreachable (see conftest.neo4j_driver).
"""

from __future__ import annotations

import pytest


@pytest.mark.integration
def test_n10s_procedures_registered(neo4j_driver):
    with neo4j_driver.session() as session:
        record = session.run(
            "SHOW PROCEDURES YIELD name WHERE name STARTS WITH 'n10s' "
            "RETURN count(*) AS n"
        ).single()
        assert record["n"] > 0, "no n10s.* procedures registered on neo4j"


@pytest.mark.integration
def test_n10s_graphconfig_init_callable(neo4j_driver):
    with neo4j_driver.session() as session:
        # Prerequisite uniqueness constraint per neosemantics install docs.
        session.run(
            "CREATE CONSTRAINT n10s_unique_uri IF NOT EXISTS "
            "FOR (r:Resource) REQUIRE r.uri IS UNIQUE"
        ).consume()
        # Writes only a single `_GraphConfig` node -- harmless, off the
        # production reasoning path (D-01/D-02).
        session.run("CALL n10s.graphconfig.init()").consume()
