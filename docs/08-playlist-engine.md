# 08 — Moteur de playlists

Tags: #playlist #rules #scoring #sync #phase-5 #phase-6 #phase-7

## Objectif

Transformer une configuration utilisateur en playlist candidate, explicable et synchronisable vers Spotify après dry-run.

La phase 5 doit livrer un moteur simple, mais l'architecture doit rester prête pour :

- phase 6 — clusters UMAP/HDBSCAN ;
- phase 7 — embeddings, moods, voice/instrumental, Essentia TensorFlow ;
- phase 8 — génération avancée par seeds, courbes, similarité et découverte.

Règle structurante :

```text
Le moteur de playlists ne lit jamais les payloads bruts des providers.
Il consomme uniquement FeatureRegistry + TrackFeatureView.
```

Référence : `18-feature-consumption-contract.md`.

---

## Pipeline général

```text
PlaylistRule
  ↓
validate rule
  ↓
source selection
  ↓
load TrackFeatureView[]
  ↓
strict filters
  ↓
weighted scoring
  ↓
diversity constraints
  ↓
deduplication
  ↓
ordering
  ↓
preview persistence
  ↓
dry-run Spotify
  ↓
apply explicite plus tard
```

---

## Phase 5 — Playlist generator v1

## 1. Principes phase 5

La phase 5 doit produire une playlist utile avec les données disponibles :

- métadonnées Spotify ;
- liked tracks ;
- playlists importées ;
- ReccoBeats ;
- Essentia low-level ;
- previews disponibles ;
- statuts de disponibilité ;
- doublons / ISRC.

Elle ne dépend pas des embeddings ou des moods TensorFlow.

En revanche, elle doit accepter des règles qui mentionnent des features futures, en retournant des warnings structurés.

---

## 2. PlaylistRule

### 2.1 Format cible JSON/YAML

```yaml
name: "Dark / Intense"
description: "High-energy dark electronic selection."
target_size: 80
engine_version: "playlist_engine_v1"

source:
  liked_tracks: true
  playlists_include: []
  playlists_exclude: []
  track_ids_include: []
  track_ids_exclude: []
  clusters_include: []       # phase 6
  clusters_exclude: []       # phase 6
  seed_tracks: []            # phase 8

filters:
  features:
    bpm:
      min: 110
      max: 150
      required: true
    energy:
      min: 0.55
      required: true
    valence:
      max: 0.60
      required: false
    feature_confidence:
      min: 0.50
      required: true
    mood_dark_score:
      min: 0.60
      required: false
      unavailable_behavior: "warn"

  availability_status:
    include: ["available"]

  market_status:
    include: ["available", "unknown"]

  exclude_artists: []
  exclude_albums: []
  exclude_tags: []

weights:
  missing_component_behavior: "skip_and_renormalize"
  components:
    energy:
      weight: 0.25
    valence_inverse:
      weight: 0.15
    danceability:
      weight: 0.15
    playlist_fit_score:
      weight: 0.20
    diversity_bonus:
      weight: 0.15
    freshness_score:
      weight: 0.10
    mood_dark_score:
      weight: 0.20
      unavailable_behavior: "skip_and_renormalize"

constraints:
  max_tracks_per_artist: 3
  max_tracks_per_album: 2
  avoid_duplicate_isrc: true
  avoid_same_artist_consecutive: true
  cluster_diversity:
    enabled: false
  vocal_balance:
    enabled: false

ordering:
  mode: "score_desc"
  random_seed: 42

spotify:
  playlist_name: "Dark / Intense"
  visibility: "private"
  sync_mode: "replace_after_dry_run"
```

### 2.2 Champs obligatoires

- `name`
- `target_size`
- `source`
- `filters`
- `weights`
- `constraints`
- `ordering`
- `spotify`

### 2.3 Valeurs recommandées

- `target_size` défaut : `80`.
- `ordering.mode` défaut : `score_desc`.
- `weights.missing_component_behavior` défaut : `skip_and_renormalize`.
- `spotify.sync_mode` défaut : `replace_after_dry_run`.

---

## 3. Validation

L'endpoint `POST /playlist-rules/validate` doit vérifier :

- `target_size > 0` ;
- `target_size` raisonnable, ex. `<= 500` en MVP ;
- somme des poids non nulle ;
- filtres connus ;
- ordering connu ;
- sync mode connu ;
- valeurs min <= max ;
- features inconnues ;
- features futures indisponibles ;
- sources playlist existantes si IDs fournis ;
- contraintes cohérentes.

