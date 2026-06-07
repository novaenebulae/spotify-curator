#!/usr/bin/env bash
# LEGACY — restore an existing SQLite archive onto Lambda SSD.
# Not used in the main workflow (empty DB + Spotify OAuth import on Lambda).
# See docs/20-lambda-gpu-cloud-analysis.md §16.
set -euo pipefail

if [[ $# -lt 1 ]]; then
  echo "Usage: $0 <path-to-spotify-curator-lambda-input.tar.gz>" >&2
  exit 1
fi

ARCHIVE="$1"
ROOT="/lambda/nfs/persistent-storage/spotify-curator"
DEST_DB="/home/ubuntu/spotify-curator-runtime/data/spotify_curator.sqlite"
MODELS_DST="/lambda/nfs/persistent-storage/spotify-curator/models"

cd "$ROOT"
tar -xzf "$ARCHIVE"

if [[ -f export-lambda/data/app.sqlite ]]; then
  cp export-lambda/data/app.sqlite "$DEST_DB"
elif [[ -f export-lambda/data/spotify_curator.sqlite ]]; then
  cp export-lambda/data/spotify_curator.sqlite "$DEST_DB"
else
  echo "No SQLite file found under export-lambda/data/" >&2
  exit 1
fi

if [[ -d export-lambda/models ]]; then
  cp -a export-lambda/models/. "$MODELS_DST/"
fi

sqlite3 "$DEST_DB" "PRAGMA integrity_check;"
echo "Restored database to $DEST_DB"
