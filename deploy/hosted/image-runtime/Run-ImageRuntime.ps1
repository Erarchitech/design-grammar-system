#requires -Version 5.1
[CmdletBinding()]
param(
    [Parameter(Mandatory=$true)][string]$PackageZip,
    [Parameter(Mandatory=$true)][string]$ExpectedZipSha256,
    [Parameter(Mandatory=$true)][string]$OutputDirectory,
    [string]$ArchiveDirectory,
    [switch]$PackagePreflightOnly,
    [switch]$RunIsolatedSmoke
)
Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

function Assert-True($Value) { if (-not $Value) { throw 'assertion failed' } }
function Get-Hash([string]$Path) { return (Get-FileHash -LiteralPath $Path -Algorithm SHA256).Hash.ToLowerInvariant() }
function Assert-RegularPath([string]$Path) {
    $current = [IO.Path]::GetFullPath($Path)
    while ($current) {
        if (Test-Path -LiteralPath $current) {
            $item = Get-Item -LiteralPath $current -Force
            Assert-True (-not ($item.Attributes -band [IO.FileAttributes]::ReparsePoint) -and -not $item.LinkType)
        }
        $parent = Split-Path -Parent $current
        if ($parent -eq $current) { break }
        $current = $parent
    }
}
function Assert-MemberName([string]$Name) {
    Assert-True ($Name -cmatch '^[a-zA-Z0-9_./-]+$' -and -not $Name.StartsWith('/'))
    foreach ($part in $Name.Split('/')) {
        Assert-True ($part -and $part -notin @('.', '..') -and $part -notmatch '[. ]$' -and $part -notmatch '^(?i:CON|PRN|AUX|NUL|COM[1-9]|LPT[1-9])(?:\.|$)')
    }
}
function Assert-ExactMap($Actual, $Expected) {
    $props = @($Expected.PSObject.Properties)
    Assert-True ($Actual.Count -eq $props.Count)
    foreach ($p in $props) {
        Assert-True ($Actual.ContainsKey($p.Name) -and @($Actual.Keys | Where-Object {$_ -ceq $p.Name}).Count -eq 1 -and $Actual[$p.Name] -ceq $p.Value)
    }
}
function Assert-RuntimePackage([string]$Root, [string]$ZipPath, [string]$Hash) {
    Assert-RegularPath $Root
    Assert-RegularPath $ZipPath
    Assert-True ($Hash -cmatch '^[0-9a-f]{64}$' -and (Get-Hash $ZipPath) -ceq $Hash)
    $manifestPath = Join-Path $Root 'image-runtime-manifest.json'
    $m = Get-Content -LiteralPath $manifestPath -Raw -Encoding UTF8 | ConvertFrom-Json
    Assert-True ($m.kind -ceq 'controlled-image-load-smoke-not-release' -and $m.schemaVersion -eq 1 -and $m.target -ceq 'DESKTOP-OS4Q8CP')
    Assert-True ($m.sourceRevision -ceq 'c82b92b29423c515e353e3fa4f9c17e9b0d83438' -and $m.sourceManifestSha256 -ceq '47cc21bfdc32af2fc37af93758f44eb8eb71b692d7084bdcccac969b7b544b23')
    Assert-True ($m.buildPackageZipSha256 -ceq '9d391a82f5dac6bf53d8d83e5154c67c448fc4f56ea008e84c01c2f2916c7717')
    $expected = @{}
    foreach ($p in $m.files.PSObject.Properties) {
        Assert-MemberName $p.Name
        Assert-True (-not $expected.ContainsKey($p.Name) -and $p.Value -cmatch '^[0-9a-f]{64}$')
        $expected[$p.Name] = $p.Value
    }
    Assert-True (-not $expected.ContainsKey('image-runtime-manifest.json'))
    $expected['image-runtime-manifest.json'] = Get-Hash $manifestPath
    $actual = @{}
    $pending = New-Object 'Collections.Generic.Stack[string]'
    $pending.Push($Root)
    while ($pending.Count) {
        foreach ($item in Get-ChildItem -LiteralPath $pending.Pop() -Force) {
            Assert-True (-not ($item.Attributes -band [IO.FileAttributes]::ReparsePoint) -and -not $item.LinkType)
            $name = $item.FullName.Substring($Root.Length + 1).Replace([IO.Path]::DirectorySeparatorChar, '/')
            Assert-MemberName $name
            if ($item.PSIsContainer) {
                Assert-True (@($expected.Keys | Where-Object {$_.StartsWith($name + '/', [StringComparison]::Ordinal)}).Count -gt 0)
                $pending.Push($item.FullName)
            } else { Assert-True (-not $actual.ContainsKey($name)); $actual[$name] = Get-Hash $item.FullName }
        }
    }
    Assert-ExactMap $actual ([pscustomobject]$expected)
    Add-Type -AssemblyName System.IO.Compression.FileSystem
    $zip = [IO.Compression.ZipFile]::OpenRead($ZipPath)
    try {
        $members = @{}
        foreach ($entry in $zip.Entries) {
            Assert-MemberName $entry.FullName
            $attributes = [BitConverter]::ToUInt32([BitConverter]::GetBytes([int]$entry.ExternalAttributes), 0)
            Assert-True ((($attributes -shr 16) -band 61440) -in @(0, 32768) -and ($attributes -band 1040) -eq 0 -and -not $members.ContainsKey($entry.FullName))
            Assert-True ($entry.Length -le 32000000)
            $stream = $entry.Open(); $algorithm = [Security.Cryptography.SHA256]::Create()
            try { $members[$entry.FullName] = [BitConverter]::ToString($algorithm.ComputeHash($stream)).Replace('-', '').ToLowerInvariant() }
            finally { $stream.Dispose(); $algorithm.Dispose() }
        }
        Assert-ExactMap $members ([pscustomobject]$expected)
    } finally { $zip.Dispose() }
    Assert-True ((Get-Hash (Join-Path $Root 'source/manifest.json')) -ceq $m.sourceManifestSha256)
    $source = Get-Content -LiteralPath (Join-Path $Root 'source/manifest.json') -Raw -Encoding UTF8 | ConvertFrom-Json
    Assert-True ($source.frameworkRevision -ceq $m.sourceRevision -and $source.status -ceq 'BLOCKED')
    $sourceFiles = @{}
    foreach ($name in $actual.Keys) { if ($name.StartsWith('source/', [StringComparison]::Ordinal) -and $name -cne 'source/manifest.json') {$sourceFiles[$name.Substring(7)] = $actual[$name]} }
    Assert-ExactMap $sourceFiles $source.files
    Assert-True ((@($m.images.PSObject.Properties.Name | Sort-Object) -join ',') -ceq 'data-service,design-grammars,dg-reasoner,neo4j')
    return $m
}

