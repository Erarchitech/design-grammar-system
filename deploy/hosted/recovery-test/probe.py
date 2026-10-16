"""Synthetic recovery probe; contract pinned to product c82b92b29423c515e353e3fa4f9c17e9b0d83438.

Execute only in the isolated API container. Private state belongs exclusively to
/exchange/probe-state.json on the named exchange volume (never a host bind mount).
The caller must encrypt that volume in transit and wipe it during cleanup.

Usage: python -B /app/recovery_probe.py {ready|seed|verify}
Inputs: DG_BOOTSTRAP_ADMIN_USER=sandbox-admin, DG_BOOTSTRAP_ADMIN_PASSWORD,
NEO4J_URI, NEO4J_PASSWORD, LLM_MASTER_SECRET; optional NEO4J_USER/DATABASE.
The readonly /mnt/repo/hosted-ingest directory must contain only README.md.
Seed is single-use; verify reads its original state without reseeding data.
Only PUT/GET /llm/settings and local decrypt_value are used: no provider calls.
"""
import hashlib
import os
import secrets
import json
import urllib.error
import urllib.request
from http.cookies import SimpleCookie
from pathlib import Path

BASE = "http://127.0.0.1:8000"
MAX_BODY = 65536


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        raise ProbeError("recovery check failed")


class HTTPClient:
    """Explicit cookie replay permits Secure cookies on container loopback only.

    No remote URL, proxy, redirect, shared cookie jar or logging is permitted.
    """
    def __init__(self, cookie=None):
        self.cookie = cookie
        self.opener = urllib.request.build_opener(urllib.request.ProxyHandler({}), NoRedirect())

    def request(self, method, path, body=None, csrf=True):
        require(path.startswith("/") and not path.startswith("//")
                and all(ord(c) >= 32 and ord(c) != 127 for c in path))
        headers = {"Content-Type": "application/json"}
        if csrf and method not in ("GET", "HEAD"):
            headers["X-DG-CSRF"] = "1"
        if self.cookie:
            require(all(c.isalnum() or c in "_-" for c in self.cookie))
            headers["Cookie"] = "dg_session=" + self.cookie
        data = None if body is None else json.dumps(body).encode()
        require(data is None or len(data) <= MAX_BODY)
        req = urllib.request.Request(BASE + path, data=data, headers=headers, method=method)
        try:
            with self.opener.open(req, timeout=15) as response:
                code = response.status
                require(200 <= code < 300)
                raw = response.read(MAX_BODY + 1)
                require(len(raw) <= MAX_BODY)
                result = json.loads(raw) if raw else {}
                require(isinstance(result, dict))
                for header in response.headers.get_all("Set-Cookie", []) if hasattr(response.headers, "get_all") else []:
                    cookies = SimpleCookie()
                    cookies.load(header)
                    if "dg_session" in cookies:
                        self.cookie = cookies["dg_session"].value or None
                if path == "/auth/logout":
                    self.cookie = None
                return code, result
        except urllib.error.HTTPError as error:
            code = error.code
            error.close()  # never read or echo an error body
            return code, {}

STATE_PATH = Path("/exchange/probe-state.json")
SOURCE = "hosted-ingest/README.md"


def read_state():
    try:
        with STATE_PATH.open("rb") as handle:
            raw = handle.read(MAX_BODY + 1)
    except FileNotFoundError:
        return None
    require(len(raw) <= MAX_BODY)
    state = json.loads(raw)
    require(isinstance(state, dict))
    return state


def write_state(state):
    raw = json.dumps(state, sort_keys=True).encode()
    require(len(raw) <= MAX_BODY)
    flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL | getattr(os, "O_NOFOLLOW", 0)
    fd = os.open(STATE_PATH, flags, 0o600)
    with os.fdopen(fd, "wb") as handle:
        handle.write(raw)
        handle.flush()
        os.fsync(handle.fileno())


def read_fixture():
    with (Path("/mnt/repo") / SOURCE).open("rb") as handle:
        raw = handle.read(MAX_BODY + 1)
    require(len(raw) <= MAX_BODY)
    # Product Path.read_text uses universal-newline decoding before ingest.
    return raw.decode("utf-8").replace("\r\n", "\n").replace("\r", "\n")


def graph_driver(env):
    from neo4j import GraphDatabase
    return GraphDatabase.driver(env["NEO4J_URI"],
        auth=(env.get("NEO4J_USER", "neo4j"), env["NEO4J_PASSWORD"]),
        connection_timeout=10, max_transaction_retry_time=0)


def read_graph(notes, env):
    from neo4j import Query
    driver = graph_driver(env)
    rows = []
    try:
        with driver.session(database=env.get("NEO4J_DATABASE", "neo4j")) as session:
            for note in notes:
                query = Query("MATCH (n:SpecNote {project:$project, graph:$graph}) "
                              "RETURN n.project AS project, n.graph AS graph, n.noteId AS noteId, "
                              "n.source AS source, n.title AS title, n.content AS content LIMIT 3", timeout=15)
                for record in session.run(query, project=note["project"], graph="SpecGraph"):
                    row = dict(record)
                    row["contentSha256"] = hashlib.sha256(row.pop("content").encode()).hexdigest()
                    rows.append(row)
    finally:
        driver.close()
    return rows


