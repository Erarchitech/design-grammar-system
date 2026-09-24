"""D-09/D-10/D-13/D-17/D-21 LLM repeatability measurement driver (plan 1204-07).

Two D-09 subjects are measured at k=10 samples per item per provider:

- `SUBJECT_RECOGNITION` -- `data-service/cg_recognition.py::recognize_structure`;
- `SUBJECT_RULE_INGEST` -- `data-service/dg_context.py::generate_validated_cypher`.

Design constraints, mirroring `live_sweep.py` (the analog: modelled on, never
called) rather than importing it:

- Adapter resolution happens ONCE per provider, never per sample --
  `resolve_adapter_once()` returns an instance the caller reuses for every one
  of that provider's k samples.
- Each sample s in 1..REPEAT_SAMPLES draws through
  `CassetteAdapter(sample_index=s)`. Sample index 0 is NEVER used: 0 means the
  legacy eight-part cassette key (1204-03), so using it here would replay one
  sample ten times instead of measuring ten samples (D-21).
- Every sample is classified by `outcome_taxonomy.classify` on a
  single-attempt list and stamped with the `LLM_SAMPLE_PROVENANCE_FIELDS`
  block, validated by `assert_llm_sample_provenance` (D-19).
- Rule-ingest calls send NO `GenerationOptions`, so the report records
  temperature as "not sent - provider default" (D-10, `record_temperature`).
- Rates are computed per provider as their own stratum and are NEVER pooled
  (D-13); any rate over fewer than `MIN_SAMPLE_FLOOR` samples renders
  `INSUFFICIENT_SAMPLES` instead of a number.
- `OUTCOME_STATUSES` verdict vocabulary never reaches a repeatability record:
  that is `live_sweep.py`'s run-status set, a different artifact entirely.

Test-only, deliberately: this package lives under `data-service/tests/` so no
production module can import it (D-10).
"""

from __future__ import annotations

import hashlib
import json
import sys
from collections import Counter
from urllib.parse import urlparse
from pathlib import Path
from typing import Any, Callable

# data-service/tests/recognition_eval/repeat_sweep.py -> parents[2] == data-service/
_DATA_SERVICE_ROOT = str(Path(__file__).resolve().parents[2])
if _DATA_SERVICE_ROOT not in sys.path:
    sys.path.insert(0, _DATA_SERVICE_ROOT)

import canonical_json  # noqa: E402

from llm_gateway import GenerateRequest, GenerateResponse  # noqa: E402

from recognition_eval import cassette as cassette_module  # noqa: E402
from recognition_eval import outcome_taxonomy  # noqa: E402
from recognition_eval import scoring  # noqa: E402
from recognition_eval.cassette import CassetteAdapter  # noqa: E402
from recognition_eval.corpus import (  # noqa: E402
    LLM_SAMPLE_PROVENANCE_FIELDS,
    assert_llm_sample_provenance,
)
from recognition_eval.outcome_taxonomy import OUTCOME_LABELS, classify  # noqa: E402

# -- D-13: k and the min-5 sample floor --

# D-13 fixes k=10 samples per item per provider.
REPEAT_SAMPLES = 10

# D-13's min-5 floor: below this many samples a rate is not reportable and
# renders `INSUFFICIENT_SAMPLES` instead of a spuriously precise number.
MIN_SAMPLE_FLOOR = 5

# The exact string a gated cell carries (D-13). Never a number, never "0%".
INSUFFICIENT_SAMPLES = "insufficient samples"

# D-10: the exact recorded value for a subject that sends no GenerationOptions.
TEMPERATURE_NOT_SENT = "not sent \u2014 provider default"

# -- D-09: the two subjects --

SUBJECT_RECOGNITION = "recognition"
SUBJECT_RULE_INGEST = "rule_ingest"

# `outcome_taxonomy.classify` spells the recognition subject with a hyphen;
# repeat_sweep spells it with an underscore. One mapping, one place.
_TAXONOMY_SUBJECT = {
    SUBJECT_RECOGNITION: "recognition",
    SUBJECT_RULE_INGEST: "rule-ingest",
}

_SUBJECTS = (SUBJECT_RECOGNITION, SUBJECT_RULE_INGEST)


