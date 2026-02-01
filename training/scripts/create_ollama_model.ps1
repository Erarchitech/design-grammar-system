param(
  [Parameter(Mandatory=$true)]
  [string]$AdapterDir,

  [Parameter(Mandatory=$true)]
  [string]$BaseModel,

  [Parameter(Mandatory=$true)]
  [string]$ModelName,

  [string]$OllamaHost = "http://localhost:11435",
  [string]$HfToken = $env:HF_TOKEN,
  [string]$ConfigUrl = "https://huggingface.co/meta-llama/Llama-3.1-8B-Instruct/resolve/main/config.json",
  [string]$TokenizerModelUrl = "https://huggingface.co/meta-llama/Llama-3.1-8B-Instruct/resolve/main/tokenizer.model",
  [string]$TokenizerJsonUrl = "https://huggingface.co/meta-llama/Llama-3.1-8B-Instruct/resolve/main/tokenizer.json",
  [string]$TokenizerConfigUrl = "https://huggingface.co/meta-llama/Llama-3.1-8B-Instruct/resolve/main/tokenizer_config.json"
)

$ErrorActionPreference = "Stop"

$adapterPath = Resolve-Path $AdapterDir
$adapterDirFull = $adapterPath.Path

$adapterConfig = Join-Path $adapterDirFull "adapter_config.json"
if (-not (Test-Path $adapterConfig)) {
  throw "Missing adapter_config.json in $adapterDirFull"
}

$adapterModel = Join-Path $adapterDirFull "adapter_model.safetensors"
if (-not (Test-Path $adapterModel)) {
  $candidates = Get-ChildItem -Path $adapterDirFull -Filter "*.safetensors" | Select-Object -First 1
  if (-not $candidates) {
    throw "No .safetensors adapter file found in $adapterDirFull"
  }
  $adapterModel = $candidates.FullName
}

$configJson = Join-Path $adapterDirFull "config.json"
$tokenizerModel = Join-Path $adapterDirFull "tokenizer.model"
$tokenizerJson = Join-Path $adapterDirFull "tokenizer.json"
$tokenizerConfig = Join-Path $adapterDirFull "tokenizer_config.json"
$useBasicParsing = $PSVersionTable.PSVersion.Major -lt 6
if ((-not (Test-Path $configJson)) -or ((Get-Item $configJson).Length -eq 0)) {
  if (-not $HfToken) {
    throw "config.json missing and HF_TOKEN not set. Set HF_TOKEN or pass -HfToken."
  }
  Write-Host "Downloading config.json from Hugging Face..."
  $iwrParams = @{
    Uri = $ConfigUrl
    Headers = @{ Authorization = "Bearer $HfToken" }
    OutFile = $configJson
  }
  if ($useBasicParsing) {
    $iwrParams.UseBasicParsing = $true
  }
  Invoke-WebRequest @iwrParams
}

if ((-not (Test-Path $tokenizerModel)) -or ((Get-Item $tokenizerModel).Length -eq 0)) {
  if (-not $HfToken) {
    throw "tokenizer.model missing and HF_TOKEN not set. Set HF_TOKEN or pass -HfToken."
  }
  Write-Host "Downloading tokenizer.model from Hugging Face..."
  $tokParams = @{
    Uri = $TokenizerModelUrl
    Headers = @{ Authorization = "Bearer $HfToken" }
    OutFile = $tokenizerModel
  }
  if ($useBasicParsing) { $tokParams.UseBasicParsing = $true }
  try {
    Invoke-WebRequest @tokParams
  } catch {
    Write-Warning "Failed to download tokenizer.model, falling back to tokenizer.json/config."
  }
}

if ((-not (Test-Path $tokenizerModel)) -or ((Get-Item $tokenizerModel).Length -eq 0)) {
  foreach ($pair in @(@{Path=$tokenizerJson; Url=$TokenizerJsonUrl}, @{Path=$tokenizerConfig; Url=$TokenizerConfigUrl})) {
    if ((-not (Test-Path $pair.Path)) -or ((Get-Item $pair.Path).Length -eq 0)) {
      Write-Host "Downloading $(Split-Path $pair.Path -Leaf) from Hugging Face..."
      $tokParams = @{
        Uri = $pair.Url
        Headers = @{ Authorization = "Bearer $HfToken" }
        OutFile = $pair.Path
      }
      if ($useBasicParsing) { $tokParams.UseBasicParsing = $true }
      Invoke-WebRequest @tokParams
    }
  }
}

function Upload-Blob($path) {
  $hash = (Get-FileHash -Algorithm SHA256 $path).Hash.ToLower()
  $url = "$OllamaHost/api/blobs/sha256:$hash"
  $uploadParams = @{
    Method = "Post"
    Uri = $url
    InFile = $path
    ContentType = "application/octet-stream"
  }
  if ($useBasicParsing) {
    $uploadParams.UseBasicParsing = $true
  }
  Invoke-WebRequest @uploadParams | Out-Null
  return "sha256:$hash"
}

$files = @{
  "adapter_model.safetensors" = (Upload-Blob $adapterModel)
  "adapter_config.json" = (Upload-Blob $adapterConfig)
  "config.json" = (Upload-Blob $configJson)
}
if ((Test-Path $tokenizerModel) -and ((Get-Item $tokenizerModel).Length -gt 0)) {
  $files["tokenizer.model"] = (Upload-Blob $tokenizerModel)
} else {
  if ((Test-Path $tokenizerJson) -and ((Get-Item $tokenizerJson).Length -gt 0)) {
    $files["tokenizer.json"] = (Upload-Blob $tokenizerJson)
  }
  if ((Test-Path $tokenizerConfig) -and ((Get-Item $tokenizerConfig).Length -gt 0)) {
    $files["tokenizer_config.json"] = (Upload-Blob $tokenizerConfig)
  }
}

$modelfile = "FROM $BaseModel`nADAPTER adapter_model.safetensors`n"

$body = @{
  name = $ModelName
  modelfile = $modelfile
  files = $files
} | ConvertTo-Json -Depth 4

Write-Host "Creating Ollama model '$ModelName'..."
Invoke-RestMethod -Method Post -Uri "$OllamaHost/api/create" -ContentType "application/json" -Body $body
