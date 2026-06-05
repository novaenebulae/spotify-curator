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

### Advanced analysis (profil `advanced-analysis`, phase 6 cible)

Services supplémentaires :

- `essentia-tensorflow-worker` ;

```bash
docker compose --profile audio --profile advanced-analysis up -d --build
```

### Clustering (phase 7 cible)

- `clustering-worker` (non implémenté).

Variables phase 6 (implémentées dans [`core/app/settings/config.py`](../core/app/settings/config.py)) :

```env
ANALYSIS_PIPELINE_MODE=streaming
AUDIO_ANALYSIS_PIPELINE_VERSION=audio_pipeline_v1
ANALYSIS_ADVANCED_ENABLED=true
ANALYSIS_DEFAULT_INCLUDE_TENSORFLOW=true
ESSENTIA_TENSORFLOW_WORKERS=1
ESSENTIA_TENSORFLOW_BATCH_SIZE=8
ESSENTIA_TENSORFLOW_MAX_RETRIES=1
ESSENTIA_TENSORFLOW_ITEM_LOCK_TIMEOUT_SECONDS=1800
ESSENTIA_TENSORFLOW_STATUS_ONLY=false
ESSENTIA_TENSORFLOW_PIPELINE_VERSION=essentia_tensorflow_v1
MODELS_DIR=/app/models
MODEL_REGISTRY_PATH=/app/models/model_registry.json
MODEL_HASH_CHECK_ENABLED=true
AUDIO_CLEANUP_WAIT_FOR_ALL_CONSUMERS=true
ADVANCED_FEATURES_TOP_K_GENRES=10
ENERGY_PROXY_ENABLED=true
```

Profil Docker `advanced-analysis` : service `essentia-tensorflow-worker` (stage `essentia_tensorflow` puis legacy `essentia_tensorflow_*` ; `ESSENTIA_TENSORFLOW_BATCH_SIZE` = taille du **flush pipeline différé**, pas le nombre d'items réservés par réplica ; scale horizontal via `--scale essentia-tensorflow-worker=K` ; mode `status_only` si modèles requis absents).

`ESSENTIA_TF_PIPELINE_VERSION=phase6_tf_unified_v1` : version diagnostics des runs stage unifié.

Modèles sous `models/` (jamais commités) : `essentia/`, `tensorflow/`, `discogs_effnet/`, `discogs_maest/`.

### Variables modèles et inférence réelle (réalignement phase 6)

Ajoutées pour la gestion de modèles et l'inférence réelle Essentia TensorFlow. Détail : [`19-essentia-tensorflow-model-management.md`](19-essentia-tensorflow-model-management.md).

```env
# Models
MODELS_DIR=/app/models
ESSENTIA_MODELS_DIR=/app/models/essentia
ESSENTIA_MODELS_MANIFEST=/app/core/app/models_registry/essentia_models_manifest.yaml
ESSENTIA_MODELS_DEFAULT_PROFILE=phase6-recommended
ESSENTIA_MODELS_DOWNLOAD_TIMEOUT_SECONDS=300
ESSENTIA_MODELS_VERIFY_HASH=true
ESSENTIA_MODELS_ACCEPT_LICENSE=false

# TensorFlow inference
ESSENTIA_TF_REAL_INFERENCE_ENABLED=true
ESSENTIA_TF_ALLOW_STUBS_IN_TESTS=false
ESSENTIA_TF_REQUIRE_MODELS_FOR_ADVANCED=false
ESSENTIA_TF_FAIL_ON_STUB_IN_PRODUCTION=true
ESSENTIA_TENSORFLOW_WORKERS=1
ESSENTIA_TENSORFLOW_BATCH_SIZE=8
ESSENTIA_TENSORFLOW_ITEM_LOCK_TIMEOUT_SECONDS=1800
```

Règles :

- `ESSENTIA_TF_ALLOW_STUBS_IN_TESTS=true` ne doit être utilisé qu'en environnement test.
- `ESSENTIA_TF_FAIL_ON_STUB_IN_PRODUCTION=true` est obligatoire.
- `ESSENTIA_MODELS_ACCEPT_LICENSE=false` par défaut : l'utilisateur doit accepter explicitement la licence `CC BY-NC-SA 4.0` avant téléchargement.
- `ESSENTIA_MODELS_DEFAULT_PROFILE=phase6-recommended` pour couvrir Genre Discogs519.
- `MODELS_DIR` doit pointer vers un volume ignoré par Git.

`.gitignore` (modèles et poids jamais commités) :

```text
models/*
!models/.gitkeep
*.pb
*.onnx
*.h5
*.tflite
*.tfjs
*.zip
```

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
| `0008_phase5_playlist_engine` | Playlist rules, generated playlists, sync |
| `0009_phase6_job_items_pipeline_stages` | `job_items` : `stage_name`, dépendances pipeline |

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
