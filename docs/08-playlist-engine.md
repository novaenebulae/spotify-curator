# 08 — Moteur de playlists

Tags: #playlist #rules #scoring #sync

## Objectif

Transformer une configuration utilisateur en playlist candidate, explicable et synchronisable vers Spotify après dry-run.

## Pipeline général

```text
source selection
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
preview
  ↓
dry-run Spotify
  ↓
apply explicite plus tard
```

## Phase 5 — Playlist generator v1

### PlaylistRule

Format JSON/YAML :

```yaml
name: "Dark / Intense"
target_size: 80

source:
  liked_tracks: true
  playlists_include: []
  playlists_exclude: []

filters:
  tempo:
    min: 110
    max: 150
  energy:
    min: 0.55
  valence:
    max: 0.60
  feature_confidence:
    min: 0.50
  availability_status:
    include: ["available"]

weights:
  energy: 0.25
  valence_inverse: 0.15
  danceability: 0.15
  playlist_fit_score: 0.20
  diversity_bonus: 0.15
  freshness_score: 0.10

constraints:
  max_tracks_per_artist: 3
  max_tracks_per_album: 2
  avoid_duplicate_isrc: true
  avoid_same_artist_consecutive: true

ordering:
  mode: "score_desc"

spotify:
  playlist_name: "Dark / Intense"
  visibility: "private"
  sync_mode: "replace_after_dry_run"
```

### Validation

Le schéma doit vérifier :

- `target_size > 0` ;
- somme des poids non nulle ;
- filtres connus ;
- ordering connu ;
- sync_mode connu ;
- valeurs min <= max ;
- features requises disponibles ou avertissement.

### Source selection

Sources possibles :

- liked tracks ;
- playlists incluses ;
- playlists exclues ;
- sélection UI ;
- cluster ;
- seed tracks en phase 8.

### Filtres stricts

Éliminent avant scoring :

- tempo hors intervalle ;
- energy hors intervalle ;
- valence hors intervalle ;
- feature confidence insuffisante ;
- artiste exclu ;
- album exclu ;
- doublon ISRC ;
- indisponible Spotify ;
- déjà présent dans playlist exclue ;
- tag utilisateur exclu.

Chaque exclusion doit pouvoir être expliquée :

```json
{
  "track_id": "trk_1",
  "excluded": true,
  "reasons": [
    {
      "code": "TEMPO_OUT_OF_RANGE",
      "message": "Tempo 98 below minimum 110"
    }
  ]
}
```

### Scoring v1

Score final normalisé 0..1.

```text
final_score =
  weight_1 * normalized_feature_1
+ weight_2 * normalized_feature_2
+ ...
+ diversity_bonus
```

Chaque item doit stocker `score_details_json` :

```json
{
  "final_score": 0.84,
  "components": {
    "energy": { "value": 0.75, "weight": 0.25, "contribution": 0.1875 },
    "danceability": { "value": 0.80, "weight": 0.15, "contribution": 0.12 }
  },
  "warnings": []
}
```

### Diversité

Contraintes :

- max titres par artiste ;
- max titres par album ;
- éviter doublons ISRC ;
- éviter même artiste consécutif ;
- diversité playlists sources ;
- diversité années si disponible ;
- équilibre vocal/instrumental plus tard ;
- diversité clusters en phase 6+.

### Preview

La preview doit créer une entrée `generated_playlists` et des items `generated_playlist_items`.

Elle ne doit pas écrire dans Spotify.

### Dry-run sync

Compare playlist candidate avec playlist Spotify cible.

Modes :

- `create` ;
- `replace` ;
- `add_only` ;
- `remove_obsolete` ;
- `replace_after_dry_run`.

Réponse dry-run :

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

## Phase 8 — Playlist engine avancé

### Seed tracks

Objectif : générer une playlist proche d’un ou plusieurs morceaux.

Méthodes :

- similarité embeddings ;
- similarité features ;
- même cluster ;
- pondération seed.

Configuration :

```yaml
seeds:
  track_ids:
    - trk_1
    - trk_2
  similarity_source: "embedding"
  min_similarity: 0.60
```

### Energy curves

Modes :

- `progressive` ;
- `warmup_peak_cooldown` ;
- `high_energy_start` ;
- `calm_to_intense` ;
- `mood_curve`.

Le moteur doit réordonner sans violer les contraintes fortes.

### Harmonic optionnel

Fonctionnalités :

- calcul Camelot ;
- compatibilité même clé ;
- clé voisine ;
- relatif majeur/mineur ;
- pénalité incompatibilité.

Cette logique est optionnelle et ne doit pas dominer le moteur généraliste.

### Discovery mode

Objectifs :

- faire ressortir des likes anciens peu écoutés ;
- varier artistes ;
- éviter titres trop récents si demandé ;
- équilibrer familiarité/découverte.

### Explications

L’UI doit pouvoir répondre :

- pourquoi ce titre est inclus ;
- pourquoi ce titre est exclu ;
- quels filtres ont agi ;
- quelles composantes ont contribué au score ;
- quelles contraintes ont déplacé ou retiré le titre.

## Presets initiaux

- Dark / Intense ;
- Calm / Focus ;
- Ambient / Drone ;
- IDM / Experimental ;
- EBM / Industrial ;
- Pop / Vocal ;
- Acoustic / Organic ;
- Electronic / Synthetic ;
- High Energy ;
- Low Vocal ;
- Instrumental Focus ;
- Discover Forgotten Likes ;
- Recently Added ;
- Clean Library ;
- Missing Tracks Recovery ;
- Mix Context optionnel.

## Tests critiques

- validation règle valide/invalide ;
- filtres stricts ;
- scoring avec poids ;
- score details ;
- max tracks par artiste ;
- déduplication ISRC ;
- preview persistée ;
- dry-run sync sans écriture ;
- explications inclusion/exclusion ;
- ordre stable avec random seed si utilisé.
