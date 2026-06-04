# Prompt Cursor — Phase 6.9 — Cleanup, observabilité et robustesse


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
Rendre le pipeline sûr pour une bibliothèque complète : cleanup fiable, retry, partial success, annulation et observabilité.

Tâches :
1. Implémenter cleanup multi-consommateurs :
   - ne pas supprimer segment si low-level ou TensorFlow pending/running ;
   - supprimer après success/skipped/failed_terminal ;
   - respecter `AUDIO_KEEP_SEGMENTS_AFTER_ANALYSIS`.
2. Ajouter événements job/stage utiles :
   - stage_created ;
   - segment_ready ;
   - stage_started ;
   - model_missing ;
   - stage_failed ;
   - cleanup_done.
3. Améliorer `GET /workers` si nécessaire :
   - worker type ;
   - current stage ;
   - heartbeat ;
   - metadata.
4. Gérer annulation :
   - job parent cancelled ;
   - pending stages cancelled ;
   - running stages finissent ou échouent proprement ;
   - cleanup si possible.
5. Tests :
   - cleanup ;
   - cancellation ;
   - lock expired ;
   - partial success ;
   - worker heartbeat.

Critères :
- Pas de segments orphelins en flux normal.
- Erreurs lisibles.
- Retry contrôlé.
- Aucun secret/log sensible.

Validation :
```bash
cd core
uv run pytest tests/test_audio_cleanup.py tests/test_jobs_cancel*.py tests/test_worker_heartbeats.py tests/test_analysis_pipeline_observability.py -q
```
