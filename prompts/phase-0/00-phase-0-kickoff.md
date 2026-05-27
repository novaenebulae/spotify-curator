# Prompt Cursor — Phase 0 kickoff

Tags: #cursor #phase-0 #bootstrap

```text
Tu vas m’aider à développer le projet Spotify Library Curator & Playlist Engine.

Avant de coder, lis :
- AGENTS.md
- docs/00-project-brief.md
- docs/01-architecture.md
- docs/02-repository-structure.md
- docs/03-development-workflow.md
- docs/12-decisions.md
- backlog/phase-0.md
- .cursor/rules/*.mdc

Objectif phase 0 :
Créer un socle technique minimal, exécutable et testable :
- structure monorepo ;
- core Python FastAPI dockerisé ;
- route /api/v1/health ;
- SQLite initial ;
- Docker Compose local ;
- application Tauri/Svelte vide ;
- écran Paramètres minimal ;
- diagnostics Docker ;
- smoke test Essentia low-level.

Contraintes :
- Tauri/Svelte côté Windows, pas dans Docker.
- Core Python dans Docker.
- API uniquement sur 127.0.0.1:8765.
- SQLite dans data/.
- Pas de PostgreSQL.
- Pas de Django.
- Pas de Celery/RabbitMQ.
- Pas de Spotify OAuth, ReccoBeats, yt-dlp réel, playlist engine ou clustering dans cette phase.
- Pas de secrets dans le repo.

Travail demandé maintenant :
1. Résume le périmètre exact de la phase 0.
2. Propose l’ordre d’implémentation des tâches 0.1 à 0.10.
3. Liste les fichiers et dossiers à créer.
4. Propose les commandes de validation.
5. Identifie les risques techniques immédiats.
6. Ne code rien tant que je n’ai pas validé le plan.

Format attendu :
- Plan d’implémentation.
- Structure de fichiers.
- Commandes.
- Risques.
- Questions bloquantes uniquement si indispensables.
```
