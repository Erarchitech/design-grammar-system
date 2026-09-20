"""DE-01 comparison core and dual-format report emission (spec/EVIDENCE-CONTRACT.md
section 8; plan 1200-05, Task 2).

Invariant this module exists to guarantee (T-1200-23): ``compare_legs`` is the single
place a cross-leg difference could be silently lost. It has no branch that returns
agreement for unequal statuses, it never normalizes or coerces a status before
comparing, and it never skips a (rule, object) pair because one leg lacks it. A
difference is always classified as exactly one of:

- **agreement** -- every leg that reports on this pair reports the same canonical
  status.
- **declared non-equivalence** -- legs differ, and every differing leg's status is
  one of ``unsupported``, ``error``, ``not_evaluated``, or ``indeterminate`` AND
  carries a non-empty warning explaining it.
- **silent disagreement** -- legs differ in any other way. Counted in
  ``silent_disagreement_count``, which must be 0 for the golden fixture to accept
  DE-01 (spec/EVIDENCE-CONTRACT.md D-14).
"""

from __future__ import annotations

import json as json_module
import sys
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
DATA_SERVICE_DIR = REPO_ROOT / "data-service"
if str(DATA_SERVICE_DIR) not in sys.path:
    sys.path.insert(0, str(DATA_SERVICE_DIR))

import canonical_json  # noqa: E402  (path-dependent import, see sys.path insert above)
import evidence_contract  # noqa: E402

from legs import LegResult  # noqa: E402

# Statuses that MAY constitute a declared (non-silent) non-equivalence when they
# differ from another leg's status -- and only when accompanied by a non-empty
# warning. This is the fixed vocabulary subset spec/EVIDENCE-CONTRACT.md's D-05
# situation table reserves for "this leg could not produce a genuine verdict",
# never for a genuine passed/failed disagreement.
_DECLARABLE_STATUSES = {"unsupported", "error", "not_evaluated", "indeterminate"}

DE01_REPORT_VERSION = "1.0.0"


@dataclass
class ComparisonRow:
    """One (ruleId, objectId) pair's cross-leg comparison result."""

    rule_id: str
    object_id: str
    per_leg: dict[str, dict[str, Any]]
    classification: str  # "agreement" | "declared_non_equivalence" | "silent_disagreement"
    reason: str | None = None


@dataclass
class ComparisonResult:
    rows: list[ComparisonRow]
    legs: dict[str, LegResult]
    silent_disagreement_count: int
    declared_non_equivalences: list[dict[str, Any]] = field(default_factory=list)
    status_tally_by_leg: dict[str, dict[str, int]] = field(default_factory=dict)


def _rows_by_pair(envelope: dict[str, Any]) -> dict[tuple[str, str], list[dict[str, Any]]]:
    """Index an envelope's rows by (ruleId, objectId). A pair may have more than
    one row (e.g. the C# leg's synthesized ObjectPropertyAtom row alongside the
    object's primary evaluation row) -- both are kept, never deduplicated.
    """
    by_pair: dict[tuple[str, str], list[dict[str, Any]]] = {}
    for row in envelope.get("rows", []):
        key = (row["ruleId"], row["objectId"])
        by_pair.setdefault(key, []).append(row)
    return by_pair


