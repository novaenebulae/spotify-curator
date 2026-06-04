# 14 — Configuration — patch phase 6

Tags: #configuration #phase-6 #workers #tensorflow #models

## Variables à ajouter

```env
# Analysis pipeline
ANALYSIS_PIPELINE_MODE=streaming
ANALYSIS_ADVANCED_ENABLED=true
ANALYSIS_DEFAULT_INCLUDE_LOWLEVEL=true
ANALYSIS_DEFAULT_INCLUDE_TENSORFLOW=true

# Audio download
AUDIO_DOWNLOAD_WORKERS=2
AUDIO_DOWNLOAD_CONCURRENCY=2
AUDIO_DOWNLOAD_MAX_RETRIES=3

# Essentia low-level
ESSENTIA_LOWLEVEL_WORKERS=2
ESSENTIA_LOWLEVEL_MAX_RETRIES=2
ESSENTIA_LOWLEVEL_PROFILE=/app/profiles/essentia_lowlevel_basic.yaml

# Essentia TensorFlow
ESSENTIA_TENSORFLOW_WORKERS=1
ESSENTIA_TENSORFLOW_BATCH_SIZE=8
ESSENTIA_TENSORFLOW_MAX_RETRIES=1
ESSENTIA_TENSORFLOW_ITEM_LOCK_TIMEOUT_SECONDS=1800
ESSENTIA_TENSORFLOW_STATUS_ONLY=false

# Models
MODELS_DIR=/app/models
MODEL_REGISTRY_PATH=/app/models/model_registry.json
MODEL_HASH_CHECK_ENABLED=true
MODEL_DOWNLOAD_ENABLED=false

# Advanced features
ADVANCED_FEATURES_STORE_RAW_PAYLOADS=true
ADVANCED_FEATURES_TOP_K_GENRES=10
ENERGY_PROXY_ENABLED=true

# Cleanup
AUDIO_CLEANUP_WAIT_FOR_ALL_CONSUMERS=true
```

## Profils Docker Compose

### Profil `audio`

- `audio-downloader`
- `preview-resolver-worker`
- `essentia-lowlevel-worker`

### Profil `advanced-analysis`

- `essentia-tensorflow-worker`

Commande :

```bash
docker compose --profile audio --profile advanced-analysis up -d --build
```

## Modèles

Les modèles doivent être stockés sous :

```text
models/
  essentia/
  tensorflow/
  discogs_effnet/
  discogs_maest/
```

Interdit :

```text
*.pb
*.h5
*.tflite
*.onnx
models/*
```

sauf `.gitkeep` éventuel.

## Valeurs de départ recommandées

Machine standard :

```text
AUDIO_DOWNLOAD_WORKERS=2
ESSENTIA_LOWLEVEL_WORKERS=2
ESSENTIA_TENSORFLOW_WORKERS=1
```

PC puissant :

```text
AUDIO_DOWNLOAD_WORKERS=2-3
ESSENTIA_LOWLEVEL_WORKERS=3-4
ESSENTIA_TENSORFLOW_WORKERS=1-2 selon RAM
```
