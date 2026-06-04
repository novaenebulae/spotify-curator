# Prompt Cursor — Phase 6.8B — Inférence réelle Essentia TensorFlow

## Objectif

Remplacer les runners stub par des runners réels. Les stubs ne doivent plus pouvoir produire de succès en production.

## Audit obligatoire

Inspecter :

```text
embeddings_runner.py
genre_runner.py
classifier_runner.py
EssentiaTensorflowWorker
ModelRegistry / ModelManager
PipelineFeatureAggregationService
```

Identifier tous les endroits où :

```text
inference_mode="stub"
_deteministic_vector
segment_id utilisé comme source de score
wav_path ignoré
```

## À implémenter

1. Ajouter une garde globale :

```text
APP_ENV=test + ESSENTIA_TF_ALLOW_STUBS_IN_TESTS=true → stub autorisé
sinon → stub interdit
```

2. Embeddings réels :

- lire `wav_path` ;
- charger le modèle Discogs EffNet ;
- produire un vecteur réel ;
- valider dimension ;
- persister `inference_mode="real"`.

3. Genre réel :

- lire `wav_path` ou embeddings selon modèle retenu ;
- exécuter le modèle Genre Discogs519/style ;
- produire top label, top score, top-k.

4. Classifiers réels :

- moods ;
- acoustic/electronic ;
- voice/instrumental ;
- approachability ;
- engagement ;
- danceability ;
- arousal/valence.

5. Gestion erreurs :

- modèle absent → `model_missing` ;
- hash invalide → `model_invalid` ;
- échec TensorFlow → `TENSORFLOW_INFERENCE_FAILED` ;
- stub appelé hors test → `STUB_INFERENCE_FORBIDDEN`.

6. Tests :

```text
tests/test_tf_stub_guard.py
tests/test_essentia_tf_real_runners.py
tests/test_essentia_tf_model_missing.py
```

## Critères

- Les runners lisent réellement `wav_path`.
- Les résultats changent si l’audio change.
- Aucun stub n’écrit `success` en production.
- `inference_mode="real"` uniquement pour vraie inférence.

## Validation

```bash
cd core
uv run pytest tests/test_tf_stub_guard.py tests/test_essentia_tf_model_missing.py -q
```
