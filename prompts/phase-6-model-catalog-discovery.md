# Prompt Cursor — Phase 6 — Découverte contrôlée du catalogue Essentia

## Objectif

Construire ou mettre à jour `core/app/models_registry/essentia_models_manifest.yaml` à partir des sources officielles Essentia, sans télécharger toute l'arborescence.

## Sources

```text
https://essentia.upf.edu/models.html
https://essentia.upf.edu/models/
```

## Règles

- Utiliser `models.html` pour comprendre les familles de modèles et les exemples d'inférence.
- Utiliser `/models/` pour vérifier l'existence exacte des fichiers `.pb` et `.json`.
- Ne pas utiliser `.onnx`, `tfjs.zip`, `savedmodel.zip`.
- Ne pas inventer de modèle absent du catalogue.
- Ne pas implémenter `valence-discogs-effnet` si ce modèle n'existe pas dans le catalogue.
- Les modèles doivent être téléchargés uniquement via manifest.

## Modèles à vérifier

### Discogs-EffNet

Dossier :

```text
https://essentia.upf.edu/models/feature-extractors/discogs-effnet/
```

Fichiers :

```text
discogs-effnet-bs64-1.pb
discogs-effnet-bs64-1.json
```

### Moods / classifiers Discogs-EffNet

Dossiers :

```text
https://essentia.upf.edu/models/classification-heads/mood_aggressive/
https://essentia.upf.edu/models/classification-heads/mood_happy/
https://essentia.upf.edu/models/classification-heads/mood_party/
https://essentia.upf.edu/models/classification-heads/mood_relaxed/
https://essentia.upf.edu/models/classification-heads/mood_sad/
https://essentia.upf.edu/models/classification-heads/mood_acoustic/
https://essentia.upf.edu/models/classification-heads/mood_electronic/
https://essentia.upf.edu/models/classification-heads/voice_instrumental/
https://essentia.upf.edu/models/classification-heads/danceability/
https://essentia.upf.edu/models/classification-heads/approachability/
https://essentia.upf.edu/models/classification-heads/engagement/
```

Fichiers attendus :

```text
mood_aggressive-discogs-effnet-1.pb/json
mood_happy-discogs-effnet-1.pb/json
mood_party-discogs-effnet-1.pb/json
mood_relaxed-discogs-effnet-1.pb/json
mood_sad-discogs-effnet-1.pb/json
mood_acoustic-discogs-effnet-1.pb/json
mood_electronic-discogs-effnet-1.pb/json
voice_instrumental-discogs-effnet-1.pb/json
danceability-discogs-effnet-1.pb/json
approachability_regression-discogs-effnet-1.pb/json
engagement_regression-discogs-effnet-1.pb/json
```

### Genre Discogs519

Dossiers :

```text
https://essentia.upf.edu/models/feature-extractors/maest/
https://essentia.upf.edu/models/classification-heads/genre_discogs519/
```

Fichiers :

```text
discogs-maest-30s-pw-519l-2.pb/json
genre_discogs519-discogs-maest-30s-pw-519l-1.pb/json
```

### Arousal / valence optionnel

Dossiers :

```text
https://essentia.upf.edu/models/feature-extractors/musicnn/
https://essentia.upf.edu/models/classification-heads/deam/
https://essentia.upf.edu/models/classification-heads/muse/
```

Fichiers optionnels :

```text
msd-musicnn-1.pb/json
deam-msd-musicnn-2.pb/json
muse-msd-musicnn-2.pb/json
```

## Sortie attendue

- Manifest YAML complet.
- Test qui vérifie que chaque URL déclarée finit par `.pb` ou `.json`.
- Test qui vérifie que les profils ne contiennent que des clés déclarées.
- Test qui vérifie que `phase6-recommended` contient `genre_discogs519_maest_519l`.
- Test qui vérifie que `phase6-minimal` ne contient pas MAEST.
