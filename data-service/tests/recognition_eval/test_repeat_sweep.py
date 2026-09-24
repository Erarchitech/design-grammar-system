"""1204-07 repeat_sweep tests: D-13 floor/strata, D-10 temperature, D-17
two-level metrics + Wilson CI, D-24 schema, D-21 replay byte-identity, and the
`--max-samples` budget cap.

Harness-side only (D-23). No live adapter, no network: every test injects a
FakeAdapter through `adapter_factory`/`adapters`.

Temp-dir note: this repo's pytest/system temp root is permission-denied in
this sandbox, so every test that needs on-disk scratch uses the repo-local
`scratch_dir` fixture below (a uniquely-named directory under `.de01/`, the
repo's own output root -- the same workaround plan 1204-05's suite uses),
always removed in a `finally`.
"""

from __future__ import annotations

import hashlib
import json
import os
import shutil
import sys
import uuid
from pathlib import Path

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, os.path.dirname(__file__))

os.environ.setdefault("LLM_MASTER_SECRET", "test-master-secret")

import pytest  # noqa: E402

from llm_gateway import GenerateResponse  # noqa: E402

from recognition_eval import repeat_sweep as repeat_sweep_module  # noqa: E402
from recognition_eval import report as report_module  # noqa: E402
from recognition_eval import scoring as scoring_module  # noqa: E402
from recognition_eval.corpus import assert_llm_sample_provenance  # noqa: E402
from recognition_eval.outcome_taxonomy import OUTCOME_LABELS  # noqa: E402
from recognition_eval.repeat_sweep import (  # noqa: E402
    INSUFFICIENT_SAMPLES,
    MIN_SAMPLE_FLOOR,
    REPEAT_SAMPLES,
    SUBJECT_RECOGNITION,
    SUBJECT_RULE_INGEST,
    TEMPERATURE_NOT_SENT,
    compute_item_metrics,
    normalize_level2,
    record_temperature,
    run_one_item,
    run_repeat_sweep,
)


# ── repo-local scratch (tmp_path is permission-denied in this sandbox) ──

_REPO_ROOT = Path(__file__).resolve().parents[3]


@pytest.fixture
def scratch_dir():
    """A uniquely-named scratch directory under `.de01/`, always removed."""
    root = _REPO_ROOT / ".de01" / f"de01-repeat-test-{uuid.uuid4().hex[:8]}"
    root.mkdir(parents=True, exist_ok=True)
    try:
        yield root
    finally:
        shutil.rmtree(root, ignore_errors=True)


# ── FakeAdapter tracer ──


class FakeAdapter:
    """Canned `GenerateResponse` per sample.

    Records every `(sample_index, request)` it is asked for so a test can
    prove distinct sample indices resolved distinct draws, and counts its own
    construction so `resolve_adapter_once`'s once-per-provider contract is
    asserted, not assumed.
    """

    def __init__(self, provider="fake-provider", model="fake-model", responses=None):
        self.provider = provider
        self.model = model
        self._responses = responses
        self.calls = []

    def generate(self, req, api_key, options=None):
        index = len(self.calls)
        self.calls.append({"index": index, "request": req, "options": options})
        if self._responses is not None:
            text = self._responses[index % len(self._responses)]
        else:
            text = json.dumps({"index": index}, sort_keys=True)
        return GenerateResponse(
            text=text,
            provider=self.provider,
            model=self.model,
            usage={"prompt_tokens": 1, "completion_tokens": 1, "total_tokens": 2},
            truncated=False,
            finish_reason="stop",
            served_model=self.model,
            response_id=f"resp-{index}",
            system_fingerprint="fp_fake",
        )


def _item(item_id="item-1", **overrides):
    """A minimally valid recognition item with a full provenance block."""
    item = {
        "item_id": item_id,
        "prompt": "structure this canvas",
        "system": "you are a recognition engine",
        "provider": "fake-provider",
        "model": "fake-model",
        "valid": True,
        "prompt_file_path": "fixtures/llm_repeatability/prompts/recognition/item-1.txt",
        "prompt_sha256": "a" * 64,
        "prompt_version": "v1",
        "gateway_commit": "abc1234",
        "service_commit": "def5678",
        "timestamp": "2026-07-27T00:00:00Z",
        "base_url": "https://api.example.com/v1",
        # Not a real secret: the fake wrapped adapter never makes a call. A
        # placeholder here would trip CassetteAdapter's fail-closed guard.
        "api_key": "fake-not-a-real-key",
    }
    item.update(overrides)
    return item


