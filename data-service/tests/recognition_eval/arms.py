"""The A0-A5 ablation arm definitions for the recognition eval harness
(Phase 35-13, 35-AI-SPEC.md 5 "Ablation arms -- turning the spec's causal
claims into evidence").

Arms are configurations injected at the adapter and artifact boundary,
NEVER a forked pipeline: an arm supplies which few-shot fixture content to
use, whether a system prompt is set, whether Tier 0 runs, which
provider/model, and whether structured output is negotiated. `run_arm()`
patches those artifacts into `cg_recognition.recognize_structure()` at the
exact seams it already exposes (module-level loader functions, the
resolved-once provider/adapter/negotiated-mode triple, and
`cg_topology.classify`) rather than duplicating any of its retry-loop,
validation, or merge logic.

A0/A0f need the *as-shipped* prompt -- the pre-35-08 few-shot fixture and
the no-system-prompt condition -- which no longer exists in the working
tree (35-08 replaced it). `resolve_arm_artifacts()` reads it out of git by
resolving, AT RUN TIME, the commit that last touched
`data-service/fixtures/frame_recognition_fewshot.json` before the 35-08
replacement. It never hardcodes a guessed sha: an A0 that silently ran the
FIXED prompt instead of the broken one would invalidate the entire sweep,
so failure to resolve the sha raises rather than falling back to the
current fixture.
"""

from __future__ import annotations

import json
import os
import re
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any

# data-service/tests/recognition_eval/arms.py -> parents[2] == data-service/,
# where cg_recognition.py/cg_topology.py live. Inserted defensively (mirrors
# scoring.py/cassette.py) so this module imports correctly regardless of the
# invoking test's cwd/sys.path setup.
_DATA_SERVICE_ROOT = str(Path(__file__).resolve().parents[2])
if _DATA_SERVICE_ROOT not in sys.path:
    sys.path.insert(0, _DATA_SERVICE_ROOT)

import cg_recognition  # noqa: E402
import cg_topology  # noqa: E402
import llm_gateway  # noqa: E402
from llm_gateway import StructuredOutputCapability  # noqa: E402

# 35-AI-SPEC.md 5's arms table "provider" column ("deepseek"/"anthropic") is
# a plain provenance label on `Arm`, NOT an `llm_gateway.get_adapter()`
# provider tag. DeepSeek has no adapter class of its own (`get_adapter`
# registers exactly `anthropic`/`openai`/`ollama`) -- it is served through
# the OpenAI-compatible Chat Completions API with a custom base_url, exactly
# how the live `/llm/settings` panel already configures it. The single
# source of truth for that translation lives here (35-15) so both the live
# record-mode driver (`live_sweep.py`, which also needs a real API key) and
# the replay-only report sweep (`report.py`, which must NEVER touch a
# secret) agree on which real provider/base_url an arm resolves to.
REAL_ADAPTER_MAP: "dict[str, tuple[str, str | None]]" = {
    "deepseek": ("openai", "https://api.deepseek.com/v1"),
    "anthropic": ("anthropic", None),
}


