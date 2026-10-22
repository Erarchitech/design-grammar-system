"""Tests for property_scripts.py (Phase 1303-15, DGOPN-02): rule DataProperty -> catalogue
calculator resolution and deterministic script assembly. No Neo4j, no Rhino."""

from __future__ import annotations

import json
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

    def __init__(self, rows, stored=(), catalogue=(), blocked=()):
        self.rows = rows
        self.stored = list(stored)
        self.catalogue = list(catalogue)
        self.blocked = list(blocked)
        self.calls = []
        self.saved = []

    def execute_write(self, fn, *args, **kwargs):
        return fn(self, *args, **kwargs)

    def run(self, query, **params):
        self.calls.append((query, params))
        # Phase 1303-16 marker contract: the save-state read carries `reviewLock`; it also names
        # `rejectedSha256Json` and starts with MERGE, so it is answered before every other branch.
        if "reviewLock" in query:
            iri = params.get("dataPropertyIri")
            return _Result([r for r in self.stored if r.get("dataPropertyIri") == iri])
        if "rejectedSha256Json" in query:
            return _Result(self.blocked)
        if "CatalogueCalculator" in query:
            return _Result(self.catalogue)
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


def test_bare_variable_names_get_the_question_mark_prefix():
    import app as app_module

    assert "SET v.name = '?' + v.name" in app_module.VAR_RENAME
    assert "NOT v.name STARTS WITH '?'" in app_module.VAR_RENAME and "project:$project" in app_module.VAR_RENAME
    assert "name: '?' + v.name" in app_module.VAR_MERGE_INTO_TWIN and "DELETE g" in app_module.VAR_MERGE_INTO_TWIN


def test_context_is_added_to_each_runs_validation_version(monkeypatch):
    import app as app_module
    import gh_bridge
    import speckle_validation

    monkeypatch.setattr(gh_bridge, "get_property_check_context", lambda project: {
        "count": 1, "skipped": 0,
        "elements": [
            {"label": "OST_Walls|Стены : Wall [1]", "geometry": {"units": "mm", "items": [
                {"kind": "mesh", "vertices": [0, 0, 0, 1, 0, 0, 0, 1, 0], "faces": [[0, 1, 2]]}]}},
            {"label": "OST_StructuralColumns|Колонны : C [2]", "geometry": {"units": "mm", "items": [
                {"kind": "mesh", "vertices": [0, 0, 0, 1, 0, 0, 0, 1, 0], "faces": [[0, 1, 2]]}]}}]})
    monkeypatch.setattr(app_module, "get_speckle_settings", lambda: speckle_validation.SpeckleConnectionSettings(
        base_url="http://s", internal_url="http://s", write_token="w", read_token="r", dg_base_url="http://dg"))
    monkeypatch.setattr(app_module, "rule_context_categories", lambda project: {
        "R_WALL": {"OST_Walls"}, "R_COL": {"OST_StructuralColumns", "OST_Columns"}})
    rule_of = {"run-a": "R_WALL", "run-b": "R_COL"}
    monkeypatch.setattr(app_module, "read_many", lambda q, p=None: [
        {"runId": r, "speckleProjectId": "p1", "validationModelId": "vm", "validationVersionId": "old-" + r,
         "rulesJson": json.dumps([{"ruleId": rule_of[r]}])} for r in p["runIds"]])
    calls = []
    monkeypatch.setattr(speckle_validation, "add_context_to_validation_version",
                        lambda settings, **kw: calls.append(kw) or "new-" + kw["run_id"])
    writes = []
    monkeypatch.setattr(app_module, "write_query", lambda q, p=None: writes.append(p))
    out = app_module._publish_check_context("str-openings-01", ["run-a", "run-b"])
    assert out["published"] is True and out["runs"] == ["run-a", "run-b"] and out["elements"] == 2
    assert [c["validation_version_id"] for c in calls] == ["old-run-a", "old-run-b"]
    # each run shows only its rule's classes: walls for the wall rule, columns for the column rule
    assert [[n["name"] for n in c["nodes"]] for c in calls] == [["OST_Walls|Стены : Wall [1]"],
                                                                 ["OST_StructuralColumns|Колонны : C [2]"]]
    assert [w["versionId"] for w in writes] == ["new-run-a", "new-run-b"]


