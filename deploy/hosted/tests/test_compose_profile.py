"""Offline structural checks of the effective local and hosted Compose models."""

import json
import os
from pathlib import Path
import subprocess
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


def model(*files):
    with tempfile.TemporaryDirectory(prefix="dg-compose-profile-") as directory:
        fixture = Path(directory) / "fixture.env"
        fixture.write_text(FIXTURE, encoding="utf-8")
        command = ["docker", "compose", "--env-file", str(fixture)]
        for file in files:
            command.extend(("-f", str(file)))
        command.extend(("config", "--no-interpolate", "--format", "json"))
        # Keep cwd outside the repository so an implicit repo .env cannot be read.
        # Remove inherited project and variable overrides without affecting PATH/Docker CLI.
        environment = {
            key: value for key, value in os.environ.items()
            if not key.startswith(("COMPOSE_", "OLLAMA_", "DG_", "NEO4J_", "N8N_", "SPECKLE_", "MINIO_"))
            and key not in ("POSTGRES_PASSWORD", "LLM_MASTER_SECRET")
        }
        completed = subprocess.run(
            command, cwd=directory, env=environment, capture_output=True,
            text=True, check=False, timeout=30,
        )
        if completed.returncode:
            # Do not echo potentially expanded configuration or credentials.
            raise AssertionError(
                f"docker compose config failed (exit={completed.returncode}); "
                "verify Compose availability, parser support and sanitized fixture"
            )
        return json.loads(completed.stdout)


def dependencies(service):
    depends_on = service.get("depends_on") or {}
    return set(depends_on if isinstance(depends_on, (dict, list)) else [])


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
        self.assertEqual(set(services), set(local["services"]) - {"ollama"})
        self.assertNotIn("ollama", hosted.get("volumes", {}))
        self.assertEqual(dependencies(services["n8n"]), {"data-service"})
        for name, service in services.items():
            with self.subTest(service=name):
                self.assertFalse(dependencies(service) - services.keys(), "dangling depends_on")
                devices = (service.get("deploy", {}).get("resources", {})
                           .get("reservations", {}).get("devices", []))
                self.assertFalse(devices, "hosted reservation devices are forbidden")
                for port in service.get("ports", []):
                    self.assertEqual(port.get("host_ip"), "127.0.0.1", "unintended public port")
        for key in ("OLLAMA_URL", "OLLAMA_HOST", "OLLAMA_MODEL"):
            self.assertNotIn(key, services["n8n"].get("environment", {}))


if __name__ == "__main__":
    unittest.main()
