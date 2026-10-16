"""Encrypted OFFLINE transport of an already exported regular directory.

This authenticates input bytes, NOT exporter identity, quiescence, or correctness
of Neo4j/Postgres/MinIO/n8n exports. Anyone with the public key can seal an
archive. This is not a live backup/restore adapter and DOES NOT close HOST-04.
The caller must stop writers and supply export-complete.json LAST, containing
exactly {"schema":1,"state":"complete","framework_revision":"<40 lowercase hex>"}.
That marker is a declaration, not independent evidence of consistency; <=4096
bytes. export-in-progress.json/export-incomplete.json and .partial/.incomplete/
.tmp path components are rejected even if the completion marker exists.

Reference/synthetic format v1: <=8 MiB plaintext including <=256 KiB manifest,
<=1024 files+directories, <=240 ASCII characters/path, <=9 MiB envelope.
No compression/tar/zip; bounded reads and few bounded byte buffers keep archive
working memory below 64 MiB (not total interpreter/crypto-library RSS). This is
NOT a large production database archiver. Plaintext only exists in RAM, input,
and protected restore staging/final destination; OS swap/crash dumps and secure
erasure are outside this contract. No persistent plaintext during seal.

RSA 2048..8192, OAEP SHA256 wraps a fresh random AES-256-GCM key. Header is AAD;
encrypted manifest binds sorted paths, sizes, SHA256, exact revision, recipient
SPKI SHA256 fingerprint and caller-chosen key-id. Strict schemas reject extras.
Keys are supplied as existing PEM paths, never generated for users or reported.
Encrypted private PEM prompts via getpass (no password argument/env support).

Parents must already exist on a trusted local filesystem, without links or
reparse points; concurrent hostile same-user changes are out of scope. Staging
is same-parent mode 0700 (Python >=3.13 on Windows applies a protected ACL for
current user/admins); files inherit that ACL, POSIX files use 0600. Publication
uses an atomic no-replace rename (Windows/Linux/macOS); unsupported OS fails
closed. Cleanup occurs on exceptions/interrupts, not uncatchable power loss or
SIGKILL; orphaned protected staging may then require owner cleanup. No claim of
power-loss durability or secure deletion. Existing destinations are never used.

CLI (cryptography must be installed in the selected interpreter):
  python recovery_archive.py seal --source EXPORT --output SNAPSHOT.dgar \
      --public-key RECIPIENT.pem --revision FULL_SHA --key-id lab-2026
  python recovery_archive.py open --archive SNAPSHOT.dgar --destination NEW_DIR \
      --private-key RECIPIENT-private.pem --revision FULL_SHA --key-id lab-2026
"""
import argparse
import ctypes
import getpass
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import stat
import struct
import sys
import tempfile
import time

from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import padding, rsa
from cryptography.hazmat.primitives.ciphers.aead import AESGCM

try:
    from .release_core import safe_path
except ImportError:
    from release_core import safe_path

MAGIC = b'DGAR001\n'
MAX_PLAINTEXT = 8 * 1024 * 1024
MAX_ARCHIVE = 9 * 1024 * 1024
MAX_MANIFEST = 256 * 1024
MAX_HEADER = 8192
MAX_ENTRIES = 1024
MARKER = 'export-complete.json'
ERROR = 'recovery archive operation rejected'


class ArchiveError(ValueError):
    """Sanitized transport failure; never includes paths, keys or data."""


def _reject():
    raise ArchiveError(ERROR)


