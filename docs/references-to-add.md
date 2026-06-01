# Références — doc 16 (jobs & workers)

Tags: #documentation #jobs #workers #index

Source canonique : [16-job-execution-model-and-worker-parallelism.md](./16-job-execution-model-and-worker-parallelism.md)

Ce fichier recense les renvois vers la doc 16. Les cases indiquent l'état d'intégration dans le dépôt (mise à jour 2026-05).

## Liens depuis la doc existante

- [x] [`docs/01-architecture.md`](./01-architecture.md) — exécution jobs MVP in-process vs cible workers ; lien doc 16
- [x] [`docs/05-domain-model.md`](./05-domain-model.md) — table `jobs` : statuts DB/API ; tables cibles `job_items` / heartbeats / events
- [x] [`docs/06-api-contract.md`](./06-api-contract.md) — section Jobs : implémenté vs cible ; lien doc 16 §15
- [x] [`docs/07-audio-analysis-pipeline.md`](./07-audio-analysis-pipeline.md) — ReccoBeats actuel vs batch `audio-features` ; lien doc 16 §7
- [x] [`docs/10-testing-strategy.md`](./10-testing-strategy.md) — tests jobs/workers / batch ReccoBeats (phase 3.5) ; lien doc 16 §20
- [x] [`docs/12-decisions.md`](./12-decisions.md) — ADR-005b modèle jobs hybride → doc 16
- [x] [`docs/13-error-handling-and-observability.md`](./13-error-handling-and-observability.md) — statuts jobs API/DB ; `job_events` cible
- [x] [`docs/14-configuration.md`](./14-configuration.md) — variables actuelles vs cibles doc 16 §14
- [x] [`docs/04-backlog-by-phase.md`](./04-backlog-by-phase.md) — ligne phase 3.5 ReccoBeats batch
- [x] [`MANIFEST.md`](../MANIFEST.md) — entrées docs/16 et ce fichier
- [x] [`backlog/phase-3.md`](../backlog/phase-3.md) — limites + section phase 3.5 batch
- [x] [`backlog/phase-4.md`](../backlog/phase-4.md) — workers Essentia → doc 16 §9–11
- [x] [`AGENTS.md`](../AGENTS.md) — paragraphe exécution tâches longues → doc 16

## Phase 3.5 ReccoBeats (documentation avant code)

- [x] Endpoint batch `GET /v1/audio-features?ids=` (max 40) dans doc 16 §7.2.1 et [`07-audio-analysis-pipeline.md`](./07-audio-analysis-pipeline.md)
- [x] Section phase 3.5 dans [`backlog/phase-3.md`](../backlog/phase-3.md) et doc 16 §21.2
- [x] Implémentation code client batch + tests mock (phase 3.5 livrée)

## Documents complétés par doc 16 (liste « Ce document complète »)

La doc 16 référence déjà : `01`, `05`, `06`, `07`, `10`, `13`, `14`, backlogs phase 3/4/6/7/9.
