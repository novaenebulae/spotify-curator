# 17 — Audio preview and hybrid segment strategy

Tags: #audio #deezer #youtube #preview #segments #phase-4

## Objectif

Décrire la stratégie nominale **Deezer preview (UI) + YouTube segments (analyse)** et les fallbacks, sans stocker de fichiers preview pour l’UI.

## Stratégie nominale

- **UI** : métadonnées Deezer (`preview_url` dans `track_previews`) — lecture streaming HTML5, pas de téléchargement ni fichier local.
- **Analyse** : 2 segments YouTube représentatifs (~1/3 et ~2/3 de la piste), 15 s chacun, max 30 s.

## Matrice de fallback

| Deezer preview (metadata) | YouTube fiable | Segments analyse | `analysis_decision` |
|---------------------------|----------------|------------------|---------------------|
| Oui | Oui | `YOUTUBE_1_3`, `YOUTUBE_2_3` | `deezer_preview_plus_two_youtube_segments` |
| Non | Oui | `YOUTUBE_1_4`, `YOUTUBE_1_2`, `YOUTUBE_3_4` | `youtube_three_segments_fallback` |
| Oui | Non | `DEEZER_PREVIEW` (fichier temporaire) | `deezer_preview_only_fallback` |
| Non | Non | aucun | `local_analysis_unavailable` |

## Types

### `track_previews` (metadata uniquement)

Pas de binaire audio. Voir [`05-domain-model.md`](05-domain-model.md).

### Segments (`track_segments`)

**Sources** : `youtube`, `deezer_preview`, `test`, `cache`

**Types** : `YOUTUBE_1_3`, `YOUTUBE_2_3`, `YOUTUBE_1_4`, `YOUTUBE_1_2`, `YOUTUBE_3_4`, `DEEZER_PREVIEW`, `TEST`, `MANUAL` (legacy `A`/`B`/`C` pour `abc_default`)

**`source_quality`** : `youtube_representative`, `youtube_fallback_three_segments`, `deezer_preview_30s`, `test_fixture`

## Confiance

```text
final_feature_confidence = parser_confidence * source_quality_weight * match_confidence
```

Poids (`settings`) :

| Mode | Poids |
|------|-------|
| YouTube 2 segments (nominal) | 0.95 |
| YouTube 3 segments (fallback) | 1.00 |
| Deezer preview seul | 0.70 |

Seuils Deezer : `DEEZER_PREVIEW_UI_MIN_CONFIDENCE`, `DEEZER_PREVIEW_ANALYSIS_MIN_CONFIDENCE`  
YouTube : `YOUTUBE_MIN_CONFIDENCE`

## Jobs et workers

| Job | Items | Worker |
|-----|-------|--------|
| `preview_resolve` | `preview_resolve_track` | `preview-resolver-worker` |
| `audio_download` | `audio_download_track` | `audio-downloader-worker` |
| `essentia_lowlevel_analysis` | `essentia_lowlevel_track` | `essentia-lowlevel-worker` |

## API

- `GET /api/v1/tracks/{track_id}/preview?resolve_if_missing=`
- `POST /api/v1/previews/resolve`
- `GET /api/v1/previews/coverage`
- `POST /api/v1/audio/segments/plan` (stratégie `hybrid_deezer_youtube_representative`)

## Règles non négociables

- Aucun segment > 30 s
- Pas de téléchargement complet standard
- Cleanup audio après analyse (`deleted_at`)
- Previews UI jamais persistées en fichier
- Workers persistants, pas de conteneur par piste/segment

## Tests attendus

Voir [`10-testing-strategy.md`](10-testing-strategy.md) — Deezer matching, hybrid 4 cas, preview API, confidence weights.

## Critères d’acceptation

- Preview Deezer en UI si trouvée (URL uniquement)
- Nominal : 2 segments YouTube si Deezer + YouTube OK
- Fallback YT : 3 segments
- Fallback Deezer-only : 1 segment preview temporaire
- Indisponible : `local_analysis_unavailable`
- Confidence Deezer-only < YouTube multi-segments
