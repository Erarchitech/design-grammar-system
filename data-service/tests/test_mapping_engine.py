"""Tests for the deterministic mapping engine (Phase 1303 MVP slice)."""

import json
import random
from pathlib import Path

import pytest

import mapping_engine as m
import mapping_fixtures as fx

RULES_APPROVED = Path(__file__).resolve().parents[2] / "test" / "v12-hexagonal-facade-01" / "rules-approved.json"
AT = "2026-10-18T09:00:00Z"


def _setup(synonyms=None):
    classes = fx.facade_classes(synonyms)
    constraints = m.constraints_from_rows(fx.facade_rule_rows())
    return classes, constraints


def _compute(descriptors, profiles=(), synonyms=None, **kw):
    classes, constraints = _setup(synonyms)
    return m.compute(descriptors, classes, constraints, profiles, rule_classes=fx.EXTRA_RULE_CLASSES, **kw)


def _question(result, qtype):
    return next(q for q in result["questions"] if q["type"] == qtype)


def _decide(result, descriptors, question, option_id, profiles=(), synonyms=None, platform="grasshopper"):
    classes, _ = _setup(synonyms)
    return m.decide(
        result, descriptors, question["questionId"], option_id, "owner", AT, classes, profiles=profiles, project="p", platform_default=platform
    )


def _learn_v1():
    """Cold start on V1, answer both questions; returns (descriptors, result, decided, profiles)."""
    d = fx.facade_v1_descriptors()
    r = _compute(d)
    decided, profiles = {}, []
    for q, opt in ((_question(r, "batch-assign"), "accept-all"), (_question(r, "mapping-or-design"), "class:ex:GroundFloorUnit")):
        out = _decide(r, d, q, opt, profiles)
        decided.update(out["decided"])
        profiles = m.merge_profiles(profiles, out["profiles"])
    r2 = _compute(d, profiles, decided=decided)
    return d, r2, decided, profiles


# 1 -------------------------------------------------------------------------


def test_constraints_from_rows_inverts_violation_pattern():
    cons = {(c.rule_id, c.class_local): c for c in m.constraints_from_rows(fx.facade_rule_rows())}
    c12 = cons[("R_HEX_HASVERTEXCOUNT_REQ_6_V", "HexagonalUnit")]
    assert (c12.prop_local, c12.op, c12.value) == ("hasVertexCount", "==", 6.0)
    c7 = cons[("R_GP_WIDTH_MIN_4.5_V", "GlassPanel")]
    assert (c7.prop_local, c7.op, c7.value) == ("hasWidthM", ">=", 4.5)
    c9 = cons[("R_HEX_HASGAPCOUNT_MAX_0_V", "HexagonalUnit")]
    assert (c9.op, c9.value) == ("<=", 0.0)
    bad = [
        {"ruleId": "R_X", "classIri": "ex:A", "propertyIri": "ex:p", "builtinIri": "swrlb:notEqual", "lex": "abc"},
        {"ruleId": "R_Y", "classIri": "ex:A", "propertyIri": "ex:p", "builtinIri": "swrlb:between", "lex": "1"},
        {"ruleId": None},
    ]
    assert m.constraints_from_rows(bad) == []


def test_rule_body_is_a_conjunction():
    """Live graph form of R9: `greaterThanOrEqual(?count, 0) ^ greaterThan(?count, 0)` is violated iff count > 0."""
    rows = [
        {"ruleId": "R_HEX_HASGAPCOUNT_MAX_0_V", "classIri": "ex:HexagonalUnit", "propertyIri": "ex:hasGapCount", "builtinIri": "swrlb:greaterThanOrEqual", "lex": "0"},
        {"ruleId": "R_HEX_HASGAPCOUNT_MAX_0_V", "classIri": "ex:HexagonalUnit", "propertyIri": "ex:hasGapCount", "builtinIri": "swrlb:greaterThan", "lex": "0"},
    ]
    cons = m.constraints_from_rows(rows)
    assert len(cons) == 2
    _, closed = m.ev_rules({"properties.hasGapCount": 0}, cons, m.CONFIG)
    _, open_ = m.ev_rules({"properties.hasGapCount": 1}, cons, m.CONFIG)
    assert {k: closed["HexagonalUnit"][k] for k in ("sat", "vio")} == {"sat": ["R_HEX_HASGAPCOUNT_MAX_0_V"], "vio": []}
    assert open_["HexagonalUnit"]["sat"] == [] and open_["HexagonalUnit"]["vio"][0][0] == "R_HEX_HASGAPCOUNT_MAX_0_V"


def test_constraints_from_swrl_plain_pattern():
    cons = m.constraints_from_swrl(
        "R_HEX_HASVERTEXCOUNT_REQ_6_V", "HexagonalUnit(?u) ^ hasVertexCount(?u, ?n) ^ swrlb:notEqual(?n, 6) -> violation(?u)"
    )
    assert [(c.class_local, c.prop_local, c.op, c.value) for c in cons] == [("HexagonalUnit", "hasVertexCount", "==", 6.0)]
    assert m.constraints_from_swrl("R_A1", "FacadeModule(?m) ^ hasUpperVertex(?m, ?v) -> PatternNode(?v)") == []


@pytest.mark.skipif(not RULES_APPROVED.exists(), reason="repo-root fixture not mounted")
def test_fixture_rules_match_rules_approved_json():
    data = json.loads(RULES_APPROVED.read_text(encoding="utf-8"))
    expected = {
        (r["graphRuleId"], r.get("graphClass") or r["class"], r.get("graphDataProperty") or r["dataProperty"], r["violationBuiltin"].split(":")[-1], float(r["threshold"]))
        for r in data["rules"]
    }
    actual = {(rid, cls, prop, b, float(lex)) for rid, cls, prop, b, lex in fx.FACADE_RULES}
    assert actual == expected


# 2 -------------------------------------------------------------------------


