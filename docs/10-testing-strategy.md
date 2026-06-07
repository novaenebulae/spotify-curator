# 10 — Stratégie de tests

Tags: #tests #pytest #docker #ui #quality

## Objectif

Garantir que chaque phase reste fonctionnelle sans casser les phases précédentes.

## Types de tests

1. Tests unitaires backend.
2. Tests intégration backend/API.
3. Tests DB/migrations.
4. Tests clients externes mockés.
5. Tests UI.
6. Smoke tests Docker.
7. Tests end-to-end locaux ciblés.

## Backend — tests unitaires

### Phase 0

- settings ;
- healthcheck ;
- runtime config ;
- diagnostics Docker parsing.

### Phase 1.5 (consolidation)

- migration Alembic `0001_initial` sur base vide ;
- `GET /runtime/config` ;
- persistance `docker_runtime_checks` ;
- enveloppe d’erreur API ;
- import liked `is_current` / `market_status` ;
- OAuth PKCE state SQLite.

### Phase 1

- PKCE generation ;
- state validation ;
- token refresh mock ;
- Spotify pagination ;
- Spotify retry/rate limit ;
- normalisation track ;
- normalisation album/artist ;
- import idempotent ;
- snapshots ;
- diff snapshots ;
- exports CSV/JSON.

### Phase 2

- recherche texte titre / artiste / album ;
- filtre ISRC, liked, playlist, durée, dates ;
- pagination et tri ;
- absence de doublons de résultats (jointures) ;
- doublons ISRC et titre/artiste/durée ;
- missing tracks (5 statuts) ;
- dry-run unlike / restore / backup playlist ;
- historique `library_actions` ;
- migration `0002_phase2_library` + backfill `album_id`.

### Phase 2.5 — Performance tracks

- `tests/test_tracks_perf.py` : seed 5k, latence page 1/2, `playlist_count` sans `playlists[]`, borne requêtes SQL ;
- `core/scripts/benchmark_tracks.py` : benchmark local / HTTP ;
- `TRACKS_PERF_LOG=1` : logs segments + en-têtes `X-Tracks-Perf-*` ;
- migration `0003_perf_tracks` (index tri liked / artists).

### Phase 2 UI polish

- `tests/test_album_cover_extract.py` : sélection image 64–300 px ;
- `tests/test_backfill_album_covers.py` : script backfill sur SQLite temporaire ;
- `tests/test_library_duplicates.py` : dédup affichage, `is_repeated_occurrence`, covers ;
- `tests/test_library_summary.py` : `GET /library/summary` ;
- `tests/test_tracks_search.py` : `album.cover_image_url` ;
- migration head `0004_album_covers` dans `tests/test_migrations.py` ;
- import : cover appliquée dans `track_upsert` (régression `test_import_liked*.py`).

Checklist UI manuelle :

- `/` : cartes statut + liens rapides ;
- `/library` : covers lazy-load, pagination fluide ;
- `/library` onglet Doublons : groupes dédupliqués, bandeau repeated occurrence ;
- `/import` : ExportPanel ;
- `/settings` : sections cartes, diagnostics repliés.

Backfill après deploy :

```bash
uv run --project core python core/scripts/backfill_album_covers.py --dry-run
# DB Docker volume:
docker compose exec core-api uv run python scripts/backfill_album_covers.py --dry-run
```

Validation :

```bash
cd core && uv run pytest tests/test_tracks_perf.py tests/test_tracks_search.py -q
uv run python core/scripts/benchmark_tracks.py --database-url sqlite:///./data/spotify_curator.sqlite
cd core && uv run pytest -q
cd core && uv run ruff check app/library app/api/v1/tracks.py app/api/v1/library.py
cd app/frontend && npm run check && npm run build
curl http://127.0.0.1:8765/api/v1/tracks?page_size=5
curl http://127.0.0.1:8765/api/v1/library/duplicates?strategy=isrc
curl http://127.0.0.1:8765/api/v1/library/missing-tracks
```

UI manuelle : `/library` (table, filtres, dry-run modal, historique, **drawer features** sur titre analysé — onglets Fusion/Sources).

### Phase 3 (implémenté)

- migration `0005_phase3_features` ;
- client ReccoBeats mock (httpx MockTransport) ;
- timeout, retry, 429 ;
- mapper + confidence ;
- upsert idempotent + raw payload ;
- job `reccobeats_enrichment` ;
- coverage API ;
- `GET /features/tracks/{track_id}` — `tests/test_track_features_api.py` (404, vide, ReccoBeats seul, RB + Essentia avec merge) ;
- UI `/features` ;
- UI `/library` : drawer features au clic titre (manuel).