function Assert-Archives([string]$Directory, $Images) {
    Assert-True ($Directory -match '^[A-Za-z]:[\\/]')
    Assert-RegularPath $Directory
    Assert-True (Test-Path -LiteralPath $Directory -PathType Container)
    foreach ($p in $Images.PSObject.Properties) {
        $image = $p.Value
        Assert-True ($image.archive -ceq ($p.Name + '.tar') -and $p.Name -cmatch '^[a-z][a-z0-9-]+$')
        Assert-True ($image.archiveSha256 -cmatch '^[0-9a-f]{64}$' -and $image.archiveBytes -is [ValueType] -and $image.archiveBytes -isnot [bool] -and $image.archiveBytes -gt 0)
        $path = Join-Path $Directory $image.archive
        Assert-RegularPath $path
        Assert-True (Test-Path -LiteralPath $path -PathType Leaf)
        Assert-True ((Get-Item -LiteralPath $path).Length -eq $image.archiveBytes)
        Assert-True ((Get-Hash $path) -ceq $image.archiveSha256)
    }
}
function Assert-BuildReport([string]$Directory, [string]$Root, $Job) {
    $path = Join-Path $Directory 'build-report.json'
    Assert-RegularPath $path
    Assert-True ((Get-Item -LiteralPath $path).Length -le 2000000)
    $build = Get-Content -LiteralPath $path -Raw -Encoding UTF8 | ConvertFrom-Json
    Assert-True ($build.schemaVersion -is [int] -and $build.schemaVersion -eq 1)
    Assert-True ($build.kind -ceq 'controlled-image-build-not-release' -and $build.status -ceq 'BUILD_EXPORT_COMPLETE' -and $null -eq $build.failureStage)
    Assert-True ($build.dockerInvoked -is [bool] -and $build.dockerInvoked -eq $true)
    Assert-True ($build.releaseAccepted -is [bool] -and $build.releaseAccepted -eq $false -and $build.reproducibleDependencies -is [bool] -and $build.reproducibleDependencies -eq $false)
    Assert-True ($build.sourceRevision -ceq $Job.sourceRevision -and $build.sourceManifestSha256 -ceq $Job.sourceManifestSha256 -and $build.packageZipSha256 -ceq $Job.buildPackageZipSha256)
    Assert-True ($build.target -ceq 'DESKTOP-OS4Q8CP' -and $build.dockerEndpoint -ceq 'npipe:////./pipe/docker_engine')
    Assert-True ($build.sourceManifest.frameworkRevision -ceq $Job.sourceRevision -and $build.sourceManifest.status -ceq 'BLOCKED')
    $source = Get-Content -LiteralPath (Join-Path $Root 'source/manifest.json') -Raw -Encoding UTF8 | ConvertFrom-Json
    $mapping = @{}
    foreach ($p in $build.sourceManifest.files.PSObject.Properties) {$mapping[$p.Name] = $p.Value}
    Assert-ExactMap $mapping $source.files
    $original = Get-Content -LiteralPath (Join-Path $Root 'support/build-job-manifest.json') -Raw -Encoding UTF8 | ConvertFrom-Json
    $mapping = @{}
    foreach ($p in $build.packageFiles.PSObject.Properties) {$mapping[$p.Name] = $p.Value}
    Assert-ExactMap $mapping $original.files
    Assert-True ($build.runnerTooling.path -ceq 'support/Run-ImageBuild.ps1' -and $build.runnerTooling.sha256 -ceq '49a9e00c1cc856a1f7fd0419735894e598c41ae5d58414e947be7211eca00798')
    Assert-True ((@($build.images.PSObject.Properties.Name | Sort-Object) -join ',') -ceq 'data-service,design-grammars,dg-reasoner,neo4j')
    foreach ($p in $Job.images.PSObject.Properties) {
        $actual = $build.images.($p.Name)
        Assert-True ($actual.status -ceq 'BUILD_EXPORT_COMPLETE' -and $actual.iid -ceq $p.Value.imageId)
        foreach ($field in $p.Value.PSObject.Properties) {
            if ($field.Name -eq 'archiveBytes') {
                Assert-True ($actual.($field.Name) -is [ValueType] -and $actual.($field.Name) -isnot [bool] -and $actual.($field.Name) -eq $field.Value)
            } else { Assert-True ($actual.($field.Name) -is [string] -and $actual.($field.Name) -ceq $field.Value) }
        }
    }
    return Get-Hash $path
}