def resolve_real_negotiated_mode(arm: "Arm") -> str:
    """The REAL structured-output mode this arm's (real provider, model,
    base_url) actually negotiates -- NEVER the naive `"json_schema_strict"
    if arm.structured_output else "none"` assumption, which 400s outright
    against DeepSeek (`llm_gateway.negotiate_structured_output`'s own
    docstring calls this "the DeepSeek trap": served through `OpenAIAdapter`
    so it LOOKS like OpenAI, but only accepts `response_format:
    {"type":"json_object"}`, never `json_schema`/`strict` -- confirmed live
    running arm A4 during 35-15 Task 2, `400 "This response_format type is
    unavailable now"`).

    Pure and hermetic: for every provider label in `REAL_ADAPTER_MAP`
    (`openai`/`anthropic`), `negotiate_structured_output` branches on
    `base_url`/model prefix alone, no network call -- only its `ollama`
    branch would probe a live endpoint, and no arm uses that label. Safe to
    call from `report.py`'s replay-only, no-secrets sweep as well as from
    `live_sweep.py`'s record-mode driver, so both compute the identical
    cassette key.

    That hermeticity claim is only true for labels actually IN
    `REAL_ADAPTER_MAP`, so the precondition is enforced rather than assumed:
    an unmapped label is refused up front instead of being silently reused as
    a real adapter tag. Guessing would either mis-key every cassette for that
    arm or -- for a label like `ollama` that `negotiate_structured_output`
    probes over HTTP -- put a live network call on `report.py`'s replay-only,
    no-secrets path, breaking the one guarantee this function's callers rely
    on. `live_sweep.resolve_live_adapter_and_key` already refuses the
    identical condition; the two now agree on the same input.
    """
    if arm.provider not in REAL_ADAPTER_MAP:
        raise ValueError(
            f"arm {arm.id!r}: no REAL_ADAPTER_MAP entry for provenance label "
            f"provider={arm.provider!r}; refusing to guess (a wrong guess "
            "either mis-keys every cassette for this arm or puts a live probe "
            "on the replay-only path). Add the mapping before using this arm."
        )
    if not arm.structured_output:
        return "none"
    real_tag, base_url = REAL_ADAPTER_MAP[arm.provider]
    return llm_gateway.negotiate_structured_output(real_tag, arm.model, base_url).mode

def few_shot_permutations(examples: "list[dict[str, Any]]", n: int = 3) -> "list[list[dict[str, Any]]]":
    """Up to `n` FIXED, deterministic, PAIRWISE-DISTINCT orderings of a
    few-shot example list (never a random shuffle -- reproducibility requires
    the same orderings every run, per `frame_recognition_fewshot.json`'s own
    `exampleOrderNote` and 35-AI-SPEC.md 5's "Example-order sub-sweep": Lu et
    al. ACL 2022 -- permuting the same demonstrations swings accuracy from
    near-SOTA to near-chance).

    Candidate 0: the as-authored order, unchanged.
    Candidate 1: fully reversed (needs >= 2 examples to differ).
    Candidate 2: rotated by half the list length (needs >= 3 to differ from
    both of the above -- a different adjacency structure than a plain
    reversal, so the abstention example's neighbors change on every ordering).

    **Duplicates are dropped, and that is the whole point.** Branching on `n`
    alone (the previous behavior) returned 3 IDENTICAL lists for a 1-example
    few-shot fixture, which arms A0/A0f use: `reversed([x]) == [x]`, and
    `k = 1//2 or 1` made the rotation `[x][1:] + [x][:1] == [x]` too. Every
    duplicate is a separately-billed live request that collides on the same
    cassette key (so the run looks like it produced 3 recordings and produced
    1) and, worst of all, lands in the report as an independent ordering --
    manufacturing a "M1 is stable across example orderings" result from a
    sub-sweep that never varied the order.

    Returns at least one ordering (the as-authored one) for any input,
    including an empty example list. Callers that asked for more orderings
    than exist must surface the shortfall by name -- see `run_live_sweep`.
    """
    if n < 1:
        raise ValueError(f"n must be >= 1 (got {n!r}): a sweep of zero orderings measures nothing.")

    candidates: "list[list[dict[str, Any]]]" = [list(examples)]
    if len(examples) >= 2:
        candidates.append(list(reversed(examples)))
    if len(examples) >= 3:
        k = len(examples) // 2
        candidates.append(list(examples[k:]) + list(examples[:k]))

    seen: "set[str]" = set()
    perms: "list[list[dict[str, Any]]]" = []
    for candidate in candidates:
        fingerprint = json.dumps(candidate, sort_keys=True, default=str)
        if fingerprint not in seen:
            seen.add(fingerprint)
            perms.append(candidate)
    return perms[:n]


