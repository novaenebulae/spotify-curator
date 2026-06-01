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

## Phase 7 — Analyse avancée

### Essentia TensorFlow

Image custom :

```text
spotify-curator-essentia-tensorflow:<version>
```

Responsabilités :

- embeddings Discogs EffNet ;
- embeddings OpenL3 si retenu ;
- mood happy/sad/aggressive/relaxed/party ;
- arousal/valence ;
- voice/instrumental ;
- electronic/acoustic ;
- timbre.

### Gestion modèles

Chaque modèle doit avoir :

- nom ;
- version ;
- hash ;
- source ;
- taille ;
- statut disponible ;
- chemin local non commité.

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

Après analyse :

1. vérifier JSON produit ;
2. parser features ;
3. stocker résultats ;
4. supprimer audio temporaire ;
5. renseigner `deleted_at` ;
6. logguer erreurs cleanup ;
7. exposer nettoyage manuel UI.

## Tests critiques

- génération segments `<=30s` ;
- morceaux courts ;
- erreurs yt-dlp ;
- erreurs FFmpeg ;
- parser JSON Essentia ;
- merge ReccoBeats/local ;
- suppression fichiers ;
- idempotence si JSON déjà présent.
