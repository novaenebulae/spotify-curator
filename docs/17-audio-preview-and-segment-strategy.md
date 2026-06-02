# 17 — Audio preview and hybrid segment strategy

Tags: #audio #deezer #youtube #preview #segments #phase-4

## Objectif

Décrire la stratégie **hybride Deezer preview (UI) + segments temporaires (analyse)**, les modes **fast** / **precise**, et les jobs workers associés.

## Modes d’analyse (`analysis_mode`)

Défaut API : **`fast`**.

| Mode | Segments planifiés | Quand |
|------|-------------------|--------|
| **fast** | 0–1 segment | Deezer preview si dispo pour analyse, sinon 1 segment YouTube centré |
| **precise** | Jusqu’à 3 | Deezer + 2× YouTube (~1/3 et ~2/3) si les deux sources OK, sinon 3× YouTube |

Implémentation : [`core/app/audio/strategy/hybrid.py`](../core/app/audio/strategy/hybrid.py).

## Matrice `analysis_decision` (code)

| Situation | `analysis_decision` |
|-----------|---------------------|
| Deezer seul (fast ou precise sans YT) | `deezer_only` |
| 1 segment YouTube (fast) | `youtube_1_segment` |
| Deezer + 2 YouTube (precise) | `deezer_plus_youtube_2_segments` |
| 3 YouTube (precise sans Deezer, ou fallback) | `youtube_3_segments` |
| Aucune source utilisable | `local_analysis_unavailable` |

Stratégie legacy **`abc_default`** : bandes A/B/C (10–25 %, 45–60 %, 70–85 %) — toujours disponible, pas le défaut HTTP.

## UI vs analyse

- **UI** : `track_previews.preview_url` — lecture streaming HTML5, pas de fichier local persisté.
- **Analyse** : segments temporaires `<= 30 s` dans `track_segments` ; cleanup après Essentia sauf option debug.

### URLs Deezer signées

Les URLs CDN (`hdnea=exp=…`) **expirent**. Avant téléchargement segment `deezer_preview`, le worker **`audio-downloader`** appelle `ensure_fresh_deezer_preview_url` puis met à jour `track_previews.preview_url`.

## Types

### `track_previews`

Voir [`05-domain-model.md`](05-domain-model.md) § track_previews.

### Segments (`track_segments`)

**Sources** : `youtube`, `deezer_preview`, `test`, `cache`

**Types segment** : `YOUTUBE_1_3`, `YOUTUBE_2_3`, `YOUTUBE_1_4`, `YOUTUBE_1_2`, `YOUTUBE_3_4`, `DEEZER_PREVIEW`, … (legacy `A`/`B`/`C` pour `abc_default`)

## Confiance

```text
final_feature_confidence = parser_confidence * source_quality_weight * match_confidence
```

Poids (`settings`) :

| Mode | Poids |
|------|-------|
| YouTube 2 segments (precise nominal) | 0.95 |
| YouTube 3 segments | 1.00 |
| Deezer preview seul | 0.70 |

Seuils : `DEEZER_PREVIEW_UI_MIN_CONFIDENCE`, `DEEZER_PREVIEW_ANALYSIS_MIN_CONFIDENCE`, `YOUTUBE_MIN_CONFIDENCE`

## Jobs et workers (Compose profil `audio`)

| Job | Items | Worker Compose | `worker_type` |
|-----|-------|----------------|---------------|
| `preview_resolve` | `preview_resolve_track` | **`preview-resolver-worker`** | `preview_resolver` |
| `audio_download` | `audio_download_track` | **`audio-downloader`** | `audio_downloader` |
| `essentia_lowlevel_analysis` | `essentia_lowlevel_track` | **`essentia-lowlevel-worker`** | `essentia_lowlevel` |

À la fin d’un job, `jobs.result_json` agrège : `succeeded`, `failed`, `skipped`, `not_found` (previews sans match).

### Resolve previews

- `POST /api/v1/previews/resolve` — `only_missing: true` par défaut : **exclut** les titres avec preview Deezer déjà valide.
- `limit: null` : traite **tous** les titres manquants (pas de cap 5000 implicite).

## API

- `GET /api/v1/tracks/{track_id}/preview?resolve_if_missing=`
- `POST /api/v1/previews/resolve`
- `GET /api/v1/previews/coverage`
- `POST /api/v1/audio/segments/plan` — stratégie par défaut `hybrid_deezer_youtube_representative`
- `POST /api/v1/audio/segments/download`
- `POST /api/v1/audio/analysis/lowlevel`

Contrats : [`06-api-contract.md`](06-api-contract.md).

## Règles non négociables

- Aucun segment > 30 s
- Pas de téléchargement complet standard
- Cleanup audio après analyse (`deleted_at`)
- Previews UI jamais persistées en fichier
- Workers persistants (poll `job_items`), pas de conteneur par piste

## Tests

Voir [`10-testing-strategy.md`](10-testing-strategy.md) — matching Deezer, hybrid, preview API, confidence weights, sélection resolve sans limite.
