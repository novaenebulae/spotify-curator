#!/usr/bin/env bash
# Install host prerequisites on a Lambda Labs Ubuntu instance.
set -euo pipefail

if [[ "${EUID:-$(id -u)}" -ne 0 ]]; then
  echo "Run as root: sudo bash $0" >&2
  exit 1
fi

export DEBIAN_FRONTEND=noninteractive
apt-get update
apt-get install -y --no-install-recommends \
  sqlite3 \
  curl \
  ca-certificates \
  python3 \
  python3-venv \
  build-essential

if ! command -v uv >/dev/null 2>&1; then
  curl -LsSf https://astral.sh/uv/install.sh | sh
  install -m 0755 /root/.local/bin/uv /usr/local/bin/uv 2>/dev/null || true
fi

echo ""
echo "Host packages installed."
echo "Ensure the deploy user is in the docker group:"
echo "  sudo usermod -aG docker ubuntu"
echo "Then reconnect SSH before running docker compose."
