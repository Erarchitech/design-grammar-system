"""D-14 LLM-sample outcome taxonomy for the 1204 determinism/reproducibility
benchmark (harness-side only, D-23).

This module is the FIRST single home for the D-14 proposal-outcome taxonomy.
Today that classification is split across two producers:

- recognition: `data-service/cg_recognition.py`'s guard stack around
  `validate_proposed_structure()` (:130) -- `bad_json` (:1143),
  `schema_violation` (:812), the relational codes (:152-410), G7
  `grammar_as_filter` (:1167/:1186), G8 `output_truncated` (:1094);
- rule-ingest: `data-service/dg_context.py`'s `validate_cypher()` (:674),
  called inside the retry loop at :989 -- the ten violation codes at
  :698-904.

Two vocabularies that must never merge:

- `OUTCOME_LABELS` -- THIS module's seven proposal outcomes (D-14).
- `VERDICT_STATUSES` -- the eight canonical verdict statuses frozen by phase
  1200 (`spec/EVIDENCE-CONTRACT.md:51-52`), used here ONLY by the disjointness
  test so the two can never intersect.

`classify()` is oracle-free (D-18): it takes the attempt record(s) and the
sample's subject, never an expected label, and performs no accuracy or
label-equality comparison. It is a provenance/taxonomy step, never an
evaluator against ground truth.

Test-only, deliberately: this package lives under `data-service/tests/` so
nothing in production code can import it.
"""

from __future__ import annotations

from dataclasses import dataclass

# ── D-14: the closed proposal-outcome vocabulary ──

