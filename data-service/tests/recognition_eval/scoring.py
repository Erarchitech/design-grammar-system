"""Deterministic, stdlib-only scoring core for the recognition eval harness
(Phase 35-11, 35-AI-SPEC.md 5 "The unit of measurement").

**Blocks -- not nodes, not canvases -- are the statistical *n*.** SC1 talks
about the architect accepting or redrawing a BLOCK, and the confirm UI's
smallest unit of correction is a block boundary. A per-node metric would
silently reward FM-4 (over-segmentation): splitting one true entity into many
correct-looking single-node proposals inflates a node-level accuracy score
while making the architect do more clicking, not less. `m5_segmentation`
exists specifically to catch over-segmentation (fragmentation) and its
catch-all mirror (fusion) -- the two failure modes a per-node count cannot see.

Net-new dependencies: zero. Jaccard, greedy matching, Brier, ECE and the
Wilson interval are all implementable with `math`, `statistics` and
`collections` alone -- no scipy, no numpy (35-AI-SPEC.md 2, 5).

This module is test-only and must never become importable from production
code (`data-service/tests/recognition_eval/` is not on the production import
path -- see corpus.py's module docstring, which forbids the OPPOSITE
direction: production code importing eval code). The one sanctioned
exception is the reverse -- this module importing `GRAMMAR_CITATION_PATTERNS`
FROM `cg_recognition` (production), so guardrail G7's online detector and
this module's offline `grammar_citation_rate` metric share one pattern set
and can never disagree (Phase 35-12 plan decision). That is a normal
test-imports-production dependency, not a freeze-protocol violation.
"""

from __future__ import annotations

import logging
import math
import statistics
import sys
from collections import Counter
from dataclasses import dataclass, field
from pathlib import Path
from typing import Iterable

# data-service/tests/recognition_eval/scoring.py -> parents[2] == data-service/,
# where cg_recognition.py lives. Inserted defensively so this module imports
# correctly regardless of the invoking test's cwd/sys.path setup.
_DATA_SERVICE_ROOT = str(Path(__file__).resolve().parents[2])
if _DATA_SERVICE_ROOT not in sys.path:
    sys.path.insert(0, _DATA_SERVICE_ROOT)

from cg_recognition import GRAMMAR_CITATION_PATTERNS  # noqa: E402

logger = logging.getLogger(__name__)


def _jaccard(a: Iterable[str], b: Iterable[str]) -> float:
    """Jaccard similarity over two member-id sets. Empty/empty is defined as
    0.0 (not 1.0) so two blocks with no members never masquerade as a match."""
    set_a, set_b = set(a), set(b)
    union = set_a | set_b
    if not union:
        return 0.0
    return len(set_a & set_b) / len(union)


@dataclass(frozen=True)
class MatchedPair:
    """One greedy-accepted (reference block, proposal) pairing."""

    reference_block_id: str
    proposal_index: int
    jaccard: float


@dataclass(frozen=True)
class MatchResult:
    """Output of `match_blocks`. Carries the original `proposals` and
    `reference_blocks` lists alongside the pairing so every metric function
    below can take just a `MatchResult` and look members up by id/index
    instead of re-threading both lists through every call."""

    proposals: list[dict]
    reference_blocks: list[dict]
    pairs: list[MatchedPair]
    misses: list[dict] = field(default_factory=list)
    """Reference blocks with no accepted proposal (recall failures)."""
    spurious: list[int] = field(default_factory=list)
    """Indices into `proposals` with no accepted reference block (precision
    failures) -- indices, not proposal dicts, since callers already have the
    proposals list and an index is unambiguous even when proposals repeat."""


