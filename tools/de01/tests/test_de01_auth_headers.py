"""D-20 tests: the DE-01 host-runner connector-token path (plan 1205-04, Task 1).

Covers ``legs.data_service_auth_headers()`` in isolation, its use on the two HTTP
legs it is wired into (``run_leg_data_service`` and ``run_leg_replay``), its use on
``run_de01_repeat.py``'s pinned-replay GET, and the no-leak property: a full
``run_repeat`` report built with a fake token configured never contains that token
anywhere in its serialised JSON or Markdown.

No live stack: every HTTP call is served by a recording ``httpx.Client`` stand-in,
following ``tools/de01/tests/test_repeat_runner.py``'s ``_RecordingHttpxClient``
pattern (bootstrap + monkeypatched client, never a real socket).
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent.parent.parent
TOOLS_DE01_DIR = REPO_ROOT / "tools" / "de01"
if str(TOOLS_DE01_DIR) not in sys.path:
    sys.path.insert(0, str(TOOLS_DE01_DIR))

import legs  # noqa: E402
import run_de01_repeat  # noqa: E402

FAKE_TOKEN = "dgc_FAKE_TOKEN_FOR_TEST_ONLY_1205_04"


def _clear_token_env(monkeypatch) -> None:
    monkeypatch.delenv("DG_DE01_CONNECTOR_TOKEN", raising=False)
    monkeypatch.delenv("DG_DE01_CONNECTOR_TOKEN_FILE", raising=False)


# ── data_service_auth_headers() in isolation ──────────────────────────────────────


class TestDataServiceAuthHeaders:
    def test_env_var_set_returns_bearer_header(self, monkeypatch):
        _clear_token_env(monkeypatch)
        monkeypatch.setenv("DG_DE01_CONNECTOR_TOKEN", FAKE_TOKEN)
        assert legs.data_service_auth_headers() == {"Authorization": f"Bearer {FAKE_TOKEN}"}

    def test_env_var_unset_falls_back_to_token_file(self, monkeypatch, tmp_path):
        _clear_token_env(monkeypatch)
        token_file = tmp_path / "connector-token"
        token_file.write_text(f"{FAKE_TOKEN}\n", encoding="utf-8")
        monkeypatch.setenv("DG_DE01_CONNECTOR_TOKEN_FILE", str(token_file))
        assert legs.data_service_auth_headers() == {"Authorization": f"Bearer {FAKE_TOKEN}"}

    def test_token_file_first_non_empty_line_is_stripped(self, monkeypatch, tmp_path):
        _clear_token_env(monkeypatch)
        token_file = tmp_path / "connector-token"
        token_file.write_text(f"\n  {FAKE_TOKEN}  \nsecond-line-ignored\n", encoding="utf-8")
        monkeypatch.setenv("DG_DE01_CONNECTOR_TOKEN_FILE", str(token_file))
        assert legs.data_service_auth_headers() == {"Authorization": f"Bearer {FAKE_TOKEN}"}

    def test_blank_env_var_falls_back_to_file(self, monkeypatch, tmp_path):
        """An empty-string env var is treated as unset, not as a blank token."""
        _clear_token_env(monkeypatch)
        monkeypatch.setenv("DG_DE01_CONNECTOR_TOKEN", "")
        token_file = tmp_path / "connector-token"
        token_file.write_text(f"{FAKE_TOKEN}\n", encoding="utf-8")
        monkeypatch.setenv("DG_DE01_CONNECTOR_TOKEN_FILE", str(token_file))
        assert legs.data_service_auth_headers() == {"Authorization": f"Bearer {FAKE_TOKEN}"}

    def test_neither_env_nor_file_returns_empty_dict(self, monkeypatch, tmp_path):
        _clear_token_env(monkeypatch)
        # Point the file lookup at a path that does not exist, so this test never
        # depends on the real .de01/connector-token being absent on the host.
        monkeypatch.setenv("DG_DE01_CONNECTOR_TOKEN_FILE", str(tmp_path / "does-not-exist"))
        assert legs.data_service_auth_headers() == {}

    def test_default_token_file_path_is_gitignored_de01_dir(self):
        assert legs.DEFAULT_CONNECTOR_TOKEN_FILE == legs.REPO_ROOT / ".de01" / "connector-token"

    def test_empty_token_file_returns_empty_dict(self, monkeypatch, tmp_path):
        _clear_token_env(monkeypatch)
        token_file = tmp_path / "connector-token"
        token_file.write_text("\n\n   \n", encoding="utf-8")
        monkeypatch.setenv("DG_DE01_CONNECTOR_TOKEN_FILE", str(token_file))
        assert legs.data_service_auth_headers() == {}


# ── Recording httpx.Client stand-in (mirrors test_repeat_runner.py) ───────────────


class _FakeResponse:
    def __init__(self, status_code: int, payload: dict | None = None):
        self.status_code = status_code
        self._payload = payload or {}

    def json(self):
        return self._payload

    @property
    def text(self):
        return json.dumps(self._payload)


class _RecordingHttpxClient:
    """Records constructor ``headers`` and every request URL; serves canned responses.

    ``responses`` maps ``(method, url)`` to a ``_FakeResponse``; a request whose
    exact URL is not present in the map returns a 404 so a test omission fails
    loudly rather than silently succeeding.
    """

    instances: list["_RecordingHttpxClient"] = []
    responses: dict[tuple[str, str], "_FakeResponse"] = {}

    def __init__(self, *args, **kwargs):
        self.headers = kwargs.get("headers")
        self.calls: list[tuple[str, str]] = []
        type(self).instances.append(self)

    def __enter__(self):
        return self

    def __exit__(self, *exc_info):
        return False

    def get(self, url: str, **kwargs):
        self.calls.append(("GET", url))
        return type(self).responses.get(("GET", url), _FakeResponse(404, {}))

    def post(self, url: str, **kwargs):
        self.calls.append(("POST", url))
        return type(self).responses.get(("POST", url), _FakeResponse(404, {}))


def _envelope(rows: list[dict], service_name: str = "svc", stage: str = "test") -> dict:
    return {
        "contractVersion": "1.0.0",
        "canonicalizationVersion": 1,
        "project": "DG-1200-GOLDEN",
        "definitionId": "def-golden-01",
        "serviceName": service_name,
        "serviceVersion": "1.0.0",
        "emittedAt": "2026-09-20T00:00:00Z",
        "stage": stage,
        "canonicalStatus": rows[0]["canonicalStatus"] if rows else "not_evaluated",
        "rows": rows,
    }


def _row(rule_id: str, object_id: str, status: str) -> dict:
    return {"ruleId": rule_id, "objectId": object_id, "canonicalStatus": status}


def _fixture() -> dict:
    return {
        "project": "DG-1200-GOLDEN",
        "rule": {
            "Rule_Id": "R_GOLD_HEIGHT_MAX_75_V",
            "RuleName": "height-max-75",
            "RuleDescription": "max height 75",
        },
        "objects": [{"objectId": "OBJ_GOLD_PASS", "objectName": "OBJ_GOLD_PASS"}],
        "expectedOutcomes": [
            {"objectId": "OBJ_GOLD_PASS", "expectedCanonicalStatus": "passed"},
        ],
    }


class TestDataServiceLegSendsHeaders:
    def setup_method(self):
        _RecordingHttpxClient.instances = []
        _RecordingHttpxClient.responses = {}

    def test_headers_sent_when_token_configured(self, monkeypatch):
        _clear_token_env(monkeypatch)
        monkeypatch.setenv("DG_DE01_CONNECTOR_TOKEN", FAKE_TOKEN)
        monkeypatch.setattr(legs, "httpx", legs.httpx)  # keep module reference
        monkeypatch.setattr(legs.httpx, "Client", _RecordingHttpxClient)

        base_url = "http://localhost:8000"
        envelope = _envelope([_row("R_GOLD_HEIGHT_MAX_75_V", "OBJ_GOLD_PASS", "passed")])
        _RecordingHttpxClient.responses = {
            ("POST", f"{base_url}/validation/publish"): _FakeResponse(200, {"runId": "R1"}),
            ("GET", f"{base_url}/validation/view/DG-1200-GOLDEN/R1"): _FakeResponse(
                200, {"evidenceEnvelope": envelope}
            ),
        }

        result = legs.run_leg_data_service(_fixture(), {"data_service_url": base_url})

        assert result.available is True
        assert len(_RecordingHttpxClient.instances) == 1
        assert _RecordingHttpxClient.instances[0].headers == {
            "Authorization": f"Bearer {FAKE_TOKEN}"
        }

    def test_no_authorization_header_when_no_token_configured(self, monkeypatch, tmp_path):
        _clear_token_env(monkeypatch)
        monkeypatch.setenv("DG_DE01_CONNECTOR_TOKEN_FILE", str(tmp_path / "does-not-exist"))
        monkeypatch.setattr(legs.httpx, "Client", _RecordingHttpxClient)

        base_url = "http://localhost:8000"
        envelope = _envelope([_row("R_GOLD_HEIGHT_MAX_75_V", "OBJ_GOLD_PASS", "passed")])
        _RecordingHttpxClient.responses = {
            ("POST", f"{base_url}/validation/publish"): _FakeResponse(200, {"runId": "R1"}),
            ("GET", f"{base_url}/validation/view/DG-1200-GOLDEN/R1"): _FakeResponse(
                200, {"evidenceEnvelope": envelope}
            ),
        }

        result = legs.run_leg_data_service(_fixture(), {"data_service_url": base_url})

        assert result.available is True
        assert _RecordingHttpxClient.instances[0].headers == {}


class TestReplayLegSendsHeaders:
    def setup_method(self):
        _RecordingHttpxClient.instances = []
        _RecordingHttpxClient.responses = {}

    def test_headers_sent_when_token_configured(self, monkeypatch):
        _clear_token_env(monkeypatch)
        monkeypatch.setenv("DG_DE01_CONNECTOR_TOKEN", FAKE_TOKEN)
        monkeypatch.setattr(legs.httpx, "Client", _RecordingHttpxClient)

        base_url = "http://localhost:8000"
        envelope = _envelope([_row("R_GOLD_HEIGHT_MAX_75_V", "OBJ_GOLD_PASS", "passed")])
        _RecordingHttpxClient.responses = {
            ("GET", f"{base_url}/validation/view/DG-1200-GOLDEN"): _FakeResponse(
                200, {"evidenceEnvelope": envelope}
            ),
        }

        result = legs.run_leg_replay(_fixture(), {"data_service_url": base_url})

        assert result.available is True
        assert _RecordingHttpxClient.instances[0].headers == {
            "Authorization": f"Bearer {FAKE_TOKEN}"
        }

    def test_no_authorization_header_when_no_token_configured(self, monkeypatch, tmp_path):
        _clear_token_env(monkeypatch)
        monkeypatch.setenv("DG_DE01_CONNECTOR_TOKEN_FILE", str(tmp_path / "does-not-exist"))
        monkeypatch.setattr(legs.httpx, "Client", _RecordingHttpxClient)

        base_url = "http://localhost:8000"
        envelope = _envelope([_row("R_GOLD_HEIGHT_MAX_75_V", "OBJ_GOLD_PASS", "passed")])
        _RecordingHttpxClient.responses = {
            ("GET", f"{base_url}/validation/view/DG-1200-GOLDEN"): _FakeResponse(
                200, {"evidenceEnvelope": envelope}
            ),
        }

        result = legs.run_leg_replay(_fixture(), {"data_service_url": base_url})

        assert result.available is True
        assert _RecordingHttpxClient.instances[0].headers == {}


class TestPinnedReplaySendsHeaders:
    """run_de01_repeat.py's pinned-replay GET (:428) uses the same headers helper."""

    def setup_method(self):
        _RecordingHttpxClient.instances = []
        _RecordingHttpxClient.responses = {}

    def test_headers_sent_when_token_configured(self, monkeypatch):
        _clear_token_env(monkeypatch)
        monkeypatch.setenv("DG_DE01_CONNECTOR_TOKEN", FAKE_TOKEN)
        monkeypatch.setattr(run_de01_repeat.httpx, "Client", _RecordingHttpxClient)

        base_url = "http://localhost:8000"
        envelope = _envelope([_row("R_GOLD_HEIGHT_MAX_75_V", "OBJ_GOLD_PASS", "passed")])
        _RecordingHttpxClient.responses = {
            ("GET", f"{base_url}/validation/view/DG-1200-GOLDEN/RUN-PINNED-1"): _FakeResponse(
                200, {"evidenceEnvelope": envelope}
            ),
        }

        result = run_de01_repeat.run_leg_replay_pinned(
            _fixture(), {"data_service_url": base_url}, "RUN-PINNED-1"
        )

        assert result.available is True
        assert _RecordingHttpxClient.instances[0].headers == {
            "Authorization": f"Bearer {FAKE_TOKEN}"
        }

    def test_no_authorization_header_when_no_token_configured(self, monkeypatch, tmp_path):
        _clear_token_env(monkeypatch)
        monkeypatch.setenv("DG_DE01_CONNECTOR_TOKEN_FILE", str(tmp_path / "does-not-exist"))
        monkeypatch.setattr(run_de01_repeat.httpx, "Client", _RecordingHttpxClient)

        base_url = "http://localhost:8000"
        envelope = _envelope([_row("R_GOLD_HEIGHT_MAX_75_V", "OBJ_GOLD_PASS", "passed")])
        _RecordingHttpxClient.responses = {
            ("GET", f"{base_url}/validation/view/DG-1200-GOLDEN/RUN-PINNED-1"): _FakeResponse(
                200, {"evidenceEnvelope": envelope}
            ),
        }

        result = run_de01_repeat.run_leg_replay_pinned(
            _fixture(), {"data_service_url": base_url}, "RUN-PINNED-1"
        )

        assert result.available is True
        assert _RecordingHttpxClient.instances[0].headers == {}


