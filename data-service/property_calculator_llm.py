"""LLM-generated property calculators for rule DataProperties the catalogue does not cover (Phase 1303-15).

Owner requirement 2026-10-20: scripts must be generated for any new rule. The vetted catalogue stays the first
choice; for a property it does not cover, the active LLM provider writes ONE Python function under a fixed contract
(``def calc_gen(ctx, box, params)`` returning a number), using only the read-only model helpers of the calculator
shell. The answer is accepted only when ``validate_function`` passes: a single function, no imports, no
transactions, no Revit write calls, no dunder access, only allowed global names. The accepted source is stored
(property_calculator_store) and reused byte-for-byte afterwards, so the LLM is asked once per property.
"""

from __future__ import annotations

import ast
import hashlib
import json
import logging
import os
import re
import sys
from typing import Any, Mapping, Optional

import llm_gateway

MAX_TOKENS = 1800
TIMEOUT_S = 90
FUNCTION_NAME = "calc_gen"
# finalize() stores a generated calculator as calc_gen_<first 10 hex of the sha256 of the normalized source>.
GENERATED_NAME = re.compile(r"^calc_gen_[0-9a-f]{10}$")

# Phase 1303-16 (D-55): every LLM generation request writes one visible line. data-service configures no root
# logging and uvicorn only its own loggers, so this logger carries its own stderr handler (added once, also after a
# reload) or the line would never reach `docker logs`. The record names the DataProperty IRI only.
_GENERATION_LOG = logging.getLogger("dg.property_calculator_generation")
_GENERATION_LOG.setLevel(logging.INFO)
if not any(getattr(h, "_dg_generation", False) for h in _GENERATION_LOG.handlers):
    _generation_handler = logging.StreamHandler(sys.stderr)
    _generation_handler._dg_generation = True  # type: ignore[attr-defined]
    _generation_handler.setFormatter(logging.Formatter("%(asctime)s %(name)s %(message)s"))
    _GENERATION_LOG.addHandler(_generation_handler)

ALLOWED_GLOBALS = frozenset({
    # shell helpers and constants
    "DB", "math", "TOL_FT", "FEET_TO_MM", "element_solids", "bbox_corners", "List",
    # safe builtins
    "len", "min", "max", "sum", "abs", "round", "float", "int", "bool", "str", "sorted", "range", "enumerate",
    "zip", "list", "tuple", "set", "dict", "isinstance", "any", "all", "None", "True", "False", "ValueError",
    "Exception",
})
FORBIDDEN_ATTRIBUTES = frozenset({
    "Set", "SetValue", "Delete", "Create", "NewFamilyInstance", "Regenerate", "SetElementOverrides",
    "Move", "Rotate", "Mirror", "Copy", "ChangeTypeId", "Start", "Commit", "RollBack", "Assimilate",
    "Transaction", "SubTransaction", "TransactionGroup", "Document", "Application", "OpenSharedParameterFile",
    "SaveAs", "Save", "Close", "Export", "Import", "Insert", "ReInsert", "Remove", "Clear", "Add",
})
FORBIDDEN_NODES = (ast.Import, ast.ImportFrom, ast.Global, ast.Nonlocal, ast.ClassDef, ast.AsyncFunctionDef,
                   ast.With, ast.AsyncWith, ast.Await, ast.Yield, ast.YieldFrom, ast.Delete)

SYSTEM = (
    "You write one Python 3 function for Design Grammars that computes a numeric property of a Revit element "
    "read through Rhino.Inside.Revit. Answer with JSON only: {\"function\": \"<python source>\", \"unit\": "
    "\"<unit>\", \"explanation\": \"<one sentence>\"}. The function must be named calc_gen, take (ctx, box, params), "
    "only READ the model and return an int or float. No imports, no transactions, no writes, no printing."
)

CONTEXT_API = """Available inside calc_gen (nothing else exists):
- box: the Revit FamilyInstance being checked (an opening box, Generic Model). Revit internal units are feet.
- ctx.doc: the active Revit Document (read only).
- ctx.solids(box) -> [Autodesk.Revit.DB.Solid] of the box.
- ctx.intersecting(box, ["OST_StructuralFraming", ...]) -> elements of these BuiltInCategory names whose solid intersects the box.
- ctx.host_walls(box) -> walls the box intersects.
- ctx.wall_frame(wall) -> (origin XYZ, unit direction XYZ along the wall) or None.
- ctx.rect_in_wall(element, frame) -> (u0, u1, z0, z1) bounding rectangle in the wall plane, feet.
- ctx.wall_openings(wall, ["OST_Doors", "OST_Windows", "OST_SWallRectOpening"]) -> openings hosted in the wall.
- ctx.box_and_openings_in_walls(box, categories) -> [(box_rect, [opening_rect, ...])] per host wall.
- element_solids(element), bbox_corners(element) -> solids / 8 bounding-box corners (XYZ).
- DB: Autodesk.Revit.DB (read-only use: FilteredElementCollector, BuiltInCategory, XYZ, Outline, filters).
- math, TOL_FT (1 mm in feet), FEET_TO_MM (304.8).
- params: dict, empty unless you need none.
Return lengths in the unit the property name states (Mm = millimetres, M = metres); counts as int."""