def mask_url(url: "str | None") -> str:
    """Reduce a base_url to `scheme://host/...` for logging/storage.

    Lifted from `live_sweep.mask_url` and kept as the identical convention,
    but defined here rather than imported: importing `live_sweep` would pull
    `arms`/`cg_recognition`/`llm_gateway` live-resolution machinery into a
    module that must stay hermetic under `-k "not live"`
    (T-1204-07-01: a credentialed URL in a report or cassette is a high
    finding, and `baseUrl` routinely carries the credential inline).

    `None` renders as its repr (never the empty string), so "not configured"
    stays distinguishable from "configured empty".
    """
    if not url:
        return repr(url)
    try:
        parsed = urlparse(url)
    except ValueError:
        return "<unparseable-url>"
    if not parsed.hostname:
        return "<masked-url>"
    scheme = f"{parsed.scheme}://" if parsed.scheme else ""
    if parsed.path.strip("/") or parsed.query:
        return f"{scheme}{parsed.hostname}/..."
    return f"{scheme}{parsed.hostname}"


class RepeatSweepError(RuntimeError):
    """Raised for a driver-level misuse -- an unknown subject, or an item that
    does not carry the inputs its subject needs."""


def _taxonomy_subject(subject: str) -> str:
    """Translate this module's subject spelling to `outcome_taxonomy`'s."""
    try:
        return _TAXONOMY_SUBJECT[subject]
    except KeyError:
        raise RepeatSweepError(
            f"unknown subject {subject!r} -- expected one of {_SUBJECTS!r} "
            "(D-09)."
        ) from None


# -- Task 1: resolve-once, run-one-item, run-the-sweep --


def resolve_adapter_once(
    provider: str,
    model: str | None = None,
    *,
    factory: "Callable[[str, str | None], Any] | None" = None,
) -> Any:
    """Resolve ONE adapter instance for `provider`, reused for every one of
    that provider's k samples.

    Resolution is a per-provider concern: an adapter that re-resolved per
    sample would re-authenticate (or re-fork a subprocess) k times and could
    silently drift to a different endpoint mid-item, which would make the
    measured disagreement unattributable to the model.

    `factory` is the injection point. Tests pass a fake factory (or drive
    `run_repeat_sweep(adapter_factory=...)`) so nothing here reaches a
    network; live resolution is plan 1204-09's concern and is deliberately
    NOT implemented in this module.
    """
    if factory is None:
        raise RepeatSweepError(
            f"no adapter factory supplied for provider {provider!r} -- "
            "repeat_sweep never constructs a live adapter itself (live "
            "resolution is plan 1204-09's concern; tests inject a fake)."
        )
    return factory(provider, model)


def _build_request(item: dict, subject: str) -> GenerateRequest:
    """Build the single `GenerateRequest` this sample draws against.

    Read from the item, never fabricated: the request body is part of the
    cassette key, so inventing a prompt here would key a cassette nothing
    ever recorded.
    """
    if subject == SUBJECT_RECOGNITION:
        prompt = item.get("prompt")
        system = item.get("system")
    elif subject == SUBJECT_RULE_INGEST:
        prompt = item.get("rule_text")
        system = item.get("system")
    else:  # pragma: no cover - _taxonomy_subject already guards this
        raise RepeatSweepError(f"unknown subject {subject!r}.")

    if not isinstance(prompt, str) or not prompt:
        raise RepeatSweepError(
            f"item {item.get('item_id')!r} carries no prompt text for subject "
            f"{subject!r} -- expected a non-empty "
            f"{'prompt' if subject == SUBJECT_RECOGNITION else 'rule_text'} "
            "field; an empty prompt would hash a cassette key nothing can "
            "match."
        )
    return GenerateRequest(
        provider=item.get("provider") or "",
        model=item.get("model"),
        system=system,
        prompt=prompt,
    )


def _attempt_record(item: dict, response: "GenerateResponse", subject: str) -> dict:
    """The single attempt record `classify()` is asked about.

    The driver drives ONE generation per sample (the retry loop belongs to
    the subjects' own production code, not here), so this is a single-element
    attempt list. `valid` comes from the item's own deterministic validity
    oracle (D-18) -- NEVER from an expected label.
    """
    attempt: dict[str, Any] = {
        "valid": item.get("valid"),
        "truncated": getattr(response, "truncated", False),
        "finish_reason": getattr(response, "finish_reason", None),
        "abstained": bool(item.get("abstained", False)),
        "provider_error": bool(item.get("provider_error", False)),
    }
    violation_code = item.get("violation_code")
    if violation_code is not None:
        attempt["violation_code"] = violation_code
    return attempt


