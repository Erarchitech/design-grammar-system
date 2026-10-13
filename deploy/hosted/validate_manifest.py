"""Validate an assembled hosted bundle; BLOCKED drafts cannot be released.

No secrets, interpolated Compose JSON or file contents are emitted on errors.
"""
import argparse
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tempfile

from release_core import HASH, IMAGE, SHA, matches, safe_path, scan_tree

COMPOSE = ('docker-compose.yml', 'docker-compose.multi-user.yml', 'docker-compose.hosted.yml')


def validate(root, *, allow_blocked=False, source=None):
    root = Path(root).absolute()
    if not root.is_dir() or root.is_symlink():
        raise ValueError('invalid bundle root')
    actual = scan_tree(root)
    if 'manifest.json' not in actual:
        raise ValueError('missing manifest')
    manifest = json.loads((root / 'manifest.json').read_text(encoding='utf-8'))
    if set(manifest) - {'schemaVersion', 'status', 'frameworkRevision', 'degramGitlink', 'files',
                        'images', 'unresolved', 'imageProvenance'}:
        raise ValueError('unexpected manifest field (logs/credentials forbidden)')
    if manifest.get('schemaVersion') != 1 or not SHA.fullmatch(str(manifest.get('frameworkRevision'))):
        raise ValueError('invalid framework revision')
    gitlink = manifest.get('degramGitlink', 'missing')
    if gitlink is not None and not SHA.fullmatch(str(gitlink)):
        raise ValueError('missing or invalid gitlink field')
    files = manifest.get('files')
    if not isinstance(files, dict) or not files or list(files) != sorted(files):
        raise ValueError('missing or unsorted file digest list')
    if any(not HASH.fullmatch(str(v)) for v in files.values()):
        raise ValueError('missing file digest')
    for path in files:
        safe_path(path)
    if set(actual) != set(files) | {'manifest.json'} or any(actual[k] != files[k] for k in files):
        raise ValueError('missing/extra file or digest mismatch')
    if source:
        repo = Path(source).resolve()
        rev = manifest['frameworkRevision']
        tree = subprocess.check_output(['git', '-C', str(repo), 'ls-tree', rev, 'apps/degram'],
                                       stderr=subprocess.DEVNULL, text=True).strip()
        if gitlink is not None and (not tree or tree.split()[2] != gitlink):
            raise ValueError('gitlink mismatch')
        if subprocess.check_output(['git', '-C', str(repo), 'rev-parse', '--verify', rev + '^{commit}'],
                                   stderr=subprocess.DEVNULL, text=True).strip() != rev:
            raise ValueError('framework revision mismatch')
    if 'deploy/hosted/release-allowlist.json' in files:
        policy = json.loads((root / 'deploy/hosted/release-allowlist.json').read_text(encoding='utf-8'))
        if policy.get('schemaVersion') != 1 or not isinstance(policy.get('inputs'), list):
            raise ValueError('invalid bundled selection policy')
        allowed = set()
        for entry in policy['inputs']:
            if not isinstance(entry, dict) or set(entry) - {'path', 'purpose', 'exclude'} or not entry.get('purpose'):
                raise ValueError('invalid policy entry')
            glob = entry['path']
            safe_path(glob)
            hits = {path for path in files if matches(path, glob)}
            if not hits:
                raise ValueError('missing policy input')
            for exclusion in entry.get('exclude', []):
                safe_path(exclusion)
                hits = {path for path in hits if not matches(path, exclusion)}
            allowed.update(hits)
        if set(files) != allowed:
            raise ValueError('undeclared bundle input')
        if policy.get('includeDegram') is not False or gitlink is not None:
            raise ValueError('component selection unsupported in this release')
    elif manifest.get('status') == 'FROZEN':
        raise ValueError('missing bundled selection policy')
    # Only named mounted source paths may be read. Never print config output.
    if all(name in files for name in COMPOSE):
        services = merged_compose(root)
        check_mounts(root, services, files)
    elif any(name in files for name in COMPOSE):
        raise ValueError('incomplete Compose set')
    else:
        services = None  # small synthetic export only
    if manifest.get('status') == 'BLOCKED':
        if not allow_blocked:
            raise ValueError('unresolved image provenance')
        if manifest.get('images') != {} or not manifest.get('unresolved') or manifest.get('imageProvenance'):
            raise ValueError('invalid draft marker')
        return len(files)
    if manifest.get('status') != 'FROZEN' or services is None:
        raise ValueError('not a frozen effective Compose release')
    images = manifest.get('images')
    if not isinstance(images, dict) or set(images) != set(services):
        raise ValueError('missing/extra service image digest')
    if any(not isinstance(v, str) or not IMAGE.fullmatch(v) for v in images.values()):
        raise ValueError('mutable or missing image digest')
    if not source:
        raise ValueError('source repository required for frozen revision check')
    provenance = manifest.get('imageProvenance')
    if not isinstance(provenance, dict) or set(provenance) != set(images):
        raise ValueError('missing image build/registry provenance')
    for name, service in services.items():
        if service.get('build'):
            if not isinstance(provenance[name], dict) or not provenance[name].get('sourceRevision') or not provenance[name].get('registryDigest'):
                raise ValueError('missing built image provenance')
            if provenance[name]['sourceRevision'] != manifest['frameworkRevision'] or provenance[name]['registryDigest'] != images[name]:
                raise ValueError('built image provenance mismatch')
        elif not isinstance(provenance[name], dict) or provenance[name].get('registryDigest') != images[name]:
            raise ValueError('registry digest mismatch')
        if service.get('image') != images[name]:
            raise ValueError('effective Compose is not pinned to manifest digest')
    if manifest.get('unresolved'):
        raise ValueError('unresolved candidate')
    return len(files)


