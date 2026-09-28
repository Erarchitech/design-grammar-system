#!/usr/bin/env python
"""DE-01 deterministic repeat runner (plan 1204-05, phase 1204; ALGN12-15).

Where ``tools/de01/run_de01.py`` proves cross-leg agreement on a *single* pass, this
controller repeats the same fixed-fixture DE-01 leg set across N fresh process
lifetimes and asks a narrower, falsifiable question: does every leg produce exactly
one distinct verdict projection hash across all N iterations, with
``silent_disagreement_count == 0`` in every iteration (D-08)?

Design constraints this module exists to honour:

- **D-01 -- reuse, never reimplement.** The four legs are imported from
  ``tools/de01/legs.py`` and the comparison is ``tools/de01/report.py``'s own
  ``compare_legs``, verbatim. ``DEFAULT_LEG_CALLABLES`` copies ``run_de01.py``'s
  ``_LEG_RUNNERS`` table exactly, swapping only the replay entry for the D-06
  pinned variant. A second leg implementation would be a second, drifting
  comparison -- the defect class this milestone exists to remove.
- **D-02 -- every leg carries a role.** ``LEG_ROLES`` is the single source of the
  ``evaluator`` / ``relay`` classification. Only ``evaluator`` legs may carry a
  validator-determinism claim; the relay legs (``data-service`` echoes the
  fixture's ``expectedOutcomes``, ``replay`` re-reads a persisted envelope) are
  reported under *round-trip stability*. Every emitted leg row draws its role from
  this one mapping, never from an inline literal.
- **D-05 -- N=10 across at least two fresh process lifetimes.** Iterations are
  split into ``batches`` contiguous chunks and a restart callable runs between
  batches (never inside one). Why restarts matter: CPython randomises string
  hashing per process, which changes ``set`` iteration order, and warm iterations
  inside one process share the hash seed -- so they cannot detect that class of
  nondeterminism at all.
- **D-08 -- the gate.** Passes iff every leg has exactly one distinct projection
  hash across all N *and* ``silent_disagreement_count == 0`` in every iteration.
  Nothing is averaged; a single divergence fails, and the diverging iteration
  pairs are recorded. Tuning the projection's exclusion list to make a divergence
  disappear is forbidden, and nothing here exposes a knob to do it.

No universal determinism claim is made anywhere in this module or its reports.
"Reimplement no leg" is enforced by construction: the only leg callables reachable
from ``DEFAULT_LEG_CALLABLES`` are the ``legs.py`` functions themselves.

The runner core is injectable -- ``leg_callables`` and ``restart`` are parameters,
not module globals -- so the whole gate is unit-testable with fakes and no live
stack (``python -m pytest tools/de01/tests/test_repeat_runner.py -k "not live"``).
"""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
TOOLS_DE01_DIR = Path(__file__).resolve().parent
if str(TOOLS_DE01_DIR) not in sys.path:
    sys.path.insert(0, str(TOOLS_DE01_DIR))

import httpx  # noqa: E402
import legs  # noqa: E402  (path-dependent import, see sys.path insert above)
import projection_hash  # noqa: E402
import report as report_module  # noqa: E402


# -- D-02: the single source of the evaluator/relay classification -----------------
#
# ``evaluator`` legs actually evaluate the rule and may carry a validator-determinism
# claim. ``relay`` legs do not: ``data-service`` echoes the fixture's
# ``expectedOutcomes`` (1204-CONTEXT.md Correction 1) and ``replay`` re-reads a
# persisted envelope, so their repetition is reported as *round-trip stability* and
# never as validator repeatability. Every emitted leg row and
# report_schema_repeat.json's ``leg_role`` enum are drawn from this one mapping.
LEG_ROLES: dict[str, str] = {
    "data-service": "relay",
    "dg-reasoner": "evaluator",
    "csharp": "evaluator",
    "replay": "relay",
}

REPEAT_REPORT_VERSION = "1.0.0"
"""Version of this runner's own report shape (mirrors report.py's DE01_REPORT_VERSION)."""

NON_PROOF_STATEMENT = (
    "N/N identical does not prove determinism; it fails to falsify it for this "
    "fixture, build and configuration."
)
"""The D-05 literal the report must carry. A failure to falsify is not a proof."""

# The label drift 1204-CONTEXT.md Correction 4 documents: the golden seed writes a
# ``:Run {Run_Id: 'RUN_GOLD_1200'}`` node (legs.py:47's FIXTURE_RUN_ID), but
# data-service's own read route matches ``:ValidationRun {runId}`` (app.py:685,
# GET /validation/view/{project}/{run_id} at app.py:2796). The seeded literal
# therefore does NOT resolve through the pinned route today -- which is exactly why
# D-06 pins the run id minted by iteration 1's data-service publish instead, and why
# this drift is recorded as a finding rather than "fixed" here (D-10: measure as
# shipped; the single-pass runner's own behaviour must not change under this plan).
LABEL_DRIFT_FINDING = (
    "Run-identity label drift (1204-CONTEXT.md Correction 4): the golden seed writes "
    ":Run {Run_Id: " + repr(legs.FIXTURE_RUN_ID) + "} (legs.py:47), but data-service's "
    "GET /validation/view/{project}/{run_id} matches :ValidationRun {runId} "
    "(app.py:685) -- so the seeded literal does not resolve through the pinned route. "
    "The D-06 pin is therefore the run id minted by iteration 1's data-service publish "
    "(a :ValidationRun.runId the route demonstrably resolves), recorded in this "
    "report's config block. Recorded as a finding; not fixed here (D-10 measure as "
    "shipped, and this plan adds no production change)."
)

# -- D-05: the only services ``--services`` may ever name ---------------------------
#
# Every name reaching ``docker compose restart`` is validated against this allowlist
# first (T-1204-05-04, command injection). Membership is drawn from
# docker-compose.yml's own service names; ``neo4j`` is deliberately absent -- the
# whole point of the restart is to give the two *Python* service legs fresh hash
# seeds, and bouncing the graph behind them would add unrelated variance.
RESTART_SERVICE_ALLOWLIST: frozenset[str] = frozenset({"data-service", "dg-reasoner"})

DEFAULT_SERVICES: tuple[str, ...] = ("data-service", "dg-reasoner")


