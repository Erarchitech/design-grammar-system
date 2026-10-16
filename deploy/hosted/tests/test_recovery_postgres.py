"""Offline child-process/command-contract tests, NOT native PostgreSQL tests.

Run with Python 3.13 and run_required.py; no services or native pg binaries.
"""
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest import mock

MODULE = Path(__file__).resolve().parents[1] / 'recovery_postgres.py'
SOURCE = 'dg-recovery-' + '1' * 32
DESTINATION = 'dg-recovery-' + '2' * 32
SCOPE = 'owner-scope:offline-fixture'
ENV = {'PGHOST': '127.0.0.1', 'PGPORT': '5432', 'PGDATABASE': 'speckle',
       'PGUSER': 'fixture', 'PGPASSWORD': 'synthetic-secret-not-for-report'}
PAYLOAD = b'PGDMP-synthetic-not-a-native-archive'


class PostgresRecoveryTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(dir=Path.home() / 'AppData/Local/hermes/cache/scratch'
                                                if os.name == 'nt' else os.environ['TMPDIR'])
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.path = self.root / 'speckle.dump'
        self.calls = []
        self.requests = []

    def module(self):
        self.assertTrue(MODULE.is_file(), 'bounded native PostgreSQL helper is absent')
        spec = importlib.util.spec_from_file_location('recovery_postgres', MODULE)
        module = importlib.util.module_from_spec(spec)
        sys.path.insert(0, str(MODULE.parent))
        self.addCleanup(lambda: sys.path.remove(str(MODULE.parent)))
        spec.loader.exec_module(module)
        return module

    def attest(self, request):
        self.requests.append(request)
        return True  # Deliberate fake outer-runner authorization, NOT runtime evidence.

    def child(self, script):
        def popen(argv, **kwargs):
            self.calls.append((argv, kwargs))
            # Exercise real subprocess pipes/exit/timeout, replacing only the executable.
            return subprocess.Popen([sys.executable, '-B', '-c', script], **kwargs)
        return popen

    def export(self, module, **overrides):
        arguments = dict(source_project=SOURCE, owner_scope=SCOPE, env=ENV,
                         attest=self.attest, timeout=3,
                         popen=self.child('import sys; sys.stdout.buffer.write(' + repr(PAYLOAD) + ')'))
        arguments.update(overrides)
        return module.export_dump(self.path, **arguments)

    def test_binary_paths_match_official_alpine_install_prefix(self):
        module = self.module()
        self.assertEqual(module.PG_DUMP, '/usr/local/bin/pg_dump')
        self.assertEqual(module.PG_RESTORE, '/usr/local/bin/pg_restore')

    def test_reader_setup_failure_reaps_child_and_removes_partial(self):
        module = self.module()
        for target in ('Queue', 'Thread', 'start'):
            processes = []
            def launch(argv, **kwargs):
                process = self.child('import time; time.sleep(20)')(argv, **kwargs)
                processes.append(process)
                return process
            patch_target = {'Queue': 'queue.Queue', 'Thread': 'threading.Thread',
                            'start': 'threading.Thread.start'}[target]
            parts = patch_target.split('.')
            obj = getattr(module, parts[0])
            if len(parts) == 3:
                obj = getattr(obj, parts[1])
            try:
                with mock.patch.object(obj, parts[-1], side_effect=RuntimeError('synthetic-failure')):
                    with self.assertRaises(module.PostgresError):
                        self.export(module, popen=launch)
                self.assertEqual(len(processes), 0 if target == 'Queue' else 1)
                for process in processes:
                    self.assertIsNotNone(process.poll(), 'child escaped cleanup')
                    self.assertTrue(process.stdout.closed)
                self.assertFalse(self.path.exists())
            finally:
                for process in processes:
                    if process.poll() is None:
                        process.kill()
                    process.wait(timeout=5)
                    process.stdout.close()

    def test_export_interruption_cleans_own_plaintext(self):
        module = self.module()
        def interrupted(argv, **kwargs):
            raise KeyboardInterrupt()
        with self.assertRaises(KeyboardInterrupt):
            self.export(module, popen=interrupted)
        self.assertFalse(self.path.exists())

    def test_export_streams_custom_dump_to_exclusive_file_and_sanitized_manifest(self):
        module = self.module()
        report = self.export(module)
        self.assertEqual(self.path.read_bytes(), PAYLOAD)
        self.assertEqual(self.calls[0][0], [module.PG_DUMP, '--format=custom', '--no-password'])
        self.assertIs(self.calls[0][1]['shell'], False)
        self.assertIs(self.calls[0][1]['stderr'], subprocess.DEVNULL)
        self.assertEqual(report, {'status': 'POSTGRES_EXPORT_CREATED_NOT_RECOVERY',
            'method': 'pg-dump-custom', 'bytes': len(PAYLOAD),
            'sha256': hashlib.sha256(PAYLOAD).hexdigest(), 'nativeRecoveryProven': False})
        self.assertEqual(self.requests[0]['operation'], 'export')
        self.assertEqual(self.requests[0]['sourceProject'], SOURCE)
        self.assertEqual(self.requests[0]['ownerScope'], SCOPE)
        self.assertNotIn(ENV['PGPASSWORD'], json.dumps(self.requests) + json.dumps(report))

    def test_failed_export_kills_reaps_and_removes_only_its_partial(self):
        module = self.module()
        self.assertTrue(hasattr(module, 'PostgresError'), 'sanitized bounded export failure contract absent')
        for script, limits in [
            ('import sys; sys.stdout.buffer.write(b"partial"); sys.exit(7)', {}),
            ('import sys,time; sys.stdout.buffer.write(b"partial"); sys.stdout.flush(); time.sleep(20)', {'timeout': 0.1}),
            ('import sys; sys.stdout.buffer.write(b"x" * 100000)', {'max_bytes': 32}),
        ]:
            with self.subTest(script=script):
                processes = []
                def launch(argv, **kwargs):
                    process = self.child(script)(argv, **kwargs)
                    processes.append(process)
                    return process
                with self.assertRaisesRegex(module.PostgresError, '^PostgreSQL operation rejected$'):
                    self.export(module, popen=launch, **limits)
                self.assertFalse(self.path.exists())
                self.assertIsNotNone(processes[0].poll())
                sentinel = self.root / 'unrelated'
                sentinel.write_bytes(b'keep')
                self.assertEqual(sentinel.read_bytes(), b'keep')
    def test_export_preflight_refuses_untrusted_scope_connection_and_bounds(self):
        module = self.module()
        bad = [dict(attest=None), dict(attest=lambda r: False), dict(attest=lambda r: 1),
               dict(owner_scope=''), dict(source_project='production'),
               dict(timeout=0), dict(timeout=float('nan')), dict(timeout=3601),
               dict(max_bytes=True), dict(max_bytes=module.MAX_BYTES + 1),
               dict(env={**ENV, 'PGDATABASE': 'postgresql://secret@host/db'}),
               dict(env={**ENV, 'PGOPTIONS': '-c session_preload_libraries=evil'}),
               dict(env={**ENV, 'PGSERVICE': 'production'}),
               dict(env={k: v for k, v in ENV.items() if k != 'PGHOST'})]
        for override in bad:
            with self.subTest(override=list(override)):
                with self.assertRaises(module.PostgresError):
                    self.export(module, **override)
                self.assertFalse(self.path.exists())
        self.assertEqual(self.calls, [])

    def test_export_never_overwrites_existing_file(self):
        module = self.module()
        self.path.write_bytes(b'existing')
        with self.assertRaises(module.PostgresError):
            self.export(module)
        self.assertEqual(self.path.read_bytes(), b'existing')
        self.assertEqual(self.calls, [])

    def test_export_requires_protected_parent_and_rejects_junction_ancestor(self):
        module = self.module()
        nested = self.root / 'unprotected'
        nested.mkdir()
        link = self.root / 'alias'
        if os.name == 'nt':
            result = subprocess.run(['cmd.exe', '/c', 'mklink', '/J', str(link), str(nested)], capture_output=True)
            self.assertEqual(result.returncode, 0)
            self.addCleanup(lambda: os.rmdir(link))
        else:
            link.symlink_to(nested, target_is_directory=True)
            nested.chmod(0o777)
            with self.assertRaises(module.PostgresError):
                module.export_dump(nested / 'out', source_project=SOURCE, owner_scope=SCOPE,
                    env=ENV, attest=self.attest, popen=self.child('raise AssertionError'))
        self.path = link / 'out'
        with self.assertRaises(module.PostgresError):
            self.export(module)
        self.assertEqual(self.calls, [])
    def restore(self, module, **overrides):
        arguments = dict(expected_sha256=hashlib.sha256(PAYLOAD).hexdigest(),
            source_project=SOURCE, destination_project=DESTINATION,
            owner_scope=SCOPE, env=ENV, attest=self.attest, timeout=3,
            popen=self.child('import sys; data=sys.stdin.buffer.read(); sys.exit(0 if data == ' + repr(PAYLOAD) + ' else 9)'))
        arguments.update(overrides)
        return module.restore_dump(self.path, **arguments)

    def test_restore_verifies_archive_before_attested_atomic_restore(self):
        module = self.module()
        self.assertTrue(hasattr(module, 'restore_dump'), 'verified PostgreSQL restore absent')
        self.path.write_bytes(PAYLOAD)
        report = self.restore(module)
        self.assertEqual(self.calls[0][0], [module.PG_RESTORE, '--exit-on-error',
            '--single-transaction', '--no-password', '--dbname', 'speckle'])
        self.assertEqual(self.requests[0]['operation'], 'restore')
        self.assertEqual(self.requests[0]['destinationProject'], DESTINATION)
        self.assertEqual(self.requests[0]['sha256'], hashlib.sha256(PAYLOAD).hexdigest())
        self.assertIs(self.calls[0][1]['stdout'], subprocess.DEVNULL)
        self.assertIs(self.calls[0][1]['stderr'], subprocess.DEVNULL)
        self.assertEqual(report['status'], 'POSTGRES_RESTORE_PROCESS_COMPLETED_NOT_RECOVERY')
        self.assertIs(report['nativeRecoveryProven'], False)
        self.assertEqual(self.path.read_bytes(), PAYLOAD)
    def test_restore_rejects_corruption_links_oversize_and_missing_authority_before_spawn(self):
        module = self.module()
        self.path.write_bytes(PAYLOAD)
        for override in [dict(destination_project=SOURCE), dict(destination_project='production'),
                         dict(attest=None), dict(attest=lambda r: False), dict(attest=lambda r: 1),
                         dict(owner_scope=''), dict(expected_sha256='0' * 64),
                         dict(expected_sha256=True), dict(max_bytes=len(PAYLOAD) - 1)]:
            with self.subTest(override=list(override)):
                with self.assertRaises(module.PostgresError):
                    self.restore(module, **override)
                self.assertEqual(self.calls, [])
        self.assertEqual(self.requests, [])

    @unittest.skipUnless(os.name == 'nt', 'NTFS stream regression')
    def test_named_streams_rejected_for_restore_verify_and_export_parent(self):
        module = self.module()
        self.path.write_bytes(PAYLOAD)
        for path in (self.path, self.root):
            stream = str(path) + ':hidden'
            try:
                with open(stream, 'wb') as output:
                    output.write(b'synthetic-hidden')
                with self.assertRaises(module.PostgresError):
                    self.restore(module)
                with self.assertRaises(module.PostgresError):
                    module.verify_archive(self.path, hashlib.sha256(PAYLOAD).hexdigest())
            finally:
                os.remove(stream)
        with open(str(self.root) + ':hidden', 'wb') as output:
            output.write(b'synthetic-hidden')
        original = self.path
        self.path = self.root / 'new.dump'
        try:
            with self.assertRaises(module.PostgresError):
                self.export(module)
        finally:
            os.remove(str(self.root) + ':hidden')
            self.path = original
        self.assertEqual(self.calls, [])

    @unittest.skipUnless(os.name == 'nt', 'NTFS stream regression')
    def test_export_rejects_explicit_stream_destination(self):
        module = self.module()
        self.path.write_bytes(PAYLOAD)
        self.path = Path(str(self.path) + ':hidden')
        with self.assertRaises(module.PostgresError):
            self.export(module)
        self.assertEqual(self.calls, [])

    def test_restore_rejects_real_hardlink_before_attestation(self):
        module = self.module()
        self.path.write_bytes(PAYLOAD)
        os.link(self.path, self.root / 'hardlink')
        with self.assertRaises(module.PostgresError):
            self.restore(module)
        self.assertEqual(self.calls, [])
        self.assertEqual(self.requests, [])

    def test_restore_rejects_file_changed_by_attestation(self):
        module = self.module()
        self.path.write_bytes(PAYLOAD)
        def mutate(request):
            self.path.write_bytes(b'x' * len(PAYLOAD))
            return True
        with self.assertRaises(module.PostgresError):
            self.restore(module, attest=mutate)
        self.assertEqual(self.calls, [])

    def test_restore_failure_or_timeout_preserves_archive_and_reaps_child(self):
        module = self.module()
        self.path.write_bytes(PAYLOAD)
        for script in ['import sys; sys.stderr.write("synthetic-secret"); sys.exit(8)',
                       'import time; time.sleep(20)']:
            processes = []
            def launch(argv, **kwargs):
                process = self.child(script)(argv, **kwargs)
                processes.append(process)
                return process
            with self.assertRaisesRegex(module.PostgresError, '^PostgreSQL operation rejected$'):
                self.restore(module, popen=launch, timeout=0.1)
            self.assertIsNotNone(processes[0].poll())
            self.assertEqual(self.path.read_bytes(), PAYLOAD)
    def test_readonly_cli_verifies_hash_and_never_accepts_mutation_flags(self):
        module = self.module()
        self.path.write_bytes(PAYLOAD)
        base = [sys.executable, '-B', str(MODULE), '--archive', str(self.path),
                '--expected-sha256', hashlib.sha256(PAYLOAD).hexdigest()]
        result = subprocess.run(base, capture_output=True, text=True, timeout=5)
        self.assertEqual(result.returncode, 0)
        self.assertTrue(result.stdout.strip(), 'read-only PostgreSQL verification CLI absent')
        self.assertEqual(json.loads(result.stdout), {
            'status': 'POSTGRES_ARCHIVE_HASH_VERIFIED_NOT_RECOVERY',
            'bytes': len(PAYLOAD), 'sha256': hashlib.sha256(PAYLOAD).hexdigest(),
            'nativeRecoveryProven': False})
        self.assertEqual(result.stderr, '')
        for args in [base + ['--restore', 'synthetic-secret'],
                     base[:-1] + ['0' * 64],
                     [sys.executable, '-B', str(MODULE), '--unknown', 'synthetic-secret']]:
            result = subprocess.run(args, capture_output=True, text=True, timeout=5)
            self.assertEqual(result.returncode, 1)
            self.assertEqual(json.loads(result.stdout), {'status': 'REJECTED',
                                                       'reason': 'PostgreSQL operation rejected'})
            self.assertEqual(result.stderr, '')
    def test_restore_rejects_junction_input_before_opening_it(self):
        module = self.module()
        directory = self.root / 'external'
        directory.mkdir()
        if os.name == 'nt':
            result = subprocess.run(['cmd.exe', '/c', 'mklink', '/J', str(self.path), str(directory)],
                                    capture_output=True)
            self.assertEqual(result.returncode, 0)
            self.addCleanup(lambda: os.rmdir(self.path))
        else:
            self.path.symlink_to(directory, target_is_directory=True)
        with self.assertRaises(module.PostgresError):
            self.restore(module)
        self.assertEqual(self.calls, [])
        self.assertEqual(self.requests, [])

    def test_export_streams_many_chunks_without_unbounded_reads(self):
        module = self.module()
        payload = b'z' * (module.CHUNK * 5 + 11)
        self.export(module, popen=self.child('import sys; sys.stdout.buffer.write(b"z" * ' + str(len(payload)) + ')'))
        self.assertEqual(self.path.read_bytes(), payload)
        report = module.verify_archive(self.path, hashlib.sha256(payload).hexdigest())
        self.assertEqual(report['bytes'], len(payload))

    def test_missing_executable_is_sanitized_and_only_own_partial_removed(self):
        module = self.module()
        sentinel = self.root / 'unrelated'
        sentinel.write_bytes(b'keep')
        def absent(argv, **kwargs):
            raise FileNotFoundError('synthetic-secret')
        with self.assertRaisesRegex(module.PostgresError, '^PostgreSQL operation rejected$'):
            self.export(module, popen=absent)
        self.assertFalse(self.path.exists())
        self.assertEqual(sentinel.read_bytes(), b'keep')
    def test_restore_cleanup_failure_never_leaks_child_details(self):
        module = self.module()
        self.path.write_bytes(PAYLOAD)
        class CleanupFailure:
            def wait(self, timeout):
                raise subprocess.TimeoutExpired('synthetic-secret', timeout)
            def poll(self):
                return None
            def kill(self):
                raise OSError('synthetic-secret')
        try:
            self.restore(module, popen=lambda argv, **kwargs: CleanupFailure())
        except Exception as error:
            self.assertIsInstance(error, module.PostgresError, 'cleanup escaped sanitization boundary')
            self.assertEqual(str(error), 'PostgreSQL operation rejected')
        else:
            self.fail('cleanup failure accepted')


if __name__ == '__main__':
    unittest.main()
