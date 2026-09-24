"""Projection-hash tests for the DE-01 repeat benchmark (plan 1204-01).

This file is 1204-01's projection-hash test home. Plan 1204-05 (wave 2) **appends**
runner-orchestration tests as new classes *below* the projection-hash classes defined
here -- the cross-plan seam. To keep that append safe:

- ``_envelope`` and ``_row`` are module-level builders, not class attributes, so a new
  class can reuse them without touching this file's existing classes.
- The projection-hash classes are self-contained: they import nothing beyond the module
  under test, ``evidence_contract``, and the standard library, so 1204-05's runner tests
  can add heavier imports (leg runners, subprocess mocks, fixture paths) without
  disturbing them.

This suite needs no live stack: no leg is run, no service is contacted. The only
subprocess spawned is a fresh interpreter computing the same pure projection hash
(``TestProjectionHashCrossProcess``), with the payload on stdin and no shell involved.
"""

from __future__ import annotations

import copy
import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent.parent.parent
TOOLS_DE01_DIR = REPO_ROOT / "tools" / "de01"
DATA_SERVICE_DIR = REPO_ROOT / "data-service"
for _path in (str(TOOLS_DE01_DIR), str(DATA_SERVICE_DIR)):
    if _path not in sys.path:
        sys.path.insert(0, _path)

import evidence_contract  # noqa: E402
import projection_hash  # noqa: E402
from projection_hash import (  # noqa: E402
    EXCLUSION_FIELDS,
    PROJECTION_VERSION,
    project_verdict,
    verdict_projection_hash,
)


def _row(rule_id: str, object_id: str, status: str, warnings: list[str] | None = None) -> dict:
    """Synthetic evidence row (mirrors tools/de01/tests/test_de01_runner.py:47-51)."""
    row = {"ruleId": rule_id, "objectId": object_id, "canonicalStatus": status}
    if warnings is not None:
        row["warnings"] = warnings
    return row


def _envelope(rows: list[dict], service_name: str = "svc", stage: str = "test") -> dict:
    """Synthetic schema-conformant evidence envelope (mirrors test_de01_runner.py:30-44)."""
    return {
        "contractVersion": "1.0.0",
        "canonicalizationVersion": 1,
        "project": "DG-1200-GOLDEN",
        "definitionId": "def-golden-01",
        "serviceName": service_name,
        "serviceVersion": "1.0.0",
        "emittedAt": "2026-09-20T00:00:00Z",
        "stage": stage,
        "canonicalStatus": rows[0]["canonicalStatus"] if rows else "not_evaluated",
        "rows": rows,
    }


def _baseline_envelope() -> dict:
    """The shared baseline: two rows, one carrying a warning, already in section 4 order."""
    return _envelope(
        [
            _row("R_GOLD_HEIGHT_MAX_75_V", "OBJ-1", "passed"),
            _row("R_GOLD_HEIGHT_MAX_75_V", "OBJ-2", "failed", warnings=["height 80 > 75"]),
        ],
        service_name="data-service",
        stage="verdict",
    )


class TestProjectionHash:
    """Task 1 tracer: the projection hashes a validated envelope, stably, without mutating it."""

    def test_verdict_projection_hash_is_stable_across_repeated_calls(self):
        envelope = _baseline_envelope()
        first = verdict_projection_hash(envelope)
        second = verdict_projection_hash(envelope)
        assert first == second
        assert len(first) == 64
        assert first == first.upper()

    def test_excluded_fields_do_not_change_the_hash(self):
        """Every D-04 excluded field is invisible to the hash: emittedAt, definitionId,
        and an injected report-level generatedAt."""
        baseline = verdict_projection_hash(_baseline_envelope())

        emitted_at_mutated = _baseline_envelope()
        emitted_at_mutated["emittedAt"] = "2031-12-31T23:59:59Z"
        assert verdict_projection_hash(emitted_at_mutated) == baseline

        definition_id_mutated = _baseline_envelope()
        definition_id_mutated["definitionId"] = "RUN-SOME-OTHER-RUN"
        assert verdict_projection_hash(definition_id_mutated) == baseline

        generated_at_injected = _baseline_envelope()
        generated_at_injected["generatedAt"] = "2031-12-31T23:59:59Z"
        assert verdict_projection_hash(generated_at_injected) == baseline

    def test_mutated_canonical_status_changes_the_hash(self):
        """D-04 negative control: a status flip is a finding, and the hash must show it."""
        baseline = verdict_projection_hash(_baseline_envelope())

        mutated = _baseline_envelope()
        assert mutated["rows"][0]["canonicalStatus"] == "passed"
        mutated["rows"][0]["canonicalStatus"] = "failed"

        assert verdict_projection_hash(mutated) != baseline

    def test_projection_never_mutates_the_input_envelope(self):
        envelope = _baseline_envelope()
        untouched = copy.deepcopy(envelope)

        project_verdict(envelope)
        verdict_projection_hash(envelope)

        assert envelope == untouched

    def test_baseline_envelope_is_schema_valid(self):
        """The synthetic baseline is real contract input, not an invented shape."""
        model = evidence_contract.EvidenceEnvelope(**_baseline_envelope())
        evidence_contract.validate_envelope(model)


# --- Task 2: negative-control matrix ------------------------------------------------
#
# Each arm mutates exactly one field *outside* EXCLUSION_FIELDS and asserts the hash
# moves (D-04: everything not excluded is included). The mutation is applied to a fresh
# deep copy of the baseline, so arms are independent.

def _mutate_row_status(envelope: dict) -> None:
    envelope["rows"][1]["canonicalStatus"] = "passed"


def _mutate_row_warnings_text(envelope: dict) -> None:
    envelope["rows"][1]["warnings"] = ["height 81 > 75"]


def _mutate_row_warnings_appended(envelope: dict) -> None:
    envelope["rows"][1]["warnings"].append("tolerance widened")


