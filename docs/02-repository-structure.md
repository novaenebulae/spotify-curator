# 02 — Structure de dépôt

Tags: #repo #monorepo #structure #cursor

## Structure cible

```text
spotify-curator/
  AGENTS.md
  README.md
  .env.example
  .gitignore
  docker-compose.yml
  docker-compose.dev.yml
  docker-compose.test.yml

  .cursor/
    rules/
      project-overview.mdc
      backend-python.mdc
      frontend-svelte.mdc
      docker-runtime.mdc
      security.mdc
      testing.mdc

  app/
    frontend/
      package.json
      src/
        lib/
          api/
          components/
          routes/
          stores/
          types/
          utils/
      tests/
    src-tauri/
      Cargo.toml
      tauri.conf.json
      src/

  core/
    pyproject.toml
    uv.lock
    alembic.ini
    app/
      main.py
      api/
        v1/
          routes_runtime.py
          routes_spotify.py
          routes_jobs.py
          routes_library.py
          routes_tracks.py
          routes_features.py
          routes_audio.py
          routes_playlists.py
          routes_clustering.py
          routes_exports.py
      database/
        session.py
        models.py
        migrations/
        repositories/
      settings/
        config.py
      jobs/
        models.py
        service.py
        runner.py
        retry.py
      spotify/
        auth.py
        client.py
        normalizer.py
        importer.py
        snapshots.py
      library/
        search.py
        duplicates.py
        missing.py
        actions.py
      reccobeats/
        client.py
        normalizer.py
        service.py
      features/
        sources.py
        merge.py
        coverage.py
        derived_scores.py
      audio_sources/
        provider.py
        resolver.py
        matching.py
      audio_download/
        segment_strategy.py
        ytdlp_provider.py
        ffmpeg.py
      audio_analysis/
        essentia_lowlevel.py
        parser.py
        cleanup.py
      clustering/
        profiles.py
        matrix.py
        umap_runner.py
        hdbscan_runner.py
      playlist_engine/
        schema.py
        filters.py
        scoring.py
        diversity.py
        ordering.py
        preview.py
        sync.py
      exports/
        csv_exporter.py
        json_exporter.py
      observability/
        errors.py
        logging.py
        diagnostics.py
    tests/
      unit/
      integration/
      fixtures/

  docker/
    core/
      Dockerfile
    audio-downloader/
      Dockerfile
    essentia-tensorflow-worker/
      Dockerfile
      analyze_effnet.py
    clustering-worker/
      Dockerfile

  profiles/
    essentia_lowlevel_basic.yaml
    essentia_lowlevel_extended.yaml
    clustering_generalist.yaml
    clustering_mood.yaml
    clustering_timbre.yaml

  docs/
    00-project-brief.md
    01-architecture.md
    02-repository-structure.md
    03-development-workflow.md
    04-backlog-by-phase.md
    05-domain-model.md
    06-api-contract.md
    06-spotify-integration.md
    07-audio-analysis-pipeline.md
    08-playlist-engine.md
    09-ui-specification.md
    10-testing-strategy.md
    11-security-and-privacy.md
    12-decisions.md
    13-error-handling-and-observability.md
    14-configuration.md
    15-cursor-rules.md

  backlog/
    phase-0.md
    phase-1.md
    ...
    phase-9.md

  templates/
    phase-review-template.md
    task-template.md
    api-endpoint-template.md
    test-plan-template.md

  prompts/
    _prompt-template.md

  data/
    .gitkeep
  cache/
    .gitkeep
  models/
    .gitkeep
  logs/
    .gitkeep
  exports/
    .gitkeep
```

## Règles de séparation

### `app/`

Contient uniquement l’application desktop et l’interface. Le frontend ne doit pas contenir de logique métier persistante, ni de secrets.

### `core/`

Contient l’API, les services métier, l’accès DB, les jobs et les tests Python.

Les routes FastAPI doivent rester fines : validation request, appel service, réponse.

### `core/app/database/repositories/`

Contient les requêtes SQLite complexes : recherche tracks, snapshots, actions, features, clustering.

### `core/app/jobs/`

Contient la logique générique de jobs : création, statut, progression, retry, erreurs.

### `core/app/spotify/`

Contient OAuth, client Spotify, import et snapshots Spotify. Ne doit pas contenir de logique UI.

### `core/app/library/`

Contient recherche, doublons, titres disparus, actions dry-run.

### `core/app/features/`

Contient le modèle multi-source des features, le merge et la coverage.

### `core/app/audio_*`

Contient résolution, téléchargement, conversion, analyse et cleanup audio.

### `core/app/playlist_engine/`

Contient les règles de playlist et le moteur de génération.

### `docker/`

Contient uniquement les Dockerfiles et scripts runtime nécessaires aux services.

### `profiles/`

Contient les profils YAML versionnables : extraction Essentia, clustering, presets de features. Pas de données personnelles.

### `data/cache/models/logs/exports`

Ces dossiers sont ignorés par Git sauf `.gitkeep`.

## Conventions de nommage

### Python

- Modules : `snake_case.py`.
- Classes : `PascalCase`.
- Fonctions : `snake_case`.
- Schémas Pydantic request/response : suffixes `Request`, `Response`, `Item`.
- Services : suffixe `Service`.
- Repositories : suffixe `Repository`.

### API

- Préfixe : `/api/v1`.
- Ressources au pluriel : `/tracks`, `/jobs`, `/features`.
- Actions explicites : `/library/actions/dry-run`.
- Pas de verbe ambigu : préférer `/snapshots/diff` à `/compare`.

### UI

- Composants réutilisables dans `src/lib/components`.
- Clients API dans `src/lib/api`.
- Types partagés dans `src/lib/types`.
- Stores dans `src/lib/stores`.

## Fichiers à ne jamais commiter

```text
.env
.env.local
*.sqlite
*.sqlite-shm
*.sqlite-wal
data/*
cache/*
models/*
logs/*
exports/*
*.wav
*.mp3
*.flac
*.ogg
*.m4a
*.onnx
*.pb
*.h5
*.tflite
```

## Fichiers autorisés dans les volumes

```text
data/.gitkeep
cache/.gitkeep
models/.gitkeep
logs/.gitkeep
exports/.gitkeep
```
