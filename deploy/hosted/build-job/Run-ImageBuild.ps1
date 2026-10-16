#requires -Version 5.1
[CmdletBinding()]
param(
    [Parameter(Mandatory=$true)][string]$PackageZip,
    [Parameter(Mandatory=$true)][string]$ExpectedZipSha256,
    [Parameter(Mandatory=$true)][string]$OutputDirectory,
    [switch]$PreflightOnly
)
Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

function Get-Sha256([string]$Path) {
    return (Get-FileHash -LiteralPath $Path -Algorithm SHA256).Hash.ToLowerInvariant()
}

function Write-BuildReport($Report, [string]$Directory) {
    $json = ConvertTo-Json -InputObject $Report -Depth 30
    [IO.File]::WriteAllText((Join-Path $Directory 'build-report.json'), $json, (New-Object Text.UTF8Encoding($false)))
}

function Assert-SafeRelative([string]$Name) {
    if (-not $Name -or $Name -match '[\\\x00-\x1f:*?"<>|]' -or $Name.StartsWith('/')) { throw 'unsafe path' }
    foreach ($part in $Name.Split('/')) {
        if (-not $part -or $part -in @('.', '..') -or $part -match '[. ]$' -or
            $part -match '^(?i:CON|PRN|AUX|NUL|COM[1-9]|LPT[1-9])(?:\.|$)') { throw 'unsafe path' }
    }
}

function Assert-NoReparseAncestors([string]$Path) {
    $current = [IO.Path]::GetFullPath($Path)
    while ($current) {
        if (Test-Path -LiteralPath $current) {
            $item = Get-Item -LiteralPath $current -Force
            if (($item.Attributes -band [IO.FileAttributes]::ReparsePoint) -ne 0 -or $item.LinkType) { throw 'linked path' }
        }
        $parent = Split-Path -Parent $current
        if ($parent -eq $current) { break }
        $current = $parent
    }
}

