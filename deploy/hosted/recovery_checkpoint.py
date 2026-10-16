"""Read-only complete-inventory/checksum validator, NOT a backup/restore adapter.

All stop/drain/export-method/image/key-reference fields are DECLARATIONS.
Checksums do not prove native format validity, exporter identity, queue discovery,
consistent S3 metadata/version coverage, key availability, or successful restore.
Never invokes Docker, generates keys, writes completion markers or changes data.
Caller supplies exact expected revision and recipient public-key fingerprint.
Trusted local filesystem without concurrent hostile same-user mutation required.
"""
import argparse

try:
    from .recovery_filesystem import reject_named_streams
except ImportError:
    from recovery_filesystem import reject_named_streams
import hashlib
import json
import os
from pathlib import Path
import re
import stat
import sys

MARKER = 'export-checkpoint.json'
ERROR = 'multi-store checkpoint rejected'
MAX_MANIFEST = 1024 * 1024
MAX_ENTRIES = 4096
MAX_BYTES = 64 * 1024 ** 3
WRITERS = frozenset({'data-service', 'dg-reasoner', 'n8n', 'speckle-server',
    'speckle-frontend-2', 'speckle-preview-service', 'speckle-webhook-service',
    'speckle-fileimport-service'})
SERVICES = WRITERS | {'neo4j', 'speckle-postgres', 'speckle-minio', 'speckle-redis'}
SECRETS = frozenset({'LLM_MASTER_SECRET', 'N8N_ENCRYPTION_KEY', 'POSTGRES_PASSWORD',
    'MINIO_ROOT_USER', 'MINIO_ROOT_PASSWORD', 'SPECKLE_SESSION_SECRET',
    'DG_SERVICE_TOKEN', 'DG_BOOTSTRAP_ADMIN_USER', 'DG_BOOTSTRAP_ADMIN_PASSWORD',
    'N8N_USER', 'N8N_PASSWORD'})
METHODS = {'neo4j': 'offline-native-dump', 'postgres': 'pg-dump-custom',
    'objects': 's3-objects-and-metadata', 'n8n': 'stopped-complete-state',
    'api': 'stopped-complete-state'}
# Logical recovery categories, NOT assumed physical queue/table names.
QUEUES = {
    'previewRequest': {'waiting', 'active', 'delayed'},
    'previewResponse': {'waiting', 'active', 'delayed'},
    'fileImport': {'queued', 'processing', 'retry'},
    'webhook': {'pending', 'processing', 'retry'},
    'legacyUpload': {'pending', 'processing'},
    'n8nExecution': {'new', 'running', 'waiting'},
}
FIELDS = {'schemaVersion', 'kind', 'sourceRevision', 'sourceProject',
    'destinationProject', 'images', 'stoppedWriters', 'queues', 'redisDisposition',
    'recipientFingerprint', 'keyReferences', 'exportMethods', 'files'}


class CheckpointError(ValueError):
    """Sanitized rejection: no owner paths, data, credentials or references."""


def _require(value):
    if not value:
        raise CheckpointError(ERROR)


def _match(pattern, value):
    return type(value) is str and re.fullmatch(pattern, value) is not None


def _fields(value, names):
    _require(type(value) is dict and set(value) == set(names))


def _pairs(items):
    result = {}
    for key, value in items:
        _require(key not in result)
        result[key] = value
    return result


def _regular(path, directory=False):
    reject_named_streams(path)
    info = path.lstat()
    _require(not stat.S_ISLNK(info.st_mode)
             and not getattr(info, 'st_file_attributes', 0) & 0x400)
    _require(stat.S_ISDIR(info.st_mode) if directory else
             stat.S_ISREG(info.st_mode) and info.st_nlink == 1)
    return info


def _signature(info):
    return info.st_dev, info.st_ino, info.st_size, info.st_mtime_ns


def _read(path, limit, digest=False):
    before = _regular(path)
    _require(before.st_size <= limit)
    fd = os.open(path, os.O_RDONLY | getattr(os, 'O_BINARY', 0) | getattr(os, 'O_NOFOLLOW', 0))
    with os.fdopen(fd, 'rb') as stream:
        _require(_signature(os.fstat(stream.fileno())) == _signature(before))
        result = hashlib.sha256() if digest else bytearray()
        count = 0
        while True:
            chunk = stream.read(min(1024 * 1024, limit - count + 1))
            if not chunk:
                break
            count += len(chunk)
            _require(count <= limit)
            if digest:
                result.update(chunk)
            else:
                result.extend(chunk)
        _require(_signature(os.fstat(stream.fileno())) == _signature(before))
    _require(count == before.st_size and _signature(_regular(path)) == _signature(before))
    return (count, result.hexdigest()) if digest else bytes(result)


def _path(name):
    _require(type(name) is str and len(name) <= 240)
    parts = name.split('/')
    _require(2 <= len(parts) <= 16 and parts[0] in METHODS)
    for part in parts:
        _require(_match(r'[A-Za-z0-9][A-Za-z0-9_.-]*', part)
                 and not part.endswith('.')
                 and not part.lower().endswith(('.tmp', '.partial', '.incomplete'))
                 and part.split('.')[0].upper() not in {'CON', 'PRN', 'AUX', 'NUL',
                     *(f'COM{i}' for i in range(1, 10)), *(f'LPT{i}' for i in range(1, 10))})
    return parts


