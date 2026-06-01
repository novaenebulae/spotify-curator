# 16 — Job execution model & worker parallelism

Tags: #jobs #workers #docker #parallelism #performance #reccobeats #essentia #sqlite #observability

## Objectif

Définir l'architecture d'exécution des tâches longues de l'application : imports Spotify, enrichissement ReccoBeats, téléchargement de segments audio, analyse Essentia, embeddings, clustering, génération de playlists et synchronisation contrôlée.

Ce document précise :

- la différence entre un **job**, un **work item** et un **worker** ;
- les règles d'exécution parallèle ;
- le rôle de Docker ;
- le modèle recommandé pour ReccoBeats ;
- le modèle recommandé pour Essentia low-level et Essentia TensorFlow ;
- les limites SQLite à respecter ;
- les variables de configuration ;
- les règles UI, tests et observabilité.

Ce document complète :

- `01-architecture.md` ;
- `05-domain-model.md` ;
- `06-api-contract.md` ;
- `07-audio-analysis-pipeline.md` ;
- `10-testing-strategy.md` ;
- `13-error-handling-and-observability.md` ;
- `14-configuration.md` ;
- les backlogs `phase-3.md`, `phase-4.md`, `phase-6.md`, `phase-7.md` et `phase-9.md`.

---

## État actuel vs cible (2026-05)

Ce document décrit la **cible** d'exécution. L'implémentation du dépôt (fin phase 3) est plus limitée :

| Élément | Actuel (repo) | Cible (ce document) |
|---|---|---|
| Services Docker | `core-api` seul ([`docker-compose.yml`](../docker-compose.yml)) | + `job-worker`, `audio-downloader`, workers Essentia, clustering (profils Compose) |
| Exécution des jobs | Thread daemon in-process dans `core-api` ([`core/app/jobs/service.py`](../core/app/jobs/service.py)) | `job_items` + workers dédiés (async ou Docker) |
| Tables `job_items`, `worker_heartbeats`, `job_events` | Absentes | Recommandées phase 3.5+ / 4+ |
| ReccoBeats HTTP | Batch `GET /v1/audio-features?ids=` par chunks ≤40 ([`core/app/reccobeats/client.py`](../core/app/reccobeats/client.py)) | `job_items` + concurrence HTTP parallèle entre chunks |
| API jobs | `GET /api/v1/jobs/{job_id}` uniquement | + liste, cancel, items, workers |
| Reprise après crash | Non (jobs `running` orphelins possibles) | Locks expirés + remise en `pending` |

Voir aussi [`backlog/phase-3.md`](../backlog/phase-3.md) (limites phase 3) et la phase **3.5** optionnelle (batch ReccoBeats) en §21.2.

---

## 1. Principe général

L'application manipule plusieurs traitements longs ou coûteux :

- import Spotify de milliers de titres ;
- import playlists et items paginés ;
- enrichissement ReccoBeats ;
- résolution de source audio ;
- extraction de segments audio temporaires ;
- analyse Essentia low-level ;
- analyse Essentia TensorFlow ;
- génération d'embeddings ;
- clustering UMAP/HDBSCAN ;
- génération de playlists ;
- dry-run et synchronisation Spotify.

Ces traitements ne doivent jamais bloquer l'interface Tauri/Svelte ni les routes HTTP du core.

Le modèle cible est donc :

```text
Tauri / Svelte UI
  ↓ HTTP localhost
core-api FastAPI
  ↓ crée et expose les jobs
SQLite jobs + work items
  ↓ dispatch contrôlé
worker pools
  ├─ API workers : Spotify / ReccoBeats
  ├─ audio downloader workers : yt-dlp / FFmpeg
  ├─ Essentia low-level workers : Docker persistants
  ├─ Essentia TensorFlow workers : Docker persistants
  ├─ clustering workers : CPU-bound
  └─ playlist/sync workers : DB/API-bound
```

Règle fondamentale :

```text
Les routes HTTP créent, annulent, listent ou observent des jobs.
Les workers exécutent les traitements longs.
L'UI ne parle jamais directement à Docker, SQLite ou Essentia.
```

---

## 2. Définitions

### 2.1 Job

Un **job** représente une opération utilisateur ou système suivie par l'application.

**Types implémentés aujourd'hui** (phase 0–3) :

- `spotify_import_liked_tracks` ;
- `spotify_import_playlists` ;
- `docker_runtime_checks` ;
- `reccobeats_enrichment`.

**Types cibles** (phases ultérieures — non implémentés) :

- `audio_download` ;
- `essentia_lowlevel_analysis` ;
- `essentia_tensorflow_analysis` ;
- `embedding_generation` ;
- `clustering_run` ;
- `playlist_preview` ;
- `spotify_sync_dry_run` ;
- `maintenance_cache_cleanup`.

Un job possède :

- un type ;
- un statut ;
- une progression globale ;
- une étape courante ;
- des tentatives ;
- une erreur éventuelle ;
- un résultat final ;
- des timestamps.

Un job peut représenter un lot important, par exemple enrichir 5000 titres via ReccoBeats.

### 2.2 Work item

Un **work item** représente une unité interne d'un job.

Exemples :

- une track à enrichir via ReccoBeats ;
- une track à analyser localement ;
- un segment audio à passer dans Essentia ;
- une ligne de matrice de features ;
- un cluster à recalculer ;
- une playlist candidate à comparer.

Un job peut donc contenir plusieurs milliers de work items.

Recommandation :

```text
1 job = 1 opération utilisateur visible
N work items = unités internes parallélisables
```

### 2.3 Worker

Un **worker** est une unité d'exécution qui prend des work items ou des jobs et les traite.

Il peut être :

- un thread in-process dans `core-api` ;
- une tâche `asyncio` ;
- un processus Python séparé ;
- un service Docker Compose ;
- un conteneur Essentia spécialisé ;
- un worker one-shot pour maintenance.

Le choix dépend du type de charge :

| Type de tâche | Nature | Worker recommandé |
|---|---|---|
| ReccoBeats | I/O-bound HTTP | async workers avec concurrence bornée |
| Spotify import | I/O-bound HTTP + DB | async ou process interne avec rate limit |
| yt-dlp/FFmpeg | I/O + subprocess | worker dédié, concurrence faible |
| Essentia low-level | CPU-bound | conteneurs Docker persistants |
| Essentia TensorFlow | CPU/GPU/RAM-bound | conteneurs Docker persistants, faible concurrence |
| Clustering | CPU/RAM-bound | process séparé ou worker Docker |
| Playlist preview | DB-bound | worker in-process ou sync court |
| Sync Spotify | I/O-bound API | async worker avec rate limit |

