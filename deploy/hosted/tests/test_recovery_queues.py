"""Offline version-bound queue admission; physical queries remain unqualified."""
import copy
import importlib.util
from pathlib import Path
import sys
import unittest

MODULE = Path(__file__).resolve().parents[1] / 'recovery_queues.py'


def synthetic_images():
    # Explicit independent fixture: do not derive expected roles from production.
    return {role:'sha256:'+str(i)*64 for i,role in enumerate((
        'speckle-server', 'speckle-preview-service', 'speckle-webhook-service',
        'speckle-fileimport-service', 'n8n', 'postgres', 'valkey'),1)}


class QueueTests(unittest.TestCase):
    def module(self):
        self.assertTrue(MODULE.is_file(), 'version-bound queue sample admission is absent')
        sys.path.insert(0, str(MODULE.parent))
        self.addCleanup(lambda: sys.path.remove(str(MODULE.parent)))
        spec = importlib.util.spec_from_file_location('queues', MODULE)
        m = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(m)
        return m

    def test_profile_requires_all_seven_queue_participant_images(self):
        m = self.module()
        old = {'images': {'speckle': 'sha256:'+'1'*64, 'n8n': 'sha256:'+'2'*64},
               'probeSha256': '8'*64, 'schemaSha256': '9'*64}
        def sample(binding, sequence):
            return {'binding': copy.deepcopy(binding), 'sequence': sequence,
                    'groups': {k:{c:0 for c in v} for k,v in m.QUEUES.items()},
                    'backendsExamined': ['n8n-sqlite','postgres','redis'], 'unknownQueues': []}
        with self.assertRaises(m.QueueError):
            m.admit_stable_empty(sample(old,1), sample(old,2), expected_binding=old)
        roles = ('speckle-server', 'speckle-preview-service', 'speckle-webhook-service',
                 'speckle-fileimport-service', 'n8n', 'postgres', 'valkey')
        binding = {'images': {role:'sha256:'+str(i)*64 for i,role in enumerate(roles,1)},
                   'probeSha256':'8'*64, 'schemaSha256':'9'*64}
        self.assertEqual(m.admit_stable_empty(sample(binding,1), sample(binding,2),
                         expected_binding=binding), sample(binding,1)['groups'])
        for role in roles:
            bad = copy.deepcopy(binding)
            del bad['images'][role]
            with self.subTest(missing=role), self.assertRaises(m.QueueError):
                m.admit_stable_empty(sample(bad,1), sample(bad,2), expected_binding=bad)
        bad = copy.deepcopy(binding)
        bad['images']['unqualified-extra'] = 'sha256:'+'a'*64
        with self.assertRaises(m.QueueError):
            m.admit_stable_empty(sample(bad,1), sample(bad,2), expected_binding=bad)

    def test_each_image_identity_is_checked_in_stable_and_drain_samples(self):
        m = self.module()
        binding = {'images': synthetic_images(),
                   'probeSha256':'8'*64, 'schemaSha256':'9'*64}
        first = {'binding':copy.deepcopy(binding), 'sequence':1,
                 'groups':{k:{c:0 for c in v} for k,v in m.QUEUES.items()},
                 'backendsExamined':['n8n-sqlite','postgres','redis'], 'unknownQueues':[]}
        for role in synthetic_images():
            for value in ('sha256:'+'f'*64, 'postgres:16.4-alpine3.20', None, True):
                bad = copy.deepcopy(first)
                bad['sequence'] = 2
                bad['binding']['images'][role] = value
                with self.subTest(role=role, value=value):
                    with self.assertRaises(m.QueueError):
                        m.admit_stable_empty(first, bad, expected_binding=binding)
                    reads = []
                    def read():
                        reads.append(1)
                        return bad
                    with self.assertRaises(m.QueueError):
                        m.wait_drained(read, expected_binding=binding, attest=lambda _:True,
                                       clock=lambda:0, sleep=lambda _:None)
                    self.assertEqual(reads,[1])
        # Incomplete expected binding must fail before attestation or any reader.
        for role in synthetic_images():
            bad = copy.deepcopy(binding)
            del bad['images'][role]
            calls = []
            with self.assertRaises(m.QueueError):
                m.wait_drained(lambda:calls.append('read'), expected_binding=bad,
                               attest=lambda _:calls.append('attest'))
            self.assertEqual(calls,[])

    def test_zero_samples_bound_to_exact_profile_and_all_three_backends(self):
        m = self.module()
        binding = {'images': synthetic_images(),
                   'probeSha256': '3' * 64, 'schemaSha256': '4' * 64}
        sample = {'binding': binding, 'sequence': 1,
                  'groups': {k: {c: 0 for c in v} for k, v in m.QUEUES.items()},
                  'backendsExamined': ['n8n-sqlite', 'postgres', 'redis'],
                  'unknownQueues': []}
        second = copy.deepcopy(sample)
        second['sequence'] = 2
        self.assertEqual(m.admit_stable_empty(sample, second, expected_binding=binding), sample['groups'])
        for mutate in (
            lambda d: d['binding'].update(probeSha256='9' * 64),
            lambda d: d.update(backendsExamined=['redis']),
            lambda d: d.update(unknownQueues=['synthetic-unknown']),
            lambda d: d['groups']['fileImport'].update(processing=1),
            lambda d: d['groups']['previewResponse'].update(active=False),
            lambda d: d['groups'].pop('legacyUpload'),
            lambda d: d.update(sequence=1),
        ):
            bad = copy.deepcopy(second)
            mutate(bad)
            with self.assertRaises(m.QueueError):
                m.admit_stable_empty(sample, bad, expected_binding=binding)
        self.assertEqual(sample['sequence'], 1)

    def test_drain_retries_complete_version_bound_samples_until_empty(self):
        m = self.module()
        self.assertTrue(hasattr(m, 'wait_drained'), 'bounded drain polling is absent')
        binding = {'images': synthetic_images(),
                   'probeSha256': '3'*64, 'schemaSha256': '4'*64}
        empty = {'binding': copy.deepcopy(binding), 'sequence': 2,
                 'groups': {k: {c: 0 for c in v} for k, v in m.QUEUES.items()},
                 'backendsExamined': ['n8n-sqlite','postgres','redis'], 'unknownQueues': []}
        busy = copy.deepcopy(empty)
        busy['sequence'] = 1
        busy['groups']['fileImport']['processing'] = 3
        samples = iter([busy, empty])
        delays = []
        result = m.wait_drained(lambda: next(samples), expected_binding=binding,
            attest=lambda _: True, clock=lambda: 0.0, sleep=delays.append,
            timeout=5, interval=0.1, max_reads=3)
        self.assertEqual(result['sample'], empty)
        self.assertEqual(result['reads'], 2)
        self.assertEqual(delays, [0.1])
        self.assertIs(result['quiescenceProven'], False)
        result['sample']['binding']['images']['n8n'] = 'modified'
        self.assertEqual(empty['binding'], binding)

    def test_drain_rejects_unsupported_samples_without_retry(self):
        m = self.module()
        binding = {'images': synthetic_images(),
                   'probeSha256':'3'*64, 'schemaSha256':'4'*64}
        sample = {'binding':binding, 'sequence':1,
                  'groups':{k:{c:0 for c in v} for k,v in m.QUEUES.items()},
                  'backendsExamined':['n8n-sqlite','postgres','redis'], 'unknownQueues':[]}
        for mutation in (
            lambda s:s['binding'].update(schemaSha256='9'*64),
            lambda s:s.update(backendsExamined=['redis']),
            lambda s:s.update(unknownQueues=['unknown']),
            lambda s:s['groups'].pop('legacyUpload'),
            lambda s:s['groups']['fileImport'].update(queued=True),
            lambda s:s['groups']['fileImport'].update(queued=-1),
            lambda s:s['groups']['fileImport'].update(queued=2**63),
        ):
            bad = copy.deepcopy(sample)
            mutation(bad)
            reads, sleeps = [], []
            def read():
                reads.append(1)
                return bad
            with self.assertRaises(m.QueueError):
                m.wait_drained(read, expected_binding=binding, attest=lambda _:True,
                               clock=lambda:0, sleep=sleeps.append)
            self.assertEqual(reads, [1])
            self.assertEqual(sleeps, [])

    def test_drain_has_poll_cap_deadline_and_monotonic_sequence(self):
        m = self.module()
        binding = {'images': synthetic_images(),
                   'probeSha256':'3'*64, 'schemaSha256':'4'*64}
        for scenario in ('cap', 'deadline', 'sequence', 'clock-backward', 'interrupt', 'denied'):
            with self.subTest(scenario=scenario):
                sample = {'binding':binding, 'sequence':0,
                    'groups':{k:{c:1 for c in v} for k,v in m.QUEUES.items()},
                    'backendsExamined':['n8n-sqlite','postgres','redis'], 'unknownQueues':[]}
                reads, delays = [], []
                current = [0.0]
                def read():
                    reads.append(1)
                    if scenario == 'interrupt':
                        raise KeyboardInterrupt('PRIVATE')
                    sample['sequence'] = 1 if scenario == 'sequence' else len(reads)
                    if scenario == 'deadline':
                        current[0] = 100.0
                        for group in sample['groups'].values():
                            for key in group:
                                group[key] = 0
                    if scenario == 'clock-backward':
                        current[0] = -1.0
                    return sample
                with self.assertRaises(m.QueueError) as error:
                    m.wait_drained(read, expected_binding=binding,
                        attest=lambda _: scenario != 'denied', timeout=1, interval=0.1,
                        max_reads=3, clock=lambda:current[0], sleep=delays.append)
                self.assertNotIn('PRIVATE', str(error.exception))
                expected = {'cap':3, 'deadline':1, 'sequence':2,
                            'clock-backward':1, 'interrupt':1, 'denied':0}[scenario]
                self.assertEqual(len(reads), expected)
                if scenario == 'cap':
                    self.assertEqual(delays, [0.1,0.1])


if __name__ == '__main__':
    unittest.main()
