# 16 — Job execution model & worker parallelism

Tags: #jobs #workers #docker #parallelism #pipeline #essentia #tensorflow #sqlite

## Objectif

Définir l'architecture d'exécution des tâches longues : imports Spotify, ReccoBeats, téléchargement de segments, analyses Essentia low-level/TensorFlow, embeddings, clustering, playlists et maintenance.

Depuis la phase 6, le modèle audio devient un pipeline de stages parallèles.

---

## Décision phase 6

Ancien flux :

```text
download all segments
  ↓
analyze all segments low-level
  ↓
later: analyze advanced
```

Nouveau flux :

```text
download segment/track
  ↓ segment_ready
  ├─ low-level analysis
  └─ TensorFlow analysis
  ↓
aggregate features
  ↓
cleanup when all consumers are done
```

---

## Règles fondamentales

- Les routes HTTP créent, annulent, listent ou observent des jobs.
- Les workers exécutent les traitements longs.
- L'UI ne parle jamais directement à Docker, SQLite ou Essentia.
- Les workers Docker sont persistants.
- Aucun conteneur n'est créé/détruit par piste en mode normal.
- SQLite reste acceptable si les transactions sont courtes et si WAL + volume Docker nommé sont utilisés.
- Les traitements indépendants peuvent être parallélisés, mais avec concurrence bornée.

---

## Types de jobs phase 6

| Job type | Rôle |
|---|---|
| `audio_analysis_pipeline` | Job parent qui orchestre téléchargement + low-level + TensorFlow |
| `audio_download` | Job legacy compatible ou sous-job de téléchargement |
| `essentia_lowlevel_analysis` | Analyse low-level existante |
| `essentia_tensorflow_analysis` | Analyse avancée TensorFlow |
| `embedding_generation` | Peut être stage séparé ou inclus dans TensorFlow |
| `feature_aggregation` | Agrégation finale par track |
| `audio_cleanup` | Nettoyage segments temporaires |

---

## Stages recommandés

| Stage | Dépendance | Parallélisable | Worker |
|---|---|---:|---|
| `segment_download` | aucune | oui | `audio-downloader` |
| `essentia_lowlevel` | `segment_download` | oui | `essentia-lowlevel-worker` |
| `essentia_tensorflow_embeddings` | `segment_download` | oui | `essentia-tensorflow-worker` |
| `essentia_tensorflow_classifiers` | embeddings ou segment selon modèle | oui, borné | `essentia-tensorflow-worker` |
| `feature_aggregation` | low-level et/ou TensorFlow terminés | oui par track | core/worker |
| `audio_cleanup` | consommateurs terminés | oui | core/worker |

---

## Statuts de stage

```text
pending
running
success
failed
skipped
blocked
cancelled
rate_limited
```

### Règles

- `blocked` signifie qu'une dépendance nécessaire n'est pas terminée.
- `skipped` est acceptable pour un modèle absent ou une feature désactivée.
- Un échec TensorFlow ne doit pas invalider les résultats low-level.
- Un job global peut être `partial` si certaines tracks ont échoué mais d'autres ont produit des features.

---

## Réservation SQLite

Les workers doivent réserver un item/stage dans une transaction courte, puis relâcher la transaction avant de faire :

- requête réseau ;
- yt-dlp ;
- FFmpeg ;
- Essentia ;
- TensorFlow.

Pseudo-règle :

```text
reserve stage item in DB
  ↓ commit
execute expensive work outside DB transaction
  ↓
write result in short DB transaction
```

---

## Cleanup multi-consommateurs

Un segment ne doit pas être supprimé dès que low-level réussit si TensorFlow doit encore le lire.

Recommandation :

```text
segment_consumers:
  - essentia_lowlevel
  - essentia_tensorflow_embeddings
  - essentia_tensorflow_classifiers
```

Cleanup autorisé si tous les consommateurs requis sont dans :

```text
success
skipped
failed_terminal
```

---

## Concurrence recommandée

Valeurs de départ :

```env
AUDIO_DOWNLOAD_WORKERS=2
ESSENTIA_LOWLEVEL_WORKERS=2
ESSENTIA_TENSORFLOW_WORKERS=1
ESSENTIA_TENSORFLOW_BATCH_SIZE=8
CLUSTERING_WORKERS=1
```

Sur machine puissante :

```env
AUDIO_DOWNLOAD_WORKERS=2-3
ESSENTIA_LOWLEVEL_WORKERS=3-4
ESSENTIA_TENSORFLOW_WORKERS=1-2 selon RAM
```

---

## Observabilité UI

L'UI doit afficher :

- jobs actifs ;
- workers actifs ;
- queue pending/running/success/failed par stage ;
- modèles disponibles/manquants ;
- tracks/minute ;
- failures récents ;
- état cleanup.

Exemple :

```text
Advanced analysis running
Downloader: 2 active
Low-level: 2 active
TensorFlow: 1 active
Downloaded: 120 / 5000
Low-level done: 96
TF done: 58
Failed: 4
Cleanup pending: 62
```

---

## API recommandée

```text
GET /api/v1/jobs
GET /api/v1/jobs/{job_id}
GET /api/v1/jobs/{job_id}/items
GET /api/v1/jobs/{job_id}/events
POST /api/v1/jobs/{job_id}/cancel
GET /api/v1/workers
GET /api/v1/models/status
```

---

## Tests

- réservation atomique ;
- lock expiré ;
- retry stage ;
- cancellation job ;
- handoff downloader → analyzers ;
- cleanup multi-consommateurs ;
- worker heartbeat ;
- job progress global ;
- partial success ;
- SQLite WAL non bloquant ;
- smoke Docker workers persistants.

---

## Critères d'acceptation

- L'UI reste réactive.
- Les jobs longs exposent leur progression.
- Les erreurs sont lisibles.
- Les retry sont contrôlés.
- Les workers Docker sont persistants.
- Les segments temporaires sont supprimés.
- Les modèles manquants ne cassent pas le pipeline.
- Les tests mockés et smoke passent.
