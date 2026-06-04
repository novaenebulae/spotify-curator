# Phase 6 — Audit post-phase 5

Tags: #phase-6 #audit #audio-pipeline #tensorflow

Date : 2026-06-03  
Périmètre : tâche **6.0** — état des lieux avant implémentation du pipeline parallèle. Aucun code pipeline modifié dans cette livraison.

Documentation de cadrage fusionnée dans les docs canoniques ; patches sources archivés sous [`archive/phase-6-patches/`](archive/phase-6-patches/).

---

## 1. État réel du dépôt

### Phases livrées

| Phase | Statut | Indices |
|---|---|---|
| 0–4 | Livré | Workers profil `audio`, `job_items`, Essentia low-level, previews hybrides |
| 5 | Livré | `0008_phase5_playlist_engine.py`, `core/app/playlists/*`, UI `/playlists`, sync dry-run |
| 6 | Non démarrée (code) | Pas de stages, pas de worker TF, pas d’API `analysis/advanced` |

### Migrations Alembic

Révisions présentes : `0001` … `0008_phase5_playlist_engine`.

**Absent** (cible phase 6) :

- colonnes stage sur `job_items` (extension option A — retenue)
- `model_registry_entries`
- `track_advanced_features`
- table SQL `track_embeddings` (documentée, pas de modèle SQLAlchemy)

### Flux audio actuel (séquentiel)

```text
POST /api/v1/audio/segments/download  → job_type audio_download
        (items: audio_download_track, 1 par track)
… attente fin job (UI ou manuel) …
POST /api/v1/audio/analysis/lowlevel  → job_type essentia_lowlevel_analysis
        (items: essentia_lowlevel_track, 1 par track)
```

Le worker low-level charge **tous** les segments actifs d’une piste à la réservation de l’item track — pas de dispatch par segment ni par stage.

L’UI enchaîne explicitement download puis analyze : [`app/frontend/src/lib/components/features/LocalAudioAnalysis.svelte`](../app/frontend/src/lib/components/features/LocalAudioAnalysis.svelte) (`runDownloadThenAnalyze`).

### Docker Compose

Profil **`audio`** (implémenté) :

- `audio-downloader`
- `preview-resolver-worker`
- `essentia-lowlevel-worker`

**Non présent** : `essentia-tensorflow-worker`, profil `advanced-analysis`.

---

## 2. Fichiers clés

### API

| Fichier | Rôle |
|---|---|
| [`core/app/api/v1/audio.py`](../core/app/api/v1/audio.py) | segments plan/download, lowlevel, cleanup |
| [`core/app/api/v1/features.py`](../core/app/api/v1/features.py) | enrich, coverage, track features |
| [`core/app/api/v1/jobs.py`](../core/app/api/v1/jobs.py) | list/get/cancel, items |
| [`core/app/api/v1/workers.py`](../core/app/api/v1/workers.py) | heartbeats |
| [`core/app/api/v1/router.py`](../core/app/api/v1/router.py) | wiring |

Endpoints **cible** phase 6 (non implémentés) : `POST /audio/analysis/advanced`, `GET /models/status`, `GET /features/advanced/coverage`.

### Workers

| Script | `worker_type` | `item_type` |
|---|---|---|
| [`run_audio_downloader_worker.py`](../core/scripts/run_audio_downloader_worker.py) | `audio_downloader` | `audio_download_track` |
| [`run_essentia_lowlevel_worker.py`](../core/scripts/run_essentia_lowlevel_worker.py) | `essentia_lowlevel` | `essentia_lowlevel_track` |
| [`run_preview_resolver_worker.py`](../core/scripts/run_preview_resolver_worker.py) | `preview_resolver` | `preview_resolve_track` |

Constantes : [`core/app/jobs/items/constants.py`](../core/app/jobs/items/constants.py) — `WORKER_ITEM_TYPES` mappe worker → types d’items.

### Jobs / persistance

| Fichier | Tables |
|---|---|
| [`models_jobs.py`](../core/app/database/models_jobs.py) | `jobs` |
| [`models_job_items.py`](../core/app/database/models_job_items.py) | `job_items`, `worker_heartbeats`, `job_events` |
| [`models_audio.py`](../core/app/database/models_audio.py) | `track_segments`, `audio_analysis_jobs`, … |
| [`models_features.py`](../core/app/database/models_features.py) | `audio_features`, `audio_feature_raw_payloads` |
| [`download_job_service.py`](../core/app/audio/download_job_service.py) | création job download |
| [`analysis_job_service.py`](../core/app/audio/analysis_job_service.py) | création job low-level |
| [`jobs/items/service.py`](../core/app/jobs/items/service.py) | réservation, locks, progression |

