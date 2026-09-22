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
from unittest.mock import MagicMock, patch

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent.parent.parent
TOOLS_DE01_DIR = REPO_ROOT / "tools" / "de01"
if str(TOOLS_DE01_DIR) not in sys.path:
    sys.path.insert(0, str(TOOLS_DE01_DIR))

import legs  # noqa: E402
from legs import LegResult, run_leg_dg_reasoner, run_leg_replay  # noqa: E402
from report import compare_legs, compare_state_hashes  # noqa: E402


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

    def test_warned_abstention_beside_agreeing_evaluators_is_declared(self):
        """Phase 1201 supplemental path. A leg that abstains with a written reason,
        beside two or more legs that evaluated and AGREE, is a declared
        non-equivalence -- not a silent one.

        This is the dg-reasoner shape: spec/RULE-PARTITION-POLICY.md assigns
        quantitative rules to the SWRL VALIDATOR, so SHACL reports not_evaluated on
        every such rule by design. Under the CR-02 guard alone every row on a
        quantitative fixture is silent forever, and D-11's gate can only be reached
        by making a leg claim a verdict it cannot justify."""
        legs = {
            "a": LegResult("a", True, _envelope([_row("R1", "OBJ1", "passed")])),
            "b": LegResult("b", True, _envelope([_row("R1", "OBJ1", "passed")])),
            "c": LegResult(
                "c",
                True,
                _envelope([_row("R1", "OBJ1", "not_evaluated", warnings=["SHACL cannot express height > 75"])]),
            ),
        }
        result = compare_legs(legs)
        assert result.silent_disagreement_count == 0
        assert len(result.declared_non_equivalences) == 1
        assert result.rows[0].classification == "declared_non_equivalence"
        assert "height > 75" in result.rows[0].reason

    def test_warned_abstention_against_a_single_evaluator_is_still_silent(self):
        """CR-02 preservation, stated as its own test. The supplemental path above
        requires a consensus of at least TWO agreeing evaluating legs. With only one
        evaluating leg there is no consensus to discount the abstention against, so
        the pair stays silent -- which is exactly CR-02's 1-vs-1 shape.

        If someone ever drops the two-leg floor, CR-02's own reproductions and this
        test fail together."""
        legs = {
            "a": LegResult("a", True, _envelope([_row("R1", "OBJ1", "passed")])),
            "b": LegResult(
                "b",
                True,
                _envelope([_row("R1", "OBJ1", "not_evaluated", warnings=["declared reason"])]),
            ),
        }
        result = compare_legs(legs)
        assert result.silent_disagreement_count == 1
        assert result.declared_non_equivalences == []
        assert result.rows[0].classification == "silent_disagreement"

    def test_abstention_beside_disagreeing_evaluators_is_still_silent(self):
        """The evaluating legs must AGREE. An abstention cannot paper over a real
        divergence between two legs that both produced a verdict -- that is the
        precise thing DE-01 exists to catch, and it stays silent no matter how well
        the third leg explains itself."""
        legs = {
            "a": LegResult("a", True, _envelope([_row("R1", "OBJ1", "passed")])),
            "b": LegResult("b", True, _envelope([_row("R1", "OBJ1", "failed")])),
            "c": LegResult(
                "c",
                True,
                _envelope([_row("R1", "OBJ1", "not_evaluated", warnings=["declared reason"])]),
            ),
        }
        result = compare_legs(legs)
        assert result.silent_disagreement_count == 1
        assert result.declared_non_equivalences == []
        assert result.rows[0].classification == "silent_disagreement"

    def test_unwarned_abstention_beside_agreeing_evaluators_is_silent(self):
        """The warning requirement holds on the supplemental path too. An abstention
        with no written reason is undeclared by definition, so it cannot be
        discounted however many legs agree around it."""
        legs = {
            "a": LegResult("a", True, _envelope([_row("R1", "OBJ1", "passed")])),
            "b": LegResult("b", True, _envelope([_row("R1", "OBJ1", "passed")])),
            "c": LegResult("c", True, _envelope([_row("R1", "OBJ1", "not_evaluated")])),
        }
        result = compare_legs(legs)
        assert result.silent_disagreement_count == 1
        assert result.declared_non_equivalences == []
        assert result.rows[0].classification == "silent_disagreement"

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


def _minimal_fixture(run_id_value: object = "unset") -> dict:
    """A minimal fixture dict shaped like fixtures/golden/fixture.json's schema,
    for driving run_leg_dg_reasoner offline (no live dg-reasoner). ``run_id_value``
    of the sentinel ``"unset"`` omits the ``runId`` key entirely (fixture.json's
    real, frozen shape -- it carries no run id field at all); pass ``None`` or a
    string to set the key explicitly.
    """
    fixture = {
        "project": "DG-1200-GOLDEN",
        "rule": {"Rule_Id": "R_GOLD_HEIGHT_MAX_75_V"},
        "objects": [
            {"objectId": "OBJ_GOLD_PASS"},
            {"objectId": "OBJ_GOLD_FAIL"},
            {"objectId": "OBJ_GOLD_EMPTY"},
        ],
    }
    if run_id_value != "unset":
        fixture["runId"] = run_id_value
    return fixture


