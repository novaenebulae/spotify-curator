#!/usr/bin/env bash
# Quick Docker + NVIDIA sanity check on the Lambda host.
set -euo pipefail

echo "=== groups (expect docker) ==="
groups

echo "=== docker ps ==="
docker ps

echo "=== nvidia-smi in TF worker image ==="
ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
cd "$ROOT"
docker compose -f docker-compose.yml -f docker-compose.gpu.yml -f docker-compose.lambda.yml \
  --env-file .env.lambda --profile advanced-analysis \
  run --rm essentia-tensorflow-worker nvidia-smi