```bash
cd core && uv run pytest tests/test_reccobeats_client.py tests/test_reccobeats_mapper.py \
  tests/test_feature_upsert.py tests/test_reccobeats_enrich_job.py tests/test_features_coverage.py \
  tests/test_track_features_api.py tests/test_openapi_track_features_route.py \
  tests/test_job_items_progress.py -q

docker compose up -d --build core-api
curl http://127.0.0.1:8765/api/v1/features/tracks/1
curl http://127.0.0.1:8765/api/v1/features/coverage
```

### Phase 3.5 (implémenté)

- batch `GET /v1/audio-features?ids=` — `tests/test_reccobeats_client.py`, `tests/test_reccobeats_batch_parsing.py`
- enrichissement par chunks — `tests/test_reccobeats_enrich_job.py` (assert `http_batches`)

### Phase 4 — audio, previews, UI (implémenté)

```bash
cd core && uv run pytest \
  tests/test_job_items_preview_resolve.py \
  tests/test_preview_resolve_selection.py \
  tests/test_preview_stream.py \
  tests/test_jobs_cancel_preview_resolve.py \
  tests/test_failures_insights.py \
  tests/test_jobs_insights.py \
  tests/test_track_feature_status.py \
  tests/test_hybrid_segment_strategy.py \
  tests/test_essentia_gating_selection.py \
  tests/test_audio_confidence_weights.py \
  tests/test_job_items_progress.py -q

docker compose --profile audio up -d --build \
  --scale audio-downloader=2 --scale essentia-lowlevel-worker=2 \
  --scale preview-resolver-worker=1
curl http://127.0.0.1:8765/api/v1/workers
curl http://127.0.0.1:8765/api/v1/previews/coverage
curl -o NUL -w "%{http_code}" http://127.0.0.1:8765/api/v1/tracks/1/preview/stream
curl -X POST http://127.0.0.1:8765/api/v1/features/merge/recompute -H "Content-Type: application/json" -d "{}"
curl http://127.0.0.1:8765/api/v1/jobs/insights/latest
```

Smoke library (volume Docker vide) : `docker exec -e PYTHONPATH=/app spotify-curator-core-api-1 uv run python scripts/seed_smoke_library.py`

UI manuelle : `/features` (Last runs repliable, failures multi-sources, Clear list), `/library` (colonnes Features, resolve Deezer previews).

Jobs / workers : `[16-job-execution-model-and-worker-parallelism.md](16-job-execution-model-and-worker-parallelism.md)`.

### Phase 3

- ReccoBeats client mock ;
- timeout ;
- retry ;
- rate limit ;
- mapping features ;
- confidence ;
- raw payload ;
- coverage ;
- relance failed.

### Phase 4

- segment strategy ;
- contrainte `<=30s` ;
- titres courts ;
- yt-dlp command options ;
- FFmpeg command builder ;
- audio_download_jobs ;
- track_segments ;
- parser JSON Essentia ;
- merge features ;
- cleanup.

### Phase 5

- PlaylistRule validation ;
- filtres stricts ;
- scoring ;
- score details ;
- diversité artiste ;
- diversité album ;
- avoid duplicate ISRC ;
- preview persistée ;
- dry-run sync.

### Phase 6

- feature profile parsing ;
- imputation ;
- normalisation ;
- matrice features ;
- UMAP runner mock/small data ;
- HDBSCAN runner mock/small data ;
- cluster_memberships ;
- outliers.

### Phase 7

- model registry ;
- model hash ;
- embeddings parse ;
- vector dimension ;
- mood mapping ;
- voice/instrumental mapping ;
- no commit model files.

### Phase 8

- seed similarity ;
- energy curve ordering ;
- harmonic compatibility ;
- discovery mode ;
- explanations selected/excluded.

### Phase 9

- backup create ;
- restore validation ;
- cache cleanup ;
- system report redaction ;
- packaging smoke.

## Tests intégration API

Utiliser une SQLite temporaire et des fixtures.

À vérifier :

- endpoints health/runtime ;
- auth mock ;
- import Spotify mock complet ;
- jobs lifecycle ;
- tracks search ;
- duplicates ;
- missing ;
- features coverage ;
- playlist preview ;
- clustering points.

## Fixtures

Créer un dataset fictif :

- 100 tracks ;
- 20 artistes ;
- 10 albums ;
- 5 playlists ;
- 3 snapshots ;
- doublons ISRC ;
- doublons titre/artiste ;
- tracks disparues ;
- tracks indisponibles ;
- features complètes ;
- features manquantes ;
- payload ReccoBeats mock ;
- JSON Essentia mock ;
- embeddings mock.