class _FactorySpy:
    """Counts factory invocations so once-per-provider is asserted."""

    def __init__(self, adapters=None):
        self.calls = []
        self.adapters = adapters or {}

    def __call__(self, provider, model):
        self.calls.append((provider, model))
        if provider in self.adapters:
            return self.adapters[provider]
        return FakeAdapter(provider=provider, model=model or "fake-model")

    @property
    def providers_resolved(self):
        return [p for p, _ in self.calls]


def test_repeat_sweep_runs_k_samples_per_item_one_provider_end_to_end():
    """Task 1 tracer: one item, one provider, exactly REPEAT_SAMPLES records."""
    spy = _FactorySpy({"fake-provider": FakeAdapter()})

    result = run_repeat_sweep(
        [_item()],
        [{"provider": "fake-provider", "model": "fake-model"}],
        subject=SUBJECT_RECOGNITION,
        adapter_factory=spy,
        mode="live",
    )

    records = result["records"]
    assert len(records) == REPEAT_SAMPLES

    assert {r["sample_index"] for r in records} == set(range(1, REPEAT_SAMPLES + 1))
    assert 0 not in {r["sample_index"] for r in records}

    for record in records:
        assert record["outcome"] in OUTCOME_LABELS
        assert record["first_attempt_outcome"] in OUTCOME_LABELS
        assert_llm_sample_provenance(record["provenance"])
        assert record["provenance"]["sampleIndex"] == record["sample_index"]

    assert spy.providers_resolved.count("fake-provider") == 1
    assert len(spy.calls) == 1

# ── Task 2: D-13 min-5 floor ──


def _rule_ingest_item(item_id="rule-1", **overrides):
    item = {
        "item_id": item_id,
        "rule_text": "MATCH (n:Project) RETURN n",
        "system": "you are a cypher generator",
        "provider": "fake-provider",
        "model": "fake-model",
        "valid": True,
        "api_key": "fake-not-a-real-key",
        "prompt_file_path": "fixtures/llm_repeatability/rule_ingest_prompts/rule-1.txt",
        "prompt_sha256": "b" * 64,
        "prompt_version": "v1",
        "gateway_commit": "abc1234",
        "service_commit": "def5678",
        "timestamp": "2026-07-27T00:00:00Z",
        "base_url": "https://api.example.com/v1",
    }
    item.update(overrides)
    return item


def _records(provider, outputs, subject=SUBJECT_RULE_INGEST, **record_overrides):
    """A crafted per-sample record set, one record per output."""
    records = []
    for index, output in enumerate(outputs, start=1):
        record = {
            "item_id": "crafted",
            "subject": subject,
            "provider": provider,
            "model": "fake-model",
            "sample_index": index,
            "outcome": "valid",
            "first_attempt_outcome": "valid",
            "attempts": 1,
            "violation_code": None,
            "raw_output": output,
            "raw_output_sha256": hashlib.sha256(output.encode()).hexdigest(),
            "temperature": record_temperature(subject),
        }
        record.update(record_overrides)
        records.append(record)
    return records


def test_min_sample_floor_insufficient_samples():
    """D-13: k=3 is below the floor, so every rate reads the sentinel."""
    records = _records("fake-provider", [" A ", "A", "A"])
    assert len(records) == 3 < MIN_SAMPLE_FLOOR

    metrics = compute_item_metrics("crafted", records)
    cell = metrics["strata"]["fake-provider"]

    assert cell["modal_agreement_rate"] == INSUFFICIENT_SAMPLES
    assert cell["level1_agreement_rate"] == INSUFFICIENT_SAMPLES
    assert cell["modal_agreement_wilson"] == INSUFFICIENT_SAMPLES
    assert not isinstance(cell["modal_agreement_rate"], (int, float))

    # The distinct COUNTS are not rates and stay honest below the floor.
    assert cell["level2_distinct"] == 1
    assert cell["level1_distinct"] == 2


def test_per_provider_strata_never_pooled():
    """D-13: two providers -> exactly two strata, never a combined cell."""
    records = _records("provider-a", ["X", "X", "X", "X", "X"])
    records += _records("provider-b", ["Y", "Y", "Y", "Y", "Z"])

    metrics = compute_item_metrics("crafted", records)

    assert set(metrics["strata"].keys()) == {"provider-a", "provider-b"}
    for pooled in ("all", "combined", "pooled", "total"):
        assert pooled not in metrics["strata"]

    assert metrics["strata"]["provider-a"]["n"] == 5
    assert metrics["strata"]["provider-b"]["n"] == 5
    assert metrics["strata"]["provider-a"]["modal_agreement_rate"] == 1.0
    assert metrics["strata"]["provider-b"]["modal_agreement_rate"] == 4 / 5


# ── Task 2: D-10 temperature recording ──