# ── No-leak property: a full run_repeat report never contains the token ──────────


def _fake_leg_callable(leg_name: str):
    def _runner(fixture: dict, config: dict):
        envelope = _envelope(
            [_row("R_GOLD_HEIGHT_MAX_75_V", "OBJ_GOLD_PASS", "passed")],
            service_name=leg_name,
            stage="test",
        )
        if leg_name == "data-service":
            envelope["definitionId"] = "run-1"
        return legs.LegResult(leg_name=leg_name, available=True, envelope=envelope)

    return _runner


class TestReportNeverLeaksTheToken:
    def test_json_and_markdown_report_never_contain_the_fake_token(self, monkeypatch, tmp_path):
        _clear_token_env(monkeypatch)
        monkeypatch.setenv("DG_DE01_CONNECTOR_TOKEN", FAKE_TOKEN)

        fake_callables = {name: _fake_leg_callable(name) for name in run_de01_repeat.LEG_ROLES}

        result = run_de01_repeat.run_repeat(
            _fixture(),
            leg_callables=fake_callables,
            restart=None,
            iterations=1,
            batches=1,
            config={"iterations": 1, "batches": 1},
        )
        result.config = run_de01_repeat.collect_config_pins(
            fixture=_fixture(),
            config=result.config,
            subprocess_runner=lambda *a, **k: type(
                "P", (), {"returncode": 1, "stdout": ""}
            )(),
        )

        report = run_de01_repeat.build_repeat_report(result)
        serialized_json = json.dumps(report, ensure_ascii=False)
        assert FAKE_TOKEN not in serialized_json

        json_path = tmp_path / "de01-repeat-report.json"
        md_path = tmp_path / "de01-repeat-report.md"
        run_de01_repeat.emit_repeat_json_report(result, json_path)
        run_de01_repeat.emit_repeat_markdown_report(result, md_path)

        assert FAKE_TOKEN not in json_path.read_text(encoding="utf-8")
        assert FAKE_TOKEN not in md_path.read_text(encoding="utf-8")

    def test_config_dict_passed_to_legs_never_carries_the_token(self, monkeypatch):
        """The token must never be folded into the config dict every leg receives."""
        _clear_token_env(monkeypatch)
        monkeypatch.setenv("DG_DE01_CONNECTOR_TOKEN", FAKE_TOKEN)

        seen_configs: list[dict] = []

        def _capturing_callable(leg_name: str):
            def _runner(fixture: dict, config: dict):
                seen_configs.append(dict(config))
                envelope = _envelope(
                    [_row("R_GOLD_HEIGHT_MAX_75_V", "OBJ_GOLD_PASS", "passed")],
                    service_name=leg_name,
                )
                if leg_name == "data-service":
                    envelope["definitionId"] = "run-1"
                return legs.LegResult(leg_name=leg_name, available=True, envelope=envelope)

            return _runner

        fake_callables = {name: _capturing_callable(name) for name in run_de01_repeat.LEG_ROLES}
        run_de01_repeat.run_repeat(
            _fixture(),
            leg_callables=fake_callables,
            restart=None,
            iterations=1,
            batches=1,
            config={"data_service_url": "http://localhost:8000"},
        )

        for config in seen_configs:
            assert FAKE_TOKEN not in json.dumps(config, ensure_ascii=False)
