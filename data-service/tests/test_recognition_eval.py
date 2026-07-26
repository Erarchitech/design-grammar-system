"""Driver tests for the recognition eval harness (Phase 35-13,
35-AI-SPEC.md 5 "Evaluation Strategy").

Extends `test_cg_recognition.py`'s sys.path/no-network boilerplate rather
than duplicating it -- see that file's own docstring for the
`_FakeAdapterForRetry` precedent this harness scales up into cassette-based
record/replay.

Built incrementally across 35-13-PLAN.md's tasks:
- `TestCassette` (Task 1): `recognition_eval.cassette`'s record/replay/miss
  behaviour.
- `TestArms` (Task 2): `recognition_eval.arms`'s A0-A5 registry and artifact
  resolution.
- The conjunctive SC1 gate, the A0 validity check, and the parametrized
  (corpus x arm) driver (Task 3).
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, os.path.dirname(__file__))

os.environ.setdefault("LLM_MASTER_SECRET", "test-master-secret")

import pytest  # noqa: E402

import cg_recognition  # noqa: E402
import cg_topology  # noqa: E402
from llm_gateway import GenerateRequest, GenerateResponse  # noqa: E402

from recognition_eval import arms as arms_module  # noqa: E402
from recognition_eval import cassette as cassette_module  # noqa: E402
from recognition_eval import corpus as corpus_module  # noqa: E402
from recognition_eval import live_sweep as live_sweep_module  # noqa: E402
from recognition_eval import report as report_module  # noqa: E402
from recognition_eval import scoring as scoring_module  # noqa: E402


class _FakeRealAdapter:
    """Stand-in for a real llm_gateway adapter, wrapped by `CassetteAdapter`
    in 'record'/'live' mode tests. Mirrors test_cg_recognition.py's
    `_FakeAdapterForRetry` precedent, retargeted at cassette round-trip
    testing rather than the retry loop."""

    def __init__(self, responses: "list[GenerateResponse]"):
        self._responses = list(responses)
        self.call_count = 0

    def generate(self, req, api_key, options=None):
        self.call_count += 1
        return self._responses.pop(0)


# ── TestCassette (Task 1) ──


class TestCassette:
    _KEY_KWARGS = dict(
        provider="anthropic",
        model="claude-sonnet-5",
        prompt_version="r35.4",
        system="you are a recognizer",
        user_prompt="classify these nodes",
        temperature=0.0,
        negotiated_mode="none",
        max_tokens=2048,
    )

    @pytest.mark.parametrize(
        "field,new_value",
        [
            ("provider", "openai"),
            ("model", "gpt-4o"),
            ("prompt_version", "r35.5"),
            ("system", "a different system prompt"),
            ("user_prompt", "a different user prompt"),
            ("temperature", 0.5),
            ("negotiated_mode", "json_schema_strict"),
            ("max_tokens", 4096),
        ],
    )
    def test_cassette_key_changes_when_any_single_input_flips(self, field, new_value):
        base_key = cassette_module.cassette_key(**self._KEY_KWARGS)
        flipped = dict(self._KEY_KWARGS)
        flipped[field] = new_value
        flipped_key = cassette_module.cassette_key(**flipped)
        assert flipped_key != base_key, f"changing {field!r} did not change the cassette key"

    def test_replay_miss_raises_with_key_and_refresh_command(self, tmp_path, monkeypatch):
        monkeypatch.setattr(cassette_module, "_FIXTURES_ROOT", tmp_path)
        adapter = cassette_module.CassetteAdapter(
            "A0", None, negotiated_mode="none", prompt_version="r35.4",
            ip_class="own", mode="replay",
        )
        req = GenerateRequest(prompt="hello", system="sys", model="m", provider="p")

        with pytest.raises(cassette_module.CassetteMissError) as excinfo:
            adapter.generate(req, "key")

        message = str(excinfo.value)
        assert "RECOGNITION_EVAL_MODE=record" in message
        expected_key = cassette_module.cassette_key(
            provider="p", model="m", prompt_version="r35.4", system="sys",
            user_prompt="hello", temperature=None, negotiated_mode="none", max_tokens=None,
        )
        assert expected_key in message

    def test_replay_miss_does_not_call_wrapped_adapter(self, tmp_path, monkeypatch):
        monkeypatch.setattr(cassette_module, "_FIXTURES_ROOT", tmp_path)
        fake = _FakeRealAdapter([])
        adapter = cassette_module.CassetteAdapter(
            "A0", fake, negotiated_mode="none", prompt_version="r35.4",
            ip_class="own", mode="replay",
        )
        req = GenerateRequest(prompt="hello", system="sys", model="m", provider="p")

        with pytest.raises(cassette_module.CassetteMissError):
            adapter.generate(req, "key")

        assert fake.call_count == 0

    def test_recorded_cassette_round_trips_truncated_finish_reason_usage(self, tmp_path, monkeypatch):
        monkeypatch.setattr(cassette_module, "_FIXTURES_ROOT", tmp_path)
        real_response = GenerateResponse(
            text='{"proposals": []}',
            provider="anthropic",
            model="claude-sonnet-5",
            usage={"prompt_tokens": 10, "completion_tokens": 5, "total_tokens": 15},
            truncated=True,
            finish_reason="max_tokens",
        )
        fake = _FakeRealAdapter([real_response])
        recorder = cassette_module.CassetteAdapter(
            "A0", fake, negotiated_mode="none", prompt_version="r35.4",
            ip_class="own", mode="record",
        )
        req = GenerateRequest(prompt="hello", system="sys", model="claude-sonnet-5", provider="anthropic")

        recorded = recorder.generate(req, "key")
        assert recorded.truncated is True
        assert fake.call_count == 1

        replayer = cassette_module.CassetteAdapter(
            "A0", None, negotiated_mode="none", prompt_version="r35.4",
            ip_class="own", mode="replay",
        )
        replayed = replayer.generate(req, "key")
        assert replayed.truncated is True
        assert replayed.finish_reason == "max_tokens"
        assert replayed.usage == real_response.usage
        assert replayed.text == real_response.text

    def test_promptbody_stored_only_for_ip_class_own(self, tmp_path, monkeypatch):
        monkeypatch.setattr(cassette_module, "_FIXTURES_ROOT", tmp_path)
        response = GenerateResponse(text="{}", provider="p", model="m", usage={})

        own_req = GenerateRequest(prompt="hello-own", system="sys", model="m", provider="p")
        own_adapter = cassette_module.CassetteAdapter(
            "A0", _FakeRealAdapter([response]), negotiated_mode="none",
            prompt_version="r1", ip_class="own", mode="record",
        )
        own_adapter.generate(own_req, "key")
        own_key = cassette_module.cassette_key(
            provider="p", model="m", prompt_version="r1", system="sys",
            user_prompt="hello-own", temperature=None, negotiated_mode="none", max_tokens=None,
        )
        own_payload = json.loads((tmp_path / "A0" / f"{own_key}.json").read_text())
        assert "promptBody" in own_payload

        other_req = GenerateRequest(prompt="hello-other", system="sys", model="m", provider="p")
        other_adapter = cassette_module.CassetteAdapter(
            "A0", _FakeRealAdapter([response]), negotiated_mode="none",
            prompt_version="r1", ip_class="third_party", mode="record",
        )
        other_adapter.generate(other_req, "key")
        other_key = cassette_module.cassette_key(
            provider="p", model="m", prompt_version="r1", system="sys",
            user_prompt="hello-other", temperature=None, negotiated_mode="none", max_tokens=None,
        )
        other_payload = json.loads((tmp_path / "A0" / f"{other_key}.json").read_text())
        assert "promptBody" not in other_payload

    def test_generate_signature_matches_llm_adapter(self):
        import inspect

        sig = inspect.signature(cassette_module.CassetteAdapter.generate)
        assert list(sig.parameters) == ["self", "req", "api_key", "options"]

    def test_unknown_mode_rejected_at_construction(self):
        with pytest.raises(ValueError):
            cassette_module.CassetteAdapter(
                "A0", None, negotiated_mode="none", prompt_version="r1",
                ip_class="own", mode="bogus",
            )


# ── TestArms (Task 2) ──


def _minimal_cg_context() -> dict:
    """A tiny hand-built cgContextJson v1 shape -- one tagged procedure
    member, two untagged nodes -- just enough for `run_arm` to exercise
    Tier-0-bypass + Tier-1 merge without depending on a real corpus fixture."""
    return {
        "nodes": [
            {"instanceId": "n1", "componentGuid": "g1", "name": "Param", "nickname": "ParSplitAt"},
            {"instanceId": "n3", "componentGuid": "g3", "name": "Panel", "nickname": "loose panel"},
            {"instanceId": "n4", "componentGuid": "g4", "name": "Line SDL", "nickname": "TopChord"},
        ],
        "algorithms": [
            {
                "index": 1,
                "name": "1_ALGORITHM",
                "procedures": [
                    {
                        "id": "cg:1:proc:11",
                        "index": 11,
                        "name": "2D Truss Configuration",
                        "source": "tagged",
                        "memberIds": ["n1"],
                        "patterns": [],
                        "parameters": [],
                        "interfaces": [],
                    }
                ],
            }
        ],
        "untagged": {
            "nodeIds": ["n3", "n4"],
            "groups": [
                {"nickname": "loose panel group", "memberIds": ["n3"]},
                {"nickname": "wired thing group", "memberIds": ["n4"]},
            ],
        },
        "wires": [
            {"fromNode": "n1", "fromParam": "p_out", "toNode": "n4", "toParam": "p_in"},
        ],
    }


class TestArms:
    def test_arms_registry_contains_exact_ids(self):
        assert set(arms_module.ARMS.keys()) == {"A0", "A0f", "A1", "A2", "A3", "A4", "A5"}

    def test_a0_is_the_negative_control_configuration(self):
        a0 = arms_module.ARMS["A0"]
        assert a0.few_shot_source == "as_shipped"
        assert a0.system_prompt is False
        assert a0.tier0 is False
        assert a0.model == "deepseek-chat"

    def test_a3_is_the_shipping_configuration(self):
        a3 = arms_module.ARMS["A3"]
        assert a3.few_shot_source == "counterexample"
        assert a3.system_prompt is True
        assert a3.tier0 is True

    def test_resolve_arm_artifacts_a0_uses_the_as_shipped_grammar_citing_fixture(self):
        artifacts = arms_module.resolve_arm_artifacts(arms_module.ARMS["A0"])
        serialized = json.dumps(artifacts.few_shot_examples).lower()
        assert "grammar" in serialized
        assert artifacts.few_shot_sha is not None

    def test_resolve_arm_artifacts_a3_uses_the_counterexample_fixture_no_grammar(self):
        artifacts = arms_module.resolve_arm_artifacts(arms_module.ARMS["A3"])
        serialized = json.dumps(artifacts.few_shot_examples).lower()
        assert "grammar" not in serialized

    def test_resolve_arm_artifacts_raises_when_sha_cannot_be_resolved(self, monkeypatch):
        def _boom():
            raise RuntimeError("simulated: no matching commit in history")

        monkeypatch.setattr(arms_module, "_resolve_pre_35_08_fewshot_sha", _boom)
        with pytest.raises(RuntimeError):
            arms_module.resolve_arm_artifacts(arms_module.ARMS["A0"])

    def test_run_arm_returns_provenance_corpus_assert_provenance_accepts(self):
        corpus = corpus_module.Corpus(
            name="test-fixture",
            context=_minimal_cg_context(),
            blocks=[],
            abstain_expected=[],
            tier0_evidence=True,
            ip_class="own",
            corpus_version=1,
            frozen_at_commit="deadbeef",
            context_sha256="dummy",
        )
        fake_response = GenerateResponse(
            text=json.dumps(
                {
                    "proposals": [],
                    "unrecognized": [
                        {"memberIds": ["n3", "n4"], "reason": "test stub -- not evaluated for real classification"}
                    ],
                }
            ),
            provider="deepseek",
            model="deepseek-chat",
            usage={},
        )
        adapter = cassette_module.CassetteAdapter(
            "A0",
            _FakeRealAdapter([fake_response]),
            negotiated_mode="none",
            prompt_version="test",
            ip_class=corpus.ip_class,
            mode="live",
        )

        # `mode="live"` reaches CassetteAdapter's real-call branch, which now
        # refuses the harness's `"test-api-key"` placeholder outright. Passing
        # an explicit key is exactly the pairing a real live caller must
        # honour, so this stub run exercises the same seam.
        outcome = arms_module.run_arm(
            arms_module.ARMS["A0"], corpus, adapter, api_key_override="stub-key-not-a-real-credential"
        )

        corpus_module.assert_provenance(outcome["provenance"])
        assert outcome["result"]["valid"] is True

    def test_live_mode_refuses_the_placeholder_api_key(self):
        """WR-06: `run_arm` patches `resolve_active_provider` to return the
        literal "test-api-key" whenever no override is passed. That is
        harmless in replay but would go out to a real provider as a Bearer /
        x-api-key header on the live path. The refusal must live at the
        boundary that knows it is live, not in one caller's memory."""
        corpus = corpus_module.Corpus(
            name="stub",
            context=_minimal_cg_context(),
            blocks=[],
            abstain_expected=[],
            tier0_evidence=True,
            ip_class="own",
            corpus_version=1,
            frozen_at_commit="deadbeef",
            context_sha256="dummy",
        )
        adapter = cassette_module.CassetteAdapter(
            "A0",
            _FakeRealAdapter([]),
            negotiated_mode="none",
            prompt_version="test",
            ip_class=corpus.ip_class,
            mode="live",
        )

        with pytest.raises(cassette_module.CassetteWriteError, match="placeholder/empty api_key"):
            arms_module.run_arm(arms_module.ARMS["A0"], corpus, adapter)

    def test_arms_module_never_forks_recognize_structure(self):
        source = Path(arms_module.__file__).read_text(encoding="utf-8")
        assert source.count("def recognize_structure") == 0