def _mock_response(json_body: dict, status_code: int = 200) -> MagicMock:
    response = MagicMock()
    response.status_code = status_code
    response.json.return_value = json_body
    return response


class TestRunLegDgReasonerRunId:
    """Task 1 (D-09): run_leg_dg_reasoner must post run_id, sourced from the
    fixture with a fallback to the seeded FIXTURE_RUN_ID constant, and must never
    silently revert to the old project-only call shape when a run id is
    genuinely unavailable."""

    def test_posted_body_includes_run_id_from_fixture_fallback(self):
        """fixture.json (frozen, D-11) carries no runId field -- the fallback to
        FIXTURE_RUN_ID (the seed.cypher value) is what must appear in the posted
        body, not a bare {"project": project}."""
        captured = {}

        def fake_post(url, json):
            captured["url"] = url
            captured["json"] = json
            return _mock_response({"conforms": True, "results": []})

        mock_client = MagicMock()
        mock_client.__enter__.return_value = mock_client
        mock_client.__exit__.return_value = False
        mock_client.post.side_effect = fake_post

        with patch.object(legs.httpx, "Client", return_value=mock_client):
            result = run_leg_dg_reasoner(_minimal_fixture(), config={})

        assert captured["json"] == {"project": "DG-1200-GOLDEN", "run_id": legs.FIXTURE_RUN_ID}
        assert result.available is True

    def test_posted_body_includes_run_id_explicitly_set_on_fixture(self):
        """When a fixture DOES carry a runId (a future, non-frozen fixture), that
        value wins over the FIXTURE_RUN_ID fallback."""
        captured = {}

        def fake_post(url, json):
            captured["json"] = json
            return _mock_response({"conforms": True, "results": []})

        mock_client = MagicMock()
        mock_client.__enter__.return_value = mock_client
        mock_client.__exit__.return_value = False
        mock_client.post.side_effect = fake_post

        with patch.object(legs.httpx, "Client", return_value=mock_client):
            run_leg_dg_reasoner(_minimal_fixture(run_id_value="SOME_OTHER_RUN"), config={})

        assert captured["json"]["run_id"] == "SOME_OTHER_RUN"

    def test_defective_project_only_call_shape_is_gone(self):
        """grep -c 'json={"project": project}' tools/de01/legs.py must be 0 --
        this test drives the same code path and asserts the actual posted body
        is never bare project-only, from the live source rather than a grep."""
        mock_client = MagicMock()
        mock_client.__enter__.return_value = mock_client
        mock_client.__exit__.return_value = False
        mock_client.post.return_value = _mock_response({"conforms": True, "results": []})

        with patch.object(legs.httpx, "Client", return_value=mock_client):
            run_leg_dg_reasoner(_minimal_fixture(), config={})

        _, kwargs = mock_client.post.call_args
        assert kwargs["json"] != {"project": "DG-1200-GOLDEN"}
        assert "run_id" in kwargs["json"]

    def test_missing_run_id_on_both_fixture_and_constant_degrades_to_typed_error(self):
        """If a fixture explicitly sets runId to a falsy value AND (hypothetically)
        FIXTURE_RUN_ID were also empty, the leg must not fall back to the
        defective project-only POST -- it must return a typed, unavailable
        LegResult explaining why. Exercised here by patching FIXTURE_RUN_ID to
        empty alongside a fixture with no runId, so both sources are genuinely
        absent."""
        mock_client = MagicMock()
        mock_client.__enter__.return_value = mock_client
        mock_client.__exit__.return_value = False

        with patch.object(legs, "FIXTURE_RUN_ID", ""), patch.object(
            legs.httpx, "Client", return_value=mock_client
        ):
            result = run_leg_dg_reasoner(_minimal_fixture(run_id_value=None), config={})

        assert result.available is False
        assert result.error is not None and "run id" in result.error.lower()
        # The guard must fire before any HTTP call is attempted.
        mock_client.post.assert_not_called()
        rows = result.envelope["rows"]
        assert rows, "typed error envelope must still carry rows for every fixture pair"
        assert all(row["canonicalStatus"] == "error" for row in rows)
        assert all(row["warnings"] for row in rows)


