# 06 — Contrats API locale

Tags: #api #fastapi #contracts

Base URL :

```text
http://127.0.0.1:8765/api/v1
```

## Format d’erreur

```json
{
  "error": {
    "code": "STRING_CODE",
    "message": "Human readable message",
    "details": {},
    "retryable": false
  }
}
```

## Phase 0

### `GET /health`

```json
{
  "status": "ok",
  "service": "spotify-curator-core",
  "version": "0.1.0"
}
```

### `GET /runtime/config`

Retourne configuration non sensible.

### `GET /runtime/docker/checks`

Retourne derniers diagnostics Docker.

### `POST /runtime/docker/checks/run`

Lance les diagnostics.

## Phases futures

- `/spotify/auth/*`
- `/library/import`
- `/library/snapshots`
- `/tracks`
- `/library/actions/*`
- `/jobs`
- `/features/*`
- `/clustering/*`
- `/playlist-rules`
- `/generated-playlists`
- `/sync`
