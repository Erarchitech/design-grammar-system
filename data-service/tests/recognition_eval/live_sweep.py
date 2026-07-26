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

import json
import os
import sys
from dataclasses import dataclass, field
from urllib.parse import urlparse
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


def mask_url(url: "str | None") -> str:
    """Reduce a base_url to `scheme://host` for logging. `baseUrl` is not a
    secret by design, but the OpenAI-compatible endpoints `REAL_ADAPTER_MAP`
    exists to support routinely carry the credential IN the URL (gateway/proxy
    path segments, Azure's `?api-key=`, self-hosted routers with an embedded
    token), and this value reaches stdout and CI logs. Mirrors the project's
    own `llm_gateway.mask_key` convention: never interpolate a
    possibly-credentialed value verbatim."""
    if not url:
        return repr(url)
    try:
        parsed = urlparse(url)
    except ValueError:
        return "<unparseable-url>"
    if not parsed.hostname:
        return "<masked-url>"
    scheme = f"{parsed.scheme}://" if parsed.scheme else ""
    return f"{scheme}{parsed.hostname}/..." if (parsed.path.strip("/") or parsed.query) else f"{scheme}{parsed.hostname}"


# The literal `test_recognition_eval.py` setdefault()s at import so the free
# replay suite can run without any real configuration. It must never reach a
# record/live sweep, where it silently decrypts nothing.
_PLACEHOLDER_MASTER_SECRET = "test-master-secret"


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
            + (f" baseUrl={mask_url(required_base_url)}" if required_base_url else "")
            + f", but the persisted LLM settings are provider={persisted_provider!r} "
            f"baseUrl={mask_url(persisted_base_url)}. Configure the matching "
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


def estimate_usd_cost_priced(
    real_provider: str, model: "str | None", usage: "dict[str, Any] | None"
) -> "tuple[float, bool]":
    """Approximate USD cost from a REAL usage dict (`prompt_tokens`/
    `completion_tokens`, both real token counts from the live response) and a
    looked-up $/MTok rate.

    Returns `(cost, priced)`. A missing price must never block recording, so
    an unlisted (provider, model) pair still yields 0.0 -- but it is flagged
    `priced=False` rather than being indistinguishable from a genuinely free
    call. `USD_PER_MTOK` has exactly two entries, so a model rename, an
    OpenAI-compatible endpoint swap, or an Anthropic response echoing a dated
    model id (`claude-sonnet-5-2026xxxx`) would otherwise under-report the
    headline cost by exactly the unpriced volume while still looking
    authoritative -- the same silent drop the rest of this harness (cassette
    misses, provenance refusal, `SkippedRow`) is built to refuse."""
    if not usage or not model:
        return 0.0, False
    rates = USD_PER_MTOK.get((real_provider, model))
    if rates is None:
        return 0.0, False
    prompt_tokens = usage.get("prompt_tokens", 0) or 0
    completion_tokens = usage.get("completion_tokens", 0) or 0
    cost = (prompt_tokens / 1_000_000.0) * rates["input"] + (completion_tokens / 1_000_000.0) * rates["output"]
    return cost, True


def estimate_usd_cost(real_provider: str, model: "str | None", usage: "dict[str, Any] | None") -> float:
    """Cost-only view of `estimate_usd_cost_priced` (kept for callers that
    only need the number). Prefer the `_priced` variant anywhere the result is
    reported, so an unpriced call is never presented as a free one."""
    return estimate_usd_cost_priced(real_provider, model, usage)[0]


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
    priced: bool = True
    """False when no `USD_PER_MTOK` rate existed for this (provider, model) --
    `usd_cost` is then 0.0 because the price is UNKNOWN, not because the call
    was free. Reported separately so the headline total is never silently
    short by the unpriced volume."""


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
        usd_cost, priced = estimate_usd_cost_priced(self._real_provider, response.model, usage)
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
                usd_cost=usd_cost,
                priced=priced,
            )
        )
        return response

    def list_models(self, api_key: "str | None" = None) -> "list[str]":
        return self._wrapped.list_models(api_key)


# Lives in `arms.py` (the module that owns few-shot artifact resolution) so
# `report.py` can reuse it for the replay-side permutation sweep without
# importing this module -- `live_sweep` already imports `report`, so the other
# direction would be a cycle. Re-exported here: this is where the record path
# and every existing caller/test look for it.
few_shot_permutations = arms_module.few_shot_permutations


@dataclass
class ArmCorpusOutcome:
    """What happened for one (arm, corpus) combo: either every requested
    permutation recorded and scored, or the whole combo was skipped with a
    named reason (never a silent drop)."""

    arm_id: str
    corpus: str
    status: str
    """One of `OUTCOME_STATUSES`. `"failed"` means the combo raised after the
    money was already spent -- the attempt's cost is still in
    `LiveSweepResult.costs`."""
    detail: str
    permutations: "list[dict[str, Any]]" = field(default_factory=list)


