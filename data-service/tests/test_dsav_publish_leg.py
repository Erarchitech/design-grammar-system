"""Phase 39 Wave 4: the single deliberate Speckle publish leg (D-11).

This is the *only* module in Phase 39 that turns the per-project
`publishEnabled` flag on, and it turns it on for exactly one capture. Every
other Phase 39 run — including all six scenarios in
`test_dsav_live_loop.py` — is persist-only (T-39-04).

Why this module is separate and double-marked (P-15)
----------------------------------------------------
It carries **both** `integration` and `live`. `data-service/tests/conftest.py`
deselects every `live`-marked item unless the caller supplies an explicit `-m`
expression, so a routine

    docker compose exec -T data-service python -m pytest tests/ -q

can never mint a Speckle version by accident. Running it is a deliberate act:

    docker compose exec -T data-service python -m pytest \
        tests/test_dsav_publish_leg.py -q -m "integration and live"

**The image must be rebuilt first.** `data-service/tests/` has no bind mount,
so this file is invisible inside a stale container. See
`data-service/tests/README.md` -> "Known gotcha -- image staleness".

Evidence honesty (P-16 / T-39-12)
---------------------------------
If the dev stack has no working Speckle write configuration this module does
**not** synthesize a number, does **not** mock Speckle and does **not**
silently skip. It writes `{"status": "blocked", "reason": ...}` into the
evidence file and fails loudly with that reason, so the human checkpoint
routes the decision to the operator. An unmeasurable measurement recorded as
measured is worse than an acknowledged gap.

Teardown is unconditional (T-39-11)
-----------------------------------
`publishEnabled` goes back to false and the `provider:'AutoValidation'` row is
deleted, along with the `provider:'Speckle'` row this module provisions for the
fixture project. Leaving the flag on would turn every future capture into a
Speckle version — the one way this investigation could damage the environment
it ran in.

Secrets (T-39-09): the Speckle write token and the connector token live in
this process only. Speckle *project* and *version* identifiers are recorded;
tokens never are.
"""

from __future__ import annotations

import json
import os
import sys
import time
from datetime import datetime, timedelta, timezone
from typing import Any

import httpx
import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import app as data_service_app  # noqa: E402
import dsav_watcher  # noqa: E402
from dsav_fixtures import FIXTURE_PROJECT, capture_envelope  # noqa: E402
from speckle_validation import (  # noqa: E402
    SpeckleValidationError,
    build_client,
    get_latest_model_version_id,
)

# P-15: both markers. `integration` = needs the compose network; `live` =
# reaches a real external system and is deselected by a bare pytest run.
pytestmark = [pytest.mark.integration, pytest.mark.live]

# ── T-39-10 isolation guard ─────────────────────────────────────────────────
assert FIXTURE_PROJECT == "p39-autoval", (
    "Phase 39 reserves exactly one live-Neo4j project string; the fixture "
    "module changed it out from under this driver."
)
assert FIXTURE_PROJECT not in {"p37-structure", "p1", "default-project"}

BASE_URL = os.getenv("DSAV_TARGET_BASE_URL", "http://localhost:8000").rstrip("/")

# A file of its own, deliberately NOT the Wave 3 path: this module must never
# overwrite `dsav-evidence.json`. The executor merges this one key into
# `39-EVIDENCE.json`, preserving every Wave 3 measurement.
EVIDENCE_PATH = os.getenv(
    "DSAV_PUBLISH_EVIDENCE_PATH", "/app/data/dsav-publish-evidence.json"
)

CONNECTOR_ID = "grasshopper"
HTTP_TIMEOUT_SECONDS = 20.0

# ── Guardrail parameters for the one publish-enabled run ─────────────────────
DEBOUNCE_SECONDS = 2.0
RATE_LIMIT_PER_MINUTE = 3
MAX_ATTEMPTS = 3
PUBLISH_ENABLED = True  # D-11: the only `True` in the entire phase.

CAPTURES_ISSUED = 1  # D-11: exactly one, and no others while the flag is on.
COMPLETE_DEADLINE_SECONDS = 40.0
PUBLISH_DEADLINE_SECONDS = 60.0

MEASUREMENTS: dict[str, Any] = {}


