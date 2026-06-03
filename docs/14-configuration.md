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
RECCOBEATS_BATCH_DELAY_MS=100
RECCOBEATS_HTTP_BATCH_SIZE=40
RECCOBEATS_DB_UPSERT_BATCH_SIZE=50
RECCOBEATS_ENRICH_DEFAULT_LIMIT=5000
RECCOBEATS_ENRICH_MAX_LIMIT=10000

# Playlist engine
PLAYLIST_DEFAULT_TARGET_SIZE=80
PLAYLIST_DRY_RUN_REQUIRED=true

# Logging
LOG_LEVEL=INFO
LOG_REDACT_SECRETS=true
```

## Variables jobs / workers

**Lues par le core aujourd'hui** : `JOB_DEFAULT_MAX_ATTEMPTS`, `RECCOBEATS_*`, et (phase 4) `JOB_*`, `WORKER_*`, `AUDIO_*`, `YTDLP_*`, `FFMPEG_*`, `ESSENTIA_LOWLEVEL_*` — voir [`.env.example`](../.env.example).

Profil Compose **`audio`** : `audio-downloader`, `preview-resolver-worker`, `essentia-lowlevel-worker` (voir [`16-job-execution-model-and-worker-parallelism.md`](16-job-execution-model-and-worker-parallelism.md)).

Variables utiles : `JOB_EVENTS_ENABLED`, `WORKER_HEARTBEATS_ENABLED`, `TRACKS_PERF_LOG`, `DEEZER_PREVIEW_UI_MIN_CONFIDENCE`, `DEEZER_PREVIEW_ANALYSIS_MIN_CONFIDENCE`, `YOUTUBE_MIN_CONFIDENCE` — voir [`.env.example`](../.env.example) et [`core/app/settings/config.py`](../core/app/settings/config.py).

## Profils Docker Compose

### Développement minimal

Services :

- core-api ;
- SQLite volume ;
- diagnostics.

### Audio local (profil `audio`)

Services supplémentaires :

- `audio-downloader` ;
- `preview-resolver-worker` ;
- `essentia-lowlevel-worker`.

```bash
docker compose --profile audio up -d --build
```

### Advanced analysis

Services supplémentaires :

- essentia-tensorflow ;
- clustering-worker.

## Variables sensibles

Aucune variable sensible ne doit être commitée. `SPOTIFY_CLIENT_ID` n’est pas aussi critique qu’un secret, mais il doit rester dans `.env` local si l’utilisateur le souhaite.

## Migrations Alembic

Révisions Alembic (ordre) :

| Révision | Contenu |
|----------|---------|
| `0001_initial` | Schéma phase 0–1 |
| `0002_phase2_library` | Library actions, etc. |
| `0003_perf_tracks` | Index perf liste tracks |
| `0004_album_covers` | Covers albums |
| `0005_phase3_features` | Features multi-source |
| `0006_phase4_audio_local` | Audio, `job_items`, heartbeats |
| `0007_track_previews_hybrid` | `track_previews`, hybrid metadata |

```bash
cd core
uv run alembic upgrade head
```

Au démarrage du core, `init_db()` exécute `upgrade head` automatiquement sur une base vide dans `data/`.

Variable optionnelle pour tests locaux : `DATABASE_URL=sqlite:///./data/test.sqlite`

**Docker Compose** : `docker-compose.yml` fixe `DATABASE_URL` sur le volume nommé (`/app/data/…`). Ne pas exporter une URL Windows (`sqlite:///c:/…`) dans la session PowerShell avant `docker compose up` : Compose l’injectait dans les conteneurs et vidait la bibliothèque (base vide sous `/app/c:/…`). Migrations Alembic **dans Docker** : `docker compose exec core-api uv run alembic upgrade head`. Alembic **sur l’hôte** : `DATABASE_URL=sqlite:///./data/spotify_curator.sqlite` (fichier local, distinct du volume Docker).

`SQLITE_JOURNAL_MODE` : `WAL` (défaut Docker Compose) avec le volume nommé `spotify_curator_data`. Utiliser `DELETE` seulement si vous remontez `./data:/app/data` (bind mount Windows, plus lent).

### Volume SQLite (recommandé)

```yaml
# docker-compose.yml
volumes:
  - spotify_curator_data:/app/data
```

Migration one-shot depuis `data/spotify_curator.sqlite` :

```powershell
.\scripts\migrate-sqlite-to-docker-volume.ps1
```

Sauvegarde manuelle depuis le volume :

```powershell
docker run --rm -v spotify_curator_data:/from -v ${PWD}/data:/to alpine cp /from/spotify_curator.sqlite /to/backup.sqlite
```

## Chemins Windows

L’application Tauri tourne côté Windows. Le core Docker utilise le volume `spotify_curator_data` (fichiers dans la VM Linux, pas le dossier `data/` du repo).

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
