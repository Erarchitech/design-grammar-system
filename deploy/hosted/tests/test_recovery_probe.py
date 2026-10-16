"""Offline synthetic fixtures only; never contact an API or graph."""
import hashlib
import importlib.util
import unittest
import io
import json
import urllib.error
from unittest import mock
from pathlib import Path

SPEC = importlib.util.spec_from_file_location(
    "recovery_probe", Path(__file__).resolve().parents[1] / "recovery-test" / "probe.py")


class RecoveryProbeTests(unittest.TestCase):
    def test_exact_note_ids_are_project_scoped(self):
        self.assertTrue(SPEC.origin and Path(SPEC.origin).is_file(), "recovery probe is missing")
        probe = importlib.util.module_from_spec(SPEC)
        SPEC.loader.exec_module(probe)
        notes = probe.expected_notes(["synthetic-a", "synthetic-b"],
                                     "hosted-ingest/README.md", "# Synthetic fixture\n")
        self.assertEqual(len(notes), 2)
        self.assertNotEqual(notes[0]["noteId"], notes[1]["noteId"])
        self.assertEqual(notes[0]["noteId"], hashlib.sha256(
            b"synthetic-a:hosted-ingest/README.md").hexdigest()[:16])
        self.assertEqual(notes[0]["title"], "Synthetic fixture")
        self.assertEqual(notes[0]["contentSha256"], hashlib.sha256(
            b"# Synthetic fixture\n").hexdigest())


def load_probe():
    probe = importlib.util.module_from_spec(SPEC)
    SPEC.loader.exec_module(probe)
    return probe


class SyntheticAPI:
    """In-memory contract fixture; deliberately not a product/service emulator."""
    def __init__(self):
        self.calls = []
        self.projects = []
        self.sessions = {}
        self.serial = 0
        self.notes = []
        self.member = None
        self.password = None

    def client(self, cookie=None):
        api = self

        class Client:
            def __init__(self):
                self.cookie = cookie

            def request(self, method, path, body=None, csrf=True):
                api.calls.append((method, path, body, self.cookie, csrf))
                identity = api.sessions.get(self.cookie)
                if method == "GET" and path == "/":
                    return 200, {"status": "ok"}
                if path == "/auth/login":
                    if body["username"] == "sandbox-admin":
                        if body["password"] != "synthetic-admin-password":
                            return 401, {}
                        identity = "admin"
                    elif body["username"] == api.member and body["password"] == api.password:
                        identity = "member"
                    else:
                        return 401, {}
                    api.serial += 1
                    self.cookie = "synthetic-session-" + str(api.serial)
                    api.sessions[self.cookie] = identity
                    return 200, {"username": body["username"], "isAdmin": identity == "admin"}
                if path == "/auth/accept-invite":
                    if body["inviteCode"] != "synthetic-invite":
                        return 400, {}
                    api.password = body["password"]
                    api.serial += 1
                    self.cookie = "synthetic-session-" + str(api.serial)
                    api.sessions[self.cookie] = "member"
                    return 200, {"username": api.member, "isAdmin": False}
                if not identity:
                    return 401, {}
                if method != "GET" and not csrf:
                    return 403, {}
                if path == "/auth/logout":
                    api.sessions.pop(self.cookie, None)
                    self.cookie = None
                    return 204, {}
                if path == "/auth/me":
                    return 200, {"username": api.member, "isAdmin": False,
                                 "memberships": [{"project": api.projects[0], "role": "viewer"}]}
                if path == "/projects" and method == "POST" and identity == "admin":
                    api.projects.append(body["project"])
                    return 201, {"project": body["project"], "role": "owner"}
                if path == "/auth/invites" and identity == "admin":
                    api.member = body["username"]
                    return 200, {"status": "invited", "inviteCode": "synthetic-invite"}
                if path == "/knowledge/ingest/folder" and identity == "admin":
                    api.notes += load_probe().expected_notes([body["project"]],
                        "hosted-ingest/README.md", "# Synthetic fixture\n")
                    return 200, {"inserted": 1, "skipped": 0}
                if path == "/projects" and method == "GET":
                    return 200, {"projects": [{"project": api.projects[0], "role": "viewer"}]}
                if path.startswith("/knowledge/notes/"):
                    project = path.rsplit("/", 1)[1]
                    if identity == "member" and project != api.projects[0]:
                        return 403, {}
                    return 200, {"project": project, "notes": [n for n in api.notes if n["project"] == project]}
                if path.startswith("/knowledge/note/"):
                    note = next(n for n in api.notes if n["noteId"] == path.rsplit("/", 1)[1])
                    if identity == "member" and note["project"] != api.projects[0]:
                        return 404, {}
                    return 200, dict(note, content="# Synthetic fixture\n")
                raise AssertionError("unexpected synthetic route")
        return Client()


