"""LLM proposal for automatic mapping (Phase 1303, 1303-CONTEXT D-37).

One call per mapping session, through the provider-agnostic gateway: the model sees the
project ontology (classes, datatype properties, rules) and a compact digest of the canvas
(element streams, calculation outputs, named sliders with the canvas text around them) and
proposes which stream is which DG class, which output carries which DG property, and which
sliders are DG parameters. The answer is validated against the digest (unknown ids or IRIs
are dropped) and recorded in the session; the deterministic engine treats it as one vote,
and a human confirms. The API key never leaves the gateway.
"""

from __future__ import annotations

import json
import os
import re
from collections import Counter
from typing import Any, Mapping, Optional, Sequence

import llm_gateway
import mapping_engine as engine

# Reasoning models spend completion tokens on hidden reasoning before the answer; 4 000
# tokens ended in an empty, truncated answer on the live facade digest (2026-10-18).
MAX_TOKENS = 24000
# The proposal runs in the background (mapping_store.LLM_ASYNC); at 24 000 tokens the reasoning
# model needed more than the gateway's interactive 120 s on the clean facade (2026-10-18).
TIMEOUT_S = 420.0
MAX_STREAMS = 60
MAX_MEASURES = 80
MAX_SLIDERS = 80

SYSTEM = (
    "You map a Grasshopper (Rhino) definition to the ontology of a Design Grammars (DG) project. "
    "In DG an element stream (geometry output) is an instance population of an ontology Class; a number slider is a "
    "DG Parameter of the design (it drives variants); the value of a datatype Property comes from the output of a "
    "calculation component (for example Area, or a script that measures the elements of one stream). "
    "Use the names, group names, scribble text, counts, geometry features and value ranges given. "
    "Russian and English names both occur. Propose only what the evidence supports; use null when nothing fits. "
    "Keep reasons to a few words and keep thinking short. Answer with ONE JSON object and nothing else."
)

SCHEMA_HINT = {
    "objects": [{"stream": "<stream id>", "classIri": "<class IRI or null>", "confidence": 0.0, "reason": "<short>"}],
    "measures": [{"measure": "<measure id>", "propertyIri": "<property IRI or null>", "stream": "<stream id or null>", "confidence": 0.0, "reason": "<short>"}],
    "parameters": [{"slider": "<slider id>", "isParameter": True, "confidence": 0.0, "reason": "<short>"}],
}


def _short(values: Sequence[Any], n: int) -> list:
    return [str(v)[:80] for v in list(values)[:n]]


def build_digest(elements: Sequence[Mapping], measures: Sequence[Mapping], parameters: Sequence[Mapping],
                 classes: Sequence[engine.ClassInfo], properties: Sequence[engine.PropertyInfo],
                 constraints: Sequence[engine.Constraint]) -> dict:
    streams: dict = {}
    for d in elements or []:
        sid = d.get("stream")
        if not sid:
            continue
        s = streams.setdefault(str(sid), {"id": str(sid), "source": d.get("source"), "names": _short(engine._texts(d.get("names")), 6),
                                           "count": 0, "kinds": Counter(), "vertexCounts": Counter(), "sample": None})
        s["count"] += 1
        geo = d.get("geometry") if isinstance(d.get("geometry"), Mapping) else {}
        s["kinds"][str(geo.get("kind"))] += 1
        if geo.get("vertexCount") is not None:
            s["vertexCounts"][str(geo.get("vertexCount"))] += 1
        if s["sample"] is None:
            props = d.get("properties") if isinstance(d.get("properties"), Mapping) else {}
            s["sample"] = {k: v for k, v in list({**geo, **props}.items())[:12]}
    stream_list = []
    for s in sorted(streams.values(), key=lambda s: s["id"])[:MAX_STREAMS]:
        stream_list.append({**s, "kinds": dict(s["kinds"]), "vertexCounts": dict(s["vertexCounts"].most_common(4))})
    measure_list = []
    for m in sorted(measures or [], key=lambda m: str(m.get("nativeId")))[:MAX_MEASURES]:
        measure_list.append({
            "id": str(m.get("nativeId")),
            "name": m.get("name"),
            "component": m.get("component"),
            "names": _short(engine._texts(m.get("names")), 4),
            "count": m.get("count"),
            "min": m.get("min"),
            "max": m.get("max"),
            "streamsWithSameBranches": [str(s.get("stream")) for s in m.get("streams") or [] if isinstance(s, Mapping) and s.get("pathMatch")],
        })
    slider_list = [
        {"id": str(p.get("nativeId")), "name": p.get("name"), "names": _short(engine._texts(p.get("names")), 3), "value": p.get("value"),
         "min": p.get("min"), "max": p.get("max")}
        for p in sorted(parameters or [], key=lambda p: str(p.get("nativeId")))[:MAX_SLIDERS]
    ]
    rules = [
        {"ruleId": c.rule_id, "class": c.class_local, "property": c.prop_local, "required": f"{c.op} {engine._fmt(c.value)}"}
        for c in constraints
    ]
    return {
        "ontology": {
            "classes": [{"iri": c.iri, "label": c.label} for c in classes],
            "properties": [{"iri": p.iri, "label": p.label, "usedByClasses": [engine.local_name(x) for x in p.classes]} for p in properties],
            "rules": rules[:120],
        },
        "canvas": {"streams": stream_list, "measures": measure_list, "sliders": slider_list},
    }


