"""Tests for property_calculator_review.py (Phase 1303-17, DGOPN-05, D-54, D-58, D-59). Pure: no Neo4j, no app."""

from __future__ import annotations

import json
import os
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import property_calculator_review as review  # noqa: E402

DG = "https://w3id.org/dg#"
IRI = DG + "hasOpeningHeightMm"
OTHER = DG + "hasBeamIntersectionCount"


def _payload(count=12):
    """A v2 envelope: `count` boxes with a numeric height, one non-numeric value, one duplicate, one other property."""
    objs = [{"stateId": f"OS_{i}", "objectRef": f"box-{i:02d}", "label": f"Box [{i}]", "classIri": DG + "OpeningBox"}
            for i in range(count)]
    props = [{"stateId": f"PS_{i}", "ruleIri": "R1", "dataPropertyIri": IRI, "objectRef": f"box-{i:02d}",
              "propValue": {"value": 100.0 + i, "type": "double", "displayName": "h"}} for i in range(count)]
    props.append({"stateId": "PS_dup", "dataPropertyIri": IRI, "objectRef": "box-00",
                  "propValue": {"value": 100.0, "type": "double"}})  # same (objectRef, value) as box-00
    props.append({"stateId": "PS_text", "dataPropertyIri": IRI, "objectRef": "box-99",
                  "propValue": {"value": "n/a", "type": "string"}})
    props.append({"stateId": "PS_bool", "dataPropertyIri": IRI, "objectRef": "box-98",
                  "propValue": {"value": True, "type": "boolean"}})
    props.append({"stateId": "PS_other", "dataPropertyIri": OTHER, "objectRef": "box-00",
                  "propValue": {"value": 7, "type": "integer"}})
    props.append({"stateId": "PS_bad", "dataPropertyIri": IRI, "objectRef": "box-01", "propValue": "not a dict"})
    return {"version": "2", "objStates": objs, "propStates": props}


def _run(created="2026-10-22T10:00:00Z", run_id="VR-1", payload=None):
    return {"runId": run_id, "createdAt": created,
            "statePayloadJson": json.dumps(payload if payload is not None else _payload())}


def _calc(iri=IRI, created="2026-10-22T09:00:00Z", **extra):
    row = {"dataPropertyIri": iri, "function": "calc_gen_0123456789",
           "source": "def calc_gen_0123456789(ctx, box, params):\n    return len(ctx.intersecting(box, ['OST_Floors']))\n",
           "sha256": "a" * 64, "unit": "mm", "explanation": "tallest", "provider": "fake", "model": "m",
           "createdAt": created, "createdBy": "owner", "catalogueId": None, "retired": False}
    row.update(extra)
    return row


def test_run_values_keep_the_property_dedupe_and_sort():
    values = review.run_values(_run(), IRI)
    refs = [v["objectRef"] for v in values]
    assert refs == sorted(refs) and refs.count("box-00") == 1  # the duplicate is gone
    assert len(values) == 12 + 2  # 12 boxes + the text value + the bool value; the other property and bad row are not
    assert values[0] == {"objectRef": "box-00", "label": "Box [0]", "value": 100.0}
    assert next(v for v in values if v["objectRef"] == "box-99")["label"] is None  # no objState: no label


@pytest.mark.parametrize("bad", [None, "", "{not json", "[1, 2]", json.dumps({"propStates": "x"})])
def test_run_values_of_an_invalid_or_absent_payload_are_empty(bad):
    assert review.run_values({"runId": "r", "statePayloadJson": bad}, IRI) == []
    assert review.run_values(None, IRI) == []


def test_sample_summary_caps_samples_and_ranges_over_numbers_only():
    summary = review.sample_summary(review.run_values(_run(), IRI))
    assert len(summary["samples"]) == review.SAMPLE_LIMIT == 10
    assert summary["stats"] == {"n": 14, "numeric": 12, "min": 100.0, "max": 111.0}  # bool and text are not numeric
    empty = review.sample_summary([])
    assert empty == {"samples": [], "stats": {"n": 0, "numeric": 0, "min": None, "max": None}}
    textual = review.sample_summary([{"objectRef": "a", "label": None, "value": "x"}])
    assert textual["stats"] == {"n": 1, "numeric": 0, "min": None, "max": None}


def test_verdict_counts_group_by_rule_and_sort():
    rows = [{"ruleId": "R_B", "status": "pass", "count": 3}, {"ruleId": "R_A", "status": "violation", "count": 2},
            {"ruleId": "R_A", "status": "pass", "count": 10}]
    assert review.verdict_counts(rows) == [{"ruleId": "R_A", "counts": {"pass": 10, "violation": 2}},
                                           {"ruleId": "R_B", "counts": {"pass": 3}}]
    assert review.verdict_counts(None) == []


