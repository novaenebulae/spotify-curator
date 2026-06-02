# Prompt Cursor — Phase 5.3 — Playlist preview engine

Objectif : implémenter le moteur de génération de preview : source selection, filtres stricts, scoring, diversité, ordering, persistance et explications.

## À lire avant de coder

```text
docs/08-playlist-engine.md
docs/18-feature-consumption-contract.md
backlog/phase-5.md
```

## Préconditions

Doivent exister :

```text
FeatureRegistry
FeatureResolver
TrackFeatureView
PlaylistRule validation
playlist_rules CRUD
generated_playlists / generated_playlist_items tables
```

Si une précondition manque, signale-la avant de continuer.

## Modules à créer ou compléter

```text
core/app/playlists/candidates.py
core/app/playlists/filters.py
core/app/playlists/scoring.py
core/app/playlists/diversity.py
core/app/playlists/ordering.py
core/app/playlists/explanations.py
core/app/playlists/preview_service.py
core/app/database/repositories/generated_playlists.py
core/app/api/v1/playlists.py
```

Les noms peuvent suivre l'existant.

## Pipeline à implémenter

```text
PlaylistRule
  ↓
validate
  ↓
source selection
  ↓
FeatureResolver.load_views(track_ids)
  ↓
strict filters
  ↓
weighted scoring
  ↓
diversity constraints
  ↓
ordering
  ↓
persist generated playlist
  ↓
return preview
```

## Source selection phase 5

Supporter :

```text
liked_tracks
playlists_include
playlists_exclude
track_ids_include
track_ids_exclude
```

Préparer avec warning :

```text
clusters_include
clusters_exclude
seed_tracks
```

## Filtres stricts

Implémenter au minimum :

```text
bpm
energy
valence
danceability
feature_confidence
availability_status
market_status
exclude artists
exclude albums
dedup ISRC
```

Chaque exclusion doit produire une raison structurée.

## Missing feature policy

Respecter :

```text
required=true + missing -> exclusion FEATURE_MISSING
required=false + missing -> warning
future unavailable -> FEATURE_NOT_AVAILABLE_YET
low confidence -> exclusion si confidence filter strict, sinon warning
```

## Scoring

Implémenter :

```text
weighted components
normalization 0..1
valence_inverse
missing component skip
weight renormalization
score_details_json
SCORE_NOT_COMPUTABLE
```

## Diversité

Implémenter :

```text
max_tracks_per_artist
max_tracks_per_album
avoid_duplicate_isrc
avoid_same_artist_consecutive
stable selection
```

## Ordering

Implémenter au minimum :

```text
score_desc
score_asc
recently_added_desc
recently_added_asc
random_seeded
artist_spread
```

Les modes futurs doivent retourner warning ou erreur claire :

```text
ORDERING_MODE_NOT_AVAILABLE_YET
```

## Endpoint preview

Ajouter :

```text
POST /api/v1/generated-playlists/preview
GET /api/v1/generated-playlists
GET /api/v1/generated-playlists/{generated_playlist_id}
```

Réponse preview attendue :

```json
{
  "generated_playlist_id": "...",
  "summary": {
    "candidate_count": 1000,
    "excluded_count": 920,
    "scored_count": 80,
    "selected_count": 80,
    "warnings": []
  },
  "items": [],
  "exclusions_sample": []
}
```

## Tests attendus

```text
source liked tracks
source playlist include/exclude
filter bpm
filter energy
filter missing required
filter missing optional
future feature warning
scoring simple
scoring renormalization
score not computable
diversity max artist
diversity max album
dedup ISRC
avoid same artist consecutive
ordering stable
preview persisted
read generated playlist
```

## Contraintes

- Ne pas écrire dans Spotify.
- Ne pas ajouter dry-run sync dans cette tâche sauf structure nécessaire.
- Ne pas ajouter UI.
- Ne pas ajouter TensorFlow/clustering.
- Garder services testables indépendamment des routes.

## Validation

```bash
cd core
uv run pytest -q
uv run ruff check .
```

## Réponse attendue

Fournis :

```text
- modules ajoutés ;
- endpoints ajoutés ;
- format des score details ;
- exemples de reasons ;
- tests ajoutés ;
- commandes exécutées ;
- risques restants.
```
