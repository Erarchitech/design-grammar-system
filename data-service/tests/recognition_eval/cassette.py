"""Cassette-based record/replay adapter for the recognition eval harness
(Phase 35-13, 35-AI-SPEC.md 5 "Record / replay -- how CI stays deterministic
and free").

`CassetteAdapter` is a drop-in replacement for a real `llm_gateway.LLMAdapter`
-- same `generate(req, api_key, options=None) -> GenerateResponse` signature
-- so an eval arm can be run through it exactly like a real adapter. Mode is
read from `RECOGNITION_EVAL_MODE` (default `replay`, i.e. $0/no secrets):

- `replay` (default): reads a cassette keyed by `cassette_key(...)`. A MISS
  RAISES -- it never silently falls through to a live call, which is exactly
  how CI would start quietly costing money.
- `record`: calls the wrapped real adapter, writes the cassette, returns the
  live response.
- `live`: calls the wrapped real adapter, writes nothing.

Cassette key = sha256(provider | model | promptVersion | system | userPrompt
| temperature | negotiatedMode | maxTokens). Because promptVersion and both
prompt bodies are in the key, ANY prompt change invalidates every cassette by
construction -- the freeze discipline is enforced by the hash, not by
remembering.

Cassette contents: {requestDigest, promptBody?, responseText, usage,
finishReason, truncated, provider, model, recordedAt, cassetteVersion}.
`promptBody` is stored ONLY when the corpus's `ip_class == "own"` -- a corpus
derived from anyone else's canvas stores the request digest alone (1b
third-party-IP constraint + the never-log-the-prompt-body rule).

Test-only, like the rest of `recognition_eval/` -- see corpus.py's module
docstring for the freeze-protocol import-direction rule this package lives
under.
"""

from __future__ import annotations

import hashlib
import json
import logging
import os
import sys
import time
from pathlib import Path
from typing import Any

# data-service/tests/recognition_eval/cassette.py -> parents[2] == data-service/,
# where llm_gateway.py lives. Inserted defensively (mirrors scoring.py) so this
# module imports correctly regardless of the invoking test's cwd/sys.path setup.
_DATA_SERVICE_ROOT = str(Path(__file__).resolve().parents[2])
if _DATA_SERVICE_ROOT not in sys.path:
    sys.path.insert(0, _DATA_SERVICE_ROOT)

from llm_gateway import GenerateRequest, GenerateResponse, GenerationOptions  # noqa: E402

logger = logging.getLogger(__name__)

CASSETTE_VERSION = 1

# data-service/tests/recognition_eval/cassette.py -> parents[2] == data-service/
_FIXTURES_ROOT = Path(__file__).resolve().parents[2] / "fixtures" / "recognition_eval" / "cassettes"

_VALID_MODES = ("replay", "record", "live")

_REFRESH_COMMAND_TEMPLATE = (
    "RECOGNITION_EVAL_MODE=record python -m pytest tests/test_recognition_eval.py "
    "-m live --arms={arm}"
)


def cassette_key(
    *,
    provider: str,
    model: "str | None",
    prompt_version: str,
    system: "str | None",
    user_prompt: str,
    temperature: "float | None",
    negotiated_mode: str,
    max_tokens: "int | None",
) -> str:
    """SHA-256 over the eight identity inputs, pipe-joined in the exact order
    35-AI-SPEC.md 5 specifies: provider | model | promptVersion | system |
    userPrompt | temperature | negotiatedMode | maxTokens.

    Because `prompt_version` and both prompt bodies are hashed in, ANY prompt
    change invalidates every cassette by construction -- the freeze
    discipline is enforced by the hash, not by remembering.
    """
    parts = [
        provider or "",
        model or "",
        prompt_version or "",
        system or "",
        user_prompt or "",
        "" if temperature is None else repr(float(temperature)),
        negotiated_mode or "",
        "" if max_tokens is None else str(int(max_tokens)),
    ]
    digest_input = "|".join(parts).encode("utf-8")
    return hashlib.sha256(digest_input).hexdigest()


class CassetteMissError(RuntimeError):
    """Raised in `replay` mode when no cassette exists for the computed key.

    NEVER falls through to a live call under any condition -- that silent
    fallthrough is exactly how a free CI gate quietly becomes a metered one.
    """


class CassetteWriteError(RuntimeError):
    """Raised when `record`/`live` mode is requested but no real adapter was
    supplied to wrap."""


def _cassette_path(arm_id: str, key: str) -> Path:
    return _FIXTURES_ROOT / arm_id / f"{key}.json"


