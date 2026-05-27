# 03 — Workflow de développement avec Cursor

Tags: #workflow #cursor #phases

## Cycle de phase

1. Lire `AGENTS.md`.
2. Lire les docs de contexte.
3. Lire `backlog/phase-X.md`.
4. Demander un plan.
5. Implémenter une tâche courte.
6. Tester.
7. Corriger.
8. Documenter.
9. Revue de phase.
10. Phase suivante.

## Cycle de tâche

1. Copier la tâche du backlog.
2. Demander à Cursor de résumer le périmètre.
3. Demander la liste des fichiers.
4. Valider le plan.
5. Implémenter.
6. Lancer tests.
7. Mettre à jour le statut.

## Statuts

```text
TODO
IN_PROGRESS
BLOCKED
REVIEW
DONE
DEFERRED
```

## Branches

```text
phase-0/bootstrap
phase-0/core-api-health
phase-1/spotify-oauth
phase-4/yt-dlp-segments
```

## Commits

```text
phase(0): bootstrap monorepo
core: add health endpoint
docker: add core api service
db: add initial sqlite models
docs: update architecture decisions
test: add healthcheck tests
```