# -- D-01: the leg dispatch table, copied from run_de01.py:33-38 verbatim -----------
#
# Same four entries, same callables, same order. The one deviation is the ``replay``
# entry, which points at the D-06 pinned variant so that repeat-mode reads a single
# pinned run id instead of whatever run happens to be newest at read time. Every
# callable is a ``legs.py`` function (or a thin wrapper around one) -- no leg logic is
# reimplemented here.
def _pinned_replay_leg_callable(
    fixture: dict[str, Any],
    config: dict[str, Any],
) -> "legs.LegResult":
    """The live replay callable used when ``run_repeat`` has pinned a run id.

    Reads ``config["pinned_replay_run_id"]`` -- set by :func:`run_repeat` from
    iteration 1's data-service envelope -- and delegates to
    :func:`run_leg_replay_pinned`. When no pin is present (the first iteration, or a
    direct call outside ``run_repeat``) it falls back to ``legs.run_leg_replay``, the
    un-pinned newest-run read, so this callable never invents a run id.
    """
    run_id = config.get("pinned_replay_run_id")
    if not run_id:
        return legs.run_leg_replay(fixture, config)
    return run_leg_replay_pinned(fixture, config, run_id)


DEFAULT_LEG_CALLABLES: dict[str, Callable[[dict[str, Any], dict[str, Any]], "legs.LegResult"]] = {
    "data-service": legs.run_leg_data_service,
    "dg-reasoner": legs.run_leg_dg_reasoner,
    "csharp": legs.run_leg_csharp,
    "replay": _pinned_replay_leg_callable,
}


@dataclass
class RepeatRunResult:
    """The outcome of one N-iteration repeat run (D-05/D-08).

    ``leg_hashes`` maps each leg name to its N projection hashes, in iteration order;
    ``per_iteration_silent_counts`` carries ``compare_legs``'s
    ``silent_disagreement_count`` for each iteration. ``gate_passed`` is the D-08
    verdict and ``diverging_pairs`` the evidence for a failure -- a leg whose hashes
    are not all identical contributes a ``{leg, iteration_a, iteration_b, hash_a,
    hash_b}`` entry naming its *first two* differing iterations, and every nonzero
    per-iteration silent count contributes an ``{iteration,
    silent_disagreement_count}`` entry. ``config`` holds the D-07 pin block and
    ``pinned_replay_run_id`` the D-06 pin (both ``None``/empty until Task 2 collects
    them).
    """

    leg_hashes: dict[str, list[str]] = field(default_factory=dict)
    per_iteration_silent_counts: list[int] = field(default_factory=list)
    gate_passed: bool = False
    diverging_pairs: list[dict[str, Any]] = field(default_factory=list)
    config: dict[str, Any] = field(default_factory=dict)
    pinned_replay_run_id: str | None = None


# -- Batch planning (D-05) ----------------------------------------------------------


def split_into_batches(iterations: int, batches: int) -> list[list[int]]:
    """Split ``iterations`` into ``batches`` contiguous 1-based iteration chunks.

    Iteration 1 is always in batch 1 (the pin is captured there, D-06). Chunks are
    ordered and cover every iteration exactly once. ``batches`` is clamped to
    ``[1, iterations]`` so a caller can never ask for more batches than iterations
    (which would create empty chunks that still triggered a restart) or for zero
    batches (which would silently drop every iteration). Remainder iterations are
    distributed to the *earlier* batches, so batch sizes differ by at most one and
    the last batch is never the oversized one -- with N=10/batches=2 that is
    ``[[1,2,3,4,5], [6,7,8,9,10]]``, exactly the shape D-05's split describes.
    """
    if iterations < 1:
        raise ValueError(f"iterations must be >= 1, got {iterations}")
    if batches < 1:
        raise ValueError(f"batches must be >= 1, got {batches}")

    effective_batches = min(batches, iterations)
    base, remainder = divmod(iterations, effective_batches)

    chunks: list[list[int]] = []
    next_iteration = 1
    for batch_index in range(effective_batches):
        size = base + (1 if batch_index < remainder else 0)
        chunks.append(list(range(next_iteration, next_iteration + size)))
        next_iteration += size
    return chunks


# -- The injectable core (D-01/D-05/D-06/D-08) --------------------------------------


def _distinct_hashes(hashes: list[str]) -> list[str]:
    """Distinct hashes in first-seen order -- the D-08 comparison unit.

    Order is preserved rather than sorted so the reported set reads in iteration
    order, which makes a diverging pair legible without cross-referencing indices.
    """
    seen: list[str] = []
    for value in hashes:
        if value not in seen:
            seen.append(value)
    return seen


def _first_divergence_pair(hashes: list[str]) -> tuple[int, int] | None:
    """The (first_index, second_index) 0-based pair of the first two differing hashes.

    ``None`` when every hash is identical (the D-08 pass case). Comparing against the
    *first* hash's first sighting is deliberate: it names the baseline iteration the
    divergence departs from, which is the pair an operator needs to diff -- not the
    two adjacent iterations that happen to sit next to each other in the list.
    """
    if not hashes:
        return None
    baseline = hashes[0]
    for index in range(1, len(hashes)):
        if hashes[index] != baseline:
            return (0, index)
    return None


