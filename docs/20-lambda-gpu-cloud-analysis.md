# 20 — Exécution cloud GPU sur Lambda Labs pour l’analyse audio avancée

## 1. Objectif

Ce document décrit le workflow recommandé pour exécuter l’analyse audio avancée du projet Spotify Curator sur une instance GPU Lambda Labs, avec une base SQLite **créée directement sur Lambda**.

Le but est :

```text
1. Créer une VM GPU Lambda.
2. Cloner le projet.
3. Créer une base SQLite vierge sur le SSD local Lambda.
4. Se reconnecter à Spotify via l’UI, avec tunnel SSH.
5. Importer la bibliothèque Spotify dans la base Lambda.
6. Télécharger les modèles Essentia depuis l’UI du projet.
7. Lancer l’analyse audio avancée.
8. Exporter uniquement la base SQLite finale.
9. Récupérer cette base sur le PC local.
```

Le workflow n’impose donc plus d’envoyer une base SQLite locale vers Lambda. L’ancien chemin [`restore-input.sh`](../scripts/lambda/restore-input.sh) devient uniquement un mode de restauration/import optionnel (voir §16).

**Fichiers implémentés** : [`.env.lambda.example`](../.env.lambda.example), [`docker-compose.gpu.yml`](../docker-compose.gpu.yml), [`docker-compose.lambda.yml`](../docker-compose.lambda.yml), [`Makefile`](../Makefile), [`scripts/lambda/`](../scripts/lambda/) (dont [`init-empty-db.sh`](../scripts/lambda/init-empty-db.sh)), [`docker/frontend/Dockerfile`](../docker/frontend/Dockerfile).

**Cibles Makefile** :

| Cible | Rôle |
|-------|------|
| `make lambda-init-empty-db` | Base SQLite vierge + migrations |
| `make lambda-build` | Build images (TF target `gpu`) |
| `make lambda-up` / `lambda-up-a100` | Stack stable (1 worker TF) |
| `make lambda-up-a100-tf2` / `lambda-up-tf2` | 2 workers TF (après benchmark) |
| `make lambda-up-a10` | Même scale que A100 stable |
| `make lambda-check-gpu` | Vérif Essentia TensorFlow + `nvidia-smi` |
| `make lambda-up-a100-ui` | Stack + frontend VM (optionnel) |
| `make lambda-export` | Export final vers NFS |
| `make lambda-migrate-sqlite-to-postgres` | Copie SQLite → Postgres (workers arrêtés) |
| `make lambda-up-a10-stable-tf6-pg` | 6 TF + Postgres sidecar (SSD local) |

### PostgreSQL sidecar (jobs >5k pistes)

Pour supprimer le plafond **single-writer** SQLite avec 15+ workers :

1. `make lambda-migrate-sqlite-to-postgres` — backup NFS, Alembic PG, copie batch, bascule `.env.lambda`
2. `DATABASE_URL=postgresql+psycopg://spotify:spotify@postgres:5432/spotify_curator`
3. Données Postgres sur `/home/ubuntu/spotify-curator-runtime/postgres-data` (SSD, pas NFS)
4. Benchmark : `scripts/measure_full_pipeline_benchmark.py --database-url postgresql+psycopg://...`

Retour SQLite : restaurer `.env.lambda.sqlite.bak` puis `make lambda-up-a10-stable-tf6`.

---

## 2. Choix GPU : A100 vs A10

Aucune A6000 n’étant disponible, les deux options pertinentes sont A100 et A10.

### Recommandation directe

```text
Choix recommandé : A100
Fallback : A10 si A100 indisponible ou trop cher
```

### Pourquoi A100 est préférable

L’A100 est un GPU datacenter conçu pour les charges TensorFlow/IA. Il dispose de beaucoup plus de bande passante mémoire et de Tensor Cores plus adaptés. Selon NVIDIA, l’A100 40/80 GB utilise de la mémoire HBM2/HBM2e avec une bande passante pouvant atteindre environ 1,5 à 2,0 TB/s selon le modèle. L’A10 dispose de 24 GB GDDR6 et d’environ 600 GB/s de bande passante mémoire.

Pour le projet Spotify Curator, cela signifie :

