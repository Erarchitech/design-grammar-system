"""Asserts ALGN12-03's required content of fixtures/golden/fixture.json (Phase 1200
Plan 03) -- the golden fixture's shape is asserted by an automated test, not just
review.
"""
import json
import os
import sys
from pathlib import Path

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))


def _repo_root() -> Path:
    mnt = Path("/mnt/repo")
    if mnt.exists():
        return mnt
    return Path(__file__).resolve().parent.parent.parent


def _load_fixture() -> dict:
    fixture_path = _repo_root() / "fixtures" / "golden" / "fixture.json"
    with open(fixture_path, "r", encoding="utf-8") as f:
        return json.load(f)


def _load_manifest_text() -> str:
    manifest_path = _repo_root() / "fixtures" / "golden" / "MANIFEST.md"
    return manifest_path.read_text(encoding="utf-8")


def test_fixture_has_exactly_four_atom_types():
    fixture = _load_fixture()
    atom_types = {atom["type"] for atom in fixture["atoms"]}
    assert atom_types == {"ClassAtom", "DataPropertyAtom", "BuiltinAtom", "ObjectPropertyAtom"}
    assert len(fixture["atoms"]) == 4


def test_fixture_has_at_least_two_objects_with_mixed_outcomes():
    fixture = _load_fixture()
    outcomes = {row["expectedCanonicalStatus"] for row in fixture["expectedOutcomes"]}
    assert "passed" in outcomes
    assert "failed" in outcomes
    assert len(fixture["objects"]) >= 2


def test_fixture_design_state_covers_all_three_kinds():
    fixture = _load_fixture()
    kinds = {state["kind"] for state in fixture["designState"]["states"]}
    assert kinds == {"ObjState", "ParamState", "PropState"}


def test_fixture_has_geometry_reference():
    fixture = _load_fixture()
    assert "geometry" in fixture
    assert fixture["geometry"]["speckleObjectId"]
    assert "boundingBox" in fixture["geometry"]


def test_fixture_has_no_population_expected_row():
    fixture = _load_fixture()
    no_population_rows = [
        row for row in fixture["expectedOutcomes"] if row["expectedCanonicalStatus"] == "no_population"
    ]
    assert len(no_population_rows) >= 1


def test_fixture_expected_outcomes_sorted_ascending_by_objectid():
    fixture = _load_fixture()
    object_ids = [row["objectId"] for row in fixture["expectedOutcomes"]]
    assert object_ids == sorted(object_ids)


def test_manifest_names_objectpropertyatom_and_phase_1201():
    manifest_text = _load_manifest_text()
    assert "ObjectPropertyAtom" in manifest_text
    assert "1201" in manifest_text
