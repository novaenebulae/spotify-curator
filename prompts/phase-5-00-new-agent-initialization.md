# Prompt Cursor — Phase 5.0 — Initialisation nouvel agent

Tu es un nouvel agent Cursor sur le projet Spotify Library Curator & Playlist Engine.

Tu ne dois pas supposer avoir le contexte d'un chat précédent. Tu dois reconstruire le contexte depuis la documentation du dépôt et l'état du code.

## Objectif général

Démarrer la phase 5 : Playlist generator v1.

La phase 5 doit livrer :

```text
- FeatureRegistry ;
- FeatureResolver ;
- TrackFeatureView ;
- PlaylistRule JSON/YAML ;
- validation ;
- CRUD minimal règles ;
- filtres stricts ;
- scoring explicable ;
- diversité ;
- preview persistée ;
- dry-run Spotify sans écriture ;
- UI Playlist Builder.
```

Ordre projet conservé :

```text
Phase 5 → Phase 6 → Phase 7
```

Mais la phase 5 doit être conçue pour l'arrivée de la phase 7 : embeddings, moods, voice/instrumental, Essentia TensorFlow.

## Règle d'architecture principale

```text
Tout ce qui consomme des features doit passer par :
FeatureRegistry → FeatureResolver → TrackFeatureView
```

Interdictions :

```text
- Ne pas lire les payloads bruts ReccoBeats directement dans le moteur de playlists.
- Ne pas lire les JSON Essentia directement dans le moteur de playlists.
- Ne pas hardcoder les features dans le scoring sans passer par FeatureRegistry.
- Ne pas créer un moteur séparé pour les futures features phase 7.
- Ne pas ajouter de write Spotify réel en phase 5.
```

## Documents à lire avant toute proposition

Lis dans cet ordre :

```text
AGENTS.md
README.md
docs/01-architecture.md
docs/02-repository-structure.md
docs/03-development-workflow.md
docs/04-backlog-by-phase.md
docs/05-domain-model.md
docs/06-api-contract.md
docs/07-audio-analysis-pipeline.md
docs/08-playlist-engine.md
docs/09-ui-specification.md
docs/12-decisions.md
docs/14-configuration.md
docs/16-job-execution-model-and-worker-parallelism.md
docs/17-audio-preview-and-segment-strategy.md
docs/18-feature-consumption-contract.md
backlog/phase-4.md
backlog/phase-4-validation.md
backlog/phase-5.md
```

## État supposé du projet

Phases 0 à 4 livrées :

- core FastAPI Dockerisé ;
- Tauri/Svelte ;
- SQLite ;
- Spotify OAuth/import/snapshots ;
- gestion bibliothèque ;
- ReccoBeats batch ;
- phase 4 audio hybride Deezer/YouTube ;
- previews Deezer UI ;
- workers audio Docker persistants ;
- Essentia low-level ;
- merge features ;
- UI coverage/features.

Tu dois vérifier cet état dans le code avant de commencer.

## Première tâche demandée

Ne code pas immédiatement.

Produit d'abord un plan d'implémentation phase 5 découpé en tâches courtes :

```text
1. audit code existant lié tracks/features/playlists/jobs ;
2. FeatureRegistry / FeatureResolver / TrackFeatureView ;
3. migrations DB playlist rules/generated playlists/sync jobs ;
4. PlaylistRule validation ;
5. CRUD rules ;
6. source selection ;
7. filters ;
8. scoring ;
9. diversity ;
10. preview persistence ;
11. dry-run sync ;
12. UI ;
13. tests/docs/review.
```

Pour chaque tâche, indique :

```text
- fichiers probables ;
- migration oui/non ;
- endpoints ;
- tests ;
- risques ;
- validation attendue.
```

Attends validation humaine avant de modifier la DB ou de créer de gros modules.

## Contraintes phase 5

- Dry-run obligatoire.
- Aucune écriture Spotify réelle.
- Pas de phase 6 clustering.
- Pas de phase 7 TensorFlow.
- Les champs phase 6/7 peuvent exister dans les schémas, mais doivent retourner warnings si utilisés trop tôt.
- Tests mockés pour Spotify si dry-run nécessite une playlist cible.
- Documentation mise à jour à chaque étape.

## Critères d'acceptation phase 5

```text
- Une règle simple génère une preview.
- Les scores sont explicables.
- Les exclusions sont explicables.
- Le dry-run sync ne modifie pas Spotify.
- Les features futures ne cassent pas le moteur.
- Le clustering phase 6 pourra réutiliser FeatureResolver.
- La phase 7 pourra ajouter embeddings/moods sans refonte du moteur.
```
