"""Tests for property_scripts.py (Phase 1303-15, DGOPN-02): rule DataProperty -> catalogue
calculator resolution and deterministic script assembly. No Neo4j, no Rhino."""

from __future__ import annotations

import os
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import property_scripts as ps  # noqa: E402

DG = "https://w3id.org/dg#"
PROJECT = "str-openings-01"
RULE_PROPS = {
    "R_STR_OPENING_ABOVE_V": "hasOpeningsBelowCount",
    "R_STR_OPENING_BEAM_V": "hasBeamIntersectionCount",
    "R_STR_OPENING_CLEARANCE_300_V": "hasMinOpeningClearanceMm",
    "R_STR_OPENING_COLUMN_V": "hasColumnIntersectionCount",
}


def _rows(rule_props=RULE_PROPS, box="OpeningBox"):
    rows = []
    for rule_id, prop in rule_props.items():
        rows.append({"ruleId": rule_id, "labels": ["Class"], "iri": DG + box, "label": box})
        rows.append({"ruleId": rule_id, "labels": ["DatatypeProperty"], "iri": DG + prop, "label": prop})
    return rows


@pytest.fixture(scope="module")
def catalogue():
    return ps.load_catalogue()


def test_rows_group_into_rules_sorted_by_id():
    rules = ps.rules_from_rows(reversed(_rows()))
    assert [r["ruleId"] for r in rules] == sorted(RULE_PROPS)
    assert all(len(r["classes"]) == 1 and len(r["dataProperties"]) == 1 for r in rules)


def test_four_opening_properties_resolve_by_alias(catalogue):
    res = ps.resolve(ps.rules_from_rows(_rows()), catalogue)
    assert res["unsupported"] == []
    assert res["boxClass"] == {"iri": DG + "OpeningBox", "label": "OpeningBox"}
    by_rule = {r["ruleId"]: r for r in res["resolved"]}
    assert by_rule["R_STR_OPENING_BEAM_V"]["calculator"] == "revit_category_intersection_count"
    assert by_rule["R_STR_OPENING_BEAM_V"]["params"] == {"categories": ["OST_StructuralFraming"]}
    assert by_rule["R_STR_OPENING_COLUMN_V"]["params"] == {"categories": ["OST_StructuralColumns", "OST_Columns"]}
    assert by_rule["R_STR_OPENING_ABOVE_V"]["calculator"] == "revit_openings_below_count"
    clearance = by_rule["R_STR_OPENING_CLEARANCE_300_V"]
    assert clearance["calculator"] == "revit_min_opening_clearance_mm"
    assert clearance["params"]["sentinel_mm"] == 100000
    assert all(r["resolvedBy"] == "alias" for r in res["resolved"])


def test_unknown_property_is_unsupported_not_guessed(catalogue):
    rules = ps.rules_from_rows(_rows({"R_X_V": "hasFireRatingMinutes"}))
    res = ps.resolve(rules, catalogue)
    assert res["resolved"] == []
    assert res["unsupported"][0]["dataPropertyLabel"] == "hasFireRatingMinutes"
    with pytest.raises(ps.PropertyScriptError) as err:
        ps.assemble(PROJECT, res, catalogue)
    assert err.value.code == "NOTHING_TO_COMPUTE"


def test_chooser_answer_outside_catalogue_is_rejected(catalogue):
    rules = ps.rules_from_rows(_rows({"R_X_V": "hasPipeClearanceMm"}))

    def rogue(_dp, _menu):
        return {"calculator": "import os; os.system('x')", "params": {}}

    def bad_params(_dp, _menu):
        return {"calculator": "revit_category_intersection_count", "params": {"categories": ["__import__"]}}

    def good(_dp, menu):
        assert "revit_min_opening_clearance_mm" in menu
        return {"calculator": "revit_min_opening_clearance_mm", "params": {"sentinel_mm": 5000}}

    assert ps.resolve(rules, catalogue, rogue)["resolved"] == []
    assert ps.resolve(rules, catalogue, bad_params)["resolved"] == []
    chosen = ps.resolve(rules, catalogue, good)["resolved"][0]
    assert chosen["resolvedBy"] == "chooser"
    assert chosen["params"] == {"opening_categories": ["OST_Doors", "OST_Windows", "OST_SWallRectOpening"],
                                "sentinel_mm": 5000}


