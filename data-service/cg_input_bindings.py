"""Input Generation Bindings -- JOIN B (Phase 38: GHIN-01).

This module resolves two questions about a Metagraph Rule, and answers
neither by guessing:

1. *Which* Computgraph parameters does the rule actually constrain?
2. *Is* the rule's numeric limit checkable from those parameters alone, or
   does checking it require geometry this system never evaluated?

It reads the rule's numeric threshold from the one place it is authored --
the Rule's SWRL ``Literal`` atom, via a single parameterized read query --
and it authors no threshold of its own. The declarative ``inputBindings``
artifact this module loads (a new sibling top-level key in
``llm/structure_rules.json``) is a *selector* (which parameters, what kind of
determinability), never a *value* -- the same value-threshold fence
``cg_structure_checks._FORBIDDEN_PARAM_KEYS`` established for
``mappings[].params`` is re-applied here to ``inputBindings[]`` entries
(``_FORBIDDEN_BINDING_KEYS``). See
``spec/RULE-PARTITION-POLICY.md``'s "Input Generation Bindings (Phase 38)"
addendum for the normative schema this loader validates against.

Determinability can only ever be under-claimed: a rule with no binding
entry -- or a binding whose class is ``geometry-required`` -- always carries
``limit=None`` downstream, regardless of what ``read_rule_limit`` found on
the graph. This is the structural mechanism (not a prompt instruction) that
keeps the generator from ever claiming a geometry-dependent rule is
satisfied (D-09).
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from cg_structure_checks import STRUCTURE_RULES_FILE as _STRUCTURE_RULES_FILE

logger = logging.getLogger(__name__)

# The three determinability classes an inputBindings entry (or the default)
# may carry. "geometry-required" is the safe default for an unmapped rule --
# it can only ever under-claim (D-08).
DETERMINABILITY_CLASSES: frozenset[str] = frozenset(
    {"direct-parameter", "monotone-bound", "geometry-required"}
)

# Value-threshold keys forbidden at any nesting level of an inputBindings
# entry. Mirrors cg_structure_checks._FORBIDDEN_PARAM_KEYS' fence and
# spec/RULE-PARTITION-POLICY.md's "Input Generation Bindings (Phase 38)"
# scope fence: a binding selects parameters and determinability only -- a
# numeric limit, comparison operator, or threshold value is SWRL scope and
# must be expressed by editing the Rule's SWRL Literal instead (D-10).
_FORBIDDEN_BINDING_KEYS: frozenset[str] = frozenset(
    {"min", "max", "threshold", "value", "limit", "operator"}
)


class InputBindingError(ValueError):
    """Raised for an ``inputBindings`` entry that IS present but malformed.

    Absence -- of the file, the key, or a mapping for a given rule -- is
    never an error; it degrades to the safe ``geometry-required`` default. A
    present-but-wrong-shaped entry IS an error, because it would otherwise
    silently change which parameters get generated for.
    """


def _find_forbidden_key(node: Any) -> str | None:
    """Return the first forbidden key found anywhere inside `node` (any
    nesting level of dict/list), or None if none is present."""
    if isinstance(node, dict):
        for key, value in node.items():
            if key in _FORBIDDEN_BINDING_KEYS:
                return key
            found = _find_forbidden_key(value)
            if found is not None:
                return found
    elif isinstance(node, list):
        for item in node:
            found = _find_forbidden_key(item)
            if found is not None:
                return found
    return None


def _reject(rule_id: str, what: str, how_to_fix: str) -> None:
    raise InputBindingError(
        f"{what} Where: llm/structure_rules.json inputBindings[ruleId={rule_id!r}]. "
        f"How to fix: {how_to_fix}"
    )


def _validate_binding_entry(entry: Any, already_seen: dict[str, dict[str, Any]]) -> None:
    """Raise InputBindingError for any shape violation in one inputBindings
    entry. Absence of the whole array/file is handled by the caller before
    this is ever invoked -- this function only runs against entries that
    exist."""
    if not isinstance(entry, dict):
        raise InputBindingError(
            "An inputBindings entry is malformed: expected a JSON object. "
            f"Where: llm/structure_rules.json inputBindings[]. Entry was {entry!r}. "
            "How to fix: each entry must be an object carrying at least ruleId and determinability."
        )

    rule_id = entry.get("ruleId")
    if not isinstance(rule_id, str) or not rule_id:
        raise InputBindingError(
            "An inputBindings entry is malformed: ruleId is missing or not a non-empty string. "
            f"Where: llm/structure_rules.json inputBindings[]. Entry was {entry!r}. "
            "How to fix: set ruleId to the Metagraph Rule_Id this binding maps."
        )

    forbidden_key = _find_forbidden_key(entry)
    if forbidden_key is not None:
        _reject(
            rule_id,
            f"Entry contains forbidden value-threshold key {forbidden_key!r}.",
            "a binding selects parameters and determinability only -- express a numeric "
            "limit by editing the Rule's SWRL Literal instead, never here.",
        )

    if rule_id in already_seen:
        _reject(
            rule_id,
            "Duplicate ruleId in inputBindings -- last-wins is not permitted.",
            "remove or merge the duplicate entry so each ruleId appears at most once.",
        )

    determinability = entry.get("determinability")
    if determinability not in DETERMINABILITY_CLASSES:
        _reject(
            rule_id,
            f"determinability {determinability!r} is not a recognized class.",
            f"set determinability to one of {sorted(DETERMINABILITY_CLASSES)}.",
        )

    parameters = entry.get("parameters")
    if (
        not isinstance(parameters, list)
        or not parameters
        or not all(isinstance(p, str) and p for p in parameters)
    ):
        _reject(
            rule_id,
            "parameters is missing, empty, or contains a non-string/empty entry.",
            "set parameters to a non-empty list of non-empty parameter-name strings.",
        )

    metric_expression = entry.get("metricExpression")
    monotone_in = entry.get("monotoneIn")
    if determinability == "monotone-bound":
        if not isinstance(metric_expression, str) or not metric_expression:
            _reject(
                rule_id,
                "determinability is monotone-bound but metricExpression is missing or empty.",
                "set metricExpression to the expression relating the constrained metric to parameters.",
            )
        if (
            not isinstance(monotone_in, list)
            or not monotone_in
            or not all(isinstance(m, str) and m for m in monotone_in)
        ):
            _reject(
                rule_id,
                "determinability is monotone-bound but monotoneIn is missing, empty, or malformed.",
                "set monotoneIn to the non-empty subset of parameters the metric is provably "
                "monotone increasing in.",
            )
        if not set(monotone_in).issubset(set(parameters)):
            _reject(
                rule_id,
                "monotoneIn contains a name absent from parameters.",
                "monotoneIn must be a subset of parameters.",
            )
    elif metric_expression or monotone_in:
        _reject(
            rule_id,
            f"metricExpression/monotoneIn are set but determinability is {determinability!r}, "
            "not monotone-bound.",
            "only a monotone-bound entry may carry metricExpression/monotoneIn.",
        )


def load_input_bindings(path: str | Path | None = None) -> dict[str, dict[str, Any]]:
    """Read the ``inputBindings`` array from ``llm/structure_rules.json`` (or
    an explicit override `path`, for tests) and return it as a dict keyed by
    ``ruleId``.

    Resolves the default path exactly the way
    ``cg_structure_checks.load_structure_rules()`` does -- literally reusing
    its ``STRUCTURE_RULES_FILE`` constant -- so the two loaders can never
    diverge on which file they read (D-07).

    Never raises for absence: a missing file, an unreadable file, invalid
    JSON, a payload that isn't an object, or a missing/non-list
    ``inputBindings`` key all return ``{}``. A missing binding for a given
    rule is the safe direction (the rule defaults to ``geometry-required``
    downstream) so there is nothing to raise about.

    Raises ``InputBindingError`` for a malformed entry that IS present --
    absence is fine, a wrong shape is not, because it silently changes which
    parameters get generated for.
    """
    resolved = Path(path) if path is not None else _STRUCTURE_RULES_FILE
    if not resolved.exists():
        return {}
    try:
        payload = json.loads(resolved.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    if not isinstance(payload, dict):
        return {}
    raw_bindings = payload.get("inputBindings")
    if not isinstance(raw_bindings, list):
        return {}

    bindings: dict[str, dict[str, Any]] = {}
    for entry in raw_bindings:
        _validate_binding_entry(entry, bindings)
        bindings[entry["ruleId"]] = entry
    return bindings


def binding_for_rule(bindings: dict[str, dict[str, Any]], rule_id: str) -> dict[str, Any] | None:
    """Plain lookup. Returns None for a rule absent from `bindings` -- the
    caller (classify_rule) is what turns that None into the geometry-required
    default; this function makes no policy decision of its own."""
    return bindings.get(rule_id)


# ── SWRL threshold extraction ──


@dataclass(frozen=True)
class RuleLimit:
    """The numeric constraint a candidate must respect, decoded from a
    Rule's violation-inverted SWRL body atom."""

    operator: str
    value: float
    datatype: str
    variableName: str