def test_generated_calculator_output_names_do_not_shadow_its_helpers(catalogue):
    """Live 2026-10-21: the output 'Context = []' replaced the helper class Context, so the calculator failed with
    "'list' object is not callable". No assembled output may rebind a class or function of the script."""
    import ast

    out = ps.assemble(PROJECT, ps.resolve(ps.rules_from_rows(_rows()), catalogue), catalogue)
    tree = ast.parse(out["calculator"]["source"])
    defined = {n.name for n in tree.body if isinstance(n, (ast.ClassDef, ast.FunctionDef))}
    outputs = set(out["calculator"]["outputs"])
    assert not (defined & outputs), defined & outputs


def test_a_published_check_answers_at_once_and_publishes_context_in_the_background(monkeypatch):
    """Live 2026-10-21: DeGram got 504 (60 s proxy limit), and the toggle reset expired the chain mid-solution."""
    import app as app_module
    import gh_bridge

    calls = []
    monkeypatch.setattr(gh_bridge, "run_property_check", lambda params: calls.append(dict(params)) or {
        "finished": True, "send": params["send"], "clear": params["clear"], "paint": params["paint"],
        "status": {"boxes": 3, "violations": [], "validationRunId": ["VR-1"], "messages": []}})
    started = []

    class FakeThread:
        def __init__(self, target, args, daemon):
            started.append((target, args))

        def start(self):
            pass

    monkeypatch.setattr(app_module.threading, "Thread", FakeThread)
    monkeypatch.setattr(app_module, "read_many", lambda q, p=None: [{"runId": "VR-1"}])
    out = app_module.post_property_check_run(app_module.PropertyCheckRunRequest(project="p", refresh=False),
                                             request=None)
    assert len(calls) == 1 and calls[0]["send"] is True  # one canvas call, no reset run afterwards
    assert out["context"] == {"scheduled": True, "runs": ["VR-1"]}
    assert started and started[0][1] == ("p", ["VR-1"])



def test_highlighter_writes_revit_only_when_the_verdict_changed(catalogue):
    """Live 2026-10-21: each Revit write made Rhino.Inside re-solve, so repainting the same result looped forever."""
    out = ps.assemble(PROJECT, ps.resolve(ps.rules_from_rows(_rows()), catalogue), catalogue)
    src = out["highlighter"]["source"]
    assert "DG.Highlighter.LastDigest" in src and "if unchanged:" in src
    assert src.index("if unchanged:") < src.index("t.Start()")


def test_published_runs_are_read_from_the_graph_when_the_listener_stopped_waiting(monkeypatch):
    """Live 2026-10-21: the 4 publishes took ~70 s, the listener answered after 25 s and DeGram reported a failure."""
    import app as app_module
    import gh_bridge

    monkeypatch.setattr(gh_bridge, "run_property_check", lambda params: {
        "finished": False, "send": True, "clear": False, "paint": True,
        "status": {"boxes": 313, "violations": [], "validationRunId": ["", "", "", ""], "messages": [],
                   "ruleNames": ["R1", "R2", "R3", "R4"]}})
    polls = []

    def fake_read_many(query, params=None):
        polls.append(params)
        return [{"runId": "VR-%d" % i} for i in range(min(4, 2 * len(polls)))]

    monkeypatch.setattr(app_module, "read_many", fake_read_many)
    monkeypatch.setattr(app_module, "PUBLISH_POLL_S", 0)
    monkeypatch.setattr(app_module, "_publish_check_context", lambda project, runs: None)

    class NoThread:
        def __init__(self, target, args, daemon):
            pass

        def start(self):
            pass

    monkeypatch.setattr(app_module.threading, "Thread", NoThread)
    out = app_module.post_property_check_run(app_module.PropertyCheckRunRequest(project="p", refresh=False),
                                             request=None)
    assert out["summary"]["ok"] is True and out["summary"]["published"] is True
    assert out["summary"]["validationRunIds"] == ["VR-0", "VR-1", "VR-2", "VR-3"] and len(polls) == 2


