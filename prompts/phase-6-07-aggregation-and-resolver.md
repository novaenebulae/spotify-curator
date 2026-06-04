# Prompt Cursor — Phase 6.7 — Agrégation finale et TrackFeatureView


Tu travailles sur le projet Spotify Curator.

Contexte actuel :
- Phases 0 à 5 implémentées.
- Phase 5 terminée : playlist generator v1, règles, filtres, scoring, diversité, preview persistée, dry-run sync.
- Phase 4 existante : audio-downloader, preview-resolver-worker, essentia-lowlevel-worker, Deezer previews, segments YouTube/Deezer, Essentia low-level, job_items, worker_heartbeats.
- Nouvelle phase 6 : remplacer le flux séquentiel `download all → analyze all` par un pipeline streaming/parallèle et ajouter Essentia TensorFlow + features avancées.
- Ne jamais commiter secrets, DB, cache, audio, modèles lourds.
- Les segments audio restent temporaires et <= 30s.
- Les workers Docker doivent rester persistants.
- Le playlist engine ne doit jamais lire les payloads bruts : il consomme FeatureRegistry + FeatureResolver + TrackFeatureView.

Contraintes générales :
- Commencer par auditer le code existant avant de modifier.
- Ne pas casser les tests des phases précédentes.
- Préférer des changements incrémentaux, testés, documentés.
- Ajouter ou mettre à jour les tests à chaque étape.
- Mettre à jour la documentation impactée.


Objectif :
Finaliser l'agrégation par track et intégrer les features avancées dans le contrat de consommation unique.

Tâches :
1. Créer/adapter `FeatureAggregationService`.
2. Agréger par track :
   - low-level multi-segments ;
   - embeddings ;
   - classifiers ;
   - genres top-k ;
   - fallbacks.
3. Enrichir `FeatureValue` :
   - source ;
   - confidence ;
   - model_name ;
   - model_version ;
   - model_hash ;
   - pipeline_version ;
   - aggregation_method ;
   - warnings.
4. Ajouter alias :
   - `genre_discogs519` → `genre_discogs_519`
   - `mood_electronic` → `electronic_profile_score`
   - `instrumental` → `instrumental_focus_score`
   - `acoustic` → `acoustic_profile_score`
   - `valence_local` → `valence_tf`
   - `danceability_local` → `danceability_tf`
5. Garantir que playlist engine et future clustering utilisent uniquement `TrackFeatureView`.
6. Tests non-régression phase 5.

Critères :
- Aucun consumer ne lit les payloads raw.
- Les nouvelles features apparaissent dans l'API.
- Les règles playlist avec features avancées fonctionnent ou warning proprement.

Validation :
```bash
cd core
uv run pytest tests/test_feature_aggregation.py tests/test_feature_resolver.py tests/test_playlist_engine*.py -q
```
