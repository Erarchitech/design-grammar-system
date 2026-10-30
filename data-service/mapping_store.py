"""Mapping sessions, decisions and profiles in the project graph (Phase 1303 MVP slice).

Persistence (1303-CONTEXT D-32, 1303-API-CONTRACT §6): project-scoped,
``graph: 'Computgraph'`` nodes ``MappingSession``, ``MappingDecision`` and
``MappingProfile`` with ``HAS_DECISION``, ``CREATED_PROFILE`` and
``ASSIGNS_ROLE`` edges. No ``Representation`` or ``MAPPED_AS`` is written by
this slice. Every statement binds ``$project`` and carries an ``// op=`` tag.

The orchestration functions (``create_session``, ``post_decision``,
``apply_session``, ``create_authored_profile``) call the low-level
persistence functions through this module's globals, so tests can replace
them with an in-memory fake.
"""

from __future__ import annotations

import base64
import hashlib
import json
import threading
import zlib
from datetime import datetime, timezone
from typing import Any, Optional

import mapping_engine as engine
import mapping_llm

GRAPH = "Computgraph"
_COMPRESS_OVER = 8 * 1024


def _get_driver():
    # Same lazy driver and env vars as dg_context (no second copy of the settings).
    import dg_context

    return dg_context._get_driver()


def utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


# ---------------------------------------------------------------------------
# JSON packing
# ---------------------------------------------------------------------------


def pack(obj: Any) -> str:
    """zlib + base64 of canonical JSON."""
    raw = engine.canonical_json(obj).encode("utf-8")
    return base64.b64encode(zlib.compress(raw, 6)).decode("ascii")


def unpack(text: Optional[str]) -> Any:
    if not text:
        return None
    return json.loads(zlib.decompress(base64.b64decode(text)).decode("utf-8"))


def _put_json(props: dict, name: str, obj: Any) -> None:
    text = engine.canonical_json(obj)
    if len(text) > _COMPRESS_OVER:
        props[name + "Z"] = pack(obj)
    else:
        props[name + "Json"] = text


def _get_json(props: dict, name: str, default: Any = None) -> Any:
    if props.get(name + "Z"):
        return unpack(props[name + "Z"])
    if props.get(name + "Json"):
        return json.loads(props[name + "Json"])
    return default


def _run(session, query: str, params: dict) -> list:
    if session is None:
        with _get_driver().session() as s:
            return [r.data() for r in s.run(query, params)]
    return [r.data() for r in session.run(query, params)]


# ---------------------------------------------------------------------------
# Reads of the project graph
# ---------------------------------------------------------------------------

CLASSES_QUERY = """
// op=mapping_classes
MATCH (c:Class)
WHERE c.project = $project AND c.graph = 'OntoGraph'
RETURN DISTINCT c.iri AS iri, coalesce(c.label, c.iri) AS label
ORDER BY iri
"""

RULE_ROWS_QUERY = """
// op=mapping_rule_rows
MATCH (r:Rule {project: $project, graph: 'Metagraph'})
WHERE NOT EXISTS { (r)-[:SUPERSEDED_BY]->() }
MATCH (r)-[:HAS_BODY]->(classAtom:Atom {type: 'ClassAtom'})-[:REFERS_TO]->(cls:Class)
MATCH (classAtom)-[:ARG]->(entityVar:Var)
MATCH (r)-[:HAS_BODY]->(propAtom:Atom {type: 'DataPropertyAtom'})-[:REFERS_TO]->(prop:DatatypeProperty)
MATCH (propAtom)-[:ARG {pos: 1}]->(entityVar)
MATCH (propAtom)-[:ARG {pos: 2}]->(valueVar:Var)
MATCH (r)-[:HAS_BODY]->(cmpAtom:Atom {type: 'BuiltinAtom'})-[:REFERS_TO]->(b:Builtin)
MATCH (cmpAtom)-[:ARG {pos: 1}]->(valueVar)
OPTIONAL MATCH (cmpAtom)-[:ARG {pos: 2}]->(lit:Literal)
RETURN DISTINCT r.Rule_Id AS ruleId, cls.iri AS classIri, prop.iri AS propertyIri,
       b.iri AS builtinIri, lit.lex AS lex, lit.datatype AS datatype
ORDER BY ruleId
"""

CLASS_RULES_QUERY = """
// op=mapping_class_rules
MATCH (r:Rule {project: $project, graph: 'Metagraph'})
WHERE NOT EXISTS { (r)-[:SUPERSEDED_BY]->() }
MATCH (r)-[:HAS_BODY]->(:Atom {type: 'ClassAtom'})-[:REFERS_TO]->(cls:Class)
RETURN cls.iri AS classIri, collect(DISTINCT r.Rule_Id) AS ruleIds
ORDER BY classIri
"""


# Design properties only: the ones rule bodies constrain, plus project properties that never
# appear in a rule head (heads carry violation flags such as widthBelowMin, which are not
# something a slider can drive).
PROPERTIES_QUERY = """
// op=mapping_properties
MATCH (p:DatatypeProperty)
WHERE EXISTS {
     MATCH (r:Rule {project: $project, graph: 'Metagraph'})-[:HAS_BODY]->(:Atom)-[:REFERS_TO]->(p)
   }
   OR (p.project = $project AND NOT EXISTS {
     MATCH (:Rule)-[:HAS_HEAD]->(:Atom)-[:REFERS_TO]->(p)
   })
RETURN DISTINCT p.iri AS iri, coalesce(p.SWRL_label, p.label, p.iri) AS label
ORDER BY iri
"""


def fetch_properties(session, project: str, constraints) -> list:
    """Datatype properties of the project; `classes` = classes whose rules constrain the property."""
    rows = _run(session, PROPERTIES_QUERY, {"project": project})
    classes_of: dict = {}
    for c in constraints:
        classes_of.setdefault(c.prop_local, set()).add(c.class_local)
    out = []
    for r in rows:
        if not r.get("iri"):
            continue
        local = engine.local_name(r["iri"])
        out.append(engine.PropertyInfo(str(r["iri"]), str(r["label"]), tuple(sorted(classes_of.get(local, ())))))
    return out


def fetch_classes(session, project: str) -> list:
    rows = _run(session, CLASSES_QUERY, {"project": project})
    return [engine.ClassInfo(str(r["iri"]), str(r["label"])) for r in rows if r.get("iri")]


def fetch_rule_rows(session, project: str) -> list:
    return _run(session, RULE_ROWS_QUERY, {"project": project})


