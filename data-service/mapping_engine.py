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
    # Calculation outputs (measures) → DG datatype properties; sliders → DG parameters.
    "prior_param": -1.0,
    "w_param_own": 2.0,
    "w_param_context": 1.0,
    "w_param_cap": 4.0,
    "w_measure_acronym": 2.0,
    "w_measure_agree": 4.0,
    "w_measure_agree_const": 1.5,
    # A stream measured by an output whose property only some classes' rules use.
    "w_measure_class": 2.5,
    "w_measure_class_cap": 3.0,
    # An LLM proposal (D-37) is one vote among the deterministic evidence.
    "w_llm": 2.5,
    "max_parameters": 500,
    "max_measures": 500,
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
# Canvas text around an element (group names, scribbles, component nicknames,
# the class an OBJECT STATE already names). Word evidence only, no acronyms.
CONTEXT_FIELD = "context.names"

# Small bilingual vocabulary: Russian stems and English variants → English
# concept words, so canvas text such as «Ширина соты» or "Panels" meets
# class and property labels (hasWidthM, GlassPanel). Prefix match on stems.
LEXICON_RU = (
    ("ширин", ("width",)),
    ("высот", ("height",)),
    ("длин", ("length",)),
    ("глубин", ("depth",)),
    ("толщин", ("thickness",)),
    ("наклон", ("tilt", "slope", "inclination")),
    ("угол", ("angle",)),
    ("угл", ("angle",)),
    ("площад", ("area",)),
    ("колво", ("count",)),
    ("количеств", ("count",)),
    ("вершин", ("vertex",)),
    ("ребр", ("edge",)),
    ("ребер", ("edge",)),
    ("сторон", ("side",)),
    ("уров", ("level",)),
    ("этаж", ("floor", "storey", "level")),
    ("отступ", ("offset",)),
    ("оффсет", ("offset",)),
    ("смещ", ("offset",)),
    ("выступ", ("projection", "protrusion")),
    ("шаг", ("spacing", "step", "pitch")),
    ("соотнош", ("ratio",)),
    ("пропорц", ("ratio", "proportion")),
    ("отношен", ("ratio",)),
    ("планар", ("planarity",)),
    ("плоск", ("planarity", "flat")),
    ("отклон", ("deviation",)),
    ("радиус", ("radius",)),
    ("диаметр", ("diameter",)),
    ("панел", ("panel",)),
    ("стекл", ("glass",)),
    ("остекл", ("glazing", "glass")),
    ("сот", ("hexagonal", "cell", "honeycomb")),
    ("шестиуг", ("hexagonal",)),
    ("пятиуг", ("pentagon", "pentagonal")),
    ("треуг", ("triangular", "triangle")),
    ("модул", ("module", "unit")),
    ("фасад", ("facade",)),
    ("каркас", ("frame",)),
    ("стойк", ("mullion", "post")),
    ("ригел", ("transom",)),
    ("нижн", ("bottom",)),
    ("верх", ("top",)),
    ("разрыв", ("gap",)),
    ("зазор", ("gap",)),
    ("замкн", ("closed",)),
    ("контур", ("outline",)),
)
EN_ALIASES = {
    "hex": ("hexagonal",),
    "hexagon": ("hexagonal",),
    "pent": ("pentagon",),
    "tri": ("triangular",),
    "triangle": ("triangular",),
    "glazing": ("glass",),
    "proportion": ("ratio",),
    "storey": ("level",),
}
# Property label words that carry no meaning of their own.
PROPERTY_STOP = {"has", "is", "of", "the", "value", "values"}
UNIT_TOKENS = {"m", "mm", "cm", "m2", "m3", "deg", "rad", "pct"}
# Generic words count half: "КолВо ребер" must not become hasVertexCount by "count" alone,
# nor "1 оффсет" (a Grasshopper offset distance) hasLevelOffsetM by "offset" alone.
GENERIC_WORDS = {"count", "number", "size", "value", "offset"}


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


@dataclass(frozen=True)
class PropertyInfo:
    """A DG datatype property a GH parameter can be mapped to; `classes` = classes whose rules use it."""

    iri: str
    label: str
    classes: tuple = ()
    synonyms: tuple = ()

    @property
    def local(self) -> str:
        return local_name(self.iri)


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


def _singular(t: str) -> str:
    if len(t) > 3 and t.endswith("ies"):
        return t[:-3] + "y"
    if len(t) > 3 and t.endswith("s") and not t.endswith("ss"):
        return t[:-1]
    return t


def concepts(tokens: Iterable[str]) -> set:
    """Token set expanded with singular forms, English aliases and Russian stems."""
    out: set = set()
    for raw in tokens:
        t = str(raw or "").lower()
        if not t:
            continue
        s = _singular(t)
        out.update((t, s))
        out.update(EN_ALIASES.get(s, ()))
        if len(t) >= 3 and re.search("[а-яё]", t):
            for stem, words in LEXICON_RU:
                if t.startswith(stem):
                    out.update(words)
    return out


def _word_hit(token: str, words: set) -> Optional[str]:
    if token in words:
        return token
    return next((w for w in sorted(concepts([token])) if len(w) >= 3 and w in words), None)


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
    names = descriptor.get("names")
    if isinstance(names, (list, tuple)):
        texts = [str(n).strip() for n in names if isinstance(n, (str, int, float)) and not isinstance(n, bool) and str(n).strip()]
        if texts:
            f[CONTEXT_FIELD] = " ; ".join(texts[:20])
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
    ctx = set(split_tokens(feats.get(CONTEXT_FIELD, ""))) - toks
    # A one-letter token is an abbreviation only when it is the whole name ("F"), not a
    # letter inside one ("Panels C" is not Corridor).
    whole = {split_tokens(feats[k])[0] for k in NAME_FIELDS if k in feats and len(split_tokens(feats[k])) == 1}
    if not toks and not ctx:
        return []
    out = []
    for c in classes:
        acr = class_acronym(c.label)
        words = set(class_tokens(c.label))
        for syn in c.synonyms:
            words.update(split_tokens(syn))
        # Each distinct class word counts once: "Panels" and "panel" are one hit, and a full
        # match (bottom + triangular + panel) outweighs a shared word (panel).
        total, parts, hits = 0.0, [], set()
        for t in sorted(toks):
            abbreviation_ok = len(t) >= 2 or t in whole
            if acr and t == acr and abbreviation_ok:
                total += cfg["w_name_acronym"]
                parts.append(f"'{t}' is the acronym of {c.label}")
            elif acr and abbreviation_ok and len(t) < len(acr) and t[0] == acr[0] and _is_subsequence(t, acr):
                total += cfg["w_name_subsequence"]
                parts.append(f"'{t}' abbreviates {c.label}")
            hit = _word_hit(t, words) if len(t) >= 3 else None
            if hit and hit not in hits:
                hits.add(hit)
                total += cfg["w_name_token"]
                parts.append(f"word '{t}' matches {c.label}" + (f" ({hit})" if hit != t else ""))
        for t in sorted(ctx):
            hit = _word_hit(t, words) if len(t) >= 3 else None
            if hit and hit not in hits:
                hits.add(hit)
                total += cfg["w_name_token"]
                parts.append(f"canvas text '{t}' matches {c.label}" + (f" ({hit})" if hit != t else ""))
        if total:
            out.append(Evidence(c.local, "name", min(total, cfg["w_name_cap"]), "; ".join(parts)))
    return out