```text
A100 :
- meilleur choix pour essentia_tensorflow ;
- plus stable avec plusieurs modèles TensorFlow ;
- meilleure marge VRAM ;
- meilleure chance de supporter 2 workers TF ;
- potentiellement 3 workers sur A100 80 GB, après benchmark.

A10 :
- probablement plus rapide que ton CPU local ;
- moins cher si disponible ;
- VRAM limitée à 24 GB ;
- 1 worker TF recommandé ;
- 2 workers seulement si benchmark validé et VRAM suffisante.
```

### Estimation réaliste

Les gains exacts dépendent du conteneur TensorFlow GPU, du nombre de segments, du profil modèle et du temps CPU autour de l’inférence.

Estimation prudente :

```text
A10 :
- nettement plus rapide que CPU local ;
- probablement moins bon qu’A100 ;
- recommandé si le budget est prioritaire.

A100 :
- meilleur débit TensorFlow ;
- meilleur choix si tu veux minimiser le temps total ;
- probablement meilleur rapport temps/simplicité si le prix reste acceptable.
```

Règle économique simple :

```text
Si l’A100 coûte moins de 2x à 2,5x le prix de l’A10, choisir A100.
Si l’A100 coûte beaucoup plus cher ou n’est disponible qu’en grosse configuration multi-GPU, choisir A10.
```

---

## 3. Workers recommandés selon GPU

Le goulot étant `essentia_tensorflow`, il ne sert pas à surdimensionner le téléchargement. Il faut surtout garder le GPU alimenté sans saturer SQLite, CPU ou réseau.

### A100 — configuration stable

```env
ESSENTIA_TENSORFLOW_WORKERS=1
ESSENTIA_LOWLEVEL_WORKERS=1
AUDIO_DOWNLOAD_WORKERS=2
PREVIEW_RESOLVER_WORKERS=1
AUDIO_DOWNLOAD_CONCURRENCY=2

ESSENTIA_TF_BATCH_SIZE=1
ESSENTIA_TF_WARMUP=false
TF_FORCE_GPU_ALLOW_GROWTH=true
TF_NUM_INTRAOP_THREADS=4
TF_NUM_INTEROP_THREADS=2
OMP_NUM_THREADS=4
```

### A100 — configuration optimisée à tester

```env
ESSENTIA_TENSORFLOW_WORKERS=2
ESSENTIA_LOWLEVEL_WORKERS=1
AUDIO_DOWNLOAD_WORKERS=2
PREVIEW_RESOLVER_WORKERS=1
AUDIO_DOWNLOAD_CONCURRENCY=2

ESSENTIA_TF_BATCH_SIZE=1
ESSENTIA_TF_WARMUP=false
TF_FORCE_GPU_ALLOW_GROWTH=true
TF_NUM_INTRAOP_THREADS=2
TF_NUM_INTEROP_THREADS=1
OMP_NUM_THREADS=2
```

### A100 80 GB — configuration expérimentale

```env
ESSENTIA_TENSORFLOW_WORKERS=3
ESSENTIA_LOWLEVEL_WORKERS=1
AUDIO_DOWNLOAD_WORKERS=2
PREVIEW_RESOLVER_WORKERS=1
AUDIO_DOWNLOAD_CONCURRENCY=2

TF_NUM_INTRAOP_THREADS=2
TF_NUM_INTEROP_THREADS=1
OMP_NUM_THREADS=2
```

À utiliser uniquement si :

```text
- 2 workers TF utilisent nettement moins que la VRAM disponible ;
- GPU utilization reste faible ;
- CPU non saturé ;
- SQLite ne montre pas de contention ;
- les benchmarks montrent un meilleur débit global.
```

### A10 — configuration recommandée

```env
ESSENTIA_TENSORFLOW_WORKERS=1
ESSENTIA_LOWLEVEL_WORKERS=1
AUDIO_DOWNLOAD_WORKERS=2
PREVIEW_RESOLVER_WORKERS=1
AUDIO_DOWNLOAD_CONCURRENCY=2

ESSENTIA_TF_BATCH_SIZE=1
ESSENTIA_TF_WARMUP=false
TF_FORCE_GPU_ALLOW_GROWTH=true
TF_NUM_INTRAOP_THREADS=4
TF_NUM_INTEROP_THREADS=2
OMP_NUM_THREADS=4
```