def read_graph_ready(env):
    from neo4j import Query
    driver = graph_driver(env)
    try:
        with driver.session(database=env.get("NEO4J_DATABASE", "neo4j")) as session:
            require(session.run(Query("RETURN 1 AS ok", timeout=15)).single()["ok"] == 1)
    finally:
        driver.close()


def check_llm(client, key, seed, env):
    # Pinned app.py PUT/GET do encryption/decryption only. Never call
    # /llm/settings/test, /llm/models, /llm/generate or a provider adapter.
    from llm_gateway import load_persisted_llm_settings, decrypt_value
    expected = {"provider": "openai", "model": "recovery-no-call", "baseUrl": "http://127.0.0.1:9/v1"}
    if seed:
        call(client, "PUT", "/llm/settings", dict(expected, apiKey=key))
    result = call(client, "GET", "/llm/settings")
    require(all(result.get(k) == v for k, v in expected.items()))
    require(result.get("apiKeyConfigured") is True)
    require(result.get("apiKeyPreview") == key[:6] + "..." + key[-6:])
    persisted = load_persisted_llm_settings()
    require(all(persisted.get(k) == v for k, v in expected.items()))
    ciphertext = persisted.get("apiKey", "")
    require(bool(ciphertext) and ciphertext != key and key not in ciphertext)
    require(decrypt_value(ciphertext, env["LLM_MASTER_SECRET"]) == key)


class ProbeError(Exception):
    """Never contains response bodies, credentials or environment values."""


def require(condition):
    if not condition:
        raise ProbeError("recovery check failed")


def expected_notes(projects, source, content):
    title = next((line.strip()[2:].strip() for line in content.split("\n")
                  if line.strip().startswith("# ")), "README")
    return [{"project": project, "graph": "SpecGraph", "source": source,
             "noteId": hashlib.sha256(f"{project}:{source}".encode()).hexdigest()[:16],
             "title": title, "contentSha256": hashlib.sha256(content.encode()).hexdigest()}
            for project in projects]


def call(client, method, path, body=None, status=200, csrf=True):
    code, result = client.request(method, path, body, csrf=csrf)
    require(code == status)
    return result


def login(client, username, password, admin):
    result = call(client, "POST", "/auth/login", {"username": username, "password": password})
    require(result.get("username") == username and result.get("isAdmin") is admin and client.cookie)


def validate_state(state):
    require(isinstance(state, dict) and state.get("version") == 1)
    projects, notes = state.get("projects"), state.get("notes")
    require(isinstance(projects, list) and len(projects) == 2
            and all(isinstance(p, str) and p.startswith("dg-recovery-") and len(p) <= 64
                    and all(c.isalnum() or c == "-" for c in p) for p in projects)
            and len(set(projects)) == 2)
    require(isinstance(notes, list) and len(notes) == 2)
    for project, note in zip(projects, notes):
        require(isinstance(note, dict) and note.get("project") == project
                and note.get("source") == SOURCE and note.get("graph") == "SpecGraph")
        require(note.get("noteId") == hashlib.sha256(f"{project}:{SOURCE}".encode()).hexdigest()[:16])
        digest = note.get("contentSha256")
        require(isinstance(digest, str) and len(digest) == 64 and all(c in "0123456789abcdef" for c in digest))
        require(isinstance(note.get("title"), str))
    for key in ("username", "password", "revokedCookie", "llmKey"):
        require(isinstance(state.get(key), str) and 1 <= len(state[key]) <= 512)
    require(state["username"].startswith("recovery-"))


def check_user(client, state):
    me = call(client, "GET", "/auth/me")
    require(me.get("username") == state["username"] and me.get("isAdmin") is False)
    memberships = me.get("memberships", [])
    require([(m["project"], m["role"]) for m in memberships] == [(state["projects"][0], "viewer")])
    projects = call(client, "GET", "/projects").get("projects", [])
    require([(p["project"], p["role"]) for p in projects] == [(state["projects"][0], "viewer")])
    first, second = state["notes"]
    notes = call(client, "GET", "/knowledge/notes/" + first["project"])
    require(notes.get("project") == first["project"])
    require([n["noteId"] for n in notes.get("notes", [])] == [first["noteId"]])
    detail = call(client, "GET", "/knowledge/note/" + first["noteId"])
    require(detail.get("project") == first["project"] and detail.get("noteId") == first["noteId"])
    require(hashlib.sha256(detail["content"].encode()).hexdigest() == first["contentSha256"])
    call(client, "GET", "/knowledge/notes/" + second["project"], status=403)
    # Resource-scoped denial deliberately conceals existence (D-15).
    call(client, "GET", "/knowledge/note/" + second["noteId"], status=404)


