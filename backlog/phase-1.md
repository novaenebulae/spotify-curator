# Phase 1 — Spotify Library Backup

Tags: #backlog #phase-1 #spotify-curator

## But

Importer et sauvegarder la bibliothèque Spotify.

## Definition of Done phase

- Les livrables de phase sont présents.
- Les tests minimum passent.
- Les commandes de validation sont documentées.
- La documentation est à jour.
- Aucun secret, cache, modèle lourd ou fichier audio n’est commité.

---

## 1.1 — Configuration Spotify

Statut : TODO

### Sous-tâches

- .env.example
- settings non sensibles
- redirect URI

### Critères d’acceptation

- pas de secret
- config lisible

### Tests minimum

- Tests adaptés à la tâche.
- Commande de validation documentée.
- Pas de régression sur les tâches précédentes.

## 1.2 — OAuth PKCE

Statut : TODO

### Sous-tâches

- start/callback/status/logout
- scopes
- token dev

### Critères d’acceptation

- login local
- status OK

### Tests minimum

- Tests adaptés à la tâche.
- Commande de validation documentée.
- Pas de régression sur les tâches précédentes.

## 1.3 — SpotifyClient

Statut : TODO

### Sous-tâches

- pagination
- retry
- erreurs

### Critères d’acceptation

- tests mocks

### Tests minimum

- Tests adaptés à la tâche.
- Commande de validation documentée.
- Pas de régression sur les tâches précédentes.

## 1.4 — Import liked tracks

Statut : TODO

### Sous-tâches

- fetch
- normalisation
- raw_json

### Critères d’acceptation

- DB remplie
- relançable

### Tests minimum

- Tests adaptés à la tâche.
- Commande de validation documentée.
- Pas de régression sur les tâches précédentes.

## 1.5 — Import playlists

Statut : TODO

### Sous-tâches

- playlists
- items
- pagination

### Critères d’acceptation

- items stockés

### Tests minimum

- Tests adaptés à la tâche.
- Commande de validation documentée.
- Pas de régression sur les tâches précédentes.

## 1.6 — Snapshots

Statut : TODO

### Sous-tâches

- liked
- playlists
- metadata

### Critères d’acceptation

- snapshot daté

### Tests minimum

- Tests adaptés à la tâche.
- Commande de validation documentée.
- Pas de régression sur les tâches précédentes.

## 1.7 — Diff snapshots

Statut : TODO

### Sous-tâches

- ajouts
- suppressions
- disparus

### Critères d’acceptation

- diff API

### Tests minimum

- Tests adaptés à la tâche.
- Commande de validation documentée.
- Pas de régression sur les tâches précédentes.

## 1.8 — Écran import

Statut : TODO

### Sous-tâches

- boutons
- jobs
- erreurs

### Critères d’acceptation

- UI import

### Tests minimum

- Tests adaptés à la tâche.
- Commande de validation documentée.
- Pas de régression sur les tâches précédentes.

## 1.9 — Exports

Statut : TODO

### Sous-tâches

- CSV
- JSON
- snapshot

### Critères d’acceptation

- export OK

### Tests minimum

- Tests adaptés à la tâche.
- Commande de validation documentée.
- Pas de régression sur les tâches précédentes.
