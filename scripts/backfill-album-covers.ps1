# Backfill album covers using the core uv environment (not system Python).
$ErrorActionPreference = "Stop"
$RepoRoot = Split-Path -Parent $PSScriptRoot
Push-Location (Join-Path $RepoRoot "core")
try {
    uv run python scripts/backfill_album_covers.py @args
} finally {
    Pop-Location
}