def test_cold_start_v1_two_questions():
    r = _compute(fx.facade_v1_descriptors())
    assert r["summary"]["openQuestions"] == 2
    assert r["summary"]["auto"] == 0 and r["summary"]["confirmed"] == 0
    types = sorted(q["type"] for q in r["questions"])
    assert types == ["batch-assign", "mapping-or-design"]
    batch = _question(r, "batch-assign")
    groups = {g["groupId"]: g for g in r["groups"]}
    tops = sorted((groups[g]["candidates"][0]["label"], groups[g]["size"]) for g in batch["groupIds"])
    assert tops == [("BottomTriangularPanel", 125), ("Facade", 1), ("GlassPanel", 125), ("HexagonalUnit", 100)]
    mod = _question(r, "mapping-or-design")
    assert groups[mod["groupIds"][0]]["size"] == 25
    options = [o["optionId"] for o in mod["options"]]
    assert "class:ex:GroundFloorUnit" in options and "design-error:ex:HexagonalUnit" in options
    effects = {(c["optionId"], x["ruleId"], x["effect"], x["count"]) for c in mod["consequences"] for x in c["rules"]}
    assert ("design-error:ex:HexagonalUnit", "R_HEX_HASVERTEXCOUNT_REQ_6_V", "violated", 25) in effects
    assert ("class:ex:GroundFloorUnit", "R_GF_HASVERTEXCOUNT_REQ_5_V", "passes", 25) in effects
    assert "Is the mapping wrong or the design?" in mod["text"]
    assert "Где ошибка — в меппинге или в проекте?" in mod["textRu"]
    assert all(not e["roles"] or e["roles"][0]["state"] == "suggested" for e in r["elements"])


def test_mapping_or_design_text_explains_each_option():
    # Owner 2026-10-18: "mapping error or design error?" was unclear. The text names the
    # evidence behind the conflicting class and says what each button (quoted with its UI
    # label) does to the elements.
    r = _compute(fx.facade_v1_descriptors())
    mod = _question(r, "mapping-or-design")
    ru, en = mod["textRu"], mod["text"]
    assert ru.startswith("25 элементов из HU (5 вершин). Свидетельства за HexagonalUnit: названия на холсте; но как HexagonalUnit: R_HEX_HASVERTEXCOUNT_REQ_6_V нарушено ×25")
    assert "«GroundFloorUnit»: ошибся меппинг; элементы получат класс GroundFloorUnit." in ru
    assert (
        "«HexagonalUnit — нарушения правил — ошибки проекта»: класс верен, ошибся проект; элементы получат класс HexagonalUnit, "
        "а нарушения R_HEX_HASVERTEXCOUNT_REQ_6_V останутся в отчёте VALIDATOR и больше не вызовут этот вопрос." in ru
    )
    assert "«Обе роли»: элементы получат оба класса и будут проверяться правилами обоих." in ru
    assert "«Ни один из вариантов»: элементы останутся без класса DG и не будут проверяться." in ru
    assert ru.endswith("Ответ запомнится как профиль для похожих элементов.")
    assert en.startswith("25 elements from HU (5 vertices). Evidence for HexagonalUnit: canvas names; but as HexagonalUnit: R_HEX_HASVERTEXCOUNT_REQ_6_V violated ×25")
    assert '"GroundFloorUnit": the mapping is wrong; the elements get GroundFloorUnit.' in en
    assert (
        '"HexagonalUnit — rule violations are design errors": the class is right and the design is wrong; the elements get HexagonalUnit, '
        "and the violations of R_HEX_HASVERTEXCOUNT_REQ_6_V stay in the VALIDATOR report without raising this question again." in en
    )
    assert '"Both roles": the elements get both classes and are checked by the rules of both.' in en
    assert '"None of these": the elements get no DG class and are not checked.' in en
    assert en.endswith("The answer is remembered as a profile for similar elements.")
    # Every offered option is explained, and only offered ones.
    assert [o["optionId"] for o in mod["options"]] == ["class:ex:GroundFloorUnit", "design-error:ex:HexagonalUnit", "both", "none"]


# 3 -------------------------------------------------------------------------


def test_decisions_confirm_all_and_learn_profiles():
    d, r2, decided, profiles = _learn_v1()
    assert r2["summary"]["confirmed"] == 376 and r2["summary"]["openQuestions"] == 0
    assert len(profiles) == 5 and all(p["source"] == "learned" for p in profiles)
    pent = next(p for p in profiles if p["roles"] == ["ex:GroundFloorUnit"])
    assert pent["selector"].get("geometry.vertexCount") == 5
    assert not any("nativeId" in k for p in profiles for k in p["selector"])
    # A fresh session on the same geometry is mapped by profiles alone.
    fresh = _compute(d, profiles)
    assert fresh["summary"]["auto"] == 376 and fresh["summary"]["openQuestions"] == 0
    metrics = m.evaluate_against_gold(fresh["elements"], fx.gold_labels(d))
    for cls in ("HexagonalUnit", "GroundFloorUnit", "GlassPanel", "BottomTriangularPanel", "Facade"):
        assert metrics["perClass"][cls]["precision"] == 1.0
        assert metrics["perClass"][cls]["recall"] == 1.0


# 4 -------------------------------------------------------------------------


def test_v2_reuses_profiles_with_design_signals():
    _, _, _, profiles = _learn_v1()
    d2 = fx.facade_v2_descriptors()
    r = _compute(d2, profiles)
    assert r["summary"]["openQuestions"] == 0 and r["summary"]["auto"] == 376
    width = [e for e in r["elements"] if any(s["ruleId"] == "R_GP_WIDTH_MIN_4.5_V" for s in e["designSignals"])]
    aspect = [e for e in r["elements"] if any(s["ruleId"] == "R_GLASS_ASPECTRATIO_MAX_6_V" for s in e["designSignals"])]
    assert len(width) == 57 and len(aspect) == 12
    assert all(e["roles"][0]["classIri"] == "ex:GlassPanel" and e["state"] == "auto" for e in width + aspect)


# 5 -------------------------------------------------------------------------


def test_determinism_and_order_independence():
    d = fx.facade_v1_descriptors()
    a = m.canonical_json(_compute(d))
    b = m.canonical_json(_compute(list(d)))
    shuffled = list(d)
    random.Random(7).shuffle(shuffled)
    c = m.canonical_json(_compute(shuffled))
    assert a == b == c


