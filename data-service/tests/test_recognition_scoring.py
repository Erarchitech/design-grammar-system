"""Tests for the recognition eval scoring core and corpus loader (Phase 35-11).

Covers `recognition_eval/scoring.py`'s block matcher and every SC1 metric
function, plus `recognition_eval/corpus.py`'s loading, provenance and
freeze-protocol checks. Follows the existing test pattern from
test_cg_recognition.py: sys.path.insert boilerplate header, class-per-concern
shape, hand-built fixture dicts.
"""

from __future__ import annotations

import hashlib
import json
import logging
import os
import sys
from pathlib import Path

sys.path.insert(0, os.path.dirname(__file__))

import pytest  # noqa: E402

from recognition_eval import corpus, scoring  # noqa: E402


# ── Brute-force oracle for the greedy-vs-optimal comparison ──
#
# Exhaustive over all partial injective assignments proposal_index ->
# reference_block_id, maximising total Jaccard. Only tractable at the small
# sizes used here (<= 5 blocks per side), which is exactly what it is for.


def _jaccard(a, b) -> float:
    set_a, set_b = set(a), set(b)
    union = set_a | set_b
    return len(set_a & set_b) / len(union) if union else 0.0


def _brute_force_optimal_total_jaccard(proposals: list[dict], reference_blocks: list[dict]) -> float:
    pair_j: dict[tuple[int, str], float] = {}
    for p_idx, proposal in enumerate(proposals):
        for ref in reference_blocks:
            j = _jaccard(proposal.get("memberIds", []), ref["memberIds"])
            if j > 0.0:
                pair_j[(p_idx, ref["id"])] = j

    ref_ids = [ref["id"] for ref in reference_blocks]

    def best(proposal_indices: tuple[int, ...], available_refs: tuple[str, ...]) -> float:
        if not proposal_indices:
            return 0.0
        p, rest = proposal_indices[0], proposal_indices[1:]
        # Leave p unmatched.
        best_total = best(rest, available_refs)
        for r in available_refs:
            j = pair_j.get((p, r), 0.0)
            if j <= 0.0:
                continue
            remaining = tuple(x for x in available_refs if x != r)
            candidate = j + best(rest, remaining)
            if candidate > best_total:
                best_total = candidate
        return best_total

    return best(tuple(range(len(proposals))), tuple(ref_ids))


# Three small, deliberately unambiguous synthetic cases (<= 5 blocks each) --
# each has a single clear optimum, matching the plan's claim that greedy and
# optimal coincide when most true matches sit at J == 1.0.

_CASE_TRIVIAL_1TO1 = (
    [{"memberIds": ["a", "b"]}, {"memberIds": ["c"]}],
    [{"id": "r1", "memberIds": ["a", "b"]}, {"id": "r2", "memberIds": ["c"]}],
)

_CASE_PARTIAL_OVERLAP = (
    [{"memberIds": ["a", "b", "c"]}, {"memberIds": ["a"]}],
    [{"id": "r1", "memberIds": ["a", "b"]}, {"id": "r2", "memberIds": ["a", "b", "c"]}],
)

_CASE_THREE_WAY = (
    [{"memberIds": ["a"]}, {"memberIds": ["b"]}, {"memberIds": ["a", "b"]}],
    [
        {"id": "r1", "memberIds": ["a"]},
        {"id": "r2", "memberIds": ["b"]},
        {"id": "r3", "memberIds": ["a", "b"]},
    ],
)


class TestMatchBlocks:
    def test_identical_sets_are_all_exact_with_zero_misses_and_spurious(self):
        refs = [
            {"id": "r1", "kind": "Pattern", "memberIds": ["a", "b"]},
            {"id": "r2", "kind": "Interface", "memberIds": ["c"]},
        ]
        proposals = [{"memberIds": ["a", "b"]}, {"memberIds": ["c"]}]

        result = scoring.match_blocks(proposals, refs)

        assert len(result.pairs) == 2
        assert all(pair.jaccard == 1.0 for pair in result.pairs)
        assert result.misses == []
        assert result.spurious == []

    def test_deterministic_across_repeated_calls(self):
        refs = [
            {"id": "r1", "memberIds": ["a", "b", "c"]},
            {"id": "r2", "memberIds": ["d"]},
        ]
        proposals = [
            {"memberIds": ["a", "b"]},
            {"memberIds": ["d"]},
            {"memberIds": ["a", "b", "c", "e"]},
        ]

        def serialize(result: scoring.MatchResult):
            return [(p.reference_block_id, p.proposal_index, p.jaccard) for p in result.pairs]

        first = scoring.match_blocks(proposals, refs)
        second = scoring.match_blocks(proposals, refs)
        assert serialize(first) == serialize(second)

    def test_tie_on_same_reference_block_logs_a_warning(self, caplog):
        refs = [{"id": "r1", "memberIds": ["a", "b"]}]
        # Both proposals overlap r1 at the same J (2/3) -- greedy's choice
        # between them is arbitrary beyond proposal_index order.
        proposals = [{"memberIds": ["a", "b", "c"]}, {"memberIds": ["a", "b", "d"]}]

        with caplog.at_level(logging.WARNING, logger="recognition_eval.scoring"):
            scoring.match_blocks(proposals, refs)

        assert any("r1" in record.getMessage() for record in caplog.records)

    @pytest.mark.parametrize(
        "proposals,refs",
        [_CASE_TRIVIAL_1TO1, _CASE_PARTIAL_OVERLAP, _CASE_THREE_WAY],
        ids=["trivial-1to1", "partial-overlap", "three-way"],
    )
    def test_greedy_equals_brute_force_optimal_total_jaccard(self, proposals, refs):
        result = scoring.match_blocks(proposals, refs)
        greedy_total = sum(pair.jaccard for pair in result.pairs)
        optimal_total = _brute_force_optimal_total_jaccard(proposals, refs)
        assert greedy_total == pytest.approx(optimal_total)