### 3.1 Erreurs bloquantes

```text
RULE_INVALID_YAML
RULE_INVALID_SCHEMA
UNKNOWN_FILTER
UNKNOWN_ORDERING_MODE
UNKNOWN_SYNC_MODE
INVALID_RANGE
NO_SOURCE_SELECTED
NO_SCORING_COMPONENTS
TARGET_SIZE_INVALID
```

### 3.2 Warnings non bloquants

```text
FEATURE_NOT_AVAILABLE_YET
FEATURE_MISSING_FOR_MANY_TRACKS
LOW_FEATURE_COVERAGE
WRITE_SCOPE_NOT_AVAILABLE
CLUSTER_SOURCE_NOT_AVAILABLE_YET
SEED_TRACKS_NOT_AVAILABLE_IN_PHASE_5
```

Une règle avec `mood_dark_score` en phase 5 doit être valide si `required=false`, mais retourner `FEATURE_NOT_AVAILABLE_YET`.

---

## 4. Source selection

Sources phase 5 :

- liked tracks ;
- playlists incluses ;
- playlists exclues ;
- sélection explicite `track_ids_include` ;
- exclusion explicite `track_ids_exclude`.

Sources futures déjà prévues dans le schéma :

- clusters phase 6 ;
- seeds phase 8.

### 4.1 Règles

- Si `liked_tracks=true`, inclure les titres actuellement likés.
- Si `playlists_include` est non vide, inclure les titres présents dans ces playlists.
- Si `playlists_exclude` est non vide, retirer les titres présents dans ces playlists.
- Si `track_ids_include` est non vide, les ajouter à la source candidate.
- Si `track_ids_exclude` est non vide, les retirer.
- La source finale doit être dédupliquée par `track_id`, puis contrôlée par ISRC si demandé.

---

## 5. Filtres stricts

Les filtres stricts éliminent avant scoring.

Filtres phase 5 :

- bpm min/max ;
- energy min/max ;
- valence min/max ;
- danceability min/max ;
- loudness min/max ;
- key/mode ;
- feature confidence min ;
- availability status ;
- market status ;
- artiste exclu ;
- album exclu ;
- playlist exclue ;
- tag exclu si tags implémentés ;
- doublon ISRC ;
- preview disponible si demandé.

### 5.1 Politique features manquantes

| Cas | Résultat |
|---|---|
| Feature présente et valide | appliquer filtre |
| Feature absente + `required=true` | exclure |
| Feature absente + `required=false` | garder avec warning |
| Feature future phase 7 | warning `FEATURE_NOT_AVAILABLE_YET` |
| Confidence insuffisante | exclure si filtre confidence strict, sinon warning |

### 5.2 Exclusion reason

Chaque exclusion doit être stockée.

```json
{
  "track_id": 1,
  "excluded": true,
  "reasons": [
    {
      "code": "BPM_OUT_OF_RANGE",
      "message": "BPM 98 below minimum 110",
      "field": "bpm",
      "value": 98,
      "expected": { "min": 110, "max": 150 }
    }
  ]
}
```

Codes minimum :

```text
BPM_OUT_OF_RANGE
ENERGY_OUT_OF_RANGE
VALENCE_OUT_OF_RANGE
DANCEABILITY_OUT_OF_RANGE
FEATURE_MISSING
FEATURE_NOT_AVAILABLE_YET
FEATURE_LOW_CONFIDENCE
ARTIST_EXCLUDED
ALBUM_EXCLUDED
PLAYLIST_EXCLUDED
DUPLICATE_ISRC_EXCLUDED
TRACK_UNAVAILABLE
MARKET_UNAVAILABLE
SCORE_NOT_COMPUTABLE
```

---

## 6. Scoring v1

Score final normalisé `0..1`.

```text
final_score = sum(component_contribution) + bonuses - penalties
```

### 6.1 Composants initiaux

- `energy`
- `valence`
- `valence_inverse`
- `danceability`
- `feature_confidence`
- `freshness_score`
- `playlist_fit_score`
- `diversity_bonus`
- `preview_bonus`

Composants futurs phase 7 :

- `mood_dark_score`
- `mood_aggressive_score`
- `mood_relaxed_score`
- `vocal_presence_score`
- `instrumental_focus_score`
- `acoustic_profile_score`
- `electronic_profile_score`
- `embedding_similarity`

