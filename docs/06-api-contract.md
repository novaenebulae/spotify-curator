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

Query params :

- `q`
- `artist`
- `album`
- `isrc`
- `liked`
- `playlist_id`
- `in_any_playlist`
- `missing_from_playlists`
- `duplicate_group_id`
- `availability_status`
- `snapshot_status`
- `min_duration_ms`
- `max_duration_ms`
- `added_after`
- `added_before`
- `sort`
- `order`
- `page`
- `page_size`

Réponse :

```json
{
  "items": [
    {
      "track_id": "trk_1",
      "spotify_track_id": "...",
      "spotify_uri": "spotify:track:...",
      "title": "Track title",
      "artists": ["Artist"],
      "album": "Album",
      "duration_ms": 240000,
      "explicit": false,
      "popularity": 50,
      "isrc": "...",
      "liked": true,
      "liked_added_at": "2026-05-29T10:00:00Z",
      "playlist_count": 2,
      "playlists": [
        {
          "playlist_id": "pl_1",
          "spotify_playlist_id": "...",
          "name": "Playlist"
        }
      ],
      "availability_status": "available",
      "duplicate_status": "none",
      "last_seen_at": "2026-05-29T10:00:00Z",
      "raw_available": true
    }
  ],
  "page": 1,
  "page_size": 50,
  "total": 1,
  "sort": "liked_added_at",
  "order": "desc"
}
```

## Phase 2 — Doublons

### `GET /library/duplicates`

Query params :

- `strategy`: `isrc`, `title_artist`, `duration`, `all`
- `min_confidence`
- `page`
- `page_size`

Réponse :

```json
{
  "groups": [
    {
      "group_id": "dup_1",
      "strategy": "isrc",
      "confidence": 1.0,
      "reason": "same_isrc",
      "tracks": []
    }
  ],
  "page": 1,
  "page_size": 20,
  "total_groups": 1
}
```

## Phase 2 — Absents/disparus

### `GET /library/missing-tracks`

Query params :

- `snapshot_id`
- `status`
- `page`
- `page_size`

Réponse :

```json
{
  "items": [],
  "summary": {
    "removed_from_liked": 0,
    "missing_from_current_import": 0,
    "unavailable_on_spotify": 0,
    "null_playlist_track": 0,
    "possibly_relinked": 0
  },
  "page": 1,
  "page_size": 50,
  "total": 0
}
```

## Phase 2 — Actions bibliothèque

### `POST /library/actions/dry-run`

Body :

```json
{
  "action_type": "unlike_tracks",
  "track_ids": ["trk_1"],
  "filter": {},
  "options": {
    "backup_playlist_name": "Backup",
    "reason": "cleanup"
  }
}
```

Actions :

- `unlike_tracks`
- `restore_liked_tracks`
- `create_backup_playlist`
- `tag_tracks` plus tard
- `delete_local_cache` plus tard

Réponse :

```json
{
  "action_id": "act_1",
  "dry_run": true,
  "action_type": "unlike_tracks",
  "affected_count": 1,
  "affected_tracks": [
    {
      "track_id": "trk_1",
      "spotify_track_id": "...",
      "title": "Track",
      "artists": ["Artist"],
      "reason": "selected"
    }
  ],
  "warnings": [],
  "blocked": false,
  "requires_write_scope": true
}
```

### `GET /library/actions`

### `GET /library/actions/{action_id}`

## Phase 3 — Features / ReccoBeats

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
