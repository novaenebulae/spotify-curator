# Phase 7 — Clustering visuel

Tags: #backlog #phase-7 #clustering #umap #hdbscan #embeddings

## But

Explorer la bibliothèque par similarité musicale via une carte 2D, en utilisant le socle enrichi de la phase 6 : ReccoBeats, Essentia low-level, embeddings, moods, genres/styles, vocal/acoustic/electronic.

## Definition of Done phase

- Les livrables de phase sont présents.
- Les tests minimum passent.
- Les commandes de validation sont documentées.
- La documentation est à jour.
- Aucun secret, cache, modèle lourd ou fichier audio n'est commité.
- Aucune régression sur les phases précédentes.
- Le clustering consomme `FeatureRegistry`, `FeatureResolver` et `TrackFeatureView`.
- La carte est utilisable avec environ 5000 titres.

## 7.1 — Feature profiles

Statut : TODO

### Sous-tâches

- Profil `generalist`.
- Profil `mood`.
- Profil `timbre`.
- Profil `rhythm`.
- Profil `embedding`.
- YAML profiles.
- Validation features requises.
- Warnings si couverture insuffisante.

## 7.2 — Matrice features

Statut : TODO

### Sous-tâches

- Sélection tracks.
- Chargement `TrackFeatureView`.
- Imputation.
- Normalisation.
- Gestion valeurs manquantes.
- Rapport coverage par feature.
- Tests matrice.

## 7.3 — UMAP

Statut : TODO

### Sous-tâches

- Paramètres.
- Random seed.
- Persist x/y.
- Job clustering.
- Tests small matrix.
- Stocker profil + paramètres.

## 7.4 — HDBSCAN

Statut : TODO

### Sous-tâches

- Clusters.
- Probabilities.
- Outliers.
- Labels.
- Persist memberships.
- Résumé par cluster.

## 7.5 — Carte UI

Statut : TODO

### Sous-tâches

- Afficher points.
- Zoom/pan.
- Couleur par cluster/feature/playlist/genre/mood.
- Tooltip.
- Sélection.
- Filtres.
- Panneau détail cluster/track.
- Canvas si SVG trop lent.

## 7.6 — Playlist depuis cluster

Statut : TODO

### Sous-tâches

- Sélection cluster.
- Sélection manuelle de points.
- Envoyer vers playlist preview phase 5.
- Export sélection CSV/JSON.
- Ajouter warning si cluster contient beaucoup d'outliers.

## Critères phase

- Carte utilisable avec 5000 tracks.
- Clusters persistés.
- Outliers visibles.
- Sélection cluster utilisable dans le moteur de playlist.
