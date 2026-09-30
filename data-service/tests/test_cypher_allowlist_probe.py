"""Differential check of `cypher_allowlist` against a REAL Neo4j engine
(Phase 1205, review iteration 4).

Opt-in: skipped unless `DG_ALLOWLIST_PROBE_BOLT` names a bolt URL, for example

    docker run -d --rm --name dg-allowlist-probe -e NEO4J_AUTH=none \
        -p 127.0.0.1:17687:7687 neo4j:5.26
    DG_ALLOWLIST_PROBE_BOLT=bolt://127.0.0.1:17687 \
        python -m pytest data-service/tests/test_cypher_allowlist_probe.py -q -s

The engine MUST be a disposable one. The fixture refuses the compose default
port (7687), any non-loopback host, and any database that already holds data,
so it cannot seed into (or read from) the live `neo4j` container by accident.

Two synthetic tenants, P1 and P2, are seeded. Every string value on a P2 node or
relationship carries the marker `P2MARK`. For every read query the allowlist
ACCEPTS, the query runs with `$project = 'P1'` and the whole result -- scalars,
maps, lists, nodes, relationships, paths -- must contain no marker. A control
proves the detection works: the reviewer's attack queries, run raw against the
engine, DO return the marker. Every write example (catalog shapes, template
block, reference corpus) is run through `EXPLAIN`, which plans without writing.
"""

from __future__ import annotations

import os
import sys
from urllib.parse import urlparse

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, os.path.dirname(__file__))

os.environ.setdefault("LLM_MASTER_SECRET", "test-master-secret")

import cypher_allowlist  # noqa: E402
import dg_context  # noqa: E402
import test_cypher_allowlist as corpus  # noqa: E402

BOLT = os.environ.get("DG_ALLOWLIST_PROBE_BOLT", "").strip()
MARK = "P2MARK"

pytestmark = [
    pytest.mark.neo4j_probe,
    pytest.mark.skipif(not BOLT, reason="set DG_ALLOWLIST_PROBE_BOLT to a disposable Neo4j"),
]


def _refuse_live_engine(url: str) -> None:
    parsed = urlparse(url)
    assert parsed.hostname in ("127.0.0.1", "localhost", "::1"), f"not a loopback engine: {url}"
    assert parsed.port not in (None, 7687), "refusing the compose default bolt port"


SEED = [
    # P1 tenant
    "CREATE (:Rule {Rule_Id: 'R_P1_A', project: 'P1', graph: 'Metagraph', kind: 'violation', "
    "SWRL: 'p1 swrl', name: 'p1-a', secret: 'p1-secret', starts: 'p1', ends: 'p1'})",
    "CREATE (:Rule {Rule_Id: 'R_P1_B', project: 'P1', graph: 'Metagraph', kind: 'compliance', "
    "SWRL: 'p1 swrl 2', name: 'p1-b', secret: 'p1-secret-b'})",
    "CREATE (:Atom {Atom_Id: 'R_P1_A_A1', project: 'P1', graph: 'Metagraph', type: 'ClassAtom', "
    "iri: 'ex:P1Thing', SWRL_label: 'P1Thing', secret: 'p1-atom'})",
    "CREATE (:Class {iri: 'ex:P1Thing', project: 'P1', graph: 'OntoGraph', label: 'P1Thing'})",
    "CREATE (:ValidationRun {Run_Id: 'RUN_P1', project: 'P1', statePayloadJson: '{}'})",
    # P2 tenant (every string carries the marker)
    f"CREATE (:Rule {{Rule_Id: 'R_{MARK}_A', project: 'P2', graph: 'Metagraph', kind: 'violation', "
    f"SWRL: '{MARK} swrl', name: '{MARK}-a', secret: '{MARK}-SECRET-FOREIGN', "
    f"starts: '{MARK}', ends: '{MARK}'}})",
    f"CREATE (:Atom {{Atom_Id: 'R_{MARK}_A_A1', project: 'P2', graph: 'Metagraph', type: 'ClassAtom', "
    f"iri: 'ex:{MARK}Thing', SWRL_label: '{MARK}Thing', secret: '{MARK}-atom-secret'}})",
    f"CREATE (:Class {{iri: 'ex:{MARK}Thing', project: 'P2', graph: 'OntoGraph', label: '{MARK}Thing'}})",
    f"CREATE (:ValidationRun {{Run_Id: 'RUN_{MARK}', project: 'P2', statePayloadJson: '{MARK}'}})",
    # relationships, including cross-tenant edges the scope rule must never follow
    "MATCH (r:Rule {Rule_Id: 'R_P1_A'}), (a:Atom {Atom_Id: 'R_P1_A_A1'}) "
    "CREATE (r)-[:HAS_BODY {order: 1}]->(a)",
    "MATCH (a:Atom {Atom_Id: 'R_P1_A_A1'}), (c:Class {iri: 'ex:P1Thing'}) "
    "CREATE (a)-[:REFERS_TO]->(c)",
    "MATCH (r:Rule {Rule_Id: 'R_P1_A'}), (s:Rule {Rule_Id: 'R_P1_B'}) "
    "CREATE (r)-[:SUPERSEDED_BY {supersededAt: 'now'}]->(s)",
    f"MATCH (r:Rule {{Rule_Id: 'R_{MARK}_A'}}), (a:Atom {{Atom_Id: 'R_{MARK}_A_A1'}}) "
    f"CREATE (r)-[:HAS_BODY {{order: 1, note: '{MARK}'}}]->(a)",
    f"MATCH (r:Rule {{Rule_Id: 'R_P1_A'}}), (a:Atom {{Atom_Id: 'R_{MARK}_A_A1'}}) "
    f"CREATE (r)-[:HAS_BODY {{order: 2, note: '{MARK}-cross'}}]->(a)",
    f"MATCH (r:Rule {{Rule_Id: 'R_{MARK}_A'}}), (s:Rule {{Rule_Id: 'R_P1_B'}}) "
    f"CREATE (r)-[:SUPERSEDED_BY {{supersededAt: '{MARK}'}}]->(s)",
]


