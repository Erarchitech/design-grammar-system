"""Exercise read-only diagnostic projection in real PS5, no daemon."""
import json
from pathlib import Path
import shutil
import subprocess
import unittest

HERE = Path(__file__).resolve().parents[1]
SCRIPT = HERE / 'recovery-test/Get-RecoveryDiagnostic.ps1'


class DiagnosticTests(unittest.TestCase):
    def run_projection(self, fail=False):
        body = SCRIPT.read_text().split('$result=[ordered]', 1)[1]
        fixture = r'''
$ErrorActionPreference='Stop';Set-StrictMode -Version Latest
function Assert-True($v){if(-not $v){throw 'assertion'}}
$expected='e430407e70a21af210a0a3d8816ca01f2fc8c54844b82dd879eb8a959e56b135'
$p='dg-recovery-'+('a'*32)
function Read-DiagnosticDocker([string[]]$cmd){
 if($script:fail){throw 'PRIVATE-NATIVE-ERROR'}
 if($cmd[1] -eq 'ls'){
  if($cmd -contains 'label=com.docker.compose.project'){return $p}
  if($cmd -contains 'name=^dg-recovery-'){return ($p+'_graph')}
  if($cmd[0] -eq 'container'){return ('b'*64)}
  return ($p+'_'+$(if($cmd[0] -eq 'network'){'sandbox'}else{'graph'}))
 }
 if($cmd[1] -ne 'inspect'){throw 'MUTATION'}
 if($cmd[0] -eq 'container'){
 return (@{Owner='graph-admin';Image='sha256:0efd832ad89fcc0526e80abf8b26bb79f196ebe87eac655c6f19c08c5be766b8';State='running';Exit=0;Mounts=@(@{Type='volume';Name=('c'*64);Destination='/logs';Source='PRIVATE-HOST-PATH'},@{Type='bind';Source='PRIVATE-HOST-PATH'})}|ConvertTo-Json -Depth 5 -Compress)
 }
 $o=if($cmd[0] -eq 'network'){'sandbox'}else{'graph'}
 return (@{Name=$p+'_'+$o;Owner=$o}|ConvertTo-Json -Compress)
}
'''
        command = fixture + '$script:fail=$' + str(fail).lower() + ';$result=[ordered]' + body
        return subprocess.run([shutil.which('powershell.exe'), '-NoProfile', '-NonInteractive', '-Command', command], capture_output=True, text=True, errors='replace', timeout=30)

    def test_projection_reports_only_allowlisted_fields(self):
        result = self.run_projection()
        self.assertEqual(result.returncode, 0, result.stderr)
        value = json.loads(result.stdout)
        self.assertTrue(value['completed'])
        self.assertEqual(len(value['containers']), 1)
        item = value['containers'][0]
        self.assertEqual(set(item), {'project', 'service', 'state', 'exitCode', 'imageMatches', 'volumes'})
        self.assertTrue(item['volumes'][0]['anonymousName'])
        self.assertFalse(item['volumes'][0]['knownProjectVolume'])
        self.assertNotIn('PRIVATE', result.stdout + result.stderr)

    def test_failure_never_returns_native_error(self):
        result = self.run_projection(fail=True)
        self.assertEqual(result.returncode, 1)
        value = json.loads(result.stdout)
        self.assertFalse(value['completed'])
        self.assertEqual(value['failureSection'], 'project-list')
        self.assertNotIn('PRIVATE', result.stdout + result.stderr)


if __name__ == '__main__':
    unittest.main()
