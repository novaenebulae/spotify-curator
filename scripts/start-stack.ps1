Param(
  [switch]$Build,
  [switch]$Down,
  [switch]$Logs,
  [string]$EnvFile = ".env"
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$root = Split-Path $PSScriptRoot -Parent
Set-Location $root

if (-not (Test-Path $EnvFile)) {
  if (Test-Path ".env.example") {
    Copy-Item ".env.example" $EnvFile
    Write-Host "Created $EnvFile from .env.example"
  } else {
    throw "Missing $EnvFile and .env.example"
  }
}

function Get-EnvValue {
  param([string]$Name, [string]$Default)
  foreach ($line in Get-Content $EnvFile) {
    if ($line -match "^\s*${Name}\s*=\s*(.+)\s*$") {
      return $Matches[1].Trim()
    }
  }
  return $Default
}

$downloadWorkers = Get-EnvValue "AUDIO_DOWNLOAD_WORKERS" "2"
$lowlevelWorkers = Get-EnvValue "ESSENTIA_LOWLEVEL_WORKERS" "2"
$tfWorkers = Get-EnvValue "ESSENTIA_TENSORFLOW_WORKERS" "2"

if ($Down) {
  docker compose --profile audio --profile advanced-analysis down
}

$composeArgs = @(
  "compose",
  "--profile", "audio",
  "--profile", "advanced-analysis",
  "up", "-d",
  "--scale", "audio-downloader=$downloadWorkers",
  "--scale", "essentia-lowlevel-worker=$lowlevelWorkers",
  "--scale", "essentia-tensorflow-worker=$tfWorkers"
)

if ($Build) {
  $composeArgs += "--build"
}

Write-Host "Starting stack: download=$downloadWorkers lowlevel=$lowlevelWorkers tensorflow=$tfWorkers"
& docker @composeArgs

if ($Logs) {
  docker compose logs -f core-api
}