# 6 -------------------------------------------------------------------------


def _window_wall(disjoint=()):
    classes = [m.ClassInfo("ex:Window", "Window", ("glazed",)), m.ClassInfo("ex:Wall", "Wall", ("glazed",))]
    d = [{"nativeId": f"e{i}", "source": "Glazed facade element"} for i in range(4)]
    r = m.compute(d, classes, [], disjoint=disjoint)
    return classes, d, r


def test_window_and_wall_both_roles():
    classes, d, r = _window_wall()
    q = r["questions"][0]
    assert q["type"] == "disambiguate"
    assert any(o["optionId"] == "both" for o in q["options"])
    out = m.decide(r, d, q["questionId"], "both", "owner", AT, classes)
    r2 = m.compute(d, classes, [], out["profiles"], decided=out["decided"])
    roles = {tuple(sorted(x["classIri"] for x in e["roles"])) for e in r2["elements"]}
    assert roles == {("ex:Wall", "ex:Window")}
    fresh = m.compute([{"nativeId": "n1", "source": "Glazed facade element"}], classes, [], out["profiles"])
    assert fresh["elements"][0]["state"] == "auto" and len(fresh["elements"][0]["roles"]) == 2


def test_window_and_wall_disjoint_blocks_both():
    classes, d, r = _window_wall(disjoint=[("ex:Window", "ex:Wall")])
    q = r["questions"][0]
    assert not any(o["optionId"] == "both" for o in q["options"])
    assert r["summary"]["ambiguous"] == 4
    out = m.decide(r, d, q["questionId"], "class:ex:Window", "owner", AT, classes)
    r2 = m.compute(d, classes, [], out["profiles"], disjoint=[("ex:Window", "ex:Wall")], decided=out["decided"])
    assert {e["roles"][0]["classIri"] for e in r2["elements"]} == {"ex:Window"}


# 7 -------------------------------------------------------------------------


def test_revit_like_population_and_names():
    _, v1_confirmed, _, _ = _learn_v1()
    populations = m.populations_of(v1_confirmed)
    d = fx.revit_like_descriptors("r1")
    r = _compute(d, synonyms=fx.REVIT_SYNONYMS, populations=populations, platform_default="revit")
    groups = {g["groupId"]: g for g in r["groups"]}
    assert len(groups) == 5
    assert r["summary"]["openQuestions"] <= 5
    # Category and IFC carry no class-discriminating evidence.
    for g in groups.values():
        for c in g["candidates"]:
            assert not any(e["kind"] == "ifc" for e in c["evidence"])
            assert not any("generic" in e["detail"] or "models" in e["detail"] for e in c["evidence"])
    gold = fx.gold_labels(d)
    by_family = {}
    for e in r["elements"]:
        by_family.setdefault(e["nativeId"].split("-")[1], groups[e["groupId"]])
    hex_group = by_family["Facade_Module_Hex"]
    hex_q = next(q for q in r["questions"] if hex_group["groupId"] in q["groupIds"])
    assert hex_q["type"] == "disambiguate"
    both = next(o for o in hex_q["options"] if o["optionId"] == "both")
    assert both["roles"] == ["ex:FacadeModule", "ex:HexagonalUnit"]
    # Answer every question with gold (both roles for the hex modules).
    decided, profiles = {}, []
    for q in r["questions"]:
        g = groups[q["groupIds"][0]]
        family = next(e["nativeId"].split("-")[1] for e in r["elements"] if e["groupId"] in q["groupIds"])
        if q["type"] == "batch-assign":
            opt = "accept-all"
        elif family == "Facade_Module_Hex":
            opt = "both"
        else:
            target = next(c for f, _, c in fx.REVIT_FAMILIES if f == family)
            opt = f"class:ex:{target}"
            assert any(o["optionId"] == opt for o in q["options"]), (family, [o["optionId"] for o in q["options"]])
        out = _decide(r, d, q, opt, profiles, fx.REVIT_SYNONYMS, platform="revit")
        decided.update(out["decided"])
        profiles = m.merge_profiles(profiles, out["profiles"])
    d2 = fx.revit_like_descriptors("r2")
    r2 = _compute(d2, profiles, synonyms=fx.REVIT_SYNONYMS, populations=populations, platform_default="revit")
    assert r2["summary"]["openQuestions"] == 0 and r2["summary"]["auto"] == len(d2)
    gold2 = fx.gold_labels(d2)
    for nid in gold2:
        if "Facade_Module_Hex" in nid:
            gold2[nid] = {"HexagonalUnit", "FacadeModule"}
    metrics = m.evaluate_against_gold(r2["elements"], gold2)
    assert metrics["overall"]["precision"] == 1.0 and metrics["overall"]["recall"] == 1.0


# 7b — population evidence per applied group, not per class (D-49) -----------
#
# Live session ms-56907a90d11f (2026-10-18): confirmed/auto counts per GH stream.
# Per class this collapsed to BottomTriangularPanel 250, GlassPanel 125,
# GroundFloorUnit 26, HexagonalUnit 100, Facade 1, so a 125 group of triangles
# was given «GlassPanel» and the 25 ground-floor modules nothing.
LIVE_STREAMS = (
    ("Panels A", "BottomTriangularPanel", 125),
    ("Panels C", "BottomTriangularPanel", 125),
    ("Panels B", "GlassPanel", 125),
    ("5-Module contours", "GroundFloorUnit", 25),
    ("Basement contour", "GroundFloorUnit", 1),
    ("6-Module contours", "HexagonalUnit", 100),
    ("bbox F", "Facade", 1),
)

LIVE_POPULATIONS = {
    "BottomTriangularPanel": [125, 125],
    "Facade": [1],
    "GlassPanel": [125],
    "GroundFloorUnit": [1, 25],
    "HexagonalUnit": [100],
}


def _live_result():
    """The live result shape: `stream` carries the GH source component id."""
    elements = []
    for stream, cls, count in LIVE_STREAMS:
        for i in range(count):
            elements.append(
                {
                    "nativeId": f"{stream}/{i}",
                    "groupId": f"G-{stream}",
                    "state": "confirmed",
                    "stream": stream,
                    "roles": [{"classIri": f"ex:{cls}", "label": cls, "state": "confirmed", "source": "human", "confidence": 1.0}],
                }
            )
    return {"elements": elements}


