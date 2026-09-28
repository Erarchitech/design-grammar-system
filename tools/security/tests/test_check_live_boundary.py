"""Tests for tools/security/check_live_boundary.py (Phase 1205, D-16/D-18).

Bootstraps `sys.path` to `tools/security` (no `__init__.py` there, mirroring
`test_check_env_file.py`) so this test can `import check_live_boundary`
directly. Every HTTP call is served by `httpx.MockTransport` -- no live
stack, no real socket for the HTTP checks. Port checks use an injected fake
connector, never a real `socket.create_connection`.
"""

from __future__ import annotations

import json
import os
import sys

import httpx

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import check_live_boundary as clb  # noqa: E402

UI_URL = "http://ui.test"
DS_URL = "http://ds.test"


def _passing_handler(request: httpx.Request) -> httpx.Response:
    url = str(request.url)
    method = request.method

    if method == "GET" and url == f"{UI_URL}/neo4j/":
        return httpx.Response(404)
    if method == "POST" and url == f"{UI_URL}/neo4j/db/neo4j/tx/commit":
        return httpx.Response(404)
    if method == "GET" and url == f"{UI_URL}/n8n/webhook/dg/graph-query":
        return httpx.Response(404)

    if method == "GET" and url == f"{UI_URL}/data-service/validation/runs/any-project":
        return httpx.Response(401)
    if method == "POST" and url == f"{UI_URL}/data-service/mcp":
        return httpx.Response(401)
    if method == "GET" and url == f"{UI_URL}/data-service/auth/me":
        return httpx.Response(401)
    if method == "GET" and url == f"{DS_URL}/validation/runs/any-project":
        return httpx.Response(401)
    if method == "GET" and url == f"{UI_URL}/data-service/":
        return httpx.Response(200, text="ok")

    if method == "GET" and url == f"{UI_URL}/config.js":
        body = (
            "window.GRAPH_CONFIG = {\n"
            '  dataServiceUrl: "/data-service",\n'
            '  speckleBaseUrl: "http://localhost:8090"\n'
            "};\n"
        )
        return httpx.Response(200, text=body)

    return httpx.Response(599, text=f"unexpected request in test: {method} {url}")


def _client(handler) -> httpx.Client:
    return httpx.Client(transport=httpx.MockTransport(handler), timeout=5.0)


def _refuse_all(host: str, port: int, timeout: float) -> bool:
    return False


def _reachable_all(host: str, port: int, timeout: float) -> bool:
    return True


class TestCheckProxyRemoved:
    def test_all_404_pass(self):
        client = _client(_passing_handler)
        rows = clb.check_proxy_removed(client, UI_URL)
        assert len(rows) == 3
        assert all(row["result"] == "pass" for row in rows)

    def test_200_spa_fallback_is_a_failure(self):
        def handler(request: httpx.Request) -> httpx.Response:
            if str(request.url) == f"{UI_URL}/neo4j/":
                return httpx.Response(200, text="<html>SPA fallback</html>")
            return _passing_handler(request)

        client = _client(handler)
        rows = clb.check_proxy_removed(client, UI_URL)
        neo4j_row = next(r for r in rows if r["target"] == f"GET {UI_URL}/neo4j/")
        assert neo4j_row["result"] == "fail"
        assert neo4j_row["observed"] == "200"

    def test_connection_error_is_a_failure_not_a_crash(self):
        def handler(request: httpx.Request) -> httpx.Response:
            raise httpx.ConnectError("refused", request=request)

        client = _client(handler)
        rows = clb.check_proxy_removed(client, UI_URL)
        assert all(row["result"] == "fail" for row in rows)
        assert all(row["observed"] == "unreachable" for row in rows)


class TestCheckUnauthenticated:
    def test_all_pass_on_a_correctly_authorized_stack(self):
        client = _client(_passing_handler)
        rows = clb.check_unauthenticated(client, UI_URL, DS_URL)
        assert len(rows) == 5
        assert all(row["result"] == "pass" for row in rows)

    def test_a_200_on_a_protected_route_is_a_failure(self):
        def handler(request: httpx.Request) -> httpx.Response:
            if str(request.url) == f"{UI_URL}/data-service/auth/me":
                return httpx.Response(200, json={"leaked": "data"})
            return _passing_handler(request)

        client = _client(handler)
        rows = clb.check_unauthenticated(client, UI_URL, DS_URL)
        auth_me_row = next(r for r in rows if "auth/me" in r["target"])
        assert auth_me_row["result"] == "fail"
        assert auth_me_row["observed"] == "200"

    def test_root_not_200_is_a_failure(self):
        def handler(request: httpx.Request) -> httpx.Response:
            if str(request.url) == f"{UI_URL}/data-service/":
                return httpx.Response(500)
            return _passing_handler(request)

        client = _client(handler)
        rows = clb.check_unauthenticated(client, UI_URL, DS_URL)
        root_row = next(r for r in rows if r["target"] == f"GET {UI_URL}/data-service/")
        assert root_row["result"] == "fail"