class CassetteAdapter:
    """Drop-in `LLMAdapter`-shaped wrapper implementing record/replay/live.

    `negotiated_mode` and `prompt_version` are constructor-time, not
    per-call, values. Within one `recognize_structure()` run both are
    resolved ONCE before the Tier-1 retry loop and held fixed across every
    attempt (`recognize_structure`'s own docstring), so pinning them here --
    rather than threading them through `generate()`, which must keep the
    real adapter's exact `(req, api_key, options=None)` signature -- is the
    correct scope for them, not a shortcut.
    """

    def __init__(
        self,
        arm_id: str,
        wrapped: "Any | None",
        *,
        negotiated_mode: str,
        prompt_version: str,
        ip_class: str,
        mode: "str | None" = None,
    ) -> None:
        self.arm_id = arm_id
        self._wrapped = wrapped
        self.negotiated_mode = negotiated_mode
        self.prompt_version = prompt_version
        self.ip_class = ip_class
        self.mode = mode if mode is not None else os.environ.get("RECOGNITION_EVAL_MODE", "replay")
        if self.mode not in _VALID_MODES:
            raise ValueError(
                f"unknown RECOGNITION_EVAL_MODE {self.mode!r} -- must be one "
                f"of {_VALID_MODES!r}."
            )

    def generate(
        self,
        req: GenerateRequest,
        api_key: "str | None",
        options: "GenerationOptions | None" = None,
    ) -> GenerateResponse:
        key = cassette_key(
            provider=req.provider or "",
            model=req.model,
            prompt_version=self.prompt_version,
            system=req.system,
            user_prompt=req.prompt,
            temperature=options.temperature if options is not None else None,
            negotiated_mode=self.negotiated_mode,
            max_tokens=options.max_tokens if options is not None else None,
        )
        path = _cassette_path(self.arm_id, key)

        if self.mode == "replay":
            if not path.exists():
                raise CassetteMissError(
                    f"cassette miss for arm={self.arm_id!r} key={key} "
                    f"(expected at {path}). RECOGNITION_EVAL_MODE=replay "
                    f"never falls through to a live call. To record it: "
                    f"{_REFRESH_COMMAND_TEMPLATE.format(arm=self.arm_id)}"
                )
            return self._load(path)

        if self._wrapped is None:
            raise CassetteWriteError(
                f"RECOGNITION_EVAL_MODE={self.mode!r} requires a real "
                f"wrapped adapter to call, but none was supplied to this "
                f"CassetteAdapter (arm={self.arm_id!r})."
            )

        # Fail closed on the eval harness's own placeholder key. `run_arm`
        # patches `resolve_active_provider` to hand back the literal
        # "test-api-key" whenever no `api_key_override` is passed -- harmless
        # in replay (the wrapped adapter is never called) but fatal here: it
        # would go out to a real provider as `Authorization: Bearer
        # test-api-key` / `x-api-key: test-api-key` and 401. Enforcing the
        # pairing at the boundary that KNOWS it is live means a future second
        # live caller cannot reintroduce the bug by forgetting the keyword.
        # No-op for every replay test, which returns above.
        if api_key in (None, "", "test-api-key"):
            raise CassetteWriteError(
                f"refusing to make a live call with a placeholder/empty "
                f"api_key (arm={self.arm_id!r}, mode={self.mode!r}). Pass a "
                f"real decrypted key through "
                f"arms.run_arm(..., api_key_override=<key>) -- see "
                f"live_sweep.resolve_live_adapter_and_key."
            )

        response = self._wrapped.generate(req, api_key, options)

        if self.mode == "record":
            self._write(path, key, req, response)

        return response

    def _load(self, path: Path) -> GenerateResponse:
        payload = json.loads(path.read_text(encoding="utf-8"))
        return GenerateResponse(
            text=payload["responseText"],
            provider=payload["provider"],
            model=payload["model"],
            usage=payload.get("usage") or {},
            truncated=payload.get("truncated", False),
            finish_reason=payload.get("finishReason"),
        )

    def _write(
        self,
        path: Path,
        key: str,
        req: GenerateRequest,
        response: GenerateResponse,
    ) -> None:
        payload: dict[str, Any] = {
            "requestDigest": key,
            "responseText": response.text,
            "usage": response.usage,
            "finishReason": response.finish_reason,
            "truncated": response.truncated,
            "provider": response.provider,
            "model": response.model,
            "recordedAt": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "cassetteVersion": CASSETTE_VERSION,
        }
        if self.ip_class == "own":
            # Only for a corpus the researcher/architect authored themselves
            # (1b's third-party-IP constraint). Never logged/stored otherwise.
            payload["promptBody"] = {"system": req.system, "prompt": req.prompt}

        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