def fetch_class_rules(session, project: str) -> dict:
    rows = _run(session, CLASS_RULES_QUERY, {"project": project})
    return {engine.local_name(r["classIri"]): sorted(r["ruleIds"] or []) for r in rows if r.get("classIri")}


# ---------------------------------------------------------------------------
# Profiles
# ---------------------------------------------------------------------------

PROFILES_QUERY = """
// op=mapping_profiles
MATCH (p:MappingProfile {project: $project})
RETURN properties(p) AS p
ORDER BY p.profileId
"""

PROFILE_MERGE_QUERY = """
// op=mapping_profile_merge
MERGE (p:MappingProfile {profileId: $profileId, project: $project})
SET p += $props
WITH p
OPTIONAL MATCH (d:MappingDecision {decisionId: $decisionId, project: $project})
FOREACH (_ IN CASE WHEN d IS NULL THEN [] ELSE [1] END | MERGE (d)-[:CREATED_PROFILE]->(p))
WITH p
UNWIND $roles AS role
OPTIONAL MATCH (c:Class {iri: role, project: $project, graph: 'OntoGraph'})
WITH p, role, head(collect(c)) AS cls
FOREACH (_ IN CASE WHEN cls IS NULL THEN [] ELSE [1] END | MERGE (p)-[:ASSIGNS_ROLE]->(cls))
RETURN count(*) AS linked
"""


def _profile_props(p: dict) -> dict:
    return {
        "graph": GRAPH,
        "platform": p.get("platform", "*"),
        "selectorJson": engine.canonical_json(p.get("selector") or {}),
        "rolesJson": engine.canonical_json(p.get("roles") or []),
        "excludedRolesJson": engine.canonical_json(p.get("excludedRoles") or []),
        "acceptsViolationsJson": engine.canonical_json(p.get("acceptsViolations") or []),
        "decisionIdsJson": engine.canonical_json(p.get("decisionIds") or []),
        "source": p.get("source", "learned"),
        "state": p.get("state", "active"),
        "confirmations": int(p.get("confirmations", 0)),
        "rejections": int(p.get("rejections", 0)),
        "support": int(p.get("support", 0)),
        "createdBy": p.get("createdBy"),
        "createdAt": p.get("createdAt"),
        "updatedAt": p.get("updatedAt") or p.get("createdAt"),
        "engineVersion": p.get("engineVersion", engine.ENGINE_VERSION),
        "comment": p.get("comment"),
    }


def _profile_from_props(project: str, props: dict) -> dict:
    p = {
        "profileId": props["profileId"],
        "project": project,
        "platform": props.get("platform", "*"),
        "selector": json.loads(props.get("selectorJson") or "{}"),
        "roles": json.loads(props.get("rolesJson") or "[]"),
        "excludedRoles": json.loads(props.get("excludedRolesJson") or "[]"),
        "acceptsViolations": json.loads(props.get("acceptsViolationsJson") or "[]"),
        "decisionIds": json.loads(props.get("decisionIdsJson") or "[]"),
        "source": props.get("source", "learned"),
        "state": props.get("state", "active"),
        "confirmations": int(props.get("confirmations") or 0),
        "rejections": int(props.get("rejections") or 0),
        "support": int(props.get("support") or 0),
        "createdBy": props.get("createdBy"),
        "createdAt": props.get("createdAt"),
        "updatedAt": props.get("updatedAt"),
        "engineVersion": props.get("engineVersion"),
    }
    if props.get("comment"):
        p["comment"] = props["comment"]
    p["confidence"] = engine.profile_confidence(p["confirmations"], p["rejections"])
    return p


def fetch_profiles(session, project: str) -> list:
    rows = _run(session, PROFILES_QUERY, {"project": project})
    return [_profile_from_props(project, r["p"]) for r in rows]


def save_profile(session, project: str, profile: dict, decision_id: Optional[str] = None) -> None:
    _run(
        session,
        PROFILE_MERGE_QUERY,
        {
            "project": project,
            "profileId": profile["profileId"],
            "props": _profile_props(profile),
            "decisionId": decision_id,
            "roles": list(profile.get("roles") or []),
        },
    )


# ---------------------------------------------------------------------------
# Sessions and decisions
# ---------------------------------------------------------------------------

SESSION_CREATE_QUERY = """
// op=mapping_session_create
CREATE (s:MappingSession {sessionId: $sessionId, project: $project})
SET s += $props
RETURN s.sessionId AS sessionId
"""

SESSION_LOAD_QUERY = """
// op=mapping_session_load
MATCH (s:MappingSession {sessionId: $sessionId, project: $project})
RETURN properties(s) AS s
"""

SESSION_UPDATE_QUERY = """
// op=mapping_session_update
MATCH (s:MappingSession {sessionId: $sessionId, project: $project})
SET s += $props
RETURN s.sessionId AS sessionId
"""

SESSION_LIST_QUERY = """
// op=mapping_session_list
MATCH (s:MappingSession {project: $project})
RETURN s.sessionId AS sessionId, s.platform AS platform, s.label AS label,
       s.engineVersion AS engineVersion, s.createdAt AS createdAt, s.createdBy AS createdBy,
       s.updatedAt AS updatedAt, s.summaryJson AS summaryJson, s.appliedAt AS appliedAt,
       s.appliedBy AS appliedBy, s.appliedCount AS appliedCount
ORDER BY s.createdAt DESC, s.sessionId DESC
LIMIT $limit
"""

SESSION_LATEST_APPLIED_QUERY = """
// op=mapping_session_latest_applied
MATCH (s:MappingSession {project: $project, platform: $platform})
WHERE s.appliedAt IS NOT NULL OR s.lastCommittedAt IS NOT NULL
RETURN s.sessionId AS sessionId
ORDER BY coalesce(s.lastCommittedAt, s.appliedAt) DESC, s.sessionId DESC
LIMIT 1
"""

DECISION_CREATE_QUERY = """
// op=mapping_decision_create
MATCH (s:MappingSession {sessionId: $sessionId, project: $project})
CREATE (d:MappingDecision {decisionId: $decisionId, project: $project})
SET d += $props
CREATE (s)-[:HAS_DECISION]->(d)
RETURN d.decisionId AS decisionId
"""


