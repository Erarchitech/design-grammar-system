"""LLM-driven Computgraph structure recognition (Phase 35: RCGN-01/RCGN-04).

Mirrors `dg_context.py`'s `generate_validated_cypher()`/`validate_cypher()`
structure verbatim -- this is NOT a new idiom. `recognize_structure()` calls
the LLM gateway in-process via `resolve_active_provider()`/`get_adapter()`/
`adapter.generate()`, exactly like `generate_validated_cypher()`, and NEVER
re-POSTs to `/llm/generate` on retry. `validate_proposed_structure()` returns
the exact same `{"valid": bool, "violations": [{"code","message","path"}]}`
shape as `validate_cypher()`, so `append_recognition_feedback()` (this
module's `append_corrective_feedback()` analog) works unchanged across
attempts.

Composes from `dg_knowledge.load_computgraph_catalog()` (concept catalog +
annotation-convention grammar) and a bundled Frame few-shot fixture
(`fixtures/frame_recognition_fewshot.json`) rather than inventing new prompt
infrastructure.

RCGN-04 safety contract: this module contains NO Neo4j write path --
recognition never persists. A hallucinated/tagged-overlapping member id is a
hard-reject `unknown_member_id`/`tagged_overlap` violation (a validator
check, never a prompt instruction alone); unrecognized blocks are reported
with their member ids, never invented or silently dropped. Nothing reaches
Neo4j until Phase 36's confirmed-only publish.
"""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

import dg_knowledge
from llm_gateway import (
    GenerateRequest,
    get_adapter,
    load_persisted_llm_settings,
    resolve_active_provider,
)


# ── DoS bounds (Security V5) ──

MAX_PROPOSALS = 200
MAX_MEMBERS_PER_PROPOSAL = 1000


# ── validate_proposed_structure() -- mirrors validate_cypher()'s violation-list shape ──


def _collect_known_member_ids(cg_context: dict) -> set[str]:
    """Every node id present in the submitted context's `nodes` collection."""
    return {
        node.get("instanceId")
        for node in (cg_context.get("nodes") or [])
        if isinstance(node, dict) and node.get("instanceId")
    }


def _collect_tagged_member_ids(cg_context: dict) -> set[str]:
    """Every member id already owned by a tagged (ground-truth) procedure,
    pattern, parameter, or interface -- walks `algorithms[].procedures[]` and
    each procedure's nested `patterns`/`parameters`/`interfaces` lists,
    collecting `memberIds` wherever `source == "tagged"`."""
    tagged: set[str] = set()
    for algorithm in cg_context.get("algorithms") or []:
        for procedure in algorithm.get("procedures") or []:
            if not isinstance(procedure, dict):
                continue
            if procedure.get("source") == "tagged":
                tagged.update(procedure.get("memberIds") or [])
            for key in ("patterns", "parameters", "interfaces"):
                for entity in procedure.get(key) or []:
                    if isinstance(entity, dict) and entity.get("source") == "tagged":
                        tagged.update(entity.get("memberIds") or [])
    return tagged