# Path resolution mirrors dg_knowledge.py's _REPO_ROOT: inside the
# data-service Docker container the repo root (with its .git directory) is
# mounted read-only at /mnt/repo (docker-compose.yml's `.:/mnt/repo:ro`
# volume + `DG_KNOWLEDGE_REPO_ROOT: /mnt/repo` env var). Outside the
# container the env var is unset and this falls back to the path computed
# relative to this file (parents[3] == repo root).
_REPO_ROOT = Path(os.getenv("DG_KNOWLEDGE_REPO_ROOT", str(Path(__file__).resolve().parents[3])))

_FEWSHOT_FIXTURE_RELATIVE_PATH = "data-service/fixtures/frame_recognition_fewshot.json"

# The 35-08 commit subject line replaced the fixture with the counterexample
# shape ("feat(35-08): system prompt + counterexample few-shot ..."). Matching
# on the phase tag in the subject, not a hardcoded sha, is what makes this
# resolution survive a rebase/renumber of the commit itself.
_REPLACEMENT_COMMIT_MARKER = re.compile(r"35-08", re.IGNORECASE)

_pre_35_08_sha_cache: "str | None" = None


def _run_git(args: "list[str]") -> str:
    try:
        proc = subprocess.run(
            ["git", *args],
            cwd=str(_REPO_ROOT),
            capture_output=True,
            text=True,
            check=True,
            timeout=15,
        )
    except (OSError, subprocess.CalledProcessError, subprocess.TimeoutExpired) as exc:
        raise RuntimeError(f"git {' '.join(args)!r} failed: {exc}") from exc
    return proc.stdout


def _resolve_pre_35_08_fewshot_sha() -> str:
    """Resolve, via `git log` at run time, the commit that last touched the
    few-shot fixture BEFORE the 35-08 replacement commit. Never a hardcoded
    guess: raises loudly if the replacement commit or an earlier commit
    cannot be found, rather than silently returning the CURRENT (fixed)
    fixture's history entry."""
    global _pre_35_08_sha_cache
    if _pre_35_08_sha_cache is not None:
        return _pre_35_08_sha_cache

    output = _run_git(["log", "--format=%H %s", "--", _FEWSHOT_FIXTURE_RELATIVE_PATH])
    lines = [ln for ln in output.splitlines() if ln.strip()]

    replacement_idx = None
    for i, line in enumerate(lines):
        if _REPLACEMENT_COMMIT_MARKER.search(line):
            replacement_idx = i
            break

    if replacement_idx is None or replacement_idx + 1 >= len(lines):
        raise RuntimeError(
            "could not resolve the pre-35-08 few-shot fixture commit: no "
            "commit matching '35-08' was found in "
            f"{_FEWSHOT_FIXTURE_RELATIVE_PATH}'s git history (or no earlier "
            f"commit exists before it). History checked: {lines!r} -- "
            "refusing to fall back to the CURRENT (fixed) fixture, since "
            "that would silently invalidate arm A0's negative-control role."
        )

    _pre_35_08_sha_cache = lines[replacement_idx + 1].split(" ", 1)[0]
    return _pre_35_08_sha_cache


def _read_git_blob(sha: str, relative_path: str) -> str:
    return _run_git(["show", f"{sha}:{relative_path}"])


@dataclass(frozen=True)
class Arm:
    """One ablation arm configuration (35-AI-SPEC.md 5's arms table)."""

    id: str
    description: str
    claim: str
    few_shot_source: str  # "as_shipped" | "counterexample"
    system_prompt: bool
    tier0: bool
    provider: str
    model: str
    structured_output: bool