def _session_props(platform, label, descriptors, result, actor, created_at, context) -> dict:
    props = {
        "graph": GRAPH,
        "platform": platform,
        "label": label,
        "engineVersion": result.get("engineVersion", engine.ENGINE_VERSION),
        "createdAt": created_at,
        "createdBy": actor,
        "updatedAt": created_at,
        "summaryJson": engine.canonical_json(result["summary"]),
        "contextJson": engine.canonical_json(context or {}),
        "descriptorsZ": pack(descriptors),
        "resultZ": pack(result),
    }
    return props


def save_session(session, project, platform, label, descriptors, result, actor, created_at, context) -> str:
    digest = hashlib.sha1(
        f"{project}|{platform}|{actor}|{created_at}|{engine.canonical_json(descriptors)}".encode("utf-8")
    ).hexdigest()[:12]
    session_id = f"ms-{digest}"
    _run(
        session,
        SESSION_CREATE_QUERY,
        {"project": project, "sessionId": session_id, "props": _session_props(platform, label, descriptors, result, actor, created_at, context)},
    )
    return session_id


def load_session(session, project: str, session_id: str) -> Optional[dict]:
    rows = _run(session, SESSION_LOAD_QUERY, {"project": project, "sessionId": session_id})
    if not rows:
        return None
    s = rows[0]["s"]
    return {
        "sessionId": s["sessionId"],
        "project": project,
        "platform": s.get("platform"),
        "label": s.get("label"),
        "engineVersion": s.get("engineVersion"),
        "createdAt": s.get("createdAt"),
        "createdBy": s.get("createdBy"),
        "updatedAt": s.get("updatedAt"),
        "appliedAt": s.get("appliedAt"),
        "appliedBy": s.get("appliedBy"),
        "appliedCount": s.get("appliedCount"),
        "context": json.loads(s.get("contextJson") or "{}"),
        "descriptors": unpack(s.get("descriptorsZ")) or [],
        "result": unpack(s.get("resultZ")) or {},
        "batches": json.loads(s.get("batchesJson") or "[]"),
    }


def update_session_result(session, project: str, session_id: str, result: dict, at: str) -> None:
    _run(
        session,
        SESSION_UPDATE_QUERY,
        {
            "project": project,
            "sessionId": session_id,
            "props": {"resultZ": pack(result), "summaryJson": engine.canonical_json(result["summary"]), "updatedAt": at},
        },
    )


def record_apply(session, project: str, session_id: str, actor: str, at: str, count: int) -> None:
    _run(
        session,
        SESSION_UPDATE_QUERY,
        {"project": project, "sessionId": session_id, "props": {"appliedAt": at, "appliedBy": actor, "appliedCount": int(count)}},
    )


def latest_applied_session_id(session, project: str, platform: str = "grasshopper") -> Optional[str]:
    rows = _run(session, SESSION_LATEST_APPLIED_QUERY, {"project": project, "platform": platform})
    return rows[0]["sessionId"] if rows else None


def list_sessions(session, project: str, limit: int) -> list:
    rows = _run(session, SESSION_LIST_QUERY, {"project": project, "limit": int(limit)})
    out = []
    for r in rows:
        item = {k: v for k, v in r.items() if k != "summaryJson" and v is not None}
        item["project"] = project
        item["document"] = document_of(r.get("platform"), r.get("label"))
        item["summary"] = json.loads(r.get("summaryJson") or "{}")
        out.append(item)
    return out


DECISION_LIST_QUERY = """
// op=mapping_decision_list
MATCH (d:MappingDecision {project: $project, sessionId: $sessionId})
RETURN properties(d) AS d
ORDER BY d.decidedAt DESC, d.decisionId DESC
"""

DECISION_UNDO_QUERY = """
// op=mapping_decision_undo
MATCH (d:MappingDecision {project: $project, sessionId: $sessionId})
WHERE d.decisionId IN $decisionIds AND d.undoneAt IS NULL
SET d.undoneAt = $at, d.undoneBy = $actor
RETURN count(d) AS undone
"""


def fetch_decisions(session, project: str, session_id: str) -> list:
    """The session's decisions, newest first (undone ones included, marked by `undoneAt`)."""
    out = []
    for r in _run(session, DECISION_LIST_QUERY, {"project": project, "sessionId": session_id}):
        props = r["d"]
        out.append(
            {
                "decisionId": props.get("decisionId"),
                "answerId": props.get("answerId"),
                "questionId": props.get("questionId"),
                "groupId": props.get("groupId"),
                "optionId": props.get("optionId"),
                "questionText": props.get("questionText"),
                "memberIds": _get_json(props, "memberIds", []) or [],
                "answer": _get_json(props, "answer"),
                "decidedBy": props.get("decidedBy"),
                "decidedAt": props.get("decidedAt"),
                "undoneAt": props.get("undoneAt"),
                "committedAt": props.get("committedAt"),
                "roles": json.loads(props.get("rolesJson") or "[]"),
                "profileId": props.get("profileId"),
            }
        )
    return out


def mark_decisions_undone(session, project: str, session_id: str, decision_ids: list, actor: str, at: str) -> None:
    _run(session, DECISION_UNDO_QUERY, {"project": project, "sessionId": session_id, "decisionIds": list(decision_ids), "actor": actor, "at": at})


def save_decision(session, project: str, session_id: str, decision: dict) -> None:
    props = {
        "graph": GRAPH,
        "sessionId": session_id,
        "questionId": decision["questionId"],
        "groupId": decision["groupId"],
        "optionId": decision["optionId"],
        "rolesJson": engine.canonical_json(decision["roles"]),
        "memberCount": int(decision["memberCount"]),
        "questionText": decision["questionText"],
        "decidedBy": decision["decidedBy"],
        "decidedAt": decision["decidedAt"],
        "profileId": decision.get("profileId"),
    }
    if decision.get("answerId"):
        props["answerId"] = decision["answerId"]
        _put_json(props, "answer", decision.get("answer") or {})
    _put_json(props, "memberIds", decision.get("memberIds", []))
    _put_json(props, "evidence", decision.get("evidenceShown", []))
    _put_json(props, "consequences", decision.get("consequencesShown", []))
    _run(session, DECISION_CREATE_QUERY, {"project": project, "sessionId": session_id, "decisionId": decision["decisionId"], "props": props})


# ---------------------------------------------------------------------------
# Orchestration (used by the /mapping routes)
# ---------------------------------------------------------------------------


