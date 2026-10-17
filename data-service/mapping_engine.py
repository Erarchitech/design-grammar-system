"""Deterministic mapping engine for the Phase 1303 MVP slice.

Turns element descriptors from Grasshopper or Revit into multi-role DG class
candidates, groups them, asks few consequence-framed questions, records
decisions and induces reusable mapping profiles.

The module is pure: no Neo4j, HTTP, clock, random or LLM input. The same
descriptors, classes, constraints, profiles and decisions always give the
same result (1303-CONTEXT D-11). Shapes follow
.planning/phases/1303-pravilo-gh-obekt/1303-API-CONTRACT.md.

Evidence sources (D-12): learned or authored profiles, name tokens, rule
consistency (DG rules use the violation pattern, so a body comparison is
inverted into the required constraint), IFC hints and population match.
"""

from __future__ import annotations

import hashlib
import json
import math
import re
from dataclasses import dataclass
from typing import Any, Iterable, Mapping, Optional, Sequence

ENGINE_VERSION = "dgmap-0.1"

CONFIG: dict[str, float] = {
    "prior": -1.0,
    "w_profile": 4.0,
    "w_name_acronym": 2.0,
    "w_name_subsequence": 1.0,
    "w_name_token": 1.5,
    "w_name_cap": 3.0,
    # Rule consistency is weighted by specificity: an equality constraint
    # (hasVertexCount == 6) is a class signature, a range constraint
    # (hasWidthM >= 4.5) is weak support, so a class with many range rules
    # cannot outvote a class with one matching signature.
    "w_rule_eq_satisfied": 2.5,
    "w_rule_range_satisfied": 0.75,
    "w_rule_cap": 4.0,
    "w_rule_eq_violated": -1.5,
    "w_rule_range_violated": -2.0,
    "w_ifc": 2.0,
    "w_population": 1.0,
    "tau_candidate": 0.6,
    "tau_clear": 0.8,
    "margin_delta": 0.3,
    "profile_auto": 0.8,
    "profile_alpha": 4,
    "profile_beta": 1,
    "max_elements": 5000,
    "representatives": 3,
}

SELECTOR_FEATURES = (
    "platform",
    "source",
    "category",
    "family",
    "type",
    "geometry.kind",
    "geometry.vertexCount",
    "geometry.closed",
)

# Order in which profile induction tries to drop selector keys (most specific first).
DROP_ORDER = ("type", "family", "geometry.closed", "geometry.kind", "category", "source")

PROPERTY_ALIASES = {
    "hasVertexCount": "geometry.vertexCount",
    "hasGapCount": "geometry.gapCount",
    "hasWidthM": "geometry.widthM",
    "hasPlanarityDeviationM": "geometry.planarityDeviationM",
}

# Violation pattern: the body builtin is true when the rule is violated, so the
# required constraint is its negation (same semantics as
# cg_input_bindings.BODY_BUILTIN_TO_CONSTRAINT, plus `equal`).
BUILTIN_TO_REQUIRED = {
    "greaterThan": "<=",
    "lessThan": ">=",
    "notEqual": "==",
    "greaterThanOrEqual": "<",
    "lessThanOrEqual": ">",
    "equal": "!=",
}

STATES = ("confirmed", "auto", "suggested", "ambiguous", "unmapped")
NAME_FIELDS = ("source", "family", "type", "name", "category")


class MappingInputError(ValueError):
    """Invalid engine input; carries an API error code and HTTP status."""

    def __init__(self, code: str, detail: str, status: int = 400):
        super().__init__(detail)
        self.code = code
        self.detail = detail
        self.status = status


@dataclass(frozen=True)
class ClassInfo:
    iri: str
    label: str
    synonyms: tuple = ()
    ifc_hints: tuple = ()

    @property
    def local(self) -> str:
        return local_name(self.iri)


@dataclass(frozen=True)
class Constraint:
    rule_id: str
    class_local: str
    prop_local: str
    op: str
    value: float

    def describe(self) -> str:
        return f"{self.prop_local} {self.op} {_fmt(self.value)}"


@dataclass(frozen=True)
class Evidence:
    class_local: str
    kind: str
    weight: float
    detail: str


# ---------------------------------------------------------------------------
# Small helpers
# ---------------------------------------------------------------------------


def local_name(iri: Any) -> str:
    text = str(iri or "")
    for sep in ("#", "/", ":"):
        if sep in text:
            text = text.rsplit(sep, 1)[1]
    return text


def canonical_json(obj: Any) -> str:
    return json.dumps(obj, sort_keys=True, ensure_ascii=False, separators=(",", ":"))


def _sha(text: str, n: int) -> str:
    return hashlib.sha1(text.encode("utf-8")).hexdigest()[:n]


def _r(x: float) -> float:
    return round(float(x), 4)


def _fmt(x: float) -> str:
    if float(x).is_integer():
        return str(int(x))
    return f"{x:g}"


def _logistic(score: float) -> float:
    return 1.0 / (1.0 + math.exp(-score))


_CAMEL = re.compile(r"(?<=[a-z0-9])(?=[A-Z])|(?<=[A-Z])(?=[A-Z][a-z])")


def split_tokens(text: Any) -> list[str]:
    raw = _CAMEL.sub(" ", str(text or ""))
    return [t.lower() for t in re.split(r"[^0-9A-Za-zА-Яа-яЁё]+", raw) if t]


def class_tokens(label: str) -> tuple:
    return tuple(split_tokens(label))


def class_acronym(label: str) -> str:
    return "".join(t[0] for t in class_tokens(label) if t)


def _is_subsequence(short: str, long: str) -> bool:
    it = iter(long)
    return all(ch in it for ch in short)


def _num(v: Any) -> Optional[float]:
    if isinstance(v, bool):
        return None
    if isinstance(v, (int, float)):
        return float(v)
    if isinstance(v, str):
        try:
            return float(v.strip())
        except ValueError:
            return None
    return None


def _norm(v: Any) -> Any:
    """Normalised value used for selector matching and signatures."""
    if isinstance(v, bool):
        return v
    if isinstance(v, (int, float)):
        f = round(float(v), 9)
        return int(f) if f.is_integer() else f
    return str(v).strip().lower()


def profile_confidence(confirmations: int, rejections: int, config: Optional[Mapping] = None) -> float:
    cfg = config or CONFIG
    a, b = cfg["profile_alpha"], cfg["profile_beta"]
    return _r((confirmations + a) / (confirmations + rejections + a + b))


def _ru_plural(n: int, forms: tuple) -> str:
    n = abs(int(n))
    if n % 10 == 1 and n % 100 != 11:
        return forms[0]
    if 2 <= n % 10 <= 4 and not 12 <= n % 100 <= 14:
        return forms[1]
    return forms[2]


