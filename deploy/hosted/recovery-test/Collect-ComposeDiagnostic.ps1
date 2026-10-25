# Single Compose-client diagnostic, Docker must remain OFF. No service commands.
param([Parameter(Mandatory=$true)][string]$ReportPath,[switch]$PreflightOnly)
$ErrorActionPreference='Stop';Set-StrictMode -Version 2.0
function Require-CD($Value){if(-not $Value){throw 'diagnostic rejected'}}
function Assert-CDHost([string]$Name){Require-CD ($Name -ceq 'DESKTOP-OS4Q8CP')}
function Assert-CDPath([string]$Path){
 Require-CD ($Path -cmatch '^[A-Za-z]:\\' -and -not $Path.Substring(2).Contains(':'))
 $item=Get-Item -LiteralPath $Path -Force
 while($null -ne $item){
  Require-CD (-not ($item.Attributes -band [IO.FileAttributes]::ReparsePoint))
  $parent=Split-Path -Parent $item.FullName
  if(-not $parent -or $parent -eq $item.FullName){break}
  $item=Get-Item -LiteralPath $parent -Force
 }
}
function Get-CDCategory([string]$Text){
 if($Text -match '(?i)(home directory|userprofile|\$HOME)'){return 'HOME_UNAVAILABLE'}
 if($Text -match '(?i)(access is denied|permission denied)'){return 'ACCESS_DENIED'}
 if($Text -match '(?i)(not a docker command|unknown command.+compose|compose.+not.+command)'){return 'COMPOSE_COMMAND_UNAVAILABLE'}
 if($Text -match '(?i)(invalid plugin|failed to (fetch|load).+plugin|plugin.+(invalid|failed))'){return 'PLUGIN_LOAD_FAILED'}
 if($Text -match '(?i)(unknown (flag|shorthand)|flag provided but not defined|requires.+argument)'){return 'CLI_ARGUMENT_REJECTED'}
 if($Text -match '(?i)(docker_engine|cannot connect|daemon is not running)'){return 'LOCAL_ENDPOINT_UNAVAILABLE'}
 return 'UNCLASSIFIED'
}
$report=[ordered]@{schemaVersion=1;kind='compose-client-diagnostic-not-recovery';target='DESKTOP-OS4Q8CP';
 status='BLOCKED';dockerOffPrerequisite='owner-stated-not-probed';dockerInvoked=$false;nativeCommandsStarted=0;
 observedAtUtc=$null;dockerExecutableSha256=$null;pluginCandidates=@();composeVersion=$null;
 read=[ordered]@{phase='PRECHECK';started=$false;timedOut=$false;exitCode=$null;category=$null;stdoutChars=$null;stderrChars=$null;elapsedMs=0};
 nativeRecoveryProven=$false;releaseAccepted=$false;failureStage=$null}