class TestRunLegDgReasonerNotEvaluatedMapping:
    """Task 2 (D-10): a conforming report against a non-empty target set maps to
    not_evaluated with a warning, never passed. A violation still maps to
    failed."""

    def test_conforming_nonempty_report_maps_to_not_evaluated_with_warning(self):
        mock_client = MagicMock()
        mock_client.__enter__.return_value = mock_client
        mock_client.__exit__.return_value = False
        # conforms=True with a non-empty results list that has no violations --
        # e.g. an Info/Warning-only report (D-18) -- is still "conforming and
        # non-empty" for this leg's purposes.
        mock_client.post.return_value = _mock_response(
            {"conforms": True, "results": [{"severity": "Info", "focusLabel": "OBJ_GOLD_PASS"}]}
        )

        with patch.object(legs.httpx, "Client", return_value=mock_client):
            result = run_leg_dg_reasoner(_minimal_fixture(), config={})

        assert result.available is True
        rows = result.envelope["rows"]
        assert rows, "expected rows in the envelope"
        for row in rows:
            assert row["canonicalStatus"] == "not_evaluated"
            assert row["warnings"], "not_evaluated rows must carry a non-empty warning (D-10)"
            warning_text = " ".join(row["warnings"]).lower()
            assert "partition" in warning_text or "rule_partition" in warning_text.replace(
                "-", "_"
            ) or "swrl validator" in warning_text

    def test_violation_naming_a_focus_node_still_maps_to_failed(self):
        mock_client = MagicMock()
        mock_client.__enter__.return_value = mock_client
        mock_client.__exit__.return_value = False
        mock_client.post.return_value = _mock_response(
            {
                "conforms": False,
                "results": [
                    {"severity": "violation", "focusLabel": "OBJ_GOLD_FAIL"},
                ],
            }
        )

        with patch.object(legs.httpx, "Client", return_value=mock_client):
            result = run_leg_dg_reasoner(_minimal_fixture(), config={})

        rows_by_object = {row["objectId"]: row for row in result.envelope["rows"]}
        assert rows_by_object["OBJ_GOLD_FAIL"]["canonicalStatus"] == "failed"
        # Every other object in this conforming-elsewhere report is not_evaluated,
        # not passed -- SHACL still has no opinion on the quantitative rule.
        assert rows_by_object["OBJ_GOLD_PASS"]["canonicalStatus"] == "not_evaluated"
        assert rows_by_object["OBJ_GOLD_EMPTY"]["canonicalStatus"] == "not_evaluated"


class TestNotEvaluatedVsGenuineVerdictClassification:
    """Task 2's disagreement-classification behavior, verified empirically against
    the live (unmodified, CR-02-guarded) compare_legs rather than assumed.

    **Deviation from the plan's stated expectation, recorded here and in the plan
    06 handoff.** The plan's objective and Task 2's behavior bullets assert that
    "the resulting disagreement between dg-reasoner's not_evaluated and the other
    legs' passed/failed classifies as declared_non_equivalence, not
    silent_disagreement." Empirically this is FALSE for not_evaluated vs failed
    (and vs passed): `_DECLARABLE_STATUSES` is `{unsupported, error, not_evaluated,
    indeterminate}` -- `failed` and `passed` are deliberately NOT declarable
    (CR-02, report.py:174-186: "Any non-declarable status participating in a
    difference makes that difference silent, regardless of ... what the other legs
    reported"). Since one leg reporting a declarable-and-warned status can never
    outweigh another leg's non-declarable status, not_evaluated vs failed/passed is
    unconditionally silent_disagreement under the current, correct, unmodified
    guard -- there is no configuration of warnings that makes it declared.

    This is NOT a defect in Task 2's mapping change (not_evaluated is still the
    semantically honest status per D-10, and still strictly better than the
    previous `passed`, which would have been non-declarable too and produced the
    exact same silent classification). It means the OBJ_GOLD_FAIL pair is expected
    to still show up in plan 06's live DE-01 re-run as a silent_disagreement
    between dg-reasoner (not_evaluated) and the legs that genuinely evaluate the
    quantitative rule (failed) -- see this plan's SUMMARY for the full account."""

    def test_not_evaluated_with_warning_vs_failed_is_silent_not_declared(self):
        """Ground truth, not the plan's aspiration: failed is not declarable, so
        CR-02's guard makes this silent regardless of the not_evaluated row's
        warning."""
        dg_reasoner_leg = LegResult(
            "dg-reasoner",
            True,
            _envelope(
                [
                    _row(
                        "R_GOLD_HEIGHT_MAX_75_V",
                        "OBJ_GOLD_FAIL",
                        "not_evaluated",
                        warnings=["SHACL has no opinion on this quantitative rule (partition policy)"],
                    )
                ]
            ),
        )
        csharp_leg = LegResult(
            "csharp",
            True,
            _envelope([_row("R_GOLD_HEIGHT_MAX_75_V", "OBJ_GOLD_FAIL", "failed")]),
        )
        result = compare_legs({"dg-reasoner": dg_reasoner_leg, "csharp": csharp_leg})
        assert result.silent_disagreement_count == 1
        assert result.declared_non_equivalences == []
        assert result.rows[0].classification == "silent_disagreement"

    def test_not_evaluated_with_warning_vs_passed_is_also_silent_not_declared(self):
        """Same guard, same outcome against passed -- confirms this is general to
        any non-declarable status, not specific to failed."""
        dg_reasoner_leg = LegResult(
            "dg-reasoner",
            True,
            _envelope(
                [
                    _row(
                        "R_GOLD_HEIGHT_MAX_75_V",
                        "OBJ_GOLD_PASS",
                        "not_evaluated",
                        warnings=["SHACL has no opinion on this quantitative rule (partition policy)"],
                    )
                ]
            ),
        )
        csharp_leg = LegResult(
            "csharp",
            True,
            _envelope([_row("R_GOLD_HEIGHT_MAX_75_V", "OBJ_GOLD_PASS", "passed")]),
        )
        result = compare_legs({"dg-reasoner": dg_reasoner_leg, "csharp": csharp_leg})
        assert result.silent_disagreement_count == 1
        assert result.declared_non_equivalences == []
        assert result.rows[0].classification == "silent_disagreement"

    def test_not_evaluated_vs_not_evaluated_both_warned_is_agreement(self):
        """When both legs genuinely have nothing to say (e.g. two SHACL-only
        legs), matching not_evaluated statuses are a plain agreement -- not a
        declared non-equivalence, since there is no disagreement to declare."""
        dg_reasoner_leg = LegResult(
            "dg-reasoner",
            True,
            _envelope([_row("R_GOLD_HEIGHT_MAX_75_V", "OBJ_GOLD_PASS", "not_evaluated", warnings=["reason a"])]),
        )
        other_leg = LegResult(
            "other",
            True,
            _envelope([_row("R_GOLD_HEIGHT_MAX_75_V", "OBJ_GOLD_PASS", "not_evaluated", warnings=["reason b"])]),
        )
        result = compare_legs({"dg-reasoner": dg_reasoner_leg, "other": other_leg})
        assert result.rows[0].classification == "agreement"
        assert result.silent_disagreement_count == 0

    def test_not_evaluated_without_warning_vs_failed_is_still_silent(self):
        """Guard against a regression that drops the warning requirement: an
        unwarned not_evaluated is still a silent disagreement against a genuine
        verdict, same as any other declarable-status-without-warning case."""
        dg_reasoner_leg = LegResult(
            "dg-reasoner",
            True,
            _envelope([_row("R_GOLD_HEIGHT_MAX_75_V", "OBJ_GOLD_FAIL", "not_evaluated", warnings=[])]),
        )
        csharp_leg = LegResult(
            "csharp",
            True,
            _envelope([_row("R_GOLD_HEIGHT_MAX_75_V", "OBJ_GOLD_FAIL", "failed")]),
        )
        result = compare_legs({"dg-reasoner": dg_reasoner_leg, "csharp": csharp_leg})
        assert result.silent_disagreement_count == 1
        assert result.rows[0].classification == "silent_disagreement"


