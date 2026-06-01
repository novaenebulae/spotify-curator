# Phase 4 — yt-dlp + analyse locale low-level

Tags: #backlog #phase-4 #audio #yt-dlp #essentia

## But

Analyser des segments audio temporaires pour compléter les features locales low-level.

## Definition of Done phase

- Les livrables de phase sont présents.
- Les tests minimum passent.
- Les commandes de validation sont documentées.
- La documentation est à jour.
- Aucun secret, cache, modèle lourd ou fichier audio n’est commité.
- Aucune régression sur les phases précédentes.

## 4.1 — AudioProvider

Statut : DONE

- Interface `AudioProvider`, `StubAudioProvider` / `YtDlpSegmentProvider`.
- Tests unitaires sans réseau.

## 4.2 — Stratégie segments

Statut : DONE

- `abc_default`, limite 30s, cas courts, tests limites.
- **Hybride** : `hybrid_deezer_youtube_representative` (doc [`17-audio-preview-and-segment-strategy.md`](../docs/17-audio-preview-and-segment-strategy.md)), migration `0007`, previews Deezer metadata, worker `preview-resolver-worker`.

## 4.3 — YtDlpSegmentProvider

Statut : DONE

- Résolution, matching, `download-sections`, `noplaylist`, FFmpeg WAV.

## 4.4 — audio_download_jobs

Statut : DONE

## 4.5 — track_segments

Statut : DONE

- Contrainte DB `duration_seconds <= 30`.

## 4.6 — Essentia low-level

Statut : DONE

- Worker Docker persistant, profil YAML, subprocess (pas de `docker run` par piste).

## 4.7 — Parser JSON

Statut : DONE

## 4.8 — Merge features

Statut : DONE (MVP)

- `POST /features/merge/recompute`, upsert `essentia_lowlevel`.

## 4.9 — Cleanup

Statut : DONE

## Workers & jobs

Statut : DONE

- Tables `job_items`, `worker_heartbeats`, `job_events`.
- Services `audio-downloader` et `essentia-lowlevel-worker` (profil Compose `audio`).

## Validation

```bash
cd core && uv run alembic upgrade head
cd core && uv run pytest -q
docker compose up -d --build core-api
docker compose --profile audio up -d --build --scale audio-downloader=2 --scale essentia-lowlevel-worker=2
curl http://127.0.0.1:8765/api/v1/workers
```
