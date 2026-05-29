# Phase 1 — Spotify Library Backup

Tags: #backlog #phase-1 #spotify-curator

## But

Importer et sauvegarder localement la bibliothèque Spotify.


## Definition of Done phase

- Les livrables de phase sont présents.
- Les tests minimum passent.
- Les commandes de validation sont documentées.
- La documentation est à jour.
- Aucun secret, cache, modèle lourd ou fichier audio n’est commité.
- Aucune régression sur les phases précédentes.


## 1.1 — Configuration Spotify

Statut : DONE (phase 1.5 — `GET /runtime/config`)

### Sous-tâches

- `.env.example` avec `SPOTIFY_CLIENT_ID`, `SPOTIFY_REDIRECT_URI`, `SPOTIFY_SCOPES`.
- Documentation Spotify Developer Dashboard.
- Settings non sensibles exposés via `/runtime/config`.
- Validation config absente.

### Critères d’acceptation

- Aucun secret commité.
- Redirect URI documenté.
- Scopes read-only en phase 1.

## 1.2 — OAuth PKCE

Statut : DONE

### Sous-tâches

- `/spotify/auth/start`.
- `/spotify/auth/callback`.
- `/spotify/auth/status`.
- `/spotify/auth/logout`.
- Génération verifier/challenge/state.
- Token storage local dev.

### Critères d’acceptation

- Login local fonctionne.
- Status retourne connecté.
- Logout supprime token local.
- Pas de client secret.

## 1.3 — SpotifyClient

Statut : DONE

### Sous-tâches

- Pagination.
- Retry/backoff.
- Rate limit `Retry-After`.
- Refresh token.
- Erreurs normalisées.
- Tests mocks.

## 1.4 — Import liked tracks

Statut : DONE (phase 1.5 — `is_current`, `market_status`, normalisation)

### Sous-tâches

- Fetch tous les saved tracks.
- Normaliser tracks/artists/albums.
- Stocker raw_json.
- Upserts idempotents.
- Job avec progression.

### Critères d’acceptation

- DB remplie.
- Import relançable.
- `is_current`/`last_seen_at` corrects.

## 1.5 — Import playlists

Statut : DONE

### Sous-tâches

- Fetch playlists.
- Fetch items paginés.
- Stocker position.
- Gérer tracks nulles/locales.
- Job avec progression.

## 1.6 — Snapshots

Statut : DONE

### Sous-tâches

- Snapshot liked.
- Snapshot playlists.
- Snapshot full.
- Metadata JSON.

## 1.7 — Diff snapshots

Statut : DONE

### Sous-tâches

- Ajouts.
- Suppressions.
- Disparus.
- Possibly relinked.
- API diff.

## 1.8 — Écran import

Statut : DONE

### Sous-tâches

- Connexion.
- Boutons import.
- Jobs.
- Snapshots.
- Diff.
- Erreurs.

## 1.9 — Exports

Statut : DONE

### Sous-tâches

- CSV liked.
- JSON liked.
- Playlists.
- Snapshot.
- Diff.

## Commandes de validation

À conserver dans la revue phase 1 réelle.
