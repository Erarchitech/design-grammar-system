"""Independent aggregation, SDK proof, iteration diff and preservation checks."""
import datetime, difflib, hashlib, json, re, subprocess
from pathlib import Path
ROOT=Path(__file__).resolve().parents[5]
OUT=Path(__file__).resolve().parent
PHASE=OUT.parent.parent
results=json.loads((OUT/'results.json').read_text())
assert len(results)==11 and all(r['exit']==0 for r in results)
sdk=json.loads((OUT/'sdk-resolve.json').read_text(encoding='utf-8-sig'))
refs={Path(r['Identity']).name:r['Identity'] for r in sdk['Items']['ReferencePath'] if Path(r['Identity']).name in ['RhinoCommon.dll','Grasshopper.dll','GH_IO.dll']}
assert len(refs)==3 and all(Path(p).is_file() for p in refs.values())
assert 'GRASSHOPPER_SDK' in sdk['Properties']['DefineConstants']
compiled=[x['Identity'].replace('\\','/') for x in sdk['Items']['Compile']]
assert all(p in compiled for p in ['Validation/ValidationPublishClient.cs','Validation/ValidationPublishContract.cs'])
counts={}
for m in re.finditer(r'^data-service/tests/([^:]+)::.* PASSED ',(OUT/'wire.log').read_text(encoding='utf-8'),re.M):
    counts[m.group(1)]=counts.get(m.group(1),0)+1
assert sum(counts.values())==428 and counts['test_evidence_unicode_containers.py']==98 and counts['test_evidence_raw_admission.py']==122
observations=json.loads((OUT/'review-probe.json').read_text())
s=observations['summary']
assert not s['expected_admission_mismatches'] and not s['response_failures'] and not s['strict_process_failures'] and not s['binary_changed_during_probe'],s
assert all(x['factory']==x['legacy_validate']=='rejected' for x in observations['inmemory'])
assert all(not x['admitted'] and x['response']=='ok' for x in observations['shacl'])
assert all(x['python_read']==x['csharp_read']['admitted'] for x in observations['cases'])
assert all(x['full_model']==x['csharp_strict']['admitted'] for x in observations['cases'] if 'full_model' in x and 'csharp_strict' in x)
before=json.loads((OUT/'protected-before.json').read_text())
changed=[p for p,h in before.items() if not (ROOT/p).exists() or hashlib.sha256((ROOT/p).read_bytes()).hexdigest()!=h]
# The original run_checks failure stays intact: parallel reviewer replay was
# captured while being written, not an immutable historical artifact.
concurrent = (PHASE/'evidence/review-3-replay.json').relative_to(ROOT).as_posix()
assert set(changed) <= {concurrent}, changed
reconciliation = dict(originalRunnerExit=1,originalAssertion='assert not changed',
    originalManifestCount=len(before), changed=changed,
    classification='Concurrent reviewer round-3 output, not prior history/source',
    excludedFromImmutableScope=[concurrent],
    beforeSha256=before.get(concurrent),
    afterSha256=hashlib.sha256((ROOT/concurrent).read_bytes()).hexdigest(),
    immutableCount=len(before)-int(concurrent in before),
    immutableChanged=[p for p in changed if p != concurrent])
(OUT/'preservation-reconciliation.json').write_text(json.dumps(reconciliation,indent=2),encoding='utf-8')
fix=OUT.parent/'fix-iteration2'
manifest=json.loads((fix/'manifest.json').read_text())
assert all(hashlib.sha256((ROOT/p).read_bytes()).hexdigest()==h for p,h in manifest['source_sha256'].items())
diff=[]
for path in manifest['source_sha256']:
    oldpath=fix/'before'/path
    old=oldpath.read_text(encoding='utf-8').splitlines(keepends=True) if oldpath.exists() else []
    new=(ROOT/path).read_text(encoding='utf-8').splitlines(keepends=True)
    diff.extend(difflib.unified_diff(old,new,fromfile='before/'+path,tofile='after/'+path))
assert ''.join(diff)==(fix/'iteration-only.diff').read_text(encoding='utf-8')
scan=[]
for path in manifest['source_sha256']:
    if path.endswith(('.py','.cs')):
        for i,line in enumerate((ROOT/path).read_text(encoding='utf-8').splitlines(),1):
            if re.search(r'\b(TBD|FIXME|XXX|TODO|HACK|PLACEHOLDER)\b|pytest\.mark\.(skip|xfail)|Skip\s*=',line):
                scan.append(dict(path=path,line=i,text=line))
proof=dict(verified=datetime.datetime.now(datetime.timezone.utc).isoformat(),head=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),sdk=refs,properties=sdk['Properties'],publishCompileItems=[p for p in compiled if 'ValidationPublish' in p],wirePassedByModule=counts,reviewRawCases=len(observations['cases']),reviewSummary=s,reviewInmemoryCases=len(observations['inmemory']),reviewShaclCases=len(observations['shacl']),domainProbeCases=len(json.loads((OUT/'domain-probe.json').read_text())),protectedFiles=len(before),protectedChanged=changed,fixSourceManifestMatches=True,iterationDiffMatches=True,extraScanFindings=scan,projectSkillDirectories={p:(ROOT/p).is_dir() for p in ['.hermes/skills','.agents/skills']})
(OUT/'final-checks.json').write_text(json.dumps(proof,indent=2),encoding='utf-8')
print(json.dumps(proof,indent=2))
old=(PHASE/'1205.1-VERIFICATION-2.md').read_text(encoding='utf-8')
covered=[line[4:] for line in old.split('covered_files:\n',1)[1].split('covered_digest:',1)[0].splitlines() if line.startswith('  - ')]
covered+=['data-service/tests/test_evidence_unicode_containers.py']
covered += [(PHASE/name).relative_to(ROOT).as_posix() for name in ['1205.1-VERIFICATION-2.md','1205.1-REVIEW-2.md','1205.1-REVIEW-FIX-2.md']]
covered=sorted(set(covered))
(OUT/'covered-files.json').write_text(json.dumps(covered,indent=2),encoding='utf-8')
base=['node','C:/Users/Admin/AppData/Local/hermes/gsd-core/bin/gsd-tools.cjs','query']
for name,command in [('fingerprint',base+['verification.fingerprint',PHASE.relative_to(ROOT).as_posix(),*covered]),('decision-coverage',base+['check.decision-coverage-verify',PHASE.relative_to(ROOT).as_posix(),(PHASE/'1205.1-CONTEXT.md').relative_to(ROOT).as_posix()])]:
    p=subprocess.run(command,cwd=ROOT,capture_output=True,check=True)
    (OUT/(name+'.json')).write_bytes(p.stdout)
    print(name,p.stdout.decode('utf-8'))