def validate_proposed_structure(parsed: dict, cg_context: dict) -> dict:
    """Validate an LLM-produced proposed-structure object against the
    submitted context (32-RESEARCH.md section 6 shape).

    Returns `{"valid": bool, "violations": [{"code","message","path"}]}` --
    the exact shape `validate_cypher()` returns, so `append_recognition_feedback`
    and the bounded retry loop work unchanged. Never raises.

    Violation codes: `bad_shape`, `missing_field`, `unknown_member_id`,
    `tagged_overlap`, `too_many_proposals`, `too_many_members`. Every message
    follows What+Where+How-to-fix phrasing.
    """
    violations: list[dict[str, Any]] = []

    proposals = parsed.get("proposals") if isinstance(parsed, dict) else None
    if not isinstance(proposals, list):
        violations.append(
            {
                "code": "bad_shape",
                "message": (
                    "'proposals' must be a list. Where: top-level 'proposals' "
                    "key. How to fix: return "
                    '{"proposals": [...], "unrecognized": [...]}.'
                ),
                "path": "proposals",
            }
        )
        return {"valid": False, "violations": violations}

    if len(proposals) > MAX_PROPOSALS:
        violations.append(
            {
                "code": "too_many_proposals",
                "message": (
                    f"'proposals' contains {len(proposals)} entries, exceeding "
                    f"the {MAX_PROPOSALS} bound. Where: top-level 'proposals' "
                    f"list. How to fix: scope recognition to a single "
                    f"procedure_index or reduce the proposal count."
                ),
                "path": "proposals",
            }
        )
        return {"valid": False, "violations": violations}

    known_ids = _collect_known_member_ids(cg_context)
    tagged_ids = _collect_tagged_member_ids(cg_context)

    for i, proposal in enumerate(proposals):
        path = f"proposals[{i}]"
        if not isinstance(proposal, dict):
            violations.append(
                {
                    "code": "bad_shape",
                    "message": f"Proposal at {path} is not an object.",
                    "path": path,
                }
            )
            continue

        for field in ("kind", "suggestedName", "memberIds", "confidence", "rationale"):
            if field not in proposal:
                violations.append(
                    {
                        "code": "missing_field",
                        "message": (
                            f"Proposal is missing required field '{field}'. "
                            f"Where: {path}. How to fix: include kind/"
                            f"suggestedName/memberIds/confidence/rationale on "
                            f"every proposal."
                        ),
                        "path": path,
                    }
                )

        member_ids = proposal.get("memberIds")
        if not isinstance(member_ids, list):
            member_ids = []

        if len(member_ids) > MAX_MEMBERS_PER_PROPOSAL:
            violations.append(
                {
                    "code": "too_many_members",
                    "message": (
                        f"Proposal at {path} references {len(member_ids)} "
                        f"member ids, exceeding the {MAX_MEMBERS_PER_PROPOSAL} "
                        f"bound. Where: {path}.memberIds. How to fix: split "
                        f"into smaller proposals."
                    ),
                    "path": path,
                }
            )
            continue

        unknown = [m for m in member_ids if m not in known_ids]
        if unknown:
            violations.append(
                {
                    "code": "unknown_member_id",
                    "message": (
                        f"Proposal references ids not present in the "
                        f"submitted context: {unknown}. Where: "
                        f"{path}.memberIds. How to fix: only reference ids "
                        f"from the submitted cg_context's nodes."
                    ),
                    "path": path,
                }
            )

        overlap = [m for m in member_ids if m in tagged_ids]
        if overlap:
            violations.append(
                {
                    "code": "tagged_overlap",
                    "message": (
                        f"Proposal references ids already owned by a tagged "
                        f"(ground-truth) entity: {overlap}. Where: "
                        f"{path}.memberIds. How to fix: remove already-tagged "
                        f"ids from the proposal -- tagged entities are "
                        f"immutable ground truth."
                    ),
                    "path": path,
                }
            )

    return {"valid": len(violations) == 0, "violations": violations}


# ── _extract_json() -- Pitfall 1: no existing precedent in this codebase ──

_FENCE_PREFIXES = ("```json", "```")


def _extract_json(text: str | None) -> tuple[dict | None, str | None]:
    """Extract a JSON object from an LLM's raw text response.

    (1) strips a leading/trailing ```json / ``` fence if the whole response
    is fenced, (2) if leading/trailing prose remains, slices from the first
    `{` to the matching last `}`, (3) `json.loads` the candidate. Never
    raises -- returns `(obj, None)` on success, `(None, message)` on failure
    (fed into the bounded retry loop as a `bad_json` violation).
    """
    if not text or not text.strip():
        return None, "LLM response was empty. Where: the LLM's raw text output."

    candidate = text.strip()

    if candidate.startswith("```") and candidate.endswith("```"):
        inner = candidate[3:-3].strip()
        for prefix in ("json", "JSON"):
            if inner.startswith(prefix):
                inner = inner[len(prefix):].strip()
                break
        candidate = inner

    if not (candidate.startswith("{") and candidate.endswith("}")):
        start = candidate.find("{")
        end = candidate.rfind("}")
        if start != -1 and end != -1 and end > start:
            candidate = candidate[start : end + 1]

    try:
        parsed = json.loads(candidate)
    except ValueError as exc:
        return None, (
            f"Could not parse JSON from the LLM response ({exc}). Where: the "
            f"LLM's raw text output. How to fix: output ONLY a single JSON "
            f"object, no markdown fences, no commentary."
        )

    if not isinstance(parsed, dict):
        return None, (
            "Parsed value is not a JSON object (expected "
            '{"proposals": [...], "unrecognized": [...]}). Where: the LLM\'s '
            "raw text output. How to fix: output a single top-level JSON "
            "object, not an array or scalar."
        )

    return parsed, None