def run_repeat(
    fixture: dict[str, Any],
    leg_callables: dict[str, Callable[[dict[str, Any], dict[str, Any]], Any]] | None = None,
    restart: Callable[[tuple[str, ...]], Any] | None = None,
    iterations: int = 10,
    batches: int = 2,
    config: dict[str, Any] | None = None,
    services: tuple[str, ...] = DEFAULT_SERVICES,
) -> RepeatRunResult:
    """Run ``iterations`` iterations of every leg, restarting between batches.

    Leg callables and the restart callable are injected, not looked up, so this core
    is unit-testable with fakes and no live stack (D-01's injectable-core contract).

    Per iteration, every leg in :data:`LEG_ROLES` key order is invoked once with
    ``(fixture, config)``; its envelope is hashed with
    ``projection_hash.verdict_projection_hash``; and ``report.compare_legs`` runs over
    that iteration's leg results so its ``silent_disagreement_count`` is recorded
    per iteration.

    ``restart`` fires **between** batches only -- ``batches - 1`` times for a run that
    is not clamped, never inside a batch -- which is what gives each batch a fresh
    process lifetime (D-05). Nothing is averaged anywhere: the gate is a per-leg
    set-equality check plus a per-iteration zero-silent-count check (D-08).
    """
    leg_callables = dict(DEFAULT_LEG_CALLABLES if leg_callables is None else leg_callables)
    chunk_plan = split_into_batches(iterations, batches)

    # Per-leg hash accumulator, pre-seeded in LEG_ROLES order so a leg that somehow
    # never ran still appears in the report (as an empty list) rather than vanishing.
    leg_hashes: dict[str, list[str]] = {leg_name: [] for leg_name in LEG_ROLES}
    per_iteration_silent_counts: list[int] = []
    pinned_replay_run_id: str | None = None
    if config is not None and config.get("pinned_replay_run_id"):
        pinned_replay_run_id = config["pinned_replay_run_id"]
    findings: list[str] = []

    for batch_index, chunk in enumerate(chunk_plan):
        if batch_index > 0 and restart is not None:
            # Between batches only: batch_index 0 is the first batch, so this fires
            # exactly len(chunk_plan) - 1 times, always at a batch boundary and never
            # inside one.
            restart(services)

        for iteration in chunk:
            iteration_config = dict(config) if config is not None else {}
            if pinned_replay_run_id:
                iteration_config["pinned_replay_run_id"] = pinned_replay_run_id

            leg_results: dict[str, Any] = {}
            for leg_name in LEG_ROLES:
                callable_for_leg = leg_callables.get(leg_name)
                if callable_for_leg is None:
                    raise KeyError(
                        f"leg_callables is missing '{leg_name}'; every leg in LEG_ROLES "
                        "must have a callable (D-01: no leg may be silently skipped)."
                    )
                if leg_name == "replay" and pinned_replay_run_id and iteration != 1:
                    # Iterations 2..N: the pin was already captured (below, at
                    # iteration 1) and every replay read from here on must address
                    # that same pinned run id. Iteration 1 is excluded on purpose --
                    # its own data-service publish is what mints the pin, so the pin
                    # does not exist yet when iteration 1's replay leg would need it.
                    iteration_config["pinned_replay_run_id"] = pinned_replay_run_id
                result = callable_for_leg(fixture, iteration_config)
                leg_results[leg_name] = result
                leg_hashes[leg_name].append(
                    projection_hash.verdict_projection_hash(result.envelope)
                )

            # D-06: capture the pin from iteration 1's data-service publish. The pin
            # is the envelope's ``definitionId`` (1204-CONTEXT.md Correction 3:
            # data-service passes ``definition_id=run_id`` at app.py:2358), and it is
            # held fixed for every subsequent replay read via ``iteration_config``
            # above. Captured once, at iteration 1 only -- a later iteration minting a
            # new run must not move the pin backwards out from under the comparison.
            if iteration == 1 and pinned_replay_run_id is None:
                data_service_envelope = leg_results["data-service"].envelope or {}
                candidate_run_id = data_service_envelope.get("definitionId")
                if candidate_run_id:
                    pinned_replay_run_id = candidate_run_id
                else:
                    findings.append(
                        "D-06 pin unavailable: iteration 1's data-service envelope carried "
                        "no definitionId, so no run id could be pinned. The replay leg "
                        "falls back to legs.run_leg_replay's newest-run route, which "
                        "weakens the replay comparison to round-trip stability only."
                    )

            comparison = report_module.compare_legs(leg_results)
            per_iteration_silent_counts.append(comparison.silent_disagreement_count)

    # -- D-08 gate + divergence evidence ------------------------------------------
    diverging_pairs: list[dict[str, Any]] = []
    for leg_name, hashes in leg_hashes.items():
        pair = _first_divergence_pair(hashes)
        if pair is not None:
            iteration_a, iteration_b = pair
            diverging_pairs.append(
                {
                    "leg": leg_name,
                    "iteration_a": iteration_a + 1,
                    "iteration_b": iteration_b + 1,
                    "hash_a": hashes[iteration_a],
                    "hash_b": hashes[iteration_b],
                }
            )

    for index, silent_count in enumerate(per_iteration_silent_counts):
        if silent_count:
            diverging_pairs.append(
                {"iteration": index + 1, "silent_disagreement_count": silent_count}
            )

    one_distinct_hash_per_leg = all(
        len(_distinct_hashes(hashes)) == 1 for hashes in leg_hashes.values()
    ) and bool(leg_hashes)
    no_silent_disagreements = all(
        count == 0 for count in per_iteration_silent_counts
    )
    gate_passed = one_distinct_hash_per_leg and no_silent_disagreements

    result_config = dict(config) if config is not None else {}
    result_config.setdefault("iterations", iterations)
    result_config.setdefault("batches", batches)
    if findings:
        existing_findings = result_config.get("findings")
        result_config["findings"] = list(existing_findings or []) + findings

    return RepeatRunResult(
        leg_hashes=leg_hashes,
        per_iteration_silent_counts=per_iteration_silent_counts,
        gate_passed=gate_passed,
        diverging_pairs=diverging_pairs,
        config=result_config,
        pinned_replay_run_id=pinned_replay_run_id,
    )


# -- D-06: the pinned-replay variant ------------------------------------------------
#
# ''run_leg_replay'' (legs.py:835-858) reads ``GET /validation/view/{project}`` -- the
# newest-run route. That is round-trip *stability* of whatever run happens to be
# newest at read time, not repeatability of one fixed subject: iteration k could be
# reading a different run from iteration 1. This variant changes exactly one thing --
# the URL gains ``/{run_id}`` -- so all N replay reads address the *same* run.
#
# The body below is copied from legs.py:835-938 with only line 858's URL changed
# (plus this docstring). No leg logic is reimplemented (D-01): same typed-error
# envelopes, same ``_seed_hint`` precondition pointer, same
# ``_validated_leg_result``-free direct return shape the original uses.