# ── SC1 gate (Task 3) -- a pure, corpus/arm-agnostic conjunctive assertion so
# its failing-conjunct behaviour is unit-testable with synthetic numbers,
# independent of any cassette or corpus/arm run ──

DEFAULT_SC1_GATE_THRESHOLD = 0.60


def assert_sc1_gate(
    *,
    m1: float,
    e1_violations: int,
    silent_drop_count: int,
    grammar_citation_rate: float,
    confidence_spread_ok: bool,
    provenance_ok: bool,
    threshold: float = DEFAULT_SC1_GATE_THRESHOLD,
) -> None:
    """The SC1 ship gate (35-AI-SPEC.md 5 "SC1 pass threshold"): ONE
    conjunctive assertion -- M1 >= threshold AND E1 violations == 0 AND
    silent drops == 0 AND grammar_citation_rate == 0.00 AND the
    confidence-spread check passes AND provenance is complete. Any single
    conjunct failing fails the gate. Raises naming EVERY failing conjunct,
    not just that the gate failed, so debugging starts from the actual
    cause."""
    failing: "list[str]" = []
    if not (m1 >= threshold):
        failing.append(f"M1={m1:.3f} < threshold {threshold:.2f}")
    if e1_violations != 0:
        failing.append(f"E1 violations={e1_violations} != 0")
    if silent_drop_count != 0:
        failing.append(f"silent_drop_count={silent_drop_count} != 0")
    if grammar_citation_rate != 0.0:
        failing.append(f"grammar_citation_rate={grammar_citation_rate:.3f} != 0.00")
    if not confidence_spread_ok:
        failing.append("confidence_spread_ok is False")
    if not provenance_ok:
        failing.append("provenance is incomplete")

    if failing:
        raise AssertionError("SC1 gate FAILED -- conjunct(s) not satisfied: " + "; ".join(failing))


