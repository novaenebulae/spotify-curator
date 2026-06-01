# 06 — Contrats API locale

Tags: #api #fastapi #contracts #json

## Base URL

```text
http://127.0.0.1:8765/api/v1
```

## Principes

- Tous les endpoints retournent JSON.
- Toutes les erreurs utilisent le format commun.
- Les opérations longues retournent un `job_id`.
- Les endpoints destructifs doivent supporter dry-run.
- Aucun endpoint ne doit exposer de secret ou token.
- Les routes sont versionnées sous `/api/v1`.

## Format d’erreur commun

```json
{
  "error": {
    "code": "STRING_CODE",
    "message": "Human readable message",
    "details": {},
    "retryable": false
  }
}
```

Codes génériques :

| Code | Usage |
|---|---|
| `VALIDATION_ERROR` | Paramètre invalide |
| `NOT_FOUND` | Ressource absente |
| `CONFLICT` | Ressource déjà existante ou état incompatible |
| `UNAUTHORIZED_SPOTIFY` | Connexion Spotify absente ou expirée |
| `SPOTIFY_RATE_LIMITED` | Spotify rate limit |
| `EXTERNAL_SERVICE_ERROR` | Erreur ReccoBeats/yt-dlp/etc. |
| `JOB_ALREADY_RUNNING` | Job incompatible déjà actif |
| `DRY_RUN_REQUIRED` | Action réelle refusée sans dry-run |
| `WRITE_SCOPE_REQUIRED` | Scope Spotify write absent |
| `AUDIO_SEGMENT_TOO_LONG` | Segment > 30 secondes |
| `DOCKER_UNAVAILABLE` | Docker indisponible |
| `INTERNAL_ERROR` | Erreur inattendue |

## Pagination

Query params standards :

```text
page=1
page_size=50
sort=created_at
order=desc
```

Réponse standard :

```json
{
  "items": [],
  "page": 1,
  "page_size": 50,
  "total": 0,
  "sort": "created_at",
  "order": "desc"
}
```

## Jobs

> **Implémentation phase 3** : seul `GET /api/v1/jobs/{job_id}` est exposé ([`core/app/api/v1/jobs.py`](../core/app/api/v1/jobs.py)). `GET /jobs` (liste) et `POST /jobs/{id}/cancel` sont documentés ci-dessous comme **cible**. Modèle d'exécution et endpoints futurs (`/items`, `/workers`) : [`16-job-execution-model-and-worker-parallelism.md`](16-job-execution-model-and-worker-parallelism.md) §15.

### `POST /jobs/{job_id}/cancel`

Annule un job si possible.

### `GET /jobs/{job_id}`

```json
{
  "id": "job_123",
  "job_type": "spotify_import_liked_tracks",
  "status": "running",
  "progress_current": 120,
  "progress_total": 5000,
  "current_step": "fetching_saved_tracks",
  "attempt_count": 1,
  "max_attempts": 3,
  "next_retry_at": null,
  "last_error": null,
  "result": {},
  "created_at": "2026-05-29T10:00:00Z",
  "started_at": "2026-05-29T10:00:02Z",
  "finished_at": null
}
```

### `GET /jobs`

Filtres :

- `job_type`
- `status`
- `page`
- `page_size`

## Phase 0 — Runtime

> **Phase 1.5** : endpoints runtime implémentés. `GET /diagnostics` reste disponible (alias enrichi). Erreurs au format `{ "error": { ... } }`. Auth : `connected` + alias `authenticated` ; `authorize_url` + alias `authorization_url`.

### `GET /health`

```json
{
  "status": "ok",
  "service": "spotify-curator-core",
  "version": "0.1.0"
}
```

### `GET /runtime/config`

Retourne uniquement la configuration non sensible.

```json
{
  "api_base_url": "http://127.0.0.1:8765/api/v1",
  "database_configured": true,
  "spotify_client_id_configured": true,
  "export_dir": "/app/exports",
  "cache_dir": "/app/cache"
}
```

### `GET /runtime/docker/checks`

Retourne les derniers diagnostics.

### `POST /runtime/docker/checks/run`