def _en_plural(n: int, one: str, many: str) -> str:
    return one if int(n) == 1 else many


# ---------------------------------------------------------------------------
# Features, constraints
# ---------------------------------------------------------------------------


def features(descriptor: Mapping, platform_default: str = "grasshopper") -> dict:
    f: dict[str, Any] = {}
    platform = descriptor.get("platform") or platform_default
    f["platform"] = str(platform).strip().lower()
    for key in NAME_FIELDS:
        v = descriptor.get(key)
        if v not in (None, ""):
            f[key] = str(v)
    ifc = descriptor.get("ifc")
    if isinstance(ifc, Mapping):
        if ifc.get("entity"):
            f["ifc.entity"] = str(ifc["entity"])
        if ifc.get("predefinedType"):
            f["ifc.predefinedType"] = str(ifc["predefinedType"])
    for group in ("geometry", "properties", "parameters"):
        block = descriptor.get(group)
        if isinstance(block, Mapping):
            for k, v in block.items():
                if isinstance(v, (str, int, float, bool)) and v != "":
                    f[f"{group}.{k}"] = v
    return f


def property_value(feats: Mapping, prop_local: str) -> Optional[float]:
    v = _num(feats.get(f"properties.{prop_local}"))
    if v is None and prop_local in PROPERTY_ALIASES:
        v = _num(feats.get(PROPERTY_ALIASES[prop_local]))
    return v


def constraints_from_rows(rows: Iterable[Mapping]) -> list[Constraint]:
    """Rows: {ruleId, classIri, propertyIri, builtinIri, lex}. Never raises."""
    out: dict[tuple, Constraint] = {}
    for row in rows or ():
        try:
            op = BUILTIN_TO_REQUIRED.get(local_name(row.get("builtinIri")))
            value = _num(row.get("lex"))
            rule_id = str(row.get("ruleId") or "")
            cls = local_name(row.get("classIri"))
            prop = local_name(row.get("propertyIri"))
        except Exception:  # noqa: BLE001 - malformed rows are skipped by contract
            continue
        if not (op and rule_id and cls and prop) or value is None:
            continue
        c = Constraint(rule_id, cls, prop, op, value)
        out[(rule_id, cls, prop, op, value)] = c
    return sorted(out.values(), key=lambda c: (c.rule_id, c.class_local, c.prop_local))


_SWRL_CLASS = re.compile(r"(?:^|\^)\s*([A-Za-z_][\w:#/.-]*)\(\s*\?(\w+)\s*\)")
_SWRL_PROP = re.compile(r"([A-Za-z_][\w:#/.-]*)\(\s*\?(\w+)\s*,\s*\?(\w+)\s*\)")
_SWRL_CMP = re.compile(r"swrlb:(\w+)\(\s*\?(\w+)\s*,\s*(-?\d+(?:\.\d+)?)\s*\)")


def constraints_from_swrl(rule_id: str, swrl: str) -> list[Constraint]:
    """Plain body pattern `Class(?x) ^ prop(?x, ?v) ^ swrlb:op(?v, number)`."""
    body = (swrl or "").split("->", 1)[0]
    classes = {var: local_name(name) for name, var in _SWRL_CLASS.findall(body) if not name.startswith("swrlb")}
    props = {val: (local_name(name), ent) for name, ent, val in _SWRL_PROP.findall(body) if not name.startswith("swrlb")}
    out = []
    for builtin, var, number in _SWRL_CMP.findall(body):
        op = BUILTIN_TO_REQUIRED.get(builtin)
        if not op or var not in props:
            continue
        prop, ent = props[var]
        cls = classes.get(ent)
        if cls:
            out.append(Constraint(rule_id, cls, prop, op, float(number)))
    return out


def rules_by_class(constraints: Iterable[Constraint], extra: Optional[Mapping] = None) -> dict:
    out: dict[str, set] = {}
    for c in constraints:
        out.setdefault(c.class_local, set()).add(c.rule_id)
    for cls, rules in (extra or {}).items():
        out.setdefault(local_name(cls), set()).update(rules)
    return {k: sorted(v) for k, v in sorted(out.items())}


def check_constraint(c: Constraint, value: float) -> bool:
    eps = 1e-9
    if c.op == "==":
        return abs(value - c.value) <= eps
    if c.op == "!=":
        return abs(value - c.value) > eps
    if c.op == "<=":
        return value <= c.value + eps
    if c.op == ">=":
        return value >= c.value - eps
    if c.op == "<":
        return value < c.value - eps
    if c.op == ">":
        return value > c.value + eps
    return False


# ---------------------------------------------------------------------------
# Evidence
# ---------------------------------------------------------------------------


def profile_matches(profile: Mapping, feats: Mapping) -> bool:
    if profile.get("state", "active") != "active":
        return False
    platform = str(profile.get("platform") or "*").lower()
    if platform != "*" and platform != feats.get("platform"):
        return False
    selector = profile.get("selector") or {}
    if not selector:
        return False
    for key, value in selector.items():
        if key not in feats or _norm(feats[key]) != _norm(value):
            return False
    return True


def _profile_conf(profile: Mapping, cfg: Mapping) -> float:
    return profile_confidence(int(profile.get("confirmations", 0)), int(profile.get("rejections", 0)), cfg)


def ev_profiles(feats: Mapping, profiles: Sequence[Mapping], cfg: Mapping) -> tuple:
    evidence: list[Evidence] = []
    matched = []
    for p in profiles:
        if not profile_matches(p, feats):
            continue
        conf = _profile_conf(p, cfg)
        matched.append((p, conf))
        for role in p.get("roles") or ():
            evidence.append(Evidence(local_name(role), "profile", cfg["w_profile"] * conf, f"profile {p['profileId']} (confidence {conf:.2f})"))
        for role in p.get("excludedRoles") or ():
            evidence.append(Evidence(local_name(role), "profile", -cfg["w_profile"] * conf, f"profile {p['profileId']} excludes this class"))
    return evidence, matched


def _name_tokens(feats: Mapping) -> set:
    toks: set = set()
    for key in NAME_FIELDS:
        if key in feats:
            toks.update(split_tokens(feats[key]))
    return toks


