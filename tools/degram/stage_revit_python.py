#!/usr/bin/env python3
"""Stage the Python the DeGram installer bundles for the Revit adapter.

The DG Revit connector (``apps/dg-revit-connector/main.py``) imports ``mcp.server.fastmcp`` and ``httpx``. The
agent's own interpreter carries ``mcp`` 2.x, which has no ``fastmcp`` module, so the adapter needs a separate
interpreter. Until now that was the developer's ``.venv`` (``DEGRAM_PYTHON``); a tester's machine has none. This
script produces ``resources/revit-python`` for the installer: the official Windows *embeddable* CPython 3.11
with ``mcp<2`` and ``httpx`` unpacked into its ``Lib/site-packages``. ``resolveRevitAdapter`` in
``apps/degram/apps/desktop/electron/degram/dg-config.ts`` picks it up when no ``DEGRAM_PYTHON``, ``revitPython``
or adapter ``.venv`` is set.

Nothing is installed on this machine: the interpreter comes from python.org (its Authenticode signature, which
must be the Python Software Foundation's, is checked), and the packages are downloaded as binary wheels for
Windows/CPython 3.11 and unpacked with ``pip install --target``.

Usage::

    python tools/degram/stage_revit_python.py --out D:\\dgb\\revit-python\\3.11.9
    python tools/degram/stage_revit_python.py --out <dir> --adapter apps/dg-revit-connector   # default

Then point the DeGram build at it (``D:\\dgb\\run-build.sh``)::

    export DEGRAM_REVIT_PYTHON_SOURCE='<out>'

Exit codes: 0 staged and verified, 2 refused (non-empty output, download, signature, install or verification failed).
"""

import argparse
import datetime
import hashlib
import json
import shutil
import subprocess
import sys
import tempfile
import urllib.request
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DEFAULT_ADAPTER = Path("apps/dg-revit-connector")

#: The last CPython 3.11 release that ships Windows binaries (3.11.10 and later are source-only).
PYTHON_VERSION = "3.11.9"
EMBED_URL = "https://www.python.org/ftp/python/{v}/python-{v}-embed-amd64.zip"
#: ``mcp`` 2.x dropped ``mcp.server.fastmcp``; ``httpx`` is the adapter's HTTP client.
REQUIREMENTS = ("mcp<2", "httpx")
PUBLISHER = "Python Software Foundation"
SITE_PACKAGES = "Lib/site-packages"
#: What pip ``--target`` puts beside the packages that the bundle never needs.
SKIP_TOP_LEVEL = ("bin",)


class StageError(Exception):
    """The Python cannot be staged."""


