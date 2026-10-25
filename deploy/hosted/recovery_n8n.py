"""Complete stopped .n8n file-tree adapter; no CLI, services or SQLite SQL.

Supports ONLY n8n 2.4.8 SQLite stopped-tree qualification scope. Copies all files,
including config/key, WAL/SHM, binary data and empty directories. Never opens a
SQLite connection (which might checkpoint it). No workflow activation or key
regeneration. A trusted outer runner MUST prove stopped processes, no external
binary store, matching image/version/key, approved scope, private scratch/DACL,
empty owned target and trusted archive provenance. Callback True is NOT proof.
Trusted local filesystem/no hostile concurrent mutation. POSIX metadata/ACLs,
non-Windows xattrs and native n8n recovery are NOT qualified by this adapter.
"""
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import stat
import time
import uuid
try:
    from .recovery_filesystem import reject_named_streams
except ImportError:
    from recovery_filesystem import reject_named_streams

MAX_FILES = 4096
MAX_BYTES = 64 * 1024 ** 3
MAX_MANIFEST = 1024 * 1024
ERROR = 'n8n state operation rejected'


class StateError(ValueError):
    pass


def _require(value):
    if not value:
        raise StateError(ERROR)


def _regular(path, directory=False):
    reject_named_streams(path)
    info = path.lstat()
    _require(not stat.S_ISLNK(info.st_mode) and not getattr(info, 'st_file_attributes', 0) & 0x400)
    _require(stat.S_ISDIR(info.st_mode) if directory else stat.S_ISREG(info.st_mode) and info.st_nlink == 1)
    return info


def _root(path):
    path = Path(os.path.abspath(path))
    for parent in reversed((path, *path.parents)):
        _regular(parent, True)
    return path


def _name(name):
    _require(type(name) is str and len(name) <= 240)
    parts = name.split('/')
    _require(1 <= len(parts) <= 16)
    for part in parts:
        _require(re.fullmatch(r'[A-Za-z0-9_.-]+', part) and part not in ('.', '..')
                 and not part.endswith('.') and
                 part.split('.')[0].upper() not in {'CON', 'PRN', 'AUX', 'NUL',
                     *(f'COM{i}' for i in range(1, 10)), *(f'LPT{i}' for i in range(1, 10))})
    return name


def _hash(path):
    before = _regular(path)
    _require(before.st_size <= MAX_BYTES)
    count = 0
    digest = hashlib.sha256()
    with path.open('rb') as source:
        while chunk := source.read(1024 * 1024):
            count += len(chunk)
            _require(count <= MAX_BYTES)
            digest.update(chunk)
    after = _regular(path)
    _require((before.st_dev, before.st_ino, before.st_size, before.st_mtime_ns) ==
             (after.st_dev, after.st_ino, after.st_size, after.st_mtime_ns) and count == before.st_size)
    return {'bytes': count, 'sha256': digest.hexdigest()}


def _inventory(root):
    files, directories, names = {}, [], set()
    total = 0
    def scan(folder):
        nonlocal total
        entries = []
        remaining = MAX_FILES - len(names)
        with os.scandir(folder) as iterator:
            for entry in iterator:
                _require(len(entries) < remaining)
                entries.append(Path(entry.path))
        for path in sorted(entries):
            name = _name(path.relative_to(root).as_posix())
            _require(name.casefold() not in names and len(names) < MAX_FILES)
            names.add(name.casefold())
            if path.is_dir():
                _regular(path, True)
                directories.append(name)
                scan(path)
            else:
                files[name] = _hash(path)
                total += files[name]['bytes']
                _require(total <= MAX_BYTES)
    scan(root)
    _require('config' in files and 'database.sqlite' in files)
    _require(files['config']['bytes'] <= MAX_MANIFEST)
    config = json.loads((root / 'config').read_bytes(), object_pairs_hook=_pairs)
    _require(type(config) is dict and type(config.get('encryptionKey')) is str
             and 0 < len(config['encryptionKey']) <= 4096)
    # Environment/external configuration still MUST be checked by the outer runner.
    if 'database' in config:
        _require(type(config['database']) is dict and config['database'].get('type') == 'sqlite')
    return {'files': files, 'directories': sorted(directories)}


def _new_destination(source, destination):
    destination = Path(os.path.abspath(destination))
    _root(destination.parent)
    reject_named_streams(destination.parent)
    _name(destination.name)
    _require(not os.path.lexists(destination))
    _require(source != destination and source not in destination.parents and destination not in source.parents)
    return destination


