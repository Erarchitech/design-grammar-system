"""Synthetic offline transport tests; never connect to services or user keys."""
import importlib.util
import json
import os
from pathlib import Path
import struct
import subprocess
import tracemalloc
from unittest import mock

from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric import padding
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
import sys
import tempfile
import unittest

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa

MODULE = Path(__file__).resolve().parents[1] / 'recovery_archive.py'
REVISION = 'a' * 40


class RecoveryArchiveTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.key = rsa.generate_private_key(public_exponent=65537, key_size=2048)

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(dir=os.environ.get('TMPDIR'))
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.source = self.root / 'export'
        self.source.mkdir()
        (self.source / 'nested').mkdir()
        (self.source / 'nested' / 'payload.bin').write_bytes(b'fixture\x00data')
        (self.source / 'empty.txt').touch()
        (self.source / 'export-complete.json').write_text(json.dumps({
            'schema': 1, 'state': 'complete', 'framework_revision': REVISION}))
        self.public = self.root / 'recipient.pem'
        self.private = self.root / 'recipient-private.pem'
        self.public.write_bytes(self.key.public_key().public_bytes(
            serialization.Encoding.PEM, serialization.PublicFormat.SubjectPublicKeyInfo))
        self.private.write_bytes(self.key.private_bytes(serialization.Encoding.PEM,
            serialization.PrivateFormat.PKCS8, serialization.NoEncryption()))
        self.archive = self.root / 'snapshot.dgar'
        self.dest = self.root / 'restored'

    def module(self):
        self.assertTrue(MODULE.is_file(), 'encrypted offline transport is not implemented')
        spec = importlib.util.spec_from_file_location('recovery_archive', MODULE)
        module = importlib.util.module_from_spec(spec)
        sys.path.insert(0, str(MODULE.parent))
        self.addCleanup(lambda: sys.path.remove(str(MODULE.parent)))
        spec.loader.exec_module(module)
        return module

    def test_roundtrip_nested_regular_files(self):
        m = self.module()
        m.seal(self.source, self.archive, self.public, REVISION, 'lab-2026')
        m.open_archive(self.archive, self.dest, self.private, REVISION, 'lab-2026')
        expected = {p.relative_to(self.source).as_posix(): p.read_bytes()
                    for p in self.source.rglob('*') if p.is_file()}
        actual = {p.relative_to(self.dest).as_posix(): p.read_bytes()
                  for p in self.dest.rglob('*') if p.is_file()}
        self.assertEqual(actual, expected)
        self.assertNotIn(b'fixture', self.archive.read_bytes())

    def seal_fixture(self, m):
        m.seal(self.source, self.archive, self.public, REVISION, 'lab-2026')

    def assert_rejected(self, m, action):
        before = sorted(p.name for p in self.root.iterdir())
        with self.assertRaisesRegex(m.ArchiveError, '^recovery archive operation rejected$'):
            action()
        self.assertFalse(self.dest.exists())
        self.assertEqual(before, sorted(p.name for p in self.root.iterdir()))

    def restore(self, m, **kwargs):
        m.open_archive(self.archive, self.dest, kwargs.get('key', self.private),
                       kwargs.get('revision', REVISION), kwargs.get('key_id', 'lab-2026'))

    def test_interrupted_export_marker_rejected_even_with_completion_marker(self):
        m = self.module()
        (self.source / 'export-in-progress.json').write_text('{}')
        self.assert_rejected(m, lambda: self.seal_fixture(m))
        self.assertFalse(self.archive.exists())

    def test_wrong_key_revision_key_id_preserve_destination(self):
        m = self.module()
        self.seal_fixture(m)
        other = rsa.generate_private_key(public_exponent=65537, key_size=2048)
        wrong = self.root / 'wrong.pem'
        wrong.write_bytes(other.private_bytes(serialization.Encoding.PEM,
            serialization.PrivateFormat.PKCS8, serialization.NoEncryption()))
        for options in ({'key': wrong}, {'revision': 'b' * 40}, {'key_id': 'another-key'}):
            with self.subTest(options=list(options)):
                self.assert_rejected(m, lambda: self.restore(m, **options))

    def test_ciphertext_corruption_and_truncation(self):
        m = self.module()
        self.seal_fixture(m)
        original = self.archive.read_bytes()
        for changed in (original[:-1], original[:5], original[:12],
                        original[:-1] + bytes([original[-1] ^ 1]), original + b'extra'):
            with self.subTest(length=len(changed)):
                self.archive.write_bytes(changed)
                self.assert_rejected(m, lambda: self.restore(m))

    def tamper(self, change_manifest=None, change_header=None, change_body=None):
        """Recipient-authored malformed envelopes exercise validation AFTER GCM."""
        envelope = self.archive.read_bytes()
        end = 12 + struct.unpack('>I', envelope[8:12])[0]
        header = json.loads(envelope[12:end])
        secret = self.key.decrypt(bytes.fromhex(header['wrapped_key']), padding.OAEP(
            mgf=padding.MGF1(hashes.SHA256()), algorithm=hashes.SHA256(), label=b'DGAR001\n'))
        plain = AESGCM(secret).decrypt(bytes.fromhex(header['nonce']), envelope[end:], envelope[:end])
        count = struct.unpack('>I', plain[:4])[0]
        manifest = json.loads(plain[4:4 + count])
        body = plain[4 + count:]
        if change_manifest:
            change_manifest(manifest)
        if change_header:
            change_header(header)
        if change_body:
            body = change_body(body)
        encode = lambda value: json.dumps(value, sort_keys=True, separators=(',', ':')).encode()
        metadata = encode(manifest)
        plain = struct.pack('>I', len(metadata)) + metadata + body
        encoded_header = encode(header)
        prefix = b'DGAR001\n' + struct.pack('>I', len(encoded_header)) + encoded_header
        self.archive.write_bytes(prefix + AESGCM(secret).encrypt(bytes.fromhex(header['nonce']), plain, prefix))

    def test_authenticated_manifest_hash_path_member_tampering(self):
        m = self.module()
        self.seal_fixture(m)
        original = self.archive.read_bytes()
        changes = {
            'hash': lambda x: x['files'][0].update(sha256='0' * 64),
            'traversal': lambda x: x['files'][0].update(path='../outside'),
            'absolute': lambda x: x['files'][0].update(path='/outside'),
            'windows': lambda x: x['files'][0].update(path='C:\\outside'),
            'private': lambda x: x['files'][0].update(path='private.pem'),
            'device': lambda x: x['files'][0].update(path='CON.txt'),
            'trailing-dot': lambda x: x['files'][0].update(path='bad.'),
            'duplicate': lambda x: x['files'].append(x['files'][0].copy()),
            'missing-member': lambda x: x['files'].pop(),
            'extra-field': lambda x: x.update(extra='forbidden'),
            'member-extra': lambda x: x['files'][0].update(extra='forbidden'),
            'revision': lambda x: x.update(framework_revision='b' * 40),
            'fingerprint': lambda x: x.update(recipient_sha256='0' * 64),
            'key-id': lambda x: x.update(key_id='wrong'),
            'case-collision': lambda x: x['directories'].extend(['NESTED']),
            'parent-missing': lambda x: x['directories'].clear(),
            'file-as-parent': lambda x: x['directories'].append('empty.txt'),
            'unsorted': lambda x: x['files'].reverse(),
            'negative-size': lambda x: x['files'][0].update(size=-1),
            'boolean-size': lambda x: x['files'][0].update(size=True),
        }
        for name, change in changes.items():
            with self.subTest(name=name):
                self.archive.write_bytes(original)
                self.tamper(change_manifest=change)
                with mock.patch.object(m, '_publish', side_effect=AssertionError('must not stage')) as publish:
                    self.assert_rejected(m, lambda: self.restore(m))
                    publish.assert_not_called()
        self.archive.write_bytes(original)
        self.tamper(change_body=lambda data: data + b'unlisted-member')
        self.assert_rejected(m, lambda: self.restore(m))

    def test_header_extra_and_recipient_binding_tampering(self):
        m = self.module()
        self.seal_fixture(m)
        original = self.archive.read_bytes()
        for change in (lambda x: x.update(extra=1),
                       lambda x: x.update(recipient_sha256='0' * 64),
                       lambda x: x.update(framework_revision='b' * 40)):
            self.archive.write_bytes(original)
            self.tamper(change_header=change)
            self.assert_rejected(m, lambda: self.restore(m))

    def test_incomplete_missing_or_extra_completion_marker(self):
        m = self.module()
        marker = self.source / 'export-complete.json'
        for value in ({'schema': 1, 'state': 'incomplete', 'framework_revision': REVISION},
                      {'schema': 1, 'state': 'complete', 'framework_revision': 'b' * 40},
                      {'schema': 1, 'state': 'complete', 'framework_revision': REVISION, 'extra': 1}):
            marker.write_text(json.dumps(value))
            self.assert_rejected(m, lambda: self.seal_fixture(m))
        marker.unlink()
        self.assert_rejected(m, lambda: self.seal_fixture(m))

    def test_existing_archive_and_destination_never_overwritten(self):
        m = self.module()
        self.seal_fixture(m)
        original = self.archive.read_bytes()
        self.assert_rejected(m, lambda: self.seal_fixture(m))
        self.assertEqual(self.archive.read_bytes(), original)
        for directory in (False, True):
            with self.subTest(directory=directory):
                if directory:
                    self.dest.mkdir()
                    sentinel = self.dest / 'sentinel'
                else:
                    sentinel = self.dest
                sentinel.write_bytes(b'keep')
                with self.assertRaises(m.ArchiveError):
                    self.restore(m)
                self.assertEqual(sentinel.read_bytes(), b'keep')
                sentinel.unlink()
                if directory:
                    self.dest.rmdir()

    def test_private_unsafe_input_names_rejected(self):
        m = self.module()
        for name in ('.env', 'credentials.json', 'private.pem', 'id_ed25519', 'secret.txt'):
            path = self.source / name
            path.write_bytes(b'not-a-secret')
            self.assert_rejected(m, lambda: self.seal_fixture(m))
            path.unlink()

    def test_symlink_rejected_if_supported(self):
        m = self.module()
        link = self.source / 'linked'
        try:
            link.symlink_to(self.source / 'empty.txt')
        except (OSError, NotImplementedError):
            self.skipTest('symlink creation not permitted on this host')
        self.assert_rejected(m, lambda: self.seal_fixture(m))

    def test_atomic_publish_failure_cleans_staging(self):
        m = self.module()
        with mock.patch.object(m, '_rename_new', side_effect=OSError('synthetic interruption')):
            self.assert_rejected(m, lambda: self.seal_fixture(m))
        self.seal_fixture(m)
        with mock.patch.object(m, '_rename_new', side_effect=KeyboardInterrupt):
            with self.assertRaises(KeyboardInterrupt):
                self.restore(m)
        self.assertFalse(self.dest.exists())
        self.assertFalse(list(self.root.glob('.dg-recovery-*')))

    def test_racing_destination_is_not_replaced(self):
        m = self.module()
        self.seal_fixture(m)
        real = m._rename_new
        def race(source, destination):
            destination.mkdir()
            (destination / 'sentinel').write_bytes(b'keep')
            real(source, destination)
        with mock.patch.object(m, '_rename_new', side_effect=race):
            with self.assertRaises(m.ArchiveError):
                self.restore(m)
        self.assertEqual((self.dest / 'sentinel').read_bytes(), b'keep')
        self.assertFalse(list(self.root.glob('.dg-recovery-*')))

    def test_reference_size_and_working_memory_limit(self):
        m = self.module()
        (self.source / 'large.bin').write_bytes(b'x' * (7 * 1024 * 1024))
        tracemalloc.start()
        try:
            self.seal_fixture(m)
            self.restore(m)
            peak = tracemalloc.get_traced_memory()[1]
        finally:
            tracemalloc.stop()
        self.assertLess(peak, 64 * 1024 * 1024)
        self.archive.unlink()
        with (self.source / 'large.bin').open('wb') as stream:
            stream.truncate(m.MAX_PLAINTEXT + 1)
        with self.assertRaises(m.ArchiveError):
            self.seal_fixture(m)
        self.assertFalse(self.archive.exists())

    def test_completion_marker_revalidated_from_packaged_bytes(self):
        m = self.module()
        original = m._read
        reads = 0
        def changed(path, limit):
            nonlocal reads
            data = original(path, limit)
            if path.name == 'export-complete.json':
                reads += 1
                if reads == 2:
                    return b'{"schema":1,"state":"incomplete","framework_revision":"' + REVISION.encode() + b'"}'
            return data
        with mock.patch.object(m, '_read', side_effect=changed):
            self.assert_rejected(m, lambda: self.seal_fixture(m))

    def test_oversize_completion_marker_rejected_before_json_decode(self):
        m = self.module()
        huge = b' ' * 4097
        with mock.patch.object(m, '_load', side_effect=AssertionError('must not parse')) as load:
            with self.assertRaises(m.ArchiveError):
                m._marker(huge, REVISION)
            load.assert_not_called()

    def test_encrypted_private_pem_library_roundtrip(self):
        m = self.module()
        self.private.write_bytes(self.key.private_bytes(serialization.Encoding.PEM,
            serialization.PrivateFormat.PKCS8, serialization.BestAvailableEncryption(b'synthetic-only')))
        self.seal_fixture(m)
        with self.assertRaises(m.ArchiveError):
            self.restore(m)
        m.open_archive(self.archive, self.dest, self.private, REVISION, 'lab-2026',
                       password=b'synthetic-only')
        self.assertEqual((self.dest / 'nested/payload.bin').read_bytes(), b'fixture\x00data')

    def test_mid_restore_write_failure_removes_plaintext_staging(self):
        m = self.module()
        self.seal_fixture(m)
        original = m._write
        count = 0
        def interrupted(path, data):
            nonlocal count
            original(path, data)
            count += 1
            if count == 2:
                raise OSError('synthetic failed write')
        with mock.patch.object(m, '_write', side_effect=interrupted):
            self.assert_rejected(m, lambda: self.restore(m))
        self.assertFalse(list(self.root.glob('.dg-recovery-*')))

    @unittest.skipUnless(os.name == 'nt', 'Windows sharing semantics')
    def test_windows_publication_retries_transient_reader_without_share_delete(self):
        import ctypes
        from ctypes import wintypes
        import threading
        m = self.module()
        self.seal_fixture(m)
        real = m._rename_new
        observed = []
        def held_reader(source, destination):
            api = ctypes.WinDLL('kernel32', use_last_error=True)
            api.CreateFileW.argtypes = [wintypes.LPCWSTR, wintypes.DWORD, wintypes.DWORD,
                ctypes.c_void_p, wintypes.DWORD, wintypes.DWORD, wintypes.HANDLE]
            api.CreateFileW.restype = wintypes.HANDLE
            api.CloseHandle.argtypes = [wintypes.HANDLE]
            handle = api.CreateFileW(str(source), 0x80000000, 3, None, 3, 0x02000000, None)
            self.assertNotEqual(handle, ctypes.c_void_p(-1).value)
            try:
                try:
                    os.rename(source, destination)
                except PermissionError as error:
                    observed.append(error.winerror)
                self.assertTrue(observed, 'real reader must block rename')
                release = threading.Timer(0.08, lambda: api.CloseHandle(handle))
                release.start()
                try:
                    real(source, destination)
                finally:
                    release.join()
            except BaseException:
                api.CloseHandle(handle)
                raise
        with mock.patch.object(m, '_rename_new', side_effect=held_reader):
            self.restore(m)
        self.assertTrue(self.dest.is_dir())

    def test_same_parent_staging_is_protected_before_plaintext_write(self):
        m = self.module()
        self.seal_fixture(m)
        real_write = m._write
        checked = []
        def inspect(path, data):
            stage = next(p for p in path.parents if p.name.startswith('.dg-recovery-'))
            self.assertEqual(stage.parent, self.dest.parent)
            if os.name == 'nt':
                import ctypes
                from ctypes import wintypes
                api = ctypes.WinDLL('advapi32', use_last_error=True)
                descriptor = ctypes.c_void_p()
                api.GetNamedSecurityInfoW.argtypes = [wintypes.LPWSTR, wintypes.DWORD,
                    wintypes.DWORD, ctypes.c_void_p, ctypes.c_void_p, ctypes.c_void_p,
                    ctypes.c_void_p, ctypes.POINTER(ctypes.c_void_p)]
                self.assertEqual(api.GetNamedSecurityInfoW(str(stage), 1, 4,
                    None, None, None, None, ctypes.byref(descriptor)), 0)
                try:
                    control, revision = wintypes.WORD(), wintypes.DWORD()
                    self.assertTrue(api.GetSecurityDescriptorControl(descriptor,
                        ctypes.byref(control), ctypes.byref(revision)))
                    self.assertTrue(control.value & 0x1000, 'DACL must be protected')
                finally:
                    ctypes.windll.kernel32.LocalFree.argtypes = [ctypes.c_void_p]
                    ctypes.windll.kernel32.LocalFree(descriptor)
            else:
                self.assertEqual(stage.stat().st_mode & 0o777, 0o700)
            checked.append(path)
            real_write(path, data)
        with mock.patch.object(m, '_write', side_effect=inspect):
            self.restore(m)
        self.assertEqual(len(checked), 3)

    @unittest.skipUnless(os.name == 'nt', 'Windows junction check')
    def test_windows_reparse_junction_rejected(self):
        m = self.module()
        outside = self.root / 'outside'
        outside.mkdir()
        junction = self.source / 'junction'
        result = subprocess.run(['cmd.exe', '/c', 'mklink', '/J', str(junction), str(outside)],
                                capture_output=True)
        if result.returncode:
            self.skipTest('junction creation not permitted on this host')
        try:
            self.assert_rejected(m, lambda: self.seal_fixture(m))
        finally:
            os.rmdir(junction)

    def test_authenticated_interrupted_member_rejected_before_staging(self):
        m = self.module()
        self.seal_fixture(m)
        self.tamper(change_manifest=lambda x: x['files'][0].update(path='export-in-progress.json'))
        with mock.patch.object(m, '_publish') as publish:
            self.assert_rejected(m, lambda: self.restore(m))
            publish.assert_not_called()

    def test_declared_limits_reject_before_staging(self):
        m = self.module()
        self.seal_fixture(m)
        original = self.archive.read_bytes()
        cases = [b'DGAR001\n' + struct.pack('>I', m.MAX_HEADER + 1),
                 b'DGAR001\n' + struct.pack('>I', 20) + b'{"schema":1,"schema":1}',
                 b'DGAR001\n' + struct.pack('>I', 2) + b'[]']
        for data in cases:
            self.archive.write_bytes(data)
            self.assert_rejected(m, lambda: self.restore(m))
        self.archive.write_bytes(original)
        with mock.patch.object(m, 'MAX_ENTRIES', 2):
            self.assert_rejected(m, lambda: self.seal_fixture(m))
        with self.archive.open('wb') as stream:
            stream.truncate(m.MAX_ARCHIVE + 1)
        self.assert_rejected(m, lambda: self.restore(m))

    def test_cli_encrypted_pem_refuses_noninteractive_passphrase_input(self):
        m = self.module()
        self.seal_fixture(m)
        self.private.write_bytes(self.key.private_bytes(serialization.Encoding.PEM,
            serialization.PrivateFormat.PKCS8, serialization.BestAvailableEncryption(b'synthetic-only')))
        result = subprocess.run([sys.executable, '-B', str(MODULE), 'open',
            '--archive', str(self.archive), '--destination', str(self.dest),
            '--private-key', str(self.private), '--revision', REVISION, '--key-id', 'lab-2026'],
            input='synthetic-only\n', text=True, capture_output=True, timeout=15)
        self.assertEqual(result.returncode, 1)
        self.assertEqual(result.stderr.strip(), 'recovery archive operation rejected')
        self.assertFalse(self.dest.exists())

    def test_cli_existing_pem_paths_and_sanitized_failures(self):
        base = [sys.executable, '-B', str(MODULE)]
        common = ['--revision', REVISION, '--key-id', 'lab-2026']
        commands = [
            ['seal', '--source', str(self.source), '--output', str(self.archive),
             '--public-key', str(self.public)],
            ['open', '--archive', str(self.archive), '--destination', str(self.dest),
             '--private-key', str(self.private)]]
        for command in commands:
            result = subprocess.run(base + command + common, text=True, capture_output=True)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertNotIn('PRIVATE KEY', result.stdout + result.stderr)
        result = subprocess.run(base + commands[1] + common, text=True, capture_output=True)
        self.assertEqual(result.returncode, 1)
        self.assertEqual(result.stderr.strip(), 'recovery archive operation rejected')
        result = subprocess.run(base + ['open', '--password', 'never-accepted'], text=True, capture_output=True)
        self.assertEqual(result.returncode, 2)
        self.assertNotIn('never-accepted', result.stderr)


if __name__ == '__main__':
    unittest.main()
