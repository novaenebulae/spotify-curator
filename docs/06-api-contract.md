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

## Périmètre implémenté (2026-06)

| Zone | Statut |
|---|---|
| Phases 0–4 (runtime, Spotify, library, features, audio, previews, workers) | **Implémenté** — voir sections ci-dessous |
| Phases 5–9 (playlists, clustering, TensorFlow, maintenance avancée) | **Non implémenté** — contrats de cible conservés en fin de document |

Exécution des jobs : [`16-job-execution-model-and-worker-parallelism.md`](16-job-execution-model-and-worker-parallelism.md). Previews Deezer : [`17-audio-preview-and-segment-strategy.md`](17-audio-preview-and-segment-strategy.md).

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

Implémenté dans [`core/app/api/v1/jobs.py`](../core/app/api/v1/jobs.py). Workers : [`core/app/api/v1/workers.py`](../core/app/api/v1/workers.py). Modèle d'exécution : [`16-job-execution-model-and-worker-parallelism.md`](16-job-execution-model-and-worker-parallelism.md).

### `GET /jobs`

Query : `job_type`, `status`, `limit` (défaut 20, max 100). Pas de pagination `page`/`page_size`.

Réponse :

```json
{
  "jobs": [
    {
      "id": "job_123",
      "job_type": "reccobeats_enrichment",
      "status": "running",
      "progress_current": 120,
      "progress_total": 5000,
      "current_step": "enriching_tracks",
      "created_at": "2026-05-29T10:00:00Z"
    }
  ]
}
```

### `GET /jobs/insights/latest`

Dernier job terminal par type (`essentia_lowlevel_analysis`, `audio_download`, `reccobeats_enrichment`, `preview_resolve`). Utilisé par l’UI « Last runs ».

```json
{
  "jobs": [
    {
      "job_id": "...",
      "job_type": "reccobeats_enrichment",
      "status": "succeeded",
      "finished_at": "...",
      "result_json": { "succeeded": 100, "failed": 2, "skipped": 50 }
    }
  ]
}
```

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

Statuts API : `pending`, `running`, `success`, `failed`, `partial`, `rate_limited`, `cancelled` (mapping depuis statuts DB — voir doc 16 §3).

### `GET /jobs/{job_id}/items`

Query : `limit` (défaut 100, max 500), `offset`. Liste les `job_items` du job (audio / preview / essentia).

### `POST /jobs/{job_id}/cancel`

Annule un job `queued` ou `running`. Pour `audio_download` et `essentia_lowlevel_analysis`, annule aussi les items `pending`. `preview_resolve` : annulation job en base sans `cancel_pending_for_job` sur les items (comportement partiel).

Erreur `409 JOB_NOT_CANCELLABLE` si le job n’est plus actif.

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

### `GET /diagnostics`

Alias enrichi (health + config non sensible + derniers checks Docker). Implémenté dans [`core/app/api/v1/diagnostics.py`](../core/app/api/v1/diagnostics.py).

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

Crée un job d’import des titres likés. **Pas de body** (comportement fixe côté service).

Réponse :

```json
{
  "job_id": "job_...",
  "status": "pending"
}
```

### `POST /spotify/import/playlists`

Crée un job d’import playlists/items. **Pas de body**.

### `POST /spotify/import/full-library`

