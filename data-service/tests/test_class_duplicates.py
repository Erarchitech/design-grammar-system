"""Near-duplicate classes and properties (Phase 1303-15, owner 2026-10-20)."""

from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import class_duplicates as cd  # noqa: E402


def _items(names):
    return [{"iri": "ex:" + n, "label": n} for n in names]


STR = ["Beam", "Column", "Door", "Opening", "Wall", "WallOpening", "Window"]
FACADE = ["GlassPanel", "HexagonalUnit", "GroundFloorUnit", "BottomTriangularPanel", "Facade", "FacadeModule"]
PROPS = ["hasBeamIntersectionCount", "hasColumnIntersectionCount", "hasMinHostOpeningClearanceMm",
         "hasMinOpeningClearanceMm", "hasOpeningsBelowCount", "hasOpeningViolation", "hasAspectRatio",
         "hasVertexCount", "hasWidthM", "hasGapCount", "hasLevelOffsetM", "hasPlanarityDeviationM"]


def pairs(found):
    return {(c["a"]["label"], c["b"]["label"]) for c in found}


def test_reports_the_opening_and_property_duplicates_of_the_openings_project():
    found = pairs(cd.candidates(_items(STR), _items(PROPS)))
    assert found == {("Opening", "WallOpening"), ("hasMinHostOpeningClearanceMm", "hasMinOpeningClearanceMm")}


def test_different_head_nouns_are_not_duplicates():
    assert cd.class_reason("Wall", "WallOpening") is None
    assert cd.class_reason("Facade", "FacadeModule") is None
    assert cd.class_reason("Door", "Window") is None
    assert cd.candidates(_items(FACADE), []) == []


def test_synonyms_and_generic_carriers_are_folded():
    assert cd.class_reason("Floor", "Slab")
    assert cd.class_reason("Opening", "OpeningBox")
    assert cd.class_reason("Opening", "Hole")


def test_a_settled_pair_is_not_reported_again():
    found = cd.candidates(_items(STR), [], resolved=[("ex:WallOpening", "ex:Opening")])
    assert found == []


class _Session:
    def __init__(self, rows, resolved=()):
        self.rows, self.resolved = rows, list(resolved)

    def run(self, query, **params):
        class R:
            def __init__(self, data):
                self._d = data

            def data(self):
                return self._d
        return R(self.resolved if "DISTINCT_FROM" in query else self.rows)


def test_ingest_question_only_concerns_new_entities_and_puts_the_new_one_first():
    rows = [{"kind": "Class", "iri": "ex:" + n, "label": n} for n in ("Opening", "Beam", "WallOpening")]
    found = cd.find(_Session(rows), "p", new_iris=["ex:Opening"])
    assert [(c["a"]["label"], c["b"]["label"], c["existing"]) for c in found] == [("Opening", "WallOpening", True)]
    assert cd.find(_Session(rows), "p", new_iris=["ex:Beam"]) == []


def test_properties_are_compared_by_iri_name_not_by_a_descriptive_label():
    props = [{"iri": "ex:hasMinHostOpeningClearanceMm", "label": "minimum clear distance to a door or window (mm)"},
             {"iri": "ex:hasMinOpeningClearanceMm", "label": "hasMinOpeningClearanceMm"}]
    assert len(cd.candidates([], props)) == 1