def test_clean_line_collapses_whitespace_drops_controls_and_caps():
    assert review.clean_line("  tallest \t opening\n height\x00 ", 160) == "tallest opening height"
    assert review.clean_line("a" * 500, 40) == "a" * 40
    assert review.clean_line("ab cd", 3) == "ab"  # the cap never leaves a trailing space
    assert review.clean_line("zero​width‮", 160) == "zerowidth"  # format characters are dropped


@pytest.mark.parametrize("empty", ["", "   ", "\x00\x01", "\n\t", None, 5])
def test_clean_line_raises_when_nothing_is_left(empty):
    with pytest.raises(ValueError):
        review.clean_line(empty, 160)


def test_build_candidates_show_source_samples_stats_verdicts_and_a_newer_run():
    candidates = review.build_candidates(
        [_calc(OTHER), _calc(IRI)], _run(), {IRI: [{"ruleId": "R1", "status": "pass", "count": 12}]},
        {IRI: ["R2", "R1"]})
    assert [c["dataPropertyIri"] for c in candidates] == sorted([IRI, OTHER])
    mine = next(c for c in candidates if c["dataPropertyIri"] == IRI)
    assert mine["propertyName"] == "hasOpeningHeightMm" and mine["source"].startswith("def calc_gen_")
    assert mine["readCategories"] == ["OST_Floors"] and mine["ruleIds"] == ["R1", "R2"]
    assert len(mine["samples"]) == 10 and mine["stats"]["n"] == 14
    assert mine["verdicts"] == [{"ruleId": "R1", "counts": {"pass": 12}}]
    assert mine["run"] == {"runId": "VR-1", "createdAt": "2026-10-22T10:00:00Z"}
    assert mine["runNewerThanCalculator"] is True
    assert mine["retired"] is False and mine["catalogueId"] is None
    other = next(c for c in candidates if c["dataPropertyIri"] == OTHER)
    assert other["samples"] == [{"objectRef": "box-00", "label": "Box [0]", "value": 7}]
    assert other["verdicts"] == [] and other["ruleIds"] == []


def test_build_candidates_flag_a_run_older_than_the_calculator():
    candidates = review.build_candidates([_calc(created="2026-10-22T11:00:00Z")], _run("2026-10-22T10:00:00Z"), {}, {})
    assert candidates[0]["runNewerThanCalculator"] is False
    assert candidates[0]["run"]["runId"] == "VR-1" and candidates[0]["stats"]["n"] == 14


def test_build_candidates_without_a_run_have_no_samples_and_no_newer_flag():
    candidate = review.build_candidates([_calc()], None, {}, {})[0]
    assert candidate["run"] is None and candidate["runNewerThanCalculator"] is False
    assert candidate["samples"] == []
    assert candidate["stats"] == {"n": 0, "numeric": 0, "min": None, "max": None}


def test_build_candidates_retired_copy_uses_its_own_run_and_carries_the_catalogue_id():
    shared_run = _run("2026-10-22T10:00:00Z", "VR-NEW", {"version": "2", "objStates": [], "propStates": []})
    confirmed_on = _run("2026-10-21T12:00:00Z", "VR-OLD")
    retired = _calc(created="2026-10-21T09:00:00Z", retired=True, catalogueId="CC-0123456789abcdef")
    pending = _calc(OTHER, created="2026-10-22T09:00:00Z")
    candidates = review.build_candidates([retired, pending], shared_run, {}, {}, runs_by_property={IRI: confirmed_on})
    old = next(c for c in candidates if c["dataPropertyIri"] == IRI)
    assert old["retired"] is True and old["catalogueId"] == "CC-0123456789abcdef"
    assert old["run"]["runId"] == "VR-OLD" and old["stats"]["n"] == 14 and old["runNewerThanCalculator"] is True
    new = next(c for c in candidates if c["dataPropertyIri"] == OTHER)
    assert new["run"]["runId"] == "VR-NEW" and new["retired"] is False and new["samples"] == []


def test_module_stays_pure():
    import re

    path = os.path.join(os.path.dirname(__file__), "..", "property_calculator_review.py")
    imports = re.findall(r"^\s*(?:import|from)\s+([\w.]+)", open(path, encoding="utf-8").read(), re.M)
    assert "app" not in imports and not any(name.startswith("neo4j") for name in imports)
