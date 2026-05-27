# 05 — Modèle de données

Tags: #sqlite #database #domain-model

## Tables principales

```text
tracks
artists
albums
track_artists
spotify_tracks
spotify_albums
spotify_artists
liked_tracks
liked_track_snapshots
playlists
playlist_snapshots
playlist_tracks
external_ids
feature_sources
audio_features
audio_feature_raw_payloads
audio_download_jobs
track_segments
audio_analysis_jobs
track_embeddings
clusters
cluster_memberships
user_tags
track_user_tags
playlist_rules
generated_playlists
generated_playlist_items
sync_jobs
sync_logs
library_actions
settings
docker_runtime_checks
```

## Contraintes critiques

- `track_segments.duration_seconds <= 30`.
- Jobs persistés avec statut, erreurs, tentatives.
- Sources de features versionnées.
- Actions Spotify tracées.
- Snapshots comparables.
- Audio temporaire supprimé après analyse.

## Tables à créer en phase 0

- `settings`
- `docker_runtime_checks`

Les tables métier complètes seront ajoutées progressivement à partir de la phase 1.