def run_leg_replay_pinned(
    fixture: dict[str, Any],
    config: dict[str, Any],
    run_id: str,
) -> "legs.LegResult":
    """Read one *pinned* persisted run back through the validation-view route.

    Identical to :func:`legs.run_leg_replay` except that the read is addressed at
    ``GET {base_url}/validation/view/{project}/{run_id}`` -- the route
    data-service's own leg already uses (legs.py:230, app.py:2796), which matches
    ``:ValidationRun {runId}`` (app.py:685). ``run_id`` is the D-06 pin captured
    from iteration 1's data-service publish, so every iteration reads the same run.

    Never raises: an unreachable service, a 404, a non-200, invalid JSON or an
    absent ``evidenceEnvelope`` all degrade to a typed ``error`` LegResult naming
    the missing precondition (D-13), exactly as the unpinned leg does.
    """
    base_url = config.get("data_service_url", "http://localhost:8000")
    project = fixture["project"]
    rule_id = fixture["rule"]["Rule_Id"]
    object_ids = [obj["objectId"] for obj in fixture["objects"]]

    def _seed_hint(extra: str) -> str:
        return (
            f"{extra} The persisted-replay leg requires fixtures/golden/seed.cypher to have been "
            f"applied first: cypher-shell -a bolt://localhost:7687 -u neo4j -p <password> -f "
            f"fixtures/golden/seed.cypher"
        )

    try:
        with httpx.Client(
            timeout=httpx.Timeout(connect=2.0, read=10.0, write=2.0, pool=2.0),
            headers=legs.data_service_auth_headers(),
        ) as client:
            response = client.get(f"{base_url}/validation/view/{project}/{run_id}")
    except httpx.RequestError as exc:
        return legs.LegResult(
            leg_name="replay",
            available=False,
            envelope=legs._synthesize_error_envelope(
                "replay",
                service_name="data-service",
                service_version="unknown",
                stage="validation.view.replay",
                reason=_seed_hint(f"could not reach {base_url}: {exc}."),
                rule_ids=[rule_id],
                object_ids=object_ids,
            ),
            error=f"connection error: {exc}",
        )
    except Exception as exc:  # noqa: BLE001
        return legs.LegResult(
            leg_name="replay",
            available=False,
            envelope=legs._synthesize_error_envelope(
                "replay",
                service_name="data-service",
                service_version="unknown",
                stage="validation.view.replay",
                reason=_seed_hint(f"unexpected error calling data-service: {exc}."),
                rule_ids=[rule_id],
                object_ids=object_ids,
            ),
            error=f"unexpected error: {exc}",
        )

    if response.status_code == 404:
        return legs.LegResult(
            leg_name="replay",
            available=False,
            envelope=legs._synthesize_error_envelope(
                "replay",
                service_name="data-service",
                service_version="unknown",
                stage="validation.view.replay",
                reason=_seed_hint(
                    f"GET {base_url}/validation/view/{project}/{run_id} returned 404 -- the pinned "
                    f"run id '{run_id}' does not resolve for project '{project}'."
                ),
                rule_ids=[rule_id],
                object_ids=object_ids,
            ),
            error="404: pinned run id not found",
        )

    if response.status_code != 200:
        detail = legs._safe_json(response)
        return legs.LegResult(
            leg_name="replay",
            available=False,
            envelope=legs._synthesize_error_envelope(
                "replay",
                service_name="data-service",
                service_version="unknown",
                stage="validation.view.replay",
                reason=_seed_hint(
                    f"GET {base_url}/validation/view/{project}/{run_id} returned "
                    f"{response.status_code}: {detail}."
                ),
                rule_ids=[rule_id],
                object_ids=object_ids,
            ),
            error=f"HTTP {response.status_code}: {detail}",
        )

    try:
        view_payload = response.json()
    except Exception as exc:  # noqa: BLE001
        return legs.LegResult(
            leg_name="replay",
            available=False,
            envelope=legs._synthesize_error_envelope(
                "replay",
                service_name="data-service",
                service_version="unknown",
                stage="validation.view.replay",
                reason=_seed_hint(f"response body was not valid JSON: {exc}."),
                rule_ids=[rule_id],
                object_ids=object_ids,
            ),
            error=f"invalid JSON response: {exc}",
        )

    envelope_dict = view_payload.get("evidenceEnvelope")
    if not envelope_dict:
        return legs.LegResult(
            leg_name="replay",
            available=False,
            envelope=legs._synthesize_error_envelope(
                "replay",
                service_name="data-service",
                service_version="unknown",
                stage="validation.view.replay",
                reason=_seed_hint(
                    f"GET {base_url}/validation/view/{project}/{run_id} returned no "
                    f"evidenceEnvelope for the pinned run."
                ),
                rule_ids=[rule_id],
                object_ids=object_ids,
            ),
            error="no evidenceEnvelope in validation view",
        )

    # Re-stamp stage so the report distinguishes this leg's re-derivation from
    # the publish-time envelope it re-reads (D-06), exactly mirroring
    # run_leg_replay's own re-stamp (legs.py:909-913).
    envelope_dict = dict(envelope_dict)
    envelope_dict["stage"] = "validation.view.replay"

    # Validate the dict directly against the JSON schema via the same
    # _validated_leg_result helper run_leg_replay uses (legs.py:130-152) --
    # NOT evidence_contract.validate_envelope, which expects an already-built
    # EvidenceEnvelope pydantic model (it calls envelope.model_dump()) and
    # signals failure by raising, never by returning non-None.
    result = legs._validated_leg_result("replay", envelope_dict)

    # canonicalStateHash/canonicalizationVersion (D-16): read from the same
    # view response, independent of envelope validation above, mirroring
    # run_leg_replay's own state_hash attachment (legs.py:975-984).
    canonical_state_hash = view_payload.get("canonicalStateHash")
    if canonical_state_hash:
        result.state_hash = {
            "hash": canonical_state_hash,
            "canonicalizationVersion": view_payload.get("canonicalizationVersion"),
        }

    return result


# -- D-07: the configuration pin block ---------------------------------------------
#
# A repeat run that does not record what it ran against is not evidence: "N/N
# identical" is meaningless if one iteration ran a different image or a different
# fixture build. This block pins the commit, the image ids, the SDK/build
# configuration, the sha256 of every fixture file, the contract/canonicalization
# versions, the per-leg serviceVersion, the D-06 pin and N/batches.
#
# What it deliberately does NOT record: environment variables (T-1204-05-03), any
# credential, or any .secrets/ path. Only the enumerated keys below are ever read.
#
# ``subprocess_runner`` is injectable so the whole block is unit-testable with no
# git, no docker and no network -- the same contract run_repeat uses for its legs.

IMAGE_NAMES: tuple[str, ...] = ("data-service", "dg-reasoner", "neo4j")
"""Compose services whose running image id is pinned (docker-compose.yml:19/42/…)."""

FIXTURE_FILES_FOR_PINNING: tuple[str, ...] = (
    "fixtures/golden/fixture.json",
    "fixtures/golden/replay/mixed-verdicts.json",
)
"""The fixture files hashed into the config block (D-07's fixture_sha256)."""


def _run_pin_command(
    cmd: list[str],
    subprocess_runner: Callable[..., Any],
    timeout: int = 60,
) -> subprocess.CompletedProcess | None:
    """Run one pinning command with list args (never ``shell=True``), or ``None``.

    A missing ``git``/``docker`` binary, a non-zero exit or any OSError degrades to
    ``None`` -- an unpinned field is a recorded absence, never a crash. No shell is
    ever involved, so no pinning argument can be interpreted as a shell metacharacter
    (T-1204-05-04).
    """
    try:
        completed = subprocess_runner(
            list(cmd),
            capture_output=True,
            text=True,
            timeout=timeout,
            check=False,
            shell=False,
        )
    except (OSError, subprocess.SubprocessError):
        return None
    if getattr(completed, "returncode", 1) != 0:
        return None
    return completed


