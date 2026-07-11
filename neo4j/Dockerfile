# Pinned neo4j 5.26.x LTS + a deterministic, version-matched neosemantics (n10s) jar.
# NEO4J_PLUGINS='["n10s"]' auto-download is flaky on some Neo4j 5.x releases
# (neo4j/docker-neo4j#489), so the jar is fetched at build time from the
# neosemantics GitHub release matching this exact neo4j tag.
FROM neo4j:5.26

RUN wget -q \
    https://github.com/neo4j-labs/neosemantics/releases/download/5.26.0/neosemantics-5.26.0.jar \
    -O /var/lib/neo4j/plugins/neosemantics-5.26.0.jar
