# Prompt Cursor — Phase 5.4 — Spotify dry-run sync

Objectif : implémenter la synchronisation Spotify en dry-run uniquement.

## À lire avant de coder

```text
docs/06-api-contract.md
docs/08-playlist-engine.md
backlog/phase-5.md
```

## Préconditions

Doivent exister :

```text
generated_playlists
generated_playlist_items
preview endpoint
Spotify client read playlist tracks
```

Si les APIs Spotify nécessaires n'existent pas, ajoute uniquement les méthodes read nécessaires. Ne pas ajouter de write.

## Interdiction absolue phase 5

```text
Aucune écriture Spotify réelle.
Aucun ajout/suppression de tracks dans Spotify.
Aucune création réelle de playlist Spotify.
Aucun endpoint apply.
```

## Modules à créer ou compléter

```text
core/app/playlists/sync_dry_run.py
core/app/database/repositories/sync_jobs.py
core/app/api/v1/sync.py
```

## Tables

Utiliser ou créer :

```text
sync_jobs
sync_logs
```

Champs attendus :

```text
generated_playlist_id
target_spotify_playlist_id
sync_mode
dry_run=true
status
diff_json
created_at
finished_at
```

## Endpoint

Ajouter :

```text
POST /api/v1/sync/dry-run
GET /api/v1/sync/jobs/{sync_job_id}
```

Payload :

```json
{
  "generated_playlist_id": "...",
  "target_spotify_playlist_id": "...",
  "sync_mode": "replace"
}
```

Modes :

```text
create
replace
add_only
remove_obsolete
replace_after_dry_run
```

## Diff attendu

```json
{
  "to_add": [],
  "to_remove": [],
  "unchanged": [],
  "not_syncable": [],
  "warnings": []
}
```

Chaque item doit inclure au minimum :

```text
track_id
spotify_track_id
title
artist_names
reason
```

## Scopes

- Le dry-run doit fonctionner sans scope write.
- Si scope write absent, ajouter warning `WRITE_SCOPE_NOT_AVAILABLE`.
- Si Spotify non connecté, retourner erreur structurée `UNAUTHORIZED_SPOTIFY`.
- Si playlist cible introuvable, retourner `NOT_FOUND`.

## Tests attendus

```text
dry-run create mode
replace mode diff
add_only mode diff
remove_obsolete mode diff
unchanged tracks
tracks without spotify id -> not_syncable
missing Spotify auth
missing write scope warning
no Spotify write method called
sync job persisted
sync logs persisted
```

Utiliser mocks pour Spotify.

## Validation

```bash
cd core
uv run pytest -q
uv run ruff check .
```

## Réponse attendue

Fournis :

```text
- endpoints ajoutés ;
- format diff_json ;
- fichiers modifiés ;
- garanties anti-write ;
- tests ajoutés ;
- commandes exécutées ;
- risques restants.
```
