"""Unit tests for tools/de01/report.py's compare_legs, plus the DE-01 wrapper test
(plan 1200-05, Task 2).

Unit tests use synthetic LegResult objects with no live services -- the ``-k "not
live"`` selector in tools/de01/README.md and this plan's <verify> block excludes the
wrapper test at the bottom of this file, which drives the real runner against the
golden fixture and requires the dev stack.
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent.parent.parent
TOOLS_DE01_DIR = REPO_ROOT / "tools" / "de01"
if str(TOOLS_DE01_DIR) not in sys.path:
    sys.path.insert(0, str(TOOLS_DE01_DIR))

from legs import LegResult  # noqa: E402
from report import compare_legs  # noqa: E402


def _envelope(rows: list[dict], service_name: str = "svc", stage: str = "test") -> dict:
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


def _row(rule_id: str, object_id: str, status: str, warnings: list[str] | None = None) -> dict:
    row = {"ruleId": rule_id, "objectId": object_id, "canonicalStatus": status}
    if warnings is not None:
        row["warnings"] = warnings
    return row


class TestCompareLegsAgreement:
    def test_identical_statuses_across_all_available_legs_counts_zero_of_both(self):
        leg_a = LegResult(
            "a", True, _envelope([_row("R1", "OBJ1", "passed")]),
        )
        leg_b = LegResult(
            "b", True, _envelope([_row("R1", "OBJ1", "passed")]),
        )
        result = compare_legs({"a": leg_a, "b": leg_b})
        assert result.silent_disagreement_count == 0
        assert result.declared_non_equivalences == []
        assert len(result.rows) == 1
        assert result.rows[0].classification == "agreement"


class TestCompareLegsSilentDisagreement:
    def test_differing_statuses_with_no_declared_reason_counts_one_silent_disagreement(self):
        leg_a = LegResult("a", True, _envelope([_row("R1", "OBJ1", "passed")]))
        leg_b = LegResult("b", True, _envelope([_row("R1", "OBJ1", "failed")]))
        result = compare_legs({"a": leg_a, "b": leg_b})
        assert result.silent_disagreement_count == 1
        assert result.declared_non_equivalences == []
        assert result.rows[0].classification == "silent_disagreement"

    def test_lone_non_declarable_status_beside_declarable_is_silent(self):
        """CR-02 regression: the exact defect DE-01 exists to catch. One leg
        reports a genuine verdict (``passed``) and the other degrades to
        ``unsupported`` with a warning. The docstring's rule (report.py lines
        4-17) requires EVERY differing leg's status to be declarable-and-warned
        before a difference is declared -- ``passed`` is not itself a declarable
        non-result, so wrapping the other leg's status in a warning does not make
        this pair's difference declared. It must count as a silent disagreement."""
        leg_a = LegResult("a", True, _envelope([_row("R1", "OBJ1", "passed")]))
        leg_b = LegResult(
            "b",
            True,
            _envelope([_row("R1", "OBJ1", "unsupported", warnings=["no branch for this atom type"])]),
        )
        result = compare_legs({"a": leg_a, "b": leg_b})
        assert result.silent_disagreement_count == 1
        assert result.declared_non_equivalences == []
        assert result.rows[0].classification == "silent_disagreement"

    def test_unknown_beside_declarable_warned_status_is_silent(self):
        """Reviewer's second reproduction (1200-REVIEW.md CR-02): ``unknown`` is a
        genuine binding-resolution outcome under D-05, not a non-result, so a
        difference against a declarable-and-warned status on another leg behaves
        the same way ``passed`` does -- silent, not declared."""
        leg_a = LegResult("a", True, _envelope([_row("R1", "OBJ1", "unknown")]))
        leg_b = LegResult(
            "b",
            True,
            _envelope([_row("R1", "OBJ1", "unsupported", warnings=["no branch for this atom type"])]),
        )
        result = compare_legs({"a": leg_a, "b": leg_b})
        assert result.silent_disagreement_count == 1
        assert result.declared_non_equivalences == []
        assert result.rows[0].classification == "silent_disagreement"

    def test_two_declarable_warned_statuses_differing_is_still_declared(self):
        """Over-correction guard: two DIFFERING statuses that are both declarable
        and both warned must still classify as a declared non-equivalence. Without
        this test, firing the guard on any non-empty set of non-declarable
        statuses could be satisfied by a trivially over-strict implementation that
        collapses every difference into silent."""
        leg_a = LegResult(
            "a", True, _envelope([_row("R1", "OBJ1", "unsupported", warnings=["reason a"])])
        )
        leg_b = LegResult(
            "b", True, _envelope([_row("R1", "OBJ1", "error", warnings=["reason b"])])
        )
        result = compare_legs({"a": leg_a, "b": leg_b})
        assert result.silent_disagreement_count == 0
        assert len(result.declared_non_equivalences) == 1
        assert result.rows[0].classification == "declared_non_equivalence"

    def test_declarable_status_without_warning_is_still_silent(self):
        """A declarable-vocabulary status (unsupported/error/not_evaluated/indeterminate)
        with NO warning does not get a free pass -- the warning requirement is real,
        not decorative."""
        leg_a = LegResult("a", True, _envelope([_row("R1", "OBJ1", "passed")]))
        leg_b = LegResult("b", True, _envelope([_row("R1", "OBJ1", "unsupported", warnings=[])]))
        result = compare_legs({"a": leg_a, "b": leg_b})
        assert result.silent_disagreement_count == 1
        assert result.rows[0].classification == "silent_disagreement"

    def test_two_non_declarable_statuses_differing_is_never_declared(self):
        """passed vs failed is never declarable, even if a third leg reports
        unsupported with a warning for the same pair."""
        leg_a = LegResult("a", True, _envelope([_row("R1", "OBJ1", "passed")]))
        leg_b = LegResult("b", True, _envelope([_row("R1", "OBJ1", "failed")]))
        leg_c = LegResult(
            "c", True, _envelope([_row("R1", "OBJ1", "unsupported", warnings=["reason"])])
        )
        result = compare_legs({"a": leg_a, "b": leg_b, "c": leg_c})
        assert result.silent_disagreement_count == 1
        assert result.rows[0].classification == "silent_disagreement"


