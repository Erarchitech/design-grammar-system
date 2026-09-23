"""Projection-hash tests for the DE-01 repeat benchmark (plan 1204-01).

This file is 1204-01's projection-hash test home. Plan 1204-05 (wave 2) **appends**
runner-orchestration tests as new classes *below* the projection-hash classes defined
here -- the cross-plan seam. To keep that append safe:

- ``_envelope`` and ``_row`` are module-level builders, not class attributes, so a new
  class can reuse them without touching this file's existing classes.
- The projection-hash classes are self-contained: they import nothing beyond the module
  under test, ``evidence_contract``, and the standard library, so 1204-05's runner tests
  can add heavier imports (leg runners, subprocess mocks, fixture paths) without
  disturbing them.

This suite needs no live stack: no leg is run, no service is contacted. The only
subprocess spawned is a fresh interpreter computing the same pure projection hash
(``TestProjectionHashCrossProcess``), with the payload on stdin and no shell involved.
"""

from __future__ import annotations

import copy
import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent.parent.parent
TOOLS_DE01_DIR = REPO_ROOT / "tools" / "de01"
DATA_SERVICE_DIR = REPO_ROOT / "data-service"
for _path in (str(TOOLS_DE01_DIR), str(DATA_SERVICE_DIR)):
    if _path not in sys.path:
        sys.path.insert(0, _path)

import evidence_contract  # noqa: E402
import projection_hash  # noqa: E402
from projection_hash import (  # noqa: E402
    EXCLUSION_FIELDS,
    PROJECTION_VERSION,
    project_verdict,
    verdict_projection_hash,
)


def _row(rule_id: str, object_id: str, status: str, warnings: list[str] | None = None) -> dict:
    """Synthetic evidence row (mirrors tools/de01/tests/test_de01_runner.py:47-51)."""
    row = {"ruleId": rule_id, "objectId": object_id, "canonicalStatus": status}
    if warnings is not None:
        row["warnings"] = warnings
    return row


def _envelope(rows: list[dict], service_name: str = "svc", stage: str = "test") -> dict:
    """Synthetic schema-conformant evidence envelope (mirrors test_de01_runner.py:30-44)."""
    return {
        "contractVersion": "1.0.0",
        "canonicalizationVersion": 1,
        "project": "DG-1200-GOLDEN",
        "definitionId": "def-golden-01",
        "serviceName": service_name,
        "serviceVersion": "1.0.0",
        "emittedAt": "2026-09-20T00:00:00Z",
        "stage": stage,
        "canonicalStatus": rows[0]["canonicalStatus"] if rows else "not_evaluated",
        "rows": rows,
    }


def _baseline_envelope() -> dict:
    """The shared baseline: two rows, one carrying a warning, already in section 4 order."""
    return _envelope(
        [
            _row("R_GOLD_HEIGHT_MAX_75_V", "OBJ-1", "passed"),
            _row("R_GOLD_HEIGHT_MAX_75_V", "OBJ-2", "failed", warnings=["height 80 > 75"]),
        ],
        service_name="data-service",
        stage="verdict",
    )


class TestProjectionHash:
    """Task 1 tracer: the projection hashes a validated envelope, stably, without mutating it."""

    def test_verdict_projection_hash_is_stable_across_repeated_calls(self):
        envelope = _baseline_envelope()
        first = verdict_projection_hash(envelope)
        second = verdict_projection_hash(envelope)
        assert first == second
        assert len(first) == 64
        assert first == first.upper()

    def test_excluded_fields_do_not_change_the_hash(self):
        """Every D-04 excluded field is invisible to the hash: emittedAt, definitionId,
        and an injected report-level generatedAt."""
        baseline = verdict_projection_hash(_baseline_envelope())

        emitted_at_mutated = _baseline_envelope()
        emitted_at_mutated["emittedAt"] = "2031-12-31T23:59:59Z"
        assert verdict_projection_hash(emitted_at_mutated) == baseline

        definition_id_mutated = _baseline_envelope()
        definition_id_mutated["definitionId"] = "RUN-SOME-OTHER-RUN"
        assert verdict_projection_hash(definition_id_mutated) == baseline

        generated_at_injected = _baseline_envelope()
        generated_at_injected["generatedAt"] = "2031-12-31T23:59:59Z"
        assert verdict_projection_hash(generated_at_injected) == baseline

    def test_mutated_canonical_status_changes_the_hash(self):
        """D-04 negative control: a status flip is a finding, and the hash must show it."""
        baseline = verdict_projection_hash(_baseline_envelope())

        mutated = _baseline_envelope()
        assert mutated["rows"][0]["canonicalStatus"] == "passed"
        mutated["rows"][0]["canonicalStatus"] = "failed"

        assert verdict_projection_hash(mutated) != baseline

    def test_projection_never_mutates_the_input_envelope(self):
        envelope = _baseline_envelope()
        untouched = copy.deepcopy(envelope)

        project_verdict(envelope)
        verdict_projection_hash(envelope)

        assert envelope == untouched

    def test_baseline_envelope_is_schema_valid(self):
        """The synthetic baseline is real contract input, not an invented shape."""
        model = evidence_contract.EvidenceEnvelope(**_baseline_envelope())
        evidence_contract.validate_envelope(model)


