# 00 — Project brief

Tags: #brief #spotify #curation #mvp #desktop

## Vision

Application desktop standalone pour sauvegarder, explorer, enrichir, analyser et trier automatiquement une bibliothèque Spotify personnelle.

L’objectif n’est pas de reproduire Spotify, mais de construire un moteur personnel de curation configurable selon BPM, tonalité, énergie, valence, genres, clusters, période, artistes, albums, tags, playlists sources, similarité, exclusions, seed tracks, ambiance, niveau vocal, cohérence sonore et structure musicale.

## Problèmes

1. Grande bibliothèque difficile à trier.
2. Audio features Spotify non fiables comme base.
3. Titres pouvant disparaître ou devenir indisponibles.
4. Besoin de règles de playlist plus fines.
5. Certaines features nécessitent une analyse locale.

## MVP inclus

- Desktop visuel.
- Tauri + Svelte.
- Core Python dockerisé.
- Docker Compose.
- SQLite.
- Spotify OAuth.
- Import titres likés et playlists.
- Snapshots et diffs.
- Gestion bibliothèque.
- ReccoBeats.
- Jobs.
- yt-dlp + FFmpeg pour segments temporaires.
- Segment <= 30 secondes.
- Essentia low-level via Docker.
- Playlist generator v1.
- Dry-run Spotify.

## MVP exclu

- Web hébergé.
- Multi-utilisateur.
- Django.
- PostgreSQL.
- Celery/RabbitMQ.
- Stockage permanent audio.
- Téléchargement complet standard.
- Installation native Windows d’Essentia.
- Modèles ML propriétaires.
