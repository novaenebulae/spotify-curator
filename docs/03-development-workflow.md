# 03 — Workflow de développement avec Cursor

Tags: #workflow #cursor #phases #quality

## Principe général

Le projet doit être développé par phases, puis par tâches courtes. Cursor ne doit pas recevoir tout le projet en une seule demande d’implémentation.

## Cycle de phase

1. Lire `AGENTS.md`.
2. Lire les docs `docs/00` à `docs/15`.
3. Lire `backlog/phase-X.md`.
4. Auditer le code existant.
5. Proposer un plan.
6. Attendre validation.
7. Implémenter tâche par tâche.
8. Tester chaque tâche.
9. Mettre à jour docs/backlog.
10. Faire une revue de phase.

## Cycle de tâche

Pour chaque tâche :

1. rappeler le périmètre ;
2. lister les fichiers modifiés ;
3. proposer les changements DB/API/UI/tests ;
4. attendre validation si la tâche touche l’architecture ou la DB ;
5. coder ;
6. lancer tests ciblés ;
7. lancer tests de non-régression ;
8. documenter ;
9. mettre le statut backlog à `DONE` uniquement si validé.

## Statuts backlog

```text
TODO        Non commencé
IN_PROGRESS En cours
BLOCKED     Bloqué par une décision ou erreur externe
REVIEW      Implémenté, en attente de revue humaine
DONE        Validé et testé
DEFERRED    Reporté volontairement
```

## Règles de validation

Une tâche n’est `DONE` que si :

- le code est implémenté ;
- les tests minimum passent ;
- la documentation impactée est mise à jour ;
- aucune régression phase précédente n’est introduite ;
- les commandes de validation sont notées.

## Branches conseillées

```text
phase-0/bootstrap
phase-1/spotify-backup
phase-2/library-management
phase-3/reccobeats-enrichment
phase-4/local-audio-analysis
phase-5/playlist-generator-v1
phase-6/visual-clustering
phase-7/advanced-analysis
phase-8/advanced-playlist-engine
phase-9/packaging-polish
```

Pour des sous-tâches :

```text
phase-2/tracks-search-api
phase-2/library-table-ui
phase-4/ytdlp-segment-provider
phase-5/rule-schema
```

## Commits

Format recommandé :

```text
phase(2): add tracks search API
core: add library actions dry-run service
ui: add library management table
db: add library_actions table
test: add duplicate detection tests
docs: update API contract for phase 2
```

## Commandes de validation types

Backend :

```bash
docker compose -f docker-compose.dev.yml up -d core-api
docker compose -f docker-compose.dev.yml exec core-api uv run pytest
docker compose -f docker-compose.dev.yml exec core-api uv run ruff check .
docker compose -f docker-compose.dev.yml exec core-api uv run ruff format --check .
```

Frontend :

```bash
cd app/frontend
npm install
npm run lint
npm run test
npm run build
```

API smoke :

```bash
curl http://127.0.0.1:8765/api/v1/health
curl http://127.0.0.1:8765/api/v1/runtime/config
```

Docker :

```bash
docker --version
docker compose version
docker compose -f docker-compose.dev.yml ps
```

## Règles Cursor

Cursor doit éviter :

- les gros patchs multi-phases ;
- les changements de stack non demandés ;
- les migrations destructives ;
- l’ajout de logique audio avant phase 4 ;
- l’ajout de clustering avant phase 6 ;
- les appels Spotify write avant dry-run/confirmation.

Cursor doit privilégier :

- tests mockés ;
- services isolés ;
- endpoints documentés ;
- schémas Pydantic explicites ;
- erreurs structurées ;
- migrations réversibles ;
- commits courts.

## Revue de phase

À la fin de chaque phase, produire :

- livrables réalisés ;
- tâches restantes ;
- dette technique ;
- commandes de validation ;
- risques pour la phase suivante ;
- captures ou description UI si pertinent ;
- mise à jour du backlog.