def test_rules_over_two_classes_are_refused(catalogue):
    rows = _rows({"R_A_V": "hasBeamIntersectionCount"}) + _rows({"R_B_V": "hasOpeningsBelowCount"}, box="Duct")
    with pytest.raises(ps.PropertyScriptError) as err:
        ps.resolve(ps.rules_from_rows(rows), catalogue)
    assert err.value.code == "BOX_CLASS_AMBIGUOUS"


def test_assembly_is_byte_identical_and_valid_python(catalogue):
    res = ps.resolve(ps.rules_from_rows(_rows()), catalogue)
    first = ps.assemble(PROJECT, res, catalogue)
    second = ps.assemble(PROJECT, ps.resolve(ps.rules_from_rows(list(reversed(_rows()))), catalogue), catalogue)
    for key in ("calculator", "highlighter"):
        assert first[key]["source"] == second[key]["source"]
        assert first[key]["sha256"] == second[key]["sha256"]
        source = first[key]["source"]
        assert source.startswith("#! python3\n")
        assert "$" not in source  # every template slot substituted
        compile(source, f"<{key}>", "exec")  # parses as Python 3
    calc = first["calculator"]["source"]
    assert "project:     str-openings-01" in calc
    for rule_id in RULE_PROPS:
        assert rule_id in calc
    assert 'BOX_CLASS_IRI = "https://w3id.org/dg#OpeningBox"' in calc
    for fn in ("calc_category_intersection_count", "calc_openings_below_count", "calc_min_opening_clearance_mm"):
        assert f"def {fn}(" in calc


def test_outputs_match_property_count_and_placement_wires(catalogue):
    out = ps.assemble(PROJECT, ps.resolve(ps.rules_from_rows(_rows()), catalogue), catalogue)
    outputs = out["calculator"]["outputs"]
    for k in range(1, 5):
        assert {f"R{k}", f"D{k}", f"P{k}"} <= set(outputs)
    assert "P5" not in outputs
    plan = out["placement"]
    keys = {c["key"] for c in plan["components"]}
    assert sum(1 for c in plan["components"] if c.get("type") == "PROPERTY STATE") == 4
    script_ports = {
        "calculator": {i["name"] for i in out["calculator"]["inputs"]} | set(outputs),
        "highlighter": {i["name"] for i in out["highlighter"]["inputs"]} | set(out["highlighter"]["outputs"]),
    }
    for source, target in plan["wires"]:
        for end in (source, target):
            key, _, port = end.partition(".")
            assert key in keys, end
            if key in script_ports and port:
                assert port in script_ports[key], end
    connector = next(c for c in plan["components"] if c["key"] == "connector")
    assert connector["reuse"] and connector["required"]


class _Result:
    def __init__(self, rows):
        self._rows = rows

    def data(self):
        return self._rows

    def consume(self):
        return None


class _Session:
    """Fake Neo4j session: rule atoms, stored calculators, and recorded saves."""

    def __init__(self, rows, stored=()):
        self.rows = rows
        self.stored = list(stored)
        self.calls = []
        self.saved = []

    def run(self, query, **params):
        self.calls.append((query, params))
        if "PropertyCalculator" in query and query.lstrip().startswith("MERGE"):
            self.saved.append(params)
            return _Result([])
        if "PropertyCalculator" in query:
            return _Result(self.stored)
        return _Result(self.rows)