def _apply_vocabulary(classes: list, vocabulary: Optional[dict]) -> list:
    if not vocabulary:
        return classes
    synonyms = vocabulary.get("synonyms") or {}
    hints = vocabulary.get("ifcHints") or {}
    out = []
    for c in classes:
        keys = (c.label, c.local, c.iri)
        syn = next((synonyms[k] for k in keys if k in synonyms), ())
        ifc = next((hints[k] for k in keys if k in hints), ())
        out.append(engine.ClassInfo(c.iri, c.label, tuple(str(s) for s in syn), tuple(str(h) for h in ifc)))
    return out


def _clean_context(context: Optional[dict]) -> dict:
    context = context or {}
    vocab = context.get("vocabulary") or {}
    if not isinstance(vocab, dict):
        raise engine.MappingInputError("MAPPING_INPUT_INVALID", "context.vocabulary must be an object")
    clean_vocab = {}
    for key in ("synonyms", "ifcHints"):
        block = vocab.get(key) or {}
        if not isinstance(block, dict) or not all(isinstance(v, list) for v in block.values()):
            raise engine.MappingInputError("MAPPING_INPUT_INVALID", f"context.vocabulary.{key} must map class labels to lists")
        if block:
            clean_vocab[key] = {str(k): [str(x) for x in v] for k, v in block.items()}
    out = {}
    if clean_vocab:
        out["vocabulary"] = clean_vocab
    if context.get("populationsFromSessionId"):
        out["populationsFromSessionId"] = str(context["populationsFromSessionId"])
    return out


def _apply_property_vocabulary(properties: list, vocabulary: Optional[dict]) -> list:
    synonyms = (vocabulary or {}).get("synonyms") or {}
    if not synonyms:
        return properties
    out = []
    for p in properties:
        syn = next((synonyms[k] for k in (p.label, p.local, p.iri) if k in synonyms), ())
        out.append(engine.PropertyInfo(p.iri, p.label, p.classes, tuple(str(s) for s in syn)))
    return out


def _engine_inputs(session, project: str, vocabulary: Optional[dict]):
    classes = _apply_vocabulary(fetch_classes(session, project), vocabulary)
    constraints = engine.constraints_from_rows(fetch_rule_rows(session, project))
    rule_classes = fetch_class_rules(session, project)
    profiles = fetch_profiles(session, project)
    return classes, constraints, rule_classes, profiles


def _engine_properties(session, project: str, vocabulary: Optional[dict], constraints) -> list:
    return _apply_property_vocabulary(fetch_properties(session, project, constraints), vocabulary)


def document_of(platform: Optional[str], label: Optional[str], descriptors: Optional[list] = None) -> Optional[str]:
    """The document a session was read from: the label before « · »; for GH also the `gh:<key>:` prefix.

    The Revit connector labels its sessions `<document key> · HH:MM:SS` (D-48).
    """
    kind = str(platform or "").lower()
    if kind not in ("grasshopper", "revit"):
        return None
    text = str(label or "")
    if " · " in text:
        return text.split(" · ", 1)[0] or None
    if kind != "grasshopper":
        return None
    first = str((descriptors or [{}])[0].get("nativeId") or "") if descriptors else ""
    parts = first.split(":")
    return parts[1] if len(parts) > 2 and parts[0] == "gh" else None


def answers_of(decisions: list, applied: bool) -> list:
    """Given answers, newest first, undone ones left out; one answer = one POST …/decisions."""
    seen: dict = {}
    for d in decisions:
        if d.get("undoneAt"):
            continue
        aid = d.get("answerId") or d["decisionId"]
        if aid in seen:
            continue
        a = d.get("answer") or {}
        text = str(d.get("questionText") or "")
        short = text if len(text) <= 90 else text[:89] + "…"
        seen[aid] = {
            "answerId": aid,
            "questionId": d.get("questionId"),
            "type": a.get("type"),
            "title": a.get("title") or short,
            "titleRu": a.get("titleRu") or a.get("title") or short,
            "optionId": d.get("optionId"),
            "items": a.get("items") or [],
            "decidedAt": d.get("decidedAt"),
            "decidedBy": d.get("decidedBy"),
            # Answers recorded before plan 1303-10 carry no profile effects to reverse.
            "undoable": bool(d.get("answerId")) and not applied and not d.get("committedAt"),
            "committedAt": d.get("committedAt"),
            "accepted": any(it.get("proposal") for it in a.get("items") or []),
        }
    return list(seen.values())


def public_session(meta: dict, result: dict, answers: Optional[list] = None) -> dict:
    body = {
        "sessionId": meta["sessionId"],
        "project": meta["project"],
        "document": document_of(meta.get("platform") or result.get("platform"), meta.get("label"), meta.get("descriptors")),
        "answers": answers or [],
        "revision": session_revision(meta, result, answers or []),
        "pendingAnswerIds": [a["answerId"] for a in (answers or []) if a.get("accepted") and not a.get("committedAt")],
        "batches": meta.get("batches") or [],
        "platform": meta.get("platform") or result.get("platform"),
        "label": meta.get("label"),
        "engineVersion": result.get("engineVersion", engine.ENGINE_VERSION),
        "createdAt": meta.get("createdAt"),
        "createdBy": meta.get("createdBy"),
        "summary": result["summary"],
        "questions": result["questions"],
        "groups": result["groups"],
        "elements": result["elements"],
        "parameters": result.get("parameters", []),
        "measures": result.get("measures", []),
    }
    proposal = (meta.get("context") or {}).get("llm")
    if isinstance(proposal, dict):
        body["llm"] = {k: proposal.get(k) for k in ("status", "provider", "model", "error", "truncated") if proposal.get(k) is not None}
    for key in ("updatedAt", "appliedAt", "appliedBy", "appliedCount"):
        if meta.get(key) is not None:
            body[key] = meta[key]
    return body


def _llm_for_engine(ctx: dict) -> Optional[dict]:
    proposal = ctx.get("llm")
    return proposal if isinstance(proposal, dict) and proposal.get("status") == "ok" else None