def _json(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'), ensure_ascii=True).encode('ascii')


def _load(data):
    def pairs(items):
        result = {}
        for key, value in items:
            if key in result:
                _reject()
            result[key] = value
        return result
    return json.loads(data, object_pairs_hook=pairs,
                      parse_constant=lambda _: _reject())


def _fields(value, names):
    if type(value) is not dict or set(value) != set(names.split()):
        _reject()


def _identity(revision, key_id):
    if not isinstance(revision, str) or not re.fullmatch('[0-9a-f]{40}', revision):
        _reject()
    if not isinstance(key_id, str) or not re.fullmatch('[A-Za-z0-9][A-Za-z0-9._-]{0,63}', key_id):
        _reject()


def _path(value):
    safe_path(value)
    if any(part.casefold() in {'export-in-progress.json', 'export-incomplete.json'}
           or part.casefold().endswith(('.partial', '.incomplete', '.tmp'))
           for part in value.split('/')):
        _reject()
    if len(value) > 240 or len(value.split('/')) > 16:
        _reject()
    for part in value.split('/'):
        if (not re.fullmatch('[A-Za-z0-9_.-]+', part) or part.endswith(('.', ' '))
                or part.split('.')[0].upper() in {'CON', 'PRN', 'AUX', 'NUL',
                    *(f'COM{i}' for i in range(1, 10)), *(f'LPT{i}' for i in range(1, 10))}
                or part.lower().startswith(('id_', 'credentials', 'secret', 'private'))):
            _reject()
    return value


def _regular(path, directory=False):
    info = path.lstat()
    if (stat.S_ISLNK(info.st_mode) or getattr(info, 'st_file_attributes', 0) & 0x400
            or not (stat.S_ISDIR(info.st_mode) if directory else stat.S_ISREG(info.st_mode))):
        _reject()
    return info


def _parents(path):
    for parent in reversed((path, *path.parents)):
        _regular(parent, directory=True)


def _read(path, limit):
    _parents(path.parent)
    before = _regular(path)
    if before.st_size > limit:
        _reject()
    fd = os.open(path, os.O_RDONLY | getattr(os, 'O_BINARY', 0) | getattr(os, 'O_NOFOLLOW', 0))
    with os.fdopen(fd, 'rb') as stream:
        opened = os.fstat(stream.fileno())
        if (opened.st_dev, opened.st_ino) != (before.st_dev, before.st_ino):
            _reject()
        data = stream.read(limit + 1)
        after = os.fstat(stream.fileno())
    if (len(data) > limit or len(data) != before.st_size
            or (after.st_size, after.st_mtime_ns) != (before.st_size, before.st_mtime_ns)):
        _reject()
    return data


def _key(path, private=False, password=None):
    data = _read(Path(path).absolute(), 16384)
    key = (serialization.load_pem_private_key(data, password=password) if private
           else serialization.load_pem_public_key(data))
    if not isinstance(key, rsa.RSAPrivateKey if private else rsa.RSAPublicKey):
        _reject()
    if key.key_size < 2048 or key.key_size > 8192:
        _reject()
    return key


def _fingerprint(key):
    if isinstance(key, rsa.RSAPrivateKey):
        key = key.public_key()
    return hashlib.sha256(key.public_bytes(serialization.Encoding.DER,
        serialization.PublicFormat.SubjectPublicKeyInfo)).hexdigest()


def _oaep():
    return padding.OAEP(mgf=padding.MGF1(hashes.SHA256()), algorithm=hashes.SHA256(), label=MAGIC)


def _scan(root):
    _parents(root)
    files, directories, seen = [], [], set()
    def walk(directory):
        for entry in sorted(directory.iterdir()):
            name = _path(entry.relative_to(root).as_posix())
            if name.casefold() in seen or len(seen) >= MAX_ENTRIES:
                _reject()
            seen.add(name.casefold())
            info = entry.lstat()
            if stat.S_ISDIR(info.st_mode):
                _regular(entry, directory=True)
                directories.append(name)
                walk(entry)
            else:
                _regular(entry)
                files.append(name)
    walk(root)
    return sorted(files), sorted(directories)


def _marker(data, revision):
    if len(data) > 4096:
        _reject()
    value = _load(data)
    _fields(value, 'schema state framework_revision')
    if type(value['schema']) is not int or value != {
            'schema': 1, 'state': 'complete', 'framework_revision': revision}:
        _reject()


def _new_target(value):
    path = Path(value).absolute()
    _parents(path.parent)
    if os.path.lexists(path):
        _reject()
    if os.name == 'nt' and sys.version_info < (3, 13):
        _reject()
    return path


def _rename_new(source, destination):
    # Unlike os.replace and POSIX os.rename, these never replace a racing target.
    if os.name == 'nt':
        for attempt in range(8):
            try:
                os.rename(source, destination)
                break
            except PermissionError as error:
                if (error.winerror not in (5, 32, 33) or attempt == 7
                        or os.path.lexists(destination)):
                    raise
                time.sleep(0.025 * (attempt + 1))
    elif sys.platform.startswith('linux'):
        libc = ctypes.CDLL(None, use_errno=True)
        fn = libc.renameat2
        fn.argtypes = [ctypes.c_int, ctypes.c_char_p, ctypes.c_int, ctypes.c_char_p, ctypes.c_uint]
        fn.restype = ctypes.c_int
        if fn(-100, os.fsencode(source), -100, os.fsencode(destination), 1):
            raise OSError(ctypes.get_errno(), 'publication rejected')
    elif sys.platform == 'darwin':
        libc = ctypes.CDLL(None, use_errno=True)
        fn = libc.renamex_np
        fn.argtypes = [ctypes.c_char_p, ctypes.c_char_p, ctypes.c_uint]
        fn.restype = ctypes.c_int
        if fn(os.fsencode(source), os.fsencode(destination), 4):
            raise OSError(ctypes.get_errno(), 'publication rejected')
    else:
        _reject()


def _publish(destination, writer, directory):
    stage = Path(tempfile.mkdtemp(prefix='.dg-recovery-', dir=destination.parent))
    try:
        payload = stage / 'payload'
        if directory:
            payload.mkdir(mode=0o700)
        writer(payload)
        _parents(destination.parent)
        _rename_new(payload, destination)
    finally:
        shutil.rmtree(stage)


def _write(path, data):
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | getattr(os, 'O_BINARY', 0), 0o600)
    with os.fdopen(fd, 'wb') as stream:
        stream.write(data)
        stream.flush()
        os.fsync(stream.fileno())


