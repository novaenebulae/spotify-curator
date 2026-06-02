# Prompt Cursor — Phase 5.1 — Feature contract + DB foundations

Objectif : implémenter les fondations de la phase 5 sans encore construire tout le moteur de playlists.

## À lire avant de coder

```text
docs/05-domain-model.md
docs/07-audio-analysis-pipeline.md
docs/08-playlist-engine.md
docs/18-feature-consumption-contract.md
backlog/phase-5.md
```

## Livrables

### Backend features contract

Créer ou adapter les modules :

```text
core/app/playlists/feature_registry.py
core/app/playlists/feature_resolver.py
core/app/playlists/types.py
```

Le nom exact peut être adapté à la structure existante, mais le découpage doit rester clair.

Implémenter :

```text
FeatureDescriptor
FeatureRegistry
FeatureValue
TrackFeatureView
FeatureResolver
```

Le resolver doit s'appuyer sur les données existantes :

```text
tracks
artists
albums
spotify_tracks
external_ids
liked_tracks
playlist_tracks
audio_features
feature_sources
track_previews
```

Il doit préparer l'arrivée future de :

```text
track_embeddings
essentia_tensorflow
moods
voice/instrumental
```

mais sans les implémenter maintenant.

### Features à déclarer

Phase 5 disponibles :

```text
bpm
energy
valence
danceability
acousticness
instrumentalness
speechiness
liveness
loudness
key
mode
time_signature
duration_ms
feature_confidence
preview_available
availability_status
market_status
liked_status
playlist_membership
duplicate_status
isrc
artist_id
album_id
```

Features futures phase 7 à déclarer comme indisponibles :

```text
embedding_similarity
mood_happy_score
mood_sad_score
mood_aggressive_score
mood_relaxed_score
mood_party_score
mood_dark_score
arousal
valence_tf
voice_probability
vocal_presence_score
instrumental_focus_score
acoustic_profile_score
electronic_profile_score
```

Alias :

```text
tempo -> bpm
valence_inverse -> 1 - valence
```

### DB foundations

Vérifier si les tables phase 5 existent déjà. Sinon créer une migration Alembic pour :

```text
playlist_rules
generated_playlists
generated_playlist_items
sync_jobs
sync_logs
```

Respecter `docs/05-domain-model.md`.

Ajouter si pertinent :

```text
generated_playlists.engine_version
generated_playlists.warning_json
generated_playlist_items.exclusion_details_json nullable
```

Ne pas faire de migration destructive.

## Tests attendus

Ajouter tests unitaires pour :

```text
FeatureRegistry resolves known feature
FeatureRegistry resolves alias
FeatureRegistry rejects unknown feature
FeatureRegistry marks future feature as not available yet
FeatureResolver returns TrackFeatureView for tracks with ReccoBeats
FeatureResolver handles missing features
FeatureResolver handles low confidence
FeatureResolver exposes preview availability
```

## Contraintes

- Ne pas implémenter encore `/generated-playlists/preview`.
- Ne pas implémenter encore l'UI.
- Ne pas ajouter TensorFlow.
- Ne pas ajouter clustering.
- Ne pas lire les raw payloads dans le moteur futur.

## Validation

Lancer :

```bash
cd core
uv run alembic upgrade head
uv run pytest -q
uv run ruff check .
```

## Réponse attendue

À la fin, fournis :

```text
- fichiers modifiés ;
- migration créée ou non ;
- description FeatureRegistry ;
- description FeatureResolver ;
- tests ajoutés ;
- commandes exécutées ;
- risques restants.
```
