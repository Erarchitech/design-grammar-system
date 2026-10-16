"""Offline tests for the real-candidate capability handoff (no service starts)."""
import importlib.util
import json
from pathlib import Path
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[3]
HOSTED = ROOT / 'deploy/hosted'


def builder():
    path = HOSTED / 'build_bundle_test.py'
    if not path.is_file():
        raise AssertionError('missing real-candidate handoff builder')
    spec = importlib.util.spec_from_file_location('bundle_test_builder', path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class BundlePackageTests(unittest.TestCase):
    def test_builder_refuses_dirty_support_before_writing_zip(self):
        module = builder()
        self.assertTrue(callable(getattr(module, 'build', None)), 'missing committed candidate ZIP builder')
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            subprocess.run(['git', 'init', '-q', str(root / 'repo')], check=True)
            repo = root / 'repo'
            (repo / 'sample.txt').write_text('fixture')
            subprocess.run(['git', '-C', str(repo), 'add', 'sample.txt'], check=True)
            subprocess.run(['git', '-C', str(repo), '-c', 'user.name=Fixture',
                            '-c', 'user.email=fixture@example.invalid', 'commit', '-qm', 'fixture'], check=True)
            revision = subprocess.check_output(['git', '-C', str(repo), 'rev-parse', 'HEAD'], text=True).strip()
            with self.assertRaises(ValueError):
                module.build(repo, revision, root / 'bad.zip')
            self.assertFalse((root / 'bad.zip').exists())

    def test_powershell_runner_checks_candidate_identity_before_docker(self):
        path = HOSTED / 'bundle-test/Run-BundleTest.ps1'
        self.assertTrue(path.is_file(), 'missing owner-run bundle integration runner')
        script = path.read_text(encoding='utf-8')
        for guard in ('bundle-test-manifest.json', 'candidateManifestSha256', 'candidate/manifest.json',
                      'DESKTOP-OS4Q8CP', 'PreflightOnly', 'projectVacant', 'finally'):
            self.assertIn(guard, script)
        self.assertLess(script.index('$report.checks.candidateIntegrity = $true'),
                        script.index("$stage = 'image-pull'"))
        self.assertIn("@('build','--quiet','neo4j','data-service')", script)
        self.assertIn("$report.checks.cleanupVerified", script)
        self.assertIn("$model.networks.sandbox.internal", script)
        self.assertNotIn("$report.status = 'PREFLIGHT_ONLY'; return", script,
                         'return must not bypass failure exit when report writing fails')
        self.assertNotIn('$report.checks.dataService = $evidence', script)
        code = ("$tokens=$null;$errors=$null;[void][Management.Automation.Language.Parser]::ParseFile('"
                + str(path).replace("'", "''") + "',[ref]$tokens,[ref]$errors); if($errors.Count){exit 1}")
        result = subprocess.run(['powershell.exe', '-NoProfile', '-Command', code], capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, 'PowerShell syntax failed')

    def test_timeout_terminates_process_tree_before_cleanup(self):
        script = (HOSTED / 'bundle-test/Run-BundleTest.ps1').read_text(encoding='utf-8')
        self.assertIn('function Stop-BoundedProcess', script)
        self.assertIn('Stop-BoundedProcess $p', script)
        self.assertNotIn('try { $p.Kill() } catch {}', script)
        # Execute only the termination helper, against disposable PowerShell
        # processes. No Docker executable or service is invoked.
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            pid_file = root / 'child.pid'
            parent = root / 'parent.ps1'
            parent.write_text("$p=Start-Process powershell.exe -ArgumentList '-NoProfile -Command Start-Sleep -Seconds 45' -PassThru; $p.Id | Set-Content -LiteralPath '"
                              + str(pid_file).replace("'", "''") + "'; Start-Sleep -Seconds 45", encoding='utf-8')
            function = script[script.index('function Stop-BoundedProcess'):script.index('function Invoke-Bounded')]
            probe = root / 'test.ps1'
            probe.write_text(function + "\n$ErrorActionPreference='Stop'; $p=Start-Process powershell.exe -ArgumentList @('-NoProfile','-File','\""
                + str(parent) + "\"') -PassThru; try { for($i=0;$i -lt 100 -and -not (Test-Path '"
                + str(pid_file) + "');$i++){Start-Sleep -Milliseconds 100}; $childId=[int](Get-Content '"
                + str(pid_file) + "'); Stop-BoundedProcess $p; if(Get-Process -Id $childId -ErrorAction SilentlyContinue){exit 2} } finally { if(-not $p.HasExited){Stop-Process -Id $p.Id -Force} }; exit 0", encoding='utf-8')
            result = subprocess.run(['powershell.exe', '-NoProfile', '-ExecutionPolicy', 'Bypass', '-File', str(probe)],
                                    capture_output=True, text=True, timeout=35)
            self.assertEqual(result.returncode, 0, 'process-tree termination failed: ' + result.stderr)

    def test_committed_fixture_zip_exercises_real_powershell_preflight_without_docker(self):
        module = builder()
        with tempfile.TemporaryDirectory(prefix='dg-bundle-offline-') as tmp:
            root = Path(tmp)
            repo = root / 'repo'
            repo.mkdir()
            # Deliberately synthetic repository: never a production handoff ZIP.
            tools = ('build_bundle_test.py', 'assemble.py', 'validate_manifest.py', 'release_core.py')
            for name in tuple('deploy/hosted/' + n for n in tools) + module.SUPPORT:
                target = repo / name
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_bytes((ROOT / name).read_bytes())
            inputs = {
                'docker-compose.yml': json.dumps({'services': {
                    'neo4j': {'build': './neo4j', 'volumes': ['graph:/data']},
                    'data-service': {'build': './data-service', 'volumes': ['state:/app/data']},
                    'n8n': {'image': 'n8nio/n8n:2.4.8', 'volumes': ['n8n:/home/node/.n8n']},
                }, 'volumes': {'graph': {}, 'state': {}, 'n8n': {}}}),
                'docker-compose.multi-user.yml': 'services: {}\n',
                'docker-compose.hosted.yml': 'services: {}\n',
                'neo4j/Dockerfile': 'FROM scratch\n',
                'data-service/Dockerfile': 'FROM scratch\n',
            }
            policy_name = 'deploy/hosted/release-allowlist.json'
            inputs[policy_name] = json.dumps({'schemaVersion': 1, 'includeDegram': False, 'inputs': [
                {'path': name, 'purpose': 'offline synthetic fixture'}
                for name in sorted((*inputs, policy_name))]}) + '\n'
            for name, value in inputs.items():
                path = repo / name
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_bytes(value.encode())
            subprocess.run(['git', 'init', '-q', str(repo)], check=True, capture_output=True)
            subprocess.run(['git', '-C', str(repo), '-c', 'core.autocrlf=false', 'add', '.'], check=True, capture_output=True)
            subprocess.run(['git', '-C', str(repo), '-c', 'user.name=Fixture', '-c',
                            'user.email=fixture@example.invalid', 'commit', '-qm', 'offline fixture'],
                           check=True, capture_output=True)
            rev = subprocess.check_output(['git', '-C', str(repo), 'rev-parse', 'HEAD'], text=True).strip()
            archive = root / 'fixture-not-for-handoff.zip'
            checksum = module.build(repo, rev, archive)
            self.assertEqual(checksum, module.verify(archive))
            # A clean Windows checkout may use CRLF; archive must still contain
            # canonical committed bytes, not the checkout's conversion.
            policy_path = repo / policy_name
            policy_path.write_bytes(policy_path.read_bytes().replace(b'\r\n', b'\n') + b'\r\n')
            # Preserve JSON semantics but not whitespace: this is genuinely dirty.
            with self.assertRaises(ValueError):
                module.build(repo, rev, root / 'dirty-policy.zip')
            committed_policy = subprocess.check_output(['git', '-C', str(repo), 'show', f'{rev}:{policy_name}'])
            policy_path.write_bytes(committed_policy.replace(b'\n', b'\r\n'))
            empty_env = repo / 'deploy/hosted/bundle-test/empty-env.txt'
            empty_env.write_bytes(empty_env.read_bytes().replace(b'\r\n', b'\n').replace(b'\n', b'\r\n'))
            converted = root / 'crlf-fixture.zip'
            module.build(repo, rev, converted)
            self.assertEqual(module.verify(converted), checksum)
            import zipfile
            extraction = root / 'extracted'
            with zipfile.ZipFile(archive) as z:
                z.extractall(extraction)
            def preflight(extra=()):
                report = root / ('report-' + str(len(list(root.glob('report-*')))) + '.json')
                result = subprocess.run(['powershell.exe', '-NoProfile', '-ExecutionPolicy', 'Bypass',
                    '-File', str(extraction / 'support/Run-BundleTest.ps1'), '-PreflightOnly',
                    '-PackageZip', str(archive), '-ExpectedZipSha256', checksum, '-ReportPath', str(report),
                    *extra], capture_output=True, text=True, timeout=40)
                data = json.loads(report.read_text(encoding='utf-8-sig')) if report.exists() else None
                return result, data
            result, report = preflight()
            self.assertEqual(result.returncode, 0, 'real PowerShell preflight failed: ' + str(report))
            self.assertEqual(report['status'], 'PREFLIGHT_ONLY')
            self.assertTrue(report['checks']['candidateIntegrity'])
            self.assertNotIn('projectVacant', report['checks'])
            (extraction / 'unexpected.txt').write_text('extra')
            result, report = preflight()
            self.assertNotEqual(result.returncode, 0)
            self.assertEqual(report['status'], 'FAIL')
            (extraction / 'unexpected.txt').unlink()
            candidate = extraction / 'candidate/data-service/Dockerfile'
            candidate.write_text('changed')
            result, report = preflight()
            self.assertNotEqual(result.returncode, 0)
            self.assertEqual(report['failureStage'], 'preflight')

    def test_runtime_subset_preserves_actual_bundle_mounts_and_builds(self):
        module = builder()
        self.assertIn('deploy/hosted/bundle-test/empty-env.txt', module.SUPPORT,
                      'runner must never fall back to an owner environment file')
        import sys
        sys.path.insert(0, str(HOSTED))
        from validate_manifest import merged_compose
        services = merged_compose(ROOT)
        model = module.runtime_model(ROOT, services)
        self.assertEqual(set(model['services']), {'neo4j', 'data-service', 'n8n'})
        ds = model['services']['data-service']
        self.assertEqual(ds['build']['context'], './candidate/data-service')
        original = {m['target']: m for m in services['data-service']['volumes']}
        actual = {m['target']: m for m in ds['volumes']}
        for target in original:
            self.assertIn(target, actual)
            self.assertEqual(original[target]['type'], actual[target]['type'])
            if original[target]['type'] == 'bind':
                self.assertTrue(actual[target]['read_only'])
                self.assertTrue(actual[target]['source'].startswith('./candidate/'))
        self.assertEqual(model['services']['neo4j']['build']['context'], './candidate/neo4j')
        self.assertNotIn('/files/workflows/sandbox-file-read.json',
                         [v['target'] for v in model['services']['n8n']['volumes']],
                         'nested bind into read-only candidate directory cannot create absent target')
        self.assertIn('./test-workflows', [v.get('source') for v in model['services']['n8n']['volumes']])
        self.assertTrue(model['networks']['sandbox']['internal'])
        for name, service in model['services'].items():
            self.assertFalse(service.get('ports'))
            self.assertFalse(service.get('container_name'))
            self.assertFalse(service.get('extra_hosts'))
            self.assertEqual(service['networks'], ['sandbox'])
            self.assertTrue(service['mem_limit'])
            self.assertTrue(service['cpus'])
            self.assertNotIn('OLLAMA_URL', service.get('environment', {}))
        with tempfile.TemporaryDirectory() as tmp:
            compose = Path(tmp) / 'compose.json'
            compose.write_text(json.dumps(model), encoding='utf-8')
            from test_compose_profile import compose_result
            result = compose_result(compose)
            self.assertEqual(result.returncode, 0, 'offline generated model parse failed')


if __name__ == '__main__':
    unittest.main()
