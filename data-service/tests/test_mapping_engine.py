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
    assert closed["HexagonalUnit"] == {"sat": ["R_HEX_HASGAPCOUNT_MAX_0_V"], "vio": []}
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
    assert "Mapping error or design error?" in mod["text"]
    assert "ошибка меппинга" in mod["textRu"]
    assert all(not e["roles"] or e["roles"][0]["state"] == "suggested" for e in r["elements"])


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


def test_range_rules_do_not_outvote_a_signature():
    """A triangle that also satisfies all four GlassPanel range rules is asked about, not
    silently mapped to GlassPanel; with a violated range rule it stays BottomTriangularPanel."""
    base = {"source": "PA", "geometry": {"kind": "surface", "vertexCount": 3, "closed": True}}
    contested = dict(base, nativeId="t1", properties={"hasVertexCount": 3, "hasAspectRatio": 2.0, "hasPlanarityDeviationM": 0.0, "hasWidthM": 5.0})
    narrow = dict(base, nativeId="t2", properties={"hasVertexCount": 3, "hasAspectRatio": 2.0, "hasPlanarityDeviationM": 0.0, "hasWidthM": 4.2})
    r = _compute([contested, narrow])
    by_id = {e["nativeId"]: e for e in r["elements"]}
    groups = {g["groupId"]: g for g in r["groups"]}
    assert by_id["t1"]["state"] == "ambiguous"
    labels = [c["label"] for c in groups[by_id["t1"]["groupId"]]["candidates"]]
    assert "BottomTriangularPanel" in labels and "GlassPanel" in labels
    assert by_id["t2"]["state"] == "suggested"
    assert by_id["t2"]["roles"][0]["classIri"] == "ex:BottomTriangularPanel"


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