class TestCompareLegsPairPresence:
    def test_pair_present_in_only_one_leg_still_appears_in_output_rows(self):
        leg_a = LegResult("a", True, _envelope([_row("R1", "OBJ1", "passed")]))
        leg_b = LegResult("b", True, _envelope([]))
        result = compare_legs({"a": leg_a, "b": leg_b})
        assert len(result.rows) == 1
        row = result.rows[0]
        assert row.rule_id == "R1"
        assert row.object_id == "OBJ1"
        assert row.per_leg["a"]["present"] is True
        assert row.per_leg["b"]["present"] is False

    def test_value_equal_but_distinct_objects_are_not_deduplicated(self):
        """Two rows with different objectId are never merged even if every other
        field is identical (spec/EVIDENCE-CONTRACT.md section 4 identity rule)."""
        leg_a = LegResult(
            "a",
            True,
            _envelope(
                [
                    _row("R1", "OBJ1", "passed"),
                    _row("R1", "OBJ2", "passed"),
                ]
            ),
        )
        result = compare_legs({"a": leg_a})
        assert len(result.rows) == 2
        object_ids = {row.object_id for row in result.rows}
        assert object_ids == {"OBJ1", "OBJ2"}


class TestCompareLegsOrdering:
    def test_rows_ordered_ascending_by_object_id_ties_by_rule_id(self):
        leg_a = LegResult(
            "a",
            True,
            _envelope(
                [
                    _row("R2", "OBJ_B", "passed"),
                    _row("R1", "OBJ_A", "passed"),
                    _row("R1", "OBJ_B", "passed"),
                ]
            ),
        )
        result = compare_legs({"a": leg_a})
        pairs = [(row.object_id, row.rule_id) for row in result.rows]
        assert pairs == sorted(pairs)


