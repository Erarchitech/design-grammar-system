"""Canonical DesignState projection and content hash (Phase 1202, ALGN12-08/ALGN12-09, D-01/D-02).

Cross-language parity contract
-------------------------------
This module mirrors ``DG.Core.Serialization.DesignStateCanonicalProjection`` (the C# original,
plan 1202-02 Task 1) key-for-key: same top-level keys, same per-entry keys, same ordinal sorts.
``compute_state_hash`` calls ``canonical_json.hash_canonical`` -- never the digest module
directly and never a second canonicalization -- extending the already-hardened Phase 1200
hasher (D-02).
Inventing a second canonicalization here is forbidden; if this projection needed a rule
``canonical_json``'s six rules cannot express, that would be a finding against
spec/EVIDENCE-CONTRACT.md, not a local fix.

Projection shape (mirrors DesignStateCanonicalProjection.cs's class doc-comment):
- ``stateId``, ``label`` (``None`` when absent), ``capturedAtUtc`` (ISO-8601 round-trip string,
  already how the v2 payload stores it).
- ``members`` -- the ALGN12-09 membership manifest: a list of ``{"kind", "stateId"}`` entries,
  one per objState/paramState/propState, sorted by kind then stateId (ordinal / code-point,
  matching Python's default ``sorted()`` on ``str``, which matches C#'s
  ``StringComparer.Ordinal``).
- ``objStates`` -- sorted by stateId; **geometry is never read or written here** -- this is the
  D-06 exclusion contract. The v2 wire payload this module reads from (see
  ``DesignStatePayloadV2Serializer.ObjStateDto``) carries no geometry key to begin with, so there
  is nothing to strip; the exclusion is structural on both legs.
- ``paramStates`` -- sorted by stateId; each entry's ``parameters`` array sorted by parameterId.
- ``propStates`` -- sorted by stateId. **No capturedAtUtc** on a propState entry -- PropState is
  value-scoped (rule IRI + property IRI + value), not capture-scoped; a capture timestamp on it
  would make two identical property assertions captured a second apart hash differently, which
  contradicts the content-hash purpose. This is a deliberate exclusion, mirrored from the C# side.

Numeric handling: a Number parameter's value is converted to ``decimal.Decimal`` before entering
the projection, matching ``canonical_json``'s own decimal-only rule for non-integer numbers -- a
raw JSON float would diverge from the C# leg's ``decimal`` path. NaN/Infinity/non-finite values
raise ``ValueError`` naming the offending field -- never coerced (V5 fail-closed convention).

Input shape: this module operates on the **parsed v2 wire payload** (a ``dict`` matching
``DesignStatePayloadV2Serializer``'s DTO shape: ``version``, ``stateId``, ``label``,
``capturedAtUtc``, ``objStates``, ``paramStates``, ``propStates``), not on a live Python domain
object -- there is no Python-side ``DesignState`` domain type (RESEARCH.md: "Python only projects
and writes; no consumer needs full reconstruction yet").
"""

from __future__ import annotations

import math
from decimal import Decimal, InvalidOperation
from typing import Any

from canonical_json import hash_canonical

_VALID_PARAMETER_TYPES = {"number", "integer", "boolean"}


def _require_state_id(entry: dict[str, Any], kind: str) -> str:
    state_id = entry.get("stateId")
    if not isinstance(state_id, str) or not state_id:
        raise ValueError(f"design_state_projection: a {kind} entry is missing a non-empty 'stateId'")
    return state_id


def _build_parameter_value(parameter: dict[str, Any]) -> Any:
    parameter_id = parameter.get("parameterId", "<unknown>")
    param_type = parameter.get("type")
    if param_type not in _VALID_PARAMETER_TYPES:
        raise ValueError(
            f"design_state_projection: parameter '{parameter_id}' has an unsupported type '{param_type}'"
        )

    value = parameter.get("value")

    if param_type == "number":
        if isinstance(value, bool):
            raise ValueError(f"design_state_projection: parameter '{parameter_id}' with type number carries a bool value")
        if value is None:
            raise ValueError(f"design_state_projection: parameter '{parameter_id}' with type number is missing a value")
        if isinstance(value, float):
            if math.isnan(value) or math.isinf(value):
                raise ValueError(
                    f"design_state_projection: parameter '{parameter_id}' has a non-finite NumberValue "
                    f"({value!r}) which cannot be represented in canonical form (canonical_json rule 6)"
                )
            try:
                # Match C#'s Convert.ToDecimal(double) "shortest round-trip" scale exactly:
                # Decimal(repr(value)) preserves the same digits Convert.ToDecimal would produce,
                # then .normalize() strips the trailing zero Python's float repr always keeps for
                # a whole number (repr(42.0) == "42.0") but C#'s double->decimal conversion does
                # not (Convert.ToDecimal(42.0) == 42m, scale 0) -- confirmed empirically against
                # the C# leg, since a source double has no meaningful stored scale to preserve
                # (unlike canonical_json's own Decimal-input trailing-zero-preservation rule,
                # which applies to values that were already Decimal on input).
                return Decimal(repr(value)).normalize()
            except InvalidOperation as exc:
                raise ValueError(
                    f"design_state_projection: parameter '{parameter_id}' has a NumberValue that cannot "
                    f"be converted to Decimal ({value!r})"
                ) from exc
        if isinstance(value, Decimal):
            if not value.is_finite():
                raise ValueError(
                    f"design_state_projection: parameter '{parameter_id}' has a non-finite Decimal value "
                    f"({value!r})"
                )
            return value
        if isinstance(value, int):
            return Decimal(value)
        raise ValueError(
            f"design_state_projection: parameter '{parameter_id}' with type number has an unsupported "
            f"value type {type(value).__name__}"
        )

    if param_type == "integer":
        if isinstance(value, bool) or not isinstance(value, int):
            raise ValueError(f"design_state_projection: parameter '{parameter_id}' with type integer requires an int value")
        return value

    # boolean
    if not isinstance(value, bool):
        raise ValueError(f"design_state_projection: parameter '{parameter_id}' with type boolean requires a bool value")
    return value


