# 10 — Stratégie de tests — patch phase 6

Tags: #tests #phase-6 #pipeline #tensorflow #workers

## Tests backend phase 6

### Pipeline stages

- création `audio_analysis_pipeline`;
- création stages par track/segment;
- réservation atomique stage;
- stage bloqué si dépendance absente;
- handoff `segment_download` → `essentia_lowlevel`;
- handoff `segment_download` → `essentia_tensorflow_embeddings`;
- premier segment analysé avant fin du téléchargement global;
- retry stage;
- partial success;
- annulation job.

### Cleanup

- segment non supprimé si TensorFlow pending;
- segment supprimé si low-level + TensorFlow terminés;
- cleanup idempotent si fichier déjà absent;
- `AUDIO_KEEP_SEGMENTS_AFTER_ANALYSIS=true` respecté.

### Model registry

- modèle disponible;
- modèle manquant;
- hash invalide;
- endpoint `/models/status`;
- pas de dépendance aux vrais modèles lourds.

### TensorFlow worker mock

- worker démarre;
- heartbeat;
- réserve un stage;
- retourne embedding mock;
- retourne classifier mock;
- échec inférence;
- modèle manquant → stage skipped/model_missing.

### Embeddings

- dimension correcte;
- dimension incorrecte;
- agrégation multi-segments;
- persistance `track_embeddings`;
- source/model/hash/version.

### Advanced features

- mapping mood binaire vers score;
- mapping acoustic/electronic;
- mapping voice/instrumental;
- mapping approachability/engagement;
- normalisation valence TF;
- calcul `energy_proxy`;
- fallback ReccoBeats → local;
- `FeatureResolver` source priority.

### API

- `POST /audio/analysis/advanced`;
- `GET /models/status`;
- `GET /features/advanced/coverage`;
- extension `/features/tracks/{track_id}`;
- jobs progress par stage.

## Tests frontend

- `/features` affiche modèles manquants;
- `/features` affiche coverage avancée;
- `TrackFeaturesDrawer` affiche onglet Advanced;
- states loading/error/empty;
- raw payloads repliés.

## Smoke Docker

```bash
docker compose --profile audio --profile advanced-analysis up -d --build
curl http://127.0.0.1:8765/api/v1/workers
curl http://127.0.0.1:8765/api/v1/models/status
```

## Non-régression

Relancer impérativement :

- tests phase 4 audio/previews/low-level;
- tests phase 5 playlist engine;
- build frontend.
