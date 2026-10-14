param(
  [Parameter(Mandatory=$true)][string]$PackageZip,
  [Parameter(Mandatory=$true)][string]$ExpectedZipSha256,
  [Parameter(Mandatory=$true)][string]$ReportPath
)
$ErrorActionPreference = 'Stop'
$project = 'dg-hosted-1309-sandbox'
$root = (Resolve-Path (Join-Path $PSScriptRoot '../../..')).Path
$compose = Join-Path $PSScriptRoot 'compose.yaml'
$report = [ordered]@{ schemaVersion=1; target='DESKTOP-OS4Q8CP'; status='BLOCKED'; failureStage=$null; frameworkRevision=$null; zipSha256=$null; checks=[ordered]@{}; cleanup='not-started' }
$stage = 'preflight'
$dockerTouched = $false
$deadline = $null
$previousEnv = @{}
$secretKeys = @('NEO4J_PASSWORD','LLM_MASTER_SECRET','DG_SERVICE_TOKEN','DG_BOOTSTRAP_ADMIN_PASSWORD','N8N_ENCRYPTION_KEY')

function Invoke-Bounded([string[]]$Arguments, [int]$Seconds) {
  if ($null -ne $deadline) {
    $remaining = [int][Math]::Floor(($deadline - [DateTime]::UtcNow).TotalSeconds)
    if ($remaining -le 0) { throw 'sandbox runtime deadline exceeded' }
    $Seconds = [Math]::Min($Seconds, $remaining)
  }
  $psi = [System.Diagnostics.ProcessStartInfo]::new()
  $psi.FileName = 'docker'
  # No secret is ever passed as a command argument. Quote native Windows paths.
  $psi.Arguments = (($Arguments | ForEach-Object { '"' + $_.Replace('"','\"') + '"' }) -join ' ')
  $psi.UseShellExecute = $false
  $psi.RedirectStandardOutput = $true
  $psi.RedirectStandardError = $true
  $psi.CreateNoWindow = $true
  $p = [System.Diagnostics.Process]::new()
  $p.StartInfo = $psi
  [void]$p.Start()
  $out = $p.StandardOutput.ReadToEndAsync()
  $err = $p.StandardError.ReadToEndAsync()
  if (-not $p.WaitForExit($Seconds * 1000)) {
    try { $p.Kill() } catch {}
    throw 'bounded Docker command timed out'
  }
  $text = $out.GetAwaiter().GetResult()
  $ignored = $err.GetAwaiter().GetResult() # never emit raw stderr; may contain env/credentials
  return @{ code=$p.ExitCode; text=$text }
}
function Assert-Ok($value, [string]$message) { if (-not $value) { throw $message } }
function Compose([string[]]$Arguments, [int]$Seconds) {
  return Invoke-Bounded (@('compose','-p',$project,'-f',$compose) + $Arguments) $Seconds
}
function Get-ServiceStates {
  # Inspect only fixed Docker state fields; never serialize CLI text or container logs.
  $states = [ordered]@{}
  foreach ($service in @('neo4j','data-service')) {
    $state = [ordered]@{ status='unknown'; exitCode=$null; oomKilled=$false }
    try {
      $found = Compose @('ps','--all','-q',$service) 15
      if ($found.code -eq 0 -and -not $found.text.Trim()) {
        $state.status = 'absent'
      } elseif ($found.code -eq 0 -and $found.text.Trim() -match '^[0-9a-fA-F]{12,64}$') {
        $inspection = Invoke-Bounded @('inspect','--format','{{json .State}}',$found.text.Trim()) 15
        if ($inspection.code -eq 0) {
          $raw = $inspection.text | ConvertFrom-Json
          if ($raw.Status -cin @('created','running','restarting','exited','paused','dead')) { $state.status = $raw.Status }
          if ($null -ne $raw.ExitCode -and [int]$raw.ExitCode -ge 0 -and [int]$raw.ExitCode -le 255) { $state.exitCode = [int]$raw.ExitCode }
          $state.oomKilled = ($raw.OOMKilled -eq $true)
        }
      }
    } catch {} # Diagnostics must not override the original stage or cleanup.
    $states[$service] = $state
  }
  return $states
}
function Get-StartupFailureSignature {
  # Only fixed labels from an allowlist enter the report; never pass through log text.
  $signature = [ordered]@{ phase='unknown'; errorClass='unknown' }
  try {
    $log = Compose @('logs','--no-color','--no-log-prefix','--tail','120','data-service') 15
    if ($log.code -ne 0) { return $signature }
    $text = $log.text
    if ($text.Length -gt 32768) { $text = $text.Substring($text.Length - 32768) }
    if ($text -match 'ensure_spec_indexes') { $signature.phase = 'neo4j-availability' }
    elseif ($text -match 'ensure_bootstrap_admin') { $signature.phase = 'bootstrap-admin' }
    elseif ($text -match 'enforce_startup_secrets') { $signature.phase = 'secret-policy' }
    elseif ($text -match 'self_registration_enabled|deployment_profile') { $signature.phase = 'deployment-profile' }
    if ($text -match '(?m)^(?:[\w.]+\.)?(ServiceUnavailable|AuthError|RuntimeError|ValueError|FileNotFoundError|PermissionError|ModuleNotFoundError|OSError|ClientError):') {
      $signature.errorClass = $Matches[1]
    }
  } catch {} # Diagnostics must not override cleanup or expose raw logs.
  return $signature
}
function Get-N8nOutputShape([string]$Text) {
  # Diagnostic vocabulary only. Never extract or accept a JSON fragment as proof.
  if ([string]::IsNullOrWhiteSpace($Text)) { return 'empty' }
  $value = $Text.Trim()
  if ($value.StartsWith('{') -or $value.StartsWith('[')) {
    if (-not ($value.EndsWith('}') -or $value.EndsWith(']')) -and $value.Contains('}')) { return 'text-after-json' }
    return 'json-like-malformed'
  }
  if ($value -match '(?m)^\s*[\{\[]') { return 'text-before-json' }
  return 'text-only'
}
function Get-N8nCliSignal([string]$Text) {
  # Match only n8n 2.4.8 CLI's fixed execution-failure banners.
  # Never report an error message, JSON body, path, or arbitrary stdout.
  if ($Text -cmatch '(?m)^Execution was NOT successful\. See log message for details\.$') {
    return 'execution-failed'
  }
  if ($Text -cmatch '(?m)^Error executing workflow\. See log messages for details\.$') {
    return 'execute-catch'
  }
  return 'none'
}
function Read-N8nExecutionJson([string]$Text) {
  # n8n 2.4.8 can print this fixed settings notice even with --rawOutput.
  # Permit exactly one known line, not arbitrary text before a JSON fragment.
  $notice = "User settings loaded from: /home/node/.n8n/config`n"
  if ($Text.StartsWith($notice, [StringComparison]::Ordinal)) {
    $Text = $Text.Substring($notice.Length)
  } else {
    $windowsNotice = $notice.Replace("`n", "`r`n")
    if ($Text.StartsWith($windowsNotice, [StringComparison]::Ordinal)) {
      $Text = $Text.Substring($windowsNotice.Length)
    }
  }
  $data = $Text | ConvertFrom-Json -ErrorAction Stop
  if ($null -eq $data -or $data -isnot [pscustomobject]) { throw 'n8n execution JSON object required' }
  return $data
}
function Assert-N8nNamedRead {
  try {
    $importGood = Compose @('run','--rm','--no-deps','n8n','import:workflow','--input=/files/workflows/sandbox-file-read.json') 120
  } catch {
    $report.checks.n8nDetail = 'import-command-error'
    throw 'n8n workflow import command failed'
  }
  if ($importGood.code -ne 0) {
    $report.checks.n8nDetail = 'import-nonzero'
    throw 'n8n workflow import failed'
  }
  try {
    $good = Compose @('run','--rm','--no-deps','n8n','execute','--id=dg1309FileRead','--rawOutput') 120
  } catch {
    $report.checks.n8nDetail = 'execute-command-error'
    throw 'n8n workflow execute command failed'
  }
  if ($good.code -ne 0) {
    $report.checks.n8nDetail = 'execute-nonzero'
    throw 'n8n workflow execute failed'
  }
  $goodData = $null
  try { $goodData = Read-N8nExecutionJson $good.text } catch {
    $report.checks.n8nDetail = 'output-not-json'
    $report.checks.n8nOutputShape = Get-N8nOutputShape $good.text
    $report.checks.n8nCliSignal = Get-N8nCliSignal $good.text
    throw 'n8n output not JSON'
  }
  try {
    $assertions = @($goodData.data.resultData.runData.'Assert named content')
    Assert-Ok ($assertions.Count -eq 1 -and
               $assertions[0].data.main[0][0].json.fileReadVerified -eq $true -and
               $assertions[0].data.main[0][0].json.workflowId -ceq 'dg1309FileRead' -and
               -not $goodData.data.resultData.error) 'n8n evidence mismatch'
  } catch {
    $report.checks.n8nDetail = 'unexpected-evidence'
    throw 'n8n file-reading execution failed'
  }
  $report.checks.n8nNamedRead = $true
}
function Assert-N8nDeniedRead {
  $importDenied = Compose @('run','--rm','--no-deps','n8n','import:workflow','--input=/files/workflows/sandbox-file-denied.json') 120
  Assert-Ok ($importDenied.code -eq 0) 'n8n denial workflow import failed'
  $denied = Compose @('run','--rm','--no-deps','n8n','execute','--id=dg1309DeniedRead','--rawOutput') 120
  $deniedData = $null
  try { $deniedData = Read-N8nExecutionJson $denied.text } catch {}
  Assert-Ok ($deniedData.data.resultData.error -and
             $deniedData.data.resultData.lastNodeExecuted -ceq 'Read outside named mount' -and
             -not $deniedData.data.resultData.runData.'Assert named content') 'n8n file denial not observed at read node'
  $report.checks.n8nDeniedRead = $true
}
function New-RandomSecret {
  $bytes = [byte[]]::new(48)
  $rng = [System.Security.Cryptography.RandomNumberGenerator]::Create()
  try { $rng.GetBytes($bytes) } finally { $rng.Dispose() }
  return [BitConverter]::ToString($bytes).Replace('-','').ToLowerInvariant()
}
try {
  # All preflight checks precede the FIRST docker compose command.
  Assert-Ok ([Environment]::MachineName.ToUpperInvariant() -ceq 'DESKTOP-OS4Q8CP') 'wrong host'
  Assert-Ok ($PSVersionTable.PSVersion.Major -ge 5) 'PowerShell unavailable'
  $zip = (Resolve-Path -LiteralPath $PackageZip).Path
  Assert-Ok (-not $zip.StartsWith($root + [IO.Path]::DirectorySeparatorChar, [StringComparison]::OrdinalIgnoreCase)) 'ZIP inside extraction'
  $reportFile = [IO.Path]::GetFullPath($ReportPath)
  Assert-Ok (-not $reportFile.StartsWith($root + [IO.Path]::DirectorySeparatorChar, [StringComparison]::OrdinalIgnoreCase)) 'report inside package'
  Assert-Ok (-not (Test-Path -LiteralPath $reportFile)) 'report already exists'
  Assert-Ok ($ExpectedZipSha256 -match '^[0-9a-fA-F]{64}$') 'invalid expected hash'
  $hash = (Get-FileHash -LiteralPath $zip -Algorithm SHA256).Hash.ToLowerInvariant()
  Assert-Ok ($hash -ceq $ExpectedZipSha256.ToLowerInvariant()) 'ZIP SHA-256 mismatch'
  $report.zipSha256 = $hash
  $manifestPath = Join-Path $root 'sandbox-manifest.json'
  $manifest = Get-Content -LiteralPath $manifestPath -Raw -Encoding UTF8 | ConvertFrom-Json
  Assert-Ok ((@($manifest.PSObject.Properties.Name | Sort-Object) -join ',') -ceq 'files,frameworkRevision,images,kind,schemaVersion') 'unexpected manifest fields'
  Assert-Ok ($manifest.kind -ceq 'synthetic-capability-sandbox-not-release') 'not a sandbox manifest'
  Assert-Ok ($manifest.schemaVersion -eq 1 -and $manifest.images -ceq 'unresolved-target-build-and-pull') 'unexpected manifest schema'
  Assert-Ok ($manifest.frameworkRevision -match '^[0-9a-f]{40}$') 'invalid revision'
  $report.frameworkRevision = $manifest.frameworkRevision
  $allowed = @{}
  foreach ($property in $manifest.files.PSObject.Properties) {
    $name = $property.Name
    Assert-Ok ($name -match '^[a-zA-Z0-9_./-]+$' -and -not $name.Contains('..') -and -not $name.StartsWith('/')) 'unsafe member'
    Assert-Ok ($property.Value -match '^[0-9a-f]{64}$') 'invalid file digest'
    $allowed[$name] = $property.Value
    $item = Get-Item -LiteralPath (Join-Path $root ($name -replace '/', [IO.Path]::DirectorySeparatorChar)) -Force
    Assert-Ok (-not ($item.Attributes -band [IO.FileAttributes]::ReparsePoint)) 'linked input'
    Assert-Ok ((Get-FileHash -LiteralPath $item.FullName -Algorithm SHA256).Hash.ToLowerInvariant() -ceq $property.Value) 'file hash mismatch'
  }
  $actual = @(Get-ChildItem -LiteralPath $root -Recurse -Force -File)
  Assert-Ok ($actual.Count -eq ($allowed.Count + 1)) 'extra or missing files'
  foreach ($item in $actual) {
    $relative = $item.FullName.Substring($root.Length + 1).Replace([IO.Path]::DirectorySeparatorChar, '/')
    Assert-Ok ($relative -ceq 'sandbox-manifest.json' -or $allowed.ContainsKey($relative)) 'unknown package input'
  }
  Assert-Ok (-not @(Get-ChildItem -LiteralPath $root -Recurse -Force -Attributes ReparsePoint).Count) 'linked directory'
  Add-Type -AssemblyName System.IO.Compression.FileSystem
  $archive = [IO.Compression.ZipFile]::OpenRead($zip)
  try {
    $zipNames = @($archive.Entries | ForEach-Object { $_.FullName })
    Assert-Ok ($zipNames.Count -eq ($allowed.Count + 1) -and @($zipNames | Select-Object -Unique).Count -eq $zipNames.Count) 'ZIP entry count mismatch'
    foreach ($name in $zipNames) { Assert-Ok ($name -ceq 'sandbox-manifest.json' -or $allowed.ContainsKey($name)) 'ZIP entry unexpected' }
    $entry = $archive.GetEntry('sandbox-manifest.json')
    Assert-Ok ($null -ne $entry) 'ZIP manifest missing'
    $reader = [IO.StreamReader]::new($entry.Open())
    try { $zipManifest = $reader.ReadToEnd() } finally { $reader.Dispose() }
    Assert-Ok ($zipManifest -ceq (Get-Content -LiteralPath $manifestPath -Raw -Encoding UTF8)) 'ZIP manifest differs from extraction'
  } finally { $archive.Dispose() }
  $report.checks.packageHash = $true
  $stage = 'disk-and-docker-preflight'
  $drive = Get-PSDrive -Name ([IO.Path]::GetPathRoot($root).Substring(0,1))
  Assert-Ok ($drive.Free -ge 12GB) 'insufficient disk'
  $report.checks.diskPreflight = $true
  foreach ($port in @(8000,5678,7474,7687)) {
    Assert-Ok (-not @(Get-NetTCPConnection -LocalPort $port -State Listen -ErrorAction SilentlyContinue).Count) 'port occupied'
  }
  Assert-Ok (-not @(Get-Content -LiteralPath $compose | Select-String '^\s+ports:|network_mode:\s*host|privileged:\s*true')) 'network or mount policy anomaly'
  $version = Invoke-Bounded @('compose','version','--short') 15
  Assert-Ok ($version.code -eq 0 -and $version.text.Trim() -match '^v?(\d+)\.(\d+)\.(\d+)') 'Compose version unavailable'
  $major = [int]$Matches[1]; $minor = [int]$Matches[2]; $patch = [int]$Matches[3]
  Assert-Ok ($major -gt 2 -or ($major -eq 2 -and ($minor -gt 24 -or ($minor -eq 24 -and $patch -ge 4)))) 'Compose below 2.24.4'
  $report.checks.composeVersion = $true
  $existing = Invoke-Bounded @('ps','-a','--filter',"label=com.docker.compose.project=$project",'--format','{{.ID}}') 15
  Assert-Ok ($existing.code -eq 0 -and -not $existing.text.Trim()) 'named project already has containers'
  $existingNetwork = Invoke-Bounded @('network','ls','--filter',"label=com.docker.compose.project=$project",'--format','{{.Name}}') 15
  Assert-Ok ($existingNetwork.code -eq 0 -and -not $existingNetwork.text.Trim()) 'named project already has network'
  $existingVolume = Invoke-Bounded @('volume','ls','--filter',"label=com.docker.compose.project=$project",'--format','{{.Name}}') 15
  Assert-Ok ($existingVolume.code -eq 0 -and -not $existingVolume.text.Trim()) 'named project already has volumes'
  $report.checks.projectVacant = $true
  $deadline = [DateTime]::UtcNow.AddMinutes(35)
  foreach ($key in $secretKeys) {
    $previousEnv[$key] = [Environment]::GetEnvironmentVariable($key, 'Process')
    [Environment]::SetEnvironmentVariable($key, (New-RandomSecret), 'Process')
  }
  # The temporary secrets live only in this owner-run process/container metadata.
  $dockerTouched = $true
  $stage = 'compose-config'
  $config = Compose @('config','--format','json') 30
  Assert-Ok ($config.code -eq 0) 'Compose config rejected'
  $model = $config.text | ConvertFrom-Json
  Assert-Ok ((($model.services.PSObject.Properties.Name | Sort-Object) -join ',') -ceq 'data-service,n8n,neo4j') 'unexpected services'
  foreach ($service in $model.services.PSObject.Properties) {
    Assert-Ok (-not $service.Value.ports -and -not $service.Value.privileged -and -not $service.Value.network_mode) 'unexpected port or privilege'
    Assert-Ok ($service.Value.mem_limit -and $service.Value.cpus -and $service.Value.pids_limit) 'resource limit missing'
    foreach ($volume in $service.Value.volumes) {
      if ($volume.type -eq 'bind') { Assert-Ok ($volume.read_only -and $volume.source.StartsWith($root, [StringComparison]::OrdinalIgnoreCase)) 'unsafe bind' }
    }
  }
  $report.checks.composeIsolation = $true
  $started = [DateTime]::UtcNow
  $stage = 'image-pull'
  $pull = Compose @('pull','--quiet','neo4j','n8n') 1200
  Assert-Ok ($pull.code -eq 0) 'image pull failed'
  $stage = 'data-service-build'
  $built = Compose @('build','--quiet','data-service') 1200
  Assert-Ok ($built.code -eq 0) 'data-service build failed'
  $stage = 'service-start'
  # First wait for an authenticated Neo4j query; "running" is not ready for
  # ensure_spec_indexes() and the app does not retry its startup transaction.
  $neoUp = Compose @('up','-d','--no-build','--wait','--wait-timeout','180','neo4j') 210
  if ($neoUp.code -ne 0) {
    $report.checks.startDetail = 'neo4j-not-ready'
    $report.checks.startState = Get-ServiceStates
    throw 'sandbox Neo4j not ready'
  }
  $up = Compose @('up','-d','--no-build','data-service') 90
  if ($up.code -ne 0) {
    $report.checks.startDetail = 'compose-up-nonzero'
    $report.checks.startState = Get-ServiceStates
    throw 'sandbox start failed'
  }
  $ready = $false
  for ($i=0; $i -lt 24; $i++) {
    $check = Compose @('exec','-T','data-service','python','-c','import urllib.request; urllib.request.urlopen("http://127.0.0.1:8000/auth/options",timeout=3)') 10
    if ($check.code -eq 0) { $ready = $true; break }
    Start-Sleep -Seconds 5
  }
  if (-not $ready) {
    $report.checks.startDetail = 'readiness-timeout'
    $report.checks.startState = Get-ServiceStates
    if ($report.checks.startState.'data-service'.status -ceq 'exited') {
      $report.checks.startSignature = Get-StartupFailureSignature
    }
    throw 'data-service not ready'
  }
  $stage = 'data-service-ingest'
  $probe = Compose @('exec','-T','data-service','python','/app/sandbox_probe.py') 120
  Assert-Ok ($probe.code -eq 0) 'data-service probe failed'
  $evidence = $probe.text.Trim() | ConvertFrom-Json
  Assert-Ok ($evidence.ingest_inserted -eq 1 -and $evidence.neo4j_scoped_notes -eq 1 -and $evidence.denied_paths -eq 4 -and $evidence.csrf_denied -eq $true) 'data-service evidence anomaly'
  $report.checks.dataService = $evidence
  $stage = 'n8n-named-file-read'
  Assert-N8nNamedRead
  $stage = 'n8n-denied-file-read'
  Assert-N8nDeniedRead
  Assert-Ok (([DateTime]::UtcNow - $started).TotalMinutes -le 35) 'overall runtime exceeded 35 minutes'
  $report.status = 'PASS'
} catch {
  # Never serialize exception details: tools and service errors may contain secrets.
  $report.status = 'FAIL'
  $report.failureStage = $stage
} finally {
  if ($dockerTouched) {
    try {
      $deadline = $null # cleanup must run even after the operational deadline
      $down = Compose @('down','-v','--remove-orphans','--timeout','20') 90
      $report.cleanup = if ($down.code -eq 0) { 'project-down-volumes-removed' } else { 'FAILED' }
    } catch { $report.cleanup = 'FAILED' }
  }
  foreach ($key in $secretKeys) { [Environment]::SetEnvironmentVariable($key, $previousEnv[$key], 'Process') }
  if ($report.cleanup -eq 'FAILED') { $report.status = 'FAIL'; $report.failureStage = 'cleanup' }
  try {
    $parent = Split-Path -Parent $reportFile
    Assert-Ok (Test-Path -LiteralPath $parent -PathType Container) 'report parent missing'
    $report | ConvertTo-Json -Depth 8 | Set-Content -LiteralPath $reportFile -Encoding UTF8 -NoNewline
  } catch { $report.status = 'FAIL' }
}
if ($report.status -ne 'PASS') { exit 1 }
