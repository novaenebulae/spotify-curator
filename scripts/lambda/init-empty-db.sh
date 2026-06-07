#!/usr/bin/env bash
# Initialize an empty Spotify Curator SQLite database on Lambda SSD.
# Uses core-api migrations (same path as application startup).
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
cd "$ROOT"

RUNTIME_ROOT="${RUNTIME_ROOT:-/home/ubuntu/spotify-curator-runtime}"
BACKUP_DIR="${BACKUP_DIR:-/lambda/nfs/persistent-storage/spotify-curator/backups}"
DEST_DB="${RUNTIME_ROOT}/data/spotify_curator.sqlite"

FORCE=0
BACKUP_EXISTING=0

usage() {
  echo "Usage: $0 [--force] [--backup-existing]" >&2
  echo "  Creates ${DEST_DB} via Alembic migrations (docker compose run core-api)." >&2
  echo "  Refuses to overwrite an existing database unless --force or --backup-existing." >&2
  exit 1
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --force)
      FORCE=1
      shift
      ;;
    --backup-existing)
      BACKUP_EXISTING=1
      shift
      ;;
    -h|--help)
      usage
      ;;
    *)
      echo "Unknown option: $1" >&2
      usage
      ;;
  esac
done

if [[ ! -f .env.lambda ]]; then
  echo "Missing .env.lambda — copy from .env.lambda.example first." >&2
  exit 1
fi

mkdir -p "${RUNTIME_ROOT}/data" "${RUNTIME_ROOT}/logs" "${RUNTIME_ROOT}/temp-audio"

if [[ "${RUNTIME_ROOT}" == "/home/ubuntu/spotify-curator-runtime" ]]; then
  bash scripts/lambda/prepare-runtime.sh
fi

if [[ -f "$DEST_DB" ]]; then
  if [[ "$BACKUP_EXISTING" -eq 1 ]]; then
    mkdir -p "$BACKUP_DIR"
    TS="$(date +%Y%m%d-%H%M%S)"
    cp "$DEST_DB" "${BACKUP_DIR}/spotify_curator.${TS}.sqlite"
    echo "Backed up existing database to ${BACKUP_DIR}/spotify_curator.${TS}.sqlite"
    rm -f "$DEST_DB" "${DEST_DB}-wal" "${DEST_DB}-shm"
  elif [[ "$FORCE" -eq 1 ]]; then
    rm -f "$DEST_DB" "${DEST_DB}-wal" "${DEST_DB}-shm"
    echo "Removed existing database (--force)."
  else
    echo "Database already exists: $DEST_DB" >&2
    echo "Use --backup-existing to archive it, or --force to replace it." >&2
    exit 1
  fi
fi

if [[ "${SKIP_DOCKER_INIT:-}" == "1" ]]; then
  echo "SKIP_DOCKER_INIT=1 — skipping migration container (test mode)."
  exit 0
fi

COMPOSE=(
  docker compose
  -f docker-compose.yml
  -f docker-compose.gpu.yml
  -f docker-compose.lambda.yml
  --env-file .env.lambda
)

echo "Running database migrations via core-api..."
"${COMPOSE[@]}" run --rm --no-deps core-api \
  uv run python -c "from app.database.init_db import init_db; init_db()"

if [[ ! -f "$DEST_DB" ]]; then
  echo "Expected database file was not created: $DEST_DB" >&2
  exit 1
fi

if ! command -v sqlite3 >/dev/null 2>&1; then
  echo "sqlite3 not found on host — skipping PRAGMA integrity_check." >&2
else
  echo "Running PRAGMA integrity_check..."
  sqlite3 "$DEST_DB" "PRAGMA integrity_check;"
fi

echo "Empty database ready: $DEST_DB"