### A10 — 2 workers, expérimental

```env
ESSENTIA_TENSORFLOW_WORKERS=2
TF_NUM_INTRAOP_THREADS=2
TF_NUM_INTEROP_THREADS=1
OMP_NUM_THREADS=2
```

À tester uniquement sur 20–50 pistes. Sur A10, 2 workers peuvent être moins rapides qu’un seul si les deux processus TensorFlow saturent les 24 GB VRAM ou se disputent le GPU.

### Règle finale

```text
A100 40 GB : 1 worker stable, 2 workers recommandé après benchmark, 3 déconseillé.
A100 80 GB : 1 worker stable, 2 workers recommandé, 3 expérimental.
A10 24 GB  : 1 worker recommandé, 2 expérimental, 3+ déconseillé.
```

---

## 4. Pourquoi réduire `AUDIO_DOWNLOAD_WORKERS`

La version précédente proposait :

```env
AUDIO_DOWNLOAD_WORKERS=4
AUDIO_DOWNLOAD_CONCURRENCY=4
```

Ce n’est pas dangereux en soi, mais ce n’est probablement pas utile si le téléchargement est rapide et que le vrai goulot est TensorFlow.

Risques d’un téléchargement trop agressif :

```text
- plus de fichiers temporaires ;
- plus de pression I/O ;
- plus de risques de rate limiting ou échecs yt-dlp ;
- plus de locks jobs en parallèle ;
- aucun gain si la file TensorFlow est déjà remplie.
```

Nouvelle recommandation :

```env
AUDIO_DOWNLOAD_WORKERS=2
AUDIO_DOWNLOAD_CONCURRENCY=2
```

Monter à 4 seulement si :

```text
- la file `essentia_tensorflow` se vide régulièrement ;
- le GPU attend les segments ;
- `nvidia-smi` montre beaucoup de périodes à 0 % ;
- les logs indiquent que les workers TF n’ont pas de travail.
```

---

## 5. Base SQLite vierge sur Lambda

Le nouveau workflow ne transfère plus de base SQLite depuis le PC local.

La base active doit être créée sur le SSD local Lambda :

```text
/home/ubuntu/spotify-curator-runtime/data/spotify_curator.sqlite
```

Les backups et l’export final sont stockés sur le filesystem persistant :

```text
/lambda/nfs/persistent-storage/spotify-curator/backups
/lambda/nfs/persistent-storage/spotify-curator/final-output
```

### Préparation runtime

```bash
cd /lambda/nfs/persistent-storage/spotify-curator
bash scripts/lambda/prepare-runtime.sh
```

Le script `prepare-runtime.sh` crée les dossiers runtime sur SSD et les dossiers persistants NFS.

### Création d’une base vierge

Script : [`scripts/lambda/init-empty-db.sh`](../scripts/lambda/init-empty-db.sh)

Comportement :

```text
1. Vérifier que /home/ubuntu/spotify-curator-runtime/data existe.
2. Si une base existe déjà :
   - refuser par défaut ;
   - ou sauvegarder si --backup-existing est passé ;
   - ou supprimer uniquement si --force est passé.
3. Créer une base vide via les migrations du core.
4. Exécuter PRAGMA integrity_check.
5. Afficher le chemin de la base créée.
```

Commande cible :

```bash
bash scripts/lambda/init-empty-db.sh
# options: --force  --backup-existing
```

Ou via Makefile :

```bash
make lambda-init-empty-db
```

Les migrations utilisent le même chemin que `core-api` au démarrage (`init_db()` → Alembic `upgrade head`), via :

```bash
docker compose … run --rm --no-deps core-api uv run python -c "from app.database.init_db import init_db; init_db()"
```

---

## 6. Configuration `.env.lambda`

Exemple recommandé A100 stable :