---

## 3. États des jobs

Les statuts sont stockés en **SQLite** puis exposés à l'API via un mapping ([`core/app/jobs/status_mapping.py`](../core/app/jobs/status_mapping.py)).

### 3.1 Statuts SQLite (`jobs.status`)

| Statut DB | Signification |
|---|---|
| `queued` | Job créé, pas encore démarré par le thread worker |
| `running` | Job actif |
| `succeeded` | Terminé sans exception bloquante au niveau job |
| `failed` | Terminé en erreur (exception non gérée dans le worker) |
| `rate_limited` | Suspendu (ex. `SpotifyRateLimited` sur imports Spotify) |
| `cancelled` | Annulé (cible ; peu utilisé en phase 3) |

### 3.2 Statuts API JSON (`GET /api/v1/jobs/{id}`)

| Statut API | Source DB |
|---|---|
| `pending` | `queued` |
| `running` | `running` |
| `success` | `succeeded` |
| `failed` | `failed` |
| `rate_limited` | `rate_limited` |
| `cancelled` | `cancelled` |

### 3.3 `partial_success` (cible, non implémenté au niveau job)

Statut API **recommandé** pour les jobs batch avec échecs partiels. **Aujourd'hui** : `reccobeats_enrichment` termine en `succeeded` (DB) / `success` (API) même si des pistes échouent ; les compteurs `succeeded`, `failed`, `not_found`, etc. sont dans `result_json` ([`core/app/features/enrichment.py`](../core/app/features/enrichment.py)).

### 3.4 Règles

- Un job long doit exposer une progression même approximative.
- Un job batch **devrait** pouvoir terminer en `partial_success` (cible).
- Les erreurs réseau doivent être retryables.
- Les erreurs de validation ne doivent pas être retryées automatiquement.
- Les erreurs de parsing doivent être conservées pour diagnostic.
- Un job annulé ne doit pas laisser de ressources temporaires non nettoyées.

---

## 4. Modèle de persistance

### 4.1 Table `jobs`

**Implémentée** (migration `0001_initial`). La table `jobs` reste la table centrale.

Champs attendus :

```text
id
job_type
status
progress_current
progress_total
current_step
attempt_count
max_attempts
next_retry_at
last_error
result_json
created_at
started_at
finished_at
```

### 4.2 Table optionnelle `job_items`

> **Non présent en base** — schéma cible (phase 3.5+).

Pour les traitements batch lourds, ajouter une table `job_items` est recommandé.

Objectifs :

- suivre chaque track/segment individuellement ;
- reprendre après crash ;
- paralléliser proprement ;
- éviter de stocker une énorme liste dans `jobs.result_json` ;
- exposer les échecs détaillés dans l'UI.

Schéma recommandé :

| Champ | Type | Notes |
|---|---|---|
| `id` | PK | UUID ou integer cohérent avec le projet |
| `job_id` | FK jobs indexed | job parent |
| `item_type` | text indexed | track, segment, playlist, cluster |
| `track_id` | FK tracks nullable indexed | si applicable |
| `segment_id` | FK track_segments nullable indexed | si applicable |
| `status` | text indexed | pending/running/success/failed/cancelled/skipped/rate_limited |
| `priority` | int | défaut 0 |
| `attempt_count` | int | tentatives item |
| `max_attempts` | int | tentatives max item |
| `locked_by` | text nullable indexed | worker id |
| `locked_at` | datetime nullable | lock court |
| `next_retry_at` | datetime nullable indexed | retry différé |
| `error_code` | text nullable | erreur normalisée |
| `error_message` | text nullable | erreur lisible |
| `input_json` | text nullable | paramètres item |
| `result_json` | text nullable | résultat léger |
| `created_at` | datetime | |
| `started_at` | datetime nullable | |
| `finished_at` | datetime nullable | |

Index recommandés :

```sql
CREATE INDEX ix_job_items_job_status ON job_items(job_id, status);
CREATE INDEX ix_job_items_available ON job_items(status, next_retry_at, priority);
CREATE INDEX ix_job_items_locked_by ON job_items(locked_by);
```

### 4.3 Table optionnelle `worker_heartbeats`

> **Non présent en base** — schéma cible (phase 4+ / 9).

Pour les workers persistants, ajouter une table `worker_heartbeats` peut aider l'observabilité.

| Champ | Type | Notes |
|---|---|---|
| `id` | PK | |
| `worker_id` | text unique | identifiant stable |
| `worker_type` | text indexed | api/reccobeats/audio/essentia_lowlevel/essentia_tf/clustering |
| `status` | text | starting/idle/running/stopping/error |
| `current_job_id` | FK jobs nullable | |
| `current_item_id` | FK job_items nullable | |
| `hostname` | text nullable | conteneur ou host |
| `process_id` | int nullable | |
| `started_at` | datetime | |
| `last_seen_at` | datetime indexed | heartbeat |
| `metadata_json` | text nullable | version, image, concurrency |

Cette table est utile en phase 4+ et phase 9, notamment pour le rapport système.

### 4.4 Table optionnelle `job_events`

> **Non présent en base** — schéma cible (phase 4+).

Pour debug et observabilité, une table `job_events` peut stocker un historique append-only.

| Champ | Type | Notes |
|---|---|---|
| `id` | PK | |
| `job_id` | FK jobs indexed | |
| `item_id` | FK job_items nullable indexed | |
| `level` | text | info/warning/error/debug |
| `event_type` | text indexed | created/started/progress/retry/rate_limit/failed/completed/cleanup |
| `message` | text | lisible |
| `context_json` | text nullable | redacted |
| `created_at` | datetime indexed | |

Règle : ne jamais stocker tokens, URLs d'autorisation complètes, fichiers audio binaires ou payloads sensibles non redacted dans `job_events`.

---

## 5. Réservation des work items avec SQLite

SQLite peut convenir à une application desktop locale, mais il faut éviter les écritures concurrentes incontrôlées.

