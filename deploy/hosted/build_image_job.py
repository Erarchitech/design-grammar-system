"""Prepare an exact-commit, target-only image BUILD/SAVE job, not a release.

Source comes only from assemble.py's allowlisted committed blobs. Newly authored
runner tooling is separately hashed and explicitly not claimed as part of that
source commit. No Docker daemon, service, registry push or Git mutation here.
"""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import zipfile

from assemble import assemble
from release_core import SHA, digest, safe_path
from validate_manifest import merged_compose, validate

SERVICES = {
    'neo4j': {'context': 'source/neo4j', 'dockerfile': 'Dockerfile'},
    'dg-reasoner': {'context': 'source/dg-reasoner', 'dockerfile': 'Dockerfile'},
    'data-service': {'context': 'source/data-service', 'dockerfile': 'Dockerfile'},
    'design-grammars': {'context': 'source/ui-v2', 'dockerfile': 'Dockerfile'},
}
KIND = 'controlled-image-build-not-release'
TOOLING = 'hashed-preparation-tools-not-part-of-source-revision'


def prepare(repo, revision, destination, *, runner=None):
    repo, destination = Path(repo).resolve(), Path(destination).absolute()
    if (not SHA.fullmatch(revision) or destination.exists() or destination.is_symlink() or
            repo == destination or repo in destination.parents):
        raise ValueError('exact revision and new external destination required')
    here = Path(__file__).resolve().parent
    # Do not run a dirty source selector or verifier and claim committed selection.
    for name in ('assemble.py', 'validate_manifest.py', 'release_core.py', 'release-allowlist.json'):
        rel = 'deploy/hosted/' + name
        committed = subprocess.check_output(['git', '-C', str(repo), 'show', revision + ':' + rel],
                                             stderr=subprocess.DEVNULL)
        current = repo / rel
        if (current.is_symlink() or not current.is_file() or
                current.read_bytes().replace(b'\r\n', b'\n') != committed.replace(b'\r\n', b'\n')):
            raise ValueError('dirty preparation input')
        if name.endswith('.py') and (here / name).read_bytes().replace(b'\r\n', b'\n') != committed.replace(b'\r\n', b'\n'):
            raise ValueError('executed preparation code differs from revision')
    runner = Path(runner) if runner else here / 'build-job/Run-ImageBuild.ps1'
    if runner.is_symlink() or not runner.is_file() or not runner.stat().st_size:
        raise ValueError('missing regular target runner')
    with tempfile.TemporaryDirectory(prefix='dg-controlled-build-') as tmp:
        source = Path(tmp) / 'source'
        assemble(repo, revision, repo / 'deploy/hosted/release-allowlist.json', source)
        validate(source, allow_blocked=True, source=repo)
        services = merged_compose(source)
        built = {name for name, value in services.items() if value.get('build')}
        if built != set(SERVICES):
            raise ValueError('unexpected built service inventory')
        for name, contract in SERVICES.items():
            context = Path(services[name]['build']['context']).resolve().relative_to(source).as_posix()
            if 'source/' + context != contract['context']:
                raise ValueError('unexpected build context')
        manifest_bytes = (source / 'manifest.json').read_bytes()
        source_manifest = json.loads(manifest_bytes)
        payload = {'source/' + name: (source / name).read_bytes() for name in source_manifest['files']}
        payload['source/manifest.json'] = manifest_bytes
        payload['support/Run-ImageBuild.ps1'] = runner.read_bytes()
        job = {'schemaVersion': 1, 'kind': KIND, 'frameworkRevision': revision,
               'sourceManifestSha256': digest(manifest_bytes), 'target': 'DESKTOP-OS4Q8CP',
               'services': SERVICES, 'toolingStatus': TOOLING,
               'files': {name: digest(data) for name, data in sorted(payload.items())}}
        payload['build-job-manifest.json'] = (json.dumps(job, indent=2, sort_keys=True) + '\n').encode()
        destination.parent.mkdir(parents=True, exist_ok=True)
        with zipfile.ZipFile(destination, 'x', compression=zipfile.ZIP_DEFLATED) as archive:
            for name, data in sorted(payload.items()):
                info = zipfile.ZipInfo(name, date_time=(2026, 1, 1, 0, 0, 0))
                archive.writestr(info, data, compress_type=zipfile.ZIP_DEFLATED)
    return verify(destination)


def verify(destination):
    with zipfile.ZipFile(destination) as archive:
        names = archive.namelist()
        if len(names) != len({name.casefold() for name in names}):
            raise ValueError('duplicate member')
        for info in archive.infolist():
            safe_path(info.filename)
            if info.is_dir() or info.file_size > 32_000_000 or (info.external_attr >> 16) & 0o170000 == 0o120000:
                raise ValueError('unsafe member')
        job = json.loads(archive.read('build-job-manifest.json'))
        if (set(job) != {'schemaVersion', 'kind', 'frameworkRevision', 'sourceManifestSha256',
                         'target', 'services', 'files', 'toolingStatus'} or
                type(job['schemaVersion']) is not int or job['schemaVersion'] != 1 or
                job['kind'] != KIND or job['target'] != 'DESKTOP-OS4Q8CP' or
                job['toolingStatus'] != TOOLING or job['services'] != SERVICES or
                not SHA.fullmatch(str(job['frameworkRevision']))):
            raise ValueError('job schema mismatch')
        if (set(names) != set(job['files']) | {'build-job-manifest.json'} or
                {name for name in names if not name.startswith('source/')} !=
                {'support/Run-ImageBuild.ps1', 'build-job-manifest.json'}):
            raise ValueError('job membership mismatch')
        for name, expected in job['files'].items():
            if digest(archive.read(name)) != expected:
                raise ValueError('job digest mismatch')
        raw = archive.read('source/manifest.json')
        source = json.loads(raw)
        if (digest(raw) != job['sourceManifestSha256'] or source['frameworkRevision'] != job['frameworkRevision'] or
                source['status'] != 'BLOCKED' or source['degramGitlink'] is not None):
            raise ValueError('source identity mismatch')
        if {name for name in names if name.startswith('source/')} != {'source/' + name for name in source['files']} | {'source/manifest.json'}:
            raise ValueError('source membership mismatch')
        for name, expected in source['files'].items():
            if digest(archive.read('source/' + name)) != expected:
                raise ValueError('source digest mismatch')
    return digest(Path(destination).read_bytes())


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--repo', default='.')
    parser.add_argument('--revision')
    parser.add_argument('--output', required=True)
    parser.add_argument('--verify-only', action='store_true')
    args = parser.parse_args()
    try:
        value = verify(args.output) if args.verify_only else prepare(args.repo, args.revision, args.output)
        print('Controlled image build ZIP SHA256: ' + value)
    except (ValueError, OSError, KeyError, TypeError, subprocess.CalledProcessError, zipfile.BadZipFile):
        print('Build job package BLOCKED (no raw output emitted)', file=sys.stderr)
        return 1
    return 0


if __name__ == '__main__':
    sys.exit(main())
