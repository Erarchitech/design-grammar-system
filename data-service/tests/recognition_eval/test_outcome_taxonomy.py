"""D-14/D-15/D-16/D-18 outcome-taxonomy tests for the 1204 benchmark.

Harness-side only (D-23): this file asserts the taxonomy module's closed
label set, its per-subject violation codes, D-15's first-attempt-vs-final
measurement, D-16's explicit-channel-only abstention, and D-18's oracle-free
signature. No production module is imported beyond the taxonomy under test.
"""

from __future__ import annotations

import inspect
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, os.path.dirname(__file__))

os.environ.setdefault("LLM_MASTER_SECRET", "test-master-secret")

import pytest  # noqa: E402

import outcome_taxonomy  # noqa: E402
from outcome_taxonomy import (  # noqa: E402
    ABSTENTION_UNSUPPORTED,
    OUTCOME_LABELS,
    RECOGNITION_VIOLATION_CODES,
    RULE_INGEST_VIOLATION_CODES,
    VERDICT_STATUSES,
    VIOLATION_CODES,
    Classification,
    classify,
)

# `data-service/dg_context.py:698-904` -- the ten validate_cypher codes.
_EXPECTED_RULE_INGEST_CODES = {
    "empty_output",
    "no_cypher_statement",
    "unbalanced_brackets",
    "malformed_node_pattern",
    "unknown_label",
    "unknown_relationship",
    "bad_kind_enum",
    "bad_key_name",
    "missing_project_key",
    "disallowed_verb",
}

# `data-service/cg_recognition.py` -- bad_json (:1143), schema_violation
# (:812), the relational codes of validate_proposed_structure (:130),
# empty_procedure_scope (:1021), the G6/G7/G8 codes and provider_refusal
# (:1121).
_EXPECTED_RECOGNITION_CODES = {
    "bad_json",
    "schema_violation",
    "bad_shape",
    "missing_field",
    "invalid_kind",
    "unknown_member_id",
    "tagged_overlap",
    "duplicate_member",
    "too_many_proposals",
    "too_many_members",
    "too_many_unrecognized",
    "empty_procedure_scope",
    "unaddressed_candidate",
    "grammar_as_filter",
    "output_truncated",
    "provider_refusal",
}


def _attempt(**overrides) -> dict:
    """A synthetic, minimal attempt record -- fields the gateway/paths report."""
    base = {
        "truncated": False,
        "finish_reason": "stop",
        "abstained": False,
        "valid": True,
        "violation_code": None,
        "provider_error": False,
    }
    base.update(overrides)
    return base


class TestLabelReachability:
    """Every OUTCOME_LABELS member is reachable from a synthetic attempt."""

    @pytest.mark.parametrize(
        "attempt, expected",
        [
            (_attempt(valid=True), "valid"),
            (_attempt(valid=False, violation_code="bad_json"), "invalid"),
            (_attempt(abstained=True), "abstained"),
            (_attempt(truncated=True), "truncated"),
            (_attempt(finish_reason="refusal"), "refused"),
            (_attempt(provider_error=True), "provider_error"),
        ],
    )
    def test_attempt_record_classifies_to_its_label(self, attempt, expected):
        assert classify([attempt], "recognition").final_outcome == expected

    def test_valid_after_retry_label_is_member_and_reachable(self):
        # The seventh label needs two attempts (D-15), in its own test below.
        assert "valid_after_retry" in OUTCOME_LABELS
        result = classify(
            [_attempt(valid=False, violation_code="bad_json"), _attempt(valid=True)],
            "recognition",
        )
        assert result.final_outcome == "valid_after_retry"

    def test_every_outcome_label_is_reachable(self):
        reached = {
            "valid",
            "invalid",
            "abstained",
            "truncated",
            "refused",
            "provider_error",
        }
        reached |= {"valid_after_retry"}
        assert reached == set(OUTCOME_LABELS)


class TestConstants:
    def test_outcome_labels_is_the_exact_seven_label_set(self):
        assert OUTCOME_LABELS == frozenset(
            {
                "valid",
                "valid_after_retry",
                "invalid",
                "abstained",
                "truncated",
                "refused",
                "provider_error",
            }
        )

    def test_verdict_statuses_is_the_exact_eight_status_set(self):
        assert VERDICT_STATUSES == frozenset(
            {
                "passed",
                "failed",
                "unknown",
                "not_evaluated",
                "no_population",
                "unsupported",
                "indeterminate",
                "error",
            }
        )

    def test_rule_ingest_violation_codes_is_the_exact_ten_code_set(self):
        assert RULE_INGEST_VIOLATION_CODES == frozenset(_EXPECTED_RULE_INGEST_CODES)

    def test_violation_codes_aliases_rule_ingest_violation_codes(self):
        assert VIOLATION_CODES == RULE_INGEST_VIOLATION_CODES
        assert VIOLATION_CODES is RULE_INGEST_VIOLATION_CODES

    def test_recognition_violation_codes_is_the_exact_enumerated_set(self):
        assert RECOGNITION_VIOLATION_CODES == frozenset(_EXPECTED_RECOGNITION_CODES)


class TestOracleFreeSignature:
    def test_classify_signature_has_no_expected_label_or_accuracy_parameter(self):
        params = set(inspect.signature(classify).parameters)
        assert "expected" not in params
        assert "label" not in params
        assert "accuracy" not in params
        assert params == {"attempts", "subject"}

    def test_classify_returns_classification_with_two_level_measurement(self):
        result = classify([_attempt(valid=True)], "recognition")
        assert isinstance(result, Classification)
        assert result.first_attempt_outcome == "valid"
        assert result.final_outcome == "valid"
        assert result.attempts == 1
        assert result.violation_code is None


