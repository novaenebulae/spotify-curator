# Prompt Cursor — Phase 6.0 — Initialisation agent et audit


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
Initialiser la phase 6 et produire un audit technique court avant toute implémentation.

Tâches :
1. Lire la documentation projet pertinente :
   - `docs/04-backlog-by-phase.md`
   - `docs/07-audio-analysis-pipeline.md`
   - `docs/16-job-execution-model-and-worker-parallelism.md`
   - `docs/17-audio-preview-and-segment-strategy.md`
   - `docs/18-feature-consumption-contract.md`
   - `backlog/phase-6.md`
2. Auditer le code existant :
   - endpoints audio/features/jobs/workers ;
   - workers `audio-downloader`, `essentia-lowlevel-worker`, `preview-resolver-worker` ;
   - tables/migrations jobs, job_items, track_segments, audio_features, raw payloads ;
   - FeatureRegistry/FeatureResolver/TrackFeatureView ;
   - tests phase 4 et phase 5.
3. Produire `docs/phase-6-audit.md` avec :
   - état réel du dépôt ;
   - fichiers clés ;
   - gaps vs phase 6 ;
   - risques ;
   - ordre d'implémentation proposé ;
   - commandes de validation.
4. Ne pas implémenter encore le pipeline.

Critères :
- Aucun gros refactor.
- Audit factuel basé sur le code.
- Documentation créée.
- Tests existants non modifiés sauf correction triviale si nécessaire.

Validation :
```bash
cd core
uv run pytest -q
cd ../app/frontend
npm run check
npm run build
```
