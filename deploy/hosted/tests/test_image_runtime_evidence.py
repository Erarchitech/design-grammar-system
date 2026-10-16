"""Evidence reconciliation only: no Docker or target runtime invocation."""
import copy
import importlib.util
import json
from pathlib import Path
import sys
import tempfile
import unittest

HERE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(HERE))
MODULE = HERE / 'reconcile_image_runtime.py'
REPORT = HERE / 'image-runtime/evidence/c82b92b-v2-owner-smoke-report.json'
ARCHIVE = Path('C:/Users/Admin/Downloads/DG-image-runtime-c82b92b-v2.zip')


class EvidenceTests(unittest.TestCase):
    def load_module(self):
        self.assertTrue(MODULE.is_file(), 'four-image evidence reconciler missing')
        spec = importlib.util.spec_from_file_location('reconcile_image_runtime', MODULE)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module

    def test_unknown_exit_preserves_report_checks_not_full_acceptance(self):
        module = self.load_module()
        result = module.reconcile(REPORT, ARCHIVE, exit_code=None)
        self.assertEqual(result['status'], 'OWNER_REPORTED_SMOKE_COMPLETE_EXIT_UNKNOWN')
        self.assertIsNone(result['processExitCode'])
        self.assertFalse(result['evidenceComplete'])
        self.assertTrue(result['reportChecksMatched'])
        self.assertFalse(result['releaseAccepted'])
        self.assertFalse(result['independentlyObservedRuntime'])
        self.assertIsNone(result['runtimeTimestamp'])

    def test_typed_or_changed_report_rejected(self):
        module = self.load_module()
        original = json.loads(REPORT.read_bytes())
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / 'report.json'
            for section, key, value in [('checks', 'cleanupVerified', 1),
                    ('checks', 'readiness', False), (None, 'schemaVersion', True),
                    (None, 'releaseAccepted', True), (None, 'buildReportSha256', 'f'*64),
                    (None, 'unexpected', 'not-admitted')]:
                bad = copy.deepcopy(original)
                (bad[section] if section else bad)[key] = value
                path.write_text(json.dumps(bad))
                with self.subTest(key=key), self.assertRaises(ValueError):
                    module.reconcile(path, ARCHIVE, exit_code=None)
            bad = copy.deepcopy(original)
            bad['images']['neo4j']['imageId'] = 'sha256:'+'a'*64
            path.write_text(json.dumps(bad))
            with self.assertRaises(ValueError):
                module.reconcile(path, ARCHIVE, exit_code=None)

    def test_cli_requires_exit_disposition_and_preserves_unknown(self):
        import subprocess
        command = [sys.executable, str(MODULE), '--report', str(REPORT), '--zip', str(ARCHIVE)]
        result = subprocess.run(command + ['--exit-unknown'], capture_output=True, text=True, timeout=30)
        self.assertEqual(result.returncode, 2)
        self.assertIsNone(json.loads(result.stdout)['processExitCode'])
        result = subprocess.run(command, capture_output=True, text=True, timeout=30)
        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(result.stdout, '')

    def test_exit_and_archive_never_inferred(self):
        module = self.load_module()
        self.assertTrue(module.reconcile(REPORT, ARCHIVE, exit_code=0)['evidenceComplete'])
        for value in (True, '0', 1, -1):
            with self.subTest(value=value), self.assertRaises(ValueError):
                module.reconcile(REPORT, ARCHIVE, exit_code=value)
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / 'wrong.zip'
            path.write_bytes(b'not the issued ZIP')
            with self.assertRaises(ValueError):
                module.reconcile(REPORT, path, exit_code=None)


if __name__ == '__main__':
    unittest.main()