def _known():
    return {c.local for c in _setup()[0]}


def test_populations_of_counts_applied_groups_not_classes():
    assert m.populations_of(_live_result()) == LIVE_POPULATIONS
    # Without `stream` the base group is the unit; only confirmed/auto elements count.
    result = {
        "elements": [
            {"groupId": "G-a", "state": "confirmed", "roles": [{"classIri": "ex:GlassPanel"}]},
            {"groupId": "G-a", "state": "auto", "roles": [{"classIri": "ex:GlassPanel"}]},
            {"groupId": "G-a", "state": "suggested", "roles": [{"classIri": "ex:GlassPanel"}]},
            {"groupId": "G-b", "state": "confirmed", "roles": [{"classIri": "ex:GlassPanel"}, {"classIri": "ex:Facade"}]},
            {"groupId": "G-c", "state": "unmapped", "roles": []},
        ]
    }
    assert m.populations_of(result) == {"Facade": [1], "GlassPanel": [1, 2]}


def test_population_evidence_only_for_an_unambiguous_group_size():
    populations, known = m.populations_of(_live_result()), _known()
    # 125 is Panels A/C (triangles) and Panels B (glass): no evidence either way.
    assert m.ev_population(125, populations, known, m.CONFIG) == []
    # 1 is the basement contour and the bbox: ambiguous as well.
    assert m.ev_population(1, populations, known, m.CONFIG) == []
    [gfu] = m.ev_population(25, populations, known, m.CONFIG)
    assert (gfu.class_local, gfu.kind, gfu.weight) == ("GroundFloorUnit", "population", m.CONFIG["w_population"])
    assert gfu.detail == "group size 25 equals a confirmed group of GroundFloorUnit"
    [hu] = m.ev_population(100, populations, known, m.CONFIG)
    assert hu.class_local == "HexagonalUnit" and hu.detail == "group size 100 equals a confirmed group of HexagonalUnit"
    # A size no confirmed group has gives nothing.
    assert m.ev_population(26, populations, known, m.CONFIG) == []


def test_population_evidence_accepts_the_old_class_shape():
    known = _known()
    [gp] = m.ev_population(125, {"GlassPanel": 125}, known, m.CONFIG)
    assert gp.class_local == "GlassPanel" and gp.detail == "group size 125 equals a confirmed group of GlassPanel"
    # Absence and ambiguity give nothing, exactly as in the new shape.
    assert m.ev_population(1, {"GlassPanel": 125}, known, m.CONFIG) == []
    assert m.ev_population(125, {"Nope": 125}, known, m.CONFIG) == []
    assert m.ev_population(125, {"GlassPanel": 125, "Facade": 125}, known, m.CONFIG) == []
    # Malformed values are skipped, never raised on.
    assert m.ev_population(125, {"GlassPanel": "abc", "Facade": None}, known, m.CONFIG) == []
    assert m.ev_population(125, {"GlassPanel": {"n": 125}}, known, m.CONFIG) == []
    assert m.ev_population(125, {"GlassPanel": [125, "abc"], "Facade": 125}, known, m.CONFIG) == []
    [gp2] = m.ev_population(125, {"GlassPanel": [125, "abc"]}, known, m.CONFIG)
    assert gp2.class_local == "GlassPanel"


def test_compute_takes_population_evidence_from_group_sizes():
    """A 125 group gets nothing, 25 gets GroundFloorUnit, 26 nothing (the live bug)."""
    populations = m.populations_of(_live_result())
    pent = {"geometry": {"kind": "curve", "vertexCount": 5}, "properties": {"hasVertexCount": 5, "hasGapCount": 0}}

    def population_evidence(size):
        r = _compute([dict(pent, nativeId=f"n{i}") for i in range(size)], populations=populations, platform_default="revit")
        [group] = r["groups"]
        assert group["size"] == size
        return [(c["label"], e["detail"]) for c in group["candidates"] for e in c["evidence"] if e["kind"] == "population"]

    assert population_evidence(125) == []
    assert population_evidence(26) == []
    assert population_evidence(25) == [("GroundFloorUnit", "group size 25 equals a confirmed group of GroundFloorUnit")]


def test_population_counts_and_evidence_are_deterministic():
    result = _live_result()
    shuffled = list(result["elements"])
    random.Random(11).shuffle(shuffled)
    for _ in range(3):
        assert m.populations_of(result) == LIVE_POPULATIONS
        assert m.populations_of({"elements": list(shuffled)}) == LIVE_POPULATIONS
        assert m.ev_population(25, LIVE_POPULATIONS, _known(), m.CONFIG) == m.ev_population(25, LIVE_POPULATIONS, _known(), m.CONFIG)


def test_range_rules_do_not_outvote_a_signature():
    """A triangle that also satisfies all four GlassPanel range rules is not mapped to
    GlassPanel: the satisfied signature (hasVertexCount == 3) decides, GlassPanel stays a
    visible candidate (2026-10-18 tie-break); with a violated range rule it is
    BottomTriangularPanel as well."""
    base = {"source": "PA", "geometry": {"kind": "surface", "vertexCount": 3, "closed": True}}
    contested = dict(base, nativeId="t1", properties={"hasVertexCount": 3, "hasAspectRatio": 2.0, "hasPlanarityDeviationM": 0.0, "hasWidthM": 5.0})
    narrow = dict(base, nativeId="t2", properties={"hasVertexCount": 3, "hasAspectRatio": 2.0, "hasPlanarityDeviationM": 0.0, "hasWidthM": 4.2})
    r = _compute([contested, narrow])
    by_id = {e["nativeId"]: e for e in r["elements"]}
    groups = {g["groupId"]: g for g in r["groups"]}
    assert by_id["t1"]["state"] == "suggested"
    assert by_id["t1"]["roles"][0]["classIri"] == "ex:BottomTriangularPanel"
    labels = [c["label"] for c in groups[by_id["t1"]["groupId"]]["candidates"]]
    assert labels[0] == "BottomTriangularPanel" and "GlassPanel" in labels
    assert by_id["t2"]["state"] == "suggested"
    assert by_id["t2"]["roles"][0]["classIri"] == "ex:BottomTriangularPanel"


