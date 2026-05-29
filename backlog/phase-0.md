# Phase 0 — Cadrage technique et socle exécutable

Tags: #backlog #phase-0 #bootstrap

## But

Créer un socle projet local, reproductible, testable et observable.


## Definition of Done phase

- Les livrables de phase sont présents.
- Les tests minimum passent.
- Les commandes de validation sont documentées.
- La documentation est à jour.
- Aucun secret, cache, modèle lourd ou fichier audio n’est commité.
- Aucune régression sur les phases précédentes.


## 0.1 — Initialiser le dépôt monorepo

Statut : DONE

### Sous-tâches

- Créer structure `app/`, `core/`, `docker/`, `docs/`, `backlog/`.
- Ajouter `.gitignore` complet.
- Ajouter `.env.example` sans secret.
- Ajouter README minimal.
- Ajouter AGENTS.md.

### Critères d’acceptation

- Structure conforme à `docs/02-repository-structure.md`.
- Dossiers data/cache/models/logs/exports ignorés par Git.

### Tests minimum

- Vérifier `git status` sans fichiers sensibles.

## 0.2 — Créer core Python minimal

Statut : DONE

### Sous-tâches

- `pyproject.toml` avec uv.
- FastAPI.
- Route `/api/v1/health`.
- Settings non sensibles.
- Tests health.

### Critères d’acceptation

- Health retourne 200.
- Tests pytest OK.

## 0.3 — Dockeriser core-api

Statut : DONE

### Sous-tâches

- Dockerfile core.
- Compose dev.
- Port bind `127.0.0.1:8765`.
- Volumes data/cache/logs.

### Critères d’acceptation

- `docker compose up` démarre.
- Jamais `0.0.0.0`.

## 0.4 — Initialiser SQLite

Statut : DONE (consolidé phase 1.5 — Alembic + `docker_runtime_checks`)

### Sous-tâches

- Database layer.
- Table `settings`.
- Table `docker_runtime_checks`.
- DB dans `data/`.

### Critères d’acceptation

- DB créée dans volume.
- Tests DB OK.

## 0.5 — Créer Tauri/Svelte vide

Statut : DONE

### Sous-tâches

- Frontend Svelte.
- Tauri config.
- Layout minimal.
- Écran paramètres placeholder.

## 0.6 — Connecter UI au core

Statut : DONE

### Sous-tâches

- Client API frontend.
- Appel `/health`.
- Affichage online/offline.

## 0.7 — Diagnostics Docker

Statut : DONE (phase 1.5 — `/runtime/docker/checks` + persistance)

### Sous-tâches

- Vérifier Docker version.
- Vérifier Compose version.
- API diagnostics.
- UI diagnostics.

## 0.8 — Smoke Essentia low-level

Statut : DONE

### Sous-tâches

- Pull image Essentia.
- Générer WAV court de test.
- Exécuter streaming extractor.
- Logger résultat.

## 0.9 — Tests et qualité

Statut : DONE

### Sous-tâches

- pytest.
- ruff.
- commandes documentées.

## 0.10 — Revue phase 0

Statut : DONE

### Livrables

- Socle exécutable.
- Documentation initiale.
- Backlog phase 1 prêt.
