# Phase 3 — ReccoBeats enrichment

Tags: #backlog #phase-3 #features #reccobeats

## But

Ajouter les features audio simples via ReccoBeats et préparer le modèle multi-source.


## Definition of Done phase

- Les livrables de phase sont présents.
- Les tests minimum passent.
- Les commandes de validation sont documentées.
- La documentation est à jour.
- Aucun secret, cache, modèle lourd ou fichier audio n’est commité.
- Aucune régression sur les phases précédentes.


## 3.1 — Tables features

Statut : TODO

### Sous-tâches

- Créer `feature_sources`.
- Créer `audio_features`.
- Créer `audio_feature_raw_payloads`.
- Ajouter index track/source/is_active.
- Ajouter source `reccobeats`.

### Critères d’acceptation

- DB prête pour features multi-source.
- Migration non destructive.

## 3.2 — Client ReccoBeats

Statut : TODO

### Sous-tâches

- Client HTTP isolé.
- Timeouts.
- Retry.
- Rate limit.
- Erreurs normalisées.
- Tests mocks.

### Critères d’acceptation

- Aucun appel réseau réel dans tests.
- Rate limit géré.

## 3.3 — Normalisation

Statut : TODO

### Sous-tâches

- Mapper les champs ReccoBeats.
- Stocker raw payload.
- Calculer confidence.
- Upsert idempotent.
- Marquer `source_version`.

### Critères d’acceptation

- Features stockées et relançables.

## 3.4 — Jobs enrichissement

Statut : TODO

### Sous-tâches

- Endpoint `/features/reccobeats/enrich`.
- Batch configurable.
- Progression.
- Retry failed.
- Only missing.
- Force refresh.

### Critères d’acceptation

- Job relançable.
- UI peut poller statut.

## 3.5 — Coverage

Statut : TODO

### Sous-tâches

- Endpoint `/features/coverage`.
- Coverage globale.
- Coverage par field.
- Tracks failed/missing.

### Critères d’acceptation

- Endpoint exploitable UI.

## 3.6 — UI enrichment

Statut : TODO

### Sous-tâches

- Écran Enrichissement.
- Bouton lancer ReccoBeats.
- Progression job.
- Coverage cards.
- Liste failed.
- Relance failed.

### Critères d’acceptation

- UI claire et non bloquante.
