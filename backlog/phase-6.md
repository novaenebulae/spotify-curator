# Phase 6 — Pipeline parallèle, gestion modèles et inférence réelle Essentia TensorFlow

Tags: #backlog #phase-6 #audio-pipeline #essentia #tensorflow #embeddings #features #models

## But

Remplacer le flux séquentiel `download all segments → analyze all segments` par un pipeline parallèle et ajouter l'analyse avancée Essentia TensorFlow **réelle** lorsque les modèles sont présents localement.

La phase 6 absorbe l'ancien périmètre "Phase 7 — Analyse avancée", car les embeddings, moods et genres doivent être disponibles avant le clustering visuel. Par conséquent, les embeddings, moods, genres, voice/instrumental, acoustic/electronic, approachability et engagement ne doivent pas rester des stubs de production.

## Décision de réalignement

La phase 6 avait divergé : elle a été implémentée en grande partie comme un socle technique avec des runners TensorFlow en **stub déterministe** (`inference_mode="stub"`) traités comme résultats de production. Ce n'est pas suffisant. Voir [`docs/19-essentia-tensorflow-model-management.md`](../docs/19-essentia-tensorflow-model-management.md).

La phase 6 n'est pas validable tant que :

- `POST /api/v1/audio/analysis/advanced` n'existe pas ;
- le pipeline avancé n'est pas déclenchable depuis l'API/UI ;
- les modèles attendus ne sont pas déclarés dans un manifest versionné ;
- l'utilisateur ne peut pas télécharger/vérifier les modèles via CLI/API ;
- les runners TensorFlow produisent des valeurs fake/stub en runtime normal ;
- aucun smoke test WAV court ne prouve une vraie inférence quand les modèles sont présents.

Reclassement des tâches :

- 6.2 Handoff → **PARTIAL** tant que le pipeline n'est pas déclenchable par l'utilisateur.
- 6.4 Worker TensorFlow → **PARTIAL** tant que l'inférence réelle n'est pas branchée.
- 6.5 Model registry → **PARTIAL** tant qu'il n'y a pas de manifest/downloader/verifier.
- 6.6 Embeddings + Genre Discogs519 → **PARTIAL** tant que les runners sont stub.
- 6.7 Classifiers avancés → **PARTIAL** tant que les runners sont stub.
- Ajout de tâches **bloquantes** : 6.8A (gestion modèles, downloader, vérification), 6.8B (inférence réelle), 6.8C (smoke tests inférence réelle).

Règles non négociables :

- aucun modèle lourd commité ;
- aucun segment audio > 30 secondes ;
- aucun stub en runtime normal ;
- `inference_mode="real"` uniquement si un modèle réel a été exécuté sur un WAV réel ;
- modèle absent → `model_missing` ; modèle invalide → `model_invalid` ; pas de fake success ;
- stubs autorisés uniquement si `APP_ENV=test` et `ESSENTIA_TF_ALLOW_STUBS_IN_TESTS=true` ;
- le playlist engine consomme toujours `TrackFeatureView`, jamais les payloads raw.

## Sources modèles officielles

Les sources officielles utilisées pour construire le manifest sont :

```text
https://essentia.upf.edu/models.html
https://essentia.upf.edu/models/
```

Règles :

- télécharger uniquement les fichiers `.pb` + `.json` déclarés dans le manifest ;
- ne pas télécharger toute l'arborescence `/models/` ;
- ne pas utiliser `.onnx`, `tfjs.zip` ou `savedmodel.zip` dans cette phase ;
- afficher la licence `CC BY-NC-SA 4.0` et demander acceptation explicite.

## Profils de modèles

### `phase6-minimal`

- `discogs-effnet-bs64-1.pb/json`
- `mood_aggressive-discogs-effnet-1.pb/json`
- `mood_happy-discogs-effnet-1.pb/json`
- `mood_party-discogs-effnet-1.pb/json`
- `mood_relaxed-discogs-effnet-1.pb/json`
- `mood_sad-discogs-effnet-1.pb/json`
- `mood_acoustic-discogs-effnet-1.pb/json`
- `mood_electronic-discogs-effnet-1.pb/json`
- `voice_instrumental-discogs-effnet-1.pb/json`
- `danceability-discogs-effnet-1.pb/json`
- `approachability_regression-discogs-effnet-1.pb/json`
- `engagement_regression-discogs-effnet-1.pb/json`

