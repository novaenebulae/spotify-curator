# 06 — Contrats API locale — patch phase 6

Tags: #api #phase-6 #advanced-analysis #models #features

## Nouveaux endpoints phase 6

### `POST /api/v1/audio/analysis/advanced`

Crée un job `audio_analysis_pipeline`.

Body :

```json
{
  "track_ids": [1, 2, 3],
  "filter": {},
  "only_missing": true,
  "retry_failed": false,
  "force_refresh": false,
  "limit": null,
  "strategy": "hybrid_deezer_youtube_representative",
  "analysis_mode": "fast",
  "include_lowlevel": true,
  "include_tensorflow": true,
  "models": ["all"],
  "pipeline_mode": "streaming"
}
```

Réponse :

```json
{
  "job_id": "job_...",
  "status": "pending"
}
```

### `GET /api/v1/models/status`

Réponse :

```json
{
  "models": [
    {
      "model_key": "genre_discogs_519",
      "model_name": "genre_discogs519-discogs-maest-30s-pw-519l",
      "task_type": "genre",
      "status": "available",
      "version": "1",
      "sha256": "...",
      "dimension": null,
      "last_checked_at": "2026-06-03T10:00:00Z"
    }
  ],
  "summary": {
    "available": 4,
    "missing": 8,
    "invalid_hash": 0,
    "disabled": 0
  }
}
```

### `GET /api/v1/features/advanced/coverage`

Réponse :

```json
{
  "summary": {
    "track_count": 5000,
    "with_any_advanced_features": 1200,
    "with_embeddings": 900,
    "with_genre_discogs_519": 850,
    "with_moods": 800,
    "coverage_percent": 24.0
  },
  "fields": [
    {
      "field": "mood_happy_score",
      "available_count": 800,
      "coverage_percent": 16.0
    }
  ],
  "models": {
    "available": [],
    "missing": []
  },
  "recent_failures": []
}
```

### Extension `GET /api/v1/features/tracks/{track_id}`

Ajouter dans chaque source :

```json
{
  "source_name": "essentia_tensorflow",
  "display_name": "Essentia TensorFlow",
  "is_active": true,
  "status": "success",
  "fields": {
    "mood_happy_score": 0.12,
    "mood_aggressive_score": 0.73,
    "electronic_profile_score": 0.91,
    "instrumental_focus_score": 0.84,
    "approachability": 0.42,
    "engagement": 0.77,
    "genre_discogs_519_top_label": "Techno",
    "genre_discogs_519_top_score": 0.34
  },
  "extended": {
    "genre_discogs_519_top_k": [
      {"label": "Techno", "score": 0.34},
      {"label": "Industrial", "score": 0.21}
    ],
    "embedding": {
      "available": true,
      "dimension": 1280,
      "model_name": "discogs_effnet"
    },
    "models_used": []
  }
}
```

## Jobs

`GET /api/v1/jobs/{job_id}` doit idéalement exposer les compteurs par stage :

```json
{
  "items": {
    "segment_download": {"pending": 10, "running": 2, "success": 50, "failed": 1},
    "essentia_lowlevel": {"pending": 20, "running": 2, "success": 38, "failed": 0},
    "essentia_tensorflow": {"pending": 30, "running": 1, "success": 20, "failed": 0}
  }
}
```

## Erreurs phase 6

| Code | Usage |
|---|---|
| `MODEL_MISSING` | Modèle absent |
| `MODEL_INVALID_HASH` | Hash modèle non conforme |
| `TENSORFLOW_INFERENCE_FAILED` | Inférence échouée |
| `EMBEDDING_SHAPE_INVALID` | Dimension inattendue |
| `ANALYSIS_STAGE_BLOCKED` | Dépendance non terminée |
| `SEGMENT_CONSUMER_PENDING` | Cleanup impossible car consommateur pending |
| `ADVANCED_ANALYSIS_DISABLED` | Fonction désactivée par configuration |
