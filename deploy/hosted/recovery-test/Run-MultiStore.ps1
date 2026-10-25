#requires -Version 5.1
[CmdletBinding()]
param(
    [Parameter(Mandatory=$true)][string]$PackageZip,
    [Parameter(Mandatory=$true)][string]$ExpectedZipSha256,
    [Parameter(Mandatory=$true)][string]$OutputDirectory,
    [string]$ScopeJson='',
    [switch]$RunNativeMultiStore
)
Set-StrictMode -Version Latest
$ErrorActionPreference='Stop'
# Self-contained bootstrap: do NOT dot-source any extracted support before both
# independent ZIP pin and full ZIP/extraction/source checks have completed.
function Require($Value) {if(-not $Value){throw 'MULTISTORE_REJECTED'}}
function Hash([string]$Path) {return (Get-FileHash -LiteralPath $Path -Algorithm SHA256).Hash.ToLowerInvariant()}
function RegularPath([string]$Path) {
    Require ($Path -match '^[A-Za-z]:[\\/]')
    $current=[IO.Path]::GetFullPath($Path)
    while($current) {
        if(Test-Path -LiteralPath $current) {
            $item=Get-Item -LiteralPath $current -Force
            Require (-not ($item.Attributes -band [IO.FileAttributes]::ReparsePoint) -and -not $item.LinkType)
            $streams=@(Get-Item -LiteralPath $current -Force -Stream * -ErrorAction Stop)
            foreach($stream in $streams){Require ($stream.Stream -ceq ':$DATA')}
        }
        $parent=Split-Path -Parent $current
        if($parent -eq $current){break};$current=$parent
    }
}
function Member([string]$Name) {
    Require ($Name.Length -le 240 -and $Name -cmatch '^[A-Za-z0-9_./-]+$' -and -not $Name.StartsWith('/'))
    foreach($part in $Name.Split('/')) {
        Require ($part -and $part -notin @('.','..') -and $part -notmatch '[. ]$' -and $part -notmatch '^(?i:CON|PRN|AUX|NUL|COM[1-9]|LPT[1-9])(?:\.|$)')
    }
}
function ExactFields($Value,[string[]]$Names) {
    Require ($Value -is [pscustomobject] -and @($Value.PSObject.Properties).Count -eq $Names.Count)
    foreach($name in $Names){Require ($null -ne $Value.PSObject.Properties[$name] -and $Value.PSObject.Properties[$name].Name -ceq $name)}
}
function ExactMap($Actual,$Expected) {
    Require ($Actual.Count -eq @($Expected.PSObject.Properties).Count)
    foreach($p in $Expected.PSObject.Properties){Require ($Actual.ContainsKey($p.Name) -and @($Actual.Keys|Where-Object{$_ -ceq $p.Name}).Count -eq 1 -and $Actual[$p.Name] -ceq $p.Value)}
}
function PrivateDirectory([string]$Path) {
    $security=New-Object Security.AccessControl.DirectorySecurity
    $sid=[Security.Principal.WindowsIdentity]::GetCurrent().User
    $security.SetOwner($sid);$security.SetAccessRuleProtection($true,$false)
    $rule=New-Object Security.AccessControl.FileSystemAccessRule($sid,'FullControl','ContainerInherit,ObjectInherit','None','Allow')
    $security.AddAccessRule($rule)
    # Windows Framework overload applies DACL at creation, not after exposure.
    [void][IO.Directory]::CreateDirectory($Path,$security)
}
function Assert-Package([string]$Root,[string]$ZipPath,[string]$Expected) {
    RegularPath $Root;RegularPath $ZipPath
    Require ($Expected -cmatch '^[0-9a-f]{64}$' -and (Hash $ZipPath) -ceq $Expected)
    Require ((Get-Item -LiteralPath $ZipPath).Length -le 128000000)
    $mp=Join-Path $Root 'multistore-manifest.json';RegularPath $mp
    Require ((Get-Item -LiteralPath $mp).Length -le 2000000)
    $job=Get-Content -LiteralPath $mp -Raw -Encoding UTF8|ConvertFrom-Json
    ExactFields $job @('schemaVersion','kind','target','preparationBase','productRevision','sourceRevision','sourceFileCount','sourceManifestSha256','toolingStatus','toolPins','images','limits','budget','queueQualification','approval','ageTrust','files','preparationFiles')
    Require ($job.schemaVersion -is [int] -and $job.schemaVersion -eq 2 -and $job.kind -ceq 'isolated-full-multistore-native-candidate-not-release')
    Require ($job.target -ceq 'DESKTOP-OS4Q8CP' -and $job.preparationBase -ceq '535eb3020532a00f7405b02f0c791d8fe1b5522c')
    Require ($job.productRevision -ceq 'c82b92b29423c515e353e3fa4f9c17e9b0d83438' -and $job.sourceRevision -ceq $job.productRevision -and $job.sourceFileCount -is [int] -and $job.sourceFileCount -eq 187)
    Require ($job.sourceManifestSha256 -ceq '10bbde850bfc53fb9e924b76ebac1d8f7abfa20a84fe3cf77ed9a0d2c9b25eaf')
    Require ($job.toolingStatus -ceq 'separately-hashed-current-preparation-not-committed-product')
    ExactFields $job.ageTrust @('publisherEd25519LeafSignatureVerified','sigsumQuorumVerified','verificationEvidence','linuxExecuted','windowsHostToolOptional')
    Require ($job.ageTrust.verificationEvidence -ceq 'historical-pinned-report-not-reverified')
    foreach($name in @('publisherEd25519LeafSignatureVerified','windowsHostToolOptional')){Require ($job.ageTrust.$name -is [bool] -and $job.ageTrust.$name)}
    foreach($name in @('sigsumQuorumVerified','linuxExecuted')){Require ($job.ageTrust.$name -is [bool] -and -not $job.ageTrust.$name)}
    ExactFields $job.limits @('fileBytes','totalBytes','fileCount')
    Require ($job.limits.fileBytes -eq 32000000 -and $job.limits.totalBytes -eq 128000000 -and $job.limits.fileCount -eq 512)
    ExactFields $job.budget @('maxSeconds','maxCommands','cleanupSeconds','cleanupCommands')
    Require ($job.budget.maxSeconds -eq 5400 -and $job.budget.maxCommands -eq 500 -and $job.budget.cleanupSeconds -eq 300 -and $job.budget.cleanupCommands -eq 160)
    ExactFields $job.queueQualification @('status','nativeApplicationExecutionAllowed')
    Require ($job.queueQualification.status -ceq 'UNQUALIFIED' -and $job.queueQualification.nativeApplicationExecutionAllowed -is [bool] -and -not $job.queueQualification.nativeApplicationExecutionAllowed)
    $expectedFiles=@{}
    foreach($p in $job.files.PSObject.Properties) {
        Member $p.Name
        Require (-not $expectedFiles.ContainsKey($p.Name) -and $p.Value -is [string] -and $p.Value -cmatch '^[0-9a-f]{64}$')
        $expectedFiles[$p.Name]=$p.Value
    }
    Require (-not $expectedFiles.ContainsKey('multistore-manifest.json') -and $expectedFiles.Count -lt 512)
    $preparation=@{}
    foreach($name in $expectedFiles.Keys){if(-not $name.StartsWith('source/',[StringComparison]::Ordinal)){$preparation[$name]=$expectedFiles[$name]}}
    $supportNames=@('Run-MultiStore.ps1','Invoke-OwnerMultiStore.ps1','runtime-functions.ps1','multistore_execution.ps1','multistore_orchestrator.ps1','probe.py','smoke_probe.py','sandbox_probe.py','multistore_archive.py','multistore_native.py','multistore_n8n.py','multistore_speckle.py','multistore_exchange.py','speckle-source-binding.json','multistore_qualified_app.py','multistore_qualified_queue.py','speckle-physical-contract.json','recovery_checkpoint.py','recovery_filesystem.py','recovery_postgres.py','recovery_pg_init.py','recovery_objects.py','recovery_n8n.py','recovery_queues.py','recovery_bundle.py','recovery_sequence.py','recovery_transport.py','package-functions.ps1','empty-env.txt')
    $allowedPreparation=@($supportNames|ForEach-Object{'support/'+$_})+@('source-compose.json','destination-compose.json','tools/age','tools/age-keygen','tools/LICENSE','tools/windows/age.exe','tools/windows/age-keygen.exe','tools/windows/LICENSE','provenance/age/CONTRACT.md','provenance/age/signature-verification.json','provenance/age/download-provenance.json','provenance/age/extracted-tools.json','provenance/age/delivery-manifest.json','provenance/preparation/build_multistore_package.py','provenance/preparation/build_multistore_test.py','provenance/preparation/build_image_runtime.py','provenance/images/build-evidence.json','provenance/images/owner-observation.json','provenance/queues/unqualified-candidates.json')
    Require ($preparation.Count -eq $allowedPreparation.Count)
    foreach($name in $allowedPreparation){Require ($preparation.ContainsKey($name) -and @($preparation.Keys|Where-Object{$_ -ceq $name}).Count -eq 1)}
    ExactMap $preparation $job.preparationFiles
    $expectedFiles['multistore-manifest.json']=Hash $mp
    Add-Type -AssemblyName System.IO.Compression.FileSystem
    $zip=[IO.Compression.ZipFile]::OpenRead($ZipPath)
    try {
        Require ($zip.Entries.Count -eq $expectedFiles.Count -and $zip.Entries.Count -le 512)
        $members=@{};[long]$total=0
        foreach($entry in $zip.Entries) {
            Member $entry.FullName
            $total+=$entry.Length
            Require (-not $members.ContainsKey($entry.FullName) -and $entry.Length -le 32000000 -and $total -le 128000000)
            $bits=[BitConverter]::ToUInt32([BitConverter]::GetBytes([int]$entry.ExternalAttributes),0)
            Require ((($bits -shr 16) -band 61440) -in @(0,32768) -and ($bits -band 1040) -eq 0)
            $stream=$entry.Open();$hash=[Security.Cryptography.SHA256]::Create()
            try{$members[$entry.FullName]=[BitConverter]::ToString($hash.ComputeHash($stream)).Replace('-','').ToLowerInvariant()}
            finally{$stream.Dispose();$hash.Dispose()}
        }
        ExactMap $members ([pscustomobject]$expectedFiles)
    } finally{$zip.Dispose()}
    $actual=@{};[long]$total=0;$entries=0
    $pending=New-Object 'Collections.Generic.Stack[string]';$pending.Push($Root)
    while($pending.Count) {
        foreach($path in [IO.Directory]::EnumerateFileSystemEntries($pending.Pop())) {
            $entries++;Require ($entries -le 2048)
            RegularPath $path
            $item=Get-Item -LiteralPath $path -Force
            $name=$item.FullName.Substring($Root.Length+1).Replace([IO.Path]::DirectorySeparatorChar,'/')
            Member $name
            if($item.PSIsContainer) {
                Require (@($expectedFiles.Keys|Where-Object{$_.StartsWith($name+'/',[StringComparison]::Ordinal)}).Count -gt 0)
                $pending.Push($item.FullName)
            } else {
                $total+=$item.Length
                Require ($actual.Count -lt 512 -and $item.Length -le 32000000 -and $total -le 128000000 -and -not $actual.ContainsKey($name))
                $actual[$name]=Hash $item.FullName
            }
        }
    }
    ExactMap $actual ([pscustomobject]$expectedFiles)
    # Fixed pins are independent of rehashed manifest declarations. No bundled
    # executable or provenance script is imported to obtain these expectations.
    $agePins=@{
        'tools/age'='aaec874ed903da4b02a9d503778ae05ee5005b2acc0f4a4cf10e5d0f17fd4384'
        'tools/age-keygen'='50f849de5f05dc136de3dba623dd2b7e166e7badb9d4e3d83da88f2dbdb2d439'
        'tools/LICENSE'='32cc8df32709c059f3ee312dc088bae7ddb8b8adc1efdd2b6394cdcb8b6300c8'
        'tools/windows/age.exe'='5729bd8f90d5cdf0a69ccd10408f000877ad4ab4bec8e49f80fbd8bd15539cc7'
        'tools/windows/age-keygen.exe'='2c3ac6c083ee68458c39f1a61feaff8c4d754c44e236eaca54a026066a968cd4'
        'tools/windows/LICENSE'='32cc8df32709c059f3ee312dc088bae7ddb8b8adc1efdd2b6394cdcb8b6300c8'
        'provenance/age/CONTRACT.md'='a92ffe757c2aff2236b475a6106d1478ac40b3e3334aaa09277e514326255f67'
        'provenance/age/signature-verification.json'='d6d6921a52f794d262658a77e9fedf6fc3d1004642e6577123c49302d9cf287a'
        'provenance/age/download-provenance.json'='03943e1f455bba2b9133c81a424cee48e52d300a0b0ee021a7d2c37c18b4118b'
        'provenance/age/extracted-tools.json'='f8efa1bec4ee1fb96d8e5bf3eb127f84c107b9feb77f1fae4595ce4eadd30709'
    }
    foreach($name in $agePins.Keys){Require ($actual[$name] -ceq $agePins[$name])}
    $delivery=Get-Content -LiteralPath (Join-Path $Root 'provenance/age/delivery-manifest.json') -Raw -Encoding UTF8|ConvertFrom-Json
    ExactFields $delivery @('schemaVersion','kind','files','verificationEvidence')
    Require ($delivery.schemaVersion -is [int] -and $delivery.schemaVersion -eq 2 -and $delivery.kind -ceq 'current-package-age-inputs-not-historical-delivery')
    Require ($delivery.verificationEvidence -ceq 'historical-pinned-report-not-reverified')
    ExactMap $agePins $delivery.files
    $sp=Join-Path $Root 'source/manifest.json'
    Require ((Hash $sp) -ceq $job.sourceManifestSha256)
    $source=Get-Content -LiteralPath $sp -Raw -Encoding UTF8|ConvertFrom-Json
    Require ($source.frameworkRevision -ceq $job.preparationBase -and $source.productRevision -ceq $job.productRevision)
    $sourceFiles=@{}
    foreach($name in $actual.Keys){if($name.StartsWith('source/',[StringComparison]::Ordinal) -and $name -cne 'source/manifest.json'){$sourceFiles[$name.Substring(7)]=$actual[$name]}}
    Require ($sourceFiles.Count -eq 187);ExactMap $sourceFiles $source.files
    return $job
}
$root=[IO.Path]::GetFullPath((Split-Path -Parent $PSScriptRoot))
$stage='package-preflight';$outputOwned=$false
$report=[ordered]@{schemaVersion=1;kind='isolated-full-multistore-native-candidate-not-release';status='FAILED';failureStage=$null;dockerInvoked=$false;releaseAccepted=$false;fullRecoveryAccepted=$false;offMachineRestoreProven=$false;cleanup='not-started';cleanupFailureStage=$null;checks=[ordered]@{}}
try {
    RegularPath $OutputDirectory
    $output=[IO.Path]::GetFullPath($OutputDirectory)
    Require (-not (Test-Path -LiteralPath $output) -and (Test-Path -LiteralPath (Split-Path -Parent $output) -PathType Container))
    Require (-not $output.Equals($root,[StringComparison]::OrdinalIgnoreCase) -and -not $output.StartsWith($root+'\',[StringComparison]::OrdinalIgnoreCase) -and -not $root.StartsWith($output+'\',[StringComparison]::OrdinalIgnoreCase))
    PrivateDirectory $output;$outputOwned=$true
    $job=Assert-Package $root $PackageZip $ExpectedZipSha256
    $report.packageZipSha256=$ExpectedZipSha256;$report.sourceRevision=$job.productRevision;$report.preparationBase=$job.preparationBase;$report.checks.packageIntegrity=$true
    if($RunNativeMultiStore) {
        $stage='external-scope'
        Require ($ScopeJson -and $ScopeJson -match '^[A-Za-z]:[\\/]')
        $scopePath=[IO.Path]::GetFullPath($ScopeJson);RegularPath $scopePath
        Require (-not $scopePath.StartsWith($root+'\',[StringComparison]::OrdinalIgnoreCase) -and (Get-Item -LiteralPath $scopePath).Length -le 16384)
        $scope=Get-Content -LiteralPath $scopePath -Raw -Encoding UTF8|ConvertFrom-Json
        # Loading is now safe: all exact extracted bytes matched the pinned ZIP.
        . (Join-Path $PSScriptRoot 'package-functions.ps1')
        . (Join-Path $PSScriptRoot 'runtime-functions.ps1')
        . (Join-Path $PSScriptRoot 'multistore_execution.ps1')
        Assert-MultiScope $scope ([Environment]::MachineName) $ExpectedZipSha256 ([datetime]::UtcNow)
        $report.checks.externalScopeRecordValid=$true
        $stage='queue-profile-unqualified'
        # A scope record does NOT qualify unknown queue/schema profiles. Candidate
        # stays blocked before ANY Docker command or application execution.
        Require ($job.queueQualification.status -ceq 'QUALIFIED' -and $job.queueQualification.nativeApplicationExecutionAllowed -eq $true)
        . (Join-Path $PSScriptRoot 'multistore_orchestrator.ps1')
        $stage='native-multistore'
        Invoke-MultiStoreExercise $root $output $job $scope $report
        Require ($report.status -cne 'FAILED')
    } else {Require (-not $ScopeJson);$report.status='PACKAGE_PREFLIGHT_COMPLETE'}
} catch {
    if($null -eq $report.failureStage){$report.failureStage=$stage}
    $report.status='FAILED';[Console]::Error.WriteLine('MULTISTORE_FAILED: '+$report.failureStage)
}
if($outputOwned) {
    try {
        $bytes=(New-Object Text.UTF8Encoding($false)).GetBytes((ConvertTo-Json -InputObject $report -Depth 20))
        $stream=[IO.File]::Open((Join-Path $output 'multistore-report.json'),[IO.FileMode]::CreateNew,[IO.FileAccess]::Write,[IO.FileShare]::None)
        try{$stream.Write($bytes,0,$bytes.Length)}finally{$stream.Dispose()}
    } catch {[Console]::Error.WriteLine('MULTISTORE_REPORT_WRITE_FAILED');exit 1}
}
if($report.status -ceq 'FAILED'){exit 1};exit 0
