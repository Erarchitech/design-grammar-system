# Standalone collector: keep outside the immutable extracted package.
param(
  [Parameter(Mandatory=$true)][string]$PackageZip,
  [Parameter(Mandatory=$true)][string]$PackageRoot,
  [Parameter(Mandatory=$true)][string]$ReportPath,
  [switch]$PreflightOnly
)
$ErrorActionPreference = 'Stop'
Set-StrictMode -Version 2.0
# Pins identify the issued source package, NOT Docker build provenance or a release.
$approvedZipSha256 = '1e032824fbb3006d3e001a3460185a97e1d4661941910671f6f4f62ecc4af87e'
$expectedRevision = '2dedbfb3e138c2b437e781696197105dca93342a'
$expectedCandidateSha256 = '864878de1e60aadc79211f20e574f32cb5f97a096c06dac696a1f52215f04810'
$target = 'DESKTOP-OS4Q8CP'
$project = 'dg-hosted-1309-sandbox'
$stage = 'paths'
$reportStream = $null
$zipStream = $null
$archive = $null
$report = [ordered]@{
  schemaVersion=1; kind='candidate-three-image-observation-not-release'; status='BLOCKED'
  failureStage=$null; target=$target; zipSha256=$null; frameworkRevision=$null
  candidateManifestSha256=$null; dockerInvoked=$false; observedAtUtc=$null
  releaseAcceptance=$false; fullStackInventory=$false; buildProvenance='not-established'
  historicalRunImageBinding='not-established'; requestedImages=[ordered]@{}; images=@()
}
function Assert-Inventory($Condition, [string]$Message) {
  if (-not $Condition) { throw $Message }
}
function Assert-UnlinkedAncestors([string]$Path) {
  $item = Get-Item -LiteralPath $Path -Force
  while ($null -ne $item) {
    Assert-Inventory (-not ($item.Attributes -band [IO.FileAttributes]::ReparsePoint)) 'linked path'
    $parent = Split-Path -Parent $item.FullName
    if (-not $parent -or $parent -eq $item.FullName) { break }
    $item = Get-Item -LiteralPath $parent -Force
  }
}
function Get-UnlinkedFiles([string]$Directory) {
  foreach ($item in @(Get-ChildItem -LiteralPath $Directory -Force)) {
    Assert-Inventory (-not ($item.Attributes -band [IO.FileAttributes]::ReparsePoint)) 'linked member'
    if ($item.PSIsContainer) { Get-UnlinkedFiles $item.FullName } else { $item }
  }
}
function Get-StreamSha256([IO.Stream]$Stream) {
  $sha = [Security.Cryptography.SHA256]::Create()
  try { return [BitConverter]::ToString($sha.ComputeHash($Stream)).Replace('-','').ToLowerInvariant() }
  finally { $sha.Dispose() }
}
function Read-ZipJson([string]$Name) {
  $reader = [IO.StreamReader]::new($archive.GetEntry($Name).Open())
  try { return ($reader.ReadToEnd() | ConvertFrom-Json) } finally { $reader.Dispose() }
}
function Assert-TargetHost {
  Assert-Inventory ([Environment]::MachineName.ToUpperInvariant() -ceq 'DESKTOP-OS4Q8CP') 'wrong host'
}
function New-ImageInspectArguments([string]$Image) {
  Assert-Inventory ($Image -cin @('dg-hosted-1309-sandbox-neo4j:latest', 'dg-hosted-1309-sandbox-data-service:latest', 'n8nio/n8n:2.4.8')) 'unapproved image'
  $format = '{"Id":{{json .Id}},"RepoDigests":{{json .RepoDigests}},"Os":{{json .Os}},"Architecture":{{json .Architecture}}}'
  return @('--host','npipe:////./pipe/docker_engine','image','inspect','--format',$format,$Image)
}
function Convert-ImageObservation([string]$Service, [string]$Image, [string]$Text) {
  [void](New-ImageInspectArguments $Image)
  $expectedImage = switch ($Service) {
    'neo4j' { 'dg-hosted-1309-sandbox-neo4j:latest' }
    'data-service' { 'dg-hosted-1309-sandbox-data-service:latest' }
    'n8n' { 'n8nio/n8n:2.4.8' }
    default { throw 'unapproved service' }
  }
  Assert-Inventory ($Image -ceq $expectedImage -and $Text.Length -le 16384) 'invalid observation'
  $raw = $Text | ConvertFrom-Json
  Assert-Inventory ($raw.Id -is [string] -and $raw.Id -cmatch '^sha256:[0-9a-f]{64}$') 'invalid config image ID'
  Assert-Inventory ($raw.Os -cin @('linux','windows')) 'invalid OS'
  Assert-Inventory ($raw.Architecture -cin @('amd64','arm64','arm','386','ppc64le','s390x','riscv64')) 'invalid architecture'
  $digests = @()
  if ($null -ne $raw.RepoDigests) {
    Assert-Inventory ($raw.RepoDigests -is [Array] -and $raw.RepoDigests.Count -le 32) 'invalid digest array'
    foreach ($digest in $raw.RepoDigests) {
      Assert-Inventory ($digest -is [string] -and $digest.Length -le 320 -and $digest -cmatch '^[a-z0-9][a-z0-9._:/-]*@sha256:[0-9a-f]{64}$') 'invalid registry digest'
      $digests += $digest
    }
  }
  return [ordered]@{
    service=$Service; image=$Image
    status=$(if ($digests.Count) { 'OBSERVED_NOW' } else { 'UNRESOLVED_REGISTRY_DIGEST' })
    # Id hashes the local image config. It is never used to fill a RepoDigest.
    localConfigImageId=$raw.Id; registryRepoDigests=@($digests | Sort-Object -Unique)
    os=$raw.Os; architecture=$raw.Architecture
  }
}
function Invoke-FixedImageInspect([string]$Image) {
  # This is the ONLY native launch. No caller-supplied executable or arguments.
  Assert-TargetHost
  foreach ($key in @('DOCKER_HOST','DOCKER_CONTEXT','DOCKER_TLS','DOCKER_TLS_VERIFY','DOCKER_CERT_PATH','DOCKER_API_VERSION','DOCKER_CONFIG')) {
    Assert-Inventory (-not [Environment]::GetEnvironmentVariable($key, 'Process')) 'Docker override forbidden'
  }
  $arguments = @(New-ImageInspectArguments $Image)
  $docker = Get-Command docker.exe -CommandType Application -ErrorAction Stop
  $psi = [Diagnostics.ProcessStartInfo]::new()
  $psi.FileName = $docker.Source
  $psi.Arguments = (($arguments | ForEach-Object { '"' + $_.Replace('"','\"') + '"' }) -join ' ')
  $psi.UseShellExecute = $false
  $psi.CreateNoWindow = $true
  $psi.RedirectStandardOutput = $true
  $psi.RedirectStandardError = $true
  $p = [Diagnostics.Process]::new()
  $p.StartInfo = $psi
  try {
    [void]$p.Start()
    $script:report.dockerInvoked = $true
    $stdout = $p.StandardOutput.ReadToEndAsync()
    $stderr = $p.StandardError.ReadToEndAsync()
    if (-not $p.WaitForExit(15000)) {
      $p.Kill()
      [void]$p.WaitForExit(5000)
      throw 'image inspect timed out'
    }
    $text = $stdout.GetAwaiter().GetResult()
    [void]$stderr.GetAwaiter().GetResult() # discard, never emit native errors
    return @{ code=$p.ExitCode; text=$text }
  } finally { $p.Dispose() }
}
try {
  $root = (Resolve-Path -LiteralPath $PackageRoot).ProviderPath.TrimEnd([IO.Path]::DirectorySeparatorChar)
  Assert-Inventory (Test-Path -LiteralPath $root -PathType Container) 'package directory required'
  Assert-UnlinkedAncestors $root
  $reportFile = [IO.Path]::GetFullPath($ReportPath)
  Assert-UnlinkedAncestors (Split-Path -Parent $reportFile)
  Assert-Inventory (-not $reportFile.StartsWith($root + [IO.Path]::DirectorySeparatorChar, [StringComparison]::OrdinalIgnoreCase)) 'report inside package'
  Assert-Inventory (-not (Test-Path -LiteralPath $reportFile)) 'report exists'
  # Atomic ownership: CreateNew refuses even concurrent writers. Never truncate.
  $reportStream = [IO.File]::Open($reportFile, [IO.FileMode]::CreateNew, [IO.FileAccess]::Write, [IO.FileShare]::None)
  $stage = 'zip-integrity'
  $zip = (Resolve-Path -LiteralPath $PackageZip).ProviderPath
  Assert-UnlinkedAncestors $zip
  Assert-Inventory (-not $zip.StartsWith($root + [IO.Path]::DirectorySeparatorChar, [StringComparison]::OrdinalIgnoreCase)) 'ZIP inside package'
  $zipStream = [IO.File]::Open($zip, [IO.FileMode]::Open, [IO.FileAccess]::Read, [IO.FileShare]::Read)
  $zipHash = Get-StreamSha256 $zipStream
  Assert-Inventory ($zipHash -ceq $approvedZipSha256) 'unapproved ZIP'
  $report.zipSha256 = $zipHash
  $zipStream.Position = 0
  Add-Type -AssemblyName System.IO.Compression
  $archive = [IO.Compression.ZipArchive]::new($zipStream, [IO.Compression.ZipArchiveMode]::Read, $true)
  $stage = 'package-integrity'
  $manifest = Read-ZipJson 'bundle-test-manifest.json'
  Assert-Inventory ($manifest.schemaVersion -eq 1 -and $manifest.kind -ceq 'hosted-candidate-capability-test-not-release') 'wrong package schema'
  Assert-Inventory ($manifest.frameworkRevision -ceq $expectedRevision) 'wrong revision'
  Assert-Inventory ($manifest.candidateManifestSha256 -ceq $expectedCandidateSha256) 'wrong candidate identity'
  $allowed = @{}
  foreach ($p in $manifest.files.PSObject.Properties) {
    Assert-Inventory ($p.Name -cmatch '^[a-zA-Z0-9_./-]+$' -and -not $p.Name.Contains('..') -and -not $p.Name.StartsWith('/') -and -not $p.Name.EndsWith('/') -and -not $allowed.ContainsKey($p.Name)) 'unsafe or duplicate member'
    Assert-Inventory ($p.Value -cmatch '^[0-9a-f]{64}$') 'invalid member hash'
    $allowed[$p.Name] = $p.Value
  }
  $seen = @{}
  foreach ($entry in $archive.Entries) {
    $name = $entry.FullName
    Assert-Inventory (-not $seen.ContainsKey($name)) 'duplicate ZIP entry'
    $seen[$name] = $true
    Assert-Inventory ($name -ceq 'bundle-test-manifest.json' -or $allowed.ContainsKey($name)) 'unknown ZIP entry'
    Assert-Inventory ($entry.Length -le 32000000 -and (($entry.ExternalAttributes -shr 16) -band 61440) -ne 40960) 'unsafe ZIP entry'
    $stream = $entry.Open()
    try { $entryHash = Get-StreamSha256 $stream } finally { $stream.Dispose() }
    if ($name -cne 'bundle-test-manifest.json') {
      Assert-Inventory ($entryHash -ceq $allowed[$name]) 'ZIP member hash mismatch'
    }
    $file = Join-Path $root ($name.Replace('/', [IO.Path]::DirectorySeparatorChar))
    Assert-UnlinkedAncestors $file
    Assert-Inventory ((Get-FileHash -LiteralPath $file -Algorithm SHA256).Hash.ToLowerInvariant() -ceq $entryHash) 'extracted hash mismatch'
  }
  Assert-Inventory ($seen.Count -eq ($allowed.Count + 1)) 'missing ZIP entries'
  $actual = @(Get-UnlinkedFiles $root)
  Assert-Inventory ($actual.Count -eq $seen.Count) 'extra or missing extracted files'
  foreach ($file in $actual) {
    $relative = $file.FullName.Substring($root.Length + 1).Replace([IO.Path]::DirectorySeparatorChar, '/')
    Assert-Inventory ($seen.ContainsKey($relative)) 'unknown extracted member'
  }
  $candidate = Read-ZipJson 'candidate/manifest.json'
  Assert-Inventory ($allowed['candidate/manifest.json'] -ceq $expectedCandidateSha256 -and $candidate.frameworkRevision -ceq $expectedRevision) 'candidate mismatch'
  Assert-Inventory ($candidate.schemaVersion -eq 1 -and $candidate.status -ceq 'BLOCKED' -and $null -eq $candidate.degramGitlink) 'candidate schema mismatch'
  $candidateCount = 0
  foreach ($p in $candidate.files.PSObject.Properties) {
    $key = 'candidate/' + $p.Name
    Assert-Inventory ($allowed.ContainsKey($key) -and $allowed[$key] -ceq $p.Value) 'candidate member mismatch'
    $candidateCount++
  }
  Assert-Inventory (@($allowed.Keys | Where-Object { $_.StartsWith('candidate/') }).Count -eq ($candidateCount + 1)) 'candidate membership mismatch'
  $report.frameworkRevision = $expectedRevision
  $report.candidateManifestSha256 = $expectedCandidateSha256
  # Authenticated JSON only: no Compose invocation, interpolation or .env load.
  $model = Read-ZipJson 'compose.json'
  Assert-Inventory ((@($model.services.PSObject.Properties.Name | Sort-Object) -join ',') -ceq 'data-service,n8n,neo4j') 'unexpected services'
  foreach ($service in @('neo4j','data-service','n8n')) {
    $definition = $model.services.$service
    $imageProperty = $definition.PSObject.Properties['image']
    if ($null -ne $imageProperty -and $imageProperty.Value) {
      $image = [string]$imageProperty.Value
    } else {
      Assert-Inventory ($null -ne $definition.PSObject.Properties['build']) 'no image or build'
      # Exact runner -p value determines the Compose implicit build tag.
      $image = $project + '-' + $service + ':latest'
    }
    $expected = switch ($service) {
      'neo4j' { 'dg-hosted-1309-sandbox-neo4j:latest' }
      'data-service' { 'dg-hosted-1309-sandbox-data-service:latest' }
      'n8n' { 'n8nio/n8n:2.4.8' }
    }
    Assert-Inventory ($image -ceq $expected) 'unexpected image name'
    $report.requestedImages[$service] = $image
  }
  if ($PreflightOnly) {
    $report.status = 'PREFLIGHT_ONLY'
  } else {
    $stage = 'host-guard'
    Assert-TargetHost
    $stage = 'image-observation'
    $report.observedAtUtc = [DateTime]::UtcNow.ToString('o')
    $unresolved = $false
    foreach ($service in @('neo4j','data-service','n8n')) {
      $image = $report.requestedImages[$service]
      try {
        $inspection = Invoke-FixedImageInspect $image
        $report.dockerInvoked = $true
        Assert-Inventory ($inspection.code -eq 0) 'inspect unavailable'
        $observation = Convert-ImageObservation $service $image $inspection.text
      } catch {
        # Absence, daemon errors and malformed data are indistinguishable here.
        $observation = [ordered]@{
          service=$service; image=$image; status='UNRESOLVED_INSPECTION'
          localConfigImageId=$null; registryRepoDigests=@(); os=$null; architecture=$null
        }
      }
      if ($observation.status -cne 'OBSERVED_NOW') { $unresolved = $true }
      $report.images += $observation
    }
    if ($unresolved) { $report.status = 'UNRESOLVED' }
    else { $report.status = 'OBSERVED_NOW' }
  }
} catch {
  # Never serialize exceptions, paths, native output, configuration or secrets.
  $report.status = 'BLOCKED'
  $report.failureStage = $stage
} finally {
  if ($null -ne $archive) { $archive.Dispose() }
  if ($null -ne $zipStream) { $zipStream.Dispose() }
  if ($null -ne $reportStream) {
    try {
      $bytes = [Text.UTF8Encoding]::new($false).GetBytes(($report | ConvertTo-Json -Depth 8))
      $reportStream.Write($bytes, 0, $bytes.Length)
      $reportStream.Flush()
    } catch { $report.status = 'BLOCKED' }
    finally { $reportStream.Dispose() }
  }
}
Write-Output ('Image inventory: ' + $report.status + '; stage=' + $report.failureStage)
if ($report.status -eq 'UNRESOLVED') { exit 2 }
if ($report.status -notin @('PREFLIGHT_ONLY','OBSERVED_NOW')) { exit 1 }
exit 0