class GeneratedCalculatorError(ValueError):
    pass


def validate_function(source: str, name: str = FUNCTION_NAME) -> str:
    """Return the normalized source when it satisfies the contract, else raise GeneratedCalculatorError.

    ``name`` is the function name the source must define: ``calc_gen`` for an LLM answer, ``calc_gen_<hex>`` for a
    stored (finalized) source."""
    try:
        tree = ast.parse(source)
    except SyntaxError as exc:
        raise GeneratedCalculatorError(f"not valid Python: {exc.msg}") from exc
    body = [n for n in tree.body if not (isinstance(n, ast.Expr) and isinstance(getattr(n, "value", None), ast.Constant))]
    if len(body) != 1 or not isinstance(body[0], ast.FunctionDef) or body[0].name != name:
        raise GeneratedCalculatorError(f"the answer must be exactly one function named {name}")
    fn = body[0]
    if [a.arg for a in fn.args.args] != ["ctx", "box", "params"] or fn.args.vararg or fn.args.kwarg:
        raise GeneratedCalculatorError(f"{name} must take exactly (ctx, box, params)")
    local_names = {a.arg for a in fn.args.args}
    for node in ast.walk(fn):
        if isinstance(node, (ast.Name, ast.arg)) and isinstance(getattr(node, "ctx", None), ast.Store):
            local_names.add(node.id)
        elif isinstance(node, ast.FunctionDef) and node is not fn:
            local_names.add(node.name)
            local_names.update(a.arg for a in node.args.args)
        elif isinstance(node, ast.Lambda):
            local_names.update(a.arg for a in node.args.args)
        elif isinstance(node, ast.comprehension):
            for t in ast.walk(node.target):
                if isinstance(t, ast.Name):
                    local_names.add(t.id)
        elif isinstance(node, ast.ExceptHandler) and node.name:
            local_names.add(node.name)
    for node in ast.walk(fn):
        if isinstance(node, FORBIDDEN_NODES):
            raise GeneratedCalculatorError(f"forbidden construct: {type(node).__name__}")
        if isinstance(node, ast.Attribute):
            if node.attr.startswith("_"):
                raise GeneratedCalculatorError(f"forbidden attribute: {node.attr}")
            if node.attr in FORBIDDEN_ATTRIBUTES:
                raise GeneratedCalculatorError(f"forbidden model call: {node.attr}")
        if isinstance(node, ast.Name) and isinstance(node.ctx, ast.Load):
            if node.id not in ALLOWED_GLOBALS and node.id not in local_names:
                raise GeneratedCalculatorError(f"name not available to calculators: {node.id}")
        if isinstance(node, ast.Constant) and isinstance(node.value, str) and "__" in node.value:
            raise GeneratedCalculatorError("dunder strings are not allowed")
    return ast.unparse(fn).strip() + "\n"


def categories_in(source: str) -> list[str]:
    """The Revit BuiltInCategory names a calculator reads, taken from its string constants (``"OST_..."``) by AST,
    so the classes DG creates for it never depend on what the LLM claims."""
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []
    return sorted({n.value for n in ast.walk(tree)
                   if isinstance(n, ast.Constant) and isinstance(n.value, str) and re.fullmatch(r"OST_[A-Za-z]+", n.value)})


def finalize(source: str) -> tuple[str, str]:
    """(function name, source) with a content-derived name, so the same function always gets the same name."""
    normalized = validate_function(source)
    digest = hashlib.sha256(normalized.encode("utf-8")).hexdigest()[:10]
    name = f"calc_gen_{digest}"
    return name, re.sub(r"^def calc_gen\(", f"def {name}(", normalized, count=1)


def verify_stored_source(source: Any, function: Any, sha256: Any) -> Optional[str]:
    """None when a stored generated calculator is exactly what ``finalize`` produced, else a short reason.

    Checked before a calculator is promoted into the company catalogue (D-54): the function name, the sha256 of the
    stored bytes, the contract (a re-validation must give back the same bytes, i.e. the source is an ``ast.unparse``
    fixed point) and the content-derived name."""
    if not isinstance(source, str) or not isinstance(function, str) or not isinstance(sha256, str):
        return "calculator source, function or hash is missing"
    if not GENERATED_NAME.match(function):
        return "function name is not calc_gen_<10 hex>"
    if hashlib.sha256(source.encode("utf-8")).hexdigest() != sha256:
        return "source does not match its sha256"
    try:
        normalized = validate_function(source, name=function)
    except GeneratedCalculatorError as exc:
        return f"source fails the contract: {exc}"
    if normalized != source:
        return "source is not the normalized form"
    unnamed = re.sub(r"^def " + re.escape(function) + r"\(", "def calc_gen(", source, count=1)
    if hashlib.sha256(unnamed.encode("utf-8")).hexdigest()[:10] != function[len("calc_gen_"):]:
        return "function name does not match the source digest"
    return None