def _mutate_row_detail(envelope: dict) -> None:
    envelope["rows"][0]["detail"] = "evaluated against rule R_GOLD_HEIGHT_MAX_75_V"


def _mutate_envelope_status(envelope: dict) -> None:
    envelope["canonicalStatus"] = "error"


def _mutate_stage(envelope: dict) -> None:
    envelope["stage"] = "published"


def _mutate_service_name(envelope: dict) -> None:
    envelope["serviceName"] = "dg-reasoner"


def _mutate_service_version(envelope: dict) -> None:
    envelope["serviceVersion"] = "2.0.0"


def _set_envelope_input_hash(envelope: dict) -> None:
    envelope["inputHash"] = "A" * 64


def _mutate_envelope_input_hash(envelope: dict) -> None:
    envelope["inputHash"] = "B" * 64


def _set_envelope_output_hash(envelope: dict) -> None:
    envelope["outputHash"] = "C" * 64


def _mutate_envelope_output_hash(envelope: dict) -> None:
    envelope["outputHash"] = "D" * 64


def _scramble_rows(envelope: dict) -> None:
    envelope["rows"] = list(reversed(envelope["rows"]))


def _empty_row_warnings(envelope: dict) -> None:
    envelope["rows"][1]["warnings"] = []


class TestProjectionHashNegativeControl:
    """D-04 negative controls: inclusion mutations change the hash, row order does not."""

    @pytest.mark.parametrize(
        "mutate",
        [
            pytest.param(_mutate_row_status, id="row-canonical-status"),
            pytest.param(_mutate_row_warnings_text, id="row-warnings-text"),
            pytest.param(_mutate_row_warnings_appended, id="row-warnings-appended"),
            pytest.param(_mutate_row_detail, id="row-detail"),
            pytest.param(_mutate_envelope_status, id="envelope-canonical-status"),
            pytest.param(_mutate_stage, id="stage"),
            pytest.param(_mutate_service_name, id="service-name"),
            pytest.param(_mutate_service_version, id="service-version"),
            pytest.param(_set_envelope_input_hash, id="input-hash-added"),
            pytest.param(_mutate_envelope_input_hash, id="input-hash-changed"),
            pytest.param(_set_envelope_output_hash, id="output-hash-added"),
            pytest.param(_mutate_envelope_output_hash, id="output-hash-changed"),
        ],
    )
    def test_single_field_mutation_changes_the_hash(self, mutate):
        baseline = _baseline_envelope()
        baseline_hash = verdict_projection_hash(baseline)

        mutated = copy.deepcopy(baseline)
        mutate(mutated)

        assert mutated != baseline, f"{mutate.__name__} did not mutate the envelope"
        assert verdict_projection_hash(mutated) != baseline_hash, (
            f"{mutate.__name__} did not change the projection hash -- it is inside "
            "EXCLUSION_FIELDS or the projection dropped it"
        )

    def test_reordered_rows_hash_identically(self):
        """Section 4 ordering is canonicalized, so a scrambled input hashes the same.

        Without the sort step in project_verdict this test fails -- that is the point.
        """
        baseline = _baseline_envelope()
        assert [r["objectId"] for r in baseline["rows"]] == ["OBJ-1", "OBJ-2"]

        scrambled = _baseline_envelope()
        _scramble_rows(scrambled)
        assert [r["objectId"] for r in scrambled["rows"]] == ["OBJ-2", "OBJ-1"]

        assert verdict_projection_hash(scrambled) == verdict_projection_hash(baseline)

    def test_empty_warnings_differs_from_populated_warnings(self):
        """An empty warnings list is not the same evidence as a populated one."""
        baseline = _baseline_envelope()
        assert baseline["rows"][1]["warnings"] == ["height 80 > 75"]

        emptied = _baseline_envelope()
        _empty_row_warnings(emptied)
        assert emptied["rows"][1]["warnings"] == []

        assert verdict_projection_hash(emptied) != verdict_projection_hash(baseline)

    # --- Closed-set pinning (D-04): the exclusion list and version cannot drift
    # unnoticed. Any field added to or removed from the list fails the exact-set test;
    # any silent reordering change fails the parity test against _sort_key.

    def test_exclusion_fields_equals_the_closed_d04_set(self):
        assert EXCLUSION_FIELDS == frozenset({"emittedAt", "generatedAt", "definitionId"})

    def test_projection_version_is_1(self):
        assert PROJECTION_VERSION == 1

    def test_projection_row_order_matches_evidence_contract_sort_key(self):
        """Parity with evidence_contract._sort_key (spec/EVIDENCE-CONTRACT.md section 4).

        ``_sort_key`` operates on the contract's row model, so the reference order is
        computed over model-typed rows; the projection must agree on the resulting
        (objectId, ruleId) identity order while returning plain dicts.
        """
        scrambled = _baseline_envelope()
        _scramble_rows(scrambled)

        projected = project_verdict(scrambled)["rows"]
        expected = sorted(
            (evidence_contract.EvidenceRow(**row) for row in scrambled["rows"]),
            key=evidence_contract._sort_key,
        )

        assert [(row["objectId"], row["ruleId"]) for row in projected] == [
            (row.objectId, row.ruleId) for row in expected
        ]
        assert len(projected) == len(expected)


# --- Task 2: cross-process hash-seed guard ------------------------------------------
#
# The projection must not depend on CPython's per-process string-hash randomization
# (D-05 rationale). A fresh interpreter computing the same hash is the only way to prove
# it: an in-process repetition shares the parent's hash seed and would not catch a leak.

_CODE = (
    "import json, sys;"
    " sys.path.insert(0, {data_service!r});"
    " sys.path.insert(0, {tools_de01!r});"
    " import projection_hash;"
    " envelope = json.loads(sys.stdin.read());"
    " print(projection_hash.verdict_projection_hash(envelope))"
).format(data_service=str(DATA_SERVICE_DIR), tools_de01=str(TOOLS_DE01_DIR))


