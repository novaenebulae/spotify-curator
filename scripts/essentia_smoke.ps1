Param(
  [string]$OutDir = "logs/essentia-smoke",
  [string]$Profile = "profiles/essentia_lowlevel_full.yaml"
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$image = "ghcr.io/mtg/essentia:bullseye-v2.1_beta5"

New-Item -ItemType Directory -Force -Path $OutDir | Out-Null

$wavPath = Join-Path $OutDir "test.wav"
$jsonPath = Join-Path $OutDir "features.json"

python scripts\\generate_test_wav.py --out $wavPath | Out-Null

docker pull $image | Out-Null

$mountPath = (Resolve-Path $OutDir).Path
$profilePath = Join-Path $PSScriptRoot ".." $Profile
if (!(Test-Path $profilePath)) {
  throw "Profile not found: $profilePath"
}
$profileMount = (Resolve-Path $profilePath).Path
$profileInContainer = "/profiles/$(Split-Path $profilePath -Leaf)"

docker run --rm `
  -v "${mountPath}:/work" `
  -v "${profileMount}:${profileInContainer}:ro" `
  $image `
  bash -lc "essentia_streaming_extractor_music /work/test.wav /work/features.json ${profileInContainer}"

if (!(Test-Path $jsonPath)) {
  throw "Essentia output not found at $jsonPath"
}

$json = Get-Content $jsonPath -Raw | ConvertFrom-Json
if (-not $json.rhythm.bpm) {
  throw "Expected rhythm.bpm in Essentia output"
}

Write-Host "OK: $jsonPath (profile=$Profile, bpm=$($json.rhythm.bpm))"