$root = [IO.Path]::GetFullPath((Split-Path -Parent $PSScriptRoot))
$stage = 'package-preflight'
$report = [ordered]@{schemaVersion=1; kind='controlled-image-load-smoke-not-release'; status='FAILED'; failureStage=$null; dockerInvoked=$false; releaseAccepted=$false; archiveBytesVerified=$false; crossDaemonPortabilityProven=$false; fullHostedAcceptance=$false; cleanup='not-started'; checks=[ordered]@{}; images=[ordered]@{}}
$output = $null
$outputOwned = $false
try {
    Assert-True ($OutputDirectory -match '^[A-Za-z]:[\\/]')
    $output = [IO.Path]::GetFullPath($OutputDirectory)
    Assert-RegularPath $output
    Assert-True (-not (Test-Path -LiteralPath $output) -and (Test-Path -LiteralPath (Split-Path -Parent $output) -PathType Container))
    Assert-True (-not $output.Equals($root, [StringComparison]::OrdinalIgnoreCase) -and -not $output.StartsWith($root + '\', [StringComparison]::OrdinalIgnoreCase))
    [void][IO.Directory]::CreateDirectory($output)
    $outputOwned = $true
    Assert-True (-not ($PackagePreflightOnly -and $RunIsolatedSmoke))
    $job = Assert-RuntimePackage $root $PackageZip $ExpectedZipSha256
    $report.packageZipSha256 = Get-Hash $PackageZip
    $report.sourceRevision = $job.sourceRevision
    $report.sourceManifestSha256 = $job.sourceManifestSha256
    $report.checks.packageIntegrity = $true
    if ($PackagePreflightOnly) { $report.status = 'PACKAGE_PREFLIGHT_COMPLETE' }
    else {
        $stage = 'archive-and-build-report-verification'
        Assert-True ($ArchiveDirectory -and -not $output.Equals([IO.Path]::GetFullPath($ArchiveDirectory), [StringComparison]::OrdinalIgnoreCase) -and -not $output.StartsWith([IO.Path]::GetFullPath($ArchiveDirectory).TrimEnd('\') + '\', [StringComparison]::OrdinalIgnoreCase))
        Assert-Archives $ArchiveDirectory $job.images
        $report.buildReportSha256 = Assert-BuildReport $ArchiveDirectory $root $job
        $report.archiveBytesVerified = $true
        $report.checks.buildReportBoundToIssuedPackage = $true
        foreach ($p in $job.images.PSObject.Properties) {
            $report.images[$p.Name] = [ordered]@{imageId=$p.Value.imageId; archiveSha256=$p.Value.archiveSha256; archiveBytes=$p.Value.archiveBytes; archiveVerified=$true}
        }
        if ($RunIsolatedSmoke) {
            $stage = 'isolated-runtime'
            . (Join-Path $PSScriptRoot 'runtime-execution.ps1')
            Invoke-IsolatedSmoke $root $output $ArchiveDirectory $job $report
        } else { $report.status = 'ARCHIVES_VERIFIED_NO_DOCKER' }
    }
} catch {
    if ($null -eq $report.failureStage) { $report.failureStage = $stage }
    $report.status = 'FAILED'
    [Console]::Error.WriteLine('IMAGE_RUNTIME_FAILED: ' + $report.failureStage)
}
if ($outputOwned) {
    try { [IO.File]::WriteAllText((Join-Path $output 'runtime-report.json'), (ConvertTo-Json -InputObject $report -Depth 20), (New-Object Text.UTF8Encoding($false))) }
    catch { [Console]::Error.WriteLine('IMAGE_RUNTIME_REPORT_WRITE_FAILED'); exit 1 }
}
if ($report.status -eq 'FAILED') { exit 1 }
exit 0
