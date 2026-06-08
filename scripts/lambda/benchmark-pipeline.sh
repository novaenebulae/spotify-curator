#!/usr/bin/env bash
set -euo pipefail

LIMIT="${1:-20}"
# Host tunnel to Lambda API (core-api published as 127.0.0.1:8000 on the VM).
BASE_URL="${BASE_URL:-http://127.0.0.1:8000}"

ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
cd "$ROOT"

COMPOSE=(docker compose -f docker-compose.yml -f docker-compose.gpu.yml -f docker-compose.lambda.yml \
  --env-file .env.lambda --profile audio --profile advanced-analysis)

"${COMPOSE[@]}" exec -T core-api \
  uv run python scripts/benchmark_advanced_pipeline.py \
  --base-url http://127.0.0.1:8765 \
  --limit "$LIMIT" \
  --profile phase6-recommended
