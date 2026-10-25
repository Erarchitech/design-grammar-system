"""OFFLINE reference logic for a bounded PostgreSQL output sink; NOT a qualified transport.

The only producer destination is an anonymous pipe. The sink checks the remaining
byte budget BEFORE every write, so the result file can never exceed it. The budget
is a mandatory caller-supplied parameter: there is deliberately no default, and any
value above HARD_CEILING is rejected. A Linux production supervisor (PID 1 in a
dedicated one-shot container) must reproduce this behaviour; see PG-TRANSPORT.md.
Windows execution proves file bounds and direct-child reap only, not Linux
permissions, process groups, cgroup cleanup or native PostgreSQL behaviour.
"""
import hashlib
import os
from pathlib import Path
import queue
import signal
import stat
import subprocess
import threading
import time

# Absolute upper bound on any budget a caller may request. A safety rail, not a
# recommended or measured size; the operational budget is an owner decision.
HARD_CEILING = 1024 * 1024 * 1024
MAX_SECONDS = 180
SQL = '/opt/recovery/sql/snapshot.sql'
MODES = {
    'snapshot': ('source.json', ('/usr/local/bin/psql', '-X', '--no-password', '-qAt', '-v',
                                 'ON_ERROR_STOP=1', '--dbname=speckle', '--file=' + SQL)),
    'dump': ('speckle.dump', ('/usr/local/bin/pg_dump', '--format=custom', '--no-password',
                              '--no-owner', '--no-privileges', '--dbname=speckle')),
}


def pg_spec(mode, password):
    """Fixed argv and environment: no arbitrary argv, URI/password argument, --output,
    --file dump, --jobs or host overrides. Raises KeyError for an unknown mode."""
    name, argv = MODES[mode]
    if not isinstance(password, str) or not password or '\x00' in password:
        raise ValueError('AUTH_REJECTED')
    env = {'PGHOST': 'speckle-postgres', 'PGPORT': '5432', 'PGDATABASE': 'speckle',
           'PGUSER': 'speckle', 'PGPASSWORD': password, 'PGCONNECT_TIMEOUT': '5',
           'PGCLIENTENCODING': 'UTF8', 'LC_ALL': 'C', 'HOME': '/nonexistent',
           'PGSYSCONFDIR': '/nonexistent'}
    return name, argv, env


def valid_budget(limit):
    return type(limit) is int and 0 < limit <= HARD_CEILING


def _checked_parent(parent):
    # No resolve(): it would erase links before they are checked.
    parent = Path(os.path.abspath(parent))
    for item in [*reversed(parent.parents), parent]:
        info = item.lstat()
        if stat.S_ISLNK(info.st_mode) or not stat.S_ISDIR(info.st_mode):
            raise ValueError('PARENT_REJECTED')
        if getattr(info, 'st_file_attributes', 0) & 0x400:
            raise ValueError('PARENT_REJECTED')
    if os.name == 'posix':
        info = parent.stat()
        if info.st_uid != os.geteuid() or stat.S_IMODE(info.st_mode) & 0o077:
            raise ValueError('PRIVATE_PARENT_REQUIRED')
    return parent


