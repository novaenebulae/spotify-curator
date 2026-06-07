#!/usr/bin/env bash
set -euo pipefail

mkdir -p /home/ubuntu/spotify-curator-runtime/data
mkdir -p /home/ubuntu/spotify-curator-runtime/logs
mkdir -p /home/ubuntu/spotify-curator-runtime/temp-audio
mkdir -p /lambda/nfs/persistent-storage/spotify-curator/models
mkdir -p /lambda/nfs/persistent-storage/spotify-curator/backups
mkdir -p /lambda/nfs/persistent-storage/spotify-curator/final-output

echo "Lambda runtime directories ready."