def _shell_namespace(source):
    """The model-reading part of an assembled calculator (constants, helpers, ModelContext) against a fake Revit DB."""
    import ast
    import types

    class Xyz:
        def __init__(self, x, y, z):
            self.X, self.Y, self.Z = x, y, z

    class Box:
        def __init__(self, lo, hi):
            self.Min, self.Max = Xyz(*lo), Xyz(*hi)

    names = ["OST_GenericModel", "OST_StructuralFraming", "OST_StructuralColumns", "OST_Columns", "OST_Walls",
             "OST_Floors", "OST_Doors", "OST_Windows", "OST_SWallRectOpening", "OST_ArcWallRectOpening",
             "OST_StructuralFoundation", "OST_Roofs"]
    bic = types.SimpleNamespace(**{n: -2000 - i for i, n in enumerate(names)})

    class Collector:
        def __init__(self, doc):
            self.doc = doc
            self.cat = None

        def OfCategory(self, c):
            self.cat = int(c)
            return self

        def OfCategoryId(self, cid):
            self.cat = cid.IntegerValue
            return self

        def WhereElementIsNotElementType(self):
            return self

        def __iter__(self):
            return iter([e for e in self.doc.elements if e.Category.Id.IntegerValue == self.cat])

    db = types.SimpleNamespace(BuiltInCategory=bic, FilteredElementCollector=Collector,
                               StorageType=types.SimpleNamespace(String="String"),
                               Options=lambda: types.SimpleNamespace())
    tree = ast.parse(source)
    wanted = ("_bic", "_text_parameter", "dg_classes", "ModelContext")
    skipped = {n.name for n in tree.body if isinstance(n, (ast.FunctionDef, ast.ClassDef)) and n.name not in wanted}
    keep = [n for n in tree.body
            if (isinstance(n, ast.Assign)
                and all(isinstance(t, ast.Name) and t.id.isupper() and not t.id.startswith("_") for t in n.targets)
                and not any(m.id in skipped or m.id.startswith("_")
                            for m in ast.walk(n.value) if isinstance(m, ast.Name)))
            or (isinstance(n, (ast.FunctionDef, ast.ClassDef)) and n.name in wanted)]
    ns = {"DB": db, "math": __import__("math")}
    exec(compile(ast.Module(body=keep, type_ignores=[]), "<shell>", "exec"), ns)

    def element(eid, category, dg_class="", state="", lo=(0, 0, 0), hi=(1, 1, 1)):
        params = {"DG_Class": dg_class, "DG_MappingState": state}

        def lookup(name):
            if name not in params:
                return None
            return types.SimpleNamespace(StorageType="String", AsString=lambda: params[name])

        cat = types.SimpleNamespace(Id=types.SimpleNamespace(IntegerValue=int(getattr(bic, category))))
        return types.SimpleNamespace(Id=types.SimpleNamespace(IntegerValue=eid), Category=cat,
                                     LookupParameter=lookup, get_BoundingBox=lambda view: Box(lo, hi))

    return ns, element, bic


def test_an_element_mapped_to_a_class_is_read_as_that_class_whatever_its_revit_category(catalogue):
    """Live 2026-10-21: column 4711685 is modelled as a wall (category Walls) and mapped DG_Class = Column; the column
    calculator read only the column categories, so three boxes through it passed and the run showed no column."""
    out = ps.assemble(PROJECT, ps.resolve(ps.rules_from_rows(_rows()), catalogue), catalogue)
    ns, element, bic = _shell_namespace(out["calculator"]["source"])

    pylon = element(4711685, "OST_Walls", "Column", "confirmed")
    wall = element(1, "OST_Walls", "Wall", "confirmed")
    unmapped_wall = element(2, "OST_Walls")
    column = element(3, "OST_StructuralColumns")
    rejected = element(4, "OST_Walls", "Column", "rejected")
    types_ns = __import__("types")
    walls_cat = types_ns.SimpleNamespace(Id=types_ns.SimpleNamespace(IntegerValue=int(bic.OST_Walls)))

    class Bindings:
        def ForwardIterator(self):
            items = iter([(types_ns.SimpleNamespace(Name="DG_Class"),
                           types_ns.SimpleNamespace(Categories=[walls_cat]))])

            class It:
                Key = Current = None

                def MoveNext(self):
                    try:
                        self.Key, self.Current = next(items)
                        return True
                    except StopIteration:
                        return False
            return It()

    doc = types_ns.SimpleNamespace(elements=[pylon, wall, unmapped_wall, column, rejected], ParameterBindings=Bindings())
    ctx = ns["ModelContext"](doc, [])
    columns = sorted(e.Id.IntegerValue for e, _lo, _hi in ctx.candidates(["OST_StructuralColumns", "OST_Columns"]))
    walls = sorted(e.Id.IntegerValue for e, _lo, _hi in ctx.candidates(["OST_Walls"]))
    assert columns == [3, 4711685]
    assert walls == [1, 2, 4]  # the pylon is a Column now; a rejected mapping does not reclassify
    assert ctx.category_of[4711685] in ("OST_StructuralColumns", "OST_Columns")
    assert ctx.category_of[1] == "OST_Walls"


