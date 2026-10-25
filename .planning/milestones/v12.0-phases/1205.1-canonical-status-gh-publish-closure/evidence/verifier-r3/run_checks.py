"""Independent round-3 offline verification. Preserve previous evidence/source."""
import datetime, hashlib, json, os, shutil, subprocess, time
from pathlib import Path
ROOT = Path(__file__).resolve().parents[5]
OUT = Path(__file__).resolve().parent
PHASE = OUT.parent.parent
ENV = dict(os.environ)
ENV['DG_DE01_CONNECTOR_TOKEN'] = ''
ENV['DG_DE01_CONNECTOR_TOKEN_FILE'] = str(OUT/'nonexistent-test-token')
ENV['PYTHONDONTWRITEBYTECODE'] = '1'
ENV.pop('DG_RETAIN_PHASE1205_1_EVIDENCE', None)
assert not Path(ENV['DG_DE01_CONNECTOR_TOKEN_FILE']).exists()
assert not (OUT/'results.json').exists()
protected = [p for p in PHASE.rglob('*') if p.is_file() and OUT not in p.parents and not any(x in p.parts for x in ['__pycache__','bin','obj'])]
protected += [ROOT/'.planning'/n for n in ['STATE.md','ROADMAP.md','REQUIREMENTS.md']]
source_paths = set()
for plan in PHASE.glob('*-PLAN.md'):
    section = plan.read_text(encoding='utf-8').split('files_modified:\n',1)[1].split('autonomous:',1)[0]
    source_paths.update(line[2:].strip() for line in section.splitlines() if line.startswith('- '))
source_paths.update(['DG/src/DG.Core/Contracts/EvidenceEnvelopeReader.cs','data-service/tests/test_evidence_raw_admission.py','data-service/tests/test_evidence_unicode_containers.py'])
protected += [ROOT/p for p in source_paths]
before = {p.relative_to(ROOT).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest() for p in protected}
(OUT/'protected-before.json').write_text(json.dumps(before,indent=2),encoding='utf-8')
copies = {}
for relative in ['verifier/admission_probe.py','verifier/source_checks.py','verifier-r2/inmemory_probe.py']:
    src = OUT.parent/relative
    dst = OUT/src.name
    shutil.copyfile(src,dst)
    assert dst.read_bytes() == src.read_bytes()
    copies[relative] = hashlib.sha256(dst.read_bytes()).hexdigest()
UV = ['uv','run','--no-project','--with-requirements','data-service/requirements.txt','python']
TEST = UV+['-m','pytest']
CASES = [
 ('csharp',['dotnet','test','DG/tests/DG.Tests/DG.Tests.csproj','--no-restore','--filter','FullyQualifiedName~EvidenceContractTests|FullyQualifiedName~RuleEvaluatorTests|FullyQualifiedName~ValidationPublishPackageBuilderTests|FullyQualifiedName~Neo4jValidGraphRepositoryTests|FullyQualifiedName~DataServiceRequestAuthTests|FullyQualifiedName~SwrlSubsetConformanceTests','-v','minimal']),
 ('backend',TEST+['data-service/tests/test_evidence_contract.py','data-service/tests/test_validation_run_immutability.py','data-service/tests/test_route_inventory.py','data-service/tests/test_cross_project_matrix.py','-q','-m','not live and not integration']),
 ('wire',TEST+['data-service/tests/test_gh_publish_wire.py','data-service/tests/test_evidence_versions.py','data-service/tests/test_validation_entity_rollup.py','data-service/tests/test_evidence_raw_admission.py','data-service/tests/test_evidence_unicode_containers.py','-v','-m','not live and not integration']),
 ('de01',TEST+['tools/de01/tests','-q','-m','not live','-k','not live']),
 ('gh-rebuild',['dotnet','build','DG/src/DG.Grasshopper/DG.Grasshopper.csproj','-c','Release','--no-restore','-t:Rebuild','-v','minimal']),
 ('sdk-resolve',['dotnet','msbuild','DG/src/DG.Grasshopper/DG.Grasshopper.csproj','-p:Configuration=Release','-t:ResolveReferences','-getProperty:DefineConstants,TargetFramework','-getItem:ReferencePath,Compile']),
 ('artifact-check',['python',str(PHASE/'evidence/verify_evidence.py')]),
 ('source-checks',['python',str(OUT/'source_checks.py')]),
 ('admission-probe',UV+[str(OUT/'admission_probe.py')]),
 ('inmemory-probe',UV+[str(OUT/'inmemory_probe.py')]),
 ('review-probe',UV+['-B',str(OUT.parent/'review-2-probe.py')]),
]
results = []
for name, command in CASES:
    started = datetime.datetime.now(datetime.timezone.utc).isoformat()
    tick = time.monotonic()
    result = subprocess.run(command,cwd=ROOT,env=ENV,capture_output=True,timeout=600)
    output = (result.stdout+result.stderr).decode('utf-8',errors='replace')
    elapsed = round(time.monotonic()-tick,3)
    (OUT/(name+'.log')).write_text('command='+json.dumps(command)+'\nstarted='+started+'\n'+output+'\nexit='+str(result.returncode)+'\nwall_seconds='+str(elapsed)+'\n',encoding='utf-8')
    if name in ['sdk-resolve','review-probe'] and result.returncode == 0:
        (OUT/(name+'.json')).write_bytes(result.stdout)
    results.append(dict(name=name,command=command,started=started,exit=result.returncode,wall_seconds=elapsed))
    (OUT/'results.json').write_text(json.dumps(results,indent=2),encoding='utf-8')
    print(name,'exit',result.returncode,'seconds',elapsed,flush=True)
    if name not in ['sdk-resolve','review-probe']: print('\n'.join(output.splitlines()[-7:]),flush=True)
changed = [p for p,h in before.items() if not (ROOT/p).exists() or hashlib.sha256((ROOT/p).read_bytes()).hexdigest()!=h]
proof = dict(protectedFiles=len(before),changed=changed,copiedProbeSha256=copies)
(OUT/'preservation.json').write_text(json.dumps(proof,indent=2),encoding='utf-8')
print(proof,flush=True)
assert not changed
assert all(r['exit']==0 for r in results)