```env
APP_ENV=lambda
RUN_ENV=lambda

DATA_DIR=/app/data
SQLITE_PATH=/app/data/spotify_curator.sqlite
DATABASE_URL=sqlite:////app/data/spotify_curator.sqlite
SQLITE_JOURNAL_MODE=WAL
CACHE_DIR=/app/temp-audio
MODELS_DIR=/app/models
LOGS_DIR=/app/logs
EXPORT_DIR=/app/exports

SPOTIFY_CLIENT_ID=
SPOTIFY_REDIRECT_URI=http://127.0.0.1:8000/api/v1/spotify/auth/callback
SPOTIFY_SCOPES=user-read-private user-library-read playlist-read-private playlist-read-collaborative
SPOTIFY_AUTH_STORAGE=sqlite

ESSENTIA_MODEL_PROFILE=phase6-recommended
ESSENTIA_MODELS_DEFAULT_PROFILE=phase6-recommended
ESSENTIA_MODELS_DIR=/app/models/essentia
ESSENTIA_MODELS_MANIFEST=/app/core/app/models_registry/essentia_models_manifest.yaml
ESSENTIA_MODELS_VERIFY_HASH=true
ESSENTIA_MODELS_ACCEPT_LICENSE=false

ESSENTIA_TF_DEVICE=gpu
ESSENTIA_TF_WARMUP=false
ESSENTIA_TF_BATCH_SIZE=1
ESSENTIA_TENSORFLOW_BATCH_SIZE=1
ESSENTIA_TF_REAL_INFERENCE_ENABLED=true
ESSENTIA_TF_ALLOW_STUBS_IN_TESTS=false
ESSENTIA_TF_FAIL_ON_STUB_IN_PRODUCTION=true

ESSENTIA_TENSORFLOW_WORKERS=1
ESSENTIA_LOWLEVEL_WORKERS=1
AUDIO_DOWNLOAD_WORKERS=2
PREVIEW_RESOLVER_WORKERS=1

AUDIO_DOWNLOAD_CONCURRENCY=2
AUDIO_DOWNLOAD_MAX_RETRIES=3
AUDIO_DOWNLOAD_BATCH_SIZE=20

TF_FORCE_GPU_ALLOW_GROWTH=true
TF_CPP_MIN_LOG_LEVEL=1
TF_NUM_INTRAOP_THREADS=4
TF_NUM_INTEROP_THREADS=2
OMP_NUM_THREADS=4

NVIDIA_VISIBLE_DEVICES=all
NVIDIA_DRIVER_CAPABILITIES=compute,utility

VITE_API_BASE_URL=http://127.0.0.1:8000
```

Important :

```text
Utiliser 127.0.0.1, pas localhost, pour Spotify OAuth.
```

---

## 7. Frontend local + tunnel API (recommandé)

Le workflow principal utilise le **frontend Svelte sur le PC local** et un tunnel SSH **API uniquement**. Le service `frontend-dev` sur Lambda (profil `lambda-ui`) reste optionnel (`make lambda-up-a100-ui`).

### Tunnel à ouvrir depuis le PC local

```bash
ssh -i ~/.ssh/lambda_spotify_curator -L 8000:127.0.0.1:8000 ubuntu@<LAMBDA_INSTANCE_IP>
```

PowerShell :

```powershell
ssh -i $env:USERPROFILE\.ssh\lambda_spotify_curator `
  -L 8000:127.0.0.1:8000 `
  ubuntu@<LAMBDA_INSTANCE_IP>
```

### Frontend local (PC)

```bash
cd app/frontend
VITE_API_BASE_URL=http://127.0.0.1:8000 npm run dev -- --host 127.0.0.1 --port 5173
```

Ouvrir :

```text
http://127.0.0.1:5173
```

L’UI appelle l’API Lambda via le tunnel :

```text
http://127.0.0.1:8000
```

Ne pas forwarder le port `5173` sur la VM si le frontend tourne localement.

### Redirect URI Spotify à configurer

Dans Spotify Developer Dashboard, ajouter exactement :

```text
http://127.0.0.1:8000/api/v1/spotify/auth/callback
```

Ne pas utiliser :

```text
http://localhost:8000/...
```

Spotify exige que le `redirect_uri` corresponde exactement à celui déclaré dans le dashboard, et les URI loopback doivent utiliser une IP explicite comme `127.0.0.1`.

### Ce qui se passe techniquement

```text
1. Tu ouvres l’UI via http://127.0.0.1:5173.
2. Tu cliques sur Connect Spotify.
3. L’UI demande à l’API distante Lambda de générer l’URL OAuth.
4. Spotify ouvre la page d’autorisation dans ton navigateur local.
5. Après validation, Spotify redirige vers :
   http://127.0.0.1:8000/api/v1/spotify/auth/callback
6. Le tunnel SSH transfère cette requête vers l’API Lambda.
7. L’API Lambda échange le code OAuth contre des tokens.
8. Les tokens sont stockés dans la SQLite Lambda.
```

