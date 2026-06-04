# 13 — Erreurs, observabilité et diagnostics

Tags: #errors #logs #jobs #diagnostics

## Objectif

Rendre les erreurs compréhensibles côté UI et exploitables côté développement.

## Format erreur API

**Implémenté (phase 1.5)** via handlers FastAPI dans `core/app/observability/errors.py` : `ApiError`, `HTTPException`, validation Pydantic, `SpotifyAuthError`, `SpotifyRateLimited`, erreurs 500.

```json
{
  "error": {
    "code": "VALIDATION_ERROR",
    "message": "Invalid page_size",
    "details": { "page_size": "must be <= 200" },
    "retryable": false
  }
}
```

## Niveaux de logs

- `DEBUG` : détails techniques, jamais tokens.
- `INFO` : étapes normales.
- `WARNING` : fallback, retry, data partielle.
- `ERROR` : échec action/job.
- `CRITICAL` : corruption DB, Docker impossible.

## Logs jobs

Chaque job doit fournir :

- `job_type` ;
- `status` ;
- progression ;
- étape courante ;
- tentative ;
- erreur ;
- timestamps.

## Statuts jobs

**API** (`GET /api/v1/jobs/{id}`) :

```text
pending
running
success
failed
cancelled
rate_limited
```

Mapping depuis SQLite : `queued` → `pending`, `succeeded` → `success` ([`core/app/jobs/status_mapping.py`](../core/app/jobs/status_mapping.py)).

**Implémenté** : statut job DB **`partial`** (succès + échecs items) pour jobs workers ; API expose souvent `partial` tel quel (mapping `partial_success` encore incomplet).

**Implémenté (6.9c)** : `GET /api/v1/jobs/{job_id}/events` (taxonomie `stage_created`, `segment_ready`, `stage_started`, `stage_failed`, `model_missing`, `cleanup_done`, …) ; `GET /api/v1/workers` avec `metadata.stage_name` pendant le traitement d'un item.

**Cible restante** : mapping API `partial_success` uniforme — [`16-job-execution-model-and-worker-parallelism.md`](16-job-execution-model-and-worker-parallelism.md) §3 et §17.

**Liste tracks** : en-têtes perf optionnels si `TRACKS_PERF_LOG=1` (`X-Tracks-Perf-Ms`, etc.) — voir [`backlog/phase-2.5-perf.md`](../backlog/phase-2.5-perf.md).

## Retry

Stratégie recommandée :

- erreurs réseau : retry ;
- 429 : respecter `Retry-After` ;
- validation : pas de retry ;
- fichier audio introuvable : retry limité ;
- erreur parsing JSON : pas de retry sans correction.

## Diagnostics runtime

Diagnostics phase 0+ :

- Docker version ;
- Docker Compose version ;
- core health ;
- SQLite writable ;
- chemins volumes ;
- ffmpeg available phase 4 ;
- yt-dlp available phase 4 ;
- Essentia image available phase 4 ;
- TensorFlow image available phase 6 ;
- models present phase 6.

## Endpoint rapport système

Phase 9 : `/maintenance/system-report`

Inclure :

- version app ;
- version core ;
- versions Docker ;
- DB path redacted ;
- counts tracks/playlists/features/jobs ;
- cache size ;
- last failed jobs ;
- models status.

Exclure :

- tokens ;
- secrets ;
- raw payloads complets ;
- fichiers audio.

## UI erreurs

Chaque erreur doit afficher :

- message lisible ;
- action possible ;
- bouton retry si retryable ;
- détails techniques repliables.

## Erreurs spécifiques par domaine

### Spotify

- non connecté ;
- token expiré ;
- scope manquant ;
- rate limit ;
- playlist inaccessible ;
- import partiel.

### Audio

- source introuvable ;
- mauvaise correspondance ;
- segment trop long ;
- yt-dlp failed ;
- ffmpeg failed ;
- Essentia failed ;
- cleanup failed.

### Features

- source indisponible ;
- feature manquante ;
- confidence faible ;
- merge conflict.

### Playlist engine

- règle invalide ;
- aucun candidat ;
- features insuffisantes ;
- dry-run requis ;
- write scope absent.
