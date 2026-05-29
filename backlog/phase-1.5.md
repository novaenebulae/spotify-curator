# Phase 1.5 — Consolidation phases 0/1

Tags: #backlog #phase-1.5 #consolidation

## But

Aligner le code des phases 0/1 avec la documentation enrichie avant la phase 2.


## Definition of Done phase

- Alembic opérationnel avec migrations non destructives.
- Schéma phases 0/1 aligné (champs import, jobs, runtime, erreurs API).
- Tests backend passent (24+).
- Documentation et backlog à jour.
- Aucune fonctionnalité phase 2+ codée.


## 1.5.1 — Alembic

Statut : DONE

- Migration unique `0001_initial` (schéma consolidé)
- `init_db()` → `alembic upgrade head`
- Réinitialisation locale : supprimer `data/spotify_curator.sqlite` puis redémarrer Docker

## 1.5.2 — Schéma DB

Statut : DONE

- `docker_runtime_checks`, `oauth_pkce_states`, `settings` (structure doc)
- Jobs : `attempt_count`, `max_attempts`, `next_retry_at`
- Liked / playlist tracks : `is_current`, timestamps, `null_reason`, etc.
- Normalisation : `normalized_title`, `normalized_name`

## 1.5.3 — Runtime API

Statut : DONE

- `GET /runtime/config`
- `GET /runtime/docker/checks`
- `POST /runtime/docker/checks/run` (job async)
- `GET /diagnostics` conservé (alias enrichi)

## 1.5.4 — Erreurs API uniformes

Statut : DONE

- Handler `{ error: { code, message, details, retryable } }`
- Frontend : fallback `detail` legacy

## 1.5.5 — OAuth

Statut : DONE

- PKCE state en SQLite (TTL)
- `user_id` réel via `GET /me` après callback
- Tokens SQLite = dev local (documenté) — keychain : DEFERRED phase 9

## 1.5.6 — Import enrichi

Statut : DONE

- `is_current`, `market_status`, normalisation, playlist upsert

## 1.5.7 — Tests

Statut : DONE

- migrations, runtime, erreurs, import enrichi, oauth state DB

## Dette technique volontaire (hors 1.5)

- PK entiers (`tracks.id`) vs UUID doc — cible future
- `tracks.name` vs `canonical_title` — mapping documenté
- Tables snapshots spécialisées vs `snapshot_tracks` générique
- `GET /jobs` liste, `POST /jobs/{id}/cancel` — phase 2+
- `POST /spotify/import/full-library` — optionnel
