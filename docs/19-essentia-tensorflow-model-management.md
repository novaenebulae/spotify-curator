# 19 — Gestion des modèles Essentia TensorFlow

Tags: #models #essentia #tensorflow #phase-6 #manifest #download #inference

## Objectif

Définir comment l'application Spotify Curator découvre, télécharge, vérifie et utilise les modèles Essentia TensorFlow nécessaires à la phase 6.

Cette documentation corrige une divergence importante : la phase 6 ne doit pas être validée avec des runners TensorFlow en stub de production. Les stubs sont autorisés uniquement pour les tests unitaires, sous flag explicite.

## Sources officielles

Les seules sources autorisées pour le manifest phase 6 sont :

```text
https://essentia.upf.edu/models.html
https://essentia.upf.edu/models/
```

La page `models.html` sert de documentation fonctionnelle : tâches, familles de modèles, exemples de code, algorithmes Essentia à utiliser, sorties attendues.

Le dossier `/models/` sert de source de téléchargement : fichiers TensorFlow `.pb` et metadata `.json`.

Règles :

- utiliser uniquement les fichiers `.pb` et `.json` dans le pipeline Essentia actuel ;
- ne pas choisir `.onnx`, `.tfjs.zip` ou `savedmodel.zip` sauf décision technique future explicite ;
- ne pas télécharger toute l'arborescence `/models/` ;
- ne télécharger que les modèles déclarés dans `essentia_models_manifest.yaml`.

## Licence

Les modèles MTG/Essentia indiqués sur la page officielle sont sous licence `CC BY-NC-SA 4.0` pour l'usage non commercial, avec possibilité de licence propriétaire sur demande.

Conséquences produit :

- le téléchargement ne doit jamais être automatique au démarrage ;
- l'utilisateur doit accepter explicitement la licence avant téléchargement ;
- l'UI doit afficher la licence du profil/modèle ;
- `ESSENTIA_MODELS_ACCEPT_LICENSE=false` par défaut ;
- l'API doit refuser `POST /models/download*` si `accept_license=false`.

## Emplacement local

Les modèles sont stockés dans un volume ignoré par Git :

```text
MODELS_DIR=/app/models
ESSENTIA_MODELS_DIR=/app/models/essentia
```

Arborescence recommandée :

```text
models/
  essentia/
    feature-extractors/
      discogs-effnet/
      maest/
      musicnn/
    classification-heads/
      mood_aggressive/
      mood_happy/
      mood_party/
      mood_relaxed/
      mood_sad/
      mood_acoustic/
      mood_electronic/
      voice_instrumental/
      danceability/
      approachability/
      engagement/
      genre_discogs519/
      deam/
      muse/
```

À ne jamais commiter :

```text
models/*
*.pb
*.onnx
*.h5
*.tflite
*.tfjs
*.zip
```

## Manifest obligatoire

Le fichier suivant devient un livrable bloquant de phase 6 :

```text
core/app/models_registry/essentia_models_manifest.yaml
```

Chaque entrée doit déclarer :

```yaml
model_key: mood_happy_discogs_effnet
display_name: Mood Happy — Discogs EffNet
task: classifier
family: classification-head
backend: essentia_tensorflow_pb
weights_url: https://essentia.upf.edu/models/classification-heads/mood_happy/mood_happy-discogs-effnet-1.pb
metadata_url: https://essentia.upf.edu/models/classification-heads/mood_happy/mood_happy-discogs-effnet-1.json
local_weights_path: essentia/classification-heads/mood_happy/mood_happy-discogs-effnet-1.pb
local_metadata_path: essentia/classification-heads/mood_happy/mood_happy-discogs-effnet-1.json
depends_on:
  - discogs_effnet_bs64
required_for:
  - mood_happy_score
license: CC BY-NC-SA 4.0
expected_sha256: null
size_bytes: 514458
```

`expected_sha256` peut être `null` au départ si Essentia ne fournit pas de hash officiel, mais le système doit calculer le SHA256 local après téléchargement et l'afficher.

## Profils de téléchargement

### `phase6-minimal`

But : obtenir une vraie inférence TensorFlow légère et couvrir les classifiers Discogs-EffNet principaux, sans télécharger MAEST.

Contenu :

