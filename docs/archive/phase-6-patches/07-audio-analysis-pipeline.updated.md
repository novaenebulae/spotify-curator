# 07 — Pipeline audio et features

Tags: #audio #yt-dlp #ffmpeg #essentia #tensorflow #features #pipeline

## Objectif

Enrichir les titres avec des features musicales issues de sources multiples :

1. ReccoBeats.
2. Analyse locale segmentée.
3. Essentia low-level.
4. Essentia TensorFlow.
5. Embeddings Discogs/MAEST/OpenL3 selon modèles retenus.
6. Spotify metadata.
7. Tags utilisateur.
8. Valeurs manuelles ou dérivées.

Depuis la phase 6, le pipeline audio ne doit plus fonctionner en deux blocs bloquants `download all → analyze all`. Il doit fonctionner par handoff progressif entre workers.

---

## Règles strictes

- Pas de téléchargement complet standard.
- Segment temporaire uniquement.
- Segment `<= 30` secondes.
- Suppression audio après analyse par tous les consommateurs requis.
- Pas de commit audio.
- Pas de stockage audio permanent par défaut.
- Tout résultat local doit stocker `pipeline_version`.
- Toute feature doit conserver source, confiance, modèle et version si applicable.
- Les payloads bruts ne sont jamais consommés directement par le playlist engine ou le clustering.

---

## Pipeline phase 6

```text
POST /audio/analysis/advanced
  ↓
analysis_pipeline job
  ↓
stage: segment_download
  ↓ segment_ready
  ├─ stage: essentia_lowlevel
  └─ stage: essentia_tensorflow_embeddings
       ↓
     stage: essentia_tensorflow_classifiers
  ↓
stage: feature_aggregation
  ↓
stage: audio_cleanup
```

### Pourquoi séparer les branches low-level et TensorFlow

Le low-level Essentia extrait des descripteurs classiques : BPM, key, loudness, MFCC, HPCP, spectral features, etc.

Les modèles TensorFlow utilisent généralement l'audio ou des embeddings comme entrée. Ils ne doivent donc pas attendre les résultats low-level si les segments audio sont déjà prêts.

---

## Stages

| Stage | Entrée | Sortie | Worker |
|---|---|---|---|
| `segment_download` | track metadata | `track_segments` + fichier WAV temporaire | `audio-downloader` |
| `essentia_lowlevel` | segment WAV | low-level JSON + agrégats | `essentia-lowlevel-worker` |
| `essentia_tensorflow_embeddings` | segment WAV | embeddings segment/track | `essentia-tensorflow-worker` |
| `essentia_tensorflow_classifiers` | audio ou embeddings | moods, genre, voice/instrumental, etc. | `essentia-tensorflow-worker` |
| `feature_aggregation` | résultats stages | `audio_features`, advanced features, embeddings | core/worker |
| `audio_cleanup` | stage completion state | suppression fichiers temporaires | core/worker |

---

## Features low-level

À conserver depuis la phase 4 :

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

---

## Features avancées phase 6

### Genre / style

- `genre_discogs_519`
- `genre_discogs_519_top_label`
- `genre_discogs_519_top_score`
- `genre_discogs_519_top_k`

### Engagement / accessibilité

- `approachability`
- `engagement`

### Moods

- `mood_aggressive_score`
- `mood_happy_score`
- `mood_party_score`
- `mood_relaxed_score`
- `mood_sad_score`

### Profils sonores

- `electronic_profile_score`
- `acoustic_profile_score`
- `voice_probability`
- `vocal_presence_score`
- `instrumental_focus_score`

### Fallbacks locaux

- `danceability_tf`
- `valence_tf`
- `energy_proxy`

Important : ces champs ne remplacent pas automatiquement ReccoBeats si celui-ci fournit une valeur fiable. Ils servent de fallback ou de source alternative explicite.

---

## Priorité source recommandée

| Feature canonique | Source prioritaire | Fallback |
|---|---|---|
| `bpm` | Essentia low-level si confidence suffisante | ReccoBeats |
| `key` / `mode` | Essentia low-level si confidence suffisante | ReccoBeats |
| `loudness` | Essentia low-level | ReccoBeats |
| `energy` | ReccoBeats | `energy_proxy` |
| `danceability` | ReccoBeats | `danceability_tf` |
| `valence` | ReccoBeats | `valence_tf` normalisée |
| `instrumentalness` | ReccoBeats | `instrumental_focus_score` |
| `acousticness` | ReccoBeats | `acoustic_profile_score` |
| `mood_*` | Essentia TensorFlow | missing |
| `genre_discogs_519` | Essentia TensorFlow | missing |
| `embedding_similarity` | `track_embeddings` | missing |

---

## Agrégation multi-segments

| Feature | Agrégation |
|---|---|
| tempo | médiane |
| loudness | médiane ou moyenne robuste |
| key | vote pondéré par confidence |
| energy proxy | moyenne pondérée ou p75 |
| danceability TF | moyenne pondérée |
| valence TF | moyenne |
| moods | moyenne ou max selon modèle, à documenter |
| vocal presence | moyenne/p75 |
| embeddings | centroïde ou moyenne normalisée |
| genre top-k | moyenne des logits/probabilités puis top-k |

Chaque agrégat doit stocker :

```text
segments_planned
segments_used
aggregation_method
source_quality
confidence
pipeline_version
model_name
model_version
```

---

## Cleanup

Le cleanup audio doit être conditionné par l'état de consommation.

Un segment peut être supprimé seulement si :

```text
segment_download = success
AND all_required_consumers in success|skipped|failed_terminal
AND AUDIO_KEEP_SEGMENTS_AFTER_ANALYSIS=false
```

Consommateurs typiques :

- `essentia_lowlevel`
- `essentia_tensorflow_embeddings`
- `essentia_tensorflow_classifiers`

---

## Compatibilité phase 5

Le playlist engine continue de consommer uniquement :

```text
FeatureRegistry
FeatureResolver
TrackFeatureView
```

Aucun accès direct aux payloads Essentia/TensorFlow n'est autorisé.

---

## Tests critiques

- génération segments `<=30s` ;
- handoff downloader → low-level ;
- handoff downloader → TensorFlow ;
- premier segment analysé avant fin téléchargement global ;
- cleanup après multi-consommateurs ;
- modèles manquants ;
- mapping classifier ;
- embeddings shape ;
- merge ReccoBeats/local ;
- non-régression phase 5 playlist engine.