ARMS: "dict[str, Arm]" = {
    "A0": Arm(
        id="A0",
        description="As-shipped: current few-shot, no system prompt, no Tier 0, deepseek-chat.",
        claim=(
            "Negative control, and the harness's own validity test. A0 must "
            "reproduce F3 -- near-zero M1 with high grammar_citation_rate. "
            "If A0 does not fail this way, the harness is wrong, not the "
            "model, and no other arm's number can be trusted. Run this first."
        ),
        few_shot_source="as_shipped",
        system_prompt=False,
        tier0=False,
        provider="deepseek",
        model="deepseek-chat",
        structured_output=False,
    ),
    "A0f": Arm(
        id="A0f",
        description="A0's prompt, unchanged, on claude-sonnet-5.",
        claim=(
            "Completes the 2x2: does a frontier model override a bad "
            "demonstration on its own?"
        ),
        few_shot_source="as_shipped",
        system_prompt=False,
        tier0=False,
        provider="anthropic",
        model="claude-sonnet-5",
        structured_output=False,
    ),
    "A1": Arm(
        id="A1",
        description="A0 + counterexample-shaped few-shot (fixture replacement only).",
        claim=(
            "Section 4b.3's central claim: fixing the demonstration is the "
            "highest-impact change."
        ),
        few_shot_source="counterexample",
        system_prompt=False,
        tier0=False,
        provider="deepseek",
        model="deepseek-chat",
        structured_output=False,
    ),
    "A2": Arm(
        id="A2",
        description="A1 + system prompt with grammar-as-target / grammar-anti-filter double framing.",
        claim="Isolates the req.system defect (D1/D2) from the fixture defect.",
        few_shot_source="counterexample",
        system_prompt=True,
        tier0=False,
        provider="deepseek",
        model="deepseek-chat",
        structured_output=False,
    ),
    "A3": Arm(
        id="A3",
        description="A2 + Tier 0 (deterministic pre-classifier + feature-enriched candidate lines).",
        claim="The shipping configuration. Also isolates D5 (impoverished node features).",
        few_shot_source="counterexample",
        system_prompt=True,
        tier0=True,
        provider="deepseek",
        model="deepseek-chat",
        structured_output=False,
    ),
    "A4": Arm(
        id="A4",
        description="A3 + negotiated provider-native structured outputs.",
        claim=(
            "Whether constrained decoding buys anything once the prompt is "
            "sane, or only converts bad_json retries into content retries (D3)."
        ),
        few_shot_source="counterexample",
        system_prompt=True,
        tier0=True,
        provider="deepseek",
        model="deepseek-chat",
        structured_output=True,
    ),
    "A5": Arm(
        id="A5",
        description="A3 on claude-sonnet-5.",
        claim="Cost decision: is the cheap deployed provider sufficient once the prompt is fixed?",
        few_shot_source="counterexample",
        system_prompt=True,
        tier0=True,
        provider="anthropic",
        model="claude-sonnet-5",
        structured_output=False,
    ),
}


@dataclass(frozen=True)
class ArmArtifacts:
    """The concrete few-shot content and system-prompt text resolved for one
    arm, plus the git sha the as-shipped fixture was read from (None for a
    counterexample arm, since that content lives in the working tree)."""

    few_shot_examples: "list[dict[str, Any]]"
    system_prompt: str
    few_shot_sha: "str | None"


def resolve_arm_artifacts(arm: Arm) -> ArmArtifacts:
    """Resolve the concrete few-shot examples and system-prompt text for
    `arm`. For `few_shot_source == "as_shipped"`, reads the pre-35-08 fixture
    out of git (never the working tree) via `git show <sha>:<path>` and
    raises if the sha cannot be resolved -- see `_resolve_pre_35_08_fewshot_sha`.
    """
    if arm.few_shot_source == "as_shipped":
        sha = _resolve_pre_35_08_fewshot_sha()
        raw = _read_git_blob(sha, _FEWSHOT_FIXTURE_RELATIVE_PATH)
        payload = json.loads(raw)
        # Pre-35-08 shape is a single {description, input, expected} example,
        # not the post-35-08 {description, promptVersion, examples[]} list --
        # wrap it so callers always see a uniform list[dict] shape.
        if isinstance(payload, dict) and isinstance(payload.get("examples"), list):
            examples = payload["examples"]
        else:
            examples = [payload]
        few_shot_sha = sha
    elif arm.few_shot_source == "counterexample":
        examples = cg_recognition._load_frame_fewshot()
        few_shot_sha = None
    else:
        raise ValueError(f"unknown few_shot_source {arm.few_shot_source!r} on arm {arm.id!r}")

    system_prompt = cg_recognition.build_recognition_system_prompt() if arm.system_prompt else ""

    return ArmArtifacts(few_shot_examples=examples, system_prompt=system_prompt, few_shot_sha=few_shot_sha)