def _stdout_or_none(completed: "subprocess.CompletedProcess | None") -> str | None:
    if completed is None:
        return None
    value = (completed.stdout or "").strip()
    return value or None


def _sha256_of_file(path: Path) -> str | None:
    """sha256 hexdigest of ``path``, or ``None`` when the file is absent.

    Typed-absence idiom (mirrors report_schema.json:92-134): a fixture that is not
    on disk is recorded as ``None``, never as a zero hash that would look like a
    real pin.
    """
    if not path.is_file():
        return None
    digest = hashlib.sha256()
    digest.update(path.read_bytes())
    return digest.hexdigest()


def collect_config_pins(
    fixture: dict[str, Any] | None = None,
    config: dict[str, Any] | None = None,
    subprocess_runner: Callable[..., Any] | None = None,
    *,
    service_versions: dict[str, str] | None = None,
) -> dict[str, Any]:
    """Build the D-07 configuration pin block for a repeat run.

    Returns exactly the keys D-07 enumerates (plus ``findings``, which carries the
    ``:Run`` vs ``:ValidationRun`` label-drift note from 1204-CONTEXT.md
    Correction 4). Every external probe is optional and degrades to a recorded
    absence:

    - ``git_commit`` -- ``git rev-parse HEAD`` (list args)
    - ``git_dirty`` -- ``git status --porcelain`` non-emptiness flag
    - ``image_ids`` -- per-service ``docker inspect -f {{.Id}} <service>``
    - ``dotnet_sdk_version`` -- ``dotnet --version``
    - ``build_configuration`` -- the DE-01 harness build configuration in effect
    - ``fixture_sha256`` -- sha256 of each file in
      :data:`FIXTURE_FILES_FOR_PINNING`
    - ``contract_version`` / ``canonicalization_version`` -- the contract and
      canonicalization versions the comparison is only valid under
    - ``service_versions`` -- per-leg ``serviceVersion``; dg-reasoner is expected to
      report ``"unknown"`` (1204-CONTEXT.md Correction 11)
    - ``pinned_replay_run_id``, ``iterations``, ``batches``
    - ``stale_image_check`` -- ``{checked: bool, note: str}``; records that the
      running image must be verified to hold the code under test (T-1204-05-06)
    - ``findings`` -- non-empty; always carries :data:`LABEL_DRIFT_FINDING`
    """
    fixture = fixture or {}
    config = dict(config or {})
    run = subprocess_runner if subprocess_runner is not None else subprocess.run

    git_commit = _stdout_or_none(_run_pin_command(["git", "rev-parse", "HEAD"], run))
    git_status = _stdout_or_none(
        _run_pin_command(["git", "status", "--porcelain"], run)
    )
    # None (git unavailable) is a typed absence, not "clean" -- an unpinned dirty
    # flag must not read as a verified clean tree.
    git_dirty: bool | None
    if git_commit is None and git_status is None:
        git_dirty = None
    else:
        git_dirty = bool(git_status)

    dotnet_sdk_version = _stdout_or_none(_run_pin_command(["dotnet", "--version"], run))

    image_ids: dict[str, str | None] = {}
    for service in IMAGE_NAMES:
        image_ids[service] = _stdout_or_none(
            _run_pin_command(["docker", "inspect", "-f", "{{.Id}}", service], run)
        )

    fixture_sha256: dict[str, str | None] = {
        relative: _sha256_of_file(REPO_ROOT / relative)
        for relative in FIXTURE_FILES_FOR_PINNING
    }

    if service_versions is None:
        service_versions = {
            "data-service": "unknown",
            "dg-reasoner": "unknown",  # Correction 11: no version endpoint
            "csharp": "unknown",
            "replay": "unknown",
        }

    fixture_version = fixture.get("fixtureVersion", "unknown")
    iterations = int(config.get("iterations", 10))
    batches = int(config.get("batches", 2))
    pinned_replay_run_id = config.get("pinned_replay_run_id") or None

    findings: list[str] = [LABEL_DRIFT_FINDING]
    pinned_image_ids = all(value is not None for value in image_ids.values())
    stale_image_check = {
        "checked": False,
        "note": (
            "The running image id(s) below were recorded from the live daemon, but whether "
            "each image actually contains the code under test was NOT verified by this run. "
            "docker compose reuses a previously built image when the compose file and "
            "Dockerfile inputs are unchanged, so a stale image can mask a source change: "
            "before treating an N/N result as evidence for THIS commit, rebuild "
            "(docker compose build) or confirm image ids match a build of git_commit. "
            f"Recorded image ids: {image_ids}."
        ),
    }
    if not pinned_image_ids:
        findings.append(
            "D-07 stale-image check partial: at least one of "
            f"{list(IMAGE_NAMES)} could not be inspected (docker unavailable or the "
            "container is not running), so its image id is recorded as null rather than "
            "guessed."
        )

    pins: dict[str, Any] = {
        "git_commit": git_commit,
        "git_dirty": git_dirty,
        "image_ids": image_ids,
        "dotnet_sdk_version": dotnet_sdk_version,
        "build_configuration": "Release",
        "fixture_sha256": fixture_sha256,
        "fixture_version": fixture_version,
        "contract_version": legs.evidence_contract.EVIDENCE_CONTRACT_VERSION,
        "canonicalization_version": legs.canonical_json.CANONICALIZATION_VERSION,
        "service_versions": service_versions,
        "pinned_replay_run_id": pinned_replay_run_id,
        "iterations": iterations,
        "batches": batches,
        "stale_image_check": stale_image_check,
        "findings": findings,
    }

    # The D-06 pin must be visible as an actual pin, not as a silently-absent key.
    if not pinned_replay_run_id:
        pins["findings"] = list(pins["findings"]) + [
            "D-06 pin absent from the config block: no pinned replay run id was supplied. "
            "Either the run did not reach iteration 1's capture, or --pinned-replay-run-id "
            "was not passed. The replay leg then falls back to the newest-run route, which "
            "supports round-trip stability only, never determinism."
        ]

    return pins


# -- D-24: the repeat report emitters (JSON + Markdown) -----------------------------
#
# Both emitters are pure writers over a RepeatRunResult: they read no environment
# variable, contact no service, and carry no credential (T-1204-05-03). Every leg row
# draws its ``leg_role`` from :data:`LEG_ROLES` -- never from an inline literal (D-02).
# The JSON shape is validated by tools/de01/report_schema_repeat.json, this module's
# sibling schema (never report_schema.json's, which describes a different report).


