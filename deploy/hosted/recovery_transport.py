"""Pure age transport PLAN, not encryption or a runnable backup CLI.

Engineering candidate: upstream age 1.2.1 streaming authenticated encryption.
NOT installed/qualified here; no known distribution SHA is asserted. Caller hash
is a future independent allowlist input, not verified by this pure function.
Recipient syntax only (Bech32 checksum/ownership validated by qualified age and
owner out of band). No key generation/read, secrets, subprocess or transport.

Future runner MUST verify distribution signature/hash+version before spawn,
stream bounded framed inventory, observe exit0, fsync/exclusively publish, and
verify transferred ciphertext hash. Decrypt into private scratch, exhaust and
authenticate the ENTIRE stream and manifest before any native destination write.
Partial decrypted bytes are never acceptance. age recipient encryption is NOT
exporter identity authentication; authenticated expected archive identity needs
a separate approved provenance channel. Retained identity/custody and current-PC
protected path/transfer/retention are owner gates. Never extend legacy custom crypto.
"""
import re
from pathlib import PureWindowsPath, PurePosixPath


class TransportError(ValueError):
    pass


def age_plan(*, executable, tool_sha256, recipient, recipient_fingerprint, qualified_version):
    if not (type(executable) is str and '\x00' not in executable and
            (PureWindowsPath(executable).is_absolute() or PurePosixPath(executable).is_absolute())
            and type(tool_sha256) is str and re.fullmatch('[0-9a-f]{64}', tool_sha256)
            and type(recipient_fingerprint) is str and re.fullmatch('[0-9a-f]{64}', recipient_fingerprint)
            and type(recipient) is str and re.fullmatch('age1[023456789acdefghjklmnpqrstuvwxyz]{58}', recipient)
            and qualified_version == '1.2.1'):
        raise TransportError('streaming transport plan rejected')
    return {'argv': [executable, '--encrypt', '--recipient', recipient], 'shell': False,
            'toolSha256': tool_sha256, 'version': qualified_version,
            'recipientFingerprint': recipient_fingerprint,
            'stdin': 'verified-framed-export-stream',
            'stdout': 'exclusive-private-ciphertext-file',
            'executableHashMustMatchBeforeSpawn': True,
            'runtimeQualified': False, 'exporterAuthenticated': False}


def encrypt_file(source, destination, *, executable, tool_sha256, recipient,
                 recipient_fingerprint, qualified_version, attest, popen=None,
                 timeout=30, max_input=64 * 1024 ** 3, max_output=65 * 1024 ** 3):
    """Timeout-bound direct-child wrapper, NOT a qualified transport/crypto CLI.

    Output size is monitored, not an OS disk quota: caller MUST provide a quota
    for a hard disk bound. Parent ACL/custody, source framing, binary provenance,
    actual --version and recipient ownership are trusted outer-runner duties.
    Injectable process factory is a test seam, not authorization. No decrypt,
    transfer, key generation or plaintext cleanup is claimed. Only a trusted
    no-descendant executable is permitted; this manages the direct child only.
    """
    import hashlib
    import math
    import os
    import stat
    import subprocess
    import time
    import uuid
    from pathlib import Path
    # Reuse fail-closed regular-file checks, including reparse/ADS/hardlinks.
    import sys
    module_dir = str(Path(__file__).resolve().parent)
    if module_dir not in sys.path:
        sys.path.insert(0, module_dir)
    from recovery_n8n import _regular, _root

    process = None
    stage = None
    def stability(info):
        # Reading may legitimately update atime; it is not source mutation.
        return (info.st_dev, info.st_ino, info.st_mode, info.st_nlink,
                info.st_size, info.st_mtime_ns)
    try:
        plan = age_plan(executable=executable, tool_sha256=tool_sha256,
                        recipient=recipient, recipient_fingerprint=recipient_fingerprint,
                        qualified_version=qualified_version)
        if not (type(timeout) in (float, int) and math.isfinite(timeout) and 0 < timeout <= 3600
                and type(max_input) is int and 0 < max_input <= 64 * 1024 ** 3
                and type(max_output) is int and 0 < max_output <= 65 * 1024 ** 3):
            raise TransportError('streaming transport rejected')
        if attest('private-quota-parent-qualified-tool-and-verified-framed-source') is not True:
            raise TransportError('streaming transport rejected')
        source, destination, tool = Path(source).absolute(), Path(destination).absolute(), Path(executable)
        _root(destination.parent)
        if os.path.lexists(destination):
            raise TransportError('streaming transport rejected')
        _regular(tool)
        digest = hashlib.sha256()
        with tool.open('rb') as binary:
            for chunk in iter(lambda: binary.read(65536), b''):
                digest.update(chunk)
        if digest.hexdigest() != tool_sha256:
            raise TransportError('streaming transport rejected')
        source_stat = _regular(source)
        if source_stat.st_size > max_input:
            raise TransportError('streaming transport rejected')
        candidate = destination.parent / ('.age-stage-' + uuid.uuid4().hex)
        fd = os.open(candidate, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
        stage = candidate  # Owned only after exclusive creation.
        deadline = time.monotonic() + timeout
        with os.fdopen(fd, 'wb') as output, source.open('rb') as input_stream:
            if stability(os.fstat(input_stream.fileno())) != stability(source_stat):
                raise TransportError('streaming transport rejected')
            process = (popen or subprocess.Popen)(plan['argv'], stdin=input_stream,
                stdout=output, stderr=subprocess.DEVNULL, shell=False, env={},
                cwd=str(destination.parent), close_fds=True)
            while True:
                if time.monotonic() >= deadline or stage.stat().st_size > max_output:
                    raise TransportError('streaming transport rejected')
                try:
                    code = process.wait(timeout=min(0.05, max(0.001, deadline - time.monotonic())))
                    break
                except subprocess.TimeoutExpired:
                    pass
            if code != 0 or not 0 < stage.stat().st_size <= max_output:
                raise TransportError('streaming transport rejected')
            output.flush()
            os.fsync(output.fileno())
        if stability(_regular(source)) != stability(source_stat):
            raise TransportError('streaming transport rejected')
        digest = hashlib.sha256()
        with stage.open('rb') as ciphertext:
            for chunk in iter(lambda: ciphertext.read(65536), b''):
                digest.update(chunk)
        # Atomic no-clobber publication; unsupported filesystems fail closed.
        os.link(stage, destination)
        return {'sha256': digest.hexdigest(), 'bytes': destination.stat().st_size,
                'nativeRecoveryProven': False, 'cryptographyQualified': False,
                'exporterAuthenticated': False, 'offMachineTransferProven': False}
    except BaseException:
        raise TransportError('streaming transport rejected') from None
    finally:
        try:
            if process is not None and process.poll() is None:
                process.kill()
                process.wait(timeout=5)
        finally:
            if stage is not None:
                try:
                    stage.unlink()
                except OSError:
                    raise TransportError('streaming transport cleanup rejected') from None