function Get-TreeFiles([string]$Root) {
    $found = @{}
    $directories = New-Object 'Collections.Generic.List[string]'
    $pending = New-Object 'Collections.Generic.Stack[string]'
    $pending.Push($Root)
    while ($pending.Count) {
        foreach ($item in Get-ChildItem -LiteralPath $pending.Pop() -Force) {
            if (($item.Attributes -band [IO.FileAttributes]::ReparsePoint) -ne 0 -or $item.LinkType) { throw 'linked tree' }
            $relative = $item.FullName.Substring($Root.TrimEnd('\').Length + 1).Replace('\', '/')
            Assert-SafeRelative $relative
            if ($item.PSIsContainer) { $directories.Add($relative); $pending.Push($item.FullName) }
            else {
                if ($found.ContainsKey($relative)) { throw 'duplicate tree file' }
                $found[$relative] = Get-Sha256 $item.FullName
            }
        }
    }
    foreach ($directory in $directories) {
        $prefix = $directory + '/'
        if (-not @($found.Keys | Where-Object {$_.StartsWith($prefix, [StringComparison]::Ordinal)}).Count) { throw 'unmanifested directory' }
    }
    return $found
}

function Get-HashMap($Object) {
    if ($null -eq $Object -or $Object -isnot [PSCustomObject]) { throw 'invalid file map' }
    $map = @{}
    foreach ($property in $Object.PSObject.Properties) {
        Assert-SafeRelative $property.Name
        if ($property.Value -isnot [string] -or $property.Value -cnotmatch '^[0-9a-f]{64}$' -or $map.ContainsKey($property.Name)) { throw 'invalid file hash' }
        $map[$property.Name] = $property.Value
    }
    return $map
}

function Assert-MapEqual($Actual, $Expected) {
    if ($Actual.Count -ne $Expected.Count) { throw 'membership mismatch' }
    foreach ($name in $Expected.Keys) {
        if (-not $Actual.ContainsKey($name) -or -not @($Actual.Keys | Where-Object {$_ -ceq $name}).Count -or $Actual[$name] -cne $Expected[$name]) { throw 'file mismatch' }
    }
}

function Assert-Package([string]$Root, [string]$ZipPath, [string]$ExpectedHash, [string]$RunnerPath) {
    Assert-NoReparseAncestors $Root
    Assert-NoReparseAncestors $ZipPath
    if ($ExpectedHash -cnotmatch '^[0-9a-f]{64}$' -or (Get-Sha256 $ZipPath) -cne $ExpectedHash) { throw 'ZIP hash mismatch' }
    $tree = Get-TreeFiles $Root
    $jobPath = Join-Path $Root 'build-job-manifest.json'
    $job = Get-Content -LiteralPath $jobPath -Raw | ConvertFrom-Json
    if ($job.schemaVersion -ne 1 -or $job.kind -cne 'controlled-image-build-not-release' -or
        $job.frameworkRevision -cnotmatch '^[0-9a-f]{40}$' -or $job.target -cne 'DESKTOP-OS4Q8CP' -or
        $job.toolingStatus -cne 'hashed-preparation-tools-not-part-of-source-revision') { throw 'job contract mismatch' }
    $expected = Get-HashMap $job.files
    if ($expected.ContainsKey('build-job-manifest.json')) { throw 'recursive manifest entry' }
    $expected['build-job-manifest.json'] = Get-Sha256 $jobPath
    Assert-MapEqual $tree $expected
    if (-not $expected.ContainsKey('support/Run-ImageBuild.ps1') -or
        (Get-Sha256 $RunnerPath) -cne $expected['support/Run-ImageBuild.ps1']) { throw 'runner mismatch' }
    foreach ($name in $expected.Keys) {
        if ($name -cne 'build-job-manifest.json' -and $name -cne 'support/Run-ImageBuild.ps1' -and -not $name.StartsWith('source/', [StringComparison]::Ordinal)) { throw 'unexpected package path' }
    }
    Add-Type -AssemblyName System.IO.Compression.FileSystem
    $zip = [IO.Compression.ZipFile]::OpenRead($ZipPath)
    try {
        $members = @{}
        foreach ($entry in $zip.Entries) {
            Assert-SafeRelative $entry.FullName
            # Only regular file entries; no explicit directories, symlinks, devices or reparse attributes.
            $attributes = [BitConverter]::ToUInt32([BitConverter]::GetBytes([int]$entry.ExternalAttributes), 0)
            $mode = ($attributes -shr 16) -band 61440
            if ($mode -notin @(0, 32768) -or ($attributes -band 1040) -ne 0 -or $members.ContainsKey($entry.FullName)) { throw 'unsupported ZIP member' }
            $stream = $entry.Open()
            $algorithm = [Security.Cryptography.SHA256]::Create()
            try { $hash = [BitConverter]::ToString($algorithm.ComputeHash($stream)).Replace('-', '').ToLowerInvariant() }
            finally { $algorithm.Dispose(); $stream.Dispose() }
            $members[$entry.FullName] = $hash
        }
        Assert-MapEqual $members $expected
    } finally { $zip.Dispose() }
    $sourcePath = Join-Path $Root 'source/manifest.json'
    if ($job.sourceManifestSha256 -cnotmatch '^[0-9a-f]{64}$' -or (Get-Sha256 $sourcePath) -cne $job.sourceManifestSha256) { throw 'source manifest mismatch' }
    $source = Get-Content -LiteralPath $sourcePath -Raw | ConvertFrom-Json
    if ($source.schemaVersion -ne 1 -or $source.status -cne 'BLOCKED' -or $source.frameworkRevision -cne $job.frameworkRevision) { throw 'source provenance mismatch' }
    $sourceExpected = Get-HashMap $source.files
    $sourceActual = @{}
    foreach ($name in $tree.Keys) {
        if ($name.StartsWith('source/', [StringComparison]::Ordinal) -and $name -cne 'source/manifest.json') { $sourceActual[$name.Substring(7)] = $tree[$name] }
    }
    Assert-MapEqual $sourceActual $sourceExpected
    $services = [ordered]@{'neo4j'='source/neo4j'; 'dg-reasoner'='source/dg-reasoner'; 'data-service'='source/data-service'; 'design-grammars'='source/ui-v2'}
    if (@($job.services.PSObject.Properties).Count -ne 4) { throw 'service contract mismatch' }
    foreach ($name in $services.Keys) {
        $service = $job.services.PSObject.Properties[$name].Value
        if ($service.context -cne $services[$name] -or $service.dockerfile -cne 'Dockerfile' -or
            @($service.PSObject.Properties).Count -ne 2 -or -not $tree.ContainsKey($services[$name] + '/Dockerfile')) { throw 'service contract mismatch' }
    }
    return $job
}

function Assert-RuntimeGuard([string]$ComputerName, [System.Collections.IDictionary]$Environment) {
    if ($ComputerName -cne 'DESKTOP-OS4Q8CP') { throw 'named host required' }
    foreach ($key in $Environment.Keys) {
        if ([string]$key -match '^(?i:DOCKER_|BUILDKIT_|BUILDX_)' -and [string]$Environment[$key] -ne '') { throw 'Docker environment override rejected' }
    }
}

function Assert-FreeBytes([long]$AvailableBytes) {
    if ($AvailableBytes -lt 30GB) { throw 'at least 30GB free space required' }
}

function New-LocalTag([string]$Service) {
    if ($Service -notin @('neo4j','dg-reasoner','data-service','design-grammars')) { throw 'unknown service' }
    return 'dg-controlled/' + $Service + ':' + [guid]::NewGuid().ToString('N')
}

function Get-ServiceContext([string]$Service, [string]$Root) {
    $contexts = @{'neo4j'='neo4j'; 'dg-reasoner'='dg-reasoner'; 'data-service'='data-service'; 'design-grammars'='ui-v2'}
    if (-not $contexts.ContainsKey($Service)) { throw 'unknown service' }
    return Join-Path (Join-Path $Root 'source') $contexts[$Service]
}

function Get-BuildArguments([string]$Service, [string]$Root, [string]$Output, [string]$Revision, [string]$Tag) {
    if ($Revision -cnotmatch '^[0-9a-f]{40}$') { throw 'exact revision required' }
    $context = Get-ServiceContext $Service $Root
    return @('--host', 'npipe:////./pipe/docker_engine', 'build', '--pull', '--no-cache', '--platform', 'linux/amd64',
        '--iidfile', (Join-Path $Output ($Service + '.iid')), '--label', ('org.opencontainers.image.revision=' + $Revision),
        '--tag', $Tag, '--file', (Join-Path $context 'Dockerfile'), $context)
}

function Get-SaveArguments([string]$Service, [string]$Output, [string]$Tag) {
    return @('--host', 'npipe:////./pipe/docker_engine', 'image', 'save', '--output', (Join-Path $Output ($Service + '.tar')), $Tag)
}

function Get-InspectArguments([string]$Tag) {
    return @('--host', 'npipe:////./pipe/docker_engine', 'image', 'inspect', '--format',
        '{"Id":{{json .Id}},"RepoDigests":{{json .RepoDigests}},"Os":{{json .Os}},"Architecture":{{json .Architecture}}}', $Tag)
}

function Confirm-ImageIdentity([string]$Iid, [string]$Inspection) {
    $image = $Inspection | ConvertFrom-Json
    $fields = @($image.PSObject.Properties.Name | Sort-Object)
    if (($fields -join ',') -cne 'Architecture,Id,Os,RepoDigests' -or $Iid -cnotmatch '^sha256:[0-9a-f]{64}$' -or
        $image.Id -cne $Iid -or $image.Os -cne 'linux' -or $image.Architecture -cne 'amd64') { throw 'image identity or platform mismatch' }
    $digests = @()
    foreach ($digest in $image.RepoDigests) {
        if ($digest -isnot [string] -or $digest -cnotmatch '^[a-zA-Z0-9][a-zA-Z0-9._:/-]*@sha256:[0-9a-f]{64}$') { throw 'invalid repo digest' }
        $digests += $digest
    }
    return [ordered]@{imageId=$Iid; repoDigests=$digests; os=$image.Os; architecture=$image.Architecture}
}

function ConvertTo-WindowsArgument([string]$Value) {
    # CommandLineToArgvW/C-runtime quoting; never use a shell to launch Docker.
    return '"' + [regex]::Replace([regex]::Replace($Value, '(\\*)"', '$1$1\"'), '(\\+)$', '$1$1') + '"'
}

function Invoke-BoundedProcess([string]$Executable, [string[]]$Arguments, [int]$TimeoutSeconds, [datetime]$Deadline, [switch]$Capture) {
    $remaining = [math]::Min($TimeoutSeconds, ($Deadline - [datetime]::UtcNow).TotalSeconds)
    if ($remaining -le 0) { throw 'total time limit' }
    $info = New-Object Diagnostics.ProcessStartInfo
    $info.FileName = $Executable
    $info.Arguments = (@($Arguments | ForEach-Object { ConvertTo-WindowsArgument $_ }) -join ' ')
    $info.UseShellExecute = $false
    $info.CreateNoWindow = $true
    $info.RedirectStandardOutput = $true
    $info.RedirectStandardError = $true
    $process = New-Object Diagnostics.Process
    $process.StartInfo = $info
    try {
        [void]$process.Start()
        # Drain asynchronously, discarding all build/save stdout and all stderr.
        # Only the explicit four-field inspect projection is captured in memory.
        if ($Capture) { $stdout = $process.StandardOutput.ReadToEndAsync() }
        else { $stdout = $process.StandardOutput.BaseStream.CopyToAsync([IO.Stream]::Null) }
        $stderr = $process.StandardError.BaseStream.CopyToAsync([IO.Stream]::Null)
        if (-not $process.WaitForExit([int][math]::Floor($remaining * 1000))) {
            $killerInfo = New-Object Diagnostics.ProcessStartInfo
            $killerInfo.FileName = Join-Path $env:SystemRoot 'System32/taskkill.exe'
            $killerInfo.Arguments = '/PID ' + $process.Id + ' /T /F'
            $killerInfo.UseShellExecute = $false
            $killerInfo.CreateNoWindow = $true
            $killerInfo.RedirectStandardOutput = $true
            $killerInfo.RedirectStandardError = $true
            $killer = [Diagnostics.Process]::Start($killerInfo)
            try {
                $killOut = $killer.StandardOutput.BaseStream.CopyToAsync([IO.Stream]::Null)
                $killErr = $killer.StandardError.BaseStream.CopyToAsync([IO.Stream]::Null)
                if (-not $killer.WaitForExit(15000)) { $killer.Kill(); [void]$killer.WaitForExit(5000) }
            } finally { $killer.Dispose() }
            if (-not $process.WaitForExit(15000)) { throw 'timeout termination unconfirmed; daemon build cancellation unproven' }
            throw 'command timeout; daemon build cancellation unproven'
        }
        # The process has exited; bounded drain completion avoids pipe-inheriting child hangs.
        if (-not $stdout.Wait(5000) -or -not $stderr.Wait(5000)) { throw 'output drain timeout' }
        if ($process.ExitCode -ne 0) { throw 'command failed' }
        if ($Capture) {
            $result = $stdout.Result
            if ($result.Length -gt 65536) { throw 'inspect output too large' }
            return $result.Trim()
        }
        return ''
    } finally { $process.Dispose() }
}

$root = [IO.Path]::GetFullPath((Split-Path -Parent $PSScriptRoot))
$stage = 'preflight'
$report = [ordered]@{
    schemaVersion = 1; kind = 'controlled-image-build-not-release'; status = 'FAILED'
    failureStage = $null; dockerInvoked = $false; releaseAccepted = $false
    reproducibleDependencies = $false; dependencyCaveat = 'Mutable base images and dependency resolution; not a reproducible release.'
    daemonBuildCancellationProven = $false
    timeoutCaveat = 'Timeout terminates the CLI process tree and waits; daemon-side build cancellation is unproven. Inspect the daemon manually; no automatic cleanup is authorized.'
    commandTimeoutSeconds = 2700; totalTimeoutSeconds = 10800
    images = [ordered]@{}
}
$output = $null
$outputCreated = $false
try {
    if ($OutputDirectory -notmatch '^[A-Za-z]:[\\/]') { throw 'absolute local output required' }
    $output = [IO.Path]::GetFullPath($OutputDirectory)
    $outputDrive = New-Object IO.DriveInfo([IO.Path]::GetPathRoot($output))
    if ($outputDrive.DriveType -ne [IO.DriveType]::Fixed) { throw 'local fixed drive required' }
    Assert-NoReparseAncestors $output
    if (Test-Path -LiteralPath $output) { throw 'output already exists' }
    if ($output.Equals($root, [StringComparison]::OrdinalIgnoreCase) -or
        $output.StartsWith($root.TrimEnd('\') + '\', [StringComparison]::OrdinalIgnoreCase)) { throw 'output must be external' }
    $parent = Split-Path -Parent $output
    if (-not (Test-Path -LiteralPath $parent -PathType Container)) { throw 'output parent must exist' }
    [void](New-Item -ItemType Directory -Path $output -ErrorAction Stop)
    $outputCreated = $true
    $job = Assert-Package $root $PackageZip $ExpectedZipSha256 $PSCommandPath
    $source = Get-Content -LiteralPath (Join-Path $root 'source/manifest.json') -Raw | ConvertFrom-Json
    $report.sourceRevision = $job.frameworkRevision
    $report.sourceManifest = $source
    $report.sourceManifestSha256 = $job.sourceManifestSha256
    $report.packageZipSha256 = Get-Sha256 $PackageZip
    $report.packageFiles = $job.files
    $report.runnerTooling = [ordered]@{path='support/Run-ImageBuild.ps1'; sha256=(Get-Sha256 $PSCommandPath); status=$job.toolingStatus}
    $contexts = [ordered]@{}
    foreach ($service in $job.services.PSObject.Properties) {
        $mapping = [ordered]@{}
        $prefix = $service.Value.context.Substring(7) + '/'
        foreach ($file in $source.files.PSObject.Properties) {
            if ($file.Name.StartsWith($prefix, [StringComparison]::Ordinal)) { $mapping[$file.Name] = $file.Value }
        }
        $contexts[$service.Name] = [ordered]@{context=$service.Value.context; dockerfile=$service.Value.dockerfile; sourceFiles=$mapping}
    }
    $report.contexts = $contexts
    if ($PreflightOnly) {
        $report.status = 'PREFLIGHT_ONLY_COMPLETE'
        Write-BuildReport $report $output
        exit 0
    }
    $stage = 'runtime-guard'
    Assert-RuntimeGuard ([Environment]::MachineName) ([Environment]::GetEnvironmentVariables())
    $deadline = [datetime]::UtcNow.AddHours(3)
    $drive = New-Object IO.DriveInfo([IO.Path]::GetPathRoot($output))
    Assert-FreeBytes $drive.AvailableFreeSpace
    $docker = (Get-Command docker.exe -CommandType Application -ErrorAction Stop).Source
    $report.target = 'DESKTOP-OS4Q8CP'
    $report.dockerEndpoint = 'npipe:////./pipe/docker_engine'
    $report.retainedArtifacts = 'Local images and image tar archives remain; no cleanup or deployment performed.'
    # Empty private CLI config prevents inherited contexts, credentials or proxy build arguments.
    # Set only for child processes by temporarily replacing process environment after guard.
    $config = Join-Path $output 'docker-config'
    [void][IO.Directory]::CreateDirectory($config)
    [IO.File]::WriteAllText((Join-Path $config 'config.json'), '{}')
    $oldConfig = [Environment]::GetEnvironmentVariable('DOCKER_CONFIG')
    [Environment]::SetEnvironmentVariable('DOCKER_CONFIG', $config)
    try {
        foreach ($service in @('neo4j', 'dg-reasoner', 'data-service', 'design-grammars')) {
            $stage = 'verify-inputs:' + $service
            [void](Assert-Package $root $PackageZip $ExpectedZipSha256 $PSCommandPath)
            Assert-FreeBytes $drive.AvailableFreeSpace
            $tag = New-LocalTag $service
            $report.images[$service] = [ordered]@{tag=$tag; status='BUILD_PENDING'}
            $stage = 'build:' + $service
            $report.dockerInvoked = $true
            [void](Invoke-BoundedProcess $docker (Get-BuildArguments $service $root $output $job.frameworkRevision $tag) 2700 $deadline)
            $stage = 'inspect:' + $service
            $iid = (Get-Content -LiteralPath (Join-Path $output ($service + '.iid')) -Raw).Trim()
            $inspection = Invoke-BoundedProcess $docker (Get-InspectArguments $tag) 2700 $deadline -Capture
            $identity = Confirm-ImageIdentity $iid $inspection
            $report.images[$service] = [ordered]@{tag=$tag; status='IMAGE_VERIFIED'; iid=$iid; imageId=$identity.imageId; repoDigests=$identity.repoDigests; os=$identity.os; architecture=$identity.architecture}
            $stage = 'save:' + $service
            [void](Invoke-BoundedProcess $docker (Get-SaveArguments $service $output $tag) 2700 $deadline)
            $stage = 'archive-hash:' + $service
            $archive = Join-Path $output ($service + '.tar')
            Assert-NoReparseAncestors $archive
            $size = (Get-Item -LiteralPath $archive).Length
            if ($size -le 0) { throw 'empty archive' }
            $report.images[$service].archive = $service + '.tar'
            $report.images[$service].archiveSha256 = Get-Sha256 $archive
            $report.images[$service].archiveBytes = $size
            $report.images[$service].status = 'BUILD_EXPORT_COMPLETE'
            Write-BuildReport $report $output
            if ([datetime]::UtcNow -ge $deadline) { throw 'total time limit' }
        }
    } finally { [Environment]::SetEnvironmentVariable('DOCKER_CONFIG', $oldConfig) }
    if ($report.images.Count -ne 4 -or @($report.images.Values | Where-Object {$_.status -cne 'BUILD_EXPORT_COMPLETE'}).Count -ne 0) { throw 'incomplete build export' }
    $report.status = 'BUILD_EXPORT_COMPLETE'
    Write-BuildReport $report $output
    exit 0
} catch {
    $report.failureStage = $stage
    if ($outputCreated) { Write-BuildReport $report $output }
    [Console]::Error.WriteLine('CONTROLLED_BUILD_FAILED: ' + $stage)
    exit 1
}
