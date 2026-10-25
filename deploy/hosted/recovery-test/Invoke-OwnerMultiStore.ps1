#requires -Version 5.1
[CmdletBinding()]
param(
    [string]$Runner='',
    [Parameter(Mandatory=$true)][string]$PackageZip,
    [Parameter(Mandatory=$true)][string]$ExpectedZipSha256,
    [Parameter(Mandatory=$true)][string]$OutputDirectory,
    [string]$ScopeJson='',
    [switch]$RunNativeMultiStore
)
Set-StrictMode -Version Latest
$ErrorActionPreference='Stop'
# Resolve in the body: PSScriptRoot in a param default is unreliable in PS5.
if(-not $Runner){$Runner=Join-Path $PSScriptRoot 'Run-MultiStore.ps1'}
if(Test-Path -LiteralPath $OutputDirectory){throw 'fresh output required'}
$arguments=@('-NoProfile','-NonInteractive','-ExecutionPolicy','Bypass','-File',$Runner,
    '-PackageZip',$PackageZip,'-ExpectedZipSha256',$ExpectedZipSha256,'-OutputDirectory',$OutputDirectory)
if($RunNativeMultiStore){$arguments+='-RunNativeMultiStore'}
if($ScopeJson){$arguments+=@('-ScopeJson',$ScopeJson)}
& (Join-Path $PSHOME 'powershell.exe') @arguments
$code=$LASTEXITCODE
# Preserve the native exit BEFORE any other invocation, report parsing or work.
if($null -eq $code){throw 'child process exit unknown'}
if(-not (Test-Path -LiteralPath $OutputDirectory -PathType Container)){throw 'child output missing'}
$current=[IO.Path]::GetFullPath($OutputDirectory)
while($current) {
    $item=Get-Item -LiteralPath $current -Force
    if($item.Attributes -band [IO.FileAttributes]::ReparsePoint){throw 'linked output denied'}
    $parent=Split-Path -Parent $current
    if($parent -eq $current){break};$current=$parent
}
$record=[ordered]@{schemaVersion=1;processExitCode=[int]$code;runtimeAccepted=$false;releaseAccepted=$false}
$bytes=(New-Object Text.UTF8Encoding($false)).GetBytes((ConvertTo-Json -InputObject $record))
$stream=[IO.File]::Open((Join-Path $OutputDirectory 'process-exit.json'),[IO.FileMode]::CreateNew,[IO.FileAccess]::Write,[IO.FileShare]::None)
try{$stream.Write($bytes,0,$bytes.Length)}finally{$stream.Dispose()}
[Console]::WriteLine('MULTISTORE_PROCESS_EXIT='+[string]$code)
exit ([int]$code)
