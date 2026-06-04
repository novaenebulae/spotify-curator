# Phase 9 — Packaging, maintenance et stabilisation

Tags: #backlog #phase-9 #packaging #windows #maintenance #backup

## But

Stabiliser l'application desktop locale, documenter l'installation, ajouter backup/restore et finaliser la maintenance utilisateur.

## Definition of Done phase

- Build Windows documenté.
- Guide d'installation utilisateur.
- Docker Compose/profils documentés.
- Backup/restore SQLite fonctionnel.
- Nettoyage cache/audio/modèles/logs.
- Rapport système redacted.
- Tests finaux.
- Aucun secret ni donnée personnelle n'est commité.

## 9.1 — Packaging Windows

Statut : TODO

### Sous-tâches

- Build Tauri.
- Vérifier lancement core/API.
- Vérifier dépendances Docker Desktop.
- Documenter limitations Windows/WSL2.

## 9.2 — Docker guide

Statut : TODO

### Sous-tâches

- Profil minimal.
- Profil audio.
- Profil advanced-analysis.
- Workers scaling.
- Volumes.
- Migrations.
- Troubleshooting.

## 9.3 — Backup / restore

Statut : TODO

### Sous-tâches

- Backup SQLite.
- Backup settings non sensibles.
- Restore validé.
- Warnings si version schéma incompatible.
- Dry-run restore si possible.

## 9.4 — Cache cleanup

Statut : TODO

### Sous-tâches

- Audio segments.
- JSON cache.
- Failed segments debug.
- Models status.
- Logs rotation.
- UI maintenance.

## 9.5 — System report

Statut : TODO

### Sous-tâches

- Core version.
- DB revision.
- Docker services.
- Workers heartbeat.
- Jobs récents.
- Models status.
- Cache size.
- Redaction secrets/paths sensibles.

## Critères phase

- L'application peut être installée et diagnostiquée proprement.
- Les données utilisateur peuvent être sauvegardées/restaurées.
- Le projet est documenté pour une utilisation locale stable.