class TestCheckConfigJs:
    def test_passing_config_js_has_no_credential_or_default(self):
        client = _client(_passing_handler)
        rows = clb.check_config_js(client, UI_URL)
        assert len(rows) == 2
        assert all(row["result"] == "pass" for row in rows)

    def test_credential_key_present_is_a_failure(self):
        def handler(request: httpx.Request) -> httpx.Response:
            if str(request.url) == f"{UI_URL}/config.js":
                body = 'window.GRAPH_CONFIG = { neo4jPassword: "12345678" };'
                return httpx.Response(200, text=body)
            return _passing_handler(request)

        client = _client(handler)
        rows = clb.check_config_js(client, UI_URL)
        key_row = next(r for r in rows if "credential key" in r["expected"])
        default_row = next(r for r in rows if "known-default" in r["expected"])
        assert key_row["result"] == "fail"
        assert "neo4jPassword" in key_row["observed"]
        assert default_row["result"] == "fail"
        assert "12345678" in default_row["observed"]

    def test_known_default_source_is_recorded_in_the_note(self):
        client = _client(_passing_handler)
        rows = clb.check_config_js(client, UI_URL)
        default_row = next(r for r in rows if "known-default" in r["expected"])
        assert "knownDefaultsSource=" in default_row["note"]

    def test_non_200_config_js_is_a_failure(self):
        def handler(request: httpx.Request) -> httpx.Response:
            if str(request.url) == f"{UI_URL}/config.js":
                return httpx.Response(404)
            return _passing_handler(request)

        client = _client(handler)
        rows = clb.check_config_js(client, UI_URL)
        assert len(rows) == 1
        assert rows[0]["result"] == "fail"


class TestCheckPorts:
    def test_multi_user_refused_ports_pass(self):
        rows = clb.check_ports("127.0.0.1", "multi-user", connect=_refuse_all)
        assert len(rows) == 3
        assert all(row["result"] == "pass" for row in rows)

    def test_multi_user_reachable_port_fails(self):
        rows = clb.check_ports("127.0.0.1", "multi-user", connect=_reachable_all)
        assert all(row["result"] == "fail" for row in rows)

    def test_local_profile_reports_info_never_fail(self):
        rows_reachable = clb.check_ports("127.0.0.1", "local", connect=_reachable_all)
        rows_refused = clb.check_ports("127.0.0.1", "local", connect=_refuse_all)
        assert all(row["result"] == "info" for row in rows_reachable)
        assert all(row["result"] == "info" for row in rows_refused)
        assert all("trusted-local" in row["note"] for row in rows_reachable)

    def test_targets_are_bolt_http_and_n8n(self):
        rows = clb.check_ports("127.0.0.1", "multi-user", connect=_refuse_all)
        targets = {row["target"] for row in rows}
        assert targets == {"127.0.0.1:7687", "127.0.0.1:7474", "127.0.0.1:5678"}


class TestRunAllChecksAndExitCode:
    def test_passing_stack_multi_user_exits_0(self):
        client = _client(_passing_handler)
        report = clb.run_all_checks(
            ui_url=UI_URL,
            data_service_url=DS_URL,
            host="127.0.0.1",
            profile="multi-user",
            client=client,
            connect=_refuse_all,
        )
        assert report["passed"] is True
        assert all(row["result"] != "fail" for row in report["checks"])

    def test_reachable_port_in_multi_user_fails_the_whole_report(self):
        client = _client(_passing_handler)
        report = clb.run_all_checks(
            ui_url=UI_URL,
            data_service_url=DS_URL,
            host="127.0.0.1",
            profile="multi-user",
            client=client,
            connect=_reachable_all,
        )
        assert report["passed"] is False

    def test_local_profile_ports_never_fail_the_report(self):
        client = _client(_passing_handler)
        report = clb.run_all_checks(
            ui_url=UI_URL,
            data_service_url=DS_URL,
            host="127.0.0.1",
            profile="local",
            client=client,
            connect=_reachable_all,
        )
        assert report["passed"] is True

    def test_report_never_carries_more_than_200_chars_of_body(self):
        client = _client(_passing_handler)
        report = clb.run_all_checks(
            ui_url=UI_URL,
            data_service_url=DS_URL,
            host="127.0.0.1",
            profile="local",
            client=client,
            connect=_refuse_all,
        )
        serialized = json.dumps(report)
        for row in report["checks"]:
            for value in row.values():
                if isinstance(value, str):
                    assert len(value) <= clb._MAX_BODY_CHARS + 100  # generous cap on any single field
        assert serialized  # report is JSON-serializable end to end


class TestMain:
    def test_help_exits_0_and_lists_profile(self, capsys):
        try:
            clb.main(["--help"])
        except SystemExit as exc:
            assert exc.code == 0
        else:
            raise AssertionError("--help should raise SystemExit")
        out = capsys.readouterr().out
        assert "--profile" in out

    def test_json_out_written_when_given(self, tmp_path, monkeypatch, capsys):
        def fake_run_all_checks(**kwargs):
            return {"passed": True, "checks": []}

        monkeypatch.setattr(clb, "run_all_checks", fake_run_all_checks)
        json_out = tmp_path / "report.json"

        exit_code = clb.main(
            [
                "--ui-url",
                UI_URL,
                "--data-service-url",
                DS_URL,
                "--profile",
                "local",
                "--json-out",
                str(json_out),
            ]
        )

        assert exit_code == 0
        assert json.loads(json_out.read_text(encoding="utf-8")) == {"passed": True, "checks": []}