def _leg_pins(result: "RepeatRunResult") -> dict[str, dict[str, Any]]:
    """Per-leg report entries, in ``LEG_ROLES`` order, with the D-02 role attached."""
    legs: dict[str, dict[str, Any]] = {}
    for leg_name in LEG_ROLES:
        hashes = list(result.leg_hashes.get(leg_name, []))
        distinct = _distinct_hashes(hashes)
        legs[leg_name] = {
            "leg_role": LEG_ROLES[leg_name],
            "projectionHashes": hashes,
            "distinctHashCount": len(distinct),
            "gatePassed": len(distinct) == 1,
        }
    return legs


def build_repeat_report(result: "RepeatRunResult") -> dict[str, Any]:
    """The repeat report's JSON structure, before serialisation.

    Split out from :func:`emit_repeat_json_report` so the shape is inspectable (and
    assertable) without touching the filesystem. The non-proof statement lives in the
    ``gate`` object so it cannot be dropped from a report that carries a verdict.
    """
    config = dict(result.config or {})
    legs = _leg_pins(result)
    return {
        "repeatReportVersion": REPEAT_REPORT_VERSION,
        "generatedAt": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "fixtureVersion": config.get("fixture_version", "unknown"),
        "contractVersion": legs.get("contract_version") or legs_module_contract_version(),
        "canonicalizationVersion": config.get(
            "canonicalization_version", legs_module_canonicalization_version()
        ),
        "projectionVersion": projection_hash.PROJECTION_VERSION,
        "iterationsRequested": int(config.get("iterations", 0) or 0),
        "batchesRequested": int(config.get("batches", 0) or 0),
        "pinnedReplayRunId": result.pinned_replay_run_id,
        "legs": legs,
        "config": config,
        "iterations": {
            "count": len(result.per_iteration_silent_counts),
            "silentDisagreementCount": list(result.per_iteration_silent_counts),
            "divergingPairs": list(result.diverging_pairs),
        },
        "gate": {
            "passed": bool(result.gate_passed),
            "nonProofStatement": NON_PROOF_STATEMENT,
        },
        "findings": list(config.get("findings") or []),
    }


def legs_module_contract_version() -> str:
    """The contract version the compared envelopes are only admissible under."""
    return str(legs.evidence_contract.EVIDENCE_CONTRACT_VERSION)


def legs_module_canonicalization_version() -> int:
    """The canonicalization version the compared hashes are only meaningful under."""
    return int(legs.canonical_json.CANONICALIZATION_VERSION)


def emit_repeat_json_report(result: "RepeatRunResult", path: Path) -> None:
    """Write the machine-readable repeat report (validated against the sibling schema).

    ``indent=2``/``ensure_ascii=False`` mirror report.py:347-368. The JSON never
    embeds an environment-variable dump and never a credential: it is built from
    :func:`build_repeat_report`, whose only inputs are the run result and the D-07 pin
    block.
    """
    report = build_repeat_report(result)
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")


def emit_repeat_markdown_report(result: "RepeatRunResult", path: Path) -> None:
    """Write the human-readable repeat report.

    Opens with the D-08 verdict, lists every leg with its D-02 ``leg_role`` column and
    its distinct-hash count, records the per-iteration silent counts, prints the D-07
    configuration pins and any findings, and closes with the literal non-proof
    statement (D-05) so a reader cannot mistake N/N identical for a proof of
    determinism.
    """
    config = dict(result.config or {})
    legs = _leg_pins(result)
    verdict = "PASS" if result.gate_passed else "FAIL"
    generated = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

    lines: list[str] = []
    lines.append("# DE-01 Deterministic Repeat Benchmark Report")
    lines.append("")
    lines.append(f"**D-08 gate verdict:** {verdict}")
    lines.append(f"**Iterations:** {len(result.per_iteration_silent_counts)}")
    lines.append(f"**Batches:** {config.get('batches', 0)}")
    lines.append(f"**Pinned replay run id (D-06):** {result.pinned_replay_run_id}")
    lines.append(f"**Projection version:** {projection_hash.PROJECTION_VERSION}")
    lines.append(f"**Generated:** {generated}")
    lines.append("")
    lines.append(
        "Gate rule (D-08): passes iff every leg produced exactly one distinct projection "
        "hash across all N iterations AND `silent_disagreement_count == 0` in every "
        "iteration. Nothing is averaged; a single divergence fails."
    )
    lines.append("")

    lines.append("## Per-leg projection stability")
    lines.append("")
    lines.append("| Leg | Role | Iterations | Distinct hashes | Leg verdict |")
    lines.append("|---|---|---|---|---|")
    for leg_name in LEG_ROLES:
        entry = legs[leg_name]
        leg_verdict = "PASS" if entry["gatePassed"] else "FAIL"
        lines.append(
            f"| {leg_name} | {entry['leg_role']} | {len(entry['projectionHashes'])} | "
            f"{entry['distinctHashCount']} | {leg_verdict} |"
        )
    lines.append("")
    lines.append(
        "Roles are `LEG_ROLES` (D-02): only `evaluator` legs (csharp, dg-reasoner) may "
        "carry a validator-determinism claim. `relay` legs (data-service, replay) echo or "
        "re-read persisted evidence, so the table above reports round-trip stability for "
        "them, never validator repeatability."
    )
    lines.append("")

    lines.append("## Per-iteration silent disagreement counts")
    lines.append("")
    lines.append("| Iteration | silent_disagreement_count |")
    lines.append("|---|---|")
    for index, count in enumerate(result.per_iteration_silent_counts):
        lines.append(f"| {index + 1} | {count} |")
    lines.append("")

    if result.diverging_pairs:
        lines.append("## Diverging pairs (D-08 failure evidence)")
        lines.append("")
        for pair in result.diverging_pairs:
            lines.append(f"- `{json.dumps(pair, ensure_ascii=False, sort_keys=True)}`")
        lines.append("")

    lines.append("## Configuration pins (D-07)")
    lines.append("")
    for key in (
        "git_commit",
        "git_dirty",
        "dotnet_sdk_version",
        "build_configuration",
        "contract_version",
        "canonicalization_version",
        "pinned_replay_run_id",
        "iterations",
        "batches",
        "fixture_version",
    ):
        lines.append(f"- **{key}:** {config.get(key)}")
    lines.append(f"- **image_ids:** `{json.dumps(config.get('image_ids'), ensure_ascii=False, sort_keys=True)}`")
    lines.append(
        f"- **fixture_sha256:** `{json.dumps(config.get('fixture_sha256'), ensure_ascii=False, sort_keys=True)}`"
    )
    lines.append(
        f"- **service_versions:** `{json.dumps(config.get('service_versions'), ensure_ascii=False, sort_keys=True)}`"
    )
    stale = config.get("stale_image_check") or {}
    lines.append(f"- **stale_image_check.checked:** {stale.get('checked')}")
    lines.append(f"- **stale_image_check.note:** {stale.get('note')}")
    lines.append("")

    findings = list(config.get("findings") or [])
    lines.append("## Findings")
    lines.append("")
    if findings:
        for finding in findings:
            lines.append(f"- {finding}")
    else:
        lines.append("- none")
    lines.append("")

    lines.append("## Non-proof statement (D-05)")
    lines.append("")
    lines.append(NON_PROOF_STATEMENT)
    lines.append("")

    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines), encoding="utf-8")


