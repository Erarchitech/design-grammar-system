"""Build the isolated Windows fixture in Hermes scratch, without starting Caddy.

Usage: python deploy/hosted/edge/build_test_zip.py <official-Caddy-zip> <official-checksums.txt>
Inputs are downloaded separately from the exact official release URLs in README.
OpenSSL on the builder generates short-lived synthetic certs; nothing secret is committed.
"""
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import zipfile

ROOT = Path(__file__).resolve().parents[3]
EDGE = Path(__file__).resolve().parent
SCRATCH = Path.home() / "AppData/Local/hermes/cache/scratch"
RELEASE = "caddy_2.10.2_windows_amd64.zip"
URL = "https://github.com/caddyserver/caddy/releases/download/v2.10.2/"


def sha(data, algorithm="sha256"):
    return hashlib.new(algorithm, data).hexdigest()


def build(release, checksums):
    archive = Path(release).read_bytes()
    checksum_lines = Path(checksums).read_text(encoding="utf-8").splitlines()
    found = [line.split()[0].lower() for line in checksum_lines if line.endswith("  " + RELEASE)]
    if len(found) != 1 or found[0] != sha(archive, "sha512"):
        raise ValueError("official SHA-512 release checksum mismatch")
    with zipfile.ZipFile(Path(release)) as z:
        if z.namelist().count("caddy.exe") != 1:
            raise ValueError("official release contains no unique caddy.exe")
        binary = z.read("caddy.exe")
    source = (EDGE / "Caddyfile").read_bytes()
    source_digest = sha(source)
    runner = (EDGE / "Run-Edge-Test.ps1").read_text(encoding="utf-8")
    if runner.count("CADDY_SHA256_REPLACE") != 1 or runner.count("SOURCE_SHA256_REPLACE") != 1:
        raise ValueError("runner digest placeholders drifted")
    runner = runner.replace("CADDY_SHA256_REPLACE", sha(binary)).replace("SOURCE_SHA256_REPLACE", source_digest)
    certs = {}
    with tempfile.TemporaryDirectory(dir=SCRATCH, prefix="dg-edge-certs-") as temp:
        for role, hostname in (("dg", "dg.example.invalid"), ("speckle", "speckle.example.invalid"),
                               ("object", "objects.example.invalid")):
            cert = Path(temp) / (role + ".crt")
            key = Path(temp) / (role + ".key")
            command = ["openssl", "req", "-x509", "-newkey", "rsa:2048", "-nodes", "-sha256",
                       "-days", "7", "-subj", "/CN=" + hostname, "-addext", "subjectAltName=DNS:" + hostname,
                       "-keyout", str(key), "-out", str(cert)]
            result = subprocess.run(command, capture_output=True, timeout=30, check=False)
            if result.returncode:
                raise RuntimeError("OpenSSL test certificate generation failed")
            certs["certs/" + role + ".crt"] = cert.read_bytes()
            certs["certs/" + role + ".key"] = key.read_bytes()
    readme = (EDGE / "TEST-PACKAGE.md").read_bytes()
    payload = {"caddy.exe": binary, "Caddyfile.source": source,
               "Run-Edge-Test.ps1": runner.encode("utf-8"), "README.md": readme, **certs}
    manifest = {"release": "Caddy v2.10.2 windows_amd64", "releaseUrl": URL + RELEASE,
                "releaseChecksumsUrl": URL + "caddy_2.10.2_checksums.txt",
                "releaseZipSha512": found[0], "releaseZipSha256": sha(archive),
                "files": {name: sha(data) for name, data in payload.items()},
                "certificates": "Synthetic self-signed 7-day test keys; no production use",
                "source": "deploy/hosted/edge/Caddyfile byte-for-byte"}
    payload["manifest.json"] = (json.dumps(manifest, indent=2, sort_keys=True) + "\n").encode()
    output = SCRATCH / "dg-edge-blackbox-DESKTOP-0S4Q8CP.zip"
    with zipfile.ZipFile(output, "w", compression=zipfile.ZIP_DEFLATED) as z:
        for name, data in payload.items():
            z.writestr(name, data)
    with zipfile.ZipFile(output) as z:
        for name, digest in manifest["files"].items():
            if sha(z.read(name)) != digest:
                raise AssertionError("ZIP entry integrity failed")
        if z.testzip() is not None:
            raise AssertionError("ZIP CRC failed")
    print(output)
    print("ZIP SHA256", sha(output.read_bytes()))
    print("Caddy EXE SHA256", sha(binary))
    print("Source Caddyfile SHA256", source_digest)
    print("Entry count", len(payload))


if __name__ == "__main__":
    if len(sys.argv) != 3:
        raise SystemExit(__doc__)
    build(sys.argv[1], sys.argv[2])
