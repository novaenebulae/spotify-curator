<!-- FILE: prompts/phase-4-validation.md -->

# Prompt Cursor — Phase 4 validation finale

Tu travailles sur le projet Spotify Library Curator & Playlist Engine.

Objectif : valider définitivement la phase 4 avant de passer à la phase 5.

Important : cette tâche est une validation/audit. Tu ne dois pas ajouter de nouvelles fonctionnalités majeures. Tu peux corriger les bugs, écarts de documentation ou régressions bloquantes détectés pendant l'audit.

## Contexte projet

Le projet est une application desktop locale :

- Tauri/Svelte pour l'UI ;
- FastAPI Python dans Docker pour le core ;
- SQLite local dans volume Docker ;
- workers Docker persistants pour l'audio ;
- Spotify import/library déjà livré ;
- ReccoBeats livré ;
- phase 4 implémentée avec stratégie hybride Deezer + YouTube.

## Documents à lire avant toute modification

Lis d'abord :

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
docs/09-ui-specification.md
docs/14-configuration.md
docs/16-job-execution-model-and-worker-parallelism.md
docs/17-audio-preview-and-segment-strategy.md
backlog/phase-4.md
backlog/phase-4-validation.md
```

## Ce que tu dois auditer

1. Migrations phase 4 :
   - `0006_phase4_audio_local`
   - `0007_track_previews_hybrid`
   - tables `job_items`, `worker_heartbeats`, `job_events`
   - tables audio/previews
   - contrainte segment `<= 30s`

2. Workers :
   - `preview-resolver-worker`
   - `audio-downloader`
   - `essentia-lowlevel-worker`
   - heartbeats via `/api/v1/workers`
   - pas de conteneur par piste

3. Previews Deezer :
   - resolve only missing
   - limit null = toute bibliothèque manquante
   - URL preview non persistée en fichier
   - refresh URL signée si nécessaire

4. Stratégie hybride :
   - `fast`
   - `precise`
   - `deezer_only`
   - `youtube_1_segment`
   - `deezer_plus_youtube_2_segments`
   - `youtube_3_segments`
   - `local_analysis_unavailable`

5. Audio analysis :
   - download segments
   - FFmpeg WAV
   - Essentia low-level
   - parser JSON
   - raw payload
   - confidence
   - cleanup

6. Merge features :
   - ReccoBeats + Essentia low-level
   - active source
   - `GET /features/tracks/{track_id}`
   - coverage

7. UI :
   - Home coverage cards
   - Library features columns
   - Track preview play
   - TrackFeaturesDrawer
   - Features page coverage/failures/last runs
   - Settings workers/runtime

## Méthode

Commence par produire un plan d'audit court :

```text
- fichiers à inspecter ;
- commandes à lancer ;
- risques ;
- corrections probables.
```

Attends validation avant modifications si tu identifies une migration DB ou un changement d'architecture.

## Commandes de validation attendues

Backend :

```bash
cd core
uv run alembic upgrade head
uv run pytest -q
uv run ruff check .
```

Docker :

```bash
docker compose up -d --build core-api
docker compose --profile audio up -d --build --scale audio-downloader=2 --scale essentia-lowlevel-worker=2
curl http://127.0.0.1:8765/api/v1/health
curl http://127.0.0.1:8765/api/v1/workers
```

Frontend :

```bash
cd app/frontend
npm run check
npm run build
```

## Livrable attendu

À la fin, fournis :

```text
- résumé des points validés ;
- écarts détectés ;
- corrections appliquées ;
- fichiers modifiés ;
- commandes exécutées ;
- résultats tests ;
- risques restants ;
- décision GO / NO-GO pour phase 5.
```

## Contraintes

- Ne pas ajouter la phase 5 pendant cette validation.
- Ne pas ajouter Essentia TensorFlow.
- Ne pas ajouter clustering.
- Ne pas ajouter de write Spotify.
- Ne pas conserver de fichiers audio hors option debug explicite.
- Ne pas rendre les diagnostics techniques dominants dans l'UI.


<!-- FILE: prompts/phase-5-00-new-agent-initialization.md -->

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


<!-- FILE: prompts/phase-5-01-feature-contract-and-db.md -->

# Prompt Cursor — Phase 5.1 — Feature contract + DB foundations

Objectif : implémenter les fondations de la phase 5 sans encore construire tout le moteur de playlists.

## À lire avant de coder

```text
docs/05-domain-model.md
docs/07-audio-analysis-pipeline.md
docs/08-playlist-engine.md
docs/18-feature-consumption-contract.md
backlog/phase-5.md
```

## Livrables

### Backend features contract

Créer ou adapter les modules :

```text
core/app/playlists/feature_registry.py
core/app/playlists/feature_resolver.py
core/app/playlists/types.py
```

Le nom exact peut être adapté à la structure existante, mais le découpage doit rester clair.

Implémenter :

```text
FeatureDescriptor
FeatureRegistry
FeatureValue
TrackFeatureView
FeatureResolver
```

Le resolver doit s'appuyer sur les données existantes :

```text
tracks
artists
albums
spotify_tracks
external_ids
liked_tracks
playlist_tracks
audio_features
feature_sources
track_previews
```

Il doit préparer l'arrivée future de :

```text
track_embeddings
essentia_tensorflow
moods
voice/instrumental
```

mais sans les implémenter maintenant.

### Features à déclarer

Phase 5 disponibles :

```text
bpm
energy
valence
danceability
acousticness
instrumentalness
speechiness
liveness
loudness
key
mode
time_signature
duration_ms
feature_confidence
preview_available
availability_status
market_status
liked_status
playlist_membership
duplicate_status
isrc
artist_id
album_id
```

Features futures phase 7 à déclarer comme indisponibles :

```text
embedding_similarity
mood_happy_score
mood_sad_score
mood_aggressive_score
mood_relaxed_score
mood_party_score
mood_dark_score
arousal
valence_tf
voice_probability
vocal_presence_score
instrumental_focus_score
acoustic_profile_score
electronic_profile_score
```

Alias :

```text
tempo -> bpm
valence_inverse -> 1 - valence
```

### DB foundations

Vérifier si les tables phase 5 existent déjà. Sinon créer une migration Alembic pour :

```text
playlist_rules
generated_playlists
generated_playlist_items
sync_jobs
sync_logs
```

Respecter `docs/05-domain-model.md`.

Ajouter si pertinent :

```text
generated_playlists.engine_version
generated_playlists.warning_json
generated_playlist_items.exclusion_details_json nullable
```

Ne pas faire de migration destructive.

## Tests attendus

Ajouter tests unitaires pour :

```text
FeatureRegistry resolves known feature
FeatureRegistry resolves alias
FeatureRegistry rejects unknown feature
FeatureRegistry marks future feature as not available yet
FeatureResolver returns TrackFeatureView for tracks with ReccoBeats
FeatureResolver handles missing features
FeatureResolver handles low confidence
FeatureResolver exposes preview availability
```

## Contraintes

- Ne pas implémenter encore `/generated-playlists/preview`.
- Ne pas implémenter encore l'UI.
- Ne pas ajouter TensorFlow.
- Ne pas ajouter clustering.
- Ne pas lire les raw payloads dans le moteur futur.

## Validation

Lancer :

```bash
cd core
uv run alembic upgrade head
uv run pytest -q
uv run ruff check .
```

## Réponse attendue

À la fin, fournis :

```text
- fichiers modifiés ;
- migration créée ou non ;
- description FeatureRegistry ;
- description FeatureResolver ;
- tests ajoutés ;
- commandes exécutées ;
- risques restants.
```


<!-- FILE: prompts/phase-5-02-playlist-rules-validation-crud.md -->

# Prompt Cursor — Phase 5.2 — PlaylistRule validation + CRUD minimal

Objectif : implémenter le schéma de règle, la validation et le CRUD minimal des règles de playlists.

## À lire avant de coder

```text
docs/08-playlist-engine.md
docs/18-feature-consumption-contract.md
backlog/phase-5.md
```

## Précondition

La tâche précédente doit avoir introduit :

```text
FeatureRegistry
FeatureResolver
TrackFeatureView
tables playlist_rules si nécessaires
```

Si ce n'est pas le cas, arrête-toi et signale l'écart.

## Livrables backend

Créer ou compléter :

```text
core/app/playlists/schemas.py
core/app/playlists/rule_validation.py
core/app/playlists/rules_service.py
core/app/database/repositories/playlist_rules.py
core/app/api/v1/playlists.py ou playlist_rules.py
```

Le nom exact des fichiers peut suivre les conventions du repo.

## Schéma PlaylistRule

Supporter le format documenté dans `docs/08-playlist-engine.md` :

```text
name
description
target_size
engine_version
source
filters
weights
constraints
ordering
spotify
```

Champs phase 6/7 autorisés mais non actifs :

```text
clusters_include
clusters_exclude
cluster_diversity
seed_tracks
mood_* features
embedding_similarity
voice/instrumental features
```

## Endpoint validation

Ajouter :

```text
POST /api/v1/playlist-rules/validate
```

Réponse attendue :

```json
{
  "valid": true,
  "errors": [],
  "warnings": [],
  "normalized_rule": {}
}
```

Erreurs bloquantes minimum :

```text
RULE_INVALID_SCHEMA
UNKNOWN_FEATURE
UNKNOWN_FILTER
UNKNOWN_ORDERING_MODE
UNKNOWN_SYNC_MODE
INVALID_RANGE
NO_SOURCE_SELECTED
NO_SCORING_COMPONENTS
TARGET_SIZE_INVALID
```

Warnings minimum :

```text
FEATURE_NOT_AVAILABLE_YET
CLUSTER_SOURCE_NOT_AVAILABLE_YET
SEED_TRACKS_NOT_AVAILABLE_IN_PHASE_5
WRITE_SCOPE_NOT_AVAILABLE
LOW_FEATURE_COVERAGE
```

## CRUD minimal

Ajouter endpoints :

```text
POST /api/v1/playlist-rules
GET /api/v1/playlist-rules
GET /api/v1/playlist-rules/{rule_id}
PUT /api/v1/playlist-rules/{rule_id}
DELETE /api/v1/playlist-rules/{rule_id}
```

`DELETE` peut être logique (`enabled=false`) si plus cohérent avec le projet.

## Presets

Ajouter des presets backend ou seed local si simple :

```text
Dark / Intense
Calm / Focus
High Energy
Recently Added
Discover Forgotten Likes
Clean Library
```

Les presets phase 7 peuvent être déclarés avec warnings, mais ne doivent pas casser la validation.

## Tests attendus

```text
valid basic rule
invalid YAML/JSON
unknown feature
future feature optional -> warning
future feature required -> warning or error according to schema policy
invalid range
no source selected
no scoring components
create/list/read/update/disable rule
```

## Contraintes

- Ne pas implémenter la génération preview dans cette tâche.
- Ne pas ajouter d'écriture Spotify.
- Ne pas ajouter l'UI.
- Ne pas ajouter TensorFlow.

## Validation

```bash
cd core
uv run pytest -q
uv run ruff check .
```

## Réponse attendue

Fournis :

```text
- endpoints ajoutés ;
- schémas ajoutés ;
- fichiers modifiés ;
- exemples de payload ;
- tests ajoutés ;
- commandes exécutées ;
- risques restants.
```


<!-- FILE: prompts/phase-5-03-preview-engine.md -->

# Prompt Cursor — Phase 5.3 — Playlist preview engine

Objectif : implémenter le moteur de génération de preview : source selection, filtres stricts, scoring, diversité, ordering, persistance et explications.

## À lire avant de coder

```text
docs/08-playlist-engine.md
docs/18-feature-consumption-contract.md
backlog/phase-5.md
```

## Préconditions

Doivent exister :

```text
FeatureRegistry
FeatureResolver
TrackFeatureView
PlaylistRule validation
playlist_rules CRUD
generated_playlists / generated_playlist_items tables
```

Si une précondition manque, signale-la avant de continuer.

## Modules à créer ou compléter

```text
core/app/playlists/candidates.py
core/app/playlists/filters.py
core/app/playlists/scoring.py
core/app/playlists/diversity.py
core/app/playlists/ordering.py
core/app/playlists/explanations.py
core/app/playlists/preview_service.py
core/app/database/repositories/generated_playlists.py
core/app/api/v1/playlists.py
```

Les noms peuvent suivre l'existant.

## Pipeline à implémenter

```text
PlaylistRule
  ↓