def merged_compose(root):
    # Compose config is a parser only; no daemon/service invocation. --no-interpolate
    # and a scrubbed environment avoid reading local credentials or real .env.
    for file in COMPOSE:
        if not (root / file).is_file():
            raise ValueError('missing Compose file')
    with tempfile.TemporaryDirectory(prefix='dg-hosted-compose-') as temp:
        envfile = Path(temp) / 'fixture.env'
        keys = ('NEO4J_PASSWORD', 'LLM_MASTER_SECRET', 'DG_SERVICE_TOKEN',
                'DG_BOOTSTRAP_ADMIN_USER', 'DG_BOOTSTRAP_ADMIN_PASSWORD',
                'N8N_USER', 'N8N_PASSWORD', 'POSTGRES_PASSWORD', 'MINIO_ROOT_USER',
                'MINIO_ROOT_PASSWORD', 'SPECKLE_SESSION_SECRET')
        envfile.write_text(''.join(f'{k}=synthetic-{k.lower()}\n' for k in keys) +
                           'HOSTED_DG_HOST=dg.example.invalid\nHOSTED_SPECKLE_HOST=speckle.example.invalid\n'
                           'HOSTED_OBJECT_HOST=objects.example.invalid\nHOSTED_EDGE_CIDR=172.30.90.0/28\n'
                           'HOSTED_EDGE_IP=172.30.90.2\nHOSTED_EDGE_CERT_DIR=synthetic-external-certs\n')
        env = {k: v for k, v in os.environ.items() if k.upper() in
               ('PATH', 'PATHEXT', 'SYSTEMROOT', 'WINDIR', 'COMSPEC', 'TEMP', 'TMP', 'TMPDIR',
                'APPDATA', 'LOCALAPPDATA', 'PROGRAMFILES', 'PROGRAMFILES(X86)',
                'PROGRAMDATA', 'USERPROFILE', 'HOME')}
        env['DOCKER_CONFIG'] = str(Path(temp) / 'empty-config')
        command = [shutil.which('docker') or 'docker', 'compose', '--env-file', str(envfile)]
        for file in COMPOSE:
            command += ['-f', str(root / file)]
        command += ['config', '--no-interpolate', '--format', 'json']
        result = subprocess.run(command, cwd=temp, env=env, capture_output=True, timeout=45)
        if result.returncode:
            raise ValueError('offline merged Compose parse failed')
        return json.loads(result.stdout)['services']