class TestM1M2Mean:
    def test_m1_exact_rate_three_of_five(self):
        refs = [{"id": f"r{i}", "memberIds": [f"n{i}"]} for i in range(1, 6)]
        # Exact matches for r1-r3; r4/r5 have no proposal at all (misses).
        proposals = [{"memberIds": ["n1"]}, {"memberIds": ["n2"]}, {"memberIds": ["n3"]}]

        result = scoring.match_blocks(proposals, refs)

        assert scoring.m1_exact_rate(result) == pytest.approx(0.6)

    def test_m2_near_rate_counts_j_at_least_half(self):
        refs = [{"id": "r1", "memberIds": ["a", "b"]}, {"id": "r2", "memberIds": ["c", "d"]}]
        # r1: exact (J=1.0). r2: near but not exact (J=0.5 -- one extra id).
        proposals = [{"memberIds": ["a", "b"]}, {"memberIds": ["c", "d", "e"]}]

        result = scoring.match_blocks(proposals, refs)

        assert scoring.m2_near_rate(result) == pytest.approx(1.0)
        assert scoring.m1_exact_rate(result) == pytest.approx(0.5)

    def test_mean_jaccard_over_matched_pairs_only(self):
        refs = [{"id": "r1", "memberIds": ["a"]}, {"id": "r2", "memberIds": ["b"]}]
        proposals = [{"memberIds": ["a"]}]  # r2 is a miss, excluded from the mean.

        result = scoring.match_blocks(proposals, refs)

        assert scoring.mean_jaccard(result) == pytest.approx(1.0)


class TestMemberEditDistance:
    def test_counts_symmetric_difference_plus_unmatched_members(self):
        refs = [{"id": "r1", "memberIds": ["a", "b"]}, {"id": "r2", "memberIds": ["c"]}]
        # r1 matched with one extra + one missing member (symmetric diff = 2).
        # r2 is a miss (contributes its 1 member). One spurious proposal
        # (contributes its 1 member).
        proposals = [{"memberIds": ["a", "z"]}, {"memberIds": ["y"]}]

        result = scoring.match_blocks(proposals, refs)

        assert scoring.member_edit_distance(result) == 2 + 1 + 1


class TestM5Segmentation:
    def test_one_to_one_correct_match_has_fragmentation_and_fusion_of_one(self):
        refs = [{"id": "r1", "memberIds": ["a"]}, {"id": "r2", "memberIds": ["b"]}]
        proposals = [{"memberIds": ["a"]}, {"memberIds": ["b"]}]

        result = scoring.match_blocks(proposals, refs)
        m5 = scoring.m5_segmentation(result)

        assert m5["ratio"] == pytest.approx(1.0)
        assert m5["fragmentation"] == pytest.approx(1.0)
        assert m5["fusion"] == pytest.approx(1.0)

    def test_over_segmentation_raises_fragmentation(self):
        # One true block split into two proposals -- both overlap r1.
        refs = [{"id": "r1", "memberIds": ["a", "b"]}]
        proposals = [{"memberIds": ["a"]}, {"memberIds": ["b"]}]

        result = scoring.match_blocks(proposals, refs)
        m5 = scoring.m5_segmentation(result)

        assert m5["ratio"] == pytest.approx(2.0)
        assert m5["fragmentation"] == pytest.approx(2.0)

    def test_fusion_catches_a_catch_all_proposal(self):
        # One proposal merges two true blocks into one catch-all.
        refs = [{"id": "r1", "memberIds": ["a"]}, {"id": "r2", "memberIds": ["b"]}]
        proposals = [{"memberIds": ["a", "b"]}]

        result = scoring.match_blocks(proposals, refs)
        m5 = scoring.m5_segmentation(result)

        assert m5["fusion"] == pytest.approx(2.0)


