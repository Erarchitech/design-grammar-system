"""Independent round-2 designated offline verification; never overwrite earlier evidence."""
import datetime
import hashlib
import json
import os
from pathlib import Path
import subprocess
import time

ROOT = Path(__file__).resolve().parents[5]
OUT = Path(__file__).resolve().parent
PHASE = OUT.parent.parent
ENV = dict(os.environ)
ENV['DG_DE01_CONNECTOR_TOKEN'] = ''
ENV['DG_DE01_CONNECTOR_TOKEN_FILE'] = str(OUT / 'nonexistent-test-token')
ENV['PYTHONDONTWRITEBYTECODE'] = '1'
ENV.pop('DG_RETAIN_PHASE1205_1_EVIDENCE', None)
assert not Path(ENV['DG_DE01_CONNECTOR_TOKEN_FILE']).exists()
assert not (OUT/'results.json').exists(), 'Refuse overwriting a completed round'
protected = list(PHASE.glob('*.md')) + [ROOT/'.planning'/n for n in ['STATE.md','ROADMAP.md','REQUIREMENTS.md']]
for directory in ['wire','verifier','fix-iteration1']:
    protected += [p for p in (OUT.parent/directory).rglob('*') if p.is_file() and '__pycache__' not in p.parts]
source_paths = set()
for plan in PHASE.glob('*-PLAN.md'):
    section = plan.read_text(encoding='utf-8').split('files_modified:\n',1)[1].split('autonomous:',1)[0]
    source_paths.update(line[2:].strip() for line in section.splitlines() if line.startswith('- '))
source_paths.update(['DG/src/DG.Core/Contracts/EvidenceEnvelopeReader.cs','data-service/tests/test_evidence_raw_admission.py'])
protected += [ROOT/p for p in source_paths]
before = {str(p.relative_to(ROOT)).replace('\\','/'): hashlib.sha256(p.read_bytes()).hexdigest() for p in protected}
(OUT/'protected-before.json').write_text(json.dumps(before,indent=2),encoding='utf-8')
for name in ['admission_probe.py','source_checks.py']:
    source = OUT.parent/'verifier'/name
    (OUT/name).write_bytes(source.read_bytes())
    assert (OUT/name).read_bytes() == source.read_bytes()
UV = ['uv','run','--no-project','--with-requirements','data-service/requirements.txt','python']
TEST = UV + ['-m','pytest']
CASES = [
 ('csharp',['dotnet','test','DG/tests/DG.Tests/DG.Tests.csproj','--no-restore','--filter','FullyQualifiedName~EvidenceContractTests|FullyQualifiedName~RuleEvaluatorTests|FullyQualifiedName~ValidationPublishPackageBuilderTests|FullyQualifiedName~Neo4jValidGraphRepositoryTests|FullyQualifiedName~DataServiceRequestAuthTests|FullyQualifiedName~SwrlSubsetConformanceTests','-v','minimal']),
 ('backend',TEST+['data-service/tests/test_evidence_contract.py','data-service/tests/test_validation_run_immutability.py','data-service/tests/test_route_inventory.py','data-service/tests/test_cross_project_matrix.py','-q','-m','not live and not integration']),
 ('wire',TEST+['data-service/tests/test_gh_publish_wire.py','data-service/tests/test_evidence_versions.py','data-service/tests/test_validation_entity_rollup.py','data-service/tests/test_evidence_raw_admission.py','-v','-m','not live and not integration']),
 ('de01',TEST+['tools/de01/tests','-q','-m','not live','-k','not live']),
 ('gh-rebuild',['dotnet','build','DG/src/DG.Grasshopper/DG.Grasshopper.csproj','-c','Release','--no-restore','-t:Rebuild','-v','minimal']),
 ('sdk-resolve',['dotnet','msbuild','DG/src/DG.Grasshopper/DG.Grasshopper.csproj','-p:Configuration=Release','-t:ResolveReferences','-getProperty:DefineConstants,TargetFramework','-getItem:ReferencePath,Compile']),
 ('artifact-check',['python',str(PHASE/'evidence/verify_evidence.py')]),
 ('source-checks',['python',str(OUT/'source_checks.py')]),
 ('admission-probe',UV+[str(OUT/'admission_probe.py')]),
]
results=[]
for name,command in CASES:
    started=datetime.datetime.now(datetime.timezone.utc).isoformat()
    tick=time.monotonic()
    result=subprocess.run(command,cwd=ROOT,env=ENV,capture_output=True,timeout=300)
    output=(result.stdout+result.stderr).decode('utf-8',errors='replace')
    elapsed=round(time.monotonic()-tick,3)
    (OUT/(name+'.log')).write_text('command='+json.dumps(command)+'\nstarted='+started+'\n'+output+'\nexit='+str(result.returncode)+'\nwall_seconds='+str(elapsed)+'\n',encoding='utf-8')
    if name=='sdk-resolve' and result.returncode==0:
        (OUT/'sdk-resolved.json').write_bytes(result.stdout)
    results.append({'name':name,'command':command,'started':started,'exit':result.returncode,'wall_seconds':elapsed})
    (OUT/'results.json').write_text(json.dumps(results,indent=2),encoding='utf-8')
    print(name, 'exit',result.returncode,'seconds',elapsed,flush=True)
    if name != 'sdk-resolve': print('\n'.join(output.splitlines()[-7:]),flush=True)
changed=[p for p,h in before.items() if hashlib.sha256((ROOT/p).read_bytes()).hexdigest()!=h]
proof={'protectedFiles':len(before),'changed':changed,'probeByteIdentical':(OUT/'admission_probe.py').read_bytes()==(OUT.parent/'verifier/admission_probe.py').read_bytes(),'sourceChecksByteIdentical':(OUT/'source_checks.py').read_bytes()==(OUT.parent/'verifier/source_checks.py').read_bytes()}
(OUT/'preservation.json').write_text(json.dumps(proof,indent=2),encoding='utf-8')
print(proof,flush=True)
assert not changed
assert all(r['exit']==0 for r in results)