class TestSC1GateConjunction:
    def test_all_conjuncts_pass_is_silent(self):
        assert (
            assert_sc1_gate(
                m1=0.80,
                e1_violations=0,
                silent_drop_count=0,
                grammar_citation_rate=0.0,
                confidence_spread_ok=True,
                provenance_ok=True,
                threshold=0.60,
            )
            is None
        )

    def test_low_m1_fails_naming_that_conjunct(self):
        with pytest.raises(AssertionError, match=r"M1=0\.400 < threshold 0\.60"):
            assert_sc1_gate(
                m1=0.40,
                e1_violations=0,
                silent_drop_count=0,
                grammar_citation_rate=0.0,
                confidence_spread_ok=True,
                provenance_ok=True,
                threshold=0.60,
            )

    def test_silent_drop_fails_separately_from_m1(self):
        """M1 above threshold but silent_drop_count > 0 must still fail the
        gate, and the message must name silent_drop_count, not M1."""
        with pytest.raises(AssertionError) as excinfo:
            assert_sc1_gate(
                m1=0.80,
                e1_violations=0,
                silent_drop_count=3,
                grammar_citation_rate=0.0,
                confidence_spread_ok=True,
                provenance_ok=True,
                threshold=0.60,
            )
        message = str(excinfo.value)
        assert "silent_drop_count=3" in message
        assert "M1=" not in message

    def test_multiple_failing_conjuncts_all_named(self):
        with pytest.raises(AssertionError) as excinfo:
            assert_sc1_gate(
                m1=0.10,
                e1_violations=1,
                silent_drop_count=2,
                grammar_citation_rate=0.5,
                confidence_spread_ok=False,
                provenance_ok=False,
                threshold=0.60,
            )
        message = str(excinfo.value)
        for fragment in (
            "M1=",
            "E1 violations",
            "silent_drop_count",
            "grammar_citation_rate",
            "confidence_spread_ok",
            "provenance",
        ):
            assert fragment in message, f"expected {fragment!r} in gate failure message"


