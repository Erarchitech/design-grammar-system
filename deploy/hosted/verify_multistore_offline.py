"""Repeatable strict OFFLINE subset verification; never a HOST-04 certificate.

Explicit allowlist only. Tests use synthetic scratch, local child processes and
config-only checks, not daemon/services. Legacy archive suite with known skip
and native integration are deliberately excluded, NOT marked passed.
Run from repository root: python3 -B deploy/hosted/verify_multistore_offline.py
JSON stdout is sanitized evidence; no key files or owner data read by this tool.
"""
import hashlib
import json
import math
import os
from pathlib import Path
import re
import subprocess
import sys
import time

SUITES = (
    'test_recovery_checkpoint.py', 'test_recovery_postgres.py',
    'test_recovery_package.py', 'test_recovery_execution.py',
    'test_recovery_runner.py', 'test_recovery_probe.py',
    'test_recovery_snapshot.py', 'test_recovery_diagnostic.py',
    'test_recovery_cleanup.py', 'test_recovery_sequence.py',
    'test_recovery_n8n.py', 'test_recovery_objects.py',
    'test_recovery_queues.py', 'test_recovery_pg_init.py',
    'test_recovery_transport.py', 'test_recovery_multistore_offline.py',
    'test_recovery_offline_verifier.py')
SUMMARY = re.compile(r'^Required tests: discovered=(\d+), ran=(\d+), failures=(\d+), errors=(\d+), skipped=(\d+)$', re.M)


def verify(*, run=None, clock=None):
    """Trusted local test sources, max90s child/max600s total. No report writes."""
    run, clock = run or subprocess.run, clock or time.monotonic
    hosted = Path(__file__).resolve().parent
    repository = hosted.parents[1]
    start = previous = clock()
    if type(start) not in (int, float) or not math.isfinite(start):
        raise ValueError('offline verification clock rejected')
    deadline = start + 600
    rows, expired = [], False
    for suite in SUITES:
        now = clock()
        if type(now) not in (int, float) or not math.isfinite(now) or not previous <= now < deadline:
            expired = True
            break
        previous = now
        row = {'module': suite, 'passed': False, 'exitCode': None, 'counts': None}
        try:
            row['testSourceSha256'] = hashlib.sha256((hosted / 'tests' / suite).read_bytes()).hexdigest()
            result = run([sys.executable, '-B', str(hosted / 'tests' / 'run_required.py'), suite],
                         cwd=str(repository), shell=False, capture_output=True, text=True,
                         timeout=min(90, deadline-now), env=dict(os.environ, PYTHONDONTWRITEBYTECODE='1'))
            row['exitCode'] = result.returncode
            matches = SUMMARY.findall(result.stderr.replace('\r\n','\n'))
            if len(matches) == 1:
                counts = dict(zip(('discovered','ran','failures','errors','skipped'), map(int,matches[0])))
                row['counts'] = counts
                row['passed'] = (result.returncode == 0 and counts['discovered'] == counts['ran']
                                 and counts['ran'] > 0 and not any(counts[k] for k in ('failures','errors','skipped')))
        except Exception:
            # Do not echo test tracebacks, paths, argv or output in reports.
            row['passed'] = False
        rows.append(row)
    # Include last child in total wall-clock admission, not only next iteration.
    if not expired:
        now = clock()
        expired = type(now) not in (int,float) or not math.isfinite(now) or not previous <= now < deadline
    return {'kind': 'OFFLINE_SYNTHETIC_SUBSET_NOT_NATIVE_RECOVERY',
            'passed': not expired and len(rows) == len(SUITES) and all(r['passed'] for r in rows),
            'suites': rows, 'totalTestsRun': sum(r['counts']['ran'] for r in rows if r['counts']),
            'deadlineExceeded': expired, 'nativeRecoveryProven': False,
            'offMachineRestoreProven': False, 'cryptographyQualified': False,
            'releaseAccepted': False,
            'excluded': ['legacy archive suite (known required-runner skip)',
                         'native containers/services/integration', 'image/build/evidence suites outside recovery subset']}


def main():
    if len(sys.argv) != 1:
        print(json.dumps({'passed':False,'error':'offline verifier takes no arguments'}))
        return 2
    try:
        report = verify()
    except Exception:
        print(json.dumps({'passed':False,'error':'offline verification rejected'}))
        return 1
    print(json.dumps(report, indent=2))
    return 0 if report['passed'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
