# 10 — Stratégie de tests

Tags: #tests #pytest #docker #ui

## Backend

Tester healthcheck, settings, DB, snapshots, jobs, validation segments, merge features, playlist rules.

## Intégration

Tester API core, SQLite temporaire, Spotify mocké, ReccoBeats mocké, Docker Compose, Essentia smoke.

## UI

Tester statut API, erreurs, navigation, filtres, confirmations, polling jobs.

## Smoke Docker

```text
docker --version
docker compose version
core-api /health
ffmpeg -version
yt-dlp --version
pull ghcr.io/mtg/essentia:bullseye-v2.1_beta5
essentia_streaming_extractor_music sur WAV court
```
