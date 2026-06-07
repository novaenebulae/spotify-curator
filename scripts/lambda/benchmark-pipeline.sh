#!/usr/bin/env bash
set -euo pipefail

LIMIT="${1:-20}"
BASE_URL="${BASE_URL:-http://127.0.0.1:8000}"

cd "$(dirname "$0")/../../core"
uv run python scripts/benchmark_advanced_pipeline.py \
  --base-url "$BASE_URL" \
  --limit "$LIMIT" \
  --profile phase6-recommended
