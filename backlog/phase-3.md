# Phase 3 — ReccoBeats enrichment

Tags: #backlog #phase-3 #features #reccobeats

## But

Ajouter les features audio simples via ReccoBeats et préparer le modèle multi-source.

## Definition of Done phase

- [x] Les livrables de phase sont présents.
- [x] Les tests minimum passent.
- [x] Les commandes de validation sont documentées.
- [x] La documentation est à jour.
- [x] Aucun secret, cache, modèle lourd ou fichier audio n'est commité.
- [x] Aucune régression sur les phases précédentes.

## 3.1 — Tables features

Statut : **DONE**

### Livrables

- Migration `0005_phase3_features`
- Tables `feature_sources`, `audio_features`, `audio_feature_raw_payloads`
- Seed idempotent 5 sources (reccobeats actif)

## 3.2 — Client ReccoBeats

Statut : **DONE**

### Livrables

- `core/app/reccobeats/client.py` — httpx, retries, 429, timeout
- Résolution Spotify track ID → ReccoBeats ID → audio features
- Tests mock sans réseau

## 3.3 — Normalisation

Statut : **DONE**

### Livrables

- `core/app/features/reccobeats_mapper.py`
- `core/app/features/confidence.py`
- `core/app/features/upsert.py`
- Raw payloads + upsert idempotent

## 3.4 — Jobs enrichissement

Statut : **DONE**

### Livrables

- `POST /api/v1/features/reccobeats/enrich`
- Job type `reccobeats_enrichment`
- Modes : only_missing, retry_failed, force_refresh, limit

## 3.5 — Coverage

Statut : **DONE**

### Livrables

- `GET /api/v1/features/coverage`
- Summary, sources, fields, recent_failures

## 3.6 — UI enrichment

Statut : **DONE**

### Livrables

- Route `/features`
- `featuresApi.ts`, coverage cards, actions, job progress, failures

## Commandes de validation

```bash
cd core
uv run pytest -q
uv run ruff check app/features app/reccobeats app/api/v1/features.py

cd app/frontend
npm run check
npm run build

docker compose up -d --build
curl http://127.0.0.1:8765/api/v1/health
curl http://127.0.0.1:8765/api/v1/features/coverage
curl -X POST http://127.0.0.1:8765/api/v1/features/reccobeats/enrich \
  -H "Content-Type: application/json" \
  -d "{\"only_missing\": true, \"limit\": 5}"
```

UI : `npm run dev` → `/features`

## 3.5 — Optimisation ReccoBeats batch

Statut : **DONE**

### Livrables

- `GET /v1/audio-features?ids=` (≤40 ids : Spotify track ID, ISRC, ReccoBeats ID)
- [`core/app/reccobeats/parsing.py`](../core/app/reccobeats/parsing.py), `get_audio_features_batch` dans le client
- [`core/app/features/reccobeats_batch.py`](../core/app/features/reccobeats_batch.py) + refactor [`enrichment.py`](../core/app/features/enrichment.py)
- Settings `RECCOBEATS_HTTP_BATCH_SIZE`, `RECCOBEATS_DB_UPSERT_BATCH_SIZE`
- Tests mock batch + non-régression enrichissement

### Validation

```bash
cd core
uv run pytest tests/test_reccobeats_client.py tests/test_reccobeats_batch_parsing.py \
  tests/test_reccobeats_enrich_job.py -q
```

## Limites restantes

- Pas de recherche ReccoBeats par ISRC/title (API non documentée) — résolution batch via Spotify ID ou ISRC local.
- Pas de merge multi-source actif (`POST /features/merge/recompute`) — phase 4+.
- Pas de tests frontend automatisés (Vitest absent).
- Job worker in-process (thread) — un seul job `reccobeats_enrichment` (`queued`/`running`) à la fois.
- Pas de `job_items` ni concurrence HTTP parallèle entre chunks (phase ultérieure).
