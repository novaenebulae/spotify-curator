#!/usr/bin/env bash
# Health checks for Lambda stack (run on the instance after make lambda-up-a100).
# API is required; frontend on the VM is optional (prefer local PC + SSH tunnel).
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
cd "$ROOT"

COMPOSE=(docker compose -f docker-compose.yml -f docker-compose.gpu.yml -f docker-compose.lambda.yml \
  --env-file .env.lambda --profile audio --profile advanced-analysis)

fail=0
CHECK_FRONTEND="${CHECK_FRONTEND:-1}"

echo "Checking API http://127.0.0.1:8000/api/v1/health ..."
if curl -fsS "http://127.0.0.1:8000/api/v1/health" >/dev/null; then
  echo "API OK"
else
  echo "API FAILED" >&2
  fail=1
fi

if [[ "$CHECK_FRONTEND" != "0" ]]; then
  echo "Checking frontend http://127.0.0.1:5173 (optional; set CHECK_FRONTEND=0 to skip) ..."
  if curl -fsS "http://127.0.0.1:5173" >/dev/null 2>&1; then
    echo "Frontend OK"
  else
    echo "Frontend not reachable (expected when lambda-ui profile is off; use local frontend)" >&2
  fi
fi

echo "Checking workers API ..."
if curl -fsS "http://127.0.0.1:8000/api/v1/workers" | grep -q essentia_tensorflow; then
  echo "TensorFlow worker heartbeat visible"
else
  echo "TensorFlow worker heartbeat not found (worker may still be starting)" >&2
fi

echo "Checking Essentia TensorFlow GPU in container ..."
if "${COMPOSE[@]}" run --rm -e REQUIRE_GPU=false essentia-tensorflow-worker \
  uv run python scripts/lambda/check_essentia_tf.py; then
  echo "Essentia TensorFlow GPU check script OK"
else
  echo "Essentia TensorFlow GPU check FAILED" >&2
  fail=1
fi

exit "$fail"