def ev_name(feats: Mapping, classes: Sequence[ClassInfo], cfg: Mapping) -> list[Evidence]:
    toks = _name_tokens(feats)
    if not toks:
        return []
    out = []
    for c in classes:
        acr = class_acronym(c.label)
        words = set(class_tokens(c.label))
        for syn in c.synonyms:
            words.update(split_tokens(syn))
        total, parts = 0.0, []
        for t in sorted(toks):
            if acr and t == acr:
                total += cfg["w_name_acronym"]
                parts.append(f"'{t}' is the acronym of {c.label}")
            elif acr and len(t) < len(acr) and t[0] == acr[0] and _is_subsequence(t, acr):
                total += cfg["w_name_subsequence"]
                parts.append(f"'{t}' abbreviates {c.label}")
            if len(t) >= 3 and t in words:
                total += cfg["w_name_token"]
                parts.append(f"word '{t}' matches {c.label}")
        if total:
            out.append(Evidence(c.local, "name", min(total, cfg["w_name_cap"]), "; ".join(parts)))
    return out


def _is_equality(c: Constraint) -> bool:
    return c.op in ("==", "!=")


def ev_rules(feats: Mapping, constraints: Sequence[Constraint], cfg: Mapping) -> tuple:
    """Returns (evidence, stats) with stats[class] = {"sat": [...], "vio": [(rule, detail)]}."""
    stats: dict[str, dict] = {}
    weights: dict[str, dict] = {}
    for c in constraints:
        value = property_value(feats, c.prop_local)
        if value is None:
            continue
        s = stats.setdefault(c.class_local, {"sat": [], "vio": []})
        w = weights.setdefault(c.class_local, {"sat": 0.0, "vio": 0.0})
        if check_constraint(c, value):
            s["sat"].append(c.rule_id)
            w["sat"] += cfg["w_rule_eq_satisfied"] if _is_equality(c) else cfg["w_rule_range_satisfied"]
        else:
            s["vio"].append((c.rule_id, f"{c.prop_local} = {_fmt(value)}, required {c.op} {_fmt(c.value)}"))
            w["vio"] += cfg["w_rule_eq_violated"] if _is_equality(c) else cfg["w_rule_range_violated"]
    evidence = []
    for cls, s in sorted(stats.items()):
        if s["sat"]:
            evidence.append(Evidence(cls, "rule", min(weights[cls]["sat"], cfg["w_rule_cap"]), "rules satisfied: " + ", ".join(sorted(set(s["sat"])))))
        if s["vio"]:
            ids = sorted({r for r, _ in s["vio"]})
            evidence.append(Evidence(cls, "rule", weights[cls]["vio"], "rules violated: " + ", ".join(ids)))
    return evidence, stats


def ev_ifc(feats: Mapping, classes: Sequence[ClassInfo], cfg: Mapping) -> list[Evidence]:
    entity = str(feats.get("ifc.entity") or "").lower()
    if not entity:
        return []
    predefined = str(feats.get("ifc.predefinedType") or "").lower()
    out = []
    for c in classes:
        for hint in c.ifc_hints:
            h_entity, _, h_pre = str(hint).partition(".")
            if h_entity.lower() == entity and (not h_pre or h_pre.lower() == predefined):
                out.append(Evidence(c.local, "ifc", cfg["w_ifc"], f"IFC {feats.get('ifc.entity')} matches hint {hint}"))
                break
    return out


def ev_population(group_size: int, populations: Optional[Mapping], known: set, cfg: Mapping) -> list[Evidence]:
    if not populations:
        return []
    hits = sorted(local_name(c) for c, n in populations.items() if int(n) == int(group_size) and local_name(c) in known)
    if len(hits) != 1:
        return []
    return [Evidence(hits[0], "population", cfg["w_population"], f"group size {group_size} equals the confirmed population of {hits[0]}")]


# ---------------------------------------------------------------------------
# Compute
# ---------------------------------------------------------------------------


def _validate(descriptors: Any, cfg: Mapping) -> list:
    if not isinstance(descriptors, list):
        raise MappingInputError("MAPPING_INPUT_INVALID", "elements must be a list")
    if len(descriptors) > int(cfg["max_elements"]):
        raise MappingInputError("MAPPING_TOO_MANY_ELEMENTS", f"at most {int(cfg['max_elements'])} elements per session")
    seen = set()
    for d in descriptors:
        if not isinstance(d, Mapping) or not str(d.get("nativeId") or "").strip():
            raise MappingInputError("MAPPING_INPUT_INVALID", "every element needs a nativeId")
        nid = str(d["nativeId"])
        if nid in seen:
            raise MappingInputError("MAPPING_INPUT_INVALID", f"duplicate nativeId {nid}")
        seen.add(nid)
    return sorted(descriptors, key=lambda d: str(d["nativeId"]))


def _base_signature(feats: Mapping, extra_keys: Sequence[str]) -> dict:
    sig = {k: feats[k] for k in SELECTOR_FEATURES if k in feats}
    for k in sorted(set(extra_keys)):
        if k in feats:
            sig[k] = feats[k]
    return sig


def _rule_consistent(stats: Mapping, cls: str) -> bool:
    s = stats.get(cls)
    return bool(s and s["sat"] and not s["vio"])


def _blocking(stats: Mapping, role: str, others: Iterable[str], accepted: set) -> bool:
    s = stats.get(role)
    if not s:
        return False
    vio = [r for r, _ in s["vio"] if r not in accepted]
    return bool(vio) and any(_rule_consistent(stats, o) for o in others if o != role)


def _design_signals(stats: Mapping, roles: Iterable[str], iri_of: Mapping, accepted: set) -> list:
    out = []
    for role in sorted(set(roles)):
        for rule_id, detail in (stats.get(role) or {}).get("vio", []):
            out.append({"ruleId": rule_id, "classIri": iri_of.get(role, role), "detail": detail, "accepted": rule_id in accepted})
    return out