def _copy(source, destination, inventory, *, create=True):
    if create:
        destination.mkdir(mode=0o700)
    for name in sorted(inventory['directories'], key=lambda s: (s.count('/'), s)):
        (destination / name).mkdir(mode=0o700)
    for name in inventory['files']:
        with (source / name).open('rb') as src:
            fd = os.open(destination / name, os.O_CREAT | os.O_EXCL | os.O_WRONLY | getattr(os, 'O_BINARY', 0), 0o600)
            with os.fdopen(fd, 'wb') as dst:
                count = 0
                while chunk := src.read(1024 * 1024):
                    count += len(chunk)
                    _require(count <= inventory['files'][name]['bytes'])
                    dst.write(chunk)
                dst.flush()
                os.fsync(dst.fileno())
    _require(_inventory(destination) == inventory)


def _pairs(pairs):
    result = {}
    for key, value in pairs:
        _require(key not in result)
        result[key] = value
    return result


def _publish_new(source, destination):
    # Keep Windows no-replace rename; retry only known transient sharing denials.
    for attempt in range(8):
        try:
            os.rename(source, destination)
            return
        except PermissionError as error:
            if (os.name != 'nt' or getattr(error, 'winerror', None) not in (5, 32, 33)
                    or attempt == 7 or os.path.lexists(destination)):
                raise
            time.sleep(0.025 * (attempt + 1))


def export_state(source, destination, *, version, attest):
    staging = None
    try:
        _require(version == '2.4.8' and callable(attest))
        source = _root(source)
        destination = _new_destination(source, destination)
        _require(attest({'operation': 'n8n-export', 'version': version}) is True)
        inventory = _inventory(source)
        candidate = destination.parent / ('.n8n-stage-' + uuid.uuid4().hex)
        candidate.mkdir(mode=0o700)
        staging = candidate
        _copy(source, staging / 'tree', inventory)
        _require(_inventory(source) == inventory)
        manifest = {'schemaVersion': 1, 'version': version, **inventory,
                    'nativeRecoveryProven': False}
        raw = json.dumps(manifest, sort_keys=True, separators=(',', ':')).encode()
        _require(len(raw) <= MAX_MANIFEST)
        with (staging / 'state-manifest.json').open('xb') as stream:
            stream.write(raw)
        _require(not os.path.lexists(destination))
        _publish_new(staging, destination)
        staging = None
        return manifest
    except Exception:
        raise StateError(ERROR) from None
    finally:
        if staging is not None and staging.exists():
            try:
                shutil.rmtree(staging)
            except Exception:
                raise StateError(ERROR) from None


def restore_state(package, destination, *, expected_manifest_sha256, version, attest):
    staging = None
    try:
        _require(version == '2.4.8' and callable(attest) and type(expected_manifest_sha256) is str
                 and re.fullmatch('[0-9a-f]{64}', expected_manifest_sha256))
        package = _root(package)
        destination = _new_destination(package, destination)
        _require({p.name for p in package.iterdir()} == {'tree', 'state-manifest.json'})
        marker = package / 'state-manifest.json'
        _require(_regular(marker).st_size <= MAX_MANIFEST)
        raw = marker.read_bytes()
        _require(hashlib.sha256(raw).hexdigest() == expected_manifest_sha256)
        d = json.loads(raw, object_pairs_hook=_pairs)
        _require(type(d) is dict and set(d) == {'schemaVersion', 'version', 'files', 'directories', 'nativeRecoveryProven'})
        _require(type(d['schemaVersion']) is int and d['schemaVersion'] == 1
                 and d['version'] == version and d['nativeRecoveryProven'] is False)
        tree = _root(package / 'tree')
        inventory = _inventory(tree)
        _require(d['files'] == inventory['files'] and d['directories'] == inventory['directories'])
        _require(attest({'operation': 'n8n-restore', 'version': version,
                        'manifestSha256': expected_manifest_sha256}) is True)
        _require(_inventory(tree) == inventory and marker.read_bytes() == raw)
        candidate = destination.parent / ('.n8n-stage-' + uuid.uuid4().hex)
        candidate.mkdir(mode=0o700)
        staging = candidate
        _copy(tree, staging, inventory, create=False)
        _require(_inventory(tree) == inventory and not os.path.lexists(destination))
        _publish_new(staging, destination)
        staging = None
        return {'status': 'N8N_TREE_COPIED_NOT_RECOVERY', 'nativeRecoveryProven': False}
    except Exception:
        raise StateError(ERROR) from None
    finally:
        if staging is not None and staging.exists():
            try:
                shutil.rmtree(staging)
            except Exception:
                raise StateError(ERROR) from None