def create_session(session, project, platform, label, elements, context, actor, created_at, parameters=None, measures=None) -> dict:
    platform = str(platform).lower()
    if platform not in ("grasshopper", "revit"):
        raise engine.MappingInputError("MAPPING_INPUT_INVALID", "platform must be grasshopper or revit")
    use_llm = bool((context or {}).get("llm"))
    ctx = _clean_context(context)
    classes, constraints, rule_classes, profiles = _engine_inputs(session, project, ctx.get("vocabulary"))
    properties = []
    if parameters:
        engine._validate_parameters(parameters, engine.CONFIG)
        ctx["parameters"] = parameters
    if measures:
        engine._validate_measures(measures, engine.CONFIG)
        ctx["measures"] = measures
    if parameters or measures:
        properties = _engine_properties(session, project, ctx.get("vocabulary"), constraints)
    populations = None
    if platform == "revit" and not ctx.get("populationsFromSessionId"):
        # D-49: a Revit read compares its group sizes with the latest applied GH session.
        latest = latest_applied_session_id(session, project, "grasshopper")
        if latest:
            ctx["populationsFromSessionId"] = latest
    if ctx.get("populationsFromSessionId"):
        ref = load_session(session, project, ctx["populationsFromSessionId"])
        if ref is None:
            raise engine.MappingInputError("MAPPING_SESSION_NOT_FOUND", "populationsFromSessionId does not name a session of this project", 404)
        if ref.get("appliedAt"):
            populations = engine.populations_of(ref["result"])  # historical whole-session contract
        else:
            committed = {el["nativeId"]: {**el, "state": "confirmed",
                         "roles": [{"classIri": iri} for iri in el["roles"]]}
                         for batch in ref.get("batches") or []
                         for el in batch["payload"].get("elements") or []}
            populations = engine.populations_of({"elements": list(committed.values())})
        ctx["populations"] = populations
    def run(llm=None):
        return engine.compute(
            elements,
            classes,
            constraints,
            profiles,
            populations=populations,
            platform_default=platform,
            rule_classes=rule_classes,
            parameters=parameters or None,
            properties=properties,
            measures=measures or None,
            llm=llm,
        )

    result = run()
    # D-37: ask the LLM only when the deterministic pass leaves questions (learned variants
    # need no paid call); its proposal is recorded and reused for every recompute. A slow
    # (reasoning) model must not hold the session back: by default the session is saved at
    # once and the proposal refines it in the background, keeping answers already given.
    ask = use_llm and result["summary"]["openQuestions"] > 0
    if ask and not LLM_ASYNC:
        ctx["llm"] = mapping_llm.propose_mapping(elements, measures or [], parameters or [], classes, properties, constraints)
        if _llm_for_engine(ctx):
            result = run(_llm_for_engine(ctx))
    elif ask:
        ctx["llm"] = {"status": "pending"}
    session_id = save_session(session, project, platform, label, elements, result, actor, created_at, ctx)
    if ask and LLM_ASYNC:
        threading.Thread(
            target=_refine_with_llm,
            args=(project, session_id, elements, measures or [], parameters or [], classes, properties, constraints),
            daemon=True,
        ).start()
    meta = {"sessionId": session_id, "project": project, "platform": platform, "label": label, "createdAt": created_at, "createdBy": actor,
            "context": ctx}
    profile_batch = queue_profile_batch(session, project, session_id, result, created_at)
    if profile_batch is not None:
        meta["batches"] = [profile_batch]
    return public_session(meta, result)


def queue_profile_batch(session, project: str, session_id: str, result: dict, at: str):
    """D-03: an element an active profile maps above the threshold (state ``auto``) is already confirmed; it is
    delivered without a further human confirmation. Since the explicit-confirmation rollout (2026-10-19) only
    accepted answers reached a batch, so elements added to a model and recognised by a profile were never
    written to the CAD file (owner, 2026-10-20: new openings were not mapped). One queued batch per session,
    ``source: profile``, answerIds empty; human answers still need the explicit confirmation."""
    auto = [el for el in result.get("elements") or [] if el.get("state") == "auto" and el.get("roles")]
    if not auto:
        return None
    constraints = engine.constraints_from_rows(fetch_rule_rows(session, project))
    part = engine.partition({"elements": auto}, constraints)
    part["bindings"] = engine.rule_bindings({"elements": auto, "measures": []}, constraints)
    batch = {"batchId": f"profile-{session_id}", "revision": "profile", "answerIds": [], "committedAt": at,
             "source": "profile", "payload": part, "delivery": {"state": "queued"}}
    save_batches(session, project, session_id, [batch])
    return batch


# Background LLM refinement (D-37). Tests set this to False for a synchronous call.
LLM_ASYNC = True


def _refine_with_llm(project, session_id, elements, measures, parameters, classes, properties, constraints) -> None:
    proposal = mapping_llm.propose_mapping(elements, measures, parameters, classes, properties, constraints)
    try:
        def refine(tx):
            lock_session(tx, project, session_id)
            s = load_session(tx, project, session_id)
            if s is None:
                return
            ctx = dict(s.get("context") or {})
            ctx["llm"] = proposal
            result = s["result"]
            # Serialize with answers and commits; a late proposal cannot overwrite their result.
            if proposal.get("status") == "ok" and not s.get("appliedAt"):
                c2, k2, rule_classes, profiles = _engine_inputs(tx, project, ctx.get("vocabulary"))
                current_properties = _engine_properties(tx, project, ctx.get("vocabulary"), k2)
                result = engine.compute(
                    s["descriptors"], c2, k2, profiles,
                    populations=ctx.get("populations"),
                    platform_default=s.get("platform") or "grasshopper",
                    decided=result.get("decided") or {},
                    splits=result.get("splits") or {},
                    rule_classes=rule_classes,
                    parameters=ctx.get("parameters") or None,
                    properties=current_properties,
                    decided_parameters=result.get("decidedParameters") or {},
                    measures=ctx.get("measures") or None,
                    decided_measures=result.get("decidedMeasures") or {},
                    llm=proposal,
                )
            _run(tx, SESSION_UPDATE_QUERY, {"project": project, "sessionId": session_id, "props": {
                "contextJson": engine.canonical_json(ctx),
                "resultZ": pack(result),
                "summaryJson": engine.canonical_json(result["summary"]),
                "updatedAt": utc_now(),
            }})

        with _get_driver().session() as session:
            session.execute_write(refine)
    except Exception:  # noqa: BLE001 - a lost refinement leaves the deterministic session in place
        return


def get_session(session, project: str, session_id: str) -> dict:
    s = load_session(session, project, session_id)
    if s is None:
        raise engine.MappingInputError("MAPPING_SESSION_NOT_FOUND", f"mapping session {session_id} not found", 404)
    return public_session(s, s["result"], answers_of(fetch_decisions(session, project, session_id), bool(s.get("appliedAt"))))


