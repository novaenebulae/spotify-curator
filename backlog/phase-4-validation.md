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

Statut : **DONE** (juin 2026)

Preuve : `uv run alembic upgrade head` + `171 passed` pytest local ; `core-api` Docker démarre avec `SQLiteImpl` Alembic au boot ; tables phase 4 couvertes par `tests/test_migrations.py` / contrainte 30s (`tests/test_audio_segments.py`).

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

Statut : **DONE** (juin 2026)

Preuve : `docker compose ps` — `core-api` + profil `audio` (2× `audio-downloader`, 2× `essentia-lowlevel-worker`, 1× `preview-resolver-worker`) ; `GET /workers` → 5 workers (`preview_resolver`, `audio_downloader`×2, `essentia_lowlevel`×2) heartbeats < 30s ; `POST /previews/resolve` `limit=5` → 5/5 items traités (~6s). Scaling = réplicas Compose, pas de conteneur par piste.

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

Statut : **DONE** (juin 2026 — signé utilisateur pour GO phase 5)

Preuve : pytest `test_preview_stream`, `test_preview_resolve_selection`, `test_job_items_preview_resolve`, `test_jobs_cancel_preview_resolve`, `test_deezer_preview_*`, `test_preview_api` ; proxy `GET /tracks/{id}/preview/stream` (CORB) ; cancel `preview_resolve` via `WORKER_MANAGED_JOB_TYPES` + stats partielles ; smoke API OK. Validation manuelle bibliothèque réelle : **acceptée par le porteur produit** (lecture ▶ via proxy local, resolve / Last runs).

### À vérifier

- `POST /api/v1/previews/resolve` ;
- `only_missing=true` n'écrase pas les previews valides ;
- `limit=null` traite toute la bibliothèque manquante ;
- URLs signées rafraîchies avant téléchargement analyse ;
- `GET /api/v1/tracks/{track_id}/preview` fonctionne ;
- `GET /api/v1/previews/coverage` cohérent.

---

## 4V.5 — Validation stratégie segments

Statut : **DONE** (juin 2026)

Preuve : `tests/test_hybrid_segment_strategy.py` (5 décisions documentées) ; `tests/test_audio_segments.py` — `duration_seconds <= 30` en DB.

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

Statut : **DONE** (juin 2026 — GO avec risque résiduel documenté en 4V.9)

Preuve : `tests/test_essentia_parser.py`, `test_essentia_aggregate.py`, `test_essentia_gating_selection.py`, `test_audio_confidence_weights.py`, `test_job_items_progress.py` verts ; workers `essentia_lowlevel` opérationnels (4V.3). Smoke E2E Docker sur 1–3 titres réels : non bloquant pour phase 5 si ReccoBeats déjà présent sur la majorité des titres cibles playlists.

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

Statut : **DONE** (juin 2026)

Preuve : `tests/test_track_features_api.py`, `test_features_coverage.py`, `test_feature_upsert.py` ; smoke `POST /features/merge/recompute` body `{}` → `tracks_processed=10` (seed smoke) ; `GET /features/coverage`, `/jobs/insights/latest` OK.

### À vérifier

- `POST /api/v1/features/merge/recompute` ;
- ReccoBeats et Essentia peuvent coexister ;
- une source active est choisie ;
- `GET /api/v1/features/tracks/{track_id}` retourne `merged` et `sources` ;
- les sources inactives restent visibles ;
- coverage `with_reccobeats` / `with_essentia_lowlevel` cohérent.

---

## 4V.8 — Validation UI

Statut : **DONE** (juin 2026 — signé utilisateur pour GO phase 5)

Preuve : `npm run check` (0 erreurs, 2 warnings a11y CollapsibleSection/DryRunModal) ; `npm run build` OK (~11s). Checklist manuelle Home / Library / Features / Settings : **acceptée par le porteur produit**.

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

Statut : **DONE** — **GO phase 5** (juin 2026, validation porteur produit)

### Synthèse par section

| Section | Statut | Commentaire |
|---------|--------|-------------|
| 4V.1 Documentation | DONE | Docs phase 4 alignées avec code et Compose |
| 4V.2 Migrations / DB | DONE | `0006`–`0007`, contrainte 30s, 171 pytest |
| 4V.3 Workers Docker | DONE | Profil `audio`, 5 heartbeats, jobs `preview_resolve` consommés |
| 4V.4 Previews Deezer | DONE | Proxy stream, cancel stats, tests + validation manuelle |
| 4V.5 Stratégie hybride | DONE | 5 `analysis_decision`, segments ≤ 30s |
| 4V.6 Essentia low-level | DONE | Chaîne testée ; E2E réel optionnel accepté en risque |
| 4V.7 Merge features | DONE | Recompute, coverage, track detail API |
| 4V.8 UI | DONE | `check` + `build` ; parcours utilisateur validé |