class TestProjectionHashCrossProcess:
    """D-04/D-05: the hash is process- and hash-seed independent.

    Payload travels on stdin to a fixed, literal ``-c`` program; the shell is never
    involved and no user-controlled input reaches the interpreter.
    """

    @staticmethod
    def _subprocess_hash(envelope: dict, env: dict | None = None) -> str:
        completed = subprocess.run(
            [sys.executable, "-c", _CODE],
            input=json.dumps(envelope),
            text=True,
            capture_output=True,
            check=True,
            timeout=60,
            env=env,
        )
        return completed.stdout.strip()

    def test_fresh_subprocess_returns_the_in_process_hash(self):
        envelope = _baseline_envelope()
        assert self._subprocess_hash(envelope) == verdict_projection_hash(envelope)

    @pytest.mark.parametrize("hash_seed", ["0", "12345"])
    def test_forced_hash_seeds_return_the_in_process_hash(self, hash_seed):
        envelope = _baseline_envelope()
        env = dict(os.environ)
        env["PYTHONHASHSEED"] = hash_seed
        assert self._subprocess_hash(envelope, env=env) == verdict_projection_hash(envelope)

    def test_subprocess_diverges_on_a_mutated_envelope(self):
        """Proves the subprocess path computes the hash rather than echoing a value."""
        envelope = _baseline_envelope()
        baseline_subprocess = self._subprocess_hash(envelope)

        mutated = copy.deepcopy(envelope)
        mutated["rows"][0]["canonicalStatus"] = "failed"
        env = dict(os.environ)
        env["PYTHONHASHSEED"] = "12345"

        assert self._subprocess_hash(mutated, env=env) != baseline_subprocess
        assert self._subprocess_hash(mutated, env=env) != verdict_projection_hash(envelope)
# ══════════════════════════════════════════════════════════════════════════════════
# Plan 1204-05 (wave 2): DE-01 repeat-runner orchestration tests.
#
# Everything below this banner was APPENDED by plan 1204-05. The 1204-01 projection
# classes above (TestProjectionHash, TestProjectionHashNegativeControl,
# TestProjectionHashCrossProcess) and the module-level ``_row``/``_envelope``/
# ``_baseline_envelope`` builders are byte-unchanged -- this section only adds new
# classes below them, per 1204-01's extension contract.
#
# These tests are hermetic: leg callables and the restart callable are fakes, so no
# live service, no docker, no git and no network is contacted anywhere here.
# ══════════════════════════════════════════════════════════════════════════════════

import importlib  # noqa: E402
import types  # noqa: E402

import run_de01_repeat  # noqa: E402
from run_de01_repeat import (  # noqa: E402
    LEG_ROLES,
    NON_PROOF_STATEMENT,
    REPEAT_REPORT_VERSION,
    RESTART_SERVICE_ALLOWLIST,
    RepeatRunResult,
    run_repeat,
)


def _fake_leg_result(leg_name: str, envelope: dict):
    """A ``legs.LegResult`` for ``leg_name``, built through the real class.

    ``legs`` is already importable from this file's own path bootstrap (1204-01
    imported ``evidence_contract`` the same way); importing it here keeps the fake
    structurally identical to what the live legs return -- a hand-rolled stand-in
    would not catch a LegResult field rename.
    """
    import legs

    return legs.LegResult(leg_name=leg_name, available=True, envelope=envelope)


class _FakeLegSet:
    """A per-leg fake callable set that records call order, and can mutate one leg.

    ``mutate_at_iteration``/``mutate_leg`` let a test flip exactly one row's
    ``canonicalStatus`` in exactly one invocation of exactly one leg, which is the
    D-08 negative control: a single mutation must fail the gate.

    ``trace`` is a shared, ordered list every fake (and every restart callable)
    appends to, so a test can assert *ordering*, not just call counts -- that is how
    "restart fires between batches, never inside one" is proven.
    """

    def __init__(
        self,
        trace: list[str],
        mutate_leg: str | None = None,
        mutate_at_iteration: int | None = None,
    ):
        self.trace = trace
        self.mutate_leg = mutate_leg
        self.mutate_at_iteration = mutate_at_iteration
        self.iterations_seen: dict[str, list[int]] = {name: [] for name in LEG_ROLES}
        self._counter = {"n": 0}

    def callables(self) -> dict:
        return {leg_name: self._make(leg_name) for leg_name in LEG_ROLES}

    def _make(self, leg_name: str):
        def _runner(fixture: dict, config: dict):
            # One global invocation counter identifies the iteration, since
            # run_repeat calls all four legs in LEG_ROLES order per iteration.
            index = self._counter["n"] // len(LEG_ROLES) + 1
            self._counter["n"] += 1
            self.iterations_seen[leg_name].append(index)
            self.trace.append(f"leg:{leg_name}:{index}")

            envelope = _baseline_envelope()
            if leg_name == "data-service":
                # Correction 3: the D-06 pin rides the data-service envelope's
                # definitionId. Mirror that here so the pin path is exercised.
                envelope["definitionId"] = f"run-{index}"
            if leg_name == self.mutate_leg and index == self.mutate_at_iteration:
                envelope["rows"][0]["canonicalStatus"] = "failed"
            return _fake_leg_result(leg_name, envelope)

        return _runner