def _provenance_block(
    item: dict,
    response: "GenerateResponse",
    *,
    subject: str,
    provider: str,
    model: str | None,
    sample_index: int,
    adapter_name: str,
    negotiated_mode: str,
    raw_output: str,
) -> dict:
    """Assemble (and D-19-validate) one sample's provenance block.

    Only the non-secret `LLM_SAMPLE_PROVENANCE_FIELDS` block is carried --
    never the raw request, never an API key. The endpoint is a bare host, and
    any URL-shaped input is routed through `mask_url` first
    (T-1204-07-01).
    """
    sampling_params = record_temperature(subject)
    provenance: dict[str, Any] = {
        "adapter": adapter_name,
        "endpointHost": mask_url(item.get("base_url")),
        "requestedModelId": model,
        "promptFilePath": item.get("prompt_file_path"),
        "promptSha256": item.get("prompt_sha256"),
        "promptVersion": item.get("prompt_version"),
        "renderedRequestSha256": hashlib.sha256(
            _build_request(item, subject).model_dump_json().encode("utf-8")
        ).hexdigest(),
        "samplingParamsAsSent": (
            sampling_params
            if isinstance(sampling_params, dict)
            else {"temperature": sampling_params}
        ),
        "negotiatedMode": negotiated_mode,
        "gatewayCommit": item.get("gateway_commit"),
        "serviceCommit": item.get("service_commit"),
        "inputSha256": getattr(response, "response_id", None) or sample_input_sha256(item, subject),
        "sampleIndex": sample_index,
        "timestamp": item.get("timestamp"),
        "usage": dict(getattr(response, "usage", None) or {}),
        "finishReason": getattr(response, "finish_reason", None),
        # 1204-02 provider-attested fields, read verbatim; None means the
        # provider omitted them (the gateway never fabricates a value).
        "servedModelId": getattr(response, "served_model", None),
        "responseId": getattr(response, "response_id", None),
        "systemFingerprint": getattr(response, "system_fingerprint", None),
        "ollamaWeightsDigest": item.get("ollama_weights_digest"),
    }
    assert_llm_sample_provenance(provenance)
    return provenance


def sample_input_sha256(item: dict, subject: str) -> str:
    """Stable sha256 over the sample's INPUT (the rendered request body).

    Named separately so `_provenance_block` never has to invent a value for
    `inputSha256` when the provider returns no response id.
    """
    request = _build_request(item, subject)
    payload = json.dumps(
        {
            "system": request.system,
            "prompt": request.prompt,
            "provider": request.provider,
            "model": request.model,
        },
        sort_keys=True,
        separators=(",", ":"),
    )
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def run_one_item(
    item: dict,
    provider: str,
    model: str | None,
    adapter: Any,
    *,
    subject: str = SUBJECT_RECOGNITION,
    samples: int = REPEAT_SAMPLES,
    arm_id: str | None = None,
    negotiated_mode: str = "json_schema_strict",
    prompt_version: str | None = None,
    ip_class: str = "own",
    adapter_name: str | None = None,
    mode: str | None = None,
) -> list[dict]:
    """Drive ONE item through `samples` draws for ONE provider.

    Sample s (1..samples) is drawn through `CassetteAdapter(sample_index=s)`
    so each draw resolves a DISTINCT cassette key. Index 0 is never used --
    see the module docstring.

    Returns one record per sample, each carrying the item/provider/model
    identity, the sample index, the classified outcome (including D-15's
    first-attempt outcome and attempt count), the 1204-02 provider-attested
    fields, the raw output at level 1, and the D-19-validated provenance
    block.
    """
    taxonomy_subject = _taxonomy_subject(subject)
    request = _build_request(item, subject)
    records: list[dict[str, Any]] = []

    for sample_index in range(1, samples + 1):
        cassettes = CassetteAdapter(
            arm_id or item.get("arm_id") or "llm_repeatability",
            adapter,
            negotiated_mode=negotiated_mode,
            prompt_version=prompt_version or item.get("prompt_version") or "v1",
            ip_class=ip_class,
            mode=mode,
            sample_index=sample_index,
        )

        # D-10: rule-ingest sends NO GenerationOptions at all -- so the
        # cassette key's temperature/maxTokens parts stay empty and the
        # recorded value is the "not sent" sentinel, never a default.
        options = None
        response = cassettes.generate(request, item.get("api_key"), options)

        raw_output = response.text
        classification = classify(
            [_attempt_record(item, response, subject)], taxonomy_subject
        )

        record: dict[str, Any] = {
            "item_id": item.get("item_id"),
            "subject": subject,
            "provider": provider,
            "model": model,
            "model_requested": model,
            "sample_index": sample_index,
            # D-15: both levels, so the first-attempt invalid rate the retry
            # loop hides stays reportable.
            "outcome": classification.final_outcome,
            "first_attempt_outcome": classification.first_attempt_outcome,
            "attempts": classification.attempts,
            "violation_code": classification.violation_code,
            # 1204-02 provider-attested identity.
            "served_model": getattr(response, "served_model", None),
            "response_id": getattr(response, "response_id", None),
            "system_fingerprint": getattr(response, "system_fingerprint", None),
            # D-17 level 1: the raw bytes, un-normalised.
            "raw_output": raw_output,
            "raw_output_sha256": hashlib.sha256(
                raw_output.encode("utf-8")
            ).hexdigest(),
            "temperature": record_temperature(subject),
        }
        record["provenance"] = _provenance_block(
            item,
            response,
            subject=subject,
            provider=provider,
            model=model,
            sample_index=sample_index,
            adapter_name=adapter_name or f"cassette:{arm_id or item.get('arm_id') or 'llm_repeatability'}",
            negotiated_mode=negotiated_mode,
            raw_output=raw_output,
        )
        records.append(record)

    return records