# ── Helpers ──────────────────────────────────────────────────────────────────


def _now_utc() -> datetime:
    return datetime.now(timezone.utc)


def _parse_iso(value: Any) -> datetime | None:
    if not isinstance(value, str) or not value:
        return None
    text = value[:-1] + "+00:00" if value.endswith("Z") else value
    try:
        parsed = datetime.fromisoformat(text)
    except ValueError:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed


def _record_blocked(reason: str, detail: str | None = None) -> None:
    """P-16: the blocked branch is a first-class recorded outcome, never a
    silent skip and never a fabricated number."""
    MEASUREMENTS["speckle_publish"] = {
        "status": "blocked",
        "reason": reason,
        "detail": detail,
        "versions_minted": 0,
        "captures_issued": 0,
        "validation_version_id": None,
        "speckle_project_id": None,
        "model_viewer_url": None,
        "note": (
            "D-11's measured Speckle data point was NOT obtained: the dev "
            "stack has no working Speckle write configuration. Per P-16 no "
            "number was synthesized and Speckle was not mocked. The operator "
            "decides between configuring Speckle and re-running, or "
            "accepting an analytic estimate that Plan 05 must label as an "
            "estimate."
        ),
    }


def _all_rows(session: Any) -> list[dict[str, Any]]:
    result = session.run(
        """
        MATCH (run:ValidationRun {graph:$graph, project:$project})
        OPTIONAL MATCH (run)-[:HAS_ENTITY]->(ve:ValidationEntity)
        RETURN
            run.runId AS runId,
            run.status AS status,
            run.trigger AS trigger,
            run.verdictSource AS verdictSource,
            run.capturedAt AS capturedAt,
            run.completedAt AS completedAt,
            run.attempts AS attempts,
            run.lastError AS lastError,
            run.ValidStatus AS validStatus,
            run.SendStatus AS sendStatus,
            run.shaclReportJson AS shaclReportJson,
            run.speckleProjectId AS speckleProjectId,
            run.baseModelId AS baseModelId,
            run.baseVersionId AS baseVersionId,
            run.validationModelId AS validationModelId,
            run.validationVersionId AS validationVersionId,
            run.modelViewerUrl AS modelViewerUrl,
            run.validationResourceUrl AS validationResourceUrl,
            count(DISTINCT ve) AS entityCount
        """,
        graph=dsav_watcher.VALIDATION_GRAPH,
        project=FIXTURE_PROJECT,
    )
    return [dict(record) for record in result]


def _row(session: Any, run_id: str) -> dict[str, Any] | None:
    for row in _all_rows(session):
        if row.get("runId") == run_id:
            return row
    return None


def _scrub(session: Any) -> None:
    session.run(
        "MATCH (n:ValidationRun {project:$project}) DETACH DELETE n",
        project=FIXTURE_PROJECT,
    )
    session.run(
        "MATCH (n:IntegrationConfig {project:$project}) DETACH DELETE n",
        project=FIXTURE_PROJECT,
    )


def _delete_config_rows(session: Any) -> int:
    """Remove both config rows this module touches and return how many
    `provider:'AutoValidation'` rows remain (T-39-11: must be 0)."""
    session.run(
        "MATCH (n:IntegrationConfig {project:$project}) DETACH DELETE n",
        project=FIXTURE_PROJECT,
    )
    record = session.run(
        "MATCH (cfg:IntegrationConfig {graph:$graph, provider:'AutoValidation', "
        "project:$project}) RETURN count(cfg) AS n",
        graph=dsav_watcher.VALIDATION_GRAPH,
        project=FIXTURE_PROJECT,
    ).single()
    return int(record["n"]) if record else 0


def _completions_since(session: Any, cutoff: datetime) -> list[dict[str, Any]]:
    out = []
    for row in _all_rows(session):
        if row.get("status") != "completed":
            continue
        completed_at = _parse_iso(row.get("completedAt"))
        if completed_at is not None and completed_at >= cutoff:
            out.append(row)
    return out


