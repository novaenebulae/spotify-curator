# 05 — Modèle de données SQLite

Tags: #sqlite #database #domain-model #sqlalchemy

## Principes

La base SQLite est la source locale de vérité. Elle doit permettre :

- import Spotify relançable ;
- snapshots historiques ;
- diff entre états ;
- recherche/filtres ;
- détection doublons ;
- features multi-source ;
- jobs relançables ;
- analyse audio traçable ;
- génération playlist ;
- synchronisation dry-run ;
- backup/restore.

## Conventions

- Clés primaires internes : `id` string UUID ou integer selon choix existant, mais cohérent.
- Timestamps : ISO UTC ou `DateTime(timezone=True)` si support SQLAlchemy.
- JSON : stocké en TEXT JSON ou type JSON SQLAlchemy portable.
- Raw payloads : conserver la réponse brute pour audit.
- Upsert : imports relançables sans doublons.
- Index : tous les champs de recherche/filtre.

## Phase 1.5 — État implémenté (2026-05)

**Implémenté** : migration Alembic `0001_initial` ; `settings` (id/key/value_json) ; `docker_runtime_checks` ; `oauth_pkce_states` ; champs jobs enrichis ; `liked_tracks.is_current` / timestamps ; `playlist_tracks` enrichi ; `normalized_*` sur tracks/artists/albums ; `external_ids.source` / `external_type` / `confidence`.

**Mapping doc** : `tracks.name` = titre canonique (`canonical_title` doc) ; PK `INTEGER` sur tracks/artists/albums (pas UUID).

**Cible future** : PK UUID ; table générique `snapshot_tracks` ; `snapshot_diffs` persisté ; champs album `release_date_precision`, `album_type`.

## Tables phase 0

### settings

| Champ | Type | Notes |
|---|---|---|
| id | PK | |
| key | text unique | nom setting |
| value_json | text | valeur JSON |
| is_sensitive | bool | false par défaut ; les secrets ne doivent pas être stockés ici |
| created_at | datetime | |
| updated_at | datetime | |

### docker_runtime_checks

| Champ | Type | Notes |
|---|---|---|
| id | PK | |
| check_name | text | docker_available, compose_available... |
| service_name | text nullable | |
| image_name | text nullable | |
| image_tag | text nullable | |
| command | text | commande exécutée |
| exit_code | int nullable | |
| stdout | text nullable | tronqué si nécessaire |
| stderr | text nullable | tronqué si nécessaire |
| success | bool | |
| created_at | datetime | |

## Tables phase 1 — Spotify backup

### artists

| Champ | Type | Notes |
|---|---|---|
| id | PK | |
| canonical_name | text | nom affiché |
| normalized_name | text indexed | pour recherche/doublons |
| created_at | datetime | |
| updated_at | datetime | |

### albums

| Champ | Type | Notes |
|---|---|---|
| id | PK | |
| canonical_name | text | |
| normalized_name | text indexed | |
| release_date | text nullable | Spotify peut fournir année ou date complète |
| release_date_precision | text nullable | year/month/day |
| album_type | text nullable | album/single/compilation |
| created_at | datetime | |
| updated_at | datetime | |

### tracks

| Champ | Type | Notes |
|---|---|---|
| id | PK | |
| canonical_title | text indexed | |
| normalized_title | text indexed | |
| duration_ms | int indexed | |
| explicit | bool | |
| created_at | datetime | |
| updated_at | datetime | |

### track_artists

| Champ | Type | Notes |
|---|---|---|
| track_id | FK tracks | |
| artist_id | FK artists | |
| position | int | ordre artistes |

Contrainte unique : `(track_id, artist_id, position)`.

### spotify_artists

| Champ | Type | Notes |
|---|---|---|
| id | PK | |
| artist_id | FK artists | |
| spotify_artist_id | text unique indexed | |
| spotify_uri | text | |
| href | text nullable | |
| external_url | text nullable | |
| raw_json | text | |
| created_at | datetime | |
| updated_at | datetime | |

### spotify_albums

| Champ | Type | Notes |
|---|---|---|
| id | PK | |
| album_id | FK albums | |
| spotify_album_id | text unique indexed | |
| spotify_uri | text | |
| href | text nullable | |
| external_url | text nullable | |
| images_json | text nullable | |
| raw_json | text | |
| created_at | datetime | |
| updated_at | datetime | |

### spotify_tracks