def compare_legs(leg_results: dict[str, LegResult]) -> ComparisonResult:
    """Compare all legs' envelopes and classify every cross-leg difference.

    Builds the union of all (ruleId, objectId) pairs seen in ANY leg's envelope
    (available or not -- an unavailable leg's synthesized all-error envelope still
    carries the fixture's own pairs, so its absence is visible per-pair, not just
    at the leg level), ordered ascending by objectId, ties broken by ruleId
    (spec/EVIDENCE-CONTRACT.md section 4 -- the same normative order the envelopes
    themselves use). Every pair present in any leg appears in the output; a leg
    that has no row for a given pair is recorded as absent for that row, never
    silently omitted from the comparison.
    """
    per_leg_pairs: dict[str, dict[tuple[str, str], list[dict[str, Any]]]] = {
        leg_name: _rows_by_pair(result.envelope) for leg_name, result in leg_results.items()
    }

    all_pairs: set[tuple[str, str]] = set()
    for pairs in per_leg_pairs.values():
        all_pairs.update(pairs.keys())

    ordered_pairs = sorted(all_pairs, key=lambda pair: (pair[1], pair[0]))  # (objectId, ruleId)

    rows: list[ComparisonRow] = []
    silent_count = 0
    declared: list[dict[str, Any]] = []
    status_tally: dict[str, dict[str, int]] = {leg_name: {} for leg_name in leg_results}

    for rule_id, object_id in ordered_pairs:
        per_leg: dict[str, dict[str, Any]] = {}
        statuses_seen: set[str] = set()

        for leg_name, pairs in per_leg_pairs.items():
            leg_rows = pairs.get((rule_id, object_id))
            if not leg_rows:
                per_leg[leg_name] = {"present": False}
                continue

            # Multiple rows for the same pair (e.g. the C#-leg synthesized
            # ObjectPropertyAtom row) are all recorded; the pair's classification
            # walks every row this leg reported for it, not just the first.
            per_leg[leg_name] = {
                "present": True,
                "rows": [
                    {
                        "canonicalStatus": row["canonicalStatus"],
                        "warnings": row.get("warnings") or [],
                        "inputHash": row.get("inputHash"),
                        "outputHash": row.get("outputHash"),
                        "detail": row.get("detail"),
                        "serviceName": leg_results[leg_name].envelope.get("serviceName"),
                        "serviceVersion": leg_results[leg_name].envelope.get("serviceVersion"),
                    }
                    for row in leg_rows
                ],
            }
            for row in leg_rows:
                statuses_seen.add(row["canonicalStatus"])
                bucket = status_tally[leg_name]
                bucket[row["canonicalStatus"]] = bucket.get(row["canonicalStatus"], 0) + 1

        if len(statuses_seen) <= 1:
            classification = "agreement"
            reason = None
        else:
            # A difference exists. It is declared only if EVERY leg whose status
            # differs from the majority/most-common status set is itself reporting
            # a declarable status AND carries a non-empty warning. This function
            # never returns agreement here -- the len(statuses_seen) > 1 branch is
            # exhaustively either declared_non_equivalence or silent_disagreement,
            # with no third "treat as equal anyway" path.
            all_declarable_with_warning = True
            reasons: list[str] = []
            for leg_name, leg_data in per_leg.items():
                if not leg_data.get("present"):
                    continue
                for row in leg_data["rows"]:
                    status = row["canonicalStatus"]
                    if status not in _DECLARABLE_STATUSES:
                        continue
                    if not row["warnings"]:
                        all_declarable_with_warning = False
                    else:
                        reasons.append(f"{leg_name}: {row['warnings'][0]}")

            # Any non-declarable status participating in a difference makes that
            # difference silent, regardless of how many distinct non-declarable
            # statuses are present and regardless of what the other legs
            # reported. CR-02 (1200-REVIEW.md): the previous form of this guard
            # only fired when more than one distinct non-declarable status was
            # present, which let a lone non-declarable status (e.g. one leg
            # reporting `passed`, the sole non-declarable status here) pass
            # through as declared just because it was alone. Do not narrow this
            # back to a size-based condition.
            non_declarable_statuses = statuses_seen - _DECLARABLE_STATUSES
            if non_declarable_statuses:
                all_declarable_with_warning = False

            if all_declarable_with_warning and reasons:
                classification = "declared_non_equivalence"
                reason = "; ".join(reasons)
                declared.append(
                    {
                        "ruleId": rule_id,
                        "objectId": object_id,
                        "reason": reason,
                        "statuses": sorted(statuses_seen),
                    }
                )
            else:
                classification = "silent_disagreement"
                reason = f"Statuses disagree with no declared reason: {sorted(statuses_seen)}"
                silent_count += 1

        rows.append(
            ComparisonRow(
                rule_id=rule_id,
                object_id=object_id,
                per_leg=per_leg,
                classification=classification,
                reason=reason,
            )
        )

    return ComparisonResult(
        rows=rows,
        legs=leg_results,
        silent_disagreement_count=silent_count,
        declared_non_equivalences=declared,
        status_tally_by_leg=status_tally,
    )


def _row_to_dict(row: ComparisonRow) -> dict[str, Any]:
    return {
        "ruleId": row.rule_id,
        "objectId": row.object_id,
        "classification": row.classification,
        "reason": row.reason,
        "perLeg": row.per_leg,
    }