def _recompute(session, project: str, s: dict, ctx: dict, profiles: list, decided: dict, splits: dict,
               decided_parameters: dict, decided_measures: dict) -> dict:
    classes, constraints, rule_classes, _ = _engine_inputs(session, project, ctx.get("vocabulary"))
    parameters = ctx.get("parameters") or None
    measures = ctx.get("measures") or None
    properties = _engine_properties(session, project, ctx.get("vocabulary"), constraints) if (parameters or measures) else []
    return engine.compute(
        s["descriptors"],
        classes,
        constraints,
        profiles,
        populations=ctx.get("populations"),
        platform_default=s.get("platform") or "grasshopper",
        decided=decided,
        splits=splits,
        rule_classes=rule_classes,
        parameters=parameters,
        properties=properties,
        decided_parameters=decided_parameters,
        measures=measures,
        decided_measures=decided_measures,
        llm=_llm_for_engine(ctx),
    )


def _answer_items(question: dict, out: dict) -> list:
    """The question's rows as decided by this answer (plan 1303-10)."""
    by_group = {d["groupId"]: d["roles"] for d in out["decisions"]}
    decided_items = {**(out.get("decidedMeasures") or {}), **(out.get("decidedParameters") or {})}
    items = []
    for it in question.get("items") or []:
        roles = by_group.get(it["itemId"]) if it["kind"] == "stream" else decided_items.get(it["itemId"])
        if roles is None:
            continue  # a group left out of a batch answer
        labels = {x["iri"]: x["label"] for x in ([it["proposal"]] if it.get("proposal") else []) + list(it.get("alternatives") or [])}
        refs = [{"iri": r, "label": labels.get(r) or engine.local_name(r)} for r in roles]
        items.append({**it, "proposal": refs[0] if refs else None, "alternatives": refs[1:], "state": "confirmed" if refs else "unmapped"})
    return items


def _profile_effects(before: list, after: list) -> list:
    """What an answer did to each profile, so an undo can take exactly that back."""
    by_id = {p["profileId"]: p for p in before}
    effects = []
    for p in after:
        b = by_id.get(p["profileId"])
        effects.append(
            {
                "profileId": p["profileId"],
                "created": b is None,
                "confirmations": int(p.get("confirmations", 0)) - int((b or {}).get("confirmations", 0)),
                "rejections": int(p.get("rejections", 0)) - int((b or {}).get("rejections", 0)),
                "stateBefore": (b or {}).get("state", "active") if b else None,
            }
        )
    return effects


def post_decision(session, project, session_id, question_id, option_id, group_ids, roles, actor, at) -> dict:
    s = load_session(session, project, session_id)
    if s is None:
        raise engine.MappingInputError("MAPPING_SESSION_NOT_FOUND", f"mapping session {session_id} not found", 404)
    if s.get("appliedAt"):
        raise engine.MappingInputError("MAPPING_SESSION_APPLIED", "historical applied sessions are read-only", 409)
    ctx = s.get("context") or {}
    classes, constraints, rule_classes, profiles = _engine_inputs(session, project, ctx.get("vocabulary"))
    result = s["result"]
    out = engine.decide(
        result,
        s["descriptors"],
        question_id,
        option_id,
        actor,
        at,
        classes,
        group_ids=group_ids,
        roles=roles,
        profiles=profiles,
        project=project,
        platform_default=s.get("platform") or "grasshopper",
    )
    question = next((q for q in result.get("questions", []) if q["questionId"] == question_id), {})
    answer = {
        "answerId": "A-" + engine._sha(f"{session_id}|{question_id}|{option_id}|{at}", 12),
        "questionId": question_id,
        "type": question.get("type"),
        "title": question.get("title"),
        "titleRu": question.get("titleRu"),
        "items": _answer_items(question, out),
        "effects": [],
        "draftProfiles": out["profiles"],
    }
    for d in out["decisions"]:
        d["sessionId"] = session_id
        d["answerId"] = answer["answerId"]
        d["answer"] = answer
        save_decision(session, project, session_id, d)
    # Draft choices affect only this session's explicit decided maps, never global profiles.
    merged = profiles
    decided = dict(result.get("decided") or {})
    decided.update(out["decided"])
    splits = dict(result.get("splits") or {})
    splits.update(out["splits"])
    decided_parameters = dict(result.get("decidedParameters") or {})
    decided_parameters.update(out.get("decidedParameters") or {})
    decided_measures = dict(result.get("decidedMeasures") or {})
    decided_measures.update(out.get("decidedMeasures") or {})
    result2 = _recompute(session, project, s, ctx, merged, decided, splits, decided_parameters, decided_measures)
    update_session_result(session, project, session_id, result2, at)
    s["updatedAt"] = at
    decisions = [{k: v for k, v in d.items() if k not in ("memberIds", "answer")} for d in out["decisions"]]
    answers = answers_of(fetch_decisions(session, project, session_id), bool(s.get("appliedAt")))
    return {"decisions": decisions, "profiles": out["profiles"], "session": public_session(s, result2, answers)}


def undo_answer(session, project: str, session_id: str, answer_id: str, actor: str, at: str) -> dict:
    """Take one answer back (plan 1303-10): its decisions, the profile effects it had, a recompute."""
    s = load_session(session, project, session_id)
    if s is None:
        raise engine.MappingInputError("MAPPING_SESSION_NOT_FOUND", f"mapping session {session_id} not found", 404)
    if s.get("appliedAt"):
        raise engine.MappingInputError(
            "MAPPING_SESSION_APPLIED", "the session is applied; close the definition without saving and start again", 409
        )
    decisions = [d for d in fetch_decisions(session, project, session_id) if d.get("answerId") == answer_id and not d.get("undoneAt")]
    if not decisions or not decisions[0].get("answer"):
        raise engine.MappingInputError("MAPPING_ANSWER_NOT_FOUND", f"answer {answer_id} not found or already undone", 404)
    if any(d.get("committedAt") for d in decisions):
        raise engine.MappingInputError("MAPPING_ANSWER_COMMITTED", "a committed answer cannot be undone as a draft", 409)
    answer = decisions[0]["answer"]
    result = s["result"]
    decided = dict(result.get("decided") or {})
    decided_parameters = dict(result.get("decidedParameters") or {})
    decided_measures = dict(result.get("decidedMeasures") or {})
    for d in decisions:
        gid = str(d.get("groupId") or "")
        target = decided_parameters if gid.startswith("parameters:") else decided_measures if gid.startswith("measures:") else decided
        for nid in d.get("memberIds") or []:
            target.pop(nid, None)
    current = {p["profileId"]: p for p in fetch_profiles(session, project)}
    for e in answer.get("effects") or []:
        p = current.get(e["profileId"])
        if p is None:
            continue
        p = dict(p)
        p["confirmations"] = max(0, int(p.get("confirmations", 0)) - int(e.get("confirmations", 0)))
        p["rejections"] = max(0, int(p.get("rejections", 0)) - int(e.get("rejections", 0)))
        if e.get("created"):
            p["state"] = "retired"
        elif e.get("stateBefore"):
            p["state"] = e["stateBefore"]
        p["confidence"] = engine.profile_confidence(p["confirmations"], p["rejections"], engine.CONFIG)
        p["updatedAt"] = at
        save_profile(session, project, p)
        current[p["profileId"]] = p
    mark_decisions_undone(session, project, session_id, [d["decisionId"] for d in decisions], actor, at)
    ctx = s.get("context") or {}
    profiles = [current[k] for k in sorted(current)]
    result2 = _recompute(session, project, s, ctx, profiles, decided, dict(result.get("splits") or {}), decided_parameters, decided_measures)
    update_session_result(session, project, session_id, result2, at)
    s["updatedAt"] = at
    return public_session(s, result2, answers_of(fetch_decisions(session, project, session_id), False))