class WorkflowTests(unittest.TestCase):
    def setUp(self):
        self.probe = load_probe()
        self.api = SyntheticAPI()
        self.saved = None
        self.llm_calls = []
        self.env = {"DG_BOOTSTRAP_ADMIN_USER": "sandbox-admin",
                    "DG_BOOTSTRAP_ADMIN_PASSWORD": "synthetic-admin-password"}

    def save(self, state):
        self.saved = state

    def run_probe(self, mode):
        return self.probe.run(mode, env=self.env, client_factory=self.api.client,
            load_state=lambda: self.saved, save_state=self.save,
            fixture_reader=lambda: "# Synthetic fixture\n",
            graph_reader=lambda notes: list(self.api.notes),
            llm_check=lambda client, key, seed: self.llm_calls.append(seed))

    def test_verify_fails_closed_on_missing_or_damaged_private_state(self):
        self.run_probe("seed")
        original = self.saved
        for state in (None, {}, dict(original, notes=original["notes"][:1]),
                      dict(original, projects=[original["projects"][0]] * 2)):
            self.saved = state
            with self.subTest(state_present=state is not None), self.assertRaises(self.probe.ProbeError):
                self.run_probe("verify")
        self.saved = original
        self.api.notes[0]["contentSha256"] = "synthetic-damaged-content"
        with self.assertRaises(self.probe.ProbeError):
            self.run_probe("verify")

    def test_restored_revoked_cookie_resurrection_is_detected(self):
        self.run_probe("seed")
        self.api.sessions[self.saved["revokedCookie"]] = "member"
        with self.assertRaises(self.probe.ProbeError):
            self.run_probe("verify")

    def test_restored_cross_project_access_is_detected(self):
        self.run_probe("seed")
        factory = self.api.client
        def broken_factory(cookie=None):
            client = factory(cookie)
            request = client.request
            def broken(method, path, body=None, csrf=True):
                if path == "/knowledge/notes/" + self.saved["projects"][1]:
                    return 200, {"notes": []}
                return request(method, path, body, csrf)
            client.request = broken
            return client
        with mock.patch.object(self.api, "client", side_effect=broken_factory):
            with self.assertRaises(self.probe.ProbeError):
                self.run_probe("verify")

    def test_seed_honors_pinned_note_resource_not_found_contract(self):
        # Execute the exact committed not-found factory without importing the
        # application (which would initialize runtime dependencies/stores).
        import ast
        import subprocess
        from types import SimpleNamespace
        root = Path(__file__).resolve().parents[3]
        raw = subprocess.check_output(['git', 'show',
            'c82b92b29423c515e353e3fa4f9c17e9b0d83438:data-service/app.py'], cwd=root)
        tree = ast.parse(raw)
        factory = next(n for n in tree.body
                       if isinstance(n, ast.FunctionDef) and n.name == '_note_not_found')
        namespace = {'HTTPException': lambda **kw: SimpleNamespace(**kw)}
        exec(compile(ast.Module(body=[factory], type_ignores=[]), '<pinned-note-policy>', 'exec'), namespace)
        denied = namespace['_note_not_found']().status_code
        self.assertEqual(denied, 404)
        original = self.api.client
        def client_factory(cookie=None):
            client = original(cookie)
            request = client.request
            def contract(method, path, body=None, csrf=True):
                code, result = request(method, path, body, csrf=csrf)
                if path.startswith('/knowledge/note/') and code == 403:
                    return denied, {}
                return code, result
            client.request = contract
            return client
        with mock.patch.object(self.api, 'client', side_effect=client_factory):
            self.assertTrue(self.run_probe('seed')['project_isolation'])
            self.assertTrue(self.run_probe('verify')['project_isolation'])

    def test_logout_failure_never_replaces_primary_or_skips_other_logout(self):
        original = self.api.client
        attempts = []
        def broken_factory(cookie=None):
            client = original(cookie)
            request = client.request
            def broken(method, path, body=None, csrf=True):
                if path == '/auth/logout':
                    attempts.append(client.cookie)
                    raise RuntimeError('synthetic logout failure')
                return request(method, path, body, csrf=csrf)
            client.request = broken
            return client
        with mock.patch.object(self.api, 'client', side_effect=broken_factory), \
             mock.patch.object(self.probe, 'check_user', side_effect=ValueError('synthetic primary')):
            with self.assertRaisesRegex(ValueError, 'synthetic primary'):
                self.run_probe('seed')
        self.assertEqual(len(attempts), 2)

    def test_logout_only_failure_is_not_reported_as_success(self):
        self.run_probe('seed')
        original = self.api.client
        attempts = []
        def broken_factory(cookie=None):
            client = original(cookie)
            request = client.request
            def broken(method, path, body=None, csrf=True):
                if path == '/auth/logout':
                    attempts.append(client.cookie)
                    raise RuntimeError('synthetic logout failure')
                return request(method, path, body, csrf=csrf)
            client.request = broken
            return client
        with mock.patch.object(self.api, 'client', side_effect=broken_factory):
            with self.assertRaises(self.probe.ProbeError):
                self.run_probe('verify')
        self.assertEqual(len(attempts), 2)

    def test_seed_refuses_existing_state_without_creating_projects(self):
        self.saved = {"synthetic": "existing"}
        with self.assertRaises(self.probe.ProbeError):
            self.run_probe("seed")
        self.assertFalse(self.api.projects)

    def test_seed_then_verify_restored_private_expectations(self):
        self.assertTrue(hasattr(self.probe, "run"), "recovery workflow is missing")
        seed = self.run_probe("seed")
        state = self.saved
        self.assertEqual(len(state["notes"]), 2)
        self.assertEqual(len(set(state["projects"])), 2)
        self.assertEqual(state["notes"], self.api.notes)
        self.assertTrue(state["password"])
        self.assertTrue(state["revokedCookie"])
        self.assertNotIn(state["revokedCookie"], self.api.sessions)
        before = len(self.api.calls)
        verify = self.run_probe("verify")
        self.assertIs(self.saved, state)
        self.assertEqual(seed['projects_created'], 2)
        self.assertEqual(verify["neo4j_scoped_notes"], 2)
        self.assertNotIn('csrf_denied', verify)
        self.assertNotIn('authenticated_ingests', verify)
        self.assertNotIn('projects_created', verify)
        self.assertEqual(verify['seed_authenticated_ingests'], 2)
        self.assertIs(verify['seed_csrf_denied'], True)
        self.assertEqual(verify['seed_projects_created'], 2)
        self.assertTrue(verify["revoked_session_denied"])
        self.assertTrue(all(type(value) in (bool, int) for value in verify.values()))
        restored_calls = self.api.calls[before:]
        self.assertTrue(any(path == "/auth/login" and body["username"] == state["username"]
                            for method, path, body, cookie, csrf in restored_calls))
        self.assertFalse(any(path in ("/auth/invites", "/auth/accept-invite", "/knowledge/ingest/folder")
                             for method, path, body, cookie, csrf in restored_calls))
        self.assertFalse(any(method == "POST" and path == "/projects"
                             for method, path, body, cookie, csrf in restored_calls))
        self.assertEqual(self.llm_calls, [True, False])
        self.assertFalse(self.api.sessions, "temporary fresh sessions must be logged out")