class TestNestingAgreement:
    def test_agrees_when_no_pattern_pairs_present(self):
        refs = [{"id": "r1", "kind": "Interface", "memberIds": ["a"]}]
        proposals = [{"memberIds": ["a"]}]
        result = scoring.match_blocks(proposals, refs)

        assert scoring.nesting_agreement(result) == pytest.approx(1.0)

    def test_detects_disagreement_on_host_pattern(self):
        # r1 is a non-Pattern host so it is excluded from the denominator --
        # isolates the assertion to the single Pattern pair (r2) under test.
        refs = [
            {"id": "r1", "kind": "Interface", "memberIds": ["a"], "hostBlockId": None},
            {"id": "r2", "kind": "Pattern", "memberIds": ["b"], "hostBlockId": "r1"},
        ]
        proposals = [{"memberIds": ["a"]}, {"memberIds": ["b"]}]
        result = scoring.match_blocks(proposals, refs)

        # Correct: proposal 1 (matched to r2) nests inside proposal 0 (matched to r1).
        assert scoring.nesting_agreement(result, {1: 0}) == pytest.approx(1.0)
        # Wrong: proposal 1 claimed as top-level when the reference expects nesting.
        assert scoring.nesting_agreement(result, {1: None}) == pytest.approx(0.0)


class TestSilentDropCount:
    def test_nonzero_when_a_candidate_is_addressed_by_neither_list(self):
        count = scoring.silent_drop_count(
            ["a", "b", "c"],
            proposals=[{"memberIds": ["a"]}],
            unrecognized=[{"memberIds": ["b"]}],
        )
        assert count == 1

    def test_zero_when_every_candidate_is_addressed(self):
        count = scoring.silent_drop_count(
            ["a", "b", "c"],
            proposals=[{"memberIds": ["a"]}],
            unrecognized=[{"memberIds": ["b", "c"]}],
        )
        assert count == 0


class TestAbstention:
    def test_recall_and_precision_on_a_partial_match(self):
        abstain_expected = [{"memberIds": ["x"]}, {"memberIds": ["y"]}]
        unrecognized = [{"memberIds": ["x"]}, {"memberIds": ["z"]}]

        assert scoring.abstention_recall(abstain_expected, unrecognized) == pytest.approx(0.5)
        assert scoring.abstention_precision(abstain_expected, unrecognized) == pytest.approx(0.5)

    def test_recall_vacuously_true_when_nothing_expected(self):
        assert scoring.abstention_recall([], [{"memberIds": ["z"]}]) == pytest.approx(1.0)

    def test_precision_vacuously_true_when_nothing_abstained(self):
        assert scoring.abstention_precision([{"memberIds": ["x"]}], []) == pytest.approx(1.0)


class TestGrammarCitationRate:
    def test_returns_one_for_pre_35_08_style_grammar_citing_rationales(self):
        # Historical (pre-35-08 fix) shape of UAT F3: the model cites the
        # naming grammar/convention as its REASON instead of graph evidence.
        rationales = [
            "Named '11_IntF_ParSplitAt' -- matches the Interface naming grammar <NN>_IntF_<Name>.",
            "The nickname follows the 12_Var_ naming convention, so this must be a VariableParam.",
        ]
        assert scoring.grammar_citation_rate(rationales) == pytest.approx(1.0)

    def test_returns_zero_for_a_degree_citing_rationale(self):
        rationales = [
            "Integer slider, in-degree 0, out-degree 1, driving the count "
            "input of procedure 11's tagged Divide Curve.",
        ]
        assert scoring.grammar_citation_rate(rationales) == pytest.approx(0.0)


class TestConfidenceSpreadOk:
    def test_false_for_five_identical_confidences(self):
        assert scoring.confidence_spread_ok([0.9, 0.9, 0.9, 0.9, 0.9]) is False

    def test_true_for_a_spread_set(self):
        assert scoring.confidence_spread_ok([0.9, 0.5, 0.7, 0.3, 0.95]) is True

    def test_true_when_fewer_than_five_proposals(self):
        assert scoring.confidence_spread_ok([0.9, 0.9]) is True


class TestBrierScore:
    def test_perfect_calibration_scores_zero(self):
        assert scoring.brier_score([1.0, 0.0], [True, False]) == pytest.approx(0.0)

    def test_worst_case_scores_one(self):
        assert scoring.brier_score([1.0, 0.0], [False, True]) == pytest.approx(1.0)


