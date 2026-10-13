"""Offline, sanitized Compose interpolation policy checks (never starts an edge)."""
import ipaddress
import json
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest

from test_compose_profile import (BASE, MULTI_USER, HOSTED, HOSTED_INPUTS,
                                  compose_result, environment_map)


def check_hosted(model):
    services = model["services"]
    edge = services["hosted-edge"]
    origins = [environment_map(services["data-service"])["DG_BASE_URL"],
               environment_map(services["data-service"])["SPECKLE_BASE_URL"],
               environment_map(services["speckle-server"])["S3_PUBLIC_ENDPOINT"]]
    hosts = []
    for origin in origins:
        if not origin.startswith("https://") or origin.count("://") != 1:
            raise ValueError("external origin must use HTTPS")
        host = origin[len("https://"):]
        if (not host or any(c in host for c in "/:@?# ") or "." not in host
                or host.startswith(".") or host.endswith(".") or host.lower() == "localhost"
                or host.lower().endswith(".localhost")):
            raise ValueError("external origin must be a DNS hostname without port/path")
        try:
            ipaddress.ip_address(host)
        except ValueError:
            pass
        else:
            raise ValueError("external origin cannot be an IP address")
        hosts.append(host.lower())
    if len(set(hosts)) != 3 or [edge["environment"][key].lower() for key in
                               ("HOSTED_DG_HOST", "HOSTED_SPECKLE_HOST", "HOSTED_OBJECT_HOST")] != hosts:
        raise ValueError("distinct hostname/origin mismatch")
    ds = environment_map(services["data-service"])
    ui = environment_map(services["design-grammars"])
    if ds["DG_COOKIE_SECURE"] != "true":
        raise ValueError("insecure cookie")
    ip = ipaddress.ip_address(edge["networks"]["hosted_edge"]["ipv4_address"])
    cidr = ipaddress.ip_network(model["networks"]["hosted_edge"]["ipam"]["config"][0]["subnet"])
    if ip.version != 4 or not ip.is_private or ip not in cidr or not cidr.is_private:
        raise ValueError("edge must occupy a private IPv4 subnet")
    if ds["DG_TRUSTED_PROXIES"] != f"{ip}/32" or ui["DG_TRUSTED_PROXIES"] != f"{ip}/32":
        raise ValueError("proxy trust must name only actual edge IP")
    ports = [(name, p.get("host_ip"), p.get("published"), p.get("target"), p.get("protocol"))
             for name, service in services.items() for p in service.get("ports", [])]
    if ports != [("hosted-edge", "127.0.0.1", "443", 443, "tcp")]:
        raise ValueError("unexpected published ports")
    if environment_map(services["speckle-server"])["S3_ENDPOINT"] != "http://speckle-minio:9000":
        raise ValueError("internal S3 endpoint drift")


class EdgeFixtureMachineTests(unittest.TestCase):
    def test_owner_report_machine_matches_package_guard(self):
        edge = Path(__file__).resolve().parents[1] / "edge"
        # Owner's preflight report is the source of truth: O, not zero, after the hyphen.
        actual = "DESKTOP-OS4Q8CP"
        mistaken = "DESKTOP-0S4Q8CP"
        for name in ("Run-Edge-Test.ps1", "build_test_zip.py", "TEST-PACKAGE.md"):
            with self.subTest(name=name):
                text = (edge / name).read_text(encoding="utf-8")
                self.assertIn(actual, text)
                self.assertNotIn(mistaken, text)
    def test_fixture_failure_report_identifies_stage_without_exception_text(self):
        edge = Path(__file__).resolve().parents[1] / "edge"
        script = (edge / "Run-Edge-Test.ps1").read_text(encoding="utf-8")
        self.assertIn("$stage = 'preflight'", script)
        for stage in ("rewrite", "validate", "ports", "upstreams", "proxy", "routes"):
            with self.subTest(stage=stage):
                self.assertIn("$stage = '" + stage + "'", script)
        self.assertIn("stage=$stage", script)
        self.assertNotIn("message=$_.Exception.Message", script)

    def test_fixture_preflight_reaches_loopback_assertion(self):
        powershell = shutil.which("powershell.exe")
        if not powershell:
            self.skipTest("Windows PowerShell required for this Windows fixture regression")
        edge = Path(__file__).resolve().parents[1] / "edge"
        # Execute the exact source transformation on Windows PowerShell without
        # starting Caddy or opening a socket. Parse-only checks miss runtime operators.
        script = (edge / "Run-Edge-Test.ps1").read_text(encoding="utf-8")
        start = script.index("    $replacements = [ordered]@{")
        end = script.index("    # Explicit origins only;", start)
        excerpt = script[start:end]
        excerpt = excerpt.replace("    Assert-Result 'four-loopback-binds' ",
                                  "    if (-not ", 1)
        excerpt = excerpt.replace("-and $tls.Count -eq 4)\n", "-and $tls.Count -eq 4)) { throw 'loopback-binds-failed' }\n", 1)
        with tempfile.TemporaryDirectory(prefix="dg-edge-repro-") as directory:
            probe = Path(directory) / "probe.ps1"
            probe.write_text("$ErrorActionPreference = 'Stop'\n" +
                             "function Assert-Result([string]$name, [bool]$ok) { if (-not $ok) { throw $name } }\n" +
                             "$root = " + "'" + str(edge).replace("'", "''") + "'\n" +
                             "$source = [System.IO.File]::ReadAllText((Join-Path $root 'Caddyfile'))\n" +
                             excerpt + "Write-Output 'LOOPBACK_PREFLIGHT_OK'\n", encoding="utf-8")
            result = subprocess.run([powershell, "-NoProfile", "-ExecutionPolicy", "Bypass",
                                     "-File", str(probe)], capture_output=True, text=True,
                                    encoding="utf-8", errors="replace", timeout=20, check=False)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("LOOPBACK_PREFLIGHT_OK", result.stdout)