def build_prompt(digest: Mapping) -> str:
    return (
        "Ontology and canvas digest (JSON):\n"
        + json.dumps(digest, ensure_ascii=False, separators=(",", ":"))
        + "\n\nReturn JSON of exactly this shape (one entry per stream, measure and slider you can judge):\n"
        + json.dumps(SCHEMA_HINT, ensure_ascii=False)
        + "\nRules: classIri and propertyIri must be IRIs from the ontology or null; stream/measure/slider ids must be "
          "ids from the canvas; a measure's stream is the element stream whose elements it measures (usually one of "
          "streamsWithSameBranches); isParameter is true for sliders that are design parameters (they change the "
          "design or its variants), false for drawing or tolerance helpers; confidence is 0..1."
    )


_FENCE = re.compile(r"```(?:json)?\s*(.*?)```", re.S)


def _extract_json(text: str) -> Optional[dict]:
    if not text:
        return None
    m = _FENCE.search(text)
    candidate = m.group(1) if m else text
    start, end = candidate.find("{"), candidate.rfind("}")
    if start < 0 or end <= start:
        return None
    try:
        obj = json.loads(candidate[start:end + 1])
    except ValueError:
        return None
    return obj if isinstance(obj, dict) else None


def parse_proposal(text: str, digest: Mapping) -> dict:
    obj = _extract_json(text) or {}
    canvas = digest.get("canvas") or {}
    stream_ids = {s["id"] for s in canvas.get("streams") or []}
    measure_ids = {m["id"] for m in canvas.get("measures") or []}
    slider_ids = {s["id"] for s in canvas.get("sliders") or []}
    onto = digest.get("ontology") or {}
    class_iris = {c["iri"] for c in onto.get("classes") or []}
    prop_iris = {p["iri"] for p in onto.get("properties") or []}

    def conf(v: Any) -> float:
        c = engine._num(v)
        return 0.7 if c is None else max(0.0, min(1.0, c))

    out = {"objects": {}, "measures": {}, "parameters": {}}
    for e in obj.get("objects") or []:
        if isinstance(e, Mapping) and str(e.get("stream")) in stream_ids and e.get("classIri") in class_iris:
            out["objects"][str(e["stream"])] = {"classIri": e["classIri"], "confidence": conf(e.get("confidence")), "reason": str(e.get("reason") or "")[:300]}
    for e in obj.get("measures") or []:
        if isinstance(e, Mapping) and str(e.get("measure")) in measure_ids and e.get("propertyIri") in prop_iris:
            stream = str(e["stream"]) if str(e.get("stream")) in stream_ids else None
            out["measures"][str(e["measure"])] = {"propertyIri": e["propertyIri"], "stream": stream, "confidence": conf(e.get("confidence")),
                                                   "reason": str(e.get("reason") or "")[:300]}
    for e in obj.get("parameters") or []:
        if isinstance(e, Mapping) and str(e.get("slider")) in slider_ids and isinstance(e.get("isParameter"), bool):
            out["parameters"][str(e["slider"])] = {"isParameter": e["isParameter"], "confidence": conf(e.get("confidence")), "reason": str(e.get("reason") or "")[:300]}
    return out


def propose_mapping(elements, measures, parameters, classes, properties, constraints) -> dict:
    """Ask the active LLM provider for a mapping proposal; never raises.

    Returns {status: ok | empty | unavailable, provider, model, objects, measures, parameters}.
    """
    digest = build_digest(elements, measures, parameters, classes, properties, constraints)
    try:
        settings = llm_gateway.load_persisted_llm_settings()
        provider, model, api_key = llm_gateway.resolve_active_provider(settings, os.getenv("LLM_MASTER_SECRET", ""))
        adapter = llm_gateway.get_adapter(provider, settings.get("baseUrl"))
        request = llm_gateway.GenerateRequest(prompt=build_prompt(digest), system=SYSTEM, model=model, provider=provider)
        response = adapter.generate(request, api_key, options=llm_gateway.GenerationOptions(temperature=0.0, max_tokens=MAX_TOKENS, timeout_s=TIMEOUT_S))
    except Exception as exc:  # noqa: BLE001 - the proposal is optional; the engine works without it
        try:
            code = llm_gateway.map_provider_error(exc)[2]
        except Exception:  # noqa: BLE001
            code = type(exc).__name__
        return {"status": "unavailable", "error": str(code)[:80], "objects": {}, "measures": {}, "parameters": {}}
    proposal = parse_proposal(getattr(response, "text", "") or "", digest)
    found = sum(len(v) for v in proposal.values())
    return {
        "status": "ok" if found else "empty",
        "provider": getattr(response, "provider", None),
        "model": getattr(response, "model", None),
        "truncated": bool(getattr(response, "truncated", False)),
        **proposal,
    }