def compute(
    descriptors: list,
    classes: Sequence[ClassInfo],
    constraints: Sequence[Constraint],
    profiles: Sequence[Mapping] = (),
    disjoint: Iterable[tuple] = (),
    populations: Optional[Mapping] = None,
    platform_default: str = "grasshopper",
    config: Optional[Mapping] = None,
    decided: Optional[Mapping] = None,
    splits: Optional[Mapping] = None,
    rule_classes: Optional[Mapping] = None,
) -> dict:
    """Map descriptors to DG classes. Returns the deterministic session body.

    `decided` maps nativeId → list of class IRIs confirmed by a human in this
    session ([] = explicitly none); `splits` maps nativeId → extra signature
    features requested by a split answer.
    """
    cfg = dict(CONFIG)
    cfg.update(config or {})
    items = _validate(descriptors, cfg)
    decided = {str(k): list(v) for k, v in (decided or {}).items()}
    splits = {str(k): list(v) for k, v in (splits or {}).items()}
    classes = sorted(classes, key=lambda c: c.local)
    iri_of = {c.local: c.iri for c in classes}
    label_of = {c.local: c.label for c in classes}
    known = set(iri_of)
    disjoint_pairs = {frozenset((local_name(a), local_name(b))) for a, b in disjoint}
    rmap = rules_by_class(constraints, rule_classes)
    active_profiles = sorted(
        [p for p in profiles if p.get("state", "active") == "active"], key=lambda p: str(p.get("profileId"))
    )

    # 1. Element-level evidence and base groups.
    rows = []
    base_groups: dict[str, list] = {}
    for d in items:
        nid = str(d["nativeId"])
        feats = features(d, platform_default)
        evidence, matched = ev_profiles(feats, active_profiles, cfg)
        evidence += ev_name(feats, classes, cfg)
        rule_ev, stats = ev_rules(feats, constraints, cfg)
        evidence += rule_ev
        evidence += ev_ifc(feats, classes, cfg)
        sig = _base_signature(feats, splits.get(nid, ()))
        key = canonical_json({k: _norm(v) for k, v in sig.items()})
        row = {"nid": nid, "feats": feats, "evidence": evidence, "matched": matched, "stats": stats, "sig": sig, "key": key}
        rows.append(row)
        base_groups.setdefault(key, []).append(row)

    # 2. Group-level population evidence.
    for members in base_groups.values():
        pop = ev_population(len(members), populations, known, cfg)
        for row in members:
            row["evidence"] = row["evidence"] + pop

    # 3. Scores, candidates and states.
    for row in rows:
        score = {c: cfg["prior"] for c in known}
        for e in row["evidence"]:
            if e.class_local in score:
                score[e.class_local] += e.weight
        conf = {c: _r(_logistic(s)) for c, s in score.items()}
        cands = sorted((c for c in known if conf[c] >= cfg["tau_candidate"]), key=lambda c: (-conf[c], label_of[c]))
        row["score"], row["conf"], row["cands"] = score, conf, cands
        stats = row["stats"]
        nid = row["nid"]
        accepted = set()
        for p, _ in row["matched"]:
            accepted.update(p.get("acceptsViolations") or ())
        row["accepted"] = accepted
        row["reason"] = None
        if nid in decided:
            roles = [local_name(r) for r in decided[nid] if local_name(r) in known]
            row["state"] = "confirmed" if roles else "unmapped"
            row["roles"] = [(r, "confirmed", "human", 1.0, None) for r in roles]
            row["decidedNone"] = not roles
            continue
        auto = [(p, c) for p, c in row["matched"] if c >= cfg["profile_auto"]]
        if auto:
            roles: list[str] = []
            excluded: set = set()
            for p, _ in auto:
                for r in p.get("roles") or ():
                    if local_name(r) in known and local_name(r) not in roles:
                        roles.append(local_name(r))
                excluded.update(local_name(r) for r in p.get("excludedRoles") or ())
            roles = sorted(r for r in roles if r not in excluded)
            others = [c for c in cands if c not in roles]
            if roles and not any(_blocking(stats, r, others, accepted) for r in roles):
                best = {}
                for p, c in auto:
                    for r in p.get("roles") or ():
                        lr = local_name(r)
                        if c >= best.get(lr, (0.0, None))[0]:
                            best[lr] = (c, p["profileId"])
                row["state"] = "auto"
                row["roles"] = [(r, "auto", "profile", best[r][0], best[r][1]) for r in roles]
                continue
            if not roles and excluded:
                row["state"] = "unmapped"
                row["roles"] = []
                continue
            row["state"] = "ambiguous"
            row["reason"] = "mapping-or-design"
            row["roles"] = []
            row["blockRoles"] = roles
            continue
        if not cands:
            row["state"], row["roles"] = "unmapped", []
            continue
        top = cands[0]
        second = cands[1] if len(cands) > 1 else None
        margin = conf[top] - conf[second] if second else 1.0
        # Mapping error or design error: one of the two leading classes violates
        # its rules while the other is rule-consistent (in either order).
        pair_conflict = bool(second) and margin < cfg["margin_delta"] and any(
            _blocking(stats, a, [b], accepted) for a, b in ((top, second), (second, top))
        )
        if _blocking(stats, top, cands[1:], accepted) or pair_conflict:
            row["state"], row["reason"] = "ambiguous", "mapping-or-design"
        elif second and margin < cfg["margin_delta"]:
            row["state"], row["reason"] = "ambiguous", "disambiguate"
        elif conf[top] >= cfg["tau_clear"]:
            row["state"] = "suggested"
        else:
            row["state"], row["reason"] = "ambiguous", "assign"
        row["roles"] = [(top, "suggested", "evidence", conf[top], None)] if row["state"] == "suggested" else []

    # 4. Final groups.
    groups: dict[str, dict] = {}
    for row in rows:
        roles = sorted(r[0] for r in row["roles"])
        label_set = roles if row["state"] in ("confirmed", "auto") else row["cands"][:2]
        gsig = {
            "base": row["key"],
            "state": row["state"],
            "labels": label_set,
            "reason": row.get("reason"),
            "none": bool(row.get("decidedNone")),
        }
        gid = "G-" + _sha(canonical_json(gsig), 8)
        row["groupId"] = gid
        g = groups.setdefault(gid, {"groupId": gid, "rows": [], "state": row["state"], "reason": row.get("reason"), "sig": row["sig"]})
        g["rows"].append(row)

    for g in groups.values():
        _finish_group(g, iri_of, label_of, rmap, constraints, cfg)

    ordered_groups = sorted(groups.values(), key=lambda g: (-g["priority"], g["groupId"]))

    # 5. Questions.
    questions = _build_questions(ordered_groups, iri_of, label_of, disjoint_pairs, cfg)
    qid_of = {}
    for q in questions:
        for gid in q["groupIds"]:
            qid_of[gid] = q["questionId"]

    # 6. Output.
    out_groups = []
    for g in ordered_groups:
        out_groups.append(
            {
                "groupId": g["groupId"],
                "size": len(g["rows"]),
                "signature": dict(sorted(g["sig"].items())),
                "representatives": sorted(r["nid"] for r in g["rows"])[: int(cfg["representatives"])],
                "status": g["state"],
                "candidates": g["candidates"],
                "ruleImpact": g["ruleImpact"],
                "priority": g["priority"],
                "questionId": qid_of.get(g["groupId"]),
            }
        )
    elements = []
    for row in rows:
        accepted = row["accepted"]
        role_locals = [r[0] for r in row["roles"]] or ([row["cands"][0]] if row["cands"] else [])
        elements.append(
            {
                "nativeId": row["nid"],
                "groupId": row["groupId"],
                "state": row["state"],
                "roles": [
                    {
                        "classIri": iri_of[r],
                        "label": label_of[r],
                        "state": st,
                        "source": src,
                        "confidence": _r(c),
                        **({"profileId": pid} if pid else {}),
                    }
                    for r, st, src, c, pid in row["roles"]
                ],
                "designSignals": _design_signals(row["stats"], role_locals, iri_of, accepted)
                if row["state"] in ("confirmed", "auto", "suggested")
                else [],
            }
        )
    counts = {s: 0 for s in STATES}
    for row in rows:
        counts[row["state"]] += 1
    summary = {"total": len(rows), **counts, "openQuestions": len(questions)}
    return {
        "engineVersion": ENGINE_VERSION,
        "platform": str(platform_default).lower(),
        "summary": summary,
        "questions": questions,
        "groups": out_groups,
        "elements": elements,
        "decided": {k: sorted(v) for k, v in sorted(decided.items())},
        "splits": {k: sorted(v) for k, v in sorted(splits.items())},
    }


