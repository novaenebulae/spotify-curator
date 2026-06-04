# Prompt Cursor — Phase 6.8A — Gestion modèles, manifest officiel, downloader et vérification

Tu travailles sur Spotify Curator.

## Problème à corriger

La phase 6 a divergé : l'infrastructure TensorFlow existe partiellement, mais les modèles Essentia ne sont pas gérés explicitement et les runners peuvent rester en stub.

Objectif : l'utilisateur ne doit pas télécharger les modèles au hasard ni deviner les chemins. Cursor doit implémenter une gestion complète des modèles à partir des sources officielles.

## Sources officielles

Utiliser uniquement :

```text
https://essentia.upf.edu/models.html
https://essentia.upf.edu/models/
```

Contraintes :

- ne pas télécharger toute l'arborescence `/models/` ;
- ne pas choisir librement les modèles ;
- ne pas utiliser `.onnx`, `tfjs.zip`, `savedmodel.zip` dans le pipeline actuel ;
- utiliser les fichiers TensorFlow `.pb` + metadata `.json` ;
- aucun modèle lourd ne doit être commité ;
- les stubs sont interdits en runtime normal.

## À implémenter

### 1. Manifest versionné

Créer :

```text
core/app/models_registry/essentia_models_manifest.yaml
```

Le manifest doit déclarer explicitement les modèles phase 6.

### 2. Profils

Ajouter :

```text
phase6-minimal
phase6-recommended
phase6-full
```

#### phase6-minimal

Inclure :

```text
Feature extractor:
- discogs-effnet-bs64-1.pb/json

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

#### phase6-recommended

Ajouter :

```text
- discogs-maest-30s-pw-519l-2.pb/json
- genre_discogs519-discogs-maest-30s-pw-519l-1.pb/json
```

#### phase6-full

Ajouter :

```text
- msd-musicnn-1.pb/json
- deam-msd-musicnn-2.pb/json
- muse-msd-musicnn-2.pb/json
```

Note importante : ne pas inventer de modèle `valence-discogs-effnet`. Si aucun modèle valence compatible Discogs-EffNet n'est documenté, `valence_tf` doit rester `model_missing` / `not_supported_yet`, sauf si `phase6-full` installe MusicNN + DEAM/MuSe.

### 3. ModelManager

Créer :

```text
core/app/models_registry/manager.py
```

API attendue :

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

### 4. Endpoints

Ajouter ou compléter :

```text
GET  /api/v1/models/status
POST /api/v1/models/download
POST /api/v1/models/download-profile
POST /api/v1/models/verify
```

### 5. CLI

Ajouter :

```text
core/scripts/download_essentia_models.py
```

Commandes attendues :

```bash
uv run python scripts/download_essentia_models.py --profile phase6-minimal --accept-license
uv run python scripts/download_essentia_models.py --profile phase6-recommended --accept-license
uv run python scripts/download_essentia_models.py --profile phase6-full --accept-license
uv run python scripts/download_essentia_models.py --verify-only
```

### 6. Licence

La licence à afficher est :

```text
CC BY-NC-SA 4.0
```

Règles :

- `accept_license=true` obligatoire pour télécharger ;
- `ESSENTIA_MODELS_ACCEPT_LICENSE=false` par défaut ;
- si licence refusée : `MODEL_LICENSE_NOT_ACCEPTED`.

### 7. Tests

Ajouter :

```text
tests/test_essentia_models_manifest.py
tests/test_model_manager.py
tests/test_models_download_api.py
tests/test_model_license_acceptance.py
```

Tester :

- manifest YAML valide ;
- profils valides ;
- URLs `.pb` et `.json` présentes ;
- téléchargement profil minimal n'inclut pas MAEST ;
- téléchargement profil recommended inclut MAEST + Genre Discogs519 ;
- modèle absent → `missing` ;
- poids présent sans metadata → `metadata_missing` ;
- metadata présente sans poids → `weights_missing` ;
- hash local calculé ;
- licence non acceptée → refus ;
- aucun stub en production.

## Validation

```bash
cd core
uv run pytest tests/test_essentia_models_manifest.py tests/test_model_manager.py tests/test_models_download_api.py tests/test_model_license_acceptance.py -q
```

## Critères DONE

- L'utilisateur ne doit pas chercher les modèles manuellement.
- Le manifest contient les URLs officielles.
- Les profils sont listables via API.
- Le téléchargement est explicite.
- La vérification fonctionne.
- Aucun modèle n'est commité.
