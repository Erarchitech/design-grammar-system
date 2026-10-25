#requires -Version 5.1
# Function-only trusted boundary, never auto-invoked on import.
# Scope JSON is an issued owner-approval record, NOT proof that approval exists.
# Caller must match the original owner decision and exact immutable package.
function Assert-True($Value) { if(-not $Value){throw 'multi-store rejected'} }
function Assert-MultiScope($Scope,[string]$HostName,[string]$PackageSha,[datetime]$Now) {
    Assert-IsolatedFields $Scope @('schemaVersion','target','kind','packageSha256','approvalReference','expiresAtUtc','maxSeconds','maxCommands','network','data','daemonState','cleanup') -Exact
    Assert-True ($Scope.schemaVersion -is [int] -and $Scope.schemaVersion -eq 1)
    Assert-True ($HostName -ceq 'DESKTOP-OS4Q8CP' -and $Scope.target -ceq $HostName)
    Assert-True ($Scope.kind -ceq 'one-synthetic-multistore-exercise')
    Assert-True ($PackageSha -cmatch '^[0-9a-f]{64}$' -and $Scope.packageSha256 -ceq $PackageSha)
    Assert-True ($Scope.approvalReference -is [string] -and $Scope.approvalReference -cmatch '^[a-zA-Z0-9][a-zA-Z0-9._-]{0,95}$')
    Assert-True ($Scope.expiresAtUtc -is [string])
    $expires=[datetime]::Parse($Scope.expiresAtUtc,[Globalization.CultureInfo]::InvariantCulture,[Globalization.DateTimeStyles]::RoundtripKind)
    Assert-True ($expires.Kind -eq [DateTimeKind]::Utc -and $Now.ToUniversalTime() -lt $expires -and $expires -le $Now.ToUniversalTime().AddDays(7))
    foreach($key in @('maxSeconds','maxCommands')) {
        $v=$Scope.PSObject.Properties[$key].Value
        Assert-True (($v -is [int] -or $v -is [long]) -and $v -gt 0)
    }
    Assert-True ($Scope.maxSeconds -le 5400 -and $Scope.maxCommands -le 500)
    Assert-True ($Scope.network -ceq 'internal-no-published-ports' -and $Scope.data -ceq 'new-synthetic-volumes-only')
    Assert-True ($Scope.daemonState -ceq 'already-running-no-start-stop' -and $Scope.cleanup -ceq 'owned-resources-only')
}
function Assert-MultiPair([string]$Source,[string]$Destination) {
    foreach($name in @($Source,$Destination)){Assert-True ($name -cmatch '^dg-multi-[0-9a-f]{32}$')}
    Assert-True ($Source -cne $Destination)
}
function Use-MultiBudget($Context) {
    Assert-True ($Context.Commands -is [int] -and $Context.MaxCommands -is [int] -and $Context.Commands -lt $Context.MaxCommands)
    Assert-True ([datetime]::UtcNow -lt $Context.Deadline)
    if($Context.ContainsKey('SharedBudget')) {
        $budget=$Context.SharedBudget
        Assert-True ($budget.Commands -is [int] -and $budget.MaxCommands -is [int] -and $budget.Commands -lt $budget.MaxCommands)
        Assert-True ([datetime]::UtcNow -lt $budget.Deadline)
        $budget.Commands++
    }
    $Context.Commands++
}
function Assert-MultiContainerRecord($Context,[string]$Service,$Record,[bool]$Running) {
    Assert-IsolatedFields $Record @('Id','Image','Project','Service','Running') -Exact
    Assert-True ($Context.Project -cmatch '^dg-multi-[0-9a-f]{32}$' -and $Context.Images.ContainsKey($Service))
    Assert-True ($Record.Id -is [string] -and $Record.Id -cmatch '^[0-9a-f]{64}$')
    Assert-True ($Record.Image -ceq $Context.Images[$Service] -and $Record.Project -ceq $Context.Project -and $Record.Service -ceq $Service)
    Assert-True ($Record.Running -is [bool] -and $Record.Running -eq $Running)
}
function Get-MultiArguments($Context,[string[]]$Command) {
    Assert-True ($Command.Count -gt 0)
    $config=$Context.Config
    if($Command[0] -ceq 'compose'){$config=$Context.ComposeConfig}
    return @('--host','npipe:////./pipe/docker_engine','--config',$config)+$Command
}
function Get-MultiComposeArguments($Context,[string[]]$Command) {
    Assert-True ($Context.Project -cmatch '^dg-multi-[0-9a-f]{32}$')
    return Get-MultiArguments $Context (@('compose','--env-file',(Join-Path $Context.Root 'support/empty-env.txt'),'--project-directory',$Context.Root,'--file',(Join-Path $Context.Root $Context.Compose),'--project-name',$Context.Project)+$Command)
}
function Invoke-MultiProcess([string]$Executable,[string[]]$Arguments,[string]$Root,
    [Collections.IDictionary]$Environment,[int]$Seconds,[datetime]$Deadline,[int]$CaptureLimit=0) {
    $process=$null;$buffer=$null;$started=$false;$out=$null;$err=$null
    try {
        Initialize-IsolatedCapture
        $remaining=($Deadline-[datetime]::UtcNow).TotalSeconds
        Assert-True ($remaining -gt 25 -and $Seconds -gt 0 -and $CaptureLimit -ge 0 -and $CaptureLimit -le 1048576)
        $wait=[int]([math]::Min($Seconds,$remaining-25)*1000)
        $psi=New-Object Diagnostics.ProcessStartInfo
        $psi.FileName=$Executable;$psi.WorkingDirectory=$Root
        $psi.Arguments=(@($Arguments|ForEach-Object{ConvertTo-IsolatedArgument $_}) -join ' ')
        $psi.UseShellExecute=$false;$psi.CreateNoWindow=$true
        $psi.RedirectStandardOutput=$true;$psi.RedirectStandardError=$true
        $psi.EnvironmentVariables.Clear()
        foreach($key in $Environment.Keys){$psi.EnvironmentVariables[$key]=[string]$Environment[$key]}
        $process=New-Object Diagnostics.Process;$process.StartInfo=$psi
        $buffer=New-Object DgRuntimeBoundedStream($CaptureLimit)
        [void]$process.Start();$started=$true
        $out=$process.StandardOutput.BaseStream.CopyToAsync($buffer)
        $err=$process.StandardError.BaseStream.CopyToAsync([IO.Stream]::Null)
        if(-not $process.WaitForExit($wait)){Stop-IsolatedProcess $process;throw 'rejected'}
        if(-not $out.Wait(1000) -or -not $err.Wait(1000)){Stop-IsolatedProcess $process;throw 'rejected'}
        Assert-True (-not $buffer.Overflow -and $process.ExitCode -eq 0 -and [datetime]::UtcNow -lt $Deadline)
        return @{Code=0;Text=$buffer.Text().Trim()}
    } catch {
        if($started -and -not $process.HasExited){try{Stop-IsolatedProcess $process}catch{}}
        throw 'multi-store command rejected'
    } finally {
        if($null -ne $process){$process.Dispose()}
        if($null -ne $buffer){$buffer.Dispose()}
    }
}
function Invoke-MultiDocker($Context,[string[]]$Command,[int]$Seconds=30,[int]$Limit=16384) {
    Use-MultiBudget $Context
    $Context.Report.dockerInvoked=$true
    $child=@{SystemRoot=[Environment]::GetEnvironmentVariable('SystemRoot','Process');PATH=(Split-Path -Parent $Context.Docker);DOCKER_CONFIG=$Context.Config}
    return (Invoke-MultiProcess $Context.Docker (Get-MultiArguments $Context $Command) $Context.Root $child $Seconds $Context.Deadline $Limit).Text
}
function Invoke-MultiCompose($Context,[string[]]$Command,[int]$Seconds=30,[int]$Limit=16384) {
    Use-MultiBudget $Context
    $Context.Report.dockerInvoked=$true
    $child=@{SystemRoot=[Environment]::GetEnvironmentVariable('SystemRoot','Process');PATH=(Split-Path -Parent $Context.Docker);DOCKER_CONFIG=$Context.ComposeConfig}
    foreach($key in $Context.Environment.Keys){$child[$key]=$Context.Environment[$key]}
    return (Invoke-MultiProcess $Context.Docker (Get-MultiComposeArguments $Context $Command) $Context.Root $child $Seconds $Context.Deadline $Limit).Text
}
function Assert-MultiEqual($Actual,$Expected) {
    if($null -eq $Expected){Assert-True ($null -eq $Actual);return}
    if($Expected -is [pscustomobject]) {
        $names=@($Expected.PSObject.Properties|ForEach-Object{$_.Name})
        Assert-IsolatedFields $Actual $names -Exact
        foreach($p in $Expected.PSObject.Properties){Assert-MultiEqual $Actual.PSObject.Properties[$p.Name].Value $p.Value}
    } elseif($Expected -is [Array]) {
        Assert-True ($Actual -is [Array] -and $Actual.Count -eq $Expected.Count)
        for($i=0;$i -lt $Expected.Count;$i++){Assert-MultiEqual $Actual[$i] $Expected[$i]}
    } elseif($Expected -is [bool]) {Assert-True ($Actual -is [bool] -and $Actual -eq $Expected)}
    elseif($Expected -is [string]) {Assert-True ($Actual -is [string] -and $Actual -ceq $Expected)}
    else {Assert-True (($Actual -is [int] -or $Actual -is [long] -or $Actual -is [double] -or $Actual -is [decimal]) -and $Actual -eq $Expected)}
}
function Get-MultiMemoryBytes($Value) {
    if($Value -is [int] -or $Value -is [long]){return [long]$Value}
    Assert-True ($Value -is [string] -and $Value -cmatch '^([1-9][0-9]*)([mMgG]?)$')
    $number=[long]$Matches[1]
    if($Matches[2] -match '^[mM]$'){$number*=1MB}elseif($Matches[2] -match '^[gG]$'){$number*=1GB}
    return $number
}
function Assert-MultiModel($Model,$Context) {
    $text=Get-Content -LiteralPath (Join-Path $Context.Root $Context.Compose) -Raw -Encoding UTF8
    foreach($key in $Context.Environment.Keys){$text=$text.Replace(('${'+$key+':?required}'),[string]$Context.Environment[$key])}
    # Literal $$ is reduced by Compose to a single dollar inside shell commands.
    $text=$text.Replace('$$','$')
    $template=$text|ConvertFrom-Json
    Assert-IsolatedFields $Model @('name','services','networks','volumes') -Exact
    Assert-True ($Model.name -ceq $Context.Project)
    $roles=@($template.services.PSObject.Properties|ForEach-Object{$_.Name})
    Assert-IsolatedFields $Model.services $roles -Exact
    Assert-IsolatedFields $Model.networks @('sandbox') -Exact
    $network=$Model.networks.sandbox
    Assert-IsolatedFields $network @('name','internal','enable_ipv6','ipam')
    Assert-True ($network.name -ceq ($Context.Project+'_sandbox') -and $network.internal -is [bool] -and $network.internal)
    Assert-True ($network.enable_ipv6 -is [bool] -and -not $network.enable_ipv6)
    $ipam=Get-IsolatedValue $network 'ipam';if($null -ne $ipam){Assert-IsolatedFields $ipam @() -Exact}
    $volumes=@($template.volumes.PSObject.Properties|ForEach-Object{$_.Name})
    Assert-IsolatedFields $Model.volumes $volumes -Exact
    foreach($name in $volumes){Assert-IsolatedFields $Model.volumes.PSObject.Properties[$name].Value @('name') -Exact;Assert-True ($Model.volumes.PSObject.Properties[$name].Value.name -ceq ($Context.Project+'_'+$name))}
    foreach($role in $roles) {
        $expected=$template.services.PSObject.Properties[$role].Value;$actual=$Model.services.PSObject.Properties[$role].Value
        $names=@($expected.PSObject.Properties|ForEach-Object{$_.Name})
        Assert-IsolatedFields $actual ($names+@('command','entrypoint'))
        foreach($field in @('command','entrypoint')) {
            if($field -cnotin $names){
                $property=$actual.PSObject.Properties[$field]
                if($null -ne $property){Assert-True ($null -eq $property.Value)}
            }
        }
        foreach($p in $expected.PSObject.Properties) {
            # Reading through a function would enumerate singleton/empty arrays.
            Assert-True ($null -ne $actual.PSObject.Properties[$p.Name])
            $value=$actual.PSObject.Properties[$p.Name].Value
            switch -CaseSensitive ($p.Name) {
                'mem_limit' {Assert-True ((Get-MultiMemoryBytes $value) -eq (Get-MultiMemoryBytes $p.Value))}
                'security_opt' {Assert-True ((@($value)-join ',') -cin @('no-new-privileges:true','no-new-privileges'))}
                'networks' {
                    Assert-IsolatedFields $value @('sandbox') -Exact
                    if($null -ne $value.sandbox){Assert-IsolatedFields $value.sandbox @() -Exact}
                }
                'depends_on' {
                    $deps=@($p.Value.PSObject.Properties|ForEach-Object{$_.Name});Assert-IsolatedFields $value $deps -Exact
                    foreach($dep in $deps) {
                        $d=$value.PSObject.Properties[$dep].Value
                        Assert-IsolatedFields $d @('condition','required','restart')
                        Assert-True ($d.condition -ceq $p.Value.PSObject.Properties[$dep].Value.condition)
                        $required=Get-IsolatedValue $d 'required';if($null -ne $required){Assert-True ($required -is [bool] -and $required)}
                        $restart=Get-IsolatedValue $d 'restart';if($null -ne $restart){Assert-True ($restart -is [bool] -and -not $restart)}
                    }
                }
                'volumes' {
                    Assert-True (@($value).Count -eq @($p.Value).Count);$seen=@{}
                    foreach($mount in $value) {
                        Assert-IsolatedFields $mount @('type','source','target','read_only','bind','volume')
                        Assert-True (-not $seen.ContainsKey($mount.target));$seen[$mount.target]=$true
                        $want=@($p.Value|Where-Object{$_.target -ceq $mount.target});Assert-True ($want.Count -eq 1);$want=$want[0]
                        Assert-True ($mount.type -ceq $want.type)
                        $ro=Get-IsolatedValue $mount 'read_only';$wantRo=Get-IsolatedValue $want 'read_only'
                        if($null -ne $ro){Assert-True ($ro -is [bool])}
                        Assert-True ([bool]$ro -eq [bool]$wantRo)
                        if($mount.type -ceq 'bind') {
                            Assert-True ($ro -eq $true)
                            $path=[IO.Path]::GetFullPath((Join-Path $Context.Root $want.source))
                            Assert-True ([IO.Path]::GetFullPath($mount.source).Equals($path,[StringComparison]::OrdinalIgnoreCase))
                            $opts=Get-IsolatedValue $mount 'bind'
                            if($null -ne $opts){Assert-IsolatedFields $opts @('create_host_path');Assert-True (-not (Get-IsolatedValue $opts 'create_host_path'))}
                            Assert-True ($null -eq (Get-IsolatedValue $mount 'volume'))
                        } else {
                            Assert-True ($mount.type -ceq 'volume' -and $mount.source -ceq $want.source)
                            Assert-True ($null -eq (Get-IsolatedValue $mount 'bind'))
                            $opts=Get-IsolatedValue $mount 'volume'
                            if($null -ne $opts){Assert-IsolatedFields $opts @('nocopy');Assert-True (-not (Get-IsolatedValue $opts 'nocopy'))}
                        }
                    }
                }
                default {Assert-MultiEqual $value $p.Value}
            }
        }
    }
}
function Get-MultiResources($Context) {
    $resources=@{}
    foreach($kind in @('containers','networks','volumes')) {
        $command=switch -CaseSensitive ($kind) {
            'containers' {@('container','ls','--all','--filter',('label=com.docker.compose.project='+$Context.Project),'--format','{{.ID}}','--no-trunc')}
            'networks' {@('network','ls','--filter',('label=com.docker.compose.project='+$Context.Project),'--format','{{.ID}}','--no-trunc')}
            'volumes' {@('volume','ls','--filter',('label=com.docker.compose.project='+$Context.Project),'--format','{{.Name}}')}
        }
        $text=Invoke-MultiDocker $Context $command 15 16384
        $items=@($text.Split(@("`r","`n"),[StringSplitOptions]::RemoveEmptyEntries))
        Assert-True ($items.Count -le 32 -and @($items|Sort-Object -Unique).Count -eq $items.Count)
        foreach($item in $items){Assert-True ($item -cmatch '^[a-zA-Z0-9][a-zA-Z0-9_.-]{0,127}$')}
        $resources[$kind]=$items
    }
    return $resources
}
function Assert-MultiVacant($Context) {
    $resources=Get-MultiResources $Context
    foreach($kind in $resources.Keys){Assert-True ($resources[$kind].Count -eq 0)}
    foreach($role in @('sandbox')+$Context.Volumes) {
        $kind=if($role -ceq 'sandbox'){'network'}else{'volume'}
        $text=Invoke-MultiDocker $Context @($kind,'ls','--filter',('name=^'+$Context.Project+'_'+$role+'$'),'--format','{{.Name}}') 15 4096
        Assert-True (-not $text)
    }
}
function Assert-MultiOwnership($Context) {
    Assert-True ($Context.Project -cmatch '^dg-multi-[0-9a-f]{32}$')
    $resources=Get-MultiResources $Context
    $seen=@{}
    foreach($id in $resources.containers) {
        $format='{"Id":{{json .Id}},"Name":{{json .Name}},"Image":{{json .Image}},"Project":{{json (index .Config.Labels "com.docker.compose.project")}},"Service":{{json (index .Config.Labels "com.docker.compose.service")}},"Mounts":{{json .Mounts}}}'
        $item=(Invoke-MultiDocker $Context @('container','inspect','--format',$format,$id))|ConvertFrom-Json
        Assert-IsolatedFields $item @('Id','Name','Image','Project','Service','Mounts') -Exact
        Assert-True ($item.Project -ceq $Context.Project -and $item.Service -cin $Context.Services -and $Context.Images.ContainsKey($item.Service))
        Assert-True ($item.Id -ceq $id -and $item.Image -ceq $Context.Images[$item.Service])
        Assert-True ($item.Name -ceq ('/'+$Context.Project+'-'+$item.Service+'-1') -and -not $seen.ContainsKey($item.Service))
        $seen[$item.Service]=$true
        foreach($mount in $item.Mounts) {
            if($mount.Type -ceq 'volume') {
                Assert-True ($mount.Name -cin @($Context.Volumes|ForEach-Object{$Context.Project+'_'+$_}))
            } else {Assert-True ($mount.Type -ceq 'bind')}
        }
    }
    foreach($kind in @('networks','volumes')) {
        $singular=if($kind -ceq 'networks'){'network'}else{'volume'}
        foreach($id in $resources[$kind]) {
            $format='{"Name":{{json .Name}},"Project":{{json (index .Labels "com.docker.compose.project")}},"Owner":{{json (index .Labels "com.docker.compose.'+$singular+'")}}}'
            $item=(Invoke-MultiDocker $Context @($singular,'inspect','--format',$format,$id))|ConvertFrom-Json
            Assert-IsolatedFields $item @('Name','Project','Owner') -Exact
            $allowed=if($kind -ceq 'networks'){@('sandbox')}else{$Context.Volumes}
            Assert-True ($item.Project -ceq $Context.Project -and $item.Owner -cin $allowed -and $item.Name -ceq ($Context.Project+'_'+$item.Owner))
            if($kind -ceq 'volumes') {
                $text=Invoke-MultiDocker $Context @('container','ls','--all','--filter',('volume='+$item.Name),'--format','{{.ID}}','--no-trunc') 15 8192
                $consumers=@($text.Split(@("`r","`n"),[StringSplitOptions]::RemoveEmptyEntries))
                Assert-True ($consumers.Count -le 32)
                foreach($consumer in $consumers){Assert-True ($consumer -cin $resources.containers)}
            }
        }
    }
    return $resources
}
function Complete-MultiCleanup([object[]]$Contexts,$Report) {
    $activated=0;$ok=$true;$remainingCommands=160
    $cleanupDeadline=[datetime]::UtcNow.AddMinutes(5)
    foreach($context in $Contexts) {
        if(-not $context.CleanupActivated){continue}
        $activated++;$substage='ownership'
        # One cleanup allowance shared by both owned projects, not per project.
        $context.Commands=0;$context.MaxCommands=$remainingCommands
        if($context.ContainsKey('SharedBudget')){$context.Remove('SharedBudget')}
        try {
            $context.Deadline=$cleanupDeadline
            [void](Assert-MultiOwnership $context)
            $substage='down'
            [void](Invoke-MultiCompose $context @('--profile','maintenance','down','--volumes','--remove-orphans','--timeout','20') 120 0)
            $substage='vacancy';Assert-MultiVacant $context
        } catch {$ok=$false;if($null -eq $Report.cleanupFailureStage){$Report.cleanupFailureStage=$substage}}
        finally {$remainingCommands-=$context.Commands}
    }
    $Report.cleanup=if($activated -eq 0){'not-started'}elseif($ok){'owned-projects-volumes-removed'}else{'FAILED'}
    if(-not $ok -and $null -eq $Report.failureStage){$Report.failureStage='cleanup'}
}
