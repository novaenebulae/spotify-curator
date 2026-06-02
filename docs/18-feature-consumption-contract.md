# 18 — Feature consumption contract

Tags: #features #playlist-engine #clustering #phase-5 #phase-6 #phase-7 #architecture

## Objectif

Définir le contrat unique par lequel les modules applicatifs consomment les features musicales.

Ce document s'applique à :

- phase 5 — Playlist generator v1 ;
- phase 6 — clustering visuel UMAP/HDBSCAN ;
- phase 7 — Essentia TensorFlow, embeddings, moods, voice/instrumental ;
- phase 8 — playlist engine avancé.

Règle fondamentale :

```text
Aucun moteur applicatif ne doit lire directement les payloads bruts ReccoBeats, Essentia ou TensorFlow.
```

Les moteurs doivent consommer des vues normalisées, versionnées et explicables.

---

## 1. Problème à résoudre

Les features proviennent de plusieurs sources :

- ReccoBeats ;
- Essentia low-level ;
- Essentia TensorFlow ;
- embeddings ;
- métadonnées Spotify ;
- tags utilisateur ;
- valeurs manuelles ou dérivées.

Ces sources n'ont pas les mêmes champs, ni les mêmes niveaux de confiance.

Sans contrat commun, le moteur de playlists et le clustering risquent de dépendre directement :

- des colonnes SQL actuelles ;
- de la structure d'un payload ReccoBeats ;
- de la structure d'un JSON Essentia ;
- de noms de modèles TensorFlow ;
- d'une phase spécifique du projet.

Ce couplage rendrait la phase 7 coûteuse à intégrer.

---

## 2. Architecture cible

```text
Raw providers
  ├─ ReccoBeats
  ├─ Essentia low-level
  ├─ Essentia TensorFlow
  ├─ embeddings
  ├─ metadata
  └─ manual/user tags
      ↓
Feature storage
  ├─ audio_features
  ├─ audio_feature_raw_payloads
  ├─ track_embeddings
  └─ tags / metadata
      ↓
FeatureRegistry
      ↓
FeatureResolver
      ↓
TrackFeatureView
      ↓
Consumers
  ├─ Playlist engine
  ├─ Clustering matrix builder
  ├─ Explorer UI
  └─ Explanations
```

---

## 3. FeatureRegistry

### 3.1 Rôle

Le `FeatureRegistry` déclare toutes les features consommables par l'application.

Il ne calcule pas les valeurs. Il décrit :

- le nom canonique ;
- le type ;
- la plage attendue ;
- les sources disponibles ;
- les sources futures ;
- la stratégie de normalisation ;
- la stratégie en cas de valeur manquante ;
- les phases où la feature devient disponible.

### 3.2 Exemple de descriptor

```python
FeatureDescriptor(
    name="energy",
    label="Energy",
    value_type="float",
    range_min=0.0,
    range_max=1.0,
    available_sources=["reccobeats", "essentia_lowlevel"],
    future_sources=["essentia_tensorflow"],
    phase_available=3,
    normalization="identity_0_1",
    missing_policy="exclude_if_required",
)
```

```python
FeatureDescriptor(
    name="mood_dark_score",
    label="Dark mood",
    value_type="float",
    range_min=0.0,
    range_max=1.0,
    available_sources=[],
    future_sources=["essentia_tensorflow", "derived"],
    phase_available=7,
    normalization="identity_0_1",
    missing_policy="warn_until_available",
)
```

### 3.3 Features phase 5 disponibles

```text
bpm
tempo_alias
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

### 3.4 Features phase 7 futures

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
timbre_embedding
style_embedding
genre_discogs_519
```

### 3.5 Alias

Le registry doit accepter des alias historiques ou utilisateur.

Exemples :

```text
tempo → bpm
valence_inverse → 1 - valence
energy_profile_score → energy, puis dérivé phase 7/8
instrumental_focus_score → instrumentalness, puis voice/instrumental phase 7
```

Les alias doivent être résolus avant validation des règles.

---

## 4. FeatureResolver

### 4.1 Rôle

Le `FeatureResolver` charge les valeurs de features pour un ensemble de pistes.

Il applique :

- priorité des sources ;
- validation des valeurs ;
- conversion d'échelle ;
- confidence ;
- fallback ;
- métadonnées de source.

### 4.2 Priorité source par défaut

Priorité générale :

```text
manual
  ↓
essentia_tensorflow / derived advanced
  ↓
essentia_lowlevel multi-segment
  ↓
essentia_lowlevel single-segment
  ↓
reccobeats
  ↓
spotify metadata
  ↓
unknown
```

Exceptions possibles :

- `danceability`, `energy`, `valence` peuvent rester ReccoBeats en phase 5 si Essentia low-level ne produit pas un équivalent fiable.
- `bpm`, `key`, `mode`, `loudness` peuvent privilégier Essentia low-level si confidence suffisante.
- `embedding_similarity` est obligatoirement `track_embeddings`.
- `voice_probability` et `mood_*` sont obligatoirement phase 7 ou dérivés ultérieurs.

### 4.3 Sortie attendue

Le resolver retourne une `TrackFeatureView` par piste.