def _validate(root, revision, fingerprint):
    _require(_match('[0-9a-f]{40}', revision) and _match('[0-9a-f]{64}', fingerprint))
    root = Path(os.path.abspath(root))
    for parent in reversed((root, *root.parents)):
        _regular(parent, directory=True)
    raw = _read(root / MARKER, MAX_MANIFEST)
    declaration = json.loads(raw, object_pairs_hook=_pairs,
                             parse_constant=lambda _: _require(False))
    _fields(declaration, FIELDS)
    d = declaration
    _require(type(d['schemaVersion']) is int and d['schemaVersion'] == 2
             and d['kind'] == 'dg-multi-store-export-declaration'
             and d['sourceRevision'] == revision and d['recipientFingerprint'] == fingerprint)
    for field in ('sourceProject', 'destinationProject'):
        _require(_match('dg-recovery-[0-9a-f]{32}', d[field]))
    _require(d['sourceProject'] != d['destinationProject'])
    _fields(d['images'], SERVICES)
    _require(all(_match('sha256:[0-9a-f]{64}', v) for v in d['images'].values()))
    _require(type(d['stoppedWriters']) is list
             and all(type(v) is str for v in d['stoppedWriters'])
             and d['stoppedWriters'] == sorted(WRITERS | {'neo4j'}))
    _fields(d['queues'], QUEUES)
    for group, counters in QUEUES.items():
        _fields(d['queues'][group], counters)
        _require(all(type(v) is int and v == 0 for v in d['queues'][group].values()))
    _require(d['redisDisposition'] == 'empty-not-restored')
    _fields(d['keyReferences'], SECRETS)
    _require(all(_match(r'escrow:[A-Za-z0-9][A-Za-z0-9_.-]{0,63}', v)
                 for v in d['keyReferences'].values()))
    _fields(d['exportMethods'], METHODS)
    _require(d['exportMethods'] == METHODS)
    _require(type(d['files']) is dict and 5 <= len(d['files']) <= MAX_ENTRIES)
    allowed_dirs, names, stores = set(), set(), set()
    total = 0
    for name, record in d['files'].items():
        parts = _path(name)
        _require(name.casefold() not in names)
        names.add(name.casefold())
        stores.add(parts[0])
        allowed_dirs.update('/'.join(parts[:i]) for i in range(1, len(parts)))
        _fields(record, {'bytes', 'sha256'})
        _require(type(record['bytes']) is int and 0 <= record['bytes'] <= MAX_BYTES
                 and _match('[0-9a-f]{64}', record['sha256']))
        total += record['bytes']
    _require(stores == set(METHODS) and total <= MAX_BYTES
             and len(allowed_dirs) + len(names) <= MAX_ENTRIES)
    actual = set()
    count = 0
    def scan(folder):
        nonlocal count
        for entry in folder.iterdir():
            count += 1
            _require(count <= MAX_ENTRIES + 1)
            name = entry.relative_to(root).as_posix()
            if entry.is_dir():
                _regular(entry, directory=True)
                _require(name in allowed_dirs)
                scan(entry)
            else:
                _regular(entry)
                _require(name == MARKER or name in d['files'])
                actual.add(name)
    scan(root)
    _require(actual == set(d['files']) | {MARKER})
    for name, record in d['files'].items():
        size, digest = _read(root / name, record['bytes'], digest=True)
        _require(size == record['bytes'] and digest == record['sha256'])
    _require(raw == _read(root / MARKER, MAX_MANIFEST))
    return {'schemaVersion': 1, 'status': 'OFFLINE_CHECKPOINT_VALIDATED_NOT_RECOVERY',
        'filesVerified': len(d['files']), 'bytesVerified': total,
        'nativeRecoveryProven': False, 'offMachineRestoreProven': False,
        'releaseAccepted': False}


def validate(root, revision, fingerprint):
    """Verify typed declarations and complete regular-file inventory read-only."""
    try:
        return _validate(root, revision, fingerprint)
    except (OSError, ValueError, TypeError, RecursionError, OverflowError):
        raise CheckpointError(ERROR) from None


class _Parser(argparse.ArgumentParser):
    def error(self, message):
        raise CheckpointError(ERROR)


def main(argv=None):
    parser = _Parser(description=__doc__, allow_abbrev=False)
    parser.add_argument('--export-directory', required=True)
    parser.add_argument('--revision', required=True)
    parser.add_argument('--recipient-fingerprint', required=True)
    try:
        args = parser.parse_args(argv)
        result = validate(args.export_directory, args.revision, args.recipient_fingerprint)
    except CheckpointError:
        print(json.dumps({'status': 'REJECTED', 'reason': ERROR}))
        return 1
    print(json.dumps(result, sort_keys=True))
    return 0


if __name__ == '__main__':
    sys.exit(main())
