"""Offline structural checks of the effective local and hosted Compose models."""

import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[3]
BASE = ROOT / "docker-compose.yml"
MULTI_USER = ROOT / "docker-compose.multi-user.yml"
HOSTED = ROOT / "docker-compose.hosted.yml"
# No real .env or process credentials are used. Compose only parses, never starts.
FIXTURE = "\n".join(
    f"{key}=fixture-{key.lower()}"
    for key in (
        "NEO4J_PASSWORD", "LLM_MASTER_SECRET", "DG_SERVICE_TOKEN",
        "DG_BOOTSTRAP_ADMIN_USER", "DG_BOOTSTRAP_ADMIN_PASSWORD",
        "N8N_USER", "N8N_PASSWORD", "POSTGRES_PASSWORD",
        "MINIO_ROOT_USER", "MINIO_ROOT_PASSWORD", "SPECKLE_SESSION_SECRET",
    )
) + "\n"


HOSTED_INPUTS = {
    "HOSTED_DG_HOST": "dg.example.invalid",
    "HOSTED_SPECKLE_HOST": "speckle.example.invalid",
    "HOSTED_OBJECT_HOST": "objects.example.invalid",
    "HOSTED_EDGE_CIDR": "172.30.90.0/28",
    "HOSTED_EDGE_IP": "172.30.90.2",
    "HOSTED_EDGE_CERT_DIR": "C:/synthetic-edge-certs",
}


def compose_result(*files, interpolate=False, overrides=None):
    with tempfile.TemporaryDirectory(prefix="dg-compose-profile-") as directory:
        fixture = Path(directory) / "fixture.env"
        fixture.write_text(FIXTURE + "".join(
            f"{key}={value}\n" for key, value in
            ((HOSTED_INPUTS if overrides is None else overrides).items())
        ), encoding="utf-8")
        command = [shutil.which("docker") or "docker", "compose", "--env-file", str(fixture)]
        for file in files:
            command.extend(("-f", str(file)))
        command.extend(("config", "--format", "json"))
        if not interpolate:
            command.append("--no-interpolate")
        # Keep cwd outside repository and scrub interpolation/Compose variables.
        # Allow only OS/toolchain variables; no real .env or process credentials.
        environment = {
            key: value for key, value in os.environ.items()
            if key.upper() in ("PATH", "PATHEXT", "SYSTEMROOT", "WINDIR", "COMSPEC",
                               "APPDATA", "LOCALAPPDATA", "PROGRAMFILES", "PROGRAMFILES(X86)",
                               "PROGRAMDATA", "USERPROFILE", "HOME", "TEMP", "TMP", "TMPDIR")
        }
        environment["DOCKER_CONFIG"] = str(Path(directory) / "empty-docker-config")
        completed = subprocess.run(
            command, cwd=directory, env=environment, capture_output=True,
            text=True, check=False, timeout=30,
        )
        return completed


def model(*files):
    completed = compose_result(*files)
    if completed.returncode:
        raise AssertionError("docker compose config failed; sanitized structural fixture")
    return json.loads(completed.stdout)


def dependencies(service):
    depends_on = service.get("depends_on") or {}
    return set(depends_on if isinstance(depends_on, (dict, list)) else [])


def environment_map(service):
    entries = service.get("environment") or {}
    if isinstance(entries, list):
        return dict(entry.split("=", 1) for entry in entries)
    return entries


