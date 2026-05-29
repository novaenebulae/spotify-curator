# Phase 7 — Analyse avancée

Tags: #backlog #phase-7 #essentia #tensorflow #embeddings

## But

Ajouter embeddings et modèles TensorFlow Essentia pour features avancées.


## Definition of Done phase

- Les livrables de phase sont présents.
- Les tests minimum passent.
- Les commandes de validation sont documentées.
- La documentation est à jour.
- Aucun secret, cache, modèle lourd ou fichier audio n’est commité.
- Aucune régression sur les phases précédentes.


## 7.1 — Image essentia-tensorflow

Statut : TODO

### Sous-tâches

- Dockerfile.
- Dépendances.
- Scripts inference.
- Build local.
- Smoke WAV court.

## 7.2 — Gestion modèles

Statut : TODO

### Sous-tâches

- Registry modèles.
- `models/` non commité.
- Version.
- Hash.
- Endpoint `/models/status`.

## 7.3 — Embeddings

Statut : TODO

### Sous-tâches

- Discogs EffNet ou OpenL3.
- Stocker `track_embeddings`.
- Dimension.
- Model hash.
- Tests vector shape.

## 7.4 — Moods/styles

Statut : TODO

### Sous-tâches

- Happy/sad/aggressive/relaxed/party.
- Arousal/valence.
- Electronic/acoustic.
- Genre/style si disponible.

## 7.5 — Voice/instrumental

Statut : TODO

### Sous-tâches

- Vocal presence.
- Instrumental score.
- Confidence.
- Merge features.

## Critères phase

- Image build.
- Modèles non commités.
- Embeddings persistés.
- Features avancées visibles.
