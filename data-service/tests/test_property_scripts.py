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
    assert chosen["params"] == {"opening_categories": ["OST_Doors", "OST_Windows"],
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
        if "READS_CLASS" in query:
            if "MERGE (k:Class" in query:
                self.classes = getattr(self, "classes", []) + [params]
            return _Result([])
        if "PropertyCalculator" in query and query.lstrip().startswith("MERGE"):
            self.saved.append(params)
            return _Result([])
        if ("DISTINCT_FROM" in query or "AS kind, n.iri" in query or "source:'property_scripts'" in query
                or "coalesce(k.label, k.iri) AS label" in query):
            return _Result([])  # duplicate scan and context-class pruning see an empty ontology here
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


def test_classes_behind_the_read_categories_are_created_and_linked(catalogue):
    session = _Session(_rows())
    out = ps.generate(session, PROJECT, None, catalogue=catalogue, store=True)
    by_rule = {r["ruleId"]: [c["label"] for c in r["contextClasses"]] for r in out["resolved"]}
    assert by_rule["R_STR_OPENING_BEAM_V"] == ["Beam"]
    assert by_rule["R_STR_OPENING_COLUMN_V"] == ["Column"]
    assert by_rule["R_STR_OPENING_ABOVE_V"] == ["Door", "Wall", "Window"]  # wall rect openings are not proyomy
    assert by_rule["R_STR_OPENING_CLEARANCE_300_V"] == ["Door", "Wall", "Window"]
    column = next(c for r in out["resolved"] for c in r["contextClasses"] if c["label"] == "Column")
    assert column == {"label": "Column", "iri": DG + "Column", "revitCategories": ["OST_Columns", "OST_StructuralColumns"]}
    written = {(c["dataPropertyIri"].split("#")[-1], c["label"]) for c in session.classes}
    assert ("hasBeamIntersectionCount", "Beam") in written and ("hasOpeningsBelowCount", "Window") in written
    assert ("hasOpeningsBelowCount", "WallOpening") not in written
    assert len(session.classes) == 1 + 1 + 3 + 3


def test_preview_creates_no_classes(catalogue):
    session = _Session(_rows())
    ps.generate(session, PROJECT, None, catalogue=catalogue)
    assert not getattr(session, "classes", [])


def test_generated_calculator_classes_come_from_its_source_not_from_the_llm(catalogue):
    from property_calculator_llm import finalize

    source = "def calc_gen(ctx, box, params):\n    return len(ctx.intersecting(box, ['OST_Floors', 'OST_Bogus']))\n"

    def generator(dp, rules, box):
        name, src = finalize(source)
        return {"status": "ok", "function": name, "source": src, "provider": "fake", "model": "m"}

    out = ps.generate(_Session(_rows({"R_X_V": "hasSlabCrossingCount"})), PROJECT, None, catalogue=catalogue,
                      generator=generator, store=True)
    assert out["resolved"][0]["contextClasses"] == [
        {"label": "Floor", "iri": DG + "Floor", "revitCategories": ["OST_Floors"]}]


def test_failed_generation_is_reported_unsupported(catalogue):
    rows = _rows({"R_A_V": "hasBeamIntersectionCount"}) + _rows({"R_B_V": "hasFireRatingMinutes"})
    out = ps.generate(_Session(rows), PROJECT, None, catalogue=catalogue,
                      generator=lambda dp, rules, box: {"status": "invalid", "error": "forbidden model call: Delete"})
    assert [r["ruleId"] for r in out["resolved"]] == ["R_A_V"]
    assert out["unsupported"][0]["reason"].startswith("generation invalid: forbidden model call")


def test_rule_classes_are_created_with_the_rule_for_every_element_class(catalogue):
    # Owner 2026-10-20: "no openings in columns" must create OpeningBox (ingest) and Column (here).
    rows = _rows({"R_COL_V": "hasColumnIntersectionCount"}) + _rows({"R_FAC_V": "hasAspectRatio"}, box="GlassPanel")
    session = _Session(rows)
    calls = []

    def generator(dp, rules, box):
        calls.append((dp["label"], box))
        return {"status": "invalid", "error": "not a Revit property"}

    out = ps.ensure_rule_classes(session, PROJECT, catalogue=catalogue, generator=generator, actor="owner")
    assert out["linked"] == [{"ruleId": "R_COL_V", "dataPropertyIri": DG + "hasColumnIntersectionCount",
                              "classes": ["Column"]}]
    assert [u["ruleId"] for u in out["unsupported"]] == ["R_FAC_V"]  # another element class does not block it
    assert calls == [("hasAspectRatio", "GlassPanel")]
    column = [c for q, c in session.calls if "MERGE (k:Class" in q]
    assert [c["label"] for c in column] == ["Column"] and column[0]["iri"] == DG + "Column"


def test_wording_variant_binds_to_the_vetted_calculator_and_replaces_a_generated_one(catalogue):
    """hasMinHostOpeningClearanceMm (LLM wording) is hasMinOpeningClearanceMm: the catalogue calculator is used and
    supersedes the generated calculator stored for it earlier; the LLM is not asked again."""
    rows = _rows({"R4": "hasMinHostOpeningClearanceMm"})
    stored = [{"dataPropertyIri": DG + "hasMinHostOpeningClearanceMm", "calculator": "generated:3e8b69da92",
               "origin": "generated", "paramsJson": "{}", "function": "calc_gen_x", "source": "def calc_gen_x(): pass",
               "sha256": "x", "provider": "openai", "model": "m", "createdAt": None, "createdBy": None}]
    session = _Session(rows, stored)
    out = ps.generate(session, PROJECT, None, catalogue=catalogue, store=True,
                      generator=lambda *a: pytest.fail("the LLM must not be asked"))
    entry = out["resolved"][0]
    assert entry["calculator"] == "revit_min_opening_clearance_mm"
    assert entry["resolvedBy"] == "vocabulary-near-match" and entry["nearMatch"] == "hasMinOpeningClearanceMm"
    assert session.saved and session.saved[0]["origin"] == "catalogue"


def test_alias_and_near_match_use_the_iri_name_when_the_label_is_a_description(catalogue):
    dp = {"iri": DG + "hasMinHostOpeningClearanceMm", "label": "minimum clear distance to a door or window (mm)"}
    assert ps.resolve_property(dp, catalogue)["calculator"] == "revit_min_opening_clearance_mm"
    dp = {"iri": DG + "hasBeamIntersectionCount", "label": "number of beams the box crosses"}
    assert ps.resolve_property(dp, catalogue)["resolvedBy"] == "alias"


def test_check_summary_never_reports_a_failed_chain_as_clean():
    import app as app_module

    failed = {"finished": True, "send": True, "clear": False, "status": {
        "boxes": 0, "violations": [], "validationRunId": [],
        "messages": ["error DG PROPERTY CALCULATOR: Rhino.UnitSystem value cannot be converted", "warning RULE BY ID: Set RuleId."]}}
    s = app_module.property_check_summary(failed)
    assert s["ok"] is False and s["problems"][0].startswith("error DG PROPERTY CALCULATOR")
    good = {"finished": True, "send": True, "clear": False, "status": {
        "boxes": 12, "violations": ["box [1]: R1"], "validationRunId": ["VR-1"], "messages": []}}
    assert app_module.property_check_summary(good) == {"ok": True, "problems": [], "boxes": 12, "violations": 1,
                                                       "validationRunIds": ["VR-1"], "published": True}


def test_atom_type_repair_derives_the_type_from_refers_to_and_never_overwrites():
    import app as app_module

    q = app_module.ATOM_TYPE_REPAIR
    assert "a.type IS NULL OR a.type = ''" in q and "project:$project" in q
    for label, atom_type in (("Class", "ClassAtom"), ("DatatypeProperty", "DataPropertyAtom"),
                             ("ObjectProperty", "ObjectPropertyAtom"), ("Builtin", "BuiltinAtom")):
        assert f"p:{label} THEN '{atom_type}'" in q