def match_blocks(proposals: list[dict], reference_blocks: list[dict]) -> MatchResult:
    """Deterministic, reproducible block matcher (35-AI-SPEC.md 5's five-step rule).

    1. Compute Jaccard over member-id sets for every (proposal, reference) pair.
    2. Drop pairs where J == 0.
    3. Sort survivors by `(-J, reference_block_id, proposal_index)` -- a TOTAL
       order, so the result is byte-reproducible regardless of input order.
    4. Greedily accept top-down, skipping any pair whose proposal or
       reference block is already taken.
    5. Leftover reference blocks become `misses`; leftover proposals become
       `spurious`.

    Greedy is NOT guaranteed to maximise total Jaccard -- Hungarian assignment
    would be optimal, at the cost of scipy/numpy, which this harness must not
    depend on. At the corpus sizes here, where most true matches sit at
    J == 1.0, greedy and optimal coincide in practice (see
    test_recognition_scoring.py's brute-force comparison), but the gap is
    measured, not assumed away: whenever two or more surviving pairs tie on J
    for the SAME reference block, greedy's choice among them is arbitrary
    beyond `proposal_index` order, and that is logged here as a warning.
    """
    candidates: list[tuple[float, str, int]] = []
    for ref in reference_blocks:
        ref_id = ref["id"]
        ref_members = ref["memberIds"]
        for idx, proposal in enumerate(proposals):
            j = _jaccard(ref_members, proposal.get("memberIds", []))
            if j > 0.0:
                candidates.append((j, ref_id, idx))

    _warn_on_ties(candidates)

    candidates.sort(key=lambda t: (-t[0], t[1], t[2]))

    taken_refs: set[str] = set()
    taken_proposals: set[int] = set()
    pairs: list[MatchedPair] = []
    for j, ref_id, idx in candidates:
        if ref_id in taken_refs or idx in taken_proposals:
            continue
        pairs.append(MatchedPair(reference_block_id=ref_id, proposal_index=idx, jaccard=j))
        taken_refs.add(ref_id)
        taken_proposals.add(idx)

    misses = [ref for ref in reference_blocks if ref["id"] not in taken_refs]
    spurious = [i for i in range(len(proposals)) if i not in taken_proposals]

    return MatchResult(
        proposals=proposals,
        reference_blocks=reference_blocks,
        pairs=pairs,
        misses=misses,
        spurious=spurious,
    )


def _warn_on_ties(candidates: list[tuple[float, str, int]]) -> None:
    """Logs a warning for every reference block where >= 2 surviving
    candidate proposals share the same J -- the visible half of "greedy is
    not guaranteed optimal" (35-AI-SPEC.md's plan_decisions)."""
    by_ref: dict[str, list[float]] = {}
    for j, ref_id, _idx in candidates:
        by_ref.setdefault(ref_id, []).append(j)

    for ref_id, js in by_ref.items():
        tied = {j: count for j, count in Counter(js).items() if count >= 2}
        for j, count in tied.items():
            logger.warning(
                "match_blocks: %d proposals tie at J=%.4f for reference block %r "
                "-- greedy's choice among them is arbitrary beyond proposal_index order.",
                count,
                j,
                ref_id,
            )


def m1_exact_rate(result: MatchResult) -> float:
    """Fraction of reference blocks matched at J == 1.0 (set equality -- the
    architect clicks Accept and edits no boundary)."""
    if not result.reference_blocks:
        return 0.0
    exact = sum(1 for pair in result.pairs if pair.jaccard == 1.0)
    return exact / len(result.reference_blocks)


def m2_near_rate(result: MatchResult) -> float:
    """Fraction of reference blocks matched at J >= 0.5, recorded separately
    from exact because a boundary redraw is the most expensive correction in
    the confirm UI."""
    if not result.reference_blocks:
        return 0.0
    near = sum(1 for pair in result.pairs if pair.jaccard >= 0.5)
    return near / len(result.reference_blocks)


def mean_jaccard(result: MatchResult) -> float:
    """Mean Jaccard over the accepted pairs only (misses/spurious excluded --
    they have no Jaccard to average)."""
    if not result.pairs:
        return 0.0
    return sum(pair.jaccard for pair in result.pairs) / len(result.pairs)


def member_edit_distance(result: MatchResult) -> int:
    """The literal count of nodes the architect must add or remove to turn
    the proposals into the reference: symmetric-difference size for every
    matched pair, plus every member of an unmatched block on either side."""
    total = 0
    ref_by_id = {ref["id"]: ref for ref in result.reference_blocks}

    for pair in result.pairs:
        ref_members = set(ref_by_id[pair.reference_block_id]["memberIds"])
        proposal_members = set(result.proposals[pair.proposal_index].get("memberIds", []))
        total += len(ref_members ^ proposal_members)

    for miss in result.misses:
        total += len(miss["memberIds"])

    for idx in result.spurious:
        total += len(result.proposals[idx].get("memberIds", []))

    return total


