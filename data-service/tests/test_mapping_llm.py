"""Tests for the LLM mapping proposal (Phase 1303, D-37): digest, validation, failure path. No network."""

import json

import mapping_engine as m
import mapping_fixtures as fx
import mapping_llm as llm


def _inputs():
    classes = fx.facade_classes()
    constraints = m.constraints_from_rows(fx.facade_rule_rows())
    props = [m.PropertyInfo("ex:hasAspectRatio", "hasAspectRatio", ("ex:GlassPanel",)), m.PropertyInfo("ex:hasVertexCount", "hasVertexCount")]
    elements = fx.facade_v1_descriptors()[:3]
    for el in elements:
        el["stream"] = "S1"
        el["names"] = ["Group B Panels"]
    measures = [{"nativeId": "M1", "name": "AR", "component": "measure", "count": 3, "streams": [{"stream": "S1", "pathMatch": True}]}]
    sliders = [{"nativeId": "P1", "name": "Module Width F1", "names": ["Ширина соты"], "value": 6000}]
    return elements, measures, sliders, classes, props, constraints


def test_digest_is_compact_and_complete():
    digest = llm.build_digest(*_inputs())
    canvas = digest["canvas"]
    assert canvas["streams"][0]["id"] == "S1" and canvas["streams"][0]["count"] == 3
    assert canvas["measures"][0]["streamsWithSameBranches"] == ["S1"]
    assert canvas["sliders"][0]["name"] == "Module Width F1"
    assert {c["label"] for c in digest["ontology"]["classes"]} >= {"GlassPanel", "HexagonalUnit"}
    assert digest["ontology"]["rules"] and "required" in digest["ontology"]["rules"][0]
    prompt = llm.build_prompt(digest)
    assert "isParameter" in prompt and json.loads(prompt.split("(JSON):\n", 1)[1].split("\n\nReturn", 1)[0])


def test_proposal_is_validated_against_the_digest():
    digest = llm.build_digest(*_inputs())
    text = "```json\n" + json.dumps({
        "objects": [{"stream": "S1", "classIri": "ex:GlassPanel", "confidence": 0.9, "reason": "glass"},
                    {"stream": "NOPE", "classIri": "ex:GlassPanel"},
                    {"stream": "S1", "classIri": "ex:Invented"}],
        "measures": [{"measure": "M1", "propertyIri": "ex:hasAspectRatio", "stream": "S1", "confidence": 2},
                     {"measure": "M1", "propertyIri": "ex:Invented"}],
        "parameters": [{"slider": "P1", "isParameter": True, "confidence": 0.8}, {"slider": "P1", "isParameter": "yes"}],
    }) + "\n```"
    out = llm.parse_proposal(text, digest)
    assert out["objects"] == {"S1": {"classIri": "ex:GlassPanel", "confidence": 0.9, "reason": "glass"}}
    assert out["measures"]["M1"]["confidence"] == 1.0 and out["measures"]["M1"]["stream"] == "S1"
    assert out["parameters"]["P1"]["isParameter"] is True
    assert llm.parse_proposal("no json here", digest) == {"objects": {}, "measures": {}, "parameters": {}}


def test_provider_failure_is_reported_not_raised(monkeypatch):
    def boom():
        raise RuntimeError("no settings")

    monkeypatch.setattr(llm.llm_gateway, "load_persisted_llm_settings", boom)
    out = llm.propose_mapping(*_inputs())
    assert out["status"] == "unavailable" and out["objects"] == {} and "error" in out