Champ `job_items.segment_id` : présent en schéma, **toujours `None`** à la création d’items.

### Playlist engine (phase 5)

| Fichier | Rôle |
|---|---|
| [`feature_registry.py`](../core/app/playlists/feature_registry.py) | descriptors ; TF/moods en `phase_available=7` |
| [`feature_resolver.py`](../core/app/playlists/feature_resolver.py) | charge colonnes `audio_features` ; futures → `not_available_yet` |
| [`types.py`](../core/app/playlists/types.py) | `TrackFeatureView`, `FeatureValue` |
| [`preview_service.py`](../core/app/playlists/preview_service.py) | consomme uniquement le resolver |

**Conforme** : aucun accès à `audio_feature_raw_payloads` sous `core/app/playlists/`.

---

## 3. Flux cible phase 6

```text
POST /audio/analysis/advanced → job audio_analysis_pipeline
segment_download → segment_ready
  ├─ essentia_lowlevel
  └─ essentia_tensorflow_embeddings → essentia_tensorflow_classifiers
feature_aggregation → audio_cleanup (multi-consommateurs)
```

Mode legacy conservé via `ANALYSIS_PIPELINE_MODE=legacy` (à implémenter en 6.2).

---

## 4. Gaps vs backlog

| Domaine | État actuel | Tâche backlog |
|---|---|---|
| Modèle stages | Items track-level uniquement | 6.1 — étendre `job_items` (`stage_name`, `segment_id`, …) |
| Handoff segment_ready | Downloader ne crée pas de stages analyse | 6.2 |
| Low-level dans pipeline | Job séparé post-download | 6.3 |
| Worker / image TF | Absent | 6.4 |
| Model registry | Absent | 6.5 |
| `track_embeddings` | Registry only | 6.6 |
| Classifiers / moods | `not_available_yet` | 6.7 |
| FeatureResolver TF | Stubs phase 7 | 6.8 |
| API + UI advanced | Partiel (features track API, pas advanced) | 6.9 |
| Tests pipeline / TF | Absents | 6.10 |
| Cleanup multi-consumer | Cleanup après low-level track item | 6.9 |

### Dérive doc / code

- Roadmap docs : phase 6 = TF (fusionnée juin 2026).
- `FeatureRegistry` : plusieurs features TF encore `phase_available=7` — à passer à `6` lors de 6.8.
- Seed DB `feature_sources.essentia_tensorflow` existe (migration `0005`) ; pas de données produites.

---

## 5. Décision : extension de `job_items` (option A retenue)

**Décision produit (juin 2026)** : ne pas créer de table `analysis_stage_items`. Tous les stages du pipeline phase 6 vivent dans **`job_items`**, sur le même mécanisme de réservation, locks, events et progression que la phase 4.

Objectif : un **flux unique** évolutif (streaming + legacy via `ANALYSIS_PIPELINE_MODE`), sans second modèle à maintenir ni dépréciation ultérieure du flux actuel.

### Champs à ajouter (migration 6.1)

| Champ | Type | Notes |
|---|---|---|
| `stage_name` | text indexed, nullable | `segment_download`, `essentia_lowlevel`, … ; `NULL` = items legacy track-only |
| `depends_on_item_id` | FK `job_items.id` nullable | dépendance directe entre stages |
| `consumer_group` | text nullable | verrou cleanup multi-consommateurs |
| `model_name` | text nullable | modèle TensorFlow |
| `pipeline_version` | text nullable | version pipeline |
| `blocked_reason` | text nullable | si status `blocked` |

`segment_id` existe déjà — à renseigner pour les stages liés à un segment.

### Impacts implémentation (6.1+)

- Étendre `WORKER_ITEM_TYPES` (ou filtre équivalent) pour réserver par `stage_name` + `item_type` selon le worker.
- Jobs `audio_analysis_pipeline` : plusieurs items par track/segment (un par stage) ; jobs legacy (`audio_download`, `essentia_lowlevel_analysis`) inchangés en mode `legacy` (items sans `stage_name` ou job type distinct).
- `recompute_job_progress` : agrégation par `stage_name` dans `jobs.result_json` pour l’UI.
- `AnalysisPipelineOrchestrator` : crée les items stage ; le downloader marque `segment_download` success et enfile `essentia_lowlevel` / TF pour le `segment_id` concerné.

### Option B — `analysis_stage_items` (non retenue)

