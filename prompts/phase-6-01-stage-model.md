# Prompt Cursor — Phase 6.1 — Modèle de stages pipeline


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
Ajouter le modèle de stages permettant d'orchestrer téléchargement, low-level, TensorFlow, agrégation et cleanup.

Tâches :
1. Partir de l'audit `docs/phase-6-audit.md`.
2. **Étendre `job_items`** (décision retenue — voir `docs/phase-6-audit.md` §5) :
   - `stage_name`, `depends_on_item_id`, `consumer_group`, `model_name`, `pipeline_version`, `blocked_reason` ;
   - utiliser `segment_id` pour les stages liés à un segment ;
   - ne pas créer `analysis_stage_items`.
3. Ajouter migration Alembic.
4. Créer les constantes de stages :
   - `segment_download`
   - `essentia_lowlevel`
   - `essentia_tensorflow_embeddings`
   - `essentia_tensorflow_classifiers`
   - `feature_aggregation`
   - `audio_cleanup`
5. Créer `AnalysisPipelineOrchestrator` :
   - création job parent ;
   - création stages ;
   - calcul dépendances ;
   - statuts `pending/running/success/failed/skipped/blocked/cancelled`.
6. Ajouter tests :
   - création stages ;
   - dépendances ;
   - stage blocked ;
   - retry ;
   - progress global.

Critères :
- Pas de traitement audio réel dans cette étape.
- Migrations réversibles.
- Tests backend ciblés.

Validation :
```bash
cd core
uv run alembic upgrade head
uv run pytest tests/test_analysis_pipeline_stages.py tests/test_migrations.py -q
```
