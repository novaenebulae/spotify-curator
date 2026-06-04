# Prompt Cursor — Phase 6.8C — Smoke tests inférence réelle

## Objectif

Prouver que l’inférence réelle fonctionne avec un WAV court lorsque les modèles sont présents.

## À implémenter

1. Script :

```text
scripts/smoke_essentia_tensorflow_real.py
```

2. Le script doit :

- vérifier `/models/status` ou `ModelManager` ;
- générer ou utiliser un WAV court de test ;
- lancer au moins un runner réel du profil minimal ;
- vérifier `inference_mode="real"` ;
- vérifier une sortie non vide ;
- persister un résultat de test ou exécuter en dry-run selon option ;
- retourner un message clair si modèle absent.

3. Ajouter options :

```bash
--require-models
--allow-missing
--track-id 1
--wav-path path/to/test.wav
```

4. Ajouter documentation validation.

## Validation

```bash
docker compose --profile audio --profile advanced-analysis up -d --build
docker compose exec core-api uv run python scripts/download_essentia_models.py --profile phase6-minimal --accept-license
docker compose exec core-api uv run python scripts/download_essentia_models.py --verify-only
docker compose exec core-api uv run python scripts/smoke_essentia_tensorflow_real.py --require-models
```

## Critères

- En absence de modèles : sortie `model_missing`, pas crash.
- Avec modèles : vraie inférence, sortie non vide.
- Aucun stub en production.
