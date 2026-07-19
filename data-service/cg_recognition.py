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
    `too_many_proposals`, `too_many_members`. Every message follows
    What+Where+How-to-fix phrasing.
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


# ── Frame few-shot fixture (Phase 35-02: A4 few-shot budget resolution) ──

FRAME_FEWSHOT_FILE = Path(__file__).resolve().parent / "fixtures" / "frame_recognition_fewshot.json"

_EMPTY_FEWSHOT: dict[str, Any] = {"input": {}, "expected": {"proposals": [], "unrecognized": []}}

_fewshot_cache: dict[str, Any] | None = None


def _load_frame_fewshot() -> dict[str, Any]:
    """Load the bundled Frame few-shot fixture once, cached at module scope
    (mirrors dg_context.load_cypher_catalog()'s defensive load pattern --
    never raises on a missing or malformed file)."""
    global _fewshot_cache
    if _fewshot_cache is not None:
        return _fewshot_cache
    if not FRAME_FEWSHOT_FILE.exists():
        _fewshot_cache = dict(_EMPTY_FEWSHOT)
        return _fewshot_cache
    try:
        _fewshot_cache = json.loads(FRAME_FEWSHOT_FILE.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        _fewshot_cache = dict(_EMPTY_FEWSHOT)
    return _fewshot_cache


# ── _build_recognition_prompt() -- deterministic prompt assembly (Phase 35-02) ──

_CONCEPT_CATALOG_MARKER = "=== COMPUTGRAPH CONCEPT CATALOG ==="
_FEWSHOT_MARKER = "=== FRAME FEW-SHOT EXAMPLE ==="
_TAGGED_ANCHOR_MARKER = "=== TAGGED ENTITIES (GROUND TRUTH -- DO NOT RENAME, SPLIT, OR ABSORB) ==="
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


def _trimmed_node_lines(cg_context: dict, node_ids: list[str]) -> list[str]:
    nodes_by_id = {
        n.get("instanceId"): n for n in (cg_context.get("nodes") or []) if isinstance(n, dict)
    }
    lines: list[str] = []
    for node_id in node_ids:
        node = nodes_by_id.get(node_id)
        if not node:
            continue
        lines.append(
            f"- {node_id}: name={node.get('name')!r} nickname={node.get('nickname')!r} "
            f"position={node.get('position')!r}"
        )
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


def _tagged_anchor_lines(cg_context: dict) -> list[str]:
    lines: list[str] = []
    for algorithm in cg_context.get("algorithms") or []:
        for procedure in algorithm.get("procedures") or []:
            if not isinstance(procedure, dict):
                continue
            if procedure.get("source") == "tagged":
                lines.append(
                    f"- Procedure '{procedure.get('name')}' (index "
                    f"{procedure.get('index')}, id {procedure.get('id')}) "
                    f"members: {procedure.get('memberIds')}"
                )
            for key, label in _ENTITY_LABEL_BY_KEY.items():
                for entity in procedure.get(key) or []:
                    if isinstance(entity, dict) and entity.get("source") == "tagged":
                        name = entity.get("label") or entity.get("name")
                        lines.append(
                            f"- {label} '{name}' (id {entity.get('id')}) "
                            f"members: {entity.get('memberIds')}"
                        )
    return lines


def _build_recognition_prompt(cg_context: dict, procedure_index: int | None) -> str:
    """Deterministically assemble the recognition prompt: concept catalog +
    annotation-convention grammar, the Frame few-shot, tagged entities as
    ground-truth anchors, the untagged nodes/wires/group hints (trimmed,
    scoped to `procedure_index` when set), and an explicit JSON-only output
    instruction. Fixed section order -- same request yields the same prompt
    every time (mirrors CTXA-05's determinism discipline)."""
    catalog = dg_knowledge.load_computgraph_catalog()
    fewshot = _load_frame_fewshot()

    scoped_node_ids = _filtered_untagged_node_ids(cg_context, procedure_index)
    scoped_groups = _filtered_untagged_groups(cg_context, scoped_node_ids, procedure_index)

    node_lines = _trimmed_node_lines(cg_context, scoped_node_ids) or ["(none)"]
    wire_lines = _trimmed_wire_lines(cg_context, scoped_node_ids) or ["(none)"]
    group_lines = [
        f"- {g.get('nickname')}: members {g.get('memberIds')}" for g in scoped_groups
    ] or ["(none)"]
    anchor_lines = _tagged_anchor_lines(cg_context) or ["(none)"]

    sections = [
        _CONCEPT_CATALOG_MARKER,
        f"entity_classes: {json.dumps(catalog.get('entity_classes'), sort_keys=True)}",
        f"relations: {json.dumps(catalog.get('relations'), sort_keys=True)}",
        f"enum_values: {json.dumps(catalog.get('enum_values'), sort_keys=True)}",
        "annotation_convention (DG Canvas Annotation Convention grammar):",
        json.dumps(catalog.get("annotation_convention"), sort_keys=True),
        "",
        _FEWSHOT_MARKER,
        json.dumps(fewshot, sort_keys=True),
        "",
        _TAGGED_ANCHOR_MARKER,
        *anchor_lines,
        "",
        _UNTAGGED_MARKER,
        "Nodes:",
        *node_lines,
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

    Returns `{"valid": True, "proposal": {...}, "attempts": N}` on success or
    `{"valid": False, "violations": [...], "attempts": N}` after the bound is
    exhausted (default `max_retries=2` => 3 attempts total).
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
            return {"valid": True, "proposal": parsed, "attempts": attempt + 1}
        violations = result["violations"]
        current_prompt = append_recognition_feedback(prompt, violations)

    return {"valid": False, "violations": violations, "attempts": max_retries + 1}