def _is_equality(c: Constraint) -> bool:
    return c.op in ("==", "!=")


def rule_groups(constraints: Iterable[Constraint]) -> dict:
    """Constraints of one rule and class, evaluated together.

    A SWRL body is a conjunction: a violation-pattern rule fires only when
    every body comparison holds. Each Constraint stores the negation of one
    comparison, so the rule is satisfied when ANY of its constraints holds and
    violated only when all of them fail (e.g. R9 `greaterThanOrEqual(?n, 0) ^
    greaterThan(?n, 0)` is violated iff n > 0).
    """
    groups: dict[tuple, list] = {}
    for c in constraints:
        groups.setdefault((c.rule_id, c.class_local), []).append(c)
    return groups


def ev_rules(feats: Mapping, constraints: Sequence[Constraint], cfg: Mapping) -> tuple:
    """Returns (evidence, stats) with stats[class] = {"sat": [...], "vio": [(rule, detail)]}."""
    stats: dict[str, dict] = {}
    weights: dict[str, dict] = {}
    for (rule_id, cls), group in sorted(rule_groups(constraints).items()):
        values = [(c, property_value(feats, c.prop_local)) for c in group]
        if any(v is None for _, v in values):
            continue
        s = stats.setdefault(cls, {"sat": [], "vio": [], "eq_sat": 0})
        w = weights.setdefault(cls, {"sat": 0.0, "vio": 0.0})
        equality = all(_is_equality(c) for c in group)
        if any(check_constraint(c, v) for c, v in values):
            s["sat"].append(rule_id)
            if equality:
                s["eq_sat"] += 1
            w["sat"] += cfg["w_rule_eq_satisfied"] if equality else cfg["w_rule_range_satisfied"]
        else:
            measured = sorted({f"{c.prop_local} = {_fmt(v)}" for c, v in values})
            required = " or ".join(f"{c.op} {_fmt(c.value)}" for c in group)
            s["vio"].append((rule_id, ", ".join(measured) + ", required " + required))
            w["vio"] += cfg["w_rule_eq_violated"] if equality else cfg["w_rule_range_violated"]
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


def _population_sizes(value: Any) -> set:
    """Group sizes of one class: `[n, …]` (per applied group) or a plain `n` (older sessions)."""
    values = value if isinstance(value, (list, tuple)) else [value]
    sizes = set()
    for v in values:
        if isinstance(v, int) and not isinstance(v, bool):
            sizes.add(v)
    return sizes


