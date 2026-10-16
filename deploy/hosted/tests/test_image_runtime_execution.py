"""Offline contracts exercised by real Windows PowerShell 5.1 AST extraction.

These tests never start Docker. Synthetic models/command responses are explicitly
unit fixtures, not target-host runtime or archive evidence.
"""
import json
from pathlib import Path
import shutil
import subprocess
import unittest

HERE = Path(__file__).resolve().parents[1]
RUNNER = HERE / 'image-runtime/runtime-execution.ps1'
PS = shutil.which('powershell.exe')


def quote(value):
    return "'" + str(value).replace("'", "''") + "'"


@unittest.skipUnless(PS, 'Windows PowerShell 5.1 required')
class ExecutionTests(unittest.TestCase):
    def helper(self, code):
        self.assertTrue(RUNNER.is_file(), 'runtime execution implementation missing')
        script = (
            "$ErrorActionPreference='Stop'; Set-StrictMode -Version Latest; "
            "if($PSVersionTable.PSVersion.Major -ne 5){throw 'PS5 required'}; "
            "$t=$null;$e=$null;"
            f"$ast=[Management.Automation.Language.Parser]::ParseFile({quote(RUNNER)},[ref]$t,[ref]$e);"
            "if($e.Count){throw ($e | Out-String)};"
            "$ast.FindAll({param($n) $n -is [Management.Automation.Language.FunctionDefinitionAst]},$false) | "
            "ForEach-Object { . ([scriptblock]::Create($_.Extent.Text)) };"
            "function Assert-True($v){if(-not $v){throw 'assertion failed'}};" + code
        )
        return subprocess.run([PS, '-NoProfile', '-NonInteractive', '-Command', script],
                              capture_output=True, text=True, errors='replace', timeout=45)

    def ok(self, code):
        result = self.helper(code)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        return result.stdout.strip()

    def test_guard_allows_only_named_host_without_overrides(self):
        self.ok("Assert-IsolatedRuntimeGuard 'DESKTOP-OS4Q8CP' @{}")
        for code in ["Assert-IsolatedRuntimeGuard 'OTHER' @{}"] + [
                f"Assert-IsolatedRuntimeGuard 'DESKTOP-OS4Q8CP' @{{{name}='override'}}"
                for name in ('DOCKER_HOST', 'DOCKER_CONTEXT', 'DOCKER_CONFIG', 'DOCKER_TLS_VERIFY',
                             'DOCKER_CERT_PATH', 'COMPOSE_FILE', 'COMPOSE_PROJECT_NAME', 'BUILDX_BUILDER')]:
            with self.subTest(code=code):
                self.assertNotEqual(self.helper(code).returncode, 0)

    def test_argument_prefix_and_compose_paths(self):
        output = self.ok("$c=@{Config='C:\\fresh\\docker-config';Root='C:\\pkg';Project='dg-image-'+('a'*32)}; "
                         "ConvertTo-Json -Compress -InputObject @(Get-IsolatedComposeArguments $c @('up','--detach','--no-build','--pull','never'))")
        args = json.loads(output)
        self.assertEqual(args[:4], ['--host', 'npipe:////./pipe/docker_engine', '--config', 'C:\\fresh\\docker-config'])
        self.assertIn('--project-name', args)
        self.assertIn('--env-file', args)
        self.assertIn('C:\\pkg\\support\\empty-env.txt', args)
        self.assertEqual(args[-5:], ['up', '--detach', '--no-build', '--pull', 'never'])

    def test_fixed_smoke_evidence_and_no_raw_passthrough(self):
        evidence = {'api': {'admin_login': True, 'csrf_denied': True, 'ingest_inserted': 1,
                            'neo4j_scoped_notes': 1, 'denied_paths': 4}, 'uiAssets': 2,
                    'uiHeaders': True, 'uiProxyTombstones': True, 'uiRuntimeConfig': True,
                    'reasonerNeo4jUp': True, 'selfRegistrationDisabled': True}
        code = f"$e={quote(json.dumps(evidence))}|ConvertFrom-Json; "
        actual = json.loads(self.ok(code + 'ConvertTo-Json -Compress -Depth 10 (Confirm-IsolatedSmokeEvidence $e)'))
        self.assertEqual(actual, evidence)
        for key in evidence:
            bad = dict(evidence)
            bad[key] = False if key != 'api' else {'admin_login': 'true'}
            with self.subTest(key=key):
                self.assertNotEqual(self.helper(f"Confirm-IsolatedSmokeEvidence ({quote(json.dumps(bad))}|ConvertFrom-Json)").returncode, 0)
        bad = dict(evidence, raw='SECRET_SENTINEL')
        result = self.helper(f"Confirm-IsolatedSmokeEvidence ({quote(json.dumps(bad))}|ConvertFrom-Json)")
        self.assertNotEqual(result.returncode, 0)
        self.assertNotIn('SECRET_SENTINEL', result.stdout + result.stderr)

    def test_daemon_minimum_and_image_revision(self):
        self.ok("Assert-IsolatedDaemon '{\"Server\":{\"Os\":\"linux\",\"Arch\":\"amd64\"}}' '{\"OSType\":\"linux\",\"Architecture\":\"x86_64\",\"MemTotal\":6442450944}' '2.24.4'")
        for version in ('2.24.3', '1.99.0', '2.24.4-rc.1', 'junk'):
            self.assertNotEqual(self.helper("Assert-IsolatedDaemon '{\"Server\":{\"Os\":\"linux\",\"Arch\":\"amd64\"}}' '{\"OSType\":\"linux\",\"Architecture\":\"x86_64\",\"MemTotal\":6442450944}' " + quote(version)).returncode, 0)
        image = {'Id': 'sha256:' + 'a'*64, 'Os': 'linux', 'Architecture': 'amd64', 'Revision': 'b'*40}
        self.ok(f"Confirm-IsolatedImage ({quote(json.dumps(image))}|ConvertFrom-Json) {quote(image['Id'])} {quote(image['Revision'])}")
        for field in image:
            bad = dict(image)
            bad[field] = 'wrong'
            self.assertNotEqual(self.helper(f"Confirm-IsolatedImage ({quote(json.dumps(bad))}|ConvertFrom-Json) {quote(image['Id'])} {quote(image['Revision'])}").returncode, 0)

    def test_lifecycle_success_and_fail_closed_cleanup(self):
        # Replace only OS/Docker boundaries, never execute actual runtime/Docker.
        setup = r'''
function Assert-IsolatedRuntimeGuard {}
function Assert-IsolatedLocalStorage {}
function Assert-RegularPath {}
function Get-Hash { return ('f'*64) }
function Assert-IsolatedDaemon {}
function Confirm-IsolatedImage {}
function Assert-IsolatedComposeModel {}
function Assert-IsolatedArchiveRetained {}
function Assert-IsolatedVacant {}
function New-IsolatedContext {param($Root,$Output,$Report) return @{Root=$Root;Config='unused';Project=('dg-image-'+('a'*32));Environment=@{};Deadline=[datetime]::UtcNow.AddMinutes(30)} }
$script:calls=New-Object 'Collections.Generic.List[string]'
function Get-IsolatedResources {param($Context) return @{containers=@();networks=@();volumes=@()} }
function Assert-IsolatedOwnership {param($Context) $script:calls.Add('ownership'); if($script:failOwnership){throw 'fixture ownership failure'};return @{containers=@('fixture');networks=@();volumes=@()} }
function Invoke-IsolatedDocker {param($Context,$Command,$Seconds,$Limit=0) $script:calls.Add(($Command -join ' ')); $text=if($Command[0] -eq 'image' -and $Command[3] -eq '{{.Id}}'){('sha256:'+('a'*64))}else{'{}'};return @{Code=0;Text=$text} }
function Invoke-IsolatedCompose {param($Context,$Command,$Seconds,$Limit=0)
 $script:calls.Add(($Command -join ' '))
 if($Command[0] -eq 'config' -and $script:failConfig){throw 'fixture config failure'}
 if($Command[0] -eq 'up' -and $script:failStart){return @{Code=1;Text=''}}
 if($Command[0] -eq 'config'){return @{Code=0;Text='{}'}}
 if($Command[0] -eq 'down' -and $script:failDown){throw 'fixture down failure'}
 if($Command[0] -eq 'exec' -and $Command[-1] -eq '/app/image_runtime_probe.py'){
 return @{Code=0;Text='{"api":{"admin_login":true,"csrf_denied":true,"ingest_inserted":1,"neo4j_scoped_notes":1,"denied_paths":4},"uiAssets":2,"uiHeaders":true,"uiProxyTombstones":true,"uiRuntimeConfig":true,"reasonerNeo4jUp":true,"selfRegistrationDisabled":true}'} }
 return @{Code=0;Text='2.24.4'}
}
$images=[ordered]@{};foreach($name in @('neo4j','dg-reasoner','data-service','design-grammars')){$images[$name]=@{imageId=('sha256:'+('a'*64));archive=($name+'.tar');archiveSha256=('f'*64);archiveBytes=1;tag='fixture:local'}}
$job=[pscustomobject]@{images=[pscustomobject]$images;sourceRevision=('b'*40)}
$report=[ordered]@{status='FAILED';failureStage=$null;dockerInvoked=$false;archiveBytesVerified=$true;checks=[ordered]@{};images=[ordered]@{};cleanup='not-started'}
'''
        for fail_down, fail_ownership, fail_start, fail_config in (
                (False, False, False, False), (True, False, False, False),
                (False, True, False, False), (False, False, True, False),
                (False, False, False, True)):
            code = setup + f"$script:failDown=${str(fail_down).lower()};$script:failOwnership=${str(fail_ownership).lower()};"
            code += f"$script:failStart=${str(fail_start).lower()};$script:failConfig=${str(fail_config).lower()};"
            code += "try {Invoke-IsolatedSmoke 'C:\\pkg' 'C:\\out' 'C:\\tar' $job $report} catch {};"
            code += "ConvertTo-Json -Compress -Depth 10 @{report=$report;calls=@($script:calls)}"
            data = json.loads(self.ok(code))
            if fail_start or fail_config:
                self.assertEqual(data['report']['status'], 'FAILED')
                self.assertEqual(data['report']['failureStage'], 'service-start' if fail_start else 'compose-config')
                self.assertEqual(data['report']['cleanup'], 'project-down-volumes-removed' if fail_start else 'not-started')
            elif not fail_down and not fail_ownership:
                self.assertEqual(data['report']['status'], 'LOAD_AND_ISOLATED_SMOKE_COMPLETE')
                self.assertEqual(data['report']['cleanup'], 'project-down-volumes-removed')
            else:
                self.assertEqual(data['report']['status'], 'FAILED')
                self.assertEqual(data['report']['failureStage'], 'cleanup')
                self.assertEqual(data['report']['cleanup'], 'FAILED')
            down = [call for call in data['calls'] if call.startswith('down ')]
            self.assertEqual(len(down), 0 if fail_ownership or fail_config else 1)
            self.assertEqual(sum(call.startswith('image load ') for call in data['calls']), 4)

    def test_vacancy_detects_all_resource_kinds(self):
        setup = r'''
$c=@{Project=('dg-image-'+('a'*32))}
function Invoke-IsolatedDocker {param($Context,$Command,$Seconds,$Limit) return @{Code=0;Text=$script:text} }
$script:text=''
'''
        self.ok(setup + 'Assert-IsolatedVacant $c')
        self.assertNotEqual(self.helper(setup + "$script:text='existing';Assert-IsolatedVacant $c").returncode, 0)
        self.ok(setup + "$script:text='one';$r=Get-IsolatedResources $c;Assert-True ($r.containers.Count -eq 1 -and $r.networks.Count -eq 1 -and $r.volumes.Count -eq 1)")

    def test_resource_memory_cannot_exceed_package_budget(self):
        self.ok("Assert-IsolatedMemory '1500m' 1500; Assert-IsolatedMemory 1572864000 1500")
        for value in ('999999999999', '2g', '0', '-1', 'oops'):
            self.assertNotEqual(self.helper(f"Assert-IsolatedMemory {quote(value)} 1500").returncode, 0)

    def test_ownership_exact_labels_and_resource_sets(self):
        setup = r'''
$project='dg-image-'+('a'*32)
$context=@{Project=$project;Images=[pscustomobject]@{neo4j=@{imageId=('sha256:'+('b'*64))}}}
function Get-IsolatedResources {param($Context) return @{containers=@('containerfixture');networks=@('networkfixture');volumes=@('volumefixture')} }
$script:items=@{
 containerfixture=@{Name=('/'+$project+'-neo4j-1');Project=$project;Owner='neo4j';Number='1';Oneoff='False';Image=('sha256:'+('b'*64));Mounts=@(@{Type='volume';Name=($project+'_graph');Destination='/data'},@{Type='volume';Name=('c'*64);Destination='/logs'})};
 networkfixture=@{Name=($project+'_sandbox');Project=$project;Owner='sandbox'};
 volumefixture=@{Name=($project+'_graph');Project=$project;Owner='graph'}
}
function Invoke-IsolatedDocker {param($Context,$Command,$Seconds,$Limit) return @{Code=0;Text=($script:items[$Command[-1]]|ConvertTo-Json -Compress)} }
'''
        self.ok(setup + "$r=Assert-IsolatedOwnership $context; Assert-True ($r.anonymousVolumes.Count -eq 1 -and $r.anonymousVolumes[0] -ceq ('c'*64))")
        for mutation in ("$script:items.containerfixture.Project='foreign'",
                         "$script:items.containerfixture.Owner='unknown'",
                         "$script:items.containerfixture.Oneoff='True'",
                         "$script:items.containerfixture.Image='sha256:wrong'",
                         "$script:items.networkfixture.Name='foreign'",
                         "$script:items.volumefixture.Owner='foreign'"):
            self.assertNotEqual(self.helper(setup + mutation + '; Assert-IsolatedOwnership $context').returncode, 0)

    def test_runtime_guard_failure_has_no_cleanup_or_docker(self):
        self.ok(r'''
function Assert-IsolatedRuntimeGuard {throw 'explicit offline guard fixture'}
function Invoke-IsolatedDocker {throw 'UNEXPECTED_DOCKER'}
function Invoke-IsolatedCompose {throw 'UNEXPECTED_DOCKER'}
$r=[ordered]@{status='FAILED';failureStage=$null;archiveBytesVerified=$true;cleanup='not-started';dockerInvoked=$false}
try{Invoke-IsolatedSmoke 'C:\pkg' 'C:\out' 'C:\tar' @{} $r}catch{}
Assert-True ($r.status -ceq 'FAILED' -and $r.failureStage -ceq 'runtime-guard' -and $r.cleanup -ceq 'not-started' -and -not $r.dockerInvoked)
''')

    def test_timeout_terminates_local_fixture_process_tree(self):
        # Only a harmless sleeping PowerShell fixture; no service/Docker.
        self.ok(f"$start=[datetime]::UtcNow; $failed=$false;try{{Invoke-IsolatedProcess {quote(PS)} "
                "@('-NoProfile','-NonInteractive','-Command','Start-Sleep -Seconds 60') "
                "'C:\\Users\\Admin' @{} 1 ([datetime]::UtcNow.AddSeconds(60)) 1024}catch{$failed=$true};"
                "Assert-True ($failed -and ([datetime]::UtcNow-$start).TotalSeconds -lt 30)")

    def test_function_only_static_policy(self):
        text = RUNNER.read_text()
        self.ok(f"$t=$null;$e=$null;$a=[Management.Automation.Language.Parser]::ParseFile({quote(RUNNER)},[ref]$t,[ref]$e);"
                "$bad=@($a.EndBlock.Statements | Where-Object {$_ -isnot [Management.Automation.Language.FunctionDefinitionAst]});Assert-True ($bad.Count -eq 0)")
        self.assertNotIn('.ReadToEnd', text)
        self.assertNotIn('SetEnvironmentVariable', text)
        self.assertIn("' /T /F'", text)
        self.assertIn('AddMinutes(30)', text)
        self.assertIn('AddMinutes(5)', text)
        self.assertNotRegex(text, r"@\('(?:build|pull|push|rmi|prune|logs)'[,)]")
        self.assertNotIn('--rmi', text)

    def test_bounded_process_captures_caps_and_suppresses_stderr(self):
        code = (f"$r=Invoke-IsolatedProcess {quote(PS)} @('-NoProfile','-NonInteractive','-Command',"
                "'[Console]::Out.Write(\"x\"*200);[Console]::Error.Write(\"SECRET_SENTINEL\")') "
                "'C:\\Users\\Admin' @{} 10 ([datetime]::UtcNow.AddSeconds(60)) 1024; "
                "Assert-True ($r.Code -eq 0 -and $r.Text.Length -eq 200); 'SAFE'")
        self.assertEqual(self.ok(code), 'SAFE')
        overflow = (f"Invoke-IsolatedProcess {quote(PS)} @('-NoProfile','-NonInteractive','-Command',"
                    "'[Console]::Out.Write(\"x\"*10000)') 'C:\\Users\\Admin' @{} 10 ([datetime]::UtcNow.AddSeconds(60)) 128")
        self.assertNotEqual(self.helper(overflow).returncode, 0)

    def test_model_rejects_unsafe_features(self):
        # Current parent model is read only; import does not execute package/Docker work.
        import sys
        sys.path.insert(0, str(HERE))
        from build_image_runtime import runtime_model
        ids = {name: {'imageId': 'sha256:' + str(i)*64}
               for i, name in enumerate(('neo4j', 'dg-reasoner', 'data-service', 'design-grammars'), 1)}
        model = runtime_model(ids)
        project = 'dg-image-' + 'a'*32
        # Approximate Compose's documented normalization, not real Compose evidence.
        for name, service in model['services'].items():
            service['networks'] = {'sandbox': None}
            for volume in service.get('volumes', []):
                if volume['type'] == 'bind':
                    volume['source'] = 'C:\\pkg\\' + volume['source'][2:].replace('/', '\\')
        model['name'] = project
        model['networks']['sandbox']['name'] = project + '_sandbox'
        for name, volume in model['volumes'].items():
            volume['name'] = project + '_' + name
        def check(value):
            code = f"$m={quote(json.dumps(value))}|ConvertFrom-Json;$j={quote(json.dumps({'images':ids}))}|ConvertFrom-Json;"
            code += f"Assert-IsolatedComposeModel $m $j 'C:\\pkg' {quote(project)}"
            return self.helper(code)
        self.assertEqual(check(model).returncode, 0)
        import copy
        for field, value in [('ports', ['80:80']), ('privileged', True), ('build', {}),
                             ('network_mode', 'host'), ('devices', ['/dev/anything']),
                             ('volumes_from', ['foreign']), ('env_file', ['.env']),
                             ('container_name', 'foreign'), ('entrypoint', ['evil']),
                             ('use_api_socket', True)]:
            bad = copy.deepcopy(model)
            bad['services']['data-service'][field] = value
            with self.subTest(field=field):
                self.assertNotEqual(check(bad).returncode, 0)
        for mutate in (
                lambda m: m['networks']['sandbox'].update(external=True),
                lambda m: m['networks']['sandbox'].update(internal=False),
                lambda m: m['volumes']['graph'].update(name='existing-data'),
                lambda m: m['services']['neo4j']['volumes'][0].update(source='foreign'),
                lambda m: m['services']['data-service']['volumes'][1].update(source='C:\\outside\\file'),
                lambda m: m['services']['data-service'].update(image='mutable:latest')):
            bad = copy.deepcopy(model)
            mutate(bad)
            self.assertNotEqual(check(bad).returncode, 0)


if __name__ == '__main__':
    unittest.main()
