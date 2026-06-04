# Prompt Cursor — Phase 6.10 — Validation finale et documentation


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
Finaliser la phase 6 avec tests, documentation et revue de phase.

Tâches :
1. Mettre à jour documentation :
   - `docs/04-backlog-by-phase.md`
   - `docs/05-domain-model.md`
   - `docs/06-api-contract.md`
   - `docs/07-audio-analysis-pipeline.md`
   - `docs/10-testing-strategy.md`
   - `docs/14-configuration.md`
   - `docs/16-job-execution-model-and-worker-parallelism.md`
   - `docs/18-feature-consumption-contract.md`
   - `backlog/phase-6.md`
   - `backlog/phase-7.md`
2. Ajouter `docs/phase-6-review.md` :
   - livrables réalisés ;
   - tests exécutés ;
   - limites ;
   - dette technique ;
   - risques phase 7 ;
   - commandes de validation.
3. Lancer validation complète.
4. Corriger uniquement les régressions liées à la phase 6.
5. Ne pas démarrer phase 7.

Commandes :
```bash
cd core
uv run alembic upgrade head
uv run pytest -q
uv run ruff check .
uv run ruff format --check .

cd ../app/frontend
npm run check
npm run build

docker compose --profile audio --profile advanced-analysis up -d --build
curl http://127.0.0.1:8765/api/v1/health
curl http://127.0.0.1:8765/api/v1/workers
curl http://127.0.0.1:8765/api/v1/models/status
curl http://127.0.0.1:8765/api/v1/features/advanced/coverage
```

Critères :
- Phase 6 documentée.
- Tests OK ou échecs documentés avec justification.
- Pas de modèles/audio/cache commité.
- Phase 7 prête à démarrer.
