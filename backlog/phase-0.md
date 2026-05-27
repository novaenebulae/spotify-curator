# Phase 0 — Cadrage technique

Tags: #backlog #phase-0 #spotify-curator

## But

Créer un socle projet exécutable, reproductible et observable.

## Definition of Done phase

- Les livrables de phase sont présents.
- Les tests minimum passent.
- Les commandes de validation sont documentées.
- La documentation est à jour.
- Aucun secret, cache, modèle lourd ou fichier audio n’est commité.

---

## 0.1 — Initialiser le dépôt monorepo

Statut : TODO

### Sous-tâches

- Structure dossiers
- README/AGENTS/docs/backlog
- .gitignore

### Critères d’acceptation

- Structure conforme
- Aucun secret/cache/audio

### Tests minimum

- Tests adaptés à la tâche.
- Commande de validation documentée.
- Pas de régression sur les tâches précédentes.

## 0.2 — Créer le core Python minimal

Statut : TODO

### Sous-tâches

- pyproject uv
- FastAPI
- /api/v1/health
- settings

### Critères d’acceptation

- Health 200
- pytest OK

### Tests minimum

- Tests adaptés à la tâche.
- Commande de validation documentée.
- Pas de régression sur les tâches précédentes.

## 0.3 — Dockeriser core-api

Statut : TODO

### Sous-tâches

- Dockerfile
- compose
- port 127.0.0.1:8765
- volumes

### Critères d’acceptation

- compose up OK
- pas 0.0.0.0

### Tests minimum

- Tests adaptés à la tâche.
- Commande de validation documentée.
- Pas de régression sur les tâches précédentes.

## 0.4 — Initialiser SQLite

Statut : TODO

### Sous-tâches

- database layer
- settings table
- docker_runtime_checks

### Critères d’acceptation

- DB dans data
- tests DB

### Tests minimum

- Tests adaptés à la tâche.
- Commande de validation documentée.
- Pas de régression sur les tâches précédentes.

## 0.5 — Créer Tauri/Svelte vide

Statut : TODO

### Sous-tâches

- frontend
- src-tauri
- layout
- settings placeholder

### Critères d’acceptation

- app démarre
- écran visible

### Tests minimum

- Tests adaptés à la tâche.
- Commande de validation documentée.
- Pas de régression sur les tâches précédentes.

## 0.6 — Connecter UI au core

Statut : TODO

### Sous-tâches

- client API
- appel health
- online/offline

### Critères d’acceptation

- statut visible
- erreur lisible

### Tests minimum

- Tests adaptés à la tâche.
- Commande de validation documentée.
- Pas de régression sur les tâches précédentes.

## 0.7 — Diagnostics Docker

Statut : TODO

### Sous-tâches

- docker version
- compose version
- persist checks

### Critères d’acceptation

- API diagnostics
- UI diagnostics

### Tests minimum

- Tests adaptés à la tâche.
- Commande de validation documentée.
- Pas de régression sur les tâches précédentes.

## 0.8 — Smoke Essentia low-level

Statut : TODO

### Sous-tâches

- pull image
- WAV test
- streaming_extractor_music

### Critères d’acceptation

- smoke exécutable
- résultat loggé

### Tests minimum

- Tests adaptés à la tâche.
- Commande de validation documentée.
- Pas de régression sur les tâches précédentes.

## 0.9 — Tests et qualité

Statut : TODO

### Sous-tâches

- pytest
- ruff
- commandes

### Critères d’acceptation

- tests/lint documentés

### Tests minimum

- Tests adaptés à la tâche.
- Commande de validation documentée.
- Pas de régression sur les tâches précédentes.

## 0.10 — Revue phase 0

Statut : TODO

### Sous-tâches

- phase review
- limites
- docs

### Critères d’acceptation

- livrables validés

### Tests minimum

- Tests adaptés à la tâche.
- Commande de validation documentée.
- Pas de régression sur les tâches précédentes.