# ── A0 validity check (Task 3) -- also a pure function, for the same reason ──

A0_M1_NEAR_ZERO_THRESHOLD = 0.10


def assert_a0_validity(m1: float, grammar_citation_rate: float) -> None:
    """A0 is the harness's OWN validity test (35-AI-SPEC.md 5): it must
    reproduce UAT F3 -- near-zero M1 with a non-zero grammar_citation_rate.
    If A0 does NOT fail this way, the HARNESS is wrong, not the model, and no
    other arm's number can be trusted until this is fixed."""
    if m1 <= A0_M1_NEAR_ZERO_THRESHOLD and grammar_citation_rate > 0.0:
        return
    raise AssertionError(
        "A0 validity check FAILED: arm A0 (as-shipped few-shot, no system "
        "prompt, no Tier 0, deepseek-chat) was expected to reproduce UAT F3 "
        f"-- near-zero M1 (got {m1:.3f}, expected <= {A0_M1_NEAR_ZERO_THRESHOLD}) "
        f"with a non-zero grammar_citation_rate (got {grammar_citation_rate:.3f}). "
        "If A0 does NOT fail this way, the HARNESS is wrong, not the model -- "
        "no other arm's number can be trusted until this is fixed."
    )


class TestA0ValidityCheck:
    def test_passes_silently_when_a0_fails_as_expected(self):
        assert assert_a0_validity(m1=0.03, grammar_citation_rate=0.75) is None

    def test_raises_stating_harness_is_wrong_when_a0_does_not_fail(self):
        with pytest.raises(AssertionError) as excinfo:
            assert_a0_validity(m1=0.90, grammar_citation_rate=0.0)
        message = str(excinfo.value).lower()
        assert "harness" in message
        assert "not the model" in message


# ── E0/Tier-0-evidence stamping (Task 3) ──


def stamp_e0_evidence(e0_rows: "list[dict]", tier0_evidence: bool) -> "list[dict]":
    """Stamp every E0 row with `evidence: tier0_evidence`. Rows computed from
    a corpus carrying `tier0Evidence: false` (Corpus A, `frame_ablated`) are
    printed but excluded from every reported figure (report.py, Task 4, reads
    this stamp to do the excluding)."""
    return [{**row, "evidence": tier0_evidence} for row in e0_rows]


def t0_gates_apply(tier0_evidence: bool) -> bool:
    """Whether the T0-precision >= 0.98 / T0-contamination == 0 gates are
    asserted for a corpus -- only True when `tier0_evidence` is True."""
    return tier0_evidence


