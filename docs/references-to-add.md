# Références — doc 16 (jobs & workers)

Tags: #documentation #jobs #workers #index

Source canonique : [16-job-execution-model-and-worker-parallelism.md](./16-job-execution-model-and-worker-parallelism.md)

Ce fichier recense les renvois vers la doc 16. Les cases indiquent l'état d'intégration dans le dépôt (mise à jour 2026-06).

## Liens depuis la doc existante

- [x] [`docs/01-architecture.md`](./01-architecture.md) — exécution jobs in-process + workers profil `audio`
- [x] [`docs/05-domain-model.md`](./05-domain-model.md) — `jobs`, `job_items`, `worker_heartbeats`, `job_events` (0006)
- [x] [`docs/06-api-contract.md`](./06-api-contract.md) — Jobs / workers / previews implémentés
- [x] [`docs/07-audio-analysis-pipeline.md`](./07-audio-analysis-pipeline.md) — workers + agrégation résultats
- [x] [`docs/10-testing-strategy.md`](./10-testing-strategy.md) — tests job_items, previews, insights
- [x] [`docs/12-decisions.md`](./12-decisions.md) — ADR-005b modèle jobs hybride
- [x] [`docs/13-error-handling-and-observability.md`](./13-error-handling-and-observability.md) — statuts jobs ; `partial` en DB
- [x] [`docs/14-configuration.md`](./14-configuration.md) — variables jobs/workers/audio
- [x] [`docs/17-audio-preview-and-segment-strategy.md`](./17-audio-preview-and-segment-strategy.md) — jobs preview/download/essentia
- [x] [`docs/04-backlog-by-phase.md`](./04-backlog-by-phase.md) — phase 3.5 / 4
- [x] [`MANIFEST.md`](../MANIFEST.md) — docs 16 et 17
- [x] [`backlog/phase-3.md`](../backlog/phase-3.md) — limites ReccoBeats
- [x] [`backlog/phase-4.md`](../backlog/phase-4.md) — workers + UI
- [x] [`AGENTS.md`](../AGENTS.md) — paragraphe exécution tâches longues

## Dette documentée (cible, pas encore livré)

- [ ] `GET /jobs/{id}/events` HTTP
- [ ] `partial_success` mappé uniformément en API (DB `partial` existe pour jobs items)
- [ ] `RECCOBEATS_CONCURRENCY` / chunks HTTP parallèles
- [ ] Service `job-worker` centralisé

## Phase 3.5 ReccoBeats

- [x] Batch `GET /v1/audio-features?ids=` — livré
- [x] Implémentation + tests mock