def emit_json_report(comparison: ComparisonResult, path: Path, fixture_version: str) -> None:
    """Write the structured DE-01 report: run metadata, per-leg availability, the
    ordered comparison rows, declared non-equivalences, per-status tallies, and
    ``silent_disagreement_count``.
    """
    report = {
        "de01ReportVersion": DE01_REPORT_VERSION,
        "generatedAt": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "fixtureVersion": fixture_version,
        "contractVersion": evidence_contract.EVIDENCE_CONTRACT_VERSION,
        "canonicalizationVersion": canonical_json.CANONICALIZATION_VERSION,
        "legs": {
            leg_name: {
                "available": result.available,
                "error": result.error,
                "serviceName": result.envelope.get("serviceName"),
                "serviceVersion": result.envelope.get("serviceVersion"),
                "stage": result.envelope.get("stage"),
            }
            for leg_name, result in comparison.legs.items()
        },
        "comparison_rows": [_row_to_dict(row) for row in comparison.rows],
        "declared_non_equivalences": comparison.declared_non_equivalences,
        "status_tally_by_leg": comparison.status_tally_by_leg,
        "silent_disagreement_count": comparison.silent_disagreement_count,
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json_module.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")


def emit_markdown_report(comparison: ComparisonResult, path: Path, fixture_version: str) -> None:
    """Write the human-readable Markdown sibling report.

    No in-repo Markdown-report generator exists to copy (1200-PATTERNS.md); this
    format is built directly from the plan's spec: a header stating the verdict
    and silent_disagreement_count, a per-leg availability table, a comparison
    table with one row per (rule, object) pair and one column per leg showing the
    canonical status, a declared non-equivalences section, and a warnings
    appendix.
    """
    lines: list[str] = []
    verdict = "PASS" if comparison.silent_disagreement_count == 0 else "FAIL"
    lines.append("# DE-01 Cross-Service Evidence Report")
    lines.append("")
    lines.append(f"**Verdict:** {verdict}")
    lines.append(f"**silent_disagreement_count:** {comparison.silent_disagreement_count}")
    lines.append(f"**Fixture version:** {fixture_version}")
    lines.append(f"**Contract version:** {evidence_contract.EVIDENCE_CONTRACT_VERSION}")
    lines.append(f"**Generated:** {datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')}")
    lines.append("")
    lines.append(
        "Acceptance rule (spec/EVIDENCE-CONTRACT.md section 8, D-14): a silent disagreement is a "
        "failure; a declared non-equivalence is not."
    )
    lines.append("")

    lines.append("## Per-leg availability")
    lines.append("")
    lines.append("| Leg | Available | Service | Version | Stage | Error |")
    lines.append("|---|---|---|---|---|---|")
    leg_names = sorted(comparison.legs.keys())
    for leg_name in leg_names:
        result = comparison.legs[leg_name]
        lines.append(
            f"| {leg_name} | {result.available} | {result.envelope.get('serviceName', '')} | "
            f"{result.envelope.get('serviceVersion', '')} | {result.envelope.get('stage', '')} | "
            f"{result.error or ''} |"
        )
    lines.append("")

    lines.append("## Comparison rows")
    lines.append("")
    header = "| ruleId | objectId | " + " | ".join(leg_names) + " | classification | reason |"
    sep = "|---|---|" + "---|" * len(leg_names) + "---|---|"
    lines.append(header)
    lines.append(sep)
    for row in comparison.rows:
        cells = []
        for leg_name in leg_names:
            leg_data = row.per_leg.get(leg_name, {"present": False})
            if not leg_data.get("present"):
                cells.append("absent")
            else:
                statuses = ", ".join(r["canonicalStatus"] for r in leg_data["rows"])
                cells.append(statuses)
        lines.append(
            f"| {row.rule_id} | {row.object_id} | " + " | ".join(cells)
            + f" | {row.classification} | {row.reason or ''} |"
        )
    lines.append("")

    lines.append("## Declared non-equivalences")
    lines.append("")
    if comparison.declared_non_equivalences:
        lines.append("| ruleId | objectId | statuses | reason |")
        lines.append("|---|---|---|---|")
        for item in comparison.declared_non_equivalences:
            lines.append(
                f"| {item['ruleId']} | {item['objectId']} | {', '.join(item['statuses'])} | "
                f"{item['reason']} |"
            )
    else:
        lines.append("None.")
    lines.append("")

    lines.append("## Status tally by leg")
    lines.append("")
    lines.append("| Leg | Tally |")
    lines.append("|---|---|")
    for leg_name in leg_names:
        tally = comparison.status_tally_by_leg.get(leg_name, {})
        tally_str = ", ".join(f"{status}={count}" for status, count in sorted(tally.items()))
        lines.append(f"| {leg_name} | {tally_str} |")
    lines.append("")

    lines.append("## Warnings appendix")
    lines.append("")
    any_warning = False
    for row in comparison.rows:
        for leg_name in leg_names:
            leg_data = row.per_leg.get(leg_name, {"present": False})
            if not leg_data.get("present"):
                continue
            for leg_row in leg_data["rows"]:
                if leg_row["warnings"]:
                    any_warning = True
                    lines.append(f"- **{leg_name}** / {row.rule_id} / {row.object_id}:")
                    for warning in leg_row["warnings"]:
                        lines.append(f"  - {warning}")
    if not any_warning:
        lines.append("None.")
    lines.append("")

    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines), encoding="utf-8")
