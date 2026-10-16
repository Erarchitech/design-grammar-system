"""Actual PowerShell 5.1, no Docker. Fixture failures must precede Docker."""
import json
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest
import sys

HERE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(HERE))
import build_image_runtime as package

PS = shutil.which('powershell.exe')
SCRATCH = Path('C:/Users/Admin/AppData/Local/hermes/cache/scratch')
RUNNER = HERE / 'image-runtime/Run-ImageRuntime.ps1'
BUILD_ZIP = Path('C:/Users/Admin/Downloads/DG-controlled-build-c82b92b-v2.zip')


def quote(value):
    return "'" + str(value).replace("'", "''") + "'"


@unittest.skipUnless(PS, 'Windows PowerShell required')
class RuntimeRunnerTests(unittest.TestCase):
    def helper(self, code):
        return subprocess.run([PS, '-NoProfile', '-NonInteractive', '-Command',
                               "$ErrorActionPreference='Stop'; $t=$null; $e=$null; "
                               f"$ast=[System.Management.Automation.Language.Parser]::ParseFile({quote(RUNNER)},[ref]$t,[ref]$e); "
                               "if($e.Count){throw 'parse failed'}; "
                               "$ast.FindAll({param($n) $n -is [System.Management.Automation.Language.FunctionDefinitionAst]},$false) | "
                               "ForEach-Object { . ([scriptblock]::Create($_.Extent.Text)) }; " + code],
                              capture_output=True, text=True, errors='replace', timeout=40)

    def test_archive_hash_and_size_verified_before_docker(self):
        with tempfile.TemporaryDirectory(prefix='dg-tar-hash-', dir=SCRATCH) as tmp:
            base = Path(tmp)
            data = b'explicit synthetic archive fixture, not target evidence'
            (base / 'neo4j.tar').write_bytes(data)
            import hashlib
            image = {'neo4j': {'archive': 'neo4j.tar', 'archiveSha256': hashlib.sha256(data).hexdigest(), 'archiveBytes': len(data)}}
            contract = base / 'contract.json'
            contract.write_text(json.dumps(image))
            code = f"$images=Get-Content -LiteralPath {quote(contract)} -Raw | ConvertFrom-Json; Assert-Archives {quote(base)} $images; 'VERIFIED'"
            result = self.helper(code)
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            self.assertIn('VERIFIED', result.stdout)
            (base / 'neo4j.tar').write_bytes(b'X' * len(data))
            self.assertNotEqual(self.helper(code).returncode, 0)

    def test_archive_traversal_rejected(self):
        result = self.helper("$images=[pscustomobject]@{neo4j=[pscustomobject]@{archive='../escape.tar'; archiveSha256=('a'*64); archiveBytes=1}}; Assert-Archives 'C:\\DG-test' $images")
        self.assertNotEqual(result.returncode, 0)

    def test_build_report_identity_and_typed_flags(self):
        import zipfile
        with tempfile.TemporaryDirectory(prefix='dg-report-contract-', dir=SCRATCH) as tmp:
            base = Path(tmp)
            package.prepare(BUILD_ZIP, base / 'runtime.zip')
            with zipfile.ZipFile(base / 'runtime.zip') as archive:
                archive.extractall(base / 'package')
            root = base / 'package'
            manifest = json.loads((root / 'image-runtime-manifest.json').read_bytes())
            source = json.loads((root / 'source/manifest.json').read_bytes())
            original = json.loads((root / 'support/build-job-manifest.json').read_bytes())
            # Explicit synthetic report fixture, never written as target evidence.
            build = dict(schemaVersion=1, kind='controlled-image-build-not-release',
                         status='BUILD_EXPORT_COMPLETE', failureStage=None, dockerInvoked=True,
                         releaseAccepted=False, reproducibleDependencies=False,
                         sourceRevision=package.REVISION, sourceManifestSha256=package.SOURCE_SHA,
                         packageZipSha256=package.BUILD_SHA, target='DESKTOP-OS4Q8CP',
                         dockerEndpoint='npipe:////./pipe/docker_engine', sourceManifest=source,
                         packageFiles=original['files'], runnerTooling=dict(path='support/Run-ImageBuild.ps1',
                         sha256='49a9e00c1cc856a1f7fd0419735894e598c41ae5d58414e947be7211eca00798'),
                         images={n: dict(v, status='BUILD_EXPORT_COMPLETE', iid=v['imageId'])
                                 for n, v in manifest['images'].items()})
            job_path = root / 'image-runtime-manifest.json'
            code = (f"$job=Get-Content -LiteralPath {quote(job_path)} -Raw | ConvertFrom-Json; "
                    f"Assert-BuildReport {quote(base)} {quote(root)} $job")
            report_path = base / 'build-report.json'
            report_path.write_text(json.dumps(build))
            result = self.helper(code)
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            for key, value in [('dockerInvoked', 1), ('releaseAccepted', 0), ('sourceRevision', '0' * 40),
                               ('schemaVersion', True), ('target', 'wrong-target')]:
                broken = dict(build, **{key: value})
                report_path.write_text(json.dumps(broken))
                self.assertNotEqual(self.helper(code).returncode, 0, key)
            build['images']['neo4j']['archiveBytes'] = True
            report_path.write_text(json.dumps(build))
            self.assertNotEqual(self.helper(code).returncode, 0)

    def test_actual_package_preflight_no_docker(self):
        self.assertTrue(RUNNER.is_file(), 'image runtime runner not implemented')
        with tempfile.TemporaryDirectory(prefix='dg-image-runtime-', dir=SCRATCH) as tmp:
            base = Path(tmp)
            path = base / 'runtime.zip'
            digest = package.prepare(BUILD_ZIP, path)
            import zipfile
            with zipfile.ZipFile(path) as archive:
                archive.extractall(base / 'package')
            output = base / 'output'
            result = subprocess.run([PS, '-NoProfile', '-NonInteractive', '-ExecutionPolicy', 'Bypass',
                                     '-File', str(base / 'package/support/Run-ImageRuntime.ps1'),
                                     '-PackageZip', str(path), '-ExpectedZipSha256', digest,
                                     '-OutputDirectory', str(output), '-PackagePreflightOnly'],
                                    capture_output=True, text=True, timeout=45)
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            report = json.loads((output / 'runtime-report.json').read_bytes())
            self.assertEqual(report['status'], 'PACKAGE_PREFLIGHT_COMPLETE')
            self.assertFalse(report['dockerInvoked'])
            self.assertFalse(report['releaseAccepted'])
            self.assertFalse(report['archiveBytesVerified'])
            self.assertFalse(report['crossDaemonPortabilityProven'])
            # Final extraction is itself part of the contract, not just ZIP bytes.
            (base / 'package/source/ui-v2/src/main.jsx').write_bytes(b'corrupt fixture')
            failed_output = base / 'tampered-output'
            result = subprocess.run([PS, '-NoProfile', '-NonInteractive', '-ExecutionPolicy', 'Bypass',
                                     '-File', str(base / 'package/support/Run-ImageRuntime.ps1'),
                                     '-PackageZip', str(path), '-ExpectedZipSha256', digest,
                                     '-OutputDirectory', str(failed_output), '-PackagePreflightOnly'],
                                    capture_output=True, text=True, errors='replace', timeout=45)
            self.assertNotEqual(result.returncode, 0)
            report = json.loads((failed_output / 'runtime-report.json').read_bytes())
            self.assertEqual(report['status'], 'FAILED')
            self.assertEqual(report['failureStage'], 'package-preflight')
            self.assertFalse(report['dockerInvoked'])


if __name__ == '__main__':
    unittest.main()
