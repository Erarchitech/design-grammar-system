"""Bounded adapter for a FUTURE isolated, digest-pinned PostgreSQL 16 container.

Runtime native validation is BLOCKED; offline tests use disposable Python children.
No Docker, shell, SQL, service lifecycle, arbitrary flags or connection URLs.
Fixed official-Alpine install-prefix paths must be validated against the later pinned image.

Module API (mutating; no standalone mutation CLI):
    export_dump(new_path, source_project=..., owner_scope=..., env=..., attest=...)
    restore_dump(path, expected_sha256=..., source_project=...,
                 destination_project=..., owner_scope=..., env=..., attest=...)
The env dictionary must contain ONLY PGHOST, PGPORT, PGDATABASE, PGUSER, PGPASSWORD.
An authorized outer runner supplies those values privately, never via CLI arguments.
The injectable popen seam is for trusted code/offline tests, not user configuration.

TRUST BOUNDARY: attest(request) must be a trusted outer-runner callback returning
literal True after independently verifying current owner authorization, expiry,
pinned image/client/server identity, synthetic source and connection mapping,
writer quiescence/queue drain, protected private directory/ACL, and resource limits.
For restore it MUST ALSO prove the named destination's actual database identity,
empty disposable state, ownership, isolation from source, role/extension readiness,
and approved archive provenance/content. Names, hashes, scope labels and callbacks
alone prove NONE of those facts. This helper does not query or establish ownership,
empty target, native dump validity, or consistency. An untrusted archive can execute
SQL via pg_restore; hashing is not authentication. Never manufacture an attestation.
No outer runner is included; absent/refused attestation prevents mutation.

Trusted local filesystem with no hostile concurrent same-user changes is required.
Link/reparse/hardlink checks and held input descriptor reduce accidents, not hostile
TOCTOU attacks. POSIX output is exclusive 0600 in an owned private parent; Windows
ACL privacy remains an outer-runner obligation (chmod does not prove NTFS privacy).
Export limits: <=64 GiB, <=3600s, 64 KiB chunks and two queued chunks. Child output
is never reported; failure terminates/reaps the direct native client (which must not
spawn children) and attempts to remove only the file identity created here. Cleanup
failure is not proof of deletion; outer runner must check retained plaintext. Restore
failure never removes input; transaction rollback/connection death require later
native validation. Single transaction is not a multi-store transaction or acceptance.

Read-only CLI:
    python3 -B recovery_postgres.py --archive FILE --expected-sha256 HEX
It checks file integrity only and deliberately offers no fake approval/restore flag.
All reports retain nativeRecoveryProven=False; no completion marker is written.
"""
import argparse

try:
    from .recovery_filesystem import reject_named_streams
except ImportError:
    from recovery_filesystem import reject_named_streams
import hashlib
import json
import math
import os
from pathlib import Path
import re
import stat
import queue
import subprocess
import threading
import time

PG_DUMP = '/usr/local/bin/pg_dump'
PG_RESTORE = '/usr/local/bin/pg_restore'
MAX_BYTES = 64 * 1024 ** 3
CHUNK = 64 * 1024
ERROR = 'PostgreSQL operation rejected'


class PostgresError(ValueError):
    """Sanitized error; never expose child output or connection details."""


def _require(condition):
    if not condition:
        raise PostgresError(ERROR)


def _match(pattern, value):
    return type(value) is str and re.fullmatch(pattern, value) is not None


def _preflight(source_project, owner_scope, env, attest, timeout, max_bytes):
    _require(_match(r'dg-recovery-[0-9a-f]{32}', source_project))
    _require(_match(r'owner-scope:[A-Za-z0-9_-]{1,80}', owner_scope))
    _require(callable(attest))
    _require(type(timeout) in (int, float) and math.isfinite(timeout) and 0 < timeout <= 3600)
    _require(type(max_bytes) is int and 0 < max_bytes <= MAX_BYTES)
    required = {'PGHOST', 'PGPORT', 'PGDATABASE', 'PGUSER', 'PGPASSWORD'}
    _require(type(env) is dict and set(env) == required)
    _require(all(type(v) is str and 0 < len(v) <= 4096 and '\x00' not in v for v in env.values()))
    _require(_match(r'[A-Za-z0-9][A-Za-z0-9_.-]{0,252}', env['PGHOST']))
    _require(_match(r'[0-9]{1,5}', env['PGPORT']) and 0 < int(env['PGPORT']) <= 65535)
    for name in ('PGDATABASE', 'PGUSER'):
        _require(_match(r'[A-Za-z_][A-Za-z0-9_]{0,62}', env[name]))
    # Do not inherit libpq service files/options, loader variables, HOME or PATH.
    return {**env, 'PGCONNECT_TIMEOUT': str(max(1, min(30, math.ceil(timeout)))), 'LC_ALL': 'C'}


