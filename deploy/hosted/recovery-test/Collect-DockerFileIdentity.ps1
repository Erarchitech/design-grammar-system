# Fixed installed-file identity only. Never execute Docker or Compose.
param([Parameter(Mandatory=$true)][string]$ReportPath,[switch]$PreflightOnly)
$ErrorActionPreference='Stop';Set-StrictMode -Version 2.0
function Require-DFI($Value){if(-not $Value){throw 'file identity rejected'}}
function Assert-DFIHost([string]$Name){Require-DFI ($Name -ceq 'DESKTOP-OS4Q8CP')}
function Assert-DFIPath([string]$Path){
 Require-DFI ($Path -cmatch '^[A-Za-z]:\\' -and -not $Path.Substring(2).Contains(':'))
 $item=Get-Item -LiteralPath $Path -Force
 while($null -ne $item){
  Require-DFI (-not ($item.Attributes -band [IO.FileAttributes]::ReparsePoint))
  $parent=Split-Path -Parent $item.FullName
  if(-not $parent -or $parent -eq $item.FullName){break}
  $item=Get-Item -LiteralPath $parent -Force
 }
}
function Convert-DFIVersion([string]$Text){
 # File resources are untrusted declarations, not CLI/runtime versions.
 if($null -eq $Text){return $null}
 $v=$Text.Trim()
 if($v.Length -gt 0 -and $v.Length -le 128 -and $v -cmatch '\Av?[0-9][0-9A-Za-z.+_ -]*\z'){return $v}
 return $null
}
function Read-DFIFile([string]$Slot,[string]$Path){
 $o=[ordered]@{slot=$Slot;status='UNRESOLVED';sha256=$null;bytes=$null;fileVersion=$null;productVersion=$null;versionMetadata='UNAVAILABLE_OR_REJECTED';failureStage=$null}
 $stream=$null;$stage='FILE_GUARD'
 try{
  Assert-DFIPath $Path
  $item=Get-Item -LiteralPath $Path -Force
  Require-DFI ($item -is [IO.FileInfo] -and $item.Length -gt 0 -and $item.Length -le 536870912)
  $stage='FILE_READ'
  # Deny write/delete sharing for the duration; no execution or owner config reads.
  $stream=[IO.File]::Open($Path,[IO.FileMode]::Open,[IO.FileAccess]::Read,[IO.FileShare]::Read)
  $length=$stream.Length;Require-DFI ($length -gt 0 -and $length -le 536870912)
  $h1=(Get-FileHash -InputStream $stream -Algorithm SHA256).Hash.ToLowerInvariant()
  $stage='FILE_RESOURCES'
  $v=[Diagnostics.FileVersionInfo]::GetVersionInfo($Path)
  $fv=Convert-DFIVersion $v.FileVersion;$pv=Convert-DFIVersion $v.ProductVersion
  $stage='FILE_STABILITY'
  $stream.Position=0
  $h2=(Get-FileHash -InputStream $stream -Algorithm SHA256).Hash.ToLowerInvariant()
  Require-DFI ($h1 -ceq $h2 -and $stream.Length -eq $length -and $h1 -cmatch '\A[0-9a-f]{64}\z')
  $o.sha256=$h1;$o.bytes=$length;$o.fileVersion=$fv;$o.productVersion=$pv
  $o.versionMetadata=$(if($null -ne $fv -and $null -ne $pv){'BOTH_OBSERVED'}elseif($null -ne $fv -or $null -ne $pv){'PARTIAL'}else{'UNAVAILABLE_OR_REJECTED'})
  $o.status='OBSERVED'
 }catch{$o.failureStage=$stage}finally{if($null -ne $stream){$stream.Dispose()}}
 return $o
}
$report=[ordered]@{schemaVersion=1;kind='installed-docker-file-identity-not-runtime-not-recovery';target='DESKTOP-OS4Q8CP';
 status='BLOCKED';observedAtUtc=$null;dockerInvoked=$false;nativeCommandsStarted=0;files=@();
 runtimeVersionProven=$false;provenanceVerified=$false;nativeRecoveryProven=$false;releaseAccepted=$false;failureStage=$null}
$stream=$null;$stage='REPORT_PATH'
try{
 $file=[IO.Path]::GetFullPath($ReportPath);Assert-DFIPath (Split-Path -Parent $file)
 Require-DFI (-not $file.Substring(2).Contains(':') -and -not (Test-Path -LiteralPath $file))
 $stream=[IO.File]::Open($file,[IO.FileMode]::CreateNew,[IO.FileAccess]::Write,[IO.FileShare]::None)
 if($PreflightOnly){$report.status='PREFLIGHT_ONLY'}else{
  $stage='HOST';Assert-DFIHost ([Environment]::MachineName.ToUpperInvariant())
  $install=Join-Path ([Environment]::GetFolderPath('ProgramFiles')) 'Docker\Docker'
  $report.observedAtUtc=[DateTime]::UtcNow.ToString('o');$stage='OBSERVATION'
  foreach($slot in @('resources/bin/docker.exe','resources/cli-plugins/docker-compose.exe')){
   $path=Join-Path $install ($slot.Replace('/','\'))
   $report.files+=,(Read-DFIFile $slot $path)
  }
  $report.status=$(if(@($report.files|Where-Object{$_.status -cne 'OBSERVED'}).Count -eq 0){'FILES_OBSERVED'}else{'UNRESOLVED'})
 }
}catch{$report.status='BLOCKED';$report.failureStage=$stage}finally{
 if($null -ne $stream){
  try{$bytes=[Text.UTF8Encoding]::new($false).GetBytes(($report|ConvertTo-Json -Depth 8));$stream.Write($bytes,0,$bytes.Length);$stream.Flush()}
  catch{$report.status='BLOCKED'}finally{$stream.Dispose()}
 }
}
Write-Output ('Docker file identity: '+$report.status)
if($report.status -ceq 'UNRESOLVED'){exit 2}
if($report.status -cnotin @('FILES_OBSERVED','PREFLIGHT_ONLY')){exit 1}
exit 0