def test_rule_ingest_temperature_not_sent_provider_default():
    """D-10: rule-ingest sends no GenerationOptions -> the sentinel."""
    assert record_temperature(SUBJECT_RULE_INGEST) == TEMPERATURE_NOT_SENT
    assert TEMPERATURE_NOT_SENT == "not sent \u2014 provider default"

    fake = FakeAdapter(responses=['MATCH (n) RETURN n'])
    records = run_one_item(
        _rule_ingest_item(),
        "fake-provider",
        "fake-model",
        fake,
        subject=SUBJECT_RULE_INGEST,
        samples=3,
        mode="live",
    )

    assert len(records) == 3
    for record in records:
        assert record["temperature"] == TEMPERATURE_NOT_SENT
        assert record["provenance"]["samplingParamsAsSent"] == {
            "temperature": TEMPERATURE_NOT_SENT
        }

    # No GenerationOptions was sent on any rule-ingest draw.
    assert all(call["options"] is None for call in fake.calls)
    # ...and the metric cell carries the sentinel forward.
    metrics = compute_item_metrics("rule-1", records)
    assert metrics["strata"]["fake-provider"]["temperature"] == TEMPERATURE_NOT_SENT


def test_recognition_temperature_records_sampling_params_as_sent():
    """D-10 contrast: recognition records what was actually sent."""
    sent = {"temperature": 0.0, "max_tokens": 2048}
    assert record_temperature(SUBJECT_RECOGNITION, sent) == sent


# ── Task 2: D-17 level-2 normalization ──


def test_level2_normalization_subjects():
    """D-17: per-subject normalization collapses the declared equivalence."""
    # recognition: canonical JSON -- key order and whitespace stop counting.
    a = '{"blocks": [{"kind": "Procedure", "label": "A"}]}'
    b = '{"blocks":[{"label":"A","kind":"Procedure"}]}'
    assert a != b
    assert normalize_level2(SUBJECT_RECOGNITION, a) == normalize_level2(
        SUBJECT_RECOGNITION, b
    )

    # rule-ingest: whitespace-normalized Cypher.
    c = "MATCH (n:Project)\n  RETURN   n"
    d = "MATCH (n:Project) RETURN n"
    assert c != d
    assert normalize_level2(SUBJECT_RULE_INGEST, c) == normalize_level2(
        SUBJECT_RULE_INGEST, d
    )

    # An unsupported subject raises KeyError.
    with pytest.raises(KeyError):
        normalize_level2("nonsense", c)

    # An induced two-output, byte-different but level-2-equal fixture
    # collapses to one level-2 distinct count at n >= the floor.
    records = _records(
        "fake-provider",
        [c, d, c, d, c, d, c, d, c, d],
        subject=SUBJECT_RULE_INGEST,
    )
    cell = compute_item_metrics("crafted", records)["strata"]["fake-provider"]
    assert cell["level1_distinct"] == 2
    assert cell["level2_distinct"] == 1
    assert cell["modal_agreement_rate"] == 1.0


# ── Task 2: D-17 Wilson CI via scoring.wilson_interval ──


def test_wilson_ci_computed_via_scoring(monkeypatch):
    """D-17: bounds equal a direct scoring.wilson_interval(modal, n) call,
    with an INT successes count -- never a proportion."""
    n = MIN_SAMPLE_FLOOR
    records = _records("fake-provider", ["A"] * (n - 1) + ["B"])
    modal_count = n - 1

    seen = []
    real_wilson = scoring_module.wilson_interval

    def _spy(successes, total, z=1.96):
        seen.append((successes, total))
        return real_wilson(successes, total, z)

    monkeypatch.setattr(scoring_module, "wilson_interval", _spy)

    cell = compute_item_metrics("crafted", records)["strata"]["fake-provider"]
    expected_lower, expected_upper = real_wilson(modal_count, n)

    assert cell["modal_agreement_wilson"]["lower"] == pytest.approx(expected_lower)
    assert cell["modal_agreement_wilson"]["upper"] == pytest.approx(expected_upper)
    assert cell["modal_agreement_wilson"]["n"] == n

    assert seen, "scoring.wilson_interval was never called"
    successes, total = seen[-1]
    assert isinstance(successes, int) and not isinstance(successes, bool)
    assert isinstance(total, int) and not isinstance(total, bool)
    assert (successes, total) == (modal_count, n)


def test_wilson_ci_int_successes():
    """D-17: a crafted 7-of-10 modal setup matches wilson_interval(7, 10)."""
    records = _records("fake-provider", ["A"] * 7 + ["B"] * 3)
    cell = compute_item_metrics("crafted", records)["strata"]["fake-provider"]

    assert cell["modal_count"] == 7
    assert cell["n"] == 10
    assert cell["modal_agreement_rate"] == pytest.approx(0.7)

    lower, upper = scoring_module.wilson_interval(7, 10)
    assert cell["modal_agreement_wilson"]["lower"] == pytest.approx(lower)
    assert cell["modal_agreement_wilson"]["upper"] == pytest.approx(upper)


