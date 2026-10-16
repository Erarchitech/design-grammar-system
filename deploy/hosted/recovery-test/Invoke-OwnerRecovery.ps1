#requires -Version 5.1
[CmdletBinding()]
param(
    [string]$Runner='',
    [Parameter(Mandatory=$true)][string]$PackageZip,
    [Parameter(Mandatory=$true)][string]$ExpectedZipSha256,
    [Parameter(Mandatory=$true)][string]$OutputDirectory,
    [switch]$RunRecovery
)
Set-StrictMode -Version Latest
$ErrorActionPreference='Stop'
if(-not $Runner){$Runner=Join-Path $PSScriptRoot 'Run-Recovery.ps1'}
# Refuse an existing destination: never overwrite an older exit evidence file.
if(Test-Path -LiteralPath $OutputDirectory){throw 'fresh output required'}
$arguments=@('-NoProfile','-NonInteractive','-ExecutionPolicy','Bypass','-File',$Runner,
    '-PackageZip',$PackageZip,'-ExpectedZipSha256',$ExpectedZipSha256,'-OutputDirectory',$OutputDirectory)
if($RunRecovery){$arguments+='-RunRecovery'}
& (Join-Path $PSHOME 'powershell.exe') @arguments
$code=$LASTEXITCODE
if($null -eq $code){throw 'child process exit unknown'}
# Only persist in the new child-created output; avoid adopting other directories.
if(-not (Test-Path -LiteralPath $OutputDirectory -PathType Container)){throw 'child output missing'}
$item=Get-Item -LiteralPath $OutputDirectory -Force
if($item.Attributes -band [IO.FileAttributes]::ReparsePoint){throw 'reparse output denied'}
$record=[ordered]@{schemaVersion=1;processExitCode=[int]$code;runtimeAccepted=$false}
$path=Join-Path $OutputDirectory 'process-exit.json'
$bytes=(New-Object Text.UTF8Encoding($false)).GetBytes((ConvertTo-Json -InputObject $record))
$stream=[IO.File]::Open($path,[IO.FileMode]::CreateNew,[IO.FileAccess]::Write,[IO.FileShare]::None)
try{$stream.Write($bytes,0,$bytes.Length)}finally{$stream.Dispose()}
[Console]::WriteLine('RECOVERY_PROCESS_EXIT='+[string]$code)
exit ([int]$code)