def _finish_group(g: dict, iri_of: Mapping, label_of: Mapping, rmap: Mapping, constraints: Sequence[Constraint], cfg: Mapping) -> None:
    rows = g["rows"]
    n = len(rows)
    union: list[str] = []
    for row in rows:
        pool = [r[0] for r in row["roles"]] if row["state"] in ("confirmed", "auto") else row["cands"]
        for c in pool + row.get("blockRoles", []):
            if c not in union:
                union.append(c)
    cand_out = []
    for c in union:
        mean_conf = sum(row["conf"][c] for row in rows) / n
        mean_score = sum(row["score"][c] for row in rows) / n
        ev: dict[tuple, dict] = {}
        for row in rows:
            for e in row["evidence"]:
                if e.class_local != c:
                    continue
                k = (e.kind, e.detail)
                slot = ev.setdefault(k, {"kind": e.kind, "detail": e.detail, "weight": 0.0, "count": 0})
                slot["weight"] += e.weight
                slot["count"] += 1
        evidence = [
            {"kind": v["kind"], "weight": _r(v["weight"] / v["count"]), "detail": v["detail"], "count": v["count"]}
            for v in sorted(ev.values(), key=lambda v: (-abs(v["weight"]), v["kind"], v["detail"]))
        ]
        conflicts: dict[str, int] = {}
        for row in rows:
            for rule_id, _ in (row["stats"].get(c) or {}).get("vio", []):
                conflicts[rule_id] = conflicts.get(rule_id, 0) + 1
        cand_out.append(
            {
                "classIri": iri_of[c],
                "label": label_of[c],
                "score": _r(mean_score),
                "confidence": _r(mean_conf),
                "evidence": evidence,
                "conflicts": [{"ruleId": r, "count": k} for r, k in sorted(conflicts.items())],
            }
        )
    cand_out.sort(key=lambda x: (-x["confidence"], x["label"]))
    g["candidates"] = cand_out
    impact = []
    by_class = {}
    for c in constraints:
        by_class.setdefault(c.class_local, []).append(c)
    for cand in cand_out:
        c = local_name(cand["classIri"])
        rules = []
        for rule_id in rmap.get(c, []):
            sat = vio = nm = 0
            cons = [k for k in by_class.get(c, []) if k.rule_id == rule_id]
            for row in rows:
                if not cons:
                    nm += 1
                    continue
                s = row["stats"].get(c) or {"sat": [], "vio": []}
                if rule_id in s["sat"]:
                    sat += 1
                elif any(r == rule_id for r, _ in s["vio"]):
                    vio += 1
                else:
                    nm += 1
            rules.append({"ruleId": rule_id, "satisfied": sat, "violated": vio, "notMeasured": nm})
        impact.append({"classIri": cand["classIri"], "rules": rules})
    g["ruleImpact"] = impact
    rules_affected = len({r["ruleId"] for i in impact for r in i["rules"]})
    if g["state"] == "ambiguous":
        if len(cand_out) >= 2:
            uncertainty = 1.0 - (cand_out[0]["confidence"] - cand_out[1]["confidence"])
        elif cand_out:
            uncertainty = 1.0 - cand_out[0]["confidence"]
        else:
            uncertainty = 1.0
    elif g["state"] == "suggested" and cand_out:
        uncertainty = 1.0 - cand_out[0]["confidence"]
    else:
        uncertainty = 0.0
    g["priority"] = _r(uncertainty * math.log(1 + n) * (1 + rules_affected))


def _describe_group(g: Mapping, lang: str) -> str:
    sig = g["sig"]
    src = sig.get("source") or sig.get("family") or sig.get("type") or sig.get("category") or ("selection" if lang == "en" else "выборки")
    n = len(g["rows"])
    vc = sig.get("geometry.vertexCount")
    if lang == "en":
        text = f"{n} {_en_plural(n, 'element', 'elements')} from {src}"
        if vc is not None:
            text += f" ({_fmt(float(vc))} {_en_plural(int(vc), 'vertex', 'vertices')})"
    else:
        text = f"{n} {_ru_plural(n, ('элемент', 'элемента', 'элементов'))} из {src}"
        if vc is not None:
            text += f" ({_fmt(float(vc))} {_ru_plural(int(vc), ('вершина', 'вершины', 'вершин'))})"
    return text


def _impact_phrase(g: Mapping, class_iri: str, lang: str) -> str:
    for item in g["ruleImpact"]:
        if item["classIri"] != class_iri:
            continue
        parts = []
        for r in item["rules"]:
            if r["violated"]:
                parts.append(f"{r['ruleId']} {'violated' if lang == 'en' else 'нарушено'} ×{r['violated']}")
        for r in item["rules"]:
            if r["satisfied"]:
                parts.append(f"{r['ruleId']} {'passes' if lang == 'en' else 'выполняется'} ×{r['satisfied']}")
        if not parts:
            applies = [r["ruleId"] for r in item["rules"]]
            if applies:
                parts.append(("applies: " if lang == "en" else "применяются: ") + ", ".join(applies))
            else:
                parts.append("no rules" if lang == "en" else "нет правил")
        return ", ".join(parts)
    return "no rules" if lang == "en" else "нет правил"


def _consequences(g: Mapping, option_id: str, roles: Sequence[str]) -> dict:
    rules = []
    for iri in roles:
        for item in g["ruleImpact"]:
            if item["classIri"] != iri:
                continue
            for r in item["rules"]:
                if r["violated"]:
                    rules.append({"classIri": iri, "ruleId": r["ruleId"], "effect": "violated", "count": r["violated"], "groupId": g["groupId"]})
                if r["satisfied"]:
                    rules.append({"classIri": iri, "ruleId": r["ruleId"], "effect": "passes", "count": r["satisfied"], "groupId": g["groupId"]})
                if not r["violated"] and not r["satisfied"]:
                    rules.append({"classIri": iri, "ruleId": r["ruleId"], "effect": "applies", "count": r["notMeasured"], "groupId": g["groupId"]})
    return {"optionId": option_id, "rules": rules}


