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
        help="Path to the frozen golden fixture (default: fixtures/golden/fixture.json).",
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
    print(f"DE-01: available legs = {available_legs}")
    if unavailable_legs:
        print(f"DE-01: unavailable legs (typed error, not a crash) = {unavailable_legs}")

    return 1 if comparison.silent_disagreement_count > 0 else 0


if __name__ == "__main__":
    sys.exit(main())