def ev_population(group_size: int, populations: Optional[Mapping], known: set, cfg: Mapping) -> list[Evidence]:
    """Population evidence only when exactly one class has a confirmed group of this size (D-49)."""
    if not populations:
        return []
    hits = sorted(
        local_name(c)
        for c, sizes in populations.items()
        if local_name(c) in known and int(group_size) in _population_sizes(sizes)
    )
    if len(hits) != 1:
        return []
    return [Evidence(hits[0], "population", cfg["w_population"], f"group size {group_size} equals a confirmed group of {hits[0]}")]


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
    parameters: Optional[list] = None,
    properties: Sequence[PropertyInfo] = (),
    decided_parameters: Optional[Mapping] = None,
    measures: Optional[list] = None,
    decided_measures: Optional[Mapping] = None,
    llm: Optional[Mapping] = None,
) -> dict:
    """Map descriptors to DG classes. Returns the deterministic session body.

    `decided` maps nativeId → list of class IRIs confirmed by a human in this
    session ([] = explicitly none); `splits` maps nativeId → extra signature
    features requested by a split answer. `parameters` (GH sliders) become DG
    parameters, `measures` (outputs of calculation components) are mapped to
    `properties`; `decided_parameters` / `decided_measures` hold the answers.
    `llm` is a recorded LLM proposal (D-37): {objects: {stream: {classIri,
    confidence, reason}}, measures: {...}, parameters: {...}}; it is input
    data, so the result stays deterministic for the same proposal.
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

    # Calculation outputs first: the property an output carries is evidence for its stream's class.
    decided_parameters = {str(k): sorted(v) for k, v in (decided_parameters or {}).items()}
    decided_measures = {str(k): sorted(v) for k, v in (decided_measures or {}).items()}
    measure_rows: list = map_measures(measures, properties, active_profiles, decided_measures, llm, platform_default, cfg) if measures else []
    measure_ev = measure_class_evidence(measure_rows, known, cfg)

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
        stream = str(d["stream"]) if d.get("stream") else None
        evidence += measure_ev.get(stream, []) if stream else []
        proposal = _llm_entry(llm, "objects", stream) if stream else None
        if proposal and local_name(proposal.get("classIri")) in known:
            evidence.append(
                Evidence(
                    local_name(proposal["classIri"]),
                    "llm",
                    cfg["w_llm"] * _llm_conf(proposal),
                    "LLM: " + (str(proposal.get("reason") or "proposed")[:200]),
                )
            )
        sig = _base_signature(feats, splits.get(nid, ()))
        key = canonical_json({k: _norm(v) for k, v in sig.items()})
        row = {"nid": nid, "feats": feats, "evidence": evidence, "matched": matched, "stats": stats, "sig": sig, "key": key, "stream": stream}
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
        if second and margin < cfg["margin_delta"]:
            # Signature tie-break: within the margin, the one class whose equality rule
            # (its signature, e.g. hasVertexCount == 3) holds wins over classes supported
            # only by ranges and a single shared word. A close class that violates rules or
            # is named explicitly (two words, e.g. the class an OBJECT STATE names) keeps the
            # question.
            name_w: dict = {}
            for e in row["evidence"]:
                if e.kind == "name":
                    name_w[e.class_local] = name_w.get(e.class_local, 0.0) + e.weight
            close = [c for c in cands if conf[top] - conf[c] < cfg["margin_delta"]]
            signed = [c for c in close if (stats.get(c) or {}).get("eq_sat") and not (stats.get(c) or {}).get("vio")]
            weak = all(
                not (stats.get(c) or {}).get("vio") and name_w.get(c, 0.0) <= cfg["w_name_token"]
                for c in close
                if c not in signed
            )
            if len(signed) == 1 and weak:
                top = signed[0]
                cands = [top] + [c for c in cands if c != top]
                row["cands"] = cands
                second, margin = None, 1.0
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

    # 5. Questions (element groups, then calculation outputs, then sliders).
    questions = _build_questions(ordered_groups, iri_of, label_of, disjoint_pairs, cfg)
    param_rows: list = []
    if measures:
        questions = questions + _measure_questions(measure_rows)
    if parameters:
        param_rows = map_parameters(parameters, active_profiles, decided_parameters, llm, platform_default, cfg)
        questions = questions + _parameter_questions(param_rows)
    qid_of = {}
    for q in questions:
        for gid in q["groupIds"]:
            qid_of[gid] = q["questionId"]
    _decorate_questions(questions, ordered_groups, measure_rows if measures else [], param_rows if parameters else [])

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
                **({"stream": row["stream"]} if row["stream"] else {}),
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
    body = {
        "engineVersion": ENGINE_VERSION,
        "platform": str(platform_default).lower(),
        "summary": summary,
        "questions": questions,
        "groups": out_groups,
        "elements": elements,
        "decided": {k: sorted(v) for k, v in sorted(decided.items())},
        "splits": {k: sorted(v) for k, v in sorted(splits.items())},
    }
    for key, kind_rows, decided_kind, given in (
        ("parameters", param_rows, decided_parameters, parameters),
        ("measures", measure_rows, decided_measures, measures),
    ):
        if given:
            kcounts = {s: 0 for s in STATES}
            for r in kind_rows:
                kcounts[r["state"]] += 1
            summary[key] = {"total": len(kind_rows), **kcounts}
            body[key] = kind_rows
            body["decided" + key.capitalize()] = dict(sorted(decided_kind.items()))
    return body


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
    # A suggested group leads with the class its elements are suggested as (the signature
    # tie-break can pick a class that is not the most confident one); questions use it.
    if g["state"] == "suggested" and rows[0]["roles"]:
        chosen = iri_of[rows[0]["roles"][0][0]]
        cand_out.sort(key=lambda x: 0 if x["classIri"] == chosen else 1)
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


# ---------------------------------------------------------------------------
# Proposal cards (plan 1303-10): a short title and one row per proposed canvas component
# ---------------------------------------------------------------------------

_GH_GUID = re.compile(r"^[0-9a-f]{32}$")


def _guid_or_none(value: Any) -> Optional[str]:
    text = str(value or "").lower()
    return text if _GH_GUID.match(text) else None


def _ref(iri: Any, label: Any) -> dict:
    return {"iri": str(iri), "label": str(label or local_name(iri))}


def _group_item(g: Mapping) -> dict:
    streams = [r.get("stream") for r in g["rows"] if r.get("stream")]
    stream = max(sorted(set(streams)), key=streams.count) if streams else None
    cands = g.get("candidates") or []
    return {
        "itemId": g["groupId"],
        "kind": "stream",
        "name": _src(g),
        "componentId": _guid_or_none(stream),
        "count": len(g["rows"]),
        "proposal": _ref(cands[0]["classIri"], cands[0]["label"]) if cands else None,
        "alternatives": [_ref(c["classIri"], c["label"]) for c in cands[1:4]],
        "state": g["state"],
    }


def _measure_item(r: Mapping) -> dict:
    nid = str(r["nativeId"])
    prop = r.get("property")
    cands = r.get("candidates") or []
    proposal = _ref(prop["iri"], prop["label"]) if prop else (_ref(cands[0]["propertyIri"], cands[0]["label"]) if cands else None)
    return {
        "itemId": nid,
        "kind": "measure",
        "name": _measure_label(r),
        "componentId": _guid_or_none(nid.rsplit(":measure:", 1)[-1]) if ":measure:" in nid else None,
        "count": r.get("count"),
        "proposal": proposal,
        "alternatives": [_ref(c["propertyIri"], c["label"]) for c in cands if not proposal or c["propertyIri"] != proposal["iri"]][:3],
        "state": r["state"],
    }


def _parameter_item(r: Mapping) -> dict:
    nid = str(r["nativeId"])
    return {
        "itemId": nid,
        "kind": "parameter",
        "name": str(r["name"]),
        "componentId": _guid_or_none(nid.rsplit(":slider:", 1)[-1]) if ":slider:" in nid else None,
        "count": None,
        "proposal": None if r["state"] == "unmapped" else _ref(PARAMETER_ROLE, "DG parameter"),
        "alternatives": [],
        "state": r["state"],
    }


def _decorate_questions(questions: list, groups: Sequence[dict], measure_rows: Sequence[dict], param_rows: Sequence[dict]) -> None:
    """Add `title` / `titleRu` (one short line) and `items` (one row per proposed component)."""
    by_group = {g["groupId"]: g for g in groups}
    by_measure = {str(r["nativeId"]): r for r in measure_rows}
    by_param = {str(r["nativeId"]): r for r in param_rows}
    for q in questions:
        qtype = q["type"]
        if qtype in ("batch-measures", "map-measure"):
            items = [_measure_item(by_measure[i]) for i in q.get("measureIds") or [] if i in by_measure]
        elif qtype == "batch-parameters":
            ids = list(q.get("parameterIds") or []) + list(q.get("heldParameterIds") or [])
            items = [_parameter_item(by_param[i]) for i in ids if i in by_param]
        else:
            items = [_group_item(by_group[i]) for i in q.get("groupIds") or [] if i in by_group]
        q["items"] = items
        k = len(items)
        n = sum(int(i["count"] or 0) for i in items)
        if qtype == "batch-assign":
            q["title"] = f"{k} {_en_plural(k, 'group', 'groups')}, {n} {_en_plural(n, 'element', 'elements')}: accept the proposed classes"
            q["titleRu"] = (
                f"{k} {_ru_plural(k, ('группа', 'группы', 'групп'))}, {n} {_ru_plural(n, ('элемент', 'элемента', 'элементов'))}: "
                "принять предложенные классы"
            )
        elif qtype == "batch-measures":
            q["title"] = f"{k} calculation {_en_plural(k, 'output', 'outputs')} → DG properties"
            q["titleRu"] = f"{k} {_ru_plural(k, ('расчётный выход', 'расчётных выхода', 'расчётных выходов'))} → свойства DG"
        elif qtype == "map-measure":
            name = items[0]["name"] if items else "?"
            q["title"] = f"Output «{name}»: which DG property?"
            q["titleRu"] = f"Выход «{name}»: какое свойство DG?"
        elif qtype == "batch-parameters":
            h = len(q.get("heldParameterIds") or [])
            k -= h
            q["title"] = f"{k} {_en_plural(k, 'slider', 'sliders')} → DG parameters" + (f", {h} not a parameter (LLM)" if h else "")
            q["titleRu"] = f"{k} {_ru_plural(k, ('слайдер', 'слайдера', 'слайдеров'))} → параметры DG" + (f", {h} — не параметр (LLM)" if h else "")
        else:
            src = items[0]["name"] if items else "?"
            labels = [o["label"] for o in q.get("options") or [] if o.get("roles") and len(o["roles"]) == 1 and str(o["optionId"]).startswith("class:")]
            labels += [local_name(o["roles"][0]) for o in q.get("options") or [] if str(o["optionId"]).startswith("design-error:")]
            labels = [] if q.get("unmatched") else list(dict.fromkeys(labels))[:3]
            choice_en = " or ".join(labels) if labels else "which class"
            choice_ru = " или ".join(labels) if labels else "какой класс"
            q["title"] = f"{src} · {n} {_en_plural(n, 'element', 'elements')}: {choice_en}?"
            q["titleRu"] = f"{src} · {n} {_ru_plural(n, ('элемент', 'элемента', 'элементов'))}: {choice_ru}?"


# Evidence kinds named in the mapping-or-design text (rule evidence is the conflict itself).
_EVIDENCE_WORDS = {
    "name": ("canvas names", "названия на холсте"),
    "profile": ("a learned profile", "выученный профиль"),
    "llm": ("the LLM proposal", "предложение LLM"),
    "measure": ("a calculation output", "расчётный выход"),
    "ifc": ("the IFC class", "класс IFC"),
    "population": ("the element count", "численность элементов"),
}


def _mapping_or_design_text(g: Mapping, conflicting: Mapping, alt: Optional[Mapping], option_ids: Sequence[str]) -> tuple:
    """EN/RU text of a mapping-or-design question (owner 2026-10-18: say what each option means).

    Names the evidence behind the conflicting class, the rule outcomes per class, and what
    each offered button does; buttons are quoted with their Web UI labels.
    """
    c_lab, c_iri = conflicting["label"], conflicting["classIri"]
    kinds: list = []
    for e in conflicting["evidence"]:
        if e["weight"] > 0 and e["kind"] in _EVIDENCE_WORDS and e["kind"] not in kinds:
            kinds.append(e["kind"])
    if kinds:
        en = f"{_describe_group(g, 'en')}. Evidence for {c_lab}: " + ", ".join(_EVIDENCE_WORDS[k][0] for k in kinds)
        en += f"; but as {c_lab}: {_impact_phrase(g, c_iri, 'en')}."
        ru = f"{_describe_group(g, 'ru')}. Свидетельства за {c_lab}: " + ", ".join(_EVIDENCE_WORDS[k][1] for k in kinds)
        ru += f"; но как {c_lab}: {_impact_phrase(g, c_iri, 'ru')}."
    else:
        en = f"{_describe_group(g, 'en')}. As {c_lab}: {_impact_phrase(g, c_iri, 'en')}."
        ru = f"{_describe_group(g, 'ru')}. Как {c_lab}: {_impact_phrase(g, c_iri, 'ru')}."
    if alt:
        en += f" As {alt['label']}: {_impact_phrase(g, alt['classIri'], 'en')}."
        ru += f" Как {alt['label']}: {_impact_phrase(g, alt['classIri'], 'ru')}."
    en += " Is the mapping wrong or the design?"
    ru += " Где ошибка — в меппинге или в проекте?"
    violated = ", ".join(x["ruleId"] for x in conflicting["conflicts"]) or "—"
    if alt and f"class:{alt['classIri']}" in option_ids:
        a = alt["label"]
        en += f' "{a}": the mapping is wrong; the elements get {a}.'
        ru += f" «{a}»: ошибся меппинг; элементы получат класс {a}."
    en += (
        f' "{c_lab} — rule violations are design errors": the class is right and the design is wrong; the elements get {c_lab}, '
        f"and the violations of {violated} stay in the VALIDATOR report without raising this question again."
    )
    ru += (
        f" «{c_lab} — нарушения правил — ошибки проекта»: класс верен, ошибся проект; элементы получат класс {c_lab}, "
        f"а нарушения {violated} останутся в отчёте VALIDATOR и больше не вызовут этот вопрос."
    )
    if "both" in option_ids:
        en += ' "Both roles": the elements get both classes and are checked by the rules of both.'
        ru += " «Обе роли»: элементы получат оба класса и будут проверяться правилами обоих."
    # "None of these" is offered with every group question.
    en += ' "None of these": the elements get no DG class and are not checked.'
    ru += " «Ни один из вариантов»: элементы останутся без класса DG и не будут проверяться."
    en += " The answer is remembered as a profile for similar elements."
    ru += " Ответ запомнится как профиль для похожих элементов."
    return en, ru


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
            text, text_ru = _mapping_or_design_text(g, conflicting, alt, [o["optionId"] for o in options])
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
    # A Revit group with no candidate at all (no profile, rule, name, IFC or population
    # support) is asked once with every class, so a cold Revit read never leaves a family
    # unmapped without a question (D-52). Grasshopper keeps its LLM proposal for this.
    for g in groups:
        if g["state"] != "unmapped" or str(g["sig"].get("platform") or "") != "revit":
            continue
        if any(r.get("decidedNone") or r.get("matched") for r in g["rows"]):
            continue
        options = [
            {"optionId": f"class:{iri_of[c]}", "label": label_of[c], "roles": [iri_of[c]]}
            for c in sorted(iri_of, key=lambda c: label_of[c])
        ]
        cons = [_consequences(g, o["optionId"], o["roles"]) for o in options]
        options.append({"optionId": "none", "label": "None of these", "roles": []})
        questions.append(
            {
                "questionId": "Q-" + _sha("assign-unmatched|" + g["groupId"], 8),
                "type": "assign",
                "unmatched": True,
                "groupIds": [g["groupId"]],
                "text": f"{_describe_group(g, 'en')}: no profile, rule, name or IFC evidence points to a DG class. Which class are they?",
                "textRu": f"{_describe_group(g, 'ru')}: ни профиль, ни правила, ни имена, ни IFC не указывают на класс DG. Какой это класс?",
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
# Grasshopper parameters (sliders) and measures (outputs of calculation components)
# ---------------------------------------------------------------------------
# Owner clarification 2026-10-18 (1303-CONTEXT D-37): in the DG ontology a slider is a DG
# Parameter (PARAMETER STATE), and a datatype property value comes from the output of a
# calculation component (Area, a measure script). An LLM proposal is one more vote; a
# human confirms.

PARAMETER_ROLE = "dg:Parameter"
_INDEX_TOKEN = re.compile(r"^(?:\d+|[a-zа-яё]\d+|\d+[a-zа-яё])$")


def name_stem(name: Any) -> str:
    """Name without index tokens: 'Module Width F1' → 'module width', '1 оффсет' → 'оффсет'."""
    toks = split_tokens(name)
    core = [t for t in toks if not _INDEX_TOKEN.match(t)]
    return " ".join(core or toks)


def _property_core_tokens(p: PropertyInfo) -> list:
    return [t for t in split_tokens(p.local) if t not in PROPERTY_STOP and t not in UNIT_TOKENS]


def property_words(p: PropertyInfo) -> set:
    words: set = set()
    for t in split_tokens(p.label) + split_tokens(p.local):
        if len(t) < 3 or t in PROPERTY_STOP or t in UNIT_TOKENS:
            continue
        words.add(_singular(t))
    for syn in p.synonyms:
        words |= {w for w in concepts(split_tokens(syn)) if len(w) >= 3}
    return words


def property_acronym(p: PropertyInfo) -> str:
    """hasAspectRatio → 'ar', hasPlanarityDeviationM → 'pd', hasWidthM → 'w'."""
    return "".join(t[0] for t in _property_core_tokens(p) if t)


def parameter_features(p: Mapping, platform_default: str = "grasshopper") -> dict:
    platform = p.get("platform") or platform_default
    return {"platform": str(platform).strip().lower(), "kind": "parameter", "nameStem": name_stem(p.get("name"))}


def measure_features(m: Mapping, platform_default: str = "grasshopper") -> dict:
    platform = m.get("platform") or platform_default
    return {"platform": str(platform).strip().lower(), "kind": "measure", "measureName": str(m.get("name") or "").strip().lower()}


def _texts(values: Any) -> list:
    if not isinstance(values, (list, tuple)):
        return []
    return [str(v).strip() for v in values if isinstance(v, (str, int, float)) and not isinstance(v, bool) and str(v).strip()]


def _validate_named(items: Any, cfg: Mapping, what: str, limit_key: str) -> list:
    if items is None:
        return []
    if not isinstance(items, list):
        raise MappingInputError("MAPPING_INPUT_INVALID", f"{what} must be a list")
    if len(items) > int(cfg[limit_key]):
        raise MappingInputError("MAPPING_INPUT_INVALID", f"at most {int(cfg[limit_key])} {what} per session")
    seen = set()
    for p in items:
        if not isinstance(p, Mapping) or not str(p.get("nativeId") or "").strip() or not str(p.get("name") or "").strip():
            raise MappingInputError("MAPPING_INPUT_INVALID", f"every item of {what} needs a nativeId and a name")
        nid = str(p["nativeId"])
        if nid in seen:
            raise MappingInputError("MAPPING_INPUT_INVALID", f"duplicate {what} nativeId {nid}")
        seen.add(nid)
    return sorted(items, key=lambda p: str(p["nativeId"]))


def _validate_parameters(parameters: Any, cfg: Mapping) -> list:
    return _validate_named(parameters, cfg, "parameters", "max_parameters")


def _validate_measures(measures: Any, cfg: Mapping) -> list:
    return _validate_named(measures, cfg, "measures", "max_measures")


def _prop_ref(p: PropertyInfo) -> dict:
    return {"iri": p.iri, "label": p.label, "classes": list(p.classes)}


def _llm_entry(llm: Optional[Mapping], kind: str, nid: Any) -> Optional[Mapping]:
    block = (llm or {}).get(kind) or {}
    entry = block.get(str(nid)) if isinstance(block, Mapping) else None
    return entry if isinstance(entry, Mapping) else None


def _llm_conf(entry: Mapping) -> float:
    c = _num(entry.get("confidence"))
    return 0.7 if c is None else max(0.0, min(1.0, c))


def _matched_profiles(profiles: Sequence[Mapping], kind: str, feats: Mapping, cfg: Mapping) -> list:
    out = []
    for pr in profiles:
        if pr.get("state", "active") == "active" and (pr.get("selector") or {}).get("kind") == kind and profile_matches(pr, feats):
            out.append((pr, _profile_conf(pr, cfg)))
    return sorted(out, key=lambda t: str(t[0].get("profileId")))


def map_parameters(
    parameters: Any,
    profiles: Sequence[Mapping] = (),
    decided: Optional[Mapping] = None,
    llm: Optional[Mapping] = None,
    platform_default: str = "grasshopper",
    config: Optional[Mapping] = None,
) -> list:
    """Which named sliders are DG Parameters (PARAMETER STATE inputs, ParameterId = name)."""
    cfg = dict(CONFIG)
    cfg.update(config or {})
    items = _validate_parameters(parameters, cfg)
    decided = {str(k): list(v) for k, v in (decided or {}).items()}
    rows = []
    for item in items:
        nid = str(item["nativeId"])
        name = str(item["name"]).strip()
        feats = parameter_features(item, platform_default)
        matched = _matched_profiles(profiles, "parameter", feats, cfg)
        entry = _llm_entry(llm, "parameters", nid)
        reason = None
        if nid in decided:
            state, source, conf = ("confirmed" if decided[nid] else "unmapped"), "human", 1.0
        elif any(c >= cfg["profile_auto"] for _, c in matched):
            best = max((t for t in matched if t[1] >= cfg["profile_auto"]), key=lambda t: t[1])
            state = "auto" if PARAMETER_ROLE in (best[0].get("roles") or []) else "unmapped"
            source, conf, reason = "profile", best[1], f"profile {best[0]['profileId']}"
        elif entry is not None:
            yes = bool(entry.get("isParameter"))
            state, source, conf = ("suggested" if yes else "unmapped"), "llm", _llm_conf(entry)
            reason = str(entry.get("reason") or "")[:300] or None
        else:
            state, source, conf, reason = "suggested", "name", 0.8, "named slider"
        rows.append(
            {
                "nativeId": nid,
                "name": name,
                "nameStem": feats["nameStem"],
                "state": state,
                "source": source,
                "isParameter": state in ("confirmed", "auto", "suggested"),
                "confidence": _r(conf),
                "reason": reason,
                "value": item.get("value"),
                "questionId": None,
            }
        )
    return rows


def _natural_key(text: str) -> list:
    return [int(x) if x.isdigit() else x.lower() for x in re.split(r"(\d+)", text)]


def _shown_names(names: Sequence[str]) -> str:
    names = sorted(set(names), key=_natural_key)
    return ", ".join(names) if len(names) <= 6 else f"{', '.join(names[:4])} … {names[-1]}"


def _parameter_questions(rows: Sequence[dict]) -> list:
    members = [r for r in rows if r["state"] == "suggested"]
    if not members:
        return []
    # Sliders the LLM holds back as "not a DG parameter" have no human decision yet: they are shown
    # in the same question, and its answer decides them too (rehearsal 2026-10-18: otherwise every
    # later variant asked about them again).
    held = [r for r in rows if r["state"] == "unmapped" and r.get("source") == "llm"]
    ids = sorted(m["nativeId"] for m in members)
    held_ids = sorted(h["nativeId"] for h in held)
    n = len(members)
    shown = _shown_names([m["name"] for m in members])
    qid = "Q-" + _sha("batch-parameters|" + "|".join(ids) + ("|held:" + "|".join(held_ids) if held_ids else ""), 8)
    for m in members + held:
        m["questionId"] = qid
    text = f"{n} {_en_plural(n, 'slider', 'sliders')} look like DG parameters of the design (PARAMETER STATE): {shown}."
    text_ru = (
        f"{n} {_ru_plural(n, ('слайдер', 'слайдера', 'слайдеров'))} {'похож' if n == 1 else 'похожи'} на параметры DG "
        f"(PARAMETER STATE): {shown}."
    )
    if held:
        names = _shown_names([h["name"] for h in held])
        text += f" The LLM holds {names} back as not a DG parameter."
        text_ru += f" LLM считает не параметром DG: {names}."
    return [
        {
            "questionId": qid,
            "type": "batch-parameters",
            "groupIds": [],
            "parameterIds": ids,
            "heldParameterIds": held_ids,
            "text": text + " Accept all?",
            "textRu": text_ru + " Принять все?",
            "options": [
                {"optionId": "accept-all", "label": "Accept all as DG parameters", "roles": None},
                {"optionId": "none", "label": "None of these", "roles": []},
            ],
            "consequences": [],
        }
    ]


def map_measures(
    measures: Any,
    properties: Sequence[PropertyInfo],
    profiles: Sequence[Mapping] = (),
    decided: Optional[Mapping] = None,
    llm: Optional[Mapping] = None,
    platform_default: str = "grasshopper",
    config: Optional[Mapping] = None,
) -> list:
    """Propose the DG datatype property each calculation output carries, and its element stream.

    Evidence: values equal to the property the plugin computed from the stream's own
    geometry (strong; weak for a constant column), the output name as the property's
    acronym or words, the canvas text around the component, the LLM proposal, and learned
    measure profiles.
    """
    cfg = dict(CONFIG)
    cfg.update(config or {})
    items = _validate_measures(measures, cfg)
    decided = {str(k): list(v) for k, v in (decided or {}).items()}
    props = sorted(properties, key=lambda p: p.local)
    by_local = {p.local: p for p in props}
    words_of = {p.local: property_words(p) for p in props}
    rows = []
    for item in items:
        nid = str(item["nativeId"])
        name = str(item["name"]).strip()
        feats = measure_features(item, platform_default)
        name_toks = split_tokens(name)
        own = concepts(name_toks)
        ctx = concepts(t for x in _texts(item.get("names")) + _texts([item.get("component")]) for t in split_tokens(x)) - own
        streams = [s for s in (item.get("streams") or []) if isinstance(s, Mapping) and s.get("stream")]
        path_streams = sorted(str(s["stream"]) for s in streams if s.get("pathMatch"))
        input_streams = [s for s in path_streams if any(str(x["stream"]) == s and x.get("input") for x in streams)]
        entry = _llm_entry(llm, "measures", nid)
        # The LLM's stream counts only when the output's branches follow it.
        llm_stream = str(entry["stream"]) if entry is not None and entry.get("stream") and (not path_streams or str(entry["stream"]) in path_streams) else None
        score: dict = {}
        evid: dict = {}
        stream_of: dict = {}
        ties_of: dict = {}
        for p in props:
            s, parts = 0.0, []
            acr = property_acronym(p)
            if acr and any(t == acr for t in name_toks):
                s += cfg["w_measure_acronym"]
                parts.append(f"'{name}' is the acronym of {p.label}")
            for w in sorted(words_of[p.local]):
                k = 0.5 if w in GENERIC_WORDS else 1.0
                if w in own:
                    s += cfg["w_param_own"] * k
                    parts.append(f"name '{name}' → {w}")
                elif w in ctx:
                    s += cfg["w_param_context"] * k
                    parts.append(f"canvas text → {w}")
            best_f, best_stream, constant, best_input = 0.0, None, False, False
            for st in streams:
                agreement = st.get("agreement") or {}
                f = _num(agreement.get(p.local)) if isinstance(agreement, Mapping) else None
                # Equal agreement on two streams (copies of the same panels): the stream the
                # calculation component reads itself is the one it measures.
                if f is not None and (f > best_f or (f == best_f and f > 0 and st.get("input") and not best_input)):
                    best_f, best_stream, constant, best_input = f, str(st["stream"]), bool(st.get("constant")), bool(st.get("input"))
            if best_f >= 0.95:
                s += (cfg["w_measure_agree_const"] if constant else cfg["w_measure_agree"]) * best_f
                parts.append(f"values equal {p.label} of stream {best_stream} ({best_f:.2f}{', constant' if constant else ''})")
                stream_of[p.local] = best_stream
                # Streams agreeing just as well (one script reads Panels A and B, both all zero):
                # the rule's class picks among them when the rule is bound.
                tied = sorted(str(st["stream"]) for st in streams if _num((st.get("agreement") or {}).get(p.local)) == best_f)
                ties_of[p.local] = [t for t in tied if t in input_streams] or tied
            if entry is not None and local_name(entry.get("propertyIri")) == p.local:
                s += cfg["w_llm"] * _llm_conf(entry)
                parts.append("LLM: " + (str(entry.get("reason") or "proposed")[:200]))
                if llm_stream and (p.local not in stream_of or llm_stream in ties_of.get(p.local, ())):
                    stream_of[p.local] = llm_stream
            if s:
                score[p.local] = s
                evid[p.local] = parts
        matched = _matched_profiles(profiles, "measure", feats, cfg)
        for pr, conf in matched:
            for r in pr.get("roles") or ():
                lr = local_name(r)
                if lr in by_local:
                    score[lr] = score.get(lr, 0.0) + cfg["w_profile"] * conf
                    evid.setdefault(lr, []).append(f"profile {pr['profileId']} (confidence {conf:.2f})")
            for r in pr.get("excludedRoles") or ():
                lr = local_name(r)
                if lr in score:
                    score[lr] -= cfg["w_profile"] * conf
        conf_of = {k: _r(_logistic(cfg["prior_param"] + v)) for k, v in score.items()}
        cands = sorted((k for k in conf_of if conf_of[k] >= cfg["tau_candidate"]), key=lambda k: (-conf_of[k], k))
        prop_local, source = None, None
        if nid in decided:
            chosen = [local_name(r) for r in decided[nid] if local_name(r) in by_local]
            state = "confirmed" if chosen else "unmapped"
            prop_local, source = (chosen[0] if chosen else None), "human"
        else:
            auto = [(pr, c) for pr, c in matched if c >= cfg["profile_auto"]]
            roles = sorted({local_name(r) for pr, _ in auto for r in pr.get("roles") or () if local_name(r) in by_local})
            if auto and roles:
                state, prop_local, source = "auto", roles[0], "profile"
            elif auto:
                state, source = "unmapped", "profile"
            elif not cands:
                state = "unmapped"
            else:
                top = cands[0]
                margin = conf_of[top] - conf_of[cands[1]] if len(cands) > 1 else 1.0
                if conf_of[top] >= cfg["tau_clear"] and margin >= cfg["margin_delta"]:
                    state, prop_local, source = "suggested", top, "evidence"
                else:
                    state = "ambiguous"
        def stream_for(local: Optional[str]) -> Optional[str]:
            if local and local in stream_of:
                return stream_of[local]
            if llm_stream:
                return llm_stream
            if len(input_streams) == 1:
                return input_streams[0]
            return path_streams[0] if len(path_streams) == 1 else None

        rows.append(
            {
                "nativeId": nid,
                "name": name,
                "component": item.get("component"),
                "count": item.get("count"),
                "min": item.get("min"),
                "max": item.get("max"),
                "state": state,
                "source": source,
                "property": _prop_ref(by_local[prop_local]) if prop_local else None,
                "stream": stream_for(prop_local),
                "streamOptions": ties_of.get(prop_local, []) if prop_local else [],
                "pathStreams": path_streams,
                "candidates": [
                    {
                        "propertyIri": by_local[k].iri,
                        "label": by_local[k].label,
                        "classes": list(by_local[k].classes),
                        "confidence": conf_of[k],
                        "evidence": evid.get(k, []),
                        "stream": stream_for(k),
                        "streamOptions": ties_of.get(k, []),
                    }
                    for k in cands[:4]
                ],
                "questionId": None,
            }
        )
    return rows


def measure_class_evidence(measure_rows: Sequence[Mapping], known: set, cfg: Mapping) -> dict:
    """Stream → class evidence from the calculation outputs that measure it.

    An output on a stream carries a DG property, so the stream's class is one whose rules use
    that property (H on 'bbox F' → hasTotalHeightM → Facade). The vote is shared between the
    classes using the property, between streams whose values agree equally well, and, for an
    open output, between its two leading candidates.
    """
    acc: dict = {}
    for r in measure_rows:
        state = r.get("state")
        cands = r.get("candidates") or []
        if state in ("confirmed", "auto") and r.get("property"):
            prop = r["property"]
            picks = [(prop.get("label"), prop.get("classes") or [], 1.0, r.get("stream"), r.get("streamOptions") or [])]
        elif state == "suggested" and cands:
            c = cands[0]
            picks = [(c["label"], c.get("classes") or [], c["confidence"], c.get("stream"), c.get("streamOptions") or [])]
        elif state == "ambiguous":
            picks = [(c["label"], c.get("classes") or [], c["confidence"], c.get("stream"), c.get("streamOptions") or []) for c in cands[:2]]
        else:
            continue
        for label, classes, conf, stream, ties in picks:
            users = sorted({local_name(c) for c in classes} & known)
            targets = ties if len(ties) > 1 else ([stream] if stream else [])
            if not targets or not users:
                continue
            w = cfg["w_measure_class"] * float(conf) / len(picks) / len(users) / len(targets)
            for target in targets:
                for cls in users:
                    slot = acc.setdefault((str(target), cls), [0.0, []])
                    slot[0] += w
                    slot[1].append(f"output {r['name']} → {label}")
    out: dict = {}
    for (stream, cls), (w, parts) in sorted(acc.items()):
        detail = "calculation outputs used by its rules: " + ", ".join(sorted(set(parts)))
        out.setdefault(stream, []).append(Evidence(cls, "measure", _r(min(w, cfg["w_measure_class_cap"])), detail[:300]))
    return out


def _measure_label(r: Mapping) -> str:
    comp = r.get("component")
    return f"{r['name']} ({comp})" if comp else str(r["name"])


def _measure_questions(rows: Sequence[dict]) -> list:
    questions = []
    suggested = [r for r in rows if r["state"] == "suggested" and r.get("property")]
    if suggested:
        ids = sorted(r["nativeId"] for r in suggested)
        n = len(suggested)
        pairs = "; ".join(f"{_measure_label(r)} → {r['property']['label']}" for r in sorted(suggested, key=lambda r: _natural_key(r["name"])))
        qid = "Q-" + _sha("batch-measures|" + "|".join(ids), 8)
        for r in suggested:
            r["questionId"] = qid
        questions.append(
            {
                "questionId": qid,
                "type": "batch-measures",
                "groupIds": [],
                "measureIds": ids,
                "text": f"{n} calculation {_en_plural(n, 'output has', 'outputs have')} one clear DG property: {pairs}. Accept all?",
                "textRu": (
                    f"{n} {_ru_plural(n, ('расчётный выход', 'расчётных выхода', 'расчётных выходов'))} "
                    f"{'имеет' if n == 1 else 'имеют'} одно очевидное свойство DG: {pairs}. Принять все?"
                ),
                "options": [
                    {"optionId": "accept-all", "label": "Accept all proposed properties", "roles": None},
                    {"optionId": "none", "label": "None of these", "roles": []},
                ],
                "consequences": [],
            }
        )
    for r in sorted((r for r in rows if r["state"] == "ambiguous" and r["candidates"]), key=lambda r: _natural_key(r["name"])):
        cands = r["candidates"][:3]
        span = f"{r.get('count')} values" if r.get("min") is None else f"{r.get('count')} values, {_fmt(_num(r['min']) or 0)}…{_fmt(_num(r['max']) or 0)}"
        span_ru = f"{r.get('count')} знач." if r.get("min") is None else f"{r.get('count')} знач., {_fmt(_num(r['min']) or 0)}…{_fmt(_num(r['max']) or 0)}"
        listing = "; ".join(f"{c['label']} ({c['confidence']:.2f})" for c in cands)
        qid = "Q-" + _sha("map-measure|" + r["nativeId"], 8)
        r["questionId"] = qid
        questions.append(
            {
                "questionId": qid,
                "type": "map-measure",
                "groupIds": [],
                "measureIds": [r["nativeId"]],
                "text": f"Output «{_measure_label(r)}» ({span}) could be one of the DG properties: {listing}. Which one?",
                "textRu": f"Выход «{_measure_label(r)}» ({span_ru}) может соответствовать свойствам DG: {listing}. Какому?",
                "options": [{"optionId": f"property:{c['propertyIri']}", "label": c["label"], "roles": [c["propertyIri"]]} for c in cands]
                + [{"optionId": "none", "label": "Not a DG property", "roles": []}],
                "consequences": [],
            }
        )
    return questions


def _item_profile(existing: Mapping, out: dict, pid: str, project, platform, selector, roles, excluded, actor, at, decision_id, support, cfg) -> None:
    prof = dict(out.get(pid) or existing.get(pid) or {})
    if prof:
        prof["state"] = "active"  # a human answer switches a retired profile back on
        prof["confirmations"] = int(prof.get("confirmations", 0)) + 1
        prof["decisionIds"] = sorted(set(prof.get("decisionIds", [])) | {decision_id})
        prof["support"] = max(int(prof.get("support", 0)), support)
        prof["updatedAt"] = at
    else:
        prof = {
            "profileId": pid,
            "project": project,
            "platform": platform,
            "selector": dict(selector),
            "roles": list(roles),
            "excludedRoles": list(excluded),
            "acceptsViolations": [],
            "source": "learned",
            "confirmations": 1,
            "rejections": 0,
            "support": support,
            "createdBy": actor,
            "createdAt": at,
            "updatedAt": at,
            "decisionIds": [decision_id],
            "engineVersion": ENGINE_VERSION,
            "state": "active",
        }
    prof["confidence"] = profile_confidence(prof["confirmations"], prof.get("rejections", 0), cfg)
    out[pid] = prof


def _decide_items(
    result: Mapping,
    question: Mapping,
    option: Mapping,
    actor: str,
    at: str,
    profiles: Sequence[Mapping],
    project: Optional[str],
    platform_default: str,
    cfg: Mapping,
) -> dict:
    qtype = question.get("type")
    kind = "parameters" if qtype == "batch-parameters" else "measures"
    by_id = {r["nativeId"]: r for r in result.get(kind) or []}
    ids = question.get("parameterIds") if kind == "parameters" else question.get("measureIds")
    held = set(question.get("heldParameterIds") or []) if kind == "parameters" else set()
    members = [nid for nid in sorted(list(ids or []) + sorted(held)) if nid in by_id]
    if not members:
        raise MappingInputError("MAPPING_QUESTION_NOT_FOUND", f"question {question['questionId']} has nothing left to decide", 404)
    platform = str(result.get("platform") or platform_default).lower()
    option_id = option["optionId"]
    decision_id = "D-" + _sha(f"{question['questionId']}|{kind}|{option_id}|{at}", 12)
    existing = {p["profileId"]: dict(p) for p in profiles}
    out: dict = {}
    decided: dict = {}
    for nid in members:
        row = by_id[nid]
        if kind == "parameters":
            # Accepting the batch accepts the proposal as shown: the LLM-held sliders are not parameters.
            chosen = [PARAMETER_ROLE] if option_id == "accept-all" and nid not in held else []
            selector = {"kind": "parameter", "nameStem": row["nameStem"]}
            excluded = [] if chosen else [PARAMETER_ROLE]
        else:
            if option_id == "accept-all":
                chosen = [row["property"]["iri"]] if row.get("property") else []
            else:
                chosen = list(option.get("roles") or [])
            selector = {"kind": "measure", "measureName": str(row["name"]).strip().lower()}
            excluded = [] if chosen else sorted({c["propertyIri"] for c in row.get("candidates") or []})
        decided[nid] = chosen
        pid = profile_id(platform, selector, chosen, excluded)
        _item_profile(existing, out, pid, project, platform, selector, chosen, excluded, actor, at, decision_id, 1, cfg)
    decision = {
        "decisionId": decision_id,
        "project": project,
        "questionId": question["questionId"],
        "groupId": f"{kind}:{question['questionId']}",
        "optionId": option_id,
        "roles": sorted({r for v in decided.values() for r in v}),
        "memberCount": len(members),
        "memberIds": members,
        "questionText": question["text"],
        "evidenceShown": [{"id": nid, "candidates": by_id[nid].get("candidates", [])} for nid in members],
        "consequencesShown": [],
        "decidedBy": actor,
        "decidedAt": at,
        "profileId": sorted(out)[0] if out else None,
    }
    key = "decidedParameters" if kind == "parameters" else "decidedMeasures"
    return {"decisions": [decision], "profiles": [out[k] for k in sorted(out)], "decided": {}, "splits": {}, key: decided}


def rule_bindings(result: Mapping, constraints: Sequence[Constraint]) -> list:
    """Rule → class → property → calculation output, for PROPERTY STATE placement.

    A rule binds when its class has applied elements, its property is the confirmed (or
    auto) property of a measure, and that measure's stream, or a stream whose values agree
    with it just as well, is one of the class's streams. A measure without branch-matched
    streams (no path information) binds to a class with a single stream.
    """
    streams_of: dict = {}
    iri_of: dict = {}
    for el in result.get("elements") or []:
        if el.get("state") in ("confirmed", "auto") and el.get("stream"):
            for r in el.get("roles") or []:
                streams_of.setdefault(local_name(r["classIri"]), set()).add(str(el["stream"]))
                iri_of[local_name(r["classIri"])] = r["classIri"]
    measures = [m for m in result.get("measures") or [] if m.get("state") in ("confirmed", "auto") and m.get("property")]
    out = []
    for (rule_id, cls), group in sorted(rule_groups(constraints).items()):
        cls_streams = streams_of.get(cls) or set()
        for prop in sorted({c.prop_local for c in group}):
            cands = [m for m in measures if local_name(m["property"]["iri"]) == prop]
            match, stream = next(((m, m["stream"]) for m in cands if m.get("stream") in cls_streams), (None, None))
            if match is None:
                match, stream = next(
                    ((m, t) for m in cands for t in m.get("streamOptions") or [] if t in cls_streams), (None, None)
                )
            if match is None and len(cls_streams) == 1:
                match = next((m for m in cands if not m.get("stream") and not m.get("pathStreams")), None)
                stream = next(iter(cls_streams))
            if match is not None:
                out.append(
                    {
                        "ruleId": rule_id,
                        "classLocal": cls,
                        "classIri": iri_of.get(cls, cls),
                        "propertyIri": match["property"]["iri"],
                        "measureId": match["nativeId"],
                        "stream": stream,
                    }
                )
    return out


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
    if question.get("type") in ("batch-parameters", "batch-measures", "map-measure"):
        if option is None:
            raise MappingInputError("MAPPING_OPTION_INVALID", f"option {option_id} is not offered by {question_id}")
        return _decide_items(result, question, option, actor, at, profiles, project, platform_default, cfg)
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
        known_iris = {c.iri for c in classes}
        unknown = [r for r in chosen if r not in known_iris]
        if unknown:
            raise MappingInputError("MAPPING_INPUT_INVALID", f"unknown classes {unknown}")
        chosen = sorted(set(chosen))
        member_feats = [rows[nid]["feats"] for nid in members]
        others = [(rows[nid]["feats"], _label_set(rows[nid]["el"], groups)) for nid in sorted(rows) if rows[nid]["el"]["groupId"] != gid]
        platform = member_feats[0].get("platform", platform_default)
        induced = induce_profile(member_feats, others, chosen, platform, excluded, project)
        decision_id = "D-" + _sha(f"{question_id}|{gid}|{option_id}|{at}", 12)
        pid = induced["profileId"]
        prof = existing.get(pid) or out_profiles.get(pid)
        if prof:
            prof = dict(prof)
            # A human answer that gives a retired profile again switches it back on.
            prof["state"] = "active"
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


def partition(result: Mapping, constraints: Optional[Sequence[Constraint]] = None) -> dict:
    """Applied mapping. With `constraints`, also the rule bindings CONNECTOR places as PROPERTY STATE."""
    by_class: dict[str, list] = {}
    applied, skipped, elements = 0, [], []
    for el in result["elements"]:
        if el["state"] in ("confirmed", "auto") and el["roles"]:
            roles = sorted(r["classIri"] for r in el["roles"])
            elements.append({"nativeId": el["nativeId"], "roles": roles, **({"stream": el["stream"]} if el.get("stream") else {})})
            for r in roles:
                by_class.setdefault(r, []).append(el["nativeId"])
            applied += 1
        else:
            skipped.append({"nativeId": el["nativeId"], "reason": el["state"]})
    out = {
        "applied": applied,
        "byClass": {k: sorted(v) for k, v in sorted(by_class.items())},
        "elements": elements,
        "skipped": skipped,
    }
    if result.get("parameters"):
        out["parameters"] = [
            {"nativeId": r["nativeId"], "name": r["name"]}
            for r in result["parameters"]
            if r["state"] in ("confirmed", "auto")
        ]
    if result.get("measures"):
        out["measures"] = [
            {"nativeId": r["nativeId"], "name": r["name"], "propertyIri": r["property"]["iri"], "stream": r.get("stream")}
            for r in result["measures"]
            if r["state"] in ("confirmed", "auto") and r.get("property")
        ]
    if constraints is not None:
        out["bindings"] = rule_bindings(result, constraints)
    return out


def populations_of(result: Mapping) -> dict:
    """Confirmed group sizes per class: one size per applied GH stream (else per group), D-49.

    Per-class totals merged streams (Panels A + C = 250 triangles) and hid the real
    group sizes another platform compares against.
    """
    counts: dict[tuple, int] = {}
    for el in result.get("elements", []):
        if el.get("state") in ("confirmed", "auto"):
            unit = el.get("stream") or el.get("groupId")
            for r in el.get("roles") or ():
                key = (str(unit), local_name(r["classIri"]))
                counts[key] = counts.get(key, 0) + 1
    sizes: dict[str, list] = {}
    for (_, cls), n in counts.items():
        sizes.setdefault(cls, []).append(n)
    return {cls: sorted(v) for cls, v in sorted(sizes.items())}


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