### 5.1 Règles SQLite

- Utiliser le volume Docker nommé `spotify_curator_data`.
- Utiliser `SQLITE_JOURNAL_MODE=WAL`.
- Garder les transactions courtes.
- Ne jamais garder une transaction ouverte pendant une requête réseau ou une analyse audio.
- Réserver un item dans une transaction courte, puis traiter hors transaction.
- Écrire les résultats par petits batches.
- Éviter plusieurs gros writers simultanés.

### 5.2 Réservation atomique recommandée

Pseudo-code :

```python
def reserve_next_item(worker_id: str, worker_type: str) -> JobItem | None:
    now = utcnow()
    stale_before = now - timedelta(minutes=10)

    with db.transaction():
        item = db.query("""
            SELECT *
            FROM job_items
            WHERE status IN ('pending', 'rate_limited')
              AND (next_retry_at IS NULL OR next_retry_at <= :now)
              AND (
                locked_by IS NULL
                OR locked_at < :stale_before
              )
            ORDER BY priority DESC, created_at ASC
            LIMIT 1
        """, now=now, stale_before=stale_before).first()

        if item is None:
            return None

        updated = db.execute("""
            UPDATE job_items
            SET status = 'running',
                locked_by = :worker_id,
                locked_at = :now,
                started_at = COALESCE(started_at, :now),
                attempt_count = attempt_count + 1
            WHERE id = :item_id
              AND (
                locked_by IS NULL
                OR locked_at < :stale_before
              )
        """, worker_id=worker_id, now=now, stale_before=stale_before, item_id=item.id)

        if updated.rowcount != 1:
            return None

    return item
```

### 5.3 Écriture des résultats

Pseudo-code :

```python
def mark_item_success(item_id: str, result: dict):
    with db.transaction():
        db.update_job_item(
            id=item_id,
            status='success',
            result_json=result,
            locked_by=None,
            locked_at=None,
            finished_at=utcnow(),
        )
        db.increment_job_progress(job_id)
```

### 5.4 Gestion des locks périmés

Un worker peut mourir pendant un traitement.

Règles :

- chaque item `running` possède `locked_by` et `locked_at` ;
- un lock trop ancien peut être repris ;
- le seuil doit dépendre du type de job ;
- Essentia TensorFlow peut nécessiter un timeout plus long que ReccoBeats.

Exemples :

```env
JOB_ITEM_LOCK_TIMEOUT_SECONDS=600
RECCOBEATS_ITEM_LOCK_TIMEOUT_SECONDS=120
ESSENTIA_LOWLEVEL_ITEM_LOCK_TIMEOUT_SECONDS=900
ESSENTIA_TENSORFLOW_ITEM_LOCK_TIMEOUT_SECONDS=1800
```

---

## 6. Modèles d'exécution

## 6.1 Worker in-process

Un worker in-process tourne dans le même conteneur/processus que `core-api`.

Usage acceptable :

- MVP ;
- jobs peu coûteux ;
- imports simples ;
- dry-runs ;
- ReccoBeats en phase 3 actuelle ;
- tests locaux.

Limites :

- risque de bloquer ou ralentir le core si mal isolé ;
- scaling limité ;
- redémarrage du `core-api` interrompt les threads daemon (pas de reprise automatique des jobs laissés en `running`) ;
- moins adapté aux traitements CPU lourds.

**Comportement phase 3** :

- `JobService.start_background` lance un `threading.Thread` daemon ([`core/app/jobs/service.py`](../core/app/jobs/service.py)).
- `reccobeats_enrichment` : `assert_no_running_job()` refuse un second job du même type si statut `queued` ou `running` ([`core/app/features/enrichment.py`](../core/app/features/enrichment.py)) — **pas** une limite globale sur tous les types de jobs.

Règle : aucun traitement audio lourd ne doit rester durablement dans le process HTTP principal.

## 6.2 Async worker pool

Modèle recommandé pour les APIs externes.

Usage :

- ReccoBeats ;
- Spotify import ;
- Spotify sync dry-run si appels API ;
- autres sources HTTP futures.

Principe :

```text
1 job batch
  ↓
N work items tracks
  ↓
asyncio.Semaphore(concurrency)
  ↓
requêtes HTTP concurrentes bornées
  ↓
retry/backoff/rate limit
  ↓
upsert DB par petits lots
```

Avantages :

- accélère les traitements I/O-bound ;
- ne nécessite pas plusieurs conteneurs ;
- respecte les limites API via sémaphores ;
- simple à tester avec `httpx.MockTransport`.

## 6.3 Process worker

Modèle recommandé pour traitements CPU modérés ou isolables sans Docker spécialisé.

Usage :

- clustering UMAP/HDBSCAN ;
- génération de matrice features ;
- batch DB lourd ;
- opérations de maintenance.

Avantages :

- évite le GIL pour les traitements CPU ;
- isole mieux les crashs ;
- plus léger qu'un conteneur supplémentaire.

## 6.4 Docker worker persistant

Modèle recommandé pour Essentia.

Principe :

```text
docker compose démarre N workers
  ↓
chaque worker reste actif
  ↓
chaque worker réserve un work item
  ↓
le worker exécute Essentia sur un segment ou une track
  ↓
le worker écrit les résultats
  ↓
le worker prend l'item suivant
```

Règle critique :

```text
Ne pas créer/détruire un conteneur Docker pour chaque piste ou segment.
```

Les conteneurs Essentia doivent être **long-lived** pendant une session d'analyse.

Pourquoi :

- réduire le coût de démarrage Docker ;
- éviter de recharger Essentia et TensorFlow à chaque piste ;
- mieux amortir le chargement des modèles ;
- simplifier les logs ;
- permettre un heartbeat worker ;
- faciliter l'annulation contrôlée.

---

## 7. Modèle ReccoBeats

## 7.1 Nature du traitement

ReccoBeats est un traitement principalement **I/O-bound**.

Le temps est majoritairement passé à attendre :

- la résolution Spotify track ID vers ReccoBeats ID ;
- la récupération des audio features ;
- les réponses HTTP ;
- les éventuels retry/rate limits.

Le bon modèle n'est donc pas un pool Docker Essentia, mais un **pool HTTP async borné**.

## 7.2 Pipeline cible (phase 3.5+)