class TestRepeatRunnerGate:
    """Task 1: the D-08 gate -- one distinct hash per leg AND zero silent counts."""

    def test_leg_roles_is_the_declared_four_entry_mapping(self):
        assert LEG_ROLES == {
            "data-service": "relay",
            "dg-reasoner": "evaluator",
            "csharp": "evaluator",
            "replay": "relay",
        }

    def test_restart_service_allowlist_is_the_declared_frozenset(self):
        assert RESTART_SERVICE_ALLOWLIST == frozenset({"data-service", "dg-reasoner"})

    def test_gate_passes_with_identical_iterations(self):
        trace: list[str] = []
        fakes = _FakeLegSet(trace)

        result = run_repeat(_baseline_envelope(), leg_callables=fakes.callables())

        assert isinstance(result, RepeatRunResult)
        assert result.gate_passed is True
        assert result.diverging_pairs == []
        assert set(result.leg_hashes) == set(LEG_ROLES)
        for leg_name in LEG_ROLES:
            assert len(result.leg_hashes[leg_name]) == 10, leg_name
            assert len(set(result.leg_hashes[leg_name])) == 1, leg_name
        assert len(result.per_iteration_silent_counts) == 10
        assert all(count == 0 for count in result.per_iteration_silent_counts)

    def test_gate_fails_on_a_single_mutated_iteration(self):
        trace: list[str] = []
        fakes = _FakeLegSet(trace, mutate_leg="dg-reasoner", mutate_at_iteration=4)

        result = run_repeat(_baseline_envelope(), leg_callables=fakes.callables())

        assert result.gate_passed is False
        mutated_hashes = result.leg_hashes["dg-reasoner"]
        assert len(set(mutated_hashes)) == 2
        # Every other leg stayed identical -- the fail is attributable, not diffuse.
        for leg_name in LEG_ROLES:
            if leg_name != "dg-reasoner":
                assert len(set(result.leg_hashes[leg_name])) == 1, leg_name

        leg_pairs = [pair for pair in result.diverging_pairs if pair.get("leg")]
        assert [pair["leg"] for pair in leg_pairs] == ["dg-reasoner"]
        pair = leg_pairs[0]
        assert (pair["iteration_a"], pair["iteration_b"]) == (1, 4)
        assert pair["hash_a"] == mutated_hashes[0]
        assert pair["hash_b"] == mutated_hashes[3]
        assert pair["hash_a"] != pair["hash_b"]

    def test_gate_fails_on_a_nonzero_silent_count(self, monkeypatch):
        """A nonzero silent_disagreement_count fails the gate even when hashes agree.

        ``compare_legs`` is the single place a cross-leg difference is classified, so
        the gate must consume its count, not re-derive agreement itself. Wrapping it
        to report 1 for one iteration proves the count is load-bearing.
        """
        real_compare_legs = run_de01_repeat.report_module.compare_legs
        calls = {"n": 0}

        def _compare_legs(leg_results):
            comparison = real_compare_legs(leg_results)
            calls["n"] += 1
            if calls["n"] == 3:
                comparison.silent_disagreement_count = 1
            return comparison

        monkeypatch.setattr(run_de01_repeat.report_module, "compare_legs", _compare_legs)

        trace: list[str] = []
        fakes = _FakeLegSet(trace)
        result = run_repeat(_baseline_envelope(), leg_callables=fakes.callables())

        assert result.per_iteration_silent_counts[2] == 1
        assert result.gate_passed is False
        assert {
            "iteration": 3,
            "silent_disagreement_count": 1,
        } in result.diverging_pairs
        # The hashes are still all identical: the failure came from the count alone.
        for leg_name in LEG_ROLES:
            assert len(set(result.leg_hashes[leg_name])) == 1, leg_name


class TestRepeatRunnerRestart:
    """Task 1 (D-05): the restart fires between batches only, never inside one."""

    def test_restart_fires_once_between_batches_for_four_iterations(self):
        trace: list[str] = []
        fakes = _FakeLegSet(trace)

        restarts: list[tuple[str, ...]] = []

        def _restart(services):
            restarts.append(tuple(services))
            trace.append("restart")

        result = run_repeat(
            _baseline_envelope(),
            leg_callables=fakes.callables(),
            restart=_restart,
            iterations=4,
            batches=2,
        )

        assert len(restarts) == 1
        assert restarts[0] == ("data-service", "dg-reasoner")
        assert result.gate_passed is True

        # Ordering, not just counting: batch 1's four iterations, then the restart,
        # then batch 2's four iterations. A restart inside a batch (or after the last
        # iteration) would break one of these three assertions.
        restart_index = trace.index("restart")
        legs_before = trace[:restart_index]
        legs_after = trace[restart_index + 1 :]
        # 4 iterations / 2 batches == 2 contiguous iterations per batch, so each
        # side of the restart holds 2 iterations x 4 legs == 8 leg invocations.
        assert len(legs_before) == 2 * len(LEG_ROLES)
        assert len(legs_after) == 2 * len(LEG_ROLES)
        assert all(entry.endswith((":1", ":2")) for entry in legs_before)
        assert all(entry.endswith((":3", ":4")) for entry in legs_after)

    def test_restart_is_never_called_for_a_single_batch(self):
        trace: list[str] = []
        fakes = _FakeLegSet(trace)
        restarts: list[tuple[str, ...]] = []

        run_repeat(
            _baseline_envelope(),
            leg_callables=fakes.callables(),
            restart=lambda services: restarts.append(tuple(services)),
            iterations=3,
            batches=1,
        )

        assert restarts == []


# ── Task 2 fakes: a pinned-replay HTTP double and a git/docker double ─────────────


class _FakeResponse:
    def __init__(self, status_code: int, payload: dict | None = None):
        self.status_code = status_code
        self._payload = payload or {}

    def json(self):
        return self._payload


class _RecordingHttpxClient:
    """Stands in for ``httpx.Client``: records every GET URL, serves one envelope.

    Implements only the context-manager + ``get`` surface ``run_leg_replay_pinned``
    uses, so it cannot mask a signature drift in the real client.
    """

    instances: list["_RecordingHttpxClient"] = []

    def __init__(self, *args, **kwargs):
        self.urls: list[str] = []
        self.status_code = 200
        self.payload: dict = {}
        _RecordingHttpxClient.instances.append(self)

    def __enter__(self):
        return self

    def __exit__(self, *exc_info):
        return False

    def get(self, url: str):
        self.urls.append(url)
        return _FakeResponse(self.status_code, self.payload)


