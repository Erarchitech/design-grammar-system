"""Owned failed-attempt cleanup offline contracts, no Docker daemon."""
import json
from pathlib import Path
import shutil
import subprocess
import unittest

HERE = Path(__file__).resolve().parents[1]


class CleanupTests(unittest.TestCase):
    def exercise(self, foreign=False, consumer=False):
        body = (HERE / 'recovery-test/Remove-FailedRecovery.ps1').read_text().split('$result=[ordered]', 1)[1]
        def q(p):
            return "'" + str(p).replace("'", "''") + "'"
        fixture = f". {q(HERE / 'image-runtime/runtime-execution.ps1')};. {q(HERE / 'recovery-test/execution.ps1')};"
        fixture += r'''
$ErrorActionPreference='Stop';Set-StrictMode -Version Latest
function Assert-True($v){if(-not $v){throw 'assertion'}}
$p='dg-recovery-3b9148574bb84061babce755691900d3'
$context=@{Project=$p;Images=[pscustomobject]@{'graph-admin'='sha256:abc';snapshot='sha256:def'}}
$script:removedContainer=$false;$script:removedVolume=$false
$script:calls=New-Object 'Collections.Generic.List[string]'
function Get-IsolatedResources {
 $c=@();if(-not $script:removedContainer){$c=@('c')}
 $v=@();if(-not $script:removedVolume){$v=@($p+'_graph')}
 return @{containers=$c;volumes=$v;networks=@()}
}
function Invoke-RecoveryDocker {param($ctx,$cmd,$seconds,$limit)
 $script:calls.Add(($cmd -join ' '))
 if($cmd[1] -ceq 'inspect'){
  if($cmd[0] -ceq 'container'){
   $vol=if($script:foreign){'other-project_graph'}else{$p+'_graph'}
   return (@{Name='/'+$p+'-graph-admin-1';Owner='graph-admin';Project=$p;Image='sha256:abc';Mounts=@(@{Type='volume';Name=$vol})}|ConvertTo-Json -Depth 5 -Compress)
  }
  return (@{Name=$p+'_graph';Owner='graph';Project=$p}|ConvertTo-Json -Compress)
 }
 if($cmd[0] -ceq 'container' -and $cmd[1] -ceq 'ls'){
  if($script:consumer){return 'foreign-consumer'}
  if(-not $script:removedContainer){return 'c'}
  return ''
 }
 if($cmd[0] -ceq 'container' -and $cmd[1] -ceq 'rm'){$script:removedContainer=$true;return ''}
 if($cmd[0] -ceq 'volume' -and $cmd[1] -ceq 'rm'){$script:removedVolume=$true;return ''}
 return ''
}
'''
        fixture += f"$script:foreign=${str(foreign).lower()};$script:consumer=${str(consumer).lower()};"
        # Replace only output/exit tail so fixture calls can be asserted too.
        body = body.split('ConvertTo-Json -InputObject $result', 1)[0]
        script = fixture + '$result=[ordered]' + body + "@{report=$result;calls=@($script:calls)}|ConvertTo-Json -Depth 10 -Compress"
        result = subprocess.run([shutil.which('powershell.exe'), '-NoProfile', '-NonInteractive', '-Command', script], capture_output=True, text=True, errors='replace', timeout=30)
        self.assertEqual(result.returncode, 0, result.stderr)
        return json.loads(result.stdout)

    def test_verified_removal_then_vacancy(self):
        value = self.exercise()
        self.assertEqual(value['report']['status'], 'OWNED_CLEANUP_COMPLETE')
        self.assertTrue(value['report']['cleanupVerified'])
        calls = value['calls']
        self.assertLess(next(i for i, c in enumerate(calls) if c.startswith('container rm')), next(i for i, c in enumerate(calls) if c.startswith('volume rm')))
        self.assertFalse(any(c.startswith('volume rm --force') for c in calls))

    def test_foreign_volume_refuses_all_mutations(self):
        value = self.exercise(foreign=True)
        self.assertEqual(value['report']['failureStage'], 'ownership')
        self.assertFalse(any(' rm ' in c for c in value['calls']))

    def test_foreign_consumer_refuses_all_mutations(self):
        value = self.exercise(consumer=True)
        self.assertEqual(value['report']['failureStage'], 'volume-consumers')
        self.assertFalse(any(' rm ' in c for c in value['calls']))


if __name__ == '__main__':
    unittest.main()
