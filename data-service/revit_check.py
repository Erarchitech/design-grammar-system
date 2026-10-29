"""Rule checks of a Revit model without Grasshopper (F-01, 2026-10-29): the pure steps between the DG Revit connector,
dg-evaluator and /validation/publish. app.py wires them to the routes; nothing here does I/O.

1. The connector runs the generated pyRevit program (property_scripts.assemble -> ``revit``) and answers per box its
   UniqueId, label, one value per property and a mesh.
2. ``evaluator_request`` turns that into the Design State input of dg-evaluator (DG.Core, the evaluator VALIDATOR runs).
3. ``with_geometry`` puts each box's mesh on its entity in the per-rule publish bodies dg-evaluator returns.
4. ``verdicts`` / ``check_status`` give the connector what to paint and DeGram the status it already reads from the
   Grasshopper path (boxes, violations, reports, run ids).
"""

from __future__ import annotations

import copy
from typing import Any

FAILED_STATUSES = ("failed", "error")


def evaluator_request(project: str, box_class: dict, result: dict, label: str | None = None) -> dict:
    properties = list(result.get("properties") or [])
    objects = []
    values = []
    for box in result.get("boxes") or []:
        ref = str(box.get("uniqueId") or "")
        if not ref:
            continue
        objects.append({"ref": ref, "label": box.get("label")})
        row = list(box.get("values") or [])
        for k, prop in enumerate(properties):
            value = row[k] if k < len(row) else None
            if isinstance(value, bool) or not isinstance(value, (int, float)):
                continue
            values.append({"ruleId": prop["ruleId"], "dataPropertyIri": prop["dataPropertyIri"], "ref": ref,
                           "value": value})
    rule_ids = []
    for prop in properties:
        if prop["ruleId"] not in rule_ids:
            rule_ids.append(prop["ruleId"])
    return {"project": project, "classIri": box_class["iri"], "label": label, "ruleIds": rule_ids,
            "objects": objects, "values": values}


def with_geometry(publish: dict, result: dict) -> dict:
    """A copy of a dg-evaluator publish body whose entities carry the connector's box meshes."""
    meshes = {str(b.get("uniqueId")): b.get("mesh") for b in result.get("boxes") or [] if b.get("mesh")}
    body = copy.deepcopy(publish)
    for entity in body.get("entities") or []:
        mesh = meshes.get(str(entity.get("dgEntityId")))
        if mesh:
            entity["geometry"] = mesh
    return body


def verdicts(evaluated: dict, result: dict) -> dict[str, dict]:
    """{UniqueId: {broken: [ruleId], open: [ruleId]}} per box, from the canonical status of every rule (D-71: a box
    without data is "no verdict", never a violation)."""
    refs = [str(b.get("uniqueId")) for b in result.get("boxes") or [] if b.get("uniqueId")]
    seen = []
    for ref in refs:
        if ref not in seen:
            seen.append(ref)
    out = {ref: {"broken": [], "open": []} for ref in seen}
    for run in evaluated.get("runs") or []:
        names = list(run.get("validStatusNames") or [])
        for i, ref in enumerate(seen):
            status = names[i] if i < len(names) else ""
            if status in FAILED_STATUSES:
                out[ref]["broken"].append(run["ruleId"])
            elif status and status != "passed":
                out[ref]["open"].append(run["ruleId"])
    return out


def violation_lines(by_ref: dict[str, dict], result: dict) -> list[str]:
    labels = {str(b.get("uniqueId")): b.get("label") or b.get("uniqueId") for b in result.get("boxes") or []}
    return ["%s: %s" % (labels.get(ref, ref), ", ".join(v["broken"])) for ref, v in by_ref.items() if v["broken"]]


def check_status(result: dict, evaluated: dict, run_ids: list[str], by_ref: dict[str, dict],
                 messages: list[str]) -> dict:
    """The status object of the Grasshopper listener, filled from the Revit-native check."""
    runs = list(evaluated.get("runs") or [])
    broken = sum(1 for v in by_ref.values() if v["broken"])
    no_verdict = sum(1 for v in by_ref.values() if not v["broken"] and v["open"])
    return {
        "platform": "Revit",
        "document": result.get("document"),
        "boxes": len(by_ref),
        "violations": violation_lines(by_ref, result),
        "calculatorReport": list(result.get("report") or []),
        "validatorReport": ["%s: %s" % (r.get("ruleId"), r.get("report")) for r in runs],
        "ruleNames": [r.get("ruleName") or r.get("ruleId") for r in runs],
        "validationRunId": list(run_ids),
        "highlighterReport": ["Revit: %d boxes, %d with violations, %d without a verdict, %d pass (painted by the "
                              "DG Revit connector)" % (len(by_ref), broken, no_verdict,
                                                       len(by_ref) - broken - no_verdict)],
        "messages": list(messages),
        "missingRules": list(evaluated.get("missingRules") or []),
    }


def context_categories(label: Any) -> str:
    """The BuiltInCategory a context label starts with ("OST_Walls|Стены : name [id]")."""
    return str(label or "").split("|", 1)[0]