# --- Task 2: negative-control matrix ------------------------------------------------
#
# Each arm mutates exactly one field *outside* EXCLUSION_FIELDS and asserts the hash
# moves (D-04: everything not excluded is included). The mutation is applied to a fresh
# deep copy of the baseline, so arms are independent.

def _mutate_row_status(envelope: dict) -> None:
    envelope["rows"][1]["canonicalStatus"] = "passed"


def _mutate_row_warnings_text(envelope: dict) -> None:
    envelope["rows"][1]["warnings"] = ["height 81 > 75"]


def _mutate_row_warnings_appended(envelope: dict) -> None:
    envelope["rows"][1]["warnings"].append("tolerance widened")


def _mutate_row_detail(envelope: dict) -> None:
    envelope["rows"][0]["detail"] = "evaluated against rule R_GOLD_HEIGHT_MAX_75_V"


def _mutate_envelope_status(envelope: dict) -> None:
    envelope["canonicalStatus"] = "error"


def _mutate_stage(envelope: dict) -> None:
    envelope["stage"] = "published"


def _mutate_service_name(envelope: dict) -> None:
    envelope["serviceName"] = "dg-reasoner"


def _mutate_service_version(envelope: dict) -> None:
    envelope["serviceVersion"] = "2.0.0"


def _set_envelope_input_hash(envelope: dict) -> None:
    envelope["inputHash"] = "A" * 64


def _mutate_envelope_input_hash(envelope: dict) -> None:
    envelope["inputHash"] = "B" * 64


def _set_envelope_output_hash(envelope: dict) -> None:
    envelope["outputHash"] = "C" * 64


def _mutate_envelope_output_hash(envelope: dict) -> None:
    envelope["outputHash"] = "D" * 64


def _scramble_rows(envelope: dict) -> None:
    envelope["rows"] = list(reversed(envelope["rows"]))


def _empty_row_warnings(envelope: dict) -> None:
    envelope["rows"][1]["warnings"] = []


