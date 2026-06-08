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

Variables phase 6 (référence complète : [`.env.example`](../.env.example), implémentation : [`core/app/settings/config.py`](../core/app/settings/config.py)) :

```env
# Scale Docker (scripts/start-stack.ps1)
AUDIO_DOWNLOAD_WORKERS=2
ESSENTIA_LOWLEVEL_WORKERS=2
ESSENTIA_TENSORFLOW_WORKERS=2
DOCKER_TF_MEM_LIMIT=3584m

# Low-level (profil complet rhythm+tonal)
ESSENTIA_LOWLEVEL_PROFILE=/app/profiles/essentia_lowlevel_full.yaml
ESSENTIA_LOWLEVEL_PIPELINE_VERSION=essentia_lowlevel_v2_full

# Pipeline
ANALYSIS_PIPELINE_MODE=streaming
AUDIO_ANALYSIS_PIPELINE_VERSION=audio_pipeline_v1
ANALYSIS_PIPELINE_TICK_ENABLED=true
ANALYSIS_PIPELINE_TICK_INTERVAL_SECONDS=45

# TensorFlow — deux versions distinctes :
# ESSENTIA_TENSORFLOW_PIPELINE_VERSION = legacy / agrégation
# ESSENTIA_TF_PIPELINE_VERSION         = stage unifié (runs réels)
ESSENTIA_TENSORFLOW_PIPELINE_VERSION=essentia_tensorflow_v1
ESSENTIA_TF_PIPELINE_VERSION=phase6_tf_unified_v1
ESSENTIA_TENSORFLOW_BATCH_SIZE=1
ESSENTIA_TENSORFLOW_ITEM_LOCK_TIMEOUT_SECONDS=600
```

### Propagation `.env` → containers

Chaque service dans [`docker-compose.yml`](../docker-compose.yml) utilise `env_file: .env` + le bloc partagé `x-app-env`. Les chemins container (`DATABASE_URL`, `ESSENTIA_LOWLEVEL_PROFILE`, `MODELS_DIR`) sont surchargés explicitement. **Copier `.env.example` vers `.env`** avant le premier démarrage.

### Démarrage stack complète

```powershell
.\scripts\start-stack.ps1 -Build
```

### Budget RAM (Docker Desktop 12 Go)

| Service | `mem_limit` | `cpus` |
|---------|-------------|--------|
| `core-api` | 768m | 1 |
| `preview-resolver-worker` | 256m | 0.5 |
| `audio-downloader` (×N) | 512m | 1 |
| `essentia-lowlevel-worker` (×N) | 1024m | 2 |
| `essentia-tensorflow-worker` (×N) | 3584m (`DOCKER_TF_MEM_LIMIT`) | 4 |

`time_signature` n’est **pas** extrait par Essentia low-level — source : ReccoBeats.

Profil Docker `advanced-analysis` : `essentia-tensorflow-worker` (stage `essentia_tensorflow` ; `ESSENTIA_TENSORFLOW_BATCH_SIZE` = flush pipeline différé, pas réservations par réplica).

**Tick pipeline (`core-api`)** : `ANALYSIS_PIPELINE_TICK_*` — agrégation/cleanup, verrous stale. Diagnostic : `GET /api/v1/jobs/{id}` → `non_terminal_items`, `stuck_hint`.

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
ESSENTIA_TENSORFLOW_BATCH_SIZE=1
ANALYSIS_PIPELINE_TICK_ENABLED=true
ANALYSIS_PIPELINE_TICK_INTERVAL_SECONDS=45
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

## Mode Lambda GPU (`APP_ENV=lambda`)

Fichier modèle : [`.env.lambda.example`](../.env.lambda.example) (copier vers `.env.lambda` sur l’instance).

**Pas besoin de `.env` local sur l’instance.** [`docker-compose.lambda.yml`](../docker-compose.lambda.yml) remplace `env_file: .env` par `env_file: !override [.env.lambda]`. Le Makefile passe aussi `--env-file .env.lambda` pour l’interpolation du bloc `x-app-env` dans [`docker-compose.yml`](../docker-compose.yml) — même mécanisme que `--env-file .env` en local.

Overlays Compose :

- [`docker-compose.gpu.yml`](../docker-compose.gpu.yml) — GPU NVIDIA pour `essentia-tensorflow-worker` (target `gpu`) ;
- [`docker-compose.lambda.yml`](../docker-compose.lambda.yml) — volumes SSD/NFS, ports tunnel SSH.

```bash
make lambda-init-empty-db   # base vierge sur SSD Lambda
make lambda-build
make lambda-up-a100         # alias: make lambda-up (1 worker TF)
make lambda-up-a100-tf2     # alias: make lambda-up-tf2
make lambda-up-a10
make lambda-check-gpu
```

Variables clés :

```env
APP_ENV=lambda
RUN_ENV=lambda
DATABASE_URL=sqlite:////app/data/spotify_curator.sqlite
CACHE_DIR=/app/temp-audio
SPOTIFY_REDIRECT_URI=http://127.0.0.1:8000/api/v1/spotify/auth/callback
ESSENTIA_MODEL_PROFILE=phase6-recommended
ESSENTIA_TF_DEVICE=gpu
ESSENTIA_TF_WARMUP=false
ESSENTIA_TENSORFLOW_WORKERS=1
ESSENTIA_LOWLEVEL_WORKERS=1
AUDIO_DOWNLOAD_WORKERS=2
PREVIEW_RESOLVER_WORKERS=1
AUDIO_DOWNLOAD_CONCURRENCY=2
VITE_API_BASE_URL=http://127.0.0.1:8000
```

- Utiliser **`127.0.0.1`** (pas `localhost`) pour OAuth Spotify ;
- API exposée sur l’instance : `127.0.0.1:8000` → conteneur `core-api:8765` ; tunnel SSH **API seul** (`-L 8000:127.0.0.1:8000`) ;
- UI recommandée : frontend local PC avec `VITE_API_BASE_URL=http://127.0.0.1:8000` ;
- UI optionnelle VM : service `frontend-dev` (profil `lambda-ui`, `make lambda-up-a100-ui`) sur `127.0.0.1:5173` ;
- GPU check : `scripts/lambda/check_essentia_tf.py` (pas `tensorflow` Python obligatoire) ;
- SQLite actif sur SSD local (`/home/ubuntu/spotify-curator-runtime/data`), pas sur NFS ;
- `ESSENTIA_TF_BATCH_SIZE=1` par défaut (micro-batching inference non implémenté).
- Variables pipeline non listées dans `.env.lambda.example` (Deezer, yt-dlp, ReccoBeats, jobs…) : valeurs par défaut de `x-app-env` ; surcharger dans `.env.lambda` si besoin.

Détail opérationnel : [`20-lambda-gpu-cloud-analysis.md`](20-lambda-gpu-cloud-analysis.md).

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
