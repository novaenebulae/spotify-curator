# Prompt Cursor — Phase 6.2 — Handoff downloader → analyzers


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
Modifier le pipeline pour qu'un segment téléchargé déclenche immédiatement les stages d'analyse, sans attendre la fin complète du téléchargement du job.

Tâches :
1. Ajouter configuration :
   - `ANALYSIS_PIPELINE_MODE=streaming|legacy`
   - défaut `streaming`.
2. Adapter `audio-downloader` :
   - après création d'un `track_segment` prêt, créer/débloquer les stages `essentia_lowlevel` et `essentia_tensorflow_*` ;
   - ne pas supprimer le segment à ce stade ;
   - écrire un event/job log léger.
3. Ajouter logique de consumers :
   - chaque segment connaît les consommateurs requis ;
   - cleanup impossible tant que consumers pending/running.
4. Conserver compatibilité avec endpoints phase 4 existants.
5. Tests :
   - un segment prêt crée les stages d'analyse ;
   - le premier segment peut être analysé avant fin du job de téléchargement ;
   - mode legacy ne casse pas ;
   - cleanup non autorisé si consumer pending.

Critères :
- Aucun changement destructif sur stratégie Deezer/Youtube.
- Aucun segment >30s.
- Tests phase 4 audio existants passent.

Validation :
```bash
cd core
uv run pytest tests/test_hybrid_segment_strategy.py tests/test_analysis_pipeline_handoff.py tests/test_audio_cleanup.py -q
```
