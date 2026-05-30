# One-time copy of SQLite from ./data into Docker named volume spotify_curator_data.
# Run from repo root: .\scripts\migrate-sqlite-to-docker-volume.ps1

$ErrorActionPreference = "Stop"
$RepoRoot = Split-Path -Parent $PSScriptRoot
Set-Location $RepoRoot

$DbName = "spotify_curator.sqlite"
$HostDb = Join-Path (Join-Path $RepoRoot "data") $DbName

if (-not (Test-Path $HostDb)) {
    Write-Error "Missing $HostDb. Place the SQLite file in data/ first."
}

Write-Host "Stopping core-api (if running)..."
$prevEap = $ErrorActionPreference
$ErrorActionPreference = "Continue"
docker compose stop core-api 2>&1 | Out-Null
$ErrorActionPreference = $prevEap

Write-Host "Ensuring Docker volume spotify_curator_data exists..."
$ErrorActionPreference = "Continue"
docker volume inspect spotify_curator_data 2>&1 | Out-Null
if ($LASTEXITCODE -ne 0) {
    docker volume create spotify_curator_data 2>&1 | Out-Null
}
$ErrorActionPreference = $prevEap

Write-Host "Copying database files from data/ into volume..."
$CopyCmd = 'for f in spotify_curator.sqlite spotify_curator.sqlite-wal spotify_curator.sqlite-shm; do if [ -f /host/$f ]; then cp -f /host/$f /app/data/$f && echo copied $f; fi; done; ls -la /app/data'
docker run --rm -v "${RepoRoot}/data:/host:ro" -v spotify_curator_data:/app/data alpine:3.20 sh -c $CopyCmd
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Write-Host ""
Write-Host "Done. Start the stack with: docker compose up -d --build"
Write-Host "Host copy unchanged: data\$DbName"
Write-Host "Benchmark: cd core; uv run python scripts/benchmark_tracks.py --base-url http://127.0.0.1:8765 --runs 5"
