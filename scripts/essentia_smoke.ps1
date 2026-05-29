Param(
  [string]$OutDir = "logs/essentia-smoke"
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

docker run --rm `
  -v "${mountPath}:/work" `
  $image `
  bash -lc "essentia_streaming_extractor_music /work/test.wav /work/features.json"

if (!(Test-Path $jsonPath)) {
  throw "Essentia output not found at $jsonPath"
}

Write-Host "OK: $jsonPath"

