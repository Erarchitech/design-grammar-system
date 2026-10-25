#requires -Version 5.1
# Function-only orchestration boundary; never self-authorize or run on import.
# Latent executable mechanics are below. No reviewed physical/app profile ships.
# No declaration or callback grants provenance; public admission remains closed.
function Get-MultiReviewedProfile($Root,$Job,$Scope) {
    # Future admission must be a static exact-package reviewed binding, including
    # Linux age/keygen, app fixture, producer barrier and physical queue catalogs.
    # There is intentionally no user-selected path, callback or override flag.
    throw 'multi-store native contract unavailable'
}
function Invoke-MultiStoreExercise {
    param([string]$Root,[string]$Output,$Job,$Scope,$Report)
    $contexts=@();$stage='queue-profile-unqualified'
    try {
        Assert-True ($null -ne $Job -and $null -ne $Job.PSObject.Properties['queueQualification'])
        $qualification=$Job.queueQualification
        Assert-True ($null -ne $qualification)
        Assert-IsolatedFields $qualification @('status','nativeApplicationExecutionAllowed') -Exact
        Assert-True ($qualification.status -is [string] -and $qualification.status -ceq 'QUALIFIED')
        Assert-True ($qualification.nativeApplicationExecutionAllowed -is [bool] -and $qualification.nativeApplicationExecutionAllowed)
        $stage='reviewed-native-contract-unavailable'
        $profile=Get-MultiReviewedProfile $Root $Job $Scope
        $stage='host-tool-daemon-images'
        $contexts=@(New-MultiContexts $Root $Output $Job $Scope $Report)
        Assert-MultiHost $contexts[0] $Job
        foreach($context in $contexts) {
            $stage='compose-model'
            $model=(Invoke-MultiCompose $context @('--profile','maintenance','config','--format','json') 30 1048576)|ConvertFrom-Json
            Assert-MultiModel $model $context
            $stage='vacancy';Assert-MultiVacant $context
        }
        foreach($context in $contexts) {
            $context.CleanupActivated=$true
            Start-MultiStores $context
        }
        $stage='six-tree-exercise'
        Invoke-MultiLatentFlow $contexts[0] $contexts[1] $profile $Output $Report
        $Report.status='LATENT_FLOW_COMPLETE_NOT_RELEASE'
    } catch {
        if($null -eq $Report.failureStage){$Report.failureStage=$stage}
        $Report.status='FAILED'
        throw 'multi-store exercise blocked'
    } finally {
        $Report.releaseAccepted=$false;$Report.fullRecoveryAccepted=$false
        if($contexts.Count -gt 0){Complete-MultiCleanup $contexts $Report}
        if($null -ne $Report.failureStage){$Report.status='FAILED'}
    }
}
function Get-MultiContainer($Context,[string]$Service,[bool]$Running) {
    Assert-True ($Service -cin $Context.Services -and $Context.Images.ContainsKey($Service))
    $id=Invoke-MultiCompose $Context @('ps','--all','--quiet',$Service) 15 1024
    Assert-True ($id -cmatch '^[0-9a-f]{64}$')
    $format='{"Id":{{json .Id}},"Image":{{json .Image}},"Project":{{json (index .Config.Labels "com.docker.compose.project")}},"Service":{{json (index .Config.Labels "com.docker.compose.service")}},"Running":{{json .State.Running}}}'
    $record=(Invoke-MultiDocker $Context @('container','inspect','--format',$format,$id) 15 4096)|ConvertFrom-Json
    Assert-MultiContainerRecord $Context $Service $record $Running
    $isolationFormat='{"Id":{{json .Id}},"Image":{{json .Image}},"Name":{{json .Name}},"Config":{"Labels":{{json .Config.Labels}},"User":{{json .Config.User}}},"HostConfig":{{json .HostConfig}},"NetworkSettings":{{json .NetworkSettings}},"Mounts":{{json .Mounts}}}'
    $isolation=(Invoke-MultiDocker $Context @('container','inspect','--format',$isolationFormat,$id) 15 131072)|ConvertFrom-Json
    Assert-MultiContainerIsolation $Context $Service $isolation
    return $id
}
function Assert-MultiContainerIsolation($Context,[string]$Service,$Record) {
    Assert-True ($Context.Images.ContainsKey($Service) -and $Record.Image -ceq $Context.Images[$Service])
    Assert-True ($Record.Id -cmatch '^[0-9a-f]{64}$' -and $Record.Name -ceq ('/'+$Context.Project+'-'+$Service+'-1'))
    Assert-True ($Record.Config.Labels.'com.docker.compose.project' -ceq $Context.Project -and $Record.Config.Labels.'com.docker.compose.service' -ceq $Service)
    $model=Get-Content -LiteralPath (Join-Path $Context.Root $Context.Compose) -Raw -Encoding UTF8|ConvertFrom-Json
    $expected=$model.services.PSObject.Properties[$Service].Value
    $hostConfig=$Record.HostConfig
    Assert-True ($hostConfig.Privileged -is [bool] -and -not $hostConfig.Privileged)
    foreach($field in @('CapAdd','Devices','ExtraHosts')){Assert-True (@($hostConfig.PSObject.Properties[$field].Value).Count -eq 0)}
    Assert-True ($hostConfig.PidMode -ceq '' -and $hostConfig.IpcMode -cin @('','private'))
    foreach($bindings in @($hostConfig.PortBindings,$Record.NetworkSettings.Ports)) {
        if($null -ne $bindings){foreach($property in $bindings.PSObject.Properties){Assert-True ($null -eq $property.Value -or @($property.Value).Count -eq 0)}}
    }
    if((Get-IsolatedValue $expected 'network_mode') -ceq 'none') {
        Assert-True ($hostConfig.NetworkMode -ceq 'none')
        Assert-IsolatedFields $Record.NetworkSettings.Networks @() -Exact
    } else {
        Assert-True ($hostConfig.NetworkMode -ceq ($Context.Project+'_sandbox'))
        Assert-IsolatedFields $Record.NetworkSettings.Networks @($Context.Project+'_sandbox') -Exact
    }
    $wanted=@($expected.volumes)
    Assert-True (@($Record.Mounts).Count -eq $wanted.Count)
    $seen=@{}
    foreach($mount in $Record.Mounts) {
        Assert-True (-not $seen.ContainsKey($mount.Destination));$seen[$mount.Destination]=$true
        $want=@($wanted|Where-Object{$_.target -ceq $mount.Destination});Assert-True ($want.Count -eq 1);$want=$want[0]
        Assert-True ($mount.Type -ceq $want.type -and $mount.RW -is [bool] -and $mount.RW -ne [bool](Get-IsolatedValue $want 'read_only'))
        if($mount.Type -ceq 'volume'){Assert-True ($mount.Name -ceq ($Context.Project+'_'+$want.source))}
        else {
            Assert-True ($mount.Type -ceq 'bind' -and -not $mount.RW)
            $path=[IO.Path]::GetFullPath((Join-Path $Context.Root $want.source))
            Assert-True ([IO.Path]::GetFullPath($mount.Source).Equals($path,[StringComparison]::OrdinalIgnoreCase))
        }
    }
}
function Invoke-MultiExec($Context,[string]$Service,[string[]]$Command,[int]$Seconds=30,[int]$Limit=16384) {
    [void](Get-MultiContainer $Context $Service $true)
    Assert-True ($Command.Count -gt 0)
    return Invoke-MultiCompose $Context (@('exec','-T',$Service)+$Command) $Seconds $Limit
}
function Assert-MultiStopped($Context) {
    # Verify application writer services exited after compose stop.
    # AppServices is optional; when absent, no per-service verification.
    $services=if($Context.ContainsKey('AppServices')){@($Context.AppServices)}else{@()}
    foreach($service in $services){[void](Get-MultiContainer $Context $service $false)}
}
function New-MultiContexts($Root,[string]$Output,$Job,$Scope,$Report) {
    # Isolated docker configs; no host env leak; shared budget across both contexts.
    $docker=(Get-Command docker.exe -CommandType Application -ErrorAction Stop).Source
    Assert-True ($null -ne $Scope -and $Scope.maxSeconds -is [int] -and $Scope.maxCommands -is [int])
    $deadline=[datetime]::UtcNow.AddSeconds($Scope.maxSeconds)
    $shared=@{Commands=0;MaxCommands=$Scope.maxCommands;Deadline=$deadline}
    $contexts=@();$env=@{}
    foreach($key in @('NEO4J_PASSWORD','POSTGRES_PASSWORD','MINIO_ROOT_USER','MINIO_ROOT_PASSWORD','SPECKLE_SESSION_SECRET','LLM_MASTER_SECRET','DG_SERVICE_TOKEN','DG_BOOTSTRAP_ADMIN_PASSWORD','N8N_ENCRYPTION_KEY')) {
        $env[$key]=New-IsolatedSecret
    }
    foreach($side in @('source','destination')) {
        $name='dg-multi-'+[guid]::NewGuid().ToString('N')
        $compose=$side+'-compose.json'
        $model=Get-Content -LiteralPath (Join-Path $Root $compose) -Raw -Encoding UTF8|ConvertFrom-Json
        $services=@($model.services.PSObject.Properties|ForEach-Object{$_.Name})
        $volumes=@($model.volumes.PSObject.Properties|ForEach-Object{$_.Name})
        $images=@{}
        foreach($service in $services) {
            $image=$model.services.PSObject.Properties[$service].Value.image
            Assert-True ($image -is [string] -and $image -cmatch '^sha256:[0-9a-f]{64}$')
            $images[$service]=$image
        }
        $cfg=Join-Path $Output ($side+'-config')
        $ccfg=Join-Path $Output ($side+'-compose-config')
        foreach($d in @($cfg,$ccfg)) {
            Assert-True (-not (Test-Path -LiteralPath $d))
            [void][IO.Directory]::CreateDirectory($d)
        }
        [IO.File]::WriteAllText((Join-Path $cfg 'config.json'),'{}',(New-Object Text.UTF8Encoding($false)))
        $plugin=[IO.Path]::GetFullPath((Join-Path (Split-Path -Parent $docker) '..\cli-plugins'))
        $pluginConfig=@{cliPluginsExtraDirs=@($plugin)}|ConvertTo-Json -Compress
        [IO.File]::WriteAllText((Join-Path $ccfg 'config.json'),$pluginConfig,(New-Object Text.UTF8Encoding($false)))
        $ctx=@{Side=$side;Root=$Root;Docker=$docker;Config=$cfg;ComposeConfig=$ccfg;
               Project=$name;Compose=$compose;Services=$services;Volumes=$volumes;
               Images=$images;Environment=$env.Clone();
               Commands=0;MaxCommands=$Scope.maxCommands;Deadline=$deadline;
               SharedBudget=$shared;Report=$Report;CleanupActivated=$false}
        $contexts+=$ctx
    }
    Assert-MultiPair $contexts[0].Project $contexts[1].Project
    return $contexts
}
function Assert-MultiHost($Context,$Job) {
    # Exact host name; daemon OS/arch/memory; compose version; declared image cache.
    Assert-True ([Environment]::MachineName -ceq 'DESKTOP-OS4Q8CP')
    $version=(Invoke-MultiDocker $Context @('version','--format','{{json .}}') 20 65536)
    $info=(Invoke-MultiDocker $Context @('info','--format','{"OSType":{{json .OSType}},"Architecture":{{json .Architecture}},"MemTotal":{{json .MemTotal}}}') 20 4096)
    $composeVer=(Invoke-MultiDocker $Context @('compose','version','--short') 20 1024)
    Assert-IsolatedDaemon $version $info $composeVer
    $Context.Report.checks.daemonPreflight=$true
    Assert-MultiImageCache $Context
}
function Assert-MultiImageCache($Context) {
    Assert-True ($Context.Images -is [hashtable] -and $Context.Images.Count -gt 0)
    foreach($name in @($Context.Images.Keys|Sort-Object)) {
        $imageId=$Context.Images[$name]
        Assert-True ($imageId -is [string] -and $imageId -cmatch '^sha256:[0-9a-f]{64}$')
        $id=Invoke-MultiDocker $Context @('image','inspect','--format','{{.Id}}',$imageId) 20 1024
        Assert-True ($id -is [string] -and $id -ceq $imageId)
    }
    $Context.Report.checks.imageCacheVerified=$true
}
function Get-MultiWriterServices {
    return @('neo4j','dg-reasoner','data-service','design-grammars','n8n','speckle-server','speckle-frontend-2','speckle-preview-service','speckle-webhook-service','speckle-ifc-import-service','speckle-ingress')
}
function Start-MultiStores($Context) {
    # Start containers without image build or pull; then verify snapshot container readiness.
    $arguments=@('--profile','maintenance','up','--detach','--no-build','--pull','never')
    if($Context.Side -ceq 'destination') {
        # Destination state volumes must stay virgin: application writers (n8n, data-service,
        # Speckle, Neo4j) are never created there, so restore targets are provably empty.
        # Restore helpers refuse a non-empty destination rather than clearing it.
        $writers=@(Get-MultiWriterServices)
        $stores=@($Context.Services|Where-Object{$writers -cnotcontains $_})
        Assert-True ($stores.Count -gt 0 -and ($stores -ccontains 'snapshot'))
        $arguments+=@('--no-deps')+$stores
    }
    [void](Invoke-MultiCompose $Context $arguments 240 0)
    $ready=$false
    for($i=0;$i -lt 24 -and -not $ready;$i++){
        try{
            $r=(Invoke-MultiExec $Context 'snapshot' @('python','-B','/opt/recovery/multistore_exchange.py','hash','--source','/opt/recovery/multistore_exchange.py') 10 1024)|ConvertFrom-Json
            if($r.verified -is [bool] -and $r.verified){$ready=$true}
        }catch{}
        if(-not $ready){Start-Sleep -Seconds 5}
    }
    Assert-True $ready
    $Context.Report.checks.storeReadiness=$true
}
function Wait-MultiQueueBarrier($Context,$Profile) {
    Assert-True ($Profile.QueueSampleSeconds -is [int] -and $Profile.QueueSampleSeconds -ge 2 -and $Profile.QueueSampleSeconds -le 10)
    $fingerprints=@()
    for($i=0;$i -lt 4;$i++) {
        $sample=(Invoke-MultiExec $Context 'snapshot' @('python','-B','/opt/recovery/multistore_qualified_queue.py','sample') 30 65536)|ConvertFrom-Json
        Assert-True ($sample.schemaMatched -is [bool] -and $sample.schemaMatched)
        Assert-True ($sample.drained -is [bool] -and $sample.drained)
        Assert-True ($sample.fingerprint -is [string] -and $sample.fingerprint -cmatch '^[0-9a-f]{64}$')
        $fingerprints+=$sample.fingerprint
        if($i -lt 3){Start-Sleep -Seconds $Profile.QueueSampleSeconds}
    }
    Assert-True ($fingerprints[-1] -ceq $fingerprints[-2] -and $fingerprints[-2] -ceq $fingerprints[-3])
}
function Stop-MultiWriters($Context) {
    $writers=@(Get-MultiWriterServices)
    foreach($service in $writers){Assert-True ($service -cin $Context.Services)}
    [void](Invoke-MultiCompose $Context (@('stop','--timeout','20')+$writers) 90 0)
    foreach($service in $writers){[void](Get-MultiContainer $Context $service $false)}
}
function Invoke-MultiPg($Context,[string]$Tool,[string[]]$Arguments) {
    Assert-True ($Tool -cin @('psql','pg_dump','pg_restore'))
    # Fixed script, never interpolate a secret or untrusted identifier into SQL/argv.
    $script='umask 077; export PGHOST=127.0.0.1 PGPORT=5432 PGDATABASE=speckle PGUSER=speckle; export PGPASSWORD="$POSTGRES_PASSWORD"; exec "$@"'
    return Invoke-MultiExec $Context 'speckle-postgres' (@('/bin/sh','-c',$script,'pg-tool',('/usr/local/bin/'+$Tool))+$Arguments) 180 0
}
function Export-MultiPostgres($Context) {
    # capture=0 discards stdout; it does NOT bound psql --output files. No
    # qualified kernel limit or byte-stream transport with remote-child cleanup
    # is available in this model. Refuse before even creating SQL/output files.
    throw 'PostgreSQL private output production unavailable: hard byte bound and container-child cleanup unqualified'
    [void](Invoke-MultiExec $Context 'snapshot' @('python','-B','/opt/recovery/multistore_speckle.py','postgres-sql','--directory','/exchange/run/sql/pg') 30 65536)
    [void](Invoke-MultiPg $Context 'psql' @('-X','--no-password','-qAt','-v','ON_ERROR_STOP=1','--dbname=speckle','--file=/exchange/run/sql/pg/snapshot.sql','--output=/exchange/run/exports/postgres/source.json'))
    [void](Invoke-MultiPg $Context 'pg_dump' @('--format=custom','--no-password','--no-owner','--no-privileges','--dbname=speckle','--file=/exchange/run/exports/postgres/speckle.dump'))
    [void](Invoke-MultiPg $Context 'psql' @('-X','--no-password','-qAt','-v','ON_ERROR_STOP=1','--dbname=speckle','--file=/exchange/run/sql/pg/snapshot.sql','--output=/exchange/run/reports/postgres-source-after.json'))
    [void](Invoke-MultiExec $Context 'snapshot' @('python','-B','/opt/recovery/multistore_exchange.py','equal','--source','/exchange/run/exports/postgres/source.json','--destination','/exchange/run/reports/postgres-source-after.json') 30 65536)
}
function Restore-MultiPostgres($Context) {
    # Refuse before empty.sql/pg_restore: do not modify a destination that cannot
    # subsequently be verified under the required hard private-output contract.
    throw 'PostgreSQL private output production unavailable: hard byte bound and container-child cleanup unqualified'
    [void](Invoke-MultiExec $Context 'snapshot' @('python','-B','/opt/recovery/multistore_speckle.py','postgres-sql','--directory','/exchange/run/sql/pg') 30 65536)
    [void](Invoke-MultiPg $Context 'psql' @('-X','--no-password','-qAt','-v','ON_ERROR_STOP=1','--dbname=speckle','--file=/exchange/run/sql/pg/empty.sql'))
    [void](Invoke-MultiPg $Context 'pg_restore' @('--exit-on-error','--single-transaction','--no-password','--no-owner','--no-privileges','--dbname=speckle','/exchange/run/restored/postgres/speckle.dump'))
    [void](Invoke-MultiPg $Context 'psql' @('-X','--no-password','-qAt','-v','ON_ERROR_STOP=1','--dbname=speckle','--file=/exchange/run/sql/pg/snapshot.sql','--output=/exchange/run/reports/postgres-destination.json'))
    [void](Invoke-MultiExec $Context 'snapshot' @('python','-B','/opt/recovery/multistore_exchange.py','equal','--source','/exchange/run/restored/postgres/source.json','--destination','/exchange/run/reports/postgres-destination.json') 30 65536)
}
function Open-MultiArchive($Context,$Profile,$Seal) {
    Assert-True ($Seal.sha256 -is [string] -and $Seal.sha256 -cmatch '^[0-9a-f]{64}$')
    $common=@('--archive','/exchange/run/inbox/archive.age','--identity-file','/exchange/run/keys/identity.txt','--archive-sha256',$Seal.sha256,'--age','/opt/tools/age','--age-sha256',$Profile.AgeSha256,'--work','/exchange/run/work')
    $negative=(Invoke-MultiExec $Context 'snapshot' (@('python','-B','/opt/recovery/multistore_archive.py','negative')+$common+@('--wrong-identity-file','/exchange/run/keys/wrong-identity.txt','--destination','/exchange/run/negative-sentinel')) 600 65536)|ConvertFrom-Json
    foreach($field in @('positiveControl','badKeyRejectedBeforeDestination','corruptCiphertextRejectedBeforeDestination','sourceCiphertextUnchanged')) {
        $value=$negative.PSObject.Properties[$field].Value
        Assert-True ($value -is [bool] -and $value)
    }
    $opened=(Invoke-MultiExec $Context 'snapshot' (@('python','-B','/opt/recovery/multistore_archive.py','open')+$common+@('--destination','/exchange/run/restored')) 600 65536)|ConvertFrom-Json
    Assert-True ($opened.nativeRecoveryProven -is [bool] -and -not $opened.nativeRecoveryProven)
}
function Copy-MultiFile($Source,$Destination,[string]$From,[string]$To,[string]$Output,[string]$Name) {
    # Synthetic exercise file via the runner's private output directory, then hash-verified
    # on both sides. Never used for real keys or retained custody material.
    $staged=Join-Path $Output $Name
    [void](Invoke-MultiDocker $Source @('cp',($Source.Project+'-snapshot-1:'+$From),$staged) 60 0)
    [void](Invoke-MultiDocker $Destination @('cp',$staged,($Destination.Project+'-snapshot-1:'+$To)) 60 0)
    $before=(Invoke-MultiExec $Source 'snapshot' @('python','-B','/opt/recovery/multistore_exchange.py','hash','--source',$From) 30 65536)|ConvertFrom-Json
    $after=(Invoke-MultiExec $Destination 'snapshot' @('python','-B','/opt/recovery/multistore_exchange.py','hash','--source',$To) 30 65536)|ConvertFrom-Json
    Assert-True ($before.sha256 -is [string] -and $before.sha256 -cmatch '^[0-9a-f]{64}$' -and $after.sha256 -is [string] -and $after.sha256 -ceq $before.sha256)
}
function Invoke-MultiLatentFlow($Source,$Destination,$Profile,$Output,$Report) {
    # Latent six-tree orchestration. Guarded from native admission: Get-MultiReviewedProfile
    # must have succeeded before this is reached in the main exercise flow.
    # No native acceptance is granted here; nativeRecoveryProven remains false throughout.

    # Phase 1: Source exchange init. Exclusive mkdir inside the snapshot container.
    $init=(Invoke-MultiExec $Source 'snapshot' @('python','-B','/opt/recovery/multistore_exchange.py','init','--root','/exchange/run') 30 65536)|ConvertFrom-Json
    Assert-True ($init.verified -is [bool] -and $init.verified)

    # Phase 2: App seed via qualified app helper. Absent profile/helper blocks here.
    $seed=(Invoke-MultiExec $Source 'snapshot' @('python','-B','/opt/recovery/multistore_qualified_app.py','seed') 120 65536)|ConvertFrom-Json
    Assert-True ($seed.verified -is [bool] -and $seed.verified)

    # Phase 3: Block external and scheduled producers before quiescence probe.
    $block=(Invoke-MultiExec $Source 'snapshot' @('python','-B','/opt/recovery/multistore_qualified_app.py','block-producers') 60 65536)|ConvertFrom-Json
    Assert-True ($block.producerBarrier -is [bool] -and $block.producerBarrier)

    # Drain with consumers running, then keep only storage and maintenance alive.
    Wait-MultiQueueBarrier $Source $Profile
    Stop-MultiWriters $Source
    # A stopped app cannot produce; take a new timed stable empty pair after stop.
    Wait-MultiQueueBarrier $Source $Profile

    # Phase 6: Source full snapshots. Application database, not standalone fixture.
    Export-MultiPostgres $Source
    # 6c: Neo4j full graph dump via graph-admin container.
    [void](Invoke-MultiExec $Source 'graph-admin' @('neo4j-admin','database','dump','neo4j','--to-path=/exchange/run/exports/neo4j') 180 0)
    # 6d: MinIO all-objects export via sibling helper in snapshot service.
    [void](Invoke-MultiExec $Source 'snapshot' @('python','-B','/opt/recovery/multistore_native.py','export-objects','--directory','/exchange/run/exports/minio/objects') 120 65536)
    # 6e: n8n full SQLite tree and decrypted credential export.
    [void](Invoke-MultiExec $Source 'snapshot' @('python','-B','/opt/recovery/multistore_exchange.py','call','--helper','multistore_n8n','--stdout-file','/exchange/run/reports/n8n-source.json','--','snapshot','--tree','/n8n-state/.n8n','--package','/exchange/run/exports/n8n/package','--key-reference','ephemeral-exercise-only','--version','2.4.8','--key-file','/exchange/run/keys/n8n.key','--scratch','/exchange/run/work','--fixture-state','/exchange/run/n8n-fixture/fixture-state.json','--decrypted-export','/exchange/run/reports/n8n-decrypted-source.json') 300 65536)
    # 6f: Preserve the complete stopped API tree beside the app fixture state.
    [void](Invoke-MultiExec $Source 'snapshot' @('python','-B','/opt/recovery/multistore_exchange.py','tree','--source','/state','--destination','/exchange/run/exports/api/state') 300 65536)

    # Phase 7: Seal six-tree archive with age. Linux age executable pinned by SHA256.
    $seal=(Invoke-MultiExec $Source 'snapshot' @('python','-B','/opt/recovery/multistore_archive.py','seal','--source','/exchange/run/exports','--recipient-file','/exchange/run/keys/recipient.txt','--destination','/exchange/run/sealed','--age','/opt/tools/age','--age-sha256',$Profile.AgeSha256,'--work','/exchange/run/work') 600 65536)|ConvertFrom-Json
    Assert-True ($seal.sha256 -is [string] -and $seal.sha256 -cmatch '^[0-9a-f]{64}$')

    # Phase 8: Copy ciphertext — source container → private host path → destination container.
    # Only the ciphertext (never plaintext) leaves the source volume.
    $init=(Invoke-MultiExec $Destination 'snapshot' @('python','-B','/opt/recovery/multistore_exchange.py','init','--root','/exchange/run') 30 65536)|ConvertFrom-Json
    Assert-True ($init.verified -is [bool] -and $init.verified)
    $hostArchive=Join-Path $Output 'archive.age'
    [void](Invoke-MultiDocker $Source @('cp',($Source.Project+'-snapshot-1:/exchange/run/sealed/archive.age'),$hostArchive) 60 0)
    [void](Invoke-MultiDocker $Destination @('cp',$hostArchive,($Destination.Project+'-snapshot-1:/exchange/run/inbox/archive.age')) 60 0)

    # Phase 9: Both negative controls and authenticated extraction must succeed
    # before any native restore command sees the extracted tree.
    Open-MultiArchive $Destination $Profile $seal

    # Phase 10: Destination PG — pristine check, restore, full-state comparison.
    Restore-MultiPostgres $Destination

    # Phase 11: Destination Neo4j load.
    [void](Invoke-MultiExec $Destination 'graph-admin' @('neo4j-admin','database','load','neo4j','--from-path=/exchange/run/restored/neo4j') 180 0)

    # Phase 11b: MinIO objects. speckle-server (which would create the bucket) never starts on the
    # destination, so create it explicitly; an existing bucket fails closed. restore-objects then
    # refuses any non-empty bucket.
    $bucket=(Invoke-MultiExec $Destination 'snapshot' @('python','-B','/opt/recovery/multistore_native.py','create-bucket') 60 65536)|ConvertFrom-Json
    Assert-True ($bucket.verified -is [bool] -and $bucket.verified)
    $objects=(Invoke-MultiExec $Destination 'snapshot' @('python','-B','/opt/recovery/multistore_native.py','restore-objects','--directory','/exchange/run/restored/minio/objects') 300 65536)|ConvertFrom-Json
    Assert-True ($objects.verified -is [bool] -and $objects.verified)

    # Phase 11c: API state tree into the (empty, writer-free) destination volume root.
    $api=(Invoke-MultiExec $Destination 'snapshot' @('python','-B','/opt/recovery/multistore_exchange.py','restore-tree','--source','/exchange/run/restored/api/state','--destination','/state') 300 65536)|ConvertFrom-Json
    Assert-True ($api.verified -is [bool] -and $api.verified)

    # Phase 11d: n8n. The expected observation and the exercise key are retained by this runner
    # (never taken from the archive) and hash-verified after transfer. Synthetic data only.
    $n8n=@(
        @('/exchange/run/reports/n8n-source.json','/exchange/run/inbox/n8n-expected.json','n8n-expected.json'),
        @('/exchange/run/keys/n8n.key','/exchange/run/inbox/n8n.key','n8n.key'),
        @('/exchange/run/n8n-fixture/fixture-state.json','/exchange/run/inbox/n8n-fixture-state.json','n8n-fixture-state.json'),
        @('/exchange/run/reports/n8n-decrypted-source.json','/exchange/run/inbox/n8n-decrypted-source.json','n8n-decrypted-source.json'))
    foreach($item in $n8n){Copy-MultiFile $Source $Destination $item[0] $item[1] $Output $item[2]}
    $n8nCommon=@('--key-reference','ephemeral-exercise-only','--version','2.4.8','--key-file','/exchange/run/inbox/n8n.key','--scratch','/exchange/run/work','--fixture-state','/exchange/run/inbox/n8n-fixture-state.json','--decrypted-export','/exchange/run/inbox/n8n-decrypted-source.json')
    $restored=(Invoke-MultiExec $Destination 'snapshot' (@('python','-B','/opt/recovery/multistore_exchange.py','call','--helper','multistore_n8n','--stdout-file','/exchange/run/reports/n8n-destination-restore.json','--','restore','--package','/exchange/run/restored/n8n/package','--destination','/n8n-state/.n8n','--expected','/exchange/run/inbox/n8n-expected.json')+$n8nCommon) 300 65536)|ConvertFrom-Json
    Assert-True ($restored.treeRestored -is [bool] -and $restored.treeRestored)
    $matched=(Invoke-MultiExec $Destination 'snapshot' (@('python','-B','/opt/recovery/multistore_exchange.py','call','--helper','multistore_n8n','--stdout-file','/exchange/run/reports/n8n-destination-verify.json','--','verify','--tree','/n8n-state/.n8n','--expected','/exchange/run/inbox/n8n-expected.json')+$n8nCommon) 300 65536)|ConvertFrom-Json
    Assert-True ($matched.restoredStateMatched -is [bool] -and $matched.restoredStateMatched)

    # Phase 12: Post-restore destination verify via qualified app helper.
    $verify=(Invoke-MultiExec $Destination 'snapshot' @('python','-B','/opt/recovery/multistore_qualified_app.py','verify') 180 65536)|ConvertFrom-Json
    Assert-True ($verify.verified -is [bool] -and $verify.verified)

    $Report.checks.latentFlowComplete=$true
}