def check_mounts(root, services, manifest_files):
    for name, service in services.items():
        for mount in service.get('volumes', []):
            source, target = str(mount.get('source', '')), str(mount.get('target', ''))
            if name == 'hosted-edge' and target == '/etc/caddy/certs':
                if mount.get('type') != 'volume' or not source.startswith('${HOSTED_EDGE_CERT_DIR:') or not mount.get('read_only'):
                    raise ValueError('external certificate mount unresolved')
                continue
            if mount.get('type') != 'bind':
                continue
            if target in ('/mnt/repo', '/files', '/app/ontology', '/app/fixtures', '/app/data'):
                raise ValueError('broad repository/runtime bind')
            if not mount.get('read_only'):
                raise ValueError('writable bind forbidden')
            if target == '/etc/caddy/certs':
                raise ValueError('unexpected certificate bind')
            source_path = Path(source).absolute()
            try:
                relative = source_path.relative_to(root)
            except ValueError:
                raise ValueError('bind outside bundle')
            safe_path(relative.as_posix())
            if source_path.is_symlink() or not source_path.exists():
                raise ValueError('missing/linked bind source')
            if source_path.is_dir():
                allowed = {'deploy/hosted/ingest': ('data-service', '/mnt/repo/hosted-ingest'),
                           'n8n/workflows': ('n8n', '/files/workflows')}
                if allowed.get(relative.as_posix()) != (name, target) or not any(
                    item.startswith(relative.as_posix() + '/') for item in manifest_files
                ):
                    raise ValueError('undeclared directory bind')
            elif relative.as_posix() not in manifest_files or (name, target, relative.as_posix()) not in {
                ('data-service', '/mnt/repo/llm/cypher_catalog.json', 'llm/cypher_catalog.json'),
                ('data-service', '/mnt/repo/llm/structure_rules.json', 'llm/structure_rules.json'),
                ('data-service', '/mnt/repo/ontology/DesignGrammar-V7.owl', 'ontology/DesignGrammar-V7.owl'),
                ('data-service', '/mnt/repo/ontology/export_to_markdown_v7.py', 'ontology/export_to_markdown_v7.py'),
                ('data-service', '/mnt/repo/spec/evidence-contract.schema.json', 'spec/evidence-contract.schema.json'),
                ('dg-reasoner', '/app/ontology/DesignGrammar-V7.owl', 'ontology/DesignGrammar-V7.owl'),
                ('dg-reasoner', '/app/ontology/dg-disjointness.ttl', 'ontology/dg-disjointness.ttl'),
                ('dg-reasoner', '/app/ontology/dg-shapes.ttl', 'ontology/dg-shapes.ttl'),
                ('speckle-postgres', '/docker-entrypoint-initdb.d/20-bootstrap-local.sql', 'speckle/bootstrap-local.sql'),
                ('hosted-edge', '/etc/caddy/Caddyfile', 'deploy/hosted/edge/Caddyfile'),
            }:
                raise ValueError('undeclared bind')
    for name, service in services.items():
        if name == 'ollama' or service.get('gpus') or service.get('devices'):
            raise ValueError('Ollama/GPU forbidden')
        if set(service.get('environment') or {}) & {'OLLAMA_URL', 'OLLAMA_HOST', 'OLLAMA_MODEL'}:
            raise ValueError('Ollama environment forbidden')
        for port in service.get('ports', []):
            if port.get('host_ip') != '127.0.0.1':
                raise ValueError('public port forbidden')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('bundle')
    parser.add_argument('--allow-blocked', action='store_true', help='offline integrity only, never release')
    parser.add_argument('--source', help='clean git repository for revision/gitlink cross-check')
    args = parser.parse_args()
    try:
        count = validate(args.bundle, allow_blocked=args.allow_blocked, source=args.source)
        print(f'{"BLOCKED draft integrity" if args.allow_blocked else "FROZEN release"}: {count} hashed files')
    except (ValueError, OSError, KeyError, TypeError, subprocess.CalledProcessError, json.JSONDecodeError) as error:
        print(f'VALIDATION BLOCKED: {type(error).__name__}', file=sys.stderr)
        return 1
    return 0


if __name__ == '__main__':
    sys.exit(main())
