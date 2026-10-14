"""Offline contract for the separate Windows owner-run capability package."""
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
import zipfile

ROOT = Path(__file__).resolve().parents[3]
HOSTED = ROOT / 'deploy/hosted'


def committed_builder_if_needed(directory):
    """A dirty builder intentionally cannot package a not-yet-committed input."""
    present = subprocess.run(['git', '-C', str(ROOT), 'cat-file', '-e',
                              'HEAD:deploy/hosted/sandbox/evidence.cjs'],
                             stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL).returncode == 0
    if present:
        return HOSTED / 'build_sandbox.py'
    previous = subprocess.check_output(['git', '-C', str(ROOT), 'show',
                                         'HEAD:deploy/hosted/build_sandbox.py'])
    previous_path = Path(directory) / 'committed_builder.py'
    previous_path.write_bytes(previous)
    return previous_path


class SandboxPackageTests(unittest.TestCase):
    def test_builder_exports_committed_revision_only_and_verifies_contents(self):
        with tempfile.TemporaryDirectory() as temp:
            destination = Path(temp) / 'sandbox.zip'
            revision = subprocess.check_output(['git', '-C', str(ROOT), 'rev-parse', 'HEAD'], text=True).strip()
            command = [sys.executable, str(committed_builder_if_needed(temp)), '--repo', str(ROOT),
                       '--revision', revision, '--output', str(destination)]
            run = subprocess.run(command, capture_output=True, text=True)
            self.assertEqual(run.returncode, 0, run.stderr)
            with zipfile.ZipFile(destination) as archive:
                files = set(archive.namelist())
                manifest = json.loads(archive.read('sandbox-manifest.json'))
                self.assertEqual(files, set(manifest['files']) | {'sandbox-manifest.json'})
                self.assertNotIn('.env', files)
                self.assertNotIn('DG_OBSIDIAN', ' '.join(files))
                self.assertNotIn('Publications', ' '.join(files))
                self.assertEqual(manifest['frameworkRevision'], revision)
                self.assertIn('data-service/app.py', files)
                self.assertIn('n8n/workflows/sandbox-file-read.json', files)
                self.assertIn('deploy/hosted/sandbox/Run-Sandbox.ps1', files)
                self.assertIn('deploy/hosted/sandbox/compose.yaml', files)
                for member in ('deploy/hosted/sandbox/compose.yaml',
                               'deploy/hosted/sandbox/Run-Sandbox.ps1'):
                    committed = subprocess.check_output(['git', '-C', str(ROOT),
                                                          'show', f'{revision}:{member}'])
                    self.assertEqual(archive.read(member), committed,
                                     f'{member} must preserve exact committed bytes')
            verify = subprocess.run([*command, '--verify-only'], capture_output=True, text=True)
            self.assertEqual(verify.returncode, 0, verify.stderr)

    def test_preflight_is_host_guarded_and_no_start_before_checks(self):
        script = (HOSTED / 'sandbox/Run-Sandbox.ps1').read_text(encoding='utf-8')
        host = script.index('DESKTOP-OS4Q8CP')
        docker = script.index('docker compose')
        self.assertLess(host, docker)
        for guard in ('2.24.4', 'Get-FileHash', 'sandbox-manifest.json', 'Get-PSDrive', 'Get-NetTCPConnection',
                      'finally', 'dg-hosted-1309-sandbox', '127.0.0.1', '--timeout', 'cpus:', 'mem_limit:'):
            self.assertTrue(guard in script or guard in (HOSTED / 'sandbox/compose.yaml').read_text(), guard)
        self.assertNotIn('docker-compose.hosted.yml', script)

    def test_probe_login_uses_required_csrf_header(self):
        probe = (HOSTED / 'sandbox/probe.py').read_text(encoding='utf-8')
        self.assertIn("request(opener, '/auth/login', {'username': user, 'password': password}, csrf=True)", probe)
        self.assertIn("headers['X-DG-CSRF'] = '1'", probe)

    def test_windows_powershell_preflight_reads_extracted_members(self):
        script = (HOSTED / 'sandbox/Run-Sandbox.ps1').read_text(encoding='utf-8')
        path_line = next(line.strip() for line in script.splitlines() if '$relative = $item.FullName.Substring' in line)
        zip_init = next((line.strip() for line in script.splitlines() if 'Add-Type -AssemblyName System.IO.Compression.FileSystem' in line), '')
        with tempfile.TemporaryDirectory() as temp:
            member = Path(temp) / 'data-service' / 'app.py'
            member.parent.mkdir()
            member.write_text('synthetic', encoding='utf-8')
            code = ("$root=(Resolve-Path -LiteralPath '" + str(Path(temp)).replace("'", "''") + "').Path; "
                    "$item=Get-Item -LiteralPath (Join-Path $root 'data-service/app.py'); "
                    + path_line + "; if($relative -cne 'data-service/app.py'){exit 2}; "
                    + zip_init + "; if(-not ('System.IO.Compression.ZipFile' -as [type])){exit 3}")
            result = subprocess.run(['powershell.exe', '-NoProfile', '-Command', code],
                                    capture_output=True, text=True)
            self.assertEqual(result.returncode, 0, result.stderr)

    def test_start_failure_reports_only_allowlisted_container_state(self):
        script = (HOSTED / 'sandbox/Run-Sandbox.ps1').read_text(encoding='utf-8')
        self.assertIn("$report.checks.startDetail = 'compose-up-nonzero'", script)
        self.assertIn("$report.checks.startDetail = 'readiness-timeout'", script)
        self.assertIn("$report.checks.startState = Get-ServiceStates", script)
        self.assertNotIn("$report.checks.startState = $up.text", script)
        start = script.index('function Get-ServiceStates')
        end = script.index('function New-RandomSecret', start)
        helper = script[start:end]
        # The diagnostic is exercised with mocked Docker responses; no Docker runs here.
        code = ("$ErrorActionPreference='Stop'; "
                "function Compose([string[]]$a,[int]$t) { return @{code=0;text='abc123def456'} }; "
                "function Invoke-Bounded([string[]]$a,[int]$t) { "
                "return @{code=0;text='{\"Status\":\"exited\",\"ExitCode\":137,\"OOMKilled\":true,\"Error\":\"SECRET_DO_NOT_EMIT\"}'} }; "
                + helper + "; $x=Get-ServiceStates; "
                "if($x.'neo4j'.status -cne 'exited' -or $x.'neo4j'.exitCode -ne 137 "
                "-or -not $x.'neo4j'.oomKilled){exit 2}; "
                "$j=$x | ConvertTo-Json -Depth 5; "
                "if($j.Contains('SECRET_DO_NOT_EMIT')){exit 3}; "
                "if($x.'data-service'.status -cne 'exited'){exit 4}")
        result = subprocess.run(['powershell.exe', '-NoProfile', '-Command', code],
                                capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stderr)

    def test_startup_log_signature_is_sanitized_and_bounded(self):
        script = (HOSTED / 'sandbox/Run-Sandbox.ps1').read_text(encoding='utf-8')
        start = script.index('function Get-StartupFailureSignature')
        end = script.index('function New-RandomSecret', start)
        helper = script[start:end]
        samples = (
            ('Traceback (most recent call last):\n  File "app.py", line 127, in lifespan\n'
             '  File "app.py", line 1400, in ensure_spec_indexes\n'
             'neo4j.exceptions.ServiceUnavailable: SECRET_DO_NOT_EMIT', 'neo4j-availability', 'ServiceUnavailable'),
            ('  File "app.py", line 122, in lifespan\n'
             '  File "auth.py", line 753, in ensure_bootstrap_admin\n'
             'RuntimeError: SECRET_DO_NOT_EMIT', 'bootstrap-admin', 'RuntimeError'),
            ('  File "app.py", line 121, in lifespan\n'
             '  File "secrets_policy.py", line 137, in enforce_startup_secrets\n'
             'RuntimeError: SECRET_DO_NOT_EMIT', 'secret-policy', 'RuntimeError'),
            ('Secret-only log SECRET_DO_NOT_EMIT', 'unknown', 'unknown'),
        )
        for sample, expected_phase, expected_error in samples:
            code = ("$ErrorActionPreference='Stop'; "
                    "function Compose([string[]]$a,[int]$t) { "
                    "return @{code=0;text=[Text.Encoding]::UTF8.GetString([Convert]::FromBase64String('"
                    + __import__('base64').b64encode(sample.encode()).decode() + "'))} }; "
                    + helper + "; $x=Get-StartupFailureSignature; "
                    "$j=$x | ConvertTo-Json -Compress; "
                    "if($x.phase -cne '" + expected_phase + "' -or $x.errorClass -cne '"
                    + expected_error + "' -or $j.Contains('SECRET_DO_NOT_EMIT')){exit 2}")
            result = subprocess.run(['powershell.exe', '-NoProfile', '-Command', code],
                                    capture_output=True, text=True)
            self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn('$report.checks.startSignature = Get-StartupFailureSignature', script)

    def test_neo4j_readiness_precedes_data_service_start(self):
        compose = (HOSTED / 'sandbox/compose.yaml').read_text(encoding='utf-8')
        script = (HOSTED / 'sandbox/Run-Sandbox.ps1').read_text(encoding='utf-8')
        self.assertIn('healthcheck:', compose)
        self.assertIn('condition: service_healthy', compose)
        self.assertIn('cypher-shell', compose)
        self.assertIn('$${NEO4J_AUTH#neo4j/}', compose)
        self.assertIn('NEO4J_PASSWORD=', compose)
        self.assertNotIn('cypher-shell -u neo4j -p ', compose)
        self.assertIn("'--wait-timeout','180'", script)
        self.assertLess(script.index("$neoUp = Compose @('up'"),
                        script.index("$up = Compose @('up'"))
        self.assertLess(script.index("$stage = 'service-start'"),
                        script.index("$stage = 'data-service-ingest'"))

    def test_neo4j_wait_has_bounded_failure_evidence(self):
        script = (HOSTED / 'sandbox/Run-Sandbox.ps1').read_text(encoding='utf-8')
        self.assertIn("$report.checks.startDetail = 'neo4j-not-ready'", script)
        self.assertIn("$report.checks.startDetail = 'readiness-timeout'", script)

    def test_n8n_workflows_write_only_post_assertion_artifacts(self):
        compose = (HOSTED / 'sandbox/compose.yaml').read_text(encoding='utf-8')
        self.assertIn('N8N_RESTRICT_FILE_ACCESS_TO: /files/workflows;/files/evidence', compose)
        self.assertIn('n8n_evidence:/files/evidence', compose)
        self.assertIn('./evidence.cjs:/files/probe/evidence.cjs:ro', compose)
        for filename, assertion in (('sandbox-file-read.json', 'Assert named content'),
                                    ('sandbox-file-denied.json', 'Assert denied path')):
            workflow = json.loads((ROOT / 'n8n/workflows' / filename).read_text(encoding='utf-8'))
            nodes = {node['name']: node for node in workflow['nodes']}
            self.assertEqual(nodes['Evidence to text']['parameters']['operation'], 'toText')
            self.assertEqual(nodes['Write evidence']['parameters']['operation'], 'write')
            self.assertEqual(nodes['Write evidence']['type'], 'n8n-nodes-base.readWriteFile')
            self.assertEqual(workflow['connections'][assertion]['main'][0][0]['node'], 'Evidence to text')
            self.assertEqual(workflow['connections']['Evidence to text']['main'][0][0]['node'], 'Write evidence')
            self.assertIn('/files/evidence/', nodes['Write evidence']['parameters']['fileName'])
        denied = json.loads((ROOT / 'n8n/workflows/sandbox-file-denied.json').read_text(encoding='utf-8'))
        nodes = {node['name']: node for node in denied['nodes']}
        self.assertTrue(nodes['Read outside named mount']['continueOnFail'])
        self.assertIn('Access to the file is not allowed.', nodes['Assert denied path']['parameters']['jsCode'])

    def test_n8n_assertions_reject_wrong_input_before_writing_marker(self):
        named = json.loads((ROOT / 'n8n/workflows/sandbox-file-read.json').read_text(encoding='utf-8'))
        denied = json.loads((ROOT / 'n8n/workflows/sandbox-file-denied.json').read_text(encoding='utf-8'))
        samples = (
            (named, 'Assert named content',
             {'data': {'id': 'dg1309FileRead', 'name': named['name']}}, True),
            (named, 'Assert named content', {'data': {'id': 'wrong', 'name': named['name']}}, False),
            (denied, 'Assert denied path',
             {'error': 'Access to the file is not allowed. Allowed paths: /files/workflows'}, True),
            (denied, 'Assert denied path', {'error': 'ENOENT: file missing'}, False),
            (denied, 'Assert denied path', {'fileName': '/etc/passwd'}, False),
        )
        for workflow, node_name, item, accepted in samples:
            source = next(n['parameters']['jsCode'] for n in workflow['nodes'] if n['name'] == node_name)
            js = ("const $input={first:()=>({json:" + json.dumps(item) +
                  "})}; let passed=false; try{ const run=new Function('$input'," +
                  json.dumps(source) +
                  "); const out=run($input); passed=Array.isArray(out) && out.length===1; "
                  "}catch(e){ if(!e.message.includes('Unexpected workflow file content') "
                  "&& !e.message.includes('Read node did not deny outside path'))process.exit(5); } "
                  "process.exit(passed===" + ('true' if accepted else 'false') + '?0:3);')
            run = subprocess.run(['node', '-e', js], capture_output=True, text=True)
            self.assertEqual(run.returncode, 0, (node_name, item, run.stderr))

    def test_n8n_evidence_is_checked_outside_cli_stdout(self):
        script = (HOSTED / 'sandbox/Run-Sandbox.ps1').read_text(encoding='utf-8')
        self.assertIn('Assert-N8nEvidenceEmpty', script)
        self.assertIn('Test-N8nEvidenceFile', script)
        self.assertIn('n8nNamedRead', script)
        self.assertIn('n8nDeniedRead', script)
        self.assertNotIn('Read-N8nExecutionJson $good.text', script)
        self.assertNotIn('Read-N8nExecutionJson $denied.text', script)
        self.assertIn('deploy/hosted/sandbox/evidence.cjs', __import__('runpy').run_path(
            str(HOSTED / 'build_sandbox.py'))['INPUTS'])
        self.assertLess(script.index('Assert-N8nEvidenceEmpty\n  $stage'), script.index('Assert-N8nNamedRead\n  $stage'))

    def test_n8n_evidence_reader_rejects_missing_wrong_or_extra_files(self):
        helper = HOSTED / 'sandbox/evidence.cjs'
        self.assertTrue(helper.is_file(), 'isolated evidence verifier must be packaged')
        cases = [
            ({}, 'empty', True),
            ({'named.txt': 'DG1309-NAMED-READ-VERIFIED'}, 'named', True),
            ({'named.txt': 'DG1309-NAMED-READ-VERIFIED',
              'denied.txt': 'DG1309-DENIED-READ-VERIFIED'}, 'denied', True),
            ({'named.txt': 'DG1309-NAMED-READ-VERIFIED'}, 'denied', False),
            ({'named.txt': 'DG1309-NAMED-READ-VERIFIED', 'other': 'x'}, 'named', False),
            ({'named.txt': 'SECRET_DO_NOT_EMIT'}, 'named', False),
            ({'named.txt': 'DG1309-NAMED-READ-VERIFIED\n'}, 'named', False),
            ({'denied.txt': 'DG1309-DENIED-READ-VERIFIED'}, 'denied', False),
        ]
        for files, stage, accepted in cases:
            with tempfile.TemporaryDirectory() as temp:
                for name, content in files.items():
                    (Path(temp) / name).write_text(content, encoding='utf-8')
                run = subprocess.run(['node', str(helper), stage, temp], capture_output=True, text=True)
                self.assertEqual(run.returncode == 0, accepted, (stage, files))
                self.assertNotIn('SECRET_DO_NOT_EMIT', run.stdout + run.stderr)

    def test_n8n_init_requires_empty_disposable_evidence_volume(self):
        script = (HOSTED / 'sandbox/Run-Sandbox.ps1').read_text(encoding='utf-8')
        self.assertIn("'--user','0:0'", script)
        self.assertIn("'--entrypoint','node','n8n','/files/probe/evidence.cjs','init'", script)
        self.assertIn('n8n-evidence-init', script)
        helper = (HOSTED / 'sandbox/evidence.cjs').read_text(encoding='utf-8')
        self.assertIn("directory !== '/files/evidence'", helper)
        self.assertIn('fs.chownSync(directory, 1000, 1000)', helper)

    def test_n8n_named_read_failure_reports_only_bounded_stage(self):
        script = (HOSTED / 'sandbox/Run-Sandbox.ps1').read_text(encoding='utf-8')
        helper = script[script.index('function Assert-N8nNamedRead'):script.index('function Assert-N8nDeniedRead')]
        # stdout may contain arbitrary text or a forged success-looking JSON suffix.
        for import_code, execute_code, evidence_ok, expected in (
            (1, 0, True, 'import-nonzero'),
            (0, 1, True, 'execute-nonzero'),
            (0, 0, False, 'evidence-missing-or-invalid'),
            (0, 0, True, None),
        ):
            code = ("$ErrorActionPreference='Stop'; $report=@{checks=@{}}; "
                    "function Compose([string[]]$a,[int]$t) { "
                    f"if($a -contains 'import:workflow'){{return @{{code={import_code};text='SECRET_DO_NOT_EMIT'}}}}; "
                    f"return @{{code={execute_code};text='SECRET_DO_NOT_EMIT`n{{\"data\":{{}}}}'}} }}; "
                    "function Test-N8nEvidenceFile([string]$p){return " +
                    ('$true' if evidence_ok else '$false') + '}; ' + helper +
                    "; try { Assert-N8nNamedRead } catch {}; "
                    "$j=$report | ConvertTo-Json -Depth 5; if($j.Contains('SECRET_DO_NOT_EMIT')){exit 3}; "
                    "if((($report.checks.n8nDetail -as [string]) -cne '" + (expected or '') + "')){exit 4}; "
                    "if([bool]$report.checks.n8nNamedRead -ne " +
                    ('$true' if expected is None else '$false') + "){exit 5}")
            result = subprocess.run(['powershell.exe', '-NoProfile', '-Command', code],
                                    capture_output=True, text=True, errors='replace')
            self.assertEqual(result.returncode, 0, f'{expected}: {result.stderr}')

    def test_n8n_cli_stdout_is_never_used_as_evidence(self):
        script = (HOSTED / 'sandbox/Run-Sandbox.ps1').read_text(encoding='utf-8')
        segment = script[script.index('function Test-N8nEvidenceFile'):script.index('function New-RandomSecret')]
        self.assertNotIn('ConvertFrom-Json', segment)
        self.assertNotIn('$good.text', segment)
        self.assertNotIn('$denied.text', segment)
        self.assertIn("Test-N8nEvidenceFile 'named'", segment)
        self.assertIn("Test-N8nEvidenceFile 'denied'", segment)

    def test_n8n_denied_read_requires_read_node_error_and_sanitizes_output(self):
        script = (HOSTED / 'sandbox/Run-Sandbox.ps1').read_text(encoding='utf-8')
        helper = script[script.index('function Assert-N8nDeniedRead'):script.index('function New-RandomSecret')]
        for import_code, execute_code, evidence_ok, accepted in (
            (0, 0, True, True), (1, 0, True, False),
            (0, 1, True, False), (0, 0, False, False),
        ):
            code = ("$ErrorActionPreference='Stop'; $report=@{checks=@{}}; "
                    "function Assert-Ok($v,[string]$m){if(-not $v){throw $m}}; "
                    "function Compose([string[]]$a,[int]$t){ "
                    f"if($a -contains 'import:workflow'){{return @{{code={import_code};text='SECRET_DO_NOT_EMIT'}}}}; "
                    f"return @{{code={execute_code};text='SECRET_DO_NOT_EMIT'}} }}; "
                    "function Test-N8nEvidenceFile([string]$p){return " +
                    ('$true' if evidence_ok else '$false') + '}; ' + helper +
                    "; try{Assert-N8nDeniedRead}catch{}; "
                    "if([bool]$report.checks.n8nDeniedRead -ne " +
                    ('$true' if accepted else '$false') + "){exit 2}; "
                    "$j=$report|ConvertTo-Json -Depth 5; "
                    "if($j.Contains('SECRET_DO_NOT_EMIT')){exit 3}")
            result = subprocess.run(['powershell.exe', '-NoProfile', '-Command', code],
                                    capture_output=True, text=True, errors='replace')
            self.assertEqual(result.returncode, 0, f'{accepted}: {result.stderr}')
        self.assertIn('Assert-N8nDeniedRead', script[script.index("$stage = 'n8n-denied-file-read'"):])

    def test_manifest_rejects_changed_zip_member(self):
        with tempfile.TemporaryDirectory() as temp:
            destination = Path(temp) / 'sandbox.zip'
            revision = subprocess.check_output(['git', '-C', str(ROOT), 'rev-parse', 'HEAD'], text=True).strip()
            command = [sys.executable, str(committed_builder_if_needed(temp)), '--repo', str(ROOT),
                       '--revision', revision, '--output', str(destination)]
            self.assertEqual(subprocess.run(command, capture_output=True).returncode, 0)
            with zipfile.ZipFile(destination) as source:
                entries = {n: source.read(n) for n in source.namelist()}
            entries['deploy/hosted/ingest/README.md'] = b'altered'
            with zipfile.ZipFile(destination, 'w') as output:
                for name, content in entries.items():
                    output.writestr(name, content)
            self.assertNotEqual(subprocess.run([*command, '--verify-only'], capture_output=True).returncode, 0)


if __name__ == '__main__':
    unittest.main()
