"""LLM-driven Computgraph structure recognition (Phase 35: RCGN-01/RCGN-04).

Two-tier orchestrator (Phase 35-12 SC1 remediation): `recognize_structure()`
first resolves per-procedure scope and runs Tier 0 (`cg_topology`), a
deterministic, no-LLM rule table over topology features -- an unchallengeable
`confidence: 1.0` decision for whatever it can decide with certainty, honest
abstention (`residual`) for everything else. Only the RESIDUAL goes to
Tier 1, the LLM, over a prompt split into a real system half
(`build_recognition_system_prompt()`, `prompts/recognition_system.md`) and a
user half (`_build_recognition_prompt()`) carrying derived candidate
features and the Tier-0 decisions as an in-context worked example. When the
residual is empty the LLM is never called at all and the result carries
`tier: "0"`.

Mirrors `dg_context.py`'s `generate_validated_cypher()`/`validate_cypher()`
structure verbatim for the Tier-1 retry loop -- this is NOT a new idiom.
`recognize_structure()` calls the LLM gateway in-process via
`resolve_active_provider()`/`get_adapter()`/`adapter.generate()`, exactly
like `generate_validated_cypher()`, and NEVER re-POSTs to `/llm/generate` on
retry -- doing so would re-read settings and could silently switch models
between attempts, destroying eval reproducibility. Provider/model/adapter
are resolved ONCE before the loop.

Pydantic (`cg_schemas.ProposedStructure`) sits BETWEEN `_extract_json()` and
`validate_proposed_structure()`: it guarantees shape and value ranges (e.g.
`confidence` in [0, 1]); `validate_proposed_structure()` runs POST-MERGE,
UNCHANGED, and guarantees the RELATIONAL safety contract (RCGN-04) --
`tagged_overlap`, `duplicate_member`, `unknown_member_id`, DoS bounds --
rules that are relations between a proposal and the submitted context and
cannot be expressed in a JSON Schema. `validate_proposed_structure()` returns
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
import logging
import os
import re
import statistics
import time
from pathlib import Path
from typing import Any

from pydantic import ValidationError

import cg_schemas
import cg_topology
import dg_knowledge
from llm_gateway import (
    GenerateRequest,
    GenerationOptions,
    get_adapter,
    load_persisted_llm_settings,
    negotiate_structured_output,
    resolve_active_provider,
)

_LOG = logging.getLogger(__name__)


# ── DoS bounds (Security V5) ──

MAX_PROPOSALS = 200
MAX_MEMBERS_PER_PROPOSAL = 1000

# Kind vocabulary accepted on proposals (WR-02): both the catalog/prompt-taught
# entity-class kinds (dg_knowledge annotation_convention "kind" values, e.g.
# "Interface") and the C# EntityTagKind short names ("IntF") that
# PreviewRegistry's ProposalDto.ToEntityTagKind() maps on the Grasshopper side.
# "Algorithm" is deliberately absent -- proposals are group-level entities only.
ALLOWED_PROPOSAL_KINDS = {
    "Proc", "Procedure",
    "Pat", "Pattern",
    "Var", "VariableParam",
    "Const", "ConstantParam",
    "Emg", "EmergentParam",
    "IntF", "Interface",
}

_ALLOWED_KIND_LOOKUP = {k.lower() for k in ALLOWED_PROPOSAL_KINDS}


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

    Violation codes: `bad_shape`, `missing_field`, `invalid_kind`,
    `unknown_member_id`, `tagged_overlap`, `duplicate_member`,
    `too_many_proposals`, `too_many_members`, `too_many_unrecognized`. Every
    message follows What+Where+How-to-fix phrasing. The `unrecognized` block
    is validated too (WR-06): entries must be `{memberIds, reason}` objects
    whose ids exist in the submitted context -- "never invented" is a
    validator guarantee, not a prompt instruction.
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

        if "kind" in proposal:
            kind = proposal.get("kind")
            if not isinstance(kind, str) or kind.strip().lower() not in _ALLOWED_KIND_LOOKUP:
                violations.append(
                    {
                        "code": "invalid_kind",
                        "message": (
                            f"Proposal 'kind' {kind!r} is not an allowed entity "
                            f"kind. Where: {path}.kind. How to fix: use one of "
                            f"{sorted(ALLOWED_PROPOSAL_KINDS)}."
                        ),
                        "path": f"{path}.kind",
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

    # WR-03: cross-proposal duplicate check -- two proposals claiming the same
    # node would preview as overlapping groups and, once both are accepted in
    # DG STRUCTURE CONFIRM, produce the exact double-ownership state the
    # tagged_overlap rule exists to prevent, just one confirmation step later.
    seen: dict[str, int] = {}
    for i, proposal in enumerate(proposals):
        members = proposal.get("memberIds") if isinstance(proposal, dict) else None
        if not isinstance(members, list):
            continue
        for m in members:
            if m in seen:
                violations.append(
                    {
                        "code": "duplicate_member",
                        "message": (
                            f"Member id {m!r} appears in proposals[{seen[m]}] "
                            f"and proposals[{i}]. Where: "
                            f"proposals[{i}].memberIds. How to fix: assign "
                            f"each node to exactly one proposal."
                        ),
                        "path": f"proposals[{i}].memberIds",
                    }
                )
            else:
                seen[m] = i

    # WR-06: the module contract promises unrecognized member ids are "never
    # invented" -- enforce it as a validator check (shape, size bound, and
    # unknown_member_id), not a prompt instruction alone. Downstream consumers
    # (Phase 36 publish, UI) reasonably trust ids in a "validated" response.
    unrecognized = parsed.get("unrecognized")
    if unrecognized is not None:
        if not isinstance(unrecognized, list):
            violations.append(
                {
                    "code": "bad_shape",
                    "message": (
                        "'unrecognized' must be a list of "
                        '{"memberIds", "reason"} objects. Where: top-level '
                        "'unrecognized' key. How to fix: return "
                        '{"proposals": [...], "unrecognized": [...]}.'
                    ),
                    "path": "unrecognized",
                }
            )
        elif len(unrecognized) > MAX_PROPOSALS:
            violations.append(
                {
                    "code": "too_many_unrecognized",
                    "message": (
                        f"'unrecognized' contains {len(unrecognized)} entries, "
                        f"exceeding the {MAX_PROPOSALS} bound. Where: "
                        f"top-level 'unrecognized' list. How to fix: merge "
                        f"related nodes into fewer entries."
                    ),
                    "path": "unrecognized",
                }
            )
        else:
            for i, entry in enumerate(unrecognized):
                entry_path = f"unrecognized[{i}]"
                if not isinstance(entry, dict):
                    violations.append(
                        {
                            "code": "bad_shape",
                            "message": f"Entry at {entry_path} is not an object.",
                            "path": entry_path,
                        }
                    )
                    continue

                for field in ("memberIds", "reason"):
                    if field not in entry:
                        violations.append(
                            {
                                "code": "missing_field",
                                "message": (
                                    f"Unrecognized entry is missing required "
                                    f"field '{field}'. Where: {entry_path}. "
                                    f"How to fix: include memberIds and reason "
                                    f"on every unrecognized entry."
                                ),
                                "path": entry_path,
                            }
                        )

                entry_members = entry.get("memberIds")
                if not isinstance(entry_members, list):
                    entry_members = []

                if len(entry_members) > MAX_MEMBERS_PER_PROPOSAL:
                    violations.append(
                        {
                            "code": "too_many_members",
                            "message": (
                                f"Unrecognized entry references "
                                f"{len(entry_members)} member ids, exceeding "
                                f"the {MAX_MEMBERS_PER_PROPOSAL} bound. Where: "
                                f"{entry_path}.memberIds. How to fix: split "
                                f"into smaller entries."
                            ),
                            "path": f"{entry_path}.memberIds",
                        }
                    )
                    continue

                unknown = [m for m in entry_members if m not in known_ids]
                if unknown:
                    violations.append(
                        {
                            "code": "unknown_member_id",
                            "message": (
                                f"Unrecognized entry references ids not "
                                f"present in the submitted context: {unknown}. "
                                f"Where: {entry_path}.memberIds. How to fix: "
                                f"only reference ids from the submitted "
                                f"cg_context's nodes -- never invent ids."
                            ),
                            "path": f"{entry_path}.memberIds",
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


# ── System prompt loader (Phase 35-12 Task 1: prompt split, role/task/grammar
# framing moves out of the user prompt and into a real system prompt) ──

SYSTEM_PROMPT_FILE = Path(__file__).resolve().parent / "prompts" / "recognition_system.md"


def _parse_front_matter(text: str) -> tuple[dict[str, str], str]:
    """Split a `---\\nkey: value\\n---\\nbody` file into `(front_matter, body)`.

    Deliberately not a YAML parser -- the front matter here is a flat set of
    scalar `key: value` pairs and pulling in a YAML dependency for that would
    be a net-new dependency for one field. Never raises: text with no leading
    `---` fence returns `({}, text)` unchanged.
    """
    lines = text.splitlines()
    if not lines or lines[0].strip() != "---":
        return {}, text
    front_matter: dict[str, str] = {}
    body_start: int | None = None
    for i in range(1, len(lines)):
        if lines[i].strip() == "---":
            body_start = i + 1
            break
        if ":" in lines[i]:
            key, _, value = lines[i].partition(":")
            front_matter[key.strip()] = value.strip()
    if body_start is None:
        # Opening fence with no closing fence -- malformed, degrade to "no
        # front matter" rather than guessing where the body starts.
        return {}, text
    return front_matter, "\n".join(lines[body_start:])


_system_prompt_cache: str | None = None
_prompt_version_cache: str | None = None


def _load_system_prompt() -> tuple[str, str]:
    """Load `prompts/recognition_system.md` once, cached at module scope --
    mirrors `_load_frame_fewshot()`'s defensive load pattern: NEVER raises on
    a missing or malformed file. On failure returns `("", "")` and logs a
    warning, so a missing prompt file degrades recognition to pre-Phase-35
    behaviour (no system prompt sent) rather than breaking it outright."""
    global _system_prompt_cache, _prompt_version_cache
    if _system_prompt_cache is not None:
        return _system_prompt_cache, _prompt_version_cache or ""
    if not SYSTEM_PROMPT_FILE.exists():
        _LOG.warning("recognition_system_prompt_missing path=%s", SYSTEM_PROMPT_FILE)
        _system_prompt_cache = ""
        _prompt_version_cache = ""
        return _system_prompt_cache, _prompt_version_cache
    try:
        raw = SYSTEM_PROMPT_FILE.read_text(encoding="utf-8")
        front_matter, body = _parse_front_matter(raw)
        _system_prompt_cache = body.strip()
        _prompt_version_cache = front_matter.get("prompt_version", "")
    except OSError:
        _LOG.warning("recognition_system_prompt_load_failed path=%s", SYSTEM_PROMPT_FILE)
        _system_prompt_cache = ""
        _prompt_version_cache = ""
    return _system_prompt_cache, _prompt_version_cache or ""


def build_recognition_system_prompt() -> str:
    """Return the recognition system prompt (front matter stripped), loaded
    once and cached. Never raises -- returns `""` when the file is absent or
    malformed. Passed as `GenerateRequest.system` by `recognize_structure()`;
    role, task framing, and the grammar-is-not-a-filter guidance all live
    here now, not in the user prompt (Phase 35-12 D-prompt-split)."""
    body, _ = _load_system_prompt()
    return body


PROMPT_VERSION: str = _load_system_prompt()[1]


# ── Frame few-shot fixture (Phase 35-02: A4 few-shot budget resolution;
# Phase 35-08/35-12: adapted to the `{description, promptVersion, examples[]}`
# shape) ──

FRAME_FEWSHOT_FILE = Path(__file__).resolve().parent / "fixtures" / "frame_recognition_fewshot.json"

_EMPTY_FEWSHOT_EXAMPLES: list[dict[str, Any]] = []

_fewshot_cache: list[dict[str, Any]] | None = None


def _load_frame_fewshot() -> list[dict[str, Any]]:
    """Load the bundled Frame few-shot fixture once, cached at module scope
    (mirrors dg_context.load_cypher_catalog()'s defensive load pattern --
    never raises on a missing or malformed file).

    Returns the `examples` LIST from the fixture's `{description,
    promptVersion, examples[]}` shape, not the whole fixture object --
    returning a list rather than one blob is what makes a later
    dynamic-retrieval example selector (pick a relevant subset instead of
    always returning every example) a one-line change at the call site.
    """
    global _fewshot_cache
    if _fewshot_cache is not None:
        return _fewshot_cache
    if not FRAME_FEWSHOT_FILE.exists():
        _fewshot_cache = list(_EMPTY_FEWSHOT_EXAMPLES)
        return _fewshot_cache
    try:
        payload = json.loads(FRAME_FEWSHOT_FILE.read_text(encoding="utf-8"))
        examples = payload.get("examples") if isinstance(payload, dict) else None
        _fewshot_cache = examples if isinstance(examples, list) else list(_EMPTY_FEWSHOT_EXAMPLES)
    except (OSError, ValueError):
        _fewshot_cache = list(_EMPTY_FEWSHOT_EXAMPLES)
    return _fewshot_cache


# ── _build_recognition_prompt() -- deterministic prompt assembly (Phase
# 35-02; Phase 35-12: rewired to the USER half only, over the two-tier
# scope/features/tier0 inputs) ──

_CONCEPT_CATALOG_MARKER = "=== COMPUTGRAPH CONCEPT CATALOG ==="
_FEWSHOT_MARKER = "=== FRAME FEW-SHOT EXAMPLE ==="
_TAGGED_ANCHOR_MARKER = "=== TAGGED ENTITIES (GROUND TRUTH -- DO NOT RENAME, SPLIT, OR ABSORB) ==="
_TIER0_DECISIONS_MARKER = "=== ALREADY DECIDED BY TOPOLOGY (do not re-propose these ids) ==="
_UNTAGGED_MARKER = "=== UNTAGGED NODES TO CLASSIFY ==="
_OUTPUT_INSTRUCTION_MARKER = "=== OUTPUT INSTRUCTIONS ==="

_ENTITY_LABEL_BY_KEY: dict[str, str] = {
    "patterns": "Pattern",
    "parameters": "Parameter",
    "interfaces": "Interface",
}


def _candidate_feature_lines(features: "dict[str, Any]", node_ids: list[str]) -> list[str]:
    """One line per candidate, rendering DERIVED topology features (widget
    kind, wiring degree, group, adjacent tagged procedure, name/nickname) --
    not raw data. `position` is deliberately absent: it is FM-1's most
    seductive and least reliable signal, and the model must decide from
    graph evidence instead. `features` values are `cg_topology.NodeFeatures`
    instances (typed as `Any` here to avoid a hard dataclass-shape coupling
    in the type hint)."""
    lines: list[str] = []
    for node_id in node_ids:
        f = features.get(node_id)
        if f is None:
            continue
        group = f.group_id if f.group_id else "none"
        lines.append(
            f"- {node_id}: widget={f.widget_kind} in={f.in_degree} out={f.out_degree} "
            f"group={group!r} adj_proc={f.adjacent_tagged_procedures} "
            f"name={f.name!r} nick={f.nickname!r}"
        )
    return lines


def _tier0_decision_lines(tier0_decided: list[dict]) -> list[str]:
    """One line per Tier-0 decision, so Tier 1 both avoids re-proposing an
    already-decided id AND gets a free in-context worked example generated
    from the architect's own canvas -- the strongest few-shot available,
    since it is real evidence from this exact context, not a fixture."""
    lines: list[str] = []
    for row in tier0_decided:
        if not isinstance(row, dict):
            continue
        member_ids = row.get("memberIds") or []
        member_id = member_ids[0] if member_ids else "?"
        lines.append(f"- {member_id} -> {row.get('kind')}  ({row.get('rationale')})")
    return lines


def _trimmed_wire_lines(cg_context: dict, node_ids: list[str]) -> list[str]:
    scoped = set(node_ids)
    lines: list[str] = []
    for wire in cg_context.get("wires") or []:
        if wire.get("fromNode") in scoped or wire.get("toNode") in scoped:
            lines.append(
                f"- {wire.get('fromNode')}.{wire.get('fromParam')} -> "
                f"{wire.get('toNode')}.{wire.get('toParam')}"
            )
    return lines


def _tagged_anchor_lines(cg_context: dict, procedure_index: int | None = None) -> list[str]:
    """Tagged (ground-truth) entities, as anchors Tier 1 must never rename,
    split, or absorb into.

    When `procedure_index` is set, this widens to also SUMMARIZE the rest of
    the canvas rather than omit it: the target procedure gets its full
    `memberIds` list (Tier 1 needs those ids to reason about adjacency), and
    every OTHER tagged procedure/entity collapses to a one-line
    name/index/member-count summary. On a mostly-tagged canvas the full
    anchor block is the single largest prompt section and most of it is
    irrelevant to the procedure actually being recognized.
    """
    lines: list[str] = []
    for algorithm in cg_context.get("algorithms") or []:
        for procedure in algorithm.get("procedures") or []:
            if not isinstance(procedure, dict):
                continue
            proc_index = procedure.get("index")
            is_target = procedure_index is not None and proc_index == procedure_index
            summarize = procedure_index is not None and not is_target

            if procedure.get("source") == "tagged":
                if summarize:
                    member_count = len(procedure.get("memberIds") or [])
                    lines.append(
                        f"- Procedure '{procedure.get('name')}' (index "
                        f"{proc_index}) member count: {member_count}"
                    )
                else:
                    lines.append(
                        f"- Procedure '{procedure.get('name')}' (index "
                        f"{proc_index}, id {procedure.get('id')}) "
                        f"members: {procedure.get('memberIds')}"
                    )

            if summarize:
                # Nested entities of a non-target procedure are folded into
                # that procedure's one-line summary above -- their own
                # memberIds add no signal Tier 1 needs for a DIFFERENT
                # procedure's residual candidates.
                continue

            for key, label in _ENTITY_LABEL_BY_KEY.items():
                for entity in procedure.get(key) or []:
                    if isinstance(entity, dict) and entity.get("source") == "tagged":
                        name = entity.get("label") or entity.get("name")
                        lines.append(
                            f"- {label} '{name}' (id {entity.get('id')}) "
                            f"members: {entity.get('memberIds')}"
                        )
    return lines


def _build_recognition_prompt(
    cg_context: dict,
    scope: "Any",
    features: "dict[str, Any]",
    tier0: "Any",
    negotiated_mode: str,
) -> str:
    """Deterministically assemble the USER half of the recognition prompt:
    concept catalog + annotation-convention grammar, the Frame few-shot
    examples, tagged entities as ground-truth anchors (scoped to
    `scope.procedure_index`), the Tier-0 decisions block, the residual
    candidate feature lines, the residual wire lines, group hints, and an
    explicit JSON-only output instruction.

    Deliberately does NOT restate the role, the task, or the grammar
    anti-filter framing -- those live in `build_recognition_system_prompt()`
    now (the system half). Stating the output contract twice in different
    words is a real regression risk, not a harmless redundancy.

    `scope`/`features`/`tier0` are `cg_topology.Scope`/`NodeFeatures`
    dict/`Tier0Result` respectively (typed as `Any` here to avoid a hard
    import-order coupling in the type hint). Fixed section order -- same
    request yields the same prompt every time (CTXA-05's determinism
    discipline).
    """
    catalog = dg_knowledge.load_computgraph_catalog()
    fewshot_examples = _load_frame_fewshot()

    residual_ids = list(tier0.residual)
    residual_set = set(residual_ids)

    candidate_lines = _candidate_feature_lines(features, residual_ids) or ["(none)"]
    wire_lines = _trimmed_wire_lines(cg_context, residual_ids) or ["(none)"]
    group_lines = [
        f"- {g.get('nickname')}: members {g.get('memberIds')}"
        for g in scope.groups
        if any(m in residual_set for m in (g.get("memberIds") or []))
    ] or ["(none)"]
    anchor_lines = _tagged_anchor_lines(cg_context, scope.procedure_index) or ["(none)"]
    decision_lines = _tier0_decision_lines(tier0.decided)

    sections = [
        _CONCEPT_CATALOG_MARKER,
        f"entity_classes: {json.dumps(catalog.get('entity_classes'), sort_keys=True)}",
        f"relations: {json.dumps(catalog.get('relations'), sort_keys=True)}",
        f"enum_values: {json.dumps(catalog.get('enum_values'), sort_keys=True)}",
        "annotation_convention (DG Canvas Annotation Convention grammar):",
        json.dumps(catalog.get("annotation_convention"), sort_keys=True),
        "",
        _FEWSHOT_MARKER,
        json.dumps(fewshot_examples, sort_keys=True),
        "",
        _TAGGED_ANCHOR_MARKER,
        *anchor_lines,
    ]

    if decision_lines:
        sections += ["", _TIER0_DECISIONS_MARKER, *decision_lines]

    sections += [
        "",
        _UNTAGGED_MARKER,
        "Candidates:",
        *candidate_lines,
        "Wires:",
        *wire_lines,
        "Group hints:",
        *group_lines,
        "",
        _OUTPUT_INSTRUCTION_MARKER,
        (
            "Output ONLY a single JSON object matching this shape: "
            '{"proposals": [{"kind","suggestedName","procedureIndex",'
            '"memberIds","confidence","rationale"}], "unrecognized": '
            '[{"memberIds","reason"}]}. No markdown fences. No commentary. '
            "No text before or after the JSON object."
        ),
    ]

    if negotiated_mode == "json_object":
        # DeepSeek-shaped providers (reached through OpenAIAdapter via
        # base_url) require the literal word "json" in the prompt and
        # recommend a compact shape example -- branch on the NEGOTIATED
        # MODE, never on `provider == "openai"` (llm_gateway.py's DeepSeek
        # trap note).
        sections.append(
            "Return a valid json object. Example shape: "
            '{"proposals": [{"kind": "Interface", "suggestedName": '
            '"11_IntF_Example", "procedureIndex": 11, "memberIds": ["<id>"], '
            '"confidence": 0.7, "rationale": "..."}], "unrecognized": []}'
        )

    return "\n".join(sections)


def append_recognition_feedback(prompt: str, violations: list[dict[str, Any]]) -> str:
    """Append structured violations to the ORIGINAL prompt as corrective
    feedback for the next attempt (mirrors dg_context.append_corrective_feedback's
    What+Where+How-to-fix vocabulary, retargeted at the JSON-only output
    discipline)."""
    lines = [
        prompt,
        "",
        "--- CORRECTIVE FEEDBACK: the previous proposal failed validation ---",
    ]
    for violation in violations:
        where = f" (at: {violation['path']})" if violation.get("path") else ""
        lines.append(f"- [{violation['code']}] {violation['message']}{where}")
    lines.append(
        "Regenerate the proposal, fixing every violation listed above. Output "
        "ONLY a single JSON object -- no markdown fences, no commentary."
    )
    return "\n".join(lines)


# ── recognize_structure() -- two-tier orchestrator (Phase 35-12: Tier 0
# cg_topology + Tier 1 bounded LLM retry loop, mirrors CTXA-04) ──


def _schema_violations_from_pydantic(exc: ValidationError) -> list[dict[str, Any]]:
    """One `schema_violation` violation per Pydantic error, in the existing
    What+Where+How-to-fix phrasing so `append_recognition_feedback` needs no
    special-casing for this violation code."""
    violations: list[dict[str, Any]] = []
    for err in exc.errors():
        loc = ".".join(str(p) for p in err.get("loc", ()))
        violations.append(
            {
                "code": "schema_violation",
                "message": (
                    f"Proposal failed schema validation: {err.get('msg')}. "
                    f"Where: {loc or '(top level)'}. How to fix: conform the "
                    f"proposal to the required ProposedStructure shape."
                ),
                "path": loc,
            }
        )
    return violations


# ── G7 grammar_as_filter -- the pattern set is defined ONCE here so
# tests/recognition_eval/scoring.py's grammar_citation_rate (the offline
# metric) can import it, rather than reimplementing it, and the online
# guardrail and the offline metric can never disagree (UAT F3's live root
# cause) ──

GRAMMAR_CITATION_KEYWORDS: tuple[str, ...] = ("grammar", "convention", "does not match")
GRAMMAR_CITATION_NAME_RE = re.compile(r"\b\d{2}_(Proc|Pat|Var|Const|Emg|Emr|IntF)_")

GRAMMAR_CITATION_PATTERNS: dict[str, Any] = {
    "keywords": GRAMMAR_CITATION_KEYWORDS,
    "name_pattern": GRAMMAR_CITATION_NAME_RE,
}


def cites_grammar_as_reason(rationale: str) -> bool:
    """G7's detector: keyword scan for 'grammar' / 'convention' / 'does not
    match', plus a regex for a `<NN>_<Kind>_<Name>` form cited AS
    justification (e.g. "matches 11_IntF_ParSplitAt")."""
    if not rationale:
        return False
    lowered = rationale.lower()
    if any(keyword in lowered for keyword in GRAMMAR_CITATION_KEYWORDS):
        return True
    return GRAMMAR_CITATION_NAME_RE.search(rationale) is not None


def _grammar_as_filter_triggered(proposals: list[dict], residual_count: int) -> bool:
    """G7 (35-AI-SPEC.md section 6): fires on a grammar-citing rationale OR
    the structural signature -- zero proposals for >= 5 candidates, the
    live SC1 root cause (UAT F3). Zero tolerance."""
    rationales = [p.get("rationale", "") for p in proposals if isinstance(p, dict)]
    if any(cites_grammar_as_reason(r) for r in rationales):
        return True
    return len(proposals) == 0 and residual_count >= 5


# ── G6 unaddressed_candidate -- RCGN-04's "never silently dropped" ──


def _unaddressed_candidates(merged: dict, residual_ids: list[str]) -> list[str]:
    """Scoped candidate ids appearing in neither `proposals[].memberIds` nor
    `unrecognized[].memberIds`."""
    addressed: set[str] = set()
    for p in merged.get("proposals") or []:
        if isinstance(p, dict):
            addressed.update(p.get("memberIds") or [])
    for u in merged.get("unrecognized") or []:
        if isinstance(u, dict):
            addressed.update(u.get("memberIds") or [])
    return [n for n in residual_ids if n not in addressed]


# ── G10 confidence floor -- demotes, never blocks ──

CONFIDENCE_FLOOR = 0.5
# GUESS: this threshold is provisional and has NOT been derived from real
# accept-rate-vs-confidence data. AI-SPEC.md section 7 calls for re-deriving
# it once >= 50 flywheel records exist (recognition_runs.jsonl +
# recognition_labels.jsonl review queue, deferred per STATE.md). Do not
# treat 0.5 as calibrated -- it is a starting guess, stated as one in code
# so nobody mistakes it for a measured value.


def _demote_low_confidence(merged: dict, confidence_floor: float) -> None:
    """G10: a proposal below `confidence_floor` is DEMOTED (never blocked)
    into `unrecognized[]`, carrying the would-be kind as a hint. Mutates
    `merged` in place."""
    kept: list[dict] = []
    for p in merged.get("proposals") or []:
        confidence = p.get("confidence") if isinstance(p, dict) else None
        if isinstance(confidence, (int, float)) and confidence < confidence_floor:
            merged.setdefault("unrecognized", []).append(
                {
                    "memberIds": p.get("memberIds") or [],
                    "reason": (
                        f"confidence {confidence} is below the "
                        f"{confidence_floor} floor (would-be kind: "
                        f"{p.get('kind')})."
                    ),
                }
            )
        else:
            kept.append(p)
    merged["proposals"] = kept


# ── G11 flat-confidence detector -- flags, never blocks ──


def _confidence_is_flat(confidences: list[float]) -> bool:
    """G11 (35-AI-SPEC.md section 6): True when >= 5 proposals carry a
    single unique confidence value or a near-zero spread (population stdev
    < 0.02) -- mirrors tests/recognition_eval/scoring.py's
    confidence_spread_ok, inverted. A rendered percentage that carries no
    information is worse than showing none."""
    if len(confidences) < 5:
        return False
    if len(set(confidences)) == 1:
        return True
    return statistics.pstdev(confidences) < 0.02


# ── Per-attempt structured logging (35-AI-SPEC.md section 4b) ──


def _log_attempt(
    attempt_number: int,
    provider: str,
    model: str | None,
    negotiated_mode: str,
    max_tokens: int,
    usage: dict,
    finish_reason: str | None,
    tier0_decided_count: int,
    tier1_residual_count: int,
    violation_codes: list[str],
    latency_ms: float,
) -> None:
    """One structured log record per Tier-1 attempt. NEVER logs
    `current_prompt`, `system_prompt`, or the API key -- only attributable
    run metadata (LLMC-06). JSON-serialized directly into the log MESSAGE
    (not `extra=`) so every field is visible in captured log text, not only
    on the LogRecord object."""
    record = {
        "attempt": attempt_number,
        "provider": provider,
        "model": model,
        "negotiated_mode": negotiated_mode,
        "prompt_version": PROMPT_VERSION,
        "temperature": 0.0,
        "max_tokens": max_tokens,
        "usage": usage,
        "finish_reason": finish_reason,
        "tier0_decided_count": tier0_decided_count,
        "tier1_residual_count": tier1_residual_count,
        "violation_codes": violation_codes,
        "latency_ms": round(latency_ms, 1),
    }
    _LOG.info("recognition_attempt %s", json.dumps(record, sort_keys=True, default=str))


def recognize_structure(
    cg_context: dict,
    procedure_index: int | None = None,
    max_retries: int = 2,
    confidence_floor: float = CONFIDENCE_FLOOR,
) -> dict:
    """Two-tier structure recognition: Tier 0 (`cg_topology`) decides what
    topology alone can decide with certainty; only the residual goes to
    Tier 1 (the LLM), bounded-retry validated (mirrors
    `dg_context.generate_validated_cypher()`'s exact loop structure).

    Resolves the active provider/adapter ONCE before the Tier-1 loop and
    calls `adapter.generate()` in-process each attempt -- NEVER re-POSTs to
    `/llm/generate` (RESEARCH.md Anti-pattern guard): a re-POST re-reads
    settings and could silently switch models between attempts, destroying
    eval reproducibility.

    Four in-band guardrails run inside the Tier-1 loop, each promoting a UAT
    finding into an enforced invariant: G6 `unaddressed_candidate` (retries,
    then auto-fills into `unrecognized[]` on the final attempt, flagging
    `unaddressed_candidates_autofilled`); G7 `grammar_as_filter` (retries
    once with a targeted corrective message, then blocks with a diagnostic
    naming the prompt version and provider); G10 (`confidence_floor`, a
    provisional guess) demotes low-confidence proposals into
    `unrecognized[]`; G11 flags (never blocks) an uninformative flat
    confidence spread across >= 5 proposals.

    Returns one of:
    - `{"valid": False, "violations": [...], "attempts": 0}` -- `procedure_index`
      resolves to a tagged-but-member-less procedure (G9); the LLM is never
      called.
    - `{"valid": True, "proposal": {...}, "attempts": 0, "tier": "0"}` --
      Tier 0 decided every candidate; the LLM is never called.
    - `{"valid": True, "proposal": {...}, "attempts": N, "tier": "0+1",
      "provider": ..., "model": ..., "flags": [...]}` -- Tier 1 was invoked
      and its output, merged with Tier 0's decisions, passed
      `validate_proposed_structure()`. `flags` may contain
      `unaddressed_candidates_autofilled` and/or `confidence_uninformative`.
    - `{"valid": False, "violations": [...], "attempts": N, "provider": ...,
      "model": ..., "flags": [...]}` -- the retry bound was exhausted, or a
      non-retryable Tier-1 outcome (`output_truncated`, `provider_refusal`,
      a final-attempt `grammar_as_filter` block) ended the run immediately.

    `provider`/`model` are the resolved LLM identity behind the proposal
    (Phase 36 UAT F6). They are ALSO injected into the returned `proposal`
    object on the Tier-1 success path, so a caller can hand
    `result["proposal"]` straight to `gh_preview_structure` without
    re-stitching provenance.
    """
    scope = cg_topology.scope_untagged(cg_context, procedure_index)
    if scope.empty_procedure:
        return {
            "valid": False,
            "violations": [
                {
                    "code": "empty_procedure_scope",
                    "message": (
                        f"Procedure {procedure_index} has no tagged members "
                        f"in the submitted context. Where: procedure_index="
                        f"{procedure_index}. How to fix: tag that "
                        f"procedure's members first, or omit procedure_index "
                        f"to recognize across the whole canvas."
                    ),
                    "path": "procedure_index",
                }
            ],
            "attempts": 0,
        }

    features = cg_topology.extract_features(cg_context, scope.node_ids)
    tier0 = cg_topology.classify(features)

    if not tier0.residual:
        # Tier 0 decided every candidate -- the LLM is never called.
        merged = cg_topology.merge(tier0.decided, {"proposals": [], "unrecognized": []})
        return {"valid": True, "proposal": merged, "attempts": 0, "tier": "0"}

    system_prompt = build_recognition_system_prompt()

    master_secret = os.getenv("LLM_MASTER_SECRET", "")
    settings = load_persisted_llm_settings()
    provider, model, api_key = resolve_active_provider(settings, master_secret)
    adapter = get_adapter(provider, settings.get("baseUrl"))
    caps = negotiate_structured_output(provider, model, settings.get("baseUrl"))

    prompt = _build_recognition_prompt(cg_context, scope, features, tier0, caps.mode)
    schema = caps.schema_for(cg_schemas.to_strict_json_schema(cg_schemas.ProposedStructure))
    options = GenerationOptions(
        temperature=0.0,
        max_tokens=cg_topology.output_token_budget(tier0.residual),
        output_schema=schema,
    )

    current_prompt = prompt
    violations: list[dict[str, Any]] = []
    flags: list[str] = []
    g7_already_retried = False

    for attempt in range(max_retries + 1):
        is_final_attempt = attempt == max_retries
        flags = []

        start = time.monotonic()
        req = GenerateRequest(prompt=current_prompt, system=system_prompt, model=model, provider=provider)
        response = adapter.generate(req, api_key, options=options)
        latency_ms = (time.monotonic() - start) * 1000.0

        def log_this(violation_codes: list[str]) -> None:
            _log_attempt(
                attempt + 1,
                provider,
                model,
                caps.mode,
                options.max_tokens,
                response.usage,
                response.finish_reason,
                len(tier0.decided),
                len(tier0.residual),
                violation_codes,
                latency_ms,
            )

        if response.truncated:
            # G8: NO retry -- an identical scope truncates identically, so a
            # retry burns the most expensive call for zero value. Advise
            # scoping instead.
            violations = [
                {
                    "code": "output_truncated",
                    "message": (
                        f"The model's response was truncated at the "
                        f"{options.max_tokens}-token cap with "
                        f"{len(tier0.residual)} residual candidates in "
                        f"scope. Where: the LLM response. How to fix: scope "
                        f"recognition to a single procedure_index to reduce "
                        f"the candidate count."
                    ),
                    "path": None,
                }
            ]
            log_this(["output_truncated"])
            return {
                "valid": False,
                "violations": violations,
                "attempts": attempt + 1,
                "provider": provider,
                "model": model,
                "flags": flags,
            }

        if response.finish_reason == "refusal":
            # A refusal is not malformed output -- surface it distinctly
            # rather than burning retries on a misleading bad_json.
            violations = [
                {
                    "code": "provider_refusal",
                    "message": (
                        "The model refused to generate a response for this "
                        "request. Where: the LLM response. How to fix: "
                        "review the submitted context for content the "
                        "provider may be declining to process."
                    ),
                    "path": None,
                }
            ]
            log_this(["provider_refusal"])
            return {
                "valid": False,
                "violations": violations,
                "attempts": attempt + 1,
                "provider": provider,
                "model": model,
                "flags": flags,
            }

        parsed, parse_error = _extract_json(response.text)
        if parse_error:
            violations = [{"code": "bad_json", "message": parse_error, "path": None}]
            log_this(["bad_json"])
            current_prompt = append_recognition_feedback(prompt, violations)
            continue

        try:
            typed = cg_schemas.ProposedStructure.model_validate(parsed)
        except ValidationError as exc:
            violations = _schema_violations_from_pydantic(exc)
            log_this([v["code"] for v in violations])
            current_prompt = append_recognition_feedback(prompt, violations)
            continue

        merged = cg_topology.merge(tier0.decided, typed.model_dump(mode="json"))

        # G7 grammar_as_filter -- checked BEFORE G6, since a systemic
        # filter-reading failure is usually also why nothing was addressed;
        # its targeted diagnostic is more useful than a generic
        # unaddressed_candidate retry for the same root cause.
        if _grammar_as_filter_triggered(merged["proposals"], len(tier0.residual)):
            if not g7_already_retried and not is_final_attempt:
                g7_already_retried = True
                violations = [
                    {
                        "code": "grammar_as_filter",
                        "message": (
                            "The naming convention is an OUTPUT TARGET, "
                            "never a filter -- every untagged candidate is "
                            "eligible regardless of its current name. "
                            "Re-classify every candidate from graph "
                            "evidence (wiring direction/degree, group "
                            "membership, adjacent tagged procedure), not "
                            "from whether its name already matches the "
                            "convention."
                        ),
                        "path": None,
                    }
                ]
                log_this(["grammar_as_filter"])
                current_prompt = append_recognition_feedback(prompt, violations)
                continue
            violations = [
                {
                    "code": "grammar_as_filter",
                    "message": (
                        "the model is filtering by name instead of "
                        f"classifying by topology -- prompt version "
                        f"{PROMPT_VERSION}, provider {provider}."
                    ),
                    "path": None,
                }
            ]
            log_this(["grammar_as_filter"])
            return {
                "valid": False,
                "violations": violations,
                "attempts": attempt + 1,
                "provider": provider,
                "model": model,
                "flags": flags,
            }

        # G6 unaddressed_candidate.
        missing = _unaddressed_candidates(merged, tier0.residual)
        if missing:
            if is_final_attempt:
                for node_id in missing:
                    merged.setdefault("unrecognized", []).append(
                        {"memberIds": [node_id], "reason": "not addressed by the model"}
                    )
                flags.append("unaddressed_candidates_autofilled")
            else:
                violations = [
                    {
                        "code": "unaddressed_candidate",
                        "message": (
                            f"The following candidate ids were not "
                            f"addressed in either proposals or unrecognized: "
                            f"{missing}. Where: top-level proposal. How to "
                            f"fix: include every scoped candidate id in "
                            f"exactly one of proposals[].memberIds or "
                            f"unrecognized[].memberIds."
                        ),
                        "path": None,
                    }
                ]
                log_this(["unaddressed_candidate"])
                current_prompt = append_recognition_feedback(prompt, violations)
                continue

        result = validate_proposed_structure(merged, cg_context)
        if result["valid"]:
            # G10: demote (never block) low-confidence proposals.
            _demote_low_confidence(merged, confidence_floor)
            # G11: flag (never block) an uninformative flat confidence spread.
            confidences = [
                p.get("confidence")
                for p in merged["proposals"]
                if isinstance(p, dict) and isinstance(p.get("confidence"), (int, float))
            ]
            if _confidence_is_flat(confidences):
                flags.append("confidence_uninformative")

            # Stamp the run's LLM identity onto the validated proposal (F6).
            # Done AFTER validation so these keys can never influence it.
            merged["provider"] = provider
            merged["model"] = model
            log_this([])
            return {
                "valid": True,
                "proposal": merged,
                "attempts": attempt + 1,
                "tier": "0+1",
                "provider": provider,
                "model": model,
                "flags": flags,
            }
        violations = result["violations"]
        log_this([v["code"] for v in violations])
        current_prompt = append_recognition_feedback(prompt, violations)

    return {
        "valid": False,
        "violations": violations,
        "attempts": max_retries + 1,
        "provider": provider,
        "model": model,
        "flags": flags,
    }