@pytest.fixture(scope="module")
def engine():
    from neo4j import GraphDatabase

    _refuse_live_engine(BOLT)
    driver = GraphDatabase.driver(BOLT, auth=None, notifications_min_severity="OFF")
    driver.verify_connectivity()
    with driver.session() as session:
        existing = session.run("MATCH (n) RETURN count(n) AS c").single()["c"]
        assert existing == 0, "refusing to seed a database that already holds data"
        for statement in SEED:
            session.run(statement).consume()
        total = session.run("MATCH (n) RETURN count(n) AS c").single()["c"]
        assert total == 9
    yield driver
    with driver.session() as session:
        session.run("MATCH (n) DETACH DELETE n").consume()
    driver.close()


def _contains_marker(value) -> bool:
    """Walk a driver value: scalars, lists, maps, nodes, relationships, paths."""
    from neo4j.graph import Node, Path, Relationship

    if value is None or isinstance(value, (bool, int, float)):
        return False
    if isinstance(value, str):
        return MARK in value
    if isinstance(value, (list, tuple, set)):
        return any(_contains_marker(v) for v in value)
    if isinstance(value, dict):
        return any(_contains_marker(k) or _contains_marker(v) for k, v in value.items())
    if isinstance(value, Node):
        return any(_contains_marker(v) for v in value.values()) or any(
            _contains_marker(label) for label in value.labels
        )
    if isinstance(value, Relationship):
        return _contains_marker(dict(value)) or _contains_marker(value.type)
    if isinstance(value, Path):
        return any(_contains_marker(n) for n in value.nodes) or any(
            _contains_marker(r) for r in value.relationships
        )
    return MARK in repr(value)


def _run_read(driver, cypher: str, params: dict) -> tuple[str, list]:
    """('ok', rows) | ('engine_error', message)."""
    from neo4j.exceptions import Neo4jError

    with driver.session() as session:
        try:
            result = session.run(cypher, params)
            return "ok", [record.values() for record in result]
        except Neo4jError as exc:
            return "engine_error", str(exc)[:200]


PARAMS = {"project": "P1", "limit": 5}

# Queries the reviewer reproduced (run raw as a control, and asserted rejected).
REVIEW_ATTACKS = [
    # CR-01
    "MATCH (a:Rule {project: $project}), (b:Rule {project: $project}) "
    "WHERE a.project = $project OR a.starts WITH a MATCH (b) RETURN b.secret",
    "MATCH (a:Rule {project: $project}), (b:Rule {project: $project}) "
    "WHERE a.project = $project OR a.ends WITH a MATCH (b) RETURN b.secret",
    # CR-02
    "MATCH (a:Rule {project: $project}) WHERE (a IS Rule)-->({secret: '" + MARK + "-atom-secret'}) "
    "RETURN 'ORACLE' AS r",
    "MATCH (a:Rule {project: $project}) WHERE (IS Rule)-->({secret: '" + MARK + "-atom-secret'}) "
    "RETURN 'GLOBAL-ORACLE' AS r",
    # pattern predicates with an unscoped far node
    "MATCH (a:Rule {project: $project}) WHERE (a)-[:HAS_BODY]->({secret: '" + MARK + "-atom-secret'}) "
    "RETURN 'ORACLE' AS r",
    "MATCH (a:Rule {project: $project}) RETURN [(a)-[:HAS_BODY]->(x) | x.secret] AS leak",
]


