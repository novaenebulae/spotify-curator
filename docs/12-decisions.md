# 12 — Décisions techniques

Tags: #decisions #adr #architecture

## Décisions validées

### ADR-001 — Application desktop locale

Décision : Tauri/Svelte pour l’interface desktop.

Raison : expérience locale, accès facile au core local, distribution Windows possible.

### ADR-002 — Core Python Dockerisé

Décision : logique métier dans un core FastAPI exécuté sous Docker.

Raison : reproductibilité, dépendances audio lourdes, isolation des outils Python.

### ADR-003 — SQLite

Décision : SQLite comme base locale.

Raison : projet mono-utilisateur, simplicité, portabilité, backup facile.

Rejeté : PostgreSQL pour MVP.

### ADR-004 — Pas de Django

Décision : FastAPI léger au lieu de Django.

Raison : API locale, pas de back-office web, services audio/jobs personnalisés.

### ADR-005 — Pas de Celery/RabbitMQ

Décision : jobs persistés SQLite et runner local.

Raison : réduire complexité. Architecture compatible avec worker séparé si besoin.

### ADR-006 — OAuth PKCE

Décision : Spotify OAuth Authorization Code with PKCE.

Raison : application desktop sans client secret.

### ADR-007 — Scopes minimaux

Décision : lecture seule en phase 1/2 ; write seulement à partir des phases de sync.

Raison : sécurité et principe de moindre privilège.

### ADR-008 — Segments audio temporaires

Décision : pas de téléchargement complet standard ; segments `<=30s`.

Raison : limiter stockage, temps d’analyse et risques.

### ADR-009 — Features multi-source

Décision : stocker source, version, confiance, raw payload.

Raison : ReccoBeats, Essentia et modèles peuvent diverger.

### ADR-010 — Dry-run obligatoire

Décision : toute modification Spotify doit être prévisualisée.

Raison : éviter pertes de likes/playlists.

### ADR-011 — Modèles externes non commités

Décision : `models/` ignoré par Git.

Raison : taille, licences, reproductibilité via scripts.

### ADR-012 — Documentation phase par phase

Décision : backlogs et docs mis à jour pendant le développement.

Raison : Cursor doit conserver un contexte fiable.

## Décisions ouvertes

### ODR-001 — SQLAlchemy vs SQLModel

Choisir selon l’existant phase 0/1. Ne pas changer sans raison forte.

### ODR-002 — Stockage token chiffré

À traiter après MVP ou en phase 9.

Options :

- OS keychain via Tauri ;
- keyring Python ;
- chiffrement local avec clé utilisateur.

### ODR-003 — Bibliothèque carte UMAP UI

À choisir en phase 6.

Options :

- Canvas custom ;
- D3 ;
- Plotly ;
- PixiJS si performance nécessaire.

### ODR-004 — Modèles Essentia TF exacts

À choisir en phase 7 selon disponibilité, poids et compatibilité Docker.