| Champ | Type | Notes |
|---|---|---|
| spotify_track_id | text PK | |
| track_id | FK tracks | unique |
| album_id | FK albums nullable indexed | phase 2 — lien album pour recherche/tri |
| spotify_uri | text | |
| href | text nullable | |
| external_url | text nullable | |
| popularity | int nullable | |
| preview_url | text nullable | |
| is_playable | bool nullable | |
| available_markets_json | text nullable | |
| linked_from_spotify_track_id | text nullable | pour relink |
| restrictions_json | text nullable | |
| market_status | text indexed | available/unavailable/missing/unknown |
| last_seen_at | datetime indexed | |
| raw_json | text | |
| created_at | datetime | |
| updated_at | datetime | |

### external_ids

| Champ | Type | Notes |
|---|---|---|
| id | PK | |
| track_id | FK tracks indexed | |
| source | text indexed | spotify/reccobeats/musicbrainz/youtube |
| external_type | text indexed | isrc/reccobeats_id/video_id |
| external_value | text indexed | |
| confidence | float | 0..1 |
| created_at | datetime | |

Contrainte unique recommandée : `(source, external_type, external_value, track_id)`.

### liked_tracks

| Champ | Type | Notes |
|---|---|---|
| id | PK | |
| track_id | FK tracks indexed | |
| spotify_track_id | text indexed | |
| added_at | datetime indexed | date Spotify |
| is_current | bool indexed | présent dans dernier import |
| first_seen_at | datetime | |
| last_seen_at | datetime | |
| raw_json | text nullable | |

Contrainte unique : `spotify_track_id`.

### playlists

| Champ | Type | Notes |
|---|---|---|
| id | PK | |
| spotify_playlist_id | text unique indexed | |
| name | text indexed | |
| description | text nullable | |
| owner_id | text nullable | |
| owner_display_name | text nullable | |
| public | bool nullable | |
| collaborative | bool | |
| snapshot_id_spotify | text nullable | |
| track_count | int | |
| raw_json | text | |
| first_seen_at | datetime | |
| last_seen_at | datetime | |
| created_at | datetime | |
| updated_at | datetime | |

### playlist_tracks

| Champ | Type | Notes |
|---|---|---|
| id | PK | |
| playlist_id | FK playlists indexed | |
| track_id | FK tracks nullable indexed | null si Spotify item vide |
| spotify_track_id | text nullable indexed | |
| position | int | ordre dans playlist |
| added_at | datetime nullable | |
| added_by | text nullable | |
| is_local | bool | Spotify local track |
| is_current | bool indexed | |
| null_reason | text nullable | unavailable/local/episode/unknown |
| raw_json | text nullable | |
| first_seen_at | datetime | |
| last_seen_at | datetime | |

Index : `(playlist_id, position)`, `(playlist_id, spotify_track_id)`.

### snapshots

Table générique recommandée pour liked/playlists/full.

| Champ | Type | Notes |
|---|---|---|
| id | PK | |
| snapshot_type | text indexed | liked/playlists/full |
| status | text | creating/complete/failed |
| track_count | int | |
| playlist_count | int | |
| metadata_json | text | |
| hash | text nullable | |
| created_at | datetime indexed | |

### snapshot_tracks

| Champ | Type | Notes |
|---|---|---|
| id | PK | |
| snapshot_id | FK snapshots indexed | |
| track_id | FK tracks nullable indexed | |
| spotify_track_id | text nullable indexed | |
| context_type | text indexed | liked/playlist |
| playlist_id | FK playlists nullable | |
| position | int nullable | |
| added_at | datetime nullable | |
| status | text | present/null/unavailable |
| payload_json | text nullable | |

### snapshot_diffs

| Champ | Type | Notes |
|---|---|---|
| id | PK | |
| from_snapshot_id | FK snapshots | |
| to_snapshot_id | FK snapshots | |
| summary_json | text | |
| result_json | text | |
| created_at | datetime | |

## Tables génériques jobs

### jobs

| Champ | Type | Notes |
|---|---|---|
| id | PK | |
| job_type | text indexed | import, enrichment, analysis, clustering... |
| status | text indexed | pending/running/success/failed/cancelled/rate_limited |
| progress_current | int | |
| progress_total | int nullable | |
| current_step | text nullable | |
| attempt_count | int | |
| max_attempts | int | |
| next_retry_at | datetime nullable | |
| last_error | text nullable | |
| result_json | text nullable | |
| created_at | datetime | |
| started_at | datetime nullable | |
| finished_at | datetime nullable | |

## Tables phase 2 — Gestion bibliothèque

### library_actions

| Champ | Type | Notes |
|---|---|---|
| id | PK | |
| action_type | text indexed | unlike_tracks/restore_liked_tracks/create_backup_playlist/tag_tracks |
| status | text indexed | previewed/applied/failed/cancelled |
| filter_json | text nullable | filtres ayant produit la sélection |
| selected_track_ids_json | text nullable | sélection explicite |
| affected_count | int | |
| dry_run | bool indexed | obligatoire par défaut |
| spotify_applied | bool | false en phase 2 |
| result_json | text | titres affectés, erreurs, etc. |
| warning_json | text nullable | |
| created_by_context | text nullable | ui/api/import |
| created_at | datetime | |
| completed_at | datetime nullable | |

