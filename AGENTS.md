# AGENTS — Contexte permanent Cursor

Tags: #cursor #agents #instructions #spotify-curator

## Rôle de Cursor dans ce projet

Cursor doit agir comme un développeur assistant incrémental. Il ne doit pas réinterpréter l’architecture à chaque phase. Il doit respecter les décisions déjà validées et travailler par petites tâches testables.

## Produit

Application desktop locale permettant de sauvegarder, explorer, enrichir, analyser et trier automatiquement une bibliothèque Spotify personnelle.

Objectifs principaux :

- sauvegarder localement les titres likés et playlists Spotify ;
- créer des snapshots historiques ;
- détecter les titres supprimés, disparus, indisponibles ou remplacés ;
- gérer les titres en masse avec dry-run obligatoire ;
- enrichir les tracks avec ReccoBeats et analyses audio locales ;
- générer des playlists configurables ;
- synchroniser vers Spotify uniquement après preview/dry-run ;
- conserver une architecture locale, reproductible, non hébergée.

## Architecture validée

```text
Windows
  └── Tauri / Svelte / TypeScript
          ↓ HTTP localhost
Docker Desktop + WSL2
  └── Docker Compose
          ├── core-api FastAPI / Python
          ├── job-worker
          ├── audio-downloader yt-dlp + FFmpeg
          ├── essentia-lowlevel
          ├── essentia-tensorflow
          └── clustering-worker
```

## Exécution des tâches longues

Jobs persistés SQLite, progression observable, pas de blocage HTTP. **État actuel** : threads in-process dans `core-api` ; **cible** : workers parallèles (API async, Docker Essentia persistants). Référence : [`docs/16-job-execution-model-and-worker-parallelism.md`](docs/16-job-execution-model-and-worker-parallelism.md).

## Contraintes fortes

- Tauri/Svelte reste hors Docker.
- Le core Python tourne dans Docker.
- API locale uniquement sur `127.0.0.1:8765`.
- SQLite comme base locale.
- Pas de PostgreSQL.
- Pas de Django.
- Pas de Celery/RabbitMQ.
- Pas de backend hébergé.
- Pas de multi-utilisateur.
- Pas de stockage permanent d’audio par défaut.
- Pas de morceau complet en analyse standard.
- Segments audio temporaires de 30 secondes maximum.
- Dry-run obligatoire avant toute modification Spotify.

## Stack validée

- Tauri ;
- Svelte/SvelteKit en SPA/static ;
- TypeScript ;
- Python ;
- FastAPI ;
- SQLAlchemy ou SQLModel ;
- Alembic si migrations SQLAlchemy ;
- SQLite ;
- Docker Compose ;
- uv ;
- httpx ;
- Pydantic ;
- yt-dlp ;
- FFmpeg ;
- Essentia ;
- librosa ;
- scikit-learn ;
- UMAP ;
- HDBSCAN.

## Méthode de travail obligatoire

Pour chaque phase :

1. lire la documentation projet ;
2. lire le backlog de phase ;
3. auditer l’existant ;
4. proposer un plan ;
5. attendre validation ;
6. implémenter une tâche courte ;
7. tester ;
8. corriger ;
9. documenter ;
10. mettre à jour le backlog.

## Interdictions

Cursor ne doit pas :

- ajouter une nouvelle technologie majeure sans justification ;
- déplacer l’architecture vers une application web hébergée ;
- remplacer SQLite par PostgreSQL ;
- remplacer FastAPI par Django ;
- télécharger des morceaux complets par défaut ;
- commiter `data/`, `cache/`, `models/`, `logs/`, `exports/` sauf `.gitkeep` ;
- stocker des tokens ou secrets dans le repo ;
- appliquer une action Spotify sans dry-run et confirmation.

## Qualité attendue

- Code typé autant que possible.
- Fonctions courtes.
- Services métier séparés des routes API.
- Tests unitaires et intégration pour chaque logique importante.
- Erreurs API uniformes.
- Jobs longs non bloquants.
- Logs suffisants pour diagnostiquer.
- Documentation mise à jour dans la même PR/tâche.
