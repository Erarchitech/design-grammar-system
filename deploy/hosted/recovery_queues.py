"""Read-only queue sample admission, NOT version-specific query implementation.

An approved outer runner supplies independent exact image/probe/schema binding
and two actual reads after producer block, consumer drain, writer stop. Binding
hashes and monotonic sequence labels alone cannot establish query completeness,
physical schema mapping, elapsed time or real quiescence. No builtin qualified
runtime profiles exist yet. The seven-role image set is a minimum qualification
subset, NOT discovery of all producers/queues or proof of the running container
images. Actual bindings and physical schema/probe coverage need a trusted runner.
Never translate unsupported/missing queues to zero.
"""
import copy
import re
try:
    from .recovery_checkpoint import QUEUES
except ImportError:
    from recovery_checkpoint import QUEUES


BINDING_IMAGES = frozenset({
    'speckle-server', 'speckle-preview-service', 'speckle-webhook-service',
    'speckle-fileimport-service', 'n8n', 'postgres', 'valkey'})


class QueueError(ValueError):
    pass


def _require(condition):
    if not condition:
        raise QueueError('queue sample rejected')


def _binding(binding):
    _require(type(binding) is dict and set(binding) == {'images', 'probeSha256', 'schemaSha256'})
    _require(type(binding['images']) is dict and set(binding['images']) == BINDING_IMAGES)
    _require(all(type(x) is str and re.fullmatch('sha256:[0-9a-f]{64}', x) for x in binding['images'].values()))
    _require(all(type(binding[k]) is str and re.fullmatch('[0-9a-f]{64}', binding[k])
                 for k in ('probeSha256', 'schemaSha256')))


def _sample(sample, expected_binding, *, empty):
    _require(type(sample) is dict and set(sample) ==
             {'binding', 'sequence', 'groups', 'backendsExamined', 'unknownQueues'})
    _binding(sample['binding'])
    _require(sample['binding'] == expected_binding)
    _require(type(sample['sequence']) is int and sample['sequence'] > 0)
    _require(sample['backendsExamined'] == ['n8n-sqlite', 'postgres', 'redis']
             and sample['unknownQueues'] == [])
    groups = sample['groups']
    _require(type(groups) is dict and set(groups) == set(QUEUES))
    for group, counters in QUEUES.items():
        _require(type(groups[group]) is dict and set(groups[group]) == counters)
        _require(all(type(x) is int and 0 <= x <= 2**63 - 1
                     and (not empty or x == 0) for x in groups[group].values()))


def admit_stable_empty(first, second, *, expected_binding):
    try:
        _binding(expected_binding)
        for sample in (first, second):
            _sample(sample, expected_binding, empty=True)
        _require(second['sequence'] > first['sequence'])
        return copy.deepcopy(first['groups'])
    except Exception:
        raise QueueError('queue sample rejected') from None


def wait_drained(read_sample, *, expected_binding, attest, timeout=30,
                 interval=0.25, max_reads=120, clock=None, sleep=None):
    """Bounded admission loop; not physical query implementation/quiescence proof.

    Outer runner MUST bound each synchronous reader call and enforce producer
    block with consumers running. This loop cannot preempt a blocked callback.
    On success, stop writers then obtain/admit two stable empty samples; a single
    drain sample does not authorize export. No stop/start calls occur here.
    """
    import math
    import time
    try:
        _binding(expected_binding)
        expected_binding = copy.deepcopy(expected_binding)
        _require(type(max_reads) is int and 1 <= max_reads <= 10000)
        _require(all(type(x) in (int, float) and math.isfinite(x) and x > 0
                     for x in (timeout, interval)) and interval <= timeout <= 3600)
        _require(attest('producers-blocked-consumers-running-bounded-reader') is True)
        clock, sleep = clock or time.monotonic, sleep or time.sleep
        start = previous_time = clock()
        _require(type(start) in (float, int) and math.isfinite(start))
        deadline = start + timeout
        previous_sequence = 0
        for index in range(max_reads):
            now = clock()
            _require(type(now) in (int, float) and math.isfinite(now)
                     and previous_time <= now < deadline)
            previous_time = now
            sample = copy.deepcopy(read_sample())
            now = clock()
            _require(type(now) in (int, float) and math.isfinite(now)
                     and previous_time <= now < deadline)
            previous_time = now
            _sample(sample, expected_binding, empty=False)
            _require(sample['sequence'] > previous_sequence)
            previous_sequence = sample['sequence']
            if all(value == 0 for group in sample['groups'].values() for value in group.values()):
                return {'sample': sample, 'reads': index + 1, 'quiescenceProven': False,
                        'nativeRecoveryProven': False}
            if index + 1 < max_reads:
                sleep(min(interval, deadline - now))
        raise QueueError('queue drain rejected')
    except BaseException:
        raise QueueError('queue drain rejected') from None