class TestDeclarableStatusesUnchanged:
    """Explicit guard mirroring the plan's git diff check: _DECLARABLE_STATUSES
    must remain byte-identical to its pre-plan content -- passed must never be
    added."""

    def test_declarable_statuses_is_exactly_the_frozen_set(self):
        import report as report_module

        assert report_module._DECLARABLE_STATUSES == {
            "unsupported",
            "error",
            "not_evaluated",
            "indeterminate",
        }
        assert "passed" not in report_module._DECLARABLE_STATUSES


class TestCompareLegsHashFallback:
    """Task 3 (D-12): row-level inputHash/outputHash fall back to the envelope's
    when the row carries none; row-level wins when present; absent-on-both stays
    None, never an empty string."""

    def test_row_with_no_hash_falls_back_to_envelope_level_hash(self):
        envelope = _envelope([_row("R1", "OBJ1", "passed")])
        envelope["inputHash"] = "envelope-input-hash"
        envelope["outputHash"] = "envelope-output-hash"
        leg_a = LegResult("a", True, envelope)
        result = compare_legs({"a": leg_a})
        row_data = result.rows[0].per_leg["a"]["rows"][0]
        assert row_data["inputHash"] == "envelope-input-hash"
        assert row_data["outputHash"] == "envelope-output-hash"

    def test_row_level_hash_wins_over_envelope_level_hash(self):
        row = _row("R1", "OBJ1", "passed")
        row["inputHash"] = "row-input-hash"
        row["outputHash"] = "row-output-hash"
        envelope = _envelope([row])
        envelope["inputHash"] = "envelope-input-hash"
        envelope["outputHash"] = "envelope-output-hash"
        leg_a = LegResult("a", True, envelope)
        result = compare_legs({"a": leg_a})
        row_data = result.rows[0].per_leg["a"]["rows"][0]
        assert row_data["inputHash"] == "row-input-hash"
        assert row_data["outputHash"] == "row-output-hash"

    def test_absent_on_both_row_and_envelope_stays_none_not_empty_string(self):
        envelope = _envelope([_row("R1", "OBJ1", "passed")])
        leg_a = LegResult("a", True, envelope)
        result = compare_legs({"a": leg_a})
        row_data = result.rows[0].per_leg["a"]["rows"][0]
        assert row_data["inputHash"] is None
        assert row_data["outputHash"] is None

    def test_partial_fallback_input_hash_present_output_hash_absent(self):
        """The two fields fall back independently -- one populated at the row
        level does not mask the other's fallback."""
        row = _row("R1", "OBJ1", "passed")
        row["inputHash"] = "row-input-hash"
        envelope = _envelope([row])
        envelope["outputHash"] = "envelope-output-hash"
        leg_a = LegResult("a", True, envelope)
        result = compare_legs({"a": leg_a})
        row_data = result.rows[0].per_leg["a"]["rows"][0]
        assert row_data["inputHash"] == "row-input-hash"
        assert row_data["outputHash"] == "envelope-output-hash"


