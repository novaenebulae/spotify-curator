# Prompt Cursor — Phase 6.6 — Classifiers avancés et fallbacks


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
Ajouter les features avancées demandées dans le registry, les mappings d'inférence et les fallbacks locaux.

Features à couvrir :
- `approachability`
- `engagement`
- `mood_aggressive_score`
- `mood_happy_score`
- `mood_party_score`
- `mood_relaxed_score`
- `mood_sad_score`
- `electronic_profile_score`
- `danceability_tf`
- `valence_tf`
- `instrumental_focus_score`
- `acoustic_profile_score`
- `energy_proxy`

Tâches :
1. Ajouter descriptors dans `FeatureRegistry`.
2. Créer mappers de sorties modèles :
   - binaire → score 0..1 ;
   - régression arousal/valence → normalisation ;
   - voice/instrumental → vocal/instrumental scores ;
   - acoustic/electronic → profils.
3. Implémenter `energy_proxy` dérivé de low-level :
   - loudness ;
   - dynamic_complexity ;
   - onset/rhythm si disponible ;
   - normalisation documentée.
4. Définir source priority :
   - ReccoBeats prioritaire pour energy/danceability/valence/instrumentalness/acousticness ;
   - fallback local si ReccoBeats absent/incomplet.
5. Tests :
   - mapping de chaque feature ;
   - ReccoBeats présent → conserve ReccoBeats ;
   - ReccoBeats absent → fallback local ;
   - modèle manquant → status `model_missing`.

Critères :
- Toutes les features sont consommables via `TrackFeatureView`.
- Les fallbacks sont explicites et traçables.
- Le playlist engine phase 5 continue de passer.

Validation :
```bash
cd core
uv run pytest tests/test_advanced_feature_mappers.py tests/test_feature_registry.py tests/test_feature_resolver.py tests/test_playlist_* -q
```