> **Non implémenté** — pas de route dans [`spotify_import.py`](../core/app/api/v1/spotify_import.py). Utiliser liked + playlists séparément.

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
  "status": "completed"
}
```

### `GET /library/snapshots`

Retourne une **liste** de snapshots (pas d’enveloppe `{ items, page, total }`).

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

Query : `source=reccobeats|all`, `include_failed`, `include_fields`, `recent_failures_limit`, `failures_page`, `failures_page_size`, `failures_after` (ISO — masque les échecs antérieurs à cette date, ex. après « Clear list » UI).

Réponse (extrait) :

```json
{
  "summary": {
    "track_count": 5000,
    "with_any_features": 4200,
    "with_reccobeats": 4100,
    "missing_reccobeats": 900,
    "failed_reccobeats": 50,
    "with_essentia_lowlevel": 800,
    "coverage_percent": 82.0
  },
  "sources": [],
  "fields": [{ "field": "bpm", "available_count": 4000, "coverage_percent": 80.0 }],
  "fields_by_source": {
    "reccobeats": [],
    "essentia_lowlevel": []
  },
  "recent_failures": [],
  "failures": {
    "total": 12,
    "page": 1,
    "page_size": 20,
    "items": [
      {
        "id": "audio_download:42",
        "source": "audio_download",
        "track_id": 25,
        "title": "...",
        "artist_names": [],
        "status": "failed",
        "error_code": "DOWNLOAD_FAILED",
        "error_message": "...",
        "occurred_at": "2026-06-01T12:00:00"
      }
    ]
  }
}
```

Sources d’échecs agrégées (`FailureInsightsService`) : `reccobeats`, `essentia_lowlevel`, `deezer_preview`, `audio_download`.

### `GET /features/tracks/{track_id}`

Retourne la ligne fusionnée active (`is_active=true`) et **toutes** les sources ayant une ligne `audio_features` pour ce titre (y compris sources inactives après merge).

Réponse (extrait) :

```json
{
  "track_id": 1,
  "merged": {
    "primary_source": "essentia_lowlevel",
    "display_name": "Essentia low-level",
    "is_active": true,
    "status": "success",
    "feature_confidence": 0.85,
    "fields": { "bpm": 127.2, "key": 7, "mode": 1, "loudness": -8.2 },
    "meta": {
      "pipeline_version": "essentia_lowlevel_v1",
      "segments_used": 2,
      "analysis_decision": "deezer_preview_plus_two_youtube_segments"
    }
  },
  "sources": [
    {
      "source_name": "reccobeats",
      "display_name": "ReccoBeats",
      "is_active": false,
      "status": "success",
      "fields": { "bpm": 128, "energy": 0.71 },
      "extended": {}
    },
    {
      "source_name": "essentia_lowlevel",
      "display_name": "Essentia low-level",
      "is_active": true,
      "status": "success",
      "fields": { "bpm": 127.2, "key": 7, "mode": 1, "loudness": -8.2 },
      "extended": {
        "spectral_centroid": 2200.0,
        "spectral_rolloff": 4500.0,
        "spectral_contrast": [1.0, 2.0, 3.0],
        "dynamic_complexity": 4.5,
        "onset_rate": 2.1,
        "mfcc": [0.1, 0.2, 0.3],
        "hpcp": [0.5, 0.4, 0.3],
        "analysis_decision": "deezer_only",
        "segments_used": 1
      }
    }
  ],
  "availability": {
    "has_any_features": true,
    "has_reccobeats": true,
    "has_essentia_lowlevel": true,
    "other_sources_count": 0
  }
}
```

- **404** si le `track_id` n’existe pas.
- **200** avec `merged: null` et `sources: []` si aucune analyse.
- `extended` (source `essentia_lowlevel` uniquement) : agrégat JSON `payload.aggregated` du dernier `audio_feature_raw_payloads` :
  - scalaires : `spectral_centroid`, `spectral_rolloff`, `dynamic_complexity`, `onset_rate`
  - vecteurs : `mfcc`, `hpcp`, `spectral_contrast`
  - meta : `analysis_decision`, `segments_used`, `segments_planned`, `segments_analyzed`, `segments_missing_reason`
- Les colonnes SQL `audio_features` restent limitées au rythme/tonalité (`bpm`, `key`, `mode`, `loudness`, …) ; l’UI drawer lit `extended` pour le timbre.
- Titres analysés **avant** une mise à jour du pipeline : relancer Essentia avec `force_refresh=true` pour regénérer `aggregated` complet (merge recompute ne suffit pas).

### `POST /features/merge/recompute`

Body : `{ "track_ids": [1, 2], "limit": 5000 }`. Recalcule la ligne fusionnée active par piste.

Réponse : `{ "tracks_processed": 10, "deactivated_rows": 5 }`.

## Phase 4 — Audio local

Implémenté dans [`core/app/api/v1/audio.py`](../core/app/api/v1/audio.py). Jobs types : `audio_download`, `essentia_lowlevel_analysis` (workers profil Compose `audio`).

### `POST /audio/segments/plan`

Planifie les segments sans télécharger. `track_id` : **entier** (ID SQLite).

Body (extrait) :

```json
{
  "track_id": 1,
  "strategy": "hybrid_deezer_youtube_representative",
  "analysis_mode": "fast"
}
```

Stratégies : `hybrid_deezer_youtube_representative` (défaut), `abc_default`. Modes : `fast` (défaut), `precise`.

### `POST /audio/segments/download`

Crée un job `audio_download` (items `job_items`). Body : `track_ids`, `filter`, `only_missing`, `retry_failed`, `limit`, `strategy`, `analysis_mode`, etc.

### `GET /audio/segments/{track_id}`

`track_id` : entier. Liste les segments et statut cleanup.

### `POST /audio/analysis/lowlevel`

Crée un job `essentia_lowlevel_analysis`.

### `POST /audio/cache/cleanup`

Nettoie les fichiers temporaires.

## Phase 4 — Previews Deezer

[`core/app/api/v1/previews.py`](../core/app/api/v1/previews.py). Détail stratégie : [`17-audio-preview-and-segment-strategy.md`](17-audio-preview-and-segment-strategy.md).

### `GET /tracks/{track_id}/preview`

Query : `resolve_if_missing` (bool). Retourne la meilleure preview disponible ou démarre un job resolve unitaire si demandé. Inclut `playback_url` (chemin same-origin vers le stream ci-dessous) pour l’UI.

### `GET /tracks/{track_id}/preview/stream`

Proxy audio **same-origin** (MP3) : le core télécharge la preview Deezer (URL rafraîchie si expirée) et la renvoie au player. Évite le blocage CORB/CORS du navigateur sur les URLs CDN Deezer.

### `POST /previews/resolve`

Body : `{ "only_missing": true, "force_refresh": false, "limit": null }`. `limit` null = **tous** les titres sans preview Deezer valide (pas de plafond 5000 implicite). Job type `preview_resolve` (worker Docker `preview-resolver-worker`, profil Compose `audio`).

`POST /jobs/{id}/cancel` sur `preview_resolve` annule les `job_items` en attente et agrège `succeeded` / `not_found` dans `result` (comme `audio_download`).

### `GET /previews/coverage`

Résumé couverture previews (Deezer / any).

## Workers

### `GET /workers`

Liste les heartbeats workers (`preview_resolver`, `audio_downloader`, `essentia_lowlevel`, …). Nécessite workers Docker profil `audio` démarrés.

---

## Phase 5 — Playlist generator v1 (implémenté)

Les endpoints ci-dessous sont disponibles dans le core. Aucune écriture Spotify réelle en phase 5.

### `GET /playlist-rules/presets`

Presets initiaux (JSON embarqué côté core).

## Phase 6–9 — Non implémentées (contrats cibles)

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

## Phase 6 — Modèles Essentia TensorFlow

Gestion des modèles Essentia TensorFlow : déclaration, téléchargement explicite, vérification. Voir [`19-essentia-tensorflow-model-management.md`](19-essentia-tensorflow-model-management.md).

### `GET /models/status`

**Implémenté** ([`core/app/api/v1/models.py`](../core/app/api/v1/models.py)). Retourne le statut des modèles déclarés et des profils.

Réponse :

```json
{
  "summary": {
    "total": 18,
    "available": 2,
    "missing": 16,
    "invalid_hash": 0,
    "disabled": 0,
    "real_inference_ready": false,
    "default_profile": "phase6-recommended"
  },
  "profiles": [
    {
      "name": "phase6-minimal",
      "status": "partial",
      "available_count": 1,
      "missing_count": 11,
      "description": "Discogs EffNet + classifiers principaux"
    },
    {
      "name": "phase6-recommended",
      "status": "missing",
      "available_count": 1,
      "missing_count": 13,
      "description": "Profil phase 6 complet avec Genre Discogs519"
    },
    {
      "name": "phase6-full",
      "status": "missing",
      "available_count": 1,
      "missing_count": 16,
      "description": "Ajoute MusicNN + DEAM/MuSe pour arousal/valence"
    }
  ],
  "models": [
    {
      "model_key": "discogs_effnet_bs64",
      "display_name": "Discogs EffNet BS64",
      "task": "embedding",
      "status": "available",
      "required_for": ["style_embedding", "timbre_embedding"],
      "license": "CC BY-NC-SA 4.0",
      "local_weights_path": "essentia/feature-extractors/discogs-effnet/discogs-effnet-bs64-1.pb",
      "local_metadata_path": "essentia/feature-extractors/discogs-effnet/discogs-effnet-bs64-1.json",
      "sha256": "computed-local-hash",
      "expected_sha256": null,
      "size_bytes": 18366619
    }
  ]
}
```

### `POST /models/download`

Body :

```json
{
  "model_key": "discogs_effnet_bs64",
  "accept_license": true,
  "force": false
}
```

### `POST /models/download-profile`

Body :

```json
{
  "profile": "phase6-recommended",
  "accept_license": true,
  "force": false
}
```

Règles :

- `accept_license=true` obligatoire ;
- le téléchargement est explicite ;
- jamais de téléchargement automatique au démarrage ;
- seuls les modèles déclarés dans le manifest sont téléchargeables.

### `POST /models/verify`

Body :

```json
{
  "model_key": "discogs_effnet_bs64"
}
```

Réponse :

```json
{
  "model_key": "discogs_effnet_bs64",
  "status": "available",
  "weights_exists": true,
  "metadata_exists": true,
  "sha256": "computed-local-hash",
  "expected_sha256": null
}
```

## Phase 6 — Analyse avancée

### `POST /audio/analysis/advanced`

Crée un job `audio_analysis_pipeline`.

Body :

```json
{
  "track_ids": [1, 2, 3],
  "filter": {},
  "only_missing": true,
  "force_refresh": false,
  "analysis_mode": "fast",
  "include_lowlevel": true,
  "include_tensorflow": true,
  "pipeline_mode": "streaming",
  "model_profile": "phase6-recommended",
  "require_real_tensorflow": false
}
```

Réponse : `{ "job_id": "job_...", "status": "pending" }`.

Règles :

- si `require_real_tensorflow=true` et modèles absents → erreur `MODEL_MISSING` avant téléchargement audio ;
- si `require_real_tensorflow=false` et modèles absents → stages TensorFlow `skipped`/`model_missing`, low-level peut continuer ;
- jamais de stub en production.

### `GET /features/advanced/coverage`

Couverture embeddings, genres, moods, modèles manquants, échecs récents.

### Extension `GET /features/tracks/{track_id}`

Source `essentia_tensorflow` avec champs moods, `genre_discogs_519_*`, embedding status dans `extended`.

### `GET /embeddings/tracks/{track_id}`

Détail embedding persisté (dimension, modèle, agrégation).

### Jobs — compteurs par stage

`GET /jobs/{job_id}` peut exposer `items` par `stage_name` (pending/running/success/failed).

### Erreurs phase 6

| Code | Usage |
|---|---|
| `MODEL_MISSING` | Modèle absent |
| `MODEL_INVALID_HASH` | Hash non conforme |
| `MODEL_METADATA_MISSING` | Metadata `.json` absente |
| `MODEL_WEIGHTS_MISSING` | Poids `.pb` absent |
| `MODEL_LICENSE_NOT_ACCEPTED` | Téléchargement refusé sans acceptation licence |
| `MODEL_DOWNLOAD_FAILED` | Téléchargement impossible |
| `TENSORFLOW_INFERENCE_FAILED` | Inférence échouée |
| `STUB_INFERENCE_FORBIDDEN` | Runner stub appelé hors test |
| `EMBEDDING_SHAPE_INVALID` | Dimension inattendue |
| `ANALYSIS_STAGE_BLOCKED` | Dépendance non terminée |
| `SEGMENT_CONSUMER_PENDING` | Cleanup bloqué |
| `ADVANCED_ANALYSIS_DISABLED` | Désactivé par config |

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
