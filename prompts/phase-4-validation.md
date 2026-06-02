# Prompt Cursor — Phase 4 validation finale

Tu travailles sur le projet Spotify Library Curator & Playlist Engine.

Objectif : valider définitivement la phase 4 avant de passer à la phase 5.

Important : cette tâche est une **validation / audit**. Tu ne dois pas ajouter de nouvelles fonctionnalités majeures. Tu peux corriger les bugs, écarts de documentation ou régressions bloquantes détectés pendant l'audit.

## Contexte projet

Application desktop locale :

- Tauri/Svelte pour l'UI ;
- FastAPI Python dans Docker (`127.0.0.1:8765`) ;
- SQLite dans volume Docker `spotify_curator_data` ;
- **Jobs in-process** : imports Spotify, `reccobeats_enrichment` ;
- **Jobs workers** (profil Compose `audio`) : `preview_resolve`, `audio_download`, `essentia_lowlevel_analysis` via `job_items` ;
- Phases 0–3 + **phase 4 livrée** : hybride Deezer + YouTube, previews metadata, Essentia low-level, merge features, UI library/features.

Phases **5–9** (playlists, clustering, TensorFlow) : **hors scope** de cette validation.

## Documents à lire avant toute modification

```text
AGENTS.md
README.md
docs/01-architecture.md
docs/02-repository-structure.md
docs/03-development-workflow.md
docs/04-backlog-by-phase.md
docs/05-domain-model.md
docs/06-api-contract.md
docs/07-audio-analysis-pipeline.md
docs/09-ui-specification.md
docs/10-testing-strategy.md
docs/14-configuration.md
docs/16-job-execution-model-and-worker-parallelism.md
docs/17-audio-preview-and-segment-strategy.md
backlog/phase-4.md
backlog/phase-4-validation.md
```

Checklist détaillée : sections **4V.1** à **4V.9** dans [`backlog/phase-4-validation.md`](../backlog/phase-4-validation.md).

## Périmètre d'audit (aligné backlog 4V)

### 4V.1 — Documentation vs code

- Endpoints phases 0–4 documentés dans `06-api-contract` existent dans `core/app/api/v1/`.
- Phases 5–9 marquées **non implémentées** (pas confondues avec l'API actuelle).
- Migrations `0001` … `0007` cohérentes avec `14-configuration.md`.
- Noms `analysis_decision` = doc 17 / `hybrid.py` (`deezer_only`, `youtube_1_segment`, etc.).

### 4V.2 — Migrations & DB

- `0006_phase4_audio_local` : `job_items`, `worker_heartbeats`, `job_events`, tables audio ;
- `0007_track_previews_hybrid` : `track_previews`, `source_quality` sur segments ;
- contrainte `track_segments.duration_seconds <= 30`.

### 4V.3 — Workers Docker

- Services : `preview-resolver-worker`, `audio-downloader`, `essentia-lowlevel-worker` ;
- `GET /api/v1/workers` avec heartbeats ;
- pas de conteneur par piste ; workers poll `job_items`.

### 4V.4 — Previews Deezer

- `POST /previews/resolve` : `only_missing=true`, `limit=null` = tous les manquants ;
- pas de re-fetch des previews déjà valides ;
- refresh URL signée avant download segment Deezer ;
- `GET /tracks/{id}/preview`, `GET /previews/coverage`.

### 4V.5 — Stratégie hybride

- `analysis_mode` : `fast` (défaut) vs `precise` ;
- décisions : `deezer_only`, `youtube_1_segment`, `deezer_plus_youtube_2_segments`, `youtube_3_segments`, `local_analysis_unavailable` ;
- aucun segment > 30 s.

### 4V.6 — Essentia low-level

- download → FFmpeg WAV → Essentia → parser → upsert `essentia_lowlevel` ;
- raw payload, confidence, gating vs ReccoBeats ;
- cleanup segments ; meta `segments_planned` / `segments_analyzed`.

### 4V.7 — Merge features

- `POST /features/merge/recompute` ;
- `GET /features/tracks/{track_id}` : `merged` + `sources` ;
- coverage `with_reccobeats` / `with_essentia_lowlevel`.

### 4V.8 — UI

- `/` : tuiles ReccoBeats, Essentia, Deezer previews ;
- `/library` : colonnes Features, preview ▶, `TrackFeaturesDrawer` ;
- `/features` : coverage, Field coverage / Recent failures / **Last runs** (repliables), failures multi-sources + `failures_after`, `JobRunStatsBar` ;
- `/settings` : runtime/workers sans debug dominant.

### 4V.9 — Décision

Produire recommandation **GO / NO-GO** phase 5 (voir critère en fin de backlog).

## Méthode

1. Produire un **plan d'audit court** (fichiers, commandes, risques, corrections probables).
2. **Attendre validation** avant migration DB ou changement d'architecture.
3. Exécuter commandes ci-dessous ; corriger uniquement bloquants / doc incohérente.
4. Mettre à jour `backlog/phase-4-validation.md` (statuts 4V.x) et doc si écart trouvé.

## Commandes de validation

Backend :

```bash
cd core
uv run alembic upgrade head
uv run pytest tests/test_job_items_preview_resolve.py \
  tests/test_preview_resolve_selection.py \
  tests/test_failures_insights.py \
  tests/test_jobs_insights.py \
  tests/test_track_feature_status.py \
  tests/test_hybrid_segment_strategy.py \
  tests/test_essentia_gating_selection.py \
  tests/test_audio_confidence_weights.py \
  tests/test_job_items_progress.py \
  tests/test_track_features_api.py \
  tests/test_features_coverage.py -q
uv run pytest -q
uv run ruff check app/audio app/previews app/workers app/jobs/items app/features
```

Docker :

```bash
docker compose up -d --build core-api
docker compose --profile audio up -d --build --scale audio-downloader=2 --scale essentia-lowlevel-worker=2
curl http://127.0.0.1:8765/api/v1/health
curl http://127.0.0.1:8765/api/v1/workers
curl http://127.0.0.1:8765/api/v1/previews/coverage
curl http://127.0.0.1:8765/api/v1/jobs/insights/latest
curl "http://127.0.0.1:8765/api/v1/features/coverage?include_failed=true&failures_page=1"
```

Frontend :

```bash
cd app/frontend
npm run check
npm run build
```

## Livrable attendu

```text
- résumé des points validés (par section 4V.x) ;
- écarts détectés ;
- corrections appliquées ;
- fichiers modifiés ;
- commandes exécutées ;
- résultats tests ;
- risques restants ;
- décision GO / NO-GO pour phase 5.
```

## Contraintes

- Ne pas implémenter la phase 5 (playlists), TensorFlow, clustering.
- Pas de write Spotify.
- Pas de fichiers audio commités ; segments temporaires ≤ 30 s uniquement.
- Pas de diagnostics techniques dominants dans l'UI utilisateur.
