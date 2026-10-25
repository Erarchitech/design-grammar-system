"""Actual PS5 orchestration-boundary tests; synthetic CLI only, never Docker."""
from pathlib import Path
import shutil
import subprocess
import unittest

HERE = Path(__file__).resolve().parents[1]
CORE = HERE / 'image-runtime/runtime-execution.ps1'
EXECUTION = HERE / 'recovery-test/multistore_execution.ps1'
MODULE = HERE / 'recovery-test/multistore_orchestrator.ps1'
PS = shutil.which('powershell.exe')


def q(value):
    return "'" + str(value).replace("'", "''") + "'"


class OrchestratorTests(unittest.TestCase):
    def run_ps(self, code):
        self.assertTrue(MODULE.is_file(), 'full multi-store orchestrator absent')
        self.assertTrue(PS, 'actual Windows PowerShell required')
        script = "$ErrorActionPreference='Stop';Set-StrictMode -Version Latest;"
        script += f'. {q(CORE)};. {q(EXECUTION)};. {q(MODULE)};' + code
        return subprocess.run([PS, '-NoProfile', '-NonInteractive', '-Command', script],
                              capture_output=True, text=True, errors='replace', timeout=40)

    def test_main_rejects_unqualified_before_any_command_and_preserves_failure(self):
        result = self.run_ps(r'''
$script:invoked=0
function Invoke-MultiProcess {$script:invoked++;throw 'must not launch'}
function Invoke-MultiCompose {$script:invoked++;throw 'must not launch'}
function Invoke-MultiDocker {$script:invoked++;throw 'must not launch'}
$job=[pscustomobject]@{queueQualification=[pscustomobject]@{status='UNQUALIFIED';nativeApplicationExecutionAllowed=$false}}
$report=@{status='FAILED';failureStage=$null;cleanupFailureStage=$null;cleanup='not-started';dockerInvoked=$false;releaseAccepted=$false;fullRecoveryAccepted=$false;checks=@{}}
try {Invoke-MultiStoreExercise 'unused-root' 'unused-output' $job $null $report;throw 'unexpected success'}
catch {if($_.Exception.Message -ceq 'unexpected success'){throw}}
if($script:invoked -ne 0 -or $report.dockerInvoked){throw 'invoked'}
if($report.failureStage -cne 'queue-profile-unqualified'){throw 'wrong stage'}
if($report.cleanup -cne 'not-started' -or $report.fullRecoveryAccepted -or $report.releaseAccepted){throw 'false acceptance'}
$report.failureStage='original-failure'
try {Invoke-MultiStoreExercise 'unused-root' 'unused-output' $job $null $report}catch{}
if($report.failureStage -cne 'original-failure'){throw 'lost first failure'}
exit 0
''')
        self.assertEqual(result.returncode, 0, result.stderr)

    def test_main_cannot_self_qualify_from_labels_or_owner_callbacks(self):
        result = self.run_ps(r'''
$script:invoked=0
function Invoke-MultiProcess {$script:invoked++;throw 'must not launch'}
function Invoke-MultiCompose {$script:invoked++;throw 'must not launch'}
function Invoke-MultiDocker {$script:invoked++;throw 'must not launch'}
foreach($qualification in @($null,
 [pscustomobject]@{status='QUALIFIED';nativeApplicationExecutionAllowed='true'},
 [pscustomobject]@{status='QUALIFIED';nativeApplicationExecutionAllowed=$true},
 [pscustomobject]@{status='QUALIFIED';nativeApplicationExecutionAllowed=$true;probe={return $true};schema='observed-now'})) {
 $report=@{status='FAILED';failureStage=$null;cleanupFailureStage=$null;cleanup='not-started';dockerInvoked=$false;releaseAccepted=$false;fullRecoveryAccepted=$false;checks=@{}}
 $job=[pscustomobject]@{queueQualification=$qualification}
 try {Invoke-MultiStoreExercise 'unused-root' 'unused-output' $job $null $report;throw 'unexpected success'}
 catch {if($_.Exception.Message -ceq 'unexpected success'){throw}}
 if($null -eq $report.failureStage -or $script:invoked -ne 0){throw 'missing admission boundary'}
 if($report.cleanup -cne 'not-started' -or $report.fullRecoveryAccepted -or $report.releaseAccepted){throw 'false acceptance'}
}
exit 0
''')
        self.assertEqual(result.returncode, 0, result.stderr)

    def test_latent_flow_stops_at_unqualified_pg_output_before_seal_or_restore(self):
        result=self.run_ps(r'''
$script:trace=New-Object 'Collections.Generic.List[string]'
function Invoke-MultiExec {param($c,$service,$cmd,$seconds,$limit)
 $script:trace.Add(($c.Side+':'+$service+':'+($cmd -join '|')))
 if($cmd -contains 'seal'){return '{"sha256":"aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"}'}
 if($cmd -contains 'negative'){return '{"positiveControl":true,"badKeyRejectedBeforeDestination":true,"corruptCiphertextRejectedBeforeDestination":true,"sourceCiphertextUnchanged":true,"nativeRecoveryProven":false}'}
 if($cmd -contains 'open'){return '{"nativeRecoveryProven":false}'}
 if($cmd -contains 'hash'){return ('{"verified":true,"sha256":"'+('c'*64)+'"}')}
 if($cmd -contains 'restore'){return '{"treeRestored":true,"nativeRecoveryProven":false}'}
 if($cmd -contains 'verify' -and $cmd -contains 'multistore_n8n'){return '{"restoredStateMatched":true,"nativeRecoveryProven":false}'}
 return ('{"verified":true,"producerBarrier":true,"schemaMatched":true,"drained":true,"fingerprint":"'+('a'*64)+'"}')
}
function Invoke-MultiCompose {param($c,$cmd,$seconds,$limit) $script:trace.Add(($c.Side+':compose:'+($cmd -join '|')));return ''}
function Get-MultiContainer {param($c,$s,$running) return ('b'*64)}
function Invoke-MultiDocker {param($c,$cmd,$seconds,$limit) $script:trace.Add(($c.Side+':docker:'+($cmd -join '|')));return ''}
function Assert-MultiOwnership {}
function Start-Sleep {}
function Assert-MultiStopped {}
$source=@{Side='source';Root='unused';Project=('dg-multi-'+('a'*32));Services=@('neo4j','dg-reasoner','data-service','design-grammars','n8n','speckle-server','speckle-frontend-2','speckle-preview-service','speckle-webhook-service','speckle-ifc-import-service','speckle-ingress')}
$destination=@{Side='destination';Root='unused';Project=('dg-multi-'+('b'*32))}
$profile=@{AgeSha256=('a'*64);KeygenSha256=('b'*64);QueueSampleSeconds=2}
$report=@{checks=@{};releaseAccepted=$false;fullRecoveryAccepted=$false}
$message=$null
try {Invoke-MultiLatentFlow $source $destination $profile 'private-output' $report} catch {$message=$_.Exception.Message}
if($message -cne 'PostgreSQL private output production unavailable: hard byte bound and container-child cleanup unqualified'){throw 'latent flow must refuse'}
$joinedTrace=$script:trace -join "`n"
$expected=@('source:snapshot:python|-B|/opt/recovery/multistore_exchange.py|init',
 'source:snapshot:python|-B|/opt/recovery/multistore_qualified_app.py|seed',
 'source:snapshot:python|-B|/opt/recovery/multistore_qualified_app.py|block-producers',
 'source:snapshot:python|-B|/opt/recovery/multistore_qualified_queue.py|sample',
 'source:compose:stop|--timeout|20')
$position=0
foreach($item in $expected){$next=$joinedTrace.IndexOf($item,$position,[StringComparison]::Ordinal);if($next -lt 0){throw ('missing/order '+$item)};$position=$next+$item.Length}
if(@($script:trace|Where-Object{$_ -like '*qualified_queue.py|sample*'}).Count -ne 8){throw 'stable samples absent'}
foreach($part in @('speckle-postgres:','graph-admin:','|seal|',':docker:','destination:')) {
 if($joinedTrace.Contains($part)){throw 'continued beyond PG refusal'}
}
if($report.checks.ContainsKey('latentFlowComplete') -or $report.fullRecoveryAccepted -or $report.releaseAccepted){throw 'false completion'}
''')
        self.assertEqual(result.returncode,0,result.stderr)

    def test_latent_archive_handoff_uses_one_exchange_child_and_mounted_tools(self):
        # Command trace only: deliberately replace PG guards to inspect the later
        # latent seam. No native command, crypto, file transfer or service runs.
        result=self.run_ps(r'''
$script:trace=New-Object 'Collections.Generic.List[string]'
function Invoke-MultiExec {param($c,$service,$cmd,$seconds,$limit)
 $script:trace.Add(($c.Side+':'+$service+':'+($cmd -join '|')))
 if($cmd -contains 'seal'){return ('{"sha256":"'+('a'*64)+'"}')}
 if($cmd -contains 'negative'){return '{"positiveControl":true,"badKeyRejectedBeforeDestination":true,"corruptCiphertextRejectedBeforeDestination":true,"sourceCiphertextUnchanged":true,"nativeRecoveryProven":false}'}
 if($cmd -contains 'open'){return '{"nativeRecoveryProven":false}'}
 if($cmd -contains 'hash'){return ('{"verified":true,"sha256":"'+('c'*64)+'"}')}
 if($cmd -contains 'restore'){return '{"treeRestored":true,"nativeRecoveryProven":false}'}
 if($cmd -contains 'verify' -and $cmd -contains 'multistore_n8n'){return '{"restoredStateMatched":true,"nativeRecoveryProven":false}'}
 return ('{"verified":true,"producerBarrier":true,"schemaMatched":true,"drained":true,"fingerprint":"'+('a'*64)+'"}')
}
function Export-MultiPostgres {param($c) $script:trace.Add('source:PG-SYNTHETIC-SEAM')}
function Restore-MultiPostgres {param($c) $script:trace.Add('destination:PG-SYNTHETIC-SEAM')}
function Invoke-MultiCompose {return ''}
function Get-MultiContainer {return ('b'*64)}
function Invoke-MultiDocker {param($c,$cmd,$seconds,$limit) $script:trace.Add(($c.Side+':docker:'+($cmd -join '|')));return ''}
function Start-Sleep {}
$source=@{Side='source';Project=('dg-multi-'+('a'*32));Services=@('neo4j','dg-reasoner','data-service','design-grammars','n8n','speckle-server','speckle-frontend-2','speckle-preview-service','speckle-webhook-service','speckle-ifc-import-service','speckle-ingress')}
$destination=@{Side='destination';Project=('dg-multi-'+('b'*32))}
$report=@{checks=@{};releaseAccepted=$false;fullRecoveryAccepted=$false}
Invoke-MultiLatentFlow $source $destination @{AgeSha256=('a'*64);QueueSampleSeconds=2} 'private-output' $report
$t=$script:trace -join "`n"
$expected=@(
 'source:snapshot:python|-B|/opt/recovery/multistore_exchange.py|init|--root|/exchange/run',
 'source:PG-SYNTHETIC-SEAM',
 'source:graph-admin:neo4j-admin|database|dump|neo4j|--to-path=/exchange/run/exports/neo4j',
 'source:snapshot:python|-B|/opt/recovery/multistore_native.py|export-objects|--directory|/exchange/run/exports/minio/objects',
 'source:snapshot:python|-B|/opt/recovery/multistore_exchange.py|call|--helper|multistore_n8n|--stdout-file|/exchange/run/reports/n8n-source.json|--|snapshot|--tree|/n8n-state/.n8n|--package|/exchange/run/exports/n8n/package',
 'source:snapshot:python|-B|/opt/recovery/multistore_exchange.py|tree|--source|/state|--destination|/exchange/run/exports/api/state',
 'source:snapshot:python|-B|/opt/recovery/multistore_archive.py|seal|--source|/exchange/run/exports|--recipient-file|/exchange/run/keys/recipient.txt|--destination|/exchange/run/sealed|--age|/opt/tools/age',
 'destination:snapshot:python|-B|/opt/recovery/multistore_exchange.py|init|--root|/exchange/run',
 ('source:docker:cp|'+$source.Project+'-snapshot-1:/exchange/run/sealed/archive.age|'),
 ('destination:docker:cp|'+(Join-Path 'private-output' 'archive.age')+'|'+$destination.Project+'-snapshot-1:/exchange/run/inbox/archive.age'),
 'destination:snapshot:python|-B|/opt/recovery/multistore_archive.py|negative',
 'destination:snapshot:python|-B|/opt/recovery/multistore_archive.py|open',
 'destination:PG-SYNTHETIC-SEAM',
 'destination:graph-admin:neo4j-admin|database|load|neo4j|--from-path=/exchange/run/restored/neo4j',
 'destination:snapshot:python|-B|/opt/recovery/multistore_native.py|create-bucket',
 'destination:snapshot:python|-B|/opt/recovery/multistore_native.py|restore-objects|--directory|/exchange/run/restored/minio/objects',
 'destination:snapshot:python|-B|/opt/recovery/multistore_exchange.py|restore-tree|--source|/exchange/run/restored/api/state|--destination|/state',
 ('source:docker:cp|'+$source.Project+'-snapshot-1:/exchange/run/reports/n8n-source.json|'),
 ('destination:docker:cp|'+(Join-Path 'private-output' 'n8n-expected.json')+'|'+$destination.Project+'-snapshot-1:/exchange/run/inbox/n8n-expected.json'),
 ('source:docker:cp|'+$source.Project+'-snapshot-1:/exchange/run/keys/n8n.key|'),
 ('destination:docker:cp|'+(Join-Path 'private-output' 'n8n.key')+'|'+$destination.Project+'-snapshot-1:/exchange/run/inbox/n8n.key'),
 'destination:snapshot:python|-B|/opt/recovery/multistore_exchange.py|call|--helper|multistore_n8n|--stdout-file|/exchange/run/reports/n8n-destination-restore.json|--|restore|--package|/exchange/run/restored/n8n/package|--destination|/n8n-state/.n8n|--expected|/exchange/run/inbox/n8n-expected.json',
 'destination:snapshot:python|-B|/opt/recovery/multistore_exchange.py|call|--helper|multistore_n8n|--stdout-file|/exchange/run/reports/n8n-destination-verify.json|--|verify|--tree|/n8n-state/.n8n|--expected|/exchange/run/inbox/n8n-expected.json')
$position=0
foreach($item in $expected){$next=$t.IndexOf($item,$position,[StringComparison]::Ordinal);if($next -lt 0){throw ('missing/order '+$item)};$position=$next+$item.Length}
foreach($bad in @('/exchange/exports','/exchange/sealed','/exchange/inbox','/exchange/neo4j','/exchange/n8n','/exchange/minio','|/tools/age')){if($t.Contains($bad)){throw ('legacy path '+$bad)}}
if($report.releaseAccepted -or $report.fullRecoveryAccepted){throw 'false native acceptance'}
if(-not $report.checks.latentFlowComplete){throw 'latent flow incomplete'}
''')
        self.assertEqual(result.returncode,0,result.stderr)

    def test_latent_archive_handoff_aborts_before_restore_on_failed_stage(self):
        # Only synthetic function seams execute; PG refusal has its own test.
        result=self.run_ps(r'''
function Invoke-MultiExec {param($c,$service,$cmd,$seconds,$limit)
 if($cmd -contains $script:failMode -and ($script:failMode -cne 'init' -or $c.Side -ceq 'destination')){throw 'synthetic stage failure'}
 if($cmd -contains 'restore' -and $cmd -contains 'multistore_n8n'){$script:n8nRestores++}
 if($cmd -contains 'seal'){return ('{"sha256":"'+('a'*64)+'"}')}
 if($cmd -contains 'negative'){return '{"positiveControl":true,"badKeyRejectedBeforeDestination":true,"corruptCiphertextRejectedBeforeDestination":true,"sourceCiphertextUnchanged":true,"nativeRecoveryProven":false}'}
 if($cmd -contains 'open'){return '{"nativeRecoveryProven":false}'}
 if($cmd -contains 'hash'){return ('{"verified":true,"sha256":"'+('c'*64)+'"}')}
 if($cmd -contains 'restore'){return '{"treeRestored":true,"nativeRecoveryProven":false}'}
 if($cmd -contains 'verify' -and $cmd -contains 'multistore_n8n'){return '{"restoredStateMatched":true,"nativeRecoveryProven":false}'}
 return ('{"verified":true,"producerBarrier":true,"schemaMatched":true,"drained":true,"fingerprint":"'+('a'*64)+'"}')
}
function Export-MultiPostgres {}
function Restore-MultiPostgres {$script:restores++}
function Invoke-MultiCompose {return ''}
function Get-MultiContainer {return ('b'*64)}
function Invoke-MultiDocker {
 $script:copies++
 if($script:failMode -ceq 'copy' -and $script:copies -eq $script:failCopy){throw 'synthetic stage failure'}
 return ''
}
function Start-Sleep {}
$source=@{Side='source';Project=('dg-multi-'+('a'*32));Services=@('neo4j','dg-reasoner','data-service','design-grammars','n8n','speckle-server','speckle-frontend-2','speckle-preview-service','speckle-webhook-service','speckle-ifc-import-service','speckle-ingress')}
$destination=@{Side='destination';Project=('dg-multi-'+('b'*32))}
foreach($mode in @('export-objects','call','tree','seal','init','copy','negative','open','create-bucket','restore-objects','restore-tree')) {
 foreach($copy in @(1,2,3,4,5)) {
  $script:failMode=$mode;$script:failCopy=$copy;$script:restores=0;$script:copies=0;$script:n8nRestores=0
  $report=@{checks=@{};releaseAccepted=$false;fullRecoveryAccepted=$false}
  $message=$null
  try {Invoke-MultiLatentFlow $source $destination @{AgeSha256=('a'*64);QueueSampleSeconds=2} 'private-output' $report}catch{$message=$_.Exception.Message}
  if($message -cne 'synthetic stage failure'){throw ('failure swallowed '+$mode)}
  $late=($mode -cin @('create-bucket','restore-objects','restore-tree')) -or ($mode -ceq 'copy' -and $copy -ge 3)
  $expectedRestores=if($late){1}else{0}  # PostgreSQL is restored before the late phases
  if($script:restores -ne $expectedRestores -or $report.checks.ContainsKey('latentFlowComplete')){throw ('restored/completed after failure '+$mode)}
  if($mode -cin @('export-objects','call','tree','seal','init') -and $script:copies -ne 0){throw 'copied after early failure'}
  if($mode -ceq 'copy' -and $script:copies -ne $copy){throw 'continued copy after failure'}
  if($mode -cin @('restore-objects','restore-tree','copy') -and $copy -ge 3 -and $script:n8nRestores -ne 0){throw ('n8n restored after failure '+$mode)}
  if($mode -cin @('create-bucket','restore-objects','restore-tree') -and $script:n8nRestores -ne 0){throw ('n8n restored after failure '+$mode)}
 }
}
''')
        self.assertEqual(result.returncode,0,result.stderr)

    def test_destination_restore_rejects_changed_n8n_transfer_before_restore(self):
        result=self.run_ps(r'''
$script:restore=0
function Invoke-MultiExec {param($c,$service,$cmd,$seconds,$limit)
 if($cmd -contains 'seal'){return ('{"sha256":"'+('a'*64)+'"}')}
 if($cmd -contains 'negative'){return '{"positiveControl":true,"badKeyRejectedBeforeDestination":true,"corruptCiphertextRejectedBeforeDestination":true,"sourceCiphertextUnchanged":true,"nativeRecoveryProven":false}'}
 if($cmd -contains 'open'){return '{"nativeRecoveryProven":false}'}
 if($cmd -contains 'hash'){$h=if($c.Side -ceq 'destination' -and $cmd -contains $script:tampered){'d'*64}else{'c'*64};return ('{"verified":true,"sha256":"'+$h+'"}')}
 if($cmd -contains 'restore'){$script:restore++;return '{"treeRestored":true,"nativeRecoveryProven":false}'}
 return ('{"verified":true,"producerBarrier":true,"schemaMatched":true,"drained":true,"fingerprint":"'+('a'*64)+'"}')
}
function Export-MultiPostgres {}
function Restore-MultiPostgres {}
function Invoke-MultiCompose {return ''}
function Get-MultiContainer {return ('b'*64)}
function Invoke-MultiDocker {return ''}
function Start-Sleep {}
$source=@{Side='source';Project=('dg-multi-'+('a'*32));Services=@('neo4j','dg-reasoner','data-service','design-grammars','n8n','speckle-server','speckle-frontend-2','speckle-preview-service','speckle-webhook-service','speckle-ifc-import-service','speckle-ingress')}
$destination=@{Side='destination';Project=('dg-multi-'+('b'*32))}
foreach($tampered in @('/exchange/run/inbox/n8n-expected.json','/exchange/run/inbox/n8n.key','/exchange/run/inbox/n8n-fixture-state.json','/exchange/run/inbox/n8n-decrypted-source.json')) {
 $script:tampered=$tampered;$script:restore=0
 $report=@{checks=@{};releaseAccepted=$false;fullRecoveryAccepted=$false}
 $failed=$false
 try {Invoke-MultiLatentFlow $source $destination @{AgeSha256=('a'*64);QueueSampleSeconds=2} 'private-output' $report}catch{$failed=$true}
 if(-not $failed){throw ('changed copy accepted '+$tampered)}
 if($script:restore -ne 0 -or $report.checks.ContainsKey('latentFlowComplete')){throw ('n8n restored after mismatched transfer '+$tampered)}
}
''')
        self.assertEqual(result.returncode,0,result.stderr)

    def test_destination_starts_storage_and_maintenance_without_application_writers(self):
        result=self.run_ps(r'''
$script:cmds=New-Object 'Collections.Generic.List[string]'
function Invoke-MultiCompose {param($c,$cmd,$seconds,$limit) $script:cmds.Add($c.Side+':'+($cmd -join '|'));return ''}
function Invoke-MultiExec {return '{"verified":true}'}
function Start-Sleep {}
$services=@('snapshot','graph-admin','n8n-admin','speckle-postgres','speckle-redis','speckle-minio','neo4j','dg-reasoner','data-service','design-grammars','n8n','speckle-server','speckle-frontend-2','speckle-preview-service','speckle-webhook-service','speckle-ifc-import-service','speckle-ingress')
foreach($side in @('source','destination')){
 $c=@{Side=$side;Services=$services;Report=@{checks=@{}}}
 Start-MultiStores $c
}
$source=$script:cmds[0];$destination=$script:cmds[1]
if($source -cne 'source:--profile|maintenance|up|--detach|--no-build|--pull|never'){throw ('source start changed: '+$source)}
if(-not $destination.StartsWith('destination:--profile|maintenance|up|--detach|--no-build|--pull|never|--no-deps|')){throw ('destination start: '+$destination)}
$words=$destination -split '\|'
foreach($writer in @('neo4j','dg-reasoner','data-service','design-grammars','n8n','speckle-server','speckle-frontend-2','speckle-preview-service','speckle-webhook-service','speckle-ifc-import-service','speckle-ingress')){
 if($words -ccontains $writer){throw ('writer started on destination: '+$writer)}
}
foreach($store in @('snapshot','graph-admin','n8n-admin','speckle-postgres','speckle-redis','speckle-minio')){
 if(-not ($words -ccontains $store)){throw ('missing store '+$store)}
}
''')
        self.assertEqual(result.returncode,0,result.stderr)

    def test_queue_barrier_rejects_nonempty_unknown_or_unstable_before_any_stop(self):
        for replacement in (
            '$sample.drained=$false', '$sample.drained="true"',
            '$sample.schemaMatched=$false', '$sample.fingerprint="not-a-hash"',
            '$sample.fingerprint=if($script:count -eq 4){"b"*64}else{"a"*64}',
        ):
            result=self.run_ps(r'''
$script:count=0;$script:stops=0
function Invoke-MultiExec {param($c,$s,$cmd,$seconds,$limit)
 $script:count++
 $sample=[pscustomobject]@{schemaMatched=$true;drained=$true;fingerprint=('a'*64)}
''' + replacement + r'''
 return ($sample|ConvertTo-Json -Compress)
}
function Invoke-MultiCompose {$script:stops++;throw 'must not stop'}
function Start-Sleep {}
$failed=$false
try {Wait-MultiQueueBarrier @{} @{QueueSampleSeconds=2};throw 'unexpected'}
catch {if($_.Exception.Message -ceq 'unexpected'){throw};$failed=$true}
if(-not $failed -or $script:stops -ne 0){throw 'barrier bypass'}
''')
            self.assertEqual(result.returncode,0,(replacement,result.stderr))
        good=self.run_ps(r'''
$script:count=0
function Invoke-MultiExec { $script:count++;return ('{"schemaMatched":true,"drained":true,"fingerprint":"'+('a'*64)+'"}') }
function Start-Sleep {}
Wait-MultiQueueBarrier @{} @{QueueSampleSeconds=2}
if($script:count -ne 4){throw 'missing distinct samples'}
''')
        self.assertEqual(good.returncode,0,good.stderr)

    def test_stop_writers_never_stops_snapshot_pg_minio_or_redis(self):
        result=self.run_ps(r'''
$script:cmd=$null;$script:checked=New-Object 'Collections.Generic.List[string]'
function Invoke-MultiCompose {param($c,$cmd,$seconds,$limit) $script:cmd=$cmd;return ''}
function Get-MultiContainer {param($c,$service,$running) if($running){throw 'expected stopped'};$script:checked.Add($service);return ('a'*64)}
$c=@{Services=@('snapshot','graph-admin','n8n-admin','speckle-postgres','speckle-redis','speckle-minio','neo4j','dg-reasoner','data-service','design-grammars','n8n','speckle-server','speckle-frontend-2','speckle-preview-service','speckle-webhook-service','speckle-ifc-import-service','speckle-ingress')}
Stop-MultiWriters $c
$expected=@('neo4j','dg-reasoner','data-service','design-grammars','n8n','speckle-server','speckle-frontend-2','speckle-preview-service','speckle-webhook-service','speckle-ifc-import-service','speckle-ingress')
if(($script:cmd -join '|') -cne ( (@('stop','--timeout','20')+$expected) -join '|')){throw 'stop set'}
if(($script:checked -join '|') -cne ($expected -join '|')){throw 'stopped evidence absent'}
$c.Services=@('snapshot')
try {Stop-MultiWriters $c;throw 'unexpected'}catch{if($_.Exception.Message -ceq 'unexpected'){throw}}
exit 0
''')
        self.assertEqual(result.returncode,0,result.stderr)

    def test_packaged_job_builds_two_distinct_contexts_without_undeclared_job_fields(self):
        import json
        import tempfile
        services={'neo4j':{'image':'sha256:'+'a'*64},'snapshot':{'image':'sha256:'+'b'*64}}
        model={'services':services,'volumes':{'graph':{},'exchange':{}}}
        with tempfile.TemporaryDirectory(dir=Path('C:/Users/Admin/AppData/Local/hermes/cache/scratch')) as tmp:
            root=Path(tmp);out=root/'output';out.mkdir()
            for name in ('source-compose.json','destination-compose.json'):
                (root/name).write_text(json.dumps(model))
            result=self.run_ps(f"$root={q(root)};$out={q(out)};"+r'''
function Get-Command {return [pscustomobject]@{Source='C:\\synthetic\\bin\\docker.exe'}}
$job=[pscustomobject]@{images=[pscustomobject]@{neo4j=[pscustomobject]@{configId=('sha256:'+('a'*64))}}}
$scope=[pscustomobject]@{maxCommands=500;maxSeconds=5400}
$report=@{checks=@{}}
$c=@(New-MultiContexts $root $out $job $scope $report)
if($c.Count -ne 2 -or $c[0].Compose -cne 'source-compose.json' -or $c[1].Compose -cne 'destination-compose.json'){throw 'compose contexts'}
if($c[0].Project -ceq $c[1].Project){throw 'same project'}
if(-not $c[0].Images.ContainsKey('snapshot') -or $c[0].Images['snapshot'] -cne ('sha256:'+('b'*64))){throw 'maintenance missing'}
if(-not [object]::ReferenceEquals($c[0].SharedBudget,$c[1].SharedBudget)){throw 'budget multiplied'}
if(($c[0].Services -join ',') -cne 'neo4j,snapshot'){throw 'services mismatch'}
foreach($key in @('NEO4J_PASSWORD','POSTGRES_PASSWORD','MINIO_ROOT_USER','MINIO_ROOT_PASSWORD','SPECKLE_SESSION_SECRET','LLM_MASTER_SECRET','DG_SERVICE_TOKEN','DG_BOOTSTRAP_ADMIN_PASSWORD','N8N_ENCRYPTION_KEY')) {
 if($c[0].Environment[$key].Length -lt 16){throw 'missing synthetic secret'}
 if($c[0].Environment[$key] -cne $c[1].Environment[$key]){throw 'restore key continuity'}
}
if((Get-Content -LiteralPath (Join-Path $c[0].Config 'config.json') -Raw).Trim() -cne '{}'){throw 'owner config'}
$cc=Get-Content -LiteralPath (Join-Path $c[0].ComposeConfig 'config.json') -Raw|ConvertFrom-Json
if(@($cc.PSObject.Properties).Count -ne 1 -or @($cc.cliPluginsExtraDirs).Count -ne 1){throw 'plugin config'}
''')
            self.assertEqual(result.returncode,0,result.stderr)

    def test_pg_export_and_restore_fail_closed_before_any_production_or_restore(self):
        # No qualified hard file bound/remote-child cleanup exists. In particular,
        # restore must refuse BEFORE empty.sql or pg_restore modifies destination.
        result=self.run_ps(r'''
$script:calls=0
function Invoke-MultiExec {$script:calls++;return '{"verified":true}'}
function Invoke-MultiPg {$script:calls++;return ''}
foreach($operation in @('Export-MultiPostgres','Restore-MultiPostgres')) {
 $message=$null
 try {& $operation @{} } catch {$message=$_.Exception.Message}
 if($message -cne 'PostgreSQL private output production unavailable: hard byte bound and container-child cleanup unqualified'){throw 'missing explicit fail-closed limitation'}
 if($script:calls -ne 0){throw 'command or restore side effect before refusal'}
}
''')
        self.assertEqual(result.returncode,0,result.stderr)
        self.assertEqual(result.stdout, '')

    def test_authenticated_archive_open_requires_both_negative_controls_before_open(self):
        result=self.run_ps(r'''
$script:trace=New-Object 'Collections.Generic.List[string]'
function Invoke-MultiExec {param($c,$service,$cmd,$seconds,$limit)
 $script:trace.Add(($cmd -join '|'))
 if($cmd -contains 'negative'){return '{"positiveControl":true,"badKeyRejectedBeforeDestination":true,"corruptCiphertextRejectedBeforeDestination":true,"sourceCiphertextUnchanged":true,"nativeRecoveryProven":false}'}
 return '{"nativeRecoveryProven":false,"sha256":"aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"}'
}
Open-MultiArchive @{} @{AgeSha256=('b'*64)} @{sha256=('a'*64);bytes=256}
$t=$script:trace -join "`n"
if($script:trace.Count -ne 2 -or $t.IndexOf('|negative|') -ge $t.IndexOf('|open|')){throw 'authentication order'}
foreach($part in @('/opt/tools/age','--archive|/exchange/run/inbox/archive.age','--destination|/exchange/run/restored','--identity-file|/exchange/run/keys/identity.txt')){if(-not $t.Contains($part)){throw ('missing '+$part)}}
''')
        self.assertEqual(result.returncode,0,result.stderr)
        for field in ('positiveControl','badKeyRejectedBeforeDestination','corruptCiphertextRejectedBeforeDestination','sourceCiphertextUnchanged'):
            for value in ('$false', '"true"'):
                result=self.run_ps(r'''
$script:opens=0
function Invoke-MultiExec {param($c,$s,$cmd,$seconds,$limit)
 if($cmd -contains 'open'){$script:opens++;throw 'must not open'}
 $r=@{positiveControl=$true;badKeyRejectedBeforeDestination=$true;corruptCiphertextRejectedBeforeDestination=$true;sourceCiphertextUnchanged=$true;nativeRecoveryProven=$false}
''' + f"$r['{field}']={value};" + r'''
 return ($r|ConvertTo-Json -Compress)
}
try {Open-MultiArchive @{} @{AgeSha256=('b'*64)} @{sha256=('a'*64);bytes=256};throw 'unexpected'}catch{if($_.Exception.Message -ceq 'unexpected'){throw}}
if($script:opens -ne 0){throw 'opened without negatives'}
exit 0
''')
                self.assertEqual(result.returncode,0,(field,value,result.stderr))

    def test_image_cache_checks_exact_mapping_values_and_rejects_missing_or_changed(self):
        result=self.run_ps(r'''
$script:observed=New-Object 'Collections.Generic.List[string]'
function Invoke-MultiDocker {param($c,$cmd,$seconds,$limit)
 if(($cmd[0..3] -join '|') -cne 'image|inspect|--format|{{.Id}}' -or $cmd.Count -ne 5){throw 'unexpected argv'}
 $script:observed.Add($cmd[4]);return $cmd[4]
}
$c=@{Images=@{snapshot=('sha256:'+('b'*64));neo4j=('sha256:'+('a'*64))};Report=@{checks=@{}}}
Assert-MultiImageCache $c
if($script:observed.Count -ne 2 -or ($script:observed|Sort-Object -Unique).Count -ne 2){throw 'map not checked'}
if(-not $c.Report.checks.imageCacheVerified){throw 'missing checked result'}
foreach($part in @(('sha256:'+('a'*64)),('sha256:'+('b'*64)))){if($part -cnotin $script:observed){throw 'value skipped'}}
exit 0
''')
        self.assertEqual(result.returncode,0,result.stderr)
        for images in ('@{}', '@{snapshot="not-an-id"}', '@{snapshot=("sha256:"+("b"*64))}'):
            result=self.run_ps(r'''
$script:calls=0
function Invoke-MultiDocker { $script:calls++;return ('sha256:'+('c'*64)) }
$c=@{Images='''+images+r''';Report=@{checks=@{}}}
try {Assert-MultiImageCache $c;throw 'unexpected'}catch{if($_.Exception.Message -ceq 'unexpected'){throw}}
if($c.Report.checks.ContainsKey('imageCacheVerified')){throw 'false image acceptance'}
if($script:calls -gt 1){throw 'continued after failure'}
exit 0
''')
            self.assertEqual(result.returncode,0,(images,result.stderr))

    def test_incomplete_main_does_not_unlock_package_builder(self):
        import sys
        sys.path.insert(0, str(HERE))
        try:
            import build_multistore_package as builder
            with self.assertRaisesRegex(ValueError, 'complete orchestration required'):
                builder.require_orchestration()
        finally:
            sys.path.remove(str(HERE))

    def test_effective_container_isolation_rejects_ports_foreign_networks_and_mounts(self):
        import json
        import tempfile
        model = {'services': {'snapshot': {'image': 'sha256:'+'b'*64, 'network_mode': 'none',
                 'volumes': [{'type':'volume','source':'exchange','target':'/exchange'}]}}}
        record = {'Id':'c'*64,'Image':'sha256:'+'b'*64,'Name':'/dg-multi-'+('a'*32)+'-snapshot-1',
                  'Config':{'Labels':{'com.docker.compose.project':'dg-multi-'+('a'*32),
                                      'com.docker.compose.service':'snapshot'},'User':'0:0'},
                  'HostConfig':{'Privileged':False,'NetworkMode':'none','PortBindings':{},
                                'PidMode':'','IpcMode':'private','Binds':[], 'CapAdd':[],
                                'Devices':[], 'ExtraHosts':[]},
                  'NetworkSettings':{'Networks':{},'Ports':{}},
                  'Mounts':[{'Type':'volume','Name':'dg-multi-'+('a'*32)+'_exchange',
                             'Destination':'/exchange','RW':True}], 'State':{'Running':True}}
        scratch = Path('C:/Users/Admin/AppData/Local/hermes/cache/scratch')
        with tempfile.TemporaryDirectory(dir=scratch) as tmp:
            root=Path(tmp)
            (root/'model.json').write_text(json.dumps(model))
            path=root/'inspect.json';path.write_text(json.dumps(record))
            setup=f"$c=@{{Root={q(root)};Compose='model.json';Project=('dg-multi-'+('a'*32));Images=@{{snapshot=('sha256:'+('b'*64))}}}};$r=Get-Content -LiteralPath {q(path)} -Raw|ConvertFrom-Json;"
            result=self.run_ps(setup+"Assert-MultiContainerIsolation $c 'snapshot' $r")
            self.assertEqual(result.returncode,0,result.stderr)
            mutations=["$r.HostConfig.Privileged=$true", "$r.HostConfig.NetworkMode='host'",
                       "$r.NetworkSettings.Networks|Add-Member foreign @{}",
                       "$r.HostConfig.PortBindings|Add-Member '80/tcp' @(@{HostPort='8080'})",
                       "$r.Mounts[0].Name='owner-volume'", "$r.Mounts[0].RW=$false",
                       "$r.HostConfig.CapAdd=@('SYS_ADMIN')", "$r.HostConfig.Devices=@('device')",
                       "$r.HostConfig.ExtraHosts=@('host.docker.internal:host-gateway')"]
            for mutation in mutations:
                result=self.run_ps(setup+mutation+";Assert-MultiContainerIsolation $c 'snapshot' $r")
                self.assertNotEqual(result.returncode,0,mutation)

    def test_each_native_exec_rechecks_exact_container_state_before_invocation(self):
        setup = r'''
$c=@{Project=('dg-multi-'+('a'*32));Services=@('snapshot');Images=@{snapshot=('sha256:'+('b'*64))}}
$script:seen=New-Object 'Collections.Generic.List[string]'
function Invoke-MultiCompose {param($ctx,$cmd,$seconds,$limit)
 $script:seen.Add(($cmd -join '|'))
 if($cmd[0] -ceq 'ps'){return ('c'*64)}
 if($cmd[0] -ceq 'exec'){return '{"verified":true}'}
 throw 'unexpected'
}
function Invoke-MultiDocker {param($ctx,$cmd)
 $script:seen.Add(($cmd[0..1] -join '|'))
 if($cmd[0] -ceq 'container' -and $cmd[1] -ceq 'inspect' -and $cmd[3].Contains('HostConfig')){return '{}'}
 return (@{Id=('c'*64);Image=$script:image;Project=$c.Project;Service='snapshot';Running=$true}|ConvertTo-Json -Compress)
}
function Assert-MultiContainerIsolation {param($ctx,$role,$record) $script:seen.Add('isolation')}
'''
        good = self.run_ps(setup + r'''
$script:image='sha256:'+('b'*64)
$r=Invoke-MultiExec $c 'snapshot' @('python','-B','/opt/recovery/multistore_native.py','manifest','--directory','/exchange/minio') 20 1024
if($r -cne '{"verified":true}'){throw 'result'}
if(($script:seen -join ';') -cne 'ps|--all|--quiet|snapshot;container|inspect;container|inspect;isolation;exec|-T|snapshot|python|-B|/opt/recovery/multistore_native.py|manifest|--directory|/exchange/minio'){throw 'order'}
''')
        self.assertEqual(good.returncode, 0, good.stderr)
        bad = self.run_ps(setup + r'''
$script:image='sha256:'+('d'*64)
try {Invoke-MultiExec $c 'snapshot' @('python','-B','bad') 20 1024;throw 'unexpected'}
catch {if($_.Exception.Message -ceq 'unexpected'){throw}}
if(@($script:seen|Where-Object{$_.StartsWith('exec|')}).Count){throw 'executed after identity mismatch'}
''')
        self.assertEqual(bad.returncode, 0, bad.stderr)


if __name__ == '__main__':
    unittest.main()
