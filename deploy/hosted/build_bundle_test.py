"""Prepare a target-only capability test of an actual allowlisted source candidate.

Not a frozen release, not full hosted staging. All source bytes must be committed.
"""
import argparse
import copy
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import zipfile

sys.path.insert(0, str(Path(__file__).resolve().parent))
from assemble import assemble
from release_core import SHA, digest, safe_path
from validate_manifest import merged_compose, validate

SUPPORT = (
    'deploy/hosted/bundle-test/Run-BundleTest.ps1',
    'deploy/hosted/bundle-test/README.md',
    'deploy/hosted/bundle-test/empty-env.txt',
    'deploy/hosted/sandbox/probe.py', 'deploy/hosted/sandbox/evidence.cjs',
    'n8n/workflows/sandbox-file-read.json', 'n8n/workflows/sandbox-file-denied.json',
)


def runtime_model(root, services):
    """Narrow actual merged mounts/build contexts, with explicit test-only changes."""
    root = Path(root).resolve()
    selected = {}
    for name in ('neo4j', 'data-service', 'n8n'):
        service = copy.deepcopy(services[name])
        for key in ('container_name', 'ports', 'extra_hosts', 'networks', 'depends_on',
                    'restart', 'deploy', 'profiles'):
            service.pop(key, None)
        service.update(networks=['sandbox'], mem_limit='1500m' if name == 'neo4j' else '1250m',
                       cpus=1.0, pids_limit=256)
        if service.get('build'):
            context = Path(service['build']['context']).resolve().relative_to(root).as_posix()
            service['build'] = {'context': './candidate/' + context}
        mounts = []
        for mount in service.get('volumes', []):
            if mount['type'] == 'bind':
                relative = Path(mount['source']).resolve().relative_to(root).as_posix()
                safe_path(relative)
                if not mount.get('read_only'):
                    raise ValueError('writable candidate bind')
                mounts.append({'type': 'bind', 'source': './candidate/' + relative,
                               'target': mount['target'], 'read_only': True,
                               'bind': {'create_host_path': False}})
            else:
                mounts.append({'type': 'volume', 'source': {'neo4j': 'graph',
                               'data-service': 'api_state', 'n8n': 'n8n_state'}[name],
                               'target': mount['target']})
        service['volumes'] = mounts
        selected[name] = service
    neo = selected['neo4j']
    neo['environment'] = {
        'NEO4J_AUTH': 'neo4j/${NEO4J_PASSWORD:?required}',
        'NEO4J_server_memory_heap_initial__size': '256m',
        'NEO4J_server_memory_heap_max__size': '512m',
        'NEO4J_server_memory_pagecache_size': '256m',
    }
    neo['healthcheck'] = {
        'test': ['CMD-SHELL', 'NEO4J_PASSWORD="$${NEO4J_AUTH#neo4j/}" cypher-shell -u neo4j "RETURN 1" >/dev/null 2>&1'],
        'interval': '5s', 'timeout': '5s', 'retries': 30, 'start_period': '30s',
    }
    ds = selected['data-service']
    ds['depends_on'] = {'neo4j': {'condition': 'service_healthy'}}
    ds['environment'] = {
        'DG_DATA_DIR': '/app/data', 'DG_KNOWLEDGE_REPO_ROOT': '/mnt/repo',
        'DG_DEPLOYMENT': 'multi-user', 'DG_ALLOW_SELF_REGISTRATION': 'false',
        # No browser/ingress: probe runs inside the API container over loopback.
        'DG_COOKIE_SECURE': 'false', 'NEO4J_URI': 'bolt://neo4j:7687',
        'NEO4J_USER': 'neo4j', 'NEO4J_PASSWORD': '${NEO4J_PASSWORD:?required}',
        'NEO4J_DATABASE': 'neo4j', 'LLM_MASTER_SECRET': '${LLM_MASTER_SECRET:?required}',
        'DG_SERVICE_TOKEN': '${DG_SERVICE_TOKEN:?required}',
        'DG_BOOTSTRAP_ADMIN_USER': 'sandbox-admin',
        'DG_BOOTSTRAP_ADMIN_PASSWORD': '${DG_BOOTSTRAP_ADMIN_PASSWORD:?required}',
        'DG_REASONER_URL': 'http://127.0.0.1:9', 'SPECKLE_BASE_URL': 'http://127.0.0.1:9',
        'N8N_INTERNAL_URL': 'http://n8n:5678',
    }
    ds['volumes'].append({'type': 'bind', 'source': './support/probe.py',
                          'target': '/app/sandbox_probe.py', 'read_only': True,
                          'bind': {'create_host_path': False}})
    n8n = selected['n8n']
    n8n['environment'] = {
        'N8N_ENCRYPTION_KEY': '${N8N_ENCRYPTION_KEY:?required}',
        'N8N_RESTRICT_FILE_ACCESS_TO': '/files/workflows;/files/evidence',
        'N8N_DEFAULT_BINARY_DATA_MODE': 'filesystem', 'N8N_DIAGNOSTICS_ENABLED': 'false',
        'N8N_VERSION_NOTIFICATIONS_ENABLED': 'false', 'N8N_TEMPLATES_ENABLED': 'false',
        'N8N_BLOCK_ENV_ACCESS_IN_NODE': 'true',
    }
    # Materialize a read-only union of exact candidate workflow bytes and the
    # two test files. Nested mounts cannot create targets in a read-only bind.
    for mount in n8n['volumes']:
        if mount['target'] == '/files/workflows':
            mount['source'] = './test-workflows'
    n8n['volumes'] += [
        {'type': 'volume', 'source': 'n8n_evidence', 'target': '/files/evidence'},
        {'type': 'bind', 'source': './support/evidence.cjs', 'target': '/files/probe/evidence.cjs', 'read_only': True},
    ]
    return {'services': selected, 'networks': {'sandbox': {'internal': True, 'enable_ipv6': False}},
            'volumes': {name: {} for name in ('graph', 'api_state', 'n8n_state', 'n8n_evidence')}}


