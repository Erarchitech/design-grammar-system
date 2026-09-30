"""Record held-out result, resolved SDK, test counts, source preservation and fingerprint."""
import datetime
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
ROOT=Path(__file__).resolve().parents[5]
OUT=Path(__file__).resolve().parent
PHASE=OUT.parent.parent
command=['uv','run','--no-project','--with-requirements','data-service/requirements.txt','python',str(OUT/'inmemory_probe.py')]
env=dict(os.environ);env['PYTHONDONTWRITEBYTECODE']='1'
r=subprocess.run(command,cwd=ROOT,env=env,capture_output=True,timeout=30)
(OUT/'inmemory-probe.log').write_text('command='+json.dumps(command)+'\n'+(r.stdout+r.stderr).decode('utf-8')+'\nexit='+str(r.returncode)+'\n',encoding='utf-8')
print('held-out probe exit',r.returncode)
print(r.stdout.decode('utf-8'))
sdk=json.loads((OUT/'sdk-resolved.json').read_text(encoding='utf-8-sig'))
refs={}
for ref in sdk['Items']['ReferencePath']:
    p=Path(ref['Identity'])
    if p.name in ['RhinoCommon.dll','Grasshopper.dll','GH_IO.dll']:
        refs[p.name]={'path':str(p),'exists':p.is_file()}
assert len(refs)==3 and all(x['exists'] for x in refs.values())
assert 'GRASSHOPPER_SDK' in sdk['Properties']['DefineConstants']
compiled=[x['Identity'].replace('\\','/') for x in sdk['Items']['Compile']]
assert all(p in compiled for p in ['Validation/ValidationPublishClient.cs','Validation/ValidationPublishContract.cs'])
wire=(OUT/'wire.log').read_text(encoding='utf-8')
counts={}
for match in re.finditer(r'^data-service/tests/([^:]+)::.* PASSED ',wire,re.M):
    counts[match.group(1)]=counts.get(match.group(1),0)+1
assert sum(counts.values())==330 and counts['test_evidence_raw_admission.py']==122
before=json.loads((OUT/'protected-before.json').read_text(encoding='utf-8'))
changed=[p for p,h in before.items() if hashlib.sha256((ROOT/p).read_bytes()).hexdigest()!=h]
assert not changed
extras=['DG/tests/DG.PublishWireHarness/Program.cs','data-service/tests/test_evidence_raw_admission.py','DG/src/DG.Core/Contracts/EvidenceEnvelopeReader.cs']
scan=[]
for path in extras:
    for i,line in enumerate((ROOT/path).read_text(encoding='utf-8').splitlines(),1):
        if re.search(r'\b(TBD|FIXME|XXX|TODO|HACK|PLACEHOLDER)\b|pytest\.mark\.(skip|xfail)|Skip\s*=',line):
            scan.append({'path':path,'line':i,'text':line})
proof={'verified':datetime.datetime.now(datetime.timezone.utc).isoformat(),'head':subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),'sdk':refs,'properties':sdk['Properties'],'productionPublishCompileItems':[p for p in compiled if 'ValidationPublish' in p],'wirePassedByModule':counts,'protectedFiles':len(before),'protectedChanged':changed,'extraScanFindings':scan,'heldOutExit':r.returncode,'projectSkillDirectories':{p:(ROOT/p).is_dir() for p in ['.hermes/skills','.agents/skills']}}
(OUT/'final-checks.json').write_text(json.dumps(proof,indent=2),encoding='utf-8')
print(json.dumps(proof,indent=2))
old=(PHASE/'1205.1-VERIFICATION.md').read_text(encoding='utf-8')
covered=[line[4:] for line in old.split('covered_files:\n',1)[1].split('covered_digest:',1)[0].splitlines() if line.startswith('  - ')]
covered+=['data-service/tests/test_evidence_raw_admission.py',str((PHASE/'1205.1-REVIEW.md').relative_to(ROOT)).replace('\\','/'),str((PHASE/'1205.1-REVIEW-FIX.md').relative_to(ROOT)).replace('\\','/')]
covered=sorted(set(covered))
command=['node','C:/Users/Admin/AppData/Local/hermes/gsd-core/bin/gsd-tools.cjs','query','verification.fingerprint',str(PHASE.relative_to(ROOT)).replace('\\','/'),*covered]
f=subprocess.run(command,cwd=ROOT,capture_output=True,check=True)
(OUT/'fingerprint.json').write_bytes(f.stdout)
print(f.stdout.decode('utf-8'))
