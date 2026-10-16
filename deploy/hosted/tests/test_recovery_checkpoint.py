"""Read-only synthetic checkpoint validation; never native recovery evidence."""
import copy
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

MODULE = Path(__file__).resolve().parents[1] / 'recovery_checkpoint.py'
REVISION = 'a' * 40
WRITERS = ['data-service', 'dg-reasoner', 'n8n', 'speckle-server',
           'speckle-frontend-2', 'speckle-preview-service',
           'speckle-webhook-service', 'speckle-fileimport-service']
SERVICES = WRITERS + ['neo4j', 'speckle-postgres', 'speckle-minio', 'speckle-redis']
SECRETS = ['LLM_MASTER_SECRET', 'N8N_ENCRYPTION_KEY', 'POSTGRES_PASSWORD',
           'MINIO_ROOT_USER', 'MINIO_ROOT_PASSWORD', 'SPECKLE_SESSION_SECRET',
           'DG_SERVICE_TOKEN', 'DG_BOOTSTRAP_ADMIN_USER',
           'DG_BOOTSTRAP_ADMIN_PASSWORD', 'N8N_USER', 'N8N_PASSWORD']


class RecoveryCheckpointTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(dir=os.environ.get('TMPDIR'))
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name) / 'exports'
        self.root.mkdir()
        files = {}
        for store, name in [('neo4j', 'neo4j.dump'), ('postgres', 'speckle.dump'),
                            ('objects', 'object.bin'), ('n8n', 'state.bin'),
                            ('api', 'state.bin')]:
            folder = self.root / store
            folder.mkdir()
            # Explicit synthetic bytes, not a claimed native dump/database.
            data = b'synthetic-validator-fixture-' + store.encode()
            (folder / name).write_bytes(data)
            files[store + '/' + name] = {'bytes': len(data),
                'sha256': hashlib.sha256(data).hexdigest()}
        self.manifest = {
            'schemaVersion': 2, 'kind': 'dg-multi-store-export-declaration',
            'sourceRevision': REVISION,
            'sourceProject': 'dg-recovery-' + '1' * 32,
            'destinationProject': 'dg-recovery-' + '2' * 32,
            'images': {name: 'sha256:' + '3' * 64 for name in SERVICES},
            'stoppedWriters': sorted(WRITERS + ['neo4j']),
            'queues': {
                'previewRequest': {'waiting': 0, 'active': 0, 'delayed': 0},
                'previewResponse': {'waiting': 0, 'active': 0, 'delayed': 0},
                'fileImport': {'queued': 0, 'processing': 0, 'retry': 0},
                'webhook': {'pending': 0, 'processing': 0, 'retry': 0},
                'legacyUpload': {'pending': 0, 'processing': 0},
                'n8nExecution': {'new': 0, 'running': 0, 'waiting': 0},
            },
            'redisDisposition': 'empty-not-restored',
            'recipientFingerprint': '4' * 64,
            'keyReferences': {name: 'escrow:test-' + str(i)
                              for i, name in enumerate(SECRETS)},
            'exportMethods': {'neo4j': 'offline-native-dump',
                'postgres': 'pg-dump-custom', 'objects': 's3-objects-and-metadata',
                'n8n': 'stopped-complete-state', 'api': 'stopped-complete-state'},
            'files': files,
        }
        self.save()

    def save(self):
        (self.root / 'export-checkpoint.json').write_text(json.dumps(self.manifest))

    def module(self):
        self.assertTrue(MODULE.is_file(), 'read-only multi-store checkpoint validator is absent')
        spec = importlib.util.spec_from_file_location('checkpoint', MODULE)
        module = importlib.util.module_from_spec(spec)
        sys.path.insert(0, str(MODULE.parent))
        self.addCleanup(lambda: sys.path.remove(str(MODULE.parent)))
        spec.loader.exec_module(module)
        return module

    def test_aggregate_queue_zeroes_cannot_hide_unexamined_consumers(self):
        module = self.module()
        # Legacy six counters cannot distinguish webhook/import/preview/n8n work.
        self.manifest['queues'] = {name: 0 for name in (
            'redisPending', 'redisActive', 'redisScheduled',
            'postgresPending', 'postgresActive', 'postgresRetry')}
        self.save()
        with self.assertRaises(module.CheckpointError):
            module.validate(self.root, REVISION, '4' * 64)

    def test_every_queue_category_is_required_and_zero_typed(self):
        module = self.module()
        original = copy.deepcopy(self.manifest)
        for group, counters in original['queues'].items():
            with self.subTest(group=group, case='absent'):
                self.manifest = copy.deepcopy(original)
                del self.manifest['queues'][group]
                self.save()
                with self.assertRaises(module.CheckpointError):
                    module.validate(self.root, REVISION, '4' * 64)
            for counter in counters:
                for bad in (1, -1, False, '0', None):
                    with self.subTest(group=group, counter=counter, bad=bad):
                        self.manifest = copy.deepcopy(original)
                        self.manifest['queues'][group][counter] = bad
                        self.save()
                        with self.assertRaises(module.CheckpointError):
                            module.validate(self.root, REVISION, '4' * 64)
        self.manifest = copy.deepcopy(original)
        self.manifest['schemaVersion'] = 1
        self.save()
        with self.assertRaises(module.CheckpointError):
            module.validate(self.root, REVISION, '4' * 64)

    def test_complete_tree_allows_empty_regular_files(self):
        module = self.module()
        (self.root / 'api' / 'empty.lock').touch()
        self.manifest['files']['api/empty.lock'] = {
            'bytes': 0, 'sha256': hashlib.sha256(b'').hexdigest()}
        self.save()
        self.assertEqual(module.validate(self.root, REVISION, '4' * 64)['filesVerified'], 6)

    def test_typed_manifest_rejections(self):
        module = self.module()
        original = copy.deepcopy(self.manifest)
        cases = [
            lambda d: d.update(schemaVersion=True),
            lambda d: d.update(sourceProject=d['destinationProject']),
            lambda d: d['queues']['fileImport'].update(processing=1),
            lambda d: d['queues']['previewRequest'].update(delayed=False),
            lambda d: d['images'].update(n8n='n8nio/n8n:2.4.8'),
            lambda d: d['keyReferences'].pop('N8N_ENCRYPTION_KEY'),
            lambda d: d['stoppedWriters'].remove('speckle-fileimport-service'),
            lambda d: d.update(recipientFingerprint='5' * 64),
            lambda d: d.update(sourceRevision='b' * 40),
            lambda d: d.update(redisDisposition='replay'),
            lambda d: d['files']['api/state.bin'].update(bytes=True),
            lambda d: d['files'].pop('objects/object.bin'),
            lambda d: d['files'].update({'api/../outside': {'bytes': 1, 'sha256': '0' * 64}}),
            lambda d: d.update(secret='synthetic-should-not-echo'),
        ]
        for i, mutate in enumerate(cases):
            with self.subTest(case=i):
                self.manifest = copy.deepcopy(original)
                mutate(self.manifest)
                self.save()
                with self.assertRaisesRegex(module.CheckpointError, '^multi-store checkpoint rejected$'):
                    module.validate(self.root, REVISION, '4' * 64)

    def test_corruption_and_unlisted_files_rejected(self):
        module = self.module()
        target = self.root / 'objects' / 'object.bin'
        original = target.read_bytes()
        target.write_bytes(b'x' * len(original))
        with self.assertRaises(module.CheckpointError):
            module.validate(self.root, REVISION, '4' * 64)
        target.write_bytes(original)
        (self.root / 'export-in-progress.json').write_text('{}')
        with self.assertRaises(module.CheckpointError):
            module.validate(self.root, REVISION, '4' * 64)

    def test_duplicate_and_nonfinite_json_rejected(self):
        module = self.module()
        for raw in ['{"schemaVersion":1,"schemaVersion":1}', '{"schemaVersion":NaN}']:
            (self.root / 'export-checkpoint.json').write_text(raw)
            with self.assertRaises(module.CheckpointError):
                module.validate(self.root, REVISION, '4' * 64)

    def test_cli_argument_errors_never_echo_values(self):
        self.module()
        for args in (['--export-directory', str(self.root), '--revision', REVISION,
                      '--recipient-fingerprint', '4' * 64,
                      '--unexpected', 'synthetic-secret-do-not-echo'],
                     ['--unexpected', 'synthetic-secret-do-not-echo'],
                     ['--export-directory'], [], ['--revision', 'synthetic-secret']):
            proc = subprocess.run([sys.executable, '-B', str(MODULE), *args],
                                  capture_output=True, text=True)
            self.assertEqual(proc.returncode, 1)
            self.assertEqual(json.loads(proc.stdout), {
                'status': 'REJECTED', 'reason': 'multi-store checkpoint rejected'})
            self.assertEqual(proc.stderr, '')

    def test_cli_rejection_does_not_echo_paths_or_content(self):
        module = self.module()
        self.manifest['queues']['webhook']['processing'] = 1
        self.save()
        proc = subprocess.run([sys.executable, '-B', str(MODULE),
            '--export-directory', str(self.root), '--revision', REVISION,
            '--recipient-fingerprint', '4' * 64], capture_output=True, text=True)
        self.assertEqual(proc.returncode, 1)
        self.assertEqual(json.loads(proc.stdout), {
            'status': 'REJECTED', 'reason': 'multi-store checkpoint rejected'})
        self.assertEqual(proc.stderr, '')

    @unittest.skipUnless(os.name == 'nt', 'NTFS stream regression')
    def test_ntfs_named_streams_rejected_on_file_marker_and_directory(self):
        module = self.module()
        for path in (self.root / 'api' / 'state.bin',
                     self.root / 'export-checkpoint.json', self.root / 'api', self.root):
            with self.subTest(kind=path.name):
                stream = str(path) + ':unlisted'
                try:
                    with open(stream, 'wb') as output:
                        output.write(b'synthetic-hidden-content')
                    with self.assertRaises(module.CheckpointError):
                        module.validate(self.root, REVISION, '4' * 64)
                finally:
                    os.remove(stream)

    def test_hardlinked_export_rejected(self):
        module = self.module()
        os.link(self.root / 'api' / 'state.bin', self.root.parent / 'alias.bin')
        with self.assertRaises(module.CheckpointError):
            module.validate(self.root, REVISION, '4' * 64)

    def test_junction_or_directory_link_rejected(self):
        module = self.module()
        external = self.root.parent / 'external'
        external.mkdir()
        link = self.root / 'api' / 'escape'
        if os.name == 'nt':
            proc = subprocess.run(['cmd.exe', '/c', 'mklink', '/J', str(link), str(external)],
                                  capture_output=True)
            self.assertEqual(proc.returncode, 0)
            self.addCleanup(lambda: os.rmdir(link))
        else:
            link.symlink_to(external, target_is_directory=True)
        with self.assertRaises(module.CheckpointError):
            module.validate(self.root, REVISION, '4' * 64)

    def test_streaming_limits_fail_before_oversize_read(self):
        module = self.module()
        module.MAX_BYTES = 1
        with self.assertRaises(module.CheckpointError):
            module.validate(self.root, REVISION, '4' * 64)
        module.MAX_BYTES = 64 * 1024 ** 3
        module.MAX_ENTRIES = 4
        with self.assertRaises(module.CheckpointError):
            module.validate(self.root, REVISION, '4' * 64)

    def test_cli_success_is_explicitly_offline(self):
        self.module()
        proc = subprocess.run([sys.executable, '-B', str(MODULE),
            '--export-directory', str(self.root), '--revision', REVISION,
            '--recipient-fingerprint', '4' * 64], capture_output=True, text=True)
        self.assertEqual(proc.returncode, 0)
        self.assertIs(json.loads(proc.stdout)['nativeRecoveryProven'], False)
        self.assertEqual(proc.stderr, '')

    def test_validated_declarations_do_not_claim_recovery(self):
        module = self.module()
        before = {p.relative_to(self.root).as_posix(): p.read_bytes()
                  for p in self.root.rglob('*') if p.is_file()}
        result = module.validate(self.root, REVISION, '4' * 64)
        self.assertEqual(result['status'], 'OFFLINE_CHECKPOINT_VALIDATED_NOT_RECOVERY')
        self.assertIs(result['nativeRecoveryProven'], False)
        self.assertIs(result['offMachineRestoreProven'], False)
        self.assertIs(result['releaseAccepted'], False)
        self.assertEqual(result['filesVerified'], 5)
        after = {p.relative_to(self.root).as_posix(): p.read_bytes()
                 for p in self.root.rglob('*') if p.is_file()}
        self.assertEqual(before, after)


if __name__ == '__main__':
    unittest.main()
