"""Automated test for the CQ3 ATTRIBUTE_OF bidirectional bridge fixture
(Phase 1203 plan 06, D-14, requirement ALGN12-14).

Loads `fixtures/golden/cq3-attribute-of/expected-cq3.json` and asserts that
querying an in-memory graph seeded with the exact same shape as
`fixtures/golden/cq3-attribute-of/seed-cq3.cypher` returns:

  - the forward direction (Rule -HAS_BODY-> DataPropertyAtom -ATTRIBUTE_OF->
    Parameter) as exactly one row matching the committed expectation;
  - the reverse direction (Parameter <-ATTRIBUTE_OF- Atom <-HAS_BODY- Rule) as
    exactly one row matching the committed expectation;
  - both directions against a DIFFERENT project as zero rows (cross-project
    isolation).

This test does NOT invoke `computgraph_publish.publish_structure` or
`_publish_attribute_of` -- it seeds the graph directly, mirroring
`seed-cq3.cypher`'s graph-level approach (see this fixture's own README.md,
"Seeding method" section, for why). Derivation from `inputBindings` through
the real publish path is covered separately by
`data-service/tests/test_computgraph_publish.py`'s
`test_attribute_of_forward_query_returns_governing_parameter_name` and
`test_attribute_of_reverse_query_returns_governing_rule_and_atom` (among
others in that file's "ALGN12-14" sections). Neither test file substitutes
for the other; together they evidence derivation (there) plus queryability of
the resulting shape (here).

Follows the FakeGraph/FixtureSession mocking style established in
`data-service/tests/test_computgraph_publish.py` (duck-typed in-memory store
keyed by (label, key, project), dispatched by simple query predicates
rather than the full op= Cypher-tag protocol, since this test's graph is
purpose-built for exactly one seed shape rather than the full publish
surface).
"""

from __future__ import annotations

import json
import os
from pathlib import Path

FIXTURE_DIR = Path(__file__).resolve().parents[2] / "fixtures" / "golden" / "cq3-attribute-of"
EXPECTED_PATH = FIXTURE_DIR / "expected-cq3.json"


