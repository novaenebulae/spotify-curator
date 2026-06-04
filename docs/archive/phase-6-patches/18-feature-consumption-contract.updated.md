# 18 — Feature consumption contract

Tags: #features #playlist-engine #clustering #phase-5 #phase-6 #phase-7 #architecture

## Objectif

Définir le contrat unique par lequel les modules applicatifs consomment les features musicales.

Règle fondamentale :

```text
Aucun moteur applicatif ne lit directement les payloads bruts ReccoBeats, Essentia ou TensorFlow.
```

Les consommateurs utilisent uniquement :

```text
FeatureRegistry
FeatureResolver
TrackFeatureView
```

---

## Sources

- ReccoBeats.
- Essentia low-level.
- Essentia TensorFlow.
- Embeddings.
- Spotify metadata.
- Tags utilisateur.
- Valeurs manuelles.
- Scores dérivés.

---

## Features phase 6 à déclarer

### Embeddings / genres

```text
style_embedding
timbre_embedding
genre_discogs_519
genre_discogs_519_top_label
genre_discogs_519_top_score
genre_discogs_519_top_k
```

### Engagement

```text
approachability
engagement
```

### Moods

```text
mood_aggressive_score
mood_happy_score
mood_party_score
mood_relaxed_score
mood_sad_score
```

### Profils sonores

```text
electronic_profile_score
acoustic_profile_score
voice_probability
vocal_presence_score
instrumental_focus_score
```

### Fallbacks

```text
danceability_tf
valence_tf
energy_proxy
```

---

## Alias

```text
genre_discogs519 → genre_discogs_519
mood_electronic → electronic_profile_score
mood_acoustic → acoustic_profile_score
instrumental → instrumental_focus_score
acoustic → acoustic_profile_score
valence_local → valence_tf
danceability_local → danceability_tf
```

---

## Priorité source par feature

| Feature consommée | Priorité |
|---|---|
| `energy` | ReccoBeats → `energy_proxy` |
| `danceability` | ReccoBeats → `danceability_tf` |
| `valence` | ReccoBeats → `valence_tf` |
| `instrumentalness` | ReccoBeats → `instrumental_focus_score` |
| `acousticness` | ReccoBeats → `acoustic_profile_score` |
| `bpm` | Essentia low-level → ReccoBeats |
| `key` / `mode` | Essentia low-level → ReccoBeats |
| `mood_*` | Essentia TensorFlow |
| `genre_discogs_519` | Essentia TensorFlow |
| `embedding_similarity` | `track_embeddings` |

---

## FeatureValue enrichi

```python
class FeatureValue:
    name: str
    value: Any | None
    confidence: float | None
    source: str | None
    source_version: str | None
    model_name: str | None
    model_version: str | None
    model_hash: str | None
    pipeline_version: str | None
    aggregation_method: str | None
    status: str
    missing_reason: str | None
    warnings: list[str]
```

---

## Status

```text
available
missing
not_available_yet
model_missing
invalid
low_confidence
source_failed
not_applicable
```

---

## Consommation playlist engine

La phase 5 doit continuer à fonctionner avec les règles existantes. Après la phase 6, les presets peuvent utiliser les nouvelles features sans changer de moteur.

Exemples :

```yaml
filters:
  features:
    mood_aggressive_score:
      min: 0.6
      required: false
    electronic_profile_score:
      min: 0.5
      required: false
```

---

## Consommation clustering phase 7

Le clustering construit la matrice via :

```text
FeatureProfile
TrackFeatureView[]
FeatureRegistry
```

Les profils peuvent utiliser :

- features numériques classiques ;
- moods ;
- embeddings ;
- genre top score ;
- vocal/acoustic/electronic.

---

## Tests minimum

- descriptor phase 6 présent ;
- alias résolu ;
- modèle manquant ;
- fallback ReccoBeats → local ;
- fallback local absent ;
- source priority ;
- playlist rule avec feature avancée ;
- clustering profile avec embedding ;
- TrackFeatureView sans payload raw.
