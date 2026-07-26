"""Corpus loading, provenance and freeze-protocol checks for the recognition
eval harness (Phase 35-11, 35-AI-SPEC.md 5 "Freeze protocol").

Test-only, deliberately: this package lives under `data-service/tests/` (not
`data-service/`) so nothing in production code can import it. A corpus
reference is a grading artifact, not a runtime dependency -- if
`recognition_eval` ever becomes importable from `data-service/*.py`, that is
itself a freeze-protocol violation (`grep -rn "recognition_eval" data-service/*.py`
must return no match).
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from pathlib import Path

# data-service/tests/recognition_eval/corpus.py -> parents[2] == data-service/
FIXTURES_DIR = Path(__file__).resolve().parents[2] / "fixtures" / "recognition_eval"


class ProvenanceError(ValueError):
    """Raised when a result row or corpus fails the freeze protocol's
    mechanical checks (35-AI-SPEC.md 5, freeze protocol items 3-4). A caller
    catching `ValueError` still catches this."""


@dataclass(frozen=True)
class Corpus:
    """A loaded `<name>.context.json` + `<name>.expected.json` pair."""

    name: str
    context: dict
    blocks: list[dict]
    abstain_expected: list[dict]
    tier0_evidence: bool
    ip_class: str
    corpus_version: int
    frozen_at_commit: str
    context_sha256: str


def load(corpus_name: str) -> Corpus:
    """Reads `fixtures/recognition_eval/<corpus_name>.context.json` and
    `.expected.json`, returning both as a `Corpus`."""
    context_path = FIXTURES_DIR / f"{corpus_name}.context.json"
    reference_path = FIXTURES_DIR / f"{corpus_name}.expected.json"

    context = json.loads(context_path.read_text(encoding="utf-8"))
    reference = json.loads(reference_path.read_text(encoding="utf-8"))

    return Corpus(
        name=corpus_name,
        context=context,
        blocks=reference["blocks"],
        abstain_expected=reference.get("abstainExpected", []),
        tier0_evidence=reference["tier0Evidence"],
        ip_class=reference["ipClass"],
        corpus_version=reference["corpusVersion"],
        frozen_at_commit=reference["frozenAtCommit"],
        context_sha256=reference["contextSha256"],
    )


# Freeze protocol item 3 (35-AI-SPEC.md 5): "Every result row records
# frozenAtCommit, contextSha256, promptVersion, provider, model, temperature
# and negotiatedMode. The harness refuses to score a run whose provenance
# block is incomplete." corpusVersion is required alongside them so a score
# is never silently compared across corpus versions (freeze protocol item 4).
REQUIRED_PROVENANCE_FIELDS = (
    "promptVersion",
    "provider",
    "model",
    "temperature",
    "negotiatedMode",
    "contextSha256",
    "frozenAtCommit",
    "corpusVersion",
)


def assert_provenance(result_row: dict) -> None:
    """Raises `ProvenanceError` unless `result_row` carries every field in
    `REQUIRED_PROVENANCE_FIELDS`, and again if `frozenAtCommit == "unfrozen"`
    -- a missing freeze commit must block a score, not default to a
    plausible-looking value (35-11-PLAN.md task 1)."""
    missing = [
        field
        for field in REQUIRED_PROVENANCE_FIELDS
        if field not in result_row or result_row[field] is None
    ]
    if missing:
        raise ProvenanceError(
            f"result row is missing required provenance field(s): {missing} -- "
            "the harness refuses to score a run whose provenance block is "
            "incomplete (35-AI-SPEC.md 5, freeze protocol item 3)."
        )

    if result_row["frozenAtCommit"] == "unfrozen":
        raise ProvenanceError(
            "result row's frozenAtCommit is 'unfrozen' -- the corpus this run "
            "was scored against was never frozen at a real commit; a missing "
            "freeze commit must block a score, not default to a "
            "plausible-looking value."
        )


def assert_context_unchanged(corpus: Corpus) -> None:
    """Raises `ProvenanceError` when the on-disk `<corpus.name>.context.json`'s
    SHA-256 no longer matches `corpus.context_sha256` -- the mechanical half
    of the freeze protocol, the part a rebase cannot defeat (35-AI-SPEC.md 5,
    freeze protocol item 3)."""
    context_path = FIXTURES_DIR / f"{corpus.name}.context.json"
    on_disk_sha256 = hashlib.sha256(context_path.read_bytes()).hexdigest()

    if on_disk_sha256 != corpus.context_sha256:
        raise ProvenanceError(
            f"{context_path.name}'s on-disk SHA-256 ({on_disk_sha256}) does not "
            f"match the reference's contextSha256 ({corpus.context_sha256}) -- "
            "the frozen input has changed since the reference was authored; "
            "scoring against it would be invalid."
        )


# Freeze protocol item 1 (35-AI-SPEC.md 5): "*.expected.json is committed in a
# SEPARATE commit from any change to prompts/recognition_system.md,
# fixtures/frame_recognition_fewshot.json, or cg_topology.py. If the
# reference and the prompt change in the same commit, the run is void."
_FREEZE_CONFLICT_SUFFIXES = (
    "prompts/recognition_system.md",
    "fixtures/frame_recognition_fewshot.json",
    "cg_topology.py",
)


def check_freeze_commit(staged_files: list[str]) -> list[str]:
    """Advisory freeze-protocol check (35-AI-SPEC.md 5, freeze protocol item
    2): returns the subset of `staged_files` that would void a run if
    committed alongside a `*.expected.json` change -- empty when there is no
    violation.

    Advisory only, and deliberately not installed as a pre-commit hook: a
    rebase or squash can defeat a staged-file check, so the REAL guarantee is
    `assert_context_unchanged` (above) plus the cassette key the harness
    records per run, not this function. This exists as a plain pytest
    assertion over `git diff --cached --name-only` so an accidental
    same-commit change is caught before it ships, not as the sole line of
    defence.
    """
    has_reference_change = any(path.endswith(".expected.json") for path in staged_files)
    if not has_reference_change:
        return []

    return [
        path
        for path in staged_files
        if any(path.endswith(conflict) for conflict in _FREEZE_CONFLICT_SUFFIXES)
    ]