## Tests UI

Outils possibles selon stack installée :

- Vitest ;
- Testing Library ;
- Playwright si e2e ajouté ;
- mocks API.

Cas :

- core offline ;
- navigation écrans ;
- statut Spotify ;
- import job polling ;
- table library ;
- filtres ;
- sélection multiple ;
- modal dry-run ;
- historique actions ;
- enrichment coverage ;
- playlist rule validation ;
- clustering map smoke.

## Smoke Docker

Commandes :

```bash
docker --version
docker compose version
docker compose -f docker-compose.dev.yml up -d core-api
curl http://127.0.0.1:8765/api/v1/health
```

Phase 4+ :

```bash
ffmpeg -version
yt-dlp --version
docker pull ghcr.io/mtg/essentia:bullseye-v2.1_beta5
essentia_streaming_extractor_music input.wav output.json profile.yaml
```

Phase 6+ :

```bash
docker compose --profile audio --profile advanced-analysis up -d --build
curl http://127.0.0.1:8765/api/v1/workers
curl http://127.0.0.1:8765/api/v1/models/status
curl -X POST http://127.0.0.1:8765/api/v1/audio/analysis/advanced -H "Content-Type: application/json" -d "{\"track_ids\":[1],\"only_missing\":true}"
curl http://127.0.0.1:8765/api/v1/features/advanced/coverage
```

Pipeline complet + observabilité (bash) :

```bash
JOB=$(curl -s -X POST http://127.0.0.1:8765/api/v1/audio/analysis/advanced \
  -H "Content-Type: application/json" \
  -d '{"track_ids":[1],"only_missing":false,"include_tensorflow":true}' | jq -r .job_id)
curl -s "http://127.0.0.1:8765/api/v1/jobs/$JOB/events?limit=30" | jq .
curl -s http://127.0.0.1:8765/api/v1/workers | jq .
# curl -X POST "http://127.0.0.1:8765/api/v1/jobs/$JOB/cancel"
```

PowerShell (Windows) : voir backlog [`phase-6.md`](../backlog/phase-6.md) §6.9c.

### Validation manuelle — job intermédiaire (≈100 pistes) puis bibliothèque (~5000)

Checklist après un job `audio_analysis_pipeline` de ~100 pistes (`only_missing=true`) :

1. **Last Runs** : tuiles en unité **tracks** (pas jobs/items).
2. **Barre progression** : recharger `/features` pendant un job `running` → `GlobalJobBar` réapparaît (`GET /jobs?status=running` + backup `localStorage`).
3. **Workers TF** : pendant l’inférence MAEST, `GET /workers` conserve **4** entrées `essentia_tensorflow` (heartbeat pendant inférence).
4. **Only missing partiel** : relancer avec `only_missing=true` n’exclut pas les pistes low-level OK mais TF manquant.
5. **Genres** : vérifier qu’aucune masse anormale `Electronic---Experimental` / `Vaporwave` sur titres non électroniques (post-fix MonoLoader).

Feu vert ~5000 pistes (un seul pipeline à la fois, profil `audio` + `advanced-analysis`) — tuning `.env` recommandé :

```env
ESSENTIA_TENSORFLOW_WORKERS=4
AUDIO_DOWNLOAD_WORKERS=2
ESSENTIA_LOWLEVEL_WORKERS=2
ESSENTIA_TENSORFLOW_BATCH_SIZE=4
ESSENTIA_TENSORFLOW_ITEM_LOCK_TIMEOUT_SECONDS=1800
ESSENTIA_LOWLEVEL_ITEM_LOCK_TIMEOUT_SECONDS=900
JOB_WORKER_HEARTBEAT_INTERVAL_SECONDS=10
```

Lancement : `only_missing=true`, `analysis_mode=fast`, `model_profile=phase6-recommended`, `limit` null ou explicite. ETA grossier phase TF : `(tracks_restants / workers_TF) × ~90s`.

### Diagnostic — pipeline bloqué en fin de run

Si le job `audio_analysis_pipeline` reste `running` (ex. `13/20` tracks, `79/100` items) :

```powershell
$JOB = "<job_id>"
curl "http://127.0.0.1:8765/api/v1/jobs/$JOB" | jq '{status, current_step, tracks_progress, stuck_hint, non_terminal_items}'
curl "http://127.0.0.1:8765/api/v1/jobs/$JOB/items?limit=500" | jq '[.items[] | select(.status | test("pending|running|blocked|rate_limited")) | {stage_name, status, track_id, error_code, locked_by}]'
```