def build(repo, revision, destination):
    repo, destination = Path(repo).resolve(), Path(destination).absolute()
    if not SHA.fullmatch(revision) or destination.exists() or repo == destination or repo in destination.parents:
        raise ValueError('new external destination and exact revision required')
    # Refuse a dirty implementation/policy rather than packaging a different runner.
    tool_paths = ('deploy/hosted/build_bundle_test.py', 'deploy/hosted/assemble.py',
                  'deploy/hosted/validate_manifest.py', 'deploy/hosted/release_core.py',
                  'deploy/hosted/release-allowlist.json', *SUPPORT)
    payload = {}
    for name in tool_paths:
        safe_path(name)
        try:
            committed = subprocess.check_output(['git', '-C', str(repo), 'show', f'{revision}:{name}'],
                                                 stderr=subprocess.DEVNULL)
        except subprocess.CalledProcessError:
            raise ValueError('missing committed preparation input') from None
        path = repo / name
        if path.is_symlink() or not path.is_file():
            raise ValueError('missing or linked preparation input')
        current = path.read_bytes()
        if name.endswith(('.py', '.ps1', '.md', '.cjs', '.json', '.txt')):
            current = current.replace(b'\r\n', b'\n')
            committed_compare = committed.replace(b'\r\n', b'\n')
        else:
            committed_compare = committed
        if current != committed_compare:
            raise ValueError('preparation input differs from exact commit')
        if name in SUPPORT:
            payload['support/' + Path(name).name] = committed
    with tempfile.TemporaryDirectory(prefix='dg-bundle-test-build-') as tmp:
        candidate = Path(tmp) / 'candidate'
        assemble(repo, revision, repo / 'deploy/hosted/release-allowlist.json', candidate)
        validate(candidate, allow_blocked=True, source=repo)
        services = merged_compose(candidate)
        model = runtime_model(candidate, services)
        manifest_bytes = (candidate / 'manifest.json').read_bytes()
        manifest = json.loads(manifest_bytes)
        payload.update({'candidate/' + name: (candidate / name).read_bytes() for name in manifest['files']})
        payload['candidate/manifest.json'] = manifest_bytes
        for name in manifest['files']:
            if name.startswith('n8n/workflows/'):
                payload['test-workflows/' + Path(name).name] = payload['candidate/' + name]
        for name in ('sandbox-file-read.json', 'sandbox-file-denied.json'):
            key = 'test-workflows/' + name
            if key in payload:
                raise ValueError('test workflow would replace candidate file')
            payload[key] = payload['support/' + name]
        payload['compose.json'] = (json.dumps(model, sort_keys=True, indent=2) + '\n').encode()
        package = {
            'schemaVersion': 1, 'kind': 'hosted-candidate-capability-test-not-release',
            'frameworkRevision': revision, 'candidateManifestSha256': digest(manifest_bytes),
            'images': 'unresolved-target-build-and-pull',
            'files': {name: digest(data) for name, data in sorted(payload.items())},
        }
        payload['bundle-test-manifest.json'] = (json.dumps(package, sort_keys=True, indent=2) + '\n').encode()
        destination.parent.mkdir(parents=True, exist_ok=True)
        with zipfile.ZipFile(destination, 'x', compression=zipfile.ZIP_DEFLATED) as archive:
            for name, data in sorted(payload.items()):
                info = zipfile.ZipInfo(name, date_time=(2026, 1, 1, 0, 0, 0))
                archive.writestr(info, data, compress_type=zipfile.ZIP_DEFLATED)
    return digest(destination.read_bytes())


