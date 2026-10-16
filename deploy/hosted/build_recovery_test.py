"""Prepare a two-store synthetic recovery exercise, not a production backup."""
import argparse
import copy
import hashlib
import json
from pathlib import Path
import sys
import zipfile

from build_image_runtime import REVISION, bind, encoded, sha, verify as verify_runtime
from release_core import safe_path

HERE = Path(__file__).resolve().parent
RUNTIME_SHA = '6fc3b7ad060db3e79a1452e2a2868f87e339aed8bfa70c39b2f3c82b1fa8199f'
IMAGE_IDS = {
    'neo4j': 'sha256:0efd832ad89fcc0526e80abf8b26bb79f196ebe87eac655c6f19c08c5be766b8',
    'data-service': 'sha256:9787e347b10eb8303498fed9e79651b89a3a1d4f62501ee98e51f6f25d0b22d1',
}
KIND = 'synthetic-two-store-recovery-not-release'
TOOLS = ('Run-Recovery.ps1', 'Invoke-OwnerRecovery.ps1', 'execution.ps1', 'probe.py', 'snapshot.py', 'README.md')


def model(*, destination=False):
    # Reuse committed input paths/environment, not the old runner's UI/reasoner.
    from build_image_runtime import runtime_model
    images = {name: {'imageId': value} for name, value in IMAGE_IDS.items()}
    images.update({name: {'imageId': IMAGE_IDS['data-service']} for name in ('dg-reasoner', 'design-grammars')})
    base = runtime_model(images)
    services = {name: copy.deepcopy(base['services'][name]) for name in IMAGE_IDS}
    api = services['data-service']
    api['environment']['DG_REASONER_URL'] = 'http://127.0.0.1:9'
    api['volumes'] = [m for m in api['volumes'] if m['target'] not in ('/app/image_runtime_probe.py','/app/sandbox_probe.py')]
    api['volumes'] += [bind('./support/probe.py', '/app/recovery_probe.py'),
                       {'type': 'volume', 'source': 'exchange', 'target': '/exchange'}]
    services['neo4j']['volumes'].append({'type': 'volume', 'source': 'graph_logs', 'target': '/logs'})
    common = {'pull_policy': 'never', 'platform': 'linux/amd64', 'restart': 'no',
              'cpus': 1.0, 'pids_limit': 128, 'mem_limit': '768m',
              'security_opt': ['no-new-privileges:true'], 'network_mode': 'none',
              'entrypoint': ['/bin/sh', '-c', 'exec sleep 3600'], 'user': '0:0'}
    services['graph-admin'] = dict(common, image=IMAGE_IDS['neo4j'], profiles=['maintenance'], volumes=[
        {'type': 'volume', 'source': name, 'target': target}
        for name, target in [('graph','/data'),('graph_logs','/logs'),('exchange','/exchange')]])
    services['snapshot'] = dict(common, image=IMAGE_IDS['data-service'], profiles=['maintenance'], volumes=[
        {'type': 'volume', 'source': 'api_state', 'target': '/state', 'read_only': not destination},
        {'type': 'volume', 'source': 'exchange', 'target': '/exchange'},
        bind('./support/snapshot.py', '/app/recovery_snapshot.py')],
        environment={'RECOVERY_KEY': '${RECOVERY_KEY:?required}'})
    return {'services': services, 'networks': base['networks'],
            'volumes': {n: {} for n in ('graph', 'api_state', 'exchange', 'graph_logs')}}


