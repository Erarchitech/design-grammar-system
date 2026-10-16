"""Offline synthetic fixtures only; no services, real cookies, or user keys."""
import importlib.util
import json
import os
from pathlib import Path
import struct
import subprocess
import sys
import tempfile
import unittest
from unittest import mock

from cryptography.hazmat.primitives.ciphers.aead import AESGCM

MODULE = Path(__file__).resolve().parents[1] / 'recovery-test' / 'snapshot.py'
REVISION = 'c82b92b29423c515e353e3fa4f9c17e9b0d83438'


class SnapshotTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(dir=os.environ.get('TMPDIR'))
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.source = self.root / 'source'
        self.source.mkdir()
        (self.source / 'nested').mkdir()
        (self.source / 'empty').mkdir()
        (self.source / 'nested' / 'data.bin').write_bytes(b'synthetic-api-data\x00')
        self.exchange = self.root / 'exchange'
        self.exchange.mkdir()
        (self.exchange / 'neo4j.dump').write_bytes(b'synthetic-native-dump')
        (self.exchange / 'probe-state.json').write_bytes(b'{"fixture":"synthetic-only"}')
        self.dest = self.root / 'destination'
        self.dest.mkdir()
        self.out = self.root / 'out'
        self.out.mkdir()
        self.key = AESGCM.generate_key(bit_length=256).hex()
        patch = mock.patch.dict(os.environ, {'RECOVERY_KEY': self.key})
        patch.start()
        self.addCleanup(patch.stop)

    def module(self):
        self.assertTrue(MODULE.is_file(), 'snapshot helper is not implemented')
        spec = importlib.util.spec_from_file_location('snapshot_test_module', MODULE)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module

    def seal(self, m):
        m.seal(self.source, self.exchange)
        (self.out / 'backup.enc').write_bytes((self.exchange / 'backup.enc').read_bytes())

    def tree(self, root):
        return {p.relative_to(root).as_posix(): p.read_bytes() if p.is_file() else None
                for p in root.rglob('*')}

    def test_real_encryption_roundtrip_full_tree_and_dump(self):
        m = self.module()
        self.seal(m)
        cipher = (self.out / 'backup.enc').read_bytes()
        self.assertNotIn(b'synthetic', cipher)
        self.assertNotIn(self.key.encode(), cipher)
        m.open_snapshot(self.dest, self.out)
        self.assertEqual(self.tree(self.source), self.tree(self.dest))
        for name in ('neo4j.dump', 'probe-state.json'):
            self.assertEqual((self.out / name).read_bytes(), (self.exchange / name).read_bytes())
        marker = json.loads((self.out / m.MARKER).read_bytes())
        self.assertEqual(marker, {'schema': 1, 'state': 'complete', 'framework_revision': REVISION})
        (self.exchange / 'backup.enc').unlink()
        m.seal(self.source, self.exchange)
        self.assertNotEqual(cipher, (self.exchange / 'backup.enc').read_bytes())

    def assert_open_rejected(self, m):
        before = self.tree(self.root)
        with self.assertRaisesRegex(m.SnapshotError, '^snapshot operation rejected$'):
            m.open_snapshot(self.dest, self.out)
        self.assertEqual(before, self.tree(self.root))
        self.assertFalse((self.out / m.MARKER).exists())

    def tamper(self, m, manifest_change=None, body_change=None):
        path = self.out / 'backup.enc'
        envelope = path.read_bytes()
        plain = AESGCM(bytes.fromhex(self.key)).decrypt(envelope[8:20], envelope[20:], m.AAD)
        count = struct.unpack('>I', plain[:4])[0]
        manifest = json.loads(plain[4:4 + count])
        body = plain[4 + count:]
        if manifest_change:
            manifest_change(manifest)
        if body_change:
            body = body_change(body)
        metadata = json.dumps(manifest, sort_keys=True, separators=(',', ':')).encode()
        plain = struct.pack('>I', len(metadata)) + metadata + body
        nonce = os.urandom(12)
        path.write_bytes(m.MAGIC + nonce + AESGCM(bytes.fromhex(self.key)).encrypt(nonce, plain, m.AAD))

    def test_authenticated_invalid_inventory_rejected_before_staging(self):
        m = self.module()
        self.seal(m)
        original = (self.out / 'backup.enc').read_bytes()
        changes = {
            'revision': lambda x: x.update(framework_revision='a' * 40),
            'schema-type': lambda x: x.update(schema=True),
            'extra-field': lambda x: x.update(key='not-permitted'),
            'store-missing': lambda x: x['stores'].pop('api-state'),
            'hash': lambda x: x['entries'][-1].update(sha256='0' * 64),
            'extra-member': lambda x: x['entries'][-1].update(extra=1),
            'traversal': lambda x: x['entries'][-1].update(path='../escape'),
            'absolute': lambda x: x['entries'][-1].update(path='/escape'),
            'windows': lambda x: x['entries'][-1].update(path='C:\\escape'),
            'backslash': lambda x: x['entries'][-1].update(path='state\\escape'),
            'device': lambda x: x['entries'][-1].update(path='state/CON.txt'),
            'directory-data': lambda x: x['entries'][0].update(size=1),
            'negative-size': lambda x: x['entries'][-1].update(size=-1),
            'boolean-size': lambda x: x['entries'][-1].update(size=True),
            'symlink-type': lambda x: x['entries'][-1].update(type='symlink'),
            'store-mismatch': lambda x: x['entries'][-1].update(store='api-state'),
            'missing': lambda x: x['entries'].pop(),
            'duplicate': lambda x: x['entries'].append(x['entries'][0].copy()),
            'unknown-exchange-file': lambda x: x['entries'][-1].update(path='extra.json'),
            'missing-parent': lambda x: x['entries'].pop(2),
            'case-collision': lambda x: x['entries'].append(dict(x['entries'][1], path='STATE/EMPTY')),
        }
        for name, change in changes.items():
            with self.subTest(name=name):
                (self.out / 'backup.enc').write_bytes(original)
                self.tamper(m, manifest_change=change)
                with mock.patch.object(m.tempfile, 'mkdtemp', side_effect=AssertionError('must not stage')) as stage:
                    self.assert_open_rejected(m)
                    stage.assert_not_called()
        (self.out / 'backup.enc').write_bytes(original)
        self.tamper(m, body_change=lambda data: data + b'extra-unlisted-bytes')
        self.assert_open_rejected(m)

    def test_wrong_key_corrupt_truncated_inputs_do_not_mutate(self):
        m = self.module()
        self.seal(m)
        original = (self.out / 'backup.enc').read_bytes()
        with mock.patch.dict(os.environ, {'RECOVERY_KEY': '00' * 32}):
            self.assert_open_rejected(m)
        for changed in (b'', original[:8], original[:20], original[:-1],
                        original[:-1] + bytes([original[-1] ^ 1]), original + b'extra'):
            with self.subTest(length=len(changed)):
                (self.out / 'backup.enc').write_bytes(changed)
                self.assert_open_rejected(m)

    def assert_seal_rejected(self, m):
        with self.assertRaisesRegex(m.SnapshotError, '^snapshot operation rejected$'):
            m.seal(self.source, self.exchange)
        self.assertFalse((self.exchange / 'backup.enc').exists())
        self.assertFalse(any(p.name.startswith('.snapshot-') for p in self.root.rglob('*')))

    def test_nonempty_destination_and_existing_outputs_never_overwritten(self):
        m = self.module()
        self.seal(m)
        for target in (self.dest / 'unrelated', self.out / 'neo4j.dump',
                       self.out / 'probe-state.json', self.out / m.MARKER):
            with self.subTest(target=target.name):
                target.write_bytes(b'existing-sentinel')
                before = self.tree(self.root)
                with self.assertRaises(m.SnapshotError):
                    m.open_snapshot(self.dest, self.out)
                self.assertEqual(before, self.tree(self.root))
                target.unlink()
        before = self.tree(self.root)
        with self.assertRaises(m.SnapshotError):
            m.seal(self.source, self.exchange)
        self.assertEqual(before, self.tree(self.root))

    def make_directory_link(self, link, target):
        try:
            link.symlink_to(target, target_is_directory=True)
            return 'symlink'
        except OSError:
            if os.name != 'nt':
                raise
            subprocess.run(['cmd.exe', '/c', 'mklink', '/J', str(link), str(target)],
                           check=True, capture_output=True)
            self.assertTrue(getattr(link, 'is_junction', lambda: False)(), 'junction fallback must be real')
            return 'junction'

    def test_directory_symlink_or_windows_junction_rejected(self):
        m = self.module()
        link = self.source / 'linked'
        self.make_directory_link(link, self.out)
        try:
            self.assert_seal_rejected(m)
        finally:
            link.rmdir() if getattr(link, 'is_junction', lambda: False)() else link.unlink()

    def test_hardlinked_input_rejected(self):
        m = self.module()
        os.link(self.source / 'nested' / 'data.bin', self.source / 'alias.bin')
        self.assert_seal_rejected(m)

    def test_unsafe_names_rejected_on_seal(self):
        m = self.module()
        bad = self.source / 'unsafe name'
        bad.write_bytes(b'fixture')
        self.assert_seal_rejected(m)

    def test_linked_destination_rejected(self):
        m = self.module()
        self.seal(m)
        self.dest.rmdir()
        self.make_directory_link(self.dest, self.source / 'empty')
        try:
            with self.assertRaises(m.SnapshotError):
                m.open_snapshot(self.dest, self.out)
            self.assertEqual(list((self.source / 'empty').iterdir()), [])
            self.assertFalse((self.out / m.MARKER).exists())
        finally:
            self.dest.rmdir() if getattr(self.dest, 'is_junction', lambda: False)() else self.dest.unlink()

    def test_bounds_enforced_on_seal_and_authenticated_open(self):
        m = self.module()
        self.seal(m)
        for constant, limit in (('MAX_FILE', 8), ('MAX_TOTAL', 16), ('MAX_ENTRIES', 3), ('MAX_MANIFEST', 8)):
            with self.subTest(constant=constant), mock.patch.object(m, constant, limit):
                (self.exchange / 'backup.enc').unlink(missing_ok=True)
                self.assert_seal_rejected(m)
                self.assert_open_rejected(m)

    def test_exact_aes256_hex_key_required(self):
        m = self.module()
        for value in ('00' * 16, '00' * 24, '00' * 33, 'zz' * 32, ' 00' * 32):
            with self.subTest(length=len(value)), mock.patch.dict(os.environ, {'RECOVERY_KEY': value}):
                self.assert_seal_rejected(m)

    def test_native_dump_larger_than_old_eight_mib_limit(self):
        m = self.module()
        payload = b'native-fixture' * (700 * 1024)
        self.assertGreater(len(payload), 8 * 1024 * 1024)
        (self.exchange / 'neo4j.dump').write_bytes(payload)
        self.seal(m)
        m.open_snapshot(self.dest, self.out)
        self.assertEqual((self.out / 'neo4j.dump').read_bytes(), payload)

    def test_interrupted_publication_rolls_back_and_never_marks_complete(self):
        m = self.module()
        self.seal(m)
        original = m._publish_file
        calls = []
        def interrupt(source, target):
            calls.append(target)
            if len(calls) == 2:
                raise KeyboardInterrupt()
            original(source, target)
        before = self.tree(self.root)
        with mock.patch.object(m, '_publish_file', side_effect=interrupt):
            with self.assertRaises(KeyboardInterrupt):
                m.open_snapshot(self.dest, self.out)
        self.assertEqual(before, self.tree(self.root))
        self.assertFalse((self.out / m.MARKER).exists())

    def cli(self, mode, state=None, exchange=None, env=None):
        return subprocess.run([sys.executable, str(MODULE), mode, '--state', str(state or self.source),
                               '--exchange', str(exchange or self.exchange)],
                              env=env, capture_output=True, text=True)

    def test_cli_seal_negative_open_and_sanitized_errors(self):
        m = self.module()
        result = self.cli('seal')
        self.assertEqual((result.returncode, result.stdout, result.stderr), (0, 'snapshot sealed\n', ''))
        (self.out / 'backup.enc').write_bytes((self.exchange / 'backup.enc').read_bytes())
        before = self.tree(self.root)
        result = self.cli('check-negative', self.dest, self.out)
        self.assertEqual((result.returncode, result.stdout, result.stderr),
                         (0, 'snapshot negative checks passed\n', ''))
        self.assertEqual(before, self.tree(self.root))
        result = self.cli('open', self.dest, self.out)
        self.assertEqual((result.returncode, result.stdout, result.stderr), (0, 'snapshot opened\n', ''))
        self.assertEqual(self.tree(self.source), self.tree(self.dest))
        result = self.cli('seal')
        self.assertEqual((result.returncode, result.stdout, result.stderr), (1, '', m.ERROR + '\n'))
        result = self.cli('sensitive-unrecognized-value')
        self.assertEqual((result.returncode, result.stdout, result.stderr), (2, '', m.ERROR + '\n'))

    def test_negative_checks_restore_environment_and_do_not_mutate(self):
        m = self.module()
        self.seal(m)
        before = self.tree(self.root)
        m.check_negative(self.dest, self.out)
        self.assertEqual(os.environ['RECOVERY_KEY'], self.key)
        self.assertEqual(before, self.tree(self.root))

    def test_staging_stays_on_destination_filesystems(self):
        m = self.module()
        self.seal(m)
        real = m.tempfile.TemporaryDirectory
        with mock.patch.object(m.tempfile, 'TemporaryDirectory', wraps=real) as stage:
            m.open_snapshot(self.dest, self.out)
        self.assertEqual([call.kwargs['dir'] for call in stage.call_args_list], [self.dest, self.out])

    def test_actual_bounds_and_sparse_oversize_file(self):
        m = self.module()
        self.assertEqual((m.MAX_FILE, m.MAX_TOTAL, m.MAX_ENTRIES), (64 * 1024 * 1024, 128 * 1024 * 1024, 1024))
        with (self.exchange / 'neo4j.dump').open('wb') as stream:
            stream.truncate(m.MAX_FILE + 1)
        self.assert_seal_rejected(m)

    def test_negative_invalid_baseline_restores_environment(self):
        m = self.module()
        self.seal(m)
        (self.out / 'backup.enc').write_bytes(b'truncated')
        before = self.tree(self.root)
        with self.assertRaises(m.SnapshotError):
            m.check_negative(self.dest, self.out)
        self.assertEqual(os.environ['RECOVERY_KEY'], self.key)
        self.assertEqual(before, self.tree(self.root))

    def test_truncated_inputs_never_create_even_temporary_staging(self):
        m = self.module()
        self.seal(m)
        (self.out / 'backup.enc').write_bytes((self.out / 'backup.enc').read_bytes()[:-1])
        with mock.patch.object(m.tempfile, 'mkdtemp', side_effect=AssertionError('must not stage')) as stage:
            self.assert_open_rejected(m)
            stage.assert_not_called()

    def test_missing_state_root_and_missing_dump_rejected(self):
        m = self.module()
        self.seal(m)
        self.tamper(m, manifest_change=lambda value: value['entries'].pop(0))
        self.assert_open_rejected(m)
        (self.exchange / 'backup.enc').unlink()
        (self.exchange / 'neo4j.dump').unlink()
        self.assert_seal_rejected(m)

    def test_unusual_fifo_entry_rejected_without_blocking(self):
        m = self.module()
        # Windows lacks FIFOs: real socket is also an unusual, non-regular entry.
        if hasattr(os, 'mkfifo'):
            os.mkfifo(self.source / 'fifo')
            self.assert_seal_rejected(m)
        else:
            # Windows has no portable on-disk FIFO/socket constructor. Exercise
            # its type policy with an explicit simulated FIFO (not a skipped
            # integration test); real reparse entries are covered above.
            from types import SimpleNamespace
            import stat
            fake = SimpleNamespace(st_mode=stat.S_IFIFO | 0o600, st_file_attributes=0, st_nlink=1)
            with mock.patch.object(Path, 'lstat', return_value=fake):
                with self.assertRaises(m.SnapshotError):
                    m._regular(self.source / 'fifo')


if __name__ == '__main__':
    unittest.main()