class ComposeProfileTests(unittest.TestCase):
    def test_local_two_file_model_retains_ollama_and_dependency(self):
        local = model(BASE, MULTI_USER)
        self.assertIn("ollama", local["services"])
        self.assertIn("ollama", local["volumes"])
        self.assertIn("ollama", dependencies(local["services"]["n8n"]))
        self.assertIn("data-service", dependencies(local["services"]["n8n"]))
        self.assertIn("OLLAMA_URL", local["services"]["n8n"]["environment"])

    def test_hosted_model_excludes_ollama_and_preserves_graph(self):
        self.assertTrue(HOSTED.is_file(), "hosted overlay absent: create docker-compose.hosted.yml")
        local = model(BASE, MULTI_USER)
        hosted = model(BASE, MULTI_USER, HOSTED)
        services = hosted["services"]
        # Расширение графа только явным TLS edge; все прежние не-Ollama сервисы остаются.
        self.assertEqual(set(services), (set(local["services"]) - {"ollama"}) | {"hosted-edge"})
        self.assertNotIn("ollama", hosted.get("volumes", {}))
        self.assertEqual(dependencies(services["n8n"]), {"data-service"})
        for name, service in services.items():
            with self.subTest(service=name):
                self.assertFalse(dependencies(service) - services.keys(), "dangling depends_on")
                devices = (service.get("deploy", {}).get("resources", {})
                           .get("reservations", {}).get("devices", []))
                self.assertFalse(devices, "hosted reservation devices are forbidden")
                self.assertNotIn("nvidia", str(service.get("runtime", "")).lower())
                self.assertFalse(service.get("gpus"), "hosted GPU allocation is forbidden")
                self.assertFalse(
                    set(service.get("environment", {})) & {"OLLAMA_URL", "OLLAMA_HOST", "OLLAMA_MODEL"},
                    "hosted Ollama environment is forbidden",
                )
                for mount in service.get("volumes", []):
                    self.assertNotEqual(mount.get("source"), "ollama")
                for port in service.get("ports", []):
                    self.assertEqual(port.get("host_ip"), "127.0.0.1", "unintended public port")
        for key in ("OLLAMA_URL", "OLLAMA_HOST", "OLLAMA_MODEL"):
            self.assertNotIn(key, services["n8n"].get("environment", {}))

    def test_hosted_edge_wiring_origins_and_port_boundary(self):
        hosted = model(BASE, MULTI_USER, HOSTED)
        services = hosted["services"]
        self.assertEqual(
            {name: service.get("ports") for name, service in services.items() if service.get("ports")},
            {"hosted-edge": [{"mode": "ingress", "host_ip": "127.0.0.1", "target": 443,
                               "published": "443", "protocol": "tcp"}]},
        )
        edge = services["hosted-edge"]
        self.assertIn("hosted_edge", edge["networks"])
        self.assertEqual(set(services["design-grammars"]["networks"]), {"default", "hosted_edge"})
        self.assertEqual(set(services["speckle-ingress"]["networks"]), {"default", "hosted_edge"})
        self.assertEqual(set(services["speckle-minio"]["networks"]), {"default", "hosted_edge"})
        self.assertEqual(edge["environment"]["HOSTED_DG_HOST"],
                         "${HOSTED_DG_HOST:?set approved DG DNS hostname}")
        self.assertEqual(edge["environment"]["HOSTED_SPECKLE_HOST"],
                         "${HOSTED_SPECKLE_HOST:?set approved Speckle DNS hostname}")
        self.assertEqual(edge["environment"]["HOSTED_OBJECT_HOST"],
                         "${HOSTED_OBJECT_HOST:?set approved distinct object DNS hostname}")
        mounts = {item["target"]: item for item in edge["volumes"]}
        self.assertTrue(mounts["/etc/caddy/Caddyfile"]["read_only"])
        self.assertTrue(mounts["/etc/caddy/certs"]["read_only"])
        self.assertTrue(mounts["/etc/caddy/certs"]["source"].startswith("${HOSTED_EDGE_CERT_DIR:?"))
        self.assertEqual(hosted["networks"]["hosted_edge"]["enable_ipv6"], False)
        self.assertTrue(hosted["networks"]["hosted_edge"]["ipam"]["config"][0]["subnet"].startswith(
            "${HOSTED_EDGE_CIDR:?"))
        ds = environment_map(services["data-service"])
        ui = environment_map(services["design-grammars"])
        server = environment_map(services["speckle-server"])
        frontend = environment_map(services["speckle-frontend-2"])
        self.assertEqual(ds["DG_COOKIE_SECURE"], "true")
        self.assertEqual(ds["DG_TRUSTED_PROXIES"], ui["DG_TRUSTED_PROXIES"])
        self.assertEqual(ds["DG_TRUSTED_PROXIES"], "${HOSTED_EDGE_IP:?set actual private Caddy IPv4}/32")
        dg_origin = "https://${HOSTED_DG_HOST:?set approved DG DNS hostname}"
        speckle_origin = "https://${HOSTED_SPECKLE_HOST:?set approved Speckle DNS hostname}"
        object_origin = "https://${HOSTED_OBJECT_HOST:?set approved distinct object DNS hostname}"
        self.assertEqual(ds["DG_BASE_URL"], dg_origin)
        for value in (ds["SPECKLE_BASE_URL"], ui["SPECKLE_BASE_URL"],
                      server["CANONICAL_URL"], server["FRONTEND_ORIGIN"],
                      frontend["NUXT_PUBLIC_API_ORIGIN"], frontend["NUXT_PUBLIC_BASE_URL"]):
            self.assertEqual(value, speckle_origin)
        self.assertEqual(server["S3_PUBLIC_ENDPOINT"], object_origin)
        self.assertEqual(server["S3_ENDPOINT"], "http://speckle-minio:9000")

    def test_required_runner_rejects_zero_tests_and_skips(self):
        runner = Path(__file__).with_name("run_required.py")
        with tempfile.TemporaryDirectory(prefix="dg-required-tests-") as directory:
            copy = Path(directory) / "run_required.py"
            copy.write_bytes(runner.read_bytes())
            for name, source in (
                ("test_empty.py", "# deliberately no tests\n"),
                ("test_skip.py", "import unittest\nclass Skipped(unittest.TestCase):\n"
                 "    @unittest.skip('required')\n    def test_required(self): pass\n"),
            ):
                (Path(directory) / name).write_text(source, encoding="utf-8")
                result = subprocess.run([sys.executable, str(copy), name],
                                        capture_output=True, text=True, check=False)
                self.assertNotEqual(result.returncode, 0, name)


if __name__ == "__main__":
    unittest.main()
