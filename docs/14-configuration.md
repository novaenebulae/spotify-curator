# 14 — Configuration

Tags: #configuration #env #docker #volumes

## `.env.example`

```env
# Core
APP_ENV=development
APP_VERSION=0.1.0
API_HOST=127.0.0.1
API_PORT=8765
API_BASE_URL=http://127.0.0.1:8765/api/v1

# Paths in container
DATA_DIR=/app/data
CACHE_DIR=/app/cache
MODELS_DIR=/app/models
LOGS_DIR=/app/logs
EXPORT_DIR=/app/exports
DATABASE_URL=sqlite:////app/data/spotify_curator.sqlite

# Spotify PKCE
SPOTIFY_CLIENT_ID=
SPOTIFY_REDIRECT_URI=http://127.0.0.1:8765/api/v1/spotify/auth/callback
SPOTIFY_SCOPES=user-read-private user-library-read playlist-read-private playlist-read-collaborative

# Jobs
JOB_DEFAULT_MAX_ATTEMPTS=3
JOB_POLL_INTERVAL_MS=1000

# Audio constraints
AUDIO_SEGMENT_MAX_SECONDS=30
AUDIO_KEEP_SEGMENTS_AFTER_ANALYSIS=false
AUDIO_DEBUG_KEEP_FAILED_SEGMENTS=false

# ReccoBeats
RECCOBEATS_BASE_URL=https://api.reccobeats.com
RECCOBEATS_TIMEOUT_SECONDS=15
RECCOBEATS_MAX_RETRIES=3

# Playlist engine
PLAYLIST_DEFAULT_TARGET_SIZE=80
PLAYLIST_DRY_RUN_REQUIRED=true

# Logging
LOG_LEVEL=INFO
LOG_REDACT_SECRETS=true
```

## Profils Docker Compose

### Développement minimal

Services :

- core-api ;
- SQLite volume ;
- diagnostics.

### Audio local

Services supplémentaires :

- audio-downloader ;
- essentia-lowlevel.

### Advanced analysis

Services supplémentaires :

- essentia-tensorflow ;
- clustering-worker.

## Variables sensibles

Aucune variable sensible ne doit être commitée. `SPOTIFY_CLIENT_ID` n’est pas aussi critique qu’un secret, mais il doit rester dans `.env` local si l’utilisateur le souhaite.

## Chemins Windows

L’application Tauri tourne côté Windows. Docker utilise les volumes montés.

Éviter les chemins absolus Windows dans la DB. Stocker des chemins relatifs au volume quand possible.

## Configuration UI

L’UI doit lire la configuration non sensible via :

```text
GET /api/v1/runtime/config
```

Elle ne doit pas lire `.env` directement.

## Modes debug

Options :

- conserver segments échoués ;
- logs plus détaillés ;
- afficher raw payloads ;
- exporter rapport système.

Le mode debug ne doit pas désactiver les règles de sécurité.