Lance les diagnostics Docker.

Réponse :

```json
{
  "job_id": "job_docker_checks",
  "status": "pending"
}
```

## Phase 1 — Spotify Auth

### `GET /spotify/auth/start`

Démarre OAuth PKCE.

Réponse :

```json
{
  "authorization_url": "https://accounts.spotify.com/...",
  "state": "...",
  "expires_at": "2026-05-29T10:10:00Z"
}
```

### `GET /spotify/auth/callback`

Callback OAuth local. Peut retourner HTML minimal ou redirection vers l’app.

Query params :

- `code`
- `state`
- `error`

### `GET /spotify/auth/status`

```json
{
  "authenticated": true,
  "display_name": "Lucas",
  "spotify_user_id": "...",
  "scopes": ["user-library-read"],
  "expires_at": "2026-05-29T11:00:00Z",
  "token_storage": "sqlite_dev"
}
```

### `POST /spotify/auth/logout`

Supprime les tokens locaux.

```json
{
  "authenticated": false
}
```

## Phase 1 — Import Spotify

### `POST /spotify/import/liked-tracks`

Crée un job d’import des titres likés.

Body :

```json
{
  "force_refresh": false,
  "create_snapshot": true
}
```

Réponse :

```json
{
  "job_id": "job_...",
  "status": "pending"
}
```

### `POST /spotify/import/playlists`

Crée un job d’import playlists/items.

Body :

```json
{
  "include_items": true,
  "create_snapshot": true
}
```

### `POST /spotify/import/full-library`

Importe liked + playlists + snapshots.

Body :

```json
{
  "force_refresh": false,
  "create_snapshot": true
}
```

## Phase 1 — Snapshots

### `POST /library/snapshots/create`

Body :

```json
{
  "type": "full"
}
```

Valeurs : `full`, `liked`, `playlists`.

Réponse :

```json
{
  "snapshot_id": "snap_...",
  "status": "complete"
}
```

### `GET /library/snapshots`

Liste les snapshots.

### `GET /library/snapshots/{snapshot_id}`

Détail d’un snapshot.

### `POST /library/snapshots/diff`

Body :

```json
{
  "from_snapshot_id": "snap_old",
  "to_snapshot_id": "snap_new"
}
```

Réponse :

```json
{
  "from_snapshot_id": "snap_old",
  "to_snapshot_id": "snap_new",
  "liked": {
    "added": [],
    "removed": []
  },
  "playlists": {
    "added": [],
    "removed": [],
    "changed": []
  },
  "tracks": {
    "statuses": [
      {
        "status": "removed_from_liked",
        "spotify_track_id": "...",
        "spotify_playlist_id": null,
        "position": null,
        "context": {}
      }
    ]
  },
  "summary": {
    "liked": {
      "added_count": 0,
      "removed_count": 0
    },
    "playlists": {
      "added_count": 0,
      "removed_count": 0,
      "changed_count": 0
    },
    "track_status_counts": {}
  }
}
```

Statuts :

- `removed_from_liked`
- `missing_from_current_import`
- `unavailable_on_spotify`
- `null_playlist_track`
- `possibly_relinked`

## Phase 1 — Exports

### `POST /exports/liked-tracks`

Body : `{ "format": "csv" }` ou `{ "format": "json" }`.

### `POST /exports/playlists`

### `POST /exports/snapshot/{snapshot_id}`

### `POST /exports/diff`

Les réponses retournent :

```json
{
  "path": "/app/exports/liked_tracks.csv",
  "filename": "liked_tracks.csv",
  "row_count": 5000
}
```

## Phase 2 — Recherche tracks

### `GET /tracks`

Query params cumulables : `q`, `title`, `artist`, `album`, `isrc`, `liked`, `playlist_id`, `spotify_playlist_id`, `in_any_playlist`, `missing_from_playlists`, `availability_status`, `market_status`, `snapshot_status`, `duplicate_status`, `min_duration_ms`, `max_duration_ms`, `added_after`, `added_before`, `sort`, `order`, `page`, `page_size`.

Réponse :