```text
POST /api/v1/features/reccobeats/enrich
  ↓
création job reccobeats_enrichment
  ↓
sélection tracks cibles (Spotify track ID ; ISRC local pour confidence)
  ↓
création job_items track (cible)
  ↓
chunks de ≤40 identifiants
  ↓
GET /v1/audio-features?ids=...  (batch HTTP)
  ↓
(optionnel) GET /v1/track?ids=... si métadonnées manquantes
  ↓
ReccoBeats worker pool (async, concurrence bornée)
  ↓
retry/backoff/429
  ↓
raw payload
  ↓
normalisation
  ↓
upsert audio_features par lots DB
  ↓
coverage
```

## 7.2.1 Endpoint batch ReccoBeats (cible)

API publique ReccoBeats :

```text
GET https://api.reccobeats.com/v1/audio-features?ids={id1},{id2},...
```

- Jusqu'à **40** identifiants par requête (liste comma-separated, URL-encoded).
- IDs acceptés : **ReccoBeats ID**, **Spotify track ID**, **ISRC**.
- Exemple : `.../audio-features?ids=FRPDG1900200%2CFR9W12607777%2CUSIR19801877`

Priorité recommandée par chunk : Spotify track ID si présent en base, sinon ISRC local.

## 7.3 Concurrence et variables (cible phase 3.5+)

> Les clés ci-dessous ne sont **pas** toutes présentes dans [`core/app/settings/config.py`](../core/app/settings/config.py) aujourd'hui. Voir §14 pour les variables réellement lues.

Valeurs de départ recommandées :

```env
RECCOBEATS_WORKER_ENABLED=true
RECCOBEATS_CONCURRENCY=5
RECCOBEATS_HTTP_BATCH_SIZE=40
RECCOBEATS_DB_UPSERT_BATCH_SIZE=50
RECCOBEATS_BATCH_DELAY_MS=250
RECCOBEATS_TIMEOUT_SECONDS=15
RECCOBEATS_MAX_RETRIES=3
RECCOBEATS_RATE_LIMIT_BACKOFF_SECONDS=30
```

| Variable | Rôle |
|---|---|
| `RECCOBEATS_HTTP_BATCH_SIZE` | Taille max d'un appel `GET /v1/audio-features?ids=` (plafond API : 40) |
| `RECCOBEATS_DB_UPSERT_BATCH_SIZE` | Nombre d'upserts SQLite par transaction après réponses HTTP |
| `RECCOBEATS_BATCH_DELAY_MS` | Pause entre chunks HTTP (throttle global) |
| `RECCOBEATS_CONCURRENCY` | Requêtes HTTP parallèles max (si plusieurs chunks en vol) |

Stratégie :

- commencer à `5` requêtes concurrentes ;
- mesurer les erreurs 429 ;
- monter à `8` ou `10` si stable ;
- réduire si l'API rate-limit ;
- respecter systématiquement `Retry-After` si fourni.

## 7.4 Règles retry

| Erreur | Action |
|---|---|
| Timeout | retry avec backoff |
| HTTP 429 | respecter `Retry-After`, passer item/job en `rate_limited` |
| HTTP 5xx | retry limité |
| HTTP 404 track | `not_found`, pas de retry automatique |
| Payload invalide | `failed`, pas de retry sans correction |
| Erreur mapping | `failed` avec payload conservé |

## 7.5 Batching DB

Recommandation :

```text
Requêtes HTTP concurrentes
  ↓
résultats en mémoire courte
  ↓
upsert SQLite par batches de 25 à 100
```

Ne pas ouvrir une transaction SQLite pendant une requête HTTP.

## 7.6 État actuel phase 3.5 (implémenté)

```text
POST /api/v1/features/reccobeats/enrich
  ↓
job reccobeats_enrichment (thread in-process)
  ↓
chargement contexts (spotify_id, isrc, reccobeats_id)
  ↓
pour chaque chunk ≤ RECCOBEATS_HTTP_BATCH_SIZE (défaut 40) :
    GET /v1/audio-features?ids=...
    upsert SQLite (commit par chunk, hors HTTP)
    fallback per-track si entrée manquante
  ↓
pause tous les batch_size pistes (param API, défaut 50)
    via RECCOBEATS_BATCH_DELAY_MS
```

Points importants :

- Le paramètre API `batch_size` contrôle la **fréquence de pause**, pas la taille du batch HTTP.
- Variables : `RECCOBEATS_HTTP_BATCH_SIZE`, `RECCOBEATS_DB_UPSERT_BATCH_SIZE`, `RECCOBEATS_BATCH_DELAY_MS`, etc.

Dette restante :

```text
job_items + pool HTTP async parallèle (§7.2) — non implémenté.
```

---

## 8. Modèle Spotify API

Spotify suit les mêmes principes que ReccoBeats, avec des contraintes de rate limit et pagination.

## 8.1 Import liked/playlists

```text
spotify_import_liked_tracks
  ↓
pagination Spotify
  ↓
normalisation
  ↓
upsert DB par pages
  ↓
progression job
```

Recommandation :

- pagination séquentielle par endpoint ;
- pas de concurrence agressive ;
- respecter `Retry-After` ;
- transactions courtes ;
- progression par page ou par nombre de tracks importées.

## 8.2 Sync Spotify

Les écritures Spotify doivent rester prudentes :

```text
preview local
  ↓
dry-run sync
  ↓
confirmation UI
  ↓
write Spotify borné
  ↓
journalisation action
```

Règles :

- pas d'écriture sans dry-run ;
- pas d'écriture sans scope ;
- pas de parallélisme agressif sur les writes ;
- gérer erreurs partielles ;
- conserver les diffs.

---

## 9. Modèle audio downloader

## 9.1 Nature du traitement

Le téléchargement et la découpe audio sont :

- I/O-bound ;
- dépendants de yt-dlp ;
- dépendants de FFmpeg ;
- potentiellement soumis à erreurs externes ;
- sensibles aux chemins de fichiers ;
- soumis à la contrainte stricte de segments temporaires `<= 30s`.

## 9.2 Pipeline recommandé

```text
audio_download job
  ↓
resolve source
  ↓
plan segments A/B/C
  ↓
yt-dlp download_ranges
  ↓
FFmpeg WAV PCM
  ↓
track_segments
  ↓
handoff vers analyse Essentia
  ↓
cleanup après analyse
```

