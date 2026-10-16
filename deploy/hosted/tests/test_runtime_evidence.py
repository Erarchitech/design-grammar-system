"""Offline evidence validation is not a runtime re-execution."""
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest

HOSTED = Path(__file__).resolve().parents[1]
EVIDENCE = HOSTED / 'runtime-evidence/2dedbfb-owner-report.json'
ZIP = Path('C:/Users/Admin/Downloads/DG-candidate-test-2dedbfb-DESKTOP-OS4Q8CP.zip')


def module():
    path = HOSTED / 'accept_runtime_evidence.py'
    if not path.is_file():
        raise AssertionError('missing owner-report identity validator')
    spec = importlib.util.spec_from_file_location('accept_runtime_evidence', path)
    value = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(value)
    return value


class RuntimeEvidenceTests(unittest.TestCase):
    def test_rejects_nonboolean_or_missing_checks_and_failed_exit(self):
        validator = module()
        original = json.loads(EVIDENCE.read_text())
        variants = []
        for key, replacement in [('packageHash', 1), ('n8nNamedRead', 'true'),
                                 ('cleanupVerified', False)]:
            value = json.loads(json.dumps(original))
            value['checks'][key] = replacement
            variants.append(value)
        value = json.loads(json.dumps(original))
        value['checks']['dataService']['ingest_inserted'] = True
        variants.append(value)
        variants.append({**original, 'extra': 'forbidden'})
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / 'report.json'
            for value in variants:
                path.write_text(json.dumps(value))
                with self.subTest(value=value), self.assertRaises(ValueError):
                    validator.accept(path, ZIP, exit_code=0)
            path.write_text(json.dumps(original))
            for code in (1, None, False):
                with self.subTest(exit=code), self.assertRaises(ValueError):
                    validator.accept(path, ZIP, exit_code=code)

    def test_rejects_wrong_package_without_runtime(self):
        validator = module()
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / 'wrong.zip'
            path.write_bytes(b'not the issued ZIP')
            with self.assertRaises(ValueError):
                validator.accept(EVIDENCE, path, exit_code=0)

    def test_exact_owner_report_and_zip_validate_without_runtime(self):
        validator = module()
        receipt = validator.accept(EVIDENCE, ZIP, exit_code=0)
        self.assertEqual(receipt['status'], 'OWNER_REPORTED_CAPABILITY_PASS')
        self.assertFalse(receipt['independentlyObservedRuntime'])
        self.assertFalse(receipt['releaseAccepted'])
        self.assertEqual(receipt['frameworkRevision'], '2dedbfb3e138c2b437e781696197105dca93342a')


if __name__ == '__main__':
    unittest.main()