Résultat : tu es reconnecté à Spotify directement dans la base Lambda.

---

## 8. Téléchargement des modèles Essentia sur Lambda

Les modèles ne sont plus transférés depuis le PC.

Ils doivent être téléchargés depuis l’UI du projet, sur la VM Lambda.

Chemin persistant :

```text
/lambda/nfs/persistent-storage/spotify-curator/models
```

Montage conteneur :

```text
/app/models
```

Workflow :

```text
1. Ouvrir l’UI via tunnel SSH.
2. Aller dans la page Features / Models / Advanced analysis.
3. Accepter explicitement la licence si l’UI le demande.
4. Télécharger le profil phase6-recommended.
5. Vérifier le statut des modèles dans l’UI.
6. Lancer un smoke test ou benchmark.
```

Recommandation :

```text
Commencer par phase6-recommended.
Éviter phase6-full pour le premier run complet.
```

---

## 9. Démarrage complet Lambda

### Sur l’instance Lambda

```bash
sudo bash scripts/lambda/install-host-prereqs.sh
bash scripts/lambda/verify-docker-gpu.sh   # après reconnexion SSH si groupe docker ajouté

cd /lambda/nfs/persistent-storage
git clone <REPO_GIT> spotify-curator
cd spotify-curator

cp .env.lambda.example .env.lambda
nano .env.lambda
```

Modifier au minimum :

```env
SPOTIFY_CLIENT_ID=<ton_client_id_spotify>
SPOTIFY_REDIRECT_URI=http://127.0.0.1:8000/api/v1/spotify/auth/callback
VITE_API_BASE_URL=http://127.0.0.1:8000
```

Préparer runtime et créer base :

```bash
bash scripts/lambda/prepare-runtime.sh
bash scripts/lambda/init-empty-db.sh
```

Build :

```bash
make lambda-build
```

Vérification GPU :

```bash
make lambda-check-gpu
```

Démarrage A100 :

```bash
make lambda-up-a100
# alias: make lambda-up
```

Démarrage A10 (même scale stable) :

```bash
make lambda-up-a10
```

Après benchmark A100 (2 workers TF) :

```bash
make lambda-up-a100-tf2
# alias: make lambda-up-tf2
```

Vérification services :

```bash
bash scripts/lambda/check-services.sh
```

---

## 10. Tunnel API + UI locale

Depuis le PC local (tunnel API seul) :

```bash
ssh -i ~/.ssh/lambda_spotify_curator \
  -L 8000:127.0.0.1:8000 \
  ubuntu@<LAMBDA_INSTANCE_IP>
```

Frontend local : voir §7. Puis :

```text
1. Connecter Spotify.
2. Importer liked tracks/playlists.
3. Télécharger modèles Essentia.
4. Lancer benchmark (scripts/lambda/benchmark-pipeline.sh via conteneur core-api).
5. Lancer analyse complète.
```

`check-services.sh` exige l’API ; le frontend VM est un avertissement seulement (`CHECK_FRONTEND=0` pour ignorer).

---

## 11. Benchmark recommandé

### A100

1 worker :

```bash
make lambda-down
make lambda-up
bash scripts/lambda/benchmark-pipeline.sh 30
```

2 workers :

```bash
make lambda-down
make lambda-up-tf2
bash scripts/lambda/benchmark-pipeline.sh 30
```

Comparer :

```text
- temps total ;
- segments/min ;
- durée moyenne essentia_tensorflow ;
- p95 essentia_tensorflow ;
- utilisation GPU ;
- VRAM ;
- failures.
```

### A10

Tester d’abord uniquement :

```bash
make lambda-up
bash scripts/lambda/benchmark-pipeline.sh 30
```

Tester 2 workers seulement si le GPU est sous-utilisé et la VRAM reste confortable.

---

## 12. Analyse complète

Depuis l’UI :

```text
Features → Run complete local analysis
```

Configuration recommandée :

```text
profile : phase6-recommended
only_missing : true
include_tensorflow : true
```