def test_a_check_whose_runs_are_still_uploading_is_not_started_again(monkeypatch):
    """Live 2026-10-21 12:55: VALIDATOR uploads its runs after the solution (one per rule, ~25 s apart), so SendValid is
    already off and no run exists when the listener answers. Taking that for an early reset started the check again;
    the canvas answered BUSY while it published, DeGram got 502 and the model context was never added."""
    import app as app_module
    import gh_bridge

    calls = []
    monkeypatch.setattr(gh_bridge, "run_property_check", lambda params: calls.append(dict(params)) or {
        "finished": True, "send": True, "clear": False, "paint": True,
        "status": {"boxes": 313, "violations": [], "validationRunId": [""], "messages": [],
                   "ruleNames": ["R1", "R2", "R3", "R4"]}})
    monkeypatch.setattr(gh_bridge, "get_property_check_status", lambda project: {
        "toggles": {"Run": True, "SendValid": False, "Paint": False}, "boxes": 313})
    polls = []

    def fake_read_many(query, params=None):
        polls.append(query)
        return [{"runId": "VR-%d" % i, "n": 0} for i in range(min(4, len(polls) - 1))]

    monkeypatch.setattr(app_module, "read_many", fake_read_many)
    monkeypatch.setattr(app_module, "PUBLISH_POLL_S", 0)
    started = []

    class FakeThread:
        def __init__(self, target, args, daemon):
            started.append(args)

        def start(self):
            pass

    monkeypatch.setattr(app_module.threading, "Thread", FakeThread)
    out = app_module.post_property_check_run(app_module.PropertyCheckRunRequest(project="p", refresh=False),
                                             request=None)
    assert len(calls) == 1  # never started a second time
    assert out["summary"]["validationRunIds"] == ["VR-0", "VR-1", "VR-2", "VR-3"]
    assert started == [("p", ["VR-0", "VR-1", "VR-2", "VR-3"])]


def test_the_view_names_the_source_model_and_the_element_id_in_it():
    """Owner 2026-10-21: a picked element shows the model it was exported from and its id in that model."""
    import app as app_module

    state = json.dumps({"objStates": [
        {"objectRef": "56b4bc31-e76d-4242-9a3b-fb0a9f62b0f5-004a2c7d", "label": "BoxСтена : BoxСтена [4861053]"},
        {"objectRef": "no-id", "label": "free text"},
        "not a state"]})
    assert app_module.native_ids_from_state(state) == {"56b4bc31-e76d-4242-9a3b-fb0a9f62b0f5-004a2c7d": "4861053"}
    assert app_module.native_ids_from_state(None) == {} and app_module.native_ids_from_state("{bad") == {}
    report = ["document: Likino_KR_GP_R24_CH10-dg-openings", "boxes: 313"]
    assert app_module.source_model_of(report) == "Likino_KR_GP_R24_CH10-dg-openings"
    assert app_module.source_model_of(["boxes: 1"]) is None


def test_a_published_check_records_the_source_model_on_its_runs(monkeypatch):
    import app as app_module
    import gh_bridge

    monkeypatch.setattr(gh_bridge, "run_property_check", lambda params: {
        "finished": True, "send": True, "clear": False, "paint": True,
        "status": {"boxes": 2, "violations": [], "validationRunId": [""], "messages": [], "ruleNames": ["R1"],
                   "calculatorReport": ["document: Likino", "boxes: 2"]}})
    monkeypatch.setattr(app_module, "read_many", lambda q, p=None: [{"runId": "VR-1"}])
    writes = []
    monkeypatch.setattr(app_module, "write_query", lambda q, p=None: writes.append(p))

    class NoThread:
        def __init__(self, target, args, daemon):
            pass

        def start(self):
            pass

    monkeypatch.setattr(app_module.threading, "Thread", NoThread)
    app_module.post_property_check_run(app_module.PropertyCheckRunRequest(project="p", refresh=False), request=None)
    assert {"project": "p", "runIds": ["VR-1"], "model": "Likino"} in writes


# --------------------------------------------------------------------------------------------------------------
# Phase 1303-17 (DGOPN-05, D-54..D-60): resolution order, integrity, rejected-hash guard, company scope
# --------------------------------------------------------------------------------------------------------------

HEIGHT_RULES = {"R_H_V": "hasOpeningHeightMm"}
HEIGHT_IRI = DG + "hasOpeningHeightMm"