Interprétation rapide :

| `non_terminal_items` | Action |
|----------------------|--------|
| `audio_cleanup` + `SEGMENT_CONSUMER_PENDING` | Attendre le tick pipeline (~45s) ou `POST /jobs/{id}/cancel` |
| `feature_aggregation` `pending` longtemps | Vérifier prérequis LL/TF ; tick core-api doit débloquer |
| `essentia_tensorflow` `running` + `locked_by` | Verrou stale (jusqu’à 30 min) ou tick `release_stale_pipeline_stage_locks` |

Tests stall pipeline :

```bash
cd core
uv run pytest tests/test_pipeline_ticker.py tests/test_pipeline_cleanup_retry.py tests/test_feature_aggregation_noop.py tests/test_job_items_pipeline_refresh.py -q
```

Tests API analyse avancée (backend, sans UI) :

```bash
cd core
uv run pytest tests/test_advanced_analysis_api.py tests/test_advanced_features_coverage_api.py tests/test_track_features_advanced_api.py tests/test_jobs_pipeline_stages_live.py -q
```

Tests cleanup / observabilité (6.9c) :

```bash
cd core
uv run pytest tests/test_audio_cleanup.py tests/test_jobs_cancel_pipeline.py tests/test_worker_heartbeats.py tests/test_analysis_pipeline_observability.py tests/test_pipeline_audio_cleanup.py -q
```

Tests backend phase 6 : pipeline stages, handoff downloader → analyzers (déclenchement HTTP `POST /audio/analysis/advanced`), cleanup pipeline stage, events API, annulation `blocked`, model registry mock, TensorFlow worker mock, embeddings shape, `FeatureResolver` source priority, non-régression phase 4 audio et phase 5 playlist.

### UI features avancées (6.9b — implémenté)

```bash
cd app/frontend
npm run check
npm run build
```

Validation manuelle (Docker `audio` + `advanced-analysis`) :

1. Ouvrir `/features` — couverture locale fusionnée, **Run complete local analysis**, workers sur carte séparée, un seul **Recent failures** (stages pipeline inclus).
2. Vérifier `GlobalJobBar` / `JobProgress` : **Track N / M**, temps écoulé, ETA si actif ; détail **Pipeline stages**.
3. Bibliothèque → drawer → onglets **Features** (resolved) et **Sources** (carte TensorFlow) après job terminé.
4. Colonne Features : badges ReccoBeats + **Local** (pas Preview).
5. Arrêter Docker → bannière offline, pas de crash.

Pytest ciblé correctifs 6.9b feedback :

```bash
cd core
uv run pytest tests/test_track_features_advanced_api.py tests/test_track_feature_status.py tests/test_jobs_pipeline_stages_live.py tests/test_failures_insights.py -q
```

Pytest ciblé correctifs analyse TF + progression titres :

```bash
cd core
uv run pytest tests/test_pipeline_track_progress.py tests/test_advanced_aggregate_scores.py tests/test_model_manager_paths.py tests/test_track_features_advanced_api.py tests/test_jobs_pipeline_stages_live.py -q
```

Smoke genre / classifiers (conteneur ou venv avec Essentia TF + modèles `phase6-recommended`, WAV **30 s**) :

```bash
cd core
uv run python scripts/smoke_essentia_tensorflow_real.py --wav-path /path/to/segment.wav
```

Vérifier dans la sortie : `genre_available`, `genre_top_k_len`, mode `real` vs `missing` / `stub`.

Validation manuelle complémentaire (après rebuild `audio-downloader` si padding 30 s modifié) :

1. Pipeline `phase6-recommended` sur ~10 titres — drawer **Sources** : section **Top 3 genres** visible, pas de `MODEL_MISSING` genre si inférence OK.
2. Moods / approachability / engagement : scores **distincts** sur un même titre (hors audio réellement plat).
3. `GlobalJobBar` : `Track X / M` cohérent ; pas de `JobProgress` dans le panneau Local analysis ; elapsed/ETA plausibles.
4. `/features` : ordre Features coverage → Enrichment → Local analysis (h2, non repliable) → Workers (grille) → Models → Last runs → Recent failures.

### Tests modèles

```bash
cd core
uv run pytest tests/test_model_registry.py tests/test_model_manager.py tests/test_models_download_api.py -q
```

Cas à couvrir : manifest valide, modèle absent, modèle fake présent, hash invalide, téléchargement profil minimal, refus téléchargement sans acceptation licence, verify-only.

### Tests stubs

```bash
cd core
uv run pytest tests/test_tf_stub_guard.py -q
```