class TestE0EvidenceStamping:
    def test_frame_ablated_e0_rows_stamped_not_evidence(self):
        corpus = corpus_module.load("frame_ablated")
        assert corpus.tier0_evidence is False

        stamped = stamp_e0_evidence([{"nodeId": "n1"}, {"nodeId": "n2"}], corpus.tier0_evidence)
        assert all(row["evidence"] is False for row in stamped)
        assert t0_gates_apply(corpus.tier0_evidence) is False

    def test_urbanblock_slice_e0_rows_carry_evidence_true(self):
        corpus = corpus_module.load("urbanblock_slice")
        assert corpus.tier0_evidence is True

        stamped = stamp_e0_evidence([{"nodeId": "n1"}], corpus.tier0_evidence)
        assert all(row["evidence"] is True for row in stamped)
        assert t0_gates_apply(corpus.tier0_evidence) is True


# ── Provenance refusal (Task 3) ──


class TestProvenanceRefusal:
    def test_result_row_missing_negotiated_mode_is_refused(self):
        incomplete_row = {
            "promptVersion": "r1",
            "provider": "anthropic",
            "model": "m",
            "temperature": 0.0,
            "contextSha256": "x",
            "frozenAtCommit": "y",
            "corpusVersion": 1,
            # negotiatedMode deliberately missing.
        }
        with pytest.raises(corpus_module.ProvenanceError):
            corpus_module.assert_provenance(incomplete_row)


# ── conftest.py CLI options (Task 3) ──


class TestConftestOptions:
    def test_pytest_help_lists_recognition_eval_options(self):
        result = subprocess.run(
            [sys.executable, "-m", "pytest", "--help"],
            cwd=str(Path(__file__).resolve().parent.parent),
            capture_output=True,
            text=True,
            timeout=60,
        )
        help_text = result.stdout
        for opt in ("--corpus", "--arm", "--arms", "--sc1-gate", "--permutations"):
            assert opt in help_text, f"{opt} not listed in pytest --help output"

    def test_options_registered_with_expected_defaults(self, request):
        # pytest CLI options are process-global for the whole session -- this
        # test can only verify DEFAULTS when nothing overrode them. 35-15's
        # own documented Task 3 command (`--corpus=urbanblock_slice --arm=A3
        # --sc1-gate=0.60`) runs this whole file in one session, which makes
        # these assertions structurally unable to hold; skip rather than
        # falsely fail when an override is active, exactly like
        # TestEndToEndDriver's own --corpus/--arm skip precedent above.
        # Guard EVERY option this test asserts, not just three of the five --
        # the previous guard omitted sc1_gate/permutations while lines below
        # assert exactly those, so `pytest --permutations=3` (a documented
        # knob) failed a test that has nothing to do with the run.
        expected_defaults = {
            "corpus": None,
            "arm": None,
            "arms": None,
            "sc1_gate": 0.60,
            "permutations": 1,
        }
        overridden = [
            name
            for name, default in expected_defaults.items()
            if request.config.getoption(name) != default
        ]
        if overridden:
            pytest.skip(
                "cannot verify registered DEFAULTS in a session where "
                f"{overridden} were explicitly passed (pytest CLI options are "
                "process-global, not per-test)."
            )
        for name, default in expected_defaults.items():
            actual = request.config.getoption(name)
            if isinstance(default, float):
                assert actual == pytest.approx(default), name
            else:
                assert actual == default, name


# ── The real (corpus x arm) driver, wired through cassette replay (Task 3) ──


class TestEndToEndDriver:
    """Skipped by default: no cassettes are recorded yet as of 35-13 (they
    are populated by 35-15's record sweep once Corpus B is frozen). Pass
    `--corpus`/`--arm` explicitly once cassettes exist to actually run this
    -- e.g. the CI command from 35-AI-SPEC.md 5:
    `pytest tests/test_recognition_eval.py -q --corpus=urbanblock_slice
    --arm=A3 --sc1-gate=0.60`."""

    def test_scores_one_corpus_arm_combo_via_replay(self, request):
        corpus_name = request.config.getoption("corpus")
        arm_id = request.config.getoption("arm")
        if not corpus_name or not arm_id:
            pytest.skip(
                "requires --corpus and --arm (e.g. --corpus=urbanblock_slice "
                "--arm=A3); no cassettes are recorded yet as of 35-13 -- run "
                "the 35-15 record sweep first."
            )

        corpus = corpus_module.load(corpus_name)
        corpus_module.assert_context_unchanged(corpus)

        arm = arms_module.ARMS[arm_id]
        # Same single source of truth report.py uses. NEVER
        # `"json_schema_strict" if arm.structured_output` here: negotiated_mode
        # is one of the cassette-key inputs, and arm A4's REAL mode is
        # `json_object` (DeepSeek rejects json_schema/strict outright), so the
        # naive placeholder computed a key no recording could ever match --
        # A4, the only arm this harness exists to distinguish, was the only one
        # the driver could not replay.
        negotiated_mode = arms_module.resolve_real_negotiated_mode(arm)
        adapter = cassette_module.CassetteAdapter(
            arm_id,
            None,
            negotiated_mode=negotiated_mode,
            prompt_version=cg_recognition.PROMPT_VERSION,
            ip_class=corpus.ip_class,
            mode="replay",
        )

        outcome = arms_module.run_arm(
            arm, corpus, adapter, negotiated_mode_override=negotiated_mode
        )
        corpus_module.assert_provenance(outcome["provenance"])  # refuses to score an incomplete row

        result = outcome["result"]
        assert result["valid"] is True, result.get("violations")

        proposals = result["proposal"]["proposals"]
        match_result = scoring_module.match_blocks(proposals, corpus.blocks)
        m1 = scoring_module.m1_exact_rate(match_result)
        rationales = [p.get("rationale", "") for p in proposals if isinstance(p, dict)]
        grammar_rate = scoring_module.grammar_citation_rate(rationales)

        if arm_id == "A0":
            assert_a0_validity(m1=m1, grammar_citation_rate=grammar_rate)
        elif arm_id == "A3":
            residual_ids = cg_topology.scope_untagged(corpus.context, None).node_ids
            silent_drops = scoring_module.silent_drop_count(
                residual_ids, proposals, result["proposal"].get("unrecognized", [])
            )
            confidences = [
                p.get("confidence") for p in proposals if isinstance(p.get("confidence"), (int, float))
            ]
            assert_sc1_gate(
                m1=m1,
                e1_violations=0,  # validate_proposed_structure() already passed above
                silent_drop_count=silent_drops,
                grammar_citation_rate=grammar_rate,
                confidence_spread_ok=scoring_module.confidence_spread_ok(confidences),
                provenance_ok=True,
                threshold=request.config.getoption("sc1_gate"),
            )