## 9.3 Concurrence recommandée

Valeurs de départ :

```env
AUDIO_DOWNLOAD_CONCURRENCY=2
AUDIO_DOWNLOAD_MAX_RETRIES=3
AUDIO_DOWNLOAD_BATCH_SIZE=20
AUDIO_SEGMENT_MAX_SECONDS=30
```

Raison :

- yt-dlp/FFmpeg peuvent saturer le disque et le réseau ;
- trop de téléchargements parallèles peuvent provoquer des erreurs ou ralentir Docker Desktop ;
- les segments doivent rester temporaires.

## 9.4 Work item recommandé

Pour le téléchargement :

```text
1 work item = 1 track à résoudre et segmenter
```

Le worker peut produire plusieurs `track_segments` pour une track.

---

## 10. Modèle Essentia low-level

## 10.1 Nature du traitement

Essentia low-level est principalement **CPU-bound** avec I/O fichier.

Il nécessite :

- un environnement Linux stable ;
- l'image Essentia ;
- des fichiers WAV courts ;
- des profils YAML ;
- un parsing JSON ;
- une agrégation multi-segments.

## 10.2 Conteneurs persistants

Le modèle recommandé est un pool de conteneurs workers persistants :

```text
essentia-lowlevel-worker-1 → segment/track A → segment/track E → ...
essentia-lowlevel-worker-2 → segment/track B → segment/track F → ...
essentia-lowlevel-worker-3 → segment/track C → segment/track G → ...
```

Ces workers doivent démarrer une fois, puis traiter plusieurs items.

Interdit par défaut :

```text
1 docker run = 1 track
1 docker run = 1 segment
```

Cette stratégie est trop coûteuse pour une bibliothèque de plusieurs milliers de pistes.

## 10.3 Unité de travail

Deux stratégies sont possibles.

### Option A — 1 work item = 1 track

Le worker :

1. récupère la track ;
2. vérifie ou déclenche les segments ;
3. analyse les segments A/B/C ;
4. parse les JSON ;
5. agrège ;
6. écrit les features finales ;
7. nettoie les segments.

Avantages :

- orchestration simple ;
- progression par track ;
- cleanup plus simple ;
- bonne lisibilité UI.

Inconvénients :

- moins fin si un segment échoue ;
- durée item plus variable.

### Option B — 1 work item = 1 segment

Le worker :

1. prend un segment ;
2. exécute Essentia ;
3. écrit les features segment ;
4. un job agrégateur fusionne les segments.

Avantages :

- parallélisme plus fin ;
- retry segmentaire.

Inconvénients :

- orchestration plus complexe ;
- agrégation obligatoire ;
- cleanup plus délicat.

### Choix recommandé

Pour le MVP phase 4 :

```text
1 work item = 1 track
```

Les segments restent internes à l'item, mais leurs résultats peuvent être stockés dans `track_segments.features_json`.

## 10.4 Concurrence recommandée

Valeurs de départ :

```env
ESSENTIA_LOWLEVEL_WORKERS=2
ESSENTIA_LOWLEVEL_ITEM_MODE=track
ESSENTIA_LOWLEVEL_MAX_RETRIES=2
ESSENTIA_LOWLEVEL_PROFILE=profiles/essentia_lowlevel_basic.yaml
```

Sur machine solide :

```env
ESSENTIA_LOWLEVEL_WORKERS=4
```

Éviter de dépasser le nombre de cœurs disponibles ou de saturer le disque.

## 10.5 Docker Compose

Exemple indicatif :

```yaml
services:
  essentia-lowlevel-worker:
    image: ghcr.io/mtg/essentia:bullseye-v2.1_beta5
    command: ["python", "-m", "app.audio_analysis.lowlevel_worker"]
    volumes:
      - spotify_curator_data:/app/data
      - spotify_curator_cache:/app/cache
      - ./profiles:/app/profiles:ro
    environment:
      DATABASE_URL: sqlite:////app/data/spotify_curator.sqlite
      CACHE_DIR: /app/cache
      ESSENTIA_LOWLEVEL_PROFILE: /app/profiles/essentia_lowlevel_basic.yaml
```

Scaling local :

```bash
docker compose up -d --scale essentia-lowlevel-worker=2
```

Le nom exact du service peut être adapté, mais le principe reste : workers persistants et scalables.

## 10.6 Commande Essentia

Commande type interne au worker :

```bash
essentia_streaming_extractor_music input.wav output.json profile.yaml
```

Règles :

- `input.wav` doit être un segment temporaire `<= 30s` ;
- `output.json` doit être validé avant ingestion ;
- l'erreur Essentia doit être capturée ;
- le JSON peut être conservé en cache technique si utile ;
- les fichiers audio doivent être supprimés après analyse normale.

---

## 11. Modèle Essentia TensorFlow

## 11.1 Nature du traitement

Essentia TensorFlow est plus coûteux que le low-level.

Contraintes :

- modèles lourds ;
- temps de chargement modèle ;
- RAM plus importante ;
- résultats vectoriels ;
- version/hash modèle obligatoires ;
- risque de saturation machine.

## 11.2 Conteneurs persistants obligatoires

Pour TensorFlow, le modèle persistant est encore plus important.

Raison :

```text
charger TensorFlow + modèles pour chaque track serait trop coûteux.
```

Le worker doit charger les modèles une fois au démarrage, puis traiter plusieurs tracks.

## 11.3 Concurrence recommandée

Valeurs de départ :

```env
ESSENTIA_TENSORFLOW_WORKERS=1
ESSENTIA_TENSORFLOW_BATCH_SIZE=8
ESSENTIA_TENSORFLOW_MAX_RETRIES=1
```

Monter à `2` uniquement si :

- la RAM est suffisante ;
- les modèles ne saturent pas le CPU ;
- les temps diminuent réellement ;
- aucun crash TensorFlow n'apparaît.

## 11.4 Unité de travail

Recommandation :

```text
1 work item = 1 track
```

Le worker peut analyser plusieurs segments ou un segment représentatif selon la stratégie retenue.

Pour les embeddings :

- stocker source ;
- stocker model name ;
- stocker version ;
- stocker hash ;
- stocker dimension ;
- stocker vector JSON ou chemin cache si trop lourd.

---