### `phase6-recommended`

Tout `phase6-minimal`, plus :

- `discogs-maest-30s-pw-519l-2.pb/json`
- `genre_discogs519-discogs-maest-30s-pw-519l-1.pb/json`

Profil recommandé pour valider le périmètre phase 6 complet, car il ajoute `genre_discogs_519`.

### `phase6-full`

Tout `phase6-recommended`, plus :

- `msd-musicnn-1.pb/json`
- `deam-msd-musicnn-2.pb/json`
- `muse-msd-musicnn-2.pb/json`

Ajoute une première voie arousal/valence réelle. Sans ce profil, `valence` reste prioritairement fournie par ReccoBeats ; si ReccoBeats est absent, `valence_tf` doit être `model_missing` ou `not_supported_yet`.

## Principe cible

```text
analysis job
  ↓
audio-downloader workers
  ↓ segment_ready
  ├─ essentia-lowlevel-worker
  └─ essentia-tensorflow-worker
       ├─ embeddings
       ├─ genre Discogs519
       ├─ moods
       ├─ approachability / engagement
       └─ fallbacks danceability / valence / instrumental / acoustic / energy proxy
  ↓
track_feature_aggregator
  ↓
FeatureRegistry / FeatureResolver / TrackFeatureView
  ↓
UI features + playlist engine + future clustering
```

## Definition of Done phase

- Les livrables de phase sont présents.
- Les tests minimum passent.
- Les commandes de validation sont documentées.
- La documentation est à jour.
- Aucun secret, cache, modèle lourd ou fichier audio n'est commité.
- Aucune régression sur les phases précédentes.
- Le téléchargement et l'analyse sont chaînés par statuts/stages, pas par deux lots bloquants.
- Les workers Docker restent persistants.
- Les segments temporaires sont supprimés après consommation par tous les stages requis.
- Les modèles Essentia TensorFlow attendus sont déclarés dans `core/app/models_registry/essentia_models_manifest.yaml`.
- L'utilisateur peut télécharger ou vérifier les modèles via CLI et API.
- L'absence d'un modèle produit `model_missing`, pas une feature fake.
- Les stubs sont interdits en production.
- Un smoke test WAV court prouve une vraie inférence TensorFlow lorsque les modèles sont présents.
- Les features avancées sont visibles dans l'API et dans l'UI.
- Le playlist engine phase 5 continue de fonctionner.

---

## 6.0 — Audit post-phase 5 et cadrage migration

Statut : DONE (2026-06-03) — l'audit [`docs/phase-6-audit.md`](../docs/phase-6-audit.md) doit être mis à jour en 6.10 pour refléter le réalignement modèles/inférence réelle.

Livrables : [`docs/phase-6-audit.md`](../docs/phase-6-audit.md), fusion docs canoniques phase 6, patches archivés sous `docs/archive/phase-6-patches/`. Baseline : 194 pytest, frontend check/build OK.

### Sous-tâches

- Vérifier les migrations Alembic actuelles.
- Vérifier l'état réel des workers audio existants.
- Vérifier les endpoints `/audio/*`, `/features/*`, `/jobs/*`, `/workers`.
- Vérifier que la phase 5 consomme bien `TrackFeatureView`.
- Identifier les tables/colonnes manquantes pour features avancées.
- Identifier l'emplacement réel des services `audio-downloader`, `essentia-lowlevel-worker`.
- Produire un court rapport `docs/phase-6-audit.md`.

### Critères

- Aucun refactor majeur n'est lancé sans état des lieux.
- Les décisions s'appuient sur le code existant, pas uniquement sur la documentation.

---

## 6.1 — Modèle de pipeline par stages

Statut : DONE (2026-06-03)

Livrables : migration `0009_phase6_job_items_pipeline_stages`, extension `job_items`, [`core/app/audio/pipeline/orchestrator.py`](../core/app/audio/pipeline/orchestrator.py), tests `test_analysis_pipeline_stages.py`.

