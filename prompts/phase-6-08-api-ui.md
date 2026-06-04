# Prompt Cursor — Phase 6.8 — API et UI features avancées

> **État juin 2026** : **API backend** (6.9a) et **UI** (6.9b) livrées. Observabilité jobs : [`phase-6-09-cleanup-observability.md`](phase-6-09-cleanup-observability.md) (6.9c).

Tu travailles sur le projet Spotify Curator.

Contexte actuel :
- Phases 0 à 5 implémentées.
- Phase 5 terminée : playlist generator v1, règles, filtres, scoring, diversité, preview persistée, dry-run sync.
- Phase 4 existante : audio-downloader, preview-resolver-worker, essentia-lowlevel-worker, Deezer previews, segments YouTube/Deezer, Essentia low-level, job_items, worker_heartbeats.
- Nouvelle phase 6 : remplacer le flux séquentiel `download all → analyze all` par un pipeline streaming/parallèle et ajouter Essentia TensorFlow + features avancées.
- Ne jamais commiter secrets, DB, cache, audio, modèles lourds.
- Les segments audio restent temporaires et <= 30s.
- Les workers Docker doivent rester persistants.
- Le playlist engine ne doit jamais lire les payloads bruts : il consomme FeatureRegistry + FeatureResolver + TrackFeatureView.

Contraintes générales :
- Commencer par auditer le code existant avant de modifier.
- Ne pas casser les tests des phases précédentes.
- Préférer des changements incrémentaux, testés, documentés.
- Ajouter ou mettre à jour les tests à chaque étape.
- Mettre à jour la documentation impactée.


Objectif :
Exposer et afficher les modèles, la coverage avancée, les jobs par stage et les nouvelles features.

Tâches API :
1. Ajouter `POST /api/v1/audio/analysis/advanced`.
2. Ajouter `GET /api/v1/models/status`.
3. Ajouter `GET /api/v1/features/advanced/coverage`.
4. Étendre `GET /api/v1/features/coverage`.
5. Étendre `GET /api/v1/features/tracks/{track_id}` avec source `essentia_tensorflow`.
6. Étendre `GET /api/v1/jobs/{job_id}` ou `/items` pour afficher les compteurs par stage.

Tâches UI :
1. Mettre à jour écran `/features`.
2. Afficher :
   - coverage ReccoBeats ;
   - coverage low-level ;
   - coverage TensorFlow ;
   - modèles disponibles/manquants ;
   - jobs actifs ;
   - failures par modèle/stage.
3. Mettre à jour `TrackFeaturesDrawer` :
   - onglet Advanced ;
   - moods ;
   - genre Discogs top-k ;
   - embedding status ;
   - source/confidence/model.
4. Gérer loading/error/empty/offline.
5. Garder payload raw replié.

Critères :
- L'utilisateur comprend pourquoi une feature avancée est absente.
- Aucun modèle/audio n'est exposé.
- UI build OK.

Validation :
```bash
cd core
uv run pytest tests/test_advanced_features_api.py tests/test_models_status_api.py -q
cd ../app/frontend
npm run check
npm run build
```
