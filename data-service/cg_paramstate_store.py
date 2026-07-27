"""Accept-time persistence for AI-generated Grasshopper script inputs (Phase
38: GHIN-02/03/04, D-18/D-19/D-21/D-22).

This module is the **first `:DesignState` writer** in the repository. It is
deliberately its own module, separate from `cg_input_generation`, because
GHIN-04/D-22 require the generation path to have no route to a write at
all: `tests/test_cg_input_boundary.py`'s `ast`-based import-closure walk
asserts `cg_input_generation` does not import this module. Anyone merging
the two breaks a requirement, not a style rule -- "generate a candidate"
and "persist an accepted candidate" are two different trust boundaries
(browser round-trip vs. server-authored write) and must stay two different
call paths.

`accept_candidate()` is the only write path for AI-generated candidates
(D-19): the generate route performs zero writes, and a rejected candidate
leaves no trace in the graph. Before writing anything, it **re-reads the
live published `:Parameter` rows** for the given definition and re-runs
`cg_input_sampler.validate_candidate()` against them -- the candidate
travelled through a browser and back, and the published domains may have
changed since generation (T-38-17). Clamping is never implemented here
either, matching `cg_input_sampler`'s own no-clamp discipline: a violation
is reported and the write is refused, never silently coerced.

The written node's shape is documented in `spec/DATABASE.md`'s amended
DesignState section: a standalone, Run-less `:DesignState {kind:
'ParamState'}` node, `MERGE`'d by `StateId` + `project` so re-accepting the
same candidate is idempotent (D-18), carrying Phase 36's provenance
vocabulary verbatim (`source`, `sourceRuleId`, `provider`, `model`,
`confidence`, `definitionId`, `publishedAt`, `strategy`,
`determinabilityClass`, `generatedAt`) plus `acceptedAt` (D-21).
"""

from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from typing import Any

import cg_input_bindings
import cg_input_sampler

# ── Public exceptions ──


class CandidateDomainViolation(ValueError):
    """Raised when the accept-time re-validation against the LIVE published
    domains finds at least one violation. `violations` carries the exact
    violation-dict list `cg_input_sampler.validate_candidate()` returned --
    the route maps this to 422 COMPUTGRAPH_ACCEPT_CANDIDATE_DOMAIN_VIOLATION.
    No write happens before this exception is raised or after it -- the
    caller (`accept_candidate`) never issues the MERGE once a single
    violation is found (T-38-17)."""

    def __init__(self, message: str, violations: list[dict[str, Any]]):
        super().__init__(message)
        self.violations = violations


class CandidateRequestInvalid(ValueError):
    """Raised for a structurally invalid request: a `candidate` that isn't
    an object, a missing/empty `parameters` list, or a `provenance` block
    missing one of the required attribution keys (`sourceRuleId`,
    `provider`, `model`, `generatedAt`). A ParamState without provenance
    would silently defeat GHIN-03 at exactly the moment it becomes
    permanent -- this is the guard that makes provenance completeness a
    write-time requirement, not a documentation convention."""


# ── compute_param_state_id() -- deterministic, never the generation-time id ──


def compute_param_state_id(candidate: dict[str, Any]) -> str:
    """A deterministic `DS_`-prefixed id derived from the candidate's
    parameter set (sorted `(parameterId, value)` pairs) plus its
    `provenance.sourceRuleId`. Determinism is what makes the MERGE
    idempotent: accepting the same candidate twice produces the same node,
    not a second one.

    Deliberately NOT the generation-time `candidateId` (`c0`, `c1`, ...) --
    that id is per-request and would make two independent accept calls for
    the identical candidate content mint two different nodes, defeating
    D-18's idempotency guarantee.
    """
    provenance = candidate.get("provenance") or {}
    source_rule_id = provenance.get("sourceRuleId") or ""
    pairs = sorted(
        (view.get("parameterId"), _extract_value(view))
        for view in (candidate.get("parameters") or [])
    )
    payload = json.dumps(
        {"sourceRuleId": source_rule_id, "parameters": pairs}, sort_keys=True, default=str
    )
    digest = hashlib.sha256(payload.encode("utf-8")).hexdigest()[:16].upper()
    return f"DS_{digest}"


