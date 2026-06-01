# 01 — Architecture

Tags: #architecture #docker #tauri #svelte #fastapi #sqlite #workers

## Vue d’ensemble

```text
┌───────────────────────────────────────────────────────┐
│ Windows host                                           │
│                                                       │
│  ┌─────────────────────────────────────────────────┐  │
│  │ Tauri Desktop App                               │  │
│  │ - WebView2                                      │  │
│  │ - Svelte/SvelteKit SPA                          │  │
│  │ - UI / navigation / confirmations               │  │
│  │ - OAuth browser opening                         │  │
│  └───────────────────────┬─────────────────────────┘  │
│                          │ HTTP localhost             │
└──────────────────────────┼─────────────────────────────┘
                           │ http://127.0.0.1:8765/api/v1
┌──────────────────────────┼─────────────────────────────┐
│ Docker Desktop + WSL2    │                             │
│                          ▼                             │
│  ┌─────────────────────────────────────────────────┐  │
│  │ core-api FastAPI                                │  │
│  │ - API locale                                    │  │
│  │ - orchestration métier                          │  │
│  │ - SQLite                                        │  │
│  │ - jobs                                          │  │
│  └───────┬─────────┬───────────────┬────────────────┘  │
│          │         │               │                   │
│          ▼         ▼               ▼                   │
│  job-worker  audio-downloader  clustering-worker       │
│          │         │               │                   │
│          ▼         ▼               ▼                   │
│  essentia-lowlevel  essentia-tensorflow                │
└─────────────────────────────────────────────────────────┘
```

## Composants

### Tauri / Svelte

Responsabilités :

- afficher l’UI ;
- appeler le core local ;
- afficher les états de jobs ;
- ouvrir le navigateur pour OAuth ;
- gérer les confirmations utilisateur ;
- ne pas contenir la logique métier lourde.

Ne doit pas :

- accéder directement à SQLite ;
- exécuter Essentia ;
- télécharger l’audio ;
- stocker des tokens en clair dans le frontend.

### core-api

Responsabilités :

- exposer l’API locale ;
- gérer la configuration non sensible ;
- orchestrer les imports Spotify ;
- gérer les snapshots ;
- lancer et suivre les jobs ;
- lire/écrire SQLite ;
- agréger les résultats workers ;
- fournir les exports.

### job-worker

Responsabilités :

- exécuter les tâches longues ;
- mettre à jour la progression ;
- gérer retry/backoff ;
- journaliser erreurs ;
- éviter de bloquer les routes HTTP.

Pour le MVP, `job-worker` peut être un module/processus du core. L’architecture doit toutefois rester compatible avec une séparation future.

**État actuel (phase 3)** : seul le service `core-api` est déclaré dans `docker-compose.yml`. Les jobs longs tournent en **threads daemon in-process** (`JobService.start_background`), pas en conteneurs `job-worker` séparés. Le schéma Compose ci-dessus (workers audio, Essentia, clustering) est la **cible** des phases 4+.

Référence détaillée : [`16-job-execution-model-and-worker-parallelism.md`](16-job-execution-model-and-worker-parallelism.md) (état actuel vs cible, parallélisme ReccoBeats batch, workers Essentia persistants).

### audio-downloader

Responsabilités :

- résoudre une source audio ;
- télécharger uniquement des segments ;
- utiliser yt-dlp ;
- convertir via FFmpeg ;
- écrire dans `cache/audio_segments` ;
- supprimer après analyse.

### essentia-lowlevel

Responsabilités :

- utiliser `ghcr.io/mtg/essentia:bullseye-v2.1_beta5` ;
- exécuter `essentia_streaming_extractor_music` ;
- produire JSON low-level ;
- ne pas gérer la logique métier.

### essentia-tensorflow

Responsabilités :

- exécuter les modèles TensorFlow Essentia ;
- générer embeddings ;
- prédire mood/style/voice/instrumental selon modèles disponibles ;
- versionner modèle et pipeline.

### clustering-worker

Responsabilités :

- construire matrice features ;
- imputer/normaliser ;
- exécuter UMAP ;
- exécuter HDBSCAN ;
- persister projection et clusters.

## API locale

Base URL :

```text
http://127.0.0.1:8765/api/v1
```

Règles :

- ne jamais binder sur `0.0.0.0` ;
- CORS uniquement pour l’origine locale de l’app Tauri si nécessaire ;
- erreurs uniformes ;
- routes versionnées ;
- aucune route destructive sans dry-run.

## Volumes

```text
data/
  spotify_curator.sqlite
  backups/

cache/
  audio_segments/
  essentia_lowlevel_json/
  essentia_tensorflow_json/
  clustering/

models/
  essentia/
  tensorflow/
  openl3/
  discogs_effnet/

logs/
  core/
  jobs/
  docker/

exports/
  csv/
  json/
```

Règles :

- `data/` contient des données personnelles ; ignorer Git.
- `cache/` peut être supprimé ; ignorer Git.
- `models/` peut être lourd ; ignorer Git.
- `logs/` peut contenir des chemins/données ; ignorer Git.
- `exports/` peut contenir la bibliothèque personnelle ; ignorer Git.

## Flux principaux

### Import Spotify

```text
OAuth PKCE
  ↓
SpotifyClient paginé
  ↓
normalisation tracks/artists/albums/playlists
  ↓
upsert SQLite
  ↓
snapshot
  ↓
diff avec snapshot précédent
  ↓
UI résumé + exports
```

### Gestion bibliothèque

```text
SQLite tracks/playlists/snapshots
  ↓
API /tracks avec filtres
  ↓
UI table sélectionnable
  ↓
dry-run action
  ↓
library_actions
```

### ReccoBeats

```text
tracks sans features
  ↓
job enrichment
  ↓
ReccoBeatsClient retry/backoff
  ↓
raw payload
  ↓
normalisation features
  ↓
audio_features + coverage
```

### Analyse locale

```text
track metadata
  ↓
resolve audio source
  ↓
segments A/B/C <= 30s
  ↓
yt-dlp + FFmpeg
  ↓
Essentia low-level
  ↓
parse JSON
  ↓
merge multi-source
  ↓
cleanup audio
```

### Playlist generation

```text
PlaylistRule
  ↓
source selection
  ↓
strict filters
  ↓
scoring weighted
  ↓
diversity constraints
  ↓
ordering
  ↓
preview
  ↓
dry-run sync
```

## Découpage par phase

| Phase | Architecture concernée |
|---:|---|
| 0 | core-api, Docker, SQLite, Tauri shell |
| 1 | Spotify OAuth/import/snapshots/exports |
| 2 | library management API/UI/actions |
| 3 | ReccoBeats/jobs/features coverage |
| 4 | audio downloader + Essentia low-level |
| 5 | playlist engine v1 + dry-run sync |
| 6 | clustering worker + UMAP UI |
| 7 | Essentia TensorFlow + embeddings |
| 8 | playlist engine avancé |
| 9 | packaging, backup/restore, polish |