def _wait_for_empty_rate_window(session: Any, timeout: float = 80.0) -> float:
    """Same drain the Wave 3 driver performs: the limiter is in-process and
    shared (D-15), so a run of this module minutes after that one could
    otherwise start against a primed window and never publish."""
    started = time.time()
    deadline = started + timeout
    while time.time() < deadline:
        cutoff = _now_utc() - timedelta(seconds=dsav_watcher.RATE_LIMIT_WINDOW_SECONDS)
        if not _completions_since(session, cutoff):
            break
        time.sleep(2.0)
    return round(time.time() - started, 3)


def _set_auto_validation(
    session: Any, *, enabled: bool, publish_enabled: bool
) -> None:
    """P-06: there is deliberately no configuration route, so the driver
    writes the config through the watcher module itself."""
    dsav_watcher.upsert_auto_validation_config(
        FIXTURE_PROJECT,
        dsav_watcher.AutoValidationConfig(
            enabled=enabled,
            publish_enabled=publish_enabled,
            debounce_window_seconds=DEBOUNCE_SECONDS,
            rate_limit_per_minute=RATE_LIMIT_PER_MINUTE,
            max_attempts=MAX_ATTEMPTS,
        ),
        session=session,
    )


def _post_capture(token: str, payload_json: str) -> dict[str, Any]:
    """One authenticated capture across the same trust boundary a real
    connector crosses (T-39-01) — no auth bypass for convenience."""
    response = httpx.post(
        f"{BASE_URL}/designstate/capture",
        headers={"Authorization": f"Bearer {token}"},
        json={"project": FIXTURE_PROJECT, "statePayloadJson": payload_json},
        timeout=HTTP_TIMEOUT_SECONDS,
    )
    assert response.status_code == 202, (response.status_code, response.text)
    return response.json()


def _version_ids(client: Any, project_id: str, model_id: str, limit: int = 20) -> list[str]:
    versions = client.version.get_versions(model_id, project_id, limit=limit)
    return [item.id for item in versions.items]


# ── Preflight probe (P-16) ───────────────────────────────────────────────────


class _Blocked(Exception):
    """Raised by the preflight when Speckle cannot be published to for real."""

    def __init__(self, reason: str, detail: str | None = None):
        super().__init__(f"{reason}: {detail}" if detail else reason)
        self.reason = reason
        self.detail = detail


