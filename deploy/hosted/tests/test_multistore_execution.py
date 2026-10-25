"""Actual PS5 guard tests with synthetic children; NEVER invokes Docker."""
from pathlib import Path
import json
import os
import shutil
import subprocess
import tempfile
import unittest

HERE = Path(__file__).resolve().parents[1]
MODULE = HERE / 'recovery-test/multistore_execution.ps1'
CORE = HERE / 'image-runtime/runtime-execution.ps1'
SCRATCH = Path('C:/Users/Admin/AppData/Local/hermes/cache/scratch')
PS = shutil.which('powershell.exe')


def q(value):
    return "'" + str(value).replace("'", "''") + "'"


class MultiExecutionTests(unittest.TestCase):
    def run_ps(self, code, timeout=35, env=None):
        self.assertTrue(MODULE.is_file(), 'trusted multi-store execution module absent')
        self.assertTrue(PS, 'Windows PowerShell 5.1 is required')
        script = "$ErrorActionPreference='Stop';Set-StrictMode -Version Latest;"
        script += f". {q(CORE)};. {q(MODULE)};" + code
        return subprocess.run([PS, '-NoProfile', '-NonInteractive', '-Command', script],
                              capture_output=True, text=True, errors='replace', timeout=timeout, env=env)

    def test_module_exists_and_parses(self):
        r = self.run_ps("'parsed'")
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertEqual(r.stdout.strip(), 'parsed')

    def test_scope_requires_exact_target_unexpired_issued_authorization(self):
        setup = "$s=[pscustomobject]@{schemaVersion=1;target='DESKTOP-OS4Q8CP';kind='one-synthetic-multistore-exercise';packageSha256=('a'*64);approvalReference='owner-issued-test';expiresAtUtc=[datetime]::UtcNow.AddHours(1).ToString('o');maxSeconds=5400;maxCommands=500;network='internal-no-published-ports';data='new-synthetic-volumes-only';daemonState='already-running-no-start-stop';cleanup='owned-resources-only'};"
        good = setup + "Assert-MultiScope $s 'DESKTOP-OS4Q8CP' ('a'*64) ([datetime]::UtcNow)"
        self.assertEqual(self.run_ps(good).returncode, 0)
        mutations = ["$s.target='OTHER'", "$s.expiresAtUtc=[datetime]::UtcNow.AddMinutes(-1).ToString('o')",
                     "$s.packageSha256=('b'*64)", "$s.maxCommands=$true", "$s.maxSeconds=5401",
                     "$s.network='public'", "$s.approvalReference=''", "$s.schemaVersion=$true",
                     "$s|Add-Member extra 'ignored'", "$s.data='owner-volumes'", "$s.daemonState='start-if-needed'"]
        for mutation in mutations:
            r = self.run_ps(setup + mutation + ";Assert-MultiScope $s 'DESKTOP-OS4Q8CP' ('a'*64) ([datetime]::UtcNow)")
            self.assertNotEqual(r.returncode, 0, mutation)

    def test_running_identity_requires_exact_image_project_service_and_state(self):
        setup = "$c=@{Project=('dg-multi-'+('a'*32));Images=@{postgres=('sha256:'+('b'*64))}};$r=[pscustomobject]@{Id=('c'*64);Image=('sha256:'+('b'*64));Project=$c.Project;Service='postgres';Running=$false};"
        self.assertEqual(self.run_ps(setup + "Assert-MultiContainerRecord $c 'postgres' $r $false").returncode, 0)
        for mutation in ["$r.Running='false'", "$r.Running=$null", "$r.Running=$true", "$r.Image='tag:latest'",
                         "$r.Project='foreign'", "$r.Service='n8n'", "$r.Id='short'", "$r|Add-Member Extra $true"]:
            self.assertNotEqual(self.run_ps(setup + mutation + ";Assert-MultiContainerRecord $c 'postgres' $r $false").returncode, 0, mutation)

    def test_project_pair_and_command_budget_fail_closed(self):
        good = "Assert-MultiPair ('dg-multi-'+('a'*32)) ('dg-multi-'+('b'*32));$c=@{Commands=0;MaxCommands=1;Deadline=[datetime]::UtcNow.AddMinutes(2)};Use-MultiBudget $c;"
        self.assertEqual(self.run_ps(good).returncode, 0)
        self.assertNotEqual(self.run_ps(good + 'Use-MultiBudget $c').returncode, 0)
        self.assertNotEqual(self.run_ps("Assert-MultiPair ('dg-multi-'+('a'*32)) ('dg-multi-'+('a'*32))").returncode, 0)
        self.assertNotEqual(self.run_ps("Assert-MultiPair 'owner' ('dg-multi-'+('a'*32))").returncode, 0)
        self.assertNotEqual(self.run_ps("$c=@{Commands=0;MaxCommands=5;Deadline=[datetime]::UtcNow.AddSeconds(-1)};Use-MultiBudget $c").returncode, 0)

    def test_child_environment_is_cleared_not_just_docker_keys(self):
        with tempfile.TemporaryDirectory(dir=SCRATCH) as tmp:
            child = Path(tmp) / 'environment.ps1'
            child.write_text("if($env:OWNER_SENTINEL -or $env:AWS_SECRET_ACCESS_KEY -or $env:DOCKER_CONTEXT){exit 9};if($env:DG_SYNTHETIC -cne 'safe'){exit 8};[Console]::Write('safe');exit 0", encoding='utf-8')
            env = dict(os.environ, OWNER_SENTINEL='private-test', AWS_SECRET_ACCESS_KEY='private-test', DOCKER_CONTEXT='owner-test')
            code = f"$e=@{{SystemRoot=$env:SystemRoot;DG_SYNTHETIC='safe'}};$r=Invoke-MultiProcess {q(PS)} @('-NoProfile','-NonInteractive','-File',{q(child)}) {q(tmp)} $e 5 ([datetime]::UtcNow.AddMinutes(1)) 1024;$r|ConvertTo-Json -Compress"
            r = self.run_ps(code, env=env)
            self.assertEqual(r.returncode, 0, r.stderr)
            self.assertEqual(json.loads(r.stdout), {'Code': 0, 'Text': 'safe'})

    def test_real_child_timeout_nonzero_and_output_overflow_sanitized(self):
        with tempfile.TemporaryDirectory(dir=SCRATCH) as tmp:
            for name, body, seconds, cap in [('bad', "[Console]::Error.Write('private-canary');exit 7", 5, 100),
                                               ('large', "[Console]::Write(('x'*2000));exit 0", 5, 32),
                                               ('slow', 'Start-Sleep -Seconds 20;exit 0', 1, 32)]:
                p = Path(tmp) / (name + '.ps1');p.write_text(body)
                r = self.run_ps(f"$e=@{{SystemRoot=$env:SystemRoot}};try{{[void](Invoke-MultiProcess {q(PS)} @('-NoProfile','-NonInteractive','-File',{q(p)}) {q(tmp)} $e {seconds} ([datetime]::UtcNow.AddMinutes(1)) {cap});throw 'unexpected'}}catch{{if($_.Exception.Message -cne 'multi-store command rejected'){{throw}};'denied'}}")
                self.assertEqual(r.returncode, 0, r.stderr)
                self.assertEqual(r.stdout.strip(), 'denied')
                self.assertNotIn('private-canary', r.stdout + r.stderr)

    def test_resource_ownership_refuses_foreign_volume_consumers_before_cleanup(self):
        setup = r'''
$p='dg-multi-'+('a'*32)
$c=@{Project=$p;Images=@{snapshot=('sha256:'+('b'*64))};Volumes=@('exchange');Services=@('snapshot')}
function Get-MultiResources {return @{containers=@(('c'*64));networks=@();volumes=@($p+'_exchange')}}
function Invoke-MultiDocker {param($context,$command)
 if($command[0] -ceq 'container' -and $command[1] -ceq 'inspect'){
  return (@{Id=('c'*64);Name=('/'+$p+'-snapshot-1');Image=('sha256:'+('b'*64));Project=$p;Service='snapshot';Mounts=@(@{Type='volume';Name=($p+'_exchange');Destination='/exchange'})}|ConvertTo-Json -Depth 5 -Compress)
 }
 if($command[0] -ceq 'volume' -and $command[1] -ceq 'inspect'){
  return (@{Name=($p+'_exchange');Project=$p;Owner='exchange'}|ConvertTo-Json -Compress)
 }
 if($command[0] -ceq 'container' -and $command[1] -ceq 'ls'){return $script:consumer}
 throw 'unexpected'
}
'''
        good = self.run_ps(setup + "$script:consumer=('c'*64);[void](Assert-MultiOwnership $c)")
        self.assertEqual(good.returncode, 0, good.stderr)
        for consumer in ("('d'*64)", "(('c'*64)+\"`n\"+('d'*64))"):
            bad = self.run_ps(setup + "$script:consumer=" + consumer + ";[void](Assert-MultiOwnership $c)")
            self.assertNotEqual(bad.returncode, 0)

    def test_cleanup_keeps_primary_failure_and_never_down_after_ownership_denial(self):
        setup = r'''
$script:commands=New-Object 'Collections.Generic.List[string]'
$c=@{Project=('dg-multi-'+('a'*32));Deadline=[datetime]::UtcNow;CleanupActivated=$true}
$r=[ordered]@{failureStage='native-export';cleanup='not-started';cleanupFailureStage=$null}
function Assert-MultiOwnership {param($c) if($script:denied){throw 'foreign'} }
function Invoke-MultiCompose {param($c,$cmd) $script:commands.Add(($cmd -join ' '));if($script:failDown){throw 'failed'} }
function Assert-MultiVacant {param($c) $script:commands.Add('vacant')}
'''
        for denied, fail_down in ((False,False),(True,False),(False,True)):
            r=self.run_ps(setup+f"$script:denied=${str(denied).lower()};$script:failDown=${str(fail_down).lower()};Complete-MultiCleanup @($c) $r;@{{report=$r;commands=@($script:commands)}}|ConvertTo-Json -Depth 5 -Compress")
            self.assertEqual(r.returncode,0,r.stderr);data=json.loads(r.stdout)
            self.assertEqual(data['report']['failureStage'],'native-export')
            if denied:
                self.assertEqual(data['commands'],[])
                self.assertEqual(data['report']['cleanupFailureStage'],'ownership')
            if denied or fail_down:
                self.assertEqual(data['report']['cleanup'],'FAILED')
            else:
                self.assertEqual(data['report']['cleanup'],'owned-projects-volumes-removed')
                self.assertIn('vacant',data['commands'])

    def test_source_and_destination_share_one_exercise_command_budget(self):
        code=r'''
$b=@{Commands=0;MaxCommands=2;Deadline=[datetime]::UtcNow.AddMinutes(2)}
$a=@{Commands=0;MaxCommands=500;Deadline=$b.Deadline;SharedBudget=$b}
$c=@{Commands=0;MaxCommands=500;Deadline=$b.Deadline;SharedBudget=$b}
Use-MultiBudget $a;Use-MultiBudget $c
try {Use-MultiBudget $a;throw 'unexpected'}catch{if($_.Exception.Message -ceq 'unexpected'){throw}}
if($b.Commands -ne 2 -or $a.Commands -ne 1 -or $c.Commands -ne 1){throw 'not shared'}
[Console]::Write('budget-shared')
'''
        result=self.run_ps(code)
        self.assertEqual(result.returncode,0,result.stderr)

    def test_full_two_project_cleanup_has_enough_shared_command_allowance(self):
        code=r'''
$c=@{Project=('dg-multi-'+('a'*32));Deadline=[datetime]::UtcNow;CleanupActivated=$true;Commands=0;MaxCommands=500}
$d=@{Project=('dg-multi-'+('b'*32));Deadline=[datetime]::UtcNow;CleanupActivated=$true;Commands=0;MaxCommands=500}
$r=[ordered]@{failureStage='export';cleanup='not-started';cleanupFailureStage=$null}
function Assert-MultiOwnership {param($c) for($i=0;$i -lt 39;$i++){Use-MultiBudget $c}}
function Invoke-MultiCompose {param($c,$cmd) Use-MultiBudget $c}
function Assert-MultiVacant {param($c) for($i=0;$i -lt 13;$i++){Use-MultiBudget $c}}
Complete-MultiCleanup @($c,$d) $r
if($r.cleanup -cne 'owned-projects-volumes-removed'){throw 'insufficient shared cleanup allowance'}
if(($c.Commands+$d.Commands) -gt 160){throw 'over cleanup limit'}
'''
        result=self.run_ps(code)
        self.assertEqual(result.returncode,0,result.stderr)

    def test_cleanup_has_separate_shared_budget_but_never_exceeds_total_bound(self):
        code=r'''
$c=@{Project=('dg-multi-'+('a'*32));Deadline=[datetime]::UtcNow;CleanupActivated=$true;Commands=500;MaxCommands=500}
$r=[ordered]@{failureStage='budget';cleanup='not-started';cleanupFailureStage=$null}
function Assert-MultiOwnership {param($c) Use-MultiBudget $c}
function Invoke-MultiCompose {param($c,$cmd) Use-MultiBudget $c}
function Assert-MultiVacant {param($c) Use-MultiBudget $c}
Complete-MultiCleanup @($c) $r
@{report=$r;commands=$c.Commands;maxCommands=$c.MaxCommands}|ConvertTo-Json -Depth 5 -Compress
'''
        result=self.run_ps(code)
        self.assertEqual(result.returncode,0,result.stderr)
        actual=json.loads(result.stdout)
        self.assertEqual(actual['report']['cleanup'],'owned-projects-volumes-removed')
        self.assertLessEqual(actual['commands'],160)
        self.assertEqual(actual['maxCommands'],160)

    def test_normalized_model_rejects_port_environment_mount_and_command_drift(self):
        import importlib.util
        import sys
        sys.path.insert(0,str(HERE));self.addCleanup(lambda:sys.path.remove(str(HERE)))
        import build_multistore_test as builder
        model=builder.native_model()
        project='dg-multi-'+'a'*32
        # Deliberately model Compose's documented empty/default normalization;
        # this is admission-unit evidence, not actual Compose qualification.
        normalized=json.loads(json.dumps(model))
        normalized['name']=project
        normalized['networks']['sandbox']['name']=project+'_sandbox'
        normalized['networks']['sandbox']['ipam']={}
        for name,v in normalized['volumes'].items():v['name']=project+'_'+name
        with tempfile.TemporaryDirectory(dir=SCRATCH) as tmp:
            root=Path(tmp);(root/'source-compose.json').write_text(json.dumps(model))
            for name,service in normalized['services'].items():
                service.setdefault('command',None);service.setdefault('entrypoint',None)
                if 'healthcheck' in service:
                    service['healthcheck']['test']=[x.replace('$$','$') for x in service['healthcheck']['test']]
                if 'networks' in service:service['networks']={'sandbox':None}
                for dep in service.get('depends_on',{}).values():dep['required']=True
                for mount in service.get('volumes',[]):
                    if mount['type']=='bind':mount['source']=str(root/mount['source'][2:])
            path=root/'normalized.json';path.write_text(json.dumps(normalized))
            code=f"$c=@{{Project='{project}';Root={q(root)};Compose='source-compose.json';Environment=@{{}}}};$v=Get-Content -LiteralPath {q(path)} -Raw|ConvertFrom-Json;Assert-MultiModel $v $c"
            debug=code.replace(';Assert-MultiModel $v $c',";try{Assert-MultiModel $v $c}catch{[Console]::Error.WriteLine($_.ScriptStackTrace);throw}")
            initial=self.run_ps(debug,timeout=35)
            self.assertEqual(initial.returncode,0,initial.stderr)
            mutations=["$v.services.neo4j|Add-Member ports @('7474:7474')", "$v.services.n8n.environment.EXECUTIONS_MODE='queue'",
                       "$v.services.snapshot.volumes[0].read_only=$false", "$v.services.neo4j.entrypoint=@()",
                       "$v.networks.sandbox.internal=$false", "$v.services.'data-service'.image='latest'",
                       "$v.services.snapshot.volumes[3].source='C:\\owner-data'",
                       "$v.services.'speckle-postgres'.volumes[0].source='foreign'"]
            base=code[:code.index(';Assert-MultiModel')]
            for mutation in mutations:
                r=self.run_ps(base+';'+mutation+';Assert-MultiModel $v $c')
                self.assertNotEqual(r.returncode,0,mutation)

    def test_native_argv_fixed_endpoint_and_private_compose_config(self):
        code = "$c=@{Config='C:\\private\\base';ComposeConfig='C:\\private\\compose';Root='C:\\bundle';Project=('dg-multi-'+('a'*32));Compose='source-compose.json'};@{a=@(Get-MultiArguments $c @('version'));b=@(Get-MultiArguments $c @('compose','version','--short'));d=@(Get-MultiComposeArguments $c @('up','--detach'))}|ConvertTo-Json -Depth 5 -Compress"
        r = self.run_ps(code);self.assertEqual(r.returncode, 0, r.stderr);d = json.loads(r.stdout)
        for key in ('a', 'b', 'd'):
            self.assertEqual(d[key][:2], ['--host', 'npipe:////./pipe/docker_engine'])
        self.assertEqual(d['a'][3], 'C:\\private\\base')
        self.assertEqual(d['b'][3], 'C:\\private\\compose')
        self.assertIn('--env-file', d['d'])
        self.assertIn('--project-name', d['d'])


if __name__ == '__main__':
    unittest.main()
