"""Live record-mode sweep driver for the recognition eval harness (Phase
35-15).

35-13's own SUMMARY.md asserted that
`RECOGNITION_EVAL_MODE=record python -m pytest tests/test_recognition_eval.py
-m live --arms=A0,A0f,A1,A2,A3,A4,A5 --permutations=3` was ready to run once
Corpus B existed. It was not: no test in the suite is marked
`@pytest.mark.live` (the marker is only *registered* in `conftest.py`), and
both `report.py::run_report_sweep` and
`test_recognition_eval.py::TestEndToEndDriver` hardcode
`CassetteAdapter(..., mode="replay")` with `wrapped=None` -- there was no
code path that could ever call a live provider or write a cassette. This
module is that path, added as a 35-15 deviation (35-13-SUMMARY.md overstated
readiness; 35-15 is the sole consumer of the record-mode command line it
documented).

Design constraints carried over from `arms.py`/`cassette.py` (35-13):

- NEVER duplicate `recognize_structure()`'s retry/validation/merge logic --
  this module only resolves a REAL adapter + REAL API key and wraps it, then
  hands off to the existing, unmodified `arms.run_arm()`.
- Replay must stay hermetic ($0, no secrets, no network). Nothing in this
  module runs unless `RECOGNITION_EVAL_MODE` is `record` or `live` --
  callers gate on that before importing/using it for anything beyond the
  pure helpers (`few_shot_permutations`, `estimate_usd_cost`).
- A missing/mismatched credential for one arm's provider skips that arm
  with a named reason -- it never silently falls back to a different
  provider (which would falsify the arm's provenance) and it never crashes
  the whole sweep.
"""

from __future__ import annotations

import os
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

# data-service/tests/recognition_eval/live_sweep.py -> parents[2] == data-service/
_DATA_SERVICE_ROOT = str(Path(__file__).resolve().parents[2])
if _DATA_SERVICE_ROOT not in sys.path:
    sys.path.insert(0, _DATA_SERVICE_ROOT)
_TESTS_ROOT = str(Path(__file__).resolve().parents[1])
if _TESTS_ROOT not in sys.path:
    sys.path.insert(0, _TESTS_ROOT)

import cg_recognition  # noqa: E402
import llm_gateway  # noqa: E402

from recognition_eval import arms as arms_module  # noqa: E402
from recognition_eval import cassette as cassette_module  # noqa: E402
from recognition_eval import corpus as corpus_module  # noqa: E402
from recognition_eval import report as report_module  # noqa: E402

# The provider-label -> (real llm_gateway tag, base_url) map lives in
# `arms.py` (35-15) so both this live driver (which also needs a real
# decrypted API key) and `report.py`'s replay-only sweep (which must NEVER
# touch a secret) resolve the identical real provider/base_url -- and,
# critically, the identical negotiated structured-output mode, or a cassette
# recorded here would MISS on replay under a different computed key
# (discovered live: report.py's own prior `"json_schema_strict" if
# arm.structured_output` assumption produced a cassette-key mismatch against
# arm A4's real recording).
REAL_ADAPTER_MAP = arms_module.REAL_ADAPTER_MAP

# List pricing looked up at 2026-07-27 (api-docs.deepseek.com/quick_start/pricing
# for deepseek-chat cache-miss rate; Anthropic's published Sonnet rate for
# claude-sonnet-5) -- approximate and explicitly re-statable, per
# 35-AI-SPEC.md 5's own "re-verify at implementation time" note on its cost
# table. The token COUNTS multiplied against these rates are always real,
# taken from the live provider's own `usage` field in its HTTP response --
# only the $/token constant below is a looked-up, not measured, number.
USD_PER_MTOK: "dict[tuple[str, str], dict[str, float]]" = {
    ("openai", "deepseek-chat"): {"input": 0.27, "output": 1.10},
    ("anthropic", "claude-sonnet-5"): {"input": 3.00, "output": 15.00},
}


class LiveCredentialError(RuntimeError):
    """Raised when an arm's real provider/API key cannot be resolved from
    the persisted LLM settings -- e.g. an `anthropic` arm (A0f/A5) requested
    when only a DeepSeek key is configured. Callers skip the arm with this
    reason; they never substitute a different provider/model and relabel it
    as the requested arm, which would falsify that arm's provenance."""