def test_named_class_keeps_the_question_against_a_signature():
    """The class an OBJECT STATE names (two words) is not overridden silently by the signature."""
    d = {"nativeId": "g1", "source": "join GU", "names": ["OS GroundFloorUnit: GlassPanel"],
         "geometry": {"kind": "curve", "vertexCount": 5, "closed": True},
         "properties": {"hasVertexCount": 5, "hasGapCount": 0}}
    r = _compute([d])
    assert r["elements"][0]["state"] == "ambiguous"
    assert [q["type"] for q in r["questions"]] == ["disambiguate"]


# 8 -------------------------------------------------------------------------


def test_profile_confidence_and_rejection():
    assert m.profile_confidence(1, 0) == round(5 / 6, 4) and m.profile_confidence(1, 0) >= 0.8
    assert m.profile_confidence(1, 1) == round(5 / 7, 4) and m.profile_confidence(1, 1) < 0.8
    _, _, _, profiles = _learn_v1()
    weakened = [dict(p, rejections=1) if p["roles"] == ["ex:GlassPanel"] else p for p in profiles]
    r = _compute(fx.facade_v1_descriptors(), weakened)
    glass = [e for e in r["elements"] if "PB" in e["nativeId"]]
    assert glass and all(e["state"] != "auto" for e in glass)


def test_contradicting_answer_rejects_profile():
    _, _, _, profiles = _learn_v1()
    # Pentagons answered as design errors of HexagonalUnit in a new session that still
    # carries the GroundFloorUnit profile: that profile gets a rejection.
    d = fx.facade_descriptors("facade-v9")
    r = _compute(d, [p for p in profiles if p["roles"] != ["ex:GroundFloorUnit"]])
    q = _question(r, "mapping-or-design")
    gfu_profile = next(p for p in profiles if p["roles"] == ["ex:GroundFloorUnit"])
    out = _decide(r, d, q, "design-error:ex:HexagonalUnit", profiles)
    updated = {p["profileId"]: p for p in out["profiles"]}
    assert updated[gfu_profile["profileId"]]["rejections"] == 1
    new = next(p for p in out["profiles"] if p["roles"] == ["ex:HexagonalUnit"] and p["acceptsViolations"])
    assert "R_HEX_HASVERTEXCOUNT_REQ_6_V" in new["acceptsViolations"]


# 9 -------------------------------------------------------------------------


def test_robust_inputs():
    empty = _compute([])
    assert empty["summary"]["total"] == 0 and empty["questions"] == []
    with pytest.raises(m.MappingInputError) as dup:
        _compute([{"nativeId": "a"}, {"nativeId": "a"}])
    assert dup.value.code == "MAPPING_INPUT_INVALID"
    with pytest.raises(m.MappingInputError) as big:
        _compute([{"nativeId": f"n{i}"} for i in range(5001)])
    assert big.value.code == "MAPPING_TOO_MANY_ELEMENTS"
    odd = _compute([{"nativeId": "x", "unknown": {"deep": [1, 2]}, "geometry": {"kind": "curve", "weird": [1]}}])
    assert odd["summary"]["unmapped"] == 1
    r = _compute(fx.facade_v1_descriptors())
    classes, _ = _setup()
    with pytest.raises(m.MappingInputError) as nq:
        m.decide(r, fx.facade_v1_descriptors(), "Q-missing", "none", "o", AT, classes)
    assert nq.value.code == "MAPPING_QUESTION_NOT_FOUND" and nq.value.status == 404
    with pytest.raises(m.MappingInputError) as no:
        m.decide(r, fx.facade_v1_descriptors(), r["questions"][0]["questionId"], "class:ex:Nope", "o", AT, classes)
    assert no.value.code == "MAPPING_OPTION_INVALID"


def test_apply_partition_after_decisions():
    _, r2, _, _ = _learn_v1()
    part = m.partition(r2)
    sizes = {k: len(v) for k, v in part["byClass"].items()}
    assert sizes == {"ex:BottomTriangularPanel": 125, "ex:Facade": 1, "ex:GlassPanel": 125, "ex:GroundFloorUnit": 25, "ex:HexagonalUnit": 100}
    assert part["applied"] == 376 and part["skipped"] == []


# 10 ------------------------------------------------------------------------


def test_no_adapter_names_and_pure_imports():
    src = (Path(m.__file__)).read_text(encoding="utf-8")
    assert "adapter" not in src.lower()
    for banned in ("import requests", "import httpx", "import urllib", "import random", "import time", "import datetime", "from datetime"):
        assert banned not in src


# 11 Canvas text, DG parameters and calculation outputs (owner clarifications 2026-10-18:
# group names, scribbles and component names take part; sliders are DG Parameters; datatype
# property values come from the outputs of calculation components) -----------------------


def _properties():
    """The fixture's rule properties, with the classes whose rules use them."""
    classes_of = {}
    for _rid, cls, prop, _b, _v in fx.FACADE_RULES:
        classes_of.setdefault(prop, set()).add(cls)
    return [m.PropertyInfo(f"ex:{p}", p, tuple(sorted(f"ex:{c}" for c in cs))) for p, cs in sorted(classes_of.items())]


def _sliders():
    out = [{"nativeId": f"gh:doc:slider:mw{i}", "name": f"Module Width F{i}", "names": ["Ширина соты"], "value": 7600} for i in range(1, 6)]
    out.append({"nativeId": "gh:doc:slider:tilt-even", "name": "Наклон чет сот", "names": ["Наклон сот"], "value": -1})
    out.append({"nativeId": "gh:doc:slider:ribs", "name": "КолВо ребер", "value": 5})
    return out