class SyntheticResponse(io.BytesIO):
    status = 200
    headers = {}


class TransportTests(unittest.TestCase):
    def setUp(self):
        self.probe = load_probe()

    def test_http_is_loopback_proxy_free_csrf_bounded_and_cookie_explicit(self):
        self.assertTrue(hasattr(self.probe, "HTTPClient"), "HTTP transport is missing")
        opener = mock.Mock()
        opener.open.return_value = SyntheticResponse(b'{"ok":true}')
        with mock.patch.object(self.probe.urllib.request, "build_opener", return_value=opener) as build:
            client = self.probe.HTTPClient(cookie="synthetic-cookie")
        self.assertTrue(any(isinstance(h, self.probe.urllib.request.ProxyHandler) and h.proxies == {}
                            for h in build.call_args.args))
        self.assertTrue(any(isinstance(h, self.probe.NoRedirect) for h in build.call_args.args))
        code, body = client.request("POST", "/projects", {"project": "synthetic-a"})
        req = opener.open.call_args.args[0]
        self.assertEqual(req.full_url, "http://127.0.0.1:8000/projects")
        self.assertEqual(req.get_header("Cookie"), "dg_session=synthetic-cookie")
        self.assertEqual(req.get_header("X-dg-csrf"), "1")
        self.assertEqual(opener.open.call_args.kwargs["timeout"], 15)
        self.assertEqual((code, body), (200, {"ok": True}))
        for path in ("http://external.invalid", "//external.invalid", "/x\r\nsecret"):
            with self.subTest(path=path), self.assertRaises(self.probe.ProbeError):
                client.request("GET", path)
        opener.open.return_value = SyntheticResponse(b"x" * (self.probe.MAX_BODY + 1))
        with self.assertRaises(self.probe.ProbeError):
            client.request("GET", "/")
        opener.open.side_effect = urllib.error.HTTPError(
            "http://127.0.0.1:8000/", 401, "synthetic secret error", {}, io.BytesIO(b"synthetic private"))
        self.assertEqual(client.request("GET", "/auth/me"), (401, {}))

    def test_secure_cookie_can_be_replayed_only_to_fixed_loopback(self):
        self.assertTrue(hasattr(self.probe, "HTTPClient"), "HTTP transport is missing")
        from email.message import Message
        headers = Message()
        headers.add_header("Set-Cookie", "dg_session=synthetic-secure; Secure; HttpOnly; Path=/")
        response = SyntheticResponse(b'{"username":"synthetic"}')
        response.headers = headers
        opener = mock.Mock()
        opener.open.return_value = response
        with mock.patch.object(self.probe.urllib.request, "build_opener", return_value=opener):
            client = self.probe.HTTPClient()
        client.request("POST", "/auth/login", {})
        self.assertEqual(client.cookie, "synthetic-secure")
        response = SyntheticResponse(b"")
        response.status = 204
        opener.open.return_value = response
        client.request("POST", "/auth/logout")
        self.assertIsNone(client.cookie)


