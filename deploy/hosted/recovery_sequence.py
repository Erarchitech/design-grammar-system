"""Offline sequence engine, NOT a trusted outer runner or authorization attestation.

Trusted adapter code must independently enforce real ownership, approval, expiry,
identity, deadlines, isolation and native evidence. Literal True is only an adapter
success signal; it is never proof of any of those properties. No CLI or native
adapter is wired here. No completion marker, retries, cleanup or acceptance claim.
Failure latches: the next export/restore cannot run on partial/unknown state.
"""
BACKUP = ('scope', 'identity', 'block-producers', 'drain-with-consumers',
          'stop-writers', 'stable-empty-queues', 'export-neo4j',
          'export-postgres', 'export-objects', 'export-n8n', 'export-api',
          'verify-inventory', 'encrypt', 'verify-ciphertext-transfer',
          'verify-plaintext-cleanup')

RESTORE = ('scope', 'identity', 'authenticate-decrypt', 'verify-inventory',
           'verify-key-custody', 'verify-empty-destination',
           'initialize-postgres', 'restore-postgres', 'restore-neo4j',
           'restore-objects', 'restore-n8n', 'restore-api',
           'verify-empty-queues', 'start-isolated-read-only',
           'semantic-verification', 'verify-plaintext-cleanup')


class SequenceError(ValueError):
    pass


class Sequence:
    def __init__(self, operation):
        if operation not in ('backup', 'restore'):
            raise SequenceError('recovery sequence rejected')
        self._steps = BACKUP if operation == 'backup' else RESTORE
        self._completed = []
        self._failed = None
        self._running = False

    @property
    def next_step(self):
        if self._failed is not None or len(self._completed) == len(self._steps):
            return None
        return self._steps[len(self._completed)]

    def run_next(self, adapter):
        step = self.next_step
        if step is None or not callable(adapter) or self._running:
            if self._running:
                self._failed = step
            raise SequenceError('recovery sequence rejected')
        self._running = True
        try:
            if adapter(step) is not True or self._failed is not None:
                raise SequenceError('recovery sequence rejected')
        except BaseException as error:
            self._failed = step
            if not isinstance(error, Exception):
                raise
            raise SequenceError('recovery sequence rejected') from None
        finally:
            self._running = False
        self._completed.append(step)

    def report(self):
        return {'status': 'ADAPTER_SEQUENCE_COMPLETED_NOT_RECOVERY'
                if len(self._completed) == len(self._steps) else
                'SEQUENCE_FAILED' if self._failed else 'SEQUENCE_PENDING',
                'completedSteps': list(self._completed), 'failedStep': self._failed,
                'nativeRecoveryProven': False, 'offMachineRestoreProven': False,
                'releaseAccepted': False}


def run_sequence(operation, adapters):
    """Preflight and run all fixed steps; NOT the trusted/native outer runner.

    An exact, privately snapshotted adapter map avoids a missing late adapter
    being discovered only after export/mutation. Trusted adapter bodies must
    enforce per-operation authorization, identity, deadlines and native evidence.
    No services, retries, completion marker or automatic recovery are wired here.
    """
    runner = Sequence(operation)
    steps = BACKUP if operation == 'backup' else RESTORE
    if type(adapters) is not dict or set(adapters) != set(steps):
        raise SequenceError('recovery sequence rejected')
    adapters = dict(adapters)
    if not all(callable(adapter) for adapter in adapters.values()):
        raise SequenceError('recovery sequence rejected')
    while runner.next_step is not None:
        runner.run_next(adapters[runner.next_step])
    return runner.report()