```json
{
  "items": [
    {
      "track_id": 1,
      "spotify_track_id": "...",
      "title": "Track title",
      "artists": [{ "artist_id": 1, "spotify_artist_id": "...", "name": "Artist" }],
      "artist_names": ["Artist"],
      "album": {
        "album_id": 1,
        "spotify_album_id": "...",
        "name": "Album",
        "cover_image_url": "https://i.scdn.co/image/...",
        "cover_image_width": 64,
        "cover_image_height": 64
      },
      "external_url": "https://open.spotify.com/track/...",
      "spotify_uri": "spotify:track:...",
      "duration_ms": 240000,
      "isrc": "...",
      "liked": true,
      "is_current_liked": true,
      "playlist_count": 2,
      "playlists": [],
      "availability_status": "available",
      "market_status": "available",
      "duplicate_status": "none"
    }
  ],
  "pagination": { "page": 1, "page_size": 50, "total": 1, "total_pages": 1 },
  "sort": { "field": "liked_added_at", "order": "desc" },
  "filters": {}
}
```

**Performance (phase 2.5)** : en liste paginée, `playlists` est toujours un tableau vide ; utiliser `playlist_count` pour l’affichage table. Les détails playlist par titre ne sont pas chargés sur cet endpoint (réduction payload). Diagnostic : `TRACKS_PERF_LOG=1`, en-têtes `X-Tracks-Perf-*`, script `core/scripts/benchmark_tracks.py`.

## Phase 2 — Doublons

### `GET /library/duplicates`

Query params :

- `strategy`: `isrc`, `spotify_track_id`, `title_artist`, `title_artist_duration`, `all`
- `min_confidence`
- `page`, `page_size`

Réponse : `groups[]`, `pagination` (`total_groups`), `summary`.

Chaque groupe inclut : `reason`, `reason_label` (libellé humain), `occurrence_count`, `unique_track_count`, `is_repeated_occurrence`, `confidence`, `isrc` (si stratégie ISRC). Les `tracks[]` sont dédupliqués pour l’affichage (par `spotify_track_id`, puis empreinte titre/artiste/album/durée) avec `cover_image_url`, `external_url`, `spotify_uri`, `occurrence_count`, `contexts[]` (playlists, optionnel).

## Phase 2 UI — Résumé bibliothèque

### `GET /library/summary`

Réponse :

```json
{
  "tracks_total": 5000,
  "playlists_total": 120,
  "albums_total": 4800,
  "latest_snapshot": { "id": "...", "created_at": "..." },
  "spotify_connected": true
}
```

Utilisé par l’écran Accueil (`/`) pour les cartes statut sans multiplier les appels.

## Phase 2 — Absents/disparus

### `GET /library/missing-tracks`

Query params : `snapshot_id`, `from_snapshot_id`, `to_snapshot_id`, `status`, `page`, `page_size`.

Réponse : `items[]` avec `album_name`, `cover_image_url` (si album lié), `summary` par statut, `pagination`.

## Phase 2 — Actions bibliothèque

### `POST /library/actions/dry-run`

Body : `action_type` (`unlike_tracks`, `restore_liked_tracks`, `create_backup_playlist`), `track_ids`, `filter`, `options`.

Réponse : `action_id`, `dry_run`, `affected_count`, `affected_tracks`, `warnings`, `requires_write_scope`, `spotify_applied` (toujours `false` en phase 2).

### `GET /library/actions`

Filtres : `action_type`, `dry_run`, `status`, pagination.

### `GET /library/actions/{action_id}`

Détail avec `filter`, `selected_track_ids`, `result`, `warnings`.

## Phase 3 — Features / ReccoBeats (implémenté)

### `POST /features/reccobeats/enrich`

Body :

```json
{
  "track_ids": [1, 2, 3],
  "filter": {},
  "batch_size": 50,
  "only_missing": true,
  "retry_failed": false,
  "force_refresh": false,
  "limit": null
}
```

Réponse : `{ "job_id": "...", "status": "pending" }`.

Job type : `reccobeats_enrichment`. Erreur `409 JOB_ALREADY_RUNNING` si un job enrichissement est déjà actif.

