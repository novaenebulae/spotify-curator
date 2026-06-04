# Prompt Cursor — Phase 6.4 — Worker Essentia TensorFlow + model registry


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
Ajouter l'infrastructure TensorFlow sans dépendre immédiatement de modèles lourds réels.

Tâches :
1. Créer `docker/essentia-tensorflow-worker/Dockerfile`.
2. Ajouter service Compose `essentia-tensorflow-worker` sous profil `advanced-analysis`.
3. Créer worker persistant :
   - heartbeat ;
   - réservation stage ;
   - mode `status_only` si modèles absents ;
   - logs redacted ;
   - pas de conteneur par piste.
4. Créer `ModelRegistry` :
   - déclarations modèles attendus ;
   - chemin local ;
   - status `available/missing/invalid_hash/disabled` ;
   - hash sha256 si fichier présent ;
   - endpoint `GET /api/v1/models/status`.
5. Ajouter tests sans modèles réels :
   - registry modèle manquant ;
   - modèle fake présent ;
   - hash invalide ;
   - endpoint status ;
   - worker démarre en mode status_only.

Critères :
- Build Docker possible.
- L'absence des modèles ne casse pas l'application.
- Aucun modèle lourd commité.

Validation :
```bash
cd core
uv run pytest tests/test_model_registry.py tests/test_models_status_api.py -q
docker compose --profile advanced-analysis build essentia-tensorflow-worker
```
