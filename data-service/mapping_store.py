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
import zlib
from datetime import datetime, timezone
from typing import Any, Optional

import mapping_engine as engine

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
WHERE c.project = $project
   OR EXISTS {
     MATCH (r:Rule {project: $project, graph: 'Metagraph'})-[:HAS_BODY|HAS_HEAD]->(:Atom)-[:REFERS_TO]->(c)
   }
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
OPTIONAL MATCH (c:Class {iri: role})
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


def list_sessions(session, project: str, limit: int) -> list:
    rows = _run(session, SESSION_LIST_QUERY, {"project": project, "limit": int(limit)})
    out = []
    for r in rows:
        item = {k: v for k, v in r.items() if k != "summaryJson" and v is not None}
        item["project"] = project
        item["summary"] = json.loads(r.get("summaryJson") or "{}")
        out.append(item)
    return out


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


def public_session(meta: dict, result: dict) -> dict:
    body = {
        "sessionId": meta["sessionId"],
        "project": meta["project"],
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
    }
    for key in ("updatedAt", "appliedAt", "appliedBy", "appliedCount"):
        if meta.get(key) is not None:
            body[key] = meta[key]
    return body


def create_session(session, project, platform, label, elements, context, actor, created_at, parameters=None) -> dict:
    platform = str(platform).lower()
    if platform not in ("grasshopper", "revit"):
        raise engine.MappingInputError("MAPPING_INPUT_INVALID", "platform must be grasshopper or revit")
    ctx = _clean_context(context)
    classes, constraints, rule_classes, profiles = _engine_inputs(session, project, ctx.get("vocabulary"))
    properties = []
    if parameters:
        engine._validate_parameters(parameters, engine.CONFIG)
        ctx["parameters"] = parameters
        properties = _engine_properties(session, project, ctx.get("vocabulary"), constraints)
    populations = None
    if ctx.get("populationsFromSessionId"):
        ref = load_session(session, project, ctx["populationsFromSessionId"])
        if ref is None:
            raise engine.MappingInputError("MAPPING_SESSION_NOT_FOUND", "populationsFromSessionId does not name a session of this project", 404)
        populations = engine.populations_of(ref["result"])
        ctx["populations"] = populations
    result = engine.compute(
        elements,
        classes,
        constraints,
        profiles,
        populations=populations,
        platform_default=platform,
        rule_classes=rule_classes,
        parameters=parameters or None,
        properties=properties,
    )
    session_id = save_session(session, project, platform, label, elements, result, actor, created_at, ctx)
    meta = {"sessionId": session_id, "project": project, "platform": platform, "label": label, "createdAt": created_at, "createdBy": actor}
    return public_session(meta, result)


def get_session(session, project: str, session_id: str) -> dict:
    s = load_session(session, project, session_id)
    if s is None:
        raise engine.MappingInputError("MAPPING_SESSION_NOT_FOUND", f"mapping session {session_id} not found", 404)
    return public_session(s, s["result"])


def post_decision(session, project, session_id, question_id, option_id, group_ids, roles, actor, at) -> dict:
    s = load_session(session, project, session_id)
    if s is None:
        raise engine.MappingInputError("MAPPING_SESSION_NOT_FOUND", f"mapping session {session_id} not found", 404)
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
    created = {d["profileId"]: d["decisionId"] for d in out["decisions"]}
    for d in out["decisions"]:
        d["sessionId"] = session_id
        save_decision(session, project, session_id, d)
    for p in out["profiles"]:
        save_profile(session, project, p, created.get(p["profileId"]))
    merged = engine.merge_profiles(profiles, out["profiles"])
    decided = dict(result.get("decided") or {})
    decided.update(out["decided"])
    splits = dict(result.get("splits") or {})
    splits.update(out["splits"])
    parameters = ctx.get("parameters") or None
    decided_parameters = dict(result.get("decidedParameters") or {})
    decided_parameters.update(out.get("decidedParameters") or {})
    properties = _engine_properties(session, project, ctx.get("vocabulary"), constraints) if parameters else []
    result2 = engine.compute(
        s["descriptors"],
        classes,
        constraints,
        merged,
        populations=ctx.get("populations"),
        platform_default=s.get("platform") or "grasshopper",
        decided=decided,
        splits=splits,
        rule_classes=rule_classes,
        parameters=parameters,
        properties=properties,
        decided_parameters=decided_parameters,
    )
    update_session_result(session, project, session_id, result2, at)
    s["updatedAt"] = at
    decisions = [{k: v for k, v in d.items() if k != "memberIds"} for d in out["decisions"]]
    return {"decisions": decisions, "profiles": out["profiles"], "session": public_session(s, result2)}


def apply_session(session, project: str, session_id: str, actor: str, at: str) -> dict:
    s = load_session(session, project, session_id)
    if s is None:
        raise engine.MappingInputError("MAPPING_SESSION_NOT_FOUND", f"mapping session {session_id} not found", 404)
    part = engine.partition(s["result"])
    record_apply(session, project, session_id, actor, at, part["applied"])
    return {"project": project, "sessionId": session_id, **part}


def list_profiles(session, project: str) -> dict:
    return {"profiles": fetch_profiles(session, project)}


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
