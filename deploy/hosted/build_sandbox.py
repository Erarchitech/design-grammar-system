"""Build/verify a portable synthetic sandbox ZIP from exact committed blobs only.

This is NOT the immutable hosted release manifest. Images are unresolved.
"""
import argparse
import hashlib
import io
import json
from pathlib import Path
import re
import subprocess
import sys
import tarfile
import zipfile

SHA = re.compile(r'[0-9a-f]{40}\Z')
INPUTS = (
    'data-service/Dockerfile', 'data-service/requirements.txt', 'data-service/*.py',
    'data-service/prompts/input_generation_system.md',
    'data-service/prompts/recognition_system.md',
    'data-service/fixtures/frame_recognition_fewshot.json',
    'llm/cypher_catalog.json', 'llm/structure_rules.json',
    'ontology/DesignGrammar-V7.owl', 'ontology/export_to_markdown_v7.py',
    'spec/evidence-contract.schema.json',
    'deploy/hosted/ingest/README.md', 'n8n/workflows/sandbox-file-read.json',
    'n8n/workflows/sandbox-file-denied.json',
    'deploy/hosted/sandbox/compose.yaml', 'deploy/hosted/sandbox/Run-Sandbox.ps1',
    'deploy/hosted/sandbox/probe.py', 'deploy/hosted/sandbox/README.md',
)


def build(repo, revision, destination):
    if not SHA.fullmatch(revision):
        raise ValueError('exact 40-hex revision required')
    repo, destination = Path(repo).resolve(), Path(destination).absolute()
    if destination.exists() or repo == destination or repo in destination.parents:
        raise ValueError('destination must be new and outside checkout')
    actual = subprocess.check_output(['git', '-C', str(repo), 'rev-parse', '--verify', revision + '^{commit}'],
                                     stderr=subprocess.DEVNULL, text=True).strip()
    if actual != revision:
        raise ValueError('revision mismatch')
    rows = subprocess.check_output(['git', '-C', str(repo), 'ls-tree', '-rz', '--full-tree', revision])
    tracked = {}
    for row in rows.split(b'\0'):
        if row:
            header, name = row.split(b'\t', 1)
            tracked[name.decode('utf-8')] = header.split()[0].decode('ascii')
    from fnmatch import fnmatchcase
    selected = set()
    for entry in INPUTS:
        found = {name for name in tracked if name.count('/') == entry.count('/') and fnmatchcase(name, entry)}
        if not found:
            raise ValueError('missing committed sandbox input')
        selected.update(found - {'data-service/rotate_llm_master_secret.py'})
    for name in selected:
        if tracked[name] not in ('100644', '100755') or name.startswith('/') or '\\' in name or '..' in name.split('/'):
            raise ValueError('linked or unsafe selected path')
        if any(part.startswith('.') for part in name.split('/')):
            raise ValueError('private selected path')
        if name.startswith('data-service/') and name.endswith('.py') and 'rotate_llm_master_secret' in name:
            raise ValueError('maintenance tool not permitted')
    archive = subprocess.check_output(['git', '-C', str(repo), 'archive', '--format=tar', revision,
                                       '--', *sorted(selected)])
    payload = {}
    with tarfile.open(fileobj=io.BytesIO(archive)) as tar:
        for member in tar:
            if member.isdir():
                continue
            if member.name not in selected or not member.isfile() or member.name in payload:
                raise ValueError('unexpected archive member')
            payload[member.name] = tar.extractfile(member).read()
    if set(payload) != selected or len({x.casefold() for x in payload}) != len(payload):
        raise ValueError('archive mismatch or case collision')
    manifest = {'schemaVersion': 1, 'kind': 'synthetic-capability-sandbox-not-release',
                'frameworkRevision': revision, 'images': 'unresolved-target-build-and-pull',
                'files': {name: hashlib.sha256(content).hexdigest() for name, content in sorted(payload.items())}}
    payload['sandbox-manifest.json'] = (json.dumps(manifest, sort_keys=True, indent=2) + '\n').encode()
    destination.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(destination, 'x', compression=zipfile.ZIP_DEFLATED) as output:
        for name, content in sorted(payload.items()):
            output.writestr(name, content)
    return hashlib.sha256(destination.read_bytes()).hexdigest()


def verify(destination):
    with zipfile.ZipFile(destination) as archive:
        infos = archive.infolist()
        names = [info.filename for info in infos]
        if len(names) != len(set(names)) or any(name.startswith('/') or '\\' in name or '..' in name.split('/')
                                                or info.is_dir() or info.file_size > 4_000_000 for name, info in zip(names, infos)):
            raise ValueError('unsafe ZIP entries')
        manifest = json.loads(archive.read('sandbox-manifest.json'))
        if manifest['kind'] != 'synthetic-capability-sandbox-not-release' or set(names) != set(manifest['files']) | {'sandbox-manifest.json'}:
            raise ValueError('ZIP manifest mismatch')
        for name, expected in manifest['files'].items():
            if hashlib.sha256(archive.read(name)).hexdigest() != expected:
                raise ValueError('content hash mismatch')
    return hashlib.sha256(Path(destination).read_bytes()).hexdigest()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--repo')
    parser.add_argument('--revision')
    parser.add_argument('--output', required=True)
    parser.add_argument('--verify-only', action='store_true')
    args = parser.parse_args()
    try:
        value = verify(args.output) if args.verify_only else build(args.repo, args.revision, args.output)
        print('sandbox ZIP SHA-256: ' + value)
    except (ValueError, KeyError, OSError, subprocess.CalledProcessError, tarfile.TarError, zipfile.BadZipFile) as error:
        print('sandbox package BLOCKED: ' + type(error).__name__, file=sys.stderr)
        return 1
    return 0


if __name__ == '__main__':
    sys.exit(main())