# ── live_sweep.py pure helpers -- free, hermetic, no marker needed. These
# cover the money-and-measurement invariants that a paid, marker-gated test
# cannot practically assert. ──


class TestLiveSweepHelpers:
    def test_permutations_are_pairwise_distinct(self):
        """CR-01: branching on `n` alone returned 3 IDENTICAL orderings for a
        1-example few-shot list (`reversed([x]) == [x]`, and `k = 1//2 or 1`
        made the rotation a no-op too). Arms A0/A0f use exactly such a list.
        Each duplicate is a separately-billed live call that collides on the
        same cassette key and then lands in the report as an independent
        ordering -- manufacturing an example-order stability result from a
        sub-sweep that never varied the order."""
        for examples, expected in (([], 1), ([{"a": 1}], 1), ([{"a": 1}, {"b": 2}], 2)):
            perms = live_sweep_module.few_shot_permutations(examples, n=3)
            assert len(perms) == expected, (examples, perms)
            fingerprints = {json.dumps(p, sort_keys=True, default=str) for p in perms}
            assert len(fingerprints) == len(perms), f"duplicate ordering emitted for {examples!r}"

    def test_permutations_still_yields_three_for_a_real_multi_example_list(self):
        examples = [{"i": i} for i in range(5)]
        perms = live_sweep_module.few_shot_permutations(examples, n=3)
        assert len(perms) == 3
        assert len({json.dumps(p, sort_keys=True) for p in perms}) == 3
        assert perms[0] == examples, "permutation 0 must be the as-authored order"

    def test_permutations_rejects_a_nonpositive_count(self):
        """WR-03: `--permutations=0` previously fell through to the
        single-ordering branch, silently billing a different sweep than the
        operator asked for."""
        for bad in (0, -1):
            with pytest.raises(ValueError, match="must be >= 1"):
                live_sweep_module.few_shot_permutations([{"a": 1}], n=bad)

    def test_run_live_sweep_rejects_a_nonpositive_permutation_count(self):
        with pytest.raises(ValueError, match="must be >= 1"):
            live_sweep_module.run_live_sweep(["A0"], ["frame_ablated"], permutations=0, mode="record")

    def test_unpriced_calls_are_flagged_not_silently_free(self):
        """WR-02: an unlisted (provider, model) yields 0.0, which is
        indistinguishable from a genuinely free call unless it is flagged.
        `USD_PER_MTOK` has two entries, so a model rename or an endpoint swap
        would otherwise under-report the headline cost by exactly the unpriced
        volume while still looking authoritative."""
        usage = {"prompt_tokens": 1000, "completion_tokens": 500, "total_tokens": 1500}

        cost, priced = live_sweep_module.estimate_usd_cost_priced("openai", "deepseek-chat", usage)
        assert priced is True and cost > 0.0

        cost, priced = live_sweep_module.estimate_usd_cost_priced("openai", "some-renamed-model", usage)
        assert priced is False and cost == 0.0

    def test_cost_summary_names_the_unpriced_volume(self):
        def _attempt(model, priced, usd):
            return live_sweep_module.AttemptCost(
                arm_id="A0", corpus="c", permutation_index=0, real_provider="openai",
                model=model, prompt_tokens=10, completion_tokens=5, total_tokens=15,
                usd_cost=usd, priced=priced,
            )

        clean = live_sweep_module.LiveSweepResult(outcomes=[], costs=[_attempt("deepseek-chat", True, 0.01)])
        assert "UNPRICED" not in clean.cost_summary()

        dirty = live_sweep_module.LiveSweepResult(
            outcomes=[], costs=[_attempt("deepseek-chat", True, 0.01), _attempt("mystery-model", False, 0.0)]
        )
        summary = dirty.cost_summary()
        assert "UNPRICED" in summary and "openai/mystery-model" in summary

    def test_mask_url_drops_credential_bearing_path_segments(self):
        """WR-08: the OpenAI-compatible endpoints REAL_ADAPTER_MAP exists to
        support routinely carry the credential in the URL, and this value
        reaches stdout and CI logs."""
        masked = live_sweep_module.mask_url("https://gateway.example.com/tok_SECRET123/v1")
        assert "SECRET123" not in masked
        assert "gateway.example.com" in masked

    def test_report_sweep_can_replay_the_permutation_subsweep(self):
        """WR-04: the permutation cassettes are committed (arm A3 recorded its
        sub-sweep), but no code in the repo could re-score them --
        `run_live_sweep` scored each ordering in-process and persisted nothing
        but the cassette, and `run_report_sweep`, the only replay-side scorer,
        always replayed the as-authored order. The per-ordering M1 figures
        lived only in pytest stdout. In a harness whose output goes in a thesis
        appendix, the sub-sweep was the one result not reproducible from
        committed state."""
        single, _ = report_module.run_report_sweep(["urbanblock_slice"], ["A3"], permutations=1)
        if not single:
            pytest.skip("no committed cassette for urbanblock_slice x A3")

        scored, skipped = report_module.run_report_sweep(["urbanblock_slice"], ["A3"], permutations=3)
        assert not skipped, skipped
        assert len(scored) == 3, "expected one ScoredRow per distinct ordering"
        assert [r.permutation_index for r in scored] == [0, 1, 2]
        assert scored[0].m1 == single[0].m1, "ordering 0 must reproduce the as-authored row"

    def test_report_sweep_rejects_a_nonpositive_permutation_count(self):
        with pytest.raises(ValueError, match="must be >= 1"):
            report_module.run_report_sweep(["urbanblock_slice"], ["A3"], permutations=0)

    def test_credential_error_does_not_echo_the_raw_base_url(self, monkeypatch):
        monkeypatch.setattr(
            live_sweep_module.llm_gateway,
            "load_persisted_llm_settings",
            lambda: {"provider": "anthropic", "baseUrl": "https://gw.example.com/tok_SECRET123/v1"},
        )
        with pytest.raises(live_sweep_module.LiveCredentialError) as excinfo:
            live_sweep_module.resolve_live_adapter_and_key(arms_module.ARMS["A4"])
        assert "SECRET123" not in str(excinfo.value)