# Violation-inverted body semantics (cypher_template.txt's SEMANTIC MAPPING
# section): the body atom fires when the constraint is VIOLATED, so the
# constraint the candidate must satisfy is the logical inverse of the body
# builtin's own comparison.
#   "maximum X"  -> body swrlb:greaterThan(?v, X)  -> constraint v <= X
#   "minimum X"  -> body swrlb:lessThan(?v, X)      -> constraint v >= X
#   "equal to X" -> body swrlb:notEqual(?v, X)       -> constraint v == X
# The inclusive forms are decoded too, so a rule ingested with an inclusive
# body comparison is not silently unmatched:
#   body swrlb:greaterThanOrEqual(?v, X) -> constraint v < X
#   body swrlb:lessThanOrEqual(?v, X)     -> constraint v > X
BODY_BUILTIN_TO_CONSTRAINT: dict[str, str] = {
    "swrlb:greaterThan": "<=",
    "swrlb:lessThan": ">=",
    "swrlb:notEqual": "==",
    "swrlb:greaterThanOrEqual": "<",
    "swrlb:lessThanOrEqual": ">",
}


class RuleNotFoundError(ValueError):
    """Raised when no Rule node with the given Rule_Id exists in the given
    project. The caller (a route handler) maps this onto 422
    COMPUTGRAPH_GENERATE_INPUTS_RULE_NOT_FOUND."""