### Sous-tâches

- Introduire un modèle de stage idempotent :
  - `segment_download`
  - `essentia_lowlevel`
  - `essentia_tensorflow_embeddings`
  - `essentia_tensorflow_classifiers`
  - `feature_aggregation`
  - `audio_cleanup`
- **Étendre `job_items`** (décision retenue — pas de table `analysis_stage_items`) : voir [`docs/phase-6-audit.md`](../docs/phase-6-audit.md) §5.
- Stocker les dépendances entre stages.
- Gérer les statuts :
  - `pending`
  - `running`
  - `success`
  - `failed`
  - `skipped`
  - `blocked`
  - `cancelled`
  - `rate_limited`
- Ajouter `stage_name`, `depends_on_stage`, `track_id`, `segment_id`, `consumer_group`, `result_json`, `error_code`, `model_name`, `pipeline_version` si nécessaire.
- Ajouter un service `AnalysisPipelineOrchestrator`.

### Critères

- Un segment prêt peut déclencher immédiatement low-level et TensorFlow.
- Un échec d'un stage n'empêche pas les stages indépendants.
- Un job peut terminer en succès partiel.
- Les stages sont relançables.

---

## 6.2 — Handoff downloader → analyzers

Statut : PARTIAL — le mécanisme de handoff existe, mais le pipeline n'est pas encore déclenchable par l'utilisateur.

Livrables : `ANALYSIS_PIPELINE_MODE`, `PipelineSegmentHandoffService`, `audio_downloader` pipeline segment path, consumers/cleanup gating, tests `test_analysis_pipeline_handoff.py`, `test_audio_cleanup.py`. Baseline : 205 pytest.

Critères bloquants restants :

- `AnalysisPipelineOrchestrator.create_pipeline_job` doit être appelé depuis `POST /api/v1/audio/analysis/advanced` (cf. 6.9), pas seulement depuis les tests.
- Le mode streaming ne doit pas être limité aux tests.
- L'UI doit déclencher le job `audio_analysis_pipeline`.

### Sous-tâches

- Modifier le worker `audio-downloader` pour créer les stages d'analyse dès qu'un segment est prêt.
- Ne pas attendre la fin du job de téléchargement complet.
- Ajouter une configuration :
  - `ANALYSIS_PIPELINE_MODE=streaming|legacy`
  - défaut : `streaming`
- Ajouter des verrous de consommation pour le cleanup.
- Ajouter une option de compatibilité pour conserver l'ancien flux si nécessaire.
- Mettre à jour les progressions job globales.

### Critères

- Un test prouve que le premier segment téléchargé est analysable avant la fin des téléchargements suivants.
- Les segments ne sont pas supprimés avant la fin des consommateurs low-level et TensorFlow.
- L'ancien endpoint de low-level reste compatible.

---

## 6.3 — Essentia low-level dans le pipeline parallèle

Statut : DONE (2026-06-03)

Livrables : réservation stage `essentia_lowlevel`, branche pipeline du worker, `PipelineFeatureAggregationService`, sérialisation segment pour agrégat, tests `test_analysis_pipeline_lowlevel.py`. Baseline : 212 pytest.

### Sous-tâches

- Adapter le worker `essentia-lowlevel-worker` pour consommer les stages `essentia_lowlevel`.
- Garantir idempotence par `track_id + segment_id + pipeline_version`.
- Conserver les agrégats multi-segments existants.
- Continuer à produire :
  - BPM
  - beats
  - loudness
  - key
  - mode
  - key confidence
  - MFCC
  - HPCP
  - spectral centroid
  - spectral rolloff
  - spectral contrast
  - dynamic complexity
  - onset rate
- Ajouter tests de non-régression sur l'API `/features/tracks/{track_id}`.

### Critères

- Les résultats low-level restent identiques ou compatibles avec la phase 4.
- Le merge de features existant continue de fonctionner.
- Le cleanup fonctionne après succès low-level seul et après succès low-level + TF.

---

## 6.4 — Image et worker Essentia TensorFlow

