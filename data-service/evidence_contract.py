"""Typed canonical status, evidence envelope models, and schema validation.

Vocabulary authority
---------------------
``spec/evidence-contract.schema.json`` `$defs.CanonicalStatus.enum` is the single
mechanical authority for the eight-member canonical status vocabulary
(spec/EVIDENCE-CONTRACT.md section 1, D-02). ``CanonicalStatus`` below MUST NOT drift
from that enum in either direction; ``data-service/tests/test_evidence_contract.py``
asserts set equality between this Python enum and the schema's enum array read from
the file at test time, so a drift is caught mechanically rather than by review alone.

Envelope shape authority
-------------------------
``EvidenceEnvelope`` / ``EvidenceRow`` mirror ``spec/evidence-contract.schema.json``
`$defs.EvidenceEnvelope` / `$defs.EvidenceRow` field-for-field. Per D-01: the schema is
authoritative for shape (field names, types, required-ness); spec/EVIDENCE-CONTRACT.md
is authoritative for meaning (what each status asserts, ordering/identity rules,
canonicalization rules, DE-01 acceptance).

Legacy boolean direction (D-03/D-04)
-------------------------------------
The canonical status is new, additive, and parallel to the legacy boolean outcome
surfaces (``RuleEvaluationResult.Passed``, ``Run.ValidStatus``, ``conforms``). The
mapping is one-directional -- canonical to boolean, lossy, and defined
(``to_legacy_boolean``). The reverse direction is undefined and forbidden: no function
in this module infers a canonical status from a legacy boolean. A legacy ``false`` is
compatible with seven of the eight canonical statuses, and guessing which one collapses
exactly the distinction this vocabulary exists to preserve.
"""

from __future__ import annotations

import functools
import os
from datetime import datetime, timezone
from enum import StrEnum
from pathlib import Path
from typing import Any

import json as _json

import jsonschema
from pydantic import BaseModel, ConfigDict, Field

import canonical_json

EVIDENCE_CONTRACT_VERSION = "1.0.0"


class CanonicalStatus(StrEnum):
    """The frozen 8-member canonical status vocabulary (D-02).

    Values are the snake_case wire forms defined in
    spec/evidence-contract.schema.json `$defs.CanonicalStatus.enum`. No renaming, no
    additions, no merging outside a phase that explicitly revises the contract.
    test_evidence_contract.py asserts this enum's value set equals the schema's enum
    array read from the file, so this cannot drift from the schema unnoticed.
    """

    PASSED = "passed"
    FAILED = "failed"
    UNKNOWN = "unknown"
    NOT_EVALUATED = "not_evaluated"
    NO_POPULATION = "no_population"
    UNSUPPORTED = "unsupported"
    INDETERMINATE = "indeterminate"
    ERROR = "error"


# Canonical -> legacy boolean mapping (D-04). Only `passed` maps to True; every other
# status -- including the ones that are not literally a rule violation -- maps to
# False, because the legacy surface has no room for the distinction this vocabulary
# exists to preserve.
_TO_LEGACY_BOOLEAN: dict["CanonicalStatus", bool] = {
    CanonicalStatus.PASSED: True,
    CanonicalStatus.FAILED: False,
    CanonicalStatus.UNKNOWN: False,
    CanonicalStatus.NOT_EVALUATED: False,
    CanonicalStatus.NO_POPULATION: False,
    CanonicalStatus.UNSUPPORTED: False,
    CanonicalStatus.INDETERMINATE: False,
    CanonicalStatus.ERROR: False,
}

# Envelope-level roll-up precedence (worst-case-first), per build_envelope's
# docstring below. Index = precedence rank, lower index wins.
_ROLLUP_PRECEDENCE: tuple[CanonicalStatus, ...] = (
    CanonicalStatus.ERROR,
    CanonicalStatus.FAILED,
    CanonicalStatus.INDETERMINATE,
    CanonicalStatus.UNSUPPORTED,
    CanonicalStatus.UNKNOWN,
    CanonicalStatus.NOT_EVALUATED,
    CanonicalStatus.NO_POPULATION,
    CanonicalStatus.PASSED,
)


