# One approved A/B Compose version comparison. Docker must remain OFF.
param([Parameter(Mandatory=$true)][string]$ReportPath,[switch]$PreflightOnly)
$ErrorActionPreference='Stop';Set-StrictMode -Version 2.0
function Require-CC($Value){if(-not $Value){throw 'comparison rejected'}}
function Assert-CCHost([string]$Name){Require-CC ($Name -ceq 'DESKTOP-OS4Q8CP')}
function Assert-CCPath([string]$Path){
 Require-CC ($Path -cmatch '^[A-Za-z]:\\' -and -not $Path.Substring(2).Contains(':'))
 $item=Get-Item -LiteralPath $Path -Force
 while($null -ne $item){
  Require-CC (-not ($item.Attributes -band [IO.FileAttributes]::ReparsePoint))
  $parent=Split-Path -Parent $item.FullName
  if(-not $parent -or $parent -eq $item.FullName){break}
  $item=Get-Item -LiteralPath $parent -Force
 }
}
function Get-CCCategory([string]$Text){
 if($Text -match '(?i)(home directory|userprofile|\$HOME)'){return 'HOME_UNAVAILABLE'}
 if($Text -match '(?i)(access is denied|permission denied)'){return 'ACCESS_DENIED'}
 if($Text -match '(?i)(not a docker command|unknown command.+compose|compose.+not.+command)'){return 'COMPOSE_COMMAND_UNAVAILABLE'}
 if($Text -match '(?i)(invalid plugin|failed to (fetch|load).+plugin|plugin.+(invalid|failed))'){return 'PLUGIN_LOAD_FAILED'}
 if($Text -match '(?i)(unknown (flag|shorthand)|flag provided but not defined|requires.+argument)'){return 'CLI_ARGUMENT_REJECTED'}
 if($Text -match '(?i)(docker_engine|cannot connect|daemon is not running)'){return 'LOCAL_ENDPOINT_UNAVAILABLE'}
 return 'UNCLASSIFIED'
}
function Invoke-CCVersion([string]$Mode,[string]$Config){
 Assert-CCHost ([Environment]::MachineName.ToUpperInvariant())
 Require-CC ($Mode -cin @('EMPTY_CONFIG','EXPLICIT_PLUGIN_DIR') -and $script:report.dockerClientLaunches -lt 2)
 $o=[ordered]@{mode=$Mode;composeVersion=$null;read=[ordered]@{phase='PRECHECK';started=$false;timedOut=$false;exitCode=$null;category=$null;stdoutChars=$null;stderrChars=$null;elapsedMs=0}}
 $psi=[Diagnostics.ProcessStartInfo]::new();$psi.FileName=$script:docker
 $argv=@('--config',$Config,'--host','npipe:////./pipe/docker_engine','compose','version','--short')
 # Fixed argv, config path ends in GUID (not a general Windows argument encoder).
 $psi.Arguments=(($argv|ForEach-Object{'"'+$_.Replace('"','\"')+'"'}) -join ' ')
 $psi.UseShellExecute=$false;$psi.CreateNoWindow=$true;$psi.RedirectStandardOutput=$true;$psi.RedirectStandardError=$true
 $psi.WorkingDirectory=$Config;$psi.EnvironmentVariables.Clear()
 $psi.EnvironmentVariables['SystemRoot']=[Environment]::GetEnvironmentVariable('SystemRoot','Process')
 $psi.EnvironmentVariables['PATH']=Split-Path -Parent $script:docker;$psi.EnvironmentVariables['DOCKER_CONFIG']=$Config
 $p=[Diagnostics.Process]::new();$p.StartInfo=$psi;$started=$false;$clock=[Diagnostics.Stopwatch]::StartNew()
 try{
  $o.read.phase='START';[void]$p.Start();$started=$true;$o.read.started=$true
  $script:report.dockerClientLaunches++;$script:report.dockerInvoked=$true
  $out=$p.StandardOutput.ReadToEndAsync();$err=$p.StandardError.ReadToEndAsync();$o.read.phase='WAIT'
  if(-not $p.WaitForExit(10000)){$o.read.timedOut=$true;$o.read.category='TIMEOUT';throw 'comparison rejected'}
  $o.read.phase='DRAIN';Require-CC ($out.Wait(1000) -and $err.Wait(1000))
  $text=$out.Result;$errorText=$err.Result;$o.read.phase='EXIT';$o.read.exitCode=$p.ExitCode
  $o.read.stdoutChars=$text.Length;$o.read.stderrChars=$errorText.Length
  if($p.ExitCode -ne 0){$o.read.category=Get-CCCategory $errorText;throw 'comparison rejected'}
  $o.read.phase='SCHEMA';Require-CC ($text.Length -le 256)
  $v=$text.Trim();Require-CC ($v -cmatch '\Av?[0-9]+\.[0-9]+\.[0-9]+[-+a-zA-Z0-9.]*\z')
  $o.composeVersion=$v;$o.read.category='VERSION_OBSERVED'
 }catch{
  # Never include native output, exception text, paths or environment values.
 }finally{
  $clock.Stop();$o.read.elapsedMs=$clock.ElapsedMilliseconds
  try{if($started -and -not $p.HasExited){$p.Kill();Require-CC ($p.WaitForExit(5000))}}finally{$p.Dispose()}
 }
 return $o
}
$report=[ordered]@{schemaVersion=1;kind='compose-discovery-comparison-not-recovery';target='DESKTOP-OS4Q8CP';status='BLOCKED';
 dockerOffPrerequisite='owner-stated-not-probed';dockerInvoked=$false;dockerClientLaunches=0;observedAtUtc=$null;
 dockerExecutableSha256=$null;pluginSha256=$null;pluginSlot='resources/cli-plugins/docker-compose.exe';
 observations=@();nativeRecoveryProven=$false;releaseAccepted=$false;failureStage=$null}
