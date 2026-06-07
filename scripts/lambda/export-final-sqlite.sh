#!/usr/bin/env bash
set -euo pipefail

SRC="${SQLITE_PATH:-/home/ubuntu/spotify-curator-runtime/data/spotify_curator.sqlite}"
ROOT="/lambda/nfs/persistent-storage/spotify-curator"
OUT_DIR="$ROOT/final-output"
OUT_DB="$OUT_DIR/app.sqlite"
ARCHIVE="$ROOT/spotify-curator-lambda-output.tar.gz"

mkdir -p "$OUT_DIR"

sqlite3 "$SRC" "PRAGMA wal_checkpoint(FULL);"
sqlite3 "$SRC" "PRAGMA integrity_check;"

cp "$SRC" "$OUT_DB"
cp "$SRC" "$OUT_DIR/spotify_curator.sqlite"

cd "$ROOT"
tar -czf "$ARCHIVE" final-output

echo "Exported: $OUT_DB"
echo "Archive: $ARCHIVE"