class TestCompareLegsUnavailableLeg:
    def test_unavailable_leg_all_error_rows_are_visible_not_dropped(self):
        leg_a = LegResult("a", True, _envelope([_row("R1", "OBJ1", "passed")]))
        leg_b = LegResult(
            "b",
            False,
            _envelope([_row("R1", "OBJ1", "error", warnings=["service unreachable"])]),
            error="connection refused",
        )
        result = compare_legs({"a": leg_a, "b": leg_b})
        assert len(result.rows) == 1
        # error is in the declarable vocabulary and carries a warning, but the
        # OTHER leg's status (passed) is not itself declarable -- the docstring's
        # rule (report.py lines 4-17) requires EVERY differing leg's status to be
        # declarable-and-warned before a difference is declared. `passed` is a
        # lone non-declarable status here, so this is silent, not declared
        # (CR-02: this assertion previously certified the same defect the
        # dedicated regression tests in TestCompareLegsSilentDisagreement catch).
        # The unavailable leg's error row is still visible in the output, which
        # is this test's actual subject -- see len(result.rows) == 1 above.
        assert result.rows[0].classification == "silent_disagreement"
        assert result.silent_disagreement_count == 1


class TestCompareLegsNeverLosesADifference:
    """Backstop tests asserting the module's own stated invariant: no branch
    returns agreement for unequal statuses, no coercion/normalization happens
    before comparison, and no pair is skipped for lacking a leg."""

    def test_no_silent_coercion_of_a_genuinely_different_status_set(self):
        leg_a = LegResult("a", True, _envelope([_row("R1", "OBJ1", "no_population")]))
        leg_b = LegResult("b", True, _envelope([_row("R1", "OBJ1", "not_evaluated", warnings=[])]))
        result = compare_legs({"a": leg_a, "b": leg_b})
        # no_population is not in the declarable set, not_evaluated has no warning --
        # this must not silently collapse to agreement.
        assert result.rows[0].classification == "silent_disagreement"
        assert result.silent_disagreement_count == 1


class TestReportSchemaCanonicalStatusPinning:
    def test_report_schema_canonical_status_matches_contract_schema(self):
        """report_schema.json's local $defs.CanonicalStatus.enum (a same-document
        pin, required so a bare jsonschema.validate(instance, schema) call resolves
        without a caller-supplied Registry -- see the schema's own top-level
        description) must never drift from spec/evidence-contract.schema.json's
        $defs.CanonicalStatus.enum, the single authored source of truth (D-02)."""
        import json as json_mod

        contract_schema = json_mod.loads(
            (REPO_ROOT / "spec" / "evidence-contract.schema.json").read_text(encoding="utf-8")
        )
        report_schema = json_mod.loads(
            (REPO_ROOT / "tools" / "de01" / "report_schema.json").read_text(encoding="utf-8")
        )
        contract_enum = set(contract_schema["$defs"]["CanonicalStatus"]["enum"])
        report_enum = set(report_schema["$defs"]["CanonicalStatus"]["enum"])
        assert report_enum == contract_enum


# ── Wrapper test: run the real runner against the golden fixture ────────────────


@pytest.mark.live
def test_de01_runner_against_golden_fixture_has_zero_silent_disagreements(tmp_path):
    """Runs the actual CLI against the golden fixture and asserts the JSON report
    exists with silent_disagreement_count == 0. Deselect with `-k "not live"` when
    the dev stack is down. Fails (never skips silently) naming the missing
    precondition when the report is absent.
    """
    out_dir = tmp_path / "de01"
    result = subprocess.run(
        [
            sys.executable,
            str(REPO_ROOT / "tools" / "de01" / "run_de01.py"),
            "--fixture",
            str(REPO_ROOT / "fixtures" / "golden" / "fixture.json"),
            "--out-dir",
            str(out_dir),
        ],
        capture_output=True,
        text=True,
        timeout=180,
    )

    report_path = out_dir / "de01-report.json"
    if not report_path.is_file():
        pytest.fail(
            "DE-01 report was not produced at "
            f"{report_path}. stdout: {result.stdout}\nstderr: {result.stderr}\n"
            "This means the runner itself failed to write a report -- check that the "
            "dev stack is up per tools/de01/README.md's per-leg precondition table."
        )

    report = json.loads(report_path.read_text(encoding="utf-8"))
    assert report["silent_disagreement_count"] == 0, (
        f"silent_disagreement_count={report['silent_disagreement_count']} -- "
        f"see {out_dir / 'de01-report.md'} for the declared-vs-silent breakdown."
    )