def to_legacy_boolean(status: "CanonicalStatus") -> bool:
    """One-directional canonical -> legacy boolean mapping (D-04).

    Returns True only for CanonicalStatus.PASSED; False for every other status. The
    reverse direction (inferring a canonical status from a legacy boolean) is
    undefined and forbidden -- no function here performs it. A legacy `false` is
    compatible with seven of the eight canonical statuses, so guessing which one would
    collapse exactly the distinction this vocabulary exists to preserve.
    """
    return _TO_LEGACY_BOOLEAN[status]


@functools.lru_cache(maxsize=1)
def load_contract_schema() -> dict[str, Any]:
    """Resolve, load, and cache spec/evidence-contract.schema.json.

    Resolves relative to the repo root via the same ``DG_KNOWLEDGE_REPO_ROOT``
    mechanism ``dg_knowledge.py`` uses, so this works both in-container
    (``/mnt/repo/spec/...``) and from the host. This is a hard dependency, not an
    optional sidecar -- a missing file raises a clear error naming the expected path
    rather than degrading quietly, because there is nothing meaningful to validate
    against without it.
    """
    repo_root = Path(os.getenv("DG_KNOWLEDGE_REPO_ROOT", str(Path(__file__).resolve().parent.parent)))
    schema_path = repo_root / "spec" / "evidence-contract.schema.json"
    if not schema_path.is_file():
        raise FileNotFoundError(
            f"evidence_contract.load_contract_schema: expected schema file at {schema_path} "
            "(resolved from DG_KNOWLEDGE_REPO_ROOT or the module's own repo-relative fallback). "
            "This is a hard dependency, not an optional sidecar."
        )
    with open(schema_path, "r", encoding="utf-8") as f:
        return _json.load(f)


class EvidenceRow(BaseModel):
    """Per-(rule, object) evidence row (spec/EVIDENCE-CONTRACT.md section 3/4).

    Rows are addressed by the (ruleId, objectId) identity pair, never by value --
    two value-equal rows with distinct identity remain separately addressable and are
    never merged, collided, or deduplicated on value equality alone.
    """

    model_config = ConfigDict(extra="forbid")

    ruleId: str
    objectId: str
    canonicalStatus: CanonicalStatus
    warnings: list[str] = Field(default_factory=list)
    inputHash: str | None = None
    outputHash: str | None = None
    detail: str | None = None


class EvidenceEnvelope(BaseModel):
    """The evidence envelope a stage emits to report an evaluation outcome.

    Mirrors spec/evidence-contract.schema.json `$defs.EvidenceEnvelope` field-for-field,
    including `additionalProperties: false` (enforced here via `extra="forbid"`).
    Emitted at every stage boundary that produces or transforms a verdict (D-06), not
    only at final persistence.
    """

    model_config = ConfigDict(extra="forbid")

    contractVersion: str
    canonicalizationVersion: int
    project: str
    definitionId: str
    serviceName: str
    serviceVersion: str
    emittedAt: str
    stage: str
    canonicalStatus: CanonicalStatus
    rows: list[EvidenceRow] = Field(default_factory=list)

    dgId: str | None = None
    sourceRepresentation: dict[str, Any] | None = None
    inputHash: str | None = None
    outputHash: str | None = None
    schemaVersion: str | None = None
    ontologyVersion: str | None = None
    ruleVersion: str | None = None
    shapeVersion: str | None = None
    provider: str | None = None
    model: str | None = None
    warnings: list[str] = Field(default_factory=list)


def _sort_key(row: EvidenceRow) -> tuple[str, str]:
    return (row.objectId, row.ruleId)


