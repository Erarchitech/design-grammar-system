"""Generate property-calculator scripts from the rules of a project (Phase 1303-15, DGOPN-02).

Design Grammars turns the DataProperties that the rules of a project test into a ready
Grasshopper chain: a calculator script that computes those properties from the active
Revit model (Rhino.Inside.Revit), the OBJECT STATE / PROPERTY STATE / DESIGN STATE /
VALIDATOR components, and a highlighter script that colours the result in Revit.

The scripts are assembled only from the vetted templates of
``property_calculators/catalogue.json``. A DataProperty is resolved to a catalogue entry by
alias pattern; an optional chooser (an LLM) may name an entry and its parameters for a
property no alias covers, and its answer is accepted only when it names an existing entry
with schema-valid parameters. Nothing a chooser returns is ever inserted as code, and an
unresolved property is reported as unsupported, never guessed. Same input, same bytes.
"""

from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path
from string import Template
from typing import Any, Callable, Iterable

CATALOGUE_DIR = Path(__file__).resolve().parent / "property_calculators"

RULE_ATOMS_QUERY = (
    "MATCH (r:Rule {graph:'Metagraph', project:$project})-[:HAS_BODY]->(a:Atom)-[:REFERS_TO]->(p) "
    "WHERE $ruleIds IS NULL OR r.Rule_Id IN $ruleIds "
    "RETURN r.Rule_Id AS ruleId, labels(p) AS labels, p.iri AS iri, "
    "coalesce(p.label, p.SWRL_label, p.iri) AS label "
    "ORDER BY ruleId, iri"
)

Chooser = Callable[[dict, dict], "dict | None"]


class PropertyScriptError(ValueError):
    """A request the generator cannot serve (no rules, several box classes, ...)."""

    def __init__(self, code: str, message: str):
        super().__init__(message)
        self.code = code


def load_catalogue(directory: Path = CATALOGUE_DIR) -> dict:
    catalogue = json.loads((directory / "catalogue.json").read_text(encoding="utf-8"))
    catalogue["_dir"] = str(directory)
    return catalogue


def _template_text(catalogue: dict, name: str) -> str:
    return (Path(catalogue["_dir"]) / name).read_text(encoding="utf-8").replace("\r\n", "\n")


def local_name(iri_or_label: str) -> str:
    text = (iri_or_label or "").strip()
    for sep in ("#", "/", ":"):
        if sep in text:
            text = text.rsplit(sep, 1)[1]
    return text


def rules_from_rows(rows: Iterable[dict]) -> list[dict]:
    """Group RULE_ATOMS_QUERY rows into [{ruleId, classes, dataProperties}] sorted by ruleId."""
    rules: dict[str, dict] = {}
    for row in rows:
        rule = rules.setdefault(row["ruleId"], {"ruleId": row["ruleId"], "classes": [], "dataProperties": []})
        labels = set(row.get("labels") or [])
        entry = {"iri": row.get("iri") or "", "label": row.get("label") or row.get("iri") or ""}
        if "Class" in labels:
            bucket = rule["classes"]
        elif "DatatypeProperty" in labels:
            bucket = rule["dataProperties"]
        else:
            continue
        if entry not in bucket:
            bucket.append(entry)
    return [rules[k] for k in sorted(rules)]


def load_rules(session: Any, project: str, rule_ids: list[str] | None) -> list[dict]:
    rows = session.run(RULE_ATOMS_QUERY, project=project, ruleIds=rule_ids or None).data()
    return rules_from_rows(rows)


def _validate_params(catalogue: dict, calculator_id: str, params: dict) -> dict:
    spec = catalogue["calculators"][calculator_id]["params"]
    unknown = sorted(set(params) - set(spec))
    if unknown:
        raise PropertyScriptError("PARAM_UNKNOWN", f"{calculator_id}: unknown parameters {unknown}")
    allowed = set(catalogue["builtin_categories"])
    out: dict[str, Any] = {}
    for name in sorted(spec):
        rule = spec[name]
        if name in params:
            value = params[name]
        elif rule.get("required"):
            raise PropertyScriptError("PARAM_MISSING", f"{calculator_id}: parameter {name} is required")
        else:
            value = rule.get("default")
        if rule["type"] == "builtin_category_list":
            if not isinstance(value, list) or not value or any(v not in allowed for v in value):
                raise PropertyScriptError("PARAM_INVALID", f"{calculator_id}: {name} must list known categories")
            value = list(value)
        elif rule["type"] == "number":
            if isinstance(value, bool) or not isinstance(value, (int, float)):
                raise PropertyScriptError("PARAM_INVALID", f"{calculator_id}: {name} must be a number")
        out[name] = value
    return out


