"""Synthetic stopped n8n tree packaging, not native n8n qualification."""
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import sys
import tempfile
import unittest
import uuid

MODULE = Path(__file__).resolve().parents[1] / 'recovery_n8n.py'


class N8nStateTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(dir='C:/Users/Admin/AppData/Local/hermes/cache/scratch')
        self.addCleanup(self.temp.cleanup)
        self.base = Path(self.temp.name)
        self.source = self.base / 'source'
        self.source.mkdir()
        self.files = {'config': b'{"encryptionKey":"synthetic-not-a-real-key"}',
                      'database.sqlite': b'synthetic-sqlite-main-not-native',
                      'database.sqlite-wal': b'synthetic-wal',
                      'database.sqlite-shm': b'synthetic-shm',
                      'binaryData/ab/data': b'\x00\xffsynthetic',
                      '.cache/empty': b''}
        for name, data in self.files.items():
            path = self.source / name
            path.parent.mkdir(exist_ok=True, parents=True)
            path.write_bytes(data)
        (self.source / 'empty-directory').mkdir()

    def module(self):
        self.assertTrue(MODULE.is_file(), 'complete stopped n8n state adapter is absent')
        sys.path.insert(0, str(MODULE.parent))
        self.addCleanup(lambda: sys.path.remove(str(MODULE.parent)))
        spec = importlib.util.spec_from_file_location('n8n_state', MODULE)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module

    def test_complete_stopped_tree_roundtrip_preserves_sidecars_binary_and_empty_dirs(self):
        module = self.module()
        package = self.base / 'package'
        manifest = module.export_state(self.source, package, version='2.4.8', attest=lambda _: True)
        self.assertIs(manifest['nativeRecoveryProven'], False)
        digest = hashlib.sha256((package / 'state-manifest.json').read_bytes()).hexdigest()
        destination = self.base / 'destination'
        module.restore_state(package, destination, expected_manifest_sha256=digest,
                             version='2.4.8', attest=lambda _: True)
        actual = {p.relative_to(destination).as_posix(): p.read_bytes()
                  for p in destination.rglob('*') if p.is_file()}
        self.assertEqual(actual, self.files)
        self.assertTrue((destination / 'empty-directory').is_dir())
        self.assertEqual({p.relative_to(self.source).as_posix(): p.read_bytes()
                          for p in self.source.rglob('*') if p.is_file()}, self.files)

    def test_export_rejects_links_streams_overwrite_and_wrong_version(self):
        module = self.module()
        package = self.base / 'pkg-links'
        (self.source / 'database.sqlite').rename(self.source / 'database.sqlite.bak')
        os.link(self.source / 'database.sqlite.bak', self.source / 'database.sqlite')
        with self.assertRaises(module.StateError):
            module.export_state(self.source, package, version='2.4.8', attest=lambda _: True)
        os.remove(self.source / 'database.sqlite')
        (self.source / 'database.sqlite.bak').rename(self.source / 'database.sqlite')
        stream = str(self.source / 'config') + ':hidden'
        with open(stream, 'wb') as out:
            out.write(b'synthetic')
        with self.assertRaises(module.StateError):
            module.export_state(self.source, package, version='2.4.8', attest=lambda _: True)
        os.remove(stream)
        self.assertFalse(package.exists())
        package.mkdir()
        (package / 'preexisting').write_bytes(b'x')
        with self.assertRaises(module.StateError):
            module.export_state(self.source, package, version='2.4.8', attest=lambda _: True)
        self.assertEqual((package / 'preexisting').read_bytes(), b'x')
        (package / 'preexisting').unlink()
        package.rmdir()
        for bad_version in ('2.4.9', '', None, 248):
            with self.subTest(version=bad_version):
                with self.assertRaises(module.StateError):
                    module.export_state(self.source, self.base / ('pkg-v' + str(uuid.uuid4())),
                                        version=bad_version, attest=lambda _: True)
        with self.assertRaises(module.StateError):
            module.export_state(self.source, self.base / ('pkg-a' + str(uuid.uuid4())),
                                version='2.4.8', attest=lambda _: False)
        with self.assertRaises(module.StateError):
            module.export_state(self.source, self.base / ('pkg-b' + str(uuid.uuid4())),
                                version='2.4.8', attest='not-callable')

    def test_external_database_config_is_rejected_not_copied_as_complete(self):
        module = self.module()
        (self.source / 'config').write_text(json.dumps(
            {'database': {'type': 'postgresdb'}}))
        with self.assertRaises(module.StateError):
            module.export_state(self.source, self.base / ('pkg-ext' + str(uuid.uuid4())),
                                version='2.4.8', attest=lambda _: True)
        (self.source / 'config').write_bytes(self.files['config'])

    def test_restore_rejects_tampered_manifest_mismatch_and_overwrite(self):
        module = self.module()
        package = self.base / 'pkg-restore'
        module.export_state(self.source, package, version='2.4.8', attest=lambda _: True)
        digest = hashlib.sha256((package / 'state-manifest.json').read_bytes()).hexdigest()
        good = json.loads((package / 'state-manifest.json').read_text())
        (package / 'tree' / 'config').write_bytes(b'synthetic-swapped')
        with self.assertRaises(module.StateError):
            module.restore_state(package, self.base / 'dest-1',
                                 expected_manifest_sha256=digest, version='2.4.8',
                                 attest=lambda _: True)
        (package / 'tree' / 'config').write_bytes(self.files['config'])
        (package / 'state-manifest.json').write_text(json.dumps(
            {**good, 'files': {**good['files'], 'config': {'bytes': 1, 'sha256': '0' * 64}}}))
        with self.assertRaises(module.StateError):
            module.restore_state(package, self.base / 'dest-2',
                                 expected_manifest_sha256=digest, version='2.4.8',
                                 attest=lambda _: True)
        self.assertFalse((self.base / 'dest-2').exists())
        (package / 'state-manifest.json').write_text(json.dumps(good))
        fresh = hashlib.sha256((package / 'state-manifest.json').read_bytes()).hexdigest()
        destination = self.base / 'dest-3'
        destination.mkdir()
        (destination / 'owner-file').write_bytes(b'keep')
        with self.assertRaises(module.StateError):
            module.restore_state(package, destination, expected_manifest_sha256=fresh,
                                 version='2.4.8', attest=lambda _: True)
        self.assertEqual((destination / 'owner-file').read_bytes(), b'keep')
        with self.assertRaises(module.StateError):
            module.restore_state(package, self.base / 'dest-4',
                                 expected_manifest_sha256='0' * 64, version='2.4.8',
                                 attest=lambda _: True)
        self.assertFalse((self.base / 'dest-4').exists())

    def test_partial_copy_interruption_and_cleanup_errors_are_sanitized(self):
        m = self.module()
        from unittest.mock import patch
        for failure in (OSError('synthetic-private'), KeyboardInterrupt()):
            def fail_copy(source, destination, inventory):
                destination.mkdir()
                (destination / 'partial').write_bytes(b'synthetic')
                raise failure
            with patch.object(m, '_copy', fail_copy):
                error = KeyboardInterrupt if isinstance(failure, KeyboardInterrupt) else m.StateError
                with self.assertRaises(error) as caught:
                    m.export_state(self.source, self.base / 'failed', version='2.4.8', attest=lambda _: True)
                self.assertNotIn('synthetic-private', str(caught.exception))
            self.assertFalse((self.base / 'failed').exists())
            self.assertFalse(list(self.base.glob('.n8n-stage-*')))
        def fail_copy(source, destination, inventory):
            destination.mkdir()
            raise OSError('synthetic-private')
        with patch.object(m, '_copy', fail_copy), patch.object(m.shutil, 'rmtree', side_effect=OSError('synthetic-private')):
            with self.assertRaisesRegex(m.StateError, '^n8n state operation rejected$'):
                m.export_state(self.source, self.base / 'cleanup-failed', version='2.4.8', attest=lambda _: True)
        self.assertFalse((self.base / 'cleanup-failed').exists())
        self.assertTrue(list(self.base.glob('.n8n-stage-*')))

    def test_actual_junction_directory_stream_and_restore_callback_mutation_rejected(self):
        m = self.module()
        import subprocess
        external = self.base / 'external'
        external.mkdir()
        link = self.source / 'escape'
        p = subprocess.run(['cmd.exe', '/c', 'mklink', '/J', str(link), str(external)], capture_output=True)
        self.assertEqual(p.returncode, 0)
        try:
            with self.assertRaises(m.StateError):
                m.export_state(self.source, self.base / 'junction', version='2.4.8', attest=lambda _: True)
        finally:
            os.rmdir(link)
        stream = str(self.source / 'binaryData') + ':unlisted'
        try:
            with open(stream, 'wb') as out:
                out.write(b'synthetic')
            with self.assertRaises(m.StateError):
                m.export_state(self.source, self.base / 'stream', version='2.4.8', attest=lambda _: True)
        finally:
            os.remove(stream)
        package = self.base / 'package-mutate'
        m.export_state(self.source, package, version='2.4.8', attest=lambda _: True)
        digest = hashlib.sha256((package / 'state-manifest.json').read_bytes()).hexdigest()
        def mutate(_):
            (package / 'tree' / 'database.sqlite').write_bytes(b'changed')
            return True
        with self.assertRaises(m.StateError):
            m.restore_state(package, self.base / 'destination-mutate', expected_manifest_sha256=digest,
                            version='2.4.8', attest=mutate)
        self.assertFalse((self.base / 'destination-mutate').exists())

    def test_staging_name_collision_never_deletes_preexisting_tree(self):
        m = self.module()
        from unittest.mock import patch
        class Fixed:
            hex = '0' * 32
        existing = self.base / ('.n8n-stage-' + '0' * 32)
        existing.mkdir()
        (existing / 'keep').write_bytes(b'preexisting')
        with patch.object(m.uuid, 'uuid4', return_value=Fixed()):
            with self.assertRaises(m.StateError):
                m.export_state(self.source, self.base / 'collision', version='2.4.8', attest=lambda _: True)
        self.assertTrue((existing / 'keep').exists(), 'preexisting staging tree was deleted')
        self.assertEqual((existing / 'keep').read_bytes(), b'preexisting')

    def test_restore_staging_collision_preserves_existing_bytes(self):
        m = self.module()
        from unittest.mock import patch
        package = self.base / 'package-collision'
        m.export_state(self.source, package, version='2.4.8', attest=lambda _: True)
        digest = hashlib.sha256((package / 'state-manifest.json').read_bytes()).hexdigest()
        class Fixed:
            hex = '0' * 32
        existing = self.base / ('.n8n-stage-' + '0' * 32)
        existing.mkdir()
        (existing / 'keep').write_bytes(b'preexisting')
        with patch.object(m.uuid, 'uuid4', return_value=Fixed()):
            with self.assertRaises(m.StateError):
                m.restore_state(package, self.base / 'restore-collision', version='2.4.8',
                                expected_manifest_sha256=digest, attest=lambda _: True)
        self.assertTrue((existing / 'keep').exists(), 'restore removed preexisting stage')

    def test_directory_enumeration_stops_at_remaining_entry_budget(self):
        m = self.module()
        from unittest.mock import patch
        for nested in (False, True):
            enumerated = []
            original = Path.iterdir
            folder = self.source / 'binaryData' if nested else self.source
            for i in range(100):
                (folder / f'oversize-{i:03d}').touch()
            def entries(path):
                for entry in original(path):
                    if path == folder:
                        enumerated.append(entry)
                    yield entry
            # Root budget is generous enough to reach the nested directory.
            limit = 20 if nested else 2
            with patch.object(m, 'MAX_FILES', limit), patch.object(Path, 'iterdir', entries):
                with self.assertRaises(m.StateError):
                    m._inventory(self.source)
            self.assertLessEqual(len(enumerated), limit + 1,
                                 'enumerated oversized directory before enforcing bound')
            for i in range(100):
                (folder / f'oversize-{i:03d}').unlink()

    def test_windows_export_and_restore_retry_real_directory_sharing_denial(self):
        import ctypes
        from ctypes import wintypes
        from unittest.mock import patch
        self.assertEqual(os.name, 'nt', 'Windows sharing qualification requires Windows')
        m = self.module()
        api = ctypes.WinDLL('kernel32', use_last_error=True)
        api.CreateFileW.argtypes = [wintypes.LPCWSTR, wintypes.DWORD, wintypes.DWORD,
                                   ctypes.c_void_p, wintypes.DWORD, wintypes.DWORD, wintypes.HANDLE]
        api.CreateFileW.restype = wintypes.HANDLE
        api.CloseHandle.argtypes = [wintypes.HANDLE]
        real_rename = os.rename
        observed = []
        held = set()

        def sharing_denial(source, destination):
            if str(source) not in held:
                held.add(str(source))
                # Read/write sharing only: omit FILE_SHARE_DELETE on a real directory.
                handle = api.CreateFileW(str(source), 0x80000000, 3, None, 3, 0x02000000, None)
                self.assertNotEqual(handle, ctypes.c_void_p(-1).value)
                try:
                    try:
                        real_rename(source, destination)
                    except PermissionError as error:
                        observed.append(error.winerror)
                        raise
                    self.fail('real directory reader did not block rename')
                finally:
                    api.CloseHandle(handle)
            return real_rename(source, destination)

        package = self.base / 'sharing-package'
        with patch.object(m.os, 'rename', sharing_denial):
            m.export_state(self.source, package, version='2.4.8', attest=lambda _: True)
            digest = hashlib.sha256((package / 'state-manifest.json').read_bytes()).hexdigest()
            destination = self.base / 'sharing-destination'
            m.restore_state(package, destination, expected_manifest_sha256=digest,
                            version='2.4.8', attest=lambda _: True)
        self.assertEqual(len(observed), 2, 'both export and restore must hit real denial')
        self.assertTrue(all(code in (5, 32, 33) for code in observed))
        self.assertEqual((destination / 'database.sqlite').read_bytes(), self.files['database.sqlite'])
        self.assertFalse(list(self.base.glob('.n8n-stage-*')))

    def test_publication_refusal_race_and_backoff_interrupt_preserve_destination(self):
        from unittest.mock import patch
        m = self.module()
        package = self.base / 'refusal-package'
        m.export_state(self.source, package, version='2.4.8', attest=lambda _: True)
        digest = hashlib.sha256((package / 'state-manifest.json').read_bytes()).hexdigest()
        for operation in ('export', 'restore'):
            for mode in ('permanent', 'unknown', 'race', 'interrupt'):
                with self.subTest(operation=operation, mode=mode):
                    destination = self.base / (operation + '-' + mode)
                    calls = []
                    pauses = []
                    def denied(source, target):
                        calls.append((source, target))
                        if mode == 'race':
                            target.mkdir()
                            (target / 'owner-marker').write_bytes(b'preserve-owner')
                        error = PermissionError('synthetic-private-sharing-error')
                        error.winerror = 87 if mode == 'unknown' else 5
                        raise error
                    def pause(seconds):
                        pauses.append(seconds)
                        if mode == 'interrupt':
                            raise KeyboardInterrupt()
                    expected = KeyboardInterrupt if mode == 'interrupt' else m.StateError
                    with patch.object(m.os, 'rename', denied), patch.object(m.time, 'sleep', pause):
                        with self.assertRaises(expected) as caught:
                            if operation == 'export':
                                m.export_state(self.source, destination, version='2.4.8',
                                               attest=lambda _: True)
                            else:
                                m.restore_state(package, destination, expected_manifest_sha256=digest,
                                                version='2.4.8', attest=lambda _: True)
                    self.assertNotIn('synthetic-private', str(caught.exception))
                    self.assertEqual(len(calls), 8 if mode == 'permanent' else 1)
                    self.assertEqual(len(pauses), 7 if mode == 'permanent' else int(mode == 'interrupt'))
                    self.assertLessEqual(sum(pauses), 0.7 + 1e-9)
                    if mode == 'race':
                        self.assertEqual((destination / 'owner-marker').read_bytes(), b'preserve-owner')
                    else:
                        self.assertFalse(destination.exists())
                    self.assertFalse(list(self.base.glob('.n8n-stage-*')))
        self.assertEqual((self.source / 'database.sqlite').read_bytes(), self.files['database.sqlite'])

    def test_actual_os_scandir_consumption_is_bounded_before_path_materialization(self):
        m = self.module()
        from unittest.mock import patch
        for i in range(100):
            (self.source / f'entry-{i:03d}').touch()
        consumed = []
        original = os.scandir
        class Counted:
            def __init__(inner, path):
                inner.iterator = original(path)
            def __enter__(inner):
                return inner
            def __exit__(inner, *args):
                inner.iterator.close()
            def __iter__(inner):
                return inner
            def __next__(inner):
                entry = next(inner.iterator)
                consumed.append(entry.name)
                return entry
        with patch.object(m, 'MAX_FILES', 2), patch.object(os, 'scandir', Counted):
            with self.assertRaises(m.StateError):
                m._inventory(self.source)
        self.assertLessEqual(len(consumed), 3, 'Path.iterdir eagerly consumed OS directory listing')


if __name__ == '__main__':
    unittest.main()
