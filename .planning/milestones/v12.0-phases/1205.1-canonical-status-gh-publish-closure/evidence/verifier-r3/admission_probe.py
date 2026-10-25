"""Independent held-out raw-schema/Python/C# admission controls; no app/I/O."""
import copy
import json
from pathlib import Path
import subprocess
import sys
ROOT=Path(__file__).resolve().parents[5]
OUT=Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT/'data-service'))
import evidence_contract as contract
import jsonschema
base=json.loads((OUT.parent/'wire/supported/persisted-evidence.json').read_bytes())
cases=[]
for name in ['baseline','integral-json-number','newline-hash']:
    p=copy.deepcopy(base)
    if name=='integral-json-number': p['canonicalizationVersion']=1.0
    if name=='newline-hash': p['inputHash']='A'*64+'\n'
    raw=json.dumps(p).encode()
    try:
        jsonschema.validate(p,contract.load_contract_schema()); schema=True
    except jsonschema.ValidationError: schema=False
    py=contract.read_envelope_dict(p) is not None
    result=subprocess.run(['dotnet',str(ROOT/'DG/tests/DG.PublishWireHarness/bin/Debug/net9.0/DG.PublishWireHarness.dll'),'read'],input=raw,capture_output=True,check=True)
    cs=json.loads(result.stdout)['envelopePresent']
    cases.append({'case':name,'rootSchemaAccepted':schema,'pythonReadAccepted':py,'csharpReadAccepted':cs})
    (OUT/(name+'-input.json')).write_bytes(raw)
    (OUT/(name+'-reader.json')).write_bytes(result.stdout)
(OUT/'admission-probe.json').write_text(json.dumps(cases,indent=2),encoding='utf-8')
print(json.dumps(cases,indent=2))
assert all(c['rootSchemaAccepted']==c['pythonReadAccepted']==c['csharpReadAccepted'] for c in cases), 'Strict full-envelope admission diverges across root schema, Python and C#'
