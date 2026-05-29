# Spotify Library Curator & Playlist Engine — Documentation Cursor enrichie

Tags: #projet #spotify #cursor #documentation #tauri #svelte #fastapi #docker #sqlite

## Objectif de ce kit

Ce dossier remplace et enrichit les documents Markdown précédents afin que Cursor puisse développer le projet de manière incrémentale, sans perdre le contexte métier, technique et fonctionnel.

La documentation est structurée pour être utilisée ainsi :

1. Cursor lit `AGENTS.md`.
2. Cursor lit les documents `docs/00` à `docs/15`.
3. Cursor lit uniquement le backlog de la phase en cours.
4. Cursor propose un plan sans coder.
5. L’utilisateur valide.
6. Cursor implémente une tâche courte.
7. Cursor teste.
8. Cursor documente.
9. Cursor met à jour le backlog.
10. Cursor passe à la tâche suivante.

## Documents principaux

| Fichier | Rôle |
|---|---|
| `AGENTS.md` | Contexte permanent à donner à Cursor. |
| `docs/00-project-brief.md` | Vision produit, périmètre, objectifs. |
| `docs/01-architecture.md` | Architecture desktop + core Docker + workers. |
| `docs/02-repository-structure.md` | Structure du monorepo et responsabilités des dossiers. |
| `docs/03-development-workflow.md` | Méthode de travail incrémentale avec Cursor. |
| `docs/04-backlog-by-phase.md` | Roadmap synthétique et dépendances entre phases. |
| `docs/05-domain-model.md` | Modèle de données SQLite détaillé. |
| `docs/06-api-contract.md` | Contrats API par phase. |
| `docs/06-spotify-integration.md` | OAuth PKCE, scopes, Spotify API, rate limits. |
| `docs/07-audio-analysis-pipeline.md` | ReccoBeats, yt-dlp, FFmpeg, Essentia, embeddings. |
| `docs/08-playlist-engine.md` | Moteur de règles, scoring, preview, sync. |
| `docs/09-ui-specification.md` | Spécification UI complète par écran. |
| `docs/10-testing-strategy.md` | Tests backend, frontend, intégration, smoke Docker. |
| `docs/11-security-and-privacy.md` | Secrets, tokens, audio temporaire, droits Spotify. |
| `docs/12-decisions.md` | Décisions techniques validées. |
| `docs/13-error-handling-and-observability.md` | Erreurs API, logs, jobs, diagnostics. |
| `docs/14-configuration.md` | Variables d’environnement, volumes, profils. |
| `docs/15-cursor-rules.md` | Règles spécifiques à Cursor pour ce projet. |
| `backlog/phase-0.md` à `backlog/phase-9.md` | Backlogs détaillés. |
| `backlog/phase-1.5.md` | Consolidation schéma / API / migrations (avant phase 2). |

## Migrations SQLite (Alembic)

Le core applique une migration initiale unique (`0001_initial`) au démarrage (`alembic upgrade head`).

**Nouvelle installation** : la base est créée automatiquement dans `data/`.

**Réinitialiser la base locale** (données de dev uniquement) :

```powershell
docker compose down
Remove-Item -Force data\spotify_curator.sqlite, data\spotify_curator.sqlite-wal, data\spotify_curator.sqlite-shm -ErrorAction SilentlyContinue
docker compose up --build
```

Si vous conservez une ancienne base (révisions `0001_baseline` / `0003_phase15_backfill`), le core tente un réalignement automatique vers `0001_initial` au démarrage. En cas d'échec, supprimez le fichier SQLite comme ci-dessus.

**Tests** : chaque test utilise un fichier SQLite temporaire via `DATABASE_URL`.

Commandes utiles :

```bash
cd core
uv run alembic current
uv run alembic upgrade head
uv run pytest -q
```

**Logs Docker** : `docker compose up` (sans `-d`) ou `docker compose logs -f core-api` pour suivre les requêtes HTTP (`--access-log`) et le démarrage. Sur Windows, `SQLITE_JOURNAL_MODE=DELETE` est défini dans Compose pour éviter les écritures SQLite très lentes sur le volume `data/`.

## Règles absolues

- Ne jamais commiter de secrets Spotify, tokens OAuth, fichiers audio, modèles lourds, caches ou exports personnels.
- Ne jamais exposer le core sur `0.0.0.0` en développement local : utiliser `127.0.0.1:8765`.
- Ne jamais télécharger de morceau complet pour l’analyse standard : uniquement des segments temporaires de 30 secondes maximum.
- Toute action modifiant Spotify doit passer par un dry-run, une confirmation UI et une vérification des scopes.
- Chaque phase doit préserver les phases précédentes.
- Cursor doit toujours proposer un plan avant de coder une tâche importante.