def _load_expected() -> dict:
    with open(EXPECTED_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


class Cq3Graph:
    """Minimal in-memory graph mirroring seed-cq3.cypher's exact shape:
    one Rule, three Atoms (A1 ClassAtom, A2 DataPropertyAtom, H1 head
    DataPropertyAtom), HAS_BODY/HAS_HEAD edges, one Parameter, and one
    ATTRIBUTE_OF edge from A2 to the Parameter -- all scoped to a single
    project. A second project is never seeded, so any query against it
    is expected to return zero rows (cross-project isolation).
    """

    def __init__(self, seed: dict, project: str):
        self.project = project
        self.rule_id = seed["ruleId"]
        self.atom_id = seed["atomId"]
        self.atom_type = seed["atomType"]
        self.atom_iri = seed["atomIri"]
        self.param_cg_id = seed["parameterCgId"]
        self.param_definition_id = seed["parameterDefinitionId"]
        self.param_name = seed["parameterName"]
        self.param_kind = seed["parameterKind"]

        # HAS_BODY: rule -> [A1 (ClassAtom), A2 (DataPropertyAtom)]
        self.has_body = [
            (self.rule_id, f"{self.rule_id}_A1", "ClassAtom"),
            (self.rule_id, self.atom_id, self.atom_type),
        ]
        # HAS_HEAD: rule -> H1, also type DataPropertyAtom (disambiguation case)
        self.has_head = [(self.rule_id, f"{self.rule_id}_H1", "DataPropertyAtom")]

        # ATTRIBUTE_OF: only the body A2 atom carries this edge.
        self.attribute_of = [(self.atom_id, self.param_cg_id)]

    def forward_query(self, rule_id: str, project: str) -> list[dict]:
        """MATCH (r:Rule {Rule_Id: $ruleId, project: $project})
        MATCH (r)-[:HAS_BODY]->(a:Atom {type: 'DataPropertyAtom'})
        MATCH (a)-[:ATTRIBUTE_OF]->(p:Parameter)
        RETURN p.parameterName, p.paramKind, p.cgId
        """
        if project != self.project or rule_id != self.rule_id:
            return []
        rows: list[dict] = []
        for (r, atom, atom_type) in self.has_body:
            if r != rule_id or atom_type != "DataPropertyAtom":
                continue
            for (from_atom, to_param) in self.attribute_of:
                if from_atom != atom:
                    continue
                if to_param == self.param_cg_id:
                    rows.append(
                        {
                            "parameterName": self.param_name,
                            "parameterKind": self.param_kind,
                            "parameterCgId": self.param_cg_id,
                        }
                    )
        return rows

    def reverse_query(self, param_cg_id: str, definition_id: str, project: str) -> list[dict]:
        """MATCH (p:Parameter {cgId: $parameterCgId, definitionId: $definitionId, project: $project})
        MATCH (a:Atom)-[:ATTRIBUTE_OF]->(p)
        MATCH (r:Rule)-[:HAS_BODY]->(a)
        RETURN r.Rule_Id, a.Atom_Id, a.type
        """
        if (
            project != self.project
            or param_cg_id != self.param_cg_id
            or definition_id != self.param_definition_id
        ):
            return []
        rows: list[dict] = []
        for (from_atom, to_param) in self.attribute_of:
            if to_param != param_cg_id:
                continue
            for (r, atom, atom_type) in self.has_body:
                if atom != from_atom:
                    continue
                rows.append(
                    {
                        "ruleId": r,
                        "atomId": atom,
                        "atomType": atom_type,
                    }
                )
        return rows


def test_expected_cq3_json_traces_paper_c_032():
    expected = _load_expected()
    assert expected["traceability"]["paperClaimId"] == "PAPER-C-032"
    assert expected["seed"]["ruleId"] == "R_BUILDING_MIN_DISTANCE_12_V"
    assert expected["seed"]["parameterName"] == "SepDist"
    assert expected["seed"]["parameterKind"] == "Variable"
    assert expected["seed"]["atomType"] == "DataPropertyAtom"


def test_cq3_forward_query_returns_exactly_one_row_matching_expected():
    expected = _load_expected()
    graph = Cq3Graph(expected["seed"], project=expected["project"])

    rows = graph.forward_query(
        rule_id=expected["forwardQuery"]["parameters"]["ruleId"],
        project=expected["forwardQuery"]["parameters"]["project"],
    )

    assert len(rows) == expected["forwardQuery"]["expectedRowCount"] == 1
    assert rows == expected["forwardQuery"]["expectedRows"]


def test_cq3_reverse_query_returns_exactly_one_row_matching_expected():
    expected = _load_expected()
    graph = Cq3Graph(expected["seed"], project=expected["project"])

    rows = graph.reverse_query(
        param_cg_id=expected["reverseQuery"]["parameters"]["parameterCgId"],
        definition_id=expected["reverseQuery"]["parameters"]["definitionId"],
        project=expected["reverseQuery"]["parameters"]["project"],
    )

    assert len(rows) == expected["reverseQuery"]["expectedRowCount"] == 1
    assert rows == expected["reverseQuery"]["expectedRows"]


def test_cq3_forward_query_cross_project_isolation_returns_zero_rows():
    expected = _load_expected()
    graph = Cq3Graph(expected["seed"], project=expected["project"])
    other_project = expected["crossProjectIsolation"]["otherProject"]

    rows = graph.forward_query(
        rule_id=expected["forwardQuery"]["parameters"]["ruleId"],
        project=other_project,
    )

    assert len(rows) == expected["crossProjectIsolation"]["expectedRowCountForward"] == 0


def test_cq3_reverse_query_cross_project_isolation_returns_zero_rows():
    expected = _load_expected()
    graph = Cq3Graph(expected["seed"], project=expected["project"])
    other_project = expected["crossProjectIsolation"]["otherProject"]

    rows = graph.reverse_query(
        param_cg_id=expected["reverseQuery"]["parameters"]["parameterCgId"],
        definition_id=expected["reverseQuery"]["parameters"]["definitionId"],
        project=other_project,
    )

    assert len(rows) == expected["crossProjectIsolation"]["expectedRowCountReverse"] == 0


def test_cq3_readme_states_no_solver_equivalence_claim():
    """Guards T-1203-06-04: the README must never overstate this fixture's
    scope beyond a populated, queryable bridge."""
    readme_path = FIXTURE_DIR / "README.md"
    text = readme_path.read_text(encoding="utf-8")
    assert "solver equivalence" in text.lower()
    assert "does not claim" in text.lower() or "does **not** claim" in text.lower()


def test_cq3_readme_documents_graph_level_seeding_and_names_derivation_test():
    """Guards T-1203-06-05: since seed-cq3.cypher creates ATTRIBUTE_OF directly
    (graph-level) rather than via the publish path, the README must say so and
    name the plan 04 test file/suite covering derivation."""
    readme_path = FIXTURE_DIR / "README.md"
    text = readme_path.read_text(encoding="utf-8")
    assert "test_computgraph_publish.py" in text
    assert "graph-level" in text.lower()


def test_frozen_fixture_json_byte_unchanged():
    """Guards the plan's hard prohibition: fixtures/golden/fixture.json must
    never be edited by this plan. This is a repo-relative existence + sanity
    check; the authoritative check is `git diff --exit-code --quiet
    fixtures/golden/fixture.json` run by the plan's <verify> block."""
    frozen_path = FIXTURE_DIR.parent / "fixture.json"
    assert frozen_path.exists()


def test_cq3_fixture_files_present():
    assert (FIXTURE_DIR / "README.md").exists()
    assert (FIXTURE_DIR / "seed-cq3.cypher").exists()
    assert (FIXTURE_DIR / "expected-cq3.json").exists()


def test_cq3_project_namespace_not_reused_elsewhere_in_fixtures_golden():
    """Guards the key_link: the fixture's project namespace string must appear
    in no other fixture's data files under fixtures/golden/ outside this
    directory. MANIFEST.md itself is exempt -- it is expected to reference
    every sibling fixture's project namespace once, as a registration entry
    (the same way it already names DG-1200-GOLDEN and DG-1202-REPLAY for the
    other two sibling fixtures); that is documentation, not a data collision.
    """
    expected = _load_expected()
    project = expected["project"]
    golden_root = FIXTURE_DIR.parent
    exempt_files = {golden_root / "MANIFEST.md"}

    offending: list[str] = []
    for root, _dirs, files in os.walk(golden_root):
        root_path = Path(root)
        if FIXTURE_DIR == root_path or FIXTURE_DIR in root_path.parents:
            continue
        for name in files:
            file_path = root_path / name
            if file_path in exempt_files:
                continue
            try:
                content = file_path.read_text(encoding="utf-8")
            except (UnicodeDecodeError, OSError):
                continue
            if project in content:
                offending.append(str(file_path))

    assert offending == []