def read_rule_limit(session: Any, rule_id: str, project: str) -> RuleLimit | None:
    """Recover the numeric limit a candidate must respect from the Rule's own
    SWRL atoms -- one parameterized, read-only Cypher call, never a write.

    Resolution rules:
    - No Rule node with this Rule_Id in this project -> raises
      RuleNotFoundError.
    - Rule exists but has no comparison BuiltinAtom -> returns None (not an
      error -- the rule simply has nothing for a sampler to bound against).
    - Exactly one comparison BuiltinAtom whose iri is recognized and whose
      pos-2 argument is a Literal parsing to a float -> returns the RuleLimit
      with the inverted operator.
    - More than one such atom -> returns None and logs one warning. A
      conjunction of bounds is legitimate SWRL, but this phase samples
      against a single limit; honouring only the first would be exactly the
      overclaim D-09 forbids, so the rule is demoted to unbounded sampling.
    - A pos-2 argument that is a Var (not a Literal), or a lex that does not
      parse as a float -> None with a warning.
    """
    result = session.run(
        """
        MATCH (r:Rule {Rule_Id: $ruleId, project: $project})
        OPTIONAL MATCH (r)-[hb:HAS_BODY]->(a:Atom {type: 'BuiltinAtom'})
        OPTIONAL MATCH (a)-[:ARG {`pos`: 1}]->(vArg:Var)
        OPTIONAL MATCH (a)-[:ARG {`pos`: 2}]->(litArg:Literal)
        RETURN a.iri AS builtinIri, hb.`order` AS bodyOrder,
               vArg.name AS variableName, litArg.lex AS lex, litArg.datatype AS datatype
        ORDER BY bodyOrder
        // op=READ_RULE_LIMIT
        """,
        {"ruleId": rule_id, "project": project},
    )
    rows = list(result)
    if not rows:
        raise RuleNotFoundError(
            f"No Rule node found for Rule_Id {rule_id!r} in project {project!r}."
        )

    comparisons: list[RuleLimit] = []
    for row in rows:
        builtin_iri = row.get("builtinIri")
        if not builtin_iri or builtin_iri not in BODY_BUILTIN_TO_CONSTRAINT:
            continue
        variable_name = row.get("variableName")
        lex = row.get("lex")
        if not variable_name or lex is None:
            logger.warning(
                "Rule %s has a comparison BuiltinAtom %s whose pos-2 argument is not a "
                "Literal with a value; demoting to unbounded.",
                rule_id,
                builtin_iri,
            )
            continue
        try:
            value = float(lex)
        except (TypeError, ValueError):
            logger.warning(
                "Rule %s has a comparison BuiltinAtom %s whose Literal lex %r does not "
                "parse as a float; demoting to unbounded.",
                rule_id,
                builtin_iri,
                lex,
            )
            continue
        comparisons.append(
            RuleLimit(
                operator=BODY_BUILTIN_TO_CONSTRAINT[builtin_iri],
                value=value,
                datatype=row.get("datatype") or "",
                variableName=variable_name,
            )
        )

    if not comparisons:
        return None
    if len(comparisons) > 1:
        logger.warning(
            "Rule %s has %d competing comparison BuiltinAtoms; demoting to unbounded "
            "sampling rather than honouring only the first.",
            rule_id,
            len(comparisons),
        )
        return None
    return comparisons[0]