def resolve_property(data_property: dict, catalogue: dict, chooser: Chooser | None = None) -> dict | None:
    """Catalogue binding for one DataProperty: alias first, then an optional validated chooser."""
    name = local_name(data_property.get("label") or data_property.get("iri") or "").lower()
    for alias in catalogue["aliases"]:
        if re.match(alias["pattern"], name):
            return {
                "calculator": alias["calculator"],
                "params": _validate_params(catalogue, alias["calculator"], alias["params"]),
                "resolvedBy": "alias",
            }
    if chooser is None:
        return None
    menu = {cid: {"summary": c["summary"], "params": c["params"], "unit": c["unit"]}
            for cid, c in sorted(catalogue["calculators"].items())}
    answer = chooser(data_property, menu)
    if not isinstance(answer, dict) or answer.get("calculator") not in catalogue["calculators"]:
        return None
    try:
        params = _validate_params(catalogue, answer["calculator"], answer.get("params") or {})
    except PropertyScriptError:
        return None
    return {"calculator": answer["calculator"], "params": params, "resolvedBy": "chooser"}


def resolve(rules: list[dict], catalogue: dict, chooser: Chooser | None = None) -> dict:
    if not rules:
        raise PropertyScriptError("NO_RULES", "The project has no rules with DataProperty atoms to compute")
    classes = sorted({(c["iri"], c["label"]) for r in rules for c in r["classes"]})
    if len(classes) != 1:
        raise PropertyScriptError(
            "BOX_CLASS_AMBIGUOUS",
            f"The rules must test exactly one element class; found {[c[1] for c in classes] or 'none'}")
    resolved: list[dict] = []
    unsupported: list[dict] = []
    for rule in rules:
        for dp in sorted(rule["dataProperties"], key=lambda d: d["iri"]):
            binding = resolve_property(dp, catalogue, chooser)
            if binding is None:
                unsupported.append({"ruleId": rule["ruleId"], "dataPropertyIri": dp["iri"],
                                    "dataPropertyLabel": dp["label"], "reason": "no catalogue calculator"})
                continue
            resolved.append({
                "ruleId": rule["ruleId"],
                "dataPropertyIri": dp["iri"],
                "dataPropertyLabel": local_name(dp["label"]),
                **binding,
            })
    return {"boxClass": {"iri": classes[0][0], "label": local_name(classes[0][1])},
            "resolved": resolved, "unsupported": unsupported}


def _py_literal(value: Any) -> str:
    """A Python literal for JSON-like data (deterministic: sorted keys, no LLM text outside values)."""
    return json.dumps(value, sort_keys=True, ensure_ascii=False, indent=4).replace(": true", ": True").replace(
        ": false", ": False").replace(": null", ": None")


def assemble(project: str, resolution: dict, catalogue: dict) -> dict:
    resolved = resolution["resolved"]
    if not resolved:
        raise PropertyScriptError("NOTHING_TO_COMPUTE", "No rule DataProperty resolved to a catalogue calculator")
    used = sorted({r["calculator"] for r in resolved})
    functions = "\n\n".join(_template_text(catalogue, catalogue["calculators"][c]["template"]).rstrip()
                            for c in used)
    table = [{"key": f"P{k}", "ruleId": r["ruleId"], "dataPropertyIri": r["dataPropertyIri"],
              "dataPropertyLabel": r["dataPropertyLabel"], "calculator": r["calculator"], "params": r["params"]}
             for k, r in enumerate(resolved, start=1)]
    defaults = "\n".join(f'R{k} = {json.dumps(r["ruleId"])}\nD{k} = {json.dumps(r["dataPropertyIri"])}\nP{k} = []'
                         for k, r in enumerate(resolved, start=1))
    assignments = "\n".join(f"        P{k} = _values[{k - 1}]" for k in range(1, len(resolved) + 1))
    rule_ids = sorted({r["ruleId"] for r in resolved})
    common = {
        "project": project,
        "rule_ids": ", ".join(rule_ids),
        "catalogue_version": catalogue["version"],
    }
    calculator_source = Template(_template_text(catalogue, catalogue["shell"]["template"])).substitute(
        common,
        calculator_ids=", ".join(used),
        box_class_iri=resolution["boxClass"]["iri"],
        box_class_label=resolution["boxClass"]["label"],
        property_table=_py_literal(table),
        calculators=functions,
        calculator_functions="{" + ", ".join(
            f'"{c}": {catalogue["calculators"][c]["function"]}' for c in used) + "}",
        output_defaults=defaults,
        output_assignments=assignments,
    )
    highlighter_source = Template(_template_text(catalogue, catalogue["highlighter"]["template"])).substitute(common)
    n = len(resolved)
    calculator = {
        "key": "calculator",
        "nickname": "DG PROPERTY CALCULATOR",
        "language": "python3",
        "source": calculator_source,
        "inputs": [{"name": "Run", "access": "item", "hint": "bool"},
                   {"name": "BoxFamilyFilter", "access": "item", "hint": "str"}],
        "outputs": ["Objects", "Geometry", "Labels", "UniqueIds", "RuleIds", "Report"]
                   + [f"{p}{k}" for k in range(1, n + 1) for p in ("R", "D", "P")],
    }
    highlighter = {
        "key": "highlighter",
        "nickname": "DG VALIDATION HIGHLIGHTER",
        "language": "python3",
        "source": highlighter_source,
        "inputs": [{"name": "Run", "access": "item", "hint": "bool"},
                   {"name": "Clear", "access": "item", "hint": "bool"},
                   {"name": "UniqueIds", "access": "list", "hint": "str"},
                   {"name": "RuleIds", "access": "list", "hint": "str"},
                   {"name": "ValidStatus", "access": "tree", "hint": "bool"}],
        "outputs": ["Report", "Violations"],
    }
    for script in (calculator, highlighter):
        script["sha256"] = hashlib.sha256(script["source"].encode("utf-8")).hexdigest()
    return {"calculator": calculator, "highlighter": highlighter,
            "placement": placement_plan(project, n)}


