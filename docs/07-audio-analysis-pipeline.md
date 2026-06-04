# 07 — Pipeline audio et features

Tags: #audio #yt-dlp #ffmpeg #essentia #reccobeats #features

## Objectif

Enrichir les titres avec des features musicales issues de sources multiples : ReccoBeats, analyse locale low-level, modèles avancés et tags utilisateur.

**Stratégie segments (hybride Deezer + YouTube)** : voir [`17-audio-preview-and-segment-strategy.md`](17-audio-preview-and-segment-strategy.md).

## Sources

1. ReccoBeats.
2. Analyse locale segmentée.
3. Essentia low-level.
4. Essentia TensorFlow.
5. librosa.
6. all-in-one structure analyzer.
7. OpenL3 / Discogs EffNet.
8. Spotify metadata.
9. Tags utilisateur.
10. Valeurs manuelles utilisateur.

## Règles strictes

- Pas de téléchargement complet standard.
- Segment temporaire uniquement.
- Segment `<= 30` secondes.
- Suppression audio après analyse.
- Pas de commit audio.
- Pas de stockage audio permanent par défaut.
- Tout résultat local doit stocker `pipeline_version`.
- Toute feature doit conserver source et confiance.

## Phase 3 — ReccoBeats

### Features attendues

- `acousticness`
- `danceability`
- `energy`
- `instrumentalness`
- `key`
- `liveness`
- `loudness`
- `mode`
- `speechiness`
- `tempo`
- `valence`

### Pipeline

```text
tracks sans features
  ↓
job enrichment
  ↓
ReccoBeatsClient
  ↓
retry/backoff/rate limit
  ↓
raw payload
  ↓
normalisation
  ↓
audio_features source=reccobeats
  ↓
coverage
```