### Écarts détectés pendant la validation

| Écart | Gravité | Résolution |
|-------|---------|------------|
| CORB navigateur sur URLs Deezer CDN directes | Bloquant UI | `GET /tracks/{id}/preview/stream` + lecteur via API locale |
| Job `preview_resolve` bloqué `queued` 0% | Bloquant jobs | `reserve_next` joint jobs actifs ; cleanup `job_items` orphelins au boot |
| Cancel `preview_resolve` → stats nulles / « no active worker » | Bloquant UX | `WORKER_MANAGED_JOB_TYPES` + `cancel_pending_for_job` |
| Workers absents de `/workers` pendant charge DB | Bloquant observabilité | Heartbeat idle avant `reserve_next` |
| `POST /features/merge/recompute` sans body → 422 | Mineur smoke | Body `{}` requis (documenté) |
| `ruff check` sur périmètre audio (E501, etc.) | Non bloquant | Dette style préexistante ; hors gate GO |
| 2 warnings a11y Svelte (`CollapsibleSection`, `DryRunModal`) | Mineur | À traiter en polish UI phase 5+ |

### Corrections appliquées (code)

- `core/app/previews/stream.py` + route API preview stream
- `app/frontend/src/lib/previewApi.ts`, `previewPlayer.ts` — lecture via proxy
- `core/app/jobs/items/constants.py` — `WORKER_MANAGED_JOB_TYPES`
- `core/app/jobs/items/service.py` — `reserve_next` + cancel pending
- `core/app/main.py` — `cancel_pending_for_terminal_parent_jobs` au démarrage
- `core/app/workers/base_worker.py` — heartbeat avant réservation file
- Tests : `test_preview_stream`, `test_jobs_cancel_preview_resolve`, `test_job_items_progress`, etc.
- Docs : `06-api-contract`, `10-testing-strategy`, `prompts/phase-4-validation`

### Commandes exécutées

```bash
cd core && uv run alembic upgrade head && uv run pytest -q          # 171 passed
cd core && uv run pytest tests/test_preview_stream.py ...            # sous-ensembles 4V.4–4V.7
cd app/frontend && npm run check && npm run build

docker compose up -d --build core-api
docker compose --profile audio up -d --build \
  --scale audio-downloader=2 --scale essentia-lowlevel-worker=2 \
  --scale preview-resolver-worker=1
curl http://127.0.0.1:8765/api/v1/health
curl http://127.0.0.1:8765/api/v1/workers
curl http://127.0.0.1:8765/api/v1/previews/coverage
curl -X POST http://127.0.0.1:8765/api/v1/previews/resolve -H "Content-Type: application/json" -d '{"limit":5}'
curl -X POST http://127.0.0.1:8765/api/v1/features/merge/recompute -H "Content-Type: application/json" -d "{}"
```

### Tests

| Suite | Résultat |
|-------|----------|
| `pytest` complet (`core`) | **171 passed** |
| `npm run check` | **0 errors** (2 warnings a11y) |
| `npm run build` | **OK** |
| `ruff check` (périmètre phase 4) | Échecs style préexistants — non retenus comme gate |

### Risques restants (acceptés pour phase 5)

1. **`preview_resolve` sur toute la bibliothèque (~5k titres)** — long ; lancer avec `limit` petit puis run complet ; surveiller SQLite sous 5 workers.
2. **Essentia E2E non rejoué sur échantillon réel** dans la passe automatisée — mitigé par tests unitaires/intégration et workers up ; enrichir au fil de l’eau si besoin clustering.
3. **ReccoBeats encore in-process** — hors scope workers 4V.3 ; suffisant pour moteur playlists si données RB déjà importées (phase 3).
4. **Volume Docker** — s’assurer que prod utilise le volume `spotify_curator_data` habituel (ne pas confondre avec DB seed smoke vide).

### Décision

**Recommandation : GO phase 5**

**Critère satisfait :** le moteur de playlists peut consommer `tracks`, `audio_features` (merged + sources), `track_previews` et métadonnées segments sans dépendre d’un pipeline phase 4 instable.

**Signataire :** porteur produit — GO explicite juin 2026.

**Prochaine étape :** démarrer [`backlog/phase-5.md`](phase-5.md) (règles playlists, scoring, dry-run sync Spotify).
