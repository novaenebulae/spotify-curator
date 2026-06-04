# Prompt Cursor — Réalignement Phase 6 : modèles, vraie inférence, API/UI

Tu travailles sur Spotify Curator.

## Contexte

La phase 6 a divergé. Elle a été implémentée en grande partie comme un socle technique avec stubs TensorFlow déterministes. Cela n’est pas suffisant.

La phase 6 absorbe l’ancien périmètre “Analyse avancée” : embeddings, genre Discogs519, moods, voice/instrumental, acoustic/electronic, approachability, engagement. Elle doit donc permettre une vraie inférence Essentia TensorFlow lorsque les modèles sont présents.

Les stubs sont acceptables uniquement pour tests unitaires, jamais comme résultat de production.

## Décision de réalignement

Reclasser les tâches :

- 6.4 Worker TensorFlow : PARTIAL tant que l’inférence réelle n’est pas branchée.
- 6.5 Model registry : PARTIAL tant qu’il n’y a pas de manifest/downloader/verifier.
- 6.6 Embeddings + Genre Discogs519 : PARTIAL tant que les runners sont stub.
- 6.7 Classifiers avancés : PARTIAL tant que les runners sont stub.
- 6.8/6.9/6.10 : restent TODO.

Ajouter des tâches bloquantes :

- 6.8A — Gestion modèles, downloader et vérification.
- 6.8B — Inférence réelle Essentia TensorFlow.
- 6.8C — Smoke tests inférence réelle.

## Règles non négociables

- Aucun modèle lourd ne doit être commité.
- Aucun segment audio > 30 secondes.
- Aucun stub en runtime normal.
- `inference_mode="real"` uniquement si un modèle réel a été exécuté sur un WAV réel.
- Modèle absent → `model_missing`, pas de fake success.
- Modèle invalide → `model_invalid`.
- Les stubs ne sont autorisés que si `APP_ENV=test` et `ESSENTIA_TF_ALLOW_STUBS_IN_TESTS=true`.
- Le playlist engine doit continuer à consommer `TrackFeatureView`, jamais les payloads raw.

## Ordre d’implémentation obligatoire

1. Mettre à jour la documentation/backlog avec les fichiers fournis :
  - `backlog/phase-6.realigned.models-updated.md`
  - `docs/19-essentia-tensorflow-model-management.md`
  - patches API/config/tests/pipeline.
2. Auditer le code actuel :
  - `embeddings_runner.py`
  - `genre_runner.py`
  - `classifier_runner.py`
  - `EssentiaTensorflowWorker`
  - `ModelRegistry`
  - API `audio.py`, `models.py`, `features.py`
  - UI `/features`, `TrackFeaturesDrawer`
3. Implémenter 6.8A.
4. Implémenter 6.8B.
5. Implémenter 6.8C.
6. Reprendre ensuite 6.8/6.9/6.10.

## Critère de fin

La phase 6 n’est pas terminée tant que :

- `POST /api/v1/audio/analysis/advanced` ne lance pas le pipeline ;
- les modèles peuvent être téléchargés/vérifiés ;
- les runners réels existent ;
- un smoke WAV court peut produire une vraie inférence si les modèles sont présents ;
- l’UI montre les modèles, les statuts et les features avancées ;
- aucun stub ne peut écrire de feature `success` en production.

Commence par produire un plan d’audit court, puis applique les changements par petits commits logiques.