def session_revision(meta: dict, result: dict, answers: list) -> str:
    # The model snapshot status (Phase 1303-26) arrives after the apply; it must not make the next commit stale.
    batches = [{k: v for k, v in b.items() if k != "snapshot"} for b in meta.get("batches") or []]
    return engine._sha(engine.canonical_json({"result": result, "answers": answers, "batches": batches}), 24)


def lock_session(session, project: str, session_id: str) -> None:
    # Called within one explicit Neo4j transaction, before reading or changing the draft.
    if session is not None:
        _run(session, "MATCH (s:MappingSession {project:$project, sessionId:$sid}) "
             "SET s.commitLock = coalesce(s.commitLock, 0) + 1 RETURN s.sessionId AS id",
             {"project": project, "sid": session_id})


def last_human_commit(batches: list):
    """``lastCommittedAt`` reflects human confirmations only: a profile batch (D-03) does not make a session the
    "latest applied" population reference of D-49."""
    human = [b for b in batches if b.get("source") != "profile"]
    return human[-1]["committedAt"] if human else None


def save_batches(session, project: str, session_id: str, batches: list) -> None:
    _run(session, SESSION_UPDATE_QUERY, {"project": project, "sessionId": session_id,
                                       "props": {"batchesJson": engine.canonical_json(batches),
                                                 "lastCommittedAt": last_human_commit(batches)}})


def mark_decisions_committed(session, project, session_id, ids, actor, at):
    _run(session, "MATCH (s:MappingSession {project:$project, sessionId:$sid})-[:HAS_DECISION]->(d:MappingDecision) "
         "WHERE d.answerId IN $ids AND d.undoneAt IS NULL SET d.committedAt=$at, d.committedBy=$actor",
         {"project": project, "sid": session_id, "ids": ids, "actor": actor, "at": at})


def _batch_subset(result: dict, decisions: list) -> dict:
    selected = {"elements": set(), "parameters": set(), "measures": set()}
    for d in decisions:
        gid = str(d.get("groupId") or "")
        kind = "parameters" if gid.startswith("parameters:") else "measures" if gid.startswith("measures:") else "elements"
        # One parameter/measure answer may contain both accepted and excluded rows.
        decided_key = {"elements": "decided", "parameters": "decidedParameters", "measures": "decidedMeasures"}[kind]
        decided = result.get(decided_key) or {}
        selected[kind].update(nid for nid in d.get("memberIds") or [] if decided.get(nid))
    return {**result, **{kind: [r for r in result.get(kind) or [] if r["nativeId"] in ids]
                         for kind, ids in selected.items()}}


def apply_session(session, project: str, session_id: str, actor: str, at: str,
                  request_id=None, revision=None, answer_ids=None) -> dict:
    s = load_session(session, project, session_id)
    if s is None:
        raise engine.MappingInputError("MAPPING_SESSION_NOT_FOUND", f"mapping session {session_id} not found", 404)
    ids = sorted(answer_ids or [])
    batches = list(s.get("batches") or [])
    for batch in batches:
        if batch["batchId"] == request_id:
            if batch["answerIds"] != ids or batch["revision"] != revision:
                raise engine.MappingInputError("MAPPING_COMMIT_CONFLICT", "requestId already names another intent", 409)
            return batch
    decisions = fetch_decisions(session, project, session_id)
    answers = answers_of(decisions, bool(s.get("appliedAt")))
    pending = sorted(a["answerId"] for a in answers if a.get("accepted") and not a.get("committedAt"))
    if s.get("appliedAt") or not request_id or not ids or len(ids) != len(set(ids)) or ids != pending:
        raise engine.MappingInputError("MAPPING_COMMIT_CONFLICT", "confirm the current nonempty pending answer set", 409)
    if revision != session_revision(s, s["result"], answers):
        raise engine.MappingInputError("MAPPING_COMMIT_CONFLICT", "the draft changed; refresh before confirming", 409)
    chosen = [d for d in decisions if d.get("answerId") in ids and not d.get("undoneAt")]
    subset = _batch_subset(s["result"], chosen)
    known_classes = {c.iri for c in fetch_classes(session, project)}
    constraints = engine.constraints_from_rows(fetch_rule_rows(session, project))
    known_props = {p.iri for p in fetch_properties(session, project, constraints)}
    object_decisions = [d for d in chosen if not str(d.get("groupId") or "").startswith(("parameters:", "measures:"))]
    if any(role not in known_classes for d in object_decisions for role in d.get("roles") or []):
        raise engine.MappingInputError("MAPPING_INPUT_INVALID", "a selected class is no longer in the project OntoGraph", 409)
    selected_elements = {el["nativeId"]: sorted(r["classIri"] for r in el.get("roles") or []) for el in subset["elements"]}
    if any(selected_elements.get(nid) != sorted(d["roles"]) for d in object_decisions
           if d.get("roles") for nid in d.get("memberIds") or []):
        raise engine.MappingInputError("MAPPING_COMMIT_CONFLICT", "the selected element mapping changed", 409)
    if any(r["classIri"] not in known_classes for el in subset["elements"] for r in el.get("roles") or []):
        raise engine.MappingInputError("MAPPING_INPUT_INVALID", "a selected class is no longer in the project OntoGraph", 409)
    if any((r.get("property") or {}).get("iri") not in known_props for r in subset["measures"]):
        raise engine.MappingInputError("MAPPING_INPUT_INVALID", "a selected property is no longer in the project ontology", 409)
    part = engine.partition(subset, constraints)
    # Bindings may connect this batch to earlier committed objects/measures, never to remaining drafts.
    # Failed deliveries are excluded; queued predecessors are delivered in order by the connector.
    history = [b["payload"] for b in batches if b.get("delivery", {}).get("state") != "failed"]
    committed_elements = {el["nativeId"]: {**el, "state": "confirmed",
                          "roles": [{"classIri": iri} for iri in el["roles"]]}
                          for payload in history for el in payload.get("elements") or []}
    committed_measures = {m["nativeId"]: {**m, "state": "confirmed", "property": {"iri": m["propertyIri"]}}
                          for payload in history for m in payload.get("measures") or []}
    committed_elements.update({el["nativeId"]: el for el in subset["elements"]})
    committed_measures.update({m["nativeId"]: m for m in subset.get("measures") or []})
    part["bindings"] = engine.rule_bindings({"elements": list(committed_elements.values()),
                                            "measures": list(committed_measures.values())}, constraints)
    batch = {"batchId": request_id, "revision": revision, "answerIds": ids, "committedAt": at,
             "payload": part, "delivery": {"state": "queued"}}
    # Activate only profiles belonging to accepted answers, once, under the same lock.
    current = {p["profileId"]: p for p in fetch_profiles(session, project)}
    seen_answers = set()
    for d in chosen:
        aid = d["answerId"]
        if aid in seen_answers:
            continue
        seen_answers.add(aid)
        accepted_decisions = {row["decisionId"] for row in chosen if row.get("answerId") == aid and row.get("roles")}
        for draft in (d.get("answer") or {}).get("draftProfiles") or []:
            if not draft.get("roles") or not accepted_decisions.intersection(draft.get("decisionIds") or []):
                continue
            p = dict(draft)
            previous = current.get(p["profileId"])
            if previous and previous.get("state") == "retired":
                continue  # manual retirement is not undone by a mapping confirmation
            p["confirmations"] = int((previous or {}).get("confirmations", 0)) + 1
            p["state"], p["updatedAt"] = "active", at
            if previous:
                p["decisionIds"] = sorted(set(previous.get("decisionIds") or []) | set(p.get("decisionIds") or []))
            save_profile(session, project, p, d["decisionId"])
            current[p["profileId"]] = p
    mark_decisions_committed(session, project, session_id, ids, actor, at)
    save_batches(session, project, session_id, batches + [batch])
    return batch