def _rollup_status(rows: list[EvidenceRow]) -> CanonicalStatus:
    """Derive the envelope-level roll-up status from row statuses by explicit
    precedence, never by boolean arithmetic.

    Precedence (highest to lowest): error > failed > indeterminate > unsupported >
    unknown > not_evaluated > no_population > passed. The first status present in the
    rows, walking this precedence order, is the roll-up. An empty row list (e.g. a
    rule-level no_population situation with zero contributing rows) rolls up to
    `no_population` by this same precedence, since there is no `passed` row to fall
    back to and no worse-ranked status is present either -- callers with a genuine
    zero-row no_population case should pass the explicit `roll_up` override instead of
    relying on this default.
    """
    present = {row.canonicalStatus for row in rows}
    for candidate in _ROLLUP_PRECEDENCE:
        if candidate in present:
            return candidate
    return CanonicalStatus.NO_POPULATION


def build_envelope(
    project: str,
    definition_id: str,
    service_name: str,
    service_version: str,
    stage: str,
    rows: list[EvidenceRow],
    *,
    roll_up: CanonicalStatus | None = None,
    dg_id: str | None = None,
    source_representation: dict[str, Any] | None = None,
    input_hash: str | None = None,
    output_hash: str | None = None,
    schema_version: str | None = None,
    ontology_version: str | None = None,
    rule_version: str | None = None,
    shape_version: str | None = None,
    provider: str | None = None,
    model: str | None = None,
    warnings: list[str] | None = None,
) -> EvidenceEnvelope:
    """Construct an ordered, versioned EvidenceEnvelope.

    - `contractVersion` is set to EVIDENCE_CONTRACT_VERSION.
    - `canonicalizationVersion` is set to canonical_json.CANONICALIZATION_VERSION.
    - `emittedAt` is the current UTC time, RFC 3339 with a `Z` suffix.
    - `rows` are sorted ascending by `objectId`, ties broken by `ruleId`
      (spec/EVIDENCE-CONTRACT.md section 4 -- normative, not incidental).
    - `canonicalStatus` (the envelope-level roll-up) is derived from the rows by
      explicit precedence (see `_rollup_status`), not by boolean arithmetic, unless
      the caller supplies an explicit `roll_up` override.
    """
    sorted_rows = sorted(rows, key=_sort_key)
    envelope_status = roll_up if roll_up is not None else _rollup_status(sorted_rows)
    emitted_at = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

    return EvidenceEnvelope(
        contractVersion=EVIDENCE_CONTRACT_VERSION,
        canonicalizationVersion=canonical_json.CANONICALIZATION_VERSION,
        project=project,
        definitionId=definition_id,
        serviceName=service_name,
        serviceVersion=service_version,
        emittedAt=emitted_at,
        stage=stage,
        canonicalStatus=envelope_status,
        rows=sorted_rows,
        dgId=dg_id,
        sourceRepresentation=source_representation,
        inputHash=input_hash,
        outputHash=output_hash,
        schemaVersion=schema_version,
        ontologyVersion=ontology_version,
        ruleVersion=rule_version,
        shapeVersion=shape_version,
        provider=provider,
        model=model,
        warnings=warnings or [],
    )


def validate_envelope(envelope: EvidenceEnvelope) -> None:
    """Validate `envelope` against spec/evidence-contract.schema.json (D-01's
    mechanical enforcement). Raises `jsonschema.ValidationError` on shape violation --
    lets it propagate to the caller.

    ``exclude_none=True`` on the dump: the schema's optional scalar fields are typed
    as ``string`` (no ``null`` alternative) since absence, not an explicit JSON
    ``null``, is how an unset optional field is represented (e.g. ``shapeVersion``,
    ``dgId``). ``sourceRepresentation`` is the sole exception -- it is explicitly
    typed ``["object", "null"]`` in the schema, so its own ``None`` is a legitimate
    value; ``exclude_none`` still drops the *key* when its Python value is ``None``,
    matching "absent" rather than emitting a literal JSON ``null``. Both renderings
    are schema-valid for that field, and dropping the key when unset is the exact same
    treatment every other optional field gets.
    """
    schema = load_contract_schema()
    payload = envelope.model_dump(mode="json", exclude_none=True)
    jsonschema.validate(instance=payload, schema=schema)