Ne pas utiliser `phase6-full` au premier passage.

---

## 13. Suivi

GPU :

```bash
watch -n 1 nvidia-smi
```

Logs TF :

```bash
make lambda-logs-tf
```

Progression jobs :

```bash
docker compose -f docker-compose.yml -f docker-compose.gpu.yml -f docker-compose.lambda.yml \
  --env-file .env.lambda exec -T core-api \
  uv run python scripts/inspect_jobs.py
```

Reset locks stale (après crash worker, avec backup SQLite) :

```bash
docker compose ... exec -T core-api uv run python scripts/reset_stale_jobs.py --dry-run
docker compose ... exec -T core-api uv run python scripts/reset_stale_jobs.py --stage essentia_tensorflow_embeddings
```

Backups intermédiaires :

```bash
make lambda-backup
```

---

## 14. Export final

Après analyse :

```bash
make lambda-down
make lambda-export
```

Le script doit produire :

```text
/lambda/nfs/persistent-storage/spotify-curator/spotify-curator-lambda-output.tar.gz
```

Contenu attendu :

```text
final-output/spotify_curator.sqlite
final-output/app.sqlite
```

---

## 15. Récupération locale

Depuis le PC local :

```bash
scp -i ~/.ssh/lambda_spotify_curator \
  ubuntu@<LAMBDA_INSTANCE_IP>:/lambda/nfs/persistent-storage/spotify-curator/spotify-curator-lambda-output.tar.gz \
  .
```

Extraction :

```bash
tar -xzf spotify-curator-lambda-output.tar.gz
```

La base finale est :

```text
final-output/spotify_curator.sqlite
```

Tu peux ensuite l’importer dans ton volume Docker local ou la conserver comme snapshot analysé.

---

## 16. Rôle de `restore-input.sh`

`restore-input.sh` reste utile uniquement si tu veux reprendre une base existante ou restaurer un backup.

Dans le workflow principal Lambda, il n’est plus utilisé.

Nouveau workflow principal :

```text
prepare-runtime.sh
→ init-empty-db.sh
→ make lambda-build
→ make lambda-up
→ Spotify OAuth via tunnel
→ import bibliothèque
→ download modèles
→ analyse
→ export-final-sqlite.sh
```

---

## 17. Cibles Makefile

Référence : [`Makefile`](../Makefile).

```bash
make lambda-init-empty-db
make lambda-build
make lambda-check-gpu
make lambda-up-a100      # ou make lambda-up / make lambda-up-a10 (sans frontend VM)
make lambda-up-a100-ui   # optionnel : profil lambda-ui
make lambda-up-a100-tf2  # ou make lambda-up-tf2
make lambda-down
make lambda-backup
make lambda-export
make lambda-logs-tf
```

---

## 18. Checklist de validation incrémentale

Ordre recommandé (post-mortem A100) :

```text
1. install-host-prereqs.sh + verify-docker-gpu.sh
2. init-empty-db + lambda-build + lambda-check-gpu (check_essentia_tf.py)
3. make lambda-up-a100 (sans lambda-ui)
4. Tunnel API seul + frontend local PC
5. OAuth Spotify + import bibliothèque
6. Téléchargement modèles phase6-recommended depuis l’UI
7. Workers audio + heartbeat essentia_tensorflow visible
8. 1 job pipeline avec au moins 1 job_item essentia_tensorflow traité
9. nvidia-smi actif pendant inférence
10. benchmark-pipeline.sh (30 pistes)
11. export final + integrity_check
```

## 19. Dépannage

| Symptôme | Diagnostic |
|----------|------------|
| Worker TF restart loop | Logs : warmup MAEST ; `ESSENTIA_TF_WARMUP=false` dans `.env.lambda` ; pas d’override dans `docker-compose.gpu.yml` |
| `Cannot dlopen GPU libraries` | Image `gpu` : CUDA 11.2/cuDNN via conda + `LD_LIBRARY_PATH` (voir Dockerfile) |
| `check_tf_gpu` échoue sans `tensorflow` Python | Utiliser `make lambda-check-gpu` → `check_essentia_tf.py` |
| Pipeline bloquée | `inspect_jobs.py` ; `reset_stale_jobs.py --dry-run` |
| Frontend VM inaccessible | Normal si `lambda-ui` off ; utiliser frontend local + tunnel API |