def verify(destination):
    with zipfile.ZipFile(destination) as archive:
        names = archive.namelist()
        if len(names) != len(set(n.casefold() for n in names)):
            raise ValueError('duplicate member')
        for info in archive.infolist():
            safe_path(info.filename)
            if info.is_dir() or info.file_size > 32_000_000 or (info.external_attr >> 16) & 0o170000 == 0o120000:
                raise ValueError('unsafe archive entry')
        package = json.loads(archive.read('bundle-test-manifest.json'))
        if package['kind'] != 'hosted-candidate-capability-test-not-release' or set(names) != set(package['files']) | {'bundle-test-manifest.json'}:
            raise ValueError('package mismatch')
        if any(digest(archive.read(name)) != expected for name, expected in package['files'].items()):
            raise ValueError('package digest mismatch')
        candidate_bytes = archive.read('candidate/manifest.json')
        candidate = json.loads(candidate_bytes)
        if digest(candidate_bytes) != package['candidateManifestSha256'] or candidate['frameworkRevision'] != package['frameworkRevision']:
            raise ValueError('candidate identity mismatch')
        if {name for name in names if name.startswith('candidate/')} != {'candidate/' + name for name in candidate['files']} | {'candidate/manifest.json'}:
            raise ValueError('candidate membership mismatch')
        for name, expected in candidate['files'].items():
            if digest(archive.read('candidate/' + name)) != expected:
                raise ValueError('candidate digest mismatch')
    return digest(Path(destination).read_bytes())


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--repo')
    parser.add_argument('--revision')
    parser.add_argument('--output', required=True)
    parser.add_argument('--verify-only', action='store_true')
    args = parser.parse_args()
    try:
        value = verify(args.output) if args.verify_only else build(args.repo, args.revision, args.output)
        print('candidate test ZIP SHA-256: ' + value)
    except (ValueError, OSError, KeyError, TypeError, subprocess.CalledProcessError, zipfile.BadZipFile):
        print('Candidate test package BLOCKED (no raw tool output emitted)', file=sys.stderr)
        return 1
    return 0


if __name__ == '__main__':
    sys.exit(main())