def acknowledge_batch(session, project, session_id, batch_id, delivery):
    s = load_session(session, project, session_id)
    if s is None:
        raise engine.MappingInputError("MAPPING_SESSION_NOT_FOUND", "session not found", 404)
    batches = list(s.get("batches") or [])
    batch = next((b for b in batches if b["batchId"] == batch_id), None)
    if batch is None:
        raise engine.MappingInputError("MAPPING_COMMIT_CONFLICT", "unknown batch", 409)
    state = delivery.get("state")
    written, skipped = delivery.get("written"), delivery.get("skipped")
    total = batch["payload"]["applied"]
    if (state not in ("written", "failed") or type(written) is not int or type(skipped) is not int
            or min(written, skipped) < 0 or written + skipped != total
            or (state == "written" and skipped != 0)):
        raise engine.MappingInputError("MAPPING_INPUT_INVALID", "invalid CAD delivery counts")
    if batch["delivery"]["state"] != "queued" and batch["delivery"] != delivery:
        raise engine.MappingInputError("MAPPING_COMMIT_CONFLICT", "batch already acknowledged", 409)
    batch["delivery"] = dict(delivery)
    save_batches(session, project, session_id, batches)
    return batch


def set_batch_snapshot(session, project: str, session_id: str, batch_id: str, snapshot: dict) -> None:
    """Phase 1303-26 (D-79): the model snapshot status of a written batch, shown with the session's batches."""
    s = load_session(session, project, session_id)
    if s is None:
        return
    batches = list(s.get("batches") or [])
    for batch in batches:
        if batch.get("batchId") == batch_id:
            batch["snapshot"] = dict(snapshot)
            save_batches(session, project, session_id, batches)
            return


def list_profiles(session, project: str) -> dict:
    # Retired profiles stay in the graph and are never reactivated by draft answers or batch confirmation.
    return {"profiles": [p for p in fetch_profiles(session, project) if p.get("state", "active") == "active"]}


def create_authored_profile(session, project, platform, selector, roles, comment, actor, at) -> dict:
    platform = str(platform).lower()
    if platform not in ("grasshopper", "revit", "*"):
        raise engine.MappingInputError("MAPPING_INPUT_INVALID", "platform must be grasshopper, revit or *")
    if not isinstance(selector, dict) or not selector:
        raise engine.MappingInputError("MAPPING_INPUT_INVALID", "selector must be a non-empty object")
    if any(not isinstance(v, (str, int, float, bool)) for v in selector.values()):
        raise engine.MappingInputError("MAPPING_INPUT_INVALID", "selector values must be strings, numbers or booleans")
    known = {c.local: c.iri for c in fetch_classes(session, project)}
    if not roles or any(engine.local_name(r) not in known for r in roles):
        raise engine.MappingInputError("MAPPING_INPUT_INVALID", "roles must name classes of this project")
    iris = sorted(known[engine.local_name(r)] for r in roles)
    pid = engine.profile_id(platform, selector, iris)
    existing = next((p for p in fetch_profiles(session, project) if p["profileId"] == pid), None)
    profile = dict(existing) if existing else {
        "profileId": pid,
        "project": project,
        "platform": platform,
        "selector": dict(sorted(selector.items())),
        "roles": iris,
        "excludedRoles": [],
        "acceptsViolations": [],
        "source": "authored",
        "state": "active",
        "confirmations": 0,
        "rejections": 0,
        "support": 0,
        "createdBy": actor,
        "createdAt": at,
        "decisionIds": [],
        "engineVersion": engine.ENGINE_VERSION,
    }
    profile["confirmations"] = int(profile.get("confirmations", 0)) + 1
    profile["updatedAt"] = at
    if comment:
        profile["comment"] = str(comment)[:500]
    profile["confidence"] = engine.profile_confidence(profile["confirmations"], profile.get("rejections", 0))
    save_profile(session, project, profile)
    return profile
