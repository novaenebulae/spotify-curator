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

UI manuelle : `/library` (table, filtres, dry-run modal, historique).

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

Phase 7+ :

```bash
docker compose build essentia-tensorflow
# run small inference on test wav
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
