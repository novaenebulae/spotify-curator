# Phase 4 — Validation finale avant phase 5

Tags: #backlog #phase-4 #validation #audio #workers #features

## But

Valider que la phase 4 livrée est suffisamment stable pour servir de socle à la phase 5.

Cette phase de validation ne doit pas ajouter de nouvelles fonctionnalités majeures. Elle doit corriger uniquement les divergences, bugs bloquants ou écarts documentaires détectés.

---

## Definition of Done validation

- Les migrations phase 4 sont appliquées.
- Les workers audio sont démarrables via le profil Compose `audio`.
- Les heartbeats workers sont visibles via `/api/v1/workers`.
- Les previews Deezer sont résolues et affichables en UI.
- Les segments générés respectent `duration_seconds <= 30`.
- Aucun téléchargement complet standard n'est effectué.
- Essentia low-level produit des features exploitables.
- Le merge ReccoBeats / Essentia low-level fonctionne.
- Le cleanup audio fonctionne.
- L'UI Features/Library affiche coverage, failures et last runs.
- Les tests backend passent.
- Les tests frontend minimum passent.
- La documentation phase 4 est cohérente avec le code.

---

## 4V.1 — Audit documentation vs code

Statut : DONE (sync docs juin 2026 — re-vérifier si le code change)

### À vérifier

- `docs/01-architecture.md`
- `docs/05-domain-model.md`
- `docs/06-api-contract.md`
- `docs/07-audio-analysis-pipeline.md`
- `docs/09-ui-specification.md`
- `docs/14-configuration.md`
- `docs/16-job-execution-model-and-worker-parallelism.md`
- `docs/17-audio-preview-and-segment-strategy.md`
- `backlog/phase-4.md`

### Critères

- Les endpoints documentés existent ou sont explicitement marqués cible.
- Les variables `.env` documentées correspondent aux variables réellement lues.
- Les migrations mentionnées existent.
- Les workers mentionnés correspondent aux services Compose.
- Les noms `analysis_decision` documentés correspondent au code.

---

## 4V.2 — Validation migrations et DB

Statut : PARTIAL (pytest local OK ; smoke Docker non exécuté ici)

### À vérifier

- migration `0006_phase4_audio_local` ;
- migration `0007_track_previews_hybrid` ;
- tables `job_items`, `worker_heartbeats`, `job_events` ;
- tables `track_previews`, `track_segments`, `audio_download_jobs`, `audio_analysis_jobs` ;
- contrainte `track_segments.duration_seconds <= 30` ;
- index utiles pour jobs/items/features.

### Commandes indicatives

```bash
cd core
uv run alembic upgrade head
uv run pytest -q
```

---

## 4V.3 — Validation workers Docker

Statut : TODO

### À vérifier

- `core-api` démarre ;
- profil `audio` démarre ;
- `preview-resolver-worker` heartbeat ;
- `audio-downloader` heartbeat ;
- `essentia-lowlevel-worker` heartbeat ;
- scaling workers sans conteneur par piste ;
- logs sans secrets ni fichiers audio persistants.

### Commandes indicatives

```bash
docker compose up -d --build core-api
docker compose --profile audio up -d --build --scale audio-downloader=2 --scale essentia-lowlevel-worker=2
curl http://127.0.0.1:8765/api/v1/workers
```

---

## 4V.4 — Validation previews Deezer

Statut : TODO

### À vérifier

- `POST /api/v1/previews/resolve` ;
- `only_missing=true` n'écrase pas les previews valides ;
- `limit=null` traite toute la bibliothèque manquante ;
- URLs signées rafraîchies avant téléchargement analyse ;
- `GET /api/v1/tracks/{track_id}/preview` fonctionne ;
- `GET /api/v1/previews/coverage` cohérent.

---

## 4V.5 — Validation stratégie segments

Statut : TODO

### Cas à tester

- `analysis_mode=fast` + Deezer disponible → `deezer_only` ;
- `analysis_mode=fast` + Deezer absent + YouTube OK → `youtube_1_segment` ;
- `analysis_mode=precise` + Deezer + YouTube OK → `deezer_plus_youtube_2_segments` ;
- `analysis_mode=precise` + Deezer absent + YouTube OK → `youtube_3_segments` ;
- aucune source → `local_analysis_unavailable` ;
- morceaux courts ;
- aucun segment > 30s.

---

## 4V.6 — Validation analyse Essentia low-level

Statut : TODO

### À vérifier

- planification segments ;
- téléchargement segments ;
- analyse Essentia ;
- parsing JSON ;
- écriture `audio_features` source `essentia_lowlevel` ;
- raw payload conservé si prévu ;
- confidence ;
- `segments_planned` / `segments_analyzed` ;
- cleanup après analyse ;
- failure lisible si yt-dlp/FFmpeg/Essentia échoue.

---

## 4V.7 — Validation merge features

Statut : TODO

### À vérifier

- `POST /api/v1/features/merge/recompute` ;
- ReccoBeats et Essentia peuvent coexister ;
- une source active est choisie ;
- `GET /api/v1/features/tracks/{track_id}` retourne `merged` et `sources` ;
- les sources inactives restent visibles ;
- coverage `with_reccobeats` / `with_essentia_lowlevel` cohérent.

---

## 4V.8 — Validation UI

Statut : TODO

### Pages à tester

- `/` Home — tuiles ReccoBeats / Essentia / Deezer previews ;
- `/library` — colonnes Features RB / Essentia / Preview ;
- `TrackFeaturesDrawer` ;
- preview play Deezer ;
- `/features` — coverage, field coverage, failures, last runs ;
- `/settings` — workers/runtime sans debug dominant.

### Commandes indicatives

```bash
cd app/frontend
npm run check
npm run build
```

---

## 4V.9 — Décision fin phase 4

À la fin de cette validation, produire :

```text
- résumé des écarts trouvés ;
- corrections appliquées ;
- commandes exécutées ;
- tests passés/échoués ;
- risques restants ;
- recommandation GO / NO-GO phase 5.
```

Critère GO phase 5 :

```text
Le moteur de playlists peut consommer les données tracks/features/previews sans dépendre d'un traitement phase 4 instable.
```