# ── live_sweep.py (35-15 deviation) -- the record-mode driver 35-13-SUMMARY.md
# asserted was ready but never actually existed: no test here was ever marked
# `@pytest.mark.live` before this class. Making a real, metered LLM call is
# this class's entire purpose, so it is gated twice over: the `live` marker
# (deselected by default per conftest.py) AND an explicit
# RECOGNITION_EVAL_MODE=record/live check inside the test itself. ──


class TestLiveRecordSweep:
    @pytest.mark.live
    def test_records_requested_arms_against_requested_corpora(self, request):
        arms_opt = request.config.getoption("arms")
        corpus_opt = request.config.getoption("corpus")
        permutations = request.config.getoption("permutations")

        if not arms_opt:
            pytest.skip(
                "requires --arms (e.g. --arms=A0,A1,A2,A3,A4); this test "
                "never runs implicitly."
            )

        mode = os.environ.get("RECOGNITION_EVAL_MODE", "replay")
        if mode not in ("record", "live"):
            pytest.skip(
                f"RECOGNITION_EVAL_MODE={mode!r} -- this test only records "
                "with RECOGNITION_EVAL_MODE=record (or spot-checks with "
                "=live). The default (replay) is intentionally a no-op here "
                "so a bare `-m live` pass without the env var set does not "
                "silently do nothing while looking like it ran."
            )

        arm_ids = [a.strip() for a in arms_opt.split(",") if a.strip()]
        corpus_names = (
            [corpus_opt] if corpus_opt else ["frame_ablated", "urbanblock_slice"]
        )

        result = live_sweep_module.run_live_sweep(
            arm_ids, corpus_names, permutations=permutations, mode=mode
        )

        for outcome in result.outcomes:
            print(f"[{outcome.corpus} x {outcome.arm_id}] {outcome.status}: {outcome.detail}")
            for row in outcome.permutations:
                print(f"    permutation {row['permutation_index']}: {row}")
        print(f"[live_sweep] {result.cost_summary()}")

        # Every requested combo must be accounted for -- either recorded or
        # skipped with a named, expected reason. An unrecognized status
        # would mean a combo silently vanished, which is exactly what the
        # rest of this harness (cassette misses, provenance refusal) exists
        # to prevent.
        unexpected = [o for o in result.outcomes if o.status not in live_sweep_module.OUTCOME_STATUSES]
        assert not unexpected, unexpected

        # The status check above CANNOT FAIL ON ITS OWN: `status` is assigned
        # at a handful of sites in live_sweep.py using exactly the literals in
        # OUTCOME_STATUSES, so as the only assertion in this test it was a
        # tautology -- a paid record run in which every combo was skipped for
        # credentials exited green, having spent nothing and recorded nothing,
        # indistinguishable in CI from a successful record. (pytest captures
        # and discards the prints above on a pass, so the operator saw a green
        # dot and no data.) That failure mode is live: this module calls
        # os.environ.setdefault("LLM_MASTER_SECRET", "test-master-secret") at
        # import, so a record run without the REAL secret exported decrypts
        # nothing and skips every arm. Assert the run actually MEASURED
        # something.
        failed = [o for o in result.outcomes if o.status == "failed"]
        assert not failed, f"combo(s) failed after spending money: {[(o.arm_id, o.corpus, o.detail) for o in failed]}"

        recorded = [o for o in result.outcomes if o.status == "recorded"]
        assert recorded, (
            "record sweep produced ZERO recordings -- nothing was measured. "
            "Most likely LLM_MASTER_SECRET is not the real one (this module "
            "setdefault()s a fake at import), so every decrypt returned no "
            "key. Skips: "
            f"{[(o.arm_id, o.corpus, o.status, o.detail) for o in result.outcomes]}"
        )
        assert result.costs, "recordings exist but no token usage was captured -- cost accounting is broken"


