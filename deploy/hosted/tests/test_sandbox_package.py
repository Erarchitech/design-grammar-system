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


class SandboxPackageTests(unittest.TestCase):
    def test_builder_exports_committed_revision_only_and_verifies_contents(self):
        with tempfile.TemporaryDirectory() as temp:
            destination = Path(temp) / 'sandbox.zip'
            revision = subprocess.check_output(['git', '-C', str(ROOT), 'rev-parse', 'HEAD'], text=True).strip()
            command = [sys.executable, str(HOSTED / 'build_sandbox.py'), '--repo', str(ROOT),
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

    def test_manifest_rejects_changed_zip_member(self):
        with tempfile.TemporaryDirectory() as temp:
            destination = Path(temp) / 'sandbox.zip'
            revision = subprocess.check_output(['git', '-C', str(ROOT), 'rev-parse', 'HEAD'], text=True).strip()
            command = [sys.executable, str(HOSTED / 'build_sandbox.py'), '--repo', str(ROOT),
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