def prepare(runtime_zip, output):
    if verify_runtime(runtime_zip) != RUNTIME_SHA:
        raise ValueError('issued runtime ZIP required')
    with zipfile.ZipFile(runtime_zip) as archive:
        payload = {n: archive.read(n) for n in archive.namelist() if n.startswith('source/')}
        payload['support/runtime-functions.ps1'] = archive.read('support/runtime-execution.ps1')
        # Function-only package checks; do not execute old runner main.
        raw = archive.read('support/Run-ImageRuntime.ps1').decode('utf-8')
        payload['support/package-functions.ps1'] = raw[raw.index('function Assert-True'):raw.index('$root = [IO.Path]')].encode()
    for name in TOOLS:
        payload['support/' + name] = (HERE / 'recovery-test' / name).read_bytes()
    payload['support/empty-env.txt'] = b'# Explicitly empty environment.\n'
    payload['source-compose.json'] = encoded(model())
    payload['destination-compose.json'] = encoded(model(destination=True))
    manifest = {'schemaVersion': 1, 'kind': KIND, 'sourceRevision': REVISION,
        'target': 'DESKTOP-OS4Q8CP', 'runtimeZipSha256': RUNTIME_SHA, 'images': IMAGE_IDS,
        'toolingStatus': 'hashed-preparation-not-part-of-source-revision',
        'files': {n: sha(v) for n, v in sorted(payload.items())}}
    payload['recovery-manifest.json'] = encoded(manifest)
    output = Path(output)
    output.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(output, 'x', zipfile.ZIP_DEFLATED) as archive:
        for name, value in sorted(payload.items()):
            info = zipfile.ZipInfo(name, (2026, 1, 1, 0, 0, 0))
            archive.writestr(info, value, compress_type=zipfile.ZIP_DEFLATED)
    return verify(output)


def verify(path):
    with zipfile.ZipFile(path) as archive:
        names = archive.namelist()
        if len(names) != len({n.casefold() for n in names}):
            raise ValueError('duplicate members')
        for entry in archive.infolist():
            safe_path(entry.filename)
            if entry.is_dir() or entry.file_size > 32_000_000 or (entry.external_attr >> 16 & 0o170000) not in (0, 0o100000):
                raise ValueError('unsafe member')
        m = json.loads(archive.read('recovery-manifest.json'))
        fields = {'schemaVersion', 'kind', 'sourceRevision', 'target', 'runtimeZipSha256', 'images', 'toolingStatus', 'files'}
        if (type(m) is not dict or set(m) != fields or type(m['schemaVersion']) is not int
                or m['schemaVersion'] != 1 or m['target'] != 'DESKTOP-OS4Q8CP'
                or m['toolingStatus'] != 'hashed-preparation-not-part-of-source-revision'):
            raise ValueError('manifest contract')
        if m['kind'] != KIND or m['sourceRevision'] != REVISION or m['runtimeZipSha256'] != RUNTIME_SHA or m['images'] != IMAGE_IDS:
            raise ValueError('identity mismatch')
        support = {'support/' + n for n in TOOLS + ('empty-env.txt','runtime-functions.ps1','package-functions.ps1')}
        if {n for n in names if not n.startswith('source/')} != support | {'source-compose.json','destination-compose.json','recovery-manifest.json'}:
            raise ValueError('support membership')
        if set(names) != set(m['files']) | {'recovery-manifest.json'}:
            raise ValueError('membership')
        for name, digest in m['files'].items():
            if sha(archive.read(name)) != digest:
                raise ValueError('hash')
        for filename, destination in [('source-compose.json',False),('destination-compose.json',True)]:
            if archive.read(filename) != encoded(model(destination=destination)):
                raise ValueError('compose model')
        source = json.loads(archive.read('source/manifest.json'))
        from build_image_runtime import SOURCE_SHA
        if sha(archive.read('source/manifest.json')) != SOURCE_SHA:
            raise ValueError('source manifest')
        if set(n[7:] for n in names if n.startswith('source/')) != set(source['files']) | {'manifest.json'}:
            raise ValueError('source membership')
        for name, digest in source['files'].items():
            if sha(archive.read('source/' + name)) != digest:
                raise ValueError('source hash')
    return sha(Path(path).read_bytes())


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--runtime-zip')
    parser.add_argument('--output', required=True)
    parser.add_argument('--verify-only', action='store_true')
    args = parser.parse_args()
    print(verify(args.output) if args.verify_only else prepare(args.runtime_zip, args.output))


if __name__ == '__main__':
    main()
