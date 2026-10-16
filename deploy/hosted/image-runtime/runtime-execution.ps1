#requires -Version 5.1
# Function-only module. Dot-source ONLY after package and archive validation.
function Get-IsolatedDockerArguments($Context, [string[]]$Command) {
    return @('--host', 'npipe:////./pipe/docker_engine', '--config', $Context.Config) + $Command
}
function Get-IsolatedComposeArguments($Context, [string[]]$Command) {
    return Get-IsolatedDockerArguments $Context (@('compose', '--env-file', (Join-Path $Context.Root 'support/empty-env.txt'),
        '--project-directory', $Context.Root, '--file', (Join-Path $Context.Root 'compose.json'), '--project-name', $Context.Project) + $Command)
}
function Assert-IsolatedFields($Object, [string[]]$Allowed, [switch]$Exact) {
    Assert-True ($Object -is [pscustomobject])
    $names = @($Object.PSObject.Properties | ForEach-Object {$_.Name})
    foreach ($name in $names) { Assert-True ($name -cin $Allowed) }
    if ($Exact) { Assert-True ($names.Count -eq $Allowed.Count) }
}
function Get-IsolatedValue($Object, [string]$Name) {
    $property = $Object.PSObject.Properties[$Name]
    if ($null -ne $property) { return $property.Value }
    return $null
}
function Assert-IsolatedDaemon([string]$VersionJson, [string]$InfoJson, [string]$ComposeVersion) {
    $version = $VersionJson | ConvertFrom-Json
    $info = $InfoJson | ConvertFrom-Json
    Assert-True ($version.Server.Os -ceq 'linux' -and $version.Server.Arch -ceq 'amd64')
    Assert-True ($info.OSType -ceq 'linux' -and $info.Architecture -cin @('amd64','x86_64') -and [long]$info.MemTotal -ge 6GB)
    Assert-True ($ComposeVersion.Trim() -cmatch '^v?([0-9]+)\.([0-9]+)\.([0-9]+)$')
    $v = [version]($Matches[1] + '.' + $Matches[2] + '.' + $Matches[3])
    Assert-True ($v -ge [version]'2.24.4')
}
function Confirm-IsolatedImage($Image, [string]$Id, [string]$Revision) {
    Assert-IsolatedFields $Image @('Id','Os','Architecture','Revision') -Exact
    Assert-True ($Id -cmatch '^sha256:[0-9a-f]{64}$' -and $Revision -cmatch '^[0-9a-f]{40}$')
    Assert-True ($Image.Id -ceq $Id -and $Image.Os -ceq 'linux' -and $Image.Architecture -ceq 'amd64' -and $Image.Revision -ceq $Revision)
}
function Confirm-IsolatedSmokeEvidence($Evidence) {
    Assert-IsolatedFields $Evidence @('api','uiAssets','uiHeaders','uiProxyTombstones','uiRuntimeConfig','reasonerNeo4jUp','selfRegistrationDisabled') -Exact
    Assert-IsolatedFields $Evidence.api @('admin_login','csrf_denied','ingest_inserted','neo4j_scoped_notes','denied_paths') -Exact
    foreach ($key in @('admin_login','csrf_denied')) {
        $value = $Evidence.api.PSObject.Properties[$key].Value
        Assert-True ($value -is [bool] -and $value)
    }
    foreach ($key in @('ingest_inserted','neo4j_scoped_notes','denied_paths')) {
        $value = $Evidence.api.PSObject.Properties[$key].Value
        $expected = if ($key -ceq 'denied_paths') {4} else {1}
        Assert-True (($value -is [int] -or $value -is [long]) -and $value -eq $expected)
    }
    foreach ($key in @('uiHeaders','uiProxyTombstones','uiRuntimeConfig','reasonerNeo4jUp','selfRegistrationDisabled')) {
        $value = $Evidence.PSObject.Properties[$key].Value
        Assert-True ($value -is [bool] -and $value)
    }
    Assert-True (($Evidence.uiAssets -is [int] -or $Evidence.uiAssets -is [long]) -and $Evidence.uiAssets -ge 1 -and $Evidence.uiAssets -le 20)
    # Reconstruct; never pass through arbitrary probe keys or values.
    return [ordered]@{api=[ordered]@{admin_login=$true;csrf_denied=$true;ingest_inserted=1;neo4j_scoped_notes=1;denied_paths=4};
        uiAssets=[int]$Evidence.uiAssets;uiHeaders=$true;uiProxyTombstones=$true;uiRuntimeConfig=$true;reasonerNeo4jUp=$true;selfRegistrationDisabled=$true}
}
function ConvertTo-IsolatedArgument([string]$Value) {
    return '"' + [regex]::Replace([regex]::Replace($Value, '(\\*)"', '$1$1\"'), '(\\+)$', '$1$1') + '"'
}
function Stop-IsolatedProcess([Diagnostics.Process]$Process) {
    # Also call after an inherited-pipe drain failure; descendants may outlive CLI.
    $psi = New-Object Diagnostics.ProcessStartInfo
    $psi.FileName = Join-Path $env:SystemRoot 'System32/taskkill.exe'
    $psi.Arguments = '/PID ' + $Process.Id + ' /T /F'
    $psi.UseShellExecute=$false; $psi.CreateNoWindow=$true
    $psi.RedirectStandardOutput=$true; $psi.RedirectStandardError=$true
    $killer = [Diagnostics.Process]::Start($psi)
    try {
        $out = $killer.StandardOutput.BaseStream.CopyToAsync([IO.Stream]::Null)
        $err = $killer.StandardError.BaseStream.CopyToAsync([IO.Stream]::Null)
        if (-not $killer.WaitForExit(10000)) { $killer.Kill(); [void]$killer.WaitForExit(2000); throw 'termination failed' }
        $exited=$Process.WaitForExit(10000)
        Assert-True ($killer.ExitCode -eq 0 -and $exited)
        Assert-True ($out.Wait(1000) -and $err.Wait(1000))
    } finally { $killer.Dispose() }
}
function Initialize-IsolatedCapture {
    if ('DgRuntimeBoundedStream' -as [type]) { return }
    # CopyToAsync drains without unbounded ReadToEnd buffers or PS callbacks.
    Add-Type -TypeDefinition @'
using System;
using System.IO;
public sealed class DgRuntimeBoundedStream : Stream {
    readonly MemoryStream data = new MemoryStream();
    readonly int cap;
    public bool Overflow { get; private set; }
    public DgRuntimeBoundedStream(int limit) { cap = limit; }
    public string Text() { lock(data) { return System.Text.Encoding.UTF8.GetString(data.ToArray()); } }
    public override void Write(byte[] b,int o,int n) {
        lock(data) { if(cap == 0) return; int keep = Math.Min(n, cap-(int)data.Length);
            if(keep>0) data.Write(b,o,keep); if(keep<n) Overflow=true; }
    }
    public override bool CanRead { get { return false; } }
    public override bool CanSeek { get { return false; } }
    public override bool CanWrite { get { return true; } }
    public override long Length { get { return data.Length; } }
    public override long Position { get { return data.Position; } set { throw new NotSupportedException(); } }
    public override void Flush() {}
    public override int Read(byte[] b,int o,int n) { throw new NotSupportedException(); }
    public override long Seek(long o,SeekOrigin s) { throw new NotSupportedException(); }
    public override void SetLength(long n) { throw new NotSupportedException(); }
    protected override void Dispose(bool disposing) { if(disposing) data.Dispose(); base.Dispose(disposing); }
}
'@
}
function Invoke-IsolatedProcess([string]$Executable, [string[]]$Arguments, [string]$Root,
    [Collections.IDictionary]$Environment, [int]$Seconds, [datetime]$Deadline, [int]$CaptureLimit=0) {
    $process=$null; $buffer=$null; $started=$false
    try {
        Initialize-IsolatedCapture
        $remaining = ($Deadline - [datetime]::UtcNow).TotalSeconds
        # Reserve termination + pipe-drain time within the caller's deadline.
        Assert-True ($remaining -gt 25 -and $Seconds -gt 0 -and $CaptureLimit -ge 0 -and $CaptureLimit -le 1048576)
        $wait = [int]([math]::Min($Seconds, $remaining-25)*1000)
        $psi = New-Object Diagnostics.ProcessStartInfo
        $psi.FileName=$Executable; $psi.WorkingDirectory=$Root
        $psi.Arguments=(@($Arguments | ForEach-Object {ConvertTo-IsolatedArgument $_}) -join ' ')
        $psi.UseShellExecute=$false; $psi.CreateNoWindow=$true
        $psi.RedirectStandardOutput=$true; $psi.RedirectStandardError=$true
        foreach ($key in @($psi.EnvironmentVariables.Keys)) {
            if ($key -match '^(?i:DOCKER_|COMPOSE_|BUILDKIT_|BUILDX_)') { $psi.EnvironmentVariables.Remove($key) }
        }
        foreach ($key in $Environment.Keys) { $psi.EnvironmentVariables[$key]=[string]$Environment[$key] }
        $process=New-Object Diagnostics.Process; $process.StartInfo=$psi
        $buffer=New-Object DgRuntimeBoundedStream($CaptureLimit)
        [void]$process.Start(); $started=$true
        $out=$process.StandardOutput.BaseStream.CopyToAsync($buffer)
        $err=$process.StandardError.BaseStream.CopyToAsync([IO.Stream]::Null)
        if (-not $process.WaitForExit($wait)) { Stop-IsolatedProcess $process; throw 'command timeout' }
        if (-not $out.Wait(1000) -or -not $err.Wait(1000)) { Stop-IsolatedProcess $process; throw 'drain timeout' }
        Assert-True (-not $buffer.Overflow -and [datetime]::UtcNow -lt $Deadline)
        return @{Code=$process.ExitCode;Text=$buffer.Text().Trim()}
    } catch {
        if ($started -and -not $process.HasExited) { Stop-IsolatedProcess $process }
        throw 'bounded runtime command failed'
    } finally {
        if ($null -ne $process) { $process.Dispose() }
        if ($null -ne $buffer) { $buffer.Dispose() }
    }
}
function Assert-IsolatedMemory([string]$Value, [int]$MaxMiB) {
    Assert-True ($Value -cmatch '^([1-9][0-9]*)([mMgG]?)$')
    $bytes=[decimal]$Matches[1]
    if($Matches[2] -match '^[mM]$'){$bytes*=1MB}
    elseif($Matches[2] -match '^[gG]$'){$bytes*=1GB}
    Assert-True ($bytes -gt 0 -and $bytes -le ([decimal]$MaxMiB*1MB))
}
function Assert-IsolatedComposeModel($Model, $Job, [string]$Root, [string]$Project) {
    Assert-True ($Project -cmatch '^dg-image-[0-9a-f]{32}$')
    Assert-IsolatedFields $Model @('name','services','networks','volumes') -Exact
    Assert-True ($Model.name -ceq $Project)
    Assert-IsolatedFields $Model.services @('neo4j','dg-reasoner','data-service','design-grammars') -Exact
    Assert-IsolatedFields $Model.networks @('sandbox') -Exact
    $network=$Model.networks.sandbox
    Assert-IsolatedFields $network @('name','internal','enable_ipv6','ipam')
    $ipam=Get-IsolatedValue $network 'ipam'
    if ($null -ne $ipam) { Assert-IsolatedFields $ipam @() -Exact }
    Assert-True ($network.name -ceq ($Project+'_sandbox') -and $network.internal -eq $true -and -not (Get-IsolatedValue $network 'enable_ipv6'))
    Assert-IsolatedFields $Model.volumes @('graph','api_state') -Exact
    foreach ($v in $Model.volumes.PSObject.Properties) {
        Assert-IsolatedFields $v.Value @('name') -Exact
        Assert-True ($v.Value.name -ceq ($Project+'_'+$v.Name))
    }
    $binds=@{
        'dg-reasoner'=@{'/app/ontology/DesignGrammar-V7.owl'='source/ontology/DesignGrammar-V7.owl';'/app/ontology/dg-disjointness.ttl'='source/ontology/dg-disjointness.ttl';'/app/ontology/dg-shapes.ttl'='source/ontology/dg-shapes.ttl'}
        'data-service'=@{'/mnt/repo/llm/cypher_catalog.json'='source/llm/cypher_catalog.json';'/mnt/repo/llm/structure_rules.json'='source/llm/structure_rules.json';'/mnt/repo/ontology/DesignGrammar-V7.owl'='source/ontology/DesignGrammar-V7.owl';'/mnt/repo/ontology/export_to_markdown_v7.py'='source/ontology/export_to_markdown_v7.py';'/mnt/repo/spec/evidence-contract.schema.json'='source/spec/evidence-contract.schema.json';'/mnt/repo/hosted-ingest'='source/deploy/hosted/ingest';'/app/image_runtime_probe.py'='support/probe.py';'/app/sandbox_probe.py'='support/sandbox_probe.py'}
        'neo4j'=@{}; 'design-grammars'=@{}
    }
    foreach ($property in $Model.services.PSObject.Properties) {
        $name=$property.Name; $s=$property.Value
        Assert-IsolatedFields $s @('image','pull_policy','platform','networks','restart','mem_limit','cpus','pids_limit','security_opt','environment','volumes','depends_on','healthcheck','command','entrypoint')
        # Compose emits nulls for inherited image defaults. Empty lists/strings
        # are explicit overrides and must not be admitted as equivalent to null.
        foreach ($field in @('command','entrypoint')) {
            $override=$s.PSObject.Properties[$field]
            if ($null -ne $override) { Assert-True ($null -eq $override.Value) }
        }
        Assert-True ($s.image -ceq $Job.images.PSObject.Properties[$name].Value.imageId -and $s.pull_policy -ceq 'never' -and $s.platform -ceq 'linux/amd64')
        Assert-True ($s.restart -ceq 'no' -and [double]$s.cpus -gt 0 -and [double]$s.cpus -le 1 -and [int]$s.pids_limit -gt 0 -and [int]$s.pids_limit -le 256)
        $memoryMax=if($name -ceq 'neo4j'){1500}else{1250}
        Assert-IsolatedMemory ([string]$s.mem_limit) $memoryMax
        Assert-True ((@($s.security_opt) -join ',') -cin @('no-new-privileges:true','no-new-privileges'))
        Assert-IsolatedFields $s.networks @('sandbox') -Exact
        $netOptions=Get-IsolatedValue $s.networks 'sandbox'
        if ($null -ne $netOptions) { Assert-IsolatedFields $netOptions @() -Exact }
        $seen=@{}
        foreach ($mount in (Get-IsolatedValue $s 'volumes')) {
            Assert-IsolatedFields $mount @('type','source','target','read_only','bind','volume')
            Assert-True (-not $seen.ContainsKey($mount.target)); $seen[$mount.target]=$true
            if ($mount.type -ceq 'bind') {
                Assert-True ($binds[$name].ContainsKey($mount.target) -and $mount.read_only -eq $true)
                $expected=[IO.Path]::GetFullPath((Join-Path $Root $binds[$name][$mount.target]))
                Assert-True ([IO.Path]::GetFullPath($mount.source).Equals($expected,[StringComparison]::OrdinalIgnoreCase))
                $options=Get-IsolatedValue $mount 'bind'
                if ($null -ne $options) { Assert-IsolatedFields $options @('create_host_path'); Assert-True (-not (Get-IsolatedValue $options 'create_host_path')) }
            } else {
                Assert-True ($mount.type -ceq 'volume')
                Assert-True (($name -ceq 'neo4j' -and $mount.source -ceq 'graph' -and $mount.target -ceq '/data') -or ($name -ceq 'data-service' -and $mount.source -ceq 'api_state' -and $mount.target -ceq '/app/data'))
                $options=Get-IsolatedValue $mount 'volume'
                if ($null -ne $options) { Assert-IsolatedFields $options @('nocopy'); Assert-True (-not (Get-IsolatedValue $options 'nocopy')) }
            }
        }
        $expectedCount=$binds[$name].Count
        if ($name -cin @('neo4j','data-service')) { $expectedCount++ }
        Assert-True ($seen.Count -eq $expectedCount)
        $dependencies=Get-IsolatedValue $s 'depends_on'
        if ($null -ne $dependencies) {
            Assert-IsolatedFields $dependencies @('neo4j') -Exact
            Assert-IsolatedFields $dependencies.neo4j @('condition','required','restart')
            Assert-True ($dependencies.neo4j.condition -ceq 'service_healthy' -and -not (Get-IsolatedValue $dependencies.neo4j 'restart'))
        }
    }
}
function Assert-IsolatedLocalStorage([string]$Root, [string]$Output, [string]$ArchiveDirectory) {
    foreach ($path in @($Root,$Output,$ArchiveDirectory)) {
        Assert-True ($path -match '^[A-Za-z]:[\\/]')
        Assert-RegularPath $path
        $drive=New-Object IO.DriveInfo([IO.Path]::GetPathRoot($path))
        Assert-True ($drive.DriveType -eq [IO.DriveType]::Fixed -and $drive.AvailableFreeSpace -ge 20GB)
    }
}
function New-IsolatedSecret {
    $bytes=New-Object byte[] 48
    $rng=[Security.Cryptography.RandomNumberGenerator]::Create()
    try { $rng.GetBytes($bytes); return [BitConverter]::ToString($bytes).Replace('-','').ToLowerInvariant() }
    finally { $rng.Dispose(); [Array]::Clear($bytes,0,$bytes.Length) }
}
function New-IsolatedContext([string]$Root, [string]$Output, $Report) {
    $config=Join-Path $Output 'docker-config'
    Assert-RegularPath $config
    Assert-True (-not (Test-Path -LiteralPath $config))
    [void][IO.Directory]::CreateDirectory($config)
    [IO.File]::WriteAllText((Join-Path $config 'config.json'),'{}',(New-Object Text.UTF8Encoding($false)))
    $environment=@{}
    foreach ($key in @('NEO4J_PASSWORD','LLM_MASTER_SECRET','DG_SERVICE_TOKEN','DG_BOOTSTRAP_ADMIN_PASSWORD')) { $environment[$key]=New-IsolatedSecret }
    # Child-only environment: no mutation of current process/user/machine env.
    return @{Root=$Root;Config=$config;Project=('dg-image-'+[guid]::NewGuid().ToString('N'));
        Environment=$environment;Deadline=[datetime]::UtcNow.AddMinutes(30);
        Docker=(Get-Command docker.exe -CommandType Application -ErrorAction Stop).Source;Report=$Report}
}
function Invoke-IsolatedDocker($Context, [string[]]$Command, [int]$Seconds, [int]$Limit=0) {
    $Context.Report.dockerInvoked=$true
    return Invoke-IsolatedProcess $Context.Docker (Get-IsolatedDockerArguments $Context $Command) $Context.Root $Context.Environment $Seconds $Context.Deadline $Limit
}
function Invoke-IsolatedCompose($Context, [string[]]$Command, [int]$Seconds, [int]$Limit=0) {
    $Context.Report.dockerInvoked=$true
    return Invoke-IsolatedProcess $Context.Docker (Get-IsolatedComposeArguments $Context $Command) $Context.Root $Context.Environment $Seconds $Context.Deadline $Limit
}
function Get-IsolatedResources($Context) {
    $result=@{}
    foreach ($kind in @('containers','networks','volumes')) {
        $command = switch ($kind) {
            'containers' { @('container','ls','--all','--filter',('label=com.docker.compose.project='+$Context.Project),'--format','{{.ID}}','--no-trunc') }
            'networks' { @('network','ls','--filter',('label=com.docker.compose.project='+$Context.Project),'--format','{{.ID}}','--no-trunc') }
            'volumes' { @('volume','ls','--filter',('label=com.docker.compose.project='+$Context.Project),'--format','{{.Name}}') }
        }
        $r=Invoke-IsolatedDocker $Context $command 15 8192
        Assert-True ($r.Code -eq 0)
        $values=@($r.Text.Split(@("`r","`n"),[StringSplitOptions]::RemoveEmptyEntries))
        Assert-True ($values.Count -le 4 -and @($values | Sort-Object -Unique).Count -eq $values.Count)
        foreach ($value in $values) { Assert-True ($value -cmatch '^[a-zA-Z0-9][a-zA-Z0-9_.-]{0,127}$') }
        $result[$kind]=$values
    }
    return $result
}
function Assert-IsolatedVacant($Context) {
    $resources=Get-IsolatedResources $Context
    foreach ($key in $resources.Keys) { Assert-True ($resources[$key].Count -eq 0) }
    # Do not adopt unrelated, unlabelled resources with colliding generated names.
    foreach ($spec in @(@('network','sandbox'),@('volume','graph'),@('volume','api_state'))) {
        $r=Invoke-IsolatedDocker $Context @($spec[0],'ls','--filter',('name=^'+$Context.Project+'_'+$spec[1]+'$'),'--format','{{.Name}}') 15 4096
        Assert-True ($r.Code -eq 0 -and -not $r.Text)
    }
}
function Assert-IsolatedOwnership($Context) {
    $resources=Get-IsolatedResources $Context
    $seen=@{}; $anonymous=New-Object 'Collections.Generic.List[string]'
    foreach ($kind in @('containers','networks','volumes')) {
        foreach ($id in $resources[$kind]) {
            if ($kind -ceq 'containers') {
                $format='{"Name":{{json .Name}},"Project":{{json (index .Config.Labels "com.docker.compose.project")}},"Owner":{{json (index .Config.Labels "com.docker.compose.service")}},"Number":{{json (index .Config.Labels "com.docker.compose.container-number")}},"Oneoff":{{json (index .Config.Labels "com.docker.compose.oneoff")}},"Image":{{json .Image}},"Mounts":{{json .Mounts}}}'
                $r=Invoke-IsolatedDocker $Context @('container','inspect','--format',$format,$id) 15 16384
            } else {
                $singular=if($kind -ceq 'networks'){'network'}else{'volume'}
                $format='{"Name":{{json .Name}},"Project":{{json (index .Labels "com.docker.compose.project")}},"Owner":{{json (index .Labels "com.docker.compose.'+$singular+'")}}}'
                $r=Invoke-IsolatedDocker $Context @($singular,'inspect','--format',$format,$id) 15 4096
            }
            Assert-True ($r.Code -eq 0)
            $item=$r.Text | ConvertFrom-Json
            Assert-True ($item.Project -ceq $Context.Project)
            if ($kind -ceq 'containers') {
                Assert-True ($item.Owner -cin @('neo4j','dg-reasoner','data-service','design-grammars') -and $item.Number -ceq '1' -and $item.Oneoff -ceq 'False')
                Assert-True ($item.Name -ceq ('/'+$Context.Project+'-'+$item.Owner+'-1'))
                Assert-True ($item.Image -ceq $Context.Images.PSObject.Properties[$item.Owner].Value.imageId)
                foreach($mount in $item.Mounts) {
                    if($mount.Type -ceq 'volume' -and $mount.Name -cnotin @(($Context.Project+'_graph'),($Context.Project+'_api_state'))) {
                        # Neo4j's inherited image VOLUME /logs is anonymous and has
                        # no Compose project label. Track it through its owned container.
                        Assert-True ($item.Owner -ceq 'neo4j' -and $mount.Destination -cin @('/logs','/data') -and $mount.Name -cmatch '^[0-9a-f]{64}$')
                        Assert-True (-not $anonymous.Contains($mount.Name));$anonymous.Add($mount.Name)
                    }
                }
            } elseif ($kind -ceq 'networks') {
                Assert-True ($item.Owner -ceq 'sandbox' -and $item.Name -ceq ($Context.Project+'_sandbox'))
            } else {
                Assert-True ($item.Owner -cin @('graph','api_state') -and $item.Name -ceq ($Context.Project+'_'+$item.Owner))
            }
            $key=$kind+':'+$item.Owner
            Assert-True (-not $seen.ContainsKey($key));$seen[$key]=$true
        }
    }
    $resources['anonymousVolumes']=@($anonymous.ToArray())
    return $resources
}
function Assert-IsolatedArchiveRetained([string]$Directory, $Image) {
    Assert-True ($Image.archive -cmatch '^(neo4j|dg-reasoner|data-service|design-grammars)\.tar$')
    $path=Join-Path $Directory $Image.archive
    Assert-RegularPath $path
    Assert-True ((Get-Item -LiteralPath $path -Force).Length -eq $Image.archiveBytes)
}
function Invoke-IsolatedSmoke([string]$Root, [string]$Output, [string]$ArchiveDirectory, $Job, $Report) {
    $stage='runtime-guard';$context=$null;$startup=$false;$smoke=$false;$failed=$false
    $Report.status='FAILED'
    try {
        Assert-True ($Report.archiveBytesVerified -eq $true)
        Assert-IsolatedRuntimeGuard ([Environment]::MachineName) ([Environment]::GetEnvironmentVariables())
        Assert-IsolatedLocalStorage $Root $Output $ArchiveDirectory
        Assert-True ((@($Job.images.PSObject.Properties.Name | Sort-Object) -join ',') -ceq 'data-service,design-grammars,dg-reasoner,neo4j')
        $context=New-IsolatedContext $Root $Output $Report
        $context.Images=$Job.images
        $stage='daemon-preflight'
        $version=Invoke-IsolatedDocker $context @('version','--format','{{json .}}') 20 65536
        $info=Invoke-IsolatedDocker $context @('info','--format','{"OSType":{{json .OSType}},"Architecture":{{json .Architecture}},"MemTotal":{{json .MemTotal}}}') 20 4096
        $composeVersion=Invoke-IsolatedDocker $context @('compose','version','--short') 20 1024
        Assert-True ($version.Code -eq 0 -and $info.Code -eq 0 -and $composeVersion.Code -eq 0)
        Assert-IsolatedDaemon $version.Text $info.Text $composeVersion.Text
        $Report.checks.daemonPreflight=$true
        foreach ($name in @('neo4j','dg-reasoner','data-service','design-grammars')) {
            $image=$Job.images.PSObject.Properties[$name].Value
            $stage='load:'+ $name
            Assert-IsolatedArchiveRetained $ArchiveDirectory $image
            $r=Invoke-IsolatedDocker $context @('image','load','--input',(Join-Path $ArchiveDirectory $image.archive)) 360
            Assert-True ($r.Code -eq 0)
            $stage='image-identity:'+ $name
            $projection='{"Id":{{json .Id}},"Os":{{json .Os}},"Architecture":{{json .Architecture}},"Revision":{{json (index .Config.Labels "org.opencontainers.image.revision")}}}'
            $r=Invoke-IsolatedDocker $context @('image','inspect','--format',$projection,$image.imageId) 20 4096
            Assert-True ($r.Code -eq 0)
            Confirm-IsolatedImage ($r.Text | ConvertFrom-Json) $image.imageId $Job.sourceRevision
            # Verify the archive's declared local tag resolves to the same identity.
            $r=Invoke-IsolatedDocker $context @('image','inspect','--format',$projection,$image.tag) 20 4096
            Assert-True ($r.Code -eq 0)
            Confirm-IsolatedImage ($r.Text | ConvertFrom-Json) $image.imageId $Job.sourceRevision
            $Report.images[$name]=[ordered]@{imageId=$image.imageId;status='LOADED_AND_VERIFIED';os='linux';architecture='amd64';revision=$Job.sourceRevision}
        }
        $stage='compose-config'
        $r=Invoke-IsolatedCompose $context @('config','--format','json') 30 262144
        Assert-True ($r.Code -eq 0)
        $model=$r.Text | ConvertFrom-Json
        Assert-IsolatedComposeModel $model $Job $Root $context.Project
        $model=$null;$r=$null
        $Report.checks.composeIsolation=$true
        $stage='project-vacancy'
        Assert-IsolatedVacant $context
        $Report.checks.projectVacant=$true
        $stage='service-start'
        $startup=$true # up can fail after partial resource creation
        $r=Invoke-IsolatedCompose $context @('up','--detach','--no-build','--pull','never') 240
        Assert-True ($r.Code -eq 0)
        $stage='readiness'
        $ready=$false
        for($i=0;$i -lt 48;$i++) {
            $r=Invoke-IsolatedCompose $context @('exec','-T','data-service','python','/app/image_runtime_probe.py','ready') 30
            if($r.Code -eq 0){$ready=$true;break}
            Assert-True (([datetime]::UtcNow.AddSeconds(30)) -lt $context.Deadline)
            Start-Sleep -Seconds 5
        }
        Assert-True $ready
        $Report.checks.readiness=$true
        $stage='isolated-smoke'
        $r=Invoke-IsolatedCompose $context @('exec','-T','data-service','python','/app/image_runtime_probe.py') 180 16384
        Assert-True ($r.Code -eq 0)
        $Report.checks.smoke=Confirm-IsolatedSmokeEvidence ($r.Text | ConvertFrom-Json)
        $r=$null
        $smoke=$true
    } catch {
        $Report.failureStage=$stage;$failed=$true
    } finally {
        if($startup) {
            try {
                $context.Deadline=[datetime]::UtcNow.AddMinutes(5)
                $resources=Assert-IsolatedOwnership $context
                $count=0;foreach($key in $resources.Keys){$count+=$resources[$key].Count}
                if($count -gt 0) {
                    $r=Invoke-IsolatedCompose $context @('down','--volumes','--remove-orphans','--timeout','20') 90
                    Assert-True ($r.Code -eq 0)
                }
                $remaining=Get-IsolatedResources $context
                foreach($key in $remaining.Keys){Assert-True ($remaining[$key].Count -eq 0)}
                foreach($volume in $resources['anonymousVolumes']) {
                    $r=Invoke-IsolatedDocker $context @('volume','ls','--filter',('name=^'+$volume+'$'),'--format','{{.Name}}') 15 1024
                    Assert-True ($r.Code -eq 0 -and -not $r.Text)
                }
                foreach($name in @('neo4j','dg-reasoner','data-service','design-grammars')) {
                    $image=$Job.images.PSObject.Properties[$name].Value
                    Assert-IsolatedArchiveRetained $ArchiveDirectory $image
                    $r=Invoke-IsolatedDocker $context @('image','inspect','--format','{{.Id}}',$image.imageId) 15 1024
                    Assert-True ($r.Code -eq 0 -and $r.Text -ceq $image.imageId)
                }
                $Report.cleanup='project-down-volumes-removed';$Report.checks.cleanupVerified=$true
                $Report.checks.imagesAndArchivesRetained=$true
            } catch {
                $Report.cleanup='FAILED';$Report.failureStage='cleanup';$failed=$true
            }
        }
        if($null -ne $context){$context.Environment.Clear()}
    }
    if($failed -or -not $smoke -or $Report.cleanup -cne 'project-down-volumes-removed') {
        throw 'isolated runtime failed; consult sanitized failureStage'
    }
    $Report.status='LOAD_AND_ISOLATED_SMOKE_COMPLETE'
}
function Assert-IsolatedRuntimeGuard([string]$ComputerName, [Collections.IDictionary]$Environment) {
    Assert-True ($ComputerName -ceq 'DESKTOP-OS4Q8CP')
    foreach ($key in $Environment.Keys) {
        if ([string]$key -match '^(?i:DOCKER_|COMPOSE_|BUILDKIT_|BUILDX_)') {
            Assert-True ([string]$Environment[$key] -ceq '')
        }
    }
}