def _calculator(variant=1):
    """(function, source, sha256) of a contract-valid generated calculator; each variant is a different source."""
    import hashlib

    from property_calculator_llm import finalize

    name, source = finalize(GOOD_FUNCTION.replace("round(best, 1)", f"round(best, {variant})"))
    return name, source, hashlib.sha256(source.encode("utf-8")).hexdigest()


def _entry(variant=1, **over):
    name, source, digest = _calculator(variant)
    row = {"catalogueId": f"CC-{digest[:16]}", "propertyKey": "hasopeningheightmm",
           "propertyName": "hasOpeningHeightMm", "sha256": digest, "source": source, "function": name,
           "unit": "mm", "meaning": "tallest opening height", "contractVersion": None, "provider": "fake",
           "model": "m", "status": "active"}
    row.update(over)
    return row


def _stored_row(variant=1, **over):
    name, source, digest = _calculator(variant)
    row = {"dataPropertyIri": HEIGHT_IRI, "calculator": f"generated:{digest[:10]}", "origin": "generated",
           "params": {}, "function": name, "source": source, "sha256": digest, "provider": "fake", "model": "m",
           "unit": None, "explanation": None, "catalogueId": None, "reviewStatus": "pending"}
    row.update(over)
    return row


def _height_rules():
    return ps.rules_from_rows(_rows(HEIGHT_RULES))


def _generator(variant, calls):
    def generator(dp, rules, box):
        calls.append(dp)
        name, source, _digest = _calculator(variant)
        return {"status": "ok", "function": name, "source": source, "unit": "mm", "explanation": "tallest",
                "provider": "fake", "model": "m"}

    return generator


def _no_generator(*_a):
    pytest.fail("the generator must not be called")


def test_shared_entry_binds_before_stored_without_a_generator_call(catalogue):
    entry = _entry(1, contractVersion=catalogue["version"])
    res = ps.resolve(_height_rules(), catalogue, stored={HEIGHT_IRI: _stored_row(2)}, generator=_no_generator,
                     shared={"hasopeningheightmm": entry}, blocked={})
    bound = res["resolved"][0]
    assert bound["resolvedBy"] == "shared" and bound["origin"] == "generated"
    assert bound["catalogueId"] == entry["catalogueId"] and bound["reviewStatus"] == "confirmed"
    assert bound["sha256"] == entry["sha256"] and bound["unit"] == "mm" and bound["new"] is True
    assert res["warnings"] == [] and res["unsupported"] == []


def test_shared_file_catalogue_alias_binds_before_a_shared_entry(catalogue):
    rules = ps.rules_from_rows(_rows({"R_B_V": "hasBeamIntersectionCount"}))
    entry = _entry(1, propertyKey="hasbeamintersectioncount", propertyName="hasBeamIntersectionCount",
                   contractVersion=catalogue["version"])
    res = ps.resolve(rules, catalogue, shared={"hasbeamintersectioncount": entry}, generator=_no_generator)
    assert res["resolved"][0]["resolvedBy"] == "alias" and res["resolved"][0]["origin"] == "catalogue"


def test_shared_hit_reports_not_new_when_the_project_holds_the_same_source(catalogue):
    entry = _entry(1, contractVersion=catalogue["version"])
    held = _stored_row(1, catalogueId=entry["catalogueId"], reviewStatus="confirmed")
    res = ps.resolve(_height_rules(), catalogue, stored={HEIGHT_IRI: held}, shared={"hasopeningheightmm": entry})
    assert res["resolved"][0]["resolvedBy"] == "shared" and res["resolved"][0]["new"] is False


def test_shared_contract_version_mismatch_warns_but_still_binds(catalogue):
    entry = _entry(1, contractVersion="older-contract")
    res = ps.resolve(_height_rules(), catalogue, shared={"hasopeningheightmm": entry})
    assert res["resolved"][0]["resolvedBy"] == "shared"
    assert len(res["warnings"]) == 1 and "older-contract" in res["warnings"][0]


