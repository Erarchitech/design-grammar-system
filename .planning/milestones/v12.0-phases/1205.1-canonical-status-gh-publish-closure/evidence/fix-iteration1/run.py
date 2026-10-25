"""Bounded commands, timestamped output; no production network or credentials."""
import datetime
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[5]
OUT = Path(__file__).resolve().parent
UV = ['uv', 'run', '--no-project', '--with-requirements', 'data-service/requirements.txt', 'python']
ENV = dict(os.environ)
ENV['DG_DE01_CONNECTOR_TOKEN'] = ''
ENV['DG_DE01_CONNECTOR_TOKEN_FILE'] = str(OUT / 'nonexistent-token')
ENV.pop('DG_RETAIN_PHASE1205_1_EVIDENCE', None)
assert not Path(ENV['DG_DE01_CONNECTOR_TOKEN_FILE']).exists()


def run(name, command):
    result = subprocess.run(command, cwd=ROOT, env=ENV, capture_output=True, timeout=300)
    output = (result.stdout + result.stderr).decode('utf-8', errors='replace')
    (OUT / (name + '.log')).write_text('command=' + json.dumps(command) + '\ntime=' + datetime.datetime.now(datetime.timezone.utc).isoformat() + '\n' + output + '\nexit=' + str(result.returncode), encoding='utf-8')
    print(name, 'exit', result.returncode)
    print(output[-3500:])
    return result.returncode


if __name__ == '__main__':
    name = sys.argv[1]
    if name == 'snapshot':
        files = ['data-service/app.py', 'data-service/evidence_contract.py', 'DG/src/DG.Core/Contracts/EvidenceEnvelopeReader.cs', 'spec/evidence-contract.schema.json', 'spec/EVIDENCE-CONTRACT.md', 'spec/API.md', 'spec/DATABASE.md']
        for file in files:
            target = OUT / 'before' / file
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes((ROOT / file).read_bytes())
        phase = OUT.parent.parent
        protected = list(phase.glob('*SUMMARY.md')) + [phase / '1205.1-REVIEW.md', phase / '1205.1-VERIFICATION.md'] + list((OUT.parent / 'wire').rglob('*.json')) + [OUT.parent / 'verifier/admission_probe.py']
        (OUT / 'protected-before.json').write_text(json.dumps({str(p.relative_to(ROOT)): hashlib.sha256(p.read_bytes()).hexdigest() for p in protected}, indent=2))
    else:
        run(name, UV + ['-m', 'pytest', 'data-service/tests/test_evidence_raw_admission.py', '-q', '--tb=short'] + sys.argv[2:])