def run(mode, *, env=None, client_factory=None, load_state=None, save_state=None,
        fixture_reader=None, graph_reader=None, llm_check=None):
    env = os.environ if env is None else env
    client_factory = client_factory or HTTPClient
    load_state = load_state or read_state
    save_state = save_state or write_state
    fixture_reader = fixture_reader or read_fixture
    graph_reader = graph_reader or (lambda notes: read_graph(notes, env))
    llm_check = llm_check or (lambda client, key, seed: check_llm(client, key, seed, env))
    require(mode in ("seed", "verify", "ready"))
    if mode == "ready":
        call(client_factory(), "GET", "/")
        read_graph_ready(env)
        return {"api_ready": True, "neo4j_ready": True}
    admin = client_factory()
    member = client_factory()
    primary_failed = False
    try:
        login(admin, env["DG_BOOTSTRAP_ADMIN_USER"], env["DG_BOOTSTRAP_ADMIN_PASSWORD"], True)
        if mode == "seed":
            require(load_state() is None)
            suffix = secrets.token_hex(8)
            projects = ["dg-recovery-" + suffix + "-a", "dg-recovery-" + suffix + "-b"]
            state = {"version": 1, "projects": projects, "username": "recovery-" + suffix,
                     "password": secrets.token_urlsafe(32), "llmKey": "synthetic-recovery-" + secrets.token_hex(24),
                     "notes": expected_notes(projects, SOURCE, fixture_reader())}
            for project in projects:
                result = call(admin, "POST", "/projects", {"project": project}, status=201)
                require(result.get("project") == project and result.get("role") == "owner")
                payload = {"project": project, "path": "hosted-ingest"}
                call(admin, "POST", "/knowledge/ingest/folder", payload, status=403, csrf=False)
                result = call(admin, "POST", "/knowledge/ingest/folder", payload)
                require(result.get("inserted") == 1 and result.get("skipped") == 0)
            invite = call(admin, "POST", "/auth/invites", {
                "username": state["username"], "project": projects[0], "role": "viewer"})
            require(invite.get("status") == "invited" and invite.get("inviteCode"))
            accepted = call(member, "POST", "/auth/accept-invite", {
                "inviteCode": invite["inviteCode"], "password": state["password"]})
            require(accepted.get("username") == state["username"] and accepted.get("isAdmin") is False)
            require(member.cookie)
            state["revokedCookie"] = member.cookie
            check_user(member, state)  # prove the session was valid before revocation
            call(member, "POST", "/auth/logout", status=204)
        else:
            state = load_state()
            validate_state(state)
        revoked = client_factory(cookie=state["revokedCookie"])
        call(revoked, "GET", "/auth/me", status=401)
        login(member, state["username"], state["password"], False)
        require(member.cookie != state["revokedCookie"])
        check_user(member, state)
        rows = graph_reader(state["notes"])
        require(sorted(rows, key=lambda n: n["project"]) == sorted(state["notes"], key=lambda n: n["project"]))
        llm_check(admin, state["llmKey"], mode == "seed")
        if mode == "seed":
            save_state(state)
        result = {"admin_login": True, "user_login": True, "membership_restored": True,
                  "project_isolation": True, "revoked_session_denied": True,
                  "neo4j_scoped_notes": 2, "llm_settings_decrypted": True}
        prefix = "" if mode == "seed" else "seed_"
        result.update({prefix + "projects_created": 2, prefix + "authenticated_ingests": 2,
                       prefix + "csrf_denied": True})
        return result
    except BaseException:
        primary_failed = True
        raise
    finally:
        logout_failed = False
        for client in (member, admin):
            if client.cookie:
                try:
                    call(client, "POST", "/auth/logout", status=204)
                except Exception:
                    logout_failed = True
        if logout_failed and not primary_failed:
            raise ProbeError("recovery check failed")


RESULT_KEYS = frozenset({"admin_login", "projects_created", "authenticated_ingests", "csrf_denied",
    "user_login", "membership_restored", "project_isolation", "revoked_session_denied",
    "neo4j_scoped_notes", "llm_settings_decrypted", "api_ready", "neo4j_ready",
    "seed_projects_created", "seed_authenticated_ingests", "seed_csrf_denied"})


def main(argv=None):
    import sys
    try:
        args = sys.argv[1:] if argv is None else argv
        require(len(args) == 1 and args[0] in ("ready", "seed", "verify"))
        result = run(args[0])
        require(isinstance(result, dict) and bool(result) and set(result) <= RESULT_KEYS)
        require(all(type(value) in (bool, int) for value in result.values()))
        print(json.dumps(result, sort_keys=True))
        return 0
    except Exception:
        print("recovery probe failed", file=sys.stderr)
        return 1


if __name__ == "__main__":
    import sys
    sys.exit(main())