def resolve_live_adapter_and_key(arm: "arms_module.Arm") -> "tuple[Any, str, str, str | None]":
    """Resolve a REAL (not eval-mocked) adapter + decrypted API key for
    `arm`, for use only under `RECOGNITION_EVAL_MODE=record`/`live`. Never
    returns the eval harness's own `"test-api-key"` placeholder literal --
    that string only ever appears on the replay path, where
    `CassetteAdapter` never calls the wrapped adapter at all.

    Reads `llm_gateway` directly (not through `cg_recognition`'s rebindable
    module attributes) so this always resolves the REAL functions
    regardless of whether `arms.run_arm()` has patched `cg_recognition` for
    an unrelated, concurrently-running call.

    Returns `(adapter, api_key, real_provider_tag, resolved_base_url)`.
    Raises `LiveCredentialError` if the persisted settings don't match this
    arm's required real provider/base_url, or no key can be decrypted.
    """
    if arm.provider not in REAL_ADAPTER_MAP:
        raise LiveCredentialError(
            f"arm {arm.id!r}: no REAL_ADAPTER_MAP entry for provenance "
            f"label provider={arm.provider!r} -- add one before recording "
            "this arm live."
        )
    real_tag, required_base_url = REAL_ADAPTER_MAP[arm.provider]

    master_secret = os.environ.get("LLM_MASTER_SECRET", "")
    settings = llm_gateway.load_persisted_llm_settings()
    persisted_provider = settings.get("provider")
    persisted_base_url = settings.get("baseUrl")

    base_url_mismatch = required_base_url is not None and persisted_base_url != required_base_url
    if persisted_provider != real_tag or base_url_mismatch:
        raise LiveCredentialError(
            f"arm {arm.id!r} (provenance provider={arm.provider!r}) needs a "
            f"real adapter provider={real_tag!r}"
            + (f" baseUrl={required_base_url!r}" if required_base_url else "")
            + f", but the persisted LLM settings are provider={persisted_provider!r} "
            f"baseUrl={persisted_base_url!r}. Configure the matching "
            "provider via the LLM Settings panel (POST /llm/settings) "
            "before recording this arm."
        )

    _, _, api_key = llm_gateway.resolve_active_provider(settings, master_secret)
    if not api_key:
        raise LiveCredentialError(
            f"arm {arm.id!r}: persisted LLM settings matched provider "
            f"{real_tag!r} but no API key could be decrypted (wrong "
            "LLM_MASTER_SECRET, or apiKey missing/corrupt)."
        )

    resolved_base_url = required_base_url or persisted_base_url
    adapter = llm_gateway.get_adapter(real_tag, resolved_base_url)
    return adapter, api_key, real_tag, resolved_base_url


def estimate_usd_cost(real_provider: str, model: "str | None", usage: "dict[str, Any] | None") -> float:
    """Approximate USD cost from a REAL usage dict (`prompt_tokens`/
    `completion_tokens`, both real token counts from the live response) and
    a looked-up $/MTok rate. Returns 0.0 for an unlisted (provider, model)
    pair rather than raising -- a missing price must never block recording."""
    if not usage or not model:
        return 0.0
    rates = USD_PER_MTOK.get((real_provider, model))
    if rates is None:
        return 0.0
    prompt_tokens = usage.get("prompt_tokens", 0) or 0
    completion_tokens = usage.get("completion_tokens", 0) or 0
    return (prompt_tokens / 1_000_000.0) * rates["input"] + (completion_tokens / 1_000_000.0) * rates["output"]


@dataclass(frozen=True)
class AttemptCost:
    """One real LLM call's token usage + approximate cost -- the record
    underlying Task 3's "actual cost and total token usage" requirement."""

    arm_id: str
    corpus: str
    permutation_index: int
    real_provider: str
    model: "str | None"
    prompt_tokens: int
    completion_tokens: int
    total_tokens: int
    usd_cost: float