Inspecter l’environnement **par service** (pas un grep global ambigu) :

```bash
docker compose -f docker-compose.yml -f docker-compose.gpu.yml -f docker-compose.lambda.yml \
  --env-file .env.lambda exec essentia-tensorflow-worker \
  bash -lc 'env | grep -E "ESSENTIA_TF_WARMUP|ESSENTIA_TENSORFLOW_WORKERS|DATABASE_URL|LD_LIBRARY_PATH"'
```

## 20. Critères d’acceptation

Le mode Lambda mis à jour est valide si :

```text
- aucune SQLite locale n’est nécessaire pour démarrer ;
- une base vierge est créée sur Lambda ;
- les migrations sont appliquées ;
- Spotify OAuth fonctionne via tunnel SSH ;
- les tokens Spotify sont stockés dans la SQLite Lambda ;
- l’import Spotify remplit la base Lambda ;
- les modèles Essentia sont téléchargeables depuis l’UI ;
- `check_essentia_tf.py` + `nvidia-smi` OK dans le conteneur TF ;
- `ESSENTIA_TF_WARMUP=false` n’empêche pas l’inférence (warmup optionnel) ;
- A100/A10 sont configurables via .env.lambda ;
- 1 worker TF fonctionne ;
- 2 workers TF sont benchmarkables sur A100 ;
- l’export final produit spotify_curator.sqlite ;
- la base finale passe PRAGMA integrity_check.
```

---

## 21. Annexe — import SQLite legacy (PC → Lambda)

Workflow **optionnel** si vous souhaitez reprendre une base existante au lieu de `init-empty-db.sh`.

Depuis le PC Windows, exporter depuis le volume Docker `spotify_curator_data` :

```powershell
docker compose stop core-api
docker run --rm -v spotify_curator_data:/from -v ${PWD}/export-lambda/data:/to alpine:3.20 sh -c `
  "sqlite3 /from/spotify_curator.sqlite 'PRAGMA wal_checkpoint(FULL);' && cp /from/spotify_curator.sqlite /to/"
tar -czf spotify-curator-lambda-input.tar.gz export-lambda
scp -i ~/.ssh/lambda_spotify_curator spotify-curator-lambda-input.tar.gz ubuntu@<IP>:/lambda/nfs/persistent-storage/spotify-curator/
```

Sur Lambda :

```bash
bash scripts/lambda/prepare-runtime.sh
bash scripts/lambda/restore-input.sh spotify-curator-lambda-input.tar.gz
```

---

## 22. Annexe — réimporter la base analysée en local (Windows)

Après `make lambda-export` et `scp` de l’archive :

```powershell
tar -xzf spotify-curator-lambda-output.tar.gz
docker compose stop core-api
docker run --rm -v spotify_curator_data:/app/data -v ${PWD}/final-output:/host alpine:3.20 sh -c `
  "cp /host/spotify_curator.sqlite /app/data/spotify_curator.sqlite 2>/dev/null || cp /host/app.sqlite /app/data/spotify_curator.sqlite"
docker compose up -d
```

---

## 23. Résumé opérationnel

```bash
# --- Lambda ---
cd /lambda/nfs/persistent-storage/spotify-curator
cp .env.lambda.example .env.lambda   # renseigner SPOTIFY_CLIENT_ID
bash scripts/lambda/prepare-runtime.sh
bash scripts/lambda/init-empty-db.sh
make lambda-build && make lambda-check-gpu
make lambda-up-a100
bash scripts/lambda/check-services.sh
```

```bash
# --- PC local : tunnel API + frontend dev ---
ssh -i ~/.ssh/lambda_spotify_curator -L 8000:127.0.0.1:8000 ubuntu@<IP>
cd app/frontend && VITE_API_BASE_URL=http://127.0.0.1:8000 npm run dev -- --host 127.0.0.1 --port 5173
# http://127.0.0.1:5173 → OAuth Spotify → import bibliothèque → modèles UI → analyse
```

```bash
# --- Lambda : export ---
make lambda-export
scp ubuntu@<IP>:/lambda/nfs/persistent-storage/spotify-curator/spotify-curator-lambda-output.tar.gz .
```