### duplicate_groups optionnelle

Peut être calculée à la demande ou persistée.

| Champ | Type | Notes |
|---|---|---|
| id | PK | |
| strategy | text | isrc/title_artist/duration/all |
| confidence | float | |
| reason | text | |
| track_ids_json | text | |
| created_at | datetime | |

## Tables phase 3 — Features ReccoBeats

### feature_sources

| Champ | Type | Notes |
|---|---|---|
| id | PK | |
| name | text unique | reccobeats/local_essentia/manual |
| type | text | api/local/manual/inferred |
| priority | int | |
| enabled | bool | |
| requires_audio | bool | |
| requires_api_key | bool | |
| source_version | text nullable | |
| created_at | datetime | |

### audio_features

| Champ | Type | Notes |
|---|---|---|
| id | PK | |
| track_id | FK tracks indexed | |
| source | text indexed | reccobeats/local_essentia/... |
| source_version | text | |
| pipeline_version | text nullable | |
| confidence | float indexed | |
| acousticness | float nullable | 0..1 |
| danceability | float nullable | 0..1 |
| energy | float nullable | 0..1 |
| instrumentalness | float nullable | 0..1 |
| key | int nullable | 0..11 |
| key_confidence | float nullable | |
| camelot_key | text nullable | |
| liveness | float nullable | |
| loudness | float nullable | dB |
| mode | int nullable | 0/1 |
| speechiness | float nullable | |
| tempo | float nullable | BPM |
| tempo_confidence | float nullable | |
| valence | float nullable | |
| spectral_centroid | float nullable | |
| spectral_rolloff | float nullable | |
| spectral_contrast | float nullable | |
| mfcc_summary_json | text nullable | |
| chroma_summary_json | text nullable | |
| hpcp_summary_json | text nullable | |
| onset_rate | float nullable | |
| dynamic_range | float nullable | |
| integrated_loudness | float nullable | |
| vocal_presence | float nullable | |
| electronic_acoustic_score | float nullable | |
| arousal | float nullable | |
| mood_happy | float nullable | |
| mood_sad | float nullable | |
| mood_aggressive | float nullable | |
| mood_relaxed | float nullable | |
| mood_party | float nullable | |
| energy_profile_score | float nullable | |
| calm_score | float nullable | |
| intensity_score | float nullable | |
| focus_score | float nullable | |
| background_score | float nullable | |
| playlist_fit_score | float nullable | |
| discovery_score | float nullable | |
| is_active | bool indexed | valeur active fusionnée |
| created_at | datetime | |
| updated_at | datetime | |

Contrainte unique recommandée : `(track_id, source, source_version, pipeline_version)`.

### audio_feature_raw_payloads

| Champ | Type | Notes |
|---|---|---|
| id | PK | |
| track_id | FK tracks indexed | |
| source | text indexed | |
| source_version | text | |
| request_json | text nullable | |
| response_json | text | |
| status_code | int nullable | |
| fetched_at | datetime | |

## Tables phase 4 — Audio local

### audio_download_jobs

| Champ | Type | Notes |
|---|---|---|
| id | PK | |
| job_id | FK jobs nullable | |
| track_id | FK tracks indexed | |
| provider | text | ytdlp |
| source_url | text nullable | |
| status | text indexed | pending/running/success/failed/rate_limited/skipped/cancelled |
| attempt_count | int | |
| max_attempts | int | |
| rate_limited | bool | |
| last_error | text nullable | |
| next_retry_at | datetime nullable | |
| created_at | datetime | |
| started_at | datetime nullable | |
| finished_at | datetime nullable | |

### track_segments

| Champ | Type | Notes |
|---|---|---|
| id | PK | |
| track_id | FK tracks indexed | |
| analysis_job_id | FK audio_analysis_jobs nullable | |
| download_job_id | FK audio_download_jobs nullable | |
| start_seconds | float | |
| end_seconds | float | |
| duration_seconds | float | CHECK <= 30 |
| segment_type | text | A/B/C/manual |
| source | text | youtube/cache/test |
| source_url_hash | text nullable indexed | pas forcément URL brute |
| temporary_path | text nullable | |
| file_hash | text nullable | |
| features_json | text nullable | |
| confidence | float nullable | |
| created_at | datetime | |
| deleted_at | datetime nullable | |

### audio_analysis_jobs

