"""Shared pytest configuration.

Phase 35-13: registers the recognition eval harness's CLI options
(`--corpus`/`--arm`/`--arms`/`--sc1-gate`/`--permutations`, 35-AI-SPEC.md 5
"CI/CD integration") and the `eval`/`live` markers, with `not live` as the
default marker expression -- a developer running bare `pytest` must never
make a paid API call by accident.
"""

import pytest


def pytest_addoption(parser: pytest.Parser) -> None:
    group = parser.getgroup("recognition-eval")
    group.addoption(
        "--corpus",
        action="store",
        default=None,
        help="Recognition eval: corpus name to score (e.g. urbanblock_slice).",
    )
    group.addoption(
        "--arm",
        action="store",
        default=None,
        help="Recognition eval: single ablation arm id to run (e.g. A3).",
    )
    group.addoption(
        "--arms",
        action="store",
        default=None,
        help="Recognition eval: comma-separated ablation arm ids to sweep (e.g. A0,A0f,A1,A2,A3,A4,A5).",
    )
    group.addoption(
        "--sc1-gate",
        action="store",
        default=0.60,
        type=float,
        help="Recognition eval: SC1 ship-gate M1 threshold (default 0.60).",
    )
    group.addoption(
        "--permutations",
        action="store",
        default=1,
        type=int,
        help="Recognition eval: number of few-shot example-order permutations to sweep (default 1).",
    )


def pytest_configure(config: pytest.Config) -> None:
    config.addinivalue_line(
        "markers",
        "eval: recognition eval harness test (deterministic/replay by default, still not a unit test).",
    )
    config.addinivalue_line(
        "markers",
        "live: makes a live LLM call. Excluded by default -- pass -m live to run "
        "(and RECOGNITION_EVAL_MODE=record or =live).",
    )
    config.addinivalue_line(
        "markers",
        "integration: requires the compose network -- the `neo4j` hostname only "
        "resolves there (not from the host). Not deselected by default; select "
        "explicitly with `-k structural` or `-m integration` inside the container.",
    )


def pytest_collection_modifyitems(config: pytest.Config, items: list) -> None:
    """Deselect every `live`-marked item unless the user explicitly passed
    `-m ...` themselves -- a bare `pytest` run must never make a paid API
    call by accident (35-AI-SPEC.md 5)."""
    if config.option.markexpr:
        return  # user supplied -m explicitly; respect it verbatim

    selected, deselected = [], []
    for item in items:
        if item.get_closest_marker("live") is not None:
            deselected.append(item)
        else:
            selected.append(item)

    if deselected:
        config.hook.pytest_deselected(items=deselected)
        items[:] = selected
