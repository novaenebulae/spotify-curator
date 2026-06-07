#!/usr/bin/env bash
set -euo pipefail

SRC="${SQLITE_PATH:-/home/ubuntu/spotify-curator-runtime/data/spotify_curator.sqlite}"
DST_DIR="/lambda/nfs/persistent-storage/spotify-curator/backups"
TS="$(date +%Y%m%d-%H%M%S)"

mkdir -p "$DST_DIR"

sqlite3 "$SRC" "PRAGMA wal_checkpoint(FULL);"
sqlite3 "$SRC" "PRAGMA integrity_check;"

cp "$SRC" "$DST_DIR/app.${TS}.sqlite"

echo "Backup created: $DST_DIR/app.${TS}.sqlite"
