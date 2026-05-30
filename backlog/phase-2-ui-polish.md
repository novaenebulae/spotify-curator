# Backlog — Phase 2 UI polish

Tags: #backlog #ui #phase2

## Objectif

Améliorer l’UX (covers Spotify, doublons lisibles, shell CSS, Home/Settings/Import) sans extension métier ni régression perf phase 2.5.

## Livré

- [x] Migration `0004_album_covers` — colonnes `albums.cover_*`
- [x] `app/library/album_cover.py` + extraction à l’import (`track_upsert.py`)
- [x] Script `core/scripts/backfill_album_covers.py` (`--dry-run`)
- [x] API : covers sur `GET /tracks`, `GET /library/duplicates`, `GET /library/missing-tracks`
- [x] Doublons : dédup présentation, `reason_label`, counts, `contexts` playlists
- [x] `GET /api/v1/library/summary`
- [x] Frontend : tokens `app.css`, shell layout, `AlbumCover`, `StatusBadge`
- [x] `LibraryTable`, `DuplicateGroupCard`, `ExportPanel`, Home dashboard, Settings cards
- [x] Tests + docs 05/06/09/10

## Validation

```bash
cd core && uv run pytest -q && uv run ruff check app/library app/database app/api/v1/library.py
cd app/frontend && npm run check && npm run build
docker compose up -d --build
curl http://127.0.0.1:8765/api/v1/health
curl "http://127.0.0.1:8765/api/v1/tracks?page_size=5"
curl http://127.0.0.1:8765/api/v1/library/summary
curl "http://127.0.0.1:8765/api/v1/library/duplicates?strategy=isrc"
```

Après migration sur une base existante :

```bash
# Host (core venv) — ne pas utiliser `python` seul
uv run --project core python core/scripts/backfill_album_covers.py --dry-run
# ou
.\scripts\backfill-album-covers.ps1 --dry-run

# Base SQLite dans le volume Docker (recommandé si vous utilisez docker compose)
docker compose exec core-api uv run python scripts/backfill_album_covers.py --dry-run
docker compose exec core-api uv run python scripts/backfill_album_covers.py
```

UI manuelle : `/`, `/import`, `/library` (titres + doublons), `/settings`.

## Hors scope

ReccoBeats, audio, playlist engine, écriture Spotify réelle, Tailwind, stockage local des images, proxy cover.