def _measures():
    return [
        {"nativeId": "gh:doc:measure:ar", "name": "AR", "component": "measure", "count": 125, "min": 1.4, "max": 5.5,
         "streams": [{"stream": "PB", "pathMatch": True, "agreement": {"hasAspectRatio": 1.0}}, {"stream": "PA", "pathMatch": True}]},
        {"nativeId": "gh:doc:measure:vc", "name": "VC", "component": "measure", "count": 125, "min": 3, "max": 3,
         "streams": [{"stream": "PA", "pathMatch": True, "agreement": {"hasVertexCount": 1.0}}]},
        {"nativeId": "gh:doc:measure:hg", "name": "HG", "component": "measure", "count": 100, "min": 0, "max": 0,
         "streams": [{"stream": "HU", "pathMatch": True, "constant": True, "agreement": {"hasGapCount": 1.0, "hasLevelOffsetM": 1.0}}]},
        {"nativeId": "gh:doc:measure:sum", "name": "Summary", "component": "measure", "count": 1, "streams": []},
    ]


def _stream_descriptors():
    d = fx.facade_v1_descriptors()
    for el in d:
        el["stream"] = el["nativeId"].split(":")[2]
    return d


def _full(params=None, measures=None, profiles=(), llm=None, **kw):
    return _compute(_stream_descriptors(), profiles, parameters=params, measures=measures, properties=_properties(), llm=llm, **kw)


def test_canvas_text_is_word_evidence_without_acronyms():
    classes, _ = _setup()
    feats = m.features({"nativeId": "x", "source": "Result", "names": ["Стеклянные панели", "Group B"]})
    ev = {e.class_local: e for e in m.ev_name(feats, classes, m.CONFIG)}
    assert ev["GlassPanel"].weight > ev["BottomTriangularPanel"].weight
    assert "canvas text" in ev["GlassPanel"].detail
    # A one-letter token from a group name is not an abbreviation of BottomTriangularPanel.
    assert "abbreviates" not in ev["BottomTriangularPanel"].detail
    assert m.CONTEXT_FIELD not in m.SELECTOR_FEATURES


def test_named_sliders_are_proposed_as_dg_parameters():
    r = _full(params=_sliders())
    assert {p["state"] for p in r["parameters"]} == {"suggested"}
    q = next(q for q in r["questions"] if q["type"] == "batch-parameters")
    assert len(q["parameterIds"]) == 7 and q["options"][0]["optionId"] == "accept-all"
    assert "PARAMETER STATE" in q["textRu"]
    # With an LLM proposal a slider that is not a design parameter stays out, with its reason.
    llm = {"parameters": {"gh:doc:slider:ribs": {"isParameter": False, "confidence": 0.9, "reason": "profile detail"}}}
    r2 = _full(params=_sliders(), llm=llm)
    ribs = next(p for p in r2["parameters"] if p["name"] == "КолВо ребер")
    assert ribs["state"] == "unmapped" and ribs["source"] == "llm" and ribs["reason"] == "profile detail"
    assert len(next(q for q in r2["questions"] if q["type"] == "batch-parameters")["parameterIds"]) == 6


def test_parameter_answers_are_learned():
    r = _full(params=_sliders())
    q = next(q for q in r["questions"] if q["type"] == "batch-parameters")
    out = _decide(r, _stream_descriptors(), q, "accept-all")
    assert len(out["decidedParameters"]) == 7
    assert all(v == [m.PARAMETER_ROLE] for v in out["decidedParameters"].values())
    r2 = _full(params=_sliders(), profiles=out["profiles"], decided_parameters=out["decidedParameters"])
    assert {p["state"] for p in r2["parameters"]} == {"confirmed"}
    r3 = _full(params=[{"nativeId": "gh:other:slider:mw6", "name": "Module Width F6"}], profiles=out["profiles"])
    assert r3["parameters"][0]["state"] == "auto"
    none = _decide(r, _stream_descriptors(), q, "none")
    r4 = _full(params=[{"nativeId": "gh:other:slider:mw7", "name": "Module Width F7"}], profiles=none["profiles"])
    assert r4["parameters"][0]["state"] == "unmapped"
    assert m.partition(r2)["parameters"][0]["name"].startswith(("Module Width", "Наклон", "КолВо"))


def test_llm_excluded_slider_is_shown_and_learned_with_the_batch():
    # Rehearsal 2026-10-18: the LLM held one of 14 sliders back as "not a DG parameter"; it was not
    # in the batch question, so no answer and no profile covered it, and every later variant asked
    # about it again (and paid an LLM call). The batch now shows it and accepting learns it.
    llm = {"parameters": {"gh:doc:slider:ribs": {"isParameter": False, "confidence": 0.9, "reason": "profile detail"}}}
    r = _full(params=_sliders(), llm=llm)
    q = next(q for q in r["questions"] if q["type"] == "batch-parameters")
    assert len(q["parameterIds"]) == 6 and q["heldParameterIds"] == ["gh:doc:slider:ribs"]
    held = next(i for i in q["items"] if i["itemId"] == "gh:doc:slider:ribs")
    assert held["proposal"] is None and held["state"] == "unmapped"
    assert "КолВо ребер" in q["textRu"] and "не параметр" in q["textRu"]
    assert q["titleRu"] == "6 слайдеров → параметры DG, 1 — не параметр (LLM)"
    out = _decide(r, _stream_descriptors(), q, "accept-all")
    assert out["decidedParameters"]["gh:doc:slider:ribs"] == []
    assert sum(1 for v in out["decidedParameters"].values() if v == [m.PARAMETER_ROLE]) == 6
    # Without an LLM proposal, the learned profiles map every slider: no question is left.
    later = _full(params=_sliders(), profiles=out["profiles"])
    assert not [x for x in later["questions"] if x["type"] == "batch-parameters"]
    ribs = next(p for p in later["parameters"] if p["name"] == "КолВо ребер")
    assert ribs["state"] == "unmapped" and ribs["source"] == "profile"