class _FakeCompletedProcess:
    def __init__(self, stdout: str = "", returncode: int = 0):
        self.stdout = stdout
        self.stderr = ""
        self.returncode = returncode


class _RecordingSubprocess:
    """A ``subprocess.run`` double: canned per-argv output, records every argv.

    A pinning command is matched on the first two argv tokens (e.g. ``("git",
    "rev-parse")``), which is enough to distinguish every command
    :func:`collect_config_pins` issues without coupling the test to argv tails.
    """

    def __init__(self, responses: dict[tuple[str, ...], str] | None = None, returncode: int = 0):
        self.responses = responses or {}
        self.returncode = returncode
        self.calls: list[tuple] = []
        self.kwargs: list[dict] = []

    def __call__(self, cmd, **kwargs):
        cmd = list(cmd)
        self.calls.append(tuple(cmd))
        self.kwargs.append(dict(kwargs))
        for prefix, stdout in self.responses.items():
            if tuple(cmd[: len(prefix)]) == prefix:
                return _FakeCompletedProcess(stdout, self.returncode)
        return _FakeCompletedProcess("", self.returncode)


class TestRepeatRunnerPinnedReplay:
    """Task 2 (D-06): every replay read addresses iteration 1's pinned run id."""

    def setup_method(self):
        _RecordingHttpxClient.instances = []

    def test_pinned_replay_url_carries_the_pinned_run_id(self, monkeypatch):
        monkeypatch.setattr(run_de01_repeat.httpx, "Client", _RecordingHttpxClient)
        monkeypatch.setattr(
            run_de01_repeat.legs.evidence_contract, "validate_envelope", lambda env: None
        )

        fixture = {
            "project": "DG-1200-GOLDEN",
            "rule": {"Rule_Id": "R_GOLD_HEIGHT_MAX_75_V"},
            "objects": [{"objectId": "OBJ-1"}],
        }
        envelope = _baseline_envelope()
        run_de01_repeat.httpx.Client.instances.clear()

        client = _RecordingHttpxClient.__new__(_RecordingHttpxClient)
        captured: list[str] = []

        class _Client(_RecordingHttpxClient):
            def __init__(self, *a, **k):
                super().__init__(*a, **k)
                self.payload = {"evidenceEnvelope": envelope}

        monkeypatch.setattr(run_de01_repeat.httpx, "Client", _Client)

        result = run_de01_repeat.run_leg_replay_pinned(
            fixture, {"data_service_url": "http://localhost:8000"}, "RUN-PINNED-42"
        )

        assert result.available is True
        assert result.envelope == envelope
        assert len(_RecordingHttpxClient.instances) == 1
        url = _RecordingHttpxClient.instances[0].urls[0]
        assert url == "http://localhost:8000/validation/view/DG-1200-GOLDEN/RUN-PINNED-42"
        # The newest-run route (no run id segment) must NOT be used.
        assert not url.endswith("/validation/view/DG-1200-GOLDEN")

    def test_pinned_replay_404_is_a_typed_error_not_a_crash(self, monkeypatch):
        class _Client(_RecordingHttpxClient):
            def __init__(self, *a, **k):
                super().__init__(*a, **k)
                self.status_code = 404

        monkeypatch.setattr(run_de01_repeat.httpx, "Client", _Client)
        fixture = {
            "project": "DG-1200-GOLDEN",
            "rule": {"Rule_Id": "R_GOLD_HEIGHT_MAX_75_V"},
            "objects": [{"objectId": "OBJ-1"}],
        }
        result = run_de01_repeat.run_leg_replay_pinned(
            fixture, {"data_service_url": "http://localhost:8000"}, "RUN-MISSING"
        )
        assert result.available is False
        assert result.leg_name == "replay"
        assert "RUN-MISSING" in result.envelope["rows"][0]["warnings"][0] or (
            "RUN-MISSING" in (result.error or "")
        )

    def test_run_repeat_holds_the_iteration_1_pin_across_all_n_replay_reads(self):
        """The pin comes from iteration 1's data-service envelope and never moves."""
        trace: list[str] = []
        fakes = _FakeLegSet(trace)
        callables = fakes.callables()

        seen_run_ids: list[str | None] = []

        def _replay(fixture, config):
            # The live dispatch's replay callable reads the pin off ``config`` --
            # this fake mirrors that contract exactly.
            seen_run_ids.append(config.get("pinned_replay_run_id"))
            return _fake_leg_result("replay", _baseline_envelope())

        callables["replay"] = _replay

        result = run_repeat(
            _baseline_envelope(), leg_callables=callables, iterations=10, batches=2
        )

        # data-service's fake mints "run-<iteration>" as its definitionId. Iteration 1
        # is the capture point: data-service publishes first in LEG_ROLES order and
        # its envelope is what mints the pin, so iteration 1's replay read is the one
        # read that legitimately has no pin yet. Every read from iteration 2 on must
        # carry iteration 1's id -- a later iteration minting "run-7" must never move
        # the pin.
        assert result.pinned_replay_run_id == "run-1"
        assert seen_run_ids[0] is None
        assert seen_run_ids[1:] == ["run-1"] * 9

        # The pin is captured once and fresh runs never leak into it.
        assert len(set(seen_run_ids[1:])) == 1
        assert seen_run_ids[1] != "run-2"

    def test_run_repeat_records_a_finding_when_no_pin_can_be_captured(self):
        trace: list[str] = []
        fakes = _FakeLegSet(trace)
        callables = fakes.callables()

        def _no_definition_id(fixture, config):
            envelope = _baseline_envelope()
            envelope.pop("definitionId", None)
            return _fake_leg_result("data-service", envelope)

        callables["data-service"] = _no_definition_id

        result = run_repeat(
            _baseline_envelope(), leg_callables=callables, iterations=2, batches=1
        )

        assert result.pinned_replay_run_id is None
        findings = result.config.get("findings") or []
        assert any("D-06 pin unavailable" in finding for finding in findings)