## 12. Modèle clustering

Le clustering UMAP/HDBSCAN est CPU/RAM-bound et dépend de la matrice de features.

## 12.1 Pipeline

```text
clustering_run job
  ↓
select tracks
  ↓
build feature matrix
  ↓
impute missing values
  ↓
normalize
  ↓
UMAP
  ↓
HDBSCAN
  ↓
persist clusters + memberships
  ↓
UI similarity map
```

## 12.2 Concurrence

Recommandation :

```env
CLUSTERING_WORKERS=1
```

Raison :

- UMAP/HDBSCAN peut consommer beaucoup de RAM ;
- lancer plusieurs clusterings simultanés est rarement utile ;
- un seul run contrôlé est plus prévisible.

## 12.3 Annulation

Un job clustering doit pouvoir être marqué `cancelled`, mais l'arrêt effectif dépendra de l'implémentation.

Règle MVP :

- ne pas lancer un nouveau clustering si un clustering est déjà `running` ;
- afficher `JOB_ALREADY_RUNNING`.

---

## 13. Génération de playlists et sync

## 13.1 Playlist preview

La génération de preview est généralement DB-bound et peut rester in-process si elle est rapide.

Si les règles deviennent lourdes :

```text
playlist_preview job
  ↓
query candidates
  ↓
strict filters
  ↓
scoring
  ↓
diversity constraints
  ↓
ordering
  ↓
persist generated_playlist_items
```

Concurrence recommandée :

```env
PLAYLIST_PREVIEW_WORKERS=1
```

## 13.2 Spotify sync

La sync réelle ou dry-run API doit être prudente :

```env
SPOTIFY_SYNC_CONCURRENCY=1
SPOTIFY_SYNC_MAX_RETRIES=3
```

Règles :

- dry-run obligatoire ;
- confirmation UI obligatoire pour write ;
- respecter scopes ;
- respecter rate limits ;
- gérer erreurs partielles.

---

## 14. Configuration

### 14.0 Variables lues aujourd'hui (phase 3)

Présentes dans [`.env.example`](../.env.example) et [`core/app/settings/config.py`](../core/app/settings/config.py) :

```env
JOB_DEFAULT_MAX_ATTEMPTS=3
RECCOBEATS_BASE_URL=https://api.reccobeats.com
RECCOBEATS_TIMEOUT_SECONDS=15
RECCOBEATS_MAX_RETRIES=3
RECCOBEATS_BATCH_DELAY_MS=100
RECCOBEATS_ENRICH_DEFAULT_LIMIT=5000
RECCOBEATS_ENRICH_MAX_LIMIT=10000
```

`JOB_POLL_INTERVAL_MS` figure dans `.env.example` mais **n'est pas utilisée** par le code actuel.

### 14.1 Configuration cible (à ajouter progressivement)

Bloc recommandé pour `.env.example` (phase 3.5+ / 4+) — **la plupart des clés ci-dessous ne sont pas encore lues par le core** :

```env
# Jobs global
JOB_DEFAULT_MAX_ATTEMPTS=3
JOB_POLL_INTERVAL_MS=1000
JOB_WORKER_HEARTBEAT_INTERVAL_SECONDS=10
JOB_ITEM_LOCK_TIMEOUT_SECONDS=600
JOB_MAX_ACTIVE_JOBS=3
JOB_ENABLE_ITEM_TABLE=true

# API worker pools
API_WORKER_ENABLED=true
API_WORKER_CONCURRENCY=5
API_WORKER_BATCH_SIZE=100

# Spotify API
SPOTIFY_API_CONCURRENCY=2
SPOTIFY_API_MAX_RETRIES=3
SPOTIFY_API_RATE_LIMIT_BACKOFF_SECONDS=30

# ReccoBeats
RECCOBEATS_WORKER_ENABLED=true
RECCOBEATS_CONCURRENCY=5
RECCOBEATS_HTTP_BATCH_SIZE=40
RECCOBEATS_DB_UPSERT_BATCH_SIZE=50
RECCOBEATS_BATCH_DELAY_MS=250
RECCOBEATS_TIMEOUT_SECONDS=15
RECCOBEATS_MAX_RETRIES=3
RECCOBEATS_RATE_LIMIT_BACKOFF_SECONDS=30
RECCOBEATS_ITEM_LOCK_TIMEOUT_SECONDS=120

# Audio download
AUDIO_DOWNLOAD_WORKERS=2
AUDIO_DOWNLOAD_CONCURRENCY=2
AUDIO_DOWNLOAD_MAX_RETRIES=3
AUDIO_DOWNLOAD_BATCH_SIZE=20
AUDIO_SEGMENT_MAX_SECONDS=30
AUDIO_KEEP_SEGMENTS_AFTER_ANALYSIS=false
AUDIO_DEBUG_KEEP_FAILED_SEGMENTS=false

# Essentia low-level
ESSENTIA_LOWLEVEL_WORKERS=2
ESSENTIA_LOWLEVEL_ITEM_MODE=track
ESSENTIA_LOWLEVEL_MAX_RETRIES=2
ESSENTIA_LOWLEVEL_PROFILE=/app/profiles/essentia_lowlevel_basic.yaml
ESSENTIA_LOWLEVEL_ITEM_LOCK_TIMEOUT_SECONDS=900

# Essentia TensorFlow
ESSENTIA_TENSORFLOW_WORKERS=1
ESSENTIA_TENSORFLOW_BATCH_SIZE=8
ESSENTIA_TENSORFLOW_MAX_RETRIES=1
ESSENTIA_TENSORFLOW_ITEM_LOCK_TIMEOUT_SECONDS=1800

# Clustering
CLUSTERING_WORKERS=1
CLUSTERING_MAX_ACTIVE_RUNS=1

# Playlist engine
PLAYLIST_PREVIEW_WORKERS=1
PLAYLIST_DRY_RUN_REQUIRED=true

# Observability
JOB_EVENTS_ENABLED=true
JOB_EVENTS_RETENTION_DAYS=30
WORKER_HEARTBEATS_ENABLED=true
```

### 14.2 Valeurs par défaut recommandées (cible)

Pour une machine Windows standard :

```text
ReccoBeats concurrency: 5
Spotify API concurrency: 2
Audio download workers: 2
Essentia low-level workers: 2
Essentia TensorFlow workers: 1
Clustering workers: 1
```