def test_shared_generate_store_saves_the_project_copy_once_with_the_catalogue_id(catalogue, monkeypatch):
    import property_calculator_store as store

    monkeypatch.setattr(store, "company_of", lambda project: "ACME")
    entry = _entry(1, contractVersion=catalogue["version"])
    rows = _rows(HEIGHT_RULES)
    session = _Session(rows, catalogue=[entry])
    first = ps.generate(session, PROJECT, None, catalogue=catalogue, generator=_no_generator, store=True,
                        actor="owner")
    assert first["resolved"][0]["resolvedBy"] == "shared" and first["warnings"] == []
    assert len(session.saved) == 1 and session.saved[0]["catalogueId"] == entry["catalogueId"]
    assert session.saved[0]["sha256"] == entry["sha256"]
    # the next generation finds the copy (same sha256, same catalogue id): nothing is saved again
    held = {k: v for k, v in _stored_row(1, catalogueId=entry["catalogueId"], reviewStatus="confirmed").items()
            if k != "params"}
    held["paramsJson"] = "{}"  # the row as Neo4j returns it; load_active parses it
    again_session = _Session(rows, stored=[held], catalogue=[entry])
    again = ps.generate(again_session, PROJECT, None, catalogue=catalogue, generator=_no_generator, store=True)
    assert again["resolved"][0]["resolvedBy"] == "shared" and again_session.saved == []
    assert [e for e in again["resolved"] if "new" in e] == []


def test_shared_generate_without_a_company_runs_no_catalogue_statement(catalogue, monkeypatch):
    import property_calculator_store as store

    monkeypatch.setattr(store, "company_of", lambda project: None)
    entry = _entry(1, contractVersion=catalogue["version"])
    rows = _rows({"R_B_V": "hasBeamIntersectionCount"}) + _rows(HEIGHT_RULES)
    session = _Session(rows, catalogue=[entry])
    out = ps.generate(session, PROJECT, None, catalogue=catalogue)
    assert not any("CatalogueCalculator" in q for q, _p in session.calls)
    assert [r["dataPropertyLabel"] for r in out["resolved"]] == ["hasBeamIntersectionCount"]
    assert [u["dataPropertyLabel"] for u in out["unsupported"]] == ["hasOpeningHeightMm"]
    assert session.calls[0][1] == {"project": PROJECT, "ruleIds": None}  # load_rules stays the first session call


def test_shared_generate_reads_the_catalogue_of_the_projects_company_only(catalogue, monkeypatch):
    import property_calculator_store as store

    monkeypatch.setattr(store, "company_of", lambda project: "ACME")
    session = _Session(_rows({"R_B_V": "hasBeamIntersectionCount"}), catalogue=[])
    ps.generate(session, PROJECT, None, catalogue=catalogue)
    queries = [(q, p) for q, p in session.calls if "CatalogueCalculator" in q]
    assert len(queries) == 1 and queries[0][1] == {"company": "ACME"}
    assert "company:$company" in queries[0][0]
    assert not any("CatalogueCalculator" in q for q, _p in session.calls[:1])


def test_shared_ensure_rule_classes_binds_the_company_entry_without_the_llm(catalogue, monkeypatch):
    import property_calculator_store as store

    monkeypatch.setattr(store, "company_of", lambda project: "ACME")
    entry = _entry(1, contractVersion=catalogue["version"])
    session = _Session(_rows(HEIGHT_RULES), catalogue=[entry])
    out = ps.ensure_rule_classes(session, PROJECT, catalogue=catalogue, generator=_no_generator, actor="owner")
    assert [e["dataPropertyIri"] for e in out["linked"]] == [HEIGHT_IRI] and out["unsupported"] == []
    assert out["warnings"] == [] and session.saved[0]["catalogueId"] == entry["catalogueId"]


def test_integrity_failing_shared_entry_is_skipped_with_a_warning_and_never_assembled(catalogue):
    entry = _entry(1, contractVersion=catalogue["version"])
    entry["source"] = entry["source"].replace("round(best, 1)", "round(best, 9)")  # no longer matches its sha256
    res = ps.resolve(_height_rules(), catalogue, shared={"hasopeningheightmm": entry},
                     generator=lambda *a: {"status": "invalid", "error": "x"})
    assert res["resolved"] == [] and len(res["warnings"]) == 1
    assert "skipped" in res["warnings"][0] and "sha256" in res["warnings"][0]
    with pytest.raises(ps.PropertyScriptError):
        ps.assemble(PROJECT, res, catalogue)


def test_integrity_failing_shared_entry_with_forbidden_code_never_binds(catalogue):
    import hashlib

    source = "def calc_gen_0123456789(ctx, box, params):\n    import os\n    return 1\n"
    entry = _entry(1, contractVersion=catalogue["version"], source=source, function="calc_gen_0123456789",
                   sha256=hashlib.sha256(source.encode("utf-8")).hexdigest())
    res = ps.resolve(_height_rules(), catalogue, shared={"hasopeningheightmm": entry})
    assert res["resolved"] == [] and "contract" in res["warnings"][0]


