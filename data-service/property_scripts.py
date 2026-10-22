"""Generate property-calculator scripts from the rules of a project (Phase 1303-15, DGOPN-02).

Design Grammars turns the DataProperties that the rules of a project test into a ready
Grasshopper chain: a calculator script that computes those properties from the active
Revit model (Rhino.Inside.Revit), the OBJECT STATE / PROPERTY STATE / DESIGN STATE /
VALIDATOR components, and a highlighter script that colours the result in Revit.

A DataProperty is bound, in order, to: a vetted catalogue template
(``property_calculators/catalogue.json``) by alias or an optional catalogue chooser; a calculator
confirmed by the company (Phase 1303-17, D-54: ``CatalogueCalculator``, no LLM call); its stored
calculator (property_calculator_store, so scripts persist across rule updates and Design States);
and, for a property nothing covers, a calculator the LLM writes under the contract of
property_calculator_llm (validated AST, read-only model helpers). Shared and stored generated
code is verified (sha256, contract) before it binds, and a source the project rejected is never
bound. New bindings are stored when the scripts are placed, so the LLM is asked once per
property; a property that still has no calculator is reported as unsupported, never guessed.
Same rules and store, same bytes.
"""

from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path
from string import Template
from typing import Any, Callable, Iterable

CATALOGUE_DIR = Path(__file__).resolve().parent / "property_calculators"