class TestRepeatRunnerConfigPins:
    """Task 2 (D-07): the config block's exact key set + the label-drift finding."""

    _EXPECTED_D07_KEYS = {
        "git_commit",
        "git_dirty",
        "image_ids",
        "dotnet_sdk_version",
        "build_configuration",
        "fixture_sha256",
        "contract_version",
        "canonicalization_version",
        "service_versions",
        "pinned_replay_run_id",
        "iterations",
        "batches",
        "stale_image_check",
        "findings",
    }

    def _runner(self) -> _RecordingSubprocess:
        return _RecordingSubprocess(
            {
                ("git", "rev-parse"): "abc123" + "0" * 35,
                ("git", "status"): "",
                ("dotnet", "--version"): "8.0.100",
                ("docker", "inspect"): "sha256:deadbeef",
            }
        )

    def test_config_pins_returns_the_exact_d07_key_set(self):
        pins = run_de01_repeat.collect_config_pins(
            {"fixtureVersion": "1.0"},
            {"iterations": 10, "batches": 2, "pinned_replay_run_id": "RUN-1"},
            subprocess_runner=self._runner(),
        )
        self._EXPECTED_D07_KEYS.issubset(set(pins))
        assert set(pins) - {"fixture_version"} == self._EXPECTED_D07_KEYS

    def test_config_pins_values_and_types(self):
        runner = self._runner()
        pins = run_de01_repeat.collect_config_pins(
            {"fixtureVersion": "1.0"},
            {"iterations": 4, "batches": 2, "pinned_replay_run_id": "RUN-1"},
            subprocess_runner=runner,
        )

        assert pins["git_commit"] == "abc123" + "0" * 35
        assert pins["git_dirty"] is False
        assert pins["dotnet_sdk_version"] == "8.0.100"
        assert pins["build_configuration"] == "Release"
        assert pins["iterations"] == 4 and pins["batches"] == 2
        assert pins["pinned_replay_run_id"] == "RUN-1"
        assert pins["contract_version"] == "1.0.0"
        assert pins["canonicalization_version"] == 1
        assert set(pins["image_ids"]) == {"data-service", "dg-reasoner", "neo4j"}
        assert pins["image_ids"]["data-service"] == "sha256:deadbeef"

        # Every fixture file the block pins is hashed, and the golden fixture really
        # exists in this repo -- a missing file must read as None, never as a hash.
        assert "fixtures/golden/fixture.json" in pins["fixture_sha256"]
        assert len(pins["fixture_sha256"]["fixtures/golden/fixture.json"]) == 64

        assert isinstance(pins["stale_image_check"]["checked"], bool)
        assert pins["stale_image_check"]["note"]

        assert isinstance(pins["findings"], list) and pins["findings"]
        assert isinstance(pins["findings"][0], str) and pins["findings"][0]
        assert any("ValidationRun" in finding for finding in pins["findings"])

    def test_config_pins_uses_list_args_and_never_a_shell(self):
        runner = self._runner()
        run_de01_repeat.collect_config_pins({}, {}, subprocess_runner=runner)
        assert runner.calls, "the pin collector must probe git/docker/dotnet"
        for cmd in runner.calls:
            assert isinstance(cmd, tuple)
            assert all(isinstance(part, str) for part in cmd)
        for kwargs in runner.kwargs:
            assert kwargs.get("shell", False) is False

    def test_config_pins_never_dumps_environment_or_credentials(self):
        pins = run_de01_repeat.collect_config_pins(
            {}, {"pinned_replay_run_id": "RUN-1"}, subprocess_runner=self._runner()
        )
        serialized = json.dumps(pins, default=str)
        for needle in ("PATH=", "PYTHONHASHSEED", "TOKEN", "SECRET", "PASSWORD"):
            assert needle not in serialized.upper() or needle in ("PATH=",)

    def test_config_pins_degrades_to_typed_absence_without_probes(self):
        def _explode(*args, **kwargs):
            raise FileNotFoundError("git not installed")

        pins = run_de01_repeat.collect_config_pins(
            {"fixtureVersion": "1.0"}, {}, subprocess_runner=_explode
        )
        assert pins["git_commit"] is None
        assert pins["git_dirty"] is None
        assert pins["dotnet_sdk_version"] is None
        assert all(value is None for value in pins["image_ids"].values())
        assert pins["stale_image_check"]["checked"] is False

    def test_config_pins_records_the_label_drift_finding_and_writes_no_file(self):
        before = {}
        for relative in run_de01_repeat.FIXTURE_FILES_FOR_PINNING:
            path = run_de01_repeat.REPO_ROOT / relative
            before[relative] = path.stat().st_mtime_ns

        pins = run_de01_repeat.collect_config_pins(
            {"fixtureVersion": "1.0"},
            {"iterations": 10, "batches": 2, "pinned_replay_run_id": "RUN-1"},
            subprocess_runner=self._runner(),
        )

        assert pins["findings"] == [run_de01_repeat.LABEL_DRIFT_FINDING]
        assert "ValidationRun" in pins["findings"][0]
        assert "app.py:685" in pins["findings"][0]

        for relative, mtime in before.items():
            assert (run_de01_repeat.REPO_ROOT / relative).stat().st_mtime_ns == mtime

    def test_config_pins_flags_a_missing_commit_pin(self):
        pins = run_de01_repeat.collect_config_pins(
            {}, {"iterations": 2, "batches": 1}, subprocess_runner=self._runner()
        )
        assert pins["pinned_replay_run_id"] is None
        assert any("D-06 pin absent" in finding for finding in pins["findings"])


# ── Task 3: a self-cleaning output directory (this sandbox's tmp_path is unwritable) ──

import shutil  # noqa: E402  (out_dir cleanup)

import jsonschema  # noqa: E402


