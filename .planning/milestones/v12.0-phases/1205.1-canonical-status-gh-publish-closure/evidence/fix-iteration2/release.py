"""Designated safe gates plus unchanged historical probes; no history overwrite."""
import ast
import difflib
import hashlib
import importlib.util
import json
import shutil
import subprocess
import sys
from run import ROOT, OUT, UV, ENV, TOUCH, run

copied = {}
for source in ['verifier/admission_probe.py', 'verifier/source_checks.py', 'verifier-r2/inmemory_probe.py']:
    origin = OUT.parent / source
    target = OUT / origin.name
    shutil.copyfile(origin, target)
    assert origin.read_bytes() == target.read_bytes()
    copied[source] = hashlib.sha256(target.read_bytes()).hexdigest()
checks = [
 ('backend', UV + ['-m','pytest','data-service/tests/test_evidence_contract.py','data-service/tests/test_validation_run_immutability.py','data-service/tests/test_route_inventory.py','data-service/tests/test_cross_project_matrix.py','-q','-m','not live and not integration']),
 ('wire', UV + ['-m','pytest','data-service/tests/test_gh_publish_wire.py','data-service/tests/test_evidence_versions.py','data-service/tests/test_validation_entity_rollup.py','data-service/tests/test_evidence_raw_admission.py','data-service/tests/test_evidence_unicode_containers.py','-q','-m','not live and not integration']),
 ('csharp', ['dotnet','test','DG/tests/DG.Tests/DG.Tests.csproj','--no-restore','--filter','FullyQualifiedName~EvidenceContractTests|FullyQualifiedName~RuleEvaluatorTests|FullyQualifiedName~ValidationPublishPackageBuilderTests|FullyQualifiedName~Neo4jValidGraphRepositoryTests|FullyQualifiedName~DataServiceRequestAuthTests|FullyQualifiedName~SwrlSubsetConformanceTests','-v','minimal']),
 ('de01', UV + ['-m','pytest','tools/de01/tests','-q','-m','not live','-k','not live']),
 ('gh-rebuild', ['dotnet','build','DG/src/DG.Grasshopper/DG.Grasshopper.csproj','-c','Release','--no-restore','-t:Rebuild','-v','minimal']),
 ('admission-probe', UV + [str(OUT / 'admission_probe.py')]),
 ('inmemory-probe', UV + [str(OUT / 'inmemory_probe.py')]),
 ('source-checks', ['python', str(OUT / 'source_checks.py')]),
 ('artifact-check', ['python',str(OUT.parent / 'verify_evidence.py')]),
]
if '--resume-probes' in sys.argv:
    results = {}
    for name, command in checks:
        log = (OUT / (name + '.log')).read_text(encoding='utf-8')
        results[name] = int(log.rsplit('exit=', 1)[1])
else:
    results = {name: run(name, command) for name, command in checks}
# The review probe uses parents[4]; execute it at its original path unchanged.
# It only prints observations, so redirect those bytes into the NEW directory.
probe = OUT.parent / 'review-2-probe.py'
p = subprocess.run(UV + ['-B', str(probe)], cwd=ROOT, env=ENV, capture_output=True, timeout=300)
(OUT / 'review-2-probe.json').write_bytes(p.stdout)
(OUT / 'review-2-probe.stderr.log').write_bytes(p.stderr)
results['review-probe-exit'] = p.returncode
assert p.returncode == 0, p.stderr.decode(errors='replace')
observations = json.loads(p.stdout)
s = observations['summary']
assert not s['expected_admission_mismatches'] and not s['response_failures'] and not s['strict_process_failures'] and not s['binary_changed_during_probe'], s
assert all(x['factory'] == x['legacy_validate'] == 'rejected' for x in observations['inmemory'])
assert all(not x['admitted'] and x['response'] == 'ok' for x in observations['shacl'])
# All raw read and full-admission observations agree; historical full-vs-read differs intentionally.
assert all(x['python_read'] == x['csharp_read']['admitted'] for x in observations['cases'])
assert all(x['full_model'] == x['csharp_strict']['admitted'] for x in observations['cases'] if 'full_model' in x and 'csharp_strict' in x)
results['review-observations'] = s
spec = importlib.util.spec_from_file_location('verify_evidence', OUT.parent / 'verify_evidence.py')
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)
module.EVIDENCE = OUT
module.sdk_proof()
protected = json.loads((OUT / 'protected-before.json').read_text())
changed = [p for p, digest in protected.items() if not (ROOT/p).is_file() or hashlib.sha256((ROOT/p).read_bytes()).hexdigest() != digest]
assert not changed, changed
results['protected_unchanged'] = len(protected)
results['copied_probe_sha256'] = copied
modified = TOUCH + ['data-service/tests/test_evidence_unicode_containers.py']
diff = []
for path in modified:
    before = OUT / 'before' / path
    old = before.read_text(encoding='utf-8').splitlines(keepends=True) if before.exists() else []
    new = (ROOT/path).read_text(encoding='utf-8').splitlines(keepends=True)
    diff.extend(difflib.unified_diff(old, new, fromfile='before/'+path, tofile='after/'+path))
    if path.endswith('.py'):
        ast.parse((ROOT/path).read_text(encoding='utf-8'))
(OUT / 'iteration-only.diff').write_text(''.join(diff), encoding='utf-8')
(OUT / 'manifest.json').write_text(json.dumps({
    'source_sha256': {p: hashlib.sha256((ROOT/p).read_bytes()).hexdigest() for p in modified},
    'protected_files': protected, 'changed_protected': changed,
    'copied_probe_sha256': copied,
    'review_probe_sha256': hashlib.sha256(probe.read_bytes()).hexdigest(),
}, indent=2), encoding='utf-8')
(OUT / 'release-results.json').write_text(json.dumps(results, indent=2), encoding='utf-8')
assert all(value == 0 for name,value in results.items() if isinstance(value,int) and name != 'protected_unchanged'), results
print(json.dumps(results, indent=2))
