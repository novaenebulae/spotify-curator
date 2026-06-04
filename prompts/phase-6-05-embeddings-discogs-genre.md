# Prompt Cursor — Phase 6.5 — Embeddings + Genre Discogs519


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
Implémenter la persistance et le parsing des embeddings, puis préparer l'inférence Genre Discogs519.

Tâches :
1. Vérifier/étendre table `track_embeddings`.
2. Ajouter repository/service embeddings :
   - upsert ;
   - version/hash modèle ;
   - dimension ;
   - aggregation_method ;
   - segments_used.
3. Ajouter runner mockable pour embeddings :
   - entrée segment WAV ;
   - sortie vector ;
   - validation dimension.
4. Ajouter mapping Genre Discogs519 :
   - top label ;
   - top score ;
   - top-k labels/scores ;
   - stockage en advanced features ou payload normalisé.
5. Exposer via `FeatureResolver` :
   - `style_embedding`
   - `timbre_embedding`
   - `genre_discogs_519`
   - `genre_discogs_519_top_label`
   - `genre_discogs_519_top_score`.
6. Tests :
   - vector shape ;
   - top-k genre ;
   - modèle absent ;
   - resolver feature.

Critères :
- Fonctionne avec mocks sans modèle réel.
- Compatible modèle réel ultérieur.
- Pas d'accès payload raw depuis consumers.

Validation :
```bash
cd core
uv run pytest tests/test_embeddings_repository.py tests/test_embeddings_runner.py tests/test_genre_discogs_mapping.py tests/test_feature_resolver.py -q
```