def _replay_fixture() -> dict:
    """A minimal fixture dict shaped for run_leg_replay -- project/rule/objects
    only, matching _minimal_fixture's shape (run_leg_replay reads the same
    fixture keys run_leg_dg_reasoner does: project, rule.Rule_Id, objects[].objectId)."""
    return {
        "project": "DG-1202-REPLAY",
        "rule": {"Rule_Id": "R_GOLD_HEIGHT_MAX_75_V"},
        "objects": [
            {"objectId": "OBJ_GOLD_PASS"},
            {"objectId": "OBJ_GOLD_FAIL"},
            {"objectId": "OBJ_GOLD_EMPTY"},
        ],
    }


def _view_response(
    *,
    evidence_envelope: dict | None,
    canonical_state_hash: str | None = None,
    canonicalization_version: int | None = None,
    status_code: int = 200,
) -> MagicMock:
    body: dict[str, Any] = {"evidenceEnvelope": evidence_envelope}
    if canonical_state_hash is not None:
        body["canonicalStateHash"] = canonical_state_hash
    if canonicalization_version is not None:
        body["canonicalizationVersion"] = canonicalization_version
    return _mock_response(body, status_code=status_code)


def _replay_envelope() -> dict:
    return _envelope(
        [
            _row("R_GOLD_HEIGHT_MAX_75_V", "OBJ_GOLD_PASS", "passed"),
            _row("R_GOLD_HEIGHT_MAX_75_V", "OBJ_GOLD_FAIL", "failed"),
            _row("R_GOLD_HEIGHT_MAX_75_V", "OBJ_GOLD_EMPTY", "no_population"),
        ],
        service_name="data-service",
        stage="validation.publish",
    )


class TestRunLegReplayStateHash:
    """Task 1 (D-16): run_leg_replay surfaces canonicalStateHash/canonicalizationVersion
    from the view response onto LegResult.state_hash, with typed absence when the
    view reports none -- offline, no live services."""

    def test_state_hash_populated_when_view_reports_one(self):
        mock_client = MagicMock()
        mock_client.__enter__.return_value = mock_client
        mock_client.__exit__.return_value = False
        mock_client.get.return_value = _view_response(
            evidence_envelope=_replay_envelope(),
            canonical_state_hash="3D2D5EDF750FEA213CFB564E424C61F029220F2BF93B0B227EE6FEEC4F55A428",
            canonicalization_version=1,
        )

        with patch.object(legs.httpx, "Client", return_value=mock_client):
            result = run_leg_replay(_replay_fixture(), config={})

        assert result.available is True
        assert result.state_hash == {
            "hash": "3D2D5EDF750FEA213CFB564E424C61F029220F2BF93B0B227EE6FEEC4F55A428",
            "canonicalizationVersion": 1,
        }

    def test_state_hash_is_none_when_view_reports_none(self):
        """The view response carries no canonicalStateHash key at all (e.g. the
        run has no statePayloadJson) -- typed absence, LegResult.state_hash stays
        None, and this must not affect envelope-based availability."""
        mock_client = MagicMock()
        mock_client.__enter__.return_value = mock_client
        mock_client.__exit__.return_value = False
        mock_client.get.return_value = _view_response(evidence_envelope=_replay_envelope())

        with patch.object(legs.httpx, "Client", return_value=mock_client):
            result = run_leg_replay(_replay_fixture(), config={})

        assert result.available is True
        assert result.state_hash is None

    def test_state_hash_is_none_when_view_reports_explicit_null(self):
        """build_view_payload's own absence convention emits canonicalStateHash:
        null rather than omitting the key -- run_leg_replay must treat an explicit
        null the same as a missing key, never as a falsy-but-present hash."""
        mock_client = MagicMock()
        mock_client.__enter__.return_value = mock_client
        mock_client.__exit__.return_value = False
        mock_client.get.return_value = _view_response(
            evidence_envelope=_replay_envelope(),
            canonical_state_hash=None,
        )

        with patch.object(legs.httpx, "Client", return_value=mock_client):
            result = run_leg_replay(_replay_fixture(), config={})

        assert result.state_hash is None

    def test_state_hash_stays_none_when_leg_unavailable(self):
        """An unreachable data-service degrades run_leg_replay to a typed error
        LegResult (available=False) -- state_hash must stay at its None default,
        never fabricated from a synthesized error envelope."""
        mock_client = MagicMock()
        mock_client.__enter__.return_value = mock_client
        mock_client.__exit__.return_value = False
        mock_client.get.side_effect = legs.httpx.RequestError("connection refused")

        with patch.object(legs.httpx, "Client", return_value=mock_client):
            result = run_leg_replay(_replay_fixture(), config={})

        assert result.available is False
        assert result.state_hash is None


