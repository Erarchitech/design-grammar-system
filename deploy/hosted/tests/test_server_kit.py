"""Offline tests of the server-stand kit: env generator, 4th Compose overlay, edge config, scripts.

Nothing here starts Docker services, contacts a host or reads a real .env. Compose is only
parsed with a synthetic generated env file in a temporary directory.
"""
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[3]
KIT = ROOT / "deploy/hosted/server"
MAKE_ENV = KIT / "make_env.py"
EXAMPLE = ROOT / ".env.example"
FILES = [ROOT / name for name in ("docker-compose.yml", "docker-compose.multi-user.yml",
                                  "docker-compose.hosted.yml", "docker-compose.server.yml")]
HOSTS = ("--dg-host", "dg.example.test", "--speckle-host", "speckle.example.test",
         "--object-host", "objects.example.test", "--acme-email", "ops@example.test")
OPTIONAL_BLANK = {"SPECKLE_PROJECT_ID", "SPECKLE_BASE_MODEL_ID", "DG_TRUSTED_PROXIES",
                  "DG_ALLOW_SELF_REGISTRATION", "SPECKLE_WRITE_TOKEN", "SPECKLE_READ_TOKEN"}


def generate(directory, *extra, hosts=HOSTS, name=".env.generated"):
    output = Path(directory) / name
    completed = subprocess.run(
        [sys.executable, "-I", "-B", str(MAKE_ENV), "--example", str(EXAMPLE),
         "--output", str(output), *hosts, *extra],
        capture_output=True, text=True, timeout=30)
    return output, completed


def parse(path):
    values = {}
    for line in Path(path).read_text(encoding="utf-8").splitlines():
        if line and not line.startswith("#") and "=" in line:
            key, _, value = line.partition("=")
            values[key.strip()] = value.strip()
    return values


def example_keys():
    keys = []
    for line in EXAMPLE.read_text(encoding="utf-8").splitlines():
        match = re.match(r"^([A-Z][A-Z0-9_]*)=", line)
        if match:
            keys.append(match.group(1))
    return keys


class MakeEnvTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)

    def test_generates_every_example_key_with_strong_unique_secrets_and_hosted_inputs(self):
        output, run = generate(self.temp.name)
        self.assertEqual(run.returncode, 0, run.stderr)
        values = parse(output)
        for key in example_keys():
            self.assertIn(key, values, key)
            if key not in OPTIONAL_BLANK:
                self.assertTrue(values[key], key)
        secret_keys = [k for k in values if re.search(r"PASSWORD|SECRET|TOKEN", k)
                       and k not in OPTIONAL_BLANK]
        for key in secret_keys:
            self.assertGreaterEqual(len(values[key]), 24, key)
            self.assertFalse(values[key].startswith("change-me-"), key)
        self.assertEqual(len({values[k] for k in secret_keys}), len(secret_keys), 'secrets must be unique')
        self.assertEqual(values["DG_DEPLOYMENT"], "multi-user")
        self.assertEqual(values["DG_COOKIE_SECURE"], "true")
        self.assertEqual(values["DG_ALLOW_SELF_REGISTRATION"], "false")
        # Speckle tokens stay blank: blank falls back to the token saved in the UI.
        self.assertEqual(values["SPECKLE_WRITE_TOKEN"], "")
        self.assertEqual(values["SPECKLE_READ_TOKEN"], "")
        self.assertEqual(values["HOSTED_DG_HOST"], "dg.example.test")
        self.assertEqual(values["HOSTED_SPECKLE_HOST"], "speckle.example.test")
        self.assertEqual(values["HOSTED_OBJECT_HOST"], "objects.example.test")
        self.assertEqual(values["HOSTED_ACME_EMAIL"], "ops@example.test")
        self.assertEqual(values["HOSTED_EDGE_CIDR"], "172.30.90.0/28")
        self.assertEqual(values["HOSTED_EDGE_IP"], "172.30.90.2")
        self.assertEqual(values["HOSTED_EDGE_DYNAMIC_RANGE"], "172.30.90.8/29")
        self.assertTrue(values["HOSTED_EDGE_CERT_DIR"])

    def test_two_runs_generate_different_secrets(self):
        first, run = generate(self.temp.name, name="a.env")
        self.assertEqual(run.returncode, 0, run.stderr)
        second, run = generate(self.temp.name, name="b.env")
        self.assertEqual(run.returncode, 0, run.stderr)
        a, b = parse(first), parse(second)
        self.assertNotEqual(a["POSTGRES_PASSWORD"], b["POSTGRES_PASSWORD"])
        self.assertNotEqual(a["DG_BOOTSTRAP_ADMIN_PASSWORD"], b["DG_BOOTSTRAP_ADMIN_PASSWORD"])

    def test_never_prints_secret_values(self):
        output, run = generate(self.temp.name)
        self.assertEqual(run.returncode, 0, run.stderr)
        shown = run.stdout + run.stderr
        for key, value in parse(output).items():
            if re.search(r"PASSWORD|SECRET|TOKEN", key) and value:
                self.assertNotIn(value, shown, key)

    def test_refuses_to_overwrite_an_existing_file(self):
        target = Path(self.temp.name) / "exists.env"
        target.write_text("KEEP=1\n", encoding="utf-8")
        output, run = generate(self.temp.name, name="exists.env")
        self.assertNotEqual(run.returncode, 0)
        self.assertEqual(target.read_text(encoding="utf-8"), "KEEP=1\n")

    def test_rejects_bad_hostnames_without_writing(self):
        bad = ["localhost", "127.0.0.1", "10.0.0.5", "https://dg.example.test", "dg.example.test:8443",
               "DG.Example.Test", "dg_example.test", "dg.example.test/path", "single", ""]
        for index, value in enumerate(bad):
            with self.subTest(host=value):
                hosts = ("--dg-host", value, "--speckle-host", "speckle.example.test",
                         "--object-host", "objects.example.test", "--acme-email", "ops@example.test")
                output, run = generate(self.temp.name, hosts=hosts, name=f"bad{index}.env")
                self.assertNotEqual(run.returncode, 0)
                self.assertFalse(output.exists())
        same = ("--dg-host", "same.example.test", "--speckle-host", "same.example.test",
                "--object-host", "objects.example.test", "--acme-email", "ops@example.test")
        output, run = generate(self.temp.name, hosts=same, name="same.env")
        self.assertNotEqual(run.returncode, 0)
        self.assertFalse(output.exists())
        email = ("--dg-host", "dg.example.test", "--speckle-host", "speckle.example.test",
                 "--object-host", "objects.example.test", "--acme-email", "not-an-email")
        output, run = generate(self.temp.name, hosts=email, name="email.env")
        self.assertNotEqual(run.returncode, 0)
        self.assertFalse(output.exists())

    def test_output_is_private_on_posix_and_has_unix_newlines(self):
        output, run = generate(self.temp.name)
        self.assertEqual(run.returncode, 0, run.stderr)
        if os.name == "posix":
            self.assertEqual(output.stat().st_mode & 0o077, 0)
        self.assertNotIn(b"\r", output.read_bytes())