def test_integrity_failing_stored_calculator_is_skipped_and_the_generator_is_asked(catalogue):
    tampered = _stored_row(1)
    tampered["source"] = tampered["source"] + "\n# tampered\n"
    calls = []
    res = ps.resolve(_height_rules(), catalogue, stored={HEIGHT_IRI: tampered}, generator=_generator(2, calls))
    assert len(calls) == 1 and res["resolved"][0]["resolvedBy"] == "llm"
    assert res["resolved"][0]["sha256"] != tampered["sha256"]
    assert "stored calculator" in res["warnings"][0] and "skipped" in res["warnings"][0]


def test_integrity_valid_stored_calculator_binds_with_review_fields(catalogue):
    record = _stored_row(1, unit="mm", explanation="tallest", catalogueId="CC-1", reviewStatus="confirmed")
    res = ps.resolve(_height_rules(), catalogue, stored={HEIGHT_IRI: record}, generator=_no_generator)
    bound = res["resolved"][0]
    assert bound["resolvedBy"] == "stored" and bound["unit"] == "mm" and bound["explanation"] == "tallest"
    assert bound["catalogueId"] == "CC-1" and bound["reviewStatus"] == "confirmed" and res["warnings"] == []


def test_generated_binding_carries_unit_explanation_and_pending_review(catalogue):
    calls = []
    res = ps.resolve(_height_rules(), catalogue, generator=_generator(1, calls))
    bound = res["resolved"][0]
    assert bound["resolvedBy"] == "llm" and bound["unit"] == "mm" and bound["explanation"] == "tallest"
    assert bound["reviewStatus"] == "pending" and bound["new"] is True


def test_reject_blocks_the_property_without_a_generator_call(catalogue):
    _n, _s, digest = _calculator(1)
    blocked = {HEIGHT_IRI: {"status": "rejected", "sha256": digest, "sha256s": [digest], "reason": "wrong unit",
                            "by": "u", "regenerate": False}}
    res = ps.resolve(_height_rules(), catalogue, generator=_no_generator, blocked=blocked)
    assert res["resolved"] == []
    assert res["unsupported"][0]["reason"].startswith("rejected") and "wrong unit" in res["unsupported"][0]["reason"]


def test_reject_with_regenerate_calls_the_generator_once_with_the_reason(catalogue):
    _n, _s, digest = _calculator(1)
    blocked = {HEIGHT_IRI: {"status": "rejected", "sha256": digest, "sha256s": [digest], "reason": "wrong unit",
                            "by": "u", "regenerate": True}}
    calls = []
    res = ps.resolve(_height_rules(), catalogue, generator=_generator(2, calls), blocked=blocked)
    assert len(calls) == 1 and calls[0]["rejectedReason"] == "wrong unit"
    assert res["resolved"][0]["resolvedBy"] == "llm" and res["resolved"][0]["reviewStatus"] == "pending"


def test_reject_of_a_regenerated_source_the_project_already_rejected_is_unsupported(catalogue):
    _n, _s, digest = _calculator(1)
    blocked = {HEIGHT_IRI: {"status": "rejected", "sha256": digest, "sha256s": [digest], "reason": "r",
                            "by": "u", "regenerate": True}}
    res = ps.resolve(_height_rules(), catalogue, generator=_generator(1, []), blocked=blocked)
    assert res["resolved"] == []
    assert res["unsupported"][0]["reason"] == "regenerated source was already rejected"


def test_reject_shared_entry_the_project_rejected_is_skipped_with_a_warning(catalogue):
    entry = _entry(1, contractVersion=catalogue["version"])
    blocked = {HEIGHT_IRI: {"status": "active", "sha256": "other", "sha256s": [entry["sha256"]], "reason": None,
                            "by": None, "regenerate": False}}
    res = ps.resolve(_height_rules(), catalogue, shared={"hasopeningheightmm": entry}, blocked=blocked)
    assert res["resolved"] == [] and "rejected" in res["warnings"][0]


def test_reject_stored_source_the_project_rejected_is_skipped_with_a_warning(catalogue):
    record = _stored_row(1)
    blocked = {HEIGHT_IRI: {"status": "active", "sha256": record["sha256"], "sha256s": [record["sha256"]],
                            "reason": None, "by": None, "regenerate": False}}
    res = ps.resolve(_height_rules(), catalogue, stored={HEIGHT_IRI: record}, blocked=blocked)
    assert res["resolved"] == [] and "rejected" in res["warnings"][0]


