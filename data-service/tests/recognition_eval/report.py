"""Markdown + JSON run-report emitter for the recognition eval harness
(Phase 35-13, 35-AI-SPEC.md 5 "CI/CD integration" -- the human-readable
report is "the artifact that goes in the thesis appendix").

Runnable as `python -m tests.recognition_eval.report --out <path>`, writing
BOTH a markdown report and a sibling JSON file of the same run rows. NEVER
writes a prompt body or an API key into either output.

Rendering (`render_markdown`/`render_json`) is a PURE function of a list of
already-computed `ScoredRow`/`SkippedRow` records, independent of whether a
real corpus x arm sweep can succeed today -- this is what makes the report's
structure (Wilson interval + n=, ECE with per-bin counts, the ship-gate vs
claim-threshold verdicts, the "Not measured in this run" section) testable
with synthetic data regardless of whether any cassette has been recorded yet
(35-15's job). `run_report_sweep()` is the part that actually drives
`arms.run_arm()` through a replay `CassetteAdapter` and turns a cassette miss
into a `SkippedRow` rather than a crash -- a partial sweep must never read as
a full one.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from dataclasses import asdict, dataclass, field, replace
from pathlib import Path
from typing import Any

# data-service/tests/recognition_eval/report.py -> parents[2] == data-service/
_DATA_SERVICE_ROOT = str(Path(__file__).resolve().parents[2])
if _DATA_SERVICE_ROOT not in sys.path:
    sys.path.insert(0, _DATA_SERVICE_ROOT)
_TESTS_ROOT = str(Path(__file__).resolve().parents[1])
if _TESTS_ROOT not in sys.path:
    sys.path.insert(0, _TESTS_ROOT)

import cg_recognition  # noqa: E402
import cg_topology  # noqa: E402

from recognition_eval import arms as arms_module  # noqa: E402
from recognition_eval import cassette as cassette_module  # noqa: E402
from recognition_eval import corpus as corpus_module  # noqa: E402
from recognition_eval import scoring as scoring_module  # noqa: E402

DEFAULT_SC1_GATE_THRESHOLD = 0.60

# 35-AI-SPEC.md 5's LLM-judge policy: E4-name and E7-soft need a calibrated
# judge (>= 0.7 agreement on >= 20 human labels) that does not exist yet --
# always reported as uncalibrated/not measured, never silently omitted.
UNCALIBRATED_DIMENSIONS = ("E4-name (procedure attribution name semantics)", "E7-soft (rationale groundedness judge)")


def _collapse_var_const(kind: "str | None") -> "str | None":
    if kind in ("Var", "VariableParam", "Const", "ConstantParam"):
        return "Var/Const"
    return kind


@dataclass(frozen=True)
class ScoredRow:
    """One fully-scored (corpus x arm) row -- every field a rendered figure
    in the report reads from, and nothing else (no prompt body, no key)."""

    corpus: str
    arm_id: str
    claim: str
    provenance: "dict[str, Any]"
    tier0_evidence: bool
    n_blocks: int
    m1: float
    m1_successes: int
    m2: float
    mean_jaccard: float
    member_edit_distance: int
    m5: "dict[str, float]"
    e3_strict: float
    e3_collapsed: float
    e3_intf_false_positive_rate: float
    abstention_recall: float
    abstention_precision: float
    silent_drop_count: int
    brier: float
    ece_value: float
    ece_bins: "list[dict]"
    grammar_citation_rate: float
    e8_publishability_failures: int
    e8_note: str
    permutation_index: int = 0
    """Which few-shot ordering produced this row (0 == the as-authored order).
    Only ever non-zero when `run_report_sweep(..., permutations=N)` replayed
    the example-order sub-sweep."""


@dataclass(frozen=True)
class SkippedRow:
    """A (corpus x arm) combo that could not be scored this run -- printed,
    never silently dropped, so a partial sweep never reads as a full one."""

    corpus: str
    arm_id: str
    reason: str


def _e8_publishability_failures(match_result, corpus_obj: "Any") -> tuple[int, str]:
    """Proxy for E8 (35-AI-SPEC.md 5): counts exact-matched proposals whose
    matched reference block is marked `publishable: false` -- i.e. the model
    correctly identified a Const/parameter the reference itself documents as
    unrealisable at accept time.

    Honest limitation, stated once here: the REAL E8 check simulates
    `CanvasAnnotationParser.TryInferParameterDataType` (C#-only, 35-11's
    generator invokes it directly). This Python harness has no access to
    that classifier, so it reads the reference corpus's own `publishable`
    field instead of re-deriving it -- a proxy for "would this proposal
    survive accept-time parsing", not a re-simulation of the parser itself.
    """
    ref_by_id = {r["id"]: r for r in corpus_obj.blocks}
    failures = 0
    for pair in match_result.pairs:
        if pair.jaccard != 1.0:
            continue
        ref = ref_by_id[pair.reference_block_id]
        if ref.get("publishable") is False:
            failures += 1
    note = (
        "proxy metric: counts exact matches against reference blocks marked "
        "publishable:false; not a live re-simulation of "
        "CanvasAnnotationParser.TryInferParameterDataType (C#-only)."
    )
    return failures, note


def compute_scored_row(
    corpus_obj: "Any",
    arm: "arms_module.Arm",
    outcome: "dict[str, Any]",
) -> ScoredRow:
    """Score one `run_arm` outcome into a `ScoredRow`.

    PUBLIC on purpose: `live_sweep.run_live_sweep` is a hard consumer of this
    exact `(corpus_obj, arm, outcome) -> ScoredRow` signature and of
    `ScoredRow`'s field set, so it can score a permutation in-process rather
    than re-implementing the metric stack. It was previously underscore-private,
    which meant a routine refactor of this module's internals would silently
    break the record path -- a path exercised only by a paid, marker-gated
    test, so the break would have surfaced mid-metered-run. Treat the signature
    as a contract with `live_sweep.py`.
    """
    result = outcome["result"]
    proposal = result["proposal"]
    proposals = proposal.get("proposals") or []
    unrecognized = proposal.get("unrecognized") or []

    match_result = scoring_module.match_blocks(proposals, corpus_obj.blocks)
    m5 = scoring_module.m5_segmentation(match_result)

    exact_pairs = [p for p in match_result.pairs if p.jaccard == 1.0]
    ref_by_id = {r["id"]: r for r in corpus_obj.blocks}
    strict_hits = collapsed_hits = 0
    intf_false_positives = intf_total_proposed = 0
    for pair in exact_pairs:
        ref = ref_by_id[pair.reference_block_id]
        proposed_kind = proposals[pair.proposal_index].get("kind")
        ref_kind = ref.get("kind")
        if proposed_kind == ref_kind:
            strict_hits += 1
        if _collapse_var_const(proposed_kind) == _collapse_var_const(ref_kind):
            collapsed_hits += 1
        if proposed_kind in ("IntF", "Interface"):
            intf_total_proposed += 1
            if ref_kind not in ("IntF", "Interface"):
                intf_false_positives += 1

    residual_ids = cg_topology.scope_untagged(corpus_obj.context, None).node_ids
    silent_drops = scoring_module.silent_drop_count(residual_ids, proposals, unrecognized)

    matched_by_proposal_index = {pair.proposal_index: pair.jaccard for pair in match_result.pairs}
    confidences: "list[float]" = []
    outcomes: "list[bool]" = []
    for i, p in enumerate(proposals):
        conf = p.get("confidence")
        if not isinstance(conf, (int, float)):
            continue
        confidences.append(conf)
        outcomes.append(matched_by_proposal_index.get(i) == 1.0)
    brier = scoring_module.brier_score(confidences, outcomes)
    ece_value, ece_bins = scoring_module.ece(confidences, outcomes)

    grammar_rate = scoring_module.grammar_citation_rate([p.get("rationale", "") for p in proposals])
    e8_failures, e8_note = _e8_publishability_failures(match_result, corpus_obj)

    n_blocks = len(corpus_obj.blocks)
    m1_successes = len(exact_pairs)

    return ScoredRow(
        corpus=corpus_obj.name,
        arm_id=arm.id,
        claim=arm.claim,
        provenance=outcome["provenance"],
        tier0_evidence=corpus_obj.tier0_evidence,
        n_blocks=n_blocks,
        m1=scoring_module.m1_exact_rate(match_result),
        m1_successes=m1_successes,
        m2=scoring_module.m2_near_rate(match_result),
        mean_jaccard=scoring_module.mean_jaccard(match_result),
        member_edit_distance=scoring_module.member_edit_distance(match_result),
        m5=m5,
        e3_strict=(strict_hits / len(exact_pairs)) if exact_pairs else 0.0,
        e3_collapsed=(collapsed_hits / len(exact_pairs)) if exact_pairs else 0.0,
        e3_intf_false_positive_rate=(intf_false_positives / intf_total_proposed) if intf_total_proposed else 0.0,
        abstention_recall=scoring_module.abstention_recall(corpus_obj.abstain_expected, unrecognized),
        abstention_precision=scoring_module.abstention_precision(corpus_obj.abstain_expected, unrecognized),
        silent_drop_count=silent_drops,
        brier=brier,
        ece_value=ece_value,
        ece_bins=ece_bins,
        grammar_citation_rate=grammar_rate,
        e8_publishability_failures=e8_failures,
        e8_note=e8_note,
    )


def run_report_sweep(
    corpora: "list[str]",
    arm_ids: "list[str]",
    *,
    permutations: int = 1,
) -> "tuple[list[ScoredRow], list[SkippedRow]]":
    """Attempt every (corpus x arm) combo via a replay `CassetteAdapter`.
    A cassette miss or an incomplete-provenance refusal becomes a
    `SkippedRow`, never a crash -- so a report can always be produced, even
    before any cassette has been recorded (35-15's job).

    `permutations > 1` additionally replays the few-shot example-order
    sub-sweep, emitting one `ScoredRow` per (corpus x arm x ordering). Without
    it, the permutation cassettes that ARE committed (arm A3 has 6 of its 7
    recordings from the sub-sweep) were unreachable by any code in the repo:
    `run_live_sweep` scored each ordering in-process and persisted nothing but
    the cassette, and this — the only replay-side scorer — always replayed the
    as-authored order. The per-ordering M1 figures therefore lived only in
    pytest stdout and whatever was hand-copied into `35-EVAL-REPORT.md`, which
    made the sub-sweep the one result in a "goes in the thesis appendix"
    harness that could not be regenerated from committed state.

    Orderings come from `arms.few_shot_permutations`, the same generator the
    record path uses, so the replayed orderings are byte-identical to the
    recorded ones and hit the same cassette keys.
    """
    if permutations < 1:
        raise ValueError(
            f"permutations must be >= 1 (got {permutations!r}): a sweep of "
            "zero orderings measures nothing."
        )

    scored: "list[ScoredRow]" = []
    skipped: "list[SkippedRow]" = []

    for corpus_name in corpora:
        try:
            corpus_obj = corpus_module.load(corpus_name)
            corpus_module.assert_context_unchanged(corpus_obj)
        except (FileNotFoundError, corpus_module.ProvenanceError) as exc:
            for arm_id in arm_ids:
                skipped.append(SkippedRow(corpus=corpus_name, arm_id=arm_id, reason=f"corpus load failed: {exc}"))
            continue

        for arm_id in arm_ids:
            arm = arms_module.ARMS.get(arm_id)
            if arm is None:
                skipped.append(SkippedRow(corpus=corpus_name, arm_id=arm_id, reason="unknown arm id"))
                continue

            negotiated_mode = arms_module.resolve_real_negotiated_mode(arm)

            # Same generator the record path used, so the replayed orderings
            # are byte-identical to the recorded ones and hit the same keys.
            overrides: "list[list[dict[str, Any]] | None]"
            if permutations > 1:
                try:
                    base_artifacts = arms_module.resolve_arm_artifacts(arm)
                except Exception as exc:  # noqa: BLE001 -- git resolution can fail; never crash the report
                    skipped.append(
                        SkippedRow(
                            corpus=corpus_name,
                            arm_id=arm_id,
                            reason=f"few-shot artifact resolution failed: {type(exc).__name__}: {exc}",
                        )
                    )
                    continue
                overrides = list(
                    arms_module.few_shot_permutations(base_artifacts.few_shot_examples, n=permutations)
                )
            else:
                overrides = [None]

            for perm_idx, override in enumerate(overrides):
                # Only label rows when the sub-sweep actually ran, so a normal
                # single-ordering report is unchanged.
                label = f"{corpus_name} x {arm_id}" + (f" (ordering {perm_idx})" if permutations > 1 else "")
                adapter = cassette_module.CassetteAdapter(
                    arm_id,
                    None,
                    negotiated_mode=negotiated_mode,
                    prompt_version=cg_recognition.PROMPT_VERSION,
                    ip_class=corpus_obj.ip_class,
                    mode="replay",
                )
                try:
                    outcome = arms_module.run_arm(
                        arm,
                        corpus_obj,
                        adapter,
                        few_shot_examples_override=override,
                        negotiated_mode_override=negotiated_mode,
                    )
                    corpus_module.assert_provenance(outcome["provenance"])
                except cassette_module.CassetteMissError as exc:
                    skipped.append(SkippedRow(corpus=label, arm_id=arm_id, reason=f"cassette miss: {exc}"))
                    continue
                except corpus_module.ProvenanceError as exc:
                    skipped.append(SkippedRow(corpus=label, arm_id=arm_id, reason=f"provenance incomplete: {exc}"))
                    continue

                result = outcome["result"]
                if not result.get("valid"):
                    skipped.append(
                        SkippedRow(
                            corpus=label,
                            arm_id=arm_id,
                            reason=f"recognition run invalid: {result.get('violations')}",
                        )
                    )
                    continue

                row = compute_scored_row(corpus_obj, arm, outcome)
                if perm_idx:
                    row = replace(row, permutation_index=perm_idx)
                scored.append(row)

    return scored, skipped


def _format_ece_bins(bins: "list[dict]") -> str:
    parts = []
    for b in bins:
        parts.append(f"[{b['lower']:.1f}-{b['upper']:.1f}) n={b['count']}")
    return "; ".join(parts) if parts else "(no confidences to bin)"


def render_markdown(
    scored: "list[ScoredRow]",
    skipped: "list[SkippedRow]",
    *,
    sc1_gate_threshold: float = DEFAULT_SC1_GATE_THRESHOLD,
) -> str:
    lines: "list[str]" = ["# Recognition Eval Report (Phase 35-13, 35-AI-SPEC.md 5)", ""]

    if not scored:
        lines.append(
            "**No (corpus x arm) combo was scored in this run.** See "
            "'Not measured in this run' below -- every combo was skipped, "
            "most likely because no cassette has been recorded yet."
        )
        lines.append("")

    for row in scored:
        lo, hi = scoring_module.wilson_interval(row.m1_successes, row.n_blocks)
        ship_gate_pass = row.m1 >= sc1_gate_threshold
        claim_pass = lo > 0.50

        lines.append(f"## {row.corpus} x {row.arm_id}")
        lines.append("")
        lines.append(f"**Claim under test:** {row.claim}")
        lines.append("")
        prov = row.provenance
        lines.append(
            "**Provenance:** "
            f"promptVersion={prov.get('promptVersion')}, provider={prov.get('provider')}, "
            f"model={prov.get('model')}, temperature={prov.get('temperature')}, "
            f"negotiatedMode={prov.get('negotiatedMode')}, contextSha256={prov.get('contextSha256')}, "
            f"frozenAtCommit={prov.get('frozenAtCommit')}, corpusVersion={prov.get('corpusVersion')}, "
            f"fewShotSha={prov.get('fewShotSha')}"
        )
        lines.append("")
        lines.append(
            f"- **M1 (exact match rate):** {row.m1:.3f} (n={row.n_blocks}, "
            f"Wilson 95% CI [{lo:.3f}, {hi:.3f}])"
        )
        lines.append(
            f"- **M2 (near match, J>=0.5):** {row.m2:.3f}; mean Jaccard "
            f"{row.mean_jaccard:.3f}; member-edit distance {row.member_edit_distance}"
        )
        lines.append(
            f"- **M5 segmentation:** ratio={row.m5['ratio']:.3f}, "
            f"fragmentation={row.m5['fragmentation']:.3f}, fusion={row.m5['fusion']:.3f}"
        )
        lines.append(
            f"- **E3 kind accuracy:** strict={row.e3_strict:.3f}, "
            f"Var/Const collapsed={row.e3_collapsed:.3f}, "
            f"IntF false-positive rate={row.e3_intf_false_positive_rate:.3f}"
        )
        lines.append(
            f"- **E5 abstention:** recall={row.abstention_recall:.3f}, "
            f"precision={row.abstention_precision:.3f}; silent-drop count={row.silent_drop_count}"
        )
        lines.append(
            f"- **E6 calibration:** Brier={row.brier:.3f}; ECE={row.ece_value:.3f} "
            f"(bins: {_format_ece_bins(row.ece_bins)})"
        )
        lines.append(f"- **E7 grammar_citation_rate:** {row.grammar_citation_rate:.3f}")
        lines.append(f"- **E8 publishability failures:** {row.e8_publishability_failures} ({row.e8_note})")
        lines.append("")
        lines.append(f"**Ship gate (M1 >= {sc1_gate_threshold:.2f}):** {'PASS' if ship_gate_pass else 'FAIL'}")
        lines.append(
            f"**Claim threshold (Wilson lower bound > 0.50):** {'PASS' if claim_pass else 'FAIL'} "
            f"(lower bound {lo:.3f})"
        )
        if not row.tier0_evidence:
            lines.append("")
            lines.append(
                "> `evidence: false` -- this corpus carries `tier0Evidence: false` "
                "(Corpus A / frame_ablated); E0 figures for it are excluded from "
                "every reported SC1 figure (35-AI-SPEC.md 5)."
            )
        lines.append("")

    lines.append("## Not measured in this run")
    lines.append("")
    if skipped:
        for row in skipped:
            lines.append(f"- {row.corpus} x {row.arm_id}: {row.reason}")
    else:
        lines.append("- (every requested corpus x arm combo was scored)")
    lines.append("")
    lines.append("**Uncalibrated dimensions (excluded from SC1 until calibrated, 35-AI-SPEC.md 5):**")
    for dim in UNCALIBRATED_DIMENSIONS:
        lines.append(f"- {dim}")
    lines.append("")

    return "\n".join(lines)


def render_json(scored: "list[ScoredRow]", skipped: "list[SkippedRow]") -> "dict[str, Any]":
    return {
        "scored": [asdict(row) for row in scored],
        "skipped": [asdict(row) for row in skipped],
        "notMeasured": {
            "skippedCombos": [f"{row.corpus} x {row.arm_id}" for row in skipped],
            "uncalibratedDimensions": list(UNCALIBRATED_DIMENSIONS),
        },
    }


def _default_out_path() -> Path:
    data_dir = Path(os.getenv("DG_DATA_DIR", "/app/data"))
    return data_dir / "recognition-eval-report.md"


def main(argv: "list[str] | None" = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", default=str(_default_out_path()), help="Markdown output path (a sibling .json is also written).")
    parser.add_argument(
        "--corpora",
        default="frame_ablated,urbanblock_slice",
        help="Comma-separated corpus names to sweep.",
    )
    parser.add_argument(
        "--arms",
        default=",".join(arms_module.ARMS.keys()),
        help="Comma-separated arm ids to sweep.",
    )
    parser.add_argument("--sc1-gate", type=float, default=DEFAULT_SC1_GATE_THRESHOLD)
    parser.add_argument(
        "--permutations",
        type=int,
        default=1,
        help=(
            "Replay the few-shot example-order sub-sweep, emitting one row per "
            "(corpus x arm x ordering). Requires the permutation cassettes to "
            "have been recorded; missing ones become SkippedRows."
        ),
    )
    args = parser.parse_args(argv)

    corpora = [c.strip() for c in args.corpora.split(",") if c.strip()]
    arm_ids = [a.strip() for a in args.arms.split(",") if a.strip()]

    scored, skipped = run_report_sweep(corpora, arm_ids, permutations=args.permutations)
    markdown = render_markdown(scored, skipped, sc1_gate_threshold=args.sc1_gate)
    json_payload = render_json(scored, skipped)

    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(markdown, encoding="utf-8")
    out_path.with_suffix(".json").write_text(
        json.dumps(json_payload, indent=2, sort_keys=True), encoding="utf-8"
    )

    print(f"wrote {out_path} and {out_path.with_suffix('.json')}")
    print(f"scored {len(scored)} combo(s); skipped {len(skipped)} combo(s)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