class UsageTrackingAdapter:
    """Drop-in `LLMAdapter`-shaped wrapper (same `generate(req, api_key,
    options=None)` signature) that passes every call through to `wrapped`
    unchanged and records the REAL response usage/cost into `sink` as a
    side effect. Purely an observer: never mutates the request or the
    response, so it is transparent to `CassetteAdapter` on either side."""

    def __init__(
        self,
        wrapped: "Any",
        sink: "list[AttemptCost]",
        *,
        arm_id: str,
        corpus: str,
        permutation_index: int,
        real_provider: str,
    ) -> None:
        self._wrapped = wrapped
        self._sink = sink
        self._arm_id = arm_id
        self._corpus = corpus
        self._permutation_index = permutation_index
        self._real_provider = real_provider

    def generate(self, req: "Any", api_key: "str | None", options: "Any" = None) -> "Any":
        response = self._wrapped.generate(req, api_key, options)
        usage = response.usage or {}
        self._sink.append(
            AttemptCost(
                arm_id=self._arm_id,
                corpus=self._corpus,
                permutation_index=self._permutation_index,
                real_provider=self._real_provider,
                model=response.model,
                prompt_tokens=usage.get("prompt_tokens", 0) or 0,
                completion_tokens=usage.get("completion_tokens", 0) or 0,
                total_tokens=usage.get("total_tokens", 0) or 0,
                usd_cost=estimate_usd_cost(self._real_provider, response.model, usage),
            )
        )
        return response

    def list_models(self, api_key: "str | None" = None) -> "list[str]":
        return self._wrapped.list_models(api_key)


def few_shot_permutations(examples: "list[dict[str, Any]]", n: int = 3) -> "list[list[dict[str, Any]]]":
    """3 FIXED, deterministic orderings of a few-shot example list (never a
    random shuffle -- reproducibility requires the same orderings every
    run, per `frame_recognition_fewshot.json`'s own `exampleOrderNote` and
    35-AI-SPEC.md 5's "Example-order sub-sweep": Lu et al. ACL 2022 --
    permuting the same demonstrations swings accuracy from near-SOTA to
    near-chance).

    Permutation 0: the as-authored order, unchanged.
    Permutation 1: fully reversed.
    Permutation 2: rotated by half the list length (a different adjacency
    structure than a plain reversal -- the abstention example's neighbors
    change on every one of the 3 orderings).
    """
    perms: "list[list[dict[str, Any]]]" = [list(examples)]
    if n >= 2:
        perms.append(list(reversed(examples)))
    if n >= 3 and examples:
        k = len(examples) // 2 or 1
        perms.append(list(examples[k:]) + list(examples[:k]))
    return perms[:n]


@dataclass
class ArmCorpusOutcome:
    """What happened for one (arm, corpus) combo: either every requested
    permutation recorded and scored, or the whole combo was skipped with a
    named reason (never a silent drop)."""

    arm_id: str
    corpus: str
    status: str  # "recorded" | "skipped_credentials" | "skipped_invalid" | "skipped_corpus_load_failed"
    detail: str
    permutations: "list[dict[str, Any]]" = field(default_factory=list)


@dataclass
class LiveSweepResult:
    outcomes: "list[ArmCorpusOutcome]"
    costs: "list[AttemptCost]"

    @property
    def total_usd_cost(self) -> float:
        return sum(c.usd_cost for c in self.costs)

    @property
    def total_tokens(self) -> int:
        return sum(c.total_tokens for c in self.costs)


