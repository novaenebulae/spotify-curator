# Phase 2.5 — Performance GET /tracks & /library

Tags: #phase-2.5 #performance #tracks #library

## Objectif

Diagnostiquer et optimiser `GET /api/v1/tracks` et l’UI `/library` sans changer les fonctionnalités.

## Instrumentation

| Mécanisme | Activation |
|-----------|------------|
| Logs API + segments SQL | `TRACKS_PERF_LOG=1` sur le conteneur `core-api` |
| En-têtes réponse | `X-Tracks-Perf-Ms`, `X-Tracks-Sql-Count`, `X-Tracks-Sql-Ms` |
| Script benchmark | `uv run python core/scripts/benchmark_tracks.py` |
| EXPLAIN | `uv run python core/scripts/benchmark_tracks.py --explain --database-url sqlite:///...` |
| Frontend | `import.meta.env.DEV` + `localStorage.LIBRARY_PERF_LOG=1` → `console.debug` |

### Scénarios benchmark

- `page1_default` — page=1, page_size=50, sort=liked_added_at desc
- `page2_default` — page=2
- `search_q` — `q=a` (override avec `--q=terme`)
- `sort_liked_desc`
- `playlist_filter` — `--playlist-id=N`

```bash
# HTTP (core Docker démarré) — chemin réel de l’app
cd core
uv run python scripts/benchmark_tracks.py --base-url http://127.0.0.1:8765 --runs 5
```

## Optimisations appliquées

1. **COUNT** sans `ORDER BY` et sans sous-requête DISTINCT ; jointures minimales pour les filtres uniquement.
2. **Suppression DISTINCT** (jointures 1:1 par track).
3. **`playlist_count`** via `COUNT … GROUP BY` au lieu de charger `playlists[]`.
4. **Réponse liste** : `playlists` toujours `[]`.
5. **Index** `0003_perf_tracks` : `liked_tracks(added_at)`, `track_artists(track_id, position)`.
6. **Frontend** : stale-while-revalidate, `AbortController` par fetch, marques `performance`.
7. **Infra** : SQLite dans le volume Docker nommé `spotify_curator_data` + `SQLITE_JOURNAL_MODE=WAL` (plus de bind mount `./data` par défaut).

## Stockage SQLite

| Mode | Compose | Journal | Usage |
|------|---------|---------|--------|
| Bind mount (ancien) | `./data:/app/data` | `DELETE` | Mesures baseline ci-dessous |
| Volume nommé (actuel) | `spotify_curator_data:/app/data` | `WAL` | Production locale recommandée |

Migration depuis `data/` :

```powershell
.\scripts\migrate-sqlite-to-docker-volume.ps1
docker compose up -d --build
```

## Mesures

### A — Bind mount `./data` + `DELETE` (avant migration volume)

| Scénario | median_ms | notes |
|----------|-----------|-------|
| page1_default | 6142.2 | runs 8410, 7210, 5275, 5167, 6142 |
| page2_default | 6353.0 | |
| search_q (`q=a`) | 21169.0 | |
| sort_liked_desc | 5632.6 | |

### B — Volume `spotify_curator_data` + `WAL` (après migration)

Mesure locale (HTTP, 3 runs) après `migrate-sqlite-to-docker-volume.ps1` :

| Scénario | median_ms | vs bind mount (A) |
|----------|-----------|-------------------|
| page1_default | 89.9 | ~68× plus rapide |
| page2_default | 98.7 | ~64× |
| search_q (`q=a`) | 230.5 | ~92× |
| sort_liked_desc | 77.2 | ~73× |

```
page1_default   runs=[347.6, 86.4, 89.9]
page2_default   runs=[84.7, 98.7, 98.7]
search_q        runs=[230.5, 298.8, 216.6]
sort_liked_desc runs=[77.2, 73.0, 77.3]
```

**Verdict** : le bind mount `./data` sur Windows était le goulot principal (~6–21 s). Avec le volume nommé + WAL, les requêtes restent sous ~300 ms (recherche `q` incluse). Les optimisations SQL restent utiles mais l’infra Docker était critique sur cette machine.

## Validation

```bash
cd core && uv run pytest tests/test_tracks_search.py tests/test_tracks_perf.py tests/test_migrations.py -q
```
