param(
  [Parameter(Mandatory=$true)]
  [string]$AdapterDir,

  [Parameter(Mandatory=$true)]
  [string]$BaseModel,

  [Parameter(Mandatory=$true)]
  [string]$ModelName,

  [string]$MergedDir = "training/output/merged_hf",
  [string]$OllamaHost = "http://localhost:11435",
  [string]$HfToken = $env:HF_TOKEN,
  [string]$Quantize = "q4_K_M"
)

$ErrorActionPreference = "Stop"

if (-not $HfToken) {
  throw "HF_TOKEN is required to download base model files."
}

Write-Host "Merging adapter into base model (this can take a while)..."

docker compose -f training/docker-compose.train.yml run --rm trainer `
  python /workspace/training/merge_adapter.py `
  --base-model $BaseModel `
  --adapter-dir /workspace/$AdapterDir `
  --output-dir /workspace/$MergedDir `
  --hf-token $HfToken

$mergedPath = Resolve-Path $MergedDir
$mergedPathStr = $mergedPath.Path.Replace('\','/')

$modelfilePath = Join-Path $mergedPath.Path "Modelfile"
@" 
FROM $mergedPathStr
"@ | Set-Content -Encoding ASCII $modelfilePath

$env:OLLAMA_HOST = $OllamaHost

$quantizeArg = ""
if ($Quantize -and $Quantize -ne "none") {
  $quantizeArg = "--quantize $Quantize"
}

Write-Host "Creating Ollama model '$ModelName' (experimental safetensors import)..."
# Use cmd.exe to avoid PowerShell treating native stderr as terminating when ErrorActionPreference=Stop.
$createOutput = cmd /c "ollama create $ModelName -f `"$modelfilePath`" --experimental $quantizeArg 2>&1"
if ($LASTEXITCODE -ne 0 -and $createOutput -match "unknown flag: --experimental") {
  Write-Warning "Local Ollama client does not support --experimental. Falling back to container CLI."
  $containerHost = $OllamaHost -replace "localhost", "host.docker.internal"
  $containerHost = $containerHost -replace "127\.0\.0\.1", "host.docker.internal"
  $containerHost = $containerHost -replace "0\.0\.0\.0", "host.docker.internal"
  $containerModelfile = Join-Path $mergedPath.Path "Modelfile.container"
  @"
FROM /merged_hf
"@ | Set-Content -Encoding ASCII $containerModelfile

  $dockerArgs = @(
    "run", "--rm",
    "-v", "$($mergedPath.Path):/merged_hf",
    "-e", "OLLAMA_HOST=$containerHost",
    "ollama/ollama",
    "create", $ModelName,
    "-f", "/merged_hf/Modelfile.container",
    "--experimental"
  )
  if ($quantizeArg) {
    $dockerArgs += @("--quantize", $Quantize)
  }
  & docker @dockerArgs
} elseif ($LASTEXITCODE -ne 0) {
  throw $createOutput
}
