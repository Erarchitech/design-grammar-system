"""Temporary synthetic git repos for offline release tests."""
import json
from pathlib import Path
import subprocess
import sys

HOSTED = Path(__file__).resolve().parents[1]


def fixture_repository(root, symlink=False):
    source = root / "source"
    source.mkdir()
    subprocess.run(["git", "init", "-q", str(source)], check=True, capture_output=True)
    (source / "sample.txt").write_text("committed fixture\n")
    paths = ["sample.txt"]
    if symlink:
        try:
            (source / "link.txt").symlink_to("sample.txt")
        except OSError:
            blob = subprocess.check_output(["git", "-C", str(source), "hash-object", "-w", "--stdin"],
                                           input=b"sample.txt", stderr=subprocess.DEVNULL).decode().strip()
            subprocess.run(["git", "-C", str(source), "update-index", "--add", "--cacheinfo",
                            f"120000,{blob},link.txt"], check=True, capture_output=True)
        else:
            paths.append("link.txt")
    subprocess.run(["git", "-C", str(source), "add", *paths], check=True, capture_output=True)
    subprocess.run(["git", "-C", str(source), "-c", "user.name=Fixture",
                    "-c", "user.email=fixture@example.invalid", "commit", "-qm", "fixture"],
                   check=True, capture_output=True)
    revision = subprocess.check_output(["git", "-C", str(source), "rev-parse", "HEAD"], text=True).strip()
    return source, revision


def assemble(source, revision, output, path="sample.txt"):
    allowlist = output.parent / (output.name + "-allowlist.json")
    allowlist.write_text(json.dumps({"schemaVersion": 1, "includeDegram": False, "inputs": [
        {"path": path, "purpose": "synthetic fixture"}
    ]}))
    return subprocess.run([sys.executable, str(HOSTED / "assemble.py"), "--repo", str(source),
                           "--revision", revision, "--allowlist", str(allowlist),
                           "--output", str(output)], capture_output=True, text=True)


def validator(output, *args):
    return subprocess.run([sys.executable, str(HOSTED / "validate_manifest.py"), str(output), *args],
                          capture_output=True, text=True)
