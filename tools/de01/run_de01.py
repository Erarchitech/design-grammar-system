#!/usr/bin/env python
"""DE-01: the standalone cross-service runner CLI (spec/EVIDENCE-CONTRACT.md section 8;
plan 1200-05, Task 2).

Drives the golden fixture through all four legs, validates every leg's envelope
against the contract schema, compares canonical statuses per (rule, object) pair, and
emits both a machine-readable JSON report and a human-readable Markdown report. Exits
non-zero when ``silent_disagreement_count`` is greater than zero -- a leg being
unavailable does NOT by itself affect the exit code, per D-13: that is a typed outcome
recorded in the report, not a runner failure.

See tools/de01/README.md for invocation, per-leg preconditions, and the acceptance
rule stated operationally.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
TOOLS_DE01_DIR = Path(__file__).resolve().parent
if str(TOOLS_DE01_DIR) not in sys.path:
    sys.path.insert(0, str(TOOLS_DE01_DIR))

import legs  # noqa: E402
import report as report_module  # noqa: E402

ALL_LEG_NAMES = ("data-service", "dg-reasoner", "csharp", "replay")

_LEG_RUNNERS = {
    "data-service": legs.run_leg_data_service,
    "dg-reasoner": legs.run_leg_dg_reasoner,
    "csharp": legs.run_leg_csharp,
    "replay": legs.run_leg_replay,
}


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="run_de01.py",
        description="Drive the golden fixture through all four DE-01 legs and compare canonical statuses.",
    )
    parser.add_argument(
        "--fixture",
        default=str(REPO_ROOT / "fixtures" / "golden" / "fixture.json"),
        help=(
            "Path to the DE-01 fixture (default: fixtures/golden/fixture.json, the frozen "
            "golden fixture -- D-11, never modified). Pass "
            "fixtures/golden/replay/mixed-verdicts.json (or use --replay-fixture as a "
            "shorthand) to exercise a real, round-trippable Design State and a live "
            "canonical state hash agreement verdict (D-16) -- see "
            "fixtures/golden/replay/README.md."
        ),
    )
    parser.add_argument(
        "--replay-fixture",
        action="store_true",
        help=(
            "Shorthand for --fixture fixtures/golden/replay/mixed-verdicts.json -- the "
            "sibling fixture whose statePayloadJson round-trips through "
            "DesignStatePayloadV2Serializer.Deserialize, making a non-not_applicable "
            "canonical state hash agreement verdict reachable (D-16). Requires "
            "fixtures/golden/replay/seed-replay.cypher to have been applied first against "
            "project DG-1202-REPLAY. Overrides --fixture when both are passed."
        ),
    )
    parser.add_argument(
        "--out-dir",
        default=str(REPO_ROOT / ".de01"),
        help="Directory to write de01-report.json and de01-report.md into (default: .de01/).",
    )
    parser.add_argument(
        "--data-service-url",
        default="http://localhost:8000",
        help="Base URL for the data-service leg and the persisted-replay leg (default: http://localhost:8000).",
    )
    parser.add_argument(
        "--dg-reasoner-url",
        default="http://localhost:8001",
        help=(
            "Base URL for the dg-reasoner leg (default: http://localhost:8001). "
            "dg-reasoner has no host-exposed port in docker-compose.yml by default -- "
            "see tools/de01/README.md's per-leg precondition table."
        ),
    )
    parser.add_argument(
        "--legs",
        nargs="+",
        choices=ALL_LEG_NAMES,
        default=list(ALL_LEG_NAMES),
        help="Run only a subset of legs (default: all four).",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_arg_parser()
    args = parser.parse_args(argv)

    # --replay-fixture is a documented first-class shorthand (D-16) rather than a
    # path a future operator must remember -- overrides --fixture when both are
    # passed. The --fixture default itself is UNCHANGED: fixtures/golden/fixture.json.
    if args.replay_fixture:
        fixture_path = REPO_ROOT / "fixtures" / "golden" / "replay" / "mixed-verdicts.json"
    else:
        fixture_path = Path(args.fixture)
    if not fixture_path.is_file():
        print(f"run_de01.py: fixture not found at {fixture_path}", file=sys.stderr)
        return 1

    fixture = json.loads(fixture_path.read_text(encoding="utf-8"))

    config = {
        "fixture_path": str(fixture_path),
        "data_service_url": args.data_service_url,
        "dg_reasoner_url": args.dg_reasoner_url,
    }

    leg_results: dict[str, legs.LegResult] = {}
    for leg_name in args.legs:
        runner = _LEG_RUNNERS[leg_name]
        leg_results[leg_name] = runner(fixture, config)

    comparison = report_module.compare_legs(leg_results)

    # Second comparison dimension (D-16, plan 1202-07): the canonical DesignState
    # hash, computed alongside (never merged into) the per-(ruleId, objectId) row
    # comparison above. expectedCanonicalStateHash comes from the fixture when it
    # supplies one (e.g. fixtures/golden/replay/mixed-verdicts.json); the frozen
    # fixtures/golden/fixture.json carries none, so this is None for that run.
    expected_canonical_state_hash = fixture.get("expectedCanonicalStateHash")
    comparison.state_hash_comparison = report_module.compare_state_hashes(
        leg_results, expected_canonical_state_hash
    )

    # Exit-code rule is UNCHANGED: still non-zero only on silent_disagreement_count
    # > 0 (see this function's own return statement below), never on leg
    # unavailability. A state-hash "disagree" verdict IS folded into that same
    # counter here -- two legs that both claim to have replayed the same Design
    # State but computed different hashes is a silent disagreement in exactly the
    # sense comparison_rows' silent_disagreement classification already is. A
    # "not_applicable" verdict (fewer than two legs reported a hash) is a typed
    # absence, not a disagreement, and must NOT increment the counter -- this
    # mirrors how comparison_rows never counts a leg's mere unavailability as a
    # silent disagreement by itself. No new sys.exit / differently-conditioned
    # exit path is added anywhere in this file -- only this one counter changes.
    if comparison.state_hash_comparison.get("agreement") == "disagree":
        comparison.silent_disagreement_count += 1

    out_dir = Path(args.out_dir)
    json_path = out_dir / "de01-report.json"
    md_path = out_dir / "de01-report.md"

    fixture_version = fixture.get("fixtureVersion", "unknown")
    report_module.emit_json_report(comparison, json_path, fixture_version)
    report_module.emit_markdown_report(comparison, md_path, fixture_version)

    available_legs = [name for name, result in leg_results.items() if result.available]
    unavailable_legs = [name for name, result in leg_results.items() if not result.available]

    print(f"DE-01: reports written to {json_path} and {md_path}")
    print(f"DE-01: silent_disagreement_count = {comparison.silent_disagreement_count}")
    print(
        "DE-01: canonical state hash agreement = "
        f"{comparison.state_hash_comparison.get('agreement', 'not_applicable')}"
    )
    print(f"DE-01: available legs = {available_legs}")
    if unavailable_legs:
        print(f"DE-01: unavailable legs (typed error, not a crash) = {unavailable_legs}")

    return 1 if comparison.silent_disagreement_count > 0 else 0


if __name__ == "__main__":
    sys.exit(main())
