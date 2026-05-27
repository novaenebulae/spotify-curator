# 02 — Structure de dépôt

Tags: #repo #monorepo #structure

```text
spotify-curator/
  AGENTS.md
  README.md
  .cursor/rules/
  app/
    frontend/
    src-tauri/
  core/
    app/
      api/
      database/
      jobs/
      spotify/
      reccobeats/
      audio_sources/
      audio_download/
      audio_analysis/
      features/
      clustering/
      playlist_engine/
      settings/
    tests/
    pyproject.toml
  docker/
    core/
    audio-downloader/
    essentia-tensorflow-worker/
    clustering-worker/
  profiles/
  data/
  cache/
  models/
  logs/
  docs/
  backlog/
  prompts/
  templates/
  docker-compose.yml
  docker-compose.dev.yml
  docker-compose.test.yml
  .env.example
```

## Séparation

- `app/` : UI seulement.
- `core/` : logique métier, DB, API, jobs.
- `docker/` : images et runtime.
- `data/cache/models/logs` : volumes locaux, non committés sauf `.gitkeep`.
