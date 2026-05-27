# AGENTS.md — Instructions permanentes pour Cursor

Tags: #cursor #agents #spotify-curator #instructions

## Rôle

Tu développes `Spotify Library Curator & Playlist Engine`, une application desktop locale de sauvegarde, exploration, analyse et génération de playlists Spotify.

Tu dois travailler comme un assistant de développement senior : incrémental, prudent, explicite, testable.

## Documents à lire en priorité

1. `docs/00-project-brief.md`
2. `docs/01-architecture.md`
3. `docs/02-repository-structure.md`
4. `docs/03-development-workflow.md`
5. `docs/12-decisions.md`
6. Le backlog de la phase en cours dans `backlog/`
7. Les règles applicables dans `.cursor/rules/`

La spécification complète d’origine est conservée dans :

```text
docs/source/specification_projet_spotify_playlist_curator_docker.md
```

## Décisions non négociables

- Application desktop standalone.
- UI Tauri + Svelte/SvelteKit côté Windows.
- Core Python dans Docker.
- API locale exposée uniquement sur `127.0.0.1`.
- SQLite comme base locale persistante.
- Docker Desktop + WSL2 comme cible Windows.
- Docker Compose pour orchestrer core et workers.
- Essentia via Docker, pas en installation native Windows.
- Analyse audio par segments temporaires.
- Segment audio <= 30 secondes.
- Pas de téléchargement complet standard des morceaux.
- Pas de stockage audio permanent par défaut.
- Toute écriture Spotify sensible exige dry-run + confirmation.
- Les usages DJ/mix sont optionnels, pas centraux.
- Le projet doit rester généraliste pour tous styles musicaux.

## Interdits

Ne pas :

- remplacer Tauri/Svelte par Electron, React ou Angular ;
- remplacer SQLite par PostgreSQL pour le MVP ;
- introduire Django, Celery, RabbitMQ ou backend hébergé ;
- exposer l’API sur `0.0.0.0` ;
- coder des chemins Windows absolus dans le core ;
- stocker des secrets dans le repo ;
- télécharger ou conserver des morceaux complets par défaut ;
- implémenter plusieurs phases en une seule passe ;
- ajouter des dépendances lourdes sans justification ;
- modifier une décision structurante sans mettre à jour `docs/12-decisions.md`.

## Méthode obligatoire

Pour chaque tâche :

1. Identifier la phase.
2. Lire le backlog de la phase.
3. Proposer un plan court.
4. Lister les fichiers à modifier.
5. Implémenter uniquement le périmètre demandé.
6. Ajouter ou adapter les tests.
7. Donner les commandes de vérification.
8. Signaler limites et risques restants.
9. Mettre à jour la documentation si nécessaire.

## Statuts backlog

```text
TODO
IN_PROGRESS
BLOCKED
REVIEW
DONE
DEFERRED
```

## Definition of Done globale

Une tâche est terminée seulement si :

- le code est implémenté ;
- les tests pertinents passent ;
- les erreurs principales sont gérées ;
- les commandes de validation sont documentées ;
- la documentation est mise à jour si nécessaire ;
- aucun secret, cache, modèle lourd ou fichier audio n’est commité ;
- les critères d’acceptation sont remplis.
