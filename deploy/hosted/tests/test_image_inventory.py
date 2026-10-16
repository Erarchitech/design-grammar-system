"""Offline PowerShell checks; never invoke Docker, including for runtime tests.

Uses the already issued, pinned ZIP (DG_IMAGE_INVENTORY_PACKAGE may locate it).
All extraction and reports are below the Hermes scratch directory.
"""
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest
import zipfile

ROOT = Path(__file__).resolve().parents[3]
SCRIPT = ROOT / 'deploy/hosted/bundle-test/Collect-ImageInventory.ps1'
ZIP_SHA = '1e032824fbb3006d3e001a3460185a97e1d4661941910671f6f4f62ecc4af87e'
REVISION = '2dedbfb3e138c2b437e781696197105dca93342a'
CANDIDATE_SHA = '864878de1e60aadc79211f20e574f32cb5f97a096c06dac696a1f52215f04810'
IMAGES = {
    'neo4j': 'dg-hosted-1309-sandbox-neo4j:latest',
    'data-service': 'dg-hosted-1309-sandbox-data-service:latest',
    'n8n': 'n8nio/n8n:2.4.8',
}


def ps_quote(value):
    return "'" + str(value).replace("'", "''") + "'"


class ImageInventoryTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.powershell = shutil.which('powershell.exe') or shutil.which('pwsh')
        if not cls.powershell:
            raise AssertionError('real PowerShell is required')
        cls.scratch = Path(os.environ.get('TMPDIR', Path.home() / 'AppData/Local/hermes/cache/scratch'))
        cls.scratch.mkdir(parents=True, exist_ok=True)
        cls.temp = tempfile.TemporaryDirectory(prefix='dg-image-inventory-', dir=cls.scratch)
        cls.base = Path(cls.temp.name)
        cls.package = Path(os.environ.get('DG_IMAGE_INVENTORY_PACKAGE',
                           str(Path.home() / 'Downloads/DG-candidate-test-2dedbfb-DESKTOP-OS4Q8CP.zip')))
        if not cls.package.is_file():
            raise AssertionError('issued package required; set DG_IMAGE_INVENTORY_PACKAGE')
        if hashlib.sha256(cls.package.read_bytes()).hexdigest() != ZIP_SHA:
            raise AssertionError('issued package SHA256 mismatch')
        cls.extracted = cls.base / 'package'
        with zipfile.ZipFile(cls.package) as archive:
            archive.extractall(cls.extracted)
        print('Offline package SHA256: ' + ZIP_SHA)

    @classmethod
    def tearDownClass(cls):
        cls.temp.cleanup()

    def run_ps(self, command):
        return subprocess.run([self.powershell, '-NoProfile', '-NonInteractive', '-Command', command],
                              capture_output=True, text=True, encoding='utf-8', errors='replace', timeout=90)

    def invoke(self, root=None, report=None, package=None, preflight=True):
        report = report or self.base / (self._testMethodName + '.json')
        command = ('& ' + ps_quote(SCRIPT) + ' -PackageZip ' + ps_quote(package or self.package)
                   + ' -PackageRoot ' + ps_quote(root or self.extracted)
                   + ' -ReportPath ' + ps_quote(report)
                   + (' -PreflightOnly' if preflight else ''))
        return self.run_ps(command), report

    def test_preflight_verifies_issued_package_without_docker(self):
        result, report = self.invoke()
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        data = json.loads(report.read_text(encoding='utf-8-sig'))
        self.assertEqual(data['status'], 'PREFLIGHT_ONLY')
        self.assertFalse(data['dockerInvoked'])
        self.assertEqual(data['zipSha256'], ZIP_SHA)
        self.assertEqual(data['frameworkRevision'], REVISION)
        self.assertEqual(data['candidateManifestSha256'], CANDIDATE_SHA)
        self.assertEqual(data['requestedImages'], IMAGES)
        self.assertEqual(data['images'], [])
        self.assertFalse(data['releaseAcceptance'])
        self.assertEqual(data['historicalRunImageBinding'], 'not-established')
        print('Issued ZIP preflight: PREFLIGHT_ONLY; dockerInvoked=false; exit=0')

    def functions(self):
        # Load declarations only via PowerShell AST: never execute script body/Docker.
        return ("$t=$null;$e=$null;$ast=[System.Management.Automation.Language.Parser]::ParseFile("
                + ps_quote(SCRIPT) + ",[ref]$t,[ref]$e);"
                "foreach ($f in $ast.FindAll({param($n) $n -is [System.Management.Automation.Language.FunctionDefinitionAst]},$false)) "
                "{ . ([scriptblock]::Create($f.Extent.Text)) }; ")

    def test_fixed_inspect_arguments_and_sanitized_observation(self):
        command = self.functions() + """
$ErrorActionPreference='Stop'
$args = @(New-ImageInspectArguments 'n8nio/n8n:2.4.8')
$raw = @{ Id=('sha256:' + ('a'*64)); RepoDigests=@(); Os='linux'; Architecture='amd64'; Env='DO-NOT-COPY' } | ConvertTo-Json -Compress
$o = Convert-ImageObservation 'n8n' 'n8nio/n8n:2.4.8' $raw
@{ arguments=$args; observation=$o } | ConvertTo-Json -Depth 8
"""
        result = self.run_ps(command)
        self.assertEqual(result.returncode, 0, result.stderr)
        data = json.loads(result.stdout)
        args = data['arguments']
        self.assertEqual(args[:5], ['--host', 'npipe:////./pipe/docker_engine', 'image', 'inspect', '--format'])
        self.assertEqual(args[-1], IMAGES['n8n'])
        self.assertEqual(json.loads(args[5].replace('{{json .Id}}', 'null').replace('{{json .RepoDigests}}', 'null')
                                   .replace('{{json .Os}}', 'null').replace('{{json .Architecture}}', 'null')),
                         dict.fromkeys(['Id', 'RepoDigests', 'Os', 'Architecture']))
        observation = data['observation']
        self.assertEqual(set(observation), {'service', 'image', 'status', 'localConfigImageId',
                                           'registryRepoDigests', 'os', 'architecture'})
        self.assertEqual(observation['status'], 'UNRESOLVED_REGISTRY_DIGEST')
        self.assertEqual(observation['registryRepoDigests'], [])
        self.assertEqual(observation['localConfigImageId'], 'sha256:' + 'a' * 64)
        self.assertNotIn('DO-NOT-COPY', result.stdout)

    def test_bad_image_name_and_bad_digest_are_rejected(self):
        command = self.functions() + """
$ErrorActionPreference='Stop'
$count=0
try { New-ImageInspectArguments 'unapproved:latest' | Out-Null } catch { $count++ }
try { Convert-ImageObservation 'n8n' 'n8nio/n8n:2.4.8' '{"Id":"secret","RepoDigests":[],"Os":"linux","Architecture":"amd64"}' | Out-Null } catch { $count++ }
try { Convert-ImageObservation 'n8n' 'n8nio/n8n:2.4.8' ('{"Id":"sha256:' + ('a'*64) + '","RepoDigests":["secret"],"Os":"linux","Architecture":"amd64"}') | Out-Null } catch { $count++ }
Write-Output $count
"""
        result = self.run_ps(command)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout.strip(), '3')

    def test_preflight_blocks_changed_extracted_member(self):
        changed = self.base / 'changed'
        shutil.copytree(self.extracted, changed)
        (changed / 'compose.json').write_text('SECRET-MARKER')
        result, report = self.invoke(root=changed)
        self.assertEqual(result.returncode, 1)
        data = json.loads(report.read_text(encoding='utf-8-sig'))
        self.assertEqual(data['failureStage'], 'package-integrity')
        self.assertFalse(data['dockerInvoked'])
        self.assertNotIn('SECRET-MARKER', report.read_text())

    def test_preflight_blocks_extra_env_without_reading_it(self):
        changed = self.base / 'extra'
        shutil.copytree(self.extracted, changed)
        (changed / '.env').write_text('SECRET-MARKER=never-load')
        result, report = self.invoke(root=changed)
        self.assertEqual(result.returncode, 1)
        self.assertFalse(json.loads(report.read_text())['dockerInvoked'])
        self.assertNotIn('SECRET-MARKER', report.read_text())

    def test_preflight_blocks_unapproved_original_zip(self):
        changed = self.base / 'changed.zip'
        changed.write_bytes(self.package.read_bytes() + b'changed')
        result, report = self.invoke(package=changed)
        self.assertEqual(result.returncode, 1)
        data = json.loads(report.read_text())
        self.assertEqual(data['failureStage'], 'zip-integrity')
        self.assertFalse(data['dockerInvoked'])

    def test_output_never_overwrites_or_enters_package(self):
        existing = self.base / 'existing.json'
        existing.write_text('keep-me')
        result, _ = self.invoke(report=existing)
        self.assertEqual(result.returncode, 1)
        self.assertEqual(existing.read_text(), 'keep-me')
        inside = self.extracted / 'inventory.json'
        result, _ = self.invoke(report=inside)
        self.assertEqual(result.returncode, 1)
        self.assertFalse(inside.exists())

    def test_runtime_host_guard_and_inspect_only_contract(self):
        source = SCRIPT.read_text()
        self.assertNotIn('runtime not implemented', source)
        self.assertIn("$stage = 'host-guard'", source)
        self.assertIn("$report.status = 'OBSERVED_NOW'", source)
        self.assertNotIn("$report.status = 'PASS'", source)
        self.assertEqual(source.count('[void]$p.Start()'), 1)
        command = self.functions() + """
$ErrorActionPreference='Stop'
if ([Environment]::MachineName.ToUpperInvariant() -eq 'DESKTOP-OS4Q8CP') { Assert-TargetHost; Write-Output 'target' }
else { try { Assert-TargetHost; exit 1 } catch { Write-Output 'blocked-nontarget' } }
"""
        result = self.run_ps(command)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn(result.stdout.strip(), ['target', 'blocked-nontarget'])

    def test_registry_digest_is_not_replaced_by_config_id(self):
        command = self.functions() + """
$ErrorActionPreference='Stop'
$raw = @{ Id=('sha256:' + ('a'*64)); RepoDigests=@('n8nio/n8n@sha256:' + ('b'*64)); Os='linux'; Architecture='amd64' } | ConvertTo-Json -Compress
Convert-ImageObservation 'n8n' 'n8nio/n8n:2.4.8' $raw | ConvertTo-Json -Depth 8
"""
        result = self.run_ps(command)
        self.assertEqual(result.returncode, 0, result.stderr)
        data = json.loads(result.stdout)
        self.assertEqual(data['status'], 'OBSERVED_NOW')
        self.assertEqual(data['registryRepoDigests'], ['n8nio/n8n@sha256:' + 'b' * 64])
        self.assertNotIn(data['localConfigImageId'], data['registryRepoDigests'])

    def test_collector_exists_and_parses_in_real_powershell(self):
        self.assertTrue(SCRIPT.is_file(), 'read-only collector is not implemented')
        powershell = shutil.which('powershell.exe') or shutil.which('pwsh')
        self.assertIsNotNone(powershell, 'real PowerShell is required, not a skip')
        command = (
            '$tokens=$null; $errors=$null; '
            '[void][System.Management.Automation.Language.Parser]::ParseFile('
            + ps_quote(SCRIPT) + ',[ref]$tokens,[ref]$errors); '
            'if ($errors.Count) { $errors | ForEach-Object { $_.Message }; exit 1 }; '
            'Write-Output "PowerShell parser: OK"'
        )
        result = subprocess.run([powershell, '-NoProfile', '-NonInteractive', '-Command', command],
                                capture_output=True, text=True, timeout=30)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)


if __name__ == '__main__':
    unittest.main(verbosity=2)