---

## 5. TrackFeatureView

### 5.1 Rôle

`TrackFeatureView` est la vue stable consommée par le playlist engine et le clustering.

Elle doit être indépendante des payloads bruts.

### 5.2 Structure conceptuelle

```python
class FeatureValue:
    name: str
    value: Any | None
    confidence: float | None
    source: str | None
    source_version: str | None
    status: str
    missing_reason: str | None
    warnings: list[str]

class TrackFeatureView:
    track_id: int
    spotify_track_id: str | None
    title: str
    artist_names: list[str]
    artist_ids: list[int]
    album_id: int | None
    album_name: str | None
    isrc: str | None
    duration_ms: int | None
    availability_status: str | None
    market_status: str | None
    liked: bool | None
    playlist_ids: list[int]
    duplicate_status: str | None
    preview_available: bool
    features: dict[str, FeatureValue]
```

### 5.3 Status FeatureValue

```text
available
missing
not_available_yet
invalid
low_confidence
source_failed
not_applicable
```

### 5.4 Missing reasons

```text
FEATURE_NOT_AVAILABLE_YET
FEATURE_MISSING
FEATURE_SOURCE_FAILED
FEATURE_LOW_CONFIDENCE
FEATURE_INVALID_VALUE
FEATURE_NOT_APPLICABLE
TRACK_NOT_ANALYZED
```

---

## 6. Politique features manquantes

### 6.1 Filtres stricts

| Cas | Comportement |
|---|---|
| Feature présente et valide | appliquer le filtre |
| Feature absente + `required=true` | exclure |
| Feature absente + `required=false` | garder avec warning |
| Feature future phase 7 | warning `FEATURE_NOT_AVAILABLE_YET` |
| Confidence insuffisante | exclure si filtre confidence strict, sinon warning |

### 6.2 Scoring

| Cas | Comportement |
|---|---|
| Composante présente | calcul normal |
| Composante absente | ignorer et renormaliser les poids restants |
| Composante future indisponible | warning + skip |
| Toutes les composantes absentes | exclure avec `SCORE_NOT_COMPUTABLE` |

### 6.3 Renormalisation des poids

Exemple :

```yaml
weights:
  components:
    energy: 0.40
    valence_inverse: 0.30
    mood_dark_score: 0.30
```

Si `mood_dark_score` est indisponible en phase 5 :

```text
energy: 0.40 / 0.70 = 0.5714
valence_inverse: 0.30 / 0.70 = 0.4286
mood_dark_score: skipped
```

Le `score_details_json` doit conserver le poids initial et le poids effectif.

---

## 7. Consommation par le playlist engine

Le playlist engine ne doit consommer que :

```text
PlaylistRule
TrackFeatureView[]
FeatureRegistry
```

Il doit produire :

```text
GeneratedPlaylist
GeneratedPlaylistItem[]
Inclusion explanations
Exclusion explanations
Score details
Warnings
```

---

## 8. Consommation par le clustering

Le clustering doit consommer :

```text
FeatureProfile
TrackFeatureView[]
FeatureRegistry
```

Il doit produire :

```text
feature matrix
track_ids
feature_names
missing report
normalization report
UMAP projection
HDBSCAN labels
cluster memberships
```

Les profils phase 6 doivent pouvoir inclure des features futures désactivées jusqu'à la phase 7.

---

## 9. Compatibilité phase 7

La phase 7 ne doit pas modifier le contrat `PlaylistRule` ni le pipeline principal de phase 5.

Elle doit seulement :

1. ajouter des descriptors dans `FeatureRegistry` ;
2. enrichir `FeatureResolver` ;
3. écrire `track_embeddings` et features avancées ;
4. ajouter des profils de clustering ;
5. ajouter ou améliorer des presets de playlist.

Interdit :

```text
Créer un second moteur de playlist spécifique TensorFlow.
Créer une seconde matrice clustering incompatible avec FeatureProfile.
Lire les embeddings directement depuis l'UI.
Réécrire les règles existantes.
```

---

## 10. Tests minimum

### FeatureRegistry

- feature connue ;
- alias ;
- feature inconnue ;
- feature future ;
- plage min/max ;
- stratégie missing.

### FeatureResolver

- ReccoBeats seul ;
- Essentia low-level prioritaire ;
- valeur manquante ;
- confidence faible ;
- feature future indisponible ;
- valeur invalide ;
- fallback source.

### Playlist engine

- filtre avec feature manquante required ;
- filtre avec feature manquante optional ;
- scoring avec renormalisation ;
- score non calculable ;
- explanations.

### Clustering

- profil avec features disponibles ;
- profil avec feature future désactivée ;
- matrice avec imputation ;
- rapport missing.

---

## 11. Critères d'acceptation

Le contrat est accepté si :

- le moteur de playlists ne dépend pas des payloads bruts ;
- le clustering utilise le même resolver ;
- les features futures peuvent être déclarées sans casser la phase 5 ;
- les règles mentionnant des features phase 7 produisent des warnings, pas des crashes ;
- les scores restent explicables ;
- les tests couvrent features manquantes, futures et faibles confiances.