class TestViolationCodeBySubject:
    def test_rule_ingest_invalid_carries_its_own_code(self):
        result = classify(
            [_attempt(valid=False, violation_code="disallowed_verb")], "rule-ingest"
        )
        assert result.final_outcome == "invalid"
        assert result.violation_code == "disallowed_verb"

    def test_recognition_invalid_carries_its_own_code(self):
        result = classify(
            [_attempt(valid=False, violation_code="schema_violation")],
            "recognition",
        )
        assert result.final_outcome == "invalid"
        assert result.violation_code == "schema_violation"

    def test_recognition_code_rejected_for_rule_ingest_subject(self):
        with pytest.raises(ValueError):
            classify(
                [_attempt(valid=False, violation_code="bad_json")], "rule-ingest"
            )

    def test_rule_ingest_code_rejected_for_recognition_subject(self):
        with pytest.raises(ValueError):
            classify(
                [_attempt(valid=False, violation_code="disallowed_verb")],
                "recognition",
            )

    def test_unknown_subject_rejected(self):
        with pytest.raises(ValueError):
            classify([_attempt(valid=True)], "not-a-subject")

    def test_empty_attempts_rejected(self):
        with pytest.raises(ValueError):
            classify([], "recognition")


class TestPrecedence:
    def test_provider_error_outranks_every_other_signal(self):
        assert (
            classify([_attempt(provider_error=True, truncated=True)], "recognition")
            .final_outcome
            == "provider_error"
        )

    def test_truncated_outranks_refusal_and_abstention(self):
        assert (
            classify(
                [_attempt(truncated=True, finish_reason="refusal", abstained=True)],
                "recognition",
            ).final_outcome
            == "truncated"
        )

    def test_refusal_outranks_abstention(self):
        assert (
            classify(
                [_attempt(finish_reason="refusal", abstained=True)], "recognition"
            ).final_outcome
            == "refused"
        )


class TestD15FirstAttemptVsFinal:
    def test_valid_after_retry_when_first_invalid_final_valid(self):
        result = classify(
            [_attempt(valid=False, violation_code="bad_json"), _attempt(valid=True)],
            "recognition",
        )
        assert result.final_outcome == "valid_after_retry"
        assert result.first_attempt_outcome == "invalid"
        assert result.attempts == 2

    def test_no_valid_after_retry_without_retry(self):
        result = classify([_attempt(valid=True)], "recognition")
        assert result.final_outcome == "valid"
        assert result.first_attempt_outcome == "valid"
        assert result.attempts == 1

    def test_records_first_attempt_and_attempts_for_a_still_invalid_final(self):
        result = classify(
            [
                _attempt(valid=False, violation_code="schema_violation"),
                _attempt(valid=False, violation_code="bad_json"),
                _attempt(valid=False, violation_code="schema_violation"),
            ],
            "recognition",
        )
        assert result.first_attempt_outcome == "invalid"
        assert result.final_outcome == "invalid"
        assert result.attempts == 3
        assert result.violation_code == "schema_violation"

    def test_no_valid_after_retry_when_first_attempt_already_valid(self):
        result = classify([_attempt(valid=True), _attempt(valid=True)], "recognition")
        assert result.final_outcome == "valid"


class TestD16AbstentionChannels:
    def test_g6_autofill_is_not_abstention(self):
        # G6-autofilled shape: abstained=False, valid=True with the autofill
        # flag -- a model gap, NOT model abstention (D-16).
        result = classify(
            [
                _attempt(
                    abstained=False,
                    valid=True,
                    flags=["unaddressed_candidates_autofilled"],
                )
            ],
            "recognition",
        )
        assert result.final_outcome == "valid"
        assert result.final_outcome != "abstained"

    def test_explicit_abstain_flag_is_the_only_abstention_channel(self):
        assert (
            classify([_attempt(abstained=True, valid=False)], "recognition")
            .final_outcome
            == "abstained"
        )

    def test_rule_ingest_abstention_is_not_supported_by_output_contract(self):
        assert ABSTENTION_UNSUPPORTED == "not supported by output contract"
        assert ABSTENTION_UNSUPPORTED not in OUTCOME_LABELS


class TestDisjointness:
    def test_outcome_labels_disjoint_from_verdict_statuses(self):
        assert OUTCOME_LABELS.isdisjoint(VERDICT_STATUSES) is True

    def test_rule_ingest_and_recognition_code_sets_are_disjoint_enough_to_be_own_sets(
        self,
    ):
        # Sanity: both sets are non-empty and each is a subset of nothing else
        # in this module's vocabulary (the codes are never outcome labels).
        assert RULE_INGEST_VIOLATION_CODES
        assert RECOGNITION_VIOLATION_CODES
        assert OUTCOME_LABELS.isdisjoint(RULE_INGEST_VIOLATION_CODES)
        assert OUTCOME_LABELS.isdisjoint(RECOGNITION_VIOLATION_CODES)

    def test_module_exposes_no_oracle_comparison(self):
        # D-18: no oracle parameter, and no label-equality comparison in the
        # executable code of classify / its helper -- the probe is on
        # behaviour, not on docstring prose.
        assert set(inspect.signature(classify).parameters) == {"attempts", "subject"}
        assert set(inspect.signature(outcome_taxonomy._classify_attempt).parameters) == {
            "attempt"
        }
        # A field naming a ground-truth label is simply ignored, never compared.
        result = classify(
            [_attempt(valid=True, expected="invalid", label="invalid")],
            "recognition",
        )
        assert result.final_outcome == "valid"