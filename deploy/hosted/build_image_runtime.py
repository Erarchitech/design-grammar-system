"""Prepare four-image local load/smoke tooling, never a hosted release.

Consumes the previously issued exact-source ZIP; tooling is separately hashed.
No Docker, source checkout mutation, credential read, commit or push here.
"""
import argparse
import hashlib
import json
from pathlib import Path
import sys
import zipfile

from build_image_job import verify as verify_build
from release_core import safe_path

HERE = Path(__file__).resolve().parent
KIND = 'controlled-image-load-smoke-not-release'
BUILD_SHA = '9d391a82f5dac6bf53d8d83e5154c67c448fc4f56ea008e84c01c2f2916c7717'
REVISION = 'c82b92b29423c515e353e3fa4f9c17e9b0d83438'
SOURCE_SHA = '47cc21bfdc32af2fc37af93758f44eb8eb71b692d7084bdcccac969b7b544b23'
SERVICES = ('neo4j', 'dg-reasoner', 'data-service', 'design-grammars')


def encoded(value):
    return (json.dumps(value, indent=2, sort_keys=True) + '\n').encode()


def sha(value):
    return hashlib.sha256(value).hexdigest()


def bind(source, target):
    return {'type': 'bind', 'source': source, 'target': target, 'read_only': True,
            'bind': {'create_host_path': False}}


def runtime_model(images):
    services = {}
    for name in SERVICES:
        services[name] = {'image': images[name]['imageId'], 'pull_policy': 'never',
                          'platform': 'linux/amd64', 'networks': ['sandbox'],
                          'restart': 'no', 'mem_limit': '1500m' if name == 'neo4j' else '1250m',
                          'cpus': 1.0, 'pids_limit': 256, 'security_opt': ['no-new-privileges:true']}
    neo = services['neo4j']
    neo['environment'] = {
        'NEO4J_AUTH': 'neo4j/${NEO4J_PASSWORD:?required}',
        'NEO4J_server_memory_heap_initial__size': '256m',
        'NEO4J_server_memory_heap_max__size': '512m',
        'NEO4J_server_memory_pagecache_size': '256m'}
    neo['volumes'] = [{'type': 'volume', 'source': 'graph', 'target': '/data'}]
    neo['healthcheck'] = {
        'test': ['CMD-SHELL', 'NEO4J_PASSWORD="$${NEO4J_AUTH#neo4j/}" cypher-shell -u neo4j "RETURN 1" >/dev/null 2>&1'],
        'interval': '5s', 'timeout': '5s', 'retries': 36, 'start_period': '30s'}
    reasoner = services['dg-reasoner']
    reasoner['environment'] = {'NEO4J_URI': 'bolt://neo4j:7687', 'NEO4J_USER': 'neo4j',
                               'NEO4J_PASSWORD': '${NEO4J_PASSWORD:?required}', 'DG_REASONER_TIMEOUT_SECONDS': '30'}
    reasoner['depends_on'] = {'neo4j': {'condition': 'service_healthy'}}
    reasoner['volumes'] = [bind('./source/ontology/' + n, '/app/ontology/' + n)
                           for n in ('DesignGrammar-V7.owl', 'dg-disjointness.ttl', 'dg-shapes.ttl')]
    api = services['data-service']
    api['depends_on'] = {'neo4j': {'condition': 'service_healthy'}}
    api['environment'] = {
        'DG_DATA_DIR': '/app/data', 'DG_KNOWLEDGE_REPO_ROOT': '/mnt/repo',
        'DG_DEPLOYMENT': 'multi-user', 'DG_ALLOW_SELF_REGISTRATION': 'false',
        'DG_COOKIE_SECURE': 'false', 'NEO4J_URI': 'bolt://neo4j:7687',
        'NEO4J_USER': 'neo4j', 'NEO4J_PASSWORD': '${NEO4J_PASSWORD:?required}',
        'NEO4J_DATABASE': 'neo4j', 'LLM_MASTER_SECRET': '${LLM_MASTER_SECRET:?required}',
        'DG_SERVICE_TOKEN': '${DG_SERVICE_TOKEN:?required}',
        'DG_BOOTSTRAP_ADMIN_USER': 'sandbox-admin',
        'DG_BOOTSTRAP_ADMIN_PASSWORD': '${DG_BOOTSTRAP_ADMIN_PASSWORD:?required}',
        'DG_REASONER_URL': 'http://dg-reasoner:8000',
        'SPECKLE_BASE_URL': 'http://127.0.0.1:9', 'SPECKLE_INTERNAL_URL': 'http://127.0.0.1:9',
        'N8N_INTERNAL_URL': 'http://127.0.0.1:9', 'GH_BRIDGE_HOST': '127.0.0.1'}
    api['volumes'] = [{'type': 'volume', 'source': 'api_state', 'target': '/app/data'}]
    for name in ('llm/cypher_catalog.json', 'llm/structure_rules.json', 'ontology/DesignGrammar-V7.owl',
                 'ontology/export_to_markdown_v7.py', 'spec/evidence-contract.schema.json'):
        api['volumes'].append(bind('./source/' + name, '/mnt/repo/' + name))
    api['volumes'] += [bind('./source/deploy/hosted/ingest', '/mnt/repo/hosted-ingest'),
                       bind('./support/probe.py', '/app/image_runtime_probe.py'),
                       bind('./support/sandbox_probe.py', '/app/sandbox_probe.py')]
    services['design-grammars']['environment'] = {'DATA_SERVICE_URL': '/data-service',
                                                  'SPECKLE_BASE_URL': 'http://127.0.0.1:9'}
    return {'services': services, 'networks': {'sandbox': {'internal': True, 'enable_ipv6': False}},
            'volumes': {'graph': {}, 'api_state': {}}}