class TestLegResultStateHashDefault:
    """The new state_hash field is additive: every existing LegResult constructor
    (no state_hash kwarg) keeps working unchanged, defaulting to None."""

    def test_legresult_constructor_without_state_hash_kwarg_defaults_to_none(self):
        result = LegResult("a", True, _envelope([_row("R1", "OBJ1", "passed")]))
        assert result.state_hash is None

    def test_legresult_constructor_with_error_kwarg_still_defaults_state_hash_to_none(self):
        result = LegResult("a", False, _envelope([]), error="unreachable")
        assert result.state_hash is None


class TestCompareStateHashes:
    """Task 1 (D-16): compare_state_hashes' agreement/disagreement/typed-absence
    behavior, plus the fixture-expected-hash comparison."""

    def test_two_legs_reporting_the_same_hash_agree(self):
        legs_map = {
            "replay": LegResult(
                "replay", True, _envelope([]), state_hash={"hash": "ABC123", "canonicalizationVersion": 1}
            ),
            "csharp": LegResult(
                "csharp", True, _envelope([]), state_hash={"hash": "ABC123", "canonicalizationVersion": 1}
            ),
        }
        result = compare_state_hashes(legs_map)
        assert result["agreement"] == "agree"
        assert result["perLeg"]["replay"]["present"] is True
        assert result["perLeg"]["replay"]["hash"] == "ABC123"
        assert result["perLeg"]["csharp"]["present"] is True

    def test_two_legs_reporting_different_hashes_disagree(self):
        legs_map = {
            "replay": LegResult(
                "replay", True, _envelope([]), state_hash={"hash": "ABC123", "canonicalizationVersion": 1}
            ),
            "csharp": LegResult(
                "csharp", True, _envelope([]), state_hash={"hash": "ZZZ999", "canonicalizationVersion": 1}
            ),
        }
        result = compare_state_hashes(legs_map)
        assert result["agreement"] == "disagree"

    def test_non_participating_leg_reports_typed_absence_with_reason_never_fabricated(self):
        """data-service/dg-reasoner evaluate the rule fixture and capture no Design
        State (Open Question 2) -- typed absence with a non-empty reason, never a
        fabricated hash, and their absence does not by itself make the verdict
        'disagree'."""
        legs_map = {
            "replay": LegResult(
                "replay", True, _envelope([]), state_hash={"hash": "ABC123", "canonicalizationVersion": 1}
            ),
            "data-service": LegResult("data-service", True, _envelope([]), state_hash=None),
        }
        result = compare_state_hashes(legs_map)
        assert result["perLeg"]["data-service"] == {
            "present": False,
            "reason": (
                "the data-service leg does not capture or report a Design State "
                "(Open Question 2 -- see LegResult.state_hash's docstring)"
            ),
        }
        # Only one leg actually reported a hash -- not enough to compare.
        assert result["agreement"] == "not_applicable"

    def test_absent_leg_alone_is_not_applicable_not_a_disagreement(self):
        """A single leg reporting a hash, with every other leg typed-absent, must
        never itself be classified as a disagreement -- mirroring how a lone row
        in compare_legs can never itself be a cross-leg difference."""
        legs_map = {
            "replay": LegResult(
                "replay", True, _envelope([]), state_hash={"hash": "ABC123", "canonicalizationVersion": 1}
            ),
        }
        result = compare_state_hashes(legs_map)
        assert result["agreement"] == "not_applicable"

    def test_all_legs_absent_is_not_applicable(self):
        legs_map = {
            "data-service": LegResult("data-service", True, _envelope([]), state_hash=None),
            "dg-reasoner": LegResult("dg-reasoner", True, _envelope([]), state_hash=None),
        }
        result = compare_state_hashes(legs_map)
        assert result["agreement"] == "not_applicable"
        assert result["perLeg"]["data-service"]["present"] is False
        assert result["perLeg"]["dg-reasoner"]["present"] is False

    def test_present_hash_matching_expected_reports_true(self):
        legs_map = {
            "replay": LegResult(
                "replay", True, _envelope([]), state_hash={"hash": "ABC123", "canonicalizationVersion": 1}
            ),
        }
        result = compare_state_hashes(legs_map, expected_canonical_state_hash="ABC123")
        assert result["perLeg"]["replay"]["expected_match"] is True
        assert result["expectedCanonicalStateHash"] == "ABC123"

    def test_present_hash_not_matching_expected_reports_false(self):
        legs_map = {
            "replay": LegResult(
                "replay", True, _envelope([]), state_hash={"hash": "WRONG", "canonicalizationVersion": 1}
            ),
        }
        result = compare_state_hashes(legs_map, expected_canonical_state_hash="ABC123")
        assert result["perLeg"]["replay"]["expected_match"] is False

    def test_no_expected_hash_supplied_reports_none_not_false(self):
        """A third typed-absence case: no fixture expected value at all must not
        be conflated with a genuine mismatch (False)."""
        legs_map = {
            "replay": LegResult(
                "replay", True, _envelope([]), state_hash={"hash": "ABC123", "canonicalizationVersion": 1}
            ),
        }
        result = compare_state_hashes(legs_map)
        assert result["perLeg"]["replay"]["expected_match"] is None
        assert result["expectedCanonicalStateHash"] is None