def sha256(path):
    digest = hashlib.sha256()
    with open(path, "rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def download(url, destination, opener=urllib.request.urlopen):
    try:
        with opener(url, timeout=120) as response, open(destination, "wb") as handle:
            while True:
                chunk = response.read(1 << 20)
                if not chunk:
                    break
                handle.write(chunk)
    except OSError as error:
        raise StageError("could not download {}: {}".format(url, error))


def signature_publisher(executable, run=subprocess.run):
    """The Authenticode signer subject of ``executable``, or ``""`` when unsigned or the check cannot run."""
    script = "$s = Get-AuthenticodeSignature -LiteralPath '{}'; if ($s.Status -eq 'Valid') {{ $s.SignerCertificate.Subject }}".format(
        str(executable).replace("'", "''"))
    result = run(["powershell", "-NoProfile", "-NonInteractive", "-Command", script],
                 capture_output=True, text=True, check=False)
    return result.stdout.strip() if result.returncode == 0 else ""


def extract(archive, target):
    target.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(archive) as bundle:
        bundle.extractall(target)
    if not (target / "python.exe").is_file():
        raise StageError("the archive has no python.exe")


def patch_path_file(target):
    """Let the embeddable interpreter see its site-packages.

    The embeddable distribution runs isolated: a ``python311._pth`` file replaces every other source of
    ``sys.path`` (``PYTHONPATH`` and the script directory included). The adapter's own folder is resolved
    relative to this file, ``..\\revit-mcp`` being its place beside ``revit-python`` under the app's resources, so
    ``main.py`` finds ``dg_transport`` and ``tools``.
    """
    files = sorted(target.glob("python*._pth"))
    if len(files) != 1:
        raise StageError("expected one python*._pth file in {}".format(target))
    path_file = files[0]
    lines = [line for line in path_file.read_text(encoding="utf-8").splitlines()]
    ours = (SITE_PACKAGES, SITE_PACKAGES.replace("/", "\\"), "..\\revit-mcp", "../revit-mcp")
    kept = [line for line in lines if line.strip() not in ours]
    insert_at = next((i for i, line in enumerate(kept) if line.strip() == "."), len(kept) - 1) + 1
    kept[insert_at:insert_at] = [SITE_PACKAGES.replace("/", "\\"), "..\\revit-mcp"]
    # `import site` makes site-packages a site directory, so its .pth files run. mcp pulls pywin32 on Windows, and
    # pywin32 wires its DLL directory and sub-packages through pywin32.pth.
    kept = ["import site" if line.strip() == "#import site" else line for line in kept]
    if not any(line.strip() == "import site" for line in kept):
        kept.append("import site")
    # Bytes, not write_text: text mode would turn each "\r\n" into "\r\r\n" on Windows.
    path_file.write_bytes(("\r\n".join(kept) + "\r\n").encode("utf-8"))
    return path_file


def install_packages(host_python, target, requirements=REQUIREMENTS, run=subprocess.run):
    """Unpack binary wheels for Windows/CPython 3.11 into the staged interpreter's site-packages."""
    site = target / SITE_PACKAGES
    site.mkdir(parents=True, exist_ok=True)
    command = [host_python, "-m", "pip", "install", "--no-input", "--disable-pip-version-check",
               "--target", str(site), "--only-binary=:all:", "--implementation", "cp",
               "--python-version", PYTHON_VERSION.rsplit(".", 1)[0], "--platform", "win_amd64",
               *requirements]
    result = run(command, capture_output=True, text=True, check=False)
    if result.returncode != 0:
        raise StageError("pip could not fetch the packages (exit {}): {}".format(
            result.returncode, (result.stderr or result.stdout).strip()[-600:]))
    for name in SKIP_TOP_LEVEL:
        leftover = site / name
        if leftover.is_dir():
            for child in sorted(leftover.rglob("*"), reverse=True):
                child.rmdir() if child.is_dir() else child.unlink()
            leftover.rmdir()
    for cache in site.rglob("__pycache__"):
        for child in cache.iterdir():
            child.unlink()
        cache.rmdir()


def installed_versions(python, run=subprocess.run):
    code = ("import importlib.metadata as m, json, sys; "
            "print(json.dumps({'python': sys.version.split()[0], 'mcp': m.version('mcp'), 'httpx': m.version('httpx')}))")
    result = run([str(python), "-c", code], capture_output=True, text=True, check=False)
    if result.returncode != 0:
        raise StageError("the staged interpreter cannot import its packages: {}".format(result.stderr.strip()[-400:]))
    return json.loads(result.stdout.strip().splitlines()[-1])


def verify(python, adapter=None, run=subprocess.run):
    """Run the staged interpreter the way DeGram will: the fastmcp import, and the adapter's ``--help`` when given.

    The adapter check runs from a copy laid out like the app's resources (``revit-python`` beside ``revit-mcp``),
    because the ``._pth`` file names the adapter folder relative to the interpreter.
    """
    result = run([str(python), "-c", "from mcp.server.fastmcp import FastMCP; import httpx"],
                 capture_output=True, text=True, check=False)
    if result.returncode != 0:
        raise StageError("mcp.server.fastmcp or httpx does not import: {}".format(result.stderr.strip()[-400:]))
    if adapter is None:
        return
    adapter = Path(adapter)
    if not (adapter / "main.py").is_file():
        raise StageError("no main.py in the adapter folder {}".format(adapter))
    with tempfile.TemporaryDirectory(prefix="revit-python-check-") as tmp:
        layout = Path(tmp)
        shutil.copytree(Path(python).parent, layout / "revit-python")
        shutil.copytree(adapter, layout / "revit-mcp",
                        ignore=shutil.ignore_patterns("tests", ".git", ".venv", "__pycache__", "*.pyc"))
        result = run([str(layout / "revit-python" / "python.exe"), str(layout / "revit-mcp" / "main.py"), "--help"],
                     capture_output=True, text=True, check=False, cwd=str(layout))
    if result.returncode != 0:
        raise StageError("the adapter does not start with this interpreter: {}".format(
            (result.stderr or result.stdout).strip()[-400:]))


def file_hashes(root):
    return {path.relative_to(root).as_posix(): sha256(path) for path in sorted(root.rglob("*")) if path.is_file()}


def stage(out, host_python=sys.executable, adapter=None, work=None, opener=urllib.request.urlopen, run=subprocess.run, now=None):
    """Download, unpack, install and verify into ``out``; returns the manifest dict."""
    out = Path(out)
    if out.exists() and any(out.iterdir()):
        raise StageError("the output folder is not empty: {}".format(out))
    out.mkdir(parents=True, exist_ok=True)
    archive = Path(work or out.parent) / "python-{}-embed-amd64.zip".format(PYTHON_VERSION)
    archive.parent.mkdir(parents=True, exist_ok=True)
    url = EMBED_URL.format(v=PYTHON_VERSION)
    download(url, archive, opener)
    archive_hash = sha256(archive)

    extract(archive, out)
    publisher = signature_publisher(out / "python.exe", run)
    if PUBLISHER not in publisher:
        raise StageError("python.exe is not signed by {} (signer: {!r})".format(PUBLISHER, publisher or "none"))
    patch_path_file(out)
    install_packages(host_python, out, run=run)
    versions = installed_versions(out / "python.exe", run)
    verify(out / "python.exe", adapter, run)

    moment = now or datetime.datetime.now(datetime.timezone.utc)
    manifest = {
        "stagedAt": moment.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "source": url,
        "archiveSha256": archive_hash,
        "signedBy": publisher,
        "requirements": list(REQUIREMENTS),
        "versions": versions,
        "adapterChecked": adapter is not None,
        "files": file_hashes(out),
    }
    (out.parent / (out.name + "-manifest.json")).write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return manifest


def main(argv=None):
    parser = argparse.ArgumentParser(description="Stage the Python for the DeGram Revit adapter.")
    parser.add_argument("--out", required=True, help="an empty output folder (becomes resources/revit-python)")
    parser.add_argument("--adapter", default=str(ROOT / DEFAULT_ADAPTER), help="the Revit connector folder to smoke-test")
    parser.add_argument("--no-adapter-check", action="store_true", help="only check the imports")
    parser.add_argument("--host-python", default=sys.executable, help="the interpreter whose pip downloads the wheels")
    arguments = parser.parse_args(argv)
    try:
        manifest = stage(arguments.out, arguments.host_python, None if arguments.no_adapter_check else arguments.adapter)
    except StageError as error:
        print("error: {}".format(error), file=sys.stderr)
        return 2
    out = Path(arguments.out).resolve()
    print("staged CPython {} with mcp {} and httpx {}".format(
        manifest["versions"]["python"], manifest["versions"]["mcp"], manifest["versions"]["httpx"]))
    print("  {} files, signed by {}".format(len(manifest["files"]), manifest["signedBy"]))
    print("add to the DeGram build driver:")
    print("  export DEGRAM_REVIT_PYTHON_SOURCE='{}'".format(out))
    return 0


if __name__ == "__main__":
    sys.exit(main())
