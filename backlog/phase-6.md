# Phase 6 — Clustering visuel

Tags: #backlog #phase-6 #clustering #umap #hdbscan

## But

Explorer la bibliothèque par similarité musicale via une carte 2D.


## Definition of Done phase

- Les livrables de phase sont présents.
- Les tests minimum passent.
- Les commandes de validation sont documentées.
- La documentation est à jour.
- Aucun secret, cache, modèle lourd ou fichier audio n’est commité.
- Aucune régression sur les phases précédentes.


## 6.1 — Feature profiles

Statut : TODO

### Sous-tâches

- Profil généraliste.
- Profil mood.
- Profil timbre.
- Profil rhythm.
- YAML profiles.
- Validation features requises.

## 6.2 — Matrice features

Statut : TODO

### Sous-tâches

- Sélection tracks.
- Imputation.
- Normalisation.
- Gestion valeurs manquantes.
- Tests matrice.

## 6.3 — UMAP

Statut : TODO

### Sous-tâches

- Paramètres.
- Random seed.
- Persist x/y.
- Job clustering.
- Tests small matrix.

## 6.4 — HDBSCAN

Statut : TODO

### Sous-tâches

- Clusters.
- Probabilities.
- Outliers.
- Labels.
- Persist memberships.

## 6.5 — Carte UI

Statut : TODO

### Sous-tâches

- Afficher points.
- Zoom/pan.
- Couleur par cluster/feature/playlist.
- Tooltip.
- Sélection.
- Filtres.

## 6.6 — Playlist depuis cluster

Statut : TODO

### Sous-tâches

- Sélection cluster.
- Envoyer vers playlist preview.
- Export sélection.

## Critères phase

- Carte utilisable avec 5000 tracks.
- Clusters persistés.
- Outliers visibles.
