# Phase 2 — Gestion bibliothèque

Tags: #backlog #phase-2 #spotify-curator

## But

Explorer, filtrer, auditer et préparer des actions sur les titres importés.

## Definition of Done phase

- Les livrables de phase sont présents.
- Les tests minimum passent.
- Les commandes de validation sont documentées.
- La documentation est à jour.
- Aucun secret, cache, modèle lourd ou fichier audio n’est commité.
- Aucune régression sur les phases précédentes.

## 2.1 — API recherche tracks

Statut : DONE

### Livré

- Migration `0002_phase2_library` (library_actions, album_id, index).
- `GET /api/v1/tracks` avec filtres cumulables, pagination, tri stable.
- Repository + `TrackSearchService` + tests `test_tracks_search.py`.

## 2.2 — Table UI bibliothèque

Statut : DONE

### Livré

- Route `/library` avec onglets Titres / Doublons / Absents / Historique.
- `libraryApi.ts`, `LibraryTable`, `DryRunModal`.
- Nav « Bibliothèque » dans le layout.

## 2.3 — Doublons

Statut : DONE

### Livré

- `GET /api/v1/library/duplicates` (strategies isrc, title_artist, title_artist_duration, all).
- Tests `test_library_duplicates.py`.

## 2.4 — Absents/disparus

Statut : DONE

### Livré

- `GET /api/v1/library/missing-tracks` (réutilise diff snapshots).
- Tests `test_library_missing.py`.

## 2.5 — Actions dry-run

Statut : DONE

### Livré

- `POST /api/v1/library/actions/dry-run` (unlike, restore, backup).
- Warnings `WRITE_SCOPE_MISSING`, limite 500 titres.
- Aucune écriture Spotify.

## 2.6 — Historique actions

Statut : DONE

### Livré

- Table `library_actions`, `GET /library/actions`, `GET /library/actions/{id}`.
- Tests historique + dry-run.

## Commandes de validation

```bash
cd core
uv run pytest -q
uv run ruff check app/library app/api/v1/tracks.py app/api/v1/library.py app/database/repositories

cd app/frontend
npm run check
npm run build

docker compose -f docker-compose.dev.yml up -d core-api
curl http://127.0.0.1:8765/api/v1/health
curl "http://127.0.0.1:8765/api/v1/tracks?page_size=5"
curl "http://127.0.0.1:8765/api/v1/library/duplicates?strategy=isrc"
curl "http://127.0.0.1:8765/api/v1/library/missing-tracks"
```

UI : `npm run dev` → http://localhost:5173/library

## Limites restantes (hors phase 2)

- Pas d’application réelle des actions Spotify.
- Pas de replay automatique depuis l’historique.
- Doublons calculés à la demande (non persistés).
- Sélection UI limitée à la page courante.
- Pas de tests Vitest frontend (infra absente).
- Pas de features audio / ReccoBeats / playlist engine.

## Documentation à jour

- `docs/05-domain-model.md`
- `docs/06-api-contract.md`
- `docs/09-ui-specification.md`
- `docs/10-testing-strategy.md`
