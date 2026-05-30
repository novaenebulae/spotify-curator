#!/usr/bin/env sh
# One-time copy of SQLite from ./data into Docker named volume spotify_curator_data.
# Run from repo root: sh scripts/migrate-sqlite-to-docker-volume.sh

set -e
cd "$(dirname "$0")/.."

DB=spotify_curator.sqlite
if [ ! -f "data/$DB" ]; then
  echo "Missing data/$DB" >&2
  exit 1
fi

echo "Stopping core-api (if running)..."
docker compose stop core-api 2>/dev/null || true

echo "Ensuring Docker volume spotify_curator_data exists..."
docker volume inspect spotify_curator_data >/dev/null 2>&1 \
  || docker volume create spotify_curator_data

echo "Copying database files into volume..."
docker run --rm \
  -v "$(pwd)/data:/host:ro" \
  -v spotify_curator_data:/app/data \
  alpine:3.20 \
  sh -c 'set -e
for f in spotify_curator.sqlite spotify_curator.sqlite-wal spotify_curator.sqlite-shm; do
  if [ -f "/host/$f" ]; then cp -f "/host/$f" "/app/data/$f"; echo "copied $f"; fi
done
ls -la /app/data'

echo ""
echo "Done. Start: docker compose up -d --build"