Pour un PC puissant :

```text
ReccoBeats concurrency: 8-10 si pas de 429
Audio download workers: 2-3
Essentia low-level workers: 4
Essentia TensorFlow workers: 1-2 selon RAM
```

---

## 15. API jobs

Préfixe API : `/api/v1/jobs`.

### 15.0 État d'implémentation (phase 3)

| Endpoint | Statut |
|---|---|
| `GET /api/v1/jobs/{job_id}` | **Implémenté** ([`core/app/api/v1/jobs.py`](../core/app/api/v1/jobs.py)) |
| `GET /api/v1/jobs` | Documenté dans [`06-api-contract.md`](06-api-contract.md), **non implémenté** |
| `POST /api/v1/jobs/{job_id}/cancel` | Idem, **non implémenté** |
| `GET /api/v1/jobs/{job_id}/items` | Cible phase 3.5+ |
| `GET /api/v1/jobs/{job_id}/events` | Cible phase 4+ |
| `GET /api/v1/workers` | Cible phase 4+ |

La réponse actuelle de `GET /jobs/{id}` correspond à `JobStatus.to_api_dict()` (pas de champs `workers` ni `items`).

## 15.1 Endpoints minimum (cible complète)

```text
GET /jobs
GET /jobs/{job_id}
POST /jobs/{job_id}/cancel
```

## 15.2 Endpoints utiles phase 4+

```text
GET /jobs/{job_id}/items
GET /jobs/{job_id}/events
GET /workers
GET /workers/{worker_id}
```

## 15.3 Réponse cible enrichie `GET /jobs/{job_id}` (phase 3.5+)

```json
{
  "id": "job_123",
  "job_type": "reccobeats_enrichment",
  "status": "running",
  "progress_current": 240,
  "progress_total": 5000,
  "current_step": "fetching_audio_features",
  "attempt_count": 1,
  "max_attempts": 3,
  "next_retry_at": null,
  "last_error": null,
  "result": {},
  "workers": {
    "active": 5,
    "idle": 0,
    "failed": 0
  },
  "items": {
    "pending": 4700,
    "running": 5,
    "success": 240,
    "failed": 55,
    "rate_limited": 0
  },
  "created_at": "2026-05-29T10:00:00Z",
  "started_at": "2026-05-29T10:00:02Z",
  "finished_at": null
}
```

## 15.4 Réponse cible `GET /workers` (phase 4+)

```json
{
  "items": [
    {
      "worker_id": "reccobeats-worker-1",
      "worker_type": "reccobeats",
      "status": "running",
      "current_job_id": "job_123",
      "current_item_id": "item_456",
      "last_seen_at": "2026-05-29T10:15:00Z",
      "metadata": {
        "concurrency": 5,
        "version": "0.1.0"
      }
    }
  ]
}
```

---

## 16. UI jobs et workers

## 16.1 Principes UI

L'UI doit afficher les jobs de manière compréhensible, sans exposer les détails techniques par défaut.

À afficher :

- type de job ;
- statut ;
- progression ;
- étape courante ;
- nombre de réussites/échecs ;
- bouton retry si applicable ;
- bouton cancel si possible ;
- résumé des workers actifs.

À replier :

- raw JSON ;
- logs techniques ;
- stack traces ;
- payloads externes ;
- IDs internes longs.

## 16.2 GlobalJobProgress

Composant recommandé :

```text
GlobalJobProgress
  active jobs count
  most recent running job
  progress bar
  link to details
```

## 16.3 Écran Features

Pour ReccoBeats :

```text
ReccoBeats enrichment
- coverage
- missing tracks
- failed tracks
- active job
- concurrency setting read-only display
- retry failed
```

Exemple :

```text
ReccoBeats enrichment running
241 / 5000 tracks processed
5 concurrent requests
12 failed · 0 rate-limited
```

## 16.4 Écran Audio analysis

Pour Essentia :

```text
Local audio analysis
- segments planned
- segments downloaded
- low-level analysis progress
- TensorFlow analysis progress
- cleanup status
- active workers
```

Exemple :

```text
Essentia low-level running
2 workers active
118 / 5000 tracks analyzed
Temporary audio cleanup enabled
```

## 16.5 Settings

Ajouter une section `Workers & jobs` :

- active jobs ;
- worker pools ;
- configured concurrency ;
- Docker services status ;
- last heartbeat ;
- failed jobs ;
- button `Run diagnostics`.

Les réglages avancés peuvent rester en lecture seule au début et être modifiés via `.env`.

---

## 17. Observabilité

## 17.1 Logs

Chaque worker doit logger :

- startup ;
- shutdown ;
- heartbeat ;
- item reserved ;
- item success ;
- item failed ;
- retry scheduled ;
- rate limit ;
- cleanup result.

Format recommandé :

```json
{
  "level": "INFO",
  "event": "job_item_success",
  "job_id": "job_123",
  "item_id": "item_456",
  "worker_id": "essentia-lowlevel-worker-1",
  "track_id": 42,
  "duration_ms": 1830
}
```

## 17.2 Métriques minimum

À calculer dans le rapport système ou l'UI :

- jobs running ;
- jobs failed ;
- items success/failed/rate_limited ;
- durée moyenne par item ;
- débit tracks/minute ;
- workers actifs ;
- workers sans heartbeat récent ;
- taille cache audio ;
- derniers échecs.

## 17.3 Redaction

Les logs et événements ne doivent jamais contenir :

- tokens OAuth ;
- refresh tokens ;
- code OAuth ;
- URL complète d'autorisation ;
- fichiers audio binaires ;
- payload complet si debug désactivé ;
- chemins personnels inutiles.

---

## 18. Annulation et reprise

## 18.1 Annulation

Un job annulé doit :

1. passer `jobs.status` à `cancelled` ;
2. empêcher la réservation de nouveaux items ;
3. laisser finir ou interrompre proprement les items en cours selon le worker ;
4. nettoyer les fichiers temporaires ;
5. enregistrer un événement `cancelled`.

## 18.2 Reprise après crash

Au démarrage du core ou d'un worker :

- détecter les jobs `running` sans heartbeat récent ;
- libérer les locks expirés ;
- remettre les items `running` expirés en `pending` si retry possible ;
- marquer `failed` si max attempts atteint ;
- recalculer la progression du job.

