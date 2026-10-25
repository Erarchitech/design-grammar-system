"""Independent phase verification: designated offline invocations only."""
import datetime
import json
import os
from pathlib import Path
import subprocess
import time

ROOT = Path(__file__).resolve().parents[5]
OUT = Path(__file__).resolve().parent
PHASE = '.planning/phases/1205.1-canonical-status-gh-publish-closure'
ENV = dict(os.environ)
ENV['DG_DE01_CONNECTOR_TOKEN'] = ''
ENV['DG_DE01_CONNECTOR_TOKEN_FILE'] = str(ROOT / PHASE / 'nonexistent-test-token')
ENV.pop('DG_RETAIN_PHASE1205_1_EVIDENCE', None)
assert not Path(ENV['DG_DE01_CONNECTOR_TOKEN_FILE']).exists()
UV = ['uv', 'run', '--no-project', '--with-requirements', 'data-service/requirements.txt', 'python', '-m', 'pytest']
CASES = [
 ('csharp', ['dotnet','test','DG/tests/DG.Tests/DG.Tests.csproj','--no-restore','--filter','FullyQualifiedName~EvidenceContractTests|FullyQualifiedName~RuleEvaluatorTests|FullyQualifiedName~ValidationPublishPackageBuilderTests|FullyQualifiedName~Neo4jValidGraphRepositoryTests|FullyQualifiedName~DataServiceRequestAuthTests|FullyQualifiedName~SwrlSubsetConformanceTests','-v','minimal']),
 ('backend', UV + ['data-service/tests/test_evidence_contract.py','data-service/tests/test_validation_run_immutability.py','data-service/tests/test_route_inventory.py','data-service/tests/test_cross_project_matrix.py','-q','-m','not live and not integration']),
 ('wire', UV + ['data-service/tests/test_gh_publish_wire.py','data-service/tests/test_evidence_versions.py','data-service/tests/test_validation_entity_rollup.py','-q','-m','not live and not integration']),
 ('de01', UV + ['tools/de01/tests','-q','-m','not live','-k','not live']),
 ('gh-build', ['dotnet','build','DG/src/DG.Grasshopper/DG.Grasshopper.csproj','-c','Release','--no-restore','-v','minimal']),
 ('gh-rebuild', ['dotnet','build','DG/src/DG.Grasshopper/DG.Grasshopper.csproj','-c','Release','--no-restore','-t:Rebuild','-v','minimal']),
 ('artifact-check', ['python', PHASE+'/evidence/verify_evidence.py']),
]
results=[]
for name, command in CASES:
    started = datetime.datetime.now(datetime.timezone.utc).isoformat()
    tick=time.monotonic()
    result=subprocess.run(command,cwd=ROOT,env=ENV,capture_output=True,timeout=240)
    duration=round(time.monotonic()-tick,3)
    output=(result.stdout+result.stderr).decode('utf-8',errors='replace')
    (OUT/(name+'.log')).write_text('command='+json.dumps(command)+'\nstarted='+started+'\n'+output+'\nexit='+str(result.returncode)+'\nwall_seconds='+str(duration)+'\n',encoding='utf-8')
    entry={'name':name,'command':command,'started':started,'exit':result.returncode,'wall_seconds':duration,'log':name+'.log'}
    results.append(entry)
    (OUT/'results.json').write_text(json.dumps(results,indent=2),encoding='utf-8')
    print(name, 'exit',result.returncode,'wall',duration,flush=True)
    print('\n'.join(output.splitlines()[-9:]),flush=True)