def _split_feature(g: Mapping) -> Optional[str]:
    rows = g["rows"]
    if len(rows) < 2:
        return None
    labels = [tuple(r["cands"][:1]) for r in rows]

    def entropy(seq):
        counts: dict = {}
        for x in seq:
            counts[x] = counts.get(x, 0) + 1
        total = len(seq)
        return -sum((k / total) * math.log2(k / total) for k in counts.values())

    base = entropy(labels)
    keys = sorted({k for r in rows for k in r["feats"] if k.split(".")[0] in ("source", "category", "family", "type", "geometry", "properties", "parameters")})
    best, best_gain = None, 0.0
    for k in keys:
        values = [_norm(r["feats"].get(k)) for r in rows]
        if len(set(map(str, values))) < 2:
            continue
        parts: dict = {}
        for v, lab in zip(values, labels):
            parts.setdefault(str(v), []).append(lab)
        rem = sum(len(p) / len(rows) * entropy(p) for p in parts.values())
        gain = base - rem
        if gain > best_gain + 1e-12:
            best, best_gain = k, gain
    return best


def _build_questions(groups: Sequence[dict], iri_of: Mapping, label_of: Mapping, disjoint: set, cfg: Mapping) -> list:
    questions = []
    suggested = [g for g in groups if g["state"] == "suggested"]
    if suggested:
        gids = sorted(g["groupId"] for g in suggested)
        n_el = sum(len(g["rows"]) for g in suggested)
        parts_en, parts_ru, cons = [], [], []
        for g in suggested:
            top = g["candidates"][0]
            parts_en.append(f"{len(g['rows'])} from {_src(g)} → {top['label']}")
            parts_ru.append(f"{len(g['rows'])} из {_src(g)} → {top['label']}")
            cons.append(_consequences(g, "accept-all", [top["classIri"]]))
        k = len(suggested)
        text = f"{k} {_en_plural(k, 'group', 'groups')} ({n_el} {_en_plural(n_el, 'element', 'elements')}) have one clear class: " + "; ".join(parts_en) + ". Accept all?"
        text_ru = (
            f"{k} {_ru_plural(k, ('группа', 'группы', 'групп'))} ({n_el} {_ru_plural(n_el, ('элемент', 'элемента', 'элементов'))}) "
            f"{'имеет' if k == 1 else 'имеют'} один очевидный класс: " + "; ".join(parts_ru) + ". Принять все?"
        )
        merged = {"optionId": "accept-all", "rules": [r for c in cons for r in c["rules"]]}
        questions.append(
            {
                "questionId": "Q-" + _sha("batch-assign|" + "|".join(gids), 8),
                "type": "batch-assign",
                "groupIds": gids,
                "text": text,
                "textRu": text_ru,
                "options": [
                    {"optionId": "accept-all", "label": "Accept all proposed classes", "roles": None},
                    {"optionId": "none", "label": "None of these", "roles": []},
                ],
                "consequences": [merged],
                "_priority": max(g["priority"] for g in suggested),
            }
        )
    for g in groups:
        if g["state"] != "ambiguous":
            continue
        reason = g.get("reason") or "disambiguate"
        cands = g["candidates"]
        options, cons = [], []
        if reason == "mapping-or-design" and cands:
            conflicting = next((c for c in cands if c["conflicts"]), cands[0])
            alt = next(
                (c for c in cands if c is not conflicting and not c["conflicts"] and any(e["kind"] == "rule" and e["weight"] > 0 for e in c["evidence"])),
                None,
            )
            if alt:
                options.append({"optionId": f"class:{alt['classIri']}", "label": alt["label"], "roles": [alt["classIri"]]})
            options.append(
                {
                    "optionId": f"design-error:{conflicting['classIri']}",
                    "label": f"{conflicting['label']} — rule violations are design errors",
                    "roles": [conflicting["classIri"]],
                }
            )
            if alt and frozenset((local_name(alt["classIri"]), local_name(conflicting["classIri"]))) not in disjoint:
                options.append({"optionId": "both", "label": "Both roles", "roles": sorted([alt["classIri"], conflicting["classIri"]])})
            text = f"{_describe_group(g, 'en')}. As {conflicting['label']}: {_impact_phrase(g, conflicting['classIri'], 'en')}."
            text_ru = f"{_describe_group(g, 'ru')}. Как {conflicting['label']}: {_impact_phrase(g, conflicting['classIri'], 'ru')}."
            if alt:
                text += f" As {alt['label']}: {_impact_phrase(g, alt['classIri'], 'en')}."
                text_ru += f" Как {alt['label']}: {_impact_phrase(g, alt['classIri'], 'ru')}."
            text += " Mapping error or design error?"
            text_ru += " Это ошибка меппинга или ошибка проекта?"
        elif reason == "assign" and cands:
            top = cands[0]
            options.append({"optionId": f"class:{top['classIri']}", "label": top["label"], "roles": [top["classIri"]]})
            text = f"{_describe_group(g, 'en')} look like {top['label']} (confidence {top['confidence']:.2f}): {_impact_phrase(g, top['classIri'], 'en')}. Confirm?"
            text_ru = f"{_describe_group(g, 'ru')} похожи на {top['label']} (уверенность {top['confidence']:.2f}): {_impact_phrase(g, top['classIri'], 'ru')}. Подтвердить?"
        else:
            reason = "disambiguate"
            for c in cands[:4]:
                options.append({"optionId": f"class:{c['classIri']}", "label": c["label"], "roles": [c["classIri"]]})
            if len(cands) >= 2 and frozenset((local_name(cands[0]["classIri"]), local_name(cands[1]["classIri"]))) not in disjoint:
                options.append({"optionId": "both", "label": "Both roles", "roles": sorted([cands[0]["classIri"], cands[1]["classIri"]])})
            listing = ", ".join(f"{c['label']} ({c['confidence']:.2f})" for c in cands[:4])
            text = f"{_describe_group(g, 'en')}. Candidates: {listing}."
            text_ru = f"{_describe_group(g, 'ru')}. Кандидаты: {listing}."
            for c in cands[:2]:
                text += f" As {c['label']}: {_impact_phrase(g, c['classIri'], 'en')}."
                text_ru += f" Как {c['label']}: {_impact_phrase(g, c['classIri'], 'ru')}."
            text += " Which roles apply?"
            text_ru += " Какие роли применимы?"
        feature = _split_feature(g)
        if feature and reason != "mapping-or-design":
            options.append({"optionId": f"split:{feature}", "label": f"Split by {feature}", "roles": None})
        options.append({"optionId": "none", "label": "None of these", "roles": []})
        for opt in options:
            if opt["roles"]:
                cons.append(_consequences(g, opt["optionId"], opt["roles"]))
        questions.append(
            {
                "questionId": "Q-" + _sha(reason + "|" + g["groupId"], 8),
                "type": reason,
                "groupIds": [g["groupId"]],
                "text": text,
                "textRu": text_ru,
                "options": options,
                "consequences": cons,
                "_priority": g["priority"],
            }
        )
    questions.sort(key=lambda q: (-q["_priority"], q["questionId"]))
    for q in questions:
        q.pop("_priority")
    return questions