# ── Determinability classification and parameter selection ──


@dataclass(frozen=True)
class RuleClassification:
    """The answer to "which parameters, and is the limit checkable from them
    alone" for one Rule, at one call."""

    ruleId: str
    determinability: str
    parameterNames: tuple[str, ...]
    metricExpression: str | None
    monotoneIn: tuple[str, ...]
    limit: RuleLimit | None
    source: str


def classify_rule(
    session: Any,
    rule_id: str,
    project: str,
    bindings: dict[str, dict[str, Any]],
    parameter_overrides: list[str] | None = None,
) -> RuleClassification:
    """Classify one Rule's determinability and parameter scope.

    Calls read_rule_limit first, so RuleNotFoundError surfaces before any
    binding lookup is attempted. A rule absent from `bindings` classifies as
    geometry-required with an empty parameter list and source="default" --
    the safe direction (D-08). `parameter_overrides`, when non-empty, replaces
    *which* parameters are in scope (source="override") but never changes the
    determinability class itself: an architect may say which sliders matter,
    but cannot declare a geometry-level rule checkable (D-06).

    limit is forced to None whenever determinability is geometry-required,
    regardless of what read_rule_limit found -- the single line that makes
    D-09 structural rather than aspirational.
    """
    limit = read_rule_limit(session, rule_id, project)
    binding = binding_for_rule(bindings, rule_id)

    if binding is None:
        return RuleClassification(
            ruleId=rule_id,
            determinability="geometry-required",
            parameterNames=(),
            metricExpression=None,
            monotoneIn=(),
            limit=None,
            source="default",
        )

    determinability = binding["determinability"]
    parameter_names = tuple(binding["parameters"])
    metric_expression = binding.get("metricExpression")
    monotone_in = tuple(binding.get("monotoneIn") or ())
    source = "binding"

    if parameter_overrides:
        parameter_names = tuple(parameter_overrides)
        source = "override"

    if determinability == "geometry-required":
        limit = None

    return RuleClassification(
        ruleId=rule_id,
        determinability=determinability,
        parameterNames=parameter_names,
        metricExpression=metric_expression,
        monotoneIn=monotone_in,
        limit=limit,
        source=source,
    )