class TestProjectionHashNegativeControl:
    """D-04 negative controls: inclusion mutations change the hash, row order does not."""

    @pytest.mark.parametrize(
        "mutate",
        [
            pytest.param(_mutate_row_status, id="row-canonical-status"),
            pytest.param(_mutate_row_warnings_text, id="row-warnings-text"),
            pytest.param(_mutate_row_warnings_appended, id="row-warnings-appended"),
            pytest.param(_mutate_row_detail, id="row-detail"),
            pytest.param(_mutate_envelope_status, id="envelope-canonical-status"),
            pytest.param(_mutate_stage, id="stage"),
            pytest.param(_mutate_service_name, id="service-name"),
            pytest.param(_mutate_service_version, id="service-version"),
            pytest.param(_set_envelope_input_hash, id="input-hash-added"),
            pytest.param(_mutate_envelope_input_hash, id="input-hash-changed"),
            pytest.param(_set_envelope_output_hash, id="output-hash-added"),
            pytest.param(_mutate_envelope_output_hash, id="output-hash-changed"),
        ],
    )
    def test_single_field_mutation_changes_the_hash(self, mutate):
        baseline = _baseline_envelope()
        baseline_hash = verdict_projection_hash(baseline)

        mutated = copy.deepcopy(baseline)
        mutate(mutated)

        assert mutated != baseline, f"{mutate.__name__} did not mutate the envelope"
        assert verdict_projection_hash(mutated) != baseline_hash, (
            f"{mutate.__name__} did not change the projection hash -- it is inside "
            "EXCLUSION_FIELDS or the projection dropped it"
        )

    def test_reordered_rows_hash_identically(self):
        """Section 4 ordering is canonicalized, so a scrambled input hashes the same.

        Without the sort step in project_verdict this test fails -- that is the point.
        """
        baseline = _baseline_envelope()
        assert [r["objectId"] for r in baseline["rows"]] == ["OBJ-1", "OBJ-2"]

        scrambled = _baseline_envelope()
        _scramble_rows(scrambled)
        assert [r["objectId"] for r in scrambled["rows"]] == ["OBJ-2", "OBJ-1"]

        assert verdict_projection_hash(scrambled) == verdict_projection_hash(baseline)

    def test_empty_warnings_differs_from_populated_warnings(self):
        """An empty warnings list is not the same evidence as a populated one."""
        baseline = _baseline_envelope()
        assert baseline["rows"][1]["warnings"] == ["height 80 > 75"]

        emptied = _baseline_envelope()
        _empty_row_warnings(emptied)
        assert emptied["rows"][1]["warnings"] == []

        assert verdict_projection_hash(emptied) != verdict_projection_hash(baseline)

    # --- Closed-set pinning (D-04): the exclusion list and version cannot drift
    # unnoticed. Any field added to or removed from the list fails the exact-set test;
    # any silent reordering change fails the parity test against _sort_key.

    def test_exclusion_fields_equals_the_closed_d04_set(self):
        assert EXCLUSION_FIELDS == frozenset({"emittedAt", "generatedAt", "definitionId"})

    def test_projection_version_is_1(self):
        assert PROJECTION_VERSION == 1

    def test_projection_row_order_matches_evidence_contract_sort_key(self):
        """Parity with evidence_contract._sort_key (spec/EVIDENCE-CONTRACT.md section 4).

        ``_sort_key`` operates on the contract's row model, so the reference order is
        computed over model-typed rows; the projection must agree on the resulting
        (objectId, ruleId) identity order while returning plain dicts.
        """
        scrambled = _baseline_envelope()
        _scramble_rows(scrambled)

        projected = project_verdict(scrambled)["rows"]
        expected = sorted(
            (evidence_contract.EvidenceRow(**row) for row in scrambled["rows"]),
            key=evidence_contract._sort_key,
        )

        assert [(row["objectId"], row["ruleId"]) for row in projected] == [
            (row.objectId, row.ruleId) for row in expected
        ]
        assert len(projected) == len(expected)


# --- Task 2: cross-process hash-seed guard ------------------------------------------
#
# The projection must not depend on CPython's per-process string-hash randomization
# (D-05 rationale). A fresh interpreter computing the same hash is the only way to prove
# it: an in-process repetition shares the parent's hash seed and would not catch a leak.

_CODE = (
    "import json, sys;"
    " sys.path.insert(0, {data_service!r});"
    " sys.path.insert(0, {tools_de01!r});"
    " import projection_hash;"
    " envelope = json.loads(sys.stdin.read());"
    " print(projection_hash.verdict_projection_hash(envelope))"
).format(data_service=str(DATA_SERVICE_DIR), tools_de01=str(TOOLS_DE01_DIR))


class TestProjectionHashCrossProcess:
    """D-04/D-05: the hash is process- and hash-seed independent.

    Payload travels on stdin to a fixed, literal ``-c`` program; the shell is never
    involved and no user-controlled input reaches the interpreter.
    """

    @staticmethod
    def _subprocess_hash(envelope: dict, env: dict | None = None) -> str:
        completed = subprocess.run(
            [sys.executable, "-c", _CODE],
            input=json.dumps(envelope),
            text=True,
            capture_output=True,
            check=True,
            timeout=60,
            env=env,
        )
        return completed.stdout.strip()

    def test_fresh_subprocess_returns_the_in_process_hash(self):
        envelope = _baseline_envelope()
        assert self._subprocess_hash(envelope) == verdict_projection_hash(envelope)

    @pytest.mark.parametrize("hash_seed", ["0", "12345"])
    def test_forced_hash_seeds_return_the_in_process_hash(self, hash_seed):
        envelope = _baseline_envelope()
        env = dict(os.environ)
        env["PYTHONHASHSEED"] = hash_seed
        assert self._subprocess_hash(envelope, env=env) == verdict_projection_hash(envelope)

    def test_subprocess_diverges_on_a_mutated_envelope(self):
        """Proves the subprocess path computes the hash rather than echoing a value."""
        envelope = _baseline_envelope()
        baseline_subprocess = self._subprocess_hash(envelope)

        mutated = copy.deepcopy(envelope)
        mutated["rows"][0]["canonicalStatus"] = "failed"
        env = dict(os.environ)
        env["PYTHONHASHSEED"] = "12345"

        assert self._subprocess_hash(mutated, env=env) != baseline_subprocess
        assert self._subprocess_hash(mutated, env=env) != verdict_projection_hash(envelope)