def bounded_child(parent, directory_name, argv, env, limit, seconds, filename='result.bin'):
    """Run argv with stdout captured through a pipe and publish at most `limit` bytes.

    `limit` has no default. This function accepts arbitrary argv for tests only and
    must NOT be exposed as a production CLI; production code passes pg_spec() output.
    No child bytes, exception messages, paths or environment appear in the report.
    """
    report = {'status': 'REJECTED', 'writtenBytes': 0, 'peakFileBytes': 0,
              'directChildReaped': False, 'readerJoined': False,
              'nativeRecoveryProven': False, 'remoteCleanupQualified': False}
    if not valid_budget(limit):
        return report
    if type(seconds) not in (int, float) or not 0 < seconds <= MAX_SECONDS:
        return report
    if type(directory_name) is not str or not directory_name \
            or Path(directory_name).name != directory_name or directory_name in ('.', '..'):
        return report
    if type(filename) is not str or not filename \
            or Path(filename).name != filename or filename in ('.', '..', '.part'):
        return report
    try:
        parent = _checked_parent(parent)
    except (OSError, ValueError):
        return report
    run = parent / directory_name
    owned = False
    proc = reader = out = None
    stop = threading.Event()
    frames = queue.Queue(maxsize=2)
    partial = run / '.part'
    final = run / filename
    deadline = time.monotonic() + seconds
    try:
        run.mkdir(mode=0o700)  # exclusive ownership; never clean up somebody else's collision
        owned = True
        flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL | getattr(os, 'O_NOFOLLOW', 0) | getattr(os, 'O_BINARY', 0)
        out = os.fdopen(os.open(partial, flags, 0o600), 'wb', buffering=0)
        proc = subprocess.Popen(tuple(argv), stdin=subprocess.DEVNULL, stdout=subprocess.PIPE,
                                stderr=subprocess.DEVNULL, env=dict(env), close_fds=True,
                                start_new_session=(os.name == 'posix'))

        def put(value):
            while not stop.is_set():
                try:
                    frames.put(value, timeout=.025)
                    return
                except queue.Full:
                    pass

        def drain():
            try:
                while not stop.is_set():
                    chunk = proc.stdout.read1(65536)
                    if not chunk:
                        put(None)
                        return
                    put(chunk)
            except Exception:
                put(False)

        reader = threading.Thread(target=drain, daemon=True)
        reader.start()
        digest = hashlib.sha256()
        while True:
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                report['status'] = 'TIMEOUT'
                break
            try:
                chunk = frames.get(timeout=min(.025, remaining))
            except queue.Empty:
                continue
            if chunk is None:
                remaining = deadline - time.monotonic()
                try:
                    code = proc.wait(timeout=max(.001, remaining))
                except subprocess.TimeoutExpired:
                    report['status'] = 'TIMEOUT'
                    break
                if code != 0:
                    report['status'] = 'CHILD_FAILED'
                elif report['writtenBytes'] == 0:
                    report['status'] = 'EMPTY'
                else:
                    out.flush()
                    os.fsync(out.fileno())
                    out.close()
                    out = None
                    # link() never replaces an existing name; do not use os.replace.
                    os.link(partial, final)
                    # Published: the report must match the disk even if tidying fails.
                    report.update(status='COMPLETE', sha256=digest.hexdigest())
                    try:
                        partial.unlink()
                    except OSError:
                        pass
                break
            if chunk is False:
                report['status'] = 'READ_FAILED'
                break
            if len(chunk) > limit - report['writtenBytes']:
                report['status'] = 'OVERFLOW'
                break  # the excess is never written, not even transiently
            offset = 0
            while offset < len(chunk):
                count = out.write(chunk[offset:])
                if not count:
                    raise OSError('WRITE_FAILED')
                offset += count
                report['writtenBytes'] += count
                report['peakFileBytes'] = max(report['peakFileBytes'], os.fstat(out.fileno()).st_size)
            digest.update(chunk)
    except FileExistsError:
        report['status'] = 'COLLISION'
    except Exception:
        report['status'] = 'REJECTED'
    finally:
        stop.set()
        if proc is not None:
            # POSIX: kill the whole fixed-tool session group. NOT a proof against setsid escape.
            if os.name == 'posix':
                try:
                    os.killpg(proc.pid, signal.SIGKILL)
                except OSError:
                    pass  # gone or no longer ours (PGID reuse); the wait/join below must still run
            elif proc.poll() is None:
                proc.kill()  # Windows test path: no descendant claim
            try:
                proc.wait(timeout=2)
                report['directChildReaped'] = True
            except subprocess.TimeoutExpired:
                report['status'] = 'CLEANUP_FAILED'
            if reader is not None:
                reader.join(timeout=2)
                report['readerJoined'] = not reader.is_alive()
                if reader.is_alive():
                    report['status'] = 'CLEANUP_FAILED'
            if report['readerJoined'] or reader is None:
                proc.stdout.close()
        if out is not None:
            out.close()
        if owned and report['status'] != 'COMPLETE':
            partial.unlink(missing_ok=True)
            # A colliding final file is intentionally preserved, never deleted.
            try:
                run.rmdir()
            except OSError:
                pass
    return report
