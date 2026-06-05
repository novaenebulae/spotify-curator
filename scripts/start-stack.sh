#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

ENV_FILE="${ENV_FILE:-.env}"
BUILD=false
DOWN=false
LOGS=false

while [[ $# -gt 0 ]]; do
  case "$1" in
    --build) BUILD=true ;;
    --down) DOWN=true ;;
    --logs) LOGS=true ;;
    --env-file) ENV_FILE="$2"; shift ;;
    *) echo "Unknown option: $1" >&2; exit 1 ;;
  esac
  shift
done

if [[ ! -f "$ENV_FILE" ]]; then
  if [[ -f .env.example ]]; then
    cp .env.example "$ENV_FILE"
    echo "Created $ENV_FILE from .env.example"
  else
    echo "Missing $ENV_FILE and .env.example" >&2
    exit 1
  fi
fi

get_env() {
  local name="$1"
  local default="$2"
  local line
  line="$(grep -E "^[[:space:]]*${name}[[:space:]]*=" "$ENV_FILE" | tail -n1 || true)"
  if [[ -n "$line" ]]; then
    echo "${line#*=}" | tr -d '[:space:]'
  else
    echo "$default"
  fi
}

DOWNLOAD_WORKERS="$(get_env AUDIO_DOWNLOAD_WORKERS 2)"
LOWLEVEL_WORKERS="$(get_env ESSENTIA_LOWLEVEL_WORKERS 2)"
TF_WORKERS="$(get_env ESSENTIA_TENSORFLOW_WORKERS 2)"

if $DOWN; then
  docker compose --profile audio --profile advanced-analysis down
fi

ARGS=(
  compose --profile audio --profile advanced-analysis up -d
  --scale "audio-downloader=${DOWNLOAD_WORKERS}"
  --scale "essentia-lowlevel-worker=${LOWLEVEL_WORKERS}"
  --scale "essentia-tensorflow-worker=${TF_WORKERS}"
)

if $BUILD; then
  ARGS+=(--build)
fi

echo "Starting stack: download=${DOWNLOAD_WORKERS} lowlevel=${LOWLEVEL_WORKERS} tensorflow=${TF_WORKERS}"
docker "${ARGS[@]}"

if $LOGS; then
  docker compose logs -f core-api
fi