**ReccoBeats API — implémenté (phase 3.5)** : batch `GET /v1/audio-features?ids={id1},{id2},...` (jusqu'à 40 ids par requête : Spotify track ID, ISRC ou ReccoBeats ID), chunks séquentiels dans le job `reccobeats_enrichment` ([`core/app/reccobeats/client.py`](../core/app/reccobeats/client.py), [`core/app/features/enrichment.py`](../core/app/features/enrichment.py)). Fallback per-track via `/v1/track` + `/v1/track/{id}/audio-features` si une entrée manque dans le batch.

Un seul job enrichissement `queued`/`running` à la fois. Détail : [`16-job-execution-model-and-worker-parallelism.md`](16-job-execution-model-and-worker-parallelism.md) §7.

Alias DB : `tempo` → `bpm`.

### Confidence (phase 3)

| Cas | Confidence |
|---|---|
| Feature directe ReccoBeats valide | 1.0 |
| ISRC local == ISRC ReccoBeats | 1.0 |
| Résolution via Spotify track ID | 0.9 |
| Champ absent ou invalide | NULL |

### Statuts par enregistrement

- `success`, `partial`, `not_found`, `failed`, `skipped`

### Statuts pipeline (historique)

- `not_started`
- `pending`
- `reccobeats_done`
- `reccobeats_failed`
- `local_required`
- `partial`
- `complete`
- `failed`
- `stale`

## Phase 4 — Analyse locale low-level

**État** : workers Docker profil Compose **`audio`** (`audio-downloader`, `preview-resolver-worker`, `essentia-lowlevel-worker`). Jobs via **`job_items`** ([`16-job-execution-model-and-worker-parallelism.md`](16-job-execution-model-and-worker-parallelism.md)).

À la complétion d’un job audio/preview, `JobItemService.recompute_job_progress` met à jour `jobs.result_json` avec `succeeded`, `failed`, `skipped`, `not_found` (previews).

### AudioProvider

Interface :

```text
AudioProvider
  resolve(track) -> AudioSourceCandidate[]
  get_segments(track, segment_strategy) -> TrackSegment[]
  cleanup(job) -> CleanupResult
```

Implémentations :

- `YtDlpSegmentProvider`
- `CachedSegmentProvider`
- `TestAudioProvider`

### Résolution source audio

Critères :

- titre ;
- artiste principal ;
- album ;
- durée ;
- ISRC ;
- source URL ;
- score de matching textuel ;
- écart de durée.

Champs candidat :

```json
{
  "source": "youtube",
  "url": "...",
  "candidate_title": "...",
  "candidate_channel": "...",
  "candidate_duration": 240,
  "expected_duration": 238,
  "duration_delta": 2,
  "text_match_score": 0.92,
  "confidence": 0.88,
  "selected": true,
  "rejected_reason": null
}
```

### Stratégie segments

#### Modes Fast / Precise

L’analyse locale supporte 2 modes explicites, propagés depuis l’UI jusqu’aux jobs audio (`analysis_mode`):

- **Fast** (défaut) : **1 seul segment** représentatif.
  - Deezer preview si disponible (et jugée utilisable), sinon 1 segment YouTube centré.
- **Precise** : **3 segments**.
  - Deezer preview + 2 segments YouTube si Deezer+YouTube sont disponibles, sinon 3 segments YouTube.

Le code `analysis_decision` reflète désormais la réalité des segments planifiés/analy­sés :

- `deezer_only`
- `youtube_1_segment`
- `deezer_plus_youtube_2_segments`
- `youtube_3_segments`

Segments recommandés :

```text
A : 10–25 %
B : 45–60 %
C : 70–85 %
```

Règles :

- chaque segment `<= 30s` ;
- éviter intro immédiate ;
- éviter fade-out ;
- réduire durée pour morceaux courts ;
- permettre un seul segment si durée courte ;
- tester les cas limites : 20s, 45s, 90s, 10min.

### yt-dlp

Options minimales :

- `format=bestaudio/best`
- `download_ranges`
- `force_keyframes_at_cuts`
- `noplaylist=True`
- postprocessor FFmpeg vers WAV ou format attendu.

Interdit :

- télécharger playlist entière ;
- ignorer la limite 30s ;
- conserver fichier après analyse sans option debug explicite.

### FFmpeg

Responsabilités :

- extraire segment ;
- convertir en WAV PCM ;
- normaliser format d’entrée pour Essentia ;
- échouer proprement avec logs.

### Essentia low-level

Image :

```text
ghcr.io/mtg/essentia:bullseye-v2.1_beta5
```

Commande type :

```bash
essentia_streaming_extractor_music input.wav output.json profile.yaml
```

Le fichier `profiles/essentia_lowlevel_basic.yaml` suit le format **AcousticBrainz** (`outputFormat`, `lowlevel`/`rhythm`/`tonal`, `startTime`/`endTime`). Il ne doit pas utiliser une liste `algorithms:` (format d’un autre outil Essentia) — cela provoque l’erreur `YamlInput: invalid StereoSample format`.

Features extraites :

- BPM ;
- beats ;
- loudness ;
- key ;
- mode ;
- key confidence ;
- MFCC ;
- HPCP ;
- spectral centroid ;
- spectral rolloff ;
- spectral contrast ;
- dynamic complexity ;
- onset rate.

**Persistance** : agrégation multi-segments → `audio_feature_raw_payloads.payload_json.aggregated` (timbre/spectral inclus) + colonnes scalaires `audio_features` pour merge. L’UI Library (`GET /features/tracks/{id}` → `sources[].extended`) expose les descripteurs timbre.

**Meta segments** (drawer / `extended`) : `segments_planned`, `segments_analyzed`, `segments_missing_reason`, `analysis_decision`.

**Cleanup WAV** (inchangé) : après succès Essentia low-level, segments supprimés du cache sauf `AUDIO_KEEP_SEGMENTS_AFTER_ANALYSIS=true`.

#### Gating (éviter l’analyse locale inutile)

Par défaut, l’analyse Essentia low-level est **filtrée** pour ne tourner que si elle apporte de la valeur vs ReccoBeats :

- si ReccoBeats est absent / `failed` / `not_found` / `pending` → Essentia est autorisée (fallback),
- sinon Essentia ne s’exécute que si ReccoBeats a des champs low-level manquants (actuellement : `bpm`, `loudness`, `key`, `mode`, `duration_ms`).

Un override manuel existe via `force_refresh=true`.

## Phase 6 — Pipeline parallèle et Essentia TensorFlow

Le pipeline phase 6 remplace le modèle `download all → analyze all` par un handoff progressif et ajoute l'analyse avancée Essentia TensorFlow **réelle** lorsque les modèles sont présents. Voir [`16-job-execution-model-and-worker-parallelism.md`](16-job-execution-model-and-worker-parallelism.md), [`backlog/phase-6.md`](../backlog/phase-6.md) et [`19-essentia-tensorflow-model-management.md`](19-essentia-tensorflow-model-management.md).

### Règle bloquante phase 6

Les runners TensorFlow ne doivent **jamais** écrire de features avancées fake en runtime normal.

```text
APP_ENV=test + ESSENTIA_TF_ALLOW_STUBS_IN_TESTS=true → stubs autorisés
Sinon → stubs interdits (error STUB_INFERENCE_FORBIDDEN)
```

`inference_mode="real"` est réservé aux vraies inférences (modèle réel exécuté sur un WAV réel). Modèle absent → `model_missing`, jamais un score fake.

### Sources modèles

Les runners réels utilisent exclusivement les modèles déclarés dans :

```text
core/app/models_registry/essentia_models_manifest.yaml
```

Ce manifest est construit à partir de :

```text
https://essentia.upf.edu/models.html
https://essentia.upf.edu/models/
```

Le pipeline phase 6 utilise les fichiers TensorFlow `.pb` et metadata `.json`, pas ONNX/TFJS.

### Pipeline avancé réel

```text
POST /audio/analysis/advanced
  ↓
audio_analysis_pipeline job
  ↓
segment_download
  ↓ segment_ready
  ├─ essentia_lowlevel réel
  └─ essentia_tensorflow
       ├─ model profile check
       ├─ real Discogs EffNet embedding inference
       ├─ real Discogs519 genre inference if recommended profile installed
       └─ real classifier inference
  ↓
feature_aggregation
  ↓
audio_cleanup
```

| Stage | Worker |
|---|---|
| `segment_download` | `audio-downloader` |
| `essentia_lowlevel` | `essentia-lowlevel-worker` (un item = un segment ; upsert track différé) |
| `essentia_tensorflow_embeddings` / `essentia_tensorflow_classifiers` | `essentia-tensorflow-worker` (profil `advanced-analysis`) |
| `feature_aggregation` | core (`PipelineFeatureAggregationService`, après succès des prérequis stage) |
| `audio_cleanup` | core |

**Implémenté (6.3)** : le worker low-level réserve les stages `essentia_lowlevel` du job `audio_analysis_pipeline` (mode `streaming`), persiste les features par segment (`features_json` enrichi), puis le stage `feature_aggregation` agrège et appelle `FeatureUpsertService.upsert_essentia_lowlevel`. Le flux legacy `essentia_lowlevel_analysis` / `essentia_lowlevel_track` est inchangé.

**Contrat en place (6.6/6.7, inférence réelle restante)** : le stage `essentia_tensorflow_embeddings` produit `embedding_outputs` (Discogs EffNet) et `genre_outputs` (Discogs519) ; le stage `essentia_tensorflow_classifiers` produit `classifier_outputs` / `models_missing`. L'agrégation écrit `track_embeddings` et les features avancées/genre dans `track_advanced_features`, et calcule `energy_proxy` (source `derived`). `FeatureResolver` expose `style_embedding`, `timbre_embedding` (256 premières dims) et `genre_discogs_519*` avec fallbacks ReccoBeats. Le contrat de données est complet ; l'inférence réelle remplace les runners stub (cf. backlog 6.8B).

### Profils modèles

| Profil | Usage |
|---|---|
| `phase6-minimal` | Discogs EffNet + classifiers principaux |
| `phase6-recommended` | Ajoute MAEST + Genre Discogs519 |
| `phase6-full` | Ajoute MusicNN + DEAM/MuSe pour arousal/valence |

### Gestion modèles avant stage TensorFlow

Avant chaque stage TensorFlow :

1. lire le manifest ;
2. résoudre le profil demandé ;
3. vérifier les dépendances ;
4. vérifier présence `.pb` + `.json` ;
5. vérifier hash si attendu ;
6. si absent : stage `skipped`, error_code `MODEL_MISSING` ;
7. si metadata absente : stage `failed`, error_code `MODEL_METADATA_MISSING` ;
8. si hash invalide : stage `failed`, error_code `MODEL_INVALID_HASH` ;
9. si présent : exécuter l'inférence réelle.

### Sorties attendues

Chaque résultat TensorFlow doit inclure :

```json
{
  "inference_mode": "real",
  "model_key": "mood_happy_discogs_effnet",
  "model_name": "mood_happy-discogs-effnet-1",
  "model_version": "1",
  "model_hash": "computed-local-hash",
  "segment_id": 123,
  "wav_path_used": true,
  "pipeline_version": "phase6_tf_real_v1"
}
```

`inference_mode="stub"` est interdit hors tests.

### Essentia TensorFlow

Image custom :

```text
spotify-curator-essentia-tensorflow:<version>
```

Responsabilités :

- embeddings Discogs EffNet ;
- genre Discogs519 ;
- moods (aggressive, happy, party, relaxed, sad) ;
- approachability / engagement ;
- arousal/valence, voice/instrumental, electronic/acoustic ;
- fallbacks `danceability_tf`, `valence_tf`, `energy_proxy`.

### Features avancées phase 6

- `genre_discogs_519`, `genre_discogs_519_top_label`, `genre_discogs_519_top_score`, `genre_discogs_519_top_k`
- `approachability`, `engagement`
- `mood_*_score`, `electronic_profile_score`, `acoustic_profile_score`
- `voice_probability`, `vocal_presence_score`, `instrumental_focus_score`
- `danceability_tf`, `valence_tf`, `energy_proxy`

Ces champs ne remplacent pas automatiquement ReccoBeats si celui-ci fournit une valeur fiable.

### Priorité source (phase 6)

| Feature | Prioritaire | Fallback |
|---|---|---|
| `energy` | ReccoBeats | `energy_proxy` |
| `danceability` | ReccoBeats | `danceability_tf` |
| `valence` | ReccoBeats | `valence_tf` |
| `instrumentalness` | ReccoBeats | `instrumental_focus_score` |
| `acousticness` | ReccoBeats | `acoustic_profile_score` |
| `bpm`, `key`, `mode` | Essentia low-level | ReccoBeats |
| `mood_*`, `genre_discogs_519` | Essentia TensorFlow | missing |

### Particularité valence

Aucun modèle `valence-discogs-effnet` ne doit être inventé (absent du catalogue officiel utilisé).

Règle phase 6 :

- `valence` prioritaire : ReccoBeats ;
- fallback local réel uniquement si `phase6-full` installe MusicNN + DEAM/MuSe ;
- sinon `valence_tf` = `model_missing` ou `not_supported_yet`.

### Gestion modèles

Chaque modèle doit avoir :

- nom, version, hash, chemin local non commité ;
- statut `available` / `missing` / `invalid_hash` / `disabled` ;
- endpoints `GET /api/v1/models/status`, `POST /api/v1/models/download`, `POST /api/v1/models/download-profile`, `POST /api/v1/models/verify`.

Détail complet (manifest, profils, downloader, CLI, licence) : [`19-essentia-tensorflow-model-management.md`](19-essentia-tensorflow-model-management.md).

### Cleanup multi-consommateurs

Un segment WAV peut être supprimé seulement si tous les consommateurs requis (`essentia_lowlevel`, `essentia_tensorflow_embeddings`, `essentia_tensorflow_classifiers`) sont en `success`, `skipped` ou échec terminal, et `AUDIO_KEEP_SEGMENTS_AFTER_ANALYSIS=false`.

### Compatibilité phase 5

Le playlist engine consomme uniquement `FeatureRegistry`, `FeatureResolver`, `TrackFeatureView` — jamais les payloads bruts Essentia/TensorFlow.

### Validation

Le smoke test phase 6 doit prouver :

- un WAV est lu ;
- un modèle réel est utilisé ;
- une sortie non vide est générée ;
- la sortie est persistée ;
- les features sont visibles via API ;
- un appel stub hors test échoue avec `STUB_INFERENCE_FORBIDDEN`.

## Fusion des features

Priorité générale :

1. valeur manuelle ;
2. local multi-segments ;
3. local segment unique ;
4. ReccoBeats ;
5. metadata ;
6. inconnu.

La priorité peut varier par feature :

- tempo : local peut être prioritaire ;
- danceability : ReccoBeats peut rester prioritaire ;
- structure : local obligatoire ;
- embeddings : local obligatoire ;
- key : comparer sources et confiance.

## Agrégation multi-segments

| Feature | Agrégation |
|---|---|
| tempo | médiane |
| loudness | moyenne ou médiane |
| key | vote pondéré confiance |
| energy | moyenne pondérée ou p75 |
| danceability | moyenne pondérée |
| valence | moyenne |
| vocal_presence | moyenne/p75 |
| embeddings | moyenne ou centroïde |

## Scores dérivés

Scores généralistes :

- `energy_profile_score`
- `calm_score`
- `intensity_score`
- `mood_positive_score`
- `mood_dark_score`
- `mood_melancholic_score`
- `focus_score`
- `background_score`
- `vocal_presence_score`
- `instrumental_focus_score`
- `acoustic_profile_score`
- `electronic_profile_score`
- `rhythmic_stability_score`
- `tempo_stability_score`
- `groove_score`
- `structure_clarity_score`

Scores optionnels DJ/mix :

- `mixability_score`
- `harmonic_compatibility_score`
- `intro_outro_usability_score`
- `transition_smoothness_score`

## Cleanup

Après analyse (phase 4, un consommateur) :

1. vérifier JSON produit ;
2. parser features ;
3. stocker résultats ;
4. supprimer audio temporaire ;
5. renseigner `deleted_at` ;
6. logguer erreurs cleanup ;
7. exposer nettoyage manuel UI.

Phase 6 : voir cleanup multi-consommateurs ci-dessus.

## Tests critiques

- génération segments `<=30s` ;
- morceaux courts ;
- erreurs yt-dlp ;
- erreurs FFmpeg ;
- parser JSON Essentia ;
- merge ReccoBeats/local ;
- suppression fichiers ;
- idempotence si JSON déjà présent ;
- handoff downloader → low-level / TensorFlow (phase 6) ;
- premier segment analysé avant fin téléchargement global ;
- modèles manquants sans crash ;
- non-régression playlist engine phase 5.
