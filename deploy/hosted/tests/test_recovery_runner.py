"""Exercise actual delivered ZIP/PS5 and config-only Compose; no daemon."""
import copy
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest
import zipfile

HERE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(HERE))
import build_recovery_test as package
import test_recovery_execution as execution
from test_recovery_execution import quote

SCRATCH = Path('C:/Users/Admin/AppData/Local/hermes/cache/scratch')
RUNTIME = Path('C:/Users/Admin/Downloads/DG-image-runtime-c82b92b-v2.zip')
PS = shutil.which('powershell.exe')


class RunnerTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix='dg-recovery-test-', dir=SCRATCH)
        self.addCleanup(self.tmp.cleanup)
        self.base = Path(self.tmp.name)
        self.path = self.base / 'recovery.zip'
        self.digest = package.prepare(RUNTIME, self.path)
        self.root = self.base / 'package'
        with zipfile.ZipFile(self.path) as archive:
            archive.extractall(self.root)
        self.job = json.loads((self.root / 'recovery-manifest.json').read_bytes())

    def launch(self, name):
        out = self.base / name
        result = subprocess.run([PS, '-NoProfile', '-NonInteractive', '-ExecutionPolicy', 'Bypass',
            '-File', str(self.root / 'support/Invoke-OwnerRecovery.ps1'), '-PackageZip', str(self.path),
            '-ExpectedZipSha256', self.digest, '-OutputDirectory', str(out)],
            capture_output=True, text=True, errors='replace', timeout=60)
        self.assertTrue((out / 'recovery-report.json').is_file(), result.stdout + result.stderr)
        return result, json.loads((out / 'recovery-report.json').read_bytes()), json.loads((out / 'process-exit.json').read_bytes())

    def test_final_package_preflight_and_tamper_before_docker(self):
        result, report, process = self.launch('good')
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(report['status'], 'PACKAGE_PREFLIGHT_COMPLETE')
        self.assertFalse(report['dockerInvoked'])
        self.assertEqual(process['processExitCode'], 0)
        (self.root / 'source/ui-v2/src/main.jsx').write_bytes(b'synthetic-tamper')
        result, report, process = self.launch('tampered')
        self.assertEqual(result.returncode, 1)
        self.assertEqual(report['failureStage'], 'package-preflight')
        self.assertFalse(report['dockerInvoked'])
        self.assertEqual(process['processExitCode'], 1)

    def test_actual_compose_normalization_and_mutation_denial(self):
        config = self.base / 'config'
        config.mkdir()
        (config / 'config.json').write_text('{}')
        env = {k: v for k, v in os.environ.items() if k.upper() in (
            'PATH', 'PATHEXT', 'SYSTEMROOT', 'WINDIR', 'COMSPEC', 'APPDATA', 'LOCALAPPDATA',
            'PROGRAMFILES', 'PROGRAMFILES(X86)', 'PROGRAMDATA', 'USERPROFILE', 'HOME', 'TEMP', 'TMP', 'TMPDIR')}
        values = {key: 'a' * 96 for key in ('NEO4J_PASSWORD', 'LLM_MASTER_SECRET',
            'DG_SERVICE_TOKEN', 'DG_BOOTSTRAP_ADMIN_PASSWORD')}
        values['RECOVERY_KEY'] = 'b' * 64
        env.update(values)
        project = 'dg-recovery-' + 'a' * 32
        for filename in ('source-compose.json', 'destination-compose.json'):
            result = subprocess.run([shutil.which('docker'), '--host', 'npipe:////./pipe/docker_engine',
                '--config', str(config), 'compose', '--env-file', str(self.root/'support/empty-env.txt'),
                '--project-directory', str(self.root), '--file', str(self.root/filename),
                '--project-name', project, '--profile', 'maintenance', 'config', '--format', 'json'],
                cwd=self.root, env=env, capture_output=True, text=True, errors='replace', timeout=30)
            self.assertEqual(result.returncode, 0, 'offline Compose failed')
            model = json.loads(result.stdout)
            def check(value):
                p = self.base/'normalized.json'
                p.write_text(json.dumps(value))
                c = dict(Root=str(self.root), Project=project, Files=self.job['files'], Compose=filename,
                    Images=dict(self.job['images'], snapshot=self.job['images']['data-service'],
                                **{'graph-admin': self.job['images']['neo4j']}), Environment=values)
                cp = self.base/'context.json'
                cp.write_text(json.dumps(c))
                return execution.ExecutionTests().helper(f"$c=Get-Content {quote(cp)} -Raw|ConvertFrom-Json;"
                    "$files=@{};foreach($p in $c.Files.PSObject.Properties){$files[$p.Name]=$p.Value};$c.Files=$files;"
                    "$ev=@{};foreach($p in $c.Environment.PSObject.Properties){$ev[$p.Name]=$p.Value};$c.Environment=$ev;"
                    f"$m=Get-Content {quote(p)} -Raw|ConvertFrom-Json;try{{Assert-RecoveryModel $m $c}}catch{{[Console]::Error.WriteLine($_.ScriptStackTrace);exit 1}}")
            good = check(model)
            self.assertEqual(good.returncode, 0, good.stdout + good.stderr)
            def change_target(m):
                m['services']['snapshot']['volumes'][0]['target'] = '/wrong'
            def change_env(m):
                m['services']['data-service']['environment']['DG_DATA_DIR'] = '/wrong'
            def writable(m):
                m['services']['snapshot']['volumes'][-1]['read_only'] = False
            def health(m):
                m['services']['neo4j']['healthcheck']['test'] = ['CMD', 'true']
            def extra_option(m):
                m['services']['snapshot']['volumes'][0]['volume'] = {'subpath': 'other'}
            def network_options(m):
                m['services']['data-service']['networks']['sandbox'] = {'aliases': ['other']}
            for mutate in (change_target, change_env, writable, health, extra_option, network_options):
                bad = copy.deepcopy(model)
                mutate(bad)
                with self.subTest(filename=filename, mutation=mutate.__name__):
                    self.assertNotEqual(check(bad).returncode, 0)


if __name__ == '__main__':
    unittest.main()