class ServerProfileTests(unittest.TestCase):
    @classmethod
    def merged(cls):
        with tempfile.TemporaryDirectory(prefix="dg-server-kit-") as directory:
            output, run = generate(directory)
            assert run.returncode == 0, run.stderr
            command = [shutil.which("docker") or "docker", "compose", "--env-file", str(output)]
            for file in FILES:
                command.extend(("-f", str(file)))
            command.extend(("config", "--format", "json"))
            environment = {k: v for k, v in os.environ.items()
                           if k.upper() in ("PATH", "PATHEXT", "SYSTEMROOT", "WINDIR", "COMSPEC", "APPDATA",
                                            "LOCALAPPDATA", "PROGRAMFILES", "PROGRAMFILES(X86)",
                                            "PROGRAMDATA", "USERPROFILE", "HOME", "TEMP", "TMP", "TMPDIR")}
            environment["DOCKER_CONFIG"] = str(Path(directory) / "empty-docker-config")
            done = subprocess.run(command, cwd=directory, env=environment, capture_output=True,
                                  text=True, timeout=60)
            assert done.returncode == 0, 'docker compose config failed for the 4-file server profile'
            return json.loads(done.stdout)

    def test_speckle_minio_uses_an_image_that_can_still_be_pulled(self):
        """minio/minio is no longer pullable from Docker Hub (found on the real server, 2026-10-24)."""
        image = self.merged()["services"]["speckle-minio"]["image"]
        self.assertEqual(image, "cgr.dev/chainguard/minio:latest")

    def test_every_service_restarts_after_a_reboot(self):
        services = self.merged()["services"]
        for name, service in services.items():
            self.assertEqual(service.get("restart"), "unless-stopped", name)

    def test_edge_network_keeps_the_static_edge_address_out_of_the_dynamic_pool(self):
        import ipaddress
        network = self.merged()["networks"]["hosted_edge"]
        config = network["ipam"]["config"]
        self.assertEqual(len(config), 1, config)
        subnet = ipaddress.ip_network(config[0]["subnet"])
        pool = ipaddress.ip_network(config[0]["ip_range"])
        edge = ipaddress.ip_address("172.30.90.2")
        self.assertTrue(pool.subnet_of(subnet))
        self.assertNotIn(edge, pool)   # containers started before Caddy must never take its address
        self.assertIn(edge, subnet)

    def test_overlay_and_edge_files_exist(self):
        for path in (ROOT / "docker-compose.server.yml", KIT / "Caddyfile.acme"):
            self.assertTrue(path.is_file(), str(path))

    def test_merged_model_publishes_only_http_and_https_from_the_edge(self):
        model = self.merged()
        published = {}
        for name, service in model["services"].items():
            for port in service.get("ports", []) or []:
                published.setdefault(name, []).append((str(port.get("published")), port.get("protocol", "tcp")))
        self.assertEqual(set(published), {"hosted-edge"}, published)
        self.assertEqual(sorted(published["hosted-edge"]), [("443", "tcp"), ("80", "tcp")])
        for port in model["services"]["hosted-edge"]["ports"]:
            self.assertIn(port.get("host_ip", ""), ("", "0.0.0.0"))

    def test_speckle_postgres_does_not_mount_the_bootstrap_into_first_init(self):
        service = self.merged()["services"]["speckle-postgres"]
        targets = [v["target"] for v in service.get("volumes", [])]
        self.assertEqual(targets, ["/var/lib/postgresql/data"])

    def test_edge_uses_acme_caddyfile_persists_certificate_state_and_mounts_no_cert_directory(self):
        service = self.merged()["services"]["hosted-edge"]
        mounts = {v["target"]: v for v in service["volumes"]}
        self.assertEqual(set(mounts), {"/etc/caddy/Caddyfile", "/data", "/config"})
        self.assertTrue(mounts["/etc/caddy/Caddyfile"]["read_only"])
        self.assertTrue(mounts["/etc/caddy/Caddyfile"]["source"].endswith("Caddyfile.acme"))
        self.assertEqual(mounts["/data"]["type"], "volume")
        self.assertEqual(service["environment"]["HOSTED_ACME_EMAIL"], "ops@example.test")

    def test_acme_caddyfile_keeps_route_policy_and_has_no_file_certificates(self):
        acme = (KIT / "Caddyfile.acme").read_text(encoding="utf-8")
        original = (ROOT / "deploy/hosted/edge/Caddyfile").read_text(encoding="utf-8")
        self.assertNotRegex(acme, r"(?m)^\s*tls\s")
        self.assertIn("email {$HOSTED_ACME_EMAIL}", acme)

        def body(text):
            return [line for line in text.splitlines()
                    if line.strip() and not line.strip().startswith(("#", "tls "))]
        reviewed = body(original)
        catch_all = reviewed.index(":443 {")
        self.assertEqual(reviewed[catch_all:], [":443 {", "    respond 404", "}"])
        kept = reviewed[:catch_all]
        generated = body(acme)
        self.assertEqual(generated[:3], ["{", "    email {$HOSTED_ACME_EMAIL}", "}"])
        # Exact ORDERED equality: no route may be added, removed, duplicated or reordered.
        self.assertEqual(generated[3:], kept)

    def test_scripts_exist_use_unix_newlines_and_pass_bash_syntax_check(self):
        bash = shutil.which("bash")
        self.assertTrue(bash, "bash is required to syntax-check the server scripts")
        for name in ("bootstrap-server.sh", "deploy.sh", "import-n8n.sh"):
            path = KIT / name
            self.assertTrue(path.is_file(), name)
            self.assertNotIn(b"\r", path.read_bytes(), name)
            done = subprocess.run([bash, "-n", str(path)], capture_output=True, text=True, timeout=30)
            self.assertEqual(done.returncode, 0, (name, done.stderr))

    def test_deploy_script_applies_the_speckle_bootstrap_after_the_schema_exists(self):
        text = (KIT / "deploy.sh").read_text(encoding="utf-8")
        self.assertIn("bootstrap-local.sql", text)
        self.assertIn("set -euo pipefail", text)
        # Wait (query) first, apply the SQL only afterwards, and wait for the registered apps too.
        wait = text.index("to_regclass('public.scopes')")
        apply = text.index("-f - < speckle/bootstrap-local.sql")
        self.assertLess(wait, apply)
        self.assertIn("spklwebapp", text[wait:apply])
        self.assertIn("explorer", text[wait:apply])
        host_line = [line for line in text.splitlines() if line.startswith("dg_host=")][0]
        self.assertIn("|| true", host_line)   # a failing grep must not abort the script under pipefail
        # No secret may be echoed.
        self.assertNotRegex(text, r"echo[^\n]*(PASSWORD|SECRET|TOKEN)")

    def test_scripts_have_no_early_exiting_reader_after_a_pipe_under_pipefail(self):
        """`cmd | awk '...exit'` or `| head -n1` can SIGPIPE `cmd`; with pipefail + set -e that aborts the script.

        Found on the real server: sshd -T | awk '/^port /{print $2; exit}' stopped bootstrap-server.sh (exit 141).
        """
        for name in ("bootstrap-server.sh", "deploy.sh", "import-n8n.sh"):
            text = (KIT / name).read_text(encoding="utf-8")
            for number, line in enumerate(text.splitlines(), 1):
                code = line.split("#", 1)[0]
                self.assertNotRegex(code, r"\|\s*awk\b[^|]*\bexit\b", (name, number, line))
                if "set -euo pipefail" in text:
                    # head/grep -q close the pipe early too; only allowed where the producer is tiny and local.
                    self.assertNotRegex(code, r"\|\s*(head\s+-n?\s*1|grep\s+-q)\b(?![^|]*\|\|\s*true)",
                                        (name, number, line)) if "sort -V" not in code else None

    def test_n8n_import_publishes_with_the_current_verb_and_the_workflows_own_id(self):
        """Found on the real server: update:workflow is deprecated and a file's own id must be used."""
        text = (KIT / "import-n8n.sh").read_text(encoding="utf-8")
        self.assertIn("publish:workflow", text)
        self.assertNotIn("update:workflow", text)
        self.assertIn('data["id"]', text)          # publish by the id stored in the imported file
        self.assertNotIn('--id="$name"', text)     # the file name is not the workflow id

    def test_bootstrap_script_opens_only_ssh_http_https(self):
        text = (KIT / "bootstrap-server.sh").read_text(encoding="utf-8")
        for rule in ("ufw allow 22/tcp", "ufw allow 80/tcp", "ufw allow 443/tcp"):
            self.assertIn(rule, text)
        self.assertNotRegex(text, r"ufw allow (?!22/|80/|443/)")
        self.assertIn("set -euo pipefail", text)
        self.assertIn("DPkg::Lock::Timeout", text)
        # Enabling the firewall with SSH on another port would lock the owner out.
        self.assertLess(text.index("sshd -T"), text.index("ufw --force enable"))