OUTCOME_STATUSES = frozenset(
    {
        "recorded",
        "failed",
        "skipped_credentials",
        "skipped_invalid",
        "skipped_corpus_load_failed",
    }
)


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

    @property
    def unpriced(self) -> "list[AttemptCost]":
        """Calls whose (provider, model) had no `USD_PER_MTOK` rate. Non-empty
        means `total_usd_cost` is an UNDER-estimate by exactly this volume."""
        return [c for c in self.costs if not c.priced]

    def cost_summary(self) -> str:
        """One-line accounting suitable for stdout/CI. Always names the
        unpriced volume rather than letting it vanish into the total."""
        line = (
            f"total tokens={self.total_tokens} "
            f"approx_usd_cost={self.total_usd_cost:.4f} over {len(self.costs)} call(s)"
        )
        unpriced = self.unpriced
        if unpriced:
            pairs = sorted({f"{c.real_provider}/{c.model}" for c in unpriced})
            line += (
                f" -- WARNING: {len(unpriced)} call(s), "
                f"{sum(c.total_tokens for c in unpriced)} tokens UNPRICED "
                f"(no rate for {', '.join(pairs)}); the total above is an "
                "under-estimate by that volume"
            )
        return line


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
    `report.compute_scored_row` (reused, not re-implemented) so a
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

    # Validate at the entry point rather than letting `permutations=0` or a
    # negative value fall through to the single-ordering branch: the operator's
    # requested sweep size must never silently differ from what gets billed.
    if permutations < 1:
        raise ValueError(
            f"permutations must be >= 1 (got {permutations!r}): a sweep of "
            "zero orderings measures nothing."
        )

    # Fail loudly BEFORE spending anything if the master secret is the test
    # suite's own placeholder. `test_recognition_eval.py` runs
    # `os.environ.setdefault("LLM_MASTER_SECRET", "test-master-secret")` at
    # import, so an operator who runs the documented record command without
    # exporting the REAL secret would otherwise get a fake one injected: every
    # `resolve_active_provider` decrypt returns no key, every arm skips with a
    # credential error, and the run completes having recorded nothing while
    # looking like it ran. A misconfigured record run must be an error, not a
    # silent no-op.
    if os.environ.get("LLM_MASTER_SECRET", "") == _PLACEHOLDER_MASTER_SECRET:
        raise LiveCredentialError(
            f"LLM_MASTER_SECRET is the test placeholder "
            f"({_PLACEHOLDER_MASTER_SECRET!r}), which cannot decrypt any real "
            "persisted API key -- every arm would skip and the sweep would "
            "record nothing. Export the REAL master secret before running a "
            "record/live sweep."
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
            # Everything below has already passed the credential gate, so any
            # failure from here on happens AFTER money may have been spent.
            # Isolate it per-combo: an httpx 429/500, a ProvenanceError, a
            # RuntimeError from resolve_arm_artifacts' git subprocess or a
            # malformed-JSON blob must not propagate out of the loop, because
            # `LiveSweepResult` is only constructed at the end -- an escaping
            # exception would destroy the entire accumulated cost/token record
            # along with the frame, and (loop order being `for corpus: for
            # arm:`) would lose every remaining corpus too. This is what makes
            # the module docstring's "it never crashes the whole sweep" true
            # for more than just credential mismatches.
            try:
                negotiated_mode = arms_module.resolve_real_negotiated_mode(arm)

                perm_examples: "list[list[dict[str, Any]] | None]"
                shortfall_detail = ""
                if permutations > 1:
                    base_artifacts = arms_module.resolve_arm_artifacts(arm)
                    distinct = few_shot_permutations(base_artifacts.few_shot_examples, n=permutations)
                    perm_examples = list(distinct)
                    if len(distinct) < permutations:
                        # Name the shortfall instead of silently running fewer
                        # orderings -- or, worse, duplicate ones presented as
                        # independent samples. A reader of these rows must be
                        # able to tell "M1 was stable across 3 orderings" from
                        # "there was only ever 1 ordering to vary".
                        shortfall_detail = (
                            f"requested {permutations} orderings but only "
                            f"{len(distinct)} distinct ordering(s) exist "
                            f"(few-shot list has {len(base_artifacts.few_shot_examples)} "
                            "example(s)); ran the distinct ones only"
                        )
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
                        scored = report_module.compute_scored_row(corpus_obj, arm, outcome)
                        row["m1"] = scored.m1
                        row["m1_successes"] = scored.m1_successes
                        row["n_blocks"] = scored.n_blocks
                        row["grammar_citation_rate"] = scored.grammar_citation_rate
                    else:
                        row["violations"] = result.get("violations")
                    perm_rows.append(row)
            except Exception as exc:  # noqa: BLE001 -- deliberate: see comment above
                outcomes.append(
                    ArmCorpusOutcome(
                        arm_id=arm_id,
                        corpus=corpus_name,
                        status="failed",
                        detail=f"{type(exc).__name__}: {exc}",
                    )
                )
                continue

            outcomes.append(
                ArmCorpusOutcome(
                    arm_id=arm_id,
                    corpus=corpus_name,
                    status="recorded",
                    detail=shortfall_detail,
                    permutations=perm_rows,
                )
            )

    return LiveSweepResult(outcomes=outcomes, costs=costs)
