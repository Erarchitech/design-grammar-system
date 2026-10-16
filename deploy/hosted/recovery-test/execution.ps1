#requires -Version 5.1
# Function-only module. Called after exact ZIP/extraction validation.
function Assert-RecoveryName([string]$Name) { Assert-True ($Name -cmatch '^dg-recovery-[0-9a-f]{32}$') }
function Assert-RecoveryPair([string]$Source,[string]$Destination) {
    Assert-RecoveryName $Source; Assert-RecoveryName $Destination; Assert-True ($Source -cne $Destination)
}
function Assert-RecoveryCipherName([string]$Name) { Assert-True ($Name -ceq 'backup.enc') }
function Assert-RecoveryStoppedRecord($Record,$Context,[string]$Service) {
    Assert-True ($Record.Running -is [bool] -and -not $Record.Running)
    Assert-True ($Record.Project -ceq $Context.Project -and $Record.Owner -ceq $Service -and $Record.Image -ceq $Context.Images.PSObject.Properties[$Service].Value)
}
function Invoke-RecoveryCompose($Context,[string[]]$Command,[int]$Seconds=30,[int]$Limit=16384) {
    $args=@('compose','--env-file',(Join-Path $Context.Root 'support/empty-env.txt'),'--project-directory',$Context.Root,
        '--file',(Join-Path $Context.Root $Context.Compose),'--project-name',$Context.Project)+$Command
    $r=Invoke-IsolatedDocker $Context $args $Seconds $Limit
    Assert-True ($r.Code -eq 0)
    return $r.Text
}
function Invoke-RecoveryDocker($Context,[string[]]$Command,[int]$Seconds=30,[int]$Limit=16384) {
    $r=Invoke-IsolatedDocker $Context $Command $Seconds $Limit
    Assert-True ($r.Code -eq 0)
    return $r.Text
}
function Get-RecoveryContainer($Context,[string]$Service) {
    Assert-True ($Service -cin @('neo4j','data-service','graph-admin','snapshot'))
    $id=Invoke-RecoveryCompose $Context @('ps','--all','--quiet',$Service)
    Assert-True ($id -cmatch '^[0-9a-f]{64}$')
    return $id
}
function Assert-RecoveryStopped($Context,[string]$Service) {
    $id=Get-RecoveryContainer $Context $Service
    $format='{"Running":{{json .State.Running}},"Project":{{json (index .Config.Labels "com.docker.compose.project")}},"Owner":{{json (index .Config.Labels "com.docker.compose.service")}},"Image":{{json .Image}}}'
    $r=Invoke-RecoveryDocker $Context @('container','inspect','--format',$format,$id)
    Assert-RecoveryStoppedRecord ($r|ConvertFrom-Json) $Context $Service
}
function Assert-RecoveryVacant($Context) {
    Assert-RecoveryName $Context.Project
    $resources=Get-IsolatedResources $Context
    foreach($key in $resources.Keys){Assert-True ($resources[$key].Count -eq 0)}
    foreach($spec in @(@('network','sandbox'),@('volume','graph'),@('volume','api_state'),@('volume','exchange'),@('volume','graph_logs'))) {
        $text=Invoke-RecoveryDocker $Context @($spec[0],'ls','--filter',('name=^'+$Context.Project+'_'+$spec[1]+'$'),'--format','{{.Name}}')
        Assert-True (-not $text)
    }
}
function Assert-RecoveryOwnership($Context) {
    $resources=Get-IsolatedResources $Context
    $seen=@{}
    foreach($kind in @('containers','networks','volumes')) {
        foreach($id in $resources[$kind]) {
            if($kind -ceq 'containers') {
                $format='{"Name":{{json .Name}},"Project":{{json (index .Config.Labels "com.docker.compose.project")}},"Owner":{{json (index .Config.Labels "com.docker.compose.service")}},"Image":{{json .Image}},"Mounts":{{json .Mounts}}}'
                $item=(Invoke-RecoveryDocker $Context @('container','inspect','--format',$format,$id))|ConvertFrom-Json
                Assert-True ($item.Owner -cin @('neo4j','data-service','graph-admin','snapshot'))
                Assert-True ($item.Name -ceq ('/'+$Context.Project+'-'+$item.Owner+'-1'))
                Assert-True ($item.Image -ceq $Context.Images.PSObject.Properties[$item.Owner].Value)
                foreach($mount in $item.Mounts) {
                    if($mount.Type -ceq 'volume') {
                        Assert-True ($mount.Name -cin @(($Context.Project+'_graph'),($Context.Project+'_graph_logs'),($Context.Project+'_api_state'),($Context.Project+'_exchange')))
                    }
                }
            } else {
                $singular=if($kind -ceq 'networks'){'network'}else{'volume'}
                $format='{"Name":{{json .Name}},"Project":{{json (index .Labels "com.docker.compose.project")}},"Owner":{{json (index .Labels "com.docker.compose.'+$singular+'")}}}'
                $item=(Invoke-RecoveryDocker $Context @($singular,'inspect','--format',$format,$id))|ConvertFrom-Json
                $allowed=if($kind -ceq 'networks'){@('sandbox')}else{@('graph','graph_logs','api_state','exchange')}
                Assert-True ($item.Owner -cin $allowed -and $item.Name -ceq ($Context.Project+'_'+$item.Owner))
            }
            Assert-True ($item.Project -ceq $Context.Project)
            $key=$kind+':'+$item.Owner
            Assert-True (-not $seen.ContainsKey($key));$seen[$key]=$true
        }
    }
    return $resources
}
function Assert-RecoveryModel($Model,$Context) {
    $template=Get-Content -LiteralPath (Join-Path $Context.Root $Context.Compose) -Raw|ConvertFrom-Json
    Assert-IsolatedFields $Model @('name','services','networks','volumes') -Exact
    Assert-True ($Model.name -ceq $Context.Project)
    Assert-IsolatedFields $Model.services @('neo4j','data-service','graph-admin','snapshot') -Exact
    Assert-IsolatedFields $Model.networks @('sandbox') -Exact
    $n=$Model.networks.sandbox
    Assert-IsolatedFields $n @('name','internal','enable_ipv6','ipam')
    Assert-True ($n.name -ceq ($Context.Project+'_sandbox') -and $n.internal -eq $true -and -not $n.enable_ipv6)
    $ipam=Get-IsolatedValue $n 'ipam'; if($null -ne $ipam){Assert-IsolatedFields $ipam @() -Exact}
    Assert-IsolatedFields $Model.volumes @('graph','api_state','graph_logs','exchange') -Exact
    foreach($p in $Model.volumes.PSObject.Properties) {
        Assert-IsolatedFields $p.Value @('name') -Exact;Assert-True ($p.Value.name -ceq ($Context.Project+'_'+$p.Name))
    }
    foreach($p in $Model.services.PSObject.Properties) {
        $s=$p.Value;$name=$p.Name
        Assert-IsolatedFields $s @('image','pull_policy','platform','networks','restart','mem_limit','cpus','pids_limit','security_opt','environment','volumes','depends_on','healthcheck','command','entrypoint','profiles','user','network_mode')
        Assert-True ($s.image -ceq $Context.Images.PSObject.Properties[$name].Value -and $s.pull_policy -ceq 'never' -and $s.platform -ceq 'linux/amd64' -and $s.restart -ceq 'no')
        Assert-True ([double]$s.cpus -gt 0 -and [double]$s.cpus -le 1 -and [int]$s.pids_limit -gt 0 -and [int]$s.pids_limit -le 256)
        $max=if($name -ceq 'neo4j'){1500}elseif($name -ceq 'data-service'){1250}else{768}
        Assert-IsolatedMemory ([string]$s.mem_limit) $max
        Assert-True ((@($s.security_opt) -join ',') -cin @('no-new-privileges:true','no-new-privileges'))
        if($name -cin @('snapshot','graph-admin')) {
            Assert-True ($s.network_mode -ceq 'none' -and $s.user -ceq '0:0')
            Assert-True ((@($s.entrypoint) -join '|') -ceq '/bin/sh|-c|exec sleep 3600')
            Assert-True ($null -eq (Get-IsolatedValue $s 'networks') -and $null -eq (Get-IsolatedValue $s 'command'))
        } else {
            Assert-IsolatedFields $s.networks @('sandbox') -Exact
            $attachment=Get-IsolatedValue $s.networks 'sandbox'
            if($null -ne $attachment){Assert-IsolatedFields $attachment @() -Exact}
            Assert-True ($null -eq (Get-IsolatedValue $s 'command') -and $null -eq (Get-IsolatedValue $s 'entrypoint'))
        }
        $expected=$template.services.PSObject.Properties[$name].Value
        $expectedEnv=Get-IsolatedValue $expected 'environment';$actualEnv=Get-IsolatedValue $s 'environment'
        if($null -ne $expectedEnv) {
            Assert-IsolatedFields $actualEnv @($expectedEnv.PSObject.Properties|ForEach-Object{$_.Name}) -Exact
            foreach($e in $expectedEnv.PSObject.Properties) {
                $want=[string]$e.Value
                foreach($key in $Context.Environment.Keys){$want=$want.Replace(('${'+$key+':?required}'),[string]$Context.Environment[$key])}
                Assert-True ($actualEnv.PSObject.Properties[$e.Name].Value -ceq $want)
            }
        } else {Assert-True ($null -eq $actualEnv)}
        $profiles=Get-IsolatedValue $s 'profiles';$wantProfiles=Get-IsolatedValue $expected 'profiles'
        Assert-True ((@($profiles)-join '|') -ceq (@($wantProfiles)-join '|'))
        $health=Get-IsolatedValue $s 'healthcheck';$wantHealth=Get-IsolatedValue $expected 'healthcheck'
        if($null -ne $wantHealth) {
            Assert-IsolatedFields $health @('test','interval','timeout','retries','start_period') -Exact
            Assert-True ((@($health.test)-join '|') -ceq (@($wantHealth.test)-join '|'))
            foreach($key in @('interval','timeout','retries','start_period')){Assert-True ($health.PSObject.Properties[$key].Value -ceq $wantHealth.PSObject.Properties[$key].Value)}
        } else {Assert-True ($null -eq $health)}
        $deps=Get-IsolatedValue $s 'depends_on'
        if($name -ceq 'data-service') {
            Assert-IsolatedFields $deps @('neo4j') -Exact
            Assert-IsolatedFields $deps.neo4j @('condition','required','restart')
            Assert-True ($deps.neo4j.condition -ceq 'service_healthy' -and -not (Get-IsolatedValue $deps.neo4j 'restart'))
        } else {Assert-True ($null -eq $deps)}
        Assert-True (@($s.volumes).Count -eq @($expected.volumes).Count)
        $seen=@{}
        foreach($mount in $s.volumes) {
            Assert-IsolatedFields $mount @('type','source','target','read_only','bind','volume')
            Assert-True (-not $seen.ContainsKey($mount.target));$seen[$mount.target]=$true
            $want=@($expected.volumes|Where-Object{$_.target -ceq $mount.target})
            Assert-True ($want.Count -eq 1 -and $want[0].type -ceq $mount.type)
            $want=$want[0]
            Assert-True ([bool](Get-IsolatedValue $mount 'read_only') -eq [bool](Get-IsolatedValue $want 'read_only'))
            if($mount.type -ceq 'bind') {
                Assert-True ($mount.read_only -eq $true)
                $source=[IO.Path]::GetFullPath($mount.source)
                $wantedSource=[IO.Path]::GetFullPath((Join-Path $Context.Root $want.source))
                Assert-True ($source.Equals($wantedSource,[StringComparison]::OrdinalIgnoreCase))
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
}
function Wait-RecoveryReady($Context) {
    for($i=0;$i -lt 40;$i++) {
        $r=Invoke-IsolatedProcess $Context.Docker (Get-IsolatedDockerArguments $Context @('compose','--env-file',(Join-Path $Context.Root 'support/empty-env.txt'),'--project-directory',$Context.Root,'--file',(Join-Path $Context.Root $Context.Compose),'--project-name',$Context.Project,'exec','-T','data-service','python','/app/recovery_probe.py','ready')) $Context.Root $Context.Environment 15 $Context.Deadline 1024
        if($r.Code -eq 0){return}
        Start-Sleep -Seconds 4
    }
    throw 'readiness failed'
}
function Invoke-RecoveryExercise([string]$Root,[string]$Output,$Job,$Report) {
    $stage='runtime-guard';$contexts=@();$active=New-Object 'Collections.Generic.List[object]';$success=$false;$cleanupOk=$true
    try {
        Assert-IsolatedRuntimeGuard ([Environment]::MachineName) ([Environment]::GetEnvironmentVariables())
        Assert-IsolatedLocalStorage $Root $Output $Root
        $deadline=[datetime]::UtcNow.AddMinutes(40)
        $envs=@{}
        foreach($key in @('NEO4J_PASSWORD','LLM_MASTER_SECRET','DG_SERVICE_TOKEN','DG_BOOTSTRAP_ADMIN_PASSWORD')){$envs[$key]=New-IsolatedSecret}
        $envs['RECOVERY_KEY']=(New-IsolatedSecret).Substring(0,64)
        $images=[pscustomobject]@{'neo4j'=$Job.images.neo4j;'data-service'=$Job.images.'data-service';'graph-admin'=$Job.images.neo4j;'snapshot'=$Job.images.'data-service'}
        $config=Join-Path $Output 'docker-config';[void][IO.Directory]::CreateDirectory($config)
        [IO.File]::WriteAllText((Join-Path $config 'config.json'),'{}')
        $files=@{};foreach($p in $Job.files.PSObject.Properties){$files[$p.Name]=$p.Value}
        foreach($file in @('source-compose.json','destination-compose.json')) {
            $contexts+=@{Root=$Root;Config=$config;Project=('dg-recovery-'+[guid]::NewGuid().ToString('N'));Compose=$file;
                Environment=$envs;Deadline=$deadline;Docker=(Get-Command docker.exe -CommandType Application -ErrorAction Stop).Source;
                Report=$Report;Images=$images;Files=$files}
        }
        $source=$contexts[0];$destination=$contexts[1]
        Assert-RecoveryPair $source.Project $destination.Project
        $stage='daemon-preflight'
        $version=Invoke-RecoveryDocker $source @('version','--format','{{json .}}')
        $info=Invoke-RecoveryDocker $source @('info','--format','{"OSType":{{json .OSType}},"Architecture":{{json .Architecture}},"MemTotal":{{json .MemTotal}}}')
        $cv=Invoke-RecoveryDocker $source @('compose','version','--short')
        Assert-IsolatedDaemon $version $info $cv
        foreach($p in $Job.images.PSObject.Properties) {
            $format='{"Id":{{json .Id}},"Os":{{json .Os}},"Architecture":{{json .Architecture}},"Revision":{{json (index .Config.Labels "org.opencontainers.image.revision")}}}'
            $image=(Invoke-RecoveryDocker $source @('image','inspect','--format',$format,$p.Value))|ConvertFrom-Json
            Confirm-IsolatedImage $image $p.Value $Job.sourceRevision
        }
        $Report.checks.daemonAndImages=$true
        $stage='compose-and-vacancy'
        foreach($c in $contexts) {
            $m=(Invoke-RecoveryCompose $c @('--profile','maintenance','config','--format','json') 30 262144)|ConvertFrom-Json
            Assert-RecoveryModel $m $c;Assert-RecoveryVacant $c
        }
        $Report.checks.isolationAndVacancy=$true
        $stage='source-start'
        $active.Add($source)
        # Maintenance containers only act on newly created, ownership-checked volumes.
        [void](Invoke-RecoveryCompose $source @('up','--detach','--no-build','--pull','never','--no-deps','graph-admin','snapshot'))
        [void](Assert-RecoveryOwnership $source)
        [void](Invoke-RecoveryCompose $source @('exec','-T','graph-admin','chmod','0777','/exchange'))
        [void](Invoke-RecoveryCompose $source @('up','--detach','--no-build','--pull','never','neo4j','data-service') 240)
        Wait-RecoveryReady $source
        $stage='seed'
        $seed=Invoke-RecoveryCompose $source @('exec','-T','data-service','python','/app/recovery_probe.py','seed') 90 16384
        $Report.checks.seed=Confirm-RecoveryProbe ($seed|ConvertFrom-Json) 'seed'
        $stage='quiesce'
        [void](Invoke-RecoveryCompose $source @('stop','--timeout','30','data-service','neo4j') 90)
        Assert-RecoveryStopped $source 'data-service';Assert-RecoveryStopped $source 'neo4j'
        $Report.checks.writersStopped=$true
        $stage='native-dump'
        [void](Invoke-RecoveryCompose $source @('exec','-T','graph-admin','neo4j-admin','database','dump','neo4j','--to-path=/exchange') 180)
        $Report.checks.nativeDump=$true
        $stage='seal'
        [void](Invoke-RecoveryCompose $source @('exec','-T','snapshot','python','/app/recovery_snapshot.py','seal','--state','/state','--exchange','/exchange') 90)
        Assert-RecoveryCipherName 'backup.enc'
        $cipher=Join-Path $Output 'backup.enc'
        $sid=Get-RecoveryContainer $source 'snapshot'
        [void](Invoke-RecoveryDocker $source @('cp',($sid+':/exchange/backup.enc'),$cipher) 90 0)
        Assert-RegularPath $cipher
        Assert-True ((Get-Item -LiteralPath $cipher).Length -gt 32 -and (Get-Item -LiteralPath $cipher).Length -le 190MB)
        $Report.backupSha256=Get-Hash $cipher
        $Report.backupBytes=(Get-Item -LiteralPath $cipher).Length
        [void](Invoke-RecoveryCompose $source @('stop','--timeout','15','graph-admin','snapshot') 45)
        Assert-RecoveryStopped $source 'graph-admin';Assert-RecoveryStopped $source 'snapshot'
        $stage='destination-helpers'
        $active.Add($destination)
        [void](Invoke-RecoveryCompose $destination @('up','--detach','--no-build','--pull','never','--no-deps','graph-admin','snapshot'))
        [void](Assert-RecoveryOwnership $destination)
        $did=Get-RecoveryContainer $destination 'snapshot'
        [void](Invoke-RecoveryDocker $destination @('cp',$cipher,($did+':/exchange/backup.enc')) 90 0)
        $hash=Invoke-RecoveryCompose $destination @('exec','-T','snapshot','python','-c','import hashlib;print(hashlib.sha256(open("/exchange/backup.enc","rb").read()).hexdigest())')
        Assert-True ($hash -ceq $Report.backupSha256)
        $Report.checks.ciphertextCopiedAndVerified=$true
        $stage='negative-restore'
        [void](Invoke-RecoveryCompose $destination @('exec','-T','snapshot','python','/app/recovery_snapshot.py','check-negative','--state','/state','--exchange','/exchange') 90)
        $Report.checks.wrongKeyAndCorruptionDenied=$true
        $stage='restore-files'
        [void](Invoke-RecoveryCompose $destination @('exec','-T','snapshot','python','/app/recovery_snapshot.py','open','--state','/state','--exchange','/exchange') 90)
        $stage='native-load'
        [void](Invoke-RecoveryCompose $destination @('exec','-T','graph-admin','neo4j-admin','database','load','neo4j','--from-path=/exchange') 180)
        [void](Invoke-RecoveryCompose $destination @('exec','-T','graph-admin','chown','-R','neo4j:neo4j','/data','/logs'))
        $Report.checks.nativeLoad=$true
        $stage='destination-start'
        [void](Invoke-RecoveryCompose $destination @('up','--detach','--no-build','--pull','never','neo4j','data-service') 240)
        Wait-RecoveryReady $destination
        $stage='semantic-verify'
        $verified=Invoke-RecoveryCompose $destination @('exec','-T','data-service','python','/app/recovery_probe.py','verify') 90 16384
        $Report.checks.restore=Confirm-RecoveryProbe ($verified|ConvertFrom-Json) 'verify'
        # Source remains stopped, with its original volumes never overwritten.
        Assert-RecoveryStopped $source 'data-service';Assert-RecoveryStopped $source 'neo4j'
        $Report.checks.sourceStillStopped=$true
        $success=$true
    } catch { $Report.failureStage=$stage }
    finally {
        foreach($c in $active) {
            try {
                $c.Deadline=[datetime]::UtcNow.AddMinutes(3)
                $cleanupStage='ownership'
                [void](Assert-RecoveryOwnership $c)
                $cleanupStage='down'
                [void](Invoke-RecoveryCompose $c @('--profile','maintenance','down','--volumes','--remove-orphans','--timeout','20') 90)
                $cleanupStage='vacancy'
                Assert-RecoveryVacant $c
            } catch {$cleanupOk=$false;$Report.cleanupFailureStage=$cleanupStage}
        }
        foreach($c in $contexts){$c.Environment.Clear()}
    }
    $Report.cleanup=if($active.Count -eq 0){'not-started'}elseif($cleanupOk){'owned-projects-volumes-removed'}else{'FAILED'}
    $Report.checks.cleanupVerified=($active.Count -gt 0 -and $cleanupOk)
    if(-not $cleanupOk -and $null -eq $Report.failureStage){$Report.failureStage='cleanup'}
    if($success -and $cleanupOk) {
        $Report.status='TWO_STORE_RECOVERY_COMPLETE';$Report.failureStage=$null
    } else { throw 'recovery exercise failed' }
}
function Confirm-RecoveryProbe($Value,[string]$Mode) {
    Assert-True ($Mode -cin @('seed','verify'))
    $prefix=if($Mode -ceq 'verify'){'seed_'}else{''}
    $booleans=@('admin_login','user_login','membership_restored','project_isolation','revoked_session_denied','llm_settings_decrypted',($prefix+'csrf_denied'))
    $counts=@(($prefix+'projects_created'),($prefix+'authenticated_ingests'),'neo4j_scoped_notes')
    Assert-IsolatedFields $Value ($booleans+$counts) -Exact
    $safe=[ordered]@{}
    foreach($key in $booleans) {
        $v=$Value.PSObject.Properties[$key].Value
        Assert-True ($v -is [bool] -and $v);$safe[$key]=$true
    }
    foreach($key in $counts) {
        $v=$Value.PSObject.Properties[$key].Value
        Assert-True (($v -is [int] -or $v -is [long]) -and $v -eq 2);$safe[$key]=2
    }
    return $safe
}
