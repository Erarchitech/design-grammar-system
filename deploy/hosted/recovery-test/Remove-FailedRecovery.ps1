#requires -Version 5.1
[CmdletBinding()]
param(
 [Parameter(Mandatory=$true)][string]$PackageDirectory,
 [Parameter(Mandatory=$true)][string]$PackageZip,
 [Parameter(Mandatory=$true)][string]$ReportDirectory
)
Set-StrictMode -Version Latest
$ErrorActionPreference='Stop'
$expected='e430407e70a21af210a0a3d8816ca01f2fc8c54844b82dd879eb8a959e56b135'
if((Get-FileHash -LiteralPath $PackageZip -Algorithm SHA256).Hash.ToLowerInvariant() -cne $expected){throw 'issued ZIP required'}
Add-Type -AssemblyName System.IO.Compression.FileSystem
$zip=[IO.Compression.ZipFile]::OpenRead($PackageZip)
try{
 $modules=@{}
 foreach($name in @('package-functions.ps1','runtime-functions.ps1','execution.ps1')){
  $stream=$zip.GetEntry('support/'+$name).Open();$reader=New-Object IO.StreamReader($stream)
  try{$modules[$name]=$reader.ReadToEnd()}finally{$reader.Dispose()}
 }
}finally{$zip.Dispose()}
# Execute only definitions from the hash-pinned issued ZIP, never extraction scripts.
. ([scriptblock]::Create($modules['package-functions.ps1']))
. ([scriptblock]::Create($modules['runtime-functions.ps1']))
$old="@(`$Context.Project+'_graph',`$Context.Project+'_graph_logs',`$Context.Project+'_api_state',`$Context.Project+'_exchange')"
$new="@((`$Context.Project+'_graph'),(`$Context.Project+'_graph_logs'),(`$Context.Project+'_api_state'),(`$Context.Project+'_exchange'))"
Assert-True ($modules['execution.ps1'].Contains($old))
. ([scriptblock]::Create($modules['execution.ps1'].Replace($old,$new)))
Assert-IsolatedRuntimeGuard ([Environment]::MachineName) ([Environment]::GetEnvironmentVariables())
Assert-RegularPath $PackageDirectory;Assert-RegularPath $ReportDirectory
$config=Join-Path $ReportDirectory 'docker-config';Assert-RegularPath $config
Assert-True ((Get-Content -LiteralPath (Join-Path $config 'config.json') -Raw).Trim() -ceq '{}')
$context=@{Root=$PackageDirectory;Config=$config;Project='dg-recovery-3b9148574bb84061babce755691900d3';Environment=@{};
 Deadline=[datetime]::UtcNow.AddMinutes(3);Docker=(Get-Command docker.exe -CommandType Application -ErrorAction Stop).Source;Report=@{dockerInvoked=$false};
 Images=[pscustomobject]@{'graph-admin'='sha256:0efd832ad89fcc0526e80abf8b26bb79f196ebe87eac655c6f19c08c5be766b8';'snapshot'='sha256:9787e347b10eb8303498fed9e79651b89a3a1d4f62501ee98e51f6f25d0b22d1'}}
$result=[ordered]@{schemaVersion=1;kind='failed-recovery-owned-cleanup';project=$context.Project;status='FAILED';failureStage=$null;ownershipVerified=$false;cleanupVerified=$false}
$stage='ownership'
try{
 $resources=Assert-RecoveryOwnership $context
 Assert-True ($resources.networks.Count -eq 0 -and $resources.containers.Count -le 2 -and $resources.volumes.Count -le 4)
 # All consumers must be these validated helper containers, including stopped ones.
 $stage='volume-consumers'
 foreach($volume in $resources.volumes){
  $text=Invoke-RecoveryDocker $context @('container','ls','--all','--filter',('volume='+$volume),'--format','{{.ID}}','--no-trunc') 10 8192
  $ids=@(($text -split '\r?\n')|Where-Object{$_})
  foreach($id in $ids){Assert-True ($id -cin $resources.containers)}
 }
 $result.ownershipVerified=$true
 $stage='remove-containers'
 foreach($id in $resources.containers){
  [void](Assert-RecoveryOwnership $context)
  [void](Invoke-RecoveryDocker $context @('container','rm','--force',$id) 30 1024)
 }
 $stage='remove-volumes'
 foreach($volume in $resources.volumes){
  [void](Assert-RecoveryOwnership $context)
  # Never force volume deletion: Docker refuses any remaining consumer.
  [void](Invoke-RecoveryDocker $context @('volume','rm',$volume) 15 1024)
 }
 $stage='verify-vacancy';Assert-RecoveryVacant $context
 $result.cleanupVerified=$true;$result.status='OWNED_CLEANUP_COMPLETE'
}catch{$result.failureStage=$stage}
ConvertTo-Json -InputObject $result -Depth 5
if(-not $result.cleanupVerified){exit 1}
exit 0
