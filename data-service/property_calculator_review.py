"""Pure read model of the property-calculator review (Phase 1303-17, DGOPN-05, D-54, D-58).

What a person needs to confirm a generated calculator: its source, the values it produced in a published
validation run, and the rule verdicts of that run. Everything here is computed from persisted data (the run's
``statePayloadJson`` and the verdict counts the store reads); there is no Neo4j, no HTTP and no app import, so the
module is tested without services.

Honesty note (D-58, SECURITY-BOUNDARY 3.10): a run records no calculator sha256, so "this run belongs to this
calculator" is a heuristic. ``runNewerThanCalculator`` says the run was created after the calculator was stored; it
does not prove which calculator computed the values. Objects named by ``objectRef`` are opaque strings here;
whether ``objectRef`` maps to the Revit box one-to-one is verified live in plan 1303-18 (research assumption A1).
"""

from __future__ import annotations

import json
import unicodedata
from typing import Any, Iterable, Mapping

SAMPLE_LIMIT = 10
MEANING_MAX = 160
UNIT_MAX = 40
REASON_MAX = 300


def _payload(run: Mapping | None) -> dict:
    raw = (run or {}).get("statePayloadJson")
    if isinstance(raw, dict):
        return raw
    if not isinstance(raw, str) or not raw.strip():
        return {}
    try:
        parsed = json.loads(raw)
    except ValueError:
        return {}
    return parsed if isinstance(parsed, dict) else {}


def _entries(payload: dict, key: str) -> list[dict]:
    value = payload.get(key)
    return [e for e in value if isinstance(e, dict)] if isinstance(value, list) else []


def run_values(run: Mapping | None, iri: str) -> list[dict]:
    """The values a run holds for one DataProperty: ``[{objectRef, label, value}]``, deduplicated on
    (objectRef, value) and sorted by (objectRef, str(value)). An absent or invalid payload gives []."""
    payload = _payload(run)
    labels = {str(o.get("objectRef")): o.get("label") for o in _entries(payload, "objStates")
              if o.get("objectRef") is not None}
    seen: set[tuple[str, str]] = set()
    values: list[dict] = []
    for state in _entries(payload, "propStates"):
        if state.get("dataPropertyIri") != iri:
            continue
        prop_value = state.get("propValue")
        if not isinstance(prop_value, dict):
            continue
        ref = str(state.get("objectRef"))
        value = prop_value.get("value")
        key = (ref, json.dumps(value, sort_keys=True, ensure_ascii=False, default=str))
        if key in seen:
            continue
        seen.add(key)
        values.append({"objectRef": ref, "label": labels.get(ref), "value": value})
    values.sort(key=lambda v: (v["objectRef"], str(v["value"])))
    return values


def _is_number(value: Any) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool)


def sample_summary(values: list[dict]) -> dict:
    """At most ``SAMPLE_LIMIT`` samples plus ``stats {n, numeric, min, max}`` over all values. min and max range over
    int or float values only (never bool) and are None when there are none."""
    numbers = [v["value"] for v in values if _is_number(v.get("value"))]
    return {
        "samples": [dict(v) for v in values[:SAMPLE_LIMIT]],
        "stats": {"n": len(values), "numeric": len(numbers),
                  "min": min(numbers) if numbers else None, "max": max(numbers) if numbers else None},
    }


def verdict_counts(rows: Iterable[Mapping] | None) -> list[dict]:
    """``[{ruleId, status, count}]`` -> ``[{ruleId, counts: {status: n}}]`` sorted by ruleId, statuses sorted."""
    per_rule: dict[str, dict[str, int]] = {}
    for row in rows or []:
        rule = row.get("ruleId")
        if rule is None:
            continue
        bucket = per_rule.setdefault(str(rule), {})
        status = str(row.get("status"))
        bucket[status] = bucket.get(status, 0) + int(row.get("count") or 0)
    return [{"ruleId": rule, "counts": dict(sorted(per_rule[rule].items()))} for rule in sorted(per_rule)]


def clean_line(text: Any, limit: int) -> str:
    """One clean line of operator text: whitespace collapsed to single spaces, control characters dropped, capped at
    ``limit``. Raises ValueError when nothing is left. It guards the text that later enters the ingest prompt."""
    if not isinstance(text, str):
        raise ValueError("text is required")
    kept = []
    for char in text:
        if char.isspace():
            kept.append(" ")
        elif unicodedata.category(char) in ("Cc", "Cf", "Cs", "Co"):
            continue
        else:
            kept.append(char)
    cleaned = " ".join("".join(kept).split())[:max(0, int(limit))].rstrip()
    if not cleaned:
        raise ValueError("text is empty after cleaning")
    return cleaned


def _run_ref(run: Mapping | None) -> dict | None:
    if not run:
        return None
    return {"runId": run.get("runId"), "createdAt": run.get("createdAt")}


def build_candidates(calculators: Iterable[Mapping], run: Mapping | None,
                     verdict_rows_by_property: Mapping[str, list] | None,
                     rule_ids_by_property: Mapping[str, list] | None,
                     runs_by_property: Mapping[str, Mapping] | None = None) -> list[dict]:
    """Candidate dicts in dataPropertyIri order, one per calculator row of ``load_candidates``.

    A candidate takes its samples, its ``run {runId, createdAt}`` and ``runNewerThanCalculator`` from
    ``runs_by_property[iri]`` when present (a retired copy shown with the run it was confirmed on, D-59), else from
    ``run``. ``runNewerThanCalculator`` is False when there is no run."""
    import property_calculator_store
    import property_scripts
    from property_calculator_llm import categories_in

    verdicts = verdict_rows_by_property or {}
    rule_ids = rule_ids_by_property or {}
    per_property = runs_by_property or {}
    out: list[dict] = []
    for row in sorted(calculators, key=lambda r: r.get("dataPropertyIri") or ""):
        iri = row.get("dataPropertyIri") or ""
        used = per_property.get(iri) or run
        summary = sample_summary(run_values(used, iri) if used else [])
        retired = bool(row.get("retired"))
        source = row.get("source") or ""
        out.append({
            "dataPropertyIri": iri,
            "propertyName": property_scripts.local_name(iri),
            "function": row.get("function"),
            "source": source,
            "sha256": row.get("sha256"),
            "unit": row.get("unit"),
            "explanation": row.get("explanation"),
            "provider": row.get("provider"),
            "model": row.get("model"),
            "createdAt": row.get("createdAt"),
            "createdBy": row.get("createdBy"),
            "readCategories": categories_in(source),
            "ruleIds": sorted(rule_ids.get(iri) or []),
            "samples": summary["samples"],
            "stats": summary["stats"],
            "verdicts": verdict_counts(verdicts.get(iri)),
            "run": _run_ref(used),
            "runNewerThanCalculator": bool(
                used and property_calculator_store.created_after(used.get("createdAt"), row.get("createdAt"))),
            "retired": retired,
            "catalogueId": (row.get("catalogueId") or None) if retired else None,
        })
    return out