def _accepted_corpus() -> list[str]:
    queries = list(corpus.LEGIT_READ_QUERIES)
    queries += [
        "MATCH (r:Rule {project: $project}) OPTIONAL MATCH (r)-[:SUPERSEDED_BY]->(s:Rule {project: $project}) "
        "WHERE s IS NULL RETURN r.Rule_Id",
        "MATCH (r:Rule {project: $project})-[h:HAS_BODY]->(a:Atom {project: $project}) "
        "RETURN r, h, a LIMIT $limit",
        "MATCH (r:Rule {project: $project}) WHERE r.starts STARTS WITH 'p' RETURN r.Rule_Id AS id, r.ends AS e",
        "MATCH (r:Rule {project: $project}) RETURN r.Rule_Id, collect(r.secret) AS s, {k: r.name} AS m",
        "MATCH (r:Rule {project: $project}) RETURN r.Rule_Id ORDER BY r.Rule_Id SKIP 1 LIMIT 5",
        "MATCH (n {project: $project}) RETURN labels(n) AS l, count(*) AS c",
        "MATCH (a:Atom {project: $project})-[:REFERS_TO]->(c:Class {project: $project}) RETURN a, c",
        "MATCH (r:Rule {project: $project}) RETURN properties(r) AS p, keys(r) AS k",
    ]
    # accepted mutations of the legit set (most are nonsense to the engine; the
    # ones the allowlist accepts must still never leak)
    accepted = [q for q in corpus._mutations(corpus.LEGIT_READ_QUERIES, 6000) if not cypher_allowlist.check_read_allowlist(q)]
    return queries + sorted(set(accepted))


class TestAcceptedReadQueriesNeverReturnAnotherTenantsData:
    def test_seed_is_visible_to_a_raw_unscoped_read(self, engine):
        status, rows = _run_read(engine, "MATCH (n {project: 'P2'}) RETURN n", {})
        assert status == "ok" and rows, "seed missing"
        assert any(_contains_marker(row) for row in rows)

    @pytest.mark.parametrize("attack", REVIEW_ATTACKS)
    def test_control_the_review_attacks_leak_when_run_raw(self, engine, attack):
        status, rows = _run_read(engine, attack, PARAMS)
        assert status == "ok", (attack, rows)
        leaked = any(_contains_marker(row) for row in rows) or any(
            row and row[0] in ("ORACLE", "GLOBAL-ORACLE") for row in rows
        )
        assert leaked, f"control failed: the raw attack returned no foreign data: {attack}"

    @pytest.mark.parametrize("attack", REVIEW_ATTACKS)
    def test_the_allowlist_rejects_every_review_attack(self, attack):
        assert cypher_allowlist.check_read_allowlist(attack), attack

    def test_no_accepted_query_returns_a_foreign_marker(self, engine, capsys):
        queries = _accepted_corpus()
        executed = engine_errors = rows_seen = 0
        for cypher in queries:
            assert cypher_allowlist.check_read_allowlist(cypher) == [], cypher
            status, rows = _run_read(engine, cypher, PARAMS)
            if status == "engine_error":
                engine_errors += 1
                continue
            executed += 1
            rows_seen += len(rows)
            for row in rows:
                assert not _contains_marker(row), (cypher, row)
        with capsys.disabled():
            print(
                f"\nallowlist probe: {len(queries)} accepted read queries, "
                f"{executed} executed, {engine_errors} refused by the engine (syntax/parameter), "
                f"{rows_seen} rows inspected, 0 foreign markers"
            )
        assert executed >= 20, "too few accepted queries ran for the probe to mean anything"

    def test_accepted_queries_return_the_tenants_own_data(self, engine):
        status, rows = _run_read(
            engine, "MATCH (r:Rule {project: $project}) RETURN r.Rule_Id AS id ORDER BY id", PARAMS
        )
        assert status == "ok"
        assert [row[0] for row in rows] == ["R_P1_A", "R_P1_B"]


def _write_examples() -> list[tuple[str, str]]:
    examples: list[tuple[str, str]] = []
    for shape in dg_context.load_cypher_catalog()["shapes"]:
        examples.append((f"catalog:{shape['id']}:worked_example", shape["worked_example"]))
        examples.append((f"catalog:{shape['id']}:cypher_template", shape["cypher_template"]))
    examples.append(("template_txt_block", corpus._instantiate(corpus._template_block())))
    examples.append(("tests:HEIGHT_RULE", corpus.HEIGHT_RULE))
    return examples


class TestWriteExamplesPlanOnTheEngine:
    def test_every_write_example_passes_the_allowlist_and_explains(self, engine, capsys):
        from neo4j.exceptions import Neo4jError

        planned = 0
        examples = _write_examples()
        for name, cypher in examples:
            assert cypher_allowlist.check_write_allowlist(cypher) == [], name
            text = cypher.rstrip().rstrip(";")  # n8n removes the one trailing ';'
            with engine.session() as session:
                try:
                    session.run("EXPLAIN " + text, {"project": "P1"}).consume()
                except Neo4jError as exc:  # pragma: no cover - reported, then fails
                    pytest.fail(f"EXPLAIN failed for {name}: {exc}")
            planned += 1
        with capsys.disabled():
            print(f"\nallowlist probe: {planned} write examples accepted by the allowlist and EXPLAINed")
        assert planned == len(examples) >= 14

    def test_explain_wrote_nothing(self, engine):
        with engine.session() as session:
            assert session.run("MATCH (n) RETURN count(n) AS c").single()["c"] == 9
