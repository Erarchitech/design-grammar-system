"""Full-export authenticated age1.2.1 transport (Python stdlib, age external).

Framing: MAGIC, unsigned big-endian 8-byte manifest length, UTF-8 JSON, file
bytes concatenated in manifest order; no compression or archive extraction API.
Source has EXACTLY six nonempty component trees: api, key-references, minio,
n8n, neo4j, postgres. Keep native dumps/.n8n tar/MinIO export opaque here;
this helper neither exports nor restores services. Empty subdirectories survive.

Limits: 64 GiB content, 100000 files + 100000 directories, 8 MiB manifest,
512 UTF-8 bytes/path, depth32, 64 KiB reads, timeout per age subprocess <=3600s.
Fail closed for links/reparse points, duplicate/case aliases, unsafe portable
paths, malformed metadata, changed inputs, trailing bytes, and existing targets.

Trust prerequisites: stopped/quiescent complete exports; private non-adversarial
read-only source/tool/key mounts; quota-protected work/exchange; validated tool
provenance and independent expected ciphertext hash; retained X25519 identity
custody separately. Hash pins alone are not distribution authentication.
Only owned staging/output directories are removed. Unlink is NOT secure erase.
Mode0600/0700 is not a Windows ACL. Process size polling is not a disk quota.
No native destination write occurs until complete age exit0 + all file hashes.
An output tree is admissible ONLY after atomic COMPLETE.json publication and
successful caller exit0. No fsync crash-durability/transfer/native acceptance or
exporter identity authentication is claimed. Do not ingest private encryption
identities as exports; key-references are custody references, not identity keys.
"""
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import stat
import struct
import math
import subprocess
import time
import uuid

MAGIC = b'DG-MULTISTORE-1\x00'
SCHEMA = 'dg-multistore-frame-v1'
COMPONENTS = ('api', 'key-references', 'minio', 'n8n', 'neo4j', 'postgres')
MAX_MANIFEST = 8 * 1024 * 1024
MAX_FILES = 100000
MAX_DIRS = 100000
MAX_TOTAL = 64 * 1024 ** 3
CHUNK = 65536
# Single X25519 recipient header + payload nonce, conservatively bounded.
AGE_HEADER_BOUND = 65536


