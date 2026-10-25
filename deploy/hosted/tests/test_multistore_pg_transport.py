"""Strict OFFLINE tests for the bounded PostgreSQL output sink (reference logic).

Real synthetic child processes only. No PostgreSQL, Docker, network or keys.
Passing here does NOT qualify a native/Linux supervisor or remote cleanup.
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

MODULE = Path(__file__).resolve().parents[1] / 'recovery-test' / 'multistore_pg_transport.py'
SNAPSHOT = 4 * 1024 * 1024


def load():
    assert MODULE.is_file(), 'bounded PostgreSQL transport module is missing'
    spec = importlib.util.spec_from_file_location('multistore_pg_transport', MODULE)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class TransportTests(unittest.TestCase):
    def setUp(self):
        self.t = load()
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.parent = Path(self.temp.name)
        os.chmod(self.parent, 0o700)

    def run_child(self, source, limit=SNAPSHOT, seconds=5):
        env = {k: os.environ[k] for k in ('SystemRoot', 'WINDIR') if k in os.environ}
        result = self.t.bounded_child(self.parent, 'new', [sys.executable, '-I', '-B', '-c', source],
                                      env, limit, seconds)
        if result['status'] != 'REJECTED':
            self.assertLessEqual(result['peakFileBytes'], limit)
            self.assertTrue(result['directChildReaped'])
            self.assertTrue(result['readerJoined'])
        return result

    def test_exact_limit_accepted_and_hash_matches(self):
        r = self.run_child('import os; b=b"x"*65536\nfor _ in range(64): os.write(1,b)')
        self.assertEqual(r['status'], 'COMPLETE')
        raw = (self.parent / 'new/result.bin').read_bytes()
        self.assertEqual(len(raw), SNAPSHOT)
        self.assertEqual(hashlib.sha256(raw).hexdigest(), r['sha256'])

    def test_one_byte_over_limit_never_written_or_published(self):
        r = self.run_child('import os; b=b"x"*65536\nfor _ in range(64): os.write(1,b)\nos.write(1,b"!")')
        self.assertEqual(r['status'], 'OVERFLOW')
        self.assertFalse((self.parent / 'new').exists())

    def test_unbounded_producer_is_cut_off(self):
        r = self.run_child('import os\nwhile True: os.write(1,b"x"*65536)')
        self.assertEqual(r['status'], 'OVERFLOW')
        self.assertFalse((self.parent / 'new').exists())

    def test_silent_child_times_out(self):
        r = self.run_child('import time; time.sleep(30)', seconds=.2)
        self.assertEqual(r['status'], 'TIMEOUT')
        self.assertFalse((self.parent / 'new').exists())

    def test_stdout_closed_but_child_alive_times_out(self):
        r = self.run_child('import os,time; os.close(1); time.sleep(30)', seconds=.2)
        self.assertEqual(r['status'], 'TIMEOUT')

    def test_nonzero_exit_leaks_neither_stdout_nor_stderr(self):
        r = self.run_child('import os; os.write(1,b"private-output"); os.write(2,b"SECRET_SENTINEL"); raise SystemExit(7)')
        self.assertEqual(r['status'], 'CHILD_FAILED')
        self.assertNotIn('SECRET_SENTINEL', json.dumps(r))
        self.assertNotIn('private-output', json.dumps(r))
        self.assertFalse((self.parent / 'new').exists())

    def test_empty_output_rejected(self):
        self.assertEqual(self.run_child('pass')['status'], 'EMPTY')

    def test_stderr_flood_does_not_deadlock(self):
        r = self.run_child('import os\nfor _ in range(128): os.write(2,b"s"*65536)\nos.write(1,b"ok")')
        self.assertEqual(r['status'], 'COMPLETE')
        self.assertEqual(r['writtenBytes'], 2)

    def test_existing_directory_is_not_launched_into_or_clobbered(self):
        run = self.parent / 'new'
        run.mkdir()
        (run / 'marker').write_bytes(b'keep')
        launched = self.parent / 'launched'
        source = f'open({str(launched)!r},"wb").write(b"x")'
        r = self.t.bounded_child(self.parent, 'new', [sys.executable, '-I', '-c', source], {}, 10, 1)
        self.assertEqual(r['status'], 'COLLISION')
        self.assertFalse(r['directChildReaped'])
        self.assertFalse(launched.exists())
        self.assertEqual((run / 'marker').read_bytes(), b'keep')

    def test_invalid_time_name_and_parent_arguments_are_rejected_not_raised(self):
        launched = self.parent / 'launched'
        argv = [sys.executable, '-I', '-c', f'open({str(launched)!r},"wb").write(b"x")']
        cases = [
            dict(seconds=None), dict(seconds='5'), dict(seconds=True), dict(seconds=0),
            dict(seconds=-1), dict(seconds=181), dict(seconds=float('nan')),
            dict(name='..'), dict(name='a/b'), dict(name=''), dict(name=None),
            dict(filename='..'), dict(filename='a/b'), dict(filename='.part'), dict(filename=''),
            dict(parent=self.parent / 'does-not-exist'),
        ]
        for case in cases:
            with self.subTest(case=str(case)):
                launched.unlink(missing_ok=True)
                (self.parent / 'new').exists() and self.fail('previous case left a run directory')
                r = self.t.bounded_child(case.get('parent', self.parent), case.get('name', 'new'), argv, {},
                                         10, case.get('seconds', 1), **({'filename': case['filename']} if 'filename' in case else {}))
                self.assertEqual(r['status'], 'REJECTED')
                self.assertFalse(launched.exists())
                self.assertFalse((self.parent / 'new').exists())

    def test_chunk_crossing_the_budget_boundary_is_never_written(self):
        r = self.run_child('import os,time; os.write(1,b"a"*98); time.sleep(.3); os.write(1,b"b"*5)', limit=100)
        self.assertEqual(r['status'], 'OVERFLOW')
        self.assertLessEqual(r['peakFileBytes'], 100)
        self.assertFalse((self.parent / 'new').exists())

    def test_publication_failure_reports_match_disk(self):
        from unittest import mock
        source = 'import os; os.write(1,b"payload")'
        real_unlink = Path.unlink

        def failing_unlink(path, *args, **kwargs):
            if path.name == '.part':
                raise OSError('synthetic unlink failure after link')
            return real_unlink(path, *args, **kwargs)

        with mock.patch.object(Path, 'unlink', failing_unlink):
            r = self.run_child(source)
        self.assertEqual(r['status'], 'COMPLETE')  # published bytes are valid; leftover partial is harmless
        self.assertEqual((self.parent / 'new/result.bin').read_bytes(), b'payload')

    def test_unsupported_hardlink_rejects_without_publishing(self):
        from unittest import mock
        with mock.patch.object(self.t.os, 'link', side_effect=OSError('synthetic no hardlinks')):
            r = self.run_child('import os; os.write(1,b"payload")')
        self.assertEqual(r['status'], 'REJECTED')
        self.assertFalse((self.parent / 'new').exists())

    def test_final_collision_is_not_replaced(self):
        final = self.parent / 'new/result.bin'
        r = self.run_child(f'import os; open({str(final)!r},"xb").write(b"keep"); os.write(1,b"payload")')
        self.assertEqual(r['status'], 'COLLISION')
        self.assertEqual(final.read_bytes(), b'keep')
        self.assertFalse((self.parent / 'new/.part').exists())

    def test_budget_is_mandatory_and_strictly_validated(self):
        """No default dump budget exists: absent/invalid values fail before any launch."""
        marker = self.parent / 'launched'
        source = f'open({str(marker)!r},"wb").write(b"x")'
        for bad in (None, True, False, 0, -1, 1.5, '64', self.t.HARD_CEILING + 1):
            with self.subTest(limit=bad):
                r = self.t.bounded_child(self.parent, 'new', [sys.executable, '-I', '-c', source], {}, bad, 1)
                self.assertEqual(r['status'], 'REJECTED')
                self.assertFalse(marker.exists())
                self.assertFalse((self.parent / 'new').exists())
        self.assertFalse(hasattr(self.t, 'DUMP_LIMIT'))
        self.assertFalse(hasattr(self.t, 'SNAPSHOT_LIMIT'))

    def test_budget_parameter_is_not_defaulted(self):
        import inspect
        parameters = inspect.signature(self.t.bounded_child).parameters
        self.assertIs(parameters['limit'].default, inspect.Parameter.empty)

    def test_fixed_argv_env_contract(self):
        for mode in ('snapshot', 'dump'):
            name, argv, env = self.t.pg_spec(mode, 'synthetic-not-owner-secret')
            self.assertIn('--dbname=speckle', argv)
            self.assertNotIn('synthetic-not-owner-secret', ' '.join(argv))
            self.assertFalse(any(a.startswith('--output') for a in argv))
            if mode == 'dump':
                self.assertFalse(any(a.startswith('--file') for a in argv))
                self.assertFalse(any(a.startswith(('--jobs', '-j')) for a in argv))
            self.assertEqual(env['PGUSER'], 'speckle')
            self.assertEqual(env['PGDATABASE'], 'speckle')
            self.assertEqual(env['PGHOST'], 'speckle-postgres')
            for forbidden in ('PGSERVICE', 'PGOPTIONS', 'PGPASSFILE'):
                self.assertNotIn(forbidden, env)
        with self.assertRaises(KeyError):
            self.t.pg_spec('arbitrary', 'x')
        for bad in (None, '', 'a\x00b', 7):
            with self.assertRaises(ValueError):
                self.t.pg_spec('dump', bad)

    def test_regression_direct_file_output_is_not_bounded_by_capture(self):
        """Documents the old psql --output / pg_dump --file boundary: stdout capture is irrelevant."""
        target = self.parent / 'old-output'
        source = f'open({str(target)!r},"xb").write(b"x"*4194305)'
        completed = subprocess.run([sys.executable, '-I', '-B', '-c', source],
                                   stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=10)
        self.assertEqual(completed.returncode, 0)
        self.assertEqual(target.stat().st_size, 4194305)


if __name__ == '__main__':
    unittest.main()
