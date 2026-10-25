# Read-only local image/tool observation. No container/config/data inspection.
param([Parameter(Mandatory=$true)][string]$ReportPath,[switch]$PreflightOnly)
$ErrorActionPreference='Stop'
Set-StrictMode -Version 2.0
function Require-Inventory($Condition) { if(-not $Condition){throw 'inventory rejected'} }
function Assert-InventoryTarget([string]$HostName) {
  Require-Inventory ($HostName -ceq 'DESKTOP-OS4Q8CP')
}
function Get-ApprovedImages {
  @('dg-hosted-1309-sandbox-neo4j:latest','dg-hosted-1309-sandbox-data-service:latest',
    'n8nio/n8n:2.4.8','postgres:16.4-alpine3.20','valkey/valkey:8.1-alpine',
    'minio/minio:latest','speckle/speckle-server:latest','speckle/speckle-frontend-2:latest',
    'speckle/speckle-preview-service:latest','speckle/speckle-webhook-service:latest',
    'speckle/speckle-fileimport-service:latest','speckle/speckle-docker-compose-ingress:latest')
}
function Get-InventoryArguments([string]$Kind,[string]$Image) {
  $prefix=@('--host','npipe:////./pipe/docker_engine')
  switch -CaseSensitive ($Kind) {
    'image' {
      Require-Inventory ($Image -cin @(Get-ApprovedImages))
      $format='{"Id":{{json .Id}},"RepoDigests":{{json .RepoDigests}},"Os":{{json .Os}},"Architecture":{{json .Architecture}}}'
      return $prefix+@('image','inspect','--format',$format,$Image)
    }
    'version' { return $prefix+@('version','--format','{"client":{{json .Client.Version}},"server":{{json .Server.Version}}}') }
    'compose' { return $prefix+@('compose','version','--short') }
    default { throw 'inventory rejected' }
  }
}
function Convert-InventoryImage([string]$Image,[string]$Text) {
  [void](Get-InventoryArguments 'image' $Image)
  Require-Inventory ($Text.Length -le 16384)
  $raw=$Text|ConvertFrom-Json
  Require-Inventory ($raw.Id -is [string] -and $raw.Id -cmatch '^sha256:[0-9a-f]{64}$')
  Require-Inventory ($raw.Os -ceq 'linux' -and $raw.Architecture -cin @('amd64','arm64'))
  $digests=@()
  if($null -ne $raw.RepoDigests){
    Require-Inventory ($raw.RepoDigests -is [Array] -and $raw.RepoDigests.Count -le 32)
    foreach($d in $raw.RepoDigests){
      Require-Inventory ($d -is [string] -and $d.Length -le 320 -and $d -cmatch '^[a-z0-9][a-z0-9._:/-]*@sha256:[0-9a-f]{64}$')
      $digests+=$d
    }
  }
  [ordered]@{reference=$Image;status=$(if($digests.Count){'OBSERVED_NOW'}else{'UNRESOLVED_REGISTRY_DIGEST'});
    configId=$raw.Id;repoDigests=@($digests|Sort-Object -Unique);os=$raw.Os;architecture=$raw.Architecture}
}
function Assert-InventoryPath([string]$Path) {
  Require-Inventory ($Path -cmatch '^[A-Za-z]:\\' -and -not $Path.Substring(2).Contains(':'))
  $item=Get-Item -LiteralPath $Path -Force
  while($null -ne $item){
    Require-Inventory (-not ($item.Attributes -band [IO.FileAttributes]::ReparsePoint))
    $parent=Split-Path -Parent $item.FullName
    if(-not $parent -or $parent -eq $item.FullName){break}
    $item=Get-Item -LiteralPath $parent -Force
  }
}
function Get-InventoryPlugin([string]$Docker) {
  Require-Inventory ((Get-FileHash -LiteralPath $Docker -Algorithm SHA256).Hash.ToLowerInvariant() -ceq '6c699720bb9523dedb9eb5d22a49951ea9210dbdb1314a3554029eee9be76896')
  $plugin=[IO.Path]::GetFullPath((Join-Path (Split-Path -Parent $Docker) '..\cli-plugins\docker-compose.exe'))
  Assert-InventoryPath $plugin
  Require-Inventory ((Get-Item -LiteralPath $plugin -Force) -is [IO.FileInfo])
  $hash=(Get-FileHash -LiteralPath $plugin -Algorithm SHA256).Hash.ToLowerInvariant()
  Require-Inventory ($hash -ceq 'e6176502e836a7fee8d71cab5fcda736c8dacc79ccefdf9659af977f7eae2375')
  return [ordered]@{directory=(Split-Path -Parent $plugin);sha256=$hash}
}
function Get-InventoryErrorCategory([string]$Text) {
  # Only emit a fixed category; never publish native output, paths or arguments.
  if($Text -match '(?i)(home directory|userprofile|\$HOME)'){return 'HOME_UNAVAILABLE'}
  if($Text -match '(?i)(access is denied|permission denied)'){return 'ACCESS_DENIED'}
  if($Text -match '(?i)(no such image|image.+not found)'){return 'IMAGE_NOT_FOUND'}
  if($Text -match '(?i)(docker_engine|cannot connect|daemon is not running|pipe.+cannot find)'){return 'LOCAL_ENDPOINT_UNAVAILABLE'}
  return 'UNCLASSIFIED'
}
function Invoke-InventoryRead([string]$Kind,[string]$Image) {
  $script:lastRead=[ordered]@{phase='PRECHECK';started=$false;timedOut=$false;exitCode=$null;errorCategory=$null;stdoutChars=$null;stderrChars=$null;elapsedMs=0}
  Assert-InventoryTarget ([Environment]::MachineName.ToUpperInvariant())
  Require-Inventory ([DateTime]::UtcNow -lt $script:deadline)
  $fixed=@(Get-InventoryArguments $Kind $Image)
  $psi=[Diagnostics.ProcessStartInfo]::new()
  $psi.FileName=$script:docker
  $activeConfig=$script:config
  if($Kind -ceq 'compose'){$activeConfig=$script:composeConfig}
  $argv=@('--config',$activeConfig)+$fixed
  $psi.Arguments=(($argv|ForEach-Object{'"'+$_.Replace('"','\"')+'"'}) -join ' ')
  $psi.UseShellExecute=$false;$psi.CreateNoWindow=$true
  $psi.RedirectStandardOutput=$true;$psi.RedirectStandardError=$true
  $psi.WorkingDirectory=$activeConfig
  $psi.EnvironmentVariables.Clear()
  $psi.EnvironmentVariables['SystemRoot']=[Environment]::GetEnvironmentVariable('SystemRoot','Process')
  $psi.EnvironmentVariables['PATH']=Split-Path -Parent $script:docker
  $psi.EnvironmentVariables['DOCKER_CONFIG']=$activeConfig
  $p=[Diagnostics.Process]::new();$p.StartInfo=$psi;$started=$false
  $clock=[Diagnostics.Stopwatch]::StartNew()
  try {
    $script:lastRead.phase='START'
    [void]$p.Start();$started=$true;$script:report.dockerInvoked=$true;$script:lastRead.started=$true
    $out=$p.StandardOutput.ReadToEndAsync();$err=$p.StandardError.ReadToEndAsync()
    $script:lastRead.phase='WAIT'
    if(-not $p.WaitForExit(10000)){$script:lastRead.timedOut=$true;throw 'inventory rejected'}
    $script:lastRead.phase='DRAIN'
    Require-Inventory ($out.Wait(1000) -and $err.Wait(1000))
    $text=$out.Result;$errorText=$err.Result
    $script:lastRead.phase='EXIT';$script:lastRead.exitCode=$p.ExitCode
    $script:lastRead.stdoutChars=$text.Length;$script:lastRead.stderrChars=$errorText.Length
    if($p.ExitCode -ne 0){$script:lastRead.errorCategory=Get-InventoryErrorCategory $errorText}
    Require-Inventory ($p.ExitCode -eq 0 -and $text.Length -le 16384)
    $script:lastRead.phase='READ_OK'
    return $text
  } finally {
    $clock.Stop();$script:lastRead.elapsedMs=$clock.ElapsedMilliseconds
    if($started -and -not $p.HasExited){$p.Kill();Require-Inventory ($p.WaitForExit(5000))}
    $p.Dispose()
  }
}
$report=[ordered]@{schemaVersion=3;kind='multi-store-image-tool-observation-not-recovery';
 status='BLOCKED';target='DESKTOP-OS4Q8CP';observedAtUtc=$null;dockerInvoked=$false;
 releaseAccepted=$false;nativeRecoveryProven=$false;historicalRunBinding='not-established';
 fullStackInventory=$false;queueCatalogSchemaObserved=$false;images=@();tools=[ordered]@{};diagnostics=@();failureStage=$null}