def run_live_sweep(
    arm_ids: "list[str]",
    corpus_names: "list[str]",
    *,
    permutations: int = 1,
    mode: "str | None" = None,
) -> LiveSweepResult:
    """Drive `arms.run_arm()` through a REAL adapter (never the eval
    harness's `"test-api-key"` placeholder) for every requested (arm,
    corpus) combo, recording each attempt's response into a cassette via
    `CassetteAdapter(mode=...)` and scoring it immediately with
    `report._compute_scored_row` (reused, not re-implemented) so a
    permutation sub-sweep's per-ordering M1 is available without a second
    replay pass.

    `mode` defaults to `RECOGNITION_EVAL_MODE` (must be `record` or `live`
    for this function to make any live call -- `replay` is rejected
    immediately, since this driver's entire purpose is making live calls).
    """
    resolved_mode = mode if mode is not None else os.environ.get("RECOGNITION_EVAL_MODE", "replay")
    if resolved_mode not in ("record", "live"):
        raise cassette_module.CassetteWriteError(
            f"run_live_sweep requires RECOGNITION_EVAL_MODE=record or =live "
            f"(got {resolved_mode!r}). Set the env var explicitly -- this "
            "driver never falls back to replay."
        )

    outcomes: "list[ArmCorpusOutcome]" = []
    costs: "list[AttemptCost]" = []

    corpora_cache: "dict[str, Any]" = {}

    for corpus_name in corpus_names:
        if corpus_name not in corpora_cache:
            try:
                corpus_obj = corpus_module.load(corpus_name)
                corpus_module.assert_context_unchanged(corpus_obj)
                corpora_cache[corpus_name] = corpus_obj
            except (FileNotFoundError, corpus_module.ProvenanceError) as exc:
                corpora_cache[corpus_name] = exc
        corpus_result = corpora_cache[corpus_name]

        for arm_id in arm_ids:
            if isinstance(corpus_result, Exception):
                outcomes.append(
                    ArmCorpusOutcome(
                        arm_id=arm_id,
                        corpus=corpus_name,
                        status="skipped_corpus_load_failed",
                        detail=f"corpus load failed: {corpus_result}",
                    )
                )
                continue

            corpus_obj = corpus_result
            arm = arms_module.ARMS.get(arm_id)
            if arm is None:
                outcomes.append(
                    ArmCorpusOutcome(arm_id=arm_id, corpus=corpus_name, status="skipped_invalid", detail="unknown arm id")
                )
                continue

            try:
                real_adapter, api_key, real_provider, _real_base_url = resolve_live_adapter_and_key(arm)
            except LiveCredentialError as exc:
                outcomes.append(
                    ArmCorpusOutcome(arm_id=arm_id, corpus=corpus_name, status="skipped_credentials", detail=str(exc))
                )
                continue

            # Shared with report.py (arms.resolve_real_negotiated_mode) so
            # both the record path and the replay path compute the IDENTICAL
            # negotiated mode -- and therefore the identical cassette key.
            # NEVER assume "json_schema_strict" just because
            # `arm.structured_output` is True: that assumption 400s outright
            # against DeepSeek ("This response_format type is unavailable
            # now", discovered live running A4 during 35-15 Task 2).
            negotiated_mode = arms_module.resolve_real_negotiated_mode(arm)

            perm_examples: "list[list[dict[str, Any]] | None]"
            if permutations > 1:
                base_artifacts = arms_module.resolve_arm_artifacts(arm)
                perm_examples = list(few_shot_permutations(base_artifacts.few_shot_examples, n=permutations))
            else:
                perm_examples = [None]

            perm_rows: "list[dict[str, Any]]" = []
            for perm_idx, override in enumerate(perm_examples):
                tracking_adapter = UsageTrackingAdapter(
                    real_adapter,
                    costs,
                    arm_id=arm_id,
                    corpus=corpus_name,
                    permutation_index=perm_idx,
                    real_provider=real_provider,
                )
                cassette_adapter = cassette_module.CassetteAdapter(
                    arm_id,
                    tracking_adapter,
                    negotiated_mode=negotiated_mode,
                    prompt_version=cg_recognition.PROMPT_VERSION,
                    ip_class=corpus_obj.ip_class,
                    mode=resolved_mode,
                )

                outcome = arms_module.run_arm(
                    arm,
                    corpus_obj,
                    cassette_adapter,
                    few_shot_examples_override=override,
                    api_key_override=api_key,
                    negotiated_mode_override=negotiated_mode,
                )
                corpus_module.assert_provenance(outcome["provenance"])  # refuses to score an incomplete row

                result = outcome["result"]
                row: "dict[str, Any]" = {
                    "permutation_index": perm_idx,
                    "valid": bool(result.get("valid")),
                }
                if result.get("valid"):
                    scored = report_module._compute_scored_row(corpus_obj, arm, outcome)
                    row["m1"] = scored.m1
                    row["m1_successes"] = scored.m1_successes
                    row["n_blocks"] = scored.n_blocks
                    row["grammar_citation_rate"] = scored.grammar_citation_rate
                else:
                    row["violations"] = result.get("violations")
                perm_rows.append(row)

            outcomes.append(
                ArmCorpusOutcome(arm_id=arm_id, corpus=corpus_name, status="recorded", detail="", permutations=perm_rows)
            )

    return LiveSweepResult(outcomes=outcomes, costs=costs)
