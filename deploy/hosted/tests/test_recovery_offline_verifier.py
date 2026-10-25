"""Strict offline suite selector; no Docker/native test discovery."""
import importlib.util
from pathlib import Path
import subprocess
import sys
import unittest

MODULE = Path(__file__).resolve().parents[1] / 'verify_multistore_offline.py'


class OfflineVerifierTests(unittest.TestCase):
    def module(self):
        self.assertTrue(MODULE.is_file(), 'repeatable strict offline verifier is absent')
        spec = importlib.util.spec_from_file_location('offline_verifier', MODULE)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module

    def test_explicit_suite_allowlist_has_no_native_or_legacy_archive_suite(self):
        m = self.module()
        expected = (
            'test_recovery_checkpoint.py', 'test_recovery_postgres.py',
            'test_recovery_package.py', 'test_recovery_execution.py',
            'test_recovery_runner.py', 'test_recovery_probe.py',
            'test_recovery_snapshot.py', 'test_recovery_diagnostic.py',
            'test_recovery_cleanup.py', 'test_recovery_sequence.py',
            'test_recovery_n8n.py', 'test_recovery_objects.py',
            'test_recovery_queues.py', 'test_recovery_pg_init.py',
            'test_recovery_transport.py', 'test_recovery_multistore_offline.py',
            'test_recovery_offline_verifier.py')
        self.assertEqual(m.SUITES, expected)
        calls = []
        def run(argv, **kwargs):
            calls.append((argv, kwargs))
            return subprocess.CompletedProcess(argv, 0, '',
                'Required tests: discovered=2, ran=2, failures=0, errors=0, skipped=0\n')
        report = m.verify(run=run)
        self.assertEqual(len(calls), len(expected))
        self.assertEqual(report['totalTestsRun'], 2 * len(expected))
        self.assertIs(report['passed'], True)
        self.assertIs(report['nativeRecoveryProven'], False)
        self.assertIs(report['releaseAccepted'], False)
        for (argv, options), suite in zip(calls, expected):
            self.assertEqual(argv, [sys.executable, '-B', str(MODULE.parent / 'tests' / 'run_required.py'), suite])
            self.assertIs(options['shell'], False)
            self.assertGreater(options['timeout'], 0)
            self.assertLessEqual(options['timeout'], 90)
            self.assertNotIn('input', options)

    def test_skips_zero_mismatch_nonzero_and_ambiguous_counts_fail_closed(self):
        m = self.module()
        for code, summary in (
            (0,'discovered=0, ran=0, failures=0, errors=0, skipped=0'),
            (0,'discovered=2, ran=1, failures=0, errors=0, skipped=0'),
            (0,'discovered=2, ran=2, failures=0, errors=0, skipped=1'),
            (0,'discovered=2, ran=2, failures=1, errors=0, skipped=0'),
            (0,'discovered=2, ran=2, failures=0, errors=1, skipped=0'),
            (1,'discovered=2, ran=2, failures=0, errors=0, skipped=0'),
            (0,'malformed'),
            (0,('discovered=2, ran=2, failures=0, errors=0, skipped=0\nRequired tests: ')*2),
        ):
            with self.subTest(code=code, summary=summary):
                def run(argv, **kwargs):
                    return subprocess.CompletedProcess(argv, code, 'PRIVATE', 'Required tests: '+summary+'\n')
                report = m.verify(run=run)
                self.assertIs(report['passed'], False)
                self.assertNotIn('PRIVATE', str(report))

    def test_subprocess_failure_and_global_deadline_are_bounded(self):
        m = self.module()
        calls = []
        def failed(argv, **kwargs):
            calls.append(argv)
            raise subprocess.TimeoutExpired(argv, 0.1, output='PRIVATE')
        report = m.verify(run=failed)
        self.assertIs(report['passed'], False)
        self.assertEqual(len(calls), len(m.SUITES))
        self.assertNotIn('PRIVATE', str(report))
        times = iter([0, 601])
        calls.clear()
        report = m.verify(run=failed, clock=lambda:next(times))
        self.assertIs(report['passed'], False)
        self.assertEqual(calls, [])
        self.assertTrue(report['deadlineExceeded'])


if __name__ == '__main__':
    unittest.main()
