"""Bounded synthetic TWO-store offline transport, not a production backup.

Caller stops writers and supplies an offline native neo4j.dump and full API
state tree. Encryption proves neither consistency nor exporter identity and
this slice does not close HOST-04. Probe state (including any cookie/password)
is encrypted with everything else; seal never stages plaintext on disk.

AES-256-GCM, random 96-bit nonce, fixed AAD; RECOVERY_KEY is exactly 64 hex
characters supplied ephemerally by the caller, never written or reported.
In-memory format: <=128 MiB plaintext including manifest, <=64 MiB/file,
<=1024 files+directories including the state root and exchange inputs.
Multiple bounded buffers are used, so process RSS can exceed 128 MiB.

Use only trusted, private, offline container filesystems; hostile concurrent
filesystem mutation, secure erasure, swap/crash dumps and power-loss durability
are outside this contract. Open validates everything before staging plaintext
in protected staging siblings of output files on each destination filesystem.
Publication is exclusive, not a two-volume
transaction. The exchange completion marker is published LAST. On interruption
without a marker, discard the partial destination; never treat it as complete.
Catchable failures attempt rollback; SIGKILL may leave protected staging.

  python snapshot.py seal --state /state --exchange /exchange
  python snapshot.py open --state /state --exchange /exchange
  python snapshot.py check-negative --state /state --exchange /exchange
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import stat
import struct
import sys
import tempfile

from cryptography.hazmat.primitives.ciphers.aead import AESGCM

REVISION = 'c82b92b29423c515e353e3fa4f9c17e9b0d83438'
MAGIC = b'DGSNAP1\n'
AAD = b'DG synthetic two-store snapshot v1'
MARKER = 'snapshot-complete.json'
MAX_TOTAL = 128 * 1024 * 1024
MAX_FILE = 64 * 1024 * 1024
MAX_ENTRIES = 1024
MAX_MANIFEST = 512 * 1024
ERROR = 'snapshot operation rejected'
STORES = {'api-state': 'state', 'neo4j-native-dump': 'neo4j.dump', 'probe-state': 'probe-state.json'}


class SnapshotError(ValueError):
    """Sanitized failure, with no input values."""


def _reject():
    raise SnapshotError(ERROR)


def _json(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'), ensure_ascii=True).encode('ascii')


def _key():
    value = os.environ['RECOVERY_KEY']
    if not re.fullmatch('[0-9a-fA-F]{64}', value):
        _reject()
    return bytes.fromhex(value)


def _regular(path, directory=False):
    info = path.lstat()
    if (stat.S_ISLNK(info.st_mode) or getattr(info, 'st_file_attributes', 0) & 0x400
            or not (stat.S_ISDIR(info.st_mode) if directory else stat.S_ISREG(info.st_mode))
            or (not directory and info.st_nlink != 1)):
        _reject()
    return info


def _parents(path):
    for parent in reversed((path, *path.parents)):
        _regular(parent, directory=True)


def _read(path, limit):
    _parents(path.parent)
    before = _regular(path)
    if limit < 0 or before.st_size > limit:
        _reject()
    fd = os.open(path, os.O_RDONLY | getattr(os, 'O_NOFOLLOW', 0) | getattr(os, 'O_BINARY', 0))
    with os.fdopen(fd, 'rb') as stream:
        opened = os.fstat(stream.fileno())
        if (opened.st_dev, opened.st_ino, opened.st_nlink) != (before.st_dev, before.st_ino, 1):
            _reject()
        data = stream.read(limit + 1)
        after = os.fstat(stream.fileno())
    if (len(data) > limit or len(data) != before.st_size
            or (after.st_size, after.st_mtime_ns, after.st_nlink) != (before.st_size, before.st_mtime_ns, 1)):
        _reject()
    return data


def _scan(state):
    _parents(state)
    result = []
    def walk(directory):
        for path in sorted(directory.iterdir()):
            name = _name('state/' + path.relative_to(state).as_posix())
            info = path.lstat()
            directory_entry = stat.S_ISDIR(info.st_mode)
            _regular(path, directory=directory_entry)
            if len(result) + 3 >= MAX_ENTRIES:
                _reject()
            result.append((path, name, directory_entry))
            if directory_entry:
                walk(path)
    walk(state)
    return result


def _collect(state, exchange):
    entries, body = [], bytearray()
    def add(path, name, store):
        directory = path.is_dir()
        data = b'' if directory else _read(path, min(MAX_FILE, MAX_TOTAL - len(body)))
        entries.append({'path': name, 'store': store, 'type': 'directory' if directory else 'file',
                        'size': len(data), 'sha256': hashlib.sha256(data).hexdigest()})
        body.extend(data)
    inventory = _scan(state)
    add(state, 'state', 'api-state')
    for path, name, _ in inventory:
        add(path, name, 'api-state')
    add(exchange / 'neo4j.dump', 'neo4j.dump', 'neo4j-native-dump')
    add(exchange / 'probe-state.json', 'probe-state.json', 'probe-state')
    if inventory != _scan(state):
        _reject()
    metadata = _json({'schema': 1, 'framework_revision': REVISION, 'stores': STORES, 'entries': entries})
    if len(metadata) > MAX_MANIFEST or len(body) + 4 + len(metadata) > MAX_TOTAL:
        _reject()
    plain = struct.pack('>I', len(metadata)) + metadata + body
    _validate(plain)
    return plain


def _fields(value, fields):
    if type(value) is not dict or set(value) != set(fields.split()):
        _reject()


def _name(name):
    if type(name) is not str or len(name) > 240 or len(name.split('/')) > 16:
        _reject()
    for part in name.split('/'):
        if (part in ('', '.', '..') or not re.fullmatch(r'[A-Za-z0-9_.-]+', part)
                or part.endswith('.') or part.split('.')[0].upper() in {
                    'CON', 'PRN', 'AUX', 'NUL', *(f'COM{i}' for i in range(1, 10)),
                    *(f'LPT{i}' for i in range(1, 10))}):
            _reject()
    return name


def _load(data):
    def pairs(items):
        result = {}
        for key, value in items:
            if key in result:
                _reject()
            result[key] = value
        return result
    return json.loads(data, object_pairs_hook=pairs, parse_constant=lambda _: _reject())


def _validate(plain):
    if len(plain) < 4 or len(plain) > MAX_TOTAL:
        _reject()
    length = struct.unpack('>I', plain[:4])[0]
    if length > MAX_MANIFEST or length > len(plain) - 4:
        _reject()
    manifest = _load(plain[4:4 + length])
    _fields(manifest, 'schema framework_revision stores entries')
    if (type(manifest['schema']) is not int or manifest['schema'] != 1
            or manifest['framework_revision'] != REVISION or manifest['stores'] != STORES):
        _reject()
    entries = manifest['entries']
    if type(entries) is not list or not 3 <= len(entries) <= MAX_ENTRIES:
        _reject()
    offset, result, seen, dirs = 4 + length, [], set(), set()
    for entry in entries:
        _fields(entry, 'path store type size sha256')
        name = _name(entry['path'])
        kind, size = entry['type'], entry['size']
        if (name.casefold() in seen or kind not in ('directory', 'file')
                or type(size) is not int or not 0 <= size <= MAX_FILE
                or type(entry['sha256']) is not str or not re.fullmatch('[0-9a-f]{64}', entry['sha256'])):
            _reject()
        seen.add(name.casefold())
        if name == 'state' or name.startswith('state/'):
            if entry['store'] != 'api-state' or (name == 'state' and kind != 'directory'):
                _reject()
        elif name in ('neo4j.dump', 'probe-state.json'):
            if kind != 'file' or entry['store'] != ('probe-state' if name == 'probe-state.json' else 'neo4j-native-dump'):
                _reject()
        else:
            _reject()
        parent = name.rpartition('/')[0]
        if parent and parent not in dirs:
            _reject()
        if kind == 'directory':
            if size != 0:
                _reject()
            dirs.add(name)
        end = offset + size
        data = memoryview(plain)[offset:end]
        if end > len(plain) or hashlib.sha256(data).hexdigest() != entry['sha256']:
            _reject()
        result.append((entry, data))
        offset = end
    if offset != len(plain) or not {'state', 'neo4j.dump', 'probe-state.json'} <= seen:
        _reject()
    return result


def _decode(envelope):
    if not envelope.startswith(MAGIC) or len(envelope) < 36:
        _reject()
    plain = AESGCM(_key()).decrypt(envelope[8:20], envelope[20:], AAD)
    return _validate(plain)


def _write(path, data):
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | getattr(os, 'O_BINARY', 0), 0o600)
    with os.fdopen(fd, 'wb') as stream:
        stream.write(data)
        stream.flush()
        os.fsync(stream.fileno())


def _publish_file(source, target):
    # Hard-link publication is atomic/no-replace even on POSIX (rename is not).
    os.link(source, target)


def seal(state, exchange):
    try:
        state, exchange = Path(state).absolute(), Path(exchange).absolute()
        _parents(exchange)
        if state.is_relative_to(exchange) or exchange.is_relative_to(state):
            _reject()
        if os.path.lexists(exchange / 'backup.enc'):
            _reject()
        key = _key()
        plain = _collect(state, exchange)
        nonce = os.urandom(12)
        envelope = MAGIC + nonce + AESGCM(key).encrypt(nonce, plain, AAD)
        with tempfile.TemporaryDirectory(prefix='.snapshot-', dir=exchange) as temp:
            stage = Path(temp) / 'backup.enc'
            _write(stage, envelope)
            _publish_file(stage, exchange / 'backup.enc')
    except Exception:
        raise SnapshotError(ERROR) from None


def open_snapshot(state, exchange):
    created = []
    try:
        state, exchange = Path(state).absolute(), Path(exchange).absolute()
        _parents(state)
        _parents(exchange)
        if (state.is_relative_to(exchange) or exchange.is_relative_to(state)
                or any(state.iterdir())
                or any(os.path.lexists(exchange / name) for name in ('neo4j.dump', 'probe-state.json', MARKER))):
            _reject()
        entries = _decode(_read(exchange / 'backup.enc', MAX_TOTAL + 36))
        with tempfile.TemporaryDirectory(prefix='.snapshot-', dir=state) as api_temp, \
                tempfile.TemporaryDirectory(prefix='.snapshot-', dir=exchange) as exchange_temp:
            api_stage, exchange_stage = Path(api_temp), Path(exchange_temp)
            for entry, data in entries:
                name = entry['path']
                target = api_stage / name[6:] if name.startswith('state/') else exchange_stage / name
                if name == 'state':
                    continue
                if entry['type'] == 'directory':
                    target.mkdir(mode=0o700)
                else:
                    _write(target, data)
            for path in sorted(api_stage.rglob('*')):
                target = state / path.relative_to(api_stage)
                if path.is_dir():
                    target.mkdir(mode=0o700)
                else:
                    _publish_file(path, target)
                created.append(target)
            for name in ('neo4j.dump', 'probe-state.json'):
                target = exchange / name
                _publish_file(exchange_stage / name, target)
                created.append(target)
            _write(exchange_stage / MARKER, _json({'schema': 1, 'state': 'complete', 'framework_revision': REVISION}))
            _publish_file(exchange_stage / MARKER, exchange / MARKER)
            created.append(exchange / MARKER)
    except BaseException as error:
        for path in reversed(created):
            try:
                path.rmdir() if path.is_dir() else path.unlink()
            except OSError:
                pass
        if isinstance(error, (KeyboardInterrupt, SystemExit)):
            raise
        raise SnapshotError(ERROR) from None


def check_negative(state, exchange):
    """Authenticate the real bundle, then prove two failures in throwaway dirs."""
    original = os.environ.get('RECOVERY_KEY')
    try:
        state, exchange = Path(state).absolute(), Path(exchange).absolute()
        _parents(state)
        _parents(exchange)
        envelope = _read(exchange / 'backup.enc', MAX_TOTAL + 36)
        _decode(envelope)  # Do not report success for an invalid baseline/key.
        wrong = bytes([_key()[0] ^ 1]) + _key()[1:]
        with tempfile.TemporaryDirectory(prefix='.snapshot-negative-', dir=exchange) as temp:
            root = Path(temp)
            for index, (key, data) in enumerate(((wrong.hex(), envelope), (original, envelope[:-1]))):
                test = root / str(index)
                test.mkdir(mode=0o700)
                destination, inputs = test / 'state', test / 'exchange'
                destination.mkdir(mode=0o700)
                inputs.mkdir(mode=0o700)
                _write(inputs / 'backup.enc', data)
                os.environ['RECOVERY_KEY'] = key
                try:
                    open_snapshot(destination, inputs)
                except SnapshotError:
                    pass
                else:
                    _reject()
                if (any(destination.iterdir()) or sorted(p.name for p in inputs.iterdir()) != ['backup.enc']
                        or (inputs / 'backup.enc').read_bytes() != data
                        or sorted(p.name for p in test.iterdir()) != ['exchange', 'state']):
                    _reject()
    except Exception:
        raise SnapshotError(ERROR) from None
    finally:
        if original is None:
            os.environ.pop('RECOVERY_KEY', None)
        else:
            os.environ['RECOVERY_KEY'] = original


class _Parser(argparse.ArgumentParser):
    def error(self, message):
        self.exit(2, ERROR + '\n')


def main(argv=None):
    parser = _Parser(description='Bounded synthetic offline snapshot helper')
    parser.add_argument('mode', choices=('seal', 'open', 'check-negative'))
    parser.add_argument('--state', default='/state')
    parser.add_argument('--exchange', default='/exchange')
    args = parser.parse_args(argv)
    try:
        {'seal': seal, 'open': open_snapshot, 'check-negative': check_negative}[args.mode](args.state, args.exchange)
    except (Exception, KeyboardInterrupt):
        print(ERROR, file=sys.stderr)
        return 1
    print({'seal': 'snapshot sealed', 'open': 'snapshot opened',
           'check-negative': 'snapshot negative checks passed'}[args.mode])
    return 0


if __name__ == '__main__':
    sys.exit(main())