def test_answer_reactivates_a_retired_profile():
    # Rehearsal 2026-10-18: profiles are retired (state != active) for a cold restart; the same
    # answer gives the same profileId, and a human answer must switch it back on, or the
    # next variant is asked again instead of being mapped by the profile.
    d, _, _, profiles = _learn_v1()
    retired = [dict(p, state="retired") for p in profiles]
    cold = _compute(d, retired)
    assert sorted(q["type"] for q in cold["questions"]) == ["batch-assign", "mapping-or-design"]
    gfu = _decide(cold, d, _question(cold, "mapping-or-design"), "class:ex:GroundFloorUnit", retired)
    again = next(p for p in gfu["profiles"] if p["roles"] == ["ex:GroundFloorUnit"])
    assert again["profileId"] in {p["profileId"] for p in retired}
    assert again["state"] == "active" and again["confirmations"] == 2
    # Slider (item) profiles behave the same.
    r = _full(params=_sliders())
    q = next(q for q in r["questions"] if q["type"] == "batch-parameters")
    first = _decide(r, _stream_descriptors(), q, "accept-all")["profiles"]
    off = [dict(p, state="retired") for p in first]
    assert {p["state"] for p in _full(params=_sliders(), profiles=off)["parameters"]} == {"suggested"}
    on = _decide(r, _stream_descriptors(), q, "accept-all", off)["profiles"]
    assert {p["state"] for p in on} == {"active"} and {p["profileId"] for p in on} == {p["profileId"] for p in off}


def test_questions_carry_short_titles_and_one_item_per_component():
    # Owner 2026-10-18 (plan 1303-10): a proposal is a short line plus one row per proposed
    # canvas component (stream, calculation output, slider) with its GH InstanceGuid.
    hexes = {"HU": "a" * 32, "GU": "b" * 32, "PB": "c" * 32, "PA": "d" * 32, "F": "e" * 32}
    d = _stream_descriptors()
    for el in d:
        el["stream"] = hexes.get(el["stream"], el["stream"])
    measures = [dict(x, nativeId=f"gh:doc:measure:{i + 100:032x}") for i, x in enumerate(_measures())]
    for x in measures:
        for s in x["streams"]:
            s["stream"] = hexes.get(s["stream"], s["stream"])
    sliders = [dict(s, nativeId="gh:doc:slider:" + f"{i:032x}") for i, s in enumerate(_sliders())]
    r = _compute(d, parameters=sliders, measures=measures, properties=_properties())
    by_type = {q["type"]: q for q in r["questions"]}
    mod = by_type["mapping-or-design"]
    assert mod["titleRu"] == "HU · 25 элементов: GroundFloorUnit или HexagonalUnit?"
    assert mod["title"] == "HU · 25 elements: GroundFloorUnit or HexagonalUnit?"
    [item] = mod["items"]
    assert item["kind"] == "stream" and item["name"] == "HU" and item["componentId"] == "a" * 32 and item["count"] == 25
    assert item["proposal"]["label"] in ("GroundFloorUnit", "HexagonalUnit") and item["alternatives"]
    batch = by_type["batch-assign"]
    assert batch["titleRu"].startswith("4 группы, 351 элемент: принять предложенные классы")
    assert sorted(i["name"] for i in batch["items"]) == ["F", "HU", "PA", "PB"]
    assert {i["proposal"]["label"] for i in batch["items"]} == {"BottomTriangularPanel", "Facade", "GlassPanel", "HexagonalUnit"}
    bm = by_type["batch-measures"]
    assert all(i["kind"] == "measure" and len(i["componentId"]) == 32 for i in bm["items"])
    assert {i["name"] for i in bm["items"]} >= {"AR (measure)", "VC (measure)"}
    bp = by_type["batch-parameters"]
    assert bp["titleRu"] == "7 слайдеров → параметры DG"
    assert [i["kind"] for i in bp["items"]] == ["parameter"] * 7 and bp["items"][0]["count"] is None
    assert bp["items"][0]["componentId"] == "0" * 32 or len(bp["items"][0]["componentId"]) == 32
    # Element streams without a GH guid (Revit, synthetic) have no componentId.
    plain = _compute(fx.facade_v1_descriptors())
    assert all(i["componentId"] is None for q in plain["questions"] for i in q["items"])


def test_calculation_outputs_map_to_properties_by_values_and_names():
    r = _full(measures=_measures())
    by = {x["name"]: x for x in r["measures"]}
    assert by["AR"]["state"] == "suggested" and by["AR"]["property"]["label"] == "hasAspectRatio" and by["AR"]["stream"] == "PB"
    assert by["VC"]["state"] == "suggested" and by["VC"]["stream"] == "PA"
    # A constant column agrees with every all-zero property: asked, not guessed.
    assert by["HG"]["state"] == "ambiguous"
    assert by["Summary"]["state"] == "unmapped"
    batch = next(q for q in r["questions"] if q["type"] == "batch-measures")
    assert set(batch["measureIds"]) == {"gh:doc:measure:ar", "gh:doc:measure:vc"}
    single = next(q for q in r["questions"] if q["type"] == "map-measure")
    assert single["measureIds"] == ["gh:doc:measure:hg"] and single["options"][-1]["optionId"] == "none"
    # The LLM vote breaks the tie for HG.
    llm = {"measures": {"gh:doc:measure:hg": {"propertyIri": "ex:hasGapCount", "stream": "HU", "confidence": 0.9, "reason": "HG = hexagon gaps"}}}
    r2 = _full(measures=_measures(), llm=llm)
    hg = next(x for x in r2["measures"] if x["name"] == "HG")
    assert hg["state"] == "suggested" and hg["property"]["label"] == "hasGapCount"
    assert any("LLM" in e for e in hg["candidates"][0]["evidence"])


def test_llm_votes_for_element_classes():
    d = [{"nativeId": "s1", "stream": "S1", "source": "Result", "geometry": {"kind": "surface"}}]
    llm = {"objects": {"S1": {"classIri": "ex:GlassPanel", "confidence": 0.9, "reason": "glass panels of facade B"}}}
    r = _compute(d, llm=llm)
    group = r["groups"][0]
    top = group["candidates"][0]
    assert top["label"] == "GlassPanel" and any(e["kind"] == "llm" for e in top["evidence"])
    assert r["elements"][0]["stream"] == "S1"


