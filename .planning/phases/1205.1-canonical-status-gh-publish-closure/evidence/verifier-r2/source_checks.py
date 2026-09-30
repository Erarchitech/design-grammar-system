"""Read-only source/provenance checks, output only in verifier evidence."""
import ast
import datetime
import hashlib
import json
from pathlib import Path
import re
import subprocess

ROOT=Path(__file__).resolve().parents[5]
OUT=Path(__file__).resolve().parent
PHASE=OUT.parent.parent

def head(path):
    return subprocess.run(['git','show','HEAD:'+path],cwd=ROOT,capture_output=True,check=True).stdout.decode('utf-8').replace('\r\n','\n')

def segment(source,name):
    return ast.dump(next(n for n in ast.parse(source).body if getattr(n,'name',None)==name),include_attributes=False)

py='data-service/tests/test_evidence_contract.py'
assert segment(head(py),'TestParseEvidenceEnvelope') == segment((ROOT/py).read_text(encoding='utf-8'),'TestParseEvidenceEnvelope')
cs='DG/tests/DG.Tests/Neo4jValidGraphRepositoryTests.cs'
old=head(cs);new=(ROOT/cs).read_text(encoding='utf-8')
pattern=r'    private static string BuildEnvelopeJson\(.*?(?=\n    \[)'
a=re.search(pattern,old,re.S);b=re.search(pattern,new,re.S)
assert a and b and a.group(0).strip()==b.group(0).strip()
app='data-service/app.py'
oldtree=ast.parse(head(app));newtree=ast.parse((ROOT/app).read_text(encoding='utf-8'))
changes=[]
for name in ['parse_evidence_envelope','_parse_shacl_report','_compute_canonical_state_hash','_project_state_summary']:
    def catches(tree):
        fn=next(n for n in tree.body if getattr(n,'name',None)==name)
        return [ast.unparse(h.type) for n in ast.walk(fn) if isinstance(n,ast.Try) for h in n.handlers]
    changes.append({'function':name,'before':catches(oldtree),'after':catches(newtree)})
paths=set()
for plan in sorted(PHASE.glob('*-PLAN.md')):
    text=plan.read_text(encoding='utf-8')
    section=text.split('files_modified:\n',1)[1].split('autonomous:',1)[0]
    paths.update(line[2:].strip() for line in section.splitlines() if line.startswith('- '))
scan=[]
for path in sorted(paths):
    if path.endswith(('.cs','.py','.json')):
        for n,line in enumerate((ROOT/path).read_text(encoding='utf-8').splitlines(),1):
            if re.search(r'\b(TBD|FIXME|XXX|TODO|HACK|PLACEHOLDER)\b|pytest\.mark\.(skip|xfail)|Skip\s*=',line):
                scan.append({'path':path,'line':n,'text':line})
checks=[]
dll=ROOT/'DG/tests/DG.PublishWireHarness/bin/Debug/net9.0/DG.PublishWireHarness.dll'
for directory in sorted((PHASE/'evidence/wire').iterdir()):
    raw=(directory/'persisted-evidence.json').read_bytes()
    p=json.loads(raw);request=json.loads((directory/'request.json').read_bytes())
    result=subprocess.run(['dotnet',str(dll),'read'],input=raw,cwd=ROOT,capture_output=True,check=True)
    projection=json.loads(result.stdout)
    assert projection==json.loads((directory/'reader-output.json').read_bytes())
    assert projection['inputSha256']==hashlib.sha256(raw).hexdigest()
    for row in p['rows']:
        entity=next(e for e in request['entities'] if e['dgEntityId']==row['objectId'])
        assert row['canonicalStatus']==entity['canonicalStatuses'][row['ruleId']]
        assert row.get('warnings',[])==entity['canonicalWarnings'].get(row['ruleId'],[])
        assert row.get('detail')==entity['canonicalDetails'].get(row['ruleId'])
    checks.append({'scenario':directory.name,'persistedSha256':hashlib.sha256(raw).hexdigest(),'rows':[(r['ruleId'],r['objectId'],r['canonicalStatus']) for r in p['rows']],'ruleResults':[(r['ruleId'],r['canonicalStatus']) for r in p['ruleResults']],'currentReaderMatchesRetained':True,'rowHashPairs':sum(bool(r.get('inputHash') and r.get('outputHash')) for r in p['rows'])})
    (OUT/(directory.name+'-current-reader.json')).write_bytes(result.stdout)
proof={'verified':datetime.datetime.now(datetime.timezone.utc).isoformat(),'originalPythonParserClassUnchanged':True,'originalCSharpFullLiteralHelperUnchanged':True,'catches':changes,'scanFindings':scan,'retainedArtifactsCurrentReader':checks,'phaseOwnedPaths':sorted(paths)}
(OUT/'source-checks.json').write_text(json.dumps(proof,indent=2),encoding='utf-8')
print(json.dumps(proof,indent=2))