```text
Feature extractor:
- discogs-effnet-bs64-1.pb
- discogs-effnet-bs64-1.json

Classification heads:
- mood_aggressive-discogs-effnet-1.pb/json
- mood_happy-discogs-effnet-1.pb/json
- mood_party-discogs-effnet-1.pb/json
- mood_relaxed-discogs-effnet-1.pb/json
- mood_sad-discogs-effnet-1.pb/json
- mood_acoustic-discogs-effnet-1.pb/json
- mood_electronic-discogs-effnet-1.pb/json
- voice_instrumental-discogs-effnet-1.pb/json
- danceability-discogs-effnet-1.pb/json
- approachability_regression-discogs-effnet-1.pb/json
- engagement_regression-discogs-effnet-1.pb/json
```

Ce profil couvre :

```text
style_embedding
timbre_embedding
mood_aggressive_score
mood_happy_score
mood_party_score
mood_relaxed_score
mood_sad_score
acoustic_profile_score
electronic_profile_score
voice_probability
vocal_presence_score
instrumental_focus_score
danceability_tf
approachability
engagement
```

### `phase6-recommended`

But : couvrir le périmètre phase 6 complet attendu, y compris Genre Discogs519.

Contenu :

```text
Tout phase6-minimal

MAEST feature extractor:
- discogs-maest-30s-pw-519l-2.pb
- discogs-maest-30s-pw-519l-2.json

Genre Discogs519 classification head:
- genre_discogs519-discogs-maest-30s-pw-519l-1.pb
- genre_discogs519-discogs-maest-30s-pw-519l-1.json
```

Ce profil ajoute :

```text
genre_discogs_519
genre_discogs_519_top_label
genre_discogs_519_top_score
genre_discogs_519_top_k
```

### `phase6-full`

But : ajouter une première inférence arousal/valence réelle hors Discogs-EffNet.

Contenu :

```text
Tout phase6-recommended

MusicNN feature extractor:
- msd-musicnn-1.pb
- msd-musicnn-1.json

Arousal/valence heads optionnels:
- deam-msd-musicnn-2.pb/json
- muse-msd-musicnn-2.pb/json
```

Important : aucun modèle `valence-discogs-effnet` n'est retenu en phase 6, car il n'est pas documenté dans le catalogue officiel utilisé. En l'absence de `phase6-full`, `valence` reste prioritairement fournie par ReccoBeats ; sinon `valence_tf` doit être `model_missing` ou `not_supported_yet`.

## Catalogue contrôlé phase 6

### Feature extractor Discogs-EffNet

```yaml
- model_key: discogs_effnet_bs64
  display_name: Discogs EffNet BS64
  task: embedding
  weights_url: https://essentia.upf.edu/models/feature-extractors/discogs-effnet/discogs-effnet-bs64-1.pb
  metadata_url: https://essentia.upf.edu/models/feature-extractors/discogs-effnet/discogs-effnet-bs64-1.json
  local_weights_path: essentia/feature-extractors/discogs-effnet/discogs-effnet-bs64-1.pb
  local_metadata_path: essentia/feature-extractors/discogs-effnet/discogs-effnet-bs64-1.json
  required_for: [style_embedding, timbre_embedding]
```

### Classification heads Discogs-EffNet

```yaml
- mood_aggressive_discogs_effnet
- mood_happy_discogs_effnet
- mood_party_discogs_effnet
- mood_relaxed_discogs_effnet
- mood_sad_discogs_effnet
- mood_acoustic_discogs_effnet
- mood_electronic_discogs_effnet
- voice_instrumental_discogs_effnet
- danceability_discogs_effnet
- approachability_regression_discogs_effnet
- engagement_regression_discogs_effnet
```

Tous dépendent de :

```text
discogs_effnet_bs64
```

### Genre Discogs519

```yaml
- model_key: discogs_maest_30s_pw_519l
  task: embedding
  weights_url: https://essentia.upf.edu/models/feature-extractors/maest/discogs-maest-30s-pw-519l-2.pb
  metadata_url: https://essentia.upf.edu/models/feature-extractors/maest/discogs-maest-30s-pw-519l-2.json

- model_key: genre_discogs519_maest_519l
  task: genre_classifier
  weights_url: https://essentia.upf.edu/models/classification-heads/genre_discogs519/genre_discogs519-discogs-maest-30s-pw-519l-1.pb
  metadata_url: https://essentia.upf.edu/models/classification-heads/genre_discogs519/genre_discogs519-discogs-maest-30s-pw-519l-1.json
  depends_on: [discogs_maest_30s_pw_519l]
```