Statut : PARTIAL — le worker et l'image existent, mais l'inférence reste stub (pas d'inférence réelle branchée).

Livrables : `docker/essentia-tensorflow-worker`, Compose profil `advanced-analysis`, `EssentiaTensorflowWorker`, `ModelRegistry`, `GET /api/v1/models/status`, tests registry/API/worker, smoke script. Baseline : 219+ pytest.

Critères bloquants restants :

- le worker démarre sans modèle lourd obligatoire ;
- le worker n'écrit aucune feature fake ;
- le worker peut exécuter une vraie inférence sur WAV court lorsqu'au moins `phase6-minimal` est installé (cf. 6.8B) ;
- le worker ne lance pas un conteneur par piste.

### Sous-tâches

- Créer `docker/essentia-tensorflow-worker/Dockerfile`.
- Ajouter le service Compose `essentia-tensorflow-worker` dans un profil `advanced-analysis`.
- Créer un worker Python persistant :
  - heartbeat ;
  - réservation stage ;
  - chargement modèles au démarrage ;
  - traitement multi-items ;
  - logs redacted.
- Ajouter un script smoke WAV court.
- Ajouter `ESSENTIA_TENSORFLOW_WORKERS=1` par défaut.
- Ne pas commiter les modèles.

### Critères

- Le worker démarre sans modèle lourd obligatoire si mode `status_only`.
- Un smoke test WAV court fonctionne avec un modèle présent.
- Le worker ne lance pas un conteneur par piste.

---

## 6.5 — Model registry

Statut : PARTIAL — le registry déclare les modèles, mais ne sait pas encore les télécharger/vérifier (manifest + downloader + verifier manquants).

### Sous-tâches

- Créer `core/app/models_registry/` (fait en 6.4).
- Déclarer les modèles attendus :
  - embeddings Discogs EffNet ;
  - Genre Discogs519 ;
  - approachability ;
  - engagement ;
  - moods aggressive/happy/party/relaxed/sad ;
  - mood electronic ;
  - mood acoustic ;
  - danceability ;
  - arousal/valence ;
  - voice/instrumental ;
  - energy proxy config.
- Stocker :
  - model key ;
  - filename attendu ;
  - chemin local ;
  - version ;
  - hash sha256 si fichier présent ;
  - dimension embedding si applicable ;
  - status `available|missing|invalid_hash|disabled`.
- Ajouter endpoint `GET /api/v1/models/status`.

### Sous-tâches ajoutées (réalignement)

- Créer `core/app/models_registry/essentia_models_manifest.yaml`.
- Déclarer les profils `phase6-minimal`, `phase6-recommended`, `phase6-full`.
- Ajouter `ModelManager` (`list_models`, `get_status`, `download_model`, `download_profile`, `verify_model`, `compute_sha256`, `read_metadata`).
- Ajouter CLI `core/scripts/download_essentia_models.py`.
- Ajouter API `GET /models/status`, `POST /models/download`, `POST /models/download-profile`, `POST /models/verify`.

### Critères

- L'absence d'un modèle ne casse pas l'application.
- L'UI peut afficher les modèles manquants.
- Les tests ne dépendent pas de modèles réels lourds.
- L'utilisateur peut télécharger/vérifier un profil sans deviner les URLs.

---

## 6.6 — Embeddings et Genre Discogs519

Statut : DONE (inférence réelle livrée en 6.8B).

Note : persistance `track_embeddings` + genre dans `track_advanced_features` ; intégré à l'agrégation pipeline commune avec §6.7. L'inférence embeddings/genre réelle est livrée en 6.8B (backend Essentia injectable, `inference_mode="real"`, `model_missing` si modèle absent).

### Sous-tâches

- Ajouter persistance `track_embeddings` si absente ou l'étendre si nécessaire.
- Générer embeddings par segment puis agréger par track.
- Stocker :
  - `track_id`
  - `source`
  - `model_name`
  - `model_version`
  - `model_hash`
  - `dimension`
  - `vector_json`
  - `aggregation_method`
  - `segments_used`
  - `confidence`
- Ajouter inférence `genre_discogs_519`.
- Stocker top-k labels + scores dans une table dédiée ou payload normalisé.
- Exposer dans `FeatureResolver` :
  - `style_embedding`
  - `timbre_embedding`
  - `genre_discogs_519`
  - `genre_discogs_519_top_label`
  - `genre_discogs_519_top_score`.

### Sous-tâches restantes (réalignement)

- Remplacer `EmbeddingsRunner` stub par un runner réel basé sur `discogs-effnet-bs64-1.pb`.
- Lire `wav_path` réellement.
- Produire des embeddings depuis le modèle installé.
- Remplacer `GenreRunner` stub par MAEST + head Genre Discogs519.
- Persister `inference_mode="real"` seulement si l'inférence a utilisé le modèle.
- Conserver les tests mock/stub uniquement sous flag test.

### Critères

- Test vector shape.
- Test top-k genres.
- Test modèle absent → status lisible, pas de crash.

---

## 6.7 — Classifiers avancés

Statut : DONE (inférence réelle livrée en 6.8B).

Note : le contrat `classifier_outputs` → `track_advanced_features` est en place. L'inférence Essentia TensorFlow réelle sur WAV est livrée en 6.8B (backend injectable, garde stub `STUB_INFERENCE_FORBIDDEN` hors test).

### Features obligatoires

- `approachability`
- `engagement`
- `mood_aggressive_score`
- `mood_happy_score`
- `mood_party_score`
- `mood_relaxed_score`
- `mood_sad_score`
- `electronic_profile_score`
- `danceability_tf`
- `valence_tf`
- `instrumental_focus_score`
- `acoustic_profile_score`
- `energy_proxy`

### Sous-tâches

- Mapper les sorties binaires en scores `0..1`.
- Mapper les sorties régression arousal/valence vers une échelle normalisée.
- Mapper voice/instrumental vers :
  - `voice_probability`
  - `vocal_presence_score`
  - `instrumental_focus_score`.
- Mapper mood acoustic/electronic vers :
  - `acoustic_profile_score`
  - `electronic_profile_score`.
- Calculer `energy_proxy` depuis low-level :
  - loudness ;
  - dynamic complexity ;
  - spectral energy si disponible ;
  - onset/rhythm features si disponible.
- Stocker `feature_source`, `confidence`, `model_name`, `model_version`, `pipeline_version`.

### Sous-tâches restantes (réalignement)

- Remplacer `ClassifierRunner` stub par des appels réels aux modèles du profil `phase6-minimal`.
- Lire les métadonnées modèle pour classes / labels.
- Stocker `model_name`, `model_version`, `model_hash`, `inference_mode`, `pipeline_version`.
- En cas d'absence modèle, persister un statut lisible, pas un score fake.

### Critères

- Toutes les features demandées existent dans `FeatureRegistry`.
- Les features absentes pour cause modèle manquant ont un statut explicite.
- ReccoBeats reste source préférée pour `energy`, `danceability`, `valence`, `instrumentalness`, `acousticness` si disponible et fiable.
- Les fallbacks locaux sont seulement utilisés si ReccoBeats est absent/incomplet ou si la règle demande explicitement source locale.

---

## 6.8A — Gestion modèles, downloader et vérification

Statut : DONE (2026-06-04)

Objectif : permettre à l'utilisateur d'installer les modèles nécessaires sans deviner les URLs, les fichiers ou les chemins. Voir [`docs/19-essentia-tensorflow-model-management.md`](../docs/19-essentia-tensorflow-model-management.md).

Livrables : manifeste versionné [`core/app/models_registry/essentia_models_manifest.yaml`](../core/app/models_registry/essentia_models_manifest.yaml) (17 modèles, profils minimal/recommended/full), [`ModelManager`](../core/app/models_registry/manager.py) (statut/téléchargement/vérification/hash/licence, downloader injectable), endpoints `GET /models/status` (réécrit), `POST /models/download`, `POST /models/download-profile`, `POST /models/verify`, CLI [`core/scripts/download_essentia_models.py`](../core/scripts/download_essentia_models.py), settings `essentia_models_*`, dépendance `pyyaml`. Tests : `test_essentia_models_manifest.py`, `test_model_manager.py`, `test_models_download_api.py`, `test_model_license_acceptance.py`, `test_models_status_api.py` (réseau mocké). Baseline : 268 pytest. Le `ModelRegistry` legacy reste en place pour le worker/runners (migration en 6.8B).

### Sous-tâches

- Construire `core/app/models_registry/essentia_models_manifest.yaml` à partir du catalogue officiel.
- Implémenter `ModelManager` (download/verify/hash).
- Implémenter la CLI `scripts/download_essentia_models.py`.
- Implémenter les endpoints `POST /models/download`, `POST /models/download-profile`, `POST /models/verify`.

### Critères

- `phase6-minimal` télécharge le minimum pour exécuter un smoke test réel.
- `phase6-recommended` couvre les features demandées dont Genre Discogs519.
- les modèles ne sont pas téléchargés automatiquement au démarrage ;
- le téléchargement est déclenché explicitement par CLI/API/UI ;
- `accept_license=true` est obligatoire.

---

## 6.8B — Inférence réelle Essentia TensorFlow

Statut : DONE

### Critères

- `inference_mode="real"` est réservé aux vraies inférences ;
- aucun `inference_mode="stub"` en runtime normal ;
- les résultats avancés changent si l'audio change ;
- les tests prouvent que `wav_path` est lu ;
- les modèles absents donnent `model_missing`.

Livrables : backend d'inférence injectable [`core/app/audio/tensorflow/backend.py`](../core/app/audio/tensorflow/backend.py) (`EssentiaTensorflowBackend`, import `essentia` paresseux ; `Protocol` mocké en test), garde stub [`guard.py`](../core/app/audio/tensorflow/guard.py) + erreurs [`errors.py`](../core/app/audio/tensorflow/errors.py) (`STUB_INFERENCE_FORBIDDEN`, `TENSORFLOW_INFERENCE_FAILED`, `MODEL_MISSING`, `MODEL_INVALID`), pont clés legacy↔manifeste [`model_map.py`](../core/app/audio/tensorflow/model_map.py), runners réécrits (`EmbeddingsRunner`/`GenreRunner`/`ClassifierRunner` pilotés par `ModelManager` + backend, `inference_mode` réel/stub/none, `model_missing`), worker [`essentia_tensorflow_worker.py`](../core/app/workers/essentia_tensorflow_worker.py) (backend réel par défaut, gating `ModelManager.real_inference_ready`, capture `InferenceError`→`mark_failed`), settings `app_env` + `essentia_tf_*`, accès publics `ModelManager` (`get_entry`/`weights_path`/`metadata_path`/`is_available`) + champs `output`/`sample_rate`/`backend`. Tests : `test_tf_stub_guard.py`, `test_essentia_tf_real_runners.py`, `test_essentia_tf_model_missing.py`, `test_embeddings_runner.py` (réécrit), `test_essentia_tensorflow_worker.py` + `test_feature_aggregation_*` (backend factice → mode `real`). Suite : 277 pytest verts. Stub uniquement si `APP_ENV=test` + `ESSENTIA_TF_ALLOW_STUBS_IN_TESTS=true`.

---

## 6.8C — Smoke tests inférence réelle

Statut : DONE

### Critères

- si modèles absents, le smoke indique `model_missing` ;
- si modèles présents, le smoke produit au moins une vraie sortie ;
- le smoke est documenté dans [`docs/10-testing-strategy.md`](../docs/10-testing-strategy.md).

Livrables : script [`core/scripts/smoke_essentia_tensorflow_real.py`](../core/scripts/smoke_essentia_tensorflow_real.py) (`run_smoke` réutilisable + `main`, génération d'un WAV court 16 kHz mono ≤ 30 s, exécution des runners réels du profil `phase6-minimal` via `ModelManager` + `EssentiaTensorflowBackend`, validation `inference_mode="real"` + sortie non vide, persistance optionnelle de l'embedding via `TrackEmbeddingsRepository`). Options : `--require-models`, `--allow-missing`, `--track-id`, `--wav-path`, `--profile`, `--persist`. Codes : réel=0, `model_missing`=1 si `--require-models` (0 sinon/`--allow-missing`), erreur inférence=2. Tests : [`core/tests/test_smoke_essentia_tf_real.py`](../core/tests/test_smoke_essentia_tf_real.py) (backend factice : `model_missing`, sortie réelle, codes de sortie `main`). Doc : section "Smoke inférence réelle" de [`docs/10-testing-strategy.md`](../docs/10-testing-strategy.md).

---

## 6.8 — FeatureRegistry / FeatureResolver / TrackFeatureView

Statut : TODO

### Sous-tâches

- Ajouter tous les descriptors phase 6.
- Ajouter alias :
  - `genre_discogs519` → `genre_discogs_519`
  - `mood_electronic` → `electronic_profile_score`
  - `instrumental` → `instrumental_focus_score`
  - `acoustic` → `acoustic_profile_score`
  - `valence_local` → `valence_tf`
  - `danceability_local` → `danceability_tf`
- Ajouter source priority par feature.
- Ajouter `feature_source_detail` et `model_name`.
- Garantir que le playlist engine phase 5 ne lit pas les payloads raw.
- Préparer profils clustering phase 7.

### Critères

- Les règles de playlist peuvent utiliser les nouvelles features.
- Les features futures/absentes retournent warnings structurés.
- Les tests de phase 5 continuent de passer.

---

## 6.9 — API et UI features avancées

Statut : TODO

### Sous-tâches API

- `POST /api/v1/audio/analysis/advanced`
- `GET /api/v1/models/status`
- `POST /api/v1/models/download`
- `POST /api/v1/models/download-profile`
- `POST /api/v1/models/verify`
- `GET /api/v1/features/advanced/coverage`
- Étendre `GET /api/v1/features/tracks/{track_id}`.
- Étendre `GET /api/v1/features/coverage`.
- Étendre `GET /api/v1/jobs/{job_id}` ou `/items` avec compteurs par stage.

### Sous-tâches UI

- Mettre à jour écran `/features`.
- Afficher :
  - coverage low-level ;
  - coverage TensorFlow ;
  - modèles disponibles/manquants ;
  - bouton téléchargement profil minimal/recommandé ;
  - bouton lancement analyse avancée ;
  - derniers jobs avancés ;
  - failures par modèle.
- Mettre à jour `TrackFeaturesDrawer` :
  - onglet Advanced ;
  - moods ;
  - genre Discogs top-k ;
  - embeddings status ;
  - source/confidence/model ;
  - statut `model_missing`.

### Critères

- L'utilisateur comprend pourquoi une feature est absente.
- Les payloads raw restent repliés.
- Aucun fichier audio/modèle n'est exposé.

---

## 6.10 — Tests, validation et documentation

Statut : TODO

### Sous-tâches

- Tests migrations.
- Tests stage orchestrator.
- Tests handoff downloader → analyzers.
- Tests worker low-level non-régression.
- Tests model registry.
- Tests TensorFlow worker mock.
- Tests embeddings shape.
- Tests classifier mapping.
- Tests FeatureResolver.
- Tests API.
- Tests UI build/check.
- Smoke Docker profil `advanced-analysis`.
- Documentation mise à jour.

### Commandes minimum

```bash
cd core
uv run pytest -q
uv run ruff check .
uv run ruff format --check .

cd app/frontend
npm run check
npm run build

docker compose --profile audio --profile advanced-analysis up -d --build
curl http://127.0.0.1:8765/api/v1/health
curl http://127.0.0.1:8765/api/v1/workers
curl http://127.0.0.1:8765/api/v1/models/status
curl http://127.0.0.1:8765/api/v1/features/advanced/coverage
```

### Commandes modèles

```bash
docker compose exec core-api uv run python scripts/download_essentia_models.py --profile phase6-minimal --accept-license
docker compose exec core-api uv run python scripts/download_essentia_models.py --profile phase6-recommended --accept-license
docker compose exec core-api uv run python scripts/download_essentia_models.py --verify-only
docker compose exec core-api uv run python scripts/smoke_essentia_tensorflow_real.py
```

### Critères phase

- Le pipeline parallèle fonctionne sur un petit lot de tracks.
- Les jobs sont observables.
- Les modèles manquants sont gérés proprement.
- Les modèles présents permettent une vraie inférence.
- Les features avancées demandées sont disponibles ou explicitement marquées indisponibles.
- La phase 7 clustering peut commencer sans refonte du modèle features.