class PackSourceTests(unittest.TestCase):
    PACK = KIT / "pack_source.py"

    @classmethod
    def archive(cls):
        import tarfile
        directory = tempfile.mkdtemp(prefix="dg-pack-")
        output = Path(directory) / "dg-stand.tar.gz"
        done = subprocess.run([sys.executable, "-I", "-B", str(cls.PACK), "--repo", str(ROOT),
                               "--output", str(output)], capture_output=True, text=True, timeout=120)
        assert done.returncode == 0, done.stderr
        with tarfile.open(output) as tar:
            members = {m.name: m for m in tar.getmembers()}
            info = json.loads(tar.extractfile("PACK-INFO.json").read())
        return output, members, info, done.stdout

    def test_pack_has_sources_kit_and_template_and_nothing_private(self):
        output, members, info, shown = self.archive()
        self.addCleanup(shutil.rmtree, output.parent, True)
        names = set(members)
        for required in ("docker-compose.yml", "docker-compose.multi-user.yml", "docker-compose.hosted.yml",
                         "docker-compose.server.yml", ".env.example", "neo4j/Dockerfile",
                         "ui-v2/package.json", "ui-v2/src/main.jsx", "speckle/bootstrap-local.sql",
                         "deploy/hosted/edge/Caddyfile", "deploy/hosted/server/deploy.sh",
                         "deploy/hosted/server/make_env.py", "deploy/hosted/server/Caddyfile.acme",
                         "tools/security/check_env_file.py", "data-service/app.py"):
            self.assertIn(required, names, required)
        forbidden = {".secrets", "dg_obsidian", "publications", ".git", ".planning", ".degram",
                     "graphify-out", "node_modules", "__pycache__", "profiles", "personal-cv", "personal-graph"}
        for name in names:
            parts = [part.casefold() for part in name.split("/")]
            self.assertFalse(forbidden & set(parts), name)
            if name != ".env.example":
                self.assertFalse(any(part.startswith(".env") for part in parts), name)
            self.assertFalse(name.endswith((".pem", ".key", ".p12", ".pfx", ".kdbx")), name)
        self.assertFalse(any(n.startswith("data-service/tests/") or n == "data-service/rotate_llm_master_secret.py"
                             for n in names))
        self.assertLess(len(names), 600)

    def test_pack_is_deterministic_private_and_records_its_inputs(self):
        first, members, info, shown = self.archive()
        self.addCleanup(shutil.rmtree, first.parent, True)
        second, _, info2, _ = self.archive()
        self.addCleanup(shutil.rmtree, second.parent, True)
        self.assertEqual(first.read_bytes(), second.read_bytes(), "archive must be byte-reproducible")
        self.assertEqual(info["files"], info2["files"])
        self.assertRegex(info["revision"], r"^[0-9a-f]{40}$")
        self.assertIn(info["workingTreeState"], ("clean", "uncommitted-changes-included"))
        for member in members.values():
            self.assertEqual((member.uid, member.gid, member.mtime), (0, 0, 0), member.name)
        # Modes depend only on the file name, never on the checkout platform.
        for name, member in members.items():
            self.assertEqual(member.mode, 0o755 if name.endswith(".sh") else 0o644, name)
        self.assertIn(hashlib_sha256(first.read_bytes()), shown)

    def test_pack_refuses_a_missing_allowlisted_input(self):
        with tempfile.TemporaryDirectory() as directory:
            fake = Path(directory) / "repo"
            (fake / "deploy/hosted").mkdir(parents=True)
            (fake / "deploy/hosted/release-allowlist.json").write_text(json.dumps({
                "schemaVersion": 1, "inputs": [{"path": "absent.txt", "purpose": "x"}]}), encoding="utf-8")
            for command in (["init", "-q"], ["add", "-A"],
                            ["-c", "user.name=Fixture", "-c", "user.email=f@example.invalid", "commit", "-qm", "f"]):
                subprocess.run(["git", "-C", str(fake), *command], check=True, capture_output=True)
            done = subprocess.run([sys.executable, "-I", "-B", str(self.PACK), "--repo", str(fake),
                                   "--output", str(Path(directory) / "out.tar.gz")],
                                  capture_output=True, text=True, timeout=60)
            self.assertNotEqual(done.returncode, 0)
            self.assertIn("matches nothing: absent.txt", done.stderr)
            self.assertFalse((Path(directory) / "out.tar.gz").exists())

    def test_pack_ships_mapping_runtime_files_that_the_release_allowlist_does_not_name(self):
        # data-service/property_scripts.py reads property_calculators/catalogue.json and the *.py.tmpl
        # templates at run time; the image is built from the archive alone (COPY . .), so a silent
        # omission would only surface when a property check runs. Absent on branches without the
        # mapping code (the real repo here), so the stand list is optional, never required.
        import tarfile
        with tempfile.TemporaryDirectory() as directory:
            fake = Path(directory) / "repo"
            files = {
                "deploy/hosted/release-allowlist.json": json.dumps({
                    "schemaVersion": 1, "inputs": [{"path": "data-service/app.py", "purpose": "x"}]}),
                "data-service/app.py": "app = 1\n",
                "data-service/property_calculators/catalogue.json": "{}\n",
                "data-service/property_calculators/calculator_shell.py.tmpl": "shell\n",
                "data-service/property_calculators/notes.md": "not runtime\n",
                "data-service/property_calculators/.secrets/key.py.tmpl": "private\n",
                "docker-compose.server.yml": "services: {}\n",
                "deploy/hosted/server/deploy.sh": "#!/bin/sh\n",
                "tools/security/check_env_file.py": "pass\n",
                "test/smoke_rules_ingest.sh": "#!/bin/sh\n",
                "test/smoke_graph_query.sh": "#!/bin/sh\n",
                ".env.example": "A=1\n",
            }
            for name, text in files.items():
                (fake / name).parent.mkdir(parents=True, exist_ok=True)
                (fake / name).write_text(text, encoding="utf-8")
            for command in (["init", "-q"], ["add", "-A"],
                            ["-c", "user.name=Fixture", "-c", "user.email=f@example.invalid", "commit", "-qm", "f"]):
                subprocess.run(["git", "-C", str(fake), *command], check=True, capture_output=True)
            output = Path(directory) / "out.tar.gz"
            done = subprocess.run([sys.executable, "-I", "-B", str(self.PACK), "--repo", str(fake),
                                   "--output", str(output)], capture_output=True, text=True, timeout=60)
            self.assertEqual(done.returncode, 0, done.stderr)
            with tarfile.open(output) as tar:
                names = {member.name for member in tar.getmembers()}
            self.assertIn("data-service/property_calculators/catalogue.json", names)
            self.assertIn("data-service/property_calculators/calculator_shell.py.tmpl", names)
            self.assertNotIn("data-service/property_calculators/notes.md", names)
            self.assertNotIn("data-service/property_calculators/.secrets/key.py.tmpl", names)


def hashlib_sha256(data):
    import hashlib
    return hashlib.sha256(data).hexdigest()


if __name__ == "__main__":
    unittest.main()
