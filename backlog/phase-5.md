# Phase 5 — Playlist generator v1

Tags: #backlog #phase-5 #playlist-engine

## But

Générer des playlists simples à partir de règles explicites et prévisualiser la synchronisation Spotify.


## Definition of Done phase

- Les livrables de phase sont présents.
- Les tests minimum passent.
- Les commandes de validation sont documentées.
- La documentation est à jour.
- Aucun secret, cache, modèle lourd ou fichier audio n’est commité.
- Aucune régression sur les phases précédentes.


## 5.1 — Schéma PlaylistRule

Statut : TODO

### Sous-tâches

- Pydantic schema.
- JSON/YAML import.
- Validation.
- Endpoint `/playlist-rules/validate`.
- CRUD règles minimal.

## 5.2 — Filtres stricts

Statut : TODO

### Sous-tâches

- BPM.
- Energy.
- Valence.
- Source playlists.
- Exclusions artistes/albums/tags.
- Disponibilité.
- Confidence features.

## 5.3 — Scoring v1

Statut : TODO

### Sous-tâches

- Pondérations.
- Normalisation.
- Score details.
- Explanations simples.

## 5.4 — Diversité

Statut : TODO

### Sous-tâches

- Max artiste.
- Max album.
- Dedup ISRC.
- Éviter artiste consécutif.
- Sélection stable.

## 5.5 — Preview

Statut : TODO

### Sous-tâches

- `generated_playlists`.
- `generated_playlist_items`.
- Endpoint `/generated-playlists/preview`.
- UI preview.
- Export preview.

## 5.6 — Dry-run sync

Statut : TODO

### Sous-tâches

- Endpoint `/sync/dry-run`.
- Comparer playlist candidate/Spotify cible.
- Modes create/replace/add_only/remove_obsolete.
- Aucun write sans apply explicite.

## Critères phase

- Une règle simple génère une preview.
- Les scores sont explicables.
- Dry-run sync n’écrit pas dans Spotify.