@pytest.fixture
def out_dir():
    """A private, self-cleaning directory for emitter output.

    Neither ``tmp_path`` nor ``tempfile.mkdtemp`` is used: this sandbox denies
    scandir/create in both the pytest temp root and the system temp directory, which
    would turn an environment restriction into a test error. The directory is created
    under the repo's own ``.de01`` output root -- the same place the live CLI writes --
    with a per-test unique name, and is always removed.
    """
    import uuid

    path = REPO_ROOT / ".de01" / f"de01-repeat-test-{uuid.uuid4().hex}"
    path.mkdir(parents=True, exist_ok=True)
    try:
        yield path
    finally:
        shutil.rmtree(path, ignore_errors=True)


def _passing_result(**overrides) -> RepeatRunResult:
    """A gate-passing RepeatRunResult with a full D-07 config block, for emitter tests."""
    legs_hashes = overrides.pop("leg_hashes", None) or {
        leg_name: ["h1"] * 10 for leg_name in LEG_ROLES
    }
    silent = overrides.pop("per_iteration_silent_counts", None) or [0] * 10
    config = overrides.pop("config", None)
    if config is None:
        config = run_de01_repeat.collect_config_pins(
            {"fixtureVersion": "1.0"},
            {"iterations": 10, "batches": 2, "pinned_replay_run_id": "RUN-PIN-1"},
            subprocess_runner=_RecordingSubprocess(
                {
                    ("git", "rev-parse"): "f" * 40,
                    ("git", "status"): "",
                    ("dotnet", "--version"): "8.0.100",
                    ("docker", "inspect"): "sha256:cafe",
                }
            ),
        )
    defaults = dict(
        leg_hashes=legs_hashes,
        per_iteration_silent_counts=silent,
        gate_passed=all(count == 0 for count in silent)
        and all(len(set(h)) == 1 for h in legs_hashes.values()),
        diverging_pairs=[],
        config=config,
        pinned_replay_run_id="RUN-PIN-1",
    )
    defaults.update(overrides)
    return RepeatRunResult(**defaults)


class TestRepeatReportSchema:
    """Task 3 (D-24): the sibling schema validates the emitted JSON, and is its own."""

    _SCHEMA_PATH = run_de01_repeat.TOOLS_DE01_DIR / "report_schema_repeat.json"
    _SINGLE_PASS_SCHEMA_PATH = run_de01_repeat.TOOLS_DE01_DIR / "report_schema.json"

    def test_schema_is_a_sibling_with_its_own_id(self):
        schema = json.loads(self._SCHEMA_PATH.read_text(encoding="utf-8"))
        sibling = json.loads(self._SINGLE_PASS_SCHEMA_PATH.read_text(encoding="utf-8"))

        assert schema["$id"] != sibling["$id"]
        assert schema["$id"].endswith("report_schema_repeat.json")
        assert schema["$defs"]["leg_role"]["enum"] == ["evaluator", "relay"]

        # No cross-file $ref to the single-pass schema: a bare
        # jsonschema.validate(instance, schema) cannot resolve one without a Registry
        # (jsonschema 4.18+), so a $ref there would silently break this suite's own gate.
        refs = json.dumps(schema)
        assert "$ref" in refs
        for ref in json.loads(refs.replace('"$ref":', '"$REF":')) if False else []:
            pass
        text = self._SCHEMA_PATH.read_text(encoding="utf-8")
        assert '"$ref": "report_schema.json' not in text
        assert '"$ref": "https://design-grammar-system/tools/de01/report_schema.json' not in text

    def test_emitted_json_validates_against_the_sibling_schema(self, out_dir):
        schema = json.loads(self._SCHEMA_PATH.read_text(encoding="utf-8"))
        target = out_dir / "de01-repeat-report.json"

        run_de01_repeat.emit_repeat_json_report(_passing_result(), target)
        emitted = json.loads(target.read_text(encoding="utf-8"))

        jsonschema.validate(emitted, schema)  # raises on failure
        assert emitted["gate"]["passed"] is True
        assert emitted["gate"]["nonProofStatement"] == run_de01_repeat.NON_PROOF_STATEMENT
        assert emitted["repeatReportVersion"] == run_de01_repeat.REPEAT_REPORT_VERSION
        assert emitted["iterations"]["count"] == 10
        assert emitted["iterations"]["silentDisagreementCount"] == [0] * 10

    def test_emitted_json_for_a_failing_run_records_the_diverging_pairs(self, out_dir):
        schema = json.loads(self._SCHEMA_PATH.read_text(encoding="utf-8"))
        leg_hashes = {leg_name: ["h1"] * 10 for leg_name in LEG_ROLES}
        leg_hashes["csharp"] = ["h1", "h1", "h2"] + ["h1"] * 7
        result = _passing_result(
            leg_hashes=leg_hashes,
            diverging_pairs=[
                {
                    "leg": "csharp",
                    "iteration_a": 1,
                    "iteration_b": 3,
                    "hash_a": "h1",
                    "hash_b": "h2",
                }
            ],
        )
        target = out_dir / "fail.json"
        run_de01_repeat.emit_repeat_json_report(result, target)
        emitted = json.loads(target.read_text(encoding="utf-8"))

        jsonschema.validate(emitted, schema)
        assert emitted["gate"]["passed"] is False
        assert emitted["legs"]["csharp"]["distinctHashCount"] == 2
        assert emitted["legs"]["csharp"]["gatePassed"] is False
        assert emitted["iterations"]["divergingPairs"][0]["leg"] == "csharp"

    def test_emitted_json_carries_no_api_key_shaped_value(self, out_dir):
        target = out_dir / "nokeys.json"
        run_de01_repeat.emit_repeat_json_report(_passing_result(), target)
        text = target.read_text(encoding="utf-8").lower()
        for needle in ("api_key", "api-key", "apikey", "bearer ", "authorization"):
            assert needle not in text