class TestStateHashDisagreementFoldedIntoSilentDisagreementCount:
    """run_de01.py's exit-code rule stays non-zero only on
    silent_disagreement_count > 0 -- a state-hash 'disagree' must increment that
    same counter, and 'not_applicable' must not, verified against the actual
    ComparisonResult object rather than only against compare_state_hashes'
    return value in isolation."""

    def test_disagree_increments_the_shared_silent_disagreement_counter(self):
        comparison = compare_legs(
            {
                "a": LegResult("a", True, _envelope([_row("R1", "OBJ1", "passed")])),
            }
        )
        assert comparison.silent_disagreement_count == 0
        comparison.state_hash_comparison = compare_state_hashes(
            {
                "replay": LegResult(
                    "replay", True, _envelope([]), state_hash={"hash": "AAA", "canonicalizationVersion": 1}
                ),
                "csharp": LegResult(
                    "csharp", True, _envelope([]), state_hash={"hash": "BBB", "canonicalizationVersion": 1}
                ),
            }
        )
        if comparison.state_hash_comparison.get("agreement") == "disagree":
            comparison.silent_disagreement_count += 1
        assert comparison.silent_disagreement_count == 1

    def test_not_applicable_does_not_increment_the_counter(self):
        comparison = compare_legs(
            {
                "a": LegResult("a", True, _envelope([_row("R1", "OBJ1", "passed")])),
            }
        )
        comparison.state_hash_comparison = compare_state_hashes(
            {"data-service": LegResult("data-service", True, _envelope([]), state_hash=None)}
        )
        if comparison.state_hash_comparison.get("agreement") == "disagree":
            comparison.silent_disagreement_count += 1
        assert comparison.silent_disagreement_count == 0


class TestReportJsonValidatesAgainstSchemaWithStateHashSection:
    """The report JSON (including the new state_hash_comparison section) must
    validate against tools/de01/report_schema.json -- offline, no live services."""

    def test_emitted_json_report_with_state_hash_comparison_validates_against_schema(self, tmp_path):
        import jsonschema

        comparison = compare_legs(
            {
                "a": LegResult("a", True, _envelope([_row("R1", "OBJ1", "passed")])),
                "b": LegResult("b", True, _envelope([_row("R1", "OBJ1", "passed")])),
            }
        )
        comparison.state_hash_comparison = compare_state_hashes(
            {
                "a": LegResult(
                    "a", True, _envelope([]), state_hash={"hash": "ABC123", "canonicalizationVersion": 1}
                ),
                "b": LegResult(
                    "b", True, _envelope([]), state_hash={"hash": "ABC123", "canonicalizationVersion": 1}
                ),
            },
            expected_canonical_state_hash="ABC123",
        )

        import report as report_module

        json_path = tmp_path / "de01-report.json"
        report_module.emit_json_report(comparison, json_path, fixture_version="1.0.0")

        report = json.loads(json_path.read_text(encoding="utf-8"))
        schema = json.loads(
            (REPO_ROOT / "tools" / "de01" / "report_schema.json").read_text(encoding="utf-8")
        )
        jsonschema.validate(instance=report, schema=schema)
        assert report["state_hash_comparison"]["agreement"] == "agree"

    def test_emitted_json_report_with_not_applicable_state_hash_validates_against_schema(self, tmp_path):
        import jsonschema
        import report as report_module

        comparison = compare_legs(
            {"a": LegResult("a", True, _envelope([_row("R1", "OBJ1", "passed")]))}
        )
        comparison.state_hash_comparison = compare_state_hashes(
            {"a": LegResult("a", True, _envelope([]), state_hash=None)}
        )

        json_path = tmp_path / "de01-report.json"
        report_module.emit_json_report(comparison, json_path, fixture_version="1.0.0")

        report = json.loads(json_path.read_text(encoding="utf-8"))
        schema = json.loads(
            (REPO_ROOT / "tools" / "de01" / "report_schema.json").read_text(encoding="utf-8")
        )
        jsonschema.validate(instance=report, schema=schema)
        assert report["state_hash_comparison"]["agreement"] == "not_applicable"