def test_calculation_outputs_vote_for_their_stream_class():
    # 'bbox F.B': no class word, one solid; the output H on it carries hasTotalHeightM, which
    # only the Facade rule uses.
    d = [{"nativeId": "f1", "stream": "BB", "source": "bbox F.B", "geometry": {"kind": "solid"}, "properties": {"hasTotalHeightM": 114.275}}]
    h = [{"nativeId": "gh:doc:measure:h", "name": "H", "component": "C#", "count": 1, "min": 114.275, "max": 114.275,
          "streams": [{"stream": "BB", "pathMatch": True, "constant": True, "input": True, "agreement": {"hasTotalHeightM": 1.0}}]}]
    without = _compute(d, properties=_properties())
    assert not without["groups"][0]["candidates"]
    r = _compute(d, measures=h, properties=_properties())
    top = r["groups"][0]["candidates"][0]
    assert top["label"] == "Facade" and any(e["kind"] == "measure" and "output H" in e["detail"] for e in top["evidence"])
    # A property several classes' rules use shares the vote between them.
    known = {c.local for c in _setup()[0]}
    full = _full(measures=_measures())
    ev = m.measure_class_evidence(full["measures"], known, m.CONFIG)
    pa = {e.class_local: e.weight for e in ev["PA"]}
    assert set(pa) == {"BottomTriangularPanel", "GroundFloorUnit", "HexagonalUnit"} and len(set(pa.values())) == 1
    assert {e.class_local for e in ev["PB"]} == {"GlassPanel"}
    assert max(e.weight for es in ev.values() for e in es) <= m.CONFIG["w_measure_class_cap"]


def test_rule_bindings_pick_the_tied_stream_of_the_rule_class():
    # One script reads Panels A and Panels B; planarity is 0 on both. The glass rule binds to
    # Panels B; an output following other branches (bbox, basement) never binds to glass.
    _, constraints = _setup()
    result = {
        "elements": [
            {"state": "confirmed", "stream": "PB", "roles": [{"classIri": "ex:GlassPanel"}]},
            {"state": "confirmed", "stream": "PA", "roles": [{"classIri": "ex:BottomTriangularPanel"}]},
        ],
        "measures": [
            {"nativeId": "d1", "state": "confirmed", "property": {"iri": "ex:hasPlanarityDeviationM"}, "stream": None, "pathStreams": ["BB", "BS"]},
            {"nativeId": "pd", "state": "confirmed", "property": {"iri": "ex:hasPlanarityDeviationM"}, "stream": "PA",
             "streamOptions": ["PA", "PB"], "pathStreams": ["PA", "PB", "PC"]},
        ],
    }
    bound = {b["ruleId"]: (b["measureId"], b["stream"]) for b in m.rule_bindings(result, constraints)}
    assert bound["R_GLASS_PLANARITYDEVIATION_MAX_0p005_V"] == ("pd", "PB")
    # Measure rows carry the tie; an LLM stream the branches do not follow is ignored.
    pd = [{"nativeId": "gh:doc:measure:pd", "name": "PD", "component": "C#", "count": 125, "min": 0, "max": 0,
           "streams": [{"stream": s, "pathMatch": True, "input": s != "PC", "constant": True, "agreement": {"hasPlanarityDeviationM": 1.0}} for s in ("PA", "PB", "PC")]}]
    row = m.map_measures(pd, _properties())[0]
    assert row["streamOptions"] == ["PA", "PB"] and row["pathStreams"] == ["PA", "PB", "PC"]
    llm = {"measures": {"gh:doc:measure:pd": {"propertyIri": "ex:hasPlanarityDeviationM", "stream": "ZZ", "confidence": 0.9}}}
    assert m.map_measures(pd, _properties(), llm=llm)[0]["stream"] in ("PA", "PB")
    llm["measures"]["gh:doc:measure:pd"]["stream"] = "PB"
    assert m.map_measures(pd, _properties(), llm=llm)[0]["stream"] == "PB"


def test_rule_bindings_link_rule_class_property_and_output():
    d = _stream_descriptors()
    r = _full(measures=_measures())
    decided = {}
    profiles = []
    for qtype, opt in (("batch-assign", "accept-all"), ("mapping-or-design", "class:ex:GroundFloorUnit")):
        q = next(x for x in r["questions"] if x["type"] == qtype)
        out = _decide(r, d, q, opt, profiles)
        decided.update(out["decided"])
        profiles = m.merge_profiles(profiles, out["profiles"])
    q = next(x for x in r["questions"] if x["type"] == "batch-measures")
    out = _decide(r, d, q, "accept-all", profiles)
    r2 = _full(measures=_measures(), profiles=m.merge_profiles(profiles, out["profiles"]), decided=decided, decided_measures=out["decidedMeasures"])
    _, constraints = _setup()
    part = m.partition(r2, constraints)
    bound = {(b["ruleId"], b["measureId"], b["stream"]) for b in part["bindings"]}
    assert ("R_GLASS_ASPECTRATIO_MIN_1.3_V", "gh:doc:measure:ar", "PB") in bound
    assert ("R_GLASS_ASPECTRATIO_MAX_6_V", "gh:doc:measure:ar", "PB") in bound
    assert ("R_BTP_HASVERTEXCOUNT_REQ_3_V", "gh:doc:measure:vc", "PA") in bound
    assert all(b["classIri"].startswith("ex:") for b in part["bindings"])
    assert {x["name"] for x in part["measures"]} == {"AR", "VC"}


def test_parameters_and_measures_are_validated_and_deterministic():
    with pytest.raises(m.MappingInputError):
        _full(params=[{"nativeId": "a"}])
    with pytest.raises(m.MappingInputError):
        _full(measures=[{"nativeId": "a", "name": "x"}, {"nativeId": "a", "name": "y"}])
    a = _full(params=_sliders(), measures=_measures())
    b = _full(params=list(reversed(_sliders())), measures=list(reversed(_measures())))
    assert json.dumps(a, sort_keys=True, ensure_ascii=False) == json.dumps(b, sort_keys=True, ensure_ascii=False)
    assert m.name_stem("1 оффсет") == "оффсет" and m.name_stem("T4_Offset") == "offset"
    assert m.property_acronym(m.PropertyInfo("ex:hasPlanarityDeviationM", "hasPlanarityDeviationM")) == "pd"