class HostedInterpolationTests(unittest.TestCase):
    def render(self, overrides=None):
        result = compose_result(BASE, MULTI_USER, HOSTED, interpolate=True, overrides=overrides)
        # Do not include Compose output/stderr in assertion messages: base config can contain secrets.
        self.assertEqual(result.returncode, 0, "sanitized Compose interpolation failed")
        return json.loads(result.stdout)

    def test_positive_sanitized_interpolation(self):
        config = self.render()
        check_hosted(config)
        self.assertEqual(config["services"]["hosted-edge"]["environment"]["HOSTED_DG_HOST"],
                         HOSTED_INPUTS["HOSTED_DG_HOST"])
        self.assertNotIn("fixture-dg_service_token", repr(config["services"]["hosted-edge"]))

    def test_missing_required_variable_fails(self):
        for key in HOSTED_INPUTS:
            with self.subTest(key=key):
                inputs = {k: v for k, v in HOSTED_INPUTS.items() if k != key}
                result = compose_result(BASE, MULTI_USER, HOSTED, interpolate=True, overrides=inputs)
                self.assertNotEqual(result.returncode, 0, "missing required variable accepted")

    def test_negative_shape_mutations(self):
        import copy
        base = self.render()
        for label, edit in [
            ("localhost", lambda m: m["services"]["data-service"]["environment"].__setitem__("DG_BASE_URL", "https://localhost")),
            ("http-speckle", lambda m: m["services"]["data-service"]["environment"].__setitem__("SPECKLE_BASE_URL", "http://speckle.example.invalid")),
            ("http-object", lambda m: m["services"]["speckle-server"]["environment"].__setitem__("S3_PUBLIC_ENDPOINT", "http://objects.example.invalid")),
            ("duplicate-host", lambda m: m["services"]["speckle-server"]["environment"].__setitem__("S3_PUBLIC_ENDPOINT", "https://dg.example.invalid")),
            ("cookie", lambda m: m["services"]["data-service"]["environment"].__setitem__("DG_COOKIE_SECURE", "false")),
            ("wildcard-trust", lambda m: m["services"]["data-service"]["environment"].__setitem__("DG_TRUSTED_PROXIES", "0.0.0.0/0")),
            ("extra-port", lambda m: m["services"]["design-grammars"].__setitem__("ports", [{"host_ip": "0.0.0.0", "published": "8080", "target": 80}])),
        ]:
            with self.subTest(label=label):
                mutated = copy.deepcopy(base)
                edit(mutated)
                with self.assertRaises(ValueError):
                    check_hosted(mutated)

    def test_invalid_inputs_fail_policy_even_if_compose_interpolates(self):
        for key, value in (("HOSTED_DG_HOST", "localhost"),
                           ("HOSTED_SPECKLE_HOST", "127.0.0.1"),
                           ("HOSTED_OBJECT_HOST", "dg.example.invalid"),
                           ("HOSTED_EDGE_IP", "0.0.0.0")):
            with self.subTest(key=key):
                config = self.render({**HOSTED_INPUTS, key: value})
                with self.assertRaises(ValueError):
                    check_hosted(config)


if __name__ == "__main__":
    unittest.main()
