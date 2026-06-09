#!/usr/bin/env bash
# Host-side full pipeline benchmark (no core-api container — avoids OOM on large jobs).
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
DURATION_SEC="${1:-300}"
INTERVAL_SEC="${2:-30}"
JOB_ID="${JOB_ID:-7d5cdb9ea98d4807bfa6068ce2408bd9}"
SQLITE_PATH="${SQLITE_PATH:-/home/ubuntu/spotify-curator-runtime/data/spotify_curator.sqlite}"

export SQLITE_PATH
exec python3 "${ROOT}/scripts/measure_full_pipeline_benchmark.py" \
  --job-id "$JOB_ID" \
  --sqlite-path "$SQLITE_PATH" \
  --duration-sec "$DURATION_SEC" \
  --interval-sec "$INTERVAL_SEC" \
  --label "${LABEL:-host-${DURATION_SEC}s}"
