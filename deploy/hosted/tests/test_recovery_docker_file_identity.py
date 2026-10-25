"""File-resource identity only: no Docker process or daemon operation."""
import json
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest

SCRIPT = Path(__file__).resolve().parents[1] / 'recovery-test' / 'Collect-DockerFileIdentity.ps1'
SCRATCH = 'C:/Users/Admin/AppData/Local/hermes/cache/scratch'


def quote(s):
    return "'" + str(s).replace("'", "''") + "'"


class DockerFileIdentityTests(unittest.TestCase):
    def run_ps(self, command):
        ps = shutil.which('powershell.exe')
        self.assertIsNotNone(ps)
        return subprocess.run([ps, '-NoProfile', '-NonInteractive', '-Command', command],
                              capture_output=True, text=True, encoding='utf-8', errors='replace', timeout=60)

    def test_preflight_no_file_observations_and_exclusive_report(self):
        self.assertTrue(SCRIPT.is_file(), 'file identity collector absent')
        with tempfile.TemporaryDirectory(dir=SCRATCH) as temp:
            report = Path(temp) / 'preflight.json'
            command = '& ' + quote(SCRIPT) + ' -PreflightOnly -ReportPath ' + quote(report) + '; exit $LASTEXITCODE'
            r = self.run_ps(command)
            self.assertEqual(r.returncode, 0, r.stderr)
            d = json.loads(report.read_text(encoding='utf-8-sig'))
            self.assertEqual(d['status'], 'PREFLIGHT_ONLY')
            self.assertIs(d['dockerInvoked'], False)
            self.assertEqual(d['nativeCommandsStarted'], 0)
            self.assertEqual(d['files'], [])
            before = report.read_bytes()
            self.assertNotEqual(self.run_ps(command).returncode, 0)
            self.assertEqual(report.read_bytes(), before)

    def test_full_synthetic_pe_metadata_without_execution(self):
        self.assertTrue(SCRIPT.is_file(), 'file identity collector absent')
        import hashlib
        with tempfile.TemporaryDirectory(dir=SCRATCH) as temp:
            root = Path(temp)
            install = root / 'install'
            docker = install / 'resources' / 'bin' / 'docker.exe'
            plugin = install / 'resources' / 'cli-plugins' / 'docker-compose.exe'
            docker.parent.mkdir(parents=True); plugin.parent.mkdir(parents=True)
            marker = root / 'MUST-NOT-EXECUTE'
            marker_cs = str(marker).replace('\\', '\\\\').replace('"', '\\"')
            code = ('using System.Reflection; [assembly: AssemblyFileVersion("1.2.3.4")] '
                    '[assembly: AssemblyInformationalVersion("1.2.3+synthetic")] '
                    'public class NeverExecute { public static int Main() { '
                    'System.IO.File.WriteAllText("' + marker_cs + '","EXECUTED");return 91;}}')
            c = self.run_ps('Add-Type -TypeDefinition ' + quote(code) + ' -OutputAssembly ' + quote(docker) + ' -OutputType ConsoleApplication')
            self.assertEqual(c.returncode, 0, c.stderr)
            plugin.write_bytes(docker.read_bytes())
            source = SCRIPT.read_text(encoding='utf-8')
            host = "Require-DFI ($Name -ceq 'DESKTOP-OS4Q8CP')"
            assignment = "$install=Join-Path ([Environment]::GetFolderPath('ProgramFiles')) 'Docker\\Docker'"
            self.assertIn(host, source); self.assertIn(assignment, source)
            source = source.replace(host, 'Require-DFI $true').replace(assignment, '$install=' + quote(install))
            script = root / 'synthetic.ps1'; script.write_text(source, encoding='utf-8')
            report = root / 'identity.json'
            r = self.run_ps('& ' + quote(script) + ' -ReportPath ' + quote(report) + '; exit $LASTEXITCODE')
            self.assertEqual(r.returncode, 0, r.stderr + r.stdout)
            d = json.loads(report.read_text(encoding='utf-8-sig'))
            self.assertEqual(d['status'], 'FILES_OBSERVED')
            self.assertEqual([x['slot'] for x in d['files']], ['resources/bin/docker.exe', 'resources/cli-plugins/docker-compose.exe'])
            self.assertEqual(len(d['files']), 2)
            for x in d['files']:
                self.assertEqual(x['sha256'], hashlib.sha256(docker.read_bytes()).hexdigest())
                self.assertEqual(x['fileVersion'], '1.2.3.4')
                self.assertEqual(x['productVersion'], '1.2.3+synthetic')
                self.assertEqual(x['bytes'], docker.stat().st_size)
                self.assertEqual(x['status'], 'OBSERVED')
            self.assertIs(d['dockerInvoked'], False)
            self.assertEqual(d['nativeCommandsStarted'], 0)
            self.assertIs(d['runtimeVersionProven'], False)
            self.assertIs(d['nativeRecoveryProven'], False)
            self.assertFalse(marker.exists())
            plugin.unlink()
            report = root / 'missing-plugin.json'
            r = self.run_ps('& ' + quote(script) + ' -ReportPath ' + quote(report) + '; exit $LASTEXITCODE')
            self.assertEqual(r.returncode, 2, r.stderr + r.stdout)
            d = json.loads(report.read_text(encoding='utf-8-sig'))
            self.assertEqual(d['status'], 'UNRESOLVED')
            self.assertEqual(d['files'][0]['status'], 'OBSERVED')
            self.assertEqual(d['files'][1]['failureStage'], 'FILE_GUARD')
            self.assertIsNone(d['files'][1]['sha256'])
            self.assertNotIn(str(root), report.read_text(encoding='utf-8-sig') + r.stdout + r.stderr)
            self.assertFalse(marker.exists())

    def test_invalid_metadata_host_and_paths_fail_closed(self):
        self.assertTrue(SCRIPT.is_file(), 'file identity collector absent')
        load = ('$t=$null;$e=$null;$a=[System.Management.Automation.Language.Parser]::ParseFile('
                + quote(SCRIPT) + ',[ref]$t,[ref]$e);if($e.Count){throw "parse"};'
                'foreach($f in $a.FindAll({param($n)$n -is [System.Management.Automation.Language.FunctionDefinitionAst]},$false))'
                '{. ([scriptblock]::Create($f.Extent.Text))};')
        r = self.run_ps(load + '''$ErrorActionPreference='Stop';$n=0;
try{Assert-DFIHost 'WRONG-HOST'}catch{$n++};
try{Assert-DFIPath '\\\\server\\share'}catch{$n++};
try{Assert-DFIPath 'C:\\file:stream'}catch{$n++};
@{rejections=$n;valid=(Convert-DFIVersion '29.1.2+build.4');invalid=@(
 (Convert-DFIVersion 'PRIVATE-MARKER'),
 (Convert-DFIVersion '1.2 C:/private/owner'),
 (Convert-DFIVersion ('1'+('a'*128))),
 (Convert-DFIVersion "1.2`nPRIVATE-MARKER")
)}|ConvertTo-Json -Depth 5''')
        self.assertEqual(r.returncode, 0, r.stderr)
        d = json.loads(r.stdout)
        self.assertEqual(d['rejections'], 3)
        self.assertEqual(d['valid'], '29.1.2+build.4')
        self.assertEqual(d['invalid'], [None] * 4)
        self.assertNotIn('PRIVATE-MARKER', r.stdout)


if __name__ == '__main__':
    unittest.main()
