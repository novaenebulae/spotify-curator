# 15 — Règles Cursor pour implémentation

Tags: #cursor #rules #implementation

## Règles générales

Cursor doit :

- lire le contexte avant chaque phase ;
- ne pas coder avant validation du plan ;
- respecter le backlog de phase ;
- ne pas anticiper les phases futures sauf préparation minimale ;
- ajouter tests et docs ;
- garder les patches petits.

## Règles backend

- Routes FastAPI fines.
- Services métier séparés.
- Repositories pour requêtes DB complexes.
- Pydantic pour request/response.
- Erreurs uniformes.
- Tests mockés pour API externes.
- Jobs pour tâches longues.

## Règles DB

- Migrations non destructives.
- Ne pas supprimer données existantes.
- Ajouter index si endpoint filtrable.
- Raw payloads conservés.
- JSON documenté.
- DB test séparée.

## Règles frontend

- API client centralisé.
- Types TypeScript pour responses.
- États loading/empty/error.
- Pas de token dans UI.
- Confirmation pour actions dangereuses.
- Polling jobs raisonnable.
- Pas de logique métier lourde dans composants.

## Règles Docker

- Core bind `127.0.0.1:8765`.
- Volumes data/cache/models/logs/exports.
- Services audio séparables par profiles.
- Commandes documentées.
- Images lourdes non requises avant phase concernée.

## Règles audio

- Jamais de morceau complet par défaut.
- Segments `<=30s`.
- Cleanup obligatoire.
- Hash/metadata plutôt que fichier permanent.
- Tests limites.

## Règles Spotify

- Scopes minimaux.
- PKCE uniquement.
- Pas de client secret.
- Dry-run avant write.
- Confirmation UI avant write.
- Rate limit respecté.
- Tokens redacted.

## Règles documentation

Chaque tâche qui modifie une API doit mettre à jour :

- `docs/06-api-contract.md` ;
- tests associés ;
- backlog phase.

Chaque tâche UI doit mettre à jour :

- `docs/09-ui-specification.md` si comportement nouveau ;
- tests UI si disponibles.

Chaque tâche DB doit mettre à jour :

- `docs/05-domain-model.md` ;
- migration ;
- tests migration/repository.

## Anti-patterns à refuser

- Ajouter PostgreSQL.
- Ajouter Django.
- Ajouter Celery/RabbitMQ.
- Exécuter Tauri dans Docker.
- Stocker tokens dans localStorage.
- Télécharger audio complet.
- Modifier Spotify sans dry-run.
- Coder phases multiples dans un seul patch.
- Ignorer les tests pour aller plus vite.