Cas à couvrir :

- stub autorisé si `APP_ENV=test` + `ESSENTIA_TF_ALLOW_STUBS_IN_TESTS=true` ;
- stub interdit si `APP_ENV!=test` ;
- aucune feature `success` avec `inference_mode=stub` en production.

### Smoke inférence réelle

Le download/verify et le smoke s'exécutent dans `essentia-tensorflow-worker` : seule cette image embarque le wheel `essentia-tensorflow` (le service `core-api` n'a pas `essentia`).

```bash
docker compose --profile audio --profile advanced-analysis up -d --build
docker compose exec essentia-tensorflow-worker uv run python scripts/download_essentia_models.py --profile phase6-minimal --accept-license
docker compose exec essentia-tensorflow-worker uv run python scripts/download_essentia_models.py --verify-only
docker compose exec essentia-tensorflow-worker uv run python scripts/smoke_essentia_tensorflow_real.py --require-models
```

Options du smoke : `--require-models` (échoue si modèles absents), `--allow-missing` (tolère l'absence), `--track-id`, `--wav-path` (sinon un WAV de 30 s 16 kHz mono est généré, durée requise par MAEST), `--profile` (défaut `phase6-minimal`), `--persist` (écrit l'embedding réel via `TrackEmbeddingsRepository`, sinon dry-run).

Codes de sortie : `0` inférence réelle OK ; `1` `model_missing` avec `--require-models` ; `2` échec d'inférence Essentia.

Test unitaire (backend mocké, sans Essentia) :

```bash
cd core
uv run pytest tests/test_smoke_essentia_tf_real.py -q
```

Résultats attendus :

- si modèles absents : sortie claire `model_missing` ;
- si modèles présents : au moins une vraie inférence `inference_mode=real` ;
- aucune écriture de feature fake ;
- API `/features/ advanced/coverage` cohérente.

Phase 7+ :

```bash
docker compose build essentia-tensorflow-worker
# run small inference on test wav
```

## Tests mode Lambda (CPU host / GPU instance)

Unitaires (sans GPU, mocks TensorFlow/Essentia) :

```bash
cd core
uv run pytest tests/test_lambda_settings.py tests/test_tf_warmup.py \
  tests/test_check_tf_gpu.py tests/test_tf_segment_metrics.py \
  tests/test_tf_worker_parallel_reserve.py tests/test_docker_compose_lambda_env.py \
  tests/test_lambda_init_empty_db.py -q
```

Validation manuelle sur instance Lambda (workflow base vierge) :

```bash
bash scripts/lambda/prepare-runtime.sh
bash scripts/lambda/init-empty-db.sh
make lambda-build
make lambda-check-gpu
make lambda-up-a100
bash scripts/lambda/check-services.sh
bash scripts/lambda/benchmark-pipeline.sh 30
make lambda-export
```

Vérification GPU sur instance Lambda :

```bash
make lambda-check-gpu
# ou
docker compose -f docker-compose.yml -f docker-compose.gpu.yml -f docker-compose.lambda.yml \
  --env-file .env.lambda --profile advanced-analysis run --rm -e REQUIRE_GPU=true \
  essentia-tensorflow-worker uv run python scripts/lambda/check_tf_gpu.py
```

Benchmark pipeline (20–50 pistes, API locale ou tunnel) :

```bash
cd core
uv run python scripts/benchmark_advanced_pipeline.py --base-url http://127.0.0.1:8000 --limit 30
```

## Tests de sécurité

- `.env` non commité ;
- tokens absents des logs ;
- data/cache/models/logs/exports ignorés ;
- endpoints ne retournent pas de token ;
- write Spotify bloqué sans scope ;
- dry-run obligatoire.

## Non-régression phase

Chaque phase doit relancer :

- tests unitaires de la phase courante ;
- tests critiques phases précédentes ;
- smoke API health ;
- lint backend ;
- build/lint frontend si impact UI.

## Commandes types

Backend :

```bash
docker compose -f docker-compose.dev.yml exec core-api uv run pytest
```

Backend ciblé :

```bash
docker compose -f docker-compose.dev.yml exec core-api uv run pytest tests/unit/test_library_search.py
```

Lint :

```bash
docker compose -f docker-compose.dev.yml exec core-api uv run ruff check .
docker compose -f docker-compose.dev.yml exec core-api uv run ruff format --check .
```

Frontend :

```bash
cd app/frontend
npm run lint
npm run test
npm run build
```

## Critère global

Une fonctionnalité sans tests minimum et sans documentation à jour reste en `REVIEW`, pas `DONE`.