$stream=$null;$config=$null;$owned=$false;$stage='PATH'
try{
 $file=[IO.Path]::GetFullPath($ReportPath);Assert-CDPath (Split-Path -Parent $file)
 Require-CD (-not $file.Substring(2).Contains(':') -and -not (Test-Path -LiteralPath $file))
 $stream=[IO.File]::Open($file,[IO.FileMode]::CreateNew,[IO.FileAccess]::Write,[IO.FileShare]::None)
 if($PreflightOnly){$report.status='PREFLIGHT_ONLY'}else{
  $stage='HOST';Assert-CDHost ([Environment]::MachineName.ToUpperInvariant())
  $stage='INSTALLATION'
  $install=Join-Path ([Environment]::GetFolderPath('ProgramFiles')) 'Docker\Docker'
  Assert-CDPath $install
  $docker=Join-Path $install 'resources\bin\docker.exe';Assert-CDPath $docker
  $report.dockerExecutableSha256=(Get-FileHash -LiteralPath $docker -Algorithm SHA256).Hash.ToLowerInvariant()
  # Only two fixed installation candidates; no directory enumeration or owner config.
  foreach($relative in @('resources\cli-plugins\docker-compose.exe','resources\bin\docker-compose.exe')){
   $candidate=Join-Path $install $relative
   # Validate nearest existing ancestor before probing a candidate under it.
   $parent=Split-Path -Parent $candidate
   while(-not (Test-Path -LiteralPath $parent)){$parent=Split-Path -Parent $parent}
   Assert-CDPath $parent
   $exists=Test-Path -LiteralPath $candidate;$sha=$null
   if($exists){Assert-CDPath $candidate;Require-CD (Test-Path -LiteralPath $candidate -PathType Leaf)
    $sha=(Get-FileHash -LiteralPath $candidate -Algorithm SHA256).Hash.ToLowerInvariant()}
   $report.pluginCandidates+=,[ordered]@{slot=$relative.Replace('\','/');present=[bool]$exists;sha256=$sha}
  }
  $stage='CONFIG';$config=Join-Path (Split-Path -Parent $file) ('.dg-compose-'+[Guid]::NewGuid().ToString('N'))
  Require-CD (-not (Test-Path -LiteralPath $config));[void][IO.Directory]::CreateDirectory($config);$owned=$true
  $stage='READ';$report.observedAtUtc=[DateTime]::UtcNow.ToString('o')
  $psi=[Diagnostics.ProcessStartInfo]::new();$psi.FileName=$docker
  $argv=@('--config',$config,'--host','npipe:////./pipe/docker_engine','compose','version','--short')
  # Fixed argv and GUID-ending config path; no caller-provided native arguments.
  $psi.Arguments=(($argv|ForEach-Object{'"'+$_.Replace('"','\"')+'"'}) -join ' ')
  $psi.UseShellExecute=$false;$psi.CreateNoWindow=$true;$psi.RedirectStandardOutput=$true;$psi.RedirectStandardError=$true
  $psi.WorkingDirectory=$config;$psi.EnvironmentVariables.Clear()
  $psi.EnvironmentVariables['SystemRoot']=[Environment]::GetEnvironmentVariable('SystemRoot','Process')
  $psi.EnvironmentVariables['PATH']=Split-Path -Parent $docker;$psi.EnvironmentVariables['DOCKER_CONFIG']=$config
  $p=[Diagnostics.Process]::new();$p.StartInfo=$psi;$started=$false;$clock=[Diagnostics.Stopwatch]::StartNew()
  try{
   $report.read.phase='START';[void]$p.Start();$started=$true;$report.dockerInvoked=$true;$report.nativeCommandsStarted=1;$report.read.started=$true
   $out=$p.StandardOutput.ReadToEndAsync();$err=$p.StandardError.ReadToEndAsync()
   $report.read.phase='WAIT'
   if(-not $p.WaitForExit(10000)){$report.read.timedOut=$true;$report.read.category='TIMEOUT';throw 'diagnostic rejected'}
   $report.read.phase='DRAIN';Require-CD ($out.Wait(1000) -and $err.Wait(1000))
   $text=$out.Result;$errorText=$err.Result;$report.read.phase='EXIT';$report.read.exitCode=$p.ExitCode
   $report.read.stdoutChars=$text.Length;$report.read.stderrChars=$errorText.Length
   if($p.ExitCode -ne 0){$report.read.category=Get-CDCategory $errorText;throw 'diagnostic rejected'}
   $report.read.phase='SCHEMA';Require-CD ($text.Length -le 256)
   $v=$text.Trim();Require-CD ($v -cmatch '\Av?[0-9]+\.[0-9]+\.[0-9]+[-+a-zA-Z0-9.]*\z')
   $report.composeVersion=$v;$report.read.category='VERSION_OBSERVED';$report.status='OBSERVED_NOW'
  }catch{$report.status='UNRESOLVED'}finally{
   $clock.Stop();$report.read.elapsedMs=$clock.ElapsedMilliseconds
   try{if($started -and -not $p.HasExited){$p.Kill();Require-CD ($p.WaitForExit(5000))}}finally{$p.Dispose()}
  }
 }
}catch{$report.status='BLOCKED';$report.failureStage=$stage}finally{
 if($owned){try{[IO.Directory]::Delete($config,$false)}catch{$report.status='BLOCKED';$report.failureStage='CONFIG_CLEANUP'}}
 if($null -ne $stream){try{$bytes=[Text.UTF8Encoding]::new($false).GetBytes(($report|ConvertTo-Json -Depth 8));$stream.Write($bytes,0,$bytes.Length);$stream.Flush()}
 catch{$report.status='BLOCKED'}finally{$stream.Dispose()}}
}
Write-Output ('Compose diagnostic: '+$report.status)
if($report.status -ceq 'UNRESOLVED'){exit 2}
if($report.status -notin @('OBSERVED_NOW','PREFLIGHT_ONLY')){exit 1}
exit 0