$stream=$null;$config=$null;$configOwned=$false;$composeConfig=$null;$composeFileOwned=$false;$stage='paths'
try {
  $file=[IO.Path]::GetFullPath($ReportPath)
  Assert-InventoryPath (Split-Path -Parent $file)
  Require-Inventory (-not $file.Substring(2).Contains(':') -and -not (Test-Path -LiteralPath $file))
  $stream=[IO.File]::Open($file,[IO.FileMode]::CreateNew,[IO.FileAccess]::Write,[IO.FileShare]::None)
  if($PreflightOnly){$report.status='PREFLIGHT_ONLY'}else{
    $stage='host-guard';Assert-InventoryTarget ([Environment]::MachineName.ToUpperInvariant())
    $stage='tool-guard'
    $docker=Join-Path ([Environment]::GetFolderPath('ProgramFiles')) 'Docker\Docker\resources\bin\docker.exe'
    Assert-InventoryPath $docker
    $report.tools.dockerExecutableSha256=(Get-FileHash -LiteralPath $docker -Algorithm SHA256).Hash.ToLowerInvariant()
    $plugin=Get-InventoryPlugin $docker
    $report.tools.composePluginSha256=$plugin.sha256
    $report.tools.composeDiscovery='EXPLICIT_PLUGIN_DIR'
    $config=Join-Path (Split-Path -Parent $file) ('.dg-inventory-'+[Guid]::NewGuid().ToString('N'))
    Require-Inventory (-not (Test-Path -LiteralPath $config))
    [void][IO.Directory]::CreateDirectory($config);$configOwned=$true
    $composeCandidate=Join-Path $config 'compose'
    Require-Inventory (-not (Test-Path -LiteralPath $composeCandidate))
    [void][IO.Directory]::CreateDirectory($composeCandidate);$composeConfig=$composeCandidate
    $configFile=Join-Path $composeConfig 'config.json'
    $cf=[IO.File]::Open($configFile,[IO.FileMode]::CreateNew,[IO.FileAccess]::Write,[IO.FileShare]::None)
    $composeFileOwned=$true
    try{$cb=[Text.UTF8Encoding]::new($false).GetBytes((@{cliPluginsExtraDirs=@($plugin.directory)}|ConvertTo-Json -Compress));$cf.Write($cb,0,$cb.Length)}finally{$cf.Dispose()}
    $deadline=[DateTime]::UtcNow.AddSeconds(240)
    $report.observedAtUtc=[DateTime]::UtcNow.ToString('o');$stage='observation'
    $unresolved=$false
    foreach($kind in @('version','compose')){
      try{
        $text=Invoke-InventoryRead $kind ''
        $lastRead.phase='SCHEMA'
        if($kind -ceq 'version'){
          $lastRead.phase='JSON_PARSE';$v=$text|ConvertFrom-Json;$lastRead.phase='SCHEMA'
          foreach($name in @('client','server')){
            Require-Inventory ($v.$name -is [string] -and $v.$name -cmatch '^v?[0-9]+\.[0-9]+\.[0-9]+[-+a-zA-Z0-9.]*$')
          }
          $report.tools.dockerClientVersion=$v.client;$report.tools.dockerServerVersion=$v.server
        }else{
          $v=$text.Trim();Require-Inventory ($v -cmatch '^v?[0-9]+\.[0-9]+\.[0-9]+[-+a-zA-Z0-9.]*$')
          $report.tools.composeVersion=$v
        }
      }catch{
        $unresolved=$true;$report.tools[$kind+'Status']='UNRESOLVED'
        $report.diagnostics+=,[ordered]@{kind=$kind;reference=$null;read=$lastRead}
      }
    }
    foreach($image in @(Get-ApprovedImages)){
      try{
        $text=Invoke-InventoryRead 'image' $image
        $lastRead.phase='IMAGE_PROJECTION';$o=Convert-InventoryImage $image $text
      }catch{
        $o=[ordered]@{reference=$image;status='UNRESOLVED_INSPECTION';configId=$null;repoDigests=@();os=$null;architecture=$null}
        $report.diagnostics+=,[ordered]@{kind='image';reference=$image;read=$lastRead}
      }
      if($o.status -cne 'OBSERVED_NOW'){$unresolved=$true};$report.images+=,$o
    }
    $report.status=$(if($unresolved){'UNRESOLVED'}else{'OBSERVED_NOW'})
  }
}catch{$report.status='BLOCKED';$report.failureStage=$stage}
finally{
  if($configOwned){
    try{
      if($composeFileOwned){[IO.File]::Delete((Join-Path $composeConfig 'config.json'))}
      if($null -ne $composeConfig){[IO.Directory]::Delete($composeConfig,$false)}
      [IO.Directory]::Delete($config,$false)
    }catch{$report.status='BLOCKED';$report.failureStage='owned-config-cleanup'}
  }
  if($null -ne $stream){
    try{$bytes=[Text.UTF8Encoding]::new($false).GetBytes(($report|ConvertTo-Json -Depth 8));$stream.Write($bytes,0,$bytes.Length);$stream.Flush()}
    catch{$report.status='BLOCKED'}finally{$stream.Dispose()}
  }
}
Write-Output ('Inventory: '+$report.status)
if($report.status -ceq 'UNRESOLVED'){exit 2}
if($report.status -notin @('OBSERVED_NOW','PREFLIGHT_ONLY')){exit 1}
exit 0
