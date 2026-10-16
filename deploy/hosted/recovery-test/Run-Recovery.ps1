#requires -Version 5.1
[CmdletBinding()]
param(
    [Parameter(Mandatory=$true)][string]$PackageZip,
    [Parameter(Mandatory=$true)][string]$ExpectedZipSha256,
    [Parameter(Mandatory=$true)][string]$OutputDirectory,
    [switch]$RunRecovery
)
Set-StrictMode -Version Latest
$ErrorActionPreference='Stop'
# Bootstrap only function definitions. ZIP pin/extraction validation happens before
# any runtime function is invoked. Do not run untrusted packages in the first place.
. (Join-Path $PSScriptRoot 'package-functions.ps1')
function Assert-RecoveryPackage([string]$Root,[string]$ZipPath,[string]$Expected) {
    Assert-RegularPath $Root;Assert-RegularPath $ZipPath
    Assert-True ($Expected -cmatch '^[0-9a-f]{64}$' -and (Get-Hash $ZipPath) -ceq $Expected)
    $path=Join-Path $Root 'recovery-manifest.json'
    $job=Get-Content -LiteralPath $path -Raw -Encoding UTF8|ConvertFrom-Json
    Assert-True ($job.schemaVersion -is [int] -and $job.schemaVersion -eq 1 -and $job.kind -ceq 'synthetic-two-store-recovery-not-release')
    Assert-True ($job.target -ceq 'DESKTOP-OS4Q8CP' -and $job.sourceRevision -ceq 'c82b92b29423c515e353e3fa4f9c17e9b0d83438')
    Assert-True ($job.images.neo4j -ceq 'sha256:0efd832ad89fcc0526e80abf8b26bb79f196ebe87eac655c6f19c08c5be766b8')
    Assert-True ($job.images.'data-service' -ceq 'sha256:9787e347b10eb8303498fed9e79651b89a3a1d4f62501ee98e51f6f25d0b22d1')
    $expectedFiles=@{}
    foreach($p in $job.files.PSObject.Properties) {
        Assert-MemberName $p.Name
        Assert-True (-not $expectedFiles.ContainsKey($p.Name) -and $p.Value -cmatch '^[0-9a-f]{64}$')
        $expectedFiles[$p.Name]=$p.Value
    }
    Assert-True (-not $expectedFiles.ContainsKey('recovery-manifest.json'))
    $expectedFiles['recovery-manifest.json']=Get-Hash $path
    $actual=@{};$pending=New-Object 'Collections.Generic.Stack[string]';$pending.Push($Root)
    while($pending.Count) {
        foreach($item in Get-ChildItem -LiteralPath $pending.Pop() -Force) {
            Assert-True (-not ($item.Attributes -band [IO.FileAttributes]::ReparsePoint) -and -not $item.LinkType)
            $name=$item.FullName.Substring($Root.Length+1).Replace([IO.Path]::DirectorySeparatorChar,'/')
            Assert-MemberName $name
            if($item.PSIsContainer) {
                Assert-True (@($expectedFiles.Keys|Where-Object{$_.StartsWith($name+'/',[StringComparison]::Ordinal)}).Count -gt 0)
                $pending.Push($item.FullName)
            } else {Assert-True (-not $actual.ContainsKey($name));$actual[$name]=Get-Hash $item.FullName}
        }
    }
    Assert-ExactMap $actual ([pscustomobject]$expectedFiles)
    Add-Type -AssemblyName System.IO.Compression.FileSystem
    $zip=[IO.Compression.ZipFile]::OpenRead($ZipPath)
    try {
        $members=@{}
        foreach($entry in $zip.Entries) {
            Assert-MemberName $entry.FullName
            Assert-True (-not $members.ContainsKey($entry.FullName) -and $entry.Length -le 32000000)
            $bits=[BitConverter]::ToUInt32([BitConverter]::GetBytes([int]$entry.ExternalAttributes),0)
            Assert-True ((($bits -shr 16) -band 61440) -in @(0,32768) -and ($bits -band 1040) -eq 0)
            $stream=$entry.Open();$hash=[Security.Cryptography.SHA256]::Create()
            try{$members[$entry.FullName]=[BitConverter]::ToString($hash.ComputeHash($stream)).Replace('-','').ToLowerInvariant()}
            finally{$stream.Dispose();$hash.Dispose()}
        }
        Assert-ExactMap $members ([pscustomobject]$expectedFiles)
    } finally{$zip.Dispose()}
    Assert-True ((Get-Hash (Join-Path $Root 'source/manifest.json')) -ceq '47cc21bfdc32af2fc37af93758f44eb8eb71b692d7084bdcccac969b7b544b23')
    return $job
}
$root=[IO.Path]::GetFullPath((Split-Path -Parent $PSScriptRoot))
$report=[ordered]@{schemaVersion=1;kind='synthetic-two-store-recovery-not-release';status='FAILED';failureStage=$null;dockerInvoked=$false;releaseAccepted=$false;fullRecoveryAccepted=$false;offMachineRestoreProven=$false;cleanup='not-started';checks=[ordered]@{}}
$outputOwned=$false;$stage='package-preflight'
try {
    Assert-True ($OutputDirectory -match '^[A-Za-z]:[\\/]')
    $output=[IO.Path]::GetFullPath($OutputDirectory);Assert-RegularPath $output
    Assert-True (-not (Test-Path -LiteralPath $output) -and (Test-Path -LiteralPath (Split-Path -Parent $output) -PathType Container))
    Assert-True (-not $output.Equals($root,[StringComparison]::OrdinalIgnoreCase) -and -not $output.StartsWith($root+'\',[StringComparison]::OrdinalIgnoreCase) -and -not $root.StartsWith($output+'\',[StringComparison]::OrdinalIgnoreCase))
    [void][IO.Directory]::CreateDirectory($output);$outputOwned=$true
    $job=Assert-RecoveryPackage $root $PackageZip $ExpectedZipSha256
    $report.packageZipSha256=$ExpectedZipSha256;$report.sourceRevision=$job.sourceRevision;$report.checks.packageIntegrity=$true
    if($RunRecovery) {
        $stage='recovery-runtime'
        . (Join-Path $PSScriptRoot 'runtime-functions.ps1')
        . (Join-Path $PSScriptRoot 'execution.ps1')
        Invoke-RecoveryExercise $root $output $job $report
    } else {$report.status='PACKAGE_PREFLIGHT_COMPLETE'}
} catch {
    if($null -eq $report.failureStage){$report.failureStage=$stage}
    $report.status='FAILED';[Console]::Error.WriteLine('RECOVERY_FAILED: '+$report.failureStage)
}
if($outputOwned) {
    try {[IO.File]::WriteAllText((Join-Path $output 'recovery-report.json'),(ConvertTo-Json -InputObject $report -Depth 15),(New-Object Text.UTF8Encoding($false)))}
    catch{[Console]::Error.WriteLine('RECOVERY_REPORT_WRITE_FAILED');exit 1}
}
if($report.status -ceq 'FAILED'){exit 1}
exit 0
