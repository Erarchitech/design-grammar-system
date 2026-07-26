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
import logging
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


def _procedure_member_ids(cg_context: dict, procedure_index: int) -> set[str]:
    ids: set[str] = set()
    for algorithm in cg_context.get("algorithms") or []:
        for procedure in algorithm.get("procedures") or []:
            if isinstance(procedure, dict) and procedure.get("index") == procedure_index:
                ids.update(procedure.get("memberIds") or [])
    return ids


def _filtered_untagged_node_ids(cg_context: dict, procedure_index: int | None) -> list[str]:
    """Untagged node ids in scope for the prompt. With no `procedure_index`,
    every untagged node is in scope. With one, scope narrows to untagged
    nodes wired (one hop) to that procedure's tagged member ids -- the only
    per-procedure signal cgContextJson v1's `untagged` block carries, since
    untagged nodes have no procedure ownership field of their own."""
    node_ids = list((cg_context.get("untagged") or {}).get("nodeIds") or [])
    if procedure_index is None:
        return node_ids

    procedure_ids = _procedure_member_ids(cg_context, procedure_index)
    if not procedure_ids:
        return node_ids

    node_id_set = set(node_ids)
    adjacent: set[str] = set()
    for wire in cg_context.get("wires") or []:
        from_node = wire.get("fromNode")
        to_node = wire.get("toNode")
        if from_node in procedure_ids and to_node in node_id_set:
            adjacent.add(to_node)
        if to_node in procedure_ids and from_node in node_id_set:
            adjacent.add(from_node)
    return [n for n in node_ids if n in adjacent]


def _filtered_untagged_groups(cg_context: dict, scoped_node_ids: list[str], procedure_index: int | None) -> list[dict]:
    groups = (cg_context.get("untagged") or {}).get("groups") or []
    if procedure_index is None:
        return groups
    scoped = set(scoped_node_ids)
    return [g for g in groups if any(m in scoped for m in (g.get("memberIds") or []))]


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


# ── recognize_structure() -- bounded retry loop (Phase 35-02: mirrors CTXA-04) ──


def recognize_structure(
    cg_context: dict, procedure_index: int | None = None, max_retries: int = 2
) -> dict:
    """Classify untagged canvas entities into a schema-valid proposed-structure
    object via the LLM gateway, with a bounded corrective-feedback retry
    (mirrors `dg_context.generate_validated_cypher()`'s exact loop structure).

    Resolves the active provider/adapter ONCE before the loop and calls
    `adapter.generate()` in-process each attempt -- NEVER re-POSTs to
    `/llm/generate` (RESEARCH.md Anti-pattern guard).

    Returns `{"valid": True, "proposal": {...}, "attempts": N, "provider": ...,
    "model": ...}` on success or `{"valid": False, "violations": [...],
    "attempts": N, "provider": ..., "model": ...}` after the bound is exhausted
    (default `max_retries=2` => 3 attempts total).

    `provider`/`model` are the resolved LLM identity behind the proposal (Phase
    36 UAT F6). They are ALSO injected into the returned `proposal` object, so a
    caller can hand `result["proposal"]` straight to `gh_preview_structure`
    without re-stitching provenance: the listener reads them off the top level of
    the preview command, carries them through the PreviewRegistry, and
    `DG STRUCTURE CONFIRM` stamps them into the canvas recognition marker. Before
    F6 this identity was resolved here and then dropped, so every recognized node
    published with `provider`/`model`/`confidence = null`.
    """
    prompt = _build_recognition_prompt(cg_context, procedure_index)

    master_secret = os.getenv("LLM_MASTER_SECRET", "")
    settings = load_persisted_llm_settings()
    provider, model, api_key = resolve_active_provider(settings, master_secret)
    adapter = get_adapter(provider, settings.get("baseUrl"))

    current_prompt = prompt
    violations: list[dict[str, Any]] = []
    for attempt in range(max_retries + 1):
        req = GenerateRequest(prompt=current_prompt, model=model, provider=provider)
        response = adapter.generate(req, api_key)

        parsed, parse_error = _extract_json(response.text)
        if parse_error:
            violations = [{"code": "bad_json", "message": parse_error, "path": None}]
            current_prompt = append_recognition_feedback(prompt, violations)
            continue

        result = validate_proposed_structure(parsed, cg_context)
        if result["valid"]:
            # Stamp the run's LLM identity onto the validated proposal (F6). Done
            # AFTER validation so these keys can never influence it, and only on
            # the success path so an invalid proposal is never made to look
            # attributable.
            if isinstance(parsed, dict):
                parsed["provider"] = provider
                parsed["model"] = model
            return {
                "valid": True,
                "proposal": parsed,
                "attempts": attempt + 1,
                "provider": provider,
                "model": model,
            }
        violations = result["violations"]
        current_prompt = append_recognition_feedback(prompt, violations)

    return {
        "valid": False,
        "violations": violations,
        "attempts": max_retries + 1,
        "provider": provider,
        "model": model,
    }
