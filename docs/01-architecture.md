# 01 — Architecture

Tags: #architecture #docker #tauri #svelte #fastapi #sqlite

## Vue générale

```text
Windows
  └── Tauri / Svelte
          ↓ HTTP localhost
Docker Desktop + WSL2
  └── Docker Compose
          ├── core-api Python
          ├── job-worker
          ├── audio-downloader
          ├── essentia-lowlevel
          ├── essentia-tensorflow
          └── clustering-worker
```

## Hors Docker

- Tauri.
- Svelte/SvelteKit.
- WebView2.
- UI.
- OAuth desktop.
- Appels HTTP vers core local.

## Dans Docker

- FastAPI core.
- Jobs.
- SQLite.
- Clients Spotify/ReccoBeats.
- yt-dlp.
- FFmpeg.
- Essentia.
- UMAP/HDBSCAN.

## API locale

```text
http://127.0.0.1:8765/api/v1
```

Jamais `0.0.0.0`.

## Volumes

```text
data/    SQLite + backups
cache/   segments temporaires + JSON cache
models/  modèles externes non committés
logs/    logs core/jobs/docker
```

## Pipeline import

```text
OAuth → Spotify API → normalisation → SQLite → snapshot → diff
```

## Pipeline audio

```text
track → résolution source → segment yt-dlp <= 30s → FFmpeg WAV
→ Essentia low-level → JSON → merge features → cleanup audio
```