# ══════════════════════════════════════════════════════════════════════════════════
# Task 4 -- the live CLI layer
#
# Nothing above this line is modified by Task 4. The CLI is purely additive: it parses
# arguments, wires the existing injectable core (:func:`run_repeat`) to the real leg
# callables and the real restart callable, collects the D-07 pins, and writes both
# reports. No leg is reimplemented here (D-01) and no determinism knob is exposed --
# the projection's exclusion list and the D-08 gate are untouchable from the command
# line (D-08).
#
# The exit-code contract mirrors run_de01.py:139-174 exactly: non-zero ONLY for a
# failed gate. A typed leg unavailability is a recorded fact in the report, not a
# runner crash, and must never move the exit code.
# ══════════════════════════════════════════════════════════════════════════════════

PLAY_STARTED_AT_FORMAT = "{{.Id}}"
"""The docker inspect Go-template this module asks for, per service, at each batch."""

INSPECT_ID_FORMAT = "{{.Id}}"
INSPECT_STARTED_AT_FORMAT = "{{.State.StartedAt}}"

RESTART_TIMEOUT_SECONDS = 120
"""Timeout for the restart and inspect calls, mirroring legs.py:680-697's ``timeout=120``."""

DEFAULT_COMPOSE_CMD: tuple[str, ...] = ("docker", "compose")
DEFAULT_INSPECT_CMD: str = "docker"


def _split_services(raw: str) -> list[str]:
    """Whitespace-split a ``--services`` value into individual service names."""
    return [token for token in str(raw).split() if token]


def _validate_services(services: "list[str] | tuple[str, ...]") -> list[str]:
    """Return ``services`` unchanged when every token is allow-listed; else raise.

    T-1204-05-04 (command injection via ``--services``): every name that could reach
    ``subprocess.run`` is checked against :data:`RESTART_SERVICE_ALLOWLIST` *before*
    any subprocess exists. Value is raised as :class:`ValueError` rather than as a
    usage error so this stays callable from tests and from the parser alike, and so
    ``shell``-shaped tokens (``data-service; rm -rf /``) fail on membership rather
    than on quoting.
    """
    names = list(services)
    if not names:
        raise ValueError("at least one service name is required")
    unknown = [name for name in names if name not in RESTART_SERVICE_ALLOWLIST]
    if unknown:
        raise ValueError(
            f"unknown service name(s) {unknown}; allowed services are "
            f"{sorted(RESTART_SERVICE_ALLOWLIST)} (RESTART_SERVICE_ALLOWLIST, "
            "T-1204-05-04). Service names are never passed to a shell."
        )
    return names


def _services_from_arg(raw: str) -> list[str]:
    """``argparse`` ``type=`` for ``--services``: split, then allow-list validate.

    ``argparse`` turns a raised :class:`ValueError` into a usage error, which exits 2
    -- the required unknown-name behaviour.
    """
    return _validate_services(_split_services(raw))


def build_arg_parser() -> argparse.ArgumentParser:
    """The repeat runner's argument parser (Task 4).

    Reuses the single-pass CLI's flag names and defaults for ``--fixture``,
    ``--data-service-url``, ``--dg-reasoner-url``, ``--legs`` and ``--out-dir``
    (run_de01.py:41-96) and adds the D-05/D-06 flags. ``--services`` is parsed through
    :func:`_services_from_arg`, so an unknown name is a usage error (exit 2) and never
    reaches a subprocess.
    """
    parser = argparse.ArgumentParser(
        prog="run_de01_repeat.py",
        description=(
            "Repeat the golden-fixture DE-01 leg set across N fresh process lifetimes, "
            "restarting the Python service legs between batches, and apply the D-08 "
            "determinism gate (one distinct verdict projection hash per leg, zero "
            "silent disagreements in every iteration)."
        ),
    )
    parser.add_argument(
        "--fixture",
        default=str(REPO_ROOT / "fixtures" / "golden" / "fixture.json"),
        help=(
            "Path to the DE-01 fixture (default: fixtures/golden/fixture.json, the "
            "frozen golden fixture -- D-11, never modified)."
        ),
    )
    parser.add_argument(
        "--iterations",
        type=int,
        default=10,
        help="Number of iterations to run (D-05 default: 10).",
    )
    parser.add_argument(
        "--batches",
        type=int,
        default=2,
        help=(
            "Number of contiguous iteration batches; a restart fires between batches "
            "only (D-05 default: 2)."
        ),
    )
    parser.add_argument(
        "--out-dir",
        default=str(REPO_ROOT / ".de01"),
        help=(
            "Directory to write de01-repeat-report.json and de01-repeat-report.md into "
            "(default: .de01/)."
        ),
    )
    parser.add_argument(
        "--services",
        type=_services_from_arg,
        default=_split_services("data-service dg-reasoner"),
        help=(
            "Whitespace-separated service names to restart between batches "
            "(default: 'data-service dg-reasoner'). Every name must be in the "
            "RESTART_SERVICE_ALLOWLIST; an unknown name is a usage error."
        ),
    )
    parser.add_argument(
        "--pinned-replay-run-id",
        default=None,
        help=(
            "D-06 pin: the persisted run id every replay read must address. When "
            "omitted, iteration 1's data-service publish mints the pin and it is held "
            "fixed for every later iteration."
        ),
    )
    parser.add_argument(
        "--data-service-url",
        default="http://localhost:8000",
        help="Base URL for the data-service leg and the pinned-replay leg (default: http://localhost:8000).",
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
        choices=tuple(LEG_ROLES),
        default=list(LEG_ROLES),
        help="Run only a subset of legs (default: all four, in LEG_ROLES order).",
    )
    return parser


