# Phase 2 — Gestion bibliothèque

Tags: #backlog #phase-2 #spotify-curator

## But

Explorer, filtrer, auditer et préparer des actions sur les titres importés.


## Definition of Done phase

- Les livrables de phase sont présents.
- Les tests minimum passent.
- Les commandes de validation sont documentées.
- La documentation est à jour.
- Aucun secret, cache, modèle lourd ou fichier audio n’est commité.
- Aucune régression sur les phases précédentes.


## 2.1 — API recherche tracks

Statut : TODO

### Sous-tâches

- Implémenter `GET /api/v1/tracks`.
- Ajouter filtres cumulables : q, artist, album, isrc, liked, playlist_id, disponibilité, snapshot status, durée, date.
- Ajouter pagination.
- Ajouter tri stable.
- Ajouter index DB.
- Éviter doublons dus aux jointures.

### Critères d’acceptation

- Recherche sur 5000+ titres acceptable.
- Résultats paginés.
- Tests filtres OK.

### Tests minimum

- q titre/artiste.
- filtre playlist.
- filtre ISRC.
- tri asc/desc.
- pagination.

## 2.2 — Table UI bibliothèque

Statut : TODO

### Sous-tâches

- Créer écran Gestion bibliothèque.
- Table tracks.
- Colonnes principales.
- Filtres visibles.
- Tri.
- Pagination.
- Sélection multiple.
- États loading/empty/error/offline.

### Critères d’acceptation

- Table utilisable avec les données importées.
- Sélection fiable.
- Erreurs lisibles.

## 2.3 — Doublons

Statut : TODO

### Sous-tâches

- Détection ISRC.
- Détection spotify_track_id contextuel.
- Détection titre/artiste normalisés.
- Détection durée proche ±3s.
- Endpoint `/library/duplicates`.
- Vue groupes doublons.

### Critères d’acceptation

- Doublons listés sans suppression automatique.
- Confiance et raison affichées.

## 2.4 — Absents/disparus

Statut : TODO

### Sous-tâches

- Exploiter diffs snapshots.
- Endpoint `/library/missing-tracks`.
- Résumé par statut.
- Vue UI dédiée ou filtre.

### Critères d’acceptation

- Statuts distincts : removed, missing, unavailable, null, relinked.

## 2.5 — Actions dry-run

Statut : TODO

### Sous-tâches

- Endpoint `/library/actions/dry-run`.
- Actions unlike, restore, create_backup_playlist.
- Vérifier scopes write mais ne pas appliquer.
- Modale UI confirmation dry-run.
- Warnings.

### Critères d’acceptation

- Aucune écriture Spotify réelle par défaut.
- Dry-run historisé.

## 2.6 — Historique actions

Statut : TODO

### Sous-tâches

- Table `library_actions`.
- Endpoints list/detail.
- UI historique.
- Détail résultats.

### Critères d’acceptation

- Chaque dry-run est traçable.

## Documentation à mettre à jour

- `docs/05-domain-model.md`.
- `docs/06-api-contract.md`.
- `docs/09-ui-specification.md`.
- `docs/10-testing-strategy.md`.