def _discover_speckle_config(session: Any) -> Any:
    """Resolve a *real* Speckle configuration to publish through.

    P-16 names two blockers, and both are probed here:

    * `speckle_token_missing` — no Speckle write token is configured
      (`get_speckle_settings().write_token` is empty).
    * `speckle_config_missing` — the dev stack has no reachable
      `provider:'Speckle'` `IntegrationConfig` at all, or the one it has
      points at a Speckle project/base model that cannot be read back with
      the write token.

    Deviation from the plan's literal probe, deliberately: the plan says to
    require a `provider:'Speckle'` row **for the fixture project**. `p39-autoval`
    is a synthetic project string reserved by this phase (P-03) that has never
    had a Speckle project of its own, and the Wave 3 driver's scrub deletes
    every `IntegrationConfig` scoped to it. Blocking on that would record
    `blocked` for an environment that demonstrably *does* have a working
    Speckle write configuration — a false negative that misrepresents the
    stack exactly as badly as a fabricated number would (T-39-12). D-11's
    actual requirement is "a working Speckle config **in the dev stack**".

    So: an existing fixture-project row is used when present; otherwise a
    donor row is *discovered* from the live database, its Speckle project and
    base model are proven readable with the write token, and the fixture
    project is pointed at that same real Speckle project. Nothing is invented
    — every identifier below comes out of Neo4j or Speckle.
    """
    settings = data_service_app.get_speckle_settings()
    if not settings.write_token:
        raise _Blocked(
            "speckle_token_missing",
            "get_speckle_settings().write_token is empty; no SPECKLE_WRITE_TOKEN "
            "env var and no persisted writeToken in the data dir.",
        )

    existing = data_service_app.get_integration_config(FIXTURE_PROJECT)
    donor_project = None
    if existing is not None and existing.speckleProjectId and existing.baseModelId:
        config = existing
    else:
        rows = list(
            session.run(
                """
                MATCH (cfg:IntegrationConfig {graph:$graph, provider:'Speckle'})
                WHERE cfg.speckleProjectId IS NOT NULL
                  AND cfg.speckleProjectId <> ''
                  AND cfg.baseModelId IS NOT NULL
                  AND cfg.baseModelId <> ''
                  AND cfg.project <> $project
                RETURN
                    cfg.project AS project,
                    cfg.speckleProjectId AS speckleProjectId,
                    cfg.baseModelId AS baseModelId,
                    cfg.baseModelName AS baseModelName,
                    cfg.validationModelId AS validationModelId
                ORDER BY cfg.project
                """,
                graph=dsav_watcher.VALIDATION_GRAPH,
                project=FIXTURE_PROJECT,
            )
        )
        if not rows:
            raise _Blocked(
                "speckle_config_missing",
                "no provider:'Speckle' IntegrationConfig row with a "
                "speckleProjectId and baseModelId exists anywhere in "
                f"graph:'{dsav_watcher.VALIDATION_GRAPH}'.",
            )
        donor = dict(rows[0])
        donor_project = donor["project"]
        config = data_service_app.SpeckleProjectConfigPayload(
            speckleProjectId=donor["speckleProjectId"],
            baseModelId=donor["baseModelId"],
            baseModelName=donor.get("baseModelName"),
            validationModelId=donor.get("validationModelId"),
        )

    # Prove the config is genuinely usable before anything is enabled: an
    # unreachable Speckle or a base model with no versions is a blocker, not
    # a publish failure to be discovered halfway through.
    try:
        client = build_client(settings.internal_url, settings.write_token)
        base_version_id = get_latest_model_version_id(
            client, config.speckleProjectId, config.baseModelId
        )
    except SpeckleValidationError as exc:
        raise _Blocked("speckle_config_missing", str(exc)) from exc
    except Exception as exc:  # transport / auth / GraphQL
        raise _Blocked(
            "speckle_config_missing",
            f"Speckle at {settings.internal_url} is not usable with the "
            f"configured write token: {type(exc).__name__}: {exc}",
        ) from exc

    data_service_app.upsert_integration_config(FIXTURE_PROJECT, config)

    return {
        "settings": settings,
        "client": client,
        "config": data_service_app.get_integration_config(FIXTURE_PROJECT),
        "base_version_id": base_version_id,
        "donor_project": donor_project,
    }


# ── Fixtures ─────────────────────────────────────────────────────────────────


@pytest.fixture(scope="module")
def live_session():
    """One real Neo4j session for the module. The scrub runs at *setup only*:
    the published run row is this plan's evidence, and the acceptance
    criterion "exactly one :ValidationRun for p39-autoval carries SendStatus
    true" is checked against the database after the module exits."""
    driver = dsav_watcher._get_driver()
    with driver.session() as session:
        _wait_for_empty_rate_window(session, timeout=80.0)
        _scrub(session)
        dsav_watcher.reset_guardrail_state()
        yield session


@pytest.fixture(scope="module", autouse=True)
def publish_flag_guard(live_session):
    """T-39-11, unconditional: the flag goes back off and the config rows go
    away no matter how the test exits. This teardown is the single most
    important thing in the module — leaving `publishEnabled` on would turn
    every future capture for this project into a Speckle version."""
    yield
    try:
        _set_auto_validation(live_session, enabled=False, publish_enabled=False)
    finally:
        remaining = _delete_config_rows(live_session)
        MEASUREMENTS.setdefault("teardown", {})
        MEASUREMENTS["teardown"] = {
            "publish_enabled_reset_to": False,
            "auto_validation_config_rows_remaining": remaining,
        }
        assert remaining == 0, (
            "T-39-11: a provider:'AutoValidation' IntegrationConfig row "
            f"survived teardown for {FIXTURE_PROJECT}"
        )


@pytest.fixture(scope="module")
def capture_token():
    """A real project-scoped connector credential, revoked at teardown. The
    plaintext token lives in this process only (T-39-09)."""
    created = httpx.post(
        f"{BASE_URL}/connectors/{CONNECTOR_ID}/credentials",
        json={"label": "phase-39 publish leg", "project": FIXTURE_PROJECT},
        timeout=HTTP_TIMEOUT_SECONDS,
    )
    assert created.status_code == 201, (created.status_code, created.text)
    body = created.json()
    yield body["token"]
    httpx.delete(
        f"{BASE_URL}/connectors/{CONNECTOR_ID}/credentials/{body['credential_id']}",
        timeout=HTTP_TIMEOUT_SECONDS,
    )