# ── report.py (Task 4) -- rendering tested with synthetic rows, independent
# of whether a real corpus x arm sweep can succeed today ──


class TestReport:
    def _synthetic_scored_row(self, **overrides) -> report_module.ScoredRow:
        base = dict(
            corpus="urbanblock_slice",
            arm_id="A3",
            claim="The shipping configuration.",
            provenance={
                "promptVersion": "r35.4",
                "provider": "deepseek",
                "model": "deepseek-chat",
                "temperature": 0.0,
                "negotiatedMode": "none",
                "contextSha256": "abc",
                "frozenAtCommit": "def",
                "corpusVersion": 1,
                "armId": "A3",
                "fewShotSha": None,
            },
            tier0_evidence=True,
            n_blocks=30,
            m1=0.70,
            m1_successes=21,
            m2=0.80,
            mean_jaccard=0.75,
            member_edit_distance=12,
            m5={"ratio": 1.0, "fragmentation": 1.0, "fusion": 1.0},
            e3_strict=0.9,
            e3_collapsed=0.95,
            e3_intf_false_positive_rate=0.0,
            abstention_recall=1.0,
            abstention_precision=1.0,
            silent_drop_count=0,
            brier=0.05,
            ece_value=0.03,
            ece_bins=[{"lower": 0.0, "upper": 0.2, "count": 0, "confidence_sum": 0.0, "outcome_sum": 0.0}],
            grammar_citation_rate=0.0,
            e8_publishability_failures=0,
            e8_note="proxy metric",
        )
        base.update(overrides)
        return report_module.ScoredRow(**base)

    def test_render_markdown_contains_m1_wilson_interval_and_n(self):
        markdown = report_module.render_markdown([self._synthetic_scored_row()], [], sc1_gate_threshold=0.60)
        assert "Wilson 95% CI" in markdown
        assert "n=30" in markdown

    def test_render_markdown_contains_ece_with_per_bin_counts(self):
        markdown = report_module.render_markdown([self._synthetic_scored_row()], [], sc1_gate_threshold=0.60)
        assert "ECE=" in markdown
        assert "n=0" in markdown  # the synthetic bin's count, proving per-bin counts are rendered

    def test_render_markdown_reports_ship_gate_and_claim_threshold_as_two_lines(self):
        markdown = report_module.render_markdown([self._synthetic_scored_row()], [], sc1_gate_threshold=0.60)
        assert "Ship gate" in markdown
        assert "Claim threshold" in markdown

    def test_render_markdown_has_not_measured_section_naming_skipped_combos_and_uncalibrated_dims(self):
        skipped = [report_module.SkippedRow(corpus="urbanblock_slice", arm_id="A0", reason="cassette miss")]
        markdown = report_module.render_markdown([], skipped, sc1_gate_threshold=0.60)
        assert "## Not measured in this run" in markdown
        assert "urbanblock_slice x A0" in markdown
        assert "E4-name" in markdown
        assert "E7-soft" in markdown

    def test_render_markdown_stamps_evidence_false_for_frame_ablated(self):
        row = self._synthetic_scored_row(corpus="frame_ablated", tier0_evidence=False)
        markdown = report_module.render_markdown([row], [], sc1_gate_threshold=0.60)
        assert "evidence: false" in markdown

    def test_render_markdown_never_leaks_prompt_body_or_api_key(self):
        markdown = report_module.render_markdown([self._synthetic_scored_row()], [], sc1_gate_threshold=0.60)
        assert "sk-" not in markdown
        assert "promptBody" not in markdown

    def test_render_json_round_trips_scored_and_skipped_rows(self):
        skipped = [report_module.SkippedRow(corpus="frame_ablated", arm_id="A1", reason="cassette miss")]
        payload = report_module.render_json([self._synthetic_scored_row()], skipped)
        assert payload["scored"][0]["corpus"] == "urbanblock_slice"
        assert payload["skipped"][0]["reason"] == "cassette miss"
        assert "frame_ablated x A1" in payload["notMeasured"]["skippedCombos"]
        assert "sk-" not in json.dumps(payload)

    def test_main_writes_markdown_and_json_and_exits_0(self, tmp_path):
        out_path = tmp_path / "eval-report.md"

        exit_code = report_module.main(["--out", str(out_path), "--corpora", "frame_ablated", "--arms", "A0"])

        assert exit_code == 0
        assert out_path.exists()
        assert out_path.with_suffix(".json").exists()
        markdown = out_path.read_text(encoding="utf-8")
        assert "sk-" not in markdown
        assert "## Not measured in this run" in markdown  # no cassette recorded yet as of 35-13
