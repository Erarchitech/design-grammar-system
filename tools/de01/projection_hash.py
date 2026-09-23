"""Benchmark-computed verdict projection hash for the DE-01 repeat benchmark (D-04).

Purpose
-------
No DE-01 leg emits an output hash of its own (1204-CONTEXT.md Correction 2), so the
repeat benchmark cannot read repeatability off the producers. Instead the benchmark
computes its own hash over each leg envelope, minus a small, closed, explicitly
recorded exclusion list. That projection is what plan 1204-05's N-iteration runner and
the D-08 N/N gate compare across iterations.

What is hashed
--------------
``canonical_json.hash_canonical`` over the leg envelope dict with exactly the fields in
:data:`EXCLUSION_FIELDS` removed and ``rows`` canonically ordered per
``spec/EVIDENCE-CONTRACT.md`` section 4 (``objectId`` ascending, ``ruleId`` tiebreak).
This is the section 6 *nested-payload* canonical hashing entry point;
``canonicalizationVersion`` 1.

Recorded exclusion reasons (D-04)
---------------------------------
- ``emittedAt`` -- wall clock, stamped per emission
  (``data-service/evidence_contract.py:253``). It must differ between iterations,
  so it cannot participate in a repeatability comparison.
- ``generatedAt`` -- report-level wall clock (``tools/de01/report.py:354``), same reason.
- ``definitionId`` -- carries the run id on the data-service leg
  (``app.py:2358`` passes ``definition_id=run_id``; 1204-CONTEXT.md Correction 3).
  Every publish mints a new run, so the field varies per iteration by construction.

Exclusion is purely by field *name* at any depth of the top-level envelope dict. No run
id literal is ever hardcoded here (Correction 3): a literal would silently stop
excluding anything the day the run id scheme changes.

Change discipline (D-04 one-way reversibility)
----------------------------------------------
Adding a field to :data:`EXCLUSION_FIELDS` requires (1) a recorded reason in the
contract -- ``spec/REPRODUCIBILITY.md`` once plan 1204-06 authors it -- and (2) a bump of
:data:`PROJECTION_VERSION`. Two projections that differ in exclusion list must never
compare equal by accident. The list is deliberately not configurable at the call site:
tuning it to make a divergence disappear is forbidden (D-08).

Do not use the pipe-joined scalar-tuple helper
----------------------------------------------
Only the nested-payload canonical hashing entry point (:func:`canonical_json.hash_canonical`)
may be used. The separate pipe-joined scalar-tuple helper in ``data-service/canonical_json.py``
diverges from the identity functions after phase 1203 D-09 (1204-CONTEXT.md Correction 10),
and must never be imported or called from this module.

Scope
-----
Pure transform: this module never mutates its input envelope and never re-validates it
(``tools/de01/legs.py:10-13`` already validates every envelope before returning it).
"""

from __future__ import annotations

import copy
import sys
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
DATA_SERVICE_DIR = REPO_ROOT / "data-service"
if str(DATA_SERVICE_DIR) not in sys.path:
    sys.path.insert(0, str(DATA_SERVICE_DIR))

import canonical_json  # noqa: E402  (path-dependent import, see sys.path insert above)

PROJECTION_VERSION = 1
"""Version of the projection: exclusion list + row ordering. Bump on any change."""

EXCLUSION_FIELDS = frozenset({"emittedAt", "generatedAt", "definitionId"})
"""The closed D-04 exclusion list -- one explicit constant, pinned by an exact-set test."""


def project_verdict(envelope: dict) -> dict:
    """Return the D-04 verdict projection of ``envelope`` -- a new dict.

    Deep-copies the input, drops exactly the keys named in :data:`EXCLUSION_FIELDS`,
    and sorts ``rows`` per ``spec/EVIDENCE-CONTRACT.md`` section 4: ascending by
    ``objectId``, ties broken by ``ruleId`` (mirroring ``evidence_contract._sort_key``).
    A missing or empty ``rows`` key stays exactly that way. The input is never mutated.
    """
    raise NotImplementedError


def verdict_projection_hash(envelope: dict) -> str:
    """Canonical hash of :func:`project_verdict` of ``envelope``.

    64-character uppercase SHA-256 hex, from ``canonical_json.hash_canonical``.
    """
    raise NotImplementedError
def _row_sort_key(row: dict) -> tuple[str, str]:
    """Row identity sort key: ``(objectId, ruleId)``.

    Mirrors ``evidence_contract._sort_key`` (section 4 ordering: objectId ascending,
    ties broken by ruleId). Absent keys sort as the empty string, so a malformed row
    never raises here -- validating the envelope is the caller's job, not this module's.
    """
    return (row.get("objectId", ""), row.get("ruleId", ""))


def project_verdict(envelope: dict) -> dict:
    """Return the D-04 verdict projection of ``envelope`` -- a new dict.

    Deep-copies the input, drops exactly the keys named in :data:`EXCLUSION_FIELDS`,
    and sorts ``rows`` per ``spec/EVIDENCE-CONTRACT.md`` section 4: ascending by
    ``objectId``, ties broken by ``ruleId`` (mirroring ``evidence_contract._sort_key``).
    A missing or empty ``rows`` key stays exactly that way. The input is never mutated.
    """
    projected = {k: v for k, v in copy.deepcopy(envelope).items() if k not in EXCLUSION_FIELDS}
    rows = projected.get("rows")
    if isinstance(rows, list) and rows:
        projected["rows"] = sorted(rows, key=_row_sort_key)
    return projected


def verdict_projection_hash(envelope: dict) -> str:
    """Canonical hash of :func:`project_verdict` of ``envelope``.

    64-character uppercase SHA-256 hex, from ``canonical_json.hash_canonical``.
    """
    return canonical_json.hash_canonical(project_verdict(envelope))
