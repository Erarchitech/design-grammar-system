#!/usr/bin/env python3
"""Pack the files the server stand needs into ONE reproducible tar.gz; refuse anything private.

Selection = the reviewed release allowlist (deploy/hosted/release-allowlist.json) + the
server-stand kit + the env template. Files come from the WORKING TREE (git-tracked or untracked
and not ignored), so the archive records whether uncommitted changes were included. This is a
stand package, not a frozen release: no image digests, no signature.

    python3 pack_source.py --repo . --output dg-stand.tar.gz
"""
import argparse
import gzip
import hashlib
import importlib.util
import io
import json
from pathlib import Path
import subprocess
import sys
import tarfile

HERE = Path(__file__).resolve().parent
KIT_PATHS = [
    "docker-compose.server.yml",
    "deploy/hosted/server/*",
    "tools/security/check_env_file.py",
    "test/smoke_rules_ingest.sh",
    "test/smoke_graph_query.sh",
]
TEMPLATE = ".env.example"          # the only dot-env name allowed in the archive
# Runtime files of branches ahead of the release allowlist. They ship when present and are skipped
# when absent (the release policy stays untouched until a release freeze decides on them).
# data-service/property_scripts.py reads the catalogue and the *.py.tmpl templates at run time and
# the image is built from the archive alone, so leaving them out would only fail at first use.
OPTIONAL_PATHS = [
    "data-service/property_calculators/catalogue.json",
    "data-service/property_calculators/*.py.tmpl",
    # F-01 (2026-10-29): dg-evaluator is built from DG.Core and its own project (build context ./DG).
    "DG/.dockerignore",
    "DG/src/DG.Core/DG.Core.csproj",
    "DG/src/DG.Core/*/*.cs",
    "DG/src/DG.Core/*/*/*.cs",
    "DG/tools/DG.Evaluator/*",
]


def fail(message):
    print("pack_source: " + message, file=sys.stderr)
    raise SystemExit(2)


def load_core():
    spec = importlib.util.spec_from_file_location("release_core", HERE.parent / "release_core.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def git(repo, *args):
    done = subprocess.run(["git", "-C", str(repo), *args], capture_output=True, timeout=60)
    if done.returncode:
        fail("git failed: " + " ".join(args[:2]))
    return done.stdout


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--repo", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args(argv)
    repo, output = Path(args.repo).resolve(), Path(args.output)
    if output.exists():
        fail("output exists; refusing to overwrite")
    core = load_core()

    allowlist_file = repo / "deploy/hosted/release-allowlist.json"
    if not allowlist_file.is_file():
        fail("release allowlist not found")
    allowlist = json.loads(allowlist_file.read_text(encoding="utf-8"))
    revision = git(repo, "rev-parse", "HEAD").decode().strip()
    listed = git(repo, "ls-files", "-z", "--cached", "--others", "--exclude-standard").split(b"\0")
    candidates = sorted({item.decode("utf-8") for item in listed if item} )
    symlinks = {p for p in candidates if (repo / p).is_symlink()}
    candidates = [p for p in candidates if (repo / p).is_file() or (repo / p).is_symlink()]

    selected = {}
    specs = [(item["path"], item.get("exclude", [])) for item in allowlist["inputs"]]
    specs += [(path, []) for path in KIT_PATHS] + [(TEMPLATE, [])]
    specs += [(path, []) for path in OPTIONAL_PATHS]
    for pattern, excluded in specs:
        found = [p for p in candidates if core.matches(p, pattern)
                 and not any(core.matches(p, e) for e in excluded)]
        if not found and pattern not in OPTIONAL_PATHS:
            fail(f"allowlisted input matches nothing: {pattern}")
        for path in found:
            if path in symlinks:
                fail(f"selected path is a symbolic link: {path}")
            if path != TEMPLATE:
                try:
                    core.safe_path(path)
                except ValueError:
                    fail(f"forbidden or private path selected: {path}")
            selected[path] = (repo / path).read_bytes()

    files = {}
    for path in sorted(selected):
        data = selected[path]
        if path.endswith(".sh"):
            data = data.replace(b"\r\n", b"\n")   # a Windows checkout must not break shell scripts
        selected[path] = data
        files[path] = hashlib.sha256(data).hexdigest()

    # Compare against HEAD without passing thousands of paths on a command line.
    changed = {item.decode("utf-8") for item in
               git(repo, "diff", "--name-only", "-z", "HEAD").split(b"\0") if item}
    changed |= {item.decode("utf-8") for item in
                git(repo, "ls-files", "-z", "--others", "--exclude-standard").split(b"\0") if item}
    dirty = bool(changed & set(selected))
    info = {"schemaVersion": 1, "kind": "dg-server-stand-source-not-a-release", "revision": revision,
            "workingTreeState": "uncommitted-changes-included" if dirty else "clean",
            "files": files}
    info_bytes = (json.dumps(info, indent=2, sort_keys=True) + "\n").encode("utf-8")

    buffer = io.BytesIO()
    with gzip.GzipFile(fileobj=buffer, mode="wb", mtime=0) as zipped:
        with tarfile.open(fileobj=zipped, mode="w", format=tarfile.PAX_FORMAT) as tar:
            members = sorted([*selected.items(), ("PACK-INFO.json", info_bytes)])
            for name, data in members:
                member = tarfile.TarInfo(name)
                member.size = len(data)
                member.mtime = 0
                member.uid = member.gid = 0
                member.uname = member.gname = ""
                # Mode depends on the name only, so Windows and Linux builds are byte-identical.
                member.mode = 0o755 if name.endswith(".sh") else 0o644
                tar.addfile(member, io.BytesIO(data))
    blob = buffer.getvalue()
    temporary = output.with_name(output.name + ".partial")
    try:
        with open(temporary, "xb") as stream:
            stream.write(blob)
        temporary.replace(output)
    finally:
        if temporary.exists():
            temporary.unlink()
    print(f"packed {len(selected)} files from {revision[:12]} ({info['workingTreeState']})")
    print(f"sha256 {hashlib.sha256(blob).hexdigest()}  {output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
