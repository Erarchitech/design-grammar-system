#requires -Version 5.1
[CmdletBinding()]
param(
    [Parameter(Mandatory=$true)][string]$PackageDirectory,
    [Parameter(Mandatory=$true)][string]$PackageZip,
    [Parameter(Mandatory=$true)][string]$ReportDirectory
)
Set-StrictMode -Version Latest
$ErrorActionPreference='Stop'
# Read-only Docker diagnostics. No logs/config/env or raw native errors returned.
$expected='e430407e70a21af210a0a3d8816ca01f2fc8c54844b82dd879eb8a959e56b135'
if((Get-FileHash -LiteralPath $PackageZip -Algorithm SHA256).Hash.ToLowerInvariant() -cne $expected){throw 'issued ZIP required'}
Add-Type -AssemblyName System.IO.Compression.FileSystem
$zip=[IO.Compression.ZipFile]::OpenRead($PackageZip)
try {
    foreach($name in @('package-functions.ps1','runtime-functions.ps1')){
        $path=Join-Path $PackageDirectory ('support/'+$name)
        $stream=$zip.GetEntry('support/'+$name).Open();$hasher=[Security.Cryptography.SHA256]::Create()
        try{$hash=[BitConverter]::ToString($hasher.ComputeHash($stream)).Replace('-','').ToLowerInvariant()}
        finally{$stream.Dispose();$hasher.Dispose()}
        if((Get-FileHash -LiteralPath $path -Algorithm SHA256).Hash.ToLowerInvariant() -cne $hash){throw 'support mismatch'}
    }
} finally{$zip.Dispose()}
. (Join-Path $PackageDirectory 'support/package-functions.ps1')
. (Join-Path $PackageDirectory 'support/runtime-functions.ps1')
Assert-IsolatedRuntimeGuard ([Environment]::MachineName) ([Environment]::GetEnvironmentVariables())
$config=Join-Path $ReportDirectory 'docker-config'
Assert-RegularPath $config
Assert-True ((Get-Content -LiteralPath (Join-Path $config 'config.json') -Raw).Trim() -ceq '{}')
$context=@{Docker=(Get-Command docker.exe -CommandType Application -ErrorAction Stop).Source;Root=$PackageDirectory;Config=$config;Environment=@{};Deadline=[datetime]::UtcNow.AddMinutes(2);Report=@{dockerInvoked=$false}}
function Read-DiagnosticDocker([string[]]$Command){
    $r=Invoke-IsolatedDocker $context $Command 10 65536
    Assert-True ($r.Code -eq 0)
    return $r.Text
}
$result=[ordered]@{schemaVersion=1;kind='recovery-read-only-diagnostic';packageZipSha256=$expected;completed=$false;projects=@();containers=@();networks=@();volumes=@();failureSection=$null}
$section='project-list'
try{
    $projects=@()
    foreach($kind in @('container','network','volume')){
        $cmd=@($kind,'ls');if($kind -ceq 'container'){$cmd+='--all'}
        $format=if($kind -ceq 'container'){'{{.Label "com.docker.compose.project"}}'}else{'{{.Name}}'}
        $filter=if($kind -ceq 'container'){'label=com.docker.compose.project'}else{'name=^dg-recovery-'}
        $text=Read-DiagnosticDocker ($cmd+@('--filter',$filter,'--format',$format))
        foreach($line in ($text -split '\r?\n')){
            if($line -cmatch '^(dg-recovery-[0-9a-f]{32})(?:_(?:sandbox|graph|graph_logs|api_state|exchange))?$'){$projects+=$Matches[1]}
        }
    }
    $projects=@($projects|Sort-Object -Unique);Assert-True ($projects.Count -le 4)
    $result.projects=$projects
    foreach($project in $projects){
        foreach($kind in @('container','network','volume')){
            $section=$kind
            $cmd=@($kind,'ls');if($kind -ceq 'container'){$cmd+='--all'}
            $format=if($kind -ceq 'volume'){'{{.Name}}'}else{'{{.ID}}'}
            $text=Read-DiagnosticDocker ($cmd+@('--filter',('label=com.docker.compose.project='+$project),'--format',$format))
            $ids=@(($text -split '\r?\n')|Where-Object{$_});Assert-True ($ids.Count -le 8)
            foreach($id in $ids){
                Assert-True ($id -cmatch '^[a-zA-Z0-9][a-zA-Z0-9_.-]{0,127}$')
                if($kind -ceq 'container'){
                    $fmt='{"Owner":{{json (index .Config.Labels "com.docker.compose.service")}},"Image":{{json .Image}},"State":{{json .State.Status}},"Exit":{{json .State.ExitCode}},"Mounts":{{json .Mounts}}}'
                    $item=(Read-DiagnosticDocker @('container','inspect','--format',$fmt,$id))|ConvertFrom-Json
                    Assert-True ($item.Owner -cin @('neo4j','data-service','graph-admin','snapshot'))
                    Assert-True ($item.State -cin @('created','running','paused','restarting','removing','exited','dead'))
                    $mounts=@();foreach($m in $item.Mounts){
                        if($m.Type -ceq 'volume'){
                            $known=$m.Name -cin @(($project+'_graph'),($project+'_graph_logs'),($project+'_api_state'),($project+'_exchange'))
                            $anonymous=$m.Name -cmatch '^[0-9a-f]{64}$'
                            $target=if($m.Destination -cin @('/data','/logs','/state','/exchange','/app/data')){$m.Destination}else{'other'}
                            $mounts+=@{knownProjectVolume=[bool]$known;anonymousName=[bool]$anonymous;target=$target}
                        }
                    }
                    $want=if($item.Owner -cin @('neo4j','graph-admin')){'sha256:0efd832ad89fcc0526e80abf8b26bb79f196ebe87eac655c6f19c08c5be766b8'}else{'sha256:9787e347b10eb8303498fed9e79651b89a3a1d4f62501ee98e51f6f25d0b22d1'}
                    $result.containers+=@{project=$project;service=$item.Owner;state=$item.State;exitCode=[int]$item.Exit;imageMatches=[bool]($item.Image -ceq $want);volumes=$mounts}
                }else{
                    $fmt='{"Name":{{json .Name}},"Owner":{{json (index .Labels "com.docker.compose.'+$kind+'")}}}'
                    $item=(Read-DiagnosticDocker @($kind,'inspect','--format',$fmt,$id))|ConvertFrom-Json
                    $allowed=if($kind -ceq 'network'){@('sandbox')}else{@('graph','graph_logs','api_state','exchange')}
                    $owned=($item.Owner -cin $allowed -and $item.Name -ceq ($project+'_'+$item.Owner))
                    $entry=@{project=$project;expectedIdentity=[bool]$owned}
                    if($kind -ceq 'network'){$result.networks+=$entry}else{$result.volumes+=$entry}
                }
            }
        }
    }
    $result.completed=$true
}catch{$result.failureSection=$section}
ConvertTo-Json -InputObject $result -Depth 10
if(-not $result.completed){exit 1}