def run_repeat_sweep(
    items: list[dict],
    providers: list[Any],
    *,
    subject: str = SUBJECT_RECOGNITION,
    samples: int = REPEAT_SAMPLES,
    adapter_factory: "Callable[[str, str | None], Any] | None" = None,
    adapters: "dict[str, Any] | None" = None,
    resolved_adapters: "dict[str, Any] | None" = None,
    **kwargs: Any,
) -> dict:
    """Drive every (item, provider) pair for `subject`.

    Returns a dict with:

    - `records` -- the flat per-sample records from `run_one_item`;
    - `by_item` -- records grouped by item id;
    - `metrics` -- pure `compute_item_metrics` output per item (Task 2);
    - `resolved_adapters` -- the provider -> adapter map, so a test can
      assert `resolve_adapter_once` ran EXACTLY ONCE per provider.
    """
    _taxonomy_subject(subject)

    if resolved_adapters is None:
        resolved_adapters = {}
    if adapters is None and adapter_factory is None:
        raise RepeatSweepError(
            "run_repeat_sweep needs either an `adapter_factory` or an "
            "`adapters` map -- it never constructs a live adapter itself."
        )

    records: list[dict[str, Any]] = []

    for provider_spec in providers:
        if isinstance(provider_spec, str):
            provider = provider_spec
            model = None
        else:
            provider = provider_spec.get("provider")
            model = provider_spec.get("model")

        # Resolution happens ONCE per provider here, outside the item loop.
        if provider not in resolved_adapters:
            if adapters is not None:
                resolved_adapters[provider] = adapters[provider]
            else:
                resolved_adapters[provider] = resolve_adapter_once(
                    provider, model, factory=adapter_factory
                )
        adapter = resolved_adapters[provider]

        for item in items:
            records.extend(
                run_one_item(
                    item,
                    provider,
                    model,
                    adapter,
                    subject=subject,
                    samples=samples,
                    **kwargs,
                )
            )

    by_item: dict[Any, list[dict]] = {}
    for record in records:
        by_item.setdefault(record["item_id"], []).append(record)

    return {
        "subject": subject,
        "samples": samples,
        "records": records,
        "by_item": by_item,
        "metrics": {
            item_id: compute_item_metrics(item_id, item_records)
            for item_id, item_records in by_item.items()
        },
        "resolved_adapters": resolved_adapters,
    }

# ── Task 2: D-10 temperature recording ──


def record_temperature(subject: str, sampling_params: "dict[str, Any] | None" = None) -> Any:
    """D-10: record the sampling parameters AS SENT.

    Rule-ingest calls `generate_validated_cypher()` WITHOUT a
    `GenerationOptions` object, so no temperature is ever sent and the honest
    record is the `TEMPERATURE_NOT_SENT` sentinel -- never a plausible-looking
    provider default the harness never actually requested. Recognition passes
    its sampling params through and they are recorded verbatim.
    """
    _taxonomy_subject(subject)
    if subject == SUBJECT_RULE_INGEST:
        return TEMPERATURE_NOT_SENT
    return sampling_params if sampling_params is not None else {}


# ── Task 2: D-17 two-level normalization ──