def m5_segmentation(result: MatchResult) -> dict:
    """Segmentation ratio, fragmentation and fusion -- the FM-4 catch.

    Looks at ALL nonzero-overlap pairs, not just the pairs `match_blocks`
    greedily accepted, because over-segmentation and fusion are properties of
    the overlap graph as a whole, not of one particular assignment.

    - `ratio`: len(proposals) / len(reference_blocks).
    - `fragmentation`: mean, over reference blocks with >= 1 overlapping
      proposal, of how many DISTINCT proposals overlap that reference block.
      1.0 means no reference block was split across multiple proposals.
    - `fusion`: the mirror -- mean, over proposals with >= 1 overlapping
      reference block, of how many DISTINCT reference blocks that proposal
      overlaps. 1.0 means no proposal merged multiple reference blocks into
      one catch-all.
    """
    proposals = result.proposals
    reference_blocks = result.reference_blocks

    ratio = (len(proposals) / len(reference_blocks)) if reference_blocks else 0.0

    proposals_per_ref: dict[str, set[int]] = {ref["id"]: set() for ref in reference_blocks}
    refs_per_proposal: dict[int, set[str]] = {i: set() for i in range(len(proposals))}

    for ref in reference_blocks:
        ref_members = ref["memberIds"]
        for idx, proposal in enumerate(proposals):
            if _jaccard(ref_members, proposal.get("memberIds", [])) > 0.0:
                proposals_per_ref[ref["id"]].add(idx)
                refs_per_proposal[idx].add(ref["id"])

    overlapped_refs = [members for members in proposals_per_ref.values() if members]
    fragmentation = (
        sum(len(members) for members in overlapped_refs) / len(overlapped_refs)
        if overlapped_refs
        else 0.0
    )

    overlapped_proposals = [refs for refs in refs_per_proposal.values() if refs]
    fusion = (
        sum(len(refs) for refs in overlapped_proposals) / len(overlapped_proposals)
        if overlapped_proposals
        else 0.0
    )

    return {"ratio": ratio, "fragmentation": fragmentation, "fusion": fusion}


def nesting_agreement(
    result: MatchResult, proposal_host_index: dict[int, int | None] | None = None
) -> float:
    """Agreement rate over matched Pattern pairs' host relationship.

    `StructureProposal` (cg_schemas.py) carries no `hostBlockId` field of its
    own -- proposals are flat. `proposal_host_index` lets the caller supply,
    for a matched proposal's index, the index of the OTHER proposal it
    considers its host (or None for top-level), resolved however the caller's
    proposal payload encodes nesting. Defaults to "every proposal is
    top-level" when the caller has no nesting signal at all -- the honest
    answer, not an assumed one.

    Returns 1.0 (vacuously true) when there are no matched Pattern pairs to
    judge, so a corpus without nested patterns never drags this metric down.
    """
    proposal_host_index = proposal_host_index or {}
    ref_by_id = {ref["id"]: ref for ref in result.reference_blocks}
    matched_ref_by_proposal_index = {pair.proposal_index: pair.reference_block_id for pair in result.pairs}

    agreements = 0
    total = 0
    for pair in result.pairs:
        ref = ref_by_id[pair.reference_block_id]
        if ref.get("kind") != "Pattern":
            continue
        total += 1

        expected_host = ref.get("hostBlockId")
        proposed_host_index = proposal_host_index.get(pair.proposal_index)
        proposed_host_ref_id = (
            matched_ref_by_proposal_index.get(proposed_host_index)
            if proposed_host_index is not None
            else None
        )

        if proposed_host_ref_id == expected_host:
            agreements += 1

    return agreements / total if total else 1.0


def silent_drop_count(
    scoped_candidate_ids: Iterable[str], proposals: list[dict], unrecognized: list[dict]
) -> int:
    """Count of scoped candidate ids appearing in NEITHER `proposals[].memberIds`
    NOR `unrecognized[].memberIds` -- a hard gate that must be 0 (guardrail G6,
    RCGN-04's "never silently dropped" promise)."""
    addressed: set[str] = set()
    for proposal in proposals:
        addressed.update(proposal.get("memberIds", []))
    for block in unrecognized:
        addressed.update(block.get("memberIds", []))
    return sum(1 for candidate_id in scoped_candidate_ids if candidate_id not in addressed)


def abstention_recall(abstain_expected: list[dict], unrecognized: list[dict]) -> float:
    """Fraction of expected-abstain member ids the run actually abstained on.
    Vacuously 1.0 when the reference expects no abstentions."""
    expected_ids = {member_id for entry in abstain_expected for member_id in entry.get("memberIds", [])}
    if not expected_ids:
        return 1.0
    actual_ids = {member_id for entry in unrecognized for member_id in entry.get("memberIds", [])}
    return len(expected_ids & actual_ids) / len(expected_ids)


