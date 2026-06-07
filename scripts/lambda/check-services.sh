#!/usr/bin/env bash
# Health checks for Lambda stack (run on the instance after make lambda-up-a100).
# Requires tunnel from PC for UI/OAuth testing — API/frontend bind 127.0.0.1 on the VM.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
cd "$ROOT"

COMPOSE=(docker compose -f docker-compose.yml -f docker-compose.gpu.yml -f docker-compose.lambda.yml --env-file .env.lambda --profile audio --profile advanced-analysis --profile lambda-ui)

fail=0

echo "Checking API http://127.0.0.1:8000/api/v1/health ..."
if curl -fsS "http://127.0.0.1:8000/api/v1/health" >/dev/null; then
  echo "API OK"
else
  echo "API FAILED" >&2
  fail=1
fi

echo "Checking frontend http://127.0.0.1:5173 ..."
if curl -fsS "http://127.0.0.1:5173" >/dev/null; then
  echo "Frontend OK"
else
  echo "Frontend FAILED (is --profile lambda-ui active?)" >&2
  fail=1
fi

echo "Checking workers API ..."
if curl -fsS "http://127.0.0.1:8000/api/v1/workers" | grep -q essentia_tensorflow; then
  echo "TensorFlow worker heartbeat visible"
else
  echo "TensorFlow worker heartbeat not found (worker may still be starting)" >&2
fi

echo "Checking TensorFlow GPU in container ..."
if "${COMPOSE[@]}" run --rm -e REQUIRE_GPU=false essentia-tensorflow-worker \
  uv run python scripts/lambda/check_tf_gpu.py; then
  echo "TensorFlow GPU check script OK"
else
  echo "TensorFlow GPU check FAILED" >&2
  fail=1
fi

exit "$fail"