def test_reject_cycle_regenerated_source_already_rejected_is_unsupported(catalogue):
    """Reject A, regenerate B, reject B, regenerate A ends unsupported; B is never revived through the active row."""
    _na, _sa, hash_a = _calculator(1)
    _nb, _sb, hash_b = _calculator(2)
    # 1. A rejected with regenerate: the generator's B binds as a pending candidate
    blocked = {HEIGHT_IRI: {"status": "rejected", "sha256": hash_a, "sha256s": [hash_a], "reason": "r",
                            "by": "u", "regenerate": True}}
    first = ps.resolve(_height_rules(), catalogue, generator=_generator(2, []), blocked=blocked)
    assert first["resolved"][0]["sha256"] == hash_b and first["resolved"][0]["reviewStatus"] == "pending"
    # 2. B rejected as well (A and B rejected, regenerate): a generator answering A is unsupported
    blocked = {HEIGHT_IRI: {"status": "rejected", "sha256": hash_b, "sha256s": sorted([hash_a, hash_b]),
                            "reason": "r", "by": "u", "regenerate": True}}
    second = ps.resolve(_height_rules(), catalogue, generator=_generator(1, []), blocked=blocked)
    assert second["resolved"] == []
    assert second["unsupported"][0]["reason"] == "regenerated source was already rejected"
    # 3. the row is active again holding a stored B that fails integrity, A is still rejected: A is not revived
    broken = _stored_row(2)
    broken["source"] = broken["source"] + "\n# tampered\n"
    blocked = {HEIGHT_IRI: {"status": "active", "sha256": hash_b, "sha256s": [hash_a], "reason": None,
                            "by": None, "regenerate": False}}
    third = ps.resolve(_height_rules(), catalogue, stored={HEIGHT_IRI: broken}, generator=_generator(1, []),
                       blocked=blocked)
    assert third["resolved"] == []
    assert third["unsupported"][0]["reason"] == "regenerated source was already rejected"
    assert any("skipped" in w for w in third["warnings"])


def test_retire_entry_absent_from_the_catalogue_does_not_bind_and_the_copy_stays_unsupported(catalogue):
    _n, _s, digest = _calculator(1)
    blocked = {HEIGHT_IRI: {"status": "retired", "sha256": digest, "sha256s": [], "reason": "retired from the "
                            "company catalogue: obsolete", "by": "o", "regenerate": False}}
    res = ps.resolve(_height_rules(), catalogue, shared={}, generator=_no_generator, blocked=blocked)
    assert res["resolved"] == []
    assert res["unsupported"][0]["reason"].startswith("retired")


def test_retired_entry_confirmed_again_binds_as_shared(catalogue):
    """D-59: after an owner confirms the retired entry again it is back in the catalogue and the copy is active."""
    import property_calculator_store as store

    entry = _entry(1, contractVersion=catalogue["version"])
    retired_state = {HEIGHT_IRI: {"status": "retired", "sha256": entry["sha256"], "sha256s": [], "reason": "r",
                                  "by": "o", "regenerate": False}}
    # a retired row's own hash is paused, not rejected
    assert store.rejected_source(retired_state, HEIGHT_IRI, entry["sha256"]) is False
    paused = ps.resolve(_height_rules(), catalogue, shared={}, generator=_no_generator, blocked=retired_state)
    assert paused["resolved"] == [] and paused["unsupported"][0]["reason"].startswith("retired")
    held = _stored_row(1, catalogueId=entry["catalogueId"], reviewStatus="confirmed")
    again = ps.resolve(_height_rules(), catalogue, stored={HEIGHT_IRI: held}, generator=_no_generator,
                       shared={"hasopeningheightmm": entry}, blocked={})
    assert again["resolved"][0]["resolvedBy"] == "shared" and again["unsupported"] == []
    assert again["resolved"][0]["new"] is False


def test_shared_save_refusal_becomes_a_warning(catalogue, monkeypatch):
    import property_calculator_store as store

    monkeypatch.setattr(store, "company_of", lambda project: None)
    monkeypatch.setattr(store, "save", lambda *a, **k: {"saved": False, "reason": "rejected source"})
    out = ps.generate(_Session(_rows(HEIGHT_RULES)), PROJECT, None, catalogue=catalogue,
                      generator=_generator(1, []), store=True)
    assert any("hasOpeningHeightMm" in w and "rejected source" in w for w in out["warnings"])
