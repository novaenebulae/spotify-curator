# Prompt Cursor — Phase 5.2 — PlaylistRule validation + CRUD minimal

Objectif : implémenter le schéma de règle, la validation et le CRUD minimal des règles de playlists.

## À lire avant de coder

```text
docs/08-playlist-engine.md
docs/18-feature-consumption-contract.md
backlog/phase-5.md
```

## Précondition

La tâche précédente doit avoir introduit :

```text
FeatureRegistry
FeatureResolver
TrackFeatureView
tables playlist_rules si nécessaires
```

Si ce n'est pas le cas, arrête-toi et signale l'écart.

## Livrables backend

Créer ou compléter :

```text
core/app/playlists/schemas.py
core/app/playlists/rule_validation.py
core/app/playlists/rules_service.py
core/app/database/repositories/playlist_rules.py
core/app/api/v1/playlists.py ou playlist_rules.py
```

Le nom exact des fichiers peut suivre les conventions du repo.

## Schéma PlaylistRule

Supporter le format documenté dans `docs/08-playlist-engine.md` :

```text
name
description
target_size
engine_version
source
filters
weights
constraints
ordering
spotify
```

Champs phase 6/7 autorisés mais non actifs :

```text
clusters_include
clusters_exclude
cluster_diversity
seed_tracks
mood_* features
embedding_similarity
voice/instrumental features
```

## Endpoint validation

Ajouter :

```text
POST /api/v1/playlist-rules/validate
```

Réponse attendue :

```json
{
  "valid": true,
  "errors": [],
  "warnings": [],
  "normalized_rule": {}
}
```

Erreurs bloquantes minimum :

```text
RULE_INVALID_SCHEMA
UNKNOWN_FEATURE
UNKNOWN_FILTER
UNKNOWN_ORDERING_MODE
UNKNOWN_SYNC_MODE
INVALID_RANGE
NO_SOURCE_SELECTED
NO_SCORING_COMPONENTS
TARGET_SIZE_INVALID
```

Warnings minimum :

```text
FEATURE_NOT_AVAILABLE_YET
CLUSTER_SOURCE_NOT_AVAILABLE_YET
SEED_TRACKS_NOT_AVAILABLE_IN_PHASE_5
WRITE_SCOPE_NOT_AVAILABLE
LOW_FEATURE_COVERAGE
```

## CRUD minimal

Ajouter endpoints :

```text
POST /api/v1/playlist-rules
GET /api/v1/playlist-rules
GET /api/v1/playlist-rules/{rule_id}
PUT /api/v1/playlist-rules/{rule_id}
DELETE /api/v1/playlist-rules/{rule_id}
```

`DELETE` peut être logique (`enabled=false`) si plus cohérent avec le projet.

## Presets

Ajouter des presets backend ou seed local si simple :

```text
Dark / Intense
Calm / Focus
High Energy
Recently Added
Discover Forgotten Likes
Clean Library
```

Les presets phase 7 peuvent être déclarés avec warnings, mais ne doivent pas casser la validation.

## Tests attendus

```text
valid basic rule
invalid YAML/JSON
unknown feature
future feature optional -> warning
future feature required -> warning or error according to schema policy
invalid range
no source selected
no scoring components
create/list/read/update/disable rule
```

## Contraintes

- Ne pas implémenter la génération preview dans cette tâche.
- Ne pas ajouter d'écriture Spotify.
- Ne pas ajouter l'UI.
- Ne pas ajouter TensorFlow.

## Validation

```bash
cd core
uv run pytest -q
uv run ruff check .
```

## Réponse attendue

Fournis :

```text
- endpoints ajoutés ;
- schémas ajoutés ;
- fichiers modifiés ;
- exemples de payload ;
- tests ajoutés ;
- commandes exécutées ;
- risques restants.
```