def _parent(path):
    path = Path(os.path.abspath(path))
    _require(os.name != 'nt' or all(':' not in part for part in path.parts[1:]))
    for directory in path.parents:
        reject_named_streams(directory)
        info = directory.lstat()
        _require(stat.S_ISDIR(info.st_mode) and not stat.S_ISLNK(info.st_mode)
                 and not getattr(info, 'st_file_attributes', 0) & 0x400)
    if os.name != 'nt':
        info = path.parent.stat()
        _require(info.st_uid == os.geteuid() and info.st_mode & 0o077 == 0)
    # NTFS ACL privacy is an outer-runner obligation, not established by chmod.
    return path


def _export_process(output, env, timeout, max_bytes, popen):
    # Allocate setup resources before spawn; everything after spawn is protected.
    chunks = queue.Queue(maxsize=2)
    stop = threading.Event()
    reader = None
    started = False
    process = popen([PG_DUMP, '--format=custom', '--no-password'],
                    stdin=subprocess.DEVNULL, stdout=subprocess.PIPE,
                    stderr=subprocess.DEVNULL, shell=False, env=env)
    try:
        def read():
            try:
                while not stop.is_set():
                    chunk = process.stdout.read(CHUNK)
                    while not stop.is_set():
                        try:
                            chunks.put(chunk, timeout=0.05)
                            break
                        except queue.Full:
                            continue
                    if not chunk:
                        break
            except OSError:
                stop.set()
        reader = threading.Thread(target=read, daemon=True)
        reader.start()
        started = True
        deadline = time.monotonic() + timeout
        digest = hashlib.sha256()
        count = 0
        while True:
            remaining = deadline - time.monotonic()
            _require(remaining > 0)
            chunk = chunks.get(timeout=remaining)
            if not chunk:
                break
            count += len(chunk)
            _require(count <= max_bytes)
            output.write(chunk)
            digest.update(chunk)
        _require(process.wait(timeout=max(0.001, deadline - time.monotonic())) == 0)
        _require(count > 0)
        return count, digest.hexdigest()
    finally:
        stop.set()
        try:
            if process.poll() is None:
                process.kill()
        finally:
            try:
                process.wait(timeout=5)
            finally:
                try:
                    if started:
                        reader.join(timeout=5)
                finally:
                    process.stdout.close()


def export_dump(path, *, source_project, owner_scope, env, attest,
                timeout=300, max_bytes=MAX_BYTES, popen=subprocess.Popen):
    own = None
    try:
        env = _preflight(source_project, owner_scope, env, attest, timeout, max_bytes)
        path = _parent(path)
        request = dict(operation='export', sourceProject=source_project, ownerScope=owner_scope,
                       connection={k: env[k] for k in ('PGHOST', 'PGPORT', 'PGDATABASE', 'PGUSER')},
                       protectedDirectory=str(path.parent))
        _require(attest(request) is True)
        descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | getattr(os, 'O_BINARY', 0), 0o600)
        own = os.fstat(descriptor)
        with os.fdopen(descriptor, 'wb') as output:
            count, digest = _export_process(output, env, timeout, max_bytes, popen)
            output.flush()
            os.fsync(output.fileno())
        return dict(status='POSTGRES_EXPORT_CREATED_NOT_RECOVERY', method='pg-dump-custom',
                    bytes=count, sha256=digest, nativeRecoveryProven=False)
    except BaseException as error:
        if own is not None:
            try:
                now = path.lstat()
                if (now.st_dev, now.st_ino) == (own.st_dev, own.st_ino):
                    path.unlink()
            except OSError:
                pass
        if not isinstance(error, Exception):
            raise
        raise PostgresError(ERROR) from None


def _regular(info, max_bytes):
    _require(stat.S_ISREG(info.st_mode) and not stat.S_ISLNK(info.st_mode)
             and not getattr(info, 'st_file_attributes', 0) & 0x400
             and info.st_nlink == 1 and 0 < info.st_size <= max_bytes)
    return info


def _signature(info):
    # Windows CRT fstat ctime can differ from lstat even for an unchanged file.
    return (info.st_dev, info.st_ino, info.st_size, info.st_mtime_ns,
            info.st_nlink, info.st_mode, getattr(info, 'st_file_attributes', 0))


def _unchanged(path, archive, before, max_bytes):
    reject_named_streams(path)
    _require(_signature(_regular(path.lstat(), max_bytes)) == _signature(before))
    _require(_signature(_regular(os.fstat(archive.fileno()), max_bytes)) == _signature(before))