def seal(source, output, public_key, revision, key_id):
    """Seal declared-complete input. All failures expose only ArchiveError."""
    try:
        _identity(revision, key_id)
        source = Path(source).absolute()
        output = _new_target(output)
        if output.is_relative_to(source):
            _reject()
        key = _key(public_key)
        files, directories = _scan(source)
        if MARKER not in files:
            _reject()
        _marker(_read(source / MARKER, MAX_MANIFEST), revision)
        body = bytearray()
        entries = []
        for name in files:
            data = _read(source / name, MAX_PLAINTEXT - len(body))
            if name == MARKER:
                _marker(data, revision)
            entries.append({'path': name, 'size': len(data), 'sha256': hashlib.sha256(data).hexdigest()})
            body.extend(data)
        if (files, directories) != _scan(source):
            _reject()
        manifest = _json({'schema': 1, 'framework_revision': revision, 'key_id': key_id,
            'recipient_sha256': _fingerprint(key), 'files': entries, 'directories': directories})
        if len(manifest) > MAX_MANIFEST or 4 + len(manifest) + len(body) > MAX_PLAINTEXT:
            _reject()
        plain = struct.pack('>I', len(manifest)) + manifest + body
        del body, data
        secret = AESGCM.generate_key(bit_length=256)
        nonce = os.urandom(12)
        header = _json({'schema': 1, 'algorithm': 'RSA-OAEP-SHA256+AES-256-GCM',
            'framework_revision': revision, 'key_id': key_id, 'recipient_sha256': _fingerprint(key),
            'wrapped_key': key.encrypt(secret, _oaep()).hex(), 'nonce': nonce.hex()})
        prefix = MAGIC + struct.pack('>I', len(header)) + header
        cipher = AESGCM(secret).encrypt(nonce, plain, prefix)
        del plain, secret
        _publish(output, lambda path: _write(path, prefix + cipher), directory=False)
    except Exception:
        raise ArchiveError(ERROR) from None


def _validate_plain(plain, header, revision, key_id):
    if len(plain) < 4:
        _reject()
    length = struct.unpack('>I', plain[:4])[0]
    if length > MAX_MANIFEST or length > len(plain) - 4:
        _reject()
    manifest = _load(plain[4:4 + length])
    _fields(manifest, 'schema framework_revision key_id recipient_sha256 files directories')
    for field in ('schema', 'framework_revision', 'key_id', 'recipient_sha256'):
        if manifest[field] != header[field] or type(manifest[field]) is not type(header[field]):
            _reject()
    files, dirs = manifest['files'], manifest['directories']
    if type(files) is not list or type(dirs) is not list or len(files) + len(dirs) > MAX_ENTRIES:
        _reject()
    names, seen = [], set()
    for entry in files:
        _fields(entry, 'path size sha256')
        names.append(_path(entry['path']))
        if (type(entry['size']) is not int or entry['size'] < 0
                or not isinstance(entry['sha256'], str) or not re.fullmatch('[0-9a-f]{64}', entry['sha256'])):
            _reject()
    for name in dirs:
        _path(name)
    if names != sorted(names) or dirs != sorted(dirs):
        _reject()
    dirset = set(dirs)
    for name in names + dirs:
        if name.casefold() in seen:
            _reject()
        seen.add(name.casefold())
        parent = name.rpartition('/')[0]
        if parent and parent not in dirset:
            _reject()
    offset = 4 + length
    spans = []
    marker_found = False
    for entry in files:
        end = offset + entry['size']
        data = memoryview(plain)[offset:end]
        if end > len(plain) or hashlib.sha256(data).hexdigest() != entry['sha256']:
            _reject()
        if entry['path'] == MARKER:
            _marker(bytes(data), revision)
            marker_found = True
        spans.append((entry['path'], offset, end))
        offset = end
    if offset != len(plain) or not marker_found:
        _reject()
    return dirs, spans