def abstention_precision(abstain_expected: list[dict], unrecognized: list[dict]) -> float:
    """Fraction of the run's actual abstentions that were expected. Vacuously
    1.0 when the run abstained on nothing (nothing to be wrong about)."""
    actual_ids = {member_id for entry in unrecognized for member_id in entry.get("memberIds", [])}
    if not actual_ids:
        return 1.0
    expected_ids = {member_id for entry in abstain_expected for member_id in entry.get("memberIds", [])}
    return len(expected_ids & actual_ids) / len(actual_ids)


def _cites_grammar(rationale: str) -> bool:
    """Reuses `cg_recognition.GRAMMAR_CITATION_PATTERNS` -- the SAME keyword
    set and `<NN>_<Kind>_<Name>` regex guardrail G7 checks online -- so this
    offline metric and the live guardrail can never drift apart."""
    lowered = rationale.lower()
    if any(keyword in lowered for keyword in GRAMMAR_CITATION_PATTERNS["keywords"]):
        return True
    # <NN>_<Kind>_<Name> forms cited as evidence, e.g. "matches 11_IntF_ParSplitAt".
    return GRAMMAR_CITATION_PATTERNS["name_pattern"].search(rationale) is not None


def grammar_citation_rate(rationales: list[str]) -> float:
    """Fraction of rationales that cite the naming grammar/convention as a
    REASON rather than graph evidence -- guardrail G7's live root cause (UAT
    F3): keyword scan for "grammar" / "convention" / "does not match", plus a
    regex for `<NN>_<Kind>_<Name>` forms used as justification. Must be 0.00
    for a healthy run."""
    if not rationales:
        return 0.0
    hits = sum(1 for rationale in rationales if _cites_grammar(rationale))
    return hits / len(rationales)


def confidence_spread_ok(confidences: list[float]) -> bool:
    """Mirrors guardrail G11 (35-AI-SPEC.md 6): False when >= 5 proposals
    carry a single unique confidence value or a near-zero spread
    (population stdev < 0.02) -- a rendered percentage that carries no
    information is worse than showing none. Fewer than 5 proposals is
    insufficient evidence to flag either way, so this defaults to True."""
    if len(confidences) < 5:
        return True
    if len(set(confidences)) == 1:
        return False
    return statistics.pstdev(confidences) >= 0.02


def brier_score(confidences: list[float], outcomes: list[bool]) -> float:
    """Mean squared error between predicted confidence and the binary
    correctness outcome (True = accepted/exact match)."""
    if len(confidences) != len(outcomes):
        raise ValueError("confidences and outcomes must be the same length")
    if not confidences:
        return 0.0
    return sum((c - (1.0 if o else 0.0)) ** 2 for c, o in zip(confidences, outcomes)) / len(confidences)


def ece(confidences: list[float], outcomes: list[bool], n_bins: int = 5) -> tuple[float, list[dict]]:
    """5 equal-width-bin Expected Calibration Error. Returns `(value, bins)` --
    NEVER report ECE without the per-bin counts: a bare scalar hides whether
    it is backed by 40 samples or 2 (35-AI-SPEC.md 5)."""
    if len(confidences) != len(outcomes):
        raise ValueError("confidences and outcomes must be the same length")

    edges = [i / n_bins for i in range(n_bins + 1)]
    bins: list[dict] = [
        {
            "lower": edges[i],
            "upper": edges[i + 1],
            "count": 0,
            "confidence_sum": 0.0,
            "outcome_sum": 0.0,
        }
        for i in range(n_bins)
    ]

    for confidence, outcome in zip(confidences, outcomes):
        idx = min(int(confidence * n_bins), n_bins - 1)
        bucket = bins[idx]
        bucket["count"] += 1
        bucket["confidence_sum"] += confidence
        bucket["outcome_sum"] += 1.0 if outcome else 0.0

    total = len(confidences)
    value = 0.0
    for bucket in bins:
        if bucket["count"] == 0:
            continue
        avg_confidence = bucket["confidence_sum"] / bucket["count"]
        avg_accuracy = bucket["outcome_sum"] / bucket["count"]
        value += (bucket["count"] / total) * abs(avg_confidence - avg_accuracy)

    return value, bins


def wilson_interval(successes: int, n: int, z: float = 1.96) -> tuple[float, float]:
    """Wilson score interval -- 35-AI-SPEC.md 5's SC1 claim-threshold arithmetic."""
    if n <= 0:
        return (0.0, 0.0)

    phat = successes / n
    z_sq = z * z
    denom = 1 + z_sq / n
    centre = phat + z_sq / (2 * n)
    margin = z * math.sqrt((phat * (1 - phat) + z_sq / (4 * n)) / n)

    lower = (centre - margin) / denom
    upper = (centre + margin) / denom
    return (max(0.0, lower), min(1.0, upper))