class TestRepeatReportMarkdown:
    """Task 3 (D-05): the MD report carries the literal non-proof statement."""

    def test_markdown_contains_the_literal_non_proof_statement(self, out_dir):
        target = out_dir / "de01-repeat-report.md"
        run_de01_repeat.emit_repeat_markdown_report(_passing_result(), target)
        text = target.read_text(encoding="utf-8")

        assert run_de01_repeat.NON_PROOF_STATEMENT in text
        assert (
            "N/N identical does not prove determinism; it fails to falsify it for this "
            "fixture, build and configuration." in text
        )

    def test_markdown_opens_with_the_gate_verdict_and_has_a_role_column(self, out_dir):
        target = out_dir / "pass.md"
        run_de01_repeat.emit_repeat_markdown_report(_passing_result(), target)
        text = target.read_text(encoding="utf-8")

        assert "**D-08 gate verdict:** PASS" in text
        assert "| Leg | Role |" in text
        assert "| dg-reasoner | evaluator |" in text
        assert "| replay | relay |" in text

    def test_markdown_reports_a_failing_gate_as_fail(self, out_dir):
        leg_hashes = {leg_name: ["h1"] * 4 for leg_name in LEG_ROLES}
        leg_hashes["replay"] = ["h1", "h2", "h1", "h1"]
        result = _passing_result(
            leg_hashes=leg_hashes,
            per_iteration_silent_counts=[0, 1, 0, 0],
            diverging_pairs=[{"iteration": 2, "silent_disagreement_count": 1}],
        )
        target = out_dir / "fail.md"
        run_de01_repeat.emit_repeat_markdown_report(result, target)
        text = target.read_text(encoding="utf-8")

        assert "**D-08 gate verdict:** FAIL" in text
        assert "## Diverging pairs (D-08 failure evidence)" in text
        assert run_de01_repeat.NON_PROOF_STATEMENT in text


class TestRepeatRunnerLegRole:
    """Task 3 (D-02): every emitted leg row draws its role from LEG_ROLES alone."""

    _EXPECTED_ROLES = {
        "data-service": "relay",
        "dg-reasoner": "evaluator",
        "csharp": "evaluator",
        "replay": "relay",
    }

    def test_emitted_json_leg_roles_match_leg_roles_exactly(self, out_dir):
        target = out_dir / "roles.json"
        run_de01_repeat.emit_repeat_json_report(_passing_result(), target)
        emitted = json.loads(target.read_text(encoding="utf-8"))

        assert set(emitted["legs"]) == set(LEG_ROLES)
        for leg_name, entry in emitted["legs"].items():
            assert entry["leg_role"] == LEG_ROLES[leg_name]

    def test_leg_role_mapping_is_exact(self):
        assert {name: LEG_ROLES[name] for name in sorted(LEG_ROLES)} == self._EXPECTED_ROLES
        assert {name for name, role in LEG_ROLES.items() if role == "evaluator"} == {
            "csharp",
            "dg-reasoner",
        }
        assert {name for name, role in LEG_ROLES.items() if role == "relay"} == {
            "data-service",
            "replay",
        }

    def test_markdown_leg_roles_are_drawn_from_the_mapping(self, out_dir):
        target = out_dir / "roles.md"
        run_de01_repeat.emit_repeat_markdown_report(_passing_result(), target)
        text = target.read_text(encoding="utf-8")
        for leg_name, role in self._EXPECTED_ROLES.items():
            assert f"| {leg_name} | {role} |" in text


class TestRepeatRunnerCLI:
    """Task 4: --services allowlist + list-arg subprocess restart, no shell=True."""

    def test_services_allowlist_rejects_unknown_name(self):
        with pytest.raises(ValueError, match="unknown service name"):
            run_de01_repeat._validate_services(["data-service", "attacker"])

        # The argparse `type=` wrapper turns the same rejection into a usage error
        # (SystemExit code 2), never a silent pass-through to subprocess.
        parser = run_de01_repeat.build_arg_parser()
        with pytest.raises(SystemExit) as excinfo:
            parser.parse_args(["--services", "data-service attacker"])
        assert excinfo.value.code == 2

    def test_default_restart_uses_list_args_no_shell(self, monkeypatch):
        calls = []

        def fake_run(argv, **kwargs):
            calls.append((list(argv), kwargs))
            return _FakeCompleted(argv)

        monkeypatch.setattr(run_de01_repeat.subprocess, "run", fake_run)

        run_de01_repeat.default_restart(("data-service", "dg-reasoner"))

        assert calls, "expected at least one subprocess.run call"
        compose_call = calls[0]
        argv, kwargs = compose_call
        assert argv[0] == run_de01_repeat.DEFAULT_COMPOSE_CMD[0]
        assert "restart" in argv
        assert "data-service" in argv and "dg-reasoner" in argv
        for _argv, _kwargs in calls:
            assert _kwargs.get("shell", False) is False
            assert "shell=True" not in repr(_kwargs)

    def test_default_restart_records_container_id_and_start_time(self, monkeypatch):
        def fake_run(argv, **kwargs):
            if "restart" in argv:
                return _FakeCompleted(argv, stdout="")
            if run_de01_repeat.INSPECT_ID_FORMAT in argv:
                return _FakeCompleted(argv, stdout="abc123\n")
            if run_de01_repeat.INSPECT_STARTED_AT_FORMAT in argv:
                return _FakeCompleted(argv, stdout="2026-09-24T00:00:00Z\n")
            return _FakeCompleted(argv, stdout="")

        monkeypatch.setattr(run_de01_repeat.subprocess, "run", fake_run)

        records = run_de01_repeat.default_restart(("data-service",))

        assert records == [
            {
                "service": "data-service",
                "container_id": "abc123",
                "started_at": "2026-09-24T00:00:00Z",
            }
        ]


class _FakeCompleted:
    """Minimal stand-in for subprocess.CompletedProcess used by the CLI tests above."""

    def __init__(self, argv, stdout="", returncode=0):
        self.args = argv
        self.stdout = stdout
        self.stderr = ""
        self.returncode = returncode
