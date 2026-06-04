# Prompt Cursor — Phase 6.3 — Low-level dans le pipeline parallèle


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
Faire consommer au worker Essentia low-level les stages du nouveau pipeline tout en conservant les résultats phase 4.

Tâches :
1. Adapter `essentia-lowlevel-worker` pour réserver les stages `essentia_lowlevel`.
2. Garantir idempotence par track/segment/pipeline_version.
3. Conserver l'agrégation multi-segments existante.
4. Préserver les champs :
   - BPM, beats, loudness, key, mode, key confidence ;
   - MFCC, HPCP, spectral centroid, spectral rolloff, spectral contrast ;
   - dynamic complexity, onset rate.
5. Mettre à jour progression job parent.
6. Déclencher `feature_aggregation` si les conditions sont réunies.
7. Tests :
   - parser low-level non-régression ;
   - worker réserve stage ;
   - résultat écrit ;
   - `/features/tracks/{id}` inchangé ou enrichi ;
   - cleanup attend TensorFlow si requis.

Critères :
- Les tests phase 4 restent verts.
- Pas de régression UI features/library.

Validation :
```bash
cd core
uv run pytest tests/test_essentia_lowlevel* tests/test_track_features_api.py tests/test_analysis_pipeline_lowlevel.py -q
```