def _src(g: Mapping) -> str:
    sig = g["sig"]
    return str(sig.get("source") or sig.get("family") or sig.get("type") or sig.get("category") or "selection")


# ---------------------------------------------------------------------------
# Decisions and profiles
# ---------------------------------------------------------------------------


def _member_rows(result: Mapping, descriptors: Sequence[Mapping], platform_default: str) -> dict:
    by_id = {str(d["nativeId"]): d for d in descriptors}
    rows = {}
    for el in result["elements"]:
        d = by_id.get(el["nativeId"])
        if d is None:
            continue
        rows[el["nativeId"]] = {"el": el, "feats": features(d, platform_default)}
    return rows


def _label_set(el: Mapping, groups: Mapping) -> tuple:
    if el["state"] in ("confirmed", "auto"):
        return tuple(sorted(local_name(r["classIri"]) for r in el["roles"]))
    g = groups.get(el["groupId"])
    if not g:
        return ()
    return tuple(local_name(c["classIri"]) for c in g["candidates"][:2])


def profile_id(platform: str, selector: Mapping, roles: Sequence[str], excluded: Sequence[str] = ()) -> str:
    """Deterministic profile id over (platform, normalised selector, roles, excluded roles)."""
    role_set = tuple(sorted(local_name(r) for r in roles))
    excluded_t = tuple(sorted(local_name(r) for r in excluded))
    norm_sel = {k: _norm(v) for k, v in sorted(selector.items())}
    return "P-" + _sha(canonical_json([str(platform).lower(), norm_sel, role_set, excluded_t]), 12)


def induce_profile(
    member_feats: Sequence[Mapping],
    other_feats: Sequence[tuple],
    roles: Sequence[str],
    platform: str,
    excluded: Sequence[str] = (),
    project: Optional[str] = None,
) -> dict:
    """Minimal discriminating selector for a decided group.

    `other_feats` = [(feats, label_set)] of elements outside the group.
    """
    role_set = tuple(sorted(local_name(r) for r in roles))
    keys = [k for k in SELECTOR_FEATURES if all(k in f for f in member_feats)]
    selector = {}
    for k in keys:
        values = {canonical_json(_norm(f[k])) for f in member_feats}
        if len(values) == 1:
            selector[k] = member_feats[0][k]

    def conflicts(sel: Mapping) -> int:
        n = 0
        for f, labels in other_feats:
            if tuple(sorted(labels)) == role_set:
                continue
            if all(k in f and _norm(f[k]) == _norm(v) for k, v in sel.items()):
                n += 1
        return n

    base_conflicts = conflicts(selector)
    for k in DROP_ORDER:
        if k not in selector:
            continue
        trial = {kk: vv for kk, vv in selector.items() if kk != k}
        if any(kk != "platform" for kk in trial) and conflicts(trial) <= base_conflicts:
            selector = trial
    rest = [k for k in selector if k != "platform"]
    profile_platform = str(platform).lower()
    if rest and all(k.startswith(("geometry.", "properties.")) for k in rest):
        selector.pop("platform", None)
        profile_platform = "*"
    else:
        selector.pop("platform", None)
    selector = dict(sorted(selector.items()))
    return {
        "profileId": profile_id(profile_platform, selector, roles, excluded),
        "project": project,
        "platform": profile_platform,
        "selector": selector,
        "overlaps": base_conflicts,
    }


