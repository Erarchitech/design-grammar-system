"""Real PowerShell contracts only, never Docker or services."""
from pathlib import Path
import shutil
import subprocess
import unittest

HERE = Path(__file__).resolve().parents[1]
RUNNER = HERE / 'recovery-test/execution.ps1'
PS = shutil.which('powershell.exe')


def quote(value):
    return "'" + str(value).replace("'", "''") + "'"


class ExecutionTests(unittest.TestCase):
    def helper(self, code):
        self.assertTrue(RUNNER.is_file(), 'recovery execution missing')
        script = "$ErrorActionPreference='Stop';Set-StrictMode -Version Latest;"
        script += f". {quote(HERE/'image-runtime/runtime-execution.ps1')}; . {quote(RUNNER)};"
        script += "function Assert-True($v){if(-not $v){throw 'assertion'}};" + code
        return subprocess.run([PS, '-NoProfile','-NonInteractive','-Command',script],capture_output=True,text=True,errors='replace',timeout=30)

    def test_command_scope_cannot_escape_owned_projects(self):
        for bad in ('existing', 'dg-image-'+'a'*32, 'dg-recovery-'+'A'*32):
            self.assertNotEqual(self.helper(f"Assert-RecoveryName '{bad}'").returncode, 0)
        self.assertEqual(self.helper("Assert-RecoveryName ('dg-recovery-'+('a'*32))").returncode, 0)

    def test_source_destination_must_differ(self):
        self.assertNotEqual(self.helper("Assert-RecoveryPair ('dg-recovery-'+('a'*32)) ('dg-recovery-'+('a'*32))").returncode, 0)
        self.assertEqual(self.helper("Assert-RecoveryPair ('dg-recovery-'+('a'*32)) ('dg-recovery-'+('b'*32))").returncode, 0)

    def test_stopped_requires_exact_false_and_identity(self):
        setup = "$c=@{Project=('dg-recovery-'+('a'*32));Images=[pscustomobject]@{neo4j='sha256:abc'}};"
        for running in ('$true', '$null', "'false'"):
            self.assertNotEqual(self.helper(setup+f"Assert-RecoveryStoppedRecord ([pscustomobject]@{{Running={running};Project=$c.Project;Owner='neo4j';Image='sha256:abc'}}) $c 'neo4j'").returncode,0)
        self.assertEqual(self.helper(setup+"Assert-RecoveryStoppedRecord ([pscustomobject]@{Running=$false;Project=$c.Project;Owner='neo4j';Image='sha256:abc'}) $c 'neo4j'").returncode,0)

    def test_real_ownership_accepts_four_distinct_project_volume_names(self):
        setup = r'''
$p='dg-recovery-'+('a'*32)
$c=@{Project=$p;Images=[pscustomobject]@{'graph-admin'='sha256:abc'}}
function Get-IsolatedResources {return @{containers=@('c');networks=@();volumes=@('v')}}
function Invoke-RecoveryDocker {param($ctx,$cmd)
 if($cmd[0] -ceq 'container'){
  return (@{Name='/'+$p+'-graph-admin-1';Owner='graph-admin';Project=$p;Image='sha256:abc';Mounts=@(@{Type='volume';Name=$p+'_'+$script:suffix})}|ConvertTo-Json -Depth 5 -Compress)
 }
 return (@{Name=$p+'_'+$script:suffix;Owner=$script:suffix;Project=$p}|ConvertTo-Json -Compress)
}
'''
        for suffix in ('graph', 'graph_logs', 'api_state', 'exchange', 'foreign'):
            result = self.helper(setup + f"$script:suffix={quote(suffix)};[void](Assert-RecoveryOwnership $c)")
            if suffix == 'foreign':
                self.assertNotEqual(result.returncode, 0)
            else:
                self.assertEqual(result.returncode, 0, result.stderr)

    def test_launcher_persists_real_child_exit(self):
        import tempfile
        script = HERE / 'recovery-test/Invoke-OwnerRecovery.ps1'
        self.assertTrue(script.is_file(), 'exit-preserving owner launcher missing')
        with tempfile.TemporaryDirectory(dir='C:/Users/Admin/AppData/Local/hermes/cache/scratch') as tmp:
            root = Path(tmp)
            child = root / 'fake.ps1'
            child.write_text("param($PackageZip,$ExpectedZipSha256,$OutputDirectory,[switch]$RunRecovery)\nNew-Item -ItemType Directory -Path $OutputDirectory|Out-Null\nexit 7\n")
            out = root / 'out'
            result = subprocess.run([PS, '-NoProfile', '-NonInteractive', '-File', str(script),
                '-Runner', str(child), '-PackageZip', str(root/'synthetic.zip'), '-ExpectedZipSha256','a'*64,
                '-OutputDirectory', str(out)], capture_output=True,text=True,errors='replace',timeout=30)
            self.assertEqual(result.returncode,7,result.stdout+result.stderr)
            import json
            value = json.loads((out/'process-exit.json').read_bytes())
            self.assertEqual(value['processExitCode'],7)
            self.assertFalse(value['runtimeAccepted'])

    def test_lifecycle_order_failure_and_owned_cleanup(self):
        import json
        import tempfile
        with tempfile.TemporaryDirectory(dir='C:/Users/Admin/AppData/Local/hermes/cache/scratch') as tmp:
            setup = r'''
function Assert-IsolatedRuntimeGuard {}
function Assert-IsolatedLocalStorage {}
function Assert-IsolatedDaemon {}
function Confirm-IsolatedImage {}
function Assert-RecoveryModel {}
function Assert-RecoveryVacant {}
function Assert-RecoveryOwnership {param($c) $script:calls.Add('ownership');if($script:badOwnership){throw 'fixture'} }
function Assert-RecoveryStopped {param($c,$s) $script:calls.Add(($c.Compose+':stopped '+$s))}
function Wait-RecoveryReady {}
function Get-RecoveryContainer {return ('a'*64)}
function Get-Hash {return ('f'*64)}
function Assert-RegularPath {}
function Invoke-RecoveryDocker {param($c,$cmd,$seconds,$limit)
 $script:calls.Add(($c.Compose+':docker '+($cmd-join ' ')))
 if($cmd[0] -eq 'cp' -and $cmd[1].Contains(':/exchange/')){[IO.File]::WriteAllBytes($cmd[2],(New-Object byte[] 64))}
 return '{}'
}
function Invoke-RecoveryCompose {param($c,$cmd,$seconds,$limit)
 $text=$cmd-join ' ';$script:calls.Add(($c.Compose+':'+$text))
 if($script:failure -and $text.Contains($script:failure)){$script:badOwnership=($script:failure -ceq 'up --detach');throw 'fixture'}
 if($cmd[-1] -cin @('seed','verify')){
 $v=[ordered]@{admin_login=$true;csrf_denied=$true;user_login=$true;membership_restored=$true;project_isolation=$true;revoked_session_denied=$true;llm_settings_decrypted=$true;projects_created=2;authenticated_ingests=2;neo4j_scoped_notes=2}
 if($cmd[-1] -ceq 'verify'){foreach($k in @('csrf_denied','projects_created','authenticated_ingests')){$v['seed_'+$k]=$v[$k];$v.Remove($k)}}
 return ($v|ConvertTo-Json -Compress)
 }
 if($text.Contains('import hashlib')){return ('f'*64)}
 return '{}'
}
$script:calls=New-Object 'Collections.Generic.List[string]'
$j=[pscustomobject]@{images=[pscustomobject]@{neo4j=('sha256:'+('a'*64));'data-service'=('sha256:'+('b'*64))};files=[pscustomobject]@{};sourceRevision=('c'*40)}
$r=[ordered]@{status='FAILED';failureStage=$null;dockerInvoked=$false;checks=[ordered]@{};cleanup='not-started'}
'''
            for index, failure in enumerate(('', 'database dump', 'check-negative', 'database load', '--volumes', 'up --detach')):
                out = Path(tmp) / str(index)
                out.mkdir()
                result = self.helper(setup + f"$script:failure={quote(failure)};$script:badOwnership=$false;"
                    f"try{{Invoke-RecoveryExercise {quote(tmp)} {quote(out)} $j $r}}catch{{}};"
                    "@{report=$r;calls=@($script:calls)}|ConvertTo-Json -Depth 15 -Compress")
                self.assertEqual(result.returncode, 0, result.stderr)
                data = json.loads(result.stdout)
                calls, report = data['calls'], data['report']
                if failure:
                    self.assertEqual(report['status'], 'FAILED')
                    self.assertIsNotNone(report['failureStage'])
                else:
                    self.assertEqual(report['status'], 'TWO_STORE_RECOVERY_COMPLETE')
                    def at(needle):
                        return next(i for i, text in enumerate(calls) if needle in text)
                    self.assertLess(at('source-compose.json:stopped neo4j'), at('database dump'))
                    self.assertLess(at('source-compose.json:stopped snapshot'), at('destination-compose.json:up'))
                    self.assertLess(at('check-negative'), at('recovery_snapshot.py open'))
                    self.assertLess(at('recovery_snapshot.py open'), at('database load'))
                    self.assertLess(at('database load'), at('destination-compose.json:up --detach --no-build --pull never neo4j data-service'))
                    self.assertTrue(report['checks']['cleanupVerified'])
                if failure == '--volumes':
                    self.assertEqual(report['cleanup'], 'FAILED')
                if failure == 'up --detach':
                    self.assertEqual(report['failureStage'], 'source-start')
                    self.assertEqual(report['cleanup'], 'FAILED')
                    self.assertEqual(report['cleanupFailureStage'], 'ownership')
                    self.assertFalse(any('down --volumes' in c for c in calls))
                else:
                    self.assertTrue(any('down --volumes --remove-orphans' in c for c in calls))

    def test_guard_failure_never_claims_cleanup(self):
        import json
        result = self.helper("function Assert-IsolatedRuntimeGuard {throw 'fixture guard'};"
            "function Invoke-IsolatedDocker {throw 'UNEXPECTED_DOCKER'};"
            "$r=[ordered]@{status='FAILED';failureStage=$null;dockerInvoked=$false;checks=[ordered]@{};cleanup='not-started'};"
            "try{Invoke-RecoveryExercise 'C:\\unused' 'C:\\unused2' $null $r}catch{};"
            "$r|ConvertTo-Json -Depth 10 -Compress")
        self.assertEqual(result.returncode, 0, result.stderr)
        report = json.loads(result.stdout)
        self.assertEqual(report['failureStage'], 'runtime-guard')
        self.assertEqual(report['cleanup'], 'not-started')
        self.assertFalse(report['checks']['cleanupVerified'])
        self.assertFalse(report['dockerInvoked'])

    def test_probe_report_is_exact_typed_allowlist(self):
        import json
        valid = dict.fromkeys(('admin_login', 'csrf_denied', 'user_login', 'membership_restored',
            'project_isolation', 'revoked_session_denied', 'llm_settings_decrypted'), True)
        valid.update(seed_projects_created=2, seed_authenticated_ingests=2, neo4j_scoped_notes=2)
        valid['seed_csrf_denied'] = valid.pop('csrf_denied')
        def check(value):
            return self.helper(f"$v={quote(json.dumps(value))}|ConvertFrom-Json; Confirm-RecoveryProbe $v 'verify'|ConvertTo-Json -Compress")
        good = check(valid)
        self.assertEqual(good.returncode, 0, good.stderr)
        self.assertEqual(json.loads(good.stdout), valid)
        for value in ({}, dict(valid, secret='synthetic-private'), dict(valid, user_login=1),
                      dict(valid, neo4j_scoped_notes=True), dict(valid, projects_created=0),
                      dict(valid, revoked_session_denied=False)):
            with self.subTest(keys=list(value)):
                self.assertNotEqual(check(value).returncode, 0)

    def test_ciphertext_copy_restricted_name(self):
        self.assertEqual(self.helper("Assert-RecoveryCipherName 'backup.enc'").returncode,0)
        for bad in ('probe-state.json','neo4j.dump','../backup.enc','key.pem'):
            self.assertNotEqual(self.helper(f"Assert-RecoveryCipherName '{bad}'").returncode,0)


if __name__ == '__main__':
    unittest.main()
