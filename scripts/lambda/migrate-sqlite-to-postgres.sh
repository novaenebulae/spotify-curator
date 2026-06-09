#!/usr/bin/env bash
# Migrate SQLite runtime DB to PostgreSQL (Lambda sidecar).
# Usage:
#   bash scripts/lambda/migrate-sqlite-to-postgres.sh \
#     /home/ubuntu/spotify-curator-runtime/data/spotify_curator.sqlite \
#     postgresql://spotify:spotify@localhost:5432/spotify_curator
set -euo pipefail

SQLITE_PATH="${1:-/home/ubuntu/spotify-curator-runtime/data/spotify_curator.sqlite}"
PG_URL="${2:-postgresql://spotify:spotify@127.0.0.1:5432/spotify_curator}"

if [[ ! -f "$SQLITE_PATH" ]]; then
  echo "SQLite file not found: $SQLITE_PATH" >&2
  exit 1
fi

echo "==> Stopping workers (keep postgres running if already up)"
cd "$(dirname "$0")/../.."
docker compose -f docker-compose.yml -f docker-compose.gpu.yml -f docker-compose.lambda.yml \
  --env-file .env.lambda --profile audio --profile advanced-analysis \
  stop audio-downloader preview-resolver-worker essentia-lowlevel-worker \
  essentia-tensorflow-worker pipeline-ticker-worker core-api 2>/dev/null || true

echo "==> Backup SQLite"
make lambda-backup

echo "==> Ensure Postgres is up"
docker compose -f docker-compose.yml -f docker-compose.gpu.yml -f docker-compose.lambda.yml \
  --env-file .env.lambda --profile postgres up -d postgres

for _ in $(seq 1 30); do
  if docker compose -f docker-compose.yml -f docker-compose.gpu.yml -f docker-compose.lambda.yml \
    --env-file .env.lambda --profile postgres exec -T postgres \
    pg_isready -U "${POSTGRES_USER:-spotify}" -d "${POSTGRES_DB:-spotify_curator}" >/dev/null 2>&1; then
    break
  fi
  sleep 2
done

echo "==> Reset Postgres schema (fresh Alembic)"
docker compose -f docker-compose.yml -f docker-compose.gpu.yml -f docker-compose.lambda.yml \
  --env-file .env.lambda --profile postgres exec -T postgres \
  psql -U "${POSTGRES_USER:-spotify}" -d "${POSTGRES_DB:-spotify_curator}" \
  -c "DROP SCHEMA public CASCADE; CREATE SCHEMA public;"
docker compose -f docker-compose.yml -f docker-compose.gpu.yml -f docker-compose.lambda.yml \
  --env-file .env.lambda --profile postgres run --rm \
  -e DATABASE_URL="postgresql+psycopg://${POSTGRES_USER:-spotify}:${POSTGRES_PASSWORD:-spotify}@postgres:5432/${POSTGRES_DB:-spotify_curator}" \
  core-api uv run alembic upgrade head

echo "==> Batch copy via Python (pgloader OOM on large DBs)"
# SQLite needs a writable directory for journal files; copy to /tmp inside the container.
docker compose -f docker-compose.yml -f docker-compose.gpu.yml -f docker-compose.lambda.yml \
  --env-file .env.lambda --profile postgres run --rm \
  -v "$(dirname "$SQLITE_PATH"):/host-data:ro" \
  core-api sh -c "cp /host-data/$(basename "$SQLITE_PATH") /tmp/migrate.sqlite && uv run python scripts/lambda/copy_sqlite_to_postgres.py \
  --sqlite-url sqlite:////tmp/migrate.sqlite \
  --postgres-url postgresql+psycopg://${POSTGRES_USER:-spotify}:${POSTGRES_PASSWORD:-spotify}@postgres:5432/${POSTGRES_DB:-spotify_curator}"

SQLITE_JI=$(sqlite3 "$SQLITE_PATH" "SELECT COUNT(*) FROM job_items;")
PG_JI=$(docker compose -f docker-compose.yml -f docker-compose.gpu.yml -f docker-compose.lambda.yml \
  --env-file .env.lambda --profile postgres exec -T postgres \
  psql -U "${POSTGRES_USER:-spotify}" -d "${POSTGRES_DB:-spotify_curator}" -tAc "SELECT COUNT(*) FROM job_items;")
echo "==> Verify job_items: sqlite=$SQLITE_JI postgres=$PG_JI"
if [[ "$SQLITE_JI" != "$PG_JI" ]]; then
  echo "ERROR: job_items count mismatch" >&2
  exit 1
fi

echo "==> Switching .env.lambda to Postgres"
if ! grep -q '^DATABASE_URL=postgresql' .env.lambda; then
  cp .env.lambda .env.lambda.sqlite.bak
  sed -i 's|^DATABASE_URL=sqlite:////app/data/spotify_curator.sqlite|DATABASE_URL=postgresql+psycopg://spotify:spotify@postgres:5432/spotify_curator|' .env.lambda
fi

echo "==> Starting Postgres worker profile"
make lambda-up-a10-stable-tf6-pg

echo "Done. Production now uses PostgreSQL (DATABASE_URL in .env.lambda)."
