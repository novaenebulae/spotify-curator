# 05 — Modèle de données SQLite — patch phase 6

Tags: #sqlite #database #phase-6 #audio-pipeline #tensorflow

## Objectif

Ajouter les éléments nécessaires au pipeline parallèle et aux features avancées.

## Tables existantes à conserver

- `jobs`
- `job_items`
- `worker_heartbeats`
- `job_events`
- `track_segments`
- `audio_analysis_jobs`
- `audio_features`
- `audio_feature_raw_payloads`
- `track_embeddings`

## Extension recommandée : analysis stage items

Deux options sont acceptables :

### Option A — étendre `job_items`

Ajouter au modèle logique `job_items` :

| Champ | Type | Notes |
|---|---|---|
| `stage_name` | text indexed | `segment_download`, `essentia_lowlevel`, `essentia_tensorflow_embeddings`, etc. |
| `depends_on_item_id` | FK nullable | dépendance directe simple |
| `consumer_group` | text nullable | groupe consommateur du segment |
| `model_name` | text nullable | modèle TensorFlow si applicable |
| `pipeline_version` | text nullable | version pipeline |
| `blocked_reason` | text nullable | si status `blocked` |

### Option B — créer `analysis_stage_items`

À privilégier si `job_items` est trop générique ou déjà fortement utilisé.

| Champ | Type | Notes |
|---|---|---|
| `id` | PK | |
| `job_id` | FK jobs indexed | |
| `track_id` | FK tracks indexed | |
| `segment_id` | FK track_segments nullable indexed | |
| `stage_name` | text indexed | |
| `status` | text indexed | |
| `priority` | int | |
| `attempt_count` | int | |
| `max_attempts` | int | |
| `locked_by` | text nullable | |
| `locked_at` | datetime nullable | |
| `next_retry_at` | datetime nullable | |
| `depends_on_stage` | text nullable | |
| `consumer_group` | text nullable | |
| `model_name` | text nullable | |
| `pipeline_version` | text | |
| `input_json` | text nullable | |
| `result_json` | text nullable | |
| `error_code` | text nullable | |
| `error_message` | text nullable | |
| `created_at` | datetime | |
| `started_at` | datetime nullable | |
| `finished_at` | datetime nullable | |

## Nouvelle table recommandée : model_registry_entries

| Champ | Type | Notes |
|---|---|---|
| `id` | PK | |
| `model_key` | text unique indexed | |
| `model_name` | text | |
| `task_type` | text | embedding/classifier/regression/genre |
| `expected_path` | text | chemin local non commité |
| `version` | text nullable | |
| `sha256` | text nullable | |
| `dimension` | int nullable | embeddings |
| `status` | text indexed | available/missing/invalid_hash/disabled |
| `metadata_json` | text nullable | labels, classes, scale |
| `last_checked_at` | datetime nullable | |
| `created_at` | datetime | |
| `updated_at` | datetime | |

## Extension `track_embeddings`

Ajouter si absents :

| Champ | Type | Notes |
|---|---|---|
| `aggregation_method` | text nullable | mean/centroid/weighted_mean |
| `segments_used` | int nullable | |
| `pipeline_version` | text nullable | |
| `status` | text indexed | success/partial/failed/skipped |
| `error_code` | text nullable | |

## Nouvelle table possible : track_advanced_features

Recommandée pour éviter d'étendre excessivement `audio_features`.

| Champ | Type | Notes |
|---|---|---|
| `id` | PK | |
| `track_id` | FK tracks indexed | |
| `feature_name` | text indexed | |
| `value_float` | float nullable | |
| `value_text` | text nullable | |
| `value_json` | text nullable | top-k genres, etc. |
| `confidence` | float nullable | |
| `source` | text indexed | essentia_tensorflow/derived/reccobeats |
| `model_name` | text nullable | |
| `model_version` | text nullable | |
| `model_hash` | text nullable | |
| `pipeline_version` | text nullable | |
| `aggregation_method` | text nullable | |
| `status` | text indexed | success/partial/missing/model_missing/failed |
| `created_at` | datetime | |
| `updated_at` | datetime | |

Contrainte recommandée :

```sql
UNIQUE(track_id, feature_name, source, model_name, pipeline_version)
```

## Contraintes critiques

- Les fichiers modèles restent dans `models/`, jamais en Git.
- Les chemins stockés doivent être relatifs au volume si possible.
- Aucun fichier audio permanent par défaut.
- Les embeddings peuvent être en JSON pour MVP, mais prévoir migration future vers fichier cache ou stockage compact si volumétrie trop élevée.
