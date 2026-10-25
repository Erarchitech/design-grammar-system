"""Rerun designated gates, unchanged independent probe, and retained-byte checks."""
import hashlib
import importlib.util
import json
from pathlib import Path
import shutil
from run import ROOT, OUT, UV, run

phase = OUT.parent.parent
source = OUT.parent / 'verifier/admission_probe.py'
copy = OUT / 'admission_probe.py'
shutil.copyfile(source, copy)  # byte-identical; same depth, shared original evidence/wire inputs
assert source.read_bytes() == copy.read_bytes()
checks = [
 ('backend', UV + ['-m','pytest','data-service/tests/test_evidence_contract.py','data-service/tests/test_validation_run_immutability.py','data-service/tests/test_route_inventory.py','data-service/tests/test_cross_project_matrix.py','-q','-m','not live and not integration']),
 ('wire', UV + ['-m','pytest','data-service/tests/test_gh_publish_wire.py','data-service/tests/test_evidence_versions.py','data-service/tests/test_validation_entity_rollup.py','data-service/tests/test_evidence_raw_admission.py','-q','-m','not live and not integration']),
 ('csharp', ['dotnet','test','DG/tests/DG.Tests/DG.Tests.csproj','--no-restore','--filter','FullyQualifiedName~EvidenceContractTests|FullyQualifiedName~RuleEvaluatorTests|FullyQualifiedName~ValidationPublishPackageBuilderTests|FullyQualifiedName~Neo4jValidGraphRepositoryTests|FullyQualifiedName~DataServiceRequestAuthTests|FullyQualifiedName~SwrlSubsetConformanceTests','-v','minimal']),
 ('de01', UV + ['-m','pytest','tools/de01/tests','-q','-m','not live','-k','not live']),
 ('gh-rebuild', ['dotnet','build','DG/src/DG.Grasshopper/DG.Grasshopper.csproj','-c','Release','--no-restore','-t:Rebuild','-v','minimal']),
 ('admission-probe', UV + [str(copy)]),
 ('artifact-check', ['python',str(OUT.parent / 'verify_evidence.py')]),
]
results = {name: run(name, command) for name, command in checks}
spec = importlib.util.spec_from_file_location('verify_evidence', OUT.parent / 'verify_evidence.py')
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)
module.EVIDENCE = OUT
module.sdk_proof()
protected = json.loads((OUT / 'protected-before.json').read_text())
changed = [p for p, digest in protected.items() if hashlib.sha256((ROOT / p).read_bytes()).hexdigest() != digest]
assert not changed, changed
results['protected_unchanged'] = len(protected)
(OUT / 'release-results.json').write_text(json.dumps(results, indent=2), encoding='utf-8')
assert all(value == 0 for name,value in results.items() if name != 'protected_unchanged'), results