def open_archive(archive, destination, private_key, revision, key_id, *, password=None):
    """Authenticate and validate ALL bytes before even creating restore staging."""
    try:
        _identity(revision, key_id)
        destination = _new_target(destination)
        key = _key(private_key, private=True, password=password)
        envelope = _read(Path(archive).absolute(), MAX_ARCHIVE)
        if not envelope.startswith(MAGIC) or len(envelope) < len(MAGIC) + 4:
            _reject()
        length = struct.unpack('>I', envelope[len(MAGIC):len(MAGIC) + 4])[0]
        start = len(MAGIC) + 4
        end = start + length
        if length > MAX_HEADER or end + 16 > len(envelope):
            _reject()
        header = _load(envelope[start:end])
        _fields(header, 'schema algorithm framework_revision key_id recipient_sha256 wrapped_key nonce')
        if (type(header['schema']) is not int or header['schema'] != 1
                or header['algorithm'] != 'RSA-OAEP-SHA256+AES-256-GCM'
                or header['framework_revision'] != revision or header['key_id'] != key_id
                or header['recipient_sha256'] != _fingerprint(key)
                or envelope[start:end] != _json(header)):
            _reject()
        wrapped, nonce = bytes.fromhex(header['wrapped_key']), bytes.fromhex(header['nonce'])
        if len(wrapped) != key.key_size // 8 or len(nonce) != 12 or len(envelope) - end > MAX_PLAINTEXT + 16:
            _reject()
        secret = key.decrypt(wrapped, _oaep())
        if len(secret) != 32:
            _reject()
        plain = AESGCM(secret).decrypt(nonce, envelope[end:], envelope[:end])
        del envelope, secret
        dirs, spans = _validate_plain(plain, header, revision, key_id)
        def restore(root):
            for name in sorted(dirs, key=lambda item: (item.count('/'), item)):
                (root / name).mkdir(mode=0o700)
            for name, begin, finish in spans:
                _write(root / name, memoryview(plain)[begin:finish])
        _publish(destination, restore, directory=True)
    except Exception:
        raise ArchiveError(ERROR) from None


class _Parser(argparse.ArgumentParser):
    def error(self, message):
        self.exit(2, ERROR + '\n')


def main(argv=None):
    parser = _Parser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = parser.add_subparsers(dest='command', required=True)
    seal_parser = sub.add_parser('seal')
    seal_parser.add_argument('--source', required=True)
    seal_parser.add_argument('--output', required=True)
    seal_parser.add_argument('--public-key', required=True)
    open_parser = sub.add_parser('open')
    open_parser.add_argument('--archive', required=True)
    open_parser.add_argument('--destination', required=True)
    open_parser.add_argument('--private-key', required=True)
    for child in (seal_parser, open_parser):
        child.add_argument('--revision', required=True)
        child.add_argument('--key-id', required=True)
    args = parser.parse_args(argv)
    try:
        if args.command == 'seal':
            seal(args.source, args.output, args.public_key, args.revision, args.key_id)
        else:
            # Prompt only for explicitly encrypted PEM, never echo password.
            encrypted = b'ENCRYPTED' in _read(Path(args.private_key).absolute(), 16384)
            if encrypted and not sys.stdin.isatty():
                _reject()
            password = getpass.getpass('Private key passphrase: ').encode() if encrypted else None
            open_archive(args.archive, args.destination, args.private_key,
                         args.revision, args.key_id, password=password)
    except (Exception, KeyboardInterrupt):
        print(ERROR, file=sys.stderr)
        return 1
    print('archive sealed' if args.command == 'seal' else 'archive opened')
    return 0


if __name__ == '__main__':
    sys.exit(main())