# ── Parameter-view helpers (mirror cg_input_generation.py's type-slot
# convention -- duplicated, not imported, per this module's deliberately
# narrow first-party dependency surface: cg_input_bindings and
# cg_input_sampler only) ──

_TYPE_TO_JSON_TYPE: dict[str, str] = {"Number": "number", "Integer": "integer", "Boolean": "boolean"}


def _extract_value(view: dict[str, Any]) -> Any:
    ptype = (view.get("type") or "").strip()
    if ptype == "Boolean":
        return view.get("booleanValue")
    if ptype == "Integer":
        return view.get("integerValue")
    if ptype == "Number":
        return view.get("numberValue")
    return None


def _flatten_parameters(parameter_views: list[dict[str, Any]]) -> dict[str, Any]:
    """`candidate.parameters[]` (a list of `{parameterId, type,
    numberValue, integerValue, booleanValue, ...}` views) -> the flat
    `{parameterId: value}` dict `cg_input_sampler.validate_candidate()`
    expects."""
    flat: dict[str, Any] = {}
    for view in parameter_views:
        parameter_id = view.get("parameterId")
        if not parameter_id:
            continue
        flat[parameter_id] = _extract_value(view)
    return flat


def _build_state_payload_json(state_id: str, accepted_at: str, parameter_views: list[dict[str, Any]]) -> str:
    """The v2 `statePayloadJson` envelope `Neo4jValidGraphRepository.
    TryParseDesignState`'s v2 branch (the additive standalone read, plan
    38-05 Task 3) reads directly onto the `DG.Core.Models.DesignState`/
    `ParamState`/`DesignStateParameter` CLR shape -- so each parameter is
    written with the model's OWN camelCase property names
    (`parameterId`, `displayName`, `type`, `numberValue`, `integerValue`,
    `booleanValue`), never the condensed `{type, value}` pair
    `DesignStatePayloadV2Serializer`'s private DTOs use for ITS OWN
    Serialize()/Deserialize() round-trip -- those are a different shape for
    a different call path. `StateId` and an ISO-8601 `CapturedAtUtc` are set
    at both the top level and on the nested ParamState, matching the
    invariants `DesignStatePayloadV2Serializer.cs:132-144` documents.
    """
    parameters: list[dict[str, Any]] = []
    for view in parameter_views:
        json_type = _TYPE_TO_JSON_TYPE.get((view.get("type") or "").strip())
        if json_type is None:
            continue
        value = _extract_value(view)
        parameters.append(
            {
                "parameterId": view.get("parameterId"),
                "displayName": view.get("displayName") or view.get("parameterId"),
                "type": json_type,
                "numberValue": value if json_type == "number" else None,
                "integerValue": value if json_type == "integer" else None,
                "booleanValue": value if json_type == "boolean" else None,
            }
        )

    envelope = {
        "version": "2",
        "stateId": state_id,
        "label": None,
        "capturedAtUtc": accepted_at,
        "objStates": [],
        "paramStates": [
            {
                "stateId": state_id,
                "capturedAtUtc": accepted_at,
                "parameters": parameters,
            }
        ],
        "propStates": [],
    }
    return json.dumps(envelope, sort_keys=True)


# ── Live-domain re-read (one parameterized read, never a write) ──


def _list_published_parameters(session: Any, project: str, definition_id: str) -> list[dict[str, Any]]:
    """The same published `:Parameter` shape
    `cg_input_generation._list_published_parameters` reads at generation
    time -- re-read fresh at accept time so the caller never trusts what
    the client says about domains (T-38-17). Deliberately re-implemented
    here rather than imported: this module's first-party dependency surface
    is limited to `cg_input_bindings` and `cg_input_sampler` (see module
    docstring)."""
    result = session.run(
        """
        MATCH (p:Parameter {project: $project, definitionId: $definitionId})
        RETURN p.cgId AS cgId, p.dgId AS dgId, p.parameterName AS parameterName,
               p.reinstateParameterId AS reinstateParameterId, p.paramKind AS paramKind,
               p.dataType AS dataType, p.domainMin AS domainMin, p.domainMax AS domainMax,
               p.domainStep AS domainStep
        ORDER BY p.cgId
        // op=ACCEPT_CANDIDATE_LIST_PARAMETERS
        """,
        {"project": project, "definitionId": definition_id},
    )
    return [dict(row) for row in result]