**Batch HTTP (phase 3.5)** : le job appelle `GET /v1/audio-features?ids=` par chunks de jusqu'à `RECCOBEATS_HTTP_BATCH_SIZE` (défaut 40, env). Le champ body `batch_size` (défaut 50) contrôle uniquement la **pause** entre groupes de pistes traitées (`RECCOBEATS_BATCH_DELAY_MS`), pas la taille des requêtes ReccoBeats.

### `GET /features/coverage`

Query : `source=reccobeats|all`, `include_failed`, `include_fields`, `recent_failures_limit`.

Réponse :

```json
{
  "summary": {
    "track_count": 5000,
    "with_any_features": 4200,
    "with_reccobeats": 4100,
    "missing_reccobeats": 900,
    "failed_reccobeats": 50,
    "coverage_percent": 82.0
  },
  "sources": [],
  "fields": [{ "field": "bpm", "available_count": 4000, "coverage_percent": 80.0 }],
  "recent_failures": []
}
```

### Endpoints différés

- `GET /features/tracks/{track_id}` — phase 3+ / fusion
- `POST /features/merge/recompute` — phase 4+

## Phase 3 — Features / ReccoBeats (doc historique)

### `POST /features/reccobeats/enrich`

Body :

```json
{
  "track_ids": ["trk_1"],
  "only_missing": true,
  "force_refresh": false
}
```

Réponse : `{ "job_id": "...", "status": "pending" }`.

### `GET /features/coverage`

```json
{
  "total_tracks": 5000,
  "reccobeats_complete": 4200,
  "local_required": 800,
  "failed": 50,
  "fields": {
    "tempo": { "count": 4200, "coverage": 0.84 },
    "energy": { "count": 4200, "coverage": 0.84 }
  }
}
```

### `GET /features/tracks/{track_id}`

Retourne toutes les sources et la valeur active.

### `POST /features/merge/recompute`

Recalcule les valeurs actives multi-source.

## Phase 4 — Audio local

### `POST /audio/segments/plan`

Planifie les segments A/B/C sans télécharger.

Body :

```json
{
  "track_id": "trk_1",
  "strategy": "abc_default"
}
```

### `POST /audio/segments/download`

Crée un job yt-dlp/FFmpeg.

### `GET /audio/segments/{track_id}`

Liste les segments et statut cleanup.

### `POST /audio/analysis/lowlevel`

Crée un job Essentia low-level.

### `POST /audio/cache/cleanup`

Nettoie les fichiers temporaires.

## Phase 5 — Playlist generator v1

### `POST /playlist-rules/validate`

Valide une règle YAML/JSON.

### `POST /playlist-rules`

Crée une règle.

### `GET /playlist-rules`

Liste les règles.

### `POST /generated-playlists/preview`

Body :

```json
{
  "rule_id": "rule_1",
  "override": {}
}
```

Réponse :

```json
{
  "generated_playlist_id": "gen_1",
  "items": [],
  "summary": {
    "candidate_count": 1000,
    "selected_count": 80,
    "excluded_count": 920
  }
}
```

### `POST /sync/dry-run`

Prépare un diff Spotify.

## Phase 6 — Clustering

### `GET /clustering/profiles`

### `POST /clustering/run`

Crée un job UMAP/HDBSCAN.

### `GET /clustering/runs/{cluster_id}`

### `GET /clustering/points`

Retourne points UMAP filtrables.

## Phase 7 — Analyse avancée

### `POST /audio/analysis/tensorflow`

Crée un job embeddings/moods.

### `GET /embeddings/tracks/{track_id}`

### `GET /models/status`

Liste modèles disponibles, versions, hash.

## Phase 8 — Playlist avancée

### `POST /generated-playlists/advanced-preview`

Supporte seed tracks, curves, harmonic, discovery.

### `GET /generated-playlists/{id}/explanations`

Explique sélection/exclusion.

## Phase 9 — Packaging/maintenance

### `POST /maintenance/backup/create`

### `POST /maintenance/backup/restore`

### `POST /maintenance/cache/cleanup`

### `GET /maintenance/system-report`

Retourne diagnostic complet sans secrets.