def prepare(build_zip, output):
    output = Path(output).absolute()
    if output.exists() or output.is_symlink():
        raise ValueError('new destination required')
    if verify_build(build_zip) != BUILD_SHA:
        raise ValueError('wrong issued build package')
    evidence = json.loads((HERE / 'image-runtime/c82b92b-build-evidence.json').read_bytes())
    if evidence['sourceRevision'] != REVISION or evidence['packageZipSha256'] != BUILD_SHA:
        raise ValueError('evidence identity mismatch')
    with zipfile.ZipFile(build_zip) as archive:
        payload = {n: archive.read(n) for n in archive.namelist() if n.startswith('source/')}
        payload['support/build-job-manifest.json'] = archive.read('build-job-manifest.json')
        # The capability probe was committed before this build. Reuse its exact
        # source bytes rather than silently consuming a dirty checkout.
        import subprocess
        payload['support/sandbox_probe.py'] = subprocess.check_output(
            ['git', '-C', str(HERE.parents[1]), 'show', REVISION + ':deploy/hosted/sandbox/probe.py'])
    for name in ('Run-ImageRuntime.ps1', 'runtime-execution.ps1', 'probe.py', 'README.md'):
        payload['support/' + name] = (HERE / 'image-runtime' / name).read_bytes()
    payload['support/empty-env.txt'] = b'# Deliberately no environment values.\n'
    payload['build-evidence.json'] = encoded(evidence)
    payload['compose.json'] = encoded(runtime_model(evidence['images']))
    manifest = {'schemaVersion': 1, 'kind': KIND, 'sourceRevision': REVISION,
                'sourceManifestSha256': SOURCE_SHA, 'buildPackageZipSha256': BUILD_SHA,
                'target': 'DESKTOP-OS4Q8CP', 'toolingStatus': 'hashed-preparation-tools-not-part-of-source-revision',
                'images': evidence['images'], 'files': {n: sha(v) for n, v in sorted(payload.items())}}
    payload['image-runtime-manifest.json'] = encoded(manifest)
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
            raise ValueError('duplicate member')
        for info in archive.infolist():
            safe_path(info.filename)
            mode = info.external_attr >> 16 & 0o170000
            if info.is_dir() or mode not in (0, 0o100000) or info.file_size > 32_000_000:
                raise ValueError('unsafe member')
        manifest = json.loads(archive.read('image-runtime-manifest.json'))
        if (manifest['kind'] != KIND or manifest['sourceRevision'] != REVISION or
                manifest['buildPackageZipSha256'] != BUILD_SHA or manifest['sourceManifestSha256'] != SOURCE_SHA):
            raise ValueError('package identity mismatch')
        if set(names) != set(manifest['files']) | {'image-runtime-manifest.json'}:
            raise ValueError('membership mismatch')
        support = {'support/' + n for n in ('Run-ImageRuntime.ps1', 'probe.py', 'README.md',
                   'empty-env.txt', 'sandbox_probe.py', 'build-job-manifest.json', 'runtime-execution.ps1')}
        if {n for n in names if not n.startswith('source/')} != support | {'compose.json', 'build-evidence.json', 'image-runtime-manifest.json'}:
            raise ValueError('unexpected support membership')
        evidence = json.loads((HERE / 'image-runtime/c82b92b-build-evidence.json').read_bytes())
        if encoded(manifest['images']) != encoded(evidence['images']) or archive.read('build-evidence.json') != encoded(evidence):
            raise ValueError('image contract mismatch')
        for name, digest in manifest['files'].items():
            if sha(archive.read(name)) != digest:
                raise ValueError('digest mismatch')
        source_raw = archive.read('source/manifest.json')
        source = json.loads(source_raw)
        if sha(source_raw) != SOURCE_SHA or source['frameworkRevision'] != REVISION:
            raise ValueError('source mismatch')
        if {n for n in names if n.startswith('source/')} != {'source/' + n for n in source['files']} | {'source/manifest.json'}:
            raise ValueError('source membership mismatch')
        for name, value in source['files'].items():
            if sha(archive.read('source/' + name)) != value:
                raise ValueError('source digest mismatch')
        if encoded(json.loads(archive.read('compose.json'))) != encoded(runtime_model(manifest['images'])):
            raise ValueError('runtime model mismatch')
    return sha(Path(path).read_bytes())


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--build-zip')
    parser.add_argument('--output', required=True)
    parser.add_argument('--verify-only', action='store_true')
    args = parser.parse_args()
    try:
        print(verify(args.output) if args.verify_only else prepare(args.build_zip, args.output))
    except (OSError, ValueError, KeyError, TypeError, zipfile.BadZipFile):
        print('Image runtime package BLOCKED (raw input not emitted)', file=sys.stderr)
        return 1
    return 0


if __name__ == '__main__':
    sys.exit(main())
