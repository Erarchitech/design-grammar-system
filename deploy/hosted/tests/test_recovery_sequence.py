"""Offline orchestration contract. No service/daemon operations in this suite."""
import importlib.util
import sys
from pathlib import Path
import unittest

MODULE = Path(__file__).resolve().parents[1] / 'recovery_sequence.py'


class RecoverySequenceTests(unittest.TestCase):
    def module(self):
        self.assertTrue(MODULE.is_file(), 'coordinated multi-store sequence runner is absent')
        sys.path.insert(0, str(MODULE.parent))
        self.addCleanup(lambda: sys.path.remove(str(MODULE.parent)))
        spec = importlib.util.spec_from_file_location('sequence', MODULE)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module

    def test_prepare_has_no_operations_and_backup_requires_full_order(self):
        module = self.module()
        calls = []
        runner = module.Sequence('backup')
        self.assertEqual(calls, [])
        for step in ('scope', 'identity', 'block-producers', 'drain-with-consumers',
                     'stop-writers', 'stable-empty-queues', 'export-neo4j',
                     'export-postgres', 'export-objects', 'export-n8n', 'export-api',
                     'verify-inventory', 'encrypt', 'verify-ciphertext-transfer',
                     'verify-plaintext-cleanup'):
            self.assertEqual(runner.next_step, step)
            runner.run_next(lambda requested: calls.append(requested) or True)
        self.assertIsNone(runner.next_step)
        self.assertEqual(runner.report(), {
            'status': 'ADAPTER_SEQUENCE_COMPLETED_NOT_RECOVERY',
            'completedSteps': calls, 'failedStep': None,
            'nativeRecoveryProven': False, 'offMachineRestoreProven': False,
            'releaseAccepted': False})

    def test_restore_authentication_precedes_destination_and_apps(self):
        module = self.module()
        self.assertTrue(hasattr(module, 'RESTORE'), 'restore ordering contract is absent')
        runner = module.Sequence('restore')
        expected = ('scope', 'identity', 'authenticate-decrypt', 'verify-inventory',
                    'verify-key-custody', 'verify-empty-destination',
                    'initialize-postgres', 'restore-postgres', 'restore-neo4j',
                    'restore-objects', 'restore-n8n', 'restore-api',
                    'verify-empty-queues', 'start-isolated-read-only',
                    'semantic-verification', 'verify-plaintext-cleanup')
        for step in expected:
            self.assertEqual(runner.next_step, step)
            runner.run_next(lambda _: True)
        self.assertIsNone(runner.next_step)
        self.assertIs(runner.report()['releaseAccepted'], False)

    def test_each_failure_and_interruption_latches_and_sanitizes(self):
        module = self.module()
        for operation in ('backup', 'restore'):
            steps = module.BACKUP if operation == 'backup' else module.RESTORE
            for index, step in enumerate(steps):
                for bad in (False, None, 1, 'true', RuntimeError('synthetic-private'), KeyboardInterrupt()):
                    runner = module.Sequence(operation)
                    for _ in range(index):
                        runner.run_next(lambda _: True)
                    def fail(_):
                        if isinstance(bad, BaseException):
                            raise bad
                        return bad
                    error = KeyboardInterrupt if isinstance(bad, KeyboardInterrupt) else module.SequenceError
                    with self.assertRaises(error) as caught:
                        runner.run_next(fail)
                    self.assertNotIn('synthetic-private', str(caught.exception))
                    self.assertIsNone(runner.next_step)
                    with self.assertRaises(module.SequenceError):
                        runner.run_next(lambda _: self.fail('must not resume'))
                    self.assertEqual(runner.report()['failedStep'], step)
                    self.assertEqual(runner.report()['completedSteps'], list(steps[:index]))

    def test_reentrant_callback_cannot_skip_queue_or_duplicate_scope(self):
        module = self.module()
        runner = module.Sequence('backup')
        def reenter(_):
            runner.run_next(lambda _: True)
            return True
        with self.assertRaises(module.SequenceError):
            runner.run_next(reenter)
        self.assertEqual(runner.report()['completedSteps'], [])
        self.assertEqual(runner.report()['failedStep'], 'scope')

    def test_common_runner_preflights_all_adapters_before_first_call(self):
        module = self.module()
        self.assertTrue(hasattr(module, 'run_sequence'), 'common adapter runner is absent')
        for operation in ('backup', 'restore'):
            steps = module.BACKUP if operation == 'backup' else module.RESTORE
            calls = []
            adapters = {step: lambda requested: calls.append(requested) or True for step in steps}
            for bad in (dict(list(adapters.items())[:-1]), adapters | {'unknown':lambda _:True},
                        adapters | {steps[-1]:None}):
                with self.assertRaises(module.SequenceError):
                    module.run_sequence(operation, bad)
                self.assertEqual(calls, [])
            report = module.run_sequence(operation, adapters)
            self.assertEqual(calls, list(steps))
            self.assertEqual(report['completedSteps'], calls)
            self.assertIs(report['releaseAccepted'], False)

    def test_common_runner_stops_at_every_failed_step(self):
        module = self.module()
        for operation in ('backup','restore'):
            steps = module.BACKUP if operation == 'backup' else module.RESTORE
            for index, failed in enumerate(steps):
                for error in (False, RuntimeError('PRIVATE'), KeyboardInterrupt()):
                    calls = []
                    def adapter(step):
                        calls.append(step)
                        if step == failed:
                            if isinstance(error, BaseException):
                                raise error
                            return error
                        return True
                    expected = KeyboardInterrupt if isinstance(error, KeyboardInterrupt) else module.SequenceError
                    with self.assertRaises(expected) as caught:
                        module.run_sequence(operation, dict.fromkeys(steps, adapter))
                    self.assertNotIn('PRIVATE', str(caught.exception))
                    self.assertEqual(calls, list(steps[:index+1]))

    def test_common_runner_freezes_adapter_map_before_callback_mutation(self):
        module = self.module()
        calls = []
        def good(step):
            calls.append(step)
            return True
        adapters = dict.fromkeys(module.BACKUP, good)
        def scope(step):
            adapters.clear()
            return good(step)
        adapters['scope'] = scope
        report = module.run_sequence('backup', adapters)
        self.assertEqual(calls, list(module.BACKUP))
        self.assertEqual(report['status'], 'ADAPTER_SEQUENCE_COMPLETED_NOT_RECOVERY')
        self.assertEqual(adapters, {})


if __name__ == '__main__':
    unittest.main()