def placement_plan(project: str, property_count: int) -> dict:
    """Components, positions and wires of the checking chain; executed by the LISTENER command
    place_property_script. CONNECTOR is reused from the canvas (the user signs in there)."""
    col = [0, 260, 520, 780, 1040, 1300]
    components: list[dict] = [
        {"key": "connector", "kind": "dg", "type": "CONNECTOR", "reuse": True, "required": True},
        {"key": "metagraph", "kind": "dg", "type": "METAGRAPH", "reuse": True, "x": col[0], "y": -260},
        {"key": "run", "kind": "toggle", "nickname": "Run", "value": False, "x": col[0] - 200, "y": 0},
        {"key": "filter", "kind": "panel", "nickname": "BoxFamilyFilter", "text": "", "x": col[0] - 200, "y": 60},
        {"key": "calculator", "kind": "script", "script": "calculator", "x": col[0], "y": 0},
        {"key": "objstate", "kind": "dg", "type": "OBJECT STATE", "x": col[1], "y": 0},
        {"key": "rulebyid", "kind": "dg", "type": "RULE BY ID", "x": col[2], "y": -260},
        {"key": "designstate", "kind": "dg", "type": "DESIGN STATE", "x": col[3], "y": 0},
        {"key": "send", "kind": "toggle", "nickname": "SendValid", "value": False, "x": col[3], "y": -160},
        {"key": "validator", "kind": "dg", "type": "VALIDATOR", "x": col[4], "y": 0},
        {"key": "paint", "kind": "toggle", "nickname": "Paint", "value": False, "x": col[4], "y": 260},
        {"key": "clear", "kind": "toggle", "nickname": "Clear", "value": False, "x": col[4], "y": 320},
        {"key": "highlighter", "kind": "script", "script": "highlighter", "x": col[5], "y": 0},
    ]
    wires = [
        ["connector.Database", "metagraph.Metagraph"],
        ["run.", "calculator.Run"],
        ["filter.", "calculator.BoxFamilyFilter"],
        ["calculator.Objects", "objstate.Object"],
        ["calculator.Geometry", "objstate.Geometry"],
        ["calculator.Labels", "objstate.Label"],
        ["metagraph.Rules", "rulebyid.Rules"],
        ["calculator.RuleIds", "rulebyid.RuleId"],
        ["objstate.ObjState", "designstate.ObjState"],
        ["rulebyid.Rule", "validator.Rule"],
        ["designstate.DesignState", "validator.DesignState"],
        ["send.", "validator.SendValid"],
        ["connector.Session", "validator.Token"],
        ["paint.", "highlighter.Run"],
        ["clear.", "highlighter.Clear"],
        ["calculator.UniqueIds", "highlighter.UniqueIds"],
        ["calculator.RuleIds", "highlighter.RuleIds"],
        ["validator.ValidStatus", "highlighter.ValidStatus"],
    ]
    for k in range(1, property_count + 1):
        key = f"prop{k}"
        components.append({"key": key, "kind": "dg", "type": "PROPERTY STATE", "x": col[2], "y": 120 * (k - 1)})
        wires += [
            [f"calculator.R{k}", f"{key}.Rule"],
            [f"calculator.D{k}", f"{key}.DataProperty"],
            [f"calculator.P{k}", f"{key}.PropValue"],
            ["objstate.ObjState", f"{key}.ObjState"],
            [f"{key}.PropState", "designstate.PropState"],
        ]
    return {"group": f"DG · Проверка свойств ({project})", "components": components, "wires": wires}


def generate(session: Any, project: str, rule_ids: list[str] | None, chooser: Chooser | None = None,
             catalogue: dict | None = None) -> dict:
    catalogue = catalogue or load_catalogue()
    rules = load_rules(session, project, rule_ids)
    resolution = resolve(rules, catalogue, chooser)
    if resolution["unsupported"] and not resolution["resolved"]:
        raise PropertyScriptError("NOTHING_TO_COMPUTE", "No rule DataProperty resolved to a catalogue calculator")
    scripts = assemble(project, resolution, catalogue)
    return {
        "project": project,
        "catalogueVersion": catalogue["version"],
        "boxClass": resolution["boxClass"],
        "resolved": resolution["resolved"],
        "unsupported": resolution["unsupported"],
        **scripts,
    }