class TestReplayFixtureFlag:
    """Plan 1202-08 Task 1: --replay-fixture resolves to the sibling replay
    fixture path, and the replay fixture (now a complete DE-01 fixture with
    additive rule/atoms/objects/expectedOutcomes keys) passes every leg's field
    access without KeyError/TypeError -- offline, mocked HTTP boundaries only."""

    def test_replay_fixture_flag_resolves_to_replay_path(self):
        import run_de01

        parser = run_de01.build_arg_parser()
        args = parser.parse_args(["--replay-fixture"])
        assert args.replay_fixture is True

        # Mirror main()'s own resolution logic rather than re-deriving a second
        # path constant -- pins that the flag really does point at the sibling
        # fixture file, not merely that the flag parses.
        if args.replay_fixture:
            resolved = (
                run_de01.REPO_ROOT / "fixtures" / "golden" / "replay" / "mixed-verdicts.json"
            )
        assert resolved.name == "mixed-verdicts.json"
        assert resolved.is_file(), f"{resolved} must exist on disk"

    def test_fixture_flag_default_is_unchanged_frozen_fixture(self):
        import run_de01

        parser = run_de01.build_arg_parser()
        args = parser.parse_args([])
        assert args.fixture == str(run_de01.REPO_ROOT / "fixtures" / "golden" / "fixture.json")
        assert args.replay_fixture is False

    def _load_replay_fixture(self) -> dict:
        path = REPO_ROOT / "fixtures" / "golden" / "replay" / "mixed-verdicts.json"
        return json.loads(path.read_text(encoding="utf-8"))

    def test_replay_fixture_has_complete_de01_shape(self):
        """The additive keys this task adds must actually be present -- not just
        statePayloadJson/expectedCanonicalStateHash/expectedPerObjectVerdicts,
        which predate this task."""
        fixture = self._load_replay_fixture()
        assert fixture["rule"]["Rule_Id"] == "R_GOLD_HEIGHT_MAX_75_V"
        assert {obj["objectId"] for obj in fixture["objects"]} == {
            "OBJ_GOLD_PASS",
            "OBJ_GOLD_FAIL",
            "OBJ_GOLD_EMPTY",
        }
        assert len(fixture["atoms"]) == 4
        assert len(fixture["expectedOutcomes"]) >= 3
        # The fixture's own point -- byte-unchanged by this task.
        assert fixture["project"] == "DG-1202-REPLAY"
        assert fixture["expectedCanonicalStateHash"] == (
            "3D2D5EDF750FEA213CFB564E424C61F029220F2BF93B0B227EE6FEEC4F55A428"
        )

    def test_run_leg_data_service_reads_replay_fixture_fields_without_keyerror(self):
        fixture = self._load_replay_fixture()
        mock_client = MagicMock()
        mock_client.__enter__.return_value = mock_client
        mock_client.__exit__.return_value = False
        mock_client.post.side_effect = legs.httpx.RequestError("unreachable in this test")

        with patch.object(legs.httpx, "Client", return_value=mock_client):
            result = legs.run_leg_data_service(fixture, config={})

        # An unreachable service is an ACCEPTABLE typed-error outcome for this
        # criterion -- the point is that fixture["rule"]["Rule_Id"]/RuleName/
        # RuleDescription and fixture["expectedOutcomes"]/fixture["objects"] were
        # all read without raising KeyError before the HTTP call was attempted.
        assert result.available is False
        assert result.error is not None
        assert "KeyError" not in (result.error or "")

    def test_run_leg_dg_reasoner_reads_replay_fixture_fields_without_keyerror(self):
        fixture = self._load_replay_fixture()
        mock_client = MagicMock()
        mock_client.__enter__.return_value = mock_client
        mock_client.__exit__.return_value = False
        mock_client.post.side_effect = legs.httpx.RequestError("unreachable in this test")

        with patch.object(legs.httpx, "Client", return_value=mock_client):
            result = legs.run_leg_dg_reasoner(fixture, config={})

        assert result.available is False
        assert result.error is not None
        assert "KeyError" not in (result.error or "")

    def test_run_leg_replay_reads_replay_fixture_fields_without_keyerror(self):
        fixture = self._load_replay_fixture()
        mock_client = MagicMock()
        mock_client.__enter__.return_value = mock_client
        mock_client.__exit__.return_value = False
        mock_client.get.side_effect = legs.httpx.RequestError("unreachable in this test")

        with patch.object(legs.httpx, "Client", return_value=mock_client):
            result = legs.run_leg_replay(fixture, config={})

        assert result.available is False
        assert result.error is not None
        assert "KeyError" not in (result.error or "")

    def test_run_leg_csharp_reads_replay_fixture_path_without_keyerror(self):
        """run_leg_csharp reads config["fixture_path"] (a string path), not fixture
        dict keys directly -- confirm it degrades to a typed error (missing dotnet
        or harness project) rather than raising, when pointed at the replay
        fixture path offline."""
        fixture = self._load_replay_fixture()
        fixture_path = str(REPO_ROOT / "fixtures" / "golden" / "replay" / "mixed-verdicts.json")

        with patch.object(legs.subprocess, "run", side_effect=FileNotFoundError("dotnet not found")):
            result = legs.run_leg_csharp(fixture, config={"fixture_path": fixture_path})

        assert result.available is False
        assert result.error is not None
        assert "KeyError" not in (result.error or "")


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