## 18.3 Idempotence

Chaque worker doit être idempotent.

Exemples :

- ReccoBeats upsert par `track_id + feature_source_id` ;
- Essentia ne duplique pas les features actives ;
- embeddings remplacent ou versionnent selon modèle/hash ;
- cleanup peut être relancé sans erreur si fichier déjà absent.

---

## 19. Sécurité et confidentialité

Les workers respectent les règles générales du projet :

- pas de stockage audio permanent par défaut ;
- pas de commit cache/models/logs/exports ;
- pas de secrets dans l'UI ;
- pas de tokens dans les logs ;
- segments audio `<= 30s` ;
- suppression audio après analyse ;
- dry-run obligatoire pour actions Spotify destructives.

Spécifique aux workers :

- un worker ne doit pas écrire hors des volumes prévus ;
- un worker ne doit pas exposer un port réseau inutile ;
- un worker Docker ne doit pas binder `0.0.0.0` ;
- les modèles doivent être dans `models/`, non commités ;
- les chemins stockés en DB doivent être relatifs au volume si possible.

---

## 20. Tests

## 20.1 Tests unitaires

À ajouter :

- création job ;
- création job_items ;
- réservation atomique ;
- lock expiré ;
- retry item ;
- progression job ;
- cancellation ;
- idempotence upsert ;
- rate limit handling ;
- worker heartbeat.

## 20.2 Tests ReccoBeats

- concurrence bornée avec `httpx.MockTransport` ;
- timeout ;
- retry 5xx ;
- respect 429/Retry-After ;
- `partial_success` ;
- retry failed ;
- pas de transaction DB pendant HTTP.

## 20.3 Tests Essentia

- worker démarre ;
- réserve un item ;
- exécute un WAV court ;
- produit un JSON ;
- parse les features ;
- écrit le résultat ;
- cleanup audio ;
- failure si JSON invalide ;
- pas de conteneur par track.

## 20.4 Tests Docker smoke

Commandes indicatives :

```bash
docker compose up -d core-api
curl http://127.0.0.1:8765/api/v1/health

docker compose up -d --scale essentia-lowlevel-worker=2
curl http://127.0.0.1:8765/api/v1/workers
```

## 20.5 Tests performance

Scénarios à mesurer :

- ReccoBeats 100 tracks avec concurrence 1/5/10 ;
- Essentia low-level 10 tracks avec 1/2/4 workers ;
- audio download 10 tracks avec 1/2 workers ;
- impact SQLite WAL vs bind mount ;
- durée moyenne par item ;
- taux d'échec et retry.

---

## 21. Phasage recommandé

## 21.1 Phase 3 — ReccoBeats (livré)

Implémentation actuelle documentée en §7.6. Limites : [`backlog/phase-3.md`](../backlog/phase-3.md).

```text
Actuel : worker in-process, batch HTTP audio-features par chunks ≤40.
Dette : job_items + pool HTTP async parallèle entre chunks.
```

## 21.2 Phase 3.5 — Optimisation ReccoBeats batch (livré)

Livrables réalisés :

1. Client batch `GET /v1/audio-features?ids=` (≤40 ids) — §7.2.1.
2. Enrichissement par chunks HTTP + commit DB par chunk (sans transaction pendant HTTP).
3. Fallback per-track via ancien flux si entrée batch absente.
4. Tests mock + doc [`07-audio-analysis-pipeline.md`](07-audio-analysis-pipeline.md), [`backlog/phase-3.md`](../backlog/phase-3.md) §3.5.

Non livré (cible ultérieure) : `job_items`, `RECCOBEATS_CONCURRENCY`, `partial_success` job.

## 21.3 Phase 4 — Audio low-level

Ajouter :

- `audio_download_jobs` ;
- `track_segments` ;
- `audio_analysis_jobs` ;
- worker audio downloader ;
- worker Essentia low-level persistant ;
- cleanup robuste ;
- tests smoke Docker.

## 21.4 Phase 6 — Clustering

Ajouter :

- worker clustering unique ;
- job progress ;
- cancellation minimale ;
- persistance des runs.

## 21.5 Phase 7 — Essentia TensorFlow

Ajouter :

- image custom TensorFlow ;
- worker persistant ;
- modèles chargés au démarrage ;
- embeddings et moods ;
- hash/version modèle ;
- tests vector shape.

## 21.6 Phase 9 — Packaging

Ajouter :

- démarrage Docker guidé ;
- diagnostic workers ;
- rapport système ;
- cleanup cache ;
- documentation utilisateur.

---

## 22. Critères d'acceptation globaux

Une implémentation de jobs/workers est acceptée si :

- l'UI reste réactive pendant les traitements ;
- les jobs longs exposent leur progression ;
- les erreurs sont lisibles ;
- les retry sont contrôlés ;
- les rate limits sont respectés ;
- les workers Docker sont persistants ;
- aucun conteneur n'est créé/détruit par piste en mode normal ;
- les fichiers audio temporaires sont supprimés ;
- SQLite reste dans un volume Docker nommé avec WAL ;
- les transactions restent courtes ;
- les workers sont configurables ;
- la concurrence a des limites par défaut raisonnables ;
- les tests mockés et smoke passent ;
- la documentation impactée est mise à jour.

---

## 23. Décision d'architecture

Décision :

```text
Adopter un modèle hybride :
- jobs persistés en SQLite ;
- job_items pour les traitements batch ;
- workers API async pour ReccoBeats/Spotify ;
- workers Docker persistants pour Essentia ;
- concurrence configurable par type de traitement ;
- SQLite WAL en volume Docker nommé ;
- UI centrée sur progression, retry et erreurs lisibles.
```

Raisons :

- bibliothèque cible de plusieurs milliers de titres ;
- nécessité de ne pas bloquer l'UI ;
- ReccoBeats lent si strictement séquentiel ;
- Essentia coûteux à initialiser ;
- Docker est nécessaire pour fiabiliser Essentia sur Windows ;
- SQLite reste acceptable si les écritures sont courtes et bornées ;
- le modèle reste compatible MVP et phases avancées.

Conséquence :

```text
Les futures phases doivent traiter les tâches longues comme des jobs observables, annulables, relançables et parallélisables avec limites explicites.
```