def decide(
    result: Mapping,
    descriptors: Sequence[Mapping],
    question_id: str,
    option_id: str,
    actor: str,
    at: str,
    classes: Sequence[ClassInfo],
    group_ids: Optional[Sequence[str]] = None,
    roles: Optional[Sequence[str]] = None,
    profiles: Sequence[Mapping] = (),
    project: Optional[str] = None,
    platform_default: str = "grasshopper",
    config: Optional[Mapping] = None,
) -> dict:
    """Apply one answer. Returns {decisions, profiles, decided, splits}.

    `decided` (nativeId → class IRIs) and `splits` are the additions the caller
    merges into the session before recomputing; `profiles` are new or updated
    profiles (confirmation/rejection counters already applied).
    """
    cfg = dict(CONFIG)
    cfg.update(config or {})
    question = next((q for q in result.get("questions", []) if q["questionId"] == question_id), None)
    if question is None:
        raise MappingInputError("MAPPING_QUESTION_NOT_FOUND", f"question {question_id} not found", 404)
    option = next((o for o in question["options"] if o["optionId"] == option_id), None)
    iri_of = {c.local: c.iri for c in classes}
    if option is None and not (option_id == "custom" and roles):
        raise MappingInputError("MAPPING_OPTION_INVALID", f"option {option_id} is not offered by {question_id}")
    groups = {g["groupId"]: g for g in result.get("groups", [])}
    target_ids = list(question["groupIds"])
    if group_ids:
        unknown = [gid for gid in group_ids if gid not in target_ids]
        if unknown:
            raise MappingInputError("MAPPING_OPTION_INVALID", f"groups {unknown} are not part of {question_id}")
        target_ids = [gid for gid in target_ids if gid in set(group_ids)]
    rows = _member_rows(result, descriptors, platform_default)
    by_group: dict[str, list] = {}
    for nid, r in rows.items():
        by_group.setdefault(r["el"]["groupId"], []).append(nid)

    if option_id.startswith("split:"):
        feature = option_id.split(":", 1)[1]
        splits = {nid: [feature] for gid in target_ids for nid in by_group.get(gid, [])}
        return {"decisions": [], "profiles": [], "decided": {}, "splits": splits}

    existing = {p["profileId"]: dict(p) for p in profiles}
    out_decisions, out_profiles, decided = [], {}, {}
    for gid in sorted(target_ids):
        g = groups.get(gid)
        members = sorted(by_group.get(gid, []))
        if g is None or not members:
            continue
        excluded: list[str] = []
        accepts: list[str] = []
        if option_id == "accept-all":
            chosen = [g["candidates"][0]["classIri"]] if g["candidates"] else []
        elif option_id == "custom":
            chosen = list(roles or [])
        elif option_id == "none":
            chosen = []
            excluded = [c["classIri"] for c in g["candidates"]]
        else:
            chosen = list(option.get("roles") or [])
            if option_id.startswith("design-error:"):
                cls = local_name(option_id.split(":", 1)[1])
                for c in g["candidates"]:
                    if local_name(c["classIri"]) == cls:
                        accepts = [x["ruleId"] for x in c["conflicts"]]
        unknown = [r for r in chosen if local_name(r) not in iri_of]
        if unknown:
            raise MappingInputError("MAPPING_INPUT_INVALID", f"unknown classes {unknown}")
        chosen = sorted(iri_of[local_name(r)] for r in chosen)
        member_feats = [rows[nid]["feats"] for nid in members]
        others = [(rows[nid]["feats"], _label_set(rows[nid]["el"], groups)) for nid in sorted(rows) if rows[nid]["el"]["groupId"] != gid]
        platform = member_feats[0].get("platform", platform_default)
        induced = induce_profile(member_feats, others, chosen, platform, excluded, project)
        decision_id = "D-" + _sha(f"{question_id}|{gid}|{option_id}|{at}", 12)
        pid = induced["profileId"]
        prof = existing.get(pid) or out_profiles.get(pid)
        if prof:
            prof = dict(prof)
            prof["confirmations"] = int(prof.get("confirmations", 0)) + 1
            prof["decisionIds"] = sorted(set(prof.get("decisionIds", [])) | {decision_id})
            prof["support"] = max(int(prof.get("support", 0)), len(members))
            prof["updatedAt"] = at
        else:
            prof = {
                "profileId": pid,
                "project": project,
                "platform": induced["platform"],
                "selector": induced["selector"],
                "roles": chosen,
                "excludedRoles": sorted(excluded),
                "acceptsViolations": sorted(accepts),
                "source": "learned",
                "confirmations": 1,
                "rejections": 0,
                "support": len(members),
                "createdBy": actor,
                "createdAt": at,
                "updatedAt": at,
                "decisionIds": [decision_id],
                "engineVersion": ENGINE_VERSION,
                "state": "active",
            }
        prof["confidence"] = profile_confidence(prof["confirmations"], prof.get("rejections", 0), cfg)
        out_profiles[pid] = prof
        # Profiles that matched these members but proposed other roles lose confidence.
        for other in profiles:
            if other["profileId"] == pid:
                continue
            if any(profile_matches(other, rows[nid]["feats"]) for nid in members):
                if sorted(other.get("roles") or []) != chosen:
                    rej = dict(out_profiles.get(other["profileId"]) or other)
                    rej["rejections"] = int(rej.get("rejections", 0)) + 1
                    rej["updatedAt"] = at
                    rej["confidence"] = profile_confidence(int(rej.get("confirmations", 0)), rej["rejections"], cfg)
                    out_profiles[rej["profileId"]] = rej
        consequences = [c for c in question.get("consequences", []) if c["optionId"] == option_id]
        evidence = [{"classIri": c["classIri"], "evidence": c["evidence"]} for c in g["candidates"]]
        out_decisions.append(
            {
                "decisionId": decision_id,
                "project": project,
                "questionId": question_id,
                "groupId": gid,
                "optionId": option_id,
                "roles": chosen,
                "memberCount": len(members),
                "memberIds": members,
                "questionText": question["text"],
                "evidenceShown": evidence,
                "consequencesShown": consequences,
                "decidedBy": actor,
                "decidedAt": at,
                "profileId": pid,
            }
        )
        for nid in members:
            decided[nid] = chosen
    return {
        "decisions": out_decisions,
        "profiles": [out_profiles[k] for k in sorted(out_profiles)],
        "decided": decided,
        "splits": {},
    }


def merge_profiles(current: Sequence[Mapping], updates: Sequence[Mapping]) -> list:
    merged = {p["profileId"]: dict(p) for p in current}
    for p in updates:
        merged[p["profileId"]] = dict(p)
    return [merged[k] for k in sorted(merged)]


# ---------------------------------------------------------------------------
# Apply and evaluation
# ---------------------------------------------------------------------------


def partition(result: Mapping) -> dict:
    by_class: dict[str, list] = {}
    applied, skipped, elements = 0, [], []
    for el in result["elements"]:
        if el["state"] in ("confirmed", "auto") and el["roles"]:
            roles = sorted(r["classIri"] for r in el["roles"])
            elements.append({"nativeId": el["nativeId"], "roles": roles})
            for r in roles:
                by_class.setdefault(r, []).append(el["nativeId"])
            applied += 1
        else:
            skipped.append({"nativeId": el["nativeId"], "reason": el["state"]})
    return {
        "applied": applied,
        "byClass": {k: sorted(v) for k, v in sorted(by_class.items())},
        "elements": elements,
        "skipped": skipped,
    }


def populations_of(result: Mapping) -> dict:
    counts: dict[str, int] = {}
    for el in result.get("elements", []):
        if el["state"] in ("confirmed", "auto"):
            for r in el["roles"]:
                key = local_name(r["classIri"])
                counts[key] = counts.get(key, 0) + 1
    return dict(sorted(counts.items()))


def evaluate_against_gold(elements: Sequence[Mapping], gold: Mapping) -> dict:
    predicted = {}
    for el in elements:
        roles = set()
        if el["state"] in ("confirmed", "auto"):
            roles = {local_name(r["classIri"]) for r in el["roles"]}
        predicted[el["nativeId"]] = roles
    classes = sorted({c for v in gold.values() for c in v} | {c for v in predicted.values() for c in v})
    per = {}
    tp_all = fp_all = fn_all = 0
    for c in classes:
        tp = sum(1 for nid, g in gold.items() if c in g and c in predicted.get(nid, set()))
        fp = sum(1 for nid, p in predicted.items() if c in p and c not in gold.get(nid, set()))
        fn = sum(1 for nid, g in gold.items() if c in g and c not in predicted.get(nid, set()))
        tp_all, fp_all, fn_all = tp_all + tp, fp_all + fp, fn_all + fn
        per[c] = {
            "precision": _r(tp / (tp + fp)) if tp + fp else 0.0,
            "recall": _r(tp / (tp + fn)) if tp + fn else 0.0,
            "support": tp + fn,
        }
    overall = {
        "precision": _r(tp_all / (tp_all + fp_all)) if tp_all + fp_all else 0.0,
        "recall": _r(tp_all / (tp_all + fn_all)) if tp_all + fn_all else 0.0,
        "support": tp_all + fn_all,
    }
    return {"perClass": per, "overall": overall}
