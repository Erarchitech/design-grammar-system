"""Real Compose config normalization only; never contact a Docker daemon."""
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
import test_image_runtime_execution as execution
from test_image_runtime_execution import quote


class ComposeNormalizationTests(unittest.TestCase):
    def test_actual_compose_output_validates_and_overrides_remain_denied(self):
        with tempfile.TemporaryDirectory(prefix='dg-real-config-', dir='C:/Users/Admin/AppData/Local/hermes/cache/scratch') as tmp:
            root = Path(tmp) / 'package'
            with zipfile.ZipFile('C:/Users/Admin/Downloads/DG-image-runtime-c82b92b-v1.zip') as archive:
                archive.extractall(root)
            config = Path(tmp) / 'config'
            config.mkdir()
            (config / 'config.json').write_text('{}')
            env = {k: v for k, v in os.environ.items() if k.upper() in (
                'PATH', 'PATHEXT', 'SYSTEMROOT', 'WINDIR', 'COMSPEC', 'APPDATA', 'LOCALAPPDATA',
                'PROGRAMFILES', 'PROGRAMFILES(X86)', 'PROGRAMDATA', 'USERPROFILE', 'HOME', 'TEMP', 'TMP', 'TMPDIR')}
            for key in ('NEO4J_PASSWORD', 'LLM_MASTER_SECRET', 'DG_SERVICE_TOKEN', 'DG_BOOTSTRAP_ADMIN_PASSWORD'):
                env[key] = 'explicit-offline-synthetic-config-12345678'
            env['DOCKER_CONFIG'] = str(config)
            project = 'dg-image-' + 'a' * 32
            result = subprocess.run([shutil.which('docker'), '--host', 'npipe:////./pipe/docker_engine',
                '--config', str(config), 'compose', '--env-file', str(root / 'support/empty-env.txt'),
                '--project-directory', str(root), '--file', str(root / 'compose.json'),
                '--project-name', project, 'config', '--format', 'json'], cwd=root, env=env,
                capture_output=True, text=True, errors='replace', timeout=30)
            self.assertEqual(result.returncode, 0, 'actual offline Compose config failed')
            model = json.loads(result.stdout)
            job = json.loads((root / 'image-runtime-manifest.json').read_bytes())
            helper = execution.ExecutionTests()
            def check(value):
                model_path = Path(tmp) / 'normalized.json'
                model_path.write_text(json.dumps(value))
                return helper.helper(f"$m=Get-Content -LiteralPath {quote(model_path)} -Raw|ConvertFrom-Json; "
                    f"$j={quote(json.dumps(job))}|ConvertFrom-Json; Assert-IsolatedComposeModel $m $j {quote(root)} '{project}'")
            valid = check(model)
            self.assertEqual(valid.returncode, 0, valid.stdout + valid.stderr)
            import copy
            for field, value in [('entrypoint', []), ('command', []), ('entrypoint', ['evil']), ('command', ''), ('ports', [])]:
                bad = copy.deepcopy(model)
                bad['services']['data-service'][field] = value
                with self.subTest(field=field, value=value):
                    self.assertNotEqual(check(bad).returncode, 0)
            bad = copy.deepcopy(model)
            bad['networks']['sandbox']['ipam'] = {'driver': 'default'}
            self.assertNotEqual(check(bad).returncode, 0)


if __name__ == '__main__':
    unittest.main()