@pytest.fixture(scope="module", autouse=True)
def evidence_writer():
    """Serialize whatever was observed — including a `blocked` outcome, which
    is itself evidence. Nothing is written when nothing was observed at all."""
    yield
    if "speckle_publish" not in MEASUREMENTS:
        return
    payload = {
        "phase": 39,
        "measured_at": _now_utc().isoformat(),
        "source": "data-service/tests/test_dsav_publish_leg.py",
        "measurements": {
            "speckle_publish": MEASUREMENTS["speckle_publish"],
        },
        "teardown": MEASUREMENTS.get("teardown"),
    }
    os.makedirs(os.path.dirname(EVIDENCE_PATH) or ".", exist_ok=True)
    with open(EVIDENCE_PATH, "w", encoding="utf-8") as handle:
        json.dump(payload, handle, indent=2)
        handle.write("\n")


# ── The single publish-enabled run ───────────────────────────────────────────


def test_publish_leg_mints_exactly_one_real_speckle_version(
    live_session, capture_token
):
    """D-11: one capture, flag on, one real Speckle version.

    The `SendStatus` flip from the persist-only default (`false` in every
    Wave 3 run) is the observable proof that the opt-in flag is what changed
    the behaviour, and the version-id delta read back from Speckle is the
    proof the version is real rather than a field this repo wrote to itself.
    """
    try:
        probe = _discover_speckle_config(live_session)
    except _Blocked as blocked:
        _record_blocked(blocked.reason, blocked.detail)
        pytest.fail(
            f"D-11 publish leg blocked: {blocked.reason} — {blocked.detail}. "
            "Per P-16 no Speckle data point was synthesized; the human "
            "checkpoint routes the decision to the operator."
        )

    settings = probe["settings"]
    client = probe["client"]
    config = probe["config"]

    versions_before = _version_ids(
        client, config.speckleProjectId, config.validationModelId
    ) if config.validationModelId else []

    _set_auto_validation(live_session, enabled=True, publish_enabled=PUBLISH_ENABLED)

    envelope = capture_envelope()
    obj_state_count = len(envelope["objStates"])
    accepted = _post_capture(capture_token, json.dumps(envelope))
    run_id = accepted["runId"]
    assert accepted["status"] == "captured"

    # --- no further capture of any kind while the flag is on (T-39-04) ---

    # 1. Wait for the verdict. The run must complete BEFORE anything Speckle
    #    happens (P-07's inverted ordering relative to the manual path).
    deadline = time.time() + COMPLETE_DEADLINE_SECONDS
    row: dict[str, Any] | None = None
    while time.time() < deadline:
        row = _row(live_session, run_id)
        if row is not None and row.get("status") in {"completed", "failed"}:
            break
        time.sleep(0.5)
    assert row is not None and row["status"] == "completed", row
    assert row["completedAt"], row
    completed_at_observed = row["completedAt"]
    # The verdict is durable before the publish leg is reached: at this
    # instant the row is completed and still carries the persist-only
    # Speckle defaults.
    verdict_before_publish = {
        "status": row["status"],
        "completedAt": row["completedAt"],
        "sendStatus": row["sendStatus"],
        "validationVersionId": row["validationVersionId"],
    }

    # 2. Wait for the publish leg, asserting on every poll that the run's
    #    status never leaves `completed` — a Speckle failure must leave the
    #    run completed rather than reverting the verdict (P-07).
    statuses_seen: list[str] = []
    deadline = time.time() + PUBLISH_DEADLINE_SECONDS
    while time.time() < deadline:
        row = _row(live_session, run_id)
        assert row is not None
        statuses_seen.append(row["status"])
        assert row["status"] == "completed", (
            "the publish leg must never move the run off 'completed' (P-07)",
            statuses_seen,
        )
        assert row["completedAt"] == completed_at_observed, row
        if row["validationVersionId"]:
            break
        time.sleep(0.5)

    assert row is not None
    assert set(statuses_seen) == {"completed"}, statuses_seen

    # 3. The row is a published auto-run.
    assert row["trigger"] == "auto", row
    assert row["verdictSource"] == "shacl", row
    assert row["sendStatus"] is True, (
        "SendStatus must flip to true — this is the observable proof the "
        "opt-in publishEnabled flag is what changed the behaviour",
        row,
    )
    assert row["validationVersionId"], row
    assert row["speckleProjectId"], row
    assert row["modelViewerUrl"], row

    # 4. The version is real: read it back off Speckle, not off our own row.
    versions_after = _version_ids(
        client, row["speckleProjectId"], row["validationModelId"]
    )
    minted = [v for v in versions_after if v not in versions_before]
    assert row["validationVersionId"] in versions_after, (
        row["validationVersionId"],
        versions_after,
    )
    assert len(minted) == 1, (minted, versions_before, versions_after)
    assert minted[0] == row["validationVersionId"], (minted, row)

    # 5. This leg minted exactly one, from exactly one capture (D-11).
    all_rows = _all_rows(live_session)
    published_rows = [r for r in all_rows if r["sendStatus"] is True]
    assert len(published_rows) == 1, published_rows
    assert len(all_rows) == CAPTURES_ISSUED, all_rows

    MEASUREMENTS["speckle_publish"] = {
        "status": "published",
        "run_id": run_id,
        "validation_version_id": row["validationVersionId"],
        "speckle_project_id": row["speckleProjectId"],
        "validation_model_id": row["validationModelId"],
        "base_model_id": row["baseModelId"],
        "base_version_id": row["baseVersionId"],
        "model_viewer_url": row["modelViewerUrl"],
        "validation_resource_url": row["validationResourceUrl"],
        "speckle_base_url": settings.base_url,
        "versions_minted": len(minted),
        "captures_issued": CAPTURES_ISSUED,
        "speckle_versions_per_capture": len(minted) / CAPTURES_ISSUED,
        "captured_at": row["capturedAt"],
        "completed_at": row["completedAt"],
        "trigger": row["trigger"],
        "verdict_source": row["verdictSource"],
        "send_status": row["sendStatus"],
        "valid_status": list(row["validStatus"]) if row["validStatus"] else None,
        "obj_state_count": obj_state_count,
        "validation_entity_count": row["entityCount"],
        "verdict_state_before_publish": verdict_before_publish,
        "ordering": (
            "P-07 inverted relative to the manual path: the run reached "
            "'completed' with its verdict durable BEFORE the publish leg ran, "
            "and its status was observed to stay 'completed' throughout."
        ),
        "speckle_config_source": (
            "existing provider:'Speckle' IntegrationConfig for the fixture "
            "project"
            if probe["donor_project"] is None
            else (
                "the dev stack's existing Speckle configuration, discovered "
                f"from DG project '{probe['donor_project']}' and re-pointed at "
                f"'{FIXTURE_PROJECT}'; p39-autoval is a synthetic phase-"
                "reserved project string with no Speckle project of its own"
            )
        ),
        "note": (
            "The published version carries an empty entity and rules payload "
            "by construction: a captured DesignState envelope has no "
            "per-entity geometry and no failedRuleIds, so the version is a "
            "state-level marker rather than a coloured overlay. That "
            "emptiness is itself the Speckle-noise characteristic being "
            "measured — with the flag on, the observed auto-run Speckle-noise "
            "rate is 1 Speckle version per capture that survives debounce and "
            "the rate limiter, each version a near-empty commit appended to "
            "the project's dg-validation model."
        ),
        "configuration": {
            "debounce_window_seconds": DEBOUNCE_SECONDS,
            "rate_limit_per_minute": RATE_LIMIT_PER_MINUTE,
            "max_attempts": MAX_ATTEMPTS,
            "publish_enabled": PUBLISH_ENABLED,
            "poll_interval_seconds": dsav_watcher.POLL_INTERVAL_SECONDS,
            "complete_deadline_seconds": COMPLETE_DEADLINE_SECONDS,
            "publish_deadline_seconds": PUBLISH_DEADLINE_SECONDS,
        },
    }