class TestEce:
    def test_returns_value_with_per_bin_counts(self):
        value, bins = scoring.ece([0.9, 0.2], [True, False])

        assert value == pytest.approx(0.15)
        assert len(bins) == 5
        assert sum(b["count"] for b in bins) == 2


class TestWilsonInterval:
    def test_18_of_30_lower_bound_below_half(self):
        lower, _upper = scoring.wilson_interval(18, 30)
        assert lower < 0.50

    def test_21_of_30_lower_bound_above_half(self):
        lower, _upper = scoring.wilson_interval(21, 30)
        assert lower > 0.50


def test_scoring_module_declares_no_scipy_or_numpy_imports():
    source = Path(scoring.__file__).read_text(encoding="utf-8")
    assert "import scipy" not in source
    assert "import numpy" not in source


# ── recognition_eval/corpus.py ──


class TestCorpusLoad:
    def test_frame_ablated_has_at_least_28_blocks_and_no_tier0_evidence(self):
        loaded = corpus.load("frame_ablated")

        assert len(loaded.blocks) >= 28
        assert loaded.tier0_evidence is False


_VALID_PROVENANCE_ROW = {
    "promptVersion": "r35.4",
    "provider": "anthropic",
    "model": "claude-test",
    "temperature": 0.2,
    "negotiatedMode": "strict",
    "contextSha256": "a" * 64,
    "frozenAtCommit": "b" * 40,
    "corpusVersion": 1,
}


class TestAssertProvenance:
    def test_passes_for_a_complete_row(self):
        corpus.assert_provenance(dict(_VALID_PROVENANCE_ROW))  # must not raise

    @pytest.mark.parametrize("missing_field", list(_VALID_PROVENANCE_ROW.keys()))
    def test_raises_for_each_missing_field(self, missing_field):
        row = dict(_VALID_PROVENANCE_ROW)
        del row[missing_field]
        with pytest.raises(corpus.ProvenanceError):
            corpus.assert_provenance(row)

    def test_raises_when_frozen_at_commit_is_unfrozen(self):
        row = dict(_VALID_PROVENANCE_ROW, frozenAtCommit="unfrozen")
        with pytest.raises(corpus.ProvenanceError):
            corpus.assert_provenance(row)


class TestAssertContextUnchanged:
    def test_raises_when_on_disk_context_is_tampered(self, tmp_path, monkeypatch):
        fixtures_dir = tmp_path / "recognition_eval"
        fixtures_dir.mkdir()

        context_content = '{"a": 1}'
        reference = {
            "corpus": "fake",
            "sourceContext": "fake.context.json",
            "contextSha256": hashlib.sha256(context_content.encode("utf-8")).hexdigest(),
            "annotatedBy": "test",
            "annotatedAt": "2026-01-01",
            "frozenAtCommit": "c" * 40,
            "ipClass": "own",
            "tier0Evidence": False,
            "corpusVersion": 1,
            "blocks": [],
            "abstainExpected": [],
        }

        (fixtures_dir / "fake.context.json").write_text(context_content, encoding="utf-8")
        (fixtures_dir / "fake.expected.json").write_text(json.dumps(reference), encoding="utf-8")

        monkeypatch.setattr(corpus, "FIXTURES_DIR", fixtures_dir)

        loaded = corpus.load("fake")
        corpus.assert_context_unchanged(loaded)  # unmodified: must not raise

        (fixtures_dir / "fake.context.json").write_text('{"a": 2}', encoding="utf-8")
        with pytest.raises(corpus.ProvenanceError):
            corpus.assert_context_unchanged(loaded)


class TestCheckFreezeCommit:
    def test_flags_reference_staged_with_the_recognition_prompt(self):
        violations = corpus.check_freeze_commit(
            [
                "data-service/fixtures/recognition_eval/frame_ablated.expected.json",
                "data-service/prompts/recognition_system.md",
            ]
        )
        assert violations

    def test_flags_reference_staged_with_the_fewshot_fixture(self):
        violations = corpus.check_freeze_commit(
            [
                "data-service/fixtures/recognition_eval/frame_ablated.expected.json",
                "data-service/fixtures/frame_recognition_fewshot.json",
            ]
        )
        assert violations

    def test_flags_reference_staged_with_cg_topology(self):
        violations = corpus.check_freeze_commit(
            [
                "data-service/fixtures/recognition_eval/frame_ablated.expected.json",
                "data-service/cg_topology.py",
            ]
        )
        assert violations

    def test_empty_when_no_reference_file_staged(self):
        violations = corpus.check_freeze_commit(["data-service/cg_topology.py"])
        assert violations == []

    def test_empty_when_reference_staged_alone(self):
        violations = corpus.check_freeze_commit(
            ["data-service/fixtures/recognition_eval/frame_ablated.expected.json"]
        )
        assert violations == []