def _no_tier0_classify(features: "dict[str, cg_topology.NodeFeatures]") -> cg_topology.Tier0Result:
    """Bypass Tier 0 entirely: every scoped candidate becomes residual, so an
    arm with `tier0=False` measures Tier 1 alone over the whole scope."""
    return cg_topology.Tier0Result(decided=[], residual=list(features.keys()))


def run_arm(
    arm: Arm,
    corpus: "Any",
    adapter: "Any",
    few_shot_examples_override: "list[dict[str, Any]] | None" = None,
    api_key_override: "str | None" = None,
    negotiated_mode_override: "str | None" = None,
) -> dict:
    """Invoke `cg_recognition.recognize_structure()` with `arm`'s artifacts
    patched in (system prompt, few-shot fixture, provider/model/adapter
    resolution) and Tier 0 bypassed when `arm.tier0` is False.

    Patches module-level attributes on `cg_recognition`/`cg_topology`
    directly (save/restore via try/finally) rather than requiring a pytest
    `monkeypatch` fixture, so this is callable both from a test and from the
    standalone `record`-mode CLI sweep. Never forks `recognize_structure`.

    `few_shot_examples_override` (35-15): when supplied, REPLACES the
    resolved few-shot example list's order/content wholesale -- this is the
    seam the permutation sub-sweep (35-AI-SPEC.md 5, "Example-order
    sub-sweep") uses to run the same arm over 3 fixed example orderings
    without touching `resolve_arm_artifacts()`'s own as-shipped-sha
    resolution. `None` (the default) preserves every existing caller's
    behavior byte-for-byte.

    `api_key_override` (35-15): when supplied, is the literal string
    `resolve_active_provider` returns as the API key, REPLACING the
    `"test-api-key"` placeholder below. That placeholder is harmless for
    every replay-mode caller (`CassetteAdapter` in replay mode never calls
    `.generate()` on the wrapped adapter, so the key value is never used),
    but it is fatal for a REAL wrapped adapter in record/live mode --
    `recognize_structure()` reads the key from `resolve_active_provider`,
    not from whatever key was used to construct `adapter`, so leaving this
    patched to the placeholder would send a literal "test-api-key" as the
    Bearer/x-api-key header on every live call (401, discovered live during
    35-15 Task 1). `None` (the default) preserves the placeholder for every
    existing caller.

    `negotiated_mode_override` (35-15): when supplied, REPLACES the naive
    `"json_schema_strict" if arm.structured_output else "none"` default
    below. That default is a placeholder correct only for a provider that
    always supports strict schemas -- it is WRONG for DeepSeek, which
    `llm_gateway.negotiate_structured_output`'s own docstring calls out by
    name ("the DeepSeek trap": served through `OpenAIAdapter` so it LOOKS
    like OpenAI, but only accepts `response_format: {"type":"json_object"}`,
    never `json_schema`/`strict`). Forcing `json_schema_strict` against the
    real DeepSeek API 400s outright (`"This response_format type is
    unavailable now"`, discovered live running arm A4 during 35-15 Task 2).
    A live-mode caller resolves the REAL mode via
    `llm_gateway.negotiate_structured_output(real_provider, arm.model,
    base_url)` and passes it here so both the patched
    `negotiate_structured_output` and the returned provenance's
    `negotiatedMode` reflect what was actually sent. `None` (the default)
    preserves the placeholder for every replay-mode caller, where no live
    request is ever made and the exact mode string only affects the
    cassette key.

    Returns `{"result": <recognize_structure() return value>, "provenance":
    {...}}` -- the provenance block is a plain dict `corpus.assert_provenance`
    accepts directly (not nested further).
    """
    artifacts = resolve_arm_artifacts(arm)
    if few_shot_examples_override is not None:
        artifacts = ArmArtifacts(
            few_shot_examples=few_shot_examples_override,
            system_prompt=artifacts.system_prompt,
            few_shot_sha=artifacts.few_shot_sha,
        )
    if negotiated_mode_override is not None:
        negotiated_mode = negotiated_mode_override
    else:
        # NOT `"json_schema_strict" if arm.structured_output else "none"`.
        # That naive default was a known-wrong placeholder: it is correct only
        # for a provider that always supports strict schemas, and it is the
        # exact bug that survived its own fix commit -- `report.py` was
        # corrected to resolve the real mode while `TestEndToEndDriver` kept
        # the placeholder, so arm A4 (real mode `json_object`) computed a
        # cassette key no recording could ever match. Defaulting to the same
        # single source of truth both callers already use means a caller that
        # forgets the override gets the RIGHT mode instead of a wrong one.
        negotiated_mode = resolve_real_negotiated_mode(arm)
    resolved_api_key = api_key_override if api_key_override is not None else "test-api-key"

    original_get_adapter = cg_recognition.get_adapter
    original_negotiate = cg_recognition.negotiate_structured_output
    original_resolve_provider = cg_recognition.resolve_active_provider
    original_load_settings = cg_recognition.load_persisted_llm_settings
    original_build_system_prompt = cg_recognition.build_recognition_system_prompt
    original_load_fewshot = cg_recognition._load_frame_fewshot
    original_classify = cg_topology.classify

    try:
        cg_recognition.get_adapter = lambda provider, base_url=None: adapter
        cg_recognition.negotiate_structured_output = (
            lambda provider, model, base_url=None: StructuredOutputCapability(mode=negotiated_mode)
        )
        cg_recognition.resolve_active_provider = (
            lambda settings, master_secret: (arm.provider, arm.model, resolved_api_key)
        )
        cg_recognition.load_persisted_llm_settings = lambda: {}
        cg_recognition.build_recognition_system_prompt = lambda: artifacts.system_prompt
        cg_recognition._load_frame_fewshot = lambda: artifacts.few_shot_examples

        if not arm.tier0:
            cg_topology.classify = _no_tier0_classify
        # else: real cg_topology.classify runs unpatched -- the shipping path.

        result = cg_recognition.recognize_structure(corpus.context)
    finally:
        cg_recognition.get_adapter = original_get_adapter
        cg_recognition.negotiate_structured_output = original_negotiate
        cg_recognition.resolve_active_provider = original_resolve_provider
        cg_recognition.load_persisted_llm_settings = original_load_settings
        cg_recognition.build_recognition_system_prompt = original_build_system_prompt
        cg_recognition._load_frame_fewshot = original_load_fewshot
        cg_topology.classify = original_classify

    provenance = {
        "promptVersion": cg_recognition.PROMPT_VERSION if arm.system_prompt else "no-system-prompt",
        "provider": arm.provider,
        "model": arm.model,
        "temperature": 0.0,
        "negotiatedMode": negotiated_mode,
        "contextSha256": corpus.context_sha256,
        "frozenAtCommit": corpus.frozen_at_commit,
        "corpusVersion": corpus.corpus_version,
        "armId": arm.id,
        "fewShotSha": artifacts.few_shot_sha,
    }
    return {"result": result, "provenance": provenance}
