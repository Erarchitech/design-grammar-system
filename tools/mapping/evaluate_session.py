#!/usr/bin/env python3
"""Precision / recall of a saved mapping session against known answers (Phase 1303, plan 06).

Gold labels:
  * Grasshopper: the stream in the native id ``gh:<key>:<stream>:<path>:0`` (HU, GU, PB, PA, F)
    maps to the facade class (--stream-map overrides the default JSON map).
  * Revit: ``--family-map family->[classes]`` together with ``--descriptors`` (the upload file),
    because the session result carries native ids only.

Usage::

    python tools/mapping/evaluate_session.py --session act1.json
    python tools/mapping/evaluate_session.py --session act3.json --descriptors act3-revit.json \
        --family-map '{"Facade_Module_Hex": ["HexagonalUnit", "FacadeModule"]}'

Prints a JSON report: questions, states, per-class precision/recall, auto share.
"""

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "data-service"))

import mapping_engine  # noqa: E402

DEFAULT_STREAMS = {
    "HU": ["HexagonalUnit"],
    "GU": ["GroundFloorUnit"],
    "PB": ["GlassPanel"],
    "PA": ["BottomTriangularPanel"],
    "F": ["Facade"],
}


def gold_for(session, descriptors=None, stream_map=None, family_map=None):
    stream_map = stream_map or DEFAULT_STREAMS
    family_of = {}
    for d in (descriptors or {}).get("elements", []) if isinstance(descriptors, dict) else (descriptors or []):
        family_of[d.get("nativeId")] = d.get("family")
    gold = {}
    for el in session["elements"]:
        nid = el["nativeId"]
        if nid.startswith("gh:"):
            parts = nid.split(":")
            stream = parts[2] if len(parts) > 2 else ""
            if stream in stream_map:
                gold[nid] = set(stream_map[stream])
        elif family_map and family_of.get(nid) in family_map:
            gold[nid] = set(family_map[family_of[nid]])
    return gold


def report(session, gold):
    states = {}
    for el in session["elements"]:
        states[el["state"]] = states.get(el["state"], 0) + 1
    scored = [el for el in session["elements"] if el["nativeId"] in gold]
    metrics = mapping_engine.evaluate_against_gold(scored, gold)
    total = len(session["elements"]) or 1
    return {
        "sessionId": session.get("sessionId"),
        "label": session.get("label"),
        "platform": session.get("platform"),
        "openQuestions": session.get("summary", {}).get("openQuestions"),
        "questionTypes": [q["type"] for q in session.get("questions", [])],
        "states": dict(sorted(states.items())),
        "autoShare": round(states.get("auto", 0) / total, 4),
        "goldCovered": len(scored),
        "metrics": metrics,
    }


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--session", required=True, help="saved GET /mapping/sessions/{id} response (JSON)")
    parser.add_argument("--descriptors", help="upload body or descriptor list (needed for Revit family gold)")
    parser.add_argument("--stream-map", help="JSON object stream -> [class labels]")
    parser.add_argument("--family-map", help="JSON object family -> [class labels]")
    args = parser.parse_args(argv)
    session = json.loads(Path(args.session).read_text(encoding="utf-8-sig"))
    descriptors = json.loads(Path(args.descriptors).read_text(encoding="utf-8-sig")) if args.descriptors else None
    stream_map = json.loads(args.stream_map) if args.stream_map else None
    family_map = json.loads(args.family_map) if args.family_map else None
    out = report(session, gold_for(session, descriptors, stream_map, family_map))
    print(json.dumps(out, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
