"""Deterministic, network-free stand-in for the provider adapter the
`/computgraph/consult` route resolves at runtime (Phase 37 Wave 0: SVAL-03).

Mirrors `data-service/tests/recognition_eval/cassette.py`'s `CassetteAdapter`
record/replay class shape and its constructor-time pinning discipline, but
simplified to a single canned-answer double -- there is no live recording
mode here, only a deterministic in-memory response.

Matches the base `LLMAdapter.generate(req, api_key, options=None)` contract
(`data-service/llm_gateway.py` L315-334) exactly, and constructs its return
value using the gateway's real `GenerateResponse` type (not a bare dict) so a
future field addition to that type surfaces as a test failure instead of
silently diverging.

No HTTP client, no API-key use, no live-call test marker -- a bare `pytest`
run can never make a paid call through this double (T-37-06).
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from llm_gateway import GenerateResponse

CONSULT_CASSETTE_DIR = Path(__file__).resolve().parent / "fixtures" / "consult"

# Cites the 11_Var_HTotal convention token verbatim and names the 2D Truss
# Configuration procedure, phrased as a plausible model reply to "Which
# parameters drive the truss height?". Also cites 11_Var_HGhost, a
# convention-shaped token that does NOT exist in the Frame subgraph, so the
# ungrounded-mention branch has a fixture to exercise.
DEFAULT_CONSULT_ANSWER = (
    "The truss height is driven by the 11_Var_HTotal parameter inside the "
    "2D Truss Configuration procedure. A related but unrelated parameter, "
    "11_Var_HGhost, is sometimes mentioned in older notes but does not "
    "appear in this Frame subgraph."
)


class ConsultCassetteMiss(Exception):
    """Raised when replay is requested for a prompt with no recorded entry,
    so a silently-empty answer can never masquerade as a passing grounding
    test."""


class ConsultCassetteAdapter:
    """Drop-in `LLMAdapter`-shaped double for the consult path.

    The answer is pinned at construction time (mirroring how
    `recognition_eval.cassette.CassetteAdapter` pins its negotiated mode once
    rather than per call), not re-resolved on every `generate()` call.
    """

    def __init__(
        self,
        answer: str = DEFAULT_CONSULT_ANSWER,
        responses: "dict[str, str] | None" = None,
        raise_on_miss: bool = False,
    ) -> None:
        self.answer = answer
        self.responses = dict(responses) if responses is not None else {}
        self.raise_on_miss = raise_on_miss
        self.calls: list[dict[str, Any]] = []

    def generate(self, req: Any, api_key: "str | None" = None, options: Any = None) -> GenerateResponse:
        self.calls.append({"prompt": req.prompt, "model": req.model, "provider": req.provider})

        if req.prompt in self.responses:
            text = self.responses[req.prompt]
        elif self.raise_on_miss:
            raise ConsultCassetteMiss(
                f"consult cassette miss for prompt {req.prompt!r} -- "
                "raise_on_miss=True forbids falling back to the default answer."
            )
        else:
            text = self.answer

        return GenerateResponse(
            text=text,
            provider=req.provider or "anthropic",
            model=req.model or "claude-sonnet",
            usage={},
            truncated=False,
            finish_reason="end_turn",
        )