$stream=$null;$config=$null;$owned=$false;$configFileOwned=$false;$stage='PATH'
try{
 $file=[IO.Path]::GetFullPath($ReportPath);Assert-CCPath (Split-Path -Parent $file)
 Require-CC (-not $file.Substring(2).Contains(':') -and -not (Test-Path -LiteralPath $file))
 $stream=[IO.File]::Open($file,[IO.FileMode]::CreateNew,[IO.FileAccess]::Write,[IO.FileShare]::None)
 if($PreflightOnly){$report.status='PREFLIGHT_ONLY'}else{
  $stage='HOST';Assert-CCHost ([Environment]::MachineName.ToUpperInvariant())
  $stage='IDENTITY';$install=Join-Path ([Environment]::GetFolderPath('ProgramFiles')) 'Docker\Docker'
  $docker=Join-Path $install 'resources\bin\docker.exe'
  $pluginDir=Join-Path $install 'resources\cli-plugins';$plugin=Join-Path $pluginDir 'docker-compose.exe'
  foreach($path in @($docker,$plugin)){Assert-CCPath $path;Require-CC (Test-Path -LiteralPath $path -PathType Leaf)}
  $report.dockerExecutableSha256=(Get-FileHash -LiteralPath $docker -Algorithm SHA256).Hash.ToLowerInvariant()
  $report.pluginSha256=(Get-FileHash -LiteralPath $plugin -Algorithm SHA256).Hash.ToLowerInvariant()
  # Owner-supplied observed hashes pin the approved installation, not authenticity.
  Require-CC ($report.dockerExecutableSha256 -ceq '70c9fbdfb6318c2aa910581cdbe1cf4237a600177cabedcd83e95f1dac7f5db5')
  Require-CC ($report.pluginSha256 -ceq '93be120f45f1ef7a5a7c176636933a5ed0fa2e26fd4cb5907303cd395c9149dc')
  $report.observedAtUtc=[DateTime]::UtcNow.ToString('o')
  foreach($mode in @('EMPTY_CONFIG','EXPLICIT_PLUGIN_DIR')){
   $stage='CONFIG';$config=Join-Path (Split-Path -Parent $file) ('.dg-compose-compare-'+[Guid]::NewGuid().ToString('N'))
   Require-CC (-not (Test-Path -LiteralPath $config));[void][IO.Directory]::CreateDirectory($config);$owned=$true
   if($mode -ceq 'EXPLICIT_PLUGIN_DIR'){
    $configPath=Join-Path $config 'config.json'
    $json=([ordered]@{cliPluginsExtraDirs=@($pluginDir)}|ConvertTo-Json -Compress)
    $s=[IO.File]::Open($configPath,[IO.FileMode]::CreateNew,[IO.FileAccess]::Write,[IO.FileShare]::None);$configFileOwned=$true
    try{$bytes=[Text.UTF8Encoding]::new($false).GetBytes($json);$s.Write($bytes,0,$bytes.Length)}finally{$s.Dispose()}
   }
   $stage='READ';$o=Invoke-CCVersion $mode $config;$report.observations+=,$o
   $stage='CONFIG_CLEANUP'
   if($configFileOwned){[IO.File]::Delete((Join-Path $config 'config.json'));$configFileOwned=$false}
   [IO.Directory]::Delete($config,$false);$owned=$false;$config=$null
   # A failed launch/timeout/drain is not a stable A/B sample: do not start B.
   $stage='INCOMPLETE_SAMPLE'
   Require-CC ($o.read.started -and -not $o.read.timedOut -and $null -ne $o.read.exitCode)
  }
  $report.status=$(if($report.observations[1].read.category -ceq 'VERSION_OBSERVED'){'COMPARISON_COMPLETE'}else{'UNRESOLVED'})
 }
}catch{$report.status='BLOCKED';$report.failureStage=$stage}finally{
 if($owned){
  try{
   if($configFileOwned){[IO.File]::Delete((Join-Path $config 'config.json'));$configFileOwned=$false}
   [IO.Directory]::Delete($config,$false);$owned=$false
  }catch{$report.status='BLOCKED';$report.failureStage='CONFIG_CLEANUP'}
 }
 if($null -ne $stream){
  try{$bytes=[Text.UTF8Encoding]::new($false).GetBytes(($report|ConvertTo-Json -Depth 8));$stream.Write($bytes,0,$bytes.Length);$stream.Flush()}
  catch{$report.status='BLOCKED'}finally{$stream.Dispose()}
 }
}
Write-Output ('Compose comparison: '+$report.status)
if($report.status -ceq 'UNRESOLVED'){exit 2}
if($report.status -notin @('COMPARISON_COMPLETE','PREFLIGHT_ONLY')){exit 1}
exit 0
