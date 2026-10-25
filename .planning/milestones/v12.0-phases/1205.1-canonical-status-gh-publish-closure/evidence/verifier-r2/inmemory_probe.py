"""Held-out CR-03: Pydantic-supported containers must not launder nonfinite metadata."""
import json
from pathlib import Path
import subprocess
import sys
ROOT=Path(__file__).resolve().parents[5]
OUT=Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT/'data-service'))
import evidence_contract as c

results=[]
for name,value,should_reject in [
    ('finite-list', [1.5], False),
    ('finite-tuple', (1.5,), False),
    ('nan-list', [float('nan')], True),
    ('nan-tuple', (float('nan'),), True),
    ('positive-infinity-tuple', (float('inf'),), True),
    ('negative-infinity-tuple', (float('-inf'),), True),
]:
    item={'case':name,'expectedRejected':should_reject}
    try:
        envelope=c.build_envelope_with_rule_results('p','d','s','1','test',[],[],source_representation={'x':value})
        raw=envelope.model_dump_json(exclude_none=True).encode()
        item['rejected']=False
        item['serializedSourceRepresentation']=json.loads(raw)['sourceRepresentation']
        item['pythonReadAccepted']=c.read_envelope_dict(json.loads(raw)) is not None
        output=subprocess.run(['dotnet',str(ROOT/'DG/tests/DG.PublishWireHarness/bin/Debug/net9.0/DG.PublishWireHarness.dll'),'read'],input=raw,capture_output=True,check=True).stdout
        item['csharpReadAccepted']=json.loads(output)['envelopePresent']
        (OUT/(name+'-factory-output.json')).write_bytes(raw)
        (OUT/(name+'-reader.json')).write_bytes(output)
    except ValueError as exc:
        item['rejected']=True
        item['errorType']=type(exc).__name__
    results.append(item)
legacy=c.build_envelope('p','d','s','1','test',[],source_representation={'x':(float('nan'),)})
try:
    c.validate_envelope(legacy)
    legacy_rejected=False
except ValueError:
    legacy_rejected=True
summary={'cases':results,'legacyValidateEnvelopeRejectsTupleNan':legacy_rejected}
(OUT/'inmemory-probe.json').write_text(json.dumps(summary,indent=2),encoding='utf-8')
print(json.dumps(summary,indent=2))
assert all(x['rejected']==x['expectedRejected'] for x in results) and legacy_rejected, 'CR-03: tuple metadata nonfinite values silently serialized to null before admission'