# Computgraph Parameter.dataType -> ParamState value-slot type mapping.
_DATATYPE_TO_STATE_TYPE: dict[str, str] = {
    "Float": "Number",
    "Integer": "Integer",
    "Boolean": "Boolean",
}
_SUPPORTED_DATATYPES: frozenset[str] = frozenset(_DATATYPE_TO_STATE_TYPE)


def _exclusion_reason(parameter: dict[str, Any]) -> str | None:
    """The one reason (if any) a considered published parameter is excluded.
    Order matches spec/API.md's excludedParameters[].reason vocabulary walk:
    kind, then datatype, then domain, then reinstate-id resolvability. A
    Boolean parameter has no numeric domain by nature and is explicitly
    exempted from the domain check rather than relying on check ordering."""
    if parameter.get("paramKind") != "Variable":
        return "non-variable-kind"
    data_type = parameter.get("dataType")
    if data_type not in _SUPPORTED_DATATYPES:
        return "unsupported-datatype"
    if data_type != "Boolean" and (
        parameter.get("domainMin") is None or parameter.get("domainMax") is None
    ):
        return "missing-domain"
    reinstate_id = parameter.get("reinstateParameterId")
    if not reinstate_id or not str(reinstate_id).strip():
        return "unresolved-reinstate-id"
    return None


def select_parameters(
    classification: RuleClassification, published_parameters: list[dict[str, Any]]
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """Partition the published :Parameter rows into (bound, excluded) for one
    classified rule.

    When classification.parameterNames is non-empty, only parameters whose
    parameterName matches are considered -- the rest are simply out of scope
    and appear in neither list. When parameterNames is empty (the
    geometry-required default), every eligible published parameter is
    considered -- a geometry rule still gets candidates, it just never gets a
    satisfaction claim (that guarantee lives in classify_rule's limit=None,
    not here).

    Each excluded entry carries {cgId, parameterName, reason}. Each bound
    entry carries the full published row plus a stateType field holding the
    mapped ParamState type. Both lists are sorted by parameterName for
    deterministic responses.
    """
    if classification.parameterNames:
        name_filter = set(classification.parameterNames)
        considered = [p for p in published_parameters if p.get("parameterName") in name_filter]
    else:
        considered = list(published_parameters)

    bound: list[dict[str, Any]] = []
    excluded: list[dict[str, Any]] = []

    for parameter in considered:
        reason = _exclusion_reason(parameter)
        if reason is not None:
            excluded.append(
                {
                    "cgId": parameter.get("cgId"),
                    "parameterName": parameter.get("parameterName"),
                    "reason": reason,
                }
            )
            continue
        bound.append({**parameter, "stateType": _DATATYPE_TO_STATE_TYPE[parameter["dataType"]]})

    if classification.parameterNames:
        # WR-02: a name in parameterNames (from the rule's inputBindings
        # entry, or an architect-supplied parameterOverrides list) that
        # matches no published :Parameter row produces no row in
        # `considered` at all, so it never reaches `_exclusion_reason()`
        # and silently vanishes from both bound[] and excluded[] -- surface
        # it explicitly instead, matching this module's "never silently
        # drop" discipline.
        found_names = {p.get("parameterName") for p in considered}
        for missing_name in sorted(name_filter - found_names):
            excluded.append(
                {
                    "cgId": None,
                    "parameterName": missing_name,
                    "reason": "not-published",
                }
            )

    bound.sort(key=lambda p: p.get("parameterName") or "")
    excluded.sort(key=lambda p: p.get("parameterName") or "")
    return bound, excluded