### 6.2 Renormalisation

Si une composante est indisponible :

- la composante est ignorée ;
- les poids restants sont renormalisés ;
- le warning est conservé dans `score_details_json`.

Si aucune composante n'est calculable, la piste est exclue avec `SCORE_NOT_COMPUTABLE`.

### 6.3 Score details

Chaque item doit stocker :

```json
{
  "final_score": 0.84,
  "components": {
    "energy": {
      "value": 0.75,
      "initial_weight": 0.25,
      "effective_weight": 0.31,
      "contribution": 0.2325,
      "source": "reccobeats",
      "confidence": 1.0
    },
    "mood_dark_score": {
      "value": null,
      "initial_weight": 0.20,
      "effective_weight": 0.0,
      "contribution": 0.0,
      "skipped": true,
      "warning": "FEATURE_NOT_AVAILABLE_YET"
    }
  },
  "warnings": ["FEATURE_NOT_AVAILABLE_YET"],
  "engine_version": "playlist_engine_v1"
}
```

---

## 7. Diversité

Contraintes phase 5 :

- max titres par artiste ;
- max titres par album ;
- éviter doublons ISRC ;
- éviter même artiste consécutif ;
- diversité playlists sources ;
- diversité années si disponible.

Contraintes futures :

- diversité clusters phase 6 ;
- équilibre vocal/instrumental phase 7 ;
- diversité mood/style phase 7/8.

### 7.1 Sélection stable

La sélection doit être déterministe pour une même règle et un même état DB.

Utiliser :

- score desc ;
- tie-break par `track_id` ;
- `random_seed` uniquement si un mode random est demandé.

---

## 8. Ordering

Modes phase 5 :

```text
score_desc
score_asc
recently_added_desc
recently_added_asc
artist_grouped
artist_spread
random_seeded
```

Modes futurs :

```text
energy_curve_progressive
warmup_peak_cooldown
harmonic_flow
cluster_walk
embedding_similarity_path
```

En phase 5, les modes futurs doivent retourner `ORDERING_MODE_NOT_AVAILABLE_YET`.

---

## 9. Preview

La preview doit :

- créer `generated_playlists` ;
- créer `generated_playlist_items` ;
- stocker les scores ;
- stocker les raisons de sélection ;
- stocker les warnings ;
- stocker la configuration exacte utilisée ;
- ne jamais écrire dans Spotify.

### 9.1 Tables

Voir `05-domain-model.md`.

Champs importants :

```text
generated_playlists.config_json
generated_playlists.score_summary_json
generated_playlist_items.final_score
generated_playlist_items.score_details_json
generated_playlist_items.selected_reason
```

Ajouter si absent dans l'implémentation :

```text
generated_playlist_items.exclusion_details_json nullable
generated_playlists.engine_version
generated_playlists.warning_json nullable
```

---

## 10. Dry-run sync

Le dry-run compare une playlist candidate locale avec une cible Spotify.

Il ne doit jamais écrire dans Spotify.

Modes :

- `create` ;
- `replace` ;
- `add_only` ;
- `remove_obsolete` ;
- `replace_after_dry_run`.

Réponse :

```json
{
  "sync_job_id": "sync_1",
  "dry_run": true,
  "mode": "replace",
  "target_playlist": {
    "spotify_playlist_id": "...",
    "name": "..."
  },
  "diff": {
    "to_add": [],
    "to_remove": [],
    "unchanged": []
  },
  "warnings": []
}
```

Règles :

- si le scope write est absent, retourner un warning, mais le dry-run reste possible ;
- aucune route `apply` ne doit être ajoutée en phase 5 sans validation explicite ;
- ne pas demander de scopes write tant que l'action réelle n'est pas implémentée.

---

## 11. API phase 5

Endpoints à ajouter :

```text
POST /api/v1/playlist-rules/validate
POST /api/v1/playlist-rules
GET /api/v1/playlist-rules
GET /api/v1/playlist-rules/{rule_id}
PUT /api/v1/playlist-rules/{rule_id}
DELETE /api/v1/playlist-rules/{rule_id}
POST /api/v1/generated-playlists/preview
GET /api/v1/generated-playlists
GET /api/v1/generated-playlists/{generated_playlist_id}
POST /api/v1/sync/dry-run
GET /api/v1/sync/jobs/{sync_job_id}
```

