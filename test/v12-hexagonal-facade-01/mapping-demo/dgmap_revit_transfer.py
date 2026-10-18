"""Offline proof of the GH -> Revit profile transfer (Phase 1303 plan 14, task 3; D-49, D-52). Read-only.

Recomputes the descriptors of a Revit mapping session twice and never writes to Neo4j:

* ``current``: with the profiles as they are in the graph now;
* ``withProfiles18``: with only the profiles retired for the demo cold start
  (retiredReason "cold start for the demo ...", learned in Grasshopper on 2026-10-18)
  switched back on in memory, and every other profile off, so the result shows what
  the Grasshopper-learned profiles alone do to the Revit elements.

Run inside the data-service container (the engine and the driver live there)::

    MSYS_NO_PATHCONV=1 docker cp dgmap_revit_transfer.py data-service:/tmp/
    MSYS_NO_PATHCONV=1 docker cp evidence/act3-revit-gold.json data-service:/tmp/
    MSYS_NO_PATHCONV=1 docker exec -w /app -e PYTHONPATH=/app data-service \
        python /tmp/dgmap_revit_transfer.py ms-XXXXXXXXXXXX /tmp/act3-revit-gold.json > evidence/act3-revit-transfer.json

The gold file maps the Revit "<family> : <type>" name (or the family alone) to the
expected class labels: ``{"byName": {"Hex module : 6pt": ["HexagonalUnit"]}}``.
"""

import json
import sys

import mapping_engine as engine
import mapping_store as store

PROJECT = "v12-hexagonal-facade-01"
COLD_START = "cold start for the demo"


def _gold_by_native_id(descriptors, gold):
    by_name = (gold or {}).get("byName") or {}
    out = {}
    for d in descriptors:
        name = d.get("name") or ""
        family = d.get("family") or ""
        labels = by_name.get(name, by_name.get(family))
        if labels is not None:
            out[d["nativeId"]] = set(labels)
    return out


def _report(result, descriptors, gold):
    summary = result["summary"]
    total = summary["total"] or 1
    groups = []
    for g in result["groups"]:
        top = g["candidates"][0] if g["candidates"] else None
        groups.append({
            "groupId": g["groupId"],
            "size": g["size"],
            "signature": g["signature"],
            "status": g["status"],
            "top": top and {"label": top["label"], "confidence": top["confidence"],
                            "evidence": [e["kind"] + ": " + e["detail"] for e in top["evidence"]]},
            "questionId": g["questionId"],
        })
    out = {
        "summary": summary,
        "openQuestions": summary["openQuestions"],
        "autoShare": round(summary["auto"] / total, 4),
        "questions": [{"questionId": q["questionId"], "type": q["type"], "title": q.get("title")} for q in result["questions"]],
        "groups": groups,
    }
    gold_ids = _gold_by_native_id(descriptors, gold)
    if gold_ids:
        out["metrics"] = engine.evaluate_against_gold(result["elements"], {k: sorted(v) for k, v in gold_ids.items()})
        out["goldCovered"] = len(gold_ids)
    return out


def main(argv):
    if len(argv) < 2:
        print("usage: dgmap_revit_transfer.py <revit session id> [gold.json]", file=sys.stderr)
        return 2
    session_id = argv[1]
    gold = None
    if len(argv) > 2:
        with open(argv[2], encoding="utf-8") as fh:
            gold = json.load(fh)
    with store._get_driver().session() as s:
        x = store.load_session(s, PROJECT, session_id)
        if x is None:
            print("session not found: " + session_id, file=sys.stderr)
            return 1
        if (x.get("platform") or "") != "revit":
            print("not a Revit session: " + session_id, file=sys.stderr)
            return 1
        ctx = x.get("context") or {}
        classes, constraints, rule_classes, profiles = store._engine_inputs(s, PROJECT, ctx.get("vocabulary"))
        descriptors = x["descriptors"]

        def run(profile_set):
            return engine.compute(descriptors, classes, constraints, profile_set,
                                  populations=ctx.get("populations"), platform_default="revit",
                                  rule_classes=rule_classes)

        # The engine's profile dicts do not carry retiredReason: select the cold-start ids in the graph.
        cold_ids = {r["id"] for r in s.run(
            "MATCH (p:MappingProfile {project: $project}) WHERE p.retiredReason STARTS WITH $reason "
            "RETURN p.profileId AS id", project=PROJECT, reason=COLD_START).data()}
        cold = [p for p in profiles if p["profileId"] in cold_ids]
        only_18 = [dict(p, state="active") for p in cold]
        result = {
            "sessionId": session_id,
            "populationsFromSessionId": ctx.get("populationsFromSessionId"),
            "elements": len(descriptors),
            "withVertexCount": sum(1 for d in descriptors if (d.get("geometry") or {}).get("vertexCount")),
            "profiles": {"total": len(profiles),
                         "active": sum(1 for p in profiles if p.get("state", "active") == "active"),
                         "coldStartRetired": len(cold)},
            "current": _report(run(profiles), descriptors, gold),
            "withProfiles18": _report(run(only_18), descriptors, gold),
        }
    print(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
