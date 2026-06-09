#!/usr/bin/env bash
# Full PostgreSQL backup for Lambda runtime (spotify_curator).
# Writes to ~/spotify-curator-runtime/backups/ by default.
set -euo pipefail

CONTAINER="${POSTGRES_CONTAINER:-spotify-curator-postgres-1}"
DB_USER="${POSTGRES_USER:-spotify}"
DB_NAME="${POSTGRES_DB:-spotify_curator}"
OUT_DIR="${1:-$HOME/spotify-curator-runtime/backups}"
STAMP=$(date -u +%Y%m%dT%H%M%SZ)

mkdir -p "$OUT_DIR"
DUMP="$OUT_DIR/spotify_curator_${STAMP}.dump"
SQL="$OUT_DIR/spotify_curator_${STAMP}.sql.gz"
CHECKSUM="$OUT_DIR/spotify_curator_${STAMP}.sha256"

echo "Backing up $DB_NAME from $CONTAINER..."
docker exec "$CONTAINER" pg_dump -U "$DB_USER" -Fc -Z6 "$DB_NAME" > "$DUMP"
docker exec "$CONTAINER" pg_dump -U "$DB_USER" --no-owner --no-acl "$DB_NAME" | gzip -6 > "$SQL"
sha256sum "$DUMP" "$SQL" > "$CHECKSUM"

echo "Done."
ls -lh "$DUMP" "$SQL" "$CHECKSUM"