def participants_block(participants: list[Mapping]) -> str:
    """The "Participants:" block of the prompt (Phase 1303-22, D-62): one line per class the rules relate to the
    element being checked, with the relation that ties it and the Revit categories its elements have."""
    lines = []
    for participant in participants:
        tie = " ".join(str(x) for x in (participant.get("relation"), participant.get("relatedTo")) if x)
        categories = ", ".join(participant.get("revitCategories") or []) or "none known"
        lines.append(f"- {participant.get('label')}: " + (f"{tie}; " if tie else "") + f"Revit categories: {categories}")
    return "Participants:\n" + "\n".join(lines)


def build_prompt(data_property: Mapping, rules: list[Mapping], class_label: str,
                 participants: Optional[list[Mapping]] = None) -> str:
    """The generation prompt. With ``participants`` (the context classes of the rules that test the property) a
    "Participants:" block follows the rules; without them the prompt is byte-identical to the Phase 1303-16 pin."""
    rule_lines = "\n".join(f"- {r.get('ruleId')}: {r.get('text') or ''} | SWRL: {r.get('swrl') or ''}" for r in rules)
    block = f"{participants_block(participants)}\n\n" if participants else ""
    prompt = (
        f"Element class: {class_label}\n"
        f"Property to compute: {data_property.get('label')} ({data_property.get('iri')})\n"
        f"Rules that test it:\n{rule_lines}\n\n{block}{CONTEXT_API}\n"
        "Write calc_gen so that the rules above can be evaluated on this property."
    )
    reason = data_property.get("rejectedReason")
    if reason:
        prompt += (
            "\nThe operator rejected the previous calculator for this property. Reason: "
            f"{str(reason)[:400]}\nWrite a different calculator that avoids this problem."
        )
    return prompt


def _extract_json(text: str) -> Optional[dict]:
    text = (text or "").strip()
    fence = re.search(r"```(?:json)?\s*(\{.*\})\s*```", text, re.S)
    if fence:
        text = fence.group(1)
    start, end = text.find("{"), text.rfind("}")
    if start < 0 or end <= start:
        return None
    try:
        return json.loads(text[start:end + 1])
    except json.JSONDecodeError:
        return None


def generate_calculator(data_property: Mapping, rules: list[Mapping], class_label: str,
                        complete=None) -> dict[str, Any]:
    """Ask the active LLM provider for a calculator; never raises.

    Returns {status: ok | invalid | unavailable, function, source, unit, explanation, provider, model, error}.
    ``complete(prompt, system) -> (text, provider, model)`` replaces the gateway in tests.
    """
    prompt = build_prompt(data_property, rules, class_label, data_property.get("participants"))
    _GENERATION_LOG.info("property calculator LLM generation requested: %s", data_property.get("iri"))
    try:
        if complete is None:
            settings = llm_gateway.load_persisted_llm_settings()
            provider, model, api_key = llm_gateway.resolve_active_provider(settings, os.getenv("LLM_MASTER_SECRET", ""))
            adapter = llm_gateway.get_adapter(provider, settings.get("baseUrl"))
            request = llm_gateway.GenerateRequest(prompt=prompt, system=SYSTEM, model=model, provider=provider)
            response = adapter.generate(request, api_key, options=llm_gateway.GenerationOptions(
                temperature=0.0, max_tokens=MAX_TOKENS, timeout_s=TIMEOUT_S))
            text, provider, model = getattr(response, "text", ""), getattr(response, "provider", provider), getattr(response, "model", model)
        else:
            text, provider, model = complete(prompt, SYSTEM)
    except Exception as exc:  # noqa: BLE001 - generation is optional; the property is then reported unsupported
        try:
            code = llm_gateway.map_provider_error(exc)[2]
        except Exception:  # noqa: BLE001
            code = type(exc).__name__
        return {"status": "unavailable", "error": str(code)[:120]}
    answer = _extract_json(text)
    if not answer or not isinstance(answer.get("function"), str):
        return {"status": "invalid", "error": "the provider did not return {function: ...}", "provider": provider, "model": model}
    try:
        name, source = finalize(answer["function"])
    except GeneratedCalculatorError as exc:
        return {"status": "invalid", "error": str(exc), "provider": provider, "model": model}
    return {
        "status": "ok", "function": name, "source": source,
        "unit": str(answer.get("unit") or "")[:40], "explanation": str(answer.get("explanation") or "")[:400],
        "provider": provider, "model": model, "promptSha256": hashlib.sha256(prompt.encode("utf-8")).hexdigest(),
    }
