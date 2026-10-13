# Isolated Windows 11 Caddy fixture. No Docker, repo, Python, DNS or internet needed.
# The bundled private keys are disposable test data; never deploy these certificates.
param()
$ErrorActionPreference = 'Stop'
$root = Split-Path -Parent $MyInvocation.MyCommand.Path
$deadline = (Get-Date).AddMinutes(15)
$checks = New-Object System.Collections.ArrayList
$jobs = New-Object System.Collections.ArrayList
$caddy = $null
$work = Join-Path $root 'work'
$report = Join-Path $root 'edge-report.json'
$stage = 'preflight'
$expected = @{
    'caddy.exe' = 'CADDY_SHA256_REPLACE'
    'Caddyfile.source' = 'SOURCE_SHA256_REPLACE'
}
$names = @('dg', 'speckle', 'object')
function Assert-Time { if ((Get-Date) -ge $deadline) { throw 'time limit reached' } }
function Assert-Result([string]$name, [bool]$ok) {
    [void]$checks.Add([ordered]@{ name = $name; pass = $ok })
    if (-not $ok) { throw ('check failed: ' + $name) }
}
function Hash-File([string]$name) {
    return (Get-FileHash -Algorithm SHA256 -LiteralPath (Join-Path $root $name)).Hash.ToLowerInvariant()
}
function Invoke-CheckedProcess([string]$executable, [string[]]$arguments, [string]$stdout, [string]$stderr) {
    # PowerShell 5.1 may return $null ExitCode for Start-Process -PassThru
    # with RedirectStandardOutput/RedirectStandardError even after WaitForExit.
    # Native invocation preserves $LASTEXITCODE; keep stdout/stderr in fixture files.
    $global:LASTEXITCODE = $null
    $previousErrorAction = $ErrorActionPreference
    try {
        # PS 5.1 promotes native stderr to NativeCommandError under Stop.
        # Preserve stderr for diagnostics and judge success only by process exit.
        $ErrorActionPreference = 'Continue'
        & $executable @arguments 1> $stdout 2> $stderr
    } finally {
        $ErrorActionPreference = $previousErrorAction
    }
    if ($null -eq $LASTEXITCODE) { throw 'native process produced no exit code' }
    return [int]$LASTEXITCODE
}
function Request([string]$hostName, [string]$method, [string]$path, [string]$extra) {
    Assert-Time
    $tcp = New-Object System.Net.Sockets.TcpClient
    try {
        $ar = $tcp.BeginConnect('127.0.0.1', 18443, $null, $null)
        if (-not $ar.AsyncWaitHandle.WaitOne(3000)) { throw 'edge connect timeout' }
        $tcp.EndConnect($ar)
        $tcp.ReceiveTimeout = 4000; $tcp.SendTimeout = 4000
        $tls = [System.Net.Security.SslStream]::new($tcp.GetStream(), $false, [System.Net.Security.RemoteCertificateValidationCallback]{ param($sender,$cert,$chain,$errors) return $true })
        try {
            # SNI uses the synthetic hostname; TCP never performs DNS lookup.
            $tls.AuthenticateAsClient($hostName)
            $payload = ''
            if ($method -eq 'PUT') { $payload = 'synthetic-object' }
            $wire = "$method $path HTTP/1.1`r`nHost: $hostName`r`nConnection: close`r`nX-Forwarded-For: 203.0.113.44`r`n$extra"
            if ($method -eq 'PUT') { $wire += "Content-Length: $($payload.Length)`r`n" }
            $wire += "`r`n$payload"
            $bytes = [System.Text.Encoding]::ASCII.GetBytes($wire)
            $tls.Write($bytes, 0, $bytes.Length); $tls.Flush()
            $stream = New-Object System.IO.MemoryStream
            $buffer = New-Object byte[] 4096
            do { $count = $tls.Read($buffer, 0, $buffer.Length); if ($count -gt 0) { $stream.Write($buffer, 0, $count) } } while ($count -gt 0 -and $stream.Length -lt 32768 -and (Get-Date) -lt $deadline)
            if ($stream.Length -ge 32768) { throw 'response too large' }
            $text = [System.Text.Encoding]::UTF8.GetString($stream.ToArray())
            if ($text -notmatch '^HTTP/1\.[01] (\d{3})') { throw 'invalid HTTPS response' }
            return @{ status = [int]$Matches[1]; text = $text }
        } finally { $tls.Dispose() }
    } finally { $tcp.Close() }
}
$server = {
    param([int]$port, [string]$service)
    $listener = [System.Net.Sockets.TcpListener]::new([System.Net.IPAddress]::Loopback, $port)
    $listener.Start()
    try {
        while ($true) {
            if (-not $listener.Pending()) { Start-Sleep -Milliseconds 50; continue }
            $client = $listener.AcceptTcpClient()
            try {
                $client.ReceiveTimeout = 3500; $client.SendTimeout = 3500
                $stream = $client.GetStream()
                $reader = [System.IO.StreamReader]::new($stream, [System.Text.Encoding]::ASCII, $false, 1024, $true)
                $line = $reader.ReadLine()
                if (-not $line) { continue }
                $hostHeader = ''; $forwarded = ''; $length = 0
                while ($true) {
                    $header = $reader.ReadLine()
                    if ($null -eq $header -or $header -eq '') { break }
                    if ($header -match '^Host:\s*(.*)$') { $hostHeader = $Matches[1] }
                    if ($header -match '^X-Forwarded-For:\s*(.*)$') { $forwarded = $Matches[1] }
                    if ($header -match '^Content-Length:\s*(\d+)$') { $length = [int]$Matches[1] }
                }
                if ($length -gt 1024) { continue }
                $body = ''
                for ($i = 0; $i -lt $length; $i++) { $body += [char]$reader.Read() }
                $reply = [ordered]@{ service=$service; request=$line; host=$hostHeader; forwarded=$forwarded; body=$body } | ConvertTo-Json -Compress
                $data = [System.Text.Encoding]::UTF8.GetBytes($reply)
                $response = [System.Text.Encoding]::ASCII.GetBytes("HTTP/1.1 200 OK`r`nContent-Type: application/json`r`nContent-Length: $($data.Length)`r`nConnection: close`r`n`r`n")
                $stream.Write($response, 0, $response.Length); $stream.Write($data, 0, $data.Length); $stream.Flush()
            } catch { } finally { $client.Close() }
        }
    } finally { $listener.Stop() }
}
try {
    Assert-Result 'named-machine' ($env:COMPUTERNAME -eq 'DESKTOP-OS4Q8CP')
    Assert-Result 'windows-powershell-5-or-newer' ($PSVersionTable.PSVersion.Major -ge 5)
    foreach ($entry in $expected.GetEnumerator()) { Assert-Result ('integrity-' + $entry.Key) ((Hash-File $entry.Key) -eq $entry.Value) }
    foreach ($name in $names) {
        $cert = Join-Path $root ('certs\' + $name + '.crt')
        $key = Join-Path $root ('certs\' + $name + '.key')
        Assert-Result ('cert-' + $name) ((Test-Path -LiteralPath $cert) -and (Test-Path -LiteralPath $key))
        $parsed = New-Object System.Security.Cryptography.X509Certificates.X509Certificate2 -ArgumentList $cert
        Assert-Result ('cert-current-' + $name) ((Get-Date) -ge $parsed.NotBefore -and (Get-Date) -lt $parsed.NotAfter)
    }
    $stage = 'rewrite'
    $source = [System.IO.File]::ReadAllText((Join-Path $root 'Caddyfile.source'))
    # Exact, counted transformations: no alternate policy or accidental partial replacement.
    $replacements = [ordered]@{
        'design-grammars:80'='127.0.0.1:18501'; 'speckle-ingress:8080'='127.0.0.1:18502'; 'speckle-minio:9000'='127.0.0.1:18503';
        '/etc/caddy/certs/'=(([System.IO.Path]::GetFullPath((Join-Path $root 'certs')) -replace '\\','/') + '/');
        '{$HOSTED_DG_HOST}'='https://dg.example.invalid:18443'; '{$HOSTED_SPECKLE_HOST}'='https://speckle.example.invalid:18443'; '{$HOSTED_OBJECT_HOST}'='https://objects.example.invalid:18443';
        ':443 {'=':18443 {'
    }
    foreach ($entry in $replacements.GetEnumerator()) {
        $hits = [regex]::Matches($source, [regex]::Escape([string]$entry.Key)).Count
        $requiredHits = if ([string]$entry.Key -eq '/etc/caddy/certs/') { 8 } else { 1 }
        Assert-Result ('source-directive-' + $entry.Key) ($hits -eq $requiredHits)
        $source = $source.Replace([string]$entry.Key, [string]$entry.Value)
    }
    # Quote paths after adaptation: ZIP may be extracted under a directory with spaces.
    $certPrefix = [regex]::Escape(([System.IO.Path]::GetFullPath((Join-Path $root 'certs')) -replace '\\','/') + '/')
    $source = [regex]::Replace($source, $certPrefix + '(?:dg|speckle|object)\.(?:crt|key)', { param($match) '"' + $match.Value + '"' })
    Assert-Result 'eight-quoted-test-cert-paths' ([regex]::Matches($source, 'tls "[^"\r\n]+" "[^"\r\n]+"').Count -eq 4)
    # All sites, including fallback, bind only loopback. Explicit certs; disable auto redirects/admin.
    $source = "{`n admin off`n auto_https off`n}`n" + ($source -replace '(?m)^([\t ]*)(tls )', ('${1}bind 127.0.0.1' + "`n" + '${1}${2}'))
    $tls = @($source -split "`n" | Where-Object { $_ -match '^\s*tls "' })
    Assert-Result 'four-loopback-binds' ([regex]::Matches($source, 'bind 127\.0\.0\.1').Count -eq 4 -and $tls.Count -eq 4)
    # Explicit origins only; the fallback site still has its own cert and loopback binding.
    if (Test-Path $work) { throw 'work directory already exists; remove after reviewing previous run' }
    [void](New-Item -ItemType Directory -Path $work)
    $config = Join-Path $work 'Caddyfile'
    [System.IO.File]::WriteAllText($config, $source, (New-Object System.Text.UTF8Encoding($false)))
    # Validation is real Caddy; native invocation preserves the exit code on PS 5.1.
    $stage = 'validate'
    $validateCode = Invoke-CheckedProcess (Join-Path $root 'caddy.exe') @('validate','--config',$config,'--adapter','caddyfile') (Join-Path $work 'validate.out') (Join-Path $work 'validate.err')
    Assert-Result 'caddy-validate' ($validateCode -eq 0)
    $stage = 'ports'
    foreach ($port in @(18443,18501,18502,18503)) {
        $probe = [System.Net.Sockets.TcpListener]::new([System.Net.IPAddress]::Loopback, $port)
        try { $probe.Start() } finally { $probe.Stop() }
    }
    $stage = 'upstreams'
    foreach ($item in @(@(18501,'dg'),@(18502,'speckle'),@(18503,'object'))) {
        $job = Start-Job -ScriptBlock $server -ArgumentList $item[0],$item[1]
        [void]$jobs.Add($job)
    }
    $stage = 'proxy'
    $caddy = Start-Process -FilePath (Join-Path $root 'caddy.exe') -ArgumentList @('run','--config',('"'+$config+'"'),'--adapter','caddyfile') -PassThru -WindowStyle Hidden -RedirectStandardOutput (Join-Path $work 'caddy.out') -RedirectStandardError (Join-Path $work 'caddy.err')
    $ready = $false
    for ($attempt=0; $attempt -lt 40; $attempt++) {
        Assert-Time
        if ($caddy.HasExited) { break }
        try { $probe = Request 'dg.example.invalid' 'GET' '/' ''; if ($probe.status -eq 200) { $ready = $true; break } } catch { Start-Sleep -Milliseconds 150 }
    }
    Assert-Result 'caddy-started-and-routed' $ready
    $stage = 'routes'
    $dg = Request 'dg.example.invalid' 'GET' '/data-service/graph/P' ''
    $dgBody = $dg.text.Substring($dg.text.IndexOf("`r`n`r`n") + 4) | ConvertFrom-Json
    Assert-Result 'dg-allow-and-spoof-reset' ($dg.status -eq 200 -and $dgBody.service -eq 'dg' -and $dgBody.forwarded -eq '127.0.0.1')
    $sp = Request 'speckle.example.invalid' 'GET' '/api/projects' ''
    $spBody = $sp.text.Substring($sp.text.IndexOf("`r`n`r`n") + 4) | ConvertFrom-Json
    Assert-Result 'speckle-allow' ($sp.status -eq 200 -and $spBody.service -eq 'speckle')
    $obj = Request 'objects.example.invalid' 'PUT' '/speckle-server/file?a=1&X-Amz-Signature=synthetic' ''
    $objBody = $obj.text.Substring($obj.text.IndexOf("`r`n`r`n") + 4) | ConvertFrom-Json
    Assert-Result 'object-put-path-query-host-body' ($obj.status -eq 200 -and $objBody.service -eq 'object' -and $objBody.request -eq 'PUT /speckle-server/file?a=1&X-Amz-Signature=synthetic HTTP/1.1' -and $objBody.host -eq 'objects.example.invalid' -and $objBody.body -eq 'synthetic-object')
    $get = Request 'objects.example.invalid' 'GET' '/speckle-server/file?a=1&X-Amz-Signature=synthetic' ''
    $getBody = $get.text.Substring($get.text.IndexOf("`r`n`r`n") + 4) | ConvertFrom-Json
    Assert-Result 'object-get-query' ($get.status -eq 200 -and $getBody.request -eq 'GET /speckle-server/file?a=1&X-Amz-Signature=synthetic HTTP/1.1')
    foreach ($item in @(@('dg.example.invalid','/neo4j/'),@('dg.example.invalid','/unlisted'),@('speckle.example.invalid','/admin/'),@('objects.example.invalid','/other/file'),@('unknown.example.invalid','/'))) {
        $response = Request $item[0] 'GET' $item[1] ''
        Assert-Result ('deny-' + $item[0] + $item[1]) ($response.status -eq 404 -and -not $response.text.Contains('"service":'))
    }
    Assert-Result 'object-post-denied' ((Request 'objects.example.invalid' 'POST' '/speckle-server/file' '').status -eq 404)
} catch {
    # Deliberately do not return exception text, config, headers or arbitrary upstream responses.
    [void]$checks.Add([ordered]@{ name='runner-error'; pass=$false; code='preflight-or-runtime-failure'; stage=$stage })
} finally {
    if ($null -ne $caddy) { try { if (-not $caddy.HasExited) { $caddy.Kill(); $caddy.WaitForExit(5000) | Out-Null } } catch { } }
    foreach ($job in $jobs) { try { Stop-Job -Job $job -ErrorAction SilentlyContinue; Remove-Job -Job $job -Force -ErrorAction SilentlyContinue } catch { } }
    # Only processes launched above are stopped; cleanup failures fail the report.
    if ($null -ne $caddy -and -not $caddy.HasExited) { [void]$checks.Add([ordered]@{ name='cleanup-caddy'; pass=$false }) }
    $passes = @($checks | Where-Object { $_.pass }).Count
    $failed = @($checks | Where-Object { -not $_.pass }).Count
    $result = [ordered]@{ schema='dg-edge-synthetic-v1'; machine=$env:COMPUTERNAME; startedByOwner=$true; finishedUtc=(Get-Date).ToUniversalTime().ToString('o'); total=$checks.Count; passed=$passes; failed=$failed; blackBoxComplete=($failed -eq 0 -and $checks.Count -ge 29); checks=@($checks); limitations='Synthetic Caddy+loopback only; no real Speckle/MinIO, S3 signature/CORS/import proof or public deployment.' }
    $result | ConvertTo-Json -Depth 5 | Set-Content -LiteralPath $report -Encoding UTF8
    Write-Host ('Report: ' + $report + ' (passed=' + $passes + ', failed=' + $failed + ')')
    if (-not $result.blackBoxComplete) { exit 1 }
}