def test_generate_reads_rules_through_the_session(catalogue):
    session = _Session(_rows())
    out = ps.generate(session, PROJECT, None, catalogue=catalogue)
    assert session.calls[0][1] == {"project": PROJECT, "ruleIds": None}
    assert "SUPERSEDED_BY" in session.calls[0][0]  # same corpus as VALIDATOR: an updated rule drops the old version
    assert len(out["resolved"]) == 4 and out["unsupported"] == []
    assert out["catalogueVersion"] == catalogue["version"]
    assert session.saved == []  # preview writes nothing


def test_generate_with_store_saves_new_bindings_once(catalogue):
    session = _Session(_rows())
    ps.generate(session, PROJECT, None, catalogue=catalogue, store=True, actor="owner")
    assert sorted(s["dataPropertyIri"] for s in session.saved) == sorted(DG + p for p in RULE_PROPS.values())
    assert all(s["origin"] == "catalogue" and s["createdBy"] == "owner" for s in session.saved)


GOOD_FUNCTION = (
    "def calc_gen(ctx, box, params):\n"
    "    best = None\n"
    "    for wall in ctx.host_walls(box):\n"
    "        frame = ctx.wall_frame(wall)\n"
    "        if frame is None:\n"
    "            continue\n"
    "        u0, u1, z0, z1 = ctx.rect_in_wall(box, frame)\n"
    "        h = (z1 - z0) * FEET_TO_MM\n"
    "        best = h if best is None else max(best, h)\n"
    "    return 0.0 if best is None else round(best, 1)\n"
)


def test_unknown_property_is_generated_validated_stored_and_then_reused(catalogue):
    from property_calculator_llm import finalize

    calls = []

    def generator(dp, rules, box):
        calls.append((dp["label"], [r["ruleId"] for r in rules], box))
        name, source = finalize(GOOD_FUNCTION)
        return {"status": "ok", "function": name, "source": source, "provider": "fake", "model": "m"}

    rows = _rows({"R_STR_OPENING_HEIGHT_V": "hasOpeningHeightMm"})
    session = _Session(rows)
    first = ps.generate(session, PROJECT, None, catalogue=catalogue, generator=generator, store=True)
    assert calls == [("hasOpeningHeightMm", ["R_STR_OPENING_HEIGHT_V"], "OpeningBox")]
    entry = first["resolved"][0]
    assert entry["origin"] == "generated" and entry["calculator"].startswith("generated:")
    calc = first["calculator"]["source"]
    assert f"def {entry['function']}(" in calc
    compile(calc, "<calc>", "exec")
    assert session.saved[0]["origin"] == "generated" and session.saved[0]["source"] == entry["source"]

    # The next generation (rule update, new Design State) reuses the stored source: no LLM call, same bytes.
    stored = [{"dataPropertyIri": s["dataPropertyIri"], "calculator": s["calculator"], "origin": s["origin"],
               "paramsJson": s["paramsJson"], "function": s["function"], "source": s["source"],
               "sha256": s["sha256"], "provider": s["provider"], "model": s["model"],
               "createdAt": None, "createdBy": None}
              for s in session.saved]
    again = ps.generate(_Session(rows, stored), PROJECT, None, catalogue=catalogue, generator=generator, store=True)
    assert len(calls) == 1
    assert again["resolved"][0]["resolvedBy"] == "stored"
    assert again["calculator"]["sha256"] == first["calculator"]["sha256"]


def test_failed_generation_is_reported_unsupported(catalogue):
    rows = _rows({"R_A_V": "hasBeamIntersectionCount"}) + _rows({"R_B_V": "hasFireRatingMinutes"})
    out = ps.generate(_Session(rows), PROJECT, None, catalogue=catalogue,
                      generator=lambda dp, rules, box: {"status": "invalid", "error": "forbidden model call: Delete"})
    assert [r["ruleId"] for r in out["resolved"]] == ["R_A_V"]
    assert out["unsupported"][0]["reason"].startswith("generation invalid: forbidden model call")