def restore_dump(path, *, expected_sha256, source_project, destination_project,
                 owner_scope, env, attest, timeout=300, max_bytes=MAX_BYTES,
                 popen=subprocess.Popen):
    process = None
    try:
        env = _preflight(source_project, owner_scope, env, attest, timeout, max_bytes)
        _require(_match(r'dg-recovery-[0-9a-f]{32}', destination_project)
                 and source_project != destination_project)
        _require(_match(r'[0-9a-f]{64}', expected_sha256))
        path = _parent(path)
        before = _regular(path.lstat(), max_bytes)
        descriptor = os.open(path, os.O_RDONLY | getattr(os, 'O_BINARY', 0) | getattr(os, 'O_NOFOLLOW', 0))
        with os.fdopen(descriptor, 'rb') as archive:
            _unchanged(path, archive, before, max_bytes)
            digest = hashlib.sha256()
            count = 0
            while chunk := archive.read(CHUNK):
                count += len(chunk)
                _require(count <= max_bytes)
                digest.update(chunk)
            _require(count == before.st_size and digest.hexdigest() == expected_sha256)
            _unchanged(path, archive, before, max_bytes)
            request = dict(operation='restore', sourceProject=source_project,
                destinationProject=destination_project, ownerScope=owner_scope,
                sha256=digest.hexdigest(), bytes=count,
                connection={k: env[k] for k in ('PGHOST', 'PGPORT', 'PGDATABASE', 'PGUSER')})
            _require(attest(request) is True)
            _unchanged(path, archive, before, max_bytes)
            archive.seek(0)
            verified = hashlib.sha256()
            verified_count = 0
            while chunk := archive.read(CHUNK):
                verified_count += len(chunk)
                _require(verified_count <= max_bytes)
                verified.update(chunk)
            _require(verified_count == count and verified.hexdigest() == expected_sha256)
            _unchanged(path, archive, before, max_bytes)
            archive.seek(0)
            process = popen([PG_RESTORE, '--exit-on-error', '--single-transaction',
                            '--no-password', '--dbname', env['PGDATABASE']],
                            stdin=archive, stdout=subprocess.DEVNULL,
                            stderr=subprocess.DEVNULL, shell=False, env=env)
            _require(process.wait(timeout=timeout) == 0)
        return dict(status='POSTGRES_RESTORE_PROCESS_COMPLETED_NOT_RECOVERY',
                    bytes=count, sha256=digest.hexdigest(), nativeRecoveryProven=False)
    except Exception:
        raise PostgresError(ERROR) from None
    finally:
        if process is not None:
            try:
                if process.poll() is None:
                    process.kill()
                process.wait(timeout=5)
            except Exception:
                raise PostgresError(ERROR) from None


def verify_archive(path, expected_sha256, *, max_bytes=MAX_BYTES):
    """Read-only integrity check; makes no native-format or provenance claim."""
    try:
        _require(type(max_bytes) is int and 0 < max_bytes <= MAX_BYTES)
        _require(_match(r'[0-9a-f]{64}', expected_sha256))
        path = _parent(path)
        before = _regular(path.lstat(), max_bytes)
        descriptor = os.open(path, os.O_RDONLY | getattr(os, 'O_BINARY', 0) | getattr(os, 'O_NOFOLLOW', 0))
        with os.fdopen(descriptor, 'rb') as archive:
            _unchanged(path, archive, before, max_bytes)
            digest = hashlib.sha256()
            count = 0
            while chunk := archive.read(CHUNK):
                count += len(chunk)
                _require(count <= max_bytes)
                digest.update(chunk)
            _unchanged(path, archive, before, max_bytes)
            _require(count == before.st_size and digest.hexdigest() == expected_sha256)
        return dict(status='POSTGRES_ARCHIVE_HASH_VERIFIED_NOT_RECOVERY', bytes=count,
                    sha256=digest.hexdigest(), nativeRecoveryProven=False)
    except Exception:
        raise PostgresError(ERROR) from None


class _Parser(argparse.ArgumentParser):
    def error(self, message):
        raise PostgresError(ERROR)


def main(argv=None):
    parser = _Parser(description='Read-only archive integrity. Mutation is trusted-runner module API only.',
                     allow_abbrev=False)
    parser.add_argument('--archive', required=True)
    parser.add_argument('--expected-sha256', required=True)
    try:
        args = parser.parse_args(argv)
        report = verify_archive(args.archive, args.expected_sha256)
    except PostgresError:
        print(json.dumps(dict(status='REJECTED', reason=ERROR)))
        return 1
    print(json.dumps(report))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
