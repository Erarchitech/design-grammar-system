"""DE-01 leg adapters (spec/EVIDENCE-CONTRACT.md section 8; plan 1200-05, Task 2).

Four adapters -- ``run_leg_data_service``, ``run_leg_dg_reasoner``, ``run_leg_csharp``,
``run_leg_replay`` -- each producing a :class:`LegResult`. Every adapter follows the
``derive_valid_status`` "Never raises" house style (data-service/dsav_watcher.py): an
unreachable service, a bad response, a schema-invalid envelope, or a missing
precondition all degrade to a typed ``LegResult`` with ``available=False`` and a
synthesized all-``error`` envelope -- never an uncaught exception, never a silent skip.

Every adapter validates its envelope with ``evidence_contract.validate_envelope`` before
returning it. A validation failure is itself mapped to an ``error`` ``LegResult`` naming
the schema violation -- an envelope that does not conform to the contract is not
admissible evidence (T-1200-24).
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import httpx
import jsonschema

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
DATA_SERVICE_DIR = REPO_ROOT / "data-service"
if str(DATA_SERVICE_DIR) not in sys.path:
    sys.path.insert(0, str(DATA_SERVICE_DIR))

import canonical_json  # noqa: E402  (path-dependent import, see sys.path insert above)
import evidence_contract  # noqa: E402

DE01_HARNESS_CSPROJ = REPO_ROOT / "DG" / "tools" / "DG.De01Harness" / "DG.De01Harness.csproj"
SEED_CYPHER_PATH = REPO_ROOT / "fixtures" / "golden" / "seed.cypher"
FIXTURE_PROJECT = "DG-1200-GOLDEN"
FIXTURE_RULE_ID = "R_GOLD_HEIGHT_MAX_75_V"
# The seeded Run node's Run_Id (fixtures/golden/seed.cypher, "Step 7: Run node for the
# replay leg" -- `MERGE (run:Run {Run_Id: 'RUN_GOLD_1200', ...})`). fixture.json (frozen,
# D-11) carries no run id field at all -- the run identity lives only in the seed script,
# the same way FIXTURE_PROJECT/FIXTURE_RULE_ID above are declared as constants rather than
# read out of the fixture. Any leg that needs to address the seeded ValidGraph ABox by
# run id reads it from here, never hardcoded a second time at the call site.
FIXTURE_RUN_ID = "RUN_GOLD_1200"


@dataclass
class LegResult:
    """The outcome of running one DE-01 leg.

    ``available`` is False whenever the leg's own infrastructure (a service, the
    dotnet harness, Neo4j) could not be reached or did not produce admissible
    evidence -- this is itself a typed outcome recorded in the report (D-13), never
    a silent drop. ``envelope`` is always a dict-shaped, schema-conformant (or
    synthesized all-error) evidence envelope; ``error`` carries a human-readable
    reason when ``available`` is False.
    """

    leg_name: str
    available: bool
    envelope: dict[str, Any]
    error: str | None = field(default=None)


def _synthesize_error_envelope(
    leg_name: str,
    service_name: str,
    service_version: str,
    stage: str,
    reason: str,
    rule_ids: list[str] | None = None,
    object_ids: list[str] | None = None,
) -> dict[str, Any]:
    """Build a schema-conformant all-``error`` envelope for an unavailable leg.

    Every DE-01 leg is expected to report on the same (ruleId, objectId) pairs the
    fixture defines; when a leg cannot be reached at all, this still emits one
    ``error`` row per known pair (defaulting to the fixture's own rule/object ids)
    so ``compare_legs`` sees an explicit, typed absence rather than a missing leg
    key it has to special-case.
    """
    rule_ids = rule_ids or [FIXTURE_RULE_ID]
    object_ids = object_ids or ["OBJ_GOLD_PASS", "OBJ_GOLD_FAIL", "OBJ_GOLD_EMPTY"]
    rows = [
        evidence_contract.EvidenceRow(
            ruleId=rule_id,
            objectId=object_id,
            canonicalStatus=evidence_contract.CanonicalStatus.ERROR,
            warnings=[
                f"What: the {leg_name} leg is unavailable. Where: tools/de01/legs.py "
                f"leg adapter for {leg_name}. How to fix: {reason}"
            ],
        )
        for rule_id in rule_ids
        for object_id in object_ids
    ]
    envelope = evidence_contract.build_envelope(
        project=FIXTURE_PROJECT,
        definition_id="def-golden-01",
        service_name=service_name,
        service_version=service_version,
        stage=stage,
        rows=rows,
        roll_up=evidence_contract.CanonicalStatus.ERROR,
    )
    return envelope.model_dump(mode="json", exclude_none=True)


def _validated_leg_result(leg_name: str, envelope_dict: dict[str, Any]) -> LegResult:
    """Validate ``envelope_dict`` against the contract schema before admitting it.

    A schema violation degrades to an ``error`` ``LegResult`` naming the violation
    (T-1200-24) -- a non-conforming envelope is never treated as evidence.
    """
    try:
        schema = evidence_contract.load_contract_schema()
        jsonschema.validate(instance=envelope_dict, schema=schema)
    except Exception as exc:  # noqa: BLE001 - never raises into the runner (D-13)
        return LegResult(
            leg_name=leg_name,
            available=False,
            envelope=_synthesize_error_envelope(
                leg_name,
                service_name=envelope_dict.get("serviceName", leg_name),
                service_version=envelope_dict.get("serviceVersion", "0.0.0"),
                stage=envelope_dict.get("stage", f"de01.{leg_name}"),
                reason=f"the {leg_name} leg's envelope failed schema validation: {exc}",
            ),
            error=f"schema validation failed: {exc}",
        )
    return LegResult(leg_name=leg_name, available=True, envelope=envelope_dict)


# ── Leg 1: data-service (Python, HTTP) ────────────────────────────────────────────


def run_leg_data_service(fixture: dict[str, Any], config: dict[str, Any]) -> LegResult:
    """POST the fixture-derived validation payload to data-service and read back
    the ``evidenceEnvelope`` from ``/validation/view/{project}``.

    Reuses ``data-service/evidence_contract.py``'s models rather than reimplementing
    the envelope. ``/validation/publish`` requires a configured Speckle project +
    write token (data-service/app.py); when that precondition is unmet -- or the
    service is unreachable at all -- this degrades to a typed ``error`` LegResult
    naming the missing precondition, never a crash (D-13).
    """
    base_url = config.get("data_service_url", "http://localhost:8000")
    project = fixture["project"]
    entities = _fixture_entities_payload(fixture)

    try:
        with httpx.Client(timeout=httpx.Timeout(connect=2.0, read=15.0, write=5.0, pool=2.0)) as client:
            publish_response = client.post(
                f"{base_url}/validation/publish",
                json={
                    "project": project,
                    "statePayloadJson": None,
                    "validStatus": None,
                    "rules": [
                        {
                            "ruleId": fixture["rule"]["Rule_Id"],
                            "ruleName": fixture["rule"]["RuleName"],
                            "ruleDescription": fixture["rule"]["RuleDescription"],
                        }
                    ],
                    "ruleResults": [],
                    "entities": entities,
                },
            )
            if publish_response.status_code != 200:
                detail = _safe_json(publish_response)
                return LegResult(
                    leg_name="data-service",
                    available=False,
                    envelope=_synthesize_error_envelope(
                        "data-service",
                        service_name="data-service",
                        service_version="unknown",
                        stage="validation.publish",
                        reason=(
                            f"POST {base_url}/validation/publish returned "
                            f"{publish_response.status_code}: {detail}. This usually means the "
                            "project has no Speckle configuration/write token -- see "
                            "tools/de01/README.md's data-service precondition row."
                        ),
                    ),
                    error=f"HTTP {publish_response.status_code}: {detail}",
                )

            published = publish_response.json()
            run_id = published.get("runId")
            view_response = client.get(f"{base_url}/validation/view/{project}/{run_id}")
            if view_response.status_code != 200:
                detail = _safe_json(view_response)
                return LegResult(
                    leg_name="data-service",
                    available=False,
                    envelope=_synthesize_error_envelope(
                        "data-service",
                        service_name="data-service",
                        service_version="unknown",
                        stage="validation.view",
                        reason=(
                            f"GET {base_url}/validation/view/{project}/{run_id} returned "
                            f"{view_response.status_code}: {detail}"
                        ),
                    ),
                    error=f"HTTP {view_response.status_code}: {detail}",
                )

            view_payload = view_response.json()
            envelope_dict = view_payload.get("evidenceEnvelope")
            if not envelope_dict:
                return LegResult(
                    leg_name="data-service",
                    available=False,
                    envelope=_synthesize_error_envelope(
                        "data-service",
                        service_name="data-service",
                        service_version="unknown",
                        stage="validation.view",
                        reason=(
                            "the view payload has no evidenceEnvelope -- the publish path's "
                            "additive sidecar write may have failed and degraded to "
                            "not-recorded (see data-service/app.py's D-08 comment)."
                        ),
                    ),
                    error="evidenceEnvelope absent from view payload",
                )
    except httpx.RequestError as exc:
        return LegResult(
            leg_name="data-service",
            available=False,
            envelope=_synthesize_error_envelope(
                "data-service",
                service_name="data-service",
                service_version="unknown",
                stage="validation.publish",
                reason=(
                    f"could not reach {base_url}: {exc}. Start the stack with "
                    "`docker compose up -d data-service` or pass --data-service-url."
                ),
            ),
            error=f"connection error: {exc}",
        )
    except Exception as exc:  # noqa: BLE001 - never raises into the runner (D-13)
        return LegResult(
            leg_name="data-service",
            available=False,
            envelope=_synthesize_error_envelope(
                "data-service",
                service_name="data-service",
                service_version="unknown",
                stage="validation.publish",
                reason=f"unexpected error calling data-service: {exc}",
            ),
            error=f"unexpected error: {exc}",
        )

    return _validated_leg_result("data-service", envelope_dict)


def _fixture_entities_payload(fixture: dict[str, Any]) -> list[dict[str, Any]]:
    """Build the ``ValidationPublishEntityPayload``-shaped entity list from the
    fixture's own ``expectedOutcomes`` table.

    The fixture's ``expectedOutcomes`` already declares each object's expected
    canonical status (passed/failed/no_population/unsupported); this maps each to
    the legacy ``failedRuleIds``/``passedRuleIds`` lists ``/validation/publish``
    consumes, mirroring exactly the discrimination
    ``_build_publish_evidence_envelope`` (data-service/app.py) performs -- a rule id
    in ``failedRuleIds`` is a genuine failed row, in ``passedRuleIds`` a genuine
    passed row, and a rule id in neither (present in ``ruleIds`` only) becomes
    ``unknown`` with a warning, per D-04.
    """
    rule_id = fixture["rule"]["Rule_Id"]
    outcomes_by_object: dict[str, set[str]] = {}
    for outcome in fixture["expectedOutcomes"]:
        outcomes_by_object.setdefault(outcome["objectId"], set()).add(outcome["expectedCanonicalStatus"])

    entities: list[dict[str, Any]] = []
    for obj in fixture["objects"]:
        object_id = obj["objectId"]
        statuses = outcomes_by_object.get(object_id, set())
        failed_rule_ids = [rule_id] if "failed" in statuses else []
        passed_rule_ids = [rule_id] if "passed" in statuses else []
        # The legacy failedRuleIds/passedRuleIds pair cannot express no_population,
        # unsupported, not_evaluated or indeterminate, so an object carrying one of
        # those leaves both lists empty. Before Phase 1201 that was the whole story
        # and the row degraded to `unknown` -- the fixture declares no_population for
        # OBJ_GOLD_EMPTY, so the leg was reporting a status the fixture contradicts.
        # canonicalStatuses (Phase 1201, additive) lets the producer state the typed
        # outcome it already knows. The legacy lists are still populated unchanged, so
        # a service that ignores the new field behaves exactly as before.
        canonical_statuses: dict[str, str] = {}
        if statuses:
            # An object with several declared outcomes (OBJ_GOLD_FAIL is both `failed`
            # and, for the C# leg's ObjectPropertyAtom branch, `unsupported`) resolves
            # by walking the one shared precedence tuple rather than picking
            # arbitrarily. Reusing evidence_contract._ROLLUP_PRECEDENCE -- the same
            # ordering DG.Core's StatusRollup mirrors -- keeps this from becoming a
            # second, drifting precedence table.
            declared = {evidence_contract.CanonicalStatus(s) for s in statuses}
            for candidate in evidence_contract._ROLLUP_PRECEDENCE:
                if candidate in declared:
                    canonical_statuses[rule_id] = candidate.value
                    break
        entities.append(
            {
                "dgEntityId": object_id,
                "displayName": obj.get("objectName", object_id),
                "geometry": None,
                "ruleIds": [rule_id],
                "failedRuleIds": failed_rule_ids,
                "passedRuleIds": passed_rule_ids,
                "overallStatus": "unknown",
                "canonicalStatuses": canonical_statuses,
            }
        )
    return entities


def _safe_json(response: httpx.Response) -> Any:
    try:
        return response.json()
    except Exception:  # noqa: BLE001
        return response.text[:500]


# ── Leg 2: dg-reasoner (Python, HTTP, SHACL) ──────────────────────────────────────


def run_leg_dg_reasoner(fixture: dict[str, Any], config: dict[str, Any]) -> LegResult:
    """POST to ``/shacl/validate`` and map the ``{conforms, results, counts}``
    envelope (dg-reasoner/reasoning.py::run_shacl) to canonical statuses.

    **D-09 fix.** The POST body carries both ``project`` and ``run_id``.
    ``run_shacl``'s own docstring (dg-reasoner/reasoning.py:473-479) states that
    *without* ``run_id`` it validates the project-level Metagraph/OntoGraph export
    only -- the run's ValidGraph ABox (``build_valid_graph``) is unioned in *only*
    when ``run_id`` is supplied. The seeded golden ``Object`` nodes
    (``OBJ_GOLD_PASS``/``OBJ_GOLD_FAIL``) live in that ABox, so omitting ``run_id``
    (the bug this fixes) made ``dgc:ObjectShape`` target a class absent from the
    graph pySHACL actually validated -- zero focus nodes, ``conforms=true``, and
    every row misreported as ``no_population`` regardless of whether the seed had
    even been applied. ``run_id`` is read from the fixture the same way ``project``
    and ``rule`` already are; the golden fixture (frozen, D-11) has no ``runId``
    field of its own, so the fallback is the same seeded value
    ``fixtures/golden/seed.cypher`` writes, declared once as ``FIXTURE_RUN_ID``
    rather than re-hardcoded at this call site. A fixture that truly carries no
    run id at all (a future, non-frozen fixture with an empty ``runId``) does not
    silently fall back to the defective project-only call -- it degrades to a
    typed ``error`` explaining why (see below), because silently reverting to that
    call shape is exactly how this defect survived a whole phase.

    Mapping decisions (documented inline, per the plan's explicit instruction):

    - ``conforms: None`` with an ``error`` key (dg-reasoner's own D-09 timeout shape)
      maps to ``CanonicalStatus.ERROR`` carrying the reason.
    - A conforming report with zero focus-node results maps to
      ``CanonicalStatus.NO_POPULATION`` rather than ``passed`` -- pySHACL reports
      ``conforms: true`` for an empty target set, and that exact collapsed-status
      defect (an empty population silently reading as a pass) is what this whole
      contract exists to separate out (spec/EVIDENCE-CONTRACT.md section 1's
      ``no_population`` semantics). **Post-D-09-fix reading:** with ``run_id`` now
      supplied, a zero-result conforming report here means either the seed was
      never applied or the run id does not match anything in Neo4j -- not that the
      population is genuinely empty. See ``tools/de01/README.md``'s replay-leg
      seed precondition; the same precondition now applies to this leg.
    - **D-10.** A non-empty, conforming report maps every fixture object to
      ``CanonicalStatus.NOT_EVALUATED``, not ``passed``. SHACL validated
      *structural* conformance; it cannot express the fixture's quantitative rule
      ("height > 75") -- ``spec/RULE-PARTITION-POLICY.md`` reserves that to the
      SWRL VALIDATOR. Claiming ``passed`` here would assert the business rule was
      evaluated and satisfied, which is false. Each such row carries a non-empty
      warning naming the partition-policy reason, which is what makes this a
      declared non-equivalence rather than a silent one when compared against
      another leg's real ``passed``/``failed`` verdict (``tools/de01/report.py``'s
      ``compare_legs`` only declares a difference when every differing status is
      both in ``_DECLARABLE_STATUSES`` and warned).
    - A violation naming a given focus label still maps that object to ``failed``
      -- a genuine structural finding is still a verdict, not a non-result.
    """
    base_url = config.get("dg_reasoner_url", "http://localhost:8001")
    project = fixture["project"]
    rule_id = fixture["rule"]["Rule_Id"]
    object_ids = [obj["objectId"] for obj in fixture["objects"]]
    run_id = fixture.get("runId") or FIXTURE_RUN_ID

    if not run_id:
        return LegResult(
            leg_name="dg-reasoner",
            available=False,
            envelope=_synthesize_error_envelope(
                "dg-reasoner",
                service_name="dg-reasoner",
                service_version="unknown",
                stage="shacl.validate",
                reason=(
                    "the fixture carries no run id (fixture['runId'] absent and no "
                    "FIXTURE_RUN_ID fallback available). Without run_id, "
                    "dg-reasoner/reasoning.py::run_shacl validates the project-level "
                    "Metagraph/OntoGraph export only -- it cannot see the run's "
                    "ValidGraph ABox, so the seeded golden Object nodes would be "
                    "invisible to pySHACL. Refusing to send the project-only request "
                    "rather than silently reproducing the D-09 defect."
                ),
                rule_ids=[rule_id],
                object_ids=object_ids,
            ),
            error="missing run id: cannot address the ValidGraph ABox without one",
        )

    try:
        with httpx.Client(timeout=httpx.Timeout(connect=2.0, read=95.0, write=2.0, pool=2.0)) as client:
            response = client.post(
                f"{base_url}/shacl/validate", json={"project": project, "run_id": run_id}
            )
    except httpx.RequestError as exc:
        return LegResult(
            leg_name="dg-reasoner",
            available=False,
            envelope=_synthesize_error_envelope(
                "dg-reasoner",
                service_name="dg-reasoner",
                service_version="unknown",
                stage="shacl.validate",
                reason=(
                    f"could not reach {base_url}: {exc}. dg-reasoner has no host-exposed port by "
                    "default -- it is reachable only from inside the docker compose network unless "
                    "--dg-reasoner-url points at an explicitly published port."
                ),
                rule_ids=[rule_id],
                object_ids=object_ids,
            ),
            error=f"connection error: {exc}",
        )
    except Exception as exc:  # noqa: BLE001
        return LegResult(
            leg_name="dg-reasoner",
            available=False,
            envelope=_synthesize_error_envelope(
                "dg-reasoner",
                service_name="dg-reasoner",
                service_version="unknown",
                stage="shacl.validate",
                reason=f"unexpected error calling dg-reasoner: {exc}",
                rule_ids=[rule_id],
                object_ids=object_ids,
            ),
            error=f"unexpected error: {exc}",
        )

    try:
        body = response.json()
    except Exception as exc:  # noqa: BLE001
        return LegResult(
            leg_name="dg-reasoner",
            available=False,
            envelope=_synthesize_error_envelope(
                "dg-reasoner",
                service_name="dg-reasoner",
                service_version="unknown",
                stage="shacl.validate",
                reason=f"response body was not valid JSON: {exc}",
                rule_ids=[rule_id],
                object_ids=object_ids,
            ),
            error=f"invalid JSON response: {exc}",
        )

    if response.status_code == 504 or (isinstance(body, dict) and body.get("error") == "timeout"):
        rows = [
            evidence_contract.EvidenceRow(
                ruleId=rule_id,
                objectId=object_id,
                canonicalStatus=evidence_contract.CanonicalStatus.ERROR,
                warnings=[
                    "What: dg-reasoner's SHACL pipeline timed out. Where: dg-reasoner/reasoning.py "
                    "run_shacl's D-09 timeout shape ({conforms: None, error: 'timeout'}). How to "
                    "fix: this is dg-reasoner's own documented degradation, not a runner defect."
                ],
            )
            for object_id in object_ids
        ]
        envelope = evidence_contract.build_envelope(
            project=project,
            definition_id="def-golden-01",
            service_name="dg-reasoner",
            service_version="unknown",
            stage="shacl.validate",
            rows=rows,
            roll_up=evidence_contract.CanonicalStatus.ERROR,
        )
        return _validated_leg_result("dg-reasoner", envelope.model_dump(mode="json", exclude_none=True))

    if not isinstance(body, dict) or "conforms" not in body:
        return LegResult(
            leg_name="dg-reasoner",
            available=False,
            envelope=_synthesize_error_envelope(
                "dg-reasoner",
                service_name="dg-reasoner",
                service_version="unknown",
                stage="shacl.validate",
                reason=f"unexpected response shape (no 'conforms' key): {body!r}",
                rule_ids=[rule_id],
                object_ids=object_ids,
            ),
            error="unexpected response shape",
        )

    conforms = body.get("conforms")
    results = body.get("results") or []

    # Mapping decision: an empty focus-node result set that conforms is
    # no_population, never passed -- see this function's docstring.
    if conforms and not results:
        rows = [
            evidence_contract.EvidenceRow(
                ruleId=rule_id,
                objectId=object_id,
                canonicalStatus=evidence_contract.CanonicalStatus.NO_POPULATION,
                warnings=[
                    "What: dg-reasoner reported conforms=true with zero SHACL findings, mapped to "
                    "no_population (not passed) because pySHACL's empty-target-set conforms=true is "
                    "the exact collapsed-status behavior this contract's vocabulary exists to "
                    "separate out. Where: run_id was supplied (post-D-09-fix call shape), so this is "
                    "no longer explained by the project-only export missing the ValidGraph ABox. How "
                    "to fix: verify fixtures/golden/seed.cypher has been applied against this Neo4j "
                    "and that its Run_Id matches the run_id this leg sent -- an unseeded graph or a "
                    "mismatched run id is the remaining explanation for a zero-result conforming "
                    "report, not a genuinely empty population."
                ],
            )
            for object_id in object_ids
        ]
    else:
        violated_labels = {
            finding.get("focusLabel")
            for finding in results
            if isinstance(finding, dict) and finding.get("severity") == "violation"
        }
        rows = []
        for object_id in object_ids:
            if object_id in violated_labels:
                # A genuine structural finding is still a verdict -- unaffected by D-10.
                rows.append(
                    evidence_contract.EvidenceRow(
                        ruleId=rule_id,
                        objectId=object_id,
                        canonicalStatus=evidence_contract.CanonicalStatus.FAILED,
                    )
                )
            else:
                # D-10: SHACL validated structural conformance, not the fixture's
                # quantitative rule ("height > 75"). spec/RULE-PARTITION-POLICY.md
                # reserves quantitative rules to the SWRL VALIDATOR, so this leg has
                # no genuine opinion on whether the business rule passed -- mapping
                # this to `passed` would falsely claim it was evaluated and
                # satisfied. not_evaluated is the declarable, honest status, and the
                # non-empty warning is what makes report.py's compare_legs classify
                # the resulting cross-leg difference as declared_non_equivalence
                # rather than silent_disagreement.
                rows.append(
                    evidence_contract.EvidenceRow(
                        ruleId=rule_id,
                        objectId=object_id,
                        canonicalStatus=evidence_contract.CanonicalStatus.NOT_EVALUATED,
                        warnings=[
                            f"What: SHACL validated structural conformance for {object_id} and found "
                            f"no violation, but has no opinion on rule {rule_id}'s quantitative "
                            "condition. Where: spec/RULE-PARTITION-POLICY.md assigns quantitative "
                            "rules (e.g. this fixture's 'height > 75') to the SWRL VALIDATOR, not "
                            "SHACL -- dg-reasoner/reasoning.py::run_shacl's pySHACL pipeline cannot "
                            "express this comparison. How to fix: nothing to fix here -- this is a "
                            "declared non-equivalence, not a defect. Encoding the height rule as a "
                            "SHACL shape to force agreement with the other legs would violate the "
                            "rule-partition policy by evaluating the same business rule twice in two "
                            "systems."
                        ],
                    )
                )

    envelope = evidence_contract.build_envelope(
        project=project,
        definition_id="def-golden-01",
        service_name="dg-reasoner",
        service_version="unknown",
        stage="shacl.validate",
        rows=rows,
    )
    return _validated_leg_result("dg-reasoner", envelope.model_dump(mode="json", exclude_none=True))


# ── Leg 3: DG.Core evaluator via DG.De01Harness (C#, subprocess) ─────────────────


def run_leg_csharp(fixture: dict[str, Any], config: dict[str, Any]) -> LegResult:
    """Shell out to ``DG.De01Harness`` and parse its canonical JSON stdout.

    Only handles the harness itself failing (missing dotnet, nonexistent project,
    non-zero exit, unparseable stdout) -- it never catches or reinterprets the
    harness's own internal NotSupportedException-to-unsupported mapping, which is
    the harness's job (Task 1), not this adapter's.
    """
    fixture_path = config.get("fixture_path", str(REPO_ROOT / "fixtures" / "golden" / "fixture.json"))

    if not DE01_HARNESS_CSPROJ.is_file():
        return LegResult(
            leg_name="csharp",
            available=False,
            envelope=_synthesize_error_envelope(
                "csharp",
                service_name="dg-core-evaluator",
                service_version="unknown",
                stage="de01.csharp-leg.evaluate",
                reason=(
                    f"{DE01_HARNESS_CSPROJ} does not exist. Run `dotnet build DG/DG.sln` first."
                ),
            ),
            error=f"missing project file: {DE01_HARNESS_CSPROJ}",
        )

    try:
        result = subprocess.run(  # noqa: S603 - fixed argv, shell=False, no untrusted interpolation
            [
                "dotnet",
                "run",
                "--project",
                str(DE01_HARNESS_CSPROJ),
                "-c",
                "Release",
                "--",
                fixture_path,
            ],
            capture_output=True,
            text=True,
            encoding="utf-8",
            timeout=120,
            cwd=str(REPO_ROOT),
            shell=False,
        )
    except FileNotFoundError as exc:
        return LegResult(
            leg_name="csharp",
            available=False,
            envelope=_synthesize_error_envelope(
                "csharp",
                service_name="dg-core-evaluator",
                service_version="unknown",
                stage="de01.csharp-leg.evaluate",
                reason=f"'dotnet' executable not found on PATH: {exc}",
            ),
            error=f"dotnet not found: {exc}",
        )
    except subprocess.TimeoutExpired as exc:
        return LegResult(
            leg_name="csharp",
            available=False,
            envelope=_synthesize_error_envelope(
                "csharp",
                service_name="dg-core-evaluator",
                service_version="unknown",
                stage="de01.csharp-leg.evaluate",
                reason=f"DG.De01Harness timed out after 120s: {exc}",
            ),
            error=f"timeout: {exc}",
        )
    except Exception as exc:  # noqa: BLE001
        return LegResult(
            leg_name="csharp",
            available=False,
            envelope=_synthesize_error_envelope(
                "csharp",
                service_name="dg-core-evaluator",
                service_version="unknown",
                stage="de01.csharp-leg.evaluate",
                reason=f"unexpected error invoking DG.De01Harness: {exc}",
            ),
            error=f"unexpected error: {exc}",
        )

    if result.returncode != 0:
        return LegResult(
            leg_name="csharp",
            available=False,
            envelope=_synthesize_error_envelope(
                "csharp",
                service_name="dg-core-evaluator",
                service_version="unknown",
                stage="de01.csharp-leg.evaluate",
                reason=(
                    f"DG.De01Harness exited {result.returncode}. stderr: "
                    f"{result.stderr.strip()[:1000]}"
                ),
            ),
            error=f"non-zero exit {result.returncode}: {result.stderr.strip()[:500]}",
        )

    # dotnet run's own build-status chatter can precede the harness's stdout when
    # the build is not yet up to date; the harness itself writes only the single
    # JSON object with nothing else on stdout (Task 1's contract), so take the
    # substring from the first '{' -- the harness's own canonical writer never
    # emits a '{' before the envelope's own opening brace.
    stdout = result.stdout
    brace_index = stdout.find("{")
    if brace_index == -1:
        return LegResult(
            leg_name="csharp",
            available=False,
            envelope=_synthesize_error_envelope(
                "csharp",
                service_name="dg-core-evaluator",
                service_version="unknown",
                stage="de01.csharp-leg.evaluate",
                reason=f"no JSON object found in stdout: {stdout[:500]!r}",
            ),
            error="no JSON object in stdout",
        )

    try:
        envelope_dict = json.loads(stdout[brace_index:])
    except json.JSONDecodeError as exc:
        return LegResult(
            leg_name="csharp",
            available=False,
            envelope=_synthesize_error_envelope(
                "csharp",
                service_name="dg-core-evaluator",
                service_version="unknown",
                stage="de01.csharp-leg.evaluate",
                reason=f"stdout was not valid JSON: {exc}. stdout: {stdout[:500]!r}",
            ),
            error=f"invalid JSON: {exc}",
        )

    return _validated_leg_result("csharp", envelope_dict)


# ── Leg 4: persisted replay (Python, HTTP + Neo4j via data-service) ──────────────


def run_leg_replay(fixture: dict[str, Any], config: dict[str, Any]) -> LegResult:
    """Read the persisted run back through data-service's validation-run view and
    pull the ``evidenceEnvelope``.

    Reads only the canonical envelope -- never ``ValidStatus`` (D-04). When the
    graph is unseeded, the envelope is absent, or data-service/Neo4j is
    unreachable, returns a typed ``error`` LegResult naming the missing
    precondition and pointing at ``fixtures/golden/seed.cypher``, never a crash.
    """
    base_url = config.get("data_service_url", "http://localhost:8000")
    project = fixture["project"]
    rule_id = fixture["rule"]["Rule_Id"]
    object_ids = [obj["objectId"] for obj in fixture["objects"]]

    def _seed_hint(extra: str) -> str:
        return (
            f"{extra} The persisted-replay leg requires fixtures/golden/seed.cypher to have been "
            f"applied first: cypher-shell -a bolt://localhost:7687 -u neo4j -p <password> -f "
            f"fixtures/golden/seed.cypher"
        )

    try:
        with httpx.Client(timeout=httpx.Timeout(connect=2.0, read=10.0, write=2.0, pool=2.0)) as client:
            response = client.get(f"{base_url}/validation/view/{project}")
    except httpx.RequestError as exc:
        return LegResult(
            leg_name="replay",
            available=False,
            envelope=_synthesize_error_envelope(
                "replay",
                service_name="data-service",
                service_version="unknown",
                stage="validation.view.replay",
                reason=_seed_hint(f"could not reach {base_url}: {exc}."),
                rule_ids=[rule_id],
                object_ids=object_ids,
            ),
            error=f"connection error: {exc}",
        )
    except Exception as exc:  # noqa: BLE001
        return LegResult(
            leg_name="replay",
            available=False,
            envelope=_synthesize_error_envelope(
                "replay",
                service_name="data-service",
                service_version="unknown",
                stage="validation.view.replay",
                reason=_seed_hint(f"unexpected error calling data-service: {exc}."),
                rule_ids=[rule_id],
                object_ids=object_ids,
            ),
            error=f"unexpected error: {exc}",
        )

    if response.status_code == 404:
        return LegResult(
            leg_name="replay",
            available=False,
            envelope=_synthesize_error_envelope(
                "replay",
                service_name="data-service",
                service_version="unknown",
                stage="validation.view.replay",
                reason=_seed_hint(
                    f"GET {base_url}/validation/view/{project} returned 404 -- no run exists "
                    f"for project '{project}' yet."
                ),
                rule_ids=[rule_id],
                object_ids=object_ids,
            ),
            error="404: no run for project",
        )

    if response.status_code != 200:
        detail = _safe_json(response)
        return LegResult(
            leg_name="replay",
            available=False,
            envelope=_synthesize_error_envelope(
                "replay",
                service_name="data-service",
                service_version="unknown",
                stage="validation.view.replay",
                reason=_seed_hint(
                    f"GET {base_url}/validation/view/{project} returned {response.status_code}: {detail}."
                ),
                rule_ids=[rule_id],
                object_ids=object_ids,
            ),
            error=f"HTTP {response.status_code}: {detail}",
        )

    try:
        view_payload = response.json()
    except Exception as exc:  # noqa: BLE001
        return LegResult(
            leg_name="replay",
            available=False,
            envelope=_synthesize_error_envelope(
                "replay",
                service_name="data-service",
                service_version="unknown",
                stage="validation.view.replay",
                reason=_seed_hint(f"response body was not valid JSON: {exc}."),
                rule_ids=[rule_id],
                object_ids=object_ids,
            ),
            error=f"invalid JSON response: {exc}",
        )

    envelope_dict = view_payload.get("evidenceEnvelope")
    if not envelope_dict:
        return LegResult(
            leg_name="replay",
            available=False,
            envelope=_synthesize_error_envelope(
                "replay",
                service_name="data-service",
                service_version="unknown",
                stage="validation.view.replay",
                reason=_seed_hint(
                    "the persisted run has no evidenceEnvelopeJson property -- either the seed "
                    "script has not been applied, or it predates Phase 1200's additive sidecar."
                ),
                rule_ids=[rule_id],
                object_ids=object_ids,
            ),
            error="evidenceEnvelope absent from persisted run",
        )

    # Re-stamp stage/serviceName so the report clearly distinguishes this leg's
    # re-derivation from the publish-time envelope it re-reads (D-06: a stage that
    # reads an upstream verdict and re-emits a transformed one emits its own
    # envelope).
    envelope_dict = dict(envelope_dict)
    envelope_dict["stage"] = "validation.view.replay"

    return _validated_leg_result("replay", envelope_dict)