_REQUIRED_PROVENANCE_KEYS: tuple[str, ...] = ("sourceRuleId", "provider", "model", "generatedAt")

_PROVENANCE_KEYS: tuple[str, ...] = (
    "source",
    "sourceRuleId",
    "provider",
    "model",
    "confidence",
    "definitionId",
    "publishedAt",
    "strategy",
    "determinabilityClass",
    "generatedAt",
)


def _validate_request_shape(candidate: dict[str, Any]) -> dict[str, Any]:
    """Raise CandidateRequestInvalid for a structurally malformed request;
    otherwise return the candidate's `provenance` dict. Never touches the
    graph -- pure shape validation, always runs before the live-domain
    re-read."""
    if not isinstance(candidate, dict):
        raise CandidateRequestInvalid(
            "candidate must be a JSON object. Where: request body 'candidate'. How to fix: "
            "round-trip exactly one item from a prior generate-inputs response's candidates[] array."
        )

    parameters = candidate.get("parameters")
    if not isinstance(parameters, list) or not parameters:
        raise CandidateRequestInvalid(
            "candidate.parameters is missing or empty. Where: candidate.parameters. How to fix: "
            "round-trip the candidate's parameters[] array verbatim from the generate-inputs response."
        )

    provenance = candidate.get("provenance")
    if not isinstance(provenance, dict):
        raise CandidateRequestInvalid(
            "candidate.provenance is missing or not an object. Where: candidate.provenance. How to "
            "fix: round-trip the provenance object from the prior generate-inputs response verbatim."
        )

    missing = [key for key in _REQUIRED_PROVENANCE_KEYS if not provenance.get(key)]
    if missing:
        raise CandidateRequestInvalid(
            f"candidate.provenance is missing required key(s): {', '.join(missing)}. Where: "
            f"candidate.provenance. How to fix: round-trip the provenance object verbatim -- it must "
            f"carry sourceRuleId, provider, model and generatedAt."
        )

    return provenance


# ── accept_candidate() -- the only write path for AI-generated candidates ──