# The exact seven D-14 outcomes. This is a CLOSED set: a new outcome label is
# a phase-level decision, not a local edit.
OUTCOME_LABELS = frozenset(
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

# The eight canonical verdict statuses frozen by phase 1200
# (`spec/EVIDENCE-CONTRACT.md:51-52`, `$defs.CanonicalStatus.enum`). Carried
# here ONLY so the disjointness test can prove OUTCOME_LABELS never reuses
# verdict vocabulary -- this module must never emit one of these names as an
# outcome label.
VERDICT_STATUSES = frozenset(
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

# ── D-14 `invalid` sub-typing: per-subject violation codes ──

# Rule-ingest: exactly the ten `validate_cypher` codes emitted by
# `data-service/dg_context.py:698-904` (function at :674). Kept as the
# canonical name; `VIOLATION_CODES` is the documented alias below.
RULE_INGEST_VIOLATION_CODES = frozenset(
    {
        "empty_output",  # :698
        "no_cypher_statement",  # :711, :725
        "unbalanced_brackets",  # :738
        "malformed_node_pattern",  # :751
        "unknown_label",  # :768
        "unknown_relationship",  # :782
        "bad_kind_enum",  # :800, :814
        "bad_key_name",  # :829, :842, :871
        "missing_project_key",  # :854
        "disallowed_verb",  # :887, :904
    }
)

# Documented alias (the 1204 artifacts table names this constant both ways).
VIOLATION_CODES = RULE_INGEST_VIOLATION_CODES

# Recognition: the codes enumerated from `data-service/cg_recognition.py`,
# grouped by the guard that emits them --
#   parse/schema: bad_json (:1143), schema_violation (:812);
#   the relational codes of validate_proposed_structure() (:130): bad_shape,
#     missing_field, invalid_kind, unknown_member_id, tagged_overlap,
#     duplicate_member, too_many_proposals, too_many_members,
#     too_many_unrecognized;
#   scope: empty_procedure_scope (:1021);
#   G6/G7/G8: unaddressed_candidate (:1217), grammar_as_filter (:1167/:1186),
#     output_truncated (:1094);
#   refusal: provider_refusal (:1121).
RECOGNITION_VIOLATION_CODES = frozenset(
    {
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
)

# D-16: rule-ingest's output contract has NO abstention channel. It is
# reported as this fixed sentinel -- never as `0%`. This is a report value,
# NOT a taxonomy label (asserted in test_outcome_taxonomy.py).
ABSTENTION_UNSUPPORTED = "not supported by output contract"


# ── D-15/D-18: the classifier ──


@dataclass(frozen=True)
class Classification:
    """One sample's classified outcome.

    Fields:
        first_attempt_outcome: the outcome label of `attempts[0]` -- D-15's
            first-level measurement, the one the retry loop hides.
        final_outcome: the outcome label of `attempts[-1]`, upgraded to
            `valid_after_retry` when a retry turned a non-valid first attempt
            into a valid final one (D-15).
        attempts: the attempt count actually observed (D-15's attempts
            distribution input; both paths run `max_retries=2`, so this is
            1-3).
        violation_code: the final attempt's `violation_code` when the final
            outcome is `invalid`, else None.
    """

    first_attempt_outcome: str
    final_outcome: str
    attempts: int
    violation_code: str | None = None


def _subject_violation_codes(subject: str) -> frozenset:
    """The `invalid` violation-code set for one subject (D-14).

    `rule-ingest` -> RULE_INGEST_VIOLATION_CODES; `recognition` ->
    RECOGNITION_VIOLATION_CODES. Anything else is a caller error.
    """
    if subject == "rule-ingest":
        return RULE_INGEST_VIOLATION_CODES
    if subject == "recognition":
        return RECOGNITION_VIOLATION_CODES
    raise ValueError(
        f"unknown subject {subject!r} -- expected 'rule-ingest' or "
        "'recognition'; the invalid outcome's violation_code must be drawn "
        "from that subject's own code set (D-14)."
    )


def _classify_attempt(attempt: dict) -> str:
    """Map ONE attempt record to an outcome label via a FIXED precedence.

    Precedence (first match wins -- do not reorder):
        provider_error -> "provider_error"
        truncated      -> "truncated"
        finish_reason == "refusal" -> "refused"
        abstained      -> "abstained"
        else "valid" when valid is True, else "invalid"

    The `truncated`/`finish_reason` inputs are the ones the gateway already
    reports (`data-service/llm_gateway.py:55-63`) -- they are read, never
    re-derived from text heuristics. `provider_error` is the signal
    `map_provider_error()` (`llm_gateway.py:852`) surfaces.

    Abstention is strictly flag-driven (D-16): `abstained=True` is the ONLY
    path to "abstained". A G6-autofilled record (`abstained=False`,
    `valid=True`) therefore classifies as "valid", never "abstained".
    """
    if attempt.get("provider_error"):
        return "provider_error"
    if attempt.get("truncated"):
        return "truncated"
    if attempt.get("finish_reason") == "refusal":
        return "refused"
    if attempt.get("abstained"):
        return "abstained"
    return "valid" if attempt.get("valid") is True else "invalid"


def classify(attempts: list[dict], subject: str) -> Classification:
    """Classify one sample from its attempt record(s) -- oracle-free (D-18).

    Takes ONLY the attempt records and the sample's subject (which selects
    RULE_INGEST_VIOLATION_CODES or RECOGNITION_VIOLATION_CODES). There is no
    expected-label parameter and no accuracy/label comparison anywhere in this
    module: correctness enters the 1204 report only through deterministic
    validity oracles (D-14, D-15).

    Records both levels D-15 requires -- the first attempt's outcome and the
    final attempt's outcome, plus the attempts count -- so the sampling sweep
    can report the first-attempt invalid rate, the final invalid rate and the
    attempts distribution instead of the single number the retry loop hides.

    An `invalid` final outcome carries its `violation_code`, validated against
    the code set for `subject`. A code outside that set is a harness bug, not
    a classification, and raises ValueError.

    Task 2 widens the final outcome to `valid_after_retry` when a retry turned
    a non-valid first attempt into a valid final one.
    """
    if not attempts:
        raise ValueError(
            "classify() needs at least one attempt record -- an empty attempt "
            "list has no first-attempt outcome to report (D-15)."
        )

    violation_codes = _subject_violation_codes(subject)

    first_attempt_outcome = _classify_attempt(attempts[0])
    final_attempt_outcome = _classify_attempt(attempts[-1])

    violation_code: str | None = None
    if final_attempt_outcome == "invalid":
        violation_code = attempts[-1].get("violation_code")
        if violation_code is not None and violation_code not in violation_codes:
            raise ValueError(
                f"violation_code {violation_code!r} is not one of the "
                f"{subject} violation codes -- an invalid outcome's code must "
                "be drawn from that subject's own set (D-14)."
            )

    # D-15: a retry that turned a non-valid first attempt into a valid final
    # attempt is its own outcome -- the first-attempt invalid rate the retry
    # loop hides must still be reportable separately.
    if (
        len(attempts) > 1
        and final_attempt_outcome == "valid"
        and first_attempt_outcome != "valid"
    ):
        final_attempt_outcome = "valid_after_retry"

    return Classification(
        first_attempt_outcome=first_attempt_outcome,
        final_outcome=final_attempt_outcome,
        attempts=len(attempts),
        violation_code=violation_code,
    )