# Same corpus as VALIDATOR (Neo4jRuleRepository.RulesQuery): a superseded rule (rule update) is excluded.
RULE_ATOMS_QUERY = (
    "MATCH (r:Rule {graph:'Metagraph', project:$project})-[:HAS_BODY]->(a:Atom)-[:REFERS_TO]->(p) "
    "WHERE ($ruleIds IS NULL OR r.Rule_Id IN $ruleIds) AND NOT EXISTS { (r)-[:SUPERSEDED_BY]->() } "
    "RETURN r.Rule_Id AS ruleId, coalesce(r.text, '') AS text, coalesce(r.SWRL, r.swrl, '') AS swrl, "
    "labels(p) AS labels, p.iri AS iri, coalesce(p.label, p.SWRL_label, p.iri) AS label "
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
        rule = rules.setdefault(row["ruleId"], {"ruleId": row["ruleId"], "text": row.get("text") or "",
                                                "swrl": row.get("swrl") or "", "classes": [], "dataProperties": []})
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
    # Match on the IRI's local name: a DatatypeProperty's SWRL_label can be a description
    # ("minimum clear distance to a door or window opening ...") rather than its name.
    raw_name = local_name(data_property.get("iri") or data_property.get("label") or "")
    name = raw_name.lower()
    for alias in catalogue["aliases"]:
        if re.match(alias["pattern"], name):
            return {
                "calculator": alias["calculator"],
                "params": _validate_params(catalogue, alias["calculator"], alias["params"]),
                "resolvedBy": "alias",
            }
    # A wording variant of a vocabulary property (hasMinHostOpeningClearanceMm for hasMinOpeningClearanceMm) is
    # the same measure: bind it to the vetted calculator instead of asking the LLM for a new one.
    import class_duplicates

    for entry in catalogue.get("vocabulary", []):
        if class_duplicates.property_reason(raw_name, entry["property"]):
            known = entry["property"].lower()
            for alias in catalogue["aliases"]:
                if re.match(alias["pattern"], known):
                    return {
                        "calculator": alias["calculator"],
                        "params": _validate_params(catalogue, alias["calculator"], alias["params"]),
                        "resolvedBy": "vocabulary-near-match",
                        "nearMatch": entry["property"],
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


Generator = Callable[[dict, list, str], dict]


def read_categories(entry: dict, catalogue: dict) -> list[str]:
    """Revit categories the bound calculator reads: declared by the catalogue entry (``reads``), or extracted from a
    generated calculator's source by AST. Only known categories count."""
    if entry.get("origin") == "generated":
        from property_calculator_llm import categories_in

        categories = categories_in(entry.get("source") or "")
    else:
        spec = catalogue["calculators"].get(entry["calculator"], {}).get("reads") or {}
        categories = list(spec.get("fixed") or [])
        for name in spec.get("params") or []:
            categories += list((entry.get("params") or {}).get(name) or [])
    allowed = set(catalogue["builtin_categories"])
    return sorted({c for c in categories if c in allowed})


def context_classes(entry: dict, catalogue: dict, iri_prefix: str) -> list[dict]:
    """The DG classes behind the categories a calculator reads (Beam, Column, Wall, ...), so every class a rule's
    property depends on exists in the OntoGraph; DG creates them, the user never has to."""
    by_label: dict[str, list[str]] = {}
    for category in read_categories(entry, catalogue):
        label = catalogue.get("categoryClasses", {}).get(category)
        if label:
            by_label.setdefault(label, []).append(category)
    return [{"label": label, "iri": f"{iri_prefix}{label}", "revitCategories": sorted(cats)}
            for label, cats in sorted(by_label.items())]


def iri_prefix_of(iri: str) -> str:
    name = local_name(iri)
    return iri[: len(iri) - len(name)] if name and iri.endswith(name) else "ex:"


def _integrity_problem(entry: dict) -> str | None:
    """None when the generated calculator of ``entry`` is exactly what the generation contract produced (sha256,
    function name, validated AST, normalized form), else a short reason (Phase 1303-17, D-54)."""
    from property_calculator_llm import verify_stored_source

    return verify_stored_source(entry.get("source"), entry.get("function"), entry.get("sha256"))


def _from_shared(entry: dict, catalogue: dict, stored_record: dict | None, warnings: list[str]) -> dict | None:
    """A confirmed company-catalogue entry as a binding (D-54 point 5), or None with a warning when its stored source
    fails the integrity check. A shared entry is never regenerated: the LLM is not asked. ``new`` is true unless the
    project already holds exactly this source under the same catalogue id."""
    name = entry.get("propertyName") or entry.get("propertyKey") or "?"
    problem = _integrity_problem(entry)
    if problem:
        warnings.append(f"company calculator {entry.get('catalogueId')} for {name} skipped: {problem}")
        return None
    if entry.get("contractVersion") != catalogue.get("version"):
        warnings.append(f"company calculator {entry.get('catalogueId')} for {name} was confirmed under contract "
                        f"{entry.get('contractVersion')!r}, the current contract is {catalogue.get('version')!r}")
    digest = entry["sha256"]
    same = (stored_record is not None and stored_record.get("sha256") == digest
            and stored_record.get("catalogueId") == entry.get("catalogueId"))
    return {"calculator": f"generated:{digest[:10]}", "params": {}, "resolvedBy": "shared", "origin": "generated",
            "function": entry["function"], "source": entry["source"], "sha256": digest,
            "provider": entry.get("provider"), "model": entry.get("model"), "unit": entry.get("unit") or None,
            "catalogueId": entry.get("catalogueId"), "reviewStatus": "confirmed", "new": not same}


def _from_stored(record: dict, catalogue: dict, warnings: list[str] | None = None,
                 blocked: dict[str, dict] | None = None, iri: str | None = None) -> dict | None:
    """A stored calculator as a binding; a catalogue entry that no longer exists is not reused. A generated record
    is verified again (sha256, contract) and a source the project rejected is never bound (D-54 point 4)."""
    warnings = warnings if warnings is not None else []
    if record.get("origin") == "generated":
        if not record.get("source") or not record.get("function"):
            return None
        iri = record.get("dataPropertyIri") or iri or ""
        if blocked and iri and _rejected(blocked, iri, record.get("sha256")):
            warnings.append(f"stored calculator for {local_name(iri)} skipped: this project rejected that source")
            return None
        problem = _integrity_problem(record)
        if problem:
            warnings.append(f"stored calculator for {local_name(iri) or '?'} skipped: {problem}")
            return None
        return {"calculator": record["calculator"], "params": record.get("params") or {}, "resolvedBy": "stored",
                "origin": "generated", "function": record["function"], "source": record["source"],
                "sha256": record.get("sha256"), "provider": record.get("provider"), "model": record.get("model"),
                "unit": record.get("unit") or None, "explanation": record.get("explanation"),
                "catalogueId": record.get("catalogueId"),
                "reviewStatus": record.get("reviewStatus") or "pending"}
    if record.get("calculator") not in catalogue["calculators"]:
        return None
    try:
        params = _validate_params(catalogue, record["calculator"], record.get("params") or {})
    except PropertyScriptError:
        return None
    return {"calculator": record["calculator"], "params": params, "resolvedBy": "stored", "origin": "catalogue"}


def _rejected(blocked: dict[str, dict] | None, iri: str, sha256: str | None) -> bool:
    import property_calculator_store

    return property_calculator_store.rejected_source(blocked or {}, iri, sha256)


def resolve(rules: list[dict], catalogue: dict, chooser: Chooser | None = None,
            stored: dict[str, dict] | None = None, generator: Generator | None = None,
            shared: dict[str, dict] | None = None, blocked: dict[str, dict] | None = None) -> dict:
    """Bind every body DataProperty, in the order of D-54 point 5: the vetted file catalogue (alias, chooser), the
    confirmed calculators of the company (``shared``, by propertyKey), the project's stored calculator (scripts
    persist across rule updates and Design States), and last the optional LLM generator.

    A shared entry and a stored generated calculator are verified (sha256, contract) before they bind; a failing one
    is skipped with a warning and never reaches an assembled script. ``blocked`` (load_blocked) holds the rejected
    and retired rows of the project: such a property is unsupported without a generator call until an explicit
    regenerate, and a source whose sha256 the project rejected is never bound, whatever its origin."""
    import property_calculator_store

    shared = shared or {}
    blocked = blocked or {}
    warnings: list[str] = []
    if not rules:
        raise PropertyScriptError("NO_RULES", "The project has no rules with DataProperty atoms to compute")
    classes = sorted({(c["iri"], c["label"]) for r in rules for c in r["classes"]})
    if len(classes) != 1:
        raise PropertyScriptError(
            "BOX_CLASS_AMBIGUOUS",
            f"The rules must test exactly one element class; found {[c[1] for c in classes] or 'none'}")
    box_label = local_name(classes[0][1])
    stored = stored or {}
    rules_by_dp: dict[str, list[dict]] = {}
    for rule in rules:
        for dp in rule["dataProperties"]:
            rules_by_dp.setdefault(dp["iri"], []).append(rule)
    resolved: list[dict] = []
    unsupported: list[dict] = []
    fresh: dict[str, dict] = {}
    for rule in rules:
        for dp in sorted(rule["dataProperties"], key=lambda d: d["iri"]):
            # The vetted catalogue wins whenever it covers the property, so a catalogue fix (or a wording variant
            # now matched to the vocabulary) replaces an earlier stored binding, generated ones included. A stored
            # calculator is reused as is only for properties the catalogue does not cover.
            binding = fresh.get(dp["iri"])
            if binding is None:
                binding = resolve_property(dp, catalogue, chooser)
                if binding is not None:
                    previous = stored.get(dp["iri"])
                    same = (previous is not None and previous.get("origin") == "catalogue"
                            and previous.get("calculator") == binding["calculator"]
                            and (previous.get("params") or {}) == binding["params"])
                    binding = {**binding, "origin": "catalogue", "new": not same}
            if binding is None:
                entry = shared.get(property_calculator_store.property_key(dp["iri"]))
                if entry is not None:
                    if property_calculator_store.rejected_source(blocked, dp["iri"], entry.get("sha256")):
                        warnings.append(f"company calculator {entry.get('catalogueId')} for {local_name(dp['iri'])} "
                                        "skipped: this project rejected that source")
                    else:
                        binding = _from_shared(entry, catalogue, stored.get(dp["iri"]), warnings)
            if binding is None and dp["iri"] in stored:
                binding = _from_stored(stored[dp["iri"]], catalogue, warnings, blocked, dp["iri"])
            block = blocked.get(dp["iri"])
            if binding is None and property_calculator_store.is_blocked(block):
                unsupported.append({"ruleId": rule["ruleId"], "dataPropertyIri": dp["iri"],
                                    "dataPropertyLabel": dp["label"],
                                    "reason": f"{block.get('status')}: {block.get('reason') or 'no reason given'}"})
                continue
            if binding is None and generator is not None:
                request_dp = dp
                if block and block.get("regenerate") and block.get("status") == property_calculator_store.STATUS_REJECTED:
                    request_dp = {**dp, "rejectedReason": block.get("reason") or "rejected by the operator"}
                answer = generator(request_dp, rules_by_dp[dp["iri"]], box_label)
                if answer.get("status") == "ok":
                    digest = hashlib.sha256(answer["source"].encode("utf-8")).hexdigest()
                    if property_calculator_store.rejected_source(blocked, dp["iri"], digest):
                        unsupported.append({"ruleId": rule["ruleId"], "dataPropertyIri": dp["iri"],
                                            "dataPropertyLabel": dp["label"],
                                            "reason": "regenerated source was already rejected"})
                        continue
                    binding = {"calculator": f"generated:{digest[:10]}", "params": {}, "resolvedBy": "llm",
                               "origin": "generated", "function": answer["function"], "source": answer["source"],
                               "sha256": digest, "provider": answer.get("provider"), "model": answer.get("model"),
                               "unit": answer.get("unit") or None, "explanation": answer.get("explanation"),
                               "reviewStatus": "pending", "new": True}
                else:
                    unsupported.append({"ruleId": rule["ruleId"], "dataPropertyIri": dp["iri"],
                                        "dataPropertyLabel": dp["label"],
                                        "reason": f"generation {answer.get('status')}: {answer.get('error', '')}"})
                    continue
            if binding is None:
                unsupported.append({"ruleId": rule["ruleId"], "dataPropertyIri": dp["iri"],
                                    "dataPropertyLabel": dp["label"], "reason": "no catalogue calculator"})
                continue
            fresh[dp["iri"]] = binding
            resolved.append({
                "ruleId": rule["ruleId"],
                "dataPropertyIri": dp["iri"],
                "dataPropertyLabel": local_name(dp["label"]),
                **binding,
            })
    return {"boxClass": {"iri": classes[0][0], "label": box_label},
            "resolved": resolved, "unsupported": unsupported, "warnings": list(dict.fromkeys(warnings))}


def _py_literal(value: Any) -> str:
    """A Python literal for JSON-like data (deterministic: sorted keys, no LLM text outside values)."""
    return json.dumps(value, sort_keys=True, ensure_ascii=False, indent=4).replace(": true", ": True").replace(
        ": false", ": False").replace(": null", ": None")


def assemble(project: str, resolution: dict, catalogue: dict) -> dict:
    resolved = resolution["resolved"]
    if not resolved:
        raise PropertyScriptError("NOTHING_TO_COMPUTE", "No rule DataProperty resolved to a catalogue calculator")
    used = sorted({r["calculator"] for r in resolved})
    generated = {r["calculator"]: r for r in resolved if r.get("origin") == "generated"}
    blocks = []
    function_of = {}
    for c in used:
        if c in generated:
            blocks.append(f"# generated calculator {c} (stored; provider {generated[c].get('provider') or '-'})\n"
                          + generated[c]["source"].rstrip())
            function_of[c] = generated[c]["function"]
        else:
            blocks.append(_template_text(catalogue, catalogue["calculators"][c]["template"]).rstrip())
            function_of[c] = catalogue["calculators"][c]["function"]
    functions = "\n\n".join(blocks)
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
        category_classes=_py_literal(dict(sorted(catalogue.get("categoryClasses", {}).items()))),
        calculators=functions,
        calculator_functions="{" + ", ".join(f'"{c}": {function_of[c]}' for c in used) + "}",
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
        "outputs": ["Objects", "Geometry", "Labels", "UniqueIds", "RuleIds", "Report", "Context", "ContextLabels"]
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


BOX_FAMILY_FILTER_DEFAULT = "Box"


def placement_plan(project: str, property_count: int) -> dict:
    """Components, positions and wires of the checking chain; executed by the LISTENER command
    place_property_script. CONNECTOR is reused from the canvas (the user signs in there)."""
    col = [0, 260, 520, 780, 1040, 1300]
    components: list[dict] = [
        {"key": "connector", "kind": "dg", "type": "CONNECTOR", "reuse": True, "required": True},
        # METAGRAPH reads a MetagraphHandle, which GRAPH DECONSTRUCT splits out of CONNECTOR.Database (live
        # 2026-10-20: "Could not unwrap MetagraphHandle" when Database was wired straight in).
        {"key": "graphdecon", "kind": "dg", "type": "GRAPH DECONSTRUCT", "reuse": True, "x": col[0] - 220, "y": -260},
        {"key": "metagraph", "kind": "dg", "type": "METAGRAPH", "reuse": True, "x": col[0], "y": -260},
        {"key": "run", "kind": "toggle", "nickname": "Run", "value": False, "x": col[0] - 200, "y": 0},
        # Default "Box": the opening-box families (BoxПерекрытиеПрямоугольный, BoxСтенаПрямоугольный); other Generic
        # Models such as "котлован" / "засыпка" are not boxes (live 2026-10-21). Editable on the canvas.
        {"key": "filter", "kind": "panel", "nickname": "BoxFamilyFilter", "text": BOX_FAMILY_FILTER_DEFAULT,
         "x": col[0] - 200, "y": 60},
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
        ["connector.Database", "graphdecon.Database"],
        ["graphdecon.Metagraph", "metagraph.Metagraph"],
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


def _saved(outcome: Any, entry: dict, warnings: list[str]) -> bool:
    """True unless the store refused the save (a source the project rejected); a refusal becomes a warning."""
    if isinstance(outcome, dict) and outcome.get("saved") is False:
        warnings.append(f"calculator for {local_name(entry['dataPropertyIri'])} was not stored: "
                        f"{outcome.get('reason') or 'refused'}")
        return False
    return True


def ensure_rule_classes(session: Any, project: str, catalogue: dict | None = None,
                        generator: Generator | None = None, actor: str | None = None) -> dict:
    """Owner 2026-10-20: DG creates every class a rule takes part in when the rule is created. The rule ingest
    writes the classes its atoms name (OpeningBox); a class the rule only implies through its property
    ("no openings in columns" -> hasColumnIntersectionCount -> Column) is created here, together with the
    property's calculator. Runs per element class, so a project whose rules test several classes is fine.
    Never raises for rules it cannot resolve; returns what it created and what stayed unsupported."""
    import property_calculator_store

    catalogue = catalogue or load_catalogue()
    rules = load_rules(session, project, None)
    stored = property_calculator_store.load_active(session, project)
    company = property_calculator_store.company_of(project)
    shared = property_calculator_store.load_catalogue(session, company)
    blocked = property_calculator_store.load_blocked(session, project)
    warnings: list[str] = []
    by_class: dict[tuple, list[dict]] = {}
    for rule in rules:
        if len(rule["classes"]) == 1 and rule["dataProperties"]:
            by_class.setdefault((rule["classes"][0]["iri"], rule["classes"][0]["label"]), []).append(rule)
    created: list[dict] = []
    unsupported: list[dict] = []
    for (class_iri, _label), group in sorted(by_class.items()):
        resolution = resolve(group, catalogue, None, stored=stored, generator=generator, shared=shared,
                             blocked=blocked)
        warnings.extend(resolution["warnings"])
        prefix = iri_prefix_of(class_iri)
        done = set()
        for entry in resolution["resolved"]:
            if entry["dataPropertyIri"] in done:
                continue
            done.add(entry["dataPropertyIri"])
            classes = context_classes(entry, catalogue, prefix)
            if entry.get("new"):
                if _saved(property_calculator_store.save(session, project, entry, actor), entry, warnings):
                    stored[entry["dataPropertyIri"]] = entry
            property_calculator_store.save_context_classes(session, project, entry["dataPropertyIri"], classes)
            created.append({"ruleId": entry["ruleId"], "dataPropertyIri": entry["dataPropertyIri"],
                            "classes": [c["label"] for c in classes]})
        unsupported.extend(resolution["unsupported"])
    pruned = property_calculator_store.prune_context_classes(session, project)
    import class_duplicates

    return {"project": project, "linked": created, "unsupported": unsupported, "prunedClasses": pruned,
            "duplicateCandidates": class_duplicates.find(session, project),
            "warnings": list(dict.fromkeys(warnings))}


def generate(session: Any, project: str, rule_ids: list[str] | None, chooser: Chooser | None = None,
             catalogue: dict | None = None, generator: Generator | None = None, store: bool = False,
             actor: str | None = None) -> dict:
    """Scripts for the project's current rules. With ``store`` the new bindings (catalogue or LLM-generated) are
    saved, so the next generation reuses them; without it nothing is written (preview)."""
    import property_calculator_store

    catalogue = catalogue or load_catalogue()
    rules = load_rules(session, project, rule_ids)
    stored = property_calculator_store.load_active(session, project)
    company = property_calculator_store.company_of(project)
    shared = property_calculator_store.load_catalogue(session, company)
    blocked = property_calculator_store.load_blocked(session, project)
    resolution = resolve(rules, catalogue, chooser, stored=stored, generator=generator, shared=shared,
                         blocked=blocked)
    warnings = list(resolution["warnings"])
    if resolution["unsupported"] and not resolution["resolved"]:
        raise PropertyScriptError("NOTHING_TO_COMPUTE", "No rule DataProperty resolved to a catalogue calculator")
    prefix = iri_prefix_of(resolution["boxClass"]["iri"])
    for entry in resolution["resolved"]:
        entry["contextClasses"] = context_classes(entry, catalogue, prefix)
    if store:
        saved = set()
        for entry in resolution["resolved"]:
            if entry["dataPropertyIri"] in saved:
                continue
            if entry.get("new"):
                _saved(property_calculator_store.save(session, project, entry, actor), entry, warnings)
            property_calculator_store.save_context_classes(session, project, entry["dataPropertyIri"],
                                                           entry["contextClasses"])
            saved.add(entry["dataPropertyIri"])
        property_calculator_store.prune_context_classes(session, project)
    for entry in resolution["resolved"]:
        entry.pop("new", None)
    scripts = assemble(project, resolution, catalogue)
    return {
        "project": project,
        "catalogueVersion": catalogue["version"],
        "boxClass": resolution["boxClass"],
        "resolved": resolution["resolved"],
        "unsupported": resolution["unsupported"],
        "warnings": list(dict.fromkeys(warnings)),
        **scripts,
    }
