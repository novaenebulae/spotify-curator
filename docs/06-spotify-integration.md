# 06 — Intégration Spotify

Tags: #spotify #oauth #pkce #api #scopes

## Principe

L’application utilise OAuth Authorization Code avec PKCE. Aucun client secret ne doit être nécessaire ni stocké.

Redirect URI local :

```text
http://127.0.0.1:8765/api/v1/spotify/auth/callback
```

## Configuration Spotify Developer Dashboard

1. Créer une application Spotify.
2. Copier le Client ID.
3. Ajouter le Redirect URI local.
4. Ne pas utiliser le Client Secret dans le projet.
5. Définir les scopes par phase.

## Variables d’environnement

```env
SPOTIFY_CLIENT_ID=
SPOTIFY_REDIRECT_URI=http://127.0.0.1:8765/api/v1/spotify/auth/callback
SPOTIFY_SCOPES=user-read-private user-library-read playlist-read-private playlist-read-collaborative
```

## Scopes par phase

### Phase 1 — lecture uniquement

```text
user-read-private
user-library-read
playlist-read-private
playlist-read-collaborative
```

### Phase 2 — dry-run uniquement

Même scopes que phase 1. Les actions réelles doivent être bloquées si scopes write absents.

### Phase 5+ — écriture playlist

Ajouter uniquement lorsque la synchronisation est implémentée :

```text
playlist-modify-private
playlist-modify-public
```

### Phase restauration likes

Ajouter uniquement si restauration effective :

```text
user-library-modify
```

## Flux PKCE

1. Générer `code_verifier`.
2. Générer `code_challenge` en S256.
3. Générer `state` aléatoire.
4. Stocker temporairement verifier/state côté core.
5. Ouvrir URL d’autorisation.
6. Spotify redirige vers callback local.
7. Vérifier `state`.
8. Échanger `code` contre access/refresh token.
9. Stocker token localement.
10. Rafraîchir automatiquement si expiré.

## Stockage token

Phase 1 : SQLite local de développement accepté.

Contraintes :

- DB ignorée par Git ;
- ne jamais logger access token/refresh token ;
- ne jamais exposer token à l’UI ;
- prévoir dette technique vers OS keychain ou stockage chiffré.

## SpotifyClient

Responsabilités :

- injection token ;
- refresh token ;
- pagination ;
- retry/backoff ;
- respect `Retry-After` ;
- normalisation erreurs ;
- logs sans données sensibles.

## Pagination

Spotify utilise souvent `limit`, `offset`, `next`.

Le client doit fournir un générateur ou une fonction `paginate(endpoint, params)` qui :

- suit `next` ;
- s’arrête proprement ;
- supporte limite de sécurité ;
- met à jour la progression du job.

## Rate limits

En cas de `429` :

- lire `Retry-After` ;
- marquer job `rate_limited` ou attendre selon stratégie ;
- stocker `next_retry_at` ;
- ne pas spammer l’API.

## Import liked tracks

Données minimales :

- `spotify_track_id` ;
- `spotify_uri` ;
- `title` ;
- `artists` ;
- `album` ;
- `duration_ms` ;
- `explicit` ;
- `popularity` ;
- `preview_url` ;
- `external_url` ;
- `isrc` ;
- `added_at` ;
- `raw_json`.

Règles :

- upsert par `spotify_track_id` ;
- ne pas supprimer les anciennes lignes : marquer `is_current=false` ;
- `last_seen_at` doit être mis à jour ;
- créer snapshot après import si demandé.

## Import playlists

Données minimales :

- `spotify_playlist_id` ;
- `name` ;
- `description` ;
- `owner` ;
- `public` ;
- `collaborative` ;
- `snapshot_id_spotify` ;
- items paginés ;
- position ;
- `added_at` ;
- `added_by` ;
- raw payload.

Cas à gérer :

- playlist collaborative ;
- playlist privée ;
- track null ;
- local track ;
- episode/podcast item ;
- track indisponible ;
- relink Spotify.

## Écriture Spotify

Toute écriture doit respecter :

1. dry-run ;
2. confirmation UI ;
3. scope vérifié ;
4. log action ;
5. rollback local si possible ;
6. gestion erreur partielle.

Actions concernées :

- unlike tracks ;
- restore liked tracks ;
- create playlist ;
- replace playlist items ;
- add items ;
- remove obsolete items.

## Erreurs spécifiques

| Code | Cause |
|---|---|
| `SPOTIFY_NOT_AUTHENTICATED` | Token absent |
| `SPOTIFY_TOKEN_EXPIRED` | Refresh impossible |
| `SPOTIFY_RATE_LIMITED` | 429 |
| `SPOTIFY_FORBIDDEN_SCOPE` | Scope manquant |
| `SPOTIFY_TRACK_UNAVAILABLE` | Track inaccessible |
| `SPOTIFY_PLAYLIST_UNAVAILABLE` | Playlist inaccessible |
| `SPOTIFY_PARTIAL_IMPORT` | Import incomplet |