| Champ | Type | Notes |
|---|---|---|
| id | PK | |
| job_id | FK jobs nullable | |
| track_id | FK tracks indexed | |
| segment_id | FK track_segments nullable | |
| analysis_level | text indexed | essentia_lowlevel/essentia_tensorflow/allinone/openl3/clustering |
| docker_service | text | |
| image_name | text | |
| image_tag | text | |
| pipeline_version | text | |
| input_path | text nullable | |
| output_path | text nullable | |
| status | text indexed | |
| attempt_count | int | |
| last_error | text nullable | |
| started_at | datetime nullable | |
| finished_at | datetime nullable | |
| created_at | datetime | |

## Tables phase 6/7 — Embeddings et clustering

### track_embeddings

| Champ | Type | Notes |
|---|---|---|
| id | PK | |
| track_id | FK tracks indexed | |
| source | text indexed | openl3/discogs_effnet/essentia_tf |
| model_name | text | |
| model_version | text | |
| model_hash | text nullable | |
| dimension | int | |
| vector_json | text | liste floats ou chemin cache si lourd |
| confidence | float nullable | |
| created_at | datetime | |

### clusters

| Champ | Type | Notes |
|---|---|---|
| id | PK | |
| algorithm | text | hdbscan |
| feature_profile | text indexed | generalist/mood/timbre |
| parameters_json | text | |
| description | text nullable | |
| user_label | text nullable | |
| created_at | datetime | |

### cluster_memberships

| Champ | Type | Notes |
|---|---|---|
| id | PK | |
| cluster_id | FK clusters indexed | |
| track_id | FK tracks indexed | |
| cluster_label | int | -1 pour outlier |
| probability | float nullable | |
| umap_x | float | |
| umap_y | float | |
| created_at | datetime | |

## Tables phase 5/8 — Playlist engine

### playlist_rules

| Champ | Type | Notes |
|---|---|---|
| id | PK | |
| name | text indexed | |
| description | text nullable | |
| rule_json | text | configuration complète |
| rule_yaml | text nullable | version éditable |
| version | int | |
| enabled | bool | |
| created_at | datetime | |
| updated_at | datetime | |

### generated_playlists

| Champ | Type | Notes |
|---|---|---|
| id | PK | |
| playlist_rule_id | FK playlist_rules nullable | |
| name | text | |
| status | text | previewed/synced/failed |
| target_size | int | |
| actual_size | int | |
| score_summary_json | text nullable | |
| config_json | text | |
| created_at | datetime | |

### generated_playlist_items

| Champ | Type | Notes |
|---|---|---|
| id | PK | |
| generated_playlist_id | FK generated_playlists indexed | |
| track_id | FK tracks indexed | |
| position | int | |
| final_score | float | |
| score_details_json | text | |
| selected_reason | text nullable | |
| created_at | datetime | |

### sync_jobs

| Champ | Type | Notes |
|---|---|---|
| id | PK | |
| job_id | FK jobs nullable | |
| generated_playlist_id | FK generated_playlists | |
| target_spotify_playlist_id | text nullable | |
| sync_mode | text | create/replace/add_only/remove_obsolete |
| dry_run | bool | true par défaut |
| status | text | pending/previewed/applied/failed |
| diff_json | text | |
| created_at | datetime | |
| finished_at | datetime nullable | |

### sync_logs

| Champ | Type | Notes |
|---|---|---|
| id | PK | |
| sync_job_id | FK sync_jobs indexed | |
| level | text | info/warning/error |
| message | text | |
| context_json | text nullable | |
| created_at | datetime | |

## Tags utilisateur

### user_tags

| Champ | Type |
|---|---|
| id | PK |
| name | text unique indexed |
| color | text nullable |
| created_at | datetime |

### track_user_tags

| Champ | Type |
|---|---|
| track_id | FK tracks |
| tag_id | FK user_tags |
| created_at | datetime |

## Index recommandés

- `tracks.normalized_title`
- `artists.normalized_name`
- `albums.normalized_name`
- `external_ids.external_value`
- `liked_tracks.added_at`
- `liked_tracks.is_current`
- `playlist_tracks.playlist_id`
- `playlist_tracks.spotify_track_id`
- `spotify_tracks.spotify_track_id`
- `spotify_tracks.market_status`
- `spotify_tracks.last_seen_at`
- `jobs.status`
- `jobs.job_type`
- `audio_features.track_id`
- `audio_features.source`
- `audio_features.is_active`
- `library_actions.created_at`

## Contraintes critiques

- `track_segments.duration_seconds <= 30`.
- `dry_run = true` pour toute action Spotify avant confirmation explicite.
- `spotify_track_id` unique dans `spotify_tracks`.
- Données phase 1 jamais supprimées par migration phase 2+.
- Raw payloads conservés pour audit.
- Fichiers audio supprimés après analyse, mais résultats conservés.
