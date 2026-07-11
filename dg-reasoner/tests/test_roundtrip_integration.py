"""Live end-to-end round-trip integration test (Plan 821-04, success criteria 3/4).

This is the real proof the always-on unit tier (`test_routes.py`, HermiT
monkeypatched) cannot provide: a real `v8-ui-smoke` Neo4j project pushed
through the FULL pipeline -- Cypher export -> RDFLib -> hybrid TBox+overlay
union -> Owlready2 -> HermiT -- inside the dg-reasoner Docker image (Java
present, unlike the Windows dev host per Plan 821-03's documented finding).

`@pytest.mark.integration` (D-13/D-15): skipped cleanly via the
`neo4j_available()` conftest helper when Neo4j isn't reachable -- no docker
required for the always-on unit suite.

D-16 drift-immunity: asserts the two known-mistagged v8-ui-smoke atoms
(`R_DOOR_ORIENTATION_V_A1`/`_A2`, carrying `graph:'OntoGraph'` instead of the
schema-mandated `graph:'Metagraph'`, per 820-DECISION.md) still appear in the
label-scoped export -- turning Phase 820's data-quality finding into a
permanent regression guard for the label-scoped-export mandate
(`ontology_export.py`'s `ONTOGRAPH_QUERY`/`METAGRAPH_QUERY` scope by node
LABEL, never by the `graph` property).
"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest
from rdflib.namespace import RDF

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import ontology_export  # noqa: E402
import reasoning  # noqa: E402

PROJECT = "v8-ui-smoke"

pytestmark = pytest.mark.integration


@pytest.fixture(scope="module")
def project_session(neo4j_driver):
    """One bolt session shared across this module's assertions."""
    with neo4j_driver.session() as session:
        yield session


def test_run_consistency_completes_without_error(project_session):
    """Success criterion 4: the real hybrid round-trip completes without raising.

    Exercises the full Cypher export -> RDFLib -> hybrid union -> Owlready2 ->
    HermiT pipeline against live docker Neo4j (v8-ui-smoke, the richest
    project -- 16 Rule nodes per 820-DECISION.md). A well-formed D-10 contract
    dict with `consistent` set (True/False, never an unhandled exception) and
    a numeric `stripped_builtin_rules` proves the pipeline, not a toy fixture.
    """
    result = reasoning.run_consistency(PROJECT, session=project_session)

    assert result.get("error") != "timeout", (
        f"HermiT subprocess timed out against real {PROJECT} data: {result}"
    )
    assert result["consistent"] in (True, False)
    assert isinstance(result["unsatisfiable_classes"], list)
    assert isinstance(result["axiom_counts"], dict)
    # v8-ui-smoke is builtin-heavy (SWRL_BUILTIN violation-pattern rules) --
    # > 0 confirms strip_hermit_unsupported actually ran against real data,
    # not an empty/degenerate export.
    assert isinstance(result["stripped_builtin_rules"], int)
    assert result["stripped_builtin_rules"] > 0


def test_drift_immunity_mistagged_door_orientation_atoms_exported(project_session):
    """D-16 regression guard: the two known-mistagged atoms MUST be captured.

    `R_DOOR_ORIENTATION_V_A1`/`_A2` carry `graph:'OntoGraph'` instead of the
    schema-mandated `graph:'Metagraph'` (820-DECISION.md finding). The
    label-scoped export (`MATCH (n) WHERE n.project = $project AND n:Atom`,
    never `AND n.graph = 'Metagraph'`) must still capture them -- proving
    label-scoping succeeds where graph-property scoping would have silently
    dropped them (Pitfall 1).
    """
    graph = ontology_export.build_graph(project_session, PROJECT)

    for atom_id in ("R_DOOR_ORIENTATION_V_A1", "R_DOOR_ORIENTATION_V_A2"):
        atom_iri = ontology_export.mint(PROJECT, "atom", atom_id)
        # Must appear either as a mapped SWRL atom (ClassAtom/DataPropertyAtom/
        # ObjectPropertyAtom/BuiltinAtom) or as a captured-not-dropped
        # dgm:SkippedAtom -- never absent entirely.
        rdf_types = list(graph.objects(subject=atom_iri, predicate=RDF.type))
        assert rdf_types, (
            f"{atom_id} (minted IRI {atom_iri}) not found in the label-scoped "
            "export -- drift-immunity regression: the mistagged atom was "
            "silently dropped."
        )