validate
  ↓
source selection
  ↓
FeatureResolver.load_views(track_ids)
  ↓
strict filters
  ↓
weighted scoring
  ↓
diversity constraints
  ↓
ordering
  ↓
persist generated playlist
  ↓
return preview
```

## Source selection phase 5

Supporter :

```text
liked_tracks
playlists_include
playlists_exclude
track_ids_include
track_ids_exclude
```

Préparer avec warning :

```text
clusters_include
clusters_exclude
seed_tracks
```

## Filtres stricts

Implémenter au minimum :

```text
bpm
energy
valence
danceability
feature_confidence
availability_status
market_status
exclude artists
exclude albums
dedup ISRC
```

Chaque exclusion doit produire une raison structurée.

## Missing feature policy

Respecter :

```text
required=true + missing -> exclusion FEATURE_MISSING
required=false + missing -> warning
future unavailable -> FEATURE_NOT_AVAILABLE_YET
low confidence -> exclusion si confidence filter strict, sinon warning
```

## Scoring

Implémenter :

```text
weighted components
normalization 0..1
valence_inverse
missing component skip
weight renormalization
score_details_json
SCORE_NOT_COMPUTABLE
```

## Diversité

Implémenter :

```text
max_tracks_per_artist
max_tracks_per_album
avoid_duplicate_isrc
avoid_same_artist_consecutive
stable selection
```

## Ordering

Implémenter au minimum :

```text
score_desc
score_asc
recently_added_desc
recently_added_asc
random_seeded
artist_spread
```

Les modes futurs doivent retourner warning ou erreur claire :

```text
ORDERING_MODE_NOT_AVAILABLE_YET
```

## Endpoint preview

Ajouter :

```text
POST /api/v1/generated-playlists/preview
GET /api/v1/generated-playlists
GET /api/v1/generated-playlists/{generated_playlist_id}
```

Réponse preview attendue :

```json
{
  "generated_playlist_id": "...",
  "summary": {
    "candidate_count": 1000,
    "excluded_count": 920,
    "scored_count": 80,
    "selected_count": 80,
    "warnings": []
  },
  "items": [],
  "exclusions_sample": []
}
```

## Tests attendus

```text
source liked tracks
source playlist include/exclude
filter bpm
filter energy
filter missing required
filter missing optional
future feature warning
scoring simple
scoring renormalization
score not computable
diversity max artist
diversity max album
dedup ISRC
avoid same artist consecutive
ordering stable
preview persisted
read generated playlist
```

## Contraintes

- Ne pas écrire dans Spotify.
- Ne pas ajouter dry-run sync dans cette tâche sauf structure nécessaire.
- Ne pas ajouter UI.
- Ne pas ajouter TensorFlow/clustering.
- Garder services testables indépendamment des routes.

## Validation

```bash
cd core
uv run pytest -q
uv run ruff check .
```

## Réponse attendue

Fournis :

```text
- modules ajoutés ;
- endpoints ajoutés ;
- format des score details ;
- exemples de reasons ;
- tests ajoutés ;
- commandes exécutées ;
- risques restants.
```


<!-- FILE: prompts/phase-5-04-dry-run-sync.md -->

# Prompt Cursor — Phase 5.4 — Spotify dry-run sync

Objectif : implémenter la synchronisation Spotify en dry-run uniquement.

## À lire avant de coder

```text
docs/06-api-contract.md
docs/08-playlist-engine.md
backlog/phase-5.md
```

## Préconditions

Doivent exister :

```text
generated_playlists
generated_playlist_items
preview endpoint
Spotify client read playlist tracks
```

Si les APIs Spotify nécessaires n'existent pas, ajoute uniquement les méthodes read nécessaires. Ne pas ajouter de write.

## Interdiction absolue phase 5

```text
Aucune écriture Spotify réelle.
Aucun ajout/suppression de tracks dans Spotify.
Aucune création réelle de playlist Spotify.
Aucun endpoint apply.
```

## Modules à créer ou compléter

```text
core/app/playlists/sync_dry_run.py
core/app/database/repositories/sync_jobs.py
core/app/api/v1/sync.py
```

## Tables

Utiliser ou créer :

```text
sync_jobs
sync_logs
```

Champs attendus :

```text
generated_playlist_id
target_spotify_playlist_id
sync_mode
dry_run=true
status
diff_json
created_at
finished_at
```

## Endpoint

Ajouter :

```text
POST /api/v1/sync/dry-run
GET /api/v1/sync/jobs/{sync_job_id}
```

Payload :

```json
{
  "generated_playlist_id": "...",
  "target_spotify_playlist_id": "...",
  "sync_mode": "replace"
}
```

Modes :

```text
create
replace
add_only
remove_obsolete
replace_after_dry_run
```

## Diff attendu

```json
{
  "to_add": [],
  "to_remove": [],
  "unchanged": [],
  "not_syncable": [],
  "warnings": []
}
```

Chaque item doit inclure au minimum :

```text
track_id
spotify_track_id
title
artist_names
reason
```

## Scopes

- Le dry-run doit fonctionner sans scope write.
- Si scope write absent, ajouter warning `WRITE_SCOPE_NOT_AVAILABLE`.
- Si Spotify non connecté, retourner erreur structurée `UNAUTHORIZED_SPOTIFY`.
- Si playlist cible introuvable, retourner `NOT_FOUND`.

## Tests attendus

```text
dry-run create mode
replace mode diff
add_only mode diff
remove_obsolete mode diff
unchanged tracks
tracks without spotify id -> not_syncable
missing Spotify auth
missing write scope warning
no Spotify write method called
sync job persisted
sync logs persisted
```

Utiliser mocks pour Spotify.

## Validation

```bash
cd core
uv run pytest -q
uv run ruff check .
```

## Réponse attendue

Fournis :

```text
- endpoints ajoutés ;
- format diff_json ;
- fichiers modifiés ;
- garanties anti-write ;
- tests ajoutés ;
- commandes exécutées ;
- risques restants.
```


<!-- FILE: prompts/phase-5-05-ui.md -->

# Prompt Cursor — Phase 5.5 — UI Playlist Builder

Objectif : implémenter l'interface phase 5 pour créer, valider, prévisualiser et dry-run des playlists.

## À lire avant de coder

```text
docs/09-ui-specification.md
docs/08-playlist-engine.md
docs/18-feature-consumption-contract.md
backlog/phase-5.md
```

## Préconditions

Les endpoints backend doivent exister :

```text
POST /api/v1/playlist-rules/validate
POST /api/v1/playlist-rules
GET /api/v1/playlist-rules
GET /api/v1/playlist-rules/{rule_id}
PUT /api/v1/playlist-rules/{rule_id}
POST /api/v1/generated-playlists/preview
GET /api/v1/generated-playlists/{id}
POST /api/v1/sync/dry-run
GET /api/v1/sync/jobs/{id}
```

Si un endpoint manque, signale-le avant de coder l'UI correspondante.

## Route

Ajouter ou activer :

```text
/playlists
```

Ajouter la navigation dans le shell si absent :

```text
Playlist Builder
```

## UX attendue

L'écran doit contenir :

```text
PageHeader
Presets
Rule editor simple
Advanced JSON/YAML editor
Validation panel
Preview panel
Score details
Exclusions/warnings
Dry-run sync panel
```

## États obligatoires

- loading initial ;
- refreshing ;
- empty ;
- error ;
- offline core ;
- validation errors ;
- validation warnings ;
- preview running/loading ;
- dry-run loading ;
- dry-run result.

## Règles UI

- Ne jamais afficher d'action Spotify réelle.
- Afficher clairement `Dry-run only`.
- Les warnings de features futures doivent être lisibles et non bloquants.
- Les score details doivent être accessibles par item.
- Les exclusions doivent être consultables.
- Les JSON techniques doivent être repliés par défaut.
- Respecter le design system existant.

## Composants suggérés

```text
PlaylistBuilderPage.svelte
PlaylistPresetGrid.svelte
PlaylistRuleEditor.svelte
PlaylistAdvancedEditor.svelte
PlaylistValidationPanel.svelte
GeneratedPlaylistPreview.svelte
PlaylistScoreDetailsDrawer.svelte
PlaylistExclusionsPanel.svelte
PlaylistDryRunPanel.svelte
```

Adapter aux conventions existantes.

## API frontend

Créer ou compléter :

```text
app/frontend/src/lib/api/playlists.ts
app/frontend/src/lib/types/playlists.ts
```

## Presets initiaux UI

Afficher au minimum :

```text
Dark / Intense
Calm / Focus
High Energy
Recently Added
Discover Forgotten Likes
Clean Library
```

Optionnel avec warning :

```text
Low Vocal
Instrumental Focus
Electronic / Synthetic
Acoustic / Organic
```

## Tests / validation

Minimum :

```bash
cd app/frontend
npm run check
npm run build
```

Si tests frontend existent, ajouter tests pour :

```text
validation errors
warnings features futures
preview result display
score details display
dry-run result display
```

## Réponse attendue

Fournis :

```text
- pages/composants ajoutés ;
- clients API ajoutés ;
- états UI gérés ;
- limites restantes ;
- commandes exécutées ;
- risques restants.
```


<!-- FILE: prompts/phase-5-06-tests-docs-review.md -->

# Prompt Cursor — Phase 5.6 — Tests, documentation et revue finale

Objectif : finaliser la phase 5 après implémentation backend + UI.

## À lire avant de commencer

```text
docs/03-development-workflow.md
docs/04-backlog-by-phase.md
docs/05-domain-model.md
docs/06-api-contract.md
docs/08-playlist-engine.md
docs/09-ui-specification.md
docs/18-feature-consumption-contract.md
backlog/phase-5.md
```

## Audit final attendu

Vérifie que la phase 5 respecte :

```text
- FeatureRegistry utilisé ;
- FeatureResolver utilisé ;
- TrackFeatureView utilisé ;
- pas de lecture raw payload dans le moteur playlist ;
- règles validées ;
- CRUD règles ;
- preview persistée ;
- score details ;
- exclusions ;
- dry-run sync sans écriture ;
- UI utilisable ;
- features futures phase 7 gérées avec warnings ;
- docs à jour.
```

## Tests backend à compléter

Ajouter ou vérifier :

```text
FeatureRegistry
FeatureResolver
PlaylistRule validation
PlaylistRule CRUD
Source selection
Filters
Scoring
Weight renormalization
Diversity
Ordering
Preview persistence
Dry-run sync
API error formats
No Spotify write call
```

## Tests frontend à compléter si infrastructure disponible

```text
Playlist route renders
Presets visible
Validation errors visible
Warnings visible
Preview visible
Score details visible
Dry-run result visible
Offline/error states
```

## Documentation à mettre à jour

Mettre à jour selon l'implémentation réelle :

```text
docs/04-backlog-by-phase.md
docs/05-domain-model.md
docs/06-api-contract.md
docs/08-playlist-engine.md
docs/09-ui-specification.md
docs/18-feature-consumption-contract.md
docs/14-configuration.md si variables ajoutées
backlog/phase-5.md
```

Ne pas marquer `DONE` sans validation/test.

## Commandes de validation

Backend :

```bash
cd core
uv run alembic upgrade head
uv run pytest -q
uv run ruff check .
uv run ruff format --check .
```

Frontend :

```bash
cd app/frontend
npm run check
npm run build
```

Smoke API :

```bash
curl http://127.0.0.1:8765/api/v1/health
curl http://127.0.0.1:8765/api/v1/playlist-rules
```

## Revue de phase attendue

Produis un rapport :

```text
# Phase 5 review

## Livrables réalisés
## Endpoints ajoutés
## Tables/migrations ajoutées
## UI ajoutée
## Tests exécutés
## Résultats
## Documentation modifiée
## Écarts restants
## Risques phase 6
## Risques phase 7
## Décision GO/NO-GO phase 6
```

## Contraintes

- Ne pas commencer phase 6.
- Ne pas commencer phase 7.
- Ne pas ajouter d'écriture Spotify réelle.
- Ne pas masquer les tests échoués.
- Ne pas modifier l'architecture sans documenter.