def accept_candidate(
    session: Any,
    project: str,
    definition_id: str,
    rule_id: str,
    candidate: dict[str, Any],
    parameter_overrides: "list[str] | None" = None,
) -> dict[str, Any]:
    """Persist one architect-accepted candidate as a standalone `ParamState`
    `:DesignState` (D-18), after re-validating it against the LIVE published
    domains (T-38-17) -- never trusting what the client round-tripped.

    Sequence: validate the request's shape and provenance completeness ->
    re-read the live published `:Parameter` rows for `definition_id` ->
    classify `rule_id` and rebuild `bound_params` through
    `cg_input_bindings.select_parameters` (the exact same scoping generation
    used) -> re-run `cg_input_sampler.validate_candidate()` -> on any
    violation, raise `CandidateDomainViolation` WITHOUT writing anything ->
    otherwise compute the deterministic `StateId`, build the v2
    `statePayloadJson` envelope, and MERGE the standalone `:DesignState`
    node in one parameterized write.

    `parameter_overrides`, when non-empty, MUST be the same list passed to
    `cg_input_generation.generate_inputs()` for this candidate (round-tripped
    by the caller from the generate-inputs request) -- it is threaded
    through to `cg_input_bindings.classify_rule()` unchanged so accept-time
    re-classification resolves the SAME bound-parameter scope generation
    used, rather than silently falling back to the rule's default
    `inputBindings` scope (CR-01: without this, any candidate generated with
    an override is unconditionally rejected here as unknown/missing
    parameters).

    Only accepted candidates are persisted (D-19): every exception path
    above raises before `session.run()` is ever called for the write.
    """
    provenance = _validate_request_shape(candidate)

    published_parameters = _list_published_parameters(session, project, definition_id)
    bindings = cg_input_bindings.load_input_bindings()
    classification = cg_input_bindings.classify_rule(
        session, rule_id, project, bindings, parameter_overrides
    )
    bound, _excluded = cg_input_bindings.select_parameters(classification, published_parameters)

    flat_parameters = _flatten_parameters(candidate["parameters"])
    violations = cg_input_sampler.validate_candidate(flat_parameters, bound)
    if violations:
        raise CandidateDomainViolation(
            "Candidate failed re-validation against the live published domains -- the domains may "
            "have changed since this candidate was generated.",
            violations,
        )

    state_id = compute_param_state_id(candidate)
    accepted_at = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    state_payload_json = _build_state_payload_json(state_id, accepted_at, candidate["parameters"])

    full_provenance = {
        "source": provenance.get("source") or "ai-generated",
        "sourceRuleId": provenance.get("sourceRuleId"),
        "provider": provenance.get("provider"),
        "model": provenance.get("model"),
        "confidence": provenance.get("confidence"),
        "definitionId": provenance.get("definitionId") or definition_id,
        "publishedAt": provenance.get("publishedAt"),
        "strategy": provenance.get("strategy"),
        "determinabilityClass": provenance.get("determinabilityClass"),
        "generatedAt": provenance.get("generatedAt"),
    }

    session.run(
        """
        MERGE (ds:DesignState {StateId: $stateId, project: $project})
        SET ds.kind = 'ParamState',
            ds.graph = 'ValidGraph',
            ds.statePayloadJson = $statePayloadJson,
            ds.source = $source,
            ds.sourceRuleId = $sourceRuleId,
            ds.provider = $provider,
            ds.model = $model,
            ds.confidence = $confidence,
            ds.definitionId = $definitionId,
            ds.publishedAt = $publishedAt,
            ds.strategy = $strategy,
            ds.determinabilityClass = $determinabilityClass,
            ds.generatedAt = $generatedAt,
            ds.acceptedAt = $acceptedAt
        // op=ACCEPT_PARAM_STATE_CANDIDATE
        """,
        {
            "stateId": state_id,
            "project": project,
            "statePayloadJson": state_payload_json,
            "source": full_provenance["source"],
            "sourceRuleId": full_provenance["sourceRuleId"],
            "provider": full_provenance["provider"],
            "model": full_provenance["model"],
            "confidence": full_provenance["confidence"],
            "definitionId": full_provenance["definitionId"],
            "publishedAt": full_provenance["publishedAt"],
            "strategy": full_provenance["strategy"],
            "determinabilityClass": full_provenance["determinabilityClass"],
            "generatedAt": full_provenance["generatedAt"],
            "acceptedAt": accepted_at,
        },
    ).consume()

    return {
        "project": project,
        "stateId": state_id,
        "kind": "ParamState",
        "acceptedAt": accepted_at,
        "parameterCount": len(flat_parameters),
        "provenance": full_provenance,
    }


# ── fetch_generated_param_states() -- the GHIN-03 "queryable in the graph" read ──


def fetch_generated_param_states(
    session: Any, project: str, rule_id: "str | None" = None
) -> list[dict[str, Any]]:
    """Return every accepted AI-generated `ParamState` in `project`, newest
    first, optionally filtered to one `rule_id` -- the GHIN-03 SC4 assertion
    ("a MATCH on generated ParamStates returns rule, model and timestamp for
    each"). Read-only, parameterized; never touches the write path."""
    query = (
        "MATCH (ds:DesignState {project: $project, kind: 'ParamState'}) "
        "WHERE ds.source = 'ai-generated'"
    )
    params: dict[str, Any] = {"project": project}
    if rule_id:
        query += " AND ds.sourceRuleId = $ruleId"
        params["ruleId"] = rule_id
    query += (
        " RETURN ds.StateId AS stateId, ds.sourceRuleId AS sourceRuleId, ds.provider AS provider,"
        " ds.model AS model, ds.generatedAt AS generatedAt, ds.acceptedAt AS acceptedAt,"
        " ds.strategy AS strategy, ds.determinabilityClass AS determinabilityClass"
        " ORDER BY ds.acceptedAt DESC"
        " // op=FETCH_GENERATED_PARAM_STATES"
    )
    result = session.run(query, params)
    return [dict(row) for row in result]