Table dédiée écartée pour éviter duplication de réservation, repositories et dette de convergence avec `job_items`. Documentée uniquement dans [`archive/phase-6-patches/05-domain-model.phase6-patch.md`](archive/phase-6-patches/05-domain-model.phase6-patch.md) à titre historique.

---

## 6. Risques

| Risque | Mitigation |
|---|---|
| Régression low-level / merge | Tests phase 4 non-régression obligatoires en 6.3 ; mode `legacy` |
| Cleanup prématuré | `AUDIO_CLEANUP_WAIT_FOR_ALL_CONSUMERS` ; tests multi-consumer |
| SQLite contention | Transactions courtes (doc 16) ; pas d’inférence dans une transaction ouverte |
| Modèles absents | `skipped` / `model_missing` ; `ESSENTIA_TENSORFLOW_STATUS_ONLY` |
| Phase 5 playlists | Ne pas lire raw payloads ; tests resolver/presets inchangés |
| Concurrence jobs | Gardes « un job running » par type — à étendre pour `audio_analysis_pipeline` |

---

## 7. Ordre d’implémentation proposé

| # | Prompt | Backlog |
|---:|---|---|
| 1 | [`phase-6-01-stage-model.md`](../prompts/phase-6-01-stage-model.md) | 6.1 |
| 2 | [`phase-6-02-downloader-handoff.md`](../prompts/phase-6-02-downloader-handoff.md) | 6.2 |
| 3 | [`phase-6-03-lowlevel-pipeline.md`](../prompts/phase-6-03-lowlevel-pipeline.md) | 6.3 |
| 4 | [`phase-6-04-tensorflow-worker-and-model-registry.md`](../prompts/phase-6-04-tensorflow-worker-and-model-registry.md) | 6.4–6.5 |
| 5 | [`phase-6-05-embeddings-discogs-genre.md`](../prompts/phase-6-05-embeddings-discogs-genre.md) | 6.6 |
| 6 | [`phase-6-06-advanced-classifiers.md`](../prompts/phase-6-06-advanced-classifiers.md) | 6.7 |
| 7 | [`phase-6-07-aggregation-and-resolver.md`](../prompts/phase-6-07-aggregation-and-resolver.md) | 6.8 |
| 8 | [`phase-6-08-api-ui.md`](../prompts/phase-6-08-api-ui.md) | 6.9 |
| 9 | [`phase-6-09-cleanup-observability.md`](../prompts/phase-6-09-cleanup-observability.md) | observabilité |
| 10 | [`phase-6-10-validation-docs.md`](../prompts/phase-6-10-validation-docs.md) | 6.10 + `phase-6-review.md` |

---

## 8. Validation baseline (6.0)

Exécuté le 2026-06-03 :

```bash
cd core
uv run pytest -q
# → 194 passed (72.26s)

cd ../app/frontend
npm run check
# → 0 errors, 2 warnings (CollapsibleSection, DryRunModal — préexistants)

npm run build
# → OK (vite build + adapter-auto)
```

### Tests phase 4 / 5 à protéger

- Audio : `test_job_items*.py`, `test_audio_*`, `test_essentia_*`, `test_track_features_api.py`
- Playlist : `test_feature_registry.py`, `test_feature_resolver.py`, `test_playlist_*`, `test_generated_playlist_preview.py`

### Commandes cible fin de phase 6

```bash
cd core && uv run pytest -q && uv run ruff check .
cd app/frontend && npm run check && npm run build
docker compose --profile audio --profile advanced-analysis up -d --build
curl http://127.0.0.1:8765/api/v1/health
curl http://127.0.0.1:8765/api/v1/models/status
curl http://127.0.0.1:8765/api/v1/features/advanced/coverage
```

---

## 9. Documentation mise à jour (6.0)

- [`04-backlog-by-phase.md`](04-backlog-by-phase.md) — réordonnancement phases 6/7
- [`05-domain-model.md`](05-domain-model.md) — extensions phase 6
- [`06-api-contract.md`](06-api-contract.md) — endpoints cible phase 6
- [`07-audio-analysis-pipeline.md`](07-audio-analysis-pipeline.md) — pipeline streaming
- [`10-testing-strategy.md`](10-testing-strategy.md) — tests phase 6
- [`14-configuration.md`](14-configuration.md) — variables et profils Compose
- [`16-job-execution-model-and-worker-parallelism.md`](16-job-execution-model-and-worker-parallelism.md) — stages
- [`18-feature-consumption-contract.md`](18-feature-consumption-contract.md) — features et alias phase 6

Patches sources : [`archive/phase-6-patches/`](archive/phase-6-patches/).