def _ciphertext_bound(frame_bytes):
    return frame_bytes + max(1, (frame_bytes + CHUNK - 1) // CHUNK) * 16 + AGE_HEADER_BOUND


MAX_CIPHERTEXT = _ciphertext_bound(MAX_TOTAL + MAX_MANIFEST + len(MAGIC) + 8)


class ArchiveError(ValueError):
    pass


class DecryptionRejected(ArchiveError):
    """Only fixed age1.2.1 authentication diagnostics, never raw stderr."""
    def __init__(self, reason):
        self.reason = reason
        super().__init__('multi-store decryption rejected')


def _identities(path):
    path = Path(path).absolute()
    _ancestors(path.parent)
    if _node(path).st_size > 8192:
        _reject()
    keys = [line.strip() for line in path.read_text(encoding='ascii').splitlines()
            if line.strip() and not line.lstrip().startswith('#')]
    if not 0 < len(keys) <= 8:
        _reject()
    alphabet = 'QPZRY9X8GF2TVDW0S3JN54KHCE6MUA7L'
    hrp = 'age-secret-key-'
    for key in keys:
        if not re.fullmatch('AGE-SECRET-KEY-1[023456789ACDEFGHJKLMNPQRSTUVWXYZ]{58}', key):
            _reject()
        values = [alphabet.index(c) for c in key[16:]]
        # 256-bit X25519 secret: 52 data symbols, with four zero padding bits.
        if values[51] & 15:
            _reject()
        chk = 1
        for v in ([ord(c) >> 5 for c in hrp] + [0] +
                  [ord(c) & 31 for c in hrp] + values):
            top = chk >> 25
            chk = ((chk & 0x1ffffff) << 5) ^ v
            for i, g in enumerate((0x3b6a57b2, 0x26508e6d, 0x1ea119fa, 0x3d4233dd, 0x2a1462b3)):
                if (top >> i) & 1:
                    chk ^= g
        if chk != 1:
            _reject()
    return frozenset(keys)


def _reject():
    raise ArchiveError('multi-store archive rejected')


def _stable(s):
    # Windows fstat omits executable mode bits, unlike path lstat.
    return (s.st_dev, s.st_ino, stat.S_IFMT(s.st_mode), s.st_nlink, s.st_size, s.st_mtime_ns)


def _node(path, directory=False):
    s = path.lstat()
    if (stat.S_ISLNK(s.st_mode) or getattr(s, 'st_file_attributes', 0) & 0x400
            or (not stat.S_ISDIR(s.st_mode) if directory else not stat.S_ISREG(s.st_mode))
            or (not directory and s.st_nlink != 1)):
        _reject()
    return s


def _ancestors(path):
    for p in (path, *path.parents):
        _node(p, directory=True)


def _name(name):
    if (type(name) is not str or not 0 < len(name.encode('utf-8')) <= 512
            or '\\' in name or ':' in name or name.startswith('/')
            or len(name.split('/')) > 32):
        _reject()
    for part in name.split('/'):
        if (part in ('', '.', '..') or part[-1:] in (' ', '.')
                or any(ord(c) < 32 or c in '<>"|?*' or ord(c) == 127 for c in part)
                or part.split('.')[0].upper() in {'CON', 'PRN', 'AUX', 'NUL',
                    *('COM' + str(i) for i in range(1, 10)),
                    *('LPT' + str(i) for i in range(1, 10))}):
            _reject()
    return name


def _hash(stream, size, output=None):
    h = hashlib.sha256()
    remaining = size
    while remaining:
        chunk = stream.read(min(CHUNK, remaining))
        if not chunk:
            _reject()
        remaining -= len(chunk)
        h.update(chunk)
        if output is not None:
            output.write(chunk)
    return h.hexdigest()


def _manifest(value):
    if (type(value) is not dict or set(value) != {'schema', 'directories', 'files'}
            or value['schema'] != SCHEMA or type(value['directories']) is not list
            or type(value['files']) is not list or not 0 < len(value['files']) <= MAX_FILES
            or not 0 < len(value['directories']) <= MAX_DIRS):
        _reject()
    dirs = value['directories']
    files = value['files']
    names = set()
    folded = set()
    def add(name):
        _name(name)
        if name.casefold() in folded:
            _reject()
        folded.add(name.casefold())
        names.add(name)
    for name in dirs:
        add(name)
    total = 0
    paths = []
    for f in files:
        if (type(f) is not dict or set(f) != {'path', 'bytes', 'sha256'}
                or type(f['bytes']) is not int or not 0 <= f['bytes'] <= MAX_TOTAL
                or type(f['sha256']) is not str or not re.fullmatch('[0-9a-f]{64}', f['sha256'])):
            _reject()
        add(f['path'])
        paths.append(f['path'])
        total += f['bytes']
        if total > MAX_TOTAL:
            _reject()
    if dirs != sorted(dirs) or paths != sorted(paths):
        _reject()
    dirset = set(dirs)
    if {p.split('/')[0] for p in names} != set(COMPONENTS):
        _reject()
    if any(not any(p.startswith(c + '/') for p in paths) for c in COMPONENTS):
        _reject()
    for name in names:
        parent = name.rpartition('/')[0]
        if parent and parent not in dirset:
            _reject()
    return total


def _inventory(source):
    _ancestors(source)
    directories, files, count, total = [], [], 0, 0
    def walk(path):
        nonlocal count, total
        # Bound actual OS enumeration BEFORE sorting/materializing paths.
        with os.scandir(path) as iterator:
            entries = []
            for entry in iterator:
                count += 1
                if count > MAX_FILES + MAX_DIRS:
                    _reject()
                entries.append(entry)
        for entry in sorted(entries, key=lambda e: e.name):
            p = Path(entry.path)
            name = _name(p.relative_to(source).as_posix())
            s = p.lstat()
            if stat.S_ISDIR(s.st_mode):
                _node(p, True)
                directories.append(name)
                if len(directories) > MAX_DIRS:
                    _reject()
                walk(p)
            else:
                before = _node(p)
                if len(files) >= MAX_FILES or before.st_size > MAX_TOTAL - total:
                    _reject()
                total += before.st_size
                with p.open('rb') as stream:
                    if _stable(os.fstat(stream.fileno())) != _stable(before):
                        _reject()
                    digest = _hash(stream, before.st_size)
                    if stream.read(1):
                        _reject()
                if _stable(_node(p)) != _stable(before):
                    _reject()
                files.append({'path': name, 'bytes': before.st_size, 'sha256': digest})
    walk(source)
    manifest = {'schema': SCHEMA, 'directories': sorted(directories),
                'files': sorted(files, key=lambda f: f['path'])}
    _manifest(manifest)
    return manifest


def build_frame(source, destination):
    source, destination = Path(source).absolute(), Path(destination).absolute()
    if destination.is_relative_to(source):
        _reject()
    manifest = _inventory(source)
    encoded = json.dumps(manifest, sort_keys=True, separators=(',', ':'), ensure_ascii=False).encode('utf-8')
    if len(encoded) > MAX_MANIFEST:
        _reject()
    owned = False
    try:
        _ancestors(destination.parent)
        with destination.open('xb') as out:
            owned = True
            os.chmod(destination, 0o600)
            out.write(MAGIC + struct.pack('>Q', len(encoded)) + encoded)
            for item in manifest['files']:
                path = source / item['path']
                before = _node(path)
                with path.open('rb') as stream:
                    if _stable(os.fstat(stream.fileno())) != _stable(before):
                        _reject()
                    if _hash(stream, item['bytes'], out) != item['sha256'] or stream.read(1):
                        _reject()
                if _stable(_node(path)) != _stable(before):
                    _reject()
            out.flush()
            os.fsync(out.fileno())
        # Re-inventory detects added/removed/changed files before acceptance.
        if _inventory(source) != manifest:
            _reject()
        return manifest
    except BaseException:
        if owned:
            destination.unlink()
        raise ArchiveError('multi-store archive rejected') from None


def _pairs(pairs):
    result = {}
    for k, v in pairs:
        if k in result:
            _reject()
        result[k] = v
    return result


def validate_frame(frame):
    try:
        return _validate_frame(frame)
    except Exception:
        raise ArchiveError('multi-store archive rejected') from None


def _validate_frame(frame):
    frame = Path(frame)
    before = _node(frame)
    if before.st_size > MAX_TOTAL + MAX_MANIFEST + len(MAGIC) + 8:
        _reject()
    with frame.open('rb') as stream:
        if stream.read(len(MAGIC)) != MAGIC:
            _reject()
        length = stream.read(8)
        if len(length) != 8:
            _reject()
        length = struct.unpack('>Q', length)[0]
        if not 0 < length <= MAX_MANIFEST:
            _reject()
        encoded = stream.read(length)
        if len(encoded) != length:
            _reject()
        value = json.loads(encoded, object_pairs_hook=_pairs)
        total = _manifest(value)
        if before.st_size != len(MAGIC) + 8 + length + total:
            _reject()
        for item in value['files']:
            if _hash(stream, item['bytes']) != item['sha256']:
                _reject()
        if stream.read(1):
            _reject()
    if _stable(_node(frame)) != _stable(before):
        _reject()
    return value


def extract_frame(frame, destination):
    """Validate the WHOLE frame before exclusive destination creation.

    Only call on private authenticated plaintext. This function is not decrypt.
    A missing COMPLETE.json means the tree is incomplete and MUST NOT restore.
    """
    frame, destination = Path(frame).absolute(), Path(destination).absolute()
    owned = False
    try:
        manifest = validate_frame(frame)
        _ancestors(destination.parent)
        destination.mkdir(mode=0o700)
        owned = True
        for name in manifest['directories']:
            (destination / name).mkdir(mode=0o700)
        with frame.open('rb') as stream:
            stream.seek(len(MAGIC))
            length = struct.unpack('>Q', stream.read(8))[0]
            stream.seek(length, 1)
            for item in manifest['files']:
                with (destination / item['path']).open('xb') as out:
                    os.chmod(destination / item['path'], 0o600)
                    if _hash(stream, item['bytes'], out) != item['sha256']:
                        _reject()
                    out.flush()
                    os.fsync(out.fileno())
        return manifest
    except BaseException:
        if owned:
            shutil.rmtree(destination)
        raise ArchiveError('multi-store archive rejected') from None


def _file_digest(path):
    before = _node(path)
    with path.open('rb') as stream:
        if _stable(os.fstat(stream.fileno())) != _stable(before):
            _reject()
        digest = _hash(stream, before.st_size)
        if stream.read(1):
            _reject()
    if _stable(_node(path)) != _stable(before):
        _reject()
    return digest


def _run(argv, source, output, *, cwd, timeout, max_output, popen=None, decrypt=False):
    """Direct-child streaming; bounded fixed diagnostics, never returned verbatim.

    Size polling is NOT an OS disk quota. Diagnostics live only in owned stage.
    """
    child = None
    diagnostic = output.with_name(output.name + '.diagnostic')
    try:
        with output.open('xb') as out, diagnostic.open('xb') as err:
            os.chmod(output, 0o600)
            os.chmod(diagnostic, 0o600)
            with source.open('rb') as inp:
                child = (popen or subprocess.Popen)(argv, stdin=inp, stdout=out,
                    stderr=err, shell=False, env={},
                    cwd=str(cwd), close_fds=True)
                deadline = time.monotonic() + timeout
                while True:
                    if (time.monotonic() >= deadline or output.stat().st_size > max_output
                            or diagnostic.stat().st_size > 1024):
                        _reject()
                    try:
                        code = child.wait(timeout=min(0.05, max(0.001, deadline-time.monotonic())))
                        break
                    except subprocess.TimeoutExpired:
                        pass
                out.flush()
                os.fsync(out.fileno())
                err.flush()
                if (time.monotonic() >= deadline or output.stat().st_size > max_output
                        or diagnostic.stat().st_size > 1024):
                    _reject()
                if decrypt and code == 1:
                    message = diagnostic.read_bytes().replace(b'\r\n', b'\n')
                    trailer = b'\nage: report unexpected or unhelpful errors at https://filippo.io/age/report\n'
                    for reason, text in (
                        ('NO_MATCHING_IDENTITY', b'no identity matched any of the recipients'),
                        ('PAYLOAD_AUTHENTICATION_FAILED', b'failed to decrypt and authenticate payload chunk'),
                    ):
                        if message == b'age: error: ' + text + trailer:
                            raise DecryptionRejected(reason)
                if code != 0 or not 0 < output.stat().st_size <= max_output:
                    _reject()
    finally:
        if child is not None and child.poll() is None:
            child.kill()
            child.wait(timeout=5)


def _admit(executable, tool_sha256, work, timeout, popen):
    tool, work = Path(executable), Path(work).absolute()
    if (not tool.is_absolute() or type(tool_sha256) is not str
            or not re.fullmatch('[0-9a-f]{64}', tool_sha256)
            or type(timeout) not in (int, float) or not math.isfinite(timeout)
            or not 0 < timeout <= 3600):
        _reject()
    _ancestors(tool.parent)
    if _file_digest(tool) != tool_sha256:
        _reject()
    _ancestors(work)
    return tool, work


def _version(tool, stage, timeout, popen):
    source, result = stage / 'empty', stage / 'version'
    source.write_bytes(b'')
    _run([str(tool), '--version'], source, result, cwd=stage,
         timeout=timeout, max_output=32, popen=popen)
    if result.read_bytes().strip() not in (b'1.2.1', b'v1.2.1'):
        _reject()
    source.unlink()
    result.unlink()


def _complete(destination, result):
    # Atomic, exclusive completion publication; unsupported filesystems fail closed.
    candidate = destination / ('.complete-' + uuid.uuid4().hex)
    owned = False
    try:
        with candidate.open('xb') as out:
            owned = True
            os.chmod(candidate, 0o600)
            out.write(json.dumps(result, sort_keys=True, separators=(',', ':')).encode())
            out.flush()
            os.fsync(out.fileno())
        os.link(candidate, destination / 'COMPLETE.json')
    finally:
        if owned:
            candidate.unlink()


def _target(destination):
    destination = Path(destination).absolute()
    _ancestors(destination.parent)
    if os.path.lexists(destination):
        _reject()
    return destination


def seal(source, destination, *, recipient_file, executable, tool_sha256,
         work, timeout=300, popen=None):
    """Seal exports to NEW directory/archive.age + COMPLETE.json, written last."""
    stage = None
    owned = False
    try:
        tool, work = _admit(executable, tool_sha256, work, timeout, popen)
        source, destination = Path(source).absolute(), _target(destination)
        recipient_file = Path(recipient_file).absolute()
        _ancestors(recipient_file.parent)
        _node(recipient_file)
        if recipient_file.stat().st_size > 1024:
            _reject()
        recipient = recipient_file.read_text(encoding='ascii').strip()
        if not re.fullmatch('age1[023456789acdefghjklmnpqrstuvwxyz]{58}', recipient):
            _reject()
        if work.is_relative_to(source) or destination.is_relative_to(source):
            _reject()
        candidate = work / ('.multistore-' + uuid.uuid4().hex)
        candidate.mkdir(mode=0o700)
        stage = candidate
        _version(tool, stage, timeout, popen)
        manifest = build_frame(source, stage / 'plaintext.frame')
        if _file_digest(tool) != tool_sha256:
            _reject()
        _run([str(tool), '--encrypt', '--recipient', recipient],
             stage / 'plaintext.frame', stage / 'ciphertext.age', cwd=stage,
             timeout=timeout, max_output=MAX_CIPHERTEXT, popen=popen)
        ciphertext = stage / 'ciphertext.age'
        result = {'schema': 'dg-multistore-sealed-v1', 'sha256': _file_digest(ciphertext),
                  'bytes': ciphertext.stat().st_size, 'files': len(manifest['files']),
                  'toolSha256': tool_sha256, 'ageVersion': '1.2.1',
                  'exporterAuthenticated': False, 'nativeRecoveryProven': False}
        destination.mkdir(mode=0o700)
        owned = True
        # Work and exchange may be separate mounts, so copy, never replace/link.
        with ciphertext.open('rb') as inp, (destination / 'archive.age').open('xb') as out:
            os.chmod(destination / 'archive.age', 0o600)
            if _hash(inp, result['bytes'], out) != result['sha256']:
                _reject()
            out.flush()
            os.fsync(out.fileno())
        _complete(destination, result)
        return result
    except BaseException:
        if owned:
            shutil.rmtree(destination)
        raise ArchiveError('multi-store archive rejected') from None
    finally:
        if stage is not None:
            shutil.rmtree(stage)


def open_archive(archive, destination, *, identity_file, archive_sha256,
                 executable, tool_sha256, work, timeout=300, popen=None):
    """Entire age exit0 and full frame validation precede destination writes.

    Only X25519 age identities; plugins/passphrases rejected. No key copying.
    Expected ciphertext SHA must arrive from an independently trusted channel.
    """
    stage = None
    owned = False
    try:
        tool, work = _admit(executable, tool_sha256, work, timeout, popen)
        archive, destination = Path(archive).absolute(), _target(destination)
        identity_file = Path(identity_file).absolute()
        _identities(identity_file)
        if (type(archive_sha256) is not str or not re.fullmatch('[0-9a-f]{64}', archive_sha256)
                or _node(archive).st_size > MAX_CIPHERTEXT
                or _file_digest(archive) != archive_sha256):
            _reject()
        before = _node(archive)
        candidate = work / ('.multistore-' + uuid.uuid4().hex)
        candidate.mkdir(mode=0o700)
        stage = candidate
        _version(tool, stage, timeout, popen)
        if _file_digest(tool) != tool_sha256:
            _reject()
        _run([str(tool), '--decrypt', '--identity', str(identity_file)], archive,
             stage / 'plaintext.frame', cwd=stage, timeout=timeout,
             max_output=MAX_TOTAL + MAX_MANIFEST + len(MAGIC) + 8, popen=popen, decrypt=True)
        if _stable(_node(archive)) != _stable(before) or _file_digest(archive) != archive_sha256:
            _reject()
        manifest = extract_frame(stage / 'plaintext.frame', destination)
        owned = True
        result = {'schema': 'dg-multistore-opened-v1', 'sha256': archive_sha256,
                  'files': len(manifest['files']), 'authenticatedBeforeDestinationCreation': True,
                  'exporterAuthenticated': False, 'nativeRecoveryProven': False}
        _complete(destination, result)
        return result
    except DecryptionRejected:
        # Only _run's fixed decrypt diagnostic can reach this classification.
        if owned:
            shutil.rmtree(destination)
        raise
    except BaseException:
        if owned:
            shutil.rmtree(destination)
        raise ArchiveError('multi-store archive rejected') from None
    finally:
        if stage is not None:
            shutil.rmtree(stage)


def negative(archive, destination, *, identity_file, wrong_identity_file,
             archive_sha256, executable, tool_sha256, work, timeout=300, popen=None):
    """Positive control + wrong key + final byte corruption, without publication."""
    stage = None
    try:
        tool, work = _admit(executable, tool_sha256, work, timeout, popen)
        destination = _target(destination)
        if _identities(identity_file) & _identities(wrong_identity_file):
            _reject()
        candidate = work / ('.multistore-negative-' + uuid.uuid4().hex)
        candidate.mkdir(mode=0o700)
        stage = candidate
        options = dict(executable=str(tool), tool_sha256=tool_sha256, work=work,
                       timeout=timeout, popen=popen)
        archive = Path(archive).absolute()
        before = _file_digest(archive)
        if before != archive_sha256:
            _reject()
        # Rejecting everything is NOT a successful negative experiment.
        open_archive(archive, stage / 'control', identity_file=identity_file,
                     archive_sha256=archive_sha256, **options)
        shutil.rmtree(stage / 'control')
        target = stage / 'negative-output'
        try:
            open_archive(archive, target, identity_file=wrong_identity_file,
                         archive_sha256=archive_sha256, **options)
        except DecryptionRejected as error:
            if error.reason != 'NO_MATCHING_IDENTITY' or os.path.lexists(target):
                _reject()
        else:
            _reject()
        corrupt = stage / 'corrupt.age'
        with archive.open('rb') as inp, corrupt.open('xb') as out:
            os.chmod(corrupt, 0o600)
            shutil.copyfileobj(inp, out, CHUNK)
        with corrupt.open('r+b') as stream:
            stream.seek(-1, 2)
            byte = stream.read(1)
            stream.seek(-1, 2)
            stream.write(bytes([byte[0] ^ 1]))
        try:
            # Recompute expected hash: exercise age auth, not hash admission.
            open_archive(corrupt, target, identity_file=identity_file,
                         archive_sha256=_file_digest(corrupt), **options)
        except DecryptionRejected as error:
            if error.reason != 'PAYLOAD_AUTHENTICATION_FAILED' or os.path.lexists(target):
                _reject()
        else:
            _reject()
        if _file_digest(archive) != before or os.path.lexists(destination):
            _reject()
        return {'schema': 'dg-multistore-negative-v1', 'positiveControl': True,
                'badKeyRejectedBeforeDestination': True,
                'corruptCiphertextRejectedBeforeDestination': True,
                'sourceCiphertextUnchanged': True, 'nativeRecoveryProven': False}
    except BaseException:
        raise ArchiveError('multi-store negative experiment rejected') from None
    finally:
        if stage is not None:
            shutil.rmtree(stage)


def main(argv=None):
    import argparse
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest='mode', required=True)
    for mode in ('seal', 'open', 'negative'):
        p = sub.add_parser(mode)
        p.add_argument('--age', required=True, help='absolute pinned executable path')
        p.add_argument('--age-sha256', required=True)
        p.add_argument('--work', required=True, help='existing private quota-protected scratch root')
        p.add_argument('--destination', required=True, help='NEW output directory; negative: absent sentinel')
        p.add_argument('--timeout', type=float, default=300)
        if mode == 'seal':
            p.add_argument('--source', required=True)
            p.add_argument('--recipient-file', required=True)
        else:
            p.add_argument('--archive', required=True)
            p.add_argument('--archive-sha256', required=True)
            p.add_argument('--identity-file', required=True)
            if mode == 'negative':
                p.add_argument('--wrong-identity-file', required=True)
    args = parser.parse_args(argv)
    options = dict(executable=args.age, tool_sha256=args.age_sha256,
                   work=args.work, timeout=args.timeout)
    try:
        if args.mode == 'seal':
            result = seal(args.source, args.destination, recipient_file=args.recipient_file, **options)
        elif args.mode == 'open':
            result = open_archive(args.archive, args.destination, identity_file=args.identity_file,
                                  archive_sha256=args.archive_sha256, **options)
        else:
            result = negative(args.archive, args.destination, identity_file=args.identity_file,
                wrong_identity_file=args.wrong_identity_file, archive_sha256=args.archive_sha256, **options)
        print(json.dumps(result, sort_keys=True))
        return 0
    except Exception:
        print('{"error":"MULTISTORE_ARCHIVE_REJECTED"}')
        return 1


if __name__ == '__main__':
    raise SystemExit(main())