# ── Task 3 (cont.): D-24 additive emitter, D-21 replay regeneration, budget cap ──


def test_llm_report_schema_has_no_shared_or_accuracy_fields():
    """D-24/D-18: the LLM schema shares no top-level property with the
    deterministic DE-01 report schema (tools/de01/report_schema.json), and
    carries no accuracy or expected-label field."""
    schema_dir = Path(__file__).resolve().parent
    repo_root = schema_dir.parents[2]
    llm_schema = json.loads((schema_dir / "report_schema_llm.json").read_text(encoding="utf-8"))
    det_schema = json.loads(
        (repo_root / "tools" / "de01" / "report_schema.json").read_text(encoding="utf-8")
    )
    llm_keys = set(llm_schema.get("properties", {}).keys())
    det_keys = set(det_schema.get("properties", {}).keys())
    assert not llm_keys & det_keys, f"shared fields: {llm_keys & det_keys}"
    for forbidden in ("accuracy", "expected_label", "expectedLabel", "expected"):
        assert forbidden not in llm_keys


def test_llm_repeatability_emitter_is_additive():
    """D-24: the emitter round-trips an arbitrary LLM report payload without
    dropping or renaming keys. The no-shared-field property against the
    deterministic DE-01 schema is proven exhaustively by
    test_llm_report_schema_has_no_shared_or_accuracy_fields above."""
    crafted = {"providers": {"anthropic": {"distinct_count": 1, "modal_rate": 1.0}}}
    emitted = report_module.render_llm_repeatability_json(crafted)
    assert json.loads(emitted) == crafted


def test_llm_repeatability_markdown_renders_per_provider():
    """D-13: one section per provider, never a pooled total."""
    markdown = report_module.render_llm_repeatability_markdown(
        {"strata": {"anthropic": {"n": 10, "modal_count": 9}, "openai": {"n": 10, "modal_count": 7}}}
    )
    assert "## Provider: anthropic" in markdown
    assert "## Provider: openai" in markdown


def test_max_samples_budget_cap():
    """D-21: the --max-samples guard raises rather than silently truncating."""
    assert report_module.enforce_max_samples(5, cap=10) == 5
    assert report_module.enforce_max_samples(50, cap=None) == 50
    with pytest.raises(report_module.MaxSamplesExceededError):
        report_module.enforce_max_samples(15, cap=10)


def test_replay_regeneration_byte_identical():
    """D-21: regenerating the LLM report from the SAME committed inputs
    returns byte-identical JSON, labelled "scoring-pipeline determinism" --
    a claim about the scoring pipeline, never about the model."""
    item = {"id": "crafted-rule", "subject": SUBJECT_RULE_INGEST}

    first = report_module.generate_llm_report_bytes(None, "fake-provider", item)
    second = report_module.generate_llm_report_bytes(None, "fake-provider", item)
    assert first == second, "regeneration from identical inputs was not byte-identical"

    payload = json.loads(first.decode("utf-8"))
    assert payload["label"] == "scoring-pipeline determinism"
    assert payload["reportLabel"] == "scoring-pipeline determinism"
    assert payload["provider"] == "fake-provider"


def test_replay_regeneration_from_committed_cassette_is_deterministic(scratch_dir):
    """D-21: with an actual committed-style sample-index cassette on disk,
    two regeneration passes emit byte-identical JSON AND the metrics are a
    real function of the replayed records (not an empty fallback)."""
    cassette_root = scratch_dir / "cassettes"
    cassette_root.mkdir(parents=True, exist_ok=True)
    cassette_path = cassette_root / "fake-provider" / "crafted-rule.jsonl"
    cassette_path.parent.mkdir(parents=True, exist_ok=True)

    records = _records("fake-provider", ["A"] * 4 + ["B"], item_id="crafted-rule")
    cassette_path.write_text(
        "\n".join(json.dumps(r, sort_keys=True) for r in records) + "\n",
        encoding="utf-8",
    )

    item = {"id": "crafted-rule", "subject": SUBJECT_RULE_INGEST}
    first = report_module.generate_llm_report_bytes(cassette_root, "fake-provider", item)
    second = report_module.generate_llm_report_bytes(cassette_root, "fake-provider", item)
    assert first == second

    payload = json.loads(first.decode("utf-8"))
    assert payload["label"] == "scoring-pipeline determinism"

    direct = compute_item_metrics(item, records)
    assert payload["metrics"] == direct