def normalize_level2(subject: str, raw_output: str) -> str:
    """D-17 level-2 normalization: the DECLARED comparison per subject.

    Level 1 is the raw bytes (identity). Level 2 is what the subject's
    declared equivalence says two outputs mean the same thing:

    - `SUBJECT_RECOGNITION` -- canonical JSON of the PARSED recognition
      blocks, so key order and insignificant whitespace stop counting as
      disagreement while a real structural difference still does. Reuses
      `canonical_json.canonicalize` (never a second canonicalizer).
    - `SUBJECT_RULE_INGEST` -- whitespace-normalized Cypher: `" ".join(text.split())`,
      because the ingest subject's declared equivalence is "same statement,
      same tokens, indifferent layout".

    An unsupported subject raises KeyError.
    """
    if subject == SUBJECT_RECOGNITION:
        parsed = json.loads(raw_output)
        return canonical_json.canonicalize(parsed)
    if subject == SUBJECT_RULE_INGEST:
        return " ".join(raw_output.split())
    raise KeyError(
        f"no level-2 normalization declared for subject {subject!r} -- "
        f"expected one of {_SUBJECTS!r} (D-17)."
    )


# ── Task 2: D-13/D-17 per-provider metrics ──


def _strata(records: list[dict]) -> dict:
    """Group records into one stratum per provider -- NEVER a combined cell."""
    strata: dict[str, list[dict]] = {}
    for record in records:
        strata.setdefault(record["provider"], []).append(record)
    return strata


def _rate_cell(successes: int, n: int) -> Any:
    """A gated rate: `INSUFFICIENT_SAMPLES` below the D-13 min-5 floor."""
    if n < MIN_SAMPLE_FLOOR:
        return INSUFFICIENT_SAMPLES
    return successes / n


def _wilson_cell(modal_count: int, n: int) -> Any:
    """A gated Wilson CI, via `scoring.wilson_interval` and its INTEGER
    successes count -- never a proportion (scoring.py's own contract)."""
    if n < MIN_SAMPLE_FLOOR:
        return INSUFFICIENT_SAMPLES
    lower, upper = scoring.wilson_interval(modal_count, n)
    return {"lower": lower, "upper": upper, "n": n, "modal_count": modal_count}


def compute_item_metrics(item: Any, records: list[dict]) -> dict:
    """D-13/D-17 metrics for one item.

    Keyed BY PROVIDER STRATUM. There is deliberately no combined/"all"
    cell: pooling two providers' rates would average away exactly the
    per-provider instability this benchmark exists to measure (D-13).

    Per stratum of n samples:

    - `level1_distinct` -- distinct count over the raw bytes;
    - `level2_distinct` -- distinct count over `normalize_level2`;
    - `modal_level2` / `modal_count` -- the most common level-2 output and
      its integer count;
    - `modal_agreement_rate` -- `modal_count / n`, floored per D-13;
    - `modal_agreement_wilson` -- the 95% CI via
      `scoring.wilson_interval(modal_count, n)` (integers), floored per D-13;
    - `outcome_counts` -- the D-14 outcome tally (never verdict statuses).
    """
    subject = records[0]["subject"] if records else SUBJECT_RECOGNITION
    metrics: dict[str, Any] = {"item_id": item, "subject": subject, "strata": {}}

    for provider, stratum in _strata(records).items():
        n = len(stratum)
        level1 = [r["raw_output"] for r in stratum]

        level2: list[str] = []
        for record in stratum:
            try:
                level2.append(normalize_level2(record["subject"], record["raw_output"]))
            except (json.JSONDecodeError, TypeError, KeyError):
                # An unparseable output is its own level-2 value, not a crash:
                # a run that cannot be parsed is a real (maximal) disagreement
                # and must still be counted, not silently dropped.
                level2.append(f"<unparseable:{record['raw_output_sha256']}>")

        counts = Counter(level2)
        modal_level2, modal_count = counts.most_common(1)[0] if counts else ("", 0)

        metrics["strata"][provider] = {
            "provider": provider,
            "n": n,
            "level1_distinct": len(set(level1)),
            "level2_distinct": len(counts),
            "modal_level2": modal_level2,
            "modal_count": modal_count,
            "level1_agreement_rate": _rate_cell(
                Counter(level1).most_common(1)[0][1] if level1 else 0, n
            ),
            "modal_agreement_rate": _rate_cell(modal_count, n),
            "modal_agreement_wilson": _wilson_cell(modal_count, n),
            "outcome_counts": dict(Counter(r["outcome"] for r in stratum)),
            "first_attempt_outcome_counts": dict(
                Counter(r["first_attempt_outcome"] for r in stratum)
            ),
            "temperature": stratum[0].get("temperature"),
        }

    return metrics