class AdapterTests(unittest.TestCase):
    def setUp(self):
        self.probe = load_probe()
        self.env = {"NEO4J_URI": "bolt://synthetic-graph:7687", "NEO4J_USER": "synthetic-user",
                    "NEO4J_PASSWORD": "synthetic-graph-password", "NEO4J_DATABASE": "synthetic-db"}

    def test_graph_reads_only_two_scoped_projects_and_hashes_content(self):
        self.assertTrue(hasattr(self.probe, "read_graph"), "Neo4j adapter is missing")
        notes = self.probe.expected_notes(["synthetic-a", "synthetic-b"],
                                          "hosted-ingest/README.md", "# Synthetic fixture\n")
        driver = mock.MagicMock()
        session = driver.session.return_value.__enter__.return_value
        session.run.side_effect = [[dict(n, content="# Synthetic fixture\n")] for n in notes]
        graph = mock.Mock()
        graph.driver.return_value = driver
        with mock.patch.dict("sys.modules", {"neo4j": mock.Mock(
                GraphDatabase=graph, Query=lambda text, timeout: text)}):
            rows = self.probe.read_graph(notes, self.env)
        self.assertEqual(rows, notes)
        self.assertEqual(driver.session.call_args.kwargs, {"database": "synthetic-db"})
        for call, note in zip(session.run.call_args_list, notes):
            query = str(call.args[0])
            self.assertIn("project:$project", query)
            self.assertIn("graph:$graph", query)
            self.assertNotIn(note["project"], query)
            self.assertEqual(call.kwargs, {"project": note["project"], "graph": "SpecGraph"})
        driver.close.assert_called_once()
        graph.driver.assert_called_once_with("bolt://synthetic-graph:7687",
            auth=("synthetic-user", "synthetic-graph-password"), connection_timeout=10,
            max_transaction_retry_time=0)

    def test_llm_settings_safe_http_contract_proves_ciphertext_and_exact_decryption(self):
        self.assertTrue(hasattr(self.probe, "check_llm"), "safe LLM check is missing")
        key = "synthetic-recovery-secret-0000000000000000"
        client = mock.Mock()
        client.request.return_value = (200, {"provider": "openai", "model": "recovery-no-call",
            "apiKeyConfigured": True, "apiKeyPreview": key[:6] + "..." + key[-6:],
            "baseUrl": "http://127.0.0.1:9/v1"})
        ciphertext = "synthetic-ciphertext-not-a-real-token"
        gateway = mock.Mock()
        gateway.load_persisted_llm_settings.return_value = {"provider": "openai",
            "model": "recovery-no-call", "baseUrl": "http://127.0.0.1:9/v1", "apiKey": ciphertext}
        gateway.decrypt_value.return_value = key
        with mock.patch.dict("sys.modules", {"llm_gateway": gateway}):
            self.probe.check_llm(client, key, True, {"LLM_MASTER_SECRET": "synthetic-master"})
            methods = [(c.args[0], c.args[1]) for c in client.request.call_args_list]
            self.assertEqual(methods, [("PUT", "/llm/settings"), ("GET", "/llm/settings")])
            gateway.decrypt_value.assert_called_with(ciphertext, "synthetic-master")
            client.reset_mock()
            self.probe.check_llm(client, key, False, {"LLM_MASTER_SECRET": "synthetic-master"})
            self.assertEqual([(c.args[0], c.args[1]) for c in client.request.call_args_list],
                             [("GET", "/llm/settings")])
            gateway.decrypt_value.return_value = "wrong-synthetic-key"
            with self.assertRaises(self.probe.ProbeError):
                self.probe.check_llm(client, key, False, {"LLM_MASTER_SECRET": "synthetic-master"})

    def test_private_state_uses_exclusive_0600_fixed_exchange_path_and_bounded_reads(self):
        self.assertTrue(hasattr(self.probe, "write_state"), "private state adapter is missing")
        self.assertEqual(str(self.probe.STATE_PATH).replace("\\", "/"), "/exchange/probe-state.json")
        fake_file = mock.MagicMock()
        with mock.patch.object(self.probe.os, "open", return_value=73) as opening, \
             mock.patch.object(self.probe.os, "fdopen", return_value=fake_file), \
             mock.patch.object(self.probe.os, "fsync"):
            self.probe.write_state({"synthetic": "private"})
        args = opening.call_args.args
        self.assertEqual(args[0], self.probe.STATE_PATH)
        self.assertEqual(args[2], 0o600)
        self.assertTrue(args[1] & self.probe.os.O_EXCL)
        self.assertTrue(args[1] & self.probe.os.O_CREAT)
        with mock.patch.object(self.probe.Path, "open", return_value=mock.MagicMock()) as opening:
            handle = opening.return_value.__enter__.return_value
            handle.read.return_value = b'{"synthetic":"private"}'
            self.assertEqual(self.probe.read_state(), {"synthetic": "private"})
            handle.read.assert_called_once_with(self.probe.MAX_BODY + 1)
        with mock.patch.object(self.probe.Path, "open", side_effect=FileNotFoundError):
            self.assertIsNone(self.probe.read_state())

    def test_fixture_read_is_fixed_readonly_and_bounded(self):
        self.assertTrue(hasattr(self.probe, "read_fixture"), "fixture reader is missing")
        with mock.patch.object(self.probe.Path, "open", return_value=mock.MagicMock()) as opening:
            handle = opening.return_value.__enter__.return_value
            handle.read.return_value = b"# Synthetic fixture\n"
            self.assertEqual(self.probe.read_fixture(), "# Synthetic fixture\n")
            self.assertEqual(opening.call_args.args, ("rb",))
            handle.read.assert_called_once_with(self.probe.MAX_BODY + 1)
            handle.read.return_value = b"# Synthetic fixture\r\nline\r\n"
            self.assertEqual(self.probe.read_fixture(), "# Synthetic fixture\nline\n")