CRUD minimal acceptable : create/list/read/update/disable. Delete peut être logique (`enabled=false`) si plus sûr.

---

## 12. UI phase 5

Route recommandée :

```text
/playlists
```

Sections :

- Presets ;
- Rule editor simple ;
- YAML advanced editor ;
- Validation ;
- Preview ;
- Score details ;
- Exclusions ;
- Ordering ;
- Dry-run sync.

Règles UI :

- afficher les warnings de features futures sans bloquer ;
- afficher le nombre de candidats initiaux, exclus, scorés, sélectionnés ;
- afficher les raisons d'exclusion ;
- afficher les composantes de score ;
- ne jamais afficher de bouton d'écriture Spotify réelle en phase 5 ;
- afficher clairement `Dry-run only`.

---

## 13. Presets initiaux

Presets phase 5 entièrement utilisables :

- Dark / Intense ;
- Calm / Focus ;
- High Energy ;
- Recently Added ;
- Discover Forgotten Likes ;
- Clean Library ;
- Missing Tracks Recovery.

Presets partiels avec warnings phase 7 :

- Low Vocal ;
- Instrumental Focus ;
- Electronic / Synthetic ;
- Acoustic / Organic ;
- Ambient / Drone ;
- IDM / Experimental ;
- EBM / Industrial.

Ces presets peuvent exister, mais doivent signaler que certaines composantes seront améliorées après phase 7.

---

## Phase 6 — Extension clustering

La phase 6 ajoute :

- `clusters_include` ;
- `clusters_exclude` ;
- `cluster_diversity` ;
- génération depuis un cluster ;
- affichage cluster dans les previews.

Le moteur phase 5 ne doit pas être refondu. Il doit seulement recevoir une nouvelle source candidate via le même pipeline.

---

## Phase 7 — Extension features avancées

La phase 7 ajoute :

- embeddings ;
- moods ;
- voice/instrumental ;
- acoustic/electronic ;
- styles/genres ;
- features dérivées.

Elle doit intégrer ces valeurs via :

```text
FeatureRegistry
FeatureResolver
TrackFeatureView
```

Elle ne doit pas créer un second moteur de playlists.

---

## Phase 8 — Playlist engine avancé

### Seed tracks

Objectif : générer une playlist proche d'un ou plusieurs morceaux.

Méthodes :

- similarité embeddings ;
- similarité features ;
- même cluster ;
- pondération seed.

### Energy curves

Modes :

- `progressive` ;
- `warmup_peak_cooldown` ;
- `high_energy_start` ;
- `calm_to_intense` ;
- `mood_curve`.

### Harmonic optionnel

Fonctionnalités :

- calcul Camelot ;
- compatibilité même clé ;
- clé voisine ;
- relatif majeur/mineur ;
- pénalité incompatibilité.

### Discovery mode

Objectifs :

- faire ressortir des likes anciens peu écoutés ;
- varier artistes ;
- éviter titres trop récents si demandé ;
- équilibrer familiarité/découverte.

### Explications avancées

L'UI doit pouvoir répondre :

- pourquoi ce titre est inclus ;
- pourquoi ce titre est exclu ;
- quels filtres ont agi ;
- quelles composantes ont contribué au score ;
- quelles contraintes ont déplacé ou retiré le titre.

---

## Tests critiques phase 5

- validation règle valide/invalide ;
- feature inconnue ;
- feature future indisponible ;
- filtre strict ;
- filtre avec feature manquante required ;
- filtre avec feature manquante optional ;
- scoring avec poids ;
- renormalisation poids ;
- score non calculable ;
- score details ;
- max tracks par artiste ;
- max tracks par album ;
- déduplication ISRC ;
- éviter même artiste consécutif ;
- preview persistée ;
- dry-run sync sans écriture ;
- explications inclusion/exclusion ;
- ordre stable avec random seed si utilisé.

---

## Critères d'acceptation phase 5

La phase 5 est acceptée si :

- une règle simple génère une preview ;
- les scores sont explicables ;
- les exclusions sont explicables ;
- les règles peuvent mentionner des features futures sans crash ;
- les features manquantes sont gérées proprement ;
- le dry-run sync n'écrit pas dans Spotify ;
- aucun scope write n'est requis pour la preview ;
- la documentation et les tests sont à jour ;
- l'architecture est prête pour phase 6 et phase 7.