## ModelManager

Créer :

```text
core/app/models_registry/manager.py
```

API Python attendue :

```python
list_models()
list_profiles()
get_status()
get_model_status(model_key)
download_model(model_key, accept_license: bool, force: bool = False)
download_profile(profile: str, accept_license: bool, force: bool = False)
verify_model(model_key)
verify_profile(profile)
compute_sha256(path)
read_metadata(model_key)
```

Statuts :

```text
available
missing
downloading
invalid_hash
disabled
license_not_accepted
download_failed
metadata_missing
weights_missing
```

## CLI

Créer :

```text
core/scripts/download_essentia_models.py
```

Commandes attendues :

```bash
uv run python scripts/download_essentia_models.py --profile phase6-minimal --accept-license
uv run python scripts/download_essentia_models.py --profile phase6-recommended --accept-license
uv run python scripts/download_essentia_models.py --profile phase6-full --accept-license
uv run python scripts/download_essentia_models.py --model discogs_effnet_bs64 --accept-license
uv run python scripts/download_essentia_models.py --verify-only
```

## API

Endpoints :

```text
GET  /api/v1/models/status
POST /api/v1/models/download
POST /api/v1/models/download-profile
POST /api/v1/models/verify
```

`POST /models/download-profile` :

```json
{
  "profile": "phase6-recommended",
  "accept_license": true,
  "force": false
}
```

Si `accept_license=false` :

```json
{
  "error": {
    "code": "MODEL_LICENSE_NOT_ACCEPTED",
    "message": "Model download requires accepting the declared model license.",
    "retryable": false
  }
}
```

## Runtime worker

L'inférence réelle s'exécute uniquement dans le service `essentia-tensorflow-worker`. Son image (`docker/essentia-tensorflow-worker/Dockerfile`) est construite sur `python:3.11-slim` puis installe le wheel PyPI `essentia-tensorflow` dans le venv `uv`. L'image de base MTG (`ghcr.io/mtg/essentia`) n'est pas utilisée : elle fournit un `essentia` compilé sans les algorithmes `TensorflowPredict*` et pour Python 3.9, incompatible avec notre `requires-python >=3.11`. Le service `core-api` n'embarque pas `essentia`.

Optimisation d'inférence : `EssentiaTensorflowBackend` calcule les embeddings de l'extracteur (Discogs-EffNet) **une seule fois par segment** puis les réutilise pour toutes les têtes `TensorflowPredict2D` (pattern recommandé par Essentia). Les prédicteurs sont mis en cache par `(algorithme, graphFilename, output, input)` pour la durée de vie du worker ; l'audio décodé et les frames d'embedding sont mis en cache (LRU borné) par WAV.

## Règles runtime

En production ou développement normal :

```text
modèle présent + hash OK      → inference_mode="real"
modèle absent                 → status="model_missing"
metadata absente              → status="model_invalid"
hash invalide                 → status="model_invalid"
stub appelé                   → error STUB_INFERENCE_FORBIDDEN
```

En test uniquement :

```text
APP_ENV=test
ESSENTIA_TF_ALLOW_STUBS_IN_TESTS=true
```

Les stubs peuvent produire des sorties contrôlées pour tests unitaires, mais ne doivent jamais écrire `status="success"` en runtime normal.

## Tests minimum

```text
tests/test_essentia_models_manifest.py
tests/test_model_manager.py
tests/test_models_download_api.py
tests/test_model_license_acceptance.py
tests/test_no_stub_in_production.py
```

Cas à couvrir :

- manifest YAML valide ;
- profils valides ;
- URLs `.pb` et `.json` présentes ;
- modèle absent → `missing` ;
- poids présent sans metadata → `metadata_missing` ;
- metadata présente sans poids → `weights_missing` ;
- hash local calculé ;
- licence non acceptée → refus ;
- téléchargement profil minimal n'inclut pas MAEST ;
- téléchargement profil recommended inclut MAEST + genre Discogs519 ;
- stub appelé hors test → `STUB_INFERENCE_FORBIDDEN`.

## Critère d'acceptation

La gestion modèles est acceptée si l'utilisateur peut :

1. consulter les modèles manquants ;
2. télécharger explicitement un profil ;
3. vérifier les fichiers ;
4. lancer une analyse avancée ;
5. obtenir soit une vraie inférence, soit un statut `model_missing`, jamais une feature fake.