class EntryTests(unittest.TestCase):
    def setUp(self):
        self.probe = load_probe()

    def test_ready_checks_api_and_graph_without_login_or_state(self):
        self.assertTrue(hasattr(self.probe, "read_graph_ready"), "graph readiness is missing")
        client = mock.Mock()
        client.request.return_value = (200, {"status": "ok"})
        with mock.patch.object(self.probe, "read_graph_ready") as graph:
            result = self.probe.run("ready", env={}, client_factory=lambda: client,
                load_state=lambda: self.fail("ready read state"),
                save_state=lambda value: self.fail("ready wrote state"))
        self.assertEqual(result, {"api_ready": True, "neo4j_ready": True})
        graph.assert_called_once_with({})
        self.assertEqual(client.request.call_count, 1)
        self.assertEqual(client.request.call_args.args[:2], ("GET", "/"))
        driver = mock.MagicMock()
        session = driver.session.return_value.__enter__.return_value
        session.run.return_value.single.return_value = {"ok": 1}
        with mock.patch.object(self.probe, "graph_driver", return_value=driver), \
             mock.patch.dict("sys.modules", {"neo4j": mock.Mock(Query=lambda text, timeout: text)}):
            self.probe.read_graph_ready({})
        self.assertEqual(session.run.call_args.args, ("RETURN 1 AS ok",))
        driver.close.assert_called_once()

    def test_cli_only_emits_fixed_bool_count_json_and_generic_errors(self):
        self.assertTrue(hasattr(self.probe, "main"), "CLI is missing")
        for argv, result, expected_code in [(["seed"], {"neo4j_scoped_notes": 2}, 0),
                                            (["verify"], {"unexpected-secret": "synthetic-secret"}, 1),
                                            (["other"], {}, 1), ([], {}, 1)]:
            stdout, stderr = io.StringIO(), io.StringIO()
            with mock.patch.object(self.probe, "run", return_value=result), \
                 mock.patch("sys.stdout", stdout), mock.patch("sys.stderr", stderr):
                code = self.probe.main(argv)
            self.assertEqual(code, expected_code)
            if code == 0:
                self.assertEqual(json.loads(stdout.getvalue()), result)
                self.assertEqual(stderr.getvalue(), "")
            else:
                self.assertEqual(stdout.getvalue(), "")
                self.assertEqual(stderr.getvalue(), "recovery probe failed\n")
        stdout, stderr = io.StringIO(), io.StringIO()
        with mock.patch.object(self.probe, "run", side_effect=RuntimeError("synthetic-secret")), \
             mock.patch("sys.stdout", stdout), mock.patch("sys.stderr", stderr):
            self.assertEqual(self.probe.main(["verify"]), 1)
        self.assertEqual(stdout.getvalue(), "")
        self.assertEqual(stderr.getvalue(), "recovery probe failed\n")


if __name__ == "__main__":
    unittest.main()