def default_restart(
    services: "tuple[str, ...]" = DEFAULT_SERVICES,
    compose_cmd: "tuple[str, ...] | list[str] | None" = None,
    inspect_cmd: "str | None" = None,
) -> list[dict[str, Any]]:
    """The live restart callable: bounce ``services``, then record each container's id/start time.

    ``services`` is re-validated against :data:`RESTART_SERVICE_ALLOWLIST` here as well
    as at the parser, so a caller that bypasses ``--services`` still cannot smuggle a
    name (T-1204-05-04) into ``subprocess.run``.

    Two steps, both list-argument and shell-free:
    1. ``[compose, "restart", *services]`` -- ``check=True``, ``capture_output=True``,
       ``text=True``, ``timeout=120`` (the discipline of legs.py:680-697).
    2. per service, ``[inspect, "inspect", "-f", "{{.Id}}", service]`` and
       ``[inspect, "inspect", "-f", "{{.State.StartedAt}}", service]`` -- D-05
       requires the container id and start time to be recorded for each batch, so a
       reader can prove the batch really was a fresh container rather than take it on
       faith.

    Returns a list of ``{service, container_id, started_at}`` records, one per service.
    An inspect that fails or returns nothing is recorded as ``None`` rather than
    guessed or raised on: the restart itself already succeeded by then, and a missing
    id is a recorded absence, not a gate failure.
    """
    validated = _validate_services(services)
    compose = list(compose_cmd) if compose_cmd is not None else list(DEFAULT_COMPOSE_CMD)
    inspect = inspect_cmd if inspect_cmd is not None else DEFAULT_INSPECT_CMD

    subprocess.run(  # noqa: S603 - fixed argv list, shell=False, only allow-listed names
        [*compose, "restart", *validated],
        check=True,
        capture_output=True,
        text=True,
        timeout=RESTART_TIMEOUT_SECONDS,
        shell=False,
    )

    records: list[dict[str, Any]] = []
    for service in validated:
        records.append(
            {
                "service": service,
                "container_id": _inspect_field(inspect, INSPECT_ID_FORMAT, service),
                "started_at": _inspect_field(inspect, INSPECT_STARTED_AT_FORMAT, service),
            }
        )
    return records


def _inspect_field(inspect_cmd: "str | list[str]", format_string: str, service: str) -> "str | None":
    """One ``[inspect, "inspect", "-f", <format>, <service>]`` call; stdout or ``None``.

    List args, ``shell=False``, and a ``timeout`` -- the same discipline as the compose
    call above. Any failure (docker missing, container gone, non-zero exit) degrades to
    ``None``: this is a recording step, and losing a record must not fail a run that
    otherwise completed.
    """
    base = list(inspect_cmd) if isinstance(inspect_cmd, (list, tuple)) else [inspect_cmd]
    try:
        completed = subprocess.run(  # noqa: S603 - fixed argv list, shell=False
            [*base, "inspect", "-f", format_string, service],
            check=False,
            capture_output=True,
            text=True,
            timeout=RESTART_TIMEOUT_SECONDS,
            shell=False,
        )
    except (OSError, subprocess.SubprocessError):
        return None
    if completed.returncode != 0:
        return None
    value = (completed.stdout or "").strip()
    return value or None


def main(argv: "list[str] | None" = None) -> int:
    """Run the repeat benchmark end to end and return the process exit code.

    Wires the real leg callables (:data:`DEFAULT_LEG_CALLABLES`, i.e. ``legs.py``'s own
    functions plus the D-06 pinned replay variant) and :func:`default_restart` into
    :func:`run_repeat`, then collects the D-07 pins and writes both reports into
    ``--out-dir``.

    Exit code mirrors run_de01.py:139-174: ``1`` iff ``result.gate_passed`` is False,
    else ``0``. A typed leg unavailability (a leg returning ``available=False``) never
    changes the exit code -- it is a recorded outcome, not a runner failure. A missing
    fixture or an invalid ``--services`` name is a genuine usage/configuration error
    and does exit non-zero (2 for argparse, 1 for a missing fixture) because the run
    could not be attempted at all.
    """
    parser = build_arg_parser()
    args = parser.parse_args(argv)

    try:
        services = _validate_services(args.services)
    except ValueError as exc:
        parser.error(str(exc))  # usage error -> exit 2

    fixture_path = Path(args.fixture)
    if not fixture_path.is_file():
        print(f"run_de01_repeat.py: fixture not found at {fixture_path}", file=sys.stderr)
        return 1
    fixture = json.loads(fixture_path.read_text(encoding="utf-8"))

    config: dict[str, Any] = {
        "fixture_path": str(fixture_path),
        "data_service_url": args.data_service_url,
        "dg_reasoner_url": args.dg_reasoner_url,
        "iterations": args.iterations,
        "batches": args.batches,
    }
    if args.pinned_replay_run_id:
        config["pinned_replay_run_id"] = args.pinned_replay_run_id

    # --legs narrows the leg set from LEG_ROLES order; the full table is the default,
    # so the D-08 gate still sees every leg unless an operator explicitly narrows it.
    leg_callables = {name: DEFAULT_LEG_CALLABLES[name] for name in args.legs}

    restart_records: list[list[dict[str, Any]]] = []

    def _restart(batch_services: tuple[str, ...]) -> list[dict[str, Any]]:
        records = default_restart(batch_services)
        restart_records.append(records)
        return records

    result = run_repeat(
        fixture,
        leg_callables=leg_callables,
        restart=_restart,
        iterations=args.iterations,
        batches=args.batches,
        config=config,
        services=tuple(services),
    )

    # D-07 pins. Collected after the run so the pinned_replay_run_id reflects the id
    # run_repeat actually pinned (iteration 1's data-service publish) rather than only
    # whatever --pinned-replay-run-id supplied.
    pin_config = dict(config)
    if result.pinned_replay_run_id:
        pin_config["pinned_replay_run_id"] = result.pinned_replay_run_id
    result.config = collect_config_pins(fixture=fixture, config=pin_config)

    out_dir = Path(args.out_dir)
    json_path = out_dir / "de01-repeat-report.json"
    md_path = out_dir / "de01-repeat-report.md"
    emit_repeat_json_report(result, json_path)
    emit_repeat_markdown_report(result, md_path)

    print(f"DE-01 repeat: reports written to {json_path} and {md_path}")
    print(f"DE-01 repeat: iterations = {args.iterations}, batches = {args.batches}")
    print(f"DE-01 repeat: restart records = {restart_records}")
    print(f"DE-01 repeat: D-08 gate_passed = {result.gate_passed}")
    if result.diverging_pairs:
        print(f"DE-01 repeat: diverging pairs = {result.diverging_pairs}")

    # Exit-code rule (run_de01.py:139-174 mirrored): a failed gate is the ONLY
    # non-zero outcome. A leg being unavailable is a typed outcome in the report.
    return 1 if result.gate_passed is False else 0


if __name__ == "__main__":
    sys.exit(main())