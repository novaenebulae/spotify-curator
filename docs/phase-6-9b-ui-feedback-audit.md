# Phase 6.9b — Audit retours tests UI (juin 2026)

Tags: #phase-6 #ui #audit #features

Document de référence pour le lot correctifs post-6.9b. Plan d’implémentation : lots L0–L4 (voir backlog §6.9b feedback).

## Synthèse des causes racines

| Symptôme | Cause principale | Correctif |
|----------|------------------|-----------|
| Advanced : mêmes % | `formatPercent` arrondit ; filtre UI partiel sur `scalar_features` | Afficher tous les scalaires ; valeur décimale + confiance |
| Fusion incomplète | `merged` = seule ligne `audio_features` active, pas `FeatureResolver` | Champ API `resolved_features` |
| TF absent de Sources | `advanced` hors `sources[]` | Carte source `essentia_tensorflow` |
| Genre message générique | Ligne DB `model_missing` sans `top_k` | `genre.status` / `missing_reason` + message UI précis |
| Page lente | `include_fields=true` + 4 appels au mount | Lazy load ; supprimer Field coverage |
| Deux panneaux analyse | UX 6.9b initiale | `LocalAnalysisPanel` unifié |
| Couverture scindée | Deux endpoints | Section « Analyse locale » fusionnée |
| Workers dans panneau analyse | Placement composant | `WorkersStatusCard` dédiée |
| Profils techniques | Clés brutes dans `<select>` | Libellés + description manifest |
| Advanced failures doublons | 1 ligne DB par feature/track | Fusion dans `FailureInsightsService` |
| Field coverage | Peu utile, coûteux | Supprimé UI |
| Bibliothèque sans TF | `track_feature_status` low-level seul | `local_analysis_status` agrégé |
| Require real TF | Option produit rejetée | Toujours `true` en UI |
| Progression segments | `progress_*` = compteurs `job_items` | `tracks_completed` / `tracks_total` dans job |

## Critères d’acceptation

Voir [`docs/10-testing-strategy.md`](10-testing-strategy.md) section UI 6.9b feedback.
