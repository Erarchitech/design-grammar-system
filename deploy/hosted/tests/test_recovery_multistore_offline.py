"""Composed offline recovery exercise, NOT native recovery/HOST-04.

Real synthetic SQLite DB and filesystem copies; injected S3-shaped provider.
No Neo4j/PG/Redis/n8n processes, encryption, networking or owner data. Unsupported
sequence steps are explicitly recorded as synthetic, never native attestation.
"""
import copy
from contextlib import closing
import hashlib
import importlib
import json
import os
from pathlib import Path
import sqlite3
import sys
import tempfile
import unittest

HOSTED = Path(__file__).resolve().parents[1]
SCRATCH = 'C:/Users/Admin/AppData/Local/hermes/cache/scratch'


class MultiStoreOfflineTests(unittest.TestCase):
    def setUp(self):
        sys.path.insert(0, str(HOSTED))
        self.addCleanup(lambda: sys.path.remove(str(HOSTED)))
        self.sequence = importlib.import_module('recovery_sequence')
        self.n8n = importlib.import_module('recovery_n8n')
        self.objects = importlib.import_module('recovery_objects')
        self.queues = importlib.import_module('recovery_queues')
        self.pg = importlib.import_module('recovery_pg_init')
        # Reuse the explicit synthetic provider; it is not a native SDK.
        self.provider_type = importlib.import_module('test_recovery_objects').SyntheticS3
        self.temp = tempfile.TemporaryDirectory(dir=SCRATCH)
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.source = self.root / 'source'
        self.source.mkdir()
        (self.source / 'config').write_text(json.dumps({'encryptionKey':'synthetic-only'}))
        with closing(sqlite3.connect(self.source / 'database.sqlite')) as connection:
            with connection:
                connection.execute('CREATE TABLE synthetic_workflow (id TEXT PRIMARY KEY, active INTEGER)')
                connection.execute('INSERT INTO synthetic_workflow VALUES (?, ?)', ('synthetic-workflow', 0))
        (self.source / 'binaryData').mkdir()
        (self.source / 'binaryData' / 'blob').write_bytes(b'\x00\xffsynthetic-model')
        self.object_source = self.provider_type()
        self.binding = {'images':{role:'sha256:'+str(i)*64 for i,role in enumerate((
            'speckle-server','speckle-preview-service','speckle-webhook-service',
            'speckle-fileimport-service','n8n','postgres','valkey'),1)},
                        'probeSha256':'3'*64,'schemaSha256':'4'*64}

    def samples(self):
        first = {'binding':copy.deepcopy(self.binding),'sequence':1,
                 'groups':{k:{c:0 for c in counters} for k,counters in self.queues.QUEUES.items()},
                 'backendsExamined':['n8n-sqlite','postgres','redis'],'unknownQueues':[]}
        second = copy.deepcopy(first)
        second['sequence'] = 2
        return first, second

    def assert_sqlite(self, folder):
        # Read ONLY the restored synthetic DB, never live n8n or an owner's DB.
        uri = (folder / 'database.sqlite').as_uri() + '?mode=ro&immutable=1'
        with closing(sqlite3.connect(uri, uri=True)) as connection:
            self.assertEqual(connection.execute('PRAGMA integrity_check').fetchone(), ('ok',))
            self.assertEqual(connection.execute('SELECT * FROM synthetic_workflow').fetchall(),
                             [('synthetic-workflow',0)])
        self.assertEqual((folder / 'config').read_bytes(), (self.source / 'config').read_bytes())
        self.assertEqual((folder / 'binaryData' / 'blob').read_bytes(), b'\x00\xffsynthetic-model')

    def test_composed_roundtrip_preserves_sqlite_objects_and_order_without_native_claim(self):
        # Test RED initially requires the bundle verifier used by the runner.
        bundle_module = importlib.util.find_spec('recovery_bundle')
        self.assertIsNotNone(bundle_module, 'cross-adapter bundle verifier is absent')
        bundle = importlib.import_module('recovery_bundle')
        package = self.root / 'package'
        package.mkdir()
        receipts, synthetic_steps = {}, []
        def synthetic(step):
            synthetic_steps.append(step)
            return True
        adapters = dict.fromkeys(self.sequence.BACKUP, synthetic)
        def stable(_):
            self.queues.admit_stable_empty(*self.samples(), expected_binding=self.binding)
            return True
        def export_objects(_):
            receipts['objects'] = self.objects.export_objects(self.object_source, package / 'objects', attest=lambda _:True)
            return True
        def export_n8n(_):
            self.n8n.export_state(self.source, package / 'n8n', version='2.4.8', attest=lambda _:True)
            receipts['n8n'] = hashlib.sha256((package / 'n8n' / 'state-manifest.json').read_bytes()).hexdigest()
            return True
        def verify(_):
            receipts['verified'] = bundle.verify_bundle(package,
                expected_objects_sha256=receipts['objects']['manifestSha256'],
                expected_n8n_sha256=receipts['n8n'], version='2.4.8')
            return True
        adapters.update({'stable-empty-queues':stable,'export-objects':export_objects,
                         'export-n8n':export_n8n,'verify-inventory':verify})
        backup = self.sequence.run_sequence('backup', adapters)
        self.assertIs(backup['nativeRecoveryProven'], False)
        self.assertIn('encrypt', synthetic_steps)
        self.assertIn('export-postgres', synthetic_steps)
        self.assertIs(receipts['verified']['nativeRecoveryProven'], False)
        restored = self.root / 'restored'
        target = self.provider_type()
        target.objects = {}
        restored_steps = []
        def restore_synthetic(step):
            restored_steps.append(step)
            return True
        adapters = dict.fromkeys(self.sequence.RESTORE, restore_synthetic)
        def init(_):
            model = self.pg.restore_model(project='dg-recovery-'+'2'*32, image='postgres@sha256:'+'3'*64)
            self.assertNotIn('ports', model['services']['speckle-postgres'])
            return True
        def restore_objects(_):
            self.objects.restore_objects(package / 'objects', target,
                expected_manifest_sha256=receipts['objects']['manifestSha256'], attest=lambda _:True)
            return True
        def restore_n8n(_):
            self.n8n.restore_state(package / 'n8n', restored,
                expected_manifest_sha256=receipts['n8n'], version='2.4.8', attest=lambda _:True)
            return True
        def semantic(_):
            self.assert_sqlite(restored)
            self.assertEqual(target.objects, self.object_source.objects)
            return True
        adapters.update({'verify-inventory':verify,'initialize-postgres':init,
                         'restore-objects':restore_objects,'restore-n8n':restore_n8n,
                         'semantic-verification':semantic})
        result = self.sequence.run_sequence('restore', adapters)
        self.assertIs(result['releaseAccepted'], False)
        self.assertIn('authenticate-decrypt', restored_steps)
        self.assertIn('restore-postgres', restored_steps)
        self.assert_sqlite(self.source)

    def test_bundle_corruption_blocks_dispatch_before_any_restore_write(self):
        bundle = importlib.import_module('recovery_bundle')
        for scenario in ('objects','n8n','extra','missing-key','wrong-hash'):
            with self.subTest(scenario=scenario):
                package = self.root / ('package-' + scenario)
                package.mkdir()
                receipt = self.objects.export_objects(self.object_source, package / 'objects', attest=lambda _:True)
                self.n8n.export_state(self.source, package / 'n8n', version='2.4.8', attest=lambda _:True)
                state_hash = hashlib.sha256((package / 'n8n' / 'state-manifest.json').read_bytes()).hexdigest()
                if scenario == 'objects':
                    (package / 'objects' / '0000.object').write_bytes(b'corrupted')
                elif scenario == 'n8n':
                    (package / 'n8n' / 'tree' / 'binaryData' / 'blob').write_bytes(b'corrupted')
                elif scenario == 'extra':
                    (package / 'unexpected').write_bytes(b'extra')
                elif scenario == 'missing-key':
                    (package / 'n8n' / 'tree' / 'config').write_text('{}')
                else:
                    state_hash = '0'*64
                calls = []
                def synthetic(step):
                    calls.append(step)
                    return True
                adapters = dict.fromkeys(self.sequence.RESTORE, synthetic)
                def verify(step):
                    calls.append(step)
                    bundle.verify_bundle(package, expected_objects_sha256=receipt['manifestSha256'],
                                         expected_n8n_sha256=state_hash, version='2.4.8')
                    return True
                adapters['verify-inventory'] = verify
                with self.assertRaises(self.sequence.SequenceError):
                    self.sequence.run_sequence('restore', adapters)
                self.assertEqual(calls, ['scope','identity','authenticate-decrypt','verify-inventory'])
                self.assert_sqlite(self.source)


if __name__ == '__main__':
    unittest.main()