def _build_parameter(parameter: dict[str, Any]) -> dict[str, Any]:
    return {
        "parameterId": parameter.get("parameterId"),
        "displayName": parameter.get("displayName"),
        "type": parameter.get("type"),
        "value": _build_parameter_value(parameter),
    }


def _build_members(obj_states: list[dict], param_states: list[dict], prop_states: list[dict]) -> list[dict[str, str]]:
    entries: list[tuple[str, str]] = []
    for obj_state in obj_states:
        entries.append(("objState", _require_state_id(obj_state, "objState")))
    for param_state in param_states:
        entries.append(("paramState", _require_state_id(param_state, "paramState")))
    for prop_state in prop_states:
        entries.append(("propState", _require_state_id(prop_state, "propState")))

    entries.sort(key=lambda pair: (pair[0], pair[1]))
    return [{"kind": kind, "stateId": state_id} for kind, state_id in entries]


def _build_obj_states(obj_states: list[dict]) -> list[dict[str, Any]]:
    sorted_states = sorted(obj_states, key=lambda o: _require_state_id(o, "objState"))
    result = []
    for obj_state in sorted_states:
        # Geometry is never read here (D-06) -- the v2 wire payload carries no geometry key.
        result.append(
            {
                "stateId": obj_state.get("stateId"),
                "objectRef": obj_state.get("objectRef"),
                "label": obj_state.get("label"),
                "classIri": obj_state.get("classIri"),
                "dgId": obj_state.get("dgId"),
                "capturedAtUtc": obj_state.get("capturedAtUtc"),
            }
        )
    return result


def _build_param_states(param_states: list[dict]) -> list[dict[str, Any]]:
    sorted_states = sorted(param_states, key=lambda p: _require_state_id(p, "paramState"))
    result = []
    for param_state in sorted_states:
        parameters = param_state.get("parameters") or []
        sorted_parameters = sorted(parameters, key=lambda p: p.get("parameterId") or "")
        result.append(
            {
                "stateId": param_state.get("stateId"),
                "capturedAtUtc": param_state.get("capturedAtUtc"),
                "parameters": [_build_parameter(p) for p in sorted_parameters],
            }
        )
    return result


def _build_prop_states(prop_states: list[dict]) -> list[dict[str, Any]]:
    sorted_states = sorted(prop_states, key=lambda p: _require_state_id(p, "propState"))
    result = []
    for prop_state in sorted_states:
        # PropState carries no capturedAtUtc -- deliberate exclusion (see module doc-comment).
        prop_value = prop_state.get("propValue")
        result.append(
            {
                "stateId": prop_state.get("stateId"),
                "ruleIri": prop_state.get("ruleIri"),
                "dataPropertyIri": prop_state.get("dataPropertyIri"),
                "objectRef": prop_state.get("objectRef"),
                "propValue": _build_parameter(prop_value) if prop_value is not None else None,
            }
        )
    return result


def build_projection(payload: dict[str, Any]) -> dict[str, Any]:
    """Build the canonical DesignState projection from a parsed v2 wire payload.

    Raises ``ValueError`` naming the offending field for a malformed payload -- missing
    ``version``, a member missing ``stateId``, or a non-finite numeric parameter value. Never
    coerces (V5 fail-closed convention).
    """
    if not isinstance(payload, dict):
        raise ValueError("design_state_projection: payload must be a dict")

    version = payload.get("version")
    if version != "2":
        raise ValueError(f"design_state_projection: unsupported state payload version. Expected '2', got {version!r}")

    obj_states = payload.get("objStates") or []
    param_states = payload.get("paramStates") or []
    prop_states = payload.get("propStates") or []

    return {
        "stateId": payload.get("stateId"),
        "label": payload.get("label"),
        "capturedAtUtc": payload.get("capturedAtUtc"),
        "members": _build_members(obj_states, param_states, prop_states),
        "objStates": _build_obj_states(obj_states),
        "paramStates": _build_param_states(param_states),
        "propStates": _build_prop_states(prop_states),
    }


def compute_state_hash(payload: dict[str, Any]) -> str:
    """Build the canonical projection and hash it via ``canonical_json.hash_canonical``.

    This is the ``canonicalStateHash`` for ``payload``. Never calls the digest module
    directly -- D-02 forbids a second hashing regime.
    """
    return hash_canonical(build_projection(payload))
